---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-11"
date: 2026-11-11 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-11 08:30 KST. "최신"은 11-10~11-11 날짜 항목만 셉니다.
> 라벨: **[사실]** 1차·공식 출처 / **[보도]** 언론 보도(1차 미확인) / **[벤더 주장]** 벤더 자체 수치 / **[추론]** 필자 해석 / **[미확인]** 검증하지 못함.
> 11-10 브리핑과 겹치는 항목(Fable·Mythos 5.2 출시, 11-09 KEV 4건, SSHole, KubeRay 기증 발표, MCP 12-15 사양 계획 등)은 새 진전이 있을 때만 다룹니다.

## 오늘의 핵심

- **Anthropic이 IPO 로드쇼를 시작했습니다.** 공모가 밴드는 $70–78, 티커는 Nasdaq "ANT"입니다. [사실] [1]
- 같은 날 보도에 따르면 Anthropic은 정정 증권신고서에서 **RSP의 'AI R&D' 임계치를 넘었다고 판단**했다고 밝혔습니다. [보도] [5]
- **CNCF가 KubeCon NA를 맞아 Sandbox 신규 5종을 발표**했습니다. Agent Substrate·OpenShell·gVisor·KubeRay·OpenRL입니다. llm-d는 1.0이 됐고 Kubeflow는 졸업했습니다. [사실] [8]
- **11월 Patch Tuesday**가 나왔습니다. Outlook 제로데이(CVE-2026-124194)가 있고, CISA는 같은 날 KEV 6건을 추가했습니다. [사실] [12][13]
- 토스와 우아한형제들이 11-10에 새 기술 글을 올렸습니다. 토스 글은 망분리 환경의 Agent Platform 설계기입니다. [사실] [24][25]

---

## 1. AI/ML

### Anthropic IPO 로드쇼 개시
- [사실] Anthropic은 Class A 보통주 825,000,000주를 공모합니다. 이 가운데 801,351,354주는 회사 신주이고 23,648,646주는 기존 주주 매출분입니다. 공모가 밴드는 주당 $70–78, 상장 예정 시장은 Nasdaq(티커 "ANT")입니다. 인수단에는 123,750,000주의 30일 추가 매입 옵션이 있습니다. [1]
- [보도] CNBC는 익명 소식통을 인용해 가격 결정은 11-18, 거래 시작은 11-19로 예상된다고 보도했습니다. 약 20%가 개인투자자에게 배정된다고도 전했습니다. AMD·Broadcom·Google·Micron·Microsoft·Nvidia·TSMC에는 $26B 규모의 Class N 사모 배정이 있다고 보도했습니다. [2]
- [보도] TechCrunch는 밴드 상단 기준 내재 기업가치를 최대 $1.404T로 계산했습니다. 같은 기사는 10월 말 연환산 매출 $81B, 3분기 매출 $17B를 전했습니다. 이 수치는 신고서 기반이라는 보도이며, 필자는 SEC 원문을 직접 대조하지 않았습니다. [3]

### Claude 제품군 업데이트 (11-10)
- [보도] TechCrunch와 Axios에 따르면 다음 업데이트가 발표됐습니다. [4][4b]
  - **Claude Meetings**: Team·Enterprise 플랜 베타로 시작하며 Google Meet를 먼저 지원합니다. 외부 게스트가 있는 통화에는 관리자 허용 없이 참여하지 않고, 외부 게스트가 들어오면 통화에서 나갑니다.
  - **Whiteboards·Sheets**: 유료 플랜 베타입니다.
  - **Claude Data**: 이전 이름은 Dashboards이며 GA가 됐습니다.
  - **인터랙티브 커넥터**: Adobe·Atlassian·HubSpot이 추가됐습니다.
- [미확인] anthropic.com 뉴스룸에서 이 발표의 1차 게시물은 확인하지 못했습니다. 확인된 뉴스룸 게시물은 로드쇼 공지뿐입니다.

### 그 밖의 모델 소식
- [사실] Google은 개발자용 **Gemini 4 Carbon**을 공개했습니다. [6]
- [사실] Google Cloud는 **Gemini for healthcare**를 프리뷰로 발표했습니다. [7]
- 신경과학·BCI: 오늘 1차 출처로 확인한 신규 항목은 없습니다.

