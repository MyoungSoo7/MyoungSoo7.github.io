---
layout: post
title: "CrashLoopBackOff 의 진짜 피해는 '죽는 것' 이 아니라 5분이었다"
date: 2026-09-13 01:10:44 +0900
categories: [SRE, K8s]
tags: [kubernetes, kubelet, k3s, crashloopbackoff, eck, elasticsearch]
---

운영 중인 K3s 클러스터에서 ECK(Elastic Cloud on Kubernetes) operator 가 하루에도 수십 번씩
죽었다 살아나는 걸 쫓다가, 결국 **컨테이너가 아니라 kubelet 설정을 고쳐서** 끝냈다.
그 과정에서 "벤더 쪽에서 고치는 게 맞다" 는 첫 직감이 두 번 틀렸고, 두 번 다 *확인해봤더니
불가능* 해서 방향을 틀었다. 그 기록이다.

## 증상

`elastic-operator` 파드가 기동 직후 종료된다. 특이한 건 **종료 코드가 0** 이라는 점이다.

```
{"log.level":"error","message":"Failed to get operator info", ...}
{"log.level":"error","message":"Operator stopped with error", ...}
Error: Get "https://10.43.0.1:443/api/v1/namespaces/elastic-system/configmaps/elastic-operator-uuid?timeout=1m0s": net/http: TLS handshake timeout
```

기동 로그 첫 줄과 에러 줄의 타임스탬프 차이는 정확히 **15초**. 파드 이벤트상으로는
`startedAt` 과 `finishedAt` 이 거의 같고, 재시작 카운터만 계속 올라간다.
클러스터 노드 간 링크가 간헐적으로 불안정한 환경이라, apiserver 로 가는 첫 요청이
종종 실패한다는 것까지는 금방 알 수 있었다.

## 첫 번째 오진 — initContainer 로 막으면 되지 않나

가장 먼저 떠올린 건 "apiserver 가 닿을 때까지 기다렸다가 시작" 이다.
StatefulSet 에 apiserver 도달을 확인하는 initContainer 를 넣었고, 실제로 새 파드는
깔끔하게 떴다. 여기서 끝났다고 보고했는데, **틀렸다.**

며칠 뒤 같은 에러로 재시작이 4번 더 찍혔다. 이유는 단순하다.

> **initContainer 는 파드가 생성될 때 한 번만 실행된다.**
> 파드는 그대로 둔 채 컨테이너만 재시작되는 경로에서는 다시 실행되지 않는다.

Kubernetes 공식 문서도 init 컨테이너의 실행 시점을 "앱 컨테이너가 시작되기 전, 파드
시작 과정에서" 로 정의한다.[^init] 파드가 살아있는 상태에서 kubelet 이 앱 컨테이너만
재시작하는 경우는 여기에 해당하지 않는다.
즉 이 처방은 "파드 신규 생성 시 즉사" 만 막고, "기동 후 네트워크가 흔들려서 나는 재시작" 은
하나도 막지 못한다. 효과 범위를 잘못 말한 셈이라 그대로 정정했다.

## 두 번째 오진 — 클라이언트 타임아웃을 늘리면 되지 않나

다음 후보는 "operator 의 apiserver 클라이언트 타임아웃·재시도를 늘린다" 였다.
이것도 **안 된다.** 두 가지 이유가 있고, 둘 다 직접 확인했다.

**(1) ECK 에 재시도 옵션이 없다.**
operator 바이너리의 플래그를 전수로 뽑아보면 타임아웃 관련은 세 개뿐이다.

```
--elasticsearch-client-timeout duration   (default 3m0s)
--kube-client-qps float32
--kube-client-timeout duration            (default 1m0s)
```

retry / backoff / attempts 류 플래그는 존재하지 않는다.

**(2) 그리고 늘려도 이 에러는 안 막힌다.**
에러 메시지를 다시 보면 URL 에 이미 `timeout=1m0s` 가 붙어 있다. 즉 요청 타임아웃은
아직 지나지도 않았다. 실제로 터진 건 `net/http: TLS handshake timeout` —
**TLS 핸드셰이크 타임아웃**이고, 이건 요청 단위 설정이 아니라 전송 계층 설정이다.

