---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-18"
date: 2026-11-18 08:30:03 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-18 08:30 KST · **수집 범위**: 2026-11-17 ~ 11-18 KST에 공개된 1차·공식 자료
> **표기**: **[사실]** 공식 원문으로 확인 · **[보도]** 신뢰 매체 보도(1차 원문 미확인 부분 포함) · **[벤더 주장]** 벤더 자체 수치·벤치마크(중립 재현 부재) · **[추론]** 필자 해석 · **[미확인]** 날짜·내용을 원문으로 확정하지 못함
> **중복 안내**: 11-17 브리핑에서 다룬 항목(LangGraph 1.2.22, CrewAI 1.15.41, K8s 1.38 일정, Check Point·UnrealIRCd KEV, MCP 릴리스 주기 글 등)은 새 진척이 없으면 반복하지 않습니다.

## 오늘의 핵심

1. **[사실]** Microsoft Ignite 2026(11-17): Azure Cobalt 200 VM GA, Azure AI Gateway 단독 제품 GA, Azure HorizonDB GA, 그리고 판단 전용 모델 **Microsoft-Decision-1.1** GA. 판단 모델은 8번 특집에서 다룹니다. [[1]](#ref-1) [[2]](#ref-2) [[3]](#ref-3) [[4]](#ref-4)
2. **[사실]** Kubernetes 블로그(11-16): kube-proxy **IPVS 백엔드가 1.40 에서 제거될 예정**입니다. nftables 또는 iptables 로 옮겨야 합니다. [[5]](#ref-5)
3. **[사실]** CISA 가 **Puppet Enterprise CVE-2026-115731**(리포트 역직렬화 RCE)을 KEV 에 추가했습니다(11-17, 연방기관 조치 기한 12-01). [[6]](#ref-6) [[7]](#ref-7)
4. **[사실]** Amazon EKS Auto Mode 에 **Pod rightsizing(Preview)** 이 나왔습니다. 권고 모드로 시작하고, 적용 모드에선 Pod 를 제자리에서 리사이즈합니다. [[8]](#ref-8)
5. **[사실]** Claude Platform 에 **Linked billing(beta)** 이 추가됐습니다. 앱이 요청마다 누가 비용을 낼지 정할 수 있습니다. [[9]](#ref-9)

---

## 1. AI & ML

- **[사실] Claude Platform — Linked billing (beta, 11-17)** — 고객이 자기 Claude 조직을 앱에 연결하면, 앱은 `/v1/messages`·`/v1/chat/completions` 요청마다 `billing_policy` 로 과금 주체를 고릅니다. 베타 헤더는 `user-profiles-billing-2026-10-01` 입니다. 고객은 Console 에서 지출 한도를 걸거나 연결을 끊을 수 있습니다. Anthropic 에 직접 결제하는 조직에만 적용됩니다. [[9]](#ref-9)
- **[미확인 날짜] Anthropic — "Testing Claude on real-world electronics design"** — Anthropic 리서치 페이지에 올라온 글입니다. Fable 5.2 가 스피커폰, 음성 비서 허브, 휴대용 가상 펫을 설계했고 Diode Computers 가 시제품을 만들었다고 합니다. 게시일을 원문에서 확정하지 못해 "최신"으로 표기하지 않습니다. [[10]](#ref-10)
- **[사실] Microsoft Foundry 모델 업데이트 (11-17)** — 모델 라우터 선택 대상이 44개 모델로 늘었고, 지원 프로젝트에선 자동 모델 선택이 기본값이 됐습니다. Managed Compute 도 GA 입니다(시간당 GPU 과금, Data Zone 지원). [[4]](#ref-4)
- **[사실] 신경과학·BCI** — 중국과학원 선양자동화연구소가 운동 상상 EEG 해독 네트워크 URCNet 을 발표했습니다(11-17, IEEE TCDS 게재). 공개 데이터셋 BCI Competition IV 2a/2b·Cho2017 에서 정확도 83.14% / 83.57% / 71.83% 를 보고했습니다. [[11]](#ref-11)
  - **[추론]** 저자 자체 평가 수치이며 독립 재현은 부재합니다.

## 2. AI 에이전트 프레임워크

- **[사실] Devin Desktop v3.14.30819 (11-17)** [[12]](#ref-12)
  - **Devin Bots**: 결과를 정해 주면 Bot 이 계획을 세우고 끝날 때까지 세션을 돌립니다.
  - `DetectProxy` 디바이스 정책과 `devin.network.detectProxy` 설정이 추가됐습니다.
  - 멈춘 스트림을 4분 기다리던 것을 40초 후 재시도로 바꿨습니다.
  - Anthropic 모델에서 턴 사이에 프롬프트 캐시를 유지합니다.
- **[사실] Devin Desktop v3.13.4 (11-17)** — Agent Command Center 에 탭이 생겼고, 로컬 세션이 백그라운드 프로세스로 돌며, 서브에이전트 출력이 중첩 표시됩니다. [[12]](#ref-12)
- **[사실] LangGraph·CrewAI** — 각각 1.2.22(11-14), 1.15.41(11-12)에서 변동 없습니다.

## 3. Kubernetes & 클라우드 네이티브

- **[사실] kube-proxy IPVS 제거 예정 (블로그 11-16, Dan Winship)** — IPVS 백엔드는 1.35 에서 deprecated 됐고 **1.40 에서 제거**될 예정입니다. 권장 경로는 1.33 에서 GA 된 nftables, 또는 iptables 입니다. [[5]](#ref-5)
  - **[추론]** `mode: ipvs` 를 쓰는 클러스터는 1.38 업그레이드 계획을 잡을 때 nftables 전환 검증 일정도 같이 넣는 게 안전합니다.
- **[사실] 릴리스 현황** — 변동 없음. v1.38.0-beta.0(11-06), 패치 v1.37.2·v1.36.6·v1.35.10·v1.34.13(10-28).
- **[사실] EKS Auto Mode Pod rightsizing (Preview, 11-17)** [[8]](#ref-8)
  - `ClusterResourceOptimizationPolicy` 를 만들면 Recommend 모드로 시작하고, Apply 모드에서 Pod 를 제자리 리사이즈합니다.
  - 메모리를 Java 힙보다 높게 유지하고, OOM kill 뒤엔 메모리를 올립니다.
  - HPA·KEDA 의 스케일 기준은 건드리지 않으며 VPA 관리 워크로드는 제외할 수 있습니다.
  - K8s 1.36 이상, 서울·도쿄 포함, 추가 요금 없음.

## 4. 사이버보안

- **[사실] Puppet Enterprise CVE-2026-115731 — KEV 추가 (11-17)** — CA 가 서명한 에이전트 인증서만 있으면 PUT 요청의 조작된 rich-data 타입으로 코드를 실행할 수 있습니다. autosign 이 켜져 있으면 인증 없는 공격자도 인증서를 받을 수 있습니다. 수정 버전은 PE 2026.0.1 / 2025.12.1 / 2023.8.13 이며, 인증서 이름 인가 우회 CVE-2026-115732 도 함께 고쳐졌습니다. [[6]](#ref-6) [[7]](#ref-7)
- **[보도] 일본 RIKEN, 슈퍼컴퓨터 후가쿠 오프라인 (11-17)** — 공개 상태 대시보드를 통해 11-10~11-13 침입이 있었고, 후가쿠 사용자 4,222명·Rikyu 사용자 375명 정보와 SSH 개인키가 노출됐다고 보도됐습니다. 11-14 에 시스템을 내렸습니다. [[13]](#ref-13)
- **[보도] Docker Hub 이미지에 유출된 클라우드 키, 수초 내 악용 (11-17)** — Stony Brook 연구진이 허니팟 이미지 300개를 공개해 측정했습니다. 최초 사용까지 최단 7.86초, 중앙값 51.19초였고 AWS 키 100개 모두 15분 안에 쓰였습니다. ACM CCS 발표 연구입니다. [[14]](#ref-14)
- **[보도] Optimizely 공급망 공격 (11-17 KST)** — Scott Helme 가 178개 조직에서 감염된 JS 파일 188개를 찾았습니다. 카드 스키머, 암호화폐 지갑 주소 바꿔치기, iOS 익스플로잇 킷이 실렸습니다. 침해 원인은 아직 밝혀지지 않았습니다. [[15]](#ref-15)
- **[보도] 아이덴티티 — Uber 운전자 149,346명 통지 (11-17)** — 외부 업체 Fireworks 침해로 인한 것입니다. [[16]](#ref-16)
- **[벤더 주장] Microsoft 365 세션 탈취 피싱 킷 (Huntress 스폰서 글, 11-17)** — EvilTokens, Knight Office, Kali365 를 분석하고 디바이스 코드 플로 제한과 리프레시 토큰 폐기를 권합니다. [[17]](#ref-17)
- **[보도] NoisyTCP CVE-2026-99288 (11-16)** — Linux 커널 TCP NULL 포인터 역참조로 원격에서 서버를 멈출 수 있습니다. 7장 커널 안정판 갱신과 함께 확인하세요. [[18]](#ref-18)

## 5. CSP (AWS · Azure · GCP · 네이버클라우드)

**AWS (모두 11-17)**

- **[사실] IAM Access Troubleshooter** — 접근 거부 오류에 식별자가 붙어, 평가된 정책과 인가 컨텍스트를 조회할 수 있습니다. [[19]](#ref-19)
- **[사실] API Gateway REST API 네이티브 JWT authorizer** — 여러 issuer·audience·알고리즘·claim 을 지원해 Lambda authorizer 없이 검증합니다. [[20]](#ref-20)
- **[사실] ECR 글로벌 인증 토큰** — Sign-In CreateBearerToken API 로 파티션 전체에 쓰는 토큰 하나를 받습니다. 기본 12시간, 최소 5분까지 줄일 수 있습니다. [[21]](#ref-21)
- **[사실] Agentic account creation** — Claude Code·Codex·Cursor 같은 코딩 하네스가 AWS 가입을 열고 단기 자격증명을 돌려받을 수 있습니다. [[22]](#ref-22)
- **[사실] AWS Interconnect – multicloud (Azure) GA** — us-east-1, ap-southeast-2, eu-central-1. [[23]](#ref-23)
- **[사실] 그 밖의 발표** — EMR 8.2 LTS(Spark 4.1.3, Iceberg 1.11.0), Security Hub 의 GCP 확장, 리전 간 VPC/TGW/Cloud WAN 트래픽 99.999% SLA, Route 53 DNS Firewall 자동 허용목록, Bedrock 의 OpenAI GPT-6.2 Astra·Sol GA 등. [[24]](#ref-24)

**Azure (Ignite 2026, 11-17)**

- **[사실] Cobalt 200 VM GA** — 14개 리전(Korea Central 포함), 연말까지 23개 리전. [[1]](#ref-1)
  - **[벤더 주장]** Cobalt 100 대비 최대 50% 성능 향상, Java 워크로드 최대 1.6배.
- **[사실] Azure AI Gateway GA** — API Management 의 AI Gateway 티어였던 것이 단독 제품이 됐습니다. 모델·MCP 도구 접근을 Entra ID 로 통제하고, 게이트웨이당 월 1만 요청까지 무료이며 유료 과금은 2027-01-01 시작입니다. [[2]](#ref-2)
- **[사실] Azure HorizonDB GA** — 클라우드 네이티브 아키텍처의 PostgreSQL, 최대 128 TB, 기본 가용영역 이중화. [[3]](#ref-3)
  - **[벤더 주장]** 자체 관리 PostgreSQL 대비 OLTP 최대 8배(HammerDB TPROC-C 내부 벤치마크).
- **[사실] Sovereign Private Cloud** — Azure Local 에서 Foundry Local, AMD SEV-SNP 기반 confidential VM, GitHub Enterprise Local 이 GA 입니다. [[25]](#ref-25)

**GCP**

- **[사실] "Sovereign AI on your terms, made with Europe" (11-17)** — 파트너가 운영하는 Google Cloud Dedicated 에 Gemini 를 제공하고, 암호 키 통제·컴플라이언스 기능을 추가합니다. 브뤼셀 Sovereign AI Summit 발표입니다. [[26]](#ref-26)

**네이버클라우드**

- **[사실] 공지 (11-16~17)** — 11월 정기 상품 출시 및 점검(11-24), Windows Server 2025 이미지 신규 출시(11-24, KR), NAVIX 9.6 이미지 판매 종료(2027-01-21 예정), GAMEPOT 한국 리전 배포(11-24). [[27]](#ref-27)

## 6. 언어 (Python · Rust · React · Vue · Java · Kotlin · JS · TS)

- **[사실] Java — "Why It Takes 3000 Commits to Bring Valhalla's Value Objects to the JDK" (Inside.java, 11-16, David Simms)** — 값 객체를 JDK 에 넣기까지의 변경 범위를 설명하는 글입니다. [[28]](#ref-28)
- **[사실] Python** — Python Insider(11-16): XTM Transifex 가 문서 번역을 후원합니다. 언어·런타임 변경은 아닙니다. [[29]](#ref-29)
- **변동 없음** — TypeScript 최신은 7.1 Beta(10-20). Rust·React 는 11-16 이후 새 공식 글이 없습니다. Vue·Kotlin 은 이번 회차에 날짜를 확정할 새 글을 찾지 못했습니다(**[미확인]**).

## 7. 인프라 & Linux

- **[사실] kernel.org (11-17)** — stable 7.3.5, longterm 6.18.64·6.12.118 이 나왔습니다. mainline 은 7.4-rc3(11-15). [[30]](#ref-30)
- **[사실] Azure Local** — 관리 control plane 을 재배포 없이 옮기는 기능, 연결형→단절형 전환(Preview), SQL Server GA. [[25]](#ref-25)

## 9. AI 안전 & 정렬

- **[사실] Linked billing 의 지출 한도·연결 해제** — 1장 참조. 앱이 사용자 조직에 비용을 넘길 때 사용자 쪽 통제 수단이 함께 제공됩니다. [[9]](#ref-9)
- **[사실] Azure AI Gateway** — 모든 프롬프트·응답을 Azure AI Content Safety 로 검사하고, 승인된 도구만 노출하도록 게이트웨이에서 막을 수 있습니다. [[2]](#ref-2)
- Anthropic Alignment 블로그와 연구 페이지에서 11-17~18 날짜로 확정된 새 글은 찾지 못했습니다.

## 10. MCP 생태계

- **[사실] Azure AI Gateway** — 모델과 함께 **MCP 도구** 접근을 하나의 경로로 묶고, 도구 자격증명이 앱 코드에 닿지 않게 합니다. [[2]](#ref-2)
- **[사실] Foundry Local (Azure Local)** — 로컬 검색·인덱싱에 MCP 서버를 포함합니다. [[25]](#ref-25)
- **[사실] 사양** — 최신 안정판은 `2026-07-28` 그대로입니다. MCP 블로그에는 11-12 브리핑에서 다룬 11-10·11-11 글 이후 새 글이 없습니다. [[31]](#ref-31)

## 11. MLOps / 피처 스토어

- **[사실] 토스 — "같은 모델, 다른 예측" (11-17)** — 학습-서빙 skew 의 원인 세 가지(파티션 불일치, 업로드 타이밍, 오래된 값)를 짚고 point-in-time 조인과 피처 파티션으로 맞추는 과정을 다룹니다. [[32]](#ref-32)
- **[사실] 토스 — 타겟팅 모델 개발 자동화 TASTE (11-17)** — 피처 수 자동 선택(auto_k), 모델 비교·평가·데이터 결측 가드를 자동화했습니다. [[33]](#ref-33)
  - **[벤더 주장]** 학습 기간 2주 → 1일(회사 자체 수치).
- **[사실] AWS** — SageMaker AI 데이터 준비 기능, HyperPod 클러스터 운영 기능, EMR Serverless 용 Spark Optimization Agent(11-17). [[24]](#ref-24)

## 12. 에이전트 관측성

- **[사실] Langfuse v4.82.0 (11-17)** — 프로바이더별 사용량·비용 정규화, ClickHouse 기반 감사 로그 조회, LLM 평가기가 프로바이더 429 를 받으면 호출 안에서 재시도하지 않고 연결을 일시정지. **GitHub Enterprise SSO 설정의 SSRF 수정**도 포함돼 자체 호스팅이면 업그레이드 대상입니다. [[34]](#ref-34)
- **[사실] AWS Bedrock AgentCore Memory** — 단기 메모리 10년 보존, 세션 전체 요약(11-17). [[24]](#ref-24)
- **[사실] OpenTelemetry 블로그** — 블로그 정책 변경(11-17), 2026 커뮤니티 어워드(11-16). 시맨틱 컨벤션 변경은 없습니다. [[35]](#ref-35)

## 13. 그린 컴퓨팅

- **[사실] Amazon — 전력 탄소 집약도 65% 감축 목표 (11-17)** — 2030년까지 사용 전력 MWh 당 CO₂e 를 2019년 대비 65% 줄이겠다고 밝혔습니다. IEA Net Zero 2050 경로를 기준으로 했다고 합니다. [[36]](#ref-36)
- **[사실] Google–Quaise 50 MW 초고온 지열 PPA (11-17)** — 오리건 The Dalles 데이터센터용, 이르면 2030년 공급 시작. [[37]](#ref-37)
- **[사실] EU Horizon Europe 공모 "Energy efficiency and sustainability of AI data processing in Data Centres" (11-17 개시)** — 예산 €39M, 마감 2027-03-18. 칩 수준 냉각, 탄소 인지 스케줄링, 폐열 재사용 등이 대상입니다. [[38]](#ref-38)
  - **[추론]** 중립 제3자의 데이터센터 에너지 측정 자료는 이번 회차에 새로 나온 것이 없습니다(부재).

## 14. 국내 기업 기술블로그

| 기업 | 제목 | 날짜 | 요약 | 원문 |
| --- | --- | --- | --- | --- |
| 당근 | GitHub Actions 모니터링의 빈칸: Exporter로 ARC Runner 관측하기 | 2026-11-17 | K8s 위 ARC 셀프호스티드 러너의 대기 잡과 러너 Pod 매핑을 보려고 Exporter 를 직접 만든 SRE 글 | [원문](https://medium.com/daangn/github-actions-%EB%AA%A8%EB%8B%88%ED%84%B0%EB%A7%81%EC%9D%98-%EB%B9%88%EC%B9%B8-exporter%EB%A1%9C-arc-runner-%EA%B4%80%EC%B8%A1%ED%95%98%EA%B8%B0-cbe1a46a9e71) |
| 토스 | 같은 모델, 다른 예측 | 2026-11-17 | 학습-서빙 skew 원인 3가지와 PIT 조인·파티션 정렬 | [원문](https://toss.tech/article/training-serving-skew) |
| 토스 | 판단에만 집중하세요: 토스 타겟팅 모델 개발 자동화 | 2026-11-17 | TASTE 파이프라인으로 피처 선택·비교·평가 자동화 | [원문](https://toss.tech/article/targeting-model-automation) |
| 토스 | 지표 뒤에 숨은 맥락을 한눈에: New20 Timeline Hub 만들기 | 2026-11-17 | 정책·세그먼트·화면·실험·데이터 5개 레인을 한 타임라인에 | [원문](https://toss.tech/article/new20-timeline-hub) |
| 카카오 | if(kakao)26 현장 스케치 | 2026-11-17 | 컨퍼런스 현장 후기(행사 글) | [원문](https://tech.kakao.com/posts/849) |
| 우아한형제들 | 이래라저래라 하지 마라: 주니어를 성장시키는 파트너십 대화법 | 2026-11-17 | 조직문화 글 | [원문](https://techblog.woowahan.com/28524/) |

- 네이버 D2(11-16 이후), LINE(11-13 이후)은 새 글이 없습니다. 쿠팡·두나무는 이번 회차에 새 글을 확인하지 못했습니다(**[미확인]**).

## 15. Java/Spring 프리랜서 공고

수집일 2026-11-18. 공개 페이지에서 확인되는 정보만 적었습니다(로그인 필요 정보는 수집하지 않음).

| 플랫폼 | 제목 | 스택 | 형태 | 금액 | 등록/마감(상태) | 원문 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | Java 기반 차세대시스템 견적·주문 영역 분석·설계 및 개발 | Java (상세 스택은 로그인 필요) | 기간제 상주, 390일, 서울 강동구, PL·고급(11년+) | 월 8,000,000원 | 11-17 등록 / 12-01 마감(모집 중) | [원문](https://www.wishket.com/project/159690/) |
| 위시켓 | Apache NiFi 기반 패션 데이터 허브 구축 데이터 엔지니어 | Apache NiFi, Linux, SQL, Python 또는 Java/Groovy 스크립트 | 기간제 상주, 150일(12-01 시작), 서울 강남, 고급(10년+) | 월 7,500,000원 | 11-16 등록 / 11-30 마감(모집 중) | [원문](https://www.wishket.com/project/159649/) |

- **프리모아·이랜서**: 공개 페이지는 응답했지만 목록이 스크립트로 렌더링되거나 로그인 뒤에 있어 Java/Spring 공고를 텍스트로 확인하지 못했습니다. 오늘 확인된 검증 가능 공고 없음.
- 11-17 브리핑의 위시켓 159666·159668 등은 반복하지 않았습니다.

---

## 8. [특집] Jev API 와 판단 모델

### 오늘의 변화

- **[사실] Microsoft-Decision-1.1 GA (Ignite, 11-17)** — Microsoft 가 라우팅·분류·우선순위·검증용 빠르고 저렴한 판단 모델을 GA 로 냈습니다. Gemma 기반이고 이번 버전에서 이미지 입력을 지원합니다. Foundry 모델 카탈로그에 있습니다. [[4]](#ref-4) [[39]](#ref-39)
- **[사실] Jev** — 공식 변경 로그는 여전히 **Jev 1.14(10-14)** 가 최신입니다. 새 릴리스는 없습니다. [[40]](#ref-40)

### 어떻게 읽을 것인가

- **[사실]** 판단 전용 모델 진영이 Jev(10월), Google `gemini-decision-1`(11-11, 11-12 브리핑), Microsoft-Decision-1.1(11-17)로 세 곳이 됐습니다.
- **[사실]** Microsoft 는 이 모델을 "복잡한 작업엔 큰 모델, 반복적인 구조화 판단엔 작은 모델"이라는 분업 구도 안에 놓고, 같은 날 모델 라우터(44개 모델)도 기본값으로 켰습니다. [[4]](#ref-4)
- **[추론]** 판단 모델은 이제 독립 API 라기보다 클라우드 플랫폼의 라우팅·검증 계층 부품으로 들어가는 흐름입니다. Jev 가 차별화할 지점은 확률·근거 같은 출력 계약의 투명성일 가능성이 큽니다.
- **[미확인]** Microsoft-Decision-1.1 과 Jev·Gemini 판단 모델을 같은 조건에서 비교한 중립 벤치마크는 부재합니다. 성능 우열은 말할 수 없습니다.

### 실무 체크포인트

- 판단 모델을 바꿔 끼울 땐 **출력 형식**(선택지·확률·confidence)이 같은지 먼저 봅니다. 같은 "분류"라도 스키마가 다르면 다운스트림 임계값이 깨집니다.
- 모델 라우터를 기본값으로 켜면 어떤 요청이 어떤 모델로 갔는지 남겨야 합니다. 판단 결과를 감사할 땐 모델 ID 가 필수입니다.
- 평가는 자기 도메인 데이터로 따로 돌립니다. 벤더가 공개한 수치는 벤더 주장입니다.

---

## 사실 · 추론 · 미확인 정리

- **사실**: Claude Linked billing(beta), Devin v3.14.30819·v3.13.4, kube-proxy IPVS 1.40 제거 예정, EKS Pod rightsizing Preview, Puppet CVE-2026-115731 KEV, AWS 11-17 발표들, Ignite 2026 GA 발표(Cobalt 200·AI Gateway·HorizonDB·Microsoft-Decision-1.1·Foundry Local), GCP 소버린 AI, 네이버클라우드 공지, kernel 7.3.5, Langfuse v4.82.0, Amazon 탄소 집약도 목표, Google–Quaise PPA, EU 공모, 국내 블로그 6편, 위시켓 공고 2건.
- **벤더 주장·보도**: Cobalt 200 성능 수치, HorizonDB 8배, 토스 TASTE 2주→1일, Huntress 피싱 킷 분석, RIKEN 후가쿠·Optimizely·Docker Hub 키·Uber·NoisyTCP 보도.
- **추론**: IPVS 전환 일정 권고, 판단 모델의 플랫폼 부품화와 Jev 차별화 지점.
- **미확인**: Anthropic 전자설계 글의 게시일, 판단 모델 간 중립 비교, Vue·Kotlin 새 글, 쿠팡·두나무 새 글, 프리모아·이랜서 공고.

## References

<a id="ref-1"></a>[1] Microsoft Azure Blog, "Azure Cobalt 200 VMs now available, proven on real workloads and built for the agentic era" (2026-11-17) — <https://azure.microsoft.com/en-us/blog/azure-cobalt-200-vms-now-available-proven-on-real-workloads-and-built-for-the-agentic-era/>

<a id="ref-2"></a>[2] Microsoft Tech Community, "Azure AI Gateway is now generally available" (2026-11-17) — <https://techcommunity.microsoft.com/blog/integrationsonazureblog/azure-ai-gateway-is-now-generally-available-ship-faster-stay-in-control/4572644>

<a id="ref-3"></a>[3] Microsoft Tech Community, "HorizonDB: PostgreSQL for enterprises, developers, and agents on Azure and Fabric" (2026-11-17) — <https://techcommunity.microsoft.com/blog/adforpostgresql/horizondb-postgresql-for-enterprises-developers-and-agents-on-azure-and-fabric/4573498>

<a id="ref-4"></a>[4] Microsoft Tech Community, "From model choice to your durable advantage: Build AI that keeps improving" (2026-11-17) — <https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/from-model-choice-to-your-durable-advantage-build-ai-that-keeps-improving/4573609>

<a id="ref-5"></a>[5] Kubernetes Blog, "IPVS removal" (2026-11-16) — <https://kubernetes.io/blog/2026/11/16/ipvs-removal/>

<a id="ref-6"></a>[6] CISA, "CISA Adds One Known Exploited Vulnerability to Catalog" (2026-11-17) — <https://www.cisa.gov/news-events/alerts/2026/11/17/cisa-adds-one-known-exploited-vulnerability-catalog>

<a id="ref-7"></a>[7] Puppet, "What's new in Puppet Enterprise" — <https://www.puppet.com/products/puppet-enterprise/whats-new>

<a id="ref-8"></a>[8] AWS What's New, "EKS Auto Mode Pod rightsizing (Preview)" (2026-11-17) — <https://aws.amazon.com/about-aws/whats-new/2026/11/eks-auto-mode-pod-rightsizing-preview/>

<a id="ref-9"></a>[9] Claude Platform Release Notes (2026-11-17) — <https://platform.claude.com/docs/en/release-notes/overview>

<a id="ref-10"></a>[10] Anthropic Research, "Testing Claude on real-world electronics design" — <https://www.anthropic.com/research>

<a id="ref-11"></a>[11] Shenyang Institute of Automation, CAS, "U-Shaped Riemannian Manifold Network Advances Non-Invasive Brain-Computer Interface Decoding" (2026-11-17) — <http://english.sia.cas.cn/news/Research_Progress/202611/t20261117_1219676.html>

<a id="ref-12"></a>[12] Devin Docs, Desktop Changelog — <https://docs.devin.ai/desktop/changelog>

<a id="ref-13"></a>[13] BleepingComputer, "Japan takes Fugaku supercomputer offline after cyberattack" (2026-11-17) — <https://www.bleepingcomputer.com/news/security/japan-takes-fugaku-supercomputer-offlline-after-cyberattack/>

<a id="ref-14"></a>[14] BleepingComputer, "Cloud keys leaked in Docker Hub images are stolen within seconds" (2026-11-17) — <https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/>

<a id="ref-15"></a>[15] BleepingComputer, "Optimizely supply chain attack infects major brands' sites with malware" (2026-11-16 US) — <https://www.bleepingcomputer.com/news/security/optimizely-supply-chain-attack-infects-major-brands-sites-with-malware/>

<a id="ref-16"></a>[16] BleepingComputer, "Uber notifies drivers of data breach affecting nearly 150,000 people" (2026-11-17) — <https://www.bleepingcomputer.com/news/security/uber-notifies-drivers-of-data-breach-affecting-nearly-150-000-people/>

<a id="ref-17"></a>[17] BleepingComputer (Huntress 스폰서), "Inside modern phishing kits built to steal Microsoft 365 sessions" (2026-11-17) — <https://www.bleepingcomputer.com/news/security/inside-modern-phishing-kits-built-to-steal-microsoft-365-sessions/>

<a id="ref-18"></a>[18] BleepingComputer, "New NoisyTCP Linux kernel flaw lets attackers crash servers" (2026-11-16) — <https://www.bleepingcomputer.com/news/linux/new-noisytcp-linux-kernel-flaw-lets-attackers-crash-servers/>

<a id="ref-19"></a>[19] AWS What's New, IAM Access Troubleshooter (2026-11-17) — <https://aws.amazon.com/about-aws/whats-new/2026/11/iam-access-troubleshooter/>

<a id="ref-20"></a>[20] AWS What's New, API Gateway REST JWT authorizers (2026-11-17) — <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-api-gateway-rest-jwt-authorizers/>

<a id="ref-21"></a>[21] AWS What's New, Global authentication for Amazon ECR (2026-11-17) — <https://aws.amazon.com/about-aws/whats-new/2026/11/global-authentication-amazon-ecr/>

<a id="ref-22"></a>[22] AWS What's New, Agentic account creation (2026-11-17) — <https://aws.amazon.com/about-aws/whats-new/2026/11/agentic-account-creation/>

<a id="ref-23"></a>[23] AWS What's New, AWS Interconnect – multicloud with Azure GA (2026-11-17) — <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-announces-AWS-interconnect-multicloud-azure-ga/>

<a id="ref-24"></a>[24] AWS What's New, 2026-11 목록 (EMR 8.2, Security Hub GCP, 99.999% SLA, AgentCore Memory, SageMaker 등) — <https://aws.amazon.com/about-aws/whats-new/2026/11/>

<a id="ref-25"></a>[25] Microsoft Tech Community, "What's new with Sovereign Private Cloud at Microsoft Ignite 2026" (2026-11-17) — <https://techcommunity.microsoft.com/blog/azurearcblog/whats-new-with-sovereign-private-cloud-at-microsoft-ignite-2026/4573886>

<a id="ref-26"></a>[26] Google Cloud Blog, "Sovereign AI on your terms, made with Europe" (2026-11-17) — <https://cloud.google.com/blog/products/identity-security/sovereign-ai-on-your-terms-made-with-europe>

<a id="ref-27"></a>[27] 네이버클라우드 플랫폼 공지사항 — <https://www.ncloud.com/support/notice/all>

<a id="ref-28"></a>[28] Inside.java, "Why It Takes 3000 Commits to Bring Valhalla's Value Objects to the JDK" (2026-11-16) — <https://inside.java/>

<a id="ref-29"></a>[29] Python Insider (2026-11-16) — <https://blog.python.org/>

<a id="ref-30"></a>[30] The Linux Kernel Archives — <https://www.kernel.org/>

<a id="ref-31"></a>[31] modelcontextprotocol/modelcontextprotocol Releases — <https://github.com/modelcontextprotocol/modelcontextprotocol/releases>

<a id="ref-32"></a>[32] 토스 기술블로그, "같은 모델, 다른 예측" (2026-11-17) — <https://toss.tech/article/training-serving-skew>

<a id="ref-33"></a>[33] 토스 기술블로그, "판단에만 집중하세요: 토스 타겟팅 모델 개발 자동화" (2026-11-17) — <https://toss.tech/article/targeting-model-automation>

<a id="ref-34"></a>[34] Langfuse Releases, v4.82.0 (2026-11-17) — <https://github.com/langfuse/langfuse/releases>

<a id="ref-35"></a>[35] OpenTelemetry Blog — <https://opentelemetry.io/blog/>

<a id="ref-36"></a>[36] About Amazon, "Amazon sets goal to cut electricity carbon emissions 65% by 2030" (2026-11-17) — <https://www.aboutamazon.com/news/sustainability/amazon-carbon-intensity-goal-electricity-emissions>

<a id="ref-37"></a>[37] Quaise Energy, "Quaise Energy Signs 50 MW Geothermal Power Purchase Agreement with Google" (2026-11-17) — <https://www.quaise.com/news/quaise-energy-signs-50-mw-geothermal-power-purchase-agreement-with-google>

<a id="ref-38"></a>[38] Horizon Europe (France 포털), "Energy efficiency and sustainability of AI data processing in Data Centres" (개시 2026-11-17) — <https://www.horizon-europe.gouv.fr/energy-efficiency-and-sustainability-ai-data-processing-data-centres-ia-42639>

<a id="ref-39"></a>[39] Microsoft Source, "Microsoft Ignite 2026: Empowering human ambition, intelligence and trust" (2026-11-17) — <https://news.microsoft.com/source/2026/11/17/microsoft-ignite-2026-empowering-human-ambition-intelligence-and-trust/>

<a id="ref-40"></a>[40] Jev Model changelog — <https://docs.typesafe.ai/changelog>
