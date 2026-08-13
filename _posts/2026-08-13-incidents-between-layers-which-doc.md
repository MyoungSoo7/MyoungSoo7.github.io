---
layout: post
title: "사고는 층과 층 사이에서 난다 — 홈랩 K3s 장애를 '어느 문서를 안 읽었나'로 분류했다"
date: 2026-08-13 20:30:00 +0900
categories: [kubernetes, ops]
tags:
  [k3s, kubernetes, storageclass, qos, servicemonitor, argocd, ufw, postmortem]
---

## 0. 질문을 정확히 세운다

6노드 K3s 클러스터를 굴리면서 사고를 여러 번 냈다. 어느 날 스스로에게 물었다.

> **"쿠버네티스를 처음부터 제대로 공부했으면 이 사고들은 안 났을까?"**

흔한 답은 두 가지다. "당연히 안 났지, 기본을 몰라서 그래" 또는 "아니, 실전은 책에 없어". 둘 다 위로는 되는데 다음에 뭘 읽어야 할지는 안 알려준다.

그래서 다르게 물었다. **사고마다 "이 한 줄을 미리 알았으면 안 났다"는 문서 한 줄을 실제로 찾아본다.** 찾히면 그 사고는 학습으로 막을 수 있었던 것이고, 못 찾으면 다른 종류다.

결론부터 쓴다. **거의 모든 사고에 대해 그 한 줄은 존재했다. 다만 내가 읽던 문서에 없었다.** 사고는 지식이 없어서가 아니라 **층과 층 사이**에서 났다.

> 이 글은 "무엇을 알아야 하는가" 목록이 아니다. 그건 이미 [쿠버네티스 관리자가 알아야 할 A to Z]({% post_url 2026-08-12-kubernetes-admin-a-to-z %})와 [인프라 관리자가 알아야 할 A to Z]({% post_url 2026-08-12-infra-admin-a-to-z %})에 썼다. 여기서는 **"알아도 왜 놓쳤는가, 그래서 어느 문서를 읽어야 하는가"**만 다룬다. 사례 일부는 두 글과 겹치지만 분류축이 다르다.

측정 환경: 노드 6대(lemuel·louise·david·ilwon·solomon·isagal), `v1.35.4+k3s1`, Ubuntu 24.04 LTS와 26.04 LTS 혼재. 아래 수치는 2026-08-13 실측이다.

---

## 1. 1층 — 코어 API: 개념 하나로 환원되는 사고

이 층의 사고는 공통점이 있다. **쿠버네티스 공식 문서의 한 문단이 정확히 그 사고를 설명한다.** 즉 순수하게 내 무지였다.

### 1.1 StorageClass 이름이 거짓말을 한 사건

`solomon-local`이라는 StorageClass가 있다. 이름만 보면 solomon 노드의 로컬 디스크를 쓰는 클래스다. 실제로 조회하면 이렇다.

```
NAME            PROVISIONER              RECLAIMPOLICY   DEFAULT
local-path      rancher.io/local-path    Delete          true
solomon-local   rancher.io/local-path    Retain          false
```

프로비저너가 기본 `local-path`와 **완전히 같다.** 그리고 이 클래스로 만들어진 PV 4개는 전부 solomon이 아니라 **ilwon**에 붙어 있다.

```
NAME                                       SC              RECLAIM   STATUS   NODE
pvc-35d50634-...   solomon-local   Retain   Bound   ilwon
pvc-4a63b444-...   solomon-local   Retain   Bound   ilwon
pvc-80a9726a-...   solomon-local   Retain   Bound   ilwon
pvc-a3af0aa3-...   solomon-local   Retain   Bound   ilwon
```

이름은 노드를 약속하는 것처럼 생겼지만, 노드를 정하는 건 이름이 아니라 프로비저너와 스케줄링이다. 이 클래스가 기본 클래스와 갖는 **유일한 실질 차이는 `reclaimPolicy: Retain` 하나**다.

그리고 그 하나가 정확히 사고의 내용이었다. PVC를 지웠는데 디스크가 안 비었다. 쿠버네티스 공식 문서는 이걸 이렇게 못 박아 둔다.

