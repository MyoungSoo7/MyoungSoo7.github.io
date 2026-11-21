---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-22"
date: 2026-11-22 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> **기준 시각**: 2026-11-22 08:30 KST · **수집 범위**: 2026-11-20 ~ 2026-11-21 (일부 항목은 날짜를 따로 적음)
> **표기**: **[사실]** 1차·공식 출처로 확인 · **[보도]** 언론 보도(1차 출처 미공개 부분 포함) · **[벤더 주장]** 벤더 자체 발표·수치 · **[추론]** 필자 해석 · **[미확인]** 텍스트로 검증하지 못함

> **중복 안내**: 어제(11-21) 브리핑에서 다룬 Anthropic IPO 첫날, vCenter CVE-2026-123890, MCP servers v2.5.0, Claude Code v2.1.330, LangGraph 1.2.24, CrewAI 1.15.44, AWS T9g·S3 Vectors, GCP UAP, Nature Sustainability 데이터센터 탄소 연구 등은 **새 진척이 있을 때만** 다시 적었습니다.

## 오늘의 핵심

1. **리만 가설(RH·GRH)의 Lean 형식 증명 발표** — Anthropic의 Levent Alpöge가 Claude와 함께 찾았다는 증명을 공개했습니다. Lean·Mathlib 커뮤니티는 공동 성명을 내고 형식 검증 결과를 "full confidence"로 확인했습니다 [사실]. 다만 사람이 읽을 수 있는 해설과 동료심사는 아직 진행 중입니다.
2. **Ruby2Shell(CVE-2026-132825)과 GitLab 긴급 패치** — Ruby가 Regexp·String 취약점 7건을 고친 4.0.10, 3.4.13, 3.3.14를 냈고, GitLab도 19.6.1, 19.5.8, 19.4.10을 배포했습니다 [사실].
3. **GnuPG GPGME CVE-2026-129975(double free)** — GPGME 2.3.1, 1.24.4와 Gpg4win 5.1.2로 수정됐습니다. Ruby2Shell 여파로 공개가 앞당겨졌습니다 [사실].
4. **CISA KEV 11-20 추가분이 1차 카탈로그에서 확인됨** — Cisco Expressway, SAP NetWeaver, VMware vCenter, Apache Roller 4건이며 조치 기한은 11-23입니다 [사실]. 어제 적은 "1차 미확인"은 이것으로 해소됐습니다.
5. **CloudWatch Container Insights for EKS의 OSS 워크로드 내장 모니터링** — Karpenter, KEDA, vLLM, KServe, SGLang, Ray, Knative를 지원합니다 [사실]. 같은 시기 GKE ambient networking도 GA가 됐습니다 [사실].
6. **프리랜서** — 11-21(토)에 등록된 신규 공고는 확인되지 않았습니다. 미게재 공고 2건을 등록일과 함께 정리했습니다.

---

## 1. AI/ML (Claude·ML/DL·뇌과학/BCI)

### 1-1. 리만 가설 Lean 형식 증명 — Claude와 함께 발견 (11-20~21)

