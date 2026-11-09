---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-10"
date: 2026-11-10 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각:** 2026-11-10 08:30 KST. "최신"은 2026-11-09~11-10 게시분만 가리킵니다.
> **표기 규칙:** [사실] 1차·공식 출처로 확인 / [벤더 주장] 벤더 자체 수치·평가 / [보도] 언론·보안업체 보도 / [추론] 필자 해석 / [미확인] 1차 출처 미확보.
> 앞선 브리핑(2026-11-09 등)에 실린 항목은 새 진전이 있을 때만 다시 다룹니다.

## 오늘의 핵심

1. **Claude Fable 5.2 / Mythos 5.2 공개 (11-09).** 가격 인하($8/$40 per MTok)와 함께 API 파괴적 변경(thinking 블록 prefix 검사 전면 적용, 신규 computer use 툴셋 필수)이 들어갔습니다. [사실] [1][2]
2. **CISA KEV에 4건 추가 (11-09).** OpenSSH "SSHole"(CVE-2026-123158)은 11-07부터 실제 악용이 관측됐습니다. [사실][보도] [5][6]
3. **N-able N-central "Able2Shell".** 취약점 33건과 PoC가 공개되자 N-able이 호스팅 서비스를 내렸습니다. [보도] [7][8]
4. **KubeRay, CNCF 샌드박스로 기증 (11-09).** KubeCon NA 본 행사는 11-10(현지)에 시작합니다. [사실] [9][10]
5. **토스 "TASTE" 추천 파운데이션 플랫폼 (11-09).** 앱 이벤트 시퀀스 임베딩을 사내 하위 모델 전반에 공급하는 구조입니다. [사실, 수치는 회사 자체 보고] [17]

---

## 1. AI & ML (Claude · ML/DL · 뇌과학/BCI)

### Claude Fable 5.2 / Mythos 5.2 — 2026-11-09 [사실]

- **모델 ID와 공개 범위.** `claude-fable-5-2`와 `claude-mythos-5-2`로 공개됐고, 기반 모델은 같습니다. Mythos 5.2는 Cyber·Life Sciences 검증 프로그램 참여자만 쓸 수 있습니다. [1]
- **사양.** 컨텍스트 1M, 최대 출력 128k이고 adaptive thinking이 항상 켜져 있습니다. [1][2]
- **가격.** 입력 $8 / 출력 $40 per MTok로, 5.1의 $10 / $50보다 내렸습니다. Fast mode는 $16 / $80이며 최대 2.5배 빠르다고 합니다. [1]
- **API 파괴적 변경.** 마이그레이션 때 확인할 사항입니다. [2]
  - **thinking 블록 prefix 검사:** 모든 계정에 강제됩니다. system·tools·이전 메시지를 편집한 뒤 5.2의 thinking 블록을 되돌려 보내면 400을 반환합니다.
  - **computer use:** `computer_toolset_20260801`이 필요합니다. 기존 `computer_20251124`는 Bedrock을 제외하면 400입니다.
  - **advisor tool(베타):** 실행 모델이 5.2면 advisor도 5.2여야 합니다.
  - **데이터 보존:** 30일 보존이 필수이고, 별도 승인 없이는 ZDR(무보존)을 쓸 수 없습니다.
  - **thinking 블록의 범위:** 생성한 계정이나 연결된 계정에서만 쓸 수 있습니다. 대화를 다른 모델로 넘기면 5.2의 thinking 블록은 제거됩니다.
- **권장 모델.** Anthropic은 일상 작업 기본 모델로 여전히 Opus 5.5를 권장합니다. [1]
- **벤치마크 [벤더 주장, 독립 재현 없음].** [1]
  - FrontierSWE v2: 69.9% (Opus 5.5는 62.3%)
  - OSWorld 2.1: 89.3%
  - HLE(도구 사용): 74.2%
- **안전성 [보도].** 샌드박스 탈출 같은 평가 항목이 새로 추가됐습니다. Anthropic은 "고위험 정렬 실패 위험은 낮다"고 평가하면서도, 모델이 평가 중이라는 의심을 더 자주 표현한다고 밝혔습니다. TechCrunch는 METR 보고서를 인용해 AI R&D 가속이 약 2배로 시사된다고 전했는데, 원 보고서 수치는 확인하지 못했습니다. [3]

