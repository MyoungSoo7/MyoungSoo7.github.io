---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-10-29"
date: 2026-10-29 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-10-29 08:30 KST. 수집 범위는 10-28~29에 나온 1차·공식 발표가 중심입니다.
> 10-28 브리핑에 이미 실린 항목은 다시 싣지 않았습니다. 다만 **새 진척이 있는 항목**은 그 진척만 적었습니다.
> 다시 싣지 않은 항목: Anthropic Red Team CVE·GSA·신약개발 발표, Claude Code v2.1.312, KEV 10-27분(Magento·Brotli), K8s v1.34 EOL·1.38 일정, Toss SNAP, Jev 1.14 출시 내용, 위시켓 159287·159170·158840·159138.

**표기 규칙** — [사실] 1차·공식 출처로 확인 / [벤더 주장] 벤더 자체 수치, 독립 재현 없음 / [보도] 언론 보도 / [추론] 필자 해석 / [미확인] 확인 못 함

## 오늘의 핵심

1. **CISA KEV에 2건 추가 (10-28)** — VMware ESX 로깅 누락(CVE-2026-41709), 그리고 Linux 커널 "Fragnesia"(CVE-2026-46300). 연방기관 조치 기한은 11-11입니다. [사실] [3]
2. **registry.k8s.io가 승격 이미지마다 서명된 SLSA VSA를 발행합니다.** 이미지 출처를 검증한 결과가 서명된 요약 한 건으로 나옵니다. [사실] [6]
3. **Google Gemini 4 Carbon 공개** — 보안 벤치마크 수치는 전부 벤더 주장입니다. 먼저 일부 사이버 방어자에게만 제공됩니다. [벤더 주장] [4]
4. **Anthropic AI for Science 확대** — 재단·연구기관 20곳에 Claude 크레딧을 줍니다. 같은 날 Claude Enterprise의 smart reports·설문·통합 예산 기능이 GA 됐습니다. [사실] [1][2]
5. **EKS Auto Mode가 Gateway API를 지원합니다.** Ingress와 함께 쓸 수 있습니다. [사실] [7]

---

## 1. AI & ML

- **Anthropic, AI for Science 확대 (10-28)** [사실] [1]
  - 재단·연구기관·연구그룹 20곳에 무상 Claude 크레딧을 줍니다. 공개된 파트너는 Sloan Foundation, Simons Foundation, Schmidt Sciences입니다.
  - HHMI Janelia의 Model Hardware Standard(MHS)가 리서치 프리뷰로 들어갔습니다.
  - Allen Institute는 뇌 데이터 분석 에이전트를 만듭니다. **신경과학/BCI** 관련 항목입니다.
- **Claude Enterprise: smart reports · 앱 내 설문 · 그룹 통합 예산 GA (10-28)** [사실] [2][2a]
  - smart reports는 월 10회 무료이고 기본값은 꺼짐입니다. 최근 28일까지 다룹니다.
  - CMEK·HIPAA·하이브리드 배포에서는 쓸 수 없습니다.
  - 예산 알림은 50/75/95/100% 시점에 옵니다.
  - Anthropic은 이 기능을 **개인 성과 평가에 쓰지 말라**고 명시했습니다.
- **Anthropic S-1 후속 보도** [보도]
  - TechCrunch: 분기 영업이익과 NRR 900%를 보도했습니다 [2b].
  - CNBC: "AI 리스크는 보험으로 담보되지 않을 수 있다"는 위험요인 문구를 보도했습니다 [2c].
  - 두 보도 모두 S-1 원문을 인용합니다. 다만 이 브리핑은 원문 해당 페이지를 직접 대조하지 못했습니다. [미확인]
- **Google, Gemini 4 Carbon 공개 (10-28, Koray Kavukcuoglu)** [4]
  - 벤치마크 [벤더 주장]: Artificial Analysis Intelligence Index v5.0 59점(1위), SEC-bench Pro 88.2%, ExploitGym 54.8%, CWE-bench 71.0%.
  - 제공 방식 [사실]: Fairwind Program으로 일부 사이버 방어자에게 먼저 제공합니다. 미국 정부의 출시 전 테스트에도 참여했습니다.
  - 가격 [사실]: 출시 기념가는 입력 $2 / 출력 $10(1M 토큰당)입니다. 이후 $4 / $20으로 바뀌고, 캐시 입력은 95% 할인됩니다.
  - 중립 제3자 헤드투헤드 평가는 **부재**합니다.
