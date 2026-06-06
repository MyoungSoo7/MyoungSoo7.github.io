---
layout: post
title: "*청각 재활 훈련 웹앱 ASAT (eln.lemuel.co.kr)* 의 *프로젝트 구조 · 기술 스택* 과 *K3s 클러스터 위에서 *어떻게 도는가* — *6 Pod* 의 *헥사고날 + GitOps + Web Audio API* 운영 기록"
date: 2026-06-07 01:00:00 +0900
categories: [project, kubernetes, fullstack, healthcare]
tags: [asat, spring-boot, next.js, postgresql, redis, web-audio-api, hexagonal-architecture, kubernetes, k3s, gitops, argocd, image-updater, velero, jwt, flyway, jspecify, audiometry, jnd, staircase]
---

내가 운영 중인 사이트 중 하나인 [eln.lemuel.co.kr](https://eln.lemuel.co.kr) 의 *백엔드/프론트엔드/인프라* 전체 그림 정리. 이름은 *ASAT (Auditive Spatial Adaptive Training)* — *이명 환자와 청각 재활 대상자* 의 *주파수 / 공간 청각 변별 능력* 을 *적응형 알고리즘* 으로 *훈련* 시키는 *연구용 웹 애플리케이션*.

기술적으로는 *Spring Boot 4 + Next.js 16 + PostgreSQL 16 + Redis 7 + MinIO* 의 *5 컴포넌트 스택* 을 *K3s 클러스터의 6 Pod* 로 운영하면서, *Web Audio API* 의 *OscillatorNode + StereoPannerNode* 로 *브라우저에서 직접 정밀 오디오 자극을 생성* 하는 *프론트엔드 헤비 + 백엔드 데이터 적재* 구조다.

이 글은 *프로젝트 구조 → 도메인 알고리즘 → 기술 스택 선택 이유 → K3s 위의 운영 그림* 의 *4 단계* 로 진행한다. *fullstack 의 *전체 layer 가 어떻게 맞물리는지* 를 *한 도메인의 관점* 으로 *bird's-eye view* 잡는 글.

---

## TL;DR

**한 줄 요약**

> *청각 변별 임계* 를 *2-down 1-up staircase* 로 *적응적으로 추정* 하면서, *브라우저의 Web Audio API* 가 *정밀 자극을 직접 합성*, *Spring Boot 가 시행 단위로 적재 + 적응 의사결정*, *K3s 위의 6 Pod 가 *GitOps + Image Updater + Velero* 로 *자가 운영* 되는 *fullstack 의 *작은 표본*.

**3 layer 의 책임 분리**

| Layer | 도구 | 책임 |
|-------|------|------|
| **Browser** | Next.js 16 (App Router) + React 19 + Web Audio API | *오디오 자극 합성*, *2AFC 응답 수집*, *UX 와 환경 검증* |
| **Backend** | Spring Boot 4.0.4 + JPA + PostgreSQL 16 + Redis 7 | *세션·시행 적재*, *staircase 알고리즘*, *JND 추정*, *세션 신뢰도 등급* |
| **Infra** | K3s + ArgoCD + Image Updater + Velero + Cloudflare Tunnel | *오케스트레이션·GitOps·백업·외부 노출* |

---

## 1. ASAT — *도메인이 먼저, 기술이 다음*

### 1.1 *청각 변별 임계 (JND)* 란

JND = *Just Noticeable Difference*. *가장 작게나마 다르다고 *판별 가능한 *최소 차이*. *주파수 JND* 는 *1000Hz 기준 자극* 과 *X Hz 더 높은 자극* 을 *구별 가능한 X 의 최소값*. *건강한 성인* 은 *수 Hz* 수준이고, *재활 대상자* 는 *수십 Hz* 까지 올라가기도 한다.

> *JND 가 큰 사람* 은 *말소리 의 미세한 차이* 를 *놓친다*. *훈련으로 JND 가 줄어들 수 있다면* *실제 청취 능력 개선* 으로 *전이* 된다는 가정 위에 *훈련 프로토콜* 이 설계된다.

### 1.2 *왜 *적응형 알고리즘* 인가

*고정 자극* 으로 측정하면 *임계 부근* 에서 *수백 번의 시행* 이 필요하다. *2-down 1-up staircase (Levitt 1971)* 가 *수렴 표준*:

```
시작: 큰 차이 (쉬움)
  ├─ 연속 2번 정답 → 차이를 줄임 (어렵게)
  └─ 1번 오답     → 차이를 늘림 (쉽게)

reversal (방향이 바뀐 횟수) 가 12 회 차면 종료
→ 마지막 reversal 6 회의 *평균* 이 *70.7% 정확도 임계* 의 추정치
```

*적응형* 의 핵심 가치는 *피험자가 *자신의 임계 부근* 에서 시간을 쓴다는 것*. *임계 위* (너무 쉬움, 정보량 0) 와 *임계 아래* (너무 어려움, 추측만 함) 를 *최소화* 한다.

ASAT 는 *3 가지 트랙* 을 *서로 다른 패러다임* 으로 운영:

| 트랙 | 패러다임 | 알고리즘 | 종목 |
|------|----------|----------|------|
| V1 | 2AFC | 2-down 1-up (70.7%) | 주파수 JND / ILD / ITD / 복합 |
| V2 | 3AFC oddball | 3-down 1-up (79.4%) | 주파수 측정/변동/고정 / 공간 측정/훈련 |
| V3 | 2-interval 2AFC | 2-down 1-up (70.7%) | 1kHz 순음 in 백색잡음 |

### 1.3 *세션 신뢰도 등급*

연구용 데이터라 *측정 자체의 *품질* 이 결정적*. ASAT 는 *세션 단위로 A/B/C/F 등급* 을 *자동 평가*:

- *reversal 수렴 패턴* 의 *분산*
- *반응 시간 (RT) 의 분포* 가 *정상* 인지 *난수성* 인지
- *연속 동일 응답 비율* (피험자가 *그냥 한쪽만 누르면* F)
- *환경 검증* (헤드폰 ON, L/R 채널 테스트, 볼륨 캘리브레이션) 의 *통과 여부*

> *데이터 품질이 *자동 라벨링* 되면 *후속 분석* 에서 *F 등급은 제외* 하는 등의 *연구 무결성* 이 확보된다.

---

## 2. 프로젝트 구조 — *헥사고날 + 분석 사이드카*

### 2.1 *모노레포 layout*

```
inter-asat/
├── src/main/java/.../              # Backend (헥사고날)
│   ├── domain/model/               # @Entity 18 + Enum 15 + BaseEntity
│   ├── domain/port/                # Repository 인터페이스 11 개
│   ├── application/service/        # 비즈니스 로직 14 개
│   ├── application/dto/            # Record DTO 40 +
│   ├── adapter/in/web/             # REST Controller 10 개
│   ├── adapter/out/persistence/    # JPA Repository Adapter
│   └── infrastructure/             # Security / Cache / Export
├── src/main/resources/db/migration/  # Flyway V1 ~ V36
├── frontend/                       # Next.js 16
│   ├── src/app/                    # App Router 페이지 13 개
│   ├── src/audio/                  # Web Audio API 엔진
│   └── src/components/             # UI / Training / Gamification
├── analysis/                       # Python 분석 사이드카 (Prefect)
├── docs/                           # 설계 문서, ADR, OpenAPI
└── build.gradle.kts
```

*특이 사항*:
- *backend / frontend / analysis* 가 *같은 레포* 에 있지만 *서로 *완전 독립 빌드*. CI 가 *변경 디렉토리만* 빌드해서 *불필요한 재빌드 비용 0*.
- *18 엔티티 + 36 마이그레이션* 의 *적당히 큰 도메인*. *지나치게 작지도 크지도 않은* *프로젝트 1 인 운영 가능한 규모*.

### 2.2 *헥사고날 (Ports & Adapters)*

```
            ┌─────────────────┐
            │   REST API      │ ← adapter/in/web
            └────────┬────────┘
                     │ UseCase 인터페이스
            ┌────────▼────────┐
            │  application/   │ ← 비즈니스 로직
            │   service       │
            └────────┬────────┘
                     │ port/out 인터페이스
       ┌─────────────┼──────────────┐
       ▼             ▼              ▼
┌────────────┐ ┌──────────┐ ┌──────────────┐
│ JPA Repo   │ │  Redis   │ │ Export       │
│  Adapter   │ │  Cache   │ │ CSV/Excel    │
│ (out/pers) │ │ Adapter  │ │ (OpenCSV/POI)│
└────────────┘ └──────────┘ └──────────────┘
```

*핵심 규칙*:
- *domain/* 은 *Spring 의존성 0* — *순수 Java POJO + 도메인 로직*
- *application/service* 는 *port 인터페이스만 알고* *구체 구현은 모름*
- *adapter/in* 과 *adapter/out* 만 *프레임워크 의존*

> *ArchUnit* 으로 *컴파일 시점* 에 *layer 위반* 차단. *나중에 *조금만 빨리 가려고 *layer 무시* 하는 *유혹* 을 *기계가 거절*.

### 2.3 *분석 사이드카 (Python + Prefect + MinIO)*

*Spring Boot 가 잘 못 하는 일* — *대규모 시계열 분석, 통계 모델, 가시화* 는 *분석 사이드카* 로 분리:

```
[asat-app (Spring Boot)] 
       │ Trial 데이터 적재
       ▼
[PostgreSQL]
       │  ↑ Prefect 스케줄 (매일/매주)
       ▼
[analysis (Python + Prefect)]
       │ pandas / numpy / scipy / matplotlib
       │ 학습률 곡선, JND 분포, RT 분포 등 산출
       ▼
[MinIO: asat-reports bucket]
       │ Parquet / PNG / PDF 리포트
       ▼
[ADMIN 대시보드] (Next.js) 에서 *signed URL* 로 직접 조회
```

> *분석 코드를 *백엔드 안에 *섞으면 *재배포 시 *분석도 멈춤*. *별도 컨테이너 + Prefect Flow* 로 *독립 진화* 가능.

---

## 3. 기술 스택 — *왜 이걸 골랐나*

### 3.1 Java 25 + Spring Boot 4.0.4

| 결정 | 이유 |
|------|------|
| **Java 25** | virtual threads (`Project Loom`) 가 *I/O 바운드 핸들러* 에 *스레드 풀 튜닝 부담 0* 로 *동시성 모델 단순화*. 적은 Pod 으로 *동시 훈련 세션 지원*. |
| **Spring Boot 4.0.4** | *Boot 4 의 *registered services / configuration metadata 개선* + *Native Image 호환* 옵션 열어둠. |
| **JPA** | *18 엔티티 + Optimistic Lock + Pessimistic Lock* 을 *어노테이션 하나로* 분리 가능. *세션 단위 commit window* 가 작아 *동시성 문제 표면적이 작음*. |

### 3.2 Next.js 16 (App Router) + React 19

| 결정 | 이유 |
|------|------|
| **App Router** | *Server Components* 가 *훈련 페이지* 의 *초기 데이터* 를 *서버에서 직렬화* 해서 *Time-to-Interactive* 를 단축. |
| **React 19** | *useActionState* + *form actions* 로 *Trial 응답 제출* 을 *progressive enhancement* (JS 없어도 동작) 으로 유지. |
| **TypeScript** | *훈련 트랙·트라이얼 식별자·세션 상태 enum* 의 *frontend-backend type drift* 를 *컴파일 시점 차단*. |
| **Zustand + TanStack Query** | *세션 상태 (local) + 서버 동기화 (cache)* 의 *책임 분리*. |

### 3.3 Web Audio API — *오디오의 핵심*

```typescript
const ctx = new AudioContext({ sampleRate: 48000 });

const osc = ctx.createOscillator();
osc.frequency.value = 1000;       // 기준 자극

const panner = ctx.createStereoPanner();
panner.pan.value = -0.5;          // 좌측 50%

osc.connect(panner).connect(ctx.destination);
osc.start();
setTimeout(() => osc.stop(), 200);  // 200ms 자극
```

| 왜 Web Audio API 인가 | 효과 |
|----------------------|------|
| *서버에서 wav 다운로드 X* — *브라우저가 직접 합성* | *Latency 최소화*, *대역폭 0*, *cache hit 100%* |
| `OscillatorNode` 의 *주파수 정밀도* | *수 Hz JND 측정* 가능 |
| `StereoPannerNode` 의 *ILD 정밀 제어* | *공간 청각 변별* 자극 생성 |
| `DelayNode` 의 *μs 단위 ITD* | *양 귀 시간차* 자극 |
| `AnalyserNode` 의 *spectrum 검증* | *환경 검증 단계* 에서 *실제 출력이 의도와 일치* 하는지 확인 |

> *오디오를 *서버 wav 파일* 로 *내려받았다면* — *수십 MB 의 사전 합성 자극* + *cache invalidation 지옥* + *모바일 데이터 비용*. *Web Audio API* 가 *3 줄로 풀어준다*.

### 3.4 PostgreSQL 16 + Redis 7

- *PG* — *Trial 적재 / Optimistic Lock @Version 으로 세션 동시성* / *Flyway V1~V36* / *분석 쿼리의 영구 소스*
- *Redis* — *JWT 블랙리스트 / Rate Limit 카운터 / 세션 일시 상태*. *영속 X*. 손실 가능 데이터만 보관.

### 3.5 *Null Safety* — JSpecify + NullAway + ErrorProne

```java
@NullMarked
public class TrainingSession {
    private @Nullable String resultMessage;   // 명시적
    private String userId;                     // 기본 NonNull
}
```

> *Kotlin 이 아니면서 *Kotlin 수준 Null Safety*. *NPE 가 *컴파일 단에서 차단*. *런타임의 *조용한 NPE* 추적 시간 0.

---

## 4. K3s 위의 6 Pod — *어떻게 도는가*

### 4.1 *전체 트래픽 흐름*

```
[브라우저]
   │  https://eln.lemuel.co.kr
   ▼
[Cloudflare Edge]  (DNS A 레코드 → CF)
   │  HTTP/2 + TLS 종단
   ▼
[Cloudflare Tunnel — *클러스터 밖 systemd*]
   │  origin: <node-ip>:30103 (NodePort)
   ▼
[asat-frontend Pod (Next.js)]  on louise
   │  in-cluster: http://asat-app:8080/api/v1/...
   ▼
[asat-app Pod (Spring Boot)]  on louise
   │
   ├──► [asat-postgres-0]  on ilwon  (NVMe SSD, hostname affinity)
   ├──► [asat-minio-0]    on ilwon  (asat-reports bucket)
   └──► [asat-redis]       on louise (캐시, 비영속)

[pg-backup CronJob]  on david  (매일 PG dump → backup PVC)
```

### 4.2 *6 Pod 의 노드별 분포*

```
louise   (worker, 8c 16G)
  ├─ asat-app          (Spring Boot, JVM)
  ├─ asat-frontend     (Next.js)
  └─ asat-redis        (캐시)

ilwon    (control-plane + storage, 12c 32G)
  ├─ asat-postgres-0   (StatefulSet, NVMe local PV)
  └─ asat-minio-0      (StatefulSet, local-path PV)

david    (worker, 6c 15G)
  └─ pg-backup CronJob (매일 PG dump)
```

> *데이터 (PG + MinIO)* 가 *ilwon 의 NVMe* 에 *hostname affinity* 로 묶여 있어 *ilwon 이 죽으면 *데이터 layer 불가용*. *대신 *backup 은 david* 에서 *PG dump* 로 *daily 보존*, 그리고 *Velero/Kopia 가 *namespace-wide 백업* 을 *S3 호환 객체 스토리지* 로 *off-cluster* 보존.

### 4.3 *Service / 외부 노출*

| Service | type | port | 외부 노출 |
|---------|------|------|-----------|
| asat-app | NodePort | 8080 → 30102 | (내부용) |
| asat-frontend | NodePort | 3000 → 30103 | Cloudflare Tunnel origin |
| asat-postgres | ClusterIP | 5432 | (내부만) |
| asat-minio | ClusterIP | 9000, 9001 | (내부만, signed URL 로 brief 외부 노출) |
| asat-redis | ClusterIP | 6379 | (내부만) |

*Ingress controller (Traefik/Nginx) 를 *쓰지 않는다*. *Cloudflare Tunnel* 이 *Ingress 의 역할* 을 *클러스터 *밖* 에서 수행. 클러스터 안에는 *NodePort* 만 있으면 되니 *yaml 표면적이 작음*.

### 4.4 *GitOps + Image Updater 의 자가 운영*

```
[GitHub Actions]
   │ src/, frontend/ 변경 push
   ▼
[CI: build & test]
   │ ghcr.io/myoungsoo7/inter-asat-backend:<sha>
   │ ghcr.io/myoungsoo7/inter-asat-frontend:<sha>
   ▼
[GHCR]
   │
   ▼
[ArgoCD Image Updater]  ← 5 분마다 ghcr poll
   │ newest-build 전략으로 새 SHA 발견
   │ write-back-method: argocd → ArgoCD Application spec.helm.parameters 갱신
   ▼
[ArgoCD root-app]
   │ self-heal=true → 새 parameters 로 Helm template 다시 render
   ▼
[Kubernetes Deployment]
   │ rolling update — 새 Pod 띄우고 old 회수
   ▼
[새 버전 서비스 중]
```

*GitHub Actions* 의 *build → push* 가 *유일한 사람-개입 표면*. 그 뒤는 *전부 자동*.

### 4.5 *Velero + Kopia 백업*

- BackupRepository: `asat-prod-default-kopia-4n9qr` (Ready)
- 마지막 maintenance: 매 5~30분 자동
- 백업 대상: namespace 전체 (PG PVC + MinIO PVC + Secret + ConfigMap + Deployment 정의)
- 백업 저장: *S3 호환 객체 스토리지* 의 별도 bucket
- 복원: `velero restore create --from-backup ...` 한 줄로 *namespace 통째* 복원 가능

> *데이터의 *2 단계 백업*: *daily PG dump* (빠르고 작음) + *namespace-wide Velero* (전체 상태 포함). *복구 시나리오에 따라 *유연하게 선택*.

### 4.6 *보안 표면*

| 항목 | 값 |
|------|----|
| `runAsNonRoot` | true |
| `capabilities.drop` | ALL |
| `allowPrivilegeEscalation` | false |
| `priorityClassName` | lemuel-production |
| `imagePullSecrets` | ghcr-pull (private registry) |
| Secret 관리 | `asat-app-secret` (Gmail 앱비번 등), `asat-postgres-secret` |

애플리케이션 단:
- JWT Access 15min + Refresh 7day httpOnly cookie
- BCrypt cost=12
- Rate Limiting (IP 기반)
- CORS 명시적 origin
- CSP + 7 보안 헤더
- IDOR 방지 (세션 소유자 검증)
- Optimistic Lock `@Version`

---

## 5. 운영 점검 항목 — *남아있는 작은 위험*

### 5.1 *이미지 태그 `:latest`*

Helm values 의 `app.image.tag: latest` + `imagePullPolicy: IfNotPresent` 조합은 *Image Updater 가 ArgoCD parameters 로 SHA 박지 않으면* *cache 옛 이미지가 영구화* 되는 *5/17 사고 패턴*. *현재는 newest-build + write-back-method=argocd 로 정상 동작* 중이지만, *Image Updater 가 잠시 멈추면 latest 가 *남는다*. *values 자체를 SHA pin* 하는 게 더 안전.

### 5.2 *데모 모드 활성화*

`ASAT_AUTH_DEMO_MODE_ENABLED=true` 가 *현재 켜져 있음*. *포트폴리오 면접관* 의 *1-클릭 로그인* 을 위한 의도된 설정이지만, *실제 청각 재활 환자 데이터가 들어오는 운영 단계* 가 되면 *반드시 false* 로 내려야 한다. *환경별 분기* (`SPRING_PROFILES_ACTIVE`) 로 *demo vs prod* 구분이 명확한 게 좋다.

### 5.3 *데이터 layer 의 single point*

PG 와 MinIO 가 *ilwon 단일 노드* 에 *hostname affinity* 로 묶여 있어 *ilwon 이 죽으면 *데이터 계층* 통째 불가용. *daily dump + Velero* 로 *복구 자체는 가능* 하지만 *RTO* 는 *수십 분 ~ 시간 단위*. *연구용 사이트* 라 *99.9% SLA 불필요* 면 OK.

---

## 6. 끝맺음 — *작은 fullstack 의 *전체 모습*

ASAT 는 *백엔드 + 프론트엔드 + 분석 + 인프라* 의 *4 layer* 가 *한 명이 운영 가능한 작은 표면적* 으로 *각자의 책임을 다하는* *fullstack 의 *작은 표본*. *Web Audio API* 라는 *브라우저 안의 정밀 오디오 엔진* 을 *front 단에 두고*, *Spring Boot 가 *적응형 staircase 알고리즘* 으로 *시행 단위 결정*, *PostgreSQL + MinIO + Python 분석 사이드카* 가 *연구용 데이터 무결성* 을 보장, *K3s + ArgoCD + Image Updater + Velero* 가 *운영을 자가 관리*.

> *도메인이 뚜렷할 때* *기술 스택의 선택* 이 *자명* 해진다. *왜 Web Audio API 인가*, *왜 헥사고날인가*, *왜 분석을 사이드카로 분리하는가*, *왜 6 Pod 인가* — 모든 답이 *청각 변별 임계 측정 의 *연구 무결성* 이라는 *하나의 도메인 명제* 에 *기계적으로 환원* 된다.

이게 *작은 fullstack 의 *아름다움*. *기술이 도메인을 *섬길 때*만 *모든 layer 가 *서로 협조* 한다.

---

*다음 글:* *Web Audio API* 의 *OscillatorNode + StereoPannerNode + DelayNode* 가 *어떻게 *μs 단위 ITD* 와 *수 Hz 단위 JND* 를 *브라우저만으로 *측정 가능한 정밀도* 로 *합성* 하는가 — *오디오 그래프 설계 with 실제 ASAT 코드 예제*.
