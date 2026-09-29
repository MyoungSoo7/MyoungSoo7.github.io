---
layout: post
title: "DataGrip AI 잘 쓰는 법 — 권한 4단계, 읽기 전용 계정, 요청 로그로 확인하기 (2026.2 기준)"
date: 2026-09-29 20:12:06 +0900
categories: [database, ai, tools]
tags: [datagrip, jetbrains, ai-assistant, text-to-sql, mcp, claude-code, sql]
---

DataGrip 의 AI 는 2026년 들어 성격이 바뀌었다. 예전에는 "SQL 을 설명하고 고쳐 주는 버튼"이었다. 2026.1 에서 AI 채팅 안에 Claude Agent 와 Codex 가 들어왔고([What's New 2026.1](https://www.jetbrains.com/datagrip/whatsnew/2026-1/)), 2026.2 에서는 데이터베이스 전용 에이전트 스킬 세 개와 연결 관리 MCP 도구가 추가됐다([DataGrip 2026.2 블로그, 2026-07-16](https://blog.jetbrains.com/datagrip/2026/07/16/datagrip-2026-2-ai-agent-skills-mcp-tools-and-cli-commands-for-data-source-management-bundled-jdbc-drivers-and-improved-session-control/)). **에이전트가 실제 커넥션에 쿼리를 날리는 도구**가 된 것이다.

그러니 "잘 쓰는 법"의 중심도 옮겨 간다. 프롬프트를 잘 쓰는 것보다 **무엇을 허락하고, 무엇이 밖으로 나가는지 확인하는 것**이 먼저다. 이 글은 JetBrains 공식 문서와 릴리스 노트만으로 그 규칙을 정리한다.

## 0. 세 층으로 나눠 보기

DataGrip 의 AI 기능은 위험도가 다른 세 층이다.

| 층 | 무엇 | DB 에 닿는가 | 대표 기능 |
|---|---|---|---|
| ① 인라인 AI 액션 | 에디터에서 설명·수정·최적화 | 아니오(코드와 스키마 문맥만) | Explain / Fix SQL problem, Fix with AI, Optimize Query with AI |
| ② AI 채팅 | 대화 + 문맥 첨부 | 첨부한 스키마와 객체 **구조**만 | `@dbObject:`, Attach Schema |
| ③ 에이전트 + MCP | 스킬과 도구로 직접 실행 | **예. 권한을 주면 조회와 수정까지** | `database-tools`, `database-text-to-sql`, `execute_sql_query` |

출처: [Find and fix problems with AI](https://www.jetbrains.com/help/ai-assistant/find-and-fix-problems-with-ai.html), [Chat with AI](https://www.jetbrains.com/help/ai-assistant/chat-mode.html), [Use AI with databases](https://www.jetbrains.com/help/ai-assistant/use-ai-with-databases.html).

**(해석)** 층이 올라갈수록 편해지지만, 사고가 났을 때 되돌리기도 어려워진다. 아래 규칙은 대부분 ③층용이다.

## 1. 권한 설정 네 개 — "전역"이고 "확인 없이"라는 뜻을 읽어라

DataGrip 설정의 **AI Tools** 페이지에는 토글이 네 개 있다([AI Tools 설정](https://www.jetbrains.com/help/datagrip/settings-database-ai-tools.html)).

| 설정 | 허용하는 것 |
|---|---|
| Read database data | `SELECT` 같은 조회를 실행하고 **결과를 AI 에이전트로 보낸다** |
| Modify database data | `INSERT`·`UPDATE`·`DELETE`, 루틴 호출로 데이터 변경 |
| Read database schemas | 스키마 구조 읽기. 쿼리 생성 품질이 오르지만 **쿼터 소모도 늘어난다** |
| Modify database schemas | `CREATE`·`ALTER`·`DROP` |

이 페이지의 첫 문장이 핵심이다. 이 설정들을 켜면 AI 에이전트와 LLM 이 **"모든 데이터베이스에서 확인 없이"** 읽거나 바꿀 수 있다. 커넥션별 설정이 아니다. 개발용 로컬 DB 에서 편하려고 Modify 를 켜면, 같은 IDE 에 등록된 운영 커넥션에도 똑같이 적용된다.

기본값은 확인을 받는 쪽이다. 2026.1 릴리스 블로그는 데이터와 스키마 접근에 "네 단계의 사용자 동의가 기본으로 요구된다"고 썼고([DataGrip 2026.1 블로그](https://blog.jetbrains.com/datagrip/2026/03/26/datagrip-2026-1-redesigned-query-files-data-source-templates-in-your-jetbrains-account-ai-agents-in-the-ai-chat-explain-plan-flow-enhancements-and-more/)), 2026.2 에서는 CLI 에이전트도 DB 작업 전에 무엇을 할지 보여 주고 동의를 받게 됐다([2026.2 블로그](https://blog.jetbrains.com/datagrip/2026/07/16/datagrip-2026-2-ai-agent-skills-mcp-tools-and-cli-commands-for-data-source-management-bundled-jdbc-drivers-and-improved-session-control/)).

**규칙 1. 두 Modify 토글은 켜지 않는다.** 확인 팝업이 번거롭다는 건 그 팝업이 일을 하고 있다는 뜻이다.

## 2. 진짜 안전장치는 IDE 가 아니라 DB 계정이다

MCP 서버 문서에는 이런 문장이 있다.

> "To guarantee strictly read-only access for an AI agent, use a database user with properly restricted (read-only) privileges and configure the data source to use that user." — [MCP Server | DataGrip](https://www.jetbrains.com/help/datagrip/mcp-server.html)

벤더가 스스로 말한다. **읽기 전용을 "보장"하는 수단은 IDE 토글이 아니라 DB 권한이다.** 토글은 UX 층의 확인 장치이고, DB 가 `permission denied` 를 돌려주는 것만이 경계다.

**규칙 2. 에이전트용 데이터 소스를 따로 만든다.** 읽기 전용 권한만 있는 DB 사용자로 접속하고, 가능하면 운영 원본이 아닌 레플리카나 스테이징을 가리키게 한다. 이름도 `prod-ro-agent` 처럼 붙여 사람이 헷갈리지 않게 한다.

## 3. 무엇이 밖으로 나가는지 — 문서 두 개를 같이 읽어야 한다

AI Assistant 의 데이터 처리 문서에는 이런 문장이 있다. "DataGrip 에서 AI Assistant 는 데이터베이스의 데이터를 공유하지 않고 접근하지도 않는다"([Data handling](https://www.jetbrains.com/help/ai-assistant/how-we-handle-your-code-and-data.html)). 그런데 1절의 AI Tools 문서는 Read database data 를 켜면 조회 결과를 AI 에이전트로 보낸다고 쓴다. MCP 의 `execute_sql_query` 도 결과를 CSV 로 도구 응답에 붙인다([MCP Server](https://www.jetbrains.com/help/datagrip/mcp-server.html)).

**(해석)** 두 문장은 모순이 아니라 층이 다르다. 앞 문장은 ①·②층의 기본 동작이고, ③층에서 데이터 읽기를 허락하면 **쿼리 결과 행이 모델 제공자에게 간다.** 그러니 "DataGrip AI 는 데이터를 안 보낸다"를 전제로 운영 개인정보 테이블에 에이전트를 붙이면 안 된다. 참고로 2026.2 의 `database-tools` 스킬은 토큰을 아끼려고 결과를 처음엔 작은 샘플만 문맥에 넣고, 필요할 때 더 가져온다([릴리스 노트](https://www.jetbrains.com/help/datagrip/release-notes-datagrip.html)). 적게 보낼 뿐, 안 보내는 게 아니다.

확인하는 방법은 공식적으로 있다.

- **요청 로그:** `Shift` 두 번 → `Open AI Assistant Requests Log in Editor`. 모델 제공자로 간 프롬프트가 `ai-assistant-requests.md` 에 남는다. DataGrip 에서는 Markdown 플러그인이 필요하다([Data handling](https://www.jetbrains.com/help/ai-assistant/how-we-handle-your-code-and-data.html)).
- **상세 데이터 수집:** `Settings | Appearance & Behavior | System Settings | Data Sharing | Send detailed code-related data`. 켜면 JetBrains 가 대화 전문을 제품 개선과 모델 학습에 쓸 수 있다. **기본값은 꺼짐**이다(같은 문서).
- **쿼리 이력:** 2026.2 부터 에이전트가 실행한 쿼리가 데이터 소스의 쿼리 이력에 남는다([2026.2 블로그](https://blog.jetbrains.com/datagrip/2026/07/16/datagrip-2026-2-ai-agent-skills-mcp-tools-and-cli-commands-for-data-source-management-bundled-jdbc-drivers-and-improved-session-control/)). 에이전트가 무슨 SQL 을 돌렸는지 사후 감사하는 곳이다.

**규칙 3. 처음 며칠은 요청 로그를 직접 열어 본다.** "스키마만 보낸다고 생각했는데 샘플 행이 같이 갔다" 같은 차이는 로그에서만 보인다.

민감한 스키마라면 모델을 바꾸는 방법도 있다. AI Assistant 는 Ollama, LM Studio 같은 로컬 모델과 llama.cpp, LiteLLM 같은 OpenAI 호환 엔드포인트를 연결할 수 있다([Use custom models](https://www.jetbrains.com/help/ai-assistant/use-custom-models.html)). 이 경우 프롬프트가 기계 밖으로 나가지 않는다. 다만 로컬 모델의 SQL 품질이 클라우드 모델만 한지에 대한 중립 비교는 찾지 못했다.

## 4. 품질 — 스키마를 "필요한 만큼만" 붙여라

AI 가 틀린 SQL 을 쓰는 가장 흔한 이유는 테이블과 컬럼 이름을 추측하기 때문이다. 공식 문서의 인라인 기능 설명마다 "이 기능은 정확한 제안을 위해 데이터베이스 스키마 첨부가 필요할 수 있다"는 주석이 붙어 있다([Find and fix problems](https://www.jetbrains.com/help/ai-assistant/find-and-fix-problems-with-ai.html)). 2026.2 의 `database-text-to-sql` 스킬은 이 문제를 직접 겨냥한다. 스키마와 테이블 구조를 스스로 탐색해 **추측 대신 실제 메타데이터로** 쿼리를 만들고, 설정이 허락하면 한 번 실행해 동작을 확인한다([Use AI with databases](https://www.jetbrains.com/help/ai-assistant/use-ai-with-databases.html)).

채팅에서 문맥을 주는 방법은 두 가지다([Chat with AI](https://www.jetbrains.com/help/ai-assistant/chat-mode.html)).

- `@dbObject:` 로 테이블이나 스키마 **하나**를 지정한다.
- `Attach Schema` 로 **스키마 전체**를 붙인다.

**규칙 4. 전체 스키마보다 `@dbObject:` 를 먼저 쓴다.** **(해석)** 문서가 말하듯 스키마 읽기는 품질을 올리지만 쿼터를 더 쓴다. 테이블 수백 개짜리 스키마를 통째로 붙이면 비용이 들고, 관련 없는 테이블이 모델을 헷갈리게 하고, 밖으로 나가는 구조 정보도 늘어난다. 질문에 필요한 테이블 서너 개만 붙이는 게 세 면에서 다 낫다.

## 5. 성능 튜닝 — AI 에게 "해석"을 맡기고 "측정"은 내가 한다

2026.1 부터 실행 계획 해석을 AI 에 맡길 수 있다. 쿼리를 우클릭해 `Explain Plan | Explain Analyse` 를 실행하고, Query Plan 탭의 `Analyze SQL Plan with AI` 를 누른다. `AI Actions | Optimize Query with AI` 는 불필요한 JOIN, 빠진 인덱스, 비효율 계획을 찾아 재작성까지 제안한다([Use AI with databases](https://www.jetbrains.com/help/ai-assistant/use-ai-with-databases.html)).

**규칙 5. AI 가 고친 쿼리는 같은 조건으로 `EXPLAIN ANALYZE` 를 다시 돌려 숫자로 비교한다.** 실행 계획은 데이터 분포와 통계에 따라 달라진다. **(해석)** AI 는 계획을 읽어 줄 수는 있어도 운영 데이터 분포를 모른다. 인덱스 추가 제안은 쓰기 비용과 잠금까지 따져야 하므로, 제안을 그대로 운영 DDL 로 옮기지 않는다. 그 DDL 은 사람이 마이그레이션 파일로 옮겨 리뷰를 받는다.

## 6. 바깥 에이전트(Claude Code, Codex)에 DataGrip 을 빌려주기

DataGrip 은 2025.2 부터 MCP 서버를 내장한다. 활성화하면 Claude Code, Codex, VS Code, GitHub Copilot CLI 같은 외부 클라이언트가 IDE 의 도구를 쓸 수 있다. `Settings | Tools | MCP Server` 에서 `Enable MCP Server` 를 누르고 클라이언트별 `Auto-Configure` 를 누르면 된다([MCP Server](https://www.jetbrains.com/help/datagrip/mcp-server.html)). 이러면 터미널의 에이전트가 **DataGrip 에 이미 등록된 커넥션과 드라이버를 그대로** 쓸 수 있다. 에이전트에게 접속 비밀번호를 따로 넘기지 않아도 된다는 게 실무상 큰 장점이다.

그만큼 같은 문서의 두 설정을 알고 있어야 한다.

- **brave mode**("Run shell commands or run configurations without confirmation"): 외부 클라이언트가 확인 없이 터미널 명령과 실행 구성을 돌린다. **규칙 6. 켜지 않는다.**
- **Exposed Tools 와 Router-only:** 도구별로 노출 여부를 끌 수 있다. Router-only 로 두면 도구 설명이 직접 목록에서 빠져 에이전트의 문맥을 아낀다. **(해석)** 에이전트가 쓸 일 없는 `create_database_connection`·`edit_database_connection` 은 꺼 두는 게 공격면이 작다.

버전 차이 하나를 주의한다. 2026.2 릴리스 노트는 "데이터베이스 전용 MCP 도구에 더 이상 AI Assistant 플러그인이 필요 없다"고 쓰는데([릴리스 노트](https://www.jetbrains.com/help/datagrip/release-notes-datagrip.html)), MCP 서버 문서의 데이터베이스 도구 절에는 아직 플러그인이 필요하다는 안내가 남아 있다(2026-09-29 확인). 자기 버전에서 도구 목록이 실제로 뜨는지 직접 보는 게 가장 정확하다.

## 7. 안티패턴 요약

| 안티패턴 | 왜 나쁜가 | 대신 |
|---|---|---|
| 편하려고 Modify 토글 켜기 | 전역이고 확인 없이 모든 커넥션에 적용 | 끄고, 변경은 사람이 실행 |
| 운영 관리자 계정 커넥션에 에이전트 붙이기 | IDE 토글은 보장이 아니다 | 읽기 전용 DB 사용자와 전용 데이터 소스 |
| "데이터는 안 나간다"고 믿기 | ③층에서 조회 결과는 모델로 간다 | 요청 로그로 실측, 민감하면 로컬 모델 |
| 스키마 통째로 첨부 | 쿼터, 혼란, 노출 모두 늘어남 | `@dbObject:` 로 필요한 것만 |
| AI 최적화 결과를 측정 없이 채택 | 계획은 데이터 분포에 따라 달라진다 | `EXPLAIN ANALYZE` 전후 비교 |
| MCP brave mode | 외부 에이전트가 확인 없이 명령 실행 | 끄고, 필요 없는 도구는 노출 해제 |

## 8. 아직 확인 안 된 것

- **정확도 수치가 없다.** DataGrip 의 text-to-SQL 이 몇 퍼센트 정확한지에 대해 JetBrains 도 중립 제3자도 공개한 벤치마크를 찾지 못했다. 모델마다 다를 테고, 이 글은 성능을 비교하지 않는다.
- **샘플 크기.** `database-tools` 가 처음 문맥에 넣는 "작은 샘플"이 몇 행인지 문서에 숫자가 없다. 요청 로그로 직접 확인하는 수밖에 없다.
- **문서 간 불일치.** 3절(데이터 공유 문장)과 6절(플러그인 필요 여부)처럼 문서끼리 서술이 어긋나는 곳이 있다. 빠르게 바뀌는 기능이라 문서가 따라오지 못한 것으로 보인다. 결정은 자기 버전의 실제 동작으로 한다.

## References

1. JetBrains, [What's New in DataGrip 2026.1](https://www.jetbrains.com/datagrip/whatsnew/2026-1/). Claude Agent·Codex 채팅 통합, DB 전용 MCP 기능.
2. JetBrains Blog, [DataGrip 2026.1 릴리스](https://blog.jetbrains.com/datagrip/2026/03/26/datagrip-2026-1-redesigned-query-files-data-source-templates-in-your-jetbrains-account-ai-agents-in-the-ai-chat-explain-plan-flow-enhancements-and-more/), 2026-03-26. 데이터·스키마 접근 4단계 동의.
3. JetBrains Blog, [DataGrip 2026.2 릴리스](https://blog.jetbrains.com/datagrip/2026/07/16/datagrip-2026-2-ai-agent-skills-mcp-tools-and-cli-commands-for-data-source-management-bundled-jdbc-drivers-and-improved-session-control/), 2026-07-16. 에이전트 스킬 3종, CLI 동의, AI 쿼리 이력.
4. JetBrains Blog, [AI Agents in DataGrip](https://blog.jetbrains.com/datagrip/2026/08/26/ai-agents-in-datagrip/), 2026-08-26.
5. DataGrip Docs, [Release notes](https://www.jetbrains.com/help/datagrip/release-notes-datagrip.html).
6. DataGrip Docs, [AI Tools 설정](https://www.jetbrains.com/help/datagrip/settings-database-ai-tools.html). 권한 4종.
7. DataGrip Docs, [MCP Server](https://www.jetbrains.com/help/datagrip/mcp-server.html). 외부 클라이언트, brave mode, 읽기 전용 사용자 권고, DB 도구 목록.
8. AI Assistant Docs, [Use AI with databases](https://www.jetbrains.com/help/ai-assistant/use-ai-with-databases.html). text-to-SQL, 실행 계획 해석, 쿼리 최적화.
9. AI Assistant Docs, [Chat with AI](https://www.jetbrains.com/help/ai-assistant/chat-mode.html). `@dbObject:`, 스키마 첨부 동의.
10. AI Assistant Docs, [Find and fix problems with AI](https://www.jetbrains.com/help/ai-assistant/find-and-fix-problems-with-ai.html).
11. AI Assistant Docs, [Data handling](https://www.jetbrains.com/help/ai-assistant/how-we-handle-your-code-and-data.html). 요청 로그, 상세 데이터 수집 기본 꺼짐.
12. AI Assistant Docs, [Use custom models](https://www.jetbrains.com/help/ai-assistant/use-custom-models.html). Ollama, LM Studio, OpenAI 호환 엔드포인트.
