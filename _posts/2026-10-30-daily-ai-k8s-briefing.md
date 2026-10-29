---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-10-30"
date: 2026-10-30 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-10-30 08:30 KST. 수집 범위는 10-29~30에 나온 1차·공식 발표가 중심입니다(미국 시각으로 10-28 저녁에 나온 것 일부 포함).
> 10-29 브리핑에 이미 실린 항목은 다시 싣지 않았습니다. 다만 **새 진척이 있는 항목**은 그 진척만 적었습니다.
> 다시 싣지 않은 항목: Anthropic AI for Science, Claude Enterprise smart reports, Gemini 4 Carbon, Claude Code v2.1.312, LangGraph 1.2.18, CrewAI 1.15.32, registry.k8s.io SLSA VSA, KEV 10-28분 본문, AWS·GCP 10-28 발표, Spring Boot 10-23 릴리스, MLflow 3.17.2, Langfuse v4.71.0, 토스 SNAP, 위시켓 159287, Jev 배경 논문.

**표기 규칙** — [사실] 1차·공식 출처로 확인 / [벤더 주장] 벤더 자체 수치, 독립 재현 없음 / [보도] 언론 보도 / [추론] 필자 해석 / [미확인] 확인 못 함

## 오늘의 핵심

1. **CISA KEV에 2건 추가 (10-29), 조치 기한은 11-01로 짧습니다.** GitLab CE/EE 원격 코드 실행(CVE-2026-97229), Cisco ASA/FTD 서비스 거부(CVE-2026-76418)입니다. GitLab 건은 포렌식 점검까지 요구합니다. [사실] [5][6][7]
2. **Kubernetes 패치 릴리스 v1.37.2 · v1.36.6 · v1.35.10 (10-28).** Go 1.26.10 빌드, kube-proxy가 `nf_conntrack_max`를 낮추던 1.36 회귀 수정 등이 들어 있습니다. [사실] [3]
3. **AI Conformance가 워킹그룹에서 SIG Architecture 하위 프로젝트로 옮겨갔습니다.** 인증 플랫폼은 18곳에서 31곳으로 늘었습니다. [사실] [4]
4. **Claude for Legal에 법률용 아티팩트가 추가됐습니다.** 인용 검증(Cite check), 관할권 비교표 같은 대화형 도구 갤러리입니다. [사실] [1]
5. **Node.js 26.x가 LTS("Lithium")로 들어갔습니다 (26.13.0, 10-28).** 지원 기간은 2029년 4월 말까지입니다. [사실] [16]

> **정정** — 10-29 브리핑에서 KEV 10-28분 2건의 기한을 모두 11-11로 적었습니다. 보도에 따르면 Fragnesia(CVE-2026-46300)의 기한은 **10-31**입니다. 11-11은 CVE-2026-41709(ESXi)의 기한입니다. 정확한 날짜는 KEV 카탈로그 항목에서 직접 확인하시기 바랍니다. [보도] [8]

---

## 1. AI & ML

- **Claude for Legal 아티팩트 (10-28, 미국 시각)** [사실] [1]
  - 법률 업무용 대화형 아티팩트 갤러리입니다. 들어 있는 도구는 Cite check, Jurisdiction survey matrix, Matter board, Playbook deviation board, Regulatory horizon scan, Tabular review입니다.
  - 법률 커넥터는 60개 이상입니다. 예: Bloomberg Law, Filevine, Ivo, Legora, Patlytics.
  - 공유 설정에서 정보 차단벽(ethical wall)을 지원합니다.
  - ABA Journal이 10-29에 이를 보도했습니다. [보도] [2]
  - [추론] 법률 분야는 인용 오류(환각 판례)가 실제 제재로 이어진 분야입니다. 그래서 Cite check가 갤러리 맨 앞에 놓인 것으로 보입니다. 다만 검증 정확도에 대한 수치는 공개되지 않았습니다.
- Anthropic 뉴스룸에는 10-29 새 발표가 없습니다. [사실]
- ML/DL 연구, 신경과학·BCI: 10-29~30 사이 1차 출처로 확인한 주요 발표는 없습니다. [미확인]

## 2. 에이전트 프레임워크

- Claude Code(v2.1.312, 10-27), LangGraph(1.2.18, 10-26), CrewAI(1.15.32, 10-27) 모두 10-29 이후 새 릴리스가 없습니다. [사실: GitHub Releases 기준]
- Devin: 확인하지 못했습니다. [미확인]

## 3. Kubernetes & Cloud Native

