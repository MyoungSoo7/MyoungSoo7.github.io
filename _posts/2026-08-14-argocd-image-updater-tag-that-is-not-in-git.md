---
layout: post
title: "GitOps 라고 불렀지만 태그는 Git 에 없었다 — image-updater 의 write-back 을 클러스터에서 열어봤다"
date: 2026-08-14 18:35:00 +0900
categories: [gitops, kubernetes]
tags: [argocd, argocd-image-updater, gitops, github-actions, ghcr, server-side-apply, kubernetes, k3s]
---

내 XR 프로젝트의 배포 구조를 설명해 달라는 말을 듣고 한 줄로 답했다. "GitHub Actions 가 이미지를 굽고, ArgoCD 가 GitOps 로 배포한다." 맞는 말이다. 그런데 그 문장이 맞는지 확인하려고 클러스터를 열어봤더니, **지금 돌고 있는 이미지 태그가 Git 어디에도 없었다.**

이 글은 그 확인 과정이다. 구조 자랑이 아니라, 자기가 쓴 구조에 대해 자기가 틀렸던 지점의 기록에 가깝다.

> **정정 (2026-08-15)**: 이 글의 7절과 8절에 사실관계 오류가 있었다. tts 태그가 `values.yaml` 로 관리된다고 썼는데, 실제로는 한 달간 그렇지 않았다 — 그것도 이 글이 3절에 인용해 둔 데이터가 이미 보여 주고 있었다. 본문은 그대로 두고 [9절](#9-정정-2026-08-15--이-글은-스스로-인용한-증거를-못-읽었다)에 정정을 붙였다.

## 0. 무엇을 쟀고 무엇을 안 쟀나

먼저 이 글의 주장 범위를 좁혀 둔다.

- **잰 것**: 워크플로 파일의 잡 구성, Application 매니페스트의 애노테이션, 클러스터에 실제로 떠 있는 파드의 이미지 태그, Application 오브젝트의 `helm.parameters` 와 `managedFields`, Git `master` 에 그 파라미터가 있는지.
- **안 잰 것**: 성능·비용·가용성. 이 클러스터는 홈랩 K3s 단일 클러스터고, 이 글의 어떤 문장도 프로덕션 권고가 아니다.
- **추정이라고 표시한 것**: 아래 7절의 tts 타임스탬프 건. 원인이 확정되지 않았고, 리포 주석에도 "(추정)" 으로 적혀 있다.

버전은 Argo CD `v3.4.1`, Argo CD Image Updater `v0.16.0` 이다.

## 1. 구조는 이렇게 생겼다

```
git push (main)
   ↓
GitHub Actions  ci.yml — 잡 7개
   ↓ 이미지 push
ghcr.io/myoungsoo7/lemuel-xr-{backend,ai,frontend,tts}
   ↓ 레지스트리 폴링
Argo CD Image Updater
   ↓ 태그 갱신
Argo CD Application (lemuel-xr-prod)
   ↓ sync
K3s 파드 롤아웃
```

CI 쪽은 워크플로 파일이 `ci.yml` 하나고 그 안에 잡이 7개다. `changes` 가 경로 필터로 아래 잡을 켜고 끄고, `gate-baseline` 이 문서·콘텐츠 판정기를 돌리고, `backend`·`ai` 는 테스트 후 이미지를 굽고, `frontend` 는 lint·타입체크·상담번호 하드코딩 게이트·프로덕션 서버를 띄운 뒤의 탭 타깃 e2e 까지 돌고, `mission-e2e` 는 pgvector 를 띄우고 진짜 백엔드를 기동한 상태로 미션 씬 e2e 를 돈다.

이미지 태그는 `main-${{ github.sha }}` 다. 짧은 SHA 가 아니라 40자 전체가 들어간다.

**별도의 배포 워크플로 파일은 없다.** CI 의 끝은 GHCR 푸시고, 그 뒤는 클러스터가 당겨간다. 이건 [OpenGitOps 원칙](https://opengitops.dev/) 중 3번 "Pulled Automatically" 에 해당한다 — 파이프라인이 클러스터에 밀어 넣는 게 아니라, 클러스터 안의 에이전트가 스스로 당긴다.

## 2. 오늘 머지한 커밋이 파드까지 갔는지 봤다

말로만 하면 믿을 수 없으니 쟀다. 오늘 오후에 머지한 커밋은 `cc0991e` 였다.

```
$ kubectl get pods -n lemuel-xr-prod -o custom-columns=...

lemuel-xr-ai-...        ai:main-cc0991eb...        Ready
lemuel-xr-backend-...   backend:main-cc0991eb...   Ready
lemuel-xr-frontend-...  frontend:main-cc0991eb...  Ready
lemuel-xr-frontend-...  frontend:main-cc0991eb...  Ready
lemuel-xr-tts-...       tts:main-77641f7c...       Ready
```

Application 은 `Synced / Healthy`. push 부터 롤아웃까지 사람 손이 들어간 지점은 없다. 여기까지는 설명한 대로다.

그런데 `tts` 만 커밋이 다르다. 이건 뒤에서 다룬다.

## 3. 그 태그는 Git 에 없다

`kubectl get application lemuel-xr-prod -n argocd` 로 파라미터를 꺼내면 이렇게 나온다.

```
app.image.tag       = main-cc0991eb77a52035234abfdc09b3581df318976f
ai.image.tag        = main-cc0991eb77a52035234abfdc09b3581df318976f
frontend.image.tag  = main-cc0991eb77a52035234abfdc09b3581df318976f
tts.image.tag       = main-77641f7cc87d9cfb063e4307b8b3e8c294760375
```

그리고 같은 Application 의 Git 원본(`helm-deploy` 리포 `master` 의 `argocd-applications/lemuel-xr-prod.yaml`)을 열면 — `parameters` 라는 키 자체가 없다.

원인은 애노테이션 한 줄이다.

```yaml
argocd-image-updater.argoproj.io/write-back-method: argocd
```

Image Updater 의 [update methods 문서](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/)는 두 가지 write-back 방식을 정의한다. `git` 은 Application 의 Git 리포에 커밋을 만들고, `argocd` 는 **Kubernetes API 로 Application 리소스를 직접 고친다.** 후자는 `argocd app set --parameter ...` 와 같은 일을 하는 것이고, 기본값이며, 추가 설정이 필요 없다.

즉 내가 "GitOps 로 배포한다"고 말했을 때, 차트·인그레스·레플리카 같은 것은 정말로 Git 이 원본이지만, **지금 무엇이 돌고 있는가는 Git 이 모른다.** [OpenGitOps 원칙](https://opengitops.dev/) 2번 "Versioned and Immutable" — 원하는 상태가 버전 관리되고 전체 이력이 남는다 — 이 부분에 대해서는 이 구조가 그 원칙을 지키지 않는다. 롤백하려면 Git 을 되돌리는 게 아니라 클러스터의 Application 을 고쳐야 한다.

## 4. 문서가 스스로 경고하고 있었다

여기서 인상적이었던 건, 이 위험을 남이 아니라 **공식 문서가 먼저 적어 뒀다**는 점이다. 같은 페이지의 `argocd` write-back 절을 그대로 옮기면:

> This method is pseudo-persistent. If you delete the `Application` resource from the cluster and re-create it, changes made by Image Updater will be gone. The same is true if you manage your `Application` resources using Git, and the version stored in Git is synced over the resource in the cluster. This method is most suitable for Applications also created imperatively, i.e. using the Web UI or CLI.
> — [Argo CD Image Updater, Update methods](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/)

"pseudo-persistent(유사 영속)". 그리고 이 방식은 **웹 UI 나 CLI 로 명령형으로 만든 Application 에 가장 적합하다**고 못 박는다.

내 구조는 정확히 그 반대다. Application 은 Git 으로 관리된다. `root-app.yaml` 이 app-of-apps 로 `argocd-applications/` 디렉토리 전체를 sync 하고, `selfHeal: true` 다. 그 파일에 내가 직접 써 둔 주석은 이렇다.

```yaml
# 누군가 Application spec 을 직접 kubectl edit 하면 root-app 가 Git 상태로 복원.
```

Image Updater 가 하는 일이 바로 "Application spec 을 직접 고치는 것"이다. 그러면 root-app 이 그걸 Git 상태로 되돌려야 하고, 태그는 사라져야 한다. 문서 표현대로 "the version stored in Git is synced over the resource in the cluster" 다.

그런데 안 사라졌다. 위 2절에서 봤듯이 파드는 멀쩡히 최신 커밋으로 돌고 있다.

## 5. 왜 안 덮였나 — managedFields 를 열어봤다

여기서부터가 이 글을 쓰게 만든 부분이다. `--show-managed-fields` 로 Application 의 필드 소유권을 꺼냈다.

```
managedFields 4개
 - argocd-controller            Apply   | helm.parameters 소유: 아니오
 - argocd-controller            Update  | helm.parameters 소유: 아니오
 - argocd-image-updater         Update  | helm.parameters 소유: 예
 - argocd-application-controller Update | helm.parameters 소유: 예
```

root-app 이 자식 Application 을 적용할 때 쓰는 필드 매니저(`argocd-controller`)는 `spec.source.helm.parameters` 를 **소유하지 않는다.** 소유자는 `argocd-image-updater` 다.

그리고 root-app 의 sync 옵션에는 이게 켜져 있다.

```yaml
syncOptions:
  - ServerSideApply=true  # ArgoCD Application CRD 의 큰 annotation 회피
```

Kubernetes 공식 문서의 Server-Side Apply 필드 관리 절이 정확히 이 상황을 규정한다.

> If you remove a field from a manifest and apply that manifest, Server-Side Apply checks if there are any other field managers that also own the field. If the field is not owned by any other field managers, it is either deleted from the live object or reset to its default value, if it has one.
> — [Kubernetes, Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/)

Git 매니페스트에 `parameters` 가 없으니 root-app 은 그 필드를 뺀 채로 apply 한다. SSA 는 "다른 매니저가 이 필드를 소유하고 있나?" 를 확인하고, 소유자가 있으므로 지우지 않는다. 그래서 태그가 살아남는다.

**즉 문서가 경고한 사고가 안 난 이유는, 내가 그 위험을 알고 막아서가 아니다.** 주석에 적힌 대로 `ServerSideApply=true` 는 Application CRD 의 `last-applied-configuration` 애노테이션이 너무 커지는 문제를 피하려고 켠 것이다. 완전히 다른 목적으로 켠 스위치가 우연히 다른 사고를 막고 있었다.

같은 문서가 그 우연의 반대편도 알려 준다 — SSA 는 "마지막으로 적용한 상태" 를 기록하는 레거시 client-side apply 와 달리 "누가 어떤 필드를 관리하는가" 를 추적한다. 그러니 이 방어는 SSA 라는 전제 위에만 서 있다. 누군가 성능이나 호환성 이유로 저 한 줄을 끄면, 그 순간 방어도 같이 꺼진다. 그때 깨지는 것은 root-app 이 아니라 **프로덕션 이미지 태그**다.

덧붙여, 문서가 경고한 **첫 번째** 경우 — Application 을 지웠다 다시 만드는 경우 — 는 SSA 와 무관하게 그대로 유효하다. 새로 만든 오브젝트에는 image-updater 가 소유한 필드가 애초에 없다. 재해 복구로 클러스터를 다시 세우면 태그는 Git 에 없으므로 복원되지 않고, 각 서비스는 차트 기본값으로 돌아간다.

## 6. 그래서 이건 GitOps 인가

절반은 그렇다. 정직하게 나누면 이렇다.

| 대상 | 원본 | 이력 |
|---|---|---|
| 차트·인그레스·리소스·레플리카 | Git (`helm-deploy` master) | 남는다 |
| Application spec 자체 | Git (app-of-apps) | 남는다 |
| **지금 돌고 있는 이미지 태그** | **클러스터의 Application 오브젝트** | **안 남는다** |

고치는 방법은 문서에 이미 있다. `write-back-method: git` 으로 바꾸면 Image Updater 가 `.argocd-source-<앱이름>.yaml` 을 Application 이 바라보는 경로에 커밋한다. 그러면 태그도 Git 이 원본이 되고 이력이 남는다. 대신 CI 가 아니라 클러스터가 리포에 쓰기 권한을 갖게 되고, 커밋 루프와 충돌을 관리해야 한다. 문서는 이 방식이 Application 이 **브랜치**를 추적할 때를 전제한다고 명시한다.

지금 당장 바꾸지는 않았다. 다만 "GitOps 로 배포한다" 는 한 줄이 무엇을 포함하고 무엇을 포함하지 않는지는 이제 안다. 이 글의 목적은 거기까지다.

## 7. tts 만 왜 빠져 있나 (원인은 추정)

2절에서 `tts` 만 다른 커밋이었다. Application 애노테이션의 추적 목록에 tts 가 없다.

```yaml
argocd-image-updater.argoproj.io/image-list: backend=...,ai=...,frontend=...
```

세 개뿐이다. tts 태그는 사람이 직접 박는다 — **고 이 글은 썼는데, 하루 뒤 그게 틀렸다는 게 드러났다. 9절에 정정을 붙였다.**

배경은 이렇다. 세 이미지 모두 갱신 전략이 `newest-build` 인데, [문서](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-strategies/)는 이 전략을 "레지스트리에서 **가장 최근에 빌드된** 이미지로 갱신" 이라고 정의한다. 즉 순위를 매기는 기준이 태그 이름이 아니라 이미지의 빌드 시각이다.

그 빌드 시각은 OCI 이미지 설정 JSON 의 `created` 필드에서 온다. 그리고 [OCI Image Spec](https://github.com/opencontainers/image-spec/blob/main/config.md) 은 이 필드를 이렇게 정의한다.

> **created** _string_, OPTIONAL — An combined date and time at which the image was created, formatted as defined by RFC 3339, section 5.6

**OPTIONAL 이다.** 스펙이 있어도 되고 없어도 되는 값으로 규정한 필드 위에, 배포 순서 결정이 얹혀 있는 셈이다.

관측된 사실은 이렇다. 2026년 7월 14일, tts 롤아웃이 최신 fix 가 아니라 옛 이미지에 고착됐다. 대응으로 tts 를 image-updater 관리에서 빼고 태그를 직접 관리하도록 바꿨고, 그 뒤로 재발하지 않았다. 원인에 대해서는 리포 주석에 "tts 이미지를 '마지막 정상 이미지 FROM' 방식으로 빌드하면서 created timestamp 가 베이스 것으로 상속돼(추정)" 라고 적혀 있다. **이 인과는 확정되지 않았다.** 타임스탬프를 직접 뜯어 비교한 기록이 없으므로, 이 글에서도 추정으로만 남긴다.

확정된 것만 말하면 — 태그가 커밋 SHA 라서 이름만으로는 순서를 알 수 없고(알파벳순으로 정렬하면 SHA 는 무의미하다), 그래서 순서 판단이 전적으로 빌드 타임스탬프에 의존하며, 그 타임스탬프는 스펙상 선택 필드다. 이 조합은 원인이 무엇이든 취약하다.

## 8. 정리

- CI 는 이미지를 굽는 데까지고, 배포는 클러스터가 당겨간다. 여기까지는 설명대로 동작했다 — 오늘 머지한 커밋이 파드까지 간 것을 확인했다.
- 그러나 **돌고 있는 이미지 태그는 Git 에 없다.** `write-back-method: argocd` 는 Application 오브젝트를 직접 고치고, 공식 문서는 이를 "pseudo-persistent" 라고 부르며 Git 으로 관리되는 Application 에는 부적합하다고 명시한다.
- 그 사고가 아직 안 난 이유는 `ServerSideApply=true` 가 필드 소유권 검사를 하기 때문이고, **그 옵션은 완전히 다른 이유로 켠 것이었다.** 의도한 방어가 아니라 우연한 방어다. — *이 항목은 정확하지 않았다. tts 에 한해서는 사고가 이미 나 있었다. 9절 참조.*
- Application 을 재생성하는 경로에서는 이 우연도 통하지 않는다.
- `newest-build` 는 OCI 스펙상 OPTIONAL 인 `created` 필드에 순서 판단을 의존한다. tts 를 수동 관리로 뺀 이유의 관측된 결과는 명확하지만, 인과는 미확정이다.

구조를 설명할 수 있다는 것과 그 설명이 맞는지 확인해 본 적이 있다는 것은 다른 일이다. 이번에는 후자가 아니었다.

## 9. 정정 (2026-08-15) — 이 글은 스스로 인용한 증거를 못 읽었다

이 글을 올린 다음 날, tts 이미지를 `values.yaml` 에서 bump 하고 머지했다. **파드가 안 바뀌었다.** Argo CD 는 `Synced/Healthy` 였고 새 커밋까지 반영돼 있었다. 10분을 폴링하며 지켜봐도 그대로였다.

```
values.yaml (master) = main-cf6c4f35...   ← 방금 머지한 값
실제 파드 이미지      = main-77641f7c...   ← 23일 전 그대로
```

원인은 이 글이 3절에서 **이미 인용해 놓은 그 목록**이었다.

```
tts.image.tag = main-77641f7cc87d9cfb063e4307b8b3e8c294760375
```

3절은 "이 파라미터가 `values.yaml` 을 이긴다" 고 정확히 설명한다. 그리고 7절은 tts 만 예외로 "사람이 직접(= `values.yaml` 로) 박는다" 고 쓴다. **두 절이 서로 모순인데, 쓰면서 연결하지 못했다.** 목록에 `tts.image.tag` 가 찍혀 있는 것을 그대로 옮겨 놓고도, 그것을 "사람이 관리하는 값" 으로 읽었다.

### 무엇이 사실이었나

Image Updater 는 컴포넌트를 `image-list` 에서 빼도 **이미 써둔 파라미터를 지우지 않는다.** 그래서 7월 14일에 tts 를 추적 목록에서 제외한 순간, 그 파라미터는 아무도 갱신하지 않는 고아가 됐다. `--set` 과 같은 우선순위로 `values.yaml` 을 계속 이기면서.

`values.yaml` 의 tts 태그 이력을 뒤지면 이렇다.

| 커밋 | 날짜 | 내용 |
|---|---|---|
| `7ef56c6` | 2026-07-14 | `main-77641f7` 로 고정 — "af681a3 고착 해소" |
| `4b0e13d` | 2026-08-15 | 다음 변경. **그 사이 한 번도 안 바뀜** |

`values.yaml` 이 무력한 상태였으므로, 7월 14일에 파드를 `af681a3 → 77641f7` 로 옮긴 것도 `values.yaml` 고정이 아니라 그 파라미터였다. 무엇이 그 값을 썼는지는 확정하지 못했다(제외 직전 Image Updater 의 마지막 갱신이거나 수동 `argocd app set` 이거나). 확정된 것은 **조치의 공로가 잘못된 메커니즘에 돌아가 있었다**는 것뿐이다. 리포 주석에도 같은 인과가 적혀 있었고 함께 정정했다.

한 달간 아무 증상이 없었던 이유는 두 값이 우연히 같았기 때문이다(둘 다 `77641f7`). 잠복해 있다가 첫 변경에서 터지는 종류의 함정이다.

### 8절의 한 줄을 취소한다

> 그 사고가 아직 안 난 이유는 `ServerSideApply=true` 가 …

tts 에 한해서는 **이미 나 있었다.** `values.yaml` 이 배포를 통제한다는 전제가 한 달간 거짓이었고, 증상이 없었을 뿐이다. Server-Side Apply 는 Application 을 *재생성* 하는 경로를 막아 줄 뿐, 고아 파라미터가 `values.yaml` 을 덮어쓰는 것과는 무관하다.

### 조치와, 조치의 한계

고아 파라미터 두 개(`tts.image.{repository,tag}`)를 클러스터에서 제거했다. 제거 직후 즉시 롤아웃됐다. 현역 컴포넌트의 파라미터는 그대로 뒀다 — 지우면 `values.yaml` 의 `latest` 로 떨어진다.

재발 감지는 별도 스크립트로 남겼다. **CI 에는 넣지 못했다.** 이 값은 Git 에 없고 클러스터에만 있어서, Git 파일만 읽는 차트 가드에 규칙을 넣으면 검사 대상이 0건이 된다. 그 가드가 다른 규칙에서 막으려고 만들어 둔 실패 모드 — *검사하지 못한 것* 과 *검사해서 통과한 것* 의 출력이 같아지는 것 — 을 새 규칙에서 그대로 반복하는 꼴이 된다. 그래서 클러스터를 볼 수 있는 곳에서 도는 스크립트로 분리했다.

근본 원인은 그대로 남아 있다. 1번 문서가 `argocd` write-back 을 "pseudo-persistent" 라 부르며 Git 으로 관리되는 Application 에 부적합하다고 명시한 그 문장이, 이 사고의 정확한 설명이다. `write-back-method: git` 으로 옮기는 것은 아직 하지 않았다.

### 이 글이 배운 것

이 글은 "구조를 설명할 수 있다는 것과 그 설명이 맞는지 확인해 본 적이 있다는 것은 다르다" 로 끝냈다. 그러면서 **확인한 데이터를 화면에 띄워 놓고도 결론에서 그것을 뒤집지 못했다.** 증거를 모으는 것과 증거가 자기 문장과 충돌하는지 대조하는 것은 또 다른 일이었다. 이번에는 후자가 아니었다.

## References

1. Argo CD Image Updater — [Update methods](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/) (`argocd` / `git` write-back 방식의 정의, "pseudo-persistent" 경고)
2. Argo CD Image Updater — [Update strategies](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-strategies/) (`newest-build` 의 정의, mutable/immutable 태그 전제)
3. Kubernetes — [Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/) (필드 소유권과 매니페스트에서 필드를 뺐을 때의 동작)
4. OpenContainers — [OCI Image Configuration (`config.md`)](https://github.com/opencontainers/image-spec/blob/main/config.md) (`created` 필드가 OPTIONAL 임)
5. OpenGitOps — [GitOps Principles v1.0.0](https://opengitops.dev/) (Declarative / Versioned and Immutable / Pulled Automatically / Continuously Reconciled)

*인용 관련 참고: 1·2번 공식 문서의 stable 판은 설정을 `ImageUpdater` 커스텀 리소스로 적는 최신 형태를 보여 주지만, 이 클러스터가 돌리는 v0.16.0 은 Application 애노테이션 형태다. 이 글이 그 문서에서 인용한 것은 설정 문법이 아니라 두 write-back 방식과 `newest-build` 의 정의뿐이다.*
