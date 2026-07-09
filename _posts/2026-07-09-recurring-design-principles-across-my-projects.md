---
layout: post
title: "여러 프로젝트, 반복 되는 설계 — 내가 계속 고르는 6가지"
date: 2026-07-09 19:40:00 +0900
categories: [architecture, backend, design, portfolio]
tags: [hexagonal, archunit, outbox, idempotency, polyglot-persistence, pgvector, gitops, msa, monolith, design-principles]
---

프로젝트 를 여러 개 굴리다 보면 알게 된다. **설계 에 정답 은 없지만, 내가 반복 해서 고르는 결정 은 있다.** 정산 시스템 이든 청각 재활 훈련 이든 XR 신앙 앱 이든 — 도메인 은 전혀 다른데, 뼈대 를 세우는 방식 은 자꾸 같은 곳 으로 수렴 한다.

이 글 은 내 프로젝트 들(정산 `settlement` · 커머스 MSA `sparta` · 청각재활 `ASAT` · XR `lemuel-xr` · 인프라 `helm-deploy`) 을 관통 하는 **6가지 설계 원칙** 을, 각각 *실제 코드* 로 풀어 본다. 패턴 이름 을 외우는 글 이 아니라, *왜 매번 이걸 고르는지* 에 대한 기록 이다.

---

## 1. 경계 를 컨벤션 이 아니라 *컴파일러* 로 강제 한다

헥사고날(ports & adapters) 은 이제 기본 값 이다 — `settlement`, `ASAT`, `lemuel-xr` 전부 `domain → application → adapter` 로 나뉘고, 의존 방향 은 항상 안쪽 을 향한다. 도메인 은 순수 POJO 다. Spring/JPA 어노테이션 이 도메인 에 스며들지 않는다.

문제 는 이 규칙 이 *말* 로만 있으면 반드시 무너진다는 것 이다. 그래서 `settlement` 에서는 **ArchUnit 테스트 로 경계 를 빌드 실패 로 강제** 한다:

```
1. domainShouldNotDependOnSpringOrJpa      — 도메인 에 Spring/JPA import 금지
2. applicationServiceShouldNotUseJpaRepositoryDirectly — 서비스 는 port 인터페이스 로만
3. adaptersShouldNotDirectlyReferenceOtherDomainsPersistence — 도메인 간 JPA 엔티티 참조 금지
4. portsShouldBeInterfaces                 — 모든 *Port 는 인터페이스
```

> 리뷰 는 확률 이고, ArchUnit 은 보장 이다. "다음 에 고치자" 가 아니라, *위반 하면 CI 가 빨개진다.*

예외 가 필요한 곳(CQRS read 경로 3곳) 은 화이트리스트 로 명시 한다 — 규칙 을 끄는 게 아니라, *예외 를 문서화* 하는 방식. 경계 는 지켜질 때 가 아니라, 지켜지도록 *기계 가 감시* 할 때 살아 있다.

---

## 2. 이중 쓰기(dual-write) 를 없앤다 — Transactional Outbox

분산 시스템 에서 가장 흔한 버그 는 **"DB 는 바뀌었는데 이벤트 는 안 나갔다"** (혹은 그 반대) 다. `settlement` 은 이걸 **Transactional Outbox** 로 원천 차단 한다.

정산 이 생성 되면, *같은 트랜잭션 안* 에서 `outbox_events` 에 이벤트 레코드 도 함께 insert 한다. DB 커밋 이 곧 이벤트 기록 이다 — 둘 이 원자적 으로 묶인다. 그리고 별도 폴러(`OutboxPublisherScheduler`) 가 `PENDING` 레코드 를 `FOR UPDATE SKIP LOCKED` 로 집어 Kafka 로 발행 하고 상태 를 넘긴다:

```
PENDING ──(Kafka send 성공)──▶ PUBLISHED
   │
   └──(재시도 소진)──▶ FAILED
```

`SKIP LOCKED` 덕에 폴러 를 여러 개 띄워도 같은 이벤트 를 두 번 안 집는다. `claimed_at` 리스(1분) 로 죽은 워커 의 레코드 도 회수 된다. 토픽 은 `lemuel.<aggregate>.<event>` 규칙(`lemuel.payment.captured` 등) 으로 일관 한다.

