---
layout: post
title: "Kiro 네 개의 얼굴 비교 — Web·IDE·CLI·Crew, 어디서 무엇을 시킬까"
date: 2026-09-28 06:47:40 +0900
categories: [개발도구, AI]
tags: [Kiro, KiroCrew, kiro-cli, AI코딩, 에이전트, 비교]
---

[어제 글](/2026/09/27/intro-to-kiro-agentic-ide/)에서 Kiro 가 IDE 하나가 아니라
여러 인터페이스의 묶음이라고 한 줄로 적고 넘어갔다. 이번 글은 그 한 줄을 풀어서,
**Web·IDE·CLI·Crew** 네 개를 같은 기준으로 나란히 놓는다.

결론부터 적으면 이렇다.

> - 네 개는 **같은 에이전트, 다른 실행 위치**다. 스펙·스티어링·MCP·스킬 같은 핵심 기능은 공유한다.
> - 가르는 기준은 두 개면 충분하다. **코드가 어디서 돌아가나**(내 맥 vs AWS 샌드박스)와 **내가 옆에 있어야 하나**(실시간 협업 vs 맡겨두기).
> - IDE = 내 맥 + 옆에 있음, CLI = 내 맥 + 터미널·CI, Web = 클라우드 + 맡겨두기, Crew = 내 맥 + 맡겨두기.

## 1. 공식 정의 — 한 문장씩

Kiro 공식 FAQ 는 네 개를 이렇게 구분한다([Kiro FAQ][home]).

| 인터페이스 | 공식 설명 (요약) |
| --- | --- |
| **IDE** | 로컬에서 에이전트와 **실시간으로 협업**하는 능동적 개발용 |
| **CLI** | **터미널** 워크플로, 커스텀 에이전트, **배포 파이프라인**용 |
| **Web** | 브라우저에서 **위임·조종**. 세션은 격리된 **클라우드 샌드박스**에서 돌고, 노트북을 닫아도 계속된다 |
| **Crew** | 세션을 넘어 **계속 작동**하는 오픈소스 개발 워크스페이스. 내 기기에서 돈다. 무료 |

같은 FAQ 가 덧붙이는 문장이 핵심이다. *"작업에 맞는 인터페이스를 쓰면 되고, 함께 쓸 때 가장 좋다."*
스티어링 파일은 모든 인터페이스에 공통으로 적용되고, 개인 설정은 클라우드 설정 동기화로 따라온다([Kiro FAQ][home]).

모바일 앱도 있지만 문서상 아직 프리뷰라 이 글에서는 뺐다.

## 2. 한 장 비교표

| 기준 | IDE | CLI | Web | Crew |
| --- | --- | --- | --- | --- |
| 실행 위치 | 내 PC | 내 PC·CI 러너 | **AWS 클라우드 샌드박스** | 내 PC·내 서버·컨테이너 |
| 형태 | Code OSS 기반 에디터 | 터미널 (`kiro-cli`) | 브라우저 (app.kiro.dev) | 데스크톱 앱 + 웹 대시보드 + 메신저 |
| 내가 붙어 있어야 하나 | 예 | 대화형은 예, headless 는 아니오 | 아니오 | 아니오 |
| 노트북 닫으면 | 멈춤 | 멈춤 | **계속** | 서버에서 돌리면 계속 |
| 리포 접근 | 로컬 폴더 | 로컬 폴더 | GitHub·GitLab 연결, 샌드박스에 clone | 로컬 폴더 전체 |
| 반복 작업 | Hooks | Hooks, CI 파이프라인 | **클라우드 Automations** (Web 전용) | 크론, 하트비트 |
| 대표 기능 | 스펙, 실시간 diff 검토 | headless, ACP, 음성 모드 | 자율 모드, 여러 리포 동시 변경 | 영구 메모리, 교훈 학습, 서브에이전트, 메신저 채널 |
| 비용 | Kiro 요금제 | Kiro 요금제 (headless 는 유료 플랜) | **유료 계정** 필요 | Crew 자체는 무료, 모델 호출은 Kiro 계정 |

아래는 표의 근거다.

