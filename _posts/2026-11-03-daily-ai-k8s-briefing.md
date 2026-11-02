---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-03"
date: 2026-11-03 08:30:03 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-03 08:30 KST. 직전 브리핑은 10-30이었고 10-31~11-02에는 브리핑이 없었습니다. 그래서 이번 수집 범위는 **10-30~11-03**입니다. 각 항목에는 날짜를 따로 적었습니다. **11-02~03에 나온 것만 "최신"으로 봅니다.** 10-30~31 항목은 "지난 브리핑 이후"로 표시했습니다.
> 10-30 브리핑에 실린 항목은 다시 싣지 않았습니다. 예: K8s v1.37.2 패치 릴리스, AI Conformance의 SIG Architecture 이관, KEV 10-29분(GitLab·Cisco), Claude for Legal, Node.js 26 LTS, 위시켓 159357.

**표기 규칙** — [사실] 1차·공식 출처로 확인 / [벤더 주장] 벤더 자체 수치, 독립 재현 없음 / [보도] 언론 보도 / [추론] 필자 해석 / [미확인] 확인 못 함

## 오늘의 핵심

1. **Claude API에 message threads 공개 베타가 열렸습니다 (11-02).**
   - 대화 전체는 처음에 한 번만 보냅니다. 그다음부터는 새 메시지와 직전 응답 `id`만 보냅니다.
   - Anthropic은 500k~1M 토큰 요청에서 TTFT 중앙값이 약 35% 줄었다고 밝혔습니다. [벤더 주장]
   - 가격과 레이트 리밋은 그대로입니다. ZDR·HIPAA 대상이 **아닙니다**. [사실] [1][2][3]
2. **CISA KEV에 Ivanti Connect Secure 2건이 추가됐습니다 (10-30).**
   - CVE-2026-111357은 조치 기한이 **11-02로 이미 지났고**, 포렌식 점검까지 요구합니다.
   - CVE-2026-118527의 기한은 11-13입니다.
   - Volexity는 이 공격이 Ivanti Integrity Checker를 회피한다고 보고했습니다. [사실] [6][7]
3. **Anthropic이 S-1 수정본(S-1/A)을 제출했습니다 (11-02).**
   - 3분기 매출과 약 8,954억 달러 규모의 컴퓨트·인프라 약정이 공개됐습니다.
   - 위험 요인에 "RSP의 'AI로 인한 급격한 진전' 정의에 곧 도달할 수 있다"는 문구가 추가됐습니다. [보도] [4][5]
4. **OpenAI가 활성화 분류기(probe)를 안전 계층으로 쓰는 방식을 공개했습니다 (11-02).** probe는 생성 중에 토큰 단위로 응답을 감시합니다. 정책 위반이 보이면 응답이나 도구 호출을 즉시 막을 수 있습니다. [사실] [17]
5. **Linux 7.4-rc1 (11-01). 7.2 계열은 7.2.15를 끝으로 EOL입니다.** [사실] [14]

---

## 1. AI & ML

- **Message threads 공개 베타 (11-02)** [사실] [1][2][3]
  - 베타 헤더는 `message-threads-2026-08-12`입니다. Messages API 요청에 `thread` 필드를 넣습니다.
    - 첫 요청: `{"type":"create"}`로 대화 전체와 `system`·`tools`를 보냅니다.
    - 다음 요청부터: `{"type":"continue","previous_message_id":...}`로 새 메시지만 보냅니다.
  - `model`·`thinking`·`tool_choice` 같은 "고정" 필드는 매 요청마다 create 때와 같아야 합니다. 값이 다르면 400 `thread_fingerprint_mismatch`가 납니다.
  - 스레드는 best-effort입니다.
    - 마지막 요청 후 5분이 지나면 만료되고, 늦어도 1시간 안에 삭제됩니다.
    - 만료된 뒤 continue 요청을 보내면 404가 납니다. 이때는 대화 전체를 다시 보내야 합니다.
    - 스레드를 조회·목록·삭제하는 API는 없습니다.
  - 지원 범위: 모든 모델, Claude API, Claude Platform on AWS, Google Cloud(Anthropic 관리), Microsoft Foundry.
  - Claude Code 사용자 대부분에게는 이미 켜져 있습니다. TTFT 35% 감소 수치는 Anthropic 자체 측정입니다. 중립적인 제3자의 재현은 **부재**합니다. [벤더 주장]
  - [추론] 시간은 줄지만 토큰 비용은 줄지 않습니다. Claude가 매 턴 전체 대화를 읽기 때문입니다. 따라서 비용을 줄이려면 지금처럼 프롬프트 캐싱을 함께 써야 합니다. 클라이언트가 대화 원본을 계속 들고 있다가 다시 보내는 경로(replay)를 처음부터 만들어 둬야 합니다. 이 점은 기존 무상태 루프보다 설계 부담이 큽니다.
