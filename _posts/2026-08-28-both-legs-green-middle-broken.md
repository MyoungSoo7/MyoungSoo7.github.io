---
layout: post
title: "양쪽 다 초록인데 가운데가 끊겨 있었다 — 포인트 적립 왕복을 끝단까지 붙여 보고"
date: 2026-08-28 22:55:16 +0900
categories: [backend, testing, msa]
tags:
  [
    contract-test,
    kafka,
    postgresql,
    check-constraint,
    testcontainers,
    prometheus,
    observability,
  ]
---

이벤트 프로모션(출석체크·럭키박스)을 별도 서비스로 떼어내는 중이었다. 보상 포인트는 이 서비스가 직접 지급하지 않는다. 원장은 주문 서비스가 쥐고, 마케팅은 "지급해 달라"는 이벤트만 낸다. 적립이 실제로 성사되면 주문 서비스가 다시 이벤트를 돌려주고, 그걸 받아야 보상이 확정된다.

```
marketing ──reward_requested──▶ order ──적립──▶ point.granted ──▶ marketing (확정)
```

단위 테스트는 초록이었다. 아키텍처 테스트도 통과했다. 이벤트 계약 스키마도 있었다. 그런데 실제 PostgreSQL 을 띄우고 이 왕복을 처음부터 끝까지 한 번 흘려 보내자, 첫 번째 요청이 데이터베이스에서 거절됐다.

## 값 목록이 두 곳에 적혀 있었다

포인트 원장의 적립 로트에는 "출처"가 붙는다. 충전 원금, 충전 보너스, 주문 적립, 수동 지급, 환불 복원, 이체 수신… 그리고 이번에 추가한 **프로모션 보상**.

이 목록은 두 곳에 있다. 자바 enum 하나, 그리고 테이블의 `CHECK` 제약 하나.

```sql
ALTER TABLE point_lots ADD CONSTRAINT chk_point_lots_origin
    CHECK (origin IN ('CHARGE_PRINCIPAL', 'CHARGE_BONUS', 'ORDER_EARN',
                      'MANUAL_GRANT', 'REFUND_RESTORE', 'TRANSFER_IN'));
```

enum 에는 새 값을 넣었고, `CHECK` 에는 넣지 않았다.

PostgreSQL 문서는 이 상황을 한 문장으로 정리해 둔다 — "제약을 위반하는 데이터를 저장하려 시도하면 오류가 발생한다"[^pg]. 오류다. 경고도, 무시도 아니다. 그래서 적립은 예외가 되고, 트랜잭션은 롤백되고, 롤백됐으니 컨슈머는 오프셋을 커밋하지 않는다. 카프카는 레코드 단위 상태를 갖지 않고 그룹·파티션당 커밋된 오프셋 하나만 들고 있으므로[^ack], 같은 메시지가 계속 다시 온다. 계속 다시 와서 계속 거절된다. 재시도 한도를 넘기면 DLQ 로 간다.

정리하면 **보상 기능은 첫 한 건도 넣지 못하고 죽는 상태**였다. 애플리케이션 층에는 틀린 데가 한 줄도 없었다.

## 왜 아무 테스트도 못 봤나

컨슈머 테스트가 없었기 때문이다. 정확히는 이 저장소에 **컨슈머 계약 테스트가 한 건도 없었다.**

프로듀서 쪽은 잘 돼 있었다. 이벤트를 낼 때마다 JSON Schema 로 페이로드를 검증하는 테스트가 8종. 검증되고 있던 것은 "우리가 무엇을 내보내는가"였다.

검증되지 않던 것은 "남이 보낸 것을 우리가 어떻게 읽는가"였다. 그리고 계약이 깨지는 지점은 대개 후자다.

마틴 파울러가 계약 테스트를 설명하면서 던지는 질문이 정확히 이거다 — 테스트 더블에 대고만 테스트하면, 그 더블이 실제 서비스를 정확히 대변하는지, 상대가 계약을 바꾸면 무슨 일이 일어나는지는 어떻게 아는가[^fowler]. 우리 컨슈머는 목(mock) 원장에 대고만 시험되고 있었고, 목은 `CHECK` 제약을 갖고 있지 않다. 목은 무엇이든 받아 준다. 그래서 초록이었다.

컴파일러도 못 잡는다. enum 값과 `CHECK` 목록 사이에는 타입 관계가 없다. 문자열이 문자열로 옮겨 갈 뿐이다.

## 두 다리를 따로 시험하면 가운데가 어긋나도 양쪽 다 초록이다

이걸 고치면서 실 데이터베이스를 띄우는 통합 테스트를 양쪽에 붙였는데, 그 과정에서 한 번 더 배운 게 있다.

처음엔 확정 쪽 테스트에 들어갈 `point.granted` 페이로드를 손으로 적었다. 그러면 테스트는 통과한다. 그런데 그 통과가 증명하는 것은 "내가 상상한 모양을 내가 잘 읽는다"뿐이다. 발행 측이 필드 이름을 바꾸면 이 테스트는 옛 모양을 영원히 통과시킨다.

그래서 손으로 적기를 그만두고, **방금 우리가 낸 outbox 행에서 값을 뽑아** 확정 이벤트를 만들었다.

```java
// 우리가 실제로 발행한 행에서 rewardId 와 source 를 꺼내 되돌아오는 이벤트를 만든다.
// 손으로 적으면 발행 측이 바뀌어도 이 테스트는 계속 초록이다.
var rewardId = jdbc.queryForObject(
        "SELECT payload ->> 'rewardId' FROM outbox_events WHERE ...", String.class);
```

같은 이유로 컨슈머 단위 테스트의 입력도 전부 저장소가 배포하는 **정본 샘플**로 바꿨다. 발행 측이 필드를 바꾸면 샘플이 바뀌고, 그 변경이 소비 측 테스트까지 흘러온다.

