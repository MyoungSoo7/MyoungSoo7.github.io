---
layout: post
title: "데미스 허사비스의 지능론 — 체스에서 게임 AI, 노벨 화학상, 그리고 AGI까지"
date: 2026-09-19 14:23:01 +0900
categories: [ai]
tags: [demis-hassabis, deepmind, agi, alphago, alphafold, reinforcement-learning]
---

2024년 노벨 화학상 수상자이자 Google DeepMind CEO 인 데미스 허사비스(Demis Hassabis)는 자신의 경력 전체를 하나의 질문으로 요약한다. **"지능이란 무엇인가, 그리고 그것을 만들 수 있는가."** 그의 이력 — 체스 신동, 게임 개발자, 신경과학자, AI 연구소 창업자, 노벨상 수상자 — 은 겉보기에 산만해 보이지만, 본인 설명에 따르면 전부 이 한 질문을 향한 단계들이다. 이 글은 그가 1차 인터뷰·강연·논문에서 직접 밝힌 내용을 근거로, 체스 → 게임 AI → 노벨 화학상 → AGI 의 네 축으로 그의 지능론을 정리한다.

## 1. 체스 — 지능에 대한 최초의 질문

허사비스는 4살에 체스를 배웠고, 13살에 Elo 2300 으로 마스터 수준에 도달해 잉글랜드 주니어 대표팀들의 주장을 지냈다. 본인이 작성한 공식 이력서에는 "당시 같은 나이대 세계 2위 랭킹"이었다고 적혀 있다.[^cv]

결정적 순간은 체스 실력 자체가 아니라 체스 컴퓨터였다. 노벨재단 공식 인터뷰(2024년 12월 6일, 스톡홀름)에서 그는 이렇게 회고한다:

> "체스 훈련 캠프에서 체스 컴퓨터를 처음 접했다. 누군가 이 무생물 플라스틱 덩어리가 체스를 두도록 프로그래밍했다는 사실에 매료됐다. 오프닝을 연습해야 할 시간에 나는 그 밑에 깔린 프로그램과 AI 에 더 빠져들었다."[^nobel-interview]

그는 체스 상금으로 첫 컴퓨터(ZX Spectrum 48K)를 샀고, 책으로 프로그래밍을 독학해 첫 AI 프로그램(리버시)을 짰다.[^wiki] 같은 인터뷰에서 그는 게임이 자기 경력에서 세 가지 역할을 했다고 정리한다 — **① 어릴 때 자기 자신의 사고를 훈련하는 도구, ② 상업 게임의 AI 를 만드는 첫 직업, ③ DeepMind 에서 AI 시스템을 검증하는 테스트베드.**[^nobel-interview] 그의 지능론의 출발점이 "지능을 관찰하는 것"이 아니라 "지능을 만들어보며 이해하는 것"이었다는 점은 이후 전 경력을 관통한다.

## 2. 게임 AI — 만들어보며 이해한다

17살의 허사비스는 Bullfrog 에서 피터 몰리뉴와 함께 「테마파크」(1994)를 공동 설계·리드 프로그래밍했다. 플레이어가 놀이공원을 설계하면 AI 손님들이 거기에 반응해 매번 다른 게임이 되는 구조로, 천만 장 이상 팔리며 샌드박스 시뮬레이션 장르를 열었다.[^cv] 그는 노벨 인터뷰에서 "사람들이 그 AI 와 상호작용하며 즐거워하는 걸 보고, AI 에 평생을 걸기로 확신했다"고 말한다.[^nobel-interview] 이후 Lionhead 에서 「Black & White」의 리드 AI 프로그래머로 플레이어에게서 학습하는 인공 생명체를 코딩했고, 1998년 자신의 스튜디오 Elixir 를 창업해 BAFTA 후보작 두 편을 냈다.[^cv]

2005년 그는 게임 업계를 떠나 UCL 에서 인지신경과학 박사(해마와 일화기억·상상의 신경 기전)를 한다. 뇌에서 새 AI 알고리즘의 영감을 얻겠다는 명시적 목적이었고, 이 연구는 Science 선정 '2007년 10대 과학 성과'에 들었다.[^cv] 그의 지능론에서 뇌의 위상은 2017년 Neuron 에 공저한 리뷰 논문에 정식화되어 있다: **"인간 뇌는 일반지능이 가능하다는 유일한 존재 증명(existence proof)이다. 다만 생물학적 타당성은 지침이지 요구사항이 아니다 — 공학적으로는 되는 것이 전부다."**[^neuron]

2010년 창업한 DeepMind 는 이 철학의 실행이었다. 회사의 미션 자체가 "지능을 풀고(solve intelligence), 그것으로 다른 모든 것을 푼다"였고, 게임이 실험실이 됐다:

