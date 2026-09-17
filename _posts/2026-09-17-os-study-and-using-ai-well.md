---
layout: post
title: "AI를 잘 쓰는 것과 운영체제 공부의 상관관계 — 유비가 어디까지 맞고 어디서 깨지는가"
date: 2026-09-17 21:38:25 +0900
categories: [AI, Agent, Systems]
tags: [Operating System, OSTEP, MCP, Context Engineering, Agent, Concurrency]
---

먼저 정직하게 시작한다. **"OS를 공부한 사람이 AI를 더 잘 쓴다"를 측정한 연구를 나는 찾지 못했다.** 표본도, 통제도, 종속변수 정의도 없다. 그러니 이 글은 상관계수에 관한 글이 아니다.

내가 주장할 수 있는 건 더 좁고, 대신 검증 가능하다. **에이전트를 운영할 때 부딪히는 어려운 문제들이 운영체제 교과서의 목차와 같은 순서로 나온다는 것**, 그리고 그게 느슨한 비유가 아니라 **스펙 문서에 OS 용어가 그대로 박혀 있는 수준**이라는 것. 여기까지는 원문으로 보일 수 있다.

그리고 더 중요한 이야기를 하나 덧붙인다. **유비는 어딘가에서 반드시 깨지고, 깨지는 자리를 모르면 OS 지식이 오히려 오답을 만든다.** 4장이 그 얘기다.

---

## 1. "AI를 잘 쓴다"를 먼저 정의해야 한다

이 질문이 헐거운 이유는 대부분 "AI를 잘 쓴다"를 **프롬프트를 잘 쓴다**로 읽기 때문이다. 그 정의라면 OS는 상관이 없다. 글쓰기와 도메인 지식이 이긴다.

이 글의 정의는 다르다.

> **에이전트를 일에 붙여서, 끝까지 돌게 하고, 결과를 신뢰할 수 있게 만드는 것.**

한 번의 대화가 아니라 **여러 턴·여러 도구·여러 프로세스가 한 시간 넘게 도는 상태**를 운영하는 일이다. Anthropic 자신이 이 전환을 프롬프트 엔지니어링에서 **컨텍스트 엔지니어링**으로의 이동이라 부른다.[^ace]

> as we move towards engineering more capable agents that operate over multiple turns of inference and longer time horizons, we need strategies for managing the entire context state

이 정의를 채택하는 순간 문제는 **자원 관리 문제**가 된다. 그리고 자원 관리 문제를 60년째 정면으로 다뤄온 과목이 운영체제다.

---

## 2. OSTEP의 목차가 그대로 에이전트 운영의 목차다

*Operating Systems: Three Easy Pieces* (Arpaci-Dusseau 부부, 위스콘신, 무료 공개, Version 1.10 / 2023-11)는 책 전체를 **세 조각**으로 조직한다고 스스로 밝힌다.[^ostep]

> The book is centered around three conceptual pieces that are fundamental to operating systems: **virtualization, concurrency, and persistence.**

이 셋이 그대로 에이전트 운영의 세 가지 어려운 문제다.

### 2.1 Virtualization — 컨텍스트는 유한 자원이다

OS의 첫 조각은 "유한한 물리 자원을 무한한 것처럼 보이게 하기"다. 에이전트에서 그 자원은 컨텍스트 윈도우다.

Anthropic 문서의 표현은 거의 OS 교과서 문장이다.[^ace]

> Context, therefore, must be treated as a **finite resource with diminishing marginal returns.** Like humans, who have limited working memory capacity, LLMs have an **"attention budget"**

그리고 그 자원이 꽉 찼을 때 하는 일이 **compaction** — 대화를 요약해 새 컨텍스트로 갈아끼우는 것이다. Claude Code는 메시지 히스토리를 모델에 넘겨 요약하고, 아키텍처 결정·미해결 버그·구현 세부는 남기고 중복된 툴 출력은 버린 뒤, **가장 최근에 접근한 파일 다섯 개**와 함께 이어간다.[^ace]

