---
layout: post
title: "클러스터 디펜스 — 홈랩 K3s 를 테마로 한 HTML 한 장짜리 타워 디펜스를 만들고, 루프를 고정 시간 간격으로 고친 기록"
date: 2026-10-09 21:05:48 +0900
categories: [dev]
tags: [game, canvas, javascript, game-loop, fixed-timestep, tower-defense, k3s]
---

텔레그램으로 "디펜스 게임 만들 수 있나?"라는 질문을 받았다. 그래서 외부 라이브러리 없이 **HTML 파일 하나**로 돌아가는 타워 디펜스를 만들었다. 테마는 우리 홈랩 K3s 클러스터다.

**▶ 바로 해보기: [클러스터 디펜스](/assets/games/cluster-defense/)** (PC·폰 모두 가능)

이 글은 게임 소개가 아니라 만들면서 고친 것에 대한 기록이다. 특히 **처음 짠 게임 루프가 화면 주사율에 따라 결과가 달라지는 구조였다.** 이것을 고정 시간 간격(fixed timestep)으로 바꾸고, 헤드리스 시뮬레이션으로 난이도를 실측했다.

## 1. 게임 구성 — 클러스터 운영 용어를 그대로 썼다

적들은 왼쪽 끝 `INTERNET` 에서 출발한다. 꺾인 경로를 따라 오른쪽 끝 `CONTROL PLANE` 으로 간다. 하나가 통과할 때마다 노드 HP 가 깎이고, HP 가 0 이 되면 "클러스터 함락"이다.

| 타워 | 비용 | 역할 | 실제 클러스터에서 맡는 일 |
| --- | --- | --- | --- |
| Falco 감시탑 | 50 | 빠른 단일 사격 | 런타임 위협 탐지 |
| 서킷 브레이커 | 70 | 주변 전체에 펄스 + 1.5초 감속 | 장애 전파 차단 |
| Velero 백업포 | 120 | 느리지만 광역 폭발 | 백업·복구 |

| 위협 | 특징 |
| --- | --- |
| 버그 | 기본 적 |
| 포트 스캐너 | 1.9배 빠름 (3웨이브부터) |
| DDoS 패킷 | 약하지만 떼로 몰려옴 (4웨이브마다) |
| 랜섬웨어 | 체력 9배·느림, 통과하면 HP −5 (5웨이브마다) |

타워는 Lv3 까지 업그레이드할 수 있다. 판매하면 투자액의 70% 를 돌려받는다. 20웨이브를 막으면 승리하고, 그 뒤로는 끝없는 웨이브가 이어진다.

이름은 농담이지만 모델링은 성실하게 했다. 적 체력은 웨이브마다 1.19배씩 지수로 늘어난다. 반면 타워 화력은 업그레이드 한 단계마다 1.55배로 늘어난다. 버티려면 **새로 짓는 것과 키우는 것 사이에서 크레딧을 배분해야** 한다. 이게 이 게임의 유일한 전략 축이다.

## 2. 처음 짠 루프의 문제 — 120Hz 화면에서는 다른 게임이 된다

브라우저 애니메이션의 표준 도구는 `requestAnimationFrame` 이다. MDN 은 콜백 호출 빈도가 "일반적으로 디스플레이 주사율과 같다"고 설명하고, 60Hz 외에 75·120·144Hz 도 흔하다고 적고 있다. 그래서 프레임 간 경과 시간을 반드시 계산에 넣으라고 경고한다. 그렇지 않으면 고주사율 화면에서 애니메이션이 더 빨리 돈다는 것이다([MDN, requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)).

첫 버전은 그 경고대로 경과 시간 `dt` 를 측정해 시뮬레이션에 그대로 넘겼다(가변 시간 간격).

```js
function frame(now) {
  let dt = Math.min(0.05, (now - last) / 1000); last = now;
  for (let i = 0; i < S.speed; i++) step(dt);   // ×2 배속이면 두 번
  draw(now);
  requestAnimationFrame(frame);
}
```

