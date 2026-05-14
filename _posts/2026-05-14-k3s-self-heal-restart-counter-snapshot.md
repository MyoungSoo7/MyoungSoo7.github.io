---
layout: post
title: "K3s self-heal 실증 — 운영 중인 클러스터의 restart 카운터를 직접 보다"
date: 2026-05-14 14:30:00 +0900
categories: [infra, kubernetes, operations]
tags: [k3s, self-heal, crashloopbackoff, kubernetes, operations, postmortem]
---

> K3s 도입할 때 가장 먼저 학습한 개념이 **"Pod 가 죽으면 자동 재시작 / 노드가 죽으면 자동 재배치"** 였습니다. 그런데 정작 운영하면서 "이게 실제로 발동된 적이 있나?" 를 직접 확인한 적이 없었습니다. 5 노드 K3s 클러스터에 23일째 + (가장 짧은 노드 3일째) 워크로드 118 개를 굴리고 있는 시점, restart 카운터 스냅샷을 떠보니 K3s 가 조용히 일을 하고 있었다는 증거가 곳곳에 남아 있었습니다.

## 1. 어떤 명령으로 봤는가

restart 카운터는 `kubectl get pods` 에 컬럼으로 뜨지만 멀티 컨테이너 Pod 의 경우 합산이 복잡해서 jsonpath 로 한 번에 뽑았습니다.

```bash
sudo kubectl get pods -A \
  -o custom-columns='NS:.metadata.namespace,POD:.metadata.name,RESTARTS:.status.containerStatuses[*].restartCount,STATUS:.status.phase,READY:.status.containerStatuses[*].ready' \
  --no-headers \
  | awk '{
      split($3, r, ",");
      max=0; for(i in r) if(r[i]+0>max) max=r[i]+0
      if(max>0) print max"\t"$1"\t"$2"\t"$4"\t"$5
    }' \
  | sort -rn
```

## 2. 결과 — restart > 0 인 Pod 목록

전체 118 개 Pod 중 restart 카운터가 1 이상인 Pod 는 **15 개 (13%)** 였습니다.

| restart | 네임스페이스 | Pod | 상태 | Ready |
|--------:|------|-----|------|-------|
| 155 | academy-staging | user-service-679c877c8-zcfg2 | Running | false |
| 155 | academy-staging | catalog-service-74bf4b47b5-22mqq | Running | false |
| 154 | academy-staging | media-service-5c7dbd57f-smftj | Running | false |
| **11** | **academy-prod** | **catalog-service-68f687f4cb-9kmt2** | **Running** | **true** |
| 4 | jabis-prod | jabis-app-6889cc6757-thhfs | Running | true |
| 3 | velero | node-agent-hpx2b | Running | true |
| 3 | monitoring | kps-kube-state-metrics-d46bf8787-8g499 | Running | true |
| 2 | kafka | lemuel-dual-role-0 | Running | true |
| 1 | sparta-prod | sparta-product-6884758449-trmws | Running | true |
| 1 | settlement-staging | settlement-staging-postgres-0 | Running | true |
| 1 | monitoring | kps-prometheus-node-exporter-nrlzx | Running | true |
| 1 | monitoring | kps-grafana-69c97c555d-w2mtq | Running | true |
| 1 | livecommerce-prod | livecommerce-postgres-0 | Running | true |
| 1 | kube-system | node-local-dns-lddst | Running | true |
| 1 | kafka | strimzi-cluster-operator-56fbb45c6-7zzst | Running | true |

15 개 중 **12 개는 Ready=true** — 한 번 이상 죽었다가 K3s 가 살려내서 현재 서비스 중입니다. 이게 self-heal 의 직접 증거입니다.

## 3. 사례 ① — 프로덕션 Pod 가 11 회 죽었다가 안정화

가장 인상적인 케이스는 `academy-prod` 의 catalog-service 입니다. 동영상 강의 플랫폼의 핵심 도메인 서비스로, 카탈로그 / 챕터 / 레슨 데이터를 제공합니다.

```
Created (Pod):      2026-05-12 09:21:37 UTC
Last terminated:    2026-05-12 09:53:03 UTC  (Exit 1, Reason: Error)
Running since:      2026-05-12 09:58:19 UTC
Restart Count:      11
Status:             Ready=true (현재 안정 가동 중)
```

배포 직후 약 32 분 동안 **11 회** 죽었다가, 마지막 재시작 후 안정화되어 **이 글을 쓰는 시점 기준 2 일째 무중단 가동 중** 입니다.

11 회 동안 무슨 일이 일어났는지는 추측해보면:
- 부팅 직후 의존 서비스 (Postgres / Kafka / Redis) 가 아직 ready 가 아니어서 헬스체크 실패
- Spring Boot 의 startup 단계에서 DB 마이그레이션 충돌
- 컨테이너가 exit 1 로 종료 → Deployment 컨트롤러가 새 컨테이너 생성 → 재시도
- 의존성이 정상화되면서 startup 성공 → Ready 진입

만약 docker-compose 환경이었다면 `restart: unless-stopped` 정책으로도 비슷하게 처리는 됐겠지만, **재시작 backoff / 헬스체크와 Service endpoint 연결 / readinessProbe 와 트래픽 차단 / 11 회 시도 끝의 안정화 추적** 같은 부분은 K3s 가 훨씬 깔끔합니다. 특히 readinessProbe 가 false 인 동안에는 Service 가 그 Pod 에 트래픽을 보내지 않아서, 사용자는 11 회의 실패를 한 번도 체감하지 못했습니다.

## 4. 사례 ② — staging 환경의 CrashLoopBackOff 무한 재시도

