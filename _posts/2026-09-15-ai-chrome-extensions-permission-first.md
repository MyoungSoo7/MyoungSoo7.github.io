---
layout: post
title: "AI 크롬 확장 5종을 정리하며 — 기능표보다 먼저 봐야 하는 건 권한이다"
date: 2026-09-15 15:02:30 +0900
categories: [Security, Tools]
tags: [chrome-extension, ai, manifest-v3, permissions, privacy, 보안]
---

지인이 보내준 "생산성 올려주는 AI 크롬 확장 5개" 목록을 정리해 달라는 요청을 받았다. 목록 자체는 Eightify · Glasp · Monica · HARPA AI · Compose AI 다섯 개였고, 각각 "영상 요약", "하이라이트", "올인원 AI", "웹 자동화", "글쓰기 자동완성" 이라는 한 줄 소개가 붙어 있었다.

그 소개를 그대로 옮겨 적는 글은 쓰지 않기로 했다. 홍보성 소개글의 기능 목록은 전부 **개발사가 스스로 한 주장**이고, 그걸 사실처럼 재배포하면 글이 아니라 전단이 된다. 대신 축을 하나 바꾼다 — **이 다섯 개가 무엇을 해 주는가가 아니라, 이 다섯 개가 무엇을 볼 수 있게 되는가.**

이건 취향의 문제가 아니라 순서의 문제다. 크롬 확장에서 기능은 권한의 **결과**다. 권한을 먼저 보면 기능은 예측되지만, 기능을 먼저 보면 권한은 끝까지 안 보인다.

**출처 원칙.** 이 글에서 사실로 적는 것은 ① 크롬 공식 개발자 문서·웹스토어 프로그램 정책, ② 각 확장의 크롬 웹스토어 리스팅에 실제로 적혀 있는 문구뿐이다. 개발사 설명문의 성능·프라이버시 주장은 "개발사 주장" 으로 라벨한다. **설치 수·별점은 인용하지 않는다** — 조회 시점마다 값이 달랐고, 내 조회 경로로 안정적으로 재현되지 않았다. 다섯 제품 사이의 중립적 비교 벤치마크는 **존재하지 않으므로** 우열 판정도 하지 않는다.

---

## 1. 다섯 개가 스스로 밝히는 것

크롬 웹스토어의 각 상세 페이지에는 `/privacy` 서브페이지가 있다. 주소 뒤에 `/privacy` 를 붙이면 열린다. 여기에 개발자가 **직접 공시한 취급 데이터 항목**이 나온다. 마케팅 문구가 아니라 정책상 신고 항목이다.

2026-09-15 조회 기준, 다섯 개의 공시는 이렇다.

| 확장 | 스토어 공시 데이터 항목 | 비고 (스토어 리스팅 문구) |
| --- | --- | --- |
| **Eightify** | 개인 식별 정보 | 유튜브 영상 요약. "Powered by Claude and ChatGPT" (개발사 주장) |
| **Glasp** | 개인 식별 정보, **웹사이트 콘텐츠** | 웹·PDF 하이라이트. 요약은 ChatGPT·Claude·Mistral·Gemini 사용이라고 명시 |
| **Monica** | 개인 식별 정보, 금융·결제 정보, 개인 통신 | 올인원. "Browser Operator" 로 브라우저 자동 조작을 표방 |
| **HARPA AI** | 조회 시점에 공시 내용을 읽지 못함 (아래 주의) | 사이드바 + 웹 자동화. "데이터를 로컬에 보관한다" 는 개발사 주장 포함 |
| **Compose AI** | 개인 식별 정보, 개인 통신, 위치, **웹사이트 콘텐츠** | 입력창 자동완성. 버전 2.1.1 / Updated 2025-01-02 |

읽는 법 세 가지.

