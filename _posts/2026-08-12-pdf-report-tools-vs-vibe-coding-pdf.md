---
layout: post
title: "PDF 한 장의 값 — 바이브코딩 PDF vs OZ Report·CROWNIX·UbiReport"
date: 2026-08-12 01:45:00 +0900
categories: [engineering, productivity]
tags:
  [
    pdf,
    reporting-tool,
    oz-report,
    crownix,
    ubireport,
    puppeteer,
    vibe-coding,
    css-paged-media,
  ]
---

"PDF 출력이야 요즘 Claude한테 시키면 30분이면 나오는데 왜 리포팅툴을 수천만 원 주고 삽니까."

실제로 자주 듣는 말이고, **부분적으로 맞다.** 그리고 그 '부분'이 정확히 어디까지인지를 아는 사람은 드물다. 이 글은 그 경계선을 그린다.

앞서 [넥사크로·웹스퀘어 vs 바이브코딩 React](/2026/08/12/nexacro-websquare-vs-vibe-coding-react-productivity/)를 썼는데, 이 글은 그것의 **출력물 버전**이다. 화면이 아니라 종이와 PDF로 옮겼을 때 무엇이 달라지는가.

결론부터.

> "PDF 생성"은 하나의 문제가 아니라 **세 개의 다른 문제**다. 바이브코딩은 그중 하나를 아주 잘 하고, 하나는 어렵게 하고, 하나는 **구조적으로 못 한다.** 못 하는 이유는 라이브러리가 부족해서가 아니라 **조판이 고정점 문제인데 브라우저 인쇄 파이프라인에는 반복이 없기 때문**이다.

---

## 1. "PDF 생성"은 세 개의 다른 문제다

한 덩어리로 묶으면 논쟁이 끝나지 않는다. 쪼개자.

**(A) 흐름 문서 (flow document)**
내용 길이가 가변이고 페이지 수가 데이터에 따라 결정된다. 보고서, 계약서, 매뉴얼, 대시보드 스냅샷. HTML/CSS가 원래 이걸 하라고 만들어진 언어다.

**(B) 고정 양식 (fixed form)**
레이아웃이 밀리미터 단위로 고정되어 있고 데이터가 정해진 칸에 들어간다. 세금계산서, 보험 청약서, 관공서 서식, OMR 용지. 한 칸 밀리면 반려된다.

**(C) 혼합 (A+B)**
고정 양식 헤더 + 가변 길이 명세 + **페이지마다 이월되는 소계** + 마지막 페이지에만 나오는 총계·서명란. 거래명세서, 통장, 보험 설계서, 고지서가 전부 여기다.

바이브코딩은 **(A)에서 압도적이고, (B)에서 고전하고, (C)에서 막힌다.** 그리고 기업이 리포팅툴을 사는 이유는 (C) 때문이다.

---

## 2. 왜 (C)에서 막히는가 — 조판은 고정점 문제다

이게 이 글의 핵심이라 천천히 가겠다.

거래명세서 바닥에 "이월: 1,240,000원"을 찍어야 한다고 하자. 이 값을 계산하려면 **이 페이지가 어디서 끊기는지**를 알아야 한다. 그런데 페이지가 어디서 끊기는지는 바닥글의 높이에 의존하고, 바닥글에는 그 값이 들어간다. 마찬가지로 "3 / 12"의 12를 찍으려면 전체 페이지 수를 알아야 하는데, 페이지 번호를 넣으면 레이아웃이 바뀌어 총 페이지 수가 바뀔 수 있다.

즉 레이아웃 $L$과 페이지 분할 $P$가 서로를 참조한다.

$$P = f(\text{content},\ L), \qquad L = g(\text{content},\ P)$$

이건 **고정점(fixed point) 문제**다. 해는 $ (L^*, P^*) = (g(c,P^*),\ f(c,L^*)) $ 를 만족하는 지점이고, 실무에서는 반복으로 푼다.

$$P_{n+1} = f\big(c,\ g(c, P_n)\big) \quad \text{until}\quad P_{n+1} = P_n$$

