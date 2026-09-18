---
layout: post
title: "에이전트 설계를 운영체제 설계 관점으로 읽기 — 1965년 논문이 2026년 하네스를 설명하는 이유"
date: 2026-09-19 03:45:00 +0900
categories: [AI, Architecture]
tags: [AI Agent, Operating System, Harness, Capability, Prompt Injection, Context Engineering, MCP]
---

에이전트를 오래 굴리다 보면 부딪히는 문제 목록이 이상하리만치 비슷해진다.

- 컨텍스트가 넘쳐서 무엇을 버릴지 정해야 한다
- 여러 에이전트가 같은 리소스를 동시에 건드려 서로를 깬다
- 툴에 권한을 얼마나 줘야 할지 모르겠다
- 웹페이지에 적힌 문장을 에이전트가 지시로 착각한다
- "다 했습니다" 라는 보고를 믿을 수 없다

**이 다섯 개는 전부 운영체제가 1960~70년대에 이름을 붙이고 답까지 내놓은 문제다.** 페이지 교체, 상호배제, 최소권한, 혼동된 대리인, 종단 간 논증. 새로 발명할 필요가 없다.

다만 그대로 복사하면 틀리는 지점이 있다. 그래서 이 글은 두 부분이다 — **어디까지 이식되는가**, 그리고 **어디서 깨지는가**. 후자가 더 중요하다.

## 0. 가장 먼저 정할 것 — 커널 자리에 무엇을 앉히나

OS 설계에서 커널이 특별한 이유는 "중요한 일을 해서" 가 아니다. **커널은 모든 요청이 반드시 통과하는 지점이고, 그 판단이 결정론적이라고 신뢰할 수 있기 때문**이다. 이 두 성질이 나머지 모든 보호 메커니즘의 전제가 된다.

여기서 에이전트 설계의 첫 갈림길이 생긴다. LLM 은 두 성질을 **하나도** 만족하지 않는다. 같은 입력에 다른 출력을 내고, 자기 안에 들어온 데이터와 지시를 구조적으로 구분하지 못한다.

그러므로 결론은 하나뿐이다. **LLM 은 커널이 아니라 유저 프로세스다.** 커널 자리에 앉아야 하는 건 하네스 — 툴 호출을 받아 검사하고 실행하고 결과를 돌려주는 결정론적 코드다. 이 배치가 뒤집히면 아래 절의 원칙들이 전부 무의미해진다. "프롬프트에 하지 말라고 써 뒀다" 는 커널이 아니라 **유저 프로세스에게 예의를 부탁한 것**이기 때문이다.

Anthropic 의 엔지니어링 글도 같은 경계를 다른 말로 긋는다 — 코드로 정해진 경로를 따르면 workflow, LLM 이 스스로 경로와 툴 사용을 정하면 agent 이고, "workflows offer predictability and consistency for well-defined tasks" 라고[^anthropic-agents]. 예측 가능성이 필요한 부분을 코드 쪽에 남기라는 얘기다. 커널/유저 구분과 같은 선이다.

## 1. 보호 — 1975년 8원칙은 지금 그대로 쓸 수 있다

Saltzer 와 Schroeder 가 1975년에 정리한 보호 설계 8원칙은, 단어만 바꾸면 에이전트 권한 설계 체크리스트가 된다. 원문을 그대로 놓고 대응시켜 본다.

**Fail-safe defaults** — "Base access decisions on permission rather than exclusion … the default situation is lack of access, and the protection scheme identifies conditions under which access is permitted"[^saltzer75]. 금지 목록을 프롬프트에 나열하는 방식이 바로 저자들이 "wrong psychological base" 라고 부른 쪽이다. 허용 목록을 하네스에 두는 게 맞다.

**Complete mediation** — "Every access to every object must be checked for authority"[^saltzer75]. *every* 가 핵심이다. 툴 호출의 90% 를 게이트로 보내고 나머지를 편의상 우회로로 빼는 순간 mediation 은 성립하지 않는다. 같은 문단은 "a foolproof method of identifying the source of every request must be devised" 라고 덧붙인다 — 이 요청이 사용자에게서 왔는가, 방금 읽은 웹페이지에서 왔는가를 구분할 수 있어야 한다는 요구다. §2 로 이어진다.

