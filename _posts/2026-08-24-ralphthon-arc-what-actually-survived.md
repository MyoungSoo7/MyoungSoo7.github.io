---
layout: post
title: "랄프톤의 발전 방향 — 질문은 위로 올라갔는데, 코드는 어디에 남았나"
date: 2026-08-24 00:03:13 +0900
categories: [AI, Agent]
tags: [ralphthon, ralph-loop, harness, ouroboros, oh-my-codex, oh-my-darwin, auto-research, evaluation]
---

이런 요약 이미지를 하나 받았다. 랄프톤(Ralphthon)의 발전 방향을 회차별 질문으로 압축한 그림이다.

![랄프톤 회차별 발전 방향을 정리한 요약 이미지. Seoul #1 은 장시간 코딩 Agent 를 어떻게 안 죽이고 돌릴까(Ouroboros/OMX), Seoul #2 는 Agent 에게 더 고차원적 역할을 어떻게 부여할까(Polysona/자율 SaaS Clone/Hardware Agent), Singapore 는 Harness 자체가 스스로 발전할 수 있을까(oh-my-darwin), ICML 은 코딩을 넘어 연구 전체를 Agent 에게 위임할 수 있을까(AI Scientist/Review Agent). 결론은 Prompt → Context → Harness → Evaluation → Autonomous Loop 를 얼마나 잘 설계했느냐가 핵심이라는 것.](/assets/images/ralphthon-direction-summary.jpg)

그림의 주장은 선명하다. **"어떤 LLM 을 썼나"가 아니라 `Prompt → Context → Harness → Evaluation → Autonomous Loop` 를 얼마나 잘 설계했느냐**가 핵심이라는 것.

이 문장에는 동의한다. 다만 그림은 출처가 붙어 있지 않은 2차 요약이라, 받아쓰기 전에 1차 자료(주최 측 공식 이벤트 페이지, 참가자 본인 회고, GitHub API 실측)로 하나씩 대조했다. 대조해 보니 **그림이 맞은 부분, 압축하면서 흐려진 부분, 그리고 그림이 아예 다루지 않는 더 중요한 사실**이 갈렸다.

---

## 1. 실제 개최 이력

먼저 사실관계. 주최는 개발자 커뮤니티 **Team Attention**(정구봉)이고, 규칙은 어느 회차나 같다 — **랄프 루프가 시작되면 노트북에서 손을 뗀다. 만지려면 빨간 가재 모자를 쓴다.**

| 회차 | 날짜 | 장소 | 주제 / 결과 |
|---|---|---|---|
| Seoul #1 | 2026-02-28 ~ 03-01 | 서울 성북구 숙소 | 9팀 13명. 1등 Ouroboros, 2등 oh-my-codex |
| Seoul #2 + SF | 2026-03-29(서울) / 03-28(SF) | NAVER D2SF 강남 | 서울 1위 Polysona |
| Singapore | 2026-05-17 | Suntec City | Grand Prize oh-my-darwin |
| Busan | — | — | Codex Goal 4개 트랙 |
| ICML | 2026-07-12 | NAVER D2SF 강남 | Auto Research 2트랙 |

주최 측 공식 페이지 기재로, Seoul #1 에서 하룻밤 동안 **501,955줄의 코드와 543개의 커밋**이 에이전트로만 만들어졌다.[^luma2] 우승팀(사이좋은부부, 이재규·정승아)의 본인 회고에 따르면 그중 자기 팀 몫이 10만 줄 이상이고 **7만 줄 이상이 테스트 코드**였다.[^jaegyu] 국내 언론도 같은 수치와 함께 "AI 에이전트 간에 133회의 문답 과정을 거치도록 해 설계의 오류·모호성을 낮춘 게 특징"이라고 전했다.[^sedaily]

ICML 회차는 성격이 한 번 더 바뀐다. 트랙 1 **AI Scientist** 가 논문을 쓰고, 트랙 2 **Review Agent** 가 그 논문을 ICML 리뷰 포맷으로 심사한다.[^lumaicml] 1위는 KAIST 팀 WooandB 의 *Depth-AR* 로, 사람 전문가 11명 패널이 ICML 형식으로 채점했다.[^ddar]

---

## 2. 그림의 주장을 1차 자료와 대조하면

| 그림의 주장 | 1차 자료 확인 |
|---|---|
| Seoul #1 → Ouroboros / OMX | ✅ 공식 페이지에 1등 Ouroboros, 2등 oh-my-codex 로 기재[^luma2] |
| Seoul #2 → Polysona | ✅ 우승자 본인 공개 기록 및 행사 영상[^polysona] |
| Seoul #2 → 자율 SaaS Clone / Hardware Agent | ⚠️ 1차 자료에서 확인 못 함. **하드웨어 의존 사례로 확인되는 건 Seoul #1 우승작**이다 — 주방 고정캠으로 오염도를 측정하고 디스코드 봇이 알리는 시스템[^jaegyu] |
| Singapore → oh-my-darwin | ✅ Grand Prize. `darwin init`(소크라테스식 인터뷰로 검증 가능한 목표 정의) → `darwin meta`(후보 하네스 제안 → 실행 → 점수 → frontier 갱신)[^darwin] |
| ICML → AI Scientist / Review Agent | ✅ 공식 트랙명 그대로[^lumaicml] |

큰 틀은 맞다. 회차가 갈수록 질문이 **"루프를 어떻게 안 죽이나" → "에이전트에 어떤 역할을 주나" → "하네스가 스스로 나아질 수 있나" → "연구 전체를 맡길 수 있나"** 로 한 단계씩 메타로 올라간 건 사실이다.

---

## 3. 그림이 다루지 않은 것 — 살아남은 코드

발전 방향을 "질문이 고차원으로 올라간다"로만 읽으면 놓치는 게 있다. **각 회차의 대표 산출물이 지금 어떤 상태인지**를 GitHub API 로 직접 조회해 봤다. 2026-08-24 기준.

| 리포 | 생성 | 마지막 push | ★ |
|---|---|---|---|
| `Q00/ouroboros` | 2026-01-14 | **2026-08-23** | 5,634 |
| `Yeachan-Heo/oh-my-codex` | 2026-02-02 | **2026-08-23** | 32,811 |
| `clarence-lee-sheng/oh-my-darwin` | 2026-05-17 | 2026-05-19 | 5 |
| `happyhappy-jun/writing-driven-autoresearch` | 2026-07-13 | 2026-07-14 | 18 |
| `happyhappy-jun/depth-ar` | 2026-07-13 | 2026-07-14 | 9 |
| `team-attention/ralphthon-icml` | 2026-07-08 | 2026-07-12 | 8 |

두 가지가 눈에 띈다.

**첫째, 지금도 커밋이 이어지는 둘은 대회에서 태어나지 않았다.** Ouroboros 는 1월 14일, oh-my-codex 는 2월 2일 생성이다. 첫 랄프톤(2월 28일)보다 먼저 존재했고, 대회는 그 하네스의 **시험대**였다. 우승팀 본인도 "최근 제 하네스인 Ouroboros 를 만들고 있었고 이 하네스를 바이브코딩의 극한까지 시험해보고 싶었다"고 적었다.[^jaegyu] 반대로 대회 당일 생성된 리포들은 대회 다음 날~이틀 뒤에 push 가 멈춰 있다.

**둘째, 순위와 스타 수는 관계가 없다.** 싱가포르 대상작 oh-my-darwin 이 별 5개, Seoul #1 준우승작 oh-my-codex 가 별 32,811개다.

공정하게 덧붙이면, 멈춘 게 곧 실패는 아니다. `depth-ar` 와 `writing-driven-autoresearch` 는 README 에서 스스로를 대회의 **run record(기록물)** 로 규정한다 — 논문 1편과 그것을 쓴 하네스, 136개의 타임스탬프 결정 원장을 통째로 남긴 것이 목적이다.[^wooandb] 기록물이 갱신되지 않는 건 정상이다. 또 `pushed_at` 하나로 프로젝트의 생사를 판정할 수도 없다(작업이 다른 리포·비공개 저장소로 옮겨갔을 수 있다).

그래도 방향은 읽힌다. **랄프톤에서 실제로 누적되는 층은 그날 만든 제품이 아니라 하네스다.** 그림의 결론과 같은 말이지만, 그림이 제시한 근거보다 훨씬 단단한 근거가 여기 있다.

---

## 4. 그 사슬은 평평하지 않다

`Prompt → Context → Harness → Evaluation → Autonomous Loop` 를 대등한 5개 항목처럼 나열하면 오해가 생긴다. **Evaluation 은 나머지와 같은 층이 아니라, 루프가 최대화하는 목적함수 그 자체다.**

Ralph 기법의 원작자 Geoffrey Huntley 는 이걸 처음부터 명시했다. 루프는 도구를 실행하고 **그 결과를 평가**해서 컨텍스트에 적재하는 구조이며, 랄프를 다시 자기 자신에게 먹여 평가하게 만들 기회를 늘 찾으라는 것이다.[^ralph] 이걸 정리한 제3자 해설의 표현이 더 직설적이다 — **"완료 판정은 모델 밖에 산다(Completion lives outside the model)."**[^dh]

형식화하면 이렇다. 우리가 실제로 코드로 적어둔 대리 평가를 $\hat v$, 우리가 진짜로 원하는 것을 $v$ 라 하자. 루프가 오래 돌수록 결과물은 이렇게 간다.

$$
x_T \;\xrightarrow[\;T \to \infty\;]{}\; \arg\max_x \hat v(x),
\qquad
\mathrm{Regret} \;=\; v(x^\star) - v\!\left(\arg\max_x \hat v(x)\right)
$$

루프를 더 오래 돌리고 토큰을 더 붓는 건 **왼쪽 수렴에만 작용한다.** $\hat v \ne v$ 에서 오는 Regret 은 한 톨도 줄지 않는다. (개념적 정식화이지 측정값이 아니다.)

랄프톤의 규칙 설계가 흥미로운 건 이 지점이다. **가재 모자는 사람의 개입을 금지하는 장치가 아니라 점수화하는 장치다** — Seoul #2 × SF 회차 공식 영상에서 진행자는 "루프 시작 후 노트북을 만지려면 가재 복장을 입어야 하고, **로브스터 카운트가 점수의 20%**"라고 규칙을 설명한다.[^video] 개입을 세는 순간 "사람이 얼마나 안 붙어도 되는가"가 평가 항목이 된다. ICML 회차가 Review Agent 를 **별도 트랙으로 분리**한 것도 같은 성격의 결정이다. 평가자를 참가작으로 승격시킨 것.

---

## 5. 어젯밤 내가 겪은 $\hat v \ne v$

추상적인 이야기가 아니다. 이 글을 쓰기 몇 시간 전에 겪었다.

운영 중인 서비스의 장면 이미지 5장이 잘못 생성돼 있었다. 프롬프트에 `floating mystically in the air` 라는 구절이 들어 있어서, 소들이 땅에 발을 딛지 않고 공중에 떠 있었다. **모델의 실패가 아니라 스펙의 실패였다.** 프롬프트를 다시 쓰고, 재생성하고, 머지하고, CI 통과, 배포 완료.

여기까지의 내부 신호는 전부 초록이었다. 서버가 실제로 새 파일을 주고 있는 것도 확인했다 — 라이브 5장의 sha256 이 로컬 산출물과 전부 일치.

그런데 사용자 화면에는 **여전히 옛 그림**이 떠 있었다. 응답 헤더가 `cache-control: public, max-age=14400` 이었고, 그 이미지는 CSS `backgroundImage` 로 깔려 있어서 일반 새로고침으로는 재요청조차 가지 않았다.

- 내가 코드로 적어둔 평가 $\hat v$ = "빌드 초록 + 배포 완료 + 서빙 바이트 일치"
- 진짜 목적 $v$ = "**사용자 눈에** 새 그림이 보인다"

세 조건을 다 통과하고도 $v$ 는 거짓이었다. 루프를 백 번 더 돌려도 이건 안 잡힌다. 잡으려면 $\hat v$ 에 **브라우저 캐시를 통과한 관측**이라는 항을 새로 넣어야 한다. 평가함수를 고치는 일은 루프 밖에서, 사람이 한다.

같은 종류의 함정을 전에도 만났다. Docker 가 없으면 통합테스트 클래스가 조용히 스킵되는데도 로컬에선 `BUILD SUCCESSFUL` 이 뜬다. 봐야 할 숫자는 `SUCCESSFUL` 이 아니라 `ignored=0` 이다.

---

## 6. 이 글의 한계

- 원본 요약 이미지는 **출처 미상의 2차 자료**다. 이 글은 그 그림의 주장을 검증한 것이지 인용한 게 아니다.
- 501,955줄·543커밋은 **주최 측이 이벤트 페이지에 기재한 수치**이고, 10만 줄·7만 줄 테스트·133회 문답은 **참가자 본인 진술 및 이를 받은 언론 보도**다. 코드 품질을 재현 가능하게 검증한 중립 제3자 자료는 확인하지 못했다.
- GitHub 지표(★, `pushed_at`)만 2026-08-24 시점에 **내가 API 로 직접 조회한 실측**이다. 이 값들은 시간이 지나면 달라진다.
- 부산 회차는 참가 가이드 페이지로만 확인했고, 수상 결과는 확인하지 못했다.
- 하네스 간 성능 우열에 대한 중립적 head-to-head 비교는 존재하지 않는다. 이 글도 그런 주장을 하지 않는다.

---

## 정리

그림은 맞다. 다만 사슬의 다섯 항목 중 **Evaluation 하나가 나머지 넷의 목적을 정의한다.** 랄프톤의 발전 방향을 회차로 읽으면 "질문이 메타로 올라갔다"이고, 코드로 읽으면 **"대회 전에 태어난 하네스만 대회 후에 살아남았다"**이다. 두 문장은 같은 것을 가리킨다 — 축적되는 자산은 산출물이 아니라, 산출물을 판정하는 장치라는 것.

이 블로그의 관련 글: [Loop Engineering 의 loop 는 cron 인가 ralph 인가](/2026/07/08/loop-engineering-cron-vs-ralph/), [Polysona 코드 리뷰](/2026/08/23/polysona-code-review/), [oh-my-codex 해부](/2026/08/23/oh-my-codex-teardown-and-the-agent-plugins-spec/).

---

## References

[^ralph]: Geoffrey Huntley, ["Ralph Wiggum as a 'software engineer'"](https://ghuntley.com/ralph/), 2025-07-14. Ralph 기법의 원전. 후속 글 ["everything is a ralph loop"](https://ghuntley.com/loop/), 2026-01-17.
[^luma2]: Team Attention, [Ralphthon @Seoul Sponsored by OpenAI (Seoul #2 공식 이벤트 페이지)](https://luma.com/v68q8un9). Seoul #1 의 501,955줄·543커밋 및 1·2등 수상작 기재. Seoul #1 공식 페이지는 [여기](https://luma.com/vacarl0x).
[^jaegyu]: JAEGYU LEE, ["Ralphthon 후기: 10만 줄의 코드, 그리고 진화하는 무한 루프 Ouroboros"](https://kr.linkedin.com/posts/q00_ralphthon-%ED%9B%84%EA%B8%B0-10%EB%A7%8C-%EC%A4%84%EC%9D%98-%EC%BD%94%EB%93%9C-%EA%B7%B8%EB%A6%AC%EA%B3%A0-%EC%A7%84%ED%99%94%ED%95%98%EB%8A%94-%EB%AC%B4%ED%95%9C-%EB%A3%A8%ED%94%84-ouroboros-activity-7434364428847935488-rAqw), 2026-03-02. 우승자 본인 회고. 하네스 저장소: [Q00/ouroboros](https://github.com/Q00/ouroboros).
[^sedaily]: 김지영, ["인간은 자고 AI가 밤새 코딩... AI 에이전트 활용하는 '랄프톤' 한국 상륙"](https://www.sedaily.com/article/20015256), 서울경제, 2026-03-04. 9팀 참가, 10만 줄·테스트 70%·133회 문답 보도. 후원사 확대는 [뉴시스 보도](https://www.newsis.com/view/NISX20260325_0003563813), 2026-03-25.
[^polysona]: Seonmin Lee, [Ralphthon Seoul #2 우승 기록](https://kr.linkedin.com/posts/lilmgenius_%EC%B2%9C%ED%95%98%EC%A0%9C%EC%9D%BC-ai-%EB%8B%A4%EB%A4%84%EA%B2%A8%EB%A3%A8%EA%B8%B0-%EB%8C%80%ED%9A%8C-%EC%9A%B0%EC%8A%B9%ED%95%9C-ssultxt-2026%EB%85%84-3%EC%9B%94-activity-7445243631172739072-wTGx), 2026-04-01.
[^darwin]: [clarence-lee-sheng/oh-my-darwin](https://github.com/clarence-lee-sheng/oh-my-darwin) README. 싱가포르 회차 공식 페이지: [Ralphthon @SG supported by OpenAI](https://luma.com/4hx7p0vs).
[^lumaicml]: Team Attention, [Ralphthon @ICML "Auto Research" supported by Codex](https://luma.com/hjuo7auc). 5번째 회차, 2트랙 구성 및 트랙별 상금 기재. 이벤트용 Codex 스킬 저장소: [team-attention/ralphthon-icml](https://github.com/team-attention/ralphthon-icml). 부산 회차 참가 가이드: [ralphthon.team-attention.com/guide](https://ralphthon.team-attention.com/guide).
[^ddar]: ["AI wrote the paper and AI reviewed it… VESSL AI supports 'Ralphthon' with GPU infrastructure"](https://www.venturesquare.net/en/1099294/), 벤처스퀘어, 2026-07-16. 개최일·트랙 구성·13팀 포스터 진출 보도.
[^wooandb]: Woomin Song & Byungjun Yoon, ["Writing First: How We Designed the Research-Agent Harness That Won Ralphthon@ICML"](https://byungjunyoon.ai/writing-driven-autoresearch/), 2026-07-13. 하네스: [writing-driven-autoresearch](https://github.com/happyhappy-jun/writing-driven-autoresearch), 논문 저장소: [depth-ar](https://github.com/happyhappy-jun/depth-ar).
[^dh]: Ian Hernandez, ["The Ralph Wiggum Loop, from First Principles"](https://www.dreamhost.com/blog/ralph-wiggum/), DreamHost, 2026-02-04. 제3자 해설. 기법의 확산에 대한 언론 보도는 Simon Sharwood, ["'Ralph Wiggum' loop prompts Claude to vibe-clone software"](https://www.theregister.com/2026/01/27/ralph_wiggum_claude_loops/), The Register, 2026-01-27.
[^video]: Team Attention, [Ralphton 2026 SF x Seoul, A New Concept Hackathon with OpenAI](https://www.youtube.com/watch?v=44pS5lRHzl4), 2026-04-21. 행사 영상. 가재 복장 규칙과 "lobster count is 20% of your score" 발언, Seoul #2 1위 발표 포함.
