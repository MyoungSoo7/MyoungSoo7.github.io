---
layout: post
title: "[SE100 #005] SWEBOK — 소프트웨어 공학 지식 체계"
date: 2026-10-11 16:54:56 +0900
categories: [software-engineering]
tags: [se100, se-foundations, swebok, body-of-knowledge, ieee-computer-society]
---

소프트웨어 공학 100 주제 시리즈의 5번째 글이다. (카테고리: 기초와 역사)

## 한 줄 요약

SWEBOK Guide 는 IEEE Computer Society 가 펴내는 "소프트웨어 공학 지식 체계 안내서" 로, 이 분야에서 **일반적으로 인정된(generally accepted)** 지식의 범위를 지식 영역(Knowledge Area, KA)으로 나눠 정리한다. 2024년 V4.0 은 18개 KA 를 두고 있고, 소프트웨어 아키텍처·소프트웨어 공학 운영·소프트웨어 보안 세 영역이 새로 들어왔다.

## 왜 필요한가

"소프트웨어 엔지니어라면 무엇을 알아야 하는가?" 라는 질문에 사람마다 답이 다르다. 어떤 팀은 코딩과 테스트만 떠올리고, 어떤 팀은 요구사항·형상 관리·경제성까지 포함한다. 범위에 대한 합의가 없으면 생기는 문제는 구체적이다.

- **채용·평가**: 직무 기술서가 회사마다, 팀장마다 제각각이다.
- **교육**: 신입 교육이 "우리 팀이 쓰는 프레임워크" 에 머문다. 프레임워크가 바뀌면 교육도 버려진다.
- **공백 발견**: 팀이 운영·보안·유지보수를 아무도 맡지 않는다는 사실을 장애가 난 뒤에 안다.

