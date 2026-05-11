---
layout: post
title: "docker compose → K3s 마이그, 9개 서비스 실전 후기 — 고심한 것, 차이, 장단점"
date: 2026-05-12 00:00:00 +0900
categories: [infra, kubernetes, k3s, devops]
tags: [docker-compose, k3s, kubernetes, migration, gitops, helm, postmortem]
---

홈랩 K3s 5 노드 클러스터에 docker compose 로 굴러가던 서비스 9 개를 하루 안에 옮겼습니다 (cost / dart / pilgrim / data / report / fashion / goods / grid / academy). 그 과정에서 진짜로 고민한 것들, docker compose 와 K3s 가 운영상 어떻게 다른지, 각각의 장단점을 정리합니다. **"K8s 가 다 좋다"** 가 아니라 **"언제 어떤 게 더 나은지"** 의 관점입니다.

> 이 글에서 다루는 것
> - 마이그 대상 9 서비스 분류 (단순/복잡/대형)
> - 옮기면서 고민한 것 8 가지
> - 운영 차이점 8 가지 (실제 겪은 것)
> - 장단점 비교표
> - 어떤 워크로드를 어디로 가는 게 맞는가

---

## 1. 마이그 대상 — 9 서비스 분류

| 케이스 | 서비스 | 컨테이너 | 의존성 | 시간 |
|---|---|---|---|---|
| 단순 | cost / dart / pilgrim / data / report | 1~2 | PostgreSQL only | 5~50분 |
| 복잡 | fashion / goods | 5 | postgres + redis + minio + backend + frontend | 60~90분 |
| 대형 | academy | 9 | MSA (4 backend + 3 frontend + postgres + redis) | 90분 |
| 보류 | news / lowshopping / pharmacy | - | systemd 직접 실행 / 호스트 MariaDB | - |

총 9 케이스, 14 시간 작업.

---

## 2. 고민한 것 8 가지

### 2.1 어떻게 점진적으로 옮길까

처음에는 "전부 K3s 로" 하려 했는데, 옛 docker 가 운영 중인 상태에서 점진적 마이그가 현실적입니다.

**점진 패턴 (실전)**:
1. 새 K3s 차트로 같은 서비스 띄움 (NodePort 30xxx)
2. Cloudflare 라우트는 옛 docker 그대로 유지
3. K3s 가 안정 동작 확인 후 라우트 변경
4. 옛 docker 정지 + 제거
5. 메모리/디스크 회수 확인

**돌이키기 쉬워야 함**. 라우트 한 줄만 바꾸면 옛/새 사이를 전환 가능.

### 2.2 데이터 마이그를 어떻게

이게 가장 큰 고민:

- **PostgreSQL**: 사전에 8 개 DB 를 솔로몬 StatefulSet 으로 옮겨놓은 상태였음 (어제). 오늘은 앱만 옮기면 됨.
- **MinIO**: fashion 의 minio 데이터는 비어있어서 그냥 새로 생성
- **MariaDB**: lowshopping / pharmacy 는 호스트 mariadbd 또는 docker MariaDB → 더 복잡해서 보류
- **H2 file DB**: grid 처럼 임시 DB 는 emptyDir volume 마운트로 처리

**원칙**: 마이그 시점에 데이터 손실 0. 옛 DB 정지 전에 새 K3s app 이 정상 동작해야.

### 2.3 시크릿 관리

처음엔 K3s Secret 에 직접 평문 입력 (`kubectl create secret --from-literal=...`). 결국 PR 에 안 들어가는 단점.

**개선 방향** (Phase 2 작업):
- SOPS+age 로 암호화된 secret.enc.yaml → ArgoCD plugin 으로 복호화 후 apply
- 또는 ExternalSecret + Vault

### 2.4 cross-node 통신

K3s flannel CNI 는 노드 간 통신에 VXLAN 8472/UDP 사용. ufw 가 막으면 cross-node Pod 통신 자체가 fail. **5 노드 모두 ufw 8472 허용** 필요.

또 NodeLocal DNS 의 forward loop 문제도 cross-node 의존성. ([별도 글에서 정리](../k3s-nodelocal-dns-cluster-dns-디버깅/))

### 2.5 라우팅 — 같은 도메인 path 분기

옛 docker:
- `fashion.lemuel.co.kr` → nginx (호스트) → /api → fashion-app:8080, / → fashion-frontend:3000