**전문 조판 엔진은 이 반복을 돈다.** TeX가 그렇고, 밴드형 리포트 엔진이 그렇다. 그래서 "페이지 소계", "이월", "마지막 페이지에만 서명란", "총 페이지 수에 따라 달라지는 표지"가 선언적으로 표현된다.

**브라우저 인쇄 파이프라인에는 이 반복이 없다.** 한 번 레이아웃하고, 페이지 높이로 자른다. 그래서 페이지 의존적인 값은 레이아웃에 참여할 수 없고, **후처리로 주입**하는 수밖에 없다.

Puppeteer의 API가 이 사실을 그대로 드러낸다. `PDFOptions`의 `headerTemplate`/`footerTemplate`에 주입할 수 있는 값은 공식 문서에 **정확히 다섯 개**로 못 박혀 있다.[^1]

| 클래스       | 값               |
| ------------ | ---------------- |
| `date`       | 인쇄 날짜        |
| `title`      | 문서 제목        |
| `url`        | 문서 위치        |
| `pageNumber` | 현재 페이지 번호 |
| `totalPages` | 전체 페이지 수   |

**끝이다.** 페이지 소계도, 이월 합계도, "현재 장(chapter) 제목"도, "이 페이지 마지막 거래일자"도 넣을 자리가 없다. 라이브러리가 게을러서가 아니라 **그 값들은 레이아웃이 끝나기 전에는 존재할 수 없고, 레이아웃에 되먹임될 방법이 없어서**다.

같은 문서의 `tagged`(접근성 태그 PDF)와 `outline`(문서 개요) 옵션에는 **(Experimental)** 표시가 붙어 있다.[^1] 공공 문서 접근성 요건과 정면으로 부딪히는 지점이다. 그리고 공식 `PDFOptions` 목록에 **PDF/A 관련 옵션은 없다.**

---

## 3. 표준이 아직 표준이 아니다

"CSS로 인쇄 조판하면 되지 않나"에 대한 답은 W3C 문서 자체에 있다.

**CSS Paged Media Module Level 3은 아직 W3C Working Draft다.** 최초 발행 1999년 6월 23일, 최신판 2023년 9월 14일 — **24년째 Working Draft**이며 권고안(Recommendation)이 아니다.[^2] 문서 상단에 "Publication as a Working Draft does not imply endorsement by W3C and its Members"가 그대로 붙어 있다.

그 스펙 본문이 직접 이렇게 적는다.

> "However, handling content flowing across pages of differing widths is a relatively complex task, and **is not yet solved in many popular printing implementations (notably, web browsers)**."[^2]

머리글·바닥글에 **실제 내용을 넣는 메커니즘**(`string-set`, `running()`, 각주)은 Level 3이 아니라 **CSS Generated Content for Paged Media Module**에 있는데, 이쪽은 editors' draft 상태로 문서 스스로 "Don't cite this document other than as work in progress"라고 명시한다.[^3] 인쇄 표식용 `marks`·`bleed` 속성은 MDN과 caniuse 모두 **지원 브라우저 없음**으로 표시한다.[^4]

그리고 가장 설득력 있는 증거는 **구현체들의 자기 규정**이다.

- **Paged.js** 공식 문서: 자신을 **"polyfill"**이라고 정의한다 — "a bit of code that implements a feature on web browsers that do not support the feature". 목표로 삼는 W3C 모듈로 CSS Paged Media L3, CSS GCPM, CSS Fragmentation L3을 명시한다.[^5] **폴리필이 존재한다는 것 자체가 브라우저가 구현하지 않았다는 증명이다.**
- **WeasyPrint** 공식 문서: "It is based on various libraries but **not on a full rendering engine like WebKit or Gecko**. The CSS layout engine is written in Python, **designed for pagination**".[^6] 브라우저 엔진이 페이지 조판용이 아니라서 **직접 다시 만들었다**는 자백이다.

---

## 4. 바이브코딩 PDF의 세 갈래와 각각의 벽

