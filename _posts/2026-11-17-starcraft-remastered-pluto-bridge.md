---
layout: post
title: "스타크래프트 리마스터에서 플루토(Pluto) AI 돌리기 — 1.16.1 전용 봇을 리마스터에 잇는 브리지의 구조와 한계"
date: 2026-11-17 00:18:04 +0900
categories: [ai]
tags: [starcraft, brood-war, remastered, pluto, bwapi, reinforcement-learning, eula]
---

CoG 2026 우승 봇 **플루토(Pluto)** 의 성능은 [9월 글](/2026/09/28/pluto-starcraft-selfplay-rl-performance/)에서 주최 측 공식 결과로 정리했다. 이번 글은 그 봇을 **스타크래프트: 리마스터** 싱글플레이에서 돌린 설치기([CODINGNOW, 2026-11-16](https://www.coding-now.com/starcraft-pluto-ai))를 읽고, 기술적으로 무슨 일이 벌어지는지와 어디까지가 확인된 사실인지를 1차 자료로 가려 본다.

## 1. 한 줄 요약

- **플루토는 원래 리마스터용이 아니다.** 공식 요구 사항은 *브루드 워 1.16.1 + BWAPI 4.4.0* 이다. ([tscmoo/pluto README](https://github.com/tscmoo/pluto))
- 리마스터에서 돌리는 건 **제3자 비공식 브리지**([lpflhh/Pluto-AI-Starcraft-Remaster](https://github.com/lpflhh/Pluto-AI-Starcraft-Remaster))다. 플루토 원본 파일은 그대로 두고, 실행 중인 리마스터 프로세스 메모리에 올라가 BWAPI 인터페이스를 흉내 낸다.
- 지원 조합은 **리마스터 1.23.10.13515 x86(32비트) + CoG 2026 모델** 하나뿐이다. 실행기가 SHA-256 으로 검사하고 다르면 거부한다.
- 블리자드 EULA 의 "봇" 정의는 싱글·멀티를 구분하지 않는다. **위험을 감수하는 건 사용자 몫**이다.

## 2. 왜 "브리지" 가 필요한가

플루토 제작자 tscmoo 의 README 가 밝힌 실행 구조는 이렇다. ([README](https://github.com/tscmoo/pluto))

| 구성 요소 | 역할 |
| --- | --- |
| `pluto.dll` | 32비트 BWAPI 모듈. 게임 안에서 관측·명령 |
| `pluto/pluto_infer.exe` | 64비트 CPU 추론 엔진. 공유 메모리로 DLL 과 통신 |
| `pluto/pluto_weights.bin` | int8 가중치 (CoG 2026 모델은 315M 파라미터) |

모델은 **6게임프레임마다 한 스텝**을 밟고, 느린 CPU 에서는 봇이 못해지는 대신 게임이 느려지도록 설계돼 있다. 네트워크 연결은 하지 않는다. ([README](https://github.com/tscmoo/pluto), [CoG 2026 릴리스](https://github.com/tscmoo/pluto/releases/tag/cog2026-2578600))

문제는 BWAPI 4.4.0 이 1.16.1 의 메모리 구조를 전제로 한다는 점이다. 리마스터는 엔진이 다르고 BWAPI 를 공식 지원하지 않는다. 그래서 브리지 README 는 스스로를 이렇게 설명한다.

> 원본 Pluto 저장소에는 소스 코드가 공개되어 있지 않습니다. 따라서 이 프로젝트는 모델을 재작성하지 않고 원래 `pluto.dll`, `pluto_infer.exe`, 가중치를 그대로 사용합니다. BWAPI 4.4.0 인터페이스와 Pluto가 직접 참조하는 Brood War 1.16.1 메모리를 리마스터 실행 환경에 연결합니다. — [lpflhh README](https://github.com/lpflhh/Pluto-AI-Starcraft-Remaster)

즉 **플루토가 "1.16.1 이라고 믿는" 메모리 모습을 리마스터 위에 재현**해 주는 어댑터다. 그래서 범위가 좁다.

- 일반 BWAPI 봇 전체를 돌리는 대체 BWAPI가 **아니다**. 플루토가 실제로 쓰는 경로만 구현했다.
- 게임 실행 파일 해시가 바뀌면(리마스터 패치) 주소 프로필을 다시 검증해야 한다. 업데이트 한 번이면 멈춘다.
- 브리지가 지원하는 모델은 CoG 2026(`cog2026-2578600`)뿐이다. 10월에 나온 [v2.0](https://github.com/tscmoo/pluto/releases)(`md09b_1331000`, 342M)은 해시 검사에서 막힌다.
- 리마스터 64비트 실행 파일은 대상이 아니다. 플루토 DLL 이 32비트라서다.

## 3. 원문 설치기에서 확인된 것 (단일 PC 실측)

아래 수치는 **CODINGNOW 저자가 자기 PC 한 대(i7-12700KF, Windows 11)에서 2026-11-14~16 에 잰 것**이다. 재현된 값이 아니라 한 사람의 실측 기록으로 읽어야 한다. ([원문](https://www.coding-now.com/starcraft-pluto-ai))

- **원본 실행기 그대로는 실패했다.** 숨김 창으로 스타를 띄우는 탓에 `StarCraft did not create its window within 30 seconds` 가 두 번 났고, 숨김 옵션을 빼고 대기 시간을 90초로 늘려 해결했다고 적었다.
- **APM 상한은 원본에 없는 기능이다.** 저자는 제3자 패치(PlutoArena, MIT)를 적용해 브리지를 다시 빌드했다. 2배속 1대1 네 판을 상한 없음 / 400 / 220 / 150 으로 바꿔 모두 이겼고, 가장 바쁜 1분의 명령 수가 999 / 407 / 218 / 158 이었다고 기록했다(유닛 선택 제외, 저자가 고친 실행기로 잰 값).
- **1대7(컴퓨터 상대)도 이겼지만 느려졌다.** 추론 한 번에 약 86ms 가 걸려 "이 PC 가 못 따라간다" 알림이 떴다. 이것은 README 의 설계(늦으면 게임을 붙잡는다)와 맞는 증상이다. README 는 현행 데스크톱에서 스텝당 약 20ms, 큰 후반 교전에서 그 3배까지를 제시한다.
- **1대다는 원래 학습 범위 밖이다.** 플루토는 1대1 밀리로 학습됐다(README). 브리지도 1대다 모드를 "실험판" 으로 따로 두고, 오프닝과 상대 종족 판단이 대표 상대 한 명 기준이라고 밝힌다.

원문이 칭찬할 만한 점은 **해 보지 않은 것을 "확인 안 됨" 으로 따로 적었다는 것**이다. 승률 그래프, 반응 지연을 넣은 경기, v2.0 모델, 사람 대 플루토는 다루지 않았다고 명시했다.

## 4. 사람이 가장 자주 막히는 곳

원문과 브리지 README 의 문제 해결 절을 겹쳐 보면 원인은 대부분 **"조건이 1대1 밀리 + 정확한 버전" 에서 벗어난 것**이다.

| 증상 | 원인 | 출처 |
| --- | --- | --- |
| 해시 불일치로 멈춤 | 게임 패치, 또는 v2.0 모델 사용 | 브리지 README, 원문 |
| 봇이 아무것도 안 함 (`session_skipped`) | 1대1 실행기에 컴퓨터 여럿 / 유즈맵·FFA·Top vs Bottom | 브리지 README, 원문 |
| 오리지널로 들어감 | 게임 유형에서 '확장팩'을 고르지 않음 | 원문 |
| 게임이 느림 | CPU 추론 대기 (설계상 의도된 동작) | 플루토 README |
| 관전 중 유닛 클릭 → 엉킴 | 사람 입력이 봇 명령과 섞임 | 브리지 README |

로그는 브리지 폴더 `runtime\` 의 `bridge.log` · `pluto.log` · `pluto_infer.log` 에 남는다.

## 5. 약관 — 싱글이면 괜찮은가

블리자드 최종 사용자 사용권 계약(EULA) 1.C 는 금지 대상을 이렇게 정의한다. ([Blizzard EULA](https://www.blizzard.com/en-us/legal/2c72a35c-bf1b-4ae6-99ec-80624e1b429c/blizzard-end-user-license-agreement))

> bots; i.e. any code and/or software, not expressly authorized by Blizzard, that allows the automated control of a Game …
> hacks; i.e. accessing or modifying the software of the Platform in any manner not expressly authorized by Blizzard …

이 문구에는 **싱글플레이 예외가 없다.** 프로세스 메모리에 올라가 게임을 자동 조종하는 브리지는 문언상 두 정의에 모두 걸린다. 별도의 [Anti-Cheating Agreement](https://www.blizzard.com/en-us/legal/cd5930c0-2784-420c-a23d-1e0d6ff8599b/anti-cheating-agreement) 는 게임 프로세스에 붙은 제3자 코드를 검사하는 유틸리티가 돈다고도 밝힌다.

다만 **오프라인 싱글에서 실제로 제재가 나오는지는 공개 근거를 찾지 못했다.** "안전하다" 도 "반드시 걸린다" 도 이 글은 주장하지 않는다. 원문 저자의 설정 툴이 첫 실행에 "약관·계정 제재 위험, 혼자 하기 전용, 사람 상대 금지" 동의를 받는 것도 같은 판단으로 보인다.

멀티플레이는 다르다. 브리지에는 배틀넷 공개 방에서 사람과 1대1을 하는 **멀티플레이 개발판 옵션이 들어 있다**(README). 사람 상대로 봇을 몰래 쓰면 EULA 의 cheats 정의("다른 플레이어보다 이점")까지 걸리고, 상대에게 피해를 준다. 9월에 리마스터 래더에서 정체불명 계정이 프로를 이겼다는 보도(Dexerto, 2026-09-21)가 있었는데, 제작자 확인이 없는 미검증 2차 보도라 9월 글에서도 성능 근거로 쓰지 않았다.

## 6. 라이선스 — 무엇을 퍼뜨리면 안 되나

| 대상 | 라이선스 상태 |
| --- | --- |
| 플루토 dll·추론기·가중치 | 저장소에 라이선스 파일 없음, 바이너리만 배포 ([tscmoo/pluto](https://github.com/tscmoo/pluto)) |
| lpflhh 브리지 | 저장소 자체 라이선스 없음. 동봉된 BWAPI 는 LGPL v3, MinHook 은 BSD (원문 표기) |

라이선스가 없으면 기본값은 "모든 권리 보유" 다. 원문 저자가 다시 빌드한 dll·exe 와 고친 스크립트를 공개하지 않고 원래 받는 곳 링크만 건 것은 이 때문이다. 이 글도 같은 이유로 파일을 올리지 않는다.

## 7. 정리

- 리마스터에서 플루토가 도는 건 **플루토가 리마스터를 지원해서가 아니라, 제3자가 1.16.1 의 메모리 모습을 흉내 내 줘서**다. 버전 하나만 바뀌어도 깨진다.
- 원문의 APM 상한 실험은 흥미롭지만 **원본 플루토의 기능이 아니라 패치된 브리지의 기능**이고, 한 PC 의 기록이다.
- 약관 문언은 싱글·멀티를 가리지 않는다. 쓰려면 오프라인·혼자 하기에서, 계정 위험을 알고 쓰는 게 최소선이다.
- 플루토를 "공식적으로" 돌리는 길은 여전히 **1.16.1 + BWAPI 4.4.0** 이다.

## References

1. tscmoo, *Pluto — StarCraft: Brood War AI* (README, 요구 사항·실행 구조). https://github.com/tscmoo/pluto
2. tscmoo, *Pluto — CoG 2026 entry* (릴리스 노트, 315M int8, SHA-256). https://github.com/tscmoo/pluto/releases/tag/cog2026-2578600
3. tscmoo, *Pluto v2.0* (릴리스 노트, md09b_1331000). https://github.com/tscmoo/pluto/releases
4. lpflhh, *Pluto for StarCraft: Remastered* (비공식 브리지 README). https://github.com/lpflhh/Pluto-AI-Starcraft-Remaster
5. CODINGNOW, 「스타크래프트 리마스터에서 Pluto AI 돌리기 — 설치 순서 · 설정 툴 · 자주 나는 오류」, 2026-11-16 (단일 PC 실측 기록). https://www.coding-now.com/starcraft-pluto-ai
6. David Churchill, *CoG 2026 StarCraft AI Competition — Results*. https://davechurchill.ca/starcraft/cog/results/2026/
7. Blizzard Entertainment, *Blizzard End User License Agreement* §1.C. https://www.blizzard.com/en-us/legal/2c72a35c-bf1b-4ae6-99ec-80624e1b429c/blizzard-end-user-license-agreement
8. Blizzard Entertainment, *Anti-Cheating Agreement*. https://www.blizzard.com/en-us/legal/cd5930c0-2784-420c-a23d-1e0d6ff8599b/anti-cheating-agreement
9. (2차 보도, 미검증) Dexerto, 2026-09-21. https://www.dexerto.com/gaming/ai-bot-destroys-top-starcraft-pros-after-invading-ladder-and-using-absurd-strategies-3410863/
