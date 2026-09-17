---
layout: post
title: "우로보로스 × OpenRouter × omp(oh-my-pi) — 같은 아이디어, 다른 층"
date: 2026-09-17 21:34:23 +0900
categories: [AI, Architecture]
tags: [Ouroboros, OpenRouter, ohmypi, omp, Pi, Consensus, LiteLLM, Agent, LLMRouting]
---

> **개정 이력.** 이 글의 초판은 `omp` 를 다른 도구로 잘못 읽고 썼다. 같은 날 전면 재작성해
> **oh-my-pi(omp)** 기준으로 바꿨다. URL 은 유지한다.

우로보로스(Ouroboros)·OpenRouter·omp(oh-my-pi) 셋을 같이 쓰면 재미있는 일이 생긴다.
**서로 다른 두 도구가 독립적으로 같은 결론에 도달해 있다** — "역할마다 다른 모델을 꽂아라".
그런데 그 둘이 말하는 *역할* 이 같은 층의 역할이 아니다. 겹쳐 쓸 때 문제가 나는 지점이
정확히 거기다.

> **표기 약속.** 아래에서 우로보로스는 이 맥에 설치된 `ouroboros-ai 0.54.4` 의 **소스를 직접
> 읽은 것**, omp 는 **공식 저장소 README(벤더 1차)**, OpenRouter 는 **공식 문서** 기준이다.
> 근거 등급이 다르므로 섞지 않고 매번 밝힌다. 별표 없는 수치는 2026-09-17 GitHub API 실측이다.

---

## 1. omp 가 뭔가 — 이름부터 정리

`omp` 는 **oh-my-pi** 의 바이너리 이름이자 줄임말이다. 홈페이지가 아예 `omp.sh` 다.

- **omp (oh-my-pi)** — `can1357/oh-my-pi`. ⭐ 31,548 · 포크 3,329 · MIT · TypeScript + Rust.
  `brew install can1357/tap/omp` 또는 `curl -fsSL https://omp.sh/install | sh`.
- 이건 **Pi 의 포크**다. 원본은 `earendil-works/pi` (구 `badlogic/pi-mono`, Mario Zechner).
  ⭐ 106,552 · 포크 13,415 · MIT. "Pi Agent Harness" — `pi-ai`(멀티 프로바이더 통합 LLM API),
  `pi-agent-core`(에이전트 런타임), `pi-coding-agent`(CLI), `pi-tui` 로 쪼개져 있다.
- 이름의 `Pi` 가 원주율에서 온 것인지는 저장소·문서 어디에도 안 적혀 있다. 추측하지 않는다.

README 가 스스로 내세우는 스펙은 이렇다(**벤더 1차 주장**) — 60+ 프로바이더 · 내장 툴 31개 ·
LSP 14 ops · DAP 28 ops · **Rust 코어 약 8만 줄**. 슬로건은 "A coding agent with the IDE
wired in" 이고, 실제로 차별점도 거기 있다. ripgrep·glob·find 를 셸아웃하지 않고 프로세스에
링크해 넣고, `brush` 라는 내장 셸에 `ls`·`sed`·`sort`·`xargs`·`jq` 등 58개 유틸을 포팅해
fork/exec 없이 돌린다고 적혀 있다.

---

## 2. 같은 생각이 두 번 나온다 — "역할마다 다른 모델"

여기가 이 글의 본론이다.

### omp 쪽 — 아홉 개의 역할

README 기준으로 omp 는 **아홉 개 역할(role)로 작업을 라우팅**한다.

```
default · smol · slow · plan · commit · vision · task · advisor · tiny
```

`smol` 은 싼 서브에이전트 팬아웃용, `slow` 는 깊은 추론용, `plan` 은 플랜 모드용,
`commit` 은 체인지로그용이다. 그리고 **역할마다 프로바이더를 섞을 수 있다**
("Mix providers per role"). 설정은 `~/.omp/agent/config.yml` 에서 이런 꼴이다.

```yaml
modelRoles:
  default: spark/minimax-m3
```

그중 `advisor` 역할이 특히 눈에 띈다. README 의 설명을 그대로 옮기면 —

> 리뷰어 모델을 'advisor' 역할에 붙이면 메인 에이전트의 **모든 턴을 읽고** 인라인으로
> 노트를 끼워 넣는다 — 가벼운 언급이거나, 우려이거나, **하드 블로커**다. 자기 컨텍스트와
> 자기 모델에서 돌기 때문에, 실행하는 쪽이 지나친 걸 잡아낸다.

