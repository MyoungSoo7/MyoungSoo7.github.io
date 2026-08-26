---
layout: post
title: "멘토에게 묻고 싶은 여섯 가지 — 2년 굴린 GitOps 리포에서 뽑아낸 것"
date: 2026-08-27 03:23:19 +0900
categories: [engineering]
tags: [gitops, argocd, kubernetes, k3s, homelab, sops, mentoring]
---

쿠버네티스 강사님께 멘토링을 받을 기회가 생겼다. 준비하면서 GitOps 리포를 통째로 보여드릴까 했는데,
그 리포에는 노드 IP 표와 "어느 엔드포인트에 인증이 걸려 있고 어느 쪽이 무보호인지" 같은 문서가 섞여 있다.
남에게 보여주기 부끄러운 게 아니라 **인터넷에 두면 안 되는 것들**이다. 그래서 리포 대신,
거기서 뽑아낸 **질문**만 정리하기로 했다.

질문을 고르는 기준을 하나 뒀다. "이건 어떻게 하나요" 는 검색하면 나온다.
**이미 굴러가고 있는데, 이대로 두는 게 맞는지 확신이 없는 것** 만 골랐다.
그래서 각 항목은 (1) 지금 상태를 **센 수치**로, (2) 무엇이 걸리는지, (3) 실제로 묻고 싶은 것 순서다.

측정 대상은 ArgoCD app-of-apps 로 굴리는 K3s 홈랩 하나다.
Application 48개, Helm 차트 37개, 커밋 563개.

---

## 1. Synced 초록불은 git 이 참이라는 뜻이 아니었다

**측정.** 이미지 태그 자동 갱신에 Argo CD Image Updater 를 쓴다.
write-back 방식이 두 가지로 갈려 있다 — `git` 7개, `argocd` 5개.

`argocd` 방식은 공식 문서가 이렇게 설명한다.

> The `argocd` write-back method directly modifies the Argo CD `Application` resource in the cluster,
> updating the application's source parameters (similar to what `argocd app set --parameter ...` would do).
> … **This method is pseudo-persistent.**[^1]

즉 지금 도는 이미지 태그가 **git 이 아니라 etcd 의 Application 오브젝트에만** 적힌다.
게다가 그 Application 을 app-of-apps 가 Server-Side Apply 로 관리하면 필드 소유자가 달라
**diff 에도 안 잡힌다.** git 과 실물이 다른데 화면은 Synced 초록불이었다.

한 번 데였다. 어떤 앱의 사이드카 이미지 태그가 `helm.parameters` 에 박혀 있었는데,
helm parameter 는 `--set` 과 같아서 `values.yaml` 을 무조건 이긴다.
image-list 에서 그 컴포넌트를 빼도 **이미 써둔 파라미터는 지워지지 않는다.**
그래서 `values.yaml` 은 한 달 넘게 그 컴포넌트를 한 번도 통제하지 못하고 있었고,
git 만 보고 있던 나는 그걸 몰랐다.

**묻고 싶은 것.** 두 write-back 방식을 실무에서는 어떤 기준으로 나눠 쓰나.
`git` 으로 통일하는 게 정답이라면, 이미지 태그 커밋이 리포 히스토리를 도배하는 건 감수하는 건가.
아니면 태그는 애초에 GitOps 리포의 관심사가 아니라고 보고 다르게 접근하나.

## 2. `prune: false` 41개 — 기본값을 그냥 쓰고 있는 게 맞나

**측정.** 48개 Application 전부 `automated` 동기화. `selfHeal: true` 44개.
그런데 `prune: true` 는 **7개뿐**이다. 41개는 prune 이 꺼져 있다.

이게 실수는 아니다. Argo CD 문서의 명시적 기본값이다.

> By default (and as a safety mechanism), automated sync will not delete resources
> when Argo CD detects the resource is no longer defined in Git.[^2]

문제는 결과다. **git 에서 지운 리소스가 클러스터에 그대로 남는다.**
서비스 하나를 폐기했을 때 실제로 겪었다. Application 파일을 지우고 push 했는데
네임스페이스와 그 안의 리소스가 살아 있었다. Application 에 finalizer 도 없어서
자식 리소스 cascade 삭제도 안 됐고, 결국 손으로 지웠다.
(지금 finalizer 를 단 Application 은 48개 중 5개다.)