- **[사실] 1차 노트**: Anthropic 기술 스태프 Levent Alpöge가 `remark.pdf`를 공개했습니다 [[1]](#ref-1).
  - 내용은 Claude와 함께 리만 가설(RH)과 일반화 리만 가설(GRH)의 증명을 찾았고, 그 증명을 Lean으로 형식화했다는 것입니다.
  - 노트에 따르면 방법론은 함수체(function field)에서 쓰던 Stepanov 계열 접근에서 나왔고, 약 √X번의 반복 theta lift를 씁니다.
  - 작업 기간은 약 6주이며, 노트의 타임라인은 2026-10-06 ~ 11-16입니다.
- **[사실] Lean 커뮤니티 공동 성명** (2026-11-21) [[2]](#ref-2):
  - Lean과 Mathlib 커뮤니티 명의이며, Lean FRO와 Mathlib Initiative가 지지했습니다.
  - 증명은 약 1,700만 줄이고 Mathlib에만 의존합니다.
  - Lean 커널과 독립 체커(con-leche, con-ron 등)로 검사했고, 증명이 옳다고 "full confidence"를 표명했습니다.
- **[사실] 독립 재검증** — Michael Rubinstein(University of Waterloo) [[3]](#ref-3):
  - 175,187개 모듈에 대해 4가지 검사를 11-21에 모두 통과했습니다. 여기에는 두 번째 커널인 nanoda(선언 1,484,729개 검사)도 포함됩니다.
  - 증명은 표준 공리 3개에만 의존합니다.
  - 164쪽 분량의 해설 초안(working draft)도 함께 공개됐습니다.
- **[사실] 컴파일 산출물 호스팅** — Proofs & Reasons [[4]](#ref-4):
  - Lean v4.33.1 기준이며, 컴파일에 약 530 CPU-시간이 걸렸습니다.
  - 호스팅이 증명을 보증하는 것은 아니라고 명시했습니다.
- **[보도] 언론**:
  - Guardian [[5]](#ref-5)과 AP [[6]](#ref-6)가 11-21에 보도했습니다. AP는 4쪽짜리 노트라는 점, 그리고 "최근 몇 달 사이 AI와 연관된 그룹이 유명 난제 해결을 주장한 두 번째 사례"라는 점을 짚었습니다.
  - Scientific American은 11-20 기사 제목에서 "독립 수학자들이 거의 확실히 참이라고 확인"했다고 적었습니다 [[7]](#ref-7). 본문은 확인하지 못해 제목만 인용합니다.
- **[추론] 해석**:
  - "Lean 커널이 받아들인 형식 증명"이라는 점은 여러 독립 체커로 확인된 사실입니다.
  - 남은 쟁점은 두 가지입니다. ① 형식 명제가 고전적 RH 진술과 정확히 같은지 사람이 검토하는 일과 ② 수학적 아이디어를 사람이 이해할 수 있게 정리하는 일입니다.
  - 동료심사 논문은 아직 **부재**합니다.

### 1-2. Anthropic 상장 후속 (11-21) [보도]

- CNBC 보도 [[8]](#ref-8): 목요일 시가 $111.50 → 금요일 종가 $88.91. 같은 주는 2020년 이후 기술주 최악의 한 주였다고 보도했습니다.
- 시가총액은 매체마다 다릅니다(NPR과 CNBC 수치 불일치). 그래서 이 글에는 싣지 않습니다 [미확인].

### 1-3. ML/DL·뇌과학/BCI

- 11-20~21에 1차 출처로 확인한 신규 항목은 없습니다.

## 2. 에이전트 프레임워크 (LangGraph·CrewAI·Devin)

- **[사실] 신규 릴리스 없음**: LangGraph는 1.2.24(11-20), CrewAI는 1.15.44(11-19), Claude Code는 v2.1.330이 최신입니다. 모두 어제 다뤘습니다.
- **[사실] Devin Bots** (Cognition, **11-17 발표 — 최신 아님**) [[9]](#ref-9):
  - 여러 Devin 세션을 이끄는 상주형 에이전트로, 메모리를 갖고 "목표"를 맡습니다.
  - 사례로 Android 앱을 44일 동안 만들었다고 밝혔습니다. **[벤더 주장]** PR 1,134건 병합, Kotlin 344,651줄. 중립적 재현은 **부재**합니다.
- **[보도] 경쟁 구도**: Fortune은 이 제품을 OpenAI Dots, Anthropic Duet과 같은 "상주형 에이전트" 경쟁으로 보도했습니다 [[10]](#ref-10).
- **[추론]** 이번 주 흐름은 단건 작업 위임에서 "결과(outcome) 소유" 에이전트로 넘어가는 쪽입니다. 그만큼 권한 범위, 예산 상한, 사람 승인 지점을 설계하는 일이 운영의 핵심 과제가 됩니다.

## 3. Kubernetes v1.36 / v1.37

- **[사실] 패치 신규 없음**: 1.37.2와 1.36.6(10-28)이 최신 패치이고, 개발 라인은 v1.38.0-beta.0(11-06)입니다. kubernetes.io 블로그에는 11-16(kube-proxy IPVS 제거) 이후 새 글이 없습니다.
- **[사실] GKE ambient networking GA** (Google Cloud, 11-20) [[11]](#ref-11):
  - 사이드카 없는 서비스 메시를 GA로 올렸습니다. 노드 단위 공유 컴포넌트와 관리형 컨트롤 플레인을 씁니다.
  - mTLS와 인가 정책을 지원하고, L4·L7 지표를 제공합니다. 지표는 함께 나온 Network Services Monitoring에서 봅니다.
- **[추론]** IPVS 제거와 ambient 메시 GA가 겹치면서, 클러스터 네트워크 스택을 정리할 이유가 늘었습니다. 1.38 업그레이드를 계획할 때 kube-proxy 모드와 메시 데이터플레인을 함께 점검하는 것이 좋겠습니다.

## 4. 보안

### 4-1. Ruby2Shell — CVE-2026-132825 외 (Ruby 11-18, GitLab 11-20)

- **[사실] Ruby 공식 권고** [[12]](#ref-12):
  - Regexp·String 취약점 7건을 고쳤고, 수정 버전은 4.0.10, 3.4.13, 3.3.14입니다.
  - RCE PoC가 존재합니다.
  - Ruby 3.2 이하는 EOL이라 수정이 제공되지 않습니다.
  - GHSA 4건의 크레딧에 "Stephan Lipp (Ada Logics) and Anthropic"이 올라 있습니다.
- **[사실] GitLab 긴급 패치** 19.6.1, 19.5.8, 19.4.10 (11-20) [[13]](#ref-13). 직접 컴파일해 설치했다면 Ruby도 다시 빌드해야 합니다.
- **[보도/연구자 발표]** 연구자 페이지 [[14]](#ref-14):
  - 원인은 ISO-8859·Windows-125x 인코딩에서 `ß`를 대문자로 바꾸는 루프가 1바이트만 경계 검사하는 데 있습니다. UTF-8은 영향을 받지 않는다고 설명합니다.
  - GitHub Enterprise Server 3.22.5 이하는 11-21 03:52 UTC 기준으로 아직 수정이 없다고 적었습니다.

### 4-2. GnuPG GPGME — CVE-2026-129975 (11-20)

- **[사실] 공지 내용** (Werner Koch 공지 [[15]](#ref-15), 작업 페이지 [[16]](#ref-16)):
  - 조작된 매우 긴 user ID를 읽을 때 double free가 일어납니다. 데이터 유출이 가능하고, RCE도 배제할 수 없다고 했습니다.
  - GPGME 2.3.0 이전 전 버전이 영향을 받습니다. 공지는 메일 클라이언트, XMPP 클라이언트, Samba, Flatpak을 영향 범위로 들었습니다.
  - 수정은 GPGME 2.3.1, 레거시 1.24.4, Gpg4win 5.1.2이고, 구버전용 패치도 첨부됐습니다.
  - 원래 11-25 공개 예정이었으나 Ruby2Shell 때문에 앞당겼습니다.
- **[사실] 배포판**: Debian은 DSA-6646-1과 DLA-4924-1을 냈습니다 [[17]](#ref-17).
- **[보도] 악용 여부**: 악용 보고는 없다고 보도됐습니다 [[18]](#ref-18).

### 4-3. CISA KEV — 2026-11-20 추가분 (Due 2026-11-23) [사실]

CISA 카탈로그에서 다음 4건을 직접 확인했습니다 [[19]](#ref-19).

| CVE | 제품 | 비고 |
| --- | --- | --- |
| CVE-2026-76466 | Cisco Expressway | BOD 26-04에 따라 포렌식 트리아지 요구 |
| CVE-2025-42884 | SAP NetWeaver | — |
| CVE-2026-123890 | VMware vCenter | 어제 다룬 항목의 KEV 편입 확인 |
| CVE-2026-129448 | Apache Roller | — |

- **[보도] Cisco Expressway 대응**: 수정 버전은 X15.5.20입니다. 신뢰된 클러스터 노드가 아니면 TCP 4371·4372를 차단하라는 권고가 함께 보도됐습니다.

## 5. CSP (AWS·Azure·GCP·Naver Cloud)

- **[사실] AWS (11-21)**:
  - AWS Quick plugins: 에이전트, 스킬, 커넥터, 플로우를 묶어 배포할 수 있습니다 [[20]](#ref-20).
  - AWS Quick 새 웹 경험, 브라우저 확장, Microsoft 365 애드인 [[21]](#ref-21).
  - Amazon Bedrock Web Search: 5개 언어와 `country` 필드를 추가했습니다 [[22]](#ref-22).
- **[사실] AWS (11-20)**:
  - Network Firewall 자동 인터넷 방화벽, 프리뷰 [[23]](#ref-23).
  - Billing and Cost Management Data Hub, 프리뷰. CUR 2.0 기반이며 13개월치를 제공합니다 [[24]](#ref-24).
  - AWS Quick의 멀티에이전트 오케스트레이션과 프롬프트 가드레일(프리뷰) [[25]](#ref-25).
- **[사실] GCP**: GKE ambient networking GA(3장 참조). 11-17에는 Cross-Cloud Interconnect for Azure 프리뷰가 나왔습니다 [[26]](#ref-26). Azure 쪽에서는 같은 날 Multicloud Interconnect를 AWS 대상 GA, GCP 대상 프리뷰로 발표했습니다 [[27]](#ref-27). 두 건 모두 11-17 발표라 최신은 아닙니다.
- **[미확인]** MSK Kafka 4.2, CloudWatch PromQL 30일 범위 등은 애그리게이터에서만 봤고 1차 URL을 확인하지 못해 싣지 않았습니다.
- **Azure·Naver Cloud**: 11-21에 1차 출처로 확인한 신규 공지는 없습니다.

## 6. 언어

- **[사실] Ruby 4.0.10, 3.4.13, 3.3.14**는 보안 릴리스입니다(4-1 참조). 운영 중인 Ruby 3.2 이하는 EOL이라 업그레이드 외에 방법이 없습니다.
- **Java·Spring·Go·Rust·Python**: 11-20~21에 1차 출처로 확인한 신규 릴리스는 없습니다. Reactor 2026.0.0은 어제 다뤘습니다.

## 7. 인프라·Linux

- **[사실] Debian**: GPGME 보안 업데이트 DSA-6646-1과 DLA-4924-1이 나왔습니다 [[17]](#ref-17). 데스크톱 메일 클라이언트, Samba, Flatpak 호스트는 우선 반영 대상입니다.
- **[추론] 패치 우선순위**: 이번 주말에는 ① KEV 기한(11-23)이 걸린 Expressway·vCenter·NetWeaver·Roller, ② Ruby 인터프리터를 번들하는 서비스(GitLab, 자체 빌드 Rails), ③ GPGME 링크 패키지 순으로 처리하는 것이 합리적입니다.

---

## 8. [특집] Jev API와 의사결정 모델

- **[사실] 신규 릴리스 없음**: Jev 공식 문서는 "Updated 2026-09-24"이고, 모델은 `jev-1.13` / `jev-latest`입니다 [[28]](#ref-28). 엔드포인트는 `POST /api/v1/decisions`이며 Noul·Choice·Score 유형을 지원합니다. 어제 적은 changelog 최신 1.14(10-14) 이후 새 항목은 확인되지 않았습니다. changelog 페이지는 오늘 수집되지 않았습니다.
- **[사실] 국내 참고 사례 — 최신 아님**: 토스 기술 블로그 「손가락 튕기기로 LLM 비용 줄이기」(2026-10-27) [[29]](#ref-29).
  - SNAP은 요청을 사내 소형 모델로 먼저 보내고, 신뢰도가 임계값보다 낮으면 LLM으로 넘기는 라우팅입니다.
  - 글은 앞으로 "JEV처럼 특정 판단 문제에 맞춘 Decision Engine"을 실험하겠다고 언급합니다.
  - **[벤더 주장]** 목표 일치율 99.9%에서 커버리지 34.74%, 약 6일간 입력 토큰 약 76억 개를 절감했다고 밝혔습니다. 외부 재현은 **부재**합니다.
- **[사실] 참고 — 최신 아님**: 카카오 「Kanana-2-v-decide」(11-06)도 판단 특화 모델 계열의 국내 사례입니다.
- **[추론]** 범용 LLM 앞에 "판단 전용" 모델이나 API를 두고 신뢰도로 폴백하는 구조가 비용 최적화의 표준 패턴이 되어 가고 있습니다. 도입할 때는 일치율 기준(정답 대비 vs LLM 대비)을 무엇으로 잡았는지부터 확인해야 합니다.

---

## 9. AI Safety

- **[보도] Anthropic 상장과 안전 약속** (NPR, 11-21) [[30]](#ref-30):
  - 비판론자들은 상장이 안전 약속을 시험대에 올린다고 지적했습니다.
  - 보도에 실린 Dario Amodei의 발언은 학습·배포 속도를 스스로 조절하고 "business nor political pressure"에 굴하지 않겠다는 취지입니다.
- **[사실] 형식 검증과 AI 산출물 신뢰**: 리만 가설 사례에서 커뮤니티는 AI가 만든 1,700만 줄 증명을 "사람의 신뢰" 대신 여러 독립 커널로 검증했습니다 [[2]](#ref-2)[[3]](#ref-3).
- **[추론]** 위 사례는 AI 산출물을 검증 가능한 형식으로 받는 접근의 대표 사례로 볼 수 있습니다. 반대로 형식 명제가 의도한 진술과 같은지 확인하는 "명세 검증"이 새 병목이 됩니다.
- **[사실] 보안 연구 크레딧**: Ruby 권고에서 Anthropic이 취약점 공동 발견자로 이름을 올렸습니다 [[12]](#ref-12). 발견 방법은 공개되지 않았습니다 [미확인].

## 10. MCP

- **[사실] 사양 변경 없음**: 최신 사양은 2026-07-28이고, servers v2.5.0은 어제 다뤘습니다.
- **[사실] 참고 — 최신 아님**: Azure SRE Agent는 AWS 커넥터에서 AWS MCP Server의 도구를 쓰고, 인증은 키 대신 ID 페더레이션으로 처리합니다 (11-18, 퍼블릭 프리뷰) [[31]](#ref-31).

## 11. MLOps·피처 스토어

- **[사실] CloudWatch Container Insights for EKS** (11-20) [[32]](#ref-32)[[33]](#ref-33):
  - vLLM, KServe, SGLang, Ray, Karpenter, KEDA, Knative 모니터링이 내장됐습니다.
  - add-on 또는 Helm 8.0.0 이상이 필요합니다. 공지에 따르면 OTel 수집 요금은 GB당 $0.08입니다.
- **[추론]** 추론 서버(vLLM·SGLang)와 오토스케일러(Karpenter·KEDA)를 한 화면에서 보게 되면 GPU 비용과 지연을 같은 대시보드에서 상관 분석할 수 있습니다.
- **피처 스토어**: 11-20~21 신규 항목 없음.

## 12. 에이전트 관측성

- **[사실]** 위 CloudWatch EKS 통합은 OTel 기반이라, 에이전트 서빙 계층(KServe·Ray)의 트레이스와 지표를 같은 파이프라인으로 받습니다 [[33]](#ref-33).
- **[사실]** AWS Quick의 멀티에이전트 플로우와 프롬프트 가드레일(프리뷰) [[25]](#ref-25).
- **[추론]** 관리형 에이전트 제품에서도 "가드레일 + 오케스트레이션 + 관측"을 한 묶음으로 내는 추세가 이어지고 있습니다.

## 13. 그린 컴퓨팅

- 11-21~22에 1차 출처로 확인한 신규 항목은 없습니다.
- Harvard의 Nature Sustainability 연구(11-16)는 어제 다뤘고, 그 뒤 새 진척은 없습니다(후속 보도만 있음).

## 14. 국내 기업 기술 블로그

11-21(토)에는 대상 8개사(네이버 D2, 카카오, LINE, 쿠팡, 우아한형제들, 당근, 토스, 두나무) 모두 신규 글이 없었습니다(주말). 각 사의 최신 글은 이미 다뤘습니다.

| 회사 | 제목 | 게시일 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| 토스 | 손가락 튕기기로 LLM 비용 줄이기 (**최신 아님**, 8장 특집 참고용) | 2026-10-27 | 소형 모델을 먼저 쓰고 신뢰도가 낮으면 LLM으로 폴백하는 SNAP 라우팅 | [toss.tech](https://toss.tech/article/snap-llm-cost-reduction) |

- 카카오의 최신 글은 11-18(KV 캐시 오프로딩 × EPP 라우팅), 우아한형제들은 11-20, 네이버 D2는 11-19입니다. 모두 기존 브리핑에서 다뤘습니다.

## 15. Java/Spring 프리랜서 공고 (위시켓·프리모아·이랜서)

**수집일: 2026-11-22** · 11-21(토)에 등록된 신규 공고는 **확인되지 않았습니다.** 아래 2건은 앞선 브리핑에 실리지 않은 공고이며, 등록일을 그대로 적었습니다.

| 플랫폼 | 제목 | 스택 | 계약 형태 | 금액 | 수집일 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | webMethods 기반 EAI 연계 백엔드 개발 (등록 11-20, 마감 12-04) | webMethods(EAI), 백엔드 | 상주 · 120일 · 중급(4~10년) · 서울 강남 | 월 900만 원 | 2026-11-22 | [159760](https://project.wishket.com/project/159760/) |
| 위시켓 | Java/K8s 기반 대규모 데이터레이크 AI Agent 및 MCP 개발 (등록 11-09, **최신 아님**, 마감 12-09) | Java, k8s, Spark, StarRocks, AI Agent, MCP | 상주 · 90일 · 고급(7~20년) · 성남 분당 | 월 800만 원 | 2026-11-22 | [159531](https://project.wishket.com/project/159531/) |

- 두 건 모두 상세 페이지에서 "모집 중" 표시를 확인하지 못했습니다. **모집 상태 미확인**입니다.
- 프리모아·이랜서: 로그인 없이 공개 목록에서 검증할 수 있는 신규 Java/Spring 공고가 없습니다. **오늘 확인된 검증 가능 공고 없음.**

---

## 사실 · 추론 · 미확인 정리

- **사실**
  - 리만 가설 Lean 증명이 여러 독립 커널 검증을 통과했습니다.
  - Ruby 보안 릴리스와 GitLab 긴급 패치가 나왔습니다.
  - GPGME CVE-2026-129975가 수정됐습니다.
  - CISA KEV 11-20 추가분 4건이 카탈로그에서 확인됐습니다.
  - AWS가 11-20~21에 여러 공지(CloudWatch EKS 등)를 냈습니다.
  - GKE ambient networking이 GA가 됐습니다.
  - K8s, MCP, LangGraph, CrewAI, Claude Code에는 신규 릴리스가 없습니다.
- **보도**
  - Anthropic 주가 흐름과 상장을 둘러싼 안전 논쟁.
  - Cisco Expressway 대응 상세.
  - Ruby2Shell 연구자의 원인 분석과 GHES 미수정 상태.
- **벤더 주장**: Devin Bots 사례 수치, 토스 SNAP 절감 수치. 중립 재현은 모두 **부재**합니다.
- **추론**
  - RH 사례의 남은 쟁점(명세 검증, 사람이 읽을 해설).
  - 주말 패치 우선순위.
  - 판단 특화 모델 라우팅 패턴.
- **미확인**
  - Anthropic 시가총액(매체 간 불일치).
  - AWS MSK 4.2 등 애그리게이터에서만 본 항목.
  - Scientific American 기사 본문.
  - Anthropic이 취약점을 발견한 방법.

## References

<a id="ref-1"></a>[1] Levent Alpöge, "remark" (PDF), 2026-11. <https://alpo.ge/remark.pdf>

<a id="ref-2"></a>[2] Lean community blog, "Lean verification of the Riemann Hypothesis", 2026-11-21. <https://leanprover-community.github.io/blog/posts/riemann-hypothesis/>

<a id="ref-3"></a>[3] Michael Rubinstein (University of Waterloo), Alpöge–Claude GRH verification page. <https://www.math.uwaterloo.ca/~mrubinst/alpoge_claude_grh/>

<a id="ref-4"></a>[4] Proofs & Reasons, RH oleans. <https://proofsandreasons.io/rh-oleans.html>

<a id="ref-5"></a>[5] The Guardian, 2026-11-21. <https://www.theguardian.com/technology/2026/nov/21/anthropic-riemann-hypothesis-solved-claude-ai>

<a id="ref-6"></a>[6] AP News, 2026-11-21. <https://apnews.com/article/anthropic-claude-math-solution-ai-4fe8b69a891f160f9e7f0c85af8c55c8>

<a id="ref-7"></a>[7] Scientific American, 2026-11-20. <https://www.scientificamerican.com/article/the-ai-riemann-hypothesis-proof-is-almost-certainly-true-independent-mathematicians-attest/>

<a id="ref-8"></a>[8] CNBC, 2026-11-21. <https://www.cnbc.com/2026/11/21/anthropic-ipo-tech-selloff.html>

<a id="ref-9"></a>[9] Cognition, "Introducing Devin Bots", 2026-11-17. <https://devin.ai/blog/introducing-devin-bots>

<a id="ref-10"></a>[10] Fortune, 2026-11-17. <https://fortune.com/2026/11/17/exclusive-cognition-bets-on-devin-bots-coding-agents-in-challenge-to-anthropics-duet-and-openais-dots/>

<a id="ref-11"></a>[11] Google Cloud Blog, "Introducing ambient networking for GKE", 2026-11-20. <https://cloud.google.com/blog/products/networking/ambient-networking-for-gke-sidecarless-service-mesh>

<a id="ref-12"></a>[12] ruby-lang.org, "Multiple vulnerabilities in Regexp and String", 2026-11-18. <https://www.ruby-lang.org/en/news/2026/11/18/multiple-vulnerabilities-in-regexp-and-string/>

<a id="ref-13"></a>[13] GitLab, Patch release 19.6.1, 2026-11-20. <https://docs.gitlab.com/releases/patches/patch-release-gitlab-19-6-1-released/>

<a id="ref-14"></a>[14] Veria Labs, "Ruby2Shell". <https://verialabs.com/ruby2shell/>

<a id="ref-15"></a>[15] gnupg-announce, GPGME 2.3.1, 2026-11-20. <https://lists.gnupg.org/pipermail/gnupg-announce/2026q4/000517.html>

<a id="ref-16"></a>[16] GnuPG task T8557. <https://dev.gnupg.org/T8557>

<a id="ref-17"></a>[17] Debian Security Tracker, CVE-2026-129975. <https://security-tracker.debian.org/tracker/CVE-2026-129975>

<a id="ref-18"></a>[18] The Hacker News, 2026-11-21. <https://thehackernews.com/2026/11/gnupg-warns-critical-gpgme-flaw-could.html>

<a id="ref-19"></a>[19] CISA, Known Exploited Vulnerabilities Catalog. <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>

<a id="ref-20"></a>[20] AWS What's New, AWS Quick plugins, 2026-11-21. <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-quick-plugins-bundle-agents-skills-connectors-flows/>

<a id="ref-21"></a>[21] AWS What's New, AWS Quick new web experience, 2026-11-21. <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-quick-launches-new-web-experience-updated-browser-extension-microsoft-365-add-ins/>

<a id="ref-22"></a>[22] AWS What's New, Web Search on Amazon Bedrock, 2026-11-21. <https://aws.amazon.com/about-aws/whats-new/2026/11/web-search-amazon-bedrock/>

<a id="ref-23"></a>[23] AWS What's New, Network Firewall automated Internet firewall (preview), 2026-11-20. <https://aws.amazon.com/about-aws/whats-new/2026/11/network-firewall-automated-internet/>

<a id="ref-24"></a>[24] AWS What's New, Billing and Cost Management Data Hub (preview), 2026-11-20. <https://aws.amazon.com/about-aws/whats-new/2026/11/data-hub-billing-cost-management-preview/>

<a id="ref-25"></a>[25] AWS Machine Learning Blog, "New in AWS Quick", 2026-11-20. <https://aws.amazon.com/blogs/machine-learning/new-in-aws-quick-more-capable-flows-an-updated-web-experience-and-agents-that-work-together/>

<a id="ref-26"></a>[26] Google Cloud Blog, Cross-Cloud Interconnect for Microsoft Azure, 2026-11-17. <https://cloud.google.com/blog/products/networking/cross-cloud-interconnect-for-microsoft-azure>

<a id="ref-27"></a>[27] Microsoft Tech Community, "Connecting clouds and the last mile with Azure", 2026-11-17. <https://techcommunity.microsoft.com/blog/azurenetworkingblog/connecting-clouds-and-the-last-mile-with-azure/4573283>

<a id="ref-28"></a>[28] Jev API Docs. <https://jev-api.org/docs>

<a id="ref-29"></a>[29] 토스 기술 블로그, 「손가락 튕기기로 LLM 비용 줄이기」, 2026-10-27. <https://toss.tech/article/snap-llm-cost-reduction>

<a id="ref-30"></a>[30] NPR, 2026-11-21. <https://www.npr.org/2026/11/21/nx-s1-6048678/anthropic-ipo-mission-ai-safety>

<a id="ref-31"></a>[31] Microsoft Tech Community, "Azure SRE Agent now natively supports AWS and Google Cloud", 2026-11-18. <https://techcommunity.microsoft.com/blog/appsonazureblog/azure-sre-agent-now-natively-supports-aws-and-google-cloud/4569556>

<a id="ref-32"></a>[32] AWS What's New, CloudWatch Container Insights for EKS Kubernetes tools, 2026-11-20. <https://aws.amazon.com/about-aws/whats-new/2026/11/cloudwatch-eks-kubernetes-tools/>

<a id="ref-33"></a>[33] AWS Docs, Container Insights EKS OTel solutions. <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/container-insights-eks-otel-solutions.html>
