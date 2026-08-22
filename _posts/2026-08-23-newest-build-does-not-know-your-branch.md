---
layout: post
title: "newest-build 는 브랜치를 모른다 — allow-tags 한 줄이 빠져 운영에 develop 이 올라갔다"
date: 2026-08-23 04:50:19 +0900
categories: [kubernetes, argocd]
tags: [argocd, image-updater, gitops, k3s, 배포사고]
---

야간 점검 중에 운영 네임스페이스의 파드 이미지를 훑다가 이걸 봤다.

```
settlement-app-5cd58fd6dd-nnsvg      settlement:develop-71ce7d9
settlement-frontend-548585544d-b25fq settlement-frontend:develop-c74e827
settlement-anomaly-54f4794b75-wq6c9  settlement-anomaly:main-32e4b43
settlement-forecast-744445768d-78brp settlement-forecast:main-32e4b43
settlement-account-7b558f54bd-dnvq9  settlement-account:main-f2b3b84
```

같은 네임스페이스, 같은 레지스트리, 같은 모노리포에서 나온 이미지들이다. 그런데 **본체 두 개만 `develop-` 태그로 돌고 있고 위성 서비스는 전부 `main-` 태그로 돌고 있다.** 이 리포의 브랜치 전략은 `main` = 배포, `develop` = CI·안전성 검사다. 즉 운영에 올라가면 안 되는 쪽이 올라가 있었다.

## 1. 사람이 배포한 게 아니다

먼저 확인한 건 "누가 손으로 태그를 바꿨나" 였는데, 아니었다. ArgoCD Image Updater 자신의 로그에 전부 남아 있었다 (UTC).

```
09:56Z backend  develop-4547b2b → main-32e4b43
10:44Z backend  develop-4547b2b → develop-71ce7d9
15:50Z frontend main-32e4b43    → develop-1b98e6f
17:48Z frontend develop-1b98e6f → develop-c74e827
```

8시간 동안 백엔드가 develop → main → develop 으로 갔고, 프런트가 main → develop 으로 갔다. **브랜치 경계를 왕복하고 있었다.** 자동 롤백 스크립트가 남긴 "정상 태그" 기록에도 같은 왕복이 그대로 찍혀 있었다 — 하루에 6번.

## 2. 원인은 애노테이션 한 줄의 부재

문제의 Application 에는 이 애노테이션이 있었다.

```yaml
argocd-image-updater.argoproj.io/backend.update-strategy: newest-build
```

그리고 **`allow-tags` 가 없었다.**

`newest-build` 는 이름 그대로 "레지스트리에서 가장 최근에 빌드된 이미지" 로 올린다. 여기서 두 가지가 겹친다.

첫째, 공식 문서는 semver·digest 가 아닌 전략에서는 버전 제약이 무력화된다고 명시한다.

