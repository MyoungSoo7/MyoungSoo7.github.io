---
layout: post
title: "[CS300 #157] 로드 밸런싱 — L4 와 L7, 무엇을 보고 나누는가"
date: 2026-10-10 20:37:00 +0900
categories: [cs]
tags: [cs300, networking, load-balancing, consistent-hashing, nginx]
---

컴퓨터공학 300 주제 시리즈의 157번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

로드 밸런서는 들어오는 트래픽을 여러 백엔드에 나누는 장치다. L4 로드 밸런서는 IP·포트(연결 단위)만 보고 나누고, L7 로드 밸런서는 HTTP 요청을 해석해 경로·호스트·헤더(요청 단위)로 나눈다.

## 왜 필요한가

서버 한 대는 언젠가 한계에 닿고, 언젠가 죽는다. 여러 대로 나눠 받으면 처리량이 늘고, 한 대가 죽어도 서비스가 이어진다. 로드 밸런서는 이 둘을 동시에 해결한다.

그러나 로드 밸런서는 그 자체로 장애 지점이자 디버깅을 어렵게 하는 층이다. "서버 세 대 중 한 대만 계속 과부하", "gRPC 트래픽이 한 파드에만 몰림", "배포 중 잠깐 502", "로그인 세션이 자꾸 풀림" 같은 문제는 로드 밸런서가 무엇을 보고 어떻게 나누는지 알아야 풀린다.

## 핵심 개념

### L4 와 L7

| 항목 | L4 로드 밸런서 | L7 로드 밸런서 |
|---|---|---|
| 보는 정보 | 프로토콜, 출발지·목적지 IP, 포트 | HTTP 메서드, 경로, 호스트, 헤더, 쿠키 |
| 분산 단위 | 연결(TCP), 흐름(UDP) | 요청 |
| TLS | 그대로 통과(종료하지 않음)가 일반적 | 보통 여기서 종료하고 내용을 본다 |
| 기능 | 빠르고 단순, 프로토콜 무관 | 경로 기반 라우팅, 재시도, 헤더 조작, 인증, 캐시 |
| 예 | 리눅스 IPVS, 클라우드 네트워크 LB, 쿠버네티스 Service | nginx, HAProxy(HTTP 모드), Envoy, Ingress 컨트롤러 |

L7 은 클라이언트와 TCP·TLS 연결을 끝내고, 백엔드와는 별도의 연결을 맺는 프록시다. 그래서 요청마다 다른 백엔드로 보낼 수 있다. 대가는 CPU(파싱과 암호화)와 지연이다. L4 는 패킷이나 연결 단위로 전달만 하므로 빠르지만, HTTP/2 처럼 한 연결에 많은 요청을 싣는 프로토콜에서는 연결이 한 백엔드에 고정돼 요청이 고르게 나뉘지 않는다.

### 분산 알고리즘

| 알고리즘 | 동작 | 적합한 경우 |
|---|---|---|
| 라운드 로빈 | 차례대로 하나씩 | 요청 비용이 비슷할 때. nginx 의 기본값 |
| 가중 라운드 로빈 | 가중치 비율대로 | 서버 성능이 다를 때 |
| 최소 연결(least connections) | 활성 연결이 가장 적은 곳 | 요청 처리 시간이 들쭉날쭉할 때 |
| 해시(IP, URL 등) | 키의 해시로 고정 배정 | 같은 클라이언트·같은 키를 같은 서버로 |
| 일관성 해시 | 해시 링 위에서 가장 가까운 서버 | 서버 수가 바뀌어도 재배정을 최소화(캐시 서버 등) |
| 무작위 두 개 중 선택 | 둘을 무작위로 뽑아 덜 바쁜 쪽 | 분산된 여러 LB 가 독립적으로 결정할 때 |

일반 해시(`hash(key) % N`)는 서버 수 N 이 하나만 바뀌어도 대부분의 키가 다른 서버로 옮겨 간다. 캐시 서버 앞이라면 캐시가 한꺼번에 비는 셈이다. 일관성 해시는 키와 서버를 같은 원형 공간에 올려, 서버가 하나 늘거나 줄 때 대략 1/N 의 키만 옮겨 가게 한다. nginx 의 `hash ... consistent` 는 ketama 방식의 일관성 해시를 쓴다.

### 헬스 체크