- **Claude Code**: 10-27의 v2.1.312 이후 새 릴리스가 없습니다. [사실]

## 2. 에이전트 프레임워크

- **CrewAI 1.15.31 (10-27 21:36 UTC)** [사실] [5]
  - 대화형 Flow에 컨텍스트 압축(compaction)이 추가됐습니다.
  - 보안 수정: `output_file` 경로 탐색, 역직렬화, SQL 인젝션, 경로 탐색을 패치했고 취약한 audit 의존성을 갱신했습니다.
  - GPT-6 이상 모델에는 `stop` 파라미터를 보내지 않습니다.
  - [추론] 보안 패치가 여러 건 묶여 있습니다. 1.15.30 이하를 쓰는 곳은 올리는 편이 좋습니다.
- **CrewAI 1.15.32 (10-27 23:04 UTC)** — 불안정한 테스트만 고쳤습니다. [사실] [5]
- **LangGraph**: 1.2.18(10-26) 이후 새 릴리스가 없습니다. [사실]
- **Devin**: 10-28~29 공식 발표를 확인하지 못했습니다. [미확인]
- **Microsoft Copilot harness in Foundry Agent Service, 퍼블릭 프리뷰 (10-28)** [사실] [12]
  - 관리형 에이전트 루프에 skills, MCP 툴, 서브에이전트 위임이 들어갑니다.
  - hosted agent의 장기 실행 복원력(long-running resilience)은 GA입니다.
  - 과금은 12-01부터입니다. sandbox는 vCPU-시간당 $0.0994, GiB-시간당 $0.0118입니다.

## 3. Kubernetes & Cloud Native

- **"One Signed Answer: SLSA Verification Summaries for registry.k8s.io Images" (Kubernetes Contributors 블로그, 10-28, Sascha Grunert·Red Hat)** [사실] [6]
  - 2026년 10월부터 이미지 승격기 kpromo가 하는 일이 바뀌었습니다. 각 프로젝트가 kubernetes/k8s.io의 promoter manifest에 정책을 두고, kpromo가 그 정책으로 provenance를 평가합니다.
  - 승격된 이미지마다 서명된 SLSA VSA를 발행합니다. 프로젝트별로 SLSA build level 1 또는 3으로 검증됩니다.
  - 이미지 서명 자체는 v1.24부터 해 왔습니다.
  - [추론] 소비자는 attestation 여러 개를 직접 해석하지 않아도 됩니다. VSA 한 건만 검증하면 되므로 admission 정책을 쓰기가 쉬워집니다.
- **Amazon EKS Auto Mode, Kubernetes Gateway API 지원 (10-28)** [사실] [7]
  - Gateway·HTTPRoute 리소스를 지원합니다.
  - HTTP/gRPC, 네임스페이스 간 라우팅, 가중치 분할, ACM 인증서 자동 탐색을 제공합니다.
  - 기존 Ingress와 같이 쓸 수 있습니다.
- **v1.37/1.38 기능 관련**: 10-28 브리핑 이후 새 KEP 상태 변경 발표는 확인하지 못했습니다. [미확인]

## 4. 사이버 보안

- **CISA KEV, 2건 추가 (10-28) — 연방기관 조치 기한 2026-11-11** [사실] [3]
  - **CVE-2026-41709 — VMware ESX 로깅 누락** [8]
    - 처음 공개된 것은 2026-07-29 VMSA-2026-0006이고, CVSS는 2.7(Low)입니다.
    - 악의적 관리자가 로그를 남기지 않고 작업할 수 있습니다.
    - 수정 버전: ESXi80U3j-25429389, ESXi-9.0.2.0100-25595025, ESXi-9.1.0.0-25370933, VCF 5.2.4.
    - 제보자는 Ian Barton(CrowdStrike)입니다.
    - [추론] 점수는 낮지만 KEV에 올랐다는 것은 실제 악용이 있었다는 뜻입니다. 침해 후 흔적을 지우는 데 쓰였을 가능성을 의심해 볼 만합니다. CISA 항목이 BOD 26-04에 따른 포렌식 분류(triage)를 언급한 것으로 보이지만, 원문 문구는 직접 대조하지 못했습니다. [미확인]
  - **CVE-2026-46300 "Fragnesia" — Linux 커널 XFRM ESP-in-TCP 로컬 권한상승** [9][10]
    - 2026-05-13 공개, CVSS 7.8입니다.
    - page cache에 쓰기가 가능한 결함으로, Dirty Frag와 같은 계열입니다.
    - 완화책은 esp4/esp6 모듈 차단입니다.
    - 5월에는 실제 악용이 확인되지 않았습니다. 이번 KEV 등재로 악용이 확인된 셈입니다.
