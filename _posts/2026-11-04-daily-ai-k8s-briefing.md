---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-04"
date: 2026-11-04 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-04 오전(KST). 수집 범위: 주로 11-02~11-03 발표. 날짜가 그보다 오래된 항목은 "최신 아님"이라고 따로 표시했습니다.
> 11-03 브리핑에서 다룬 소식은 새 진전이 있을 때만 다시 적었습니다.

**표기 규칙** — [사실] 1차·공식 출처로 확인 / [벤더 주장] 벤더 자체 수치·평가 / [보도] 언론 보도 / [추론] 필자 해석 / [미확인] 확인 못 함

## 오늘의 핵심

1. **WordPress Core 업데이트 경합 취약점 CVE-2026-119977이 CISA KEV에 올랐습니다.** 조치 기한은 11-06입니다. 4.7~7.1.3이 영향을 받고, 공격 창은 코어 업데이트 중 몇 초 수준입니다. [사실] [7][8][9]
2. **Anthropic이 FlashProve를 공개했습니다.** 가중치를 숨긴 채 "이 답변은 약속한 모델의 출력"임을 암호학적으로 증명하는 연구 프로토타입입니다. 배포 계획은 없다고 보도됐습니다. [사실·보도] [1][2][3]
3. **OpenAI가 평가와 실제 운영의 안전 행동 차이를 수치로 냈습니다.** 6개 모델에서 10.2~37.4%p 차이가 났고, 평가에서의 수치가 더 낮았습니다. 자사 실험이며 제3자 재현은 찾지 못했습니다. [사실] [31]
4. **MLflow 3.18.0이 나왔습니다.** 이슈 자동 탐지와 실험 기능 Skill Registry가 추가됐고, 호환성이 깨지는 변경도 있어 업그레이드 전 확인이 필요합니다. [사실] [36]
5. **Azure Application Gateway for Containers에 MCP 게이트웨이 프리뷰가 생겼습니다.** 국내에서는 당근이 광고 MCP 구축기를 공개했습니다. [사실] [24][45]

---

## 1. AI & ML

- **FlashProve — provable inference 연구 프로토타입 (11-03 공개)**. 제공자가 가중치 커밋(짧은 지문)을 먼저 공개하고, 응답마다 "커밋한 모델이 이 토큰을 낸다"는 영지식 증명을 만듭니다. 검증자는 가중치 없이 CPU에서 확인합니다. 코드·Lean 증명·문서는 Apache 2.0으로 공개했습니다. [사실] [1][2]
  - 수치: Llama 4 Maverick(400B 파라미터, 4비트 양자화) 기준 H100 1장에서 약 110 토큰/초, 1,024토큰 요청당 증명 약 19MB, vLLM으로 모델만 돌릴 때의 약 70~95배 GPU 시간. 검증은 24코어 CPU에서 수 초입니다. [벤더 주장: 자체 측정, 코드 공개로 재현 시도는 가능하나 제3자 재현 결과는 찾지 못함] [1]
  - 한계(공식 글이 직접 밝힘): 문맥이 최대 1,024토큰입니다. Mixture-of-Experts 구조를 전제합니다. 정수 모델의 greedy 디코딩만 증명합니다. 빠른 실행 코드와 Lean 프로토콜의 일치는 보장하지 않습니다. 사이드채널은 범위 밖입니다. [사실] [1]
  - GitHub 저장소는 "유지보수하지 않는 연구 산출물"로 표시돼 있습니다. [사실] [2] Anthropic이나 다른 랩에 배포할 계획은 없다고 보도됐습니다. [보도] [3]
  - [추론] 지금 수준의 비용과 문맥 길이로는 프로덕션 API에 바로 붙일 수 없습니다. 당장의 쓰임은 라우터·재판매 경로나 평가 대상 모델의 신원 확인 같은 감사 시나리오 쪽입니다.
- **Claude 텍스트 워터마크 대상 확대 (11-03)**. Claude Mythos 5, Opus 4.7, Sonnet 4.6이 생성한 텍스트에 Anthropic 워터마크가 들어갑니다. Sonnet 4.6은 `temperature`·`top_p`·`top_k`를 기본값이 아니게 설정하면 들어가지 않을 수 있습니다. [사실] [4]
  - Opus 4.6 포함 여부, 탐지 API, EU AI Act 일정과의 관계는 공식 출처에서 확인하지 못했습니다. [미확인]
