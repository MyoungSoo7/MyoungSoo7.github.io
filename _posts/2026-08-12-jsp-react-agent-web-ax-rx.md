---
layout: post
title: "에이전트는 당신의 화면을 보지 않는다 — JSP·React와 AX·RX 시대의 인터페이스"
date: 2026-08-12 02:05:00 +0900
categories: [engineering, architecture]
tags:
  [
    jsp,
    react,
    ax,
    rx,
    physical-ai,
    agentic-web,
    robots-txt,
    mcp,
    accessibility,
    ssr,
  ]
---

세 편짜리 이야기의 마지막이다. 첫 글은 [화면](/2026/08/12/nexacro-websquare-vs-vibe-coding-react-productivity/)을, 둘째 글은 [출력물](/2026/08/12/pdf-report-tools-vs-vibe-coding-pdf/)을 다뤘다. 이번엔 축을 옮긴다 — **그 화면을 누가 보는가.**

JSP와 React를 낡음/새것으로 놓으면 시시한 글이 된다. AX 시대의 진짜 질문은 다르다. 30년간 UI는 사람 눈을 위해 렌더링됐다. 소비자가 에이전트로 바뀌면 렌더링 대상 자체가 바뀐다.

먼저 결론부터.

> 에이전트 관점에서는 **CSR React보다 JSP가 읽기 쉽다.** 하지만 그게 JSP의 승리를 뜻하진 않는다. 렌더링을 아무리 고쳐도 **`robots.txt`에서 문이 잠기기 때문**이다. AX 시대의 인터페이스 경쟁은 HTML 렌더링 방식이 아니라 **별도 표면**에서 벌어지고, 화면은 **법이 사람의 승인을 요구하는 자리**로 남는다.

그리고 이 글에서 가장 중요한 사실 하나를 미리 적는다. **웹 접근성을 규정한 법률의 국가 공식 원문 페이지가, 자바스크립트 없이는 읽히지 않는다.** 뒤에서 실측으로 보인다.

---

## 1. 용어부터 — AX와 RX는 생각만큼 정리된 말이 아니다

글을 쓰려고 조사하다 내 가정 두 개가 깨졌다. 먼저 이것부터 정리하지 않으면 나머지가 전부 흔들린다.

### AX는 한국(과 일본)의 조어다

과학기술정보통신부는 2024년 12월 30일 보도자료 제목에 이 말을 못 박았다 — 「**인공지능 대전환(AX, AI Transformation)**을 주도할 대한민국 디지털 혁신 기술」.[^1] 2026년도 업무계획에서는 아예 정책 단위로 쓴다 — "범정부적으로 추진하고 있는 부처별 **인공지능 전환(AX)** 사업", "**4대 지역 인공지능 전환 사업(AX프로젝트)('26~'30년, 총 3.1조 원)**".[^2] 정부 영문판도 "**AI Transformation (AX)**"로 병기한다.[^3]

민간에서 가장 선명한 정의는 LG전자다. 조주완 CEO는 자사 뉴스룸에서 이렇게 말했다.

> "이제는 **AX(AI Transformation, 인공지능전환)의 속도가 사업의 성패를 좌우**하게 될 것"
> "과거 DX(디지털전환)가 개별 단위업무에서 최적화, 가시화, 이상감지 등을 구현했다면, **AX는 DX로 최적화된 단위업무를 통합한 업무 프로세스 전반에 적용**되어 자율 공정 등 획기적인 업무 혁신을 가능케 할 수 있을 것"[^4]

그런데 영어권을 뒤지면 이 약어가 없다. Gartner는 "AI transformation"을 풀어서만 쓰고,[^5] IDC의 리서치 서비스명도 "Digital Business and **AI Transformation** Strategies"로 풀어 쓴다.[^6] McKinsey의 State of AI 보고서에는 AX 약어가 없고,[^7] Deloitte도 "agentic AI", "physical AI"는 쓰되 AX는 쓰지 않는다.[^8] 학술 문헌은 오히려 **AIT**로 약칭하며, 한 논문은 "We are unable to identify any useful definition of AIT"라고 적는다.[^9] 일본 노무라종합연구소는 "Recently, the word **AX (AI Transformation)** has been coming into use in place of DX"라고 쓴다.[^10]

**즉 AX는 한·일권에서 통용되는 말이다.** 한국 정부가 공식 영어 표기로도 밀고 있으니 "한국이 만든 말이지만 정부가 공인한 말"이 정확한 서술이다.

### RX는 대기업들이 서로 다르게 푼다

여기서 내 가정이 정면으로 깨졌다.

| 주체         | RX를 무엇으로 푸는가                         |
| ------------ | -------------------------------------------- |
| LG CNS       | **Robot Transformation (로봇 전환)**[^11]    |
| SK AX        | **Robot Transformation**[^12]                |
| **삼성전자** | **Robotics eXperience (로보틱스 경험)**[^13] |

삼성전자는 2026년 7월 21일 "대표이사 직속 **'RX(Robotics eXperience)사업추진실'**을 신설한다"고 밝혔다.[^13] 삼성 사내 어법에서 DX 부문이 이미 "Device eXperience"이므로, 삼성의 RX는 *전환*이 아니라 _경험_ 계열 작명이다. **DX→AX→RX를 매끄러운 3단 계보로 쓰면 삼성전자 사례가 곧바로 반례가 된다.**

