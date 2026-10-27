---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-10-28"
date: 2026-10-28 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각:** 2026-10-28 08:30 KST. 10-27부터 10-28 새벽 사이에 공개된 것을 주로 모았다.
> **이전 브리핑과 겹쳐서 뺀 항목:**
> - Anthropic S-1
> - Claude Code v2.1.311
> - LangGraph 1.2.18
> - CrewAI 1.15.30
> - MLflow 3.17.2
> - Langfuse v4.70.x
> - Phoenix 20.26.1
> - LY Flava MCP Hub
> - AWS 10-26 발표분 (GPT-6.1 Terra, ASG launch-before-terminate, IAM Identity Center)
> - GCP 10-26 발표분
> - MCP SEP-2792
> - Spring Boot 4.2.0-RC1 · 4.1.2
> - K8s v1.37.1
> - 위시켓 159287·158812 등 기존 공고
>
> PHP2Shell은 새 진전(오탐 정정)이 있어서 그 부분만 다시 다룬다.

**표기 규칙**
- **[사실]** 1차·공식 출처에서 확인한 내용. 공식 발표, 보안 권고, 릴리스 노트, 공고 원문이 여기에 해당한다.
- **[벤더 주장]** 벤더나 작성 회사가 스스로 낸 수치·비교. 제3자가 재현했는지는 확인하지 못했다.
- **[보도]** 언론 보도로만 확인한 내용.
- **[추론]** 위 사실을 바탕으로 필자가 해석한 내용.
- **[미확인]** 출처를 찾지 못했거나 검증하지 못한 내용.

---

## 오늘의 핵심

1. **Anthropic Frontier Red Team이 실제 소프트웨어 취약점 탐색·익스플로잇 결과를 공개했다 (10-27).**
   - 공개되지 않은 내부 모델로 공격 체인 5개를 만들었다.
   - Chrome에서는 원클릭 RCE 체인까지 만들었다.
   - Chrome 156 기준으로 CVE 62건이 배정·패치됐다. 모두 critical 또는 high 등급이고, 그중 13건은 샌드박스 탈출이다. [1]
2. **CISA가 KEV에 2건을 추가했다 (10-27, 연방기관 조치 기한 11-10).**
   - Adobe Commerce/Magento 파일 업로드 취약점 CVE-2026-48356
   - Google Brotli 취약점 CVE-2026-111497 [7][8][9]
3. **Kubernetes가 Workload Conformance WG를 출범시켰다 (10-27). 같은 날 v1.34는 EOL이 됐다.**
   - WG의 목표는 "이 워크로드가 클러스터에서 제대로 동작하는가"를 시험할 수 있는 사양과 도구를 만드는 것이다. [11][12]
4. **Anthropic이 미 연방조달청(GSA)과의 파트너십을 넓혔다 (10-27).**
   - Claude Enterprise, Claude for Government, API를 40% 할인한다.
   - 할인 대상은 주·지방·부족·준주 정부까지다. [2]
5. **토스가 「SNAP」을 공개했다 (10-27).** LLM 호출 가운데 반복되는 판단을 자동 학습한 소형 모델로 넘기는 구조다.
   - 운영 중 하루 요청의 33~37%를 소형 모델이 처리한다 [벤더(자사) 주장].
   - 그래서 Jev 섹션(8)과 함께 읽을 만하다. [20]

---

## 1. AI & ML

**Anthropic — 실제 소프트웨어의 취약점 발견·익스플로잇 (Frontier Red Team, 10-27)** [사실]
- 공개되지 않은 내부 모델로 공격 체인 5개를 만든 과정을 공개했다. [1]
- 대표 사례는 Chrome 원클릭 RCE다. 다음 결함을 차례로 엮었다.
  - V8 힙 손상
  - V8 샌드박스 탈출
  - CacheStorage 경쟁 조건
  - FedCM use-after-free
- Chrome 156 기준으로 CVE 62건이 배정·패치됐다. 전부 critical·high 등급이고, 그중 13건이 샌드박스 탈출이다.
- 공개 정책은 "패치까지 90일 + 45일"이다. 확대된 Cyber Verification Program도 함께 언급했다.
- [추론] 방어 측(패치 주기·SBOM·브라우저 업데이트 강제)의 부담이 커질 신호다.

