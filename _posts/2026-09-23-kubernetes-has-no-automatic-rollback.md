---
layout: post
title: "쿠버네티스에는 자동 롤백이 없다 — GitOps 커밋 와치독을 만든 이야기"
date: 2026-09-23 00:17:17 +0900
categories: [kubernetes, gitops]
tags: [argocd, gitops, self-heal, rollback, git-trailer, operator, sre, progressdeadlineseconds]
---

집에서 굴리는 K3s 클러스터에 ArgoCD로 80여 개 Application을 얹어 놓고 반년쯤 지나니
확신이 하나 생겼다. **자동 복구가 있다고 믿고 있었는데, 실제로 있는 건 절반뿐이었다.**

이 글은 그 나머지 절반 — "git에 잘못 커밋했을 때 누가 되돌리는가" — 를 채우려고
작은 와치독을 만들면서, 설계가 세 번 틀렸고 그때마다 무엇을 배웠는지에 대한 기록이다.

## 1. selfHeal은 git이 참일 때만 그물이다

ArgoCD의 `selfHeal`은 자주 "자동 복구"로 소개된다. 공식 문서의 정의는 더 좁다.

> By default, changes that are made to the live cluster will not trigger automated sync.
> To enable automatic sync when the live cluster's state deviates from the state defined in Git ...
> — [Argo CD, *Automated Sync Policy*][argo-autosync]

되돌리는 대상은 **"라이브 클러스터가 git에서 벗어난 것"** 이다. 누가 `kubectl edit`으로
레플리카를 건드리면 원복한다. 훌륭하다.

그런데 방향을 뒤집어 보자. **git 자체가 틀렸다면?** 그러면 selfHeal은 그 틀린 것을
*충실하게 강제한다*. 그물이 아니라 증폭기가 된다. 같은 문서에 이런 줄도 있다.

> Rollback cannot be performed against an application with automated sync enabled.
> — [Argo CD, *Automated Sync Policy*][argo-autosync]

자동 동기화를 켠 앱은 ArgoCD UI의 롤백 버튼조차 쓸 수 없다. 당연하다. 되돌려 놔 봐야
다음 리컨실에서 git이 다시 이긴다. **GitOps에서 롤백이란 곧 `git revert`다.**

## 2. 그럼 쿠버네티스가 되돌려 주지 않나

안 해준다. Deployment에는 `progressDeadlineSeconds`가 있어서 롤아웃이 막히면 실패로
표시되는데, 공식 API 레퍼런스의 설명은 이렇다.

> The maximum time in seconds for a deployment to make progress before it is considered to be
> failed. The deployment controller will continue to process failed deployments and a condition
> with a `ProgressDeadlineExceeded` reason will be surfaced in the deployment status. ...
> Defaults to 600s.
> — [Kubernetes API Reference, *DeploymentSpec*][k8s-deployment-api]

읽어야 할 문장은 "continue to process"다. **컨디션만 찍고, 계속 그 상태로 둔다.**
되돌리려면 사람이 `kubectl rollout undo`를 친다. 내 클러스터의 Deployment는 전부
이 기본값 600초를 쓰고 있었고, 즉 **데드라인을 넘겨도 아무 일도 일어나지 않는 상태**였다.

정리하면 구멍은 이렇게 생겼다.

| 무엇이 틀렸나 | 누가 되돌리나 |
| --- | --- |
| 라이브 클러스터가 git에서 벗어남 | ArgoCD `selfHeal` ✅ |
| 롤아웃이 진행되지 않음 | 아무도 안 함 (컨디션만) ❌ |
| **git에 커밋된 내용 자체가 나쁨** | **아무도 안 함** ❌ |

세 번째 칸을 메우는 게 목표다.

## 3. 설계 — 커밋이 스스로 감시를 신청한다

가장 먼저 정한 것은 **"모든 커밋을 감시하지 않는다"** 였다. 전수 감시는 오탐이 곧
운영 사고가 되고, 무엇보다 내가 그걸 신뢰하게 되기까지 시간이 걸린다.

그래서 옵트인으로 갔다. 커밋 메시지 끝에 [git trailer][git-trailers]를 박으면
그 커밋만 감시 대상이 된다.

```
nav: 되돌림 권한을 커밋 단위로 나눈다

...본문...

Nav-Watchdog: app=lemuel-xr-prod deadline=900 mode=shadow expect=Healthy
```

