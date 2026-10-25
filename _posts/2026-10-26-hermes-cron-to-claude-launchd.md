---
layout: post
title: "에이전트 크론을 옮기며 배운 것 — LLM 이 필요 없는 단계에서 LLM 을 빼기"
date: 2026-10-26 00:53:13 +0900
categories: [DevOps, AI]
tags: [claude-code, launchd, cron, agent, headless, macos]
---

> 홈랩 맥에서 상주 에이전트(헤르메스)가 돌리던 정기 작업 3개를 Claude Code 헤드리스 실행 + macOS launchd 로 옮겼다. 이 글은 이전 방법보다는, 옮기면서 *무엇이 왜 깨져 있었는지*를 정리한 기록이다.

## 1. 문제: 에이전트 크론은 "어디서 실패할지"가 넓다

헤르메스 크론에 걸려 있던 작업은 7개였다. 이번에 옮긴 것은 세 개다.

| 작업 | 주기 | 하는 일 |
|---|---|---|
| 월간 청소 | 매월 1일 04:05 | npm 캐시·오래된 로그·`/tmp` 말뭉치 삭제 |
| 주간 인프라 리포트 | 토 03:00 | K3s 상태를 모아 블로그에 리포트 게시 |
| 데일리 브리핑 | 매일 08:30 | 기술 뉴스·구인공고를 조사해 블로그 게시 |

옮기기 전 실행 기록에서 확인된 사실은 이렇다.

- **10/1 월간 청소 실패.** 원인은 상위 LLM(Gemini)의 지출 한도 429였다. 청소 자체는 셸 스크립트 하나(`rm`, `npm cache clean`)인데, 결과 요약을 LLM 에게 맡기는 구조여서 *요약 단계가 실패하면 작업 전체가 실패로 기록*됐다.
- **10/24 주간 리포트 실패.** 수집은 끝났고 LLM 호출 단계(`hermes chat`)에서 죽었다.
- **재시작 기준선이 비어 있었다.** 주간 리포트는 "누적이 아니라 이번 주 증가분으로 판단하라"는 규칙을 갖고 있었는데, 그 증가분을 계산할 기준선 파일을 열어 보니 **항목 0개**였다. 규칙은 있었지만 그 규칙을 받쳐 줄 데이터가 없었던 것이다.

세 사실의 공통점은 하나다. **결정적(deterministic)으로 끝낼 수 있는 단계까지 LLM 경로에 묶여 있었다.**

## 2. 바꾼 것: 단계마다 "LLM 이 꼭 필요한가"를 따로 묻기

### 2-1. 청소 — LLM 을 아예 뺐다

셸 스크립트를 실행하고, 출력에서 확보 용량 한 줄을 `sed` 로 뽑고, `df -h /` 결과를 붙여 텔레그램 Bot API `sendMessage` 로 보낸다. 요약할 내용이 세 줄뿐이라 모델이 낄 자리가 없다. 이제 LLM 한도가 터져도 청소는 그대로 돈다.

### 2-2. 주간 리포트 — 수집은 코드가, 글쓰기는 모델이

예전에는 쿠버네티스 API 응답 JSON 을 거의 통째로 프롬프트에 넣었다. 이번에는 파이썬 수집기가 `kubectl -o json` 을 읽어 **표로 줄여서** 넘긴다. 노드 상태, 파드 phase 분포, 비정상 대기 컨테이너, Warning 이벤트 사유별 건수, Velero 백업, 그리고 **재시작 증가분**이 들어간다.

- 증가분 계산은 수집기가 한다. 모델은 덧셈·뺄셈을 하지 않는다.
- 기준선은 **게시에 성공한 경우에만** 갱신한다. 실패한 주의 증가분은 다음 주 리포트에 합쳐져 나온다. 그래서 숫자가 사라지지 않는다.
- 프롬프트에 "표에 없는 숫자는 만들지 않는다"와 운영 맥락을 명시했다. 맥락이란 무선 운영은 의도된 것이고, Velero 정기 백업도 비용 때문에 일부러 멈춰 둔 상태라는 점이다. 이걸 빼면 모델이 "백업 0건 = FAIL, 재가동 권고"를 매주 쓴다.

### 2-3. 데일리 브리핑 — 지시문은 그대로, 실행 규칙만 덧붙임

조사·작성 지시문(16개 섹션, 사실·추론·미확인 분리)은 원문 그대로 옮겼다. 덧붙인 것은 세 가지다.

1. 검색 도구 우선순위
2. 게시 절차: `pull --rebase` → 자기 파일만 `git add` → 거절 시 재시도, `--force` 금지 → 공개 URL 200과 본문 문자열 실측
3. **출력 계약**

## 3. 출력 계약: 마지막 줄은 `RESULT=` 아니면 `FAIL=`

