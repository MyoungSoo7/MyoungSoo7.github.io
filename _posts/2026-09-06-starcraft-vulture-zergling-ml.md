---
layout: post
title: "스타크래프트 벌처로 저글링 잡기: 머신러닝으로 배우는 카이팅과 미세 조작"
date: 2026-09-06 15:57:53 +0900
categories: [Machine Learning]
tags: [StarCraft, BWAPI, Reinforcement Learning, Machine Learning, Micromanagement, Vulture, Zergling]
---

# 스타크래프트 벌처로 저글링 잡기 머신러닝

스타크래프트 브루드워에서 벌처 한 기로 저글링을 상대하는 장면은 머신러닝 문제로 바꾸기 좋다. 벌처는 빠르고 사거리가 있지만 체력이 높지 않고, 저글링은 근접 거리에서 여러 마리가 동시에 공격한다. 벌처가 공격 직후 다시 이동하고, 저글링과의 거리를 유지하며, 위험한 위치를 피하는 짧은 의사결정이 반복된다.

이 문제는 단순한 “적을 클릭하면 이긴다”가 아니다. 제한된 관측 정보에서 매 프레임 또는 일정한 의사결정 간격마다 이동·공격·정지·지뢰 설치를 선택해야 하는 **부분 관측 순차 의사결정 문제**다. BWAPI는 기본적으로 AI 모듈에 게임에서 보이는 상태만 제공하고, 안개 속 유닛 정보는 숨긴다.[1]

이 글에서는 실제 게임을 자동 플레이했다고 주장하지 않고, BWAPI 기반 환경에서 벌처-저글링 마이크로를 학습시키는 설계와 실험 방법을 정리한다.

## 1. 왜 벌처 대 저글링인가

벌처는 테란 Factory에서 생산되는 지상 유닛이다. 참고 데이터 기준으로 체력 80, 지상 공격력 20, 사거리 5, 기본 속도 6.40이며 Ion Thrusters 연구 후 속도가 9.60으로 증가한다.[2]

저글링은 빠르게 접근해 근접 공격을 시도하므로 벌처가 제자리에서 공격만 하면 포위될 위험이 커진다. 따라서 핵심은 다음의 반복이다.

```text
관측 → 목표 선택 → 사격 가능 여부 확인
      → 공격 → 후퇴 이동 → 거리 재평가
      → 필요하면 지뢰 설치 → 반복
```

벌처가 유리한 이유는 단순히 공격력이 높아서가 아니다.

- 저글링이 접근하기 전에 사격할 수 있다.
- 속도 업그레이드로 거리를 다시 만들 수 있다.
- 공격 후 이동으로 접근 시간을 늘릴 수 있다.
- Spider Mine을 이동 경로 제어와 지역 거부에 사용할 수 있다.

반대로 저글링 수가 많아지거나 지형이 좁아지면 벌처가 이동할 공간이 사라지고, 작은 실수의 비용이 커진다.

## 2. 규칙 기반 baseline부터 시작한다

머신러닝을 바로 적용하지 말고 먼저 사람이 이해할 수 있는 규칙 기반 baseline을 만든다.

```text
if 저글링이 공격 사거리 안에 있고 공격 가능:
    가장 가까운 저글링에게 공격
else if 저글링과의 최소 거리가 위험 거리보다 작음:
    가장 먼 안전 지점으로 이동
else:
    저글링의 진행 방향 반대쪽으로 이동
```

더 구체적인 baseline은 다음과 같다.

1. 가장 가까운 저글링을 선택한다.
2. 벌처의 공격 쿨다운이 끝났고 사거리 안이면 공격한다.
3. 공격 명령 직후에는 저글링 군집에서 멀어지는 방향으로 이동한다.
4. 이동 가능한 공간이 부족하면 지형 반대편이나 choke 방향으로 재배치한다.
5. 지뢰가 있으면 저글링의 예상 접근 경로에 설치한다.

이 baseline은 최종 AI가 아니라 비교 기준이다. 학습된 정책이 baseline보다 승률·생존시간·피해량에서 나아졌는지 판단하려면 반드시 필요하다.

## 3. 상태(state) 설계