트레일러는 RFC 822 헤더를 닮은 `key: value` 줄로, `git interpret-trailers`로 파싱할 수
있는 git의 표준 관용구다. `Signed-off-by:`와 같은 자리다. 별도 메타데이터 파일도,
별도 DB도 필요 없다. **되돌릴 대상과 되돌릴 조건이 같은 객체에 붙어 있다**는 점이
이 선택의 전부다. 커밋을 체리픽하면 조건도 따라간다.

필드는 넷이다.

| 필드 | 뜻 |
| --- | --- |
| `app` | 감시할 ArgoCD Application 이름 (필수) |
| `deadline` | 도달 이후 이 안에 Healthy가 안 되면 실패 (기본 900초) |
| `mode` | `shadow` = 판정만 / `arm` = 실제로 되돌림 (기본 shadow) |
| `expect` | 기대 상태 (현재 `Healthy`만 지원) |

## 4. 판정은 셋으로 나눈다

처음엔 "배포했는데 Healthy인가" 하나로 봤다. 첫 시험에서 바로 깨졌다.
**도달과 건강은 다른 실패다.**

1. **도달** — 그 커밋이 Application의 동기화된 revision의 *조상*인가.
   즉 진짜로 배포됐나.
2. **건강** — Synced + Healthy + Degraded/Missing 리소스 0 + 진행 중인 작업 없음.
3. **안정** — 위 상태가 120초 유지. 롤아웃 도중 잠깐 초록인 순간에 속지 않기 위해서다.

셋 다 통과하면 `CONFIRMED`로 감시를 종료한다. 데드라인을 넘기면 `FAIL`이고,
`mode=arm`이면 그때 `git revert` 커밋을 만들어 push한다. 그 뒤는 ArgoCD가 알아서 한다.

도달을 따로 뺀 이유가 중요하다. **도달 실패는 절대 되돌리지 않는다.**
배포되지도 않은 커밋을 되돌려 봐야 장애는 그대로다. 그때 의심할 것은 커밋이 아니라
동기화 파이프라인이다. 이 구분을 안 했다면 와치독은 "ArgoCD가 느린 날" 마다
멀쩡한 커밋을 되돌렸을 것이다.

## 5. 안전장치는 기능보다 먼저 썼다

되돌림 권한을 가진 자동화는 잘못 작동할 때의 피해가 안 하는 것보다 크다.
그래서 장치를 여섯 개 걸었다.

- **기본이 `shadow`다.** 트레일러를 달았다는 것만으로 되돌리지 않는다.
  판정이 맞는지 한동안 보고 나서 앱별로 권한을 준다.
- **`arm`은 앱 단위가 아니라 커밋 단위다.** "이 앱을 믿는다"가 아니라
  "이 커밋을 되돌려도 된다"가 단위다. 한 발씩 갈 수 있다.
- **revert 커밋에는 트레일러를 박지 않는다.** 안 그러면 자기가 만든 revert를
  다시 감시하다가 되돌리는 무한 루프가 된다.
- **연속 2회 되돌리면 서킷이 열린다.** 더는 안 건드리고 사람을 부른다.
  두 번 연속 되돌렸다는 건 판정 쪽이 틀렸을 가능성이 크다는 뜻이다.
- **전역 차단기(`DRY_RUN`)** 가 있다. `mode`와 무관하게 전부 판정만 하게 만든다.
- **도달 실패는 되돌리지 않는다** (위에서 설명).

## 6. 실증 — 일부러 망가뜨려 봤다

"되돌림이 작동한다"는 주장은 실제로 되돌아가는 걸 보기 전까지는 주장일 뿐이다.
그래서 전용 카나리 앱을 하나 만들고, **존재하지 않는 이미지 태그로 바꾸는 커밋**을
`mode=arm`, `deadline=180`으로 올렸다.

```
[..] 👁  감시 시작 c35158c9 app=nav-canary mode=arm deadline=180s
[..]   → c35158c9 nav-canary 에 도달
[..]   ! c35158c9 도달 후 180s 안에 Healthy 미달 — health=Degraded
[..]   ↩ revert 커밋 push 성공
```

state에는 `REVERTED`가 남았고 카나리는 이전 상태로 돌아왔다.
**이 한 번의 실패 시험이 이후의 모든 "작동합니다"를 떠받친다.**

