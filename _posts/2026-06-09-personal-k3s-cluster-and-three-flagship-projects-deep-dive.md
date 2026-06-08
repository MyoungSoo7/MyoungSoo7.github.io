---
layout: post
title: "*개인 K3s 6 노드 클러스터* + *대표 프로젝트 3선* — *코드 / 인프라 / 도메인* 의 *3 축이 *동시에 *production-grade* 인 *살아있는 포트폴리오*"
date: 2026-06-09 00:30:00 +0900
categories: [portfolio, kubernetes, msa, cpp, fullstack, architecture]
tags: [k3s, kubernetes, argocd, gitops, velero, spring-boot, java25, msa, hexagonal, archunit, triple-idempotency, outbox, cpp20, systemd, web-audio-api, next.js, hexagonal-architecture, ddd, portfolio, deep-dive]
---

이 글은 *내가 *집에서 *개인적으로 운영 중인 *K3s 6 노드 클러스터* 와, 그 위에서 (또는 그 *외곽에서*) *살아 움직이는 *대표 프로젝트 3 개* 를, *왜 그 기술을 골랐는가 / 어떻게 운영되고 있는가 / 깨졌을 때 어떻게 푸는가* 의 *3 층 깊이* 로 *친절하게 풀어쓴 *심층 노트* 다.

대상은 두 종류의 독자:

1. **나를 잘 모르는 분 — 이 글로 *내 작업의 *3 축 (코드 / 인프라 / 도메인)* 을 *한 번에 *파악* 하고 싶은 사람**
2. **나와 *같은 *고민 (단일 클러스터 운영, MSA 진화, low-level / fullstack 균형) 을 하고 있는 사람** — *내 의사결정의 *근거* 를 *참고* 하고 *반박* 하고 싶은 사람

*어느 쪽으로 오셔도 *길게 머무실 수 있게* 천천히 쓴다.

---

## TL;DR — *3 줄로 압축*

> *개인 K3s 6 노드 클러스터* 위에 *64 개 ArgoCD Application* 을 *GitOps* 로 굴린다. 그 안에서 *이커머스 + 정산 MSA* (Spring Boot 4 + Java 25) 와 *C++ 시장 데이터 파이프라인* (외곽 systemd) 을 *경계가 분명한 *Bounded Context* 로 운영한다. *이번 주만 *알람 13 건* 을 *postmortem* 으로 학습 압축, *블로그 8 편 (4,000+ lines)* 으로 *조직 자산화*.

**한 그림으로 보면**:

```
[ Cloudflare Edge ]
        │
        ▼
[ Cloudflare Tunnel — 외곽 systemd ]
        │
        ▼
[ K3s 6 노드 클러스터 — lemuel / ilwon / solomon (control-plane HA) + david / louise / isagal (worker) ]
        │
        ├── ArgoCD root-app  ─→  64 Application (GitOps)
        ├── Velero + Kopia   ─→  Cloudflare R2 백업
        ├── Prometheus + ELK ─→  옵저버빌리티
        │
        ├── 프로젝트 ① 이커머스 + 정산 MSA (Spring Boot 4 + Java 25)
        └── 프로젝트 ③ ASAT 청각 재활 (Spring Boot + Next.js + Web Audio API)
                │ (이벤트 / 데이터)
                ▼
        [ 클러스터 *외곽* — bare metal + systemd ]
        └── 프로젝트 ② C++ quant-core (시장 데이터 파이프라인 6 모듈)
```

---

## 0. *왜 이 글을 *지금* 쓰는가*

내가 *얕은 자기소개* 를 좋아하지 않는 이유는 *기술 스택 단어 카드만 *나열* 하면 *반드시 깊은 질문이 *왔을 때 *멈춘다* 는 것을 *경험* 했기 때문이다. *"써봤습니다"* 와 *"왜 그것을 골랐는가"* 사이엔 *큰 강* 이 있다. 이 글은 *그 강을 건넌 흔적* 을 *세 프로젝트로* *증명* 하려는 시도다.

면접관 / 동료 / 미래의 *나 자신* 누구든 *3 분 만에 *대표 작품 설명해보세요* 라고 했을 때 *떠올릴 *대본* 까지 *이 글에 *심어둔다*. 그래서 *길다*. 천천히 읽거나 *목차 보고 *필요한 부분만 *점프* 해도 좋다.

---

# 1. *Kubernetes 인프라* — *개인 K3s 6 노드 클러스터*

## 1.1 *왜 *집에서 *클러스터를 운영* 하는가*

*개인 프로젝트가 늘어나면서* *각 프로젝트를 *어디에 두느냐* 가 *고민의 시작* 이었다. *클라우드 (AWS / GCP)* 에 다 띄우면 *비용이 *월 30 만원* 을 *우습게 넘긴다*. *집 PC 한 대* 에 다 띄우면 *서버 한 대 꺼지면 *모든 사이트 동시 다운*. *팀이 *나 혼자* 인데 *전원 cycle / 패치 / 모니터링* 을 *수동으로* 다 *하는 건 *지속 불가능*.

