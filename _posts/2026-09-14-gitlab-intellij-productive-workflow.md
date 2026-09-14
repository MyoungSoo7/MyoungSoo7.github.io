---
layout: post
title: "깃랩과 인텔리제이를 생산적으로 쓰는 법 — 세 개의 루프로 나눠 보기"
date: 2026-09-14 19:17:37 +0900
categories: [devops]
tags: [gitlab, intellij, jetbrains, ci-cd, merge-request, git, productivity]
---

"IDE 단축키를 더 외우면 빨라진다" 는 말은 절반만 맞다. 실제로 시간을 먹는 건
타이핑이 아니라 **맥락 전환** 과 **기다림** 이기 때문이다. 그래서 이 글은
단축키 목록이 아니라, 깃랩·인텔리제이를 쓰는 일이 실제로 놓이는 **세 개의 루프**
로 나눠서 본다.

| 루프 | 도는 주기 | 낭비의 정체 | 줄이는 도구 |
| --- | --- | --- | --- |
| ① 편집 → 커밋 | 수 분 | 커밋이 뭉쳐서 나중에 되돌리기·리뷰가 비싸짐 | 인텔리제이 부분 커밋·체인지리스트 |
| ② 커밋 → 리뷰 | 수 시간 | IDE ↔ 브라우저 왕복 (맥락 전환) | 인텔리제이 GitLab MR 도구창 |
| ③ MR → 머지 | 수 분 ~ 수십 분 | 쓸모없어진 파이프라인이 러너를 점유 | 깃랩 파이프라인 설정·`interruptible` |

세 루프는 각각 **사람 시간** · **주의력** · **기계 시간** 을 먹는다. 셋은 다른
문제이므로 해법도 다르다. 순서대로 본다.

아래 내용은 전부 JetBrains 공식 문서와 GitLab 공식 문서에서 확인한 동작만 적었다.
버전에 따라 메뉴 위치가 바뀌므로, 각 항목의 각주 링크를 자기 버전으로 열어 대조하는 걸 권한다.

---

## 루프 ① 편집 → 커밋: "커밋을 나중에 쪼갤 수는 없다"

한 파일을 고치다 보면 관련 없는 수정이 섞인다. JetBrains 문서가 이 상황을 이렇게
설명한다 — 전부 한 커밋에 넣으면 "리뷰하고, 되돌리고, 체리픽하기가 더 어려워진다"[^idea-commit].
즉 비용은 커밋하는 순간이 아니라 **나중에** 청구된다.

인텔리제이는 이걸 세 가지 다른 방식으로 푼다. 셋의 차이를 알아야 고를 수 있다.

### (1) 청크·라인 단위 부분 커밋

Commit 도구창(`Alt+0`)에서 `Ctrl+D` 로 diff 를 열고, 커밋에 넣을 **코드 청크마다
체크박스** 를 켠다. 한 청크 안에서 특정 줄만 넣고 싶으면 그 줄을 우클릭해
`Split Chunks and Include Selected Lines into Commit` 을 고른다[^idea-commit].
선택하지 않은 변경은 그대로 남아 다음 커밋으로 간다.

### (2) 체인지리스트

체인지리스트는 "아직 커밋하지 않은 로컬 변경의 묶음" 이다[^idea-changelist].
기본값은 `Changes` 하나이고, 새로 만들어 **활성(active)** 으로 지정하면 그 뒤의
변경이 전부 거기로 들어간다. diff 에서 청크 우클릭 → `Move to Another Changelist…`
로 한 파일의 변경을 서로 다른 묶음에 나눠 담을 수도 있다[^idea-commit].
작업(task) 컨텍스트를 함께 보존하는 `Track context` 옵션도 있다[^idea-changelist].

### (3) 스테이징 영역

