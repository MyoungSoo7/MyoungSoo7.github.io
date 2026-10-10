---
layout: post
title: "[CS300 #173] WAL 과 복구 — 먼저 적고, 나중에 고친다"
date: 2026-10-10 20:53:00 +0900
categories: [cs]
tags: [cs300, database, wal, crash-recovery, aries]
---

컴퓨터공학 300 주제 시리즈의 173번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

WAL(Write-Ahead Logging)은 데이터 페이지를 고치기 전에 "무엇을 고칠지"를 순차 로그에 먼저 디스크까지 기록하는 규칙이고, 크래시가 나면 그 로그를 다시 읽어 커밋된 변경은 재적용하고 커밋되지 않은 변경은 되돌려 일관된 상태를 복원한다.

## 왜 필요한가

DB 는 데이터를 페이지 단위로 메모리 버퍼에 올려 놓고 고친다. 매 커밋마다 고친 페이지를 전부 디스크에 쓰면 어떨까? 트랜잭션 하나가 테이블 페이지, 인덱스 페이지 여러 개를 건드리면 디스크 여기저기에 랜덤 쓰기가 생긴다. 느리다. 게다가 그 쓰기들 중간에 전원이 나가면 일부 페이지만 새것인 상태가 된다.

WAL 은 이 둘을 한꺼번에 푼다.

- 커밋 시에는 **로그 끝에 순차적으로 덧붙이고** 그것만 `fsync` 한다. 순차 쓰기는 빠르고, 여러 트랜잭션의 로그를 한 번에 내려 쓸 수도 있다(그룹 커밋).
- 데이터 페이지는 나중에 편할 때 내려 쓴다.
- 크래시가 나면 로그가 진실이다. 로그를 따라 페이지를 맞추면 된다.

PostgreSQL 공식 문서는 WAL 의 핵심을 이렇게 설명한다. 데이터 파일의 변경은 그 변경을 기술한 로그 레코드가 영구 저장소에 플러시된 **뒤에만** 쓰여야 한다. 그러면 커밋 때마다 데이터 페이지를 플러시할 필요가 없다.

## 핵심 개념

### 규칙 두 개

1. **로그 먼저(write-ahead)**: 어떤 데이터 페이지를 디스크에 쓰기 전에, 그 페이지를 바꾼 로그 레코드가 먼저 디스크에 있어야 한다.
2. **커밋 = 로그 플러시**: 트랜잭션의 커밋 레코드가 디스크에 닿은 순간이 커밋이다. 그 뒤에 "커밋 성공"을 응답한다.

### 로그 레코드와 LSN

로그는 끝없이 이어지는 레코드의 줄이다. 각 레코드는 고유한 위치 번호 **LSN**(Log Sequence Number)을 가진다.

```
LSN  100: T7 UPDATE page 42, slot 3: balance 1000 → 700
LSN  101: T8 INSERT page 90, slot 1: (...)
LSN  102: T7 UPDATE page 17, slot 9: balance 0 → 300
LSN  103: T7 COMMIT
LSN  104: T8 UPDATE page 42, slot 5: ...
          ← 여기서 크래시
```

각 데이터 페이지는 자신에게 마지막으로 반영된 로그의 LSN(page LSN)을 기억한다. 복구 때 "이 페이지에 LSN 100 이 이미 반영됐나?"를 page LSN 과 비교해 판단한다.

### 버퍼 관리 정책: STEAL / NO-FORCE

| 정책 | 뜻 | 필요한 것 |
|---|---|---|
| NO-FORCE | 커밋 때 데이터 페이지를 강제로 내려 쓰지 않는다 | 크래시 후 **REDO** |
| STEAL | 커밋 안 된 트랜잭션이 고친 페이지도 디스크에 쓸 수 있다 | 크래시 후 **UNDO** |

대부분의 상용 DB 는 성능을 위해 STEAL/NO-FORCE 를 쓰고, 그래서 로그에 REDO 와 UNDO 에 필요한 정보를 모두 남긴다. (PostgreSQL 은 MVCC 덕분에 미커밋 버전이 디스크에 있어도 가시성 규칙으로 무시되므로, 전통적 의미의 UNDO 단계가 없다.)

### 체크포인트

로그가 무한히 길어지면 복구에 무한한 시간이 든다. **체크포인트**는 "이 시점까지의 변경은 모두 데이터 파일에 반영되었다"를 보장하는 지점이다. 그 앞의 로그는 복구에 필요 없으므로 재활용하거나 보관(아카이브)할 수 있다. 체크포인트 간격은 복구 시간과 평상시 쓰기 부하 사이의 거래다. 자주 하면 복구는 빠르지만 쓰기가 몰린다.

### 복구 알고리즘: ARIES

