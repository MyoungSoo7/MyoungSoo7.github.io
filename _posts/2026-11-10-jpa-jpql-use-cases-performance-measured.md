---
layout: post
title: "JPA·JPQL 사용사례와 성능 최적화 — Hibernate 7.2 에서 JDBC 왕복 횟수를 직접 세 봤다"
date: 2026-11-10 23:42:18 +0900
categories: [backend]
tags: [jpa, jpql, hibernate, n-plus-one, fetch-join, entity-graph, batch-fetch, bulk-update, jdbc-batch, performance]
---

JPA 성능 글은 대개 "N+1 은 fetch join 으로 푼다" 같은 처방 목록이다. 처방은 맞다. 하지만 **몇 번이 몇 번으로 줄어드는지**, **어떤 처방이 어디서 깨지는지**는 직접 돌려보지 않으면 감으로 남는다.

그래서 이번엔 숫자를 셌다. Hibernate ORM **7.2.7.Final** + H2 2.3.232 (인메모리) 위에 JDBC `DataSource` 를 프록시로 감싸 `executeQuery` / `executeUpdate` / `executeBatch` / `addBatch` 호출 수를 그대로 집계했다. 데이터는 팀 10개 × 회원 10명(+ 팀당 프로젝트 3개)이다.

**시간(ms)은 재지 않았다.** 인메모리 H2 에서 잰 지연 시간은 실제 네트워크 너머 DB 와 전혀 다르기 때문이다. 대신 **DB 왕복(round trip) 횟수**를 센다. 이 값은 DB 종류와 상관없이 결정적이고, 실제 운영에서 지연을 키우는 건 대부분 이 횟수다.

> 범위 메모: No-Offset 페이징·커버링 인덱스·count 쿼리 분리·QueryDSL 동적 쿼리는 이 글에서 다루지 않는다. 같은 날 별도 글 [QueryDSL 사용사례와 성능](/2026/11/10/querydsl-use-cases-performance/)이 다룬다.

## 한눈에 보는 결과

| # | 시나리오 | DB 왕복 | 비고 |
|---|---|---|---|
| 1 | Team 10개 조회 후 `members` 접근 (N+1) | **11** | 1 + 팀 수(10) |
| 2 | `join fetch t.members` | **1** | `distinct` 없이도 Team 10개로 반환 |
| 3 | EntityGraph (`jakarta.persistence.fetchgraph`) | **1** | |
| 4 | `hibernate.default_batch_fetch_size=100` | **2** | `where team_id in (?, … )` 한 번 |
| 4b | batch fetch + 페이징(0,3) | **2** | 페이징이 DB 에서 정상 적용 |
| 5 | Member 100건 조회 후 `team.getName()` (ManyToOne N+1) | **11** | 100+1 이 아니라 **1 + 서로 다른 팀 수** |
| 5x | 같은 상황에서 `m.team.name` 필드 직접 접근 | 1 | 쿼리는 안 나가지만 **값이 전부 null** |
| 6 | 컬렉션 `join fetch` + 페이징(0,3) | 1 | SQL 에 `offset/fetch` 가 **없음** → 경고 HHH90003004, 메모리에서 자름 |
| 6b | ToOne `join fetch` + 페이징(0,3) | 1 | SQL 에 `offset ? rows fetch first ? rows only` 정상 |
| 6c | `fail_on_pagination_over_collection_fetch=true` | — | 6번이 **예외**로 바뀜 |
| 7 | List 컬렉션 두 개 동시 `join fetch` | — | `MultipleBagFetchException` |
| 8 | DTO 프로젝션 `select new` | **1** | |
| 9a | 변경 감지 루프로 100건 수정 | **101** | select 1 + update 100 |
| 9b | JPQL 벌크 `update` | **1** | |
| 9c | 벌크 후 같은 엔티티 재조회 | — | clear 전 **20(옛 값)**, clear 후 120 |
| 10 | `persist` 후 JPQL 실행 | 2 | JPQL 직전에 insert 가 자동 flush |
| 11 | SEQUENCE insert 500건, `jdbc.batch_size=0` | 513 | 시퀀스 12 + insert 501 |
| 11 | SEQUENCE insert 500건, `jdbc.batch_size=50` | **23** | 시퀀스 12 + `executeBatch` 11 |
| 11 | IDENTITY insert 500건, `batch_size` 0 / 50 | **500 / 500** | 배치 설정이 **아무 효과 없음** |

아래는 각 항목을 "언제 쓰는가 → 무엇이 일어났나 → 근거" 순서로 풀어 쓴 것이다.

