---
layout: post
title: "Quant-X 읽기 — 패스트캠퍼스 금융 멀티에이전트 교재 리포, README와 실제 배선을 나란히 놓고 보기"
date: 2026-11-10 22:10:47 +0900
categories: [ai, agent]
tags: [multi-agent, smolagents, fintech, governance, rag, faiss, streamlit, code-review]
---

> 대상: [h-albert-lee/fastcampus-domain-multiagent](https://github.com/h-albert-lee/fastcampus-domain-multiagent) (커밋 `6aded5a`, 2025-12-05). 패스트캠퍼스 금융 AI 에이전트 강의용 예제다. 이 글은 리포를 직접 클론해 코드를 읽고 정리한 것이며, 실행은 하지 않았다(OpenAI 키가 필요한 경로를 돌리지 않음). 코드 위치는 `QuantX_Project/` 기준 `파일:줄`로 적는다.

## 한 줄 요약

**Quant-X는 "금융권 AI 에이전트에 무엇이 붙어야 하는가"를 보여 주는 지도로는 훌륭하다.** 매니저·리서처·애널리스트 3개 에이전트, 인증·감사로그·가드레일로 된 거버넌스 층, 합성 DART 공시 RAG, 사람 승인(HITL) 버튼까지 갖췄다. 다만 **README가 말하는 통제 중 일부는 코드에서 실제 요청 흐름에 연결돼 있지 않다.** 교재로 쓸 때는 이 차이를 숨은 버그가 아니라 "거버넌스는 선언이 아니라 배선"이라는 실습 과제로 다루면 가장 많이 배울 수 있다.

## 1. 무엇을 만드는 리포인가

README의 소개는 이렇다. "전문화된 AI 에이전트들이 협업하여, 시스템의 통제 하에 역할별 최적화된 금융 분석을 수행한다." 화면은 Streamlit 3탭(종합 상황판, 리서치 센터, 시장 분석실)과 관리자 대시보드로 구성된다.

| 층 | 구성 | 파일 |
| --- | --- | --- |
| UI | Streamlit, 로그인·요청·HITL·관리자 대시보드 | `app.py` (940줄) |
| 거버넌스 | ID 기반 역할(RBAC), 감사 로그, 입출력 가드레일 | `core/auth.py`, `core/logger.py`, `core/guardrails.py` |
| 지식 | HuggingFace 데이터셋 → 1000자 청크(200 겹침) → OpenAI 임베딩 → FAISS | `core/rag_engine.py` |
| 실행 | smolagents `CodeAgent` 3개 + 도구 5개 | `agents/core.py`, `agents/tools.py` |

파이썬 코드는 약 4,300줄이다. 주석이 아주 많은데, README가 말하는 "왜 금융 도메인에서 이런 처리가 필요한지"를 설명하는 교육용 주석이다.

**데이터.** 사내 지식베이스는 [`nmixx-fin/synthetic_dart_report_korean`](https://huggingface.co/datasets/nmixx-fin/synthetic_dart_report_korean)과 [`nmixx-fin/synthetic_financial_report_korean`](https://huggingface.co/datasets/nmixx-fin/synthetic_financial_report_korean)이다(`core/rag_engine.py:119-145`). 이름 그대로 **합성(synthetic)** 데이터다. 실제 공시를 쓰지 않고도 "사내 데이터 우선 검색"을 연습할 수 있게 한 선택은 교육용으로 적절하다. 대신 여기서 나온 답을 실제 기업 정보로 읽으면 안 된다.

**역할.** ID에 `senior`가 들어 있으면 Senior Manager, 아니면 Junior Analyst가 된다(`core/auth.py:92`). 둘의 차이는 리포트 저장과 민감 데이터 접근 권한이다. 비밀번호는 없다. 코드 주석이 "교육 목적으로 ID 기반 간단 인증을 구현"한다고 밝혀 두었다.

**API 키 없이도 돈다.** 키가 없으면 데모 모드로 바뀌어 미리 준비한 응답을 보여 준다. 강의실에서 키 문제로 실습이 멈추지 않게 한 배려다.

## 2. 잘 짠 부분

- **층 분리가 눈에 보인다.** UI, 거버넌스, 실행이 디렉터리로 나뉘어 있다. "에이전트 코드에 보안을 섞지 말고 바깥 층에서 감싼다"는 설계 의도를 수강생이 파일 구조만 보고도 알 수 있다.
- **도구 미들웨어 패턴.** `middleware_wrapper`(`agents/tools.py:42`)는 모든 도구 호출의 시작·종료·소요시간·예외를 기록한다. 예외가 나도 에이전트를 죽이지 않고 문자열로 돌려준다. 주석의 표현대로 "에이전트는 감시받는 줄 모르지만 행위는 남는다"는 구조다. 금융권 감사 요구를 코드로 옮기는 첫 단추로 좋은 예시다.
- **권한은 도구 안에서 다시 검사한다.** `save_report`는 UI에서 버튼을 숨기는 데 그치지 않고, 도구 본문에서 `check_permission`을 다시 부른다(`agents/tools.py:290`). LLM이 도구를 마음대로 불러도 권한 검사가 뚫리지 않게 하는 올바른 위치다.
- **출처를 붙인다.** 사내 검색 결과마다 `[출처: 사내 데이터]`를 붙인다(`agents/tools.py:112`). 에이전트가 쓴 보고서가 어디서 왔는지 거슬러 올라가게 하려는 의도다.
- **HITL.** 보고서에 "승인 / 재작성 요청" 버튼이 있고, 재작성 지시는 원래 요청에 덧붙여 다시 실행된다(`app.py:642-676`). 승인한 보고서는 권한이 있을 때만 저장된다.
- **금융 면책 문구 자동 첨부, 규제 위반 표현 점수화**(`core/guardrails.py:487-578`) 같은 도메인 특화 장치도 들어 있다.

## 3. README와 코드가 다른 곳 — 교재로서 가장 값진 부분

아래는 버그 사냥이 아니다. "금융권 거버넌스를 말로 선언하는 것"과 "모든 경로에 실제로 연결하는 것"의 차이를 보여 주는 실례다. 강의 과제로 내기 좋은 순서로 적었다.

### 3.1 "매니저가 하위 에이전트를 호출"은 고정 순서 파이프라인이다

README와 주석은 매니저를 오케스트레이터로 소개하고, "하위 에이전트들을 도구로 변환하여 매니저가 호출할 수 있도록 구성"한다고 적었다(`agents/core.py:512`). 실제 `_execute_management`(`agents/core.py:569-615`)는 이렇게 돈다.

1. `research_agent.research(request)`: 항상 실행
2. `analyst_agent.analyze(request)`: 항상 실행
3. 두 결과를 프롬프트에 붙여 매니저 `CodeAgent.run()`

매니저가 받는 도구는 `save_report` 하나뿐이고, 하위 에이전트는 도구로 넘어가지 않는다. 즉 **누구를 부를지 LLM이 정하는 구조가 아니라, 파이썬 코드가 순서를 정한 3단 파이프라인이다.** smolagents에는 하위 에이전트를 매니저에게 넘겨 LLM이 고르게 하는 `managed_agents` 인자가 있지만([smolagents 공식 예제](https://huggingface.co/docs/smolagents/examples/multiagents)), 이 리포는 쓰지 않는다.

이게 꼭 나쁜 선택은 아니다. 금융권에서는 **고정 파이프라인이 오히려 감사하기 쉽다.** 다만 교재라면 두 방식을 나란히 놓고 "통제 가능성 대 유연성"을 비교하게 하는 편이 낫다. 이름만 오케스트레이터인 상태로 두면 수강생이 개념을 잘못 익힌다.

### 3.2 입출력 가드레일은 만들어져 있지만 요청 흐름에서 불리지 않는다

`core/guardrails.py`(673줄)에는 `check_input`과 `filter_output`이 있다. API 키·비밀번호·카드번호·주민등록번호 정규식, OpenAI Moderation 호출, 특수문자 비율 검사, 면책 문구 첨부 기능을 갖췄다. 그런데 리포 전체를 `grep`하면 `app.py`가 가드레일에서 부르는 것은 관리자 대시보드용 `get_security_report()` 하나뿐이다(`app.py:234`, `app.py:814`). 사용자 요청을 에이전트에 넘기는 경로(`app.py:720-721`)에도, 에이전트 결과를 화면에 내보내는 경로에도 `check_input`과 `filter_output`은 없다.

진행 표시에는 "1️⃣ 보안 점검 중..."이 뜨지만, 이 단계는 `st.write` 뒤에 `time.sleep(1)`을 넣은 연출이다(`app.py:700-714`). 이어지는 "리서치 에이전트 작업 시작", "결과 취합 중" 표시도 모두 실제 실행 **전에** 1초 간격으로 찍힌다. README가 말하는 "실시간 협업 시각화"는 실행 과정을 보여 주는 화면이 아니라 미리 정해 둔 안내 문구다.

**실습 과제:** `process_request` 앞에 `check_input`, 뒤에 `filter_output`을 넣는다. 차단되면 에이전트를 아예 부르지 않게 한다. 진행 표시는 `collaboration_log`에서 실제 이벤트를 읽어 그리도록 바꾼다.

### 3.3 `add_base_tools=True`가 미들웨어 밖의 문을 연다

세 에이전트는 모두 `CodeAgent(..., add_base_tools=True)`로 만들어진다(`agents/core.py:117`, `316`, `525`). smolagents 소스를 보면 이 옵션은 `DuckDuckGoSearchTool`과 `VisitWebpageTool`을 도구 목록에 더한다(`python_interpreter`는 CodeAgent에서는 제외된다). [`default_tools.py`의 `TOOL_MAPPING`](https://github.com/huggingface/smolagents/blob/main/src/smolagents/default_tools.py)과 [`agents.py`의 `_setup_tools`](https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py)에서 확인할 수 있다.

이 내장 도구들은 `middleware_wrapper`로 감싸지지 않는다. 그래서 **에이전트가 리포가 만든 `search_web` 대신 내장 웹검색이나 웹페이지 방문을 쓰면, 그 호출은 도구 감사 로그에 남지 않는다.** "모든 도구 호출을 감시하는 투명한 미들웨어"라는 README의 약속은 이 경로에서 깨진다. 리서처에게 "사내 검색 우선"을 기대한다면 오히려 외부 우회로를 여는 셈이다.

**실습 과제:** `add_base_tools=False`로 바꾸고, 필요한 외부 도구는 직접 감싸서 넣는다.

### 3.4 "변조 불가능한 감사 로그"는 일반 파일 로그다

미들웨어 주석은 도구 호출을 "변조 불가능한 로그로 기록"한다고 적었다(`agents/tools.py:46`). 실제 미들웨어는 표준 `logging` 로거에 `info`와 `error`를 남길 뿐이다. 구조화된 감사 함수 `audit_logger.log_audit`은 가드레일 안에서만 불리는데(`core/guardrails.py:465`), 3.2에서 봤듯 가드레일 자체가 요청 흐름에서 불리지 않는다. 그래서 **도구 호출은 관리자 대시보드의 감사 로그 화면(메모리 버퍼)에 나타나지 않는다.** 로그 파일에는 해시 체인이나 추가 전용(append-only) 저장 같은 무결성 장치도 없다.

교육용 단순화로는 이해할 수 있지만, 주석은 "변조 방지 고려사항을 이해"하는 수준으로 낮추는 편이 정확하다. 실제로 변조를 막으려면 레코드마다 이전 레코드의 해시를 넣는 체인, WORM 저장소, 외부 로그 수집기로의 즉시 전송 중 하나는 있어야 한다.

### 3.5 인증·세션이 프로세스 전역 싱글턴이다

`auth_manager = AuthenticationManager()`(`core/auth.py:267`)는 모듈 수준 객체다. `current_session`도 하나뿐이다. 협업 로그 `AGENT_SESSION_STATE`(`agents/core.py:49`)도 전역 dict다. Streamlit은 한 서버 프로세스가 여러 브라우저 세션을 처리하므로, **두 사람이 동시에 로그인하면 나중 사람의 역할이 앞사람의 도구 권한 검사에 쓰일 수 있다.** 예를 들어 Junior가 실행 중일 때 다른 탭에서 senior가 로그인하면, Junior 요청의 `save_report` 검사가 senior 권한으로 통과할 수 있다. 혼자 실습할 때는 드러나지 않는 종류의 결함이다.

**실습 과제:** 세션을 `st.session_state`에 두고, 도구가 전역 대신 요청 컨텍스트에서 사용자를 받게 한다.

### 3.6 작은 것들

- README는 웹검색을 "Serper API"라고 하지만, 코드는 `ddgs`(DuckDuckGo)를 쓴다(`agents/tools.py`, `requirements.txt`).
- `check_permission`은 인자를 하나(`permission`)만 받는다(`core/auth.py:140`). 그런데 `get_all_tools`는 `check_permission(user_id, 'save_report')`로 두 개를 넘긴다(`agents/tools.py:453`). 이 함수는 단일 에이전트 버전(`agents/single_core.py`)에서만 쓰여 현재 앱 경로에는 영향이 없다.
- `check_permission`은 독스트링에 "bool을 반환"한다고 적혀 있지만, 권한이 없으면 `PermissionError`를 던진다. 호출하는 쪽마다 처리가 갈린다.
- 의존성이 모두 하한만 지정돼 있다(`smolagents>=0.3.0`, `langchain>=0.1.0` 등). 이 리포가 쓰는 import 경로를 보면, 시간이 지나면 설치가 깨지기 쉬운 조합이다. 강의 시점의 버전을 `requirements.lock`으로 고정해 두는 편이 수강생에게 친절하다.
- README에는 "MIT 라이선스 하에 배포"라고 적혀 있지만, 리포에 `LICENSE` 파일이 없다(GitHub API의 license 필드가 `null`). 가져다 쓸 생각이면 저자에게 확인하는 편이 안전하다.

## 4. CodeAgent를 금융권에 둘 때 한 가지 더

smolagents `CodeAgent`는 LLM이 쓴 파이썬 코드를 실제로 실행한다. 이 리포는 실행기를 따로 지정하지 않으므로 기본 로컬 실행기로 돈다. smolagents 공식 문서는 이렇게 적는다([Secure code execution](https://huggingface.co/docs/smolagents/tutorials/secure_code_execution)).

> 어떤 로컬 파이썬 샌드박스도 완전히 안전할 수는 없다. … 강건한 격리를 원한다면 E2B나 Docker 같은 원격 실행을 쓰는 것이 유일한 방법이다. (요약 번역)

금융권 사례라고 소개한다면, 이 부분은 주석 한 줄이 아니라 아키텍처 그림에 들어가야 할 항목이다. 거버넌스 층이 도구 호출은 감싸지만, LLM이 생성한 코드가 실행되는 공간 자체는 감싸지 않는다.

## 5. 정리 — 이 리포를 어떻게 쓰면 좋은가

| 목적 | 권장 |
| --- | --- |
| 금융 에이전트에 붙어야 할 부품 목록 익히기 | 그대로 읽는다. 층 구분과 주석이 친절하다 |
| 멀티에이전트 오케스트레이션 배우기 | 3.1을 보고 `managed_agents` 버전을 직접 만들어 비교한다 |
| 거버넌스 실습 | 3.2~3.5를 과제로 삼아 "선언된 통제"를 "배선된 통제"로 바꾼다 |
| 실제 서비스의 출발점 | 권하지 않는다. 인증, 세션 격리, 로그 무결성, 코드 실행 격리를 다시 설계해야 한다 |

이 리포의 가장 큰 교훈은 의도하지 않은 곳에 있다. **보안 기능이 파일로 존재한다는 것과 그 기능이 모든 요청 경로에서 실행된다는 것은 별개다.** 금융권 감사는 앞의 것이 아니라 뒤의 것을 본다.

## 근거의 한계

- 코드를 읽고 `grep`한 결과만 근거로 삼았다. 실제로 실행해서 확인하지는 않았다. 특히 3.5의 세션 혼선은 구조상 가능하다는 판단이고, 재현 실험은 하지 않았다.
- 분석 대상은 커밋 `6aded5a`(2025-12-05)다. 이후 커밋이나 강의에서 실제로 쓰인 버전과 다를 수 있다.
- 강의 본편이 3장의 차이를 일부러 과제로 남겼을 가능성도 있다. 강의 내용은 보지 못했다.
- smolagents 동작(`add_base_tools`, `managed_agents`)은 글을 쓰는 시점의 `main` 브랜치 소스와 공식 문서 기준이다. 리포가 요구하는 최소 버전(0.3.x)과는 세부가 다를 수 있다.

## References

**[1차] 분석 대상**
1. h-albert-lee, [fastcampus-domain-multiagent](https://github.com/h-albert-lee/fastcampus-domain-multiagent), commit `6aded5a`, 2025-12-05

**[공식] 프레임워크 문서·소스**
2. Hugging Face, [smolagents — Orchestrate a multi-agent system](https://huggingface.co/docs/smolagents/examples/multiagents)
3. Hugging Face, [smolagents — Secure code execution](https://huggingface.co/docs/smolagents/tutorials/secure_code_execution)
4. smolagents 소스 — [`agents.py`](https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py) (`add_base_tools`, `managed_agents`), [`default_tools.py`](https://github.com/huggingface/smolagents/blob/main/src/smolagents/default_tools.py) (`TOOL_MAPPING`)

**[1차] 데이터셋**
5. nmixx-fin, [synthetic_dart_report_korean](https://huggingface.co/datasets/nmixx-fin/synthetic_dart_report_korean), [synthetic_financial_report_korean](https://huggingface.co/datasets/nmixx-fin/synthetic_financial_report_korean) (Hugging Face Datasets)