**① "웹사이트 콘텐츠" 가 들어 있느냐가 1차 분기점이다.** 이 항목은 웹스토어 정의상 "텍스트, 이미지, 소리, 영상, 하이퍼링크" 를 뜻한다. 즉 **당신이 보고 있는 페이지의 내용 자체**다. Glasp 와 Compose AI 는 이걸 공시했다. 기능상 당연하다 — 하이라이트하고 자동완성하려면 페이지를 읽어야 한다. 공시가 기능과 일치한다는 건 나쁜 신호가 아니라 **정직한 신호**다.

**② 공시가 짧다고 안전한 게 아니다.** Eightify 는 개인 식별 정보만 공시한다. 이건 "페이지를 안 읽는다" 는 뜻일 수도 있고(예: 영상 ID만 서버로 보내고 자막은 서버가 직접 가져오는 설계), 단순히 공시 범위를 좁게 해석한 것일 수도 있다. **바깥에서는 구분할 수 없다.** 다만 웹스토어 정책은 이 회피 경로 하나를 명시적으로 막아 뒀다 — 사용자 기기에서 **로컬로만** 처리·저장하는 데이터도 공시 대상이라고 FAQ 에 못박혀 있다.[^userdata] "우리는 로컬에 둡니다" 는 공시 면제 사유가 아니다.

**③ Compose AI 의 `Updated` 날짜를 보라.** 조회 시점 기준 마지막 업데이트가 2025-01-02 로, 20개월이 넘었다. 업데이트가 없다는 게 곧 취약하다는 뜻은 아니지만, 확장은 브라우저 위에서 도는 코드이고 브라우저는 계속 바뀐다. 스토어 상세의 **Details → Updated** 는 설치 전에 봐야 할 한 칸이다.

> ⚠️ HARPA 의 `/privacy` 페이지는 내 조회 경로에서 본문이 비어 돌아왔다. **"공시가 없다" 는 뜻이 아니다** — 내 조회가 실패한 것과 페이지에 내용이 없는 것은 다른 사건이고, 나는 그 둘을 가르지 못했다. 직접 열어서 확인해야 한다. 참고로 HARPA 의 리스팅 설명문에는 사용자 수 주장이 적혀 있는데, 스토어가 자체적으로 표시하는 사용자 수 구간과 값이 다르다. 측정 주체가 다른 두 숫자이므로 이 글은 어느 쪽도 인용하지 않는다.

한 가지 더, 판단이 아니라 사실로만 적는다 — Monica 의 스토어 설명문에는 "AI 탐지 도구를 회피하도록(evading AI detection tools) 글을 다시 써 준다" 는 기능이 명시돼 있다. 회사 정책이나 학교 규정이 걸린 환경이라면 설치 전에 확인할 항목이다.

---

## 2. 위험 수준을 정하는 건 기능이 아니라 `host_permissions` 다

크롬 확장의 권한은 매니페스트에서 선언된다. 공식 문서가 구분하는 축은 크게 두 가지다.[^declare]

- `"permissions"` — `storage`, `cookies`, `tabs` 같은 **API 권한**
- `"host_permissions"` — `https://*/*` 같은 **호스트 매칭 패턴**

여기서 실질적인 위험을 결정하는 건 후자다. 공식 문서가 직접 열거하는바, 호스트 권한이 있으면 확장은 그 호스트에 대해 콘텐츠 스크립트를 주입하고, `chrome.tabs` 로 URL·제목을 읽고, `chrome.cookies` 로 쿠키에 접근하고, `chrome.webRequest` 로 네트워크 요청을 감시·제어할 수 있다.[^declare]

**"모든 사이트" 를 준다는 것의 의미가 여기서 나온다.** 사내 위키, 깃랩, 관리 콘솔, 쿠팡 결제창, 병원 예약 페이지가 전부 같은 집합에 들어간다. 확장 입장에서 이 페이지들은 구분되지 않는다. 개발자에게 특히 아픈 지점은 **내부 도메인** 이다 — 회사 인트라넷은 공개 웹에 없으니 크롤링당할 일이 없다고 생각하기 쉬운데, 브라우저 확장은 크롤러가 아니라 **이미 로그인한 당신의 세션 안쪽에** 있다.