**Anthropic — GSA 파트너십 확대 (10-27)** [사실]
- Claude Enterprise, Claude for Government, API를 40% 할인한다. 모든 제품 표면에 적용하고, 주·지방·부족·준주 정부도 대상이다. [2]
- Claude for Government(FedRAMP High)는 9-30부터 GA 상태다. Claude Enterprise는 FedRAMP 20x 절차로 Moderate 인가를 진행 중이다.
- "약 500개 정부기관 사용", "약 10억 달러 절감 추정"은 **[벤더 주장]**이다.

**Anthropic — Claude를 활용한 신약 개발 초기 성과 (10-27)** [사실]
- 파트너 6곳의 사례를 정리했다. BigHat, BMS, Divergence Labs, Enveda, Generate Biomedicines, The Column Group이다. [3]
- 대부분 전임상 단계다. 임상 성과로 읽으면 안 된다.

**Claude Code v2.1.312 (10-27 20:24 UTC)** [사실] [4]
- Claude apps gateway에 `oidc.user_id_claim`을 추가했다. 예를 들어 Entra의 `oid`를 사용자 식별자로 쓸 수 있다.
- 매우 큰 CLAUDE.md를 앞부분만 읽은 채 덮어쓰던 버그를 고쳤다.
- `cd` 후 스킬을 찾지 못하던 문제를 고쳤다.
- 잘못된 명령 이름을 넣으면 `claude -p`가 아무것도 출력하지 않던 문제를 고쳤다.
- Bedrock·Vertex·Foundry·Mantle에서 인식하지 못한 모델명은 짧은 시스템 프롬프트를 쓴다. 전체 프롬프트를 유지하려면 `CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT=0`을 설정한다.
- [보도] The Register는 체인지로그에 없는 환경변수 `CLAUDE_CODE_EVEN_MORE_DANGEROUSLY_SKIP_PERMISSIONS`가 있다고 보도했다. 공식 문서에서는 확인하지 못했으므로 **[미확인]**이다. 쓰지 않는 것을 권한다. [5]

**Google DeepMind — Genie 4 (10-27)** [사실]
- 월드 모델 Genie 4를 발표했다. 신뢰 테스터에게만 제한적으로 공개한다. [6]

**뇌과학/BCI**
- 10-27~28 사이에 새로 공개된 논문이나 발표는 **부재**다.
- 가장 최근 것은 10-22 Brain 논문(임상적 무반응 환자 41명 중 13명이 BCI 제어에 성공)과 10-23 npj 리뷰다. 이전 브리핑 범위라 다시 싣지 않는다.

## 2. 에이전트 프레임워크 (LangGraph · CrewAI · Devin)

- LangGraph: 1.2.18(10-26) 이후 새 릴리스는 **없음**.
- CrewAI: 1.15.30 이후 새 릴리스는 **없음**.
- Devin: 10-27~28 사이 공식 발표를 확인하지 못했다 **[미확인]**.
- 대신 볼 것: Anthropic 정렬팀의 10-27 연구 「AI 에이전트는 전문가의 판단을 어떻게 바꾸는가」. 9번 섹션에서 다룬다. [10]

## 3. Kubernetes & Cloud Native

**Workload Conformance Working Group 출범 (K8s 블로그, 10-27)** [사실]
- 작성자는 Nabarun Pal(Broadcom)이다. [11]
- 산출물은 세 가지다.
  - 마이너 버전별 워크로드 적합성 사양
  - 시험 방법
  - 업스트림 적합성 도구
- 범위는 보안, 중단(disruption), 리소스, 네트워킹, 스토리지, API 사용, 관측성이다.
- 모든 요구사항에는 객관적인 테스트가 있어야 한다.
- [추론] 지금의 Certified Kubernetes는 *클러스터*의 적합성을 본다. 이 WG는 그 반대편인 *워크로드*를 보는 것으로 읽힌다. 헬름 차트나 오퍼레이터 배포자가 체크리스트로 쓸 수 있게 될 가능성이 있다.

