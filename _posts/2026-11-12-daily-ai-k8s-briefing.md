---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-12"
date: 2026-11-12 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-12 08:30 KST. 수집 대상은 원칙적으로 **2026-11-11 ~ 11-12** 날짜가 원문에서 확인되는 소식입니다. 그보다 오래된 항목은 "배경"으로만 적고 최신으로 다루지 않습니다.
>
> **라벨**: **[사실]** 1차·공식 출처에서 직접 확인 / **[보도]** 언론 보도로만 확인(1차 원문 미확인) / **[벤더 주장]** 벤더 자체 수치·벤치마크(제3자 재현 부재) / **[추론]** 필자 해석 / **[미확인]** 확인하지 못함.
>
> **중복 안내**: [전날(11-11) 브리핑](/2026/11/11/daily-ai-k8s-briefing/)에 실린 소식은 새 진전이 있을 때만 다시 적습니다.

## 오늘의 핵심

- **[사실]** Google이 닫힌 선택지 판단 전용 **Gemini Decisions API**와 `gemini-decision-1` 모델을 공개했습니다(11-11). 특집 섹션(8)에서 Jev와 나란히 놓고 봅니다. [[1]](#ref-1)
- **[사실]** **Node.js 보안 릴리스**(11-11): 26.x·24.x·22.x 대상, High 등급 2건(HTTP/2 원격 abort, HTTPS 메모리 노출) 포함. [[9]](#ref-9)
- **[사실]** **Vite 개발 서버 원격 코드 실행** 권고(GHSA-p4f5-76q4-ffq7, Critical, 11-10 공개). 개발 서버를 네트워크에 노출했다면 즉시 패치 대상입니다. [[10]](#ref-10)
- **[사실]** MCP가 **6개월 릴리스 주기**를 공식화했습니다(11-11). 다음 사양 목표일은 2027-03-30. [[21]](#ref-21)
- **[사실]** AWS가 로컬 개발용 **AWS Emulator**를 정식 공개했고, 이것을 자율 에이전트 팀이 만들었다고 밝혔습니다(11-11). [[14]](#ref-14) [[7]](#ref-7)
- **[사실]** 위시켓에 11-11 등록된 Java/Spring 기간제 공고 4건을 원문에서 확인했습니다(섹션 15).

---

## 1. AI & ML

**Gemini Decisions API — "생성"이 아닌 "판단" 전용 엔드포인트** (Google, 11-11)

- **[사실]** 멀티모달 입력 하나(텍스트·이미지·오디오·비디오·PDF, 최대 256K 토큰)에 독립 질문을 최대 1,000개까지 붙여 한 번에 판단을 받는 API입니다. 질문 유형은 예/아니오, 2~255개 선택지 중 택일, 순서형 루브릭 점수의 세 가지이고, 응답은 확률과 0~1 신뢰도로 돌아옵니다. [[1]](#ref-1)
- **[벤더 주장]** 지연 150~250ms, 입력 100만 토큰당 $0.10·출력 과금 없음. Google 자체 발표 수치이며 제3자 재현 결과는 **부재**합니다. [[1]](#ref-1)
- **[미확인]** 개발자 문서 페이지는 수집 시점에 응답 시간 초과로 열지 못했습니다. 세부 스키마는 블로그 글 기준입니다.

**Claude 관련 후속 보도** (11-11)

- **[보도]** Computerworld는 전날 다룬 Claude Meetings가 Team 플랜에서 기본 활성화되고, 인터랙티브 커넥터가 대화 안에서 서드파티 앱 전체 화면을 여는 방식이라고 전했습니다. [[2]](#ref-2)
- **[보도]** TechTarget은 Fable/Mythos 5.2 가격을 입력 $8·출력 $40(100만 토큰당)로, 5.1의 $10·$50보다 낮게 보도했습니다. Anthropic 공식 가격 페이지에서 직접 대조하지 못했으므로 보도로만 적습니다. [[3]](#ref-3)
- **[보도]** The Decoder는 Anthropic 공동창업자 발언을 인용해, Claude가 주요 칩 계열 네 종 모두에서 학습·서빙되며 AMD GPU로의 커널 이식을 3일 만에 마쳤다고 전했습니다. "3일"은 **[벤더 주장]** 입니다. [[4]](#ref-4)

**뇌-컴퓨터 인터페이스**

- **[사실]** Luo 외, "Self-paced silent speech brain-computer interface for device control", *Communications Biology*, 2026-11-11 게재. ALS 참가자가 시각 단서 없이 소리 내지 않는 발화만으로 스마트홈 기기를 제어한 ECoG 기반 BCI 연구입니다. [[5]](#ref-5)
- **[미확인]** 제3자 요약에 도는 정확도 수치는 논문 본문에서 직접 대조하지 못해 싣지 않습니다.

## 2. AI 에이전트 프레임워크

- **[사실]** **A2UI 1.0** (Google, 11-11): 에이전트가 UI를 선언적으로 생성하는 프로토콜의 첫 안정 버전. 양방향 함수 호출·접근성·확장 기능이 들어갔고, 렌더러는 React·Angular·Lit·Flutter가 1.0, SwiftUI·Compose는 v0.9.1입니다. 웹·Flutter 렌더러는 MCP Apps 안에서도 동작한다고 밝혔습니다. [[6]](#ref-6)
- **[사실]** **AWS Emulator 제작 과정** (Amazon, 11-11): 테스트 작성·문제 탐지·수정을 맡는 세 에이전트 팀이 머지 게이트를 통과한 코드만 합치는 구조로 100% 자율 개발했다고 설명했습니다. [[7]](#ref-7) "100%"는 **[벤더 주장]** 으로 읽는 것이 안전합니다.
- **[사실]** LangGraph·CrewAI·Devin CLI는 11-11~12 날짜의 새 릴리스를 확인하지 못했습니다(전날 브리핑의 1.2.20 / 1.15.39 / v3000.12.43이 여전히 최신).

## 3. Kubernetes & Cloud Native

- **[사실]** **EKS Auto Mode가 Pod 단위 보안 그룹 지원** (AWS, 11-11): Kubernetes 1.36 이상에서 `SecurityGroupPolicy`로 Pod별 보안 그룹을 지정합니다. [[8]](#ref-8)
- **[사실]** **CNCF 발표** (11-11): Meta가 End User Case Study Contest에서 수상(Argo CD + Kargo로 100개 클러스터 배포를 시간 단위에서 분 단위로 단축했다는 사례), Adyen이 Platinum End User Member로 합류. [[16]](#ref-16)
- **[사실]** **v1.38 일정**: 코드 프리즈가 11-16(AoE)로 나흘 남았고, 정식 릴리스 목표는 12-16입니다. [[17]](#ref-17) 기능 게이트 승격을 노리는 기여자라면 이번 주가 마감입니다.
- **배경(11-10, 최신 아님)**: Microsoft가 KubeCon NA에 맞춰 AKS 관리형 DRA(GPU)·DRANET, Fleet Manager 드리프트 감지 GA, AI Runway의 CNCF Sandbox 수락을 정리해 발표했습니다. [[18]](#ref-18) 전날 브리핑에서 CNCF 쪽 발표로 다룬 범위와 일부 겹칩니다.
- **[보도]** SiliconANGLE은 Broadcom이 Workload Conformance 워킹그룹 공동 의장을 맡고 VM API를 CNCF에 기여했다고 전했습니다. CNCF 공식 발표문에서 직접 확인하지 못했습니다.
- **가이드라인 메모 [추론]**: v1.37에서 HPA scale-to-zero가 베타, DRA Extended Resource가 GA가 된 상태이므로, 1.36에 머무는 클러스터는 1.38 릴리스(12-16) 전에 1.37 업그레이드 경로를 먼저 검증해 두는 편이 한 번에 두 단계를 건너뛰는 것보다 안전합니다.

## 4. 사이버보안

- **[사실]** **Node.js 11월 보안 릴리스** (11-11): [[9]](#ref-9)
  - CVE-2026-123863 (High) — `~Http2Session`의 도달 가능한 assertion으로 원격에서 프로세스를 중단시킬 수 있음. 24.x·26.x 영향.
  - CVE-2026-123864 (High) — HTTPS에서 길이 0 TLS write 재진입으로 UAF/힙 범위 밖 읽기가 발생, 다른 연결의 메모리가 노출될 수 있음.
  - llhttp·undici·sqlite 의존성 갱신 포함.
- **[사실]** **Vite GHSA-p4f5-76q4-ffq7** (Critical, 11-10 공개): `--host` 또는 `server.host`로 개발 서버를 네트워크에 노출한 경우 원격 코드 실행. 4.0.0 이상 영향, 수정 버전 8.3.7 / 8.2.5 / 8.1.7 / 7.3.8 / 6.4.6. [[10]](#ref-10)
- **[보도]** **KEV 후속**: 전날 다룬 CISA KEV 추가 건 가운데 Barracuda 두 취약점(CVE-2026-116606, CVE-2026-111560)은 체인으로 root 권한까지 이어지며 연방기관 조치 기한이 11-13이라고 SecurityWeek가 전했습니다. [[11]](#ref-11)
- **[보도]** Cisco BroadWorks CVE-2026-20320은 탈옥된 LLM을 쓴 에이전트형 공격 캠페인에서 악용됐다고 BleepingComputer·SecurityWeek가 보안 업체 분석을 인용해 보도했습니다. 귀속·피해 규모는 단일 업체 분석에 의존하므로 **[미확인]** 으로 둡니다. [[12]](#ref-12) [[13]](#ref-13)
- **[사실]** CISA 권고 페이지에는 수집 시점까지 11-10 이후 새 경보가 없었습니다.
- **아이덴티티 보안 [추론]**: Node.js CVE-2026-123864는 "다른 연결의 메모리"가 새는 유형이라, 세션 토큰·Authorization 헤더가 같은 프로세스 메모리에 있는 API 게이트웨이·BFF가 우선 패치 대상입니다. 패치 후 장기 토큰 회전 여부는 노출 구간을 보고 판단하십시오.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

- **AWS [사실]** (11-11)
  - **AWS Emulator** 정식 공개: 인메모리 로컬 에뮬레이터, 미지원 오퍼레이션은 501 반환, CC0 라이선스, 별도 요금 없음. [[14]](#ref-14)
  - **Lambda MicroVMs x86 지원**. [[15]](#ref-15)
  - EKS Auto Mode의 Pod 보안 그룹(섹션 3). [[8]](#ref-8)
- **GCP [사실]** (11-11): Professional Agentic Architect 자격증 신설. [[19]](#ref-19)
- **Azure**: 11-11~12 날짜의 신규 공식 발표는 확인하지 못했습니다. 11-10 KubeCon 정리 글은 섹션 3 배경 참조.
- **Naver Cloud [미확인]**: 해당 기간 공식 공지를 확인하지 못했습니다.

## 6. 프로그래밍 언어

- **Python [사실]**: 전날 [미확인]으로 남겼던 **3.16.0a2**가 11-10 릴리스로 python.org에서 확인됐습니다. `re`의 중첩 집합·집합 연산·유니코드 속성, 시작 속도 개선, C 구현 `uuid4`/`uuid7`, OpenSSL 4.0 이상에서 `ssl`의 ECH 지원. 다음 알파(a3)는 12-15 예정. [[20]](#ref-20) `uuid` 속도 배수는 마이크로벤치마크 기준 **[벤더 주장]** 이라 수치는 생략합니다.
- **JavaScript/Node.js [사실]**: 섹션 4의 보안 릴리스 참조. [[9]](#ref-9)
- **Vite [사실]**: 섹션 4의 보안 권고 참조. [[10]](#ref-10)
- **Angular [보도]**: InfoQ가 Rust/Oxc 기반 전처리기 `ngp` 베타를 보도했습니다(11-11). Angular 공식 블로그 원문은 대조하지 못했습니다.
- **Rust [미확인]**: 1.100.0 안정판이 11-12 예정이라는 2차 정보가 있으나, 수집 시점에 공식 블로그 공지는 없었습니다. 11-11 공식 블로그 글은 GSoC 2026 결과 정리였습니다.
- **Java/Spring [사실]**: 11-11~12 날짜의 릴리스 공지 없음(11-10에 Spring for Apache Pulsar 이관 공지, This Week in Spring).
- **Kotlin · React · Vue · TypeScript**: 해당 기간 공식 릴리스를 확인하지 못했습니다.

## 7. 인프라 & Linux

- **[사실]** kernel.org 기준 11-10 이후 새 안정 커널은 없습니다. 메인라인은 7.4-rc2(11-08), linux-next는 `next-20261111`.
- **[보도] 정정 메모**: 전날 브리핑에서 "7.3이 올해 LTS가 될 가능성"을 [추론]으로 적었으나, Phoronix는 7.4가 2026년 LTS가 될 공산이 크다고 보도했습니다. 공식 지정 전이므로 둘 다 확정이 아니며, 전날의 추론은 근거가 약했습니다.

## 9. AI Safety & Alignment

둘 다 11-10 게재라 "배경"에 가깝지만 전날 브리핑에 싣지 못해 여기 적습니다.

- **[사실]** OpenAI Alignment 블로그, "What affects chain-of-thought monitorability across the model lifecycle?": 사전학습이 진행될수록 CoT 없이 푸는 능력이 완만히 오르고, RL 단계에서 CoT 통제 가능성이 올라가며, 이 성질이 모델 생성 데이터로의 SFT를 통해 전이된다고 보고했습니다. 저자들은 모델이 CoT로 감시하기 점점 어려워지고 있다고 정리합니다. [[23]](#ref-23)
- **[사실]** Anthropic Alignment 블로그, "Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect": 오염 데이터만으로 파인튜닝하면 오정렬 비율이 미학습 수준(약 7%)인데, 오염 20% 혼합에서는 접종(inoculation) 프롬프트 하에 16%까지 올랐다고 보고했습니다. 데이터를 **단독으로** 감사하는 방식의 한계를 시사합니다. [[24]](#ref-24)
- **[추론]** 두 결과 모두 "부분만 떼어 보면 안전해 보인다"는 공통 구조입니다. 파인튜닝 데이터 검수와 추론 과정 모니터링을 각각의 단독 게이트로 두는 설계는 재검토 대상입니다.

## 10. MCP 생태계

- **[사실]** **"A More Predictable Release Cycle for MCP"** (11-11): 사양 릴리스를 6개월 주기(3월·9월 마지막 화요일)로 고정. 다음 목표는 2027-03-30(`2027-03-30`). Release Manager 역할 신설, 일정은 계획 −8개월 → 리뷰 −6개월 → 소프트 프리즈 −2.5개월 → Tier-1 SDK 베타 −1.5개월 → 하드 프리즈 −1개월. [[21]](#ref-21)
- **[미확인]** 전날 브리핑에 적은 "12-15 사양 릴리스 계획"이 이 주기로 대체됐는지는 글에 언급이 없어 확인하지 못했습니다.
- **배경(11-10)**: 파일 업로드·다운로드용 실험 확장 `io.modelcontextprotocol/files` 탐색 글. 레퍼런스 구현은 아직 없고 연말 안정화를 목표로 한다고 밝혔습니다. [[22]](#ref-22)
- **[사실]** A2UI 1.0 렌더러의 MCP Apps 내 동작(섹션 2), Jaeger의 옵트인 MCP 엔드포인트(섹션 12).

## 11. MLOps · Feature Store

- **[사실]** 11-11~12 날짜의 신규 릴리스·공지를 확인하지 못했습니다. 참고로 MLflow 최근 릴리스는 3.18.0(11-02), Feast 블로그 최근 글은 10-05로 모두 수집 범위 밖입니다.

## 12. 에이전트 옵저버빌리티

- **배경(11-10) [사실]**: CNCF 블로그가 Jaeger v2.22의 미리보기 기능을 소개했습니다 — Ask Jaeger 어시스턴트, 도구 9개를 노출하는 옵트인 MCP 엔드포인트, 오류 근본원인·N+1 진단 스킬, OpenTelemetry GenAI 시맨틱 컨벤션 기반 트레이스 시각화. [[25]](#ref-25)
- 11-11~12 날짜의 신규 소식은 확인하지 못했습니다.

## 13. 그린 컴퓨팅

- **[사실]** BloombergNEF 보고서(11-11): 데이터센터 전력 수요가 2035년 2,354 TWh(세계 전력의 7%)로 약 4배 늘 것으로 전망. 발표된 온사이트 가스 발전 181 GW 중 90% 이상이 미국이며, 전부 지어질 경우 연 약 345 MtCO2e 배출로 추정했습니다. [[26]](#ref-26) 전망치이므로 모델 가정에 의존합니다.
- **[사실]** Nature Spotlight, "AI's energy paradox"(11-11). [[27]](#ref-27)

## 14. 국내 기업 기술 블로그

공개 RSS·목록 페이지 기준입니다.

| 회사 | 제목 | 게시일 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| 네이버 (D2) | Chaos Mesh로 Kubernetes 앱의 장애 내구성 검증하기 | **미확인** (피드 갱신 11-11) | 제목 기준 Chaos Mesh 기반 장애 주입 검증 | [원문](https://d2.naver.com/helloworld/6523094) |
| 네이버 (D2) | Socket.IO 서버를 여러 Pod에서 운영하기 | **미확인** (피드 갱신 11-11) | 제목 기준 다중 Pod 환경 Socket.IO 운영 | [원문](https://d2.naver.com/helloworld/3517874) |
| 토스 | TASTE, 토스의 추천 파운데이션 플랫폼 | 2026-11-09 (RSS) | 추천 파운데이션 플랫폼 소개. 최신 아님(배경) | [원문](https://toss.tech/article/taste) |

- **[미확인] D2 주의**: D2 피드에서 글 여러 편의 `updated` 시각이 11-11 같은 시간대에 몰려 있고 본문 끝에 채널 이전 공지가 공통으로 붙어 있습니다. 일괄 수정으로 보이며 **[추론]**, 최초 게시일은 확인하지 못했습니다. 신규 글로 단정하지 않습니다. 요약도 본문 정독이 아닌 제목 기준입니다.
- **[사실]** 토스 RSS 최신 글은 전날 다룬 Agent Platform 설계기(11-10)이고 이후 새 글 없음. 우아한형제들도 11-10 SSE 글 이후 새 글 없음.
- **[사실]** LINE(LY) 한국어 블로그 RSS 최신은 11-06, 당근 테크 블로그 RSS 최신은 11-03입니다(수집 범위 밖).
- **[미확인]** 카카오(tech.kakao.com)는 목록이 비어 보였고, 쿠팡 엔지니어링 피드는 오래된 글만 반환했으며, 두나무 기술 블로그는 접근 오류로 확인하지 못했습니다.

## 15. Java/Spring 프리랜서 공고

**수집일**: 2026-11-12. 모두 위시켓 **원문 상세 페이지**에서 등록일·마감일·"모집 중" 표시를 직접 확인한 공고입니다. 업무 상세·모집 요건은 로그인 뒤에만 보여 수집하지 않았습니다.

| 플랫폼 | 공고명 | 기술 스택 | 계약·근무 형태 | 금액 | 등록 / 마감 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | Java/Spring 기반 대외 여신(대출) 및 대외 보증·정산 연계 개발 | Java, Spring | 기간제 상주, 840일, 서울 마포 | 미드(7~9년) 월 650만원 / 시니어(10년 이상) 월 750만원 | 11-11 / 11-25 | [159582](https://project.wishket.com/project/159582/) |
| 위시켓 | AWS/Java Spring Boot 기반 서비스 인프라 이관 DevOps·백엔드 개발 | AWS, Java, Spring Boot | 기간제 상주, 120일, 서울 성동 | 시니어(7~10년) 월 800만원 | 11-11 / 11-25 | [159587](https://project.wishket.com/project/159587/) |
| 위시켓 | Java/React 기반 반도체 자산관리 시스템 개발 | Java, React | 기간제 상주, 180일, 경기 이천 | 시니어(11년 이상) 월 750만원 | 11-11 / 11-25 | [159572](https://project.wishket.com/project/159572/) |
| 위시켓 | Java/Spring Boot 기반 금융사 모바일 앱 차세대 구축 백엔드 개발 | Java, Spring Boot | 기간제 상주, 30일, 서울 영등포 | 미드(2~5년) 월 500만원 | 11-11 / 11-25 | [159586](https://project.wishket.com/project/159586/) |
| 위시켓 | Java/Spring Boot 기반 생명보험 신계약 시스템 개발 | Java, Spring, JSP | 기간제 상주, 90일, 서울 종로 | 월 600만원 | 11-09 / 11-23 | [159547](https://project.wishket.com/project/159547/) |

- 위 다섯 번째(159547)는 **전날 브리핑에도 실린 기존 공고**이며 신규가 아닙니다. 여전히 모집 중임을 재확인해 유지했습니다.
- **전날 공고 상태 변화 [사실]**: 159571은 상세 페이지에 "모집 마감일 2026.11.11."만 표시되고 남은 기간 표시가 없습니다 — 마감된 것으로 보입니다 **[추론]**. 159408(마감 11-16), 159210(마감 11-13, 임박)은 모집 중 표시를 유지했습니다.
- **프리모아·이랜서 [미확인]**: 프리모아는 연결 오류, 이랜서는 빈 응답으로 공고를 확인하지 못했습니다. 검색 요약만으로는 싣지 않습니다.
- 금액은 플랫폼에 표시된 "예상 금액"이며 실제 계약 조건과 다를 수 있습니다.

---

## 8. 특집 — Jev API와 판단(Decision) 모델

- **[사실]** Jev 변경 이력의 최신 항목은 여전히 1.14(10-14)이며, 11-11~12 날짜의 새 항목은 없습니다. [[28]](#ref-28)
- **[사실]** 이번 주의 변화는 Jev 바깥에서 왔습니다. Google의 **Gemini Decisions API**(섹션 1)는 "자유 생성"이 아니라 닫힌 집합 위의 판단을 확률·신뢰도와 함께 돌려주는 전용 엔드포인트입니다. LangChain·LiteLLM·Pydantic AI 등과의 연동을 순차 제공한다고 밝혔습니다. [[1]](#ref-1)
- **[추론]** 판단 모델을 고를 때 볼 지점은 세 가지입니다.
  1. **보정(calibration)**: 반환되는 확률이 실제 정답률과 맞는가. 벤더가 내놓는 신뢰도 값은 자체 평가 세트에서만 검증하면 순환 검증이 되므로, 자기 도메인의 라벨 데이터로 신뢰도 구간별 정답률을 직접 재야 합니다.
  2. **질문 간 독립성**: 한 입력에 질문 수백 개를 묶으면 비용은 줄지만, 질문 순서·조합이 결과에 영향을 주는지는 별도로 확인해야 합니다. Google은 "독립 질문"이라고 설명하지만 제3자 검증은 **부재**합니다.
  3. **가격 구조**: 출력 무과금 구조는 분류·라우팅·가드레일 같은 대량 호출에 유리합니다. 다만 지연·가격 수치는 모두 **[벤더 주장]** 입니다.
- **[미확인]** Jev와 Gemini Decisions의 중립 헤드투헤드 비교는 존재를 확인하지 못했습니다. 우열을 말할 근거는 현재 없습니다.

---

## 사실 · 추론 · 미확인 정리

**사실(1차 출처 확인)**
- Gemini Decisions API 공개와 기능 범위, A2UI 1.0, AWS Emulator·Lambda MicroVMs x86·EKS Auto Mode Pod 보안 그룹
- Node.js 11월 보안 릴리스의 CVE 2건, Vite GHSA-p4f5-76q4-ffq7과 수정 버전
- MCP 6개월 릴리스 주기와 2027-03-30 목표, Python 3.16.0a2 릴리스
- Kubernetes v1.38 코드 프리즈 11-16 / 릴리스 12-16
- OpenAI·Anthropic 정렬 연구 2건, BloombergNEF 전망, *Communications Biology* BCI 논문 게재
- 위시켓 공고 5건의 등록일·마감일·금액·모집 중 표시

**추론(필자 해석)**
- Node.js 메모리 노출 건의 우선 패치 대상, 1.37 선행 업그레이드 권고
- 정렬 연구 두 건의 공통 시사점, 판단 모델 선정 기준
- D2 피드 갱신이 일괄 수정이라는 해석, 위시켓 159571의 마감 판단

**미확인**
- Gemini Decisions 개발자 문서 세부, Jev와의 중립 비교
- Fable/Mythos 5.2 가격·Claude Meetings 기본값(보도만 존재)
- BroadWorks 악용 캠페인의 귀속·규모, Rust 1.100.0 릴리스 여부
- MCP 12-15 릴리스 계획의 존속 여부
- D2 글의 최초 게시일, 카카오·쿠팡·두나무 블로그 최신 글
- 프리모아·이랜서 공고, Naver Cloud 공지

## References

1. <a id="ref-1"></a>Google, "Gemini Decisions API" (2026-11-11) — <https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/>
2. <a id="ref-2"></a>Computerworld, "Anthropic targets workplace collaboration with Claude Meetings" (2026-11-11, 보도) — <https://www.computerworld.com/article/4247466/anthropic-targets-workplace-collaboration-with-claude-meetings.html>
3. <a id="ref-3"></a>TechTarget, "With IPO looming, Anthropic launches new AI models, workplace tools" (2026-11-11, 보도) — <https://www.techtarget.com/news/with-ipo-looming-anthropic-launches-new-ai-models-workplace-tools/874410/>
4. <a id="ref-4"></a>The Decoder (2026-11-11, 보도) — <https://the-decoder.com/anthropic-says-ai-is-eroding-nvidias-cuda-lead-cutting-an-amd-chip-switch-from-months-to-three-days/>
5. <a id="ref-5"></a>Luo et al., "Self-paced silent speech brain-computer interface for device control", *Communications Biology* (2026-11-11) — <https://www.nature.com/articles/s42003-026-10477-5>
6. <a id="ref-6"></a>Google Developers Blog, "A2UI 1.0" (2026-11-11) — <https://developers.googleblog.com/en/a2ui-10-build-delightful-fast-reliable-agentic-experiences/>
7. <a id="ref-7"></a>Amazon, "How autonomous AI agents built AWS Emulator" (2026-11-11) — <https://www.aboutamazon.com/news/aws/how-autonomous-ai-agents-built-aws-emulator>
8. <a id="ref-8"></a>AWS What's New, "Amazon EKS Auto Mode security groups for Pods" (2026-11-11) — <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-eks-auto-mode-security-groups-for-pods/>
9. <a id="ref-9"></a>Node.js, "November 2026 Security Releases" (2026-11-11) — <https://nodejs.org/en/blog/vulnerability/november-2026-security-releases>
10. <a id="ref-10"></a>Vite Security Advisory GHSA-p4f5-76q4-ffq7 (2026-11-10) — <https://github.com/vitejs/vite/security/advisories/GHSA-p4f5-76q4-ffq7>
11. <a id="ref-11"></a>SecurityWeek, "Recently Patched Barracuda Vulnerabilities Exploited in Attacks" (보도) — <https://www.securityweek.com/recently-patched-barracuda-vulnerabilities-exploited-in-attacks/>
12. <a id="ref-12"></a>BleepingComputer, "CISA flags Cisco BroadWorks flaw as actively exploited in attacks" (보도) — <https://www.bleepingcomputer.com/news/security/cisa-flags-cisco-broadworks-flaw-as-actively-exploited-in-attacks/>
13. <a id="ref-13"></a>SecurityWeek, "Threat Actors Exploit Openwave, Cisco BroadWorks Vulnerabilities" (보도) — <https://www.securityweek.com/threat-actors-exploit-openwave-cisco-broadworks-vulnerabilities/>
14. <a id="ref-14"></a>AWS What's New, "AWS Emulator now available" (2026-11-11) — <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-emulator-now-available/>
15. <a id="ref-15"></a>AWS What's New, "AWS Lambda MicroVMs x86 architecture" (2026-11-11) — <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-lambda-microvms-x86-architecture/>
16. <a id="ref-16"></a>CNCF Announcements — <https://www.cncf.io/announcements/>
17. <a id="ref-17"></a>Kubernetes Release Information — <https://www.kubernetes.dev/resources/release/>
18. <a id="ref-18"></a>Microsoft Open Source Blog, "What's new with Microsoft in open source and Kubernetes at KubeCon North America 2026" (2026-11-10) — <https://opensource.microsoft.com/blog/2026/11/10/whats-new-with-microsoft-in-open-source-and-kubernetes-at-kubecon-north-america-2026/>
19. <a id="ref-19"></a>Google, "Professional Agentic Architect" (2026-11-11) — <https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/professional-agentic-architect/>
20. <a id="ref-20"></a>Python.org, "Python 3.16.0a2" (2026-11-10) — <https://www.python.org/downloads/release/python-3160a2/>
21. <a id="ref-21"></a>Model Context Protocol Blog, "A More Predictable Release Cycle for MCP" (2026-11-11) — <https://blog.modelcontextprotocol.io/posts/mcp-release-cycle/>
22. <a id="ref-22"></a>Model Context Protocol Blog, "Exploring File Uploads and Downloads in MCP" (2026-11-10) — <https://blog.modelcontextprotocol.io/posts/exploring-file-uploads-and-downloads-in-mcp/>
23. <a id="ref-23"></a>OpenAI Alignment, "What affects chain-of-thought monitorability across the model lifecycle?" (2026-11-10) — <https://alignment.openai.com/cot-monitorability-model-lifecycle/>
24. <a id="ref-24"></a>Anthropic Alignment, "Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect" (2026-11-10) — <https://alignment.anthropic.com/2026/homeopathic-learning/>
25. <a id="ref-25"></a>CNCF Blog, "Jaeger previews AI-assisted troubleshooting and GenAI observability for OpenTelemetry traces at KubeCon" (2026-11-10) — <https://www.cncf.io/blog/2026/11/10/jaeger-previews-ai-assisted-troubleshooting-and-genai-observability-for-opentelemetry-traces-at-kubecon/>
26. <a id="ref-26"></a>BloombergNEF, "Data Center Power Demand Is Set to Surge, Raising New Climate Challenges" (2026-11-11) — <https://about.bnef.com/insights/data-centers/data-center-power-demand-is-set-to-surge-raising-new-climate-challenges-bloombergnef/>
27. <a id="ref-27"></a>Nature Spotlight, "AI's energy paradox" (2026-11-11) — <https://www.nature.com/articles/d41586-026-03412-5>
28. <a id="ref-28"></a>Jev Changelog — <https://docs.typesafe.ai/changelog>
29. 위시켓 프로젝트 상세 페이지(본문 표의 각 링크), Naver D2·toss.tech·LY Corporation·당근 공개 RSS 피드 (2026-11-12 수집)