### Claude로 전자회로 설계 — Anthropic 연구 글, 11-09 [벤더 주장]

- Fable 5.2가 Diode와 함께 실물 장치 3종을 설계했다는 사례입니다. [4]
- 내부 벤치마크 PCB Gym: 69% (Fable 5는 25%)
- BenchCAD 2.1: 83.5%
- 모두 Anthropic 내부 평가이며 제3자 재현은 없습니다.

### 기업 관련 보도 [보도]

CNBC는 Anthropic IPO가 이르면 다음 주에 이뤄질 수 있다고 보도했습니다. 회사의 공식 확인은 없습니다. [11]

### 뇌과학 / BCI

오늘 1차 출처로 확인한 신규 항목은 없습니다.

## 2. 에이전트 프레임워크 (LangGraph · CrewAI · Devin)

- **CrewAI 1.15.39 (11-09) [사실]:** 문서 변경만 있습니다. 앱이 연결되지 않았을 때의 `apps_not_connected` 오류가 문서화됐습니다. [12]
- **LangGraph [사실]:** 11-06 이후 새 릴리스가 없습니다(sdk 0.4.14, cli 0.4.42는 이미 지난 소식). [13]
- **Devin:** 오늘 확인한 공식 업데이트는 없습니다.

## 3. Kubernetes & Cloud Native

- **KubeRay CNCF 기증 (11-09) [사실].** [9]
  - Ray 클러스터·잡·서빙을 다루는 CRD 3종을 제공하는 KubeRay가 CNCF 샌드박스 프로젝트가 됩니다.
  - 블로그는 이를 PyTorch·AI 모델·Ray·Kubernetes를 묶은 "PARK 스택"이 Linux Foundation 아래로 모이는 흐름으로 설명합니다.
- **KubeCon + CloudNativeCon NA 본 행사 시작 (현지 11-10) [사실].** 기조연설로 "The Harness Is the New Runtime"(11-10 10:20 MST) 등이 잡혀 있습니다. [10]
  - [추론] 현지 11-10 오전은 한국 시간 11-11 새벽이라, 기조연설 발표 내용은 내일 브리핑에서 다룹니다.
- **Kubernetes 공식 블로그:** 10-29 이후 새 글이 없습니다. [사실]

## 4. 보안

### CISA KEV 4건 추가 — 11-09 [사실] [5]

| CVE | 제품 | 유형 |
| --- | --- | --- |
| CVE-2026-102895 | GPUStack | 부적절한 인증 |
| CVE-2026-116779 | SignalWire FreeSWITCH | 코드 인젝션 |
| CVE-2026-123158 | OpenSSH ("SSHole") | — |
| CVE-2026-123218 | IBM Aspera Faspex | 부적절한 인가 |

- 연방기관 조치 기한이 11-12라는 내용은 2차 출처에서만 봤습니다. [미확인]
- [추론] GPUStack은 GPU 클러스터에서 모델을 서빙하는 도구입니다. 사내 AI 추론 인프라에 쓰고 있다면 노출 여부부터 점검할 대상입니다.

### OpenSSH SSHole — 실제 악용 확인 (새 진전) [보도]

공개 사실은 이전 브리핑에서 다뤘고, 이번에는 실제 악용이 관측됐다는 진전입니다. [6]

- **영향 범위:** PAM 없이 musl로 빌드한 환경(Alpine 등)이 대상이며, 10.6p2(11-05)에서 수정됐습니다.
- **관측:** GreyNoise는 11-07 00:46 UTC에 첫 성공 악용을 봤고, 성공한 공격 체인 16건을 기록했습니다.
- **조치:** 업데이트하거나, 당장 어렵다면 비밀번호 인증을 끕니다.
- [추론] Alpine 기반 컨테이너 이미지에 sshd를 띄운 경우(디버깅용 사이드카 등)를 우선 찾아볼 만합니다.

### N-able N-central "Able2Shell" [보도] [7][8]