IBM 의 Mohan 등이 1992년에 발표한 ARIES 는 STEAL/NO-FORCE 환경의 표준 복구 알고리즘이다. 세 단계로 이루어진다.

```
1. 분석(Analysis) : 마지막 체크포인트부터 로그를 읽어
                    크래시 시점에 진행 중이던 트랜잭션과 더러운 페이지를 파악
2. 재실행(Redo)   : 필요한 지점부터 로그를 순서대로 다시 적용
                    — 커밋 여부와 상관없이 "크래시 직전 상태"를 그대로 복원
3. 취소(Undo)     : 커밋되지 않은 트랜잭션의 변경을 거꾸로 되돌림
                    — 되돌린 것도 로그(CLR)로 남겨, 복구 중 또 죽어도 안전
```

"역사를 반복한 뒤 실패한 것만 지운다(repeating history)"가 ARIES 의 핵심 아이디어다.

### WAL 의 부수 효과

WAL 은 복구 장치로 시작했지만 다른 용도가 더 커졌다.

- **복제**: 로그를 다른 서버로 보내 재생하면 그 서버가 같은 상태가 된다. PostgreSQL 스트리밍 복제가 이 방식이다.
- **시점 복구(PITR)**: 기본 백업 + 보관된 WAL 을 원하는 시점까지 재생하면, "실수로 테이블을 지우기 1분 전"으로 되돌릴 수 있다.
- **변경 데이터 캡처(CDC)**: 로그를 해석해 변경 이벤트 스트림으로 내보낸다.

## 직접 해 보기

WAL 규칙을 지키는 50줄짜리 키-값 저장소다. 데이터 파일은 체크포인트 때만 쓰고, 커밋은 로그에 `commit` 레코드를 `fsync` 하는 것으로 정의한다.

```python
import json, os, tempfile

class TinyKV:
    """WAL 을 먼저 쓰고(fsync), 데이터 파일은 나중에 쓰는 작은 키-값 저장소."""
    def __init__(self, d):
        self.log_path, self.data_path = os.path.join(d, "wal.log"), os.path.join(d, "data.json")
        self.data = json.load(open(self.data_path)) if os.path.exists(self.data_path) else {}
        self.recover()

    def recover(self):
        if not os.path.exists(self.log_path):
            return
        pending, redone = {}, 0
        for line in open(self.log_path):
            rec = json.loads(line)
            if rec["op"] == "set":
                pending.setdefault(rec["tx"], []).append(rec)
            elif rec["op"] == "commit":          # 커밋된 트랜잭션만 다시 적용(REDO)
                for r in pending.pop(rec["tx"]):
                    self.data[r["k"]] = r["v"]; redone += 1
        print(f"복구: REDO {redone}건, 버린 미커밋 트랜잭션 {sorted(pending)}")

    def _log(self, rec):
        with open(self.log_path, "a") as f:
            f.write(json.dumps(rec) + "\n"); f.flush(); os.fsync(f.fileno())

    def transaction(self, tx, writes, crash_before_commit=False):
        for k, v in writes.items():
            self._log({"op": "set", "tx": tx, "k": k, "v": v})
        if crash_before_commit:
            return                                # 커밋 기록 전에 '죽음'
        self._log({"op": "commit", "tx": tx})     # 이 줄이 디스크에 닿는 순간 = 커밋
        self.data.update(writes)                  # 데이터 파일 반영은 나중(체크포인트)에

    def checkpoint(self):
        tmp = self.data_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, self.data_path)           # 원자적 교체
        os.remove(self.log_path)                  # 반영된 로그는 버린다

d = tempfile.mkdtemp()
kv = TinyKV(d)
kv.transaction(1, {"A": 700, "B": 300})
kv.checkpoint()
kv.transaction(2, {"A": 600, "C": 100})                  # 커밋됨, 아직 체크포인트 전
kv.transaction(3, {"A": 0}, crash_before_commit=True)    # 커밋 전 크래시
del kv                                                   # 메모리 상태는 사라진다
print("데이터 파일만 보면:", json.load(open(os.path.join(d, "data.json"))))
kv2 = TinyKV(d)
print("복구 후:", kv2.data)
```

결과:

```
데이터 파일만 보면: {'A': 700, 'B': 300}
복구: REDO 2건, 버린 미커밋 트랜잭션 [3]
복구 후: {'A': 600, 'B': 300, 'C': 100}
```

데이터 파일은 트랜잭션 1 이후로 한 번도 쓰이지 않았다. 그래도 트랜잭션 2 는 커밋 레코드가 로그에 있으므로 복구 때 재적용되었다(REDO). 트랜잭션 3 은 쓰기 레코드는 있지만 커밋 레코드가 없어 버려졌다. 이 장난감은 미커밋 변경을 데이터 파일에 쓰지 않으므로(NO-STEAL) UNDO 가 필요 없다.