## 실험 장치

엔티티는 일부러 단순하게 잡았다. 모든 연관은 `LAZY`, 컬렉션은 `List` 다.

```java
@Entity class Team {
    @Id @GeneratedValue(strategy = GenerationType.SEQUENCE) Long id;
    String name;
    @OneToMany(mappedBy = "team") List<Member> members = new ArrayList<>();
    @OneToMany(mappedBy = "team") List<Project> projects = new ArrayList<>();
}

@Entity class Member {
    @Id @GeneratedValue(strategy = GenerationType.SEQUENCE) Long id;
    String name;
    int age;
    @ManyToOne(fetch = FetchType.LAZY) Team team;
}
```

왕복 수는 Hibernate 통계 대신 JDBC 프록시로 셌다. Hibernate `Statistics` 의 `prepareStatementCount` 는 배치 실행 횟수를 직접 보여주지 않아서, `executeBatch` 를 따로 세려면 드라이버 경계에서 세는 편이 정확하다. 시나리오마다 새 세션을 열고, 끝나면 롤백해 다음 시나리오에 영향이 없게 했다.

## 1. N+1 — 왜 생기고, 정확히 몇 번인가

**사용사례.** 목록 화면에서 부모 엔티티를 조회한 뒤 각 부모의 자식(컬렉션) 또는 연관 엔티티를 화면에 찍는 경우. 가장 흔한 JPA 코드 모양이다.

```java
List<Team> teams = em.createQuery("select t from Team t", Team.class).getResultList();
for (Team t : teams) total += t.getMembers().size();   // 여기서 팀마다 select
```

결과는 **11 왕복**이다. 팀 목록 1번, 그리고 팀마다 `members` 를 초기화하는 select 10번.

반대 방향(ManyToOne)은 흥미롭다. Member 100건을 조회한 뒤 `member.getTeam().getName()` 을 부르면 101번이 아니라 **11번**이다. 같은 Team 은 영속성 컨텍스트(1차 캐시)에 한 번 올라오면 다시 조회하지 않기 때문이다. 즉 ManyToOne N+1 의 실제 비용은 **서로 다른 부모의 수**에 비례한다. 부모 종류가 적으면 덜 아프고, 부모가 행마다 다르면(예: 주문 → 고객) 정확히 N+1 이 된다.

### 함정: 프록시의 필드를 직접 읽으면 쿼리 대신 null 이 나온다

5x 는 실수로 발견한 결과다. 처음엔 `m.team.name` 처럼 **필드에 직접** 접근했는데, 왕복이 1번밖에 안 나와서 "N+1 이 없네?" 라고 착각할 뻔했다. 실제로는 100명의 팀 이름이 **전부 `null`** 이었다.

LAZY `@ManyToOne` 자리에는 실제 Team 이 아니라 Hibernate 가 만든 **프록시 서브클래스**가 들어간다. 프록시는 **메서드 호출**을 가로채 초기화하므로, 클래스 밖에서 필드를 직접 읽으면 초기화되지 않은 프록시 자신의 빈 필드를 읽게 된다. Hibernate 소개서도 프록시를 "실제 엔티티인 척하는 객체"로 설명하고, 지연 로딩이 이 방식으로 동작한다고 쓴다.[^intro-proxy] 실무 코드에선 접근자를 쓰므로 드물지만, 테스트나 벤치마크 코드에서 "N+1 이 안 난다"는 잘못된 결론을 내기 딱 좋다.

## 2. 해법 셋 — fetch join, EntityGraph, batch fetch

### fetch join (JPQL)

```java
select t from Team t join fetch t.members
```

**1 왕복.** 생성된 SQL 은 Team–Member inner join 하나다.

과거 Hibernate 5 시절엔 이렇게 하면 결과 리스트에 Team 이 **회원 수만큼 중복**돼 나와서 `select distinct` 를 붙이는 게 관례였다. Hibernate 7.2.7 에서는 `distinct` 없이도 결과 리스트 크기가 **10**(팀 수)이었다. 엔티티 결과의 중복 제거를 Hibernate 가 스스로 하기 때문이다(Hibernate 6.0 부터의 동작).[^h6-migration] 오래된 블로그의 "fetch join 엔 반드시 distinct" 조언은 지금 버전에선 필요 없다.

> 주의: 위 inner join 은 회원이 없는 팀을 결과에서 뺀다. 빈 팀도 필요하면 `left join fetch`.

### EntityGraph

