---
layout: post
title: "쿠버네티스 도입 전/후 표에 없는 열 — 6노드 클러스터로 오른쪽 칸의 청구서를 받아 봤다"
date: 2026-08-18 23:20:00 +0900
categories: [engineering, kubernetes]
tags: [kubernetes, k3s, self-healing, hpa, argocd, gitops, sre, homelab]
---

이런 표를 자주 봅니다.

![쿠버네티스 도입 전/후 비교 — 관리 단위·설정 방식·장애 복구·트래픽 확장·배포 방식](/assets/images/k8s-before-after-table.jpg)

다섯 줄 다 맞는 말입니다. 저는 반박하려고 이 글을 쓰는 게 아닙니다. 집에서 6노드 K3s 클러스터를 직접 굴리고 있으니, **오른쪽 칸이 실제로 어떻게 청구되는지**를 제 클러스터 숫자로 한 줄씩 대 보려고 합니다.

결론부터 쓰면 — 표의 오른쪽 칸은 사실이지만, 각 칸에는 표에 안 적힌 **대가 열**이 하나씩 붙습니다. 그리고 그 대가는 대체로 **대시보드가 초록인 채로** 청구됩니다.

아래 수치는 전부 2026-08-18 기준 제 클러스터에서 직접 조회한 값입니다.

---

## 1. 관리 단위 — "개별 서버"에서 "파드"로. 다만 물리는 샙니다

맞습니다. 저는 평소에 노드를 개별로 다루지 않습니다. 파드 302개가 어느 기계에 앉는지는 대체로 신경 쓰지 않습니다.

그런데 추상화는 **아래쪽으로 샙니다.** 언젠가 한 노드에 뜬 파드만 DB 커넥션 풀이 마르는 일이 있었습니다. 애플리케이션 코드를 한참 뒤졌는데, 범인은 그 노드에 랜선과 WiFi 동글이 같은 주소로 동시에 붙어 있던 것이었습니다. 인바운드가 느린 쪽으로 흘렀고, 동글을 뽑으니 응답이 43.5ms 에서 0.23ms 가 됐습니다. 쿠버네티스는 그 노드를 끝까지 `Ready` 로 보고했습니다. 파드도 `Running` 이었고요.

그리고 "클러스터 전체"라는 관리 단위가 곧 고가용성은 아닙니다. 제 클러스터의 Deployment 88개 중 **84개가 `replicas: 1`** 입니다.

$$\frac{84}{88} = 95.5\%$$

즉 파드 하나가 죽으면 재스케줄되는 동안 그 서비스는 그냥 없습니다. 쿠버네티스가 준 건 "무중단"이 아니라 **"내가 안 깨워도 알아서 다시 뜬다"** 입니다. 이건 큰 차이인데, 표에는 그 차이가 안 보입니다.

## 2. 설정 방식 — 선언형은 "내 명령"이 아니라 "내 저장소"를 실행합니다

여기가 도입 후 가장 크게 바뀌는 지점이고, 동시에 가장 자주 물리는 지점입니다.

선언형이 되면 **내가 손으로 내린 명령이 오답 처리됩니다.** 저는 스케줄 잡 하나를 임시로 바꾸려고 `kubectl set env` 를 썼다가 90초 만에 ArgoCD 의 self-heal 에 원복당한 적이 있습니다. 잘못된 건 ArgoCD 가 아니라 저였습니다. 선언형 시스템에서 "지금 이 클러스터가 어때야 하는가"의 정본은 제 터미널이 아니라 git 이니까요.

두 번째로, **지운 것이 돌아옵니다.** K3s 는 번들 애드온을 매니페스트로 관리해서, 서버가 재기동될 때 그 매니페스트를 다시 적용합니다. 그래서 예전에 지웠던 Traefik 이 노드 재기동과 함께 되살아나 죽어 있던 Ingress 여섯 개가 한꺼번에 다시 붙은 일이 있었습니다. 삭제는 선언이 아니기 때문입니다. 선언형에서 "없음"을 표현하려면 **없다고 선언**해야 합니다.