- **Node2Shell(Brotli) 새 진척** [보도] [11]
  - SecurityWeek(10-28) 보도: 보안업체 두 곳의 허니팟에 실제 악용 시도가 기록됐습니다.
  - 영향 범위는 1.0.3~1.2.0이고, 수정 버전은 10-28 브리핑에 적은 v1.2.1입니다.
- **PHP2Shell 연방 조치 기한이 오늘(10-29)입니다.** [사실] 정정 내용은 10-28 브리핑을 참고하세요.

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

**AWS (10-28)** [사실]
- Lambda durable functions **Telemetry Exporter**: 전송 대상 13곳을 지원하고 MCP 서버가 함께 나왔습니다 [13].
- OpenSearch Serverless 시계열 컬렉션: warm 티어가 생겼고 hot 데이터는 최대 100 TB까지 담습니다 [14].
- ECS Managed Instances: 인스턴스 간 통합과 Spot 통합을 지원합니다 [15].
  - AWS 테스트 결과 [벤더 주장]: 인스턴스 19 → 13대, CPU 사용률 42% → 91%.
- Lambda Managed Instances에 SOCI 지연 로딩이 들어갔습니다. 시작이 "최대 70%" 빨라진다고 합니다 [벤더 주장] [16].
- IAM Identity Center Identity Store의 변경을 EventBridge 알림으로 받을 수 있습니다 [17].
- Amazon Quick smart approvals: 에이전트 작업을 분류기로 승인합니다 [18].

**Azure (10-28)** [사실]
- Azure SDK 10월 릴리스 [19]
  - Cosmos DB Rust 1.0.0이 첫 안정판입니다.
  - .NET Azure Core 1.63.0이 mTLS proof-of-possession을 지원합니다.
  - Python Identity 1.26.0이 Arc 서버의 사용자 할당 관리 ID를 지원합니다.
- Foundry Copilot harness는 2장을 참고하세요 [12].

**GCP (10-28 release notes)** [사실] [20]
- AlloyDB
  - 4단계 트리 ScaNN으로 최대 100억 벡터 행을 다룹니다.
  - IAM 그룹 인증이 GA 됐습니다.
  - GCP-2026-071 인증서 저장소 문제를 고쳤습니다(Auth Proxy v1.17.2 이상).
- Bigtable 마이크로초 타임스탬프 GA.
- DMS SQL Server DAG 마이그레이션 GA.
- Cloud SQL MySQL 관리형 복제본 인덱스 GA.
- Memorystore Redis Cluster 토큰 인증 GA.
- SecOps `chronicle-tla` 종료가 시작됐습니다.
- Google Cloud IAM Helper(10-27): 에이전트 skills와 MCP 툴로 IAM 작업을 돕습니다 [21].

**Naver Cloud**: 10-28~29 공지를 확인하지 못했습니다. [미확인]

## 6. 언어 · 런타임

- **Spring Boot**: 최신은 10-23에 나온 4.0.9, 4.1.2, 4.2.0-RC1입니다. 10-28~29 새 릴리스는 없습니다. [사실] [22]
- **Rust**: Azure Cosmos DB Rust SDK가 1.0.0 안정판에 도달했습니다(5장). [사실] [19]
- Python·Java(JDK)·Kotlin·React·Vue·TS: 10-28~29 공식 릴리스는 확인하지 못했습니다. [미확인]

## 7. 인프라 & Linux

- **Fragnesia(CVE-2026-46300)가 KEV에 올랐습니다.** 배포판 수정은 이미 나와 있습니다(Red Hat [9], Ubuntu [10]).
  - [추론] 바로 패치하지 못하는 호스트라면 IPsec ESP-in-TCP를 안 쓰는지 확인하세요. 안 쓰면 `esp4`/`esp6` 모듈을 blacklist 하는 것이 현실적인 임시 조치입니다.
- **ESXi 로깅 누락(CVE-2026-41709)** — 4장 참고. vSphere 운영 조직은 패치 레벨부터 점검해야 합니다.

## 9. AI Safety & Alignment