실제 DB 의 WAL 파일도 볼 수 있다. SQLite 를 WAL 모드로 열면 `-wal` 파일이 생긴다.

```python
import sqlite3, os, tempfile
p = os.path.join(tempfile.mkdtemp(), "w.db")
c = sqlite3.connect(p)
print(c.execute("PRAGMA journal_mode=WAL").fetchone())
c.execute("CREATE TABLE t(x)")
c.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(10000)]); c.commit()
print("DB:", os.path.getsize(p), "WAL:", os.path.getsize(p + "-wal"))
c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
print("DB:", os.path.getsize(p), "WAL:", os.path.getsize(p + "-wal"))
```

이 환경(SQLite 3.45)에서는 `DB: 4096 WAL: 107152` 다음에 `DB: 98304 WAL: 0` 이 나왔다. 커밋 직후 변경은 WAL 에만 있고 본 파일은 거의 비어 있다. 체크포인트가 WAL 의 페이지를 본 파일로 옮기자 크기가 역전되었다.

## 현업에서는

- **"커밋은 됐는데 디스크가 거짓말"**: 일부 디스크·가상화 계층은 쓰기 캐시에 받아 놓고 완료를 보고한다. 이 경우 `fsync` 를 믿을 수 없어 지속성이 깨진다. PostgreSQL 문서의 "Reliability" 장이 이 문제를 따로 다룬다. 클라우드나 홈랩에서 DB 볼륨을 고를 때 확인할 항목이다.
- **WAL 디스크 가득 참**: 복제 슬롯을 만들어 놓고 레플리카가 사라지면, 프라이머리는 그 레플리카가 필요로 할 WAL 을 지우지 못하고 계속 쌓는다. 결국 디스크가 차서 DB 가 멈춘다. 쓰지 않는 복제 슬롯 정리는 운영 점검 항목이다.
- **백업 = 기본 백업 + WAL 아카이브**: 매일 밤 덤프만 받으면 최대 하루치를 잃는다. WAL 을 계속 보관하면 마지막 아카이브 시점까지 복원할 수 있다. 쿠버네티스 위의 PostgreSQL 오퍼레이터들도 대부분 이 방식으로 백업한다.
- **체크포인트 튜닝**: 체크포인트 순간 쓰기가 몰려 지연이 튀면, 체크포인트를 더 길게 분산해 쓰도록 설정을 조정한다.

## 확인 문제

1. "로그 먼저" 규칙이 없다면 어떤 상황에서 복구가 불가능해지는가?
2. NO-FORCE 정책을 쓰면 복구 시 어떤 단계가 필요한가? STEAL 은?
3. 체크포인트가 복구 시간을 줄이는 원리는?
4. ARIES 가 Redo 단계에서 커밋되지 않은 트랜잭션의 변경까지 재적용하는 이유는?
5. WAL 이 복제와 시점 복구에 쓰일 수 있는 이유를 한 문장으로 설명하라.

### 풀이

1. 데이터 페이지가 먼저 디스크에 쓰였는데 그 변경의 로그가 없으면, 크래시 후 그 변경을 한 트랜잭션이 커밋되지 않았을 때 되돌릴 정보가 없다.
2. NO-FORCE: 커밋된 변경이 데이터 파일에 없을 수 있으므로 REDO. STEAL: 미커밋 변경이 데이터 파일에 있을 수 있으므로 UNDO.
3. 체크포인트 이전 변경은 데이터 파일에 반영되어 있으므로, 복구는 체크포인트 이후 로그만 읽으면 된다.
4. 크래시 직전 상태를 정확히 재현한 뒤 미커밋 것만 되돌리면, 페이지 상태와 로그가 항상 일치하는 단순한 불변식을 유지할 수 있다.
5. WAL 은 모든 변경을 순서대로 기록한 것이므로, 같은 출발점에서 같은 로그를 재생하면 같은 상태(또는 원하는 시점의 상태)가 된다.

## 더 읽을거리 (References)

- PostgreSQL 공식 문서, [Write-Ahead Logging (WAL)](https://www.postgresql.org/docs/current/wal-intro.html), [Reliability](https://www.postgresql.org/docs/current/wal-reliability.html)
- PostgreSQL 공식 문서, [Continuous Archiving and Point-in-Time Recovery](https://www.postgresql.org/docs/current/continuous-archiving.html)
- SQLite 공식 문서, [Write-Ahead Logging](https://www.sqlite.org/wal.html)
- C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh, P. Schwarz, "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging", *ACM TODS*, 17(1), 1992. [PDF](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)