client-go 가 쓰는 트랜스포트는 `k8s.io/apimachinery` 의 `SetOldTransportDefaults()` 를
거치는데, 여기서 `TLSHandshakeTimeout` 이 비어 있으면 Go 표준 라이브러리의
`http.DefaultTransport` 값을 그대로 복사한다.[^apimachinery]

```go
if t.TLSHandshakeTimeout == 0 {
    t.TLSHandshakeTimeout = defaultTransport.TLSHandshakeTimeout
}
```

그리고 Go 의 `http.DefaultTransport` 에서 그 값은 **10초 고정**이다.[^gotransport]

```go
var DefaultTransport RoundTripper = &Transport{
    ...
    TLSHandshakeTimeout:   10 * time.Second,
    ...
}
```

`--kube-client-timeout` 을 5분으로 올려도 10초에 죽는 건 똑같다.
앞서 관측한 "기동 15초 만에 종료" 와도 아귀가 맞는다.

**(3) 컨테이너 안에서 감싸는 것도 안 된다.**
"셸 스크립트로 감싸서 될 때까지 기다렸다가 exec" 이라는 우회도 생각했는데,
`docker.elastic.co/eck/eck-operator:2.16.1` 은 distroless 라 `/bin/sh` 도 `ls` 도 `curl` 도
없다. 확인은 간단하다.

```
$ kubectl exec elastic-operator-0 -- /bin/sh -c 'echo ok'
exec: "/bin/sh": stat /bin/sh: no such file or directory
```

여기서 방향이 바뀌었다. **벤더 컨테이너 쪽에서는 손댈 구석이 없다.**

## 문제를 다시 정의하기

그래서 다시 물었다. *죽는 게 정말 문제인가?*

operator 는 컨트롤러다. 죽어 있는 동안 Elasticsearch·Kibana·Logstash 데이터 경로는
멀쩡하다. 실제 피해는 "죽어 있는 시간" 이고, 그 시간의 대부분은 네트워크 장애가 아니라
**kubelet 의 백오프 대기**였다.

Kubernetes 의 기본 재시작 백오프는 이렇게 동작한다.[^kep]

> 파드의 재시작 정책이 `Never` 가 아닐 때, 컨테이너가 종료되면 kubelet 은 지수 백오프
> 지연(10s, 20s, 40s, …)을 두고 재시작하며 **5분에서 상한**을 친다. 이 5분 지연은 컨테이너가
> 최대 백오프의 2배(=10분) 동안 문제없이 실행될 때까지 유지되고, 그때 백오프 카운터가 초기화된다.

즉 링크가 몇 초 끊겼다가 돌아와도, 이미 백오프가 커져 있으면 operator 는 **최대 5분을 더
놀고** 나서야 돌아온다. 그동안 Elasticsearch 리소스의 reconcile 이 멈춘다.
링크 불안정 자체는 이 클러스터의 설계상 감수하기로 한 부분이라, 고쳐야 할 건
"복귀가 느리다" 쪽이었다.

## 해법: 노드 단위로 백오프 상한을 낮춘다

이 상한은 최근 조절 가능해졌다. KEP-5593(원래 KEP-4603 의 일부였다가 분리됐다) 이
`crashLoopBackOff.maxContainerRestartPeriod` 를 KubeletConfiguration 에 추가했다.[^kep]
값의 범위는 **1s ~ 300s** 이고, 설정하지 않으면 내부 기본값 300s 를 쓴다.[^kubeletapi]

기능 게이트 `KubeletCrashLoopBackOffMax` 의 상태는 이렇다.[^gates]

| 버전 | 단계 | 기본값 |
| --- | --- | --- |
| 1.32 ~ 1.34 | Alpha | `false` |
| 1.35 ~ | Beta | `true` |

대상 클러스터가 `v1.35.4+k3s1` 이라 **게이트를 따로 켤 필요 없이 값만 넣으면 된다.**
30초로 잡았다.

## K3s 에서 kubelet 설정 파일 넣기