"git 이 클러스터의 유일한 진실" 이라고 말하면서 삭제 방향으로는 그게 성립하지 않는 상태다.

**묻고 싶은 것.** prune 을 켜는 안전한 순서가 있나.
전부 켜고 `allowEmpty: false` 로 사고를 막는 쪽인지,
아니면 상태 없는 앱만 켜고 데이터 있는 앱은 영원히 수동으로 두는 게 실무 관행인지.
finalizer 를 5개에만 단 지금 상태는 일관성이 없는 건지, 아니면 원래 선별해서 다는 건지.

## 3. StorageClass 8종이 전부 노드 로컬이다

**측정.** 차트에서 참조하는 StorageClass 를 세어 보니 `local-path` 18회에,
나머지도 전부 `*-local` 계열이다. **분산·복제 스토리지가 하나도 없다.**
그 결과 37개 차트 중 27개가 `nodeSelector` 나 `nodeAffinity` 로 특정 노드에 묶여 있다.

쿠버네티스 문서는 이 조합의 위험을 이렇게 적는다.

> For storage backends that are topology-constrained and not globally accessible from all Nodes
> in the cluster, PersistentVolumes will be bound or provisioned without knowledge of
> the Pod's scheduling requirements. **This may result in unschedulable Pods.**[^3]

실제로 그렇다. PV 가 노드에 묶여 있으면 그 노드를 정비하려고 drain 하는 순간
워크로드가 **Pending 에서 영구히 멈춘다.** taint 문제가 아니라 PV 의 node affinity 라서
다른 노드로 갈 수가 없다. 스케줄러를 쓰는 게 아니라 사실상 손으로 배치하고 있는 셈이다.

더 걸리는 건 백업이다. 백업 결과물을 담는 PVC 들이 **한 노드의 로컬 디스크에 몰려 있으면**
그 노드가 죽는 순간 원본과 백업이 같이 사라진다. 이건 별도 오브젝트 스토리지로 빼서 해결했지만,
"로컬 스토리지 위에서 재해 복구를 말할 수 있나" 라는 질문은 그대로 남았다.

**묻고 싶은 것.** 6노드짜리 홈랩에서 Longhorn/Ceph 같은 분산 스토리지가 값어치를 하나.
운영 복잡도와 성능 대가를 생각하면 "로컬 + 오프사이트 백업" 이 오히려 정직한 선택인지.
현업에서는 이 규모에서 어디에 선을 긋는지 듣고 싶다.

## 4. 외부 노출 경계가 GitOps 밖에 있다

**측정.** 외부 노출은 Cloudflare Tunnel 로 한다. 그런데 이건 *remotely-managed tunnel* 이라
hostname → 백엔드 매핑 규칙이 **전부 대시보드에 저장**된다.[^4]
커넥터는 토큰만 들고 부팅해서 규칙을 받아온다 — 로컬에 `config.yml` 이 없다.

그래서 리포에는 이 라우팅에 해당하는 매니페스트가 **한 줄도 없다.**
리포에 있는 건 "지금 이렇게 돼 있더라" 를 손으로 적어둔 스냅샷 문서뿐이고,
그 문서에도 이렇게 적혀 있다 — *계정에 접근 못 하면 라우팅 규칙을 복원할 방법이 없다.*

인프라의 나머지 전부를 git 으로 재현할 수 있는데, **트래픽이 들어오는 문 하나만** 재현이 안 된다.
가장 바깥이고 가장 중요한 층이 하필 GitOps 밖이다.

**묻고 싶은 것.** 이 경계를 git 안으로 들이는 실무 방법이 무엇인가.
locally-managed 터널로 바꿔서 `config.yml` 을 커밋하는 쪽인지,
Terraform 같은 IaC 로 Cloudflare 리소스를 선언하는 쪽인지,
아니면 Gateway API 로 옮겨서 아예 클러스터 안으로 끌고 들어오는 게 맞는지.

## 5. SOPS age 수신자가 한 명이다

**측정.** 암호화된 secret 21개. 전부 SOPS[^6] + age 로 `data`/`stringData` 값만 암호화한다.
히스토리 563 커밋을 훑어도 평문 자격증명은 0건이고, 개인키가 커밋된 적도 없다.
`secrets/` 는 **첫 커밋부터** 암호화돼 있었다.