**Least privilege** — "Every program and every user of the system should operate using the least set of privileges necessary to complete the job"[^saltzer75]. 서브에이전트에 부모의 전체 권한을 상속시키는 기본 설계는 이 원칙의 정반대다. 읽기만 하는 조사용 에이전트에 쓰기 툴을 주지 않는 것만으로 사고 표면이 크게 줄어든다.

**Least common mechanism** — "Minimize the amount of mechanism common to more than one user and depended on by all users. Every shared mechanism (especially one involving shared variables) represents a potential information path between users"[^saltzer75]. 이게 병렬 에이전트 운영에서 가장 과소평가된 원칙이다. 여러 에이전트가 **같은 git 체크아웃, 같은 API 키, 같은 인덱스** 를 공유하면 그건 편의가 아니라 공유 변수다. 실제로 겪은 사고가 거기서 나왔다 — 같은 리포를 공유하는 세션들에서 `git add` 한 파일을 다른 세션이 `git commit` 으로 함께 삼켜 버리는 일. git 인덱스가 프로세스당 하나가 아니라 **작업 트리당 하나**이기 때문이다. 해법도 OS 적이다. 공유 자원을 줄이거나(에이전트마다 worktree), 원자적 연산을 쓰거나(`git commit --only <경로>`).

**Economy of mechanism** — "Keep the design as simple and small as possible"[^saltzer75]. 저자들이 든 이유가 정확히 에이전트 권한 코드에 들어맞는다 — 잘못된 접근 경로를 만드는 버그는 **정상 사용 중에는 드러나지 않는다**. 정상 사용이 그 경로를 시도하지 않기 때문이다. 권한 로직은 테스트로 커버되기 가장 어려운 코드다. 그래서 작아야 한다.

나머지 셋(**open design**, **separation of privilege**, **psychological acceptability**)도 각각 "권한 규칙을 감추지 말 것", "위험한 작업은 두 개의 독립된 승인을 요구할 것", "승인 UX 가 귀찮으면 사람은 전부 승인해 버린다" 로 바로 읽힌다. 마지막 것은 특히 현실적이다. 확인 프롬프트를 남발하면 사용자는 내용을 안 읽고 누른다 — 그건 보호가 아니라 보호의 외관이다.

## 2. 프롬프트 인젝션의 정확한 고전 이름 — 혼동된 대리인

프롬프트 인젝션을 "SQL 인젝션 같은 것" 이라고 설명하는 걸 자주 보는데, 더 정확한 선조가 따로 있다. 1988년 Norm Hardy 의 **The Confused Deputy** 다[^hardy88].

이야기는 이렇다. Tymshare 의 컴파일러 `(SYSX)FORT` 는 자기 통계 파일 `(SYSX)STAT` 에 쓰기 위해 SYSX 디렉터리 쓰기 권한(home files license)을 갖고 있었다. 어떤 사용자가 디버그 출력 파일 이름으로 **과금 정보 파일 `(SYSX)BILL`** 을 넘겼다. 컴파일러는 그 이름을 그대로 OS 에 전달했고, OS 는 컴파일러의 권한을 보고 허용했다. 과금 정보가 날아갔다[^hardy88].

Hardy 의 진단이 그대로 에이전트에 적용된다 — "The compiler serves two masters and carries some authority from each to perform its respective duties. **It has no way to keep them apart.**"[^hardy88]

에이전트도 두 주인을 섬긴다. 사용자가 부여한 권한, 그리고 방금 읽은 문서·웹페이지·이슈 코멘트가 요청하는 작업. 툴 호출은 둘 다 **같은 권한으로** 나간다. "It has no way to keep them apart" 가 문자 그대로 성립한다.