결론은 *집에 *작은 *production-grade* 환경을 만들자* 였다. 그 결과가 *지금의 6 노드 K3s 클러스터* 다.

> *클라우드는 *간편함을 *돈으로 사는 것*. *온프렘은 *깊이를 *시간으로 사는 것*. *나는 *지금은 *시간* 이 *상대적으로 *돈* 보다 *싸다*. 5 년 후엔 *반대일 수도* 있고, 그때는 *클라우드로 이전 도 *자연스럽게 가능* 하게 *helm-deploy 레포로 *재현 가능* 한 인프라* 로 *유지* 한다.

## 1.2 *규모 + 토폴로지* — *왜 6 노드인가*

```
┌─────────────────────────────────────────────────────────────┐
│   K3s v1.35.4+k3s1  (Ubuntu 24.04 / 26.04 LTS)             │
│   3 control-plane + etcd HA  +  3 worker                    │
└─────────────────────────────────────────────────────────────┘
  lemuel    (control-plane)    Mac mini M2 Pro       4c / 32G
  ilwon     (control-plane)    Mini PC i7-14700      12c / 32G  NVMe
  solomon   (control-plane)    Mac mini 2014          4c / 15G
  louise    (worker)           Mini PC                8c / 16G
  david     (worker)           Mini PC                6c / 15G
  isagal    (worker)           Dell PowerEdge R730xd  40c / 15G / 3.6 TB SAS RAID-0
                                                       ↑
                                            2026/06/06 새벽에 추가한 *듀얼 Xeon*

총합: 74 logical CPU, 125 GB RAM, 4 TB+ 안정 스토리지
```

**왜 *3 + 3* 인가**:

- *etcd HA 의 *quorum 은 *홀수*. *3 노드 control-plane* 이 *가장 가벼운 *고가용 *최소* 단위.
- *worker 3 노드* 는 *DaemonSet 의 *3 인스턴스 + 일반 워크로드의 *replicas: 2 ~ 3* 를 *여유 있게* 흡수.
- *노드의 *다양성* (Mac / PC / Dell 서버) 이 의도된 — *하드웨어 *실패 모드의 *다양성* 을 *학습 자원* 으로 본다.

**왜 *control-plane 노드도 *taint 안 걸고 *워크로드 일부* 가 떨어지나**:

> *작은 클러스터* 에서 *control-plane 의 *유휴 자원* 을 *전혀 안 쓰는 건 *낭비*. 다만 *kube-apiserver + etcd 에 *영향 가는 *고부하 워크로드* 는 *taint 로 *피한다 (ilwon = `dedicated=management:PreferNoSchedule`, solomon = `dedicated=storage:NoSchedule`). *세밀한 격리 *yes, *극단적 격리 *no*.

## 1.3 *GitOps* — *root-app 한 줄이 *64 앱을 *통제*