JPQL 을 고치지 않고 "이번 조회에선 이것도 같이 가져와"를 바깥에서 지정하는 방법이다. 같은 쿼리를 화면마다 다른 fetch 범위로 재사용할 때 쓴다.

```java
EntityGraph<Team> graph = em.createEntityGraph(Team.class);
graph.addAttributeNodes("members");
em.createQuery("select t from Team t", Team.class)
  .setHint("jakarta.persistence.fetchgraph", graph)
  .getResultList();
```

**1 왕복.** Spring Data JPA 에서는 리포지토리 메서드에 `@EntityGraph(attributePaths = "members")` 를 붙이는 것과 같다.[^spring-graph]

### batch fetch (`default_batch_fetch_size`)

```properties
hibernate.default_batch_fetch_size=100
```

쿼리는 그대로 두고, 지연 로딩이 일어날 때 **아직 초기화되지 않은 같은 종류의 컬렉션을 묶어서** 한 번에 가져오는 설정이다. 결과는 **2 왕복**. 두 번째 SQL 이 이렇다.

```sql
select ... from Member m1_0 where m1_0.team_id in (?,?,?, ... ,?)
```

`IN` 절의 `?` 는 100개였다. 팀이 10개뿐인데도 100개인 이유는 Hibernate 가 배치 크기에 맞춘 고정 길이 파라미터 목록을 쓰고 남는 자리를 채우기 때문으로 보인다(관찰 결과이며, 이 동작의 근거 문서는 찾지 못했다). 이렇게 하면 SQL 문자열 종류가 줄어 statement 캐시에 유리하다는 해석이 흔하지만, 이 실험에서 검증한 것은 아니다.

### 셋 중 무엇을 쓰나

Hibernate 소개서는 기본 처방으로 **join fetch 또는 EntityGraph** 를 꼽고, batch fetch 는 "outer join 이 카테시안 곱과 거대한 결과를 낳는 드문 경우"의 해법이라고 쓴다.[^intro-batch] 다만 아래 두 함정(페이징, 다중 컬렉션)에 걸리는 순간 batch fetch 가 사실상 유일한 선택지가 된다. 실무에서 `default_batch_fetch_size` 를 전역으로 켜 두는 관행이 흔한 이유다.

## 3. 함정 ① — 컬렉션 fetch join 에 페이징을 걸면

**사용사례.** "팀 목록을 3개씩 페이지로, 회원도 같이" — 관리자 화면에서 아주 흔하다.

```java
em.createQuery("select t from Team t join fetch t.members order by t.id", Team.class)
  .setFirstResult(0).setMaxResults(3)
  .getResultList();
```

반환은 Team 3개로 **겉보기엔 정상**이다. 하지만 실제 SQL 을 보면:

```sql
select ... from Team t1_0 join Member m1_0 on t1_0.id=m1_0.team_id order by t1_0.id
```

`offset` / `fetch first` 가 **없다**. 회원 100행을 전부 메모리로 가져온 뒤 자바에서 3개를 잘랐다. 로그에는 이 경고 한 줄만 남는다.

```
WARN: HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory
```

행 단위로 페이징하면 팀 하나의 회원이 페이지 경계에서 잘리므로, Hibernate 로서는 이게 유일하게 정확한 방법이다. 문제는 데이터가 100만 건이면 100만 건이 다 올라온다는 것이다. Hibernate 사용자 가이드도 fetch join 은 "제한·페이징된 쿼리에서는 대체로 피해야 한다"고 명시한다.[^ug-fetch-limit]

비교로 **ToOne** 쪽(`select m from Member m join fetch m.team`)에 페이징을 걸면 SQL 에 `offset ? rows fetch first ? rows only` 가 정상적으로 붙는다(6b). 행이 늘어나지 않기 때문이다.

**대응.**

1. **조용히 지나가지 않게 막는다.** `hibernate.query.fail_on_pagination_over_collection_fetch=true` 를 켜면 같은 코드가 `HibernateException` 으로 바뀐다(6c). 기본값은 `false` 다.[^ug-fail-pagination] 운영 전 테스트 환경에서만이라도 켜 둘 가치가 있다.
2. **페이징은 부모에만, 자식은 batch fetch 로.** 4b 실험이 이 조합이다. `select t from Team t order by t.id` 에 페이징을 걸고 `default_batch_fetch_size` 로 회원을 묶어 가져오면 **2 왕복**이고, 페이징은 DB 에서 처리된다.

## 4. 함정 ② — List 컬렉션 두 개를 동시에 fetch join

