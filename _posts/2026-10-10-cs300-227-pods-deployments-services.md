---
layout: post
title: "[CS300 #227] 파드·디플로이먼트·서비스 — 쿠버네티스의 세 기본 객체"
date: 2026-10-10 21:47:00 +0900
categories: [cs]
tags: [cs300, devops, kubernetes, deployment, service]
---

컴퓨터공학 300 주제 시리즈의 227번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

파드는 함께 스케줄되는 컨테이너 묶음이자 배포의 최소 단위, 디플로이먼트는 파드를 원하는 수만큼 유지하고 무중단으로 버전을 바꾸는 관리자, 서비스는 계속 바뀌는 파드들 앞에 고정된 이름과 주소를 주는 문이다.

## 왜 필요한가

파드는 언제든 죽고 새로 만들어진다. 새 파드는 새 IP 를 받는다. 그러니 "IP 10.x.x.x 의 파드에 요청하라"는 설정은 오래가지 못한다. 또 파드를 직접 만들면 그 파드가 죽었을 때 아무도 다시 만들어 주지 않는다.

그래서 세 객체가 짝을 이룬다. 디플로이먼트가 파드의 수와 버전을 지키고, 서비스가 레이블로 파드를 찾아 고정된 입구를 준다. 이 셋을 이해하면 쿠버네티스에서 웹 애플리케이션 하나를 띄우는 데 필요한 것의 대부분을 이해한 것이다.

## 핵심 개념

### 파드(Pod)

파드는 하나 이상의 컨테이너가 **같은 네트워크 네임스페이스와 볼륨을 공유**하는 단위다.

- 파드 안 컨테이너들은 같은 IP 를 쓰고 `localhost` 로 서로 통신한다.
- 같은 노드에 함께 스케줄되고 함께 삭제된다.
- 대부분의 파드는 컨테이너 하나다. 여러 개를 넣는 것은 로그 수집, 프록시 같은 보조(sidecar) 컨테이너가 긴밀히 붙어야 할 때다.

파드의 생명주기 단계(phase)는 `Pending`, `Running`, `Succeeded`, `Failed`, `Unknown` 이다. `CrashLoopBackOff` 는 phase 가 아니라 컨테이너가 반복해서 죽어 kubelet 이 재시작 간격을 늘리며 기다리는 상태를 나타내는 이유(reason)다.

파드는 직접 만들지 않는다. 대신 디플로이먼트 같은 워크로드 객체가 만들게 한다.

### 프로브

kubelet 은 세 가지 프로브로 컨테이너를 점검한다.

| 프로브 | 실패하면 |
|---|---|
| livenessProbe | 컨테이너를 재시작한다 |
| readinessProbe | 서비스 엔드포인트에서 뺀다(트래픽을 안 보낸다). 재시작은 안 한다 |
| startupProbe | 성공할 때까지 다른 프로브를 미룬다. 느리게 뜨는 앱용 |

liveness 와 readiness 를 같은 검사로 두면 위험하다. DB 가 잠깐 느려졌을 때 모든 파드가 liveness 실패로 동시에 재시작해 장애를 키울 수 있다. liveness 는 "프로세스가 고장 났는가"만, readiness 는 "지금 요청을 받을 수 있는가"를 본다.

### 디플로이먼트(Deployment)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.27
          ports:
            - containerPort: 80
          resources:
            requests: { cpu: 100m, memory: 128Mi }
            limits: { memory: 256Mi }
          readinessProbe:
            httpGet: { path: /, port: 80 }
```

- 디플로이먼트는 직접 파드를 만들지 않고 **레플리카셋**을 만든다. 레플리카셋이 파드 수를 유지한다.
- `template` 이 바뀌면(예: 이미지 태그) 새 레플리카셋을 만들고, 새 것을 늘리면서 옛 것을 줄인다. 이것이 **롤링 업데이트**다.
- `maxSurge` 는 원하는 수보다 **더** 띄울 수 있는 최대 개수, `maxUnavailable` 은 업데이트 중 원하는 수보다 **모자라도** 되는 최대 개수다. 둘 다 기본값은 25% 이고, 퍼센트는 surge 는 올림, unavailable 은 내림으로 계산한다.
- 옛 레플리카셋은 0개로 줄어든 채 남아 있어 `kubectl rollout undo` 로 되돌릴 수 있다.

전략에는 `Recreate` 도 있다. 옛 파드를 모두 지운 뒤 새 파드를 만든다. 다운타임이 생기지만, 두 버전이 동시에 돌면 안 되는 경우(예: 같은 디스크를 단독으로 써야 하는 경우)에 쓴다.

### 서비스(Service)

서비스는 **레이블 셀렉터**로 파드 집합을 고르고, 그 앞에 안정된 가상 IP(ClusterIP)와 DNS 이름을 준다.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
```

같은 네임스페이스의 다른 파드는 `http://web` 으로, 다른 네임스페이스에서는 `web.<네임스페이스>.svc.cluster.local` 형태의 이름으로 접근한다. 셀렉터에 맞고 ready 인 파드의 주소 목록은 EndpointSlice 객체로 관리된다.

| 타입 | 노출 범위 |
|---|---|
| ClusterIP (기본) | 클러스터 내부 전용 가상 IP |
| NodePort | 모든 노드의 특정 포트(기본 범위 30000–32767)로 외부 노출 |
| LoadBalancer | 외부 로드밸런서를 붙여 노출. 클라우드나 별도 구현체가 필요 |
| ExternalName | 클러스터 밖 DNS 이름에 대한 CNAME 별칭 |

HTTP 경로·호스트 기반 라우팅은 서비스가 아니라 Ingress 나 Gateway API 가 맡는다.

### 레이블이 접착제다