- 능동(active) 헬스 체크: LB 가 주기적으로 백엔드에 요청(예: `GET /healthz`)을 보내 응답을 확인한다.
- 수동(passive) 헬스 체크: 실제 요청의 실패를 보고 판단한다. nginx 오픈 소스는 이 방식으로, `fail_timeout` 동안 `max_fails` 번(기본 1번) 실패하면 그 서버를 `fail_timeout` 동안 제외했다가 다시 실제 요청으로 시험한다.

헬스 체크 엔드포인트는 "프로세스가 살아 있다"와 "요청을 받을 준비가 됐다"를 구분해야 한다. 쿠버네티스의 liveness 와 readiness 가 이 구분이다.

### 세션 고정(sticky session)

서버 메모리에 세션을 두는 앱은 같은 사용자를 같은 서버로 보내야 한다. 쿠키나 출발지 IP 해시로 고정한다. 하지만 그 서버가 죽으면 세션이 사라지고, 부하도 치우친다. 세션을 Redis 같은 외부 저장소로 빼고 서버를 상태 없게(stateless) 만드는 것이 근본 해결이다.

### 클라이언트 IP 보존

프록시를 거치면 백엔드는 프록시의 IP 만 본다. L7 은 `X-Forwarded-For` 헤더로 원래 IP 를 전달한다(이 헤더는 클라이언트가 위조할 수 있으니, 신뢰하는 프록시가 붙인 값만 믿는다). L4 는 PROXY 프로토콜이나, 주소를 바꾸지 않는 전달 방식(DSR, Direct Server Return)을 쓴다.

## 직접 해 보기

일반 해시와 일관성 해시에서 서버를 하나 추가할 때 키가 얼마나 옮겨 가는지 비교한다. 서버 이름은 예시다.

```python
import hashlib, bisect

def h(s):
    return int.from_bytes(hashlib.md5(s.encode()).digest()[:8], "big")

def mod_assign(keys, servers):
    return {k: servers[h(k) % len(servers)] for k in keys}

class Ring:
    def __init__(self, servers, vnodes=160):           # 서버당 가상 노드 160개
        self.points = sorted((h(f"{s}#{i}"), s) for s in servers for i in range(vnodes))
        self.hashes = [p for p, _ in self.points]
    def get(self, key):
        i = bisect.bisect(self.hashes, h(key)) % len(self.points)
        return self.points[i][1]

keys = [f"user:{i}" for i in range(100000)]
before = ["app-a", "app-b", "app-c", "app-d"]
after = before + ["app-e"]

m1, m2 = mod_assign(keys, before), mod_assign(keys, after)
moved_mod = sum(m1[k] != m2[k] for k in keys) / len(keys)

r1, r2 = Ring(before), Ring(after)
moved_ring = sum(r1.get(k) != r2.get(k) for k in keys) / len(keys)

print(f"서버 4 -> 5 대, 일반 해시 재배정 비율 : {moved_mod:.1%}")
print(f"서버 4 -> 5 대, 일관성 해시 재배정 비율: {moved_ring:.1%}  (이론값 1/5 = 20%)")

load = {}
for k in keys: load[r2.get(k)] = load.get(r2.get(k), 0) + 1
print("일관성 해시 서버별 키 수:", dict(sorted(load.items())))

# 라운드 로빈과 최소 연결 비교: 요청 처리 시간이 들쭉날쭉할 때
import random
def simulate(policy, n=5000, servers=4):
    random.seed(7)                                             # 두 정책에 같은 요청열
    active = [[] for _ in range(servers)]; t = 0.0; rr = 0; peak = 0
    for _ in range(n):
        t += 0.01
        for s in range(servers): active[s] = [e for e in active[s] if e > t]
        if policy == "rr": s = rr % servers; rr += 1
        else: s = min(range(servers), key=lambda i: len(active[i]))
        cost = random.choice([0.01, 0.01, 0.01, 0.5])           # 4건 중 1건은 무거운 요청
        active[s].append(t + cost); peak = max(peak, len(active[s]))
    return peak
print("동시 처리 최대치  라운드 로빈:", simulate("rr"), "| 최소 연결:", simulate("lc"))
```

```
서버 4 -> 5 대, 일반 해시 재배정 비율 : 79.9%
서버 4 -> 5 대, 일관성 해시 재배정 비율: 22.1%  (이론값 1/5 = 20%)
일관성 해시 서버별 키 수: {'app-a': 18383, 'app-b': 19263, 'app-c': 19212, 'app-d': 21004, 'app-e': 22138}
동시 처리 최대치  라운드 로빈: 10 | 최소 연결: 6
```

