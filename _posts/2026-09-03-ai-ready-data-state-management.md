---
layout: post
title: "AI ready data 는 형용사가 아니다 — 목적성과 품질성으로 본 데이터 상태관리"
date: 2026-09-03 18:27:11 +0900
categories: [data]
tags: [ai-ready-data, data-quality, data-governance, iso-5259, eu-ai-act, tfdv, delta-lake]
---

"이 데이터 AI ready 야?" 라는 질문에는 함정이 하나 있다. 질문의 형태가 예/아니오를
요구하기 때문에, 답하는 쪽은 데이터가 **가진 성질**을 답하게 된다. 그런데 지금
표준과 법이 실제로 규정하는 readiness 는 데이터의 성질이 아니다. 데이터와 목적
사이의 **관계**이고, 관계는 시점에 따라 바뀐다. 바뀌는 관계를 다루는 이름은
품질검사가 아니라 **상태관리**다.

이 글은 그 주장을 1차 자료로 받친다. 결론부터 적으면 이렇다.

> `ready` 는 술어다. $\mathrm{ready}(D)$ 가 아니라 $\mathrm{ready}(D, P, t)$ —
> 데이터셋 $D$ 가 목적 $P$ 에 대해 시점 $t$ 에 승인된 상태인가.
> 인자 $P$ 를 빼먹는 순간 그 문장은 검증할 수 없는 문장이 된다.

## 1. 법이 이미 품질을 목적에 묶어 놨다

EU AI Act 10조는 고위험 AI 시스템의 학습·검증·시험 데이터에 대한 품질 요건을
규정한다. 여기서 눈여겨볼 것은 요건의 목록이 아니라 요건에 붙은 **한정구**다.

10조 3항은 데이터셋이 "relevant, sufficiently representative, and to the best
extent possible, free of errors and complete **in view of the intended purpose**"
여야 한다고 적는다([EU AI Act Art. 10, European Commission AI Act Service
Desk](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-10)). 오류가
없어야 한다는 요구조차 절대적으로 걸리지 않는다. *의도된 목적에 비추어* 걸린다.

같은 조문의 다른 항들도 전부 같은 방향이다.

- 2항: 데이터 거버넌스 관행은 "appropriate for the **intended purpose** of the
  high-risk AI system" 이어야 한다.
- 2항 (b): 개인정보라면 "the **original purpose** of the data collection" 을
  기록해야 한다. 수집 당시의 목적이 데이터에 따라다닌다.
- 2항 (d): "the information that the data are **supposed to measure and
  represent**" 에 대한 가정을 명문화하라고 요구한다.
- 4항: 데이터셋은 시스템이 쓰일 "geographical, contextual, behavioural or
  functional setting" 의 특성을 반영해야 한다.
- 6항: 모델 학습을 하지 않는 시스템이면 이 요건들은 **시험 데이터에만** 걸린다.

6항이 특히 결정적이다. 같은 데이터라도 시스템이 그것을 어떻게 쓰느냐에 따라
적용되는 품질 요건 자체가 달라진다. 법조문이 "데이터의 품질" 이라는 절대적 속성을
상정하지 않는다는 뜻이다.

## 2. 표준도 같은 말을 오래전부터 하고 있었다

