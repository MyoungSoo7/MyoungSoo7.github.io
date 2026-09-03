---
layout: post
title: AI 그래프 엔지니어링에서 context와 memory — 최적화 방향이 반대인 두 자원
date: 2026-09-03 18:41:47 +0900
categories: [AI, Architecture]
tags: [Agent, LangGraph, Context Engineering, Memory]
---

에이전트를 그래프로 짜기 시작하면 노드마다 같은 질문을 다시 만난다. **"이 노드에 뭘 넘겨줄까."**

이 질문에 답하다 보면 context와 memory가 뒤섞인다. 둘 다 "모델이 보는 상태"처럼 보이기 때문이다. 그런데 실제로는 **최적화 방향이 정반대인 자원**이다. context는 줄이는 게 목적이고, memory는 남기는 게 목적이다. 이 둘을 한 규칙으로 다루면 반드시 한쪽이 망가진다.

이 글은 그 구분을 붙들고, 그래프 구조가 왜 이 문제에 유리한 형식인지 정리한 것이다.

## 1. 정의부터 못 박기

Anthropic은 [context를 "LLM에서 샘플링할 때 포함되는 토큰의 집합"](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)이라고 정의한다. 그리고 context engineering을 "그 토큰들의 효용을 LLM의 본질적 제약에 맞춰 최적화하는 문제"로 규정한다. 핵심은 **매 추론마다 새로 구성된다**는 점이다.

memory는 반대다. LangGraph 공식 문서는 persistence를 두 층으로 나눈다.

> LangGraph's persistence layer gives agents short-term memory through checkpointers and long-term memory through stores.

