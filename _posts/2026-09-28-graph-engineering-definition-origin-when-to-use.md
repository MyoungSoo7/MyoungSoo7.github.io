---
layout: post
title: "그래프 엔지니어링이란 무엇인가 — 루프 다음 유행어의 정의, 계보, 쓸 때와 안 쓸 때"
date: 2026-09-28 23:02:54 +0900
categories: [ai]
tags: [graph-engineering, agent, langgraph, loop-engineering, dspy, multi-agent]
---

2026년 여름 AI 개발자 사이에서 새 이름이 하나 돌기 시작했다. **그래프 엔지니어링(graph engineering)**. 프롬프트 → 컨텍스트 → 하네스 → 루프 엔지니어링 다음 칸에 놓인 말이다. 이 글은 세 가지를 정리한다. 이 말이 정확히 무엇을 가리키는지, 무엇이 새롭고 무엇이 새롭지 않은지, 그리고 언제 쓰고 언제 쓰지 말아야 하는지.

> 같은 블로그의 [「AI 그래프 엔지니어링에서 context 와 memory」](/2026/09/03/ai-graph-engineering-context-and-memory/)가 "노드에 무엇을 넘길까"를 다뤘다면, 이 글은 한 단계 위에서 "그래프라는 틀 자체"를 다룬다.

## 한 줄 정의

현재 가장 포괄적인 학술 정의는 2026년 8월 arXiv 서베이 [Graph Engineering in the Era of LLM Agents](https://arxiv.org/abs/2608.21156)(Feng 외 34인)에 있다. 이 서베이는 그래프 엔지니어링을 **과업·에이전트·시스템 상태를 명시적이고 동적으로 진화하는 그래프 구조로 표현해** 여러 에이전트를 조직하는 패러다임으로 정의한다. 앞선 패러다임이 "개별 상호작용이나 에이전트 한 개의 행동"을 최적화했다면, 그래프 엔지니어링은 **시스템 차원의 조직**을 다룬다는 것이다.

실무 쪽 정의는 더 짧다. 한마디로 **제어권의 위치를 옮기는 일**이다.

| 층위 | 무엇을 설계하나 | 다음 행동은 누가 정하나 |
|------|----------------|------------------------|
| 프롬프트 | 모델에게 보내는 말 | 모델(한 턴) |
| 컨텍스트 | 모델이 보는 토큰 | 모델(한 턴) |
| 하네스 | 도구·메모리·권한 등 주변 장치 | 모델 |
| 루프 | 한 에이전트가 끝날 때까지 반복하는 주기 | 모델(루프 안에서) |
| **그래프** | 노드·엣지·공유 상태·체크포인트 | **엔지니어가 미리 그린 구조** + 필요한 노드에서만 모델 |

이 구분은 Anthropic 이 2024년 12월 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)에서 나눈 두 범주와 정확히 겹친다. 그 글은 **워크플로(workflow)**를 "LLM 과 도구가 미리 정의된 코드 경로를 통해 조율되는 시스템"으로, **에이전트(agent)**를 "LLM 이 스스로 과정과 도구 사용을 동적으로 지휘하는 시스템"으로 구분했다. 그래프 엔지니어링은 결국 워크플로 쪽 설계를 여러 에이전트 규모로 끌어올린 이름이다.

## 어디서 왔나 — 이름은 새롭고, 구조는 오래됐다

### 이름: 2026년 7월 X

