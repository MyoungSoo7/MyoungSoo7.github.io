---
layout: post
title: "이 그림이 맞는지 GitHub API로 하나씩 확인해봤다 — DeepSeek Harness"
date: 2026-09-03 18:49:14 +0900
categories: [engineering]
tags: [deepseek, harness, agent, plugin, cordis, fact-check, 아키텍처]
---

![DeepSeek Harness가 보여준 것 — Everything is a Plugin 정리 이미지](/assets/images/deepseek-harness-everything-is-a-plugin.jpg)

이런 정리 이미지는 공유되기 좋게 만들어져 있다. 숫자가 크고, OLD/NEW 대비가 선명하고, 마지막 한 줄이 격언처럼 끝난다. 그래서 **틀렸을 때 가장 멀리 퍼진다.**

그림이 주장하는 걸 그대로 뽑으면 이렇다.

1. `deepseek-ai/deepseek-harness` 가 **207k★ / 24k forks**, TypeScript, MIT
2. **"Everything is a Plugin"**, powered by **Cordis**
3. 플러그인 링 8개 — 모델 / 도구 / 스킬 / 샌드박스 / 스케줄링 / UI / 스토리지 / 세션
4. **모델 어댑터도, 툴 레지스트리도, 세션 로그와 루프까지** 플러그인
5. **OLD**: 좋은 모델 + 프롬프트 = 데모 / **NEW**: 모델+도구+메모리+권한+로그+승인 = **운영**
6. 관찰 → 결정 → 실행 → 감사/로그
7. Developer Preview, Breaking changes, **SAFETY 먼저**

전부 GitHub API와 리포 원문으로 확인 가능한 주장이다. 하나씩 대조했다. 결론부터 쓰면 **1~4·7은 사실이고, 5는 원문이 정반대로 경고하는 지점이다.**

---

## 1. 숫자 — 그림이 오히려 보수적이었다

2026-09-03 GitHub REST API 실측값이다.[^api]

| 항목 | 그림 | 실측 (2026-09-03) |
|---|---|---|
| Stars | 207k | **210,406** |
| Forks | 24k | **24,607** |
| 언어 / 라이선스 | TypeScript / MIT | TypeScript / MIT ✓ |
| 저장소 생성일 | — | **2026-08-13T11:56:32Z** |
| 최신 릴리스 | — | **dsh-v0.1.2-rc.1** (2026-09-03) |
| Watchers(구독) | — | 905 |
| Issues | — | **비활성** (Discussions만 사용) |

같은 조직의 다른 저장소와 나란히 두면 규모가 더 분명해진다. `DeepSeek-V3` 가 104,431★, `DeepSeek-R1` 이 92,026★다. **하네스 하나가 자사 대표 모델 저장소 두 개를 합친 것에 근접한다.** 공개 21일 만이다.

다만 이 숫자를 "채택"으로 읽으면 안 된다. 스타는 관심 지표지 운영 투입 지표가 아니고, 버전은 아직 **`0.1.2-rc.1`** 이다. Issues를 꺼두고 Discussions만 여는 선택도 "쏟아지는 트래픽을 감당하는 중"에 가깝지, 성숙도의 표시가 아니다.

## 2. "Everything is a Plugin" — 저장소 설명 그 자체다

이건 해석이 아니라 인용이다. 저장소 description 필드가 통째로 `DeepSeek Harness: Everything is a Plugin.` 이다.[^api]

아키텍처 문서는 더 세게 말한다.

> "Every part of the product is a plugin, including the model adapter, the tool registry, the session log, and the agent loop itself, so each is replaceable from configuration. **There is no privileged core to patch.**"[^arch]

그림 4번 항목(모델 어댑터·툴 레지스트리·세션 로그·루프까지 플러그인)은 이 문장을 거의 직역한 것이다. 정확하다.

## 3. Cordis — 그림이 생략한 게 더 중요하다

"powered by Cordis"는 맞다. 그런데 Cordis는 DeepSeek가 이번에 만든 게 아니다.

- `cordiverse/cordis`, MIT, **2022-05-17 생성**, 8,029★ — "Meta-Framework of Spatiotemporal Composability"[^cordis]
- 설계 근거 논문: **《A Programming Paradigm for Spatiotemporal Composability》** (arXiv:2608.25512, Shi Yifan·Zhang Wei·Cui Tianyi, 2026-08-26)[^paper]

