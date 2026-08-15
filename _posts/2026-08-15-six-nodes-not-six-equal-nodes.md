---
layout: post
title: "노드 6대인데 6대가 같지 않다 — 홈랩 K3s 클러스터를 열어보고 쓴 구조와 운영"
date: 2026-08-15 15:40:00 +0900
categories: [kubernetes, infra]
tags: [kubernetes, k3s, etcd, control-plane, taint, high-availability, leader-election, homelab, gitops]
---

"쿠버네티스 6노드를 운영한다"고 말할 때가 있다. 틀린 말은 아니다. `kubectl get nodes` 를 치면 여섯 줄이 나온다. 그런데 그 여섯 줄이 무엇을 보장하는지는 그 문장 안에 안 들어 있다.

이 글은 그 문장을 확인하려고 클러스터를 실제로 열어본 기록이다. 결론부터 쓰면 이렇다. **노드는 6대인데 이중화된 겹수는 역할마다 다르다. etcd 는 3겹, apiserver 는 2겹, 워커 에이전트의 페일오버 목록도 2겹이다.** 그리고 열흘 전에 고쳤다고 적어둔 문제가 오늘 새벽에 한 번 더 일어났다.

> **명령 출력에 대해.** 아래 붙인 출력은 전부 실제로 돌려서 받은 것이지만, 사설 IP 와 MAC 주소는 `<lemuel>` · `<ilwon>` · `<solomon>` 같은 노드 이름으로 바꿔 실었다. 어느 주소가 어느 노드인지가 이 글의 논지에 필요한 전부이고, 실제 주소값은 아무것도 더 설명해주지 않는다. 치환은 1:1 이라 각 줄의 의미는 원본 그대로다.

---

## 1. 쿠버네티스는 무엇을 쪼개 놓았나

먼저 구조를 짚고 간다. 쿠버네티스 공식 문서는 클러스터 컴포넌트를 **컨트롤 플레인**과 **노드**로 나눈다([Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/)).

- 컨트롤 플레인: `kube-apiserver`, `etcd`, `kube-scheduler`, `kube-controller-manager`, 그리고 선택 사항인 `cloud-controller-manager`
- 노드: `kubelet`, 컨테이너 런타임, 그리고 (문서상 선택 사항인) `kube-proxy`

여기서 중요한 건 **이 컴포넌트들이 서로 독립적으로 배치될 수 있다는 점**이다. "컨트롤 플레인 노드"는 관습적인 묶음이지 원자 단위가 아니다. 뒤에서 이 성질을 그대로 써먹게 된다.