git 의 인덱스 개념이 더 익숙하다면 `Ctrl+Alt+S` → `Version Control | Git` →
**Enable staging area** 를 켠다. JetBrains 는 이 모드의 이점을 "같은 파일의
변경을 (겹치는 변경까지 포함해) 따로 커밋하기 쉽고, 에디터에서 포커스를 옮기지
않고도 무엇이 이미 스테이지됐는지 볼 수 있다" 로 설명한다[^idea-commit].

⚠️ 이건 되돌리기 쉬운 토글이 아니다. JetBrains 문서의 문장 그대로다 —
**"스테이징 영역을 활성화하면, 기존 체인지리스트는 모두 삭제된다."**[^idea-git-settings]
둘은 같은 문제를 푸는 서로 다른 모델이라 하나를 골라야 하고, 체인지리스트에
작업을 나눠 담아 둔 상태에서 무심코 켜면 그 구분이 사라진다. 팀이 git CLI 를
섞어 쓰면 스테이징이, IDE 안에서만 돈다면 체인지리스트가 대체로 덜 놀랍다.

### 잠깐 치워두기 — shelve 와 stash 는 다르다

둘 다 "하던 걸 잠깐 치우기" 지만 만드는 주체가 다르다[^idea-shelve].

| | 만드는 주체 | 적용 위치 | 범위 |
| --- | --- | --- | --- |
| **stash** | Git 자체 | IDE 안팎 어디서나 | 커밋 안 된 변경 **전부** |
| **shelve** | 인텔리제이 | 보통 IDE 안에서 | **일부만 골라서** 가능 |

즉 "이 파일만 치우고 싶다" 는 shelve 쪽이다(`Ctrl+Shift+H` 로 다이얼로그 없이
조용히 shelve 가능). 반대로 "IDE 밖에서도 꺼내 쓸 것 같다" 면 stash 다.

shelve 에는 알아둘 만한 설정이 하나 있다 — `Version Control | Shelf` 의
**Shelve base revisions of files under Git**. 켜두면 파일의 base revision 을
함께 저장해 두었다가 적용 중 충돌이 날 때 3-way merge 에 쓴다. 꺼두면 프로젝트
히스토리에서 base 를 찾는데, 시간이 걸릴 뿐 아니라 **리베이스로 히스토리가
바뀐 경우 그 리비전 자체가 없을 수도 있다**[^idea-shelve]. 리베이스를 일상적으로
하는 팀이면 켜는 쪽이 안전하다.

### 이미 커밋한 뒤에 후회했다면

Git 도구창(`Alt+9`)의 Log 탭에서 커밋을 우클릭하면 되돌릴 길이 꽤 많다[^idea-log].

- `Interactively Rebase from Here` — 선택한 커밋 이후를 대화형 리베이스
- `Squash Commits` — 여러 커밋 합치기
- `Extract Selected Changes to Separate Commit` — 커밋에서 일부 파일만 떼어내 별도 커밋
- `Drop Selected Changes` — 커밋 전체가 아니라 그 안의 일부 변경만 버리기
- `Push All up to Here` — 아직 밀고 싶지 않은 커밋은 남기고 여기까지만 푸시

Log 탭에는 눈에 안 띄지만 체감이 큰 옵션도 있다. **Enable Git Log Indexing** 을
켜면 로그 필터링이 빨라지고, `Search Everywhere` 에서 히스토리까지 검색된다[^idea-log].

### 푸시할 때: `--force` 대신 IDE 가 하는 일

인텔리제이에서 force push 를 고르면 실제로 실행되는 건 `git push --force` 가
아니라 **`git push --force-with-lease`** 다. JetBrains 는 이를 "남의 커밋을
덮어쓰지 않도록 보장해 주는 더 안전한 선택지" 라고 설명한다[^idea-commit].
CLI 에서 손으로 `--force` 를 치는 것과 IDE 버튼을 누르는 게 같은 동작이 아니라는
뜻이다 — 이건 알아둘 가치가 있다.

