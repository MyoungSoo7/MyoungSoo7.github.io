---
layout: post
title: "정산과 보안은 같은 통제면이다 — 원장 불변·감사 로그·필드 암호화·멱등키를 한 위협모델로 묶기"
date: 2026-10-03 17:49:50 +0900
categories: [Settlement, Security]
tags: [settlement, security, ledger, audit-log, aes-gcm, idempotency, postgresql, pci-dss]
---

정산 시스템을 만들다 보면 "이건 회계 정합성 문제", "이건 보안 문제" 하고 칸을 나누게 된다. 원장 금액이 틀어지면 회계팀 일이고, 계좌번호가 로그에 찍히면 보안팀 일이라는 식이다.

그런데 사고를 공격자 입장에서 다시 쓰면 이 칸막이가 무너진다.

- **전기된 전표의 금액을 UPDATE 한다** — 버그면 정합성 사고, 내부자가 하면 횡령이다.
- **같은 지급 이벤트를 두 번 처리한다** — 재전송이면 장애, 의도적으로 재생(replay)하면 이중 인출 공격이다.
- **감사 로그를 지운다** — 실수면 데이터 유실, 의도면 증거 인멸이다.

결과물은 똑같다. 다른 건 *의도*뿐이고, 코드는 의도를 모른다. 그래서 정산에서는 **정합성 통제와 보안 통제를 같은 장치로 만드는 편이 이득**이다. 하나를 세우면 두 위협을 함께 막는다.

이 글은 개인 프로젝트 `settlement`(Spring Boot 헥사고날 MSA, PostgreSQL)의 `main` 브랜치(커밋 `1d248cc6`)에 실제로 들어 있는 통제 다섯 가지를 이 관점으로 정리한다. 리포가 비공개라서 링크 대신 파일 경로를 적는다. 그리고 마지막에는 **이 장치들이 막지 *못하는* 것**도 같은 무게로 적는다.

---

## 0. 출발점 — "회계사는 지우개를 쓰지 않는다"

Pat Helland 는 CIDR 2015 논문 *Immutability Changes Everything* 에 이렇게 썼다.

