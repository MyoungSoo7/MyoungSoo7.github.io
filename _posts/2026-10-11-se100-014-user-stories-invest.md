---
layout: post
title: "[SE100 #014] 사용자 스토리와 INVEST 기준"
date: 2026-10-11 16:56:28 +0900
categories: [software-engineering]
tags: [se100, requirements, user-story, invest, story-splitting]
---

소프트웨어 공학 100 주제 시리즈의 14번째 글이다. (카테고리: 요구사항 공학)

## 한 줄 요약

사용자 스토리는 요구사항 문서가 아니라 **대화를 약속하는 카드**다. INVEST 는 그 카드가 계획 단위로 쓸 만한지 따지는 여섯 가지 기준이고, 실무 기술의 대부분은 큰 스토리를 INVEST 를 지키며 **세로로 자르는** 데 있다.

## 왜 필요한가

"As a … I want … so that …" 템플릿은 [요구사항 분석]({% post_url 2026-10-10-cs300-183-requirements-analysis %}) 글에서 봤다. 템플릿을 채우는 것 자체는 쉽다. 문제는 그 뒤에 생긴다.

- 스토리가 "결제 기능 개발" 처럼 커서 두 스프린트를 넘긴다. 진척률은 90% 에서 멈춘다.
- "API 만들기", "DB 테이블 만들기", "화면 만들기" 로 **가로로** 잘라 셋 다 끝나야 가치가 생긴다.
- 스토리 카드에 상세 명세를 다 적어 와서 개발자와의 대화가 사라진다. 카드가 계약서가 된다.
- "관리자로서 나는 관리하고 싶다, 그래야 관리할 수 있다" 같은 공허한 문장이 템플릿만 채운다.

INVEST 는 이 실패들을 미리 거르는 체크리스트다.

## 핵심 개념

### 출발점: XP 의 스토리, 카드·대화·확인