프로젝트 업데이트 방식(`Merge` / `Rebase`)과, 그때 커밋 안 된 변경을 `Stash` 로
치울지 `Shelve` 로 치울지도 `Version Control | Git` 에서 미리 정해둘 수 있다[^idea-git-settings].
`Warn when committing in detached HEAD or during rebase` 도 같은 화면에 있다 —
"코드 유실을 일으킬 수 있다" 는 경고가 붙어 있는 옵션이다[^idea-git-settings].

---

## 루프 ② 커밋 → 리뷰: 브라우저를 열지 않는다

여기가 깃랩+인텔리제이 조합에서 가장 크게 절약되는 지점이다. 리뷰는 **읽는 일**
인데, 코드를 가장 잘 읽는 도구는 브라우저의 diff 뷰가 아니라 IDE 이기 때문이다.

### MR 목록을 IDE 안에서 연다

메인 메뉴 `Git | GitLab | View Merge Requests` 를 고르면 Merge Requests 도구창이
열린다[^idea-mr-view]. 상태·작성자·담당자·리뷰어·레이블로 필터링할 수 있고,
목록의 MR 을 우클릭하면 다음이 나온다.

- `Open Merge Request on GitLab` — 굳이 브라우저가 필요할 때만
- `Checkout 'branch name'` — 그 브랜치를 바로 체크아웃
- `Show 'branch name' in Git Log`

### 리뷰 모드 — diff 가 아니라 "코드" 를 읽는다

MR 브랜치를 체크아웃하면 인텔리제이가 **Review mode** 로 들어간다. 이때
변경과 코멘트가 **에디터 안에서** 하이라이트된다[^idea-mr-view]. 이게 브라우저
리뷰와 결정적으로 다른 부분이다 — 리뷰 중에 `F4`(Jump to Source)로 호출부로
건너뛰고, `Ctrl+D` 로 diff 를 보고, 평소 쓰던 **Find Usages·타입 정보·네비게이션이
그대로 동작한다**. 브라우저 diff 에서는 "이 함수를 다른 데서도 이렇게 부르나?"
를 확인할 방법이 없다. 리뷰 품질이 올라가는 건 이 차이에서 온다.

### 코멘트: 즉시 알림 vs 초안

거터의 코멘트 아이콘을 누르면 두 가지가 나온다[^idea-mr-view].

- **Add Comment** — 작성 즉시 작성자에게 알림이 간다
- **Save as draft** — 초안으로 모아 뒀다가 한 번에 제출

리뷰를 훑으며 코멘트 12개를 다는 상황이라면, 12번 알림을 보내는 것과 리뷰를
끝내고 한 번 보내는 것은 **받는 사람의 루프 ①을 12번 깨느냐 한 번 깨느냐** 의
차이다. 초안 쪽을 기본값으로 삼을 이유가 충분하다.
MR 전체에 대한 코멘트는 타임라인 뷰에서 단다[^idea-mr-view].

### 승인·머지도 IDE 안에서

`Submit Review` 를 누르면 **Approve** 또는 **Submit** 을 고를 수 있고, 이미 한
승인은 **Revoke Approval** 로 취소할 수 있다[^idea-mr-view]. 머지는
`Merge` 또는 `Squash and Merge` 이며, `More` 아래에 `Request Review` 와
`Close Merge Request` 가 있다[^idea-mr-create].

MR 생성도 같은 도구창 우상단의 `Create Merge Request` 버튼으로 한다[^idea-mr-create].
여기서 한 가지 함정 — **"Squash commits before merging" 체크박스의 동작은 깃랩
프로젝트 설정에 달려 있다.** 프로젝트의 `Settings | Merge requests` 에서 squash
정책을 어떻게 뒀느냐에 따라 이 체크박스가 켜져 있는지, 아예 못 바꾸는지가 갈린다[^idea-mr-create].
IDE 쪽만 보고 "왜 체크가 안 먹지?" 하고 헤매기 쉬운 자리다.

계정 연결과 기타 설정은 `Version Control | GitLab` 에 있다 — `Add account`,
`Automatically mark opened files as viewed`, `Clone using SSH`[^idea-gitlab-settings].
중간 크기 이상의 MR 이라면 "연 파일을 자동으로 viewed 처리" 는 켜두는 편이
어디까지 봤는지 추적하기 쉽다.

