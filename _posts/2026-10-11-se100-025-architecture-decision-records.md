---
layout: post
title: "[SE100 #025] 아키텍처 결정 기록(ADR)"
date: 2026-10-11 16:58:09 +0900
categories: [software-engineering]
tags: [se100, software-architecture, adr, decision-making, documentation]
---

소프트웨어 공학 100 주제 시리즈의 25번째 글이다. (카테고리: 설계와 아키텍처)

## 한 줄 요약

ADR(Architecture Decision Record)은 **아키텍처적으로 중요한 결정 하나를, 그 맥락·결정·결과와 함께** 짧은 텍스트 파일로 남기는 관행이다. 코드 저장소에 번호를 붙여 쌓고, 결정이 바뀌면 고치지 않고 새 ADR 로 대체(superseded)한다.

## 왜 필요한가

Michael Nygard 는 ADR 을 대중화한 2011년 글 [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)에서 문제를 이렇게 설명한다. 새로 합류한 사람은 과거의 결정을 보고 당황하거나 화를 내는데, 그 근거와 결과를 모르면 선택지는 둘뿐이다.

- **맹목적으로 받아들인다.** 결정이 여전히 유효하면 괜찮다. 하지만 맥락이 바뀌어 재검토해야 할 결정도 그냥 둔다. 이해 없이 받아들인 결정이 쌓이면 팀은 아무것도 바꾸기 두려워하고 프로젝트는 자기 무게에 무너진다.
- **맹목적으로 바꾼다.** 되돌려야 할 결정이었다면 괜찮다. 하지만 동기를 모른 채 바꾸면, 예컨대 아직 테스트되지 않은 비기능 요구사항을 지탱하던 결정을 무너뜨릴 수 있다.

Nygard 의 결론은 "맹목적 수용도 맹목적 번복도 피하는 것이 낫다" 이다. 그리고 큰 문서는 갱신되지 않고 아무도 읽지 않으므로, **작고 모듈화된 문서**여야 갱신될 가능성이 있다고 말한다. ADR 은 이 두 관찰의 결합이다.

## 핵심 개념

### 정의

