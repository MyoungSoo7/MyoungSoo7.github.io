---
layout: post
title: "같은 로그, 같은 스냅샷 — 상태 머신 · 이벤트 소싱 · 결정론적 리플레이"
date: 2026-07-12 05:00:00 +0900
categories: [backend, architecture, engineering]
tags: [event-sourcing, state-machine, deterministic-replay, snapshot, runtime, rust, reliability]
---

![런타임 엔진 — COMMAND→상태머신→RuntimeEvent→EVENT_LOG→SNAPSHOT, PERSIST/LOAD(REPLAY) round-trip 검증](/assets/images/event-sourcing-state-machine-replay.jpg)

대부분 의 시스템 은 *상태 를 저장* 한다 — "이 작업 은 delivered 다" 를 DB 에 쓴다. 이 그림 은 반대 로 간다: **상태 를 저장 하지 않고, 상태 를 만든 *사건(event)* 을 저장** 한다. 그리고 상태 는 그 사건 들 을 *다시 접어서(fold)* 만든다.

핵심 문장 하나 로 시작 하자:

> **로그 가 진실 이고, 스냅샷 은 파생 이다.** 같은 로그 를 replay 하면 *항상 같은 스냅샷* 이 나온다 — 이 성질 이 이 설계 의 심장 이다.

그림 을 왼쪽 부터 부품 별 로 뜯는다.

---

## 1. COMMAND → 상태 머신 — *합법 전이 만 통과*

들어오는 건 **명령(command)** 이다 — `queue-dispatch`, `mark-delivered`. 명령 은 *하고 싶은 것* 일 뿐, 아직 사실 이 아니다. 명령 은 먼저 **상태 머신(state machine)** 을 통과 해야 한다.

상태 머신 의 규칙 은 하나 — **합법 전이 일 때 만 통과**. 불법 전이(예: 이미 delivered 인데 또 deliver) 는 `InvalidTransition` 으로 *거부* 한다.

```
pending → dispatched → delivered   (합법)
delivered → dispatched             (불법 → InvalidTransition)
```

이게 왜 중요 하냐면 — **상태 머신 이 이벤트 로그 의 문지기** 이기 때문 이다. 불법 전이 를 여기서 막으면, *로그 에는 언제나 유효 한 사건 만* 쌓인다. 로그 를 나중 에 아무리 replay 해도 모순 이 안 생긴다. 검증 을 *쓰기 시점* 에 한 번 하면, *읽기(replay) 시점* 엔 안 해도 된다.

---

## 2. RuntimeEvent → EVENT_LOG — *사건 을 append*

합법 전이 는 **RuntimeEvent** 를 낳는다 — `dispatch-delivered`, `worker.recovered`. 이 사건 이 **이벤트 로그(`Vec<RuntimeEvent>`)** 에 *덧붙는다(in-memory append)*.

여기서 관점 의 전환 이 핵심 이다:

- 전통 방식: `UPDATE task SET status='delivered'` — *과거 를 덮어쓴다*. 이전 상태 는 사라진다.
- 이벤트 소싱: `log.push(Delivered{...})` — *과거 를 남긴다*. 모든 변화 의 역사 가 로그 에 있다.

로그 는 **불변(append-only) · 순서 있음 · 완전** 하다. "왜 이 상태 가 됐나" 를 물으면, 로그 를 처음 부터 읽으면 된다. 감사(audit) 가 공짜다.

---

## 3. SNAPSHOT — *파생 상태* 일 뿐

**스냅샷(snapshot)** 은 `backlog · authority · readiness` 같은 *현재 상태* 다. 그런데 그림 이 명시 한다 — **"파생(derived)"**.

즉 스냅샷 은 *진실 이 아니라 캐시* 다. 로그 를 접으면 언제든 다시 만들 수 있다:

```
snapshot = events.fold(empty, apply)
```

스냅샷 이 있는 이유 는 단 하나 — **성능**. 매번 수백만 이벤트 를 replay 하기 싫으니까, *지금 까지 접은 결과* 를 들고 있는 것. 스냅샷 이 깨지거나 의심 스러우면? *버리고 로그 에서 다시 만들면 된다.* 진실 은 로그 에 있으니까.

---

## 4. PERSIST() — *events.json + snapshot.json*, 통째 rewrite

메모리 는 죽는다. 그래서 **PERSIST()** 가 로그 와 스냅샷 을 디스크 로 내린다 — `events.json` + `snapshot.json`.

