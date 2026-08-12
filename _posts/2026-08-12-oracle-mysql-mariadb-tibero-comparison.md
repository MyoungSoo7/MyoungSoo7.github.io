---
layout: post
title: "Oracle · MySQL · MariaDB · Tibero — 벤치마크 표 없이 쓰는 4대 RDBMS 비교"
date: 2026-08-12 20:35:00 +0900
categories: [engineering, database]
tags: [oracle, mysql, mariadb, tibero, rdbms, sql, licensing, isolation-level]
---

이 글에는 "A가 B보다 몇 배 빠르다" 같은 표가 없다. 그걸 쓸 수 있는 근거가 없기 때문이다.

이유는 두 가지다. 첫째, 이 네 제품을 **동일 조건에서 돌린 중립 제3자 head-to-head 벤치마크가 공개된 게 없다.** 둘째, 애초에 그런 걸 공개하기 어렵게 만드는 계약 조항이 있다. Oracle Technology Network 개발자 라이선스는 금지 행위 목록에 이렇게 적어 뒀다.[^otn]

> "disclose results of any Program benchmark tests without Oracle's prior consent."

업계에서 흔히 **DeWitt 조항**이라 부르는 것이다. (참고로 Oracle Free Use Terms 에는 이 문구가 없다.[^ofl] 무료 에디션과 상용 다운로드의 약관이 다르다.)

그래서 이 글은 방향을 바꾼다. 숫자 대신 **성능을 결정하는 구조**를 비교한다. MVCC를 무엇으로 구현했는지, 기본 격리수준이 무엇인지, 옵티마이저가 어떤 통계를 보는지, 그리고 — 실무에서 제일 자주 발목을 잡는 — **성능 기능 중 무엇이 유료 뒤에 잠겨 있는지**. 마지막으로 네 DB를 오가며 SQL을 짜는 사람이 데는 지점을 정리한다.

기준 시점은 **2026년 8월**이다. 이 바닥은 1년이면 표가 바뀐다.

---

## 1. 지금 쓰는 버전 (2026년 8월 기준)

먼저 전제를 하나 깨야 한다. **널리 알려진 버전 상식 중 최소 세 개가 이미 낡았다.**

### Oracle — 23ai는 없다, 26ai로 갈아탔다

2025년 10월, Oracle은 제품명을 **Oracle AI Database** 로 바꾸고 **26ai** 를 내놨다. 23ai를 대체하는 Long Term Support Release다.[^ora26]

> "Oracle AI Database 26ai replaces Oracle Database 23ai. Transitioning from 23ai to 26ai is simple—just apply the October 2025 release update with no database upgrade or application re-certification."

현행 Lifetime Support Policy 문서(2026-08-07 판)의 Oracle Database Releases 표에는 **23ai 행이 아예 없다.**[^oralsp] 온프레미스 Linux x86-64 GA는 2026년 1월 분기 RU(버전 23.26.1)로 이루어졌다.[^ora26ga]

| 릴리스                          | GA      | Premier 종료 | Extended 종료 |
| ------------------------------- | ------- | ------------ | ------------- |
| **19c** (Long Term Support)     | 2019-04 | **2029-12**  | **2032-12**   |
| 21c (Innovation)                | 2021-08 | 2027-07      | **없음**      |
| **26ai EE** (Long Term Support) | 2025-10 | **2031-12**  | TBD           |

여기서 실무자가 챙길 건 두 가지다.

**Innovation Release에는 Extended Support가 아예 없다.** 21c 행의 Extended 칸은 문자 그대로 "Not Available" 이다.[^oralsp] Premier가 끝나면 곧장 Sustaining으로 떨어진다 — 뒤에 설명하겠지만 그건 **보안 패치가 안 나온다**는 뜻이다. "최신이니까 좋겠지" 하고 Innovation을 프로덕션에 올리면 나중에 물러설 자리가 없다.

그리고 **19c는 2027년 5월부터 Java 8 관련 서드파티 지원이 빠진다.**[^oralsp] 아직 19c로 버티는 곳이 많은데, 이 각주는 잘 안 읽힌다.

### MySQL — 8.0은 이미 EOL이다

이게 이 글에서 가장 중요한 실무 정보일 것이다. **MySQL 8.0은 2026년 4월 21일부로 Sustaining Support로 내려갔다.**[^myeol]

> "April 21, 2026 — MySQL 8.0 is covered under Oracle Lifetime Sustaining Support. … Users are encouraged to upgrade to MySQL 8.4 LTS or 9.7 LTS."

Sustaining Support가 무엇을 **안 주는지**가 핵심이다. Lifetime Support Policy 원문은 이렇게 적는다.[^oralsp]

> "Sustaining Support does not include: • New updates, fixes, security alerts, data fixes, and critical patch updates …"

즉 **8.0은 더 이상 신규 보안 패치 대상이 아니다.** 지금 프로덕션이 8.0이라면 그게 이 글에서 가장 먼저 처리할 일이다.

| 릴리스      | GA      | Premier 종료 | Extended 종료      |
| ----------- | ------- | ------------ | ------------------ |
| 8.0         | 2018-04 | 2025-04      | **2026-04 (종료)** |
| **8.4 LTS** | 2024-04 | 2029-04      | 2032-04            |
| **9.7 LTS** | 2026-04 | 2031-04      | 2034-04            |

한 가지 더. **9.x = Innovation 이라는 도식도 이제 틀렸다.** 9.0~9.6이 Innovation이었고 **9.7이 LTS로 확정**됐다. 그리고 2026년 7월부터 버전 체계가 **캘린더 버저닝(YY.M)** 으로 바뀌었다 — 현재 Innovation trunk는 `MySQL 26.7` 이다.[^mycal] 실제로 mysql-server trunk의 LICENSE 헤더가 `MySQL 26.7.0 Community` 로 찍혀 있다.[^mylic] 8.4·9.7 LTS 라인은 기존 번호를 유지한다.

LTS를 건너뛰는 업그레이드는 지원되지 않는다는 것도 알아둘 것 — 8.4 → 9.7은 되지만 9.7을 건너뛸 수 없다.[^myrel]

### MariaDB — 연 1회 LTS, 10.6은 지난달 끝났다

MariaDB Foundation은 **연 1회 LTS** 를 내고 Community 바이너리를 **GA 후 3년** 유지한다(11.4 이전 릴리스는 5년).[^marlife]

| 릴리스 | GA         | Community EOL         |
| ------ | ---------- | --------------------- |
| 10.6   | 2021-07-06 | **2026-07-06 (종료)** |
| 10.11  | 2023-02-16 | 2028-02-16            |
| 11.4   | 2024-05-29 | 2029-05-29            |
| 11.8   | 2025-06-04 | 2028-06-04            |
| 12.3   | 2026-05-28 | 2029-06-12            |

표를 보면 이상한 게 하나 있다. **11.8이 11.4보다 먼저 끝난다.** 오타가 아니라 정책 전환 때문이다 — 11.4는 구 5년 정책, 11.8은 신 3년 정책을 따른다.[^mar106]

> "You can notice that MariaDB 11.8 reaches Community EOL before MariaDB 11.4. That is because MariaDB 11.4 has a longer Community maintenance period, while MariaDB 11.8 follows the newer yearly LTS model with three years of Community maintenance."

"최신이 더 오래 간다"는 직관이 여기선 틀린다. 장기 운영이 목적이면 11.4를 고르는 게 합리적일 수 있다.

### Tibero — 7.2.6, 그리고 6은 이미 EOS

