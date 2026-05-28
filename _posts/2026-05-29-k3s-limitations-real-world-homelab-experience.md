---
layout: post
title: "K3s 의 한계 — 5 노드 홈랩을 1 년 운영하며 부딪힌 실전 함정과 *언제 RKE2/Talos/vanilla 로 갈아탈 것인가*"
date: 2026-05-29 03:20:00 +0900
categories: [infra, kubernetes, homelab]
tags: [k3s, kubernetes, rke2, talos, vanilla-k8s, etcd, ha, scalability, limitations, homelab]
---

K3s 는 *경이로운 도구다*. 70MB 바이너리 한 개로 *완전한 Kubernetes* 가 1 분 내 돈다. 라즈베리 파이 / 노트북 / 작은 데스크탑에서도 *production-grade* 워크로드 운영 가능. 내 5 노드 홈랩 클러스터 (lemuel/ilwon/louise/david/solomon) 가 *1 년 동안 settlement, lemuel-xr, academy, sparta-msa 등 수십 개 prod 워크로드* 를 무사히 굴린 증거.

그러나 K3s 의 *우아한 단순함* 이 *동시에 한계* 다. 이 글은 그 한계가 *어디서 실제로 부딪혔고*, *언제 RKE2 / Talos / vanilla K8s 로 갈아탈 신호인지* 를 1 년 운영 경험 기반으로 정리한다.

---

## TL;DR — K3s 의 8 가지 *진짜* 한계

| # | 한계 | 증상 | 대응 |
|---|---|---|---|
| 1 | **임베디드 etcd 분리 불가** | etcd 만 별도 노드로 못 뺌 | 작으면 OK, 커지면 vanilla K8s |
| 2 | **단일 바이너리 디버깅** | 모든 컴포넌트 로그가 `journalctl -u k3s` 한 곳 | 익숙해지면 OK |
| 3 | **HA 가 *민감*** | server 노드 1 개 죽으면 quorum 깨짐, recovery 까다로움 | server 3 노드 *반드시* 유지 |
| 4 | **Backup/Restore 가 *반자동*** | etcd snapshot 은 자동, 전체 복구는 수동 4 단계 | runbook 미리 작성 |
| 5 | **대규모 한계** | 100+ 노드 또는 수천 pod 면 성능 ↓ | 그쯤 가면 RKE2 또는 vanilla |
| 6 | **Networking 옵션 제한** | Flannel 기본, 다른 CNI 교체 신중 | Cilium 으로 교체 가능, 다만 비표준 |
| 7 | **자체 디버깅 도구 부재** | `kubeadm`, `kubelet` 별도 명령 사용 불가 | 작은 환경엔 OK |
| 8 | **Enterprise / 보안 강화 기능** | Pod Security Standards 는 OK, FIPS 등 X | 금융권/공공이면 RKE2 |

**결정 기준 한 줄:** *5-15 노드 + 수백 pod 까지는 K3s 가 최적*. *50+ 노드* 또는 *컴플라이언스* 요구 시 RKE2 / vanilla 로.

---

## 0. K3s 의 *기원과 약속*

2019 년 Rancher 가 K3s 발표. 목표:
- *바이너리 < 100MB*
- *메모리 < 512MB*
- *ARM 지원*
- *Edge / IoT / 홈랩* 환경

달성 방법:
- *모든 컴포넌트를 단일 바이너리* — api-server, scheduler, controller-manager, etcd, kubelet, kube-proxy 가 *한 프로세스*
- *Containerd 임베디드*
- *기본 etcd 대안: SQLite* (단일 노드)
- *Flannel + Traefik + ServiceLB* 내장
- *불필요한 alpha API 제거*

이 단순함이 *5 노드 홈랩* 에선 *축복*, *50 노드 production* 에선 *제약* 이 된다.

---

## 1. 한계 ① — 임베디드 etcd 분리 불가

### 1.1 vanilla K8s 의 구조

```
[etcd cluster (3 노드 별도)]
       ↓
[kube-apiserver (3 노드)]
       ↓
[kube-scheduler] [kube-controller-manager]
       ↓
[kubelet on each worker]
```

etcd 가 *완전히 별도 노드*. *control-plane 의 다른 컴포넌트와도 분리*. *각 layer 별 *독립적 scale up*.

### 1.2 K3s 의 구조

```
[k3s-server 노드 1] ─┐
   ├─ embedded etcd  │
   ├─ apiserver       ├─ etcd raft (3 노드 quorum)
   ├─ scheduler       │
   └─ controller-mgr ─┘

[k3s-server 노드 2] (동일 구조)
[k3s-server 노드 3] (동일 구조)
```