실무에서 "AI로 PDF 뽑았다"는 셋 중 하나다.

### (가) 헤드리스 브라우저 인쇄 — Puppeteer / Playwright

가장 흔하다. HTML을 만들고 `page.pdf()`를 호출한다. 문서상 이 메서드는 **`print` CSS 미디어 타입으로 렌더링**하며, `screen` 스타일을 쓰려면 별도로 `emulateMediaType('screen')`을 불러야 한다.[^7] 기본값 `printBackground: false`라 배경색·배경이미지가 **기본으로 빠지고**, `preferCSSPageSize`가 기본 `false`라 **내용이 용지에 맞게 스케일된다**.[^1] 픽셀 퍼펙트를 요구하는 (B)에서 이 두 기본값은 사고의 단골 원인이다.

- **강점**: (A)에서 최고. 웹 화면과 동일한 렌더링, 개발자가 이미 아는 언어
- **벽**: 2장의 고정점 문제, 요청당 브라우저 컨텍스트라는 자원 구조

### (나) 전용 페이지네이션 엔진 — WeasyPrint / Prince / Paged.js

(A)와 (B) 사이를 상당히 메운다. 다만 이건 **"바이브코딩"이라 부르기 어렵다.** CSS Paged Media를 제대로 쓰려면 `@page` 마진 박스 16개, `string-set`, `break-inside`, 명명 페이지를 이해해야 하고, 그건 프론트엔드 지식이 아니라 **조판 지식**이다. LLM에게 "예쁘게 PDF로 뽑아줘"라고 해서 나오는 영역이 아니다.

### (다) 좌표 그리기 — jsPDF / pdf-lib / react-pdf

가장 오해가 많다. jsPDF 공식 문서는 이렇게 적는다.

> "The 14 standard fonts in PDF are limited to the ASCII-codepage. If you want to use UTF-8 you have to integrate a custom font, which provides the needed glyphs. jsPDF supports .ttf-files."[^8]

즉 **한글을 찍으려면 한글 TTF를 base64로 인코딩해 번들에 넣어야 한다.** 그리고 임베드 가능한 포맷은 TrueType뿐이다(WOFF 미지원).[^8] 한글 전체 글리프를 담은 폰트는 수 MB이고, 그게 JS 번들에 들어간다. "일단 만들어봤더니 되더라"가 실서비스에서 무너지는 대표적 지점이다.

---

## 5. 비교 대상은 정확히 무엇인가

이 제품들을 제대로 비교하려면 먼저 **누가 만드는지**부터 확정해야 한다. 여기서 흔히 틀린다.

| 제품                | 제조사                       | 상장          | 확인                                                      |
| ------------------- | ---------------------------- | ------------- | --------------------------------------------------------- |
| **OZ Report**       | **포시에스**(FORCS)          | KOSDAQ 189690 | KIND 사업보고서 원문 확인[^9]                             |
| **Report Designer** | **엠투소프트**(M2SOFT)       | 비상장        | 1997년 자사 제품명, 현 **CROWNIX Report & ERS** 계보[^10] |
| **UBI Report**      | **유비디시전**(Ubi Decision) | 비상장        | 자사 사이트 확인[^11]                                     |

혼동 주의 두 가지. **Report Designer는 M2SOFT의 실제 제품명**이며(1997년 1.0 출시), CLIP report·REXPERT 계열은 **한컴이노스트림(구 클립소프트)** 쪽으로 별개 계보다. 그리고 **유비디시전은 유비케어·유비스마트와 전혀 다른 회사**다.

구조는 셋 다 비슷한 3분할이다 — **디자이너(WYSIWYG) + 서버 + 뷰어**.

