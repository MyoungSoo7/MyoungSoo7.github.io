---
layout: post
title: "JPA 와 MyBatis 는 JDBC 의 무엇을 지웠고, 왜 둘 다 살아남았나"
date: 2026-08-20 21:40:00 +0900
categories: [engineering, database]
tags: [jpa, mybatis, hibernate, ibatis, jdbc, orm, java]
---

**JPA 와 MyBatis 는 서로의 상위/하위 호환이 아니다.** 시간순으로 나열해서 "MyBatis 는 옛것, JPA 가 신것" 이라고 이해하면 두 프레임워크의 실제 관계를 놓친다. 둘은 JDBC 라는 같은 통증에서 갈라져 나와 **서로 다른 방향을 골랐고, 그래서 둘 다 살아남았다.**

먼저 사실 정리부터.

- **JPA 1.0** 명세는 JSR 220 으로 **2006년 5월 11일** 확정, Java EE 5 의 일부로 편입.[^wiki-jpa] 참조 구현은 EclipseLink.
- **MyBatis** 는 **2010년 5월 19일** Apache iBATIS 3.0 에서 포크되어 Google Code 로 이주하면서 새 이름을 받음.[^wiki-mybatis] iBATIS 자체는 2000년대 초부터 있었고, MyBatis 는 그 계보의 연속.
- JPA 는 Hibernate 창시자 **Gavin King** 이 JSR 220 전문가 그룹에 참여해 만든 표준.[^wiki-jpa]

두 프레임워크의 등장 배경을 알려면 그 이전 시대로 먼저 내려가야 한다.

---

## 1. Before JPA / MyBatis — JDBC 만 있던 세계

JDBC 는 1997년(JDK 1.1) 부터 있었다. 스펙 자체는 지금도 살아 있고 두 프레임워크 모두 내부적으로 JDBC 를 쓴다. 문제는 **JDBC 만으로 애플리케이션을 짜면 코드가 어떻게 되느냐** 다.

```java
public User findById(long id) throws SQLException {
    Connection conn = null;
    PreparedStatement ps = null;
    ResultSet rs = null;
    try {
        conn = dataSource.getConnection();
        ps = conn.prepareStatement(
            "SELECT id, name, email FROM users WHERE id = ?");
        ps.setLong(1, id);
        rs = ps.executeQuery();
        if (rs.next()) {
            User u = new User();
            u.setId(rs.getLong("id"));
            u.setName(rs.getString("name"));
            u.setEmail(rs.getString("email"));
            return u;
        }
        return null;
    } finally {
        if (rs != null)   try { rs.close();   } catch (SQLException ignore) {}
        if (ps != null)   try { ps.close();   } catch (SQLException ignore) {}
        if (conn != null) try { conn.close(); } catch (SQLException ignore) {}
    }
}
```

한 개의 SELECT 를 위한 코드가 25줄이다. 이 안에 실제 비즈니스 로직은 없다. 전부 (1) 자원 획득, (2) 파라미터 바인딩, (3) ResultSet → 객체 수동 매핑, (4) 자원 해제 순서 지키기다.

JDBC 시절의 통증을 열거하면.

| 통증 | 실제 모습 |
|---|---|
| **자원 관리** | Connection · Statement · ResultSet 를 `finally` 로 close. 순서 틀리면 커넥션 누수. `try-with-resources` 는 Java 7(2011) 부터. |
| **파라미터 바인딩 수작업** | `ps.setLong(1, id)` 를 인덱스로 관리. 파라미터 추가되면 인덱스 전부 재조정. |
| **결과 매핑 수작업** | ResultSet 컬럼을 하나씩 꺼내 setter 로 넣기. 필드 추가 = 모든 매핑 코드 수정. |
| **SQLException 확산** | Checked exception. 모든 DAO 메서드에 `throws SQLException`. |
| **N+1 관리** | 부모 100개 로드 후 자식을 별도 쿼리로 100번 부르는 실수가 언어 수준에서 안 잡힘. |
| **캐시 없음** | 같은 튜플을 반복 조회해도 매번 DB 왕복. |
| **트랜잭션 수동** | `conn.setAutoCommit(false)` → `commit()` / `rollback()` 을 개발자가 직접. |

