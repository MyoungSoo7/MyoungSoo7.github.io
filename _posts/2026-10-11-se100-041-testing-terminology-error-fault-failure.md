---
layout: post
title: "[SE100 #041] 테스트 기본 용어 — 오류·결함·고장"
date: 2026-10-11 17:01:40 +0900
categories: [software-engineering]
tags: [se100, software-testing, terminology, defect, failure, dependability]
---

소프트웨어 공학 100 주제 시리즈의 41번째 글이다. (카테고리: 소프트웨어 테스팅)

## 한 줄 요약

사람이 **오류(error, mistake)** 를 저지르면 산출물에 **결함(defect, fault, bug)** 이 남고, 그 결함이 실행되어 기대와 다른 동작이 밖으로 드러나면 **고장(failure)** 이다. 셋을 구분해야 "테스트가 무엇을 찾는가", "왜 결함이 있어도 테스트가 통과하는가" 를 정확히 말할 수 있다. 단, 신뢰성 공학 쪽에서는 같은 단어 error 를 **시스템의 잘못된 내부 상태**라는 다른 뜻으로 쓴다는 점을 알아 둬야 한다.

## 왜 필요한가

장애 회고에서 이런 대화가 자주 나온다. "버그가 있었네요." "그 버그는 3년 전부터 있었는데요?" "그럼 왜 어제 터졌죠?" 이 대화가 꼬이는 이유는 한 단어(버그)로 세 가지 다른 것을 가리키기 때문이다.

- 3년 전 누군가 요구사항을 잘못 이해한 **행위**
- 그 결과 코드에 남은 **잘못된 문장**
- 어제 특정 입력이 들어와 사용자가 본 **잘못된 결과**

이 셋은 발생 시점도, 찾는 방법도, 막는 방법도 다르다. 행위는 교육·리뷰·명세 개선으로, 코드 속 결함은 정적 분석과 테스트로, 밖으로 드러난 고장은 모니터링과 장애 대응으로 다룬다. 단위 테스트와 통합 테스트의 기본은 [단위 테스트]({% post_url 2026-10-10-cs300-191-unit-testing %}) 글에서 다뤘으니, 여기서는 그 아래 깔린 어휘를 정밀하게 맞춘다.

## 핵심 개념

### ISTQB 의 사슬: 오류 → 결함 → 고장

국제 소프트웨어 테스팅 자격 위원회(ISTQB)의 [Foundation Level 강의계획서 v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) 1.2.3절은 이렇게 정의한다.

> 사람은 오류(error, mistake)를 저지르고, 그것이 결함(defect, fault, bug)을 만들며, 결함은 다시 고장(failure)으로 이어질 수 있다.

같은 절에서 중요한 단서가 이어진다.

- 결함은 코드에만 있지 않다. 요구사항 명세, 테스트 스크립트, 빌드 파일에도 있다.
- 결함이 실행되면 시스템은 해야 할 일을 하지 않거나 하지 말아야 할 일을 하여 **고장**이 난다. 어떤 결함은 실행되면 항상 고장을 내고, 어떤 결함은 특정 조건에서만, 어떤 결함은 **끝내 고장을 내지 않는다.**
- 고장의 원인이 오류와 결함만은 아니다. 방사선이나 전자기장이 펌웨어에 결함을 만드는 것처럼 **환경 조건**도 고장을 일으킨다.
- **근본 원인(root cause)** 은 문제 발생의 근본적 이유(예: 오류로 이어진 상황)이고, 근본 원인 분석으로 찾는다.

```
  사람                 산출물                   실행 / 관찰
 ┌───────┐  만든다   ┌─────────┐  실행되면   ┌──────────┐
 │ 오류  │ ───────▶ │  결함   │ ─(조건)──▶ │  고장    │
 │mistake│          │ defect  │            │ failure  │
 └───────┘          │fault/bug│            └──────────┘
     ▲              └─────────┘                 │
     └──── 근본 원인 분석(왜 그 실수를 했나) ◀───┘
```

