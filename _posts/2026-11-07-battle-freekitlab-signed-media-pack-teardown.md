---
layout: post
title: "브라우저에 2GB를 서명해서 내려받는 게임 — battle.freekitlab.com 공개 파일 뜯어보기"
date: 2026-11-07 13:26:35 +0900
categories: [web, architecture]
tags: [service-worker, cache-api, webcrypto, webview, oauth, web-game, teardown]
---

[군사의 고뇌](https://battle.freekitlab.com/)는 삼국지를 소재로 한 웹 전략 게임이다. [개인정보처리방침](https://battle.freekitlab.com/legal/privacy.html)과 [이용약관](https://battle.freekitlab.com/legal/2026-11-05-apple.html)에 적힌 운영사는 주식회사 프리키친랩이고, 두 문서의 시행일은 2026년 11월 5일이다. 상위 도메인 [freekitlab.com](https://freekitlab.com/)은 소상공인용 로봇·자동화 솔루션을 소개하는 회사 사이트다.

공개된 파일을 읽다가 가장 눈에 띈 것은 게임 규칙이 아니라 배포 방식이었다. **로그인 전에 받을 수 있는 공개 파일만 봐도, 이 게임은 2.05GB짜리 미디어 묶음을 브라우저 안에 설치하고 조각마다 해시를 검증한다.** 네이티브 앱의 설치 패키지가 하는 일을 웹 표준 API로 다시 만든 셈이다.

## 조사 범위와 한계

먼저 이 글이 볼 수 없었던 것부터 적는다.

- **가입하지 않았고 게임을 플레이하지 않았다.** 가입에는 약관 동의와 만 18세 이상 확인이 필요하다. 비로그인 상태에서 `/lobby`, `/single`은 303으로 넘어간다. 그래서 전투의 실제 감각, 서버 코드, 동시 접속자 수는 관측하지 못했다.
- **공개 클라이언트 파일과 응답 헤더만 읽었다.** 측정 시각은 2026-11-07 13시경(KST)이고, 인증을 우회하거나 API를 탐침하지 않았다.
- **APK는 내려받아 구조만 확인했고 실행하지 않았다.**
- **제3자 리뷰를 찾지 못했다.** 검색에서 독립적인 리뷰나 보도가 나오지 않아, 게임의 평판이나 완성도는 평가하지 않는다.
- 아래 구조 분석은 코드를 읽고 추론한 것이다. 코드에 그렇게 적혀 있어도 운영 환경에서 항상 그렇게 동작한다는 보증은 아니다.

## 공개 데이터로 본 게임

플레이어는 군주가 아니라 **군사(軍師)** 다. 유비·조조·손권·동탁·원소 다섯 세력에 장수가 5명씩, 모두 25명이 있고 장수마다 고유 기술을 가진다. 군사는 통솔·무력·지력·정치·매력 다섯 능력치를 가지며, 기본 합계 420에 보너스 50을 나눠 만든다.

전투 수치는 클라이언트의 밸런스 표에 있다. 표의 주석은 "2026-11-04 officer balance patch" 이후 값이라고 밝힌다. 공개 표에서 대조한 몇 줄은 다음과 같다.

| 장수 | 공격 | HP | 사거리 | 기술 | 효과(공개 가이드 기준) |
| --- | ---: | ---: | ---: | --- | --- |
| 여포 | 1750 | 9600 | 165 | 천하무쌍 | 야외 일반병 타격 시 주변 120 이내 다른 일반병 최대 2부대에 35% 피해 |
| 제갈량 | 1250 | 5400 | 247.5 | 보급의 달인 | 출전 후 65초마다 아군 전 부대 회복 |
| 주유 | 1350 | 5880 | 231 | 화공연계 | 500 이내 가시 적에 화공. 숲은 칸마다 70초 |
| 곽가 | 1250 | 5400 | 245 | 간파 | 500 이내 가시 적의 발동 기술 1회 무효화 |
| 여몽 | 1450 | 6480 | 203.5 | 백의도강 | 1,000 안에 보이는 적이 없고 비교전이면 은신 |

기술 설명을 보면 이 게임이 무엇을 싸움의 축으로 삼는지 드러난다. 군량길, 보급 차단, 행군 체력, 야영지, 회군, 안개 속 가시 범위 같은 단어가 공격력만큼 자주 나온다. 데미지 경쟁보다 병참과 정보를 다루는 쪽에 설계의 무게가 있어 보인다. 다만 이것은 규칙 문서를 읽은 인상이고 플레이로 확인한 결론은 아니다.

전장 데이터는 관도, 호로관, 적벽, 가정 남산, 진류 반격, 남만 칠종칠금 여섯 곳이다. 메뉴 코드에는 싱글, 래더, 방 만들기와 참가, 월드 화면이 있다. 장르는 단정하지 않겠다. 내부 식별자는 `srpg`인데 기술 지속시간과 재사용 시간은 초 단위라, 플레이 없이 턴제인지 실시간인지 가를 수 없다.

## 2.05GB를 웹으로 나르는 방법

서명된 매니페스트가 선언하는 묶음의 크기는 다음과 같다.

$$
2{,}048{,}688{,}928\ \text{bytes} \approx 2.05\ \text{GB} \approx 1.91\ \text{GiB}
$$

파일은 9,382개이고 중앙값은 약 50KB, 가장 큰 파일은 15.2MB다. 대부분 작은 이미지이며 PNG 4,484개, WebP 3,166개, SVG 1,505개가 차지한다. 어디에 용량을 쓰는지도 매니페스트에서 바로 계산된다.

| 경로 | 크기 | 비중 | 파일 수 |
| --- | ---: | ---: | ---: |
| `assets/motions` | 592.8MB | 28.9% | 1,629 |
| `town/duel` | 470.4MB | 23.0% | 462 |
| `world/map` | 275.6MB | 13.5% | 1,351 |
| `audio` 전체 | 163.6MB | 8.0% | 109 |
| `localmap-common-officers/q5` | 82.8MB | 4.0% | 2,304 |
| `town/officer-portraits` | 77.4MB | 3.8% | 1,012 |

`assets/motions`와 `town/duel` 두 경로만으로 절반이 넘는다. 패키지 관리자 없는 웹에서 이 규모를 다루려고 택한 구조는 크게 네 단계다.

### 1. 작은 버전 파일에 먼저 서명을 확인한다

서비스 워커는 `/asset-media-version.json`을 먼저 받아 ECDSA P-256 서명을 [`SubtleCrypto.verify()`](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/verify)로 확인한다. 그다음 저장된 값과 `revision`을 비교한다.

```js
if(prior&&(version.revision<prior.revision||
   version.revision===prior.revision&&version.build!==prior.build))
  throw Error('MANIFEST_ROLLBACK');
```

서명이 유효해도 옛날 버전이면 거부한다. 서명은 "우리가 만든 파일"임을 보여줄 뿐 "최신 파일"임을 보여주지는 않기 때문이다. 같은 revision에 다른 build가 오는 경우까지 막아 둔 점도 눈에 띈다.

`build` 값은 `manifest.files`를 JSON으로 직렬화한 SHA-256이다. 파일 목록이 곧 버전 식별자가 된다.

### 2. 파일을 1MiB 조각으로 자르고 조각의 해시로 저장한다

조각 수는 파일마다 다음과 같이 정해지고, 코드는 매니페스트의 `chunks` 길이가 이 값과 다르면 거부한다.

$$
n_{\text{chunks}} = \left\lceil \frac{\text{bytes}}{2^{20}} \right\rceil
$$

전체 조각은 10,135개이고 고유 해시는 10,117개다. 저장 키가 경로가 아니라 해시(`/__verified_media__/<sha256>`)라서, 내용이 같은 조각은 한 번만 저장한다. 파일 하나만 바뀐 배포에서는 달라진 조각만 받으면 된다. 실제로 이 묶음의 절대다수 파일은 1MiB보다 작아, 여러 조각으로 나뉘는 파일은 552개뿐이다. 그래서 "1MiB 분할"의 효과는 큰 파일보다 해시 기반 저장과 스트리밍 쪽에서 더 크게 나타난다고 볼 수 있다.

조각을 받는 코드에는 이런 주석이 있다.

```js
// Do not arrayBuffer an untrusted/oversized response. Read at most one chunk.
```

응답을 통째로 메모리에 올리지 않고, 기대한 길이를 넘는 순간 끊는다. 파일 머리의 주석은 이 역할 분담을 한 줄로 요약한다. "A signature authenticates the manifest; chunk hashes bound RAM." 서명은 진위를, 조각 해시는 메모리 상한을 맡는다.

### 3. 서비스 워커의 수명에 맞춰 다운로드를 끊는다

브라우저는 서비스 워커를 오래 살려 두지 않는다. [`waitUntil()`](https://developer.mozilla.org/en-US/docs/Web/API/ExtendableEvent/waitUntil)은 작업이 진행 중임을 알릴 뿐 무한정 실행을 보장하지 않으므로, 2GB를 한 이벤트로 받는 설계는 위험하다. 이 워커는 한 번에 최대 32개 작업을 20초 제한 안에서 처리하고, 페이지가 다음 메시지를 보내 이어 가게 한다. 코드 주석도 "Short message batches survive browser service-worker lifetime limits on large packs"라고 이유를 적어 뒀다.

시작 전에는 필요한 용량의 1.1배가 남았는지 확인하고, 모자라면 `STORAGE_SPACE`로 멈춘다. 페이지 쪽은 [`navigator.storage.persist()`](https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/persist)를 요청한다. MDN에 따르면 이 요청은 브라우저가 들어주지 않을 수 있고, [저장 공간이 부족하면 best-effort 저장소는 축출될 수 있다](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria). [Cache 문서](https://developer.mozilla.org/en-US/docs/Web/API/Cache)도 브라우저가 한 오리진의 캐시를 통째로 지울 수 있다고 설명한다.

이 점이 네이티브 설치와의 결정적인 차이다. 2GB를 정성껏 내려받아도 플랫폼이 보관을 약속하지 않는다. 대신 읽을 때 조각을 다시 검증하고, 캐시에 없거나 해시가 맞지 않으면 네트워크에서 다시 받는 코드가 있어 지워져도 복구할 수 있는 구조다.

### 4. 재생 중인 판은 건드리지 않는다

업데이트 처리에서 가장 게임다운 부분이다. 클라이언트는 전투 화면(`/matches/`, `/single/deploy`)에서는 새 버전을 받지 않는다. 또한 탭마다 쓰는 build를 고정하고, 현재와 직전 build를 남겨 둔 뒤 오래된 조각만 정리한다. 전투 도중 배포가 일어나도 그 탭은 시작할 때의 묶음을 계속 쓸 수 있다.

서빙은 [W3C 서비스 워커 명세](https://www.w3.org/TR/service-workers/)가 정의한 `fetch` 가로채기로 이뤄진다. 매니페스트에 있는 경로만 응답하고 없는 경로는 `503`이다. 오디오 탐색을 위한 Range 요청은 조각을 이어 붙인 `ReadableStream`으로 [206](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/206)이나 416을 직접 만들어 돌려준다. 서버 없이 HTTP 의미론을 브라우저 안에서 구현한 것이다. `highWaterMark:0`을 줘서, 읽히지 않는 조각은 미리 검증하지도 않는다.

저장 대상도 코드로 제한한다. 워커 주석은 "No HTML, code, credentials, gameplay API or user data enters this store."라고 선언하고, `mediaPath()`가 허용된 디렉터리와 확장자만 통과시킨다. HTML과 JS를 이 캐시에 넣지 않으므로, 오프라인 게임을 만들려는 구조가 아니라 **미디어 전용 CDN을 브라우저에 설치하는 구조**로 읽는 편이 맞다. 게임 로직은 여전히 서버와 통신한다.

### 서명이 막는 것과 막지 못하는 것

공개 키(`MEDIA_PUBLIC_KEY`)는 워커가 불러오는 모듈에 들어 있고, 그 모듈은 게임과 같은 오리진에서 내려온다. 따라서 오리진 자체가 침해되면 공격자는 키가 든 코드까지 바꿀 수 있다. 이 서명의 현실적인 효과는 미디어 파일이 코드와 따로 변조되거나, 일부만 배포되거나, 옛 버전으로 되돌아가는 경우를 잡아 내는 데 있다고 보는 것이 맞다. 이는 웹 배포 일반의 한계이지 이 사이트만의 결함이 아니다.

매니페스트의 `revision` 1794021562026을 밀리초 유닉스 시각으로 읽으면 2026-11-07 12:19 KST로, 측정 약 한 시간 전이다. 필드 정의를 문서로 확인한 것은 아니므로 추론이지만, 맞다면 배포가 매우 활발한 시기다.

## 48만 바이트짜리 "앱"

사이트가 내려주는 안드로이드 APK(v11)는 489,144바이트다. 패키지는 `com.freekitlab.battle`, 액티비티 하나, `classes.dex` 10,300바이트에 주소는 게임 사이트를 가리킨다. 즉 게임은 APK 안이 아니라 앞서 본 웹 묶음에 있고, 앱은 [Android WebView](https://developer.android.com/develop/ui/views/layout/webapps/webview) 껍데기로 전체 화면과 가로 고정을 맡는다.

이 구성의 어려운 지점은 소셜 로그인이다. Google은 [임베디드 웹뷰의 OAuth 요청을 2021년 9월 30일부터 차단한다고 공지](https://developers.googleblog.com/upcoming-security-changes-to-googles-oauth-20-authorization-endpoint-in-embedded-webviews/)했고, 앱은 시스템 브라우저 쪽으로 넘기라고 안내한다. 그런데 외부 브라우저에서 로그인한 결과를 커스텀 스킴(`com.freekitlab.battle://`)으로 돌려받으면, 같은 스킴을 등록한 다른 앱이 가로챌 여지가 생긴다.

공개 코드의 해법은 돌아오는 값을 암호화하는 것이다.

1. 앱이 ECDH P-256 키 쌍과 임의의 `state`를 만들고, 공개 키만 URL 프래그먼트에 실어 로그인 페이지로 보낸다.
2. 로그인 페이지도 자기 키 쌍을 만든다. Google ID 토큰을 받으면 AES-GCM으로 암호화하고, `state`를 추가 인증 데이터로 묶는다.
3. 암호문을 커스텀 스킴으로 돌려보낸다. 앱은 비공개 키로 복호화하고, 5분 제한과 `state` 일치를 확인한 뒤 서버에 제출한다.

코드 주석은 이렇게 적는다. "A custom-scheme handler that intercepts a return can neither read the token nor redeem it." 비공개 키와 서버 챌린지 쿠키가 앱에 남기 때문이라는 설명이다. 표준 네이티브 앱 OAuth에서 [RFC 8252](https://www.rfc-editor.org/rfc/rfc8252)와 PKCE가 맡는 "가로채도 쓸 수 없게 하는" 역할을, GIS 기반 ID 토큰 흐름에 맞춰 직접 구성한 것으로 보인다. 직접 만든 프로토콜인 만큼 서버 쪽 검증은 내가 볼 수 없었고, 안전성을 판정하지도 않는다. 앱이 실제로 외부 브라우저를 띄우는 장면도 실행으로 확인하지 않았다.

iPhone은 안내 문구 기준으로 아직 공개 배포 전이며, Safari에서 홈 화면에 추가하는 방식을 제시한다. 코드 주석에는 iOS 바이너리 언급이 있고 약관 버전 경로에 `apple`이 들어 있어 준비 중인 것으로 보인다. Sign in with Apple을 함께 제공하는 것은 Google 로그인 앱에 동등한 대안을 요구하는 [App Store 심사 지침 4.8](https://developer.apple.com/app-store/review/guidelines/)과 방향이 맞는다. 한편 같은 지침 4.2는 앱이 "repackaged website" 이상이어야 한다고 요구한다. 얇은 웹뷰 구조가 심사에서 어떻게 판단될지는 예단할 수 없다.

## 헤더와 저장 정책

공개 응답에서 확인한 보안 헤더는 비교적 엄격하다. [CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy)는 `default-src 'self'`를 기본으로 스크립트를 자기 오리진과 Google 로그인으로 제한하고, `object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'`을 건다. HSTS, `X-Frame-Options: DENY`, `nosniff`, `Cross-Origin-Opener-Policy: same-origin-allow-popups`도 있다. 처리방침에는 비밀번호 단방향 해시, Apple 갱신 토큰 암호화, 약 14일 치 암호화 백업, AWS 이용이 적혀 있다. 처리방침 내용은 운영사 진술이며 내가 검증한 사실은 아니다.

## 출처를 파일마다 남긴 콘텐츠 공정

묶음 안에는 출처 기록(provenance)이 붙은 JSON이 108개 있다. 파일마다 해시, 길이, 제작 도구, 선택 근거를 남기는 방식이다. 기록에 나타나는 도구는 음악의 Suno v6, 중국어 대사 음성의 Fish Audio S2.1 Pro, 그리고 이미지 생성 도구와 Google Cloud Text-to-Speech다.

운영 측면에서 흥미로운 것은 사람의 판단까지 기록한다는 점이다. Suno 음악 기록에는 사용자가 9곡을 직접 고르고 그 9곡의 다운로드만 허용했다는 승인 내용이, 장수 음성 기록에는 `selection: "user-listened"`가 들어 있다. AI 생성물이 수천 개로 늘어나면 어느 것을 누가 승인했는지 금방 알 수 없게 되는데, 이를 데이터로 남긴 시도다. 다만 이 기록은 작성자의 자기 진술이고, 저작권이나 라이선스 상태를 증명하지는 않는다. 그 판단은 이 글의 범위 밖이다.

음악은 33곡이며 장면별로 돌아가고, 대사가 나오는 동안 음악을 10%로 낮춘다. 페이지 대사 27개는 중국어 음성에 한국어 자막을 붙인 구성이다. 버튼 글자까지 이미지로 그린 `ui/label-art`에 1,471개 파일이 들어 있어, 2GB에 가까운 용량에는 이런 연출 선택도 반영되어 있다.

## 정리: 설치 패키지를 웹에 다시 만들면

이 사이트에서 가져갈 만한 패턴은 게임이 아니어도 쓸 수 있다.

| 네이티브 설치 패키지의 기능 | 이 사이트의 웹 구현 |
| --- | --- |
| 서명 검증 | 매니페스트 ECDSA 서명 |
| 무결성 검사 | 조각별 SHA-256, 읽을 때 재검증 |
| 다운그레이드 방지 | `revision` 비교 |
| 증분 업데이트 | 내용 주소 기반 조각 재사용 |
| 실행 중 버전 유지 | 탭별 build 고정, 직전 build 보존 |
| 설치 공간 확인 | `StorageManager` 추정치 × 1.1 |

그리고 웹이기 때문에 대신할 수 없는 부분도 분명하다. 저장소 보관은 약속되지 않고, 서비스 워커의 수명은 브라우저가 정하며, 서명 키는 코드와 같은 신뢰 경계 안에 있다. 첫 실행 전에 2GB를 받게 하는 사용자 경험이 실제로 받아들여질지도 공개 파일로는 알 수 없다. 그 답은 플레이어가 생긴 뒤의 이탈률에 있을 것이고, 현재 그 수치는 공개되어 있지 않다.

## References

**1차·공식 문서**

- W3C, [Service Workers](https://www.w3.org/TR/service-workers/), Candidate Recommendation Draft, 2026-10-29
- MDN, [Using Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)
- MDN, [ExtendableEvent: waitUntil()](https://developer.mozilla.org/en-US/docs/Web/API/ExtendableEvent/waitUntil)
- MDN, [Cache](https://developer.mozilla.org/en-US/docs/Web/API/Cache)
- MDN, [StorageManager: persist()](https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/persist)
- MDN, [Storage quotas and eviction criteria](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)
- MDN, [SubtleCrypto: verify()](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/verify)
- MDN, [206 Partial Content](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/206)
- MDN, [Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy)
- Android Developers, [Build web apps in WebView](https://developer.android.com/develop/ui/views/layout/webapps/webview)
- Google Developers Blog, [Upcoming security changes to Google's OAuth 2.0 authorization endpoint in embedded webviews](https://developers.googleblog.com/upcoming-security-changes-to-googles-oauth-20-authorization-endpoint-in-embedded-webviews/), 2021
- IETF, [RFC 8252: OAuth 2.0 for Native Apps](https://www.rfc-editor.org/rfc/rfc8252)
- Apple, [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) (4.2, 4.8)

**조사 대상의 1차 자료 (운영사 진술 포함)**

- [battle.freekitlab.com](https://battle.freekitlab.com/) 공개 클라이언트 파일과 응답 헤더, 2026-11-07 측정
- [개인정보처리방침](https://battle.freekitlab.com/legal/privacy.html)
- [이용약관](https://battle.freekitlab.com/legal/2026-11-05-apple.html)
- [freekitlab.com](https://freekitlab.com/)

**중립 제3자 자료:** 찾지 못했다. 이 글의 게임 관련 서술은 모두 공개 파일 기준이며 플레이 검증을 거치지 않았다.
