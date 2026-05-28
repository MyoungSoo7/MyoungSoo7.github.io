---
layout: post
title: "개발 리드 30 년 변천사 — 최신 기술 추종과 오버엔지니어링의 함정, 그리고 2026 생성형 AI / Agent 시대 백엔드·DevOps 리드의 좌표"
date: 2026-05-29 02:50:00 +0900
categories: [engineering, leadership, ai]
tags: [engineering-leadership, tech-lead, over-engineering, resume-driven, cpu, memory, storage, ai-agent, generative-ai, backend, devops, sre]
---

*개발 리드 (Engineering Lead / Tech Lead)* 라는 직책은 *지난 30 년간 본질이 한 번도 변하지 않았지만 *그 표면* 은 매 5 년마다 완전히 바뀌었다*. 1995 년 리드와 2026 년 리드가 *같은 일* (팀이 *올바른 시스템* 을 *지속 가능하게* 만들도록 의사결정) 을 하지만, *그 결정의 변수* 는 달라졌다.

특히 2026 년 현재 — 생성형 AI 와 AI Agent 가 산업의 모든 layer 를 뒤흔드는 시점 — *리드의 좌표* 가 *흔들리고 있다*. 무엇이 바뀌고, 무엇이 안 바뀌었는가? *오버엔지니어링과 최신 기술 추종의 함정* 이 *AI 시대에 어떤 새 옷* 을 입었는가?

이 글은 *30 년 변천사 → CPU/메모리/스토리지로 본 오버엔지니어링 → AI 시대 백엔드/DevOps 리드의 좌표* 세 축으로 정리한다.

---

## TL;DR

- 개발 리드의 *본질*: *"가장 적은 변경으로 가장 큰 가치"* 를 *지속 가능하게*. 30 년간 안 변함
- 개발 리드의 *표면*: 1990 (메인프레임) → 2000 (Java EE) → 2010 (Cloud, MSA) → 2020 (K8s, Cloud-native) → 2026 (AI Agent, Platform)
- *최신 기술 추종* 의 함정 = Resume-Driven Development. 회사 자산이 아닌 *개인 이력서* 를 위한 선택
- *오버엔지니어링* 은 *CPU/메모리/스토리지* 관점에서 명확히 진단 가능 — *측정 가능한 낭비*
- **2026 AI 시대의 리드**: AI 가 *코드 작성* 은 가속하지만 *시스템 결정* 은 더 어려워짐. 리드의 *판단 능력* 이 *더* 중요해짐

---

## 1. 개발 리드의 30 년 변천사

### 1990 년대 — *시스템 엔지니어* 의 시대

- 환경: 메인프레임, COBOL, RPG, C, 처음 등장한 Java
- 리드의 일: *하드웨어 spec* 결정, *DB 스키마* 설계, *공용 라이브러리* 정리, *주니어 코드 리뷰*
- 도구: SVN 도 없음. 텍스트 에디터 + Makefile
- 팀 크기: 5-15 명, *모두 한 사무실*
- 배포 주기: *분기* 단위. 한 번 배포에 *수 일 다운타임* 흔함

리드의 *물리적* 책무: *서버 한 대당 메모리 256MB / 디스크 4GB 시대* — 자원 절약이 *생사 문제*. *알고리즘 효율* 이 *지금의 10 배* 중요.

### 2000 년대 — *J2EE / .NET / 웹 1.0* 의 시대

- 환경: J2EE (EJB!), Struts, Spring 1.x 등장 (2004), .NET 1.x
- 리드의 일: *프레임워크 선택*, *애플리케이션 서버* 운영 (WebLogic, WebSphere, JBoss)
- 도구: CVS → SVN, Eclipse / IntelliJ 초기, JUnit
- 팀 크기: 10-30 명, *외주 + 내부* 혼합 흔함
- 배포 주기: *월* 단위. WAR 파일 직접 업로드

리드의 *고민*: EJB Entity Bean 의 끔찍한 성능 → Hibernate 도입 결정. *프레임워크 결정이 5 년 갔다*.

