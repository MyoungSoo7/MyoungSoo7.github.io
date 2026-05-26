---
layout: post
title: "K3s 3노드 etcd HA 복구 — cluster-reset 후 노드 재가입 4단계 (단순 db 삭제만으론 안 됨)"
date: 2026-05-26 19:30:00 +0900
categories: [infra, kubernetes]
tags: [k3s, etcd, cluster-reset, ha, disaster-recovery, debugging, homelab]
---

홈랩 K3s 클러스터 (3 control-plane + 2 worker, embedded etcd HA) 가 새벽 작업 cascade 끝에 죽었다. 두 control-plane 이 `"bootstrap data already found and encrypted with different token"` 에러로 부팅 실패 루프. 살아남은 1 노드의 API 도 etcd quorum 없어서 timeout.

K3s 공식 docs 는 "`--cluster-reset` 으로 reset 한 후 다른 노드들의 `db` 삭제 → 재시작" 이라고만 한다. 따라 했더니 그 다음 4 단계의 함정이 줄지어 나왔다. 이 글은 그 *실제 작동한* 절차.

---

## 0. 사고 발단 — token rotation 후 etcd 데이터와 불일치

전날 밤 노드 네트워크 작업 중 (bonding 설정, 인증서 재발급 등) 두 control-plane 의 `/var/lib/rancher/k3s/server/token` 이 *각각 다른 시간에* rewrite 되었다. 마지막 token rotation 후 k3s 가 즉시 죽지는 않았지만 — 메모리에 캐시된 옛 token 으로 etcd 데이터를 읽고 있던 상태였다.

다음 날 누군가 서비스를 재시작하자 디스크의 etcd 데이터 (옛 token 으로 암호화) 와 현재 token 파일 (새 값) 의 불일치가 감지되면서 부팅 실패. 두 노드 동시에 죽음 → quorum 깨짐 → 살아남은 한 노드의 API server 도 etcd 응답 못 받아서 timeout.

```text
$ kubectl get nodes
Error from server (Timeout): the server was unable to return a response in the time allotted

$ ssh failedNode 'sudo journalctl -u k3s | grep fatal | tail -3'
fatal Error: preparing server: failed to bootstrap cluster data:
  failed to reconcile with local datastore:
  bootstrap data already found and encrypted with different token
```

---

## 1. 살아남은 노드에서 `--cluster-reset` (공식 절차)

```bash
# 살아남은 control-plane 콘솔
sudo systemctl stop k3s
sudo k3s server --cluster-reset
# "Etcd is running, cluster reset operation completed. Managed etcd cluster
#  membership has been reset, restart without --cluster-reset flag now"
# 메시지 후 프로세스 자동 종료
sudo systemctl start k3s
```

이 노드가 *단일 etcd member 상태* 로 재출발한다. 이론적으로 다른 노드들이 `db` 삭제 후 재시작하면 새 member 로 join 한다 — 가 docs 의 설명. 실제로는 *아직 4 단계 더* 남았다.

---

## 2. 다른 노드의 token sync — *두 곳* 동기화

다른 노드에서 그냥 `db` 만 지우고 시작하면:

```text
fatal Error: preparing server: failed to bootstrap cluster data: not authorized
```

원인: 그 노드의 K3S_TOKEN 이 *옛 token* 그대로. `--cluster-reset` 이 살아남은 노드의 token 도 새로 생성하기 때문에 *다른 노드들의 token 도 새 값으로 갱신* 해야 한다.

```bash
# 살아남은 노드에서 새 token 추출
LEMUEL_TOKEN=$(ssh aliveNode 'sudo cat /var/lib/rancher/k3s/server/token')
# 109 bytes 정도. 형식: K10<hash>::server:<suffix>

# 다른 노드 각각:
echo "$LEMUEL_TOKEN" | sudo tee /var/lib/rancher/k3s/server/token
sudo sed -i "s|K3S_TOKEN=.*|K3S_TOKEN='$LEMUEL_TOKEN'|" /etc/systemd/system/k3s.service.env
sudo systemctl daemon-reload
```

**⚠ 함정**: token 파일만 바꾸면 안 됨. **systemd env 의 `K3S_TOKEN` 도 같이 바꿔야** 한다. K3s 는 환경변수를 *우선* 사용한다 (파일은 fallback). 파일만 바꾸고 재시작하면 *같은 not authorized* 가 또 나온다.

---

## 3. `server/` 디렉토리 — *대부분* 삭제

`db` 만 지우면 옛 CA cert / client cert 가 남아서:

```text
level=error msg="Failed to check local etcd status for learner management:
  rpc error: code = Unavailable desc = connection error:
  desc = \"transport: authentication handshake failed: context deadline exceeded\""
```

→ 새 cluster CA 가 발급한 cert 와 옛 노드의 etcd peer cert 가 불일치. 해결:

```bash
sudo systemctl stop k3s
sudo find /var/lib/rancher/k3s/server -mindepth 1 -maxdepth 1 \
  -not -name 'manifests' -not -name 'static' -not -name 'token' \
  -exec rm -rf {} +
# 결과적으로 server/ 아래에는 token, manifests, static 만 남음
# tls/, cred/, db/, agent-token, node-token 다 삭제
```

남기는 것:
- `token` — 2단계에서 새로 받은 값. K3s 가 join 인증에 사용
- `manifests/` — addon manifests (Traefik 등). 노드별로 동일하지만 보존
- `static/` — static pods. 비어있어도 OK

