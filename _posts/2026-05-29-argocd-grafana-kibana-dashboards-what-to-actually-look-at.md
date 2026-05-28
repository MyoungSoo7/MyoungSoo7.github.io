---
layout: post
title: "ArgoCD · Grafana · Kibana — *실제로 봐야 하는* 화면은 어디인가 (운영자 관점 고찰)"
date: 2026-05-29 03:50:00 +0900
categories: [reflection, devops, observability]
tags: [argocd, grafana, kibana, observability, kubernetes, gitops, metrics, logs, dashboard, sre]
---

K3s 홈랩에 *세 대시보드* 가 들어가 있다. ArgoCD 는 *배포 상태*, Grafana 는 *메트릭*, Kibana 는 *로그*. 셋 다 설치하면 *멋있어 보이지만*, 실제로는 *3개월 뒤* 에 한 번도 안 켜본 탭이 두 개 정도 생긴다. *왜* 그렇게 되는지, *진짜 봐야 할 것* 은 무엇인지 — 운영하면서 만들어진 *판별 기준* 을 적는다.

> 본 글은 *고찰* 이다. *처음 도입할 때* 정해두면 *6개월 뒤에 후회* 가 적은 기준들.

---

## TL;DR

| 도구 | 진짜 봐야 하는 화면 | 흔히 안 보는 함정 |
|---|---|---|
| **ArgoCD** | *Application 의 Sync Status + Health Status + 마지막 sync 시각* | Tree View 의 *예쁨* 에 만족 — *Out of Sync* 알람을 받는지가 진짜 핵심 |
| **Grafana** | *Golden Signals* — Latency · Traffic · Errors · Saturation | 화려한 대시보드 100개 → 장애 때 *어떤 거 열어야 하지?* 모름 |
| **Kibana** | *Query 가능한 검색바* + *최근 1시간 에러 로그 분포* | 모든 INFO 로그 다 저장하고 *비싸짐* — 검색은 안 함 |

---

## 1. 왜 이 *세 개* 인가

세 대시보드는 *서로 다른 시간축* 의 진실을 보여준다:

| 도구 | 시간축 | 무엇을 본다 |
|---|---|---|
| ArgoCD | *과거 → 현재 상태* | "지금 클러스터는 git 의 어느 commit 과 같은가" |
| Grafana | *현재 + 최근 N분* | "지금 어디가 느리고 어디서 에러가 났나" |
| Kibana | *최근 + 검색* | "그 에러의 *원인 메시지* 가 뭔가" |

장애 대응의 *기본 흐름* 도 이 순서:
1. Grafana 알람 — *어디가 문제* 인지
2. Kibana 검색 — *왜* 그런지
3. ArgoCD 확인 — *언제 무엇이 배포돼서* 시작됐는지 (revert 가능 여부 판단)

이 흐름이 *훈련되면* 장애 시간이 *반의 반* 으로 줄어든다.

---

## 2. ArgoCD — *Application 상태* 가 거의 전부

### 진짜 봐야 하는 것

**Applications 리스트 화면** 한 장:
- *각 앱별 Sync Status* — `Synced` / `OutOfSync`
- *Health Status* — `Healthy` / `Progressing` / `Degraded` / `Missing`
- *마지막 sync 시각* + *현재 git revision 의 SHA prefix*

```
Application       Sync       Health      Last Sync          Revision
─────────────────────────────────────────────────────────────────────
sparta-prod       Synced     Healthy     2026-05-29 03:01   2e83981
settlement-prod   OutOfSync  Healthy     2026-05-28 18:34   aa4168d
lemuel-xr-prod    Synced     Degraded    2026-05-27 22:11   6f0c467
fashion-prod      Synced     Healthy     2026-05-26 15:00   b23602a
```

이 4줄에 *클러스터의 진실 80%* 가 있다. *Degraded* 가 보이면 → 그 앱의 *Tree View* 에서 *빨간 색 노드* 찾기. 거의 항상 *crash loop pod* 또는 *image pull error*.

### 흔히 안 보는 함정

- **Tree View 만 자주 봄** — 예쁘지만 *주관적*. 장애 발견은 *리스트 화면* 이 빠르다
- **Self-heal 만 믿음** — `selfHeal: true` 가 있다고 *드리프트가 자동 해결* 되지 않음 (manifests 가 일치해야 함). *manual 변경 한 번* 이면 *영구 OutOfSync*
- **App-of-Apps 의 *root* 를 모름** — 30개 앱이 있어도 *root-app* 만 동기화하면 *모든 sub-app 이 자동 sync*. 그래서 *root-app* 의 health 만 보면 됨