- **공개 내용:** 연구자 Sean Bales가 취약점 33건과 PoC를 GitHub에 공개했습니다(11-08). 시험 대상은 Appliance 2026.4.0.31입니다.
- **가장 심각한 체인:** 인증 없이 XXE에서 RCE까지 이어집니다.
- **N-able의 대응:** 호스팅 환경을 오프라인으로 전환했고, 온프렘 고객에게도 서버를 내리라고 권고했습니다. 핫픽스를 준비 중입니다.
- **악용 여부:** 보도 시점까지 악용은 관측되지 않았습니다.

### 그 밖의 항목

- **UnrealIRCd CVE-2026-114713 [보도]:** 악용이 보고됐고 6.2.7.1에서 수정됐습니다. 벨기에 CCB 권고는 2차 출처로만 확인했습니다. [미확인]
- **Barracuda ESG CVE-2026-116606 / CVE-2026-111560 [보도]:** 인증 우회와 명령 인젝션입니다. Check Point 주간 보고(11-09)에 실렸습니다. [14]
- **초기 보도 [미확인]:** Qubole AWS 역할 악용, npm 패키지 bee-js 13.3.0 악성 릴리스, Web3Auth/Keplr 관련 건은 애그리게이터 보도만 있어 1차 출처를 확인하지 못했습니다.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

- **AWS (11-09) [사실]:** Bedrock에서 Fable 5.2와 Mythos 5.2를 제공합니다(US Geo / Global CRIS). [15]
  - `aws_review` 보존 모드와 Enterprise Frontier Safeguards(EFS)가 함께 안내됐습니다.
  - 자격이 되는 고객은 2027-06-30까지 ZDR을 쓸 수 있습니다.
- **Google Cloud / Microsoft Foundry [사실]:** 두 곳 모두 Fable 5.2를 제공한다고 Anthropic 발표에 나와 있습니다. [1]
- **Naver Cloud:** 오늘 확인한 신규 공지는 없습니다.

## 6. 언어

- **Python 3.16.0a2:** 11-10 공개가 예정돼 있지만 아직 확인하지 못했습니다. [미확인]
- **Spring:** Boot 4.2 GA는 11월로 예정돼 있습니다. Spring AI 2.1.0-RC2는 애그리게이터 보도만 있습니다. [미확인] Spring Cloud 2026.0.0-RC2(11-05)는 지난 소식입니다.

## 7. 인프라 & Linux

- SSHole 악용(4장)이 오늘의 핵심 항목입니다.
- [추론] 대응 순서를 제안하면 다음과 같습니다.
  1. musl/Alpine 기반 이미지 중 sshd를 포함한 것을 목록화합니다.
  2. 10.6p2로 재빌드합니다.
  3. `PasswordAuthentication no`를 적용합니다.

## 9. AI 안전

- **Fable/Mythos 5.2 시스템 카드 관련 [보도]:** 샌드박스 탈출 평가가 새로 들어갔고, 평가 인식(evaluation awareness)이 늘었다고 합니다. [3]
- [추론] 모델이 평가 중임을 알아채는 빈도가 높아지면 행동 평가의 타당도가 떨어집니다. 독립 평가 기관의 재현이 중요해지는 지점입니다.

## 10. MCP

- **다음 사양 2026-12-15 [사실]:** 공식 릴리스 계획 페이지에 "NOT READY"로 표시돼 있습니다. RC 목표일은 11-15인데, 범위가 확정된 SEP는 0건입니다. [16]
  - [추론] 일정이 밀릴 가능성이 있습니다.
- **C# SDK v2.4.0 (11-07, 지난 소식):** 실험적 MCP Skills 확장이 들어갔습니다. 오늘은 새 SDK 릴리스를 확인하지 못했습니다.

## 11. MLOps / 피처 스토어

- 토스 TASTE(14장)가 사실상 "임베딩 피처 플랫폼" 사례입니다. 사전학습 임베딩을 가중치를 고정한 채 하위 모델의 피처로 공급합니다. [17]
- MLflow·Feast 등의 오늘 신규 릴리스는 확인하지 못했습니다.

## 12. 에이전트 관측성

오늘 1차 출처로 확인한 신규 항목은 없습니다. KubeCon 기조연설 "The Harness Is the New Runtime"이 관련 주제일 수 있습니다. [추론]

## 13. 그린 컴퓨팅