현재 주력은 **Tibero 7**이고, 최신 패치셋은 **7.2.6**(2026-07-31 배포)이다. 릴리스 이력이 공식 매뉴얼에 표로 공개돼 있다.[^tbrel]

| 배포일         | 버전      |
| -------------- | --------- |
| 2022-08-26     | 7.2       |
| 2024-04-30     | 7.2.1     |
| 2025-03-31     | 7.2.3     |
| 2026-03-31     | 7.2.5     |
| **2026-07-31** | **7.2.6** |

**Tibero 6는 2024-03-31 EOL, 2025-03-31 EOS를 이미 지났다.** Extended Support가 2028-03-31까지 열려 있지만 유지보수 비용에 15%가 추가된다.[^tbeol] Tibero 7의 판매 종료 기준은 "차기 버전 출시 후 2년"이라 아직 시한이 확정되지 않았다.

한 가지 짚어둘 만한 점 — **Tibero는 매뉴얼 전체를 로그인 없이 공개한다.**[^tbdoc] 국내 상용 DBMS 중에서는 드문 편이고, 이 글이 Tibero에 대해 벤더 마케팅 대신 1차 문서를 인용할 수 있는 이유이기도 하다.

---

## 2. 성능은 결국 구조 차이다

### MVCC를 무엇으로 구현했는가

**Oracle은 undo 세그먼트로 읽기 일관성을 만든다.**[^oracncpt]

> "Oracle Database achieves read consistency through undo data. Whenever a user modifies data, Oracle Database creates undo entries, which it writes to undo segments."

이 설계의 대가가 그 유명한 **ORA-01555 snapshot too old** 다. 긴 조회 트랜잭션이 필요로 하는 옛 버전이 undo에서 재사용돼 사라지면 쿼리가 죽는다. MySQL/MariaDB의 InnoDB도 undo 기반 MVCC를 쓰지만 표면화되는 증상이 다르다 — 이쪽은 오래된 읽기 뷰가 undo 로그를 붙잡아 **history list가 부풀고 테이블스페이스가 커지는** 쪽으로 나타난다.

### 기본 격리수준이 다르다 — 그리고 이게 코드를 바꾼다

여기가 네 DB 비교에서 가장 실전적인 차이다.

**Oracle은 READ COMMITTED가 기본이고, 애초에 REPEATABLE READ를 제공하지 않는다.**[^oracncpt]

> "Oracle Database offers the read committed (default) and serializable isolation levels. Also, the database offers a read-only mode."

**MySQL InnoDB는 REPEATABLE READ가 기본이다.**[^myiso]

> "The default isolation level for InnoDB is REPEATABLE READ."

이게 왜 중요한가. MySQL은 REPEATABLE READ에서 **gap lock / next-key lock** 을 건다.[^myiso]

> "For other search conditions, InnoDB locks the index range scanned, using gap locks or next-key locks to block insertions by other sessions into the gaps covered by the range."

반면 READ COMMITTED로 내리면 gap locking이 사실상 꺼지고, 대신 팬텀이 생긴다.

> "Because gap locking is disabled, phantom row problems may occur, as other sessions can insert new rows into the gaps."

**결론:** `SELECT로 존재 확인 → 없으면 INSERT` 라는 흔한 패턴은 Oracle과 MySQL에서 **동시성 동작이 다르다.** Oracle에서 멀쩡하던 코드가 MySQL에서 갭 락 데드락을 만들고, MySQL에서 갭 락이 막아 주던 중복이 Oracle에서 뚫린다. 어느 쪽이든 유니크 제약으로 막는 게 정답이지, 격리수준에 기대면 안 된다.

MySQL 매뉴얼 자체가 이런 경고를 달아 뒀다.[^myiso]

> "It is not recommended to mix locking statements (UPDATE, INSERT, DELETE, or `SELECT ... FOR ...`) with non-locking SELECT statements in a single REPEATABLE READ transaction, because typically in such cases you want SERIALIZABLE."

### MariaDB는 같은 REPEATABLE READ가 아니다

MariaDB도 기본은 REPEATABLE READ다.[^marset] 그런데 **11.6.2부터 `innodb_snapshot_isolation` 기본값이 `ON` 으로 바뀌었다.**[^marsnap]

> "If enabled (set to `ON`), an error `DB_RECORD_CHANGED` … is raised if an attempt is made to acquire a lock on a record that does not exist in the current read view. This error is treated in the same way as a deadlock, and the transaction is rolled back. **This affects the default isolation level, REPEATABLE READ.**"

즉 MySQL에서 조용히 **lost update** 로 넘어가던 상황이 MariaDB 11.6.2+ 에서는 **ERROR 1020으로 롤백**된다. "MariaDB는 MySQL 호환"이라는 감각으로 재시도 로직 없이 옮기면 운영에서 새 에러가 터진다. 개인적으로는 이게 요즘 두 제품이 갈라진 지점 중 가장 실전적이라고 본다.

### 옵티마이저 — MariaDB의 통계는 "쓰긴 하는데 모으진 않는다"

MariaDB에는 스토리지 엔진과 무관한 통계(EITS)와 히스토그램이 있다. 그런데 기본 설정에 함정이 있다.[^mareits]

> "The use_stat_tables system variable is set to `preferably_for_queries` by default. With this value, engine-independent statistics are **used** by default if available, but they are **not collected** by default."

히스토그램도 마찬가지다.[^marhist]

> "Histograms are used by default from MariaDB 10.4.3 if they are available. However, histogram statistics are not automatically collected, as collection is expensive, requiring a full table scan."

**쓰기는 하는데 모으지는 않는다.** `ANALYZE TABLE ... PERSISTENT FOR ALL` 을 직접 돌리지 않으면 그 기능은 켜져 있으나 마나다. 비인덱스 컬럼 조건이 많은 쿼리에서 실행계획이 이상하면 여기부터 보는 게 맞다.

옵티마이저 힌트도 버전을 봐야 한다. MySQL 스타일 힌트(`JOIN_ORDER`, `NO_RANGE_OPTIMIZATION`, `MAX_EXECUTION_TIME` 등)는 **MariaDB 12.0/12.1에서 들어왔다.**[^marhint] **11.4·11.8 LTS에는 없다.** 힌트를 쓰려면 12.3 LTS 이상이어야 한다.

### 스토리지 엔진 — MariaDB만의 선택지

MariaDB는 InnoDB 외에 Aria, MyRocks, 분석용 ColumnStore, 샤딩용 Spider 등을 플러그블하게 제공하고,[^marreadme] **이들 모두 GPLv2 Community 서버에 포함된다.** ColumnStore는 10.5부터 서버 본체에 통합됐다.[^marcs] "분석 쿼리를 위해 컬럼 스토어를 붙인다"를 라이선스 비용 없이 할 수 있다는 건 실질적인 차이다.

### Tibero — 최대 세션 수가 기동 시점에 고정된다

Tibero는 다중 프로세스 + 다중 스레드 구조이고, 워커 프로세스 하나에 기본적으로 컨트롤 스레드 1개 + **워커 스레드 10개**가 뜬다.[^tbarch] 여기까지는 평범한데, 다음 문장이 운영에 직접 영향을 준다.

> "Tibero는 세션 멀티플렉싱(Session multiplexing)을 지원하지 않으므로 하나의 클라이언트 접속은 곧 하나의 세션과 같습니다. 그러므로 최대 세션이 생성될 수 있는 개수는 WTHR_PROC_CNT \* WTHR_PER_PROC를 연산한 값과 같습니다."

즉 **최대 동시 세션 수가 두 파라미터의 곱으로 하드하게 정해진다.** 그리고 결정적으로,

> "일단 Tibero가 기동된 뒤에는 변경할 수 없습니다."