여기서 중요한 건 Hardy 가 내린 결론이다. 그는 "컴파일러를 더 조심스럽게 만든다" 로 풀지 않았다. 애초에 **파일 이름(designation)과 권한(authority)이 따로 흐르는 구조**가 문제라고 봤고, 둘을 하나로 묶는 capability 를 답으로 제시했다. 실제로 그 시스템에 "모자 바꿔쓰기" 시스템콜을 추가해 봤지만 "Note the increase in complexity!" 라며 권한이 둘을 넘어가는 순간 일반화가 안 됐다고 기록한다[^hardy88].

**에이전트 설계의 교훈도 같다. 모델을 더 조심시키는 방향으로는 안 풀린다.** 풀리는 방향은 구조 쪽이다 — 읽어 온 내용에서 유래한 작업은 사용자 권한으로 실행하지 않는다, 외부 콘텐츠를 읽은 이후의 세션은 권한을 낮춘다(권한 하향은 되돌리지 않는다), 부작용이 있는 툴은 호출의 출처를 확인 가능한 형태로 요구한다. 전부 §1 의 complete mediation 이 요구한 "출처 식별" 이다.

## 3. 컨텍스트는 메모리다 — 문제는 용량이 아니라 교체 정책

컨텍스트 윈도우를 물리 메모리로, 파일시스템과 검색을 보조기억장치로, 컴팩션을 스왑으로 놓으면 대응이 거의 정확하다. 그런데 이 유비에서 실제로 쓸모 있는 부분은 "용량이 모자란다" 가 아니라 **무엇을 남기고 무엇을 버릴지 정하는 문제** 쪽이다.

Denning 이 1968년에 도입한 working set 모델이 그 문제의 이름이다. 그는 프로세스의 working set 을 "the collection of its most recently used pages" 로 정의하고, 그것이 "provides knowledge vital to the dynamic management of paged memories" 라고 했다[^denning68]. 논문의 출발점은 더 날카롭다 — 자원 할당을 제대로 다루지 못하는 근본 이유가 **프로그램 행동에 대한 적절한 모델이 없기 때문**이라는 것[^denning68].

에이전트 컨텍스트 관리가 지금 딱 그 상태다. 요약·압축 기법은 많은데, **"이 작업의 working set 이 무엇인가" 를 정의하지 않고** 압축부터 한다. 그래서 압축률은 좋은데 정작 필요한 걸 버린다. 순서가 반대다. 작업 종류별로 끝까지 붙어 있어야 하는 것(작업 정의, 제약, 지금까지의 결정과 그 근거)과 언제든 다시 불러올 수 있는 것(파일 본문, 로그, 검색 결과)을 먼저 가른 다음, 후자만 버린다.

이 구분을 안 하면 OS 가 부르는 이름 그대로의 증상이 나온다 — **스래싱**. 버렸다가 다시 읽고, 다시 버리고 또 읽는 에이전트. 토큰은 계속 쓰는데 진도가 안 나간다. 컨텍스트를 키워서 푸는 문제가 아니라 교체 정책을 고쳐야 하는 문제다.

부수적으로, "working set 은 참조된 것 중 최근 것" 이라는 정의 자체가 실용적 힌트를 준다. **에이전트가 실제로 다시 참조한 것을 기록**해 두면 교체 정책을 추측이 아니라 관측으로 만들 수 있다.

## 4. 스케줄링과 공유 자원 — 되돌릴 수 없는 작업은 스케줄러로 못 다룬다

에이전트 루프는 스케줄러다. 여러 서브에이전트를 돌리는 오케스트레이터는 더 명백히 그렇다. 그래서 OS 스케줄링의 고민이 그대로 온다 — 기아, 우선순위, 그리고 무엇보다 **공유 자원의 상호배제**.

앞서 든 git 인덱스 사례 말고도 병렬 에이전트는 계속 같은 곳에서 부딪힌다. 같은 브랜치에 push, 같은 API 키의 레이트리밋, 같은 파일의 동시 수정. 전부 교과서적 임계구역 문제이고, 교과서적 해법(자원 분할, 원자적 연산, 재시도)이 그대로 듣는다. 특히 **재시도가 락보다 낫다**는 점은 실측으로도 맞다 — git push 는 ref 갱신이 원자적이라 동시 push 중 하나만 성공하고 나머지는 거절되므로, 별도의 락 없이 `pull --rebase` 후 재시도만으로 안전하다.