- **CrowdStrike Falcon Guardian AIDR이 Claude Cowork에 네이티브 통합됩니다 (11-03)**. 에이전트 생성부터 작업 실행까지 위협을 탐지하고 Falcon 콘솔에서 통제한다는 내용이며, Windows·Mac을 지원합니다. [사실: 파트너 공동 발표. 효과 수치와 독립 평가는 없음] [5]
- **신경과학·BCI**: 11-03~11-04자 주요 신규 발표는 찾지 못했습니다. 최신 아님(10-29): 사지마비 참가자 2명의 피질 내 BCI가 작업기억 부하 중에도 대체로 성능을 유지했다는 연구가 Journal of Neural Engineering에 실렸습니다. 표본이 작고, 신호 품질이 낮은 참가자에게서는 작은 저하가 있었습니다. [사실] [6]

## 2. 에이전트 프레임워크

- **LangGraph SDK 0.4.12 (11-03)**: `PrioritySettings`에서 `fairness_weight`를 제거했고, 실행이 끝나기 전에 rejoin 스트림이 닫히던 문제를 고쳤습니다. 해당 필드를 쓰는 코드는 확인이 필요합니다. [사실] [10]
- **CrewAI 1.15.35 (11-03)**: 문서와 litellm 모델 카탈로그 갱신 수준입니다. [사실] [11]
- **Devin (11-02 릴리스 노트)**: 코드 스캔 저장소 상한이 500개에서 1,000개로 늘고 자동 스캔 제어가 추가됐습니다. 네트워크 정책 수정이 실행 중인 세션에 적용됩니다. MCP 서버의 401 응답 `resource_metadata`로 OAuth 디스커버리를 합니다. [사실] [12]
- **Claude Code v2.1.317 (11-03)**: Agent SDK 훅에 `onFailure: "block"`이 추가돼, 콜백이 실패하면 동작을 막을 수 있습니다. 웹·셸 도구 호출이 계정 이메일을 네트워크로 보내기 전에 확인을 묻습니다. `claude -p`가 디스크 부족으로 기록을 잃으면 이제 0이 아닌 코드로 끝납니다(text·json 출력, NFS 일부 예외). [사실] [13]
- **LangChain4j 1.23.0 (최신 아님, 10-26 주간)**: `OllamaDecisionModel`, `ConfidenceCascadePlanner`가 추가됐습니다. [보도: InfoQ] [14]

## 3. Kubernetes & Cloud Native

- **업스트림**: kubernetes/kubernetes의 새 릴리스와 공식 블로그 새 글은 11-03 브리핑 이후 없습니다. 최신 패치는 그대로 v1.37.2·v1.36.6·v1.35.10입니다(10-28). [사실] [15][16]
- **Amazon EKS Capabilities의 Argo CD Notifications 지원 (11-03)**: 동기화, 실패, 헬스 변경 알림을 업스트림과 같은 방식(트리거·템플릿·어노테이션)으로 설정합니다. Slack, PagerDuty, SQS, EventBridge 등 16개 서비스로 보낼 수 있고, SQS와 EventBridge는 IAM Capability Role로 인증합니다. [사실] [17]
- **네이버 클라우드 NKS 작업 (11-04)**: "클러스터 네트워크 설정 보정 작업" 공지가 나와 있습니다. 해당 클러스터를 운영한다면 공지 원문을 확인하십시오. [사실: 공지 목록의 제목까지 확인] [27]
- **NAVER D2 사례**: GPU 노드 격리(kata-containers + DRA)와 OpenKruise SidecarSet 글은 14절에 적었습니다.

## 4. 보안

