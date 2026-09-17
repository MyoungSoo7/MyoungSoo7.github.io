---
layout: post
title: "DeepSeek Harness 를 직접 돌려봤다 — 포스트모템 4건, 그리고 기본으로 켜진 세션 로그 업로드"
date: 2026-09-17 21:11:31 +0900
categories: [engineering]
tags: [deepseek, harness, agent, postmortem, telemetry, fail-closed, cordis]
---

DeepSeek Harness 는 이 블로그에서 두 번 다뤘다. [8월 27일](/2026/08/27/deepseek-harness-decision-ledger/)엔 리포를 클론해 결정 원장 739건을 셌고, [9월 3일](/2026/09/03/deepseek-harness-infographic-fact-check/)엔 소셜에 도는 정리 이미지를 GitHub API 로 대조했다. 두 글 다 끝에 같은 단서를 달았다 — **하네스를 실제로 실행해 검증하지는 않았다.**

이번엔 돌렸다. 그리고 2주 동안 리포에 무엇이 쌓였는지 다시 셌다. 결론부터 쓰면 세 가지다.

1. 2주 새 커밋 600건, 프리릴리스 7개. 결정 원장은 739 → 1,025건으로 늘었는데 `implemented/` 는 오히려 줄었다.
2. `docs/postmortem/` 이 생겼다. 4건 중 하나는 내가 8월에 칭찬한 fail-closed 경계에서 난 사고다.
3. 키 없이 돌리면 `MISSING_CREDENTIAL` 로 죽는다 — 8월에 문서로만 읽었던 걸 재현했다. 그리고 공식 API 로 붙이면 **세션 로그 전체가 요청에 실려 DeepSeek 으로 올라가는 플러그인이 기본으로 켜져 있다.** 문서에 적혀 있고 끌 수 있지만, README 와 SAFETY.md 에는 없다.

## 2주 동안 무엇이 바뀌었나

세 시점의 실측값이다. 8/27 과 9/3 은 이전 글, 9/17 은 오늘 GitHub REST API 와 git tree API 로 직접 센 값이다.[^api]

| 항목 | 8/27 | 9/3 | 9/17 |
|---|---|---|---|
| 스타 / 포크 | 199,396 / 22,740 | 210,406 / 24,607 | **227,477 / 27,111** |
| 버전 (루트 `package.json`) | `0.1.1-rc.2` | `0.1.2-rc.1` | **`0.1.6-alpha.1`** |
| 워크스페이스 `package.json` (`packages/` 하위) | 256 | — | **291** (그룹 58개) |
| Agent Note 합계 | 739 | — | **1,025** |
| 포스트모템 | 없음 | 없음 | **4건** |

9월 3일 이후 커밋이 600건이다 (API 로 페이지를 넘겨 센 값, 마지막 push 는 9월 15일). 릴리스 태그는 9월 4일 `0.1.3-alpha.1` 부터 9월 15일 `0.1.6-alpha.1` 까지 7개가 새로 붙었다. 8월 21일 첫 태그 이후로 세면 25일 동안 프리릴리스 15개다. 기여자는 34명이고 상위 한 명이 커밋 6,211건을 갖고 있다 — 전체 커밋 수는 17,177건으로, 리포 공개일(8월 13일)보다 훨씬 긴 비공개 이력이 그대로 들어 있다.

npm 쪽은 조금 다르다. `@deepseek-ai/dsh` 의 `latest` 태그는 `0.1.5-rc.1`, `next` 는 `0.1.5-rc.2`, `alpha` 는 `0.1.6-alpha.1` 이다.[^npm] `npx @deepseek-ai/dsh` 로 받으면 GitHub 최신 태그보다 한 단계 뒤가 온다. 뒤에 나오는 실행 결과는 그래서 `0.1.5-rc.1` 이다.

### 원장은 늘었는데 `implemented/` 는 줄었다