**재기동 없이는 못 늘린다.** 커넥션 풀 크기를 올렸다가 상한에 부딪히면 그 자리에서 해결할 방법이 없다는 뜻이다. 문서 스스로 이 파라미터를 직접 만지기보다 `MAX_SESSION_COUNT` 를 쓰라고 권한다.

문서가 자기 단점을 명시한 대목도 있다. 워커 스레드는 접속이 끊겨도 소멸하지 않고 인스턴스 기동~종료까지 유지되는데,

> "실제 클라이언트의 수가 적더라도 초기화 파라미터에 설정된 개수만큼 스레드를 생성해야 하므로 운영체제의 리소스를 계속 소모하는 단점은 있으나…"

접속 시 스레드 생성 비용이 없다는 이점과 맞바꾼 설계다. 벤더 문서가 트레이드오프를 이렇게 적어 두는 건 흔치 않아서, 인용할 가치가 있다고 봤다.

### 복제 — GTID 포맷이 아예 다르다

MariaDB GTID는 `Domain:ServerID:Sequence`, MySQL은 `UUID:Sequence` 다. MariaDB 공식 마이그레이션 매트릭스는 이 항목의 영향도를 **Critical** 로 표시한다.[^marmatrix]

> "GTID Format | `UUID:Sequence` | `Domain:ServerID:Sequence` | **Critical. Formats are incompatible. GTID replication cannot be mixed directly.**"

MariaDB의 `Domain` 필드는 장식이 아니라 **out-of-order 병렬 복제**를 위한 설계다.[^marpar] MySQL GTID에는 이 개념 자체가 없다.

---

## 3. 유료와 무료 — 경계선이 어디에 그어져 있나

### Oracle — 성능 진단 도구부터 유료다

정가는 공개돼 있다. Oracle Technology Global Price List(2026-08-03 판) 기준, Processor 라이선스 / 연간 Software Update License & Support:[^orapl]

- **Enterprise Edition** — $47,500 / $10,450
- **Standard Edition 2** — $17,500 / $3,850

그런데 EE를 샀다고 끝이 아니다. **성능과 직결되는 핵심 기능 상당수가 EE 위의 별도 유료 옵션**이고, SE2에서는 아예 못 쓴다.[^oradblic]

| 옵션                      | SE2 | EE        | 추가 비용(Proc) |
| ------------------------- | --- | --------- | --------------- |
| Partitioning              | ✗   | 별도 유료 | $11,500         |
| Database In-Memory        | ✗   | 별도 유료 | $23,000         |
| Real Application Clusters | ✗   | 별도 유료 | $23,000         |
| Advanced Compression      | ✗   | 별도 유료 | $11,500         |
| Diagnostics Pack          | ✗   | 별도 유료 | $7,500          |
| Tuning Pack               | ✗   | 별도 유료 | $5,000          |

라이선스 매뉴얼은 못을 박는다 — _"You must be licensed for an option in order to use any of its features."_[^oradblic]

**개발자가 실제로 데는 건 Diagnostics Pack이다.** AWR과 ADDM이 여기 들어 있다.[^oradblic]

> "Oracle Diagnostics Pack includes the following features: … **Automatic Workload Repository (AWR)** … **Automatic Database Diagnostic Monitor (ADDM)** … Active Session History (ASH) … In order to use the features listed above, you must purchase licenses for Oracle Diagnostics Pack."

그리고 접근 경로를 가리지 않는다.

> "Any and all methods of accessing Oracle Diagnostics Pack functionality, whether through Enterprise Manager Console, Desktop Widgets, command-line APIs, or **direct access to the underlying data**, requires an Oracle Diagnostics Pack license."

`DBA_HIST_*` 뷰를 직접 조회하는 것도, `awrrpt.sql` 을 돌리는 것도 라이선스 대상이라는 뜻이다. **"성능이 이상해서 AWR 좀 떠봤다"가 라이선스 위반이 될 수 있다.** 무심코 하는 일이라 더 위험하다. `CONTROL_MANAGEMENT_PACK_ACCESS` 파라미터로 접근 자체를 막아 둘 수 있으니, 라이선스가 없다면 `NONE` 으로 잠가 두는 편이 안전하다.

무료 옵션도 있다. **Oracle AI Database 26ai Free** — 다만 상한이 명확하다.[^orafree]

> "Oracle AI Database 26ai Free lets you use up to 2 CPUs, 2 GB of RAM, and 12 GB of storage for your data"

재미있는 건 **26ai 세대의 Free 에디션에는 In-Memory와 Advanced Compression, Diagnostics/Tuning Pack이 "Included option" 으로 들어간다**는 점이다.[^oradblic26] EE에서는 수만 달러짜리인 것들이 12GB 장난감판에서는 공짜다. 학습·PoC 용도로는 꽤 후한 셈이다.

### MySQL — 무료의 범위가 생각보다 넓다

MySQL은 **GPLv2 + 상용 이중 라이선스**다.[^myoem]

여기서 오해가 많다. **사내에서 서버로 돌리는 것 자체는 상용 라이선스 트리거가 아니다.** 트리거는 **배포와 임베딩**이다.[^myoem]

> "OEMs …, ISVs …, VARs … and other distributors that combine and distribute commercially licensed software with MySQL software and do not wish to distribute the source code for the commercially licensed software under version 2 of the GNU General Public License (the 'GPL') must enter into a commercial license agreement with Oracle."

그리고 흔히 유료라고 잘못 아는 것 하나 — **HA는 무료다.** Community Edition에 Group Replication, InnoDB Cluster, MySQL Router, Partitioning, Performance Schema가 모두 포함된다.[^mycomm]

정말로 상용 전용인 것 중 성능에 직결되는 건 **Thread Pool** 이다.[^mytp]

> "MySQL Enterprise Thread Pool is an extension included in MySQL Enterprise Edition, a commercial product."
> "The default thread-handling model in MySQL Server executes statements using one thread per client connection. As more clients connect to the server and execute statements, overall performance degrades."

동시 접속이 많은 워크로드에서 커넥션당 스레드 모델의 한계를 넘고 싶다면, 그건 유료 기능이다. (물론 이 서술은 **Oracle 자사 문서의 정성적 주장**이고, 재현 가능한 중립 벤치마크가 붙어 있지는 않다.) 그 외 Enterprise Backup(핫 백업), Audit, Firewall이 상용 전용이다.[^mybk][^myaudit][^myfw]

**TDE는 "전부 유료"가 아니다.** InnoDB 저장 데이터 암호화 자체는 모든 에디션에서 되고, 로컬 파일 키링(`component_keyring_file`)도 Community에 있다. 상용 전용은 **중앙집중식 키 관리**(Oracle Key Vault, AWS KMS, HashiCorp Vault 연동)와 결합한 형태다.[^mytde]

참고로 **MySQL Enterprise Monitor는 2025년 1월 1일부로 EOL** 이다.[^myeol] 오래된 비교 글이 아직도 이걸 "상용 장점"으로 적어 두는 경우가 있는데 이제 틀린 말이다.

### MariaDB — 서버는 GPLv2, 함정은 MaxScale

MariaDB Server 본체는 **GPLv2**이며, MySQL에서 상속받아 _"any later version"_ 조항이 없다.[^marlicense] 재단은 이걸 명시적으로 약속한다.[^marabout]

> "MariaDB Server will remain Free and Open Source Software licensed under GPLv2, independent of any commercial entities."

Enterprise 전용(유료)인 것들: MariaDB Backup, Enterprise Audit, 인덱스 한도 64→128, Hashicorp Vault 플러그인, InnoDB redo 로그 동적 리사이즈, Galera 관련 엔터프라이즈 기능 등.[^mardiff]