- **패치 릴리스 v1.37.2 · v1.36.6 · v1.35.10 (10-28)** [사실] [3]
  - 1.38.0-alpha.3도 같은 날 나왔습니다.
  - 1.37.2에 들어간 주요 변경
    - Go 1.26.10으로 빌드했습니다. Go 쪽 긴급 보안 수정을 반영한 것입니다.
    - DeviceTaintRule의 NoExecute가 DRA 기반 확장 리소스를 쓰는 파드도 퇴출(evict)합니다.
    - 같은 이름으로 다시 만든 Job이 조정(reconcile)되지 않고 남던 문제를 고쳤습니다.
    - `k8s.io/apiserver`가 요청 헤더 값을 최대 16,384개까지 받습니다. Go 1.27 기본값(500)에서는 그룹이 500개 안팎인 사용자를 가장(impersonation)할 때 HTTP 431이 났습니다.
    - kube-proxy가 더는 `nf_conntrack_max`를 낮추지 않습니다. 1.36에서 생긴 회귀입니다.
  - [추론] conntrack 회귀는 노드당 연결이 많은 클러스터에서 패킷 드롭으로 나타날 수 있습니다. 1.36 계열을 쓰고 있다면 1.36.6 적용 우선순위가 높습니다.
- **AI Conformance, SIG Architecture 하위 프로젝트로 (10-29)** [사실] [4]
  - Kubernetes Contributors 블로그의 인터뷰 글입니다. 저자는 Frederico Muñoz, Kirti Goyal입니다. 인터뷰 대상은 Janet Kuo(Google), Yuan Tang(Red Hat)입니다.
  - 인증 플랫폼은 18곳에서 31곳으로 늘었습니다.
  - 요구사항은 KAR(Kubernetes AI Requirements) 단위로 관리합니다.
  - 다음 과제는 적합성 검증의 자동화입니다.

## 4. 보안

- **CISA KEV 10-29 추가분 — 기한 2026-11-01** [사실] [5]
  - **CVE-2026-97229 — GitLab CE/EE 정수 오버플로**
    - CI/CD 설정에 넣은 조작된 정규식으로 인증 없이 원격 코드를 실행할 수 있습니다. 원인은 Ruby의 정규식 엔진(Onigmo)입니다.
    - KEV 항목에 "Forensic triage required: Yes"가 붙었습니다. 패치만으로 끝내지 말고 침해 흔적도 점검하라는 뜻입니다.
    - 수정: GitLab 패치 릴리스 19.4.2, Ruby 10-23 정규식 수정. [6]
  - **CVE-2026-76418 — Cisco ASA/FTD NULL 포인터 역참조 (DoS)** [7]
    - 권고 ID는 cisco-sa-asaftd-tunnel-dos-s6mgkb75입니다. 10-28에 처음 공개됐고 CVSS 8.6입니다.
    - 조건: Remote Access SSL VPN에서 터널 그룹에 2차 인증(secondary authentication)이 설정된 경우입니다. 인증 없이 장비를 재부팅시킬 수 있습니다.
    - Cisco PSIRT는 2026년 10월에 실제 악용을 인지했다고 밝혔습니다.
    - 수정 버전
      - ASA: 9.16.4.104, 9.18.4.96, 9.20.4.50, 9.22.3.200, 9.23.1.48, 9.24.1.27 / 9.24.10.1
      - FTD: 7.0.11, 7.2.13, 7.4.9, 7.6.7, 7.7.14, 10.0.3, 10.1.1
    - 임시 완화: 2차 인증을 끄거나 `no tunnel-group-list enable`을 적용합니다(권고의 Case 1/2 참고).
    - 캐나다 사이버보안센터도 AV26-1102로 같은 내용을 알렸습니다. [사실] [9]
  - [추론] 기한이 사흘뿐입니다. 외부에 노출된 GitLab과 VPN 장비부터 처리해야 합니다.
- **Fragnesia 기한 정정** — 맨 위 정정 상자를 참고하세요. KEV 항목은 PHP2Shell(CVE-2026-109618/109619)과 연쇄해 악용될 수 있다고 적고 있습니다. [보도] [8]
- Cisco Talos의 SD-WAN 관련 위협 행위자 보고, Unit 42의 GlobalProtect 분석은 1차 원문을 확인하지 못했습니다. [미확인]

## 5. CSP (AWS · Azure · GCP · Naver Cloud)