## 7. 설계가 틀렸던 곳 셋

여기부터가 진짜 쓸모 있는 부분이다.

### (1) ConfigMap은 갱신됐는데 프로세스는 옛 코드였다

와치독 코드는 ConfigMap으로 주입한다. 고쳐서 push하면 ArgoCD가 Synced 초록불을 켠다.
그런데 **파드 안에서 돌고 있는 파이썬 프로세스는 여전히 옛 코드였다.**
볼륨 파일은 바뀌지만 이미 메모리에 로드된 모듈은 안 바뀐다.

한동안 "고쳤는데 왜 그대로지"를 반복했다. 교훈은 하나다.
**Synced는 "선언이 일치한다"는 뜻이지 "그 코드가 실행 중이다"라는 뜻이 아니다.**
지금은 코드 다이제스트를 스스로 비교해 바뀌었으면 프로세스를 재기동한다.

### (2) `py_compile`은 import 누락을 못 잡는다

렌더 전에 문법 검사를 걸어 뒀는데, `import hashlib` 하나가 빠진 채로 클러스터까지
나가서 CrashLoop가 났다. 문법은 맞았기 때문이다. `NameError`는 **그 줄이 실행되어야**
난다.

그래서 게이트를 "컴파일"에서 "실제 1회 실행"으로 바꿨다. 클러스터 밖이라 한 주기는
반드시 실패하지만, 잡으려는 건 그게 아니라 *모듈이 로드조차 못 하는 경우*다.

```python
env = dict(os.environ, INTERVAL="0", DRY_RUN="true")
r = subprocess.run([sys.executable, src], capture_output=True, text=True, env=env)
out = r.stdout + r.stderr
for bad in ("NameError", "ImportError", "ModuleNotFoundError",
            "SyntaxError", "IndentationError", "AttributeError"):
    if bad in out:
        sys.exit("자기검사 실패 — " + bad)
```

**적용되지 않는 검증 경로를 하나 두는 것**, 그게 이 게이트의 전부다.

### (3) revision이 항상 git SHA인 것은 아니다

가장 최근에 맞은 것이고 가장 마음에 드는 실패다.

도달 판정은 이 한 줄이다.

```bash
git merge-base --is-ancestor <감시할 커밋> <Application.status.sync.revision>
```

여기엔 "revision은 git SHA"라는 전제가 깔려 있다. 그런데 **helm 차트 레포를 소스로
쓰는 Application은 거기에 차트 버전이 들어간다.** 모니터링 스택 앱의 revision은
`65.5.0`이었다.

`is_ancestor("56bb1ff…", "65.5.0")`은 영원히 False다. 그래서 와치독은 900초를 꼬박
기다린 뒤 이렇게 끝냈다.

```
! 56bb1ffb 900s 안에 monitoring-prod 에 도달하지 못함
  — 동기화가 멈춰 있는지 사람이 봐야 한다
```

동기화는 멀쩡했다. 그 커밋의 내용은 이미 클러스터에 반영돼 있었고 나는 그걸 실측까지
한 상태였다. **진짜 원인은 "구조적으로 감시할 수 없는 앱을 지목한 트레일러 오타"인데,
15분 뒤에 엉뚱한 진단을 내놓은 것이다.**

무응답보다 나쁜 건 조용한 오답이다. 그래서 가드를 넣었다. revision이 40자 hex가
아니면 기다리지 않고 즉시 `ERROR_UNWATCHABLE`로 끝내고, 이벤트에 대안까지 적는다.
900초가 0초가 됐다.

한 가지 안 건 것도 있다. revision이 비어 있는 경우는 걸지 않는다 —
아직 한 번도 동기화되지 않은 과도기이고, 그건 정상적인 도달 대기다.
**가드는 "틀린 것"만 잡아야지 "아직 안 된 것"까지 잡으면 새 오탐이 된다.**

고치고 나서 전수 조사를 해 보니, 내 클러스터 80여 개 앱 중 revision이 SHA가 아닌
— 즉 이 방식으로는 구조적으로 감시할 수 없는 — 앱이 6개였다. 전부 차트나 외부
소스를 쓰는 앱이다.

## 8. 무엇을 되돌리지 *않을지*가 더 중요하다

와치독을 실전에 무장(`arm`)하기 전에 두 축을 확인한다.

