---
layout: post
title: "PostgreSQL은 왜 쓰기 빡센가 — 설치는 5분, 운영은 평생인 이유 일곱 가지"
date: 2026-11-20 20:17:32 +0900
categories: [Database]
tags: [PostgreSQL, MVCC, VACUUM, PgBouncer, 운영, 데이터베이스]
---

PostgreSQL은 설치하고 테이블 만들고 쿼리하는 데까지는 아주 쉽다. 표준 SQL을 잘 따르고, 타입이 풍부하고, 확장도 많다. 어려워지는 건 몇 달 뒤다. 디스크가 이유 없이 불어나고, 연결이 모자라고, 어느 날 쿼리 하나가 열 배 느려진다.

"빡세다"는 말의 대부분은 사용법보다 **운영**에서 나온다. 그리고 그 운영 부담의 상당수는 PostgreSQL의 설계에서 곧장 따라 나온다. 아래 일곱 가지를 공식 문서와 1차 자료로 정리했다.

## 한 줄 요약

PostgreSQL은 행을 고칠 때 덮어쓰지 않고 **새 사본을 만든다.** 그 결과로 생기는 쓰레기 치우기(VACUUM)를 사용자가 관리해야 한다. 여기에 연결 하나당 프로세스 하나라는 구조, 메이저 업그레이드의 무게, 플래너 힌트가 없다는 철학이 더해진다.

## 1. 수정하면 행 전체가 복사된다

PostgreSQL은 MVCC(다중 버전 동시성 제어)로 읽기와 쓰기가 서로 막지 않게 한다. MVCC 자체의 원리는 [예전 글]({% post_url 2026-10-10-cs300-171-mvcc %})에서 다뤘다. 문제는 PostgreSQL이 버전을 만드는 **방식**이다.

