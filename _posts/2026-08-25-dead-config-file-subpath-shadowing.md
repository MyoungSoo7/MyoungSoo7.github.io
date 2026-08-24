---
layout: post
title: "리포에 있는 정본이 운영에서는 죽은 파일이었다 — subPath 그림자와 CI 사각지대"
date: 2026-08-25 06:59:15 +0900
categories: [engineering, kubernetes]
tags: [nginx, configmap, subpath, spa-fallback, gitops, ci, root-cause, helm]
---

관리자 화면 하나가 안 열린다는 제보를 받았다. 주소창에 직접 넣거나 새로고침하면 401 이 떨어지는데, 앱 안에서 메뉴를 눌러 들어가면 멀쩡히 열린다. 프론트 코드에도, 백엔드 권한 설정에도 손댄 사람이 없었다.

원인을 두 번 틀리게 짚고 나서야 진짜 이유에 닿았다. 그리고 진짜 이유는 "누가 규칙을 잘못 고쳤다" 가 아니라 **리포에서 정본이라고 부르던 파일이 운영에서는 아무 효력이 없는 파일이었다** 는 쪽이었다.

## 증상이 왜 이 모양이었나

SPA 는 클릭 이동에 서버 요청이 없다. 라우터가 브라우저 안에서 주소만 바꾸고 컴포넌트를 갈아끼운다. 그래서 라우팅용 서버 설정이 깨져도 **앱 안에서 돌아다니는 동안은 아무 일도 안 일어난다.** 깨진 게 드러나는 건 새로고침, 주소 직접 입력, 북마크, 새 탭 — 즉 브라우저가 그 경로로 실제 요청을 보내는 순간뿐이다.

로컬에서도 재현이 안 됐다. 개발 서버에는 nginx 가 아예 없으니까. 깨진 설정은 운영 컨테이너 안에만 있었다.

## 첫 번째 오답, 두 번째 오답

**"백엔드가 `/admin/**` 을 가로채는 것 아니냐"** — 그럴듯했지만 틀렸다. 파드에 들어가 실제로 서빙 중인 nginx 설정을 읽어보니, 401 은 백엔드가 화면 요청을 거부해서가 아니라 **nginx 가 그 요청을 정적 파일 폴백으로 안 내려보내고 그대로 API 로 넘겨서** 나온 것이었다. 백엔드 입장에서는 인증 없는 API 호출이 온 셈이니 401 이 정상 응답이다.

**"배포된 이미지가 낡았다"** — 이것도 틀렸다. 돌고 있는 이미지 태그는 그 시점 main 그대로였다. 낡은 건 이미지가 아니라 **설정**이었다.

## 근본원인 (1) — subPath 가 이미지 안의 파일을 가린다

프론트 이미지는 빌드 때 리포의 `nginx.conf` 를 컨테이너 안에 굽는다. 그런데 배포 차트가 ConfigMap 을 정확히 **그 자리에** 얹고 있었다.

```yaml
volumeMounts:
  - name: nginx-conf
    mountPath: /etc/nginx/conf.d/nginx.conf
    subPath: nginx.conf
```

`subPath` 는 볼륨 전체가 아니라 그 안의 한 항목만 지정한 경로에 마운트한다. 디렉터리째 덮지 않으니 옆의 파일들은 살아남지만, **같은 이름의 그 파일 하나는 완전히 가려진다.** 결과적으로 이미지에 구워 넣은 `nginx.conf` 는 운영에서 **한 번도 읽히지 않는 죽은 파일**이었다.

여기에 `subPath` 의 두 번째 성질이 겹친다. 쿠버네티스 문서가 못 박아 둔 문장이다.

> A container using a ConfigMap as a subPath volume mount will not receive ConfigMap updates.
> — [Kubernetes, ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)

즉 ConfigMap 내용을 고쳐도 이미 떠 있는 파드에는 반영되지 않는다. 파드를 새로 굴려야 한다. (차트에서 ConfigMap 해시를 파드 어노테이션에 넣어 두면 내용이 바뀔 때 롤아웃이 자동으로 일어난다. 이 조합이 없으면 "고쳤는데 왜 그대로지" 가 한 번 더 나온다.)

정리하면 상태는 이랬다.

| 사본 | 위치 | 운영에서 도는가 |
| --- | --- | --- |
| 1 | 앱 리포 `frontend/nginx.conf` | ❌ subPath 로 가려짐 |
| 2 | 앱 리포 `frontend/nginx.compose.conf` | ❌ 로컬 compose 전용 |
| 3 | 배포 리포 ConfigMap 템플릿 | ✅ **이것만 돈다** |