**애플리케이션 코드 에서 "DB 저장 후 Kafka 발행" 을 직접 하지 않는다.** 그 두 줄 사이 에서 프로세스 가 죽으면 정합성 이 깨지니까. 대신 *DB 트랜잭션 하나* 에 다 담고, 발행 은 뒤에서 따로.

---

## 3. at-least-once 를 idempotent 수신 으로 받는다 — 3계층 멱등

Kafka 는 *at-least-once* 다. 리밸런싱·재시도 로 컨슈머 는 **같은 이벤트 를 두 번** 받을 수 있다. `settlement` 은 어느 한 층 이 뚫려도 다음 층 이 막는 **3계층 멱등** 으로 방어 한다:

| 층 | 위치 | 제약 | 막는 것 |
|----|------|------|---------|
| **L1** | 발행측 | `outbox_events.event_id UUID UNIQUE` | 같은 작업 이 이벤트 를 중복 insert |
| **L2** | 수신측 | `processed_events(consumer_group, event_id) PK` | 같은 컨슈머 가 같은 이벤트 재처리 |
| **L3** | 비즈니스 | `settlements.payment_id UNIQUE` | L2 가 뚫려도 결제당 정산 최대 1건 |

L3 가 핵심 이다. L1·L2 는 *메시징* 레벨 방어 라 코드 버그 로 우회 될 수 있지만, L3 는 **DB 자연키 제약** 이라 무슨 일 이 있어도 "결제 하나 에 정산 둘" 은 물리적 으로 불가능 하다. 통합테스트(`SettlementIdempotencyIntegrationTest`) 가 세 층 을 전부 검증 한다.

> 교과서 패턴: *at-least-once 메시징 + idempotent 수신 = effectively-once*. 정확히-한번 배달 은 환상 이고, 정확히-한번 *처리* 는 수신측 이 만든다.

---

## 4. 저장소 는 *역할* 로 나눈다 — 폴리글랏 + 벡터 검색

하나 의 DB 로 모든 걸 하려 하면 어딘가 삐걱 인다. 그래서 저장소 를 **역할별** 로 나눈다.

- **`sparta` (커머스)** — 트랜잭션 은 PostgreSQL, 전문 검색 은 Elasticsearch 8.15(`products` 인덱스), 의미 유사도 는 pgvector **HNSW, 3072차원**(Gemini 임베딩, 코사인). 세 저장소 가 이벤트 기반 백필 로 최종일관성 을 맞춘다.
- **`lemuel-xr` (XR)** — 성경 3000+ 구절 을 `text-embedding-3-small` 로 임베딩 해 `scripture_embeddings(embedding vector(1536))` 에 HNSW(`m=16, ef_construction=64`) 로 색인. 감정 "외로움" 이 키워드 목록 없이 시편 을 찾아온다.
- **`ASAT` (재활)** — PostgreSQL(측정값 은 전부 `NUMERIC`, `double` 금지) + Redis(대시보드 캐시) + MinIO(분석 산출물 객체).

공통 은 **벡터 검색 을 외부 벡터 DB 없이 Postgres 안** 에서 푼다는 것. 사용자 1만 미만 규모 에선 Pinecone 을 붙이는 게 오버 다 — `ALTER` 없이 10만 건 까지 스케일 되고, 운영 포인트 도 안 늘린다. **필요 해지면 그때** ECK/전용 벡터DB 로 승격.

---

## 5. 분리 비용 은 *필요 할 때* 낸다 — 모놀리스 + 사이드카 / 라이브러리 모드

MSA 는 공짜 가 아니다. 배포·관측·정합성 비용 이 서비스 수 만큼 곱해진다. 그래서 나는 **논리적 분리 는 지금, 물리적 분리 는 나중** 원칙 을 쓴다.

**`ASAT` — 모놀리스 + 사이드카.** 코어 는 Java 모놀리스(동접 50 이하 연구용) 지만, 무거운 분석 은 Python 사이드카 로 뗐다. 단, 실시간 경로 엔 절대 안 끼운다. 경계 를 *권한* 으로 못 박았다:

- Python 은 `asat_analysis_ro` 롤(read-only) 로만 메인 스키마 접근 → INSERT 는 PostgreSQL 단 에서 거부.
- 산출물 메타 등록 은 반드시 Java `POST /api/internal/reports`(`X-Internal-Token`, `ROLE_INTERNAL`) 경유.
- 다운로드 는 항상 presigned URL(10분 TTL) — Java 가 본문 을 스트리밍 안 한다.

**`settlement` — 라이브러리 모드.** `settlement-service` 는 코드 상 order-service 에 의존 0(헥사고날 경계 강제) 이지만, *물리적 으론* order-service 의 fat jar 에 라이브러리 로 번들 된다:

```kotlin
tasks.named<BootJar>("bootJar") { enabled = false }  // 독립 jar 끔
```

덕분 에 지금 은 프로세스 하나 로 운영 하다가, 트래픽 이 정당화 할 때 독립 bootJar + DB 분리(ADR-0020, 이벤트 소싱 프로젝션) 로 넘어간다. **"언젠가 MSA" 를 위해 오늘 MSA 비용 을 내지 않는다.**

---

## 6. 배포 를 *무인화* 한다 — GitOps app-of-apps + Image Updater

마지막 은 인프라 다. `helm-deploy` 는 **모든 배포 가 git 을 단일 진실원천** 으로 삼는 GitOps 다.

- **app-of-apps** — `root-app` 하나 가 `argocd-applications/` 디렉토리 를 recurse 로 감시 → Application 매니페스트 를 git 에서 고치면 자동 반영. 앱 27개 가 이 밑 에 달린다.
- **ArgoCD Image Updater** — CI 가 커밋 sha 태그 를 GHCR 로 밀면, Image Updater 가 그 sha 를 `values.yaml` 에 **git write-back** → ArgoCD 가 자동 rollout. `:latest` 는 무시 하고 40-hex sha 만 추적(`allow-tags: ^[0-9a-f]{40}$`) 해 태그 경합 을 피한다.
- **selfHeal** — 누가 `kubectl edit` 로 클러스터 를 직접 만지면 git 기준 으로 되돌린다. *영구 변경 은 반드시 git 을 통과* 해야 한다.

이 구조 의 값 어치 는 사고 날 때 드러난다. 최근 `sparta-product` 가 새 이미지 에서 Kafka 부트스트랩 설정 누락 으로 CrashLoop 났을 때 — 구 ReplicaSet 이 서빙 을 유지 한 채(무중단), `values.yaml` 한 줄(cross-namespace Kafka FQDN) 을 고쳐 push 하니 ArgoCD 가 알아서 새 버전 으로 굴려 냈다. 클릭 없이, git 하나 로.

---

## 그래서 — 도메인 은 달라도 뼈대 는 같다

여섯 을 한 줄 씩 요약 하면:

1. **경계** 는 ArchUnit 으로 컴파일러처럼 강제.
2. **이벤트** 는 Outbox 로 이중 쓰기 를 없앰.
3. **중복 수신** 은 3계층 멱등 으로 effectively-once.
4. **저장소** 는 역할 로 쪼개고 벡터 는 Postgres 안 에서.
5. **분리 비용** 은 라이브러리/사이드카 로 미룸.
6. **배포** 는 GitOps 로 무인화.

이것 들 은 특정 프레임워크 나 유행 이 아니다. *정합성·경계·가역성* — 시스템 이 커져도 안 무너지게 하는 세 가지 를 각각 다른 각도 에서 지키는 방법 일 뿐 이다. 도메인 은 정산 이든 재활 이든 신앙 이든 바뀌지만, **"틀렸을 때 어떻게 덜 아프게 할까"** 라는 질문 은 안 바뀐다.

좋은 설계 는 화려한 패턴 이 아니라, *같은 원칙 을 지루 하게 반복* 하는 데서 나온다. 그리고 그 반복 이, 프로젝트 를 여러 개 굴려도 밤에 잘 자게 해준다.

---

_관련: [백엔드 설계 의 세 축]({% post_url 2026-07-07-backend-design-three-axes %}) · [GitOps 자동 배포 와 안전장치]({% post_url 2026-07-02-gitops-auto-deploy-safety %}) · [정산 시스템 을 KPI 로]({% post_url 2026-07-03-settlement-system-kpi %})_
