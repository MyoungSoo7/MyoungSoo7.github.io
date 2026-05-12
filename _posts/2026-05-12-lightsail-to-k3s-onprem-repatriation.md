---
layout: post
title: "AWS Lightsail → 5-노드 온프레미스 K3s 이관 — 월 $30 비용 0 으로"
date: 2026-05-12 22:40:00 +0900
categories: [infra, kubernetes, k3s, devops, aws]
tags: [aws, lightsail, k3s, repatriation, cost-optimization, cloudflare-tunnel]
---

서울 리전 Lightsail 2 인스턴스 (르무엘클라우드 + 포트폴리오클라우드) 에서 굴러가던 7 개 컨테이너 워크로드를 **온프레미스 K3s 클러스터로 이관**하고 인스턴스를 종료했습니다. 월 $24-30 비용 절감 + 모든 워크로드가 GitOps 로 통일된 후기.

> 이 글에서 다루는 것
> - 클라우드 → 온프레 이관 의사결정 기준
> - 데이터 보존 (PG dump + restore) 실전
> - 호스트 systemd 서비스 (judge-engine) 어떻게 처리했나
> - DB 가 호스트에 있는 워크로드 (MariaDB) K3s 에서 접근
> - Cloudflare Tunnel 라우팅 IP 변경 (apex domain 함정)

---

## 1. 인벤토리 — 무엇이 어디 있었나

```
르무엘클라우드 (43.201.110.54, 2vCPU 4GB)
├─ docker compose
│   ├─ media-app          (Pexels API, :8093)
│   ├─ codingtest-app     (Spring Boot, :8094)
│   ├─ database-app       (Spring Boot + MySQL, :8099)
│   └─ database-mysql     (MySQL 8.0)
└─ systemd
    └─ judge-engine       (C++ gRPC, lemuel-quant-core)

포트폴리오클라우드 (3.34.141.94, 2vCPU 4GB)
└─ docker compose (inter-asat 스택, eln.lmshi.site)
    ├─ asat-backend       (Spring Boot 4)
    ├─ asat-frontend      (Next.js)
    ├─ asat-postgres
    ├─ asat-redis
    └─ asat-minio
```

월 비용: $24 (2x Lightsail nano) + 기타.

## 2. 의사결정 — 왜 가져오나

| 평가 | 클라우드 | 온프레 (5 노드) |
|---|---|---|
| 월 비용 | $24+ | 0 (전기/인터넷 제외) |
| 컴퓨팅 | 2vCPU/4GB ×2 | ~40 vCPU / 80GB RAM |
| 디스크 | 60GB SSD ×2 | 4TB HDD + NVMe + 솔로몬 SSD |
| 운영 통일성 | 별도 docker compose | K3s + ArgoCD GitOps |
| DR 위험 | AWS 한 곳 | 노드 분산 |

온프레 용량 충분 + 운영 통일 가치 ↑.

## 3. inter-asat 이관 — 5-컴포넌트 + 실데이터

### 데이터 파악

```bash
$ docker exec asat-postgres pg_dump -U asat asat_dev | wc -l
9977   # 짧은 dump, 스키마만, 데이터 거의 없음

$ docker exec asat-minio mc du localminio
0B  0 objects   # MinIO 도 비어있음
```

19 테이블 있는데 데이터는 비어있음. 좋다 — 풀백업 + 신규 클러스터 띄우면 됨.

### Helm 차트 (5 컴포넌트)

`charts/asat/templates/` 구조:
- `postgres.yaml` — StatefulSet + PVC 10Gi
- `redis.yaml` — Deployment (캐시는 휘발 OK)
- `minio.yaml` — StatefulSet + PVC 10Gi
- `app.yaml` — Spring Boot, envFromSecret
- `frontend.yaml` — Next.js standalone

```yaml
# values.yaml 핵심
service:
  app:
    type: NodePort
    nodePort: 30102   # 처음 30096 으로 했다가 grid 와 충돌, 변경
  frontend:
    type: NodePort
    nodePort: 30103   # 처음 30097, report-app 과 충돌, 변경
```

### Secret 외부 주입