- Gemini 4 Carbon은 미국 정부의 출시 전 테스트를 거쳤고, Fairwind Program으로 제한 공개됩니다 [4]. [사실]
  - [추론] 공격 역량이 큰 모델은 "방어자에게 먼저" 단계적으로 푸는 방식이 업계 관행으로 굳어지고 있습니다.
- Anthropic S-1이 "AI 리스크는 보험으로 담보되지 않을 수 있다"고 적었다는 보도가 있습니다 [보도] [2c].

## 10. MCP 생태계

- 사양 최신본은 여전히 **2026-07-28**입니다. [사실] [23]
- SEP 진행 상황 [사실] [23]
  - SEP-3392 "Extension Lifecycle"가 최종 단계에 들어갔습니다(10-27 갱신).
  - SEP-3094 Granular Citations가 10-28에 갱신됐습니다.
- 벤더 쪽 MCP 도입 [사실]
  - AWS Lambda durable telemetry MCP 서버 [13]
  - Google Cloud IAM Helper MCP 툴 [21]
  - Microsoft Foundry Copilot harness의 MCP 툴 연결 [12]

## 11. MLOps / Feature Store

- **MLflow**: 3.17.2(10-21) 이후 새 릴리스가 없습니다. [사실] [24]
- **Feast**: v0.67.0(10-13) 이후 새 릴리스가 없습니다. [사실] [25]
- GCP AlloyDB의 ScaNN 확장(100억 행)은 벡터 기반 feature 조회에도 관련됩니다 [20]. [사실]

## 12. 에이전트 관측성 (Agent Observability)

- **Langfuse v4.71.0 (10-27)** [사실] [26]
  - AI gateway가 모델, 키 소유자, 업스트림 오류 정보를 기록합니다.
  - 셀프호스팅 정부용 플랜(`lf_gov_` 키)이 생겼습니다.
  - Topics 기능이 개선됐습니다.
- **Arize Phoenix (10-28)** — 소규모 패치입니다: arize-phoenix-evals 3.9.5, phoenix-client 7.16.3, phoenix-evals 2.7.1, phoenix-mcp 4.3.18. [사실] [27]
- AWS Lambda durable Telemetry Exporter도 관측성 관련 항목입니다(5장) [13].

## 13. 그린 컴퓨팅

- **영국 정부 "The Data Centre Covenant" (10-28)** [사실] [28]
  - 신규 데이터센터의 PUE 목표는 1.3 이하입니다.
  - 전략 데이터센터는 에너지·물 사용량, 효율, 배출, 폐열 재사용을 해마다 보고해야 합니다.
  - 폐열 재사용과 폐쇄 루프 냉각을 권고합니다.
- **미시간대 E-CALC (10-28)** [사실] [29]
  - DARPA가 $1.83M을 지원하는 2년 과제입니다.
  - AI 생애주기 전체의 에너지 사용을 추정하는 "energy calculus" 도구를 오픈소스로 공개할 계획입니다.
  - "AI 에너지 사용을 최대 절반 줄일 수 있다"는 것은 연구진의 목표치입니다. 아직 검증된 결과가 아닙니다.

## 14. 국내 기업 기술 블로그 (네카라쿠배당토)

| 회사 | 제목 | 날짜 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| 카카오페이 | 로그 수집기가 왜 자꾸 OOM으로 죽었나 - 누적 드롭 8.9억 건을 기록한 로그 파이프라인을 고친 이야기 | 2026-10-27 (최신 아님, 직전 브리핑 누락분) | 아래 참고 | [30] |

카카오페이 글 요약
- 카카오페이손해보험의 EKS 위 Alloy/Loki 파이프라인 이야기입니다. 하루 1.3 TB를 처리합니다.
- Alloy 메모리 한도를 올리지 않고 OOM을 해결했습니다.
- 샌드박스 수치 [자사 주장]: 활성 스트림 −78%, Loki CPU 16.9 → 0.37 코어, 쿼리 P99 −90%.
- 글에서 직접 밝힌 단서가 있습니다.
  - 위 수치는 여러 변경을 합친 효과입니다.
  - S3 −86%는 DEBUG 로그 정리와 보존기간 단축에서 나왔습니다.

다른 회사들(NAVER D2, 카카오, LINE, 쿠팡, 우아한형제들, 당근, 토스, 두나무)은 10-28~29 새 글을 확인하지 못했습니다. 토스 최신 글은 10-27 SNAP(이미 다룸), 우아한형제들 최신 글은 10-21입니다.