**릴리스 상태** [사실]
- **v1.34는 2026-10-27에 End of Life가 됐다.** 아직 1.34 클러스터가 있다면 업그레이드 계획이 필요하다. [12]
- 현재 최신 패치는 1.37.1과 1.36.5(9-15)다. 1.37의 EOL 예정일은 2027-10-28이다. [12]
- v1.38 일정 [13]
  - 문서 placeholder PR 마감: 10-29 AoE
  - beta.0: 11-04
  - 코드 프리즈: 11-16 AoE
  - 정식 릴리스 목표: 12-16

## 4. 보안

**CISA KEV 2건 추가 (10-27, 연방기관 기한 2026-11-10)** [사실] [7][9]
- **CVE-2026-48356 — Adobe Commerce/Magento 무제한 파일 업로드**
  - 패치는 APSB26-73이다. 이 공지는 원래 7-14에 나왔다.
  - Adobe 공지 당시에는 "실제 악용을 알지 못한다"고 했다. 이번 KEV 등재로 악용이 확인됐다. [8]
  - 영향 버전 예: Adobe Commerce 2.4.9, 2.4.8-p5 이하.
- **CVE-2026-111497 — Google Brotli**
  - CISA는 "unchecked return value"로 분류했다.
  - 수정은 brotli v1.2.1(10-21)이다. 릴리스 노트는 이 결함을 "out-of-bounds write로 원격 코드 실행 가능"이라고 설명한다. [14]
  - [추론] Brotli는 웹 서버, 브라우저, 언어 런타임에 정적·동적으로 많이 포함돼 있다. 그래서 *직접 의존성*뿐 아니라 *벤더 번들*까지 확인해야 한다.

**PHP2Shell 후속 — 오탐 정정** [보도]
- KEV 등재(10-26)는 이전 브리핑에서 다뤘다. 이번에는 새로 나온 진전만 적는다.
- Nextgov(10-27) 보도 내용 [15]
  - Sophos가 보고서를 정정했다. 관측한 것은 *성공한 악용*이 아니라 스캔과 실패한 시도였다.
  - Unit 42는 유럽 정부기관 공격을 이 결함과 연결한 귀속을 철회했다.
- 연방기관 조치 기한은 그대로 10-29다.
- [추론] 성공한 악용 사례가 줄었다고 해서 패치 우선순위가 내려가지는 않는다. KEV 등재는 유지되고 있다.

**Anthropic Frontier Red Team 결과** — 1번 섹션 참고. [1]

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

**AWS (10-27)** [사실]
- **ElastiCache for Valkey — 기존 클러스터의 내구성 모드 변경 지원.** 동기·비동기 중에서 고를 수 있다. 비동기 모드는 최대 10초 분량의 데이터를 잃을 수 있다고 명시돼 있다. [16]
- **Aurora Serverless — Aurora PostgreSQL 최대 384 ACU(768 GiB).**
  - 지원 PG 버전: 18.4 / 17.10 / 16.14 / 15.18 / 14.23
  - Platform Version 4 기준이다. [17]

**Google Cloud (10-27)** [사실]
- **VMware solution on Google Cloud** (자체 관리 VCF): 22개 리전에서 GA. [18]
- **Google TPU를 OCI에서 제공:** 2027년부터. [19]
- **Oracle AI Database@Google Cloud:** Data API를 쓰는 Remote MCP Server가 GA. 10번 MCP 섹션과 연결된다. [21]
- **Gemini Robotics ER 2:** 퍼블릭 프리뷰. [22]

**Azure**
- Microsoft Foundry에서 Claude 비용 관리·태깅이 GA됐다는 항목이 있다.
- 다만 공식 Azure Updates 페이지에서 본문을 확인하지 못했다. 그래서 **[미확인]**으로 둔다.

**Naver Cloud**
- 10-27~28 공식 발표 중 이 브리핑 범위에 맞는 항목을 찾지 못했다(**부재**).

## 6. 언어 (Java · Kotlin · Python · Go · Rust 등)