## 2. 에이전트 프레임워크

- [사실] **Devin CLI v3000.12.43**(11-09)이 나왔습니다. [9]
  - 이미지 읽기에 `image_size` 파라미터가 추가됐습니다.
  - 도구 호출 전에 출력이 잘리면 이제 턴을 계속 이어갑니다. 예전 동작을 원하면 `--continue-on-output-truncation=false`를 씁니다.
- [사실] CrewAI 1.15.39(11-09)는 문서만 바뀐 릴리스입니다.
- LangGraph: 1.2.20(11-05) 이후 1차 출처로 확인한 새 릴리스는 없습니다. npm `@langchain/langgraph` 1.7.3이 11-10에 나왔다는 제3자 표기가 있지만 [미확인]입니다.
- [추론] 토스의 Agent Platform 글(14절)은 하네스를 "교체 가능한 부품"으로 보고, 격리·권한·세션 영속은 플랫폼이 맡는 구조를 택했습니다. KubeCon 키노트 제목 "The Harness Is the New Runtime"과 같은 방향입니다.

## 3. Kubernetes & Cloud Native

### CNCF KubeCon NA 발표 (11-10)
- [사실] 신규 Sandbox 프로젝트 5종이 발표됐습니다. [8]
  - **Agent Substrate**
  - **OpenShell**: NVIDIA가 주도합니다.
  - **gVisor**
  - **KubeRay**
  - **OpenRL**
- [사실] 프로젝트 단계 변화도 있었습니다. [8]
  - **llm-d**가 CNCF에 합류했고 1.0이 됐습니다.
  - **Kubeflow**가 졸업했습니다.
  - **HAMi**는 Incubating으로 올라갔습니다.
- [사실] Kubernetes AI Conformance 인증 플랫폼은 40개입니다. CNCF 프로젝트 수는 231개입니다. [8]
- [사실] NVIDIA는 **Agent Substrate**의 구조를 설명했습니다. 유휴 에이전트 세션을 메모리·파일시스템째 체크포인트한 뒤, 미리 데워 둔 워커 Pod 풀에 복원하는 방식입니다. "10배 높은 밀도"는 [벤더 주장]이며 중립 재현은 부재합니다. [10]
- [사실] Google Cloud는 Kubernetes 위의 오픈 AI 스택을 정리했습니다. OpenRL·llm-d 1.0·KubeRay·Agent Substrate·gVisor·TorchTPU를 하나로 묶었습니다. [11]
- KubeCon 키노트(일정표 기준)는 다음과 같습니다. 실제 발표 내용은 영상·자료가 공개된 뒤 다루겠습니다.
  - "Agent Substrate: Open Layers for Agentic Systems"
  - "Sandbox Your Agents": Red Hat, Confidential Containers와 OpenShell
  - "The Harness Is the New Runtime"
  - "One Kubernetes, Different Environments": VM API, Workload Conformance WG

### 관리형 K8s
- [사실] AWS가 EKS용 **Nitro Sandboxes**를 발표했습니다(11-09). 하드웨어 기반 워크로드 격리입니다. [11b]
- [사실] **GKE dynamic slicing on TPUs**가 GA가 됐습니다(11-09). "최대 5배"는 [벤더 주장]입니다. [11c]
- [추론] gVisor·OpenShell의 CNCF 편입, Nitro Sandboxes, Agent Substrate가 같은 주에 나왔습니다. 그래서 올해 KubeCon의 축은 "에이전트 코드를 어디서 어떻게 격리해 돌릴 것인가"로 보입니다.

## 4. 보안

- [사실] **CISA가 KEV 6건을 추가**했습니다(11-10). [13]
  - CVE-2026-20320: Cisco BroadWorks XXE
  - CVE-2026-111560: Barracuda 여러 제품의 OS 명령 주입
  - CVE-2026-111793: Openwave Webtop Media Transcoder
  - CVE-2026-116606: Barracuda ESG 인증 우회
  - CVE-2026-124194: Microsoft Outlook
  - CVE-2026-125350: Google Chromium UAF