헤드리스 에이전트가 끝났을 때 "성공했는가"를 판단하는 기준이 필요하다. 여기서 종료 코드만 믿으면 안 된다. Claude Code 공식 문서는 `-p` 실행이 성공하면 0, 실패하면 0이 아닌 코드로 끝난다고 적는다. 그런데 같은 문서가 **실행 *안에서* 일어난 실패, 예를 들어 인증 누락은 stdout 에 결과로 출력한다**고도 적는다([Run Claude Code programmatically](https://code.claude.com/docs/en/headless)).

그래서 래퍼는 종료 코드와 별개로 로그의 마지막 `RESULT=…`/`FAIL=…` 줄을 찾는다.

- `RESULT=<URL>` → 조용히 끝낸다(원래 규칙이 "결과를 채팅으로 보내지 말 것"이었다).
- `FAIL=…` **또는 그 줄이 아예 없음** → 텔레그램으로 실패 알림.

"줄이 없음"을 실패로 치는 게 핵심이다. 이렇게 해 두면 로그아웃·타임아웃·중간 크래시가 전부 같은 경로로 드러난다. **에이전트 크론에서 가장 위험한 실패는 시끄러운 실패가 아니라 조용한 정지**이기 때문이다.

## 4. 헤드리스 실행에서 밟은 함정 두 개

**① 자식 claude 가 봇의 폴링 슬롯을 뺏는다.** 이 맥에서는 Claude Code 세션 여러 개가 텔레그램 봇으로 상주한다. 봇 세션 안에서 테스트로 `claude -p` 를 띄우면 자식이 부모의 채널 상태 디렉터리 환경변수를 물려받는다. 그 결과 살아 있는 폴러를 종료시키고 자기가 그 자리를 차지한다. 자식이 끝나면 수신도 같이 끊긴다. 대책은 두 겹이다.
  - `--strict-mcp-config --mcp-config <파일>` 로 **검색용 MCP 서버 하나만** 띄운다. 이렇게 하면 전역 플러그인이 같이 올라오지 않는다([MCP 문서](https://code.claude.com/docs/en/mcp), [CLI reference](https://code.claude.com/docs/en/cli-reference)).
  - 실행할 때마다 상태 디렉터리를 `mktemp -d` 로 격리한다.

  MCP 설정 파일에는 API 키가 들어가므로 실행 시점에 원본 설정에서 해당 서버 블록만 복사한다. 그리고 권한 0600 으로 쓴다. 스크립트 소스에는 키를 남기지 않는다.

**② `--bare` 는 답이 아니었다.** 시작이 빠르고 재현성이 좋아 보이지만, 공식 문서대로 bare 모드는 **구독 로그인과 시스템 키체인을 읽지 않는다**. 대신 API 키를 요구한다([headless 문서](https://code.claude.com/docs/en/headless)). 이 환경은 구독 로그인으로 돌기 때문에 bare 를 빼고, MCP 만 strict 로 좁혔다. 대신 launchd 아래에서 실제로 한 번 돌려 키체인 인증과 검색 MCP 가 둘 다 살아 있는지 실측했다.

## 5. 왜 cron 이 아니라 launchd 인가

- Apple 문서는 `cron` 을 "지원은 되지만 권장하지 않는(deprecated in favor of launchd)" 방식으로 분류한다([Scheduling Timed Jobs](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)).
- 실질적인 차이는 **잠자기**다. 같은 문서에 따르면 cron 작업은 시스템이 잠들어 있으면 그 회차를 건너뛴다. 반면 `StartCalendarInterval` launchd 작업은 **깨어날 때 실행**된다. 단, 전원이 꺼져 있었다면 둘 다 다음 회차까지 실행되지 않는다(같은 문서).
- 운영 경험상 이 맥에서 사용자 crontab 은 개인정보 보호(TCC) 권한 때문에 멈춘 적이 있다. 그래서 이미 다른 정기 작업도 launchd 로 옮겨 둔 상태였다.

각 작업은 plist 하나와 셸 스크립트 하나로 구성된다. 스크립트는 `--dry` 인자를 주면 프롬프트 파일만 만들고 끝난다. 블로그에 실제로 글을 올리지 않고도 치환이 맞는지 볼 수 있다.

## 6. 전후 델타

| 축 | 이전 | 이후 |
|---|---|---|
| 청소가 LLM 한도에 묶임 | 예 (10/1 실패) | 아니오 — LLM 경로 없음 |
| 재시작 증가분 근거 | 기준선 0개 | 실측 기준선, 게시 성공 시에만 갱신 |
| 모델이 계산하는 숫자 | 원시 JSON 에서 직접 | 수집기가 계산한 표만 인용 |
| 조용한 정지 탐지 | 수단 없음 | `RESULT=` 줄이 없으면 알림 |
| 스케줄러 | 상주 에이전트 내부 | launchd (잠자기 후 실행 보장) |

남은 한계도 적어 둔다.

- 이제 세 작업이 **하나의 로그인에 묶였다.** 로그아웃되면 두 블로그 작업이 같이 멈춘다. 그 사실이 실패 알림으로 드러나도록 만든 것이지, 멈추지 않게 만든 것은 아니다.
- 헤르메스 크론은 삭제하지 않고 일시정지만 했다. 언제든 다시 켤 수 있다.
- 데일리 브리핑의 품질(출처 등급·중복 제거)은 프롬프트 규칙에 기대고 있다. 이것을 기계적으로 검증하는 단계는 아직 없다. 지금 하는 검증은 URL 200, 본문 문자열, 사설 IP 0건까지다.

## References

- Anthropic, *Run Claude Code programmatically* (headless `-p`, 종료 코드, `--bare` 인증 동작) — <https://code.claude.com/docs/en/headless>
- Anthropic, *Claude Code CLI reference* (`--mcp-config`, `auth status`) — <https://code.claude.com/docs/en/cli-reference>
- Anthropic, *Connect Claude Code to tools via MCP* (`--strict-mcp-config`) — <https://code.claude.com/docs/en/mcp>
- Apple, *Scheduling Timed Jobs* (launchd vs cron, 잠자기·전원 꺼짐 시 동작) — <https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html>
- Telegram, *Bot API — sendMessage* — <https://core.telegram.org/bots/api#sendmessage>