### 2010 년대 — *Cloud + MSA + DevOps* 의 시대

- 환경: AWS / GCP / Azure, Docker (2013), K8s (2014), Spring Boot (2014), React/Vue
- 리드의 일: *MSA 분리 vs 모놀리스 유지*, *온프레미스 vs 클라우드*, *DevOps 문화 도입*
- 도구: Git, GitHub/GitLab, Jenkins, Travis CI, Slack
- 팀 크기: *팀당 5-8 명* (마이크로팀), *팀 N 개 = 서비스 N 개*
- 배포 주기: *일* 단위. CI/CD 자동화

리드의 *고민*: "마이크로서비스를 너무 일찍 도입한 후회" 가 *수많은 회사에서* 발생. *Distributed Monolith* 의 시대.

### 2020 년대 (초중반) — *Cloud-native / Platform Engineering* 의 시대

- 환경: GitOps (ArgoCD/Flux), Service Mesh (Istio/Linkerd), Observability (Prometheus/Grafana/Tempo/Loki)
- 리드의 일: *Platform Engineering 팀 운영*, *내부 PaaS 구축*, *DevEx 투자*
- 도구: K8s + Helm/Kustomize, Terraform/Pulumi, ArgoCD, Datadog/Honeycomb
- 팀 크기: *Stream-aligned team (5-8) + Platform team (10-20)* 모델 (Team Topologies)
- 배포 주기: *시간* 단위, *trunk-based development*

리드의 *고민*: K8s 운영 복잡성, *플랫폼 팀 vs 제품 팀* 의 경계, *cloud cost* 폭증 통제

### 2020 년대 후반 (2024~2026) — *AI / Agent* 의 시대

- 환경: 생성형 LLM (Claude/GPT/Gemini), AI Agent (Claude Code, Cursor, Devin), RAG, Vector DB
- 리드의 일: *AI 도구의 팀 도입*, *Agent harness 설계*, *생성된 코드의 책임성*, *AI 학습 데이터/보안 정책*
- 도구: GitHub Copilot, Claude Code, Cursor, Continue.dev, MCP servers
- 팀 크기: *AI 가 1 명 대체 + 시니어가 N 명 만큼 작업* — 팀 크기 *동결 또는 축소*
- 배포 주기: *AI Agent 가 새벽에 PR 만듦*, *사람은 검토만*

리드의 *새 고민*: *AI 가 만든 코드의 long-term 영향*, *지식의 외주화*, *주니어 성장 곡선의 변화*, *Resume-Driven AI 도구 도입*

---

## 2. *본질* 은 30 년간 안 변했다

표면이 매 5 년 바뀌어도 리드의 *본질* 은 한 줄로 같다:

> **"가장 적은 변경으로 가장 큰 가치를, 지속 가능하게."**

이걸 *3 가지 균형* 으로 풀면:

| 균형 | 한쪽 | 다른쪽 |
|---|---|---|
| **속도 vs 안정** | 빠른 출시 | 운영 부담 |
| **현재 vs 미래** | 지금 needs | 6 개월 후 needs |
| **개인 vs 팀** | 한 명의 효율 | 팀의 지속 가능성 |

30 년 전이나 지금이나, 리드가 *흔들리는 변수* 는 같다. 변하는 건 *변수의 단위* — 메모리 256MB 였던 게 256GB 가 되고, *팀에 한 명의 AI agent 추가* 같은 새 변수가 생긴다.

좋은 리드 = *변수의 단위 변화* 에 *과민반응 않고* (최신 기술 추종 안 함), *동시에 무관심도 않고* (정체되지 않음), *본질에 비추어 *판단*.

---

## 3. 최신 기술 추종의 함정 — *Resume-Driven Development*

### 3.1 증상

- 새 트렌드 (Rust, GraphQL, MSA, Serverless, Kubernetes, AI Agent ...) 가 나오면 *"우리도 도입하자"* 가 *첫 반응*
- 도입 결정 *5 분*, 마이그레이션 *5 개월*, 후회 *5 년*
- 도입 *후* 에 *"진짜 필요했나"* 라는 질문이 *처음으로* 나옴
- 그 결정을 주도한 사람은 *이미 다른 회사* 에 있음 (Resume 에 "K8s 도입 경험" 추가하고)

