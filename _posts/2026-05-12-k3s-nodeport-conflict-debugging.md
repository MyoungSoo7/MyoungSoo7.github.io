---
layout: post
title: "K3s NodePort 충돌 디버깅 — \"Employee Report 가 ASAT 도메인에 나오는 이유\""
date: 2026-05-12 22:55:00 +0900
categories: [infra, kubernetes, k3s, debugging]
tags: [k3s, nodeport, service, debugging, helm, conflict]
---

청각 재활 사이트 (eln.lemuel.co.kr) 에 들어갔는데 갑자기 **Employee Report 라는 페이지가 뜸**. 모든 게 정상 같은데 콘텐츠가 다른 이상한 버그. NodePort 충돌이 어떻게 다른 Service 의 응답을 만들어내는지, 어떻게 추적했는지 정리.

> 이 글에서 다루는 것
> - NodePort 충돌 시 K8s 가 어떻게 동작하나
> - 사용자가 알아채기 어려운 silent failure 패턴
> - 충돌 회피하는 NodePort 관리 전략

---

## 1. 증상 — 도메인이 잘못된 콘텐츠 응답

```
$ curl https://eln.lemuel.co.kr/
<title>Employee Report</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/.../ag-grid-quartz.css">
```

eln (ASAT, 청각 재활) 도메인인데 `report-prod` 의 Employee Report (사내 인사 도구) HTML 이 응답. CF Tunnel 도, K3s pod 도 다 Running 1/1 정상.

내부 확인:
```
$ kubectl get pods -n asat-prod
asat-app-...        1/1 Running
asat-frontend-...   1/1 Running
asat-postgres-0     1/1 Running
asat-redis-...      1/1 Running
asat-minio-0        1/1 Running
```

문제 없음. **그런데 외부 응답이 잘못된 콘텐츠.**

## 2. 디버깅 — NodePort 추적

CF Tunnel 라우트 확인:
```
eln.lemuel.co.kr → http://[내부VIP]:30097
```

NodePort 30097 이 누구거지?
```
$ kubectl get svc -A -o jsonpath='{range .items[?(@.spec.ports[0].nodePort==30097)]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}'
report-prod/report-app
```

⚠️ **report-prod 의 report-app 이 30097 점유 중.** asat-frontend 차트도 30097 로 설정했는데 등록 안 됐음.

asat 의 Service 상태:
```
$ kubectl get svc -n asat-prod
NAME          TYPE         CLUSTER-IP   EXTERNAL-IP   PORT(S)
asat-postgres ClusterIP    10.43.4.203  <none>        5432/TCP
asat-redis    ClusterIP    10.43.86.73  <none>        6379/TCP
asat-minio    ClusterIP    10.43.137.86 <none>        9000/TCP,9001/TCP
                                                       ← asat-app, asat-frontend 없음!
```

K3s 가 **NodePort 중복 감지하면 새 Service 등록 자체를 거부**. asat-app/asat-frontend Service 가 만들어지지도 않았음.

## 3. K8s NodePort 충돌의 silent failure

```
Service A (먼저 등록, port 30097)  ✅ 동작
Service B (NodePort 30097 요청)    ❌ "port already allocated" 에러
                                   → Service B 자체가 안 만들어짐
```

핵심 함정:
- Pod 는 정상 Running
- Helm chart sync 는 정상 (실패 안 함, 부분 적용)
- ArgoCD 도 Synced 표시
- 사용자가 직접 `kubectl get svc` 확인해야 알 수 있음

게다가 CF Tunnel 은 30097 origin 으로 라우팅 → 30097 응답하는 report-app 으로 트래픽 흘러감 → 사용자는 "eln 사이트 들어갔는데 다른 콘텐츠 나옴" 으로 인식.

## 4. 해결

```diff
# charts/asat/values.yaml
service:
  app:
    type: NodePort
-   nodePort: 30096   # ← grid-prod/grid-app 와 충돌
+   nodePort: 30102   # 사용 안 하는 포트
  frontend:
    type: NodePort
-   nodePort: 30097   # ← report-prod/report-app 와 충돌
+   nodePort: 30103
```

ArgoCD refresh → Service 정상 등록 → CF Tunnel origin 30103 으로 변경.

```
$ curl https://eln.lemuel.co.kr/
<title>ASAT — 청각 재활 훈련 시스템</title>   ✅
```

## 5. 사후 분석 — 왜 빨리 못 잡았나

| 사고 시점 | 봤어야 할 것 | 실제로 본 것 |
|---|---|---|
| 차트 작성 | 다른 차트의 NodePort 목록 | 30096-30099 가 비어있겠지 (잘못된 가정) |
| 배포 후 | `kubectl get svc -n asat-prod` | `kubectl get pods` (Running 만 확인) |
| 외부 확인 | 응답 HTML 의 title | HTTP 200 만 확인 |

## 6. 예방 — NodePort 관리 체크리스트

```bash
# 1. 새 NodePort 선정 전 사용 현황 확인
kubectl get svc -A -o jsonpath='{range .items[*]}{.spec.ports[*].nodePort}{"\n"}{end}' | sort -u
```

출력 예:
```
30001
30002
30039
30041
30086
30094
30095
30096    ← grid
30097    ← report
...
```

```bash
# 2. ArgoCD app refresh 후 Service 등록 검증
kubectl get svc -n <new-ns>
```

```bash
# 3. NodePort 응답 콘텐츠 검증 (HTML title 비교)
curl -s http://NODE_IP:NODE_PORT/ | grep -oE '<title>[^<]*</title>'
```

## 7. 더 나은 패턴 — NodePort 회피

NodePort 는 K8s 의 "필요악". 실제 production 에선 더 나은 옵션 있음:

| 방식 | 외부 노출 | 충돌 가능성 | 추천도 |
|---|---|---|---|
| **NodePort** (현재) | 노드:포트 | ✅ 30000-32767 한정, 충돌 위험 ★★★ | 홈랩/PoC |
| **Ingress** (nginx-ingress) | 도메인 path 기반 | ❌ 도메인 별로 분리 | Production |
| **LoadBalancer** (kube-vip/metallb) | VIP:443 | ❌ 외부 IP 풀에서 자동 할당 | Cloud-like |
| **Gateway API** | 새 표준 | 진행중 | 미래 |

홈랩에선 NodePort + Cloudflare Tunnel 조합이 비용 0 + 즉시 외부 노출이라 매력적이지만, NodePort 자체의 한계를 알고 써야 합니다.

## 8. 정리 — Silent failure 의 무서움

K8s 는 의외로 silent failure 가 많습니다:
- NodePort 충돌 (Service 미등록)
- nodeSelector 불일치 (Pod Pending, 다른 namespace 영향 없음)
- ImagePullBackOff (조용히 트래픽 안 받음)
- Readiness probe 실패 (endpoint 에서 빠짐)

**증상이 이상하면 항상 `kubectl get all -n <ns>` 부터.** Running 만 봐도 모자라고, Service 까지 확인.