### 실전 알람 규칙
- `OutOfSync` 5분 이상 지속 → Slack/Telegram
- `Degraded` 1분 이상 → 즉시
- `Sync` 중 fail 3회 → Slack/Telegram (rollback 신호)

---

## 3. Grafana — *Golden Signals* 4개가 본질

### Site Reliability Engineering 의 4가지 황금 신호

| 신호 | 본질 | 어떤 패널 |
|---|---|---|
| **Latency** | 응답 시간 *분포* | p50 / p95 / p99 시계열 |
| **Traffic** | 요청 *량* | RPS 시계열, 요청 분류별 |
| **Errors** | 실패 *비율* | 5xx ratio, error rate 시계열 |
| **Saturation** | 자원 *포화도* | CPU/Memory/Disk 사용률, queue depth |

이 4개만 *서비스별* 로 1개 row 에 *4 column* 으로 짜놓으면 *대시보드 1개* 로 모든 서비스 상태 *5초 안에* 파악.

### 흔히 안 보는 함정

- **대시보드 100개 만들기** — 막상 장애 때 *"어디 봐야 하지?"* 모름. **하나의 종합 대시보드** + 필요 시 *drill-down 링크* 가 정답
- **메트릭 수집 후 alert 안 만듦** — 사람이 *대시보드 안 켜고도* 장애 인지하려면 *alert rule* 이 필수. Grafana 가 있다는 사실로는 *zero 효과*
- **CPU/Memory 만 봄** — 트랜잭션 시스템에선 *p99 latency* 가 *훨씬* 중요. CPU 50% 여도 p99 가 10초면 *사용자는 죽음*
- **`stat` 패널 남발** — *현재값 한 숫자* 만 보임. 추세를 못 봄. *Time series* + *threshold 색칠* 이 더 유용

### 진짜 만들 *3개 대시보드*

1. **클러스터 한눈 보기** — 모든 노드의 CPU/Mem/Disk + 모든 네임스페이스의 Pod 상태
2. **서비스별 Golden Signals** — settlement / lemuel-xr / sparta 각자의 4신호
3. **인프라 (PostgreSQL / Kafka / Redis)** — connections / lag / hit ratio

이 3개로 *99% 의 장애 시각화* 가능. 나머지는 *drill-down* 으로.

### 실전 alert
- p99 latency > 1초 *5분 지속* → warning
- error rate > 1% *3분 지속* → critical
- 노드 CPU > 90% *10분* → warning
- Pod restart loop (분당 1회 이상) → critical

---

## 4. Kibana — *Query 가능한 검색바* 가 가치의 90%

### 진짜 봐야 하는 것

**Discover 화면 + KQL 검색바**:
```
log.level: "ERROR" and kubernetes.namespace_name: "settlement-prod" and @timestamp: now-1h
```

이 한 줄로 *최근 1시간 settlement 의 모든 에러 로그* 가 나온다. *대시보드* 는 *그 다음*.

### Discover 사용법 마스터

| 패턴 | 효과 |
|---|---|
| `message: *exception*` | exception 단어 포함 로그 |
| `log.level: "ERROR" and not message: "Connection reset"` | 에러 중 noise 제외 |
| `kubernetes.pod.name: settlement-* and @timestamp: now-15m` | 특정 pod 의 최근 15분 |
| `traceID: "abcd1234"` | 분산 트레이스 ID 로 *요청 끝에서 끝까지* 추적 |

### 흔히 안 보는 함정

- **모든 INFO 로그 다 저장** — 1년 뒤 *디스크 비용* 폭발. Index Lifecycle Management (ILM) 로 *7일 후 cold tier, 30일 후 삭제* 같은 정책 필수
- **로그 형식 일관성 X** — Spring Boot 는 logback, Python 은 stdout, nginx 는 access log. *JSON 통일* 안 하면 *검색 안 됨*
- **검색 안 함** — Kibana 가 있다는 *위안감* 만 얻고 *실제 장애 때* 는 `kubectl logs` 직접 침. *Kibana 의 가치 0*
- **Visualization 만 만들고 Discover 안 씀** — 대시보드 예쁘지만 *원인 추적 안 됨*

### 실전 *3개 saved search*

1. **최근 1시간 ERROR 전체** — 패턴 파악
2. **최근 30분 exception 별 그룹화** — top exception 5개 빠르게
3. **특정 서비스 5분 윈도우** — 장애 대응 시 *해당 서비스만*

