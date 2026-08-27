---
layout: post
title: "빼는 걸 제품으로 삼은 스킬 카탈로그 — paperthin 의 가드를 직접 돌려봤다"
date: 2026-08-27 16:47:53 +0900
categories: [engineering]
tags: [agent-skills, claude-code, ci, yaml, bash, verification]
---

[LilMGenius/paperthin](https://github.com/LilMGenius/paperthin) 을 읽었다. 에이전트 스킬 카탈로그인데, 스킬 목록을 훑는 글은 이 블로그에 이미 여러 편 있으니 이번엔 다르게 접근했다. **클론해서 그 리포의 검증 스크립트를 직접 돌렸다.** 결론부터: 설계는 좋고, 가드에는 구멍이 있다. 셋 다 재현 가능한 형태로 아래에 적는다.

## 무엇인가

GitHub API 로 확인한 사실관계 (2026-08-27 조회 기준):

| 항목 | 값 |
|---|---|
| 생성 / 최근 push | 2026-06-19 / 2026-08-18 |
| 스타 / 포크 | 731 / 74 |
| 라이선스 | MIT |
| 주 언어 | Shell |
| 버전 | 0.17.4 (`package.json`) |
| 스킬 수 | `SKILL.md` 28개, `plugin.json` 등록 28개 (실측 일치) |

주장은 한 줄이다. **모든 스킬이 무언가를 뺀다.** README 는 대부분의 에이전트 스킬이 "더하는" 방향으로 실패한다고 진단한다 — 파일이 늘고, 옵션이 늘고, 같은 말을 세 번 하는 README 가 생긴다. 그 반대편에 걸겠다는 것이다. 저자의 표현으로는 "That restraint is the product."(그 절제가 곧 제품이다).

분류 축도 단순하다. **카디널리티(하나 → 여럿) × 시간(지금 → 반복)** 의 2×2 로 `depth` / `breadth` / `coil` / `mesh` 를 나눈다. 스킬 카탈로그를 기능별로 나누면 금세 무너지는데, 이 축은 "무엇을 대상으로 하느냐" 가 아니라 "몇 개를, 언제 걸쳐" 보느냐라서 새 스킬이 들어와도 자리가 정해진다. 분류 설계로는 잘 만든 축이다.

## 진짜 볼 만한 건 철학이 아니라 CI 가드다

`.github/workflows/ci.yml` 은 매 push/PR 마다 다섯 개를 돌린다.

```
validate-skills.sh        카탈로그 규약 검사
check-skill-refs.sh       스킬 참조가 실재하는지
check-links.sh            상대 링크가 깨졌는지
check-catalog-sync.cjs    카탈로그 SSOT 드리프트 가드
check-deploy-home.cjs     배포 경로 SSOT 드리프트 가드
```

`validate-skills.sh` 의 핵심은 **삼중 상호 등록 검사**다. 스킬 하나가 살아 있으려면 `SKILL.md` 가 존재하고, `plugin.json` 에 등록돼 있고, `README.md` 에 링크가 있어야 한다. 셋 중 하나만 빠져도 CI 가 빨간불이다. 여기에 `name` 값과 디렉터리 이름 일치, 필수 섹션 4종(`Goal`/`Workflow`/`Rules`/`Verification`) 존재, `../` 상대 참조 금지까지 붙는다.

이게 정확히 맞는 자리에 있는 가드다. 스킬 시스템은 **등록에서 탈락해도 아무 소리가 안 나는** 종류의 시스템이기 때문이다. 에러가 아니라 부재로 실패한다.

`check-catalog-sync.cjs` 는 한 발 더 나간다. 스킬 명단이 두 곳(`re0-upgrade/SKILL.md` 의 문서용 명단, `scripts/catalog.cjs` 의 코드용 명단)에 물리적으로 중복될 수밖에 없다는 걸 인정하고 — 스킬이 단독 배포돼야 해서 인라인이 강제된다 — 대신 **둘이 어긋나면 CI 를 깨는** 방식으로 SSOT 를 지킨다. 물리적 단일화가 불가능할 때 논리적 단일화를 강제하는 정석이다.

## 그래서 돌려봤다 — 실측 3건

### 1. 대조군

```
$ bash scripts/validate-skills.sh
✓ skill catalog valid (28 skills)     # exit 0
```

### 2. YAML 이 깨져도 통과한다

`skills/depth/hate/SKILL.md` 의 `description` 에서 따옴표를 벗기고 값 안에 콜론+공백을 넣었다. 한국어 설명에서 아주 흔한 모양이다.

```yaml
description: 예: /hate 처럼 부르면 계획을 공격한다
```

진짜 YAML 파서는 이걸 거부한다.

```
$ python3 -c "import yaml; yaml.safe_load(front_matter)"
ScannerError: mapping values are not allowed here
```

[YAML 1.2 명세](https://yaml.org/spec/1.2.2/)상 따옴표 없는 스칼라 안의 `: ` 는 매핑 구분자로 읽힌다. 값이 아니라 **구조**가 되는 것이다. 그런데 paperthin 의 검증기는:

```
$ bash scripts/validate-skills.sh
✓ skill catalog valid (28 skills)     # exit 0 — 통과
```

원인은 `validate-skills.sh` 60행이다. front matter 를 YAML 로 파싱하지 않고 정규식 `^[a-z_-]+:\s` 로 "키: 값 꼴 줄이 있나" 만 본다. 깨진 front matter 도 이 패턴엔 맞으므로 통과한다.

이건 이론적 위험이 아니다. 나는 2026-08-14 에 내 스킬 5개(`/힙` `/풀지씨` `/지씨누수` `/스레드` `/메타스페이스`)가 정확히 이 이유로 죽어 있는 걸 발견했다. 한국어 설명에 "예: /힙 sparta-prod" 가 들어갔고, 따옴표가 없어서 front matter 파싱이 통째로 실패했고, **파싱이 실패한 스킬은 목록에 아예 안 뜬다.** 에러 메시지가 없다. 몇 달을 몰랐다.

고치는 건 한 줄이다. 정규식 대신 실제 파서를 태우면 된다 — Node 24 에는 YAML 파서가 기본 내장돼 있지 않으니 `js-yaml` 의존성을 하나 추가하든지, 최소한 "따옴표 없는 `description` 값에 `: ` 가 있으면 실패" 규칙이라도 넣는 편이 낫다.

### 3. 문서대로 `NODE=` 를 쓰면 28건이 전부 오탐이 된다

스크립트는 node 를 못 찾으면 `NODE=/path/to/node` 로 넘기라고 안내한다. 그대로 해봤다.

```
$ PATH=/usr/bin:/bin NODE=/…/node bash scripts/validate-skills.sh
::error::skills/mesh/prism/SKILL.md: frontmatter block missing or malformed
…(28개 파일 전부)…
✗ catalog validation failed
```

`plugin.json` 검사(33행)와 브랜드 문구 동기화 검사(39–40행)는 `"$node_bin"` 을 쓰는데, 루프 안의 front matter 검사(60행)만 **맨 `node`** 를 부른다. PATH 에 node 가 없으면 그 파이프가 통째로 실패하고, 실패를 곧 "front matter 가 깨졌다" 로 해석해 28개 파일에 전부 붙인다. 파일은 멀쩡하다.

두 실측을 나란히 놓으면 방향이 보인다. **깨진 파일은 통과시키고, 멀쩡한 파일은 떨어뜨린다.** 둘 다 같은 60행에서 나온다.

### 4. macOS 기본 bash 로는 5종 중 2종이 실행되지 않는다

```
$ /bin/bash --version
GNU bash, version 3.2.57(1)-release (x86_64-apple-darwin25)

$ bash scripts/check-skill-refs.sh
line 19: mapfile: command not found
line 21: declare: -A: invalid option
```

`mapfile`(= `readarray`)과 연관배열 `declare -A` 는 bash 4 부터다. Apple 은 라이선스 문제로 bash 3.2 를 계속 싣고 있다. `check-skill-refs.sh` 와 `check-links.sh` 가 둘 다 이 문법을 쓴다. CI 는 `ubuntu-latest`(bash 5.x)라 초록불이고, 리포는 이 스크립트들을 "로컬에서도 돌릴 수 있다" 고 적어뒀는데 맥에서는 안 돈다.

덧붙여 `check-skill-refs.sh` 19행은 `find … -printf` 를 쓰는데 이건 GNU find 전용이고 macOS 의 BSD find 에는 없다. 그 자리 에러가 `2>/dev/null` 로 삼켜지고 있어서, bash 5 를 설치해 문법 문제를 넘겨도 목록이 조용히 비어버릴 가능성이 있다 — 이 부분은 이 맥에 bash 5 가 없어 **직접 확인하지 못했다.** 추정으로 남긴다.

## 여기서 가져갈 것

세 발견의 공통점은 "가드가 없다" 가 아니다. **가드는 있는데, 가드가 무엇을 통과시키는지를 아무도 재보지 않았다는 것**이다.

검증기를 쓸 때 실제로 물어야 할 질문은 "통과했나" 가 아니라 이 두 개다.

1. **거짓 음성** — 진짜 고장 난 입력을 넣으면 정말 빨간불이 켜지나? (실패 케이스를 일부러 만들어 넣어봤나)
2. **거짓 양성** — 문서에 적힌 대로 실행했을 때, 파일과 무관한 이유로 빨간불이 켜지진 않나?

정규식으로 YAML 을 읽는 순간 판정자와 실제 소비자(파서)가 갈라진다. 갈라진 그 틈이 바로 "조용히 죽은 스킬" 이 사는 곳이다. 나도 같은 이유로 내 스킬 원장에 전수 검사 스크립트를 따로 두고 있는데, 그 스크립트를 만든 계기가 위의 5개 스킬 사고였다.

마지막으로 공정하게 적자면, **드리프트 가드를 CI 에 코드로 박아 둔 리포 자체가 드물다.** 대부분은 규약을 README 에 적어두고 끝낸다. paperthin 은 규약을 실행 가능한 검사로 옮겨놨고, 그래서 이렇게 구멍을 정확히 지목하는 것도 가능했다. 검사가 아예 없는 리포에는 지목할 지점조차 없다.

---

**출처와 검증 범위.** 위 실측은 2026-08-27 기준 `main`(`3bca079`)을 얕은 클론해 Node 24.14.0 / bash 3.2.57 환경에서 실행한 결과다. 스타·포크 수는 GitHub REST API 응답값이며 시점에 따라 변한다. 4번의 BSD `find -printf` 관련 추론은 bash 5 환경에서 재현하지 못했음을 본문에 명시했다. 이 글은 리포의 품질을 총평하려는 것이 아니라, 다섯 개 가드 중 `validate-skills.sh` 한 개를 실행해 얻은 관측만 다룬다.

## References

- LilMGenius, *paperthin — Low-level agentic design patterns* — <https://github.com/LilMGenius/paperthin>
- 해당 리포 `scripts/validate-skills.sh`, `.github/workflows/ci.yml`, `scripts/check-catalog-sync.cjs` (main, `3bca079`)
- YAML 1.2.2 Specification — <https://yaml.org/spec/1.2.2/>
- GNU Bash Reference Manual — Bash Builtins (`mapfile`/`readarray`) — <https://www.gnu.org/software/bash/manual/bash.html#index-mapfile>
- Anthropic, *Claude Code — Agent Skills* — <https://docs.claude.com/en/docs/claude-code/skills>