거기에 `/review` 는 전용 리뷰어 서브에이전트를 병렬로 띄워 **P0–P3 우선순위 + 확신도 +
최종 verdict** 를 낸다. 즉 omp 는 실행 하네스이면서 **자체 2차 의견 장치를 이미 갖고 있다.**

### 우로보로스 쪽 — 세 개의 역할

설치본 `ouroboros/config/models.py` 의 합의 설정 기본값이다.

```python
# ConsensusConfig (ouroboros-ai 0.54.4)
min_models: int = Field(default=3, ge=2)
threshold: float = Field(default=0.67, ge=0.0, le=1.0)
diversity_required: bool = True
models: tuple[str, ...] = (
    "openrouter/openai/gpt-4o",
    "openrouter/anthropic/claude-opus-5",
    "openrouter/google/gemini-2.5-pro",
)
advocate_model: str = "openrouter/anthropic/claude-opus-5"
devil_model: str = "openrouter/openai/gpt-4o"
judge_model: str = "openrouter/google/gemini-2.5-pro"
```

**advocate(옹호) · devil(반박) · judge(판정)** 에 **서로 다른 벤더**가 배정돼 있고,
`diversity_required = True` 가 그걸 강제한다. 그리고 기본 로스터 3종이 전부 `openrouter/`
접두사다 — 우로보로스의 합의는 *설계상* OpenRouter 를 공급 경로로 가정한다.

### 결론: 같은 아이디어, 다른 층

두 도구가 독립적으로 "역할 → 다른 모델" 에 도달했다. 하지만 **역할의 층이 다르다.**

| | omp 의 advisor | 우로보로스의 합의 |
|---|---|---|
| 단위 | **턴** 마다 | **수용(acceptance)** 판정 시점 |
| 표 수 | 1개 모델 | 최소 3개, 임계 0.67 |
| 강제력 | 노트일 뿐 — 메인 에이전트가 **무시할 수 있다** | 미달이면 **통과 못 한다** |
| 성격 | 코칭 | **게이트** |

한 줄로 줄이면 이렇다. **omp 의 advisor 는 옆에서 말해 주는 사람이고, 우로보로스의 합의는
문을 잠그는 사람이다.** 그래서 둘은 대체재가 아니다. advisor 를 켰다고 합의가 필요 없어지지
않고, 합의를 붙였다고 advisor 가 무의미해지지 않는다.

---

## 3. OpenRouter 는 그 밑에서 재료를 댄다

공식 문서 기준으로 OpenRouter 는 OpenAI 호환 엔드포인트 하나
(`https://openrouter.ai/api/v1/chat/completions`)에 `vendor/model` 꼴 슬러그를 던지는 구조다.
모델 목록은 `GET /api/v1/models`.

중요한 건 **같은 슬러그를 여러 공급자가 서빙한다**는 점이고, 기본 라우팅이 이렇다
(공식 문서 Provider Routing).

- 기본은 **가격 기반 로드 밸런싱** — 가격의 **역제곱**에 비례해 가중치를 준다.
- **최근 30초 내 장애**가 있던 공급자는 건너뛴다.
- 나머지는 **폴백**으로 남는다. `allow_fallbacks` 기본값은 `true`.
- `provider` 객체로 제어한다 — `order`, `only`, `ignore`, `quantizations`, `sort`,
  `require_parameters`, `data_collection`, `zdr`, `max_price` 등.
- **`sort` 나 `order` 를 지정하면 로드 밸런싱이 꺼진다.**

그리고 omp 의 프로바이더 목록에 **OpenRouter 가 들어 있다.** LiteLLM 도 있다. 즉 세 도구는
실제로 한 배선 위에서 만난다 — omp 가 일을 하고, 우로보로스가 판정하고, 둘 다 OpenRouter 를
통해 모델을 받을 수 있다.

---

## 4. 배선의 급소 넷

### 급소 1 — 슬래시가 둘 다 있는데 의미가 다르다

omp 의 모델 셀렉터는 `프로바이더/모델` 이다 — `spark/minimax-m3`,
`openai-codex/gpt-5.5` 처럼. 우로보로스의 합의 로스터는
`openrouter/anthropic/claude-opus-5` 처럼 **세 토막**이다. 앞쪽 `openrouter/` 는
LiteLLM 에게 "OpenRouter 로 보내라" 고 말하는 접두사이고, 뒤의 `anthropic/claude-opus-5` 가
OpenRouter 가 게시한 실제 모델 ID 다.

**한쪽 설정에서 다른 쪽으로 복붙하면 깨진다.** 설치본
`ouroboros/config/_model_defaults.py` 가 같은 모델을 두 문자열로 따로 들고 있는 이유가
이것이다.