그런데 여기서 **유비가 처음으로 크게 깨진다.**

OS 는 최악의 경우 프로세스를 죽여서 자원을 회수한다. 선점(preemption)은 OS 자원 관리의 근간이다. 메모리도, CPU 도, 파일 핸들도 되찾을 수 있다.

**에이전트가 이미 보낸 메일은 되찾을 수 없다.** 이미 머지된 PR, 이미 배포된 변경, 이미 삭제된 데이터도 마찬가지다. 즉 **비가역적 작업은 스케줄링 문제가 아니라 승인 문제다.** 선점이 불가능한 자원은 애초에 할당하지 않는 방식으로만 관리된다. 그래서 이런 작업은 "잘 조율한다" 가 아니라 "실행 전에 사람의 게이트를 통과한다" 로 다뤄야 한다. 리트라이·타임아웃·롤백 같은 스케줄러 도구가 여기서는 전부 무력하다.

## 5. 하네스에 무엇을 넣을 것인가 — 마이크로커널의 최소성 원칙

하네스를 만들다 보면 필연적으로 "이건 코드로 넣을까, 프롬프트로 시킬까" 를 매번 고민하게 된다. 이 질문에 Liedtke 가 1995년에 준 답이 있다.

마이크로커널의 **최소성 원칙**은 대략 이렇다 — 어떤 개념을 커널 밖으로 옮겼을 때 시스템이 요구하는 기능을 구현할 수 없게 된다면, 그때만 그 개념을 커널 안에 둔다[^liedtke95]. 뒤집으면 **밖에서 구현 가능한 건 전부 밖으로 뺀다**는 뜻이다.

에이전트 하네스에 그대로 옮기면 판정 기준이 생긴다.

- **프롬프트/스킬로 표현할 수 있는 것은 코드로 넣지 않는다.** 작업 순서, 문서 형식, 톤, 도메인 지식 — 바깥에 두면 고치기 쉽고 버전 관리도 된다.
- **프롬프트로는 보장할 수 없는 것만 코드로 넣는다.** 권한 검사, 감사 로그, 원자성, 레이트리밋, 확인 게이트. 이것들은 "모델이 잊지 않기" 에 걸면 보장이 아니다.

Liedtke 의 논문이 실제로 논증한 건 "마이크로커널이 느리다" 는 통념이 아이디어의 문제가 아니라 구현의 문제였다는 점이다[^liedtke95]. 하네스에도 같은 오해가 있다 — 게이트를 많이 두면 느려진다는. 느려지는 건 게이트가 **사람을 매번 부를 때**이지, 결정론적 검사를 코드로 도는 비용은 LLM 호출 한 번 앞에서 반올림 오차다.

## 6. 검증은 종단에서 — end-to-end argument

에이전트가 "테스트 통과했습니다", "배포 완료했습니다" 라고 보고한다. 이걸 얼마나 믿을 것인가. 1984년 Saltzer·Reed·Clark 의 답이 그대로 쓰인다.

> "The function in question can completely and correctly be implemented only with the knowledge and help of the application standing at the end points of the communication system. Therefore, providing that questioned function as a feature of the communication system itself is not possible."[^e2e84]

중간 계층의 보증은 **불완전한 버전**일 뿐이라는 얘기다. 에이전트의 자기 보고가 정확히 중간 계층의 보증이다. 모델은 자기가 무엇을 했다고 *믿는지* 를 말할 수 있을 뿐, 시스템의 최종 상태를 알지 못한다.

