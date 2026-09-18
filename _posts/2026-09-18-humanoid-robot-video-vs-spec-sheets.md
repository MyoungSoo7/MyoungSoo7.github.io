---
layout: post
title: "휴머노이드 영상 한 편을 사양서로 검증해보기 — 출처 없는 클립과 공식 스펙 사이"
date: 2026-09-18 21:13:24 +0900
categories: [robotics, ai]
tags: [휴머노이드, 로봇, 검증, unitree, boston-dynamics, 1x-neo, darpa-robotics-challenge]
---

## 이 글이 나온 이유

텔레그램으로 36초짜리 클립이 하나 왔다. 아파트 복도에서 남자 둘이 은색 휴머노이드와 격투를 벌인다. 캡션은 "이런 날이 올지도...?", 제보 채널은 [https://t.me/aiinnovationstudio](https://t.me/aiinnovationstudio) 다.

이런 영상은 매일 수십 개씩 돌아다닌다. 보는 사람이 실제로 던지는 질문은 하나다. **"저게 지금 되는 거야?"**

문제는 이 질문에 영상이 답을 못 한다는 것이다. 영상은 성공한 테이크만 남긴다. 실패한 테이크도, 사람이 뒤에서 조종하고 있었는지도, 배터리가 몇 분 남았는지도 프레임 안에 없다. 그래서 이 글은 영상을 해설하지 않는다. **영상으로는 판정이 안 된다는 것을 먼저 확인하고, 판정이 가능한 자료 — 제조사 공식 사양서와 동료심사 논문 — 로 갈아타는 과정**을 그대로 적는다.

---

## 1. 이 파일에 대해 확실히 말할 수 있는 것

받은 파일에서 기계적으로 읽히는 사실은 이게 전부다.

| 항목 | 값 |
| --- | --- |
| 길이 | 36.633333초 |
| 해상도 | 848×464 |
| 코덱 / 프레임레이트 | H.264 / 30fps |
| 오디오 | AAC |
| 크기 | 7,572,404 바이트 |

여기서 끝이다. 촬영 주체, 촬영 일자, 등장하는 기체의 제조사·모델명, 원본 게시처 — **하나도 확인되지 않는다.** 프레임을 늘어놓고 보면 렌더링·합성물의 특징(조명과 접지 그림자의 불일치, 충돌 순간의 관성 표현)이 눈에 띄지만, 그건 내 판단이지 증거가 아니다.

정직한 결론은 이것이다. **판정 불가.** 진짜라고도, 가짜라고도 이 파일만으로는 말할 수 없다. 그리고 이 "판정 불가"가 이 글에서 가장 중요한 한 줄이다. 출처 없는 클립을 근거로 삼는 순간, 뒤에 무슨 논리를 쌓아도 전부 무너진다.

---

## 2. 그럼 무엇으로 판정하나 — 사양서

영상이 못 하는 일을 사양서는 한다. 제조사가 자기 이름을 걸고 숫자를 적어놨고, 그 숫자는 반박 가능하다. 아래는 2026년 9월 18일 기준 **각 제조사 공식 제품 페이지에 적힌 값만** 옮긴 것이다. 제3자 리뷰·기사·집계 사이트는 한 줄도 섞지 않았다.

| 항목 | Unitree G1 | Boston Dynamics Atlas | 1X NEO |
| --- | --- | --- | --- |
| 키 | 1320mm (접으면 690mm) | 1.9 m (6.2 ft) | 5'6" |
| 무게 | 약 35kg (배터리 포함) | 90 kg (198 lbs) | 66 lbs |
| 자유도(DoF) | 23 (EDU 23~43) | 56 | 손 22×2, 팔 7×2, 목 3, 척추 2, 다리 6×2 |
| 가반하중 | 팔 최대 약 2kg (EDU 약 3kg) | 순간 50 kg / 지속 30 kg | Lift 154 lbs, Carry 55 lbs, 팔 페이로드 18 lbs |
| 구동 | 저관성 고속 내전형 PMSM | — | 저관성 텐던 드라이브 |
| 무릎 최대 토크 | 90 N·m (EDU 120 N·m) | — | — |
| 배터리 | 9000mAh, 약 2시간 | 4시간, 자가 교체식 | 842 Wh, 4시간 (급속충전 1시간 사용분당 6분) |
| 속도 | — | — | 보행 1.4 m/s, 최고 6.2 m/s, 손 8.0 m/s |
| 냉각 | 국소 공랭 | — | — |
| 안전 | — | — | 핀치포인트 없음, HIC < 250 |
| 가격 | $13.5K부터 | — | 보증금 $200 |

세 기체는 **서로 다른 문제를 푸는 기계**다. 같은 표에 올려놓으면 비교하고 싶어지지만, 실제로는 비교 대상이 아니다. G1은 13.5K달러짜리 연구·교육 플랫폼이고, Atlas는 제조 현장의 자재 취급을 겨냥하며(보스턴 다이내믹스는 페이지에서 "같은 작업대에서 직원과 같은 장비를 쓰도록 만들어졌다"고 적는다), NEO는 가정용 가사 로봇이다.

---

## 3. 영상 속 동작이 요구하는 것 vs. 사양서

이제 클립으로 돌아가자. 그 36초 동안 기체는 사람 둘을 상대로 타격을 주고받고, 균형을 잃지 않고, 좁은 복도에서 방향을 바꾼다. 이걸 사양서 항목으로 번역하면 이렇게 된다.

**팔 힘.** 사람을 밀거나 잡아채려면 팔 끝에서 수십 kg급 힘을 순간적으로 내야 한다. G1의 공식 값은 **팔 최대 부하 약 2kg**이다. 게다가 우니트리는 각주에 "팔의 최대 부하는 팔을 뻗은 자세에 따라 크게 달라진다"고 직접 적어뒀다 — 2kg조차 조건부 수치다. NEO는 Lift 154 lbs로 훨씬 크지만, 이건 들어올리기(정적 하중) 수치지 타격 수치가 아니다.

**충격을 받고도 서 있기.** 35kg짜리 이족보행체가 사람 체중이 실린 외력을 받는 상황이다. 어느 제조사 페이지에도 "외부 충격 내성" 항목은 없다. 없는 게 이상한 게 아니라, **아직 스펙으로 약속할 수 있는 영역이 아니라서** 없다.

**지속 시간.** G1 약 2시간, Atlas 4시간, NEO 4시간. 36초는 문제가 안 된다. 다만 이 수치들은 격투 같은 고부하 동작 기준이 아니다.

**열.** G1의 냉각은 "국소 공랭"이다. 뒤에서 보겠지만, 이 항목은 로봇 데모에서 가장 조용하게 실패하는 지점이다.

정리하면, 저 영상이 요구하는 능력 중 **사양서에 숫자로 존재하는 것은 거의 없다.** 그건 "로봇이 못 한다"는 뜻이 아니라, **현재 상용 기체들이 애초에 그 방향으로 설계·검증되지 않았다**는 뜻이다.

---

## 4. 업계가 스스로 적어둔 문장들

가장 설득력 있는 반증은 경쟁사가 아니라 **제조사 자신의 페이지**에 있다.

우니트리는 G1 페이지 각주에서 이렇게 쓴다.

> "The humanoid robot has a complex structure and extremely powerful power. Users are asked to keep a sufficient safe distance between the humanoid robot and people. Please use with caution"

> "Currently, the global humanoid robot industry is in the early stages of exploration. Individual users are strongly advised to thoroughly understand the limitations of humanoid robots before making a purchase."

*(휴머노이드는 구조가 복잡하고 출력이 매우 강하다. 사람과 충분한 안전거리를 유지하라. / 현재 전 세계 휴머노이드 산업은 탐색 초기 단계다. 개인 구매자는 한계를 충분히 이해한 뒤 구매하라.)*

**사람과 안전거리를 두라고 파는 제품이다.** 영상은 사람과 몸을 맞대고 있다.

1X는 NEO 페이지에서 자율성의 경계를 스스로 그어둔다.

> "NEO works autonomously by default. For any chore it doesn't know, you can schedule a 1X Expert to guide it, helping NEO learn while getting the job done."

> "Remote Control — Pilot your NEO from anywhere in the world through your Mobile App & VR device."

> "NEO arrives with basic autonomy for early owners and grows in capability overtime."

*(모르는 집안일은 1X 전문가가 원격으로 지도한다. / 모바일 앱과 VR 기기로 전 세계 어디서든 조종할 수 있다. / 초기 구매자에게는 기본 수준의 자율성으로 출고되며 차차 성장한다.)*

이건 숨겨진 약점이 아니라 **광고된 기능**이다. 그리고 동시에 영상 판독의 핵심 함의를 준다 — **매끄럽게 움직이는 휴머노이드 영상은 자율 동작의 증거가 아니다.** 사람이 VR로 조종했을 수도 있고, 그건 제품 사양에 적힌 정상 동작 모드다.

---

## 5. 10년 전에 이미 나온 결론

이 문제의 가장 좋은 1차 문헌은 2016년에 나왔다. DARPA Robotics Challenge(DRC) 결선에 나간 팀들의 자체 보고서를 모아 분석한 Atkeson 외, *"What Happened at the DARPA Robotics Challenge, and Why?"* 다. 카네기멜론 연구팀이 직접 참가하면서 쓴 보고서라, 실패를 관찰한 게 아니라 **당사자로서 기록한** 자료다.

논문이 데이터로 뒷받침하는 문장들을 원문 그대로 옮긴다.

> "There is something wrong with robotics. We have collectively produced many videos showing convincing robot performance. However, in a situation where the researchers did not control the test, most robots, even older and well-tested designs, performed poorly and often fell."

*(로보틱스에 뭔가 잘못돼 있다. 우리는 설득력 있는 로봇 성능을 보여주는 영상을 집단적으로 아주 많이 만들어냈다. 그러나 연구자가 테스트를 통제하지 못하는 상황에서는, 오래되고 충분히 검증된 설계조차 대부분 형편없이 동작했고 자주 넘어졌다.)*

이 한 문단이 이 글 전체의 논거다. **잘 만든 영상과 통제되지 않은 환경에서의 성능은 다른 축이다.** 그리고 그 둘의 간극은 DRC에서 상금 수백만 달러가 걸린 무대 위에서 공개적으로 드러났다.

논문이 짚은 구체적 실패 양상들:

**조작자 오류가 1위였다.**

> "The biggest enemy of robot stability and performance in the DRC was operator errors."

**넘어지면 못 일어났다.**

> "no biped that fell got back up"

**완전 자율도, 완전 원격조종도 아니었다.**

> "No robot was either fully teleoperated or fully autonomous"

**행동은 깨지기 쉬웠다.**

> "Behaviors were fragile"

**열이 사람을 잡았다.** Atlas는 전완부 모터가 과열돼 자동 차단됐고, NimbRo도 다리/바퀴 하이브리드에서 모터 과열을 겪었다. 논문은 이렇게 정리한다.

> "Heat dissipation, and planning for thermal management are important."

그리고 DRC 우승팀(KAIST)과 예선 우승팀(Schaft)이 방열·열관리 설계에 많은 공을 들였다고 덧붙인다. **10년 전 우승의 상당 부분이 냉각이었다.** 앞의 표에서 G1의 냉각 방식이 "국소 공랭"이라고 적혀 있던 것을 다시 보게 되는 대목이다.

**하드웨어의 한계도 명확했다.** 논문은 Atlas가 "너무 상부 중심이 높고 팔이 약했다(too top heavy and its arms were too weak)"고 적는다.

**그리고 사람이 로봇을 구하러 들어가는 건 답이 아니다.**

> "Humans rescuing robots is not acceptable"

논문의 전망은 이렇게 맺는다 — 하드웨어와 소프트웨어 설계 양쪽에서 **패러다임 전환이 없는 한(unless there is a paradigm shift in both hardware and software design)** 가까운 미래에 휴머노이드의 광범위한 활용을 기대하기 어렵다.

10년이 지났고, 그 사이 강화학습과 대규모 모델이 들어오면서 소프트웨어 쪽에서는 실제로 큰 변화가 있었다. 하지만 **열, 배터리, 넘어짐, 조작자 오류**는 물리 문제라서 그대로 남아 있다. 앞에서 본 사양서들이 정확히 그 항목들에 숫자를 적고 있는 이유다.

---

## 6. 로봇 데모 영상을 읽는 체크리스트

이 글에서 실제로 건질 수 있는 도구는 이거다. 다음에 비슷한 클립을 받으면 순서대로 물어보면 된다.

1. **원본 게시처가 어디인가.** 제조사 공식 채널인가, 재게시 계정인가. 재게시만 있으면 거기서 멈춘다.
2. **컷이 몇 번 들어갔나.** 연속 촬영 1테이크인가, 편집으로 이어붙였나. 성공 구간만 잘라 붙이면 어떤 로봇도 유능해 보인다.
3. **조종자가 화면 밖에 있는가.** 1X가 광고하는 "VR로 전 세계 어디서든 조종" 이 기본 기능이라는 걸 기억할 것.
4. **몇 번째 시도인가.** 이건 영상이 절대 안 알려준다. 자체 보고서나 논문만 알려준다.
5. **얼마나 오래 돌았나.** 30초짜리 클립은 열 문제를 절대 보여주지 않는다. DRC의 과열 실패는 몇 분~몇십 분 단위에서 나왔다.
6. **넘어졌을 때 무슨 일이 일어나는가.** 안 보여주면, 안 보여주는 데 이유가 있을 확률이 높다.
7. **그 동작에 해당하는 항목이 사양서에 있는가.** 없으면 그건 아직 제품이 약속하는 능력이 아니다.

---

## 7. 한계 명시

- **원본 영상은 끝까지 검증되지 않았다.** 제보 링크([https://t.me/aiinnovationstudio](https://t.me/aiinnovationstudio))는 클립의 **출처 표시일 뿐**이며, 이 글의 어떤 사실 주장도 이 채널을 근거로 삼지 않았다. 텔레그램 채널은 권위 있는 1차 출처가 아니다.
- **사양서는 제조사 자체 공표값이다.** 중립 제3자가 동일 조건에서 세 기체를 실측해 비교한 공개 자료를 나는 찾지 못했다. 따라서 표의 숫자들은 "제조사가 공표한 값"으로만 읽어야 하며, **기체 간 우열 판정의 근거로 쓸 수 없다.** 측정 조건(자세, 온도, 배터리 잔량)이 제품마다 다르고 대부분 공개돼 있지 않다.
- **DRC 논문은 2015년 대회 기록이다.** 소프트웨어 스택은 그 사이 크게 바뀌었다. 여기서 인용한 것은 시간이 지나도 유효한 물리·운용 측면의 관찰이며, 현재 기체의 성능을 직접 규정하지 않는다.
- **표의 빈칸("—")은 "0"이 아니라 "해당 제조사 페이지에 그 항목이 없다"는 뜻이다.** 없는 항목을 추정해 채우지 않았다.

---

## 마무리

"이런 날이 올지도?"라는 질문에 대한 정직한 답은 이렇다.

**저 영상은 근거가 될 수 없다.** 출처가 없기 때문이다. 대신 근거가 될 수 있는 것들이 공개돼 있다 — 제조사가 직접 적은 토크와 가반하중과 배터리 시간, 그리고 "사람과 안전거리를 유지하라"는 각주. 10년 전 DARPA 무대에서 "설득력 있는 영상"과 "통제되지 않은 환경의 성능"이 얼마나 벌어지는지 공개적으로 측정된 기록.

영상은 계속 나올 것이고 점점 더 그럴듯해질 것이다. 그래서 **판정의 기준을 영상 바깥에 두는 습관** 하나가, 앞으로 몇 년간 가장 실용적인 기술 리터러시가 된다.

---

## References

1. Unitree Robotics, *Unitree G1 Humanoid agent AI avatar* (공식 제품 페이지, 사양표 및 각주 [2][6][9]) — [https://www.unitree.com/g1](https://www.unitree.com/g1)
2. Boston Dynamics, *Atlas® Humanoid Robot* (공식 제품 페이지, 사양) — [https://bostondynamics.com/atlas/](https://bostondynamics.com/atlas/)
3. 1X Technologies, *NEO Home Robot* (공식 제품 페이지, Hardware/Safety 사양 및 Expert Mode·Remote Control 설명) — [https://www.1x.tech/neo](https://www.1x.tech/neo)
4. C. G. Atkeson, B. P. W. Babu, N. Banerjee, D. Berenson, C. P. Bove, X. Cui, M. DeDonato, R. Du, S. Feng, P. Franklin, M. Gennert, J. P. Graff, P. He, A. Jaeger, J. Kim, K. Knoedler, L. Li, C. Liu, X. Long, T. Padir, F. Polido, G. G. Tighe, X. Xinjilefu, *"What Happened at the DARPA Robotics Challenge, and Why?"* — [https://www.cs.cmu.edu/~cga/drc/jfr-what.pdf](https://www.cs.cmu.edu/~cga/drc/jfr-what.pdf)
5. 클립 제보 출처 (권위 있는 출처 아님, 사실 주장의 근거로 사용하지 않음) — [https://t.me/aiinnovationstudio](https://t.me/aiinnovationstudio)