여기서 한 번 더 헷갈리기 쉽다. `/etc/rancher/k3s/config.yaml` 은 **k3s 설정**이지
kubelet 설정이 아니다. kubelet 설정은 다른 경로다.

K3s 공식 문서는 v1.32 이상에서 **드롭인 파일 방식을 권장**한다.[^k3s]
k3s 는 자기 기본값을 `00-k3s-defaults.conf` 로 써두고, 같은 디렉터리의 파일들을 병합한다.

```
/var/lib/rancher/k3s/agent/etc/kubelet.conf.d/
├── 00-k3s-defaults.conf   ← k3s 가 매 기동 때 생성
└── 10-crashloop.conf      ← 여기에 추가
```

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
crashLoopBackOff:
  maxContainerRestartPeriod: 30s
```

주의할 규칙이 세 가지 있다. 셋 다 지키지 않으면 조용히 무시되거나 kubelet 이 뜨지 않는다.[^kubeletfile]

1. **확장자는 반드시 `.conf`** 여야 한다.
2. **`apiVersion` 과 `kind` 가 반드시 있어야 한다.** 부분 설정이어도 타입 메타데이터는 필수다.
3. 병합은 **파일명 사전순**이고, 뒤 파일이 앞 파일의 필드를 *교체* 한다.
   그래서 `10-` 이 `00-k3s-defaults.conf` 를 이긴다.

반영하려면 k3s 를 재시작해야 한다. 서버 노드는 `k3s.service`, 워커 노드는
`k3s-agent.service` 다.

```bash
sudo systemctl restart k3s-agent.service   # 워커
sudo systemctl restart k3s.service         # 서버
```

**재시작해도 파드는 죽지 않는다.** 두 유닛 다 `KillMode=process` 라 systemd 가 메인
프로세스만 종료하고 컨테이너는 남겨둔다. 실제로 재시작 전후 파드 age 가 그대로(2d6h 등)
유지되는 걸 확인했다.

```bash
$ systemctl show k3s-agent.service -p KillMode -p Restart
Restart=always
KillMode=process
```

## 검증은 파일이 아니라 kubelet 에게 묻는다

드롭인을 썼다고 적용된 게 아니다. 파일을 다시 `cat` 하는 건 검증이 아니다.
kubelet 이 **실제로 병합해서 들고 있는 값**을 봐야 한다. kubelet 은 `/configz` 로 이걸 노출한다.

```bash
kubectl get --raw /api/v1/nodes/<노드>/proxy/configz \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["kubeletconfig"]["crashLoopBackOff"])'
```

적용 전후, 그리고 적용하지 않은 대조군 노드까지 같이 찍으면 이렇게 나온다.

```
ilwon    {'maxContainerRestartPeriod': '30s'}     ← 적용
louise   {'maxContainerRestartPeriod': '30s'}     ← 적용
lemuel   {'maxContainerRestartPeriod': '5m0s'}    ← 미적용(대조군)
solomon  {'maxContainerRestartPeriod': '5m0s'}    ← 미적용(대조군)
david    {'maxContainerRestartPeriod': '5m0s'}    ← 미적용(대조군)
```

대조군을 남긴 건 의도적이다. 이 설정은 파드 단위가 아니라 **노드 단위**라서, 그 노드의
*모든* 컨테이너에 적용된다. 한 번에 전체 노드에 바르는 대신 문제 워크로드가 있는 두 대만
먼저 바꾸고 나머지는 그대로 뒀다. 며칠 관찰한 뒤 넓히면 된다.

## 남은 한계 — 이건 근본 원인 수정이 아니다

정직하게 적어두는 편이 낫겠다.

- **원인은 그대로다.** 링크 불안정이 사라진 게 아니라 *복귀가 빨라진* 것뿐이다.
  operator 는 여전히 죽는다. 다만 최대 5분이 아니라 최대 30초 안에 돌아온다.
- **blast radius 가 파드보다 넓다.** 노드 단위 설정이라 그 노드의 멀쩡한 워크로드도
  같은 백오프 곡선을 쓴다. 백오프의 원래 목적이 "오작동하는 컨테이너가 kubelet 을 굶기지
  못하게" 하는 것이므로[^kep], 상한을 과하게 낮추면 그 보호가 약해진다. 1s 까지 낮출 수
  있지만 30s 로 잡은 이유다.
- **이 파일은 git 에 없다.** 노드 로컬 파일이라, k3s 를 재설치해 `/var/lib/rancher/k3s/agent/etc`
  가 초기화되면 **에러 없이 조용히** 300s 로 돌아간다. 노드 재구축 절차에 복원을 끼워 넣지
  않으면 몇 달 뒤 "왜 또 느리지" 로 돌아온다.

## 정리

세 번의 시도 중 두 번은 "고칠 수 있을 것 같다" 는 직감이었고, 확인해보니 둘 다 막혀 있었다.

| 시도 | 결과 | 막힌 이유 |
| --- | --- | --- |
| initContainer 로 대기 | 부분 실패 | 파드 생성 시 1회만 실행 — 컨테이너 재시작 경로를 못 막음 |
| 클라이언트 타임아웃 확대 | 불가 | 재시도 플래그 없음 + TLS 핸드셰이크 10초는 Go 상수 |
| 컨테이너 안에서 래핑 | 불가 | distroless 이미지 — 셸이 없음 |
| kubelet 백오프 상한 축소 | **성공** | 1.35 부터 beta 기본 활성, 드롭인 한 장 |

얻은 교훈은 기술 자체보다 순서 쪽에 가깝다. **"무엇이 실제로 아픈가" 를 먼저 정하지 않으면
고칠 수 없는 곳을 계속 두드리게 된다.** 이 건에서 아픈 건 프로세스가 죽는 사건이 아니라
죽어 있는 시간이었고, 그렇게 다시 정의하고 나서야 손댈 수 있는 레이어가 보였다.

그리고 하나 더 — **효과 범위를 과장하지 않는 것**. initContainer 를 넣고 "해결했다" 고
적었던 게 가장 비쌌다. 며칠 뒤 같은 에러를 다시 만나기 전까지 해결됐다고 믿고 있었으니까.

---

## References

[^init]: Kubernetes Documentation, *Init Containers*. <https://kubernetes.io/docs/concepts/workloads/pods/init-containers/>
[^apimachinery]: kubernetes/apimachinery, `pkg/util/net/http.go` — `SetOldTransportDefaults()`. <https://github.com/kubernetes/apimachinery/blob/master/pkg/util/net/http.go>
[^gotransport]: Go standard library, `net/http` — `DefaultTransport`. <https://pkg.go.dev/net/http#DefaultTransport> (소스: <https://github.com/golang/go/blob/master/src/net/http/transport.go>)
[^kep]: Kubernetes Enhancements, *KEP-5593: Configure the max CrashLoopBackOff delay* (원래 KEP-4603 "Tune CrashLoopBackoff" 의 일부에서 분리). <https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/5593-configure-the-max-crashloopbackoff-delay>
[^kubeletapi]: Kubernetes Documentation, *Kubelet Configuration (v1beta1)* — `CrashLoopBackOffConfig.maxContainerRestartPeriod` (최소 1초, 최대 300초, 미설정 시 내부 기본값 300초). <https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/>
[^gates]: Kubernetes Documentation, *Feature Gates* — `KubeletCrashLoopBackOffMax`. <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/>
[^kubeletfile]: Kubernetes Documentation, *Set Kubelet Parameters Via A Configuration File* — 드롭인 디렉터리 규칙(`.conf` 확장자, 타입 메타데이터 필수, 사전순 병합·replace 전략). <https://kubernetes.io/docs/tasks/administer-cluster/kubelet-config-file/>
[^k3s]: K3s Documentation, *Configuration Options — Kubelet Configuration Files*. <https://docs.k3s.io/installation/configuration>

*본문의 ECK 플래그 목록·distroless 확인·`configz` 출력·`KillMode` 값은 모두 해당 클러스터에서
직접 실행해 얻은 결과다. 노드 IP 등 내부 네트워크 정보는 제외했다.*