강화학습 정책에 화면 전체 픽셀을 바로 넣을 수도 있지만, 첫 실험에서는 구조화된 상태 표현이 효율적이다. 관련 연구도 StarCraft 마이크로에서 큰 상태 공간의 복잡성을 줄이기 위해 효율적인 상태 표현을 정의했다.[4]

### 벌처 상태

- 위치 `x, y`
- 체력
- 공격 쿨다운
- 이동 속도 업그레이드 여부
- Spider Mine 연구 여부
- 남은 지뢰 수
- 현재 이동 방향
- 현재 명령과 명령 지속 시간

### 저글링 군집 상태

각 저글링에 대해 다음을 관측한다.

- 상대 위치
- 거리와 방향
- 체력
- 이동 방향
- 공격 가능 상태
- 벌처를 추적 중인지 여부

저글링 수가 가변적이면 고정된 수만 받지 말고 다음 방식 중 하나를 선택한다.

- 가장 가까운 N마리 정렬
- 거리 구간별 히스토그램
- 군집 중심·분산·최소 거리·포위 정도 요약
- attention/set encoder

### 지형 상태

- 벽과 choke point
- 이동 가능한 셀
- 장애물까지의 거리
- 지뢰 위치
- 화면 경계와 탈출 경로

지형을 빼면 정책이 빈 공간에서만 잘 움직이고, 실제 맵의 벽·언덕·좁은 길에서 무너질 수 있다.

## 4. 행동(action) 설계

행동을 너무 세밀하게 만들면 탐색 공간이 커지고, 너무 추상적으로 만들면 좋은 마이크로를 표현할 수 없다.

### 이산 행동 예시

```text
MOVE_N
MOVE_NE
MOVE_E
MOVE_SE
MOVE_S
MOVE_SW
MOVE_W
MOVE_NW
ATTACK_NEAREST
ATTACK_LOW_HP
RETREAT
PLANT_MINE
HOLD
```

### 더 좋은 계층형 행동

상위 정책이 의도를 결정하고 하위 controller가 실제 좌표를 계산하게 할 수 있다.

```text
상위 정책: ATTACK / RETREAT / REPOSITION / MINE
하위 제어: 목표점 계산, 이동 벡터, 공격 target, 명령 빈도
```

실제 게임 API에 매 프레임 명령을 계속 보내면 명령 thrashing이 발생할 수 있다. 따라서 행동 간 최소 지속시간, 명령 cooldown, 같은 명령 반복 억제를 둔다.

BWAPI는 개별 유닛을 제어하고 게임 상태를 읽으며 replay를 frame 단위로 분석할 수 있는 C++ 프레임워크다.[1] 이 API 경계에서는 “학습 정책의 출력”과 “게임에 실제로 보낸 명령”을 구분해 기록해야 한다.

## 5. 보상(reward) 설계

목표는 저글링을 많이 죽이는 것이 아니라, 제한된 시간 안에 효율적으로 생존하며 교전하는 것이다.

예시 보상:

```text
+ 1.0  저글링 처치
+ 0.1  벌처가 공격 가능한 거리 유지
- 0.2  벌처 체력 감소 비율
- 1.0  벌처 사망
- 0.1  위험 거리에서 장시간 정지
+ 0.2  지뢰가 접근 경로를 차단
- 0.05 불필요한 명령 변경
+ 5.0  제한 시간 종료까지 생존
```

보상 설계에서 주의할 점:

- 처치 수만 보상하면 무리한 추격을 배울 수 있다.
- 생존만 보상하면 계속 도망만 다닐 수 있다.
- 이동 거리만 보상하면 저글링을 공격하지 않고 빙빙 돌 수 있다.
- 지뢰 설치만 보상하면 지뢰를 낭비할 수 있다.

따라서 생존·피해·거리·목표 달성·명령 효율을 함께 평가하되, 보상 항목의 비중을 실험으로 조정해야 한다.

## 6. 학습 방법 선택

### 지도학습: 전문가 replay 모방

사람이 벌처를 조작한 replay나 규칙 기반 controller의 행동을 데이터로 수집해 다음 행동을 예측하게 한다.

```text
입력: 현재 상태 + 최근 상태 이력
출력: 이동 방향 / 공격 target / 지뢰 설치
```

장점:

- 초기 학습이 빠르다.
- 사람이 이해하기 쉬운 행동을 시작점으로 삼는다.
- 탐색 중 벌처가 너무 빨리 죽는 문제를 줄인다.

단점:

- 전문가가 경험하지 못한 상황에 약하다.
- 잘못된 행동도 그대로 모방한다.
- 최적 정책보다 인간 습관을 학습할 수 있다.

### 강화학습

환경이 상태를 관측하고 정책이 행동을 내리면 환경은 다음 상태와 보상을 반환한다.

```text
s_t → policy → a_t → StarCraft/BWAPI
                         │
              s_(t+1), reward, done
```

관련 연구는 여러 StarCraft 유닛을 제어하는 강화학습에서 parameter sharing multi-agent 방식과 move·attack 균형 보상, curriculum transfer를 사용했다.[4]

이 문제에서는 처음부터 여러 벌처를 학습하기보다 다음 순서가 안정적이다.

1. 빈 공간에서 이동 제어
2. 저글링 1마리 회피·공격
3. 저글링 2~3마리
4. 속도 업그레이드와 지형 추가
5. 지뢰 사용 추가
6. 저글링 수와 시작 위치 랜덤화
7. 새로운 맵과 미지의 패턴 평가

### Self-play와 curriculum

상대 저글링의 수·속도·시작 위치를 점진적으로 어렵게 만든다. 한 번에 20마리를 넣으면 정책이 학습 전에 죽어버릴 수 있다.

- Level 1: 벌처 1 vs 저글링 1
- Level 2: 벌처 1 vs 저글링 2
- Level 3: 벌처 1 vs 저글링 4
- Level 4: 지형과 choke 추가
- Level 5: 지뢰·속도 업그레이드
- Level 6: 복수 벌처와 여러 방향 접근

## 7. 실험 환경과 안전한 실행 구조

```text
Python trainer
  ├─ 정책 모델
  ├─ replay buffer
  └─ 평가 리포트
          │
          ▼
환경 adapter
  ├─ mock simulator: 빠른 학습
  ├─ BWAPI adapter: 실제 프레임·명령
  └─ replay analyzer: 사후 평가
          │
          ▼
StarCraft: Brood War 1.16.1
```

처음부터 실제 게임을 매번 실행하면 학습 속도가 느리고 재현성이 떨어질 수 있다. 거리·속도·공격 쿨다운·지형을 단순화한 mock simulator에서 정책을 먼저 학습한 뒤 BWAPI 환경에서 검증하는 방법이 현실적이다.

BWAPI 공식 시작 흐름은 Brood War 1.16.1, BWAPI 설치, AI module 빌드, 실행 환경 구성을 포함한다.[1] 실제 게임을 연결할 때는 게임 버전, frame rate, 명령 지연, 관측 지연, 랜덤 시드와 replay 파일을 함께 기록한다.

## 8. 평가 지표

승률 하나만 보면 정책의 문제가 보이지 않는다.

### 성능 지표

- 제한 시간 생존율
- 저글링 처치 수
- 벌처 생존 여부
- 벌처가 받은 피해량
- 킬/사망 비율
- 평균 교전 시간
- 지뢰 1개당 피해량
- 명령 수와 불필요한 명령 변경 수
- 평균·p95 frame decision latency

### 일반화 지표

- 학습에 사용하지 않은 시작 위치
- 학습하지 않은 저글링 수
- 새로운 맵과 choke 구조
- 저글링 접근 방향 변화
- 관측 지연과 명령 지연
- 속도 업그레이드 유무

### 비교군

```text
Random policy
Rule-based kite
Greedy attack policy
Trained policy
Human replay policy
```

각 조건을 동일한 random seed 집합으로 반복하고 평균뿐 아니라 분산과 최악 사례를 기록해야 한다.

## 9. 머신러닝이 배울 수 있는 것과 없는 것

학습할 수 있는 것:

- 어느 방향으로 후퇴할지
- 언제 공격과 이동을 번갈아 할지
- 가장 가까운 저글링과 낮은 체력 저글링 중 무엇을 선택할지
- 지뢰를 어디에 설치할지
- 좁은 지형에서 어느 쪽으로 빠질지

기본 규칙으로 제한하는 편이 좋은 것:

- 게임 API에 보내면 안 되는 명령
- 맵 밖 좌표
- 이미 죽은 유닛 target
- 존재하지 않는 지뢰 설치
- 명령 cooldown 위반
- 관측할 수 없는 미래 정보 사용

머신러닝 정책이 API 제약을 위반하지 않도록 action mask와 검증 계층을 둔다.

```text
정책 출력
  → action mask
  → 게임 상태 재검증
  → 명령 cooldown 확인
  → 실제 BWAPI command
  → command trace 기록
```

## 10. 실제 프로젝트로 확장하기

### 1단계: 재현 가능한 mock 환경

Python으로 좌표·속도·공격 쿨다운·간단한 충돌 모델만 구현한다. 이 단계에서는 학습 알고리즘보다 상태·행동·보상·평가 로그가 맞는지 확인한다.

### 2단계: 규칙 기반 BWAPI bot

C++ BWAPI bot으로 벌처와 저글링을 제어하고, frame별 상태와 명령을 JSONL로 기록한다. 이 결과가 baseline과 데이터 수집기가 된다.

### 3단계: 오프라인 imitation learning

규칙 기반 bot이나 사람 replay에서 state-action 데이터를 만들고 행동 예측 모델을 학습한다. 학습·검증·테스트 replay의 맵과 시작 위치를 분리한다.

### 4단계: 강화학습 fine-tuning

mock 환경에서 먼저 fine-tuning하고, 실제 BWAPI에서는 보수적인 action mask와 제한된 탐색으로 평가한다. 실제 게임에 학습 중인 정책을 바로 투입하지 말고 replay와 sandbox에서 검증한다.

### 5단계: 결과와 실패 사례 분석

잘한 경기만 저장하지 말고, 다음 실패를 별도로 분류한다.

- 공격 후 도망가지 못함
- 벽에 끼임
- 저글링에 포위됨
- 지뢰를 너무 늦게 설치함
- 공격 target을 계속 변경함
- 죽은 target을 반복 선택함
- timeout 이후에도 명령을 보냄

## 결론

벌처로 저글링을 잡는 문제는 작은 게임 실험처럼 보이지만, 실제로는 강화학습의 중요한 주제를 압축한다.

- 부분 관측
- 연속적인 위치 제어
- 공격과 이동의 결합
- 다수 적에 대한 credit assignment
- reward shaping
- curriculum learning
- action masking
- 시뮬레이터와 실제 환경의 차이
- frame 단위 평가와 재현성

전략적으로는 다음 순서가 가장 현실적이다.

1. 규칙 기반 kite bot을 만든다.
2. BWAPI frame trace를 수집한다.
3. mock 환경에서 상태·행동·보상을 검증한다.
4. imitation learning으로 초기 정책을 만든다.
5. curriculum 강화학습으로 일반화한다.
6. 새로운 맵·시작 위치·저글링 수에서 평가한다.

최종 목표는 “AI가 게임을 한다”가 아니라, **관측 가능한 상태에서 행동을 선택하고, 실패를 측정하며, 정책을 재현 가능하게 개선하는 강화학습 실험 플랫폼**을 만드는 것이다.

## 참고 자료

[1] BWAPI — StarCraft: Brood War AI 제어, 상태 관측, replay 분석  
[2] Liquipedia Vulture — 벌처 능력치와 카이팅·지뢰 활용  
[3] Liquipedia Spider Mine — 지뢰 피해·범위·작동 방식  
[4] Shao, Zhu, Zhao — StarCraft Micromanagement with Reinforcement Learning and Curriculum Transfer Learning

## 출처

- BWAPI: https://bwapi.github.io/
- Vulture: https://liquipedia.net/starcraft/Vulture
- Spider Mine: https://liquipedia.net/starcraft/Spider_Mine
- StarCraft Micromanagement with Reinforcement Learning: https://arxiv.org/abs/1804.00810

## Sources

[1] https://bwapi.github.io — BWAPI The Brood War API
[2] https://liquipedia.net/starcraft/Vulture — Liquipedia Vulture
[3] https://liquipedia.net/starcraft/Spider_Mine — Liquipedia Spider Mine
[4] https://arxiv.org/abs/1804.00810 — StarCraft Micromanagement with Reinforcement Learning
