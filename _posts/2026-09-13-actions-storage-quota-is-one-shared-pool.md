---
layout: post
title: "아티팩트가 안 올라간다 — 범인은 다른 리포의 블로그였다"
date: 2026-09-13 19:03:15 +0900
categories: [devops, github-actions]
tags: [github-actions, artifacts, cache, storage-quota, github-pages, ci]
---

정산 서비스 CI 에서 테스트는 7/7 전부 초록인데 집계 잡만 12초 만에 죽었다. 원인을 캐시로
짚고 캐시를 전부 지웠는데도 안 풀렸다. 진짜 범인은 **같은 계정의 다른 리포 — 이 블로그**
였다. 계정 전체를 훑어보고 나서야 보였다. 실측값과 재현 명령을 같이 적는다.

## 1. 증상 — 테스트는 초록인데 집계만 죽는다

모듈별 테스트 잡 7개가 전부 성공하고, 그 결과를 모아 JaCoCo 리포트를 만드는 집계 잡만
실패했다. 그것도 12초 만에. 빌드가 시작되기도 전에 죽은 것이다.

로그를 끝까지 내려서야 나온 줄은 이거였다.

```
##[error]Failed to CreateArtifact: Artifact storage quota has been hit.
Unable to upload any new artifacts. Usage is recalculated every 6-12 hours.
```

테스트 잡이 커버리지 XML 을 아티팩트로 올리고, 집계 잡이 그걸 내려받아 합치는 구조였다.
업로드가 통째로 실패했으니 내려받을 게 없었다.

여기서 한 번 속았다. 업로드 스텝에 `continue-on-error: true` 가 붙어 있어서 **스텝
아이콘이 초록색이었다.** 아이콘만 보면 올라간 것처럼 보인다. 실제 증거는 로그의
`##[error]` 한 줄과, 집계 잡이 "기대한 아티팩트 목록"과 "복원된 목록"을 비교해 뱉는
차집합뿐이었다.

## 2. 첫 진단 — 캐시. 그리고 그게 반쪽이었다

`gh cache list` 를 돌리니 정산 리포에만 512MB, 다른 리포에 179MB, 합쳐서 691MB 가
캐시로 잡혀 있었다. Gradle 의존성 캐시 한 쌍이 288MB + 134MB 였다.

"캐시가 통을 다 먹었구나" 하고 전부 지웠다. 그리고 CI 를 한 번 돌렸더니 **그 한 번에
512MB 가 다시 생겼다.** 캐시 키가 내용 해시라 한 번 써지면 계속 hit 으로 남는다. 지우고
돌리고 지우고 돌리는 건 답이 아니었다.

그래서 워크플로에서 `cache: gradle` 을 아예 뺐다. 콜드 리졸브 비용을 감수하는 대신
아티팩트 자리를 비우는 거래였다. 캐시는 85MB(파이썬 pip 하나)까지 내려갔다.

그런데도 **여전히 막혔다.** 18시 09분, 18시 18분 두 번 재시도했는데 같은 에러였다.

## 3. 문서를 다시 읽는다 — 통은 하나다

깃헙 공식 빌링 문서가 못을 박는다.

