---
layout: post
title: "코덱스로 브라우저에 글 쓰기 — 네 갈래 길과, 각각이 막히는 지점"
date: 2026-09-11 04:50:00 +0900
categories: [tech]
tags: [codex, browser-automation, playwright, mcp, agent]
---

"코덱스한테 시켜서 브라우저로 글 하나 올려줘."

말은 한 줄인데, 실제로 시켜 보면 거의 항상 같은 자리에서 멈춘다. 에이전트가 브라우저를 열긴
여는데 **로그인이 안 되어 있다.** 글을 올리려면 계정이 필요하고, 계정은 브라우저 프로필에 들어
있고, 에이전트가 여는 브라우저는 그 프로필이 아니기 때문이다.

이 글은 그 지점을 중심으로 정리한 것이다. 코덱스가 브라우저에 글을 쓰는 길은 네 갈래이고,
**갈림길에서 물어야 하는 질문은 딱 하나 — "그 사이트에 로그인이 필요한가"** 다. 나머지 결정은
전부 여기서 파생된다.

---

## 1. 네 갈래 길

| 길 | 로그인 상태 | 쓸 수 있는 표면 | 성격 |
| :--- | :--- | :--- | :--- |
| `@Browser` (in-app 브라우저) | **없음** (별도 프로필) | ChatGPT 데스크톱 앱 / 웹. **CLI·IDE 확장에는 없음** | localhost·공개 페이지 미리보기 |
| `@Chrome` (코덱스 크롬 확장) | **있음** (내 크롬 프로필) | 데스크톱 앱 | 로그인이 필요한 실제 사이트 |
| MCP 브라우저 서버 | 서버 설정에 달림 | **CLI 포함 어디든** | 직접 구성하는 자동화 |
| 사람이 직접 | 당연히 있음 | — | 발행 버튼 |

첫 줄이 가장 자주 사람을 속인다. 공식 문서는 in-app 브라우저에 대해 이렇게 못 박는다 —
"내 일반 브라우저와 **분리된 프로필**을 쓰며, 기존 탭이나 세션을 자동으로 공유하지 않는다."
그리고 별도 안내 문서에는 한 줄이 더 있다: **"Browser는 Codex CLI나 Codex IDE 확장에서는
쓸 수 없다."** CLI로 코덱스를 쓰는 사람이 가장 늦게 알게 되는 사실이다.

두 번째 줄이 "글쓰기"의 정답에 가장 가깝다. 크롬 확장은 애초에 **"로그인된 브라우저 상태가
필요한 작업"** 을 위해 있는 물건이고, 공식 문서가 드는 예가 LinkedIn·Salesforce·Gmail·사내
도구다. 게시글 작성은 정확히 이 부류다.

---

## 2. 그런데 CLI 는 "된다"고 말한다

여기가 이 글에서 가장 실용적인 부분이다.

내 맥에 깔린 코덱스에서 기능 플래그를 그대로 찍어 보면 이렇게 나온다.

```console
$ codex features list | grep -i browser
browser_use            stable   true
browser_use_external   stable   true
in_app_browser         stable   true
```

<small>측정: codex-cli 0.133.0-alpha.1, macOS(Darwin 25.6.0), 2026-09-11.</small>

세 개 다 `true` 다. 그런데 이 값이 참이라는 것과, **그 세션에 실제로 붙일 브라우저 백엔드가
있다는 것은 다른 얘기다.** 백엔드가 없는 CLI 세션에서 브라우저를 시키면 에이전트는 부트스트랩
경로를 한참 시도하다가 빈 목록을 만난다. `openai/codex` 저장소에 올라온 사용자 보고들이 그
증상을 그대로 적고 있다 — `agent.browsers.list()` 가 `[]`, `agent.browsers.get("iab")` 는
`Browser is not available: iab`. 크롬 확장 쪽도 같은 모양의 보고가 따로 있다(확장은 Connected
인데 CLI 에서는 `extension` 백엔드가 안 잡힘).

**그래서 실무 규칙은 이렇게 된다.** 플래그를 신뢰하지 말고, 브라우저 작업을 시키기 전에
"지금 이 세션에서 쓸 수 있는 브라우저를 먼저 확인해 달라"고 한 번 시켜라. 목록이 비어 있으면
그 세션에서는 어떤 프롬프트를 써도 안 된다. 설정을 고칠 문제가 아니라 표면을 바꿀 문제다.