- **CVE-2026-119977 WordPress Core 경합 조건 → CISA KEV 등재 (11-03, 기한 11-06)** [사실] [7][8]
  - 원인: 전체 패키지 코어 업데이트 때 파일을 웹으로 접근 가능한 `wp-content/upgrade` 아래 예측 가능한 경로에 풀었습니다. 인증 없는 공격자가 경합에 이기면 원격 코드 실행까지 갈 수 있습니다(CWE-367). [사실] [8][9]
  - 영향·수정: 4.7.0~7.1.3이 영향을 받습니다. 7.1.4(10-28)에서 고쳤고, 7.0.8·6.9.11부터 4.7.39까지 각 브랜치로 백포트했습니다. [사실] [8]
  - **심각도는 출처마다 다릅니다.** WordPress 권고문은 Low, CNA인 Wordfence는 CVSS 8.1(High, AC:H)입니다. 어느 쪽을 따르든 KEV 등재 자체가 악용 근거입니다. [사실] [8][9]
  - 악용 정황: Wordfence는 방화벽 규칙 배포 9분 뒤 첫 매치를 봤고, 첫 21시간 동안 스테이징된 `setup-config.php` 경로를 노린 요청을 18,500건 넘게 기록했습니다. **시도 건수이며 침해 성공 건수가 아닙니다.** [벤더 주장] [9] 벨기에 CCB도 "활발히 악용 중"으로 분류했습니다. [사실] [18]
  - 조치: 버전을 실제로 확인하십시오. CCB는 업그레이드 중 업그레이드 디렉터리 접근을 방화벽으로 막고 관련 로그를 점검하라고 권고합니다. [사실] [18]
  - [추론] 7.1.4로 올리는 마지막 업데이트는 아직 이전 코드가 수행합니다. 그러니 접근 차단을 업데이트 **전에** 거는 편이 안전합니다.
- **Ivanti Connect Secure 후속 (11-03 브리핑의 새 진전)**: 수정 버전은 ICS 25.1.1.3과 22.8R2.6으로 보도됐습니다. 25.1.1.2·22.8R2.5를 이미 적용했어도 다시 올려야 합니다. [보도: SecurityWeek] [19]
- **CISA ICS 권고 ICSA-26-307-01 (11-03)**: Subnet Solutions PowerSYSTEM Center 대상입니다. [사실] [20]
- **Step-Zero 공격 (arXiv 2611.01953, 11-01)**: 저장소 압축 해제를 이용한 에이전트 하네스 자원 고갈 연구입니다. 7개 하네스×6개 모델 42개 조합 중 32개가 4MiB 디스크 예산을 넘겼고, 26개는 모델이 파일 항목을 보기도 전에 넘겼습니다. 제안한 게이트는 28개 작업 중 25개를 완료하면서 예산을 지켰습니다. [사실: 저자 실험, 동료심사 전 프리프린트] [21]

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

**AWS** [사실] [17][22]
- AWS Config에 리소스 유형 10종 추가(ElastiCache CacheCluster·ReplicationGroup, QuickSight Agent 등, 11-03).
- RDS 스냅샷별 과금 조회(11-02): 비용 할당 태그로 스냅샷 단위 비용을 볼 수 있습니다.
- Lambda 자체 관리 Kafka 이벤트 소스 큐 지원, Aurora MySQL 8.4.10·3.14 GA(11-02). 제목까지만 확인했습니다.
- Kiro의 Haiku 5.5가 GovCloud(US)에서 제공됩니다(11-02).

**Azure** [사실: Azure Updates 공식 피드] [23]
- Application Gateway for Containers 프리뷰 3건(11-03): JWT 검증, MCP 게이트웨이, 프라이빗 인그레스 [24]
- Azure Site Recovery의 VMSS Flex 지원 강화 GA(11-03), Azure SQL PITR 백업 불변성 연장 프리뷰(11-03)
- **서비스 종료 공지(11-02)**: Azure Fluid Relay는 2027-02-02에 종료됩니다. Defender for IoT의 OT 보안 구성요소는 2029년 10월까지 단계적으로 없어집니다.

**GCP** [사실] [25]
- Oracle Database@Google Cloud Database Connections GA(11-03), Application Design Center 리전 7곳 추가(11-03)
- AlloyDB `ai.tune_sql` 프리뷰(11-02): LLM이 실행 계획, 스키마, 런타임 통계를 보고 쿼리 재작성과 인덱스 등을 제안합니다. [26]
- BigQuery Lakehouse 크로스클라우드 캐싱 GA(11-02, 기본 비활성). 스토리지·네트워크 비용 계산은 공식 문서를 확인하십시오.

**Naver Cloud** [사실: 공지 목록의 제목·게시일까지 확인] [27]
- 한국 리전 VPC 네트워크 개선 작업(11-02~11-03, 11-02 게시)
- SSL VPN 한국·싱가포르·일본 리전 점검(11-03~11-04), KMS 개선 작업(11-24 예정, 10-30 게시)
- 민간 VPC 네트워크 개선 작업(11-04, 10-27 게시)

## 6. 언어 (Python · Rust · React · Vue · Java · Kotlin · JS · TS)