반대로 잘 설계된 확장의 표식도 문서에 있다. `"activeTab"` 권한은 **경고를 띄우지 않으며**, 사용자가 확장을 실제로 실행한 그 탭에만 **일시적인** 호스트 권한을 준다.[^warnings] "요약 버튼을 눌렀을 때만 이 페이지를 읽습니다" 와 "설치된 순간부터 모든 페이지를 읽습니다" 는 UI 에서 똑같아 보이지만 매니페스트에서는 전혀 다른 물건이다.

실무 기준 하나 — **`chrome://extensions` → 해당 확장 → 세부정보 → 사이트 액세스** 에서 "클릭할 때만" 을 고를 수 있다.[^sitaccess] AI 요약·번역처럼 **내가 부를 때만 동작하면 되는** 확장은 전부 여기로 내려도 기능이 죽지 않는다. 자동완성처럼 상시 감시가 본질인 확장은 안 된다 — 그게 바로 그 확장이 상시 권한을 필요로 한다는 증거다.

---

## 3. 설치 시점의 판단에는 유통기한이 있다

여기가 이 글에서 제일 하고 싶은 말이다.

공식 문서는 두 가지를 각각 명시한다.

1. **크롬은 설치된 확장을 자동으로 최신 버전으로 갱신한다.** 기본 동작으로 시작 시점과 몇 시간 간격으로 업데이트를 확인한다.[^lifecycle]
2. **경고를 유발하는 권한이 새로 추가되면**, 사용자가 수락할 때까지 그 확장은 **비활성화된다.**[^warnings]

2번은 안전장치처럼 읽히지만, 정확히 반대로도 읽어야 한다. 경고는 **새 권한이 추가될 때** 뜬다. 이미 `<all_urls>` 를 받아 둔 확장이 그 범위 **안에서** 하는 일을 바꾸는 업데이트는, 정의상 새 경고를 띄우지 않는다. 즉 —

> 사용자가 승인한 것은 **권한의 범위**이지, 그 권한으로 무엇을 할지에 대한 **코드**가 아니다. 코드는 몇 시간마다 조용히 바뀐다.

(이 문장은 위 두 문서에서 따라 나오는 추론이지, 문서에 그대로 적힌 문장은 아니다.)

그래서 "설치 전에 리뷰를 잘 읽어라" 는 조언은 절반만 맞다. 리뷰는 **과거의 코드**에 대한 것이고, 당신이 내일 실행할 코드는 아직 존재하지 않는다. 방어선은 리뷰가 아니라 **권한 범위를 애초에 좁게 주는 것** 하나뿐이다.

---

## 4. 웹스토어 정책이 보장해 주는 것과 안 해 주는 것

"구글이 심사하니까 괜찮지 않나" 에 대한 답은 정책 원문에 있다. Limited Use 정책은 꽤 강하다 — 공개된 단일 목적에 필요한 데이터만 수집·전송할 것, 개인화 광고를 위한 데이터 전송·판매 금지, 데이터 브로커 판매 금지, 신용평가 목적 사용 금지, 사람이 사용자 데이터를 읽는 것도 원칙 금지(명시적 동의·보안 조사 등 예외).[^limiteduse]

그런데 같은 문서의 4항이 이렇게 돼 있다.

> 웹 브라우징 활동의 수집과 사용은 금지된다. **단, 해당 제품의 크롬 웹스토어 페이지와 제품 UI 에 눈에 띄게 설명된 사용자 대면 기능에 필요한 범위는 예외로 한다.**[^limiteduse]

AI 요약·번역·자동완성 확장은 **이 예외 안에 정확히 들어간다.** "페이지 요약" 은 스토어 페이지에 크게 적힌 사용자 대면 기능이고, 그걸 하려면 페이지 내용이 필요하다. 그러니 정책을 지키면서도 당신이 보는 페이지의 텍스트는 합법적으로 외부 LLM API 로 나간다.

