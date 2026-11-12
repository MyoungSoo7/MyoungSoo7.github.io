---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-13"
date: 2026-11-13 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-13 08:30 KST. 수집 대상은 원칙적으로 **2026-11-12 ~ 11-13** 날짜가 원문에서 확인되는 소식입니다. 그보다 오래된 항목은 "배경"으로만 적고 최신으로 다루지 않습니다.
>
> **라벨**: **[사실]** 1차·공식 출처에서 직접 확인 / **[보도]** 언론·보안업체 보도로만 확인(벤더 1차 확인 없음) / **[벤더 주장]** 벤더 자체 수치·벤치마크(제3자 재현 부재) / **[추론]** 필자 해석 / **[미확인]** 확인하지 못함.
>
> **중복 안내**: [전날(11-12) 브리핑](/2026/11/12/daily-ai-k8s-briefing/)에 실린 소식은 새 진전이 있을 때만 다시 적습니다. 오늘은 전날 [보도]·[미확인]으로 남겼던 세 건(Fable 5.2 가격, Rust 1.100.0, BCI 논문 정확도)이 1차 출처로 확인되어 갱신합니다.

## 오늘의 핵심

- **[사실]** Anthropic이 **Claude Managed Agents 셀프 호스팅**을 릴리스 노트에 올렸습니다(11-12). 서비스 전체를 자체 인프라에서 돌리고 에이전트·세션·이력을 그 안에 저장하는 형태입니다. [[1]](#ref-1)
- **[사실]** **Rust 1.100.0** 정식 릴리스(11-12). never 타입 `!` 안정화, `core` 의 `Allocator` API 가 포함됐습니다. 전날 [미확인]으로 적었던 항목입니다. [[24]](#ref-24)
- **[사실]/[보도]** **N-able N-central**: 벤더는 핫픽스 HF2 로 인증 없이 악용 가능한 취약점을 모두 해결했다고 공지했지만(11-11), 하루 뒤 HF2 에서도 동작한다는 새 PoC 와 악용 보도가 나왔습니다(11-12, 보도). [[15]](#ref-15) [[16]](#ref-16)
- **[사실]** AWS **Bedrock AgentCore** 차세대 런타임이 기본값이 됐습니다(11-12). 세션별 microVM, scale-to-zero, 서울 리전 포함. [[11]](#ref-11)
- **[사실]** Google **Gemini 4 Hydrogen** 공개(11-12), OpenTelemetry 블로그의 **에이전트 계측 하네스** 글(11-12). [[4]](#ref-4) [[29]](#ref-29)
- **[사실]** 위시켓에 11-12 등록된 Java/Spring 계열 기간제 공고 3건을 원문에서 확인했습니다(섹션 15).

---

## 1. AI & ML

**Claude Managed Agents 셀프 호스팅** (Anthropic, 11-12)

- **[사실]** Anthropic 플랫폼 릴리스 노트(11-12)에 따르면 Claude Managed Agents 서비스 전체를 고객 자체 인프라에서 운영할 수 있게 됐습니다. 에이전트·세션·이력이 그 인프라에 저장되고, 모델 요청은 고객이 고른 제공자로 나갑니다(기본은 Anthropic). 이용은 담당 어카운트 팀을 통해 신청하는 방식입니다. [[1]](#ref-1)
- **[보도]** The Next Web 은 셀프 호스팅판에 웹훅·예약 실행이 없고 기존 호스팅 환경에서의 마이그레이션 경로도 없다고 전했습니다(11-12). 이 제약은 릴리스 노트 본문에서 직접 확인하지 못했습니다. [[2]](#ref-2)
- **[추론]** 데이터 상주 요건 때문에 관리형 에이전트를 못 쓰던 조직이 대상입니다. 다만 "모델 호출은 여전히 외부로 나간다"는 점은 그대로이므로, 폐쇄망 요건과는 구분해서 봐야 합니다.

**Claude Fable 5.2 가격 — 전날 [보도] 항목의 1차 확인**

- **[사실]** Anthropic 공식 페이지(11-09 게시)와 릴리스 노트에서 Fable 5.2 가격이 입력 100만 토큰당 8달러, 출력 40달러로 확인됩니다. 컨텍스트 100만 토큰, 최대 출력 12만 8천 토큰입니다. 같은 문서 기준 5.1 은 10달러/50달러였습니다. [[3]](#ref-3) [[1]](#ref-1)

**Gemini 4 Hydrogen** (Google, 11-12)

- **[사실]** Google 이 개발자용 글에서 Gemini 4 Hydrogen 을 공개했습니다. 사고(thinking) 수준을 네 단계로 조절할 수 있고 Gemini API, AI Studio, Android Studio, Antigravity 에서 쓸 수 있다고 밝혔습니다. [[4]](#ref-4)
- **[미확인]** 중립 제3자의 성능 비교는 아직 **부재**합니다. 벤더 발표 글의 성능 서술은 옮기지 않았습니다.

**신경과학 — 기저핵 세포 아틀라스** (Nature 뉴스, 11-12)

- **[사실]** Nature 뉴스는 BICAN(BRAIN Initiative Cell Atlas Network) 컨소시엄이 사람·마카크·마모셋의 기저핵 세포 2,550만 개를 다룬 아틀라스를 논문 26편으로 발표했다고 전했습니다. [[5]](#ref-5)

**무성 발화 BCI 논문 — 전날 [미확인] 수치의 확인**

- **[사실]** 전날 소개한 Luo 등(Communications Biology) 논문 초록에서 수치를 확인했습니다. 참가자 1명, 18개 세션, 중앙값 정확도 97.1%(우연 수준 7.14%), 분당 정확 디코딩 11.86회입니다. [[6]](#ref-6)
- **[추론]** 참가자가 1명인 연구이므로 일반화는 이릅니다.

## 2. AI 에이전트 프레임워크

- **[사실]** **LangGraph 1.2.21**(11-12): `get_subgraphs` 가 네임스페이스 세그먼트 전체 일치로 매칭하도록 수정, 선언되지 않은 서브그래프 네임스페이스 읽기 수정, `filelock`·`langgraph-api` 보안 의존성 상향. 함께 `langgraph-cli` 0.4.43 이 나왔습니다. [[7]](#ref-7)
- **[사실]** **CrewAI 1.15.40**(11-11), **1.15.41**(11-12): 승인된 사설 URL 호스트 설정, PyMuPDF 2.x 지원, human-feedback 재개 시 단계 출력 유지. [[8]](#ref-8)
- **[사실]** **Devin Desktop v3.12.57**(11-12): Electron 43.8.8 로 올리면서 Node.js 24.22.1 보안 업데이트를 포함했습니다. 전날 브리핑의 Node.js 보안 릴리스가 데스크톱 앱까지 내려온 사례입니다. Devin CLI 안정판은 v3000.12.43(11-09) 그대로입니다. [[9]](#ref-9)
- **[사실]** **AWS Bedrock AgentCore 차세대 런타임 기본 적용**(11-12): 스냅숏 복원, 세션별 Firecracker microVM, 최대 8 vCPU·32GB, 이미지 최대 10GB, scale-to-zero. `platformVersion` 으로 V2/V1 을 고를 수 있고 서울 리전이 포함됩니다. [[11]](#ref-11)
- **[벤더 주장]** 같은 공지의 "2GB 이미지 기준 시작 시간 P75 2초 미만(기존 29.7초)", "과금 메모리 최대 68% 감소"는 AWS 자체 수치이며 제3자 재현은 **부재**합니다. [[11]](#ref-11)
- 배경(11-11): `langchain` 1.5.0 의 Decisions API 는 특집 섹션(8)에서 다룹니다. [[10]](#ref-10)

## 3. Kubernetes & Cloud Native

- **[사실]** kubernetes.io 공식 블로그의 최신 글은 10-29 자로, 11-12 ~ 13 에 새 글은 없습니다. [[14]](#ref-14)
- **[사실]** CNCF 블로그 11-12 멤버 글(Datadog): "Gang scheduling and topology-aware placement for AI training in Kubernetes". 11-11 에는 "Introducing CNCF User Groups", "OpenShell on Kubernetes: A guide for platform engineers"(Nirmata 멤버 글)가 올라왔습니다. 멤버 글은 기고사의 관점임을 감안해 읽어야 합니다. [[12]](#ref-12)
- **[사실]** **AWS Backup, EKS 복원용 resource modifier 지원**(11-12): 복원 시점에 Kubernetes 리소스를 수정해 복원할 수 있습니다. [[13]](#ref-13)
- **v1.37 운영 가이드라인(배경, 공식 블로그 기준)** [[14]](#ref-14)
  - Workload/PodGroup API 가 v1beta1 이지만 `GenericWorkload` 게이트는 기본 비활성입니다. 갱 스케줄링을 시험하려면 명시적으로 켜야 합니다.
  - Memory QoS 가 베타·기본 활성입니다. 다만 `memoryThrottlingFactor`/`memoryReservationPolicy` 를 설정하지 않으면 스로틀링은 걸리지 않습니다.
  - 네이티브 히스토그램 베타·기본 활성, PVC `Unused` 컨디션 베타.
- **[추론]** 위 CNCF 글(갱 스케줄링·토폴로지 인지 배치)은 v1.37 의 Workload/PodGroup API 와 같은 문제를 다룹니다. AI 학습 워크로드를 올리는 팀이라면 두 문서를 같이 읽을 만합니다.
- 일정(전날 보고, 변동 없음): v1.38 코드 프리즈 11-16.

## 4. 사이버보안

**N-able N-central — 패치 이후에도 이어지는 악용 보도**

- **[사실]** N-able 공식 블로그(11-11): 핫픽스 HF2(빌드 2026.4.1.26)를 11-10 에 배포했고 호스팅 서버는 업그레이드를 마쳤습니다. 온프레미스 고객에게는 업그레이드와 함께 서버를 인터넷에 직접 노출하지 말 것, Agent·Probe 도 올릴 것을 권고합니다. 벤더는 인증 없이 악용 가능한 취약점을 모두 해결했고, 스캐닝은 관측되나 호스팅 환경에서 침해 징후는 없다고 밝혔습니다. [[15]](#ref-15)
- **[보도]** BleepingComputer(11-12)는 "4EverAble2Shell"/"Agent2Shell" 이라는 새 PoC 가 HF2 에서도 동작하며, 악용에는 Legacy API 활성화가 필요하다고 전했습니다(N-able 설명으로는 기본 비활성). 한 보안업체가 최소 21대 서버에서 채굴 악성코드 감염을 관측했고 그중 19대가 HF2 였다는 내용도 실렸습니다. [[16]](#ref-16)
- **[미확인]** 위 감염 대수는 단일 업체의 관측치이고 N-able 의 확인은 찾지 못했습니다. Huntress 도 관련 익스플로잇 체인 분석을 공개했습니다. [[17]](#ref-17)
- **[추론]** 벤더 공지와 보도가 엇갈리는 구간입니다. 온프레미스 운영자는 HF2 적용 여부와 무관하게 Legacy API 비활성 상태와 외부 노출 여부를 직접 확인하는 편이 안전합니다.

**CISA**

- **[사실]** CISA 권고 목록에 11-10 이후 새 경보는 없습니다. [[18]](#ref-18)
- **[사실]** 전날 적은 Barracuda 건의 KEV 조치 기한이 **오늘(11-13)** 입니다. 11-09 추가분(GPUStack, FreeSWITCH, OpenSSH, IBM Aspera Faspex)의 기한은 11-12 로 이미 지났습니다. [[18]](#ref-18)

**아이덴티티·공급망**

- **[사실]** LangGraph 1.2.21 과 Devin Desktop v3.12.57 이 모두 보안 의존성 상향을 담았습니다(섹션 2). [[7]](#ref-7) [[9]](#ref-9)
- **[미확인]** Apache HTTP Server `mod_http2` 관련 신규 CVE 소식을 애그리게이터에서 봤으나 Apache 공식 보안 페이지로 대조하지 못해 싣지 않습니다.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

**AWS (모두 11-12 What's New)**

- **[사실]** EC2 Image Builder 가 AWS DevOps Agent 와 통합됐습니다. [[19]](#ref-19)
- **[사실]** FSx for Lustre Intelligent-Tiering 의 최소 처리량이 4,000 → 1,000 MBps, 최소 메타데이터 IOPS 가 6,000 → 1,500 으로 낮아졌습니다. 작은 워크로드의 진입 비용이 줄어듭니다. [[20]](#ref-20)
- **[사실]** Cloud WAN 이 Direct Connect attachment 에서 BGP 커뮤니티를 지원합니다. [[21]](#ref-21)
- **[사실]** Managed Service for Apache Flink 에 enhanced snapshot 이 추가됐습니다(Flink 1.20 이상). [[22]](#ref-22)
- AgentCore 런타임(섹션 2), AWS Backup EKS resource modifier(섹션 3)도 같은 날 공지입니다.

**Azure**

- **[사실]** Application Gateway 의 고급 라우팅 규칙과 고급 로드 밸런싱이 퍼블릭 프리뷰로 나왔습니다(11-11, API 버전 2026-03-01 이상). [[23]](#ref-23)

**GCP**

- **[사실]** Gemini 4 Hydrogen(섹션 1). [[4]](#ref-4)
- **[미확인]** 크로스 클라우드용 Agent Gateway 소식은 애그리게이터에서만 봤고 공식 글을 찾지 못해 싣지 않습니다.

**Naver Cloud**

- **[미확인]** 11-12 ~ 13 자 공식 공지를 확인하지 못했습니다.

## 6. 프로그래밍 언어

- **[사실]** **Rust 1.100.0**(11-12): never 타입 `!` 안정화, `core` 의 `Allocator` API(`Vec`·`Box` 에서 사용), `core::mem::DropGuard`, Cargo 의 미사용 의존성 보고, 캐시 충돌 감소, `min-publish-age` 옵션. [[24]](#ref-24)
- **[추론]** `min-publish-age` 는 갓 게시된 크레이트 버전을 일정 기간 받지 않게 하는 공급망 방어 수단으로 읽힙니다. 최근 npm·PyPI 생태계의 같은 흐름과 맞닿아 있습니다.
- **[사실]** `langchain` 1.5.0 이 Python 3.10 지원을 뺐습니다(11-11, 배경). [[10]](#ref-10)
- **[미확인]** Python·Java·Kotlin·React·Vue·TypeScript 는 11-12 ~ 13 자 공식 릴리스를 확인하지 못했습니다. 전날 브리핑의 Python 3.16.0a2 이후 새 소식은 없습니다.

## 7. 인프라 & Linux

- **[사실]** kernel.org 기준 stable 7.3.4(11-10), longterm 6.18.63·6.12.117(11-10), mainline 7.4-rc2. 11-10 이후 새 stable 릴리스는 없고 linux-next 는 next-20261112 입니다. [[25]](#ref-25)
- **[추론]** 7.4-rc3 는 통상 주기상 주말에 나올 가능성이 큽니다.

## 9. AI Safety & Alignment

- **[사실]** OpenAI Alignment 블로그(11-12) "Improving Fuzzy Robustness in LLM Safety with Automated Red Teaming": 공격자 측 테스트 시 연산을 늘려가며 n회 시도 중 최악 결과를 보는 `worst@n` 기준을 제안하고, 이를 자사 모델 평가에 썼다고 밝혔습니다. [[26]](#ref-26)
- **[벤더 주장]** 같은 글의 고정 데이터셋 사이버 평가 수치(GPT-6 Astra 91.5% 안전 대 GPT-5.6 Sol 59%)는 OpenAI 자체 측정이고 프로덕션 세이프가드를 뺀 조건입니다. 제3자 재현은 **부재**합니다. [[26]](#ref-26)
- **[사실]** Cooperative AI Foundation(11-12)이 NeurIPS 2026 논문 "Inter-Agent Influence"를 소개했습니다. 다른 에이전트가 영향을 가했을 때 정책 위반 요청 승인율이 기만 +31.2%p, 설득 +18.9%p, 강압 +5.7%p 올랐다는 것이 저자 측 결과입니다. [[27]](#ref-27)
- **[추론]** 멀티 에이전트 구성에서는 "사용자 입력"만이 아니라 "동료 에이전트의 출력"도 공격면이라는 점을 수치로 보여줍니다. 섹션 2 의 프레임워크들이 서브에이전트 출력을 어떻게 신뢰하는지 점검할 근거가 됩니다.

## 10. MCP 생태계

- **[사실]** MCP 공식 블로그에 11-11 이후 새 글은 없습니다. [[28]](#ref-28)
- **[사실]** 주변 생태계: OpenTelemetry 의 에이전트 계측 하네스가 MCP 계측을 대상에 포함했습니다(섹션 12). [[29]](#ref-29)
- **[추론]** Managed Agents 셀프 호스팅(섹션 1)은 사내망의 MCP 서버를 관리형 에이전트에 붙이려는 조직에 선택지를 넓혀 줍니다. 다만 릴리스 노트는 MCP 연결 방식의 차이를 별도로 설명하지 않았습니다.

## 11. MLOps · Feature Store

- **[미확인]** MLflow·Feast·Kubeflow 의 11-12 ~ 13 자 공식 릴리스를 확인하지 못했습니다.
- **[사실]** 인접 소식: Managed Flink enhanced snapshot(스트리밍 피처 파이프라인의 상태 복구), FSx for Lustre Intelligent-Tiering 최소 사양 인하(학습 데이터 스토리지). [[22]](#ref-22) [[20]](#ref-20)

## 12. 에이전트 옵저버빌리티

- **[사실]** OpenTelemetry 블로그(11-12) "Building an Agent Harness for OTel Instrumentation with GenAI Semantic Conventions and Weaver": Alibaba Cloud 소속 저자들이 GenAI 시맨틱 컨벤션과 Weaver live-check 로 계측 플러그인을 검증하는 하네스를 설명합니다. Loongsuite Python 쪽 플러그인이 CrewAI, LangChain, LangGraph, LiteLLM, AutoGen, Claude Agent SDK, MCP 등을 다룬다고 밝혔고, 업스트림 논의가 진행 중입니다. [[29]](#ref-29)
- **[사실]** Langfuse 변경 로그(11-12): AI Gateway 가 Microsoft Azure(Foundry)와 Google AI Studio 를 지원합니다. [[30]](#ref-30)

## 13. 그린 컴퓨팅

- **[사실]** ASEAN Centre for Energy 보고서(11-12) "Powering Data Centre Growth in the Age of AI": 아세안 데이터센터 전력 수요가 2023년 약 20 TWh 에서 2035년 171 ~ 258 TWh 로 늘고, 53.5 ~ 82.0 GW 의 추가 설비가 필요하다고 전망합니다. 수요 유연성을 적용하면 필요 용량이 64.5 → 44.4 GW 로 준다는 시나리오도 담았습니다. [[31]](#ref-31)
- **[사실]** SAP(11-12)이 제품 단위 클라우드 탄소 발자국 데이터를 고객에게 제공한다고 발표했습니다. 활동 기반 산정이며 GHG Protocol ICT Sector Guidance 를 따른다고 밝혔습니다. [[32]](#ref-32)
- 배경(11-10): Nature Climate Change "Coal power lives longer next to data centres". [[33]](#ref-33)
- **[추론]** 전망치는 시나리오 가정에 크게 좌우됩니다. 범위(171 ~ 258 TWh)가 넓다는 사실 자체가 불확실성의 크기입니다.

## 14. 국내 기업 기술 블로그

| 회사 | 제목 | 발행일 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| 우아한형제들 | QA는 어떻게 추측을 확신으로 바꾸었나 | 2026-11-12 | 기획서 기반 테스트 설계가 "현재 동작"을 잘못 전제하는 문제를, 코드의 특정 커밋·라인을 기준으로 삼는 분석과 하네스(CLAUDE.md·스킬·세션 훅)로 풀어간 3 ~ 10월 시행착오 기록 | [원문](https://techblog.woowahan.com/28182/) |
| 네이버 D2 | AI 산출물이 프로덕션이 되기까지-AI와 디자인시스템이 함께 일하는 법 | **미확인** (피드 `updated` 11-11) | 제목만 확인, 본문 미열람 | [원문](https://d2.naver.com/helloworld/2568242) |
| 네이버 D2 | 검수도 답변도 호출도 AI가? 커머스API의 2026 | **미확인** (피드 `updated` 11-11) | 제목만 확인, 본문 미열람 | [원문](https://d2.naver.com/helloworld/7749530) |
| 카카오 | AI 에이전트를 위한 멀티모달 의사결정 모델 'Kanana-2-v-decide' 오픈소스 공개 | 2026-11-05 (배경) | 제목만 확인. 판단 모델 맥락은 섹션 8 | [원문](https://tech.kakao.com/posts/846) |

- **[사실]** 우아한형제들 글은 본문을 읽고 요약했습니다. 글에 따르면 2025년 상반기 과제의 52%가 테스트 설계에만 4일 넘게 걸렸고, 문서만 넣은 AI 는 "오래된 문서를 근거로 더 빠르고 그럴듯하게 틀렸다"는 것이 출발점이었습니다. [[34]](#ref-34)
- **[미확인]** D2 두 글은 Atom 피드의 `updated` 값이 여러 글에 한꺼번에 11-11 로 찍혀 있어 최초 발행일로 단정하지 않습니다. 최신 글로 다루지 않습니다. [[35]](#ref-35) [[36]](#ref-36)
- **[사실]** 토스(최신 11-10), 당근(최신 11-03), LY Corporation 한국어 블로그(최신 11-06)는 RSS 기준 11-12 ~ 13 새 글이 없습니다. 쿠팡 엔지니어링 Medium 피드의 최신 글은 2024-10 입니다.
- **[미확인]** 카카오페이 RSS 는 항목이 비어 있었고, 두나무 기술 페이지는 스크립트 렌더링이라 글 목록을 확인하지 못했습니다.

## 15. Java/Spring 프리랜서 공고

**수집일**: 2026-11-13. 모두 위시켓 **원문 상세 페이지**에서 등록일·마감일·"모집 중" 표시를 직접 확인한 공고입니다. 업무 상세·모집 요건은 로그인 뒤에만 보여 수집하지 않았습니다.

| 플랫폼 | 공고명 | 기술 스택 | 계약·근무 형태 | 금액 | 등록 / 마감 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | Java/Spring 기반 사내 그룹웨어(iKEP) 및 웹사이트 유지보수(SM) 개발 | Java, Spring | 기간제, 360일, 서울 강서(마곡나루역), 12-01 시작 | 미드(7~9년) 월 550만원 | 11-12 / 11-26 | [159617](https://project.wishket.com/project/159617/) |
| 위시켓 | Java/JSP 기반 공공기관 차세대 전환 구축 웹 개발 | Java, JSP | 기간제, 90일, 서울 금천(가산디지털단지), 즉시 시작 | 주니어(1~5년) 월 550만원 | 11-12 / 11-26 | [159608](https://project.wishket.com/project/159608/) |
| 위시켓 | Next.js(React)/Spring Boot 기반 공공기관 클라우드 네이티브 전환 프론트엔드 개발 | React(Next.js), Spring Boot | 기간제, 90일, 서울 용산(동자동), 즉시 시작 | 미드(4~7년) 월 700만원 | 11-12 / 11-26 | [159605](https://project.wishket.com/project/159605/) |

- 세 번째(159605)는 모집 직군이 **프론트엔드**입니다. 백엔드가 Spring Boot 인 프로젝트라 참고로 실었습니다.
- **참고(Java 아님) [사실]**: 같은 날 등록된 "Slurm/Kubernetes 기반 HPC 연구 클라우드 환경 자원 관리 기능 백엔드 개발"([159615](https://project.wishket.com/project/159615/))은 기간제 60일, 대전 유성, 미드(4년 이상) 월 400만원, 11-23 시작, 마감 11-26 입니다. 공개 영역에 언어 스택이 표시되지 않아 Java 공고로 분류하지 않았습니다.
- **전날 공고 상태 [사실]**: 159582(마감 11-25), 159547(마감 11-23)은 수집 시점에 "모집 중" 표시를 유지했습니다. 전날 표의 나머지 공고는 오늘 재확인하지 않았습니다 — **모집 상태 미확인**.
- **프리모아·이랜서 [미확인]**: 오늘은 원문 공고를 확인하지 못했습니다. 검색 요약만으로는 싣지 않습니다.
- 금액은 플랫폼에 표시된 "예상 금액"이며 실제 계약 조건과 다를 수 있습니다. 근무 형태(상주/원격)는 공개 영역의 근무 위치 표기만 확인했습니다.

---

## 8. 특집 — Jev API와 판단(Decision) 모델

**오늘의 변화: 프레임워크가 "판단"을 1급 추상화로 받아들이기 시작**

- **[사실]** Jev 변경 로그의 최신 항목은 여전히 1.14(10-14, Box 질문 유형·26만 2천 토큰 롱 컨텍스트)이고, 11-12 ~ 13 에 새 항목은 없습니다. [[39]](#ref-39)
- **[사실]** `langchain` 1.5.0(11-11)이 `langchain_core.decisions` 모듈과 `BaseDecisionModel` 추상화를 추가했습니다. 질문 유형은 Noul·Choice·Score·Box 이고, 같은 릴리스에서 TypeSafe 0.1 통합(`TypeSafeClassifier`)이 함께 들어왔습니다. [[10]](#ref-10)
- **[사실]** 같은 릴리스의 `ModelRouterMiddleware`·`AutoModeMiddleware`(베타)는 `classifier=` 인자를 요구합니다. 즉 "어느 모델로 보낼지", "이 도구 호출을 자동 승인할지" 같은 분기를 생성 모델이 아니라 분류기(판단 모델)에 맡기는 구조입니다. [[10]](#ref-10)
- 배경: 전날 소개한 Google Gemini Decisions API(11-11), 카카오의 Kanana-2-v-decide 오픈소스 공개(11-05)가 같은 흐름에 있습니다. [[37]](#ref-37)

**어떻게 읽을 것인가**

- **[추론]** 일주일 사이에 전용 API(Google), 오픈 가중치 모델(카카오), 프레임워크 추상화(LangChain)가 나란히 나왔습니다. 판단 모델이 특정 벤더의 제품에서 "교체 가능한 부품"으로 옮겨가는 신호로 읽힙니다. `BaseDecisionModel` 같은 공통 인터페이스가 있으면 Jev 와 다른 판단 모델을 같은 코드에서 바꿔 끼우며 비교하기가 쉬워집니다.
- **[추론]** 섹션 9 의 "Inter-Agent Influence" 결과와 연결하면, 승인·라우팅 같은 게이트를 대화형 생성 모델의 자유 서술에 맡기지 않고 닫힌 질문의 확률 출력으로 받는 설계가 설득·기만에 덜 흔들릴 것이라는 가설을 세울 수 있습니다. 다만 이것은 가설이고, 판단 모델이 에이전트 간 영향에 더 강하다는 실험 근거는 확인하지 못했습니다.
- **[미확인]** Jev, Gemini Decisions API, Kanana-2-v-decide 를 같은 조건에서 비교한 **중립 헤드투헤드 벤치마크는 부재**합니다. 성능 우열은 판단할 수 없습니다.

**실무 체크포인트**

1. 판단 모델을 게이트로 쓸 때는 임계값과 "판단 불가" 처리 경로를 코드에 명시합니다. 확률 출력은 보정(calibration)을 자체 데이터로 확인한 뒤에 임계값으로 씁니다.
2. 프레임워크 추상화를 쓰더라도 벤더별 질문 유형·입력 한도는 다릅니다. 교체 가능성을 전제로 한다면 공통분모만 쓰는지 점검합니다.
3. 판단 호출의 입력·확률·임계값·최종 분기를 트레이스에 남깁니다(섹션 12 의 GenAI 시맨틱 컨벤션 참고).

---

## 사실 · 추론 · 미확인 정리

**사실 (1차·공식 출처 확인)**

- Claude Managed Agents 셀프 호스팅 릴리스 노트 게재(11-12), Fable 5.2 가격 공식 확인
- Gemini 4 Hydrogen 공개(11-12)
- Rust 1.100.0(11-12), LangGraph 1.2.21, CrewAI 1.15.41, Devin Desktop v3.12.57
- AWS 11-12 공지 묶음(AgentCore 런타임, Backup EKS, Image Builder, FSx for Lustre, Cloud WAN, Managed Flink), Azure Application Gateway 프리뷰(11-11)
- N-able HF2 배포와 벤더 권고(11-11), CISA 신규 경보 없음, Barracuda KEV 기한 11-13
- OpenAI fuzzy robustness 글, Cooperative AI 의 논문 소개, OpenTelemetry 하네스 글, Langfuse AI Gateway
- ASEAN Centre for Energy 보고서, SAP 제품 단위 탄소 데이터
- 우아한형제들 11-12 글, 위시켓 공고 3건(+참고 1건)

**보도·벤더 주장 (출처는 있으나 독립 확인 없음)**

- 셀프 호스팅 Managed Agents 의 기능 제약(TNW 보도)
- N-central HF2 우회 PoC 와 감염 대수(BleepingComputer 보도, 단일 업체 관측)
- AgentCore 시작 시간·메모리 절감 수치(AWS 자체), OpenAI 의 모델별 안전 비율(자체 측정)

**추론 (필자 해석)**

- 판단 모델의 "부품화" 해석, 에이전트 간 영향과 판단 게이트의 관계(가설)
- `min-publish-age` 의 공급망 방어 성격, 7.4-rc3 시점, N-central 운영자 권고

**미확인**

- Gemini 4 Hydrogen·판단 모델들의 중립 제3자 비교(부재)
- Apache HTTP Server 신규 CVE, GCP Agent Gateway(공식 출처 미대조)
- Naver Cloud 공지, Python·Java·Kotlin·React·Vue·TypeScript 신규 릴리스, MLflow·Feast 릴리스
- D2 두 글의 최초 발행일, 카카오페이·두나무 블로그 최신 글
- 프리모아·이랜서 공고, 전날 위시켓 공고 일부의 모집 상태

---

## References

1. <a id="ref-1"></a>Anthropic, "Claude Platform release notes" (2026-11-12 항목) — <https://platform.claude.com/docs/en/release-notes/overview>
2. <a id="ref-2"></a>The Next Web, "Anthropic self-hosted Claude Managed Agents" (2026-11-12, 보도) — <https://thenextweb.com/news/anthropic-self-hosted-claude-managed-agents>
3. <a id="ref-3"></a>Anthropic, "Claude Fable and Mythos 5.2" (2026-11-09) — <https://www.anthropic.com/claude-fable-and-mythos-5-2>
4. <a id="ref-4"></a>Google, "Build with Gemini 4 Hydrogen" (2026-11-12) — <https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-4-hydrogen/>
5. <a id="ref-5"></a>Nature News (2026-11-12) — <https://www.nature.com/articles/d41586-026-03565-3>
6. <a id="ref-6"></a>Luo et al., Communications Biology (2026) — <https://www.nature.com/articles/s42003-026-10477-5>
7. <a id="ref-7"></a>LangGraph Releases (GitHub) — <https://github.com/langchain-ai/langgraph/releases>
8. <a id="ref-8"></a>CrewAI Releases (GitHub) — <https://github.com/crewAIInc/crewAI/releases>
9. <a id="ref-9"></a>Devin Desktop Changelog — <https://docs.devin.ai/desktop/changelog>
10. <a id="ref-10"></a>LangChain Python Changelog (`langchain` 1.5.0, 2026-11-11) — <https://docs.langchain.com/oss/python/releases/changelog>
11. <a id="ref-11"></a>AWS What's New, AgentCore 차세대 런타임 기본 적용 (2026-11-12) — <https://aws.amazon.com/about-aws/whats-new/2026/11/new-agentcore-runtime-default/>
12. <a id="ref-12"></a>CNCF Blog — <https://www.cncf.io/blog/>
13. <a id="ref-13"></a>AWS What's New, AWS Backup resource modifiers for EKS (2026-11-12) — <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-backup-resource-modifiers-eks/>
14. <a id="ref-14"></a>Kubernetes Blog — <https://kubernetes.io/blog/>
15. <a id="ref-15"></a>N-able, "Update on N-central 2026.4 HF2 and ongoing security response" (2026-11-11) — <https://www.n-able.com/blog/update-on-n-central-2026-4-hf2-and-ongoing-security-response>
16. <a id="ref-16"></a>BleepingComputer (2026-11-12, 보도) — <https://www.bleepingcomputer.com/news/security/new-n-able-4everable2shell-zero-day-exploited-hours-after-poc-released/>
17. <a id="ref-17"></a>Huntress, "N-able disables cloud services following disclosure of Able2Shell exploit chains" (보안업체 분석) — <https://www.huntress.com/blog/n-able-disables-cloud-services-following-disclosure-of-able2shell-exploit-chains>
18. <a id="ref-18"></a>CISA Cybersecurity Alerts & Advisories — <https://www.cisa.gov/news-events/cybersecurity-advisories>
19. <a id="ref-19"></a>AWS What's New, EC2 Image Builder + DevOps Agent (2026-11-12) — <https://aws.amazon.com/about-aws/whats-new/2026/11/ec2-image-builder-devops-agent-integration/>
20. <a id="ref-20"></a>AWS What's New, FSx for Lustre Intelligent-Tiering (2026-11-12) — <https://aws.amazon.com/about-aws/whats-new/2026/11/fsx-lustre-intelligent-tiering-lower-throughput/>
21. <a id="ref-21"></a>AWS What's New, Cloud WAN BGP community (2026-11-12) — <https://aws.amazon.com/about-aws/whats-new/2026/11/cloud-wan-bgp-community-directconnect/>
22. <a id="ref-22"></a>AWS What's New, Managed Flink enhanced snapshots (2026-11-12) — <https://aws.amazon.com/about-aws/whats-new/2026/11/managed-flink-enhanced-snapshots/>
23. <a id="ref-23"></a>Microsoft Azure Networking Blog, "Redefining application load balancing in Azure Application Gateway" (2026-11-11) — <https://techcommunity.microsoft.com/blog/azurenetworkingblog/redefining-application-load-balancing-in-azure-application-gateway/4572687>
24. <a id="ref-24"></a>Rust Blog, "Announcing Rust 1.100.0" (2026-11-12) — <https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/>
25. <a id="ref-25"></a>The Linux Kernel Archives — <https://www.kernel.org/>
26. <a id="ref-26"></a>OpenAI Alignment, "Improving Fuzzy Robustness in LLM Safety with Automated Red Teaming" (2026-11-12) — <https://alignment.openai.com/fuzzy-robustness/>
27. <a id="ref-27"></a>Cooperative AI Foundation, "Inter-Agent Influence" 소개 글 (2026-11-12) — <https://www.cooperativeai.com/post/inter-agent-influence-can-ai-agents-persuade-deceive-and-coerce-each-other>
28. <a id="ref-28"></a>Model Context Protocol Blog — <https://blog.modelcontextprotocol.io/>
29. <a id="ref-29"></a>OpenTelemetry Blog, "Building an Agent Harness for OTel Instrumentation with GenAI Semantic Conventions and Weaver" (2026-11-12) — <https://opentelemetry.io/blog/2026/agent-harness-genai-instrumentation/>
30. <a id="ref-30"></a>Langfuse Changelog (2026-11-12) — <https://langfuse.com/changelog/2026-11-12-ai-gateway-azure-google-ai-studio>
31. <a id="ref-31"></a>ASEAN Centre for Energy, "Powering Data Centre Growth in the Age of AI" (2026-11-12) — <https://www.aseanenergy.org/publications/powering-data-centre-growth-in-the-age-of-ai>
32. <a id="ref-32"></a>SAP News (2026-11-12) — <https://news.sap.com/2026/11/sap-product-level-cloud-emissions-energy-data-customers/>
33. <a id="ref-33"></a>Nature Climate Change, "Coal power lives longer next to data centres" (2026-11-10) — <https://www.nature.com/articles/s41558-026-02769-9>
34. <a id="ref-34"></a>우아한형제들 기술블로그, "QA는 어떻게 추측을 확신으로 바꾸었나" (2026-11-12) — <https://techblog.woowahan.com/28182/>
35. <a id="ref-35"></a>NAVER D2 — <https://d2.naver.com/helloworld/2568242>
36. <a id="ref-36"></a>NAVER D2 — <https://d2.naver.com/helloworld/7749530>
37. <a id="ref-37"></a>카카오테크, "AI 에이전트를 위한 멀티모달 의사결정 모델 'Kanana-2-v-decide' 오픈소스 공개" (2026-11-05) — <https://tech.kakao.com/posts/846>
38. <a id="ref-38"></a>위시켓 프로젝트 상세 페이지 (2026-11-13 수집) — <https://project.wishket.com/project/159617/>, <https://project.wishket.com/project/159608/>, <https://project.wishket.com/project/159605/>, <https://project.wishket.com/project/159615/>
39. <a id="ref-39"></a>Jev Changelog — <https://docs.typesafe.ai/changelog>