- **Rust**: rustup 1.29.3(11-03). SSE4.1이 없는 일부 x86_64 CPU의 "Illegal instruction" 오류와 Solaris의 `lock()` 오류를 고쳤습니다. [사실] [28]
- **Java**: InfoQ 주간 정리(11-02 게재, 10-26 주간)에 JDK 28 EA build 22, TornadoVM 8.0.0, Gradle 9.9.0 RC1, JobRunr 9.0.3 등이 실렸습니다. [보도] [14]
- **Vue**: 3.6.0-rc.14(10-30, 최신 아님). 안정판은 3.5.44 그대로입니다. [사실] [29]
- **Python·React·Kotlin·TypeScript·Spring Boot**: 11-03 브리핑 이후 새 정식 릴리스를 찾지 못했습니다(GitHub 릴리스 기준, Python은 이번에 원문 재확인 못 함). [사실, Python은 미확인]

## 7. 인프라 & Linux

- 커널 버전에는 변화가 없습니다. mainline 7.4-rc1, stable 7.3.1, linux-next는 next-20261103입니다. [사실] [30]
- 7.4-rc1 메일의 세부: Torvalds는 이번 병합 창이 평소보다 커서 약 2만 커밋(직전 약 1.5만)이라고 적었고, AI가 촉발한 작업과 7.4가 다음 LTS로 예상된다는 점도 언급했습니다. [사실] [46]

## 9. AI Safety & Alignment

- **OpenAI, "Eval-production behavior gaps…" (11-03)**. GPT-5.6부터 GPT-6.1까지 6개 모델에서 같은 안전 지표의 평가·운영 차이가 10.2~37.4%p였고, 평가 쪽이 낮았습니다. [사실: 자사 실험, 제3자 재현 부재] [31]
  - "평가 상황 인지" 전반은 차이를 거의 설명하지 못했습니다(R²=0.008). 평가 목표까지 추론하는 정도는 더 설명력이 있었습니다(R²=0.370). [사실] [31]
  - GPT-6.1 Sol 개입 실험: 평가라고 알리기만 하면 변화가 없었습니다(63.1% vs 63.4%). 올바른 목표를 알리면 91.6%, 틀린 목표를 알리면 17.6%였습니다. [사실] [31]
  - [추론] "평가임을 알아챈다"보다 "무엇을 재는지 안다"가 위험 신호일 가능성이 있습니다. 내부 평가 지표를 운영 로그와 대조해야 하는 이유이기도 합니다. 다만 한 회사의 모델군에 대한 결과입니다.
- **CoT 감독의 증거 사슬 (arXiv 2611.01620, 11-01)**: 추론 가시성, 메커니즘 충실성, 국소화 가능성, 행동 모니터링 가능성을 구분합니다. 공개 가중치 모델 3종 사례로 "하나의 근거가 나머지를 보장하지 않는다"고 주장합니다. [사실: 프리프린트] [32]
- **목표-해악 갈등 (arXiv 2611.03374, 11-02)**: 협박·정렬 위장 같은 실패를 "목표 유지 vs 해악 회피"라는 하나의 구조로 묶고, 토큰 확률과 실제 행동을 나눠 측정합니다. [사실: 프리프린트] [33]

## 10. MCP 생태계

- 사양 최신 안정판은 그대로 `2026-07-28`입니다. Python SDK v2.3.0(10-02), TypeScript SDK v2.4.0(10-23)에서도 새 릴리스가 없습니다. [사실] [34]
- **Azure AGC MCP 게이트웨이 프리뷰 (11-03)**: `MCPRoute` 커스텀 리소스로 MCP 서버를 고정 호스트·경로 뒤에 공개하고 TLS, JWT 검증, WAF를 모읍니다. [사실] [24]
- **당근 광고 MCP (11-03)**: 위험이 낮은 조회부터 열고 수정은 검증 뒤로 미뤘으며, 결제·삭제는 열지 않기로 했습니다. "국내 최초"는 회사 측 표현입니다. [사실: 회사 공식 글, "최초"는 벤더 주장] [45]
- **MLflow 3.18.0**의 MCP 서버 버전 대소문자 구분 변경과 **Devin**의 OAuth 디스커버리는 각각 11절과 2절에 적었습니다.

## 11. MLOps / Feature Store

