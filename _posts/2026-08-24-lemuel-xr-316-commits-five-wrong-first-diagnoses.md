---
layout: post
title: "커밋 316개를 다시 읽었다 — lemuel-xr 3개월, 첫 진단이 틀렸던 다섯 번"
date: 2026-08-24 04:30:22 +0900
categories: [software-engineering, architecture, retrospective]
tags:
  [
    Kotlin,
    Spring Boot,
    WebClient,
    TTS,
    Mutation Testing,
    Git,
    Debugging,
  ]
---

[lemuel-xr](https://github.com/MyoungSoo7/lemuel-xr) 저장소가 한 매듭을 지었다. 기념으로 커밋 로그를 처음부터 끝까지 다시 읽었는데, 기능이 늘어난 기록보다 **첫 진단이 틀렸다가 뒤집힌 기록**이 훨씬 많았다. 이 글은 그 뒤집힌 지점만 모은 것이다.

이 저장소는 공개돼 있어서 아래 모든 수치는 커밋 해시로 직접 확인할 수 있다. 인용한 숫자는 전부 커밋 본문이나 `git` 출력에서 왔고, 재현 명령을 같이 적었다.

## 0. 규모 — 실측

```bash
$ git rev-list --count origin/main
316
$ git log origin/main --format='%s' \
    | sed -E 's/^([a-z]+)(\(.*\))?:.*/\1/' | sort | uniq -c | sort -rn | head -3
 103 fix
 100 feat
  37 docs
```

- 첫 커밋 [`393f4d1`](https://github.com/MyoungSoo7/lemuel-xr/commit/393f4d1) — 2026-05-20
- 마지막 커밋 [`174d84e`](https://github.com/MyoungSoo7/lemuel-xr/commit/174d84e) — 2026-08-24 (PR #141)
- 추적 파일 1,538개 — `.kt` 429 · `.ts/.tsx` 133 · `.md` 115 · `.py` 39

첫 줄부터 눈에 걸리는 건 **`fix`(103)가 `feat`(100)보다 많다**는 것이다. 97일 중 실제로 커밋이 있는 날은 **35일**이고, 2026-06-04 [`ed6a33e`](https://github.com/MyoungSoo7/lemuel-xr/commit/ed6a33e) 이후 2026-07-11 까지 **5주 넘게 커밋이 한 줄도 없다.** 회고 글이 흔히 감추는 쪽이라 먼저 적어 둔다.

fix 가 feat 보다 많은 저장소는 두 가지 중 하나다. 만든 것이 자꾸 깨지거나, **깨진 것을 찾아내는 층이 실제로 작동하거나.** 아래는 후자를 주장하려는 게 아니라, 그 둘을 어떻게 구분했는지에 대한 기록이다.

---

## 1. 설계 결정이 이틀 만에 두 번 뒤집혔다

첫 스택은 Spring Boot 4 + JDK 25 였다. 그런데 같은 날 [`f308ab0`](https://github.com/MyoungSoo7/lemuel-xr/commit/f308ab0) 에서 이렇게 내려간다.

> `fix(backend): Spring Boot 4 → 3.5.4 다운그레이드 (Spring AI 1.0 호환). JDK 25 → 21 동기화`

Spring AI 1.0 을 쓰려고 프레임워크 메이저 버전을 통째로 내린 것이다. 그리고 몇 시간 뒤 [`da89e29`](https://github.com/MyoungSoo7/lemuel-xr/commit/da89e29) 에서 다시 올라온다.

> `refactor: AI 로직을 Python 사이드카로 분리 — Spring AI 제거, SB4 + JDK25 복귀`

커밋 본문이 이유를 적어 뒀다. Spring AI 1.0 GA 가 Boot 4 와 비호환(`RestClientAutoConfiguration` 경로 변경)이었고, 애초 기획서에도 AI 오케스트레이션은 Python 으로 적혀 있었다는 것.

여기서 배울 점은 "사이드카가 옳다" 가 아니다. **한 라이브러리 하나가 프레임워크 메이저 버전을 인질로 잡았을 때, 내려가는 대신 그 라이브러리를 프로세스 밖으로 밀어낼 수 있는지 먼저 보라**는 것이다. 결과적으로 백엔드는 Boot 4.0.4 + Kotlin 2.2.20 + JDK 25 툴체인으로 남았고([`build.gradle.kts`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/backend/build.gradle.kts)), AI 코드는 모델 교체와 평가를 독립 주기로 굴릴 수 있게 됐다. 두 달 뒤 TTS 엔진을 통째로 갈아치울 때 그 분리가 실제로 값을 했다(§3).

덧붙여 2026-07-16 [`f047f52`](https://github.com/MyoungSoo7/lemuel-xr/commit/f047f52) 에서 백엔드가 Java 0% / Kotlin 100% 로 전환된다. 지금 `.kt` 429개가 그 결과다.

---

## 2. 오진 ①: "사이드카가 죽었다" — 사이드카는 200 을 주고 있었다

프로덕션에서 나레이션 오디오가 **한 번도** 재생된 적이 없었다. 증상은 백엔드의 502 뿐이었다.

[`d7844e1`](https://github.com/MyoungSoo7/lemuel-xr/commit/d7844e1) 이 그 실제 예외를 남겨 뒀다.

```
POST /api/tts/synthesize → 502 E_TTS_UPSTREAM_FAIL
detail: 200 OK from POST http://lemuel-xr-tts:5002/synthesize,
  but response failed with cause: DataBufferLimitException:
  Exceeded limit on max bytes to buffer : 262144
```

읽어야 할 곳은 `200 OK ... but response failed` 다. **업스트림은 성공했고, 그 응답을 받는 쪽의 디코더가 터졌다.** 사이드카가 오디오를 base64 data URL 로 인라인해 돌려주는데, 커밋 본문의 실측으로 5.7초짜리 한 문장이 WAV 268KB → base64 357KB 였다. Spring 의 `WebClient` 는 인메모리 코덱 버퍼 기본값이 **256KB**다 — [Spring Framework 레퍼런스](https://docs.spring.io/spring-framework/reference/web/webflux-webclient/client-builder.html)가 `maxInMemorySize` 항목에서 그 기본값을 명시한다. 262144 는 그 숫자다.

이 고장의 고약한 점은 **어느 로그에도 안 남는다**는 것이다.

- 사이드카 로그: 200 성공만 기록
- 프론트: 오디오 실패를 의도적으로 조용히 삼킴(graceful degradation)
- 캐시: 저장 단계까지 못 가서, 같은 문장을 매번 25초 들여 재합성한 뒤 다시 실패

그리고 **테스트가 이걸 못 잡은 이유가 본질적이다.** 커밋 본문이 그대로 적어 뒀다 — 스텁 응답이 전부 수백 바이트라 한도를 건드린 적이 없었다. 그래서 고칠 때 400KB 응답을 받는 회귀 테스트와, *한도만 옛 기본값으로 되돌리면 실제로 실패하는* 대조군 테스트를 함께 넣었다. 뒤쪽이 중요하다. 대조군이 없으면 그 테스트가 정말 그 결함을 재는지 알 수 없다.

같은 커밋이 LLM 사이드카에도 같은 지뢰가 있었음을 적고 함께 고친다("`ai.max-response-bytes` 기본 4MiB — LLM 사이드카도 같은 지뢰를 밟고 있었다"). 한 곳에서 찾은 결함을 같은 모양의 다른 곳에서 찾아보는 것은 거의 항상 남는 장사다.

---

## 3. 오진 ②: 잡음의 원인은 전처리가 아니라 엔진이었다

낭독 중간에 사람 말이 아닌 소리가 섞였다. 첫 지목은 한국어 발음형 전처리(경음화)였고, 실제로 그쪽을 고치는 커밋이 연달아 나간다 — [`9f250dd`](https://github.com/MyoungSoo7/lemuel-xr/commit/9f250dd)(철자 대신 발음으로), [`130ddef`](https://github.com/MyoungSoo7/lemuel-xr/commit/130ddef)(화자가 DB 슬러그를 읽고 있던 것), [`6126c92`](https://github.com/MyoungSoo7/lemuel-xr/commit/6126c92)(경음화 제거).

그리고 [`8037524`](https://github.com/MyoungSoo7/lemuel-xr/commit/8037524) 이 그 방향 전체를 접는다.

> 처음에는 발음형 전처리(경음화)를 원인으로 지목했지만 **오진이었다.** 전처리를 아예 거치지 않은 원문도 똑같이 무너진다 — 대조군을 만들어 재 보고서야 알았다.

무음으로 잘라 구간 길이를 잰 표가 커밋 본문에 그대로 있다(154자, 정상 낭독이면 약 28초):

| 변형 | 총 길이 | 최장 연속 구간 | (해당 문구의 정상 길이) |
| --- | --- | --- | --- |
| 원문 그대로 | 46.7s | 6.54s | ~1.9s |
| 발음형(경음화 포함) | 39.9s | 5.05s | ~4.1s |
| 발음형(경음화 제거) | 51.3s | 7.59s | ~4.5s |
| Gemini 3.1 | 31.3s | 1.35s | — |

어떤 입력을 줘도 XTTS-v2 는 글에 없는 소리를 만들어냈다. **전처리로 고칠 수 있는 종류의 고장이 아니었다.**

엔진을 [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation) 로 바꾸면서 딸려 나온 것들이 이 결정의 실제 크기를 보여준다.

- `korean_g2p` **삭제**. Gemini 는 한국어를 아는 모델이라 철자를 그대로 주면 된다. 발음형을 주면 오히려 "애구베서" 라고 읽는다. 그 전처리는 XTTS 가 한글을 기계적으로 로마자로 옮기는 것에 대한 *우회*였을 뿐이라, 엔진과 함께 존재 이유가 사라졌다.
- `torch`·`TTS`·`transformers` 가 빠지며 이미지가 약 2GB → 수십 MB, 기동 시 수 분짜리 모델 로딩이 사라짐.
- Coqui 모델 다운로드 장애를 피하려고 "마지막 정상 이미지를 물려쓰던" Dockerfile 우회([`af681a3`](https://github.com/MyoungSoo7/lemuel-xr/commit/af681a3), [`fe09f84`](https://github.com/MyoungSoo7/lemuel-xr/commit/fe09f84))도 함께 폐기.

여기서 눈여겨볼 것은 **버려진 코드의 정체**다. `korean_g2p`, 로마자 우회, 이미지 물려쓰기 Dockerfile, 재시도 4회 — 전부 *틀린 진단 위에 쌓인 정교한 구조물*이었다. 오진은 코드를 안 만드는 게 아니라, 오히려 많이 만든다. 그래서 오진의 비용은 "고치는 데 걸린 시간" 이 아니라 **그 위에 쌓인 것들의 총량**이다.

한 가지 더. 이 뒤집기가 가능했던 건 §1 에서 AI/TTS 를 프로세스 밖으로 밀어냈기 때문이다. 엔진 교체가 백엔드 도메인 코드를 건드리지 않았다.

---

## 4. 오진 ③: 중단된 측정이 제외 사유로 굳어 있었다

이 저장소는 문서와 시나리오를 기계로 재는 게이트 러너를 두고, **그 판정기 자체를 돌연변이로 다시 잰다**(코드를 일부러 망가뜨렸을 때 판정기가 빨간불을 내는지 확인). 그런데 그 돌연변이 러너 4종이 CI 밖에 있었다.

제외 사유는 이렇게 적혀 있었다 — *"`mutate_ac_table` 이 20분을 넘겨도 안 끝나 측정을 중단했다"* (2026-08-11).

[`be40b64`](https://github.com/MyoungSoo7/lemuel-xr/commit/be40b64) 가 그걸 다시 잰다.

> 2026-08-15 에 끝까지 돌려 다시 쟀다 — 4종 합계 **247초**, 전부 rc=0. 20분이 아니라 4분이다. **중단한 측정이 제외 사유로 굳어 있었다.**

이게 왜 위험한지도 같은 커밋이 적어 뒀다. 이 층이 없는 동안 CI 는 판정기의 *결과*만 지켰다. 기준선 비교 잡(`gate-baseline`)은 기록된 기준선과의 일치를 보므로 **판정 로직을 통째로 들어내도 초록이다.**

같은 커밋이 두 번째 구멍도 닫는다. `BLOCKED`(통과도 실패도 아닌 세 번째 값)로 비워 둔 옛 판 수치 6건인데, "재현은 안 되지만 **대조는 된다**" 는 관찰로 축을 하나 새로 만든다 — rev.N 의 기록이라고 적은 수치는 rev.N 을 선언한 커밋 본문에 실재해야 하고, 그것을 `git` 으로 확인한다. 결과는 `PASS 35 / FAIL 1 / BLOCKED 7` → `PASS 41 / FAIL 1 / BLOCKED 1`.

이 두 건의 공통점은 **"측정했다"고 적힌 문장이 실제로는 측정이 아니었다**는 것이다. 하나는 중단된 측정, 하나는 빈칸. 둘 다 문서상으로는 근거가 있는 것처럼 보였다.

사흘 뒤 [`b2d1aa6`](https://github.com/MyoungSoo7/lemuel-xr/commit/b2d1aa6) 의 제목이 그 교훈을 한 줄로 남긴다 — *"사람이 기억해야 도는 검사는 돌지 않는다."*

---

## 5. 오진 ④: 정통 명제를 이단 표본과 함께 자르고 있었다

이 앱은 종교 텍스트를 다루므로 위험 표현을 거르는 층이 있다. 그 층의 임계치를 아무리 옮겨도 안 걸리는 표본 5건이 남았고, 첫 반응은 "임계치를 더 조이자" 였다. [`e013225`](https://github.com/MyoungSoo7/lemuel-xr/commit/e013225) 가 그게 왜 틀린 방향인지 적어 뒀다.

> 그중 셋은 **명제 자체가 정통**이다(약 1:6-7 · 살전 5:18 · 시 88:18). (…) 이들은 실제로 근거하므로 임계치를 어떻게 옮겨도 안 갈린다 — **조이면 정통 묵상이 잘린다.**

저장소의 [`CLAUDE.md`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/CLAUDE.md) 가 그 구분을 표로 못박아 뒀다. "고난은 연단이다"(롬 5:3-4)는 정통 명제다. 거절 사유는 그 명제가 아니라 **회피(치료·휴식·상담)에 위협 조건을 붙인 구조**다. 그래서 임계치가 아니라 축을 새로 열었다 — 어휘가 아니라 두 어휘군을 잇는 **통사 결합**을 보는 층. 관계 6종(귀책 · 위협 조건 · 통로 폐쇄 · 애도 박탈 · 비교 축소 · 공로 환산)은 발명한 게 아니라, 사람이 라벨을 확정하며 적어 둔 근거 서술에서 그대로 뽑았다.

그런데 이 커밋의 진짜 수확은 따로 있다. **골든셋이 라벨을 인칭으로 새고 있었다.**

> 위험 표본 15건 중 12건에 "네/너" 가 있고 정통 표본 12건엔 0건이라, **"네" 한 글자짜리 정규식이 recall 0.800 · 오탐 0.000 을 낸다.**

한 글자 정규식이 분류기 성능을 낸다면, 그 데이터셋으로 잰 어떤 점수도 믿을 수 없다. 위험한 문장과 안전한 문장이 *위험해서*가 아니라 *2인칭으로 쓰여서* 갈리고 있었기 때문이다. 그래서 인칭 표지를 판정 입력에서 아예 빼고, 1인칭으로 치환한 절제 실험으로 확인했다 — 인칭 검출기는 0.000 으로 무너지고 새 층은 1.000 을 유지한다.

같은 커밋이 자기 성적의 한계도 같이 적었다. 규칙 어휘를 만들 때 저자가 표본 27건을 전부 읽었으므로 **홀드아웃도 오염돼 있고, 저 1.000 은 인샘플 상한**이라는 것. 그리고 이 층은 아직 차단이 아니라 기록만 하는 섀도우로 붙어 있다. 오염되지 않은 오탐률을 재기 전에 차단 정책을 만들지 않기 위해서다.

일반화하면 이렇다. **필터의 점수를 "잡은 것"으로만 보고하면, 잘못 자른 것도 데이터셋이 새는 것도 영원히 안 보인다.** 종교 텍스트만의 문제가 아니라 모든 분류기 게이트의 문제다.

---

## 6. 오진 ⑤: 충돌이 안 났는데 코드가 사라졌다 (그저께)

가장 최근 것이라 아직 뜨겁다. 두 PR 이 각각 초록불로 머지됐는데 **합쳐진 `main` 만 빨간불**이 됐다.

```
src/lib/hooks/useTtsNarration.ts(197,32):
  error TS2304: Cannot find name 'UNAVAILABLE_AFTER_FAILURES'
```

원인: 두 브랜치가 같은 파일의 **같은 앵커 바로 뒤**(상단 상수 블록의 같은 줄 아래)에 각각 새 상수를 끼워 넣었다. 겹치는 줄을 *고친* 게 아니라 *추가*한 것이라 git 은 이걸 충돌로 보지 않고 자동 병합했고, 그 결과에서 한쪽 **선언만 사라지고 사용처는 남았다.** [`5a59365`](https://github.com/MyoungSoo7/lemuel-xr/commit/5a59365) 가 그 선언을 되살린다.

여기서 무너지는 통념이 있다. **"내 PR 이 초록이면 됐다" 가 성립하지 않는다.** 각 PR 은 자기 브랜치에서 정직하게 초록이었다. 빨간불은 합쳐진 뒤에만 존재했고, 손으로 풀 기회(충돌 마커)조차 주어지지 않았다.

병렬 작업에서 이걸 사후에 잡는 그물은 두 개다.

1. **머지 뒤 `main` 의 CI 를 한 번 더 본다.** 실제로 이번에도 그게 유일한 발견 경로였다.
2. 남이 같은 파일을 건드린 정황이 보이면 파일별로 대조한다.

```bash
$ git diff <내커밋> origin/main -- <파일> | grep -c '^-[^-]'
```

0 이 아니면 그 줄이 남의 의도인지 내 유실인지 확인한다. 이번 건은 이 명령으로 나머지 5개 파일에 유실이 없음을 확인했다.

---

## 7. 다섯 번의 공통점

시간 순서도 영역도 다른데, 오진을 끝낸 방법은 매번 같은 모양이었다.

| # | 첫 진단 | 실제 | 무엇이 뒤집었나 |
| --- | --- | --- | --- |
| ① | 사이드카가 죽었다 | 호출자의 디코더 한도 | 예외 메시지를 끝까지 읽음(`200 OK ... but`) |
| ② | 전처리가 잡음을 만든다 | 엔진이 만든다 | **대조군** — 전처리 없는 원문도 무너짐 |
| ③ | 그 검사는 20분 넘게 걸린다 | 4분 | **재측정** — 중단된 측정을 끝까지 돌림 |
| ④ | 임계치를 더 조이면 된다 | 명제가 아니라 강제 구조, 게다가 데이터가 샘 | 한 글자 정규식으로 대조 · 인칭 절제 실험 |
| ⑤ | 각 PR 이 초록이니 안전 | 병합 결과만 빨강 | 머지 *뒤* `main` 을 다시 봄 |

②③⑤ 는 특히 같은 문장으로 요약된다. **"이미 확인했다"고 적혀 있는 것을 한 번 더 실행한 것.** 코드가 아니라 *기록*을 의심한 경우다.

그리고 ①②④ 는 전부 **잘못 잡은 자리에 이미 코드가 쌓여 있었다.** 정교한 우회, 새 전처리 모듈, 튜닝된 규칙 — 오진의 진짜 비용은 여기 있다.

---

## 8. 아직 안 끝난 것 — 정직하게

회고 글이 초록불로 끝나면 대개 뭔가 감춘 것이다. 지금 열려 있는 것을 적는다.

- **§2 의 502 는 지금도 간헐적으로 난다.** 지난 48시간 사이드카 로그에 2건 있었고, 같은 시간대에 200 이 계속 찍히니 키 만료나 할당량 소진은 아니다. 그런데 **사유를 모른다** — 사이드카가 실패 이유를 응답 본문에만 넣고 자기 로그에는 안 남기고, 호출자는 상태줄만 찍었기 때문이다. 최근 커밋 [`748914d`](https://github.com/MyoungSoo7/lemuel-xr/commit/748914d) 이 호출자 쪽 절반(응답 본문을 풀어서 로깅, 비밀값은 마스킹)을 고쳤다. 즉 **다음 502 부터 알 수 있게 만든 것이지, 원인을 고친 게 아니다.**
- 게이트 하나는 아직 임계치를 못 넘겨 차단이 아니라 **기록만 하는 섀도우 모드**로 붙어 있다([`9655b9a`](https://github.com/MyoungSoo7/lemuel-xr/commit/9655b9a)). 통과시킬 근거가 아직 없다는 뜻이고, 초록으로 만들려고 임계치를 내리지 않았다.
- 검토 사인오프를 한 사람이 한다. 독립성이 이름만 남는 구조라는 걸 기록에 남겨 뒀다.

---

## 결론

316개 커밋에서 배운 게 하나라면, 오진은 **틀린 곳을 고치는 일**이 아니라 **틀린 곳에 무언가를 쌓는 일**이라는 것이다. 전처리 모듈, Dockerfile 우회, 재시도 로직, 튜닝된 규칙 — 삭제 커밋이 그 목록이다.

그리고 그것을 끝낸 것은 매번 새 통찰이 아니라, **이미 확인했다고 적힌 것을 한 번 더 실행한 것**이었다. 대조군을 만들고, 중단한 측정을 끝까지 돌리고, 머지된 뒤의 `main` 을 다시 보는 일. 전부 지루한 쪽이다.

## References

1차 출처 — lemuel-xr 저장소 (공개, 인용한 수치는 각 커밋 본문에서 확인 가능):

- 저장소 — <https://github.com/MyoungSoo7/lemuel-xr>
- [`da89e29`](https://github.com/MyoungSoo7/lemuel-xr/commit/da89e29) AI 사이드카 분리 · Spring AI 제거 · SB4/JDK25 복귀
- [`f047f52`](https://github.com/MyoungSoo7/lemuel-xr/commit/f047f52) 헥사고날 + Java→Kotlin 100% 전환
- [`d7844e1`](https://github.com/MyoungSoo7/lemuel-xr/commit/d7844e1) WebClient 256KB 버퍼 — 실측 수치와 회귀·대조군 테스트
- [`8037524`](https://github.com/MyoungSoo7/lemuel-xr/commit/8037524) XTTS-v2 → Gemini TTS — 무음 분할 구간 길이 대조표
- [`be40b64`](https://github.com/MyoungSoo7/lemuel-xr/commit/be40b64) 돌연변이 러너 CI 편입 — 247초 재측정
- [`b2d1aa6`](https://github.com/MyoungSoo7/lemuel-xr/commit/b2d1aa6) 게이트 러너 자체 테스트를 CI 에
- [`e013225`](https://github.com/MyoungSoo7/lemuel-xr/commit/e013225) 강제 구조 분류기 — 인칭 누출 발견과 절제 실험
- [`9655b9a`](https://github.com/MyoungSoo7/lemuel-xr/commit/9655b9a) 섀도우 게이트(판정만 기록, 차단 없음)
- [`CLAUDE.md`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/CLAUDE.md) — 정통 명제 / 거절 근거 구분표
- [`5a59365`](https://github.com/MyoungSoo7/lemuel-xr/commit/5a59365) 병합이 삼킨 상수 복원
- [`748914d`](https://github.com/MyoungSoo7/lemuel-xr/commit/748914d) 사이드카 실패 사유 로깅 + 실패 1회로 죽지 않게

공식 문서:

- Spring Framework Reference — *WebClient / Codecs* (`maxInMemorySize` 기본 256KB) — <https://docs.spring.io/spring-framework/reference/web/webflux-webclient/client-builder.html>
- Spring Boot Documentation — <https://docs.spring.io/spring-boot/index.html>
- Kotlin 2.2.20 What's new — <https://kotlinlang.org/docs/whatsnew2220.html>
- Gemini API — *Speech generation (text-to-speech)* — <https://ai.google.dev/gemini-api/docs/speech-generation>
- React — `useState` (렌더 중 state 조정 패턴) — <https://react.dev/reference/react/useState>

재현 명령:

```bash
git clone https://github.com/MyoungSoo7/lemuel-xr && cd lemuel-xr
git rev-list --count origin/main
git log origin/main --format='%s' \
  | sed -E 's/^([a-z]+)(\(.*\))?:.*/\1/' | sort | uniq -c | sort -rn
git log -1 --format='%s%n%n%b' 8037524   # §3 대조표
git log -1 --format='%s%n%n%b' be40b64   # §4 재측정
```

*이 글의 수치는 2026-08-24 기준 `origin/main`(`174d84e`)에서 측정했다. 이후 커밋으로 달라질 수 있다.*
