---
layout: post
title: "K3s 3-Master HA — SQLite → embedded etcd 18분 in-place 마이그레이션 후기"
date: 2026-05-12 22:30:00 +0900
categories: [infra, kubernetes, k3s, devops]
tags: [k3s, etcd, high-availability, control-plane, raft, postmortem]
---

22일 운영 중인 single-master K3s 클러스터를 **18분 다운타임** 으로 **3-master HA** 로 전환했습니다. 백엔드는 SQLite → embedded etcd. 공식 문서에는 "지원 안 함" 으로 적혀있는 in-place 마이그레이션을 시도해서 성공시킨 기록입니다. 4 개의 실전 트러블도 같이 정리합니다.

> 이 글에서 다루는 것
> - SQLite vs embedded etcd 의 진짜 차이
> - in-place `--cluster-init` 으로 자동 변환되는 메커니즘
> - 다른 노드 agent → server 전환 시 critical config mismatch
> - etcd peer 통신 ufw 포트, multi-NIC advertise IP 함정
> - 작업 전 풀백업 스크립트 (재현 가능)

---

## 1. 왜 HA 가 필요한가

K3s default 는 SQLite 단일 파일 (`/var/lib/rancher/k3s/server/db/state.db`). 이게 죽으면:

| 영향 | 결과 |
|---|---|
| kube-apiserver 다운 | kubectl 안 됨, ArgoCD 동기화 정지 |
| 새 Pod 스케줄 불가 | 장애 복구 자동화 멈춤 |
| 이미지 업데이터 정지 | CI/CD 흐름 끊김 |
| 기존 Pod | **계속 동작** (workload data-plane 은 살아있음) |

홈랩에서 자주 간과되는 진실: **워크로드는 살아있지만 운영 자동화가 멈춤.** 포트폴리오 관점에선 "production-grade" 라고 말하려면 control-plane HA 가 표준입니다.

## 2. SQLite vs embedded etcd

```
SQLite               embedded etcd (RAFT)
┌──────────┐        ┌──────────┐ ┌──────────┐ ┌──────────┐
│ master 1 │        │ etcd1    │←│ etcd2    │←│ etcd3    │
│ state.db │        │ state    │ │ state    │ │ state    │
└──────────┘        └──────────┘ └──────────┘ └──────────┘
   단일점               동기 복제, 과반수 (2/3) 필요
```

`embedded etcd` 는 K3s 안에 etcd 가 박혀 있어서 외부 데이터스토어 불필요. RAFT 합의로 다중 마스터 가능.

## 3. 마스터 노드 선정 — RTT 가 답이다

처음엔 "유선 노드가 좋다" 생각했는데 측정해보니 의외였습니다:

```
ping -c 5 평균 RTT (모두 WiFi)
louise:  5ms   ★
solomon: 6ms   ★ (3-NIC failover 적용 후)
ilwon:   11ms
lemuel:  18ms
david:   55ms (USB 동글 품질 차이)
```

etcd 는 latency-sensitive 라 50ms 넘기면 리더 선출 자주 트리거.

**최종 선택**: lemuel + ilwon + solomon (모두 5-18ms)
**워커**: louise / david

> 교훈: 케이블 vs 무선보다 **실측 RTT** 가 우선. 동글 품질 차이가 카테고리 차이보다 큼.

## 4. Phase 1 — 풀백업 (안 하면 망함)

```bash
#!/bin/bash
BD=/var/backups/k3s-ha-$(date +%Y%m%d-%H%M)
mkdir -p "$BD"
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# 1. 클러스터 리소스 전부
for r in nodes namespaces pv pvc storageclass crd configmap secret \
         clusterrole clusterrolebinding; do
  kubectl get "$r" -A -o yaml > "$BD/$r.yaml"
done

# 2. 네임스페이스별 워크로드
for ns in $(kubectl get ns -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get all,configmap,secret,ingress,application \
    -n "$ns" -o yaml > "$BD/ns-$ns.yaml"
done

# 3. SQLite + TLS + 토큰
cp -r /var/lib/rancher/k3s/server/db "$BD/db-dir"
cp -r /var/lib/rancher/k3s/server/tls "$BD/tls"
cp /var/lib/rancher/k3s/server/node-token "$BD/node-token"
cp /etc/systemd/system/k3s.service "$BD/k3s.service"
```

총 60MB. PVC 실데이터는 `/var/lib/rancher/k3s/storage` (또는 일원 bind mount) 에 있어서 다른 노드는 안 건드림.

## 5. Phase 2 — `--cluster-init` in-place 변환

K3s 공식 문서는 "**SQLite → embedded etcd in-place 마이그는 지원 안 함**" 입니다. 하지만 v1.34 부터는 실제로 자동 변환됩니다.

systemd 파일 수정:

```diff
ExecStart=/usr/local/bin/k3s \
    server \
        '--docker' \
        '--disable' \
        'traefik' \
+       '--cluster-init'
```

재시작:
```bash
sudo systemctl daemon-reload
sudo systemctl restart k3s
```

K3s 가 자동으로:
1. `state.db` 를 `state.db.migrated` 로 rename
2. `/var/lib/rancher/k3s/server/db/etcd/` 디렉토리 생성
3. SQLite 의 모든 키 → etcd 키로 변환
4. etcd 단일 멤버 클러스터 시작