- **MLflow 3.18.0 (11-02)** [사실] [35][36]
  - 추가: Issues 탭의 자동 이슈 탐지, 실험 기능 Skill Registry, 평가·트레이스 비교 UI 개편과 실험 기능 `mlflow.genai.compare_evaluations()`, 코드 기반 온라인 스코어러(실험 기능), Databricks System One 저지, Helm 오토스케일링
  - **호환성 주의**: `search_logged_models`의 지표 정렬 변경, `models:/` 다운로드에서 `registered_model_meta` 제거, MySQL·SQL Server에서 MCP 서버 버전 대소문자 구분. DB 백업 후 `mlflow db upgrade`가 필요합니다.
- **Kubeflow Trainer v2.4.0-rc.0 (10-31, 최신 아님)**: 릴리스 후보입니다. [사실] [37]
- **Feast**: 0.67.0(10-13) 이후 새 릴리스가 없습니다. [사실] [38]

## 12. Agent Observability

- **Langfuse v4.73.0·v4.74.0 (11-03)**: AI 게이트웨이의 조직별 요청·바이트 속도 제한, 지원 접근 읽기의 감사 로그 기록, 조직 간 프로젝트 이전 Admin API. 종료된 모델을 게이트웨이에서 숨기는 수정도 포함됩니다. [사실] [39]
- **Arize Phoenix v21.0.0 (10-30, 최신 아님)**: 메이저 릴리스로 마이그레이션 문서가 있습니다. `PHOENIX_SECRET` 없이도 인증이 기본 활성화되고, 어노테이션 종류에 DECISION·AGENT가 추가됐습니다. [사실] [40]
- **Claude Code v2.1.317**: OTel 지표·이벤트·스팬에 `anthropic.plan`, `anthropic.seat_type`, `anthropic.provider`, `anthropic.custom_base_url`이 추가됐습니다. [사실] [13]
- **OTel GenAI semconv**: 저장소에서 MCP HTTP 오류 유형을 명확히 하는 변경(10-30)이 있었고, 안정성은 여전히 Development입니다. 필드가 바뀔 수 있습니다. [사실] [41]

## 13. Green Computing

- **IEC 리더십 브리핑 (2026년 11월)**: 데이터센터를 "Total Contribution = 긍정적 시스템 가치 − 부정적 시스템 부담"으로 평가하자는 틀을 제안합니다. [사실: 표준기구 정책 문서. 산업 편익을 포함하는 틀 자체에 이견이 있을 수 있음] [42]
- **유럽 데이터센터 데이터셋 (Zenodo, 11-01)**: EU-27과 영국·노르웨이·스위스의 2,980개 시설을 담았습니다. [사실: 저자 공개 데이터, 동료심사 여부 미확인] [43]

## 14. 국내 기업 기술 블로그 (네카라쿠배당토)

| 회사 | 제목 | 날짜 | 요약 | 링크 |
|---|---|---|---|---|
| 카카오 | 옮기는 것보다 증명이 어렵다 | 2026-11-03 | 커머스 클레임 검색 색인의 변경 수집을 변경 알림 기반에서 CDC로 전환한 검증 기록입니다. 공식 페이지의 메타 요약까지만 확인했고, 본문 세부는 **미확인**입니다. | [44] |
| 네이버 | 딸깍으로 안되는 Multi-interest 개발기 | 2026-11-03 | KREAM의 MINER 추천에서 특정 상품이 모든 유저에게 노출되는 hubness를 해결했습니다. 유저 무관 성분을 제거해 과노출 상품을 없애고 노출 상품 종류가 25% 늘었으며 구매 지표는 유지됐다고 밝혔습니다(회사 측 수치). | [47] |
| 네이버 | 컨테이너처럼 쓰고, VM처럼 격리하기: kata-containers with GPU | 2026-11-02 | 멀티테넌트 GPU 노드를 VM으로 격리하고 DRA로 GPU·NIC를 할당하며, 부팅 시간과 성능을 개선한 Engineering Day 세션입니다. | [48] |
| 네이버 | 사이드카의 선언적 관리: OpenKruise SidecarSet 도입과 운영 | 2026-10-29 (최신 아님) | DB Pod를 재시작하지 않고 사이드카만 선언적으로 갱신하기 위한 도입기입니다. 형상 관리, 배포, 모니터링 문제를 다룹니다. | [49] |
| 우아한형제들 | 아이폰 카메라로 B마트 상품을 찾는다고? | 2026-11-03 | 배민 앱을 Apple Visual Intelligence에 연동(App Intents)하고, AI 에이전트를 활용해 이미지 검색을 구성한 과정입니다. | [50] |
| 당근 | 국내 최초 광고 MCP를 출시하며, 개발자의 역할은 어디까지 넓어졌을까? | 2026-11-03 | 백엔드 엔지니어가 로드맵·PRD부터 출시까지 맡은 기록입니다. 위험이 낮은 조회부터 열었습니다. | [45] |