- **DQN (2013 공개, Nature 2015)** — 픽셀 입력만으로 아타리 게임들에서 인간 수준 도달. 심층 강화학습 분야를 연 결과.[^cv]
- **AlphaGo (Nature 2016)** — 2016년 3월 이세돌 9단을 4:1 로 꺾음. 바둑은 경우의 수 때문에 AI 의 성배로 불리던 과제였다.[^alphago]
- **AlphaZero (Science 2018)** — 사전 지식 없이 자가대국만으로 체스·쇼기·바둑을 마스터. 체스 신동이 만든 AI 가 최강 체스 엔진 Stockfish 를 꺾은, 전기(傳記)적으로도 상징적인 결과.[^alphazero]

허사비스는 2016년 MIT 강연에서 자신들의 조작적 정의를 명시했다: **"지능이란 넓은 범위의 과제를 잘 수행하는 능력이다. 우리는 유연성과 일반성을 강조하며, 이런 AI 를 내부적으로 AGI 라 부른다."** 그리고 그 프리즘은 강화학습이었다.[^mit]

## 3. 노벨 화학상 — 게임에서 과학으로

"지능을 풀고, 그것으로 다른 모든 것을 푼다"의 후반부가 단백질 접힘이었다. 아미노산 서열(1차원)에서 단백질의 3차원 구조를 예측하는 문제는 50년 된 생물학의 그랜드 챌린지였다. DeepMind 의 AlphaFold 는 2018년 CASP13 을 이겼고, 2020년 AlphaFold2 가 사실상 문제를 해결한 것으로 평가받았다.[^press]

2024년 10월 9일 스웨덴 왕립과학원은 노벨 화학상의 절반을 "계산적 단백질 설계"로 데이비드 베이커에게, 나머지 절반을 "단백질 구조 예측"으로 허사비스와 존 점퍼에게 공동 수여했다. 공식 보도자료 기준으로 AlphaFold2 는 연구자들이 확인한 약 2억 개 단백질 거의 전부의 구조를 예측했고, 190개국 2백만 명 이상이 사용했다.[^press]

허사비스 본인은 이 상을 지능론의 관점에서 해석한다. 노벨 인터뷰에서: "내가 평생 AI 를 연구한 이유는 AI 가 과학을 위한 궁극의 도구(ultimate tool)가 될 수 있다고 믿었기 때문이다. 처음부터 목표는 단백질 접힘 같은 과학 문제에 적용될 만큼 **일반적인** 알고리즘을 만드는 것이었다."[^nobel-interview] FT 인터뷰에서는 수상 자체를 "AI 가 과학적 발견을 도울 만큼 성숙했다는 것에 대한 분수령(watershed moment)"으로 읽었다.[^ft] 즉 그에게 노벨상은 화학의 업적이기 이전에, 게임에서 벼려낸 일반 학습 시스템이 실제 과학 문제로 전이된다는 자기 이론의 실증이다.

## 4. AGI — 지능론의 종착점

허사비스의 AGI 정의는 20년간 거의 변하지 않았고, 여러 1차 출처에서 동일하게 반복된다:

> "AGI 는 인간이 가진 **모든** 인지 능력을 발휘할 수 있는 시스템이다. 이것이 중요한 이유는, 그런 일반지능이 가능하다는 유일한 기존 증명이 인간 정신이기 때문이다."[^zeit]

이 정의에는 이론적 뿌리가 있다. 그는 뇌를 튜링 머신의 근사로 보고, AGI 를 "일종의 튜링 머신 — 충분히 일반적이어서 어떤 문제·어떤 데이터에도 적용될 수 있는 시스템"으로 규정한다.[^nobel-interview][^daedalus] 그리고 2026년 1월 다보스 대담에서는 지능의 핵심을 한 문장으로 못박았다: **"내게 학습은 지능과 동의어이며, 언제나 그랬다. '일반적'이라는 말은 곧 '일반적 학습'을 뜻한다."**[^bigtech]

같은 대담에서 그는 현 시스템과 AGI 사이의 간극을 구체적으로 나열한다 — 지속 학습(continual learning), 장기 기억, 세계 모델 기반의 장기 계획, 그리고 가장 강조하는 **진짜 창의성**: 기존 추측을 푸는 게 아니라 새로운 추측·가설을 발명하는 능력. "바둑을 세계 챔피언 수준으로 두는 것과 바둑이라는 게임을 발명하는 것은 다르다. 아인슈타인이 당시 가진 정보로 상대성이론을 떠올린 것 같은 일을 시스템이 할 수 있는가."[^bigtech-2025] 그는 AGI 를 마케팅 용어로 쓰는 업계 흐름을 공개적으로 비판하며("AGI 가 상업적 이득을 위한 마케팅 용어가 되어선 안 된다"[^bigtech]), 자신의 도달 전망을 5~10년으로 제시한다 — 이는 본인 예측이며, 업계 내에서도 논쟁적인 주장임을 밝혀둔다.[^bigtech]

