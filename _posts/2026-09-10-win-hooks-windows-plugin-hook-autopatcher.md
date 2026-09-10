---
layout: post
title: "윈도우에서만 빨간 글씨가 뜨는 이유 — win-hooks 가 고치는 것들"
date: 2026-09-10 23:27:24 +0900
categories: [tooling]
tags: [windows, claude-code, codex, plugin, hooks, nodejs, oss]
---

플러그인을 깔았다. 맥 쓰는 동료들은 잘 쓴다. 그런데 내 윈도우에서만 세션을 열 때마다 빨간 글씨가 뜬다.

[LilMGenius/win-hooks](https://github.com/LilMGenius/win-hooks) 는 정확히 그 상황 하나만 해결하는 도구다. Claude Code / Codex 플러그인의 훅(hook)이 윈도우에서 깨지는 걸 세션 시작마다 자동으로 고쳐 놓는다. MIT, Node.js, npm `@lilmgenius/win-hooks`, 2026-09-10 기준 v1.14.0.

이 글은 저장소를 직접 읽고 정리한 것이다. 인용한 수치·증상·원인은 전부 저장소의 [`README.md`](https://github.com/LilMGenius/win-hooks/blob/main/README.md) 와 [`AGENTS.md`](https://github.com/LilMGenius/win-hooks/blob/main/AGENTS.md) 에 적힌 내용이다.

## before — 왜 하필 윈도우만 깨지나

플러그인의 훅은 대개 `hooks.json` 에 "이 명령을 실행하라"라고 문자열로 적혀 있다. 그리고 그 문자열은 거의 항상 맥이나 리눅스에서 쓰이고 검증된다. 그래서 이런 게 그대로 들어간다.

- `bash hooks/check.sh` — 윈도우엔 `.sh` 를 직접 실행할 방법이 없다
- `semgrep ...` — 유닉스 도구가 깔려 있다고 가정한다
- `python3 script.py` — 윈도우는 보통 `python.exe` 만 있다
- `node ${CLAUDE_PLUGIN_ROOT}/hooks/x.js` — Git Bash 에선 되는데 훅을 띄우는 프로세스에선 `node` 가 안 보인다

README 는 이걸 사용자가 실제로 보는 에러 메시지 여섯 줄로 정리해 둔다.

| 보이는 에러 | 실제 원인 |
|---|---|
| `check.sh: No such file or directory` | 윈도우는 `.sh` 를 직접 못 돌린다 |
| `semgrep: command not found` | 플러그인이 없는 유닉스 도구를 부른다 |
| `'node' is not recognized` | Git Bash 에선 보이는데 훅 실행 프로세스에선 안 보인다 |
| `Python was not found; ... Microsoft Store` | 윈도우의 가짜 `python3` 자리표시자가 진짜를 가린다 |
| `JSON Parse error: Unrecognized token` | 설정 파일 맨 앞의 안 보이는 바이트(BOM) |
| `Cannot find module 'C:\Users...'` | 경로의 역슬래시가 훅 실행 전에 먹혔다 |

우회책은 있었다. `.sh` 를 손으로 `.cmd` 로 바꿔 쓰거나, 문제 훅을 지워 버리거나, WSL 안에서만 작업하거나. 셋 다 **플러그인이 업데이트되면 원상복구된다.** 그래서 문제는 "한 번 고치기"가 아니라 "고쳐진 상태를 유지하기"였다.

## 등장 — 한 번이 아니라 매번 고친다

설치는 한 줄이다.

```bash
# Claude Code
claude plugin marketplace add LilMGenius/win-hooks && claude plugin install win-hooks

# Codex
codex plugin marketplace add LilMGenius/win-hooks && codex plugin add win-hooks@win-hooks

# 플러그인 없이 지금 당장 고치기만
npx @lilmgenius/win-hooks
```

동작 원칙 세 개가 README·AGENTS.md 에 명시돼 있다.

1. **세션 시작마다 다시 돈다.** 나중에 설치한 플러그인, 업데이트로 다시 깨진 플러그인, 예전 win-hooks 가 남긴 잔해까지 대상이다.
2. **원본 위에 덮어쓰지 않는다.** 수리본은 원본 *옆에* 쓰고, 이미 정상인 건 건드리지 않는다.
3. **네트워크를 쓰지 않는다.** 텔레메트리·계정 없음. 플러그인 폴더 밖에는 자기 실행 로그만 남긴다.

세션 시작에 한 줄로 "돌았다"고 말하는 것도 설계 의도다. AGENTS.md 의 표현으로는, *아무도 볼 수 없는 훅은 아예 안 돈 훅과 구분되지 않기 때문*이다.

## 진짜 재미있는 부분 — 조용히 실패하는 것들

이 저장소의 값어치는 자동 패처라는 아이디어보다, `AGENTS.md` 에 쌓인 **32개의 CASE 기록**에 있다. 번호는 발견 순서로 고정돼 있어 비연속이고(최대 CASE-34), 재번호는 금지돼 있다. 그중 인상적인 넷.

### CASE-29 — 에러가 없는 게 증상이다

훅의 최후 수단은 PATH 에 있는 `bash.exe` 다. Git for Windows 가 없고 WSL 만 깔린 스톡 윈도우에서 그건 `%SystemRoot%\System32\bash.exe`, 즉 WSL 런처다. 이놈은 윈도우 경로를 못 연다 — `C:\x\y` 가 게스트에 `C:xy` 로 도착한다 — **그런데 그 실패에서 exit 0 을 낸다.**

> Symptom: none visible — that is the entire problem. On a machine with WSL but no Git for Windows, every patched hook would appear to run and do nothing, forever.

해결책은 후보 인터프리터에게 "네가 지금 돌릴 그 스크립트가 보이냐"를 증명시키는 것이다(`bash -c 'test -f "$WH_PROBE"'`). 여기에 함정이 하나 더 붙는다. 그 탐침 경로를 `$0` 로 넘기면 WSL 런처가 `$0` 를 `/bin/bash` 로 보고해서 `test -f` 가 통과해 버린다 — **걸러내려던 바로 그 인터프리터를 합격시킨다.** 그래서 경로는 환경변수로 넘긴다.

### CASE-09 — `where` 는 통과하는데 실행은 안 되는 python3

윈도우의 Microsoft Store App Execution Alias 는 `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` 에 있는 reparse point 다. `command -v python3` 는 **성공한다.** 실행하면 "Python was not found" 만 찍는다. 여기서 나온 원칙이 저장소 전체의 도그마가 된다.

> 인터프리터는 *실제로 돌아야* 인터프리터로 친다 (probes are functional, never path heuristics).

그래서 `*/WindowsApps/*` 를 블랙리스트하지 않는다. 그랬다면 정상적인 Store 설치 파이썬까지 죽인다. 대신 절대경로로 `-c ''` 를 실제로 돌려 보고, 통과한 절대경로를 훅 항목에 박아 둔다. 패치 시점에 한 번만 해석하므로 `PreToolUse` 같은 뜨거운 훅이 매번 인터프리터 기동 비용을 내지 않는다.

### CASE-31 — 어느 셸이 내 명령을 받을지 나는 모른다

Codex 의 `commandWindows` 가 cmd.exe 로 간다고 가정하고 `"<path>" <arg>` 형태로 뱉었다. Codex 는 세션 셸로 넘겼고, PowerShell 은 선두의 따옴표 문자열을 식(expression)으로 파싱한 뒤 첫 인자를 거부한다. 실측 결과가 명확하다.

- `"<path>" <arg>` → PowerShell 5.1 · pwsh 7 에서 exit 1, cmd.exe 에서 exit 0
- `cmd /c "<path>" <arg>` → 셋 다 exit 0

디스패처는 호스트의 선택이지 내 선택이 아니므로 폴백할 곳이 없다 — **한 줄이 셋 모두에서 동시에 유효해야 한다.** 그래서 Codex 쪽만 `cmd /c` 를 붙인다. Claude 쪽은 일부러 안 붙인다. 그 체인엔 Git Bash 가 낄 수 있고, Git Bash 는 `/c` 를 `C:/` 로 MSYS 변환해 버린다.

테스트 게이트도 같은 태도다. 공백이 들어간 경로에 실제 `hookRef` 를 만들어 **설치된 모든 PowerShell 에디션에서** 돌린다. 처음 통과한 셸에서 멈추면, 하필 그 도달하지 못한 셸을 쓰는 사용자의 머신에서만 초록불이 나기 때문이다.

### CASE-22 — 수리 자체가 고장 나 있었다

플러그인이 `pretooluse.py` 라는 이름의 bash 스크립트를 넣어 놓고 그게 자기 자신을 `python3` 로 부르는 경우가 있다. 수리는 그 파일을 no-op 으로 덮는 것인데, 예전 no-op 은 `#!/bin/bash` + `exit 0` 이었다. 그 두 줄은 **그 파일을 부르는 python 이나 node 에게는 문법 오류다.** 수리된 훅이 수리 대상이던 바로 그 메시지로 계속 실패했다. 지금의 no-op 은 `#!/bin/sh` 한 줄뿐이다 — python·node·bash 모두에서 exit 0 인 게 실측으로 확인된 유일한 형태다.

## bash 를 버리고 Node 로 간 이유

AGENTS.md 의 한 문단이 이 결정을 요약한다.

> win-hooks is a JSON transformation program that was first written in a language that cannot parse JSON.

awk·sed 로 훅 명령 문자열을 매칭하다가 CASE-05·16·19·24 네 개의 버그가 나왔다 — 파싱된 객체를 상대로는 존재할 수 없는 종류의 버그들이다. 속도도 구조적으로 느렸다. 17초짜리 프로파일이 32~36ms 짜리 coreutils fork 약 300회 + `node` 기동 76ms 였다. **fork 비용 자체가 런타임**이었으므로 셸 튜닝으로는 답이 없었다. Node 는 Claude Code 의 하드 의존성이라 사용자에게 추가 비용도 없다.

실측 결과: 전체 수리 1회 **21초 → 0.35초**, 테스트 스위트 약 38초 → 약 4초.

## 구조

파일 배치가 그대로 설계 문서다.

```
bin/win-hooks.mjs    진입점: [patch|heal|status] [claude|codex] [--changed-only] [--announce]
src/heal.mjs         오케스트레이션, 상태 디렉터리, 하트비트
src/patch.mjs        플러그인 스캔, 훅 디스크립터 작성, hooks.json 재작성
src/verify.mjs       패치 후 헬스체크 + 자동 재수리
src/settings.mjs     ~/.claude/settings.json 훅 명령 재작성
src/rules.mjs        도메인 SSOT: 무엇이 비호환인가, 훅 이름, 디스크립터 모양
src/hosts.mjs        Claude vs Codex 디스크립터 + 플러그인 열거
src/env.mjs          인터프리터 탐침, 인코딩 안전 파일 IO
hooks/run-hook.cmd   cmd.exe/bash 폴리글롯 진입점 (BOM 없음, CASE-01)
hooks/run.mjs        디스패처: 훅 이름을 해석해 실행 (CASE-29)
```

핵심은 **Claude 와 Codex 의 차이가 `src/hosts.mjs` 한 곳에만 산다**는 것이다. 엔진은 하나고, 호스트별 디스크립터와 열거 방식만 갈린다. `src/rules.mjs` 는 "무엇이 비호환인가"의 단일 진실 공급원이고, `DISPATCH_PREFIX = 'cmd /c '` 같은 CASE-31 의 결론이 상수로 박혀 있다.

테스트는 CASE 번호와 묶여 있다. 러너가 `AGENTS.md` 의 `### CASE-NN` 헤딩을 전부 읽어 통과한 테스트가 언급한 번호와 대조하고, **커버되지 않은 CASE 가 있으면 실행이 실패한다.** 테스트로 exercise 할 수 없는 CASE(예: CASE-14 는 코드 경로가 아니라 작업 원칙이다)는 사유를 적어 waiver 에 올려야 하고, 더 이상 필요 없어진 waiver 는 stale 로 또 실패한다.

## 한계 — 정직하게

- **윈도우 전용이다.** `package.json` 의 `"os": ["win32"]` 이고 비-윈도우에서는 exit 0 으로 빠진다. 그래서 맥에서 테스트 스위트를 돌려 나온 숫자는 통과 증거로 쓸 수 없다. CI(`.github/workflows/test.yml`) 도 주석에 그렇게 못박고 `windows-latest` 러너에서만 돌린다.
- **세션 중간 패치는 즉시 반영되지 않는다.** 두 트리거 모두 디스크의 `hooks.json` 을 고치는데 Claude Code 는 이미 훅 설정을 메모리에 올린 뒤다. 다음 세션이나 `/reload-plugins` 이후에 적용된다(CASE-13).
- **규모는 작다.** 2026-09-10 기준 star 42 · fork 4, 첫 커밋 2026-03-15, 최근 push 2026-08-31. 프로덕션 채택 사례를 뒷받침할 중립 제3자 자료는 찾지 못했다. 여기 적은 성능 수치(21s → 0.35s 등)는 전부 **저자의 저장소 자체 주장**이며, 윈도우 머신에서 재현해 본 것이 아니다.
- 훅이 셸 스크립트인 플러그인을 고치려면 [Git for Windows](https://git-scm.com/download/win) 가 필요하다.

## 남는 것

도구를 쓸 생각이 없어도 `AGENTS.md` 는 읽을 값어치가 있다. 32개 CASE 의 절반쯤은 "에러가 안 보이는 게 증상"인 부류다 — WSL bash 가 실패하고 exit 0 을 내는 것, Store 의 `python3` 스텁이 `where` 를 통과하는 것, 수리 no-op 자체가 문법 오류인 것. 셋 다 로그만 봐서는 영원히 못 찾는다.

여기서 반복되는 판정 기준이 하나 있다. **경로 휴리스틱으로 판단하지 말고 실제로 돌려서 판단하라.** 있는지 묻지 말고 되는지 물어라. 윈도우 얘기지만 윈도우에만 해당하는 얘기는 아니다.

## References

- LilMGenius, *win-hooks* (GitHub 저장소, MIT) — <https://github.com/LilMGenius/win-hooks>
- LilMGenius, *win-hooks README.md* — <https://github.com/LilMGenius/win-hooks/blob/main/README.md>
- LilMGenius, *win-hooks AGENTS.md* (아키텍처 · CASE-01~34) — <https://github.com/LilMGenius/win-hooks/blob/main/AGENTS.md>
- npm 레지스트리, `@lilmgenius/win-hooks` v1.14.0 (최초 배포 2026-07-22, 최신 2026-08-31) — <https://www.npmjs.com/package/@lilmgenius/win-hooks>
- Anthropic, *Claude Code plugins reference* — <https://code.claude.com/docs/en/plugins-reference>
- Git for Windows — <https://git-scm.com/download/win>