즉 이 정책이 보장하는 건 **"당신 몰래 팔지 않는다"** 이지 **"당신 것이 밖으로 안 나간다"** 가 아니다. NDA 문서나 고객 데이터가 떠 있는 화면에서는 이 구분이 전부다.

여기에 한 겹이 더 있다. 대부분의 AI 확장은 자체 모델을 돌리지 않고 OpenAI·Anthropic·Google 의 API 를 호출한다(위 표의 Glasp·Monica·HARPA 는 리스팅에 모델명을 직접 적어 뒀다). 그러면 데이터 경로는 `브라우저 → 확장 개발사 서버 → 모델 제공자` 가 된다. **당신이 신뢰 관계를 맺어야 하는 주체가 하나가 아니라 둘**이라는 뜻이고, 가운데 서버가 무엇을 로깅하는지는 개발사 주장 외에 검증 수단이 없다.

---

## 5. 회사 브라우저라면, 이건 개인의 판단으로 두면 안 된다

개인이 자기 프로필에서 무엇을 깔든 그건 본인 선택이다. 문제는 사내 자산이 열리는 브라우저다. 여기엔 정책 수단이 있고, 공식 문서화돼 있다.

크롬의 `ExtensionSettings` 정책은 확장 단위 제어를 제공한다. 실무에서 쓸 만한 필드는 이 셋이다.[^extsettings]

- **`installation_mode`** — `allowed` / `blocked` / `force_installed`. 확장 ID 단위로 지정하고, `*` 로 전체 기본값을 정한다. 기본을 `blocked` 으로 두고 허용 목록만 여는 방식이 가능하다.
- **`blocked_permissions`** — **특정 API 권한을 요구하는 확장의 설치·실행 자체를 막는다.** 예컨대 쿠키 접근을 차단하면, 그 권한을 요구하는 확장은 설치되지 않고 **이미 설치돼 있었다면 더 이상 로드되지 않는다.** 선택적(optional) 권한으로 들어 있는 경우엔 설치는 되고 런타임에 그 권한만 자동 거부된다.
- **`blocked_install_message`** — 차단됐을 때 사용자에게 보여줄 문구. "IT 팀에 문의" 같은 안내를 최대 1,000자까지 붙인다. 이게 없으면 사용자는 그냥 "안 깔리네" 하고 개인 프로필로 우회한다.

포인트는 **확장 ID 화이트리스트보다 권한 기반 차단이 오래 간다**는 것이다. ID 목록은 새 확장이 나올 때마다 갱신해야 하지만, "쿠키 읽는 확장 금지" 는 아직 나오지 않은 확장에도 적용된다.

---

## 6. 그래서 이 다섯 개를 어떻게 배치하나

중립 벤치마크가 없으므로 "어느 게 더 좋다" 는 말은 안 한다. 대신 **노출 면적 기준의 배치**만 적는다.

- **호출형(내가 버튼을 눌러야 도는 것) — Eightify, Glasp, Monica 의 요약 기능**: 사이트 액세스를 **"클릭할 때만"** 으로 내리고 쓴다. 유튜브 요약만 쓸 거면 **특정 사이트(youtube.com)** 로 못박는 게 더 낫다. 기능 손실이 사실상 없다.
- **상시형(입력을 계속 지켜봐야 도는 것) — Compose AI**: 구조상 "클릭할 때만" 으로 내릴 수 없다. 그러면 남는 통제 수단은 **어느 프로필에서 쓰느냐** 뿐이다. 업무 계정이 로그인된 프로필에는 두지 않는 쪽을 권한다.
- **자동화형 — HARPA, Monica 의 Browser Operator**: 페이지를 읽는 데서 끝나지 않고 **당신 세션으로 페이지를 조작한다.** 읽기 권한과 쓰기 권한은 사고의 크기가 다르다. 개인 프로필 전용으로 두고, 관리 콘솔·금융 사이트가 열리는 프로필에는 올리지 않는다.
- **공통**: 크롬 프로필을 **업무용과 개인용으로 분리**하는 것이 위의 모든 세부 설정보다 효과가 크다. 확장은 프로필 단위로 설치되므로, 프로필을 가르면 노출 면적이 설정 실수와 무관하게 갈린다.