K3s:
- backend / frontend 가 별도 Pod + Service
- 옵션:
  - (A) Ingress nginx 도입 (K3s ingress controller 추가)
  - (B) Cloudflare Tunnel 에서 path 분기 ⭐ 채택
  - (C) 별도 도메인 (api.fashion / fashion 분리)

**B 가 가장 가벼움**. Cloudflare Tunnel 의 Public Hostname 에 path `/api/*` 별 라우트 추가:

```
fashion.lemuel.co.kr  /api/*   → [LAN노드]:30086 (backend)
fashion.lemuel.co.kr  *        → [LAN노드]:30039 (frontend)
```

**순서 중요**: `/api/*` 가 catch-all (`*`) 보다 위에 있어야 함.

### 2.6 ghcr private 이미지

기본적으로 GitHub Actions 가 push 한 이미지는 **private**. K3s 가 pull 못 함 (403).

**3 가지 방식 비교**:
| 방식 | 장단점 |
|---|---|
| 패키지 public 변경 | 5초, but 보안 X — 데모용 |
| imagePullSecret + dockerconfigjson | 표준이지만 docker runtime 노드에서 자주 fail |
| **PAT + `/etc/rancher/k3s/registries.yaml`** | 운영 정석 ⭐ |

PAT 의 `read:packages` 권한만 등록. 5 노드 모두 적용. ([별도 글](../k3s-ghcr-private-pat-등록/))

### 2.7 image tag 전략

`:latest` 만 쓰면 새 이미지가 ghcr 에 올라가도 K3s 가 자동 pull 안 함 (`imagePullPolicy: IfNotPresent`).

**옵션**:
- (A) `imagePullPolicy: Always` + 매번 rollout restart
- (B) sha 태그 + ArgoCD Image Updater (자동 갱신)
- (C) GitOps 풀 사이클: 빌드 → image tag PR → ArgoCD sync

지금은 A 단계 (반자동). 다음 단계는 B/C 로 진화.

### 2.8 probe path

Spring Boot 의 `/actuator/health` 가 차트의 기본 probe path. 그런데 일부 서비스는 actuator 가 expose 안 되어 있어서 404.

**현실적 대응**:
- TCP socket probe (`tcpSocket: { port: 8080 }`) 가 가장 안전 — Tomcat 떠 있으면 OK
- 또는 `/` (welcome page) — but Spring Security 가 401/500 줄 수 있음

차트 표준은 **tcpSocket probe** 로 통일하는 게 마이그 마찰을 줄임.

---

## 3. 운영 차이점 8 가지

### 3.1 배포 — docker compose vs K3s

**docker compose**:
```bash
docker compose pull && docker compose up -d --remove-orphans
```
한 줄. 30초.

**K3s**:
```bash
helm template ... | kubectl apply -n <ns> -f -
kubectl rollout restart deployment ...
```
또는 helm install/upgrade. 2분.

→ docker compose 가 압도적으로 빠름. **단일 호스트 작업이라면**.

### 3.2 자가 치유

**docker compose**:
- restart: unless-stopped → 컨테이너 죽으면 재시작
- 노드 죽으면? 그 호스트의 컨테이너 다 다운, 다른 호스트로 옮기는 자동화 없음

**K3s**:
- Pod 죽으면 Deployment 가 새로 생성
- 노드 죽으면 다른 노드에 자동 재스케줄
- PriorityClass 로 OOM 시 우선순위 결정

→ K3s 가 **노드 단위 장애에 강함**.

### 3.3 롤링 배포

**docker compose**:
- 단순 `up -d` 는 컨테이너 정지 후 재생성 (다운타임 5~30초)
- 무다운타임 하려면 blue-green / nginx swap 수동

**K3s**:
- RollingUpdate (maxSurge/maxUnavailable) 로 자동 무다운타임
- replicaCount > 1 이면 진짜 0 다운타임

→ K3s 의 **롤링 배포가 자동**. 자주 배포할수록 차이 큼.

### 3.4 리소스 격리

**docker compose**:
- `deploy.resources` 옵션 있지만 swarm mode 가 아니면 무시
- 호스트 전체 리소스를 컨테이너가 자유롭게 씀

**K3s**:
- requests/limits 가 강제 (kubelet cgroup)
- LimitRange + ResourceQuota 로 namespace 단위 제한
- PriorityClass 로 OOM 시나리오 제어

