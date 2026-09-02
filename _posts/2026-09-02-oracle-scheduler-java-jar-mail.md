---
layout: post
title: "자바 jar 를 오라클 스케줄러로 돌려 메일 보내기 — 조용히 틀리는 지점들"
date: 2026-09-02 22:15:00 +0900
categories: [backend, database]
tags: [oracle, dbms_scheduler, java, jar, mail, batch]
---

"매일 새벽에 집계해서 담당자한테 메일 보내라" 는 요건은 오래된 만큼 길도 여러 갈래다. 그중 한국의 오라클 기반 시스템에서 유난히 자주 보이는 조합이 **실행 가능 jar + `DBMS_SCHEDULER`** 다.

이 조합은 만드는 건 반나절이면 되는데, 안 되는 이유를 찾는 데 이틀이 걸린다. 실패하는 지점들이 대부분 **에러를 안 내고 조용히 틀리기** 때문이다. 이 글은 그 지점들을 순서대로 짚는다.

> 미리 밝혀 둔다. 아래 코드는 공식 문서를 근거로 만든 최소 예제이고, 내 개인 리포에서 실제로 돌고 있는 코드를 옮긴 것이 아니다(내 리포들은 PostgreSQL 을 쓴다). 문서로 확인되는 것만 단정하고, 나머지는 그렇게 표시했다.

---

## 1. 갈림길 — 메일을 DB 안에서 보낼 것인가, 밖에서 보낼 것인가

jar 를 쓰기로 하기 전에, 오라클은 이미 자기 안에서 메일을 보낼 수 있다. `UTL_SMTP` 와 그걸 감싼 `UTL_MAIL` 이다. 한 줄이면 끝난다.

```sql
UTL_MAIL.SEND(
  sender     => 'batch@example.com',
  recipients => 'ops@example.com',
  subject    => 'Daily settlement summary',
  message    => '...');
```

그런데 이 길에는 문서에 명시된 조건이 셋 있다.

**(1) 기본 설치가 아니다.** `UTL_MAIL` 은 기본으로 설치되지 않는다. SYS 로 스크립트 두 개를 돌려야 한다.[^utlmail]

```sql
SQL> @$ORACLE_HOME/rdbms/admin/utlmail.sql
SQL> @$ORACLE_HOME/rdbms/admin/prvtmail.plb
```

**(2) `SMTP_OUT_SERVER` 초기화 파라미터를 정의해야 한다.**[^utlmail] DB 파라미터를 건드리는 일이라 운영 DBA 의 승인 대상이 된다.

**(3) 네트워크 ACL 이 필요하다.** 11g 이후 DB 에서 바깥으로 나가는 TCP 는 전부 ACL 통제 대상이다. `UTL_TCP` · `UTL_HTTP` · `UTL_SMTP` · `UTL_MAIL` 로 외부 호스트에 붙으려면 그 사용자에게 `connect` 권한이 있어야 한다.[^acl]

```sql
BEGIN
  DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
    host => 'smtp.example.com',
    lower_port => 25, upper_port => 25,
    ace  => xs$ace_type(privilege_list => xs$name_list('connect'),
                        principal_name => 'BATCH_USER',
                        principal_type => xs_acl.ptype_db));
END;
```

여기까지는 그냥 절차다. 진짜 갈림길은 네 번째다.

**(4) 문서가 못 박은 문자 범위.** `UTL_MAIL` 의 "Rules and Limits" 절은 이렇게 적혀 있다.

> Use `UTL_MAIL` only within the context of the ASCII (American Standard Code for Information Interchange) and EBCDIC (Extended Binary-Coded Decimal Interchange Code) codes.[^utlmail]

