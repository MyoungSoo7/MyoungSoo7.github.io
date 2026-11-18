---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-19"
date: 2026-11-19 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-19 08:30 KST · **수집 범위**: 주로 2026-11-17 ~ 11-18 공개분(일부 11-16 포함, 날짜 명시)
> **표기**: **[사실]** 1차·공식 출처 확인 / **[보도]** 신뢰 언론 보도(1차 미확인) / **[벤더 주장]** 벤더 자체 수치·벤치마크 / **[추론]** 필자 해석 / **[미확인]** 검증 못 함
> **중복 안내**: 11-18 브리핑에 실린 항목(Claude Linked billing, kube-proxy IPVS 제거 글, Ignite 1일차 발표, Langfuse v4.82.0, kernel 7.3.5, 토스·당근 글, 위시켓 159690/159649 등)은 새 진전이 없으면 다시 싣지 않았습니다.

## 오늘의 핵심

1. **[사실] Java 서버를 운영한다면 오늘 할 일 1순위는 "Java4Shell"(CVE-2026-114938)입니다.** x86-64 HotSpot 의 Base64 디코더 intrinsic 에서 메모리가 손상되는 결함으로, 인증 없이 원격 코드 실행(RCE)이 가능합니다. CISA 는 "즉시 패치"를 권고했고, OpenJDK·CERT-EU·Microsoft 가 수정판과 완화책을 공개했습니다. [[1]](#ref-1) [[2]](#ref-2) [[3]](#ref-3)
2. **[사실] CISA KEV 에 4건이 추가됐고, 그중 하나가 LLM 게이트웨이 LiteLLM(CVE-2026-40217)입니다.** 이제 AI 인프라 구성요소도 "실제 악용 중" 목록에 오르고 있습니다. [[6]](#ref-6) [[7]](#ref-7)
3. **[보도] Anthropic IPO 공모가가 주당 $83 으로 정해졌습니다(희망 범위 $70–78 상회).** 11-19(목)부터 나스닥 "ANT" 로 거래된다고 보도됐습니다. Anthropic 의 1차 발표는 확인하지 못했습니다. [[9]](#ref-9) [[10]](#ref-10)
4. **[사실] AWS 가 11-18 하루에 서버리스 에이전트 메모리(OpenSearch Memory GA), Lambda GPU Managed Instances, EKS Hybrid Nodes 과금 상한 등을 내놨습니다.** [[16]](#ref-16) [[17]](#ref-17) [[19]](#ref-19)
5. **[사실] Ignite 2일차: Foundry Agent Service 가 A2A 도구·음성 에이전트·computer use 를 GA 로 올리고, Toolboxes 를 "관리형 MCP 엔드포인트"로 내놨습니다.** LangGraph·CrewAI 트레이스를 받는 Insights 도 GA 입니다. [[23]](#ref-23)

---

## 1. AI & ML

- **[보도] Anthropic IPO 공모가 확정.** 공모가는 주당 $83, 거래는 11-19 나스닥 "ANT" 로 시작합니다. CNBC 는 소식통을 인용해 9억 7,960만 주, 조달액 $81.3B 라고 보도했습니다. Axios 도 같은 내용을 전했습니다. Anthropic 의 1차 보도자료나 SEC 최종 공모 서류는 이 글에서 직접 확인하지 못했으므로 수치는 **보도 기준**입니다. [[9]](#ref-9) [[10]](#ref-10)
- **[사실] Claude API 텍스트 워터마크 (11-16 릴리스 노트).** Opus 4.6/4.5, Sonnet 4.5, Haiku 4.5 출력에 텍스트 워터마크가 적용됩니다. 기본값이 아닌 temperature·top_p·top_k 를 쓰면 워터마크가 빠질 수 있다고 명시돼 있습니다. 출력 출처 검증 파이프라인을 만드는 팀은 샘플링 파라미터에 따라 결과가 달라질 수 있다는 점을 알아둬야 합니다. [[11]](#ref-11)
- **[사실]/[벤더 주장] Google "Gemini 4 Neon" 공개 (11-18).** 가격은 입력 $3/M, 출력 $15/M, 캐시 입력 $0.15/M 토큰이고 컨텍스트는 1M 입니다. 가격과 사양은 사실입니다. 블로그가 인용한 외부 리더보드 순위는 **벤더가 고른 수치**이며, 중립적인 헤드투헤드 비교는 아직 **부재**합니다. [[12]](#ref-12)
- **[벤더 주장] Flower 1.44 (11-18).** 연합학습 프레임워크입니다. 미리 띄워 둔(prewarmed) 워커로 넘기는 시간이 480 ms → 101 ms 로 줄었다고 하는데, 벤더 자체 측정이고 재현 조건은 공개 글에 한정돼 있습니다. [[13]](#ref-13)

## 2. 에이전트 프레임워크

- **[사실] CrewAI 1.15.42 (2026-11-18 UTC).** 바뀐 점은 다음과 같습니다. [[14]](#ref-14)
  - ChromaDB 가 선택 extra 로 빠졌습니다.
  - Knowledge 기본 저장소가 로컬 Qdrant 로 바뀌었습니다.
  - 단독 에이전트도 도구를 골라 쓸 수 있게 됐습니다.
  - 버그가 다수 고쳐졌습니다.
  - 보안 대응으로 soupsieve 최소 버전이 4.0 으로 올라갔습니다(CVE-2026-126190).
  - **업그레이드 시 주의:** ChromaDB 를 암묵적으로 쓰던 Knowledge 구성은 extra 를 따로 설치하거나 Qdrant 로 옮겨야 합니다.
- **[사실] LangGraph** 는 1.2.22(11-14)에서 변화가 없습니다. **Devin** 도 11-17 이후 새 릴리스 노트가 없습니다. [[15]](#ref-15)
- **[사실] Foundry Agent Service 에서 LangGraph·LangChain·CrewAI 트레이스를 수집하는 Insights 가 GA 됐습니다.** 프레임워크 중립 관측이 클라우드 관리형으로 들어오는 흐름입니다(12장 참고). [[23]](#ref-23)

## 3. Kubernetes & Cloud Native

- **[사실] Kubernetes 공식 블로그**에는 11-16 IPVS 관련 글 이후 새 글이 없습니다.
- **[사실] GKE IPv6 단일 스택 클러스터 프리뷰 (11-18).** [[24]](#ref-24)
  - 대상은 TPU v6e 와 Axion 을 포함한 CPU 노드 풀입니다.
  - 노드마다 /112 Pod 대역이 할당되고, IPv4 목적지는 DNS64/NAT64 로 접근합니다.
  - GKE 1.37.1-gke.3020000 이상이 필요합니다.
  - **[추론]** 대규모 AI 클러스터에서 IPv4 주소가 고갈되는 문제를 겨냥한 기능입니다. IPv4 전용 외부 의존성(레지스트리·라이선스 서버 등)이 NAT64 를 거쳐 제대로 동작하는지 먼저 검증해야 합니다.
- **[사실] EKS Hybrid Nodes 과금 변경.** 노드당 과금 vCPU 에 32 상한이 생겼습니다. 기존 노드는 **삭제 후 다시 붙여야** 새 단가가 적용됩니다. [[17]](#ref-17)

## 4. 보안

### Java4Shell — CVE-2026-114938 (Java/Spring 운영자 필독)

- **[사실] 결함 내용.** x86-64 HotSpot 의 Base64 디코딩 intrinsic 에서 메모리 손상이 일어납니다. 인증 없는 원격 코드 실행이 가능합니다. [[1]](#ref-1) [[2]](#ref-2)
  - OpenJDK 분류: hotspot/compiler, CVSS 3.1 기준 8.1.
  - 같은 권고문에 CVE-2026-114939 ~ 114947 9건이 함께 실렸습니다.
- **[사실] 영향 조건 (CERT-EU).** 아래 조건이 모두 맞아야 영향을 받습니다. [[3]](#ref-3)
  - CPU 가 avx512f/bw/vbmi 와 bmi2 를 지원해야 합니다(Intel Ice Lake 이후, AMD Zen 4 이후). **ARM64 는 영향이 없습니다.**
  - 해당 intrinsic 은 기본으로 켜져 있습니다.
  - 공격자가 보낸 Base64 가 디코더에 도달해야 합니다. Basic 인증 헤더, JWT, SAML, 쿠키 등 흔한 경로가 해당됩니다.
- **[사실] 수정 버전.** [[2]](#ref-2) [[3]](#ref-3) [[4]](#ref-4)
  - OpenJDK: 17.0.21.1 / 21.0.13.1 / 25.0.5.1 / 27.0.1.1.
  - Microsoft Build of OpenJDK: 25.0.5.1, 21.0.13.1, 17.0.21.1, 11.0.33.1 배포.
  - Temurin·Corretto·Zulu·Liberica·SapMachine·Red Hat 등 다운스트림 빌드는 각자 일정에 따라 배포합니다. **자기 배포판의 공지를 직접 확인하세요.**
- **[사실] 패치 전 완화책 (CERT-EU).** 둘 다 JVM 재시작이 필요합니다. [[3]](#ref-3)
  - `-XX:+UnlockDiagnosticVMOptions -XX:-UseBASE64Intrinsics` 로 intrinsic 을 끕니다.
  - 또는 `-XX:UseAVX=2` 로 낮춥니다(성능 저하 있음).
  - 적용 여부는 `java -XX:+PrintFlagsFinal -version | grep UseBASE64Intrinsics` 로 확인합니다.
- **[사실] CISA 권고 순서.** [[1]](#ref-1)
  1. 번들 런타임과 컨테이너 이미지까지 포함해 JDK 재고를 파악합니다.
  2. 인터넷에 노출된 시스템부터 패치합니다.
  3. 보완 통제로 Base64 입력 크기를 제한합니다.
- **[보도] 발견자 쪽 주장 (BleepingComputer).** [[5]](#ref-5)
  - 발견자(Calif)는 CVSS 4.0 기준 9.2 로 평가했습니다.
  - Keycloak, Jira, Confluence, Artifactory, Jenkins, PingFederate 에서 인증 없는 RCE 를 시연했고, 예제 Spring Boot·Struts 앱 데모도 공개했다고 합니다.
  - 다만 공개된 PoC 는 메모리 손상까지만 보여 주며, "범용 익스플로잇"은 없다고 했습니다.
- **[사실] Spring 팀 공지.** Spring 팀도 이번 주 "This Week in Spring" 머리말을 "UPDATE YOUR JVMs!" 로 달았습니다. [[8]](#ref-8)
- **[보도] Oracle 11월 CSPU (11-17).** Oracle 은 2026-05 부터 패치를 매월(CSPU) 냅니다. Tenable 은 이번 달 규모를 640 CVE / 655 패치로 집계했습니다. 상세 위험 매트릭스는 Oracle 공식 페이지에 있습니다. [[25]](#ref-25)

### CISA KEV 4건 추가 (11-18)

- **[사실] 추가된 4건.** CISA 알림은 BOD 26-04 를 근거로 듭니다. [[6]](#ref-6)
  - CVE-2024-10441 Synology DSM
  - **CVE-2026-40217 BerriAI LiteLLM**
  - CVE-2026-90436 Apache Axis(unsafe reflection)
  - CVE-2026-90817 REDCap(code injection)
- **[사실] LiteLLM CVE-2026-40217 상세 (GHSA).** [[7]](#ref-7)
  - `POST /guardrails/test_custom_code` 에서 샌드박스를 탈출할 수 있습니다.
  - 기본 Docker 이미지에서는 프록시가 root 로 돕니다.
  - **공격하려면 proxy-admin 자격증명이 필요합니다.**
  - 영향 범위는 1.81.8 이상 1.83.10 미만입니다.
- **[사실]/[미확인] 수정 버전 표기가 엇갈립니다.** 권고 본문은 "1.83.11 에서 수정"이라고 하는데, 패치 릴리스 태그는 `v1.83.10-stable` 입니다. 어느 쪽이 맞는지 확인하지 못했습니다. 최신 계열(v1.110.0, 11-18)로 올리는 것이 가장 안전합니다. 당장 올릴 수 없다면 해당 엔드포인트를 차단하는 것이 권고된 우회책입니다.
- **[추론] 무엇을 점검할까.** LLM 게이트웨이는 모델 API 키를 한곳에 모으는 지점입니다. 관리자 키가 유출되면 곧바로 호스트 장악으로 이어질 수 있는 구조였다는 점에서, 관리 엔드포인트를 외부에 노출했는지 점검해야 합니다.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

**AWS (11-18, What's New)**

- **[사실] Amazon OpenSearch Memory GA.** 에이전트용 서버리스 메모리입니다. 도쿄를 포함한 5개 리전에서 시작합니다. [[16]](#ref-16)
- **[사실] Lambda Customer-Managed Runtimes GA.** 커스텀 런타임 이름이 "bring your own language" 로 바뀌었습니다. [[18]](#ref-18)
- **[사실] Lambda GPU Managed Instances.** G 계열 인스턴스를 씁니다. 과금은 EC2 가격에 관리 수수료 9.75% 를 더하고, 요청 100만 건당 $0.20 이 붙습니다. [[19]](#ref-19)
- **[사실] 그 밖의 발표.** [[20]](#ref-20) [[21]](#ref-21) [[22]](#ref-22)
  - SageMaker 리전 간 추론 라우팅(추가 요금 없음).
  - CloudFront 오리진 mTLS 가 WebSocket·gRPC 를 지원합니다.
  - Cognito 시점 복구: Essentials 는 1일, Plus 는 14일.
  - RDS 빠른 스토리지 볼륨 초기화: 최대 4 TiB/시간.
  - S3 복제 제외 규칙과 다중 리전 키 해석.
- **[사실] EKS Hybrid Nodes 과금 변경**은 3장을 참고하세요.

**Azure (Ignite 2일차)**

- **[사실] Foundry Agent Service 발표.** [[23]](#ref-23)
  - Microsoft Copilot harness (프리뷰)
  - 음성 에이전트 GA, A2A 도구 GA, computer use·브라우저 자동화 GA
  - Toolboxes: 관리형 MCP 엔드포인트
  - 호스티드 에이전트: 네트워크 egress 통제 GA, 메모리 스냅샷 프리뷰
  - 고객 소유 AKS 배포는 12월 초 퍼블릭 프리뷰가 목표입니다.
- **[사실] Azure Catalyst (11-17).** 앱·데이터 현대화를 에이전트가 주도하는 통합 경험입니다. [[26]](#ref-26)

**GCP (11-18)**

- **[사실]** 3장의 IPv6 단일 스택 GKE 외에 다음 글이 올라왔습니다.
  - OKF v0.3 [[27]](#ref-27)
  - Envoy 기반 "agentic stack": 모델·토큰·MCP 라우팅 [[28]](#ref-28)
  - 에이전트형 커널 코드 리뷰 Sashiko 회고 [[29]](#ref-29) — 9장에서 다룹니다.

**Naver Cloud**

- **[사실] 11-18 공지 3건** [[30]](#ref-30)
  - Simple and Easy Notification Service API 표준화
  - 콘솔 문자 발송 기능 중지 (11-24 시행)
  - Ncloud SSO 토큰 JWT 서명키 정기 교체 (12-17 시행)
- **[추론]** SSO JWT 를 직접 검증하는 애플리케이션은 서명키를 고정(pinning)했는지, 아니면 JWKS 를 다시 조회하는지 확인해야 합니다. 그 밖에 11-24 정기 점검 예정이 공지돼 있습니다.

## 6. 언어 · 런타임

- **[사실] Java.** 4장의 Java4Shell 이 사실상 이번 주 Java 생태계의 최우선 이슈입니다. Spring 쪽은 Spring for Apache Pulsar 의 새 거처 안내 외에 새 GA 가 없습니다. Spring Boot 4.2.0-RC2(11-06)와 Spring AI 2.1.0-RC2(11-09)가 그대로입니다. [[8]](#ref-8)
- **[사실] Rust.** 11-16 공식 블로그에 "nightly 에서 병렬 프런트엔드 활성화" 글이 올라왔습니다. 최신 안정판은 Rust 1.100.0(11-12)입니다. [[31]](#ref-31)
- **[사실] Kotlin.** Kotlin Toolchain 0.14 가 나왔습니다(TestFlight 를 통한 iOS 배포, 에이전트 개발 지원). 2.5.0-Beta2 가 진행 중입니다. 정확한 게시일은 블로그 목록에서 확인하지 못했으므로 **날짜는 미확인**입니다. [[32]](#ref-32)
- Python·React·Vue·TS 는 이 기간에 1차 출처로 확인된 새 정식 릴리스가 없습니다.

## 7. 인프라 & Linux

- **[사실] kernel.org 현황.** [[33]](#ref-33)
  - mainline: 7.4-rc3 (11-15)
  - longterm: 6.18.64 · 6.12.118 (11-17)
  - stable 7.3.5 는 지난 브리핑에서 다뤘습니다.
- **[사실] Naver Cloud** 는 Windows Server 2025 이미지를 출시하고(11-24, KR), NAVIX 9.6 이미지 판매를 종료할 예정입니다(2027-01-21). [[30]](#ref-30)

## 8. [특집] Jev API 와 판단 모델

### 오늘의 변화

- **[사실] Jev 는 새 릴리스가 없습니다.** 공식 changelog 기준 최신은 여전히 1.14(10-14)입니다. [[34]](#ref-34)

### 어떻게 읽을 것인가

- **[추론] 판단 모델 주변 환경이 움직였습니다.** 이번 주에 바뀐 것은 Jev 자체가 아니라 판단(라우팅·결정) 모델을 둘러싼 환경입니다.
  - Gemini 4 Neon 이 중가 구간($3/$15)에 새 선택지로 들어왔습니다.
  - Foundry 는 에이전트 트레이스를 관리형으로 수집합니다.
  - 그 결과 "어떤 요청을 어느 모델로 보낼지" 판단할 근거 데이터를 모으기가 쉬워졌습니다.
- **[미확인] 성능 비교 근거는 부족합니다.** Jev 판단 모델과 이들 모델을 같은 조건에서 비교한 중립적 헤드투헤드는 **부재**합니다. 벤더 블로그의 순위로 대체하지 마세요.

### 실무 체크포인트

1. Jev 판단 결과를 로그로 남긴다면, 그 로그가 OpenTelemetry 트레이스와 같은 span 에 묶이는지 확인하세요. 그래야 Foundry Insights 같은 관리형 관측 도구로 넘길 때 판단 근거가 유실되지 않습니다.
2. 판단 단계를 LLM 게이트웨이(예: LiteLLM) 뒤에 둔다면, 4장의 CVE-2026-40217 영향 버전인지 먼저 점검하세요.
3. 모델 교체를 평가할 때는 자기 트래픽 샘플로 오프라인 재현 평가를 하세요. 벤더 수치는 참고만 합니다.

## 9. AI 안전 · 정렬

- **[사실] OpenAI 「Managing frontier AI risk」 (11-18).** 심층 방어 구조를 설명한 글입니다. [[35]](#ref-35)
  - 학습 중에는 실시간 인터넷 접근을 막습니다.
  - "Control Room" 이 모델 출력을 35초 안에 멈출 수 있습니다.
  - DNS 설정 오류가 악용된 뒤 9-20 ~ 10-01 동안 작업을 중단했던 사례를 공개했습니다.
  - **[추론]** 사고 경위를 공개한 점은 드물고 의미가 있습니다. 다만 모두 자체 서술이고 제3자 감사 결과는 없습니다.
- **[사실, 프리프린트] 「CoT controllability can reduce CoT monitorability」 (arXiv 2611.21799, 11-16 게시).** 모델이 자신의 사고 사슬(CoT)을 통제할 수 있게 되면 CoT 모니터링의 탐지력이 떨어질 수 있다고 보고합니다. 저자 일부는 OpenAI 재직 중 수행한 연구라고 밝혔습니다. 동료심사 전 논문입니다. [[36]](#ref-36)
- **[사실, 프리프린트] Redwood Research 등 「Auditors Struggle to Catch Sabotage…」 (arXiv 2611.21832, 11-16 게시).** AI 안전 연구 작업 기록 전체(end-to-end transcript)에서 사보타주를 찾아내는 감사 과제입니다. 인간·모델 감사자의 탐지 성능이 낮았다고 보고합니다. [[37]](#ref-37)
- **[사실] Google Sashiko 회고.** 에이전트형 커널 코드 리뷰 시스템입니다. 60일 내 수정 필요 비율이 3.4% → 2.2% 로 줄었다고 하는데, 저자들 스스로 "이 변화를 Sashiko 하나의 공으로 돌리지 말라"고 적었습니다. 인과 해석에 주의하세요. [[29]](#ref-29)

## 10. MCP 생태계

- **[사실] MCP 사양.** 새 릴리스는 없습니다. 최신 안정 사양은 2026-07-28 판입니다. [[38]](#ref-38)
- **[사실] 생태계 움직임 (11-18).** MCP 가 "서버를 직접 띄우는 것"에서 "클라우드가 관리·라우팅하는 엔드포인트"로 옮겨 가고 있습니다. [[23]](#ref-23) [[28]](#ref-28)
  - Azure Foundry Toolboxes: 관리형 MCP 엔드포인트
  - Google Cloud Envoy agentic stack: MCP 라우팅
- **[추론] 운영 관점.** 인증·egress 통제를 게이트웨이 계층에서 일괄 적용하기 쉬워집니다. 대신 게이트웨이 자체가 고가치 표적이 됩니다(4장 LiteLLM 사례 참조).

## 11. MLOps · 피처 스토어

- **[사실] 서빙·메모리.**
  - SageMaker 리전 간 추론 라우팅: 용량이 부족할 때 다른 리전으로 넘깁니다. 추가 요금은 없습니다. [[20]](#ref-20)
  - OpenSearch Memory GA: 에이전트 장기 메모리 계층입니다. [[16]](#ref-16)
- **[사실] OKF v0.3 (Google Cloud, 11-18).** 데이터 분석 영역의 공개 포맷 업데이트입니다. [[27]](#ref-27)
- **[벤더 주장] Flower 1.44.** 1장의 워커 전환 시간 단축 수치는 벤더 측정입니다. [[13]](#ref-13)

## 12. 에이전트 관측성

- **[사실] Foundry Insights GA.** LangGraph·LangChain·CrewAI 트레이스를 수집합니다. 트레이스 주석(annotation)은 프리뷰입니다. [[23]](#ref-23)
- **[추론] 과제는 "어떤 프레임워크든 OTel 로 한곳에"입니다.** 다만 관리형 수집기에 프롬프트·도구 입력이 그대로 남는다는 점을 기억해야 합니다. 그러려면 다음 두 가지를 먼저 정해야 합니다.
  - 마스킹 정책(개인정보·토큰)
  - 보존 기간
- 2장의 CrewAI 1.15.42 저장소 변경(ChromaDB → Qdrant 기본)도 트레이스에 찍히는 retriever span 이름이나 속성을 바꿀 수 있습니다. 대시보드 쿼리를 점검하세요. **[추론]**

## 13. 그린 컴퓨팅

- **[사실, 동료심사] Harvard T.H. Chan 연구진, Nature Sustainability (11-16 보도자료).** [[39]](#ref-39)
  - 미국 하이퍼스케일 데이터센터 403곳의 전력 소비를 68–99 TWh 로 추정했습니다(미국 전력의 약 1.8%).
  - 배출량은 25.7 Mt CO2, 전력의 54% 가 화석연료에서 나온다고 봤습니다.
  - DOI: 10.1038/s41893-026-01985-7
- **[사실] Nature 사설 (11-18).** 데이터센터 에너지·배출 데이터의 투명성을 요구했습니다. [[40]](#ref-40)
- **[보도] COP31 자발적 서약.** 데이터센터 청정에너지에 관한 자발적 서약이 논의되고 있다고 보도됐습니다. 서약 원문은 확인하지 못했습니다. **[미확인]**

## 14. 국내 기술 블로그

11-18 자로 우선 기업(Naver D2·Kakao·LINE/LY·Coupang·우아한형제들·당근·토스·두나무)의 **새 엔지니어링 글은 확인되지 않았습니다.** 지난 브리핑과 겹치지 않는 항목만 남깁니다.

| 기업 | 제목 | 날짜 | 요약 | 원문 |
| --- | --- | --- | --- | --- |
| 토스 | 앱인토스 11월 3주 업데이트 | 2026-11-18 | **[사실]** 엔지니어링 글이 아니라 제품 공지입니다. SDK 2.x 지원 종료, RN 미니앱은 2027-02-26 까지 WebView 로 이전해야 합니다. 해당 플랫폼 개발사는 일정 확인이 필요합니다. | [[41]](#ref-41) |
| LY Corp | Flava MCP Hub · SRE Observer 관련 글 | 미확인 | **[미확인]** 블로그 목록에서 게시 날짜를 확인하지 못해 최신 여부를 판단할 수 없습니다. 사내 MCP 허브, SRE 관측 사례입니다. | [[42]](#ref-42) |

## 15. Java/Spring 프리랜서 공고

공개 페이지에서 확인한 내용만 적었습니다(로그인이 필요한 정보는 제외). 수집일은 모두 2026-11-19 입니다. 프리모아와 이랜서는 이번 회차에 검증 가능한 공개 공고를 확보하지 못했습니다.

| 플랫폼 | 제목 | 스택 | 계약 형태 | 금액 | 수집일 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | JSP/Java 기반 병원 전자차트 VAN사(KCP) 결제 연동 개발 (2주) | Java, JSP | 기간제 · 14일 · 즉시 시작 · 경기 성남(상주 여부는 공개 범위에서 미확인) · 중급 4–7년 | 월 300만 원 | 2026-11-19 | [159697](https://project.wishket.com/project/159697/) — 등록 11-18, 마감 12-02 (모집 중) |
| 위시켓 | Java/전자정부 프레임워크·WebSquare 기반 금융권 구금고 전산시스템 구축 | Java, eGovFrame, WebSquare | 기간제 · 120일 · 즉시 시작 · 인천 · 중급 4–7년 | 월 550만 원 | 2026-11-19 | [159703](https://project.wishket.com/project/159703/) — 등록 11-18, 마감 12-02 (모집 중) |
| 위시켓 | Java/Spring 기반 금융권 모바일 웹서비스 운영·개선 PL | Java, JavaScript, Spring, SQL, Git | 기간제 · 360일 · 2026-12-17 시작 · 서울 중구 · 기술 리드 9–15년 · **수주 조건부** | 월 750만 원 | 2026-11-19 | [159714](https://project.wishket.com/project/159714/) — 등록 11-18, 마감 12-02 (모집 중) |

- 같은 제목의 159709 는 11-18 에 마감돼 제외했습니다.
- "모집 중"은 수집 시점 공개 페이지 기준입니다. 지원 전에 다시 확인하세요.

---

## 사실 · 추론 · 미확인 정리

- **사실 (1차·공식 확인)**
  - Java4Shell 영향 조건·수정 버전·완화 플래그 (CISA/OpenJDK/CERT-EU/Microsoft)
  - KEV 4건 추가와 LiteLLM 영향 범위
  - AWS 11-18 발표, Foundry Agent Service 발표, GKE IPv6 프리뷰
  - CrewAI 1.15.42, Naver Cloud 공지, kernel.org 버전
  - Harvard/Nature 데이터센터 추정치
- **보도**
  - Anthropic IPO 공모가·주식 수·조달액 (CNBC/Axios)
  - Java4Shell 발견자의 CVSS 4.0 점수와 제품별 시연 (BleepingComputer)
  - Oracle CSPU 규모 (Tenable)
  - COP31 서약
- **벤더 주장**: Gemini 4 Neon 순위, Flower 1.44 지연 수치
- **추론**: IPv6 전환 시 점검 사항, LLM 게이트웨이 위험, Jev 판단 모델 맥락, 관측 데이터 마스킹 필요성
- **미확인**
  - LiteLLM 수정 버전 표기 불일치(1.83.11 vs v1.83.10-stable)
  - Kotlin Toolchain 0.14 게시일, LY Corp 글 게시일
  - COP31 서약 원문
  - Jev 와 타 모델의 중립 헤드투헤드 비교(부재)

## References

<a id="ref-1"></a>[1] CISA, "Critical Java Vulnerability Requires Immediate Patching", 2026-11-17. <https://www.cisa.gov/news-events/alerts/2026/11/17/critical-java-vulnerability-requires-immediate-patching>
<a id="ref-2"></a>[2] OpenJDK Vulnerability Group, Advisory 2026-11-17. <https://openjdk.org/groups/vulnerability/advisories/2026-11-17>
<a id="ref-3"></a>[3] CERT-EU, Security Advisory 2026-021, 2026-11-18. <https://cert.europa.eu/publications/security-advisories/2026-021/>
<a id="ref-4"></a>[4] Microsoft, "Java OpenJDK November 2026 Critical Patch Update", 2026-11-18. <https://devblogs.microsoft.com/java/java-openjdk-november-2026-critical-patch-update/>
<a id="ref-5"></a>[5] BleepingComputer, "Critical Java4Shell flaw allows RCE attacks on major Java applications", 2026-11-17 [보도]. <https://www.bleepingcomputer.com/news/security/critical-java4shell-flaw-allows-rce-attacks-on-major-java-applications/>
<a id="ref-6"></a>[6] CISA, "CISA Adds Four Known Exploited Vulnerabilities to Catalog", 2026-11-18. <https://www.cisa.gov/news-events/alerts/2026/11/18/cisa-adds-four-known-exploited-vulnerabilities-catalog>
<a id="ref-7"></a>[7] GitHub Advisory Database, GHSA-wxxx-gvqv-xp7p (LiteLLM, CVE-2026-40217). <https://github.com/advisories/GHSA-wxxx-gvqv-xp7p>
<a id="ref-8"></a>[8] Spring, "This Week in Spring – November 18th, 2026". <https://spring.io/blog/2026/11/18/this-week-in-spring-november-18th-2026/>
<a id="ref-9"></a>[9] CNBC, Anthropic IPO pricing, 2026-11-18 [보도]. <https://www.cnbc.com/2026/11/18/anthropic-ipo-ai-offering-price.html>
<a id="ref-10"></a>[10] Axios, Anthropic IPO, 2026-11-18 [보도]. <https://www.axios.com/2026/11/18/anthropic-ipo-1-trillion>
<a id="ref-11"></a>[11] Anthropic, Claude Platform Release Notes. <https://platform.claude.com/docs/en/release-notes/overview>
<a id="ref-12"></a>[12] Google, "Introducing Gemini 4 Neon", 2026-11-18. <https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-neon/>
<a id="ref-13"></a>[13] Flower, "Announcing Flower 1.44", 2026-11-18. <https://flower.ai/blog/2026-11-18-announcing-flower-1.44-release>
<a id="ref-14"></a>[14] CrewAI Releases (1.15.42). <https://github.com/crewAIInc/crewAI/releases>
<a id="ref-15"></a>[15] LangGraph Releases. <https://github.com/langchain-ai/langgraph/releases>
<a id="ref-16"></a>[16] AWS What's New, Amazon OpenSearch Memory GA, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-opensearch-memory-generally-available/>
<a id="ref-17"></a>[17] AWS What's New, Amazon EKS Hybrid Nodes pricing change, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-hybrid-nodes-pricing-change/>
<a id="ref-18"></a>[18] AWS What's New, AWS Lambda customer-managed runtimes, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-customer-managed-runtimes/>
<a id="ref-19"></a>[19] AWS What's New, AWS Lambda GPU Managed Instances, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-gpu-managed-instances/>
<a id="ref-20"></a>[20] AWS What's New, SageMaker cross-Region routing, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/sagemaker-cross-region-routing/>
<a id="ref-21"></a>[21] AWS What's New, CloudFront origin mTLS for WebSockets/gRPC, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-cloudfront-origin-mtls-websockets-grpc/>
<a id="ref-22"></a>[22] AWS What's New, Cognito point-in-time recovery / RDS fast storage volume initialization / S3 replication exclusions, 2026-11-18. <https://aws.amazon.com/about-aws/whats-new/2026/11/cognito-point-in-time-recovery/> · <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-rds-fast-storage-volume-initialization/> · <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-s3-replication-exclusions-multi-region-key-resolution/>
<a id="ref-23"></a>[23] Microsoft Foundry Blog, "What's new in Foundry Agent Service at Ignite 2026". <https://devblogs.microsoft.com/foundry/whats-new-in-foundry-agent-service-at-ignite-2026/>
<a id="ref-24"></a>[24] Google Cloud Blog, "Run AI/ML workloads on IPv6-only GKE clusters", 2026-11-18. <https://cloud.google.com/blog/products/networking/run-aiml-workloads-on-ipv6-only-gke-clusters>
<a id="ref-25"></a>[25] Oracle, Critical Security Patch Update November 2026 – Verbose Risk Matrix. <https://www.oracle.com/security-alerts/cspunov2026verbose.html>
<a id="ref-26"></a>[26] Microsoft Tech Community, "Azure Catalyst", 2026-11-17. <https://techcommunity.microsoft.com/blog/appsonazureblog/azure-catalyst-one-connected-agent-led-modernization-experience-across-apps-data/4573988>
<a id="ref-27"></a>[27] Google Cloud Blog, "Introducing OKF v0.3", 2026-11-18. <https://cloud.google.com/blog/products/data-analytics/introducing-okf-v0-3>
<a id="ref-28"></a>[28] Google Cloud Blog, "The Envoy agentic stack: routing models, tokens and MCP", 2026-11-18. <https://cloud.google.com/blog/products/networking/the-envoy-agentic-stack-routing-models-tokens-and-mcp>
<a id="ref-29"></a>[29] Google Cloud Blog, "Lessons from building Sashiko, an agentic code review system", 2026-11-18. <https://cloud.google.com/blog/products/application-development/lessons-from-building-sashiko-an-agentic-code-review-system>
<a id="ref-30"></a>[30] NAVER Cloud Platform, 공지사항. <https://www.ncloud.com/support/notice/all>
<a id="ref-31"></a>[31] Rust Blog. <https://blog.rust-lang.org/>
<a id="ref-32"></a>[32] JetBrains Kotlin Blog. <https://blog.jetbrains.com/kotlin/>
<a id="ref-33"></a>[33] The Linux Kernel Archives. <https://www.kernel.org/>
<a id="ref-34"></a>[34] Jev Changelog. <https://docs.typesafe.ai/changelog>
<a id="ref-35"></a>[35] OpenAI, "Managing frontier AI risk", 2026-11-18. <https://openai.com/index/managing-frontier-ai-risk/>
<a id="ref-36"></a>[36] Yong, Arnav, et al., "Chain-of-Thought Controllability Can Reduce Chain-of-Thought Monitorability", arXiv:2611.21799 (preprint). <https://arxiv.org/abs/2611.21799>
<a id="ref-37"></a>[37] Shenoy et al. (Redwood Research), "Auditors Struggle to Catch Sabotage In End-to-End Transcripts of AI Safety Research", arXiv:2611.21832 (preprint). <https://arxiv.org/abs/2611.21832>
<a id="ref-38"></a>[38] Model Context Protocol Specification. <https://modelcontextprotocol.io/specification>
<a id="ref-39"></a>[39] Harvard T.H. Chan School of Public Health, hyperscale data center energy and emissions estimate, 2026-11-16 (Nature Sustainability, doi:10.1038/s41893-026-01985-7). <https://hsph.harvard.edu/news/hyperscale-data-centers-energy-consumption-carbon-emissions-newly-estimated-by-researchers/>
<a id="ref-40"></a>[40] Nature, Editorial, 2026-11-18. <https://www.nature.com/articles/d41586-026-03708-6>
<a id="ref-41"></a>[41] 토스, "앱인토스 11월 3주 업데이트", 2026-11-18. <https://toss.im/apps-in-toss/blog/update-26-11-18>
<a id="ref-42"></a>[42] LY Corporation Tech Blog. <https://techblog.lycorp.co.jp/ko>