## 3. IDE — 옆에 앉아서 같이 짠다

Kiro IDE 는 Code OSS 기반이라 VS Code 설정·테마·Open VSX 확장을 그대로 가져온다([Kiro FAQ][home]).
스펙 주도 개발(요구사항 → 설계 → 태스크)이 가장 잘 보이는 곳이고, 에이전트가 바꾼 코드를 에디터에서
바로 보고 되돌린다. 모드와 Autopilot 설정은 [따로 정리한 글](/2026/09/27/kiro-autopilot-and-five-builtin-modes/)에 있다.

**맞는 일:** 설계를 같이 다듬어야 하는 새 기능, 에이전트가 바꾼 걸 줄 단위로 봐야 하는 작업.
**안 맞는 일:** 사람이 자리를 비우는 긴 작업. 에디터를 닫으면 에이전트도 멈춘다.

## 4. CLI — 터미널과 파이프라인

`kiro-cli` 는 IDE 와 같은 핵심 기능(스티어링, 훅, MCP, 커스텀 에이전트, 스킬, 서브에이전트)을 쓰고,
터미널 전용 기능을 얹는다([Kiro CLI 문서][cli]).

- **Headless 모드**: `kiro-cli chat --no-interactive "프롬프트"` 로 사람 없이 돈다. 승인할 사람이 없으니 `--trust-tools=read,grep` 처럼 도구 권한을 미리 준다. `KIRO_API_KEY` 가 필요하고, API 키는 Pro 이상 유료 플랜만 발급된다([Headless mode][headless]).
- **ACP**: 다른 도구가 Kiro 에이전트를 프로그램으로 부를 수 있는 프로토콜이다([ACP][acp]).
- **구조화 출력**: `--output-format stream-json` 으로 이벤트를 JSON Lines 로 받는다([Headless mode][headless]).

공식 문서의 예시가 GitHub Actions 에서 PR 이 올라올 때마다 보안 리뷰를 돌리는 것이다.
**맞는 일:** CI 에서의 코드 리뷰·테스트 생성·빌드 실패 분석, 서버에 SSH 로 들어가서 하는 일.
**주의:** headless 에서 `--trust-all-tools` 는 편하지만, 문서도 최소 권한인 `--trust-tools` 를 권한다.

## 5. Web — 맡기고 퇴근한다

Web 은 네 개 중 유일하게 **코드가 내 기기 밖에서** 돈다. 작업을 맡기면 에이전트가
① 격리된 샌드박스를 띄우고 ② 허가된 리포를 clone 하고 ③ 프로젝트 설정을 감지해 환경을 잡고
④ 허가된 자원에만 접근해 작업하고 ⑤ 끝나면 샌드박스를 지운다([Sandbox][sandbox]).
샌드박스마다 헤드리스 Chrome 과 Playwright MCP 가 들어 있어서, 방금 고친 UI 를 에이전트가 직접 열어 확인한다.

Web 에만 있는 것이 두 가지다. 한 세션에서 **여러 GitHub·GitLab 리포를 동시에** 고칠 수 있고,
**클라우드 Automations**(정해진 조건에 따라 도는 작업)는 현재 Web 에서만 된다([Kiro FAQ][home], [Automations][automations]).

**맞는 일:** 잘 정의된 이슈를 맡기고 PR 로 받기, 노트북을 들고 다니는 사람의 긴 작업.
**안 맞는 일:** 내 로컬 네트워크에만 있는 자원이 필요한 일. 샌드박스의 인터넷 접근은 허용한 도메인으로 제한된다([Sandbox][sandbox]).

## 6. Crew — 내 기기에 사는 상주 에이전트

Crew 는 성격이 다르다. 공식 문서는 "로컬이나 내 하드웨어에서 돌아가는 오픈소스 개인 AI 에이전트"이고
**영구적이고, 스스로 배우고, 스스로 진화한다**고 소개한다([Crew Quick start][crew]).
설치하면 `kiro-cli` 설치와 로그인을 안내하는데, 즉 **Crew 는 CLI 위에 얹는 관리 계층**이다.
대화·도구 실행은 CLI 가 하고, Crew 는 그 위에 이런 것들을 더한다([Crew Quick start][crew]).