이 통증을 어떻게 다룰지에 대해 초기 2000년대에 **두 개의 다른 답** 이 나왔다.

---

## 2. 실패한 전신 — EJB 2.x Entity Beans (2001)

첫 번째 시도는 표준 답이었다 — **EJB 2.x Entity Beans.** 결과는 재난이었다. Wikipedia 자체가 이렇게 요약한다.

> "entity beans, in previous EJB specifications, called for much complicated code and imposed a heavy resource footprint" 그리고 그것들은 "could be used only on Java EE application servers because of interconnections and dependencies in the source code" — 그래서 개발자들은 "lightweight persistent objects provided by either persistence frameworks (such as Hibernate) or data access objects (DAO) instead" 를 선호했다.[^wiki-jpa]

Entity Bean 하나를 만들려면 (1) 홈 인터페이스, (2) 로컬/리모트 인터페이스, (3) Bean 클래스, (4) `ejb-jar.xml` 배포 서술자, (5) 앱 서버 특화 `.xml` — 파일 5~6개가 필요했다. 그리고 그 결과물은 오직 앱 서버 안에서만 돌았다. **표준을 따르면 표준에 갇혔다.**

이 재난에 대한 시장의 반응이 두 갈래로 갈렸다.

---

## 3. 두 갈래의 시작 — Hibernate vs iBATIS (2001~2002)

### 3-1. 갈래 A: Hibernate — "SQL 을 감추자" (ORM)

**Gavin King** 이 만든 Hibernate 는 EJB Entity Bean 의 반대편에서 출발했다.

- POJO(Plain Old Java Object) 하나만 있으면 된다. 앱 서버 필요 없음.
- 개발자는 객체 그래프로 사고한다. `user.getOrders()` 하면 알아서 SQL 을 날린다.
- SQL 은 프레임워크가 생성한다. 개발자는 HQL(객체 지향 질의어)이나 Criteria API 를 쓴다.
- **Object-Relational Mapping** — 객체와 테이블을 매핑한다는 이름 그대로.

핵심 철학: **객체가 먼저다. SQL 은 부산물이다.**

### 3-2. 갈래 B: iBATIS — "SQL 을 살리자" (SQL Mapper)

**Clinton Begin** 이 만든 iBATIS 는 정확히 반대 방향을 골랐다.

- SQL 을 XML 파일에 그대로 쓴다. 개발자가 SQL 을 소유한다.
- Java 메서드를 SQL 문에 매핑한다 — **객체를 테이블에 매핑하는 게 아니다.**
- 결과 컬럼을 자바 객체 필드에 매핑하는 코드만 프레임워크가 처리한다.

Wikipedia 는 이 차이를 한 문장으로 요약한다.

> "Unlike ORM frameworks, MyBatis does not map Java objects to database tables **but Java methods to SQL statements.**"[^wiki-mybatis]

핵심 철학: **SQL 이 먼저다. 객체는 결과를 받는 그릇이다.**

이 두 문장을 나란히 두면, 이후 20년의 논쟁이 이미 그 안에 다 들어 있다.

---

## 4. JPA 1.0 (2006) — Hibernate 스타일이 표준이 됐다

Hibernate 가 급속히 확산되자 Java 진영은 이걸 표준화해야 했다. JSR 220 이 그 결과다. **Gavin King 이 JBoss 대표로 그 전문가 그룹에 참여** 했다는 점에서, JPA 는 사실상 "**Hibernate 의 방식을 표준화한 명세**" 다.[^wiki-jpa]

JPA 가 실제로 지운 것.

- **벤더 종속성**. 이전까지는 Hibernate / TopLink / OpenJPA 등이 서로 다른 API 였다. `@Entity`, `EntityManager`, JPQL 이 공용 어휘가 됐다.
- **EJB Entity Bean 의 무게**. XML 5개가 어노테이션 몇 개로.
- **자원/트랜잭션 수동 관리**. Spring 이 `@Transactional` 을 얹으면서 트랜잭션 경계 관리도 선언적이 됨.