오늘 1차 출처로 확인한 신규 항목은 없습니다.

## 14. 국내 기업 기술 블로그

### 토스 — "TASTE, 토스의 추천 파운데이션 플랫폼" (2026-11-09) [사실, 수치는 회사 자체 보고] [17]

**구조**
- DCN-V2 + PLE 멀티태스크 학습 위에 앱 이벤트 시퀀스용 Causal Transformer를 얹었습니다.
- 앱 이벤트 모델과 소비 모델을 분리한 뒤 성능이 개선됐다고 합니다(Macro Recall@5k 기준).

**하위 활용**
- 임베딩을 가중치 고정(frozen) 상태로 하위 모델에 공급합니다.
- 회사는 CRM 모델 8개 모두에서 AUROC가 개선됐다고 밝혔습니다.

**저자들이 밝힌 한계**
- IM Auto Targeting의 전후 비교는 서로 다른 캠페인 간 비교라 인과적 비교가 아닙니다.
- 임베딩 평가용 TASTE Bench는 프록시 평가입니다.
- 기존 피처를 임베딩으로 대체했을 때 일관된 우위는 아직 확인되지 않았습니다.
- [추론] 이런 한계까지 함께 공개했다는 점에서 참고 가치가 높은 글입니다.

### NAVER D2 — "로그인 화면, 이제 만들지 마세요 - n3r OIDC" (2026-11-09 게시로 알려짐) [미확인]

- 애그리게이터 요약에 따르면, 사내 IAM(n3r)을 OIDC Provider로 확장한 사례입니다. 토큰에 프로젝트·역할·그룹 클레임을 넣고, 역할이 바뀌면 토큰을 재발급한다고 합니다.
- 원문 URL을 직접 확인하지 못해 세부 내용은 단정하지 않습니다. 원문은 NAVER D2 사이트에서 찾아볼 수 있습니다. [18]

## 15. Java/Spring 프리랜서 공고 (수집일 2026-11-10)