> 참고: 위 이슈들은 **사용자 보고**이지 벤더가 확인한 결함 공지가 아니다. 나도 백엔드가 빈
> 상태를 직접 재현하지는 않았다. 내가 실측한 것은 위의 플래그 출력까지다.

---

## 3. CLI 에서 되는 길 — MCP 브라우저 서버

CLI 로 일하는 사람에게 남는 길은 MCP 다. 두 개가 사실상 표준이고, 둘 다 코덱스용 설치
명령을 자기 문서에 직접 싣고 있다.

```bash
# Microsoft — Playwright MCP
codex mcp add playwright npx "@playwright/mcp@latest"

# Google Chrome DevTools 팀 — Chrome DevTools MCP
codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
```

두 명령의 `--` 유무가 다른 게 눈에 걸려서 실제로 둘 다 돌려 봤다. 내 환경(0.133.0-alpha.1)에서는
**두 형태 모두 통과**했고, 만들어진 설정도 같았다. (남의 설정을 건드리지 않으려고 임시
`CODEX_HOME` 에 넣어 확인했다.)

```toml
[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest"]
```

`codex mcp add --help` 의 사용법은 `codex mcp add [OPTIONS] <NAME> (--url <URL> | -- <COMMAND>...)`
이므로, **문서대로 쓸 거면 `--` 를 넣는 쪽이 안전하다.** 구분자 없이 되는 건 이 버전의 관용이지
계약이 아니다.

한 가지 더. MCP 로 붙인 브라우저는 **`@Chrome` 과 같은 프로필·같은 권한 모델을 물려받지
않는다.** 즉 여기서도 로그인 문제는 그대로 남는다. Chrome DevTools MCP 는 실행 중인 크롬에
붙이는 방법을 따로 문서화해 두었으니, 로그인 세션이 필요하면 그 경로를 봐야 한다.

---

## 4. 글을 실제로 쓰는 순서

브라우저가 붙었다고 치자. 여기서부터는 **에디터를 다루는 문제**다. 순서를 이렇게 잡으면 헛돈이
확 준다.

1. **페이지 상태를 한 번에 본다.** DOM 스냅샷 하나, 또는 스크린샷 하나. 둘 다 찍지 않는다.
2. **로케이터는 스냅샷에 실제로 보이는 것으로만 만든다.** `data-testid` → 안정적인 `data-*`
   → `href` → 역할+접근가능이름 → 텍스트 순으로 내려간다. 추측한 셀렉터를 탐침으로 쓰지 않는다.
3. **누르기 전에 개수를 센다.** 하나로 좁혀지지 않으면 컨테이너부터 좁힌다. `.first()` 로
   때우면 그 순간부터 어느 요소를 만졌는지 아무도 모른다.
4. **제목과 본문을 넣는다.** 여기서 함정이 하나 있다(바로 아래).
5. **발행 직전에 멈춘다.** 이건 선택이 아니다(그 아래).
6. **게시된 페이지를 다시 읽어서 확인한다.** 클릭이 성공한 것과 글이 떠 있는 것은 다른 사실이다.

### 함정 ①: `fill()` 은 타이핑이 아니다

Playwright 공식 문서는 `locator.fill()` 이 `<input>` · `<textarea>` · `[contenteditable]` 에서
동작하고, 대상이 그 셋이 아니면 **에러를 던진다**고 적는다. 즉 contenteditable 자체는 지원된다.

문제는 그 다음 줄이다. 공식 문서는 "세밀한 키보드 이벤트를 보내려면 `pressSequentially()` 를
쓰라"고 안내한다. `fill()` 은 값을 넣고 `input` 이벤트를 한 번 쏠 뿐, **키 하나하나를 흉내내지
않는다.** 그런데 Ghost·Notion·Gutenberg 류의 리치 에디터는 `keydown`/`beforeinput`/붙여넣기
핸들러 위에 자기 문서 모델을 얹어 두는 경우가 많다. 그래서 화면에는 글자가 들어간 것처럼
보이는데 저장하면 비어 있거나 포맷이 날아가는 일이 생긴다.