| 라이프사이클 | 8/27 | 9/17 | 증감 |
|---|---|---|---|
| `implemented/` | 559 | **355** | −204 |
| `archived/` | 143 | **629** | +486 |
| `proposed/` | 26 | 27 | +1 |
| `rejected/` | 11 | **14** | +3 |
| 합계 | 739 | 1,025 | +286 |

8월 글에서 "아카이브는 영구 동결이고, 앞으로의 판단에 쓸모가 다한 결정을 옮기는 곳" 이라고 썼다. 그때는 규칙만 있었다. 3주 사이에 `implemented/` 의 200건 넘게가 `archived/` 로 넘어갔고, `.agents/skills/` 에 `dsh-archive-agent-notes` 라는 스킬이 따로 있다. 원장이 살아 있는 문서라는 건 **줄어드는 칸이 있다는 것**으로 증명된다. 늘기만 하는 ADR 폴더는 결국 아무도 안 읽는다.

`rejected/` 는 11 → 14 다. 14건 중 9건이 `simplification/` 클래스로, "이 패키지를 접자" "이 API 를 쳐내자" 류의 제안을 검토하고 기각한 기록이다 — 이 팀이 가장 자주 유혹받고 가장 자주 거절하는 건 기능 추가가 아니라 **단순화** 라는 뜻이다.

## 포스트모템 디렉터리

`docs/postmortem/` 은 9월 3일 글을 쓸 때 없었다. README 의 정의가 명확하다.[^pm]

> A post-mortem is NOT an Agent Note (which records a deliberate design decision …). It is a backward-looking record of a failure: what broke, the mechanism, why every safety net missed it, and the concrete guardrails added so the same class of bug fails loudly next time.

쓰는 조건도 셋으로 못박혀 있다 — **subtle** (기제가 비자명해서 신중한 엔지니어도 다시 고생해서 알아낼 것), **systemic** (빠져나간 이유가 오타가 아니라 테스트·도구·관례의 구멍), **costly to rediscover** (실제 디버깅 시간이 들었고 또 들 것). 셋 다 만족해야 쓴다. 4건이다.

| # | 무엇이 깨졌나 | 왜 빠져나갔나 |
|---|---|---|
| 0001 | ACP 서버가 에디터(Zed) 연결 즉시 크래시 | `export default apply` 한 줄이 플러그인의 `inject` 를 날림. **단위 테스트 178개 전부 통과, 라인 커버리지 100%.** 테스트가 전부 로더를 우회해 플러그인을 손으로 마운트했기 때문 |
| 0002 | 파일시스템 도구가 영구 비활성 | `disabled: !!js …` 표현식이 `config` 밖에선 평가되지 않고 truthy 객체로 남음. 스냅샷 갱신이 `UNKNOWN_TOOL` 결과를 기대값으로 받아들임 |
| 0003 | 웹 에이전트가 자기 GUI 대신 다른 포트의 새 서버를 검증 | 에이전트가 자기 세션을 호스팅하는 URL·프로세스를 알 방법이 없었음. Vite 의 HTTP 200 을 성공으로 오인 |
| 0004 | Landlock 부분 적용 커널에서 정상 종료가 `SANDBOX_UNAVAILABLE` 로 보고됨 | 런처의 정보성 stderr 한 줄과 자식 프로세스의 nonzero exit 를 하나의 신호로 합침. ripgrep 의 "결과 없음 = exit 1" 이 샌드박스 실패로 둔갑 |

0004 를 따로 봐야 한다. 8월 글에서 나는 이 하네스가 샌드박스를 못 쓰면 조용히 실행하지 않고 `SANDBOX_UNAVAILABLE` 로 죽는다는 점을 fail-closed 의 모범으로 들었다. 그 판단 자체는 틀리지 않았다 — 포스트모템도 "confinement 가 약해지거나 명령이 격리 없이 실행된 적은 없다" 고 명시한다. 문제는 **fail-closed 의 반대편 비용**이었다. 닫히는 쪽으로 기울어진 분류기는 정상 결과를 실패로 오판하기 쉽고, 그게 실제로 일어났다. 근본 원인 문장이 정확하다.