논문 초록이 이 하네스가 왜 이렇게 생겼는지를 설명한다. 동적 조합(dynamic composition)을 두 축으로 나눈다 — **시간적 조합성**(컴포넌트를 떼면 그 부수효과가 *완전히 되감기는* 성질)과 **공간적 조합성**(컴포넌트 간 의존을 선언하고 반응적으로 관리하는 성질). 그리고 고전적 effect / coeffect 개념을 런타임 기제로 끌어내려 **되감기 가능한 효과(revertible effects)** 를 형식화한다.

아키텍처 문서의 이 한 줄이 그 형식화의 실물이다.

> "registrations are effects that unwind when their plugin unloads."[^arch]

**플러그인을 내리면 그게 등록한 것들이 알아서 풀린다.** "다 플러그인이다"라는 구호가 실제로 성립하려면 이게 있어야 한다. 없으면 플러그인은 그냥 "끼우면 되는데 빼면 잔해가 남는 것"이 된다. 그림에서 빠진, 그러나 이 설계의 핵심이 이거다.

## 4. 링 8개는 실제 디렉터리와 겹친다

`packages/` 하위를 실제로 나열해보면 그림의 8개가 대부분 실존 패키지명이다.[^pkg]

```
acp  api  attachment  boot  bundle  client  code-runtime  compaction  context
core  credentials  e2b  experimental  extensions  feedback  fs  goal  guard
hooks  host  identity  interaction  jobs  llm  lsp  mcp  plan  preset
runtime-diagnostics  sandbox  schedule  sdk  session  session-query  settings
shell  skill  spill  storage  subagent  subprocess  terminal  test-support
todo  typert  util  web  webhook  workflow  workspace
```

`skill`·`schedule`·`storage`·`session`·`sandbox`·`llm`·`web`(UI) 이 그대로 있다. 도구는 `core/tools` 다. 그림이 임의로 붙인 카테고리가 아니라는 뜻이다.

다만 리포가 실제로 쓰는 어휘는 그림보다 한 단계 위에 있다. **profile**(부팅 시 쌓을 번들 목록) → **bundle**(Cordis 설정 행과 코드를 배포하는 단위) → **patch**(id를 지목해 그 행의 설정을 통째로 갈아끼우는 오버레이) 순서로 레이어가 쌓이고, 셸에서 `dsh --profile web --dump-config` 로 자기 머신이 부팅한 트리를 통째로 찍어볼 수 있다.[^arch]

그리고 **seam**(이음매)이라는 개념이 따로 있다. 하나의 교체 가능 능력은 *Service Definition*(인터페이스) + *Service Provider*(구현) + *Consumer*(사용처) 세 역할을 다 갖춰야 하고, 셋 중 하나만 있으면 seam이 아니라고 못박는다. 문서가 드는 예가 설득력 있다 — 파일시스템과 서브프로세스 제공자가 같은 실행 세계를 공유하기 때문에, **그 둘을 원격 샌드박스로 돌리면 Bash·PTY·LSP가 통째로 따라 옮겨간다.** 제공자를 갈아끼우는 것만으로 제품 전체가 바뀌는 구조다.

## 5. 여기가 문제다 — "권한 + 로그 + 승인 = 운영"

그림의 오른쪽 NEW 박스는 이렇게 읽힌다. *모델에 도구·메모리·권한·로그·승인을 더하면 데모가 운영이 된다.*

리포는 정확히 그 반대를 경고한다. `SAFETY.md` 원문이다.[^safety]

> "DeepSeek Harness is experimental developer-preview software. It **has not undergone a security audit and must not be treated as secure or production-ready.**"

> "Sandboxing, approval prompts, and permission controls can reduce risk, but they **do not guarantee isolation or prevent damage.** Even correctly enforced restrictions cannot protect resources that the project is allowed to access."

> "**Do not rely on DeepSeek Harness as the sole security control** for untrusted workloads."

즉 그림이 "운영"의 근거로 든 **권한·승인·샌드박스 그 세 가지를, 원문은 '운영 보증이 아니다'라고 명시적으로 부인한다.** 권장 사항도 일회용 VM·컨테이너·전용 환경에서 최소 권한으로 돌리고 백업을 두라는, *격리를 못 믿는다*는 전제의 목록이다.

그림 왼쪽 아래에 "Developer Preview / Breaking changes / SAFETY 먼저"가 있긴 하다. 그런데 그건 경고 포스트잇 크기고, "= 운영"은 밑줄 두 줄이다. **같은 그림 안에서 두 정보의 시각적 무게가 뒤집혀 있다.** 정리 이미지가 틀리는 전형적인 방식이 이거다 — 문장을 위조하는 게 아니라, 맞는 문장들의 **크기를 바꾼다.**