- [사실] **Microsoft 11월 Patch Tuesday**가 나왔습니다.
  - 제로데이는 **CVE-2026-124194**(Outlook 스푸핑, CVSS 6.5)이며 NTLMv2 해시 노출로 이어집니다. [12][14]
  - Tenable은 Microsoft가 이 취약점의 발견자로 Claude를 활용한 연구자를 크레딧했다고 적었습니다. [14]
- [보도] 패치 건수는 집계 기준에 따라 다릅니다. BleepingComputer는 1,235건, Tenable은 CVE 1,093건(Critical 63건), The Register는 1,094건으로 셌습니다. 어느 수치든 "1,000건 이상"이라는 점만 공통입니다. [12][14][15]
- [보도] The Register가 짚은 제로클릭 Critical 취약점은 두 건입니다. [15]
  - **CVE-2026-116928**: Windows Search RCE(CVSS 9.8)로, Exchange 첨부파일 색인 경로를 탑니다.
  - **CVE-2026-119958**: Windows LDAP RCE(CVSS 9.8)입니다.
- [사실] 리눅스 쪽 소식입니다. X.Org Server·XWayland 보안 이슈 8건이 공개됐고, 안정 커널 3종이 동시에 나왔습니다(7절). [20][21]

## 5. CSP

- [사실] **AWS**: Bedrock AgentCore **InvokeWebSearch API**가 GA가 됐습니다. 가격은 쿼리 1,000건당 $7입니다. 6개 리전에서 제공되며 도쿄·시드니는 포함되고 서울은 목록에 없습니다. [16]
- [사실] **Azure**: Azure OpenAI in Foundry를 카타르 중부 리전에서 쓸 수 있게 됐습니다. [17]
- [사실] **GCP**: Arm 뉴스룸에 따르면 TPU 8i Max의 호스트로 Axion(Arm) CPU를 씁니다. [18]
- **Naver Cloud**: 오늘 1차 출처로 확인한 신규 항목은 없습니다.

## 6. 언어·런타임

- [사실] **.NET 11과 C# 15**가 .NET Conf 2026에서 출시됐습니다. JetBrains ReSharper·Rider 2026.3이 출시 당일부터 지원합니다. C# 15에는 union 타입, closed 클래스 계층, 확장 인덱서, 레이블 `break`/`continue`가 들어갑니다. [22][22b]
- [사실] ReSharper 2026.3부터 Visual Studio에서 Junie 외에 Claude Agent와 Codex도 고를 수 있습니다. [22]
- [사실] JetBrains MPS 2026.2가 나왔습니다. MCP API를 재설계했고, Claude Code 기준 토큰 사용량이 50% 넘게 줄었다는 것은 [벤더 주장]입니다. [23]
- [보도] InfoQ에 따르면 Tokio 팀이 Rust 풀스택 프레임워크 **Topcoat** v0.9를 공개했습니다(11-09). 0.x라 장기 안정성은 보장되지 않습니다. [23b]
- [미확인] Python 3.16.0a2는 PEP 일정상 11-10 예정이었습니다. python.org 공지는 확인하지 못했습니다.
- Java/Spring: 11-10~11 날짜의 Spring·OpenJDK 공식 릴리스 공지는 확인하지 못했습니다. Spring Framework 7.1.0-RC2는 11-05로 범위 밖입니다.

## 7. 인프라·리눅스

- [사실] Greg Kroah-Hartman이 **7.3.4, 6.18.63, 6.12.117** 안정 커널을 릴리스했습니다(11-10). 각각 1,250개·860개·1,530개 이상의 패치가 들어 있고, 공지에는 "해당 시리즈 사용자는 반드시 업그레이드"라고 적혀 있습니다. [20]
- [사실] SUSE가 **SLES for NVIDIA 16.1**을 소개했습니다(블로그 11-10, 출시 11-04). Arm 기반 NVIDIA 플랫폼(Vera Rubin, Grace Blackwell)용 OS 스트림입니다. 지원 기간은 2년이며, 표준 SLES 16.2로 제자리 전환하는 경로가 있습니다. [21b]
- [추론] 7.3이 2026 LTS로 예정돼 있어(11-02 메일링리스트 발언, 2차 보도 기준) 7.3.y 업데이트는 내년 BSP·배포판 기준선과 직결됩니다.

