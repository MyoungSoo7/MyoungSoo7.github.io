---
layout: post
title: "MCP 강의 자료 30편 정리 — 개념·전송·파일/SQLite 서버·OWASP, 그리고 공식 스펙과 어긋나는 9곳"
date: 2026-11-10 22:26:05 +0900
categories: [AI, MCP]
tags: [mcp, fastmcp, stdio, streamable-http, sqlite, owasp, llm-security, claude-code, gemini-cli]
---

> **검증 범위.** MCP 강의 PDF 30편(CH01 02–05, CH02 01–05, CH03 01–05, CH04 01–13, CH05 01–03)을 텍스트로 뽑아 **전부 읽었다.** 이 글은 그 내용을 요약한 것이다. 강의 속 코드는 **실행하지 않았다.** 사실관계는 MCP 공식 스펙(2025-11-25 리비전), Python·SQLite 공식 문서, OWASP 원문, 1차 보도로 대조했다. CH04-12·13 두 편은 PDF에 개요 두세 줄만 있다(실습은 영상 쪽으로 보인다). 그래서 이 두 편은 요약할 거리가 없다. 강의가 제시한 쿼터·임계치·가격 같은 숫자는 **예시값**이다. 1차 출처로 확인되지 않은 것은 옮기지 않았다.

## 0. 한 장 요약

| 장 | 다루는 것 | 한 줄 핵심 |
|---|---|---|
| CH01 | MCP 개념 | N×M 통합을 N+M으로. Tools·Resources·Prompts 세 원시 타입, JSON-RPC 2.0 |
| CH02 | 개발 환경 | conda → Git → Docker → devcontainer → Claude Code / Gemini CLI |
| CH03 | 첫 MCP 서버 | FastMCP 계산기, stdio vs Streamable HTTP, 클라이언트 설정, 생명주기 |
| CH04 | 실전 서버 | 파일 도구 4종(ls/read/write/edit) → SQLite 설계·CRUD·검색·파이프라인·리포트 |
| CH05 | 보안 | OWASP Top 10(2021) + OWASP LLM Top 10(2023 → 2025) |

## 1. CH01 — MCP가 푸는 문제

**N×M → N+M.** LLM 앱이 $N$개, 도구가 $M$개라고 하자. 각자 직접 연결하면 커넥터가 $N \times M$개 필요하다. 가운데에 표준 프로토콜을 두면 $N + M$개면 된다. 강의 예시로는 LLM 3개와 도구 5개가 있을 때 15개가 8개로 준다.

$$
\underbrace{N \times M}_{\text{직접 통합}} \;\longrightarrow\; \underbrace{N + M}_{\text{표준 프로토콜}}, \qquad 3 \times 5 = 15 \;\to\; 3 + 5 = 8
$$

