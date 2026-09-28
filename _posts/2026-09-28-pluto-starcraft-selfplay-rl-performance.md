---
layout: post
title: "스타1 AI 플루토(Pluto)의 성능 — CoG 2026 98.6% 승률을 1차 자료로 뜯어보기"
date: 2026-09-28 22:31:47 +0900
categories: [ai]
tags: [starcraft, brood-war, reinforcement-learning, self-play, pluto, cog2026, bwapi]
---

스타크래프트: 브루드 워 AI **플루토(Pluto)** 가 화제다. "프로를 이긴 AI" 라는 기사가 돌고 있지만, 이 글은 **대회 주최 측 공식 결과**와 **제작자가 직접 쓴 README·FAQ**만으로 성능을 정리한다. 언론 보도는 끝에 따로 떼어 "미검증 2차 보도" 로 다룬다.

## 1. 한 줄 요약

- **무엇**: 셀프플레이 강화학습으로 처음부터 학습한 **신경망 하나**가 매크로·마이크로, 세 종족 전부를 직접 플레이한다. 스크립트 플레이는 없다. ([tscmoo/pluto README](https://github.com/tscmoo/pluto))
- **성적**: CoG 2026 StarCraft AI Competition 라운드로빈 **2,884전 2,844승 40패(98.61%)**, 크래시 0·프레임 타임아웃 0. 결승(7전 4선승)에서 PurpleWave 를 **4–1** 로 꺾고 우승. ([CoG 2026 공식 결과](https://davechurchill.ca/starcraft/cog/results/2026/))
- **하드웨어**: 315M 파라미터 int8 모델을 **GPU 없이 CPU 로** 돌린다. ([Pluto FAQ](https://davechurchill.ca/starcraft/cog/results/2026/))

## 2. 대회 성적 — 주최 측 공식 수치

CoG 2026 StarCraft AI Competition 은 Memorial University 의 David Churchill 이 운영하는 대회다. 전장의 안개(fog of war)가 켜져 있고 치트는 금지이며, 프레임당 시간 제한을 넘기면 타임아웃 패로 처리한다. ([대회 규정](https://davechurchill.ca/starcraft/cog/)) 순위는 "상대 봇 중 몇 개에게 승률 우위를 가졌나(Bots Beaten)" 로 매기고, 1·2위가 7전 4선승 결승을 치렀다. ([공식 결과](https://davechurchill.ca/starcraft/cog/results/2026/))

### 라운드로빈 전체 (10개 봇)

| 봇 | 종족 | 경기 | 승 | 패 | 승률 | 크래시 | 타임아웃 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Pluto** | Random | 2884 | 2844 | 40 | **98.61%** | 0 | 0 |
| Stardust | Protoss | 2884 | 2237 | 647 | 77.57% | 0 | 11 |
| BananaBrain | Protoss | 2889 | 2135 | 754 | 73.90% | 0 | 0 |
| PurpleWave | Protoss | 2883 | 2037 | 846 | 70.66% | 0 | 0 |
| Microwave | Zerg | 2884 | 1318 | 1566 | 45.70% | 0 | 0 |
| McRave | Zerg | 2889 | 1313 | 1576 | 45.45% | 18 | 3 |
| Steamhammer | Random | 2883 | 1025 | 1858 | 35.55% | 2 | 0 |
| UAlbertaBot | Random | 2882 | 904 | 1978 | 31.37% | 2 | 0 |
| Venator | Protoss | 2883 | 483 | 2400 | 16.75% | 0 | 0 |
| InfestedArtosis | Zerg | 2889 | 129 | 2760 | 4.47% | 0 | 0 |

출처: 공식 결과 페이지의 요약 데이터(`results_summary`). 2위와의 승률 격차가 **21%p** 다.

### 플루토의 상대별 전적

| 상대 | 플루토 승 / 경기 | 승률 |
| --- | ---: | ---: |
| Stardust | 306 / 320 | 95.6% |
| BananaBrain | 318 / 321 | 99.1% |
| PurpleWave | 299 / 320 | 93.4% |
| Microwave | 321 / 321 | 100% |
| McRave | 321 / 321 | 100% |
| Steamhammer | 318 / 320 | 99.4% |
| UAlbertaBot | 320 / 320 | 100% |
| Venator | 320 / 320 | 100% |
| InfestedArtosis | 321 / 321 | 100% |

40패의 내역은 PurpleWave 21패, Stardust 14패, BananaBrain 3패, Steamhammer 2패다. 38패가 상위 프로토스 봇 3개에 몰려 있고, 나머지 상대에게는 사실상 전승이다.

특기할 점은 **플루토가 종족을 Random 으로 냈다**는 것이다. 매 경기 종족이 바뀌는데도 한 모델로 이 성적을 냈다. 상위권 봇 대부분은 한 종족에 특화한 수작업 봇이다.

## 3. 어떻게 만들었나 — 제작자 FAQ 기준

아래는 대회 제출물에 포함된 제작자 FAQ(`PLUTO_README.txt`)와 GitHub README 의 요약이다. 전부 **제작자 1차 기술 설명**이며 제3자 재현 결과는 아직 없다.

- **학습**: PPO 계열 actor-critic, **순수 셀프플레이**. 리플레이·모방학습·외부 봇 없음. 학습 경기의 양쪽을 **항상 현재 가중치**가 둔다(옛 체크포인트나 리그 상대를 쓰지 않음).
- **보상**: 유닛 자원가치 합(밀집 신호), 빌드오더 느슨한 추종 보너스, 희귀 유닛·테크 다양성 보너스, 최종 승패 ±1. 전부 제로섬.
- **관측**: 사람이 게임에서 볼 수 있는 것 위주. 보이는 유닛당 토큰 1개, 128×128 빌드타일 맵 그리드, 자원·인구 등 전역 정보, 자기 직전 4개 행동. 상대 테크는 **실제로 쓰는 걸 봐야** 안다. 정찰 정보를 따로 장부로 기록하지 않고, **GRU(4096-d) + 느린 트랜스포머 메모리**에 기억을 맡긴다.
- **구조**: 유닛 토큰 → 6층 트랜스포머(768-d), 맵 → CNN 인코더(8×8 풀링), GRU 가 유닛·맵에 교차주의. 행동은 5개 헤드(무엇을 / 인자 / 대략 위치 8×8 / 정밀 위치 16×16 / 대상 유닛)로 순차 샘플링하고 합법 행동 마스크로 강제한다. **탐색(search)은 없다** — 순전파 한 번에 행동 하나.
- **빌드 선택**: 상대별 승패 기록으로 밴딧이 오프닝 라벨을 고른다. 라운드로빈 동안 상대에 적응하는 유일한 "기억" 이다.
- **항복**: 학습 때 쓴 비평자 중 작은 승률 헤드만 남겨, 예측 승률이 약 10초간 0 근처면 "gg" 를 치고 나간다.

## 4. 실행 성능 — "AI 가 빠르게 누른다" 에 대한 답

이 부분이 성능 논의에서 가장 중요하다. FAQ 의 제약은 다음과 같다.

| 항목 | 값 | 출처 |
| --- | --- | --- |
| 모델 스텝 주기 | **6프레임마다 1회** | FAQ |
| 스텝당 행동 수 | **1개** (선택도 하나의 행동으로 계산) | FAQ |
| 최대 행동 빈도 | **초당 약 4개** | FAQ |
| 반응 지연 | 관측 후 4프레임 뒤 적용 → 새 사건 반응 **4~10프레임(약 170~420ms)** | FAQ |
| 프레임 예산 | 44ms | FAQ |
| 모델 | 315M 파라미터, int8, CPU 전용(AVX2 필수, AVX-VNNI 권장) | FAQ |
| 권장 사양 | 6코어 이상, 여유 RAM 약 2GB, 대회 설정은 8스레드 고정 | FAQ |

즉 **행동 빈도는 사람보다 느리게 묶여 있다.** 한 번 선택할 때 12기 제한이 없고, **가상 카메라가 없어 탐색된 맵 전체를 한 번에 보고 행동한다**는 점은 사람과 다른 이점이다. FAQ 가 스스로 밝힌 차이이므로, "공정한 조건" 여부를 따질 때는 이 두 가지를 같이 봐야 한다.

CPU 가 44ms 예산을 못 지키면 명령이 늦게 적용되고 스텝이 빠진다. 학습 때 본 적 없는 조건이라 플레이가 나빠진다고 제작자가 명시했다. 공식 결과의 **프레임 타임아웃 0건**은 대회 하드웨어에서 이 예산을 지켰다는 뜻이다.

## 5. 대회 밖 이야기 — 미검증 2차 보도

2026년 9월, 스타크래프트: 리마스터 래더에서 "^333^" 이라는 계정이 프로게이머들을 이겼고 이것이 플루토라는 보도가 나왔다([Dexerto, 2026-09-21](https://www.dexerto.com/gaming/ai-bot-destroys-top-starcraft-pros-after-invading-ladder-and-using-absurd-strategies-3410863/)). 같은 기사는 **제작자 허락 없이 제3자가 래더에 올린 것**이라고 전한다.

이 글에서는 아래 이유로 이 부분을 **성능 근거로 쓰지 않는다.**

- 제작자나 대회 주최 측의 1차 확인을 찾지 못했다. 상대 명단·전적도 텍스트로 검증되는 1차 자료가 없다.
- 래더 계정이 실제로 대회 제출본과 같은 모델·같은 제약(초당 약 4행동, 맵핵 없음)으로 돌았는지 알 수 없다. 보도에는 맵핵 의혹 언급도 있다.
- 일부 기사는 대회명을 "Computer Olympiad 2026" 으로 적는데, 주최 측 공식 페이지의 명칭은 **CoG 2026 StarCraft AI Competition** 이다. 2차 보도의 사실관계가 흔들린다는 신호로 본다.

## 6. 정리 — 무엇이 새롭고, 무엇은 아직 모르나

**새로운 점.** AlphaStar(스타2, DeepMind 2019)는 사람 리플레이 모방학습으로 시작해 리그 훈련을 썼다([Vinyals et al., Nature 2019](https://www.nature.com/articles/s41586-019-1724-z)). 플루토는 제작자 설명대로라면 **모방 없이 셀프플레이만**, 옛 체크포인트 리그도 없이, 세 종족을 한 모델로 학습했다. 그리고 그 결과를 **GPU 없는 CPU 추론으로** 수작업 봇 최강자들 상대로 98.6% 승률로 보였다. 브루드 워 AI 대회는 오랫동안 규칙 기반 봇이 상위권을 차지해 온 무대다.

**아직 모르는 것.**

- 학습 연산량(GPU 시간·경기 수)은 공개 자료에서 찾지 못했다. 그래서 "싸게 만들었다" 는 말은 할 수 없다.
- 플루토 대 사람 프로의 **통제된** 대결 기록은 없다. 중립 제3자 헤드투헤드 평가도 **부재**하다.
- 40패의 원인(특정 맵·특정 빌드 약점)은 공개 리플레이로 분석할 수 있지만 이 글에서는 하지 않았다.

대회 성적은 공식 수치로 확실하고, 구조·제약은 제작자 설명으로 명확하다. "프로를 이겼다" 는 이야기만 아직 1차 근거가 없다.

## References

1. tscmoo, *Pluto — StarCraft: Brood War AI* (GitHub README, releases `cog2026-2578600`). <https://github.com/tscmoo/pluto>
2. David Churchill, *CoG 2026 StarCraft AI Competition — Results* (결과 요약·상대별 전적·결승·`PLUTO_README.txt`). <https://davechurchill.ca/starcraft/cog/results/2026/>
3. David Churchill, *StarCraft AI Competition — Rules*. <https://davechurchill.ca/starcraft/cog/>
4. IEEE Conference on Games 2026, *Competitions*. <https://cog2026.org/competitions>
5. O. Vinyals et al., "Grandmaster level in StarCraft II using multi-agent reinforcement learning," *Nature* 575, 350–354 (2019). <https://www.nature.com/articles/s41586-019-1724-z>
6. (2차 보도, 미검증) Dexerto, "AI bot destroys top StarCraft pros after invading ladder…" 2026-09-21. <https://www.dexerto.com/gaming/ai-bot-destroys-top-starcraft-pros-after-invading-ladder-and-using-absurd-strategies-3410863/>