**정작 조심해야 하는 건 MaxScale이다.** 프록시/로드밸런서로 흔히 같이 쓰는데, 라이선스가 서버와 **다르다** — Business Source License다.[^marmaxscale]

> "Additional Use Grant: You may use the Licensed Work when your application uses the Licensed Work with a total of **less than three server instances** in production."
> "The Business Source License (this document, or the 'License') **is not an Open Source license**."

**프로덕션 서버 3대 미만이면 무료, 3대 이상이면 상용 라이선스가 필요하다.** "MariaDB는 오픈소스니까 다 공짜"라고 넘어가면 여기서 걸린다. 다만 BSL은 4년 뒤(또는 명시된 Change Date에) GPLv2로 전환된다.[^marbsl]

### Tibero — 상용 전용, 다만 가격은 공개돼 있다

Tibero에는 **무료 커뮤니티/개발자 에디션이 없다.** 공식 설치 안내서가 구분하는 건 두 가지뿐이다 — CPU 수와 기능으로 라이선싱되는 정식판, 그리고 **기간·사용자 수가 제한된 평가판**.[^tbinst] 앞의 세 제품과 결정적으로 다른 지점이다.

라이선싱은 **Core 기반**이고 SE/EE 2개 에디션이다.[^tblic]

> "Core 기반 Licensing 모델을 적용합니다." / "데이터베이스에 할당된 총 Core 수를 기준으로 라이선스를 산정합니다."

**Standard Edition은 노드당 8 Core 이하**, Enterprise Edition은 Core 제한이 없다. 그리고 라이선스 파일이 기능을 강제한다 — _"라이선스 범위를 초과하는 기능 사용 시 실행 제한 또는 오류가 발생할 수 있습니다."_

여기서 Oracle과 판박이인 구조가 나온다. **TAC(Tibero Active Cluster)는 SE에서 아예 미지원이고, EE에서도 별도 유상 옵션이다.**[^tbha]

> "SE | 미지원 / EE | 별도 유상 옵션" — "TAC는 EE 전용 옵션으로 제공됩니다."

Partition, Compression도 마찬가지로 SE 미지원 + EE 별도 유상이다.[^tbperf] 그리고 성능에 직결되는 **Query Results Cache, In-Memory Column Store, SQL Tuning, SQL Plan Management, Database Resource Manager, Instance Caging이 전부 SE "미제공" / EE "기본 제공"** 이다.[^tbed] Oracle의 SE2가 Partitioning·In-Memory를 못 쓰는 것과 같은 그림이다.

가격은 두 계열이 공개돼 있는데, **성격이 달라서 섞어 쓰면 안 된다.**

**(a) 벤더 정가(List Price, 2025-07-01 시행)** — Core당[^tbprice]

| 항목                              | 영구            | 월 구독      |
| --------------------------------- | --------------- | ------------ |
| Tibero Standard                   | 6,245,000원     | 250,000원    |
| Tibero Enterprise                 | 50,852,000원    | 1,990,000원  |
| (EE 옵션) TAC                     | 24,623,000원    | 970,000원    |
| (EE 옵션) Partition / Compression | 각 14,100,000원 | 각 560,000원 |

**(b) 조달청 제3자단가계약 실단가** — Tibero 7 Enterprise 1Core **15,301,000원**, TAC 1Core **8,140,000원**.[^tbg2b]

같은 EE 1Core가 정가 5,085만 원 vs 조달 계약가 1,530만 원으로 **3배 이상 벌어진다.** 어느 쪽도 틀린 값이 아니라 성격이 다른 것이고(정가 vs 계약단가), 혁신장터 표기가는 원문에 _"조달청장이 조사하여 통보한 가격이 아님"_ 이라는 단서까지 붙어 있다. 이런 숫자는 **출처를 밝히지 않고 인용하는 순간 틀린 글이 된다.**

참고로 Tibero 7은 2022-11-07 TTA GS인증 1등급을 받았고(인증번호 22-0502), 2007년 v3.0부터의 인증 이력이 TTA 데이터베이스에 남아 있다.[^tbtta] 공공 조달에서 이 인증이 갖는 무게 때문에 국내 도입 논의에서 자주 등장한다.

**다만 공공·금융 레퍼런스는 이 글에서 다루지 않는다.** 벤더 케이스스터디는 많은데 발주기관 1차 문서로 교차 확인되는 건 거의 없다. 그리고 그건 도입이 없다는 뜻이 아니라 — 「행정기관 및 공공기관 정보시스템 구축·운영 지침」(행정안전부고시 제2025-1호) 제17조에 따라 **상세 전산자원 구성이 공개 공고에서 제외되기 때문**이다.[^tbcompa] 검증이 안 되는 것과 제도적으로 공개되지 않는 것은 구분해야 한다.

---

## 4. SQL 개발자가 실제로 데는 지점

여기부터가 이 글의 본론이다. 위 내용을 다 몰라도 되지만, 아래는 모르면 반드시 한 번은 당한다.

### ① Oracle에서 빈 문자열은 NULL이다

가장 악명 높은 차이다.[^oranull]

> "Oracle Database treats a character value with a length of zero as null."

그런데 Oracle 스스로 이렇게 덧붙인다 — 이 문장을 같이 알아 두는 게 중요하다.

> "However, this may not continue to be true in future releases, and Oracle recommends that you do not treat empty strings the same as nulls."

MySQL과 MariaDB에서는 `''` 와 NULL이 **엄연히 다른 값**이다.[^mynull][^marnull]

> "These are in fact values, whereas NULL means 'not having a value.'"

무엇이 깨지는가. Oracle에서 `WHERE name = ''` 는 **항상 아무 행도 반환하지 않는다.** NULL과의 비교는 UNKNOWN이 되고, WHERE 절의 UNKNOWN은 FALSE처럼 동작하기 때문이다.[^oranull] 반대로 MySQL에서 `WHERE name IS NULL` 로 걸러지던 빈 문자열 행이 Oracle로 옮기면 걸러진다. **조건절의 의미가 통째로 뒤집힌다.**

Tibero는 이 점에서 Oracle과 같다.[^tbnull]

> "문자 타입 컬럼에 빈 문자열(`''`)을 저장하면 NULL로 처리합니다."

### ② `||` 는 DB마다 다른 연산자다

Oracle과 Tibero에서 `||` 는 문자열 연결이다. **MySQL에서는 기본적으로 논리 OR이다.**[^mylogop]

> "OR, || — Logical OR"
> "If the PIPES_AS_CONCAT SQL mode is enabled, `||` signifies the SQL-standard string concatenation operator"

`SELECT a || b` 가 에러도 없이 `0` 이나 `1` 을 뱉는다. 조용히 틀리는 종류의 버그라 더 나쁘다.

**그리고 NULL 처리가 정반대다.** Oracle의 `||` 는 NULL을 무시한다 — `'A' || NULL` 은 `'A'` 다.[^oraconcat]

> "concatenating a zero-length character string with another operand always results in the other operand, so null can result only from the concatenation of two null strings."

반면 MySQL의 `CONCAT()` 은 **인자 하나만 NULL이어도 전체가 NULL**이다.[^myconcat]

> "CONCAT() returns NULL if any argument is NULL."

주소를 `city || ' ' || street` 로 조립하는 코드를 그대로 `CONCAT(city, ' ', street)` 로 옮기면, 한 컬럼이 NULL인 순간 **주소 전체가 NULL로 사라진다.** Oracle에서는 나머지가 그대로 나왔던 코드다.