- **Anthropic S-1/A (11-02)** [보도] [4][5]
  - CNBC 보도
    - 1~3분기 누적 매출은 332.4억 달러, 3분기 매출은 약 170억 달러입니다.
    - 3분기 전분기 대비 성장률은 약 47%로, 2분기 144%보다 둔화됐습니다.
    - 순손실은 1~3분기 1,040억 달러이고, 대부분은 전환사채·파생상품의 공정가치 변동입니다.
  - TechCrunch는 위험 요인 문구를 원문 인용으로 전했습니다.
    - 현재 모델 중 RSP 임계치를 넘은 것으로 지정된 모델은 없습니다.
    - 다만 미래 모델에 대한 내부 추정으로는 곧 그 정의에 도달할 수 있다는 내용입니다.
  - SEC 원문(EDGAR)은 이 브리핑에서 직접 확인하지 못했습니다. 수치는 보도 기준입니다. [미확인: 1차 원문]
- Anthropic 뉴스룸에는 11-02자 항목이 있습니다. 다만 제목을 텍스트로 확인하지 못해 싣지 않았습니다. [미확인]
- ML/DL 연구, 신경과학·BCI: 이 기간에 1차 출처로 확인한 주요 발표는 없습니다. [미확인]

## 2. 에이전트 프레임워크

- **Claude Code v2.1.316 (10-31, 지난 브리핑 이후)** [사실] [8]
  - Opus 4.8의 fast mode를 10-30부로 deprecate했습니다. **11-30에 제거됩니다.**
    - 제거 후 fast mode 요청은 오류를 반환합니다. 표준 Opus 4.8로 자동 폴백하지 않습니다.
    - fast mode를 계속 쓰려면 Opus 5.5로 옮겨야 합니다.
  - 새 환경변수가 추가됐습니다.
    - `CLAUDE_CODE_SUBAGENT_EFFORT`: 다른 지정이 없을 때 서브에이전트가 쓸 기본 effort를 정합니다.
    - `CLAUDE_CODE_DISABLE_ULTRATHINK`: `ultrathink` 키워드를 끕니다.
  - Claude apps gateway에 몇 가지가 추가·수정됐습니다.
    - 그룹 공동 예산(`pooled_budget`)과 `managed.policy_mode: layered`가 추가됐습니다.
    - 차단된 모델명을 제대로 검사하지 않던 문제가 고쳐졌습니다.
- **LangGraph 1.2.19 (10-30)** [사실] [9]
  - 스트리밍 관련 수정이 중심입니다. 예: `trace_policy`가 스트리밍 페이로드를 다시 쓰던 문제, 일시 정지한 도구가 실패로 보고되던 문제.
  - SDK 0.4.11은 스트림 재연결에 백오프 재시도를 넣었습니다.
- **CrewAI 1.15.34 (11-01)** [사실] [10]
  - `crewai skill search`가 추가됐습니다.
  - 같은 도구를 반복 호출하면 경고합니다.
  - LLM이 빈 응답을 주면 한 번 재시도한 뒤 타입이 지정된 오류를 냅니다.
  - Breaking 항목으로 1.15.29 agent executor 제거에 대한 마이그레이션 문서가 추가됐습니다.