- 10-27~28 사이 주요 언어·프레임워크의 새 정식 릴리스는 **확인되지 않았다**.
- Spring Boot 4.0.9 / 4.1.2 / 4.2.0-RC1(10-23)은 이전 브리핑에서 다뤘다.
- Java 스택과 직접 관련된 오늘 항목은 4번의 Brotli다. JVM 라이브러리에 네이티브 Brotli 바인딩을 쓰고 있다면 버전을 점검할 것.

## 7. 인프라 & Linux

- 오늘의 인프라 체크리스트 [추론]
  1. K8s 1.34 EOL 대응 [12]
  2. Brotli 1.2.1 반영(배포판 패키지와 컨테이너 베이스 이미지) [14]
  3. Magento·PHP 스택 패치 [7][15]
- Aurora Serverless의 상한이 384 ACU로 올라갔다. 그래서 "Serverless로는 큰 OLTP를 못 돌린다"는 전제는 다시 따져볼 만하다 [추론]. [17]

## 9. AI Safety & Alignment

**「AI 에이전트는 전문가의 판단을 어떻게 바꾸는가」 (Anthropic, 10-27)** [사실]
- 저자: Herdağdelen, Joren, Tamkin [10]
- 설계: 분석가 50명이 Claude Code와 함께 판단 문제를 풀었다.
- 결과
  - 분석가는 에이전트가 기우는 쪽을 86% 따랐다.
  - 미리 선호를 밝힌 경우, 에이전트가 반대하면 60%가 입장을 바꿨다. 에이전트가 동의한 경우에 입장을 바꾼 비율은 6%였다.
- [추론] 이 결과는 "사람이 최종 판단한다(human in the loop)"는 통제가 실제로는 에이전트의 제안에 크게 끌려갈 수 있다는 뜻이다. 리뷰 프로세스를 설계할 때는 *에이전트 제안을 보기 전에 사람이 먼저 판단을 기록하는* 방식을 고려할 만하다.

**사이버 역량 공개의 이중성**
- 1번의 Red Team 결과는 방어 목적의 공개다. 그래도 같은 역량이 공격에 쓰일 수 있다는 점을 Anthropic 스스로 Cyber Verification Program 확대로 다루고 있다. [1]

## 10. MCP

- MCP 사양: 최신판은 여전히 2026-07-28이다. 10-27~28 사이 새 개정은 **없다**.
- 새 항목
  - Google Cloud가 **Oracle AI Database@Google Cloud용 Remote MCP Server(Data API)를 GA**했다 (10-27) [사실]. [21]
  - [추론] 데이터베이스 벤더가 MCP 서버를 관리형으로 제공하는 흐름이 이어지고 있다. 권한 범위와 감사 로그 설정을 먼저 볼 것.

## 11. MLOps / 피처 스토어

- MLflow: 3.17.2 이후 새 릴리스는 **없다**.
- 오늘 MLOps 관점의 실사례는 토스 SNAP이다. 14번에서 자세히 다룬다. [20]
  - LLM 호출을 Task Fingerprint로 묶는다.
  - Airflow 일 배치로 소형 모델을 자동 학습한다.
  - confidence 임계값을 넘지 못하면 LLM으로 넘긴다(폴백).
  - 데이터 → 학습 → 배포 → 폴백까지 닫힌 파이프라인이다.

## 12. 에이전트 관측성

- Langfuse와 Arize Phoenix 모두 10-27~28 사이 새 릴리스를 확인하지 못했다.
- Claude Code v2.1.312의 `oidc.user_id_claim`을 쓰면 게이트웨이 단에서 사용자 식별을 IdP 클레임에 맞출 수 있다. 사용자별 사용량·감사 로그를 붙이는 데 쓸 수 있다 [추론]. [4]

## 13. 그린 컴퓨팅

- [사실] Princeton SPIA가 데이터센터와 환경을 다룬 인터뷰를 공개했다 (10-27). [23]
- [보도] 스페인이 데이터센터의 재생에너지 관련 규정을 완화했다는 Bloomberg 보도가 있다. 1차 문서는 확인하지 못했다.
- 10-27에 데이터센터 전력 관련 벤더 보도자료가 몇 건 나왔다(800V 전원 제품, 디지털 트윈 등). 전부 **[벤더 주장]**이고 중립 검증이 **부재**해서 싣지 않는다.