### ③ NULL 정렬 순서가 반대다

Oracle은 오름차순에서 NULL이 **마지막**이다.[^orasel]

> "The database sorts nulls following all others in ascending order and preceding all others in descending order."

MySQL/MariaDB는 NULL을 최소값으로 보므로 오름차순에서 **먼저** 온다.[^mynull][^marnull]

게다가 MySQL/MariaDB 공식 매뉴얼의 문 목록에는 `NULLS FIRST` / `NULLS LAST` 구문이 존재하지 않는다. `ORDER BY ISNULL(col), col` 같은 우회가 필요하다. **페이지네이션 결과 순서가 DB만 바꿨는데 달라지는** 전형적인 원인이다.

### ④ `ROWNUM` 은 정렬보다 먼저 매겨진다

Oracle의 `ROWNUM` 은 행이 **선택되는 시점**에 매겨진다. 그래서 매뉴얼이 이렇게 적어 뒀다.[^orarownum]

> "Conditions testing for ROWNUM values greater than a positive integer are always false. For example, this query returns no rows: `SELECT * FROM employees WHERE ROWNUM > 1;`"

`WHERE ROWNUM BETWEEN 11 AND 20` 으로 페이징을 짜면 **영원히 빈 결과**가 나온다. 첫 행이 항상 ROWNUM 1을 받고 조건에 걸려 탈락하며, 그 다음 행이 다시 1을 받기 때문이다.

정렬과의 순서도 함정이다.

> "If an ORDER BY clause follows ROWNUM in the same query, then the rows will be reordered by the ORDER BY clause."

`WHERE ROWNUM <= 10 ORDER BY score DESC` 는 **상위 10명이 아니라, 아무 10명을 뽑아 정렬한 것**이다. 서브쿼리에서 정렬하고 바깥에서 ROWNUM을 걸어야 한다.

12c부터는 Oracle 스스로 표준 구문을 권한다.[^orarownum]

> "The `row_limiting_clause` of the SELECT statement provides superior support for limiting the number of rows returned by a query."

`ORDER BY score DESC FETCH FIRST 10 ROWS ONLY` 를 쓰면 된다. MySQL/MariaDB의 `LIMIT` 은 **offset이 0-based** 라는 것만 기억하면 된다 — `LIMIT 5,10` 은 6~15번째 행이다.[^mysel]

### ⑤ Oracle `DATE` 에는 시분초가 있다

Oracle의 `DATE` 는 **연·월·일·시·분·초를 모두 저장한다.**[^oratype]

MySQL의 `DATE` 는 **날짜만**이고, 시분초를 담는 건 `DATETIME` 이다.[^mydatetime]

즉 Oracle `DATE` → MySQL `DATE` 로 그대로 매핑하면 **시분초가 조용히 잘려 나간다.** 대응은 `DATETIME` 이다. 그리고 Oracle에서 `WHERE order_date = TO_DATE('2026-08-12','YYYY-MM-DD')` 가 하루치를 못 잡는 것도 같은 이유다(00:00:00만 매칭된다).

현재 시각 함수도 이름이 함정이다. MySQL의 `SYSDATE()` 는 Oracle의 `SYSDATE` 와 의미가 다르다.[^mydatefn]

> "(Within a stored function or trigger, NOW() returns the time at which the function or triggering statement began to execute.) This differs from the behavior for SYSDATE(), which returns the exact time at which it executes."

매뉴얼의 예제가 명확하다 — `SELECT NOW(), SLEEP(2), NOW();` 는 두 값이 같고, `SYSDATE()` 로 하면 2초 차이가 난다. **Oracle `SYSDATE` 에 대응하는 건 MySQL `NOW()`** 다. `SYSDATE()` 를 쓰면 한 문장 안에서 시각이 흔들려 데이터 정합성이 깨진다.

### ⑥ 식별자 대소문자 — 맥에서 되고 리눅스에서 깨진다

Oracle은 따옴표 없는 식별자를 **대문자로 해석**한다.[^oraident]

> "Nonquoted identifiers are not case sensitive. Oracle interprets them as uppercase. Quoted identifiers are case sensitive."

MySQL은 다르다. **테이블명 대소문자 민감도가 OS에 따라 달라진다.**[^myident]

> "On Unix, the default value of lower_case_table_names is 0. On Windows, the default value is 1. On macOS, the default value is 2."

개발자 맥(2: 비민감)에서 `SELECT * FROM Users` 가 잘 돌다가, 운영 리눅스(0: 민감)에 올리면 `users` 테이블을 못 찾는다. **개발에서 절대 재현되지 않는 운영 전용 버그**의 고전적 원인이다.

더 나쁜 건 이거다.

> "lower_case_table_names can only be configured when initializing the server. Changing the lower_case_table_names setting after the server is initialized is prohibited."

**서버 초기화 이후에는 못 바꾼다.** 나중에 고치려면 재초기화 + 재적재다. 처음 세팅할 때 정하는 수밖에 없다.

### ⑦ MERGE가 없는 곳이 있다

Oracle과 Tibero는 표준 `MERGE` 를 지원한다.[^oramerge][^tbmerge] 반면 **MySQL 8.4 레퍼런스 매뉴얼의 DML 문 목록에는 `MERGE` 가 존재하지 않는다.**[^mydml] 대신 `INSERT ... ON DUPLICATE KEY UPDATE` 를 쓴다.

대체할 때 걸리는 게 두 개 있다.

첫째, **유니크 인덱스가 여러 개면 동작이 모호하다.**[^myodku]

> "In general, you should try to avoid using an ON DUPLICATE KEY UPDATE clause on tables with multiple unique indexes."

둘째, **affected rows 반환값이 다르다.**

> "the affected-rows value per row is 1 if the row is inserted as a new row, 2 if an existing row is updated, and 0 if an existing row is set to its current values."

**업데이트되면 1이 아니라 2를 반환한다.** JDBC `executeUpdate()` 결과로 "1건 처리됐는지" 검증하는 코드는 여기서 조용히 틀린다.

`REPLACE` 를 MERGE 대신 쓰는 건 더 위험하다.[^myreplace]

> "REPLACE works exactly like INSERT, except that if an old row in the table has the same value … the old row is **deleted** before the new row is inserted."

**DELETE + INSERT 다.** FK가 걸려 있으면 CASCADE가 돌고, AUTO_INCREMENT가 새로 매겨지며, 명시하지 않은 컬럼은 기본값으로 초기화된다. UPDATE의 대체재가 아니다.

### ⑧ 시퀀스 vs IDENTITY vs AUTO_INCREMENT

Oracle 12c의 IDENTITY 컬럼은 **기본이 `ALWAYS`** 다.[^oracreate]

> "ALWAYS — If you specify ALWAYS, then Oracle Database always uses the sequence generator to assign a value to the column. If you attempt to explicitly assign a value to the column using INSERT or UPDATE, then an error will be returned. **This is the default.**"

애플리케이션이 PK를 직접 넣으면 에러가 난다. 데이터 마이그레이션할 때 원본 ID를 보존하려면 `BY DEFAULT` 여야 한다.

**MariaDB에는 `CREATE SEQUENCE` 가 있고 MySQL 매뉴얼의 DDL 문 목록에는 없다.**[^marseq][^myddl] Oracle에서 시퀀스를 쓰던 코드를 옮길 때 MariaDB 쪽이 훨씬 수월하다. 단 MariaDB 시퀀스는 내부적으로 테이블처럼 동작해서 `LOCK TABLES` 의 영향을 받는다 — Oracle과 다른 점이라고 문서가 직접 밝혀 뒀다.[^marseq]