내 클러스터는 K3s 다. K3s 문서는 첫 페이지에서 이렇게 말한다 — ["Operation of all Kubernetes control plane components is encapsulated in a single binary and process"](https://docs.k3s.io/). 별도 스태틱 파드 여러 개가 아니라 프로세스 하나다. 컨테이너 런타임(containerd)과 CNI(flannel)도 [패키징된 의존성](https://docs.k3s.io/) 목록에 들어 있다.

말로만 하면 안 믿기니 확인해봤다. 워커 노드에 flannel VXLAN 인터페이스는 멀쩡히 올라와 있는데,

```
flannel.1  UNKNOWN  <mac-redacted>  <BROADCAST,MULTICAST,UP,LOWER_UP>
```

flannel 파드는 클러스터 전체에 **0개**다. `kubectl get pods -A | grep -c flannel` 이 `0` 을 뱉는다. 데이터플레인은 도는데 그걸 담당하는 파드가 없는 이 그림이, K3s 가 무엇을 접어 넣었는지 한 줄로 보여준다. 다른 배포판을 쓰다 K3s 로 오면 "CNI 파드가 왜 없지?" 하고 한 번 당황하는 지점이기도 하다.

(정확히 하자면, "컨트롤 플레인이 단일 프로세스"까지는 문서에 명시돼 있고 "flannel 이 데몬셋이 아니라 에이전트 프로세스 안에서 뜬다"는 문서 문장이 아니라 위 실측과 K3s 소스 구조에서 나오는 서술이다. 문서에 없는 걸 문서에 있는 것처럼 쓰지 않으려고 나눠 적는다.)

## 2. 우리 6대의 실제 배치

`v1.35.4+k3s1`, containerd `2.2.3-k3s1`. 가장 오래된 노드(lemuel)가 116일째다. 실측 표다.

| 노드 | 역할 | CPU | MEM | Running 파드 | 테인트 |
|---|---|---|---|---|---|
| lemuel | control-plane + etcd | 4 | 31.2 GiB | 6 | `node-role.kubernetes.io/control-plane:NoSchedule` |
| ilwon | control-plane + etcd | 12 | 30.7 GiB | 34 | `dedicated=management:PreferNoSchedule` |
| solomon | control-plane + etcd | 4 | 15.0 GiB | 6 | `dedicated=storage:NoSchedule` |
| david | worker | 6 | 15.1 GiB | 34 | — |
| isagal | worker | 40 | 15.0 GiB | 32 | — |
| louise | worker | 8 | 15.5 GiB | 34 | — |

Running 파드 146개, 네임스페이스 46개.

컨트롤 플레인 3대의 **테인트가 셋 다 다르다.** 우연이 아니라 이 클러스터의 운영 이력이 그대로 굳은 자국이다. [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) 문서의 정의를 그대로 대입해보면 이렇게 읽힌다.

- `lemuel` 은 `NoSchedule`. 문서 표현으로 "매칭되는 톨러레이션이 없으면 새 파드가 스케줄되지 않는다." 실제로 6개만 도는데 그중 넷은 데몬셋이다.
- `solomon` 도 하드 배제인데 키가 `dedicated=storage` 다. 여기 붙은 워크로드는 ES 콜드 티어 하나뿐이다.
- `ilwon` 은 `PreferNoSchedule`. **소프트 배제다.** 문서는 이걸 "'preference' 또는 'soft' 버전"이라고 부르고, 스케줄러가 피하려 시도하지만 **보장하지는 않는다**고 못박는다. 그래서 컨트롤 플레인인데도 워커들과 똑같이 34개가 돈다.

`NoSchedule` 과 `PreferNoSchedule` 의 차이를 문서로 읽으면 한 줄이지만, 클러스터에서 보면 6 대 34다.

한 가지 덧붙이면 `node-role.kubernetes.io/control-plane:NoSchedule` 은 [쿠버네티스 레퍼런스](https://kubernetes.io/docs/reference/labels-annotations-taints/#node-role-kubernetes-io-control-plane-taint)상 **kubeadm 이 붙이는** 테인트다. K3s 는 서버 노드를 기본적으로 스케줄 가능 상태로 둔다. 즉 lemuel 의 저 테인트는 배포판이 준 게 아니라 누가 손으로 붙인 것이고, 실제로 이 노드용 자가치유 프로파일에는 "4코어로 과부하 이력 → 의도적 cordon 유지, 절대 uncordon 하지 않는다"가 같이 적혀 있다.

## 3. 세 번째 컨트롤 플레인은 apiserver 를 안 띄운다

여기가 이 글을 쓰게 만든 지점이다.

`solomon` 의 `/etc/rancher/k3s/config.yaml` 은 이렇게 끝난다.

```yaml
disable-apiserver: true
disable-controller-manager: true
disable-scheduler: true
```

etcd 멤버로는 그대로 남고 **API 서버만 안 띄우는 노드**다. K3s 는 이걸 정식으로 지원한다. [Managing Server Roles](https://docs.k3s.io/installation/server-roles) 문서는 "특정 컴포넌트를 비활성화해 control-plane 과 etcd 역할을 별도 노드로 분리하는 것이 가능하다"고 쓰고, etcd 전용 노드의 예시로 정확히 저 세 플래그를 든다. (임베디드 etcd 를 쓸 때만 해당하는 이야기이고, 플래그를 지우고 재시작하면 역할은 되돌아온다.)

그리고 그 위에 이유가 측정치까지 붙어 주석으로 남아 있었다(2026-08-05 자, 요약):

> apiserver 3대 중 solomon 만 lease PUT p99 2.21초 (ilwon 0.025초, lemuel 0.084초). 클라이언트가 3대에 분산되므로 1/3 확률로 느린 놈에 걸려 leader election lease 갱신이 타임아웃을 넘기고, controller-runtime 이 매니저를 종료시킨다 → 오퍼레이터 6종이 "leader election lost" 로 반복 재시작. 원인은 디스크(WAL fsync 0.669ms 로 셋 중 최우수)도 네트워크도 아닌 CPU.

즉 **느린 노드를 클러스터에서 빼는 대신, 그 노드가 맡던 역할 중 느려서 문제가 되는 역할만 뺐다.** etcd voter 는 3을 유지하고 싶었고, apiserver 풀에는 느린 놈이 섞이면 안 됐다. 1절에서 짚은 "컴포넌트는 독립적으로 배치될 수 있다"가 실전에서 쓰이는 방식이 이거다.

효과는 클러스터 안에서 그대로 관측된다. `default/kubernetes` 엔드포인트에 solomon이 없다.

```
$ kubectl get endpointslice -n default
kubernetes: <lemuel> <ilwon>
```

etcd 는 셋 다 살아 있다.

```
ilwon-f3f37c02    started  https://<ilwon>:2380
solomon-0012157a  started  https://<solomon>:2380
lemuel-64066392   started  https://<lemuel>:2380
```

**etcd 3겹, apiserver 2겹.** 이 클러스터의 실제 이중화 상태는 이 한 줄이고, "컨트롤 플레인 3대"라는 표현으론 절대 안 보인다.

etcd 쪽 숫자도 정직하게 적어두자. [etcd FAQ](https://etcd.io/docs/v3.5/faq/) 의 쿼럼 표대로 3멤버는 1대 실패까지 견딘다. 다만 쿠버네티스 문서는 프로덕션에는 [5멤버를 강하게 권한다](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/). 여기는 홈랩이라 3으로 간다 — 권고를 따른 게 아니라 안 따르기로 한 것이고, 그럼 "1대까지"라는 여유분도 그만큼이다.

## 4. 워커는 사실 어디에 붙어 있나

그러면 워커들은 어느 apiserver 에 붙나. 유닛 환경파일만 보면 하나를 가리킨다.

```
K3S_URL=https://<lemuel>:6443
```

여기서 멈추면 "단일 컨트롤 플레인에 물려 있네"로 오독하게 된다. 실제로는 그렇지 않다. [K3s 아키텍처 문서](https://docs.k3s.io/architecture)는 에이전트가 **클라이언트 사이드 로드밸런서**를 프로세스 내부에 띄우고, 거기서 서버 목록을 관리한다고 설명한다. 그리고 그 목록의 출처를 이렇게 명시한다.

> "the agent retrieves a list of kube-apiserver addresses from the Kubernetes service endpoint list in the default namespace"

이 한 문장이 3절과 정확히 맞물린다. 목록의 원천이 `default` 네임스페이스의 엔드포인트니까, apiserver 를 안 띄운 solomon 은 애초에 그 목록에 들어올 수가 없다.

실측도 그대로다. 로컬 LB 가 떠 있고(`--lb-server-port` 기본값이 [6444](https://docs.k3s.io/cli/agent)다), kubelet 의 kubeconfig 가 그쪽을 본다.

```
$ sudo ss -tlnp | grep 6444
LISTEN 127.0.0.1:6444  users:(("k3s-agent",pid=1361037))

$ grep server: /var/lib/rancher/k3s/agent/kubelet.kubeconfig
    server: https://127.0.0.1:6444
```

에이전트가 들고 있는 서버 목록도 파일로 남는다.

```json
{
  "ServerURL": "https://<lemuel>:6443",
  "ServerAddresses": ["<lemuel>:6443", "<ilwon>:6443"]
}
```

여섯 노드 전부 같은 목록이다. **정확히 2개.**

그래서 이 클러스터의 내구성은 이렇게 읽어야 한다. lemuel 이 죽으면 워커들은 ilwon 으로 넘어간다. **ilwon 까지 같이 죽으면, etcd 쿼럼이 살아 있어도 워커들이 붙을 apiserver 가 없다.** etcd 가 3겹이라는 사실이 apiserver 가 2겹이라는 사실을 가려주지 않는다.

두껍게 하려면 solomon 의 apiserver 를 되살리거나(그럼 느린 놈이 다시 섞인다), 별도의 고정 등록 주소를 앞에 두는 선택지가 있다. 지금은 안 했다. 안 한 것을 안 한 대로 적어둔다.

## 5. 고쳤다고 적어둔 것이 아직 안 고쳐졌다

이 글에서 제일 쓰기 싫었던 절이다.

8월 5일 주석은 오퍼레이터 재시작 횟수를 이렇게 남겼다. sops-operator 57회, elastic-operator 56회. 오늘 다시 셌다.

```
sops-operator     restarts=62   마지막종료=2026-08-15T04:46:45Z  reason=Error
elastic-operator  restarts=60   마지막종료=2026-08-14T04:49:32Z
```

**62회다.** 그리고 마지막 종료가 오늘 새벽이다. 이전 컨테이너 로그를 꺼내봤다.

```json
{"level":"error","ts":"2026-08-15T04:46:45.342Z","logger":"setup",
 "msg":"problem running manager","error":"leader election lost"}
```

같은 에러다. 열흘 동안 5회. 빈도는 줄었지만 **멎지는 않았다.**

이 `leader election lost` 문자열은 controller-runtime 이 리스 갱신에 실패했을 때 매니저의 `Start()` 가 돌려주는 에러 그대로다. 라이브러리 [기본값](https://github.com/kubernetes-sigs/controller-runtime/blob/main/pkg/manager/internal.go)은 LeaseDuration 15초, RenewDeadline 10초, RetryPeriod 2초이고, 이 상황에서는 graceful shutdown 을 건너뛴 뒤 호출자가 즉시 프로세스를 끝내도록 되어 있다. 로그에 `Stopping and waiting for ...` 줄들이 우르르 찍히고 파드가 재시작하는 그림이 정확히 그 경로다.

여기서 내 주석 하나를 정정한다. 저 8월 5일 메모는 "5초 타임아웃"이라고 적었는데 그건 controller-runtime 기본값 어디에도 없는 숫자다. 오퍼레이터가 값을 따로 덮었을 수도 있고 그냥 부정확하게 적힌 것일 수도 있는데, **확인 못 한 수치라 이 글에는 안 쓴다.** 근거로 남길 수 있는 건 라이브러리 기본값(15/10/2)과 실제 찍힌 에러 문자열까지다.

원인 하나를 제거해 지표가 좋아졌을 때 그걸 "해결"로 적으면 남은 원인이 안 보이게 된다. 지금 상태를 정확히 쓰면 **"가장 큰 기여자를 제거했고, 잔여 원인은 아직 특정하지 못했다"** 이다.

한 가지 더. 주석은 solomon 을 "2014 Mac Mini"라고 적었는데, 확인하니 아니었다.

```
Macmini5,1
Intel(R) Core(TM) i5-2415M CPU @ 2.30GHz
```

`Macmini5,1` 은 2011년 모델이고 i5-2415M 은 2코어 4스레드 샌디브릿지다. 쿠버네티스가 보고하는 `capacity.cpu: 4` 는 물리 코어 4개가 아니라 스레드 4개다. **2011년 2코어 위에서 etcd voter 가 돌고 있다**는 게 정확한 서술이고, apiserver 를 뺀 판단은 그래서 오히려 더 타당해 보인다. 다만 내가 남긴 기록조차 연식이 3년 틀려 있었다는 건 따로 적어둘 만하다.

## 6. 6대를 굴러가게 하는 나머지

구조 이야기만 하면 반쪽이라 운영 쪽도 적는다.

- **GitOps**: ArgoCD Application 59개, 현재 전부 `Synced/Healthy`. 46개 네임스페이스가 이걸로 관리된다.
- **백업**: Velero 로 4시간마다 핵심 백업(`hourly-critical`), 매일 03시 볼륨 포함 백업(`daily-with-volumes`). 파드 통계에서 `Succeeded` 149개가 잡히는데 대부분 이 백업 잡의 잔해다. Running 146 / Succeeded 149 를 합쳐 "파드 295개"라고 세면 안 되는 이유다.
- **DNS**: [NodeLocal DNSCache](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) 를 6대 전부에 데몬셋으로 깔았다. 문서 표현대로 "노드에서 DNS 캐싱 에이전트를 데몬셋으로 돌려 클러스터 DNS 성능을 개선"하는 부가기능이다. 여기 Corefile 에도 실측 근거 주석이 붙어 있다 — DNS 응답의 72~78% 가 NXDOMAIN 이라 denial 캐시 TTL 을 5초에서 30초로 올렸다는 기록. `ndots:5` 검색 경로 확장과, IPv4 전용 클러스터인데 AAAA 질의가 A 와 1:1 로 들어오는 게 원인이었다.
- **스토리지**: StorageClass 7종. 기본은 local-path 지만 ELK 티어(hot/warm/cold), SSD, NFS 를 따로 뒀다. PVC 46개.
- **자가치유**: 표준 라이브러리만 쓰는 파이썬 데몬셋이 노드마다 돌면서 방화벽·k3s 서비스·디스크·시각 동기화를 점검한다. 노드별 프로파일이 있고, 앞서 나온 lemuel 의 `never_uncordon: true` 가 거기 박혀 있다.

버전 이야기도 하나. 이 클러스터는 `v1.35.4` 인데 [쿠버네티스 릴리스 페이지](https://kubernetes.io/releases/) 기준 1.35 계열의 최신 패치는 1.35.6 이고 현재 최신 마이너는 1.36 이다. 즉 패치도 마이너도 뒤처져 있다. 이것도 "운영 중"이라는 말이 안 알려주는 항목이라 같이 적는다.

## 7. 정리

- **노드 수는 가용성 지표가 아니다.** 의미 있는 숫자는 "역할별로 몇 겹인가"다. 우리는 etcd 3, apiserver 2, 에이전트 페일오버 2다.
- **컨트롤 플레인은 원자 단위가 아니다.** 쿠버네티스가 컴포넌트를 쪼개 놨고 K3s 는 그걸 플래그로 노출한다. 느린 노드를 통째로 빼는 대신 문제 되는 역할만 뺄 수 있다.
- **`kubectl get nodes` 는 배치를 안 보여준다.** 테인트, 엔드포인트 목록, 에이전트 LB 파일까지 봐야 실제 그림이 나온다. 같은 `Ready` 여섯 줄 뒤에 6 대 34 가 숨어 있다.
- **지표가 좋아진 것과 문제가 끝난 것은 다르다.** 재시작이 줄어든 걸 "해결"로 적어두면 오늘 새벽에 또 일어난 한 번이 안 보인다.

이 글의 클러스터 수치는 전부 2026-08-15 에 이 클러스터에서 직접 뽑은 것이다. 남의 환경에 그대로 옮길 수 있는 값은 아니고 옮기라고 쓴 것도 아니다. 다만 "우리는 N노드를 운영한다"는 문장을 쓰기 전에 한 번 열어보라는 얘기는 하고 싶다. 나는 열어보고 세 군데 틀렸다 — 재시작은 안 멎었고, 하드웨어 연식은 3년 틀렸고, 타임아웃 수치는 근거가 없었다.

---

## References

- Kubernetes, [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/) — 컨트롤 플레인/노드 컴포넌트 구분, `cloud-controller-manager`·`kube-proxy` 의 선택적 성격
- Kubernetes, [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/) — `NoSchedule` / `PreferNoSchedule` / `NoExecute` 정의
- Kubernetes, [Well-Known Labels, Annotations and Taints — `node-role.kubernetes.io/control-plane`](https://kubernetes.io/docs/reference/labels-annotations-taints/#node-role-kubernetes-io-control-plane-taint) — 해당 테인트를 붙이는 주체가 kubeadm 이라는 점
- Kubernetes, [Operating etcd clusters for Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/) — etcd 가 모든 클러스터 데이터의 백업 저장소라는 점, 홀수 멤버 권고, 프로덕션 5멤버 권고
- etcd, [FAQ](https://etcd.io/docs/v3.5/faq/) — 쿼럼 `(n/2)+1`, 3멤버는 1대 실패 허용
- Kubernetes, [Using NodeLocal DNSCache in Kubernetes Clusters](https://kubernetes.io/docs/tasks/administer-cluster/nodelocaldns/) — 노드 로컬 DNS 캐싱 에이전트를 데몬셋으로 운영
- Kubernetes, [Releases](https://kubernetes.io/releases/) — 1.35 / 1.36 의 최신 패치 및 유지보수 대상 브랜치
- K3s, [Introduction](https://docs.k3s.io/) — 컨트롤 플레인 컴포넌트가 단일 바이너리·단일 프로세스에 캡슐화된다는 서술, 패키징된 containerd·Flannel
- K3s, [Managing Server Roles](https://docs.k3s.io/installation/server-roles) — `--disable-apiserver` / `--disable-controller-manager` / `--disable-scheduler` 로 etcd 전용 서버를 구성하는 공식 예시, 임베디드 etcd 한정, 역할 되돌리기
- K3s, [Architecture — Agent Load Balancer](https://docs.k3s.io/architecture) — 에이전트 내 클라이언트 사이드 로드밸런서, `default` 네임스페이스 엔드포인트에서 apiserver 주소 목록을 가져온다는 서술
- K3s, [`k3s agent` CLI](https://docs.k3s.io/cli/agent) — `--lb-server-port` 기본값 6444
- kubernetes-sigs/controller-runtime, [`pkg/manager/internal.go`](https://github.com/kubernetes-sigs/controller-runtime/blob/main/pkg/manager/internal.go) — 리더 선출 기본값(LeaseDuration 15s / RenewDeadline 10s / RetryPeriod 2s), 리스 상실 시 `leader election lost` 반환 및 graceful shutdown 생략

*클러스터에서 인용한 수치·로그·설정은 2026-08-15 에 직접 조회한 것이다. 성능 우열이나 일반적 권고로 읽을 만한 근거는 아니며, 특히 노드 한 대의 lease p99 비교는 이 하드웨어 조합에서의 단일 관측이라 재현 가능한 벤치마크가 아니다.*
