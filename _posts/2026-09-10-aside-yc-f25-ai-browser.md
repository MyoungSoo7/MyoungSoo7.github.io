---
layout: post
title: "Aside (YC F25) — 통합을 버리고 브라우저가 된 AI 에이전트"
date: 2026-09-10 23:20:00 +0900
categories: [tech]
tags: [ai-agent, browser-agent, ycombinator, benchmark, playwright]
---

YC 2025년 가을(F25) 배치에 [Aside](https://www.ycombinator.com/companies/aside)라는 회사가 있다. 한 줄로 줄이면 **"AI 에이전트를 위해 다시 만든 브라우저"** 다.

이 회사가 흥미로운 이유는 제품 자체보다 **주장하는 방식** 에 있다. 벤치마크 1위를 내걸었고, 인터넷이 "trust me bro 아니냐"고 되받자, 실행 데이터를 통째로 깃허브에 올리고 하네스 설계를 공개했다. 그래서 이 글은 두 부분이다. 앞쪽은 이 회사가 무엇을 만들었는가, 뒤쪽은 **그 숫자를 어디까지 믿을 수 있는가** 다. 두 번째가 더 길다.

---

## 1. 사실관계부터

YC 공식 회사 페이지 기준이다.

| 항목 | 값 |
| --- | --- |
| 배치 | Fall 2025 (F25) |
| 설립 | 2024년 |
| 팀 규모 | 5명 |
| 위치 | 샌프란시스코 |
| 담당 파트너 | Andrew Miklas |
| 창업자 | Jun Kim (CEO), Chanhee Lee, Sanghun Lee |

창업자 세 명은 한국계다. YC 프로필에 따르면 Jun Kim 과 Chanhee Lee 는 [Airbridge.io](https://www.airbridge.io/) 의 창립 엔지니어였다. 프로필에 적힌 "$30M ARR" 는 **창업자 본인이 자기 소개란에 쓴 수치** 이고 별도로 검증된 재무 공시가 아니다 — 그대로 인용하되 등급은 낮춰 읽는 게 맞다.

투자 금액은 여러 데이터 애그리게이터가 서로 다른 숫자를 내놓는다(어떤 곳은 총 $500K, 어떤 곳은 $625K). 1차 출처로 확인되지 않으므로 이 글에서는 금액을 단정하지 않는다.

---

## 2. 여섯 번 떨어지고 다섯 번 피벗했다 — 그 흔적이 YC 사이트에 그대로 남아 있다

회사 공식 링크드인 계정에 창업자들이 직접 쓴 문장이 있다.

> "We got rejected by YC 6 times. Pivoted 5 times. At one point, we had $300 left in our account."

이건 자기 서술이라 검증할 방법이 없다. 그런데 **피벗했다는 사실 자체는 1차 출처 두 개를 나란히 놓으면 그냥 보인다.**

- YC **Launch 페이지** ([링크](https://www.ycombinator.com/launches/Oj4-aside-live-answers-for-enterprise-tech-sales)) 는 아직도 이렇게 시작한다: *"Aside listens to your sales calls and surfaces answers from your docs, Slack, and past calls"* — 세일즈 콜 실시간 답변 도구다.
- YC **회사 페이지** ([링크](https://www.ycombinator.com/companies/aside)) 의 현재 한 줄 소개는 이것이다: *"The browser built to do real work for you."*

같은 회사, 같은 사이트, 전혀 다른 제품. B2B 세일즈 코칭 SaaS 로 런치했다가 AI 브라우저로 갈아탄 것이다. 스타트업 피벗을 이렇게 문서로 확인할 수 있는 경우는 흔하지 않아서, 그 자체로 기록해 둘 만하다.

---

## 3. 제품: "통합(integration)을 하지 않는다"가 설계 결정이다

지금 나와 있는 AI 에이전트 대부분은 **API 통합** 위에 서 있다. Gmail 커넥터, Slack 커넥터, Notion 커넥터를 하나씩 붙이고, 붙인 만큼만 할 수 있다.

Aside 의 공식 설명은 정반대다.

> "Unlike agents that depend on integrations, Aside uses the web the way you do."
> — [aside.com](https://aside.com/)

즉 **사람이 쓰는 그 웹사이트를, 사람이 로그인한 그 세션으로** 조작한다. 통합이 없으니 커버리지 문제도 없다는 논리다. 대신 통합이 없으면 따라오는 문제 세 가지를 제품 기능으로 정면 대응한다.

**① 로그인 — 비밀번호를 모델에 보여주지 않는다.**
에이전트가 로그인 화면에서 멈추는 게 이 방식의 최대 난점이다. Aside 는 자체 패스워드 매니저를 붙이고, 자격증명을 **모델의 컨텍스트가 아니라 페이지에 직접 autofill** 한다. 공식 문구로는 *"Credentials are autofilled into websites, not exposed to the agent"* 이고, Secure Enclave 기반 암호화와 접근 감사 로그를 함께 내세운다.

**② 위험한 행동 — 사람 승인 게이트.**
결제, 게시물 작성, 메시지 발송 같은 건 항상 사용자 확인을 기다린다고 명시한다. 에이전트가 실제 계정을 쥐고 움직이는 이상 이건 선택이 아니라 필수 설계다.

**③ 컨텍스트 — 브라우징 히스토리를 로컬 메모리로.**
"이 일은 어느 사이트에서 하는지"를 매번 설명하지 않게, 히스토리를 로컬 임베딩 모델로 자기조직화 메모리로 만든다고 한다. 데이터는 기기에 남고 LLM 제공자에게 공유하지 않는다는 게 공식 입장이다.

여기에 "자기 ChatGPT / Claude 구독이나 API 키를 가져다 쓸 수 있다(BYO subscription)"가 붙는다. 현재 macOS 용으로 배포된다.

---

## 4. 기술적으로 진짜 재미있는 부분: "우리 에이전트는 코딩 에이전트다"

창업자가 쓴 기술 포스트 [*How we built the SOTA browser agent*](https://aside.com/blog/how-we-built-the-sota-browser-agent-that-outperforms-fable) 가 이 회사에서 가장 읽을 값어치 있는 문서다. 핵심 주장 네 개를 요약한다.

### ① 모델의 학습 분포를 거스르지 말 것

> "what data have LLMs seen the most? Code."

그래서 Aside 의 핵심 도구는 단 두 개다 — **JS REPL 과 bash**. 브라우저 전용 툴셋(클릭·타이핑 같은 액션 API)을 정의하는 대신, 에이전트가 **Playwright 문법의 JS 코드를 직접 써서** 브라우저를 몬다. 폼을 채우고, 유튜브 영상을 프레임 단위로 뜯고, 막히면 네트워크 요청을 캡처해 사이트 내부 API 를 역이용하는 동작이 여기서 나온다고 설명한다. 브라우저 제어 문제를 **코드 생성 문제로 환원** 한 셈이다.

Playwright 를 고른 이유도 같다. LLM 이 가장 많이 본 브라우저 자동화 API 라서다. 재미있는 디테일 하나 — 시스템 프롬프트에서 Playwright 사용법을 **가르치지 않는다**. Playwright MCP 가 그 설명에 13K 토큰을 쓰는 동안, Aside 는 *"Playwright is available"* 한 줄만 쓴다고 주장한다.

### ② 지시를 줄이면 똑똑해진다

환각과 멍청한 행동의 원인을 두 가지로 지목한다 — 현재 상태 서술이 부실하거나, 지시가 서로 충돌하거나. 그래서 툴 정의 포함 시스템 프롬프트를 10K 토큰으로 유지한다고 한다(비교 대상으로 Claude Code 20K 를 든다).

여기 인상적인 원칙이 하나 더 있다. **"프롬프트를 AI 에게 쓰게 하지 않는다."** 벤치마크에 대고 자동 리서치를 돌리면 *"When X, do Y"*, *"Never do A, B, C"* 같은 벤치맥싱 규칙이 쏟아지는데, 그게 슬롭 위에 슬롭을 쌓는 짓이라는 것이다.

### ③ 컨텍스트 윈도우를 지킨다

DOM 을 통째로 캡처하면 90% 가 `div` 와 `style` 이다. 그래서 원시 DOM 이나 CDP 대신 **커스텀 접근성(a11y) 트리** 를 쓴다. 최근 유행하는 CDP 직결 방식에 대해서는 "LLM 은 CDP 로 학습되지 않았고, 그건 저수준 디버거 프로토콜이며, 토큰만 먹는다"고 대놓고 반대한다. **추상화 층을 엔지니어 편의가 아니라 모델이 이미 아는 쪽으로 고르라**는 이야기다.

### ④ 결국 Playwright 도 무거워서 다시 만들었다

Playwright 는 E2E 테스트용이라 에이전트에겐 과하다는 판단으로 **Asidewright** 를 만들었다. 인터페이스는 Playwright 와 100% 동일하게 두고(모델에게 익숙해야 하니까), 내부는 CDP 메서드를 얇게 감싼 구현으로 바꿨다.

기반은 `pi-mono/core` 를 골랐고, compaction·skills·hooks·sandbox·REPL·bash·브라우저 자동화는 직접 만들었다고 밝힌다. Codex, Claude Code, OpenCode 등 오픈소스에서 빌려온 것도 있다고 명시한다.

---

## 5. 그래서 그 벤치마크 숫자, 어디까지 믿을 수 있나

여기가 이 글의 본론이다.

### 숫자 자체

Aside 는 세 개 벤치마크에서 1위를 주장한다. 모든 실행 데이터는 [`at-inc/aside-benchmarks`](https://github.com/at-inc/aside-benchmarks) 리포지터리에 MIT 라이선스로 공개돼 있다.

| 벤치마크 | 구성 | Aside 결과 |
| --- | --- | --- |
| Online-Mind2Web | 136개 라이브 사이트, 300개 태스크 | 297/300 = **99.0%** (불가능 태스크 1건 제외 시 99.3%) |
| Odysseys | 실제 브라우징 세션 기반 롱호라이즌 200 태스크 | 완벽 수행 151/200 = **75.5%**, 루브릭 항목 1,050/1,182 = 88.8% |
| BU Bench V1 | 하드 태스크 100개 (WebBench·GAIA·BrowseComp 등) | 93/100 = **93.0%** |

리포의 서술 품질은 솔직히 좋은 편이다. 실패한 3건을 이름까지 적어 뒀다("재고가 없어 구매 불가한 Mac Studio", "Dillard's 가 해당 e기프트카드 디자인을 더 이상 제공하지 않음" 등), 난이도별로 쪼개 놨고(easy 100% / medium 99.3% / hard 97.4%), 실행 설정(모델·thinking·동시성·타임아웃)도 표로 남겼다.

### 그런데 누가 채점했나

같은 리포의 Configuration 표에 답이 있다.

- Online-Mind2Web 실행 — **채점자(Grader): `gpt-5.4` 자동 LLM 채점**
- Odysseys 실행 — **채점자: `gemini-3.1-flash-lite`**

즉 **Aside 가 자기 하네스로 돌리고, 자기가 고른 LLM 채점자로 채점하고, 자기 리포에 올린 결과** 다. 데이터를 공개했다는 점은 분명한 미덕이지만, 공개는 **검증이 아니다.**

그리고 이게 중요한데 — **Online-Mind2Web 에는 별도의 공식 리더보드와 제출·검수 절차가 실제로 존재한다.** 벤치마크를 만든 오하이오 주립대 OSU-NLP-Group 은 [허깅페이스 리더보드](https://huggingface.co/spaces/osunlp/Online_Mind2Web_Leaderboard)를 운영하고, v2 제출 스키마(태스크별 `result.json` + 단계별 스크린샷 궤적)를 요구하며, 자동 평가와 **사람 평가** 두 경로를 두고 있다. Aside 가 이 절차를 거쳐 리더보드에 올랐는지는 이 글을 쓰는 시점에 텍스트로 확인하지 못했다. 확인 못 한 것은 확인 못 했다고 적는 게 맞다.

### 원 논문 제목이 이미 경고다

Online-Mind2Web 을 만든 논문의 제목은 **["An Illusion of Progress? Assessing the Current State of Web Agents"](https://arxiv.org/abs/2504.01382)** (Xue et al., COLM 2025) 다. 이 벤치마크는 **기존 웹 에이전트 벤치마크들이 성능을 과대평가한다** 는 문제의식에서 나왔다. 그 벤치마크에서 99% 가 나왔다면, 축하할 일이기 이전에 **한 번 더 의심해 볼 일** 이라는 뜻이다.

### 라이브 웹이라는 재현성 구멍

이건 Aside 리포가 스스로 적어 놨다.

> "The benchmark tasks were executed against live websites, so outcomes can change as websites update their content, flows, inventory, authentication, or anti-automation behavior."

실제로 벤치마크 관리자 쪽도 사이트가 바뀌면 태스크를 계속 교체한다(2025년 11월에만 CAPTCHA 등의 이유로 36개 교체). 결국 **다른 날 다른 사람이 돌린 점수는 엄밀히는 같은 시험이 아니다.** 이런 벤치마크에서 소수점 몇 %p 차이로 순위를 다투는 건 원래 조심스러워야 한다.

### 비교 대상 숫자는 등급이 또 하나 낮다

Aside 는 경쟁 제품 점수도 같이 제시한다 — Opus 4.8 + Claude Code (Playwright MCP) 84.0%, ChatGPT Atlas 70.0%, Fable 5 조합 80% 등. 그런데 블로그 본문에 **"in our run"** 이라고 명시돼 있다. 즉 **경쟁사가 발표한 수치가 아니라 Aside 가 대신 돌려 본 수치** 다. 상대의 하네스 설정·프롬프트·재시도 정책을 최적으로 맞춰 줬는지 외부에서는 알 수 없다. 창업자 본인도 포스트 안에서 이 지적을 예상하고 *"sorry for the ragebait"* 라고 받는다 — 자기가 비교하는 건 모델이 아니라 **하네스** 라는 해명이다. 타당한 해명이지만, 그렇다고 그 숫자가 중립 비교가 되지는 않는다.

### 정리하면

| 등급 | 내용 |
| --- | --- |
| ① 1차·공식 (사실로 인용 가능) | YC 배치·팀 규모·창업자, 제품 설계 방침, 하네스 아키텍처, 벤치마크 원 논문과 공식 리더보드의 존재 |
| ② 벤더 1차 (라벨 필요) | 99.0% / 93.0% / 75.5% — 자체 실행·자체 LLM 채점, **단 실행 데이터는 공개됨** |
| ③ 중립 제3자 | **부재.** 제3자 하네스로 재현되었거나 감사된 헤드투헤드 비교는 확인되지 않음 |

**면책:** 따라서 "Aside 가 OpenAI·Anthropic 보다 낫다"는 문장은 이 글이 지지하지 않는다. 지지할 근거가 아직 없다. 지금 말할 수 있는 건 *"자사 실행 기준으로 그런 수치를 보고했고, 원본 실행 데이터를 공개했다"* 까지다.

---

## 6. 숫자를 빼고도 남는 것

벤치마크 논쟁을 다 걷어내도, 엔지니어 입장에서 가져갈 게 세 개는 남는다.

1. **추상화는 모델이 아는 쪽으로 고른다.** CDP 대 Playwright 논쟁의 핵심은 "어느 API 가 우수한가"가 아니라 **"어느 API 를 모델이 이미 많이 봤는가"** 다. 사람이 짜는 코드였다면 정반대 결론이 났을 문제다.
2. **컨텍스트는 예산이다.** 프롬프트 10K 대 20K, DOM 대신 a11y 트리, 툴 출력의 신호 대 잡음비 — 전부 같은 이야기다. 토큰을 쓰는 게 아니라 **아끼는 쪽** 에서 성능이 나온다는 주장.
3. **에이전트에 자격증명을 주는 문제는 결국 설계로 푼다.** 모델에게 비밀번호를 안 보여주고 페이지에만 채워 넣기, 위험한 행동 앞 승인 게이트, 접근 감사 로그 — 이건 브라우저 에이전트를 만들 사람이면 누구나 어차피 다시 마주칠 문제다.

세 번째는 특히 남 이야기가 아니다. 로그인된 세션을 그대로 쓰는 에이전트는 **가장 유용한 지점과 가장 위험한 지점이 정확히 같다.** 승인 게이트가 어디에 걸려 있는지가 그래서 스펙시트의 마지막 줄이 아니라 첫 줄이어야 한다.

---

## References

**1차·공식**

- Y Combinator — [Aside 회사 페이지](https://www.ycombinator.com/companies/aside) (배치 F25, 설립 2024, 팀 5명, SF, 파트너 Andrew Miklas)
- Y Combinator — [Launch YC: Aside: Live answers for enterprise tech sales](https://www.ycombinator.com/launches/Oj4-aside-live-answers-for-enterprise-tech-sales) (피벗 이전 제품)
- Aside 공식 사이트 — [aside.com](https://aside.com/) (제품 설계·보안 모델)
- Jun Kim, [*How we built the SOTA browser agent that outperforms Fable*](https://aside.com/blog/how-we-built-the-sota-browser-agent-that-outperforms-fable), 2026-06-25 (하네스 설계)
- Tianci Xue et al., [*An Illusion of Progress? Assessing the Current State of Web Agents*](https://arxiv.org/abs/2504.01382), arXiv:2504.01382, COLM 2025 — Online-Mind2Web 원 논문
- [OSU-NLP-Group/Online-Mind2Web](https://github.com/OSU-NLP-Group/Online-Mind2Web) — 벤치마크 저장소, 제출 스키마 및 태스크 갱신 이력
- [Online-Mind2Web 공식 리더보드](https://huggingface.co/spaces/osunlp/Online_Mind2Web_Leaderboard) (Hugging Face Space)
- Lawrence Keunho Jang et al., *Odysseys: Benchmarking Web Agents on Realistic Long Horizon Tasks*, arXiv:2604.24964 — [저장소](https://github.com/ljang0/Odysseys)
- [browser-use/benchmark](https://github.com/browser-use/benchmark) — BU Bench V1

**벤더 1차 (자체 실행·자체 채점)**

- [at-inc/aside-benchmarks](https://github.com/at-inc/aside-benchmarks) — 벤치마크 실행 원본 데이터, 설정, 채점자 명시

**자기 서술 (검증 불가, 인용 시 등급 하향)**

- Aside 공식 링크드인 계정의 창업자 게시물 (YC 6회 탈락·5회 피벗, Airbridge $30M ARR)

*중립 제3자에 의한 재현·감사 결과는 이 글을 쓰는 시점에 확인되지 않았다.*