```java
select t from Team t join fetch t.members join fetch t.projects
```

결과는 예외다.

```
MultipleBagFetchException: cannot simultaneously fetch multiple bags:
  [bench.Team.members, bench.Team.projects]
```

순서 정보(`@OrderColumn`) 없는 `List` 는 Hibernate 에서 **bag**(중복 허용, 순서 없음)으로 취급된다.[^ug-bag] 두 bag 을 한 SQL 로 조인하면 결과가 members × projects 카테시안 곱이 되는데, bag 은 중복이 허용되므로 어느 행이 진짜 중복인지 가려낼 수 없다. 그래서 Hibernate 는 아예 거부한다.

컬렉션을 `Set` 으로 바꾸면 예외는 사라지지만 **카테시안 곱은 그대로**다(팀당 회원 10 × 프로젝트 3 = 30행). 사용자 가이드도 여러 컬렉션을 병렬로 fetch 하면 "DB 수준에서 카테시안 곱이 생기고 성능이 매우 나쁠 수 있다"고 경고한다.[^ug-cartesian] 현실적인 해법은 **컬렉션 하나만 fetch join, 나머지는 batch fetch** 다.

## 5. DTO 프로젝션 — 조회 전용이면 엔티티를 안 만든다

**사용사례.** 통계·목록 API 처럼 읽기만 하고 수정하지 않는 화면.

```java
select new bench.Main$TeamCount(t.name, count(m))
from Team t left join t.members m
group by t.name
```

**1 왕복**, 결과는 `TeamCount[name=team0, cnt=10]` 형태의 레코드 10개. `select new` 는 결과를 엔티티 대신 사용자 클래스로 직접 만든다.[^ug-select-new] 결과 객체는 영속성 컨텍스트에 등록되지 않으므로 스냅샷 보관·변경 감지 비용이 없고, 집계처럼 엔티티로 표현할 수 없는 모양도 바로 받을 수 있다. 단점은 생성자 경로를 **문자열로 전체 클래스명까지** 적어야 한다는 것이다(중첩 클래스는 `$`). 이 불편이 QueryDSL `Projections` 나 Spring Data 인터페이스 프로젝션이 쓰이는 이유다.

## 6. 쓰기 — 변경 감지 vs 벌크 연산

### 변경 감지 루프는 건수만큼 update 한다

```java
for (Member m : em.createQuery("select m from Member m", Member.class).getResultList())
    m.age++;
em.flush();
```

**101 왕복** — select 1 + update 100. 엔티티 하나당 update 하나다.

### JPQL 벌크 update 는 한 번이다

```java
em.createQuery("update Member m set m.age = m.age + 1").executeUpdate();
```

**1 왕복**, 100건 변경. Hibernate 소개서는 "여러 엔티티를 한 번에 바꾸려면 update 문을 쓰라"고 권한다.[^intro-bulk]

### 대가: 영속성 컨텍스트가 옛 값을 들고 있다

```java
Member m = /* name='m0-0' 조회 */;            // age = 20
em.createQuery("update Member m set m.age = m.age + 100").executeUpdate();
/* 같은 조건으로 다시 조회 */ .getAge();        // → 20  (!!)
em.clear();
/* 다시 조회 */ .getAge();                     // → 120
```

벌크 update 는 DB 를 직접 바꾸고 **영속성 컨텍스트는 건드리지 않는다**. 재조회 쿼리는 DB 에 실제로 나가서 120 을 읽어 오지만, 같은 id 의 엔티티가 이미 1차 캐시에 있으면 Hibernate 는 **이미 있는 인스턴스를 돌려준다**. 그래서 화면에는 20 이 찍힌다.

Spring Data JPA 의 `@Modifying(clearAutomatically = true)` 가 바로 이 문제를 위한 옵션이다. 공식 문서는 벌크 쿼리 실행 후 `EntityManager` 에 오래된 엔티티가 남을 수 있으며, 자동으로 비우려면 이 속성을 켜라고 설명한다. 동시에 `clear()` 는 **아직 flush 되지 않은 변경을 버린다**는 경고도 함께 단다.[^spring-modifying] 그래서 벌크 연산은 트랜잭션 맨 앞에 두거나, 별도 트랜잭션으로 빼는 편이 안전하다. 그리고 벌크 update 는 기본적으로 `@Version` 컬럼도 올리지 않는다. 낙관적 락을 쓰는 엔티티라면 `update versioned` 를 써야 한다.[^ug-versioned]