## 9. AI 안전

- [보도] Yahoo Finance는 Anthropic의 정정 증권신고서를 인용해 보도했습니다. [5]
  - 신고서 문구는 "We made a determination that we have met this threshold."입니다.
  - 해당 임계치는 RSP의 **AI R&D 임계치**("극적으로 가속된 진보")입니다.
  - 11-02 S-1/A에서는 "곧 충족할 수 있다(may imminently meet)"는 표현이었습니다.
  - 보도에 따르면 이 판단은 현재 관측이 아니라, 앞으로 나올 모델과 전반적 진보 속도에 근거합니다. 임계치를 넘은 결과는 개발 중단이 아니라 추가 안전장치입니다.
- [미확인] SEC 원문(EDGAR)은 필자가 직접 열람하지 않았습니다. 정확한 문맥은 원문으로 확인하시기 바랍니다.
- [추론] IPO 직전에 임계치 충족을 공시한 것은 투자 위험 요소이기도 합니다. 동시에 RSP를 실제 공시 의무와 연결한 첫 사례라는 점에서 의미가 있습니다.

## 10. MCP

- [사실] 12-15 사양 릴리스 계획 페이지의 상태는 11-10과 같습니다. 여전히 **NOT READY**이고 SEP는 0건이며, RC 목표일은 11-15(나흘 뒤)입니다. 오늘 새 진전은 없습니다.
- [사실] JetBrains MPS 2026.2는 MCP 도구 설계 원칙을 공개했습니다(6절). 일괄 작업, 요약 응답, 큰 결과는 파일로 내보내기, fail-fast 검증이 핵심입니다. MCP 서버를 만드는 쪽에 바로 참고가 됩니다. [23]
- KubeCon 세션 목록에 "Envoy AI Gateway + Kyverno로 MCP 트래픽 거버넌스" 세션이 있습니다. 세션 목록 기준이며 내용은 미확인입니다.

## 11. MLOps·피처 스토어

- [사실] **Kubeflow가 CNCF 졸업** 프로젝트가 됐습니다. **llm-d 1.0**도 나왔습니다. [8][11]
- [보도] 테크수다 주간 정리가 메타의 F3 Lightning(광고 ML 피처 배포)을 소개했지만, 원문은 11-03자라 오늘 범위 밖입니다.
- MLflow·Feast: 오늘 1차 출처로 확인한 신규 항목은 없습니다.

## 12. 에이전트 관측성

- 오늘 OpenTelemetry GenAI semantic conventions 관련 1차 출처의 신규 항목은 없습니다.
- [사실] 토스는 하네스와 무관한 **공통 실행 기록**을 따로 두는 설계를 소개했습니다. 하네스 자체 세션 상태와 분리하며, 이력 조회와 하네스 간 요약 인계에 씁니다. 에이전트 관측성 계층을 어디에 두는지에 대한 실제 사례입니다. [24]

## 13. 그린 컴퓨팅

- 오늘 1차 출처로 확인한 신규 항목은 없습니다.

## 14. 국내 기업 기술블로그 (네카라쿠배당토 + 두나무)