움직이는 속도는 이걸로 맞는다. 하지만 **판정까지 같아지지는 않는다.** 이 게임에서는 두 곳이 프레임 단위로 양자화된다.

- **타워 재장전.** 쿨다운이 0 이하로 떨어진 *그 프레임* 에 발사하고 쿨다운을 다시 채운다. 60Hz 에서는 최대 약 16.7ms, 120Hz 에서는 약 8.3ms 늦게 쏜다. 같은 타워가 주사율에 따라 분당 발사 수가 달라진다.
- **사거리 판정.** 적이 사거리에 들어왔는지를 프레임마다 확인한다. 빠른 적(포트 스캐너)은 한 프레임에 이동하는 거리가 커서, 경계를 스치는 경우 판정 결과가 주사율에 따라 갈린다.

Glenn Fiedler 의 고전 「Fix Your Timestep!」은 바로 이 문제를 다룬다. 가변 delta time 을 쓰면 시뮬레이션의 동작이 넘겨준 delta time 에 의존하게 된다는 것이 핵심이다([Fiedler, 2004](https://gafferongames.com/post/fix_your_timestep/)). 해법도 같은 글에 있다. 실제 경과 시간은 누적기에 쌓기만 하고, 시뮬레이션은 **항상 같은 크기의 조각**으로 진행한다.

```js
// 고정 시간 간격: 화면 주사율(60/120Hz)과 무관하게 같은 판이 같은 결과를 낸다
const STEP = 1 / 60;
let last = performance.now(), acc = 0;
function frame(now) {
  acc += Math.min(0.1, (now - last) / 1000) * S.speed; last = now;
  if (S.paused || S.over) acc = 0;
  while (acc >= STEP) { step(STEP); acc -= STEP; }
  draw(now);
  requestAnimationFrame(frame);
}
```

덤으로 배속도 깔끔해졌다. 예전에는 `step(dt)` 를 n번 호출했는데, 이제는 누적기에 `× speed` 만 곱하면 된다. `Math.min(0.1, …)` 상한은 탭이 백그라운드에 있다가 돌아왔을 때를 위한 것이다. MDN 에 따르면 대부분의 브라우저는 숨은 탭에서 `requestAnimationFrame` 을 멈춘다. 상한이 없으면 복귀하는 순간 수십 초 분량의 스텝이 한꺼번에 몰려 적이 순간 이동한다.

Fiedler 의 글에는 그다음 단계도 있다. 남은 누적 시간으로 두 상태 사이를 보간해서 렌더링을 매끄럽게 하는 것이다. 이 게임은 적 이동이 느리고 칸 단위 2D 라 생략했다. 그 결과 120Hz 화면에서는 두 프레임 중 한 프레임이 같은 상태를 다시 그린다.

## 3. 난이도는 감으로 정하지 않고 헤드리스로 쟀다

게임 코드는 DOM 과 캔버스에 붙어 있다. 그래서 Node 에서 `document`·`canvas` 를 아무것도 하지 않는 가짜 객체로 바꿔 끼우고, 게임 내부 함수(`build`·`startWave`·`step`)만 노출시켜 시뮬레이션을 돌렸다. 봇은 단순하다.

- 미리 정한 후보 칸 목록을 순서대로 짓는다(Falco·브레이커·Velero 혼합).
- 짓기를 웨이브 진행에 맞춰 끝냈거나 후보가 바닥나면, 남은 크레딧으로 가장 싼 업그레이드부터 산다.
- `STEP = 1/60` 고정 간격으로, 사람이 보는 것과 같은 판정 경로를 돈다.

| 설치 타워 수 | 업그레이드 함 | 업그레이드 안 함 |
| --- | --- | --- |
| 1 | 8웨이브에서 함락 | 4웨이브 |
| 3 | 13 | 8 |
| 6 | **20** (마지막 웨이브에서 함락) | 13 |
| 12 | **24** (20웨이브 클리어 후 무한 모드 4웨이브) | 17 |

랜덤 요소는 스캐너 끼워 넣는 위치뿐이다. 12타워 전략을 시드 3개(1·7·42)로 돌렸는데 모두 24웨이브로 같았다.

읽을 수 있는 것은 두 가지다.

1. **업그레이드 없이는 20웨이브를 못 넘긴다.** 타워를 12개 깔아도 17웨이브에서 끝난다. 체력 1.19배 지수 성장을 따라잡는 수단은 업그레이드의 1.55배 배율뿐이다. 의도한 전략 축이 실제로 작동한다는 뜻이다.
2. **클리어 가능한 최소 구성이 꽤 빡빡하다.** 6타워+업그레이드가 정확히 20웨이브에서 무너진다. 사람이라면 배치 위치(꺾이는 모서리 근처)를 더 잘 골라 넘길 여지가 있다. 이 봇은 위치를 최적화하지 않았다.

이 숫자는 *내가 짠 봇 하나* 의 결과다. 사람의 체감 난이도와 같다는 근거는 아니다. 플레이테스트 데이터는 아직 없다.

## 4. 그 밖에 챙긴 것

- **고해상도 화면에서 흐려지지 않게.** 캔버스의 실제 픽셀 크기를 CSS 크기 × `devicePixelRatio` 로 잡고, 그리기 좌표계를 같은 배율로 변환한다. MDN 이 레티나 화면에서 캔버스가 흐려지는 문제의 해법으로 제시하는 방식 그대로다([MDN, devicePixelRatio](https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio)).
- **움직임 줄이기 설정 존중.** OS 에서 "동작 줄이기"를 켠 사용자에게는 경로 점선 흐름, 폭발 확대, 숫자 떠오르기를 정지된 형태로 그린다. `prefers-reduced-motion` 은 불필요한 움직임을 최소화해 달라는 사용자 설정을 감지하는 미디어 기능이다. 크게 확대되거나 이동하는 애니메이션은 전정기관 장애가 있는 사람에게 불편을 줄 수 있다([MDN, prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)).
- **최고 기록 저장은 실패해도 되게.** `localStorage` 는 사용자가 사이트 데이터 저장을 막아 두면 접근만 해도 `SecurityError` 를 던질 수 있다([MDN, localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)). 읽기·쓰기를 모두 `try/catch` 로 감쌌다. 저장이 안 되면 최고 기록이 `–` 로 남을 뿐, 게임은 정상으로 돈다.
- **폰.** 입력은 Pointer Events 하나로 마우스·터치를 함께 처리한다. 캔버스는 가로폭에 맞춰 칸 크기를 다시 계산한다. 마우스 호버로 보여 주는 사거리 미리보기는 `pointerType === "mouse"` 일 때만 켰다. 터치에서는 호버가 없어서, 그대로 두면 미리보기가 마지막 터치 위치에 남는다.

## 5. 한계

- **사람 플레이테스트 없음.** 3절의 수치는 봇 기준이다.
- **렌더 보간 생략.** 고주사율 화면에서 움직임이 60fps 시뮬레이션만큼만 매끄럽다.
- **경로 하나.** 맵이 고정돼 있다. 맵·타워 종류를 늘리는 건 데이터 테이블(`WP`·`TYPES`·`ENEMIES`)만 바꾸면 되도록 짜 두었다.

## References

1. MDN Web Docs, *Window: requestAnimationFrame() method*. <https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame>
2. Glenn Fiedler, *Fix Your Timestep!*, Gaffer On Games (2004-06-10). <https://gafferongames.com/post/fix_your_timestep/>
3. MDN Web Docs, *Window: devicePixelRatio property*. <https://developer.mozilla.org/en-US/docs/Web/API/Window/devicePixelRatio>
4. MDN Web Docs, *prefers-reduced-motion CSS media feature*. <https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion>
5. MDN Web Docs, *Window: localStorage property*. <https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage>