## 정리 — 네 단계가 하나의 이론이 되는 방식

그의 지능론을 한 줄로 압축하면 이렇다:

1. **지능은 조작적으로 정의된다** — 넓은 범위의 과제를 잘 수행하는 능력, 핵심은 일반성과 학습.[^mit][^bigtech]
2. **이해의 최고 표현은 구축이다** — "AI 과학은 지능이 무엇인지 탐구하는 것이고, 무언가를 이해했다는 최선의 표현은 그것을 만들어보는 것이다."[^nobel-interview]
3. **뇌는 유일한 존재 증명이다** — 그래서 신경과학이 알고리즘의 영감이자 검증 수단이 된다.[^neuron]
4. **게임은 실험실, 과학은 목적지다** — 체스가 질문을 주었고, 게임 AI 가 방법을 훈련시켰고, AlphaFold 가 전이를 실증했으며, AGI 가 완성형이다.

체스판 앞의 4살 아이가 품은 "이 플라스틱 덩어리가 어떻게 생각하지?"라는 질문이, 40여 년에 걸쳐 노벨상과 AGI 로드맵으로 자란 셈이다. 그의 표현대로 — "30년 전 AI 에 들어올 때의 목표가 지금도 내 목표다."[^nobel-interview]

---

## References

[^nobel-interview]: Nobel Prize Outreach, "Transcript from an interview with Demis Hassabis" (2024-12-06, 스톡홀름 노벨 주간 공식 인터뷰). <https://www.nobelprize.org/prizes/chemistry/2024/hassabis/1924974-interview-transcript/>
[^press]: The Royal Swedish Academy of Sciences, "Press release: The Nobel Prize in Chemistry 2024" (2024-10-09). <https://www.nobelprize.org/prizes/chemistry/2024/press-release/>
[^cv]: Demis Hassabis, Curriculum Vitae (Sep 2023), Pontifical Academy of Sciences 공식 게재본. <https://www.pas.va/content/dam/casinapioiv/pas/pdf-vari/cv_accademici/Demis-Hassabis-CV-2023.pdf>
[^neuron]: Hassabis, D., Kumaran, D., Summerfield, C., Botvinick, M., "Neuroscience-Inspired Artificial Intelligence", *Neuron* 95(2), 245–258 (2017). <https://doi.org/10.1016/j.neuron.2017.06.011>
[^alphago]: Silver, D. et al. (incl. Hassabis, D.), "Mastering the game of Go with deep neural networks and tree search", *Nature* 529, 484–489 (2016). <https://doi.org/10.1038/nature16961>
[^alphazero]: Silver, D. et al. (incl. Hassabis, D.), "A general reinforcement learning algorithm that masters chess, shogi, and Go through self-play", *Science* 362, 1140–1144 (2018). <https://doi.org/10.1126/science.aar6404>
[^mit]: Hassabis, D., "Towards General Artificial Intelligence", MIT CBMM 강연 (2016). <https://www.youtube.com/watch?v=vQXAsdMa_8A>
[^zeit]: DIE ZEIT, "Demis Hassabis: 'I've Been Driven My Whole Life to Build AI as the Ultimate Tool'" (2025-01-29). <https://www.zeit.de/digital/internet/2025-01/demis-hassabis-nobel-prize-artificial-intelligence-deepmind-english>
[^ft]: Financial Times, "Google DeepMind's Demis Hassabis on his Nobel Prize: 'It feels like a watershed moment for AI'" (2024-10-21). <https://www.ft.com/content/72d2c2b1-493b-4520-ae10-41c1a7f3b7e4>
[^bigtech]: Big Technology (Alex Kantrowitz), "Google DeepMind CEO Demis Hassabis on AI's Next Breakthroughs, What Counts As AGI" (2026-01-29, 다보스 라이브 팟캐스트 전문). <https://www.bigtechnology.com/p/google-deepmind-ceo-demis-hassabis-946>
[^bigtech-2025]: Big Technology (Alex Kantrowitz), "Google DeepMind CEO Demis Hassabis: The Path To AGI, LLM Creativity, And Google Smart Glasses" (2025-01-23). <https://www.bigtechnology.com/p/google-deepmind-ceo-demis-hassabis>
[^daedalus]: Hassabis, D. & Manyika, J., "AI as the Ultimate Tool for Science: A Conversation with Demis Hassabis", *Dædalus* (American Academy of Arts and Sciences, 2026). <https://doi.org/10.1162/daed.a.971>
[^wiki]: Wikipedia, "Demis Hassabis" (체스 경력·ZX Spectrum 일화의 보조 출처; 핵심 수치는 위 CV 로 교차 확인). <https://en.wikipedia.org/wiki/Demis_Hassabis>
