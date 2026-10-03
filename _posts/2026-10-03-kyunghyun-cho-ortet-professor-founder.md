---
layout: post
title: "조경현 교수의 Ortet 창업 — '사람'과 '교수라는 직업'으로 읽는 기술과 투자"
date: 2026-10-03 16:45:13 +0900
categories: [AI, Industry]
tags: [kyunghyun-cho, ortet, health-ai, foundation-model, thoreau, professor-founder, nyu, genentech]
---

![조경현 교수의 Ortet 출범 소개 글 (LinkedIn 캡처)](/assets/images/kyunghyun-cho-ortet-announcement.jpg)

*위 이미지: 조경현 교수가 LinkedIn 에 직접 올린 Ortet 출범 소개 글 캡처.*

2026년 9월 29일, 뉴욕대(NYU) 조경현(Kyunghyun Cho) 교수가 헬스케어 전용 프런티어 AI 연구소 **Ortet** 의 출범을 알렸다. 투자 측은 사모펀드 계열 헬스케어 투자사 **Thoreau** 이고, 발표된 규모는 **5억 달러($500M) "약정(commitment)"** 이다 ([BusinessWire 보도자료](https://www.financialcontent.com/article/bizwire-2026-9-29-ortet-launches-as-frontier-ai-lab-for-health-with-500-million-commitment-from-thoreau), [Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/ex-genentech-meta-aws-ai-leaders-launch-health-ai-lab-500m-backing)).

뉴스만 놓고 보면 "유명 AI 연구자가 큰돈을 받아 창업했다" 로 끝난다. 이 글은 같은 사건을 두 층으로 나눠 본다.

1. **사람** — 조경현이라는 연구자가 어떤 기술 궤적을 밟아 여기까지 왔고, 왜 하필 "건강" 인가.
2. **교수라는 직업** — 석좌교수가 수천억 원짜리 연구소의 CEO 를 겸한다는 것이 학계·산업에 무엇을 의미하는가.

그리고 각 층에서 **기술** 과 **투자** 를 따로 짚는다.

---

## 1. 사람: 어텐션의 공저자가 환자 모델로 오기까지

### 기술 궤적

조경현 교수의 이름은 현대 딥러닝 교과서에 두 번 나온다.

- **GRU / RNN 인코더-디코더** — Cho et al., *"Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine Translation"* (2014, [arXiv:1406.1078](https://arxiv.org/abs/1406.1078)). 가변 길이 시퀀스를 고정 벡터로 압축했다가 다시 풀어내는 인코더-디코더 구조와, LSTM 을 단순화한 게이트 순환 유닛(GRU)을 제안했다.
- **어텐션 메커니즘** — Bahdanau, Cho, Bengio, *"Neural Machine Translation by Jointly Learning to Align and Translate"* (2014, [arXiv:1409.0473](https://arxiv.org/abs/1409.0473)). 디코더가 매 시점 입력의 어느 부분을 볼지 스스로 "정렬" 하게 한 이 아이디어가 이후 트랜스포머의 핵심 연산으로 이어졌다.

즉 그는 오늘날 LLM 의 **뼈대 연산을 만든 쪽** 에 있었다. 그 뒤의 궤적은 언어에서 생명과학으로 옮겨 간다. 2021년 그가 공동창업한 신약 설계 AI 스타트업 **Prescient Design** 이 Genentech 에 합류했고, Genentech 은 그를 "NYU 부교수이자 Prescient Design 공동창업자·시니어 디렉터" 로 소개했다 ([Genentech, *Making Big Moves and Large Molecules*](https://www.gene.com/stories/making-big-moves-and-large-molecules); [Prescient Design 소개](https://www.gene.com/scientists/our-scientists/prescient-design)).

정리하면 **시퀀스 모델링 (2014) → 분자 설계 (2021~) → 환자 단위 건강 모델 (2026)** 이다. 다루는 대상이 단어에서 분자로, 분자에서 사람으로 커졌다.

### 왜 "건강" 인가 — 본인이 밝힌 동기

캡처한 LinkedIn 글에서 조 교수는 영주권 절차 중 받은 혈액검사가 계기가 되어 갑상선암을 발견한 경험을 직접 언급한다. 개인 병력은 본인이 공개적으로 쓴 범위까지만 옮긴다. 다만 이 일화는 Ortet 의 문제의식과 정확히 맞닿아 있다. **우연히 시스템에 걸려서 발견된 것** 이라는 점이다. 의료 데이터는 이미 쌓여 있지만, 그것이 한 사람의 건강을 *먼저* 알아채는 구조로 엮여 있지 않다는 문제다.

### 기술: Ortet 이 만들겠다는 것

Ortet 은 자사 사이트에서 목표를 **"Ortet Health Model"** 로 설명한다. 진료·청구·검사 같은 실제 의료 현장 데이터로 학습하고, 현장에 배치해 결과를 다시 학습으로 돌리는 **닫힌 학습 루프(closed learning loop)** 다 ([ortet.ai](https://ortet.ai/)). 보도자료는 Ortet 이 초기 GPU 클러스터를 이미 확보했다고 밝힌다 ([BusinessWire](https://www.financialcontent.com/article/bizwire-2026-9-29-ortet-launches-as-frontier-ai-lab-for-health-with-500-million-commitment-from-thoreau)).

창업팀 구성도 이 방향을 보여 준다 (보도자료 기준).

| 역할 | 인물 | 배경 |
| --- | --- | --- |
| CEO | 조경현 | NYU Glen de Vries 보건통계학 석좌교수, Prescient Design 공동창업 |
| Chairman | Jeff Hammerbacher | Facebook 초기 데이터팀, Cloudera 공동창업 |
| CAIO · CTO · CSO 등 | Choi(CAIO), Dwyer(CTO), Mansimov(CSO), Shi | Genentech·Meta·AWS 등 대형 바이오·테크 AI 조직 출신 (기사 제목 기준, 개인별 이력은 미확인) |

> 표의 직함·소속은 [BusinessWire 보도자료](https://www.financialcontent.com/article/bizwire-2026-9-29-ortet-launches-as-frontier-ai-lab-for-health-with-500-million-commitment-from-thoreau)와 [Fierce Healthcare](https://www.fiercehealthcare.com/ai-and-machine-learning/ex-genentech-meta-aws-ai-leaders-launch-health-ai-lab-500m-backing) 기사 기준이다. 세부 경력은 각 인물의 공개 프로필로 재확인하길 권한다.

기술적으로 눈여겨볼 지점은 **"범용 LLM 에 의료 데이터를 파인튜닝한다" 가 아니라 "환자 자체를 모델링한다"** 고 말한다는 것이다. 어텐션이 "입력 중 어디를 볼 것인가" 의 문제였다면, Ortet 의 문제는 "한 사람의 수년 치 기록 중 무엇이 지금의 위험을 말하는가" 이다. 형식은 같은 시퀀스 문제지만 데이터의 성질은 완전히 다르다. 결측이 많고, 기관마다 코드 체계가 다르고, 정답 레이블(결과)이 수년 뒤에 나온다.

### 투자: $500M 는 "누구 돈" 이고 무엇을 사는가

- **투자자 성격.** Thoreau 는 VC 가 아니라 헬스케어 서비스 기업을 사들여 키우는 투자 플랫폼이다. Axios 는 Thoreau 가 올해 Penelope 에 1억 달러를 투자했고, 6월에는 약 120억 달러 규모의 Ensemble Health Partners 인수에 참여했다고 보도했다. Thoreau 는 Matt Holt 가 이끈다 ([Axios Pro](https://www.axios.com/pro/health-tech-deals/2026/09/29/ortet-500m-commitment-thoreau)). 보도자료에 따르면 Ensemble 은 연간 550억 달러가 넘는 순환자매출(net patient revenue)의 수익주기관리(RCM)를 맡고 있다.
- **"약정" 이라는 단어.** 발표 문구는 "$500 million commitment" 다. 한 번에 입금되는 금액인지, 마일스톤에 따라 나뉘어 집행되는지(tranche)는 공개되지 않았다. 뉴스 제목의 "5억 달러 투자" 를 "5억 달러 현금 보유" 로 읽으면 안 된다.
- **자문.** 보도자료상 Goldman Sachs 가 거래 자문을 맡았다.

> **⚠️ 여기부터는 필자 해석이다.** Thoreau 산하에 Ensemble 같은 대형 RCM 사업자가 있다는 사실과, Ortet 이 "실제 현장 데이터로 학습하는 닫힌 루프" 를 내세운다는 사실을 나란히 놓으면, 이 투자가 **돈과 함께 데이터 접근 경로와 배포처를 같이 묶은 구조** 일 가능성을 읽을 수 있다. 다만 Ortet 이 Ensemble 데이터를 쓴다고 공식 발표한 자료는 확인하지 못했다. 이 연결은 추론이며, 실제로 데이터를 쓴다면 HIPAA 등 개인정보 규제 아래에서 어떻게 처리하는지가 핵심 검증 대상이 된다.

---

## 2. 교수라는 직업: 석좌교수가 CEO 를 겸한다는 것

### 기술 관점: 교수-창업자 모델의 두 번째 버전

조 교수에게 "교수이면서 창업자" 는 처음이 아니다. 2021년 Prescient Design 때도 NYU 교수 신분을 유지한 채 공동창업자로 Genentech 에 합류했다 ([Genentech](https://www.gene.com/stories/making-big-moves-and-large-molecules)). 2026년 보도자료는 그를 **"Glen de Vries Professor of Health Statistics"**, 즉 NYU 석좌교수로 소개하면서 동시에 Ortet 의 CEO 로 소개한다.

두 사례를 나란히 놓으면 차이가 보인다.

| | Prescient Design (2021) | Ortet (2026) |
| --- | --- | --- |
| 형태 | 스타트업 → 대형 제약사(Genentech) 편입 | 처음부터 독립 연구소, 단일 투자사 대규모 약정 |
| 교수의 역할 | 공동창업자·시니어 디렉터 | **CEO** |
| 연구 대상 | 분자(항체 등) 설계 | 환자 단위 건강 |
| 컴퓨트 | 모회사 인프라 | 자체 GPU 클러스터 확보 |

대학 연구실이 할 수 없는 일이 무엇인지가 이 표에 드러난다. **대규모 컴퓨트, 실제 임상 운영 데이터, 배포 후 피드백 루프.** 프런티어 모델 연구의 병목이 아이디어에서 데이터·컴퓨트로 옮겨 가면서, 교수는 연구 질문을 대학 밖으로 들고 나가야 그 질문을 풀 수 있게 됐다. 반대로 산업 쪽은 "어텐션의 공저자" 라는 학문적 신뢰를 산다. 이 교환이 교수-창업자 모델의 본질이다.

### 투자 관점: 투자자가 "교수" 에게서 사는 것

헬스케어 AI 에 대형 자본이 들어갈 때 가장 비싼 리스크는 기술보다 **신뢰** 다. 의료기관이 데이터를 내주고, 규제 당국이 결과를 받아들이고, 의사가 모델 출력을 쓰려면, 그 모델을 만든 사람이 학계 검증을 거친 사람이라는 사실이 중요하다. 석좌교수 직함은 그 신뢰의 담보물이다.

반대로 교수 입장에서 이 구조는 비용도 따른다.

- **이해상충.** 같은 사람이 NYU 에서 보건통계를 가르치고 연구하면서 영리 연구소의 CEO 를 맡는다. 대학의 겸직·이해상충 규정 안에서 어떻게 정리했는지는 공개 자료로 확인되지 않는다.
- **출판과 독점의 긴장.** 교수의 성과는 논문과 공개로 측정되고, $500M 를 넣은 투자자의 성과는 독점적 우위로 측정된다. "프런티어 AI 연구소(frontier AI lab)" 라는 명칭이 어느 쪽으로 기울지는 앞으로의 공개 정책이 보여 줄 것이다.
- **제자와 연구실.** 교수가 CEO 가 되면 연구실의 시간과 주의가 나뉜다. 학생에게는 산업 데이터에 접근할 기회일 수도, 지도 공백일 수도 있다.

### 한국 독자에게: 이 모델이 시사하는 것

한국 대학에도 교수 창업과 겸직 제도는 있다. 그러나 "석좌교수가 단일 투자사로부터 수천억 원 규모 약정을 받아 독립 연구소 CEO 를 맡는다" 는 규모의 사례는 흔치 않다. 차이는 개인 역량보다 **구조** 에서 온다. 미국에서는 (1) 대형 헬스케어 서비스 기업을 소유한 PE 자본이, (2) 그 기업들의 운영 데이터를 배경으로, (3) 학계 최상위 연구자에게 독립 연구소를 맡기는 3자 결합이 성립했다. 이 셋 중 하나라도 빠지면 같은 모델은 복제되지 않는다.

---

## 3. 한계와 면책

- **중립적 제3자 평가가 아직 없다.** Ortet 은 출범 직후라 모델·벤치마크·논문이 공개되지 않았다. 이 글의 기술 설명은 Ortet 공식 사이트와 보도자료, 즉 **회사 측 주장** 에 기반한다. "환자 모델" 이 실제로 무엇을 얼마나 잘하는지는 공개 결과가 나오기 전에는 판단할 수 없다.
- **투자 구조는 미공개다.** $500M 의 집행 방식, 지분 구조, Thoreau 포트폴리오사와의 데이터 계약 여부는 공개 자료에 없다. 위에서 Ensemble 과 연결한 부분은 필자 해석으로 명시했다.
- **개인 이야기의 범위.** 조 교수의 건강 관련 일화는 본인이 공개 게시물에 쓴 내용만 다뤘다.
- 본문의 "수천억 원" 은 규모 감을 위한 어림이며, 정확한 금액은 달러 표기($500M)를 기준으로 한다.

---

## References

1. BusinessWire (via FinancialContent), *"Ortet Launches as Frontier AI Lab for Health with $500 Million Commitment from Thoreau"*, 2026-09-29. <https://www.financialcontent.com/article/bizwire-2026-9-29-ortet-launches-as-frontier-ai-lab-for-health-with-500-million-commitment-from-thoreau> — 1차(회사 보도자료)
2. Fierce Healthcare, *"Ex-Genentech, Meta, AWS AI leaders launch health AI lab with $500M backing"*, 2026-09-30. <https://www.fiercehealthcare.com/ai-and-machine-learning/ex-genentech-meta-aws-ai-leaders-launch-health-ai-lab-500m-backing> — 업계 전문지
3. Axios Pro, *"Ortet lands $500M commitment from Thoreau"*, 2026-09-29. <https://www.axios.com/pro/health-tech-deals/2026/09/29/ortet-500m-commitment-thoreau> — 업계 전문지 (Thoreau 거래 이력)
4. Ortet 공식 사이트. <https://ortet.ai/> — 1차(회사 주장)
5. Genentech, *"Making Big Moves and Large Molecules"*. <https://www.gene.com/stories/making-big-moves-and-large-molecules> — 1차(Prescient Design 합류)
6. Genentech, *Prescient Design*. <https://www.gene.com/scientists/our-scientists/prescient-design>
7. Cho, K., van Merriënboer, B., Gulcehre, C., Bahdanau, D., Bougares, F., Schwenk, H., Bengio, Y. *"Learning Phrase Representations using RNN Encoder–Decoder for Statistical Machine Translation"*, EMNLP 2014. [arXiv:1406.1078](https://arxiv.org/abs/1406.1078)
8. Bahdanau, D., Cho, K., Bengio, Y. *"Neural Machine Translation by Jointly Learning to Align and Translate"*, ICLR 2015. [arXiv:1409.0473](https://arxiv.org/abs/1409.0473)
9. 조경현, LinkedIn 게시물 (본문 상단 캡처), 2026-09.