**Before/After 코드**

```java
// JDBC (25줄)
public User findById(long id) throws SQLException { /* 위 예시 */ }

// JPA
@Entity
public class User {
    @Id private Long id;
    private String name;
    private String email;
}

public User findById(long id) {
    return em.find(User.class, id);
}
```

`em.find(User.class, id)` 한 줄이 나머지를 다 처리한다. Connection 도, ResultSet 도, 매핑도 개발자 눈에 안 보인다.

---

## 5. MyBatis (2010) — SQL 매퍼 노선의 지속

Hibernate 가 표준화(JPA)로 흘러갈 때 iBATIS 는 다른 길로 갔다. 2010년 5월 19일 Apache iBATIS 3.0 이 발표되면서 팀은 새 이름 **MyBatis** 로 Google Code 에 옮겨 자립했다.[^wiki-mybatis] 이 시점의 결정이 지금의 두 갈래 지형을 만들었다.

MyBatis 는 무엇을 지웠나.

- **JDBC 보일러플레이트의 80%**. 자원 관리, 예외 변환, 파라미터 바인딩은 프레임워크가 처리.
- **결과 매핑 수작업**. `<resultMap>` 또는 컬럼-필드 자동 매핑.

**동시에 무엇을 지키지 않았나.**

- **SQL 자체는 개발자가 쓴다.** `<select>` 태그 안에 그대로. 벤더 특화 SQL, stored procedure, 복잡한 window function, 힌트, `MERGE` 문 — 다 쓸 수 있다.
- **객체-테이블 매핑을 강제하지 않는다.** 조회 결과 형태에 맞춘 DTO 를 자유롭게 정의. 한 쿼리가 여러 테이블에서 필드 뽑아 하나의 뷰 DTO 로 돌려주는 게 자연스러움.

**MyBatis 예시**

```xml
<select id="findById" resultType="User">
    SELECT id, name, email FROM users WHERE id = #{id}
</select>
```

```java
public interface UserMapper {
    User findById(@Param("id") long id);
}
```

25줄의 JDBC 가 XML 3줄 + 인터페이스 1줄이 됐다. **하지만 SQL 은 그대로 눈에 보인다.** 이게 핵심 차이다.

---

## 6. 두 접근이 각자 지운 것과 남긴 것

|  | JPA (ORM) | MyBatis (SQL Mapper) |
|---|---|---|
| **철학** | 객체 먼저, SQL 은 생성됨 | SQL 먼저, 객체는 결과 그릇 |
| **지운 것** | SQL 작성 자체, 연관 관계 순회, 트랜잭션 · 캐시 | JDBC 자원/예외 처리, 파라미터 바인딩, 결과 매핑 |
| **남긴 통증** | 어려운 SQL 을 표현하기 힘듦 (JPQL 한계), N+1, 세미콜론 · 힌트 벤더 특화, 러닝 커브 | SQL 을 여전히 개발자가 씀 → DBMS 이식성 낮음, 캐시 없음, 관계 그래프 자동 로딩 없음 |
| **N+1** | 자동으로 발생 (지연 로딩), `@BatchSize` · fetch join 등으로 관리 | 자동으로 발생 안 함 (개발자가 쿼리 통제) |
| **DDL 자동** | `hibernate.hbm2ddl.auto=update` 등 | 없음 (Flyway · Liquibase 별도) |
| **쓰기 좋은 곳** | 도메인 모델이 잘 정의된 새 시스템, CRUD 위주 API | 레거시 DB, 복잡한 리포트 · 통계 쿼리, 성능 튜닝 중요 시스템 |

두 표의 어느 열도 "다른 열보다 우월" 하지 않다. **다른 종류의 문제를 잘 푸는 것이다.**

---

## 7. 왜 한국에서 MyBatis 가 유독 강한가

전 세계 자바 시장 기준으로 JPA(Hibernate) 는 사실상 표준이다. 그런데 한국의 자바 백엔드 시장에서는 여전히 **MyBatis 점유율이 매우 높다.** 이건 기술적 우열의 문제가 아니라 **환경 차이** 다.