> "Accountants don't use erasers or they go to jail. All entries in a ledger remain in the ledger. Corrections can be made but only by making new entries in the ledger." — [Helland, CIDR 2015, §2.2](https://www.cidrdb.org/cidr2015/Papers/CIDR15_Paper16.pdf)

복식부기는 수백 년 동안 이 규칙으로 *변조 탐지*를 해 왔다. 틀린 전표를 고치지 않고 역분개 전표를 새로 쓰면 "언제 무엇이 틀렸고 누가 바로잡았는지"가 장부에 그대로 남는다. 회계 규칙이 곧 무결성(Integrity) 통제인 셈이다. 아래 다섯 장치는 모두 이 원리를 DB와 코드로 옮긴 것이다.

---

## 1. 원장 불변 트리거 — 버그와 내부자를 같은 문으로 막는다

`order-service/.../V20260715200001__ledger_entries_immutability_trigger.sql`

```sql
IF OLD.status = 'POSTED' THEN
    IF (NEW.amount, NEW.debit_account, NEW.credit_account, NEW.reference_id,
        NEW.reference_type, NEW.entry_type, NEW.settlement_date)
       IS DISTINCT FROM
       (OLD.amount, OLD.debit_account, OLD.credit_account, OLD.reference_id,
        OLD.reference_type, OLD.entry_type, OLD.settlement_date) THEN
        RAISE EXCEPTION 'Ledger entry id=% is POSTED (immutable). ...' USING ERRCODE = '23514';
    END IF;
    IF NEW.status NOT IN ('POSTED', 'REVERSED') THEN ... RAISE
ELSIF OLD.status = 'REVERSED' THEN ... RAISE   -- 종료 상태
```

정한 규칙은 이렇다.

| 상태 | UPDATE | DELETE |
|---|---|---|
| PENDING | 허용 | 허용(롤백) |
| POSTED | 금액·계정·참조 변경 차단, `→ REVERSED` 전이만 허용 | 차단 |
| REVERSED | 전부 차단 | 차단 |

정정 경로는 "역분개 전표를 새로 쓰고, 원 전표는 `REVERSED` 로 표시하고, `reversal_entry_id` 로 연결"하는 것 하나뿐이다. Helland 가 말한 append-only 를 상태 머신으로 강제한 것이다.

**보안 관점에서 무엇이 달라지나.** 애플리케이션 계층에서만 검증하면 우회 경로가 많다. 수기 SQL 콘솔, 마이그레이션 스크립트, 다른 서비스가 같은 DB에 붙는 경우가 그렇다. 트리거는 *어느 경로로 들어온 쓰기든* 같은 지점에서 막는다. 버그를 막으려고 넣은 장치가 내부자 위협 통제로도 그대로 쓰인다.

---

## 2. 감사 로그 append-only + PII 유입 거부 — 증거를 지키고, 증거가 유출 경로가 되지 않게

### 2-1. 변조 차단

`order-service/.../V20260715130000__audit_logs_partitioning.sql`

```sql
CREATE OR REPLACE FUNCTION opslab.audit_logs_block_modify() RETURNS trigger ... $$
BEGIN
    RAISE EXCEPTION 'audit_logs 는 append-only 입니다: % 연산 불가 (감사 로그 변조 차단)', TG_OP;
END; $$;
CREATE TRIGGER trg_audit_logs_append_only
    BEFORE UPDATE OR DELETE ON opslab.audit_logs
    FOR EACH ROW EXECUTE FUNCTION opslab.audit_logs_block_modify();
```

카드 결제 업계 표준인 PCI DSS v4.0.1 도 같은 요구를 한다. 요구사항 10.3.2 는 *"Audit log files are protected to prevent modifications by individuals"* 이다 ([PCI DSS v4.0.1, Req. 10.3.2](https://www.pcisecuritystandards.org/document_library/)). 다만 PCI DSS 는 카드번호(PAN)를 다루는 환경에 적용되는 표준이다. 이 프로젝트는 PAN 을 저장하지 않으므로 여기서는 **참고 기준**으로만 인용한다. 규제 준수를 주장하는 것이 아니다.

### 2-2. 감사 로그가 오히려 개인정보 유출 경로가 되는 역설

append-only 에는 부작용이 있다. **한번 잘못 들어간 데이터는 고칠 방법이 없다.** 기록기가 마스킹을 빠뜨리고 주민등록번호를 `detail_json` 에 넣으면, 그 주민번호는 지울 수 없는 테이블에 영구히 남는다. 무결성 통제가 기밀성 사고를 키우는 셈이다.

그래서 유입 시점에 막는다.

`order-service/.../V20260718130000__audit_detail_pii_guard.sql`

```sql
IF NEW.detail_json IS NOT NULL
   AND NEW.detail_json::text ~ '\d{6}-[1-4]\d{6}' THEN
    RAISE EXCEPTION 'audit_logs.detail_json 에 주민등록번호 패턴 유입 — 기록기 마스킹 계약 위반';
END IF;
```

국내 법적 근거도 있다. 개인정보 보호법 제24조의2 제2항은 주민등록번호를 *"암호화 조치를 통하여 안전하게 보관하여야 한다"* 고 정한다 ([국가법령정보센터, 개인정보 보호법 제24조의2](https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1006184231)). 감사 로그에 평문 주민번호가 박히면 이 의무를 지킬 수 없다.

눈여겨볼 부분은 **범위를 일부러 좁혔다**는 점이다. 마이그레이션 주석에 따르면 계좌번호와 전화번호는 형식이 느슨해서 금액이나 ID 문자열과 오탐이 난다. 그래서 정규식 거부 대상에서 빼고 기록기의 마스킹 계약에 맡겼다. 판단 기준은 "과차단이 감사 유실보다 위험하다"였다. 보안 통제가 정산 기록 자체를 막으면 그것도 사고다. 두 목표가 충돌하는 지점에서 경계선을 명시적으로 그은 사례다.

---

## 3. 지급 계좌 필드 암호화 + 마스킹 — 저장할 때와 보여줄 때를 따로 다룬다

정산의 끝은 송금이다. 송금하려면 셀러 계좌번호가 있어야 한다.

### 3-1. 저장할 때: AES-256-GCM

`settlement-service/.../crypto/FieldEncryptionConverter.java`

```java
private static final String TRANSFORMATION = "AES/GCM/NoPadding";
private static final int KEY_BYTES = 32;   // AES-256
private static final int IV_BYTES = 12;    // GCM 권장 nonce 길이
private static final int TAG_BITS = 128;   // GCM 인증 태그 길이
```

- 저장 형식은 `enc:v1:` 접두에 `Base64(IV || ciphertext+tag)` 를 붙인 것이다.
- 키 `PAYOUT_ENC_KEY` 에는 기본값이 없다. 설정하지 않으면 **부팅이 실패한다(fail-closed)**.
- 암호화는 JPA 영속 어댑터의 Converter 가 맡는다. 도메인 객체 `SellerBankAccount` 는 평문을 다루고 암호화를 모른다. 헥사고날 경계 덕에 보안 관심사가 도메인을 오염시키지 않는다.

GCM 을 고른 이유는 기밀성과 무결성을 함께 주기 때문이다. 인증 태그가 있으니 DB에서 누군가 암호문 바이트를 바꾸면 복호화가 *실패*한다. 조용히 다른 계좌번호로 풀리지 않는다. 송금 계좌가 바뀌는 건 곧 돈이 다른 곳으로 가는 일이라, 정산에서는 무결성 쪽이 더 중요하다.

**대신 GCM 에는 반드시 지켜야 할 조건이 있다.** NIST SP 800-38D 는 같은 키에서 IV 가 한 번이라도 반복되면 위조 공격에 노출될 수 있다고 하며 *"this requirement is almost as important as the secrecy of the key"* 라고 쓴다. 이 구현처럼 IV 를 난수로 만드는 RBG 기반 구성을 쓰면, **한 키로 수행하는 암호화 호출은 총 2³² 회를 넘으면 안 된다** ([NIST SP 800-38D §8, §8.3](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)). 계좌번호 필드 암호화는 이 한도에 한참 못 미치는 규모다. 그래도 키 교체 경로는 있어야 하고, `enc:v1:` 버전 접두가 그 자리를 마련해 둔 것이다. 단, 이 글을 쓰는 시점에 v2 키 교체 절차가 구현돼 있는지는 확인하지 않았다.

### 3-2. 보여줄 때: 뒤 4자리만

```java
public String maskedAccountNumber() {
    if (acct.length() <= 4) return "****";
    return "****" + acct.substring(acct.length() - 4);
}
```

이 프로젝트에서 로그, 운영자 콘솔 API, 펌뱅킹 어댑터 로그(`Mock`·`Sandbox`·`Fep` 세 구현 모두)는 `maskedAccountNumber()` 만 쓴다. 계좌번호와 성격이 같은 사업자등록번호도 지급 차단 예외 메시지에서 뒤 4자리만 남긴다(`PayoutBlockedException`). 개인사업자에게는 준식별자이기 때문이다.

PCI DSS 3.4.1 은 카드번호 표시를 *"the BIN and last four digits are the maximum"* 으로 제한하고, 3.5.1 은 저장된 PAN 을 읽을 수 없게 만들라고 요구한다 ([PCI DSS v4.0.1](https://www.pcisecuritystandards.org/document_library/)). 계좌번호는 PAN 이 아니지만, **표시(masking)와 저장(암호화)을 별개 통제로 둔다**는 구조는 그대로 빌려 쓸 수 있다.

---

## 4. 멱등키 보존 하한 7일 — 운영 편의가 이중 지급 구멍이 되지 않게

`finance-service/.../V20260716302000__prune_processed_events_min_retention_guard.sql`

```sql
IF p_retention IS NULL OR p_retention < INTERVAL '7 days' THEN
    RAISE EXCEPTION 'p_retention 은 최소 7일 이상이어야 합니다(재전송 창 내 멱등키 조기 삭제 → 이중 처리 방지)';
END IF;
```

Kafka 같은 at-least-once 메시징에서는 같은 메시지가 두 번 이상 도착할 수 있다 ([Apache Kafka 문서, Message Delivery Semantics](https://kafka.apache.org/documentation/#semantics)). 그래서 소비자는 `(consumer_group, event_id)` 를 `processed_events` 에 기록해 중복을 거른다.

함정은 이 테이블을 *청소*할 때 생긴다. 테이블이 커지면 누군가 보존 기간을 줄이고 싶어진다. 그런데 재전송 창 안에 있는 `event_id` 를 지우면, 다시 도착한 같은 지급 이벤트가 "처음 보는 이벤트"로 처리된다. **이중 기표, 이중 정산, 이중 송금**으로 이어진다.

보안 관점에서는 재생 공격 방어선이 **설정값 하나로 무너지는 구조**다. 그래서 함수 안에 하한선을 박아 넣었다. 누가 실수로 `INTERVAL '1 day'` 를 넘기면 DB가 거부한다. "7일"은 이 시스템의 재전송 지연 상한을 보고 정한 값이지 범용 기준이 아니다.

---

## 5. 지급 직전 게이트와 fail-closed — 모르면 보내지 않는다

정산에서 가장 비싼 실수는 *보내지 말아야 할 돈을 보내는 것*이다. 돈이 일단 나가면 회수는 법적·운영 절차가 된다.

- **사업자 상태 게이트.** 송금 직전에 셀러의 사업자 휴폐업 상태를 조회한다. 폐업이거나 미등록이면 `PayoutBlockedException` 을 던진다. 이때 Payout 은 `FAILED` 가 아니라 `REQUESTED` 로 *그대로 남는다*. 펌뱅킹을 호출하지 않았으므로 실패가 아니고, 상태가 바뀌면 다음 배치가 다시 판정한다(`PayoutBlockedException.java` 주석).
- **Mock 펌뱅킹 fail-closed.** `MockFirmBankingAdapter` 는 `app.firmbanking.mode=mock` 을 *명시*해야만 뜨고, prod 프로파일에서는 뜨지 않는다. 가짜 송금 어댑터가 운영에 섞여 들어가 "송금 완료"를 거짓으로 보고하는 사고를 구조적으로 막는다.
- **키 미설정 시 부팅 실패.** 3절의 `PAYOUT_ENC_KEY` 와 같은 원칙이다. 기본값으로 조용히 뜨는 대신 시끄럽게 죽는다.

세 장치 모두 **불확실하면 돈을 움직이지 않는 쪽으로 넘어진다**. 보안의 fail-closed 원칙이 정산에서는 "잘못된 송금 0건"이라는 정합성 목표와 정확히 겹친다.

덧붙여 운영 웹훅(`operation-service/.../OpsWebhookAuthFilter.java`)은 토큰을 `MessageDigest.isEqual` 로 비교한다. 문자열 `equals` 는 첫 불일치 바이트에서 멈추기 때문에, 응답 시간 차이로 토큰을 한 바이트씩 추측하는 타이밍 공격이 가능하다. 이를 막는 표준적인 방법이다.

---

## 6. 막지 못하는 것 — 트리거는 권한 모델 위에 서 있다

여기까지만 읽으면 DB 트리거가 만능처럼 보인다. 아니다. 아래 우회 경로는 **문서화된 PostgreSQL 동작**이다.

| 우회 경로 | 근거 | 이 리포의 상태 |
|---|---|---|
| **`TRUNCATE`** — row-level `BEFORE UPDATE/DELETE` 트리거는 TRUNCATE 에 발화하지 않는다 | [PostgreSQL CREATE TRIGGER](https://www.postgresql.org/docs/current/sql-createtrigger.html): TRUNCATE 는 statement-level 트리거만 지원 | **알고서 열어 뒀다.** `V20260717200000__loan_ledger_parity_hardening.sql` 주석에 "테스트 픽스처는 TRUNCATE 로 전환 … 테스트 격리와 운영 불변이 공존"이라고 적혀 있다. 테스트를 위한 선택이 운영의 구멍으로 남은 것이다 |
| **`session_replication_role = replica`** — 기본 설정의 트리거가 발화하지 않는다(FK 검사까지 꺼진다) | [PostgreSQL 19.11](https://www.postgresql.org/docs/current/runtime-config-client.html): superuser 또는 해당 `SET` 권한 보유자만 변경 가능 | 앱 DB 계정이 이 권한을 갖는지는 **이 글에서 확인하지 않았다** |
| **`ALTER TABLE … DISABLE TRIGGER` / `DROP TRIGGER`** | 테이블 소유자 권한 | Flyway 가 테이블을 만들었다면 앱 계정이 소유자일 가능성이 높다. **미확인** |

결론은 이렇다. **트리거는 "앱 계정이 테이블 소유자도 superuser 도 아니다"라는 권한 분리가 받쳐 줄 때만 내부자 통제가 된다.** 마이그레이션 계정과 런타임 계정이 같으면, 트리거는 버그는 막아도 마음먹은 내부자는 못 막는다. 이 프로젝트에서 계정이 실제로 분리돼 있는지는 다음에 확인할 항목으로 남긴다.

그래서 PCI DSS 도 로그 보호를 트리거 같은 접근 통제 하나에 맡기지 않는다. 10.3.3 은 *"modify 하기 어려운"* 중앙 서버로 즉시 백업하라고 하고, 10.3.4 는 무결성 모니터링(FIM)으로 변경 시 경보가 울리게 하라고 한다. 같은 DB 안의 트리거는 이 중 첫 단계일 뿐이다. TRUNCATE 를 statement-level 트리거로 막거나, 감사 로그를 DB 밖(WORM 스토리지 등)으로 복제하는 것이 다음 단계다.

---

## 정리 — 한 장치, 두 위협

| 장치 | 정합성 위협 (실수·장애) | 보안 위협 (의도) | 남은 구멍 |
|---|---|---|---|
| 원장 불변 트리거 | 버그성 UPDATE·수기 SQL | 내부자 금액 변조 | TRUNCATE·권한 우회 |
| 감사 로그 append-only | 로그 유실 | 증거 인멸 | 같은 DB 안에 있음(외부 복제 없음) |
| 감사 로그 주민번호 거부 | — | 지울 수 없는 PII 유출 | 계좌·전화번호는 기록기 계약에 위임 |
| 계좌 AES-GCM + 마스킹 | — | DB 덤프 유출, 암호문 바꿔치기 | 키 교체 절차 미확인, GCM 호출 한도 |
| 멱등키 보존 하한 | Kafka 재전송 이중 처리 | 재생 공격 | 하한값 7일은 이 시스템 기준 |
| 지급 게이트·fail-closed | 폐업 셀러 송금, Mock 혼입 | 잘못된 지급 유도 | 상태 조회 원천의 신선도 |

정산은 "돈이 맞는가"를 묻고 보안은 "누가 돈을 틀리게 만들 수 있는가"를 묻는다. 둘이 쳐다보는 대상은 **같은 원장, 같은 로그, 같은 송금 버튼**이다. 그러니 통제도 하나로 세우고, 그 통제가 어디까지 버티는지(6절)를 같은 문서에 적어 두는 것이 정직한 설계다.

---

## References

1. Pat Helland, "Immutability Changes Everything", *CIDR 2015*. <https://www.cidrdb.org/cidr2015/Papers/CIDR15_Paper16.pdf> (ACM Queue 판: <https://queue.acm.org/detail.cfm?id=2884038>)
2. NIST, *SP 800-38D: Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) and GMAC*, M. Dworkin, 2007. <https://csrc.nist.gov/pubs/sp/800/38/d/final> — §8 IV 유일성 요구, §8.2.2 RBG 기반 구성, §8.3 호출 횟수 2³² 제한
3. PCI Security Standards Council, *PCI DSS v4.0.1: Requirements and Testing Procedures*, June 2024. <https://www.pcisecuritystandards.org/document_library/> — Req. 3.4.1, 3.5.1, 10.3.2, 10.3.3, 10.3.4 (PAN 환경 표준. 이 글에서는 참고 기준으로만 인용)
4. PCI SSC, "Just Published: PCI DSS v4.0.1", 2024-06-11. <https://blog.pcisecuritystandards.org/just-published-pci-dss-v4-0-1>
5. 개인정보 보호법 제24조의2(주민등록번호 처리의 제한), 국가법령정보센터. <https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1006184231>
6. PostgreSQL Documentation, *CREATE TRIGGER*. <https://www.postgresql.org/docs/current/sql-createtrigger.html>
7. PostgreSQL Documentation, *19.11 Client Connection Defaults — session_replication_role*. <https://www.postgresql.org/docs/current/runtime-config-client.html>
8. Apache Kafka Documentation, *Message Delivery Semantics*. <https://kafka.apache.org/documentation/#semantics>
9. 코드 근거: 비공개 리포 `MyoungSoo7/settlement` `main` @ `1d248cc6` — 본문에 표기한 각 파일 경로