- **AWS (10-29)** [사실]
  - RDS for Oracle·SQL Server가 추가 스토리지 볼륨에도 스토리지 자동 확장을 적용합니다. 추가 볼륨은 최대 3개, 합계 최대 256 TiB입니다. [10]
  - Aurora PostgreSQL이 TLS 키 교환에서 포스트 양자(post-quantum) 알고리즘을 지원합니다. PostgreSQL 18 이상에서 `ssl_groups` 파라미터로 켭니다. [11]
  - MSK Connect에서 커넥터 플러그인과 워커 설정을 업데이트할 수 있게 됐습니다. [12]
- **Azure (10-29)** [사실]
  - Azure Blog에 "Azure Cloud HSM Hardware Audit Logging" 발표가 올라왔습니다. [13]
  - 같은 주의 다른 Azure 업데이트(VNet 흐름 로그 필터링 GA 등)는 제3자 요약에서만 봤고 1차 출처를 확인하지 못해 싣지 않았습니다. [미확인]
- **GCP (10-29 릴리스 노트)** [사실] [14]
  - Dataflow Streaming Engine 자동 확장에 지연 등급(low / medium / high_latency)과 자동 확장 일정이 생겼습니다.
  - Model Armor를 southamerica-east1에서 쓸 수 있습니다.
  - ABAP SDK 1.15가 GA 됐습니다.
  - App Optimize API에 VPC Service Controls가 미리보기로 붙었습니다.
- **Naver Cloud** — 공지 페이지에 10-29~30 새 항목이 없습니다. [미확인]
- **(국내 참고) 카카오클라우드 장애 공지** [사실] [15]
  - kr-central-2 리전 AZ-c에서 블록 스토리지 생성·삭제가 지연됐습니다.
  - 시간은 2026-10-29 19:20~21:28이며, 해소됐습니다.

## 6. 언어 (Python · Rust · React · Vue · Java · Kotlin · JS · TS)

- **Node.js 26.13.0 / 24.22.2 (10-28)** [사실] [16]
  - 26.x가 Active LTS "Lithium"으로 들어갔습니다. 지원은 2029년 4월 말까지입니다.
  - 24.x도 LTS 패치(24.22.2)가 함께 나왔습니다.
  - Node가 27부터 메이저를 1년 주기로 바꾼다는 이야기는 1차 출처로 확인하지 못했습니다. [미확인]
- Spring: 10-23 릴리스 이후 새 릴리스가 없습니다. [사실] [17]
- Python, Rust, Go, Kotlin, React, Vue, TypeScript: 10-29~30에 새 릴리스를 확인하지 못했습니다. 각 프로젝트의 최근 릴리스는 이전 브리핑에 실렸습니다. [사실: 새 항목 없음]

## 7. 인프라 & Linux

- 리눅스 stable 7.2.13 / 6.18.59 출시 소식은 집계 사이트에서만 봤습니다. kernel.org 원문을 확인하지 못했습니다. [미확인]
- 카카오클라우드 블록 스토리지 지연은 5절에 실었습니다.
- 운영 메모 [추론]
  - 이번 주 할 일이 겹칩니다. KEV 기한(10-31, 11-01), K8s 1.36.6 conntrack 수정, Node 26 LTS 전환 검토입니다.
  - 기한 순서대로 처리하는 편이 안전합니다.

## 9. AI Safety & Alignment

- 10-29~30 사이 Anthropic·OpenAI·Google DeepMind·UK AISI의 새 안전 연구나 정책 발표는 확인하지 못했습니다. [미확인]
- 1절의 법률 아티팩트는 공유 설정에서 정보 차단벽을 지원합니다. 이는 접근 통제 기능이지 모델 정렬(alignment) 연구는 아닙니다. [추론]

## 10. MCP 생태계

- 스펙 최신판은 여전히 2026-07-28입니다. [사실] [18]
- SEP 상태 변화는 다시 확인하지 못했습니다. [미확인]
- Claude for Legal은 60개 이상의 법률 커넥터를 내세웁니다. 이 중 어떤 것이 MCP 서버인지는 공지에 나와 있지 않습니다. [미확인] [1]

## 11. MLOps / Feature Store

- MLflow는 3.17.2(10-21)에서 바뀌지 않았습니다. [사실] [19]
- Feast는 다시 확인하지 못했습니다. [미확인]
- GCP Dataflow의 자동 확장 지연 등급(5절)은 스트리밍 피처 파이프라인의 비용·지연 균형에 영향을 줍니다. [추론] [14]

## 12. Agent Observability

- Langfuse는 v4.71.0(10-27)에서 바뀌지 않았습니다. [사실] [20]
- Arize Phoenix는 10-28 패치 이후 다시 확인하지 못했습니다. [미확인]