*etcd 가 k3s-server 프로세스 안에 임베디드*. 한 프로세스 죽으면 *etcd + control-plane 다 죽음*.

### 1.3 실전 사례 — etcd 만 격리 *불가*

내 환경에서 *lemuel 의 CPU 부하* 가 control-plane 컴포넌트에 영향 줘서 *cordon* 한 적 있음. *vanilla K8s 면* etcd 만 분리해 *디스크 성능 좋은 노드* 에 배치 가능. K3s 에선 *불가*.

### 1.4 우회 방법

- `--disable-apiserver --disable-controller-manager --disable-scheduler` 옵션으로 *일부 컴포넌트만* 동작 가능. 그러나 *권장 패턴 아님* (rancher 공식 문서에 mention 적음)
- 외부 etcd cluster 와 *연동* 도 가능 (`--datastore-endpoint`), 그러나 *K3s 의 단순함 장점 상실*

### 1.5 *진짜* 영향

대부분 *5-15 노드* 환경에선 *체감 무*. 50+ 노드 가면 etcd I/O 가 *진짜 병목* 이 됨. 그 시점 → RKE2 또는 vanilla 로 갈아타는 자연스러운 신호.

---

## 2. 한계 ② — 단일 바이너리의 *디버깅 비용*

### 2.1 단일 로그의 양면성

장점: `journalctl -u k3s` 한 줄로 *모든 로그* 봄. 셋업 단순.

단점: *문제가 발생했을 때* 그 *모든 컴포넌트 로그가 한 곳에 섞임*:

```
May 28 14:23:01 lemuel k3s[12345]: time="..." level=info msg="api-server: ..."
May 28 14:23:01 lemuel k3s[12345]: time="..." level=error msg="etcd: leader changed"
May 28 14:23:02 lemuel k3s[12345]: time="..." level=warning msg="scheduler: pod ..."
May 28 14:23:02 lemuel k3s[12345]: time="..." level=info msg="kubelet: pulling image ..."
May 28 14:23:03 lemuel k3s[12345]: time="..." level=info msg="controller-manager: ..."
```

*어느 컴포넌트의 어느 phase 인지* 파악 어려움. vanilla K8s 면 *각 컴포넌트 별 별도 로그 파일* + *각자 로그 레벨 조정* 가능.

### 2.2 실전 사례 — 5 월 lemuel cluster-reset 사고

내 환경에서 *etcd quorum 깨짐* 으로 *cluster-reset* 한 적 있음. 진단 시:
- `journalctl -u k3s | head -1000` 으로 *수천 줄 로그 sift*
- *어느 라인이 etcd, 어느 라인이 apiserver* 분별 어려움
- 결국 *4 단계 복구* — token sync (file + env 둘 다), server/ wipe, *옛 etcd member 강제 제거*, restart

이 모든 정보가 *vanilla K8s 였으면* *etcd member list* + *apiserver audit log* 별도로 *훨씬 명확*.

### 2.3 우회 방법

- `--log-level debug` 로 *상세 로그* 활성
- `journalctl -u k3s --since "1 hour ago" | grep -E "etcd|apiserver"` 같은 *grep 패턴* 익히기
- *Prometheus 메트릭* 적극 활용 (api-server, etcd 별 메트릭은 *별도 노출*)

### 2.4 *진짜* 영향

5 노드 환경엔 익숙해지면 OK. 50+ 노드 + *다중 팀 운영* 가면 *컴포넌트별 분리 로그* 가 필수.

---

## 3. 한계 ③ — HA 가 *민감*

### 3.1 K3s 의 etcd HA 룰

- *server 노드 = etcd 멤버* (분리 불가, 위에서 본 1번 한계)
- HA 는 *3 노드 이상* (raft quorum)
- *짝수 노드 비추* — 5 노드, 7 노드 가능
- *server 노드 *반드시* 홀수*

### 3.2 *실제로 까다로운* 부분

**시나리오**: 3 server 노드 중 1 개 *디스크 죽음* → 2 노드 남음 → quorum 유지. *그러나*:
- 그 노드를 *완전히 재가입* 시키는 절차가 *까다로움*
- *옛 etcd member 가 cluster 안에 남아있음* → 새 노드 가입 시 *충돌*

복구 4 단계:
1. *옛 member 강제 제거*: `etcdctl member remove <ID>`
2. 새 노드에서 *server/ wipe*: `rm -rf /var/lib/rancher/k3s/server/db`
3. *token 동기화* (file + env 둘 다 — 흔히 빠뜨림)
4. k3s 재시작