세 번째, 파일을 고쳐도 소용없는 경우가 있습니다. CoreDNS 애드온 값이 충돌해 apply 가 무한 실패한 적이 있는데, 매니페스트를 고쳐도 기동 때마다 원본이 재생성됐습니다. 답은 파일 수정이 아니라 그 애드온을 **적용 대상에서 빼는 것**(`.skip`)이었습니다.

정리하면 선언형의 대가는 이겁니다 — **긴급 개입 경로가 좁아집니다.** 빠르게 손대는 능력을 내주고 재현성을 삽니다. 좋은 거래지만, 거래인 건 맞습니다.

## 3. 장애 복구 — 자가 치유는 고치는 게 아니라 다시 시작하는 겁니다

이 줄이 제일 오해가 큽니다. 쿠버네티스 공식 문서의 자가 치유 정의는 이렇습니다.

> Kubernetes restarts containers that fail, replaces containers, kills containers that don't respond to your user-defined health check, and doesn't advertise them to clients until they are ready to serve.[^k8s-overview]

문장에 "고친다"는 말이 없습니다. **재시작하고, 교체하고, 죽이고, 준비될 때까지 트래픽을 안 준다** — 전부 증상에 대한 조치입니다. 원인은 그대로 남습니다.

그래서 자가 치유는 원인을 **은폐**할 수 있습니다. 지금 제 클러스터에서 재시작 횟수 상위를 뽑으면 이렇습니다.

| 파드                       | 재시작 |
| -------------------------- | ------ |
| `sops-operator`            | 65     |
| `elastic-operator`         | 64     |
| `strimzi-cluster-operator` | 18     |
| `grafana`                  | 15     |
| `kube-state-metrics`       | 14     |

전부 지금 `Running` 이고 대시보드는 초록입니다. 이 글을 쓰는 오늘도 두 번 늘었습니다. 앞의 두 파드는 **서로 다른 노드**에 있는데 같은 분(12:08 UTC)에 죽었습니다. 클러스터 전체 사건이라는 뜻입니다. 전 컨테이너 로그를 보면 원인이 그대로 적혀 있습니다.

```
E0818 12:07:56 leaderelection.go:445] "Failed to update lease optimistically,
  falling back to slow path" err="Put https://10.43.0.1:443/apis/coordination.k8s.io/v1/.../leases/...
  ?timeout=5s: context deadline exceeded"
E0818 12:08:01 leaderelection.go:452] "Error retrieving lease lock" err="... context deadline exceeded"
I0818 12:08:01 leaderelection.go:299] "Failed to renew lease" err="context deadline exceeded"
{"level":"error","logger":"setup","msg":"problem running manager","error":"leader election lost"}
```

쿠버네티스는 컴포넌트 리더 선출을 `coordination.k8s.io` 의 Lease 로 합니다.[^k8s-lease] 오퍼레이터는 5초 안에 자기 리스를 갱신해야 리더 자격을 유지하는데, API 서버 응답이 그 안에 안 오면 **스스로 종료**합니다. 그러면 쿠버네티스가 다시 띄웁니다. 그게 65번 쌓인 겁니다.

여기서 중요한 건, 재시작된 건 오퍼레이터인데 **아픈 건 컨트롤 플레인**이라는 점입니다. 자가 치유는 아픈 곳이 아니라 그 옆을 고쳤습니다. 그리고 아무것도 빨개지지 않았기 때문에, 재시작 카운터를 일부러 세어 보기 전까지는 알 수 없습니다.

비슷한 경험이 하나 더 있습니다. 백업 에이전트가 **44회 연속 OOMKilled** 된 적이 있는데, 자가 치유가 44번 성실하게 다시 띄우는 동안 그건 "장애"가 아니라 "정상 운영"처럼 보였습니다. 메모리 한도와 병렬도 두 줄을 고치니 0이 됐습니다.

