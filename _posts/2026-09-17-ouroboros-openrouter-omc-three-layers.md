---
layout: post
title: "우로보로스 × OpenRouter × OMC — 겹쳐 쓸 때 끊어지는 네 지점"
date: 2026-09-17 21:23:23 +0900
categories: [AI, Architecture]
tags: [Ouroboros, OpenRouter, OhMyClaudeCode, Consensus, LiteLLM, Agent, LLMRouting]
---

세 이름을 같이 놓고 "어느 게 제일 좋냐" 를 묻는 사람이 많다. 그런데 우로보로스(Ouroboros)·
OpenRouter·OMC(oh-my-claudecode)는 **경쟁 관계가 아니다.** 셋은 서로 다른 층에 있고, 겹치는
구간이 거의 없다. 실제로 겹쳐 쓰면 성능이 아니라 **배선**에서 문제가 난다.

이 글은 그 배선 이야기다. 셋을 같이 물렸을 때 실제로 어디가 끊어지는지, 설치본 소스와
공식 문서를 대조해서 정리했다.

> **표기 약속.** 아래에서 "설치본 실측" 은 이 맥에 설치된 `ouroboros-ai 0.54.4`
> (`Q00/ouroboros`) 와 `oh-my-claudecode 4.15.4` 의 **소스 파일을 직접 읽은 것**이고,
> OpenRouter 동작은 **공식 문서** 기준이다. 근거 등급이 다르므로 섞지 않고 매번 밝힌다.

---

## 1. 층이 다르다

| | 하는 일 | 다양성을 어디서 얻나 | 전제 |
|---|---|---|---|
| **OMC** | 실행 — 에이전트 팀을 편성하고 CLI 워커를 띄운다 | **프로세스** (별도 CLI 프로세스) | Claude Code CLI + Claude 구독 또는 Anthropic API 키 |
| **우로보로스** | 검증 — 명세를 고정하고 결과를 투표로 판정한다 | **모델·벤더** (합의 로스터) | LLM 공급 경로 |
| **OpenRouter** | 공급 — 키 하나·엔드포인트 하나로 수백 모델 | **공급자** (같은 모델의 여러 호스트) | API 키 |

정리하면 이렇다. **OMC 는 일을 시키고, 우로보로스는 그 일이 됐는지 판정하고, OpenRouter 는
판정에 쓸 다른 머리를 조달한다.** 조합의 요점은 가운데 칸이다 — 우로보로스의 판정은 *혼자*
하면 의미가 없고, 다른 벤더의 모델이 필요하고, 그걸 현실적으로 한 계정으로 모으는 수단이
OpenRouter 다.

예전에 [Superpowers × OMC × Ouroboros 3축 스택]({% post_url 2026-07-22-superpowers-omc-ouroboros-harness-stack %})
을 다룬 적이 있는데, 그때는 공급 층이 빠져 있었다. 이 글이 그 빈칸이다.

---

## 2. OMC — 다양성을 *프로세스* 로 얻는다

OMC 4.15.4 의 README 기준으로, 핵심은 Team Mode 다 (v4.1.7 부터 canonical).

```
team-plan → team-prd → team-exec → team-verify → team-fix
```

`omc team` 은 tmux 위에 **별도 CLI 프로세스**를 띄운다 — Claude Code, Codex, Gemini,
Antigravity, Grok, Cursor Agent. 즉 OMC 의 "여러 모델" 은 API 레벨이 아니라
**CLI 레벨**이다. 각 워커는 자기 인증·자기 과금·자기 컨텍스트를 갖는다.

여기서 조합의 첫 번째 사실이 나온다.

> **설치본 실측 — OMC 4.15.4 소스 트리 17,219개 파일 전체에 OpenRouter 참조가 0건이다.**
> 대소문자 무시 재귀 grep 이 파일 하나도 잡지 못한다 (2026-09-17 측정).