```
Deployment(selector app=web)
   └─ ReplicaSet(app=web, pod-template-hash=abc)
        ├─ Pod(app=web) ─┐
        ├─ Pod(app=web) ─┼── Service(selector app=web) → EndpointSlice
        └─ Pod(app=web) ─┘
```

셀렉터와 레이블이 어긋나면 서비스는 아무 파드도 가리키지 않는다. "서비스는 있는데 연결이 안 된다"의 가장 흔한 원인이다.

## 직접 해 보기

롤링 업데이트가 `maxSurge`·`maxUnavailable` 안에서 어떻게 진행되는지 계산해 보자. 새 파드가 즉시 ready 가 된다고 단순화했다.

```python
import math

def rolling_update(replicas, surge="25%", unavail="25%"):
    def resolve(v, round_up):
        if isinstance(v, str) and v.endswith("%"):
            x = replicas * int(v[:-1]) / 100
            return math.ceil(x) if round_up else math.floor(x)
        return v
    max_surge, max_unavail = resolve(surge, True), resolve(unavail, False)
    if max_surge == 0 and max_unavail == 0:
        raise ValueError("maxSurge and maxUnavailable cannot both be 0")
    old, new, step = replicas, 0, 0
    print(f"replicas={replicas} maxSurge={max_surge} maxUnavailable={max_unavail}")
    while old > 0 or new < replicas:
        # 1) 총합이 replicas+maxSurge 를 넘지 않게 새 파드 추가
        add = min(replicas - new, replicas + max_surge - (old + new))
        new += max(add, 0)
        # 2) 가용 수가 replicas-maxUnavailable 아래로 안 가게 옛 파드 제거
        remove = min(old, (old + new) - (replicas - max_unavail))
        old -= max(remove, 0)
        step += 1
        print(f"  step {step}: old={old} new={new} total={old + new}")

rolling_update(4)
rolling_update(10)
rolling_update(3, surge=0, unavail=1)
```

결과는 다음과 같다.

```
replicas=4 maxSurge=1 maxUnavailable=1
  step 1: old=2 new=1 total=3
  step 2: old=0 new=3 total=3
  step 3: old=0 new=4 total=4
replicas=10 maxSurge=3 maxUnavailable=2
  step 1: old=5 new=3 total=8
  step 2: old=0 new=8 total=8
  step 3: old=0 new=10 total=10
replicas=3 maxSurge=0 maxUnavailable=1
  step 1: old=2 new=0 total=2
  step 2: old=1 new=1 total=2
  step 3: old=0 new=2 total=2
  step 4: old=0 new=3 total=3
```

두 값이 클수록 빨리 끝나지만 순간 자원 사용(surge)이나 용량 손실(unavailable)이 커진다. `maxSurge=0` 이면 추가 자원 없이 하나씩 교체한다. 자원이 빠듯한 작은 클러스터에서 쓰는 설정이다. 실제 컨트롤러는 새 파드가 ready 가 될 때까지 기다리므로 단계 사이 시간은 readinessProbe 에 좌우된다.

## 현업에서는

- **배포했는데 트래픽이 끊긴다.** readinessProbe 가 없으면 컨테이너가 뜨자마자 ready 로 취급되어, 앱이 초기화 중인데 요청이 들어간다. 종료 쪽도 있다. 파드가 SIGTERM 을 받은 뒤에도 잠깐 요청이 올 수 있으므로, 앱은 SIGTERM 을 받으면 진행 중인 요청을 마무리하고 끝내야 한다.
- **OOMKilled 와 CrashLoopBackOff.** 메모리 limit 을 넘으면 컨테이너가 강제 종료된다(`OOMKilled`). 반복되면 CrashLoopBackOff 가 된다. `kubectl describe pod` 의 Last State 와 종료 코드(137 = SIGKILL)를 본다.
- **"서비스는 있는데 연결이 안 돼요".** `kubectl get endpointslices -l kubernetes.io/service-name=web` 로 엔드포인트가 비었는지 본다. 비었다면 셀렉터·레이블 불일치나 readiness 실패다.
- **홈랩에서 외부 노출.** 클라우드가 없는 클러스터에서는 LoadBalancer 타입이 그냥 대기 상태에 머문다. NodePort 를 쓰거나, 경량 배포판이 넣어 주는 간이 로드밸런서나 MetalLB 같은 구현체를 쓴다.

## 확인 문제

1. 파드 안의 두 컨테이너는 서로 어떻게 통신하는가?
2. livenessProbe 와 readinessProbe 가 실패했을 때 결과는 각각 무엇인가?
3. 디플로이먼트가 롤백을 할 수 있는 이유는 무엇이 남아 있어서인가?
4. `replicas: 8`, `maxSurge: 25%`, `maxUnavailable: 25%` 일 때 업데이트 중 파드 총수의 최대값과 가용 파드 수의 최소값은?
5. 서비스의 엔드포인트가 비어 있다. 의심할 원인 두 가지는?

### 풀이

1. 같은 네트워크 네임스페이스를 공유하므로 `localhost` 와 포트로 통신한다.
2. liveness 실패: 컨테이너 재시작. readiness 실패: 서비스 엔드포인트에서 제외(재시작 없음).
3. 이전 template 의 레플리카셋이 0개로 줄어든 채 남아 있기 때문이다.
4. surge = ceil(2) = 2 이므로 최대 10개, unavailable = floor(2) = 2 이므로 최소 6개 가용.
5. 서비스 셀렉터와 파드 레이블 불일치, 파드들이 readiness 를 통과하지 못함.

## 더 읽을거리 (References)

- Kubernetes Docs, [Pods](https://kubernetes.io/docs/concepts/workloads/pods/)
- Kubernetes Docs, [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- Kubernetes Docs, [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- Kubernetes Docs, [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
