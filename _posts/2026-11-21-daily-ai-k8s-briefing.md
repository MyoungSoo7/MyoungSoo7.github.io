---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-21"
date: 2026-11-21 08:30:02 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-21 08:30 KST · **수집 범위**: 2026-11-19 ~ 2026-11-20 (UTC/KST 혼재 시 원문 날짜 기준)
> **표기**: [사실] 1차·공식 출처로 확인 · [보도] 신뢰 언론 보도 · [벤더 주장] 벤더 자체 수치(독립 재현 미확인) · [추론] 필자 해석 · [미확인] 1차 출처 확인 실패

> **중복 안내**: 11-20 브리핑에서 다룬 vCenter CVE-2026-123890 패치 공지, NGINX2Root, Anthropic 상장 첫 거래일, Claude Code 2.1.327~329, LangGraph 1.2.23, CrewAI 1.15.43/44, MLflow 3.18.0, Kubeflow 26.10.0, 위시켓 공고 등은 반복하지 않는다. 진전이 있는 항목(vCenter 공격 귀속, Anthropic 상장 마감)만 후속으로 다룬다.

## 오늘의 핵심

1. **Anthropic IPO 마감** — 그린슈(초과배정옵션) 전량 행사로 공모 총액 약 935억 달러, 동시 사모 포함 약 1,195억 달러 [사실] [[1]](#ref-1). 상장 이틀째 종가는 출처마다 다르다($88.91 vs $88.30) [보도] [[2]](#ref-2)[[3]](#ref-3).
2. **vCenter 제로데이 귀속 확정** — Mandiant/GTIG 가 CVE-2026-123890 악용을 중국 연계 ARMORY CASTLE(구 UNC5221)로 귀속하고, BONESAW·SAWSNAKE 등 신규 악성코드 5종을 공개했다 [사실] [[4]](#ref-4).
3. **F5 BIG-IP 긴급 패치** — APM/iRules 치명 스택 오버플로 5건. 완화책 없음, 악용 보고는 아직 없음 [보도] [[5]](#ref-5).
4. **MCP 레퍼런스 서버 v2.5.0** — 취약점 8건 수정. filesystem 서버의 TOCTOU 수정 포함 [사실] [[6]](#ref-6).
5. **프리랜서** — 11-20 등록 Java/Spring 공고 4건(월 500~700만, 서울). 모두 12-04 마감 [사실] [[25]](#ref-25).

## 1. AI & ML (Claude/Opus · ML/DL · 뇌과학/BCI)

- **Anthropic IPO 마감** [사실] [[1]](#ref-1)
  - Class A 1,127,000,000주를 주당 $83에 매각했다. 그린슈는 전량 행사됐다.
  - 공모 총액은 약 935억 달러이고, 그중 Anthropic 몫은 약 916억 달러다.
  - 동시 사모로 Class N 313,253,007주(약 260억 달러)를 AMD·Broadcom·Google·Micron·Microsoft·NVIDIA·TSMC Partners 에 매각했다.
  - 합계는 약 1,195억 달러다.
- **상장 이틀째 주가** [보도]
  - Reuters 는 11-20 종가를 $88.91(-8.5%)로 보도했다 [[2]](#ref-2).
  - CNBC 는 $88.30 으로 보도했다 [[3]](#ref-3).
  - **두 수치가 일치하지 않는다.** 거래소 공식 종가는 이 글에서 확인하지 못했다 [미확인].
  - [추론] 공모가 $83 대비로는 여전히 위다. 다만 첫날 종가($97.17, 11-20 브리핑) 대비 하락폭을 "AI 거품" 신호로 읽는 것은 이틀치 데이터로는 과잉 해석이다.
- **Claude Code v2.1.330** (2026-11-20 22:32 UTC) [사실] [[7]](#ref-7)
  - Enterprise Admin Console 조직 로그인을 지원한다.
  - 내장 차트 모드 "easel" 이 추가됐다.
  - `CLAUDE_CODE_FULL_SIGN_IN_LINK=1` 환경 변수가 추가됐다.
  - 셀프호스티드 러너에 `--start-dir` 옵션과 신규 메트릭이 추가됐다.
  - 주요 수정은 다음과 같다.
    - 컴팩션 후 수 분간 멈추는 현상
    - WebFetch 멈춤
    - **다른 세션이 사용 중인 worktree 를 ExitWorktree 가 삭제하던 문제**
    - 동시 설정 저장 시 변경 유실
    - MCP 도구가 많을 때 발생하던 "JSON schema is invalid"
    - 서브에이전트가 선언한 MCP 서버의 조기 종료
  - [추론] 여러 세션이 한 머신에서 같은 리포를 다루는 운영이라면 worktree 삭제 수정과 설정 저장 수정이 체감상 가장 크다.
- **ML/DL · 뇌과학/BCI**: 11-19~20 에 1차 출처로 확인된 신규 항목은 없다.

## 2. 에이전트 프레임워크 (LangGraph · CrewAI · Devin)

- **LangGraph 1.2.24** (11-20) [사실] [[8]](#ref-8)
  - `_messages_delta_reducer` 에서 `REMOVE_ALL_MESSAGES` 를 처리한다.
  - `DeltaChannel` 에서 `None` 체크포인트를 처리한다(#9735).
  - [추론] 메시지 전체 삭제 후 재개하는 그래프에서 생기던 상태 불일치를 막는 패치다. 1.2.23 사용자라면 올릴 만하다.
- **CrewAI**: 1.15.44 이후 신규 릴리스가 없다 [사실] [[9]](#ref-9).
- **Devin**: 11-19~20 공식 발표는 확인하지 못했다.
- **Pydantic AI 2.71.0, langchain-core 1.8.4**: 릴리스 보도는 있지만 애그리게이터 출처뿐이다. 1차 릴리스 페이지를 확인하지 못해 [미확인]으로 둔다.

## 3. Kubernetes & Cloud Native (v1.36/1.37)

- **릴리스 현황** [사실] [[10]](#ref-10)
  - 최신 안정판은 v1.37.2(10-28)이다.
  - 개발판은 v1.38.0-beta.0(11-06)이다.
  - 11-19~20 에 신규 패치 릴리스는 없다.
- **kubernetes.io 블로그**: 11-16 이후 신규 글이 없다.
- **v1.38 일정**: 12월 중순 GA 와 11월 말 deprecation 안내 글이 예정돼 있다는 이야기가 있지만 제3자 블로그 출처뿐이다. 공식 릴리스 일정표에서 확인하지 못해 [미확인]으로 둔다.
- **Jaeger v2.22** (CNCF, 11-10) [사실] [[11]](#ref-11)
  - KubeCon NA 에서 실험 기능이 공개됐다.
    - 인제품 AI 어시스턴트 "Ask Jaeger"
    - 9개 도구를 갖춘 MCP 엔드포인트
    - OTel GenAI 시맨틱 컨벤션 기반 트레이스 뷰
  - 지난주 항목이지만 이전 브리핑에서 다루지 않았다. 12절 맥락으로 포함한다.

## 4. 보안

### vCenter CVE-2026-123890 — 공격 귀속과 TTP (후속)

- **공격 주체와 경로** [사실] [[4]](#ref-4)
  - Mandiant/GTIG 는 중국 연계로 의심되는 ARMORY CASTLE(구 UNC5221)이 **2026년 9월 초부터** 이 취약점을 악용했다고 밝혔다.
  - 진입 경로는 이전 BeyondTrust Remote Support 제로데이(CVE-2026-102764)였다. 거기서 EDR 이 없는 내부 Linux 어플라이언스로 이동했다.
- **취약점 원리** [사실] [[4]](#ref-4)
  - vmdir DCE/RPC 인터페이스(TCP **2012** 포트)의 SRP-6a 인증에서 예측 가능한 UUIDv1 타임스탬프 때문에 세션 키가 노출된다.
  - 그 결과 비밀번호 없이 `administrator@vsphere.local` 세션을 만들 수 있다.
- **신규 도구** [사실] [[4]](#ref-4)
  - **BONESAW** (Go): LMDB(data.mdb)를 유출하고, STS SAML 서명키를 탈취하고, SSO 관리자 계정을 만든다.
  - **SAWSNAKE**: Golden SAML 공격 도구다.
  - **BEARBONES**: 백도어다.
  - **SLIMSAVAGE / CAGEMATCH**: 웹셸이다.
  - **LAZYBONES**: 기존에 관찰된 백도어로, 이번에도 재사용됐다.
  - 이후 VAMI API 로 SSH 를 잠시 켜서 마스터 키와 PostgreSQL 자격증명을 빼낸 뒤 ESXi 까지 접근했다.
- **패치 이력과의 관계** [사실] [[4]](#ref-4)
  - BONESAW 는 CVE-2026-59309(7월 공개) 패치가 이미 적용된 서버에서 실행됐다.
  - 바이너리 빌드 타임스탬프는 그 공개보다 16일 앞선다. 단, GTIG 는 이 메타데이터가 조작될 수 있다고 단서를 달았다.
- **KEV 등재와 수정 버전** [보도] [[12]](#ref-12)
  - CISA 가 11-20 KEV 에 추가했다.
  - 수정 버전은 8.0 U3m, 9.0.2.0200, 9.1.1.0200, VCF 5.2.5 로 보도됐다.
  - 7.0 계열의 공개 수정 여부는 보도마다 다르다. 벤더 권고(VMSA)를 직접 확인할 것을 권한다.
- **실무 체크** [추론]
  - 2012/389/636 포트를 관리망 밖에서 접근할 수 없게 막는다.
  - `@vsphere.local` 계정 신규 생성 이력을 확인한다.
  - VAMI SSH 토글 로그를 확인한다.
  - `/bin/env` SUID 비트를 점검한다.

### 기타

- **F5 BIG-IP** [보도] [[5]](#ref-5)
  - APM/iRules 에서 치명 스택 오버플로 5건이 나왔다(CVE-2026-121805, -120292, -120285, -116953, -123637).
  - 정기 일정 밖의 핫픽스이고, 완화책이 없어 패치만이 대응이다. 현재까지 악용 보고는 없다.
- **CISA KEV 11-20 추가분** [보도·1차 미확인]
  - Cisco Expressway CVE-2026-76466: 하드코딩 자격증명. 클러스터 구성에 한정된다. X15.5.20 에서 수정됐다.
  - SAP NetWeaver Enterprise Portal CVE-2025-42884: JNDI 인젝션.
  - Apache Roller CVE-2026-129448: XML-RPC 역직렬화 RCE. 6.1.6 에서 수정됐다.
  - 보안 전문 매체 보도로만 확인했다. cisa.gov 카탈로그 원문은 확인하지 못했다.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

### AWS (11-20 What's New) [사실 / 수치는 벤더 주장]

- **EC2 T9g (Graviton5) GA** [[13]](#ref-13)
  - T4g 대비 가격 대비 성능이 최대 45% 좋다고 밝혔다 [벤더 주장].
  - 크기는 nano~medium 이고 Free Tier 에 포함된다.
- **S3 읽기 한도 상향** [[14]](#ref-14)
  - 프리픽스당 GET/HEAD 가 초당 5,500건에서 11,000건으로 늘었다.
  - [추론] 프리픽스 샤딩을 위해 키 설계를 복잡하게 했던 이유가 일부 줄어든다.
- **S3 Vectors** [[15]](#ref-15)
  - 필터 가능한 메타데이터 한도가 2KB 에서 벡터당 40KB 로 늘었다.
- **Lambda 런타임** [[16]](#ref-16)[[17]](#ref-17)
  - Python 3.15 런타임이 추가됐다. lazy imports, frozendict 등을 쓸 수 있다.
  - Node.js 26 런타임이 추가됐다. LTS 는 2029년 4월까지다.
- **Lambda MicroVMs** [[18]](#ref-18)
  - 서울을 포함한 7개 리전이 추가됐다.
  - 고객 관리형 키(CMK)를 지원한다.
- **기타**
  - Pricing Calculator 에 견적 API 가 추가됐다.
  - Agent Registry 가 이름 지정과 공개 탐색을 지원한다.
  - Billing Data Hub 가 프리뷰로 나왔다.

### GCP (11-20)

- **Unified Access Policies (프리뷰, 무료)** [사실] [[19]](#ref-19)
  - allow/deny 규칙을 하나의 스키마로 통합한다.
  - 정책 하나를 최대 25개 CRM 대상에 바인딩할 수 있다.
  - 에이전트를 1급 주체(`principal://agents.global...`)로 다룬다.
- **Managed Service for Apache Spark 4.0 GA** [사실] [[20]](#ref-20)
  - 구성은 Spark 4.2, Java 25, Python 3.13, Iceberg 1.12 이다.
  - Claude Code 등 IDE 와 MCP 로 연동된다.
  - "경쟁 고속 Spark 대비 가격 대비 성능 최대 3.25배"는 [벤더 주장]이며, 독립 비교는 부재하다.

### Azure (11-20)

- **Ignite 2026 Azure Compute** [벤더 주장] [[21]](#ref-21)
  - Maia 300 을 발표했다. 선도 GPU 시스템 대비 와트당 토큰 처리량이 40% 높을 것으로 "기대"한다고 밝혔다.
  - Cobalt 200 은 14개 리전에서 GA 다.
  - 중립 제3자 측정은 부재하다.

### Naver Cloud

- 11-19~20 공식 신규 발표는 확인하지 못했다.

## 6. 언어 (Python · Rust · React · Vue · Java · Kotlin · JS · TS)

- **Reactor 2026.0.0 릴리스 트레인** (11-20) [사실] [[22]](#ref-22)
  - reactor-core 3.9.0
  - reactor-netty 1.4.0
  - addons 3.7.0
  - pool 1.3.0
  - kotlin-extensions 1.3.3
  - [추론] 다음 Spring Boot/WebFlux 마이너에서 이 트레인을 채택할 가능성이 크다. Netty 기반 서비스는 reactor-netty 1.4 변경 내역을 미리 검토해 두는 것이 좋다.
- **Python 3.15 / Node.js 26**: AWS Lambda 지원으로 서버리스 채택 경로가 열렸다(5절).
- Rust·React·Vue·Kotlin·TS 는 11-19~20 에 1차 출처로 확인된 주요 릴리스가 없다.

## 7. Infra & Linux

- vCenter 공격의 측면 이동 대상은 EDR 이 없는 Linux 어플라이언스였다. 권한 상승은 gdb 로 `/bin/env` 에 SUID 를 붙이는 방식이었다 [사실] [[4]](#ref-4).
  - [추론] 벤더 어플라이언스는 "블랙박스라 손대지 않는다"는 이유로 무결성 감시에서 빠지기 쉽다. 최소한 SUID 변화 감시(`find / -perm -4000` 기준선 비교)라도 걸어 둘 만하다.
- **멀티클라우드 네트워크** [사실] [[23]](#ref-23)
  - Google Cloud 와 Azure 간 Partner Cross-Cloud Interconnect 가 양사 공동 지원으로 프리뷰에 들어갔다(11-17).
- Linux 커널 메인라인과 배포판의 11-19~20 주요 릴리스는 확인하지 못했다.

## 8. [특집] Jev API 와 판단 모델

### 오늘의 변화

- Jev changelog 는 여전히 **1.14 (10-14)** 가 최신이다. 신규 릴리스는 없다 [사실].
- 주변 동향으로, "판단(decision) 모델" 계열 모델이 Vercel AI Gateway 에 추가됐다는 소식이 있다. 다만 애그리게이터 출처뿐이어서 [미확인]으로 둔다.

### 어떻게 읽을 것인가

- [추론] 이번 주 에이전트 플랫폼 발표에는 공통점이 있다. GCP UAP 의 에이전트 주체, Azure/GCP 의 에이전트 이상 탐지, AWS Agent Registry 가 모두 **판단을 내리는 주체(에이전트)를 IAM·관측 체계 안의 1급 객체로 등록**하는 방향이다.
- 판단 모델 API 를 쓰는 쪽에서 중요한 것은 모델 성능보다 아래 두 가지가 될 가능성이 크다.
  - 판단 결과를 누가 어떤 권한으로 실행했는가
  - 그 판단의 근거 트레이스가 남는가

### 실무 체크포인트

- 판단 모델 호출 결과를 그대로 실행하지 말고, 실행 전 정책 계층(allow/deny)을 둔다.
- 판단 입력과 출력을 OTel GenAI 컨벤션(`gen_ai.*`)으로 남겨 두면 관측 벤더를 바꿀 때 이식할 수 있다(12절).
- Jev 1.14 이후 변경이 없으므로, 현재 통합을 고정 버전으로 잠가도 무방한 시점이다 [추론].

## 9. AI Safety & Alignment

- 11-19~20 에 동료심사나 1차 랩 발표로 확인된 신규 항목은 **없다**.
- 이번 달 이전 브리핑에서 빠뜨린 arXiv 항목은 다음과 같다(날짜 명시, "최신" 아님).
  - arXiv 2611.02162 "Rewarded for Not Getting Caught" (11-01) — 탐지 회피가 보상되는 학습 신호에 관한 연구 [사실·내용 요약은 초록 기준].
  - arXiv 2611.08438 기계적 해석가능성 서베이 (Barez 외, 11-09).
- 관련 운영 사례로, 에이전트 행동 이탈 탐지가 다른 클라우드 에이전트까지 확장됐다(12절) [사실] [[24]](#ref-24).

## 10. MCP

- **modelcontextprotocol/servers v2.5.0** (11-18) — 취약점 8건 수정 [사실] [[6]](#ref-6)
  - **mcp-server-git**
    - git maintenance/gc 훅 경유 실행
    - promisor lazy fetch
    - 쓰기 후 드라이버 재읽기
    - 빈 이름 필터
    - 워크트리 밖 index 경로
    - 서브모듈 설정 악용
  - **server-filesystem 2.4.0**: 디렉터리 목록의 TOCTOU 를 수정했다. Windows 는 아직 대상이 아니다.
  - **server-everything 2.3.1**: NAT64 사설 주소 가드를 추가했다.
  - 날짜형 버전으로 npm 을 쓰는 경우 `@modelcontextprotocol/server-filesystem@2.4.0` 을 명시해서 설치해야 한다.
  - [추론] git·filesystem 레퍼런스 서버를 "예제니까" 그대로 운영 에이전트에 붙인 경우가 많다. 이번 수정 목록은 **신뢰할 수 없는 리포를 열기만 해도 코드가 실행되는** 경로가 중심이다. 업데이트 우선순위가 높다.
- SDK 는 Python v2.3.0, TS v2.4.0, Java v2.2.0 으로 신규 릴리스가 없다.

## 11. MLOps · Feature Store

- MLflow 3.18.0(11-04)과 Feast v0.68.0(11-10)이 최신이다. 11-19~20 신규 릴리스는 없다 [사실].
- **GCP Spark 4.0** 의 Lakehouse 런타임 카탈로그 자동 연결(레거시 Hive Metastore 대체)은 피처 파이프라인 거버넌스와 관련이 있다 [사실] [[20]](#ref-20).
- **Google "data simulator"** (11-20): 데이터 에이전트 평가용 합성 데이터 "풍동"을 소개했다. 내부 도구 소개이며 공개 제품은 아니다 [사실] [[26]](#ref-26).

## 12. 에이전트 관측성

- **Google Agent Anomaly Detection** (11-20, Private Preview) [사실] [[24]](#ref-24)
  - AWS Lambda, Microsoft Foundry, 온프레미스 등 **다른 클라우드의 에이전트**도 트레이스와 로그만으로 이상 행동을 탐지한다.
  - 조건은 세 가지다.
    - Telemetry API 로 수집할 것
    - OTel 컨벤션을 따르고 프롬프트·응답을 로그 이벤트로 남길 것
    - 에이전트를 식별하는 리소스 속성이 있을 것
- **AWS Distro for OTel Python v0.23.0** (11-20) [사실] [[27]](#ref-27)
  - CrewAI LiteAgent 를 지원한다.
  - CrewAI/LangChain 스팬에 `gen_ai.tool.definitions` 를 기록한다.
  - `error.type` 에 에러 메시지 대신 예외 클래스를 넣는다. 메시지에 태스크 내용이나 인자가 새어 나가는 것을 막는다.
- [추론] 세 하이퍼스케일러 모두 "남의 클라우드 에이전트도 내 관측 플랫폼에서"를 내세운다. Azure 는 11-17 에 external-agent observability GA 를 발표했다. 그렇다면 공통 분모는 OTel GenAI 컨벤션이다. 계측은 벤더 SDK 가 아니라 OTel 로 해 두는 것이 이식성 면에서 안전하다.

## 13. 그린 컴퓨팅

- **Nature Sustainability** (11-16, 동료심사) [사실] [[28]](#ref-28)
  - 미국 하이퍼스케일 데이터센터 403곳을 시설 단위로 추정했다(2024.5~2025.4).
  - 중앙 시나리오 기준 전력 사용량은 약 82 TWh 로 미국 전체의 약 1.8% 다.
  - 귀속 CO₂ 는 약 25.7 Mt 이고, 공급 발전량의 약 54% 가 화석연료다.
  - 수집 범위(11-19~20) 밖이지만 이전 브리핑에서 다루지 않았다.
- **IEC 백서 "Clean green data centres"** (2026-11) [사실] [[29]](#ref-29)
  - PUE 같은 시설 효율 지표만으로는 부족하다고 보고, 전력망·물·지역 기여까지 평가하는 "Total Contribution" 접근을 제안했다.
- [추론] Azure 의 "토큰/와트" 수치처럼 벤더 효율 주장이 늘고 있다. 그러나 가속기 효율을 비교할 표준 지표는 아직 성숙하지 않았다. 따라서 벤더 수치를 탄소 감축 근거로 바로 쓰지 않는 편이 안전하다.

## 14. 한국 기업 기술블로그 (네카라쿠배당토)

| 기업 | 제목 | 날짜 | 요약 | 원문 |
| --- | --- | --- | --- | --- |
| 네이버 D2 | Devops Agent 리포트 오이데~ 평가 야호~ | 2026-11-19 | 통합검색 알람 발생 1분 내 장애 1차 진단 리포트를 쓰는 에이전트와 그 정확도 평가 (NAVER ENGINEERING DAY 10회 세션) | [D2](https://d2.naver.com/home) |
| 네이버 D2 | 온톨로지, 구축에서 활용까지. 질문이 답을 설계한다. | 2026-11-19 | 사내 온톨로지 구축·활용 경험 (ENGINEERING DAY 세션) | [D2](https://d2.naver.com/home) |
| 네이버 D2 | 부족한 건 모델이 아니라 팀 문서였다: 팀 공유 지식층 Third Brain 구축기 | 2026-11-19 | LLM 활용의 병목이 모델이 아니라 팀 문서였다는 관점의 공유 지식층 구축 | [D2](https://d2.naver.com/home) |
| 네이버 D2 | Jetpack Compose 기반 커스텀 3D 캐러셀 개발기 | 2026-11-19 | Compose 로 3D 캐러셀 UI 구현 | [D2](https://d2.naver.com/home) |
| 우아한형제들 | 세 번 그리던 화면을 한 번에: CLAYDesign이 디자인시스템으로 화면을 생성하는 방법 | 2026-11-20 | 디자인시스템 기반 화면 자동 생성 도구 CLAYDesign 소개 | [우아한기술블로그](https://techblog.woowahan.com/) |
| LY Corp | AI 시대 필수 보안: 외부 가드레일 완벽 가이드 | 2026-11-20 [미확인] | LLM 앱 외부 가드레일 설계 가이드 (날짜는 큐레이터 기준, 원문 미확인) | [LY 기술블로그](https://techblog.lycorp.co.jp/ko) |

- 카카오는 11-18 이후, 당근은 11-17 이후 신규 글이 없다(기존 글은 이전 브리핑에서 다룸).
- 토스는 11-20 SLASH 관련 글이 있다는 큐레이터 보도가 있지만 toss.tech 원문 날짜를 확인하지 못해 제외했다.
- 쿠팡과 두나무는 확인하지 못했다.
- [추론] D2 의 DevOps Agent 글은 "에이전트가 쓴 장애 리포트의 정확도를 어떻게 평가하는가"를 다룬다. SRE 가 에이전트를 도입할 때 가장 막히는 지점이어서 우선 읽을 만하다.

## 15. Java/Spring 프리랜서 공고

| 플랫폼 | 제목 | 스택 | 형태 | 금액 | 수집일 | 링크/상태 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | Spring Boot/Kafka 기반 EV 플랫폼 구축 백엔드 개발 | Java, Spring Boot, Kafka | 기간제 상주, 210일(12-07~), 서울 강남(선릉) | 중급 500만/월 · 고급 600만/월 | 2026-11-21 | [159753](https://www.wishket.com/project/159753/) · 등록 11-20, 마감 12-04, 모집 중 |
| 위시켓 | Java/Spring Boot·React/Vue 기반 B2C·B2E 웹서비스 풀스택 개발 및 운영 | Java, Spring Boot, React/Vue | 기간제 상주, 360일(12-20~, 연장 가능), 서울 용산 | 550만/월 (6~10년) | 2026-11-21 | [159756](https://www.wishket.com/project/159756/) · 등록 11-20, 마감 12-04, 모집 중 |
| 위시켓 | Java 기반 카드사 바우처 카드 프로세스 신규 개발 | Java (SI) | 기간제 상주, 360일(2027-01-04~), 서울 여의도 | 700만/월 (고급 8~10년) | 2026-11-21 | [159767](https://www.wishket.com/project/159767/) · 등록 11-20, 마감 12-04, 모집 중 |
| 위시켓 | Java 기반 카드사 선불카드 프로세스 구축 계정계 개발 | Java (SI 계정계) | 기간제 상주, 150일(2027-01-04~), 서울 여의도 | 700만/월 (고급 8~10년) | 2026-11-21 | [159768](https://www.wishket.com/project/159768/) · 등록 11-20, 마감 12-04, 모집 중 |
| 위시켓 | Java/Spring Boot·React/Vue SI/SM 풀스택 | Java, Spring Boot, React/Vue | 기간제 상주 | 400만/월 | 2026-11-21 | [159636](https://www.wishket.com/project/159636/) · 등록 11-13, 마감 11-27, 모집 상태 미확인 |

- 상세 업무 내용과 요건은 로그인이 필요한 영역이라 공개 필드만 적었다. 로그인 우회는 하지 않았다.
- 프리모아와 이랜서는 이번 회차에 확인하지 못했다.

## 사실 · 추론 · 미확인 정리

- **사실**
  - Anthropic IPO 마감 수치
  - vCenter 공격 귀속과 TTP (GTIG 원문)
  - Claude Code 2.1.330
  - LangGraph 1.2.24
  - MCP servers v2.5.0
  - AWS·GCP 11-20 발표 내용
  - Reactor 2026.0.0
  - ADOT Python 0.23.0
  - Nature Sustainability 수치
  - D2·우아한형제들 글
  - 위시켓 공고 공개 필드
- **보도**
  - Anthropic 11-20 종가 (Reuters $88.91 vs CNBC $88.30 불일치)
  - F5 BIG-IP 패치
  - CISA KEV 11-20 추가분
- **벤더 주장**: T9g 45%, Spark Lightning 3.25배, Maia 300 40%. 모두 중립 제3자 검증은 부재하다.
- **추론**: 각 절의 [추론] 표시 문장
- **미확인**
  - v1.38 일정
  - Pydantic AI 2.71.0, langchain-core 1.8.4
  - 판단 모델 관련 게이트웨이 소식
  - LY 글 날짜
  - 토스 SLASH 글
  - 쿠팡·두나무, Naver Cloud, Devin, Linux 커널 동향

## References

<a id="ref-1"></a>[1] Anthropic, "Anthropic announces closing of initial public offering" (2026-11-20). <https://www.anthropic.com/news/ipo-close>

<a id="ref-2"></a>[2] Reuters via Investing.com, "Anthropic's post-debut stumble delivers reality check for AI trade" (2026-11-20). <https://www.investing.com/news/economy-news/anthropics-postdebut-stumble-delivers-reality-check-for-ai-trade-5041125>

<a id="ref-3"></a>[3] CNBC, "Anthropic defies odds holding IPO despite massively disruptive market" (2026-11-20). <https://www.cnbc.com/2026/11/20/anthropic-defies-odds-holding-ipo-despite-massively-disruptive-market.html>

<a id="ref-4"></a>[4] Google Threat Intelligence Group / Mandiant, "ARMORY CASTLE Exploits vSphere" (2026-11-19). <https://cloud.google.com/blog/topics/threat-intelligence/armory-castle-exploits-vsphere>

<a id="ref-5"></a>[5] BleepingComputer, "F5 releases emergency patches for critical BIG-IP RCE flaws" (2026-11). <https://www.bleepingcomputer.com/news/security/f5-releases-emergency-patches-for-critical-big-ip-rce-flaws/>

<a id="ref-6"></a>[6] modelcontextprotocol/servers, Release v2.5.0 (2026-11-18). <https://github.com/modelcontextprotocol/servers/releases/tag/v2.5.0>

<a id="ref-7"></a>[7] Anthropic, Claude Code CHANGELOG (v2.1.330). <https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md>

<a id="ref-8"></a>[8] LangChain, LangGraph releases (1.2.24). <https://github.com/langchain-ai/langgraph/releases>

<a id="ref-9"></a>[9] CrewAI releases. <https://github.com/crewAIInc/crewAI/releases>

<a id="ref-10"></a>[10] Kubernetes releases. <https://github.com/kubernetes/kubernetes/releases>

<a id="ref-11"></a>[11] CNCF, "Jaeger Previews AI-Assisted Troubleshooting and GenAI Observability for OpenTelemetry Traces at KubeCon" (2026-11-10). <https://www.cncf.io/blog/2026/11/10/jaeger-previews-ai-assisted-troubleshooting-and-genai-observability-for-opentelemetry-traces-at-kubecon/>

<a id="ref-12"></a>[12] BleepingComputer, "VMware patches vCenter zero-day exploited in attacks since September" (2026-11). <https://www.bleepingcomputer.com/news/security/vmware-patches-vcenter-zero-day-exploited-in-attacks-since-september/> · The Hacker News (2026-11). <https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html>

<a id="ref-13"></a>[13] AWS, "Amazon EC2 T9g instances generally available" (2026-11-20). <https://aws.amazon.com/about-aws/whats-new/2026/11/ec2-t9g-instances-ga/>

<a id="ref-14"></a>[14] AWS, "Amazon S3 increases read request rate" (2026-11-20). <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-s3-increases-read-request-rate/>

<a id="ref-15"></a>[15] AWS, "Amazon S3 Vectors raises filterable metadata to 40KB per vector" (2026-11-20). <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-s3-vectors-raises-filterable-metadata-40kb-per-vector/>

<a id="ref-16"></a>[16] AWS, "AWS Lambda supports Python 3.15" (2026-11-20). <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-python-315/>

<a id="ref-17"></a>[17] AWS, "AWS Lambda supports Node.js 26" (2026-11-20). <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-nodejs-26/>

<a id="ref-18"></a>[18] AWS, "AWS Lambda MicroVMs in 7 additional regions" (2026-11-20). <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-microvms-7-regions/> · CMK: <https://aws.amazon.com/about-aws/whats-new/2026/11/lambda-microvms-customer-managed-keys/>

<a id="ref-19"></a>[19] Google Cloud, "How to simplify cloud access with Unified Access Policies" (2026-11-20). <https://cloud.google.com/blog/products/identity-security/how-to-simplify-cloud-access-with-unified-access-policies>

<a id="ref-20"></a>[20] Google Cloud, "What's new in Managed Service for Apache Spark 4.0" (2026-11-20). <https://cloud.google.com/blog/products/data-analytics/whats-new-in-managed-service-for-apache-spark-4-0>

<a id="ref-21"></a>[21] Microsoft, "Ignite 2026: The next era of enterprise AI starts with the infrastructure beneath it" (2026-11-20). <https://techcommunity.microsoft.com/blog/azurecompute/ignite-2026-the-next-era-of-enterprise-ai-starts-with-the-infrastructure-beneath/4574943>

<a id="ref-22"></a>[22] Reactor, Release 2026.0.0 (2026-11-20). <https://github.com/reactor/reactor/releases/tag/2026.0.0>

<a id="ref-23"></a>[23] Google Cloud, "Cross-Cloud Interconnect for Microsoft Azure" (2026-11-17). <https://cloud.google.com/blog/products/networking/cross-cloud-interconnect-for-microsoft-azure>

<a id="ref-24"></a>[24] Google Developers Blog, "Agent Anomaly Detection: Safeguarding agents across other clouds" (2026-11-20). <https://developers.googleblog.com/agent-anomaly-detection-safeguarding-agents-across-other-clouds/>

<a id="ref-25"></a>[25] 위시켓 프로젝트 목록 (공개 필드, 2026-11-21 수집). <https://www.wishket.com/project/>

<a id="ref-26"></a>[26] Google Cloud, "A data simulator to test agents" (2026-11-20). <https://cloud.google.com/blog/products/data-analytics/a-data-simulator-to-test-agents>

<a id="ref-27"></a>[27] aws-observability/aws-otel-python-instrumentation, Release v0.23.0 (2026-11-20). <https://github.com/aws-observability/aws-otel-python-instrumentation/releases>

<a id="ref-28"></a>[28] Guidi et al., "Assessing the carbon emissions and energy consumption of US hyperscale data centres", *Nature Sustainability* (2026-11-16). <https://www.nature.com/articles/s41893-026-01985-7>

<a id="ref-29"></a>[29] IEC, "Clean green data centres" white paper (2026-11). <https://www.iec.ch/system/files/2026-11/iec_spp_cgdc_en_lr.pdf>
