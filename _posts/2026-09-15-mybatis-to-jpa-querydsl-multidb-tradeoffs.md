---
layout: post
title: "Oracle·MySQL·MSSQL 셋을 이고 사는 MyBatis, JPA+QueryDSL 로 갈아탈 것인가 — 기회비용 계산서"
date: 2026-09-15 22:53:00 +0900
categories: [backend, database]
tags: [MyBatis, JPA, QueryDSL, Hibernate, 멀티DB, 마이그레이션, 기회비용]
---

Oracle·MySQL·MSSQL 세 벤더를 동시에 지원하는 시스템을 MyBatis 로 운영 중이고, JPA + QueryDSL 로 옮길지 고민한다고 하자. 이 결정은 흔한 "MyBatis vs JPA" 논쟁과 결이 다르다 — **멀티 DB 라는 조건이 저울 양쪽의 추를 전부 바꿔 놓기 때문이다.** 순서대로: 지금 구조의 실체 → 양쪽의 장단 → 감춰진 비용 → 기회비용 계산 프레임 → 권고.

## 0. 지금 구조의 실체 — MyBatis 멀티 DB 는 "SQL 을 벤더 수만큼" 이다

MyBatis 의 멀티 벤더 공식 해법은 `databaseIdProvider` 다 — 설정에 벤더 식별자를 등록하고, 매핑 구문마다 `databaseId` 로 벤더별 구문을 갈라 쓴다[^mybatis-config]. 동적 SQL(`if`/`choose`/`foreach`)이 이를 보조한다[^mybatis-dynsql].

이 구조는 정직하다. SQL 을 완전히 통제할 수 있는 대신, **벤더 차이를 흡수해 주는 층이 없으므로 차이가 나는 모든 지점에서 SQL 이 벤더 수만큼 늘어난다.** 페이징(Oracle `ROWNUM`/`FETCH FIRST` vs MySQL `LIMIT` vs MSSQL `OFFSET…FETCH`), 시퀀스 vs AUTO_INCREMENT vs IDENTITY, 날짜·문자열 함수, 락 힌트 — 전부 수작업 분기다. 세 DB 를 진지하게 지원한다면 사실상 **쿼리 자산의 상당 부분을 3벌로 유지·테스트**하고 있는 셈이고, 이 유지비가 이 글 전체의 논의 대상이다.

## 1. MyBatis 에 남는 것의 장단

**장점.** SQL 이 곧 코드라서 실행 계획을 눈으로 확인한 그 SQL 이 그대로 나간다. 벤더 전용 기능(옵티마이저 힌트, 분석 함수, MERGE, 계층 쿼리)을 제약 없이 쓴다. DBA 와의 협업 단위가 SQL 파일이라 튜닝 왕복이 짧다. 팀이 이미 알고 있다 — 재학습 비용 0.

**단점.** 위에서 본 3벌 유지비가 구조적으로 계속 나간다. SQL 이 XML 문자열이라 컴파일 타임 검증이 없다 — 컬럼명 오타, 파라미터 누락은 런타임에, 그것도 해당 벤더 경로가 실행될 때에야 드러난다. 세 벤더 중 하나에서만 터지는 SQL 버그는 테스트 매트릭스도 3배로 만든다.

## 2. JPA + QueryDSL 로 가는 것의 장단

**장점의 핵심은 정확히 당신의 고통 지점을 겨냥한다.** Hibernate 는 벤더 차이를 dialect 층에서 흡수한다 — Oracle·MySQL·SQL Server 는 모두 공식 지원 dialect 다[^hib-dialects]. 페이징·식별자 생성·함수 번역이 dialect 를 거쳐 벤더별 SQL 로 렌더링되므로, **JPQL/QueryDSL 로 쓴 쿼리 1벌이 세 DB 에서 돈다.** Hibernate 6 부터는 dialect 가 접속된 DB 의 버전까지 감지해 적응하므로 버전별 dialect 를 고르던 시대의 관리 부담도 없다[^hib6-mig]. QueryDSL 은 그 위에 컴파일 타임 타입 안전을 얹는다 — 컬럼명 오타가 런타임 3벌 테스트가 아니라 **컴파일 에러 1개**로 바뀐다.