이 말이 퍼진 계기는 기술 발표가 아니라 X 게시물이었다. 2026년 7월 18일 OpenClaw 창업자 피터 스타인버거가 "아직 루프 얘기 중이야, 아니면 그래프로 넘어갔어?"라고 물었고, 같은 날 "루프 엔지니어링은 죽었다"는 해설 글이 뒤따랐다. 이 경위는 X 원문이 아니라 업계 해설 기사([Towards Data Science, 2026-09-14](https://towardsdatascience.com/graph-engineering-for-ai-agents-from-prompts-and-loops-to-workflows/))를 기준으로 옮긴 것이다.

나흘 뒤인 7월 22일, LangChain 은 공식 블로그에 [「3 Years of Graph Engineering with LangGraph」](https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph)를 올렸다. 요지는 두 문장이다.

> "Graph engineering isn't a new idea. It's the latest name for a well established approach to building reliable agents."
>
> "Loop engineering isn't an alternative to graphs, so much as a simple version of them."

그래프 엔지니어링은 새 아이디어가 아니라 신뢰할 수 있는 에이전트를 만드는 기존 방식의 최신 이름이고, 루프는 그래프의 대안이 아니라 그래프의 단순한 형태(방향성 순환 그래프)라는 말이다. 벤더의 자기 홍보성 글이라는 점은 감안해야 하지만, 두 번째 문장은 정의상 참이다. 루프는 자기 자신으로 돌아오는 엣지 하나를 가진 노드다.

더 거슬러 올라가면 2024년 1월 CodiumAI 의 [AlphaCodium 논문](https://arxiv.org/abs/2401.08500)이 부제에서 이미 "From Prompt Engineering to **Flow Engineering**"이라고 썼다.

### 구조: 2021년부터 있었다

"LLM 호출을 노드로, 의존성을 엣지로" 보는 발상은 이름보다 훨씬 오래됐다.

| 연도 | 작업 | 기여 |
|------|------|------|
| 2021 | [AI Chains](https://arxiv.org/abs/2110.01691) (Wu 외, CHI 2022) | 프롬프트를 여러 단계로 쪼개 체인으로 연결, 사람이 단계별로 보고 고칠 수 있게 함 |
| 2023 | [DSPy](https://arxiv.org/abs/2310.03714) (Khattab 외) | LM 파이프라인을 텍스트 변환 그래프로 보고, 구조는 고정한 채 프롬프트를 **컴파일·최적화** |
| 2024 | [StateFlow](https://arxiv.org/abs/2403.11322) (Wu 외) | 도구를 쓰는 작업을 **상태 기계**로 모델링 |
| 2023~ | LangGraph, AutoGen GraphFlow, Prompt Flow 등 | 그래프 실행을 프레임워크 기본 개념으로 제공 |

그렇다면 무엇이 달라졌나. **노드 안에 들어가는 것**이다. 예전 노드는 프롬프트 한 번이었다. 지금은 도구를 쓰고 스스로 검증하며 수십 분씩 도는 에이전트 한 개가 통째로 노드가 된다. LangChain 글도 "전체 코딩·리서치 에이전트를 한 노드에 넣는 것"이 새로 실용화된 부분이라고 짚는다. 그래서 어려운 문제가 노드 안(프롬프트)에서 **노드 사이(배선)**로 옮겨갔다. 누가 누구에게 무엇을 넘기는지, 어느 가지가 실패하면 어떻게 되는지, 병렬로 흩어진 결과를 어디서 다시 모으는지가 설계 대상이 됐다. 연구도 같은 방향이다. 2026년 9월 [ReActNet](https://arxiv.org/abs/2609.05774)(Tieu 외)은 고정된 토폴로지를 쓰는 대신, 질의마다 추론 단계별 통신 그래프를 **컴파일**하고 엣지마다 "누가 누구에게 무엇을 전할지" 지시를 붙여 실행한다. 그래프를 짜는 일과 돌리는 일을 분리한 것이다.

## "그래프를 쓴다"의 기준 — 네 가지 조건

누구나 박스와 화살표는 그릴 수 있다. 그렇다면 어디서부터 "그래프 엔지니어링"인가. 2026년 7월 30일 Sandeco Macedo 의 프리프린트 [What makes prompts a graph](https://arxiv.org/abs/2607.27578)가 판별 기준 네 가지를 제안했다(동료심사 전 단독 저자 프리프린트).

| 조건 | 질문 | 떨어지면 |
|------|------|----------|
| G1 명시적 구조 | 실행하지 않고도 노드와 엣지를 나열할 수 있나? | 한 덩어리 프롬프트, 불투명한 스크립트 |
| G2 구조·내용 분리 | 프롬프트를 바꿔도 구조가, 구조를 바꿔도 프롬프트가 안 깨지나? | 용접된 체인 |
| G3 실행 의미론 | 런타임이 그 그래프를 실제로 스케줄·라우팅·상태관리 하나? | 그냥 아키텍처 그림 |
| G4 일급 산출물 | 그래프를 실행과 별개로 버전 관리·검증·최적화할 수 있나? | 실행 로그에만 남는 궤적 |

논문은 이 기준을 실제 시스템 여섯 개에 적용했다. LangGraph·DSPy·Prompt Flow 는 통과했고, AutoGen·CrewAI 는 모드에 따라 갈렸다(명시적 흐름은 통과, 자유 대화는 탈락). 흥미로운 결과는 **Claude Code 서브에이전트가 탈락**했다는 점이다. 서브에이전트라는 노드는 있지만 어느 것을 언제 부를지는 모델이 실행 중에 정하고, 그 흐름이 그래프로 저장되지 않기 때문이다. (이 글을 쓰는 Claude 도 Anthropic 제품이라 굳이 밝혀 둔다. 탈락이 곧 열등하다는 뜻은 아니다. 루프형 설계를 택했다는 분류일 뿐이다.)

실무에서 가장 중요한 조건은 G4 다. 그래프가 파일로 존재해야 diff 하고, 리뷰하고, 과거 실행을 재생하고, 롤백할 수 있다. 그림이 아니라 **코드 리뷰 대상**이 되는 것, 이것이 루프와 그래프의 운영상 차이다.

## 최소 예시 — 쓰고, 검토하고, 되돌린다

LangGraph 의 `StateGraph` 로 "작성 → 검토 → (반려 시) 재작성" 그래프를 그리면 이렇다. 구조는 코드에 있고, 모델은 `write`·`review` 노드 안에서만 판단한다.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    draft: str
    approved: bool
    attempts: int

def write(state: State) -> dict:
    # 여기서만 LLM 호출 (생략)
    return {"draft": "...", "attempts": state["attempts"] + 1}

def review(state: State) -> dict:
    # 검토용 LLM 또는 결정론적 검사 (생략)
    return {"approved": False}

def route(state: State) -> str:
    if state["approved"] or state["attempts"] >= 3:
        return END          # 순환에는 반드시 멈춤 조건
    return "write"

g = StateGraph(State)
g.add_node("write", write)
g.add_node("review", review)
g.add_edge(START, "write")
g.add_edge("write", "review")
g.add_conditional_edges("review", route)
app = g.compile()
```

이 코드에서 "몇 번까지 재시도하나", "반려되면 어디로 가나"는 모델이 아니라 `route` 함수가 정한다. 루프형 에이전트였다면 이 판단이 모델의 다음 토큰 안에 묻혀 있었을 것이다.

## 쓸 때와 안 쓸 때

Anthropic 의 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)는 가능한 가장 단순한 해법에서 출발하고, 필요할 때만 복잡도를 늘리라고 권한다. 에이전트형 시스템은 지연과 비용을 대가로 성능을 얻는 경우가 많다는 이유에서다. 그래프도 마찬가지다.

**그래프가 값을 하는 경우**

- 작업이 실제로 **갈라지고 다시 합쳐진다**(병렬 리서치 → 종합).
- **독립 검증**이 필요하다. 작성자와 검토자를 같은 루프에 두면 스스로에게 관대해진다.
- **사람 승인 게이트**가 있다. 배포·결제·메일 발송처럼 되돌리기 어려운 행동 앞에 멈춤 지점이 필요하다.
- 작업이 **컨텍스트 창이나 세션을 넘어** 이어져서, 중단된 지점부터 재개해야 한다.
- "왜 이 경로를 탔나"를 **사후에 설명**해야 한다(감사·규제).

**그래프가 짐이 되는 경우**

- 목표 하나, 권한 경계 하나, 측정 가능한 종료 조건 하나. 이런 작업이면 잘 만든 루프로 충분하다.
- 그래프를 그리는 이유가 "더 고급스러워 보여서"다. 에이전트 수를 늘린다고 좋은 그래프가 되지 않는다. 노드마다 **고유한 계약이나 실패 경계**가 없다면 그 노드는 분리할 이유가 없다.

## 정리 — 유행어에서 남길 것

"그래프 엔지니어링"이라는 말에서 걸러낼 것과 남길 것을 나누면 이렇다.

- **걸러낼 것:** "그래프가 루프를 대체한다"(루프는 그래프의 부분집합이다), "에이전트가 많을수록 좋다", "새 기술이 나왔다"(7월에 새로 나온 런타임은 없다).
- **남길 것:** 에이전트의 **작업 흐름을 모델 머릿속에서 꺼내, 버전 관리되는 코드 산출물로 만든다**는 원칙. 그러면 흐름을 리뷰하고, 테스트하고, 되돌릴 수 있다.

이름은 또 바뀔 것이다. 하지만 "제어 흐름을 명시적 산출물로 둔다"는 원칙은 AI Chains(2021)에서 DSPy, LangGraph 를 거쳐 지금까지 이어진 것이고, 다음 이름 아래에서도 살아남을 가능성이 높다.

## References

1. Feng, Y. et al., "Graph Engineering in the Era of LLM Agents: From Individual Intelligence to System Intelligence", arXiv:2608.21156, 2026. <https://arxiv.org/abs/2608.21156>
2. Macedo, S., "What makes prompts a graph: necessary and sufficient conditions for prompt graph engineering", arXiv:2607.27578, 2026 (프리프린트, 동료심사 전). <https://arxiv.org/abs/2607.27578>
3. Tieu, K. et al., "Inference-Time Graph Engineering for Multi-Agent LLM Workflows", arXiv:2609.05774, 2026. <https://arxiv.org/abs/2609.05774>
4. Runkle, S. & Chase, H., "3 Years of Graph Engineering with LangGraph", LangChain Blog, 2026-07-22 (벤더 글). <https://www.langchain.com/blog/3-years-of-graph-engineering-with-langgraph>
5. Anthropic, "Building effective agents", 2024-12. <https://www.anthropic.com/engineering/building-effective-agents>
6. Wu, T., Terry, M., Cai, C. J., "AI Chains: Transparent and Controllable Human-AI Interaction by Chaining Large Language Model Prompts", CHI 2022, arXiv:2110.01691. <https://arxiv.org/abs/2110.01691>
7. Khattab, O. et al., "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines", arXiv:2310.03714, 2023. <https://arxiv.org/abs/2310.03714>
8. Wu, Y. et al., "StateFlow: Enhancing LLM Task-Solving through State-Driven Workflows", arXiv:2403.11322, 2024. <https://arxiv.org/abs/2403.11322>
9. Ridnik, T., Kredo, D., Friedman, I., "Code Generation with AlphaCodium: From Prompt Engineering to Flow Engineering", arXiv:2401.08500, 2024. <https://arxiv.org/abs/2401.08500>
10. LangGraph 공식 문서. <https://docs.langchain.com/oss/python/langgraph/overview>
11. Hoang, N., "Graph Engineering for AI Agents: From Prompts and Loops to Workflows", Towards Data Science, 2026-09-14 (2차 해설, 7월 X 논쟁 경위 출처). <https://towardsdatascience.com/graph-engineering-for-ai-agents-from-prompts-and-loops-to-workflows/>