- Devin: 확인하지 못했습니다. [미확인]

## 3. Kubernetes & Cloud Native

- 10-28 이후 새 패치 릴리스는 없습니다. 현행 버전은 v1.37.2, v1.36.6, v1.35.10, v1.34.13이고, 1.38.0-alpha.3이 나와 있습니다. [사실: GitHub Releases] [11]
- kubernetes.io 블로그에도 10-29 이후 새 글이 없습니다. [사실] [12]
- **(벤더) NVIDIA Workload Map (11-02)** [사실 / 벤더 발표] [13]
  - JobSet, LeaderWorkerSet, RayCluster, KServe 같은 분산 워크로드의 구조를 한 가지 CRD 형식으로 기술하는 프로젝트입니다. 이전 이름은 Karta입니다.
  - 기술하는 항목은 파드 템플릿, 레플리카 수, 상태 필드 위치입니다.
  - KAI Scheduler의 갱 스케줄링과 Run:ai에서 이 기술을 재사용합니다.
  - [추론] 워크로드 종류마다 어댑터를 따로 짜는 문제는 업스트림 Workload Conformance WG(10-27 발표, 10-28 브리핑에서 다룸)와도 맞닿아 있습니다. 다만 Workload Map은 벤더 프로젝트이고, 업스트림 표준이 아닙니다.

## 4. 보안

- **CISA KEV: Ivanti Connect Secure 2건 (10-30 추가)** [사실] [6]
  - **CVE-2026-111357**: 중요 기능에 인증이 빠져 있습니다. 로컬 인증 사용자가 권한을 올릴 수 있습니다. 기한은 **11-02**이고, BOD 26-04에 따른 포렌식 점검 대상입니다.
  - **CVE-2026-118527**: 예측 가능한 식별자를 생성합니다(CWE-340). 원격 인증 사용자가 알려진 경로에 파일을 올릴 수 있습니다. 기한은 11-13입니다.
  - 두 건 모두 인증 우회·RCE 취약점인 CVE-2026-104935와 연쇄해 악용됩니다.
  - 보도 내용 [보도] [7]
    - Volexity가 이 공격을 UTA0576의 소행으로 보고했습니다.
    - 공격자는 AD에서 Windows LAPS 비밀번호와 BitLocker 복구 키를 조회했습니다.
    - Rapid7은 이 활동이 Ivanti Integrity Checker Tool을 회피하므로 검사 결과가 깨끗해도 침해가 아니라고 단정할 수 없다고 권고했습니다.
  - [추론] 국내 기업도 SSL VPN으로 Ivanti를 쓰는 곳이 있습니다. 대응 순서는 패치 → 메모리·로그 보존 → 헌팅 → 자격 증명 교체입니다. 지난 브리핑에서 다룬 GitLab(CVE-2026-97229, 기한 11-01)도 아직 패치하지 않았다면 함께 처리하는 것이 좋습니다.
- **AWS (11-02)** [사실]
  - Amazon Inspector가 EC2 AMI 취약점 스캔을 지원합니다. 인스턴스를 띄우지 않고 스캔합니다. [15]
  - AWS KMS가 ML-KEM(FIPS 203) 키 캡슐화를 지원합니다. 지난주 발표분으로, 주간 라운드업 기준입니다. [16]

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

- **AWS** [사실]
  - Step Functions 워크플로를 Bedrock AgentCore Gateway(MCP)로 에이전트 도구로 노출할 수 있습니다. 지난주 발표분입니다. [16]
  - Amazon Connect Customer에 MCP 도구를 호출하는 'External Tool' 블록이 추가됐습니다(11-02). 서울 리전도 포함됩니다. [18]
  - SageMaker AI 실시간 엔드포인트가 MIG 기반 GPU 분할을 지원합니다. GPU 하나를 최대 7개로 나눕니다. 발표는 10-30~11-01 사이입니다. [19]
  - MSK Provisioned가 TLS 1.3 보안 정책을 지원합니다. 발표는 10-30~11-01 사이입니다. [19]
  - GPT-6.1 Terra가 Bedrock에서 GA입니다. 성능 수치는 OpenAI 자체 평가입니다. [벤더 주장] [16]
