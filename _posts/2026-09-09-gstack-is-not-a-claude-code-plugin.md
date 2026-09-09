---
layout: post
title: "gstack은 클로드코드 '플러그인'이 아니다 — 132k 스타 스킬 번들을 통째로 깔지 않고 미식(味識)한 기록"
date: 2026-09-09 12:25:00 +0900
categories: [claude-code, ai, tooling]
tags: [claude-code, gstack, plugin, marketplace, skill-md, cross-model-review, codex]
---

![gstack 미식 세션 요약 — cross-model-review 스킬과 /codex-review·/health·/canary·/diagram 도입, findings 6건(합의 3·Codex 단독 1·Claude 단독 2)](/assets/images/gstack-tasting-cross-model-review.jpg)
*내 스택에 gstack 을 "통째로" 깔지 않고 *없는 것만* 가져온 세션의 결과 요약. 도입한 것은 cross-model-review 스킬과 `/codex-review`·`/health`·`/canary`·`/diagram`, 그리고 첫 실행에서 나온 findings 6건 — 합의 3 · Codex 단독 1 · Claude 단독 2.*

나는 이 물건을 계속 "클로드코드 플러그인 gstack" 이라고 불러 왔다. 그런데 도입 직전에 규격을 확인해 보니, **gstack 은 Claude Code 의 플러그인 규격을 쓰지 않는다.** 이름표 하나 틀린 정도의 문제가 아니라 — 설치 경로, 이름 충돌, 업데이트 핀, 설치 전 검수 표면이 전부 달라진다.

이 글은 (1) 그 사실을 실측으로 확인한 기록, (2) 그래서 실무에서 뭐가 달라지는지, (3) 통째 설치 대신 *없는 것만 가져오는* 도입 방식과 그 첫 실행 결과다.

---

## 1. 실측 — 2026-09-09 기준 `garrytan/gstack`

추정이 아니라 GitHub REST API 로 그날 값을 직접 받았다.

```bash
curl -sS https://api.github.com/repos/garrytan/gstack
curl -sS https://api.github.com/repos/garrytan/gstack/git/trees/main?recursive=1
```

| 항목 | 실측값 |
| --- | --- |
| 스타 / 포크 | 132,170 / 19,780 |
| 라이선스 | MIT |
| 기본 브랜치 | `main` |
| `VERSION` 파일 | `1.81.0.0` |
| 마지막 push | 2026-09-09T02:48:45Z |
| 리포 전체 blob | 1,553 개 |
| `SKILL.md` 파일 | **65 개** |
| 최상위 스킬 디렉터리 | **56 개** (+ 루트에 라우터 `SKILL.md` 1개) |
| `bin/` 실행파일 | **83 개** |
| `.claude-plugin/` | **없음** (API 404) |

리포 한 줄 설명은 아직 "23 opinionated tools" 인데, 트리에서 센 스킬 디렉터리는 56 개다.[^1] 성장 속도가 설명문을 앞질렀다고 보는 게 맞겠다.

그리고 마지막 줄이 이 글의 출발점이다. `.claude-plugin/` 디렉터리가 리포 어디에도 없다.

## 2. Claude Code 에서 "플러그인" 은 규격이 있는 말이다

공식 문서 기준으로 플러그인은 *자체 완결된 디렉터리* 이고, 그 정체성은 `.claude-plugin/plugin.json` 매니페스트가 정의한다. 배포는 `.claude-plugin/marketplace.json` 카탈로그를 통한다.[^2][^3]

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json     ← 여기에만 매니페스트
├── skills/             ← 나머지는 전부 플러그인 루트
├── agents/
├── hooks/
└── bin/
```

이 규격을 타면 따라오는 것들이 있다.

- **네임스페이스.** 플러그인의 스킬은 `/plugin-name:hello` 로 접두된다. 스탠드얼론 `.claude/` 스킬은 `/hello` 그대로다.[^2]
- **버전 핀.** `plugin.json` / 마켓플레이스 엔트리의 `version` 이 있으면 그 값이 바뀔 때만 업데이트가 내려간다. 없으면 커밋 SHA 로 떨어진다.[^3]
- **설치 전 인벤토리.** `/plugin` 상세 화면이 **Will install** 목록(commands·agents·skills·hooks·MCP·LSP)과 **Context cost** 추정치를 보여 준다.[^4]
- **설치 스코프.** user / project / local 중 선택. project 스코프는 `.claude/settings.json` 의 `enabledPlugins` 에 들어가 팀 전체에 공유된다.[^4]

gstack 의 설치법은 이 경로가 아니다. README 가 지시하는 것은 clone 이다.[^1]

```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git \
  ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup
