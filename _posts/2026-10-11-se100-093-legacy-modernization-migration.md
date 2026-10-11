---
layout: post
title: "[SE100 #093] 레거시 현대화와 데이터 마이그레이션"
date: 2026-10-11 17:10:42 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, legacy-modernization, data-migration, expand-contract, change-data-capture]
---

소프트웨어 공학 100 주제 시리즈의 93번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

레거시 현대화에서 코드는 다시 쓸 수 있지만 **데이터는 다시 만들 수 없다.** 그래서 현대화 계획의 중심은 데이터 이동이고, 그 기본 도구는 확장-이관-축소(expand/migrate/contract), 변경 데이터 캡처(CDC), 그리고 대사(reconciliation)다.

## 왜 필요한가

현대화 프로젝트가 실패하는 지점은 대개 코드가 아니라 데이터다.

- 새 서비스는 빨리 만들었는데, **옛 DB 를 같이 쓰는 다른 시스템** 이 열 개 나온다. 배치, 리포트, 다른 팀의 직접 쿼리.
- 컷오버 날 하룻밤에 데이터를 옮기기로 했는데, 이관 스크립트가 예상보다 오래 걸리고 중간에 실패한다. 되돌릴 방법이 없다.
- 이관 후 몇 주가 지나서야 금액 합계가 맞지 않는다는 걸 회계팀이 발견한다.