검증:
```
$ kubectl get nodes
NAME      STATUS   ROLES
lemuel    Ready    control-plane,etcd  ★ 새 역할 추가
```

워크로드 100 개 + ArgoCD 30 앱 모두 그대로 살아있습니다.

> ⚠️ **주의**: in-place 변환은 비공식이라 K3s 버전별로 동작 다를 수 있음. 반드시 풀백업.

## 6. Phase 3 — agent → server 전환 (트러블 4건)

다른 마스터 노드 (ilwon, solomon) 를 추가하는데 4 개의 트러블을 겪었습니다.

### 트러블 1 — critical configuration mismatch

```
fatal msg="failed to validate server configuration:
critical configuration value mismatch between servers"
mismatched: ClusterDNS.slice[12,13,14]
```

NodeLocal DNS 작업 때 ilwon 의 `kubelet-arg: cluster-dns=169.254.20.10` 만 설정, top-level `cluster-dns` 는 누락. 다른 마스터는 둘 다 있음.

해결:
```yaml
# /etc/rancher/k3s/config.yaml — 모든 마스터 동일하게
cluster-dns: 169.254.20.10
kubelet-arg:
  - cluster-dns=169.254.20.10
```

> 교훈: 추가 마스터의 모든 K3s 핵심 옵션이 첫 마스터와 **bit-by-bit 동일** 해야 함.

### 트러블 2 — etcd 포트 ufw 차단

```
MemberAdd request timed out
dial tcp [LAN노드]:2380: i/o timeout
```

ufw 가 etcd 포트 막고 있었음. 두 노드 모두 오픈:

```bash
sudo ufw allow from [내부LAN] to any port 2379 proto tcp \
  comment 'etcd client'
sudo ufw allow from [내부LAN] to any port 2380 proto tcp \
  comment 'etcd peer'
```

LAN 만 허용 (외부 0.0.0.0/0 절대 금지 — etcd 인증서로 보호되지만 공격면 줄임).

### 트러블 3 — multi-NIC advertise IP 잘못 선택

솔로몬은 WiFi 3 개 (.108 .112 .113) + VIP failover 운영 중. K3s 가 etcd advertise URL 을 `.112` (AX900 동글) 로 자동 선택:

```
initial-advertise-peer-urls: ["https://[LAN노드]:2380"]
```

다른 etcd 멤버는 `.108` 만 알아서 못 찾음. 해결:

```yaml
# solomon 의 /etc/rancher/k3s/config.yaml
node-ip: [내부VIP]   # VIP 와 일치 강제
```

> 교훈: multi-NIC 환경에서 K3s 는 **첫 번째 비-로컬 IP** 를 advertise. VIP failover 와 충돌 가능. `node-ip` 명시 필수.

### 트러블 4 — `K3S_URL` 환경변수의 의미

agent 모드에선 `K3S_URL=https://lemuel:6443` 이 "마스터 URL". server 모드에선 의미가 달라서 `--server` 플래그를 명시해야 안전:

```ini
ExecStart=/usr/local/bin/k3s \
    server \
        '--server' \
        'https://[LAN노드]:6443' \
        '--disable' \
        'traefik'
```

`K3S_TOKEN` 은 양쪽 모두 동일하게 동작.

## 7. 최종 확인

```
$ kubectl get nodes
NAME      STATUS   ROLES                AGE
david     Ready    <none>               3d23h
ilwon     Ready    control-plane,etcd   3d4h   ★ NEW
lemuel    Ready    control-plane,etcd   22d    ★ 첫 마스터
louise    Ready    <none>               2d3h
solomon   Ready    control-plane,etcd   2d3h   ★ NEW (VIP failover 보강)
```

외부 도메인 14 개 + ArgoCD 30 앱 모두 정상. **다운타임 실측 18 분.**

## 8. HA 효과 검증 시나리오

| 시나리오 | 결과 |
|---|---|
| lemuel 다운 | ilwon + solomon (2/3) 쿼럼 → control-plane 정상 |
| ilwon 다운 | lemuel + solomon (2/3) → 정상 |
| solomon 다운 | lemuel + ilwon (2/3) → 정상 |
| 2 노드 동시 다운 | 쿼럼 깨짐 → etcd readonly, 새 Pod 스케줄 불가, **기존 Pod 동작** |

## 9. 정리 — 진짜 production 인가?

| 항목 | 상태 |
|---|---|
| control-plane HA | ✅ 3-master etcd |
| etcd 데이터 | ✅ 실시간 RAFT 복제 |
| 자동 페일오버 | ✅ 1 노드 다운 자동 흡수 |
| 워크로드 데이터 | ❌ local-path PVC (노드 고정) — 별도 작업 필요 |
| 외부 LB | ❌ kube-vip / metallb 없음 — Cloudflare Tunnel 로 우회 중 |

홈랩 + 포트폴리오 관점에선 충분합니다. PVC 의 노드 종속성은 다음 작업 (storage CSI / longhorn / openebs 검토).

---

> 이 글이 도움이 됐다면 [전체 시리즈](/categories/k3s) 도 봐주세요. 같은 5-노드 클러스터의 다른 실전 기록들이 있습니다.