그래서 검증은 종단에서 해야 한다. 이 블로그의 발행 절차가 그 원칙을 구체화한 예다 — 커밋과 push 가 성공했다고 발행을 주장하지 않고, 실제 퍼머링크에 `curl` 로 HTTP 200 을 받고 **본문에만 있는 문구를 `grep` 으로 세어** 확인한 다음에야 URL 을 회신한다. 중간 신호(빌드 성공)가 초록인데 종단(사이트)에 글이 없는 경우를 실제로 여러 번 겪었기 때문이다.

일반화하면 규칙 하나가 된다. **자기 자신이 성공을 선언하는 구성요소를 성공의 근거로 삼지 않는다.** 테스트는 CI 의 exit code 로, 배포는 외부 도메인의 응답으로, 데이터 변경은 다시 조회해서 확인한다.

## 7. MCP 는 시스템콜이 아니라 드라이버 모델에 가깝다

툴 호출을 시스템콜에 비유하는 건 절반만 맞다. 시스템콜은 **커널이 정의한 고정된 인터페이스**다. 반면 MCP 는 호스트·클라이언트·서버 구조에 JSON-RPC 2.0 을 쓰고 **capability negotiation** 을 하며, 명시적으로 Language Server Protocol 에서 영감을 받았다고 밝힌다[^mcp-spec]. 커널이 무엇이 있는지 미리 아는 게 아니라, **연결 시점에 서로 무엇을 제공하는지 협상한다.**

그건 시스템콜보다 **로더블 커널 모듈 / 드라이버** 에 가깝다. 그리고 그 비유를 받아들이면 따라오는 함의도 같다.

- 드라이버는 **커널 권한으로 실행된다.** MCP 서버를 붙이는 건 라이브러리 추가가 아니라 신뢰 경계를 넓히는 일이다. 스펙 자체도 "arbitrary data access and code execution paths" 를 가능하게 한다고 보안 절 첫 줄에 적는다[^mcp-spec].
- 드라이버 품질이 시스템 안정성을 지배한다. 툴 설명(description)이 모호하면 모델이 잘못 부른다 — 드라이버의 잘못된 문서가 호출자를 오작동시키는 것과 같다.
- 그래서 **드라이버 서명에 해당하는 절차**가 필요하다. 어떤 MCP 서버를 어떤 권한으로 붙일지는 코드 리뷰와 같은 급으로 다뤄야 한다.

## 8. 유비가 깨지는 네 지점

여기까지가 이식되는 부분이고, 아래는 그대로 옮기면 틀리는 부분이다. 이쪽이 더 중요하다.

**① 시스템콜은 결정론적이고 툴 호출은 아니다.** OS 의 보호 모델은 "같은 요청에 같은 판정" 위에 서 있다. 에이전트는 같은 상황에서 다른 툴을 부를 수 있다. 그래서 **정책을 모델 쪽에 두면 그 정책은 확률적으로만 지켜진다.** 하네스로 내려야 하는 이유가 이것이다.

**② 명령과 데이터가 같은 채널에 있다.** 이게 가장 깊은 차이다. 현대 OS 는 실행 권한과 쓰기 권한을 분리해 데이터를 코드로 실행하지 못하게 막는다. 반면 LLM 의 컨텍스트에는 **시스템 프롬프트와 읽어 온 웹페이지가 같은 토큰 열로** 들어간다. 구조적으로 W^X 가 성립하지 않는다. 그래서 분리는 모델 안에서 할 수 없고 **모델 바깥에서** — 출처별 권한, 읽기 이후 권한 하향, 부작용 툴의 별도 승인 — 해야 한다.

**③ 프로세스는 자기 코드를 안 바꾸지만 에이전트는 바꾼다.** 스킬·프롬프트·메모리를 에이전트 자신이 고친다. OS 유비에는 대응물이 없다. 굳이 찾자면 자기수정 코드이고, OS 가 그걸 막아 온 이유가 정확히 "검증 불가능해서" 다. 실무적으로는 **에이전트가 쓰는 설정을 버전 관리 아래 두고 변경을 리뷰 대상으로** 만드는 것 말고 방법이 없다.

**④ 선점이 불가능하다.** §4 에서 본 그대로. 되돌릴 수 없는 작업에는 스케줄러의 도구가 듣지 않는다.

