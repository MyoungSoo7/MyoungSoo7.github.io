---
layout: post
title: "TTS 는 돌고, VR 은 서 있고, AR 은 계약뿐이다 — lemuel-xr 세 축의 구현과 남은 것"
date: 2026-08-24 04:51:31 +0900
categories: [software-engineering, xr, architecture]
tags: [WebXR, three.js, TTS, Gemini, Next.js, Kotlin, Unity, R2]
---

앞 글에서는 [lemuel-xr](https://github.com/MyoungSoo7/lemuel-xr) 의 커밋 316개를 훑었다. 이번엔 축을 바꿔서, **TTS · VR · AR 세 가지가 실제로 어떻게 구현돼 있고 무엇이 남았는지**를 코드 기준으로 적는다. 커밋 메시지가 아니라 현재 `main`(`174d84e`)의 파일이 근거다.

먼저 결론부터. 세 축은 완성도가 전혀 다르다.

| 축 | 상태 | 근거 |
| --- | --- | --- |
| **TTS** | 프로덕션에서 실제로 돈다 | 프론트 분할 → 잡 큐 → Gemini → MP3 → 캐시까지 전 구간 구현 |
| **VR** | 웹에서 서 있다 | WebXR `immersive-vr` + three.js 곡면 스크린, 14인물 씬 전부 |
| **AR** | **계약만 있다** | `immersive-ar` 호출 0건. 매니페스트 293개가 없는 에셋 4,052개를 가리킴 |

마지막 줄이 이 글의 핵심이라 미리 적어 둔다. AR 은 "미완성"이 아니라 **아직 시작되지 않았고, 시작된 것처럼 보이는 산출물이 있다.** 그 구분이 완성도 계획의 출발점이다.

---

## 1. TTS — 두 개의 천장 사이에서 잡힌 값들

파이프라인은 이렇다.

```
프론트(splitForTts, 280자)
  → POST /api/tts/synthesize (Kotlin, @Size(max=500))
  → TtsJobQueueAdapter (워커 1개, 유계 큐 8)
  → 사이드카 /synthesize (FastAPI)
  → Gemini TTS → raw PCM → lame 48kbps CBR MP3
  → data:audio/mpeg;base64 인라인 → sha256 캐시
```

### 왜 오디오를 URL 이 아니라 본문에 싣는가

사이드카가 ClusterIP 서비스라 **브라우저가 직접 못 닿는다.** 오브젝트 스토리지를 붙이지 않고 자족적으로 재생하려면 응답 본문에 실어야 한다. 그 대가가 base64 의 +33% 다.

여기서 인코딩 결정이 갈린다. `tts/app.py` 가 근거를 적어 뒀다 — 무압축 WAV 를 그대로 실으면 프로덕션 최장 행(51.5초)이 **3.30MB**, 48kbps CBR MP3 로 구우면 **0.41MB**. 8배다. 인라인 전송에서는 오디오 크기가 곧 전송량이라, 코덱 선택이 UX 결정이 된다.

`lame` 옵션의 `-t`(LAME/Xing 태그 프레임 생략)도 이유가 적혀 있다. 그 프레임이 있으면 파일 크기로 길이를 역산하는 계산이 한 프레임(24ms)만큼 길게 나온다. 재생 진행률이 어긋나는 종류의 버그다.

### 왜 조각 상한이 500 이 아니라 280 인가

이게 이 구현에서 제일 배울 게 많은 지점이다. 백엔드 검증기는 500자를 허용한다. 그런데 **그 앞에 두 번째 천장이 있다** — `tts.timeout-seconds: 300`. 검증을 통과해도 300초 안에 합성이 안 끝나면 백엔드가 다 만들어진 오디오를 버린다.

`splitForTts.ts` 의 실측 기록:

> 한국어 400자 = 오디오 67.7초 = 합성 298.5초(RTF 4.41). 사이드카는 **성공**해서 200 을 돌려줬는데, 백엔드가 1.5초 먼저 타임아웃을 때려 다 만들어진 오디오를 버렸다. **상한 500 은 애초에 도달할 수 없는 값이었다.**

그래서 280 으로 내렸는데, 그 값을 고른 근거 중 두 번째가 특히 실용적이다.

> **캐시가 하나도 안 식는다.** 300 → 280 으로 내려도 나오는 조각 텍스트 15개가 전부 300 일 때 나오던 18개 안에 이미 들어 있다. 새로 식는 항목 0개 — 이 값이 270 이나 260 이 아닌 이유가 이거다.

캐시 키가 `sha256(조각 본문)`이라 **상한을 건드리면 조각 경계가 바뀌고 기존 캐시가 통째로 미스**가 된다. 파라미터 하나가 스토리지 상태를 무효화하는 구조라, "안전하니까 더 내리자"가 공짜가 아니다.

엔진이 Gemini 로 바뀐 뒤 재측정한 값도 같은 파일에 있다 — 280자 34.2초·31.0초, 최악 0.122초/자로 옛 최악(0.865초/자)의 1/7. **그런데 상한을 올리지 않았다.** 이유는 속도가 아니라 위와 같은 캐시다. 여유는 "안전한 방향의 낭비"로 두고, 되찾을 이득(왕복 감소)과 캐시 재굽는 비용을 저울질할 문제로 남겼다.

### 워커 1개는 제약이 아니라 결정

```kotlin
private val executor = ThreadPoolExecutor(1, 1, 0L, MILLISECONDS, queue) { ... }
```

주석이 이유를 적어 뒀다 — 사이드카 파드가 하나뿐이라 동시에 두 건을 밀어넣으면 서로 CPU 를 뺏어 합계 처리량이 그대로거나 더 나빠진다. 직렬화해서 앞의 것부터 확실히 끝내는 편이 낫다는 것.

여기 붙은 디테일 두 개가 실무적이다.

- `inFlight` 를 큐와 **따로** 관리한다. 큐에 담기는 건 `Runnable` 이라 어떤 job 인지 알 수 없고, 워커가 꺼내 *실행 중인* 것은 이미 큐에서 빠져 있다. 큐만 보면 합성 중인 건을 놓치고, 놓치면 그게 곧 중복 합성이다.
- 종료 시 진행 중 한 건을 60초 기다린다. 그 값의 근거가 파드 유예시간이다 — `terminationGracePeriodSeconds: 90` 을 넘기면 kubelet 이 SIGKILL 을 보내므로 그 안쪽이어야 대기에 의미가 있다.

### "초록불인데 전부 실패"를 세 군데서 막는다

사이드카는 두 가지를 **기동 시점에** 확인하고, 없으면 아예 안 뜬다.

```python
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY 가 비어 있다 — ...")
if shutil.which(LAME_BIN) is None:
    raise RuntimeError(f"{LAME_BIN!r} 을 찾을 수 없다 — ...")
```

주석의 표현을 빌리면 *"키 없이 떠 있으면 `/healthz` 는 초록불인데 합성만 전부 실패하는, 가장 알아채기 어려운 상태"* 가 된다. 헬스체크가 거짓말하지 않게 만드는 가장 싼 방법은 거짓말할 수 있는 상태로 뜨지 않는 것이다.

같은 원칙이 런타임에도 세 번 적용된다 — lame 실패를 삼키지 않고(0바이트 캐시 방지), Gemini 가 오디오 대신 텍스트를 주면 명시적으로 실패시키고(`finishReason`·`safetyRatings` 를 붙여서), 실패한 흔적은 캐시에서 지운다. 전부 "재생은 되는데 소리가 없는" 상태를 막기 위한 것이다.

---

## 2. VR — 있는 소재로 거짓말하지 않기

VR 은 Unity 가 아니라 **웹에서** 돈다. `three@0.185` + WebXR 이고, 진입점은 `SceneStage` 컴포넌트다.

### 왜 스카이박스가 아니라 곡면 스크린인가

이 결정 하나가 이 구현의 성격을 다 설명한다. `immersiveStage.ts` 첫 주석:

> 배경 이미지는 1376x768 의 평범한 16:9 렌더다. 360 equirectangular 가 아니다. 이걸 구(sphere) 안쪽에 그대로 입히면 극점에서 뭉개지고 좌우가 이어지지 않아 "고장난 파노라마" 로 보인다. 대신 어두운 공간 한가운데에 넓은 곡면 스크린을 세우면, **있는 소재로 거짓말하지 않으면서도** 고개를 돌릴 이유가 있는 공간이 된다.

360 소재가 없는데 360 인 척하면 품질이 올라가는 게 아니라 **고장으로 읽힌다.** 그래서 반경 6m·수평 110°의 원통 안쪽 면(`THREE.BackSide`)에 이미지를 붙이고, 나머지는 어둠·안개·바닥 그리드·스크린이 떨어뜨리는 빛으로 채운다.

가장자리 처리도 장식이 아니다.

```ts
export function featherAlpha(u: number, v: number, edge = FEATHER): number {
  const f = (t: number) => {
    const x = Math.min(1, Math.max(0, Math.min(t, 1 - t) / edge));
    return x * x * (3 - 2 * x); // smoothstep
  };
  return f(u) * f(v);
}
```

주석의 설명 — *자르지 않고 어둠으로 녹여야 "떠 있는 사각형" 이 아니라 "빛이 있는 공간" 으로 읽힌다.* 고개를 돌리면 그 경계가 바로 보이므로 **착시의 조건**이다. 선형 페이드를 안 쓰는 이유도 적혀 있다 — 페이드가 끝나는 지점에 눈에 띄는 띠가 남는다.

이 계산이 `curvedScreen.ts` 로 따로 떨어져 있는 이유가 또 흥미롭다. 커버리지가 아니라 **무엇이 무엇을 검증하는지 가르기 위해서**다. 숫자 대 숫자는 유닛 테스트가 판정하고, WebGL 배선은 그리는 결과가 판정 대상이라 브라우저가 필요하다. 한 파일에 섞으면 "테스트가 있으니 검증됐다"와 "브라우저에서 봤으니 검증됐다"가 구분되지 않는다.

### WebXR 탐지 — `navigator.xr` 유무로 판단하면 안 된다

```ts
const xr = nav?.xr;
if (!xr || typeof xr.isSessionSupported !== "function") return "unsupported";
try {
  return (await xr.isSessionSupported("immersive-vr")) ? "supported" : "unsupported";
} catch {
  return "unknown"; // SecurityError · NotSupportedError 등
}
```

데스크톱 Chrome 은 헤드셋이 없어도 `navigator.xr` 를 노출한다. 실제로 세션을 열 수 있는지는 [`isSessionSupported()`](https://developer.mozilla.org/en-US/docs/Web/API/XRSystem/isSessionSupported) 만 답한다. 그리고 이 호출은 보안 컨텍스트(https/localhost) 밖에서는 거부되므로 reject 를 흡수해야 한다 — 그래서 불리언이 아니라 `supported / unsupported / **unknown**` 3값이다. 헤드셋 유무를 단정할 수 없는 상태를 상태로 인정하는 쪽이 정직하다.

### 리소스와 게이트 — 이 구현의 진짜 함정 둘

**① three.js 는 GC 로 정리되지 않는다.** `dispose()` 를 안 부르면 WebGL 컨텍스트가 남아 몇 번 드나들면 브라우저가 컨텍스트 한도(보통 16개)에서 렌더를 거부한다. 그래서 `dispose()` 가 지오메트리·머티리얼·텍스처·페더 텍스처·그리드·렌더러·DOM 노드·이벤트 리스너·XR 세션을 전부 되돌린다.

**② 버튼을 감추는 것과 무대를 내리는 것은 다른 일이다.** 예수 미션은 경고가 걸린 씬(겟세마네·십자가)에서 동의 전까지 몰입을 막는다. 그런데 렌더 조건만 끄면 이렇게 된다 — 무대는 살아 있는 채 다음 씬 배경으로 *다시 세워지고*, 동의 카드는 그 아래에만 뜨고, 닫기 버튼은 같은 조건 안에 있어서 함께 사라져 **나올 수도 없다.** 게이트가 막으려던 바로 그 상태(동의 전에 그 장면 *안에* 서 있기)가 된다.

고친 방식이 React 답다. 이펙트가 아니라 **렌더 중 조정**이다.

```tsx
const [gateWas, setGateWas] = useState(immersive);
if (gateWas !== immersive) {
  setGateWas(immersive);
  if (!immersive) setActive(false);
}
```

이펙트로 하면 한 번 그린 다음 되돌리는 꼴이라 경고 씬이 한 프레임 샌다. [React 공식 문서의 "prop 이 바뀔 때 state 조정"](https://react.dev/reference/react/useState#storing-information-from-previous-renders) 패턴이고, `react-hooks/set-state-in-effect` 린트가 정확히 그 실수를 막는다.

한 가지 더 — three.js 는 **사용자가 버튼을 누른 시점에 동적 import** 된다. 첫 페이지 로드 번들에 들어가지 않고, WebGL 이 없는 환경에서는 컴포넌트가 그냥 2D 배경으로 남는다. 몰입 모드는 기본값이 아니라 옵트인이다.

---

## 3. AR — 계약은 완성됐고 실체는 없다

여기가 정직하게 써야 할 부분이다. 저장소 전체에서:

```bash
$ git grep -l "immersive-ar" -- frontend backend content docs | wc -l
0
```

`immersive-ar` 세션 요청도, ARCore/ARKit 도, 평면 탐지 코드도 없다. **AR 런타임은 한 줄도 없다.**

그런데 AR *산출물* 은 많다. 백엔드가 서빙하는 에셋 매니페스트가 **293개**이고, 인물 8명 × 디바이스 3종(quest3 · galaxyxr · visionpro) × 모드 2종(vr · ar) + web 으로 갈라져 있다. AR 매니페스트는 요구 능력까지 선언한다.

```json
"capabilities_min": {
  "passthrough": true, "plane_detection": true, "anchors": true,
  "hand_tracking": true, "spatial_audio": true, "room_scale_min_meters": 2.0
}
```

문제는 그 매니페스트가 가리키는 곳이다. 고유 에셋 URL이 **4,052개**인데 전부 `https://cdn.r2.dev/lemuel-xr/...` 로 시작한다. 그리고 **`cdn.r2.dev` 는 실재한 적 없는 주소다.** Cloudflare R2 의 공개 주소는 `pub-<32자리 해시>.r2.dev` 꼴이고, `cdn.r2.dev` 는 `*.r2.dev` 와일드카드에 걸려 DNS 는 뜨지만 어떤 경로를 넣어도 오류를 준다. 즉 "CDN 이 죽었다"가 아니라 **모델·오디오·텍스처가 어디에도 업로드된 적이 없다.**

저장소가 이 사실을 숨기지는 않는다. `unity-stub/README.md` 가 스스로 적어 뒀다 — *"R2 CDN 에 실 에셋이 아직 없어서 다운로드 단계는 4xx/5xx 가 정상. manifest 수신·파싱·진척 콜백까지가 검증 범위."*

한 가지 더 확인해 둘 것이 있다. 매니페스트의 `size_bytes` 7,400개 중 **5,014개(68%)가 1000 의 배수**다. 실제 파일을 재서 나온 숫자는 이렇게 떨어지지 않는다. **저 크기들은 측정값이 아니라 설계값이다.** 매니페스트를 보고 "9.7MB 짜리 씬"이라고 말하는 순간 근거 없는 수치를 인용하게 된다.

그리고 Unity 쪽 실체는 `unity/README.md`(셋업 안내서)와 `unity-stub/` 의 C# 스크립트 5개가 전부다. Unity 프로젝트 자체가 저장소에 없다.

---

## 4. 완성도를 올리려면 — 순서가 있는 목록

우선순위는 "무엇이 다른 것을 막고 있는가"로 정했다.

### ① 에셋을 실재하게 만든다 (가장 앞, 나머지가 여기 막혀 있다)

버킷을 만들고 실제 파일을 올리고, **매니페스트의 `size_bytes` 와 URL 을 업로드 결과에서 생성**해야 한다. 손으로 적은 숫자를 두면 클라이언트의 진행률·용량 예산이 전부 허구 위에 선다. 파이프라인을 이렇게 뒤집는 게 맞다 — 지금은 *매니페스트가 먼저고 에셋이 없다*. 반대여야 한다: **에셋을 올리면 매니페스트가 그 결과로 생성된다.**

이게 끝나기 전까지 Unity 클라이언트도, AR 도, 아래 ②도 전부 대기 상태다.

### ② 360 소재 → 스카이박스 모드

`immersiveStage.ts` 가 이미 문을 열어 뒀다 — *"실제 360 소재가 생기면 `mode` 를 늘려 스카이박스로 전환하면 된다."* 그리고 웹 매니페스트는 **이미 그 파일 이름을 부르고 있다**: `env_bethlehem_field_sunset.jpg`, `env_ash_heap_night.jpg`, `env_barley_field.jpg` …

즉 "곡면 스크린"은 최종 형태가 아니라 **소재가 없는 동안의 정직한 대체물**이고, 다음 단계가 코드가 아니라 콘텐츠에 막혀 있다는 뜻이다. 완성도를 한 단계 올리는 가장 큰 레버가 여기다.

### ③ AR 은 코드가 아니라 결정이 먼저다

지금 매니페스트는 **Unity 네이티브 전제**로 쓰여 있다(`.cs.bundle`, `.shadergraph.bundle`, `entry_class`). 그런데 실제로 돌고 있는 것은 웹이다. 두 갈래 중 하나를 골라야 한다.

- **웹 WebXR `immersive-ar`** — 지금 서 있는 스택을 그대로 늘린다. `hit-test`·`anchors` 로 평면에 얹는 수준까지는 현실적이고, 배포·검증이 지금 파이프라인 그대로다. 대신 매니페스트의 Unity 전제(스크립트 번들)를 버려야 한다.
- **Unity 네이티브** — 매니페스트가 이미 그 모양이지만, 저장소에 Unity 프로젝트가 없고 빌드·서명·스토어 배포라는 완전히 다른 파이프라인이 생긴다.

결정 전에 AR 코드를 쓰기 시작하면 어느 쪽이든 버리게 된다. **먼저 골라 문서에 박고, 안 고른 쪽의 매니페스트는 지우는 게 맞다** — 남겨 두면 "구현된 것처럼 보이는 산출물"이 계속 계획을 오염시킨다.

### ④ 커버리지 구멍 메우기

씬 이미지는 인물 **14명**(abraham·daniel·david·elijah·esther·jacob·jesus·job·joseph·moses·peter·rahab·ruth·solomon)에 대해 존재하는데, 매니페스트는 **8명**뿐이다. `ruth` 는 VR 매니페스트는 있고 AR 만 없는 비대칭도 있다. 웹 씬은 전원 되지만 XR 배포 대상은 절반이 조금 넘는 상태다.

### ⑤ TTS 에 남은 것

- **간헐 502 의 사유가 아직 미상.** 최근 커밋이 호출자 쪽에 응답 본문을 풀어 로깅하도록 고쳤지만, 그건 *다음 실패부터 알 수 있게* 만든 것이지 원인을 고친 게 아니다.
- **목소리 3종 중 2종이 미검증.** 소스 주석이 그대로 적어 뒀다 — 사람이 귀로 듣고 고른 건 `narrator-male-low`(Charon) 하나뿐이고, 나머지 둘은 문서상 성격만 보고 고른 값이라 쓰기 전에 들어봐야 한다.
- **`speakingRate` 는 무시된다.** Gemini TTS 에 속도 파라미터가 없어서다. 필요해지면 ffmpeg `atempo` 후처리로 붙여야 한다.
- **preview 모델 의존.** `gemini-3.1-flash-tts-preview` 는 예고 없이 사라질 수 있다. env 로 뽑아 둔 건 옳은 대비지만, 사라졌을 때 *무엇이 어떻게 실패하는지* 는 아직 겪어 보지 않았다.
- **워커 1개**는 지금은 옳지만 CPU 합성 시절의 근거다. 엔진이 원격 API 로 바뀌어 로컬 CPU 를 안 쓰는 지금, 병렬화의 제약은 CPU 가 아니라 **API 할당량**으로 옮겨 갔다. 늘릴 거면 그 축으로 다시 계산해야 한다.

### ⑥ 브라우저에서만 판정되는 층

three.js 배선은 `three` 를 대역으로 갈아끼운 유닛 테스트로 검증한다 — 무엇을 몇 번 `dispose` 하는가, XR 세션에 무엇을 요청하는가. **실제로 그려지는지는 그 테스트가 답하지 않는다.** 저장소가 이 한계를 주석에 명시해 둔 건 좋지만, 명시가 곧 검증은 아니다. 헤드셋 실기 확인이나 WebGL 스크린샷 비교가 붙기 전까지 이 층의 "초록불"은 배선이 초록이라는 뜻일 뿐이다.

---

## 5. 세 축이 공유하는 하나의 규율

따로 만들어졌는데 같은 원칙이 반복된다. **없는 것을 있는 것처럼 렌더링하지 않는다.**

- TTS 는 키나 인코더가 없으면 **뜨지 않는다.** 초록불 헬스체크로 거짓말하느니 죽는다.
- VR 은 360 소재가 없으니 **360 인 척하지 않고** 곡면 스크린으로 간다.
- WebXR 탐지는 단정할 수 없을 때 `unknown` 을 반환한다. 불리언으로 뭉개지 않는다.

그리고 이 규율이 딱 한 곳에서 깨져 있다. **매니페스트 293개가 존재하지 않는 에셋 4,052개를 실재하는 것처럼 선언하고, 크기까지 적어 뒀다.** 세 축 중 AR 만 미완성인 것은 우연이 아니라, 그 축에서만 "산출물이 진척을 대신 증명"하고 있었기 때문이다.

완성도를 올리는 작업의 절반은 새 코드를 쓰는 일이고, 나머지 절반은 **이미 있는 산출물이 무엇을 증명하고 무엇을 증명하지 않는지 다시 표시하는 일**이다.

## References

1차 출처 — lemuel-xr 저장소 (공개, `main` = `174d84e` 기준):

- 저장소 — <https://github.com/MyoungSoo7/lemuel-xr>
- [`tts/app.py`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/tts/app.py) — Gemini TTS 사이드카, MP3 인코딩 근거, 기동 시 실패 정책
- [`frontend/src/lib/tts/splitForTts.ts`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/frontend/src/lib/tts/splitForTts.ts) — 280자 상한과 두 번째 천장(timeout) 실측
- [`backend/.../TtsJobQueueAdapter.kt`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/backend/src/main/kotlin/github/lms/lemuel/xr/tts/adapter/out/worker/TtsJobQueueAdapter.kt) — 워커 1개 · `inFlight` · 드레인 60초
- [`frontend/src/lib/xr/immersiveStage.ts`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/frontend/src/lib/xr/immersiveStage.ts) — three.js 무대 배선과 `dispose`
- [`frontend/src/lib/xr/curvedScreen.ts`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/frontend/src/lib/xr/curvedScreen.ts) — 곡면 치수 · smoothstep 페더
- [`frontend/src/lib/xr/xrSupport.ts`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/frontend/src/lib/xr/xrSupport.ts) — 3값 WebXR 탐지
- [`frontend/src/components/SceneStage.tsx`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/frontend/src/components/SceneStage.tsx) — 동적 import · 동의 게이트 · 렌더 중 조정
- [`unity-stub/README.md`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/unity-stub/README.md) — "다운로드 단계는 4xx/5xx 가 정상"
- [`unity/README.md`](https://github.com/MyoungSoo7/lemuel-xr/blob/main/unity/README.md) — Unity 셋업 안내(프로젝트 미포함)

공식 문서:

- MDN — `XRSystem.isSessionSupported()` — <https://developer.mozilla.org/en-US/docs/Web/API/XRSystem/isSessionSupported>
- W3C — WebXR Device API — <https://www.w3.org/TR/webxr/>
- three.js — WebXR — <https://threejs.org/docs/#manual/en/introduction/How-to-create-VR-content>
- React — `useState` / 이전 렌더 정보로 state 조정 — <https://react.dev/reference/react/useState#storing-information-from-previous-renders>
- Gemini API — Speech generation — <https://ai.google.dev/gemini-api/docs/speech-generation>
- Cloudflare R2 — Public buckets (`pub-<hash>.r2.dev`) — <https://developers.cloudflare.com/r2/buckets/public-buckets/>

재현 명령:

```bash
git clone https://github.com/MyoungSoo7/lemuel-xr && cd lemuel-xr
git grep -l "immersive-ar" -- frontend backend content docs | wc -l   # → 0
git ls-files backend/src/main/resources/manifests | wc -l      # → 293
git grep -ho 'https://cdn.r2.dev[^"]*' -- backend/src/main/resources/manifests \
  | sort -u | wc -l                                            # → 4052
git grep -h '"size_bytes"' -- backend/src/main/resources/manifests \
  | grep -oE '[0-9]+' | awk '$1%1000==0' | wc -l               # → 5014 / 7400
```

*수치는 2026-08-24 `main`(`174d84e`) 기준이다.*
