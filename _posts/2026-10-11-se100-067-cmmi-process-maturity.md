---
layout: post
title: "[SE100 #067] CMMI 와 프로세스 성숙도"
date: 2026-10-11 17:05:21 +0900
categories: [software-engineering]
tags: [se100, process, cmmi, process-maturity, process-improvement]
---

소프트웨어 공학 100 주제 시리즈의 67번째 글이다. (카테고리: 프로세스와 방법론)

## 한 줄 요약

성숙도 모델의 질문은 "이 팀이 잘하는가" 가 아니라 **"이 조직은 잘한 것을 반복할 수 있는가"** 다. 레벨 1 조직도 훌륭한 결과를 낼 수 있다. 다만 그것이 개인의 영웅적 노력에 달려 있어서, 사람이 바뀌거나 압박이 커지면 재현되지 않는다.

## 왜 필요한가

어떤 회사가 작년에 성공한 프로젝트 두 개와 실패한 프로젝트 세 개를 냈다. 성공한 두 개는 특정 PM 과 시니어 개발자가 맡았던 것이다. 둘이 퇴사하자 같은 종류의 프로젝트가 또 실패한다.

이 회사에 필요한 것은 더 뛰어난 사람이 아니라, 성공한 프로젝트가 **무엇을 했는지 알고 그것을 다음 프로젝트에 옮길 수 있는 능력**이다. 일정·비용을 추적하는 최소한의 관리, 조직이 공유하는 표준 프로세스, 그 프로세스의 성과를 숫자로 보는 눈. 성숙도 모델은 이 능력을 단계로 나눠 "다음에 무엇을 갖춰야 하는가" 를 알려 준다.

## 핵심 개념

### 출발점: 계약자를 평가하려던 국방부의 요청