그래서 도입 후에 실제로 필요한 건 재시작이 아니라 **재시작 횟수를 보는 눈**입니다. 저는 이걸 알람으로 걸어 두지 않았던 게 아직도 부끄럽습니다.

## 4. 트래픽 확장 — HPA 는 파드를 늘릴 뿐, 노드는 제가 사서 꽂아야 합니다

HPA 는 실제로 잘 동작합니다. 다만 제 클러스터에서 HPA 가 붙은 Deployment 는 88개 중 **2개**입니다. 둘 다 `min 3 / max 6` 인데 현재 CPU 사용률은 0~2%, 상태는 `ScalingLimited=TooFewReplicas` — 즉 **한 번도 위로 뻗은 적이 없습니다.**

이건 HPA 의 문제가 아니라 표의 프레이밍 문제입니다. 오른쪽 칸의 "자동 스케일아웃"은 **능력**이지 **상태**가 아닙니다. 붙여야 생기고, 부하가 와야 발동하고, 지표가 맞아야 의미가 있습니다. 공식 문서도 HPA 를 "부하에 맞춰 용량을 맞추는 것을 목표로 워크로드 리소스를 자동으로 갱신"한다고 정의합니다 — 수평 확장은 **파드를 더 배치하는 것**입니다.[^k8s-hpa]

그리고 집 클러스터에는 결정적인 제약이 하나 있습니다. **파드는 늘어나도 노드는 안 늘어납니다.** 클라우드였다면 노드 그룹이 따라 커지겠지만, 여기서 노드는 제가 사서 전원을 꽂아야 생기는 물건입니다. 실제로 저희 클러스터의 한 노드는 CPU 여유가 없어 스케줄링을 꺼 둔 상태로 운영 중입니다. HPA 를 아무리 넉넉하게 잡아도 그 위에 앉을 자리가 없으면 `Pending` 만 쌓입니다.

표의 왼쪽 칸("수동 인스턴스 추가")이 사라진 게 아닙니다. **위치가 바뀐 것**입니다. 파드 레벨에서 자동이 됐고, 노드 레벨에서는 여전히 사람이 삽니다.

## 5. 배포 방식 — "표준화된 무중단"은 옵션이지 기본값이 아닙니다

제 클러스터 Deployment 88개의 배포 전략을 세어 보면 이렇습니다.

| 전략               | 개수 |
| ------------------ | ---- |
| `RollingUpdate`    | 66   |
| `Recreate`         | 22   |
| 카나리 · 블루/그린 | 0    |

`RollingUpdate` 가 다수인 건 제가 잘해서가 아니라 **그게 기본값**이기 때문입니다. 공식 문서 그대로입니다 — `.spec.strategy.type` 은 `Recreate` 또는 `RollingUpdate` 이고 기본값이 `RollingUpdate` 입니다.[^k8s-strategy]

그리고 `Recreate` 22개는 의도적으로 **다운타임을 받아들인** 것들입니다. 문서는 이 전략을 이렇게 정의합니다 — "새 파드가 만들어지기 전에 기존 파드가 전부 죽는다".[^k8s-strategy] RWO 볼륨을 쓰거나 싱글턴이어야 하는 워크로드는 롤링이 불가능하니 이 선택이 맞습니다. 다만 **그 22개에는 무중단이 없습니다.**

여기에 앞의 사실을 겹치면 그림이 완성됩니다. 84개가 `replicas: 1` 이라고 했죠. `replicas: 1` 짜리 `RollingUpdate` 는 새 파드가 `Ready` 가 될 때까지 옛 파드를 유지할 수는 있지만, 그 서비스의 여유분은 여전히 0입니다. 노드 하나가 빠지면 그걸로 끝입니다.