> Process attribution requires a conjunction of independent evidence; a shared prefix is not a protocol.

`landlock-run:` 이라는 접두사 하나로 "정보성 알림" 과 "런처 치명 실패" 를 같이 표현했고, 소비자는 그 접두사 + nonzero exit 를 실패로 읽었다. 고친 방식은 규칙을 구조화한 것이다 — 치명 신호는 **exit 125 이고 그 줄이 치명 시그니처를 담을 때**, 정보성 알림은 **정확히 그 문자열 한 줄일 때만** 제외. 그리고 fs 검색은 아예 샌드박스 bash 를 거치지 않고 패키징된 ripgrep 을 서브프로세스 seam 으로 직접 부르게 옮겼다.

0001 의 교훈 문장도 이 리포 밖에서 통한다.

> 100% line coverage was satisfied the whole time. Coverage proves lines *ran*; it says nothing about whether the feature works *the way it ships*.

같은 시기에 생긴 `docs/defensive-patterns.md` 는 이 포스트모템들의 압축본이다.[^def] "실제로 여기서 출시됐거나 출시 직전까지 간 버그 클래스" 만 모아 규칙 문장으로 바꿔 놨다 — 타임아웃과 exit 0 은 동시에 참일 수 있으니 따로 보고하라, dispose 는 요청이 아니라 정지(quiescence)까지 기다려라, 스폰하는 명령에는 `*KEY*` `*SECRET*` `*TOKEN*` `*PASSWORD*` 를 지운 환경을 넘겨라. 리포 하나가 한 달 만에 자기 사고 이력을 규칙으로 바꾸는 속도가 이 정도다.

## 직접 돌려봤다

환경: 리눅스 노드 하나, Node 22.22.0, `bwrap` 설치됨. 하네스 홈을 임시 디렉터리로 돌리고 `DEEPSEEK_API_KEY` 를 지운 채 실행했다.

```sh
export DSH_HOME=/tmp/dsh-home
unset DEEPSEEK_API_KEY
npx -y @deepseek-ai/dsh --help            # 첫 실행 1분 15초 (다운로드 포함)
npx -y @deepseek-ai/dsh --version         # 0.1.5-rc.1
npx -y @deepseek-ai/dsh --profile headless "print the word hello"
```

마지막 명령의 결과는 이 한 줄이고 exit 1 이다. 9초 걸렸다.

```
dsh: MISSING_CREDENTIAL: llm-deepseek: no API key for provider route "deepseek-official";
store DEEPSEEK_API_KEY through the credentials service (the web Models page writes it),
or export DEEPSEEK_API_KEY in the launching environment
```

8월 글에서 "크리덴셜 fail-closed 는 README 의 서술이지 내가 재현한 관측이 아니다" 라고 썼다. 이제 관측이다. 환경에 있는 다른 키를 뒤지지 않고, 라우트 이름과 두 가지 해결 방법을 찍고 죽는다.

### 키가 없어도 로그는 먼저 써진다

더 흥미로운 건 죽은 자리다. `$DSH_HOME/sessions/` 아래에 세션 디렉터리가 생겼고 `session.v3.jsonl.zstd` 가 들어 있었다. 풀어서 이벤트 타입만 뽑으면 이렇다.

```
session
permission/preset      {preset: workspace-write}
sandbox/mode           {mode: workspace-write}
approval/policy        {policy: ask}
agent/inbox/spliced    (사용자 입력이 다음 턴 인박스에 들어감)
turn/start             {turn: 1}
step/start             {turn: 1, step: 1}
system/message         "You are an AI agent powered by DeepSeek Harness. …"
user/message           "print the word hello"
user/message           "Current runtime context. …"   ← 런타임 컨텍스트 스냅샷
request/header         {provider: deepseek-official, model: deepseek-flash, …}
request/context        {…}
session/title          {title: "print the word hello", source: fallback}
assistant/attempt      {stream: [{chunk: {type: finish, reason: {kind: error, …}}}]}
step/end
turn/end               {reason: {kind: error, error: {message: "llm-deepseek: no API key …"}}}
```

