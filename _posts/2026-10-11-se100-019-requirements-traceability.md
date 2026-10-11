---
layout: post
title: "[SE100 #019] 요구사항 추적성 — 요구에서 테스트까지"
date: 2026-10-11 16:56:34 +0900
categories: [software-engineering]
tags: [se100, requirements, traceability, verification, impact-analysis]
---

소프트웨어 공학 100 주제 시리즈의 19번째 글이다. (카테고리: 요구사항 공학)

## 한 줄 요약

추적성은 요구 하나의 **생애를 앞뒤로 따라갈 수 있는 능력**이다. 앞으로는 요구 → 설계 → 코드 → 테스트, 뒤로는 테스트 → 요구 → 그 요구를 낸 사람과 이유. 링크를 많이 만드는 것이 목적이 아니라, "이걸 바꾸면 무엇이 영향을 받나" 와 "이건 왜 여기 있나" 에 몇 분 안에 답하는 것이 목적이다.

## 왜 필요한가

추적성이 없는 팀에서 자주 듣는 질문들이 있다.

- "결제 타임아웃을 10초에서 5초로 바꾸면 어떤 테스트와 화면을 고쳐야 하죠?" — 아무도 모른다. 코드 검색으로 `10` 을 찾아 헤맨다.
- "이 이상한 예외 처리는 왜 있는 거죠? 지워도 되나요?" — 만든 사람은 퇴사했다. 지웠더니 석 달 뒤 정산 오류가 난다.
- "요구사항 다 구현했나요?" — "아마도요." 검증되지 않은 요구가 몇 개인지 셀 방법이 없다.
- 감사·인증 담당자가 "이 안전 요구를 검증한 테스트 결과를 보여 주세요" 라고 하면, 몇 주간 문서 작업이 시작된다.

[요구사항 분석]({% post_url 2026-10-10-cs300-183-requirements-analysis %}) 글에서 추적성의 개념을 한 단락으로 소개했다. 이 글은 원전의 정의, 방향과 종류, 그리고 **유지되는** 추적성을 만드는 법을 다룬다.

## 핵심 개념

### 원전의 정의