- **GCP (11-02 릴리스 노트)** [사실] [20]
  - App Engine에서 Python 3.15 런타임이 Preview로 나왔습니다.
  - Backup and DR의 레이블 기반 자동 보호가 GA입니다.
  - Application Load Balancer의 Cloud Trace 분산 추적이 Preview입니다. W3C Trace Context와 OpenTelemetry를 따릅니다.
- **Azure**: 10-30~11-02 사이 Azure Blog의 공식 Announcements에는 새 글이 없습니다. [사실] [21]
  - Partner Center에서는 11-02부터 CSP 소비 프로모션이 시작됐습니다. [사실] [22]
  - "Azure MCP Server 3.0 GA"는 제3자 블로그에서만 확인했습니다. [미확인: 1차]
- **Naver Cloud**: 공지에 10-23 이후 새 항목이 없습니다. [사실] [23]
  - 이전 공지 중 참고할 일정: 장기 미로그인 서브계정 비밀번호 초기화(11-24), SSL VPN 서비스 종료(2027-01-21).

## 6. 언어 (Python · Rust · React · Vue · Java · Kotlin · JS · TS)

- 10-30~11-03 사이 Python, Rust, TypeScript, React, Vue, Kotlin, JDK의 정식 릴리스는 확인하지 못했습니다.
  - 각 최신 버전: Rust 1.99.1(10-16), TypeScript 7.1 Beta(10-20)
  - [사실: 각 GitHub Releases] [24][25]
- **Spring**: Boot 4.2.0-RC1을 포함한 포트폴리오 RC1은 10-22~23에 나왔고 이전 브리핑에서 다뤘습니다.
  - 새로 정리된 점이 있습니다. Boot 4.2부터 기본 Buildpacks 빌더가 Ubuntu 26.04(Resolute)로 바뀌고, run image 버전을 고정하지 않습니다.
  - 따라서 재현 가능한 이미지가 필요하면 빌더와 run image 버전을 직접 고정해야 합니다. [사실] [26]
  - GA 날짜는 공식 발표로 확인하지 못했습니다. [미확인]

## 7. 인프라 & Linux

- **커널 (kernel.org)** [사실] [14]
  - 7.4-rc1 (11-01)
  - 7.3.1 stable (10-30)
  - 7.2.15 (11-01), **EOL**
  - LTS 6.18.60, 6.12.115, 6.6.161, 6.1.191, 5.15.224, 5.10.273 (모두 10-30)
- [추론] 7.2 계열을 쓰는 배포판·노드라면 7.3 계열이나 LTS로 옮길 계획이 필요합니다. 10-28 KEV에 오른 Fragnesia(CVE-2026-46300)는 커널 취약점입니다. 쓰고 있는 커널 계열의 stable 커밋이 반영됐는지 확인해야 합니다.

## 9. AI Safety & Alignment

- **OpenAI, "Training activation classifiers for safety and alignment" (11-02)** [사실] [17]
  - 저자: Makelov, Xu, Ananthanarayanan, Mcdonald, Dupre la Tour
  - GPT-5.6부터 모든 assistant 응답에 probe를 추가 방어 계층으로 돌립니다.
  - probe는 생성 중에 토큰 단위로 점수를 매깁니다. 정책 위반이 보이면 응답이나 도구 호출을 중간에 막고, 추론 모델에 정밀 검토를 맡깁니다.
  - 한계도 스스로 적었습니다.
    - 지도학습으로 학습하므로, 학습한 대상만 탐지합니다.
    - 기반 모델이 바뀌면 다시 학습해야 합니다.