`academy-staging` 의 세 서비스는 각각 **155 / 155 / 154 회 재시작** 중이고, 현재도 Ready=false 입니다.

```
Reason:  CrashLoopBackOff
State:   waiting — "back-off 5m0s restarting failed container"
Last:    exitCode 1, Reason Error
```

`Last finishedAt - Last startedAt` 을 보니 컨테이너가 시작한 지 **약 10 초만에** exit 1 로 죽고 있습니다. 코드 결함이 명확히 있는 상태인데, K3s 는 이걸 5 분 backoff 간격으로 무한히 재시도합니다.

여기서 중요한 건 **"운영 (academy-prod) 에는 영향 0"** 이라는 점입니다. staging 네임스페이스는 별도이고, 별도 Service / Ingress / 도메인을 쓰기 때문에 staging 의 무한 실패가 prod 트래픽을 건드리지 않습니다. K3s 의 namespace + Deployment 격리 덕분에 staging 에서 망가진 코드가 prod 를 침범하지 못합니다.

(이 staging Pod 들은 다음 fix 가 머지되면 자연스럽게 회복될 예정. ArgoCD Image Updater 가 latest 태그를 watch 하고 있어서 새 이미지가 올라가면 자동 rollout.)

## 5. 사례 ③ — 시스템 컴포넌트 곳곳의 조용한 자가 복구

운영 Pod 만이 아니라 **인프라 자체** 가 자가 복구된 흔적도 곳곳에 있습니다.

- `velero/node-agent-hpx2b` — 3 회 재시작. **백업 시스템 자체가** 죽었다가 살아남.
- `monitoring/kps-kube-state-metrics` — 3 회. 16 초 만에 회복 (2026-05-13 07:33:05 사망 → 07:33:21 재기동).
- `monitoring/kps-prometheus-node-exporter`, `kps-grafana` — 1 회씩. 모니터링 스택이 한 번씩 흔들렸지만 알람도 안 울리고 자가 복구.
- `kafka/lemuel-dual-role-0` — Kafka StatefulSet 2 회 재시작. KRaft 모드라 ZooKeeper 없이도 자가 복구.
- `kafka/strimzi-cluster-operator` — Strimzi 자체도 1 회.
- `kube-system/node-local-dns` — DNS 자체가 1 회 죽었다 살아남.

이 중 **알람이 울려서 내가 손 댄 건 0 건** 입니다. 다 자가 복구돼서 서버 모니터링 봇이 알람을 보내지 않았거나, 알람이 와도 들여다보기 전에 회복돼서 ServerCheck 봇이 다시 "✅ 정상" 으로 메시지를 보낸 케이스입니다.

이건 self-heal 의 본질적 가치를 보여줍니다: **"인간이 모르는 사이에 시스템이 알아서 복구된다."**

## 6. 어떤 메커니즘이 작동했나

위 사례들은 사실 K8s/K3s 의 여러 메커니즘이 협력한 결과입니다.

| 사례 | 작동한 메커니즘 |
|------|----------------|
| academy-prod catalog 11회 → 안정화 | Deployment + ReplicaSet (desired replicas 유지), readinessProbe (트래픽 차단), restartPolicy:Always |
| academy-staging 155회 CrashLoop | restartPolicy:Always + exponential backoff (10s → 20s → ... → 5분 cap), namespace 격리 |
| 시스템 컴포넌트 1~3회 회복 | livenessProbe (응답 없으면 kill → restart), DaemonSet (노드마다 1 개 유지) |
| Kafka 2회 회복 | StatefulSet (순서 보장 재시작 + PersistentVolume 재바인딩) |

## 7. 회고 — docker-compose 였다면?

5 일 전 까지만 해도 일부 워크로드가 docker-compose 였습니다. 만약 catalog-service 의 11 회 재시작이 docker-compose 환경에서 일어났다면:

- ✅ `restart: unless-stopped` 로 컨테이너 재시작은 됐을 것
- ❌ 그 동안 Nginx / 외부 LB 는 죽은 컨테이너로 트래픽 보냄 (readinessProbe 부재)
- ❌ 사용자가 11 회의 5xx 응답을 받음
- ❌ 사망 / 부활 시점이 로그 외엔 추적 어려움 (`kubectl describe pod` 같은 통합 뷰 없음)
- ❌ 의존 서비스 ready 여부 자동 대기 X (init container / wait-for 매번 직접 짜야 함)
- ❌ 노드 자체 다운 시 자동 재배치 X

**K3s 의 self-heal 은 단순히 "재시작" 이 아니라, 재시작 + 트래픽 격리 + 의존성 대기 + 메트릭 노출 + 분산 재배치의 통합** 입니다. 사용자에게 11 회의 실패가 0 회의 5xx 로 흡수된 게 그 가치의 본질입니다.

## 8. 결론

K3s 도입 1 개월. 이 글을 쓰는 시점 기준 클러스터 안에는:

- 운영 Pod 1 개가 **11 회 죽고 다시 살아난 흔적**
- staging Pod 3 개가 **155 회씩 무한히 재시도되는 흔적**
- 시스템 컴포넌트 11 개가 **알람 한 번 안 울리고 자가 복구된 흔적**

이 모두 누구도 손 대지 않은 상태에서 K3s 가 묵묵히 처리한 일입니다. 다음에 incident 가 발생하면 그땐 timestamp 와 이벤트를 캡처해서 더 깊이 들여다본 postmortem 을 쓸 예정입니다.

---

**다음 글 예고**: ArgoCD Application 객체와 helm chart 분리 운영의 함정 — git push 만으로 부족했던 사례