### ⑨ Tibero — "Oracle 호환"이 끝나는 지점

Tibero의 강점은 Oracle 호환이고 실제로 상당 부분 그렇다. 중요한 건 **어디까지인지를 벤더가 문서에 적어 뒀다**는 사실이다. 공식 기술 안내서의 Migration 장에서 발췌한다.[^tbmig]

**아예 없는 것:**

> "Cluster Object — Consider converting to a regular table format, as Tibero does not support cluster objects."
> "BitMap Index — Consider converting to a regular index, as this is not supported in Tibero."
> "Since Tibero does not support object types, bypass this by declaring the type within a package."
> "SEGMENT SPACE MANAGEMENT MANUAL — Since Tibero only supports the AUTO setting"

**비트맵 인덱스 부재는 성능 설계에 직접 영향을 준다.** 카디널리티 낮은 컬럼에 비트맵 인덱스를 깔던 DW성 스키마는 설계를 다시 해야 한다.

**SQL이 그냥 안 돌아가는 케이스도 명시돼 있다:**

> "if you execute a join or similar operation without assigning an alias to the table or subquery clause in the from clause, a syntax error will occur if duplicate columns exist."
> "A syntax error will occur in PSM (PL/SQL) if variables with the same name are declared within the same scope."

Oracle에서 통과하던 PL/SQL이 Tibero에서 문법 에러가 난다는 뜻이다.

그리고 개인적으로 가장 중요하다고 보는 문장:

> "In Oracle, results may be displayed in sorted form even without an ORDER BY clause, whereas in Tibero, the results may not."

**`ORDER BY` 없이 정렬을 기대하던 코드가 여기서 터진다.** 원래부터 보장되지 않던 동작에 의존한 것이고 Oracle이 우연히 받아 주고 있었을 뿐인데, 마이그레이션 때 "Tibero 버그"로 오해되기 딱 좋다. 표준을 지키지 않은 쪽이 청구서를 받는 전형적인 사례다. Tibero 기술지원 문서(TMITI031)도 Oracle→Tibero 전환 시 질의를 반드시 수정해야 하는 상황으로 ① 별칭/중복 컬럼명 ② `UNION ALL` 타입 불일치 ③ PSM 내 중복 변수명 ④ **암묵적 정렬 미보장** ⑤ PSM 컴파일 시점의 더 엄격한 객체·컬럼 존재 검사, 이 다섯 가지를 든다.[^tbconv]

타입 매핑도 그대로 옮겨지지 않는다 — `BFILE` 미지원(BLOB로 우회), `SYS.XMLTYPE` → `XMLTYPE`, `BINARY_FLOAT`/`BINARY_DOUBLE` 은 내부적으로 `NUMBER` 로 생성된다.[^tbtype] 반대로 `VARCHAR` 최대 길이는 **65,532 byte** 로 Oracle(기본 4,000 byte)보다 훨씬 넉넉하다.[^tbtypes]

마지막으로 힌트에 대해 한 가지. Tibero는 `FULL`, `INDEX`, `LEADING`, `USE_NL`, `USE_HASH` 등 **Oracle과 같은 이름의 힌트를 같은 문법으로** 제공한다.[^tbhint] 다만 공식 문서가 "Oracle 힌트와 1:1 호환"을 보증하지는 않는다 — 확인되는 건 이름이 같다는 사실까지다. 튜닝 힌트를 그대로 옮긴 뒤에는 실행계획을 다시 봐야 한다.

---

## 5. 정리

네 줄로 줄이면 이렇다.

1. **버전 상식부터 갱신하라.** MySQL 8.0은 이미 보안 패치를 못 받고(2026-04 EOL), Oracle 23ai는 26ai로 대체됐으며, MariaDB 10.6은 지난달, Tibero 6는 작년에 끝났다.
2. **성능 차이를 논하려면 격리수준부터 봐라.** Oracle은 READ COMMITTED에 REPEATABLE READ가 아예 없고, MySQL/MariaDB는 REPEATABLE READ + gap lock이다. 같은 코드가 다르게 동작한다.
3. **"오픈소스니까 공짜"의 경계선을 정확히 알아라.** MySQL은 배포·임베딩이 트리거고 HA는 무료다. MariaDB는 서버가 GPLv2지만 MaxScale은 프로덕션 3대부터 유료다. Oracle은 **AWR을 열어보는 것부터** 유료이고, Tibero는 클러스터(TAC)가 EE 위의 별도 유상 옵션이다. **HA를 무료로 주는 건 사실상 MySQL/MariaDB뿐이다.**
4. **가장 자주 데는 건 NULL이다.** Oracle의 빈 문자열=NULL, `||` 의 NULL 무시 vs `CONCAT` 의 NULL 전파, NULL 정렬 순서 — 세 개 모두 에러 없이 조용히 틀린다.

마지막으로 다시 강조하면, **이 글에 성능 우열 결론은 없다.** 중립 제3자 벤치마크가 공개돼 있지 않고, 벤더 자체 수치는 재현 조건이 공개되지 않아 인용하지 않았다. 성능은 워크로드·스키마·하드웨어에 종속적이고, 그걸 아는 유일한 방법은 **본인 워크로드로 직접 재보는 것**이다. 다만 그 결과를 공개하려 한다면 위에 인용한 약관을 먼저 읽어 보길 권한다.

---

## References

[^otn]: Oracle Technology Network License Agreement (OTN Developer License Terms), "License Rights and Restrictions". <https://www.oracle.com/downloads/licenses/standard-license.html> — 금지 행위 목록에 "disclose results of any Program benchmark tests without Oracle's prior consent" 명시.

[^ofl]: Oracle Free Use Terms and Conditions. <https://www.oracle.com/downloads/licenses/oracle-free-license.html> — 해당 문서의 제한 목록에는 벤치마크 공표 금지 조항이 포함되어 있지 않음(2026-08-12 확인).

[^ora26]: Oracle, "Oracle Announces Oracle AI Database 26ai", Oracle Database Blog. <https://blogs.oracle.com/database/oracle-announces-oracle-ai-database-26ai>

[^oralsp]: Oracle, _Lifetime Support Policy: Oracle Technology Products_ (Effective Date: August 7, 2026), "Oracle Database Releases" 및 "Oracle MySQL Releases" 표, Sustaining Support 정의. <https://www.oracle.com/us/assets/lifetime-support-technology-069183.pdf>

[^ora26ga]: Oracle, "GA of Oracle AI Database 26ai for Linux x86-64 On-Premises Platforms". <https://blogs.oracle.com/database/ga-of-oracle-ai-database-26ai-for-linux-x86-64-on-premises-platforms>

[^myeol]: Oracle, "MySQL Product Support End-of-Life Announcements". <https://www.mysql.com/support/eol-notice.html> — MySQL 8.0 의 2026-04-21 Sustaining Support 전환, Enterprise Monitor 의 2025-01-01 EOL.

[^mycal]: Mike Frank (Oracle, Product Management Director), "A More Predictable MySQL Release Model: Calendar Versions, LTS, and Innovation", 2026-06-16. <https://blogs.oracle.com/mysql/a-more-predictable-mysql-release-model-calendar-versions-lts-and-innovation>

[^mylic]: mysql/mysql-server, LICENSE (trunk). <https://github.com/mysql/mysql-server/blob/trunk/LICENSE> — 헤더에 `MySQL 26.7.0 Community` 표기(2026-08-12 확인).

[^myrel]: _MySQL 8.4 Reference Manual_, 1.3 "MySQL Releases: Innovation and LTS". <https://dev.mysql.com/doc/refman/8.4/en/mysql-releases.html>

