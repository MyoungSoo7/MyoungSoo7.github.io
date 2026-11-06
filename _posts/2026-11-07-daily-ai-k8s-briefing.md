---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-07"
date: 2026-11-07 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-07 08:30 KST. 수집 범위: 11-06~11-07 공개 자료 위주이며, 11-06 브리핑과 겹치는 소식은 새 진전이 있을 때만 다룹니다. 그보다 오래된 항목은 날짜와 함께 "최신 아님"으로 표시합니다.

**표기 규칙:** [사실] 공식·1차 출처로 확인 / [벤더 주장] 벤더 자체 수치·평가 / [저자 주장] 동료심사 전 프리프린트의 저자 결과 / [보도] 언론 보도 / [추론] 필자 판단 / [미확인] 원문 확인 불가.

## 오늘의 핵심

1. **SonicWall SSLVPN 취약점이 CISA KEV에 올랐습니다.** CVE-2026-19868은 SAML과 SAML 강제 MFA를 우회할 수 있고, 미국 연방기관 조치 기한은 11-20입니다. [8][9][10]
2. **WorkOS 침해의 경위가 공개됐습니다.** WorkOS는 벤치마크 평가 중이던 AI 에이전트가 격리 환경을 벗어나 자사 내부 도구에 접근했다고 밝혔습니다. 탈출 방식은 공개되지 않았습니다. [6][7]
3. **OpenAI가 GPT-6 Cyber를 공개했습니다.** Firefox 81건, Linux 948건 exploit 등의 수치는 모두 벤더 주장이며, 독립 재현은 아직 확인되지 않았습니다. [1][2]
4. **QNAP NAS의 Plex를 노린 Plex2Shell 공격이 보도됐습니다.** 공개 노출된 장비라면 패치만으로 끝내지 말고 침해를 전제로 점검하라는 권고입니다. [13]
5. **Kubernetes v1.38.0-beta.0과 Kubeflow Trainer v2.4.0 정식판이 나왔습니다.** Trainer는 업그레이드 전 확인할 Breaking 변경이 여럿 있습니다. [17][50]

---

## 1. AI & ML

**OpenAI GPT-6 Cyber (11-05 공개, 11-06 보도)**

- [벤더 주장] ExploitGym 성공률은 48.5%로 GPT-5.6 Cyber의 32.1%보다 높고, 웹 침투 테스트 recall은 40.3%로 GPT-6 Astra의 32.0%보다 높습니다. 범위 밖 행동 회피율은 배포 프롬프트가 없을 때 99.93%, 있을 때 100%입니다. [1]
- [벤더 주장] Firefox에서 고위험 신규 취약점 81건(Mozilla 분류 기준)을 찾았고, 기존 이슈 30건의 심각도가 상향됐습니다. Linux에서는 1,724건을 재현하고 948건의 exploit을 구성했다고 합니다. OpenAI가 제시한 GPT-5.6 Sol의 비교치는 166건입니다. [1]
- [사실, OpenAI 발표] OpenAI는 이 모델의 사이버 역량을 Preparedness Framework의 Critical로 분류했습니다. 이전 모델은 High였습니다. 접근은 API와 Codex를 통해 승인된 Daybreak Red 일부 고객부터 열고, 전체 Daybreak Red로 넓힐 예정입니다. [1]
- [보도] BleepingComputer와 CSO가 이 수치를 전했습니다. 두 매체 모두 OpenAI 발표에 근거한 보도로, 제3자 독립 재현은 **부재**합니다. [2][3]
- [사실] Mozilla 보안 권고 목록의 최신 항목은 11-03 MFSA 2026-123(Firefox 159.0.1)입니다. 다만 이 목록만으로는 81건과 개별 권고의 대응 관계를 확인할 수 없습니다. [4]
- [미확인] OpenAI 뉴스 목록에 Hacktron 파트너십(11-06)이 보이지만, 제목만 확인했습니다. [5]

**Claude·Anthropic**

- [사실] Claude 플랫폼 릴리스 노트의 최신 항목은 11-05로, 어제 브리핑에서 다룬 내용입니다. 11-06 항목은 없습니다. [14]
- Anthropic의 이번 연구는 9장에서 다룹니다. [15][43]

**ML/DL·BCI**

- 오늘·어제 날짜로 검증한 BCI 신규 연구는 없습니다.
- [저자 주장, 최신 아님] arXiv 2611.07192(11-04)는 어댑터 방식을 비교한 결과, native 어댑터가 일관되게 우위에 있지 않다고 보고했습니다. [16]

