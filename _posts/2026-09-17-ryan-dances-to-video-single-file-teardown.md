---
layout: post
title: "라이언은 어떻게 영상을 따라 춤추는가 — 한 파일 224KB 를 뜯어보기"
date: 2026-09-17 20:46:31 +0900
categories: [Engineering, Frontend]
tags: [Threejs, WebGL, 애니메이션, IK, WebAudio, 코드리딩]
---

분석 대상은 이 한 페이지다.

**[RYAN BAD CHALLENGE — quettalabs.com/garage/ryan-bad-challenge.html](https://quettalabs.com/garage/ryan-bad-challenge.html)**

페이지 좌측 패널은 스스로를 이렇게 설명한다. *"보내주신 영상 프레임을 기준으로 몸을 기울이고, 한쪽 팔꿈치를 안쪽 45°로 접어 손끝만 위아래로 파닥입니다."* 즉 **영상 하나를 참조해 3D 캐릭터가 그 춤을 따라 추는 것**이 이 데모의 주장이다.

이 글은 그 주장이 코드 상에서 *어떤 구조로* 구현되어 있는지를 뜯어본다. 브라우저에서 페이지 소스를 받아 직접 읽고 측정한 결과이고, 수치는 전부 그 파일에서 나온 것이다. 반대로 **페이지 바깥의 제작 파이프라인은 관측할 수 없으므로** 그 부분은 추측하지 않고 마지막 절에 한계로 남겼다.

먼저 전체 실측치부터.

| 항목 | 실측값 |
| --- | --- |
| 전체 파일 크기 | 224,536 bytes (HTML 1개, 298줄) |
| 그중 인라인 오디오 | 195,545 bytes — **전체의 87%** |
| 오디오 실체 | AAC 48kHz 스테레오 163kbps, 길이 **7.200000초** |
| 외부 의존 | three.js 0.160.0 + OrbitControls (unpkg, importmap) |
| 키프레임 | **64개**, 0 → 7.2초, 간격 0.1143초 |
| 애니메이션 루프 길이 | `LOOP = 7.2` — 오디오 길이와 정확히 일치 |
| 팔 뼈 길이 | 상완 0.48 · 전완 0.56 |

---

## 1. 파일의 87% 는 소리다

`<script src>` 는 하나도 없다. 대신 오디오가 한 줄로 박혀 있다.

```js
music.src='data:audio/mp4;base64,AAAAHGZ0eXBNNEEgAAACAE00QSBpc29taXNvMg...';
```

이 한 줄이 195,545자다. base64 는 3옥텟을 4문자로 바꾸는 인코딩이므로[^rfc4648] 원본 대비 약 4/3 배가 된다. 실제로 디코딩해 보면 146,657바이트의 M4A 파일이 나오고 ($195{,}545 / 146{,}657 = 1.3333$), `ffprobe` 로 재보면 길이가 **7.200000초**다. 코드 맨 위의 `const LOOP=7.2` 와 소수점까지 같다. 우연이 아니라, 뒤에서 볼 설계의 핵심이다.

왜 파일로 두지 않고 문자열로 박았을까. data URL 로 박으면 **HTML 하나만 있으면 어디서든 돈다.** 서버 설정도, MIME 타입도, CORS 도, 상대경로도 신경 쓸 게 없다. 습작·데모·포트폴리오처럼 "링크 하나로 끝나야 하는" 산출물에서는 합리적인 선택이다.

대가는 정직하게 크다. 바이트가 약 3분의 1 늘고, 브라우저 캐시를 **오디오 단위로** 쓸 수 없으며(HTML 이 바뀌면 소리도 같이 다시 받는다), 첫 렌더 전에 문자열 전체를 파싱해야 한다. 그림이 아니라 음악 한 곡이라 그 비용이 87%까지 올라갔을 뿐, 판단 자체는 트레이드오프다.

## 2. 캐릭터는 에셋이 아니라 코드다

두 번째로 눈에 띄는 것은 `.glb` 도 `.fbx` 도 없다는 점이다. 라이언은 **런타임에 프리미티브로 조립된다.**

```js
const torso = ball(body, 1, fur, [0,0,0], [.9,1.06,.69]);   // 타원체로 스케일한 구
const head  = group(body, 'head', [0,1.47,0]);
ball(head, 1.08, fur, [0,0,0], [1.08,1,.9]);
for (const sign of [-1,1]) {
  ball(head, .225, fur, [sign*.77,.77,-.035], [1,1,.64]);   // 귀
  // Positions lie outside the ellipsoid, so eyes never sink into the head.
  ball(head, .078, black, [sign*.33,.12,.928], [1,1,.40]);  // 눈
}
```

구(`SphereGeometry`)와 캡슐(`CapsuleGeometry`)과 튜브(`TubeGeometry`) 몇 개, 재질 네 종류가 전부다. 입은 `CatmullRomCurve3` 로 곡선을 만들고 반지름 0.017의 튜브를 씌운 뒤, `x` 부호만 뒤집어 반대쪽을 복제한다.

이게 왜 중요한가. 이 선택은 단순한 "에셋 없이 만들기"가 아니라, **4절에서 볼 IK 해법이 성립하게 만드는 전제**다. 잠시 기억해 두자.

## 3. 동작은 한 층이 아니라 두 층이다

### 3.1 아래층 — 64개의 키프레임

```js
const keys=[
 {t:0.0000, active:[-0.7600,-0.3500,0.3500], rest:[0.7600,-0.3500,0.3500], roll:0, yaw:0, lift:0, cross:0},
 {t:0.1143, active:[-0.5040, 0.0157,0.5557], rest:[0.7600,-0.3271,0.3500], roll:0.0137, yaw:-0.0137, ...},
 ...
 {t:7.2000, active:[-0.7600,-0.3500,0.3500], rest:[0.7600,-0.3500,0.3500], roll:0, yaw:0, lift:0, cross:0}
];
```

키 하나가 들고 있는 것은 **관절 각도가 아니라 손끝의 목표 위치**(`active`, `rest`)와 몸통의 `roll` · `yaw`, 그리고 `lift` · `cross` 두 개의 보조 스칼라다. 뼈를 직접 회전시키는 대신 "손이 어디에 있어야 하는가"만 기록해 두고, 각도는 런타임에 역으로 푼다(4절).

키 사이는 유니폼 Catmull–Rom 으로 메운다. 코드에 적힌 형태 그대로 쓰면

$$P(u)=\tfrac{1}{2}\Big[\,2P_1+(-P_0+P_2)\,u+(2P_0-5P_1+4P_2-P_3)\,u^2+(-P_0+3P_1-3P_2+P_3)\,u^3\,\Big]$$

이고, 여기서 $u\in[0,1]$ 는 두 키 사이의 정규화된 시간이다. 이 식의 도함수가 6절에서 문제가 된다.

한 가지 수치가 눈에 걸린다. 키 간격은 $7.2/63 = 0.114286$초이고, 화면 배지는 `60FPS VIDEO REFERENCE` 라고 적혀 있다. 60fps 기준 7.2초는 432프레임인데, 키 간격 0.1143초는 **6.857프레임**이다. 정수가 아니다. 즉 키프레임은 *특정 프레임을 골라 찍은 것*이 아니라 **구간 전체를 64개로 균등 리샘플링한 것**이다. 이것은 파일에서 확인되는 사실이고, 원본 영상에서 어떻게 뽑았는지는 별개 문제다(7절).

### 3.2 위층 — 시간에 직접 반응하는 절차적 오버레이

키프레임만으로는 이 춤이 안 나온다. `pose(time)` 안에는 키프레임과 **무관하게 절대 시각에 반응하는** 코드가 따로 있다.

```js
const smooth = x => { x = THREE.MathUtils.clamp(x,0,1); return x*x*(3-2*x); };
const brake  = 1 - smooth((t-1.34)/.11);
const pitch  = t < 1.45 ? .68*Math.sin(2*Math.PI*4*t)*brake : 0;   // 손 파닥임
const strikes = [4.20, 4.82, 5.44, 6.06];                          // 발 구르기
const pop = [1.56,2.08,2.61,3.14,3.67].reduce((v,o)=>v+chestPulse(o), 0);  // 가슴 튕김
```

즉 손끝의 파닥임은

$$\theta(t)=0.68\,\sin(8\pi t)\cdot\Big(1-s\!\left(\tfrac{t-1.34}{0.11}\right)\Big),\qquad s(x)=x^{2}(3-2x)$$

라는 **닫힌 형식의 진동**이다. $8\pi t$ 는 4Hz, 분당 240회. 1.34초부터 0.11초에 걸쳐 smoothstep 으로 제동이 걸리고 1.45초에 완전히 멈춘다. 발 구르기·가슴 튕김·후퇴·복귀도 전부 같은 방식으로, smoothstep 을 가중치 삼아 겹쳐 쓴다.

이 이중 구조가 이 데모의 실제 아키텍처다. **큰 궤적은 샘플링해 두고, 빠르고 반복적인 디테일은 수식으로 만든다.** 4Hz 로 파닥이는 손을 키프레임으로 담으려면 나이퀴스트 기준으로도 8Hz 이상, 실제로는 훨씬 촘촘히 찍어야 한다. 64개로는 어림없다. 반대로 몸통이 기울고 도는 저주파 궤적은 수식으로 쓰기 어렵고 샘플이 편하다. 주파수 대역으로 일을 나눈 셈이다.

여기서 흥미로운 부수 관측이 하나 나온다. 두 액센트 계열의 간격을 재 보면

| 계열 | 시각(초) | 간격 | 환산 BPM |
| --- | --- | --- | --- |
| 가슴 튕김 | 1.56 · 2.08 · 2.61 · 3.14 · 3.67 | 0.52~0.53 | 약 113.7 |
| 발 구르기 | 4.20 · 4.82 · 5.44 · 6.06 | 0.62 | 약 96.8 |

둘이 같은 템포 격자 위에 있지 않다. 하나의 BPM 에 스냅해 찍은 값이 아니라, **구간별로 눈으로 맞춘 시각**이라는 뜻이다. 사람이 영상을 보며 타점을 찍은 결과에 가깝다.

## 4. 팔은 각도가 아니라 위치로 푼다 — 2본 IK

키가 손끝 위치만 들고 있으니 어깨·팔꿈치 각도는 풀어야 한다. 코드는 교과서적인 **코사인 법칙 2본 IK** 를 쓴다.

```js
function solve(arm, target, bendHint){
  const S = arm.anchor, T = new THREE.Vector3(...target);
  dir.copy(T).sub(S); let d = dir.length(); dir.normalize();
  d = THREE.MathUtils.clamp(d, .10, UP_ARM + FORE_ARM - .008);
  T.copy(S).addScaledVector(dir, d);
  const a = (UP_ARM*UP_ARM - FORE_ARM*FORE_ARM + d*d) / (2*d),
        h = Math.sqrt(Math.max(0, UP_ARM*UP_ARM - a*a));
  pole.set(...bendHint);
  bend.copy(pole).addScaledVector(dir, -pole.dot(dir)).normalize();
  elbowPoint.copy(S).addScaledVector(dir, a).addScaledVector(bend, h);
  arm.shoulder.quaternion.setFromUnitVectors(down, v.copy(elbowPoint).sub(S).normalize());
  q.copy(arm.shoulder.quaternion).invert();
  arm.elbow.quaternion.setFromUnitVectors(down, v.copy(T).sub(elbowPoint).normalize().applyQuaternion(q));
}
```

어깨 $S$ 에서 목표 $T$ 까지 거리를 $d$, 상완·전완 길이를 $\ell_1=0.48$, $\ell_2=0.56$ 이라 하면

$$a=\frac{\ell_1^{2}-\ell_2^{2}+d^{2}}{2d},\qquad h=\sqrt{\max\!\left(0,\;\ell_1^{2}-a^{2}\right)}$$

이고 팔꿈치 위치는 $E = S + a\,\hat{d} + h\,\hat{b}$ 로 정해진다. $\hat b$ 는 `bendHint`(폴 벡터)를 $\hat d$ 에 수직으로 투영해 정규화한 것 — 두 개의 해 중 어느 쪽으로 굽힐지를 고르는 장치다.

눈여겨볼 두 줄이 있다.

- `d` 를 $[0.10,\;\ell_1+\ell_2-0.008]$ 로 **클램프**한다. 위쪽 여유 0.008은 팔이 완전히 펴져 $h=0$ 이 되는 특이점을 피한다. 이 지점에서 $\hat b$ 의 기여가 사라져 팔꿈치 방향이 정의되지 않고 떨림이 생긴다. 아래쪽 0.10은 목표가 어깨에 너무 가까워 $d\to 0$ 일 때 $a$ 가 발산하는 것을 막는다.
- 팔꿈치 회전을 **어깨 회전의 역쿼터니언으로 감아서** 넣는다(`q.invert()` 후 `applyQuaternion`). three.js 의 `Object3D.quaternion` 은 부모 기준 로컬 회전이므로, 월드 방향을 그대로 넣으면 어깨 회전이 두 번 먹는다.[^threeobj]

### 그런데 왜 팔이 비틀리지 않는가

`Quaternion.setFromUnitVectors(from, to)` 는 두 방향을 잇는 최단 회전을 준다. 이 회전은 **뼈 축을 중심으로 한 비틀림(트위스트)을 결정하지 않는다.** 실제로 사용된 버전(r160)의 구현을 보면, 두 벡터가 정반대일 때는 임의의 수직축을 골라 쓴다.

```js
let r = vFrom.dot( vTo ) + 1;
if ( r < Number.EPSILON ) {
  // vFrom and vTo point in opposite directions
  r = 0;
  if ( Math.abs( vFrom.x ) > Math.abs( vFrom.z ) ) { this._x = -vFrom.y; this._y = vFrom.x; this._z = 0; this._w = r; }
  else { this._x = 0; this._y = -vFrom.z; this._z = vFrom.y; this._w = r; }
}
```

일반 캐릭터라면 이게 문제가 된다. 손등이 제멋대로 돌아가기 때문이다. 이 페이지에서는 문제가 되지 않는다. **팔이 캡슐이고 손이 구이기 때문이다.** 회전축 대칭인 형상에는 트위스트가 보이지 않는다.

그러니까 2절의 "프리미티브로 만든 캐릭터"는 미술 선택이 아니라 **엔지니어링 선택**이었다. 리그 형상이 솔버의 미결정 자유도를 흡수하도록 맞춰져 있다. 이 데모에서 가장 잘 짜인 부분을 하나만 꼽으라면 여기다.

## 5. 시간의 단일 출처는 오디오다

가장 중요한 설계 결정은 정작 가장 짧은 줄에 있다.

```js
function tick(now){ last=now; if(playing) time = music.currentTime % LOOP; render(); requestAnimationFrame(tick); }
```

애니메이션 시각이 `performance.now()` 도, 누적 델타도 아닌 **`<audio>` 엘리먼트의 재생 위치**다. 여기서 세 가지가 공짜로 따라온다.

1. **드리프트가 구조적으로 불가능하다.** 음악과 춤이 어긋나려면 시계가 둘이어야 하는데 하나뿐이다.
2. **루프가 저절로 맞는다.** `<audio loop>` 가 붙어 있고 오디오 길이가 정확히 7.2초, `LOOP` 도 7.2다. 오디오가 감기면 애니메이션도 같은 순간에 감긴다.
3. **배속 슬라이더가 한 줄로 끝난다.** `music.playbackRate = 0.5` 만 하면 시계 자체가 느려지므로 애니메이션 쪽은 고칠 게 없다.

대가도 분명하다.

**(가) `currentTime` 은 프레임마다 움직이지 않는다.** MDN 은 이렇게 적는다. *"The value of `currentTime` is an approximation of the current playback position. … The update frequency depends on the browser and media playback pipeline. As a result, successive reads can return the same `currentTime` even when `Date.now()` has advanced."*[^mdncurrent] HTML 명세가 스크립트 실행 중 재생 위치를 안정적으로 유지하도록 요구하기 때문이기도 하다.[^htmlplay] 즉 rAF 가 60번 돌아도 시각은 그보다 성기게 갱신될 수 있고, 그만큼 같은 포즈가 반복 렌더된다. 샘플 정밀도가 필요하면 Web Audio 의 `AudioContext.currentTime` 을 쓰는 쪽이 정석이다.[^mdnactx]

**(나) 오디오가 실패하면 애니메이션도 멈춘다.** `time` 을 움직이는 경로가 그것뿐이라, 재생이 막히면 캐릭터는 정지한 채로 남는다. 흥미로운 흔적이 있다. 파일 어딘가에 이런 줄이 있다.

```js
let time=0, playing=false, speed=1, last=performance.now(), view='front';
```

`last` 는 `tick` 에서 `last=now` 로 대입되기만 하고 **한 번도 읽히지 않는다.** 델타 타임 기반의 독립 시계를 만들려다 오디오 클럭으로 갈아탄 자리가 그대로 남은 것으로 보인다.

**(다) 자동재생 정책.** 오디오가 있는 미디어는 사용자 상호작용 전에는 재생이 막히는 것이 일반적이다.[^mdnautoplay] 이 페이지는 그걸 제대로 처리한다.

```js
try { await music.play(); ... }
catch(error){ playing=false; toggle.textContent='PLAY';
  audioStatus.textContent='음악을 재생하지 못했어요. 재생 버튼을 다시 눌러주세요.'; }
```

`play()` 가 반환하는 프로미스의 거부를 잡아 UI 상태를 되돌리고 한국어로 안내한다. 게다가 `playbackRequest` 카운터로 **오래된 재생 요청의 응답을 무시한다.** 버튼을 빠르게 연타했을 때 늦게 도착한 `await` 가 최신 상태를 덮어쓰는 고전적인 경쟁 상태를, 흔히 빠뜨리는 자리에서 막아 둔 것이다.

## 6. 소스에서 확인되는 거친 자리 넷

칭찬만 하면 분석이 아니다. 아래는 전부 파일에서 직접 확인·측정한 것이다.

### (1) 루프 이음매에서 속도가 튄다

`keys[0]` 과 `keys[63]` 의 값은 **완전히 동일하다.** 위치는 매끄럽게 감긴다($C^0$). 그런데 보간 구간을 고를 때 앞뒤 제어점을 이렇게 집는다.

```js
const p0 = keys[Math.max(0, seg-1)], p3 = keys[Math.min(keys.length-1, seg+2)];
```

`seg=0` 이면 $P_0$ 가 자기 자신으로, `seg=62` 면 $P_3$ 가 마지막 키로 **잘린다.** 3.1절 식을 미분하면

$$P'(0)=\tfrac12\,(P_2-P_0),\qquad P'(1)=\tfrac12\,(P_3-P_1)$$

이므로, 잘린 제어점은 곧 **이음매에서의 접선이 틀어진다**는 뜻이다. 실제로 재 봤다. 손끝 목표의 속도를 수치미분하면

| | 이음매 직전 | 이음매 직후 | 속도 점프 |
| --- | --- | --- | --- |
| 현재 코드 (클램프) | (−0.139, 0.000, −0.063) | (1.136, 1.622, 0.912) | **2.282** |
| 인덱스를 감쌌을 때 | (0.965, 1.577, 0.824) | (1.000, 1.622, 0.851) | **0.063** |

단위는 월드 단위/초다. 루프 중반부의 전형적 속도가 0.05~0.26 수준이니, 2.28은 작지 않다. 그리고 이 점프는 **거의 전부 인덱스 클램프에서 나온다.** `keys[63] === keys[0]` 이므로 주기를 63으로 보고 감싸기만 하면

```js
const n = keys.length - 1;                    // 63 (마지막 키는 첫 키의 사본)
const p0 = keys[(seg - 1 + n) % n], p3 = keys[(seg + 2) % n];
```

점프가 2.282 → 0.063 으로 **약 36배** 줄어든다(남은 0.063은 유한차분 오차와 키 간격이 0.1143/0.1142로 갈리는 반올림 때문이다). 두 줄이다.

### (2) 자기검증이 상수를 보고한다

페이지 맨 끝에는 스스로를 감사하는 코드가 있다. 관절이 벌어지지 않았는지, 어깨 앵커가 밀리지 않았는지를 전 구간에 걸쳐 확인한다. 발상이 좋다.

```js
const audit=[];
for(let i=0;i<1350;i++){ character.pose(i/100); audit.push(...character.inspect()); }
character.pose(time);
window.ryanAudit = { samples:672,
  maxJointGap: Math.max(...audit.map(v=>Math.max(v.upperEndGap, v.foreStartGap, v.wristGap))),
  maxAnchorDrift: Math.max(...audit.map(v=>v.anchorDrift)) };
```

`maxJointGap` 과 `maxAnchorDrift` 는 실제 배열에서 계산된다. 그런데 `samples` 는 **하드코딩된 672**다. 루프는 1350번 돌고 `inspect()` 는 팔 두 개를 반환하므로 배열에는 **2,700개**가 들어간다. 672는 어느 쪽과도 맞지 않는다. 표본 수를 바꿔도 보고되는 숫자는 영원히 672다.

측정값 옆에 붙은 상수는 나중에 거의 반드시 오독된다. 이건 [조용히 실패하는 층]({% post_url 2026-07-31-silent-failure-three-layers %})에서 다룬 것과 같은 계열의 문제다 — 검증 코드가 틀린 게 아니라, **검증 코드가 자기 범위를 거짓으로 보고하는데 아무도 빨간불을 못 본다.** `samples: audit.length` 한 줄이면 끝난다.

덧붙여 이 감사 루프는 `i/100` 로 0→13.49초를 훑는다. 루프가 7.2초이므로 **1.87주기**다. 구간을 고르게 덮으려면 `i/100*LOOP/13.5` 같은 정규화가 필요하거나, 아니면 720회만 돌면 된다. 지금은 앞쪽 0~6.29초 구간만 두 번 측정된다.

### (3) 정교하게 쓴 함수가 호출되지 않는다

```js
// Explicit elbow-pivot solver used by the reference's side-on flap phrase.
// It keeps the upper-arm joint planted while the short forearm swings around it.
function solveElbowWorld(arm, elbowWorld, wristWorld){ ... }
```

주석까지 붙은 15줄짜리 함수인데, 파일 전체에서 `solveElbowWorld` 라는 문자열은 **정의부 딱 한 번** 나온다. 호출되지 않는다. 같은 일을 `pose()` 안에서 `holdWeight` 로 슬러프하는 코드가 대신하고 있다. 5절의 `last` 와 같은 흔적 — 접근을 바꾼 자리가 지워지지 않고 남았다.

### (4) 프레임마다 객체를 버린다

`solve()` 는 모듈 스코프에 스크래치 벡터를 두고 재사용한다. 저자가 이 패턴을 안다는 뜻이다.

```js
const v=new THREE.Vector3(), dir=new THREE.Vector3(), pole=new THREE.Vector3(), ...
```

그런데 같은 파일의 `pose()` 는 그러지 않는다. 세어 보면 `pose()` 한 번에 `new THREE.Vector3` 5개 + `new THREE.Quaternion` 2개 + `.clone()` 2개, 여기에 `solve()` 호출 두 번이 `Vector3` 를 하나씩 더 만든다. **프레임당 11개**, 60fps 면 초당 660개다. 치명적이진 않지만 rAF 루프에서는 GC 압력으로 나타나는 양이고, 무엇보다 **같은 파일 안에서 규칙이 갈린다.**

시작 시점은 더 크다. 감사 루프가 1350회 × (pose 11개 + inspect 12개) ≈ **3만 개 남짓**을 첫 프레임 전에 동기적으로 만들고 버린다.

두 가지가 더 있다. `preserveDrawingBuffer:true` 는 캔버스를 이미지로 캡처할 때만 필요한 옵션인데(브라우저의 버퍼 폐기 최적화를 막는다) 이 페이지에는 캡처 기능이 없다. 그리고 `tick()` 은 `playing` 이 false 여도 매 프레임 `render()` 를 부른다 — `OrbitControls` 의 damping 때문에 완전히 없앨 수는 없지만, 카메라가 멈춘 뒤에도 GPU 는 계속 돈다.

### (덧) 문구와 기능이 어긋난다

우하단 배지는 `FRONT / SIDE / BACK CHARACTER STUDY` 라고 적혀 있다. 시점 버튼은 `front` 와 `side` 둘뿐이다(`for(const name of ['front','side'])`). 사소하지만, 라벨이 기능보다 앞서 나간 자리다.

## 7. 그래서 이 데모가 실제로 증명하는 것

- **춤을 따라 하는 것과 춤을 재현하는 것은 다르다.** 이 페이지는 영상에서 뽑은 궤적(64키)과 손으로 쓴 수식(4Hz 진동·타점 5개·구르기 4회)을 **주파수 대역으로 나눠** 합친다. 순수한 모션 리타기팅도, 순수한 절차적 애니메이션도 아니다.
- **리그와 솔버는 같이 설계해야 한다.** 캡슐 팔·구형 손이라는 형상 선택이 2본 IK 의 미결정 트위스트를 통째로 무효화한다. 형상이 수학의 빈 곳을 메운 사례다.
- **시계를 하나로 만들면 동기화 버그가 사라진다.** 대신 그 시계의 성질(갱신 주기, 실패 모드, 자동재생 정책)을 전부 떠안는다. 이 페이지는 세 번째는 잘 처리했고, 첫 번째와 두 번째는 감수하고 있다.
- **접근을 바꾼 흔적은 코드에 남는다.** 읽히지 않는 `last`, 불리지 않는 `solveElbowWorld`, 갱신되지 않는 `samples:672` 는 전부 "한때 그렇게 하려다 말았다"의 화석이다. 남의 코드를 읽을 때 이 화석들은 **의도의 역사**를 알려주는 가장 값싼 단서다.

가장 고칠 값어치가 큰 것 하나만 고른다면 (1)이다. 두 줄로 루프 이음매의 속도 점프가 36배 줄어든다.

## 8. 근거의 한계

- **측정 범위는 정적 소스 분석이다.** 파일을 받아 코드를 읽고, 오디오를 디코딩해 `ffprobe` 로 재고, 키프레임을 파싱해 보간식을 같은 형태로 다시 구현해 속도를 수치미분했다. **브라우저에서 실행해 프레임을 계측한 것이 아니다.** 6절 (4)의 GC·렌더 비용은 코드에서 세어 나온 객체 수이지, 측정된 프레임 타임이 아니다.
- **"영상을 따라"의 파이프라인은 관측할 수 없다.** 키프레임이 자세 추정(pose estimation)으로 뽑혔는지, 사람이 프레임을 보며 찍었는지는 페이지에 남아 있지 않다. 키 간격이 60fps 의 정수배가 아니라는 점(6.857프레임)과 두 액센트 계열의 BPM 이 어긋난다는 점은 **자동 프레임 정렬이 아니라는 쪽의 정황**이지 증거는 아니다.
- **페이지는 언제든 바뀔 수 있다.** 위 수치는 2026-09-17 에 받은 224,536바이트 버전 기준이다.
- **캐릭터 IP.** 라이언은 카카오의 캐릭터 IP다. 이 페이지는 스스로를 `MOTION STUDY` 로 표기한 습작이고, 이 글은 그 **구현 기법**만을 다룬다. IP 이용의 적법성은 이 글의 판단 범위 밖이다.
- **성능 조언의 성격.** 객체 재사용·`preserveDrawingBuffer`·유휴 시 렌더 생략은 널리 쓰이는 관행이지만, 이 페이지 규모에서 체감 차이가 난다는 뜻은 아니다. 규모가 커질 때 먼저 무너지는 자리라는 의미다.

---

## References

[^rfc4648]: S. Josefsson, *The Base16, Base32, and Base64 Data Encodings*, RFC 4648, IETF, 2006 — §4 Base64. 24비트(3옥텟) 그룹을 6비트씩 4개의 인코딩 문자로 표현한다. <https://www.rfc-editor.org/rfc/rfc4648#section-4> data URL 스킴 자체는 MDN Web Docs, *data: URLs*. <https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data> 본문의 배수는 이 글에서 파일을 직접 디코딩해 잰 값이다.
[^threeobj]: three.js, *Object3D — `.quaternion`* (객체의 로컬 회전). <https://threejs.org/docs/#api/en/core/Object3D.quaternion> 및 *Quaternion.setFromUnitVectors*. <https://threejs.org/docs/#api/en/math/Quaternion.setFromUnitVectors> 본문에 인용한 구현은 페이지가 실제로 고정한 버전인 three.js r160 의 `src/math/Quaternion.js`. <https://github.com/mrdoob/three.js/blob/r160/src/math/Quaternion.js>
[^mdncurrent]: MDN Web Docs, *HTMLMediaElement: currentTime property* — "Time precision" 절. <https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/currentTime>
[^htmlplay]: WHATWG HTML Standard, §4.8.11.8 *Playing the media resource*. <https://html.spec.whatwg.org/multipage/media.html#playing-the-media-resource>
[^mdnactx]: MDN Web Docs, *BaseAudioContext: currentTime property*. <https://developer.mozilla.org/en-US/docs/Web/API/AudioContext/currentTime>
[^mdnautoplay]: MDN Web Docs, *Autoplay guide for media and Web Audio APIs*. <https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay>