### 무엇을 *남기지 말아야 하나*
- 모든 INFO 로그 *영구 저장* — 디스크 비용 폭발
- 매 request의 *전체 body* — PII 위험 + 비용
- access log + application log + audit log 를 *같은 인덱스* — 검색 느림

---

## 5. *세 도구 함께 쓸 때* 의 시너지

### 장애 흐름 시나리오

1. **Grafana** 알람: `settlement-prod` 의 p99 가 3초로 튄다
2. **Grafana** drill-down: 특정 endpoint `/api/orders` 만 느림
3. **Kibana** 검색: `kubernetes.pod.name: settlement-* and message: "/api/orders" and @timestamp: now-15m`
   - → "Slow query in repository.findByUserId" 로그 발견
4. **Kibana** 추가: `message: "ORM"` → N+1 쿼리 의심
5. **ArgoCD** 확인: 어제 18:34 에 `settlement-prod` 의 새 커밋 `aa4168d` sync → 그 커밋의 *변경 diff* 확인
6. **결정**: 그 커밋이 원인 → ArgoCD 에서 *previous revision rollback* (5초)

**6단계 흐름이 *3분 안에 끝나면* 사용자는 *알지도 못함***. 그 3분이 *세 도구가 함께 정상화* 됐을 때의 *진짜 ROI*.

### 도구 간 *연결* 이 중요

- Grafana 패널 → Kibana 검색 *링크* (특정 시간 윈도우 + 서비스명 자동 입력)
- Kibana 로그의 *trace ID* → Grafana 의 *trace view* (Tempo / Jaeger 가 있으면)
- ArgoCD 의 *각 Application* → Grafana 의 *해당 네임스페이스 대시보드*

이 *링크 3종* 만 만들면 *3개 도구가 진짜 하나로* 동작.

---

## 6. 흔한 함정 *5종* — 도입 6개월 뒤 후회

| 함정 | 결과 | 예방 |
|---|---|---|
| 대시보드 *100개* | 장애 때 *어디 봐야 할지* 모름 | *서비스별 1개 + 클러스터 1개* 만 |
| Alert *0개* | Grafana 있어도 *장애 모름* | 처음부터 *4 Golden Signal alert* |
| 로그 *전부 저장* | 디스크 비용 *3개월 후 폭발* | ILM 으로 *7일 hot, 30일 warm, 그 후 삭제* |
| ArgoCD selfHeal *맹신* | manual 변경 → 영구 drift | 변경은 *반드시 git PR* 강제 (RBAC 으로) |
| 도구 *링크 없음* | 도구 3개를 *왔다갔다* | Grafana ↔ Kibana ↔ ArgoCD 링크 3개 셋업 |

---

## 7. 결론 — *대시보드 = 화면이 아니라 운영 흐름*

세 도구의 가치는 *화면 그 자체* 가 아니라 *그 화면을 어떻게 활용하는 흐름* 이다.

### 처음 도입할 때 *반드시 정해둬야* 할 5가지
1. *대시보드 개수* — 처음부터 *3개 이상* 만들지 말 것 (서비스별 1 + 클러스터 1 + 인프라 1)
2. *alert 규칙* — Golden Signal 4개에 대한 alert *반드시*
3. *로그 보관 정책* — ILM 으로 *비용 한계 설정*
4. *도구 간 링크* — Grafana → Kibana → ArgoCD 일관 흐름
5. *운영 룰북* — *장애 발생 시 어느 도구 부터 어느 순서로 보는지* 글로 정리

이 5가지 안 정하고 도구만 깔면 *6개월 뒤* 에 *비싼 장식품* 이 된다. 한 번 *5분만 정해두면* 운영 인생 *10배 편해진다*.

### 마지막 — *도구는 운영자의 인지를 외부화한 것*
ArgoCD = "git 과 현실의 차이" 의 외부화
Grafana = "지금 서비스 건강도" 의 외부화
Kibana = "최근 무슨 일이 있었나" 의 외부화

운영자가 *머릿속에서* 답해야 할 *3가지 질문* 을 도구가 *대신 보여주는 것* 뿐. 그래서 *질문이 명확한 운영자* 만 이 도구를 *제대로* 쓴다. 도구가 답을 해주지 않는다 — *질문을 해야 답이 나온다*.

다음 글에선 *Golden Signals alert rule 의 실전 임계값 설정* — "p99 > 1초" 가 왜 그 숫자인지, 어떤 서비스엔 다른 숫자가 맞는지를 정리할 예정.