## 14. 국내 기업 기술 블로그 (네카라쿠배당토)

| 회사 | 제목 | 날짜 | 요약 | 링크 |
|---|---|---|---|---|
| 토스 | 손가락 튕기기로 LLM 비용 줄이기 (SNAP) | 2026-10-27 | Selective Native AI Processing. 반복되는 LLM 판단을 Task Fingerprint로 묶고, 소형 모델을 매일 자동 학습해 확신도가 높은 요청만 처리한다. 나머지는 LLM으로 폴백한다. | [20] |
| NAVER D2 | AI 시대의 개발자를 꿈꾸는 학생 개발자에게 | 2026-10-27 | 2018년 글의 후속편. 개발자의 역할이 "AI 에이전트를 관리하는 사람"으로 옮겨간다는 조직·문화 관점의 글이다. | [24] |

**토스 SNAP 수치 — 모두 [벤더(자사) 주장]**
- 검증 세트: 목표 일치율을 99.9%로 두면 요청 100,648건 중 34.74%를 소형 모델이 처리한다. 불일치는 34건이고, 실제 일치율은 99.9028%다.
- 운영
  - 하루 요청의 33~37%를 소형 모델이 처리한다.
  - 약 6일 동안 입력 토큰 약 76억 개와 출력 토큰 약 4,520만 개를 절감했다.
- 지연
  - 598 rps에서 p50 7.24 ms
  - 1,203 rps에서 p50 9.02 ms, p99 15.23 ms

**그 밖의 회사**
- 카카오(최신 10-22), 우아한형제들(10-21), LY(Flava, 이전 브리핑에서 다룸)는 새 글이 없다.
- 당근, 쿠팡, 두나무는 10-27~28 새 글을 확인하지 못했다.
- 이 기간에 장애 회고 글은 **없다**.

## 15. Java/Spring 프리랜서 공고

**오늘 확인된 검증 가능 공고 없음.**