9월 3일 글에서 인용한 아키텍처 문서의 한 줄 — "**Model-visible means logged.** Anything that reaches a model request must be reconstructable from the log" — 의 실물이다. 모델 요청이 **한 번도 나가지 않았는데도** 시스템 프롬프트, 사용자 메시지, 런타임 컨텍스트 스냅샷, 요청 헤더가 전부 로그에 있다. 로그가 요청의 부산물이 아니라 요청의 **전제조건**이라는 설계가 실행 결과로 보인다.

`--dump-config` 로 headless 프로파일이 부팅한 트리를 찍어보면 플러그인 엔트리가 87개다. `@deepseek-ai/dsh-base` 번들 위에 `dsh-headless` 패치가 얹히는 구조가 그대로 출력된다. 기본 모델 라우트는 `deepseek-official` / `deepseek-flash` 로 설정돼 있다 — 이건 하네스의 설정값이지 모델 성능에 대한 주장이 아니다.

## 기본으로 켜져 있는 두 가지

로그를 보다가 `request/header` 옆에 낯선 플러그인이 보였다. `--dump-config` 의 base 번들 안에 `session-log-deepseek` 이 있다. 패키지 README 를 읽었다.[^slog]

> Incremental canonical session-log upload for official DeepSeek LLM API requests. … owns the `dsh_session_log` request field … **Disable it only when the official API must not receive a Session-log suffix.**

| 키 | 기본값 | 의미 |
|---|---|---|
| `enabled` | **`true`** | `dsh_session_log` 기여를 등록한다. `false` 로 두면 세션 로그 업로드를 멈춘다 |

동작은 이렇다. 공식 DeepSeek API 로 나가는 요청에 `dsh_session_log` 라는 필드가 붙고, 그 안에 **마지막으로 서버가 수락한 지점 이후의 세션 이벤트 전부**가 들어간다. 서버가 2xx 를 돌려주면 `delivery-accepted` 이벤트가 로그에 추가되고, 다음 요청은 그 뒤부터 보낸다. 전송 실패면 워터마크가 안 움직여서 다음에 다시 보낸다 — at-least-once 다. 위에서 본 세션 로그가 무엇을 담는지 떠올리면, 시스템 프롬프트·사용자 메시지·도구 호출과 그 결과·런타임 컨텍스트가 전부 대상이다.

두 번째는 `@deepseek-ai/dsh-anonymous-user-id` 다.[^anon] 실행하자마자 `$DSH_HOME/.anonymous-user-id` 에 UUID 가 하나 생겼다. README 대로면 이 값은 텔레메트리의 `user.id` 속성, 피드백 확인, 그리고 **모든 공식 DeepSeek 요청의 `x-deepseek-harness-user-id` 헤더**에 붙는다. 설치 단위 식별자이고 계정·머신 정보는 없다고 명시돼 있다.

공정하게 쓰면 이렇다.