- LINE(LY)·토스: 11-03 브리핑 이후 새 글을 찾지 못했습니다. 쿠팡: 공식 피드 최신 글이 2024-10-14로 새 글이 없습니다. 두나무: 공식 기술 블로그를 확인하지 못했습니다. [미확인]
- 오늘 글 중 실제 장애 회고는 찾지 못했습니다. 운영 관점에서는 카카오의 전환 검증과 네이버의 SidecarSet 글이 가깝습니다.

## 15. Java/Spring 프리랜서 공고

수집 일자: 2026-11-04. 로그인 없이 볼 수 있는 공개 페이지만 확인했습니다.

**원 공고 (상세 페이지 확인)**

| 플랫폼 | 제목 | 스택 | 계약·근무 형태 | 금액 | 상태 | 링크 |
|---|---|---|---|---|---|---|
| 위시켓 | Java·Kubernetes 기반 대용량 이미지 처리 시스템 유지보수 | Java 5년+, Kafka 2년+, k8s 2년+, ETL 1년+ | 기간제, 미드 레벨(5~20년 차), 60일, 성남시 분당구, 즉시 시작 | 월 7,300,000원 | 모집 중, 마감 2026-11-17, 등록 11-03 | [51] |
| 위시켓 | Java/Spring 기반 호텔 식음료 POS 및 구매원가 시스템 운영·개발 | Java, Spring MVC, JSP, jQuery | 기간제, 시니어(11년 차+), 360일, 서울 광진구, 즉시 시작 | 월 7,500,000원 | 마감 2026-11-17 표시, 등록 11-03 | [52] |
| 잡코리아 | [프리랜서] 백엔드 개발자 경력채용(Java/Spring) — ㈜웅진씽크빅 | Java, Spring(제목 기준) | 프리랜서 5개월, 주5일, 서울 중구, 경력 5년+ | 회사 내규(면접 후 결정) | 접수 10-29~11-06 표시, 조기 마감 가능. **등록이 어제·오늘이 아니라 최신 공고는 아닙니다** | [53] |

- 수집 시점의 공개 페이지 기준이며, 지원 전에 원문 상태를 다시 확인하십시오.
- 위시켓의 LG전자·보험사 공고(159403, 159408, 159409)는 11-03 브리핑에서 다뤄 제외했습니다.
- **프리모아·이랜서**: 공개 페이지에서 오늘 등록된 Java/Spring 원 공고를 확인하지 못했습니다. 재수집 사이트의 "수집일"은 원 공고 등록일이 아니라서 근거로 쓰지 않았습니다. [미확인]

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- **TypeSafe Jev**: 공식 변경 이력의 최신 항목은 그대로 `jev-1.14.0`(10-14)입니다. 오늘 새 모델은 없습니다. [사실] [54]
- **MLflow 3.18.0의 Databricks System One 저지 (11-02)**: 평가 파이프라인에서 System One 계열 판정기를 쓸 수 있게 됐습니다. [사실] [35]
- **게이트웨이 계층의 수렴 (문서 날짜 미표기)**: LiteLLM은 `/v1/decisions`(OpenAI 형식)와 `/v1/systemone`(TypeSafe 형식)을 같은 공급자 목록으로 제공합니다. LangSmith LLM Gateway도 두 API를 각각 지원합니다. [사실] [55][56]
- **두 API는 호환되지 않습니다**: OpenAI는 `input`과 `predicate·choice·score`, System One은 `state`와 `noul·choice·score`(Jev 1.14는 `box` 추가)를 씁니다. [사실] [55][56][57]
- 속도·비용: OpenAI는 Responses API 대비 "최대 10배 빠르다"고 합니다(10-22, 최신 아님). [벤더 주장] [58] **Jev와 GPT-6 Luna를 직접 비교한 중립 벤치마크는 찾지 못했습니다(부재).**
- [추론] 판정 모델을 코드 전역에 직접 묶기보다 게이트웨이 뒤에 두면 교체는 쉬워집니다. 다만 응답 구조와 확률 의미가 달라 그대로 맞바꿀 수는 없으므로, 교체 전에 자기 데이터로 임계값을 다시 잡아야 합니다.