OS를 아는 사람에게 이건 낯선 얘기가 아니다.

| OS | 에이전트 |
| --- | --- |
| 물리 메모리 | 컨텍스트 윈도우 |
| 가상 주소 공간 | 전체 대화·파일·툴 출력의 우주 |
| 페이지 교체 정책 (LRU 등) | 컴팩션이 무엇을 남기고 무엇을 버릴지 |
| working set | "지금 이 작업에 실제로 필요한 파일·사실" |
| thrashing | 컨텍스트를 채웠다 비웠다 하며 진도가 안 나가는 상태 |

**working set** 개념을 아는 사람은 "관련 파일 스무 개를 미리 다 열어두기"를 자연히 피한다. 그게 왜 손해인지 설명할 언어가 이미 있기 때문이다. Anthropic 문서도 다른 길로 같은 결론에 닿는다 — *"the smallest possible set of high-signal tokens."*[^ace]

### 2.2 Concurrency — 여기서 대부분이 깨진다

두 번째 조각. 서브에이전트를 쓰는 순간 **멀티프로세스 시스템을 운영하는 것**이다. Anthropic의 서브에이전트 설명은 프로세스 격리 그 자체다.[^ace]

> specialized sub-agents can handle focused tasks with **clean context windows** ... Each subagent might explore extensively, using tens of thousands of tokens or more, but returns only a condensed, distilled summary of its work (often 1,000-2,000 tokens).

깨끗한 주소 공간에서 돌고, 끝나면 **좁은 채널로 요약만 돌려준다.** `fork()` 하고 파이프로 결과만 받는 구조다. 부모는 자식의 스택을 들여다보지 않는다.

그런데 **격리되지 않은 자원을 공유하면** OS 수업 첫 주에 나오는 문제가 그대로 나온다. 나는 이 글을 쓰는 기계에서 매일 겪는다. 이 블로그 저장소 하나를 Claude 세션 여러 개가 공유한다.

- 내 커밋을 push 한 직후 `git rev-parse HEAD` 가 **남의 커밋**을 가리킨다. 공유 워킹트리이기 때문이다. → 그래서 내 커밋이 올라갔는지 확인할 때 HEAD를 믿지 않고, `git fetch` 후 `git merge-base --is-ancestor <내SHA> origin/master` 로 본다.
- 동시 push는 하나만 성공하고 나머지는 non-fast-forward로 **거절**된다. 덮어쓰기가 아니라 거절이다. ref 갱신이 원자적이기 때문이다. → 그래서 락을 만들지 않고 **재시도 루프**를 쓴다. `git pull --rebase && git push`.
- 진짜 충돌은 **같은 파일명**을 만들 때뿐이다. → 그래서 커밋 전에 파일명 중복만 확인한다.

이건 AI 지식이 아니다. **원자적 연산이 있으면 락이 필요 없다**는, 그리고 **원자적 연산은 실패를 거절로 돌려준다**는 동시성 지식이다. 이걸 모르면 여기서 나오는 처방은 십중팔구 "세션을 하나만 쓰자"가 된다. 병렬성을 통째로 버리는, 값비싼 오답이다.

### 2.3 Persistence — 컨텍스트 밖의 기억

세 번째 조각. Anthropic이 **structured note-taking (agentic memory)** 이라 부르는 것 — 컨텍스트 윈도우 **바깥의** 파일에 메모를 쓰고 나중에 다시 끌어오는 기법이다.[^ace]

OS로 읽으면 이건 그냥 **영속 계층**이고, 영속 계층에는 늘 같은 질문이 따라붙는다. 무엇을 fsync 할 것인가(= 어떤 사실이 세션을 넘어 살아남아야 하는가). 크래시했을 때 일관적인가(= 컴팩션 직후에도 메모가 말이 되는가). 누가 GC 하는가(= 틀린 메모를 언제 지우는가).