내가 *4 시간 디버깅* 한 후 정리한 runbook. *K3s 공식 문서엔 단편적으로만* 적힘.

### 3.3 우회 방법

- *server 노드 *최소 3* + worker 분리*. server 1 개 죽어도 quorum 안 깨짐
- *etcd snapshot* 자동화 (`--etcd-snapshot-schedule-cron`)
- *runbook 미리 작성*. 한 번 겪고 나면 *영원히 기억*

---

## 4. 한계 ④ — Backup / Restore 의 *반자동*

### 4.1 K3s 의 backup 기능

- *etcd snapshot* 자동: `--etcd-snapshot-schedule-cron "0 */6 * * *"` (6시간마다)
- *retention*: `--etcd-snapshot-retention 24`
- *S3 upload* 도 가능: `--etcd-s3` + `--etcd-s3-endpoint`

여기까진 *훌륭함*. 문제는 *복구*.

### 4.2 복구 절차 — *반자동*

```bash
# 새 클러스터 셋업
k3s server \
  --cluster-reset \
  --cluster-reset-restore-path=/var/lib/rancher/k3s/server/db/snapshots/<snapshot>

# 그 다음 *수동으로*:
# - 다른 server 노드들 *재가입* (위 한계 3 의 4 단계)
# - PV (특히 local-path) *수동 복원*
# - Secret/ConfigMap 검증
# - ArgoCD 의 Application 들 *재배포*
```

vanilla K8s 의 *Velero* 같은 *full backup/restore* 도구는 K3s 에도 *사용 가능* 하지만 *기본 도구 부재*. 별도 설치 필요.

### 4.3 *진짜* 영향

소규모엔 *수동 복구 OK*. 그러나 *시간 압박* 있는 *production 사고* 시 *4 단계 매뉴얼 따라가기* 가 *스트레스*.

---

## 5. 한계 ⑤ — *대규모 한계*

### 5.1 K3s 의 *실용적 상한*

공식 문서엔 *명시 안 함*. 커뮤니티 경험 + 내 실험:

- **10 노드 이하**: *완벽*. 단일 server 도 가능
- **10-30 노드**: *3 server + N worker*. 잘 동작
- **30-100 노드**: *동작은 함*. 그러나 *etcd I/O 압박*, *apiserver 응답 시간 ↑*
- **100+ 노드**: *공식적으로 RKE2 권장*. K3s 의 단순함이 더 이상 장점 아님

### 5.2 *실측 사례*

내 5 노드 환경에서 *144 pod* 운영 중. *kubectl 응답 < 100ms*. 문제 없음.

지인의 *40 노드 K3s* 환경에서 *2,000+ pod*. *kubectl get pods -A 가 5 초*. 이 시점에 *RKE2 마이그레이션* 진행 중.

### 5.3 *왜* 한계가 오는가

- *embedded etcd 의 I/O 한계* — vanilla 처럼 etcd 분리 못 함
- *Flannel 의 VXLAN overhead* — 노드 많아지면 *broadcast 비용*
- *모든 control-plane 컴포넌트가 *같은 메모리/CPU 풀* 공유 → 압박 시 *모두 영향*

---

## 6. 한계 ⑥ — Networking 옵션 제한

### 6.1 K3s 의 기본 CNI

- **Flannel** (VXLAN 모드 기본)
- 단순, 가벼움, *대부분의 홈랩에 충분*

### 6.2 *교체 가능* 하지만 신중

다른 CNI 사용하려면:
```bash
k3s server --flannel-backend=none --disable-network-policy
# 그 다음 별도 설치:
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml
```

가능은 함. 그러나:
- *K3s 의 기본 가정* 이 Flannel 기반. *Service IP*, *kube-proxy* 등 설정 *유의*
- *RKE2* 는 Cilium / Calico / Canal *공식 지원*. *K3s 는 비공식*

### 6.3 *실전 함정*

내 환경에서 *노드 재부팅 후 ufw 활성화* → VXLAN (UDP 8472) 차단 → *Flannel 통신 죽음* → *pod-to-pod 통신 모두 실패*. 해결: `sudo ufw disable`.

이건 K3s 의 한계라기보단 *Flannel + Linux firewall* 의 함정. 그러나 *K3s 가 기본 Flannel* 이라 *대다수 사용자가 이 함정에 빠짐*.

### 6.4 대안

- **RKE2** — Cilium 기본 옵션 가능
- **vanilla K8s** — CNI *완전 자유 선택*

