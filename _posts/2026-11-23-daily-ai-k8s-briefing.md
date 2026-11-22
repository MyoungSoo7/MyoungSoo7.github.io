---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-23"
date: 2026-11-23 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-23 08:30 KST · **수집 범위**: 2026-11-21 ~ 2026-11-22 (주말이라 11-19~20 발표 중 이전 브리핑에서 빠진 항목은 날짜를 따로 적어 포함)
> **표기**: **[사실]** 1차·공식 출처로 확인 · **[보도]** 언론 보도(1차 출처 미공개 부분 포함) · **[벤더 주장]** 벤더 자체 발표·수치 · **[추론]** 필자 해석 · **[미확인]** 텍스트로 검증하지 못함

> **중복 안내**: 11-20~22 브리핑에서 다룬 리만 가설 Lean 증명, Anthropic IPO, Ruby2Shell·GitLab, GPGME, CISA KEV 11-20 추가분, Java4Shell, PHP 8.5.13 보안 릴리스, AWS Quick 플로·웹 경험, CloudWatch Container Insights for EKS, GKE ambient networking, LangGraph 1.2.24, CrewAI 1.15.44, MCP servers v2.5.0, 네이버 D2 ENGINEERING DAY 글, 우아한형제들 CLAYDesign 등은 다시 적지 않았습니다.

## 오늘의 핵심

1. **MONAI Label 0.8.6 보안 릴리스(11-22)** — 의료영상 주석 서버의 경로 조작 취약점 CVE-2026-133968(critical)을 고쳤습니다 [사실]. Amazon 위협 인텔리전스는 중국 연계 공격자의 AI 에이전트가 이 0-day 를 스스로 찾아 악용했다고 밝혔다고 언론이 보도했습니다 [보도].
2. **Spring 대규모 GA 주간(11-19~20)** — Spring Boot 4.2.0, Spring AI 2.1.0, Spring Cloud 2026.0.0, Spring Batch 6.1, Spring Data 2026.1 이 나왔습니다 [사실]. Spring AI 2.1 은 MCP 2026-07-28 과 **DecisionModel API** 를 넣어 8장 특집과 직접 이어집니다.
3. **Ghostscript Upload2Shell(CVE-2026-125396) 공개(11-21)** — Type 1 폰트 로더의 샌드박스 탈출입니다. 수정판 10.08.0 은 9월에 이미 나왔지만 세부가 이제 공개됐습니다 [사실].
4. **Kubernetes v1.38 Deprecations and Removals 블로그 예정일이 오늘(11-23)** 입니다 [사실]. rc.0 은 12-03, GA 는 12-16 예정입니다.
5. **CloudWatch Omni 가 Azure 텔레메트리를 수집(11-21)** — AWS 관측 도구가 Azure 로그·메트릭·트레이스를 직접 받습니다 [사실].
6. **프리랜서** — 위시켓에서 아직 다루지 않은 Java 공고 2건을 확인했습니다. 둘 다 11-09 등록이라 신규는 아닙니다.

---

## 1. AI/ML (Claude·ML/DL·뇌과학/BCI)

### 1-1. Claude 앱: Team·Enterprise 에 computer use(베타) (11-20, 최신 아님)