```python
DEFAULT_OPUS_MODEL           = "claude-opus-5"                       # Anthropic 직결
DEFAULT_CONSENSUS_OPUS_MODEL = "openrouter/anthropic/claude-opus-5"  # OpenRouter 경유
```

같은 파일 주석이 이유를 명시한다 — LiteLLM 은 슬러그를 **그대로(verbatim)** OpenRouter 로
넘기므로, OpenRouter 가 게시한 ID 와 **정확히** 일치해야 한다.

### 급소 2 — 틀린 모델 ID 는 에러가 아니라 조용히 한 표를 지운다

`ouroboros/providers/litellm_adapter.py` 의 키 선택 로직 마지막이 이렇다.

```python
# Unknown/custom models may still be routed through OpenRouter via credentials.
provider_name = self._extract_provider(model)
if provider_name not in {"openrouter", "openai", "anthropic", "google"}:
    ...  # credentials.providers["openrouter"] 의 키를 쓴다

# Default to OpenRouter for unknown models
return self._normalize_api_key(os.environ.get("OPENROUTER_API_KEY"))
```

오타 난 모델 ID 는 "그런 프로바이더 없음" 으로 거부되지 않고 **OpenRouter 로 간다.**
의도는 이해된다(어댑터가 모르는 신규 모델도 굴러가게). 하지만 급소 1 과 합치면 결과는
**투표 한 표가 조용히 빠지는 것**이다. `min_models=3` · `threshold=0.67` 이면 —
2/3 = 0.666… 이 0.67 미만이므로 — **한 표가 사라진 순간 합의는 구조적으로 통과할 수 없다.**
그런데 로그에는 "합의 실패" 라고만 찍힌다.

### 급소 3 — 실행층의 탄력성이 판정층에선 독이다

omp 의 라우팅 네 손잡이 중 둘이 여기 걸린다(README 기준).

- **Fallback chains** — `retry.fallbackChains` 로 역할·모델별 체인을 건다. 1순위가 429 나
  쿼터 벽에 부딪히면 **다음 항목이 그 턴의 나머지를 받는다.**
- **Round-robin credentials** — 프로바이더마다 API 키를 쌓아 두면 세션 어피니티와
  키별 백오프로 **돌려 쓴다.**

여기에 OpenRouter 의 기본 로드 밸런싱(가격 역제곱 + 30초 장애 회피)이 겹치면, 같은 슬러그가
호출마다 **다른 공급자**에게 가고, 공급자마다 **quantization 이 다를 수 있다.**

실행층에서는 이게 전부 미덕이다 — 쿼터가 말라도 일이 안 멈춘다. 그런데 **판정층에서는
치명적이다.** 우로보로스는 세 표를 세는데, 그중 한 표가 어제와 오늘 다른 공급자·다른 정밀도에서
나왔다면 같은 입력에 대한 판정이 흔들린다. 합의 하네스의 존재 이유가 판정의 재현성인데
공급 층이 그걸 흔드는 구조다.

그래서 **판정용 경로에는 탄력성을 꺼야 한다.** OpenRouter 쪽은 `order` 나 `only` 로 공급자를
못박고(그 순간 로드 밸런싱이 꺼진다) `quantizations` 로 정밀도를 제한한다. omp 쪽은 판정에
쓰는 역할에 fallback chain 을 걸지 않는다. **챗봇용 기본값과 판정자용 기본값은 같을 수 없다.**

### 급소 4 — 그래서 "물어봤다" 는 주장 자체를 검사한다

우로보로스가 이 문제를 다루는 방식이 흥미롭다. 설치본에는
`ouroboros/providers/litellm_proof_worker.py` 라는 **단일 요청 전용 워커**가 있고
(docstring: *"Single-request LiteLLM worker for frugality-proof effect isolation."*),
어댑터는 그 워커가 돌려주는 증명 딕셔너리의 키 집합을 **정확히** 대조한다.

```python
proof_keys = {
    "authority_verified", "client_cleanup_succeeded", "client_type",
    "httpx_dependency_version", "litellm_dependency_version",
    "openai_dependency_version", "transport_contract",
    "worker_executable_resolved_path", "worker_executable_content_sha256",
    "worker_python_version", "worker_module", "worker_implementation_sha256",
    "adapter_module", "adapter_implementation_sha256",
    "ouroboros_implementation_contract", "ouroboros_implementation_sha256",
}
proof_is_valid = isinstance(proof, dict) and set(proof) == proof_keys
if not proof_is_valid:
    dispatch.state.authority_drifted = True
    dispatch.state.cleanup_failed = True
```