Martin Fowler 의 [UserStory](https://martinfowler.com/bliki/UserStory.html) 설명에 따르면, Kent Beck 이 Extreme Programming 의 일부로 이 용어를 도입했고, 그 목적은 긴 문서 대신 **더 비공식적이고 대화적인** 요구 도출이었다. 스토리는 개발할 준비가 될 때까지 일부러 상세화하지 않는다.

Ron Jeffries 는 2001년 글 [Essential XP: Card, Conversation, Confirmation](https://ronjeffries.com/xprog/articles/expcardconversationconfirmation/) 에서 스토리의 세 요소를 이렇게 정리했다.

| 요소 | 역할 | 흔한 실패 |
|---|---|---|
| 카드(Card) | 요구를 **식별하고 상기시킬** 만큼의 글 | 카드에 명세를 다 쓴다 |
| 대화(Conversation) | 고객과 개발자가 계획·이터레이션 중 나누는 논의 | 대화 없이 카드만 넘긴다 |
| 확인(Confirmation) | 고객이 정의한 **인수 테스트** | "완료" 의 기준이 없다 |

카드는 대화의 **약속**이다. 요구의 실체는 대화에 있고, 대화의 결론은 확인(인수 기준, SE100 #015)으로 남는다.

### 세 부분 템플릿의 출처

Mike Cohn 은 [자기 블로그](https://www.mountaingoatsoftware.com/agile/why-the-three-part-user-story-template-works-so-well)에서 "As a …, I … so that …" 템플릿이 2000년대 초 영국 회사 Connextra 에서 애자일 코치 Rachel Davies 에게서 나왔다고 쓴다. 세 부분은 누가(who), 무엇을(what), 왜(why)다. 템플릿은 의무가 아니다. 다만 "왜" 를 강제로 생각하게 만든다는 점이 핵심 가치다. "왜" 를 쓸 수 없는 스토리는 가치가 불분명하다는 신호다.

### INVEST — 원문 그대로 읽기

Bill Wake 가 2003년에 쓴 [INVEST in Good Stories, and SMART Tasks](https://xp123.com/articles/invest-in-good-stories-and-smart-tasks/) 의 정의를 옮긴다.

| 글자 | 기준 | Wake 의 설명 요지 | 실무 점검 질문 |
|---|---|---|---|
| I | Independent | 개념이 겹치지 않고, **어떤 순서로든** 일정을 잡을 수 있다 | 이 스토리만 먼저 해도 되는가? |
| N | Negotiable | 세부는 개발 중 고객과 프로그래머가 **함께 만든다** | 카드가 해법을 못 박고 있지 않은가? |
| V | Valuable | 개발자가 아니라 **고객에게** 가치가 있다 | 이것만 배포해도 누군가 좋아지는가? |
| E | Estimable | 고객이 순위를 매기고 일정을 잡을 만큼 추정 가능하다 | 모르는 게 너무 많아 감도 안 오지 않는가? |
| S | Small | 많아야 몇 인-주(person-week) 분량 | 한 스프린트 안에 여러 개가 끝나는가? |
| T | Testable | "테스트를 쓸 수 있을 만큼 원하는 걸 이해한다" | 인수 기준을 쓸 수 있는가? |

같은 글의 후반부는 스토리를 나눈 **작업(task)**에 SMART(Specific, Measurable, Achievable, Relevant, Time-boxed)를 쓰라고 한다. INVEST 는 스토리용, SMART 는 작업용이다. 둘을 섞으면 "API 엔드포인트 작성" 같은 작업이 스토리 자리를 차지한다.

### 기준 사이의 긴장

INVEST 의 여섯 글자는 서로 당긴다.

```
   Small ◀──── 잘게 자를수록 ────▶ Independent 가 깨지기 쉽다
     │                                  (앞 조각이 있어야 뒤 조각이 의미)
     │
   Valuable ◀── 가로로 자르면 ──▶ 조각 하나하나는 가치가 없다
     │
   Estimable ◀── 미지수가 크면 ──▶ 스파이크(조사 작업)로 먼저 줄인다
```

그래서 자르는 방향이 중요하다. **세로로 자른다.** 화면·API·DB 를 모두 얇게 관통해 사용자에게 보이는 결과를 내는 조각을 만든다.

### 스토리 품질 연구: QUS 프레임워크

Lucassen 등은 Requirements Engineering 저널 논문 [Improving agile requirements: the Quality User Story framework and tool](https://research-portal.uu.nl/en/publications/improving-agile-requirements-the-quality-user-story-framework-and/) ([DOI](https://doi.org/10.1007/s00766-016-0250-x), 2016)에서 사용자 스토리가 실제로는 자주 품질 결함을 보인다는 관찰에서 출발해, 스토리 작성자가 따라야 할 **13가지 품질 기준**(QUS)과, 자연어 처리로 결함을 찾아 고칠 방법을 제안하는 도구 AQUSA 를 내놓았다. INVEST 가 계획 단위로서의 적합성을 본다면, QUS 는 문장 자체(형식이 잘 갖춰졌나, 한 스토리에 한 요구인가, 해법을 섞지 않았나 등)를 본다.

### 스토리 맵

백로그는 1차원 목록이라 전체 흐름이 안 보인다. Jeff Patton 의 [스토리 맵](https://jpattonassociates.com/story-mapping/)(책 *User Story Mapping*, O'Reilly, 2014)은 사용자 활동을 가로축(흐름), 상세 스토리를 세로축(중요도)에 놓는다. 가로로 한 줄을 그으면 그 위가 첫 릴리스다. 이렇게 하면 "로그인부터 결제까지 얇게라도 다 이어진" 첫 릴리스를 고를 수 있다.

```
활동:   메뉴 보기 │ 담기     │ 결제          │ 픽업 알림
───────────────────────────────────────────────────────
릴리스1  목록     │ 1잔 담기 │ 카드 1종       │ 번호 표시
──────────────────────────────── (선) ─────────────────
릴리스2  검색     │ 옵션     │ 간편결제       │ 푸시
         즐겨찾기  │ 여러 잔  │ 포인트         │ 예상 시간
```

## 실무 적용

### 세로 자르기 패턴

| 자르는 축 | 큰 스토리 | 조각 |
|---|---|---|
| 업무 흐름 단계 | 주문하고 결제하고 픽업한다 | 주문 접수만 / 결제 추가 / 픽업 알림 추가 |
| 규칙 변형 | 할인 정책을 적용한다 | 정률 할인 / 정액 할인 / 중복 할인 규칙 |
| 데이터 변형 | 여러 결제 수단을 받는다 | 카드 1종 → 간편결제 → 포인트 |
| 성공/실패 경로 | 결제한다 | 성공 경로 / 승인 거절 / 타임아웃 복구 |
| 품질 수준 미루기 | 1초 안에 검색된다 | 우선 동작하는 검색 / 성능 개선 스토리 별도 |
| 불확실성 분리 | 외부 배송사와 연동한다 | 스파이크: API 조사(타임박스) → 연동 스토리 |

유스케이스가 있다면 주 성공 시나리오, 확장 하나하나가 자연스러운 조각이다(SE100 #013).

### 리파인먼트에서 쓰는 점검 스크립트

자동 판정은 불가능하지만, 명백한 냄새는 기계로 거를 수 있다.

```python
import re

def smells(story: str) -> list[str]:
    s = story.strip()
    out = []
    m = re.match(r"(.+?)(으?로서|로서),\s*(.+?)(고 싶다|원한다)[.,]?\s*(그래야|왜냐하면)?\s*(.*)", s)
    if not m:
        return ["템플릿 형식이 아님(누가/무엇/왜 분리 불가)"]
    who, what, why = m.group(1), m.group(3), m.group(6)
    if who.strip() in {"사용자", "유저", "관리자"}:
        out.append(f"역할이 너무 일반적: '{who.strip()}' — 누구인지 구체화")
    if not why:
        out.append("'왜' 가 없음 → Valuable 판단 불가")
    if re.search(r"(API|DB|테이블|엔드포인트|리팩터링)", what):
        out.append("기술 작업처럼 보임 → 스토리가 아니라 작업(task)일 수 있음")
    if re.search(r"(그리고|및|,\s*또)", what):
        out.append("한 스토리에 여러 요구 → 자르기 후보(Small)")
    return out

for st in [
    "단골 고객으로서, 지난번 주문을 한 번에 다시 담고 싶다. 그래야 매번 옵션을 고르지 않는다.",
    "관리자로서, 메뉴와 가격 및 재고를 관리하고 싶다.",
    "사용자로서, 주문 API 를 호출하고 싶다. 그래야 주문이 된다.",
]:
    print("-", st)
    for x in smells(st) or ["특이사항 없음"]:
        print("   ", x)
```

```
- 단골 고객으로서, 지난번 주문을 한 번에 다시 담고 싶다. 그래야 매번 옵션을 고르지 않는다.
    특이사항 없음
- 관리자로서, 메뉴와 가격 및 재고를 관리하고 싶다.
    역할이 너무 일반적: '관리자' — 누구인지 구체화
    '왜' 가 없음 → Valuable 판단 불가
    한 스토리에 여러 요구 → 자르기 후보(Small)
- 사용자로서, 주문 API 를 호출하고 싶다. 그래야 주문이 된다.
    역할이 너무 일반적: '사용자' — 누구인지 구체화
    기술 작업처럼 보임 → 스토리가 아니라 작업(task)일 수 있음
```

이 스크립트는 대화를 대신하지 않는다. 리파인먼트 전에 명백한 문제를 걸러 **대화 시간을 아끼는** 용도다. [스크럼 가이드](https://www.scrumguides.org/scrum-guide.html)는 백로그 리파인먼트를 항목을 더 작고 정확한 항목으로 쪼개고 상세화하는 **지속적인 활동**으로 정의한다. 한 번의 회의가 아니다.

## 흔한 오해와 함정

- **"스토리 = 템플릿 문장."** 템플릿은 카드다. 대화와 확인이 빠진 스토리는 짧아진 명세서일 뿐이다.
- **기술 계층별 스토리.** "백엔드 스토리", "프론트 스토리" 로 나누면 V 와 I 가 동시에 깨진다. 기술 작업은 스토리 안의 작업으로 둔다.
- **Negotiable 을 "아무 때나 바꿔도 된다" 로 읽는다.** 협상 대상은 **세부와 해법**이다. 스프린트 중 목표 자체를 바꾸는 것은 다른 문제다.
- **Small 을 시간으로만 본다.** 작아도 가치가 없으면(V) 의미가 없다. "버튼 색 바꾸기" 열 개보다 얇은 세로 조각 하나가 낫다.
- **추정이 안 되면 그냥 크게 잡는다.** E 가 안 되는 이유는 대개 미지수다. 타임박스 조사(스파이크)로 미지수를 먼저 줄인다.

## 확인 문제

1. Jeffries 의 세 C 중 "카드" 의 역할은 무엇이고, 카드에 상세 명세를 다 적으면 무엇이 깨지는가?
2. Wake 의 원문에서 Valuable 은 "누구에게" 가치가 있어야 한다고 하는가?
3. INVEST 에서 Small 과 Independent 가 충돌하는 상황을 하나 들어 보라.
4. "회원가입 API 개발 / 회원가입 화면 개발" 로 나눈 스토리를 세로로 다시 자르라.
5. INVEST 와 QUS 프레임워크가 보는 관점의 차이는?

### 풀이

1. 요구를 식별하고 대화를 상기시키는 표식이다. 명세를 다 적으면 대화가 사라지고 Negotiable 이 깨지며, 카드가 계약서처럼 쓰인다.
2. 개발자가 아니라 고객(사용자·구매자)에게.
3. 결제 기능을 "결제 요청 화면" 과 "결제 결과 처리" 로 잘게 자르면, 뒤 조각은 앞 조각이 있어야만 의미가 있어 순서 독립성이 깨진다.
4. 예: "이메일로 가입한다(최소 필드, 화면+API+저장 모두 포함)" → "가입 시 이메일 인증을 한다" → "소셜 계정으로 가입한다". 각 조각이 배포하면 사용자에게 보인다.
5. INVEST 는 스토리가 계획 단위로 적합한지(독립성, 크기, 추정 가능성 등)를 보고, QUS 는 스토리 문장 자체의 품질(형식, 단일성, 해법 혼입 등)을 13가지 기준으로 본다.

## 더 읽을거리 (References)

- Bill Wake, [INVEST in Good Stories, and SMART Tasks](https://xp123.com/articles/invest-in-good-stories-and-smart-tasks/), 2003
- Ron Jeffries, [Essential XP: Card, Conversation, Confirmation](https://ronjeffries.com/xprog/articles/expcardconversationconfirmation/), 2001
- Martin Fowler, [UserStory](https://martinfowler.com/bliki/UserStory.html)
- Mike Cohn, [Why the Three-Part User Story Template Works So Well](https://www.mountaingoatsoftware.com/agile/why-the-three-part-user-story-template-works-so-well); *User Stories Applied*, Addison-Wesley, 2004 (서지 정보)
- G. Lucassen, F. Dalpiaz, J. M. E. M. van der Werf, S. Brinkkemper, [Improving agile requirements: the Quality User Story framework and tool](https://doi.org/10.1007/s00766-016-0250-x), Requirements Engineering 21(3), 2016
- Jeff Patton, [Story Mapping](https://jpattonassociates.com/story-mapping/); *User Story Mapping*, O'Reilly, 2014 (서지 정보)
- [The Scrum Guide (2020)](https://www.scrumguides.org/scrum-guide.html)
- CS300: [애자일과 스크럼]({% post_url 2026-10-10-cs300-182-agile-and-scrum %})
