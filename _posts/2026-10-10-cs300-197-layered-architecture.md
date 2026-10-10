---
layout: post
title: "[CS300 #197] 레이어드 아키텍처 — 표현·도메인·데이터를 층으로 나누고 의존 방향을 정하기"
date: 2026-10-10 21:17:00 +0900
categories: [cs]
tags: [cs300, software-engineering, layered-architecture, hexagonal-architecture, dependency-rule]
---

컴퓨터공학 300 주제 시리즈의 197번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

레이어드 아키텍처는 코드를 표현(UI·API), 도메인(비즈니스 규칙), 데이터(저장·외부 연동) 같은 층으로 나누고, **의존은 정해진 한 방향으로만** 흐르게 하는 구조다. 헥사고날(포트와 어댑터) 아키텍처는 여기서 한 걸음 더 나가, 도메인을 가운데 두고 데이터베이스까지도 바깥 어댑터로 밀어낸다.

## 왜 필요한가

작은 프로그램은 HTTP 요청을 받는 함수 안에서 SQL 을 날리고, 그 결과로 할인을 계산하고, HTML 을 만들어 돌려줘도 문제가 없다. 그런데 이 프로그램이 커지면 세 가지가 동시에 어려워진다.

- **이해**: 할인 규칙을 찾으려면 HTTP 처리 코드와 SQL 사이를 헤집어야 한다.
- **변경**: DB 를 바꾸거나 같은 기능을 배치 작업에서도 쓰려면 비즈니스 규칙까지 다시 써야 한다.
- **테스트**: 할인 계산 하나를 테스트하려고 웹 서버와 DB 를 띄워야 한다.