SWEBOK 은 이런 대화에 쓸 **공통 지도**를 제공하려는 시도다. 앞서 본 1968년 NATO 회의(SE100 #001)가 "공학이 되어야 한다" 고 선언했다면, SWEBOK 은 "그 공학의 지식은 이것이다" 라고 범위를 그리는 작업이다.

## 핵심 개념

### 무엇이고 누가 만드는가

[IEEE Computer Society 의 SWEBOK 페이지](https://www.computer.org/education/bodies-of-knowledge/software-engineering)가 1차 출처다. 여기서 확인되는 사실은 다음과 같다.

| 항목 | 내용 |
|---|---|
| 정식 명칭 | Guide to the Software Engineering Body of Knowledge (SWEBOK Guide) |
| 발행 | IEEE Computer Society |
| 최신판 | V4.0 (2024), 편집 Hironori Washizaki. 2025년 9월 25일 소폭 수정판 **V4.0a** 로 표기 |
| 이전 판 | 첫 SWEBOK Guide 는 2004년, 이후 2014년판 |
| 시작 | Computer Society 는 1998년 이 지식 체계의 정의를 시작 |
| 다음 판 | V5.0 을 준비 중이며 공개 검토를 받는다 |

본문은 [V4 다운로드 페이지](https://www.computer.org/education/bodies-of-knowledge/software-engineering/v4)에서 약관 동의 후 받을 수 있다. 약관상 개인·비상업 용도이며 공개 재배포는 허용되지 않으니, 팀 위키에 PDF 를 올리지 말고 링크를 공유하자.

이름에 "Guide" 가 붙은 이유가 중요하다. 지식 체계(Body of Knowledge) 전체는 한 문서에 담을 수 없으므로, SWEBOK Guide 는 그중 **일반적으로 인정된 부분집합을 식별하고 기술**하며, 각 주제에 참고문헌을 연결하는 "안내서" 역할을 한다.

### 18개 지식 영역 (V4.0)

공식 페이지의 장(chapter) 목록을 성격별로 묶으면 이렇다.

| 묶음 | 지식 영역 |
|---|---|
| 생명주기 활동 | 1 요구사항(Requirements), 2 아키텍처(Architecture)★, 3 설계(Design), 4 구성(Construction), 5 테스트(Testing), 6 소프트웨어 공학 운영(Operations)★, 7 유지보수(Maintenance) |
| 관리·지원 | 8 형상 관리(Configuration Management), 9 소프트웨어 공학 관리(Management), 10 프로세스(Process), 11 모델과 방법(Models and Methods), 12 품질(Quality), 13 보안(Security)★ |
| 직업·경제 | 14 전문가 실무(Professional Practice), 15 소프트웨어 공학 경제(Economics) |
| 기초 | 16 컴퓨팅 기초, 17 수학 기초, 18 공학 기초 |

★ 은 V4.0 에서 새로 추가된 영역이다. 공식 페이지는 이와 함께 **애자일과 DevOps** 가 이전 판 이후 널리 쓰이게 되어 여러 KA 에 통합되었다고 밝힌다. 부록으로는 KA 기술 명세(A), SWEBOK 을 뒷받침하는 IEEE·ISO/IEC 표준 목록(B), 통합 참고문헌(C)이 있다.

변화의 방향이 읽힌다. 아키텍처는 설계에서 독립했고, 운영은 "배포 이후" 를 소프트웨어 공학의 일부로 끌어들였으며, 보안은 품질의 하위 항목이 아니라 독립 영역이 되었다.

### "일반적으로 인정된 지식" 의 정의

SWEBOK 의 범위를 정하는 핵심 개념이다. 공식 페이지는 두 정의를 상호 보완적으로 쓴다.

1. PMI 의 PMBOK 정의를 빌린 것: 기술된 지식과 실무가 **대부분의 프로젝트에 대부분의 경우 적용 가능**하고 그 가치에 **폭넓은 합의**가 있다는 뜻. 단, 모든 프로젝트에 똑같이 적용해야 한다는 뜻은 아니다.
2. 2004년판 산업 자문위원회의 정의: 대학 졸업 후 **4년의 실무 경험**을 쌓은 사람이 통과할 소프트웨어 공학 면허 시험의 학습 범위에 들어갈 지식.

여기에 KA 편집자들은 3~5년 뒤에 "일반적으로 인정될" 것까지 내다보도록 요청받는다. 공식 페이지는 "일반적으로 인정된" 지식이 다른 종류의 지식과 어떻게 다른지 보여 주는 3분류 도식(초안)도 함께 제시한다. 즉 SWEBOK 은 **최신 기술 목록이 아니라 검증된 핵심**을 노린다.

### 지식 체계 ≠ 커리큘럼

공식 페이지는 소프트웨어 공학 지식 체계와 교육 과정의 내용을 분명히 구분해야 한다고 강조한다. 소프트웨어 엔지니어는 공학 고유의 지식 외에도 많은 것을 알아야 하지만, SWEBOK 의 목표는 그 전부를 나열하는 게 아니라 **소프트웨어 공학의 핵심**을 식별하는 것이다. 그 밖의 지식을 정하는 일은 자격·인증·교육과정을 만드는 다른 조직의 몫이다.

### 어떻게 만들어지는가

공식 페이지에 설명된 검토 절차는 단계적이다.

```
KA 편집자 초안
   └→ 초청 전문가 검토 (학술 논문 심사와 유사) → 반영
        └→ 초청 실무자 검토 (관련성·유용성에 관한 약 14개 질문) → 반영
             └→ 공개 검토 (특정 줄·항목을 지목한 의견만)
```

투명성, 합의 형성, 최소 한 가지 형식의 무료 접근이 원칙으로 제시된다.

## 실무 적용

SWEBOK 은 읽고 끝내는 책이 아니라 **점검표의 뼈대**로 쓸 때 가치가 크다. 팀의 실무를 KA 에 대응시켜 비어 있는 칸을 찾아보자.

```yaml
# 팀 실무 ↔ SWEBOK V4 KA 매핑 (예시 팀)
requirements:        { owner: PO,        practice: "스토리 + 인수 기준",       gap: false }
architecture:        { owner: null,      practice: "구두 합의",                gap: true  }  # ADR 없음
design:              { owner: 개발팀,     practice: "PR 설명에 설계 요약",       gap: false }
construction:        { owner: 개발팀,     practice: "린터, 코드 리뷰",          gap: false }
testing:             { owner: 개발팀,     practice: "단위 테스트만",            gap: true  }  # 통합 테스트 부재
operations:          { owner: 1인,       practice: "수동 배포 스크립트",        gap: true  }  # 버스 팩터 1
maintenance:         { owner: null,      practice: "장애 시 대응",             gap: true  }
configuration_mgmt:  { owner: 개발팀,     practice: "Git, 태그 릴리스",         gap: false }
quality:             { owner: null,      practice: "명시적 품질 목표 없음",     gap: true  }
security:            { owner: null,      practice: "의존성 스캔 없음",          gap: true  }
economics:           { owner: 팀장,      practice: "클라우드 비용 월 1회 확인",  gap: false }
professional_practice: { owner: 전원,    practice: "윤리·법규 교육 없음",       gap: true  }
```

이 표에서 `owner: null` 이 보이는 칸이 다음 분기 개선 후보다. SWEBOK 이 각 KA 에 연결해 둔 참고문헌(부록 C)을 따라가면 학습 자료 목록도 바로 생긴다.

다른 활용법:

- **신입 온보딩**: 18개 KA 를 기준으로 "우리 팀에서 이 영역은 어떻게 하는가" 한 줄씩 적은 문서를 만든다.
- **역량 평가**: 개인의 강점·약점을 KA 단위로 이야기하면 "코딩 잘함/못함" 보다 구체적이다.
- **표준 찾기**: 부록 B 는 KA 별 관련 IEEE·ISO/IEC 표준을 안내한다. 요구사항 명세 같은 주제에서 어떤 표준을 봐야 할지 출발점이 된다(SE100 #016 에서 다룬다).

## 흔한 오해와 함정

- **"SWEBOK 은 표준이다."** 공식 명칭부터 Guide 다. 무엇을 해야 한다고 강제하는 규정이 아니라 지식의 범위와 참고문헌을 정리한 안내서다.
- **"SWEBOK 에 없는 기술은 중요하지 않다."** 일부러 "일반적으로 인정된" 것만 담는다. 새롭거나 특정 분야에만 해당하는 기술은 빠지는 것이 설계 의도다.
- **"모든 KA 를 다 해야 한다."** "일반적으로 인정됨" 의 정의 자체가 모든 프로젝트에 똑같이 적용하라는 뜻이 아니라고 명시한다. 프로젝트에 맞는 수준을 고르는 것은 팀의 책임이다.
- **"한 번 읽으면 끝."** 판이 바뀌며 KA 가 추가·재편된다. 2014년판 기준 자료로 공부했다면 아키텍처·운영·보안의 변화를 따로 확인해야 한다.
- **PDF 재배포.** 이용 약관이 공개 게시와 재배포를 금지한다. 링크로 공유한다.

## 확인 문제

1. SWEBOK "Guide" 가 지식 체계 전체가 아니라 안내서인 이유는?
2. V4.0 에서 새로 추가된 세 지식 영역은?
3. SWEBOK 이 쓰는 "일반적으로 인정된 지식" 의 두 정의를 요약하라.
4. 지식 체계와 커리큘럼을 구분하는 이유는?
5. 팀에서 SWEBOK 을 가장 손쉽게 활용하는 방법 하나를 제시하라.

### 풀이

1. 신흥 분야라도 지식 전체를 한 문서에 담을 수는 없으므로, 일반적으로 인정된 부분집합을 식별·기술하고 참고문헌으로 안내하는 역할을 한다.
2. 소프트웨어 아키텍처, 소프트웨어 공학 운영, 소프트웨어 보안.
3. (1) 대부분의 프로젝트에 대부분의 경우 적용 가능하고 그 가치에 폭넓은 합의가 있는 지식. (2) 졸업 후 4년 실무 경험자가 통과할 면허 시험의 학습 범위에 들어갈 지식.
4. SWEBOK 의 목표는 소프트웨어 공학 고유의 핵심을 식별하는 것이고, 엔지니어가 알아야 할 그 밖의 지식(수학, 도메인 등)을 정하는 일은 교육과정·자격 기관의 몫이기 때문이다.
5. 팀의 실무를 18개 KA 에 대응시켜 담당자가 없거나 실무가 비어 있는 영역을 찾는 것.

## 더 읽을거리 (References)

- IEEE Computer Society, [Software Engineering Body of Knowledge (SWEBOK)](https://www.computer.org/education/bodies-of-knowledge/software-engineering)
- IEEE Computer Society, [SWEBOK Version 4 — Download](https://www.computer.org/education/bodies-of-knowledge/software-engineering/v4)
- H. Washizaki (ed.), *Guide to the Software Engineering Body of Knowledge (SWEBOK Guide), Version 4.0*, IEEE Computer Society, 2024 (서지 정보)
- 이 시리즈의 맥락: [소프트웨어 개발 생명주기]({% post_url 2026-10-10-cs300-181-software-development-life-cycle %})