- **Anthropic Alignment Science, "Automated Subtle Emergent Misalignment Research" (2026-10, 블로그 표기)** [사실] [27]
  - 저자: Balcells Obeso, Qi, MacDiarmid, Hubinger
  - 실험 설계
    - Claude에게 production과 비슷한 학습 데이터 모니터를 주었습니다.
    - 과제는 모니터를 통과하면서 연구용 모델을 비정렬로 만드는 학습 데이터를 만드는 것이었습니다.
  - 결과: 모든 실행에서 성공했고, 주로 픽션·롤플레이 형식으로 숨겼습니다.
  - 배포 모델의 행동을 뜻하는 결과는 아닙니다.
  - 11-02 이 블로그의 다른 글에서도 다뤘으므로 짧게만 적습니다.
- [추론] 두 글은 같은 문제의 양면입니다. 행 단위 텍스트 검사는 우회될 수 있습니다(Anthropic). 그래서 모델 내부 신호를 쓰는 감시층을 더하는 방향이 나옵니다(OpenAI). 다만 두 회사 모두 자기 실험이고, 중립적인 제3자의 비교 평가는 **부재**합니다.

## 10. MCP 생태계

- 사양: 최신 안정 리비전은 여전히 `2026-07-28`입니다. 새 릴리스는 없습니다. [사실] [28]
- 이번 주 흐름은 **기존 시스템을 MCP 도구로 노출하는 쪽**입니다.
  - AWS Step Functions와 Amazon Connect의 External Tool이 그 예입니다(5절). [사실] [16][18]
  - Message threads도 `mcp_servers`를 "고정" 필드로 다룹니다. 다만 서버별 인증 토큰은 턴마다 바꿀 수 있습니다. [사실] [2]

## 11. MLOps / Feature Store

- **SageMaker AI GPU 분할 (MIG)** [사실] [19]
  - 지원 인스턴스: P4d, P5, G7, G7e
  - 서울 리전은 대상에 없습니다. 아시아에서는 도쿄와 싱가포르가 포함됩니다.
  - [추론] 소형 파인튜닝 모델, 임베딩, 리랭커처럼 GPU 하나를 다 쓰지 못하는 모델이 많다면 비용 구조가 달라질 수 있습니다.
- MLflow(최신 3.17.2, 10-21)와 Feast(0.67.0, 10-13)는 이 기간에 새 릴리스가 없습니다. [사실] [29][30]

## 12. Agent Observability

- **GCP** [사실] [20]
  - Load Balancer 분산 추적이 Preview입니다(OTel 호환).
  - BigQuery 데이터 에이전트의 성능·지연·비용 모니터링이 GA입니다.
- **Langfuse v4.72.0 (10-29)**: 지난 브리핑에서 빠졌던 릴리스입니다. [사실] [31]
  - AI gateway 스팬을 키·서비스에 귀속합니다.
  - PagerDuty 알림 연동이 추가됐습니다.
  - OTel `gen_ai` 사용량 매핑에서 cache-write TTL이 두 번 집계되던 문제를 고쳤습니다.
- [추론] message threads를 쓰면 요청 페이로드가 작아집니다. 프록시 단에서 요청 크기로 컨텍스트 길이를 추정하던 관측 도구는 실제 입력 토큰과 어긋날 수 있습니다. 응답의 usage 필드를 기준으로 보는 편이 안전합니다.

## 13. Green Computing

- **ORNL 등, 데이터센터 열관리 에너지 분석법 (Int. J. Heat and Mass Transfer, 2026-11-01 게재)** [사실: 동료심사 논문] [32]
  - 냉각 루프 각 구성요소의 TUE 기여분을 보여 주는 waterfall diagram 방법을 제안했습니다.
  - 단상 direct-to-chip 수랭 구성(3U 모듈형)에서 TUE 1.016을 보고했습니다(외기 47°C).