Orlena Gotel 과 Anthony Finkelstein 의 1994년 논문 [An Analysis of the Requirements Traceability Problem](http://csis.pace.edu/~ogotel/research/GOTEL94%20An%20Analysis%20of%20the%20Requirements%20Traceability%20Problem.pdf) (ICRE '94, [DOI](https://doi.org/10.1109/ICRE.1994.292398))은 지금도 가장 많이 인용되는 정의를 내놓았다.

> 요구사항 추적성이란 요구사항의 생애를 앞 방향과 뒤 방향 모두로 기술하고 따라갈 수 있는 능력을 말한다.

이 논문은 100명 넘는 실무자가 참여한 실증 조사를 바탕으로, 추적성을 두 종류로 나눴다.

| 종류 | 정의(논문) | 다루는 것 | 예 |
|---|---|---|---|
| Pre-RS 추적성 | 요구사항이 명세(RS)에 **들어가기 전**의 생애 | 요구의 생산: 출처, 논의, 결정, 근거 | "이 요구는 2분기 고객 인터뷰와 법무 검토에서 나왔다" |
| Post-RS 추적성 | 명세에 **들어간 결과**로 생기는 생애 | 요구의 배치: 설계, 코드, 테스트 | "REQ-PAY-002 는 이 모듈과 이 테스트로 구현·검증된다" |

논문의 핵심 주장은 추적성 부족 탓으로 돌려지는 문제의 **대부분이 Pre-RS 추적성의 부족**에서 온다는 것이었다. "이 요구는 왜 있나" 에 답하지 못하는 문제다. 30년이 지난 지금도 대부분의 팀이 요구 ↔ 테스트 링크는 만들지만, 요구 ↔ 근거 링크는 만들지 않는다.

### 방향: 양방향 추적

NASA 시스템 공학 핸드북의 [요구사항 관리 절](https://www.nasa.gov/reference/6-2-requirements-management/)은 요구사항 관리 프로세스의 목적 중 하나로 **양방향 추적성**을 들고, 이렇게 정의한다.

- 추적성: 요구사항, 시스템 요소, 검증, 작업 같은 둘 이상의 논리적 실체 사이의 식별 가능한 연관.
- 양방향 추적성: 어떤 요구든 그 **부모** 요구로, 그리고 할당된 **자식** 요구로 추적할 수 있는 능력.

```
            뒤 방향(왜?)                         앞 방향(어디에?)
 이해관계자 필요 ◀── 시스템 요구 ◀── 소프트웨어 요구 ──▶ 설계 ──▶ 코드 ──▶ 테스트
   STK-03          SYS-12          REQ-PAY-002        결제모듈   PaymentPoller  test_timeout
```

양방향이어야 두 가지 결함을 모두 잡는다.

| 결함 | 어느 방향으로 찾나 | 의미 |
|---|---|---|
| 고아 요구 (자식 없음) | 앞 방향 | 구현되지 않았거나 검증되지 않은 요구 |
| 고아 산출물 (부모 없음) | 뒤 방향 | 근거 없는 코드·테스트 — 금도금(gold plating)이거나 문서화되지 않은 요구 |

### 추적성이 필수인 곳

항공·우주·의료·자동차 같은 안전 중요 분야에서는 추적성이 인증의 일부다. 예를 들어 항공기 소프트웨어 인증의 핵심 문서인 RTCA [DO-178()](https://www.rtca.org/do-178/) 계열은 1981년 처음 나왔고, 현행 DO-178C 는 2011년판으로 미국 연방항공청(FAA)의 자문 회람 AC 20-115D 가 참조한다. 이런 분야에서는 요구-코드-테스트 사이의 추적 증거를 심사에 제출해야 한다.

일반 웹 서비스에는 그 수준이 필요 없다. 하지만 **변경 영향 분석**과 **미검증 요구 찾기**라는 이점은 그대로다.

### 무엇을 얼마나 추적할까

Ramesh 와 Jarke 의 [Toward reference models for requirements traceability](https://doi.org/10.1109/32.895989) (IEEE TSE, 2001)는 추적 정보의 종류를 참조 모델로 정리한 대표 연구다. 실무 판단은 단순하게 하는 편이 낫다.

| 링크 | 비용 | 가치 | 권장 |
|---|---|---|---|
| 요구 → 인수 테스트 | 낮음(테스트에 ID 태그) | 높음(미검증 요구 탐지) | 모든 팀 |
| 요구 → 근거·출처 | 낮음(요구 기록에 칸 하나) | 높음("왜 있나") | 모든 팀 |
| 요구 → 코드 커밋 | 낮음(커밋 메시지 규칙) | 중간(변경 이력) | 대부분 |
| 요구 → 설계 요소 | 중간 | 중간 | 아키텍처가 복잡할 때 |
| 요구 → 코드 함수 단위 | 높음(유지 비용 큼) | 상황에 따라 | 규제 분야 |

원칙: **링크는 산출물을 만들 때 함께 만든다.** 나중에 문서 작업으로 링크를 채우면 반드시 낡는다.

## 실무 적용

### 테스트에 요구 ID 를 단다

추적 링크를 별도 엑셀이 아니라 **코드 안**에 둔다. 요구 기록은 리포지토리의 YAML 로, 링크는 테스트 마커로.

```yaml
# requirements.yaml
- id: REQ-PAY-001
  text: 결제가 승인되면 주문 앱은 주문 번호를 표시해야 한다
  source: STK-03
- id: REQ-PAY-002
  text: 승인 응답이 10초 안에 오지 않으면 주문 앱은 결제 상태를 조회해야 한다
  source: STK-03
- id: REQ-PAY-003
  text: 같은 주문의 결제 승인은 한 번만 반영해야 한다
  source: ES-HOTSPOT-7          # 이벤트 스토밍 핫스팟에서 나옴(Pre-RS 추적)
```

```python
# tests/test_payment.py  (pytest.ini 에 markers = req(id): requirement id 등록)
import pytest

@pytest.mark.req("REQ-PAY-001")
def test_shows_order_number_after_approval(): ...

@pytest.mark.req("REQ-PAY-003")
def test_duplicate_approval_is_ignored(): ...

def test_receipt_format(): ...          # 어떤 요구에도 연결되지 않음
```

### 추적 매트릭스를 생성한다

테스트를 실행하지 않고 소스만 정적으로 읽어 매트릭스를 만든다. CI 에서 매번 돌리면 매트릭스가 낡지 않는다.

```python
# trace.py
import ast, pathlib, re

# 요구 목록 읽기 (예제를 단순하게 하려고 YAML 파서 대신 정규식)
reqs = dict(re.findall(r"- id: (\S+)\n  text: (.+)",
                       pathlib.Path("requirements.yaml").read_text()))

# 테스트 코드에서 @pytest.mark.req("...") 를 정적으로 수집
links, untraced = {}, []
for f in pathlib.Path("tests").glob("test_*.py"):
    for node in ast.walk(ast.parse(f.read_text())):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            ids = [d.args[0].value for d in node.decorator_list
                   if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "req"]
            for rid in ids:
                links.setdefault(rid, []).append(f"{f.name}::{node.name}")
            if not ids:
                untraced.append(f"{f.name}::{node.name}")

print("요구 ID       | 테스트")
for rid in reqs:
    print(f"{rid:<13} | {', '.join(links.get(rid, [])) or '— (검증 없음)'}")
print("\n요구에 연결되지 않은 테스트:", untraced)
print("존재하지 않는 요구를 가리키는 링크:", sorted(set(links) - set(reqs)))
```

```
요구 ID       | 테스트
REQ-PAY-001   | test_payment.py::test_shows_order_number_after_approval
REQ-PAY-002   | — (검증 없음)
REQ-PAY-003   | test_payment.py::test_duplicate_approval_is_ignored

요구에 연결되지 않은 테스트: ['test_payment.py::test_receipt_format']
존재하지 않는 요구를 가리키는 링크: []
```

세 줄의 출력이 각각 다른 결함을 알려 준다.

1. **REQ-PAY-002 검증 없음** — 앞 방향 고아. 타임아웃 복구는 위험이 큰 요구인데 테스트가 없다.
2. **test_receipt_format 미연결** — 뒤 방향 고아. 영수증 형식 요구가 문서에 빠졌거나, 필요 없는 테스트다. 어느 쪽인지 확인한다.
3. **없는 요구를 가리키는 링크** — 요구가 삭제·개명됐는데 테스트는 그대로인 경우. 지금은 0건이다.

CI 에서는 1번과 3번을 실패로, 2번을 경고로 두는 식으로 시작한다. 규모가 커지면 [OpenFastTrace](https://github.com/itsallcode/openfasttrace) 같은 전용 추적 도구를 검토한다.

### 커밋과 PR 규칙

```
feat(payment): 승인 타임아웃 시 결제 상태 조회 (REQ-PAY-002)

결제 대행사 응답이 10초를 넘으면 상태 조회 API 로 확인한다.
```

요구 ID 를 커밋 메시지에 넣으면 `git log --grep REQ-PAY-002` 로 그 요구의 구현 이력이 나온다. 변경 영향 분석의 출발점이 된다.

## 흔한 오해와 함정

- **추적 매트릭스를 문서로 관리한다.** 손으로 유지하는 스프레드시트는 첫 리팩터링에서 낡는다. 링크는 코드·테스트·커밋 안에 두고 매트릭스는 생성한다.
- **Post-RS 만 추적한다.** 테스트 링크만 있으면 "구현했나" 에는 답해도 "왜 있나" 에는 못 답한다. 출처·근거 칸은 비용이 거의 들지 않는다.
- **모든 것을 모든 것에 연결한다.** 함수 단위까지 연결하면 유지 비용이 가치를 넘는다. 위험과 규제 수준에 맞춰 입도를 정한다.
- **링크가 있으니 검증됐다고 본다.** 링크는 테스트가 요구를 **가리킨다**는 것만 보장한다. 테스트가 요구를 제대로 확인하는지는 리뷰가 판단한다.
- **ID 를 재사용한다.** 삭제된 요구의 ID 를 새 요구에 주면 과거 커밋과 테스트가 엉뚱한 요구를 가리킨다. ID 는 폐기만 한다.

## 확인 문제

1. Gotel 과 Finkelstein 의 정의에서 "앞 방향과 뒤 방향" 은 각각 무엇을 따라가는가?
2. Pre-RS 추적성이 없을 때 생기는 전형적인 문제는?
3. 앞 방향 고아와 뒤 방향 고아는 각각 어떤 결함을 뜻하는가?
4. 추적 매트릭스를 생성 방식으로 만들 때의 장점은?
5. 일반 웹 서비스 팀이 최소한으로 유지할 추적 링크 두 가지를 고르고 이유를 말하라.

### 풀이

1. 앞 방향은 요구에서 그것을 구현·검증하는 설계·코드·테스트로, 뒤 방향은 산출물에서 그것을 낳은 요구와 그 요구의 출처로 따라간다.
2. "이 요구(또는 이 코드)는 왜 있나" 에 답할 수 없다. 근거를 모르니 안전하게 바꾸거나 지울 수 없다.
3. 앞 방향 고아는 구현·검증되지 않은 요구, 뒤 방향 고아는 근거가 없는 산출물(문서화되지 않은 요구이거나 불필요한 작업)이다.
4. 링크가 산출물 안에 있어 코드와 함께 바뀌고, CI 에서 매번 다시 만들어지므로 낡지 않으며, 결함을 자동으로 경고할 수 있다.
5. 요구 → 인수 테스트(미검증 요구 탐지), 요구 → 근거·출처(변경·삭제 판단 근거). 둘 다 비용이 낮고 가치가 높다.

## 더 읽을거리 (References)

- O. Gotel, A. Finkelstein, [An Analysis of the Requirements Traceability Problem](http://csis.pace.edu/~ogotel/research/GOTEL94%20An%20Analysis%20of%20the%20Requirements%20Traceability%20Problem.pdf), ICRE 1994 ([DOI 10.1109/ICRE.1994.292398](https://doi.org/10.1109/ICRE.1994.292398))
- B. Ramesh, M. Jarke, [Toward reference models for requirements traceability](https://doi.org/10.1109/32.895989), IEEE TSE 27(1), 2001
- NASA, [Systems Engineering Handbook — 6.2 Requirements Management](https://www.nasa.gov/reference/6-2-requirements-management/)
- RTCA, [DO-178() Software Considerations in Airborne Systems and Equipment Certification](https://www.rtca.org/do-178/)
- [OpenFastTrace](https://github.com/itsallcode/openfasttrace)
- CS300: [CI/CD]({% post_url 2026-10-10-cs300-196-ci-cd %})
