---
layout: post
title: "LION으로 평가한 Lemuel Settlement — 금융 정합성을 기계로 강제한 폴리글랏 MSA"
date: 2026-08-03 17:00:00 +0900
categories: [software-engineering, architecture, settlement, k3s]
tags: [LION, settlement, MSA, hexagonal, Kafka, double-entry-ledger, security, cloud, on-premises]
---

> **판정: conditional.** Lemuel Settlement는 정산·원장·이벤트 정합성을 중심으로 설계된 강한 포트폴리오형 플랫폼이다. 다만 현재 실행 증거에서 전체 테스트가 **985건 중 1건 실패·100건 스킵**했고, Docker/Testcontainers 의존성이 확인되므로 “운영 준비 완료”가 아니라 “핵심 설계는 강하고 운영 증거를 더 쌓아야 하는 상태”로 평가한다.

## 1. 평가 범위와 증거 경계

이번 평가는 LION 스킬의 `/컴과` 프로토콜을 적용해 현재 canonical repository를 읽기 전용으로 분석한 결과다.

- 대상: `/Users/lms/settlement`
- 브랜치: `feat/card-service-task11-15`
- 커밋: `e3d4811e9ca53743ddfc986ce36809ffd85e2f99`
- 프로젝트 규칙: `CLAUDE.md`, `AGENTS.md`
- 구조 근거: `README.md`, `docs/ARCHITECTURE.md`, `SPEC.md`, `docs/adr/`
- 실행 검증: `./gradlew test`, `node scripts/harness/harness-audit.mjs`
- 실행 결과: `harness-audit: healthy`; Gradle 전체 테스트는 985건 중 1건 실패, 100건 스킵

이 글은 정적 코드·문서·테스트 실행 결과를 근거로 한다. 실제 운영 트래픽, 장애율, 금전 손실률, 복구 성공률은 현재 로컬 검사만으로 확정할 수 없다.

## 2. 시스템 모델

Lemuel은 이커머스 주문에서 셀러 정산과 복식부기 원장까지 연결하는 플랫폼이다. Java/Spring 기반 핵심 도메인 서비스에 Kotlin·Go·Python 서비스를 결합한 폴리글랏 MSA 구조를 사용한다.

```text
Web/Mobile
    ↓
API Gateway
    ↓
Order / Payment ── Outbox ── Kafka ── Settlement projection
                                          ↓
                                  Settlement / Payout / Ledger
                                          ↓
                                  Account GL / Reconciliation
```

`settlement-service`는 `order-service` 코드를 import하거나 Order DB를 직접 조인하지 않는다. Order·Payment·User·Product 정보는 Kafka 이벤트를 자체 DB의 `settlement_*_view`로 투영하고, 대사는 내부 recon API를 통해 수행한다. 이 경계는 금융 정산에서 중요한 “변경 독립성”과 “감사 가능한 데이터 흐름”을 만든다.[^1][^2]

## 3. 아키텍처 평가

### 강점

1. **Bounded Context와 DB-per-service**
   - 서비스별 DB와 Flyway 마이그레이션을 분리했다.
   - Order와 Settlement 사이의 직접 코드·DB 의존을 차단했다.

2. **헥사고날 경계의 기계적 강제**
   - `domain → adapter` 의존을 금지하고 ArchUnit으로 검증한다.
   - REST·Kafka·Batch와 JPA·외부 PG·검색·PDF 어댑터를 포트 뒤에 둔다.

3. **이벤트 기반 CQRS projection**
   - 정산 서비스가 필요한 외부 상태를 자체 읽기 모델로 소유한다.
   - 소스 서비스의 스키마 변화가 정산 DB에 직접 전파되지 않는다.

4. **금융 도메인 불변식의 명시화**
   - 금액에 `BigDecimal`을 강제한다.
   - POSTED 원장 수정 대신 adjustment/reversal을 추가한다.
   - 차변·대변 균형과 정산 요율 스냅샷을 보존한다.[^3]

### 구조적 위험

- 서비스 수가 JVM 14개와 폴리글랏 서비스로 빠르게 늘어났기 때문에, 기능 추가보다 **배선·계약·운영 표준 유지 비용**이 커질 수 있다.
- 이벤트 프로젝션은 결합을 줄이지만, 이벤트 누락·순서·중복·스키마 드리프트를 운영자가 해석해야 한다.
- Gateway, Kafka, PostgreSQL, Elasticsearch, Redis, 외부 PG, 모니터링이 모두 정상이어야 사용자 여정이 완성된다. 단일 서비스 테스트 통과만으로 전체 시스템 정합성을 보장할 수 없다.

## 4. 15개 컴퓨터과학 렌즈

