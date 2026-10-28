---
layout: post
title: "Genie 4 정리 — 소리까지 내는 실시간 월드 모델, 그리고 Gemini 가 '감독' 으로 들어왔다"
date: 2026-10-28 13:44:00 +0900
categories: [AI, Research]
tags: [Google DeepMind, Genie 4, World Model, Gemini, Robotics, SynthID]
---

> 원문: **[Genie 4: A new generation of world simulation](https://deepmind.google/blog/genie-4-a-new-generation-of-world-simulation/)** — Google DeepMind 블로그, 2026-10-27. Raia Hadsell, Diego Rivas, Hang Qi.

Google DeepMind 가 월드 모델 **Genie 4** 를 공개했다. 한 문장으로 줄이면 이렇다.

> 키보드와 문장으로 조종하는 실시간 가상 세계를 만드는데, 이번엔 **소리까지 만들고**, **Gemini 가 장면을 계속 보면서 방향을 잡아 준다.**

아래는 원문 내용을 정리한 것이다. 원문에 없는 수치는 적지 않았다.

## 1. Genie 4 가 뭔가

**월드 모델**은 "다음 화면이 어떻게 될지" 를 생성하는 모델이다. 사용자가 앞으로 걸으면 앞 풍경을, 비를 내리라고 하면 비 오는 장면을 그 자리에서 만들어 낸다. 게임 엔진처럼 미리 만든 맵을 읽는 게 아니라 **매 순간 화면을 생성한다.**

원문이 내세우는 Genie 4 의 새로운 점은 다섯 가지다.

| 영역 | 원문 표현 |
|---|---|
| 사실감 | "enhanced photorealism, fluid movement, and native audio" |
| 물리 | 공기역학·충돌 같은 상황을 시뮬레이션 |
| 사람 | 자연스럽게 움직이고 환경에 반응하며, 실시간으로 조종할 수 있는 인물 |
| 소리 | "our first real-time world model to generate audio natively" — 음악·환경음·대화까지 |
| 실시간 조종 | 날씨·카메라를 바꾸거나 사람·물체를 문장으로 추가. Gemini 가 장면에 맞게 프롬프트를 고쳐 준다 |

## 2. Gemini 와 어떻게 엮이나 — 이번 글의 핵심

이번 발표에서 가장 흥미로운 대목은 Genie 가 **혼자 돌지 않는다**는 점이다.

- **Gemini Omni** 가 시뮬레이션을 실제 세계의 모습과 움직임에 붙잡아 둔다.
- 다른 Gemini 모델이 **추론**을 맡아 장면이 앞뒤가 맞게 이어지도록 한다.
- **Gemini 3.8 Flash** 는 "guiding agent in the loop" 로 들어간다. 목표를 단계로 쪼개고, **프레임을 보면서 각 단계가 됐는지 확인하고**, 세계가 바뀌거나 사용자가 끼어들면 계획을 고친다.
- **Gemini 4 Argon** 과의 실험도 소개한다. 렌더링 중에 Argon 이 다음 단계를 **텍스트 캡션**으로 Genie 에 넘기는 방식이고, 예시로 Apptronik 의 휴머노이드 Apollo 가 체커를 두는 장면이 나온다.

정리하면 **Genie 가 화면을 만들고, Gemini 가 감독처럼 보면서 지시한다.** 생성 모델과 판단 모델을 나눠서 루프로 묶은 구조다. 에이전트 하네스에서 "실행하는 모델" 과 "검증하는 모델" 을 나누는 것과 같은 발상이다.

## 3. Genie 3 와 비교

Genie 4 원문에는 해상도·프레임률·지속 시간 같은 **수치가 없다.** 그래서 직접 수치 비교는 할 수 없다. 대신 [Genie 3 원문](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/)(2025-08-05)이 밝힌 사양과 한계를 옆에 놓으면 무엇이 달라졌는지는 보인다.

| | Genie 3 (2025-08) | Genie 4 (2026-10) |
|---|---|---|
| 해상도·프레임 | 720p, 24fps | **공개 안 함** |
| 일관성 유지 | 몇 분, 시각 기억 약 1분 | 공개 안 함. "긴 세션에선 세부와 물체 영속성이 흐트러질 수 있다" |
| 소리 | 없음 | **네이티브 오디오** (음악·환경음·대화) |
| 세계 조작 | 문장으로 날씨·물체·인물 추가 | 같은 기능 + **Gemini 가 장면에 맞게 프롬프트 보정** |
| 판단 루프 | 언급 없음 | **Gemini 가 프레임을 보며 계획·검증** |
| 텍스트 렌더링 | 입력에 넣은 글자만 대체로 읽힘 | 여전히 연구 과제 |

Genie 3 의 한계 목록과 Genie 4 의 연구 과제 목록을 겹쳐 보면, **글자 렌더링·공간 정확도·장기 일관성**은 두 세대 연속으로 남아 있다.

## 4. 어디에 쓰겠다는 건가

원문이 꼽은 용도:

- **영상 사전 시각화** — 영화 제작자가 여러 테이크를 돌려 보는 "draft mode"
- **역사·아카이브** — 2D 사진 한 장을 시뮬레이션 공간으로 만들거나, 홍수·산불 같은 사건을 재현
- **게임·경험 설계** — 문장 프롬프트로 탐험 가능한 콘셉트 시제품 만들기
- **시뮬레이션** — 기업 파트너가 시나리오를 빠르게 생성하는 용도로 평가 중
- **로봇·에이전트 학습 환경** — [Gemini Robotics](https://deepmind.google/models/gemini-robotics/) 와 연결

로봇 쪽이 특히 중요하다. 실제 로봇으로 실패하며 배우는 건 비싸고 위험하다. 생성된 세계에서 "만약 이러면?" 을 무한히 돌릴 수 있다면 학습 비용이 크게 달라진다. 다만 **물리 상호작용의 정확도가 아직 연구 과제**라는 점(5절)이 그 기대의 상한선이다.

## 5. 한계 — 원문이 직접 꼽은 것

원문은 Genie 4 를 "an early, experimental model" 이라고 부르고, 아래를 진행 중인 연구 영역으로 적었다.

- 복잡한 물리 상호작용
- 실시간 오디오의 정확도
- 읽을 수 있는 글자 렌더링
- 공간 정확도
- 장기 일관성

## 6. 쓸 수 있나 — 접근과 안전

- **지금은 신뢰 테스터 대상 연구 프리뷰**다.
- **"coming soon"**: Google AI Ultra 구독자는 Project Genie 에서, 얼리 액세스 파트너는 Gemini API·Google AI Studio 에서. 원문에 대기자 명단이 걸려 있다.
- 안전: 내부 안전성 테스트를 거쳤고, 다른 Google 모델과 같은 수준의 가드레일을 두며, 생성되는 **모든 영상과 오디오에 [SynthID](https://deepmind.google/models/synthid/) 워터마크**가 들어간다.

## 7. 필자 의견

- **성능 수치를 하나도 공개하지 않았다.** 전작은 720p·24fps·약 1분 기억을 밝혔는데, 이번엔 그런 숫자가 없다. 논문 링크도 없다. "얼마나 좋아졌나" 는 현재로선 데모 영상과 서술로만 판단해야 한다.
- 진짜 변화는 화질보다 **구조**다. 생성(Genie)과 판단(Gemini)을 루프로 묶었고, 그 판단자가 프레임을 직접 보고 검증한다. 월드 모델이 "보기 좋은 영상 생성기" 에서 **에이전트가 연습하는 환경**으로 옮겨 가는 신호로 읽힌다.
- 오디오가 들어간 건 생각보다 크다. 대화하는 인물이 있는 세계는 로봇보다 **사람 상대 에이전트**(안내·교육·게임 NPC) 학습에 더 직접적이다.

## References

- Google DeepMind, *Genie 4: A new generation of world simulation* (2026-10-27): <https://deepmind.google/blog/genie-4-a-new-generation-of-world-simulation/>
- Google DeepMind, *Genie 3: A new frontier for world models* (2025-08-05): <https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/>
- Google DeepMind, Genie 모델 페이지: <https://deepmind.google/models/genie/>
- Google DeepMind, Genie 프롬프트 가이드: <https://deepmind.google/models/genie/prompt-guide/>
- Google DeepMind, Gemini Robotics: <https://deepmind.google/models/gemini-robotics/>
- Google DeepMind, SynthID: <https://deepmind.google/models/synthid/>