대규모 / 보안 강화 / multi-cluster 환경이면 *Cilium 의 eBPF* 가 *훨씬 강력*. K3s 에서도 *가능은 함* 단 *공식 path 아님*.

---

## 7. 한계 ⑦ — 자체 디버깅 도구 부재

### 7.1 vanilla K8s 의 디버깅 도구

- `kubeadm` — cluster bootstrap, upgrade, reset
- `kubelet` 직접 명령
- `etcdctl` — etcd 직접 조작
- 각 컴포넌트 별 *별도 binary*

### 7.2 K3s 에서는

- 모두 *k3s 바이너리* 안에 포함
- `etcdctl` 직접 사용은 *bundled etcd 의 socket path* 알아야:
  ```bash
  ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
    --cacert=/var/lib/rancher/k3s/server/tls/etcd/server-ca.crt \
    --cert=/var/lib/rancher/k3s/server/tls/etcd/server-client.crt \
    --key=/var/lib/rancher/k3s/server/tls/etcd/server-client.key \
    member list
  ```
- `kubeadm` 명령 사용 불가
- K3s 의 *자체 명령*: `k3s check-config`, `k3s server`, `k3s agent`, `k3s ctr` (containerd 직접)

### 7.3 *진짜* 영향

대부분의 K8s 책 / 강의 / 블로그가 *vanilla 기준*. K3s 로 따라하면 *명령이 다름* 또는 *경로가 다름*. *학습 곡선* 살짝 ↑.

---

## 8. 한계 ⑧ — Enterprise / 보안 강화

### 8.1 *부재* 또는 *까다로움* 한 기능

| 기능 | K3s | RKE2 | vanilla |
|---|---|---|---|
| Pod Security Standards | ✅ | ✅ | ✅ |
| OPA (Open Policy Agent) | ⚠️ (별도 설치) | ✅ | ✅ |
| FIPS 140-2 인증 | ❌ | ✅ | ✅ (배포본에 따라) |
| CIS Hardening | ⚠️ (수동) | ✅ (기본 활성) | ⚠️ (수동) |
| 감사 로깅 (audit) | ✅ (설정 복잡) | ✅ | ✅ |
| Encryption at rest (etcd) | ✅ (설정) | ✅ | ✅ |
| Custom scheduler plugin | ⚠️ | ⚠️ | ✅ |

### 8.2 *RKE2 가 *production-grade* 인 이유*

Rancher 가 K3s 다음으로 만든 *RKE2*:
- *K3s 의 단순함* + *vanilla K8s 의 standardness*
- *FIPS 140-2*, *CIS hardened*
- *컴포넌트 분리* — etcd, apiserver 등이 *별도 컨테이너*
- *공식 미국 정부 (US DoD)* 사용 인증

내가 *금융권 또는 공공기관 K8s 컨설팅* 한다면 *K3s 가 아닌 RKE2*. *내 홈랩* 엔 K3s 가 *압도적으로 좋음*.

---

## 9. 대안 비교 — K3s vs RKE2 vs Talos vs vanilla

| 항목 | K3s | RKE2 | Talos | vanilla (kubeadm) |
|---|---|---|---|---|
| 바이너리 크기 | 70MB | 230MB | OS 자체 | 컴포넌트별 분리 |
| 메모리 (idle) | 512MB | 1GB | 1GB | 2GB |
| 설치 시간 | 30 초 | 2 분 | 5 분 (OS 부팅) | 30 분 |
| 학습 곡선 | 낮음 | 보통 | 보통 (API only) | 가파름 |
| Production 수준 | 중소규모 | 대규모/엔터프라이즈 | 클라우드/엔터프라이즈 | 모든 규모 |
| 보안 강화 | 보통 | 강함 (CIS, FIPS) | 강함 (immutable OS) | 직접 설정 |
| 컴포넌트 분리 | ❌ (단일 바이너리) | ✅ | ✅ | ✅ |
| ARM 지원 | ✅ | ✅ | ✅ | ⚠️ |
| 홈랩 적합 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ |
| 엔터프라이즈 적합 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

### *Talos* 의 매력

Sidero Labs 의 *immutable OS for Kubernetes*. *SSH 없음*, *API 만으로 관리*. *가장 모던*:
- *공격 표면 최소*
- *upgrade 가 OS 재부팅 = 새 버전*
- 학습 곡선: `talosctl` 새로 배워야

내 환경에서 *Talos 도 시도해봄*. 결론: *고정 인프라 (servers)* 엔 좋지만 *변화 잦은 홈랩* 엔 K3s 의 *유연성* 이 더 편함.

---