| 영역 | 상태 | 근거와 평가 |
|---|---|---|
| 프로그래밍 | covered | Java 25·Kotlin·Go·Python, 도메인 모델과 포트 분리. 금액 타입·오류 처리 규칙이 명시됨. |
| 자료구조·알고리즘 | partial | 멱등 키, Kafka 처리, 캐시, 시계열·이상탐지 구현은 확인. 전역 hot path 복잡도와 대규모 부하 증거는 추가 필요. |
| 컴퓨터 구조 | not evidenced | CPU 캐시·메모리·I/O 특성 및 NUMA/하드웨어별 성능 실측은 부족. |
| 운영체제 | partial | JVM, 컨테이너, 스케줄러, resource limit은 존재하나 프로세스·파일·시그널 장애 실험은 추가 필요. |
| 네트워크 | covered | Gateway, HTTP 내부 API, Kafka, TLS/키, timeout·retry·Circuit Breaker·SSE/WebSocket 근거가 있음. |
| 데이터베이스 | covered | DB-per-service, Flyway, PostgreSQL, transaction·unique·lock·projection 설계가 핵심 축. |
| 소프트웨어공학 | covered | ADR, 헥사고날, ArchUnit, JaCoCo, 계약 테스트, GitOps, 하네스 가드가 존재. |
| 웹·모바일 | partial | Gateway·REST·frontend·SSE는 확인했으나 모바일 접근성·브라우저 보안의 전수 증거는 제한적. |
| AI·데이터 | partial | AI 챗봇, 감성분석, 이상탐지, 예측 서비스가 있으나 모델 평가·드리프트·재현성 지표는 추가 필요. |
| 이론 컴퓨터과학 | partial | 상태머신·불변식·멱등성은 강함. 형식 검증·상태 공간 전수 검증은 확인되지 않음. |
| 프로그래밍 언어 | covered | Java/Kotlin/Go/Python을 역할별로 배치하고 Gradle·standalone 빌드를 분리함. |
| 보안 | partial | JWT, RBAC, BCrypt, SSRF 차단, HMAC, PII 암호화가 있으나 운영 설정·침투 테스트 증거가 필요. |
| 그래픽·멀티미디어 | not applicable | 핵심 정산 플랫폼의 중심 영역이 아님. PDF는 운영 출력 어댑터로만 평가. |
| 분산·클라우드 | covered | Kafka, Outbox, DLT·Replay, projection, GitOps, ArgoCD, k3s, Cloudflare Tunnel이 모두 관찰됨. |
| 수학 기초 | covered | 금액·수수료·라운딩, Sharpe·MDD·확률/통계 기반 ML 서비스와 원장 균형식이 존재. 모델별 검증 지표는 보강 필요. |

핵심은 15개를 모두 “완료”로 표시하지 않는 것이다. 현재는 금융·분산·소프트웨어공학 렌즈가 가장 강하고, 컴퓨터 구조·AI 모델 평가·모바일 보안은 증거가 상대적으로 약하다.

## 5. 보안성 검토

### 긍정적 증거

- JWT HS256과 역할 기반 인가
- 셀러 리소스의 JWT 주체 기반 소유권 검증으로 IDOR 방어
- BCrypt cost 12
- 내부 API 키와 fail-closed 운영 설정
- Toss 웹훅 HMAC 검증
- 지급계좌 PII AES-256 필드 암호화
- Bucket4j rate limit
- 공공데이터 커넥터의 사설·메타데이터 IP 차단
- `settlement`, `ledger`, `payout` 이력의 수정·삭제 금지
- GitHub Actions의 Harness guard·Snyk·SonarCloud 연계

### P1/P2 보완사항

| 우선순위 | 발견 | 영향 | 다음 행동 | 검증 조건 |
|---|---|---|---|---|
| P1 | 운영 필수 키가 환경 설정에 의존 | 키 누락·약한 키·환경별 불일치가 인증/내부 API 노출로 이어질 수 있음 | 운영 배포에서 `JWT_SECRET`, internal key, PG 키를 secret manager/SOPS로 강제 | 잘못된 키·누락 시 fail-closed와 배포 차단 |
| P1 | 금융 불변식의 실운영 E2E 증거가 전체 테스트 통과와 분리됨 | 단위 테스트는 통과해도 Kafka·DB·DLT·재시도 결합에서 손실 가능 | 정산→원장→대사→역분개 시나리오를 고정한 Testcontainers/스테이징 리플레이 | event_id·settlement·ledger·payout 잔액 불변식 모두 통과 |
| P2 | 외부 API·Kafka·검색·로그의 민감정보 흐름 전수 확인 필요 | 토큰·계좌·주문 개인정보가 로그/트레이스에 남을 위험 | 필드별 데이터 분류와 로그 redaction 테스트 | 금지 필드가 로그·트레이스·DLT에 없음 |
| P2 | 의존성·컨테이너 이미지의 재현성 증거 보강 필요 | 공급망 변경과 취약 이미지가 운영에 유입될 수 있음 | lockfile·SBOM·이미지 digest·서명 검증 | CI에서 digest/SBOM/취약점 gate 통과 |