메모를 쓰기만 하고 **지우는 규율이 없는** 에이전트 셋업은, 로그 로테이션 없는 서버와 정확히 같은 방식으로 망가진다.

---

## 3. 비유가 아니라는 증거 — 스펙에 OS 용어가 그대로 있다

여기까지는 "비슷하다"는 얘기로 들릴 수 있다. 그래서 스펙 문서를 직접 편다.

### 증거 ①: MCP stdio 바인딩은 유닉스 프로세스 규율 그 자체다

MCP 2026-07-28 스펙의 stdio 전송 규정이다.[^mcp-stdio]

> The server **MUST NOT write anything to its stdout that is not a valid MCP message.** The client MUST NOT write anything to the server's stdin that is not a valid MCP message.
>
> The server **MAY write UTF-8 strings to stderr** for any logging purposes ... The client ... **SHOULD NOT assume stderr output indicates error conditions.**

MCP 서버를 짜본 사람이 한 번쯤 당하는 사고가 여기 다 있다. **디버그용 `print()` 한 줄이 서버를 죽인다.** stdout은 데이터 채널이지 사람이 보는 화면이 아니기 때문이다. stderr가 로그용이라는 것, 그리고 "stderr에 뭐가 찍혔다고 에러로 단정하지 말라"는 것 — 유닉스 파이프라인을 짜본 사람에겐 새로 배울 게 없는 문장이다.

종료 규정은 더 노골적이다.[^mcp-stdio]

> Closing the input stream to the child process ... On POSIX systems, forced termination typically escalates from **SIGTERM to SIGKILL.** ... Servers SHOULD exit promptly when their standard input is closed or reads return end-of-file. This is the **primary graceful-shutdown signal and the only portable one.**

stdin EOF를 종료 신호로 쓰고, 안 죽으면 SIGTERM, 그래도 안 죽으면 SIGKILL. 2026년 AI 프로토콜 문서인데 읽히는 건 프로세스 관리다.

### 증거 ②: "무상태니까 유실하고 재시도하라" — crash-only 설계

같은 페이지의 비정상 종료 규정.[^mcp-stdio]

> If the server process exits unexpectedly, the client SHOULD restart it. **Because the protocol is stateless, any in-flight requests are simply lost and the client can retry them against the fresh process.**

*상태가 없으니 죽으면 그냥 다시 띄우고 재시도한다.* 별도 복구 경로를 두지 않고 **재시작을 유일한 복구 수단으로 만드는** 설계다. OS·분산 시스템 쪽에서 오래 다뤄온 형태이고, 이게 성립하려면 조건이 하나 붙는다 — **재시도가 안전해야 한다.** 즉 멱등해야 한다.

프로토콜이 무상태를 택한 대가로 **멱등성 책임이 도구 구현자에게 넘어왔다**는 뜻이다. 트랜잭션과 재시도를 다뤄본 사람은 이 문장을 보자마자 "그럼 내 툴은 두 번 불려도 되나?"를 묻는다. 안 물어본 채로 결제 API를 툴로 노출하면 어떻게 되는지도 이미 안다.

### 증거 ③: 1988년 OS 논문의 용어가 2026년 AI 스펙의 섹션 제목이다

MCP 보안 문서를 열면 공격 유형 첫 항목의 제목이 이것이다.[^mcp-sec]

> **Confused Deputy Problem**

출처는 Norm Hardy가 1988년 ACM SIGOPS *Operating Systems Review* 에 실은 세 쪽짜리 글 *The Confused Deputy: (or why capabilities might have been invented)* 다.[^hardy] 사연은 이렇다. Tymshare의 FORTRAN 컴파일러가 통계 파일 `(SYSX)STAT` 에 쓰기 위해 *home files license* 라는 권한을 달고 있었는데, 어떤 사용자가 **디버그 출력 파일 이름으로 과금 파일 `(SYSX)BILL` 을 지정**했다. 컴파일러는 자기 권한으로 그걸 덮어썼다.

Hardy의 진단이 핵심이다.[^hardy]