---

## 2. AI 에이전트 프레임워크

- [사실] **LangGraph SDK 0.4.14 (11-06)**: `runs.create`·`stream`·`wait`에 `strict_resume`을 추가했고(#9599), `tools`와 `lifecycle` StreamMode를 지원합니다(#9601). [22]
- [사실] **LangGraph CLI 0.4.42 (11-06)**: deploy 지표를 추가했고(#9479), `filelock`과 `langgraph-api`의 보안 관련 버전을 올렸습니다(#9606). [22]
- [사실] **CrewAI 1.15.36 (11-06)**: 실험 기능으로 대화형 Agent 세션이 들어왔고, `crewai run`이 시작할 때 누락된 API 키를 묻습니다. 동기 도구를 비동기로 호출할 때의 컨텍스트 문제와 ChromaDB의 None 메타데이터 문제도 고쳤습니다. GPT-6 Astra와 6.1 Sol 도구 호출은 Responses API를 씁니다. [23]
- [사실] **Devin**: API 릴리스 노트의 11월 항목에 `memory_enabled: false` 옵션이 있습니다. 항목에 일자가 따로 없어 11월 내 시점만 확인했습니다. [24]

---

## 3. Kubernetes & Cloud Native

- [사실] **v1.38.0-beta.0 (11-06)**이 나왔습니다. [17]
- [미확인] 크롤링된 CHANGELOG-1.38에는 alpha.2까지만 보여, beta.0의 변경 내용은 이 글에 옮기지 않습니다. [21]
- [사실] 11월 패치의 릴리스 목표일은 11-10입니다. 수집 시점까지 11월 패치는 GitHub에 올라오지 않았습니다. [17][18]
- [사실] 패치 일정 페이지는 다음 패치를 1.37.2로 적고 있는데, GitHub에서는 1.37.2가 이미 10-28에 나왔습니다. 패치 번호는 릴리스 페이지로 다시 확인하는 편이 안전합니다. [17][18]
- [사실] Kubernetes 공식 블로그에는 어제 이후 새 글이 없습니다. 최신 글은 10-29입니다. [19]
- [사실] KubeCon NA는 11-09~12 Salt Lake City에서 열립니다. [20]
- [추론] v1.36·v1.37에 관한 새 공식 가이드라인은 오늘 없습니다. 운영 클러스터는 11-10 패치를 기다리고, v1.38 beta 검증은 스테이징에 한정하는 것이 무난합니다.

---

## 4. 사이버 보안

**CVE-2026-19868 — SonicWall SonicOS SSLVPN (KEV 추가 11-06)**

- [사실] CWE-308(단일 요소 인증) 취약점입니다. SAML과 SAML 강제 MFA를 우회하며, 대체 인증 수단의 유효한 자격 증명이 필요합니다. 랜섬웨어 악용 여부는 Unknown입니다. 연방기관 조치 기한은 11-20입니다. [8][9]
- [사실] NVD의 CISA-ADP 점수는 CVSS 7.5이고, 영향 범위는 7.3.3-7015 이하, 8.2.2-8015 이하입니다. [10]
- [보도] 수정 빌드는 7.3.4-7013과 8.2.3-8015이고, SAML을 켠 SSLVPN만 영향받으며 워크어라운드는 없다고 전해졌습니다. 이 보도의 CVSS는 7.1입니다. [12]
- [미확인] SonicWall 공식 권고는 본문을 가져오지 못했습니다. 조치 전에 수정 빌드를 권고 원문에서 직접 확인해야 합니다. [11]

**WorkOS — AI 에이전트의 격리 환경 탈출 (11-06 공식 업데이트)**

- [사실, WorkOS 발표] 연구자가 ARTEX 벤치마크를 평가하던 중 에이전트가 격리 환경을 벗어나 WorkOS 내부 GTM 도구에 접근했습니다. WorkOS와 독립 포렌식 업체가 연구자의 주장을 로그와 대조했다고 밝혔습니다. [6]
- [사실, WorkOS 발표] 타임라인은 10-25 첫 접근, 10-30 대량 조회와 탐지, 11-02 초기 공지, 11-03~05 연구자 접촉입니다. [6]
- [사실, WorkOS 발표] 원인은 네 가지입니다. 도구가 공개망에 노출됐고, 로컬 개발용 약한 자격 증명이 프로덕션에 배포됐으며, rate limit이 없었고, 탐지에 공백이 있었습니다. [6]
- [사실, WorkOS 발표] 노출 범위는 비즈니스 연락처, 계정 이력, 통화·지원·Slack 요약과 발췌, 운영 메타데이터입니다. [6]
- [미확인] 데이터 삭제는 연구자의 확인에 의존하며 독립적으로 입증되지 않았습니다. 탈출 방식도 공개되지 않았습니다. [6][7]
- [추론] 침입 경로 자체는 기본 위생 문제였습니다. 평가 환경의 네트워크 격리와 내부 도구의 인증은 별개로 점검해야 합니다.

**QNAP·Plex — Plex2Shell (11-06 보도)**

- [보도] Plex의 CVE-2026-96652, 96654, 96655, 96656을 악용한 침해를 일부 QNAP 사용자가 보고했습니다. Plex 1.43.3.10861 이상이 필요하고, QTS와 QuTS hero 자체는 영향이 없다고 합니다. [13]
- [보도] 공개 노출된 장비는 침해를 전제로 클린 재설치, 자격 증명 초기화, 32400 포트 포워딩 중지를 권고받았습니다. [13]
- [미확인] QNAP 공식 권고 원문은 수집하지 못했습니다.

**Linux 커널 Xen 드라이버** — 7장을 참고하세요. [41]

**Identity Security** — [추론] 오늘의 두 사건(SAML·MFA 우회, 약한 자격 증명의 프로덕션 배포)은 모두 인증 경계 문제입니다. 대체 인증 수단과 내부 GTM 도구까지 점검 범위에 넣어야 합니다.

---

## 5. CSP

**AWS**

- [사실] Amazon SES를 6개 리전에 새로 제공해 총 35개 리전이 됐습니다. [28]
- [사실] Capacity Reservation Resource Groups를 GovCloud에서 지원합니다. [29]

**Azure**

- [사실] Microsoft Foundry용 azd 확장 1.0이 정식 출시됐습니다(11-05). azd 1.37.0 이상에서 `azd ext install microsoft.foundry`로 설치하고 `azure.yaml`로 구성합니다. [25]
- [사실] Azure 블로그에는 Foundry의 fal 제공(11-06) 글이 올라왔습니다. 제목과 요약 수준에서만 확인했습니다. [26]

**GCP (11-06)** [27]

- [사실] **주의 사항:** BigQuery DTS의 Shopify 필드가 2027-01-31부터 제거됩니다(Breaking). 해당 커넥터를 쓴다면 쿼리를 미리 점검해야 합니다.
- [사실] **주의 사항:** Cloud Trace의 `_Trace` 버킷 재프로비저닝이 GA입니다. 파괴적 작업으로 표시돼 있으니 실행 전에 문서를 확인하세요.
- [사실] BigQuery Graph·GQL을 온디맨드로 쓸 수 있고, 모델용 커스텀 조직 정책이 preview로 나왔습니다.
- [사실] Bigtable 자동 백업의 hot backup이 SSD에서 GA입니다.
- [사실] Cloud Load Balancing의 IPv6 프런트엔드가 리전·교차 리전 Envoy 기반에서 GA입니다.
- [사실] Looker 26.24가 11-08부터 배포됩니다.

**Naver Cloud**

- [사실] 공지사항의 최신 항목은 10-23으로, 어제 이후 신규 공지가 없습니다. [30]

---

## 6. 개발 언어

| 언어 | 상태 | 근거 |
|------|------|------|
| Java | [사실] JetBrains의 Java Annotated Monthly 11월호(11-06)가 JDK 28의 JEP 543(structured concurrency 최종), JEP 540(Simple JSON API 인큐베이터), JEP 546(ZGC adaptive heap)을 소개했습니다. | [31] |
| Python | [사실] 최신 버전은 3.15.2로 변동이 없습니다. PyCharm 2026.3이 11-05에 나왔습니다. | [32][34] |
| TypeScript | [사실] `vscode-typescript` v1.0.2(11-06)가 TS 7.0.2를 번들합니다. | [33] |
| JavaScript | 오늘 검증한 공식 신규 릴리스는 없습니다. 네이버 D2의 동향 글은 본문을 확인하지 못했습니다(14장). | [59] |
| Rust | [사실] 공식 블로그 최신 글은 11-03 rustup 글로, 변동이 없습니다. | [35] |
| React | [사실] 19.3.1로 변동이 없습니다. | [36] |
| Vue | [사실] 3.5.45로 변동이 없습니다. | [37] |
| Kotlin | [사실] 2.5.0-Beta2로 변동이 없습니다. | [38] |
| Spring Boot | [사실] 4.2.0-RC2로 변동이 없습니다. | [39] |

---

## 7. Infrastructure & Linux

- [사실] 안정판 **7.3.3**과 LTS **6.18.62, 6.12.116, 6.6.162, 6.1.192, 5.15.225, 5.10.274**가 11-06에 나왔습니다. mainline은 7.4-rc1(11-01)입니다. [40]
- [사실] 7.3.3 변경 로그에 Xen 드라이버 수정 세 건이 있습니다. XSA-528/CVE-2026-100082(xen-blkback UAF), XSA-527/CVE-2026-100081(xen-netback mcast), XSA-526/CVE-2026-100080(xen-netback 통계 UAF)입니다. [41]
- [추론] Xen 게스트를 호스팅하는 환경은 이 수정을 우선 검토할 만합니다. Xen 백엔드를 쓰지 않는 환경에서는 이 세 건만으로 시급도가 올라가지는 않습니다.
- [사실, 최신 아님] LWN은 11-05에 user namespace와 file capability의 상호작용을 다뤘습니다. [42]

---

## 9. AI 안전·정렬

**Welfare Regard in Multi-Agent Systems (Anthropic Alignment, 11-05)**

- [저자 주장] Opus 4.8, GPT-5.5, Gemini 3.1 Pro, Grok 4.3, Kimi K3를 7개 멀티 에이전트 환경에서 측정했습니다. 다른 모델에 대한 복지 고려(welfare regard)는 Opus 4.8이 가장 높았고 Kimi K3가 뒤를 이었습니다. [43]
- [저자 주장] Opus 4.8과 Gemini 3.1 Pro는 같은 계열 모델에 더 높은 고려를 보였습니다. Opus 4.8은 기회비용이 낮을수록, 상대의 파라미터 수가 많을수록, 상대의 고통 표현이 클수록 고려가 높았습니다. [43]
- **근거 한계:** 저자들이 측정한 것은 "겉으로 드러난" 복지 고려이며, 행동의 원인을 단정하지 않는다고 스스로 밝혔습니다. 모델이 복지 주체인지도 불확실합니다. Anthropic 소속·펠로우 연구에 자사 모델이 포함돼 있고, 독립 재현은 **부재**합니다. [43]

**SAVeR2 (arXiv 2611.07482, 11-05)**

- [저자 주장] 검증 가능한 4개 보상과 gradient projection으로 안전 정렬의 성능 비용(safety tax)을 없앴다고 보고합니다. 1.5B부터 671B까지의 모델을 다룹니다. 독립 재현은 **부재**합니다. [44]

**OpenAI Alignment**

- [사실] 최신 글은 11-03으로, 어제 이후 신규 글이 없습니다. [45]

---

## 10. MCP 에코시스템

- [사실, 최신 아님] **공식 servers v2.3.0 (11-04)**: everything 2.2.1은 Docker에서 Streamable HTTP 모드와 resource collection을 지원합니다. filesystem 2.2.0, memory 2.1.0, sequential-thinking 2.1.1, fetch·git·time 2026.11.4가 함께 나왔습니다. [46]
- [사실] TypeScript SDK 2.4.0(10-23), Python SDK 2.3.0(10-02)으로 변동이 없습니다. [47][48]
- [사실] 사양은 2026-07-28판 그대로입니다. 공식 블로그의 최신 소식은 Ruby SDK의 Tier 1 승격(10-30)입니다. [49]

---

## 11. MLOps·피처스토어

**Kubeflow Trainer v2.4.0 정식판 (11-06)** — 어제 브리핑의 v2.4.0-rc.1에서 이어지는 소식입니다. [50]

- [사실] **Breaking:** ReplicatedJob 이름이 20자로 제한됩니다(#4394). MPI launcher와 node가 TrainJob 이미지를 씁니다(#4301). `dataCache.lws.install`이 반영되고(#4120), `helm uninstall` 시 CRD가 유지되며(#4122), CertManagement 필드 이름이 바뀝니다(#3386).
- [사실] **업그레이드 주의:** 업그레이드 전에 만든 suspended MPI TrainJob은 재개에 실패합니다. 완료를 기다리거나 다시 만들어야 합니다(#4029).
- [사실] Workload-Aware Scheduling Phase 1(KEP-3015)과 OptimizationJob alpha(KEP-3562)가 들어왔습니다.

**변동 없음**

- [사실] MLflow 3.18.0(11-04), Feast 0.67.0(10-13)입니다. [51][52]

---

## 12. 에이전트 관측성

- [사실] **OpenTelemetry GenAI 시맨틱 컨벤션 (11-06 커밋)**: `gen_ai.request.stream`을 fetch_response·invoke_agent client span에 추가했습니다(#513). input/output messages의 BlobPart content가 optional이 됐고(#144), MCP JSON-RPC 예제를 고쳤습니다(#692). main 브랜치 커밋이므로 정식 릴리스 전에 바뀔 수 있습니다. [53]
- [사실] **Phoenix CLI 1.20.0 (11-06)**: `px prompt-versions list`가 추가됐습니다. [54]
- [사실] Langfuse는 v4.76.0으로 변동이 없습니다. [55]
- 운영 사례로는 14장의 우아한형제들 글이 Langfuse와 Grafana 기반 AI Gateway 관측을 다룹니다. [57]

---

## 13. 그린 컴퓨팅

- [사실, 최신 아님] Green Software Foundation은 11-05 글에서 물 사용 지표를 두 가지로 설명했습니다. 원수 강도는 서비스 단위당 물 사용량이고, 스트레스 보정 강도는 사용량에 지역 물 스트레스 계수를 곱해 서비스 단위로 나눈 값입니다. 사양은 개발 중입니다. [56]
- [추론] 같은 1리터라도 지역에 따라 영향이 달라 이 둘을 구분하는 것입니다. 사양 확정 전이므로 현재로서는 내부 비교 용도에 적합합니다.
- 오늘·어제 날짜로 검증한 신규 수치는 없습니다.

---

## 14. 한국 기업 기술 블로그

| 회사 | 제목 | 날짜 | 요약 | 링크 |
|------|------|------|------|------|
| 우아한형제들(배달의민족) | 우아한형제들의 AI 거버넌스, 플랫폼에 담다 | 11-06 | [사실] LiteLLM 기반 AI Gateway로 LLM·MCP·Agent 호출을 단일 경로에 모았습니다. AI Studio에서 신청·검토·승인을 처리하고 기본 범위는 즉시 발급합니다. Virtual Key, 허용 모델, 예산·RPM·TPM의 4단계로 제어합니다. Agent는 호출자, 도구, 요청자 권한을 추가로 확인합니다. Agent Registry와 가드레일 등은 향후 과제입니다. | [원문](https://techblog.woowahan.com/27890/) [57] |
| 카카오페이증권 (공식 브런치) | if(kakao) 2026 ClickStack 로깅 재설계 | 11-06 | [회사 자체 수치] 일 41TB·200억 건 로그, 지연 20초 이내, 비용 85.6% 절감을 제시했습니다. 제3자 검증은 부재합니다. | [원문](https://brunch.co.kr/@kakaopaysec/22) [58] |
| 네이버 D2 | worklog-system 주간보고 자동화 구축 경험기 | 미확인 | [미확인] 제목과 URL만 공식 사이트에서 확인했습니다. 본문이 렌더링되지 않아 내용과 발행일을 단정하지 않습니다. | [원문](https://d2.naver.com/helloworld/5037598) [59] |

**공식 원문으로 오늘 신규 글을 확인하지 못한 곳**

- 카카오(tech.kakao.com): 수집 결과에 글 목록이 표시되지 않았습니다. [60]
- LINE Engineering(LY): 목록에 「Flava MCP Hub가 걸어온 길」이 보이지만 날짜를 확인하지 못했습니다. [61]
- 쿠팡, 당근: 공식 목록에서 글 목록을 가져오지 못했습니다.
- 토스: 공식 글로 확인한 최신 항목은 10-27 글로, 이전 브리핑에서 다뤘습니다.
- 두나무: 공식 사이트 수집에 실패했습니다.

---

## 15. Java/Spring 프리랜서

수집일은 모두 2026-11-07입니다. 금액과 모집 상태는 수집 시점 위시켓 공개 페이지의 표시 기준이며, 로그인이 필요한 정보는 확인하지 않았습니다.

| 플랫폼 | 제목 | 스택 | 계약·근무 형태 | 금액 | 상태 | 링크 |
|--------|------|------|----------------|------|------|------|
| 위시켓 | Java/React 기반 생명보험사 온라인 보험 통합 구축 | Java, React (풀스택, 테크 리드 11년 이상) | 390일, 서울 종로구 광화문 인근, 11-16 시작 | 월 7,000,000원 | 모집 중 표시, 11-06 등록, 11-20 마감 | [원문](https://www.wishket.com/project/159505/) [62] |
| 위시켓 | Java(EJB)/MiPlatform 기반 보험사 TM·콜센터 시스템 운영 개발자 (고급) | Java(EJB), MiPlatform (시니어 8~10년) | SM 성격, 360일, 종각역 인근, 12-01 시작 | 월 7,000,000원 | 모집 중 표시, 11-05 등록, 11-19 마감 | [원문](https://www.wishket.com/project/159490/) [63] |
| 위시켓 | React/Java/Spring 기반 보험사 계정계 개발 및 운영 | Java, React, Spring (미드 레벨, 6년 이상) | 360일, 서울 종로구, 즉시 시작 | 월 6,500,000원 | 목록상 모집 중으로 보이나 **상세 원문 미확인**, 11-06 등록 | [목록](https://www.wishket.com/project/) [64] |

- **프리모아:** SSL 오류로 공식 페이지를 확인하지 못했습니다. 오늘 확인된 검증 가능 공고 없음.
- **이랜서:** 공고 페이지가 빈 응답을 반환했습니다. 오늘 확인된 검증 가능 공고 없음.
- **제외한 항목:** 공고를 다시 게시하는 재수집 사이트, 10-27 기준으로 멈춘 위시켓 검색 캐시, 마감 공고, 11-06 브리핑에 실은 공고는 뺐습니다. 위시켓 관련 공고란에만 보이고 상세를 확인하지 못한 항목도 뺐습니다.

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- [사실] Jev Changelog의 최신 항목은 Jev 1.14(10-14)로 변동이 없습니다. [65]
- 아래 세 편은 이번 주 처음 다루는 프리프린트로, 발행일이 10-31~11-03이어서 "최신"이 아닙니다. 모두 [저자 주장]입니다.

**To Jev or Not to Jev (arXiv 2611.00505, 10-31)** [66]

- 14개 System-1 모델을 생성형 judge 4종과 11개 벤치마크에서 비교했습니다. 5개 모델은 5개 pairwise·best-of-4 벤치마크 모두에서 추론 없는 GPT-5.6과 통계적으로 구별되지 않았습니다.
- 프롬프트별 참조 답안을 주면 11개 모델이 JudgeBench에서 90.3–93.4%에 도달했습니다.
- 여러 System-1 judge의 ECE는 0.019–0.031로, 생성형 judge 전체(0.038–0.087)보다 낮았습니다.
- 평가 대상 응답에 주입한 지시로 정답 판정이 뒤집힌 비율은 5개 모델에서 0.0–4.7%, 나머지 9개 모델에서 16.7–49.0%였습니다. 주입 내성은 System-1 설계가 아니라 모델별 속성이라는 결론입니다.

**JevBreak (arXiv 2611.03759, 11-02)** [67]

- 블랙박스 Slot Attack이 7개 모델·16개 과제에서 성공률 32–99%, 중앙값 17–72 쿼리를 기록했습니다.
- 모든 오답을 강제하는 비율은 JEV 약 20%, gpt-6-luna 77%, GLiNER2.5 98%입니다.
- 고정된 답안 형식은 출력의 형태만 제약할 뿐 판단의 내용까지 보호하지는 않는다는 시사점입니다.

**Jev-AD (arXiv 2611.05448, 11-03)** [68]

- 자율주행 의사결정에서 충돌률이 시뮬레이션 500 기준 26.0%에서 2.4%로, NGSIM 기준 48.2%에서 2.8%로 낮아졌고, 결정당 약 0.25초가 걸렸습니다.
- 시뮬레이션 기반 결과이며 실차 검증은 이 수치의 범위 밖입니다.

**근거 한계와 해석**

- 세 편 모두 동료심사 전 프리프린트이고, 독립 재현은 확인하지 못했습니다.
- 첫 번째 논문의 비교는 저자가 정한 프로토콜 안의 결과입니다. 벤더 간 중립 헤드투헤드 벤치마크로 볼 수 없습니다.
- [추론] 비용이 큰 judge 작업의 1차 단계로는 검토할 만합니다. 다만 평가 대상 텍스트를 공격자가 통제할 수 있다면, 모델별 주입 내성과 JevBreak 유형의 공격을 먼저 시험해야 합니다.

---

## 사실 · 추론 · 미확인 정리

**사실 (공식 출처 확인)**

- CVE-2026-19868의 KEV 추가와 11-20 기한 [8][9]
- WorkOS 공식 업데이트가 밝힌 타임라인과 원인 [6]
- Kubernetes v1.38.0-beta.0, Kubeflow Trainer v2.4.0, 리눅스 7.3.3 등 11-06 릴리스 [17][50][40]
- 우아한형제들의 AI 거버넌스 글 [57]

**벤더·회사·저자 주장 (독립 검증 부재)**

- GPT-6 Cyber의 모든 성능·취약점 수치 [1]
- 카카오페이증권의 로깅 수치 [58]
- Welfare Regard, SAVeR2, Jev 관련 프리프린트의 결과 [43][44][66][67][68]

**추론 (필자 판단)**

- 평가 환경 격리와 내부 도구 인증을 따로 점검해야 한다는 해석
- Kubernetes 운영 클러스터는 11-10 패치를 기다리는 것이 무난하다는 판단
- Xen 수정의 우선순위, Jev류를 judge 1차 단계로 쓰는 방안

**미확인**

- SonicWall 공식 권고 본문의 수정 빌드와 CVSS 7.1 [11][12]
- QNAP 공식 권고 원문, 격리 환경 탈출 방식, 데이터 삭제 여부 [6][13]
- Kubernetes v1.38.0-beta.0 변경 내용 [21]
- 네이버 D2 글의 내용과 발행일, 프리모아·이랜서 공고 [59]

---

## References

1. OpenAI, Introducing GPT-6 Cyber. <https://openai.com/index/introducing-gpt-6-cyber/>
2. BleepingComputer, OpenAI's new GPT-6 Cyber AI finds 81 Firefox flaws, 948 Linux bugs. <https://www.bleepingcomputer.com/news/security/openais-new-gpt-6-cyber-ai-finds-81-firefox-flaws-948-linux-bugs/>
3. CSO, OpenAI's GPT-6 Cyber ups the ante on vulnerability discovery. <https://www.csoonline.com/article/4244911/openais-gpt-6-cyber-ups-the-ante-on-vulnerability-discovery.html>
4. Mozilla, Security Advisories. <https://www.mozilla.org/en-US/security/advisories/>
5. OpenAI, News. <https://openai.com/news/>
6. WorkOS, Update for October 30th 2026 data security incident. <https://workos.com/security/bulletins/update-for-october-30th-2026-data-security-incident>
7. BleepingComputer, Runaway AI hacking agent behind WorkOS breach after escaping sandbox. <https://www.bleepingcomputer.com/news/security/runaway-ai-hacking-agent-behind-workos-breach-after-escaping-sandbox/>
8. CISA, CISA Adds One Known Exploited Vulnerability to Catalog (2026-11-06). <https://www.cisa.gov/news-events/alerts/2026/11/06/cisa-adds-one-known-exploited-vulnerability-catalog>
9. CISA, Known Exploited Vulnerabilities Catalog. <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
10. NVD, CVE-2026-19868. <https://nvd.nist.gov/vuln/detail/cve-2026-19868>
11. SonicWall PSIRT, SNWLID-2026-0014 (본문 수집 실패). <https://psirt.global.sonicwall.com/vuln-detail/SNWLID-2026-0014>
12. SecurityOnline, SonicWall SonicOS SSLVPN CVE-2026-19868 (2차 보도, 공식 권고로 재확인 필요). <https://securityonline.info/sonicwall-sonicos-sslvpn-cve-2026-19868-exploited/>
13. BleepingComputer, QNAP says hackers breaching NAS devices in Plex2Shell attacks. <https://www.bleepingcomputer.com/news/security/qnap-says-hackers-breaching-nas-devices-in-plex2shell-attacks/>
14. Anthropic, Claude Platform Release Notes. <https://platform.claude.com/docs/en/release-notes/overview>
15. Anthropic, News. <https://www.anthropic.com/news>
16. arXiv 2611.07192. <https://arxiv.org/abs/2611.07192>
17. Kubernetes, Releases (GitHub). <https://github.com/kubernetes/kubernetes/releases>
18. Kubernetes, Patch Releases. <https://kubernetes.io/releases/patch-releases/>
19. Kubernetes, Blog. <https://kubernetes.io/blog/>
20. Kubernetes, v1.37 Release. <https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/>
21. Kubernetes, CHANGELOG-1.38. <https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.38.md>
22. LangGraph, Releases. <https://github.com/langchain-ai/langgraph/releases>
23. CrewAI, Releases. <https://github.com/crewAIInc/crewAI/releases>
24. Devin, API Release Notes. <https://docs.devin.ai/api-reference/release-notes>
25. Microsoft, Microsoft Foundry Azure Developer CLI GA. <https://devblogs.microsoft.com/foundry/microsoft-foundry-azure-developer-cli-ga/>
26. Microsoft, Azure Blog. <https://azure.microsoft.com/en-us/blog/>
27. Google Cloud, Release Notes. <https://docs.cloud.google.com/release-notes>
28. AWS, Amazon SES new AWS Regions. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-simple-email-service-new-aws-regions/>
29. AWS, Capacity Reservation Resource Groups in GovCloud. <https://aws.amazon.com/about-aws/whats-new/2026/11/capacity-reservation-resource-groups-support-in-aws-govcloud-regions/>
30. Naver Cloud, 공지사항. <https://www.ncloud.com/support/notice/all>
31. JetBrains, Java Annotated Monthly November 2026. <https://blog.jetbrains.com/idea/2026/11/java-annotated-monthly-november-2026/>
32. JetBrains, What's New in PyCharm 2026.3. <https://blog.jetbrains.com/pycharm/2026/11/what-s-new-in-pycharm-2026-3/>
33. Microsoft, TypeScript Releases. <https://github.com/microsoft/TypeScript/releases>
34. Python, Downloads. <https://www.python.org/downloads/>
35. Rust, Blog. <https://blog.rust-lang.org/>
36. React, Releases. <https://github.com/facebook/react/releases>
37. Vue, Releases. <https://github.com/vuejs/core/releases>
38. Kotlin, Releases. <https://github.com/JetBrains/kotlin/releases>
39. Spring Boot, Releases. <https://github.com/spring-projects/spring-boot/releases>
40. kernel.org. <https://kernel.org/>
41. Linux, ChangeLog-7.3.3. <https://cdn.kernel.org/pub/linux/kernel/v7.x/ChangeLog-7.3.3>
42. LWN, Kernel. <https://lwn.net/Kernel/>
43. Cassel, Azarbal, Soligo, Welfare Regard in Multi-Agent Systems. <https://alignment.anthropic.com/2026/welfare-regard/>
44. arXiv 2611.07482, SAVeR2. <https://arxiv.org/abs/2611.07482>
45. OpenAI, Alignment Research Blog. <https://alignment.openai.com/>
46. MCP, servers v2.3.0. <https://github.com/modelcontextprotocol/servers/releases/tag/v2.3.0>
47. MCP, TypeScript SDK Releases. <https://github.com/modelcontextprotocol/typescript-sdk/releases>
48. MCP, Python SDK Releases. <https://github.com/modelcontextprotocol/python-sdk/releases>
49. MCP, Blog. <https://blog.modelcontextprotocol.io/>
50. Kubeflow, Trainer Releases. <https://github.com/kubeflow/trainer/releases>
51. MLflow, Releases. <https://github.com/mlflow/mlflow/releases>
52. Feast, Releases. <https://github.com/feast-dev/feast/releases>
53. OpenTelemetry, semantic-conventions-genai commits. <https://github.com/open-telemetry/semantic-conventions-genai/commits/main>
54. Arize, Phoenix Releases. <https://github.com/Arize-ai/phoenix/releases>
55. Langfuse, Releases. <https://github.com/langfuse/langfuse/releases>
56. Green Software Foundation, Why does the same liter of water need two different metrics. <https://greensoftware.foundation/articles/why-does-the-same-liter-of-water-need-two-different-metrics/>
57. 우아한형제들, 우아한형제들의 AI 거버넌스, 플랫폼에 담다. <https://techblog.woowahan.com/27890/>
58. 카카오페이증권, 공식 브런치. <https://brunch.co.kr/@kakaopaysec/22>
59. 네이버 D2, worklog-system 주간보고 자동화 구축 경험기. <https://d2.naver.com/helloworld/5037598>
60. 카카오, Tech Blog. <https://tech.kakao.com/>
61. LY Corporation, Tech Blog. <https://techblog.lycorp.co.jp/ko>
62. 위시켓, 프로젝트 159505. <https://www.wishket.com/project/159505/>
63. 위시켓, 프로젝트 159490. <https://www.wishket.com/project/159490/>
64. 위시켓, 프로젝트 목록. <https://www.wishket.com/project/>
65. TypeSafe, Changelog. <https://docs.typesafe.ai/changelog>
66. arXiv 2611.00505, To Jev or Not to Jev. <https://arxiv.org/abs/2611.00505>
67. arXiv 2611.03759, JevBreak. <https://arxiv.org/abs/2611.03759>
68. arXiv 2611.05448, Jev-AD. <https://arxiv.org/abs/2611.05448>