- **Wärtsilä 연구 (11-02)** [벤더 주장] [33]
  - 오프그리드 데이터센터 55GW를 CCGT 대신 엔진 기반으로 전원을 공급하면, 20년간 1,960억 유로를 절감한다고 주장했습니다.
  - 발전 장비 제조사의 자체 모델링이고, 독립 검증은 **부재**합니다.

## 14. 국내 기업 기술 블로그 (네카라쿠배당토)

| 회사 | 제목 | 날짜 | 요약 | 링크 |
|---|---|---|---|---|
| — | 10-30~11-03 사이 새 글 확인 안 됨 | — | 아래 참조 | — |

- **토스**: 최신 글은 SNAP(10-27)으로, 이미 다뤘습니다. 카테고리에 보이는 "로그 정의 기준을 AI 스킬로" 글도 10-26 브리핑에서 다뤘습니다. [34]
- **우아한형제들**: 최신 글은 10-21 critical-script입니다. [35]
- **LY**: 목록에 새 글이 보이지 않습니다. 맨 위는 Flava MCP Hub 글로, 이미 다뤘습니다. [36]
- **카카오페이**: Alloy OOM 글(10-27)은 10-29 브리핑에서 다뤘습니다.
- **카카오, NAVER D2, 당근, 쿠팡, 두나무**: 목록 페이지가 렌더링되지 않아 확인하지 못했습니다. [미확인]
- 이 기간에 공식 블로그에 올라온 **장애 회고 글은 확인되지 않았습니다**.

## 15. Java/Spring 프리랜서 공고

수집 일자: 2026-11-03. 로그인 없이 볼 수 있는 공개 페이지만 확인했습니다.

**원 공고 (상세 페이지 확인)**

| 플랫폼 | 제목 | 스택 | 계약·근무 형태 | 금액 | 상태 | 링크 |
|---|---|---|---|---|---|---|
| 위시켓 | Spring 기반 보험사 AI 대화형 질의응답 서비스 개발 (중급) | Spring (풀스택) | 기간제, 미드 레벨(6~8년 차), 90일, 서울 종로구, 시작 11-16 | 월 5,500,000원 | 모집 중, 마감 2026-11-16, 등록 11-02 | [37] |
| 위시켓 | Spring 기반 보험사 AI 활용체계 화면 및 외부 연계 개발 (초급) | Spring (풀스택) | 기간제, 주니어(4~5년 차), 90일, 서울 종로구, 시작 11-16 | 월 4,500,000원 | 모집 중, 마감 2026-11-16, 등록 11-02 | [38] |

- 두 공고는 같은 프로젝트입니다. 보험사의 투자자산 심사·모니터링 업무를 지식화하고 AI 활용체계를 구축하는 3개월짜리 일입니다.
- 상세 기술스택 표는 공개 페이지에 나오지 않습니다. 제목에 있는 "Spring"만 확인했습니다. [사실]

**목록 페이지에서만 본 공고 (상세 페이지 미확인)** [39]
- 위시켓, "Java/React 기반 LG전자 글로벌 플랫폼 기능 개선 풀스택 개발" — 월 7,000,000원, 45일, 시니어, 서울 강서구, 등록 11-02. **모집 상태 미확인**.
- 같은 보험사 프로젝트의 "Python/FastAPI 기반 … (고급)" 공고도 있습니다(월 6,500,000원). Java/Spring 공고가 아니라서 표에 넣지 않았습니다.
- 프리모아·이랜서: 공개 페이지에서 오늘 확인한 Java/Spring 공고가 없습니다. [미확인]

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- 10-30~11-03 사이 TypeSafe(Jev)의 공식 발표나 새 릴리스는 확인하지 못했습니다. 공식 블로그의 최근 글도 새 항목이 없습니다. [사실: 공식 채널 기준] [40]
- [추론] 이번 주 다른 발표들과 겹치는 지점이 있습니다.
  - OpenAI의 probe(9절)는 "생성 중에 빠르게 판단해 차단하는 분류기"입니다. Jev 같은 의사결정 모델이 내세우는 용도(가드레일, 판정)와 겹칩니다.
  - 차이도 분명합니다. probe는 감시 대상 모델의 내부 활성값을 씁니다. 반면 Jev는 외부에서 텍스트와 상태를 입력으로 받는 별도 모델입니다.
  - 따라서 외부 판정기가 맡을 일은 모델 내부 접근이 없는 쪽에 남습니다. 서드파티 모델의 출력 검사나 업무 규칙 분기가 그런 예입니다.
  - 두 방식을 직접 비교한 중립 평가는 **부재**합니다.