- **레거시 데이터베이스 우위**. 금융 · 공공 · 대기업 SI 는 수십 년 된 DB 스키마를 다룬다. 조인 · 뷰 · 프로시저가 이미 존재하고, 그것을 그대로 감싸 쓰는 게 자연스럽다. JPA 로 매핑하려면 스키마를 뒤엎어야 하는 경우가 많다.
- **DBA 중심 문화**. SQL 튜닝은 DBA 가 한다는 관행. 개발자가 짠 SQL 을 DBA 가 리뷰 · 튜닝 · 실행 계획 확정 후 배포한다. JPA 가 자동 생성한 SQL 은 이 관행에 잘 맞지 않는다.
- **성능 튜닝 요구가 높다**. 트래픽 피크가 뚜렷한 사용자 대상 서비스(뱅킹, 게임, 커머스) 가 많고, 여기서 자동 생성된 SQL 은 문제가 잘 안 보인다.
- **교재/커뮤니티 관성**. 2010년대 초반 국내 자바 교재 · 강의가 MyBatis 중심으로 정착. 신규 개발자가 처음 배우는 게 MyBatis 여서 계속 채용된다.

이 조건들이 뒤집히지 않는 한 MyBatis 는 한국 시장에서 사라지지 않는다. **JPA 가 MyBatis 를 대체할 미래는 오는 게 아니라, 오지 않는 게 정상이다** — 두 프레임워크의 문제 영역이 다르니까.

---

## 8. 정리 — JDBC 이후 갈라진 두 길

**JDBC 이전** 은 없다. Java 세계에서 관계형 DB 접근은 처음부터 JDBC 였다. **JDBC 만 있던 시절** 은 25줄짜리 SELECT 와 커넥션 누수와 checked exception 지옥이었다. 여기서 두 갈래가 나왔다.

- **JPA / ORM 노선**: SQL 을 감춰라. 객체 그래프로 사고하라. 성능 최적화는 프레임워크가 돕는다. 대가로 SQL 통제권을 어느 정도 내려놓는다. → **"객체가 진실이다."**
- **MyBatis / SQL 매퍼 노선**: SQL 을 지켜라. 결과 매핑과 자원 관리만 대신 해달라. 대가로 매핑 코드와 XML 을 다룬다. → **"SQL 이 진실이다."**

이 두 문장 중 어느 쪽이 진실이냐는 논쟁이 15년째 이어지지만, 답은 **"당신의 시스템에서 진실이 무엇이냐" 에 달려 있다.** 새로 짜는 마이크로서비스에서 도메인 모델이 명확하다면 JPA 가 맞다. 20년 된 정산 시스템의 복잡한 조인 쿼리를 다룬다면 MyBatis 가 맞다. **한 프로젝트에 둘 다 쓰는 것도 정상이다** — Spring 이 둘 다 자연스럽게 통합한다.

**한 문장으로**: JPA 는 "SQL 을 쓰지 않아도 되게" 하려 왔고, MyBatis 는 "SQL 을 지키되 JDBC 의 지저분함만 걷어내려" 왔다. 두 목표가 서로 배타적이지 않아서, 두 프레임워크가 20년 동안 공존한다.

---

[^wiki-jpa]: Wikipedia, _Jakarta Persistence_ — <https://en.wikipedia.org/wiki/Jakarta_Persistence>. JPA 1.0 명세는 JSR 220 으로 2006년 5월 11일 확정, Java EE 5 편입; 참조 구현은 EclipseLink; Gavin King 이 JBoss 대표로 JSR 220 참여; EJB 2.x Entity Beans 의 무거움과 앱 서버 종속이 배경.

[^wiki-mybatis]: Wikipedia, _MyBatis_ — <https://en.wikipedia.org/wiki/MyBatis>. 2010년 5월 19일 Apache iBATIS 3.0 발표와 동시에 Google Code 로 이주하며 MyBatis 로 개명; iBATIS 는 MyBatis 이전의 원조 프로젝트; "MyBatis does not map Java objects to database tables but Java methods to SQL statements" 는 ORM 과의 결정적 차이를 요약하는 프로젝트 자체의 자기 규정.