- **OZ Report**: JVM 기반 서버, WAS 연동. 출력 PDF/XLS/HWP/TIF 등. 뷰어는 ActiveX(레거시)와 HTML5 병행. 인쇄 명령·부수 지정 파라미터 문서 존재. **Scheduler API** 확인.[^12]
- **CROWNIX Report & ERS**: Java 엔진, Tomcat 8.5/9.0 + JDK 11/17. 출력 PDF/EXCEL/**고정길이 TXT**/WORD/PPT/이미지 + 자체 뷰어 포맷 `.mrr`. Win32 뷰어와 HTML5 뷰어 병행.[^13]
- **UbiReport**: 유비디자이너 + 유비게이트웨이 + HTML5 유비뷰어. Non-ActiveX를 강점으로 내세움(벤더 주장).[^11]

**"고정길이 TXT" 출력**이 눈에 띈다. 이건 웹 개발자에게는 이상해 보이지만, 메인프레임·대외계 연동과 라인프린터 출력이 살아있는 현장의 요구다. 바이브코딩으로 만드는 PDF 파이프라인이 애초에 상정하지 않는 출력 경로다.

---

## 6. 성능 — 양쪽 다 쓸 만한 숫자가 없다

이 글에서 성능 비교표를 만들지 않는 이유를 밝힌다.

- **OZ Report: 공식 성능 수치를 찾지 못했다.**
- **UbiReport: 공식 성능 수치를 찾지 못했다.**
- **CROWNIX 9**(2026-07-01 출시)만 "PDF 생성 및 대용량 문서 처리 성능이 **이전 버전 대비 최대 3배 이상 향상**"이라는 수치가 있는데[^14], 이건 절대 처리량이 아니라 **자사 이전 버전 대비 상대치**이고 비교 버전·데이터셋·하드웨어 등 **측정 조건이 공개되어 있지 않다.** `[벤더 주장]` 이상으로 쓸 수 없다.
- 바이브코딩 쪽도 마찬가지다. "초당 N장" 류의 수치는 문서 복잡도와 하드웨어에 따라 자릿수가 달라져서 조건 없이는 무의미하다.

**그래서 "누가 더 빠른가"는 이 글이 답하지 않는다.** 대신 아키텍처에서 무엇이 비용인지는 말할 수 있다.

헤드리스 브라우저 방식은 PDF 한 장을 위해 **전체 웹 렌더링 엔진**(HTML 파서 + CSS 레이아웃 + JS 런타임 + 합성기)을 띄운다. 이건 (A)에서는 정당한 대가다 — 웹 화면과 똑같이 나오는 값이니까. 하지만 야간 배치로 고지서 수십만 건을 뽑는 작업에서는 **문서당 비용이 곧 총비용**이 된다. WeasyPrint가 "브라우저 엔진을 쓰지 않고 페이지네이션 전용 엔진을 직접 썼다"고 밝힌 것이 이 오버헤드에 대한 업계의 응답이다.[^6]

반대로 리포팅툴은 그 대가로 **웹 화면과 다른 렌더링**을 받아들인다. 미리보기와 실제 출력이 다르다는 오랜 불만이 여기서 나온다.

---

## 7. 생산성의 진짜 차이는 형상관리에 있다

여기가 실무에서 가장 크게 갈리는데 벤더 자료에는 절대 안 나오는 부분이다.

리포트 디자인 산출물은 **소스 저장소가 아니라 벤더의 리포지토리 서버에 산다.** OZ Report 공식 문서를 보면 리포지토리 타입이 네 가지다 — `NONE`(OS 파일시스템), `BUILTIN`(내장 DB), `RDB`(사용자 DB), `HYBRID`. 그리고 결정적인 문장.

> "You are **not able to see** those item files under the repository_files folder when using BUILTIN or RDB type repository because item files are managed in the **internal format** of OZ e-Form Server."[^15]

배포용 파일은 한 술 더 뜬다.

> "This menu **encrypts** and saves item files in the category as the certified distribution file so that the OZ Viewer can recognize them. **Encrypting report files prevents leaking of script sources.**"[^16]

즉 설계상 **소스가 보이지 않는 것이 기능이다.** 스크립트 유출 방지가 목적이니 의도된 동작이지만, 그 대가로 다음이 전부 불가능해진다.

