---
layout: post
title: "인텔리제이 AI Assistant 잘 쓰는 법 — 규칙 파일·.aiignore·에이전트·MCP·크레딧까지"
date: 2026-09-29 20:14:03 +0900
categories: [ai]
tags: [intellij, jetbrains-ai-assistant, junie, mcp, acp, ai-coding]
---

JetBrains AI Assistant 는 이제 "채팅 창 달린 자동완성 플러그인" 이 아니다. 공식 문서의 정의부터 바뀌었다 — **AI 기능 묶음 + 코딩 에이전트** 다([About AI Assistant](https://www.jetbrains.com/help/ai-assistant/about-ai-assistant.html)). 채팅 창을 열면 기본값이 채팅이 아니라 **에이전트** 이고, 그 에이전트 자리에는 JetBrains 의 Junie 말고도 Claude Agent · Codex · GitHub Copilot 이 들어간다([AI Chat](https://www.jetbrains.com/help/ai-assistant/ai-chat.html), [Activate agents](https://www.jetbrains.com/help/ai-assistant/activate-agents.html)).

그래서 "잘 쓰는 법" 도 단축키 모음이 아니라 네 가지 질문으로 정리된다.

1. **어떤 일을 어느 기능에 맡기나** — 자동완성 / 다음 편집 제안 / 에디터 내 생성 / 채팅 / 에이전트
2. **프로젝트가 AI 에게 무엇을 알려주나** — 규칙 파일, 프롬프트 라이브러리
3. **AI 가 무엇을 보면 안 되나** — `.aiignore`, `.noai`
4. **돈은 어디서 나가나** — AI 크레딧, BYOK, 로컬 모델

근거는 전부 JetBrains 공식 문서(jetbrains.com/help/ai-assistant, 2026-09-29 조회)다. 필자 의견은 **(필자 제안)** 으로 따로 표시했다. 단축키는 문서에 적힌 **Windows/Linux 기본 키맵** 기준이며, macOS 키맵에서는 다르다.

---

## 1. 일감별로 기능을 나눈다

AI Assistant 안에 있는 기능은 개입 강도가 다섯 단계다. 싼 것부터 쓰고, 모자랄 때만 한 단계씩 올린다 **(필자 제안)**.

| 단계 | 기능 | 무엇을 하나 | 어디서 |
| --- | --- | --- | --- |
| 1 | 클라우드 코드 완성 | 한 줄~함수 단위 자동완성. 기본 모델은 JetBrains 자체 모델 **Mellum** | 에디터·채팅 입력창·커밋 메시지 |
| 2 | 다음 편집 제안 (NES) | 방금 고친 것과 같은 패턴의 *다음 수정 위치* 를 예측 | 에디터, Tab 두 번 |
| 3 | 에디터 내 코드 생성 | 자연어로 그 자리에 코드 생성·재생성 | `Ctrl+\` |
| 4 | 채팅 (Chat 모드) | 질문·설명·스니펫. **파일을 자동으로 바꾸지 않음** | AI Chat |
| 5 | 에이전트 | 여러 파일에 걸친 다단계 작업. 결과를 유지하거나 되돌림 | AI Chat 에이전트 선택 |

출처: [Code completion](https://www.jetbrains.com/help/ai-assistant/code-completion.html), [Next edit suggestions](https://www.jetbrains.com/help/ai-assistant/next-edit-suggestions.html), [In-editor code generation](https://www.jetbrains.com/help/ai-assistant/code-generation.html), [AI Chat](https://www.jetbrains.com/help/ai-assistant/ai-chat.html).

### 1-1. 자동완성은 "Focused" 가 기본이다

`Settings | Editor | General | Code Completion | Inline` 의 **Completion policy** 에는 세 값이 있다([Code completion](https://www.jetbrains.com/help/ai-assistant/code-completion.html)).

- **Focused** (기본값) — 틀릴 수 있는 코드를 엄격히 걸러 짧고 정확한 제안만
- **Balanced** — 필터를 느슨하게 해 제안이 늘어남
- **Creative** — 필터를 모두 꺼서 미완성·추측성 코드도 보여줌

문서의 표현 그대로라면 Creative 는 "실험용" 이다. 제안이 너무 적다고 느껴져도 Balanced 까지만 올리는 편이 리뷰 부담이 적다 **(필자 제안)**.

같은 화면에서 챙길 것 두 가지:

- **All others 언어** 를 켜면 흔치 않은 파일 형식에서도 완성이 뜨지만, 문서는 이 경우 "소량의 쿼터가 소모될 수 있다" 고 적는다. 기본값은 꺼짐이다.
- **Local / Cloud and local / Cloud** 중 고를 수 있다. Local 은 기기에서 도는 소형 모델이라 AI Assistant 플러그인이 없어도 동작한다.

### 1-2. 다음 편집 제안(NES)은 "리팩터링 도중" 에 쓴다

NES 는 한 곳을 고치면 파일 안의 같은 패턴을 찾아 다음 수정을 제안한다. 쉼표 뒤 공백 하나를 고치면 나머지도 제안하고, 오타를 고치면 같은 오타를 잡는 식이다. **Tab 으로 그 위치로 점프, Tab 한 번 더로 적용**, Esc 로 취소한다([Next edit suggestions](https://www.jetbrains.com/help/ai-assistant/next-edit-suggestions.html)).

- **Chain suggestions** — 하나를 받으면 다음 제안을 자동으로 요청한다. 연쇄 수정에 좋다.
- **Suggest refactorings** — Rename 같은 IDE 리팩터링 동작에 기반한 제안까지 받는다.
- 제약: 문서 기준 **AI Free 등급에서는 NES 를 쓸 수 없다**.

(필자 제안) 시그니처를 바꾸는 류의 변경이라면 NES 보다 IDE 의 **정적 리팩터링(Rename, Change Signature)** 이 먼저다. 그쪽은 참조를 컴파일러 수준으로 추적하고, NES 는 예측이다.

### 1-3. Chat 과 에이전트는 "변경 권한" 이 다르다

문서가 두 모드를 가르는 기준은 명확하다. **Chat 은 제안만 하고 적용은 사람이 한다. 에이전트는 여러 파일을 직접 고치고, 사람이 유지(keep)하거나 되돌린다(roll back)** ([AI Chat](https://www.jetbrains.com/help/ai-assistant/ai-chat.html)).

주의할 점은 **채팅 창의 기본값이 에이전트** 라는 것이다. 어떤 에이전트가 기본인지는 "JetBrains 벤치마크에 따라 자동 선택되며 바뀔 수 있다" 고 문서에 적혀 있다. 다른 에이전트를 한 번 고르면 새 채팅에서도 그 선택이 유지된다.

(필자 제안) 설명만 듣고 싶은 질문을 에이전트에 던지면 파일이 바뀔 수 있다. "이 코드 뭐 하는 거야" 류는 Chat 모드로 바꿔서 묻는 습관을 들이자.

---

## 2. 채팅에 맥락을 정확히 넣는다

### 2-1. Codebase Mode 와 @멘션

Codebase Mode 가 켜져 있으면 AI Assistant 가 관련 맥락을 알아서 모은다. 이때 **`.gitignore` 와 `.aiignore` 에 있는 파일은 자동 수집에서 빠진다**([Chat with AI](https://www.jetbrains.com/help/ai-assistant/chat-mode.html)).

자동 수집보다 정확한 건 직접 지정이다. 문서에 있는 @멘션 중 실무에서 쓸모가 큰 것:

| 멘션 | 들어가는 것 |
| --- | --- |
| `@selection` | 지금 선택한 코드 |
| `@localChanges` | 커밋 안 한 변경분 |
| `@problems` | 현재 파일에서 IDE 가 잡은 문제 |
| `@projectStructure` | Project 창의 구조 |
| `@rule:` | 특정 프로젝트 규칙을 수동 삽입 |

슬래시 명령도 있다. `/explain`, `/help`, 그리고 웹을 검색해 근거 링크를 붙이는 `/web` 이다. MCP 서버를 붙이면 명령 목록이 늘어난다.

(필자 제안) 가장 효과가 큰 조합은 **`@localChanges` + `@problems`** 다. "지금 내가 바꾼 것" 과 "IDE 가 이미 찾은 문제" 를 같이 주면, 모델이 추측할 부분이 크게 준다.

### 2-2. 수동 첨부는 `.aiignore` 를 뚫는다

문서에 이 경고가 따로 있다. **`.aiignore` 로 막은 파일이라도 사람이 직접 첨부하면 그 제한을 우회해 AI 에게 보내진다**([Chat with AI](https://www.jetbrains.com/help/ai-assistant/chat-mode.html)). 비밀이 든 설정 파일을 "이거 봐줘" 하고 끌어다 넣는 순간 보호가 사라진다는 뜻이다.

---

## 3. 프로젝트 규칙 파일 — 가장 저평가된 기능

매 채팅마다 "우리는 Spring Boot 3, JUnit5, 생성자 주입만 써" 를 반복하고 있다면 규칙 파일로 옮기면 된다([Configure project rules](https://www.jetbrains.com/help/ai-assistant/configure-project-rules.html)).

- 위치: 프로젝트 루트의 **`.aiassistant/rules/*.md`**. `Settings | Tools | AI Assistant | Rules` 에서 만들거나 직접 만든다.
- 규칙마다 적용 방식을 고른다.

| Rule type | 언제 붙나 |
| --- | --- |
| **Always** | 모든 채팅에 자동 |
| **Manually** | `@rule:` / `#rule:` 로 부를 때만 |
| **By model decision** | 모델이 관련 있다고 판단할 때 (판단 기준이 되는 Instruction 필수) |
| **By file patterns** | 채팅에 언급된 파일이 패턴(`*.kt`, `src/**`)에 맞을 때 |
| **Off** | 비활성 |

- 실제로 적용됐는지는 응답 맨 앞의 **첨부 목록을 펼쳐** 확인한다.

(필자 제안) 규칙 파일도 결국 매 요청의 컨텍스트를 먹는다. 전부 Always 로 두지 말고 이렇게 나누자.

- **Always**: 짧고 전역적인 것 — 언어·프레임워크 버전, 금지 패턴 몇 줄
- **By file patterns**: 계층별 규칙 — `src/test/**` 엔 테스트 규칙, `*.sql` 엔 마이그레이션 규칙
- **Manually**: 길고 가끔 쓰는 것 — 릴리스 체크리스트, 장애 대응 절차

규칙 파일은 git 에 커밋되므로 **팀 전체가 같은 지시를 공유** 한다는 게 개인 프롬프트와의 결정적 차이다.

---

## 4. 프롬프트 라이브러리 — 반복 작업을 버튼으로

`Settings | Tools | AI Assistant | Prompt Library` 에서 두 가지를 할 수 있다([Add and customize prompts](https://www.jetbrains.com/help/ai-assistant/prompt-library.html)).

1. **내 프롬프트 추가.** `$SELECTION` 변수로 선택한 코드를 끼워 넣을 수 있다. 저장하면 에디터 우클릭 또는 `Alt+Enter` 의 **AI Actions** 메뉴에 뜬다. 채팅에서 잘 먹힌 프롬프트는 "Save Current Prompt" 로 바로 저장할 수 있다.
2. **내장 프롬프트 수정.** 커밋 메시지 생성, 테스트 생성, 문서 생성 같은 내장 동작에 지시를 **덧붙일** 수 있다(대체가 아니라 기본 프롬프트 뒤에 붙는다). General 섹션의 **Chat Instructions** 는 새 채팅을 열 때마다 자동으로 붙는다.

커밋 메시지 쪽은 특히 쓸모가 크다. 내장 **Commit Message Generation** 프롬프트에 `$GIT_BRANCH_NAME` 을 넣으면 브랜치 이름을 메시지에 반영할 수 있다([AI in version control](https://www.jetbrains.com/help/ai-assistant/ai-in-vcs-integration.html)). 예를 들어 이런 지시다.

```text
- 제목은 50자 이내, 한국어, "type: 요약" 형식 (feat/fix/refactor/docs/test/chore)
- 브랜치 이름 $GIT_BRANCH_NAME 에 이슈 키(ABC-123)가 있으면 제목 끝에 붙인다
- 본문에는 변경 이유를 쓴다. 무엇을 바꿨는지는 diff 가 말해준다
```

---

## 5. 커밋 직전: Self-Review with AI

Commit 창(`Alt+0`)에서 변경을 고르고 **Self-Review with AI** 를 누르면 Problems 창에 **AI Self-Review** 탭이 열린다. 이슈를 더블클릭(또는 F4)하면 해당 위치로 가고, 퀵픽스가 있으면 바로 적용한다. 이미 커밋한 것도 Git 창(`Alt+9`)에서 커밋을 골라 같은 리뷰를 돌릴 수 있다([AI in version control](https://www.jetbrains.com/help/ai-assistant/ai-in-vcs-integration.html)).

리뷰 기준은 `Settings | Tools | AI Assistant | Project Settings` 의 **Path to rules for AI Self-Review** 에 마크다운 파일로 지정한다([Project Settings](https://www.jetbrains.com/help/ai-assistant/settings-reference-project-settings.html)).

(필자 제안) 이 리뷰 규칙 파일은 3장의 규칙 파일과 **내용이 겹치지 않게** 둔다. 규칙 파일은 "이렇게 짜라", 리뷰 규칙은 "이런 걸 잡아라" 다. 예: 트랜잭션 경계 밖의 지연 로딩, `@Transactional` 이 private 메서드에 붙은 경우, 로그에 개인정보 출력.

---

## 6. AI 가 보면 안 되는 것 — `.aiignore` 와 `.noai`

([Restrict or disable AI Assistant features](https://www.jetbrains.com/help/ai-assistant/disable-ai-assistant.html))

- **`.aiignore`** — `.gitignore` 문법으로 AI 가 처리하지 않을 파일·폴더를 적는다. `Project Settings` 에서 **Enable .aiignore** 를 켜야 적용된다. 루트에 이미 `.cursorignore`, `.codeiumignore`, `.aiexclude` 가 있으면 그것도 인식한다.
- **`.noai`** — 프로젝트 루트에 빈 파일로 두면 그 프로젝트에서 **AI Assistant 기능 전체가 꺼진다.** 다른 IDE 에서 열어도 마찬가지다.
- 네트워크 차원에서 막으려면 JetBrains AI 서비스 도메인(`api.jetbrains.ai` 등)을 차단한다.

문서가 스스로 달아 둔 단서 두 개를 꼭 기억하자.

1. `.aiignore` 에 넣은 파일도 "예기치 못한 문제로 처리될 수 있다" — 즉 **보안 경계로 보장하지 않는다.**
2. `.noai` 는 **JetBrains AI Assistant 플러그인에만** 적용된다. 다른 AI 플러그인이나 외부 도구에는 효과가 없다.

(필자 제안) 그러니 진짜 비밀(키·토큰·인증서)은 `.aiignore` 가 아니라 **저장소 밖**에 둬야 한다. `.aiignore` 는 빌드 산출물·로그·거대한 생성 코드처럼 *맥락 낭비* 를 막는 용도로 쓰는 게 정확하다.

---

## 7. 에이전트 고르기 — Junie, Claude Agent, Codex, Copilot, 그리고 ACP

([Activate agents](https://www.jetbrains.com/help/ai-assistant/activate-agents.html))

통합 에이전트는 **Junie, Claude Agent, Codex, GitHub Copilot** 이다. 인증 방식이 여러 개인데, 이게 기능 범위를 바꾼다.

| 인증 방식 | 무엇이 열리나 |
| --- | --- |
| JetBrains AI 구독 | 모든 통합 에이전트 + AI Assistant 전 기능 |
| API 키 (BYOK) — Claude Agent(Anthropic 키), Codex(OpenAI 키) | 해당 에이전트 + 다른 AI Assistant 기능도 활성화 |
| 제공사 계정 (OAuth) — Codex, GitHub Copilot | **채팅 속 그 에이전트만.** 다른 AI Assistant 기능은 안 열림 |

선택한 인증 방식이 **요청 처리와 과금에 모두** 쓰인다. 현재 어떤 방식으로 붙어 있는지는 `Providers & API keys` 의 **Agent Authorization** 에서 확인하고, 바꾸려면 기존 방식을 철회한 뒤 새 채팅을 연다.

통합 목록에 없는 에이전트는 **ACP(Agent Client Protocol)** 로 붙인다. ACP 호환 에이전트를 설치하면 JetBrains AI 구독 없이도 AI Chat 에서 쓸 수 있고, AI Chat 우상단 메뉴의 **Add Custom Agent** 로 `acp.json` 에 직접 등록할 수도 있다. 이때 **Pass custom MCP servers / Pass IntelliJ MCP server** 설정으로 그 에이전트가 MCP 도구를 쓰게 할지 정한다.

(필자 제안) 이미 Claude·OpenAI 구독이나 키가 있다면, IDE 안에서 에이전트를 돌릴 목적이라면 BYOK/OAuth 가 중복 결제를 피하는 길이다. 다만 OAuth 로만 붙이면 자동완성·커밋 메시지 같은 **AI Assistant 쪽 기능은 따로 활성화해야** 한다는 점을 먼저 확인하자.

---

## 8. MCP — 양방향이다

### 8-1. AI Assistant 가 MCP 서버를 쓴다

`Settings | Tools | AI Assistant | Model Context Protocol (MCP)` 에서 서버를 추가한다. 전송 방식은 **STDIO, Streamable HTTP**, 그리고 레거시 **SSE** 다. Claude Desktop 설정이 있으면 **Import from Claude** 로 한 번에 가져온다. 서버마다 **전역/프로젝트** 범위를 고를 수 있다([MCP](https://www.jetbrains.com/help/ai-assistant/mcp.html)).

```json
{
  "mcpServers": {
    "docs": { "url": "https://example.com/mcp" }
  }
}
```

### 8-2. IDE 가 MCP 서버가 된다

2025.2 부터 JetBrains IDE 에는 **내장 MCP 서버** 가 있다. `Settings | Tools | MCP Server` 에서 켜면 Claude Code, Codex, VS Code 같은 외부 클라이언트가 IDE 의 도구(빌드, 실행 구성, DB 스키마 조회, 디버거 등)를 쓸 수 있다. 감지된 클라이언트는 **Auto-Configure** 로 설정 파일을 자동으로 고쳐준다([MCP](https://www.jetbrains.com/help/ai-assistant/mcp.html)).

여기서 조심할 설정 두 개:

- **brave mode** (`Run shell commands ... without confirmation`) — 외부 클라이언트가 터미널 명령·실행 구성을 **확인 없이** 돌린다. 편하지만 확인 단계가 통째로 사라진다. **(필자 제안) 기본은 끈다.**
- **Exposed Tools** 의 도구별 Enabled / **Router-only** — 안 쓰는 도구를 끄거나 라우터 뒤로 숨기면 도구 설명이 컨텍스트를 덜 먹는다. 문서도 이를 "컨텍스트 절약" 용도로 설명한다.

(필자 제안) `build_project` 처럼 **컴파일 오류를 돌려주는 도구** 가 외부 에이전트에게 가장 값지다. 에이전트가 "고쳤다" 고 말하는 것과 실제로 빌드되는 것 사이의 간극을 IDE 가 메워준다.

---

## 9. 모델과 돈 — 크레딧, BYOK, 로컬 모델

### 9-1. AI 크레딧

클라우드 모델을 쓰는 기능은 **AI Credits** 를 소모한다. **1 크레딧 = 미화 1달러** 이며, 공식 표는 다음과 같다([JetBrains AI plans and usage](https://www.jetbrains.com/help/ai-assistant/licensing-and-subscriptions.html)).

| 등급 | 개인 (가격 / 30일 크레딧) | 조직 (가격 / 30일 크레딧) |
| --- | --- | --- |
| AI Free | 무료 / 3 | 무료 / 3 |
| AI Pro | $10 / 10 | $20 / 20 |
| AI Ultimate | $30 / 35 | $60 / 70 |
| AI Enterprise | — | $60 / Ultimate 이상 (정확한 수치 비공개) |

크레딧이 떨어지면 **충전(Top-up)** 할 수 있고, 충전분은 **12개월** 유효하다. JetBrains Central 로 이전된 조직은 개인 할당이 아니라 **조직 공동 풀** 에서 쓰고, 관리자가 사용자별 한도를 건다.

이 표는 가격 정책이 바뀌면 달라진다. 글을 읽는 시점의 공식 페이지를 다시 확인하자.

### 9-2. 서드파티·로컬 모델

([Use third-party and local models](https://www.jetbrains.com/help/ai-assistant/use-custom-models.html))

`Settings | Tools | AI Assistant | Providers & API keys` 에서 **Anthropic, Google(Gemini API·Vertex AI), OpenAI, OpenAI 호환 엔드포인트(llama.cpp, LiteLLM 등), Ollama, LM Studio** 를 붙일 수 있다.

- 서드파티 제공사 모델은 기능에 **자동 배정** 된다. 그 모델이 지원하지 않는 기능은 비활성화된다.
- 로컬·OpenAI 호환 모델은 **수동 배정** 한다. **Core features**(에디터 생성·커밋 메시지·채팅 기본)와 **Instant helpers**(채팅 맥락 수집·제목 생성·이름 제안) 두 칸이다.
- 로컬 모델의 기본 컨텍스트 창은 **64,000 토큰** 이며 조정 가능하다.
- **로컬 모델에서는 MCP 도구 호출이 지원되지 않는다.**
- 자동완성과 NES 는 기본적으로 JetBrains 모델이고, 바꾸려면 AI Completion 섹션에 OpenAI 호환 제공사를 따로 지정한다.

(필자 제안) 배정 원칙은 단순하다. **Instant helpers 에는 싸고 빠른 모델**, Core 에는 믿을 만한 모델. 제목 생성 같은 곳에 큰 모델을 쓰면 비용만 늘어난다.

**우리 집 사례.** 필자의 홈랩에는 여러 모델 제공사를 하나의 OpenAI 호환 엔드포인트로 묶는 **LiteLLM 게이트웨이** 가 있다. 문서가 OpenAI 호환 예시로 LiteLLM 을 직접 드는 만큼, IDE 에서는 이 엔드포인트 하나만 등록하면 제공사별 키를 IDE 마다 흩어 넣지 않아도 되고, 사용량도 게이트웨이 한 곳에 모인다. 단 이 방식은 위 규칙대로 **수동 배정** 이 되므로, Core / Instant helpers 칸을 직접 채워야 한다.

---

## 10. 체크리스트

프로젝트에 AI Assistant 를 들일 때 이 순서로 점검한다 **(필자 제안)**.

1. **`.aiignore` 먼저** — 빌드 산출물·로그·생성 코드 제외. 비밀은 애초에 저장소 밖.
2. **`.aiassistant/rules/` 커밋** — Always 는 짧게, 나머지는 파일 패턴·수동으로.
3. **자동완성 정책 확인** — Focused 에서 시작. All others 는 필요할 때만.
4. **Chat vs 에이전트 구분** — 질문은 Chat, 다파일 수정은 에이전트. 기본값이 에이전트임을 기억.
5. **커밋 메시지 프롬프트 + Self-Review 규칙 파일** — 팀 컨벤션을 도구에 박는다.
6. **IDE MCP 서버는 brave mode 끄고, 쓰는 도구만 노출.**
7. **과금 경로 확인** — Agent Authorization 에서 어떤 인증(구독/BYOK/OAuth)으로 돌고 있는지 본다.

---

## 한계

- 이 글은 **JetBrains 공식 문서만** 근거로 썼다. 기능 존재·설정 위치는 문서 기준이며, 필자가 모든 설정을 IntelliJ 최신 버전에서 하나하나 재현한 것은 아니다.
- AI Assistant 와 다른 도구(Copilot, Cursor 등)의 **성능 우열에 대한 중립적 헤드투헤드 비교는 찾지 못했다.** 그래서 이 글은 비교하지 않는다.
- 문서의 "기능별 사용 모델" 표에는 이미 구세대인 모델명이 남아 있다. 실제 배정 모델은 버전·지역·등급에 따라 다를 수 있다.
- 에이전트 기본값, 가격, 크레딧 수치는 JetBrains 가 수시로 바꾼다. 조회일(2026-09-29) 이후의 변경은 반영하지 못한다.

---

## References

1. JetBrains, *About AI Assistant* — <https://www.jetbrains.com/help/ai-assistant/about-ai-assistant.html>
2. JetBrains, *AI Chat* — <https://www.jetbrains.com/help/ai-assistant/ai-chat.html>
3. JetBrains, *Chat with AI* — <https://www.jetbrains.com/help/ai-assistant/chat-mode.html>
4. JetBrains, *Code completion* — <https://www.jetbrains.com/help/ai-assistant/code-completion.html>
5. JetBrains, *Next edit suggestions* — <https://www.jetbrains.com/help/ai-assistant/next-edit-suggestions.html>
6. JetBrains, *In-editor code generation* — <https://www.jetbrains.com/help/ai-assistant/code-generation.html>
7. JetBrains, *Configure project rules* — <https://www.jetbrains.com/help/ai-assistant/configure-project-rules.html>
8. JetBrains, *Add and customize prompts* — <https://www.jetbrains.com/help/ai-assistant/prompt-library.html>
9. JetBrains, *AI in version control* — <https://www.jetbrains.com/help/ai-assistant/ai-in-vcs-integration.html>
10. JetBrains, *Project Settings* — <https://www.jetbrains.com/help/ai-assistant/settings-reference-project-settings.html>
11. JetBrains, *Restrict or disable AI Assistant features* — <https://www.jetbrains.com/help/ai-assistant/disable-ai-assistant.html>
12. JetBrains, *Activate agents* — <https://www.jetbrains.com/help/ai-assistant/activate-agents.html>
13. JetBrains, *Model Context Protocol (MCP)* — <https://www.jetbrains.com/help/ai-assistant/mcp.html>
14. JetBrains, *JetBrains AI plans and usage* — <https://www.jetbrains.com/help/ai-assistant/licensing-and-subscriptions.html>
15. JetBrains, *Use third-party and local models* — <https://www.jetbrains.com/help/ai-assistant/use-custom-models.html>