> The fundamental problem is that the compiler runs with **authority stemming from two sources.** (That's why the compiler is a confused deputy.)
>
> The compiler **serves two masters** and carries some authority from each to perform its respective duties. **It has no way to keep them apart.** ... The compiler **had no way of expressing these intents!**

**두 출처의 권한을 동시에 들고 있으면서 그 둘을 구분할 방법이 없는 대리인.** 이 문장을 오늘의 에이전트에 그대로 옮겨 읽어보라. 에이전트는 (1) 사용자가 위임한 권한과 (2) 자기가 들고 있는 도구·자격증명의 권한을 동시에 갖는다. 그리고 도구가 돌려준 **결과 텍스트 안에 지시문이 섞여 있을 때**, 그게 사용자의 의도인지 외부 데이터인지 구분할 구조적 수단이 없다.

우리가 2026년에 프롬프트 인젝션이라 부르는 것의 **권한 구조**는 1988년에 이미 서술돼 있었다.

그리고 Hardy는 당시의 **처방이 어떻게 실패했는지**까지 적어놨다. 이게 더 값지다.[^hardy]

> The system was modified by providing a new system call to **switch hats** which could be used to select one of its two authorities. **Note the increase in complexity!**

권한을 갈아끼우는 스위치를 하나 더 다는 것. 오늘 툴 권한 설계에서 나오는 처방과 똑같다. "이 툴은 읽기만", "이건 승인 받고", "이건 자동 허용" — 토글이 계속 늘어난다. Hardy는 같은 글에서 접근 제어 목록을 땜질하던 시절을 이렇게 회고한다. *"The last time that I wrote down the requirements for a program to open a file, it required fourteen boolean operators."*[^hardy]

OS 보안을 공부한 사람이 여기서 유리한 이유는 답을 알아서가 아니다. **이 길의 끝이 불리언 열네 개라는 걸 이미 봤기 때문**이다.

---

## 4. 유비가 깨지는 지점 — 여기가 이 글의 본론이다

대응표를 늘어놓는 글은 흔하다. 쓸모는 **어디서 틀리는지**에 있다. OS 직관 중 **반드시 틀리는 것 네 개**를 짚는다.

### ① 축출(eviction)이 무손실이 아니다 — 가장 위험한 착각

OS에서 페이지를 스왑아웃했다가 다시 읽어오면 **내용이 같다.** 가상 메모리의 전제 자체가 무손실이다. 프로그램은 자기 페이지가 디스크에 다녀왔는지 알지 못하고, 알 필요도 없다.

컴팩션은 **손실 압축**이다. Anthropic 문서가 직접 인정한다.[^ace]

> **overly aggressive compaction can result in the loss of subtle but critical context whose importance only becomes apparent later**

이게 결정적 차이다. OS 직관대로라면 "컨텍스트가 차면 알아서 스왑되니 신경 안 써도 된다"가 된다. **정확히 틀린다.** 컴팩션은 요약이고, 요약은 무엇을 버릴지 **모델이 판단**하며, 그 판단은 *나중에야 중요해질 것*을 알아보지 못한다. 마지막 문장이 핵심이다 — 버리는 시점에는 그게 중요한지 알 방법이 없다.

그래서 처방이 OS와 반대 방향이다. OS에서는 메모리 관리를 커널에 맡기는 게 정답이지만, 에이전트에서는 **중요한 사실을 컨텍스트 밖(파일·메모)에 손으로 못 박아두는 것**이 정답이다. 커널을 믿지 말라는 얘기다. 2.3의 structured note-taking이 편의 기능이 아니라 **손실 축출에 대한 방어**인 이유가 이것이다.

### ② 격리를 강제하는 주체가 없다

프로세스 격리는 **하드웨어(MMU)가 강제**한다. 옆 프로세스 메모리를 읽으려 하면 커널이 SIGSEGV를 보낸다. 개발자의 선의와 무관하다.

서브에이전트 격리는 **관례**다. 강제하는 MMU가 없다. 컨텍스트 격리는 진짜지만(서로의 대화를 못 본다), **부수 효과 격리는 아무도 안 해준다.** 둘이 같은 워킹트리에 쓰면 그냥 섞인다. 진짜로 격리하려면 별도 워크트리·별도 디렉터리처럼 **경계를 직접 지어야** 한다.

OS에서 공짜로 받던 것을 여기서는 손으로 만들어야 한다는 것. 이걸 모르면 "서브에이전트니까 알아서 격리되겠지"로 사고를 낸다.

### ③ 결정적이지 않다 — 재현이 안 된다

페이지 폴트는 재현된다. 같은 접근 패턴이면 같은 폴트가 난다. 그래서 프로파일링이 성립하고, 한 번 돌려서 원인을 특정하는 디버깅이 성립한다.

컨텍스트 열화는 재현되지 않는다. 같은 입력, 같은 도구, 다른 결과가 정상이다. **그래서 OS에서 쓰던 디버깅 루프가 그대로 작동하지 않는다.** 한 번 돌려보고 "고쳤다"고 말할 수 없다. 필요한 건 반복 측정과 로그다 — 성능 튜닝보다 **A/B 테스트나 SRE의 SLO**에 가까운 감각이다.

### ④ 스케줄러가 공정성을 보장하지 않는다

OS 스케줄러는 starvation을 막는 걸 목표로 삼는다. 에이전트 오케스트레이션에는 그런 보장이 없다. 작업 하나가 컨텍스트를 다 먹고 나머지를 굶겨도 개입하는 주체가 없다. 예산 상한·스텝 상한은 **직접 넣어야** 하고, 안 넣으면 안 생긴다.

---

## 5. 그래서 실제로 무엇이 달라지나

추상을 걷어내고, OS를 아는 사람이 **실제로 다르게 하는 행동**만 남기면 이 정도다.

1. **컨텍스트를 예산으로 다룬다.** 파일 스무 개를 미리 열지 않고 working set을 만든다.
2. **중요한 사실은 컨텍스트 밖에 못 박는다.** 축출이 손실이라는 걸 알기 때문이다. 그리고 틀린 메모를 지우는 규율까지 둔다.
3. **경계에서 무엇이 오가는지를 센다.** 서브에이전트에 무엇을 넘기고 무엇을 돌려받는지를 설계값으로 본다. 부모가 자식의 스택을 읽으려 들지 않는다.
4. **동시성은 락이 아니라 재시도로 푼다.** 원자적 연산이 실패를 거절로 돌려준다는 걸 알면, 공유 저장소에 세션 여럿을 붙이고도 락 없이 운영된다.
5. **파이프를 오염시키지 않는다.** stdout은 채널, stderr는 로그.
6. **재시도가 안전한지 먼저 묻는다.** 무상태 프로토콜은 재시도를 전제하므로, 툴이 멱등하지 않으면 그 비용은 내가 낸다.
7. **권한의 출처를 둘로 나눠 본다.** 사용자가 위임한 권한과 에이전트가 원래 가진 권한. 섞이는 지점이 사고 지점이다.
8. **멈추는 조건을 직접 넣는다.** 공정성과 종료를 보장해주는 커널은 없다.

여덟 개 중 AI 고유 지식이 필요한 건 1번과 2번뿐이다. 나머지 여섯은 **운영체제 수업의 내용**이다.

---

## 6. 결론 — 상관이 아니라 전이(transfer)다

처음 질문으로 돌아간다. "상관관계가 있느냐"는 측정된 바 없다. 내가 말할 수 있는 건 이것이다.

**AI를 잘 쓰는 일의 어려운 부분은 대체로 모델에 관한 것이 아니라 유한 자원·격리·동시성·영속성·권한에 관한 것이다.** 그리고 그 다섯은 운영체제라는 과목이 다루는 것의 거의 전부다. 그래서 OS 지식은 비유로서가 아니라 **전이 가능한 기술로서** 작동한다.

동시에, **조건 없이 전이되지는 않는다.** 4장의 네 가지 — 손실 축출, 강제되지 않는 격리, 비결정성, 없는 스케줄러 — 를 모르면 OS 지식은 잘못된 확신을 준다. "커널이 알아서 해주겠지"라는 습관이 여기서는 정확히 반대 방향의 오답이다.

그래서 권하고 싶은 문장은 "OS를 공부하면 AI를 잘 쓴다"가 아니라 이쪽이다.

> **에이전트를 운영하다 막혔을 때, 그 문제의 이름이 운영체제 교과서에 이미 있는지 먼저 의심해봐라.** 대개 있다. 그리고 이름을 찾으면 그 분야가 40년간 시도한 해법과 **실패한 해법**까지 딸려 온다.

두 번째가 더 값지다. Hardy가 남긴 게 "confused deputy라는 이름"만이 아니라 **"switch hats를 달았더니 복잡도가 늘었다"는 기록**인 것처럼. 새 분야는 남이 이미 걸어보고 버린 길을 다시 걷느라 시간을 쓴다.

---

## References

[^ace]: Anthropic, *Effective context engineering for AI agents* (2025-09-29). 인용한 "finite resource with diminishing marginal returns", "attention budget", compaction의 정의와 Claude Code 구현(최근 접근 파일 5개), "overly aggressive compaction can result in the loss of subtle but critical context", structured note-taking, 서브에이전트의 1,000–2,000 토큰 요약은 모두 이 문서 본문. <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
[^ostep]: Remzi H. Arpaci-Dusseau & Andrea C. Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Arpaci-Dusseau Books, Version 1.10 (2023-11). 무료 공개본. "three conceptual pieces ... virtualization, concurrency, and persistence"는 공식 페이지 본문. <https://pages.cs.wisc.edu/~remzi/OSTEP/>
[^mcp-stdio]: Model Context Protocol specification 2026-07-28, *Transports — stdio*. stdout/stderr 규정, EOF 기반 정상 종료와 SIGTERM→SIGKILL 에스컬레이션, 비정상 종료 시 in-flight 요청 유실·재시도 규정은 이 페이지 본문. <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio>
[^mcp-sec]: Model Context Protocol specification 2026-07-28, *Security Best Practices*. "Confused Deputy Problem"은 이 문서의 공격 유형 첫 섹션 제목. <https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices>
[^hardy]: Norm Hardy (Senior Architect, Key Logic, Inc.), *The Confused Deputy: (or why capabilities might have been invented)*, ACM SIGOPS Operating Systems Review, Vol. 22, Issue 4 (1988-10), pp. 36–38, DOI [10.1145/54289.871709](https://doi.org/10.1145/54289.871709). 본문 인용은 저자 본인 사이트에 게시된 전문에서 확인했다(ACM 원문 페이지는 자동화된 요청에 403을 반환한다). <http://cap-lore.com/CapTheory/ConfusedDeputy.html>

> **한계 명시.** ① 제목의 "상관관계"에 해당하는 **측정된 연구는 이 글에 없다.** OS 학습 이력과 에이전트 운영 성과를 함께 잰 공개 데이터를 찾지 못했고, 있는 척하지 않았다. 이 글이 제시하는 것은 구조적 대응과 그로부터 바뀌는 판단이다. ② 2.2의 동시성 사례는 이 블로그 저장소를 여러 세션이 공유하며 겪은 **나의 운영 경험**이지 통제된 실험이 아니다. ③ 인용문은 모두 해당 1차 문서 본문에서 확인했으나, 그 문서들이 OS 이론을 **근거로 인용한 것은 아니다.** 여기서 제시한 대응은 양쪽 원문을 나란히 놓고 읽은 결과이며 인과 주장이 아니다. 다만 3장 증거 ③의 confused deputy만은 예외로, MCP 보안 문서가 OS 문헌의 용어를 **그대로 채택**한 경우다.