---

## 4. *옛 etcd member 강제 제거* — 진짜 마지막 단계

3 단계까지 다 하고 재시작하면:

```text
level=error msg="Shutdown request received:
  \"etcd cluster join failed: duplicate node name found,
  please use a unique name for this node\""
```

원인: `--cluster-reset` 은 *자기 자신을 단일 member 로 reset* 하지만, **etcd member list 에는 옛 노드들의 entry 가 그대로 남아있다**. 새 노드가 같은 hostname 으로 join 시도하면 name collision.

확인:

```bash
ETCD_OPTS="--cacert=/var/lib/rancher/k3s/server/tls/etcd/server-ca.crt \
  --cert=/var/lib/rancher/k3s/server/tls/etcd/client.crt \
  --key=/var/lib/rancher/k3s/server/tls/etcd/client.key \
  --endpoints=https://127.0.0.1:2379"

sudo /path/to/etcdctl $ETCD_OPTS member list
# 890762fc6e9c4f1b, started, ilwon-e670588d, https://...    ← 옛 entry
# e5ff91e8e2ce2970, started, lemuel-64066392, https://...   ← 살아남은 노드
```

→ 옛 ilwon entry (`890762fc6e9c4f1b`) 가 살아있다. 제거:

```bash
sudo /path/to/etcdctl $ETCD_OPTS member remove 890762fc6e9c4f1b
# Member 890762fc6e9c4f1b removed from cluster 121bf41316fdabec
```

이제 다른 노드 k3s 가 *새 member ID 로* join 가능.

**etcdctl 찾기** — K3s 는 etcdctl 을 PATH 에 두지 않는다. 보통 `/var/lib/rancher/k3s/data/current/bin/` 에 있거나, 없으면 `/tmp/etcdctl` 같은 곳에 다운로드해서 써야 한다.

```bash
sudo find / -name 'etcdctl' -type f 2>/dev/null | head
```

---

## 5. 다른 노드 재시작 + 검증

```bash
# 다른 노드들 각각:
sudo systemctl start k3s
```

1-2 분 후 etcd learner → voting member 승격. 살아남은 노드에서:

```bash
sudo /path/to/etcdctl $ETCD_OPTS member list
# 다 started 상태로 표시되면 성공
```

```bash
kubectl get nodes
# 다 Ready 면 끝
```

---

## 6. 전체 절차 요약

| 단계 | 명령 | 자주 빼먹는 함정 |
|---|---|---|
| 1 | `k3s server --cluster-reset` (살아남은 노드) | — |
| 2 | token 동기화 (파일 + systemd env *둘 다*) | env 만 빠뜨림 → not authorized |
| 3 | `server/` 디렉토리 대부분 삭제 (db, tls, cred, *-token) | db 만 지움 → TLS handshake 실패 |
| 4 | etcdctl 로 *옛 member 강제 제거* | 이 단계 자체를 모름 → duplicate node name |
| 5 | 다른 노드 k3s 시작 + 검증 | — |

총 6 시간 걸렸다. 단계마다 "어, 또 다른 에러" 가 반복. K3s 공식 docs 는 1·3 만 설명하고 2·4 는 안 적혀 있다. *etcd 의 동작 방식* 을 알아야 4 단계 추론이 가능하다.

---

## 7. 미리 해뒀어야 할 안전망

이번 복구가 *6 시간 만에라도 가능했던* 이유:

```bash
# 살아남은 노드의 자동 etcd snapshot — 12시간마다
$ ls /var/lib/rancher/k3s/server/db/snapshots/
etcd-snapshot-lemuel-1779591603  33M  May 24 12:00
etcd-snapshot-lemuel-1779634804  41M  May 25 00:00
etcd-snapshot-lemuel-1779678003  35M  May 25 12:00
etcd-snapshot-lemuel-1779721204  41M  May 26 00:00
etcd-snapshot-lemuel-1779764462  31M  May 26 12:01   ← 사고 1시간 전
```

K3s 가 default 로 `--etcd-snapshot-schedule-cron='0 */12 * * *'` (12시간마다 snapshot) 을 돌린다. *모든 control-plane* 에서 활성. 5개의 snapshot 이 있어서 *최악의 경우 12:01 시점으로 복구* 가능 — 이번엔 거기까지 안 가도 됐다.

추가로 해두면 좋은 것:
- snapshot 을 *외부 위치* (S3, NFS, 다른 노드) 로 복사 — 노드 다 죽어도 살릴 수 있음
- `--etcd-snapshot-retention=10` 같은 retention 늘리기 (default 5)
- *주기적 복구 리허설* — 한 노드 정상 작동 중에 다른 노드만 wipe + 재가입 해보기. 모를 때 위 4 단계 다 발견할 수 있음

---

## 8. lesson

- **K3s embedded etcd HA 는 깨지면 굉장히 복잡**. 단순 docs 따라 하면 안 됨.
- **token 은 두 곳 (file + systemd env)** 에 박혀있다. 두 곳 다 동기화.
- **etcd member list 는 cluster-reset 으로 안 비워진다**. `etcdctl member remove` 로 수동.
- *snapshot 은 영혼의 안식처*. 무조건 자동화 + 외부 복사.

다음에 같은 사고 만나면 6 시간이 아니라 30 분에 풀 수 있을 거다 — 이 글을 보면.