| 회사 | 제목 | 날짜 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| 토스 | 실행은 격리하고, 세션은 이어간다: 망분리 환경의 Agent Platform 설계기 | 2026-11-10 | 전자금융감독규정의 망분리 환경에서 동작하는 에이전트 플랫폼 설계기입니다. 격리는 OpenSandbox가 K8s에 Workspace별 Pod를 만들고, 그 안에서 bubblewrap으로 파일·네트워크를 제한합니다. 도구 호출 시 인증정보는 하네스에 넘기지 않습니다. 작업 파일·세션 상태는 PV에 둬 Pod 교체 후에도 작업을 이어갑니다. | [toss.tech](https://toss.tech/article/agent-platform-foundation) |
| 우아한형제들 | 비가 오면 사장님이 먼저 압니다: SSE로 만든 실시간 기상악화 알림 | 2026-11-10 | 폭우 등 기상악화를 사장님에게 SSE로 실시간 알리고, 그 연결을 관리한 기록입니다. 목록 페이지 요약 기준입니다. | [techblog.woowahan.com](https://techblog.woowahan.com/) |
| 카카오(카카오워크) | 서비스 장애 안내 | 2026-11-10 | 15:50–16:30 KST, 약 40분 동안 로그인·메시지 장애가 있었고 메일은 영향이 없었습니다. 추정 원인은 DB 시스템 간 연결 오류입니다. 기술블로그가 아닌 공식 공지입니다. | [blog.kakaowork.com/297](https://blog.kakaowork.com/297) |
| 카카오(카카오클라우드) | 서비스 공지 | 2026-11-09 | 18:31–18:49 kr-central-2 AZ-b의 Block Storage·VM·Managed Service에서 지연이 발생했습니다. | [kakaocloud.com](https://www.kakaocloud.com/more/notices/2114) |

- 네이버 D2, LINE, 쿠팡, 당근, 두나무: 11-10~11 날짜의 신규 글은 확인하지 못했습니다.
- 참고(범위 밖): 카카오페이 기술블로그의 최신 글은 11-06 "if(kakao)26에서 확인한 AI의 변화"입니다.

## 15. Java/Spring 프리랜서 공고 (수집일 2026-11-11, 위시켓)

| 플랫폼 | 공고 | 스택 | 형태 | 금액 | 링크 |
| --- | --- | --- | --- | --- | --- |
| 위시켓 | **[신규]** Java/Spring 기반 계정계 여신(대출) 분석·설계 및 개발 (11-10 등록, 마감 11-24) | Java, Spring (C/Unix 레거시 → Java 전환) | 상주, 840일, 서울 마포 | 중급(7–9년) 월 650만원 / 고급(10–25년) 월 750만원 | [159571](https://project.wishket.com/project/159571/) |
| 위시켓 | 11-10 브리핑 게재 공고 (마감 11-23) | Java/Spring | 상주 | 월 600만원 | [159547](https://project.wishket.com/project/159547/) |
| 위시켓 | 11-10 브리핑 게재 공고 (마감 11-16) | Java/Spring | 상주 | 월 550만원 | [159408](https://project.wishket.com/project/159408/) |
| 위시켓 | 11-10 브리핑 게재 공고 (마감 11-13, 임박) | Java/Spring | 상주 | 월 500만원 | [159210](https://project.wishket.com/project/159210/) |

- 위 공고들은 공개 페이지의 마감 카운트다운 기준으로 모집 중입니다. 실제 지원 가능 여부는 각 링크에서 확인하시기 바랍니다.
- 위시켓 사이드바에 "카드사 차세대 시스템 구축 API 연동 개발"(월 650만원, 180일, 2027-01-04 시작)이 보였지만, 공고 URL을 확인하지 못해 표에서 뺐습니다. **모집 상태 미확인**입니다.
- 프리모아·이랜서는 오늘 확인하지 못했습니다. 로그인이 필요한 정보는 수집하지 않았습니다.

## 8. (특집) Jev API와 의사결정 모델

- [사실] 공식 changelog의 마지막 항목은 여전히 **Jev 1.14(10-14)**입니다. 오늘 새 릴리스는 없습니다. [19]
- [사실] 1.14의 주요 변경을 다시 정리합니다. [19]
  - 이미지 안에서 대상의 위치를 바운딩 박스로 답하는 Box 질문 유형이 추가됐습니다.
  - `state`·`instructions`·`criteria`에 이미지를 넣을 수 있습니다.
  - long-context 헤더를 보내면 컨텍스트 한도가 262k 토큰으로 늘어납니다.
- [추론] 오늘 소식 가운데 의사결정 모델 설계에 시사점이 있는 것은 토스 Agent Platform의 **"세션 상태와 공통 기록의 분리"**입니다. Jev처럼 `state`·`criteria`를 요청마다 명시하는 의사결정 API를 에이전트에 붙일 때는 다음처럼 나눠 두면 재현과 감사가 쉬워집니다.
  1. 판단에 쓴 `criteria`와 결정 결과는 하네스와 무관한 공통 기록에 남깁니다.
  2. 대화 맥락은 하네스 세션 상태로 따로 보관합니다.
  3. 하네스를 바꿀 때는 공통 기록의 요약만 넘깁니다.

---

## 사실 · 추론 · 미확인 정리

- **사실(1차·공식)**
  - Anthropic 로드쇼 조건(주식 수, 밴드, 티커)
  - CNCF Sandbox 5종, llm-d 1.0, Kubeflow 졸업
  - CISA KEV 6건
  - AgentCore InvokeWebSearch GA와 가격
  - 안정 커널 3종
  - .NET 11 출시(JetBrains 공지 기준)
  - 토스·우아한형제들 신규 글
  - 위시켓 159571
  - Jev 1.14가 최신이라는 점
- **보도**
  - IPO 가격 결정·상장 일정과 기업가치
  - RSP AI R&D 임계치 충족 공시
  - Claude Meetings 등 제품 발표
  - Patch Tuesday 건수와 제로클릭 취약점 상세
- **벤더 주장**
  - Agent Substrate의 "10배 밀도"
  - GKE TPU dynamic slicing의 "최대 5배"
  - MPS의 "토큰 50% 이상 절감"
  - 중립 제3자 재현은 모두 부재합니다.
- **추론**
  - KubeCon의 축이 "에이전트 격리"라는 해석
  - RSP 공시의 의미
  - Jev 연동 설계 제안
- **미확인**
  - Claude 제품 발표의 anthropic.com 1차 게시물
  - SEC 원문 문맥
  - Python 3.16.0a2 실제 릴리스
  - npm LangGraph 1.7.3
  - 카드사 차세대 공고의 URL과 상태

## References

1. Anthropic, Anthropic launches roadshow for proposed initial public offering (2026-11-10). <https://www.anthropic.com/news/roadshow-launch>
2. CNBC, Anthropic sets price range of $70 to $78 in upcoming IPO (2026-11-10). <https://www.cnbc.com/2026/11/10/anthropic-sets-price-range-of-70-to-78-in-upcoming-ipo.html>
3. TechCrunch, Anthropic sets IPO price range of $70 to $78 per share (2026-11-10). <https://techcrunch.com/2026/11/10/anthropic-sets-ipo-price-range-of-70-to-78-per-share-to-reach-an-implied-valuation-of-1-404-trillion/>
4. TechCrunch, Anthropic launches Claude Meetings (2026-11-10). <https://techcrunch.com/2026/11/10/anthropic-launches-claude-meetings-to-turn-workplace-discussions-into-plans-and-tasks/>
   - 4b. Axios, Anthropic Claude Meetings and knowledge work (2026-11-10). <https://www.axios.com/2026/11/10/anthropic-claude-meetings-knowledge-work>
5. Yahoo Finance, Anthropic says a key AI safety alarm has been triggered days before its IPO (2026-11-10). <https://finance.yahoo.com/markets/article/anthropic-says-a-key-ai-safety-alarm-has-been-triggered-days-before-its-ipo-171519615.html>
6. Google, Gemini 4 Carbon for developers (2026-11-10). <https://blog.google/innovation-and-ai/technology/developers-tools/gemini-4-carbon-developers/>
7. Google Cloud, Gemini for healthcare (2026-11-10). <https://cloud.google.com/blog/products/ai-machine-learning/gemini-for-healthcare>
8. CNCF, CNCF hits major milestones … new generation of projects to build AI systems in production (2026-11-10). <https://www.cncf.io/announcements/2026/11/10/cncf-hits-major-milestones-with-global-community-growth-record-industry-investment-and-a-new-generation-of-projects-to-build-ai-systems-in-production/>
9. Cognition, Devin CLI stable changelog (2026-11-09). <https://docs.devin.ai/cli/changelog/stable>
10. NVIDIA, Agent Substrate: Advancing Kubernetes for Agents at Scale (2026-11-10). <https://developer.nvidia.com/blog/agent-substrate-advancing-kubernetes-for-agents-at-scale/>
11. Google Cloud, The open AI-native stack on Kubernetes (2026-11-10). <https://cloud.google.com/blog/topics/developers-practitioners/the-open-ai-native-stack-on-kubernetes-from-open-models-to-distributed-inference-and-agents/>
    - 11b. AWS, AWS Nitro Sandboxes: hardware-enforced workload isolation on Amazon EKS (2026-11-09). <https://aws.amazon.com/blogs/containers/aws-nitro-sandboxes-hardware-enforced-workload-isolation-on-amazon-eks/>
    - 11c. Google Cloud, GKE dynamic slicing on TPUs (2026-11-09). <https://cloud.google.com/blog/products/containers-kubernetes/gke-dynamic-slicing-on-tpus>
12. BleepingComputer, Microsoft November 2026 Patch Tuesday (2026-11-10). <https://www.bleepingcomputer.com/news/microsoft/microsoft-november-2026-patch-tuesday-fixes-1-235-flaws-outlook-zero-day/>
13. CISA, CISA Adds Six Known Exploited Vulnerabilities to Catalog (2026-11-10). <https://www.cisa.gov/news-events/alerts/2026/11/10/cisa-adds-six-known-exploited-vulnerabilities-catalog>
14. Tenable, Microsoft's November 2026 Patch Tuesday addresses 1,093 CVEs (2026-11-10). <https://www.tenable.com/blog/microsoft-november-2026-patch-tuesday-addresses-1093-cves-cve-2026-124194>
15. The Register, November Patch Tuesday boasts over 1,000 bugs but only one zero-day so far (2026-11-10). <https://www.theregister.com/security/2026/11/10/november-patch-tuesday-boasts-over-1000-bugs-but-only-one-zero-day-so-far/5308946>
16. AWS, Amazon Bedrock AgentCore Web Search API (2026-11-10). <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-bedrock-agentcore-web-search-api/>
17. Microsoft, Azure OpenAI Service in Foundry in Qatar (2026-11-10). <https://news.microsoft.com/source/emea/2026/11/microsoft-and-qatars-ministry-of-communications-and-information-technology-mark-availability-of-azure-openai-service-in-foundry-in-qatar-at-mwc26-doha/>
18. Arm, Google expands AI infrastructure on Arm with TPU 8i Max (2026-11-10). <https://newsroom.arm.com/news/google-expands-ai-infrastructure-on-arm-with-tpu-8i-max>
19. Typesafe AI, Jev Model changelog (확인 2026-11-11). <https://docs.typesafe.ai/changelog>
20. LWN, Three new stable kernels for Tuesday (2026-11-10). <https://lwn.net/Articles/1106569/>
21. Phoronix, Recent Linux news — X.Org Server/XWayland security issues (2026-11-10). <https://www.phoronix.com/recent-linux-news>
    - 21b. SUSE, Introducing SUSE Linux Enterprise Server for NVIDIA (2026-11-10). <https://www.suse.com/blog/introducing-suse-linux-enterprise-server-for-nvidia/>
22. JetBrains, ReSharper 2026.3: Claude Agent and Codex in Visual Studio, .NET 11 and C# 15 Support (2026-11-10). <https://blog.jetbrains.com/dotnet/2026/11/10/resharper-2026-3-release/>
    - 22b. JetBrains, Rider 2026.3: .NET 11 Support and JetBrains Air (2026-11-10). <https://blog.jetbrains.com/dotnet/2026/11/10/rider-2026-3-release/>
23. JetBrains, MPS 2026.2 Has Been Released (2026-11-10). <https://blog.jetbrains.com/mps/2026/11/mps-2026-2-released/>
    - 23b. InfoQ, Tokio Releases Topcoat (2026-11-09). <https://www.infoq.com/news/2026/11/topcoat-rust-framework/>
24. 토스, 실행은 격리하고, 세션은 이어간다: 망분리 환경의 Agent Platform 설계기 (2026-11-10). <https://toss.tech/article/agent-platform-foundation>
25. 우아한형제들, 비가 오면 사장님이 먼저 압니다: SSE로 만든 실시간 기상악화 알림 (2026-11-10). <https://techblog.woowahan.com/>
26. 카카오워크, 서비스 장애 안내 (2026-11-10). <https://blog.kakaowork.com/297>
27. 카카오클라우드, 서비스 공지 (2026-11-09). <https://www.kakaocloud.com/more/notices/2114>
28. 위시켓, Java/Spring 기반 계정계 여신(대출) 분석·설계 및 개발 (2026-11-10 등록, 수집 2026-11-11). <https://project.wishket.com/project/159571/>