정확히 고치면 이렇게 된다.

> 모델 + 도구 + 메모리 + 권한 + 로그 + 승인 = **운영에 필요한 최소 구조** (운영 준비 완료가 아니라)

## 6. "관찰 → 결정 → 실행 → 감사/로그"는 실제로 어디 있나

이 루프에 대응하는 실물은 turn/step 흐름이다. 한 **step** 은 모델 요청 1회와 그것이 부른 도구들이고, 한 **turn** 은 0개 이상의 step이다.[^arch]

```
turn/start
  → agent/pre-step        (관찰·개입: 메시지 재작성 또는 거부)
    step/start
    agent/request → llm/stream → assistant/chunk* → assistant/message   (결정)
    tool/call* → tools/pre-execute → tools/execute → tools/post-execute (실행)
    step/end
  → agent/turn-stopping
turn/end
```

`turn/*`·`step/*`·`user/message`·`assistant/*`·`tool/*` 는 **durable session event** 로 로그에 남고, 나머지는 살아있는 확장점이다. 여기서 그림의 "감사/로그"에 해당하는 규칙이 문서에 한 문장으로 박혀 있다.

> "**Model-visible means logged.** Anything that reaches a model request must be reconstructable from the log, and a runtime invariant asserts it."[^arch]

**모델이 본 것은 전부 로그에서 재구성 가능해야 하고, 런타임 불변식이 그걸 강제한다.** 새 모델-가시 입력을 추가하려면 세션 이벤트를 새로 정의해야 한다는 제약이 여기서 나온다. 감사 로그를 "나중에 붙이는 기능"이 아니라 **입력 경로의 전제조건**으로 만든 것 — 이게 그림의 화살표 하나보다 훨씬 강한 주장이다.

---

## 가져갈 것

- **그림의 사실 주장은 대체로 맞았다.** 별 수는 오히려 보수적이었고, 플러그인 링도 실제 패키지와 겹치고, "루프까지 플러그인"은 문서 직역이다. 이런 이미지를 무조건 의심할 필요는 없다 — 다만 **확인하는 데 API 호출 몇 번이면 된다.**
- **틀린 건 사실이 아니라 강조 배분이었다.** SAFETY 경고는 포스트잇, "= 운영"은 밑줄 두 줄. 원문은 그 반대 비중으로 쓰여 있다.
- **그림이 빠뜨린 게 제일 중요했다.** "다 플러그인"을 성립시키는 건 되감기 가능한 효과(revertible effects)와 seam 3역할 규칙이다. 그게 없으면 플러그인 아키텍처는 구호로 남는다.
- 그리고 이건 자기 프로젝트에도 그대로 적용된다. 확장점을 늘리기 전에 **"이 플러그인을 내리면 그게 등록한 것들이 전부 풀리는가"** 를 먼저 답할 수 있어야 한다.

같은 저장소를 다른 각도로 판 이전 글: [거절한 설계를 지우지 않는 리포 — DeepSeek Harness 를 클론해서 세어봤다](/2026/08/27/deepseek-harness-decision-ledger/)

---

## References

[^api]: GitHub REST API `GET /repos/deepseek-ai/deepseek-harness`, `GET /orgs/deepseek-ai/repos`, `GET /repos/.../releases` — 2026-09-03 조회. <https://github.com/deepseek-ai/deepseek-harness>
[^arch]: DeepSeek Harness, *Architecture* (`docs/architecture.md`, master). <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md>
[^safety]: DeepSeek Harness, *Safety* (`SAFETY.md`, master). <https://github.com/deepseek-ai/deepseek-harness/blob/master/SAFETY.md>
[^cordis]: `cordiverse/cordis` — Meta-Framework of Spatiotemporal Composability, MIT. <https://github.com/cordiverse/cordis>
[^paper]: Y. Shi, W. Zhang, T. Cui, *A Programming Paradigm for Spatiotemporal Composability*, arXiv:2608.25512, 2026-08-26. <https://arxiv.org/abs/2608.25512>
[^pkg]: GitHub REST API `GET /repos/deepseek-ai/deepseek-harness/contents/packages` — 2026-09-03 조회.

첨부한 이미지는 필자가 제작한 것이 아니라 소셜에서 유통되는 정리물이며, 이 글은 그 이미지의 주장을 1차 출처와 대조한 기록이다. 별·포크 수는 조회 시점 값으로 계속 변한다.