앱 리포에서 "정본" 이라 부르며 리뷰하고 테스트하던 파일은 1번이다. 운영을 결정하는 건 3번이다.

## 왜 하필 그 화면만 깨졌나

폴백 규칙이 **allowlist 형태의 정규식** 이었기 때문이다.

```nginx
# 배포되던 사본 (문제)
location ~ ^/admin/(ceo|login|operation|settlement|system)(/|$) {
    try_files $uri /index.html;
}
```

이런 규칙은 빠진 항목이 있어도 **오류를 내지 않는다.** 목록에 있는 화면은 잘 되고, 목록에서 빠진 화면만 조용히 API 취급을 받는다. 화면이 하나 추가될 때 앱 리포의 1번 파일만 고치면, 3번은 그대로 남아 그 화면 하나만 깨진다. 부분적으로 잘 도는 시스템이라 알람도 안 울린다.

`(/|$)` 접미사는 장식이 아니라 이 규칙의 핵심이다. 화면 접두사와 백엔드 API 경로를 가르는 게 정확히 이 부분이다. `settlement(/|$)` 는 `/admin/settlements` 나 `/admin/settlement-projection` 같은 API 경로에 걸리지 않는다. 이 두 글자가 빠지면 이번과 정반대 방향의 사고 — API 요청이 HTML 을 받는 — 가 난다.

고칠 때 규칙의 **순서**도 같이 봐야 했다. nginx 정규식 location 은 먼저 쓴 것이 이긴다.