- **[사실]** Claude Help Center 릴리스 노트에 따르면 11-20 부터 Team·Enterprise 플랜에서 computer use 를 베타로 쓸 수 있습니다 [[1]](#ref-1).
- **[사실]** 같은 날 iOS 26 이상용 Claude 모바일 앱이 새 디자인으로 바뀌었습니다 [[1]](#ref-1).
- **[추론]** 조직 플랜에서 computer use 를 켜면 관리자가 허용 범위와 감사 로그를 먼저 정해 두는 것이 좋습니다. 9장 AI Safety 의 자동 레드팀 항목과 같은 맥락입니다.

### 1-2. Claude Platform 배경 정보 (11-16, 최신 아님)

- **[사실]** 조직 웹훅(베타)에 고객 관리 키 이벤트 `external_key.failed` 와 `external_key.recovered` 가 추가됐습니다 [[2]](#ref-2).

### 1-3. ML/DL·뇌과학/BCI

- 11-21~22 에 1차 출처로 확인한 신규 항목은 없습니다.

## 2. 에이전트 프레임워크 (LangGraph·CrewAI·Devin)

- **[사실]** LangGraph(마지막 릴리스 11-20)와 CrewAI(마지막 릴리스 11-19)는 그 뒤로 **신규 릴리스가 없습니다**. Devin 도 11-21~22 공식 changelog 에 새 항목이 확인되지 않았습니다.
- **[사실] Java 진영: Spring AI 2.1.0 GA (11-20)** [[3]](#ref-3)
  - Session API 가 `ChatMemory` 를 대체합니다. 세션 메모리, 압축(compaction), 회상(recall)을 지원하고 `ChatMemory` 는 deprecated 됐습니다.
  - 사람이 승인해야 실행되는 도구 호출과 턴당 도구 호출 상한이 들어갔습니다. 가드레일 거부는 거부로 표시됩니다.
  - 에이전트 조립·오케스트레이션용 새 프로젝트 **Spring AI Agent** 가 12월 초 인큐베이션을 시작한다고 밝혔습니다.
- **[추론]** 기존에 도구 호출을 상한 없이 돌리던 Spring 기반 에이전트는 2.1 로 올리면 기본 상한에 걸릴 수 있습니다. 업그레이드 노트를 먼저 확인하세요.

## 3. Kubernetes (v1.36·v1.37·v1.38 사이클)

- **[사실]** v1.38 릴리스 일정표 기준으로 **Deprecations and Removals 블로그가 11-23(월)** 에 예정돼 있습니다 [[4]](#ref-4).
  - 문서 마감과 릴리스 하이라이트 마감은 11-24, rc.0 은 12-03, v1.38.0 은 12-16 입니다.
  - 코드 프리즈는 11-17 부터 적용 중입니다.
- **[사실]** LWKD 에 따르면 v1.38.0-beta.0 부터 릴리스가 서명된 SLSA provenance 와 함께 배포됩니다 [[5]](#ref-5).
- **[사실]** 패치 릴리스는 1.37.2·1.36.6(10-28) 이후 새 버전이 없습니다.
- **[추론]** 오늘 올라올 Deprecations 글은 1.38 업그레이드 계획의 1차 체크리스트입니다. 게시되면 다음 브리핑에서 요약하겠습니다.

## 4. 보안

### 4-1. MONAI Label 0.8.6 — CVE-2026-133968 (11-22, 신규)

- **[사실]** Project MONAI 가 11-22 01:29 UTC 에 0.8.6 을 냈습니다 [[6]](#ref-6). 보안 권고 GHSA-qc22-rmgc-vg94(11-18) 내용은 다음과 같습니다 [[7]](#ref-7).
  - `PUT /datastore/image` 와 `/datastore/label` 의 경로 조작(path traversal)으로 임의 위치에 파일을 쓸 수 있습니다. 등급은 critical 입니다.
  - 세션 업로드의 tar 압축 해제 문제도 #1942 에서 함께 고쳤습니다.
  - 인증은 기본값이 꺼져 있습니다(`MONAI_LABEL_AUTH_ENABLE=False`).
  - 조치: `pip install -U monailabel==0.8.6`. 외부에 노출된 서버라면 인증을 켜고 접근을 제한하세요.
- **[보도] AI 에이전트가 0-day 를 찾아 악용** — The Register [[8]](#ref-8), The Hacker News [[9]](#ref-9), SecurityWeek [[10]](#ref-10)
  - Amazon 위협 인텔리전스(CISO CJ Moses)가 중국 연계 공격자의 AI 에이전트(Cairn)가 이 취약점을 스스로 찾아 악용했다고 밝혔다고 보도했습니다.
  - 보도에 따르면 API 파악부터 파일 쓰기까지 약 11분이 걸렸고, 이후 세션에서 Python 시작 파일을 이용해 root 권한을 얻었습니다.
  - 9월 8일부터 약 48시간 동안 동아시아 대학을 노렸고, 귀속 신뢰도는 "중간"이라고 전해졌습니다.
  - Amazon 의 1차 보고서 URL 은 찾지 못해 **[보도]** 로 분류합니다.

### 4-2. Ghostscript "Upload2Shell" — CVE-2026-125396 (11-21 공개)

- **[사실]** oss-security 메일링 리스트에 11-21 공개됐습니다 [[11]](#ref-11). Type 1 폰트 로더에서 `-dSAFER` 샌드박스를 벗어나는 문제입니다.
- **[사실]** 수정판 Ghostscript 10.08.0 은 2026-09-08 에 나왔습니다 [[12]](#ref-12). 이미지를 받아 서버에서 변환하는 앱(WordPress CVE-2026-65640, Roundcube CVE-2026-114727)도 각각 조치했습니다 [[11]](#ref-11).
- **[추론]** 업로드 파일을 ImageMagick·Ghostscript 로 변환하는 서비스라면, 배포판 패키지 버전이 10.08.0 수정분을 포함하는지 확인해야 합니다.

### 4-3. PHP 8.6.0 GA (11-19, 최신 아님)

- **[사실]** PHP 8.6.0 이 11-19 정식 출시됐습니다 [[13]](#ref-13). Partial Function Application, readonly 속성 기본값, `Io\Poll`, `clamp()`, `\Time\Duration`, `SortDirection` 이 들어갔습니다.

### 4-4. 후속: CISA KEV 조치 기한

- **[사실]** 11-20 KEV 에 추가된 4건(Cisco Expressway, SAP NetWeaver, VMware vCenter, Apache Roller)의 연방기관 조치 기한이 **오늘(11-23)** 입니다. 세부는 11-22 브리핑을 참고하세요.

## 5. CSP (AWS·Azure·GCP·Naver Cloud)

- **[사실] Amazon CloudWatch Omni 의 Azure 지원 (11-21)** [[14]](#ref-14)
  - Azure 리소스 로그, Azure Monitor 메트릭, VNet 플로우 로그, Application Insights 트레이스를 수집합니다.
  - Microsoft Entra ID 테넌트를 연결해 설정합니다.
- **[사실] AWS Quick 의 Meta 광고 커넥터 (11-22)** — Meta 의 광고 MCP 서버를 통해 동작하고, 쓰기 작업 전에는 사용자 허락을 받습니다 [[15]](#ref-15).
- Azure·GCP·Naver Cloud: 11-21~22 공식 채널에서 새로 확인한 항목은 없습니다.

## 6. 언어·프레임워크 (Python·Rust·React·Vue·Java·Kotlin·JS·TS)

- **[사실] Spring 릴리스 묶음 (11-19~20)** — spring.io 릴리스 블로그 기준 [[16]](#ref-16)
  - **Spring Boot 4.2.0** (11-19), **Spring Data 2026.1.0** (11-19), **Spring Batch 6.1** (11-19)
  - **Spring Cloud 2026.0.0 "Paddington"** (11-20): Spring Boot 4.2 기반입니다. 유지보수판 2025.1.5 도 같은 날 나왔습니다.
  - **Spring Boot 4.1.3·4.0.10** (11-20): 4.1.3 은 버그 수정·문서·의존성 업그레이드 112건입니다 [[17]](#ref-17).
  - **Spring AI 2.1.0·2.0.3** (11-20): 13개 CVE 수정을 2.0.3 에도 넣었습니다 [[3]](#ref-3).
- **[추론]** Java4Shell(11-17) 수정은 JDK 쪽이라, Boot 를 올려도 컨테이너 베이스 이미지의 JDK 를 따로 패치해야 합니다.
- **[사실] Apache Arrow Java 20.0.0 (11-21)** — 최소 JDK 가 11 에서 17 로 올라갔고 LZ4 프레임 압축 경로를 lz4-java 로 바꿨습니다 [[18]](#ref-18).
- Python·Rust·Kotlin·TypeScript·React·Vue: 11-21~22 공식 릴리스는 확인되지 않았습니다.

## 7. 인프라·Linux

- **[보도] Linux 7.4-rc4 (11-22)** — Phoronix 에 따르면 Torvalds 가 이번 rc 를 "huge" 라고 했고 변경의 절반가량이 드라이버입니다 [[19]](#ref-19). LKML 원문은 확인하지 못해 보도로 분류합니다.
- **[사실]** Linus 는 Christian Brauner 의 procfs/vfs 수정을 다음 머지 윈도우로 미뤘습니다 [[20]](#ref-20).

## 8. 특집: Jev API 와 결정 모델(Decision Model)

- **[사실] Jev** — 문서는 2026-09-24(jev-1.13) 갱신본, changelog 의 최신은 10-14 의 1.14 입니다. 11-21~22 에는 **신규 릴리스가 없습니다**.
- **[사실] Spring AI 2.1 의 DecisionModel API (11-20)** [[3]](#ref-3)
  - yes/no, 선택(choice), 점수(score) 판단을 타입이 있는 계약으로 받는 새 모델 API 입니다.
  - 제공자는 OpenAI, Ollama, System One 3개입니다.
  - 분류, 라우팅, LLM-as-judge 처럼 "자유 텍스트 대신 결정 값"이 필요한 호출을 위한 것입니다.
- **[추론] Jev 와의 관계**: Jev 처럼 결정을 별도 API 로 떼어 내는 흐름이 JVM 주류 프레임워크에도 들어왔습니다. Spring 애플리케이션에서는 DecisionModel 인터페이스 뒤에 어떤 결정 엔진을 둘지 바꿔 끼우는 구조를 생각해 볼 수 있습니다. 다만 Jev 용 공식 Spring AI 제공자는 **부재**합니다.
- 중립 제3자의 결정 모델 성능 비교는 **부재**합니다.

## 9. AI Safety

- **[사실·자사 수치] Anthropic Safeguards "frontier automated red-teaming" (11-12, 최신 아님)** [[21]](#ref-21)
  - 자동 레드팀 시스템(Anvil)으로 정적 분류기 놓침 비율이 31.5% 에서 0.4% 로 줄었다고 밝혔습니다.
  - Opus 5 에 대한 실제 공격자 성공률은 18.6% 에서 8.1% 로, Fable 5.1 에서는 33.8% 에서 표본 381건 중 0건으로 줄었다고 했습니다.
  - 모두 Anthropic 자체 측정이며, 중립 제3자 재현은 **부재**합니다.
- **[추론]** 4-1 의 MONAI Label 사례는 공격 측 에이전트가 실제 0-day 를 찾아낸 보도입니다. 방어 측 자동 레드팀의 필요성을 보여 주는 사례로 읽을 수 있습니다.

## 10. MCP

- **[사실]** 스펙 변경은 없습니다(현행 2026-07-28).
- **[사실]** Spring AI 2.1 이 MCP Java SDK 2.2.0 위에서 2026-07-28 "modern" 프로토콜을 서버·클라이언트 양쪽에 지원합니다. `spring.ai.mcp.server.protocol=MODERN` 으로 켜며, 클라이언트는 기본적으로 요청마다 새 클라이언트를 씁니다(`PER_REQUEST`) [[3]](#ref-3).
- **[사실]** AWS Quick 의 Meta 광고 커넥터가 Meta 광고 MCP 서버를 이용합니다 [[15]](#ref-15).

## 11. MLOps·피처 스토어

- **[사실/벤더 주장] AWS "distributed KV caching agent skill" (11-20 게시)** [[22]](#ref-22)
  - Agent Toolkit for AWS 의 스킬이며 Kiro, Claude Code, Codex 에서 씁니다.
  - KVTrace 로 트래픽을 분석하고, vLLM·SGLang 용 LMCache 커넥터와 ElastiCache 의 Valkey 9.1 클러스터(EFA RDMA)를 구성합니다.
  - "비용 최대 40%, TTFT 최대 80% 절감"은 **[벤더 주장]** 입니다. 중립 재현은 **부재**합니다.
  - 원문은 멀티테넌트 위험도 적었습니다. 응답 시간으로 다른 테넌트가 같은 텍스트를 보냈는지 드러날 수 있어, 격리가 필요하면 캐시를 분리해야 합니다.

## 12. 에이전트 관측성

- **[사실]** CloudWatch Omni 의 Azure 수집(5장)으로 멀티클라우드 에이전트의 트레이스를 한곳에서 볼 수 있게 됐습니다 [[14]](#ref-14).
- **[사실]** Spring AI 2.1 은 가드레일 거부를 별도로 표시하고 도구 호출 수를 제한합니다 [[3]](#ref-3). **[추론]** 에이전트 대시보드에서 "거부"와 "상한 도달"을 별도 지표로 나눠 보기 좋아졌습니다.

## 13. 그린 컴퓨팅

- **[추론]** 11장의 분산 KV 캐시는 같은 프롬프트 접두부의 prefill 계산을 다시 하지 않게 해 GPU 작업량을 줄입니다. 에너지 절감 수치는 원문에 없어 적지 않습니다.
- 11-21~22 에 1차 출처로 확인한 신규 항목은 없습니다.

## 14. 국내 기업 기술 블로그

| 회사 | 제목 | 게시일 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| — | 오늘 새로 확인된 글 없음 | — | 11-21~22(주말)에 네이버 D2·카카오·LINE(LY)·쿠팡·우아한형제들·당근·토스·두나무 공식 블로그에서 이전 브리핑에 없던 새 글을 확인하지 못했습니다. 네이버 D2 의 ENGINEERING DAY 글(장애 1차 진단 에이전트 등)과 우아한형제들 CLAYDesign 은 11-21 브리핑에서 다뤘습니다. | [D2](https://d2.naver.com/home) |

## 15. Java/Spring 프리랜서 공고

| 플랫폼 | 제목 | 스택 | 계약 형태 | 금액 | 수집일 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | Java/Spring 기반 카드사 차세대 시스템 구축 API 연동 개발 | Java·Spring (API Gateway·계정계 연동) | 기간제 상주, 180일, 2027-01-04 시작 | 월 6,500,000원 | 2026-11-23 | [159538](https://www.wishket.com/project/159538/) |
| 위시켓 | Spark/Airflow 기반 대기업 데이터레이크 파이프라인 개발 | Java·k8s·Spark·Airflow | 기간제 상주, 90일, 즉시 시작 | 월 7,300,000원 | 2026-11-23 | [159535](https://www.wishket.com/project/159535/) |

- 두 공고 모두 **2026-11-09 등록**이고 상세 페이지 기준 모집 마감일은 2026-12-09 입니다. 목록에 "모집 중" 표시가 있었습니다.
- 11-20 등록 Java 공고(풀스택 웹서비스, EV 플랫폼)는 이전 브리핑에서 다뤘습니다.
- 프리모아·이랜서: 로그인 없이 볼 수 있는 범위에서 오늘 검증 가능한 Java/Spring 신규 공고를 확인하지 못했습니다.

---

## 사실 · 추론 · 미확인 정리

- **사실**: MONAI Label 0.8.6 과 CVE-2026-133968, Ghostscript CVE-2026-125396 공개, Spring Boot 4.2.0·Spring AI 2.1.0·Spring Cloud 2026.0.0·Spring Batch 6.1 GA, Arrow Java 20.0.0, CloudWatch Omni 의 Azure 지원, K8s v1.38 일정, Claude computer use 의 Team·Enterprise 베타
- **보도**: AI 에이전트의 MONAI Label 0-day 악용(Amazon 1차 보고서 미확인), Linux 7.4-rc4 세부
- **벤더 주장**: AWS KV 캐시 스킬의 비용·TTFT 절감률, Anthropic 자동 레드팀 수치
- **추론**: Spring 업그레이드 시 도구 호출 상한 영향, DecisionModel 과 Jev 의 연결, KV 캐시의 에너지 효과
- **미확인**: Amazon 위협 인텔리전스 원문, 프리모아·이랜서 신규 공고

## References

<a id="ref-1"></a>[1] Claude Help Center, Release notes. <https://support.claude.com/en/articles/12138966-release-notes>

<a id="ref-2"></a>[2] Claude Docs, Release notes overview. <https://docs.claude.com/en/release-notes/overview>

<a id="ref-3"></a>[3] Spring Blog, "Spring AI 2.1.0 GA and 2.0.3 GA Available Now" (2026-11-20). <https://spring.io/blog/2026/11/20/spring-ai-2-1-0-GA-available-now/>

<a id="ref-4"></a>[4] Kubernetes Contributors, Release schedule. <https://www.kubernetes.dev/resources/release/>

<a id="ref-5"></a>[5] LWKD, week ending 2026-11-15. <https://buttondown.com/LastWeekInKubernetes/archive/lwkd-week-ending-november-15-2026/>

<a id="ref-6"></a>[6] Project MONAI, MONAI Label 0.8.6 release. <https://github.com/Project-MONAI/MONAILabel/releases/tag/0.8.6>

<a id="ref-7"></a>[7] Project MONAI, GHSA-qc22-rmgc-vg94. <https://github.com/Project-MONAI/MONAILabel/security/advisories/GHSA-qc22-rmgc-vg94>

<a id="ref-8"></a>[8] The Register (2026-11-20). <https://www.theregister.com/security/2026/11/20/china-attackers-deployed-ai-agents-that-autonomously-found-and-exploited-a-0-day-to-take-over-a-university-server/5311382>

<a id="ref-9"></a>[9] The Hacker News (2026-11-21). <https://thehackernews.com/2026/11/attackers-ai-agents-found-zero-day-in.html>

<a id="ref-10"></a>[10] SecurityWeek (2026-11-21). <https://www.securityweek.com/amazon-china-linked-hackers-ai-agents-exploited-medical-software-zero-day/>

<a id="ref-11"></a>[11] oss-security, Ghostscript CVE-2026-125396 (2026-11-21). <https://openwall.com/lists/oss-security/2026/11/21/2>

<a id="ref-12"></a>[12] Ghostscript, CVE list. <https://ghostscript.com/releases/cve/index.html>

<a id="ref-13"></a>[13] PHP.net, PHP 8.6.0 Released. <https://www.php.net/>

<a id="ref-14"></a>[14] AWS What's New, Amazon CloudWatch Omni for Microsoft Azure (2026-11-21). <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-cloudwatch-omni-microsoft-azure/>

<a id="ref-15"></a>[15] AWS Machine Learning Blog, "New in AWS Quick". <https://aws.amazon.com/blogs/machine-learning/new-in-aws-quick-more-capable-flows-an-updated-web-experience-and-agents-that-work-together/>

<a id="ref-16"></a>[16] Spring Blog, Releases. <https://spring.io/blog/category/releases>

<a id="ref-17"></a>[17] Spring Blog, "Spring Boot 4.1.3 available now" (2026-11-20). <https://spring.io/blog/2026/11/20/spring-boot-4-1-3-available-now/>

<a id="ref-18"></a>[18] Apache Arrow, "Apache Arrow Java 20.0.0 Release" (2026-11-21). <https://arrow.apache.org/blog/2026/11/21/arrow-java-20.0.0/>

<a id="ref-19"></a>[19] Phoronix, "Linux 7.4-rc4 Released" (2026-11-22). <https://www.phoronix.com/news/Linux-7.4-rc4-Released>

<a id="ref-20"></a>[20] LKML archive. <https://lkml.indiana.edu/hypermail/linux/kernel/2611.2/21308.html>

<a id="ref-21"></a>[21] Anthropic Safeguards, "Frontier automated red-teaming" (2026-11-12). <https://safeguards.anthropic.com/2026/automated-red-teaming/>

<a id="ref-22"></a>[22] AWS Machine Learning Blog, "Cut self-hosted LLM cost and latency with the distributed KV caching agent skill". <https://aws.amazon.com/blogs/machine-learning/cut-self-hosted-llm-cost-and-latency-with-the-distributed-kv-caching-agent-skill/>