---

## 마무리

받은 목록을 정리하면 이렇게 된다.

1. 기능 소개는 전부 개발사 주장이다. 검증 가능한 1차 정보는 스토어 상세의 **`/privacy` 공시**, **Details 의 Updated 날짜**, 그리고 설치 시 뜨는 **권한 경고** 세 개뿐이다.
2. 위험 수준은 기능이 아니라 `host_permissions` 가 정한다. "모든 사이트" 를 준 순간 사내 위키와 은행 페이지가 같은 칸에 들어간다.
3. 그 판단에는 유통기한이 있다. 확장은 몇 시간마다 자동 갱신되고, **이미 준 권한 범위 안의 변경은 새 경고를 띄우지 않는다.**
4. 웹스토어 정책은 "몰래 팔지 않는다" 를 보장하지, "밖으로 안 나간다" 를 보장하지 않는다. AI 요약은 정책상 예외 조항에 정확히 들어맞는 기능이다.
5. 조직이라면 개인의 분별에 맡기지 말고 `blocked_permissions` 로 막는다.

한 줄 요약 — **AI 확장을 고르는 기준은 "무엇을 요약해 주는가" 가 아니라 "내가 보는 화면 중 무엇을 같이 보게 되는가" 다.** 그리고 그 답은 홍보글이 아니라 주소 뒤에 `/privacy` 를 붙인 페이지에 있다.

---

## References

[^declare]: Chrome 공식 개발자 문서 — [Declare permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions) (`permissions` / `host_permissions` 구분, 호스트 권한이 여는 API 목록)
[^warnings]: Chrome 공식 개발자 문서 — [Permission warning guidelines](https://developer.chrome.com/docs/extensions/develop/concepts/permission-warnings) (새 경고 권한 추가 시 확장 비활성화, `activeTab` 은 경고 없이 일시 호스트 권한 부여)
[^lifecycle]: Chrome 공식 개발자 문서 — [The Chrome Extension update lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/extensions-update-lifecycle) (시작 시 및 수 시간 간격 자동 업데이트)
[^limiteduse]: Chrome Web Store 프로그램 정책 — [Limited Use](https://developer.chrome.com/docs/webstore/program-policies/limited-use)
[^userdata]: Chrome Web Store 프로그램 정책 — [Updated Privacy Policy & Secure Handling Requirements](https://developer.chrome.com/docs/webstore/user_data) (FAQ #3: 로컬 처리·저장 데이터도 공시 대상 / FAQ #4: 사용자 데이터 항목 정의)
[^extsettings]: Chrome Enterprise 공식 문서 — [Configure ExtensionSettings policy](https://support.google.com/chrome/a/answer/9867568) (`installation_mode`, `blocked_permissions`, `blocked_install_message`)
[^sitaccess]: Chrome Web Store 고객센터 — [Install and manage extensions](https://support.google.com/chrome_webstore/answer/2664769) (확장 관리 및 사이트 액세스 설정)

각 확장의 공시 내용은 다음 페이지에서 직접 확인할 수 있다 — [Eightify](https://chromewebstore.google.com/detail/eightify-ai-youtube-summa/cdcpabkolgalpgeingbdcebojebfelgb/privacy) · [Glasp](https://chromewebstore.google.com/detail/glasp-web-highlighter-pdf/blillmbchncajnhkjfdnincfndboieik/privacy) · [Monica](https://chromewebstore.google.com/detail/monica-all-in-one-ai-assi/ofpnmcalabcbjgholdjcjblkibolbppb/privacy) · [HARPA AI](https://chromewebstore.google.com/detail/harpa-ai-web-automation-w/eanggfilgoajaocelnaflolkadkeghjp/privacy) · [Compose AI](https://chromewebstore.google.com/detail/compose-ai-ai-powered-wri/ddlbpiadoechcolndfeaonajmngmhblj/privacy)