OMC 는 OpenRouter 를 모른다. 그리고 실행 전제가 **Claude Code CLI + Claude Max/Pro 구독
또는 Anthropic API 키** 다. 그러니 "OpenRouter 키만 있으면 OMC 를 싸게 돌릴 수 있나" 의
답은 **아니오** 다. OMC 를 OpenRouter 뒤에 숨기는 배선은 존재하지 않는다.

README 는 "smart model routing 으로 토큰 30–50% 절약" 을 내세우는데, 이건 **벤더 주장**이고
대상도 다르다 — *작업 난이도에 맞는 모델을 고른다* 는 뜻이지 *공급자를 바꿔 단가를 낮춘다* 가
아니다. 중립 제3자 측정은 찾지 못했다.

---

## 3. 우로보로스 — 다양성을 *투표* 로 쓴다

우로보로스의 3단계 합의(stage 3 voting) 기본값은 설치본에서 이렇게 잡혀 있다.

```python
# ouroboros/config/models.py — ConsensusConfig (0.54.4)
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

읽을 게 네 개다.

1. **최소 3 모델, 합의 임계 0.67.** 2:1 로는 통과하지 않는다 — 2/3 = 0.666… 이 0.67 미만이다.
   즉 3표 중 2표는 *불합의* 다. 만장일치에 가까운 설정이다.
2. **`diversity_required = True`.** 같은 벤더 모델 셋으로는 합의의 의미가 없다는 전제가
   코드에 박혀 있다.
3. **기본 로스터 3종이 전부 `openrouter/` 접두사다.** 우로보로스의 합의는 *설계상*
   OpenRouter 를 공급 경로로 가정한다.
4. **역할이 나뉜다** — advocate(옹호) / devil(반박) / judge(판정). 세 역할에 **서로 다른
   벤더**가 배정돼 있다. 옹호와 반박을 같은 모델이 하면 반박이 형식적이 된다는, 꽤 상식적인
   배치다.

여기서 조합의 두 번째 사실.

> **OMC 가 코드를 쓰고, 우로보로스가 그 코드를 3개 벤더에 물어보고, 그 3개 벤더를
> OpenRouter 가 한 키로 공급한다.** 셋을 같이 쓰는 유일하게 자연스러운 배선이 이것이다.

---

## 4. OpenRouter — 다양성을 *한 키* 로 공급한다

공식 문서 기준으로 OpenRouter 는 OpenAI 호환 엔드포인트 하나
(`https://openrouter.ai/api/v1/chat/completions`)에 `vendor/model` 꼴 슬러그를 던지는 구조다.
모델 목록은 `GET /api/v1/models` 로 받는다.

중요한 건 **같은 슬러그를 여러 공급자가 서빙한다**는 점이고, 기본 라우팅 정책이 이렇다
(공식 문서 Provider Routing).

- 기본은 **가격 기반 로드 밸런싱** — 가격의 **역제곱**에 비례해 가중치를 준다.
- **최근 30초 내 장애**가 있던 공급자는 건너뛴다.
- 나머지는 **폴백**으로 남는다. `allow_fallbacks` 기본값은 `true`.
- `provider` 객체로 제어한다 — `order`, `only`, `ignore`, `quantizations`, `sort`,
  `require_parameters`, `data_collection`, `zdr`, `max_price`,
  `preferred_min_throughput`, `preferred_max_latency`.
- **`sort` 나 `order` 를 지정하면 로드 밸런싱이 꺼진다.**

이 기본값은 챗봇에는 좋다. 그런데 **판정자**에게는 그렇지 않다. 다음 절이 그 이야기다.

---

## 5. 조합의 급소 넷

### 급소 1 — 모델 ID 포맷이 호환되지 않는다

설치본 `ouroboros/config/_model_defaults.py` 의 상수가 이렇게 갈라져 있다.