## 7. 자동 flush — JPQL 은 쓰기를 먼저 내보낸다

```java
em.persist(new Member("new", 30, team));
em.createQuery("select count(m) from Member m", Long.class).getSingleResult();
```

**2 왕복**, 순서는 `insert` → `select count`. 결과 count 는 101 로 방금 persist 한 행이 포함됐다. JPQL 은 DB 에서 실행되므로, 아직 메모리에만 있는 변경이 결과에 영향을 줄 수 있으면 Hibernate 가 쿼리 직전에 flush 한다(AUTO flush).[^ug-flush]

비교로 `persist` 직후 `em.find(Team.class, id)` 는 insert 를 내보내지 않았다(10b). 이미 1차 캐시에 있는 엔티티는 DB 에 가지 않으므로 flush 할 이유가 없다. "persist 했는데 왜 insert 가 안 나가지?" 와 "조회만 했는데 왜 insert 가 나가지?" 는 같은 규칙의 양면이다.

## 8. 쓰기 배치 — `jdbc.batch_size` 와 IDENTITY 의 함정

**사용사례.** 대량 등록, 엑셀 업로드, 정산 결과 적재처럼 한 트랜잭션에서 수백~수천 건을 insert 하는 경우.

| ID 전략 | `hibernate.jdbc.batch_size` | 왕복 | 내역 |
|---|---|---|---|
| SEQUENCE | 0 (기본) | 513 | 시퀀스 12 + insert 501 |
| SEQUENCE | 50 | **23** | 시퀀스 12 + `executeBatch` 11 (addBatch 501) |
| IDENTITY | 0 | 500 | insert 500 |
| IDENTITY | 50 | **500** | insert 500 — **배치 없음** |

SEQUENCE 는 insert 전에 id 를 알 수 있으므로 50건씩 묶어 `executeBatch` 한 번으로 보낸다. 시퀀스 조회 12번은 Hibernate 기본 `allocationSize=50` 에 따른 pooled 최적화 덕분에 501건에 12번으로 끝났다.

IDENTITY 는 id 를 **insert 를 실행해야** 받을 수 있다. Hibernate 는 영속화 시점에 id 가 필요하므로 insert 를 그 자리에서 하나씩 실행할 수밖에 없다. 사용자 가이드는 이를 명시적으로 적고 있다. IDENTITY 생성기를 쓰면 "Hibernate 가 JDBC 수준의 insert 배치를 투명하게 끈다".[^ug-batch] 같은 가이드는 시퀀스를 지원하지 않는 DB(예: MySQL 5.7)에서만 IDENTITY 를 쓰라고 권한다.[^ug-identity] MySQL 에서 `batch_size` 를 켰는데 아무 변화가 없다면 이것이 원인이다.

관련 설정 메모:

- `hibernate.jdbc.batch_size` 는 기본적으로 꺼져 있다. 사용자 가이드는 10~50 사이 값을 권한다.[^ug-batch]
- `hibernate.order_inserts=true` 는 여러 엔티티 타입이 섞여 있을 때 같은 타입끼리 모아 배치가 끊기지 않게 한다(이 실험에서는 켜 둠).
- 수천 건 이상이면 주기적으로 `flush()` + `clear()` 를 해서 1차 캐시가 무한히 커지지 않게 해야 한다.[^ug-batch] 아예 영속성 컨텍스트가 없는 `StatelessSession` 도 선택지다.[^intro-bulk]

## 정리 — 증상별 처방

| 증상 | 먼저 볼 것 | 처방 |
|---|---|---|
| 목록 API 쿼리가 행 수만큼 나간다 | 지연 로딩 위치 | `join fetch` / EntityGraph, 페이징이 있으면 batch fetch |
| 페이징이 느리고 메모리가 튄다 | 로그의 `HHH90003004` | 컬렉션 fetch join 제거 + batch fetch, `fail_on_pagination…=true` |
| `MultipleBagFetchException` | List 컬렉션 2개 이상 fetch | 하나만 fetch join, 나머지 batch fetch |
| 조회 전용 화면이 무겁다 | 엔티티 전체 로딩 여부 | `select new` DTO 프로젝션 |
| 대량 수정이 건수만큼 update | 변경 감지 루프 | 벌크 JPQL + `clearAutomatically` |
| 벌크 후 화면 값이 안 바뀐다 | 1차 캐시 | 벌크를 트랜잭션 앞에, 또는 `clear()` |
| `batch_size` 를 켰는데 insert 수 그대로 | ID 전략 | IDENTITY → SEQUENCE(가능하면) |