**대응은 단순하다 — 한 번에 다 믿지 말고 한 단락을 넣어 본 뒤 에디터가 그걸 자기 상태로
받아들였는지부터 확인한다.** 받아들이면 나머지를 같은 방식으로 넣고, 아니면 `pressSequentially`
쪽으로 내려간다. 어느 에디터가 어느 쪽인지는 문서로 정해져 있지 않고 **재 봐야 안다.**

### 함정 ②: 대표 이미지는 못 올린다 (in-app 브라우저 한정)

공식 문서에 한 줄로 있다. **"ChatGPT는 내장 브라우저에서 파일 업로드를 자동화할 수 없다."**
썸네일·대표 이미지가 필요한 글이면 그 단계는 처음부터 사람 몫으로 떼어 놓아야 한다.
계획 단계에서 빼놓지 않으면 다 써 놓고 마지막에 막힌다.

### 함정 ③: 발행 버튼 앞에서 멈추는 건 버그가 아니다

에이전트가 "발행할까요?" 하고 서는 걸 답답해할 일이 아니다. 브라우저 자동화에서 **읽기와
전송은 다른 범주**이고, 폼 제출·메시지 전송·댓글 게시·업로드는 전부 전송 쪽이다. 공식 문서도
민감한 동작(정보 제출, 결제, 권한 변경, 삭제) 앞에서는 확인을 받는다고 명시한다. 크롬 확장
쪽은 한 발 더 나가서, 기본값이 **새 사이트를 쓸 때마다 호스트 단위로 묻는 것**이다.

이 게이트를 없애는 스위치(`always allow browser content`)가 설정에 있긴 한데, 공식 문서가
그 항목에 **Elevated Risk** 라고 직접 달아 두었다. 켜기 전에 다음 항목을 읽어야 한다.

---

## 5. 새로 생기는 비용

되게 만드는 이야기만 하면 절반이다. 이 길을 열면 같이 딸려 오는 것들이 있다.

**첫째, 확장 권한의 범위.** 코덱스 크롬 확장 설치 시 크롬이 요구하는 권한 목록에는
*모든 웹사이트의 데이터 읽기·변경*, *페이지 디버거 접근*, *로그인된 모든 기기의 방문 기록
읽기·변경*, *북마크*, *다운로드 관리*, *네이티브 앱과의 통신* 이 들어 있다. 공식 문서에
그대로 나열돼 있는 항목들이다. 코덱스 자체 확인·허용목록이 그 위에 한 겹 더 있지만,
**브라우저에 부여된 권한 자체는 그만큼 넓다.**

**둘째, 페이지 내용은 신뢰할 수 없는 입력이다.** 공식 문서가 반복해서 쓰는 표현이
"page content as untrusted context" 다. 사이트에 접근 권한을 준 것과 그 사이트의 내용이
믿을 만한 것은 별개이며, 페이지에 적힌 문장이 에이전트에게 권한을 주지 않는다. 글을 쓰러
들어간 관리자 페이지에 남이 남긴 댓글이 떠 있다면, 그건 데이터지 지시가 아니다.

**셋째, 방문 기록.** 문서는 방문 기록에 내부 URL·검색어 같은 민감한 텔레메트리가 섞일 수
있다고 경고하면서, 그래서 방문 기록에는 **"항상 허용" 옵션을 두지 않았다**고 밝힌다.
매번 묻는 게 설계다.

**넷째, full CDP.** 개발자 모드(전체 Chrome DevTools Protocol 접근)는 별도 설정이고 별도
승인이며, 조직 차원에서 `requirements.toml` 의 `[features]` 아래 `browser_use_full_cdp_access = false`
로 잠글 수 있다.

---

## 6. 그래서 결론 — 브라우저는 마지막 수단이다

여기까지 세워 놓고 나면, 정작 가장 중요한 판단은 반대 방향이다.

**API 나 git 이 있는 곳에 브라우저로 글을 쓰지 마라.** 브라우저 경로는 로그인 상태, 에디터
DOM, 확인 게이트, 파일 업로드 제약, 페이지 구조 변경까지 전부를 리스크로 안는다. 반면 같은
글을 파일로 쓰고 `git push` 하거나 Admin API 로 던지면, 실패는 **HTTP 상태 코드 한 줄**로
끝난다.