> Then regular expressions are checked, in the order of their appearance in the configuration file.
> — [nginx, ngx_http_core_module](https://nginx.org/en/docs/http/ngx_http_core_module.html#location)

같은 파일에 `/admin` 을 백엔드로 넘기는 catch-all 프록시 location 이 따로 있었으므로, 폴백 블록이 그보다 **앞에** 있어야 한다. 정규식 자체가 맞아도 위치가 뒤면 아무 일도 안 한다.

수정 자체는 한 줄이었다. 검증은 기계로 했다 — 백엔드의 `/admin` 매핑 전부와 프론트 라우트 전부를 뽑아 새 정규식에 하나씩 대조해서, 화면인데 API 로 새는 것 0건 / API 인데 HTML 로 새는 것 0건을 확인하고 배포했다.

## 근본원인 (2) — 검사 대상과 배포 대상이 어긋나 있었다

여기서 멈추면 같은 사고가 또 난다. 진짜 문제는 규칙이 틀렸다는 게 아니라 **틀릴 수 있는 자리에 아무 검사도 없었다** 는 것이다.

앱 리포에는 폴백 규칙을 지키는 테스트가 이미 있었다. 잘 만들어져 있었고 잘 돌고 있었다. 다만 그게 보는 대상이 1번과 2번 — **운영에서 안 도는 두 벌** 이었다. 배포되는 3번은 어느 CI 도 보지 않았다.

이건 흔한 모양이다. 검사는 "리포 안의 파일" 을 기준으로 짜이고, 배포는 "런타임에 실제로 열리는 파일" 을 기준으로 돈다. 둘이 같다고 **가정** 하는 순간부터 사각지대가 생기고, subPath 는 그 가정을 조용히 깨는 대표적인 장치다.

그래서 배포 리포 쪽 가드에 규칙 두 개를 넣었다.

- **렌더된 ConfigMap 의 폴백 정규식이 앱 리포 원본과 문자열로 다르면 실패.**
- **원본을 못 읽거나 폴백 블록을 유일하게 특정하지 못하면 실패.**

두 번째가 있어야 하는 이유가 이 글의 요지에 가깝다. 대조를 못 한 경우를 그냥 넘기면, 가드는 **0건을 검사하고도 초록불을 준다.** "검사해서 통과" 와 "검사를 못 함" 이 같은 색으로 보이는 순간 그 가드는 신뢰의 근거가 아니라 착각의 근거가 된다. 그래서 실행 결과에 `대조 N건` 처럼 **검사한 건수를 항상 찍게** 했다. 0 이 보이면 초록불이어도 믿지 않는다.

가드가 제대로 무는지는 변이로 확인했다. 규칙을 사고 이전 상태로 되돌려 보고, 폴백 블록을 지워 보고, 원본 경로를 없는 곳으로 바꿔 봤다. 세 경우 모두 의도한 코드로 빨간불이 떴다. 여기까지 해야 "가드를 추가했다" 고 말할 수 있다.

### 방향은 리포 공개 범위가 결정했다

더 자연스러운 설계는 앱 리포의 기존 테스트가 배포 리포의 ConfigMap 까지 읽는 것이다. 그런데 앱 리포는 공개, 배포 리포는 비공개였다. 공개 리포를 받아오는 데는 토큰이 필요 없지만, 반대로 앱 리포 CI 가 비공개 배포 리포를 읽으려면 토큰이 필요하다. 그리고 포크에서 올라온 PR 에는 그 토큰이 내려가지 않는다.

> With the exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a forked repository.
> — [GitHub Docs, Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

토큰이 없으면 그 검사는 실패하는 게 아니라 **조용히 건너뛴다.** 방금 없앤 실패 모드를 그대로 다시 만드는 셈이다. 그래서 비공개 쪽이 공개 쪽을 받아오는 방향으로 뒀다. 받아오는 것도 파일 한 개짜리 sparse checkout 이면 충분하다.

## 그리고 곧바로, 그 원칙이 자기 자신에게 적용됐다

가드를 올린 PR 의 체크가 빨간불이었다. 3초 만에 끝났고 로그가 없었다. 코드 문제인 줄 알고 파봤더니 잡 자체가 시작되지 않은 것이었다.

> The job was not started because recent account payments have failed or your spending limit needs to be increased.

Actions 는 공개 리포에서는 무료지만([GitHub 문서](https://docs.github.com/en/billing/concepts/product-billing/github-actions): "For public repositories, GitHub Actions minutes remain free.") 비공개 리포는 과금 대상이다. 결제가 막히면서 **비공개인 배포 리포의 CI 는 열흘 넘게 한 번도 실행되지 않고 있었다.** 공개 리포들은 무료 분으로 멀쩡히 돌고 있었으니 대시보드만 봐서는 이상해 보이지 않았다.

여파는 단순한 불편이 아니다. 이번 수정 PR 도 **CI 가 한 번도 돌지 않은 채** 머지돼 운영에 나갔다. 결과적으로 배포는 정상이었지만, 그 근거는 초록불이 아니라 로컬 실행과 배포 후 실제 요청 확인이었다. 초록불을 근거로 삼았다면 근거가 없는 상태였다.

같은 실패 모드가 하루에 두 번 나온 셈이다. **실행되지 않은 검증은 통과한 검증과 겉모습이 같다.** 한 번은 대상이 어긋나서, 한 번은 아예 시작되지 않아서.

## 남는 것

- **"이 파일이 운영에서 실제로 읽히는가" 는 코드 리뷰로 알 수 없다.** 마운트 설정을 봐야 안다. 리포에 있다는 이유로 정본이라고 부르지 않는 게 낫다.
- **allowlist 규칙은 빠진 항목을 오류로 알려주지 않는다.** 목록과 실제 대상 집합을 대조하는 검사가 따로 필요하다.
- **같은 규칙의 사본이 둘 이상이면, 어느 사본이 배포되는지와 어느 사본이 검사되는지를 표로 적어 본다.** 이번 건은 그 표를 그리는 순간 답이 나왔다.
- **가드는 "몇 건을 검사했는지" 를 말해야 한다.** 말하지 않는 가드는 0건 검사와 전건 통과를 구분해 주지 않는다.
- **CI 가 초록불이 아니라 아예 안 돌고 있을 가능성을 주기적으로 확인한다.** 특히 공개·비공개 리포가 섞여 있으면 한쪽만 죽어도 전체가 건강해 보인다.

## References

- Kubernetes, *ConfigMaps* — subPath 볼륨 마운트와 업데이트 미반영. <https://kubernetes.io/docs/concepts/configuration/configmap/>
- Kubernetes, *Volumes* — `Using subPath`. <https://kubernetes.io/docs/concepts/storage/volumes/>
- nginx, *Module ngx_http_core_module* — `location` 지시자와 정규식 매칭 순서. <https://nginx.org/en/docs/http/ngx_http_core_module.html#location>
- GitHub Docs, *Using secrets in GitHub Actions* — 포크 PR 에 시크릿이 전달되지 않음. <https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets>
- GitHub Docs, *Billing for GitHub Actions* — 공개 리포 무료 분. <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