[adr.github.io](https://adr.github.io)는 용어를 다음처럼 정리한다.

| 용어 | 정의 |
|---|---|
| 아키텍처 결정(AD) | 아키텍처적으로 중요한 기능·비기능 요구사항을 다루는, 근거가 있는 설계 선택 |
| 아키텍처적으로 중요한 요구사항(ASR) | 시스템의 아키텍처와 품질에 측정 가능한 영향을 주는 요구사항 |
| ADR | 하나의 AD 와 그 근거를 담는 기록 |
| 결정 로그(decision log) | 한 프로젝트에서 만들고 유지하는 ADR 의 모음 |

Nygard 는 "아키텍처적으로 중요한" 결정을 **구조, 비기능 특성, 의존성, 인터페이스, 구축 기법**에 영향을 주는 결정으로 정의했다. Martin Fowler 는 2026년 3월 글 [Architecture Decision Record](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html)에서 ADR 을 "제품이나 생태계에 관련된 단일 결정을 포착하고 설명하는 짧은 문서" 로 정의한다.

ISO/IEC/IEEE 42010 도 아키텍처 결정과 근거(rationale)를 아키텍처 기술서의 구성 요소로 둔다. 근거는 결정의 설명·정당화와 **선택하지 않은 대안**까지 기록한다([42010 개념 모델](http://www.iso-architecture.org/42010/cm/)). ADR 은 이 요구를 가볍게 구현하는 방법이다.

### Nygard 의 원형 템플릿

| 절 | 내용 |
|---|---|
| 제목 | 짧은 명사구. 예: "ADR 9: LDAP for Multitenant Integration" |
| 맥락(Context) | 작용하는 힘들 — 기술적, 정치적, 사회적, 프로젝트 고유. 서로 긴장 관계일 수 있음. **가치중립적으로 사실만** |
| 결정(Decision) | 그 힘들에 대한 대응. 능동태 완전한 문장. "우리는 …할 것이다" |
| 상태(Status) | proposed / accepted / deprecated / superseded(대체한 ADR 참조) |
| 결과(Consequences) | 결정 적용 후의 맥락. **긍정만이 아니라 부정·중립 결과까지 모두** |

운영 규칙도 같은 글에 있다.

- 저장소의 `doc/arch/adr-NNN.md` 에 경량 마크업(Markdown 등)으로 둔다.
- 번호는 순차적이고 단조 증가하며 **재사용하지 않는다.**
- 결정이 뒤집히면 옛 ADR 을 지우지 않고 superseded 로 표시한다. "그것이 결정이었다는 사실은 여전히 의미가 있다."
- 각 문서는 한두 쪽 분량으로 짧게.

Fowler 의 글은 여기에 몇 가지를 더한다. 가장 중요한 내용을 앞에 두는 **역피라미드** 문체, accepted 이후에는 **다시 열거나 고치지 말고 대체**할 것, 검토한 **진지한 대안과 장단점을 명시**할 것, 결정의 **확신 수준**과 재평가를 촉발할 맥락 변화를 적을 것. 그리고 기록 그 자체보다 **쓰는 행위가 생각을 명확히 하고** 서로 다른 관점을 드러내 토론하게 만든다는 점을 더 큰 가치로 꼽는다.

### 템플릿 변형

| 템플릿 | 특징 |
|---|---|
| Nygard | 제목·맥락·결정·상태·결과. 가장 단순 |
| [MADR](https://adr.github.io/madr/) | Markdown Architectural Decision Records. 검토한 옵션과 장단점을 구조화. 2024년 9월 4.0.0 |
| [Y-statement](https://adr.github.io/adr-templates/) | 한 문장 형식. Zdun 외의 *Sustainable Architectural Decisions* 에서 제안 |

MADR 4.0 의 절 구성은 다음과 같다. 상태·날짜·결정자·자문(consulted)·통보(informed)는 선택적 YAML 머리말이다.

```
# {해결한 문제와 해법을 대표하는 짧은 제목}
## Context and Problem Statement
## Decision Drivers
## Considered Options
## Decision Outcome
### Consequences
### Confirmation
## Pros and Cons of the Options
## More Information
```

Y-statement 는 한 문장에 모든 것을 넣는다.

> In the context of <유스케이스>, facing <관심사>, we decided for <옵션> and neglected <다른 옵션>, to achieve <품질>, accepting <감수할 단점>, because <추가 근거>.

ThoughtWorks Technology Radar 는 2016년 11월판에 [Lightweight Architecture Decision Records](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)를 실으며, 위키나 협업 도구보다 **소스 저장소에 단순 마크업으로** 두는 것을 선호한다고 적었다.

## 예제

### 작성 예 (Nygard 형식 + 대안)

```markdown
# 0007. 주문 이벤트 발행에 트랜잭셔널 아웃박스를 사용한다

- 상태: accepted (2026-10-02)
- 대체: 0004 "주문 저장 후 Kafka 직접 발행" 을 대체함

## 맥락
주문 API 는 주문을 DB 에 저장한 뒤 Kafka 로 OrderPlaced 를 발행한다.
두 작업이 원자적이지 않아, 지난 분기 브로커 장애 때 저장은 됐지만
이벤트가 빠진 주문이 발생했고 배송 서비스가 이를 놓쳤다.
팀에 CDC(Debezium) 운영 경험은 없다. DB 는 PostgreSQL 이다.

## 검토한 대안
1. 현행 유지 + 재시도: 저장 후 프로세스가 죽으면 여전히 유실.
2. 트랜잭셔널 아웃박스 + 폴링 릴레이: 같은 트랜잭션에 outbox 행 저장. 지연 수 초.
3. 아웃박스 + CDC: 지연이 짧지만 새 운영 구성요소 추가.

## 결정
우리는 2번을 채택한다. outbox 테이블에 같은 트랜잭션으로 이벤트를 쓰고,
별도 릴레이가 폴링해 Kafka 로 발행한다.

## 결과
- (+) DB 커밋과 이벤트 기록이 원자적이 된다.
- (-) 릴레이는 같은 메시지를 두 번 보낼 수 있다. 모든 소비자는 멱등이어야 한다.
- (-) 발행 지연이 폴링 주기만큼 늘어난다.
- (중립) outbox 정리 배치가 필요하다.
- 재검토 조건: 지연 요구가 1초 미만으로 바뀌거나 CDC 운영 역량이 생기면 3번 재평가.
- 확신 수준: 중간. 폴링 부하는 실측 전이다.
```

이 예의 아웃박스 패턴 자체는 SE100 #028 에서 다룬다.

### 운영 체크리스트

- [ ] 위치: `docs/adr/` 또는 `doc/adr/` — 코드와 같은 저장소, 같은 PR
- [ ] 파일명: `0007-use-transactional-outbox.md` (순번 + 결정 요약)
- [ ] 아키텍처에 영향을 주는 PR 템플릿에 "관련 ADR" 칸
- [ ] accepted ADR 은 수정 금지(오탈자 제외). 바뀌면 새 ADR + 양쪽 상호 링크
- [ ] 결과 절에 부정적 결과가 최소 하나는 있는가 — 없으면 대안 검토가 부족했다는 신호
- [ ] 여러 저장소에 걸친 결정은 별도 "아키텍처 저장소" 에 둔다(Fowler 도 단일 코드베이스를 넘는 결정은 제품 저장소가 맞지 않는다고 지적)

## 흔한 오해와 함정

- **"ADR 은 설계 문서다."** ADR 은 결정 **하나**의 기록이다. 시스템 전체 구조 설명은 아키텍처 기술서(SE100 #022)나 C4 다이어그램(#024)의 몫이고, ADR 은 "왜 이 모양이 됐는가" 를 설명한다.
- **"결정이 바뀌면 ADR 을 고친다."** 그러면 "언제부터 언제까지 어떤 결정이 유효했는지" 의 이력이 사라진다. 새 ADR 로 대체한다.
- **"모든 결정을 ADR 로."** 되돌리기 쉬운 결정까지 기록하면 결정 로그가 소음이 된다. Nygard 의 기준(구조, 비기능 특성, 의존성, 인터페이스, 구축 기법)이나 "되돌리기 비싼가" 로 거른다.
- **"결정 후에 쓴다."** Fowler 가 강조하듯 쓰는 과정이 합의를 만든다. proposed 상태로 먼저 쓰고 리뷰를 받는 편이 가치가 크다.
- **"맥락 절에 결론을 섞는다."** Nygard 는 맥락을 가치중립적 사실로 쓰라고 한다. 맥락에 이미 결론이 들어 있으면 대안 검토가 형식이 된다.

## 확인 문제

1. Nygard 가 말한 "맹목적 수용" 과 "맹목적 번복" 은 각각 어떤 위험을 낳는가?
2. accepted 된 ADR 의 결정이 바뀌었을 때 올바른 처리는?
3. 결과(Consequences) 절에 긍정적 결과만 적으면 무엇이 문제인가?
4. ADR 을 위키가 아니라 코드 저장소에 두는 이유 두 가지는?
5. ISO/IEC/IEEE 42010 의 "아키텍처 근거(rationale)" 와 ADR 은 어떤 관계인가?

### 풀이

1. 맹목적 수용은 맥락이 바뀌어 재검토가 필요한 결정까지 방치해 팀이 변경을 두려워하게 만든다. 맹목적 번복은 결정이 지탱하던(예: 아직 테스트되지 않은 비기능 요구) 가치를 모르고 무너뜨린다.
2. 원래 ADR 은 그대로 두고 상태를 superseded 로 바꾼 뒤, 새 결정을 담은 새 ADR 을 만들어 서로 링크한다.
3. 결정의 비용이 기록되지 않아 나중에 재평가할 근거가 없고, 대안을 진지하게 검토하지 않았을 가능성을 가린다. Nygard 는 긍정·부정·중립 결과를 모두 적으라고 한다.
4. 코드를 다루는 사람이 바로 볼 수 있고, 경량 마크업이라 코드처럼 diff·리뷰·버전 관리가 된다. 결정과 그 결정을 구현한 변경을 같은 PR 로 묶을 수 있다.
5. 42010 은 결정과 근거(선택하지 않은 대안 포함)를 아키텍처 기술서에 담도록 하며, ADR 은 그것을 결정 단위의 짧은 파일로 구현하는 가벼운 방법이다.

## 더 읽을거리 (References)

- Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), 2011
- Martin Fowler, [Architecture Decision Record](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html), 2026
- ADR GitHub organization, [adr.github.io](https://adr.github.io), [ADR Templates](https://adr.github.io/adr-templates/), [MADR](https://adr.github.io/madr/)
- Thoughtworks Technology Radar, [Lightweight Architecture Decision Records](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records), 2016
- ISO/IEC/IEEE 42010, [Conceptual Model](http://www.iso-architecture.org/42010/cm/)
- CS300: [기술 부채]({% post_url 2026-10-10-cs300-200-technical-debt %})