ISO/IEC 25012:2008 은 데이터 품질 모델을 정의하면서 품질 속성을 **15개
characteristic** 으로 나누고, 이를 **inherent** 와 **system dependent** 라는 두
관점으로 본다. 그리고 이 문서는 "Data quality characteristics will be of varying
importance and priority to different stakeholders" 라고 못박는다
([ISO/IEC 25012:2008](https://www.iso.org/standard/35736.html)).

이 두 관점이 정확히 우리가 뒤섞어 쓰는 두 축이다.

| 축 | ISO/IEC 25012 의 관점 | 무엇을 묻나 | 누가 답할 수 있나 |
|---|---|---|---|
| **품질성** (내재) | inherent | 값 자체가 맞나 — 정확성·완전성·일관성 | 데이터만 보면 판정 가능 |
| **품질성** (시스템) | system dependent | 시스템이 그 품질을 유지·제공하나 — 가용성·이식성·복구성 | 저장·처리 환경을 봐야 판정 가능 |
| **목적성** | (품질 특성마다 붙는 "in a specific context of use" 조건) | 이 목적에 이 정도면 충분한가 | **데이터만 봐서는 절대 못 답한다** |

세 번째 줄이 핵심이다. 25012 의 개별 특성 정의들은 "in a specific context of use"
라는 조건을 달고 서술된다. 즉 표준은 애초에 맥락 없는 품질 판정을 정의하지 않는다.
그런데 실무의 "데이터 정제 완료" 는 거의 언제나 첫 줄만 보고 선언된다.

2024–2025 년에 나온 ISO/IEC 5259 시리즈는 이걸 AI 맥락으로 끌어온다. 다섯 부로
나뉘는데, 나뉜 방식 자체가 이 글의 논지와 같다.

| 파트 | 제목 | 다루는 것 |
|---|---|---|
| [5259-1:2024](https://www.iso.org/standard/81088.html) | Overview, terminology, and examples | 용어·프레임 |
| [5259-2:2024](https://www.iso.org/standard/81860.html) | Data quality measures | 무엇을 **잰다**  |
| [5259-3:2024](https://www.iso.org/standard/81092.html) | Data quality management requirements and guidelines | 어떻게 **관리**한다 |
| [5259-4:2024](https://www.iso.org/standard/81093.html) | Data quality process framework | 어떤 **프로세스**로 |
| [5259-5:2025](https://www.iso.org/standard/84150.html) | Data quality governance framework | 누가 **승인**하나 |

측정(2) 과 관리(3)·프로세스(4)·거버넌스(5) 를 굳이 갈라 놓은 이유가 있다. 재는 것만으로는
아무것도 안 바뀌기 때문이다. ISO 카탈로그에 따르면 5259-2 는 ISO/IEC 25012 와 ISO 8000
위에 세워졌다 — 25012 의 "context of use" 전제가 AI 데이터 품질로 그대로 상속됐다는 뜻이다.

## 3. 목적을 빼면 무슨 일이 나는가 — Data Cascades

여기까지가 규범이라면, 실증은 구글 리서치의 CHI 2021 논문이 제공한다. Sambasivan 등은
인도·동아프리카·서아프리카·미국의 고위험 도메인 AI 실무자 **53명**을 인터뷰해서
*data cascade* — 상류의 데이터 문제가 하류에서 복리로 터지는 현상 — 을 정의하고 측정했다.

- 응답자의 **92%** 가 최소 한 번의 cascade 를 경험했다.
- **45.3%** 는 한 프로젝트에서 두 건 이상을 겪었다.

([Sambasivan et al., CHI '21](https://doi.org/10.1145/3411764.3445518))

논문이 든 예가 이 글의 주제를 그대로 보여준다. 안질환 검출 모델을 **잡음 없는 학습
데이터**로 훈련해서 모델 성능을 높였는데, 운영에서 이미지에 먼지가 조금 앉자 예측에
실패했다. 학습 목적(정확도 최대화)에 대해서는 완벽하게 ready 였던 데이터가, 배포
목적(현장 촬영 이미지에서의 검출)에 대해서는 ready 가 아니었다. 데이터는 그대로인데
목적이 바뀌자 상태가 뒤집힌 것이다.

논문이 짚은 구조적 원인도 정확히 상태관리의 부재다. 저자들은 실무에서 쓰이는 지표가
"system-level proxy metrics ... which are only available towards the end of the
development lifecycle" 이라고 지적한다. 상류에서 상태를 판정할 수단이 없으니, 문제는
하류에서만 보이고, 그때는 이미 복리로 불어나 있다.

논문의 제목이 된 인터뷰 인용 — 실무자 한 명의 말 — 이 이 상황의 인센티브를 요약한다:
"Everyone wants to do the model work, not the data work."

## 4. 그래서 상태기계다

상태관리로 옮긴다는 건 대시보드를 하나 더 만든다는 뜻이 아니다. 세 가지를 갖춘다는 뜻이다.

1. **상태가 명시적으로 정의돼 있다.** 파일명이나 폴더 이름이 아니라, 조회 가능한 값으로.
2. **전이에 게이트가 있다.** 게이트를 통과하지 못하면 다음 상태로 못 간다 — 경고가 아니라 차단.
3. **전이가 기록되고 되돌릴 수 있다.** 누가 언제 무슨 근거로 승인했는지, 그리고 이전 상태로 복귀 가능한지.

### 4.1 전이 게이트 — 스키마를 계약으로

구글의 TFX 데이터 검증 시스템이 이 구조의 참고 구현이다. Breck 등은 ML 파이프라인에
들어가는 데이터의 이상을 잡는 시스템을 기술하면서, 기대되는 데이터 특성을
**스키마**(feature 별 type·domain·valency 제약)로 코드화하고, 배치가 들어올 때마다
그 스키마와 대조한다([Breck et al., SysML/MLSys 2019](https://proceedings.mlsys.org/paper_files/paper/2019/file/928f1160e52192e3e0017fb63ab65391-Paper.pdf)).
논문에 따르면 이 시스템은 TFX 의 일부로 운영에 배포돼 수백 개 제품 팀이 쓰고 있고,
하루 수 페타바이트 규모의 운영 데이터를 지속적으로 검증한다.
(구글 저자들의 자기 시스템 기술이며, 동료심사를 거친 SysML 게재 논문이다.)

이 시스템에서 가장 중요한 설계는 이상 탐지 자체가 아니다. **이상이 잡혔을 때 무엇을
하는가**다. 후속 논문의 워크플로 기술을 보면, 사용자는 이상을 보고 두 갈래 중 하나를
고른다 — *데이터의 오류를 고치거나*, 아니면 그 이상이 데이터의 자연스러운 진화(예:
범주형 feature 에 새 값이 정당하게 추가됨)라고 판단해 **스키마를 갱신한다**
([Caveness et al., SIGMOD '20 demo](https://doi.org/10.1145/3318464.3384707)).

이게 상태기계의 본질이다. 전이 실패는 자동으로 해소되지 않는다. 두 방향의 해소가
가능하고, **어느 쪽인지는 사람이 목적에 비추어 결정한다.** 그리고 그 결정은 스키마라는
버전 관리되는 산출물에 남는다. 결정이 남지 않으면 다음 사람은 같은 판단을 처음부터 다시 한다.

학습과 서빙 사이의 어긋남(training-serving skew)도 같은 논문이 세 갈래로 나눈다.
그중 *feature skew* 의 한 형태로 저자들이 "time travel" 이라 부르는 현상이 있다.
feature 값을 고정되지 않은 소스(예: 클릭 수가 계속 쌓이는 DB)에 질의해서 만들면,
학습 데이터를 생성하는 시점에는 서빙 시점 이후에 발생한 클릭까지 포함돼 값이 부풀려진다.
데이터가 "틀린" 게 아니다. **어느 시점의 상태를 찍었느냐**가 목적과 어긋난 것이다.

분포 어긋남은 임계값으로 판정하는데, TFDV 는 이를 $L_\infty$ 거리로 잰다:

$$
d_\infty(p, q) \;=\; \max_{i} \; \bigl| p_i - q_i \bigr|
$$

논문이 KL divergence 대신 이걸 고른 이유가 실무적으로 중요하다. 제품 팀이 지표의
자연스러운 의미를 이해하지 못하면 **임계값을 조정할 수 없고**, 조정할 수 없는 게이트는
오탐을 내다가 결국 꺼진다. 꺼진 게이트는 없는 게이트다.

### 4.2 되돌릴 수 있어야 상태다

상태를 관리한다면서 이전 상태로 못 돌아가면 그건 상태가 아니라 그냥 현재값이다.
Delta Lake 논문(Databricks 저자, 동료심사 VLDB 게재)은 이 문제를 트랜잭션 로그로 푼다.
데이터 객체와 로그가 불변이라 과거 스냅샷을 그대로 질의할 수 있고, SQL 로
`AS OF timestamp` / `VERSION AS OF commit_id` 를 지원한다
([Armbrust et al., PVLDB 13(12):3411–3424, 2020](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf)).

논문이 명시적으로 드는 동기 중 하나가 ML 이다 — "some workloads, such as machine
learning training, require faithfully reproducing an old version of the data".
그리고 저자들은 MLflow 가 이 API 로 **학습에 사용된 테이블 버전을 자동 기록**한다고
적는다. 모델과 데이터 스냅샷이 커밋 ID 로 묶이는 것이다.

이게 없으면 "이 모델은 어느 상태의 데이터로 만들어졌나" 라는 질문에 답할 수 없다.
답할 수 없으면 사고가 났을 때 데이터 문제인지 모델 문제인지 가를 수 없다.

### 4.3 상태는 데이터와 함께 이동해야 한다

상태를 사내 위키에만 적으면, 데이터가 팀·조직·리포지토리를 건너가는 순간 상태가 소실된다.
데이터는 남고 목적은 증발한다. 이 문제를 정면으로 다루는 게 데이터 문서화 표준들이다.

Gebru 등의 *Datasheets for Datasets* 는 전자부품 데이터시트에 빗대어, 모든 데이터셋에
문서를 동봉하자고 제안한다. 질문 묶음이 데이터셋 생애주기 단계에 맞춰 나뉜다 —
motivation, composition, collection process, preprocessing/cleaning/labeling,
uses, distribution, maintenance
([Gebru et al., CACM, 2021](https://cacm.acm.org/research/datasheets-for-datasets/)).

그리고 **첫 번째 질문**이 이것이다:

> "For what purpose was the dataset created? Was there a specific task in mind?
> Was there a specific gap that needed to be filled?"

목적을 맨 앞에 두는 건 우연이 아니다. 목적을 모르면 나머지 답을 해석할 수 없기 때문이다.

기계가 읽을 수 있는 형태로는 MLCommons 의 **Croissant** 가 있다. 이름 자체가
"ML-Ready Datasets" 를 위한 메타데이터 포맷이고, schema.org 의 Dataset 어휘 위에서
네 개 층 — Dataset Metadata / Resource / Structure / ML Semantics — 으로 구성된다.
논문 기준으로 Hugging Face Datasets · Kaggle Datasets · OpenML 세 저장소에 통합돼
**40만 개 이상**의 데이터셋을 이 형식으로 기술하고 있고, NeurIPS Datasets and
Benchmarks 트랙이 데이터 아티팩트로 권장한다
([Akhtar et al., NeurIPS 2024 D&B](https://proceedings.neurips.cc/paper_files/paper/2024/file/9547b09b722f2948ff3ddb5d86002bc0-Paper-Datasets_and_Benchmarks_Track.pdf)).

여기서 실무적으로 중요한 대목: Croissant 통합이 세 저장소에서 쉽게 된 이유를 논문은
"does not require changing the existing data layout" 이라고 설명한다. 상태·목적
메타데이터를 붙이는 일은 데이터 레이아웃을 갈아엎는 일이 아니다. 그동안 안 붙인 건
비용 때문이 아니었다는 뜻이기도 하다.

## 5. 최소한의 상태 설계

위 자료들을 실제 설계로 접으면 이런 모양이 된다. 상태 이름은 조직마다 달라도 되지만,
**목적이 상태의 일부**라는 점은 바뀌면 안 된다.

| 상태 | 의미 | 다음 상태로 가는 게이트 |
|---|---|---|
| `raw` | 수집 원본. 손대지 않음 | 출처·수집 목적·수집 시점이 기록됐는가 (AI Act 10(2)(b)) |
| `conformed` | 스키마·타입·도메인 통과 | 스키마 대조 통과 (TFDV 류). 실패 시 데이터 수정 **또는** 스키마 갱신을 사람이 결정 |
| `purpose-bound(P)` | **목적 P 에 한해** 적합 판정 | P 에 대한 대표성·편향 검토 (AI Act 10(2)(f)(g)), 가정 명문화 (10(2)(d)) |
| `serving-approved(P)` | P 로 운영 투입 승인 | 학습-서빙 분포 어긋남 임계 이내, 승인자 기록 (ISO/IEC 5259-5) |
| `quarantined` | 게이트 실패로 격리 | 원인 규명 + 재판정 |
| `retired` | 목적 소멸·보존기한 초과 | 스냅샷 보존 정책에 따라 조회 가능 기간 유지 |

핵심은 `purpose-bound(P)` 에 인자가 있다는 것이다. 같은 스냅샷이 `purpose-bound(사기탐지)`
이면서 동시에 `quarantined(신용평가)` 일 수 있다. 이걸 하나의 boolean 으로 접는 순간
두 목적 중 하나는 틀린 판정을 받는다.

## 6. 흔한 안티패턴 네 가지

**(1) 관측은 있는데 차단이 없다.** 데이터 품질 대시보드는 있지만 빨간불이 떠도
파이프라인은 그대로 돈다. 이건 상태관리가 아니라 사후 기록이다. 게이트는 막을 수
있어야 게이트다. 그리고 앞서 본 것처럼, 임계값을 사람이 이해하고 조정할 수 있어야
게이트가 꺼지지 않는다.

**(2) "정제 완료" 를 최종 상태로 둔다.** 목적 인자가 없는 종착 상태는 검증할 수 없다.
"무엇에 대해" 가 빠진 완료 선언은 다음 목적이 나타나는 순간 조용히 거짓이 된다.

**(3) 상태를 파일명에 적는다.** `final_v2_진짜최종.parquet` 은 상태가 아니라 소문이다.
조회 가능하고, 전이 이력이 남고, 롤백 가능한 값이어야 한다.

**(4) 스키마를 조용히 갱신한다.** TFDV 워크플로에서 스키마 갱신은 "이 변화는 오류가
아니라 정당한 진화" 라는 **판단**이다. 판단은 근거와 함께 남아야 한다. 커밋 메시지 없이
스키마를 고치는 건 승인 없이 상태를 전이시키는 것과 같다.

## 7. 정리

"AI ready data" 를 형용사로 쓰면 세 가지를 동시에 놓친다. 목적이 사라지고, 시점이
사라지고, 승인 주체가 사라진다. 세 개가 사라진 문장은 반증할 수 없고, 반증할 수 없는
품질 주장은 배포 후 하류에서 복리로 청구된다 — CHI 2021 이 92% 라고 센 그 현상이다.

문장을 바꾸면 설계가 바뀐다.

- ❌ "이 데이터는 AI ready 다."
- ✅ "이 **스냅샷**(커밋 ID)은 이 **목적**에 대해, 이 **게이트**를 통과해, 이 **시점**에,
  이 **주체**가 승인했다. 그리고 이전 상태로 되돌릴 수 있다."

두 번째 문장은 길다. 대신 각 항목이 전부 검증 가능하다. 그게 상태관리가 품질검사보다
비싼 이유이자, 비싼 값을 하는 이유다.

---

## References

**1차·공식 (규범)**

- European Commission, *AI Act Service Desk* — [Article 10: Data and data governance](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-10). Regulation (EU) 2024/1689.
- ISO/IEC 25012:2008, *Software engineering — Software product Quality Requirements and Evaluation (SQuaRE) — Data quality model*. [ISO 카탈로그](https://www.iso.org/standard/35736.html)
- ISO/IEC 5259 시리즈, *Artificial intelligence — Data quality for analytics and machine learning (ML)*:
  [Part 1:2024](https://www.iso.org/standard/81088.html) ·
  [Part 2:2024](https://www.iso.org/standard/81860.html) ·
  [Part 3:2024](https://www.iso.org/standard/81092.html) ·
  [Part 4:2024](https://www.iso.org/standard/81093.html) ·
  [Part 5:2025](https://www.iso.org/standard/84150.html)

**동료심사 논문**

- Sambasivan, N., Kapania, S., Highfill, H., Akrong, D., Paritosh, P., Aroyo, L. M. (2021).
  ["Everyone wants to do the model work, not the data work": Data Cascades in High-Stakes AI](https://doi.org/10.1145/3411764.3445518). *CHI '21*. DOI: 10.1145/3411764.3445518
- Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., Crawford, K. (2021).
  [Datasheets for Datasets](https://cacm.acm.org/research/datasheets-for-datasets/). *Communications of the ACM*.
  (프리프린트: [arXiv:1803.09010](https://arxiv.org/abs/1803.09010))
- Akhtar, M., Benjelloun, O., Conforti, C., et al. (2024).
  [Croissant: A Metadata Format for ML-Ready Datasets](https://proceedings.neurips.cc/paper_files/paper/2024/file/9547b09b722f2948ff3ddb5d86002bc0-Paper-Datasets_and_Benchmarks_Track.pdf).
  *NeurIPS 2024, Datasets and Benchmarks Track*, pp. 82133–82148.

**동료심사 논문 (벤더 저자 — 자사 시스템 기술)**

- Breck, E., Polyzotis, N., Roy, S., Whang, S. E., Zinkevich, M. (2019).
  [Data Validation for Machine Learning](https://proceedings.mlsys.org/paper_files/paper/2019/file/928f1160e52192e3e0017fb63ab65391-Paper.pdf). *SysML/MLSys 2019*. (Google)
- Caveness, E., Suganthan G. C., P., Peng, Z., Polyzotis, N., Roy, S., Zinkevich, M. (2020).
  [TensorFlow Data Validation: Data Analysis and Validation in Continuous ML Pipelines](https://doi.org/10.1145/3318464.3384707). *SIGMOD '20*. (Google)
- Armbrust, M., et al. (2020).
  [Delta Lake: High-Performance ACID Table Storage over Cloud Object Stores](https://www.vldb.org/pvldb/vol13/p3411-armbrust.pdf).
  *PVLDB* 13(12): 3411–3424. DOI: 10.14778/3415478.3415560 (Databricks)

**근거의 한계**

이 글은 "상태기계로 관리하면 사고가 줄어든다" 는 인과를 입증하지 않는다. 그런
중립적 헤드투헤드 실험은 찾지 못했다. 입증된 것은 (a) 규범이 품질을 목적에 묶어
정의한다는 사실, (b) 목적을 분리한 채 품질을 최적화했을 때 하류에서 실패가
관측된다는 CHI 2021 의 질적·비율 증거, (c) 대규모 운영에서 스키마 게이트와
스냅샷 버저닝이 실제로 배포돼 있다는 벤더 저자들의 보고까지다. 인용한 규모
수치(수 페타바이트/일, 40만 데이터셋 등)는 모두 해당 저자들의 자기 보고이며
제3자 재현 검증은 아니다.