키가 **하나라도 다르면** — 많아도, 적어도 — `authority_drifted` 가 선다. 워커 실행파일의
sha256, 워커 모듈의 sha256, 어댑터 구현의 sha256, httpx·litellm·openai 의존성 버전까지
증명 대상이다.

급소 3 의 문제의식이 코드로 내려온 형태로 읽힌다. **공급 층은 흔들리는 층이므로,
"다른 모델에게 물어봤다" 는 주장을 믿지 않고 경로를 해시로 고정한다.**

---

## 5. 그래서 어떻게 배선하나

1. **실행 역할과 판정 역할의 설정을 분리한다.** omp 의 `default`·`smol`·`task` 에는
   fallback chain 과 round-robin 키를 마음껏 건다. 우로보로스 합의 로스터에는 걸지 않는다.
2. **omp 의 `advisor` 와 우로보로스 합의를 겹쳐도 낭비가 아니다.** 앞의 표대로 하나는
   턴 단위 코칭, 하나는 수용 게이트다. 다만 **같은 벤더를 양쪽에 쓰지 않는다** — 같은 모델이
   코치도 하고 심판도 보면 2차 의견이 아니다.
3. **합의 로스터 슬러그는 OpenRouter `/api/v1/models` 응답과 문자열 대조한다.**
   눈으로 맞다고 넘기지 않는다. 급소 1·2 가 여기서 다 걸러진다.
4. **판정 호출에 `provider.order` 또는 `only` 를 못박는다.** 로드 밸런싱을 끄는 게 목적이다.
5. **합의가 실패하면 모델 품질이 아니라 배선부터 본다.** 조용히 빠진 한 표가 만드는 증상과
   판정이 실제로 갈린 증상이 **로그에서 똑같이 보이기 때문**이다. 구조적 귀결이지 경험칙이
   아니다.

---

## 6. 근거의 한계

- omp 서술은 전부 **공식 저장소 README(벤더 1차)** 다. 역할 9개, advisor 동작, 라우팅
  네 손잡이, 프로바이더 목록 모두 그쪽 주장이며 **내가 돌려서 확인한 게 아니다.**
  README 의 벤치 표(예: "Grok Code Fast 1, 6.7% → 68.3%")도 벤더 측정이고, 중립 제3자
  재현을 찾지 못해 이 글의 논거로 쓰지 않았다.
- 우로보로스 서술은 **이 맥에 설치된 0.54.4 소스를 읽은 것**이다. 공개 문서가 아니라 설치본
  기준이므로 버전이 다르면 기본값이 다를 수 있다. 상수·파일명을 그대로 적은 건 독자가 자기
  설치본에서 대조할 수 있게 하기 위해서다.
- OpenRouter 동작은 **공식 문서** 기준이고, 실제 공급자 선택 결과는 시점·모델마다 달라진다.
  같은 날 무료 모델 쪽 사정은
  [OpenRouter 무료 모델 비교]({% post_url 2026-09-17-openrouter-free-models-what-you-get %})
  에 따로 정리돼 있다.
- **세 도구를 동시에 물려 성능을 측정한 벤치마크는 이 글에 없다.** 주장하는 건 성능 우열이
  아니라 배선의 구조다.
- 별 수 없이 시점 의존적인 수치(스타 수 등)는 2026-09-17 GitHub API 응답이다.

---

## References

- oh-my-pi (omp) — <https://github.com/can1357/oh-my-pi> · <https://omp.sh> ·
  프로바이더/라우팅 레퍼런스 <https://omp.sh/docs/providers>
- Pi (원본) — <https://github.com/earendil-works/pi> · <https://pi.dev>
- can.ac, *The harness problem* — <https://blog.can.ac/2026/02/12/the-harness-problem/>
- OpenRouter, *Provider Routing* — <https://openrouter.ai/docs/features/provider-routing>
- OpenRouter, *Quickstart* — <https://openrouter.ai/docs/quickstart>
- OpenRouter, *Models* — <https://openrouter.ai/docs/overview/models>
- Ouroboros (Q00/ouroboros) — <https://github.com/Q00/ouroboros> · <https://ouroboros.page/>
  (본문 인용은 로컬 설치본 `ouroboros-ai 0.54.4` 의 `config/_model_defaults.py`,
  `config/models.py`, `providers/litellm_adapter.py`, `providers/litellm_proof_worker.py`)
- LiteLLM, *OpenRouter provider* — <https://docs.litellm.ai/docs/providers/openrouter>