강의는 이걸 ODBC와 USB-C에 빗댄다. MCP는 Anthropic이 2024-11-25에 공개했다([Anthropic](https://www.anthropic.com/news/model-context-protocol)). OpenAI는 2025-03-26에 Agents SDK부터 지원을 발표했다([TechCrunch](https://techcrunch.com/2025/03/26/openai-adopts-rival-anthropics-standard-for-connecting-ai-models-to-data/)).

**세 원시 타입**은 누가 쓰임을 결정하느냐로 나뉜다. 이 구분은 공식 스펙 표현 그대로다.

- **Tools**: 모델이 판단해 호출한다(model-controlled). 예: `tools/call`
- **Resources**: 호스트 앱이 컨텍스트에 넣는다(application-driven). 예: `resources/read`([스펙](https://modelcontextprotocol.io/specification/2025-11-25/server/resources))
- **Prompts**: 사용자가 골라 쓰는 템플릿이다(user-controlled).

**구성 요소**는 세 가지다. 호스트(Claude Desktop, IDE 같은 앱), 호스트 안에서 서버와 1:1로 연결되는 클라이언트, 그리고 기능을 노출하는 서버다.

**보안 위협**은 Red Hat 글([2025-06](https://www.redhat.com/en/blog/model-context-protocol-mcp-understanding-security-risks-and-controls))을 따라 다섯 가지로 묶는다.

1. **혼동된 대리인(confused deputy)**: 서버가 사용자 권한이 아니라 자기 권한으로 행동하는 문제.
2. **공급망**: 서버 자체가 실행 코드라는 점에서 생긴다. 서명, SAST, SCA로 대응한다.
3. **명령 주입**: 입력을 셸 인자로 그대로 넘길 때 생긴다.
4. **프롬프트 주입.**
5. **도구 주입(tool injection)**: 업데이트 뒤에 도구 설명이 악성으로 바뀌는 경우다. 대응은 버전 고정과 변경 알림이다.

**배포 형태.** 로컬 서버는 stdio로 붙는다. 원격 서버는 예전 HTTP+SSE를 거쳐 지금은 Streamable HTTP를 쓰고, 인증은 OAuth(PKCE)다.

## 2. CH02 — 개발 환경

CH02의 흐름은 다섯 단계다.

1. conda로 파이썬 환경을 나눈다.
2. Git/GitHub로 강의 리포를 clone하고 PR을 연습한다.
3. Docker의 개념(이미지·컨테이너·포트 매핑)을 VM·conda와 비교한다.
4. `devcontainer.json`(`name`·`image`·`extensions`·`postCreateCommand`·`forwardPorts`)으로 VS Code 개발 환경을 코드로 고정한다.
5. Claude Code(`npm i -g @anthropic-ai/claude-code`)와 Gemini CLI(`npm i -g @google/gemini-cli`)를 설치한다.

강의는 두 CLI의 무료 쿼터와 컨텍스트 길이도 비교한다. 이 수치는 벤더가 수시로 바꾸는 값이라 여기 옮기지 않는다. 쓰기 직전에 각 공식 문서에서 확인하는 게 맞다.

## 3. CH03 — 첫 MCP 서버

### 3-1. FastMCP 계산기 (stdio)

```python
from fastmcp import FastMCP
mcp = FastMCP("calculator")

@mcp.tool()
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("0으로 나눌 수 없음")   # 예외 → MCP 에러 응답
    return a / b

if __name__ == "__main__":
    mcp.run()          # 기본 전송 = stdio
```

**stdio 동작.** 클라이언트가 서버를 **자식 프로세스로 띄운다.** 그 서버의 stdin에 JSON-RPC를 쓰고, stdout에서 응답을 읽는다. 강의는 `fastmcp dev`로 Inspector를 띄워 테스트한다. 도커 안에서 띄울 때는 두 가지를 챙겨야 한다. Inspector는 localhost에만 붙고, HTTP 서버는 `0.0.0.0`에 바인드해야 컨테이너 밖에서 닿는다.

**FastMCP 버전.** FastMCP 1.0은 공식 Python SDK에 흡수됐다(`from mcp.server.fastmcp import FastMCP`). 2.0은 다시 독립 패키지 `fastmcp`로 나왔다([저자 블로그](https://jlowin.dev/blog/fastmcp-2), [gofastmcp](https://gofastmcp.com/docs/v2/getting-started/welcome)). 강의 코드는 2.x 쪽이다. 문서에 3.0 경고가 있으니 `fastmcp<3`처럼 상한을 거는 게 안전하다.

### 3-2. HTTP로 바꾸기

`mcp.run(transport="http", host="0.0.0.0", port=8080)` 한 줄이면 된다. 강의 실측으로는 `/`가 404, `/mcp/`가 406을 돌려준다. 406은 `Accept` 헤더에 `text/event-stream`이 없어서 생긴다. 스펙은 POST에 `application/json`과 `text/event-stream`을 둘 다 Accept로 요구한다([Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)).

### 3-3. 클라이언트 설정

Claude Code 기준 설정 위치는 세 가지다([Claude Code 문서](https://code.claude.com/docs/en/mcp-quickstart)).

- 프로젝트 공유용: `.mcp.json`
- 개인 전역: `~/.claude.json`의 최상위 `mcpServers`
- 개인·이 프로젝트만: `~/.claude.json`의 프로젝트 항목

stdio 서버는 `command`(파이썬 절대경로 권장)와 `args`로 등록한다.

### 3-4. 생명주기

생명주기는 **초기화 → 운영 → 종료** 세 단계다([Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)).

1. 클라이언트가 `initialize`를 보낸다.
2. 서버가 버전과 capabilities로 응답한다.
3. 클라이언트가 `notifications/initialized`를 보낸다.

`notifications/initialized`가 오기 전에는 서버가 ping과 로깅 말고 다른 요청을 보내면 안 된다(SHOULD NOT). 종료 전용 메시지는 없다. stdio에서는 stdin을 닫고 프로세스를 끝내는 것으로 종료한다.

CH03 마지막에는 Gemini CLI용 서버를 `uv`로 패키징한다. 강의가 `uv sync`의 entry-point 경고를 짚는데, 해법은 `[project.scripts]`를 선언하고 `tool.uv.package = true`를 켜는 것이다.

## 4. CH04 — 실전 서버: 파일 도구와 SQLite

### 4-1. 파일 도구 4종 (Gemini CLI 소스를 본뜸)

강의는 Gemini CLI의 `packages/core/src/tools`(`ls.ts`, `read-file.ts`, `write-file.ts`, `edit.ts`)를 읽고 파이썬으로 다시 만든다.

| 도구 | 설계 포인트 |
|---|---|
| `list_directory` | 절대경로·존재·디렉터리 여부 검증, `os.scandir`, `.gitignore`류 패턴(`fnmatch`) 제외, 디렉터리 먼저 정렬 |
| `read_file` | `offset`/`limit` 페이징, 응답에 `is_truncated`·`next_offset`·`original_line_count` |
| `write_file` | 부모 디렉터리 자동 생성 |
| `replace_in_file` | `old_string`/`new_string` + **`expected_replacements`** — 매치 개수가 예상과 다르면 아예 안 고친다 |

마지막 줄이 이 장의 핵심이다. LLM이 편집할 때는 "엉뚱한 곳 3군데를 고치는" 사고가 실제로 나기 때문에, 개수 불일치를 실패로 처리하는 가드가 들어간다. 이 함수들은 FastMCP 비동기 서버 안에서 `run_in_executor`로 감싸 노출한다. 테스트는 세 갈래다. LLM으로 pytest를 생성하는 법, 상태 기반 퍼징(Microsoft RESTler), 트래픽 녹화·재생(Keploy)이다.

### 4-2. SQLite 모듈

**설계.**
- 테넌트마다 DB 파일을 따로 두는 멀티테넌시.
- 1NF·2NF·3NF 정규화와 삽입·갱신·삭제 이상.
- 날짜 저장법 세 가지: ISO8601 TEXT, 율리우스 REAL, Unix INTEGER.
- 타입 선언은 `STRING`이 아니라 `TEXT`로 한다. `STRING`은 어느 규칙에도 안 걸려 NUMERIC 친화도가 된다([Datatypes](https://www.sqlite.org/datatype3.html)).
- 스키마 버전 관리는 dbmate(`migrate:up`/`down`, `schema_migrations`)로 한다.

**CRUD.** `?` 바인딩, `executemany`, `IntegrityError`/`OperationalError` 처리를 다룬다. Peewee ORM과도 비교한다.

**검색.** 세 부분으로 나뉜다.
- `QueryFilter`를 WHERE 절로 바꾼다.
- 정렬은 **허용 필드 화이트리스트**로 막는다. `ORDER BY`는 바인딩이 안 되기 때문이다.
- 페이지네이션은 아래 식으로 계산한다.

$$
\text{offset} = (\text{page} - 1) \times \text{page\_size}, \qquad \text{total\_pages} = \left\lceil \frac{\text{total\_count}}{\text{page\_size}} \right\rceil
$$

예를 들어 3페이지에 20건씩이면 `LIMIT 20 OFFSET 40`이다.

**파이프라인.**
- **파일 → DB**: 메타데이터를 추출한다. 텍스트는 `UnicodeDecodeError`가 나면 바이너리로 처리한다. `skip_existing`으로 멱등하게 만든다.
- **DB → 파일**: JSON·CSV·Markdown·Text 리포트로 내보낸다.

## 5. CH05 — 보안

**OWASP Top 10 2021.** A01 접근 통제 실패부터 A10 SSRF까지 다룬다. 방법론은 데이터에서 8개, 커뮤니티 설문에서 2개다. Insecure Design이 이때 신설됐다.

**OWASP LLM Top 10 2025**(2024-11-18 발행, [원문](https://genai.owasp.org/llm-top-10/)):

| 2025 | 항목 | 2023판과의 관계 |
|---|---|---|
| LLM01 | Prompt Injection | 유지 |
| LLM02 | Sensitive Information Disclosure | 순위 상승 |
| LLM03 | Supply Chain | 유지 |
| LLM04 | Data and Model Poisoning | Training Data Poisoning 확장 |
| LLM05 | Improper Output Handling | 이름 변경 |
| LLM06 | Excessive Agency | Insecure Plugin Design 일부 흡수 |
| LLM07 | System Prompt Leakage | **신규** |
| LLM08 | Vector and Embedding Weaknesses | **신규** (RAG) |
| LLM09 | Misinformation | Overreliance 대체 |
| LLM10 | Unbounded Consumption | **DoS 확장** + Model Theft(모델 추출) 포함 |

강의의 사례는 Air Canada 챗봇이다. 챗봇이 유족 할인을 "사후 신청 가능"이라고 잘못 안내했다. BC주 Civil Resolution Tribunal은 2024년 2월 회사가 챗봇 답변에도 책임이 있다고 보고 총 $812.02 지급을 명령했다([결정문](https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do)). LLM09 Misinformation의 교과서 사례다.

강의가 내린 결론은 세 가지다. 침해를 전제하고(Assume Breach), LLM 출력도 신뢰하지 않으며(Zero Trust), 방어를 겹겹이 쌓으라(Defense in depth). 마지막에 단계적 롤아웃과 배포 전 체크리스트로 마무리한다.

## 6. 강의 자료와 1차 출처가 어긋나는 곳

강의 흐름은 좋다. 다만 그대로 옮겨 적으면 틀리는 곳이 있어 따로 모았다.

| # | 강의 서술 | 1차 출처 기준 |
|---|---|---|
| 1 | Dhanji Prasanna를 "Anthropic CTO"로 소개 | **Block** CTO다([Anthropic 발표문](https://www.anthropic.com/news/model-context-protocol)) |
| 2 | 초기화 후 `initialized`, capabilities를 `clientCapabilities`/`serverCapabilities`로 표기 | 메서드는 `notifications/initialized`, 필드는 양쪽 다 `capabilities`([Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)) |
| 3 | ping 응답이 `"pong"` | 빈 객체 `"result": {}`([Ping](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/ping)) |
| 4 | 다이어그램의 `resources/get`, `log/message` | `resources/read`, `notifications/message`([Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources), [Logging](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/logging)) |
| 5 | tool_use/tool_result 블록을 MCP 메시지처럼 설명 | 그건 모델 API(Anthropic Messages API)의 형식이다. MCP 쪽은 `tools/call` 요청과 응답이다 |
| 6 | Streamable HTTP = "POST·GET 이중 채널" | **엔드포인트 하나**다. POST 응답이 JSON 한 건일 수도 있고 SSE 스트림일 수도 있으며, GET은 서버→클라이언트 스트림을 여는 **선택** 기능이다([Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)) |
| 7 | "Claude Code와 Gemini CLI는 HTTP MCP 서버를 표준적으로 지원하지 않음" | 적어도 Claude Code는 틀렸다. `claude mcp add --transport http <name> <url>`이 **권장** 방식이다([Claude Code 문서](https://code.claude.com/docs/en/mcp)) |
| 8 | `with sqlite3.connect(...) as conn:`이면 연결이 자동으로 닫힘 | **닫히지 않는다.** 커밋·롤백만 한다. 닫으려면 `contextlib.closing`이나 `close()`를 써야 한다([Python 문서](https://docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager)) |
| 9 | `ON DELETE CASCADE` 예제를 그대로 제시 | SQLite는 외래키가 **기본 꺼짐**이다. 연결마다 `PRAGMA foreign_keys = ON`이 없으면 CASCADE가 아예 안 돈다([SQLite](https://www.sqlite.org/foreignkeys.html)) |

### 덜 치명적이지만 고칠 것

- **stdio 서버에서 `print()`.** 스펙상 서버는 stdout에 MCP 메시지 말고는 **아무것도 쓰면 안 된다**(MUST NOT). 로그는 stderr로 보낸다(`print(..., file=sys.stderr)` 또는 `logging`). stdout에 디버그 문자열 한 줄만 섞여도 클라이언트의 JSON 파싱이 깨진다.
- **페이징 예제.** 강의의 `read_file_in_pages(all_lines, ...)`는 파일 전체를 메모리에 올린 다음 자른다. 그래서 "메모리 절약"이라는 동기와 맞지 않는다. `itertools.islice(f, offset, offset+limit)`로 스트리밍해야 이름값을 한다.
- **dbmate 예제의 `SERIAL`.** 이건 PostgreSQL 문법이다. SQLite에서는 `INTEGER PRIMARY KEY`를 쓴다.
- **도커 포트 예시.** 명령은 `-p 7777:77`인데 출력 예시는 `0.0.0.0:8080->80/tcp`다. 둘 중 하나로 맞춰야 한다.
- **OWASP LLM 비교표.** 2023 LLM04 DoS를 "포이즈닝에 통합"이라고 적었는데, 실제로는 LLM10 Unbounded Consumption으로 갔다(위 표 참고).
- **GPT-4 비용 계산.** 강의 자신의 가정(8K 토큰 × 10,000회, 입력 $0.03/1K)을 그대로 넣어도 결과가 다르다.

  $$
  8{,}000 \times 10{,}000 = 8\times10^{7}\ \text{tokens}, \qquad \frac{8\times10^{7}}{1{,}000} \times \$0.03 = \$2{,}400
  $$

  강의 본문에 적힌 240,000 토큰은 자릿수가 틀렸다.
- **OWASP Top 10은 2025판이 나와 있다.** 강의는 2021판 기준이다. 2025판에서는 SSRF가 A01로 흡수됐다. 그리고 A03 Software Supply Chain Failures와 A10 Mishandling of Exceptional Conditions가 새로 들어왔다([OWASP Top 10:2025](https://top10.owasp.org/2025/0x00_2025-Introduction/)). MCP 서버는 그 자체가 공급망의 일부이므로, 이 강의 맥락이라면 2025판의 A03을 같이 보는 게 맞다.
- **"충돌 100% 방지"(conda) 같은 단정.** 환경 격리는 충돌을 줄일 뿐이다. 없애 주지는 않는다.

## 7. 정리

강의의 뼈대는 탄탄하다. 개념에서 시작해 stdio 계산기, HTTP 전환, 실제 파일·DB 도구, 보안 순으로 간다. 특히 CH04의 `expected_replacements` 가드와 정렬 필드 화이트리스트는 MCP와 상관없이 가져다 쓸 만한 패턴이다. 반면 프로토콜 메시지 이름, 전송 방식 설명, 클라이언트 지원 현황은 스펙과 도구가 빨리 움직이는 영역이라 강의 시점 이후 낡았거나 처음부터 부정확한 곳이 있다. 실습할 때는 메시지 이름과 설정법을 [modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-11-25)와 각 클라이언트 문서에서 다시 확인하자.

## References

1. Anthropic, "Introducing the Model Context Protocol," 2024-11-25. <https://www.anthropic.com/news/model-context-protocol>
2. Model Context Protocol Specification, revision 2025-11-25 — Lifecycle / Transports / Ping / Resources / Logging. <https://modelcontextprotocol.io/specification/2025-11-25>
3. K. Wiggers, "OpenAI adopts rival Anthropic's standard for connecting AI models to data," TechCrunch, 2025-03-26. <https://techcrunch.com/2025/03/26/openai-adopts-rival-anthropics-standard-for-connecting-ai-models-to-data/>
4. F. Cano Gabarda, "Model Context Protocol (MCP): Understanding security risks and controls," Red Hat Blog, 2025-06-26. <https://www.redhat.com/en/blog/model-context-protocol-mcp-understanding-security-risks-and-controls>
5. J. Lowin, "Introducing FastMCP 2.0," 2025-04-16. <https://jlowin.dev/blog/fastmcp-2> / FastMCP docs <https://gofastmcp.com/docs/v2/getting-started/welcome>
6. Anthropic, Claude Code Docs — "Connect Claude Code to tools via MCP." <https://code.claude.com/docs/en/mcp>
7. Python Software Foundation, `sqlite3` — "How to use the connection context manager." <https://docs.python.org/3/library/sqlite3.html>
8. SQLite, "SQLite Foreign Key Support" / "Datatypes In SQLite." <https://www.sqlite.org/foreignkeys.html>, <https://www.sqlite.org/datatype3.html>
9. OWASP, "OWASP Top 10:2025." <https://top10.owasp.org/2025/0x00_2025-Introduction/> / OWASP Top 10:2021 <https://owasp.org/Top10/2021/>
10. OWASP Gen AI Security Project, "OWASP Top 10 for LLM Applications 2025," 2024-11-18. <https://genai.owasp.org/llm-top-10/>
11. Civil Resolution Tribunal (BC), *Moffatt v. Air Canada*, 2024 BCCRT 149. <https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do>