문제는 다른 데 있다. `.sops.yaml` 의 age 수신자가 **공개키 하나**다.
그 키를 잃으면 21개 secret 이 전부 영구 복호화 불가다.
리포에 백업 절차를 적어두긴 했는데, 1차 백업도 2차 백업도 **같은 노트북 안**이다.
장비 하나가 죽으면 백업 전략이 통째로 사라지는 구조다.

**묻고 싶은 것.** 1인 운영에서 age 수신자를 늘리는 게 의미가 있나
(어차피 키를 쥔 사람이 나 하나인데). 오프라인 백업 — 종이·YubiKey·별도 금고 — 중
실무에서 실제로 쓰는 건 무엇인지. 그리고 키 회전은 얼마나 자주,
어떤 계기에 하는 게 맞는지. 회전 절차를 문서로만 갖고 있고 **한 번도 실제로 돌려본 적이 없다.**

## 6. 컨트롤 플레인만 HA 다

**측정.** etcd 는 컨트롤 플레인 3대로 HA 를 구성했다. 그런데 그 위에 도는 앱은
StatefulSet 13개를 포함해 **사실상 전부 단일 복제본**이고,
PodDisruptionBudget 을 정의한 곳은 4군데뿐이다.

복제본이 1이면 PDB 는 의미가 없다.[^5] `minAvailable: 1` 을 걸면 그 파드는 **아무도 못 쫓아내고**,
`maxUnavailable: 1` 을 걸면 아무것도 안 막는다. 3번의 로컬 스토리지 제약과 겹쳐서,
복제본을 늘리고 싶어도 PV 가 노드에 묶여 있으니 늘릴 수가 없다.
결국 **컨트롤 플레인은 죽어도 되는데 앱은 죽으면 끝**인 이상한 모양이 됐다.

**묻고 싶은 것.** 홈랩 규모에서 HA 를 어디까지 추구하는 게 합리적인가.
컨트롤 플레인 HA 에 노드 3대를 쓰는 것과, 그 자원으로 앱 복제본을 늘리는 것 중
어느 쪽이 실제 가용성에 기여하는지. 애초에 이 구성에서 무중단이 목표가 될 수 있는 건지,
아니면 "빨리 복구" 로 목표를 바꾸는 게 맞는지.

---

## 정리하면서 알게 된 것

여섯 개를 늘어놓고 보니 셋(1·2·4)은 같은 말이었다.
**"git 이 클러스터의 진실" 이라는 문장이 어디까지 참인가.**
이미지 태그 방향으로 안 참이고, 삭제 방향으로 안 참이고, 외부 노출 경계에서는 아예 해당이 없다.
나머지 셋(3·5·6)도 하나로 묶인다 — **1인 홈랩에서 어디까지가 과잉인가.**

질문을 뽑는 작업 자체가 답의 절반이었다.
초록불을 믿고 있던 자리가 어디였는지는, 질문으로 바꿔 적기 전에는 잘 안 보였다.

## 이 글이 말하지 않은 것

노드 IP·호스트명 매핑, SSH 포트, NodePort 번호, 터널 식별자, 어느 도메인에 인증이
걸려 있는지 — 전부 뺐다. 홈랩 글에서 그런 걸 빼면 재미가 좀 없어지는데,
그게 정확히 인터넷에 두면 안 되는 것들이라 그렇다.
성능 수치도 없다. 이 글의 측정은 전부 **리포에 있는 파일을 센 결과**지 벤치마크가 아니다.

## References

[^1]: Argo CD Image Updater, *Update methods* — `argocd` write-back method. <https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/>
[^2]: Argo CD, *Automated Sync Policy* — Automatic Pruning. <https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/>
[^3]: Kubernetes Documentation, *Storage Classes* — Volume binding mode. <https://kubernetes.io/docs/concepts/storage/storage-classes/>
[^4]: Cloudflare Docs, *Create a tunnel (dashboard)* — remotely-managed tunnel. <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/>
[^5]: Kubernetes Documentation, *Specifying a Disruption Budget for your Application*. <https://kubernetes.io/docs/tasks/run-application/configure-pdb/>
[^6]: Mozilla SOPS. <https://github.com/getsops/sops>