> If you use an update strategy other than `semver` or `digest`, the `version_constraint` will not have any effect and **all tags returned from the registry will be considered for update**. If you need to further restrict the list of tags to consider, see filtering tags below.
>
> — [Argo CD Image Updater, Configuring images for update](https://argocd-image-updater.readthedocs.io/en/stable/configuration/images/)

둘째, 그 "further restrict" 수단인 `allow-tags` 의 기본값이 문제다.

> If the annotation is not specified, a match function `any` will be used to match the tag names, **effectively performing no filtering at all**.
>
> — [같은 문서, Filtering tags](https://argocd-image-updater.readthedocs.io/en/stable/configuration/images/#filtering-tags)

두 문장을 합치면 결론은 하나다. **`newest-build` + `allow-tags` 없음 = 레지스트리에 있는 모든 태그가 후보.** `develop-*` 도 후보고 `main-*` 도 후보다. 그중 가장 최근에 푸시된 게 이긴다.

그리고 어느 쪽이 더 자주 푸시되는가? 당연히 develop 이다. GHCR 패키지 버전을 최근 60개까지 조회해 세어보면 `settlement` 이미지에 `develop-*` 태그가 18개, `main-*` 이 2개다. 경주 자체가 성립하지 않는다. develop 이 거의 항상 이긴다.

`newest-build` 는 태그 문자열을 브랜치로 해석하지 않는다. 그 전략에게 `main-32e4b43` 과 `develop-71ce7d9` 는 그냥 **빌드 시각이 다른 두 개의 문자열**이다. 브랜치 개념은 내 머릿속에만 있었고 컨트롤러에는 없었다.

## 3. 대조군이 같은 클러스터 안에 있었다

이 진단이 추측이 아니라고 말할 수 있는 건, 반증 가능한 대조군이 옆에 있었기 때문이다.

위성 서비스들을 묶은 Application 에는 서비스마다 이 애노테이션이 붙어 있다.

```yaml
argocd-image-updater.argoproj.io/anomaly.update-strategy: newest-build
argocd-image-updater.argoproj.io/anomaly.allow-tags: regexp:^main-[0-9a-f]{7,40}$
```

전략은 **똑같이 `newest-build`** 다. 다른 건 `allow-tags` 한 줄뿐이다.

그리고 `settlement-anomaly` 의 GHCR 패키지에도 (같은 조회 범위에서) `develop-*` 태그가 14개 쌓여 있다. 즉 "위성은 develop 빌드가 없어서 안 올라간 것" 이 아니다. **후보는 똑같이 있었는데 정규식이 걸러냈다.** 그 결과 위성은 전부 `main-32e4b43` 에 머물러 있다.

같은 컨트롤러, 같은 레지스트리, 같은 태그 구성, 한 줄만 다른 설정, 정반대의 결과. 변수 하나짜리 자연 실험이 이미 돌아가고 있었던 셈이다.

## 4. 조용한 2차 피해 — 롤백 기준선 오염

더 불편한 건 이쪽이었다. 이 클러스터에는 헬스체크가 연속 실패하면 "마지막 정상 태그" 로 되돌리는 자동 롤백이 걸려 있다. 그 상태 파일을 열어보니 이렇게 되어 있었다.

```json
"good_tags": {
  "app.image.tag": "develop-71ce7d9",
  "frontend.image.tag": "develop-1b98e6f"
}
```

롤백 스크립트는 "지금 헬스체크가 통과하는 태그" 를 정상으로 학습한다. develop 이미지가 올라와서 헬스체크를 통과하면, 그게 정상 기준선이 된다. **즉 이 상태에서 장애가 나면 자동 롤백은 develop 빌드로 되돌린다.** 안전장치가 오염된 기준선을 성실하게 복원하는 셈이다.

이게 이 사고의 진짜 교훈이라고 본다. 잘못된 태그가 운영에 뜬 것보다, **그걸 정상으로 학습한 안전장치**가 더 오래 남는다.

## 5. 조치

수정 자체는 위성이 이미 쓰고 있는 걸 본체에도 붙이는 것뿐이다.

```yaml
argocd-image-updater.argoproj.io/backend.update-strategy: newest-build
argocd-image-updater.argoproj.io/backend.allow-tags: regexp:^main-[0-9a-f]{7,40}$
argocd-image-updater.argoproj.io/frontend.update-strategy: newest-build
argocd-image-updater.argoproj.io/frontend.allow-tags: regexp:^main-[0-9a-f]{7,40}$
```

한 가지 주의할 점이 있다. 문서가 이렇게 경고한다.

> If you specify an invalid match function, or the match function is misconfigured (i.e. an invalid regular expression is supplied), **no tag will be matched at all** to prevent considering (and possibly update to) the wrong tags by accident.
>
> — [같은 문서, Filtering tags](https://argocd-image-updater.readthedocs.io/en/stable/configuration/images/#filtering-tags)

정규식을 틀리면 에러가 아니라 **"아무 태그도 안 맞음"** 으로 조용히 떨어진다. 즉 오타 난 필터와 정상 동작하는 필터는 겉보기에 똑같다 — 둘 다 아무 일도 안 일어난다. 붙인 다음에는 실제로 갱신이 되는지 한 번은 확인해야 한다.

그리고 롤백 상태 파일의 `good_tags` 는 손으로 지워야 한다. 필터를 고쳐도 이미 학습된 기준선은 스스로 갱신되지 않는다.

## 6. 남는 질문 — 왜 애초에 없었나

애노테이션 7개짜리 위성 Application 은 필터를 다 갖췄는데, 정작 제일 중요한 본체 Application 만 빠져 있었다. 리포 전체를 훑어보니 `update-strategy` 를 쓰면서 `allow-tags` 가 0개인 Application 이 4개 있었다.

이건 "몰라서" 가 아니라 **필터가 없는 상태가 아무 신호도 내지 않기 때문**이라고 본다. 없으면 기본값 `any` 로 조용히 동작하고, 그 결과는 대부분의 날에는 우연히 맞다 — main 만 빌드하는 날에는 main 이 올라가니까. develop 을 푸시한 날에만 틀린다. 로그도 에러가 아니라 `level=info` 로 "Successfully updated" 라고 찍힌다.

그래서 이건 알림으로 잡을 수 있는 종류가 아니고, **설정을 정적으로 훑어서 "전략은 있는데 필터가 없는 조합" 을 찾아내는 것** 말고는 방법이 없어 보인다. 위의 `update-strategy` 개수 대 `allow-tags` 개수 비교가 그대로 그 검사식이다.

## References

- Argo CD Image Updater — [Configuring images for update](https://argocd-image-updater.readthedocs.io/en/stable/configuration/images/) (버전 제약 무력화, `allow-tags` 기본값 `any`, 잘못된 정규식 시 전량 미매치)
- Argo CD Image Updater — [Update strategies](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-strategies/) (`newest-build` 정의, `latest` 는 deprecated alias, 가변 태그에는 `digest` 권장)
- Argo CD Image Updater — [애노테이션 레퍼런스 (release-0.14 계열 문서)](https://argocd-image-updater.readthedocs.io/en/release-0.14/configuration/images/) — 이 클러스터가 돌리는 v0.16.0 은 애노테이션 방식이다. 최신 문서는 `ImageUpdater` CR 방식으로 넘어갔으므로 필드명이 다르다 (`allow-tags` → `allowTags`).

---

_이 글의 태그 전환 기록·GHCR 태그 개수·롤백 상태 파일 내용은 2026-08-21 새벽 자체 클러스터에서 직접 조회한 값이다. 인용한 세 문장은 게시 시점(2026-08-23)에 공식 문서 stable 페이지에서 그대로 확인했다 — 다만 stable 문서는 그사이 `ImageUpdater` CR 방식으로 넘어가 필드명이 `allowTags` 이고, 이 클러스터가 돌리는 v0.16.0 은 여전히 애노테이션(`allow-tags`) 방식이다. 특정 벤더의 성능·우열 주장을 담고 있지 않다._
