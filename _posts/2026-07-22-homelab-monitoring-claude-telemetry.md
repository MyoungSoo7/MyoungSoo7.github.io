---
layout: post
title: "에이전트도 워크로드다 — 홈랩 모니터링 구조와 Claude 텔레메트리 고찰"
date: 2026-07-22 06:20:00 +0900
categories: [AI, Kubernetes]
tags: [Kubernetes, K3s, Prometheus, Grafana, Alertmanager, OpenTelemetry, ClaudeCode, Observability, HarnessEngineering, Homelab]
---

# 관제면과 측정면을 나누는 것부터가 설계다

홈랩 K3s 클러스터의 모니터링 파드 배치는 이렇다. 단순해 보이지만 배치 하나하나가 결정이다.

```
┌────────────────────────── K3s 클러스터 ──────────────────────────┐
│                                                                  │
│  [server: ilwon]              ◀── 관제면 (Control Plane of Obs)  │
│   ├─ Prometheus        전체 메트릭 수집·저장 (TSDB)               │
│   ├─ Grafana           대시보드 서빙                              │
│   ├─ Alertmanager      알람 제어 — RCA 알람의 근원지               │
│   └─ kube-state-metrics  K8s 오브젝트 상태 → 메트릭                │
│                                                                  │
│  [전 노드]                    ◀── 측정면 (Data Plane of Obs)      │
│   └─ node-exporter (DaemonSet)  하드웨어·OS 메트릭                │
│                                                                  │
│  [worker: david]              ◀── 에이전트 관측 전용               │
│   └─ claude-telemetry (OTEL Collector)                           │
│        Claude Code 세션 → OTLP 수신                               │
│          ├─ metrics → Prometheus 로 합류                          │
│          └─ logs/events → 클러스터 내 ClickHouse                  │
└──────────────────────────────────────────────────────────────────┘
```

**관제면은 server 노드(ilwon)에 상주**한다. 수집기(Prometheus), 시각화(Grafana), 알람(Alertmanager), 상태 변환기(kube-state-metrics)가 한 노드에 모여 있다 — 워커가 죽어도 관제는 살아 있어야 하고, 관제가 워커의 자원 경합에 휘둘려선 안 되기 때문이다. **측정면은 전 노드에 퍼진다** — node-exporter는 DaemonSet이라 노드가 늘면 측정도 따라 늘고, 빠뜨릴 방법이 없다. 그리고 **에이전트 관측(claude-telemetry)은 워커(david)에 격리**했다 — 실험적 워크로드가 관제면과 자원을 다투지 않게.

관제와 측정의 분리는 애플리케이션 아키텍처의 control plane / data plane 분리와 정확히 같은 원리다. 모니터링 스택도 하나의 분산 시스템이고, 같은 설계 규율이 적용된다.

## Prometheus × Grafana — 이 조합이 표준이 된 이유

### 효율성: pull 모델과 책임의 분리

Prometheus의 **pull 모델**은 홈랩에서 진가를 발휘한다. 각 exporter는 자기 상태를 HTTP 엔드포인트로 노출할 뿐이고, 긁어가는 것은 Prometheus의 일이다. 타깃이 죽으면? 긁기가 실패하고, 그 실패 자체가 `up == 0` 메트릭이 된다. **관측 대상의 부재까지 관측이 되는 구조** — push 모델이라면 "메시지가 안 오는 것"과 "죽은 것"을 구분하기 위한 별도 장치가 필요하다.

라벨 기반 차원 모델도 효율의 핵심이다. `container_memory_usage_bytes{namespace="settlement-prod", pod=...}` — 네임스페이스·파드·노드가 전부 라벨이라, 대시보드 하나를 만들면 서비스가 늘어도 쿼리는 그대로다. 이 글을 쓰는 클러스터에서도 JVM 진단(힙·GC·스레드)을 Micrometer가 노출하는 `/actuator/prometheus` 지표로 수행한다 — 컨테이너에 jstat이 없어도 된다. **애플리케이션이 자기 상태를 표준 형식으로 노출하면, 나머지는 스택이 알아서 하는 구조**다.

그리고 역할 분리: Prometheus는 저장(TSDB)과 쿼리(PromQL)만, Grafana는 시각화만, Alertmanager는 알람 라우팅만 한다. kube-prometheus-stack(kps) 오퍼레이터가 이 셋의 배선을 선언적으로 관리하니, 홈랩 수준의 운영 인력(=한 명)으로도 프로덕션급 스택이 유지된다.

### 효과성: 그래프는 보라고 있고, 알람은 깨우라고 있다

효율이 "적은 비용으로 돌아간다"면 효과는 "실제로 문제를 잡는다"이다. 이 스택의 효과성은 Alertmanager에서 나온다. 대시보드는 **보고 있을 때만** 유용하다. 새벽 3시의 디스크 폭주는 아무도 보고 있지 않다 — 실제로 이 클러스터에서 방화벽 로그 폭주로 디스크가 차오르던 사건의 첫 신호는 Grafana 그래프가 아니라 Alertmanager가 쏘아올린 알람이었고, 그 알람이 RCA(근본원인분석)의 출발점이 됐다.

여기서 배치가 다시 중요해진다. Alertmanager가 server 노드에 상주하는 이유: **알람 경로는 장애 도메인과 분리되어야 한다.** 워커가 죽어서 나는 알람이, 죽은 워커 위에서 발송될 수는 없다.

kube-state-metrics는 조용한 공로자다. node-exporter가 "머신의 물리적 진실"(CPU·메모리·디스크)을 말한다면, kube-state-metrics는 "쿠버네티스의 논리적 진실"(Deployment replica 불일치, Pod pending, CrashLoopBackOff)을 메트릭으로 바꾼다. 장애의 절반은 물리가 아니라 논리에서 시작하고, 그 절반은 이 파드가 없으면 보이지 않는다.