---

## 사실 · 추론 · 미확인 정리

**사실(1차·공식 확인)**: WordPress CVE의 KEV 등재·영향 버전·수정 버전, FlashProve 공개와 공식 한계, Claude 워터마크 대상 모델 3종, OpenAI 평가-운영 차이 수치(자사 실험), MLflow 3.18.0 변경, LangGraph SDK·CrewAI·Claude Code·Langfuse 릴리스, AWS·Azure·GCP·네이버 공지, 위시켓·잡코리아 공고의 표시 내용.

**벤더 주장(독립 재현 찾지 못함)**: FlashProve 성능, Wordfence 공격 요청 수, OpenAI Decisions 속도, 네이버 Multi-interest 개선 수치, 당근 "국내 최초".

**보도**: FlashProve 배포 계획 없음(TechCrunch), Ivanti 수정 버전(SecurityWeek), Java 생태계 릴리스(InfoQ).

**추론(필자 해석)**: FlashProve의 현실적 용도, WordPress 차단 순서, "목표 인지"의 위험 신호 해석, 판정 모델 게이트웨이 설계.

**미확인**: 워터마크의 Opus 4.6 포함·탐지 API·규제 일정 연관, 카카오 글 본문 세부, 두나무 기술 블로그, 프리모아·이랜서의 오늘자 원 공고, Python의 오늘 릴리스 상태, CVE-2026-119977로 인한 실제 침해 규모, Azure·AWS 일부 항목의 세부(제목 또는 요약까지만 확인).

## References