## 10. K3s 가 *여전히 옳은* 경우

✅ **홈랩 / 학습 환경**
✅ **1-30 노드 규모**
✅ **Edge / IoT (라즈베리 파이)**
✅ **소규모 production** — 스타트업, 작은 SaaS
✅ **빠른 prototype**
✅ **CI/CD 의 *임시 K8s cluster***

내 환경 (5 노드, 144 pod, settlement/lemuel-xr/academy/sparta-msa 등 prod) 은 K3s 가 *압도적 최적*. *vanilla K8s 였으면* 운영 부담 *10 배*.

---

## 11. K3s 를 *떠나야 할* 신호

⚠️ 다음 신호 하나라도 보이면 *RKE2 / vanilla 검토*:

1. **노드 수 50+ 또는 *3 년 안에 100 노드 예상***
2. **컴플라이언스** — 금융권, 공공기관, 의료 (FIPS, CIS hardened 요구)
3. **다중 팀 운영** — 한 cluster 에 *10+ namespace, 5+ team*
4. **고급 networking 요구** — service mesh + multi-cluster + dual-stack 동시
5. **etcd 의 *독립 scale up* 필요** — 데이터 많은 환경
6. **컴포넌트 별 *별도 모니터링* 필수** — debugging 시간이 *비즈니스 손실*
7. ***다양한 CNI* 실험 필요** — Cilium 의 eBPF 기능 풀 활용 등
8. **장기 (5+ 년) production** — K3s 의 라이프사이클이 자주 변함

내 환경엔 *아직* 어느 신호도 안 보임. K3s 유지.

---

## 12. *내 클러스터의 미래*

현재:
- K3s v1.35.4
- 5 노드 (lemuel/ilwon/louise/david/solomon)
- 144 pod, 10+ namespace (prod 다수)

다음 3-6 개월:
- *issachar (R730xd)* 합류 — 6 노드
- 새 맥미니 합류 — 7 노드
- K3s 유지

12-24 개월 후 *가능한* 경로:
- *그대로 K3s* — 노드 10 개 이내 유지
- *RKE2 마이그레이션* — 컴플라이언스 또는 enterprise 기능 필요 시
- *Talos* — *고정 자원 부분* 만 (예: storage 노드)
- *vanilla K8s 서브 클러스터* — 학습 / 포트폴리오용

선택 변수: *내 운영 부담* + *클러스터 규모* + *비즈니스 요구*.

---

## 결론 — K3s 의 한계는 *결함이 아닌 *설계 결정**

K3s 의 한계는 *"못 한다"* 가 아니라 *"안 한다"* — 설계상 *단순함을 위해 *명시적으로* 포기한 것*.

> *K3s 는 *5-30 노드의 가장 좋은 K8s*. 그 위로 가면 *RKE2 / Talos / vanilla* 가 답.*

내 1 년 운영 경험으로:
- ✅ *5 노드 + 144 pod + production 워크로드 다수* — K3s 가 *놀랍게 잘 굴림*
- ⚠️ *5 월 cluster-reset 사고* — embedded etcd 의 *반자동 복구* 가 *4 시간 디버깅* 의 원인
- ⚠️ *노드 재부팅 시 ufw* — Flannel + 기본 firewall 의 함정. *한 번 겪으면 영원히 기억*
- ✅ *settlement / lemuel-xr / academy / sparta-msa 안정 운영*

*K3s 를 *완벽하게* 운영하는 사람* = *K3s 의 한계를 정확히 아는 사람*. *그 한계에 부딪힐 시점이 오면 *주저 없이 RKE2 / vanilla* 로 갈아탈* 판단도 함께.

오늘 시점 (2026 년 5 월) 내 결론: **5-15 노드면 K3s, 50+ 노드 또는 컴플라이언스면 RKE2, *immutable + API-only* 가 매력적이면 Talos**.

---

## 참고

- [K3s 공식 문서](https://docs.k3s.io/)
- [RKE2 공식 문서](https://docs.rke2.io/)
- [Talos Linux 공식 문서](https://www.talos.dev/)
- [Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) — vanilla K8s 학습용
- 관련 글:
  - [홈랩 K3s 5 노드의 CPU 가 모자랄 때 — Capacity Planning]({% post_url 2026-05-29-homelab-capacity-planning-datacenter-style %})
  - [Harness Engineering ④ Deployment Harness]({% post_url 2026-05-29-harness-engineering-4-deployment-gitops %})
  - [Dell R730XD iDRAC 첫 셋업 함정 5종]({% post_url 2026-05-28-dell-r730xd-idrac-first-setup-traps %})