- `git diff` — 무엇이 바뀌었는지 볼 수 없다
- 코드리뷰 / PR 승인 — 리뷰할 텍스트가 없다
- 충돌 해결 — 머지가 아니라 **둘 중 하나를 버려야** 한다
- CI에서의 자동 검증 — 파이프라인이 읽을 수 없다
- 변경 이력 추적 — 벤더 리포지토리의 이력 기능에 종속된다

정직하게 밝혀둘 것: **`.ozr`과 `.mrd` 파일 자체가 바이너리인지 XML/텍스트인지는 공식 문서에서 확인하지 못했다.**(CROWNIX 문서는 "전용 파일 형식"이라고만 적는다.) 하지만 위 인용은 파일 포맷과 무관하게 성립한다 — **권장 운영 구성에서 산출물은 별도 리포지토리 서버가 소유하고, 배포본은 암호화된다.**

반대편은 정확히 뒤집힌다. HTML+CSS 템플릿은 텍스트라 diff·리뷰·PR·CI가 전부 된다. **바이브코딩 진영이 이기는 축은 속도가 아니라 여기다.**

다만 여기에도 함정이 있어서 공평하게 적는다. **텍스트 diff는 렌더링 회귀를 잡지 못한다.** CSS 한 줄이 바뀌어 8페이지가 9페이지가 되고 서명란이 다음 장으로 넘어가는 사고는 diff에 **한 줄로만** 보인다. 이걸 잡으려면 시각 회귀 테스트(렌더링 결과 이미지 비교)가 필요한데, 실제로 붙여둔 팀은 드물다. **리포트 산출물의 진짜 리뷰 대상은 코드가 아니라 출력물이다.**

---

## 8. 코퍼스 — 앞 글과는 다른 결론이 나온다

[앞 글](/2026/08/12/nexacro-websquare-vs-vibe-coding-react-productivity/)에서 LLM 생산성이 공개 학습 코퍼스 밀도에 비례한다는 것을 React(SO 475,990 질문 / GitHub 247,110 스타) 대 넥사크로(스타 10) 대비로 보였다. 같은 측정을 여기서 해보면 **그림이 다르다.**

2026-08-12 직접 측정:

| 항목                          | Puppeteer         | React (참고) | OZ Report / CROWNIX / UbiReport     |
| ----------------------------- | ----------------- | ------------ | ----------------------------------- |
| GitHub 스타                   | **95,422**[^17]   | 247,110      | 벤더 공식 GitHub 조직 **발견 못함** |
| Stack Overflow 전용 태그 질문 | **약 8,100**[^18] | 475,990      | 전용 태그 **확인 못함**(부재 추정)  |

두 가지를 읽어야 한다.

**첫째, 리포팅툴 쪽은 예상대로 사실상 0이다.** 세 벤더 모두 공식 GitHub 조직을 찾지 못했고, GitHub 키워드 검색에서 나오는 `CROWNIX` 계정은 M2SOFT와 무관한 개인 사용자다. 범용 LLM에게 OZ Report 스크립트를 짜라고 하면 문법을 지어낼 것이다.

**둘째 — 그리고 이게 덜 알려진 쪽인데 — Puppeteer도 생각보다 얇다.** SO 질문 수가 React의 **약 1/59**다. "바이브코딩으로 PDF"는 사람들이 상상하는 것만큼 두꺼운 지식 기반 위에 서 있지 않다. React 컴포넌트를 뽑는 것과 같은 급의 신뢰도를 기대하면 틀린다. 인쇄 조판은 **웹 개발 안에서도 변방**이고, 그 변방성이 코퍼스에 그대로 찍혀 있다.

AI 기능 쪽에서는 **CROWNIX 9만** 자연어 기반 보고서 초안 생성, AI 요약·질의응답, MCP 기반 외부 AI 연동을 발표했다(벤더 주장).[^14] OZ Report와 UbiReport의 제품 단위 AI 기능 발표는 **찾지 못했다.**

---

## 9. 법과 표준이 실제로 요구하는 것

전자문서 출력이 규제 영역인 만큼, 1차 출처로 확인된 것만 적는다.