## 9. 정리 — 설계 체크리스트

1. **커널은 하네스다.** LLM 은 유저 프로세스다. 이 배치가 뒤집히면 나머지가 다 무너진다.
2. **기본은 거부**(fail-safe defaults). 금지 목록이 아니라 허용 목록.
3. **예외 없는 중재**(complete mediation). 90% 만 거치는 게이트는 게이트가 아니다.
4. **요청의 출처를 식별한다.** 사용자에게서 왔는가, 읽어 온 콘텐츠에서 왔는가. 혼동된 대리인을 막는 유일한 구조적 수단.
5. **최소 권한 + 공유 자원 최소화.** 서브에이전트는 필요한 툴만. 공유 체크아웃·공유 키는 공유 변수다.
6. **working set 을 먼저 정의하고 그다음에 압축한다.** 순서가 반대면 필요한 걸 버린다.
7. **커널에는 프롬프트로 보장 못 하는 것만 넣는다.** 나머지는 전부 바깥으로.
8. **검증은 종단에서.** 자기 성공을 선언하는 구성요소를 근거로 삼지 않는다.
9. **비가역 작업은 스케줄링이 아니라 승인 문제로 다룬다.**

## 근거의 한계

- 이 글은 **비교 실험이 아니라 개념 대응**이다. "OS 원칙을 적용한 에이전트가 더 낫다" 는 정량적 주장은 하지 않았다. 인용한 OS 논문들은 각자의 맥락에서 검증된 것이고, 에이전트 쪽으로의 대응은 **저자의 해석**이다. §8 을 넣은 이유가 그 해석의 유효 범위를 스스로 좁히기 위해서다.
- OS 쪽 근거는 전부 1차 문헌(원 논문)이고 인용문은 원문에서 직접 확인했다. 에이전트 쪽 근거는 **벤더 1차 자료**(Anthropic 엔지니어링 블로그, MCP 스펙)이며, 중립 제3자의 검증 자료는 아니다 — 개념 정의와 프로토콜 사실관계에 한해 인용했다.
- 본문에 든 운영 사례(공유 git 체크아웃의 인덱스 충돌, 빌드 성공인데 사이트에 글이 없던 경우)는 **저자 환경의 단일 사례**이지 일반화된 통계가 아니다.

## References

[^saltzer75]: J. H. Saltzer and M. D. Schroeder, "The Protection of Information in Computer Systems," *Proceedings of the IEEE* 63(9), 1975. 원문 HTML: <https://web.mit.edu/Saltzer/www/publications/protection/Basic.html>
[^hardy88]: N. Hardy, "The Confused Deputy (or why capabilities might have been invented)," *ACM SIGOPS Operating Systems Review* 22(4), Oct. 1988, pp. 36–38. <https://doi.org/10.1145/54289.871709> · 전문: <https://css.csail.mit.edu/6.858/2012/readings/confused-deputy.html>
[^denning68]: P. J. Denning, "The Working Set Model for Program Behavior," *Communications of the ACM* 11(5), 1968, pp. 323–333. <https://denninginstitute.com/pjd/PUBS/WSModel_1968.pdf>
[^e2e84]: J. H. Saltzer, D. P. Reed, and D. D. Clark, "End-to-End Arguments in System Design," *ACM Transactions on Computer Systems* 2(4), 1984. 원문: <https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.txt>
[^liedtke95]: J. Liedtke, "On µ-Kernel Construction," *Proceedings of the 15th ACM Symposium on Operating Systems Principles (SOSP '95)*, Dec. 1995, pp. 237–250. <https://doi.org/10.1145/224056.224075>
[^anthropic-agents]: Anthropic, "Building effective agents," Dec. 19, 2024. <https://www.anthropic.com/engineering/building-effective-agents> (벤더 1차 자료)
[^mcp-spec]: Model Context Protocol, *Specification* (2025-06-18). <https://modelcontextprotocol.io/specification/2025-06-18> (프로토콜 1차 스펙)
