---
layout: post
title: "초파리 뇌 지도로 운전하고 코인 사고 둠 한다 — 커넥톰 공개 이후 깃헙에서 벌어지는 일"
date: 2026-09-25 11:50:00 +0900
categories: [ai, neuroscience]
tags: [connectome, drosophila, malecns, flywire, simulation, lif, github, open-data, dagger]
---

농민신문이 [「틱톡부터 운전·코인까지…개발자들의 기상천외 '가상 초파리' 실험」](https://www.nongmin.com/article/20260923500406)
(2026-09-23)이라는 기사를 냈다. 요지는 이렇다. 초파리 신경계 전체의 배선도(**커넥톰, connectome**)가 공개되자
전 세계 개발자들이 그 배선도를 컴퓨터에 띄워 스마트폰 영상을 보여주고, 차를 몰게 하고, 코인을 사고팔게 하고 있다.
그리고 그 실험 대부분이 대학이나 연구소가 아니라 **깃허브**를 통해 알려지고 있다.

기사를 읽고 실제 리포지토리를 찾아가 README 와 결과표를 직접 읽었다. 이 글은 그 기록이다.
**데이터가 어디서 왔는지, 개발자들이 무엇을 만들었는지, 그리고 "초파리 뇌가 운전한다" 는 말을 어디까지 믿어도 되는지.**

---

## TL;DR

- 2026-09-03, 수컷 초파리 **중추신경계 전체**(뇌 + 복부신경삭) 커넥톰 **MaleCNS** 논문이
  [Cell 에 실렸다](https://doi.org/10.1016/j.cell.2026.08.015). 프리프린트 기준 **뉴런 166,691 개, 세포 유형 11,691 개**.
- 2024 년 암컷 초파리 **뇌** 커넥톰 **FlyWire** 가 [Nature](https://doi.org/10.1038/s41586-024-07558-y) 에 먼저 나왔다
  (뉴런 139,255 개, 화학 시냅스 약 5,000 만 개).
- 개발자 프로젝트의 공통 구조: **배선(누가 누구와 연결되는가)은 측정값 그대로**, 입력·출력 연결과 학습 규칙은 **사람이 설계**.
- 믿을 만한 프로젝트는 **대조군**을 둔다. 같은 조건에서 배선만 무작위로 섞은 가짜 뇌와 성능을 비교하는 것이다.
  이 비교가 없으면 "초파리 뇌라서 됐다" 는 말은 증명된 게 아니다.

---

## 1. 데이터 — MaleCNS 와 FlyWire

커넥톰은 전자현미경으로 뇌를 얇게 잘라 찍고, 그 이미지에서 뉴런 하나하나와 시냅스를 재구성한 배선도다.

| | FlyWire (FAFB) | MaleCNS |
|---|---|---|
| 대상 | 성체 암컷 **뇌** | 성체 수컷 **중추신경계 전체** (뇌 + 복부신경삭) |
| 규모 | 뉴런 139,255 개, 화학 시냅스 약 5×10⁷ 개 | 뉴런 166,691 개, 세포 유형 11,691 개 |
| 논문 | Dorkenwald et al., *Nature* (2024) | *Cell* (2026-09), 프리프린트 bioRxiv (2025) |
| 공식 사이트 | [flywire.ai](https://flywire.ai/) | [male-cns.janelia.org](https://male-cns.janelia.org/) |

FlyWire 수치는 [Nature 논문 초록](https://doi.org/10.1038/s41586-024-07558-y)에,
MaleCNS 수치는 [bioRxiv 프리프린트 초록](https://www.biorxiv.org/content/10.1101/2025.10.09.680999v2)에 나온다.
MaleCNS 공식 사이트에 따르면 v1.0 데이터는 **2026-06-08** 에 공개됐고, 논문은 **2026-09-03** 에 출판됐다.
데이터는 프로젝트 사이트의 [다운로드 페이지](https://male-cns.janelia.org/download/)와 neuPrint 에서 받을 수 있다.

MaleCNS 논문의 본래 주제는 게임이 아니라 **성적 이형성**이다. 프리프린트 초록에 따르면 수컷과 암컷 뇌를
시냅스 해상도로 비교해 **동형 7,205 유형, 이형 114 유형, 수컷 특이 262 유형, 암컷 특이 69 유형**을 찾았고,
성 특이·이형 뉴런은 감각·운동 말단이 아니라 **고위 뇌 중추에 몰려 있었다.**

> 참고로 개발자 리포들이 적는 "2,560 만 개 연결" 은 시뮬레이션용 그래프의 **엣지 수**다.
> 논문이 세는 시냅스 수와 단위가 다를 수 있으니, 두 숫자를 바로 비교하지 않는다.

---

## 2. 출발점 — 커넥톰을 "돌리는" 모델

배선도 자체는 정적인 그래프다. 이것을 움직이게 한 대표적인 연구가
Shiu et al. [*A Drosophila computational brain model reveals sensorimotor processing*](https://doi.org/10.1038/s41586-024-07763-9)
(Nature, 2024)이다.

- FlyWire 배선도와 신경전달물질 정보만으로 뇌 전체를 **LIF(leaky integrate-and-fire)** 모델로 만들었다.
- 모델에서 **단맛·물 감지 미각 뉴런을 활성화하면**, 실제로 맛에 반응하고 섭식 개시에 필요한 뉴런들을 정확히 예측했다.
- 모델의 예측을 **광유전학 실험과 행동 실험으로 검증**했다.

코드는 [philshiu/Drosophila_brain_model](https://github.com/philshiu/Drosophila_brain_model) 에 공개돼 있고
(MIT, ⭐344), 이후 나온 많은 개발자 프로젝트가 이 모델을 기반으로 하거나 이 방식을 참고했다.

---

## 3. 기사에 나온 프로젝트들 — 리포를 직접 확인했다

> ⭐ 숫자는 2026-09-25 오전 GitHub API 로 잰 값이다.

### 3.1 초파리가 운전한다 — `suanmiao/fly-self-driving`

기사가 캡처로 소개한 리포다. [github.com/suanmiao/fly-self-driving](https://github.com/suanmiao/fly-self-driving) (MIT)

README 가 밝히는 구조는 기사보다 훨씬 구체적이다.

- **측정값:** MaleCNS 의 뉴런 165,122 개와 연결 25,563,197 개. 누가 누구와 연결되는지(인접 행렬)는 **절대 바뀌지 않는다.**
- **학습값:** 시냅스마다 이득(gain) 하나, 뉴런마다 누설(leak) 하나, 총 25,728,319 개 파라미터. 전부 초파리 배선 안에서만 존재한다.
- **설계 후 고정:** 64×32 픽셀 앞유리 화면을 시각엽 감각 뉴런 **4,114 개**에 무작위로 연결하는 사상, 복부신경삭 운동 뉴런
  **708 개**를 조향각으로 바꾸는 무작위 판독.
- **학습 방법:** 전문가 운전 정책을 따라 하도록 먼저 학습(behaviour cloning)하고, 이어서
  [DAgger](https://arxiv.org/abs/1011.0686)(Ross et al., 2011)로 세 번 보정한다. H100 한 장으로 약 35 분.

기사의 "60 번 중 58 번 완주, 충돌 없음" 은 README 의 결과와 일치한다. 학습에 쓰지 않은 도로 20 개씩 세 세트에서
20·19·19 번 완주했고, 차량 충돌은 없었다. 그런데 **결과표 전체를 봐야 제대로 읽힌다.**

| 모델 (교통 있음, 20 개 도로) | 완주 |
|---|---|
| 전문가 (실제 상태를 읽음) | 20 |
| 선형 모델, 파라미터 1,153 개 | 12 |
| MLP, 은닉층 40, 파라미터 4.6 만 개 | 18 |
| 초파리 커넥톰, behaviour cloning 만 | 12 |
| **초파리 커넥톰 + DAgger ×3** | **20 · 19 · 19** |
| 같은 방법, **배선을 무작위로 섞은 그래프** | 16 |

기사도 짚었듯 무작위 배선이 16/20 으로 더 낮다. 실제 배선 구조가 도움이 됐을 가능성을 보여 주는 결과다.
다만 동시에 **파라미터 4.6 만 개짜리 작은 MLP 가 18/20** 을 냈다. 초파리 뇌가 이 과제에 특별히 뛰어나다는 뜻은 아니고,
"측정된 배선이라는 제약 안에서도 학습이 된다" 에 가깝다. README 도 한계를 적어 두었다.
**아직 브레이크를 밟지 못하고, 조건마다 학습 시드가 하나뿐이다.**

흥미로운 발견이 하나 더 있다. 원래 레시피는 결정할 때마다 신경 상태를 초기화했는데, **초기화하지 않고 이어 가게 바꾸자**
첫 과제에서 같은 그래프의 성공이 20 개 중 3 개에서 17 개로 뛰었다. README 의 표현으로는 *"진짜 파리는 리셋하지 않는다."*

이 프로젝트는 Mark Unthank 의 [MarkUnthank/flyhard](https://github.com/MarkUnthank/flyhard) (MIT, ⭐82)를 재현하면서 시작했다.
커넥톰 기반 초파리가 CARLA 시뮬레이터에서 운전대를 조작하도록 학습시킨 프로젝트다. README 에 따르면
Kylon 워크스페이스의 **에이전트들이 25 달러 미만의 GPU 비용으로** 만들었다(기사의 "AI 를 활용해 25 달러도 안 되는 비용").

### 3.2 초파리가 코인을 산다 — `nftechie/stonkfly`

기사가 소개한 Stonkfly 는 [github.com/nftechie/stonkfly](https://github.com/nftechie/stonkfly) (MIT, ⭐819) 에 있다.
이름과 README 의 수치(시각 입력 3,335 개, 도파민 세포 15 개)가 기사와 일치한다.

- 코인베이스 공개 시세를 **RGB 차트 이미지**로 바꿔 밝기 입력 3,335 개와 R8 색 입력 811 개를 자극한다.
- 그래프는 **MaleCNS v1.0 전체(뉴런 166,700 개, 연결 2,560 만 개)**.
- 고정된 신경 판독이 매수·매도·보유를 제안하고, Coinbase AgentKit 으로 만든 액션 프로바이더가 한도를 검사한 뒤 현물 주문을 낸다.
- 포트폴리오가 이익이면 **PAM11 도파민 세포 15 개**, 손실이면 **PPL101 혐오 도파민 세포 2 개**를 자극한다.

README 가 스스로 적은 한계가 눈에 띈다.

> **수익을 내는 학습은 입증되지 않았다.** 보상 신호는 사람이 설계한 것이고 모델링된 통증 수용체가 아니다.
> 시냅스가 바뀐다고 해서 거래를 배운다는 뜻은 아니다.

기본값은 **모의 거래(잔고 100 달러)**이고, 실거래를 켜려면 사용자가 **최대 100 USDC** 의 전용 포트폴리오와 **출금 권한이 없는**
API 키를 직접 만들어야 한다. 주문당 최대 10 달러, 하루 24 회, 공매도·레버리지 없음. 20 달러 손실에서 신규 주문을 멈추지만
**보유분을 청산하거나 추가 손실을 막아 주지는 않는다**고 명시돼 있다. 실험을 대하는 태도가 성숙하다.

### 3.3 초파리가 쇼트폼을 본다 — FlyTok

기사에 따르면 휴대전화 화면(90×160 픽셀)을 시각 뉴런 3,335 개에 넣고, 영상이 넘어갈 때마다 도파민 뉴런 15 개를 자극해
화면을 쓸어 올리는 동작을 반복하게 만든 풍자 프로젝트다.

**공식 깃허브 리포는 찾지 못했다.** `flytok` 이름으로 검색되는 리포들은 설명이 없거나 무관한 것이어서 여기 링크하지 않는다.
비슷한 발상의 공개 리포로는 MaleCNS 기반 영상 피드 실험인
[ranagwho/Fruitfly-Doomscroller](https://github.com/ranagwho/Fruitfly-Doomscroller) (MIT, ⭐13, "FlyScroll")가 있다.
모델링된 시각·버섯체(mushroom body) 활동이 다음 영상으로 넘길 시점에 영향을 주는 구조다.

---

## 4. 기사에 없던 프로젝트들

기사 이후로도 목록은 계속 늘고 있다. 가장 잘 정리된 곳은 큐레이션 리스트
[cobanov/awesome-fly](https://github.com/cobanov/awesome-fly) (CC0, ⭐609)다. 이 리스트는 항목마다
**"전체 그래프인지 회로 일부인지", "무엇이 학습되고 무엇이 고정인지"** 를 굵게 표시한다.

| 프로젝트 | 내용 | 결과에 대해 스스로 밝힌 것 |
|---|---|---|
| [nftechie/doomfly](https://github.com/nftechie/doomfly) (⭐398) | MaleCNS 시뮬레이션이 Doom 을 한다 | **학습으로 생존하는 것은 입증되지 않음.** v6 후보가 시각·조건화·생존 검증을 모두 통과하지 못했고, 실패 결과를 리포에 포함 |
| [SpikeCalls/FlyDrones](https://github.com/SpikeCalls/FlyDrones) (⭐230) | 카메라 → 초파리 눈 → 스파이킹 뇌 → 하행 뉴런 → 드론 | — |
| [nftechie/flm](https://github.com/nftechie/flm) (⭐92) | 고정된 언어 모델을 MaleCNS 커넥톰에 결합해 대화 | — |
| [Kisame76/drosophila-brain-mlx](https://github.com/Kisame76/drosophila-brain-mlx) (⭐2) | Shiu 모델의 Apple MLX/Metal 포팅 | **아무것도 학습하지 않음.** 단맛 입력에 운동뉴런 MN9 가 약 67 Hz 로 발화하지만, 연결 수만 같게 섞은 배선에서는 5 개 시드 모두 **침묵** |

마지막 항목이 특히 좋다. 학습이 전혀 없으니 결과는 **순수하게 배선에서** 나온다. 같은 입력이 실제 배선에서는
운동 뉴런까지 가고, 섞은 배선에서는 가지 않는다. 대조군이 어떤 역할을 하는지 가장 깔끔하게 보여 주는 예다.

데이터를 직접 다루고 싶다면 R 패키지 [natverse/malecns](https://github.com/natverse/malecns) (GPL-3.0)가
Janelia FlyEM 최신 데이터셋 접근을 제공한다.

---

## 5. 읽는 법 — "초파리 뇌가 운전한다" 를 어디까지 믿을까

이 프로젝트들을 볼 때 세 가지를 확인하면 과장과 실제를 구분할 수 있다.

1. **무엇이 측정값이고, 무엇이 설계값인가.** 배선은 측정값이지만 뉴런 동역학(LIF, rate 모델), 화면을 뉴런에 잇는 방식,
   출력을 행동으로 바꾸는 판독, 보상 신호는 전부 사람이 정했다. doomfly README 의 표현대로
   *"이것은 재구성된 살아 있는 파리 뇌 그 자체가 아니다."*
2. **무엇이 학습되는가.** fly-self-driving 은 시냅스 이득 2,570 만 개를 역전파로 학습한다. 배선이 고정이어도 이 정도
   파라미터면 많은 것을 맞출 수 있다. 반대로 MLX 포팅처럼 아무것도 학습하지 않는 경우도 있다. 둘은 전혀 다른 주장이다.
3. **대조군이 있는가.** 무작위 배선, 작은 MLP, 선형 모델과 비교했는가? 비교했다면 차이가 얼마인가?
   fly-self-driving 은 무작위 배선보다 낫지만 작은 MLP 와는 비슷하다. **이 두 비교를 같이 보여 준다는 점이
   오히려 이 리포를 믿게 만든다.**

---

## 마무리

기사가 짚은 흐름은 사실이다. 과학 데이터가 공개되자 연구실 바깥의 개발자들이 곧바로 그것을 재료로 쓰기 시작했다.
그리고 AI 에이전트 덕분에 그 비용이 수십 달러 수준으로 떨어졌다.

리포들을 직접 읽으며 더 인상적이었던 건 따로 있다. **잘 만든 프로젝트일수록 실패와 한계를 먼저 적는다.**
Stonkfly 는 "수익 학습은 입증되지 않았다" 를, doomfly 는 "생존 학습은 입증되지 않았다" 를 README 첫머리에 적었다.
fly-self-driving 은 자기 결과보다 좋은 MLP 결과까지 표에 넣었다. 재미로 시작한 실험이지만, 태도는 과학 논문에 가깝다.

---

## References

**1차 출처 (논문·공식 데이터)**
- Berg et al., "Sexual dimorphism in the complete Drosophila male central nervous system connectome", *Cell* (2026) — [doi:10.1016/j.cell.2026.08.015](https://doi.org/10.1016/j.cell.2026.08.015) · [bioRxiv 프리프린트](https://www.biorxiv.org/content/10.1101/2025.10.09.680999v2)
- MaleCNS 공식 프로젝트 — [male-cns.janelia.org](https://male-cns.janelia.org/) · [Download](https://male-cns.janelia.org/download/)
- Dorkenwald et al., "Neuronal wiring diagram of an adult brain", *Nature* (2024) — [doi:10.1038/s41586-024-07558-y](https://doi.org/10.1038/s41586-024-07558-y) · [flywire.ai](https://flywire.ai/)
- Shiu et al., "A Drosophila computational brain model reveals sensorimotor processing", *Nature* (2024) — [doi:10.1038/s41586-024-07763-9](https://doi.org/10.1038/s41586-024-07763-9)
- Ross, Gordon, Bagnell, "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning" (DAgger), AISTATS 2011 — [arXiv:1011.0686](https://arxiv.org/abs/1011.0686)

**GitHub 리포지토리 (README 기준, 2026-09-25 확인)**
- [suanmiao/fly-self-driving](https://github.com/suanmiao/fly-self-driving) · [MarkUnthank/flyhard](https://github.com/MarkUnthank/flyhard)
- [nftechie/stonkfly](https://github.com/nftechie/stonkfly) · [nftechie/doomfly](https://github.com/nftechie/doomfly) · [nftechie/flm](https://github.com/nftechie/flm)
- [philshiu/Drosophila_brain_model](https://github.com/philshiu/Drosophila_brain_model) · [Kisame76/drosophila-brain-mlx](https://github.com/Kisame76/drosophila-brain-mlx)
- [SpikeCalls/FlyDrones](https://github.com/SpikeCalls/FlyDrones) · [ranagwho/Fruitfly-Doomscroller](https://github.com/ranagwho/Fruitfly-Doomscroller)
- [cobanov/awesome-fly](https://github.com/cobanov/awesome-fly) · [natverse/malecns](https://github.com/natverse/malecns)

**보도**
- 농민신문, 「틱톡부터 운전·코인까지…개발자들의 기상천외 '가상 초파리' 실험」 (2026-09-23) — [nongmin.com](https://www.nongmin.com/article/20260923500406)