### 신뢰성 공학의 사슬: 결함 → 오류 → 고장

분산·고신뢰 시스템 문헌은 다른 사전을 쓴다. Avižienis, Laprie, Randell, Landwehr 의 [Basic Concepts and Taxonomy of Dependable and Secure Computing](https://doi.org/10.1109/TDSC.2004.2) (IEEE TDSC, 2004) 의 정의는 다음과 같다.

| 용어 | Avižienis 외 (2004) 의 정의 |
|---|---|
| failure | 제공된 서비스가 올바른 서비스에서 벗어날 때 발생하는 **사건** |
| error | 이후 서비스 고장으로 이어질 수 있는, 시스템 전체 **상태의 일부** |
| fault | 오류의 원인으로 판정되거나 가정된 것 |

이 논문은 "결함은 오류를 일으킬 때 **활성(active)**, 그렇지 않으면 **잠복(dormant)**" 이라 하고, `fault → (활성화) → error → (전파) → failure → (인과) → fault …` 의 사슬을 제시한다. 한 구성요소의 고장은 그것을 쓰는 상위 시스템 입장에서는 다시 결함이 된다.

두 사전을 나란히 놓으면 함정이 보인다.

| 개념 | ISTQB (테스팅) | Avižienis 외 (신뢰성) |
|---|---|---|
| 사람의 실수 | error / mistake | (설계 결함의 원인으로 다룸) |
| 산출물 속 잘못 | defect / fault / bug | fault |
| 실행 중 잘못된 내부 상태 | (명시적 용어 없음) | **error** |
| 밖으로 드러난 잘못 | failure | failure |

같은 문서에서 "error" 가 나오면 어느 사전인지부터 확인해야 한다. 테스팅 맥락의 error 는 사람의 행위이고, 내결함성(fault tolerance) 맥락의 error 는 메모리나 레지스터에 들어 있는 틀린 값이다. 이 글에서는 두 번째 뜻을 **오염된 상태**라고 부르겠다.

### 결함이 있어도 고장이 안 나는 이유: 도달·감염·전파

결함이 고장으로 드러나려면 세 조건이 모두 맞아야 한다. Voas 의 [PIE 분석](https://doi.org/10.1109/32.153381) (IEEE TSE, 1992) 은 이를 실행(Execution), 감염(Infection), 전파(Propagation) 로 나눠 각 위치에서 결함이 숨을 확률을 추정하는 기법을 제안했다. 테스트 교과서들은 같은 생각을 도달(reachability)·감염(infection)·전파(propagation) 로 부르기도 한다.

| 단계 | 질문 | 실패하면 |
|---|---|---|
| 도달 | 테스트가 결함 위치를 실행했는가 | 커버리지 밖. 결함이 숨는다 |
| 감염 | 실행 결과 상태가 실제로 틀어졌는가 | 우연히 맞는 값(coincidental correctness) |
| 전파 | 틀어진 상태가 관찰 가능한 출력까지 갔는가 | 중간에 덮어써지거나 버려짐 |
| (관찰) | 테스트가 그 출력을 **검사**했는가 | 단언(assertion) 부재 |

마지막 줄은 이 모형의 실무 확장이다. 출력이 틀어졌어도 테스트가 그 값을 확인하지 않으면 고장은 "관찰되지 않은" 상태로 지나간다. 커버리지(SE100 #043)는 첫째 줄을, 뮤테이션 테스팅(SE100 #047)은 나머지 줄을 함께 측정한다.

### 테스트는 결함의 존재만 보여 준다

Dijkstra 는 1969년 로마 NATO 소프트웨어 공학 회의에서 "테스트는 버그의 존재를 보여 줄 뿐, 부재를 보여 주지 못한다" 고 말했고, 회의 보고서 [Software Engineering Techniques](http://homepages.cs.ncl.ac.uk/brian.randell/NATO/nato1969.PDF) 에 그 발언과 함께 그가 제출한 글의 문장 "Program testing can be used to show the presence of bugs, but never to show their absence!" 가 실려 있다. 비슷한 시기의 강연 원고 [EWD303 On the reliability of programs](https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD303.html) 에도 같은 취지의 문장이 있다. ISTQB 강의계획서는 이것을 테스팅 7원칙의 첫째로 두고 출처를 Buxton 1970(그 회의 보고서)으로 단다.

결함·고장의 구분과 합치면 이 원칙의 의미가 선명해진다. 테스트가 직접 보는 것은 **고장**이다. 결함은 고장에서 거슬러 올라가 추론하는 대상이고, 고장을 일으키지 않은 결함은 테스트가 원리적으로 볼 수 없다.

### 주변 용어

| 용어 | 뜻 | 실무에서 |
|---|---|---|
| 이상(anomaly) / 사건(incident) | 기대와 다른 관찰. 아직 결함인지 모름 | 버그 리포트의 첫 상태 |
| 거짓 양성(false positive) | 결함이 없는데 테스트가 실패 | 환경 문제, 깨지기 쉬운 테스트 |
| 거짓 음성(false negative) | 결함이 있는데 테스트가 통과 | 약한 단언, 도달 못 한 경로 |
| 디버깅 | 고장에서 결함을 찾아 고치는 활동 | 테스트와 다른 활동이다 |

## 실무 적용

### 예: 같은 결함, 다른 결과

```python
def average_latency(samples: list[float]) -> float:
    total = 0.0
    for i in range(1, len(samples)):   # 결함: 0번 원소를 건너뛴다
        total += samples[i]
    return total / len(samples)

assert average_latency([0.0, 5.0, 10.0]) == 5.0    # 통과 — 결함을 실행했지만 값이 우연히 맞음
assert average_latency([4.0, 4.0]) == 4.0          # 실패 — 고장이 관찰됨 (실제 2.0)
```

- 오류: "인덱스는 1부터" 라고 착각한 개발자의 실수
- 결함: `range(1, …)` 한 줄
- 첫 번째 입력: 결함에 도달했고 반복이 한 번 덜 도는 상태 차이도 생겼다(감염). 그러나 빠진 원소가 0.0 이라 합계와 결과에는 차이가 전파되지 않는다. 관찰할 것이 없다
- 두 번째 입력: 감염·전파·관찰이 모두 일어나 고장으로 드러난다

첫 번째 테스트만 있는 저장소에서 이 결함은 몇 년이고 살아남는다. "3년 전부터 있던 버그가 어제 터진" 이유다.

### 버그 트래커 필드를 사슬에 맞추기

| 필드 | 채우는 내용 | 사슬의 위치 |
|---|---|---|
| 증상 | 관찰된 동작, 재현 절차, 기대 결과 | 고장 |
| 원인 위치 | 파일·커밋·설정 키 | 결함 |
| 유입 경위 | 왜 그 결함이 만들어졌나 | 오류 / 근본 원인 |
| 탈출 경위 | 왜 테스트·리뷰가 못 잡았나 | 도달·감염·전파·관찰 중 어디서 놓쳤나 |

"탈출 경위" 칸이 가장 쓸모 있다. 도달에서 놓쳤다면 테스트 케이스가, 관찰에서 놓쳤다면 단언이 부족했다는 뜻이고 처방이 다르다.

## 흔한 오해와 함정

- **"버그 = 결함 = 고장" 으로 뭉쳐 쓰기.** 회고에서 "버그가 있었다" 로 끝나면 재발 방지책이 나오지 않는다. 고장(무엇을 봤나), 결함(어디가 틀렸나), 오류(왜 틀리게 만들었나)를 따로 적는다.
- **error 라는 단어를 확인 없이 읽기.** 테스팅 문서의 error 는 사람의 실수, 신뢰성 문서의 error 는 오염된 상태다. 예외 클래스 이름(`Error`)은 또 다른 뜻이다.
- **고장이 없었으니 결함도 없다.** 잠복 결함은 입력 분포가 바뀌는 날(새 고객, 새 지역, 윤년) 활성화된다.
- **모든 고장의 원인이 코드다.** ISTQB 정의대로 환경 조건도 고장을 만든다. 설정·인프라·하드웨어를 원인 후보에서 빼지 않는다.
- **커버리지 100% 면 결함이 다 드러난다.** 커버리지는 도달만 보장한다. 감염·전파·관찰은 별개다.

## 확인 문제

1. ISTQB 용어로 오류, 결함, 고장을 각각 한 문장으로 정의하라.
2. Avižienis 외(2004)에서 error 는 무엇을 뜻하며, ISTQB 의 error 와 어떻게 다른가?
3. 위 `average_latency` 예에서 첫 번째 단언이 통과하는 이유를 도달·감염·전파 관점으로 설명하라.
4. "테스트는 버그의 부재를 보여 주지 못한다" 를 결함·고장 구분으로 다시 설명하라.
5. 테스트를 모두 통과했는데 운영에서 고장이 났다. 원인 후보를 사슬의 단계별로 나열하라.

### 풀이

1. 오류는 사람이 저지르는 실수, 결함은 그 실수로 산출물(코드·명세 등)에 남은 잘못, 고장은 결함이 실행되어 시스템이 해야 할 일을 안 하거나 하지 말아야 할 일을 하는 것이다.
2. 고장으로 이어질 수 있는 시스템 상태의 일부, 즉 오염된 내부 상태다. ISTQB 의 error 는 사람의 행위다. 신뢰성 사슬은 결함 → 오류 → 고장 순서라서 단어의 위치도 다르다.
3. 결함 줄은 실행되었고(도달), 0번 원소를 건너뛰어 반복 횟수라는 상태가 올바른 실행과 달라졌다(감염). 그러나 건너뛴 값이 0.0 이라 합계가 같아졌고, 차이가 출력까지 전파되지 않았다.
4. 테스트가 직접 관찰하는 것은 고장이다. 고장을 일으키지 않은 결함은 관찰할 수단이 없으므로, 고장이 관찰되지 않았다는 사실로 결함이 없다고 결론낼 수 없다.
5. 운영 입력이 결함 위치에 처음 도달했거나, 운영 데이터에서만 상태가 틀어지거나, 테스트 환경에서는 오염이 출력까지 전파되지 않았거나, 테스트가 해당 출력을 단언하지 않았거나, 코드가 아닌 환경 조건(설정·인프라)이 원인일 수 있다.

## 더 읽을거리 (References)

- ISTQB, [Certified Tester Foundation Level Syllabus v4.0.1](https://istqb.org/?sdm_process_download=1&download_id=3345) (PDF), 1.2.3절, 1.3절 — [CTFL v4.0 안내 페이지](https://www.istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/)
- A. Avižienis, J.-C. Laprie, B. Randell, C. Landwehr, [Basic Concepts and Taxonomy of Dependable and Secure Computing](https://doi.org/10.1109/TDSC.2004.2), IEEE Transactions on Dependable and Secure Computing 1(1), 2004
- J. M. Voas, [PIE: A Dynamic Failure-Based Technique](https://doi.org/10.1109/32.153381), IEEE Transactions on Software Engineering 18(8), 1992
- J. N. Buxton, B. Randell (eds.), [Software Engineering Techniques: Report on a conference sponsored by the NATO Science Committee, Rome, 1969](http://homepages.cs.ncl.ac.uk/brian.randell/NATO/nato1969.PDF)
- E. W. Dijkstra, [EWD303 On the reliability of programs](https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD303.html)
- Paul Ammann, Jeff Offutt, *Introduction to Software Testing*, 2nd ed., Cambridge University Press, 2016 (서지 정보)