**① 이미지 태그가 git에 있는가.**
ArgoCD Image Updater의 write-back 방식에 따라 답이 갈린다. 공식 문서는 `argocd`
방식을 이렇게 설명한다.

> The `argocd` write-back method directly modifies the Argo CD `Application` resource in the
> cluster ... **This method is pseudo-persistent.** If you delete the `Application` resource from
> the cluster and re-create it, changes made by Image Updater will be gone.
> — [Argo CD Image Updater, *Update methods*][image-updater-methods]

즉 이 방식을 쓰는 앱은 **이미지 태그가 클러스터에만 있고 git에는 없다.**
git이 참이 아니므로 `git revert`로 되돌릴 수 있는 게 아니다. 와치독의 전제가 깨진다.
내 클러스터에선 5개 앱이 여기 해당해서 무장 대상에서 제외했다.
(`git` 방식을 쓰는 앱은 반대로 안전하다.)

**② `prune`이 켜져 있는가.**
`prune: true`인 앱에서 잘못된 되돌림은 단순 롤백이 아니라 **리소스 삭제**로 증폭된다.
ArgoCD 문서가 prune을 기본 비활성으로 둔 이유("as a safety mechanism")와 같은
맥락이다.[^prune]

공교롭게도 내가 제일 먼저 무장하고 싶었던 앱이 두 조건에 다 걸렸다.
그래서 1호는 **"git이 참이고 prune이 꺼진, 죽어도 아프지 않은 앱"** 으로 미뤘다.
만들어 놓고 안 쓰는 게 아니라, 쓸 자리를 고르는 데 시간을 쓰는 것이다.

## 9. 한계 — 솔직하게

- **자식 앱까지 따라가지 않는다.** app-of-apps 구조에서 Application *정의* 를 고친
  커밋은 루트 앱을 지목해야 하는데, 그러면 "정의가 반영됐고 루트가 Healthy하다"까지만
  본다. 그 아래 자식 앱이 새 설정으로 건강한지는 별개다. 필요해지면 `expect`를
  확장할 일이고, 지금은 과설계다.
- **`expect`는 `Healthy` 하나뿐이다.** ArgoCD의 health가 커버하지 못하는 회귀
  (응답은 200인데 내용이 틀린 경우 같은)는 못 잡는다.
- **판정 표본이 적다.** 지금까지 실전 판정은 몇 건뿐이다. 이 글의 주장 중
  "잘 작동한다"에 해당하는 부분은 그 표본 크기만큼만 믿어야 한다.
- **단일 인스턴스다.** 와치독 자신이 죽으면 감시가 조용히 멈춘다. 감시자를 감시하는
  문제는 아직 안 풀었다.

## 10. 남는 생각

이번에 제일 여러 번 고쳐 쓴 문장은 이것이다.

> 초록불은 "선언이 일치한다"는 뜻이지 "의도가 달성됐다"는 뜻이 아니다.

Synced가 코드 실행을 보장하지 않았고, `ProgressDeadlineExceeded`가 롤백을 뜻하지
않았고, revision이 SHA를 뜻하지 않았다. 자동화를 하나 더 얹을 때마다 늘어나는 건
안심이 아니라 **확인해야 할 전제**였다.

그래서 이 와치독의 본체는 되돌림 코드가 아니라 그 옆의 여섯 개 안전장치라고 생각한다.
자동으로 뭔가를 되돌리는 기능은 200줄이면 되지만, 그게 틀렸을 때 얼마나 조용히
멈추는가는 그보다 훨씬 긴 고민이었다.

---

[^prune]: "By default (and as a safety mechanism), automated sync will not delete resources when Argo CD detects the resource is no longer defined in Git." — [Argo CD, *Automated Sync Policy*][argo-autosync]

## References

- Argo CD, *Automated Sync Policy* — <https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/>
- Kubernetes, *Deployment* (API Reference, `DeploymentSpec`) — <https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/deployment-v1/>
- Kubernetes, *Deployments* (개념 문서) — <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
- Argo CD Image Updater, *Update methods* — <https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/>
- Git, *git-interpret-trailers* — <https://git-scm.com/docs/git-interpret-trailers>

[argo-autosync]: https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/
[k8s-deployment-api]: https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/deployment-v1/
[image-updater-methods]: https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/
[git-trailers]: https://git-scm.com/docs/git-interpret-trailers