### 3.2 명명

이 패턴엔 정식 이름이 있다 — **Resume-Driven Development (RDD)** 또는 **CV-Driven Development**. 회사의 *기술 결정* 이 *조직의 needs* 가 아닌 *개인의 이력서* 를 위해 이뤄지는 안티패턴.

### 3.3 사례 — "MSA 가 답" 의 후폭풍 (2014-2020)

- 2014: Martin Fowler 의 *Microservices* 글 → 모든 회사가 *MSA 가 답* 으로 인식
- 2015-2018: 수많은 모놀리스가 *MSA 로 분리*
- 2018-2020: *분산 모놀리스* 의 고통이 *대규모로 드러남*. Segment 같은 회사가 *MSA → 모놀리스 회귀* 발표
- 2020 이후: "*Modular Monolith* 부터 시작하라" 가 *시니어들의 합의*

이 5 년 동안 *수백 회사가 동일한 함정* 에 빠졌고, *수천 엔지니어의 시간이 낭비* 됐다. *모두 그 시점의 트렌드* 였기 때문에.

### 3.4 *왜* 이 함정에 빠지나

- **FOMO** (Fear of Missing Out) — 우리만 안 쓰는 게 두려움
- **컨퍼런스 효과** — 대기업의 성공 사례가 *우리에게도 적용된다는 착각*
- **공급자 마케팅** — 클라우드 / 도구 회사가 *FUD* 를 활용
- **개인의 이력서 동기** — 위 RDD

### 3.5 진단 질문 5 가지

새 기술 도입 고민 시:
1. *지금 시스템* 의 *어떤 정확한 문제* 를 해결하는가?
2. *그 문제가 정말 큰가?* (downtime / cost / dev velocity 측정 가능)
3. *기존 기술의 한계* 인가 *팀 역량* 의 한계인가? (후자면 새 기술이 답 아님)
4. *도입 후 5 년* 동안 *누가 운영* 할 것인가?
5. *지금 도입 안 했을 때* 의 *진짜 비용* 은?

5 가지 모두 명확한 답 못 하면 *현재 기술 유지* 가 정답.

---

## 4. 오버엔지니어링 — CPU / 메모리 / 스토리지 관점에서

오버엔지니어링은 *추상적 단어* 가 아니다. *측정 가능한 자원 낭비* 다.

### 4.1 CPU 관점

**과잉의 흔한 패턴:**

1. **Reactive 강제 도입** — 트래픽 100 RPS 도 안 나오는 시스템에 WebFlux. *코드는 3 배 복잡해지고 디버깅 어려워짐*, CPU 절감은 *측정 불가*
2. **Microservice 분리** — 모놀리스에선 *함수 호출 (~ns)*, MSA 에선 *HTTP 호출 (~ms)*. **1,000,000 배** 느려짐. CPU 의 *대부분이 직렬화/역직렬화/네트워크 처리*
3. **과도한 추상화** — *Hexagonal × Clean × DDD × CQRS × Event Sourcing* 풀스택. *1 줄 read* 가 *15 클래스 거침*. CPU 자체는 작지만 *개발 시간 = 미래 CPU*
4. **Microservice → Saga** — 모놀리스에선 *DB 트랜잭션 1 회*, MSA + Saga 에선 *10 개 서비스 + 보상 트랜잭션 + outbox + idempotency*. *CPU + 운영 비용 폭증*

**적정한 패턴:**

- *작은 시스템*: 모놀리스 + JPA + sync controller. CPU 낭비 *최소*
- *큰 시스템 (100k RPS+)*: 측정 후 *병목 부분만* MSA / Reactive 도입

### 4.2 메모리 관점

**과잉의 흔한 패턴:**