### GitLab Duo 플러그인 — 설치 전에 볼 것

깃랩의 AI 기능을 JetBrains IDE 에서 쓰려면 별도 플러그인이 필요하고, 전제 조건이
있다: **JetBrains IDE 2023.2.X 이상, GitLab 16.8 이상**[^duo-setup]. 설정 위치는
`Settings > Tools > GitLab Duo` 이고, 인증은 세 가지다 — GitLab.com 은 **OAuth**,
Self-Managed/Dedicated 는 **개인 액세스 토큰(PAT)**, 그리고 **1Password CLI**[^duo-setup].
Self-Managed 에서 인스턴스 전체 OAuth 를 쓰려면 플러그인 **3.30.30 이상** 이
필요하다[^duo-setup].

⚠️ 그리고 이건 진짜 함정이다 — **JetBrains Remote Development 를 쓴다면 플러그인을
호스트(원격 서버)에만 설치해야 한다. 클라이언트 쪽에도 같이 설치하면 GitLab Duo
기능이 동작을 멈춘다**[^duo-setup]. 원격 개발 환경에서 "왜 안 되지" 로 시간을
태우기 딱 좋은 자리이고, 증상이 에러가 아니라 **조용한 무반응** 이라 더 그렇다.

플러그인이 프로젝트를 특정하지 못할 때 쓰는 **Default Namespace** 설정도 있다[^duo-setup].
모노레포거나 origin 이 여러 개인 프로젝트라면 먼저 확인할 값이다.

---

## 루프 ③ MR → 머지: 여기서 낭비되는 건 기계 시간이다

루프 ①·② 를 아무리 조여도, MR 을 올린 뒤 파이프라인을 20분 기다리면 의미가 없다.
그리고 그 20분의 상당 부분은 **이미 쓸모없어진 작업** 인 경우가 많다.

### 중복 파이프라인부터 끈다

커밋 A·B·C 를 빠르게 연달아 밀면 A·B 의 파이프라인 결과는 C 가 나온 순간
무의미해진다. 깃랩은 이걸 프로젝트 설정에서 끌 수 있다 —
`Settings > CI/CD > General pipelines > Auto-cancel redundant pipelines`[^gl-pipeline-settings].

세밀하게 제어하려면 `.gitlab-ci.yml` 쪽이다. `workflow:auto_cancel:on_new_commit`
값은 셋이다[^gl-yaml]:

- `conservative` — **정의하지 않았을 때의 기본값.** `interruptible: false` 인 잡이
  아직 시작하지 않았을 때만 파이프라인을 취소한다
- `interruptible` — `interruptible: true` 인 잡만 취소
- `none` — 아무것도 취소하지 않음

```yaml
workflow:
  auto_cancel:
    on_new_commit: interruptible
    on_job_failure: all
  rules:
    - if: $CI_COMMIT_REF_PROTECTED == 'true'
      auto_cancel:
        on_new_commit: none
        on_job_failure: none
    - when: always
```

이 예시는 평소엔 공격적으로 취소하되, **보호 브랜치 파이프라인은 취소하지 않는다**[^gl-yaml].
`on_job_failure: all` 은 잡 하나가 실패하는 즉시 나머지 러닝 잡을 전부 취소한다 —
어차피 실패할 파이프라인에 러너를 붙잡아 두지 않겠다는 뜻이다.

잡 단위 스위치는 `interruptible` 이고, **정의하지 않으면 기본값은 `false`** 다[^gl-yaml].
그래서 배포 잡은 대개 그대로 두는 게 맞다 — 취소되면 **부분 배포** 가 남는다.

### 브랜치 파이프라인과 MR 파이프라인이 겹칠 때