- **숨긴 게 아니다.** 두 패키지 모두 README 가 기본값·목적·끄는 법을 적어 놨다. 9월 15일 릴리스 노트도 "공식 API 엔드포인트에 연결할 때 요청과 함께 세션 이벤트를 보고하며, 현재 실험적으로 켜져 있고 설정으로 끌 수 있다" 고 썼다.[^rel]
- **모델은 못 본다.** `dsh_session_log` 는 `messages` 의 형제 필드라 모델 입력 토큰은 0 이고 KV 캐시에도 영향이 없다고 README 가 명시한다.
- **커스텀 엔드포인트엔 안 간다.** 공식 API 요청에만 붙는 필드다. 서드파티 프로바이더나 자체 게이트웨이를 쓰면 해당 없다.
- **그러나 README.md 와 SAFETY.md 어디에도 없다.** SAFETY.md 는 샌드박스 한계와 크리덴셜 노출을 경고하지만, 기본 설정에서 세션 로그가 벤더로 올라간다는 사실은 적지 않는다. 처음 설치하는 사람이 마주치는 두 문서에 없다는 건, 문서화됐다는 것과 별개로 **알고 동의한 상태로 시작하기 어렵다**는 뜻이다.

끄는 방법은 프로파일 오버레이에 한 줄이다. `cordis.patch.yml` 에 `session-log-deepseek` 의 `config.enabled: false` 를 넣으면 된다. 회사 코드를 이 하네스에 넣을 생각이면 **첫 실행 전에** 이걸 결정해야 한다. 실행하는 순간 첫 요청부터 올라간다.

이 부분은 8월·9월 글의 관점을 보정한다. 나는 "Model-visible means logged" 를 감사 가능성의 미덕으로만 읽었다. 그 로그가 완전하기 때문에, 같은 로그를 벤더에 보내는 플러그인도 완전한 것을 보낸다. 설계의 장점과 위험이 같은 속성에서 나온다.

## 깨는 것과 안 깨는 것의 비대칭

README 의 대문자 경고 — THERE WILL BE COMPATIBILITY-BREAKING CHANGES — 가 실제로 어떤 모양인지 `0.1.6-alpha.1` 릴리스 노트에 나온다.[^rel] 한 릴리스에서:

- DeepSeek 프로바이더 기본 프로토콜이 Messages 로 바뀌었다. 구 공식 루트 주소를 직접 설정해 뒀다면 지우거나 `https://api.deepseek.com/anthropic` 로 바꿔야 한다.
- 내장 E2B 실행 백엔드가 제거됐다.
- PTC 패키지·서비스 이름이 `ptc-runtime` 계열로 통일됐고 구 이름은 호환되지 않는다.
- `agent/session-start` 가 비동기 직렬 `agent/created` 로 바뀌어 플러그인이 적응해야 한다.
- 세션의 동기 이력 읽기 API 셋이 폐기됐다.
- 설정 핫리로드의 트랜잭션 롤백이 사라졌다.

API 는 이렇게 깬다. 그런데 **데이터는 안 깬다.** `docs/session-format-status.md` 가 세션 포맷 버전의 정본이고, 현재 릴리스된 포맷은 3, 근거 태그는 `dsh-v0.1.5-alpha.1` 이다.[^fmt] 그 문서의 한 문장이 이 비대칭을 규정한다.

> An alpha, beta, or release-candidate product publication establishes released Session-format obligations. **GitHub's prerelease flag does not make persisted user data disposable.**

알파 딱지가 붙어 있어도 사용자 디스크에 써진 세션은 다음 버전이 읽어야 한다. 마이그레이션은 인접 버전끼리만, 기존 세대는 옮기지도 덮어쓰지도 지우지도 않는다. `docs/persistence-changes/` 에는 9월 11일부터 변경마다 스키마 JSON 이 쌓이고 있다. 0.1.x 알파에서 이 규율을 지키는 프로젝트는 드물다. 대개는 반대로 한다 — API 는 지키려 애쓰고 로컬 데이터는 "알파니까" 하고 버린다.

## 가져갈 것