1. **모든 것을 캐시** — Redis 가 *진짜 hot data* 만 캐시해야 안전. *모든 read 결과 캐시* 면 stale data + 메모리 폭증
2. **JVM heap 무한 확장** — `-Xmx32g` 같은 거대 heap. *GC pause 가 폭증* 하고 *대부분의 메모리는 안 쓰는 free space*
3. **In-memory DB 흉내** — 진짜 데이터는 *DB 에* 있어야. *Application 이 DB 흉내내면* 메모리 + 복잡성 폭증
4. **Microservice 마다 자체 캐시** — 같은 데이터가 *서비스마다* 캐시 사본. 메모리 N 배 + 동기화 지옥

**적정한 패턴:**

- 캐시: *80/20 원칙* 으로 *진짜 hot 한 20%* 만
- Heap: *production 측정 후* 적절히. *그 다음* Native Memory Tracking
- *분산 캐시* 도입은 *2-3 서비스가 같은 데이터를 자주 조회* 가 *측정* 되고 나서

### 4.3 스토리지 (SSD / HDD) 관점

**과잉의 흔한 패턴:**

1. **All-SSD** — *로그 / 백업 / 감사 데이터* 도 SSD. *비용 5-10 배*. HDD 가 *지속 sequential write 에는 SSD 만큼 빠름*
2. **모든 데이터 Elasticsearch** — Elasticsearch 가 *모든 read 의 답* 이 됨. *raw data 가 elasticsearch 인덱스* 라 *RDBMS 대체 시도* → 메모리 폭증, 인덱스 폭증, 복구 어려움
3. **NoSQL 강제 도입** — Postgres 로 *충분히 잘 돌아가는* 시스템에 *MongoDB 도입*. Schema-on-read 의 *고통* + *트랜잭션 보장 상실*
4. **백업 정책 부재** — *raw production data 만* 보관. 사고 시 *복구 불가*. 또는 *모든 데이터 30 일 보관* → 비용 폭증

**적정한 패턴 (스토리지 tier 분리):**

```
Hot data (실시간 조회)        → SSD (NVMe 또는 SATA)
Warm data (가끔 조회)         → SSD (cheaper) 또는 HDD
Cold data (감사/규제용)        → HDD 또는 S3 Glacier
Backup                       → S3 + versioning + cross-region
```

Elasticsearch ILM (Index Lifecycle Management) 으로 *hot → warm → cold → delete* 자동.

### 4.4 *측정 가능한 오버엔지니어링 진단*

```
지표:
1. CPU 사용률 — 평균 40%↓ 면 *과투자*, 80%↑ 면 *부족*
2. 메모리 사용률 — heap 50%↓ 면 *과투자*
3. 스토리지 IOPS — SSD on 인데 IOPS 가 *낮으면* SSD 낭비
4. 코드 라인 vs 비즈니스 가치 — *비슷한 기능* 인데 *10 배 라인 수* 면 과잉 추상화
5. 새 기능 추가 시간 — *2 줄 변경* 이 *5 일 걸리면* 과잉 추상화
```

이 5 가지를 *분기 단위* 로 측정하면 *오버엔지니어링이 데이터로 보임*.

---

## 5. 적정 기술 (Right-Sized Technology) 의 원칙

### 5.1 원칙 1: *측정 → 결정 → 측정*

- 새 기술 도입 *전에* 베이스라인 측정
- 도입 *후* 같은 지표 측정
- 개선 없으면 *롤백*. 자존심 안 부림

### 5.2 원칙 2: *Boring Technology* 우선