- 수집일: 2026-10-28
- 위시켓 목록 페이지([목록](https://www.wishket.com/project/?q=java))
  - 10-27 등록 공고가 있었지만 Java/Spring 공고는 없었다. GCP TA, React FE, ISO PMO 등이었다.
  - 이 링크는 *목록 페이지*다. 개별 공고 원문이 아니다.
- 아직 모집 중인 Java/Spring 공고(159287, 159170, 158840, 159138)는 모두 이전 브리핑에서 이미 다뤘다. 그래서 다시 싣지 않는다.
- 통신사 기간계 AA 공고(159243)는 10-27에 마감됐다.
- 프리모아, 이랜서: 오늘 새 Java/Spring 공고를 확인하지 못했다.

---

## 8. Jev API & 의사결정 모델 (특별 섹션)

지난 브리핑(10-27)에서는 Jev API를 **[미확인]**으로 두었다. 오늘 공식 문서로 정체를 확인했다. 10-27~28 사이에 새로 나온 소식은 **없다**. 아래는 정의를 정리한 것이다.

**Jev란** [사실]
- TypeSafe의 대표 "System One" 의사결정 모델이다. [25][26]
- 텍스트를 생성하지 않는다. 대신 다음 세 가지 primitive에 대해 **보정된(calibrated) 확률**을 돌려준다.
  - `noul`: 예/아니오
  - `choice`: 선택지 중 고르기
  - `score`: 점수
- 입력은 텍스트만 받는다.
- 엔드포인트: `POST https://api.typesafe.ai/v1/systemone` [27]
- 모델
  - `jev-1.14.0`: 2026-10-14부터 사용 가능
  - Jev 1.13
  - `jev-latest`는 1.14를 가리킨다. [26]
- 가격: 입력 토큰 10억 개당 42달러. 출력 토큰은 무료다. [26]
- 컨텍스트
  - 요청당 64k, 질문당 32k
  - `TypeSafe-Danger-Zone-Long-Context` 헤더를 쓰면 최대 262k까지 늘어난다. [26]
- RLCD로 학습했다. 고객별 파인튜닝은 제공하지 않는다. [25]
- 출시 블로그는 2026-09-15에 나왔다. 여기서 말하는 "두 자릿수 배(two orders of magnitude) 빠름"은 **[벤더 주장]**이다. 중립 제3자 벤치마크는 **부재**다. [28]

**생태계 통합** [사실]
- MLflow 3.17.0(10-06): Jev judge, 트레이싱, 게이트웨이 지원을 추가했다. [29]
- MLflow 3.17.1: `make_judge()`에서 Decision API를 지원한다.
- OpenRouter에 `typesafe/jev-1.13`이 올라와 있다. [30]
- Pydantic AI는 `TypeSafeModel`과 `SystemOneModel`을 제공한다. [31]
- CrewAI 1.15.29(10-23)에는 "offline jev routing and guardrail evaluation runner"가 들어 있다.

**[추론] 토스 SNAP과의 연결**
- 두 접근은 같은 결론을 가리킨다. *쉬운 판단은 작고 보정된 모델에 맡기고, 불확실하면 LLM으로 넘긴다.*
- 차이점은 다음과 같다.

| | SNAP | Jev |
|---|---|---|
| 모델 | 회사 내부에서 태스크별로 자동 학습 | 범용 의사결정 모델을 API로 제공 |
| 특징 | 자사 데이터에 특화 | 확률이 보정돼 있음 |

- 둘 다 보정이 잘 됐는지를 독립적으로 검증한 자료는 **부재**하다.

---

## 사실 · 추론 · 미확인 정리

- **사실**
  - Anthropic Red Team 결과(CVE 62건)와 GSA 40% 할인
  - Claude Code v2.1.312
  - CISA KEV 2건(기한 11-10)과 Brotli v1.2.1
  - K8s Workload Conformance WG 출범과 v1.34 EOL
  - AWS ElastiCache·Aurora 발표, GCP 발표 4건
  - 토스 SNAP과 NAVER D2 글의 존재와 내용
  - Jev의 공식 사양
- **벤더 주장**
  - GSA 10억 달러 절감과 약 500개 기관 사용
  - 토스 SNAP의 처리율·토큰 절감·지연 수치
  - Jev가 "두 자릿수 배 빠름"
- **보도**
  - PHP2Shell 오탐 정정(Nextgov)
  - 숨은 권한 우회 환경변수(The Register)
  - 스페인 규정 완화(Bloomberg)
- **추론**
  - Workload Conformance가 차트·오퍼레이터 체크리스트로 쓰일 가능성
  - Brotli 번들 점검 필요성
  - 에이전트가 판단에 미치는 영향을 줄이는 리뷰 설계
  - SNAP과 Jev의 연결
- **미확인**
  - Azure Foundry의 Claude 비용 관리 GA
  - Devin의 새 소식
  - 환경변수의 공식 지원 여부
  - 당근·쿠팡·두나무의 새 글

---

## References

1. Anthropic, "Discovering and exploiting vulnerabilities in critical, real-world software with Claude", 2026-10-27 — <https://www.anthropic.com/research/discovering-vulnerabilities-with-claude>
2. Anthropic, "Expanding our partnership with GSA", 2026-10-27 — <https://www.anthropic.com/news/expanding-partnership-gsa>
3. Anthropic, "Early progress on accelerating drug development with Claude", 2026-10-27 — <https://www.anthropic.com/research/early-progress-drug-development>
4. GitHub anthropics/claude-code, "v2.1.312", 2026-10-27 — <https://github.com/anthropics/claude-code/releases/tag/v2.1.312>
5. The Register, "Anthropic now lets Claude users jump out of plane without parachute", 2026-10-27 — <https://www.theregister.com/ai-and-ml/2026/10/27/anthropic-now-lets-claude-users-jump-out-of-plane-without-parachute/5305807>
6. Google, "Introducing Genie 4", 2026-10-27 — <https://blog.google/innovation-and-ai/models-and-research/google-deepmind/introducing-genie-4/>
7. CISA, "CISA Adds Two Known Exploited Vulnerabilities to Catalog", 2026-10-27 — <https://www.cisa.gov/news-events/alerts/2026/10/27/cisa-adds-two-known-exploited-vulnerabilities-catalog>
8. Adobe, "Security update available for Adobe Commerce | APSB26-73", 2026-07-14 — <https://helpx.adobe.com/security/products/magento/apsb26-73.html>
9. CISA, "Known Exploited Vulnerabilities Catalog" — <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
10. Anthropic, "How AI agents shape experts' judgment calls", 2026-10-27 — <https://www.anthropic.com/research/agents-judgment-calls>
11. Kubernetes Blog, "Announcing the Workload Conformance Working Group", 2026-10-27 — <https://kubernetes.io/blog/2026/10/27/announcing-workload-conformance-wg/>
12. Kubernetes, "Releases" — <https://kubernetes.io/releases/>
13. Kubernetes Dev, "Release schedule" — <https://www.kubernetes.dev/resources/release/>
14. GitHub google/brotli, "v1.2.1", 2026-10-21 — <https://github.com/google/brotli/releases/tag/v1.2.1>
15. Nextgov/FCW, "CISA gives federal agencies until Thursday to address exploited PHP flaws", 2026-10-27 — <https://www.nextgov.com/cybersecurity/2026/10/cisa-gives-federal-agencies-until-thursday-address-exploited-php-flaws/416838/>
16. AWS What's New, "ElastiCache — changing durability", 2026-10-27 — <https://aws.amazon.com/about-aws/whats-new/2026/10/elasticache-changing-durability/>
17. AWS What's New, "Aurora Serverless supports 384 ACU", 2026-10-27 — <https://aws.amazon.com/about-aws/whats-new/2026/10/aurora-serverless-supports-384-acu/>
18. Google Cloud Blog, "VMware solution on Google Cloud", 2026-10-27 — <https://cloud.google.com/blog/products/infrastructure-modernization/vmware-solution-on-google-cloud/>
19. Google Cloud Blog, "Bringing Google TPUs to Oracle Cloud Infrastructure", 2026-10-27 — <https://cloud.google.com/blog/products/infrastructure/bringing-google-tpus-to-oracle-cloud-infrastructure>
20. 토스 기술 블로그, "손가락 튕기기로 LLM 비용 줄이기", 2026-10-27 — <https://toss.tech/article/snap-llm-cost-reduction>
21. Google Cloud Blog, "Oracle AI Database@Google Cloud: what's new at Oracle AI World", 2026-10-27 — <https://cloud.google.com/blog/products/databases/oracle-ai-databasegoogle-cloud-whats-new-at-oracle-ai-world>
22. Google Cloud Blog, "Gemini Robotics Embodied Reasoning 2 is now available on Google Cloud", 2026-10-27 — <https://cloud.google.com/blog/products/ai-machine-learning/gemini-robotics-embodied-reasoning-2-is-now-available-on-google-cloud>
23. Princeton SPIA, "Behind the headline: data centers and the environment", 2026-10-27 — <https://spia.princeton.edu/news/2026/10/27/behind-headline-data-centers-and-environment>
24. NAVER D2, "AI 시대의 개발자를 꿈꾸는 학생 개발자에게", 2026-10-27 — <https://d2.naver.com/helloworld/1975819>
25. TypeSafe Docs, "System One" — <https://docs.typesafe.ai/concepts/system-one>
26. TypeSafe Docs, "Models" — <https://docs.typesafe.ai/models>
27. TypeSafe Docs, "API" — <https://docs.typesafe.ai/api>
28. TypeSafe Blog, "Introducing System One models and Jev", 2026-09-15 — <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
29. MLflow, "Release 3.17.0", 2026-10-06 — <https://mlflow.org/releases/3.17.0/>
30. OpenRouter Docs, "Jev tutorial" — <https://openrouter.ai/docs/guides/community/jev-tutorial>
31. Pydantic AI Docs, "TypeSafe models" — <https://pydantic.dev/docs/ai/models/typesafe/>