```

즉 gstack 은 **`~/.claude/skills/` 아래에 통째로 떨어지는 스킬 번들**이다. 참고로 공식 문서에는 "스킬 디렉터리 아래 폴더에 `.claude-plugin/plugin.json` 이 있으면 `@skills-dir` 플러그인으로 로드된다" 는 경로도 있는데[^3], gstack 에는 그 매니페스트가 없으므로 이쪽에도 해당하지 않는다.

### 플러그인화는 시도됐고, main 에 안 들어갔다

흥미로운 건 이게 논의조차 없던 얘기가 아니라는 점이다. 2026-03-12 에 외부 기여자가 정확히 그 작업을 한 커밋이 리포에 남아 있다 — `1adf401`, "feat: install gstack from Claude Code marketplace". `.claude-plugin/` 매니페스트 2개를 추가하고, 스킬을 `skills/` 아래로 옮기고, 경로를 `${CLAUDE_SKILL_DIR}` 로 바꾸고, 이제 불필요해진 `setup` 스크립트를 지우는 내용이다.[^5]

그 커밋과 현재 `main` 을 비교하면:

```bash
curl -sS https://api.github.com/repos/garrytan/gstack/compare/1adf401e...main
# → status: "diverged", ahead_by: 385, behind_by: 1
```

`behind_by: 1` — 저 커밋의 고유 커밋 1개는 끝내 `main` 에 들어가지 않았다. 6개월 뒤인 지금도 설치법은 여전히 clone 이다.

한 걸음 더. Anthropic 커뮤니티 마켓플레이스 카탈로그(`anthropics/claude-plugins-community`)를 받아 보면 등록 플러그인이 2,282 개인데, **gstack 은 그 안에 없다.** 대신 걸리는 건 파생물 하나다 — `jarvis-plan-review`, 설명에 "Adapted from gstack `/plan-ceo-review`" 라고 적혀 있다.[^6]

생태계는 이미 gstack 을 *설치* 가 아니라 *번안* 으로 소비하고 있다는 뜻이다. 이게 다음 절의 근거가 된다.

## 3. 그래서 실무에서 뭐가 달라지나

플러그인이냐 스킬 번들이냐는 취향 문제가 아니다. 내 스택에 이미 40개 넘는 자체 스킬(`/힙`, `/그림`, `/깃블` 같은 한글 명령 포함)이 있는 상태에서 56개 스킬을 평평한 이름으로 같은 공간에 부으면 다음이 걸린다.

**① 이름 공간이 평평하다.** 플러그인이면 `/gstack:review` 로 격리되지만, 스킬 번들은 `/review`·`/ship`·`/health`·`/test` 같은 흔한 이름을 그대로 전역에 올린다. 내 `/health` 와 gstack 의 `health/` 는 같은 이름을 두고 경쟁한다.

**② 업데이트가 마켓플레이스 핀이 아니다.** `--depth 1` clone 이라 히스토리가 없고, 갱신은 gstack 자체 명령 `/gstack-upgrade` 가 맡는다. 플러그인 쪽의 버전/SHA 핀과 달리 "지금 내 디스크의 gstack 이 어느 지점인가" 는 `VERSION` 파일을 직접 읽어야 안다.

**③ 설치 전에 보여 주는 화면이 없다.** 플러그인은 설치 전 Will install 인벤토리와 컨텍스트 비용을 띄운다.[^4] clone 은 그런 게 없다. 그런데 이 번들에는 `bin/` 실행파일 83개가 들어 있고, README 는 Stop 훅(`gstack-verify-gate`)도 안내한다 — gstack 스스로 "훅은 권한 시스템을 우회하므로 리포당 한 번 신뢰를 명시해야 하고, `./setup` 은 절대 자동 등록하지 않는다" 고 못 박아 둔 물건이다.[^1] 설계는 조심스럽지만, **그 조심스러움을 읽어야 아는 형태**로 온다.

**④ 컨텍스트를 상시 점유한다.** 세션 시작 시 harness 는 모든 SKILL.md 의 frontmatter(name + description)를 읽어 available-skills 로 주입한다. 65개가 늘면 매 턴 그만큼이 얹힌다. (이건 내 관측 기반 추정이지 벤더가 수치로 공표한 값은 아니다.)

## 4. 그래서 통째로 깔지 않았다 — "없는 것만" 미식

세 가지 선택지가 있었다. ① 통째 설치, ② 없는 것만 가져오기, ③ 안 함. 고른 것은 **②** 다. 위 스크린샷의 "gstack 미식(옵션 2 — 없는 것만)" 이 그 결정이다.

가져온 것은 넷이다.

| 도입 | gstack 쪽 대응물 | 내가 없던 이유 |
| --- | --- | --- |
| `cross-model-review` 스킬 | `/codex` (Second Opinion) | 리뷰가 전부 단일 모델이었다 |
| `/codex-review` | `/codex` review 모드 | 합의/불일치를 구분해 본 적이 없다 |
| `/health` | `health/` | 배포 후 상태 확인이 손 명령이었다 |
| `/canary` | `canary/` | 배포 직후 감시 루프가 없었다 |
| `/diagram` | `diagram/` | 클러스터 그림은 있었지만 코드 구조 그림이 없었다 |

가져오지 않은 것이 더 많다. `/office-hours`·`/plan-ceo-review` 같은 제품 게이트는 [예전 글](/2026/07/22/garry-tan-gstack-perspectives/)에서 gstack 의 제1 기여라고 썼지만, 1인 운영에 CEO 롤플레이를 얹는 건 내 병목이 아니었다. `/browse` 계열도 뺐다 — 이미 브라우저 경로가 있다.

### 첫 실행 결과 — 단독 findings 가 절반이었다

`/codex-review` 첫 실행에서 나온 findings 는 6건. 내역은 **합의 3 · Codex 단독 1 · Claude 단독 2** 다(스크린샷).

두 모델이 낸 지적 집합을 각각 $C$(Claude), $X$(Codex) 라 하면 $|C \cap X| = 3$, $|C| = 5$, $|X| = 4$, $|C \cup X| = 6$ 이므로

$$J(C, X) = \frac{|C \cap X|}{|C \cup X|} = \frac{3}{6} = 0.5$$

읽어야 할 숫자는 "합의 3건" 이 아니라 **단독 3건** 이다. 어느 한 모델만 돌렸다면 지적의 절반을 못 봤다는 뜻이고, 이건 교차 검증을 도입한 이유 그 자체다. 다만 이 수치는 **한 리포·한 diff·1회 관측**이다. 모델 우열의 근거로 쓸 수 있는 값이 아니고, 표본이 이 정도면 임계치의 오탐도 드러나지 않는다.

## 5. 한계 명시

- 이 글은 gstack 의 품질 판정이 아니다. "플러그인 규격을 안 쓴다" 는 사실 진술이고, 그게 나쁘다는 주장은 아니다. 56개 스킬을 평평한 이름으로 굴리는 건 *하나의 워크플로를 통째로 채택하는 사용자* 에게는 오히려 마찰이 없다.
- gstack 과 다른 하네스를 비교한 **중립 제3자 벤치마크는 찾지 못했다.** 이 글의 수치는 전부 리포 실측이거나 내 단발 관측이다.
- findings 6건의 내역은 내 세션 화면에서 온 것이고, 이 글에서 재현 가능한 형태로 다시 측정한 값이 아니다.
- 위 실측값은 2026-09-09 스냅샷이다. 마지막 push 가 같은 날 새벽인 리포라 숫자는 곧 어긋난다.

---

## 정리

"플러그인 gstack" 이라고 부르던 물건은 실은 `~/.claude/skills/` 에 clone 되는 **스킬 번들**이었다. 플러그인화 커밋은 2026-03-12 에 올라왔지만 `main` 에 병합되지 않았고, 커뮤니티 마켓플레이스 2,282개 중에도 gstack 은 없다 — 대신 *번안된 파생 플러그인* 이 있다.

그래서 나도 번안했다. 56개 중 5개만, 그것도 내 스택에 없던 것만. 첫 교차 리뷰에서 단독 findings 가 절반이었으니, 적어도 그 5개는 값을 했다.

---

## References

[^1]: garrytan/gstack — README (`main`). <https://github.com/garrytan/gstack> · 실측: `GET /repos/garrytan/gstack`, `GET /repos/garrytan/gstack/git/trees/main?recursive=1` (2026-09-09).
[^2]: Claude Code Docs — Create plugins. <https://code.claude.com/docs/en/plugins>
[^3]: Claude Code Docs — Plugins reference. <https://code.claude.com/docs/en/plugins-reference>
[^4]: Claude Code Docs — Discover and install prebuilt plugins through marketplaces. <https://code.claude.com/docs/en/discover-plugins>
[^5]: garrytan/gstack — commit `1adf401` "feat: install gstack from Claude Code marketplace" (2026-03-12). <https://github.com/garrytan/gstack/commit/1adf401eadeefdc61af37721968e2729a00aea28> · `main` 과의 관계는 `GET /repos/garrytan/gstack/compare/1adf401e...main` 로 확인.
[^6]: anthropics/claude-plugins-community — `.claude-plugin/marketplace.json`. <https://github.com/anthropics/claude-plugins-community>