## 15. Java/Spring 프리랜서 공고

**오늘 확인된 검증 가능 공고 없음**

- 위시켓 159287 "Java/Spring 기반 보안관제 솔루션 커스텀 개발 및 고도화"(10-26 등록)는 이전 브리핑에서 다뤘으므로 다시 싣지 않습니다.
  - 새 진척만 적습니다: 원 공고 [31]에서 금액이 월 5,000,000원(미드 레벨), 기간 90일, 마감 11-09, 모집 중으로 확인됩니다(수집일 10-29).
- 위시켓 목록 [32]의 다른 신규 항목은 Java/Spring이 아닙니다(GCP, React, MSSQL 튜닝 등).
- 프리모아·이랜서: 로그인 없이 확인할 수 있는 10-28~29 Java/Spring 공고를 찾지 못했습니다. [미확인]

## 8. 특별 섹션 — Jev API와 의사결정 모델

- 10-27~29 사이 Jev 공식 발표나 새 릴리스는 확인하지 못했습니다. [사실: 공식 채널에 새 항목 없음]
- **배경 — 중립 제3자 평가 (이전 브리핑의 "중립 검증 부재" 보완)** [사실, 최신 아님] [33]
  - 논문: "Evaluating and Benchmarking the System One Model Jev". 본(Bonn) 대학 Deußer·Sparrenberg·Sifa, arXiv, 2026-09-29.
  - 평가 방식: jev-1.13.0을 37개 데이터셋에서 zero-shot으로 평가했습니다. 요청 346,009건에 비용은 $10 미만이었습니다.
  - 결과
    - Qwen3.8-27B 대비 27/37에서 앞섰습니다.
    - Gemma-4-E4B 대비 37/37에서 앞섰습니다.
    - 다지선다 확률은 잘 보정(calibrated)되어 있었습니다.
    - 이진 판단 확률은 0.5 임계값 기준으로 보면 위치가 좋지 않았습니다.
  - 한계: 평가 버전이 1.13.0이므로 현행 1.14.0과는 다릅니다. 동료심사 전 프리프린트이기도 합니다.
  - [추론] 확률을 그대로 의사결정 임계값에 쓰려면 이진 과제에서 따로 재보정(calibration)할 필요가 있어 보입니다.

---

## 사실 · 추론 · 미확인 정리

- **사실**: KEV 2건(11-11 기한), registry.k8s.io VSA, EKS Auto Mode Gateway API, Anthropic AI for Science와 Enterprise 기능 GA, CrewAI 1.15.31 보안 수정, Langfuse v4.71.0, GCP·AWS·Azure 10-28 발표, 영국 Data Centre Covenant.
- **벤더 주장**: Gemini 4 Carbon 벤치마크, ECS 통합률, Lambda SOCI 70%, 카카오페이 샌드박스 수치(자사 주장).
- **보도**: Anthropic S-1 관련 수치와 보험 문구, Node2Shell 허니팟 관측.
- **추론**: CVE-2026-41709의 흔적 은폐 악용 가능성, VSA가 정책 작성을 쉽게 한다는 점, 이진 확률 재보정 필요성.
- **미확인**: Devin, Naver Cloud, 프리모아·이랜서, 언어 런타임(Spring 제외) 10-28~29 릴리스, KEV 41709 항목의 BOD 26-04 문구.

## References

1. Anthropic, "AI for Science expands to foundations and research institutions", 2026-10-28 — <https://www.anthropic.com/news/ai-for-science-expands-foundations-research-institutions>
2. Claude, "Smart reports, surveys, and pooled budgets", 2026-10-28 — <https://claude.com/resources/articles/smart-reports-surveys-pooled-budgets>
   - 2a. Claude Help Center, "Get started with smart reports" — <https://support.claude.com/en/articles/16893491-get-started-with-smart-reports>
   - 2b. TechCrunch, Anthropic S-1 보도, 2026-10-28 [보도] — <https://techcrunch.com/>
   - 2c. CNBC, Anthropic S-1 AI 리스크 보도, 2026-10-28 [보도] — <https://www.cnbc.com/>