```bash
kubectl create secret generic asat-app-secret -n asat-prod \
  --from-literal=SPRING_DATA_REDIS_PASSWORD='기존prod값' \
  --from-literal=JWT_SECRET='asat-jwt-secret-...' \
  --from-literal=ASAT_INTERNAL_SERVICE_TOKEN='...' \
  --from-literal=ASAT_MINIO_ACCESS_KEY=asat_minio \
  --from-literal=ASAT_MINIO_SECRET_KEY='...' \
  --from-literal=CORS_ALLOWED_ORIGINS='https://eln.lemuel.co.kr'
```

### PG 복원

```bash
# 1. 클라우드에서 dump
ssh portfoliocloud "docker exec asat-postgres pg_dump -U asat asat_dev > /tmp/asat.sql"

# 2. local 로 가져오고 K3s 로 푸시
scp portfoliocloud:/tmp/asat.sql /tmp/
scp /tmp/asat.sql lemuel:/tmp/

# 3. K3s PG 에 복원
kubectl cp /tmp/asat.sql asat-prod/asat-postgres-0:/tmp/dump.sql
kubectl exec -n asat-prod asat-postgres-0 -- \
  psql -U asat -d asat_dev -f /tmp/dump.sql
```

19 테이블 + 2 users 복원 확인.

### NodePort 충돌 — 한 번 더 트러블

배포 후 외부 검증:
```
$ curl https://eln.lemuel.co.kr/
<title>Employee Report</title>   ← 청각재활인데?
```

`30097` 이 `report-prod/report-app` 이 19 시간 전부터 점유 중. asat 가 등록 거부됐고, CF Tunnel 이 `30097` → report-app HTML 응답.

→ asat NodePort 를 `30102/30103` 으로 변경 후 정상.

> **K3s NodePort 충돌 디버깅 팁**:
> ```bash
> kubectl get svc -A -o jsonpath='{range .items[*]}{.spec.ports[*].nodePort}{"\n"}{end}' | sort -u
> ```
> 새 NodePort 할당 전 항상 확인.

## 4. 르무엘클라우드 — judge-engine systemd 함정

codingtest-app 은 C++ gRPC 바이너리 (`judge_engine_grpc`) 호출. 이건 docker 가 아니라 **systemd 서비스** 였습니다 (sandbox + cgroup 권한 필요).

```ini
# /etc/systemd/system/judge-engine.service
[Service]
User=lqc
ExecStart=/opt/lqc/bin/judge_engine_grpc 127.0.0.1:50051
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/lqc/var
PrivateTmp=true
```

선택지:
1. K3s privileged Pod (sandbox 기능 일부 손실)
2. C++ → Docker 이미지 빌드 (1-2시간)
3. **르무엘 호스트에 그대로 systemd 이전 (옵션 A, 추천)**

옵션 A 절차:
```bash
# 1. /opt/lqc 통째로 압축
ssh lightsail "sudo tar czf /tmp/lqc.tgz -C /opt/lqc ."

# 2. 르무엘로 복사 + 압축 해제
scp lightsail:/tmp/lqc.tgz /tmp/
scp /tmp/lqc.tgz lemuel:/tmp/
ssh lemuel "sudo tar xzf /tmp/lqc.tgz -C /opt/lqc"
ssh lemuel "sudo useradd -r -s /usr/sbin/nologin -d /opt/lqc/home -m lqc"
ssh lemuel "sudo chown lqc:lqc /opt/lqc -R"

# 3. systemd 서비스 + 의존성 라이브러리
ssh lemuel "sudo apt install -y libgrpc++1.51t64 libgrpc29t64"
ssh lemuel "sudo systemctl enable --now judge-engine"

# 4. bind 0.0.0.0 변경 + ufw 오픈
sed -i 's|127.0.0.1:50051|0.0.0.0:50051|' /etc/systemd/system/judge-engine.service
sudo systemctl daemon-reload && sudo systemctl restart judge-engine
sudo ufw allow from 10.42.0.0/16 to any port 50051 proto tcp   # K8s pods
sudo ufw allow from [내부LAN] to any port 50051 proto tcp # LAN
```