- 세션·메모리·스케줄·태스크 체크포인트가 게이트웨이를 재시작해도 남는다.
- "앞으로 항상 이렇게 해"라고 고쳐 주면 교훈으로 저장해 다음 세션에 적용한다.
- 크론으로 반복 작업을 돌리고, 하트비트로 시스템을 지켜보다 이상할 때만 알린다.
- 같은 런타임을 Slack·Discord·**Telegram**·Teams·Webex 등 메신저에 연결한다([Interfaces][crew-if]).

이 글이 그 사례다. 이 글은 내 맥에서 도는 **Crew 0.7.1 + kiro-cli 2.24.1** 조합에게 텔레그램으로
"비교 깃블"이라고 보내서 나왔다. 에이전트가 공식 문서를 읽고, 블로그 리포에 글을 쓰고, push 한 뒤
게시 URL 이 200 을 반환하는지까지 확인한다. 나는 휴대폰만 들고 있었다.

**맞는 일:** 내 서버·내 리포·내 클러스터를 계속 만지는 개인 운영, 메신저로 시키는 반복 업무.
**주의할 것:** 내 기기에서 **내 권한으로** 돈다. Web 의 샌드박스 같은 격리가 기본이 아니므로 승인 정책과
금지 명령 목록을 직접 챙겨야 한다. 실제로 이 블로그의 master push 도 승인 단계에서 몇 번 막혔다가 통과했다.
그게 정상이다.

## 7. 그래서 무엇을 쓰나

| 상황 | 추천 |
| --- | --- |
| 새 기능을 설계부터 같이 잡는다 | IDE |
| PR 마다 자동 리뷰를 돌린다 | CLI headless |
| 이슈를 맡기고 퇴근한다 | Web |
| 여러 리포를 한 번에 고친다 | Web |
| 매일 아침 내 서버 상태를 요약받는다 | Crew 크론 |
| 휴대폰으로 내 맥에 일을 시킨다 | Crew + 메신저 |

실제로는 섞어 쓴다. 나는 설계는 IDE 에서, 반복 운영과 글 발행은 Crew 에서 한다. 스티어링 파일이
공통이라 한쪽에서 정한 규칙이 다른 쪽에도 적용된다는 게 섞어 쓸 수 있는 이유다.

## 한계

- 표의 기능 구분은 2026-09-28 기준 공식 문서를 따랐다. Kiro 는 업데이트가 빠르다. 예를 들어 "Automations 는 Web 전용"은 FAQ 에 "현재(today)"라고 적혀 있다.
- Web·모바일은 직접 오래 써보지 않았다. 이 부분은 문서 인용이고 체험기가 아니다.
- 성능·품질 우열은 비교하지 않았다. 네 개는 같은 모델을 쓸 수 있어서, 차이는 모델이 아니라 **실행 위치와 권한**에서 나온다.

## References

- [Kiro 공식 홈페이지 FAQ — "How is Kiro Web different from Kiro IDE, CLI, and Kiro Crew?"][home]
- [Kiro FAQ][faq]
- [Kiro CLI 문서][cli]
- [Kiro CLI — Headless mode][headless]
- [Kiro CLI — ACP][acp]
- [Kiro Web — Sandbox][sandbox]
- [Kiro Web — Automations][automations]
- [Kiro Crew — Quick start][crew]
- [Kiro Crew — Interfaces][crew-if]
- [kirodotdev/KiroCrew (GitHub)](https://github.com/kirodotdev/KiroCrew)

[home]: https://kiro.dev/
[faq]: https://kiro.dev/faq/
[cli]: https://kiro.dev/docs/cli/
[headless]: https://kiro.dev/docs/cli/headless/
[acp]: https://kiro.dev/docs/cli/acp/
[sandbox]: https://kiro.dev/docs/web/sandbox/
[automations]: https://kiro.dev/docs/web/automations/
[crew]: https://kiro.dev/docs/crew/
[crew-if]: https://kiro.dev/docs/crew/interfaces/