SEI 의 [CMM for Software v1.1](https://www.sei.cmu.edu/library/capability-maturity-model-for-software-version-11/)(Paulk, Curtis, Chrissis, Weber, CMU/SEI-93-TR-024, 1993) 초록이 기원을 정리한다.

- 1986년 11월, SEI 는 MITRE 의 도움을 받아 프로세스 성숙도 프레임워크 개발을 시작했다. 연방 정부가 **소프트웨어 계약자의 역량을 평가할 방법**을 달라고 요청한 데 대한 응답이었다.
- 1987년 9월, 프레임워크의 간단한 설명과 **성숙도 설문지**를 냈다.
- 그런데 설문지가 성숙도를 탐구하는 수단이 아니라 너무 자주 "모델 그 자체" 로 여겨졌다. 그래서 4년의 경험 뒤 완전히 정의된 모델로 발전시켰다.

SEI 의 [연혁 페이지](https://www.sei.cmu.edu/history-of-innovation/transforming-software-quality-assessment/)는 1991년의 Software CMM 발표가 정부와 업계의 소프트웨어 품질관을 바꿨고, 이후 CMMI 가 Software CMM 에서 진화했다고 쓴다. 기원부터 "평가 도구" 와 "개선 지도" 라는 두 얼굴을 갖고 있었고, 설문지가 모델로 오해받은 일은 오늘날 "레벨 인증" 이 목적이 되는 문제의 예고편이었다.

### 다섯 성숙도 레벨

CMM v1.1 의 정의(보고서 2.1절)와 CMMI-DEV v1.3 의 이름을 나란히 놓는다.

| 레벨 | CMM v1.1 | CMMI v1.3 | CMM v1.1 의 특징 서술 |
|---|---|---|---|
| 1 | Initial | Initial | 프로세스가 임기응변적이고 때로는 혼란스럽다. 정의된 프로세스가 거의 없고 성공은 개인의 노력에 달렸다 |
| 2 | Repeatable | Managed | 비용·일정·기능을 추적하는 기본 프로젝트 관리가 있다. 비슷한 프로젝트의 성공을 **반복**할 규율이 있다 |
| 3 | Defined | Defined | 관리·엔지니어링 프로세스가 조직 표준으로 문서화·통합됐고, 모든 프로젝트가 그것을 **맞춤(tailoring)** 해서 쓴다 |
| 4 | Managed | Quantitatively Managed | 프로세스와 제품 품질을 상세히 측정하고, **정량적으로** 이해·통제한다 |
| 5 | Optimizing | Optimizing | 정량적 피드백과 새 아이디어·기술의 시범 적용으로 지속적 개선이 가능하다 |

레벨 2 와 4 의 이름이 바뀐 것에 주의한다. CMM 의 레벨 4 "Managed" 는 CMMI 에서 "Quantitatively Managed" 가 됐고, CMMI 의 레벨 2 가 "Managed" 를 가져갔다. 오래된 자료를 읽을 때 혼동하기 쉽다.

레벨 2 와 3 의 차이가 실무에서 가장 중요하다. 레벨 2 는 **프로젝트 단위**의 규율이고(각 프로젝트가 자기 계획·추적을 한다), 레벨 3 은 **조직 단위**의 표준이다(조직이 프로세스 자산을 갖고, 프로젝트가 그것을 맞춤해 쓴다).

### 레벨을 건너뛸 수 없는 이유

CMM v1.1 보고서 2.5절 "Skipping Maturity Levels" 는 두 가지를 함께 말한다.

1. 상위 레벨의 프로세스를 하위 조직이 **유익하게 쓸 수는 있다.** 레벨 1·2 조직도 동료 검토(레벨 3), 파레토 분석(레벨 4), 신기술 시범(레벨 5)을 할 수 있다.
2. 그러나 **레벨을 건너뛰는 것은 역효과**다. 적절한 토대 없는 프로세스는 가장 필요한 순간 — 압박을 받을 때 — 에 무너진다. 예를 들어 동료 검토는 "불이 나서 프로젝트가 위협받을 때도" 일관되게 실행되지 않으면 충분한 효과를 내지 못한다.

보고서는 레벨 1 조직의 지배적 문제는 **관리**의 문제이고, 다른 문제들은 계획·관리의 어려움에 가려져 보이지 않는다고 쓴다. 그래서 측정(레벨 4)부터 들이는 것은 순서가 틀렸다. 계획대로 일하지 않는 프로젝트의 숫자는 의미가 없다.

### CMMI: 통합과 두 가지 표현

CMMI 는 이름 그대로 통합(Integration) 모델이다. v1.3 문서에 따르면 처음에는 소프트웨어 CMM(SW-CMM v2.0 draft C), 시스템 공학 역량 모델(SECM, EIA 731), 통합 제품 개발 CMM(IPD-CMM v0.98) 세 원천 모델을 하나로 합쳤다. *CMMI for Development, Version 1.3*(CMMI Product Team, CMU/SEI-2010-TR-033, 2010년 11월)의 구조는 이렇다.

- **프로세스 영역(PA) 22개.** 요구사항 관리, 프로젝트 계획, 형상 관리, 위험 관리, 검증, 확인 등.
- **단계적 표현(staged)**: 여러 PA 묶음으로 조직의 **성숙도 레벨** 1~5 를 정한다.
- **연속적 표현(continuous)**: PA 하나하나의 **역량 레벨** 0~3 (Incomplete, Performed, Managed, Defined)을 정한다.

```
연속적 표현                     단계적 표현
PA 별 역량 레벨 (0~3)            조직 성숙도 레벨 (1~5)
 REQM ███ 3                     5 Optimizing
 PP   ██  2                     4 Quantitatively Managed
 CM   ███ 3                     3 Defined        ◀── PA 묶음 달성
 VER  █   1                     2 Managed
 ...                            1 Initial
"어느 영역을 먼저 올릴까"          "조직 전체가 어디쯤인가"
```

연속적 표현은 "우리에게 가장 아픈 영역(예: 형상 관리)부터 올리자" 는 접근에 맞고, 단계적 표현은 조직 간 비교와 정해진 개선 경로에 맞는다.

### 애자일과의 관계

v1.3 은 "애자일 접근을 쓸 때 CMMI 해석하기" 절을 두고, 형상 관리·프로젝트 계획·요구사항 관리·검증 등 10개 PA 에 "In Agile environments" 로 시작하는 해석 노트를 붙였다. 그 노트들은 예시일 뿐 필요조건도 충분조건도 아니라고 명시한다. 배경 자료로 SEI 기술 노트 [CMMI or Agile: Why Not Embrace Both!](https://kilthub.cmu.edu/articles/report/CMMI_or_Agile_Why_Not_Embrace_Both_/6572513)(Glazer 외, CMU/SEI-2008-TN-003)를 든다. 제목 그대로, 둘 중 하나를 고르는 문제가 아니라는 입장이다.

### 현재

CMMI 는 지금 ISACA 산하 [CMMI Institute](https://cmmiinstitute.com/cmmi)가 관리한다. ISACA 는 [2023년 4월 6일 보도자료](https://www.isaca.org/about-us/newsroom/press-releases/2023/isaca-updates-cmmi-model-with-three-new-domains-that-help-organizations-improve-quality)에서 CMMI V3.0 을 발표하며 기존의 개발, 서비스, 공급자 관리, 보안, 안전 도메인에 데이터 관리, 인력 관리, 가상 업무 세 도메인을 더했다.

## 실무 적용

### 인증이 아니라 진단 도구로 쓰기

레벨 인증을 목표로 하지 않는 팀도 성숙도 모델을 **자가 진단 질문**으로 쓸 수 있다.

```
[레벨 2: 프로젝트가 스스로를 관리하는가]
 □ 요구사항 변경이 기록되고, 계획에 반영되는가
 □ 일정·노력 추정과 실적을 비교하는가
 □ 형상(코드·설정·문서)이 버전 관리되고 기준선이 있는가
 □ 외주·외부 의존의 약속을 추적하는가

[레벨 3: 조직이 배운 것을 공유하는가]
 □ 팀 간 공유되는 표준 프로세스(템플릿·파이프라인·DoD)가 있는가
 □ 프로젝트가 그 표준을 맞춤해 쓰고, 맞춤 근거를 남기는가
 □ 회고·사후 검토의 교훈이 표준 자산에 반영되는가

[레벨 4: 숫자로 예측하는가]
 □ 리드 타임·결함 유입률의 분포와 변동을 알고 있는가
 □ 그 분포로 다음 릴리스의 범위를 예측하는가
```

레벨 2 항목이 비어 있는데 레벨 4 대시보드를 만드는 것은 앞서 본 "건너뛰기" 다.

### 현대 도구로 옮기면

| 성숙도의 요구 | 현대 실무 |
|---|---|
| 형상 관리·기준선 | Git, 보호 브랜치, 태그, IaC |
| 조직 표준 프로세스 | 공용 CI 템플릿, 골든 패스, 팀 공용 DoD |
| 맞춤과 근거 | 템플릿 오버라이드 + ADR(SE100 #025) |
| 정량 관리 | DORA 지표(SE100 #070), 사이클 타임 분포 |
| 지속적 개선 | 회고(SE100 #068), 사후 검토, 실험 |

## 흔한 오해와 함정

- **"레벨 = 품질 보증서."** 레벨은 특정 시점·범위의 평가 결과다. 평가받은 조직 단위가 아닌 팀, 평가 이후의 프로젝트에 자동으로 적용되지 않는다.
- **문서를 만들면 레벨이 오른다.** CMM 초기의 교훈처럼, 평가 도구(설문지·체크리스트)를 모델로 오해하면 실제 행동은 그대로인 채 문서만 늘어난다.
- **CMMI 는 폭포수를 강요한다.** 모델은 **무엇을** 달성할지(목표·실천)를 말하지 **어떻게** 할지(생명주기)를 정하지 않는다. v1.3 은 애자일 해석 노트까지 두고 있다.
- **레벨 4 를 측정 도구 도입으로 본다.** 정량 관리는 숫자를 모으는 것이 아니라 프로세스 변동을 이해하고 예측에 쓰는 것이다. 그 전제는 프로젝트들이 같은 정의로 일하는 레벨 3 이다.
- **모든 조직이 레벨 5 를 목표로 해야 한다.** 목표 레벨은 사업 위험에 맞춰 고른다. 수십 명 규모의 스타트업이 정량 관리 체계를 갖추는 비용은 얻는 가치보다 클 수 있다.

## 확인 문제

1. CMM 개발의 원래 동기는 무엇이었나?
2. CMM v1.1 의 레벨 4 와 CMMI v1.3 의 레벨 2 는 같은 이름을 쓴다. 각각 무엇을 뜻하는가?
3. 레벨 2 와 레벨 3 의 핵심 차이를 "단위" 로 설명하라.
4. CMM 보고서가 레벨 건너뛰기를 역효과라고 한 이유를 동료 검토 예로 설명하라.
5. 연속적 표현은 어떤 상황에서 단계적 표현보다 유리한가?

### 풀이

1. 연방 정부(국방부)가 소프트웨어 계약자의 역량을 평가할 방법을 SEI 에 요청한 것.
2. CMM 의 레벨 4 "Managed" 는 프로세스·품질을 정량적으로 이해·통제하는 단계(CMMI 의 Quantitatively Managed)이고, CMMI 의 레벨 2 "Managed" 는 프로젝트 단위의 기본 관리 단계(CMM 의 Repeatable)다.
3. 레벨 2 는 프로젝트마다 자기 계획·추적 규율이 있는 상태, 레벨 3 은 조직 표준 프로세스가 있고 프로젝트가 그것을 맞춤해 쓰는 상태다.
4. 동료 검토 같은 상위 레벨 실천은 일관되게 실행될 토대(계획·관리 규율)가 없으면 압박을 받는 순간 생략된다. 토대 없는 프로세스는 가장 필요할 때 무너진다.
5. 조직 전체가 아니라 특정 프로세스 영역(예: 형상 관리, 요구사항 관리)이 가장 큰 문제일 때, 그 영역부터 역량 레벨을 올리는 개선 경로를 짤 수 있다.

## 더 읽을거리 (References)

- Mark C. Paulk, Bill Curtis, Mary Beth Chrissis, Charlie Weber, [Capability Maturity Model for Software, Version 1.1](https://www.sei.cmu.edu/library/capability-maturity-model-for-software-version-11/), CMU/SEI-93-TR-024, 1993 ([PDF](https://www.sei.cmu.edu/documents/1092/1993_005_001_16211.pdf))
- Mark C. Paulk 외, [Capability Maturity Model, Version 1.1](https://doi.org/10.1109/52.219617), IEEE Software 10(4), 1993
- CMMI Product Team, *CMMI for Development, Version 1.3*, CMU/SEI-2010-TR-033, Software Engineering Institute, 2010 (서지 정보)
- Hillel Glazer 외, [CMMI or Agile: Why Not Embrace Both!](https://kilthub.cmu.edu/articles/report/CMMI_or_Agile_Why_Not_Embrace_Both_/6572513), CMU/SEI-2008-TN-003, 2008
- SEI, [Transforming Software Quality Assessment](https://www.sei.cmu.edu/history-of-innovation/transforming-software-quality-assessment/)
- ISACA, [ISACA Updates CMMI Model with Three New Domains](https://www.isaca.org/about-us/newsroom/press-releases/2023/isaca-updates-cmmi-model-with-three-new-domains-that-help-organizations-improve-quality), 2023
- Watts S. Humphrey, *Managing the Software Process*, Addison-Wesley, 1989 (서지 정보)
