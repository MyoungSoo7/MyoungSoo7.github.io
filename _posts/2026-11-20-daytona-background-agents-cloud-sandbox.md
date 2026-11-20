---
layout: post
title: "노트북을 덮어도 일하는 에이전트 — Daytona 「Building background agents with Daytona sandboxes」 정리와 빠진 함정 셋"
date: 2026-11-20 17:53:24 +0900
categories: [AI, 인프라]
tags: [코딩에이전트, 백그라운드에이전트, 샌드박스, Daytona, ClaudeCode, 관측성]
---

> 🎤 원 발표: [Building background agents with Daytona sandboxes — James Murdza (Arize AI 유튜브, 19분)](https://www.youtube.com/watch?v=sLBx7no4pZQ)
> 📝 받은 요약의 출처: [코딩 에이전트는 클라우드 샌드박스에서 돌려야 합니다 — Sean Lee, 아라이즈 코리아 인사이트](https://www.arizekorea.com/insights/post/daytona-cloud-sandbox-background-coding-agents-ovUpAvW92Prztzh)

## 누가, 어디서

James Murdza는 샌드박스 회사 Daytona의 커뮤니티 앰배서더다. Arize AI가 뉴욕에서 연 빌더 밋업에서 19분짜리 세션을 했고, 영상은 2026년 10월 28일 Arize AI 유튜브에 올라왔다. 이 글이 정리한 요약은 그 세션을 아라이즈 코리아의 Sean Lee가 리뷰한 글에서 왔다.

출처의 성격부터 짚어 둔다. **발표자는 Daytona 사람이고, 리뷰를 쓴 곳은 관측성 도구 Arize Phoenix·Arize AX를 파는 Arize의 한국 사이트다.** 그래서 "Daytona가 가장 빠르다"는 Daytona의 주장이고, 리뷰 끝의 "관측성을 함께 설계하라"는 Arize의 관점이다. 둘 다 틀린 말은 아니지만 이해관계가 있는 말이다.

이 글은 발표 녹취와 Daytona·Claude Code 공식 문서, 패키지 소스에 대조해 다시 썼다. 요약에는 없지만 실제로 돌려 보면 부딪힐 함정 셋을 뒤에 따로 모았다.

## 한 줄 요약

코딩 에이전트를 노트북 터미널에서 꺼내 클라우드 샌드박스에 넣으면, 노트북을 덮어도 계속 돌고, 여러 개를 동시에 돌릴 수 있고, 정해진 시각에 저절로 돌게 할 수도 있다. Murdza는 이걸 타입스크립트 코드 몇 단계로 보여 줬다.

리뷰어 Sean Lee는 진짜 메시지를 "에이전트를 사람 개발자처럼 관리하라"로 읽는다. 격리된 작업 공간을 주고, 브랜치 하나만 맡기고, 결과는 PR로 받는다.

## 1. 왜 노트북 밖으로 꺼내나

발표는 일화로 시작한다. 70대인 Murdza의 어머니가 기사 하나를 보내왔다. 요즘 부모들은 아이 축구 연습장에 반쯤 연 노트북을 들고 간다, 코딩 에이전트가 돌고 있어서. 그리고 "이게 네가 하는 일이니?"라고 물었다고 한다.

이 장면이 백그라운드 에이전트가 푸는 문제다. 대부분 Claude Code나 Codex를 로컬 터미널에서 돌리니, 노트북을 덮으면 에이전트도 멈춘다. 로컬에는 다른 제약도 있다.

- 생성된 코드를 그냥 실행하면 파일이 영구 삭제되거나 정보가 샐 수 있다. 그래서 권한을 좁게 쥐게 된다.
- RAM이 바닥나면 병렬 실행도 끝난다.
- 두 브랜치의 프리뷰 서버를 동시에 띄우면 같은 포트를 두고 싸운다.

Daytona가 내세운 장점은 넷이다.

| 장점 | 발표 내용 | 성격 |
| --- | --- | --- |
| 속도 | 밀리초 단위 기동, 벤치마크상 가장 빠른 축 | Daytona 자사 주장, 이 글에서 검증하지 않음 |
| 보안 | 에이전트가 할 수 있는 최악이 샌드박스 안의 자기 결과물 삭제로 한정 | 단, 밖으로 나가는 것은 별개 (아래 함정 1) |
| 확장 | RAM·CPU·스토리지를 필요한 만큼, 실행 시간 제한 없음 | |
| 사전 구성 | 도커 이미지나 코드로 환경을 미리 구움 | |

리뷰어가 가장 무게를 둔 건 보안 항목의 뒷면이다. 버려도 되는 샌드박스라면 `--dangerously-skip-permissions` 같은 옵션을 망설임 없이 켤 수 있고, 에이전트가 낼 수 있는 성능은 허락된 권한에 비례한다는 것이다.

## 2. 백그라운드 에이전트를 만드는 6단계

발표 중간은 Daytona 타입스크립트 SDK로 백그라운드 에이전트를 짜는 흐름이다.

**① 헤드리스 + JSON 스트리밍으로 실행.** 터미널 UI로 쓰던 에이전트를 API처럼 다루려면 JSON 스트리밍 모드가 필요하다. Claude Code, Codex, Gemini 모두 프롬프트를 인자로 받고 결과를 JSON 줄 단위로 내보내는 모드가 있다. 도구 호출 하나가 JSON 한 줄로 나오니, 파싱하면 그 위에 UI를 얹을 수 있다. 문제는 에이전트마다 JSON 형식이 전부 달라서 파서를 따로 짜야 한다는 것이다.

Claude Code라면 이렇게 부른다. `-p` 와 `stream-json` 을 함께 쓸 때는 `--verbose` 가 필수다. 빠지면 CLI가 실행을 거부한다 ([Claude Code headless 문서](https://code.claude.com/docs/en/headless)).

```bash
claude -p "<프롬프트>" --output-format stream-json --verbose
```

**② 스냅샷.** Claude Code와 SDK를 설치한 이미지를 Daytona 스냅샷으로 구워 둔다. 이 스냅샷 하나로 샌드박스 수천 개를 찍어낸다. 건너뛰어도 되지만 샌드박스를 띄울 때마다 1초쯤 더 걸린다.

**③ 샌드박스 생성 + 자동 중지.** `daytona.create` 로 스냅샷 기반 샌드박스를 만들고, 예를 들어 15분 미사용 시 중지를 건다. 안 쓰는 동안 돈이 나가지 않게 하는 장치다. (이 설정에 함정이 있다. 함정 2 참고.)

**④ 저장소 클론.** SDK에 내장된 git 기능으로 작업할 저장소를 클론한다 ([Daytona git 문서](https://www.daytona.com/docs/git-operations)).

**⑤ "너는 샌드박스 안에 있다"는 시스템 프롬프트.** 필수는 아니지만 효과가 크다. 홈 디렉터리 위치, 서버를 띄우면 Daytona 프리뷰 URL로 접근된다는 사실과 그 URL 패턴, 끝나면 커밋하라는 지시를 넣는다. 이 한 단계로 에이전트가 자기가 띄운 웹서버를 사람에게 보여 주는 법을 스스로 안다.

**⑥ 비동기 실행 → 출력 파싱 → 푸시.** 세션 명령을 `runAsync` 로 백그라운드 실행하고, 출력을 받아 JSON 줄을 파싱한다. 끝나면 Daytona git 툴박스로 변경을 푸시한다.

Murdza는 이 과정을 `background-agents` 로 묶어 공개했다. 정확히 하면 `npx background-agents` 는 데스크톱 앱 런처이고, 내 코드에서 쓰는 라이브러리는 `@background-agents/sdk` 다 ([GitHub 저장소](https://github.com/jamesmurdza/background-agents), [SDK README](https://github.com/jamesmurdza/background-agents/blob/main/packages/sdk/README.md)). 발표에서는 Claude·Codex·Gemini·Copilot·Goose·OpenCode·Kilo·Pi 여덟 개를 말했는데, 지금 README의 지원 목록은 Command Code·Droid·Kimi가 더해져 열한 개다.

README를 보면 지금 SDK는 발표에서 보여 준 직접 스트리밍 방식이 아니다. 에이전트를 분리된 백그라운드 잡으로 띄워 로그 파일에 JSON을 쓰게 하고, SDK가 그 파일을 주기적으로 읽는다. 끝나면 종료 코드가 담긴 파일로 완료를 알린다. `sandbox.id` 와 `session.id` 를 저장해 두면 내 서버가 재시작돼도 다시 붙을 수 있다. 서버리스 함수보다 오래 사는 작업을 위한 선택이다.

## 3. 데모 — 채팅 하나 = 샌드박스 하나 = 브랜치 하나

데모 웹앱은 왼쪽 채팅 하나하나가 별도 샌드박스다.

첫 장면부터 재귀적이다. Murdza가 발표 직전 파워포인트 파일을 올리고 Claude에게 reveal.js 웹 프레젠테이션으로 바꾸라고 시켰는데, 지금 화면의 발표 자료가 그 결과물이었다. Claude는 스스로 파이썬 서버를 띄웠고, 시스템 프롬프트에서 배운 대로 Daytona 공개 프리뷰 URL로 보여 줬다.

본 데모는 병렬 작업이다.

1. 간단한 마인크래프트 비슷한 게임을 만드는 채팅이 있다.
2. 이 채팅에서 브랜치를 갈라 "나이트 모드 추가"를 시킨다. 부모 샌드박스 코드를 복사한 새 샌드박스가 생긴다.
3. 동시에 부모 채팅에는 청중 제안대로 "소 추가"를 시킨다.
4. 두 에이전트가 각자 샌드박스, 각자 브랜치에서 일한다. GitHub에는 커밋 두 개씩 가진 브랜치 둘이 갈라져 있다.
5. 나이트 모드 브랜치를 소 브랜치로 머지하니 충돌 없이 합쳐졌고, 소와 나이트 모드가 함께 있는 게임이 됐다.

(받은 요약은 머지에서 충돌이 났다고 했지만, 녹취에서는 충돌 없이 합쳐졌다. Murdza는 충돌이 나면 데모에 10분이 더 필요하다고 농담했다.)

설계 원칙은 단순하다. 각 에이전트는 자기 브랜치에만 푸시할 수 있으니, 몇 개를 돌리든 사람이 일부러 머지하기 전까지 서로 부딪치지 않는다. Murdza는 여러 코딩 에이전트를 협업시키는 최선의 방법이 사람에게 하듯 버전 관리와 git을 쓰는 것이라고 정리한다.

로컬 `git worktree` 로도 비슷하게 할 수 있지만, 노트북 RAM이 바닥나면 끝이고 프리뷰 서버끼리 포트를 다툰다. 샌드박스는 이 문제를 구조적으로 없앤다.

## 4. 스케줄 에이전트 — 매일 아침 9시의 코드 위생 PR

리뷰어가 가장 실용적이라고 꼽은 부분이다. 백그라운드 에이전트는 예약 실행이 된다.

Murdza는 매일 오전 9시에 도는 에이전트를 저장소 하나에 붙여 두었다. 프롬프트는 죽은 코드, 지나치게 큰 컴포넌트·클래스 같은 위생 문제를 찾아 한두 개만 고치라는 것이다. 큰 코드베이스라 매일 뭔가 찾아내 PR을 만들고, GitHub 알림이 오면 Murdza가 리뷰한다. README를 최신으로 유지하는 에이전트도 같은 방식으로 돈다.

"한두 개만"이 핵심이다. 리뷰할 사람이 하루에 감당할 크기로 작업을 자른 것이다.

## 5. 리뷰어의 시선 — 병목은 리뷰로, 그다음은 관측성

리뷰를 쓴 Sean Lee는 세 가지를 짚는다.

1. **에이전트를 어디서 돌리느냐는 이제 인프라 결정이다.** 병렬·예약 실행·권한 전면 개방이 기본값이 되면 CI/CD와 같은 급의 결정이 된다.
2. **병목은 생성에서 리뷰로 옮겨 간다.** 데모에서도 에이전트 둘을 돌리는 데는 문제가 없었고, 일이 생기는 건 사람이 합치는 순간이었다. 에이전트 열 개가 밤새 PR 열 개를 올리면 누가 무슨 근거로 승인하나.
3. **그래서 관측성이 샌드박스와 짝을 이뤄야 한다.** JSON 스트리밍은 에이전트의 모든 행동이 이미 트레이스 형태로 흘러나온다는 뜻이다. 이걸 모으면 어떤 파일을 왜 고쳤는지, PR 하나에 도구 호출과 토큰이 얼마나 들었는지, 예약 에이전트의 PR 품질이 시간이 지나며 떨어지는지 평가할 수 있다. 리뷰는 Arize Phoenix와 계측 표준 OpenInference를 예로 든다.

앞서 말했듯 3번은 관측성 도구를 파는 회사의 관점이다. 그래도 논리 자체는 서 있다. 내가 보지 않는 동안 일어난 일을 나중에 확인할 수단이 없으면, 백그라운드로 돌린 의미가 리뷰 단계에서 사라진다.

## 받은 요약에 없던 함정 셋

발표와 리뷰는 "권한을 다 열어도 안전하다"는 쪽에 무게를 둔다. 공식 문서와 소스를 대조하면 단서가 붙는다.

### 함정 1. 샌드박스는 버려도, 나간 것은 남는다

"최악이래야 샌드박스 안의 자기 결과물을 지우는 것"은 **샌드박스 안의 피해**에만 맞는 말이다. 에이전트는 GitHub에 푸시하고, API를 부른다.

`@background-agents/sdk` 의 기본 사용법은 `ANTHROPIC_API_KEY` 를 `env` 로 샌드박스에 넘기는 것이다 ([SDK README](https://github.com/jamesmurdza/background-agents/blob/main/packages/sdk/README.md)). 권한을 다 연 에이전트는 그 키를 읽을 수 있고, 네트워크가 열려 있으면 내보낼 수도 있다. Murdza의 Daytona 블로그 글은 GitHub 토큰 같은 자격 증명이 샌드박스 밖에 머문다고 설명한다 ([Daytona 블로그](https://www.daytona.io/dotfiles/background-agents-sdk-with-daytona)). 그러니 무엇이 안에 있고 무엇이 밖에 있는지는 자격 증명마다 따로 확인해야 한다.

같은 날 정리한 Anthropic Lydia Hallie의 발표가 정확히 이 지점을 다룬다. 클라우드 머신은 일회용이어도 푸시한 커밋과 보낸 메시지는 남는다. 그래서 Claude Code 클라우드 세션은 API 키를 VM 밖의 프록시에서 붙이고, deny 규칙을 저장소에 커밋해 같이 가져가라고 권한다 ([글 보기]({% post_url 2026-11-20-lydia-hallie-rethinking-claude-code-best-practices %})). 권한을 다 열 거라면 적어도 이 두 가지는 따져 볼 일이다.

- 비밀이 샌드박스 **안**에 있는가, 밖에서 붙는가.
- 브랜치 보호와 CI로, 에이전트가 푸시할 수 있는 곳을 자기 브랜치로 묶었는가. 데모의 "채팅 하나 = 브랜치 하나"는 안전장치이기도 하다.

### 함정 2. 15분 자동 중지가 일하는 에이전트를 끊을 수 있다

Daytona의 자동 중지 기본값은 15분이다. 문서는 이 타이머가 **안에서 돌고 있는 프로세스로는 초기화되지 않는다**고 분명히 적는다. 타이머를 되돌리는 건 프리뷰 URL로 들어온 요청, SSH 연결, Toolbox SDK API 요청 같은 외부 상호작용뿐이다. 바깥과 주고받지 않고 15분 넘게 도는 작업은 중간에 멈출 수 있다고 문서가 직접 경고한다 ([Daytona 샌드박스 문서](https://www.daytona.io/docs/en/sandboxes/)).

백그라운드 에이전트는 바로 그 "바깥과 말없이 오래 도는 작업"이다. SDK가 주기적으로 로그 파일을 읽는 방식이라면 그 읽기가 Toolbox 요청이 되어 타이머를 되돌릴 가능성이 높다. 하지만 아무도 폴링하지 않는 예약 에이전트라면 사정이 다르다. 에이전트를 직접 붙인다면 자동 중지 간격을 작업 길이에 맞추거나, 0으로 끄고 끝날 때 직접 지워야 한다. 0은 무기한 실행이라 비용 통제가 다시 내 몫이 된다.

### 함정 3. 프리뷰 URL은 기본이 비공개다

데모는 공개 프리뷰 URL로 발표 자료를 보여 줬다. Daytona 문서를 보면 노출된 포트마다 공개·비공개를 따로 정하고, 비공개 포트는 토큰이 있어야 열린다. 서명된 프리뷰 URL은 주소에 자격 증명이 박혀 있어서, 링크를 가진 사람은 만료되거나 취소되기 전까지 누구나 쓸 수 있다 ([Daytona 프리뷰 문서](https://www.daytona.com/docs/preview)).

에이전트가 띄운 서버를 사람에게 보여 주려고 공개로 열면, 그 서버에 무엇이 떠 있든 인터넷에 열린다. 시스템 프롬프트에 URL 패턴을 알려 줄 때 공개로 열어도 되는 것이 무엇인지도 같이 적어 두는 편이 낫다.

## 대조표 — 받은 요약 vs 확인 결과

| 받은 요약 | 확인 결과 |
| --- | --- |
| 스트리밍 실행 예시 `stream-json` 등 | 맞다. Claude Code는 `-p` + `stream-json` 에 `--verbose` 가 필수 |
| 유휴 15분 뒤 자동 중지로 비용 통제 | 맞다. 15분은 Daytona 기본값이기도 하다. 다만 안에서 도는 프로세스는 타이머를 되돌리지 않는다 (함정 2) |
| 병렬 데모 머지 | 녹취상 충돌 없이 합쳐졌다 |
| `npx background-agents` 패키지 | 정확히는 데스크톱 앱 런처. 라이브러리는 `@background-agents/sdk`, 현재 11개 에이전트 지원 |
| Daytona 빠른 기동 | Daytona 자사 주장. 독립 벤치마크는 이 글에서 확인하지 않았다 |
| 버려도 되는 환경이라 권한을 과감히 연다 | 샌드박스 안의 피해에만 해당. 푸시·API 호출·넘겨준 키는 별개 (함정 1) |
| 관측성 체계(Arize Phoenix 등)를 함께 설계 | 리뷰어(Arize) 측 주장. 논리는 타당하나 이해관계 있음 |

## 근거의 한계

- 발표자와 리뷰어 모두 이 주제에 상업적 이해관계가 있다 (Daytona, Arize). 중립적인 제3자 비교, 예를 들어 다른 샌드박스 서비스나 Claude Code 클라우드 세션과의 맞비교는 찾지 못했다.
- 데모는 작은 게임 하나와 기능 둘이다. 에이전트 열 개가 같은 코드를 건드릴 때의 머지 비용은 발표에서 보여 주지 않았다.
- 함정 2의 "SDK 폴링이 타이머를 되돌릴 가능성이 높다"는 문서의 초기화 조건에서 추론한 것이고, 실측하지 않았다.

## References

1. James Murdza, "Building background agents with Daytona sandboxes", Arize Builders Meetup NYC, Arize AI YouTube, 2026-10-28. <https://www.youtube.com/watch?v=sLBx7no4pZQ>
2. Sean Lee, "코딩 에이전트는 내 노트북이 아니라 클라우드 샌드박스에서 돌려야 합니다", 아라이즈 코리아 인사이트, 2026-11-14. <https://www.arizekorea.com/insights/post/daytona-cloud-sandbox-background-coding-agents-ovUpAvW92Prztzh>
3. James Murdza, "How I Built the Background Agents SDK with Daytona", Daytona Dotfiles, 2026-04-24. <https://www.daytona.io/dotfiles/background-agents-sdk-with-daytona>
4. jamesmurdza/background-agents (GitHub) 및 SDK README. <https://github.com/jamesmurdza/background-agents>
5. Daytona Docs, "Sandboxes" (auto-stop, 타이머 초기화 조건). <https://www.daytona.io/docs/en/sandboxes/>
6. Daytona Docs, "Preview URLs". <https://www.daytona.com/docs/preview>
7. Daytona Docs, "Git Operations". <https://www.daytona.com/docs/git-operations>
8. Claude Code Docs, "Run Claude Code programmatically" (headless, stream-json). <https://code.claude.com/docs/en/headless>
9. Claude Code Docs, "Configure cloud environments" (network secrets). <https://code.claude.com/docs/en/cloud-environments>