한글 제목·본문이 들어가는 순간 이건 **문서가 보장하지 않는 영역**이다. `UTL_SMTP` 를 직접 써서 MIME 헤더(`Content-Type: text/plain; charset=UTF-8`, `Content-Transfer-Encoding: base64`)와 [RFC 2047](https://www.rfc-editor.org/rfc/rfc2047) 제목 인코딩을 손으로 조립하면 되기는 한다. 다만 그 순간부터 **PL/SQL 로 메일 클라이언트를 직접 구현하는 일**이 된다. 첨부(엑셀 리포트)까지 들어가면 multipart 경계 문자열까지 직접 만들어야 한다.

**jar 로 나가는 이유가 여기다.** 문자셋·MIME·첨부·인증(STARTTLS, SMTP AUTH)을 이미 구현한 라이브러리가 자바 쪽에 있고, 그걸 쓰면 저걸 전부 안 짜도 된다. 대신 "DB 밖에서 도는 프로세스" 라는 새 문제가 생긴다 — 그 프로세스를 누가, 어떤 계정으로, 언제 띄우고, 실패를 어떻게 아는가.

`DBMS_SCHEDULER` 가 그 자리를 맡는다.

---

## 2. 실행 가능 jar — 만드는 건 쉽고 틀리는 건 조용하다

`java -jar app.jar` 가 되려면 manifest 에 `Main-Class` 가 있어야 한다.[^javacmd] 여기까진 다 안다. 문제는 그 다음 줄이다.

> When you use `-jar`, the specified JAR file is the source of all user classes, and **other class path settings are ignored**.[^javacmd]

즉 이렇게 쓰면 `-cp` 는 **조용히 무시된다.**

```bash
# lib/* 는 반영되지 않는다. 에러도 경고도 없다.
java -cp "lib/*" -jar mailer.jar
```

`CLASSPATH` 환경변수도 마찬가지다. 배치 계정의 `.profile` 에 `CLASSPATH` 를 걸어 두고 "설정했는데 왜 `NoClassDefFoundError` 가 나냐" 로 반나절 쓰는 게 이 지점이다.

`-jar` 를 쓰면서 외부 라이브러리를 쓰는 길은 두 가지다.

**(a) manifest 의 `Class-Path`.** JAR 스펙이 정의하는 속성이고, 값은 **jar 파일 위치를 기준으로 한 상대 URL** 목록이다(공백 구분).[^jarspec]

```
Main-Class: com.example.MailJob
Class-Path: lib/jakarta.mail.jar lib/jakarta.activation.jar
```

여기에도 함정이 하나 더 있다. 스펙의 문장이다.

> Each relative URL is resolved against the code base from which the containing application or library was loaded. **If a URL refers to a resource that cannot be found, then it is ignored.**[^jarspec]

경로를 틀려도 jar 생성 시점엔 아무 일도 없고, 실행 시점에 `NoClassDefFoundError` 로만 드러난다. 그리고 상대 경로의 기준은 **현재 디렉터리가 아니라 jar 의 위치**다. 스케줄러가 어느 디렉터리에서 프로세스를 띄울지는 별개 문제이므로, 이 차이가 "손으로 실행하면 되는데 스케줄러로 돌리면 안 되는" 전형적인 원인이 된다.

**(b) 의존성을 넣어 하나로 만든 jar(fat/uber jar).** 배포 단위가 파일 하나가 되어 위 문제가 통째로 사라진다. 서버에 파일 하나만 올리면 되는 배치라면 이쪽이 사고가 적다.

## 3. 메일 보내는 부분

Jakarta Mail 기준 최소 형태다. `Session` 에 속성을 넣고, `MimeMessage` 를 만들고, `Transport.send` 로 보낸다.[^jakartamail]

```java
public final class MailJob {

    public static void main(String[] args) {
        Properties props = new Properties();
        props.put("mail.smtp.host", System.getenv("SMTP_HOST"));
        props.put("mail.smtp.port", "587");
        props.put("mail.smtp.auth", "true");
        props.put("mail.smtp.starttls.enable", "true");

        try {
            Session session = Session.getInstance(props, new Authenticator() {
                @Override protected PasswordAuthentication getPasswordAuthentication() {
                    return new PasswordAuthentication(
                        System.getenv("SMTP_USER"), System.getenv("SMTP_PASSWORD"));
                }
            });

            MimeMessage msg = new MimeMessage(session);
            msg.setFrom(new InternetAddress("batch@example.com"));
            msg.setRecipients(Message.RecipientType.TO, args[0]);
            msg.setSubject("정산 일일 요약", "UTF-8");   // 한글 제목은 여기서 RFC 2047 로 인코딩된다
            msg.setText("본문", "UTF-8");

            Transport.send(msg);
            System.exit(0);
        } catch (Exception e) {
            e.printStackTrace();   // stdout/stderr 는 버려지지 않는다 — 5절 참고
            System.exit(1);        // 이 줄이 실패를 스케줄러에 알리는 유일한 통로다
        }
    }
}
```

두 가지만 짚는다.

**SMTP 자격증명은 코드나 jar 안에 넣지 않는다.** 위 예제는 환경변수로 받았다. 잡을 도는 OS 계정의 환경에서 읽히도록 두거나(4절의 래퍼 스크립트), 서버의 시크릿 저장소에서 읽는다. jar 는 배포물이고, 배포물에 든 비밀번호는 배포 경로 전체로 퍼진다.

**`Transport.send` 가 예외 없이 끝난 것은 "발송 서버가 접수했다" 는 뜻이지 "받는 사람에게 도착했다" 는 뜻이 아니다.** 이건 추측이 아니라 API 문서에 적힌 말이다.

> Note also that success does not imply that the message was delivered to the ultimate recipient, as failures may occur in later stages of delivery. Once a Transport accepts a message for delivery to a recipient, failures that occur later should be reported to the user via another mechanism, such as returning the undeliverable message.[^transport]

그래서 "잡이 SUCCEEDED 다" 로 메일 도착을 보증할 수는 없다. 보증하고 싶으면 반송(bounce) 메일함을 따로 봐야 한다. 배치 잡의 초록불이 커버하는 범위를 정확히 알고 있어야 하는 부분이다.

---

## 4. `DBMS_SCHEDULER` 로 그 jar 을 돌리기

### 권한 두 개

로컬이든 원격이든 외부 잡을 만들려면 `CREATE JOB` 과 `CREATE EXTERNAL JOB` 이 **둘 다** 필요하다.[^extjob]

```sql
GRANT CREATE JOB, CREATE EXTERNAL JOB TO batch_user;
```

### 자격증명 — 잡이 "누구로" 도는가

외부 잡은 DB 프로세스가 아니라 OS 프로세스를 띄운다. 그래서 어떤 OS 계정으로 돌지를 지정해야 하고, 그게 credential 객체다.[^credential] 문서의 표현대로, 자격증명이 붙은 로컬 외부 잡은 **잡 소유자가 아니라 credential 에 적힌 OS 사용자로** 실행된다.[^extjob]

```sql
BEGIN
  DBMS_CREDENTIAL.CREATE_CREDENTIAL(
    credential_name => 'BATCH_OS_CRED',
    username        => 'oraclebatch',
    password        => '&os_password');   -- 화면·스크립트에 평문으로 남기지 않는다
END;
```

이 한 줄이 파일 권한 문제의 대부분을 설명한다. `oraclebatch` 가 jar 파일과 `lib/` 와 로그 디렉터리에 접근할 수 있어야 한다. 개발자 계정에서 손으로 돌 때 되던 게 스케줄러에서 안 되는 이유는 열에 아홉 여기다.

### 잡 정의 — **셸이 아니라는 점**이 핵심

```sql
BEGIN
  DBMS_SCHEDULER.CREATE_JOB(
    job_name            => 'DAILY_MAIL_JOB',
    job_type            => 'EXECUTABLE',
    job_action          => '/opt/batch/run-mailer.sh',   -- 절대경로
    number_of_arguments => 1,
    repeat_interval     => 'FREQ=DAILY;BYHOUR=6;BYMINUTE=0',
    credential_name     => 'BATCH_OS_CRED',
    enabled             => FALSE);

  DBMS_SCHEDULER.SET_JOB_ARGUMENT_VALUE('DAILY_MAIL_JOB', 1, 'ops@example.com');
  DBMS_SCHEDULER.ENABLE('DAILY_MAIL_JOB');
END;
```

`job_action` 에 `java` 를 바로 쓰지 않고 래퍼 스크립트를 둔 게 의도적이다. `EXECUTABLE` 잡은 **실행 파일 하나를 인자와 함께 직접 띄우는 것**이고, 인자는 `SET_JOB_ARGUMENT_VALUE` 로 하나씩 넣는다.[^extjob] 셸 명령줄이 아니므로 `>` 리다이렉션·`&&`·`$VAR` 전개·와일드카드 같은 셸 문법은 기대할 수 없고, 개발자 셸의 `PATH`·`JAVA_HOME`·`LANG` 도 그대로 상속된다고 가정하면 안 된다. 래퍼가 그 환경을 명시적으로 만든다.

```bash
#!/bin/bash
# /opt/batch/run-mailer.sh
export JAVA_HOME=/usr/lib/jvm/java-21
export LANG=ko_KR.UTF-8          # 한글을 다루는 배치라면 로케일도 명시한다
cd /opt/batch                    # Class-Path 상대경로의 기준을 고정한다
exec "$JAVA_HOME/bin/java" -Dfile.encoding=UTF-8 -jar mailer.jar "$@"
```

`exec` 를 쓴 이유는 자바 프로세스의 종료코드를 스크립트의 종료코드로 그대로 내보내기 위해서다. 이게 다음 절로 이어진다.

> 참고: 스크립트 자체를 DB 안에 넣어 두고 싶다면 `job_type => 'EXTERNAL_SCRIPT'` 라는 선택지도 있다.[^jobtypes] 서버에 파일을 두고 형상관리하느냐, DB 에 넣고 관리하느냐의 취향 문제다.

---

## 5. 실패를 어떻게 아는가 — 이 조합의 진짜 어려운 부분

배치가 안 도는 것보다 나쁜 건 **안 돈 걸 아무도 모르는 것**이다. 메일 배치는 특히 그렇다. 안 오면 "오늘은 보낼 게 없었나 보다" 로 넘어가기 때문이다.

### (1) 종료코드가 유일한 신호다

외부 잡의 성패는 프로세스 종료코드로 판정된다. 그래서 자바 쪽에서 예외를 잡고 로그만 남긴 뒤 정상 종료하면 — 메일이 안 갔는데 잡은 **SUCCEEDED** 로 남는다. 3절 예제에서 `System.exit(1)` 을 명시한 이유다. 그리고 4절에서 `exec` 를 쓴 이유이기도 하다. 래퍼가 자바 종료코드를 삼키면 같은 결과가 된다.

### (2) 잡 이력 뷰

```sql
SELECT job_name, status, error#, actual_start_date, run_duration, additional_info
  FROM user_scheduler_job_run_details
 WHERE job_name = 'DAILY_MAIL_JOB'
 ORDER BY actual_start_date DESC;
```

`USER_SCHEDULER_JOB_RUN_DETAILS`(과 `*_SCHEDULER_JOB_LOG`)가 성패 판정의 근거다.[^extjob] 여기를 아무도 안 보면 잡이 몇 달째 FAILED 여도 조용하다. 이 뷰를 주기적으로 조회해서 실패가 있으면 알리는 **감시 잡**을 따로 두는 게, 배치 자체를 만드는 것만큼 중요하다.

### (3) 표준출력은 버려지지 않는다

이건 알아 두면 디버깅이 확 편해지는 부분이다.

> When an external job runs, the Scheduler automatically retrieves the output from the job and stores it inside the database.[^extjob]

`additional_info` 컬럼에 담긴 external log id 로 로그 파일 이름을 만들어 `DBMS_SCHEDULER.GET_FILE` 로 CLOB 으로 꺼낼 수 있다.[^extjob] 즉 자바가 뱉은 스택트레이스를 **서버에 SSH 로 들어가지 않고 SQL 로** 볼 수 있다. 3절 예제에서 `e.printStackTrace()` 를 남겨 둔 게 이 때문이다.

### (4) 안 도는 것도 실패다

`repeat_interval` 이 도는지, 잡이 아직 `ENABLED` 인지도 봐야 한다. `max_failures` 를 지정해 두면 연속 실패 시 잡이 자동으로 비활성화되는데 — 이건 폭주를 막아 주는 동시에, **모르는 사이에 배치가 영구히 멈추는 경로**이기도 하다. 둘 다 사실이므로 어느 쪽을 택할지는 그 배치가 밀리면 뭐가 곤란해지는지에 달렸다.

---

## 정리

| | DB 안에서 (`UTL_MAIL` / `UTL_SMTP`) | DB 밖에서 (jar + `DBMS_SCHEDULER`) |
|---|---|---|
| 설치·설정 | 스크립트 설치 + `SMTP_OUT_SERVER` + ACL | jar 배포 + credential + 잡 정의 |
| 한글·첨부 | `UTL_MAIL` 은 문서상 ASCII/EBCDIC 범위. 넘어서면 `UTL_SMTP` 로 MIME 직접 조립 | 라이브러리가 처리 |
| 실행 주체 | DB 세션 | credential 의 OS 계정 |
| 실패 감지 | PL/SQL 예외 | **프로세스 종료코드** — 자바가 exit(0) 하면 실패가 성공으로 보인다 |
| 로그 회수 | DB 안 | 스케줄러가 자동 수집 → `GET_FILE` 로 SQL 조회 |

조용히 틀리는 지점만 다시 모으면 이렇다.

1. `java -cp ... -jar` — **`-cp` 가 무시된다.** 경고 없음.
2. manifest `Class-Path` 의 경로가 틀려도 **무시된다.** 기준은 현재 디렉터리가 아니라 jar 의 위치다.
3. `EXECUTABLE` 잡은 셸이 아니다 — 리다이렉션·환경변수·`PATH` 를 기대하지 않는다.
4. 잡은 credential 의 **OS 계정**으로 돈다. 손으로 될 때 되던 파일 권한이 여기서 갈린다.
5. 자바가 예외를 삼키고 정상 종료하면 **메일이 안 갔는데 잡은 성공**이다.
6. `Transport.send` 성공은 접수이지 배달이 아니다.

1·2·5 는 전부 "에러가 안 나는" 실패다. 그래서 이 조합을 처음 세울 때 제일 먼저 만들어야 할 건 메일 발송 로직이 아니라 — **일부러 실패시켰을 때 그게 `USER_SCHEDULER_JOB_RUN_DETAILS` 에 FAILED 로 찍히는지 확인하는 절차**다. 그게 되면 나머지는 고칠 수 있고, 그게 안 되면 나머지가 다 맞아도 언젠가 조용히 멈춘다.

---

## References

[^utlmail]: [`UTL_MAIL` (Oracle Database PL/SQL Packages and Types Reference 19c)](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/UTL_MAIL.html) — Security Model / Operational Notes / Rules and Limits.
[^acl]: [`DBMS_NETWORK_ACL_ADMIN` (Oracle Database PL/SQL Packages and Types Reference)](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_NETWORK_ACL_ADMIN.html) — `APPEND_HOST_ACE`, `connect`/`resolve` 권한.
[^credential]: [`DBMS_CREDENTIAL` (Oracle Database PL/SQL Packages and Types Reference)](https://docs.oracle.com/en/database/oracle/oracle-database/26/arpls/DBMS_CREDENTIAL.html) — `CREATE_CREDENTIAL`.
[^extjob]: [Scheduling Jobs with Oracle Scheduler (Oracle Database Administrator's Guide)](https://docs.oracle.com/en/database/oracle/oracle-database/26/admin/scheduling-jobs-with-oracle-scheduler.html) — 외부 잡 권한, 자격증명, `SET_JOB_ARGUMENT_VALUE`, 잡 출력 자동 수집과 `GET_FILE`, 잡 이력 뷰.
[^jobtypes]: [`DBMS_SCHEDULER` (Oracle Database PL/SQL Packages and Types Reference 19c)](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_SCHEDULER.html) — `job_type` 목록(`PLSQL_BLOCK`·`STORED_PROCEDURE`·`EXECUTABLE`·`CHAIN`·`EXTERNAL_SCRIPT`·`SQL_SCRIPT`·`BACKUP_SCRIPT`).
[^javacmd]: [The `java` Command (Java SE 21 Tool Specifications)](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) — `-jar` 옵션과 `Main-Class`.
[^jarspec]: [JAR File Specification — Class-Path Attribute](https://docs.oracle.com/javase/8/docs/technotes/guides/jar/jar.html)
[^jakartamail]: [Jakarta Mail Specification 2.0](https://jakarta.ee/specifications/mail/2.0/jakarta-mail-spec-2.0.html) — `Session`, `Transport.send`.
[^transport]: [`jakarta.mail.Transport` (Jakarta Mail 2.0 API)](https://jakarta.ee/specifications/mail/2.0/apidocs/jakarta.mail/jakarta/mail/transport) — `send(Message)`.