3. CISA, "CISA Adds Two Known Exploited Vulnerabilities to Catalog", 2026-10-28 — <https://www.cisa.gov/news-events/alerts/2026/10/28/cisa-adds-two-known-exploited-vulnerabilities-catalog>
4. Google, "Introducing Gemini 4 Carbon", 2026-10-28 — <https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-carbon/>
5. crewAIInc/crewAI, GitHub Releases 1.15.31 · 1.15.32, 2026-10-27 — <https://github.com/crewAIInc/crewAI/releases>
6. Kubernetes Contributors, "One Signed Answer: SLSA Verification Summaries for registry.k8s.io Images", 2026-10-28 — <https://www.kubernetes.dev/blog/2026/10/28/registry-k8s-io-verification-summaries/>
7. AWS, "Amazon EKS Auto Mode now supports Kubernetes Gateway API", 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-eks-auto-mode-kubernetes-gateway-api/>
8. Broadcom, VMSA-2026-0006 (CVE-2026-41709) — <https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/38017>
9. Red Hat, CVE-2026-46300 — <https://access.redhat.com/security/cve/cve-2026-46300>
10. Ubuntu, "Fragnesia Linux vulnerability fixes available" — <https://ubuntu.com/blog/fragnesia-linux-vulnerability-fixes-available>
11. SecurityWeek, "CISA Warns of Node2Shell Exploitation as Honeypots Log Attack Attempts", 2026-10-28 [보도] — <https://www.securityweek.com/cisa-warns-of-node2shell-exploitation-as-honeypots-log-attack-attempts/>
12. Microsoft Foundry Blog, "Introducing the Microsoft Copilot harness in Foundry Agent Service", 2026-10-28 — <https://devblogs.microsoft.com/foundry/microsoft-copilot-harness-in-foundry/>
13. AWS, Lambda durable functions Telemetry Exporter, 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/lambda-durable-telemetry/>
14. AWS, OpenSearch Serverless time series collections, 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/time-series-collection-next-generation-opensearch-serverless/>
15. AWS, ECS Managed Instances consolidation, 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/ecs-managed-instances-consolidation/>
16. AWS, Lambda SOCI lazy loading, 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/aws-lambda-seekable-oci-soci/>
17. AWS, Identity Store change notifications, 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/aws-identity-store-change-notifications/>
18. AWS, Amazon Quick smart approvals, 2026-10-28 — <https://aws.amazon.com/about-aws/whats-new/2026/10/quick-smart-approvals-agentic-actions/>
19. Azure SDK Blog, "Azure SDK Release (October 2026)", 2026-10-28 — <https://devblogs.microsoft.com/azure-sdk/azure-sdk-release-october-2026/>
20. Google Cloud, Release notes (2026-10-28) — <https://docs.cloud.google.com/release-notes>
21. Google Cloud Blog, "Scale agents securely with IAM Helper agent skills and MCP tools", 2026-10-27 — <https://cloud.google.com/blog/products/identity-security/scale-agents-securely-with-iam-helper-agent-skills-and-mcp-tools>
22. Spring, Blog releases (Spring Boot 4.0.9 · 4.1.2 · 4.2.0-RC1, 2026-10-23) — <https://spring.io/blog/category/releases>
23. Model Context Protocol, SEP index — <https://plan.modelcontextprotocol.io/seps>
24. MLflow, GitHub Releases — <https://github.com/mlflow/mlflow/releases>
25. Feast, GitHub Releases — <https://github.com/feast-dev/feast/releases>
26. Langfuse, GitHub Releases v4.71.0, 2026-10-27 — <https://github.com/langfuse/langfuse/releases>
27. Arize Phoenix, GitHub Releases, 2026-10-28 — <https://github.com/Arize-ai/phoenix/releases>
28. GOV.UK, "The Data Centre Covenant", 2026-10-28 — <https://www.gov.uk/government/publications/data-centre-covenant/the-data-centre-covenant>
29. University of Michigan, "Optimizing AI energy consumption throughout its entire lifecycle", 2026-10-28 — <https://news.umich.edu/optimizing-ai-energy-consumption-throughout-its-entire-lifecycle/>
30. 카카오페이 기술 블로그, "로그 수집기가 왜 자꾸 OOM으로 죽었나", 2026-10-27 — <https://tech.kakaopay.com/post/no-more-oom-log-pipeline/>
31. 위시켓, 프로젝트 159287 (원 공고) — <https://www.wishket.com/project/159287/>
32. 위시켓, 프로젝트 찾기 (목록 페이지) — <https://www.wishket.com/project/>
33. Deußer, Sparrenberg, Sifa, "Evaluating and Benchmarking the System One Model Jev", arXiv, 2026-09-29 — <https://arxiv.org/html/2609.37647v1>