```python
DEFAULT_OPUS_MODEL           = "claude-opus-5"                       # Anthropic 직결
DEFAULT_CONSENSUS_OPUS_MODEL = "openrouter/anthropic/claude-opus-5"  # OpenRouter 경유
```

같은 모델인데 **문자열이 다르고, 서로 바꿔 쓸 수 없다.** 같은 파일의 주석이 이유를 명시한다 —
LiteLLM 은 슬러그를 **그대로(verbatim)** OpenRouter 로 넘기기 때문에, OpenRouter 가 게시한
모델 ID 와 **정확히** 일치하지 않으면 합의 투표가 실패한다.

실무에서 이게 아픈 이유는, 틀렸을 때 나는 에러가 "모델 없음" 이 아니라 **투표 한 표가 조용히
빠지는 것**이기 때문이다. `min_models=3` 에 `threshold=0.67` 이면 한 표가 사라진 순간 합의는
구조적으로 통과할 수 없다. 그런데 로그는 "합의 실패" 라고만 말한다.

### 급소 2 — 모르는 모델 ID 는 에러가 아니라 OpenRouter 로 간다

`ouroboros/providers/litellm_adapter.py` 의 키 선택 로직 마지막 부분이 이렇다.

```python
# Unknown/custom models may still be routed through OpenRouter via credentials.
provider_name = self._extract_provider(model)
if provider_name not in {"openrouter", "openai", "anthropic", "google"}:
    ...  # credentials.providers["openrouter"] 의 키를 쓴다

# Default to OpenRouter for unknown models
return self._normalize_api_key(os.environ.get("OPENROUTER_API_KEY"))
```

즉 **오타 난 모델 ID 는 거부되지 않고 OpenRouter 로 간다.** 설계 의도는 이해된다 — 어댑터가
모르는 신규 모델도 OpenRouter 를 통해 굴러가게 하려는 것이다. 하지만 부작용은, 잘못된
슬러그가 *조용히* 공급 경로를 타고 OpenRouter 에서 거부되어 돌아오는 것이다. 급소 1 과 합치면
증상은 "합의가 자꾸 실패한다" 하나로 수렴한다. **원인 진단을 모델 품질 쪽에서 시작하면 하루를
버린다.**

### 급소 3 — OpenRouter 의 기본값은 합의에 독이다

앞 절의 기본 라우팅을 다시 보자. 같은 슬러그가 호출마다 **다른 공급자**에게 갈 수 있고,
공급자마다 **quantization 이 다를 수 있다.**

판정자에게 이건 치명적이다. 우로보로스는 세 표를 세는데, 그중 한 표가 어제는 한 공급자에서,
오늘은 더 낮은 정밀도의 다른 공급자에서 나왔다면 **같은 입력에 대한 판정이 흔들린다.** 합의
하네스의 존재 이유가 "판정의 재현성" 인데 공급 층이 그걸 흔드는 구조다.

그래서 합의 로스터에는 `provider` 객체를 **반드시 고정**해야 한다 — 공식 문서 기준으로
`order` 나 `only` 로 공급자를 못박고(그 순간 로드 밸런싱이 꺼진다), `quantizations` 로 정밀도를
제한한다. 감사 로그를 남기는 용도라면 `data_collection` 과 `zdr` 도 같이 본다.

챗봇용 기본값과 판정자용 기본값은 **같을 수 없다.** 이게 셋을 겹칠 때 가장 많이 놓치는 지점이다.

### 급소 4 — 다양성은 *증명* 돼야 한다

우로보로스가 이 문제를 어떻게 다루는지가 흥미롭다. 설치본에는
`ouroboros/providers/litellm_proof_worker.py` 라는 **단일 요청 전용 워커**가 있고
(docstring: *"Single-request LiteLLM worker for frugality-proof effect isolation."*),
어댑터는 그 워커가 돌려주는 증명 딕셔너리의 키 집합을 **정확히** 검사한다.

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

