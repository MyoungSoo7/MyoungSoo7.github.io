---
layout: post
title: "AI 상태 데이터 온톨로지 — 가용성·탐색성·신뢰성·기계판독성은 나란한 네 항목이 아니다"
date: 2026-09-03 18:55:00 +0900
categories: [data, AI]
tags:
  [
    온톨로지,
    FAIR,
    DCAT,
    PROV-O,
    Croissant,
    aipref,
    메타데이터,
    machine-actionable,
  ]
---

데이터에 온톨로지를 씌우자는 제안은 대개 네 개의 명분을 함께 들고 온다. **가용성**(쓸 수
있는가), **탐색성**(찾을 수 있는가), **신뢰성**(믿을 수 있는가), **기계판독성**(기계가 읽을 수
있는가). 네 개가 나란히 적히면 체크리스트처럼 보이고, 체크리스트처럼 보이면 넷을 따로따로
채울 수 있을 것 같아진다.

그게 이 글이 반박하려는 지점이다. 네 축은 병렬 항목이 아니라 **한 방향으로만 흐르는
사슬**이고, 사슬은 항상 같은 자리에서 끊어진다. 그리고 이건 사변이 아니라 이미 10년째
측정되고 있는 사실이다.

먼저 확인해 둘 것 하나. 이 네 축은 새로 만든 분류가 아니다. 2016년에 [Wilkinson 등이
*Scientific Data*에 발표한 FAIR 원칙](https://doi.org/10.1038/sdata.2016.18)이 정확히 이
네 개를 Findable / Accessible / Interoperable / Reusable 이라는 이름으로 15개 하위 원칙까지
쪼개 놓았다. 그러니 "AI 시대에 맞는 새 온톨로지 원칙"을 설계하려는 시도는, 시작하기 전에
자기가 이미 있는 것을 다시 그리고 있는지부터 확인해야 한다.

---

## 0. FAIR 은 사람이 아니라 기계를 위해 쓰였다

FAIR 논문에서 자주 인용되지 않지만 이 글의 뼈대가 되는 문장이 있다. 저자들은 자기 원칙이
동료 이니셔티브와 무엇이 다른지를 이렇게 못 박았다.

> Distinct from peer initiatives that focus on the human scholar, the FAIR Principles put
> specific emphasis on enhancing the ability of machines to automatically find and use the
> data.
> — Wilkinson et al., 2016

그리고 그 '기계가 쓴다'는 상태를 이진값이 아니라 연속체로 정의했다. 처음 보는 디지털
객체를 만난 자율 에이전트가 (a) 객체의 **타입**을 식별하고, (b) 메타데이터를 심문해 지금
자기 과업에 **유용한지** 판단하고, (c) 라이선스·동의·접근 제약을 보고 **사용 가능한지**
판단하고, (d) 사람이 하듯 **적절한 행동을 취하는** 능력 — 이 넷을 얼마나 지원하느냐가
machine-actionability 의 정도다.

이 정의를 그대로 읽으면 우리 네 축의 순서가 저절로 나온다. (a)(b)는 탐색성, (c)는 가용성,
(d)는 신뢰성이 받쳐야 가능하고, **넷 전부가 기계판독성 위에서만 성립한다.** 기계판독성은
네 번째 항목이 아니라 나머지 셋이 서 있는 바닥이다.

FAIR 원칙 15개를 축별로 다시 배치하면 이렇다.

| 축         | FAIR 원칙                                                                                                                                                       | 기계에게 요구하는 것                                             |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 탐색성     | F1 전역 고유·영속 식별자 / F2 풍부한 메타데이터 / F3 메타데이터가 데이터 식별자를 명시 / F4 검색 가능한 자원에 색인                                             | "이게 무엇인가"를 크롤링 없이 답할 것                            |
| 가용성     | A1 식별자로 표준 프로토콜을 통해 회수 / A1.1 프로토콜은 개방·무료·보편 구현 가능 / A1.2 필요 시 인증·인가 절차 지원 / A2 데이터가 사라져도 메타데이터는 남을 것 | "가져올 수 있는가"와 "가져가도 되는가"를 분리해 답할 것          |
| 기계판독성 | I1 형식적·공유된 지식표현 언어 / I2 어휘 자체도 FAIR 할 것 / I3 다른 (메타)데이터로의 **한정된**(qualified) 참조                                                | 링크에 "무슨 관계인지"까지 실어 보낼 것                          |
| 신뢰성     | R1 정확하고 관련 있는 속성으로 풍부히 기술 / R1.1 명확한 사용 라이선스 / R1.2 **상세한 provenance** / R1.3 도메인 커뮤니티 표준 준수                            | "누가·무엇으로·어떻게 만들었는가"를 주장이 아니라 데이터로 낼 것 |

원문 15개 항목은 [논문 Box 2](https://www.nature.com/articles/sdata201618)에 그대로 있다.

---

## 1. 가용성 — "선언된 가용성"은 가용성이 아니다

가용성은 실무에서 늘 두 개의 질문이 붙어 있는데 서로 다른 층이다.

1. **회수 가능한가** — HTTP 로 GET 이 되는가. FAIR 의 A1 계열.
2. **써도 되는가** — 라이선스·동의·용도 제한. FAIR 의 R1.1.

1번은 거의 공짜다. URL 하나면 끝나고, 리포지터리가 대신 해준다. 문제는 2번인데, 지금까지
2번은 사람이 읽는 문서(약관 페이지, README 의 한 문단)에만 있었다. AI 학습 데이터
논쟁이 터진 자리가 정확히 여기다.

이걸 기계판독 가능하게 만들려는 진행 중인 표준이 IETF 의 **AI Preferences (aipref)**
워킹그룹이다. [WG 헌장](https://datatracker.ietf.org/wg/aipref/charter/)은 산출물을 셋으로
정의한다 — 선호를 표현하는 **어휘**, 그 선호를 콘텐츠에 **부착**하는 방법(RFC 8615 의
well-known URI, RFC 9309 의 robots.txt, HTTP 응답 헤더 등), 그리고 여러 선호가 충돌할 때의
**조정 방법**.

어휘 초안([draft-ietf-aipref-vocab](https://datatracker.ietf.org/doc/draft-ietf-aipref-vocab/),
편집자 Keller & Thomson(Mozilla), Standards Track 의도, 2026년 9월 현재 아직 RFC 아닌
Internet-Draft)의 데이터 모델은 놀랄 만큼 단순하다. 용도 카테고리마다 값이 셋 —
`allowed` / `disallowed` / `unknown` — 이고, **선호 표명이 없으면 전부 `unknown`** 이다.
충돌 조정 규칙도 한 줄이다. 하나라도 disallow 가 있으면 disallow, 아니면 하나라도 allow 가
있으면 allow, 그 외에는 unknown. 직렬화는 HTTP Structured Fields 의 Dictionary 에 `y`/`n`
토큰을 싣는 형태다.

여기서 이 글이 강조하고 싶은 건 어휘 자체가 아니라 **헌장이 명시한 out-of-scope 목록**이다.
같은 문서가 다음 네 가지를 범위 밖으로 못 박는다.

- 선호의 **기술적 강제**(technical enforcement)
- 크롤러의 **인증·인가**
- 선호에 관한 **레지스트리** 수립
- AI 학습에 대한 **감사(auditing)와 투명성 조치**

즉 표준이 완성돼도 나오는 것은 *기계가 읽을 수 있는 선언*이지 *지켜지는 규칙*이 아니다.
가용성 축에 온톨로지를 씌운다는 것은 "이 데이터는 학습에 써도 된다"를 **검증 가능하게
만드는 일이 아니라, 기록 가능하게 만드는 일**이다. 이 둘을 같은 칸에 적으면 나중에
"우리는 기계판독 가능한 라이선스를 붙였다"는 문장이 감사 통과의 근거처럼 오용된다.

---

## 2. 탐색성 — 식별자에 기생한다

탐색성은 네 축 중 유일하게 **남이 대신 해주는** 축이다. 데이터를 Zenodo 나 Hugging Face 에
올리면 DOI 든 리포 ID 든 영속 식별자(F1)가 붙고, 랜딩 페이지에 구조화 메타데이터가 박히고,
검색엔진이 색인한다(F4).

구체적으로 어떤 어휘인지도 정해져 있다. [Google 의 Dataset 구조화 데이터
문서](https://developers.google.com/search/docs/appearance/structured-data/dataset)는
Dataset Search 가 **schema.org 의 `Dataset` 마크업, 또는 그에 상응하는 W3C DCAT 구조**를
읽는다고 명시한다(CSVW 기반은 실험적 지원). 즉 F4 는 추상 원칙이 아니라 "JSON-LD 를 페이지에
박아라"라는 구체적 지시로 이미 번역돼 있다.

그 DCAT 도 지금은 3판이다. [DCAT 3 은 2024년 8월 22일 W3C
Recommendation](https://www.w3.org/TR/vocab-dcat-3/)으로 나왔고, 2판 대비 추가된 것이
정확히 이 글의 뒤쪽 축들과 맞물린다 — 배포본의 다이제스트를 담는 `spdx:checksum`,
버전 관계를 표현하는 `dcat:version`·`dcat:previousVersion`·`dcat:hasCurrentVersion`,
그리고 시계열 데이터를 위한 `dcat:DatasetSeries`.

체크섬과 버전이 _탐색_ 어휘에 뒤늦게 추가됐다는 사실이 시사적이다. 카탈로그는 원래 "무엇이
있는가"만 답했는데, 이제 "지금 내가 받은 이 바이트가 그때 그것인가"까지 답하라는 요구를
받고 있다. 탐색성이 신뢰성 쪽으로 밀려 들어간 흔적이다.

---

## 3. 신뢰성 — provenance 는 문장이 아니라 그래프여야 한다

신뢰성은 FAIR 에서 R1.2 한 줄, "(메타)데이터는 상세한 provenance 와 연결된다"로 요약된다.
문제는 이 한 줄이 실무에서 거의 항상 **자연어 문장**으로 채워진다는 것이다. "2025년 3분기
운영 DB 에서 추출 후 정제함" 같은 문장은 사람에게는 충분하고 기계에게는 0 이다.

이걸 그래프로 적는 표준은 이미 13년째 있다. [PROV-O 는 2013년 4월 30일 W3C
Recommendation](https://www.w3.org/TR/prov-o/)이고, 네임스페이스는
`http://www.w3.org/ns/prov#` 이다. 시작점(Starting Point) 어휘는 클래스 셋뿐이다.

- `prov:Entity` — 대상이 된 것 (데이터셋, 파일, 레코드)
- `prov:Activity` — 그것을 만든 처리 (추출, 정제, 라벨링, 증강)
- `prov:Agent` — 그 처리에 책임을 지는 주체 (사람, 조직, `prov:SoftwareAgent`)

세 개다. "AI 데이터 계보를 위한 온톨로지를 새로 설계하자"는 회의를 열기 전에, 이 세 클래스로
자기 파이프라인의 한 단계를 적어 보면 대개 회의가 필요 없어진다. 필요한 건 새 어휘가 아니라
**Activity 를 누가 기록할 것인가**라는 조직 결정이다.

ML 쪽에는 이 층을 데이터셋 단위로 감싼 포장이 따로 나왔다. MLCommons 의
[**Croissant**](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)(1.0, 2024년
3월 1일)는 schema.org 를 `@vocab` 으로 쓰는 JSON-LD 로 ML 데이터셋을 기술해서, 같은 기술
하나로 PyTorch·TensorFlow·JAX 로더가 동일하게 읽도록 한다. 명세가 스스로 밝히는 목표에
discoverability·portability·reproducibility 와 함께 **responsible AI** 가 들어가 있고,
RAI 확장 어휘는 데이터 생애주기·라벨링·참여형 시나리오·안전성/공정성 평가·추적성·규제
준수·포용 등 7개 용례를 겨냥한다.

정리하면 신뢰성 축의 도구는 이미 층이 갖춰져 있다.

| 무엇을 신뢰하려는가            | 표준                         | 형태                  |
| ------------------------------ | ---------------------------- | --------------------- |
| 받은 바이트가 그 바이트인가    | DCAT 3 `spdx:checksum`       | 다이제스트            |
| 이 버전이 그 버전인가          | DCAT 3 `dcat:version` 계열   | 버전 그래프           |
| 어떤 처리를 거쳤는가           | PROV-O Entity/Activity/Agent | 계보 그래프           |
| 학습용으로 어떻게 만들어졌는가 | Croissant + RAI 확장         | JSON-LD 데이터셋 기술 |

**빠진 칸이 없다.** 그런데도 신뢰성은 현장에서 가장 안 되는 축이다. 다음 절이 그 이유다.

---

## 4. 기계판독성 — 사슬이 끊어지는 자리는 항상 여기다

여기가 이 글의 핵심 주장이고, 다행히 주장으로 남기지 않아도 된다. 여러 독립 조사가 같은
모양의 결과를 낸다.

**(1) 표준 저자들이 자기 도구로 직접 재봤을 때.** Wilkinson 등은 2019년 _Scientific Data_
에 [FAIR Evaluator](https://doi.org/10.1038/s41597-019-0184-5)를 발표했다. 사람이 채점하는
설문이 아니라, 식별자 하나만 주면 에이전트가 자원을 방문해 **"기계가 무엇을 보는지"** 를
보고서로 내는 자동 평가다. 저자들이 이 프레임워크를 만들며 명시한 태도 자체가 중요하다 —
"이 자원은 FAIR 한가?"라는 질문은 FAIRness 가 이진값이라는 잘못된 전제를 깔고 있으므로,
평가는 **자동 에이전트가 실제로 탐지할 수 있는 특성이 무엇인지**를 물어야 한다는 것이다.

같은 팀의 [2018년 프리프린트](https://doi.org/10.1101/418376)(peer review 전 단계임을 밝힌다)
는 Dataverse·Dryad·Zenodo 를 실제로 돌려 보고 이렇게 적었다. 세 곳 모두에서 DOI 는 HTML
페이지로 해소됐고 content negotiation 에 응답하지 않았으며, Dryad 와 Dataverse 의 임베디드
메타데이터에는 데이터로 가는 명시적 링크가 없어 **F3 위반**이었다. 저자들의 결론 문장:
"the continuing focus on infrastructures created for humans versus those created for
machines."

**(2) 유럽 리포지터리 39곳을 설문했을 때.** EOSC Association 의 FAIR Metrics and Digital
Objects Task Force 가 2025년 4~9월에 39개 유럽 연구데이터 리포지터리를 조사해 2026년 4월에
낸 [보고서](https://zenodo.org/records/19431150)의 요지는 이렇다. 데이터셋 단위 PID,
라이선스, 메타데이터 검증 같은 **기초 능력은 널리 구현돼 있으나**, 데이터 *수준*의
재사용성에서는 격차가 크다 — 기계판독 가능한 라이선스 제한적, **표준화된 provenance 채택
저조**, 파일 단위 PID 불완전, 기계판독 가능한 정책 노출 미미. 보고서 자신의 표현으로
"discovery-oriented FAIR implementation" 과 "reuse-ready practices" 사이의 지속적 간극이다.
(자기보고 기반이라는 한계는 보고서가 스스로 밝힌다.)

**(3) 데이터셋 384건을 자동 채점했을 때.** 에너지 연구 도메인 데이터셋 384건을 F-UJI 와
FAIR-Checker 두 도구로 평가한 [학술대회 논문](https://doi.org/10.52825/ocp.v9i.3302)(2026,
동료심사 저널 아닌 proceedings 임을 밝힌다)의 결과도 같은 모양이다. 두 도구 모두에서
**Findability 와 Accessibility 가 가장 높고 Interoperability 가 가장 낮았으며**, 저자들은
그 원인을 "기계판독 가능한 메타데이터 스키마와 통제 어휘의 제한적 활용"으로 지목한다.

세 조사의 도메인도 방법도 시점도 다른데 결론의 **모양이 같다**. 앞의 두 축(탐색성·가용성)은
잘 되고, 뒤의 두 축(기계판독성·신뢰성)은 안 된다.

### 왜 항상 같은 자리인가

이유는 기술이 아니라 **누가 비용을 내는가**다.

- 탐색성과 가용성은 **리포지터리가 대신 낸다.** 업로드만 하면 PID 가 붙고 HTTP 로 열린다.
  데이터 생산자가 추가로 할 일이 거의 없다.
- 기계판독성과 신뢰성은 **생산자만 낼 수 있다.** 어떤 컬럼이 무슨 개념인지, 이 링크가 무슨
  관계인지(FAIR I3 이 요구하는 것은 링크가 아니라 _한정된_(qualified) 참조다), 어떤 Activity
  가 어떤 Entity 를 만들었는지 — 이건 데이터를 만든 사람 머릿속에만 있고 대행이 불가능하다.

그래서 네 축은 나란하지 않다. **비용 구배를 가진 사슬**이고, 사슬은 대행 불가능한 쪽에서
끊어진다. AI ready 라는 말이 붙은 데이터가 실제로 걸리는 지점도 여기다. 검색은 되는데
스키마의 의미가 없고, 다운로드는 되는데 계보가 없다.

---

## 5. 그런데 그 측정조차 믿을 만하지 않다

이 글이 근거로 쓴 "FAIR 점수" 자체에도 한계를 붙여 둬야 공정하다.

Candela·Mangione·Pavone 이 _Data Science Journal_ 에 낸 [FAIR Assessment
Conundrum](https://doi.org/10.5334/dsj-2024-033)(2024, 동료심사)은 FAIR 평가 도구 20개와
지표 1180개를 수집해 분석했다. 결과 중 두 가지가 특히 무겁다.

- **345개 지표**에서 "그 지표가 재겠다고 선언한 것"과 "실제로 재는 것"이 어긋났다.
- 저자들의 결론은 절대적 FAIRness 평가가 "impractical and, arguably, nonsensical" 하다는
  것이다. 원칙은 의도적으로 다면적·비규범적으로 쓰였는데 지표는 구현을 하나 골라야 하므로,
  같은 원칙이 도구마다 다르게 채점된다.

그러니 앞 절의 세 조사는 **"F/A 는 잘 되고 I/R 은 안 된다"는 방향성의 반복 관측**으로 읽어야
하고, 점수의 절대값이나 도구 간 비교로 읽으면 안 된다. 이 방향성은 세 조사가 서로 다른 도구·
방법·도메인에서 같은 모양을 냈다는 점에서 유의미하지만, "우리 조직 FAIR 점수 72점" 같은
수치는 그 자체로 의미가 약하다.

---

## 결론 — 세 가지

**하나. 새 온톨로지를 설계하기 전에, 없는 게 정말 어휘인지 확인하라.** 네 축의 어휘는
이미 다 있다. 탐색성은 schema.org `Dataset` / DCAT 3, 가용성은 A1 계열 + aipref(진행 중),
신뢰성은 PROV-O + DCAT 3 checksum/version + Croissant RAI, 기계판독성은 그 전부를 JSON-LD
로 내는 것. 새 어휘를 만들면 FAIR 의 I2("어휘 자체도 FAIR 할 것")를 스스로 위반하면서
시작하게 된다.

**둘. 네 축을 병렬 KPI 로 두지 마라.** 병렬로 두면 조직은 싼 것부터 채운다. PID 붙이고
검색 노출시키고 "가용성 100%, 탐색성 100%" 를 보고한 뒤, 정작 기계가 쓸 수 없는 데이터가
남는다. 위 세 조사가 관측한 게 정확히 그 패턴이다. 실제로 물어야 할 질문은 하나로
줄어든다 — **"처음 보는 에이전트가 이 데이터셋의 컬럼 의미와 생성 계보를, 사람에게 묻지
않고 알아낼 수 있는가."** 답이 아니오면 앞의 두 축 점수는 무의미하다.

**셋. 신뢰성은 기술 결정이 아니라 조직 결정이다.** PROV-O 의 클래스는 세 개뿐이고 13년째
안정적이다. 안 되는 이유가 어휘 부족인 적은 없었다. 안 되는 이유는 파이프라인의 각 단계에서
`prov:Activity` 를 기록할 책임자가 지정돼 있지 않기 때문이다. 이 한 칸을 비워 둔 채로
온톨로지를 도입하면, 결과물은 provenance 필드가 `null` 인 아주 잘 설계된 스키마다.

---

## References

- Wilkinson, M. D. et al. (2016). _The FAIR Guiding Principles for scientific data management and stewardship._ Scientific Data 3:160018. <https://doi.org/10.1038/sdata.2016.18>
- Wilkinson, M. D. et al. (2019). _Evaluating FAIR maturity through a scalable, automated, community-governed framework._ Scientific Data 6:174. <https://doi.org/10.1038/s41597-019-0184-5>
- Wilkinson, M. D. et al. (2018). _Evaluating FAIR-Compliance Through an Objective, Automated, Community-Governed Framework._ bioRxiv **프리프린트**(동료심사 전). <https://doi.org/10.1101/418376>
- W3C (2024-08-22). _Data Catalog Vocabulary (DCAT) — Version 3._ W3C Recommendation. <https://www.w3.org/TR/vocab-dcat-3/>
- W3C (2013-04-30). _PROV-O: The PROV Ontology._ W3C Recommendation. <https://www.w3.org/TR/prov-o/>
- MLCommons (2024-03-01). _Croissant Format Specification, Version 1.0._ <https://docs.mlcommons.org/croissant/docs/croissant-spec.html>
- IETF AI Preferences (aipref) WG Charter. <https://datatracker.ietf.org/wg/aipref/charter/>
- Keller, P. & Thomson, M. (Ed.). _A Vocabulary For Expressing AI Usage Preferences._ draft-ietf-aipref-vocab — **Internet-Draft**(2026-09 현재 RFC 아님). <https://datatracker.ietf.org/doc/draft-ietf-aipref-vocab/>
- Google Search Central. _Dataset (Dataset, DataCatalog, DataDownload) structured data._ <https://developers.google.com/search/docs/appearance/structured-data/dataset>
- Candela, L., Mangione, D. & Pavone, G. (2024). _The FAIR Assessment Conundrum: Reflections on Tools and Metrics._ Data Science Journal 23:33. <https://doi.org/10.5334/dsj-2024-033>
- EOSC Association FAIR Metrics and Digital Objects Task Force (2026-04-05). _Report on Repository Support for Data-Level Interoperability / Reusability._ Zenodo. **자기보고 설문 기반.** <https://zenodo.org/records/19431150>
- Lu, L., Wein, A. & Werth, O. (2026). _Measuring FAIR Data Compliance in German Energy Research._ Open Conference Proceedings **(학술대회 논문, 저널 동료심사 아님).** <https://doi.org/10.52825/ocp.v9i.3302>

**근거의 한계.** 이 글의 "F/A 는 되고 I/R 은 안 된다"는 관측은 세 개의 서로 다른 조사에서
반복됐지만, 그중 하나는 자기보고 설문이고 하나는 학술대회 논문이며, 셋 다 연구데이터
리포지터리를 대상으로 한다. 기업 내부 데이터 플랫폼이나 상용 AI 학습 데이터 파이프라인을
같은 방법으로 전수 측정한 중립적 조사는 확인하지 못했다. 위 결론을 사내 데이터 플랫폼에
그대로 옮길 때는 이 외삽을 감안해야 한다.