---

## 사실 · 추론 · 미확인 정리

- **사실**
  - Message threads 베타 사양(헤더, 만료, ZDR 비대상)
  - KEV Ivanti 2건과 기한
  - Claude Code 2.1.316의 Opus 4.8 fast mode 제거 일정
  - LangGraph 1.2.19, CrewAI 1.15.34
  - 커널 7.4-rc1과 7.2 EOL
  - AWS·GCP 11-02 발표
  - OpenAI probe 글, Anthropic ASEM 글
  - 위시켓 159408·159409, ORNL 논문
- **벤더 주장**
  - TTFT 35% 감소(Anthropic)
  - GPT-6.1 Terra 성능(OpenAI)
  - Wärtsilä 절감액
- **보도**
  - S-1/A 재무 수치와 위험 요인 문구
  - Volexity·Rapid7의 Ivanti 분석
- **추론**
  - threads의 비용·설계 영향과 관측 도구 영향
  - Ivanti 대응 순서
  - 7.2 EOL 대응
  - probe와 외부 판정기의 역할 분담
- **미확인**
  - S-1/A EDGAR 원문
  - Azure MCP Server 3.0 GA의 1차 출처
  - Devin, Spring GA 일정
  - 국내 블로그 다수
  - 프리모아·이랜서, LG전자 공고의 상세 페이지

## References