## 한계

- **H2 인메모리 한 종류에서만 쟀다.** 왕복 횟수는 Hibernate 가 결정하므로 DB 에 크게 의존하지 않지만, IDENTITY·시퀀스 지원, 페이징 SQL 문법은 방언마다 다르다. MySQL·PostgreSQL 에서 다시 재지는 않았다.
- **지연 시간은 재지 않았다.** "11 왕복이 1 왕복보다 몇 배 느리다"는 네트워크 RTT 와 행 수에 달려 있어 여기서 숫자로 말할 수 없다.
- **데이터가 작다.** 팀 10 × 회원 10 이다. 카테시안 곱·인메모리 페이징의 메모리 피해는 규모가 커져야 드러나고, 이 실험은 **SQL 모양과 왕복 수**만 보여준다.
- **2차 캐시, `@BatchSize` 개별 지정, subselect fetch 는 다루지 않았다.**
- Hibernate 6 의 엔티티 결과 자동 중복 제거는 마이그레이션 가이드를 근거로 들었고, 7.2.7 에서 그 동작을 관찰했다. 5.x 와의 대조 실험은 하지 않았다.

## 관련 글

- [QueryDSL 사용사례와 성능](/2026/11/10/querydsl-use-cases-performance/)
- [JPA 의 장점 — 스펙이 '반드시 해야 한다'고 적은 것만 추려봤다](/2026/10/26/jpa-advantages-what-the-spec-guarantees/)

## References

[^intro-proxy]: Hibernate ORM 7.2, *An Introduction to Hibernate 7*, §5.6 "Proxies and lazy fetching". <https://docs.jboss.org/hibernate/orm/7.2/introduction/html_single/Hibernate_Introduction.html>
[^intro-batch]: 같은 문서, §8.4–8.6 "Association fetching", "Batch fetching and subselect fetching", "Join fetching". 위 링크.
[^intro-bulk]: 같은 문서, 대량 작업에서의 `update` 문 사용 및 `StatelessSession` 설명. 위 링크.
[^h6-migration]: Hibernate ORM 6.0 Migration Guide, "DISTINCT" 항목 — 엔티티 결과의 중복 제거가 Hibernate 쪽에서 자동 적용됨. <https://docs.jboss.org/hibernate/orm/6.0/migration-guide/migration-guide.html>
[^ug-fetch-limit]: Hibernate ORM 7.2 User Guide, §17.8.4 "join fetch for association fetching" — "Fetch joins should usually be avoided in limited or paged queries." <https://docs.jboss.org/hibernate/orm/7.2/userguide/html_single/Hibernate_User_Guide.html>
[^ug-fail-pagination]: 같은 가이드, Appendix A.16.5 `hibernate.query.fail_on_pagination_over_collection_fetch` (Since 5.2.13, Default false). 위 링크.
[^ug-bag]: 같은 가이드, §3.9.11 "Bags" 및 컬렉션 시맨틱 표(BAG: 중복 허용, 순서 없음). 위 링크.
[^ug-cartesian]: 같은 가이드, §17.8.4 — 여러 컬렉션을 병렬로 fetch 하면 DB 수준 카테시안 곱이 생긴다는 경고. 위 링크.
[^ug-select-new]: 같은 가이드, §17.9.1 "select new". 위 링크.
[^ug-versioned]: 같은 가이드, update 문은 기본적으로 `@Version` 컬럼에 영향을 주지 않으며 `update versioned` 로 지정 가능. 위 링크.
[^ug-flush]: 같은 가이드, §7.1.2 "AUTO flush on JPQL/HQL query". 위 링크.
[^ug-batch]: 같은 가이드, §13 "Batching" — `hibernate.jdbc.batch_size` 기본 비활성, 10~50 권장, "Hibernate disables insert batching at the JDBC level transparently if you use an identity identifier generator", `flush()`/`clear()` 주기적 호출. 위 링크.
[^ug-identity]: 같은 가이드, 식별자 생성기 성능 권고 — "the IDENTITY generators disables JDBC batching for INSERT statements". 위 링크.
[^spring-graph]: Spring Data JPA Reference, "Query Methods → Configuring Fetch- and LoadGraphs" (`@EntityGraph`). <https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html>
[^spring-modifying]: 같은 문서, "Modifying Queries" — `@Modifying(clearAutomatically = true)` 및 `EntityManager.clear()` 가 flush 되지 않은 변경을 버린다는 경고. 위 링크.