K3s 의 codingtest-app 차트는 환경변수로 호출:
```yaml
env:
  - name: JUDGE_ENGINE_HOST
    value: "[LAN노드]"     # 르무엘 host (systemd)
  - name: JUDGE_ENGINE_PORT
    value: "50051"
```

> 교훈: **모든 걸 K8s 에 넣을 필요 없음.** sandbox 같은 호스트 권한 요구하는 워크로드는 systemd 가 깔끔.

## 5. database-app + MariaDB — 호스트 DB 그대로

lowshopping/pharmacy/api 가 르무엘 호스트의 MariaDB 10.11 (systemd) 를 쓰고 있었음. 다 docker 로 옮기지 않고:

```bash
# 1. MariaDB bind 127.0.0.1 → 0.0.0.0
sudo sed -i 's/^bind-address.*127.0.0.1/bind-address = 0.0.0.0/' \
  /etc/mysql/mariadb.conf.d/50-server.cnf
sudo systemctl restart mariadb

# 2. K8s pods 만 허용
sudo ufw allow from 10.42.0.0/16 to any port 3307 proto tcp
sudo ufw allow from [내부LAN] to any port 3307 proto tcp

# 3. root@'%' grant (LAN 만 허용된 상태)
sudo mariadb -uroot -p1005 -e \
  "GRANT ALL ON *.* TO 'root'@'%' IDENTIFIED BY '1005'; FLUSH PRIVILEGES;"
```

K3s 차트에서:
```yaml
env:
  - name: SPRING_DATASOURCE_URL
    value: "jdbc:mariadb://[LAN노드]:3307/myselectshop?..."
```

> **선택의 기준**: DB 마이그 비용 (시간/위험) vs 호스트 systemd 보존 비용. 30+ tables, 적극 사용 중인 prod DB 면 그대로 두는 게 안전.

## 6. Cloudflare Tunnel — apex 도메인 함정

ProdmainAPI 라우팅을 옮기면서 **lemuel.co.kr (apex)** 가 안 되는 문제:
```
$ curl -I https://lemuel.co.kr/
HTTP/2 522 (Connection timed out)
```

CF Tunnel 에 라우트 추가했는데도 안 됨. 원인:

```
DNS 탭:
A  lemuel.co.kr  182.225.28.203  Proxied   ← 옛 집 공인 IP!
```

apex 도메인은 서브도메인과 달리 **DNS 충돌 시 자동 CNAME 생성 안 됨**. 옛 A 레코드 삭제 → Public Hostname 라우트 재저장 → CF 가 자동 CNAME 생성 (`<tunnel-uuid>.cfargotunnel.com`) → 200 OK.

> CF apex 도메인 핫팁:
> - DNS 탭에서 충돌하는 A/AAAA/CNAME 먼저 삭제
> - Zero Trust > Tunnels > Public Hostnames 에서 추가 → 자동 CNAME

## 7. 비용 효과

```
Lightsail (작업 전): 2 × $12/mo = $24/mo
Lightsail (작업 후): 0          → 절감 $24/mo + 정적 IP/트래픽 추가 절감
온프레 추가 비용:    0           (기존 5 노드 활용)

연간 절감: $288 + α
```

## 8. 함께 정리한 것

- 끊긴 라우트 (sns/stock/k8s 등 localhost:8xxx 가리키던 것) 14 개 모두 새 NodePort 로 재라우팅
- 랜딩 페이지 `lemuel.co.kr/` 추가 (포트폴리오 진입점)
- 도메인별 K3s NodePort 정리:
  - jen / live / blog / jabis / chat / sns / eln / stock / media / codingtest / database / grafana / k8s / lemuel

총 13+ 외부 도메인이 모두 K3s 클러스터 경유.

---

## 9. 정리 — 클라우드는 언제 다시 쓸 것인가

이관 후 본질을 다시 생각해보면:

| 클라우드 (Lightsail) 가 더 나은 경우 |
|---|
| 고정 공인 IP 필수 (CDN endpoint 등) |
| 가정 인터넷이 비대칭/불안정 |
| 24x7 가동 보장 (UPS, 듀얼 ISP) 필요 |
| 글로벌 사용자 (지리 분산) |

홈랩 포트폴리오 용도는 온프레가 합리적. 진짜 서비스 단계 가면 그때 cloud-back.