- **「전자문서 및 전자거래 기본법」 제4조(전자문서의 효력)** — 전자문서의 법적 효력 근거 조항(국가법령정보센터 원문 확인).[^19]
- **「부가가치세법 시행령」 제68조** — 전자세금계산서 의무발급 대상 규정(원문 확인).[^20] 다만 **구체적 고정 서식 규격을 정하는 국세청 고시 원문까지는 확인하지 못했다.**
- **PDF/A** — 장기보존 표준 **ISO 19005-1:2005**는 2026년 재확인되어 현행이다.[^21] 국내에서는 국가기록원 기록관리 공공표준 **NAK 30**이 PDF/A-1b를 보존 포맷으로 명시한다.[^22]

여기서 실무적으로 중요한 결론 하나. **공공기록물로 남아야 하는 문서는 그냥 PDF가 아니라 PDF/A여야 한다.** 그런데 앞서 봤듯 Puppeteer 공식 `PDFOptions`에는 PDF/A 옵션이 없고, 접근성 태그(`tagged`)는 Experimental이다. 이 요건이 걸린 문서를 헤드리스 크롬으로 뽑으려면 **생성 후 별도 변환·검증 단계**를 붙여야 하며, 그 단계는 "30분이면 만든다"에 포함되어 있지 않다.

인증 쪽도 조달에서 점수로 환산된다. 포시에스는 OZ e-Form/OZ Report의 **GS인증 1등급** 취득 이력(15-0247, 19-0151, 19-0152)과 CSAP·SA(소프트웨어 접근성) 인증, 전자정부 표준프레임워크 4.2 호환성 확인, 나라장터 종합쇼핑몰 등록을 공개하고 있다.[^23] CROWNIX는 **우수조달물품** 지정이 확인된다.[^24] UbiReport 자체의 GS인증·나라장터 등록 상태는 **확인하지 못했다**(같은 회사의 별개 제품인 '유비도큐'의 2026-08-02 GS 1등급 취득만 확인됨 — 혼동 주의).[^25]

그리고 **세 제품 모두 중립 제3자 기관의 점유율 자료는 부재**했다. "국내 리포팅 시장 1위" 류의 문구는 전부 벤더 주장이다.

---

## 10. 그래서 어디에 무엇을 쓰나

| 상황                                      | 적합                               | 이유                                        |
| ----------------------------------------- | ---------------------------------- | ------------------------------------------- |
| 대시보드 스냅샷, 웹 화면 그대로 PDF       | **헤드리스 브라우저**              | (A). 화면과 동일 렌더링이 곧 요구사항       |
| 사내 보고서·영수증·간단한 명세            | **헤드리스 브라우저**              | (A). $f$가 크고 유지보수 부담 작음          |
| 조판 품질이 중요한 장문 문서(매뉴얼·논문) | **WeasyPrint / Prince / Paged.js** | (A)+(B). 단 조판 지식 필요, 바이브코딩 아님 |
| 법정 고정 서식, 밀리미터 정합             | **리포팅툴**                       | (B). CSS 조판 보증 수준 미달                |
| 이월 소계·페이지 의존 값이 있는 문서      | **리포팅툴**                       | (C). 브라우저 파이프라인에 고정점 반복 없음 |
| 야간 대량 배치(수만~수십만 건)            | **리포팅툴**                       | 문서당 엔진 비용이 총비용 지배              |
| 공공기록물 PDF/A·접근성 태그 필수         | **리포팅툴 또는 전용 변환**        | Puppeteer 옵션 부재 / Experimental          |
| 대외계 고정길이 TXT 동시 출력             | **리포팅툴**                       | 웹 파이프라인이 상정하지 않는 출력 경로     |

**혼합 전략이 현실적이다.** (A)는 헤드리스 브라우저로 내리고 라이선스 좌석을 줄이는 것이 실제로 돈이 된다. 많은 조직이 대시보드 PDF를 뽑겠다고 리포팅툴 라이선스를 쓰고 있는데, 그건 (C)를 위해 산 도구를 (A)에 쓰는 것이다.