→ K3s 가 **멀티 테넌시 / 안전성** 면에서 훨씬 좋음. 한 컨테이너가 메모리 다 먹어서 호스트가 죽는 사고 방지.

### 3.5 디버깅

**docker compose**:
- `docker logs`, `docker exec`, `docker stats` — 익숙하고 빠름

**K3s**:
- `kubectl logs`, `kubectl exec`, `kubectl describe`, `kubectl get events`
- 여러 노드 분산 → 어디 있는지 찾는 단계 한 번 더
- DNS / 네트워크 / 시크릿 / probe 등 layer 가 많아서 실패 지점 다양

→ docker compose 가 **디버깅 단순**. K3s 는 layer 가 많은 만큼 trouble 도 다양.

### 3.6 비밀번호 / 시크릿

**docker compose**:
- `.env` 파일 (호스트 평문)
- 환경변수로 컨테이너에 주입

**K3s**:
- Kubernetes Secret (base64 encoding, 평문에 가까움)
- SOPS+age, SealedSecret, Vault 같은 추가 도구 권장
- envFrom 으로 일괄 주입

→ 정상 운영이면 K3s 가 더 깔끔. 단 추가 도구 학습 필요.

### 3.7 모니터링

**docker compose**:
- Prometheus + node_exporter + 각 컨테이너 metrics endpoint 수동 설정
- 노드 추가 시 설정 갱신

**K3s**:
- ServiceMonitor / PodMonitor (Prometheus Operator)
- 새 Pod 자동 scrape
- kube-state-metrics, cAdvisor 등 자동

→ K3s 가 **확장성** 면에서 우위. 단 Prometheus Operator 도입 비용.

### 3.8 백업

**docker compose**:
- volume backup 은 직접 (tar, rclone)
- 데이터 손실 시 복구 절차 수동

**K3s**:
- Velero 같은 표준 도구 (PVC 백업 + 일정 스케줄링)
- 외부 스토리지 (S3, R2) 자동 업로드
- restore 명령 한 줄

→ K3s 의 **Velero 같은 도구가 표준화** 되어 있음. 백업/복구 자동화 쉬움.

---

## 4. 장단점 비교표

### docker compose ✅ 장점
- **단순함** — 명령 한 줄로 끝
- **빠른 시작** — 신규 서비스 부트스트랩 5분
- **디버깅 직관** — docker logs/exec 만 알면 됨
- **단일 호스트 운영** 에 최적

### docker compose ❌ 단점
- **노드 죽으면 다운** — 자동 fail over 없음
- **수평 확장 어려움** — replica 늘리려면 추가 호스트 설정
- **무다운타임 배포 수동**
- **멀티 테넌시 X**
- **GitOps 어려움** — declarative 약함

### K3s ✅ 장점
- **자가 치유 + 노드 분산**
- **롤링 배포 자동**
- **선언적 인프라 (helm chart + ArgoCD)**
- **리소스 거버넌스** (LimitRange, Quota, PriorityClass)
- **확장성** — replica 그냥 숫자 변경
- **표준 도구 풍부** (Velero, Prometheus Operator, cert-manager 등)
- **CV / 포트폴리오용 학습 가치 ★★★**

### K3s ❌ 단점
- **러닝 커브** — yaml 수, 디버깅 layer 다수
- **초기 셋업 비용** — flannel ufw, NodeLocal DNS, ghcr PAT, 차트 작성 등
- **간단한 단일 서비스에는 과함**
- **K8s 특이 함정** — 오늘 본 forward loop 같은 거
- **CI/CD 파이프라인 자체가 커짐** — GitHub Actions + ghcr + helm-deploy + ArgoCD

---

## 5. 어떤 워크로드를 어디로

### docker compose 그대로 두는 게 나은 워크로드

- **단일 컨테이너 + 호스트 의존성** (예: 시스템 패키지 직접 사용, sudo 권한 필요)
- **데이터베이스 (작은 규모)** — 단일 인스턴스 + 백업만 정기로
- **모니터링 도구 자체** (Prometheus, Grafana — K3s 위에서 K3s 를 모니터링하는 건 의존성 역전)
- **개발 / 임시 / PoC** — 빠른 부트스트랩 우선
- **호스트 시스템 도구** (portainer, uptime-kuma 같은 single-host 도구)