두 다리를 각각 시험하면 각각은 맞다. 가운데가 어긋나 있어도 양쪽 다 초록이다. 왕복을 한 줄로 이어 놓아야 그게 보인다.

## 주석이 틀리면 코드보다 위험하다

계약 스키마에 이런 주석이 달려 있었다.

> 소비측은 `referenceType="PROMOTION"`, `referenceId=rewardId` 로 적립을 멱등 처리한다

실제로 오가는 값은 `PROMOTION` 이 아니라 보상 종류 이름(`ATTENDANCE_GOAL` 같은 것)이었다. 지금 코드는 맞게 동작한다. 틀린 건 설명뿐이다.

그런데 이 문장은 다음 사람이 읽는다. 그리고 이 설명을 믿고 발행 측을 "정리"하면 — 적립은 그대로 되고, 확정만 조용히 멈춘다. 사용자 화면은 "적립 처리 중"에서 영원히 안 움직이고, 포인트는 실제로 들어가 있으니 원장 대사에서도 안 걸린다. 틀린 코드는 터지지만 틀린 주석은 안 터진다. 그래서 더 오래 산다.

계약 스키마의 또 한 군데도 함께 고쳤다. 캠페인 이름 필드를 `string` 으로만 선언해 뒀는데, 일괄 지급 경로는 캠페인을 못 찾으면 `null` 을 실어 보낸다. 이건 사람이 아니라 새로 붙인 계약 테스트가 잡았다.

## 계측했다 ≠ 감시된다

배포 정의를 채우다 같은 종류의 구멍을 하나 더 찾았다.

새 서비스는 `/actuator/prometheus` 로 지표를 전부 내보내고 있었다. 마이크로미터 의존성도 들어 있고, 액추에이터 노출 설정도 돼 있고, 컨테이너도 정의돼 있었다. 그런데 **프로메테우스 스크레이프 설정에 이 서비스가 없었다.**

프로메테우스에서 인스턴스 가용성을 보는 표준 시계열은 `up{job=..., instance=...}` 이다 — 스크레이프에 성공하면 1, 실패하면 0[^prom]. 여기서 중요한 건 스크레이프 대상이어야 이 시계열이 **존재한다**는 점이다. 대상 목록에 없으면 `up == 0` 이 아니라 시계열 자체가 없고, 그러면 `up{job="marketing"} == 0` 같은 알람 규칙은 빈 벡터를 평가하며 영원히 발화하지 않는다.

앱은 계측돼 있었다. 아무도 긁어가지 않았을 뿐이다. 죽어도 아무 소리가 안 나는 상태였고, 대시보드는 나머지 서비스로 초록이었을 것이다.

여기에 하나 더 붙였다. 왕복의 **돌아오는 다리**만 끊긴 상태는 기존 지표로 안 잡힌다. 발행은 성공했으니 outbox 적체 알람은 조용하고, 서비스는 멀쩡히 200 을 주고, 원장도 자기 관점에서는 정상이다. 그래서 "요청한 지 한참 됐는데 확정이 안 온 건수"를 직접 세는 게이지를 만들고 거기에 알람을 걸었다. 트랜잭셔널 아웃박스는 "DB 커밋과 메시지 발행을 원자적으로"까지를 보장하는 패턴이고[^outbox], 그 뒤 상대가 실제로 처리했는지는 다른 문제다.

## 남은 것

- 통합 테스트는 브로커를 띄우지 않는다. 컨슈머를 실제 빈으로 조립해 트랜잭션 안에서 직접 부르는 방식이라, 원장·확정 경로에는 목이 하나도 없지만 리스너 배선(토픽·그룹·ack 모드) 자체는 여전히 애노테이션 검증에 맡긴다.
- `CHECK` 제약이 enum 전체를 덮는지 실제 스키마에 대고 확인하는 테스트를 넣었다. 다음 출처를 추가할 때 같은 사고가 나지 않게 하려는 것인데, 이건 이번 값 하나를 막은 거지 "두 곳에 적힌 목록"이라는 구조 자체를 없앤 건 아니다.
- 이 서비스는 아직 운영에 안 떠 있다. 그래서 실제 사용자가 포인트를 못 받은 일은 없었다. 다만 이 결함들은 전부 **첫 사용자에게** 나타났을 것들이고, 그중 어느 것도 배포 전에 빨간불을 켜 주지 않았다.

가장 오래 남은 문장은 이거다. 컴파일러가 못 보고 단위 테스트가 못 보는 자리는 대체로 **경계**다. enum 과 테이블 사이, 발행과 소비 사이, 앱과 감시 사이. 세 군데 다 각각은 멀쩡했다.

## References

[^pg]: PostgreSQL Global Development Group, "PostgreSQL 17 Documentation — 5.5. Constraints." <https://www.postgresql.org/docs/17/ddl-constraints.html> ("If a user attempts to store data in a column that would violate a constraint, an error is raised.")
[^ack]: VMware, "Spring for Apache Kafka Reference — Manually Committing Offsets." <https://docs.spring.io/spring-kafka/reference/kafka/receiving-messages/ooo-commits.html> ("Kafka does not maintain state for each record, only a committed offset for each group/partition.")
[^fowler]: Martin Fowler, "Contract Test." <https://martinfowler.com/bliki/ContractTest.html>
[^prom]: Prometheus Authors, "Jobs and instances." <https://prometheus.io/docs/concepts/jobs_instances/> ("`up{job=..., instance=...}`: 1 if the instance is healthy, i.e. reachable, or 0 if the scrape failed.")
[^outbox]: Chris Richardson, "Pattern: Transactional outbox," microservices.io. <https://microservices.io/patterns/data/transactional-outbox.html>