## 6. 테스트와 운영성

`./gradlew test`는 여러 서비스의 단위·통합 경로를 실제로 실행했지만, 현재 로컬 결과는 완전한 녹색이 아니다.

```text
985 tests completed
1 failed
100 skipped
실패: QuarantineTrackingIntegrationTest initializationError
원인: Testcontainers DockerClientProviderStrategy 초기화 실패
```

이 실패는 정산 로직이 틀렸다는 증거는 아니지만, “전체 테스트 통과”라고 보고할 수 없다는 명확한 증거다. Docker/Testcontainers가 필요한 통합 경로가 개발자의 실행 환경과 CI에서 일관되게 재현되어야 한다.

추가로 `node scripts/harness/harness-audit.mjs`는 `healthy`였다. 반면 실행을 요청한 `node scripts/harness/oo-gate.test.mjs`는 파일이 존재하지 않아 실행되지 않았다. 이는 코드 결함이라기보다 **문서/도구 경로 드리프트**의 증거이며, Definition-of-Done 문서와 실제 스크립트 목록을 맞춰야 한다.

### 운영 준비도

- **RTO 후보:** 결제·정산 API와 Kafka consumer를 분리하여 복구 순서를 정의해야 한다.
- **RPO 후보:** 원장·outbox·processed_events·projection의 백업 및 재생 정책을 별도로 정의해야 한다.
- **SLO 후보:** 정산 이벤트 처리 지연, DLT 발생률, 대사 불일치율, payout 처리 지연, 원장 균형 실패 건수.
- **가장 중요한 운영 경보:** DLT, Kafka retry, projection drift, stuck state, payout/recon mismatch.

## 7. 클라우드와 온프레미스

| 영역 | 현재 강점 | 남은 질문 |
|---|---|---|
| 클라우드 | GitHub Actions→GHCR→ArgoCD 구조로 선언적 배포 가능 | Kafka·DB·ES의 관리형/자체운영 비용과 장애 책임을 분리했는가 |
| 온프레미스 K3s | 6노드, Traefik, GitOps, 내부 서비스 운영 경험 | 전력·디스크·노드 장애·백업 복구·인증서 만료의 실제 리허설 필요 |
| 네트워크 | gateway·Cloudflare Tunnel·내부 API 키 구조 | VPN/overlay/방화벽 장애 시 이벤트·대사 복구 순서 필요 |
| 데이터 | 서비스별 DB와 이벤트 projection으로 경계가 분명함 | DB·Kafka·ES 백업의 일관된 시점과 복구 검증 필요 |
| 비용 | 온프레미스는 장기 유휴 비용을 줄일 가능성 | 운영 인력과 장애 대응 시간을 TCO에 포함해야 함 |

결론적으로 이 프로젝트는 클라우드에도, 온프레미스에도 배치할 수 있는 구조지만 운영 난이도는 이미 단순 CRUD MSA를 넘어섰다. 클러스터가 존재한다는 사실과 복구 가능한 운영환경이라는 사실은 다르다.

## 8. 가치와 생산성

### 기술적 부가가치

1. 주문과 정산의 경계를 이벤트·프로젝션으로 분리해 변경 영향도를 낮춘다.
2. 복식부기 원장과 역분개 모델로 금융 이력의 감사 가능성을 높인다.
3. Outbox·멱등·DLT·대사로 at-least-once 환경의 오류를 통제한다.
4. 폴리글랏 구조로 실시간 스트리밍·ML·이벤트 알림을 도메인에 맞는 언어로 구현한다.
5. ArchUnit·계약 테스트·하네스 가드로 설계 규칙을 문서가 아닌 실행 가능한 제약으로 만든다.

### 생산성의 주의점

서비스가 20개를 넘으면 새 기능 하나의 구현 속도보다 배선·계약·운영 검증 비용이 중요해진다. 따라서 생산성은 다음으로 측정해야 한다.

```text
실질 생산성 = 고객 가치 × 품질 × 재사용률
            / (개발 시간 + 검토 시간 + 재작업 비용 + 장애 비용)
```

권장 KPI:

- 이벤트 계약 변경부터 모든 소비자 검증까지의 리드타임
- 정산 기능의 재사용 컴포넌트 비율
- DLT·재시도·projection drift 발생률
- settlement→ledger→recon E2E 통과율
- 서비스 추가 시 필요한 배선 지점 수
- 배포 후 rollback 시간
- 개발자 1인당 PR 수가 아니라 고객 가치가 발생한 lead time

## 9. 경영진·개발자·운영자용 요약

### 경영진

이 프로젝트의 차별점은 서비스 개수가 아니라 **정산·원장 정합성을 분산 시스템 안에서 강제하려는 설계**다. 투자 우선순위는 기능 확장보다 운영 자동화, 계약 검증, 복구 리허설에 둬야 한다.

### 개발자

현재 가장 중요한 품질 자산은 `settlement-service`의 BigDecimal·상태머신·Outbox·멱등·역분개·projection 경계다. 이 경계를 우회하는 편의성 코드는 단기 속도보다 큰 회계 리스크를 만든다.

### 운영자

정상 여부는 Pod Running만으로 판단할 수 없다. Kafka DLT, consumer lag, outbox backlog, projection drift, ledger balance, payout mismatch를 함께 봐야 한다.

### 비기술 이해관계자

이 시스템은 주문을 돈으로 정산하고 기록하는 과정에서 한 번의 오류가 반복되거나 사라지지 않도록 여러 겹의 기록·대사·복구 장치를 둔다. 다만 그 장치가 실제 장애에서도 작동하는지는 통합 테스트와 복구 훈련으로 계속 증명해야 한다.

## 10. 최종 실행 우선순위

| 순위 | 실행 항목 | 완료 기준 |
|---|---|---|
| P1 | Docker/Testcontainers 통합테스트 실패 원인 해결 | `QuarantineTrackingIntegrationTest` 포함 전체 테스트 통과 또는 명확한 CI 분리 근거 |
| P1 | 정산 핵심 E2E 리플레이 고정 | payment→settlement→ledger→payout→recon 불변식 자동 검증 |
| P1 | 운영 키·시크릿 fail-closed 검증 | 모든 운영 배포에서 강한 키 없이는 기동/배포 실패 |
| P2 | oo-gate 경로 문서·스크립트 정합성 교정 | Definition-of-Done 문서의 모든 명령이 실제 파일과 일치 |
| P2 | projection drift·DLT·outbox 대시보드 통합 | 운영자가 한 화면에서 backlog·불일치·재생 상태 확인 |
| P2 | 클라우드/온프레미스 복구 리허설 | RTO/RPO 측정값과 rollback/runbook 기록 |
| P3 | AI/ML 서비스 모델 평가·드리프트 지표 추가 | 데이터셋·모델 버전·정확도·드리프트·비용 기록 |

## 결론

LION 기준 Lemuel Settlement는 **금융 정합성과 분산 시스템 설계가 강한 conditional 프로젝트**다. 단순한 CRUD MSA가 아니라 주문·결제·정산·원장·대사를 이벤트와 불변식으로 연결하려는 아키텍처적 야심이 분명하다.

그러나 서비스 규모가 커진 만큼 다음 단계의 경쟁력은 “더 많은 서비스를 추가하는 것”이 아니다.

> **정산의 정확성을 코드로 정의하고, 이벤트·원장·대사·복구까지 운영환경에서 반복 재현할 수 있는가가 다음 단계의 기준이다.**

현재 가장 중요한 다음 행동은 기능 추가가 아니라 **통합테스트 실패 해소, E2E 금융 불변식 자동화, 운영 복구 리허설, 문서와 실행 도구의 정합성 회복**이다.

## References

[^1]: [CLAUDE.md — Lemuel 프로젝트 규칙](https://github.com/MyoungSoo7/settlement/blob/feat/card-service-task11-15/CLAUDE.md)
[^2]: [docs/ARCHITECTURE.md — 아키텍처 개요](https://github.com/MyoungSoo7/settlement/blob/feat/card-service-task11-15/docs/ARCHITECTURE.md)
[^3]: [AGENTS.md — Settlement Copilot 코어 규칙](https://github.com/MyoungSoo7/settlement/blob/feat/card-service-task11-15/AGENTS.md)
[^4]: [README.md — 프로젝트 개요와 검증 경로](https://github.com/MyoungSoo7/settlement/blob/feat/card-service-task11-15/README.md)

*이 글은 LION의 읽기 전용 평가 결과다. 코드·인프라를 변경하지 않았으며, 테스트 결과는 2026-08-03 현재 로컬 환경에서 관찰된 값이다.*

<style>
.post-content table { width: 100%; border-collapse: collapse; margin: 1.5rem 0; }
.post-content th, .post-content td { border: 1px solid #ddd; padding: .6rem; vertical-align: top; }
.post-content th { background: #f6f8fa; }
</style>