## Claude 텔레메트리 — 에이전트가 관측 대상이 되다

이 클러스터에서 가장 새로운 파드는 `claude-telemetry`다. 정체는 **OpenTelemetry Collector**(contrib 배포판). Claude Code는 세션의 토큰 사용량·비용·도구 호출·세션 이벤트를 OTLP로 내보내는 기능을 내장하고 있고, 이 collector가 그 수신처다. 파이프라인은 이중이다:

```
Claude Code 세션들 (OTLP export)
        │
        ▼
  OTEL Collector (worker: david)
        ├── metrics ──▶ Prometheus exporter ──▶ kps 스크레이프 ──▶ Grafana
        │                (토큰·비용·세션 수가 클러스터 메트릭과 같은 화면에)
        └── logs ────▶ 클러스터 내 ClickHouse
                         (세션 이벤트 원본 — 대용량 분석용 컬럼 저장소)
```

이 이중화는 데이터 성격에 맞춘 것이다. **집계가 의미 있는 것(토큰/비용/세션 카운트)은 시계열로** Prometheus에 — 기존 대시보드·알람 인프라를 그대로 재활용한다. **개별 레코드가 의미 있는 것(세션 이벤트 로그)은 컬럼 저장소로** ClickHouse에 — "지난주 어떤 프로젝트에서 어떤 도구를 많이 썼나" 같은 탐색적 쿼리는 TSDB의 일이 아니다.

### 맥락: 도구를 거절하고 아이디어를 취하다

재밌는 배경이 있다. 지난주에 엔터프라이즈용 Claude Code 관리 플랫폼(Zeude)을 검토하고 **"1인 홈랩에는 오버킬, 도입 불가"** 로 판정했었다. 조직용 대시보드·중앙 배포·shim 래퍼가 통째로 필요 없었기 때문이다. 그런데 그 플랫폼의 3층 구조 중 첫 층 — *"측정이 가시성을 만들고, 가시성이 개선을 만든다"는 Sensing 레이어* — 은 규모와 무관하게 옳았다.

그래서 도구는 안 깔고 **아이디어만 가져왔다**: OTEL Collector 하나 + 기존 Prometheus/Grafana + ClickHouse. 플랫폼 도입 대신 파드 하나로 같은 Sensing을 얻은 것이다. 도구 평가의 결론이 "설치 여부"가 아니라 "어떤 아이디어를 자기 인프라로 흡수할 것인가"일 수 있다는 것 — 이번 배치에서 얻은 가장 큰 교훈이다.

### 기대효과 — 하네스의 마지막 축, 관측

이 시리즈에서 하네스 엔지니어링을 계속 다뤄왔다: [코드베이스의 규율]({% post_url 2026-07-22-hexagonal-msa-oop-coverage-harness %}), [에이전트의 절차·편성·명세]({% post_url 2026-07-22-superpowers-omc-ouroboros-harness-stack %}). 그런데 어느 하네스든 공통 전제가 있다 — **측정 없이는 개선도 없다.**

에이전트 텔레메트리가 채우는 것이 정확히 그 자리다:

1. **비용의 가시화** — 어떤 프로젝트·어떤 작업 패턴이 토큰을 태우는지 시계열로 보인다. "서브에이전트 6개를 띄운 SDD 세션"과 "단일 세션 작업"의 비용 차이가 감이 아니라 그래프가 된다.
2. **하네스 개선의 근거 데이터** — 스킬·훅·워크플로를 고칠 때 전후 비교가 가능해진다. 세션 리포트 도구가 세션 하나의 해부도라면, 이 파이프라인은 **모든 세션의 종단 추세**다.
3. **에이전트 = 여느 워크로드** — 가장 중요한 관점 전환. JVM 파드의 힙을 보듯 에이전트의 토큰을 보고, 파드 재시작에 알람을 걸듯 비정상 세션 패턴에 알람을 걸 수 있다. 에이전트 운영이 감(感)의 영역에서 SRE의 영역으로 넘어온다.

## 정직한 한계

- **수집 3일차다.** collector 배포는 최근이고, 위 기대효과의 상당수는 아직 "기대"다. 추세가 쌓여야 값이 나온다.
- **단일 collector는 SPOF다.** david가 내려가면 그 시간의 에이전트 텔레메트리는 유실된다. 관제면과 달리 에이전트 관측은 아직 이중화가 없다 — 홈랩에선 감수할 만한 트레이드오프지만, 사실은 사실이다.
- **대시보드는 초기 상태다.** 데이터는 흐르는데 "봐야 할 화면"의 설계는 이제 시작이다. 좋은 관측은 수집이 아니라 질문 설계에서 완성된다.

## 맺으며

모니터링 스택의 배치도는 결국 세 문장으로 요약된다. **관제는 안정된 곳에 모아라(ilwon). 측정은 모든 곳에 퍼뜨려라(DaemonSet). 새 실험은 격리하라(david).** 그리고 2026년의 새로운 문장 하나 — **에이전트도 워크로드다. 워크로드라면, 관측하라.**

---
*시리즈: [아키텍처 규율은 어떻게 에이전트의 하네스가 되는가]({% post_url 2026-07-22-hexagonal-msa-oop-coverage-harness %}) · [Superpowers × OMC × Ouroboros 3축 스택]({% post_url 2026-07-22-superpowers-omc-ouroboros-harness-stack %}) · [Ouroboros 0.35→0.50 구조 진화]({% post_url 2026-07-22-ouroboros-035-050-structure-evolution %})*