`UPDATE` 는 기존 행을 고치지 않는다. 행 전체를 새로 써서 새 버전을 만들고, 옛 버전은 그대로 둔다. `DELETE` 도 바로 지우지 않는다. 다른 트랜잭션이 아직 옛 버전을 볼 수도 있기 때문이다 ([PostgreSQL 문서 24.1.2](https://www.postgresql.org/docs/current/routine-vacuuming.html)).

카네기멜런대의 Andy Pavlo 교수는 이 방식을 정면으로 비판한다. 컬럼 1,000개짜리 테이블에서 컬럼 하나만 바꿔도 999개를 함께 복사한다. MySQL(InnoDB)과 Oracle은 바뀐 부분만 델타로 남긴다. Pavlo는 이 설계를 1980년대의 유물이라 부르고, 지금 MVCC DBMS를 새로 만든다면 PostgreSQL처럼 하지 말라고까지 쓴다 ([Pavlo, 2023](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)).

## 2. 쓰레기는 쌓이고, 치워도 디스크는 안 줄어든다

옛 버전(dead tuple)은 누군가 치워야 한다. 그게 `VACUUM` 이다. 공식 문서는 VACUUM이 필요한 이유를 네 가지로 든다. 공간 재사용, 플래너 통계 갱신, visibility map 갱신, 그리고 아래 5번의 트랜잭션 ID 랩어라운드 방지다 ([문서 24.1.1](https://www.postgresql.org/docs/current/routine-vacuuming.html)).

여기서 처음 당황하는 지점이 있다. 일반 `VACUUM` 은 공간을 **재사용 가능**으로 표시할 뿐 OS에 돌려주지 않는다. 테이블 끝 페이지가 통째로 비었을 때만 예외다. 디스크를 실제로 줄이려면 `VACUUM FULL` 이나 `CLUSTER` 처럼 테이블을 새로 쓰는 명령이 필요하고, 이 명령들은 `ACCESS EXCLUSIVE` 락을 잡는다. 그동안은 그 테이블을 읽을 수도 없다. 테이블 크기만큼 디스크도 추가로 필요하다 ([문서 24.1.2](https://www.postgresql.org/docs/current/routine-vacuuming.html)).

최신 문서에는 `REPACK` 이 추가됐다. `CONCURRENTLY` 로 돌리면 파일을 바꿔치는 순간에만 배타 락을 잡는다. 그 전까지는 외부 확장 pg_repack이 이 역할을 했다.

공식 문서가 권하는 방향은 "최소 크기를 유지하라"가 아니다. 자주 VACUUM해서 **크기가 일정하게 유지되게** 하라는 것이다. 바꿔 말하면 PostgreSQL 테이블은 원래 데이터보다 크게 사는 게 정상이다.

## 3. 컬럼 하나 바꿔도 인덱스는 전부 고친다

PostgreSQL의 인덱스는 행의 **물리적 위치**를 가리킨다. 행이 새 버전으로 복사되면 위치가 바뀌니, 바뀐 컬럼과 상관없이 그 테이블의 인덱스를 모두 고쳐야 한다. 예외는 HOT(Heap-Only Tuple) 업데이트다. 새 버전이 같은 페이지에 들어가고, 인덱스가 걸린 컬럼이 바뀌지 않았을 때만 적용된다.

Uber는 2016년 이 문제를 이유로 PostgreSQL에서 MySQL로 옮겼다. 생년 컬럼 하나를 고쳤는데 테이블 본체와 인덱스 셋에 쓰기가 네 번 일어나고, 그 전부가 WAL에도 기록된다는 예시였다. 데이터센터 간 복제에서는 이 부풀어 오른 WAL이 대역폭 문제로 이어졌다 ([Uber Engineering, 2016](https://www.uber.com/us/en/blog/postgres-to-mysql-migration/)).

MySQL InnoDB의 보조 인덱스는 물리 주소 대신 기본 키를 가리킨다. 그래서 바뀐 인덱스만 고치면 된다.

Pavlo는 OtterTune 고객 데이터로 업데이트의 평균 약 46%만 HOT으로 처리된다고 썼다 ([Pavlo, 2023](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)). 다만 이 수치는 자사 고객 표본이다.

**실무에서 할 일:** 안 쓰는 인덱스를 지우는 것이 PostgreSQL에서는 다른 DB보다 훨씬 큰 효과를 낸다. 자주 바뀌는 테이블은 `fillfactor` 를 낮춰 페이지에 빈자리를 남겨 두면 HOT 비율을 올릴 수 있다.

## 4. autovacuum은 켜져 있지만 알아서 잘하지는 않는다

autovacuum 데몬이 VACUUM을 자동으로 돌린다. 문제는 기본값이다.

- `autovacuum_vacuum_scale_factor` 기본값은 20%다. 1억 행 테이블이면 2천만 행이 바뀔 때까지 autovacuum이 움직이지 않는다 ([Pavlo](https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html)). 큰 테이블은 테이블별로 따로 낮춰 줘야 한다.
- **오래 열린 트랜잭션** 하나가 VACUUM을 무력화한다. 그 트랜잭션이 볼 수 있는 옛 버전은 지울 수 없기 때문이다. 쓰레기가 쌓이면 쿼리가 느려지고, 느린 쿼리가 또 긴 트랜잭션이 되는 악순환이 생긴다. 결국 사람이 긴 트랜잭션을 찾아 죽여야 한다. 애플리케이션에서 트랜잭션을 열어 둔 채 외부 API를 기다리는 코드가 흔한 범인이다.
- 파티션 테이블의 부모는 autovacuum이 `ANALYZE` 해 주지 않는다. 자식 테이블이 바뀌어도 부모 통계는 그대로다. 부모 단위 통계가 필요하면 직접 돌려야 한다고 공식 문서가 적고 있다 ([문서 24.1.3](https://www.postgresql.org/docs/current/routine-vacuuming.html)).

공식 문서도 데몬을 통째로 끄는 건 현명하지 않다고 말한다. 남은 선택지는 하나다. 테이블마다 들여다보고 조정하는 것.

## 5. 트랜잭션 ID 랩어라운드 — 조용히 다가오는 정지

PostgreSQL의 트랜잭션 ID(XID)는 32비트이고 모듈로 2³² 산술로 비교한다. 오래된 행을 "얼려(freeze)" 두지 않으면, 과거 트랜잭션이 미래로 보이는 순간이 온다. 그러면 그 데이터가 보이지 않게 된다. 공식 문서 표현으로는 파국적인 데이터 손실이다. 실제로 데이터는 남아 있지만 꺼낼 수 없다 ([문서 24.1.5](https://www.postgresql.org/docs/current/routine-vacuuming.html)).

그래서 모든 데이터베이스의 모든 테이블을 **최소 20억 트랜잭션마다 한 번은** VACUUM해야 한다. PostgreSQL은 경고를 띄우다가, 랩어라운드까지 300만 트랜잭션도 안 남으면 **새 XID 발급을 거부한다.** 그때부터는 읽기 전용 트랜잭션만 시작할 수 있다. 쓰기가 전부 멈추는 셈이다.

autovacuum이 꺼져 있어도 랩어라운드 방지용 VACUUM은 강제로 돈다. 하지만 4번의 긴 트랜잭션이 그것까지 막을 수 있다. 쓰기가 많은 서비스라면 `age(datfrozenxid)` 를 모니터링 항목에 넣어야 하는 이유다.

## 6. 연결 하나 = 프로세스 하나

PostgreSQL은 "사용자당 프로세스" 모델이다. postmaster가 연결 요청마다 백엔드 프로세스를 새로 띄운다 ([문서 51.2](https://www.postgresql.org/docs/current/connect-estab.html)). MySQL이 연결마다 스레드를 쓰는 것과 다르다.

- `max_connections` 기본값은 보통 100이다. 바꾸려면 서버를 **재시작**해야 한다. PostgreSQL은 이 값에 비례해 공유 메모리 같은 자원을 잡는다 ([문서 19.3](https://www.postgresql.org/docs/current/runtime-config-connection.html)).
- 파드가 늘어날 때마다 커넥션 풀도 함께 늘어나는 쿠버네티스 환경이나 서버리스 환경에서는 이 한도에 금방 닿는다.

표준 답은 PgBouncer 같은 외부 풀러다. 애플리케이션 연결 수천 개를 실제 DB 연결 수십 개로 묶어 준다. 하지만 공짜는 아니다. 효율이 좋은 `transaction` 모드에서는 트랜잭션이 끝나면 서버 연결이 다른 클라이언트에게 넘어간다 ([PgBouncer 설정 문서](https://www.pgbouncer.org/config.html)). 그래서 `SET`, `LISTEN`, 세션 단위 advisory lock처럼 세션에 붙는 상태는 기대한 대로 동작하지 않는다. 풀러를 넣는 순간 애플리케이션 코드가 지켜야 할 규칙이 생긴다.

## 7. 메이저 업그레이드는 매번 이사다

메이저 버전 사이에는 내부 저장 형식이 바뀔 수 있다. 그래서 데이터 디렉터리를 새 버전에 그대로 물릴 수 없다 ([문서 18.6](https://www.postgresql.org/docs/current/upgrading.html)). 방법은 세 가지다.

1. `pg_dumpall` 로 덤프 후 복원. 확실하지만 느리다.
2. `pg_upgrade` 로 시스템 카탈로그만 새로 만들고 데이터 파일은 재사용. 빠르다. `--link` 모드를 쓰면 새 클러스터를 띄우는 순간 옛 클러스터로 돌아갈 수 없다.
3. 논리 복제로 새 버전을 옆에 띄우고 전환.

함정은 **확장**이다. `pg_upgrade` 문서는 외부 모듈도 바이너리 호환이어야 하지만 그건 pg_upgrade가 검사할 수 없다고 적는다 ([pg_upgrade 문서](https://www.postgresql.org/docs/current/pgupgrade.html)). pgvector나 PostGIS처럼 확장에 기대는 DB라면 업그레이드 전에 확장 버전부터 맞춰야 한다. 그리고 메이저 버전마다 지원 기간이 정해져 있으니, 이 이사는 몇 년마다 반드시 돌아온다.

## 덤 — 플래너에게 명령할 수 없다

Oracle·MySQL·SQL Server에는 "이 인덱스를 써라" 같은 옵티마이저 힌트가 있다. PostgreSQL 커뮤니티의 공식 입장은, 다른 DB가 하는 방식 그대로의 힌트는 구현할 생각이 없다는 것이다. 이유로는 업그레이드 뒤 오히려 성능을 해치고, 데이터가 커지면 틀리게 되고, 플래너 개선을 방해한다는 점을 든다 ([PostgreSQL 위키](https://wiki.postgresql.org/wiki/OptimizerHintsDiscussion)).

그래서 플랜이 갑자기 뒤집히면 할 수 있는 일은 통계를 고치거나(`ANALYZE`, `SET STATISTICS`, 확장 통계), `enable_*` 파라미터를 만지거나, 외부 확장 pg_hint_plan을 쓰는 것이다. PGDay Lowlands 2026 발표에서는 PostgreSQL 19에 플랜 고정용 확장(pg_plan_advice 등)이 **들어갈 예정**이라고 소개했다 ([Banck, 2026](https://www.postgresql.eu/events/pgdaynl2026/sessions/session/7815/slides/895/postgresql-optimizer-hints.pdf)). 발표 시점 기준의 전망이다.

## 그래도 PostgreSQL을 쓰는 이유

Pavlo도 비판 글 두 달 뒤에 「Yes, PostgreSQL Has Problems. But We're Sticking With It!」을 썼다. MVCC를 갈아 끼운 하드 포크(OrioleDB, YugabyteDB 등)도 있지만, 그 변경이 본가에 합쳐질 일은 없을 거라고 정리했다 ([Pavlo, 2023-06](https://www.cs.cmu.edu/~pavlo/blog/2023/06/yes-postgresql-has-problems-but-were-sticking-with-it.html)).

빡센 부분은 대부분 **알고 나면 관리할 수 있는** 종류다. 모르고 쓰면 몇 달 뒤 한꺼번에 터진다. 운영 첫날부터 챙길 것을 정리하면 다음과 같다.

| 증상 | 원인 | 첫 조치 |
| --- | --- | --- |
| 디스크가 데이터보다 크게 불어남 | dead tuple, bloat | 큰 테이블의 autovacuum 임계치를 테이블별로 낮춤, `pg_stat_user_tables` 의 `n_dead_tup` 감시 |
| VACUUM이 돌아도 안 줄어듦 | 긴 트랜잭션 | `pg_stat_activity` 에서 `xact_start` 가 오래된 세션 찾기, `idle_in_transaction_session_timeout` 설정 |
| 업데이트가 유독 느림 | 인덱스 전부 갱신 | 안 쓰는 인덱스 제거(`pg_stat_user_indexes` 의 `idx_scan = 0`), `fillfactor` 조정 |
| 경고 로그에 wraparound | XID 고갈 접근 | `age(datfrozenxid)` 모니터링, 긴 트랜잭션 제거 후 VACUUM |
| `too many clients` | 연결 = 프로세스 | 풀러 도입, 단 transaction 모드의 세션 상태 제약 확인 |
| 업그레이드 후 확장 오류 | 바이너리 호환 미검사 | `pg_upgrade --check` 전에 확장 버전 정렬 |
| 어느 날 쿼리가 10배 느림 | 통계 낡음, 플랜 뒤집힘 | `EXPLAIN (ANALYZE, BUFFERS)`, `ANALYZE`, 파티션 부모 수동 ANALYZE |

## 근거의 한계

- Pavlo의 비판(2023)은 당시 데이터베이스 튜닝 회사 OtterTune 공동창업자로서 쓴 글이다. HOT 46%는 그 회사 고객 표본이다.
- Uber 사례(2016)는 PostgreSQL 9.2 시절의 이야기다. 당시에도 PostgreSQL 커뮤니티에서 반론이 나왔고, 이후 논리 복제 등이 추가됐다. 같은 결론이 지금도 성립한다고 볼 수는 없다.
- PostgreSQL 19의 플랜 고정 확장은 발표 시점의 예정이다. 실제 릴리스는 이 글에서 확인하지 않았다.
- PostgreSQL과 MySQL의 성능을 중립적으로 맞비교한 최신 자료는 찾지 않았다. 이 글은 어느 쪽이 더 낫다는 주장이 아니라, PostgreSQL을 운영할 때 왜 손이 가는지에 대한 정리다.

## References

1. PostgreSQL Documentation, "24.1. Routine Vacuuming". <https://www.postgresql.org/docs/current/routine-vacuuming.html>
2. PostgreSQL Documentation, "51.2. How Connections Are Established". <https://www.postgresql.org/docs/current/connect-estab.html>
3. PostgreSQL Documentation, "19.3. Connections and Authentication". <https://www.postgresql.org/docs/current/runtime-config-connection.html>
4. PostgreSQL Documentation, "18.6. Upgrading a PostgreSQL Cluster". <https://www.postgresql.org/docs/current/upgrading.html>
5. PostgreSQL Documentation, "pg_upgrade". <https://www.postgresql.org/docs/current/pgupgrade.html>
6. PostgreSQL Wiki, "Optimizer and Query Hints Discussion". <https://wiki.postgresql.org/wiki/OptimizerHintsDiscussion>
7. Andy Pavlo & Bohan Zhang, "The Part of PostgreSQL We Hate the Most", CMU, 2023-04-26. <https://www.cs.cmu.edu/~pavlo/blog/2023/04/the-part-of-postgresql-we-hate-the-most.html>
8. Andy Pavlo, "Yes, PostgreSQL Has Problems. But We're Sticking With It!", CMU, 2023-06-07. <https://www.cs.cmu.edu/~pavlo/blog/2023/06/yes-postgresql-has-problems-but-were-sticking-with-it.html>
9. Evan Klitzke, "Why Uber Engineering Switched from Postgres to MySQL", Uber Engineering, 2016-07-26. <https://www.uber.com/us/en/blog/postgres-to-mysql-migration/>
10. PgBouncer, "Configuration". <https://www.pgbouncer.org/config.html>
11. Michael Banck, "Optimizer Hints in PostgreSQL", PGDay Lowlands 2026. <https://www.postgresql.eu/events/pgdaynl2026/sessions/session/7815/slides/895/postgresql-optimizer-hints.pdf>