층을 나누면 한 번에 한 관심사만 생각할 수 있다. Martin Fowler 는 [Presentation Domain Data Layering](https://martinfowler.com/bliki/PresentationDomainDataLayering.html)에서 프로그램을 표현, 도메인 로직, 데이터 소스의 세 층으로 나누는 것이 정보 중심 프로그램을 모듈화하는 가장 흔한 방법 중 하나이며, 덕분에 세 주제를 비교적 독립적으로 생각할 수 있다고 설명한다.

## 핵심 개념

### 전형적인 3~4계층

```
┌─────────────────────────────┐
│ 표현 (Presentation)          │  HTTP 핸들러, 컨트롤러, CLI, 화면
├─────────────────────────────┤
│ 애플리케이션 (Service)        │  유스케이스 조율, 트랜잭션 경계
├─────────────────────────────┤
│ 도메인 (Domain)              │  엔티티, 비즈니스 규칙
├─────────────────────────────┤
│ 인프라 (Infrastructure/Data) │  DB 접근, 메시지 큐, 외부 API 클라이언트
└─────────────────────────────┘
        의존 방향: 위 → 아래
```

| 계층 | 하는 일 | 하지 말아야 할 일 |
|---|---|---|
| 표현 | 입력 파싱·검증, 응답 형식 변환 | 비즈니스 규칙 계산 |
| 애플리케이션 | "주문하기" 같은 유스케이스 순서 조율, 트랜잭션 | 세부 계산 규칙 보유(도메인에 위임) |
| 도메인 | 할인·재고·상태 전이 같은 핵심 규칙 | HTTP·SQL 을 아는 것 |
| 인프라 | 저장·조회, 외부 시스템 호출 | 비즈니스 판단 |

Fowler 의 *Patterns of Enterprise Application Architecture*([패턴 카탈로그](https://martinfowler.com/eaaCatalog/))에 나오는 서비스 계층(Service Layer), 리포지터리(Repository), 데이터 매퍼(Data Mapper) 같은 패턴이 각 층의 대표 구현이다.

### 엄격한 계층과 느슨한 계층

- **엄격한(strict) 계층**: 바로 아래 층만 호출할 수 있다. 표현은 애플리케이션만 부른다.
- **느슨한(relaxed) 계층**: 아래의 어느 층이든 호출할 수 있다. 표현이 도메인 객체를 직접 쓰기도 한다.

엄격할수록 경계가 분명하지만 단순 조회에도 모든 층을 통과하는 "통과만 하는 메서드" 가 늘어난다. 실무에서는 대부분 느슨한 쪽을 택하되, **위로 거슬러 올라가는 의존은 절대 허용하지 않는다.** 도메인이 웹 프레임워크를 import 하는 순간 층은 무너진다.

### 문제: 도메인이 DB 에 의존한다

전통적인 계층 그림에서는 도메인이 인프라(데이터) 위에 있다. 즉 도메인이 DB 접근 코드에 의존한다. 그러면 DB 기술을 바꿀 때 도메인이 영향을 받고, 도메인을 테스트하려면 DB 가 필요하다.

### 해법: 의존성 역전과 헥사고날 아키텍처

Alistair Cockburn 은 2005년 [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)(포트와 어댑터)에서 목표를 이렇게 적었다. 애플리케이션이 사용자, 프로그램, 자동화된 테스트, 배치 스크립트에 의해 **똑같이 구동될 수 있게** 하고, 실제 실행 시점의 장치와 데이터베이스로부터 **격리된 채 개발·테스트**될 수 있게 하라.

```
            [웹 어댑터]   [CLI 어댑터]   [테스트]
                  \           |          /
                   ▼          ▼         ▼
              ┌──── 입력 포트(유스케이스 인터페이스) ────┐
              │                                     │
              │           도메인 + 애플리케이션        │
              │                                     │
              └──── 출력 포트(OrderRepository 등) ────┘
                   ▲          ▲         ▲
                  /           |          \
          [PostgreSQL 어댑터] [메모리 어댑터] [외부 결제 API 어댑터]
```

- **포트**: 도메인이 정의하는 인터페이스. "주문을 저장할 수 있어야 한다(`OrderRepository`)".
- **어댑터**: 포트를 특정 기술로 구현한 것. "PostgreSQL 로 저장한다".

핵심은 화살표 방향이다. 인프라 어댑터가 도메인이 정의한 포트를 **구현**하므로, 의존이 바깥에서 안쪽(도메인)으로 향한다. SOLID 글의 의존성 역전 원칙을 아키텍처 수준에 적용한 것이다. 같은 생각을 Jeffrey Palermo 는 어니언 아키텍처로, Robert C. Martin 은 클린 아키텍처로 불렀다. 이름과 그림은 달라도 규칙은 하나다. **소스 코드 의존은 안쪽(정책)으로만 향한다.**

## 직접 해 보기

계층 규칙은 문서로만 두면 언젠가 깨진다. 코드로 검사하자. 파이썬 [`ast` 모듈](https://docs.python.org/3/library/ast.html)로 각 모듈의 import 문을 읽어 허용되지 않은 방향의 의존을 찾는 작은 아키텍처 테스트다.

```python
import ast

# 가상의 프로젝트: 모듈 이름 -> 소스 코드
SOURCES = {
    "app.web.order_api":        "from app.service.order_service import place_order\n",
    "app.service.order_service":"from app.domain.order import Order\nfrom app.domain.ports import OrderRepository\n",
    "app.domain.order":         "from dataclasses import dataclass\n",
    "app.domain.ports":         "from typing import Protocol\n",
    "app.infra.sql_repo":       "import sqlite3\nfrom app.domain.ports import OrderRepository\n",
    # 규칙 위반 두 건
    "app.domain.pricing":       "from app.infra.sql_repo import SqlOrderRepository\n",
    "app.web.admin_api":        "import app.infra.sql_repo\n",
}

LAYER_OF = lambda mod: mod.split(".")[1] if mod.startswith("app.") else None

# 각 계층이 의존해도 되는 계층(자기 자신 포함). domain 은 아무것도 모른다
ALLOWED = {
    "web":     {"web", "service", "domain"},
    "service": {"service", "domain"},
    "infra":   {"infra", "domain"},          # 인프라가 도메인의 포트를 구현한다
    "domain":  {"domain"},
}

def imports_of(src):
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module

violations = 0
for mod, src in SOURCES.items():
    me = LAYER_OF(mod)
    for target in imports_of(src):
        other = LAYER_OF(target)
        if other and other not in ALLOWED[me]:
            violations += 1
            print(f"위반: {mod} ({me}) -> {target} ({other})")
print(f"검사한 모듈 {len(SOURCES)}개, 위반 {violations}건")
```

실행 결과:

```
위반: app.domain.pricing (domain) -> app.infra.sql_repo (infra)
위반: app.web.admin_api (web) -> app.infra.sql_repo (infra)
검사한 모듈 7개, 위반 2건
```

첫 번째 위반이 치명적이다. 가격 계산이라는 핵심 규칙이 SQL 저장소 구현을 알게 됐다. 이제 가격 규칙을 테스트하려면 DB 가 필요하고, DB 를 바꾸면 가격 코드도 다시 확인해야 한다. 고치는 방법은 가격 계산에 필요한 데이터를 도메인의 포트(`OrderRepository` 같은 인터페이스)로 받거나, 애플리케이션 계층이 조회해서 인자로 넘기는 것이다.

`ALLOWED` 표에서 `infra` 가 `domain` 에 의존하는 것은 허용했다는 점도 보자. 전통적 계층 그림과 화살표가 반대다. 이것이 의존성 역전이다. 이런 검사를 테스트 스위트에 넣어 CI 에서 돌리면, 리뷰어가 import 한 줄을 놓쳐도 구조가 무너지지 않는다.

## 현업에서는

- **패키지 구조로 의도를 드러낸다.** `web/`, `service/`, `domain/`, `infra/` 처럼 계층별로 나누는 방식과, `order/`, `payment/` 처럼 기능별로 나누고 그 안에서 계층을 나누는 방식이 있다. 서비스가 커지면 기능별 분할이 변경을 한곳에 모으는 데 유리하다.
- **"얇은 컨트롤러, 두꺼운 도메인"** 이 흔한 목표다. 컨트롤러에 `if` 문이 쌓이기 시작하면 비즈니스 규칙이 표현 계층으로 새고 있다는 신호다.
- **조회 성능 때문에 층을 건너뛰고 싶을 때가 있다.** 대시보드용 복잡한 집계를 도메인 객체를 거쳐 만들면 느리다. 이럴 때 조회 전용 경로(쿼리 서비스)를 따로 두는 것은 흔한 타협이다. 다만 쓰기 경로의 규칙은 반드시 도메인을 거친다.
- **인프라 쪽 경계도 같다.** 홈랩 클러스터에서 앱이 쓰는 DB 를 바꿀 때, 앱이 저장소 어댑터 하나 뒤에 DB 접근을 모아 두었다면 바꿀 곳은 그 어댑터와 배포 설정뿐이다. 접근 코드가 핸들러마다 흩어져 있으면 전부 찾아야 한다.

## 확인 문제

1. 표현, 애플리케이션, 도메인, 인프라 계층이 각각 맡는 일을 한 줄씩 쓰라.
2. 엄격한 계층과 느슨한 계층의 차이는? 어느 쪽이든 절대 허용하지 않는 의존은?
3. 전통적 계층 구조에서 "도메인이 DB 에 의존한다" 는 것이 왜 문제인가?
4. 헥사고날 아키텍처에서 포트와 어댑터는 각각 무엇이며, 누가 무엇을 정의하는가?
5. 위 예제에서 `app.domain.pricing` 의 위반을 고치는 방법 하나를 제시하라.

### 풀이

1. 표현: 입력을 받고 응답을 만든다. 애플리케이션: 유스케이스의 순서와 트랜잭션을 조율한다. 도메인: 핵심 비즈니스 규칙을 담는다. 인프라: 저장과 외부 시스템 연동을 맡는다.
2. 엄격한 계층은 바로 아래 층만, 느슨한 계층은 아래 어느 층이든 호출할 수 있다. 아래 층이 위 층에 의존하는 역방향 의존은 둘 다 허용하지 않는다.
3. DB 기술을 바꾸면 비즈니스 규칙이 영향을 받고, 규칙을 테스트하려면 DB 가 필요해진다. 가장 오래 살아야 할 코드가 가장 자주 바뀌는 기술 세부에 묶인다.
4. 포트는 도메인(애플리케이션 핵심)이 정의하는 인터페이스이고, 어댑터는 그 포트를 특정 기술(웹, DB, 외부 API)로 구현한 것이다. 어댑터가 포트에 의존한다.
5. 가격 계산에 필요한 데이터를 도메인이 정의한 포트(인터페이스)로 받게 하고 인프라가 그 포트를 구현하게 하거나, 애플리케이션 계층이 데이터를 조회해 가격 계산 함수에 인자로 넘긴다.

## 더 읽을거리 (References)

- Martin Fowler, [Presentation Domain Data Layering](https://martinfowler.com/bliki/PresentationDomainDataLayering.html)
- Alistair Cockburn, [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) (2005)
- Martin Fowler, [Catalog of Patterns of Enterprise Application Architecture](https://martinfowler.com/eaaCatalog/)
- Python 문서, [ast — Abstract Syntax Trees](https://docs.python.org/3/library/ast.html)
- Robert C. Martin, *Clean Architecture: A Craftsman's Guide to Software Structure and Design*, Prentice Hall, 2017 (서지 정보)