그림 의 디테일 이 재밌다 — **"file lock · 통째 rewrite (file-append 아님)"**. 보통 이벤트 로그 는 *append-only* 파일 이 정석 인데, 여기선 *파일 전체 를 다시 쓴다*. 트레이드오프:

- **통째 rewrite 장점** — 스냅샷 과 로그 를 *한 번 에 일관 되게* 저장(원자성 확보 쉬움), JSON 처럼 구조 를 통으로 다루기 편함, file lock 으로 동시 쓰기 차단.
- **append-only 였다면** — 쓰기 는 빠르지만(끝 에 붙이기), 스냅샷 과 로그 의 *동기화* 와 부분 쓰기 복구 가 까다로움.

작은 ~중간 규모 런타임(수천~수만 이벤트) 에선 통째 rewrite + lock 이 *단순 하고 안전* 하다. 로그 가 수백만 을 넘어가면 그때 append + 주기적 컴팩션 으로 진화 시키면 된다. **단순함 을 먼저, 최적화 는 필요 할 때.**

---

## 5. LOAD() = REPLAY — *같은 log → 동일 snapshot* (round-trip 검증)

이 설계 의 하이라이트. **LOAD() 는 그냥 읽는 게 아니라 replay 다** — `replay_event` 로 이벤트 를 하나씩 다시 적용 해 상태 를 *재구성* 한다.

그리고 그림 의 마지막 문장 이 이 글 의 제목 이다:

> **같은 log → 동일 snapshot (round-trip 검증)**

이건 *테스트 가능 한 정확성 성질* 이다:

```
snapshot_A = replay(log)
persist(log, snapshot_A)
snapshot_B = replay(load(log))
assert snapshot_A == snapshot_B      // 결정론
```

replay 가 **결정론적(deterministic)** 이면 — 같은 입력(log) 에 항상 같은 출력(snapshot) — 이 등식 이 성립 한다. 이 등식 이 깨지면? *apply 함수 에 비결정성*(시계·난수·외부 호출·맵 순회 순서 등) 이 새어 든 것. round-trip 검증 은 그걸 *자동 으로 잡는 그물* 이다.

`worker.recovered` 이벤트 가 있는 이유 도 여기 있다 — 워커 가 죽어도, **로그 를 replay 해서 죽기 직전 상태 로 정확히 복원** 한다. 크래시 복구 가 *특별한 코드* 가 아니라 *그냥 LOAD()* 다.

---

## 6. 그래서 이 구조 가 주는 것

부품 을 다 모으면 네 가지 를 공짜 로 얻는다:

| 성질 | 어디서 오나 |
|---|---|
| **복구** | 죽으면 로그 replay = LOAD(). 크래시 복구 가 일상 경로 와 같은 코드 |
| **감사** | 모든 변화 가 로그 에 불변 으로 남음. "왜 이 상태냐" = 로그 읽기 |
| **테스트** | 같은 log → 동일 snapshot. 결정론 을 등식 으로 검증 |
| **일관성** | 상태 머신 이 쓰기 시점 에 불법 전이 차단 → 로그 는 항상 유효 |

이건 사실 [Transactional Outbox]({% post_url 2026-07-07-transactional-outbox-pattern-deep-dive %}) 나 정산 시스템 의 [멱등성]({% post_url 2026-06-02-settlement-system-architecture-outbox-triple-idempotency %}) 과 같은 뿌리 다 — **"상태 를 믿지 말고, 사건 의 기록 을 믿어라."** 메시지 는 재전송 될 수 있고 상태 는 덮어써질 수 있지만, *append-only 로그* 는 거짓말 을 안 한다.

---

## 마무리 — 로그 를 진실 로 삼는 대가 와 보상

물론 공짜 는 아니다. 이벤트 스키마 를 오래 유지 해야 하고(옛 이벤트 도 replay 돼야 함), apply 함수 의 결정성 을 지켜야 하고, 스냅샷/컴팩션 전략 이 필요 하다. 하지만 그 대가 로 얻는 게 **"어느 순간 이든 로그 만 있으면 상태 를 정확히 복원 한다"** 는 보장 이다.

> 상태 를 저장 하면 *현재* 를 얻고, 사건 을 저장 하면 *역사 와 현재 를 동시에* 얻는다. 그리고 역사 는 replay 되고, replay 는 검증 된다.

같은 로그 를 넣었을 때 같은 스냅샷 이 나오는지 — 그 한 줄 의 assert 가, 이 런타임 이 *믿을 만한지* 를 증명 한다.