지금 읽고 있는 이 블로그도 그렇게 올라온다. 파일을 `_posts/` 에 쓰고 커밋하고 밀 뿐,
브라우저는 한 번도 안 뜬다. 브라우저를 꺼내야 하는 건 **기계가 들어갈 문이 없는 곳** —
공개 API 가 없는 사내 위키, 관리 콘솔, 폼으로만 받는 시스템 — 뿐이다.

그리고 어느 경로로 올리든 마지막 한 걸음은 같다. **떴는지 실측한다.** 클릭이 성공했다,
API 가 200 을 줬다, 빌드가 성공했다 — 셋 다 글이 보인다는 증거가 아니다. 어제 나는 이걸
다시 배웠다. 글 하나를 올렸는데 GitHub Pages 빌드는 `built` 라고 보고했고 페이지는 404 였다.
원인은 글의 `date` 가 실제 시각보다 2분 미래였던 것이고, Jekyll 은 미래 글을 **에러 없이 조용히
빼 버린다.** 게시의 증거는 게시된 페이지의 본문에만 있다.

---

## 부록: 어디서 무엇을 고를지 한 줄로

- 올릴 곳에 **로그인이 필요 없다** → in-app 브라우저(`@Browser`)로 충분. 단 CLI 에는 없다.
- **로그인이 필요하다** → 크롬 확장(`@Chrome`). 데스크톱 앱에서.
- **CLI 에서 꼭 해야 한다** → MCP(Playwright / Chrome DevTools). 로그인은 별도 문제로 남는다.
- **API 나 git 이 있다** → 브라우저를 쓰지 마라.

---

## References

**1차·공식 (사실로 인용)**

- OpenAI, *In-app browser / Browser — Codex app*. <https://developers.openai.com/codex/app/browser> — 별도 프로필, Computer Use, 파일 업로드 자동화 불가, 민감 동작 확인, Developer mode/full CDP, `requirements.toml` 잠금.
- OpenAI, *Browser* (ChatGPT Learn). <https://learn.chatgpt.com/docs/browser> — "Browser isn't available in Codex CLI or the Codex IDE extension."
- OpenAI, *Codex Chrome extension*. <https://developers.openai.com/codex/app/chrome-extension> — 로그인된 브라우저 상태, `@Chrome`, 호스트 단위 확인, 허용/차단 목록, always-allow 의 Elevated Risk 표기, 확장 권한 목록, 방문 기록에 always-allow 없음, 저장 범위.
- OpenAI, *Command line options — Codex CLI*. <https://developers.openai.com/codex/cli/reference> — `codex mcp`, `codex plugin`.
- Microsoft, *playwright-mcp* README. <https://github.com/microsoft/playwright-mcp> — 코덱스용 설치 명령과 `~/.codex/config.toml` 형식.
- Google Chrome DevTools 팀, *chrome-devtools-mcp* — 클라이언트 설정 문서. <https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/client-configurations.md> — `codex mcp add chrome-devtools -- npx chrome-devtools-mcp@latest`.
- Playwright, *Locator.fill()*. <https://playwright.dev/docs/api/class-locator#locator-fill> — 대상 요소 제약, `input` 이벤트, `pressSequentially()` 안내.

**내 환경에서의 실측 (재현 조건 명시)**

- `codex features list` 출력 3줄, `codex mcp add` 두 형태의 통과 여부와 생성된 `config.toml`.
  측정 환경: codex-cli 0.133.0-alpha.1, macOS Darwin 25.6.0, 2026-09-11. `mcp add` 는 임시
  `CODEX_HOME` 에서 실행했다. **다른 버전에서 같으리라는 보장은 없다.**

**사용자 보고 (벤더 확인 아님)**

- openai/codex issue #25647 — CLI TUI 에서 Browser 스킬이 마운트되지만 백엔드가 없음.
- openai/codex issue #26820 — CLI 가 크롬 확장 백엔드를 잡지 못함.
- openai/codex issue #27962 — 크롬 플러그인 설치·연결 상태인데 `iab` 만 노출됨.

*이 글은 위 출처들과 내 맥 한 대에서의 실측만을 근거로 한다. 중립 제3자가 같은 조건에서
재현한 결과는 찾지 못했고, 특히 백엔드 부재 증상은 버전·플랫폼 조합에 따라 다르게 나타난다는
보고가 같은 이슈 안에 섞여 있다.*