그리고 LLM을 리포팅툴 영역에 쓰는 방법이 하나 있다 — **생성이 아니라 독해.** 기존 서식 자산을 목록화하고, 어떤 서식이 어떤 데이터셋을 참조하는지 매핑하고, 이관 범위를 산정하는 작업에는 잘 듣는다. 코퍼스가 없어도 구조 파악은 되기 때문이다.

---

## 11. 이 글이 말하지 못하는 것

- **바이브코딩 PDF와 리포팅툴을 같은 조건에서 잰 중립 벤치마크는 존재하지 않는다.** 이 글도 하지 않았다. 성능 우열을 주장하지 않은 이유다.
- **OZ Report·UbiReport의 공식 성능 수치를 찾지 못했고**, CROWNIX의 "3배" 수치는 측정 조건이 비공개다.
- **`.ozr`·`.mrd` 파일이 바이너리인지 텍스트인지 확인하지 못했다.** 7장의 논지는 파일 포맷이 아니라 공식 문서에 명시된 리포지토리 동작에 근거한다.
- **UbiReport는 셋 중 공개 정보가 가장 적다.** 출력 포맷 목록, 프린터 제어, 배치 기능, 인증 상태를 확인하지 못했다. 이 글의 UbiReport 서술은 나머지 둘보다 근거가 얇다.
- **전자세금계산서 고정 서식을 규정하는 고시 원문과, 보험 전자청약 고정서식의 법적 강제 근거는 찾지 못했다.** 본문에서 "법이 서식을 강제한다"고 단정하지 않은 이유다.
- 코퍼스·스타 수치는 2026-08-12 시점 측정값이며 변동한다.

---

## 마무리

"AI 시키면 30분"은 (A)에서는 대체로 맞다. 그리고 많은 조직이 실제로 (A)를 하면서 (C)의 값을 치르고 있으니, 그 말은 **비용 절감 기회를 정확히 가리키고 있기도 하다.**

하지만 (C)로 넘어가는 순간 문제는 도구가 아니라 **수학**이 된다. 페이지 의존적인 값을 레이아웃에 되먹이려면 고정점 반복이 필요하고, 브라우저 인쇄 파이프라인에는 그 반복이 없다. Puppeteer의 바닥글에 주입할 수 있는 값이 정확히 다섯 개인 것은 API 설계의 게으름이 아니라 **아키텍처의 정직한 노출**이다.

그러니 질문을 이렇게 바꾸는 게 낫다. **"우리 문서는 A인가, B인가, C인가."** 이 하나만 분류해도 도구 선택 논쟁의 대부분이 사라진다.

마지막으로, 앞 글과 다른 결론 하나를 다시 강조한다. React에서 통하던 바이브코딩의 감각을 PDF 조판에 그대로 옮기면 안 된다. **Puppeteer의 Stack Overflow 질문 수는 React의 1/59다.** 인쇄는 웹 개발 안에서도 변방이고, LLM은 변방에서 약하다.

---

## References

[^1]: Puppeteer, `PDFOptions` interface (1차·공식). <https://pptr.dev/api/puppeteer.pdfoptions>

[^2]: W3C, "CSS Paged Media Module Level 3", W3C Working Draft, 2023-09-14 (1차·표준). <https://www.w3.org/TR/css-page-3/> · 발행 이력(1999-06-23 최초): <https://www.w3.org/standards/history/css-page-3/>

[^3]: W3C CSS WG, "CSS Generated Content for Paged Media Module Level 3", editors' draft (1차·표준 초안). <https://drafts.csswg.org/css-gcpm-3/>

[^4]: MDN, "CSS paged media" (1차·문서) <https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Paged_media> · caniuse, "CSS Paged Media (@page)" <https://caniuse.com/css-paged-media>

[^5]: Paged.js, "The big picture" 공식 문서 (1차·공식). <https://pagedjs.org/documentation/1-the-big-picture/>

[^6]: WeasyPrint 69.0 공식 문서 (1차·공식). <https://doc.courtbouillon.org/weasyprint/stable/>

