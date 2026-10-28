---
layout: post
title: "FDE 와 리버스 엔지니어링 — 고객 현장의 '문서 없는 시스템' 을 REA 같은 하네스로 읽어 내는 법"
date: 2026-10-28 20:30:00 +0900
categories: [AI, Engineering]
tags: [FDE, Forward Deployed Engineer, Reverse Engineering, REA, Legacy, Business Rules, Characterization Test]
---

[10월 22일 글]({% post_url 2026-10-22-rea-reverse-engineering-harness %})에서는 **REA(Reverse Engineer Anything)** 가 무엇인지 다뤘다. Ghidra·IDA·JADX 같은 분석 도구를 MCP 하나로 묶고, 결과를 "본 것 / 추론한 것 / 모르는 것" 으로 나눠 돌려주는 에이전트 하네스다. 이번 글은 그 도구를 **누가, 어떤 상황에서** 가장 절실하게 쓰게 될지를 다룬다. 답은 **FDE(Forward Deployed Engineer)** 다.

## 1. FDE 는 어떤 일을 하나

FDE 는 Palantir 가 만든 직무 이름이다. Palantir 채용 공고의 첫 문장은 이렇다.

> "Forward Deployed Engineers (FDEs) work directly with customers to quickly understand their greatest problems" — [Palantir 채용 공고 (Lever)](https://jobs.lever.co/palantir/98b81271-9e15-40b7-8dce-0c62f24702f9)

같은 회사의 신입 공고는 이 직무를 Palantir 가 만들었고, 엔지니어를 고객에게 **직접 붙여** 가장 급한 문제를 풀게 하는 자리라고 설명한다([신입 공고](https://jobs.lever.co/palantir/341d5cae-a473-4813-9a6c-0f67fcc1b253)).

일반 제품 개발자와 FDE 의 차이를 한 줄로 줄이면 이렇다.

| | 제품 개발자 | FDE |
|---|---|---|
| 일하는 곳 | 우리 코드베이스 | **고객의 시스템 옆** |
| 아는 것 | 우리 설계 의도 | 처음엔 거의 없음 |
| 문서 | 대체로 있음 | **대체로 없거나, 있어도 코드와 다름** |
| 원작자 | 옆자리에 있음 | 퇴사했거나 협력사 |
| 첫 질문 | "어떻게 만들까" | **"이게 지금 뭘 하고 있지"** |

FDE 의 첫 2주는 대부분 마지막 질문에 쓰인다. 고객 시스템과 붙이려면 그 시스템이 **실제로** 무엇을 하는지 알아야 하는데, 그걸 아는 사람이 없는 경우가 흔하다. 이게 바로 리버스 엔지니어링이 다루는 문제다.

## 2. 리버스 엔지니어링의 원래 정의 — "바꾸지 않고 다시 그린다"

용어의 기준은 Chikofsky 와 Cross 의 1990년 논문이다([IEEE Software 7(1), doi:10.1109/52.43044](https://doi.org/10.1109/52.43044)). 이 논문은 개념을 셋으로 나눈다.

- **포워드 엔지니어링** — 요구사항 → 설계 → 구현. 평소 하는 개발.
- **리버스 엔지니어링** — 구현에서 거꾸로 올라가 **더 높은 수준의 표현**을 만든다. 대상은 바꾸지 않는다.
- **디자인 리커버리** — 리버스 엔지니어링 가운데 프로그램이 **무엇을, 어떻게, 왜** 하는지 사람이 완전히 이해하는 데 필요한 정보를 다시 만들어 내는 일.

FDE 의 일에 맞춰 보면 이렇게 된다.

```
고객 레거시 (코드·바이너리·DB·로그)
   │  리버스 엔지니어링: 구조 파악
   ▼
호출 그래프 · 데이터 흐름 · 인터페이스
   │  디자인 리커버리: 업무 의미 복원
   ▼
업무 규칙 목록 ("VIP 고객은 3만원 이상 무료배송")
   │  포워드 엔지니어링
   ▼
새 기능 · 연동 · 이관
```

FDE 가 고객에게 넘겨야 하는 건 가운데 두 번째 줄, **업무 규칙 목록**이다. 디컴파일 결과나 호출 그래프는 그걸 얻기 위한 재료일 뿐이다.

## 3. 업무 규칙 역추출 — LLM 은 어디까지 왔나

레거시에서 업무 규칙을 뽑아내는 일은 최근 LLM 연구가 집중적으로 다루는 주제다. 공개된 연구 세 개를 보면 흐름이 보인다.

**① COBRAIN (EASE 2025)** — COBOL 에서 업무 규칙을 뽑는 LLM 도구를, 제어 흐름 그래프 기반 기존 도구(COBREX)와 비교했다([발표 페이지](https://conf.researchr.org/details/ease-2025/ease-2025-research-papers/57/LLM-Vs-Rule-Based-The-COBRAIN-Tool-and-An-Empirical-Study-on-Extracting-Business-Ru)).

- 사람이 만든 정답 대비 F1: **COBRAIN 0.73 vs COBREX 0.59**
- 사용자 연구 28명 중 80% 이상이 COBRAIN 의 규칙 설명이 더 이해하기 쉽다고 답함

**② Kalohia (ACL 2026 Industry Track)** — 금융권 COBOL·PL/I 340만 줄에, 결정론적 파싱 + 제어·데이터 흐름 분석으로 중간 표현을 만들고, 그 위에서 LLM 이 요구사항 문서를 생성하는 파이프라인([ACL Anthology](https://aclanthology.org/2026.acl-industry.4/)).

- 전문가가 작성한 업무 규칙과 일치율 **93%**
- 문서화 노력 약 **70% 감소**, 분석 속도 약 **3.2~3.3배**
- 핵심은 **코드로 되돌아가는 추적성(traceability)** — 생성된 규칙마다 근거 코드 위치가 붙는다

**③ AgentModernize (arXiv 2605.17535)** — 추출·명세·생성·검증 에이전트 4개로 레거시를 현대화([arXiv](https://arxiv.org/abs/2605.17535)).

- 규칙 추출 단계는 정답 규칙의 **92.3% 를 정밀도 90.2%** 로 잡았다
- 그런데 저자들의 결론은 **"병목은 추출이 아니라 코드 생성"**
- 더 강한 모델일수록 복잡한 파이프라인의 이점이 줄었다

세 연구를 겹쳐 보면 메시지가 일관된다.

1. **LLM 은 규칙을 "읽는" 데는 이미 꽤 쓸 만하다.** 사람이 읽기 좋은 설명을 쓰는 데는 기존 도구보다 낫다.
2. **좋은 결과는 LLM 혼자가 아니라 결정론적 분석 위에서 나왔다.** 파싱·흐름 분석으로 재료를 정리하고, LLM 은 그걸 사람 말로 옮긴다.
3. **추적성이 신뢰의 근거다.** 규칙마다 "이 코드 몇 번째 줄에서 나왔다" 가 붙어야 고객이 검증할 수 있다.

이 세 가지는 REA 가 하네스로서 하는 일과 정확히 겹친다 — 도구로 사실을 모으고, 결과에 출처 위치를 붙이고, 관찰과 추론을 나눈다.

## 4. FDE 의 리버스 엔지니어링 절차 — 하네스를 끼우면

고객 현장에서 실제로 쓸 수 있는 순서로 정리하면 이렇다.

### 0단계 — 권한부터 문서로 받는다

리버스 엔지니어링은 법적 경계가 있는 일이다([10-22 글 5절]({% post_url 2026-10-22-rea-reverse-engineering-harness %}) 참고). FDE 는 고객 시스템을 분석할 **서면 권한**을 먼저 받는다. 서드파티 상용 바이너리가 섞여 있으면 그 라이선스가 역분석을 금지하는지도 확인한다. 그리고 REA 문서가 직접 경고하듯 **분석 결과는 모델 제공자에게 전송된다.** 고객 데이터 정책과 맞는지, 사내 모델을 써야 하는지 이때 정한다.

### 1단계 — 바깥에서 본다 (블랙박스)

코드를 열기 전에 **입력과 출력**부터 기록한다. API 트래픽, 배치 입출력 파일, DB 변경 로그. REA 는 기록된 패킷 분석을 지원하므로 이 단계부터 쓸 수 있다.

### 2단계 — 구조를 그린다 (리버스 엔지니어링)

소스가 있으면 정적 분석, 없으면 디컴파일. 목표는 **진입점 → 호출 경로 → 데이터 저장소** 지도다. 하네스의 증거 레코드를 그대로 쌓아 두면 나중에 "이 판단 어디서 나왔어?" 에 답할 수 있다.

### 3단계 — 규칙을 뽑는다 (디자인 리커버리)

LLM 으로 규칙 후보 목록을 만들되, 각 항목을 세 칸으로 나눈다.

| 규칙 | 상태 | 근거 |
|---|---|---|
| 주문 3만원 이상 VIP 무료배송 | **관찰됨** | `ShipFee.calc()` 분기 + 트래픽 샘플 12건 |
| 공휴일엔 정산일 다음 영업일로 | **추론** | 휴일 테이블 조회 코드만 있음, 실제 사례 미확인 |
| 해외 주문 수수료 처리 | **모름** | 외부 DLL 호출, 내부 확인 불가 |

**"모름" 칸을 지우지 않는 게 핵심이다.** 고객 담당자 인터뷰 목록이 바로 여기서 나온다.

### 4단계 — 테스트로 굳힌다

Michael Feathers 가 말한 **특성화 테스트(characterization test)** 를 쓴다. 그의 표현으로는 "The purpose of characterization testing is to document your system's actual behavior" 이고, "When a system goes into production, in a way, it becomes its own specification" 이다([Feathers, 2016](https://michaelfeathers.silvrback.com/characterization-testing)).

3단계의 "관찰됨" 규칙을 **현재 동작 그대로** 테스트로 박는다. 맞는 동작인지는 따지지 않는다. 이 테스트가 있어야 4단계 이후에 무엇을 바꿔도 **원래 무엇을 했는지**를 잃지 않는다.

### 5단계 — 조금씩 바꾼다

새 기능이나 이관은 한 번에 갈아엎지 않고, 기존 시스템 앞에 새 경로를 세워 기능 단위로 넘긴다. Martin Fowler 의 [Strangler Fig](https://martinfowler.com/bliki/StranglerFigApplication.html) 패턴이다. 특성화 테스트가 새 경로와 옛 경로의 결과를 비교하는 기준이 된다.

## 5. FDE 에게 하네스가 특히 중요한 이유

제품 개발자에게 에이전트가 틀리면 다음 리뷰에서 잡힌다. FDE 에게는 그 안전망이 약하다.

- **검증해 줄 원작자가 없다.** 에이전트가 "이 함수는 할인을 계산합니다" 라고 확신 있게 말해도 반박할 사람이 없다.
- **틀린 규칙이 고객 문서가 된다.** FDE 가 넘긴 규칙 목록은 고객 쪽에서 사실로 받아들여지기 쉽다. 틀린 확신이 계약서·이관 계획에 들어간다.
- **시간 압박이 크다.** 빨리 이해해야 하는 직무라 "에이전트가 그렇다는데" 로 넘어가고 싶은 유혹이 크다.

그래서 FDE 에게 필요한 건 더 똑똑한 모델보다 **"본 것과 추측한 것을 나눠서 보여 주는 구조"** 다. 3절의 연구 셋이 모두 추적성을 강조한 것, REA 가 증거 레코드를 핵심으로 내세운 것이 같은 이유다.

## 6. 정리

| 질문 | 답 |
|---|---|
| FDE 의 첫 일은? | 고객 시스템이 **실제로** 무엇을 하는지 알아내는 것. 즉 리버스 엔지니어링 |
| 무엇을 넘겨야 하나? | 디컴파일 결과가 아니라 **근거가 붙은 업무 규칙 목록** |
| LLM 은 쓸 만한가? | 규칙 읽기와 설명은 이미 쓸 만하다. 단 결정론적 분석 위에서, 출처를 붙여서 |
| REA 같은 하네스의 역할은? | 도구 호출을 통일하고, 결과를 **관찰·추론·모름**으로 나눈다 |
| 마지막 안전장치는? | 특성화 테스트. 바꾸기 전에 **지금 동작**을 테스트로 굳힌다 |

1990년 정의에서 리버스 엔지니어링은 "대상을 바꾸지 않고 더 높은 수준으로 다시 그리는 일" 이었다. FDE 는 그 그림을 **고객이 믿고 결정을 내릴 수 있는 수준**까지 그려야 하는 직무다. 에이전트가 그리는 속도는 빨라졌다. 그래서 선마다 "본 것인지 추측한 것인지" 표시하는 일이 그만큼 더 중요해졌다.

## References

- E. J. Chikofsky, J. H. Cross II, "Reverse engineering and design recovery: a taxonomy", *IEEE Software*, 7(1), pp. 13–17, 1990. <https://doi.org/10.1109/52.43044>
- Palantir, Forward Deployed Software Engineer (채용 공고): <https://jobs.lever.co/palantir/98b81271-9e15-40b7-8dce-0c62f24702f9>, 신입 공고: <https://jobs.lever.co/palantir/341d5cae-a473-4813-9a6c-0f67fcc1b253>
- Chiranjeevi B S, S. Chimalakonda, "LLM Vs Rule-Based — The COBRAIN Tool and An Empirical Study on Extracting Business Rules from COBOL", EASE 2025. <https://conf.researchr.org/details/ease-2025/ease-2025-research-papers/57/LLM-Vs-Rule-Based-The-COBRAIN-Tool-and-An-Empirical-Study-on-Extracting-Business-Ru>
- A. Kalohia, "Leveraging Generative AI for Extracting Business Requirements from Legacy COBOL and PL/I Code", ACL 2026 Industry Track, pp. 43–55. <https://aclanthology.org/2026.acl-industry.4/>
- S. N. Ahmed, M. Galib, "AgentModernize: Preserving Business Logic in Legacy Modernization with Multi-Agent LLMs and Behavioral Specification Graphs", arXiv:2605.17535. <https://arxiv.org/abs/2605.17535>
- M. Feathers, "Characterization Testing" (2016). <https://michaelfeathers.silvrback.com/characterization-testing>
- M. Fowler, "Strangler Fig Application". <https://martinfowler.com/bliki/StranglerFigApplication.html>
- morluto/rea (REA, Reverse Engineer Anything). <https://github.com/morluto/rea>
