---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-17"
date: 2026-11-17 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-17 08:30 KST. 직전 브리핑이 [11-13](/2026/11/13/daily-ai-k8s-briefing/) 이어서, 이번 글은 **11-13 ~ 11-16 에 공개된 것**을 다룹니다. 각 항목에 원문 날짜를 적었고, 어제(11-16)가 아닌 것은 "최신"이라고 부르지 않습니다.
>
> **라벨**: **[사실]** 1차·공식 출처에서 직접 확인 / **[보도]** 언론·제3자 보안업체 보도 / **[벤더 주장]** 벤더 자체 수치·평가 / **[추론]** 필자 해석 / **[미확인]** 확인하지 못함.
>
> **중복 안내**: 11-13 브리핑에서 다룬 소식(Managed Agents 셀프호스팅, Gemini Decisions API, LangGraph 1.2.21, Rust 1.100.0, 커널 7.4-rc2 등)은 새 진전이 있을 때만 다시 적었습니다.

## 오늘의 핵심

1. **Anthropic 이 취약점 공개 기한을 90일 → 30일로 줄입니다** (11-16 발표, 2027-01-01 이후 제보분부터). 고·치명 등급 기준입니다. [[2]](#ref-2)
2. **Kubernetes v1.38 코드 프리즈가 오늘(11-17 21:00 KST)** 입니다. 정식 릴리스 예정일은 12-16. [[9]](#ref-9)
3. **Check Point Gaia OS 권한 상승 취약점(CVE-2026-123039)** 이 11-13 CISA KEV 에 올랐고, 연방기관 조치 기한(11-16)은 이미 지났습니다. [[11]](#ref-11)
4. **Rust nightly 가 병렬 프런트엔드를 기본으로 켰습니다** (11-16 발표). [[27]](#ref-27)
5. **미국 하이퍼스케일 데이터센터 403곳의 전력·탄소 추정치**가 Nature Sustainability 에 실렸습니다 (11-16). [[33]](#ref-33)

---

## 1. AI & 머신러닝

### Claude / Anthropic

- **[사실] 텍스트 워터마크 적용 (11-16)** — Claude 플랫폼 릴리스 노트에 따르면 Claude Opus 4.6, Opus 4.5, Sonnet 4.5, Haiku 4.5 가 생성한 텍스트에 지원 플랫폼에서 Anthropic 텍스트 워터마크가 들어갑니다. `temperature`·`top_p`·`top_k` 를 기본값이 아닌 값으로 주면 워터마크가 빠질 수 있다고 적혀 있습니다. [[1]](#ref-1)
- **[사실] 취약점 공개 정책 기한 단축 (11-16)** — Frontier Red Team 이 조율된 취약점 공개(CVD) 정책을 바꿨습니다. [[2]](#ref-2)
  - 고·치명 등급: 공개까지 **90일 → 30일**. 그 외 등급은 45일.
  - 메인테이너 무응답 시 외부 조정기관으로 넘기는 시점: 30일 → **15일**.
  - 패치 후 상세 공개까지 대기: 45일 → **30일**.
  - 실제 악용 중인 취약점의 7일 기한은 그대로입니다.
  - **2027-01-01 이후 제보분**부터 적용됩니다.
- **[추론]** 오픈소스 메인테이너 입장에서는 AI 가 찾은 취약점 제보에 대응할 시간이 3분의 1로 줄어듭니다. 보안 연락처(SECURITY.md)와 비공개 제보 채널을 연말 전에 점검해 둘 이유가 됩니다.

### ML/DL 연구

- **[사실] 안전성 평가 설계 권고 (11-13)** — Anthropic 이 "Building strong safety evaluations" 를 공개했습니다. 심리학의 재현성 개혁(사전 등록 등)에서 가져온 권고를 평가 설계에 적용하자는 내용입니다. 9번 섹션에서 다시 다룹니다. [[3]](#ref-3)

### 신경과학 / BCI

- **[사실] 모바일 기기에서 뇌→텍스트 디코딩 (arXiv, 11-13 제출)** — "FETTUCCINE" 논문은 음성인식(ASR) 모델을 활용한 end-to-end 뇌→텍스트 프레임워크를 제안합니다. 공개된 피질 내 음성 신경보철 사용자 데이터로 평가했고, 코멘트란에 NeurIPS 2026 이라고 적혀 있습니다. [[5]](#ref-5)
- **[벤더 주장 — 저자 자체 수치]** 단어 오류율 최저 4.39%, 상용 모바일 기기에서 실시간 대비 최대 370배 처리량. 저자 측 실험 결과이고 독립 재현은 **부재**합니다. [[5]](#ref-5)
- 11-13 에 소개한 Luo 등의 ECoG 무성 발화 BCI 논문(11-11)은 새 진전이 없어 반복하지 않습니다.

## 2. AI 에이전트 프레임워크

- **[사실] LangGraph 1.2.22 (11-14 UTC)** — 자체 스레드에서 도는 자식 그래프의 스트림이 서브그래프 스트리밍 호출자에게 전달되지 않던 문제 수정, `add_messages` 의 메시지 변환 생략 등 성능 개선. checkpoint 4.3.2, checkpoint-postgres 3.2.1, prebuilt 1.1.2 가 함께 나왔습니다. [[6]](#ref-6)
- **[사실] Devin Desktop v3.13.3 (11-16)** — Agent Command Center 탭 지원, 로컬 세션을 백그라운드 프로세스로 실행(창을 닫았다 열어도 세션 유지), Files 탭의 PDF·CSV·TSV 미리보기, 서브에이전트 출력 중첩 표시. 자동 저장 대신 Cmd/Ctrl+S 저장으로 바뀌었습니다. [[7]](#ref-7)
- **[사실] CrewAI** — 1.15.41(11-12) 이후 새 릴리스가 없습니다. [[8]](#ref-8)
- **[사실] Amazon Bedrock AgentCore** — 런타임 인스턴스가 서울을 포함한 6개 리전에 추가됐습니다(11-16). AgentCore Identity 는 OAuth 2.0 인가 서버 discovery URL 을 지원합니다(11-13). [[18]](#ref-18) [[19]](#ref-19)

## 3. Kubernetes & 클라우드 네이티브

- **[사실] v1.38 코드 프리즈·테스트 프리즈 = 오늘** — sig-release 일정표 기준 11-16 AoE, 즉 **11-17 12:00 UTC (21:00 KST)** 입니다. Docs Freeze 는 12-03 AoE, v1.38.0 릴리스 예정일은 12-16 입니다. [[9]](#ref-9)
- **[사실]** GitHub 릴리스 기준 최신은 여전히 v1.38.0-beta.0(11-06), 패치는 v1.37.2 / v1.36.6 / v1.35.10(10-28)입니다. 11-13 이후 새 릴리스는 없습니다. [[10]](#ref-10)
- **[사실]** kubernetes.io 블로그와 CNCF 블로그에는 11-13 이후 Kubernetes 기능 관련 새 글이 확인되지 않았습니다.
- **[사실] AWS Batch on EKS 보안 컨텍스트 확장 (11-13)** — Linux capabilities, seccomp 프로파일, 파드 수준 `securityContext` 를 지정할 수 있게 됐습니다. Pod Security Standards `restricted` 를 강제하는 클러스터에서 Batch 잡을 돌릴 수 있게 하는 변경입니다. [[20]](#ref-20)
- **[추론]** 프리즈 이후에는 버그 수정만 들어갑니다. v1.38 에 기대하던 KEP 가 있다면 오늘 밤 이후 enhancements 트래킹 보드에서 잔류 여부를 확인하는 편이 정확합니다.

## 4. 사이버 보안

### 실제 악용 취약점

| CVE | 대상 | 내용 | KEV 등재 / 기한 | 라벨 |
|---|---|---|---|---|
| CVE-2026-123039 | Check Point 다수 제품 (Gaia OS) | DynamicCLI 데몬이 root 로 실행되며 인증 없이 로컬 소켓을 받음 → 인증된 로컬 사용자가 root 권한 획득 | 11-13 / **11-16 (경과)** | [사실] [[11]](#ref-11) |
| CVE-2026-114713 | UnrealIRCd | 구분자 무력화 미흡. 서버 2대 이상 연결된 네트워크의 사용자가 서버 간 명령 주입 | 11-13 / **11-16 (경과)** | [사실] [[11]](#ref-11) |
| CVE-2026-90436 | Apache Axis 1.x (및 이를 쓰는 제품) | unsafe reflection 으로 비인증 원격 코드 실행 | — | [보도] [[13]](#ref-13) |

- **[보도] Check Point** — BleepingComputer(11-13)는 Check Point 가 "수십 곳의 고객"에서 실제 악용을 관측했고 긴급 핫픽스를 냈다고 전했습니다. 공격자는 Mobile Access 포털의 기존 취약점으로 진입한 뒤 이 취약점으로 root 를 얻었다고 합니다. 즉시 패치가 어려우면 해당 데몬 프로세스를 중지하라는 것이 벤더 권고입니다. [[12]](#ref-12)
- **[보도] Apache Axis 1.x → Confluence Data Center · N-able N-central** — Rapid7(11-16)은 11-13 자사 MDR 이 Confluence Data Center 를 겨냥한 CVE-2026-90436 악용을 탐지했다고 밝혔습니다. 같은 날 N-able 도 N-central 에 대한 실제 악용을 보고했다고 합니다. 두 제품 모두 **기본값이 아닌 설정**에서만 취약합니다. Confluence 는 "Remote API (XML-RPC & SOAP)" 를 켠 1.x~9.x 가 대상이고 9.2.28 이 수정 버전입니다. Axis 1.x 는 EOL 이라 Apache 는 수정 릴리스를 낼 계획이 없습니다. [[13]](#ref-13)
- **[추론]** 11-13 브리핑에서 N-central 핫픽스를 다뤘는데, 이번 건은 그 연장선입니다. Axis 1.x 는 오래된 Java SOAP 스택이라 사내 레거시 시스템에 묻혀 있을 가능성이 있습니다. `axis.jar` 의존성 검색을 한 번 돌려볼 만합니다.
- **[사실]** KEV 카탈로그 버전은 2026.11.13 입니다. 11-10 등재분(Chromium CVE-2026-125350, Outlook CVE-2026-124194, Cisco BroadWorks CVE-2026-20320 등)의 기한은 11-24 입니다. [[11]](#ref-11)

### 위협 동향

- **[벤더 주장] Google GTIG "AI Threat Tracker" (11-16)** — 자율 다중 에이전트 공격 프레임워크의 실사용, 패치 diff 를 자동 분석해 n-day 익스플로잇을 만드는 흐름, 탈취한 LLM 접근권을 되파는 LLMJacking, 코딩 어시스턴트 설정 파일을 조작하는 공급망 공격을 보고했습니다. Google 자체 관측이고 독립 검증은 **부재**합니다. [[14]](#ref-14)

### 아이덴티티 보안

- **[사실] AWS IAM Identity Center VPC 엔드포인트 (11-16)** — PrivateLink 와 네트워크 접근 제어를 지원합니다. [[21]](#ref-21)
- **[사실] AWS Secrets Manager** — Auth0·Okta·Palo Alto 용 managed external secrets(11-16), 계정 간 복제(11-13). [[22]](#ref-22) [[23]](#ref-23)
- **[사실] AWS KMS 키를 RAM 으로 공유 (11-16)**. [[24]](#ref-24)

## 5. CSP

### AWS

- **[사실] S3 Vectors 하이브리드 검색 (11-16)** — 벡터 검색과 BM25 전문 검색을 한 번의 `QueryVectors` 호출로 묶고 RRF 로 결과를 합칩니다. [[15]](#ref-15)
  - **[벤더 주장]** "최대 90% 비용 절감"은 AWS 의 주장입니다. 비교 대상·조건이 공개 재현 가능한 형태가 아닙니다.
- **[사실] Redshift 의 Iceberg 테이블 다중 문장 트랜잭션·타임 트래블 (11-16)**. [[16]](#ref-16)
- **[사실] AWS Backup 논리적 에어갭 볼트가 RDS 지원 (11-16)**. [[17]](#ref-17)
- **[사실] VPC 네트워킹 비용 배분 (11-16)** — NAT 게이트웨이·데이터 전송 비용을 CUR 에서 워크로드별로 나눠 볼 수 있습니다. [[25]](#ref-25)
- **[사실] Systems Manager 가 Google Cloud VM 온보딩 지원 (11-13)**. [[26]](#ref-26)

### Azure

- **[사실]** 11-13 이후 확인된 항목은 "Azure Data Share 2029-11-12 지원 종료" 공지(11-13) 하나입니다. [[28]](#ref-28)

### GCP

- **[사실] BigQuery·Looker 의 에이전트 관측성·거버넌스 (11-13)** — 자사 데이터 에이전트와 ADK·LangGraph 기반 커스텀 에이전트의 텔레메트리를 BigQuery 로 모읍니다. 대화 로깅, Conversational Analytics API, A2A 워크플로가 GA 입니다. [[29]](#ref-29)

### Naver Cloud

- **[미확인]** 공지 페이지가 자바스크립트 렌더링이라 11-13 ~ 11-17 항목을 텍스트로 확인하지 못했습니다.

## 6. 프로그래밍 언어

- **[사실] Rust — nightly 에서 병렬 프런트엔드 기본 활성화 (11-16 발표)** — nightly-2026-11-14 부터 기본입니다. [[27]](#ref-27)
  - **[벤더 주장 — Rust 프로젝트 자체 벤치마크]** 순차 대비 벽시계 시간 평균 변화: `check` 프로파일 −21.95%(2스레드) / −37.99%(4) / −44.23%(8), `debug` −14.2% / −29.14% / −36.1%. 중립 제3자 측정은 **부재**합니다.
  - **[추론]** stable 이 아닌 nightly 입니다. CI 에서 nightly 를 쓰는 프로젝트는 빌드 시간과 함께 메모리 사용량 변화도 같이 봐야 합니다.
- **[사실] Python** — 11-16 블로그 글은 문서 번역 후원 소식이고, 3.16.0a2(11-10) 이후 릴리스는 없습니다. [[30]](#ref-30)
- **[사실] 변동 없음** — TypeScript(7.1 Beta, 10-20), React(19.3.1, 10-14), Vue(3.6.0-rc.15, 11-12), Kotlin(2.5.0-RC, 11-11), Spring Boot(4.2.0-RC2, 11-05), Node.js(26.13.1 / 24.22.3 / 22.23.5, 11-11). 모두 11-13 이전 릴리스라 "최신 소식"은 아닙니다.

## 7. 인프라 & 리눅스

- **[사실] Linux 7.4-rc3 (11-15)** — kernel.org 기준 mainline 은 7.4-rc3, stable 은 7.3.4(11-10) 그대로, longterm 6.18.63 / 6.12.117 도 변동 없습니다. linux-next 는 next-20261116. [[31]](#ref-31)
- 11-13 브리핑에서 "주말에 rc3 가 나올 것"이라고 **[추론]** 으로 적었는데, 그대로 확인됐습니다.

## 9. AI 안전 & 정렬

- **[사실] "Building strong safety evaluations" (Anthropic, 11-13)** — 안전성 평가를 믿을 수 있게 만들기 위한 권고입니다. 사전 등록, 팀 역량 구성 등 심리학 재현성 개혁의 교훈을 가져왔습니다. [[3]](#ref-3)
- **[사실] Anthropic Alignment Science Blog 11월 게시물** — "Worse Together: How Performance Breaks Down in Multi-User Multi-Agent Teams", "Diluting Poisoned Fine-Tuning Data Can Strengthen Its Effect", "Welfare Regard in Multi-Agent Systems" 가 "November 2026" 로 올라와 있습니다. [[4]](#ref-4)
  - **[미확인]** 목록에 월만 표기돼 있어 정확한 게시일은 확인하지 못했습니다. 11-13 이후 글인지도 단정할 수 없습니다.
- **[추론]** 취약점 공개 기한 단축(1번 섹션)도 넓게 보면 안전 정책입니다. 모델이 취약점을 찾는 속도가 빨라질수록 "공개까지 기다리는 시간"이 방어자보다 공격자에게 유리해진다는 판단이 깔려 있습니다.

## 10. MCP 생태계

- **[사실]** MCP 공식 블로그에는 11-11 이후 새 글이 없습니다. [[32]](#ref-32)
- **[사실]** AgentCore Identity 의 OAuth 2.0 discovery URL 지원(11-13)은 MCP 서버 앞단 인가 구성에 닿는 변경입니다. [[19]](#ref-19)
- **[추론]** GTIG 보고서가 지적한 "코딩 어시스턴트 설정 조작" 공급망 공격은 MCP 서버 설정 파일도 대상이 될 수 있습니다. 리포에 커밋된 MCP 설정 변경은 코드 리뷰 대상에 넣어야 합니다.

## 11. MLOps / 피처 스토어

- **[사실]** 11-13 이후 새 릴리스 없음 — MLflow 3.18.0(11-04), Feast v0.68.0(11-10), Kubeflow Pipelines 2.18.0(10-28).
- **[사실]** 인접 소식으로 S3 Vectors 하이브리드 검색(11-16)과 Redshift 의 Iceberg 트랜잭션(11-16)이 있습니다. [[15]](#ref-15) [[16]](#ref-16)
- **[사실]** 네이버 D2 의 GPU 서빙 최적화 사례(11-16)는 14번 섹션에 있습니다.

## 12. 에이전트 관측성

- **[사실] Langfuse — AI Gateway 키별 모델 제한 (11-13)** — API 키마다 호출 가능한 모델을 패턴(예: `openai-prod:*`)으로 제한합니다. [[35]](#ref-35)
- **[사실] Langfuse — Gemini 판단 모델 평가기 (11-13)** — 8번 특집에서 다룹니다. [[36]](#ref-36)
- **[사실] GCP BigQuery·Looker 에이전트 관측성 (11-13)** — 5번 섹션 참조. [[29]](#ref-29)
- **[사실] OpenTelemetry (11-16)** — 2026 커뮤니티 어워드 수상자 발표. 기능 변경은 아닙니다. [[37]](#ref-37)

## 13. 그린 컴퓨팅

- **[사실] 미국 하이퍼스케일 데이터센터 전력·탄소 추정 (Nature Sustainability, 11-16)** — 2024-05 ~ 2025-04 에 가동된 403개 시설을 시설 단위로 분석했습니다. [[33]](#ref-33)
  - 전력 소비 약 68 ~ 99 TWh, 중앙 시나리오 약 82 TWh(미국 전체 전력 소비의 약 1.8%).
  - CO2 약 21 ~ 31 Mt, 중앙 시나리오 약 25.7 Mt.
  - 귀속된 발전량의 약 54% 가 화석연료.
  - 전력 가중 탄소 집약도 약 314 gCO2/kWh (미국 평균 약 348).
  - 한계: 논문은 추정치이고, Harvard 보도자료에 따르면 범용 연산과 AI 연산을 시설별로 구분하지 못했습니다. [[34]](#ref-34)
- **[사실] Antalya AI Pledge (ITU·COP31 의장국, 11-16)** — AI 인프라의 저·무탄소 전력 사용, 수명주기 관리, 환경 영향 측정·보고, 개도국 지원의 4개 축을 담은 자발적 서약입니다. [[38]](#ref-38)
- **[추론]** 서약은 자발적이라 구속력이 없습니다. 실무에 먼저 닿는 것은 "측정·보고" 축일 가능성이 큽니다. 워크로드별 전력·탄소를 내놓으라는 요구가 조달 조건으로 들어올 수 있습니다.

## 14. 국내 기업 기술 블로그

| 회사 | 제목 | 발행일 | 핵심 요약 | 링크 |
|---|---|---|---|---|
| 네이버 D2 | Image AI 서빙 최적화: CPU와 GPU의 빈 시간을 줄여 H100 67장을 절감하기까지 | 11-16 | SNOW 의 16개 Image AI 서비스를 LitServe 로 전환하고, 워커·스레드·오토스케일링 조정과 GPU 공유로 H100 환산 67.37장을 절감했다는 발표 세션 (회사 자체 수치) | [원문](https://d2.naver.com/helloworld/9994827) |
| 네이버 D2 | 노트북을 닫아도 개발은 계속된다: 자율 그래프 주도 개발 | 11-16 | 스펙·코드를 에이전트 루프가 쓰고 결정론적 코드가 검사하는 그래프 구조. Upstream → Spec → Dev → Verify → Audit 노드 구성과 루프 안정화의 어려움 | [원문](https://d2.naver.com/helloworld/5976687) |
| 네이버 D2 | 흩어진 행동을 연결하다: 네이버 전 지면의 사용자 행동을 학습하는 추천 모델 개발기 | 11-16 | 검색·피드·광고 도메인을 잇는 추천 모델의 구조, GPU 서빙 최적화, 지식 증류를 통한 도메인 간 전이 | [원문](https://d2.naver.com/helloworld/1599966) |
| 네이버 D2 | 카페 관리도구 개편기: 문서는 낡았고, 사람은 떠났고, 코드만 남았다. | 11-16 | 14년 된 레거시 관리도구를 AI 로 분석하고 Storybook·MSW 로 화면과 동작을 재현해 재개발한 과정 | [원문](https://d2.naver.com/helloworld/4049909) |
| LY Corporation (LINE) | DEF CON CTF 2026 본선 참가기 | 11-13 | 본선 3위 팀의 참가기. 규칙상 LLM·AI 에이전트 사용이 허용됐고, AI 기반 취약점 분석·익스플로잇 갱신·패치 관찰 도구를 운용한 경험 | [원문](https://techblog.lycorp.co.jp/ko/defcon-ctf-2026-finals) |
| 우아한형제들 | 옆자리 동료에게 AI를 알려주지 않기로 했다 | 11-13 | 사내 AI 전환(AX) 사례. 가르치는 대신 옆에 앉아 함께 하는 방식, 직군을 가로지른 92명 신청과 자원 AI 코치 운영 | [원문](https://techblog.woowahan.com/28497/) |

- 네이버 D2 4건은 사내 행사 NAVER Engineering Day 10th 발표 세션 공개입니다. 발행일은 D2 가 내려주는 게시 시각으로 확인했고, 본문은 발표 소개·목차 수준이며 상세는 발표 영상에 있습니다.
- **[사실]** 11-13 이후 새 글이 확인되지 않은 곳: 토스(최신 11-10), 카카오(11-08), 당근(11-03).
- **[미확인]** 쿠팡, 두나무는 11-13 이후 게시물을 확인하지 못했습니다.

## 15. Java/Spring 프리랜서 공고

수집일은 **2026-11-17** 입니다. 모두 위시켓 공고 상세 페이지 원문에서 확인했고, 로그인 뒤에 있는 상세 요구사항은 수집하지 않았습니다.

| 플랫폼 | 공고명 | 기술 스택 | 계약·근무 형태 | 금액 | 등록 / 마감 | 링크 |
|---|---|---|---|---|---|---|
| 위시켓 | Java/Airflow·K8s 기반 Datalake EDS 비정형 데이터 처리 파이프라인 개발 | Java, Airflow, Kubernetes, Iceberg, MinIO, PostgreSQL, Kafka, Jenkins, ArgoCD | 기간제 · 백엔드 시니어(8~20년) · 90일 · 12-01 시작 · 경기 성남 분당구 | 월 730만원 | 11-16 / 11-30 (모집 중) | [원문](https://www.wishket.com/project/159666/) |
| 위시켓 | Scala Spark/Java Flink 기반 Bigdata FDC 플랫폼 데이터 파이프라인 개발 | Scala, Spark, Java, Flink, Iceberg, Yunikorn, Kubeflow | 기간제 · 백엔드 시니어(8~20년) · 90일 · 12-16 시작 · 경기 성남 분당구 | 월 730만원 | 11-16 / 11-30 (모집 중) | [원문](https://www.wishket.com/project/159668/) |
| 위시켓 | Java 기반 대형 서점 시스템 운영 개발 | Java (풀스택) | 기간제 · 미드(4~7년) · 390일 · 2027-01-01 시작 · 서울 종로구 | 월 550만원 | 11-13 / 11-27 | [원문](https://www.wishket.com/project/159621/) |
| 위시켓 | Java/Spring Boot·React/Vue 기반 공공·민간 SI/SM 웹 서비스 풀스택 개발 | Java, Spring Boot, Spring MVC, Spring Data JPA, Spring Security, Redis, MySQL, MongoDB, Kafka, RabbitMQ, AWS, GCP, Docker | 기간제 · 미드(4~7년) · 360일 · 즉시 시작 · 경기 용인 기흥구 | 월 400만원 | 11-13 / 11-27 | [원문](https://www.wishket.com/project/159636/) |
| 위시켓 | Java/Kotlin·Spring Boot 기반 쇼핑몰 운영 백엔드 SM | Java, Kotlin, Spring Boot, JPA | 기간제 · 백엔드 시니어(8~10년) · 360일 · 2027-01-01 시작 · 서울 용산구 | 협의 후 결정 | 11-13 / 11-27 | [원문](https://www.wishket.com/project/159643/) |

- 11-13 등록 3건은 마감일(11-27)이 지나지 않았지만, 수집 시점의 실제 모집 상태는 **모집 상태 미확인**으로 둡니다. 지원 전에 원문에서 확인하세요.
- **[미확인]** 프리모아, 이랜서는 목록이 자바스크립트로 렌더링돼 Java/Spring 공고 원문을 확인하지 못했습니다. 검색 요약만으로는 싣지 않았습니다.
- **[추론]** 이번 주 상위 단가 2건은 둘 다 데이터 파이프라인(Iceberg + Kubernetes 계열)입니다. Spring 웹 백엔드만으로는 닿기 어려운 단가대라는 점은 11-13 브리핑과 같은 흐름입니다.

---

## 8. 특집 — Jev API와 판단(Decision) 모델

### 오늘의 변화

- **[사실] Jev 본체는 변동 없음** — TypeSafe 의 Jev 변경 이력 최신 항목은 여전히 1.14(10-14)입니다. [[39]](#ref-39)
- **[사실] Langfuse 가 Gemini 판단 모델 평가기를 추가 (11-13)** — Google AI Studio 연결로 `gemini-decision-1` 을 평가기에 쓸 수 있습니다. Choice / Score / Yes·no 질문마다 확률과 confidence 가 붙은 점수가 기록됩니다. Vertex AI 연결은 아직 지원하지 않습니다. [[36]](#ref-36)
- 11-13 브리핑에서 다룬 Gemini Decisions API(11-11), langchain 1.5.0 의 Decisions API 지원은 새 진전이 없어 반복하지 않습니다.

### 어떻게 읽을 것인가

- **[추론]** 판단 모델의 쓰임이 "에이전트 안의 분기"에서 "운영 중인 응답의 평가"로 넓어지고 있습니다. Langfuse 가 예로 든 것도 환불 정책과 모순되는 응답 표시, 검토 팀 라우팅, 0~3 루브릭 채점입니다. 생성 모델을 심사자로 쓰는 LLM-as-judge 의 자리를 일부 대체하는 구도입니다.
- **[추론]** 판단 모델은 텍스트 대신 확률을 돌려주므로 "confidence 가 낮으면 사람에게 넘긴다"는 규칙을 임계값 하나로 쓸 수 있습니다. 다만 그 확률이 얼마나 잘 보정돼 있는지는 벤더 자체 평가에 기대고 있습니다.
- **[미확인]** Jev, Gemini Decision 1, 기타 판단 모델을 같은 조건에서 비교한 **중립 헤드투헤드 벤치마크는 여전히 부재**합니다. 성능 우열은 판단할 수 없습니다.

### 실무 체크포인트

1. 평가기를 판단 모델로 바꾸기 전에, 기존 LLM-as-judge 결과와 사람 라벨 표본을 나란히 놓고 일치율을 먼저 재 보세요.
2. confidence 임계값은 벤더 기본값을 그대로 쓰지 말고 자기 데이터에서 보정 곡선을 그려 정하세요.
3. 게이트웨이를 거쳐 호출한다면 키별 모델 제한(12번 섹션)으로 평가용 키가 생성 모델을 부르지 못하게 묶어 둘 수 있습니다.

## 사실 · 추론 · 미확인 정리

**사실 (1차·공식 확인)**
- Anthropic: 텍스트 워터마크(11-16), CVD 기한 단축(11-16 발표, 2027-01-01 적용), 안전성 평가 권고(11-13)
- Kubernetes v1.38 코드 프리즈 11-17 12:00 UTC, 릴리스 예정 12-16
- CISA KEV 11-13 등재 2건(CVE-2026-123039, CVE-2026-114713), 기한 11-16
- LangGraph 1.2.22(11-14), Devin Desktop v3.13.3(11-16), Linux 7.4-rc3(11-15)
- Rust nightly 병렬 프런트엔드 기본 활성화(11-16 발표)
- AWS 11-13·11-16 발표들, GCP BigQuery·Looker 에이전트 관측성(11-13), Azure Data Share 종료 공지(11-13)
- Nature Sustainability 데이터센터 논문(11-16), Antalya AI Pledge(11-16)
- 국내 기술 블로그 6건, 위시켓 공고 5건의 게시 사실

**벤더 주장 · 보도 (독립 검증 부재)**
- S3 Vectors "최대 90% 비용 절감"
- Rust 병렬 프런트엔드 빌드 시간 수치 (프로젝트 자체 벤치마크)
- FETTUCCINE 의 WER·처리량 (저자 자체 실험)
- GTIG 의 에이전트형 위협 관측
- Check Point 악용 규모(BleepingComputer 보도), Axis 1.x 악용(Rapid7 관측)
- 네이버 D2 의 H100 67장 절감 (회사 자체 수치)

**추론 (필자 해석)**
- CVD 기한 단축이 오픈소스 메인테이너에게 주는 부담
- Axis 1.x 가 사내 레거시에 남아 있을 가능성
- MCP 설정 파일이 공급망 공격 대상이 될 수 있다는 점
- 판단 모델이 LLM-as-judge 를 일부 대체하는 구도
- 상위 단가 공고가 데이터 파이프라인에 몰려 있다는 관찰

**미확인**
- Anthropic Alignment 블로그 11월 글들의 정확한 게시일
- Naver Cloud 11-13 이후 공지
- 쿠팡·두나무 기술 블로그 신규 글
- 프리모아·이랜서의 Java/Spring 공고
- 위시켓 11-13 등록 3건의 현재 모집 상태
- 판단 모델 간 중립 비교 벤치마크

## References

<a id="ref-1"></a>[1] Anthropic, "Claude Platform release notes" — <https://platform.claude.com/docs/en/release-notes/overview>

<a id="ref-2"></a>[2] Anthropic Frontier Red Team, "Updating our coordinated vulnerability disclosure policy timelines" (2026-11-16) — <https://www.anthropic.com/research/coordinated-vulnerability-disclosure-timelines>

<a id="ref-3"></a>[3] Anthropic, "Building strong safety evaluations" (2026-11-13) — <https://www.anthropic.com/research/building-strong-safety-evaluations>

<a id="ref-4"></a>[4] Anthropic, Alignment Science Blog — <https://alignment.anthropic.com/>

<a id="ref-5"></a>[5] McCart et al., "FETTUCCINE: Fast and efficient brain-to-text decoding on mobile devices", arXiv:2611.18561 (2026-11-13 제출, 프리프린트) — <https://arxiv.org/abs/2611.18561>

<a id="ref-6"></a>[6] LangGraph releases — <https://github.com/langchain-ai/langgraph/releases>

<a id="ref-7"></a>[7] Devin Desktop changelog — <https://docs.devin.ai/desktop/changelog>

<a id="ref-8"></a>[8] CrewAI releases — <https://github.com/crewAIInc/crewAI/releases>

<a id="ref-9"></a>[9] Kubernetes SIG Release, "Kubernetes 1.38 release schedule" — <https://github.com/kubernetes/sig-release/blob/master/releases/release-1.38/README.md>

<a id="ref-10"></a>[10] Kubernetes releases — <https://github.com/kubernetes/kubernetes/releases>

<a id="ref-11"></a>[11] CISA, Known Exploited Vulnerabilities Catalog (버전 2026.11.13) — <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>

<a id="ref-12"></a>[12] BleepingComputer, "Check Point warns of zero-day flaw exploited for root access" (2026-11-13) — <https://www.bleepingcomputer.com/news/security/check-point-patches-zero-day-that-lets-hackers-get-root-access/>

<a id="ref-13"></a>[13] Rapid7, "Rapid7 Detected Exploitation of CVE-2026-90436 against Atlassian Confluence Data Center, N-able N-central also Exploited" (2026-11-16) — <https://www.rapid7.com/blog/post/etr-rapid7-detected-exploitation-of-cve-2026-90436-against-atlassian-confluence-data-center-n-able-n-central-also-exploited/>

<a id="ref-14"></a>[14] Google Threat Intelligence Group, "Agentic Threat Activity Crosses a Significant Threshold" (2026-11-16) — <https://cloud.google.com/blog/topics/threat-intelligence/agentic-threat-activity-crosses-a-significant-threshold/>

<a id="ref-15"></a>[15] AWS, "S3 Vectors hybrid search" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/s3-vectors-hybrid-search/>

<a id="ref-16"></a>[16] AWS, "Redshift multi-statement transactions and time travel for Iceberg" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/redshift-time-travel-multi-statement>

<a id="ref-17"></a>[17] AWS, "AWS Backup logically air-gapped vault for RDS" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-backup-air-gapped-vault-rds/>

<a id="ref-18"></a>[18] AWS, "AgentCore runtime instances in additional regions" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/agentcore-aws-regions/>

<a id="ref-19"></a>[19] AWS, "Bedrock AgentCore Identity OAuth 2.0 discovery" (2026-11-13) — <https://aws.amazon.com/about-aws/whats-new/2026/11/bedrock-agentcore-oauth2-discovery/>

<a id="ref-20"></a>[20] AWS, "AWS Batch on EKS security context" (2026-11-13) — <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-batch-eks-security-context/>

<a id="ref-21"></a>[21] AWS, "IAM Identity Center VPC endpoints" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/iam-identity-center-vpc-endpoints/>

<a id="ref-22"></a>[22] AWS, "Secrets Manager managed external secrets for Auth0, Okta, Palo Alto" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/secrets-manager-managed-external-secrets-auth0-okta-palo-alto/>

<a id="ref-23"></a>[23] AWS, "Secrets Manager cross-account replication" (2026-11-13) — <https://aws.amazon.com/about-aws/whats-new/2026/11/secrets-manager-cross-account/>

<a id="ref-24"></a>[24] AWS, "KMS key sharing with Resource Access Manager" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/kms-key-sharing-resource-access-manager/>

<a id="ref-25"></a>[25] AWS, "Networking Flexible Cost Allocation" (2026-11-16) — <https://aws.amazon.com/about-aws/whats-new/2026/11/networking-flexible-cost-allocation/>

<a id="ref-26"></a>[26] AWS, "Systems Manager Google Cloud support" (2026-11-13) — <https://aws.amazon.com/about-aws/whats-new/2026/11/systems-manager-google-cloud-support/>

<a id="ref-27"></a>[27] Rust Blog, "Enabling the parallel frontend on nightly" (2026-11-16) — <https://blog.rust-lang.org/2026/11/16/enabling-parallel-frontend-on-nightly/>

<a id="ref-28"></a>[28] Microsoft Azure Updates, "Retirement: Azure Data Share will be retired on November 12, 2029" (2026-11-13) — <https://azure.microsoft.com/updates?id=578818>

<a id="ref-29"></a>[29] Google Cloud Blog, "New AI agent observability and governance across BigQuery and Looker" (2026-11-13) — <https://cloud.google.com/blog/products/data-analytics/enterprise-ai-agent-observability-with-bigquery-and-looker/>

<a id="ref-30"></a>[30] Python Insider (Python 공식 블로그) — <https://blog.python.org/>

<a id="ref-31"></a>[31] The Linux Kernel Archives — <https://www.kernel.org/>

<a id="ref-32"></a>[32] Model Context Protocol Blog — <https://blog.modelcontextprotocol.io/>

<a id="ref-33"></a>[33] Guidi et al., "Assessing the carbon emissions and energy consumption of US hyperscale data centres", Nature Sustainability (2026-11-16), doi:10.1038/s41893-026-01985-7 — <https://www.nature.com/articles/s41893-026-01985-7>

<a id="ref-34"></a>[34] Harvard T.H. Chan School of Public Health, 보도자료 (2026-11-16) — <https://hsph.harvard.edu/news/hyperscale-data-centers-energy-consumption-carbon-emissions-newly-estimated-by-researchers/>

<a id="ref-35"></a>[35] Langfuse Changelog, "Restrict models per AI Gateway key" (2026-11-13) — <https://langfuse.com/changelog/2026-11-13-ai-gateway-key-model-restrictions>

<a id="ref-36"></a>[36] Langfuse Changelog, "Evaluate with Gemini decision models" (2026-11-13) — <https://langfuse.com/changelog/2026-11-13-gemini-decision-model-evaluators>

<a id="ref-37"></a>[37] OpenTelemetry Blog — <https://opentelemetry.io/blog/>

<a id="ref-38"></a>[38] ITU, "ITU and COP Presidency rally global partners to unlock sustainable AI development" (2026-11-16) — <https://www.itu.int/en/mediacentre/Pages/PR-2026-11-16-COP31-Antalya-AI-Pledge.aspx>

<a id="ref-39"></a>[39] TypeSafe, Jev changelog — <https://docs.typesafe.ai/changelog>

국내 기술 블로그와 프리랜서 공고의 원문 링크는 14·15번 섹션의 표 안에 있습니다.