카나리와 블루/그린은 0입니다. 쿠버네티스가 못 해서가 아니라 **제가 안 깔았기 때문**입니다. 표의 오른쪽 칸은 "이 도구를 쓰면 이렇게 된다"가 아니라 "이 도구 위에서 이걸 만들 수 있다"에 가깝습니다.

---

## 표를 다시 쓴다면

오른쪽 칸을 지우고 싶진 않습니다. 저 다섯 줄은 전부 제 일상이 됐고, 도입 전으로 돌아가고 싶지 않습니다. 다만 열을 하나 더 붙이고 싶습니다.

| 항목        | 도입 후                   | 새로 생기는 것                                   |
| ----------- | ------------------------- | ------------------------------------------------ |
| 관리 단위   | 클러스터 · 파드           | 물리 계층의 문제가 파드 증상으로 위장해서 옵니다 |
| 설정 방식   | 선언형                    | 긴급 개입 경로가 좁아지고, 지운 것이 돌아옵니다  |
| 장애 복구   | 자가 치유                 | 원인이 재시작에 덮여 조용해집니다                |
| 트래픽 확장 | HPA                       | 파드는 자동, 노드는 여전히 수동입니다            |
| 배포 방식   | 롤링 · 카나리 · 블루/그린 | 기본값은 롤링 하나뿐이고 나머지는 직접 만듭니다  |

핵심은 이겁니다. **쿠버네티스를 도입하면 장애가 줄어드는 게 아니라 장애의 종류가 바뀝니다.** 도입 전에는 프로세스가 죽고 서버가 죽었습니다. 도입 후에는 리스가 만료되고, 컨트롤 플레인이 느려지고, 오버레이 네트워크가 막히고, 선언이 내 손을 되돌립니다. 그리고 새로운 종류의 장애는 대부분 **파드가 `Running` 인 채로** 옵니다.

그래서 도입 후에 진짜로 필요한 건 표의 오른쪽 칸이 아니라, 그 칸이 조용히 실패할 때 빨개지는 무언가입니다. 재시작 횟수, 리스 갱신 실패, `Pending` 지속 시간, `Recreate` 워크로드의 다운타임 — 이런 것들이요. 저도 아직 다 못 걸었습니다. 이 글의 3번 항목이 그 증거입니다.

---

## References

**클러스터 실측** — 2026-08-18, 자체 K3s 6노드 클러스터에서 `kubectl` 로 직접 조회. Deployment 88개(`replicas:1` 84개), 파드 302개, HPA 2개, 배포 전략 `RollingUpdate` 66 / `Recreate` 22, 재시작 상위 5개, `leader election lost` 로그(12:08 UTC).

[^k8s-overview]: Kubernetes Documentation, _Overview_ — Self-healing. "Kubernetes restarts containers that fail, replaces containers, kills containers that don't respond to your user-defined health check, and doesn't advertise them to clients until they are ready to serve." <https://kubernetes.io/docs/concepts/overview/>

[^k8s-lease]: Kubernetes Documentation, _Leases_. "In Kubernetes, the lease concept is represented by Lease objects in the `coordination.k8s.io` API Group, which are used for system-critical capabilities such as node heartbeats and component-level leader election." <https://kubernetes.io/docs/concepts/architecture/leases/>

[^k8s-hpa]: Kubernetes Documentation, _Horizontal Pod Autoscaling_. "a HorizontalPodAutoscaler automatically updates a workload resource (such as a Deployment or StatefulSet), with the aim of automatically scaling capacity to match demand. Horizontal scaling means that the response to increased load is to deploy more Pods." <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/>

[^k8s-strategy]: Kubernetes Documentation, _Deployments — Strategy_. "`.spec.strategy.type` can be \"Recreate\" or \"RollingUpdate\". \"RollingUpdate\" is the default value." · "All existing Pods are killed before new ones are created when `.spec.strategy.type==Recreate`." <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