## 13. Green Computing

- 10-29~30 사이 1차 출처로 확인한 새 항목은 없습니다. [미확인]
- [추론] 5절 GCP Dataflow의 자동 확장 일정 기능은 예측 가능한 부하에서 유휴 워커를 줄이는 데 쓸 수 있습니다. 다만 Google은 에너지 절감 수치를 내놓지 않았습니다.

## 14. 국내 기업 기술 블로그 (네카라쿠배당토)

| 회사 | 제목 | 날짜 | 요약 | 링크 |
|---|---|---|---|---|
| 카카오클라우드 (공지) | 블록 스토리지 생성·삭제 지연 장애 | 2026-10-29 | kr-central-2 AZ-c, 19:20~21:28, 해소. 블로그 회고 글이 아니라 서비스 공지입니다. | [15] |

**그 밖의 회사**
- 토스 최신 글은 LLM 비용 절감(SNAP) 글로, 10-27에 다뤘습니다.
- 우아한형제들의 최신 글은 10-21입니다.
- LY의 Flava MCP Hub 글은 이전 브리핑에서 다뤘습니다.
- NAVER D2, 카카오, 당근, 쿠팡, 두나무는 10-29~30 새 글을 확인하지 못했습니다. 카카오 기술 블로그는 목록을 불러오지 못했습니다. [미확인]
- 이 기간에 장애 회고 글은 **확인되지 않았습니다**.

## 15. Java/Spring 프리랜서 공고

수집 일자: 2026-10-30. 로그인 없이 볼 수 있는 공개 페이지만 확인했습니다.

**원 공고 (상세 페이지 확인)**

| 플랫폼 | 제목 | 스택 | 계약·근무 형태 | 금액 | 상태 | 링크 |
|---|---|---|---|---|---|---|
| 위시켓 | Java 기반 산업 데이터 연계 시스템 백엔드 개발 및 안정화 | Java (백엔드·데이터 연계) | 기간제, 시니어(8~10년 차), 90일, 상주(울산 중구) | 월 9,000,000원 | 모집 중, 마감 2026-11-12, 등록 10-29 | [21] |

- 기존 시스템을 인수해 데이터 연계, 웹 기능 개선, 배포·안정화를 맡는 프로젝트입니다.
- 공고에는 "원수급사와 수행 조건을 협의 중이며 인력 확정 후 계약 예정"이라고 적혀 있습니다. 계약이 확정되지 않았다는 뜻입니다. [사실]

**목록 페이지에서만 본 공고 (상세 페이지 미확인)** [22]
- 위시켓, "Java 기반 산업 모니터링 웹 시스템 풀스택 개발" — 월 9,000,000원, 90일, 울산 중구, 등록 10-29. 상세 페이지를 열지 못했습니다. **모집 상태 미확인**.
- 위시켓, "Oracle WebLogic 서비스 운영 및 유지보수" — Java·WAS(JBoss)·XQuery, 월 4,000,000원, 90일, 서울 서초구, 등록 10-29. Spring 공고는 아닙니다. **모집 상태 미확인**.
- 프리모아·이랜서: 공개 페이지에서 오늘 확인한 Java/Spring 공고가 없습니다. [미확인]

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- 10-29~30 사이 TypeSafe(Jev)의 공식 발표나 새 릴리스는 확인하지 못했습니다. 현행은 Jev 1.14(10-14 공개)이며, 이전 브리핑에서 다뤘습니다. [사실: 공식 채널에 새 항목 없음]
- OpenAI Decisions API의 GA(10-22)도 이전 브리핑에서 다뤘으므로 다시 싣지 않습니다.
- [추론] 이번 주 Jev 관련 실무 질문은 새 기능이 아니라 운영 쪽에 있습니다.
  - 이진 판단 확률을 그대로 임계값으로 쓸 수 있는지가 문제입니다. 10-29에 소개한 제3자 평가가 이진 확률의 위치 문제를 지적했습니다.
  - 따라서 도입하는 쪽은 자기 데이터로 재보정하고 검증 세트를 두는 것이 필요합니다.
  - 중립적인 제3자의 직접 비교(헤드투헤드)는 여전히 **부재**합니다.

---

## 사실 · 추론 · 미확인 정리

- **사실**
  - KEV 10-29분 2건(기한 11-01)과 Cisco 수정 버전, K8s 패치 릴리스 3종, AI Conformance의 SIG Architecture 이관
  - Claude for Legal 아티팩트, Node.js 26 LTS 진입
  - AWS·GCP·Azure 10-29 발표, 카카오클라우드 장애 공지, 위시켓 159357