> "The `Retain` reclaim policy allows for manual reclamation of the resource. When the PersistentVolumeClaim is deleted, the PersistentVolume still exists and the volume is considered 'released'. But it is not yet available for another claim because **the previous claimant's data remains on the volume.**"
>
> — [Kubernetes 공식 문서, Persistent Volumes / Reclaiming](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

같은 페이지에 왜 기본 클래스는 안 그런지도 있다.

> "Volumes that were dynamically provisioned inherit the reclaim policy of their StorageClass, **which defaults to `Delete`.**"

**한 줄 요약:** 이 사고를 막는 문서는 쿠버네티스 공식 문서 한 페이지 안에 통째로 있었다. 1층 사고다.

### 1.2 데몬셋 파드가 44번 죽은 사건

Velero의 `node-agent` DaemonSet이 ilwon 노드에서 반복적으로 `OOMKilled` 됐다. 당시 기록으로 44회. 원인은 메모리 limit이 512Mi였고 백업 시 실제 사용량이 그걸 넘었다.

여기서 흔한 오해가 하나 있다. "노드에 메모리 여유가 있었는데 왜 죽었나?" 공식 문서는 QoS 클래스와 **무관하게** 적용되는 동작으로 이걸 분리해서 설명한다.

> "Any Container **exceeding a resource limit will be killed and restarted by the kubelet** without affecting other Containers in that Pod."
>
> — [Kubernetes 공식 문서, Pod Quality of Service Classes / Some behavior is independent of QoS class](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/)

즉 **노드 여유와 상관없다.** limit은 노드 압박 시의 우선순위가 아니라 컨테이너 개인의 천장이다. 노드 압박에 따른 축출(eviction)은 그와 별개로 QoS 순서(`BestEffort` → `Burstable` → `Guaranteed`)를 따른다. 두 메커니즘을 하나로 뭉쳐 이해하고 있었던 게 원인이었다.

고친 뒤 현재 상태:

```
{"limits":{"cpu":"500m","memory":"2Gi"},"requests":{"cpu":"100m","memory":"512Mi"}}

POD                NODE      QOS         RESTARTS
node-agent-8fs9h   ilwon     Burstable   0
node-agent-9dp89   isagal    Burstable   0
node-agent-bk8fw   louise    Burstable   0
node-agent-jcszr   david     Burstable   0
node-agent-nv7xl   lemuel    Burstable   0
node-agent-q5zxh   solomon   Burstable   0
```

6개 전부 재시작 0. 그리고 requests ≠ limits이므로 QoS는 `Burstable`이다. 이건 의도한 선택이다. 노드 압박 시 `Guaranteed`보다 먼저 축출되는 대신, 평소엔 여유 메모리를 빌려 쓴다. 백업 에이전트에는 그게 맞다.

**한 줄 요약:** 이것도 공식 문서 한 페이지다. 1층 사고다.

### 1.3 75일 동안 아무것도 안 걷힌 사건

ServiceMonitor를 만들어 뒀는데 Prometheus가 그 타겟을 75일간 한 번도 긁지 않았다. 대시보드는 조용했다. 에러도 없었다. **셀렉터가 안 맞으면 아무 일도 안 일어나기 때문이다.**

Prometheus Operator의 배선은 셀렉터 **두 개**를 직렬로 통과해야 한다.

```
Prometheus ──serviceMonitorSelector──▶ ServiceMonitor ──spec.selector──▶ Service ──spec.selector──▶ Pod
```

공식 문서의 예제가 이 두 홉을 그대로 보여준다. ServiceMonitor는 Service를 라벨로 고르고,

> "we create a `ServiceMonitor` object that **selects all Service objects with the `app: example-app` label**"

Prometheus는 다시 ServiceMonitor를 라벨로 고른다.

> "the Prometheus object defines **which ServiceMonitors get selected with the `spec.serviceMonitorSelector` field**."
>
> — [Prometheus Operator 공식 문서, Getting Started](https://prometheus-operator.dev/docs/developer/getting-started/)

여기서 내가 놓친 결정적인 디테일: ServiceMonitor의 `spec.selector`가 고르는 것은 **Pod의 라벨이 아니라 Service의 `metadata.labels`**다. 나는 Service의 `spec.selector`(=Pod를 고르는 라벨)만 맞춰 두고 Service 자신의 라벨은 비워 뒀다. 파드는 정상, 서비스도 정상, 엔드포인트도 정상. 오직 수집만 0이었다.

참고로 이 클러스터의 2홉은 활짝 열려 있다.

```
monitoring/kps-prometheus: smSelector={}  nsSelector={}
```

빈 셀렉터는 전부 선택한다는 뜻이므로, 실패는 전적으로 1홉(Service 라벨)에서 났다. 현재 ServiceMonitor는 27개.

**한 줄 요약:** 코어 API는 아니지만 도구의 공식 문서 첫 페이지에 있다. 여전히 "읽으면 되는" 층이다.

---

## 2. 2층 — 배포판: 같은 쿠버네티스가 아니다

여기서부터 성격이 바뀐다. **쿠버네티스 공식 문서를 아무리 읽어도 안 나온다.**

### 2.1 지운 애드온이 부활한 사건

CoreDNS 애드온이 무한히 apply 실패를 반복했다. Traefik은 지웠는데 서버를 재기동하니 되살아나서, 죽어 있던 Ingress 6개가 한꺼번에 깨어났다.

이건 K3s 고유 동작이고, K3s 문서에는 한 문장으로 명시돼 있다.

> "Manifests for packaged components are managed by K3s, and should not be altered. **The files are re-written to disk whenever K3s is started, in order to ensure their integrity.**"
>
> — [K3s 공식 문서, Managing Packaged Components](https://docs.k3s.io/installation/packaged-components)

파일을 고쳐도 소용없다. 기동할 때마다 원본이 다시 깔린다. 그래서 K3s는 별도의 탈출구를 준다.

> "For any file under `/var/lib/rancher/k3s/server/manifests`, you can create a `.skip` file which will cause K3s to ignore the corresponding manifest. **The contents of the `.skip` file do not matter, only its existence is checked.**"

지금 서버 노드의 실제 디렉터리다.

```
$ sudo ls -la /var/lib/rancher/k3s/server/manifests/
-rw------- 1 root root 1914 Aug  8 06:50 ccm.yaml
-rw------- 1 root root 5065 Aug  8 06:50 coredns.yaml
-rw-r--r-- 1 root root    0 Aug  9 12:52 coredns.yaml.skip
-rw------- 1 root root 3236 Aug  8 06:50 local-storage.yaml
-rw------- 1 root root 1737 Aug  8 06:50 rolebindings.yaml
-rw------- 1 root root  927 Aug  8 06:50 runtimes.yaml
-rw-r--r-- 1 root root    0 Aug 11 15:30 traefik.yaml.skip
```

두 가지를 동시에 볼 수 있다.

1. `ccm.yaml`·`coredns.yaml`·`local-storage.yaml`·`rolebindings.yaml`·`runtimes.yaml`의 mtime이 **전부 `Aug 8 06:50`으로 같다.** 마지막 K3s 기동 시각에 통째로 다시 쓰인 흔적이다. 문서가 말한 그대로다.
2. 최종적으로 사고를 막은 것은 **0바이트짜리 파일 두 개**다. 내용이 없다. 존재만이 의미다.

몇 시간을 태운 사고의 해법이 `touch` 두 번이었다. 그리고 그 `touch`는 쿠버네티스 문서 어디에도 없다. **배포판 문서에만 있다.**

---

## 3. 3층 — OS: 쿠버네티스 문서가 끝나는 곳

### 3.1 재부팅 한 번에 파드끼리 말이 끊긴 사건

Ubuntu 노드를 재부팅했더니 파드 간 통신이 죽었다. 노드는 `Ready`, 파드는 `Running`, 서비스도 있다. 그런데 다른 노드의 파드에는 안 닿는다.

원인은 `ufw`였다. 재부팅하면서 활성화됐고, Flannel VXLAN 터널을 막았다. 해법은 `sudo ufw disable` 한 줄이다.

이건 사실 K3s 문서에 있다.

> "The nodes need to be able to reach other nodes over **UDP port 8472 when using the Flannel VXLAN backend**"
>
> — [K3s 공식 문서, Requirements / Networking](https://docs.k3s.io/installation/requirements)

같은 문서는 아예 방화벽을 끄라고 권고한다("It is recommended to turn off firewalld"). 인바운드 규칙 표에도 `UDP 8472 / All nodes → All nodes / Required only for Flannel VXLAN`이 박혀 있다.

**그런데 이 사고를 막으려면 문서 두 개가 동시에 필요했다.** K3s 문서는 "8472를 열어라"라고 말하고, Ubuntu/ufw 문서는 "ufw는 부팅 시 자동 활성화된다"라고 말한다. 각각은 맞다. **둘을 곱해야 나오는 결론 — "재부팅하면 클러스터 네트워크가 죽는다" — 은 어느 문서에도 없다.**

이게 이 글의 핵심이다. 층별 문서는 자기 층에서만 옳다.

현재 상태:

```
ilwon   $ sudo ufw status  → Status: inactive
solomon $ sudo ufw status  → Status: inactive
```

---

## 4. 4층 — 운영 도구: 내 손을 되돌리는 것들

### 4.1 고쳤는데 90초 뒤에 원상복구된 사건

`kubectl`로 값을 바꿨다. 확인했다. 맞게 바뀌었다. 잠시 뒤 다시 보면 원래대로 돌아가 있다. 몇 번이고.

Argo CD의 self-heal이다. 문서는 기본값과 켰을 때의 차이를 이렇게 구분한다.

> **기본:** "By default, changes that are made to the live cluster will not trigger automated sync."
>
> **`selfHeal: true`일 때:** "automatic sync when the live cluster's state deviates from the state defined in Git."
>
> — [Argo CD 공식 문서, Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)

`selfHeal`의 기본값은 `false`다. 즉 이 동작은 **내가 켠 것**이다. 그걸 켰다는 사실을 잊고 명령형 도구로 싸운 게 사고였다.

오늘 이 클러스터의 Cloudflare 터널 커넥터를 3개에서 1개로 줄일 때는 같은 실수를 안 했다. `kubectl scale`을 아예 쓰지 않고 git의 `replicaCount`를 고쳐 push했다.

```
NAME                 READY   DESIRED
cloudflared-louise   1       1
```

**선언적 시스템에서 명령형 수정은 버그가 아니라 되돌려지는 게 정상이다.** 이걸 알려주는 문서는 쿠버네티스가 아니라 Argo CD에 있다.

---

## 5. 그래서 층이란 무엇인가

표로 정리하면 이렇게 된다.

| 사고                      | 증상         | 답이 있던 문서                        | 층          |
| ------------------------- | ------------ | ------------------------------------- | ----------- |
| PVC 지워도 디스크가 안 빔 | 조용함       | Kubernetes / Persistent Volumes       | 코어        |
| node-agent 반복 OOMKilled | CrashLoop    | Kubernetes / Pod QoS                  | 코어        |
| 75일간 메트릭 0           | 조용함       | Prometheus Operator / Getting Started | 도구        |
| 지운 애드온 부활          | 재기동 후    | K3s / Packaged Components             | 배포판      |
| 재부팅 후 파드 통신 두절  | 노드는 Ready | K3s Requirements **×** ufw 동작       | OS **경계** |
| kubectl 수정이 되돌아감   | 90초 뒤      | Argo CD / Automated Sync              | 도구        |

층을 $L = \{\text{core},\ \text{distro},\ \text{OS},\ \text{ops}\}$ 라 두고, 각 층의 문서 집합을 $D_i$ 라 하자. 내가 읽는 것은 합집합이다.

$$\text{내가 읽은 것} \;=\; \bigcup_{i} D_i$$

그런데 사고는 층 안이 아니라 층의 **경계** $B_{ij}$ 에서도 난다.

$$\text{사고 지점} \;\in\; \Big(\bigcup_i L_i\Big) \;\cup\; \Big(\bigcup_{i \neq j} B_{ij}\Big)$$

층이 $n$ 개면 경계는 $\binom{n}{2}$ 개다. **층은 선형으로 늘고 경계는 제곱으로 는다.**

$$n = 4 \;\Longrightarrow\; \binom{4}{2} = 6$$

층 4개를 전부 완독해도 경계 6개는 여전히 어느 책에도 없다. 위 표에서 실제로 제일 오래 헤맨 사고가 유일한 경계 사고(ufw × VXLAN)였던 것은 우연이 아니라고 본다.

> 위 표기는 내가 사고를 분류하려고 쓴 것이지 인용한 모델이 아니다. 엄밀한 정의가 아니라 "경계 수가 층 수보다 빨리 는다"는 관찰을 적은 것이다.

---

## 6. 그래서 어떻게 공부하는가 — 다섯 줄

1. **층을 먼저 그리고 문서를 층에 배정한다.** 코어(kubernetes.io), 배포판(docs.k3s.io), OS(배포판 릴리스 노트·systemd·방화벽), 운영 도구(Argo CD·Prometheus Operator·Velero). 각 층의 "공식 문서 첫 페이지"만이라도 북마크해 둔다.
2. **사고를 겪으면 "어느 층의 문서를 안 읽었나"로 분류한다.** 그게 다음에 읽을 문서를 정해 준다. "다음엔 조심하자"는 정보량이 0이다.
3. **코어 층은 커리큘럼으로 산다.** 1장의 세 사고는 전부 교과적 개념이고, 순서대로 배울 때 제일 싸게 배운다.
4. **배포판·OS 층은 커리큘럼으로 안 팔린다.** 여기는 "그 배포판의 문서를 처음부터 끝까지 한 번" 외에 지름길을 못 찾았다. K3s 문서는 다 읽어도 하루가 안 걸린다.
5. **경계는 문서로 못 메운다. 런북으로 메운다.** "재부팅 후 확인할 것" 같은 체크리스트만이 경계 사고를 잡는다. 그 체크리스트는 사고를 겪은 사람만 쓸 수 있고, 그래서 포스트모템이 자산이다.

---

## 7. 이 글의 한계

- 사고 표본이 홈랩 6노드 하나다. 매니지드 쿠버네티스(EKS/GKE)에서는 배포판·OS 층 상당 부분을 벤더가 가져가므로 층 구성이 달라진다.
- "44회"는 당시 내 기록이고, 지금 클러스터에서 재확인할 수 있는 값이 아니다(고친 뒤 재시작은 0이다). 나머지 수치와 명령 출력은 2026-08-13 실측이다.
- 층 4개는 내가 나눈 것이지 표준 분류가 아니다. 하드웨어·네트워크 장비를 별도 층으로 두면 경계는 더 는다.
- "학습으로 막을 수 있었다"는 사후 판단이다. 사고 전에 그 페이지를 읽었어도 그 한 줄을 기억했을지는 증명할 수 없다.

---

## 8. 한 줄

**문서가 없어서 사고가 나는 게 아니다. 어느 문서를 읽어야 하는지 몰라서 난다. 그리고 제일 비싼 사고는 어느 문서에도 없는 층과 층 사이에서 난다.**

---

## References

1. Kubernetes, _Persistent Volumes_ — Reclaiming(Retain/Delete), 동적 프로비저닝의 기본 reclaim policy. <https://kubernetes.io/docs/concepts/storage/persistent-volumes/>
2. Kubernetes, _Pod Quality of Service Classes_ — Guaranteed/Burstable/BestEffort 기준과 "QoS와 무관한 동작"(limit 초과 시 kubelet이 죽이고 재시작). <https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/>
3. K3s, _Managing Packaged Components_ — 패키지 매니페스트는 기동 시마다 디스크에 재작성되며 `.skip` 파일은 존재만 검사된다. <https://docs.k3s.io/installation/packaged-components>
4. K3s, _Requirements_ — Flannel VXLAN용 UDP 8472, 인바운드 규칙 표, 방화벽 비활성 권고. <https://docs.k3s.io/installation/requirements>
5. Prometheus Operator, _Getting Started_ — ServiceMonitor가 Service를 라벨로 고르고 Prometheus가 `serviceMonitorSelector`로 ServiceMonitor를 고르는 2홉 구조. <https://prometheus-operator.dev/docs/developer/getting-started/>
6. Argo CD, _Automated Sync Policy_ — 기본은 라이브 변경으로 sync를 트리거하지 않으며, `selfHeal: true`가 git 이탈을 되돌린다. <https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/>

관련 글: [쿠버네티스 관리자가 알아야 할 A to Z — 조용히 실패하는 것들]({% post_url 2026-08-12-kubernetes-admin-a-to-z %}) · [인프라 관리자가 알아야 할 A to Z — 6노드 클러스터가 나를 가르친 방식]({% post_url 2026-08-12-infra-admin-a-to-z %})
