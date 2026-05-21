---
layout: post
title: "Spring Boot 4 위에 lemuel-xr 백엔드 구축 — 하루 만에 12개 작업, 4가지 SB4 함정, 자동 배포 풀체인"
date: 2026-05-21 21:50:00 +0900
categories: [infra, kubernetes, gitops, spring-boot]
tags: [spring-boot-4, flyway, sops, argocd, image-updater, multi-provider-llm, micrometer, grafana, testcontainers, lemuel-xr]
---

오늘 하루 [lemuel-xr](https://github.com/MyoungSoo7/lemuel-xr) 백엔드를 *Spring Boot 4.0.4 + JDK 25* 위에서 처음부터 완성하면서, **SB4 가 SB3 와 다른 자리 4 곳**을 정면으로 부딪혔다. 동시에 multi-provider AI 라우팅, SOPS 시크릿 봉인, Grafana 대시보드 자동 import 까지 풀스택 작업이 한 번에 이뤄졌다.

이 글은 그 12 개 작업의 압축. 비슷한 작업하는 사람에게 *내가 어디서 막혔고 어떻게 풀었는지* 가 유용했으면.

> **소스**: 백엔드 13 bounded context, 122 Java 파일, 28 tests, 12 Flyway migration, 3 SOPS secrets, 4 row 12 panel Grafana 대시보드. 모두 자동 배포 완료.

---

## TL;DR — 12 작업

| # | 작업 | 핵심 메시지 |
|---|---|---|
| 1 | DB V1~V12 + V20260521 Flyway 마이그레이션 | 25 테이블 + 시드 (창세기 본문·위기 자원) |
| 2 | Backend 13 bounded context (헥사고날) | auth/emotion/recovery/content/game/scripture/safety/theology/ai/tts/asset/outbox/analytics + common |
| 3 | **SB4 함정 #1**: Flyway autoconfig 모듈 분리 | `spring-boot-starter-flyway` 명시 필수 |
| 4 | **SB4 함정 #2**: TestRestTemplate 제거 | `RestClient.create()` + `@LocalServerPort` 로 대체 |
| 5 | **SB4 함정 #3**: Jackson 3 기본 | `com.fasterxml.jackson.databind.ObjectMapper` 안 잡힘 → 명시 bean |
| 6 | **SB4 함정 #4**: `spring.jackson.serialization` 키 변경 | 제거 (Jackson 3 키 path 미정착) |
| 7 | AI 사이드카 multi-provider | OpenAI/Anthropic/Gemini PROVIDER_PRIORITY fallback |
| 8 | SOPS secrets 3종 봉인 + ArgoCD secrets sync | CrashLoop 회피 (배포 전 봉인) |
| 9 | 자동 배포 풀체인 검증 | GHA → ghcr → image-updater → ArgoCD → xr-prod |
| 10 | 28 tests (26 unit + 2 Testcontainers IT) | pgvector:pg17 컨테이너, RestClient 6 endpoint E2E |
| 11 | Telegram ChatOps 위기 알람 | severity ≥ high 자동 발송, PII 없이 alertId+hash 12자만 |
| 12 | Grafana 대시보드 (4 row, 12 panel) | ServiceMonitor + sidecar ConfigMap 자동 import |

---

## 1. SB4 함정 4가지 — 같이 디버깅한다 치고

Spring Boot 3.x → 4.0.4 사이에 *autoconfig 모듈 분리* 라는 큰 변화가 있다. 4 가지 모두 *startup error / 빈 못 찾음* 으로 드러나서 처음엔 *내 코드 잘못* 으로 의심했다.

### 함정 #1 — Flyway autoconfig 가 별도 모듈

**증상**: backend 부팅 시 Hibernate validate 가 `missing table [app_sessions]` 로 실패. 로그를 grep 하면 Flyway 가 *아예 안 돌았다*.

```
build.gradle.kts:
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
```

SB3 에서는 이거면 autoconfig 가 잡힌다. SB4 는 안 잡힌다.

**원인**: SB4 부터 Flyway autoconfig 가 `spring-boot-autoconfigure` 에서 빠지고 **`spring-boot-flyway`** + **`spring-boot-starter-flyway`** 별도 모듈로 이동. 의도는 *autoconfig 모듈 슬림화*. 의도하지 않은 결과는 *마이그레이션 cli 라이브러리만 있는데 Spring 이 모름*.

**수정**:
```kotlin
implementation("org.springframework.boot:spring-boot-starter-flyway")
implementation("org.flywaydb:flyway-database-postgresql")  // Postgres dialect
```

**보강**: 기존 schema 에 history 가 없는 경우를 대비:
```yaml
spring:
  flyway:
    baseline-on-migrate: true
    baseline-version: 0
```

부팅 시 V1~V13 13개 마이그레이션 자동 적용, `flyway_schema_history` 테이블 생성됨.

### 함정 #2 — TestRestTemplate 클래스 제거

**증상**: 통합 테스트 작성 후 컴파일 에러:
```
error: package org.springframework.boot.test.web.client does not exist
import org.springframework.boot.test.web.client.TestRestTemplate;
```

JAR 안을 다 뒤져봐도 클래스 없음. `find ~/.gradle/caches -name "TestRestTemplate.class"` → 결과 0건.

**원인**: SB4 가 TestRestTemplate 을 *deprecated → removed*. SB3.2 부터 `RestClient` 가 표준이라 마이그레이션 권장이 있었는데, 4.0 에서 진짜 삭제.

**수정** — RestClient + @LocalServerPort:
```java
@SpringBootTest(webEnvironment = RANDOM_PORT)
class AuthAndContentIT {
    @LocalServerPort int port;

    @Test
    void e2e() {
        var rest = RestClient.create("http://localhost:" + port);
        Map<String, Object> guest = rest.post().uri("/api/auth/guest")
                .body(Map.of("deviceFingerprint", "it-1", "deviceType", "quest3"))
                .retrieve().body(Map.class);
        assertThat(guest).containsKey("token");
    }
}
```

원래 TestRestTemplate 의 강점은 *4xx/5xx 도 예외 안 던짐* 이었는데, RestClient 는 `HttpClientErrorException` 던짐. 에러 케이스 테스트는 try-catch.

### 함정 #3 — Jackson 3 으로 기본 ObjectMapper 변경

**증상**: 부팅 시 빈 못 찾음:
```
No qualifying bean of type 'com.fasterxml.jackson.databind.ObjectMapper'
required by AssetManifestSeeder
```

**원인**: SB4 는 Jackson 3 (`tools.jackson.databind.ObjectMapper`) 를 기본 빈으로 제공. 이전 세션에서 작성된 `AssetManifestSeeder` 는 Jackson 2 (`com.fasterxml.jackson.databind.ObjectMapper`) 임포트. Spring 은 *클래스 자체가 다른 두 ObjectMapper* 를 알지 못함 — Jackson 2 빈 누락.

**수정** — Jackson 2 호환 빈 명시:
```java
@Configuration
public class JacksonCompatConfig {
    @Bean
    public com.fasterxml.jackson.databind.ObjectMapper legacyJacksonObjectMapper() {
        return new com.fasterxml.jackson.databind.ObjectMapper();
    }
}
```

장기적으로는 Jackson 3 으로 코드 이행이 맞지만, 이번엔 호환 layer 유지.

### 함정 #4 — `spring.jackson.serialization.*` 키 미정착

**증상**: application.yml 의:
```yaml
spring:
  jackson:
    serialization:
      write-dates-as-timestamps: false
```
가 부팅 시 *Failed to bind* 로 실패.

**원인**: SB4 의 `tools.jackson.databind.SerializationFeature` 에 binding 코드가 아직 미정착. SB3 키 path 가 4 에서 깨짐.

**수정**: 일단 키 제거. 필요하면 `@Bean Jackson3ObjectMapperBuilderCustomizer` 로 프로그래매틱 설정.

→ **함정 4건 모두 *autoconfig 모듈 분리* 와 *Jackson 3 전환* 이라는 두 큰 흐름의 부작용**. SB4 마이그레이션 가이드 공식 문서에 명시되어 있지만 startup error 메시지로는 *연결 짓기 어렵다*.

---

## 2. AI multi-provider 라우팅 — purpose 기반

**문제**: 첫 구현은 Gemini 단일 호출. 503 UNAVAILABLE 자주 받고, *분류는 빠른 모델이 좋고 묵상은 품질 좋은 모델이 좋다* 는 비대칭이 코드에 안 반영됨.

**해결**: Python 사이드카에 provider 추상화 + purpose 별 우선순위.

```python
# ai/providers.py
class _OpenAIProvider:    # gpt-4o-mini, gpt-4o
class _AnthropicProvider: # claude-3-haiku, claude-3.5-sonnet
class _GeminiProvider:    # gemini-2.5-flash, flash-lite

PROVIDER_PRIORITY = {
    "classify_emotion": ["openai_gpt4o_mini", "anthropic_claude3_haiku", "google_gemini_25_flash_lite"],
    "diary_meditation": ["anthropic_claude35_sonnet", "openai_gpt4o", "google_gemini_25_flash"],
    "game_branch":      ["openai_gpt4o_mini", "anthropic_claude3_haiku", "google_gemini_25_flash"],
    "polish_psalm":     ["anthropic_claude35_sonnet", "openai_gpt4o", ...],
}

def generate(purpose, prompt, ...):
    for pname in PROVIDER_PRIORITY[purpose]:
        provider = _REGISTRY.get(pname)
        if not provider.available:  # API key 없음
            continue
        try:
            return provider.generate(prompt, ...)
        except ProviderError as e:
            last_err = e
            continue
    raise last_err
```

**Spring 측은 변화 없음** — `AiSidecarClient.generate(purpose, promptKey, variables)` 가 그대로 사이드카에 위임. *purpose 라는 한 단어* 가 라우팅을 결정.

**효과**:
- 분류는 빠른 모델 (latency p99 600ms 목표)
- 묵상은 품질 좋은 모델 (latency 3s 허용, 한국어 자연스러움)
- 하나가 503 받아도 다음으로 자연 fallback
- API key 없는 provider 는 skip — 환경별 (dev/prod) 라우팅 다르게 적용 가능

---

## 3. SOPS + ArgoCD secrets sync — 안전한 봉인

**배경**: 코드는 ghcr 에 올라갔는데 K8s Secret 이 없으면 Pod 가 CrashLoop. 사용자가 "*첫 배포는 CrashLoop 이 정상이에요*" 라는 경험을 안 하게 하고 싶었다.

**SOPS 패턴** (age 키 기반):

```bash
JWT=$(openssl rand -hex 32)  # 64자 hex = 256bit HS256
cat > /tmp/lemuel-xr-jwt.sops.yaml <<EOF
apiVersion: isindir.github.com/v1alpha3
kind: SopsSecret
metadata:
  name: lemuel-xr-jwt-secret
  namespace: lemuel-xr-prod
spec:
  enforceOwnership: true
  secretTemplates:
    - name: lemuel-xr-jwt-secret
      stringData:
        secret: ${JWT}
EOF

cp /tmp/lemuel-xr-jwt.sops.yaml secrets/
sops -e --in-place secrets/lemuel-xr-jwt.sops.yaml
rm /tmp/lemuel-xr-jwt.sops.yaml
```

`stringData.secret` 의 값만 `ENC[AES256_GCM,...]` 로 치환되고, 키는 평문 (`stringData.secret`) 그대로 git 에 들어감.

**ArgoCD sync** — 다른 앱들은 `secrets/` 디렉토리를 *수동 apply* 한 흔적이 있어서, lemuel-xr 부터는 **명시적 ArgoCD Application** 으로 분리:

```yaml
# argocd-applications/lemuel-xr-secrets.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: lemuel-xr-secrets
  namespace: argocd
spec:
  source:
    path: secrets
    directory:
      include: 'lemuel-xr-*.sops.yaml'    # 다른 앱 secret 침범 X
  destination:
    namespace: lemuel-xr-prod
  syncPolicy:
    automated:
      prune: false        # secrets 삭제는 명시적으로만
      selfHeal: true
```

**flow**:
```
git push (helm-deploy)
  → ArgoCD root-app 이 argocd-applications/ 새 파일 감지
  → lemuel-xr-secrets Application 생성
  → secrets/ 의 SopsSecret CR 들을 apply
  → cluster 의 sops-operator 가 watch → 평문 K8s Secret 생성
  → 약 2분 만에 lemuel-xr-jwt-secret / -internal-token / -postgres 생성됨
```

**검증**:
```bash
kubectl -n argocd get app lemuel-xr-secrets
# lemuel-xr-secrets    Synced     Healthy

kubectl -n lemuel-xr-prod get sopssecret,secret
# sopssecret.../lemuel-xr-jwt-secret       Healthy
# secret/lemuel-xr-jwt-secret              2m11s ago
# secret/lemuel-xr-internal-token          2m10s ago
# secret/lemuel-xr-postgres-secret         2m
```

→ 그 후 backend image 가 ghcr 에 올라오면 image-updater 가 detection → ArgoCD lemuel-xr-prod sync → pod 가 secretKeyRef 로 *이미 존재하는 secret 을 읽음* → **CrashLoop 없이 한 번에 가동**.

---

## 4. Grafana 대시보드 자동 import — sidecar 패턴

**문제**: kube-prometheus-stack 의 generic 대시보드만 있고 lemuel-xr 도메인 메트릭 가시화 없음.

**3 단계 wiring**:

### 4.1 Backend 측 — Micrometer

```java
@Configuration
public class MetricsConfig {
    @Bean
    public TimedAspect timedAspect(MeterRegistry r) { return new TimedAspect(r); }
    // SB4 는 @Timed AOP autoconfig 미제공 — 명시 빈
}

@PostMapping("/classify")
@Timed(value = "emotion.classify", percentiles = {0.5, 0.95, 0.99})
public ResponseEntity<...> classify(...) { ... }

// LLM 캐시 hit rate
Counter.builder("llm.cache.hit").tag("purpose", purpose).register(meter).increment();
Counter.builder("llm.cache.miss").tag("purpose", purpose).tag("provider", fresh.provider()).register(meter).increment();

// Safety alert
Counter.builder("safety.alert").tag("severity", scan.severity()).register(meter).increment();
```

application.yml:
```yaml
management:
  endpoints.web.exposure.include: health,info,metrics,prometheus
  prometheus.metrics.export.enabled: true
  metrics:
    distribution.percentiles-histogram:
      http.server.requests: true
      emotion.classify: true
      game.decide: true
    tags.application: lemuel-xr-backend
```

### 4.2 Cluster 측 — ServiceMonitor

```yaml
# helm chart templates/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: lemuel-xr-backend
  labels:
    release: kps   # kps Prometheus 의 default selector
spec:
  selector:
    matchLabels: { app: lemuel-xr-backend }
  endpoints:
    - port: http
      path: /actuator/prometheus
      interval: 30s
```

Service port 에 `name: http` 추가 — 이게 매칭 키.

### 4.3 Grafana sidecar 가 ConfigMap watch

`kps-grafana` 는 `kiwigrid/k8s-sidecar` 컨테이너를 함께 띄움. 이게 cluster-wide 로 label `grafana_dashboard=1` 인 ConfigMap 을 watch.

```yaml
# helm chart templates/grafana-dashboard-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lemuel-xr-backend-grafana-dashboard
  namespace: monitoring   # sidecar 가 우선 스캔
  labels:
    grafana_dashboard: "1"
data:
  lemuel-xr.json: |
{{ .Files.Get "dashboards/lemuel-xr.json" | indent 4 }}
```

→ ConfigMap 이 git push 로 sync 되면 sidecar 가 즉시 감지 → Grafana 의 `/tmp/dashboards/lemuel-xr/lemuel-xr.json` 으로 mount → Grafana 가 새 대시보드 자동 등록 → 메뉴에서 *Lemuel XR — Backend Overview* 검색 가능.

**4 row · 12 panel**:
- 🚦 트래픽: Endpoint QPS / p50·p95·p99 / 5xx rate
- 🤖 AI 비용·캐시: Cache Hit Rate (80%↑ green) / provider QPS / purpose miss
- 🎮 비즈니스: emotion classify / character 별 세션 시작 / decide latency
- 🛡️ 안전: severity 별 alert / 24h critical stat / emergency exit reason

---

## 5. 자동 배포 풀체인 검증

12 개 작업을 묶어서 한 번에 푸시했다. 풀체인:

```
[1] inter-xr/lemuel-xr master push (305 files / 28k 라인)
       ↓ GHA paths-filter
[2] backend/ai/tts 4 도메인 paths-filter
       ↓ docker build-push-action
[3] ghcr.io/myoungsoo7/lemuel-xr-{backend,ai,tts}:main-<sha>
       ↓ (5분 폴링)
[4] argocd-image-updater 감지 → ArgoCD Application 파라미터 갱신
       ↓ selfHeal
[5] ArgoCD lemuel-xr-prod sync → xr-prod ns
       ↓ pod rollout
[6] 새 backend (jwt secret 이미 존재) → CrashLoop 없이 즉시 가동
[7] kps-prometheus 가 /actuator/prometheus 30s 폴링 시작
[8] kps-grafana sidecar 가 lemuel-xr-backend-grafana-dashboard ConfigMap 감지
       ↓
[9] 약 8-10분 후 대시보드 메뉴에 등장
```

**검증 명령** (어디까지 갔는지 확인):
```bash
gh run list --repo MyoungSoo7/lemuel-xr -L 1
kubectl -n argocd get app | grep lemuel-xr
kubectl -n lemuel-xr-prod get pods,secrets
kubectl -n monitoring exec deploy/kps-grafana -- ls /tmp/dashboards/lemuel-xr/
```

---

## 6. 하루 만에 12 작업이 가능한 이유 — 기반의 가치

오늘 12 작업이 가능했던 건 *지난 한 달간 쌓아둔 기반* 덕분이다:

- **자동 배포 (ArgoCD + image-updater)** — 한 번 만들어두면 git push 만 한다
- **SOPS-operator** — 시크릿 봉인 패턴이 정착돼 새 secret 만들기 5분
- **kube-prometheus-stack + Grafana sidecar** — 대시보드 등록이 *ConfigMap 한 개*
- **GHA paths-filter** — 4 도메인 (backend/ai/tts/frontend) 변경된 것만 빌드 → 빠른 CI
- **Testcontainers** — 통합 테스트가 컴퓨터에서 즉시 돈다 (Postgres 컨테이너 자동 기동)

만약 이 기반이 없었다면:
- 시크릿 만들기마다 *환경별 .env 수동 관리*
- 새 대시보드마다 *Grafana UI 에서 손으로 클릭*
- 배포마다 *kubectl apply 7~10 번*
- 통합 테스트는 *팀 DB 빌려서 더럽히기*

→ **인프라 투자는 복리(複利)** 라는 격언이 오늘 또 한 번 확인됨.

---

## 마무리 — 다음 일

오늘 끝낸 후 운영자 시야에서 보이는 *불안정 항목*:

| 증상 | 위치 |
|---|---|
| ECK operator 355회 재시작 / 42h | elastic-system ns |
| node-exporter rnk6q 738회 재시작 | david 노드 추정 |
| fluent-bit-4p9k2 21회 재시작 | 한 노드 로그 ship 일시 중단 가능 |
| elk-cluster ArgoCD OutOfSync | spec drift |

다음 글은 *ELK 자동복구* 와 *OpenTelemetry traces* 로 이어갈 예정. ECK 컨트롤러가 8분마다 재시작하는 건 noisy — 알람 신호 대 잡음비가 떨어진다.

---

## 참고

- [GitOps 전문가의 시야 — 36개 Application 운영]({% post_url 2026-05-19-gitops-expert-7-patterns-and-pitfalls %}) — 오늘의 SOPS + image-updater 흐름이 다 거기서 이어진 결과
- [K3s 홈랩 하루치 운영기 — Logstash·etcd·ECK]({% post_url 2026-05-17-elk-modernization-etcd-stability-eck-crashloop-deepdive %}) — *내일 ELK 자동복구* 글의 토대
- [AI agent 잘 쓰는 법]({% post_url 2026-05-18-how-to-work-with-ai-agents %}) — 메모리·STATUS 분리·서브에이전트 패턴이 오늘 작업의 *왜 빨랐는가* 의 답
- Spring Boot 4 [Migration Guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes) — Flyway, TestRestTemplate, Jackson 3 모두 명시
- [Micrometer Prometheus + Grafana sidecar pattern](https://github.com/kiwigrid/k8s-sidecar)