[^7]: Puppeteer, `Page.pdf()` method (1차·공식). <https://pptr.dev/api/puppeteer.page.pdf>

[^8]: jsPDF 공식 README, "Use of Unicode Characters / UTF-8" (1차·공식). <https://github.com/parallax/jsPDF#use-of-unicode-characters--utf-8> · TrueType 한정 임베드: <https://github.com/parallax/jsPDF/pull/3425>

[^9]: 포시에스 사업보고서, KIND 공시 원문 (1차·공시). <https://kind.krx.co.kr/external/2025/09/16/000277/20250916000867/11011.htm> · 회사 공식: <https://kr.forcs.com/>

[^10]: 엠투소프트 공식 사이트 (1차·공식). "1997년 Report Designer 1.0 출시부터 최신 CROWNIX Report & ERS 9까지". <https://m2soft.co.kr/>

[^11]: 유비디시전 공식 사이트 (1차·공식). <https://www.ubidecision.co.kr/> · <https://www.ubireport.com/>

[^12]: 포시에스 공식 문서 (1차·공식) — 서버 실행 <https://www.forcs.com/en/documentation-server/sv_run.html> · 인쇄 명령 <https://www.forcs.com/en/documentation-rv_dev/rv_event_ozprintcommand_html5.htm> · Scheduler API <https://www.forcs.com/en/documentation-api_java/api_sc_java_class_scheduler.html> · 리포트 디자이너 교육자료 <https://www.forcs.com/file/OZReportTrainingBook7.0.pdf>

[^13]: M2SOFT CROWNIX Report 공식 제품 문서 (1차·공식). <https://m2soft.co.jp/crownix-report/>

[^14]: "엠투소프트, CROWNIX 9 출시", IT데일리 2026-07-02 / 디지털타임스 2026-06-30 (제3자 보도, 내용은 벤더 발표). <https://www.itdaily.kr/news/articleView.html?idxno=240166> · <https://www.dt.co.kr/article/12070433>

[^15]: 포시에스, "Repository Server", OZ e-Form Developer 공식 문서 (1차·공식). <https://edu.ozeform.io/server-developer/repository-server>

[^16]: 포시에스, "User Guide for OZ Repository Manager" (1차·공식). <https://www.forcs.com/kr/wp-content/uploads/2024/06/rm.pdf>

[^17]: GitHub `puppeteer/puppeteer` 스타 수, 2026-08-12 측정. <https://github.com/puppeteer/puppeteer>

[^18]: Stack Overflow `puppeteer` 태그 질문 수, 2026-08-12 측정. <https://stackoverflow.com/questions/tagged/puppeteer>

[^19]: 「전자문서 및 전자거래 기본법」 제4조(전자문서의 효력) (1차·법령). 국가법령정보센터 <https://law.go.kr/>

[^20]: 「부가가치세법 시행령」 제68조 (1차·법령). 국가법령정보센터 <https://law.go.kr/>

[^21]: ISO 19005-1:2005, "Document management — Electronic document file format for long-term preservation — Part 1: Use of PDF 1.4 (PDF/A-1)" (1차·표준). 2026년 재확인, 현행. <https://www.iso.org/standard/38920.html>

[^22]: 국가기록원 기록관리 공공표준 NAK 30 (1차·공식). <https://www.archives.go.kr/>

[^23]: 포시에스 공식 연혁·인증 페이지 (1차·공식). <https://kr.forcs.com/company-history/> · 전자정부 표준프레임워크 호환성 관련 보도: ZDNet Korea 2024-08-22, <https://zdnet.co.kr/view/?no=20240822175730>

[^24]: "엠투소프트 우수조달물품 지정", IT데일리 2025-10-22 (제3자 보도). <https://www.itdaily.kr/news/articleView.html?idxno=235873>

[^25]: "유비디시전 유비도큐 컨버터&뷰어 v26 GS인증 1등급", 전자신문 2026-07-31 (제3자 보도). <https://www.etnews.com/20260731000124>