더 결정적인 건 이것이다. **정부 로봇 정책 문서에 RX는 없다.** 제4차 지능형로봇 기본계획 공고와 관련 보도자료를 확인했지만 RX라는 약어는 등장하지 않는다.[^14] 정부의 공식 어휘 쌍은 「**AX + 피지컬 AI**」다 — 2026년도 업무계획은 "**물리적 인공지능(피지컬AI)** 확산"과 「(가칭)물리적 인공지능(피지컬 AI) 구축·확산 전략」 수립('26.상반기)을 명시한다.[^2]

그리고 Physical AI는 AX와 달리 **실제 글로벌 공용어**다. NVIDIA는 용어집에서 이렇게 정의한다.

> "Physical AI lets autonomous systems like cameras, robots, and self-driving cars **perceive, understand, reason, and perform or orchestrate complex actions in the physical world.**"[^15]

젠슨 황의 표현 변화도 인용할 만하다. CES 2025에서 "The **ChatGPT moment for general robotics** is just around the corner"였던 것이,[^16] CES 2026에서는 "The **ChatGPT moment for robotics is here**"가 됐다.[^17] 같은 화자, 같은 자사 채널, 1년 간격이다.

**정리**: 이 시장은 용어조차 합의되지 않았다. 그 자체가 얼마나 초기인지를 말해준다. 그러니 이 글에서 RX는 "로봇·물리 세계로 확장된 자동화"라는 **느슨한 뜻**으로만 쓰고, 계보처럼 서술하지 않겠다.

---

## 2. 에이전트 가독성 — 지표 하나를 정의하자

논의를 정확히 하려면 재는 자가 필요하다. 이 글에서만 쓰는 지표를 정의한다. **표준 용어가 아니라 내가 이 글을 위해 만든 것**임을 밝힌다.

어떤 페이지에서, 자바스크립트를 실행하지 않고 얻을 수 있는 정보량을 $I_{\text{no-JS}}$, 브라우저로 완전히 렌더링한 뒤 얻을 수 있는 정보량을 $I_{\text{full}}$이라 하자. **에이전트 가독성** $\lambda$를 이렇게 둔다.

$$\lambda = \frac{I_{\text{no-JS}}}{I_{\text{full}}}, \qquad 0 \le \lambda \le 1$$

이 값이 왜 중요한가. 에이전트가 페이지 하나를 이해하는 비용이 $\lambda$에서 갈리기 때문이다.

$$C_{\text{agent}} = \begin{cases} C_{\text{fetch}} & (\lambda \approx 1) \\[4pt] C_{\text{fetch}} + C_{\text{browser}} & (\lambda < 1) \end{cases}$$

그리고 $C_{\text{browser}} \gg C_{\text{fetch}}$다. 브라우저를 띄운다는 건 HTML 파서 + CSS 레이아웃 엔진 + JS 런타임 + 합성기를 전부 올린다는 뜻이다. **바로 앞 글에서 다룬 헤드리스 크롬의 비용 구조가 그대로 여기 다시 나온다.**[^18] 페이지 $N$개를 순회하는 에이전트라면 이 차이가 $N$배로 증폭된다.

이 틀로 보면 익숙한 기술들의 좌표가 뒤집힌다.

| 방식                 | $\lambda$ | 이유                                 |
| -------------------- | --------- | ------------------------------------ |
| JSP / 서버 렌더 HTML | ≈ 1       | HTTP 응답에 내용이 전부 있음         |
| React SSR / RSC      | ≈ 1       | 서버에서 HTML 생성 후 hydrate        |
| **React CSR (SPA)**  | **≈ 0**   | 응답은 빈 컨테이너, 내용은 JS가 생성 |

**에이전트에게는 JSP가 CSR React보다 읽기 쉽다.** 이건 취향 문제가 아니라 응답 바이트에 무엇이 들어 있느냐의 문제다.

이게 내 사변이 아니라는 근거는 구글이 직접 써놨다.

> "Crawling a URL and parsing the HTML response works well for classical websites or server-side rendered pages where the HTML in the HTTP response contains all content. **Some JavaScript sites may use the app shell model where the initial HTML does not contain the actual content** and Google needs to execute JavaScript before being able to see the actual page content."
> "Googlebot queues all pages with a 200 HTTP status code for rendering… **The page may stay on this queue for a few seconds, but it can take longer than that.**"
> "**Keep in mind that server-side or pre-rendering is still a great idea because it makes your website faster for users and crawlers, and not all bots can run JavaScript.**"[^19]

마지막 문장이 핵심이다. **"not all bots can run JavaScript" — 구글 자신의 문서다.**

빙은 한 발 더 나간다.

> "bingbot is generally able to render JavaScript. However… **it is difficult for bingbot to process JavaScript at scale on every page of every website**"
> "Therefore, in order to increase the predictability of crawling and indexing by Bing, **we recommend dynamic rendering**"[^20]

---

## 3. 실측 — 한국 웹은 자바스크립트 없이 읽히지 않는다

$\lambda$를 실제로 재봤다. 2026년 8월 12일, `curl`로 받은 원시 HTML 기준이다.

### naver.com

전체 **254,768 bytes** 중 **248,306 bytes(97.5%)**가 `<script>` 태그 안이다. 태그를 걷어내고 남는 가시 텍스트는 이게 전부다.

```
NAVER 상단영역 바로가기 서비스 메뉴 바로가기 새소식 블록 바로가기
쇼핑 블록 바로가기 관심사 블록 바로가기 MY 영역 바로가기
위젯 보드 바로가기 보기 설정 바로가기 검색 검색 AI 검색 입력도구
```

뉴스도 쇼핑도 없다. $\lambda \approx 0$이다. 그리고 눈여겨볼 게 있다 — **읽히는 텍스트가 전부 "바로가기", 즉 접근성 스킵 링크다.** 에이전트가 읽을 수 있는 유일한 것이 장애인용 배려 장치라는 사실은, 이 글 8장의 논지를 미리 요약한다.

### law.go.kr — 이 글에서 가장 아이러니한 실측

국가법령정보센터의 「지능정보화 기본법」 페이지를 받아봤다.

```
http=200  bytes=145,033
"제46조"        → 0회
"접근성을 보장"   → 0회
"장애인·고령자"   → 0회
```

145KB를 받았는데 조문이 하나도 없다. 그리고 원시 HTML의 가시 텍스트 첫 줄은 이렇게 시작한다.

> "법령 > 본문 > 지능정보화 기본법 | 국가법령정보센터 **자바스크립트를 지원하지 않아 일부 기능을 사용할 수 없습니다.**"

**「지능정보화 기본법」 제46조는 국가기관에 웹 접근성 보장 의무를 지우는 조항이다.**[^21] 그 법의 국가 공식 원문 페이지가, 자바스크립트를 실행하지 않는 클라이언트에게 조문을 보여주지 않는다.

이건 비꼬려고 고른 사례가 아니다. **공공 데이터의 $\lambda$가 0이면 AX는 시작조차 못 한다**는 걸 가장 짧게 보여주는 사례라서 골랐다. (덧붙여, 이 때문에 나는 제46조 원문을 law.go.kr에서 직접 대조하지 못했다. 아래 한계 절에 적었다.)

---

## 4. 그렇다고 JSP가 이겼다는 뜻은 아니다 — 스펙의 실제 지위

여기서 흔한 오해 두 개를 동시에 잡아야 한다.

### 오해 1: "JSP는 deprecated 됐다" → **사실이 아니다**

Jakarta EE 11 플랫폼 사양 원문을 열어보면 이렇게 적혀 있다.

> "The following technologies are **required**: … Jakarta Faces 4.1 … **Jakarta Pages 4.0** … Jakarta Servlet 6.1 …"
> "The following technologies are **deprecated**: _**NONE**_"[^22]

**Jakarta Pages 4.0은 Jakarta EE 11의 필수(required) 기술이고, EE 11이 deprecate한 기술은 하나도 없다.** 이름도 바뀌었다 — 4.0부터는 "Jakarta Server Pages"가 아니라 **"Jakarta Pages"**다("Server"가 빠졌다).[^23] Jakarta EE 12용 4.1도 진행 중이다.

### 오해 2: "그럼 아직 쓸 만하다" → 이것도 아니다

4.1의 릴리스 플랜 원문이 상태를 정확히 말해준다.

> "**This release does not plan to add new features.** It aims to address known issues in the Jakarta Pages specification and to maintain alignment with the Jakarta Servlet and Expression Language specifications."
> Removals, deprecations or backwards incompatible changes: **"None"**[^24]

**유지보수는 살아 있으나 신규 기능 계획은 없다.** 4.0의 성격도 "removes deprecated code"였고, 제거 목록에는 `jsp:plugin`이 있는데 그 이유가 "the associated HTML elements are no longer supported by any major browser"였다.[^23]

그리고 Spring Boot의 입장은 훨씬 단호하다.

> "**If possible, JSPs should be avoided.** There are several known limitations when using them with embedded servlet containers."[^25]
> "**JSPs are not supported when using an executable jar.**"[^25]

Spring Boot가 자동설정으로 지원하는 템플릿 엔진 목록에 **JSP는 아예 없다**(FreeMarker / Groovy / Thymeleaf / Mustache).[^25] Spring Boot 3.5 문서에는 "**Undertow does not support JSPs**"라는 줄이 하나 더 있었는데, 최신 문서에서는 그 줄이 사라졌다.[^26]

**정확한 서술은 이것이다: 스펙은 살아 있고 필수 기술이지만 신규 기능 계획이 없고, 지배적인 프레임워크는 공식적으로 회피를 권한다.** "deprecated"와 "discouraged"는 다른 말이고, 이 구분을 흐리면 틀린 글이 된다.

---

## 5. React는 이미 서버로 돌아왔다 — 원이 아니라 나선

$\lambda$ 관점에서 CSR이 불리하다는 건 React 팀이 누구보다 잘 안다. 그래서 React Server Components가 나왔다. 공식 문서의 정의다.

> "Server Components are a new type of Component that **renders ahead of time, before bundling, in an environment separate from your client app or SSR server.**"[^27]

푸는 문제도 명시돼 있다.

> "users need to download and parse an **additional 75K (gzipped) of libraries**, and wait for a second request to fetch the data after the page loads, just to render static content"
> "Causing an **expensive client-server waterfall**."
> "Server Components can also run on a web server during a request for a page, **letting you access your data layer without having to build an API.**"[^27]

그리고 아키텍처 선언이 이 글의 논지와 정확히 겹친다.

> "This new application architecture **combines the simple 'request/response' mental model of server-centric Multi-Page Apps with the seamless interactivity of client-centric Single-Page Apps**, giving you the best of both worlds."[^27]

"서버 중심 MPA의 요청/응답 모델" — **그게 JSP가 하던 일이다.**

그래서 원점 회귀인가? 아니다. **나선이다.**

$$\text{JSP} \xrightarrow{\ \text{조합성 획득}\ } \text{SPA} \xrightarrow{\ \lambda\ \text{회복}\ } \text{RSC}$$

JSP는 $\lambda \approx 1$이었지만 컴포넌트 조합·타입 안전·상태 관리가 없었다. SPA는 그걸 얻는 대가로 $\lambda$를 버렸다. RSC는 조합성을 유지한 채 $\lambda$를 되찾는다. 같은 자리로 돌아온 게 아니라 한 바퀴 올라온 것이다.

한 가지 정확히 해둘 것 — RSC의 안정성 표기는 미묘하다.

> "While React Server Components in React 19 are **stable** and will not break between minor versions, **the underlying APIs used to implement a React Server Components bundler or framework do not follow semver and may break between minors** in React 19.x."[^27]

**앱 개발자에게는 stable, 프레임워크·번들러 저자에게는 unstable이다.** "RSC는 아직 실험적"이라고 쓰면 틀린다. (React 19는 2024년 12월 5일 정식 릴리스됐고, 2026년 8월 현재 최신은 19.2다.[^28])

React 공식 문서가 크롤러를 언급하는 곳도 있다. `renderToPipeableStream`에는 "**Waiting for all content to load for crawlers and static generation**"이라는 정식 섹션이 있고, 예제 코드에 `let isCrawler = // ... depends on your bot detection strategy ...`가 그대로 들어 있다.[^29]

---

## 6. 그런데 렌더링을 고쳐도 문이 잠긴다

여기가 이 글의 반전이다. $\lambda$를 1로 만들면 에이전트 시대가 열리는가? **실측해보면 반대 방향으로 가고 있다.**

2026년 8월 12일 기준으로 주요 사이트의 `robots.txt`를 직접 받아봤다.

`news.naver.com`에는 영문 주석이 박혀 있다.

```
# BOT ACCESS FOR THE PURPOSES OF AI TRAINING AND
# RETRIEVAL-AUGMENTED GENERATION (RAG) IS STRICTLY PROHIBITED.
User-agent: GPTBot
Disallow: /
User-agent: OAI-SearchBot
Disallow: /
...
```

GPTBot·OAI-SearchBot·PerplexityBot·Google-Extended·ClaudeBot·Claude-SearchBot·meta-externalagent·Applebot-Extended·CCBot **9종 전부 `Disallow: /`** 다.

전체 조사 결과는 이렇다.

| 사이트                | AI 크롤러 정책                                                          |
| --------------------- | ----------------------------------------------------------------------- |
| news.naver.com        | 9종 `Disallow: /` + RAG 금지 주석                                       |
| 연합뉴스              | GPTBot·ClaudeBot·PerplexityBot·CCBot 등 `Disallow: /`                   |
| brunch(카카오)        | AI 학습 크롤러 16종 `Disallow: /` — **단 Googlebot·Yeti·Daumoa는 허용** |
| 당근                  | AI 관련 user-agent 46개 나열, `Disallow: /kr/`                          |
| 조선일보              | GPTBot, DeepSeekBot 차단                                                |
| 한겨레                | GPTBot, ClaudeBot, Bytespider 차단                                      |
| **law.go.kr**         | **`User-agent:*` / `Allow: /`** (완전 개방)                             |
| **data.go.kr**        | 14 bytes, 규칙 없음                                                     |
| toss·baemin·kakaocorp | AI 봇 규칙 없음                                                         |

두 가지가 읽힌다.

**첫째, 콘텐츠가 자산인 곳은 잠그고 공공데이터는 열려 있다.** 뉴스사와 UGC 플랫폼은 예외 없이 차단했고, 법령·공공데이터 포털은 열어뒀다.

**둘째 — 이게 더 중요한데 — brunch는 검색봇은 허용하면서 AI 학습 봇만 막는다.** 업계가 이미 **"크롤러"와 "에이전트"를 다른 것으로 구분하기 시작했다**는 뜻이다. 색인되어 사람을 내 사이트로 데려오는 건 환영이고, 내용을 흡수해 내 사이트에 올 이유를 없애는 건 거부다.

$\lambda$를 올려도 이 문은 열리지 않는다. **렌더링은 기술 결정이지만 `robots.txt`는 사업 결정이기 때문이다.**

다만 여기서 과장하면 안 된다. RFC 9309는 스스로 이렇게 못 박는다.

> "**These rules are not a form of access authorization.**"[^30]

`robots.txt`는 요청이지 접근 통제가 아니다. 그리고 Perplexity는 공식 문서에서 사용자 요청 기반 페처에 대해 "**Since a user requested the fetch, this fetcher generally ignores robots.txt rules**"라고 명시한다.[^31] OpenAI도 `ChatGPT-User`에 대해 "Because these actions are initiated by a user, **robots.txt rules may not apply**"라고 쓴다.[^32] **학습 크롤러와 사용자 대행 에이전트는 규칙이 다르다.**

---

## 7. 그래서 인터페이스는 둘로 갈라진다

렌더링으로도 안 되고 `robots.txt`도 사업 결정이라면, 에이전트는 어디로 들어오는가. **HTML이 아닌 별도 표면**이다.

- **MCP(Model Context Protocol)** — 현재 프로토콜 버전은 `2026-07-28`.[^33] 2025년 12월 9일 Anthropic이 **Linux Foundation 산하 Agentic AI Foundation**에 기증했다(Block·OpenAI 공동 창립, Google·Microsoft·AWS·Cloudflare·Bloomberg 지원).[^34]
- **llms.txt** — Jeremy Howard가 2024년 9월 3일 제안했다.[^35]

여기서 정직해야 한다. **둘 다 아직 표준화 기구의 표준이 아니다.**

llms.txt는 자기 문서에서 스스로를 "**a proposal** to standardise on…", "this **informal overview**"라고 규정한다.[^35] IETF·W3C·WHATWG 어디의 승인도 확인되지 않는다. MCP는 벤더 중립 재단이 호스팅하는 오픈 프로토콜이지만, IETF·W3C·ISO에 제출됐다는 근거는 찾지 못했다. 게다가 Linux Foundation은 "**will not dictate the technical direction of MCP**"라고 명시한다.[^36]

대조가 선명하다. **`robots.txt`는 RFC 9309라는 IETF Standards Track 문서를 가졌다**(2022년 9월, Martijn Koster가 1994년 정의한 것을 표준화).[^30] 에이전트 시대의 인터페이스에는 아직 그런 게 없다.

그리고 자주 혼동되는 점 하나 — **자기 문서용 llms.txt를 발행하는 것**과 **남의 llms.txt를 읽겠다고 약속하는 것**은 전혀 다르다. 전자를 하는 벤더는 많지만, 후자를 공식 문서로 약속한 주요 AI 벤더는 찾지 못했다.

---

## 8. 화면이 사라지지 않는 이유 — 법이 사람을 요구한다

에이전트가 API로 직접 일한다면 UI는 왜 남는가? **책임 때문이다.** 그리고 이건 내 추측이 아니라 현행법 조문이다.

「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」(AI 기본법)은 **2026년 1월 22일부터 시행 중**이다(2025-01-21 공포, 법률 제20676호 → 2026-01-20 일부개정 법률 제21311호, 동일자 시행).[^37]

**제34조 제1항** — 고영향 인공지능 사업자의 의무 6가지 중 4호가 이것이다.

> "**4. 고영향 인공지능에 대한 사람의 관리·감독**"[^38]

또한 2호는 "인공지능이 도출한 최종결과, **최종결과 도출에 활용된 주요 기준**, 학습용데이터의 개요 등에 대한 **설명 방안의 수립·시행**", 5호는 "**조치의 내용을 확인할 수 있는 문서의 작성과 보관**"이다.[^38]

**제31조(투명성 확보 의무)**는 더 직접적이다.

> ① "제품 또는 서비스가 **해당 인공지능에 기반하여 운용된다는 사실을 이용자에게 사전에 고지**하여야 한다."
> ② "그 결과물이 **생성형 인공지능에 의하여 생성되었다는 사실을 표시**하여야 한다."[^39]

그리고 시행령이 표시 방법으로 **"1. 사람이 인식할 수 있는 방법 / 2. 기계가 판독할 수 있는 방법"** 둘 다를 규정한다.[^37]

여기서 구조가 드러난다. 법은 **사람이 보는 표면**(고지·설명·감독)과 **기계가 읽는 표면**(기계 판독 표시)을 **동시에** 요구한다. 7장에서 말한 이중 표면이 법률 층위에서도 똑같이 나타난다.

그러니 화면은 없어지지 않는다. **에이전트가 결정하더라도 사람이 승인하고, 그 승인이 남는 자리가 화면이다.** 앞 글에서 "법정 서식은 리포팅툴 영역"이라고 했던 것과 같은 원리다 — 자동화가 아무리 진행돼도 **법적 책임이 발생하는 지점에는 사람이 서 있어야 한다.**

다만 과장은 금물이다. **AI 기본법에 "AI 에이전트"를 직접 정의하거나 규율하는 조문은 없다.** 가장 가까운 것이 제2조 제2호의 "**다양한 수준의 자율성과 적응성**을 가지고 주어진 목표를 위하여 … 예측, 추천, 결정 등의 결과물을 추론하는" 인공지능시스템 정의다.[^40] "AI 기본법이 에이전트를 규율한다"고 쓰면 과장이다.

---

## 9. 접근성 투자가 그대로 에이전트 인프라가 된다

3장에서 naver.com의 원시 HTML에 남은 유일한 텍스트가 접근성 스킵 링크였다는 걸 봤다. 우연이 아니다.

MDN이 시맨틱 마크업의 이점을 나열한 목록을 보자. **1번과 2번이 나란히 있다.**

> "Some of the benefits from writing semantic markup are as follows:
>
> - **Search engines will consider its contents as important keywords** to influence the page's search rankings
> - **Screen readers can use it as a signpost** to help visually impaired users navigate a page"[^41]

검색엔진과 스크린리더가 같은 목록에 있다. **둘 다 "눈 없이 구조를 이해해야 하는 소비자"이기 때문이다.** 에이전트는 그 목록에 추가되는 세 번째 항목이다.

WAI-ARIA 1.2 초록은 이걸 더 근본적으로 말한다.

> "**Accessibility of web content requires semantic information about widgets, structures, and behaviors**, in order to allow assistive technologies to convey appropriate information… These semantics are designed to allow an author to **properly convey user interface behaviors and structural information to assistive technologies in document-level markup.**"[^42]

"document-level markup으로 구조 정보를 전달한다" — 에이전트가 원하는 것과 정확히 같다.

국내 제도도 이미 있다. 국가표준 **KS X OT0003**(한국형 웹 콘텐츠 접근성 지침 2.2)은 2005년 최초 제정 후 2022년 12월 28일 개정됐고, W3C WCAG 2.1을 기초로 **원칙 4 / 지침 14 / 검사항목 33**으로 구성된다.[^43] 국제 표준 쪽은 **WCAG 2.2가 2024년 12월 12일 W3C Recommendation**이 됐고, WCAG 3.0은 **아직 Working Draft**다(2026년 3월 3일자).[^44]

다만 법적 강제력은 정확히 구분해야 한다. 「지능정보화 기본법」 제46조는 **제1항에서 국가기관등에 "접근성을 보장하여야 한다"(의무)**를 지우지만, **제2항에서 민간 지능정보서비스 제공자에게는 "노력하여야 한다"(노력의무)**를 지운다.[^21] 민간 사이트에 대한 강제 의무로 읽으면 틀린다.

**실무적 함의**: 접근성 작업은 "언젠가 감사 때문에 해야 하는 일"이 아니라 **AX 시대의 인프라 투자**다. 시맨틱 마크업, ARIA 역할, 명확한 랜드마크는 스크린리더와 에이전트에게 동시에 값을 낸다. 예산 항목이 하나인데 결과가 둘이면, 그건 하기 쉬운 결정이다.

---

## 10. 코퍼스 실측 — 여기서 반전이 하나 더 나온다

이 시리즈의 신호는 매번 직접 측정하는 것이었다. 이번에도 쟀다.

측정 과정에서 그 자체로 징후적인 일이 있었다. **Stack Overflow 태그 페이지를 `curl`로 받으면 이제 HTTP 403이 돌아온다** — "Just a moment... Enable JavaScript and cookies to continue"라는 Cloudflare 봇 체크다. 그래서 **공식 Stack Exchange API**로 다시 측정했다(2026-08-12).[^45]

| 태그          | 질문 수     |
| ------------- | ----------- |
| javascript    | 2,522,113   |
| java          | 1,914,698   |
| **reactjs**   | **473,924** |
| angular       | 306,418     |
| spring-boot   | 150,322     |
| vue.js        | 107,927     |
| **jsp**       | **51,320**  |
| next.js       | 41,556      |
| jsf           | 35,462      |
| servlets      | 32,934      |
| jakarta-ee    | 29,194      |
| thymeleaf     | 9,278       |
| **puppeteer** | **8,006**   |
| htmx          | 603         |

React는 JSP의 약 9.2배다. 예상대로다. 그런데 여기 반전이 있다.

**JSP(51,320)는 Puppeteer(8,006)의 6.4배다.**

바로 앞 글에서 "바이브코딩으로 PDF"의 코퍼스가 얼마나 얇은지 보였는데, **LLM은 JSP를 그 PDF 자동화보다 6배 이상 잘 안다.** "레거시라서 AI가 JSP를 모른다"는 통념은 틀렸다. 20년간 쌓인 질문·답변이 그대로 학습 코퍼스이기 때문이다.

이게 실무에 주는 함의는 뒤집힌 것이다. **레거시 JSP 시스템의 유지보수와 이관 분석은 LLM이 의외로 잘하는 영역이다.** 오히려 최신 기술일수록 코퍼스가 얇아 LLM이 헤맨다(htmx 603, Next.js 41,556). 신기술이라 AI가 잘할 것이라는 직관은 자주 틀린다.

---

## 11. 그래서 무엇을 하나

| 상황                                          | 판단                                                                                                                                   |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| 공개 정보를 담은 페이지(제품·문서·공공데이터) | **$\lambda \approx 1$로 유지.** SSR/SSG/RSC. 구글이 직접 "not all bots can run JavaScript"라고 썼다                                    |
| 로그인 뒤 대시보드·내부 도구                  | CSR로 충분. 에이전트가 볼 일이 없다                                                                                                    |
| 에이전트가 실제로 써야 하는 기능              | **HTML을 고치지 말고 API·MCP를 내라.** 화면 긁기는 최후 수단                                                                           |
| 콘텐츠가 사업 자산                            | `robots.txt` 정책을 **의식적으로** 결정하라. 학습 봇/검색 봇/사용자 대행 페처는 각각 다른 문제다                                       |
| 고영향 AI를 쓰는 업무                         | 사람의 관리·감독이 **법적 의무**(AI기본법 제34조①4). 승인 UI와 감사 로그를 설계에 넣어라                                               |
| 접근성 예산                                   | AX 인프라 예산으로 재분류하라. 결과가 둘인데 비용은 하나다                                                                             |
| 레거시 JSP 자산                               | **폐기부터 정하지 마라.** 스펙상 필수 기술이고 LLM 지원도 두껍다. 다만 신규 기능 계획은 없으니 **신규 개발의 기본값으로는 부적절**하다 |

JSP와 React 중 무엇을 고르냐는 질문은, 사실 **"이 페이지의 $\lambda$가 얼마여야 하는가"**로 바꿔 물으면 대부분 저절로 풀린다.

---

## 12. 이 글이 말하지 못하는 것

- **$\lambda$는 내가 이 글을 위해 만든 지표다.** 표준 용어도, 인용 가능한 선행 정의도 아니다.
- **"AI 크롤러는 자바스크립트를 실행하지 않는다"고 쓰지 않았다.** OpenAI·Anthropic·Perplexity 공식 문서는 user-agent·IP 대역·robots.txt 처리까지 상세히 문서화하면서도 **JS 렌더링 여부는 긍정도 부정도 하지 않는다.**[^31][^32][^46] 이를 주장하는 글들은 제3자 측정에 의존하는데 나는 그 원문을 1차 검증하지 않아 수치를 쓰지 않았다. 논지는 **구글·빙의 1차 진술만으로** 세웠다.
- **에이전트가 웹의 주 소비자가 될 것이라는 전제 자체가 검증되지 않은 가정이다.** 이 글은 그 전제 위에서 좌표를 그렸을 뿐, 전제를 입증하지 않았다.
- **「지능정보화 기본법」 제46조 원문을 law.go.kr에서 직접 대조하지 못했다.** 3장에서 실측한 그 이유 때문이다. 조문 텍스트는 제3자 법령 DB로만 확인했으므로, 인용의 정확성은 국가 공식 원문 대비 한 단계 낮다.
- **Jakarta EE 11의 릴리스 날짜는 공식 소스가 두 개다** — 사양 문서 헤더는 "March 10, 2025", 보도자료·릴리스 페이지는 "June 26, 2025". 어느 쪽이 정오인지 설명하는 공식 문서를 찾지 못해 병기했다.[^22][^47]
- **Jakarta Pages 4.0 사양 문서 자체(PDF/HTML)를 열지 못했다.** 사양 페이지에 문서 링크가 없고 통상 경로는 404다. 그래서 릴리스 날짜 대신 **Release Review 투표 종료일(2024-06-04)**만 인용했다.[^23]
- **AX의 최초 용례는 확정하지 못했다.** 2024-12-30 과기정통부 보도자료가 내가 확인한 가장 이른 정부 공식 문서일 뿐, "최초"가 아니다.
- **조주완 LG전자 CEO가 "RX"를 사용한 사례는 찾지 못했다.** 그가 자사 채널에서 정의한 것은 AX다. Accenture의 AX 약어 사용 여부도 미확인이라 "글로벌 컨설팅사 전부"라고 일반화하지 않았다.
- 코퍼스·robots.txt·HTML 측정치는 **2026-08-12 시점 값**이며 변한다. 측정 방법은 본문에 적어뒀으니 재현 가능하다.

---

## 마무리

세 편을 관통하는 하나의 질문이 있었다. **생산성은 어디서 오는가.**

첫 글의 답은 "자유도를 줄이거나 늘려서"였다. 둘째 글의 답은 "문제를 정확히 분류해서"였다. 이번 답은 이것이다 — **소비자가 누구인지 알아야 한다.**

JSP는 사람만 보던 시대의 도구다. React CSR은 사람의 상호작용을 극대화하려고 기계 가독성을 버렸다. RSC는 그걸 되찾는 중이다. 그런데 정작 웹은 지금 에이전트에게 문을 잠그고 있고, 법은 중요한 결정에 사람이 서 있으라고 요구한다.

그래서 AX 시대의 프론트엔드 질문은 "무엇으로 만드나"가 아니다. **"이 화면은 누구를 위한 것이고, 기계가 읽어야 할 것은 어디에 따로 내놓을 것인가."**

마지막으로 이 글에서 가장 오래 남았으면 하는 사실 하나. **웹 접근성을 규정한 법률의 국가 공식 페이지가, 자바스크립트 없이는 자기 조문을 보여주지 않는다.** AX를 논하기 전에 고칠 것이 아직 많다.

---

## References

[^1]: 과학기술정보통신부 보도자료, 「인공지능 대전환(AX, AI Transformation)을 주도할 대한민국 디지털 혁신 기술」, 2024-12-30 (1차·공식). <https://www.msit.go.kr/bbs/view.do?bbsSeqNo=94&nttSeqNo=3185327&sCode=user> — 본문은 hwpx 첨부에만 있어 제목까지만 인용.

[^2]: 과학기술정보통신부, 「2026년도 업무계획」, 2025-12 (1차·공식). 대한민국 정책브리핑 <https://www.korea.kr/news/policyFocusView.do?newsId=148956404&pkgId=49500827>

[^3]: MSIT, "2026 Work Plan" 영문판 (1차·공식). <https://www.msit.go.kr/eng/bbs/view.do?bbsSeqNo=42&mId=4&nttSeqNo=1205&sCode=eng>

[^4]: LG전자 뉴스룸, 2025-07 (1차·공식 자사 채널). <https://live.lge.co.kr/2507-lg-timesquare-3/> — 동일 문서의 생산성 30% 목표 등 수치는 [벤더 주장]이라 본문에 인용하지 않음.

[^5]: Gartner, "AI roadmap" 등 (1차·기관 공식). <https://www.gartner.com/en/articles/ai-roadmap> — "AI transformation"을 풀어 쓰며 AX 약어 미사용.

[^6]: IDC 리서치 서비스명 (1차·기관 공식). <https://my.idc.com/getdoc.jsp?containerId=US54450625>

[^7]: McKinsey, "The state of AI: how organizations are rewiring to capture value", 2025 (1차·기관 공식 PDF). <https://www.mckinsey.com/~/media/mckinsey/business%20functions/quantumblack/our%20insights/the%20state%20of%20ai/2025/the-state-of-ai-how-organizations-are-rewiring-to-capture-value_final.pdf>

[^8]: Deloitte, _State of AI in the Enterprise 2026_ (1차·기관 자체 설문, 응답 3,235명). <https://www.deloitte.com/content/dam/assets-shared/docs/about/2025/state-of-ai-2026-global.pdf>

[^9]: Chalmers University 논문 (1차·학술). <https://research.chalmers.se/publication/530881/file/530881_Fulltext.pdf>

[^10]: 노무라종합연구소(NRI) 영문 저널, 2026-03-23 (1차·기관 공식). <https://www.nri.com/en/media/journal/20260323.html>

[^11]: LG CNS 배포문, 2026-04-01 (1차·공식, 작성자 LG CNS). <https://www.newswire.co.kr/newsRead.php?no=1031488> — 연합뉴스 보도 <https://www.yna.co.kr/view/AKR20260401054100017> [제3자]

[^12]: 머니투데이, 2026-07-09 [제3자 보도]. <https://www.mt.co.kr/tech/2026/07/09/2026070910392279587> — SK AX 자사 개별 보도자료 URL은 확보하지 못함.

[^13]: 삼성전자 배포문, 2026-07-21 (1차·공식, 작성자 삼성전자). <https://www.newswire.co.kr/newsRead.php?no=1038993> — 연합뉴스 <https://www.yna.co.kr/view/AKR20260721046100003> [제3자]. 삼성 자사 도메인 개별 URL은 확보하지 못함.

[^14]: 산업통상자원부, 제4차 지능형로봇 기본계획 공고(공고 제2024-028호) 및 보도자료 (1차·공식). <https://www.motie.go.kr/kor/article/ATCLc01b2801b/69079/view> · <https://www.motie.go.kr/kor/article/ATCL3f49a5a8c/168485/view> — 이 범위에서 "RX" 용례 없음(negative finding, 첨부 본문 전문 통독은 아님).

[^15]: NVIDIA Glossary, "Generative Physical AI" (1차·벤더 공식). <https://www.nvidia.com/en-us/glossary/generative-physical-ai/>

[^16]: NVIDIA Blog, CES 2025 (2025-01-07) (1차·벤더 공식). <https://blogs.nvidia.com/blog/ces-2025-jensen-huang/>

[^17]: NVIDIA Newsroom, CES 2026 (2026-01-05) (1차·벤더 공식). <https://nvidianews.nvidia.com/news/nvidia-releases-new-physical-ai-models-as-global-partners-unveil-next-generation-robots>

[^18]: 본 블로그, 「PDF 한 장의 값」, 2026-08-12. <https://myoungsoo7.github.io/2026/08/12/pdf-report-tools-vs-vibe-coding-pdf/>

[^19]: Google Search Central, "Understand JavaScript SEO basics" (1차·벤더 공식). <https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics>

[^20]: Bing Webmaster Blog, 2018-10 (1차·벤더 공식). <https://blogs.bing.com/webmaster/october-2018/bingbot-Series-JavaScript,-Dynamic-Rendering,-and-Cloaking-Oh-My> · 2019-10 evergreen Bingbot <https://blogs.bing.com/webmaster/october-2019/The-new-evergreen-Bingbot-simplifying-SEO-by-leveraging-Microsoft-Edge>

[^21]: 「지능정보화 기본법」 제46조(장애인·고령자 등의 지능정보서비스 접근 및 이용 보장). 국가법령정보센터 <https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=233999> — **해당 페이지가 client-rendered라 조문 원문을 직접 대조하지 못함**(본문 3장 실측). 조문 텍스트는 제3자 법령 DB로 확인 [비권위]: <https://casenote.kr/법령/지능정보화_기본법/제46조>

[^22]: Jakarta EE Platform 11 사양 원문 §9.7 (1차·공식 표준). <https://jakarta.ee/specifications/platform/11/jakarta-platform-spec-11.0.html>

[^23]: Jakarta Pages 4.0 사양 페이지 (1차·공식 표준). <https://jakarta.ee/specifications/pages/4.0/> · 스펙 인덱스 <https://jakarta.ee/specifications/pages/>

[^24]: Jakarta Pages 4.1 릴리스 플랜 (1차·공식 표준). <https://jakarta.ee/specifications/pages/4.1/>

[^25]: Spring Boot 공식 레퍼런스, "JSP Limitations" 및 "Template Engines" (1차·벤더 공식). <https://docs.spring.io/spring-boot/reference/web/servlet.html#web.servlet.embedded-container.jsp-limitations>

[^26]: Spring Boot 3.5 레퍼런스 (1차·벤더 공식). <https://docs.spring.io/spring-boot/3.5/reference/web/servlet.html#web.servlet.embedded-container.jsp-limitations> — "Undertow does not support JSPs" 문장은 이 버전 문서에만 존재.

[^27]: React 공식 문서, "Server Components" (1차·벤더 공식). <https://react.dev/reference/rsc/server-components>

[^28]: React Blog, "React v19", 2024-12-05 (1차·벤더 공식). <https://react.dev/blog/2024/12/05/react-19> · 버전 현황 <https://react.dev/versions>

[^29]: React 공식 문서, `renderToPipeableStream` (1차·벤더 공식). <https://react.dev/reference/react-dom/server/renderToPipeableStream>

[^30]: RFC 9309, "Robots Exclusion Protocol", IETF Standards Track, 2022-09 (1차·공식 표준). <https://www.rfc-editor.org/rfc/rfc9309.html>

[^31]: Perplexity 공식 크롤러 문서 (1차·벤더 공식). <https://docs.perplexity.ai/docs/resources/perplexity-crawlers>

[^32]: OpenAI 공식 봇 문서 (1차·벤더 공식). <https://platform.openai.com/docs/bots>

[^33]: Model Context Protocol 공식 사양 및 버전 정책 (1차·벤더 공식). <https://modelcontextprotocol.io/docs/learn/versioning> · <https://modelcontextprotocol.io/specification/2026-07-28>

[^34]: Anthropic, "Donating the Model Context Protocol…", 2025-12-09 (1차·벤더 공식). <https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation> · Linux Foundation 보도 <https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation>

[^35]: llmstxt.org, "The /llms.txt file, v2" (1차·원저자). <https://llmstxt.org/> · 최초 제안 <https://www.answer.ai/posts/2024-09-03-llmstxt>

[^36]: MCP Blog, "MCP joins the Agentic AI Foundation", 2025-12-09 (1차·공식). <https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/>

[^37]: 「인공지능 발전과 신뢰 기반 조성 등에 관한 기본법」 제정·개정문 및 현행 연혁 (1차·법령). <https://www.law.go.kr/LSW/lsRvsDocListP.do?chrClsCd=010202&lsId=014820&lsRvsGubun=all> — [시행 2026. 1. 22.] [법률 제21311호, 2026. 1. 20., 일부개정]. 시행령 [시행 2026. 7. 21.] [대통령령 제36506호]

[^38]: 동법 제34조(고영향 인공지능 안전성·신뢰성 확보 조치) (1차·법령). <https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0034&lsiSeq=282791&urlMode=lsScJoRltInfoR>

[^39]: 동법 제31조(인공지능 투명성 확보 의무) (1차·법령). <https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0031&lsiSeq=282791&urlMode=lsScJoRltInfoR>

[^40]: 동법 제2조(정의) (1차·법령). <https://www.law.go.kr/LSW/lsSideInfoP.do?docCls=jo&joBrNo=00&joNo=0002&lsiSeq=282791&urlMode=lsScJoRltInfoR>

[^41]: MDN Web Docs, "Semantics" (1차·벤더 공식). <https://developer.mozilla.org/en-US/docs/Glossary/Semantics>

[^42]: W3C, "Accessible Rich Internet Applications (WAI-ARIA) 1.2", W3C Recommendation 2023-06-06 (1차·공식 표준). <https://www.w3.org/TR/wai-aria-1.2/>

[^43]: 국립전파연구원, 「한국형 웹 콘텐츠 접근성 지침 2.2」 KS X OT0003:2022, 2022-12-28 개정 (1차·공식 표준). <https://www.rra.go.kr/ko/reference/kcsList_view.do?nb_seq=5247&nb_type=6> · 한국지능정보사회진흥원(NIA) 개정 안내 <https://www.nia.or.kr/site/nia_kor/ex/bbs/View.do?bcIdx=25083&cbIdx=90549>

[^44]: W3C, "WCAG 2.2", W3C Recommendation 2024-12-12 (1차·공식 표준). <https://www.w3.org/TR/WCAG22/> · WCAG 3.0 Working Draft 2026-03-03 <https://www.w3.org/TR/wcag-3.0/>

[^45]: Stack Exchange API v2.3 `/tags/{tag}/info`, 2026-08-12 직접 측정. <https://api.stackexchange.com/2.3/tags/jsp/info?site=stackoverflow>

[^46]: Anthropic 공식 크롤러 문서 (1차·벤더 공식). <https://privacy.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler>

[^47]: Eclipse Foundation, "Jakarta EE 11 Released" (1차·공식). <https://jakarta.ee/news/jakarta-ee-11-released/> · 릴리스 목록 <https://jakarta.ee/release/>