- **포스트모템의 입장 조건을 정해라.** subtle·systemic·costly-to-rediscover 셋을 다 만족할 때만 쓴다는 규칙이 있어서 4건이 4건으로 남는다. 조건 없이 쓰면 사고 보고서 폴더가 되고 아무도 안 읽는다.
- **fail-closed 는 공짜가 아니다.** 0004 는 닫히는 쪽으로 기운 분류기가 정상 결과를 실패로 오판한 사고다. "의심스러우면 실패" 를 택했다면 그 실패 판정의 **증거 규칙**을 구조화해야 한다. 접두사 매칭은 프로토콜이 아니다.
- **커버리지 100% 는 출시 경로를 증명하지 않는다.** 0001 의 교훈. 최소 하나의 테스트는 실제 로더·실제 진입점을 통과해야 하고, 그게 모델을 안 부른다면 키 없이 CI 에서 돌아야 한다.
- **기본값을 첫 실행 전에 읽어라.** 이 하네스는 기본 설정에서 공식 API 로 세션 로그를 올린다. 문서에 있고 끌 수 있다. 하지만 README 와 SAFETY 에는 없다. 남의 도구를 회사 코드에 붙이기 전에 `--dump-config` 같은 걸로 **무엇이 켜져 있는지** 를 찍어보는 습관이 이런 걸 잡는다.
- **API 와 데이터의 호환성 정책을 따로 세워라.** 알파에서 API 를 깨는 건 정직한 선택이다. 같은 알파에서 사용자 데이터를 버리는 건 다른 문제다. 이 리포는 둘을 다른 문서로, 다른 규칙으로 다룬다.

---

**출처와 검증 범위.** 스타·포크·커밋·릴리스·기여자 수는 2026-09-17 21시(KST) 전후 GitHub REST API 응답값이고 시간에 따라 변한다. Agent Note 와 패키지 수는 같은 시각 git tree API (`master`, 12,944 엔트리, truncated 아님) 에서 영문 `.md` 만 세었다. 실행은 npm `latest` 인 `0.1.5-rc.1` 로 했으므로 GitHub `0.1.6-alpha.1` 과 동작이 다를 수 있다. 세션 로그 업로드는 패키지 README 와 `--dump-config` 출력으로 확인한 것이지, 실제 API 키로 요청을 보내 `dsh_session_log` 필드가 전송되는 것을 패킷 수준에서 관측하지는 않았다. 샌드박스 fail-closed 는 이번에도 실행으로 재현하지 않았다 (키 없이 죽는 지점이 그 앞이다). 성능·품질 비교는 여전히 중립 측정이 없어 다루지 않았다.

## References

[^api]: GitHub REST API `GET /repos/deepseek-ai/deepseek-harness`, `/releases`, `/commits?since=2026-09-03`, `/contributors`, `/git/trees/master?recursive=1` — 2026-09-17 조회. <https://github.com/deepseek-ai/deepseek-harness>
[^npm]: npm registry `@deepseek-ai/dsh` — dist-tags `latest`/`next`/`alpha`, 2026-09-17 조회. <https://www.npmjs.com/package/@deepseek-ai/dsh>
[^pm]: DeepSeek Harness, `docs/postmortem/README.md` 및 `0001`–`0004` (master). <https://github.com/deepseek-ai/deepseek-harness/tree/master/docs/postmortem>
[^def]: DeepSeek Harness, `docs/defensive-patterns.md` (master). <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/defensive-patterns.md>
[^slog]: DeepSeek Harness, `packages/session/session-log-deepseek/README.md` (master). <https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/session/session-log-deepseek/README.md>
[^anon]: DeepSeek Harness, `packages/identity/anonymous-user-id/README.md` (master). <https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/identity/anonymous-user-id/README.md>
[^rel]: DeepSeek Harness, Release `dsh-v0.1.6-alpha.1` (2026-09-15). <https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.1.6-alpha.1>
[^fmt]: DeepSeek Harness, `docs/session-format-status.md` (master). <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/session-format-status.md>

이전 글: [거절한 설계를 지우지 않는 리포 (8/27)](/2026/08/27/deepseek-harness-decision-ledger/) · [이 그림이 맞는지 GitHub API 로 확인해봤다 (9/3)](/2026/09/03/deepseek-harness-infographic-fact-check/)
