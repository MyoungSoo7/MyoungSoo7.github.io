---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-20"
date: 2026-11-20 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-20 08:30 KST · **수집 범위**: 주로 2026-11-18 ~ 11-19 공개분. 그보다 오래된 항목은 "이번 주 놓친 항목"으로 따로 표시하고 날짜를 적었습니다.
> **표기**: **[사실]** 1차·공식 출처 확인 / **[보도]** 신뢰 언론 보도(1차 미확인) / **[벤더 주장]** 벤더 자체 수치·벤치마크 / **[추론]** 필자 해석 / **[미확인]** 검증 못 함
> **중복 안내**: 11-19 브리핑에 실린 항목(Java4Shell 기본 내용, CISA KEV 11-18 추가 4건, Anthropic IPO 공모가, Gemini 4 Neon, CrewAI 1.15.42, 위시켓 159697·159703·159714 등)은 새 진전이 있을 때만 다시 다뤘습니다.

## 오늘의 핵심

1. **[사실] VMware vCenter 에서 CVSS 9.8 인증 우회 취약점(CVE-2026-123890)이 패치됐습니다.** 보안 업체들은 중국계 APT 가 이를 제로데이로 악용했다고 보고합니다. 다만 Broadcom 권고문에는 실제 악용 언급이 없습니다. 우회책이 없으므로 패치가 유일한 대응입니다. [[1]](#ref-1) [[2]](#ref-2)
2. **[보도] NGINX 에서 CVSS 9.2 급 취약점 5건("NGINX2Root")이 고쳐졌고 PoC 도 공개됐습니다.** HTTP/2 흐름제어 버퍼 오버플로(CVE-2026-123007)는 1.9.5 이후 모든 버전에 영향을 줍니다. OSS 1.30.7 / 1.31.9 로 올리세요. [[3]](#ref-3)
3. **[보도] Java4Shell 에 진전이 있습니다. 스캐닝과 익스플로잇 시도가 시작됐습니다.** Cisco·Elastic·Red Hat·Keycloak·Atlassian·Jenkins 가 영향 공지를 냈습니다. 성공한 침해는 아직 확인되지 않았습니다. [[4]](#ref-4)
4. **[사실] PHP 8.2–8.5 보안 릴리스가 CVE 18건을 고쳤습니다.** PHP-FPM 요청 스머글링(CVE-2026-129289, CVSS 9.2)이 포함됩니다. [[5]](#ref-5) [[6]](#ref-6)
5. **[보도] Anthropic(ANT)이 나스닥 첫 거래일을 $97.17(공모가 대비 +17%)에 마감했습니다.** 시가총액 추정치는 매체마다 달라 단정하지 않습니다. [[7]](#ref-7) [[8]](#ref-8)

## 1. AI & ML

- **[보도] Anthropic 상장 첫날 (11-19).** 어제 실은 공모가 $83 결정의 후속입니다. [[7]](#ref-7) [[8]](#ref-8) [[9]](#ref-9)
  - $111.50 에 시작해 장중 $114.99 까지 올랐고, $97.17 에 마감했습니다(+17%).
  - 시가총액은 CNBC 가 완전희석 기준 약 1.8조 달러로, Guardian 은 약 1.3조(완전희석 1.75조) 달러로 보도했습니다. **산정 기준이 달라 수치가 엇갈립니다.**
- **[사실] Claude Code 2.1.328 (11-19 01:14 UTC) / 2.1.329 (11-19 22:14 UTC).** 공식 CHANGELOG 기준입니다. [[10]](#ref-10)
  - 2.1.328: Bedrock·Google Cloud Agent Platform·Microsoft Foundry 에서 Opus 4.6 / Sonnet 4.6 에 auto mode 를 지원합니다. `mcp_tool` 훅에 `"onFailure": "block"` 이 추가돼, 훅 호출이 실패하면 작업을 막을 수 있습니다.
  - 2.1.329: 폴더의 훅이 어디서 선언됐는지 알려 주는 trust 대화상자 경고가 생겼습니다. 네트워크가 멈추거나 파일이 잠겨 `~/.claude.json` 을 읽지 못할 때 기본값으로 초기화되던 버그를 고쳤습니다. OpenTelemetry 를 켠 상태에서도 Code Mode 를 쓸 수 있습니다.
  - 2.1.327 (11-17): `claude mcp add-json <name> -` 로 stdin 에서 JSON 을 읽습니다. 토큰을 커맨드라인에 남기지 않을 수 있습니다.
- **[사실 · Anthropic 주장] "Claude 가 블랙홀 물리학의 미해결 문제 두 개를 풀었다" (11-17, 이번 주 놓친 항목).** [[11]](#ref-11)
  - Claude Fable 5.2 에이전트가 약 6주 동안 작업했습니다. 결과는 Lean 으로 형식 검증했고, 물리학자가 핵심 결과를 검토했습니다.
  - 다룬 문제는 약결합 영역의 Hawking-Page 전이와 modular bootstrap 경계입니다.
  - 독립적인 제3자 재현은 **부재**합니다.

## 2. 에이전트 프레임워크

- **[사실] LangGraph 1.2.23 / prebuilt 1.1.3 (11-19).** [[12]](#ref-12)
  - `Send` 로 디스패치된 도구 호출이 엣지 경로와 같은 state 를 받게 됐습니다(#9728).
  - `wrap_tool_call` 에서 덮어쓴 state 가 도구까지 전달됩니다(#9730).
  - 동적 스키마 경고의 레이스를 고쳤습니다(#9716).
  - opentelemetry-api 를 1.45.2 로 올렸습니다.
- **[사실] CrewAI 1.15.43 · 1.15.44 (11-19).** [[13]](#ref-13)
  - 1.15.43: Claude 5 의 멀티모달 감지를 고쳤습니다.
  - 1.15.44 (보안 관련): `FilePath` 가 작업 디렉터리(cwd) 밖을 가리키지 못하게 막습니다. Pillow 입력은 PNG/JPEG/GIF/WEBP 로 제한합니다. 버전 관리되는 공유 아티팩트가 추가됐습니다. Anthropic 파일 블록마다 `cache_control` 을 붙이던 동작을 멈췄습니다.
- **[미확인] Microsoft `agent-framework` PyPI 1.26.1 / 1.26.2 악성 버전 의혹.**
  - `.pth` 훅으로 자격증명을 훔치는 버전이 11-17 에 올라왔다는 2차 보도가 있습니다.
  - 필자가 PyPI JSON API 를 확인해 보니 현재 최신 버전은 1.26.0 이고, 1.26.1 / 1.26.2 는 목록에 없었습니다. [[14]](#ref-14)
  - Microsoft·Wiz 의 1차 공지는 확인하지 못했습니다. 그래도 **11-17 이후에 의존성을 갱신했다면 lock 파일의 버전을 점검하길 권합니다** **[추론]**.
- Devin: 이번 회차에는 공식 changelog 의 새 항목을 확인하지 못했습니다.

## 3. Kubernetes & Cloud Native

- **[사실] kubernetes.io 블로그.** 11-16 이후 새 글이 없습니다. 패치 릴리스도 이번 회차에 새로 확인된 것은 없습니다.
- **[사실] GKE Dataplane V2 인플레이스 마이그레이션 프리뷰 (11-19).** [[15]](#ref-15)
  - 기존 클러스터를 다시 만들지 않고 eBPF/Cilium 기반 Dataplane V2 로 옮길 수 있습니다.
  - 대상은 GKE 1.35 이상의 VPC-native 클러스터입니다. routes 기반 클러스터나 Calico 를 쓰는 클러스터는 지원하지 않습니다.
  - 마이그레이션을 확정(finalize)하기 전까지는 롤백할 수 있습니다.
- **[사실] 네이버 D2 「컨테이너처럼 쓰고, VM처럼 격리하기」 4부작 (11-18).** Kata Containers 로 GPU 노드를 Pod 단위 VM 으로 격리한 사례입니다. 내용은 14장에 정리했습니다. [[16]](#ref-16)

## 4. 보안

- **[사실] VMware vCenter CVE-2026-123890 (VMSA-2026-0009, CVSS 9.8).** [[1]](#ref-1) [[2]](#ref-2)
  - VMware Directory Service 의 인증 우회 취약점입니다.
  - 수정 버전은 9.1.1.0200, 9.0.2.0200, 8.0 U3m 입니다. 우회책은 없습니다.
  - 7.0 은 일반 지원이 끝나(EoGS) 연장 지원 계약이 있어야 패치를 받을 수 있습니다.
  - 같은 권고문에 SDDC Manager(CVE-2026-123891/2/3)와 VMware Tools(CVE-2026-123894) 취약점도 들어 있습니다.
  - **[보도]** Mandiant/GTIG 는 UNC5221 계열 그룹이 이 취약점을 제로데이로 썼다고 밝혔습니다. 초기 침투에는 BeyondTrust 취약점을 썼다고 합니다.
  - **주의**: 보도에 따르면 8.0 U3m 이나 9.0.2.0200 을 설치하면 이후 VCF 9.1.1 로 업그레이드하는 경로가 막힙니다. 업그레이드 계획이 있다면 경로를 먼저 확인하세요.
- **[보도] F5 "NGINX2Root" (11-18 공개).** [[3]](#ref-3)
  - 모두 22건이고, 그중 NGINX 의 치명적 취약점 5건이 CVSS 9.2 입니다.
    - 메일 프록시: CVE-2026-113425
    - HTTP/3 UAF: CVE-2026-121810
    - HTTP/2 흐름제어 오버플로: CVE-2026-123007
    - HTTP/2 UAF: CVE-2026-123633
    - resolver/SSI/mirror: CVE-2026-123634
  - 수정 버전은 OSS 1.30.7 / 1.31.9, Plus 37.0.8.1 / 37.3.0.1 입니다. 임시 완화책은 HTTP/2 비활성화입니다.
  - Rapid7 이 PoC 를 공개했습니다. F5 는 실제 악용은 없다고 밝혔습니다.
  - **[추론]** Ingress-NGINX 처럼 NGINX 를 내장한 컨트롤러는 업스트림 패치가 반영된 이미지가 나왔는지 따로 확인해야 합니다.
- **[사실] PHP 8.5.13 / 8.4.28 / 8.3.37 / 8.2.36 (11-19).** CVE 18건을 고쳤습니다. [[5]](#ref-5) [[6]](#ref-6)
  - CVE-2026-129289: PHP-FPM 요청 스머글링(CVSS 9.2)입니다. 백엔드 연결을 재사용할 때만 발생하며, 지속 연결을 끄면 완화됩니다.
  - CVE-2026-126714: 세션 파일 부분 덮어쓰기입니다(GHSA-fm2m-fjf5-v3cp).
  - CVE-2026-115560: 패치 전에는 `session.upload_progress.enabled=0` 으로 완화할 수 있습니다.
- **[보도] Java4Shell(CVE-2026-114938) 진전 (11-19).** [[4]](#ref-4)
  - GreyNoise 는 150건 넘는 탐색 요청을 관측했습니다. watchTowr 도 스캐닝을 보고했습니다. 성공한 침해는 아직 보고되지 않았습니다.
  - 벤더별 상황:
    - Cisco: 십여 개 제품이 영향을 받으며, 수정판은 아직 없습니다.
    - Elastic: Elasticsearch 7.17.3 이상이 영향을 받습니다.
    - Red Hat: RHEL 8/9/10 을 Critical 로 분류했습니다.
    - Keycloak: 26.8.2-3 이미지에 수정이 들어갔습니다.
    - Atlassian: Data Center 의 임시 우회책은 AVX-512 비활성화입니다.
    - Jenkins: Java 를 업데이트한 뒤 재시작하라고 안내했습니다.
  - 취약점은 AVX-512 VBMI 를 지원하는 x86-64 에서만 발현됩니다. ARM 은 영향이 없습니다.
- **CISA KEV**: 11-19 자 신규 추가는 확인하지 못했습니다. 11-18 의 4건은 어제 다뤘습니다.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

**AWS (11-19)**

- **[사실] AWS Marketplace 에이전트 결제.** AgentCore payments 로 x402 프로토콜 결제를 지원합니다. [[17]](#ref-17)
- **[사실] AWS Marketplace Data-as-a-Service GA.** MCP 서버 예시가 함께 공개됐습니다. Express checkout 과 agent mode 확장도 같은 날 나왔습니다. [[18]](#ref-18)
- **[사실] AWS AppConfig 에 AI 모델 호출·프롬프트 설정 기능이 추가됐습니다.** 모델과 프롬프트 설정을 점진 배포하고 자동 롤백할 수 있습니다. 추가 비용은 없습니다. [[19]](#ref-19)
- **[사실] Lambda.** [[20]](#ref-20) [[21]](#ref-21)
  - 온디맨드 이벤트 함수의 최대 실행 시간이 30분으로 늘었습니다.
  - Durable Execution SDK for Rust 가 GA 됐습니다.
  - durable 함수에 OpenTelemetry 추적이 붙었습니다(12장 참고).
- **[사실] EC2 성능 상태 검사.** GPU 검사와 OTel 지표, 1분 단위 GPU 지표, 10초 단위 CPU 지표가 추가됐습니다. Route 53 은 private endpoint 헬스체크를 지원합니다. [[22]](#ref-22)

**GCP (11-19)**

- **[사실] Gemini 플랫폼 "deferred" 서비스 티어 GA.** `service_tier="deferred"` 로 쓰며, Standard PayGo 대비 50% 할인입니다. 지연을 허용하는 배치성 작업에 맞습니다. [[23]](#ref-23)
- **[사실 · 벤더 주장] Cloud Storage object enrichments 프리뷰.** 비정형 객체에서 AI 로 메타데이터를 추출합니다. [[24]](#ref-24)
  - "1천만 객체당 $700" 은 Google 이 자사 공개 가격으로 제시한 수치입니다.
  - "타 클라우드 대비 75% 절감" 은 **벤더 주장**이며, 중립적인 비교는 **부재**합니다.
- **[사실] GKE Dataplane V2 인플레이스 마이그레이션** (3장 참고). [[15]](#ref-15)

**Azure (Ignite 2026, 11-17 ~ 11-19)**

- **[사실] Ignite Book of News 의 인프라 항목.** [[25]](#ref-25)
  - 프리뷰: AKS Agent Sandbox 확장, AKS Flex nodes, AKS Kata 기반 기밀 컨테이너(CoCo), Confidential Clean Room.
  - Cobalt 200 은 11-17 에 GA 됐습니다.
- **[사실] Foundry Agent Service 호스티드 에이전트 (11-18).** [[26]](#ref-26)
  - GA: egress 제어, 장기 실행, idle timeout 설정.
  - 프리뷰: private CA 신뢰, 메모리 스냅샷.
  - 기존 AKS 에 배포하는 BYO-AKS 는 12월 초를 목표로 합니다.

**Naver Cloud**

- 이번 회차에는 공지사항을 확인하지 못했습니다. **[미확인]**

## 6. 언어 · 런타임

- **[사실] Jetpack Compose 2026년 11월 릴리스 / BOM 2026.11.01 (11-18).** Kotlin 2.2 이상이 필요합니다. Material 3 1.5.0 이 포함됐고, A2UI 렌더러가 알파로 나왔습니다. [[27]](#ref-27)
- **[사실] PHP 보안 릴리스** (4장 참고).
- **Java**: Java4Shell 진전은 4장에 정리했습니다. GraalVM 25.6.0 은 11-24 출시 예정입니다(예정 사항).
- **[미확인] Next.js CVE-2026-119351 (16.4.5 에서 수정).** 2차 출처에서만 봤고 GitHub Advisory 원문은 확인하지 못했습니다.
- Python, Rust, TypeScript, Vue, Spring: 11-18 ~ 11-19 에 새 정식 릴리스를 확인하지 못했습니다. Rust 1.100.0(11-12)은 지난 브리핑에서 다뤘습니다.

## 7. 인프라 & Linux

- **[사실] kernel.org.** 새 릴리스가 없습니다. [[28]](#ref-28)
  - mainline: 7.4-rc3 (11-15)
  - stable: 7.3.5 (11-17, 지난 브리핑에서 다룸)
  - longterm: 6.18.64 / 6.12.118 (11-17)
- **[사실] VMware vCenter·NGINX 패치** (4장 참고). 오늘 인프라 운영에서 가장 시급한 일입니다.
- **[추론] 우선순위.** 외부에 노출된 NGINX 와 vCenter 관리 인터페이스를 먼저 처리하세요. 그다음이 Java4Shell 대상인 AVX-512 VBMI 지원 x86 호스트입니다.

## 8. [특집] Jev API 와 판단 모델

### 오늘의 변화

- **[사실] 새 릴리스가 없습니다.** 공식 changelog 의 최신 버전은 여전히 1.14(10-14)입니다. [[29]](#ref-29)

### 어떻게 읽을 것인가

- **[추론]** 이번 주 다른 생태계에서는 "판단을 누가, 어디서 실행하느냐" 를 설정과 정책으로 분리하는 흐름이 보였습니다.
  - AWS AppConfig 가 모델·프롬프트 설정을 코드 밖으로 빼 점진 배포하고 롤백합니다. [[19]](#ref-19)
  - Claude Code 2.1.328 의 `"onFailure": "block"` 은 정책 훅이 실패하면 안전한 쪽(차단)으로 닫는 fail-closed 옵션입니다. [[10]](#ref-10)
  - 판단 모델을 운영 환경에 둔다면 이 두 장치를 함께 볼 만합니다. 하나는 판단 로직의 버전을 바꾸고 되돌리는 장치이고, 다른 하나는 판단기가 응답하지 않을 때의 기본 동작입니다.

### 실무 체크포인트

1. 판단 모델의 버전이나 프롬프트를 바꿀 때 점진 배포와 자동 롤백 경로가 있는지 확인합니다.
2. 판단 호출이 타임아웃되거나 실패했을 때 기본 동작이 허용(fail-open)인지 차단(fail-closed)인지 문서화합니다.
3. Jev 를 쓰고 있다면 1.14 이후 변경이 없으므로, 이번 주에는 버전을 올릴 필요가 없습니다.

## 9. AI 안전 · 정렬

- **[사실] Anthropic, 조율된 취약점 공개(CVD) 정책 기한 단축 (11-16, 이번 주 놓친 항목).** 2027-01-01 이후 접수분부터 적용됩니다. [[30]](#ref-30)
  - 높음·치명 등급의 공개 기한을 90일에서 30일로, 그 밖의 등급은 45일로 줄입니다.
  - 외부 조정 기관에 넘기는 시점은 30일에서 15일로, 패치 후 기술 세부를 공개하는 시점은 45일에서 30일로 앞당깁니다.
  - 실제 악용 중인 취약점의 7일 기한은 그대로입니다.
  - **[추론]** AI 로 취약점을 찾는 속도가 빨라지면서 공개 기한도 짧아지는 흐름입니다. 오픈소스 메인테이너에게는 대응 부담이 늘어납니다.
- **[사실, 프리프린트] GateWatch (arXiv 2611.24619, 11-18 제출).** SAE 피처 위에 불리언 회로를 얹은 경량 모니터입니다. [[31]](#ref-31)
  - Gemma-2-9B 에서 평균 정확도 80.49% 를 기록했습니다. 피처 약 3.8개와 게이트 약 3.5개만 씁니다.
  - 전체 SAE 프로브보다 1.17%p 낮지만 프로브 메모리는 99.98% 줄었습니다.
  - 저자 보고 수치이며, 독립 재현은 **부재**합니다.
- **[사실, 프리프린트] Training Language Models for Introspective Oversight (arXiv 2611.23365, 11-17).** 모델이 관찰자 역할로 자기 내부 상태를 보고하도록 훈련합니다. 관찰자 역할의 AUROC 0.907 은 저자 보고 수치입니다. [[32]](#ref-32)

## 10. MCP 생태계

- **[사실] AWS Marketplace DaaS GA 에 MCP 서버 예시가 포함됐습니다 (11-19).** 데이터 상품을 에이전트가 MCP 로 소비하는 경로입니다. [[18]](#ref-18)
- **[사실] Claude Code 의 MCP 관련 변경** (11-17 ~ 11-19). [[10]](#ref-10)
  - `mcp add-json` 이 stdin 을 받습니다.
  - `mcp_tool` 훅에 `onFailure: block` 이 생겼습니다.
  - HTTP MCP 서버가 연결을 거부하면 JSON-RPC 오류 메시지를 표시합니다.
- **이번 주 놓친 항목.**
  - **[사실] MCP 블로그 "A More Predictable Release Cycle" (11-11).** 스펙 릴리스를 매년 3월·9월 마지막 화요일로 고정합니다. 다음 스펙은 2027-03-30 입니다(SEP-3398). [[33]](#ref-33)
  - **[사실] MCP Java SDK v2.2.0 (11-16).** `io.modelcontextprotocol.modern` 패키지에 2026-07-28 스펙용 stateless 서버·클라이언트가 추가됐습니다. roots·sampling·logging 은 SEP-2577 에 따라 deprecated 됐습니다. **Spring 기반 MCP 서버를 운영한다면 확인할 항목입니다.** [[34]](#ref-34)

## 11. MLOps · 피처 스토어

- **[사실] 11-18 ~ 11-19 에 MLflow·Feast·Kubeflow 의 새 릴리스는 확인하지 못했습니다.** 이번 주 이전의 최신판만 참고로 적습니다.
  - MLflow 3.18.0 (11-02): Automatic Issue Detection, 실험적 Skill Registry, 코드 기반 온라인 평가가 들어갔습니다. [[35]](#ref-35)
  - Kubeflow Community Distribution 26.10.0 (11-06): Trainer 2.4.0, KServe 0.21.0, Pipelines 2.18.0 이 포함됐습니다. [[36]](#ref-36)
- **[사실] 국내 사례: 카카오 LLM 추론 플랫폼의 KV 캐시 오프로딩과 EPP 라우팅 (11-18).** LMCache 와 Gateway API Inference Extension 의 EPP 를 결합했습니다. 상세는 14장에 정리했습니다. [[37]](#ref-37)

## 12. 에이전트 관측성

- **[사실] AWS Lambda durable functions OpenTelemetry 추적 (11-19).** TypeScript·Python·Java SDK 에서 durable 실행 단계를 OTel 트레이스로 남깁니다. [[21]](#ref-21)
- **[사실] LangGraph 1.2.23 이 opentelemetry-api 를 1.45.2 로 올렸습니다.** [[12]](#ref-12)
- **[사실] Claude Code 2.1.329: OTel 이벤트·지표를 켠 상태에서 Code Mode 를 쓸 수 있습니다.** 다만 tracing 을 켜면 Code Mode 는 여전히 꺼집니다. [[10]](#ref-10)
- **이번 주 놓친 항목**: Azure Monitor 에이전트 관측성(11-17) 발표가 있었습니다. 교차 에이전트 디버깅은 프리뷰이고, 외부 에이전트 관측·평가는 GA 입니다. [[38]](#ref-38)
- **[추론]** OTel GenAI 시맨틱 컨벤션은 여전히 Development 상태입니다. 그래서 대시보드와 알림을 속성 이름에 하드코딩하기보다, 수집 단계에서 속성을 매핑해 두는 편이 안전합니다.

## 13. 그린 컴퓨팅

- **11-19 자 1차 출처 신규 항목은 확인하지 못했습니다.** 11-16 Harvard/Nature Sustainability 추정치와 11-18 Nature 사설은 지난 브리핑에서 다뤘습니다.
- **[추론] 효율 관점에서 볼 만한 사례.** 같은 하드웨어에서 더 많은 일을 처리하는 것도 에너지 효율 개선입니다.
  - 카카오는 같은 GPU 32장으로 처리 시간을 121.7분에서 47.2분으로 줄였다고 보고했습니다. 이 수치는 단일 측정 결과이며, 원문도 "GPU 절감으로 바꿔 읽지 말라" 고 밝혔습니다. [[37]](#ref-37)
  - Gemini deferred 티어처럼 지연을 허용하는 실행은 사업자가 유휴 용량에 작업을 배치할 수 있는 구조입니다. 다만 실제 탄소 영향은 공개된 바 없습니다. [[23]](#ref-23)

## 14. 국내 기술 블로그

우선 확인 대상(Naver D2·Kakao·LINE/LY·Coupang·우아한형제들·당근·토스·두나무) 가운데 **11-18 자 새 글은 네이버 D2 와 카카오에서만 확인했습니다.** 11-17 자 토스 글 3편, 당근 ARC 글, if(kakao)26 스케치는 11-18 브리핑에서 이미 다뤘습니다.

| 기업 | 제목 | 날짜 | 요약 | 원문 |
| --- | --- | --- | --- | --- |
| 카카오 | 같은 GPU로 더 많은 AI 요청을 처리할 수 있을까? ― KV 캐시 오프로딩 × EPP 라우팅 | 2026-11-18 | **[사실 · 사내 실험 수치]** vLLM 32B 모델에 LMCache(CPU·NVMe 오프로딩)와 EPP 프리픽스 인지 라우팅을 결합했습니다. A100 32장에서 처리량이 2.58배가 됐습니다. 오프로딩만 쓰면 1.19배, 라우팅만 쓰면 1.15배였습니다. 단일 측정이고 서비스와 분리된 노드에서 실험했다고 원문이 밝혔습니다. 원격 캐시(Redis·S3, 25GbE)는 재계산보다 느려 이번 구성에서 제외했습니다. | [[37]](#ref-37) |
| 네이버 | 컨테이너처럼 쓰고, VM처럼 격리하기 1–4편 | 2026-11-18 | **[사실]** Kubernetes GPU 노드에 Kata Containers 를 적용해 Pod 마다 VM 을 띄워 격리한 사례입니다. 다룬 주제는 VFIO 패스스루, Fabric Manager 파티션의 DRA 할당, IB NIC·로컬 NVMe 연결, 베어메탈 대비 성능입니다. NAVER Engineering Day 10th 발표를 정리한 연재입니다. | [[16]](#ref-16) |

- LY Corp, 쿠팡, 우아한형제들, 두나무는 이번 회차에 11-18 ~ 11-19 자 새 글을 확인하지 못했습니다. **[미확인]**

## 15. Java/Spring 프리랜서 공고

공개 페이지에서 확인한 내용만 적었습니다(로그인이 필요한 정보는 제외). 수집일은 모두 2026-11-20 입니다.

- 모두 위시켓 원문 페이지를 직접 조회해 **마감일이 지나지 않은 것**을 확인했습니다.
- **등록일은 11-11 ~ 11-13 이라 신규 공고는 아닙니다.** 지난 브리핑에 싣지 않은 것만 골랐습니다.
- 11-19 ~ 11-20 에 새로 등록된 Java/Spring 공고는 검증 가능한 형태로 찾지 못했습니다.
- 프리모아와 이랜서는 이번 회차에도 검증 가능한 공개 공고를 확보하지 못했습니다.

| 플랫폼 | 제목 | 스택 | 형태 | 금액 | 수집일 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | Java/Spring 기반 대외 여신(대출) 및 대외 보증·정산 연계 개발 | Java, Spring | 기간제 · 840일 · 서울 마포 · 미드 7–9년 / 시니어 10–25년 · 저축은행 차세대 SI | 월 650만 / 750만 원 | 2026-11-20 | [159582](https://project.wishket.com/project/159582/) — 등록 11-11, 마감 11-25 (모집 중) |
| 위시켓 | Java/Spring Boot 기반 금융사 모바일 앱 차세대 구축 백엔드 개발 | Java, Spring Boot | 기간제 · 30일 · 12-01 시작 · 서울 영등포 · 미드 2–5년 | 월 500만 원 | 2026-11-20 | [159586](https://project.wishket.com/project/159586/) — 등록 11-11, 마감 11-25 (모집 중) |
| 위시켓 | AWS/Java Spring Boot 기반 서비스 인프라 이관 DevOps·백엔드 개발 | Java, Spring Boot, AWS, EKS Fargate | 기간제 · 120일 · 서울 성동 · 시니어 7–10년 | 월 800만 원 | 2026-11-20 | [159587](https://project.wishket.com/project/159587/) — 등록 11-11, 마감 11-25 (모집 중) |
| 위시켓 | Java/Kotlin·Spring Boot 기반 쇼핑몰 운영 백엔드 SM | Java, Kotlin, Spring Boot, JPA | SM · 360일 · 2027-01-01 시작 · 서울 용산 · 시니어 8–10년 | 협의 | 2026-11-20 | [159643](https://project.wishket.com/project/159643/) — 등록 11-13, 마감 11-27 (모집 중) |
| 위시켓 | Java/JSP 기반 공공기관 차세대 전환 구축 웹 개발 | Java, JSP | 기간제 · 90일(9개월 연장 가능) · 서울 금천 · 주니어 1–5년 | 월 550만 원 | 2026-11-20 | [159608](https://project.wishket.com/project/159608/) — 등록 11-12, 마감 11-26 (모집 중) |

- "모집 중"은 수집 시점의 공개 페이지 기준입니다. 상주 여부와 세부 조건은 공개 범위에서 확인하지 못했으니, 지원 전에 원문을 다시 확인하세요.

---

## 사실 · 추론 · 미확인 정리

- **사실(1차·공식 확인)**
  - Claude Code 2.1.327–2.1.329 CHANGELOG
  - Anthropic CVD 정책 변경, 블랙홀 연구 글(연구 결과 자체는 Anthropic 주장)
  - LangGraph 1.2.23, CrewAI 1.15.43/44
  - GKE DPv2 마이그레이션
  - PHP 보안 릴리스와 GHSA
  - AWS 11-19 발표, Gemini deferred 티어, Compose BOM
  - kernel.org, Jev changelog, MCP 릴리스 주기 글, Java SDK v2.2.0
  - 카카오·네이버 D2 원문, 위시켓 공고 원문
- **보도(1차 일부 미확인)**
  - VMware 제로데이 악용 귀속(Mandiant/GTIG 보도이며, Broadcom 권고문에는 악용 언급 없음)
  - NGINX2Root 세부
  - Java4Shell 스캐닝·벤더 공지 묶음
  - Anthropic 상장 첫날 시세와 시가총액
- **벤더 주장**
  - Cloud Storage enrichments "75% 절감"
  - 카카오 2.58배(사내 단일 측정)
  - GateWatch·Introspective Oversight 수치(저자 보고)
- **추론**
  - Ingress-NGINX 영향, 패치 우선순위
  - Jev 특집의 fail-closed 해석
  - CVD 기한 단축의 의미, 그린 컴퓨팅 해석
- **미확인**
  - MS agent-framework 악성 버전(PyPI 에서 해당 버전이 사라진 것만 확인)
  - Next.js CVE-2026-119351
  - Naver Cloud 공지, Devin, Spring·Python 신규 릴리스
  - LY·쿠팡·우아한형제들·두나무 신규 글, 프리모아·이랜서 공고

## References

<a id="ref-1"></a>[1] SecurityWeek, "Newly Patched VMware vCenter Flaw Exploited as Zero-Day by Chinese APT", 2026-11-19. <https://www.securityweek.com/newly-patched-vmware-vcenter-flaw-exploited-as-zero-day-by-chinese-apt/>

<a id="ref-2"></a>[2] The Hacker News, "Critical VMware vCenter Flaw (CVSS 9.8)", 2026-11. <https://thehackernews.com/2026/11/critical-vmware-vcenter-flaw-cvss-98.html>

<a id="ref-3"></a>[3] SecurityWeek, "F5 Patches Critical NGINX2Root Flaws as PoC Exploits Go Public", 2026-11-19. <https://www.securityweek.com/f5-patches-critical-nginx2root-flaws-as-poc-exploits-go-public/>

<a id="ref-4"></a>[4] SecurityWeek, "Java4Shell Exploitation Attempts Begin as Vendors Rush Out Advisories", 2026-11-19. <https://www.securityweek.com/java4shell-exploitation-attempts-begin-as-vendors-rush-out-advisories/>

<a id="ref-5"></a>[5] PHP Security Advisory GHSA-fm2m-fjf5-v3cp (php/php-src). <https://github.com/php/php-src/security/advisories/GHSA-fm2m-fjf5-v3cp>

<a id="ref-6"></a>[6] BleepingComputer, "PHP security updates fix 18 flaws, including critical RCE bugs", 2026-11-19. <https://www.bleepingcomputer.com/news/security/php-security-updates-fix-18-flaws-including-critical-rce-bugs/>

<a id="ref-7"></a>[7] CNBC, "Anthropic IPO (ANT) live updates", 2026-11-19. <https://www.cnbc.com/2026/11/19/anthropic-ipo-ant-live-updates.html>

<a id="ref-8"></a>[8] The Guardian, "Anthropic public trading IPO", 2026-11-19. <https://www.theguardian.com/technology/2026/nov/19/anthropic-public-trading-ipo>

<a id="ref-9"></a>[9] CBS News, "Anthropic IPO Nasdaq debut", 2026-11-19. <https://www.cbsnews.com/news/anthropic-ipo-nasdaq-debut-claude-ai/>

<a id="ref-10"></a>[10] Anthropic, Claude Code CHANGELOG (v2.1.327–v2.1.329). <https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md>

<a id="ref-11"></a>[11] Anthropic, "Claude solves two open problems in the physics of black holes", 2026-11-17. <https://www.anthropic.com/research/claude-black-hole-physics>

<a id="ref-12"></a>[12] LangChain, LangGraph Releases (1.2.23 / prebuilt 1.1.3). <https://github.com/langchain-ai/langgraph/releases>

<a id="ref-13"></a>[13] CrewAI Releases (1.15.43 / 1.15.44). <https://github.com/crewAIInc/crewAI/releases>

<a id="ref-14"></a>[14] PyPI, agent-framework 프로젝트 페이지. <https://pypi.org/project/agent-framework/>

<a id="ref-15"></a>[15] Google Cloud Blog, "GKE Dataplane V2 in-place migration", 2026-11-19. <https://cloud.google.com/blog/products/networking/gke-dataplane-v2-in-place-migration>

<a id="ref-16"></a>[16] NAVER D2, "컨테이너처럼 쓰고, VM처럼 격리하기" 1–4편, 2026-11-18. <https://d2.naver.com/helloworld/8055238> (연재 목록: <https://d2.naver.com/home>)

<a id="ref-17"></a>[17] AWS What's New, AWS Marketplace agentic payments with AgentCore, 2026-11-19. <https://aws.amazon.com/about-aws/whats-new/2026/11/marketplace-agentic-payments-agentcore/>

<a id="ref-18"></a>[18] AWS What's New, AWS Marketplace Data-as-a-Service, 2026-11-19. <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-marketplace-data-as-a-service/>

<a id="ref-19"></a>[19] AWS What's New, AWS AppConfig native AI model invocation and prompt configurations, 2026-11-19. <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-appconfig-native-ai-model-invocation-prompt-configurations/>

<a id="ref-20"></a>[20] AWS What's New, Lambda Durable Execution SDK for Rust, 2026-11-19. <https://aws.amazon.com/about-aws/whats-new/2026/11/lambda-durable-execution-sdk-rust/>

<a id="ref-21"></a>[21] AWS What's New, Lambda durable functions OpenTelemetry tracing, 2026-11-19. <https://aws.amazon.com/about-aws/whats-new/2026/11/lambda-durable-otel/>

<a id="ref-22"></a>[22] AWS What's New, EC2 performance status checks, 2026-11-19. <https://aws.amazon.com/about-aws/whats-new/2026/11/ec2-performance-status-checks/>

<a id="ref-23"></a>[23] Google Cloud, "What's new with Google Cloud" (Nov 16–20, Gemini deferred tier). <https://cloud.google.com/blog/topics/inside-google-cloud/whats-new-google-cloud>

<a id="ref-24"></a>[24] Google Cloud Blog, "Cost-effective AI context extraction from unstructured GCS data", 2026-11-19. <https://cloud.google.com/blog/products/storage-data-transfer/cost-effective-ai-context-extraction-from-unstructured-gcs-data>

<a id="ref-25"></a>[25] Microsoft, Ignite 2026 Book of News. <https://news.microsoft.com/events/ignite/2026/book-of-news/>

<a id="ref-26"></a>[26] Microsoft Foundry Blog, "Hosted agents in Foundry Agent Service", 2026-11-18. <https://devblogs.microsoft.com/foundry/hosted-agents-foundry-agent-service-ignite-2026/>

<a id="ref-27"></a>[27] Android Developers Blog, "Jetpack Compose November 2026 release", 2026-11-18. <https://developer.android.com/blog/posts/jetpack-compose-november-2026-release>

<a id="ref-28"></a>[28] The Linux Kernel Archives. <https://www.kernel.org/>

<a id="ref-29"></a>[29] Jev Changelog. <https://docs.typesafe.ai/changelog>

<a id="ref-30"></a>[30] Anthropic Frontier Red Team, "Updating our coordinated vulnerability disclosure policy timelines", 2026-11-16. <https://www.anthropic.com/research/coordinated-vulnerability-disclosure-timelines>

<a id="ref-31"></a>[31] Spanioli & David, "GateWatch", arXiv:2611.24619 (preprint). <https://arxiv.org/abs/2611.24619>

<a id="ref-32"></a>[32] "Training Language Models for Introspective Oversight", arXiv:2611.23365 (preprint). <https://arxiv.org/abs/2611.23365>

<a id="ref-33"></a>[33] MCP Blog, "A More Predictable Release Cycle", 2026-11-11. <https://blog.modelcontextprotocol.io/posts/mcp-release-cycle/>

<a id="ref-34"></a>[34] MCP Java SDK v2.2.0 Release, 2026-11-16. <https://github.com/modelcontextprotocol/java-sdk/releases/tag/v2.2.0>

<a id="ref-35"></a>[35] MLflow, "MLflow 3.18.0 Highlights", 2026-11-02. <https://mlflow.org/releases/3.18.0/>

<a id="ref-36"></a>[36] Kubeflow Community Distribution 26.10.0, 2026-11-06. <https://github.com/kubeflow/community-distribution/releases/tag/26.10.0>

<a id="ref-37"></a>[37] 카카오 기술블로그, "같은 GPU로 더 많은 AI 요청을 처리할 수 있을까? ― KV 캐시 오프로딩 × EPP 라우팅", 2026-11-18. <https://tech.kakao.com/posts/848>

<a id="ref-38"></a>[38] Microsoft Tech Community, "Agent observability in Azure Monitor at Ignite 2026", 2026-11-17. <https://techcommunity.microsoft.com/blog/azureobservabilityblog/agent-observability-in-azure-monitor-at-ignite-2026/4573966>