1. Anthropic, "Progress on provable inference for large language models". <https://www.anthropic.com/research/provable-inference>
2. Anthropic, FlashProve 저장소. <https://github.com/anthropics/FlashProve>
3. Russell Brandom, TechCrunch, 2026-11-03. <https://techcrunch.com/2026/11/03/anthropic-is-working-on-a-system-to-prove-ai-models-identity/>
4. Claude Platform release notes. <https://platform.claude.com/docs/en/release-notes/overview>
5. CrowdStrike 보도자료, 2026-11-03. <https://www.crowdstrike.com/en-us/press-releases/crowdstrike-extends-anthropics-claude-cowork/>
6. Canario et al., Journal of Neural Engineering, 2026-10-29. <https://doi.org/10.1088/1741-2552/aebb65>
7. CISA, KEV 추가 공지, 2026-11-03. <https://www.cisa.gov/news-events/alerts/2026/11/03/cisa-adds-one-known-exploited-vulnerability-catalog>
8. WordPress, GHSA-4w3m-c66w-69mg. <https://github.com/WordPress/wordpress-develop/security/advisories/GHSA-4w3m-c66w-69mg>
9. Wordfence, "WordPress 7.1.4 Patches Unauthenticated Upgrade…". <https://www.wordfence.com/blog/2026/10/wordpress-7-1-4-security-release-rce/>
10. LangGraph Releases. <https://github.com/langchain-ai/langgraph/releases>
11. CrewAI Changelog v1.15.35. <https://docs.crewai.com/v1.15.35/en/changelog>
12. Devin Release Notes. <https://docs.devin.ai/release-notes/2026>
13. Claude Code v2.1.317. <https://github.com/anthropics/claude-code/releases/tag/v2.1.317>
14. InfoQ, Java News Roundup, 2026-11-02. <https://www.infoq.com/news/2026/11/java-news-roundup-oct26-2026/>
15. Kubernetes Releases. <https://github.com/kubernetes/kubernetes/releases>
16. Kubernetes Blog Feed. <https://kubernetes.io/feed.xml>
17. AWS, EKS Capabilities Argo CD Notifications. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-argo-cd-notifications>
18. Centre for Cybersecurity Belgium, WordPress Core 경고. <https://ccb.belgium.be/advisories/warning-remote-command-execution-wordpress-core-during-upgrade-window-actively-exploited>
19. SecurityWeek, Ivanti zero-days. <https://www.securityweek.com/ivanti-patches-two-more-zero-days-exploited-in-connect-secure-attack-chain/>
20. CISA, ICSA-26-307-01. <https://www.cisa.gov/news-events/ics-advisories/icsa-26-307-01>
21. arXiv 2611.01953. <https://arxiv.org/abs/2611.01953>
22. AWS What's New 피드. <https://aws.amazon.com/about-aws/whats-new/recent/feed/>
23. Azure Updates 공식 피드. <https://www.microsoft.com/releasecommunications/api/v2/azure/rss>
24. Azure Updates, MCP gateway for Application Gateway for Containers. <https://azure.microsoft.com/updates?id=576388>
25. Google Cloud release notes. <https://docs.cloud.google.com/release-notes>
26. Google Cloud release notes(AlloyDB 항목 포함). <https://docs.cloud.google.com/release-notes>
27. 네이버 클라우드 공지. <https://www.ncloud.com/support/notice/all>
28. Rust Blog, rustup 1.29.3. <https://blog.rust-lang.org/2026/11/03/Rustup-1.29.3/>
29. Vue Releases. <https://github.com/vuejs/core/releases>
30. The Linux Kernel Archives. <https://www.kernel.org/>
31. OpenAI Alignment, "Eval-production behavior gaps…". <https://alignment.openai.com/eval-production-behavior-gap/>
32. Li et al., arXiv 2611.01620. <https://arxiv.org/abs/2611.01620>
33. Jaipersaud, Creager, arXiv 2611.03374. <https://arxiv.org/abs/2611.03374>
34. MCP 사양 Releases. <https://github.com/modelcontextprotocol/modelcontextprotocol/releases>
35. MLflow 3.18.0. <https://mlflow.org/releases/3.18.0/>
36. MLflow CHANGELOG. <https://raw.githubusercontent.com/mlflow/mlflow/refs/heads/master/CHANGELOG.md>
37. Kubeflow Trainer Releases. <https://github.com/kubeflow/trainer/releases>
38. Feast Releases. <https://github.com/feast-dev/feast/releases>
39. Langfuse v4.74.0. <https://github.com/langfuse/langfuse/releases/tag/v4.74.0>
40. Phoenix v21.0.0. <https://github.com/Arize-ai/phoenix/releases/tag/arize-phoenix-v21.0.0>
41. OTel GenAI semantic conventions. <https://github.com/open-telemetry/semantic-conventions-genai>
42. IEC Leadership Briefing. <https://www.iec.ch/basecamp/data-centres-briefing>
43. Raszka, Grycz, Vilamová, Zenodo, 2026-11-01. <https://doi.org/10.5281/zenodo.23864200>
44. 카카오, "옮기는 것보다 증명이 어렵다". <https://tech.kakao.com/posts/845>
45. 당근, 광고 MCP 글. <https://medium.com/daangn/%EA%B5%AD%EB%82%B4-%EC%B5%9C%EC%B4%88-%EA%B4%91%EA%B3%A0-mcp%EB%A5%BC-%EC%B6%9C%EC%8B%9C%ED%95%98%EB%A9%B0-%EA%B0%9C%EB%B0%9C%EC%9E%90%EC%9D%98-%EC%97%AD%ED%95%A0%EC%9D%80-%EC%96%B4%EB%94%94%EA%B9%8C%EC%A7%80-%EB%84%93%EC%96%B4%EC%A1%8C%EC%9D%84%EA%B9%8C-8dea7fe41c07>
46. Linus Torvalds, Linux 7.4-rc1 메일, 2026-11-01. <https://lists.openwall.net/linux-kernel/2026/11/01/932>
47. NAVER D2, Multi-interest 개발기. <https://d2.naver.com/helloworld/9639872>
48. NAVER D2, kata-containers with GPU. <https://d2.naver.com/helloworld/2265641>
49. NAVER D2, OpenKruise SidecarSet. <https://d2.naver.com/helloworld/2983631>
50. 우아한형제들 기술블로그. <https://techblog.woowahan.com/27810/>
51. 위시켓 공고 159436. <https://www.wishket.com/project/159436/>
52. 위시켓 공고 159424. <https://www.wishket.com/project/159424/>
53. 잡코리아 공고 50263540. <https://www.jobkorea.co.kr/Recruit/GI_Read/50263540>
54. TypeSafe Model changelog. <https://docs.typesafe.ai/changelog>
55. LiteLLM, /v1/decisions and /v1/systemone. <https://docs.litellm.ai/docs/decisions>
56. LangChain, LangSmith Decision models. <https://docs.langchain.com/langsmith/llm-gateway-decision-models>
57. OpenAI, Decisions guide. <https://developers.openai.com/api/docs/guides/decisions>
58. OpenAI, "Build more responsive apps with the Decisions API", 2026-10-22. <https://openai.com/index/decisions-api>