앞 글(SE100 #092)의 스트랭글러 피그가 **요청 흐름** 을 점진적으로 옮기는 방법이라면, 이 글은 그 아래의 **데이터** 를 점진적으로 옮기는 방법이다.

## 핵심 개념

### 레거시란 무엇인가

Michael Feathers 는 *Working Effectively with Legacy Code* (Prentice Hall, 2004)에서 레거시 코드를 "테스트가 없는 코드" 로 정의했다. 오래됐는지, 언어가 낡았는지가 아니라 **변경을 안전하게 검증할 수단이 없는가** 가 기준이다. 이 정의는 현대화의 첫 단계를 알려 준다. 고치기 전에 현재 동작을 고정하는 특성화 테스트(characterization test)를 먼저 만든다. 테스트 전략은 [통합 테스트와 E2E 테스트]({% post_url 2026-10-10-cs300-192-integration-and-e2e-testing %}) 글에서 다뤘다.

### 현대화의 선택지

AWS 는 클라우드 이전 전략을 [7 Rs](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html) 로 정리한다. 클라우드 이전용 분류지만 현대화 의사결정에도 그대로 쓸 만하다.

| 전략 | 의미 | 데이터 관점 |
|---|---|---|
| Retire | 폐기·보관 | 보존 기간과 조회 수단만 남긴다 |
| Retain | 당분간 유지 | 변경 없음 |
| Rehost | 변경 없이 옮김(lift and shift) | 같은 DB 엔진, 덤프·복제 |
| Relocate | 플랫폼째 이동 | 인프라 단위 이전 |
| Repurchase | SaaS 등으로 교체 | 스키마 변환·매핑이 핵심 |
| Replatform | 약간 최적화하며 이동 | 관리형 DB 로 엔진 동일 이관 |
| Refactor / re-architect | 구조를 바꿈 | 스키마 분해, 소유권 재배치 |

AWS 문서는 대규모 이전에서는 refactor 를 권하지 않는다. 가장 복잡하고 비싸므로, 먼저 옮기고 **이전이 끝난 뒤에** 현대화하라고 권한다. "옮기면서 고치기" 는 변수 두 개를 동시에 바꾸는 일이다.

### 확장-이관-축소 (Parallel Change)

Danilo Sato 가 정리한 [Parallel Change](https://martinfowler.com/bliki/ParallelChange.html) 는 호환되지 않는 인터페이스 변경을 세 단계로 쪼갠다.

1. **확장(expand)**: 옛것과 새것을 동시에 지원하도록 넓힌다.
2. **이관(migrate)**: 클라이언트를 하나씩 새것으로 옮긴다.
3. **축소(contract)**: 옛것을 지운다.

각 단계가 독립적으로 배포 가능하다는 점이 핵심이다. DB 에서는 Pramod Sadalage 와 Fowler 의 [Evolutionary Database Design](https://martinfowler.com/articles/evodb.html) 이 같은 개념을 **전환기(transition phase)** 로 설명한다. "DB 가 옛 접근 방식과 새 접근 방식을 동시에 지원하는 기간" 이며, 옛 시스템이 자기 속도로 옮겨 올 시간을 준다. 같은 글은 모든 DB 변경을 버전 관리되는 마이그레이션으로 만들고, 스키마와 데이터를 함께 다루라고 원칙을 세운다.

### 변경 데이터 캡처와 이중 쓰기 문제

옛 DB 와 새 DB 가 한동안 공존하면 둘을 맞춰야 한다. 가장 쉬워 보이는 방법이 애플리케이션에서 양쪽에 쓰는 **이중 쓰기(dual write)** 인데, 한쪽만 성공하는 순간 불일치가 생기고 두 저장소를 묶는 트랜잭션은 보통 없다.

대안은 DB 의 트랜잭션 로그를 읽는 **로그 기반 CDC** 다. [Debezium 문서](https://debezium.io/documentation/reference/stable/features.html)는 폴링이나 이중 쓰기와 달리 로그 기반 CDC 가 모든 변경(삭제 포함)을 잡고, "Last Updated" 같은 컬럼 추가 없이 동작하며, 이전 레코드 상태와 트랜잭션 ID 같은 메타데이터도 담을 수 있다고 설명한다. 이벤트 발행까지 원자적으로 해야 하면 같은 트랜잭션에서 아웃박스 테이블에 쓰고 CDC 로 내보내는 [Transactional Outbox](https://microservices.io/patterns/data/transactional-outbox.html) 패턴을 쓴다.

### 공유 DB 를 도메인별로 쪼개는 순서

Azure 의 [Strangler Fig 문서](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig) 예시는 모놀리식 DB 분해를 세 단계로 보여 준다.

```
[1] 새 서비스 도입      [2] 도메인 DB 복제            [3] 컷오버
new ──► monolith DB    new ──► monolith DB           new ──► domain DB
                          │  ETL(초기 적재)              monolith 에서 해당 테이블 제거
                          │  CDC(지속 동기화)
                          ▼
                       domain DB  ← 일관성 검증
       ◄──────── 이 구간에서는 monolith 로 되돌릴 수 있다 ────────►
```

문서가 강조하는 점은 **되돌림 창(rollback window)** 이다. 2단계와 3단계 초입까지는 옛 테이블과 동기화가 살아 있어 되돌릴 수 있다. 옛 객체를 지운 뒤에 되돌리려면 복원과 변경 재생이 필요해 위험이 크게 늘어나므로, 레거시 객체 삭제는 검증이 끝난 뒤의 **의도적 마지막 단계** 로 둔다.

## 실무 적용

### 예: 컬럼 분리를 확장-축소로

`customer.name` 을 `first_name`, `last_name` 으로 나누는 경우.

```sql
-- V41__expand.sql  (배포 1: 옛 앱 그대로 동작)
ALTER TABLE customer ADD COLUMN first_name VARCHAR(100);
ALTER TABLE customer ADD COLUMN last_name  VARCHAR(100);

-- V42__backfill.sql (배치로 나눠 실행, 잠금 시간 최소화)
UPDATE customer
   SET first_name = split_part(name, ' ', 1),
       last_name  = substr(name, length(split_part(name, ' ', 1)) + 2)
 WHERE first_name IS NULL
   AND id BETWEEN :lo AND :hi;
```

- 배포 2: 앱은 **양쪽에 쓰고 새 컬럼에서 읽는다.** 같은 DB 의 같은 트랜잭션이므로 여기서의 이중 쓰기는 안전하다.
- 배포 3: 모든 소비자(리포트, 배치, 다른 팀)가 새 컬럼을 쓰는지 쿼리 로그로 확인한다.
- 배포 4: `V43__contract.sql` 로 `name` 을 지운다. 이 단계는 되돌리기 어려우니 가장 늦게 한다.

### 예: 대사(reconciliation) 스크립트

이관 중에는 "옮겼다" 가 아니라 "맞다" 를 증명해야 한다. 행 수만 비교하면 안 되고, 키별 내용과 업무 합계를 비교한다.

```python
import hashlib

def row_digest(row: dict, cols: list[str]) -> str:
    norm = "|".join("" if row[c] is None else str(row[c]).strip() for c in cols)
    return hashlib.sha256(norm.encode()).hexdigest()

def reconcile(old_rows, new_rows, key: str, cols: list[str]):
    old = {r[key]: row_digest(r, cols) for r in old_rows}
    new = {r[key]: row_digest(r, cols) for r in new_rows}
    missing  = old.keys() - new.keys()          # 옮겨지지 않음
    extra    = new.keys() - old.keys()          # 새 쪽에만 있음
    changed  = {k for k in old.keys() & new.keys() if old[k] != new[k]}
    return missing, extra, changed

# 업무 불변식: 일자별 결제 금액 합계는 양쪽이 같아야 한다
CHECK_SQL = "SELECT pay_date, SUM(amount) FROM payment GROUP BY pay_date"
```

- 정규화 규칙(공백, NULL, 시간대, 소수 자릿수)을 먼저 합의한다. 대부분의 "불일치" 는 표현 차이다.
- 대사는 한 번이 아니라 **동기화 기간 내내** 주기적으로 돌린다.
- 금액·재고처럼 돈이 걸린 값은 합계 불변식을 따로 검사한다.

### 컷오버 체크리스트

- [ ] 옛 DB 의 **모든 소비자** 목록(쿼리 로그 기반)과 각자의 이관 계획
- [ ] 초기 적재 소요 시간 실측(운영 크기의 사본으로)
- [ ] CDC 지연 모니터링과 경보
- [ ] 대사 결과 0 건(또는 합의된 허용치)인 기간이 충분히 지속됨
- [ ] 라우팅 원복 절차를 실제로 연습함
- [ ] 레거시 객체 삭제는 별도 변경으로, 마지막에

## 흔한 오해와 함정

- **"주말 한 번이면 옮긴다."** 빅뱅 컷오버는 실패 시 되돌릴 창이 없다. 동기화를 켜 둔 채 읽기부터 옮기면 컷오버가 라우팅 변경 하나로 줄어든다.
- **애플리케이션 이중 쓰기.** 두 저장소에 따로 쓰면 부분 실패가 반드시 생긴다. 한 곳에 쓰고 로그로 퍼뜨린다.
- **스키마만 옮긴다.** 트리거, 저장 프로시저, 기본값, 문자 집합, 정렬 규칙(collation)도 동작의 일부다. 정렬 규칙 차이 하나로 유니크 제약 위반이 날 수 있다.
- **"새 시스템이 기존 기능을 전부 해야 한다."** 앞 글에서 본 기능 동등성 함정이 데이터에도 있다. 아무도 읽지 않는 테이블과 컬럼은 옮기지 말고 보관(archive)한다. AWS 7 Rs 의 Retire 다.
- **축소 단계를 잊는다.** 확장만 하고 축소를 안 하면 옛 컬럼과 새 컬럼이 영원히 공존하며, 누가 어느 쪽을 믿는지 아무도 모른다. 축소 티켓을 확장할 때 같이 만든다.

## 확인 문제

1. Feathers 의 레거시 정의가 현대화의 첫 작업에 대해 시사하는 바는?
2. AWS 가 대규모 이전에서 refactor 를 권하지 않는 이유는?
3. 서로 다른 두 DB 에 애플리케이션이 이중 쓰기하는 것이 위험한 이유와 대안은?
4. Azure 문서가 말하는 되돌림 창은 언제 닫히는가?
5. 대사 시 행 수만 비교하면 놓치는 것 두 가지를 들라.

### 풀이

1. 테스트가 없는 코드가 레거시이므로, 바꾸기 전에 현재 동작을 고정하는 테스트(특성화 테스트)를 먼저 만들어 변경을 검증할 수단을 확보해야 한다.
2. 이전 중에 애플리케이션 구조까지 바꾸면 가장 복잡하고 비싸며, 많은 애플리케이션에 대해 관리하기 어렵다. 먼저 옮기고 이전이 끝난 뒤 현대화하라는 것이 권고다.
3. 두 저장소를 묶는 트랜잭션이 없어 한쪽만 성공하면 불일치가 생긴다. 한 저장소에만 쓰고 트랜잭션 로그 기반 CDC(필요하면 아웃박스 패턴)로 다른 쪽에 전파한다.
4. 모놀리식 DB 에서 해당 도메인 테이블·프로시저·동기화 프로세스를 제거할 때 닫힌다. 그 이후 되돌리려면 객체 복원과 변경 재생이 필요하다.
5. 내용이 바뀐 행(값 불일치), 한쪽 누락과 다른 쪽 추가가 같은 수만큼 있어 상쇄되는 경우, 업무 합계(금액) 불일치 등.

## 더 읽을거리 (References)

- Michael Feathers, *Working Effectively with Legacy Code*, Prentice Hall, 2004 (서지 정보)
- AWS, [About the migration strategies (7 Rs)](https://docs.aws.amazon.com/prescriptive-guidance/latest/large-migration-guide/migration-strategies.html)
- Danilo Sato, [Parallel Change](https://martinfowler.com/bliki/ParallelChange.html)
- Pramod Sadalage, Martin Fowler, [Evolutionary Database Design](https://martinfowler.com/articles/evodb.html)
- Microsoft, [Strangler Fig pattern — Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig)
- Debezium, [Features](https://debezium.io/documentation/reference/stable/features.html)
- Chris Richardson, [Pattern: Transactional outbox](https://microservices.io/patterns/data/transactional-outbox.html)
- Scott W. Ambler, Pramod J. Sadalage, *Refactoring Databases: Evolutionary Database Design*, Addison-Wesley, 2006 (서지 정보)
- [트랜잭션과 ACID]({% post_url 2026-10-10-cs300-169-transactions-and-acid %}) (CS300 #169)