MR 이 열려 있는 브랜치에 푸시하면 깃랩은 기본적으로 **브랜치 파이프라인과 MR
파이프라인을 둘 다** 만들려고 한다. 자원이 두 배로 나가고, 어느 쪽이 머지 가능
판정인지 헷갈린다[^gl-pipeline-settings]. `Settings > CI/CD > General pipelines >
Skip branch pipelines for merge requests` 로 끈다.

켰을 때 알아둘 것[^gl-pipeline-settings]:

- `Pipelines must succeed` 같은 머지 판정은 **MR 파이프라인만** 본다
- MR 을 만드는 **첫 푸시에는 브랜치 파이프라인이 그래도 생긴다** (MR 생성 전에
  파이프라인이 시작되기 때문). 그다음 푸시부터 스킵된다
- ⚠️ **파이프라인이 브랜치 파이프라인만 돌도록 구성돼 있으면, 이걸 켜는 순간
  MR 에 파이프라인이 아예 안 돈다**

### 머지 트레인 — 쓸지 말지의 기준

"각자 파이프라인은 통과했는데 합치니 깨졌다" 는 문제가 있다. 깃랩 문서의 설명이
정확하다 — merged results 파이프라인은 **그 MR 하나와 타깃 브랜치의 결합** 만
검증하고, 비슷한 시기에 머지되는 다른 MR 은 고려하지 않는다. 그래서 두 MR 이
각자 통과하고도 결합 결과는 충돌할 수 있고, 둘 다 머지되면 모든 파이프라인이
성공했는데도 타깃 브랜치가 깨진다[^gl-merge-trains].

머지 트레인은 각 MR 을 **앞선 MR 들의 결합 결과** 와 함께 테스트해서 이걸 막는다.
깃랩이 명시한 도입 기준은 이렇다[^gl-merge-trains]:

- 기본 브랜치로 머지가 잦다
- 비슷한 시기에 머지 준비되는 MR 이 여럿이다
- 기본 브랜치 파이프라인이 **항상** 통과해 있어야 한다

세 조건에 안 걸리면 트레인은 복잡도만 늘린다. 도입했다면 다음도 알아야 한다.

- 트레인당 **동시 파이프라인 기본 상한은 20개**, 초과분은 대기(대기열 자체는 무제한)[^gl-merge-trains]
- 트레인 파이프라인이 **실패하면 그 MR 은 트레인에서 빠지고, 뒤에 줄 서 있던
  MR 들의 파이프라인이 전부 새로 시작된다**[^gl-merge-trains]
- **실패한 트레인 파이프라인은 재시도할 수 없다.** 머지된 결과 자체가 낡았기
  때문이다. 다시 트레인에 넣거나(새 파이프라인), 간헐적 실패라면 잡에 `retry`
  키워드를 붙인다 — 재시도로 성공하면 MR 이 트레인에서 빠지지 않는다[^gl-merge-trains]
- `Merge immediately` 는 **다른 MR 들의 트레인 파이프라인을 전부 취소하고 트레인을
  새로 시작시킨다.** 깃랩 문서도 "CI/CD 자원을 많이 쓸 수 있으니 위급할 때만" 이라고
  적고 있다[^gl-merge-trains]

### `.gitlab-ci.yml` 은 밀기 전에 검증한다

CI 설정의 오타를 파이프라인 실패로 배우는 건 가장 느린 피드백이다. 깃랩은
`.gitlab-ci.yml` 을 편집할 때 **CI Lint 도구로 검증할 수 있다** 고 안내한다[^gl-yaml].
푸시 → 실패 → 수정 → 푸시 루프를 한 단계로 줄이는 가장 값싼 방법이다.

잡 간 순서를 스테이지에 묶어두는 대신 `needs` 로 DAG 를 만들면 **스테이지 순서보다
먼저 실행** 시킬 수 있고, `cache` 와 `artifacts` 는 목적이 다르다 — 전자는 실행
간 재사용, 후자는 잡 완료 시 첨부이며 `dependencies` 로 어느 잡의 아티팩트를
받을지 제한한다[^gl-yaml]. 파이프라인이 느리다면 이 세 키워드부터 본다.