- **[Checkpointer](https://docs.langchain.com/oss/python/langgraph/persistence)** — 스레드 스코프의 단기 기억. 대화 연속성, human-in-the-loop, time travel, 장애 복구.
- **[Store](https://docs.langchain.com/oss/python/langgraph/persistence)** — 그래프 상태 바깥에 애플리케이션이 정의한 데이터를 저장. 스레드를 가로지르는 장기 기억으로, 사용자 선호·사실·공유 지식이 여기 들어간다. [JSON 문서를 namespace와 key로 조직한다.](https://docs.langchain.com/oss/python/langchain/long-term-memory)

정리하면 이렇다.

| | context | memory |
|---|---|---|
| 생명주기 | 매 추론마다 재구성 | 턴·세션을 넘어 지속 |
| 목표 | 최소한의 고신호 토큰 | 나중에 필요한 것의 보존 |
| 실패 모드 | 희석·주의 분산 | 유실·스테일·무한 증식 |
| 비용 | 토큰·지연 | 스토리지·정합성 |

그래프의 엣지를 타고 흐르는 state는 사실 이 둘 중 어느 것도 아니다. **둘을 잇는 파이프**다. 그래서 그래프 설계란 상당 부분 "이 파이프의 굵기를 정하는 일"이 된다.

## 2. context를 무한정 늘릴 수 없는 이유

"컨텍스트 창이 커지면 해결되는 문제 아닌가"가 첫 반론이다. 두 가지 근거가 그렇지 않다고 말한다.

**첫째, 위치가 성능을 바꾼다.** Liu 등의 [Lost in the Middle](https://arxiv.org/abs/2307.03172) (2023)은 multi-document QA와 key-value retrieval에서 관련 정보의 **위치만 바꿔도** 성능이 크게 떨어진다는 걸 보였다. 논문의 표현을 그대로 옮기면, 성능은 관련 정보가 입력의 **처음이나 끝**에 있을 때 가장 높고, **중간**에 있을 때 크게 떨어진다 — 그리고 이건 명시적으로 long-context를 표방한 모델에서도 관찰된다.

**둘째, 어텐션은 유한한 예산이다.** Anthropic은 이를 **context rot**으로 부른다. 컨텍스트 창의 토큰 수가 늘수록 그 안의 정보를 정확히 회수하는 능력이 떨어지고, 이 특성은 정도의 차이는 있어도 모든 모델에서 나타난다는 것이다. 구조적 원인도 명시한다 — 트랜스포머 어텐션은 n개 토큰에 대해 n² 쌍 관계를 만들고, 컨텍스트가 길어질수록 그 관계 포착 능력이 얇게 늘어난다. 게다가 모델은 짧은 시퀀스가 흔한 학습 분포에서 어텐션 패턴을 익힌다.

같은 글은 이걸 "하드 클리프가 아니라 성능 기울기(performance gradient)"라고 표현한다. 갑자기 고장 나는 게 아니라 조용히 정밀도가 깎인다는 뜻인데, **엔지니어링 관점에서는 이게 더 나쁘다.** 테스트에서 안 잡힌다.

그래프 설계에 주는 함의는 분명하다. **attention budget은 그래프 전체가 공유하는 전역 자원이다.** 노드가 열 개인데 각 노드가 "일단 다 넘겨" 하는 습관을 가지면, 어느 노드도 단독으로는 잘못한 게 없는데 그래프 끝의 노드가 조용히 틀린다.

## 3. memory의 계층 — 결국 OS 이야기

memory 쪽 설계는 놀랍도록 오래된 아이디어로 수렴한다.

[MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) (2023)는 이를 **virtual context management**라고 부른다. 논문의 착안점은 전통적 운영체제의 계층적 메모리다 — 빠른 메모리와 느린 메모리 사이에서 데이터를 옮겨 큰 메모리가 있는 것처럼 보이게 하는 그 기법을, 제한된 컨텍스트 창 위에 그대로 얹었다.

LangGraph의 checkpointer / store 구분은 사실상 같은 구도의 엔지니어링 구현이다. 활성 작업 세트(스레드)와 영속 저장소(크로스 스레드)를 분리하고, 그 사이의 이동을 명시적으로 만든 것이다.

Anthropic의 [memory tool](https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool)은 여기에 파일 시스템이라는 인터페이스를 준다. `/memories` 디렉토리 아래 파일을 만들고 읽고 고치고 지우며, 세션을 넘어 지식을 쌓는다. 문서가 강조하는 두 가지가 인상적이다.

- **just-in-time 회수** — 관련 정보를 전부 미리 올리는 대신, 배운 걸 파일로 적어두고 필요할 때 읽는다.
- **클라이언트 사이드 실행** — Claude가 파일 연산을 *요청*하고, 실행은 애플리케이션이 한다. 저장 위치와 방식의 통제권이 사용자 인프라에 남는다.

즉 memory는 "모델 안의 무언가"가 아니라 **모델 바깥의, 우리가 운영해야 하는 시스템**이다. 이 문장이 이 글의 절반이다.

## 4. 그래프에서 실제로 부딪히는 자리

추상적인 구분은 코드에서 부딪힐 때 비로소 쓸모가 생긴다. LangGraph 공식 문서의 트러블슈팅 항목들이 이 구분을 정확히 드러낸다.

**(a) 서브그래프 경계에서 상태가 안 보인다.** 서브그래프가 상태를 갱신해도 부모 그래프가 즉시 못 볼 수 있다. [공식 설명은 각 서브그래프가 자기 체크포인트 네임스페이스를 갖기 때문이라고 말하고, 그래프 경계를 넘어야 하는 데이터는 Store를 쓰라고 권한다.](https://docs.langchain.com/oss/python/langgraph/persistence)

이건 단순한 버그 회피가 아니다. **"context는 로컬, memory는 전역"이라는 구분이 코드로 드러나는 자리**다. 경계를 넘고 싶은 데이터가 있다면, 그건 애초에 context가 아니라 memory였던 것이다.

**(b) 체크포인트가 무한 증식한다.** 긴 대화에서 체크포인트는 계속 쌓이고, 지연과 스토리지 비용을 올린다. 공식 문서의 처방은 주기적 정리 또는 보존 정책이며, 문서의 코드 예시에는 이런 주석이 그대로 붙어 있다.

```python
# Consider adding a cron job to delete checkpoints older than N days
```

memory 설계의 본체는 쓰기가 아니라 **버리는 정책**이다. 무엇을 남길지만 정하고 언제 지울지를 안 정한 메모리는, 배포 후 몇 주가 지나야 문제가 드러난다.

**(c) `InMemorySaver`는 재시작하면 다 날아간다.** 공식 문서가 별도 항목으로 적어둘 만큼 흔한 함정이다. 프로덕션에서는 `PostgresSaver`나 `SqliteSaver`를 쓰라고 명시한다. **"메모리가 있다"와 "메모리가 지속된다"는 다른 말이다.**

**(d) 서브에이전트로 컨텍스트를 격리한다.** Anthropic은 이를 컨텍스트 한계를 우회하는 별도 축으로 제시한다 — 하나의 에이전트가 프로젝트 전체의 상태를 이고 가는 대신, 전문 서브에이전트가 **깨끗한 컨텍스트 창**으로 좁은 작업을 맡는다. 상세한 탐색 컨텍스트는 서브에이전트 안에 격리되고, 리드 에이전트는 결과의 종합과 분석에 집중한다.

그래프로 보면 이건 노드가 아니라 **경계를 하나 더 그은 것**이다. 노드는 상태를 공유하고, 서브에이전트는 공유하지 않는다.

## 5. context를 줄이는 레버들

Anthropic은 장기 과업에서 쓸 레버를 세 가지로 정리하고, **선택 기준까지 명시한다.**

1. **Compaction** — 컨텍스트 한계에 다다른 대화를 요약해 새 컨텍스트 창으로 재시작. Claude Code의 구현은 아키텍처 결정·미해결 버그·구현 세부는 보존하고 중복된 툴 출력과 메시지는 버린다. → **왕복이 많은 대화형 과업**에 맞는다.
2. **Structured note-taking (agentic memory)** — 컨텍스트 창 바깥에 노트를 남기고 나중에 다시 끌어온다. 투두 리스트나 `NOTES.md` 수준의 단순한 패턴으로 영속 기억을 얻는다. → **마일스톤이 뚜렷한 반복 개발**에 맞는다.
3. **Sub-agent 아키텍처** → **병렬 탐색이 이득인 조사·분석**에 맞는다.

여기에 API 레벨의 레버가 하나 더 있다. [Context editing](https://docs.claude.com/en/docs/build-with-claude/context-editing)은 대화 이력에서 특정 내용을 선택적으로 지운다 — **tool result clearing**(툴을 많이 쓰는 에이전트 워크플로에서 오래된 툴 결과를 제거)과 **thinking block clearing**이다. 문서 자체가 목적을 이렇게 적는다. "비용과 한계 관리를 넘어, **Claude가 보는 것을 능동적으로 큐레이션하는 일**이다."

Anthropic이 말하는 **just-in-time** 전략도 같은 계열이다. 모든 데이터를 미리 처리해 올리는 대신 파일 경로·저장된 쿼리·웹 링크 같은 **경량 식별자**만 들고 다니다가, 런타임에 도구로 필요한 것만 로드한다. Claude Code는 하이브리드다 — `CLAUDE.md` 같은 파일은 앞에 그냥 올려두고, glob과 grep으로 나머지를 JIT으로 가져온다. 문서는 그 대가도 정직하게 적는다. **런타임 탐색은 미리 계산된 데이터를 가져오는 것보다 느리다.**

## 6. 고찰 — 왜 그래프인가

여기까지가 출처로 뒷받침되는 부분이고, 아래는 이걸 운영해 본 내 판단이다.

**첫째, 그래프의 진짜 이점은 병렬성이 아니라 경계다.** 긴 단일 대화 루프에는 경계가 없다. 모든 게 누적되고, 무엇을 버릴지는 사후에 판단해야 한다. 반면 그래프에서는 **노드 경계가 곧 컨텍스트 경계**이고, 엣지는 "무엇을 넘길지"를 코드에 명시하도록 강제한다. 삭제 판단이 사후가 아니라 설계 시점으로 당겨진다. 이게 그래프가 에이전트 형식으로서 갖는 가장 실질적인 가치라고 본다.

**둘째, 노드 출력은 로그가 아니라 요약이어야 한다.** 노드가 자기 작업 기록을 그대로 다음 노드에 넘기기 시작하면, 그래프는 형태만 그래프인 하나의 긴 대화가 된다. n²는 그래프 모양을 봐주지 않는다.

**셋째, 크로스 노드 데이터는 state가 아니라 Store로 보낸다.** 서브그래프 네임스페이스 문제는 버그가 아니라 신호다. 여러 노드가 봐야 하는 데이터라면 그건 이미 memory의 성격을 가진 것이고, 파이프로 실어 나르는 대신 저장소에 두고 필요한 노드가 꺼내 쓰는 게 맞다.

**넷째, 저장 경로보다 회수 경로가 자주 깨진다.** 상주 에이전트를 여러 대 두고 memory 디렉토리를 주기적으로 동기화하는 구성을 운영해 보면, 실제로 자주 실패하는 건 쓰기가 아니다. 파일은 잘 동기화되는데 세션이 그걸 읽는 시점이 없어서 아무 일도 일어나지 않는다. **디스크에 있다는 것과 모델이 안다는 것은 다른 말이다.** 회수 경로 — 언제, 어떤 트리거로, 어느 노드가 그 파일을 읽는가 — 를 같이 설계하지 않은 memory는 memory가 아니라 그냥 파일이다.

이건 앞의 (c)와 같은 종류의 실수다. `InMemorySaver`는 "저장했는데 재시작하면 없다"이고, 동기화만 된 memory 파일은 "저장했는데 아무도 안 읽는다"이다. 층위만 다르지 증상은 같다 — **확인한 층위보다 한 칸 위를 완료로 보고한 것.**

**다섯째, 메모리에는 만료 정책을 함께 설계한다.** 공식 문서가 cron 주석을 남길 정도라면 그건 흔한 실패다. 무엇을 저장할지 정하는 회의에서 언제 지울지도 같이 정해야 하고, 안 정하면 기본값은 "영원히"가 된다.

## 마무리

context와 memory는 이름이 비슷하고 자료구조도 비슷해 보이지만, 한쪽은 **줄여야 이기는 게임**이고 다른 쪽은 **남겨야 이기는 게임**이다.

그래프는 이 둘을 분리하기 좋은 형식이다 — 노드 경계가 컨텍스트를 자르고, Store가 그 경계를 넘는 것들을 받아준다. 다만 형식이 자동으로 해주지는 않는다. 엣지에 무엇을 실을지, 노드 출력을 어디까지 요약할지, 저장한 것을 언제 다시 읽을지를 **사람이 정해야** 한다.

Anthropic의 글이 결론에서 한 말이 이 지점을 잘 짚는다. 모델이 좋아질수록 규정적인 엔지니어링은 덜 필요해지겠지만, **context를 귀하고 유한한 자원으로 다루는 일은 계속 핵심으로 남는다.**

---

## References

- Anthropic, "[Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)" — context 정의, context rot, attention budget, compaction / note-taking / sub-agent, just-in-time 전략
- Anthropic, "[Context editing](https://docs.claude.com/en/docs/build-with-claude/context-editing)" — tool result clearing, thinking block clearing
- Anthropic, "[Memory tool](https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool)" — `/memories` 파일 기반 영속 기억, 클라이언트 사이드 실행
- LangChain, "[Persistence (LangGraph)](https://docs.langchain.com/oss/python/langgraph/persistence)" — checkpointer / store 구분, 서브그래프 네임스페이스, 체크포인트 보존 정책, `InMemorySaver` 휘발성
- LangChain, "[Long-term memory](https://docs.langchain.com/oss/python/langchain/long-term-memory)" — namespace / key 기반 JSON 문서 저장
- LangChain, "[Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)" — trim / delete / summarize 패턴
- N. F. Liu et al., "[Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172)", arXiv:2307.03172 (2023) — 관련 정보의 위치에 따른 성능 저하
- C. Packer et al., "[MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)", arXiv:2310.08560 (2023) — virtual context management, 계층적 메모리
