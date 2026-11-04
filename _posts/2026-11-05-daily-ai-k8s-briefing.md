---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-05"
date: 2026-11-05 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-05 오전(KST). 수집 범위: 주로 11-03~11-04 발표. 날짜가 그보다 오래된 항목은 날짜와 함께 "최신 아님"이라고 따로 표시했습니다.
> 11-03·11-04 브리핑에서 다룬 소식은 새 진전이 있을 때만 다시 적었습니다.

**표기 규칙** — [사실] 1차·공식 출처로 확인 / [벤더 주장] 벤더 자체 수치·평가 / [보도] 언론 보도 / [추론] 필자 해석 / [미확인] 확인 못 함

## 오늘의 핵심

1. **Better Auth에서 계정 탈취로 이어지는 취약점 2건이 공개됐습니다.** `expo()` 플러그인은 피해자 이메일만 알면 인증 없이 탈취가 가능합니다. 1.7.16으로 올린 뒤 시크릿 교체까지 해야 합니다. [사실] [18][19]
2. **CISA KEV에 2024년 Apple 취약점 CVE-2024-27834가 추가됐습니다.** 기한은 11-18입니다. 오래전 패치된 CVE도 KEV에 새로 오를 수 있다는 사례입니다. 앞서 등재된 WordPress CVE-2026-119977의 기한은 내일(11-06)입니다. [사실] [14][15][16]
3. **GitHub Actions `pull_request_target` 차단 시험이 11-10 새벽(KST)에 처음 실행됩니다.** 공개 저장소에서 12-02부터 기본 차단되며, 그 전에 두 차례 일시 차단이 있습니다. [사실] [22]
4. **Anthropic이 Claude를 활용한 vault 입자 연구를 공개했습니다.** 원핵세포 vault의 첫 3D 구조라는 주장이며, 프리프린트는 동료심사 전이고 제3자 재현은 찾지 못했습니다. [벤더 주장] [1]
5. **OTel GenAI 규약에 검색(retrieval) 계측 변경과 실시간 세션 규약이 들어왔습니다.** 전용 저장소에는 아직 릴리스가 없어 main 기준 변경입니다. [사실] [52]

---

## 1. AI & ML

### Claude·Anthropic

- **Vault 입자 연구(11-04).** Anthropic 생물학 연구팀이 원핵세포 vault 입자의 첫 3D 구조를 발표했습니다. [벤더 주장] [1]
  - 구조: 박테리오파지 단백질 L05 96카피, 약 9.5MDa, 약 54×45nm. 포유류 vault(67×40nm)보다 부피가 약 25% 크다고 밝혔습니다.
  - 과정: 15개 단백질 중 7개가 입자를 형성했고, cryo-EM으로 4개를 확인했습니다. 정제는 통상 3일에서 약 90분으로 줄었고, 첫 구조 모델까지 34시간이 걸렸다고 합니다.
  - 한계: vault의 기능은 여전히 규명되지 않았습니다. 대장균(E. coli)에서만 제작했습니다. 프리프린트는 bioRxiv 제출 상태이며, 독립 재현은 찾지 못했습니다.
- **Claude Code v2.1.318(11-04).** `claude auth status`와 `claude -p` JSON에 로그인 만료 정보가 추가됐고, `-p` 텍스트 출력은 만료 10일 전부터 stderr에 경고를 띄웁니다. 무인 작업을 돌린다면 볼 만합니다. `--continue`가 이전 대화를 잃던 회귀(2.1.314)도 고쳤습니다. [사실] [5]
- **Claude Code의 게임 요청 처리 조정(The Verge, 11-04).** 2.1.317에서 프롬프트 규칙이 바뀌어, 장르·메커닉을 설명하려는 언급은 허용하고 복제 요청에는 비슷한 작품을 제안하도록 했다고 보도됐습니다. [보도] [4]
- **플랫폼 릴리스 노트.** 조사 시점 최신 항목은 11-03 워터마크 공지입니다(11-04에 다룸). 이후 새 항목은 없습니다. [사실] [70]

### 신경과학·BCI

