---
layout: post
title: "영상 정리 — 「대 AI 파쿠리 시대: 미친 하네스 REA」: 하네스의 일은 결국 컨텍스트 관리와 암묵지다"
date: 2026-10-26 01:33:34 +0900
categories: [AI, Harness]
tags: [REA, Reverse Engineering, MCP, ReAct, Context Engineering, Subagent, Ghidra, 영상정리]
---

> **원본 영상:** [대 AI 파쿠리 시대: 미친 하네스 REA — 재규의세상 (YouTube)](https://youtu.be/wkjXYbxrnTY)
> <https://youtu.be/wkjXYbxrnTY>
>
> 이 글은 위 영상의 내용을 정리한 것이다. 영상 속 주장과 1차 출처로 확인한 사실을 섞지 않으려고, 영상의 말은 **「영상」**, 공식 문서·논문으로 확인한 것은 출처 링크로 구분했다. REA 자체의 기능·증거 레코드·법적 경계는 앞서 쓴 [역공학 하네스 REA 와 리버스 엔지니어링](https://myoungsoo7.github.io/2026/10/22/rea-reverse-engineering-harness/) 에 정리해 두었으니, 여기서는 **영상이 REA 를 소재로 꺼낸 하네스 이야기**에 집중한다.

## 0. 한 줄 요약

영상의 결론은 이렇다. REA 가 잘 되는 이유는 모델이 똑똑해서가 아니라 **① 베낄 정답(타깃)이 있고, ② MCP 로 컨텍스트를 덜 더럽히며, ③ 리버스 엔지니어링 전문가의 암묵지가 도구 설계에 녹아 있기 때문**이다. 그래서 "AI 가 다 해 준다"가 아니라 **도메인 지식을 가진 사람에게 더 유리한 시대**라는 것.

## 1. REA 가 뭔데 — 영상의 소개와 사실 확인

- 영상: REA(Reverse Engineering)는 "이미 있는 걸 그대로 만드는", 앱을 까서 안을 보는 프레임워크다. 화자가 만든 하네스 Ouroboros(MCP 도구 36개)와 철학이 비슷하다고 소개한다. Ouroboros 는 모호한 요구를 사람에게 되물어 검증 가능한 목표로 바꾸는 쪽이고, REA 는 이미 있는 것을 그대로 복제하는 쪽이라는 대비다.
- 사실: 저장소는 [morluto/rea](https://github.com/morluto/rea), 소개문은 "Reverse engineer anything with agents, from app behavior down to native binaries", 라이선스 MIT, 생성일 2026-04-14. 영상은 스타 수를 "36만"이라고 말하는데, 이 글을 쓰는 2026-10-26 에 GitHub API 로 조회한 값은 **382,948** 이었다. 영상 녹화 시점을 감안하면 대체로 맞는 말이다.
- 사실: 에이전트는 REA 를 **MCP 또는 CLI** 로 호출한다(같은 워크플로). 네이티브 분석은 사용자가 이미 설치한 Hopper·Ghidra·IDA 를 쓰며, REA 가 Ghidra 를 동봉하지는 않는다([README](https://github.com/morluto/rea)). 영상에서도 첫 시도에 "디컴파일러가 없어 의사코드 추출이 어렵다"는 응답이 나오자 Ghidra 를 연결하는 장면이 나온다.

### 왜 "베끼기"를 잘하나 — RLVR 비유

영상은 REA 가 잘 되는 이유를 **RLVR(Reinforcement Learning with Verifiable Rewards)** 로 설명한다. 정답을 기계적으로 확인할 수 있는 과제에서 모델이 강하다는 것이다. 이 용어는 AI2 의 Tülu 3 보고서가 제안했다. 거기서 RLVR 은 수학 정답 일치나 지시 제약 충족처럼 **검증 함수가 참일 때만 보상을 주는** 강화학습이다([Lambert et al., 2024, arXiv:2411.15124](https://arxiv.org/abs/2411.15124)).

다만 이건 비유라는 점을 짚어 둔다. REA 를 쓰는 에이전트가 그 자리에서 강화학습을 하는 건 아니다. 정확한 의미는 "**원본 앱이라는 비교 대상이 있으니 결과를 대조·검증하기 쉽다**"에 가깝다. 영상에서도 에이전트가 원본과 클론의 에셋·픽셀을 비교하며 맞춰 가는 과정을 보여 준다.

## 2. 데모 — Grok 데스크톱 앱 클론과 mini OBS

- 영상: 화자는 Grok 데스크톱 앱의 UX 를 1시간이 안 걸려 거의 똑같이 만들었다고 말한다. 애니메이션과 빠른 패널(Cmd+Shift+Space)까지 재현했다. 내부 모델은 xAI 가 아니라 Claude·Codex SDK 를 썼고, 인증 문제를 피하려고 `claude -p` 헤드리스로 연결했다. 화자 스스로 "파쿠리(베끼기)가 맞다"고 인정한다.
- 영상: 라이브로 Claude 에 REA MCP 를 켜고 "OBS 를 교육 목적으로 클론해 줘"라고 요청한다. Claude 가 REA MCP 를 3번, 셸을 2번 호출한다. 이어 의존성 설치, 디컴파일, 스캐폴딩을 거쳐 녹화 버튼이 있는 **mini OBS** 가 빌드된다. 화자도 "풀 OBS 라고 부르진 않겠다"고 말한다.

## 3. 영상이 설명한 REA 의 4단계 흐름

영상은 Claude 가 실제로 한 일을 뽑아 다음 4단계로 설명한다. 이 4단계는 **영상 화자의 정리**다. README 의 공식 단계 이름은 아니다.

| 단계 | 영상의 설명 | 관련 1차 출처 |
|---|---|---|
| ① 정적 분석 ("X-ray") | 앱을 실행하지 않고 설치 파일·앱 번들을 풀어 구조·CSS·색상·아이콘·에셋을 뽑는다. 보안 장치에 한 번 막히고 재시도한다. | macOS 앱 번들 구조([Apple: Bundle Programming Guide](https://developer.apple.com/library/archive/documentation/CoreFoundation/Conceptual/CFBundles/Introduction/Introduction.html)) |
| ② 실행 중 관찰 | 앱을 켜고 접근성(Accessibility) 기반으로 화면 요소와 동작을 확인한다. | [Apple Accessibility](https://developer.apple.com/documentation/accessibility) |
| ③ 네트워크 분석 | 예전엔 Fiddler·Wireshark 로 손수 했지만, 이제는 "tcpdump 로 트래픽 떠 줘"라고 시키면 된다. | [tcpdump](https://www.tcpdump.org/) |
| ④ 기계 해부 (디컴파일) | 네이티브 바이너리를 Ghidra 로 열어 사람이 읽을 수 있는 함수로 바꾼다. | [Ghidra (NSA)](https://github.com/NationalSecurityAgency/ghidra) |

이렇게 모은 결과로 **청사진**을 만든다. 화면과 코어 사이의 통신 채널, OS 네이티브 기능 사용 여부, **아직 검증되지 않은 부분**이 여기에 표시된다. 빈 곳은 사용자와 대화하며 채운다.

화자가 가장 감탄한 대목은 **검증 못 한 것을 추측으로 메우지 않고 막아 둔다**는 점이었다. 그럴듯하게 지어내는 환각을 구조적으로 막는다는 것이다. 이건 README 와도 맞는다. REA 는 결과를 증거와 한계가 붙은 레코드로 돌려주고, 모르는 것은 모른다고 명시하며, 정적 추론과 런타임 관찰을 구분한다([README](https://github.com/morluto/rea)). 각 도구의 산출물이 **증거(evidence)** 가 되어 다음 단계로 넘어가는 구조라는 영상 설명도 같은 얘기다.

## 4. 본론 — 에이전트 = 모델 + 컨텍스트 + 도구 (ReAct)

영상 후반은 REA 를 넘어 하네스 일반론으로 간다.

- 영상: 에이전트 개념은 1995년에 정의됐다. 지금의 에이전트는 모델(LLM)에 **컨텍스트와 도구**를 붙인 것이다. 화자가 말한 1995년은 Russell & Norvig 의 교과서 *Artificial Intelligence: A Modern Approach* 초판 연도와 맞는다. 이 책은 에이전트를 센서로 환경을 지각하고 액추에이터로 행동하는 존재로 정의한다([AIMA](https://aima.cs.berkeley.edu/)).
- **ReAct** 는 React(프론트엔드 라이브러리)가 아니다. 2022년 논문으로, 모델이 **Thought → Action(도구 호출) → Observation(결과)** 을 번갈아 쌓으며 추론과 행동을 섞는 방식을 제안했다([Yao et al., 2022, arXiv:2210.03629](https://arxiv.org/abs/2210.03629)). 영상의 예는 이렇다. 모델이 "100×100 은 1,000" 이라고 잘못 생각했다가 계산기 도구의 관찰값을 보고 스스로 고친다.
- 영상: 모델은 **도구 설명(description)과 컨텍스트**를 보고 어떤 도구를 쓸지 고른다. 그래서 도구마다 좋은 설명이 필수다. 화자는 하네스가 아무리 발전해도 이 구조는 바뀌지 않을 것이라고 본다. MCP 사양에서도 각 도구는 이름·설명·입력 스키마를 함께 노출한다([MCP Specification — Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)).

## 5. 하네스의 일 = 컨텍스트 관리

영상의 핵심 문장이다. **"하네스란 결국 에이전트 안의 컨텍스트를 관리하는 것, 그리고 도구를 어떻게 쓰고 없으면 어떻게 만들지 관리하는 것. 그 외 역할은 없다."**

### 5-1. 왜 관리해야 하나 — 컨텍스트는 쌓일수록 흐려진다

- 영상: 컨텍스트는 0번부터 쌓이는 배열 같다. 100만 토큰짜리 배열을 통째로 넘기면 모델이 앞쪽 내용을 잊는데, 화자는 이것을 "컨텍스트 오염"이라고 부른다. 80~90% 까지 채운 상태에서 일하는 게 가장 큰 낭비라고도 말한다.
- 1차 연구가 보여 주는 모양은 이것보다 조금 더 미묘하다. *Lost in the Middle* 연구에서는 긴 입력 안의 관련 정보가 **처음이나 끝에 있을 때 성능이 가장 좋았고, 가운데에 있을 때 크게 떨어지는 U자형**이었다([Liu et al., 2023, arXiv:2307.03172](https://arxiv.org/abs/2307.03172)). 그러니 "길수록 0번째를 잊는다"보다는 "**길수록 가운데에 묻힌 것을 놓친다**"가 정확하다. 다만 결론, 곧 길게 채울수록 손해라는 점은 같다.

### 5-2. "스마트 존" — 숫자는 영상과 원 출처가 다르다

- 영상: 매트 포콕(Matt Pocock)은 모델에 "스마트 존"이 있고 **100만 토큰 중 약 20%** 라고 말했다는 것이다. 그래서 200K 를 넘기면 핸드오프하라고 한다. 화자 본인도 화면에서 18% 를 쓰고 있다고 보여 준다.
- 원 출처를 확인하면 숫자가 다르다. 포콕 본인은 *What is the dumb zone?* 영상에서 dumb zone 이 시작되는 지점은 "모델마다, 과제마다 다르고 논쟁적"이라고 전제한다. 그러면서 경험칙으로 **약 150K 토큰**을 제시하고, 6개월 전엔 100K 로 봤으며 점점 올라갈 것이라고 했다([Matt Pocock, YouTube](https://www.youtube.com/watch?v=sOd7svdu_1I)). `/handoff` 소개 영상에서는 체감상 **120K 즈음**부터 dumb zone 이라고 했다([Matt Pocock, YouTube](https://www.youtube.com/watch?v=dtAJ2dOd3ko)). 즉 "20%" 는 영상 화자의 환산이고, 원 출처는 **고정 비율이 아닌 토큰 수 경험칙**이다. 모델이 바뀌면 이 값도 바뀐다.
- 포콕의 대응법은 `/compact`(요약해 같은 세션 계속)와 `/handoff`(필요한 조각만 마크다운으로 뽑아 새 세션에 넘기기)를 구분해 쓰는 것이다(같은 영상).

### 5-3. 관리 수단은 두 가지 — 서브에이전트 vs MCP

영상은 컨텍스트를 아끼는 방법을 둘로 나눈다.

| | 서브에이전트 | MCP |
|---|---|---|
| 방식 | 일을 다른 에이전트에 위임하고, 메인은 **결과와 산출물만** 받는다 | 함수처럼 "이걸 해 줘"를 넘기고 **결과만** 받는다. 안에서 여러 세션을 띄워 병렬로 돌릴 수도 있다 |
| 영상이 본 한계 | 서브에이전트가 많아지면 **돌아온 산출물만으로도** 메인 컨텍스트가 찬다 | 프로토콜이라 입력→출력 경계가 분명하다. 결과가 끝날 때까지 메인을 비워 둘 수 있다 |

Claude Code 문서도 서브에이전트가 **자기만의 컨텍스트 창**에서 일하고 메인에는 결과를 돌려준다고 적는다([Claude Code docs — Subagents](https://code.claude.com/docs/en/sub-agents)). 영상의 요점은 REA 가 디컴파일러·정적 분석기·패키지 분석기 같은 도구를 **MCP 하나로 묶었다**는 것이다. 그래서 Claude 가 한 번 요청하면 도구 사용이 MCP 안에서 처리되고, 메인 컨텍스트는 결과만큼만 찬다. 채팅 참여자의 요약도 같았다. "서브에이전트 대신 MCP 로 컨텍스트가 차는 과정을 통제한다."

### 5-4. goal 기능과 압축(compaction)의 정보 손실

- 영상: 목표(goal)를 계속 저장하는 기능이 있다. 컨텍스트가 차서 **압축이 일어나면 정보 손실이 생기는데**, 이때 저장해 둔 목표로 "아직 목표를 못 이뤘다"고 다시 상기시킨다. 그래서 최신 모델·도구가 아키텍처 문서 같은 산출물을 많이 남기려 한다는 것이다. 산출물로 남겨 두면 잊어도 다시 볼 수 있다.
- 영상: 대화 전체를 하나의 컨텍스트로 끝까지 끌고 가면 "리서치를 했던가?"를 잊는다. 캐시가 깨지는 순간에는 토큰도 크게 빨려 나간다.

## 6. 진짜 차이는 도메인 지식(암묵지)

화자가 가장 힘줘 말한 부분이다.

- 영상: 그냥 "OBS 클론해 줘"라고만 하면 이상한 웹사이트나 Electron 앱, 데모용 프로그램이 나온다. REA 에선 제대로 된 게 나오는데, 그 이유는 리버스 엔지니어링 전문가들의 **암묵지(tacit knowledge)** 가 도구에 녹아 있어서다. 예를 들어 hex·데이터 주소에서 바이트를 디코드하는 "inspect instruction" 같은 도구가 그렇다. 모델은 트랜스포머라서 좋은 토큰(Ghidra 같은 도메인 단서)을 주면 다음 토큰을 잘 추론한다.
- 영상: 보안 분야 사람이라면 REA 의 도구 목록을 뜯어보며 **"이 도구가 왜 들어갔고 어떤 개념이 담겼나"** 를 공부하라고 권한다.
- 영상은 리치 서튼의 **Bitter Lesson** 도 언급한다. 연산이 충분히 커지면 모델이 이런 도메인 지식까지 흡수할 수 있다는 것이다. 서튼의 원문 논지는 장기적으로 사람의 지식을 손으로 넣는 방법보다 **연산을 활용하는 일반적 방법(탐색·학습)** 이 이겨 왔다는 것이다([Sutton, 2019, *The Bitter Lesson*](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)). 화자의 해석은 이렇다. 언젠가는 그렇게 되겠지만 그 시점은 모르고, 그러려면 모델이 매우 비싸질 것이다. 토큰은 싸지고 있지만 도메인 지식은 여전히 필요하므로 **지금은 도메인 전문가에게 유리한 세상**이라는 것.

### "게임 만들기 쉬워졌다"는 말에 대한 반문

- 영상: "동시접속 1만 명을 받아 봤나? 터지면 어떻게 하나?" 채널 라우팅, 동적 채널, 초당 웹소켓 연결 관리, 데이터 전송, 버그 수정과 로그 관리 같은 것들은 **숨겨져 있고**, AI 만으로는 부족하다. "공부는 당신의 몫이고 AI 는 당신의 손"이며, 무엇을 만들지 정의하는 건 여전히 사람의 뇌다. 책임 있는 자리에 서려면 이걸 다 알고 있어야 한다.
- 화자의 최종 정리는 이렇다. 하네스의 관점은 **MCP, 서브에이전트, 컨텍스트 관리, 도구 관리** 넷으로 수렴하고, 앞으로 연구할 건 더 나은 검증과 더 나은 계약을 주는 방법이다.

## 7. 읽고 나서 — 짚어 둘 것

1. **"베끼기"의 범위.** 영상은 "교육 목적"과 "내부 도구"를 전제로 했다. 바이너리를 분석해 **동작을 이해하는 것**과 **코드·에셋을 가져와 배포하는 것**은 법적으로 다르다. 한국 저작권법 제101조의4(프로그램코드역분석)는 호환에 필요한 정보를 얻기 위한 경우 등으로 역분석을 제한적으로 허용한다. 그렇게 얻은 정보를 목적 외로 쓰거나 표현이 유사한 프로그램을 만드는 데 쓰는 것은 금지한다([국가법령정보센터 — 저작권법](https://www.law.go.kr/법령/저작권법)). 아이콘·에셋을 뽑아 그대로 쓰는 것도 같은 문제를 낳는다. 상세는 [앞 글 5장](https://myoungsoo7.github.io/2026/10/22/rea-reverse-engineering-harness/)에 정리했다.
2. **"계정 밴 위험 없다"는 영상 속 발언**은 근거가 제시되지 않았다. 대상 서비스의 이용약관은 각자 확인해야 한다.
3. **숫자 대부분은 영상 속 발언이다.** "1시간 안에 클론", "5년 차 수준" 같은 수치는 화자의 체감이고, 재현 가능한 측정은 제시되지 않았다. 스마트 존 수치는 위 5-2 처럼 원 출처와 다르다.
4. 그럼에도 영상의 핵심 주장, 곧 **하네스의 가치는 모델이 아니라 컨텍스트 경계와 도구 설계(=암묵지)에 있다**는 말은 REA README 의 설계와 맞아떨어진다. 증거 레코드, 모름의 명시, 정적·런타임 분리가 그 예다.

## References

- 재규의세상, 「대 AI 파쿠리 시대: 미친 하네스 REA」, YouTube — <https://youtu.be/wkjXYbxrnTY>
- morluto, *REA — Reverse engineer anything with agents* (GitHub, MIT) — <https://github.com/morluto/rea> / 문서 <https://rea.tools>
- Yao, S. et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv:2210.03629 (ICLR 2023) — <https://arxiv.org/abs/2210.03629>
- Lambert, N. et al. (2024). *Tülu 3: Pushing Frontiers in Open Language Model Post-Training* (RLVR). arXiv:2411.15124 — <https://arxiv.org/abs/2411.15124>
- Liu, N. F. et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts*. arXiv:2307.03172 (TACL 2024) — <https://arxiv.org/abs/2307.03172>
- Russell, S. & Norvig, P. *Artificial Intelligence: A Modern Approach* (1st ed. 1995) — <https://aima.cs.berkeley.edu/>
- Sutton, R. (2019). *The Bitter Lesson* — <http://www.incompleteideas.net/IncIdeas/BitterLesson.html>
- Model Context Protocol, *Specification — Tools* — <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>
- Anthropic, *Claude Code — Subagents* — <https://code.claude.com/docs/en/sub-agents>
- Matt Pocock, *What is the dumb zone?* (YouTube) — <https://www.youtube.com/watch?v=sOd7svdu_1I>
- Matt Pocock, */handoff is my new favourite skill* (YouTube, 2026-05) — <https://www.youtube.com/watch?v=dtAJ2dOd3ko>
- National Security Agency, *Ghidra* — <https://github.com/NationalSecurityAgency/ghidra>
- The Tcpdump Group, *tcpdump* — <https://www.tcpdump.org/>
- Apple, *Accessibility* — <https://developer.apple.com/documentation/accessibility>
- 국가법령정보센터, 「저작권법」 제101조의4 — <https://www.law.go.kr/법령/저작권법>