말하자면 이렇다. **"다른 모델에게 물어봤다" 는 주장 자체를 신뢰하지 않고, 물어본 경로가
그 경로가 맞는지를 해시로 고정한다.** 판정 하네스가 스스로를 의심하는 설계다. 앞의 급소 3 과
같은 문제의식 — 공급 층은 흔들리는 층이라는 것 — 이 코드 레벨로 내려온 형태로 읽힌다.

---

## 6. 그래서 어떻게 배선하나

세 층을 겹칠 때의 실무 순서는 이렇게 된다.

1. **실행(OMC)과 검증(우로보로스)의 인증을 분리한다.** OMC 는 Claude 구독/Anthropic 키로
   간다. OpenRouter 키를 OMC 쪽에 끼워 넣으려는 시도는 의미가 없다 — 참조가 0건이다.
2. **합의 로스터의 슬러그는 OpenRouter `/api/v1/models` 응답과 문자열 대조한다.**
   눈으로 맞다고 넘기지 않는다. 급소 1·2 가 여기서 다 걸러진다.
3. **판정용 호출에는 `provider.order` 또는 `only` 를 못박는다.** 로드 밸런싱을 끄는 게
   목적이다. 재현성이 필요 없는 일반 호출과 설정을 공유하지 않는다.
4. **벤더를 3사로 흩는다.** `diversity_required = True` 가 요구하는 건 모델 3개가 아니라
   *벤더* 3개다. 같은 회사 모델 셋은 상관된 오답을 낸다.
5. **합의 실패가 나면 모델 품질이 아니라 배선부터 본다.** 경험칙이 아니라 위 급소들의 구조적
   귀결이다 — 조용히 빠진 한 표가 만드는 증상과, 판정이 실제로 갈린 증상이 **로그에서 똑같이
   보인다.**

---

## 7. 근거의 한계

- 우로보로스 관련 서술은 **이 맥에 설치된 0.54.4 소스를 읽은 것**이다. 공개 문서가 아니라
  설치본 기준이므로, 버전이 다르면 기본값이 다를 수 있다. 상수·클래스 이름을 그대로 적은 건
  독자가 자기 설치본에서 같은 파일을 열어 대조할 수 있게 하기 위해서다.
- OMC 의 "30–50% 절약" 은 **벤더 주장**이다. 중립 제3자 측정을 찾지 못했고, 그 수치를 이
  글의 논거로 쓰지 않았다.
- OpenRouter 의 라우팅 동작은 **공식 문서** 기준이고, 실제 공급자 선택 결과는 시점·모델마다
  달라진다. 같은 날 공급자 수와 무료 모델 쪽 사정은
  [OpenRouter 무료 모델 비교]({% post_url 2026-09-17-openrouter-free-models-what-you-get %})
  글에 따로 정리돼 있다.
- **세 도구를 동시에 물려 성능을 측정한 벤치마크는 이 글에 없다.** 이 글이 주장하는 건
  성능 우열이 아니라 배선의 구조다.

---

## References

- OpenRouter, *Provider Routing* — <https://openrouter.ai/docs/features/provider-routing>
- OpenRouter, *Quickstart* — <https://openrouter.ai/docs/quickstart>
- OpenRouter, *Models* — <https://openrouter.ai/docs/overview/models>
- Ouroboros (Q00/ouroboros) — <https://github.com/Q00/ouroboros> · <https://ouroboros.page/>
  (본문 인용은 로컬 설치본 `ouroboros-ai 0.54.4` 의 `config/_model_defaults.py`,
  `config/models.py`, `providers/litellm_adapter.py`, `providers/litellm_proof_worker.py`)
- oh-my-claudecode 4.15.4 — 로컬 플러그인 캐시의 `README.md` (Team Mode, CLI 워커, 요구사항)
- LiteLLM, *OpenRouter provider* — <https://docs.litellm.ai/docs/providers/openrouter>