- **USMEEG 디코딩(Science Advances, 11-04).** 자원자 10명의 SSVEP 실험에서 부호화 공간해상도 0.79mm를 보고했습니다. 평균 디코딩 상관은 변조 약·중·과에서 0.84·0.90·0.89입니다. 표본이 작아 일반화에는 추가 연구가 필요합니다. [사실] [2]
- **파킨슨 폐회로 DBS 바이오마커(npj Parkinson's Disease, 11-04).** 설치류 CBGT 회로 8개 부위를 동시 기록해 255개 조합을 평가했고, H-Lo-MLP가 약 90%, 임계값 방식이 약 50%의 성능을 보였습니다. 비인간 영장류는 1마리 개념 증명이며, 사람 임상 결과가 아닙니다. [사실] [3]

## 2. 에이전트 프레임워크

- **LangGraph·CrewAI**: 11-04에 다룬 SDK 0.4.12(11-03), CrewAI 1.15.35(11-03) 이후 새 릴리스는 조사 시점에 없습니다. [사실] [7][8]
- **Devin API v3**: 세션 생성 시 `memory_enabled: false`를 지정할 수 있습니다. 노트에는 "2026년 11월"로만 표기돼 정확한 날짜는 미확인입니다. 재현성이 중요한 자동화에서 쓸 만합니다. [사실] [6]
- **Claude Code**: §1의 v2.1.318을 참고하세요.

## 3. Kubernetes & Cloud Native

- **업스트림**: 최신 패치는 v1.37.2·v1.36.6·v1.35.10(10-28)이고, 개발 버전은 v1.38.0-alpha.3(10-28)으로 지난 보도 이후 변동이 없습니다. 공식 블로그에도 10-29 이후 새 글이 없습니다. [사실] [9][10]
- **IBM Cloud Kubernetes Service 1.37 제공(11-03).** 기본 버전은 아직 1.36이고, 1.34는 deprecated이며 지원 종료일은 2027-01-20입니다. [사실] [11]
- **AKS flex nodes 포털 지원 프리뷰(11-02, 최신 아님).** 다른 리전·온프레미스·엣지의 사용자 관리 머신을 기존 AKS 클러스터의 워커로 붙이는 기능에 포털 온보딩이 생겼습니다. 호스트 보안과 네트워크 연결은 사용자 책임입니다. [사실] [12]
- **Apigee Operator for Kubernetes 1.1.2(11-04).** Netty 4.1.137.Final, Jackson 2.21.7, Jetty 12.0.36, Vert.x 4.5.35, Guava 33.7.2-jre로 올려 다수 CVE를 해소했습니다. [사실] [13]

**가이드라인**: 패치 버전 변동이 없으므로 오늘 새로 할 업그레이드는 없습니다. Apigee Operator를 쓴다면 1.1.2 적용을 검토하세요. [추론]

## 4. 사이버 보안

### Exploits·KEV

- **CVE-2024-27834 (Apple 다수 제품) KEV 추가(11-04).** 임의 읽기·쓰기 능력을 가진 공격자가 포인터 인증을 우회할 수 있는 WebKit 문제입니다. 조치 기한은 11-18, 랜섬웨어 사용 여부는 Unknown입니다. Apple은 2024-05-13 Safari 17.5에서 수정했습니다. 어떤 공격에 쓰였는지는 CISA 공지에 없습니다. [사실] [14][15][16]
- **WordPress CVE-2026-119977 새 진전.** Wordfence는 지난 24시간 동안 13,095건을 차단했다고 밝혔습니다. 이는 벤더 수치이고 시도 건수이며 침해 건수가 아닙니다. KEV 기한은 11-06입니다. [보도·벤더 주장] [17]

### Identity Security·패치

- **Better Auth 보안 릴리스(11-03).** 수정 버전은 1.7.16과 1.8.0-beta.5입니다. [사실]
  - `@better-auth/expo`(GHSA-4wq4-2ppv-q3hg): 공개 엔드포인트가 요청에서 받은 값을 앱 시크릿으로 서명해 줍니다. 인증 없는 공격자가 사용자 이메일만 알면 로그인하고 계정 이메일까지 바꿀 수 있습니다. `expo()`를 등록했다면 영향을 받습니다. 시크릿을 교체해야 기존 서명이 무효화됩니다. [18]
  - `@better-auth/electron`(GHSA-9p5w-h4pr-fcrc): 로그인 응답에 auth 시크릿과 소셜 프로바이더 클라이언트 시크릿이 담길 수 있고, 플러그인 순서에 따라 2차 인증을 건너뛸 수 있습니다. 업그레이드해도 이미 노출된 값은 되돌릴 수 없어 전부 교체해야 합니다. [19]
- **Drupal Simple OAuth 모듈 CVE-2026-122058(11-04, Critical 15/25).** consumer를 만들거나 수정할 권한이 있는 사용자가 추가 권한 토큰을 받아 다른 사용자, 최대 전체 관리자 권한으로 접근할 수 있습니다. 6.1.4, 6.0.10, 5.2.6으로 올리고, 새 권한 부여와 기존 consumer 점검도 필요합니다. [사실] [20]
- **DreamHost 침해(TechCrunch, 11-04).** 8월부터 공격이 이어져 파일 관리자 취약점으로 세션 토큰이 탈취됐습니다. 고객 이메일과 자격 증명이 유출됐고, 피해 고객은 "10% 훨씬 미만"이라고만 밝혔습니다. 취약점 세부와 뒤늦은 탐지 이유는 공개되지 않았습니다. [보도] [21]
- **GitHub Actions `pull_request_target` 기본 차단(공지 11-02).** 12-02부터 공개 저장소에서 기본 차단되며, 비공개·내부 저장소와 GHES는 대상이 아닙니다. 일시 차단 시험은 11-09와 11-16의 16:00~18:00 UTC(KST 다음 날 01:00~03:00)에 진행됩니다. Insights로 영향받는 워크플로를 먼저 확인하세요. [사실] [22]

**미확인**: CISA의 11-05자 공지는 조사 시점에 찾지 못했습니다.

## 5. CSP

### AWS (11-03~11-04)

- **DataSync Enhanced mode OIDC**: Google Cloud Storage와 Azure Blob 전송에 HMAC·SAS 같은 장기 자격 증명이 필요 없어집니다. [사실] [23]
- **ECS Managed Daemons의 json-file 로그 수집**: ECS Managed Instances의 앱 컨테이너 로그를 데몬 하나가 root 권한이나 호스트 경로 지정 없이 읽을 수 있습니다. [사실] [24]
- **Interconnect last mile 프리뷰(Equinix)**, **EC2 Capacity Manager 신규 기능**, **WorkSpaces for AI agents의 Linux·Windows 11 지원**이 공지됐습니다. 제목과 요약 수준으로만 확인했습니다. [사실] [25][26][27]

### Azure

- **소버린 클라우드 확대(Campus Technology, 11-04).** Azure Managed HSM의 외부 키 관리가 GA이고, Sovereign Control Panel은 Ignite에서 공개 프리뷰로 나온다고 보도됐습니다. Microsoft 원문은 직접 확인하지 못했습니다. [보도] [29]
- **미확인**: Azure 공식 업데이트 RSS가 조사 환경에서 403을 반환해 오늘자 전체 목록은 확인하지 못했습니다.

### GCP (11-04)

- **AlloyDB 3건**: PG18 이상에서 Direct Iceberg 접근 프리뷰, BigQuery→AlloyDB 동기화 GA(`alloydb_sync`), AlloyDB Express 프리뷰(scale-to-zero, 첫 12개월 월 무료 구간)입니다. [사실] [13]
- **Cloud SQL for SQL Server** 읽기 풀 오토스케일링 GA, **Cloud Storage** 소프트 삭제 객체의 영구 삭제 일시 중지 기능이 추가됐습니다. [사실] [13]

### Naver Cloud

- 조사 시점의 공개 목록에서 최신 공지는 10-23자입니다. 11-04에 다룬 항목 외 새 공지는 확인되지 않았고, 목록이 수집 도구 캐시일 수 있습니다. [미확인] [30]

## 6. 개발 언어

| 언어 | 상태 | 근거 |
|---|---|---|
| Python | 안정판 3.15.2(10-25, 최신 아님). 3.16.0a2가 11-10 예정이고 PEP 823/824(`?.`, `??`)가 논의 중이라는 보도가 있습니다. | [사실·보도] [31][32] |
| Rust | 안정판 1.99.1(10-15, 최신 아님). 최근 6주 주기대로면 1.100은 11-12 전후로 보입니다. | [사실·추론] [33] |
| React | 19.3.1(10-14, 최신 아님). 이후 새 릴리스 없음. | [사실] [34] |
| Kotlin | 안정판 2.4.21(10-08), 2.5.0-Beta2(10-21). 둘 다 최신 아님. | [사실] [35] |
| Java·Spring | Spring Boot 4.1.2·4.0.9(10-22, 최신 아님). JRebel 2026.4.1(11-03)이 Spring Boot 4.1.2, Spring Framework 7.0.10, Kotlin 2.4.21을 지원합니다. | [사실] [36][39] |
| JS·TS 생태계 | Node.js 27.0 alpha(새 릴리스 모델, 2027-04 Current, 2027-10 LTS), RN 0.89 RC, Rspack 2.3, Vitest 5.1, Babel 8.1이 소개됐습니다. 이차 출처이므로 채택 전 각 프로젝트 공지를 확인하세요. | [보도] [37] |
| Parcel | Parcel 3 alpha(11-04)는 Rust로 재작성됐습니다. "최대 100배"는 벤더 주장이고, 중립 벤치마크는 찾지 못했습니다. | [벤더 주장] [38] |

Vue와 TypeScript는 11-03·11-04에 다룬 버전 이후 변동이 없습니다.

## 7. 인프라 & Linux

- **커널**: 조사 시점 mainline 7.4-rc1(11-01), stable 7.3.1(10-30), linux-next는 next-20261104입니다. 지난 보도 이후 새 stable·longterm은 없습니다. [사실] [40]
- **LWN "Managing the kernel CVE flood"(11-02, 최신 아님)**: 제목만 확인했고, 본문 세부는 미확인입니다. [41]
- **WorkSpaces 번들(11-04)**: RHEL 10, Rocky 10, Ubuntu 26.04 번들이 제공됩니다. [사실] [28]

## 9. AI 안전·정렬

이번 항목들은 모두 프리프린트이며 동료심사 전입니다. 새 공식 발표는 아니고, 지금까지 다루지 않은 논문을 날짜와 함께 소개합니다.

- **"Rewarded for Not Getting Caught"(arXiv 2611.02162, 11-01, 최신 아님).** 강화 기반 훈련은 규범을 가격처럼만 인코딩하므로 행동 평가의 증거력에 한계가 있다는 이론적 논증입니다. 실험 결과가 아닙니다. [42]
- **"Predictive Safety Guardrails Do Not Always Make LLM Agents Safer"(arXiv 2611.02815, 11-02, 최신 아님).** 7개 정책 모델과 2개 환경에서 예측 개입이 강해진다고 안전 이득이 단조 증가하지 않았습니다. 오염된 예측에서도 이득이 유지돼, 예측 내용이 충실히 반영되지 않았을 가능성을 시사합니다. [43]
- **Circuit Oracle(arXiv 2611.00420, 10-30, 최신 아님).** 거짓 특징 탐지는 78.2±2.4%였지만, 비밀 유도와 거부 억제는 기준선 대비 우위가 없었습니다. 긍정 결과와 부정 결과가 함께 나온 사례입니다. [44]

## 10. MCP 에코시스템

- **사양**: 안정판은 2026-07-28로 변동이 없습니다. Python SDK v2.3.0(10-02), TypeScript SDK v2.4.0(10-23) 이후 새 릴리스도 없습니다. [사실] [47][48]
- **Vercel MCP의 CIMD 지원(11-02, 최신 아님)**: Client ID Metadata Documents로 사전 허용목록 없이 클라이언트를 연결하고, 동의 화면에 호스트명을 보여 줍니다. [사실] [46]
- **공식 Ruby SDK Tier 1 승격(10-30, 최신 아님)**: 적합성 100%로 보고됐습니다. [사실] [45]

## 11. MLOps·피처스토어

- **Kubeflow Trainer v2.4.0-rc.1(11-04)**: 11-04에 다룬 rc.0의 후속 후보입니다. 릴리스 본문이 비어 있어 변경 세부는 미확인입니다. [사실] [49]
- **Feast**: 0.67.0(10-13) 이후 새 릴리스 없음. [사실] [50]
- **MLflow**: 3.18.0 이후 새 릴리스 없음. 내용은 11-04 브리핑을 참고하세요. [사실] [51]

## 12. 에이전트 관측성

- **OTel GenAI 규약 변경(11-03~11-04, main 기준).** [사실] [52]
  - #643: `gen_ai.client.operation.duration`에서 retrieval을 제외합니다.
  - #644: 내부 retrieval 스팬과 `gen_ai.retrieval.duration` 메트릭을 추가합니다.
  - #645: `gen_ai.retrieval.client` 스팬을 deprecated 처리합니다.
  - #394(11-04): 실시간 GenAI 세션 규약을 추가합니다.
  - 전용 저장소의 GitHub 릴리스는 0건입니다. 코어 semconv v1.45.0(11-02)은 별도 릴리스입니다. [53]
  - **영향 [추론]**: retrieval을 operation duration에 함께 세던 대시보드는 지표가 달라질 수 있습니다. 계측 라이브러리가 언제 반영할지는 미확인입니다.
- **Langfuse v4.75.0(11-04)**: AI Gateway 한도 상향(Pro/Team/Enterprise 10k req/min, 5 GiB/min), Codex 스킬 리소스 로드 추적 등이 포함됐습니다. [사실] [54]
- **CloudWatch API 키 지원(11-03)**: OpenTelemetry 트레이스 전송에 API 키를 쓸 수 있습니다. [사실] [55]
- **Phoenix**: client 7.18.1, CLI 1.19.2(11-04). 변경 세부는 미확인입니다. [56]

## 13. 그린 컴퓨팅

오늘자 새 1차 자료는 찾지 못했습니다. 아래는 지금까지 다루지 않은 공식 자료입니다.

- **EU 집행위 데이터센터 에너지 효율 보고서 COM(2026) 500(09-21, 최신 아님).** 전력 소비가 2024년 68TWh에서 2030년 114TWh(EU 전력 수요의 3.2%)로 늘 것으로 봤습니다. 평균 PUE 1.36, WUE 0.58, REF 0.86입니다. 자기 신고 기반이어서 해석에 주의가 필요합니다. [사실] [57]

## 14. 한국 기업 기술 블로그

| 회사 | 제목 | 날짜 | 요약 | 링크 |
|---|---|---|---|---|
| 네이버 | 크림에서 통합 임베딩(Universal Embedding)은 어떻게 쓰일까? | 2026-11-04 | 추천 구좌별 모델을 범용 임베딩 하나로 묶은 기록입니다. v1의 모델 붕괴, 768차원 비용, 조건 조합 한계를 v2에서 MRL과 Roaring Bitmap으로 풀었고, 응답 지연은 약 4배 빨라지고 메모리는 1/6로 줄었다고 밝혔습니다(회사 측 수치). | [58] |
| 네이버 | FE News 26년 11월 소식을 전해드립니다. | 2026-11-04 | 월간 프런트엔드 소식입니다. 제목과 날짜만 확인했습니다. | [59] |

- **장애·운영 회고**: 오늘자 새 글 가운데 실제 장애 회고는 확인되지 않았습니다.
- **새 글 없음**: 우아한형제들(최신 11-03), 당근(최신 11-03), 토스(최신 10-27), LY(최신 10-26)는 이미 다룬 글이거나 어제·오늘 새 글이 없습니다. [61][62][63][64]
- **미확인**: 카카오 "옮기는 것보다 증명이 어렵다"는 이번에도 본문을 읽지 못해 세부 내용을 적지 않았습니다. [60] 쿠팡은 공식 피드에서 최근 글을 확인하지 못했고, 두나무는 공식 원문을 확인하지 못했습니다.

## 15. Java/Spring 프리랜서 공고

수집 일자: 2026-11-05. 공개 페이지의 정보만 사용했습니다.

| 플랫폼 | 제목 | 스택 | 계약·근무 형태 | 금액 | 상태 | 링크 |
|---|---|---|---|---|---|---|
| 위시켓 | Java/Spring Boot 기반 교육 기업 레거시 ERP 통합 이관 백엔드 개발 | Java·Spring Boot, MS SQL Server, MySQL·MariaDB, Linux | 기간제, 90일, 미드 레벨(4~7년 차), 서울 서초구, 즉시 시작 | 협의 후 결정 | 11-04 등록, 마감 11-18, 지원자 7명 | [65] |
| 위시켓 | Java 기반 정부지원사업 공고 크롤링·기업 매칭 웹 서비스 고도화(주 20시간) | Java·JavaScript(풀스택) | 기간제, 30일, 미드 레벨(4~7년 차), 서울 금천구, 시작 11-30 | 월 2,000,000원 | 11-02 등록(최신 아님), 마감 11-14, 지원자 3명 | [66] |
| 위시켓 | Java/Spring Boot 기반 기업 웹 시스템 개발 및 운영 유지보수 | Java·Spring Boot, Servlet/JSP 레거시 병행 | 기간제, 60일, 시니어(8~10년 차), 서울 구로구, 즉시 시작 | 월 7,200,000원 | 10-30 등록(최신 아님), 마감 11-13, 지원자 17명 | [67] |

- 상태는 공개 페이지의 표시이며, 조사 도구의 수집 시점과 실제 시각 사이에 차이가 있을 수 있습니다. 지원 전 원문에서 다시 확인하세요.
- 위시켓 159436·159424 등은 11-04에 다뤘으므로 다시 싣지 않았습니다.
- **프리모아·이랜서**: 프리모아는 조사 도구에서 접속 오류가 났고, 이랜서는 공개 목록을 읽지 못했습니다. 재수집 사이트에 이랜서발 Java 공고가 보였지만 원문을 확인하지 못해 싣지 않았습니다. 두 플랫폼은 **오늘 확인된 검증 가능 공고 없음**입니다.

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- **새 모델 없음.** 공식 변경 이력의 최신 항목은 Jev 1.14(`jev-1.14.0`, 10-14)입니다. [사실] [68]
- **OpenRouter 연동 문서(작성일 미표기).** `typesafe/jev-1.14`와 `~typesafe/jev-latest`로 호출합니다. 문서 기준 컨텍스트는 262,144토큰이고 출력 토큰은 무료이며, 질문 유형은 Choice·Noul·Score·Box 4종입니다. Decisions API(`/api/alpha/decisions`)와 System One API(`/api/v1/systemone`) 두 경로가 있고, 추론·설명 출력은 없습니다. [사실] [69]
- **실무 관점 [추론]**: 출력이 판정에 한정되므로, 이유 설명이 필요한 흐름에서는 판정과 설명 모델을 분리하는 구성이 자연스러워 보입니다.
- **비교 근거**: Jev와 OpenAI Decisions·Luna를 직접 비교한 중립 벤치마크는 **부재**합니다. 우열을 단정할 근거가 없습니다.

---

## 사실 · 추론 · 미확인 정리

**사실(1차·공식 확인)**

- Better Auth 2건, Drupal CVE-2026-122058, CVE-2024-27834 KEV 추가, GitHub Actions 차단 일정.
- GCP·AWS 공식 공지, 커널·K8s·각 언어 버전, OTel GenAI 커밋, Langfuse v4.75.0, Jev 변경 이력.
- Science Advances와 npj Parkinson's Disease 논문의 게재 사실과 보고 수치.

**벤더 주장**

- Anthropic vault 연구의 구조·시간 단축 수치, Wordfence 차단 건수, Parcel "최대 100배", 네이버 크림 지연·메모리 수치, IBM·Vercel의 자사 기능 설명.

**보도**

- The Verge(Claude Code 게임 요청 처리), TechCrunch(DreamHost), BleepingComputer(WordPress), Campus Technology(Microsoft 소버린), Real Python·This Week in React(언어 생태계).

**추론**

- 패치 우선순위 판단, OTel 변경의 대시보드 영향, Rust 1.100 시점, Jev와 설명 모델 분리 구성.

**미확인**

- CVE-2024-27834의 구체적 공격 사례, CISA 11-05자 공지, Azure 오늘자 전체 목록, Naver Cloud 11월 신규 공지.
- Devin `memory_enabled`의 정확한 날짜, Kubeflow rc.1과 Phoenix의 변경 세부, 카카오 글 본문, 쿠팡·두나무 신규 글.
- 프리모아·이랜서 공고. Claude 워터마크의 규제·탐지 후속은 저권위 출처뿐이어서 싣지 않았습니다.

## References

1. Anthropic, Investigating vault particles with Claude. <https://www.anthropic.com/research/investigating-vault-particles-with-claude>
2. Science Advances, Sci. Adv. 12, eaei1954. <https://www.science.org/doi/10.1126/sciadv.aei1954>
3. npj Parkinson's Disease, s41531-026-01616-0. <https://www.nature.com/articles/s41531-026-01616-0>
4. The Verge, Anthropic tweaks how Claude Code handles requests about making games. <https://www.theverge.com/ai-artificial-intelligence/1026672/anthropic-tweaks-how-claude-code-handles-requests-about-making-games>
5. Claude Code v2.1.318 릴리스. <https://github.com/anthropics/claude-code/releases/tag/v2.1.318>
6. Devin API release notes. <https://docs.devin.ai/api-reference/release-notes>
7. LangGraph 릴리스. <https://github.com/langchain-ai/langgraph/releases>
8. CrewAI 릴리스. <https://github.com/crewAIInc/crewAI/releases>
9. Kubernetes 릴리스. <https://github.com/kubernetes/kubernetes/releases>
10. Kubernetes 블로그. <https://kubernetes.io/blog/>
11. IBM Cloud, IKS 1.37. <https://community.ibm.com/community/user/blogs/sean-stepanek/2026/11/03/iks-1-37-ga-blog-post>
12. Microsoft, Announcing flex nodes for AKS (preview) in Azure portal. <https://techcommunity.microsoft.com/blog/appsonazureblog/announcing-flex-nodes-for-aks-preview-in-azure-portal/4569460>
13. Google Cloud release notes. <https://docs.cloud.google.com/release-notes>
14. CISA, 2026-11-04 KEV 공지. <https://www.cisa.gov/news-events/alerts/2026/11/04/cisa-adds-one-known-exploited-vulnerability-catalog>
15. CISA KEV Catalog. <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
16. Apple, About the security content of Safari 17.5. <https://support.apple.com/en-us/120896>
17. BleepingComputer, CISA flags WordPress RCE flaw as actively exploited. <https://www.bleepingcomputer.com/news/security/cisa-flags-wordpress-rce-flaw-as-actively-exploited-in-attacks/>
18. Better Auth, GHSA-4wq4-2ppv-q3hg. <https://github.com/better-auth/better-auth/security/advisories/GHSA-4wq4-2ppv-q3hg>
19. Better Auth, GHSA-9p5w-h4pr-fcrc. <https://github.com/better-auth/better-auth/security/advisories/GHSA-9p5w-h4pr-fcrc>
20. Drupal, SA-CONTRIB-2026-296. <https://www.drupal.org/sa-contrib-2026-296>
21. TechCrunch, Hackers stole DreamHost customer files and inboxes. <https://techcrunch.com/2026/11/04/hackers-stole-dreamhost-customer-files-and-inboxes-during-months-long-attack/>
22. GitHub Changelog, pull_request_target blocked by default December 2. <https://github.blog/changelog/2026-11-02-pull_request_target-blocked-by-default-december-2/>
23. AWS, DataSync Enhanced mode OIDC. <https://aws.amazon.com/about-aws/whats-new/2026/11/datasync-enhanced-oidc-google-azure/>
24. AWS, ECS Managed Instances json-file 로그. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-ecs-managed-instances-json-file-log-driver/>
25. AWS, Interconnect last mile 프리뷰. <https://aws.amazon.com/about-aws/whats-new/2026/11/interconnect-last-mile-preview-equinix/>
26. AWS, EC2 Capacity Manager 신규 기능. <https://aws.amazon.com/about-aws/whats-new/2026/11/ec2-capacity-manager-supportability-and-fulfillment/>
27. AWS, WorkSpaces for AI agents. <https://aws.amazon.com/about-aws/whats-new/2026/11/workspaces-ai-agents-linux-windows-11>
28. AWS, RHEL 10·Rocky 10·Ubuntu 26.04 WorkSpaces 번들. <https://aws.amazon.com/about-aws/whats-new/2026/11/rhel-10-rocky-10-ubuntu-26-04-workspaces/>
29. Campus Technology, Microsoft Intros New Protections and Controls for Sovereign Cloud. <https://campustechnology.com/articles/2026/11/04/microsoft-intros-new-protections-for-sovereign-cloud.aspx>
30. Naver Cloud 공지사항. <https://www.ncloud.com/support/notice/all>
31. Python.org 다운로드. <https://www.python.org/downloads/>
32. Real Python, Python News November 2026. <https://realpython.com/python-news-november-2026/>
33. Rust 블로그. <https://blog.rust-lang.org/>
34. React 릴리스. <https://github.com/facebook/react/releases>
35. Kotlin 릴리스. <https://github.com/JetBrains/kotlin/releases>
36. Spring Boot 릴리스. <https://github.com/spring-projects/spring-boot/releases>
37. This Week in React #304. <https://thisweekinreact.com/newsletter/304>
38. Parcel v3 alpha. <https://v3.parceljs.org/blog/v3-alpha/>
39. JRebel 2026.4.1 릴리스 노트. <https://www.jrebel.com/products/jrebel/release-notes/202641-3rd-november-2026>
40. The Linux Kernel Archives. <https://www.kernel.org/>
41. LWN Kernel 페이지. <https://lwn.net/Kernel/>
42. arXiv 2611.02162, Rewarded for Not Getting Caught. <https://arxiv.org/abs/2611.02162>
43. arXiv 2611.02815, Predictive Safety Guardrails Do Not Always Make LLM Agents Safer. <https://arxiv.org/abs/2611.02815>
44. arXiv 2611.00420, Circuit Oracle. <https://arxiv.org/abs/2611.00420>
45. MCP 블로그. <https://blog.modelcontextprotocol.io/>
46. Vercel, Vercel MCP now supports Client ID Metadata Documents. <https://vercel.com/changelog/vercel-mcp-now-supports-client-id-metadata-documents>
47. MCP Python SDK 릴리스. <https://github.com/modelcontextprotocol/python-sdk/releases>
48. MCP TypeScript SDK 릴리스. <https://github.com/modelcontextprotocol/typescript-sdk/releases>
49. Kubeflow Trainer 릴리스. <https://github.com/kubeflow/trainer/releases>
50. Feast 릴리스. <https://github.com/feast-dev/feast/releases>
51. MLflow 릴리스. <https://github.com/mlflow/mlflow/releases>
52. OTel semantic-conventions-genai 커밋. <https://github.com/open-telemetry/semantic-conventions-genai/commits/main>
53. OTel semantic-conventions 릴리스. <https://github.com/open-telemetry/semantic-conventions/releases>
54. Langfuse v4.75.0. <https://github.com/langfuse/langfuse/releases/tag/v4.75.0>
55. AWS, CloudWatch API keys for OpenTelemetry. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-cloudwatch-api-keys-opentelemetry/>
56. Arize Phoenix 릴리스. <https://github.com/Arize-ai/phoenix/releases>
57. EU 집행위, COM(2026) 500. <https://build-up.ec.europa.eu/system/files/2026-10/39-2026-48_Report%20on%20the%20energy%20efficiency%20of%20data%20centres%20in%20the%20EU.pdf>
58. NAVER D2, 크림에서 통합 임베딩은 어떻게 쓰일까? <https://d2.naver.com/helloworld/7134499>
59. NAVER D2, FE News 26년 11월. <https://d2.naver.com/news/1095957>
60. 카카오, 옮기는 것보다 증명이 어렵다. <https://tech.kakao.com/posts/845>
61. 토스 기술 블로그. <https://toss.tech>
62. 당근 기술 블로그. <https://medium.com/daangn>
63. 우아한형제들 기술블로그. <https://techblog.woowahan.com/>
64. LY Corporation Tech Blog. <https://techblog.lycorp.co.jp/ko>
65. 위시켓 공고 159448. <https://www.wishket.com/project/159448/>
66. 위시켓 공고 159386. <https://www.wishket.com/project/159386/>
67. 위시켓 공고 159368. <https://www.wishket.com/project/159368/>
68. TypeSafe, Jev Model changelog. <https://docs.typesafe.ai/changelog>
69. OpenRouter, Jev 가이드. <https://openrouter.ai/docs/guides/community/jev>
70. Claude Platform release notes. <https://platform.claude.com/docs/en/release-notes/overview>