내 클러스터의 *모든 변경* 은 [helm-deploy 레포](https://github.com/MyoungSoo7/helm-deploy) 의 *한 PR* 로 시작한다. *root-app* 이 이 레포의 `argocd-applications/` 디렉토리를 *재귀 watch* 하면서 *child Application 들을 *자동 생성·갱신·prune* 한다.

```yaml
# root-app.yaml — 한 번만 수동 apply, 그 다음부터는 *전부 자동*
spec:
  source:
    repoURL: https://github.com/MyoungSoo7/helm-deploy
    path: argocd-applications
    directory:
      recurse: true
  syncPolicy:
    automated:
      prune: true       # 파일 삭제 시 → 클러스터에서 Application 제거
      selfHeal: true    # 누군가 kubectl edit 하면 → Git 상태로 복원
```

새 사이트 하나 띄우려면:
1. `argocd-applications/foo.yaml` 추가 + `charts/foo/` Helm 차트 추가
2. `git push`
3. 끝 — *root-app 가 *자동 sync* 해서 *foo Application 생성* + *foo 사이트 띄움*

사이트 하나 내리려면:
1. `argocd-applications/foo.yaml` 삭제 + `git push`
2. 끝 — *prune* 이 *foo Application 제거 + 관련 리소스 회수*

이 단순함이 *6 노드 ↔ 64 앱 ↔ 30+ namespace* 의 복잡도를 *한 사람이 관리 가능* 하게 만든다.

## 1.4 *백업 / DR* — *3 단 안전망*

```
1) 즉시 복구 (Velero + Kopia)
   - 36 BackupRepository (namespace 단위)
   - 매일 자동 / off-cluster Cloudflare R2
   - 복구 시간 목표: < 30 분
   - 명령: velero restore create --from-backup ...

2) 데이터 안전망 (CronJob: pg-backup)
   - 각 사이트 Postgres → pg_dump → backup-pvc → R2
   - 더블 보호 — Velero 가 깨져도 dump 로 복원 가능

3) 인프라 자체 복원 (helm-deploy 레포)
   - 클러스터가 *재현 가능* — apply 한 번이면 *전부* 다시 띄움
```

*세 layer 의 *복구 시간 / 비용 / 보장 수준이 *서로 다른 *각자의 시나리오를 본다*. *어느 *한 layer 만 *완벽하면 안 된다* — *복합 사고가 *현실*.

## 1.5 *알람 → postmortem* 의 *루틴* — *이번 주만 13 건*

> *내가 *진짜 자신 있는 *유일한 자산* 은 *사고를 *반드시 학습 자산으로 *전환* 하는 *루프* 라고 생각한다.

이번 주 *5 일 동안 *처리한 *알람 13 건* 중 *대표 5 건*:

### Case 1 — *KubeJobFailed (velero/kopia ×3)*

```
[resolved] KubeJobFailed
namespace: velero
Job velero/argocd-default-kopia-9nkv7-maintain-job-1778421891769 failed to complete.
```

처음 의심: *Kopia maintenance 가 깨졌나*. 결과: *Kopia 는 정상*. *5 월 10 일에 한 번 실패한 *Job 객체 4 개* 가 *3 주째 *cleanup 안 됨*. *진짜 원인은 *velero ns 의 LimitRange* 의 *`maxLimitRequestRatio.memory = 2`* 와 *`default.memory: 512Mi / defaultRequest.memory: 128Mi` (ratio = 4.0)* 의 *충돌*. *Kopia Pod 가 `resources: {}` 로 들어오면 *기본값 ratio 4.0* 이 *정책 위반* → *admission webhook 거부* → Job Failed.

해결:
1. 좀비 Job 4 개 삭제
2. velero ns 의 LimitRange 자체 제거 (시스템 ns 에 *프로젝트 정책 박는 건 *결합도 폭발*)
3. 다른 6 ns 의 LimitRange 는 `default.memory: 512Mi → 256Mi` 로 *ratio 2.0 정규화*

→ [블로그 글](/2026/06/06/velero-kopia-zombie-job-limitrange-ratio-and-argocd-schema-bug/) 으로 *학습 압축*.

### Case 2 — *kubectl 이 *no route to host*, curl 은 *200**

```
$ kubectl get nodes
Unable to connect to the server: dial tcp 192.168.219.101:6443:
  connect: no route to host

$ curl -k https://192.168.219.101:6443/version
{ ... ok ... }
```

*같은 주소* 에 *같은 시각* 에 *kubectl 은 거짓 응답, curl 은 정상*. *재현 100%*.

원인 추정: *macOS 의 Go net 패키지* 의 *EHOSTUNREACH 캐싱 결함* (확실히 잡진 못함). *진단의 *진짜 문제* 는 *그 직후 *내가 *ping 으로 LAN 스캔* 해서 *5 개 노드가 죽었다* 는 *틀린 가설* 을 *세웠던 것*. 알고 보니 *내가 ping 한 IP 가 *클러스터 노드 IP 가 아니라 *LAN 의 무관한 IP* 였다. *도구의 거짓말 + 내 잘못된 도구 사용* 이 *두 번 가설을 *왜곡*.

해결 (우회 회로):
- `~/.kube/config` 의 *client cert / key / CA 추출*
- `curl --cert ... --key ... --cacert ...` 로 *API 직접 호출*
- *Python + jq* 로 *kubectl get / describe 등가 인터페이스* self-built
- 그날 *모든 운영 변경 (Job 삭제 / LimitRange 수정 / 알람 정리)* 을 *curl 만으로 진행*

→ *kubectl 이 회복될 때까지 *block 되지 않은 것이 *핵심 가치*. 도구의 *추상화 그 너머* 의 layer 한 단 *아래에서 *직접 일할 수 있는 능력* 이 *극단의 디버깅 상황* 에서 *유일한 진단 길* 인 경우가 있다.

### Case 3 — *KubeDaemonSetRolloutStuck (velero/node-agent)*

```
DaemonSet velero/node-agent has not finished or progressed for at least 15 minutes.
```

진단: *solomon 의 *dedicated=storage:NoSchedule taint* 가 *나중에 추가됨*. *DaemonSet 의 `tolerations: []`*. 이미 *solomon 에서 돌고 있던 Pod 가 *evict 되지 않음* (NoSchedule 은 *기존 Pod 안 쫓아냄*, 단지 *새로 스케줄 안 함*). 결과: *솔로몬에 *misscheduled Pod 1 개가 *영원히 남아*, DaemonSet 의 *`numberMisscheduled = 1`* → Prometheus 알람 룰 점화.

해결:
- 미스케줄 Pod 한 개 삭제 → DS controller 가 *솔로몬엔 다시 안 띄움* → `numberMisscheduled = 0`
- (정통 fix 는 Velero chart 에 *toleration 추가* — *별도 PR*)

### Case 4 — *KubeAPIErrorBudgetBurn (이번 주 마지막)*

```
[resolved] KubeAPIErrorBudgetBurn
The API server is burning too much error budget.
```

진단: *3 주 전 (5/20)* 누군가 *traefik 을 제거* 시도했는데, *helm-controller 의 *delete Job 이 *service account 먼저 삭제됨* 으로 *영원히 막힘*. *매 분 *FailedCreate 이벤트* 가 *API server 에 *짧은 5xx* 를 *돌려보냄* → *SLO burn rate* 상승.

해결:
1. `kubectl delete helmchart traefik traefik-crd` (cascade)
2. 그래도 *finalizer (`wrangler.cattle.io/on-helm-chart-remove`)* 가 *stuck* — `metadata.finalizers: []` 로 *force patch*
3. K3s embedded manifest reconciler 가 *traefik 매니페스트 재적용* → 새 helm-install Job → *성공* → *traefik 완전 재설치* ✅

> *내가 *3 주 전에 무엇을 시도했는지 *모르는 상태* 에서 *후속 *증상* 을 만났을 때, *원인을 *시간 역행* 으로 *추적* 하는 능력. 이게 *postmortem 의 *진짜 깊이*.

## 1.6 *기술 스택 한눈에*

| 카테고리 | 기술 |
|----------|------|
| 오케스트레이션 | K3s, ArgoCD, Image Updater, sops-secrets-operator |
| 옵저버빌리티 | kube-prometheus-stack (Prometheus / Grafana / AlertManager) + Loki + ELK + Tempo + node-local-dns |
| 백업 | Velero + Kopia + Cloudflare R2 |
| 인그레스 | Cloudflare Tunnel (외부) + NodePort + Traefik (대체) |
| 시크릿 | sops + age + git-encrypted secrets |
| 워크로드 | Spring Boot · Next.js · Python · C++ |

---

# 2. *대표 프로젝트 ①* — *이커머스 + 정산 MSA (Lemuel)*

> *모놀리스 → Bounded Context 분리* 의 *살아있는 진화 기록*. *Triple Idempotency / Read-only Projection / Outbox* 의 *교과서 패턴* 을 *코드에서 강제 (ArchUnit)* 한다.

## 2.1 *왜 이 프로젝트인가*

내가 *백엔드 깊이* 를 *증명* 하고 싶을 때 *가장 먼저 보여드리는 작품*. *Spring Boot 4 + Java 25 + Gradle multi-module + Outbox + Hexagonal + ArchUnit* 의 *2026 년 *최첨단 조합*. 단순히 *기술 트렌드* 를 *따라간 게 아니라*, *각 기술이 *왜 *지금 *필요한가* 를 *의사결정 단계마다 *명시적으로 기록* 했다.

## 2.2 *기술 스택 — 2026 년 최첨단*

| 구분 | 기술 | 버전 / 비고 |
|------|------|-------------|
| 언어 | Java | **25** (Virtual Thread + Pattern Matching) |
| 프레임워크 | Spring Boot | **4.0.4** |
| 빌드 | Gradle Multi-module (Kotlin DSL) | 9.x |
| 데이터베이스 | PostgreSQL | 17 |
| 메시지 브로커 | Kafka (Redpanda 호환) | 24.x |
| 검색 엔진 | Elasticsearch | 8.17 |
| 캐시 | Caffeine | - |
| 마이그레이션 | Flyway | V1 ~ V37 |
| 회복탄력성 | Resilience4j | - |
| Rate Limiting | Bucket4j | - |
| PDF 생성 | iText | 8 |
| 모니터링 | Micrometer + Prometheus | - |
| PG 연동 | Toss Payments | - |
| 컴파일 시 강제 | **ArchUnit** | *★ 핵심* |

## 2.3 *4 모듈의 *Bounded Context*

```
settlement/                       # Gradle multi-module 루트
├── shared-common/                # java-library — 양 서비스가 공유
│   └── common.{audit, config, exception, outbox, ratelimit, pdf}
├── order-service/                # 🛒 Commerce 서비스 (port 8088)
│   └── lemuel.{user, order, payment, product, category, coupon, review, game}
├── settlement-service/           # 💰 Settlement 서비스 (port 8082)
│   └── lemuel.{settlement, report}
└── gateway-service/              # 🚪 API Gateway (port 8080)
    └── (Spring Cloud Gateway 2025)
```

**원래 *단일 모놀리스* 였다**. *MSA 분리 시점의 *결정 기준* 은 *변경 속도가 *bounded context 별로 *분기한 시점*. *order 가 *주 5 PR / settlement 가 *월 1 PR* 의 *팀 / 사이클 *분리 필요* 가 *MSA 의 *진짜 trigger*. 단순히 *기술 트렌드* 가 아니라 *조직과 도메인 의 *natural fault line*.

## 2.4 *핵심 패턴 1* — *Read-only Projection*

> **목적**: settlement-service 가 order-service *코드 한 줄도 import 하지 않으면서* Order/Payment/User/Product 데이터를 *직접 SELECT* 한다.

```java
// settlement-service/.../adapter/out/readmodel/
@Entity
@Immutable
@Table(name = "payments")
public class SettlementPaymentReadModel {
    @Id private Long id;
    @Column private String orderId;
    @Column private BigDecimal amount;
    @Column private PaymentStatus status;
    // ... setter 없음 — 절대 쓰기 불가
}
```

```kotlin
// settlement-service/build.gradle.kts
dependencies {
    // implementation(project(":order-service"))   ← 의도적으로 *없음*
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    // ...
}
```

**효과**:
- ✅ MSA 의 *코드 경계 100% 확립* — *PR 단에서 *코드 결합 검출 가능*
- ✅ JPA 의 *친숙한 인터페이스* 그대로 사용
- ✅ DB 가 *유일한 결합점* (스키마 마이그레이션 *분리 협의* 만 하면 됨)
- ✅ Kafka 이벤트와 *상호 보완* (이벤트 = 사건, 프로젝션 = 상태 조회)

**면접 함정 질문 — *왜 이벤트만으로 안 되나?***

답: *이벤트는 *시간 흐름의 *사건 sequence*. *프로젝션은 *현재 상태 snapshot*. *어제 마감된 정산 보고서 *조회* 같은 *시간차 query* 를 *이벤트로 *재구성* 하면 *eventual consistency 의 *시간 비용 + 메모리 비용 + 복잡도* 가 *DB 직 read* 보다 *압도적으로 큼*. *Event Sourcing 의 *교과서적 함정*.

## 2.5 *핵심 패턴 2* — *Triple Idempotency*

> PaymentCaptured 이벤트가 *2 번 발행 / 2 번 수신 / 2 번 처리* 되어도 *최종 1 번 효과* 보장.

```
[L1] order-service 측 Outbox
     outbox_events.event_id  UUID UNIQUE
     → 같은 이벤트 *발행 단계* 중복 차단

[L2] settlement-service 측 processed_events
     PK (consumer_group, event_id)
     → 같은 이벤트 *수신 단계* 중복 차단

[L3] settlements 테이블의 비즈니스 UNIQUE
     settlements.payment_id  UNIQUE
     → 같은 결제에 *정산 row 2 개* 절대 불가
```

**왜 *3 단인가 — 오버 엔지니어링 아닌가?***

답: *각 layer 가 *실제로 *다른 실패 모드* 를 막는다*.
- L1 — *발행자의 *중복 발행 (재시도 / 네트워크 timeout)*
- L2 — *수신자의 *중복 처리 (Consumer rebalance / replay)*
- L3 — *비즈니스 키 *오염 (수동 보정 / 마이그레이션 실수 / 다른 service 의 잘못된 호출)*

*하나가 뚫려도 *다음 layer 가 막음*. *각 layer 가 *서로 다른 *실패 모드를 *전담*. *과잉이 *아니라* — *각자의 root cause* 가 *다르다*.

## 2.6 *ArchUnit* — *layer 위반은 *컴파일 fail*

```java
@ArchTest
public static final ArchRule domainShouldNotDependOnSpring =
    noClasses().that().resideInAPackage("..domain..")
               .should().dependOnClassesThat()
               .resideInAPackage("org.springframework..");

@ArchTest
public static final ArchRule applicationShouldNotUseJPA =
    noClasses().that().resideInAPackage("..application.service..")
               .should().dependOnClassesThat()
               .resideInAPackage("jakarta.persistence..");

@ArchTest
public static final ArchRule adaptersShouldNotCrossDomain =
    layeredArchitecture().consideringAllDependencies()
        .layer("settlement").definedBy("..settlement..")
        .layer("order").definedBy("..order..")
        .whereLayer("settlement").mayNotBeAccessedByLayerExcept("application");
```

> *사람이 *지키는* 게 아니라 *기계가 *거절*. *코드 리뷰의 *한 layer 더 *낮은 layer* 에서 *컴파일러* 가 *수문장*.

---

# 3. *대표 프로젝트 ②* — *lemuel-quant-core (C++ 시장 데이터 파이프라인)*

> **K3s 가 *오케스트레이션의 영역* 인 것 처럼, 이 프로젝트는 *latency-critical layer 의 영역*. *시간축 / 정합성 / 격리 요구* 가 *컨테이너 위에 올라가지 않는 워크로드* 의 *살아있는 예시*.**

## 3.1 *왜 *이 프로젝트인가*

*낮은 layer 의 깊이* 를 *증명* 하고 싶을 때 *보여드리는 작품*. *C++20 + CMake + 6 모듈 + gRPC + systemd-on-metal* 의 *system programming 영역*. *모든 모듈이 *왜 C++ 인가* 가 *서로 다른 답* 을 가진다.

## 3.2 *왜 *K3s 안이 아닌 *systemd-on-metal* 인가 — 4 가지 mismatch*

| mismatch | 영향 |
|----------|------|
| *영구 WebSocket 세션 ↔ Pod ephemeral* | Pod 재시작 시 *시세 공백 수 백 ms*. Binance 의 *연결당 *분당 rate limit* 위반 위험. *호가창 *snapshot 재구성* 비용 폭발 |
| *seccomp + cgroup ↔ K8s 의 이미 cgroup* | *judge-engine* 의 *코드 채점 격리 cgroup* 이 *containerd 가 만든 cgroup* 위에 *이중* 으로 쌓임. *권한 *오버라이딩* 의 *예측 불가* |
| *외부 API IP allowlist ↔ Pod random source IP* | 한국투자증권 API 가 *IP 고정 등록* 정책. Pod 의 *SNAT* 가 *어느 노드의 어느 IP 로 나가는지* *예측 어려움* |
| *50MB static binary vs 250MB JRE 이미지* | *오케스트레이션 metadata 가 *binary 자체보다 큼*. *systemd unit 한 줄 = 이미 binary 1 개* |

→ **클라우드 네이티브 *교조* 를 *거절* 하고 *워크로드의 본질* 에 맞는 layer 를 *별도 선택*. 이게 *MSA / SaaS / 마이크로워크로드 시대의 *진짜 deep 한 결정*.

## 3.3 *6 모듈 — 각자의 *왜 C++ 인가**

```
lemuel-quant-core/
├── shared/                          # FeedClient 추상화, 네트워크 / 로깅 / 직렬화
├── modules/
│   ├── judge-engine/                # 코드 채점 (seccomp + cgroup, μs latency)
│   ├── market-feed/                 # Binance WS — GC pause 0
│   ├── stock-feed/                  # KIS OpenAPI — peak tail latency p99.9 < 5ms
│   ├── dart-crawler/                # DART 공시 polling
│   ├── news-pipeline/               # RSS → NER → 감성 → ONNX Runtime C++
│   └── data-warehouse/              # Apache Arrow Parquet + R2 업로드
```

### *judge-engine — 왜 C++ 인가*

코딩테스트 사이트의 *제출 코드* 를 *받아 *외부 코드를 *내 호스트에서 *직접 실행* 한다. *seccomp-bpf 로 *허용 syscall 명시* + *cgroup v2 로 *메모리/CPU 한계 동적 부여*. *Java / Go / Python 의 *helper thread* 가 *예측 못한 syscall 발생시킴* → *seccomp kill*. *C++ + raw syscall + minimal runtime* 이 *유일한 안전한 길*.

### *market-feed — 왜 C++ 인가*

*100+ 채널의 *WebSocket 영구 연결*. *수 천 / 초 의 *틱* 메시지. *Boost.Beast 의 *zero-copy 파서* + *simdjson 의 *SIMD JSON 디코드* 가 *Java Jackson 의 *5-10× 빠름*. *GC pause* 자체가 *존재하지 않음 → 호가창의 *시각 동기 보장*.

### *데이터 warehouse — 왜 Arrow C++ 인가*

*수 십 GB / 일* 의 *write throughput* + *컬럼 압축 (zstd)* + *다른 언어 / 프로세스와 *0 copy IPC*. *Spark / Trino / Polars / DuckDB* 가 *모두 같은 Parquet* 을 본다.

## 3.4 *경계의 contract — 3 시간축*

```
[gRPC (지금)]           현재 상태 질의 — Spring Boot Pod 가 외곽 systemd 의 gRPC 호출
[Redis pub/sub (방금)]  이벤트 fan-out — market-feed → Redis → N 개 구독자
[Parquet on R2 (과거)]  replay / BI / 학습 — 과거 데이터 *전부 영구 저장*
```

> *지금 / 방금 / 과거 전부* 의 *세 시간축에 *각자의 도구*. *클러스터 안의 64 앱 ↔ 외곽 C++ 6 모듈* 이 *3 채널로 *느슨하게 결합*.

---

# 4. *대표 프로젝트 ③* — *ASAT 청각 재활 (eln.lemuel.co.kr)*

> *도메인이 명확한 *fullstack 의 작은 표본*. *Web Audio API + 적응형 staircase + 헥사고날 + 분석 사이드카* 의 *기술이 도메인을 *섬길 때 모든 layer 가 *협조* 한다.

## 4.1 *왜 이 프로젝트인가*

*fullstack + 도메인 깊이* 를 *증명* 하는 작품. *백엔드 + 프론트엔드 + 분석 사이드카 + 인프라* 의 *4 layer 가 *한 도메인 명제* 에 *기계적으로 환원* 된다. *연구용 소프트웨어* 라 *데이터 무결성 (세션 신뢰도 A/B/C/F)* 이 *치명적 요구*.

## 4.2 *도메인* — *청각 변별 임계 (JND)*

```
JND = Just Noticeable Difference
  주파수 JND: 1000Hz 기준 자극과 X Hz 더 높은 자극을 *구별 가능한* X 의 최소값
  공간 JND:   ILD (Inter-aural Level Difference), ITD (Inter-aural Time Difference)

훈련 트랙 3 종:
  V1 (논문 기반)    2AFC      2-down 1-up (70.7%)    주파수 / ILD / ITD / 복합
  V2 (과업지시서)  3AFC      3-down 1-up (79.4%)    공간 측정 / 훈련
  V3 (소음 속 듣기) 2-interval 2-down 1-up         1kHz 순음 in 백색잡음
```

## 4.3 *Web Audio API* — *μs 단위 오디오 합성*

```typescript
const ctx = new AudioContext({ sampleRate: 48000 });

const osc = ctx.createOscillator();
osc.frequency.value = 1000;          // 1 kHz 기준 자극

const panner = ctx.createStereoPanner();
panner.pan.value = -0.5;             // 좌측 50% (ILD)

const delay = ctx.createDelay(0.001);
delay.delayTime.value = 0.000020;    // 20 μs ITD (오른쪽 귀 자극 지연)

osc.connect(panner).connect(delay).connect(ctx.destination);
osc.start();
setTimeout(() => osc.stop(), 200);   // 200ms 자극
```

**왜 *Web Audio API 가 *유일한 정답* 인가**:

- *적응형 staircase 의 *임계가 *trial 마다 변동*. *사전 합성 wav* 는 *모든 차이값 × 수 천 파일* 필요. *합성 = O(1) 메모리, 즉시*.
- *서버 wav 다운로드 0* → *cache invalidation 지옥 0* + *모바일 데이터 0*.
- *μs 단위 정밀도* 가 *서버 wav 의 *양자화 한계를 *넘어섬*.

## 4.4 *기술 스택*

| 구분 | 기술 |
|------|------|
| Backend | Java **25** + Spring Boot **4.0.4** + JPA |
| Frontend | Next.js 16 (App Router) + React 19 + TypeScript |
| 오디오 엔진 | **Web Audio API** (OscillatorNode + StereoPannerNode + DelayNode + AnalyserNode) |
| 상태관리 | Zustand + TanStack Query |
| Null Safety | **JSpecify + NullAway + ErrorProne** |
| 데이터베이스 | PostgreSQL 16 (V1~V36 Flyway) |
| 분석 사이드카 | Python + Prefect + MinIO |
| Export | OpenCSV + Apache POI |
| 인증 | JWT (Access 15min + Refresh 7day httpOnly) |

## 4.5 *K3s 위의 *6 Pod 운영*

```
louise   (worker)        asat-app (Spring Boot) + asat-frontend (Next.js) + asat-redis
ilwon    (storage)       asat-postgres-0 (NVMe local PV) + asat-minio-0 (asat-reports bucket)
david    (worker)        pg-backup CronJob (매일 PG dump)

외부 노출 흐름:
  사용자 → Cloudflare Edge → Cloudflare Tunnel (외부 systemd) → NodePort 30103
                                                                  ↓
                                                       asat-frontend (Next.js)
                                                                  ↓ in-cluster
                                                       asat-app:8080 (Spring Boot)
                                                                  ↓
                                                       asat-postgres-0 / asat-minio-0
```

## 4.6 *세션 신뢰도 A/B/C/F* — *데이터 품질 자동 라벨링*

연구용 데이터의 *치명* 한 부분. *측정 자체의 *품질* 이 *분석의 *유효성* 을 결정.

```
A 등급: reversal 수렴 안정적, RT 분포 정상, 환경 검증 통과
B 등급: reversal 적정 수렴, RT 정상, 환경 검증 통과
C 등급: reversal 수렴 약함 또는 RT 분포 이상 1
F 등급: 연속 동일 응답 비율 > 90%, 또는 환경 검증 실패, 또는 reversal 수렴 안 됨

→ F 등급은 *후속 분석에서 *자동 제외* — *연구 무결성 보장*
```

---

# 5. *횡적 자산* — *블로그 + PR 시리즈*

## 5.1 *블로그* (https://myoungsoo7.github.io)

> 사고를 *블로그 한 편* 으로 *학습 압축* 하는 *루틴*. *같은 사고가 다시 일어나지 않게* + *조직 자산화*.

| 글 | 라인 | 주제 |
|----|------|------|
| Velero Kopia 좀비 Job postmortem | 340 | *알람 mental model* 의 새 layer |
| K3s 의 C++ 의 자리 | 318 | *systemd 외곽 quant-core 의 contract 분리* |
| ASAT eln.lemuel.co.kr 구조 | 364 | *fullstack 의 작은 표본* |
| 물류 SaaS vs 이커머스 SaaS | 398 | *시간축·정합성·외부 N면 연동* 7 가지 차이 |
| (... 기타 Spring AOP / Virtual Threads / 헥사고날 등 ...) | ~2,500 | - |

**총 4,000+ 라인 의 *기술 노트*.** 각 글이 *한 사건* 의 *왜* 와 *어떻게* 를 *후세 (혹은 미래의 나)* 가 *읽고 *같은 사고를 *겪지 않게* 한다.

## 5.2 *ssgb2e 정산 시스템 *3 단 PR* (이번 주)

> *기존 상용 시스템 (신세계 B2E) 의 *정산 배치 를 *직접 분석 → 제안 → 코드 작성 → PR* 의 *전 사이클*.

| PR | 효과 | 라인 |
|----|------|------|
| #1 멱등성 + 트랜잭션 | `@Transactional + NOT EXISTS + DB UNIQUE` 3 단 멱등 방어 — 중복 적재 90% 차단 | +272 / -21 |
| #2 Job 분리 + targetDate | 4 INSERT 를 *4 독립 Job + Orchestrator* — *운영자 REST API* 로 *과거 일자 / 부분 재정산* 가능 | +713 / -69 |
| #3 정합성 검증 + 알람 + Retry | (진행 예정) | - |

---

# 6. *면접에서 *진짜 차별화 되는 *3 가지 답변 카드***

## Card 1 — *"왜 본인이 이 회사 / 이 팀 / 이 직무에 *맞다고 *생각하나?"*

> *코드 / 인프라 / 도메인 의 *3 축이 *동시에 *production-grade* 인 사람은 드뭅니다. *6 노드 K3s 를 *혼자 운영* 하면서 *그 위에서 *Spring Boot 4 + Java 25 + 헥사고날 + Triple Idempotency* 의 *이커머스 + 정산 MSA* 를 굴리고, *그 옆에 *C++ 시장 데이터 파이프라인* 을 *systemd 외곽으로 *경계 분명히* 배치합니다. 단순히 *기술을 써본 게 아니라 *왜 그 기술인가 / 어떻게 운영되나 / 깨졌을 때 어떻게 푸나* 를 *postmortem 8 편 + PR 3 단 분리* 까지 *명시적으로 *학습 압축* 했습니다.*

## Card 2 — *"본인의 *대표 작품 한 가지를 *3 분 안에 설명해보세요."*

> *Lemuel 이커머스 + 정산 MSA 를 *모놀리스 → 4 모듈 MSA* 로 진화시킨 *실제 진화 기록* 입니다. *언제 *Bounded Context 를 분리* 하는가 가 가장 어려운 결정인데, *변경 속도 (PR 빈도) 가 *팀 단위로 분기 한 시점* 을 trigger 로 잡았습니다. 분리 시 *Read-only Projection 패턴* 으로 *settlement-service 가 order-service 코드를 한 줄도 import 하지 않으면서 *DB 직 SELECT* 로 *데이터를 본다*. 메시징은 *Triple Idempotency (Outbox → processed_events → DB UNIQUE)* 로 *3 layer 방어*. 그리고 *ArchUnit* 으로 *layer 위반이 *컴파일 fail* — 사람이 *지키는 게 아니라 *기계가 거절*. 이 패턴의 *진짜 무게* 는 *이 시스템 자체* 가 아니라 *이 시스템을 *팀이 *6 개월 *유지 가능 하게 만든다* 는 것이고, 그게 *MSA 의 *진짜 가치* 라고 생각합니다.*

## Card 3 — *"본인이 *실패한 사례 *하나 설명해보세요."*

> *이번 주에 *macOS 의 kubectl 이 *"no route to host" 로 *재현 100% 거짓 응답* 하는 사건이 있었습니다. 같은 IP 에 *curl 은 200, ping 은 정상*. *처음에 *클러스터 노드 *5 대가 동시에 죽었다*는 *잘못된 가설* 을 *세웠고 — *실제로는 *한 노드만 *잠시 NotReady* 였고, *내가 ping 한 IP 범위에 *클러스터가 *아닌 LAN 의 무관한 호스트* 가 섞여 있었던 게 *원인*. 이게 *진단의 *진짜 *함정* 인데, *도구의 거짓말과 *사용자의 잘못된 도구 사용이 *함께 가설을 *왜곡* 시킵니다. 해결 후 *블로그 한 편* 으로 *재현 가능한 진단 *우회 회로 (cert + curl + jq)* 를 *영구 자산화* 했습니다. *실패에서 *배운 게 *재발 방지 시스템* 으로 *전환*된다는 게 *제가 가장 자신 있는 *루프* 입니다.*

---

# 7. *마무리* — *이 글을 *읽어주신 분께*

> *기술이 도메인을 *섬길 때 모든 layer 가 *협조* 한다. *경계가 분명할 때 두 시스템이 *각자 더 강해진다*. *postmortem 이 *학습 자산이 될 때 *조직이 *anti-fragile* 해진다*. 이 *3 원칙이 *제 작업의 *공통된 끈* 입니다.

이 글의 *모든 layer* 는 *어느 깊이로 들어가도 *대응 가능* 하도록 *4 단 깊이 답변 hook* 까지 *미리 *준비되어 있습니다. *심층 질문* 어느 것도 *환영* 입니다.

읽어주셔서 감사합니다. *깊이 이야기 나누고 싶으시면* — *blog 의 *제 다른 글* 도 한 번 봐주시거나, *이메일 / GitHub Issue* 로 *언제든 ping* 주세요.

---

*다음 글:* *직접 운영하면서 *진짜로 *결정의 *결을 바꾼 *5 가지 *기술적 *깨달음* — Outbox 의 *언제 / DB-Inbox 의 *실효 / Redis 와 Kafka 의 *대체 가능한 구간 / Hexagonal 의 *진짜 비용* / postmortem 의 *루틴화*.