### K3s 로 옮기는 게 나은 워크로드

- **운영 앱** (배포 자주, 다운타임 민감)
- **MSA 형태 (multi-component)** — fashion / goods / academy 같은
- **수평 확장 필요한 stateless 서비스** — 트래픽 따라 replica 변경
- **데이터베이스 (StatefulSet)** — Persistent Storage + 노드 분산
- **포트폴리오 / 학습용** — K8s 운영 경험은 시장에서 가치

### 하이브리드가 현실적

오늘 마이그 결과 — **80% K3s + 20% docker compose** 하이브리드:

K3s (8 서비스):
- cost, dart, pilgrim, data, report, fashion, goods, grid, academy (Phase 2 진행)

docker compose 유지 (8개):
- portainer (관리 도구)
- uptime-kuma (모니터링)
- news (호스트 systemd gunicorn — Python 환경 의존)
- 데이비드의 Prometheus / Grafana / Loki / AlertManager (모니터링 스택)
- ghost-blog (단순 블로그)
- inter-asat (별도 Lightsail, 격리)

이게 **현실적 운영 구도**. 모든 걸 K3s 로 옮기는 건 오버엔지니어링.

---

## 6. 마이그 시 체크리스트

```
[ ] ghcr 이미지 빌드 CI 워크플로 (matrix 빌드)
[ ] PAT 가 K3s 5 노드 모두 등록되어 있는지
[ ] ufw 가 flannel 8472 허용
[ ] NodeLocal DNS forward 가 kube-dns-upstream 가리킴
[ ] 차트 templates: tcpSocket probe (actuator 의존 X)
[ ] LimitRange cpu ratio = 8, memory ratio = 2
[ ] 시크릿: stringData 로 평문, 운영 전 SOPS 암호화
[ ] postgres StatefulSet: nodeSelector + Retain reclaimPolicy
[ ] frontend/backend 분리: Cloudflare Tunnel path 분기
[ ] 옛 docker 정지 절차: 라우트 변경 → 검증 → docker compose down
```

---

## 7. 다음 단계 — Phase 2/3

오늘 끝낸 건 **단순 케이스 9 건**. 다음 단계:

- **Phase 2**: 복잡한 케이스 (academy 풀 마이그, news 시스템 처리, lowshopping/pharmacy MariaDB 같이 옮기기)
- **Phase 3 자동화**:
  - ArgoCD Image Updater 도입
  - sha 태그 GitOps
  - SOPS 시크릿 표준화
- **Phase 4 가시화**:
  - Prometheus ServiceMonitor 활용
  - Grafana K3s overview 대시보드

---

## 8. 회고

오늘 14 시간 작업. **트러블슈팅 7 시간, 실제 마이그 7 시간**. 진짜 마이그 작업은 차트 작성 + apply 라서 평탄한데, 매번 새로운 함정 (ufw, PAT, NodeLocal DNS, Spring Security probe, password placeholder) 이 나타남.

**K8s 의 진짜 비용은 학습 비용** 입니다. 한 번 셋업하면 다음부터 빠른데, 그 한 번이 길어요. 홈랩이라면 충분히 가치 있고, 실제 회사 운영이라면 SRE 1 명 풀타임이 필요합니다.

docker compose 와 K3s 는 **경쟁자가 아니라 다른 도구**. 빠른 부트스트랩 + 단일 호스트는 compose, 운영 + 확장성 + 학습은 K3s. **하이브리드가 정답** 인 게 오늘 마이그의 결론입니다.

---

이 시리즈 다른 글:
- [K3s 5노드 4-Tier 설계]({% post_url 2026-05-11-k3s-실전-5노드-4티어-설계 %})
- [솔로몬 스토리지 티어]({% post_url 2026-05-11-k3s-실전-솔로몬-스토리지-티어 %})
- [LimitRange + PriorityClass]({% post_url 2026-05-11-k3s-실전-거버넌스-limitrange-priorityclass %})
- [ufw flannel 8472]({% post_url 2026-05-11-k3s-flannel-ufw-8472-cross-node-함정 %})
- [ghcr PAT 등록]({% post_url 2026-05-11-k3s-ghcr-private-pat-등록 %})
- [NodeLocal DNS forward loop]({% post_url 2026-05-11-k3s-nodelocal-dns-cluster-dns-디버깅 %})