Dan McKinley 의 글 [Choose Boring Technology](https://boringtechnology.club/) 이 핵심:

- 회사는 *3 개의 innovation token* 만 가짐. *낯선 기술 1 개 = 1 token*
- 나머지는 *지루한* (검증된, 안정된) 기술
- *우리가 풀려는 문제* 가 *진짜 차별화 포인트* 가 아니면 *Postgres + Boring framework*

### 5.3 원칙 3: *복잡성은 항상 어딘가에 있다*

- 단순한 시스템 = 모놀리스 + 한 DB. 복잡성은 *코드 내부*
- MSA = 코드는 작아지지만 *운영/분산 시스템 복잡성* 폭증
- *Trade-off* — 복잡성은 *제거되지 않고 이동* 함

좋은 리드는 *복잡성을 *팀이 잘 다루는 곳* 으로* 옮긴다. *낯선 곳에 옮기지 않음*.

### 5.4 원칙 4: *YAGNI* + *KISS* + *DRY* 의 균형

- **YAGNI** (You Aren't Gonna Need It) — *지금 안 필요한 거 안 만듦*
- **KISS** (Keep It Simple, Stupid) — *단순함의 가치*
- **DRY** (Don't Repeat Yourself) — *중복 제거*

세 원칙은 *서로 충돌* — DRY 를 위해 *추상화* 하면 KISS 깨짐. *균형* 이 리드의 일.

*경험 법칙*: 같은 코드 *3 번 나타나기 전까지* 추상화 미룸. *2 번까지는 중복 OK*.

---

## 6. 2026 — *AI Agent 와 생성형 AI* 의 시대

### 6.1 *지금까지의 변화* 요약

```
2022 11: ChatGPT 출시 → 일반 대중에 LLM 가시화
2023 03: GPT-4 → 전문 영역 진입
2023 11: GitHub Copilot Chat → IDE 통합 본격화
2024 06: Anthropic Claude 3.5 Sonnet → 코딩 능력 도약
2024 11: MCP (Model Context Protocol) 공개 → Agent 표준화
2025: Cursor / Claude Code / Devin / Cognition 등 *agent 형 도구* 폭증
2026: AI Agent 가 *PR 작성 / CI 응답 / 운영 작업* 까지 — *공동 작업자* 로 자리잡음
```

### 6.2 무엇이 바뀌었나

✅ **코드 작성 속도** — 3-5 배 빨라짐 (단순 boilerplate, CRUD, 테스트)
✅ **언어/프레임워크 진입 장벽** — 새 언어 학습 *수개월 → 수일*
✅ **문서 작성 / 코드 리뷰** — agent 가 1차 리뷰 가능
✅ **인프라 코드 (Terraform, K8s YAML)** — 양산 속도 ↑

❌ **시스템 결정** — *모놀리스 vs MSA*, *Postgres vs NoSQL* 같은 결정은 *AI 가 못 함*. 컨텍스트 이해 한계
❌ **장기적 코드 품질** — AI 생성 코드는 *현재 시점 동작* 에 최적. *5 년 후 유지보수* 는 *여전히 사람 책임*
❌ **분산 시스템 디버깅** — 여러 서비스 + 시간 차 + 부분 실패. *AI 가 가장 약한 영역*
❌ **신뢰성 / 보안 / 컴플라이언스** — AI 의 *환각* 한 번이 *production 사고*. 검증 자동화 필수

### 6.3 *위험 - Resume-Driven AI 도입*

2026 의 RDD 새 모습:
- *"우리도 AI Coder 가 PR 90% 만들어요"* — 채용 어필
- 실제론 *AI 가 만든 코드 검토 시간* + *사고 대응 시간* 으로 *생산성 -20%*
- 그러나 *경영진 / 마케팅* 에 *AI 도입* 으로 보고

*적정* 도입 = *측정 가능한 가치* 가 있는 지점부터 (코드 리뷰, 테스트 생성, 문서, boilerplate). 그 다음 *점진적* 확장.

---

## 7. 백엔드 개발자의 리드 — AI 시대

### 7.1 *바뀐 것*

| 영역 | 이전 | AI 시대 |
|---|---|---|
| CRUD API 작성 | 30 분 | 5 분 |
| 단위 테스트 | 1 시간 | 10 분 |
| 새 라이브러리 도입 | 1 주 (학습) | 1 일 |
| 인프라 코드 (yaml) | 1 일 | 2 시간 |
| 에러 메시지 분석 | 30 분 | 5 분 (LLM 에 붙여넣기) |

### 7.2 *안 바뀐 것 (그리고 더 중요해진 것)*

| 영역 | 왜 AI 가 못 함 |
|---|---|
| **시스템 경계 결정** | 도메인 컨텍스트가 사람에 있음 |
| **트랜잭션 일관성 설계** | 비즈니스 invariants 가 사람에 있음 |
| **장애 대응** | 실시간 + 여러 시스템 + 사람 간 커뮤니케이션 |
| **레거시 마이그레이션 전략** | 정치 + 위험관리 + 시점 결정 |
| **팀의 성장 곡선 관리** | *AI 가 못 하는 것을 사람이 배우게* 하는 코칭 |

### 7.3 *새로운 역할*

백엔드 리드의 *2026 추가 책무*:

1. **AI Agent harness 설계** — 팀의 *agent 가 무엇을 자동으로 할 수 있고 무엇은 사람 승인 필요* 한지 결정
2. **검증 자동화 강화** — AI 가 *틀린 답 가져올 수 있다* 는 전제 하 *불변 검증 게이트* 강화 (ArchUnit, contract test, integration test)
3. **AI 생성 코드 리뷰 표준** — *사람 코드와 동일* 또는 *더 엄격* 한 리뷰
4. **주니어 성장 곡선 재설계** — AI 가 *주니어가 배워야 할 boilerplate* 를 다 해버리면 주니어가 *어떻게 성장* 하는가
5. **지식 외주화 위험 관리** — 팀이 *AI 에 의존* 하다 *AI 가 모르는 영역* 에서 무력화되는 위험

### 7.4 *유지해야 할 것*

- **CS 기초** — 알고리즘, 자료구조, OS, 네트워크. AI 가 코드 짜도 *왜 그 코드인지* 모르면 디버깅 못 함
- **시스템 디자인** — AI 가 안 가르쳐줌. *책 + 실전 경험* 만이 답
- **도메인 깊이** — 비즈니스 *진짜* 이해. AI 는 *우리 도메인* 모름

---

## 8. DevOps / SRE 의 리드 — AI 시대

### 8.1 *DevOps 의 진화 단계*

- 2010: *개발 + 운영 분리 → DevOps 통합* (Phoenix Project)
- 2015: *Site Reliability Engineering* (Google) — SLO 기반 운영
- 2020: *Platform Engineering* — 내부 PaaS, IDP (Internal Developer Platform)
- 2026: *AI-augmented Operations* — agent 가 *알림 분석 / runbook 실행 / 자동 회복*

### 8.2 *AI 가 가장 잘 하는 DevOps 영역*

✅ **알림 첫 응답** — 알림 받고 *대시보드 조회 + 로그 grep + 1차 분석* 까지
✅ **반복 작업 자동화** — Runbook 따라 실행
✅ **로그 / 메트릭 패턴 분석** — 이상 패턴 자동 감지
✅ **인프라 코드 작성** — Terraform, K8s yaml, Helm chart
✅ **문서 / 다이어그램 생성**

### 8.3 *AI 가 위험한 DevOps 영역*

⚠️ **Production 변경** — *agent 가 자동* 으로 변경하면 *사고 시 책임* 모호
⚠️ **장애 진단의 *마지막 1%*** — *여러 시스템의 race condition* 같은 거 못 함
⚠️ **자원 비용 결정** — *우리 비즈니스의 가치* 를 모름. 비용 절감 *과해서* 안정성 해칠 수 있음
⚠️ **보안 사고 대응** — 적이 *AI 의 답을 학습* 해 우회. *사람의 직관* 필요

### 8.4 *2026 SRE/DevOps 리드의 좌표*

**책무 1: AI Agent 의 *권한 경계* 설계**

- 어떤 작업이 *agent 자동* — pod restart, scale-up, log aggregation
- 어떤 작업이 *사람 승인 필수* — production deploy, DB schema 변경, IAM 변경
- 어떤 작업이 *agent 금지* — 결제 시스템 변경, customer data 접근

**책무 2: Toil 의 *재정의***

- 기존 SRE: *반복적 운영 작업 = toil → 자동화* 가 목표
- 2026: *AI 가 toil 흡수* → 사람은 *시스템 설계 / 사고 대응 / 비용 최적화* 같은 *고난이도* 영역에 집중

**책무 3: AI 가 *못 보는 곳* 의 모니터링**

- AI 가 보는 곳: *수치 metric, log pattern*
- AI 가 못 보는 곳: *팀의 burnout 신호, 기술 부채의 *느낌*, 정치적 변화의 시스템 영향*
- 리드의 일: *AI 가 못 보는 곳* 을 *사람이 본다*

**책무 4: 신뢰의 *역설***

AI Agent 가 *너무 잘 동작* 하면 사람이 *AI 를 너무 믿음* → 진짜 사고 시 *사람의 대응 능력 위축*. SRE 리드는 *주기적 fire drill* 로 *사람의 근육* 유지 책임.

---

## 9. 백엔드 vs DevOps — *2026 의 경계 모호화*

전통적으론:
- 백엔드 = 비즈니스 로직 + API
- DevOps = 배포 + 운영

2026 에선:
- 백엔드 개발자도 *K8s yaml, Terraform* 직접 작성 (AI 가 도와줌)
- DevOps 도 *Python / Go 로 자동화 코드* 작성
- *둘의 경계가 모호*

리드의 새 책무: *팀 구성 결정*. 한 팀에 *백엔드 + DevOps + AI Agent harness* 모두 가능한 *T-shaped engineer* 들로 구성할지, *Stream-aligned + Platform team* 으로 분리할지.

내 선호: **Stream-aligned team + Platform team + AI Agent 인프라 (Platform 의 일부)** 모델. *Team Topologies* 의 패턴이 *AI 시대에도 유효*.

---

## 10. *AI 가 바꾸지 않는* 본질 — 결론

30 년 전 리드가 *메모리 256MB 시대* 에 *어떤 알고리즘이 적절한가* 결정했듯, 2026 리드는 *AI Agent 시대* 에 *어떤 자동화 경계가 적절한가* 결정한다.

표면은 다르지만 *본질* 은 같다:

> **"가장 적은 변경으로 가장 큰 가치를, 지속 가능하게."**

이 원칙에 *AI 시대* 의 새 변수가 추가됐을 뿐:
- *AI agent 가 만든 코드의 책임* 은 *여전히 사람*
- *AI 가 가속한 속도* 가 *기술 부채의 가속* 으로 이어지지 않게 *검증 자동화* 강화
- *AI 가 못 하는* 일 (시스템 결정, 도메인 이해, 팀 성장) 에 *사람의 시간* 더 투자

가장 위험한 길은 *최신 기술 / AI 도구* 를 *Resume 를 위해* 도입하는 것. 가장 안전한 길은 *팀의 진짜 needs* 를 *측정* 으로 진단하고, *Boring Technology* 우선, *AI 는 검증 가능한 영역부터* 점진적 도입.

**리드의 가치 = *판단의 질***. AI 가 *코드 작성 능력* 을 commodity 화 했기에, *판단 능력* 의 상대가치는 *오히려 올라갔다*. 5 년 후의 리드도 같은 게임을 할 것이다 — *그때의 새 단위* 로.

---

## 참고

- *The Mythical Man-Month* — Fred Brooks (1975) — 50 년 전 책이 여전히 유효한 이유
- *Accelerate* — Forsgren, Humble, Kim (2018) — DORA metrics
- *Team Topologies* — Skelton & Pais (2019)
- *Site Reliability Engineering* — Google (2016)
- [Choose Boring Technology](https://boringtechnology.club/) — Dan McKinley
- Anthropic, [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- 관련 글:
  - [Harness Engineering 시리즈]({% post_url 2026-05-29-harness-engineering-1-ai-agent-claude-code %})
  - [DDD ↔ MSA 의 상관관계]({% post_url 2026-05-29-ddd-msa-bounded-context-aggregate-event-storming %})
  - [홈랩 K3s Capacity Planning]({% post_url 2026-05-29-homelab-capacity-planning-datacenter-style %})
  - [JVM 구조와 Java 버전 변천사]({% post_url 2026-05-29-jvm-structure-java-version-evolution-production-impact %})