[^marlife]: MariaDB Foundation, "About MariaDB Server" — Maintenance policy 및 long-term release maintenance periods 표. <https://mariadb.org/about/#maintenance-policy> ※ 12.3 의 GA/EOL 표기는 재단 블로그 글과 1~2주 차이가 있어, 본문은 라이프사이클 표 기준을 따랐다.

[^mar106]: MariaDB Foundation, "MariaDB Server 10.6 reaches End of Life on July 6th". <https://mariadb.org/mariadb-server-10-6-reaches-end-of-life-on-july-6th/>

[^tbdoc]: Tmax Tibero, _Tibero SQL 참조 안내서_ (7.2.6, 2026-07-31 발행). <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-sql-reference-guide>

[^tbrel]: Tmax Tibero, _Tibero 릴리즈 노트_ (7.2.6, 발행일 2026-07-31) — 릴리즈 이력 표. <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero.md>

[^tbeol]: 티맥스티베로, "EOL/EOS 안내" — Tibero 6 EOL 2024-03-31 / EOS 2025-03-31 / Extended Support 2028-03-31, "제품의 판매 종료일은 통상 차기 버전 출시 후 2년입니다", Extended Support 계약 시 유지보수 비용 15% 추가. <https://technet.tmax.co.kr/ko/front/support/notice/viewNotice.do?board_seq=CUST-20221102-000001>

[^tbinst]: Tmax Tibero, _Tibero 7 Installation Guide_ (v7.2.2) — "Full Purchase Version Licensed by the number of CPUs and features. Evaluation Version A license that restricts the trial period and the number of users." <https://tmaxtibero.blog/wp-content/uploads/2025/01/Tibero_7_Installation-Guide_v7.2.2.pdf>

[^tblic]: Tmax Tibero, _Tibero 라이선스 안내서_ 7.2.6, "에디션 정책 및 라이선싱". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-license-guide/tibero-edition-policy-and-licensing.md>

[^tbha]: Tmax Tibero, _Tibero 라이선스 안내서_ 7.2.6, "HA 옵션 구성 지침". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-license-guide/tibero-ha-option-configuration-guidelines.md>

[^tbperf]: Tmax Tibero, _Tibero 라이선스 안내서_ 7.2.6, "성능 옵션 구성 지침". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-license-guide/tibero-performance-option-configuration-guidelines.md>

[^tbed]: Tmax Tibero, _Tibero 라이선스 안내서_ 7.2.6 — 에디션별 기능 제공 표. <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-license-guide/tibero.md>

[^tbarch]: Tmax Tibero, _Tibero 관리자 안내서_ 7.2.6, "소개 — Tibero 프로세스/스레드 구조". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-administrator-guide/introduction.md>

[^tbprice]: 티맥스티베로, "List Price" (2025-07-01 시행). <https://tmaxtibero.blog/list-price-2025-july/> — 벤더가 공표한 정가이며 실제 계약가와 다를 수 있다.

[^tbg2b]: 조달청 디지털서비스몰 계약상품정보(공공데이터포털 원자료) <https://www.data.go.kr/data/15131726/fileData.do> — 계약 002461246, 물품식별번호 24830440(Tibero 7 Enterprise 1Core) 및 24830439(Tibero Active Cluster 1Core). 혁신장터 상세 <https://ppi.g2b.go.kr:8914/sm/dm/sch/searchGoodsDetail.do?invGdsIdntNo=00035792> — 표기 가격은 "거래희망가격(VAT 포함)"이며 "조달청장이 조사하여 통보한 가격이 아님"이라는 단서가 붙는다.

[^tbtta]: TTA 정보통신기술협회, GS인증 제품 목록 — 티베로 7, 인증번호 22-0502, 인증일자 2022-11-07, 1등급. <https://cs.tta.or.kr/tta/notification/ttaCertProductListR.do>

[^tbcompa]: 과학기술사업화진흥원, 「2026년 통합업무관리시스템 유지보수 용역 제안요청서」(나라장터 입찰공고 R26BK01423182, 2026.3) — 상용SW 현황 "DBMS Tibero 7.2.3", 및 「행정기관 및 공공기관 정보시스템 구축·운영 지침」(행정안전부고시 제2025-1호) 제17조에 따른 전산자원 상세 비공개 근거. <https://www.g2b.go.kr/pn/pnp/pnpe/UntyAtchFile/downloadFile.do?bidPbancNo=R26BK01423182&bidPbancOrd=000&fileSeq=4&prcmBsneSeCd=03>

[^tbconv]: Tibero GTS, "Application Conversion When Migrating from Oracle to Tibero" (문서번호 TMITI031). <https://support.tibero.com/hc/en-us/articles/14623836705423-Application-Conversion-When-Migrating-from-Oracle-to-Tibero>

[^oracncpt]: _Oracle Database Concepts, 19c/21c_, "Data Concurrency and Consistency". <https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html>

[^myiso]: _MySQL 8.4 Reference Manual_, 17.7.2.1 "Transaction Isolation Levels". <https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html>

[^marset]: MariaDB Documentation, "SET TRANSACTION". <https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/set-commands/set-transaction>

[^marsnap]: MariaDB Documentation, "InnoDB System Variables" — `innodb_snapshot_isolation` (Default: `ON` >= MariaDB 11.6.2). <https://mariadb.com/docs/server/server-usage/storage-engines/innodb/innodb-system-variables>

[^mareits]: MariaDB Documentation, "Engine-Independent Table Statistics". <https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/query-optimizations/statistics-for-optimizing-queries/engine-independent-table-statistics>

[^marhist]: MariaDB Documentation, "Histogram-Based Statistics". <https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/query-optimizations/statistics-for-optimizing-queries/histogram-based-statistics>

[^marhint]: MariaDB, "What is MariaDB 12.0" 릴리스 노트 (optimizer hints, MDEV-35504 / MDEV-34870 / MDEV-34860). <https://mariadb.com/docs/release-notes/community-server/old-releases/12.0/what-is-mariadb-120>

[^marreadme]: MariaDB/server, README.md — pluggable storage engines 및 GPLv2 라이선스 명시. <https://github.com/MariaDB/server/blob/main/README.md>

[^marcs]: MariaDB Foundation, "ColumnStore is now part of MariaDB Server". <https://mariadb.org/columnstore-native/>

[^marmatrix]: MariaDB Documentation, "MySQL to MariaDB Compatibility Matrix". <https://mariadb.com/docs/server/server-management/install-and-upgrade-mariadb/migrating-to-mariadb/moving-from-mysql/mysql-to-mariadb-compatibility-matrix>

[^marpar]: MariaDB Documentation, "Parallel Replication". <https://mariadb.com/docs/server/ha-and-performance/standard-replication/parallel-replication>

[^orapl]: Oracle, _Oracle Technology Global Price List_ (August 3, 2026). <https://www.oracle.com/assets/technology-price-list-070617.pdf> — 가격은 "Prices in USA (Dollar)" 기준 정가이며, 실제 계약가는 다를 수 있다.

[^oradblic]: Oracle, _Oracle Database 19c Licensing Information User Manual_ (E94254-69). <https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html> — 에디션별 feature availability 표, Diagnostics Pack / Tuning Pack 구성 및 접근 경로 제한.

[^oradblic26]: Oracle, _Oracle AI Database Licensing Information User Manual_. <https://docs.oracle.com/en/database/oracle/oracle-database/23/dblic/Licensing-Information.html> — Free 에디션의 "Included option" 표기.

[^orafree]: Oracle, "Oracle AI Database Free". <https://www.oracle.com/database/free/>