서버를 한 대 늘렸을 뿐인데 일반 해시에서는 키의 80% 가 자리를 옮겼다. 일관성 해시는 이론값 20% 근처인 22% 만 옮겼고, 옮긴 키는 모두 새 서버 `app-e` 로 갔다. 서버당 가상 노드를 여러 개 두는 이유는 서버별 키 수를 고르게 하기 위해서다. 가상 노드가 하나뿐이면 링 위 간격이 들쭉날쭉해 어떤 서버는 몇 배의 키를 받는다.

아래 시뮬레이션에서는 네 건 중 한 건이 50배 무거운 요청이다. 라운드 로빈은 무거운 요청이 쌓인 서버에도 차례가 오면 계속 보내 한 서버의 동시 처리 수가 10까지 올랐고, 최소 연결은 6에서 멈췄다. 같은 요청열이라도 고르는 규칙에 따라 꼬리 지연이 달라진다.

## 현업에서는

- 쿠버네티스 Service(ClusterIP, NodePort, LoadBalancer)는 L4 다. kube-proxy 가 연결 단위로 엔드포인트를 고른다. Ingress 와 Gateway API 는 L7 이다(160번 글).
- gRPC 처럼 오래 사는 HTTP/2 연결은 L4 Service 만으로는 고르게 분산되지 않는다. L7 프록시(Envoy, 서비스 메시)나 클라이언트 측 분산(헤드리스 Service + 클라이언트 LB)을 쓴다.
- 배포 중 502 를 줄이려면 readiness probe 로 준비되지 않은 파드를 빼고, 종료 시 preStop 대기로 LB 가 엔드포인트를 빼는 시간을 벌어 준다.
- 홈랩 k3s 클러스터에서는 기본 ServiceLB 나 MetalLB 가 LoadBalancer 타입 Service 에 IP 를 주고(L4), Traefik 같은 Ingress 컨트롤러가 그 뒤에서 호스트·경로별로 나눈다(L7). 두 층을 구분해야 "어디서 막혔나"를 말할 수 있다.

## 확인 문제

1. HTTP/2 를 쓰는 서비스 앞에 L4 로드 밸런서만 두면 어떤 문제가 생기는가?
2. `hash(key) % N` 방식이 캐시 서버 분산에 나쁜 이유는?
3. 능동 헬스 체크와 수동 헬스 체크의 차이를 한 문장씩 쓰라.
4. 백엔드가 `X-Forwarded-For` 헤더를 그대로 믿으면 어떤 위험이 있는가?
5. 요청 처리 시간이 크게 들쭉날쭉한 서비스에 라운드 로빈보다 최소 연결이 나은 이유는?

### 풀이

1. 한 연결에 많은 요청이 다중화되는데 L4 는 연결 단위로만 배정하므로, 요청이 특정 백엔드에 몰린다.
2. 서버 수가 하나만 바뀌어도 대부분의 키가 다른 서버로 재배정되어 캐시 적중률이 한꺼번에 무너지기 때문이다.
3. 능동은 LB 가 주기적으로 별도 확인 요청을 보내 판단하고, 수동은 실제 사용자 요청의 실패를 관찰해 판단한다.
4. 클라이언트가 임의 값을 넣어 IP 를 위조할 수 있어, IP 기반 접근 제어나 감사 로그가 속을 수 있다. 신뢰하는 프록시가 붙인 값만 써야 한다.
5. 라운드 로빈은 무거운 요청이 몰린 서버에도 차례대로 계속 보내지만, 최소 연결은 아직 처리 중인 요청이 적은 서버를 골라 부하를 고르게 한다.

## 더 읽을거리 (References)

- nginx 문서, *Using nginx as HTTP load balancer*: <https://nginx.org/en/docs/http/load_balancing.html>
- nginx 문서, *Module ngx_http_upstream_module* (hash consistent): <https://nginx.org/en/docs/http/ngx_http_upstream_module.html>
- Envoy 문서, *Load balancing overview*: <https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/overview>
- Kubernetes 문서, *Virtual IPs and Service Proxies*: <https://kubernetes.io/docs/reference/networking/virtual-ips/>
- Karger, D. et al., "Consistent Hashing and Random Trees", *Proceedings of the 29th ACM STOC*, 1997 (서지 정보)