**단점.** ① 학습 곡선이 실재한다 — 영속성 컨텍스트·지연 로딩·N+1·플러시 타이밍은 SQL 사고방식과 다른 축의 지식이고, 익숙해지기 전까지는 "내가 쓴 적 없는 SQL" 이 나가는 프레임워크다. ② 복잡한 조회(리포트, 통계, 벤더 전용 힌트가 필요한 튜닝 쿼리)는 결국 네이티브 SQL 로 내려간다 — 그리고 **네이티브로 내려간 만큼 3벌 문제가 그대로 부활한다.** ③ 손으로 튜닝해 둔 기존 SQL 자산은 이관 과정에서 상당 부분 버려진다.

## 3. 감춰진 비용 — QueryDSL 의 거버넌스 리스크

이 결정에서 가장 자주 빠뜨리는 항목이다. **원 QueryDSL 프로젝트(`com.querydsl`)는 사실상 멈춰 있다.** 마지막 릴리스는 5.1.0, 2024년 1월이다[^qdsl-orig]. 커뮤니티는 OpenFeign 산하로 포크했고(`io.github.openfeign.querydsl`), 포크는 2026년 8월의 7.6 까지 정기 릴리스를 이어가고 있다[^qdsl-fork]. Spring Data 공식 문서가 이 상황을 이례적으로 직접 언급한다 — *"Querydsl 유지보수가 느려져 커뮤니티가 OpenFeign 산하로 포크했으며, Spring Data 는 포크를 best-effort 기준으로 지원한다"*[^spring-ext].

보안 관점의 실례도 있다: HQL 인젝션 취약점 CVE-2024-49203 은 두 좌표계 모두에 영향이 기재돼 있고, 패치 버전은 포크 좌표(`io.github.openfeign.querydsl`)로 나왔다[^ghsa]. 즉 지금 QueryDSL 을 새로 도입한다는 것은 **"원 프로젝트가 아니라 커뮤니티 포크를, Spring 의 1급 지원이 아니라 best-effort 지원 아래에서 쓴다"** 는 결정을 함께 내리는 것이다. 못 쓸 물건이라는 뜻이 아니다 — 포크는 활발하다. 다만 선정 문서에 적어야 할 리스크 항목이라는 뜻이다.

참고로 대안인 jOOQ 는 이 시스템에선 무료가 아니다 — 오픈소스 에디션은 오픈소스 DB 만 지원하고, Oracle·SQL Server 는 상용 에디션 대상이다[^jooq].

## 4. 기회비용 계산 프레임 — 결정 변수는 하나다

지불하는 것: 매퍼 XML 재작성 공수, 튜닝 SQL 자산 폐기, 팀 재학습, 이관 기간의 이중 운영, QueryDSL 거버넌스 리스크. 얻는 것: 벤더 차이의 dialect 위임(3벌→1벌), 컴파일 타임 타입 안전, 도메인 모델 중심 설계.

그래서 결정 변수는 하나로 수렴한다. **전체 쿼리 자산 중 dialect 가 흡수할 수 있는 비율이 얼마인가.** 단순 CRUD·조건 검색·페이징이 대부분이라면 멀티 DB 야말로 JPA 전환의 이득이 극대화되는 조건이다 — 단일 DB 시스템보다 절감 폭이 벤더 수만큼 곱해진다. 반대로 벤더 전용 힌트·분석 함수·프로시저 호출이 쿼리 자산의 큰 몫이라면, 그 몫은 전환 후에도 네이티브 3벌로 남으므로 지불한 비용 대비 얻는 게 얇다. 감으로 정하지 말고 **매퍼 XML 을 실제로 분류해 세어 보라** — 이 한나절짜리 조사가 이 결정에서 가장 수익률 높은 작업이다.

## 5. 권고 — 옮기더라도 빅뱅은 아니다

MyBatis 와 JPA 는 같은 DataSource·트랜잭션 관리자 위에서 공존할 수 있다. 그러니 현실적인 경로는:

1. **계측** — 매퍼 XML 전수 분류: dialect 흡수 가능 / 벤더 전용 잔존. 이 비율이 go/no-go 를 정한다.
2. **파일럿** — 신규 도메인 또는 CRUD 비중이 높은 모듈 하나를 JPA+QueryDSL 로. 세 DB 모두에 대한 통합 테스트를 이때 세운다.
3. **공존 운영** — 단순 조회·쓰기부터 점진 이관, 복잡 조회·튜닝 쿼리는 MyBatis 에 남긴다. "전부 옮겨야 성공" 이라는 프레임을 버리면 실패 확률이 크게 준다.
4. **거버넌스 명시** — QueryDSL 좌표는 OpenFeign 포크로 시작하고, 선정 문서에 원 프로젝트 정체·best-effort 지원 사실을 기록한다.

| | MyBatis 유지 | JPA+QueryDSL 전환 |
| --- | --- | --- |
| 벤더 차이 처리 | 수작업 3벌 (databaseId 분기) | dialect 자동 흡수, 잔존분만 네이티브 |
| 타입 안전 | 런타임 (벤더별 경로 실행 시) | 컴파일 타임 (QueryDSL) |
| 벤더 전용 기능 | 무제약 | 네이티브로 우회 (3벌 부활) |
| 재학습 비용 | 0 | 영속성 컨텍스트·N+1 등 실재 |
| 거버넌스 | MyBatis 활발 | QueryDSL 은 포크가 사실상 본류 |

한 줄 요약 — **멀티 DB 는 JPA 전환의 이득을 벤더 수만큼 증폭하는 조건이지만, 그 이득은 dialect 가 흡수 가능한 쿼리에만 발생한다. 매퍼를 세어 보고, 옮긴다면 공존으로 옮겨라.**

---

## 근거의 한계

- 이관 공수(인월)·"한나절짜리 조사" 등의 규모 감각은 내 경험칙이며 정량 출처가 없다. 매퍼 수·팀 규모에 따라 크게 다르다.
- N+1·영속성 컨텍스트 학습 곡선의 크기는 정성 판단이다 — 팀의 사전 경험에 따라 0 에 가까울 수도 있다.
- MyBatis 진영과 JPA 진영의 성능 우열을 다룬 중립 헤드투헤드 벤치마크는 확인하지 못했고, 그래서 성능 주장은 이 글에 없다.
- CVE-2024-49203 의 상세 페이지(NVD)는 스크립트 렌더링이라 본문을 텍스트로 실측하지 못해, 대신 GitHub 공식 어드바이저리를 출처로 썼다.

## References

[^mybatis-config]: MyBatis 공식 문서 — [Configuration](https://mybatis.org/mybatis-3/configuration.html) (`databaseIdProvider`, 벤더별 구문 분기)
[^mybatis-dynsql]: MyBatis 공식 문서 — [Dynamic SQL](https://mybatis.org/mybatis-3/dynamic-sql.html)
[^hib-dialects]: Hibernate ORM 공식 문서 — [Supported Dialects](https://docs.hibernate.org/orm/7.1/dialect/) (Oracle·MySQL·SQL Server 공식 지원 dialect)
[^hib6-mig]: Hibernate ORM 6.0 공식 마이그레이션 가이드 — [Migration Guide](https://docs.hibernate.org/orm/6.0/migration-guide/) (dialect 가 DB 버전을 감지·적응, 버전별 dialect deprecated)
[^qdsl-orig]: GitHub — [querydsl/querydsl](https://github.com/querydsl/querydsl) (최종 릴리스 5.1.0, 2024-01-29)
[^qdsl-fork]: GitHub — [OpenFeign/querydsl](https://github.com/OpenFeign/querydsl) (커뮤니티 포크, 7.6 릴리스 2026-08-19)
[^spring-ext]: Spring Data JPA 공식 문서 — [Core Extensions](https://docs.spring.io/spring-data/jpa/reference/repositories/core-extensions.html) (Querydsl 포크 상황과 best-effort 지원 명시)
[^ghsa]: GitHub Security Advisory — [GHSA-6q3q-6v5j-h6vg](https://github.com/advisories/GHSA-6q3q-6v5j-h6vg) (CVE-2024-49203, Querydsl HQL injection through orderBy)
[^jooq]: jOOQ 공식 — [Download / Licensing](https://www.jooq.org/download/) (오픈소스 에디션의 지원 DB 목록, Oracle·SQL Server 는 상용 에디션)