- **보도**: Fragnesia 기한 10-31(정정), ABA Journal의 법률 아티팩트 보도
- **추론**
  - KEV 대응 우선순위, conntrack 회귀의 영향
  - Cite check가 갤러리 맨 앞에 놓인 배경
  - Jev 확률 재보정의 필요성, Dataflow 자동 확장 일정의 에너지 측면
- **미확인**
  - Devin, AI 안전 분야 새 발표, 그린 컴퓨팅, MCP SEP, Feast, Phoenix
  - Naver Cloud, 리눅스 stable, 국내 블로그 다수, 프리모아·이랜서
  - Azure 주간 업데이트의 1차 출처

## References

1. Claude, "Introducing artifacts for legal work", 2026-10-28 — <https://claude.com/resources/articles/introducing-artifacts-for-legal-work>
2. ABA Journal, "Anthropic raises the bar with Claude for Legal artifacts", 2026-10-29 [보도] — <https://www.abajournal.com/news/article/anthropic-raises-the-bar-with-claude-for-legal-artifacts-law-specific-interactive-tools>
3. kubernetes/kubernetes, GitHub Releases (v1.37.2 · v1.36.6 · v1.35.10 · v1.38.0-alpha.3), 2026-10-28 — <https://github.com/kubernetes/kubernetes/releases>
   - 3a. CHANGELOG-1.37 — <https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.37.md>
4. Kubernetes Contributors, "From Working Group to SIG Architecture: spotlight on AI Conformance", 2026-10-29 — <https://www.kubernetes.dev/blog/2026/10/29/sig-arch-ai-conformance-2026/>
5. CISA, "CISA Adds Two Known Exploited Vulnerabilities to Catalog", 2026-10-29 — <https://www.cisa.gov/news-events/alerts/2026/10/29/cisa-adds-two-known-exploited-vulnerabilities-catalog>
6. GitLab, "GitLab Patch Release 19.4.2" — <https://docs.gitlab.com/releases/patches/patch-release-gitlab-19-4-2-released/>
7. Cisco, Security Advisory cisco-sa-asaftd-tunnel-dos-s6mgkb75, 2026-10-28 — <https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-asaftd-tunnel-dos-s6mgkb75>
8. CISA, Known Exploited Vulnerabilities Catalog (CVE-2026-46300 기한 확인용) — <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
9. Canadian Centre for Cyber Security, "Cisco security advisory (AV26-1102)", 2026-10-29 — <https://www.cyber.gc.ca/en/alerts-advisories/cisco-security-advisory-av26-1102>
10. AWS, "Amazon RDS for Oracle and SQL Server storage autoscaling on additional storage volumes", 2026-10-29 — <https://aws.amazon.com/about-aws/whats-new/2026/10/amazon-rds-oracle-sqlserver-autoscaling-additional-storage-volumes>
11. AWS, "Aurora PostgreSQL post-quantum TLS key exchange", 2026-10-29 — <https://aws.amazon.com/about-aws/whats-new/2026/10/aurora-postgresql-post-quantum-tls-key-exchange/>
12. AWS, What's New (MSK Connect 업데이트, 2026-10-29) — <https://aws.amazon.com/about-aws/whats-new/recent/>
13. Azure Blog, Announcements ("Azure Cloud HSM Hardware Audit Logging", 2026-10-29) — <https://azure.microsoft.com/en-us/blog/content-type/announcements/>
14. Google Cloud, Release notes (2026-10-29) — <https://docs.cloud.google.com/release-notes>
15. 카카오클라우드, 공지사항 2078 (블록 스토리지 지연), 2026-10-29 — <https://kakaocloud.com/more/notices/2078>
16. nodejs/node, Release v26.13.0, 2026-10-28 — <https://github.com/nodejs/node/releases/tag/v26.13.0>
17. Spring, Blog releases — <https://spring.io/blog/category/releases>
18. modelcontextprotocol, GitHub Releases — <https://github.com/modelcontextprotocol/modelcontextprotocol/releases>
19. MLflow, GitHub Releases — <https://github.com/mlflow/mlflow/releases>
20. Langfuse, GitHub Releases — <https://github.com/langfuse/langfuse/releases>
21. 위시켓, 프로젝트 159357 (원 공고), 등록 2026-10-29 — <https://www.wishket.com/project/159357/>
22. 위시켓, 프로젝트 찾기 (목록 페이지, 2026-10-30 조회) — <https://www.wishket.com/project/>