[^myoem]: Oracle, "MySQL Commercial License for OEMs, ISVs and VARs". <https://www.mysql.com/about/legal/licensing/oem/>

[^mycomm]: Oracle, "MySQL Community Edition". <https://www.mysql.com/products/community/>

[^mytp]: _MySQL 8.4 Reference Manual_, 7.6.3 "MySQL Enterprise Thread Pool". <https://dev.mysql.com/doc/refman/8.4/en/thread-pool.html> ※ 인용된 성능 서술은 Oracle 자사 문서의 정성적 주장이며 재현 가능한 중립 벤치마크가 첨부되어 있지 않다.

[^mybk]: _MySQL 8.4 Reference Manual_, "MySQL Enterprise Backup Overview". <https://dev.mysql.com/doc/refman/8.4/en/mysql-enterprise-backup.html>

[^myaudit]: _MySQL 8.4 Reference Manual_, "MySQL Enterprise Audit". <https://dev.mysql.com/doc/refman/8.4/en/audit-log.html>

[^myfw]: _MySQL 8.4 Reference Manual_, "MySQL Enterprise Firewall". <https://dev.mysql.com/doc/refman/8.4/en/firewall.html>

[^mytde]: _MySQL 8.4 Reference Manual_, 17.13 "InnoDB Data-at-Rest Encryption" 및 8.4.4 "The MySQL Keyring". <https://dev.mysql.com/doc/refman/8.4/en/innodb-data-encryption.html>

[^marlicense]: MariaDB/server, README.md — "licensed under version 2 of the GNU General Public License (GPLv2), without the 'any later version' clause." <https://github.com/MariaDB/server/blob/main/README.md>

[^marabout]: MariaDB Foundation, "About". <https://mariadb.org/about/>

[^mardiff]: MariaDB, "Differences in MariaDB Enterprise Server 11.8". <https://mariadb.com/docs/release-notes/enterprise-server/about/mariadb-enterprise-server-differences/differences-in-mariadb-enterprise-server-11.8>

[^marmaxscale]: MariaDB MaxScale, Business Source License 1.1 (24.02). <https://github.com/mariadb-corporation/MaxScale/blob/24.02/licenses/LICENSE2402.TXT> ※ 24.02 이후 버전의 라이선스는 공식 문서로 확인하지 못했다.

[^marbsl]: MariaDB, "BSL FAQ". <https://mariadb.com/bsl-faq-mariadb/>

[^oranull]: _Oracle Database SQL Language Reference, 21c_, "Nulls". <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/Nulls.html>

[^mynull]: _MySQL 8.4 Reference Manual_, 3.3.4.6 "Working with NULL Values". <https://dev.mysql.com/doc/refman/8.4/en/working-with-null.html>

[^marnull]: MariaDB Documentation, "NULL Values". <https://mariadb.com/docs/server/reference/data-types/null-values>

[^tbnull]: Tmax Tibero, _Tibero SQL 참조 안내서_ 7.2.6, "SQL 문장의 구성요소 > NULL". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-sql-reference-guide/sql-elements/null>

[^mylogop]: _MySQL 8.4 Reference Manual_, 14.4.3 "Logical Operators". <https://dev.mysql.com/doc/refman/8.4/en/logical-operators.html>

[^oraconcat]: _Oracle Database SQL Language Reference, 21c_, "Concatenation Operator". <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/Concatenation-Operator.html>

[^myconcat]: _MySQL 8.4 Reference Manual_, 14.8 "String Functions and Operators" (CONCAT). <https://dev.mysql.com/doc/refman/8.4/en/string-functions.html>

[^orasel]: _Oracle Database SQL Language Reference, 21c_, "SELECT" — order_by_clause / row_limiting_clause. <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/SELECT.html>

[^orarownum]: _Oracle Database SQL Language Reference, 21c_, "ROWNUM Pseudocolumn". <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/ROWNUM-Pseudocolumn.html>

[^mysel]: _MySQL 8.4 Reference Manual_, 15.2.13 "SELECT Statement" (LIMIT, DUAL). <https://dev.mysql.com/doc/refman/8.4/en/select.html>

[^oratype]: _Oracle Database SQL Language Reference, 21c_, "Data Types" (DATE). <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/Data-Types.html>

[^mydatetime]: _MySQL 8.4 Reference Manual_, 13.2.2 "The DATE, DATETIME, and TIMESTAMP Types". <https://dev.mysql.com/doc/refman/8.4/en/datetime.html>

[^mydatefn]: _MySQL 8.4 Reference Manual_, 14.7 "Date and Time Functions" (NOW, SYSDATE). <https://dev.mysql.com/doc/refman/8.4/en/date-and-time-functions.html>

[^oraident]: _Oracle Database SQL Language Reference, 21c_, "Database Object Names and Qualifiers". <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/Database-Object-Names-and-Qualifiers.html>

[^myident]: _MySQL 8.4 Reference Manual_, 11.2.3 "Identifier Case Sensitivity". <https://dev.mysql.com/doc/refman/8.4/en/identifier-case-sensitivity.html>

[^oramerge]: _Oracle Database SQL Language Reference, 21c_, "MERGE". <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/MERGE.html>

[^tbmerge]: Tmax Tibero, _Tibero SQL 참조 안내서_ 7.2.6, "MERGE". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-sql-reference-guide/data-manipulation-language/merge>

[^mydml]: _MySQL 8.4 Reference Manual_, 15.2 "Data Manipulation Statements" 목차. <https://dev.mysql.com/doc/refman/8.4/en/sql-data-manipulation-statements.html> — 문 목록에 MERGE 가 존재하지 않음(부재 확인).

[^myodku]: _MySQL 8.4 Reference Manual_, 15.2.7.2 "INSERT ... ON DUPLICATE KEY UPDATE Statement". <https://dev.mysql.com/doc/refman/8.4/en/insert-on-duplicate.html>

[^myreplace]: _MySQL 8.4 Reference Manual_, 15.2.12 "REPLACE Statement". <https://dev.mysql.com/doc/refman/8.4/en/replace.html>

[^oracreate]: _Oracle Database SQL Language Reference, 21c_, "CREATE TABLE" — identity_clause. <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/CREATE-TABLE.html>

[^marseq]: MariaDB Documentation, "Sequence Overview". <https://mariadb.com/docs/server/reference/sql-structure/sequences/sequence-overview>

[^myddl]: _MySQL 8.4 Reference Manual_, 15.1 "Data Definition Statements" 목차. <https://dev.mysql.com/doc/refman/8.4/en/sql-data-definition-statements.html> — 문 목록에 CREATE SEQUENCE 가 존재하지 않음(부재 확인).

[^tbmig]: Tmax Tibero, _Tibero Technical Guides — Migration_. <https://docs.tibero.com/en_tibero-technical-guides/getting-started/migration/migration>

[^tbtype]: Tmax Tibero, _Tibero Technical Guides — Migration > Data types_. <https://docs.tibero.com/en_tibero-technical-guides/getting-started/migration/data-types>

[^tbtypes]: Tmax Tibero, _Tibero SQL 참조 안내서_ 7.2.6, "SQL 문장의 구성요소 — 데이터 타입" — "문자열은 최대 65,532 byte나 65,532자까지 선언할 수 있습니다." <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-sql-reference-guide/sql-elements/undefined.md>

[^tbhint]: Tmax Tibero, _Tibero SQL 참조 안내서_ 7.2.6, "SQL 문장의 구성요소 — 힌트". <https://docs.tibero.com/tibero-manuals/7.2.6.manuals/tibero-sql-reference-guide/sql-elements/undefined-5.md>