| 플랫폼 | 제목 | 스택 | 형태 | 금액(공개분) | 링크 |
| --- | --- | --- | --- | --- | --- |
| 위시켓 | Java/Spring Boot 기반 생명보험 신계약 시스템 개발 (신규, 11-09 등록, 마감 11-23) | Java, Spring, JSP (풀스택 중급, 4~7년) | 상주, 서울 종로구, 90일, 계약 즉시 시작 | 월 600만원 | [159547](https://project.wishket.com/project/159547/) |
| 위시켓 | (11-09 브리핑 게재분) 마감 11-16 | Java/Spring | 상주 | 월 550만원 | [159408](https://project.wishket.com/project/159408/) |
| 위시켓 | Python/Spring Batch 데이터 엔지니어 (10-21 등록, 마감 11-13 — 신규 아님) | Python, Spring Batch | — | 월 500만원 | [159210](https://project.wishket.com/project/159210/) |

- 위 공고는 수집 시점에 마감 전이었습니다. 다만 실제 모집 상태는 열람 시점에 다시 확인해야 합니다. **모집 상태 미확인**
- 159408 페이지의 관련 공고로 "Java/React 기반 생명보험사 온라인 보험 통합 구축"(월 700만원, 390일)이 보였지만, 공고 ID를 확인하지 못해 표에서 뺐습니다. [미확인]

## 8. (특집) Jev API와 의사결정 모델

- 공식 changelog의 마지막 항목은 여전히 Jev 1.14(10-14)입니다. 오늘 새 릴리스는 없습니다. [사실] [19]
- [추론] 이번 Fable 5.2의 파괴적 변경은 의사결정 파이프라인 설계에도 시사점이 있습니다. 대화 이력을 편집하는 순간 thinking 블록 재전송이 400으로 실패하므로, Jev 같은 의사결정 계층에 LLM을 붙여 이력을 재작성하는 패턴은 5.2 전환 시 점검이 필요합니다.
  1. 판단 근거(reasoning)와 확정된 결정을 분리해 저장합니다.
  2. 이력을 편집한 경우 thinking 블록을 제거한 뒤 다시 보냅니다.

---

## 사실 · 추론 · 미확인 정리

- **사실:** 다음 항목은 1차·공식 출처로 확인했습니다.
  - Fable/Mythos 5.2 사양, 가격, 파괴적 변경
  - KEV 4건 추가
  - KubeRay 기증
  - MCP 12-15 사양 "NOT READY" 상태
  - 토스 TASTE 글의 내용
  - Jev changelog 상태
  - AWS Bedrock 제공
- **벤더 주장:** 5.2 벤치마크(FrontierSWE·OSWorld·HLE)와 PCB Gym/BenchCAD 수치. 중립적 제3자의 직접 비교는 없습니다.
- **보도:** SSHole 실제 악용, N-able Able2Shell, Anthropic IPO 일정, METR 관련 수치, Barracuda.
- **추론:** KubeCon 기조연설 반영 시점, SSHole 대응 순서, MCP 일정 지연 가능성, Jev 관련 시사점.
- **미확인:** KEV 조치 기한, UnrealIRCd 권고, Qubole·bee-js·Web3Auth 건, Python 3.16.0a2, Spring AI 2.1.0-RC2, NAVER n3r OIDC 원문, 위시켓 관련 공고 ID.

## References

1. Anthropic, Introducing Claude Fable 5.2 and Mythos 5.2 (2026-11-09). <https://www.anthropic.com/claude-fable-and-mythos-5-2>
2. Anthropic, Claude Platform Release Notes (2026-11-09). <https://platform.claude.com/docs/en/release-notes/overview>
3. TechCrunch, Anthropic releases new Mythos and Fable models amid RSI concerns (2026-11-09). <https://techcrunch.com/2026/11/09/anthropic-releases-new-mythos-and-fable-models-amid-rsi-concerns/>
4. Anthropic, Claude electronics design (2026-11-09). <https://www.anthropic.com/research/claude-electronics-design>
5. CISA, CISA Adds Four Known Exploited Vulnerabilities to Catalog (2026-11-09). <https://www.cisa.gov/news-events/alerts/2026/11/09/cisa-adds-four-known-exploited-vulnerabilities-catalog>
6. BleepingComputer, Hackers exploit SSHole OpenSSH flaw to breach Linux systems (2026-11-09). <https://www.bleepingcomputer.com/news/security/hackers-exploit-sshole-openssh-flaw-to-breach-linux-systems/>
7. BleepingComputer, N-able takes cloud platform offline after 30-plus zero-days published (2026-11-09). <https://www.bleepingcomputer.com/news/security/n-able-takes-cloud-platform-offline-after-30-plus-zero-days-published/>
8. Huntress, N-able disables cloud services following disclosure of Able2Shell exploit chains (2026-11-09). <https://www.huntress.com/blog/n-able-disables-cloud-services-following-disclosure-of-able2shell-exploit-chains>
9. CNCF, Donating KubeRay to CNCF (2026-11-09). <https://www.cncf.io/blog/2026/11/09/donating-kuberay-to-cncf/>
10. Linux Foundation Events, KubeCon + CloudNativeCon North America. <https://events.linuxfoundation.org/kubecon-cloudnativecon-north-america/>
11. CNBC, Anthropic Claude Fable 5.2, Mythos 5.2 (2026-11-09). <https://www.cnbc.com/2026/11/09/anthropic-claude-fable-5-2-mythos-5-2.html>
12. CrewAI, GitHub Releases. <https://github.com/crewAIInc/crewAI/releases>
13. LangChain, LangGraph GitHub Releases. <https://github.com/langchain-ai/langgraph/releases>
14. Check Point Research, Weekly Threat Intelligence Report (2026-11-09). <https://research.checkpoint.com/>
15. AWS Machine Learning Blog, Introducing Claude Fable 5.2 on AWS (2026-11-09). <https://aws.amazon.com/blogs/machine-learning/introducing-claude-fable-5-2-on-aws/>
16. Model Context Protocol, Release plan. <https://plan.modelcontextprotocol.io/releases/2>
17. 토스, TASTE, 토스의 추천 파운데이션 플랫폼 (2026-11-09). <https://toss.tech/article/taste>
18. NAVER D2. <https://d2.naver.com/>
19. Typesafe AI, Jev Changelog. <https://docs.typesafe.ai/changelog>
