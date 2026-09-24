---
layout: post
title: "파드 하나가 뚫리면 어디까지 닿나 — 48개 네임스페이스 중 3개만 문이 있었다"
date: 2026-09-24 19:40:00 +0900
categories: [security]
tags: [kubernetes, networkpolicy, k3s, network-security, zero-trust, lateral-movement]
---

네트워크 보안이라고 하면 보통 바깥 경계부터 떠올린다. 방화벽, 포트 개방, TLS 같은 것들이다.
우리 클러스터도 공개 서비스는 주로 Cloudflare 터널을 거쳐 나간다. 바깥 문은 그나마 신경 써 온 셈이다.

그런데 공격자에게 더 중요한 질문은 그다음이다. **안에 한 번 들어온 다음, 어디까지 걸어갈 수 있나.**
이 글은 그 질문을 우리 k3s 클러스터에서 직접 재 본 기록이다. 내부 주소나 네트워크 구성은 적지 않고,
구조와 결과만 적는다.

## 쿠버네티스의 기본값은 "전부 열림"이다

[쿠버네티스 공식 문서](https://kubernetes.io/docs/concepts/services-networking/network-policies/)는 이렇게 쓴다.

> By default, a pod is non-isolated for ingress; all inbound connections are allowed.
> By default, a pod is non-isolated for egress; all outbound connections are allowed.

어떤 파드든 클러스터 안의 어떤 파드로든 연결할 수 있다는 뜻이다. 이걸 막는 도구가 **NetworkPolicy** 다.
단, 같은 문서의 경고처럼 정책은 네트워크 플러그인이 실제로 집행해야 의미가 있다.
정책을 집행하는 컨트롤러 없이 리소스만 만들면 아무 효과가 없다.

k3s 는 이 부분이 편하다. [k3s 문서](https://docs.k3s.io/networking/networking-services)에 따르면
kube-router 의 netpol 컨트롤러가 **내장**되어 있고, `--disable-network-policy` 로 끄지 않는 한 동작한다.
아래에서 보겠지만 우리 클러스터에서도 실제로 집행되고 있었다. 문제는 도구가 아니라, 정책을 거의 쓰지 않았다는 것이었다.

## 재 본 것 1 — 정책이 있는 네임스페이스

워크로드가 도는 네임스페이스 **48개** 중 NetworkPolicy 가 하나라도 있는 곳은 **3개**였다.

| 네임스페이스 성격 | 정책 | 출처 |
|---|---|---|
| GitOps 컨트롤러 | 7개 | 업스트림 차트가 기본 제공 |
| 메시지 브로커 | 2개 | 오퍼레이터가 생성 |
| AI 에이전트 | 3개 | **직접 작성** — 에이전트별 egress 제한 |

이 중 우리가 의도해서 쓴 건 AI 에이전트 네임스페이스 하나뿐이다. 나머지 45개 네임스페이스,
즉 정산 서비스, 각종 앱, DB 들에는 정책이 하나도 없다. 네임스페이스 전체를 막는 default-deny 정책은 어디에도 없었다.

## 재 본 것 2 — 실제로 연결해 보기

설정만 보고 판단하지 않고, 파드 안에서 TCP 연결을 직접 시도했다(연결만 하고 인증이나 데이터 요청은 하지 않았다).

**출발점 A: 정산 서비스의 영수증 OCR 파드 (정책 없음)**

| 목적지 | 결과 |
|---|---|
| 다른 서비스의 PostgreSQL #1 | 🔓 열림 |
| 다른 서비스의 PostgreSQL #2 | 🔓 열림 |
| 민감한 자체 호스팅 앱 | 🔓 열림 |
| 모니터링 대시보드 | 🔓 열림 |
| 쿠버네티스 API 서버 | 🔓 열림 |

영수증을 읽는 파드는 사진 앱의 DB 나 다른 제품의 DB 와 이야기할 이유가 없다. 그런데 네트워크상으로는 전부 닿는다.
물론 각 DB 에는 비밀번호가 있다. 하지만 그건 **마지막 한 겹**이다. 비밀번호가 약하거나, 재사용됐거나, 인증 없는 관리 포트가 하나라도 있으면
OCR 라이브러리의 취약점 하나가 곧 다른 서비스의 데이터 유출로 이어진다. 이런 이동을 **측면 이동(lateral movement)** 이라고 부른다.

**출발점 B: 보안 에이전트 파수꾼 파드 (egress 정책 있음)**

| 목적지 | 결과 |
|---|---|
| 정산 Redis | 🔒 거부 |
| 정산 PostgreSQL | 🔒 거부 |
| 민감한 자체 호스팅 앱 | 🔒 거부 |
| 모니터링 대시보드 | 🔒 거부 |

같은 클러스터, 같은 목적지인데 결과가 정반대다. 파수꾼의 egress 정책에는 조사에 필요한 곳(로그 저장소, 쿠버네티스 API, LLM 엔드포인트 등)만 적혀 있고,
나머지는 전부 거부된다. **정책 하나로 벽이 생긴다**는 것, 그리고 k3s 의 내장 컨트롤러가 실제로 집행하고 있다는 것을 같이 확인한 셈이다.

## 왜 AI 에이전트만 막혀 있었나

우연이 아니다. LLM 에이전트는 프롬프트 인젝션으로 **행동이 조종될 수 있는** 프로세스다.
알림 본문이나 로그 한 줄에 "이 주소로 데이터를 보내라"가 섞여 들어올 수 있다. 그래서 에이전트를 만들 때 "무엇에 닿을 수 있는가"를 먼저 정했다.

그런데 돌아보면 같은 논리가 모든 파드에 적용된다. OCR 라이브러리, 이미지 파서, 오래된 의존성 하나. 조종당할 수 있는 건 LLM 만이 아니다.

## 고치는 순서

한 번에 전부 default-deny 를 걸면 무엇이 깨질지 모른다. 그래서 위험한 곳부터, 좁게 시작한다.

### 1단계 — DB 네임스페이스부터 ingress 를 닫는다

DB 는 "누가 나한테 오는가"가 가장 명확하다. 해당 서비스의 앱 파드와 백업 잡만 허용한다.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: postgres-ingress
  namespace: example-prod
spec:
  podSelector:
    matchLabels:
      app: example-postgres
  policyTypes: ["Ingress"]
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: example-app        # 같은 네임스페이스의 앱만
    ports:
    - port: 5432
```

주의할 점이 있다. 여러 서비스가 **DB 서버 하나를 공유**하고 있으면, 허용 목록이 그 서비스들 전부를 포함해야 한다.
오늘 다른 작업을 하다가, 한 네임스페이스의 PostgreSQL 이 다른 제품군 전체의 DB 까지 겸하고 있다는 걸 알게 됐다. 정책을 쓰기 전에 **실제 접속 목록**(`pg_stat_activity`)부터 보는 게 안전하다.

### 2단계 — 네임스페이스 default-deny + 필요한 것만 허용

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: example-prod
spec:
  podSelector: {}                 # 네임스페이스의 모든 파드
  policyTypes: ["Ingress", "Egress"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: example-prod
spec:
  podSelector: {}
  policyTypes: ["Egress"]
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - {port: 53, protocol: UDP}
    - {port: 53, protocol: TCP}
```

[공식 문서](https://kubernetes.io/docs/concepts/services-networking/network-policies/)가 따로 경고하듯, egress 를 막으면 **DNS 도 막힌다**.
DNS 허용 정책을 같이 넣지 않으면 모든 게 이름 해석 단계에서 깨진다. 노드 로컬 DNS 캐시를 쓰는 클러스터라면 그 경로도 허용해야 한다.

### 3단계 — 인그레스 컨트롤러와 모니터링을 잊지 않는다

default-deny 를 건 뒤 자주 깨지는 두 가지가 있다.

- 외부 요청을 받아 넘겨주는 **인그레스 컨트롤러 → 앱** 경로
- 메트릭을 긁어 가는 **Prometheus → 앱** 경로

둘 다 다른 네임스페이스에서 들어오므로 `namespaceSelector` 로 명시적으로 열어 줘야 한다.

### 4단계 — 적용 후에는 오늘처럼 직접 연결해 본다

정책은 YAML 로 보면 맞아 보인다. 하지만 집행 여부, 셀렉터 오타, 라벨 누락은 **연결해 봐야** 드러난다.
허용해야 할 경로는 열리고 막아야 할 경로는 닫히는지, 출발점 A/B 표를 다시 만들어 보는 것까지가 작업이다.

## 정리

- 쿠버네티스 네트워크의 기본값은 **평평함**이다. 정책을 쓰지 않으면 모든 파드가 모든 파드와 닿는다.
- k3s 는 정책 컨트롤러가 내장돼 있어 도구는 이미 있다. 우리 문제는 **안 쓴 것**이었다 (48개 중 3개).
- 정책이 걸린 에이전트 파드에서는 같은 목적지가 전부 거부됐다. 벽은 YAML 한 장으로 생긴다.
- 순서: DB ingress → 네임스페이스 default-deny + DNS → 인그레스·모니터링 허용 → 실측 검증.

바깥 문을 잠그는 것만큼, **안쪽 방문들**을 잠그는 게 중요하다.

## References

- Kubernetes 문서, *Network Policies* (기본 비격리, default deny, DNS 주의) — <https://kubernetes.io/docs/concepts/services-networking/network-policies/>
- K3s 문서, *Networking Services* (내장 Network Policy Controller, kube-router netpol) — <https://docs.k3s.io/networking/networking-services>