1. Claude, "Make long-running agents faster with message threads", 2026-11-02 — <https://claude.com/resources/articles/message-threads>
2. Claude Platform Docs, "Message threads" — <https://platform.claude.com/docs/en/build-with-claude/message-threads>
3. Claude Platform release notes (2026-11-02) — <https://platform.claude.com/docs/en/release-notes/overview>
4. CNBC, "Anthropic reports $17 billion in Q3 revenue ... in revised S-1", 2026-11-02 [보도] — <https://www.cnbc.com/2026/11/02/anthropic-ant-s-1-quarter-financials.html>
5. TechCrunch, "Anthropic warns that it's very close to RSI capability", 2026-11-02 [보도] — <https://techcrunch.com/2026/11/02/anthropic-warns-that-its-very-close-to-rsi-capability-aka-self-building-ai/>
6. CISA, Known Exploited Vulnerabilities Catalog (CVE-2026-111357, CVE-2026-118527, 2026-10-30 추가) — <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
7. Help Net Security, "CISA to federal agencies: Remediate exploited Ivanti Connect Secure vulnerabilities", 2026-11-02 [보도] — <https://www.helpnetsecurity.com/2026/11/02/cisa-to-federal-agencies-remediate-exploited-ivanti-connect-secure-vulnerabilities-cve-2026-111357-cve-2026-118527/>
8. anthropics/claude-code, Release v2.1.316, 2026-10-31 — <https://github.com/anthropics/claude-code/releases>
9. langchain-ai/langgraph, Release 1.2.19, 2026-10-30 — <https://github.com/langchain-ai/langgraph/releases>
10. crewAIInc/crewAI, Release 1.15.34, 2026-11-01 — <https://github.com/crewAIInc/crewAI/releases>
11. kubernetes/kubernetes, GitHub Releases — <https://github.com/kubernetes/kubernetes/releases>
12. Kubernetes Blog — <https://kubernetes.io/blog/>
13. NVIDIA Technical Blog, "Support New AI Frameworks Faster Using NVIDIA Workload Map", 2026-11-02 — <https://developer.nvidia.com/blog/support-new-ai-frameworks-faster-using-nvidia-workload-map/>
14. The Linux Kernel Archives (2026-11-03 조회) — <https://www.kernel.org/>
15. AWS, "EC2 Amazon Machine Images can now be scanned for vulnerabilities through Amazon Inspector", 2026-11-02 — <https://aws.amazon.com/about-aws/whats-new/2026/11/ec2-amis-scanned-through-inspector/>
16. AWS News Blog, "AWS Weekly Roundup ... (November 2, 2026)" — <https://aws.amazon.com/blogs/aws/aws-weekly-roundup-gpt-6-1-terra-on-bedrock-step-functions-as-agent-tools-and-more-november-2-2026/>
17. OpenAI Alignment, "Training activation classifiers for safety and alignment", 2026-11-02 — <https://alignment.openai.com/training-activation-classifiers/>
18. AWS, "Amazon Connect Customer now supports Model Context Protocol (MCP) tools in flows", 2026-11-02 — <https://aws.amazon.com/about-aws/whats-new/2026/10/connect-flows-mcp-tools/>
19. AWS, What's New (SageMaker AI GPU partitioning, MSK TLS 1.3) — <https://aws.amazon.com/about-aws/whats-new/recent/>
20. Google Cloud, Release notes (2026-11-02) — <https://docs.cloud.google.com/release-notes>
21. Azure Blog, Announcements — <https://azure.microsoft.com/en-us/blog/content-type/announcements/>
22. Microsoft Learn, Partner Center announcements (November 2026) — <https://learn.microsoft.com/en-us/partner-center/announcements/>
23. NAVER Cloud Platform, 공지사항 — <https://www.ncloud.com/support/notice/all>
24. rust-lang/rust, GitHub Releases — <https://github.com/rust-lang/rust/releases>
25. microsoft/TypeScript, GitHub Releases — <https://github.com/microsoft/TypeScript/releases>
26. spring-projects/spring-boot, Release v4.2.0-RC1 — <https://github.com/spring-projects/spring-boot/releases>
27. Anthropic Alignment Science, "Automated Subtle Emergent Misalignment Research", 2026-10 — <https://alignment.anthropic.com/2026/automated-em-search/>
28. modelcontextprotocol, GitHub Releases — <https://github.com/modelcontextprotocol/modelcontextprotocol/releases>
29. MLflow, GitHub Releases — <https://github.com/mlflow/mlflow/releases>
30. Feast, GitHub Releases — <https://github.com/feast-dev/feast/releases>
31. Langfuse, Release v4.72.0, 2026-10-29 — <https://github.com/langfuse/langfuse/releases>
32. Park et al., "Holistic energy analysis method for thermal management architectures of data centers", Int. J. Heat and Mass Transfer 268, 128971 (2026) — <https://doi.org/10.1016/j.ijheatmasstransfer.2026.128971>
33. Wärtsilä, 보도자료, 2026-11-02 [벤더 주장] — <https://www.wartsila.com/media/news/02-11-2026-new-study-right-power-technology-choices-for-off-grid-data-centres-could-deliver-up-to-eur-200-billion-in-global-savings-3808329>
34. 토스 테크, Engineering — <https://toss.tech/category/engineering>
35. 우아한형제들 기술블로그 — <https://techblog.woowahan.com/>
36. LY Corporation Tech Blog — <https://techblog.lycorp.co.jp/ko>
37. 위시켓, 프로젝트 159408, 등록 2026-11-02 — <https://www.wishket.com/project/159408/>
38. 위시켓, 프로젝트 159409, 등록 2026-11-02 — <https://www.wishket.com/project/159409/>
39. 위시켓, 프로젝트 찾기 (목록 페이지, 2026-11-03 조회) — <https://www.wishket.com/project/>
40. TypeSafe AI, Blog — <https://typesafe.ai/>