---

## 정리하면

세 루프를 각각 한 줄로 줄이면 이렇다.

1. **커밋은 나중에 못 쪼갠다** → 부분 커밋·체인지리스트(또는 스테이징 영역) 중
   하나를 팀 표준으로 정한다. 둘은 동시에 못 쓴다.
2. **리뷰는 읽는 일이다** → MR 을 IDE 에서 체크아웃해 Review mode 로 읽고,
   코멘트는 초안으로 모아 한 번에 보낸다.
3. **기다림의 상당 부분은 이미 쓸모없는 작업이다** → 중복 파이프라인 취소와
   `interruptible` 부터 손본다. 머지 트레인은 조건에 맞을 때만.

이 글에서 제일 조심해야 할 항목 하나만 꼽으라면, **Remote Development 에서
GitLab Duo 플러그인을 클라이언트에도 설치하면 기능이 죽는다**[^duo-setup] 는 것이다.
에러가 아니라 무반응으로 나타나기 때문에 원인에 도달하기까지 가장 오래 걸린다.

### 근거의 한계

이 글의 모든 동작 서술은 **벤더 1차 문서**(JetBrains·GitLab 공식 docs) 기준이며,
필자가 모든 항목을 각 버전에서 재현 측정한 것은 아니다. 특히 다음은 환경에 따라
달라진다.

- 메뉴 경로와 단축키는 IDE 버전·키맵에 따라 다르다
- 머지 트레인의 일부 동작은 **에디션(Premium/Ultimate)과 기능 플래그** 에 걸린다.
  예컨대 "트레인을 재시작하지 않고 즉시 머지" 는 Self-Managed 에서
  `merge_trains_skip_train` 플래그로 관리자가 숨길 수 있다[^gl-merge-trains]
- 생산성 향상폭에 대한 **중립적 제3자 측정치는 인용하지 않았다.** 그런 수치를
  신뢰할 만한 형태로 찾지 못했기 때문이고, 여기 적힌 건 "무엇이 어떻게 동작하는가"
  이지 "얼마나 빨라지는가" 가 아니다

같은 맥락의 이전 글: [깃허브와 깃랩, 러너는 어디에 사는가]({% post_url 2026-09-10-github-vs-gitlab-where-the-runner-lives %})

---

## References

[^idea-mr-view]: JetBrains, "Work with GitLab merge requests | IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/work-with-gitlab-merge-requests.html>
[^idea-mr-create]: JetBrains, "Create and merge GitLab merge requests | IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/create-and-merge-gitlab-merge-requests.html>
[^idea-gitlab-settings]: JetBrains, "GitLab | Settings | Version Control — IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/settings-version-control-gitlab.html>
[^idea-commit]: JetBrains, "Commit and push changes to Git repository | IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/commit-and-push-changes.html>
[^idea-changelist]: JetBrains, "Group changes into changelists | IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/managing-changelists.html>
[^idea-shelve]: JetBrains, "Shelve or stash changes | IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/shelving-and-unshelving-changes.html>
[^idea-log]: JetBrains, "Log tab | IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/log-tab.html>
[^idea-git-settings]: JetBrains, "Git | Settings | Version Control — IntelliJ IDEA Documentation". <https://www.jetbrains.com/help/idea/settings-version-control-git.html>
[^duo-setup]: GitLab, "Install and set up the GitLab plugin for JetBrains IDEs". <https://docs.gitlab.com/editor_extensions/jetbrains_ide/setup/>
[^gl-merge-trains]: GitLab, "Merge trains | GitLab Docs". <https://docs.gitlab.com/ci/pipelines/merge_trains/>
[^gl-pipeline-settings]: GitLab, "Customize pipeline configuration | GitLab Docs". <https://docs.gitlab.com/ci/pipelines/settings/>
[^gl-yaml]: GitLab, "CI/CD YAML syntax reference | GitLab Docs". <https://docs.gitlab.com/ci/yaml/>
