---
layout: post
title: "우로보로스 스킬 22개는 기능 22개가 아니다: 루프 5개와 비계 17개"
date: 2026-08-11 22:40:00 +0900
categories: [AI, Agent]
tags: [ouroboros, claude-code, agent, skill, mcp, spec-driven]
---

Claude Code 에서 우로보로스(Ouroboros) 플러그인을 깔면 스킬 목록이 이렇게 뜬다.

![Ouroboros Skill 목록 22개](/assets/images/ouroboros-skill-list.jpg)

22개. 처음 보면 "기능이 22개구나" 싶고, 그래서 어디서부터 손대야 할지 모르겠다. 나도 그랬다.

그런데 실제로 소스를 열어보면 **루프는 5개뿐**이다. 나머지 17개는 그 루프에 들어가지 못하거나, 들어갔다가 튕겨 나왔거나, 혼자 쓰다가 팀에 넘겨야 할 때를 위한 **비계(scaffolding)** 다. 이 구분을 하고 나면 22개가 갑자기 외울 만해진다.

이 글은 그 22개를 분해한다. 사실 확인은 공개 리포지터리 [Q00/ouroboros](https://github.com/Q00/ouroboros)(MIT) 의 `main` 계열 체크아웃(HEAD `14d9f216`, 2026-08-11) 에 대해 직접 했고, 인용한 문구는 각 `skills/<name>/SKILL.md` 의 frontmatter 와 `README.md` 원문이다. 마지막 절의 함정 3개는 문서가 아니라 내가 직접 밟아본 것이고, 이 글을 쓰면서 현재 소스에 다시 대조했다.

---

## 우로보로스가 뭔가 — 한 문단

우로보로스는 "코드를 짜주는 도구"가 아니라 **에이전트 OS** 를 표방한다. 핵심 주장은 README 의 이 한 줄에 압축돼 있다.

> No spec — architecture drifts mid-build → Immutable seed spec locks intent before code
> ([README.md](https://github.com/Q00/ouroboros/blob/main/README.md))

즉 **코드를 쓰기 전에 명세(Seed)를 먼저 수렴시키고**, 그 Seed 를 불변 기준점으로 잡은 뒤, 실행 결과가 기준에서 얼마나 밀렸는지(drift) 를 수치로 재면서 세대를 돌린다. 이름이 자기 꼬리를 무는 뱀인 이유다.

루프는 이렇다.

```
Interview → Seed → Execute → Evaluate → Evolve → (Seed 로 되돌아감)
```

22개 스킬 중 이 루프에 직접 대응하는 건 `interview`, `seed`, `run`, `evaluate`, `evolve` — 다섯 개다.

---

## 22개를 5그룹으로 쪼개기

각 스킬의 `description` 은 `skills/<name>/SKILL.md` frontmatter 원문 그대로다.

### 1. 루프 본체 (5개) — 이것만이 "기능"이다

| 스킬        | 공식 description                                                | 역할                                       |
| :---------- | :-------------------------------------------------------------- | :----------------------------------------- |
| `interview` | "Socratic interview to crystallize vague requirements"          | 모호한 요구를 소크라테스식 질문으로 깎아냄 |
| `seed`      | "Generate validated Seed specifications from interview results" | 인터뷰 결과 → 검증된 Seed 명세             |
| `run`       | "Execute a Seed specification through the workflow engine"      | Seed 를 워크플로 엔진에 태움               |
| `evaluate`  | "Evaluate execution with three-stage verification pipeline"     | 3단계 검증 파이프라인                      |
| `evolve`    | "Start or monitor an evolutionary development loop"             | 세대를 돌림                                |

여기서 놓치면 안 되는 건 `evaluate` 의 "three-stage" 다. 기계적 검증(빌드·테스트가 도는가) → 의미적 검증(요구를 실제로 만족하는가) → 다중 모델 합의 순으로 게이트가 걸린다. 테스트가 초록이라는 사실만으로는 통과가 아니다.

### 2. 진입 (5개) — 루프에 들어가기 전

| 스킬         | 공식 description                                                         |
| :----------- | :----------------------------------------------------------------------- |
| `ooo`        | "Start Ouroboros onboarding. Use when the user sends bare `ooo`…"        |
| `welcome`    | "First-touch experience for new Ouroboros users"                         |
| `setup`      | "Guided onboarding wizard for Ouroboros setup"                           |
| `tutorial`   | "Interactive tutorial teaching Ouroboros hands-on"                       |
| `brownfield` | "Scan and manage brownfield repository/worktree defaults for interviews" |

진입 스킬이 5개나 되는 건 과하다기보다 **이 도구의 진입 장벽이 그만큼 높다는 자백**에 가깝다. 특히 `brownfield` 는 이 도구가 백지 프로젝트용이라는 흔한 오해를 정면으로 반박하는 스킬이다 — 이미 있는 리포를 스캔해서 인터뷰의 기본값으로 깔아준다.

### 3. 복구 (3개) — 루프가 멈췄을 때

| 스킬             | 공식 description                                                                                   |
| :--------------- | :------------------------------------------------------------------------------------------------- |
| `unstuck`        | "Break through stagnation with lateral thinking personas — single or multi-persona debate"         |
| `cancel`         | "Cancel stuck or orphaned executions"                                                              |
| `resume-session` | "List in-flight Ouroboros sessions and show the commands needed to re-attach after MCP disconnect" |

**이 그룹이 이 도구를 실제로 쓸 수 있게 만드는 부분이다.** 장시간 도는 에이전트 루프의 진짜 실패 모드는 "틀린 답을 낸다"가 아니라 "같은 자리에서 돈다"와 "붙어 있던 세션이 끊긴다"다. `unstuck` 은 전자에, `resume-session` 은 후자에 대응한다. MCP 연결이 끊겨도 세션은 백그라운드에 살아 있고, 다시 붙는 명령을 뽑아주는 스킬이 따로 있다는 건 이 실패를 설계 단계에서 예상했다는 뜻이다.

### 4. 운영·관측 (5개)

| 스킬     | 공식 description                                                                      |
| :------- | :------------------------------------------------------------------------------------ |
| `status` | "Check session status and measure goal drift"                                         |
| `qa`     | "General-purpose QA verdict for any artifact type"                                    |
| `ralph`  | "MCP-owned Ralph loop around background evolve_step jobs"                             |
| `config` | "Open or drive the Ouroboros settings GUI (browser, TUI, or conversational fallback)" |
| `update` | "Check for updates and upgrade Ouroboros to the latest version"                       |

`ralph` 는 배경 지식이 필요하다. Ralph 는 "에이전트를 한 번 부르고 끝내지 말고 조건이 만족될 때까지 계속 다시 부른다"는 지속 루프 패턴을 가리키는 통용 명칭이고, 여기서는 그 루프의 소유권을 MCP 서버가 갖고 `evolve_step` 잡을 백그라운드로 반복 발사하는 형태로 구현돼 있다.

### 5. 팀 연계 (2개)

| 스킬      | 공식 description                                                                |
| :-------- | :------------------------------------------------------------------------------ |
| `pm`      | "Generate a PM through guided PM-focused interview…"                            |
| `publish` | "Publish Seed specification as GitHub Issues for team-based project management" |

`publish` 가 이 도구의 야심을 드러낸다. Seed 는 사람이 안 읽는 내부 구조체가 아니라, **GitHub Epic/Task 이슈로 그대로 펼쳐지는 명세**다. 혼자 쓰는 코드 생성기에서 팀의 요구사항 관문으로 넘어가는 지점이 여기다.

(나머지 `help` 는 레퍼런스 문서다. 5+5+3+5+2+1 = 21, 여기에 `auto` 를 더해 22개다.)

---

## `auto` 를 따로 떼어 놓은 이유

`auto` 의 description 은 이렇다.

> "Automatically converge from goal to A-grade Seed and execute it"

목표 한 줄만 던지면 인터뷰부터 Seed 생성, 실행까지 사람 없이 다 한다는 뜻이다. **22개 중 가장 매력적이고, 내 경험상 가장 신뢰하기 어려운 스킬이다.**

2026-08-06 에 `ouroboros_start_auto` 를 두 번 연속(잡 `job_5e899504c959`, `job_6745dd7acff3`) 돌렸을 때, 자동 응답기가 1라운드 답변을 이후 라운드에 거의 그대로 복사해 넣으면서 ambiguity 가 0.22 → 0.35 로 **되레 올라가며** 루프를 돌았다. 수렴 게이트를 통과 못 하니 Seed 가 안 나오고, 안 나오니 계속 질문을 다시 하는 구조다.

이건 내 로컬 세션 1건(반복 2회) 관찰이고, 그 시점 버전에 대한 것이며, 업스트림 이슈로 확인된 재현 사례가 아니다. 위 4그룹의 사실 기술과는 등급이 다르므로 그대로 일반화하지 말 것. 다만 실용적 결론은 분명했다 — **사양이 이미 머릿속에 있다면 인터뷰를 자동으로 돌리지 말고 Seed 를 손으로 쓰고 실행으로 직행하는 편이 빠르다.**

---

## 이름이 이상한 4개 — `ouroboros-` 접두사의 정체

이미지 목록은 전부 `ouroboros-` 로 시작하지만, 실제 스킬 디렉터리와 frontmatter 를 보면 접두사가 **파일 안에 박혀 있는 건 딱 4개**다.

```
skills/config/SKILL.md   → name: ouroboros-config
skills/help/SKILL.md     → name: ouroboros-help
skills/run/SKILL.md      → name: ouroboros-run
skills/status/SKILL.md   → name: ouroboros-status
```

나머지 18개는 `name: auto`, `name: seed` 처럼 맨이름이다. 왜 이 4개만인가? README 가 직접 답한다.

> `/resume` is reserved for Claude Code's built-in session picker; use `ooo resume-session` for Ouroboros in-flight sessions.
> Claude Code also reserves `/run`, `/status`, `/help`, and `/config`.
> ([README.md](https://github.com/Q00/ouroboros/blob/main/README.md))

Claude Code 가 `/run`, `/status`, `/help`, `/config`, `/resume` 를 이미 쓰고 있어서다. 앞의 4개는 `ouroboros-` 를 붙여 피했고, `/resume` 는 아예 스킬 이름을 `resume-session` 으로 바꿔 피했다. **디렉터리 이름 하나에 호스트와의 네임스페이스 충돌 회피 이력이 화석처럼 남아 있는 것이다.**

플러그인을 만드는 입장에서 이건 그냥 남의 사정이 아니다. 슬래시 커맨드 네임스페이스는 호스트가 선점하고, 선점된 이름은 조용히 안 먹는 게 아니라 **엉뚱한 게 실행된다.** 이름 짓기 전에 예약어부터 확인해야 한다.

---

## 이 도구를 지탱하는 두 개의 수식

22개 스킬을 다 외우는 것보다, 게이트 두 개를 이해하는 게 실제로는 더 중요하다.

**게이트 1 — 모호성(Ambiguity).** Seed 를 만들어도 되는지 결정한다. Greenfield 기준 가중치는 목표 명확도 40%, 제약 명확도 30%, 성공기준 측정가능성 30% (Brownfield 는 35/25/25 에 코드베이스 이해도 15% 가 추가된다).

$$
\text{Ambiguity} = 1 - \sum_i w_i c_i \le 0.2
$$

README 의 예시를 그대로 옮기면, $0.9\times0.4 + 0.8\times0.3 + 0.7\times0.3 = 0.81$ 이므로 Ambiguity $= 0.19 \le 0.2$ → Seed 생성 가능. README 는 0.2 라는 숫자의 근거를 "가중 명확도 80% 면 남은 미지수는 코드 수준 판단으로 해소 가능한 크기"라고 설명한다.

**게이트 2 — 온톨로지 수렴(Convergence).** 진화를 멈춰도 되는지 결정한다. 세대 간 스키마를 비교한다.

$$
\text{Similarity} = 0.5\,S_{\text{name}} + 0.3\,S_{\text{type}} + 0.2\,S_{\text{exact}} \ge 0.95
$$

여기에 병리 패턴 감지가 붙는다. 3세대 연속 0.95 이상이면 정체(stagnation), $\text{Gen}_N \approx \text{Gen}_{N-2}$ 면 진동(oscillation), 3세대에 걸쳐 질문 중복도 70% 이상이면 반복 피드백, 그리고 **30세대 하드캡**이 안전판이다.

그리고 실행 중에는 세 번째 지표가 따로 돈다 — **Drift** = 목표 50% + 제약 30% + 온톨로지 20%, 임계값 0.3 이하. `status` 스킬이 재는 게 이것이다.

README 는 이 둘을 이렇게 요약한다.

> do not build until you are clear (Ambiguity ≤ 0.2), do not stop evolving until you are stable (Similarity ≥ 0.95)

정직하게 덧붙이면, **이 임계값들이 산출물 품질을 실제로 개선하는지에 대한 중립 제3자 벤치마크는 내가 찾지 못했다.** 위 수치는 전부 프로젝트 자체 문서의 설계 파라미터이고, 그 자격으로만 인용한다.

---

## 문서에 없는 함정 3개 (직접 밟은 것)

스킬을 거치지 않고 MCP 툴 `execute_seed` 로 Seed 를 직접 실행할 때, 아래 셋은 **에러 메시지만 봐서는 원인을 못 찾는다.** 아래 코드 위치는 이 글을 쓰면서 현재 HEAD(`14d9f216`) 에 다시 대조했다.

**1) Seed 는 반드시 YAML.** Markdown 으로 쓰면 `found character '`' that cannot start any token` 으로 파싱부터 죽는다. 명세 문서라는 단어 때문에 Markdown 을 떠올리기 쉬운데 아니다.

**2) `ontology_schema` 는 필수 최상위 키.** 빠뜨리면 실행 0초 만에 `Seed validation failed: ontology_schema Field required` 로 종료된다. 소스에서 확인 가능하다 — `src/ouroboros/core/seed.py` 의 Seed 모델에서 이 필드만 `Field(...)`, 즉 기본값 없는 필수다. 다른 대부분의 필드는 `default_factory=tuple` 이라 없어도 통과하기 때문에, 이 하나만 유독 다르다는 걸 모르면 계속 헤맨다.

**3) Seed 파일 경로에 제약이 있다.** `~/.ouroboros/seeds/` 아래이거나 대상 리포 안이어야 하고, 임시 디렉터리에 두면 `Seed path escapes allowed directories` 계열 메시지로 거부된다 (`src/ouroboros/mcp/tools/execution_handlers.py`).

**그리고 가장 위험한 것 — 워크트리의 base 는 대상 리포의 "현재 HEAD" 다.**

`src/ouroboros/core/worktree.py` 를 보면 `base_ref` 가 주어지지 않았을 때 `git rev-parse --verify HEAD` 결과를 base 로 삼아 `git worktree add -b <branch> <path> <base>` 를 실행한다. 즉 **호출 시점에 그 리포가 어느 브랜치에 가 있었느냐가 그대로 새 작업의 출발점이 된다.**

혼자 쓰는 리포면 무해하다. 하지만 여러 세션·여러 에이전트가 같은 체크아웃을 공유하는 환경이라면, 다른 세션이 올라타 있던 feature 브랜치 위에서 워크트리가 떠지고, 거기서 나온 커밋이 남의 미완성 작업을 업고 나온다. 나는 이걸 피하려고 **Seed 안에서 push 와 브랜치 생성을 금지하고, 최종 브랜치 정리는 오케스트레이터가 직접 한다.**

한 가지 더 — **AC(수용 기준) 게이트는 커밋된 상태만 본다.** `verify_command` 가 워크트리를 임시 디렉터리로 `git clone` 한 뒤 거기서 검증하기 때문에, 워킹 트리에만 있는 변경은 게이트 입장에서 존재하지 않는다. 순서는 반드시 **구현 → 커밋 → 게이트**다.

---

## 정리

- 22개는 기능 22개가 아니다. **루프 5개 + 비계 17개**다. `interview → seed → run → evaluate → evolve` 만 외우면 나머지는 필요할 때 찾으면 된다.
- 비계 중 가장 값어치 있는 건 복구 그룹(`unstuck`, `cancel`, `resume-session`) 이다. 장시간 에이전트 루프의 진짜 실패는 오답이 아니라 정체와 단절이기 때문이다.
- `auto` 는 가장 팔리는 스킬이면서 내 손에서는 가장 안 미더웠던 스킬이다. 사양이 이미 정해졌다면 Seed 를 직접 쓰는 게 빠르다.
- 스킬 이름 4개에 붙은 `ouroboros-` 접두사는 장식이 아니라 호스트 예약어 회피의 흔적이다. 플러그인을 만든다면 그대로 배울 점.
- 게이트 두 개(Ambiguity ≤ 0.2, Similarity ≥ 0.95)와 Drift(≤ 0.3)를 이해하면 이 도구가 왜 이렇게 생겼는지가 설명된다. 단, 이 임계값들은 프로젝트의 **설계 파라미터**이지 검증된 효과 수치가 아니다.

---

## References

**1차·공식**

- Q00/ouroboros — 리포지터리 (MIT): <https://github.com/Q00/ouroboros>
- README.md (아키텍처, 루프, 스킬↔CLI 대응표, 예약어 회피, Ambiguity/Convergence/Drift 파라미터): <https://github.com/Q00/ouroboros/blob/main/README.md>
- 각 스킬 frontmatter: `skills/<name>/SKILL.md` (인용한 description 전문의 출처)
- 소스 대조 지점: `src/ouroboros/core/seed.py` (Seed 모델 필수 필드), `src/ouroboros/core/worktree.py` (워크트리 base 결정), `src/ouroboros/mcp/tools/execution_handlers.py` (Seed 경로 검증)
- PyPI 배포: `ouroboros-ai`

**본인 실측 (일반화 금지)**

- 2026-08-06 `ouroboros_start_auto` 2회 실행 관찰 — 인터뷰 자동응답 반복으로 ambiguity 0.22 → 0.35 상승
- `execute_seed` 직접 실행 시 마주친 검증 실패 3종 및 워크트리·AC 게이트 동작

**한계 명시**

- 본문의 모든 수치·임계값은 프로젝트 자체 문서에 기재된 설계 파라미터다. 산출물 품질에 대한 **중립 제3자 벤치마크나 재현 가능한 head-to-head 비교는 확인하지 못했다.**
- 스킬 구성은 활발히 변하는 프로젝트의 특정 시점(HEAD `14d9f216`, 2026-08-11) 스냅샷이다. 개수·이름은 바뀔 수 있다.