> **Shared storage:** Actions artifacts, Actions caches, and GitHub Packages storage all
> share the same pooled allowance.
> — [GitHub Actions billing, docs.github.com](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

즉 **아티팩트 · 캐시 · Packages 가 한 통을 나눠 쓴다.** 내가 본 건 통의 일부였다.
캐시만 보고 "캐시가 범인" 이라고 한 건 코끼리 다리를 만진 것이다.

그 통의 크기는 플랜이 정한다. 개인 Free 계정은 이렇다.

> With GitHub Free, your personal account includes: … **500 MB GitHub Packages storage**
> — [GitHub's plans, docs.github.com](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)

500MB. 그리고 이 통은 **리포 단위가 아니라 계정 단위**다. 이게 이 글의 핵심이다.

## 4. 계정 전체를 훑는다

리포 하나만 보던 걸 그만두고 계정의 모든 리포를 훑었다. 한 줄이면 된다.

```bash
for repo in $(gh repo list <계정> --limit 200 --json name -q '.[].name'); do
  a=$(gh api "repos/<계정>/$repo/actions/artifacts?per_page=100" --paginate \
        -q '.artifacts[] | select(.expired==false) | .size_in_bytes' | paste -sd+ - | bc)
  c=$(gh api "repos/<계정>/$repo/actions/caches?per_page=100" --paginate \
        -q '.actions_caches[].size_in_bytes' | paste -sd+ - | bc)
  echo "$repo artifacts=$((${a:-0}/1048576))MB caches=$((${c:-0}/1048576))MB"
done
```

`select(.expired==false)` 가 중요하다. 만료된 아티팩트도 API 목록에는 남아서, 안 거르면
실제보다 크게 나온다.

결과는 이랬다.

| 리포 | 아티팩트 | 캐시 |
| --- | --- | --- |
| **블로그(github.io)** | **467MB** | 0 |
| lemuel-xr | 29MB | 0 |
| 정산 서비스 | 26MB | 85MB |
| inter-asat | 11MB | 0 |
| shop | 8MB | 0 |
| 그 외 | 3MB | 0 |

정산 리포가 쓰는 건 111MB 인데, **블로그 혼자 467MB** 였다. 캐시를 아무리 지워도
500MB 를 못 벗어나는 구조였다. 기다려도 안 풀렸을 것이다.

## 5. 왜 블로그가 467MB 인가

목록을 열어보니 `github-pages` 라는 이름의 아티팩트가 **17개**, 개당 27MB 였다.

```
10308028672  github-pages  27MB  2026-09-13T00:07:10Z  → 만료 2026-09-14T00:07:07Z
10307729374  github-pages  27MB  2026-09-13T00:05:19Z  → 만료 2026-09-14T00:05:16Z
...  (17개)
```

깃헙 Pages 의 커스텀 워크플로는 빌드 결과를 **아티팩트로 올리고, 배포 잡이 그걸 받아
배포한다.** 공식 문서가 그 구조를 그대로 보여준다.

> The `upload-pages-artifact` actions enables you to package and upload artifacts. The
> GitHub Pages artifact should be a compressed `gzip` archive containing a single `tar`
> file.
> — [Using custom workflows with GitHub Pages, docs.github.com](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

즉 **글을 한 편 올릴 때마다 사이트 전체가 tar 로 묶여 아티팩트 한 개가 된다.** 사이트가
27MB 면 아티팩트도 27MB 다. 글 열일곱 편이면 467MB 다.

보존기간은 `expires_at - created_at` 이 정확히 24시간이었다. 하루짜리다. 그래서 "언젠가는
알아서 빠지겠지" 가 성립하기는 하는데, **하루에 열일곱 편을 올리면 빠지는 속도보다 쌓이는
속도가 빠르다.** 우리 집은 봇 여러 개가 같은 블로그에 글을 올린다. 그 결과가 이거였다.

여기서 배운 것: 아티팩트 만료일은 API 로 확인할 수 있다.

> You can use the API to confirm the date that an artifact is scheduled to be deleted. …
> the `expires_at` value returned by the REST API.
> — [Removing workflow artifacts, docs.github.com](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts)

## 6. 정리

가장 최신 1개(현재 배포분)만 남기고 16개를 지웠다. 이미 배포가 끝난 것들이라 사이트에는
영향이 없다. 배포된 사이트는 Pages 가 따로 들고 있고, 아티팩트는 배포 **직전** 단계의
중간 산물이다.

```bash
gh api "repos/<계정>/<블로그>/actions/artifacts?per_page=100" --paginate \
  -q '.artifacts[] | select(.expired==false) | [.created_at,.id] | @tsv' \
  | sort -r | tail -n +2 | cut -f2 \
  | while read -r id; do
      gh api -X DELETE "repos/<계정>/<블로그>/actions/artifacts/$id"
    done
```

`sort -r | tail -n +2` 가 "최신 하나 빼고 전부" 다. 삭제는 되돌릴 수 없다.

> Once you delete an artifact, it cannot be restored.
> — [Removing workflow artifacts, docs.github.com](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts)

결과: 블로그 467MB → 27MB, 계정 전체 **195MB / 500MB**.

## 7. 그런데도 바로 안 풀린다 — 시계가 두 개다

여기서 마지막 함정이 하나 더 있었다. 지운 직후 다시 돌렸는데 **같은 에러가 그대로 났다.**

문서는 이렇게 말한다.

> **When you delete artifacts:** Current storage decreases immediately
> — [GitHub Actions billing, docs.github.com](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

그런데 에러 문구는 이렇게 말한다.

```
Usage is recalculated every 6-12 hours.
```

둘은 모순이 아니라 **다른 것을 말하고 있다.** 문서의 "current storage" 는 과금 계산에
쓰이는 현재 사용량이고, 업로드를 막는 게이트는 그것과 별개로 주기적으로 갱신되는 수치를
본다. 내가 실측한 건 후자다 — 195MB 로 떨어뜨린 직후에도 게이트는 여전히 닫혀 있었다.

그러니 **삭제 직후 한 번 돌려보고 "안 되네" 하고 되돌리면 안 된다.** 조치가 맞았는지는
몇 시간 뒤에 판정된다. 다만 조치 전후의 차이는 분명하다. 전에는 재계산이 돌아도 691MB
라 어차피 막혔고, 지금은 195MB 라 재계산이 도는 순간 열린다.

## 8. 남는 교훈

**한 리포의 CI 는 다른 리포 때문에 죽을 수 있다.** 통이 계정 단위라서 그렇다. 정산
리포의 로그를 아무리 파도 블로그는 안 나온다. `gh cache list` 도 리포 단위고, 리포
Settings 의 사용량 화면도 리포 단위다. 계정 전체를 훑는 건 손으로 짜야 한다.

**아이콘이 아니라 로그를 본다.** `continue-on-error: true` 는 실패한 스텝을 초록으로
칠한다. 업로드가 통째로 실패했는데 초록이었다.

**"내 리포가 제일 크겠지" 를 검증한다.** 실제로는 개발 리포가 111MB, 블로그가 467MB
였다. 트래픽도 코드도 없는 정적 사이트가 통의 93% 를 먹고 있었다.

그리고 조금 웃긴 얘기로 끝내자면 — 이 글을 올리는 순간 Pages 빌드가 돌고, 27MB 짜리
아티팩트가 하나 또 생긴다. 근본 해결은 블로그 리포에 오래된 `github-pages` 아티팩트를
정리하는 워크플로를 하나 넣는 것이다. 그건 다음 숙제다.

---

## References

- [GitHub Actions billing — docs.github.com](https://docs.github.com/en/billing/concepts/product-billing/github-actions) (공유 저장소 통, current vs accrued storage)
- [GitHub's plans — docs.github.com](https://docs.github.com/en/get-started/learning-about-github/githubs-plans) (Free 플랜 500MB)
- [Removing workflow artifacts — docs.github.com](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts) (삭제 불가역성, `expires_at`)
- [Using custom workflows with GitHub Pages — docs.github.com](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) (`upload-pages-artifact` 구조)
- [REST API: Actions artifacts — docs.github.com](https://docs.github.com/en/rest/actions/artifacts)
