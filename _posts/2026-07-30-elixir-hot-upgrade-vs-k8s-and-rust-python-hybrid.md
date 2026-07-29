---
layout: post
title: "*프로세스 안에서 코드를 갈아끼울 것인가, 프로세스를 통째로 버릴 것인가* — Elixir *핫 업그레이드* vs *쿠버네티스 파드 교체*, 그리고 *네이티브 하이브리드* 3종 비교 (Rust · Python · JNI/Panama)"
date: 2026-07-30 02:00:00 +0900
categories: [elixir, kubernetes, architecture, jvm]
tags: [Elixir, BEAM, OTP, HotCodeUpgrade, relup, Kubernetes, RollingUpdate, Rustler, Rust, Pythonx, Python, NIF, JNI, Panama, FFM, Java, Nx, FLAME]
---

# 두 개의 무중단 배포 철학

배포 중에 서비스를 멈추지 않는 방법은 크게 둘로 갈린다.

- **프로세스를 살려둔 채 그 안의 코드를 갈아끼운다** — Erlang/OTP 의 핫 코드 업그레이드
- **프로세스를 버리고 새 프로세스를 세운다** — 쿠버네티스의 롤링 업데이트

전자는 BEAM 이 30년 가까이 자랑해온 기능이고, 후자는 지난 10년간 사실상 업계 표준이 됐다. 이 글은 둘을 정면으로 비교한다. 그리고 결론부터 말하면, **Elixir 공식 문서 자신이 후자를 권한다.** 그 이유를 따라가면 BEAM 이 무엇을 잘하고 무엇을 포기했는지가 드러난다.

후반부에서는 같은 잣대로 네이티브 하이브리드를 비교한다 — **Elixir + Rust**, **Elixir + Python**, 그리고 **Java + C/C++ (JNI · Panama)**. 앞의 두 조합은 흔히 "궁합" 이라는 말로 뭉뚱그려지는데 실제로는 **정반대 방향으로 위험하고**, 세 번째 사례는 같은 문제를 **플랫폼 차원에서** 푸는 대조군이 된다.

---

# 1. Erlang/OTP 의 핫 업그레이드는 실제로 어떻게 동작하나

먼저 기계장치를 정확히 보자. OTP 의 릴리스 업그레이드는 두 개의 파일로 굴러간다.

- **`.appup`** — 애플리케이션 하나가 버전 A 에서 B 로 갈 때 무엇을 해야 하는지 적은 레시피
- **`.relup`** — 릴리스 전체의 업그레이드 지시서. `systools:make_relup/3` 이 `.appup` 들을 모아 저수준 명령으로 번역해 만든다[^systools]

Erlang 공식 문서(SASL `systools`)는 `relup` 을 이렇게 정의한다.

> "Generates a release upgrade file `relup` containing instructions for upgrading from or downgrading to one or more previous releases. **The instructions are used by `release_handler` when installing a new version of a release in runtime.**"[^systools]

핵심은 **런타임에 설치된다** 는 것이다. 프로세스는 죽지 않고, 모듈만 교체되며, 각 프로세스의 상태는 `code_change/3` 콜백을 통해 새 형태로 변환된다.

이론적으로는 아름답다. 커넥션이 끊기지 않고, 진행 중인 작업이 유지되며, 재기동 비용이 0 이다.

---

# 2. 그런데 Elixir 는 이 기능을 기본으로 제공하지 않는다

여기가 이 글의 첫 번째 반전이다. `mix release` 공식 문서의 "Hot Code Upgrades" 절은 이렇게 시작한다.

> "Erlang and Elixir are sometimes known for the capability of upgrading a node that is running in production without shutting down that node. **However, this feature is not supported out of the box by Elixir releases.**"[^mixrelease]

그리고 이유를 직접 밝힌다.

> "The reason we don't provide hot code upgrades is because they are **very complicated to perform in practice**, as they require careful coding of your processes and applications as well as extensive testing. **Given most teams can use other techniques that are language agnostic to upgrade their systems, such as Blue/Green deployments, Canary deployments, Rolling deployments, and others, hot upgrades are rarely a viable option.**"[^mixrelease]

**언어 비종속적인 배포 기법(블루/그린, 카나리, 롤링)을 쓰라고 언어 공식 문서가 권한다.** 이것은 곧 "쿠버네티스가 하는 방식을 쓰라" 는 말과 같다.

José Valim 은 2019년 릴리스 기능을 설계하면서 이 결정을 명시적으로 남겼다.

> "I have spent most of the week studying hot code upgrades and building prototypes and **I have decided to not include them as part of Elixir Core for now** … The rationale is that they are still very complex, error prone and opinionated in a way that whoever is performing them needs to be aware of many of the decisions taken."[^issue8612]

## 2.1 왜 그렇게 어려운가 — 문서의 예제

공식 문서가 드는 예가 정확하다. 카운터를 들고 있는 GenServer 가 있다고 하자. 상태가 `0` 이라는 정수였는데, 새 버전에서 `{counter, max}` 튜플로 바뀌었다. 그리고 호출 메시지도 `:bump` 에서 `{:bump, by}` 로 바뀌었다.

이때 핫 업그레이드를 하면 **크래시한다.** 문서는 그 이유를 이렇게 설명한다.

> "…in the initial version the state was just a counter but in the new version the state is a tuple. Furthermore, you changed the format of the `call` message from `:bump` to `{:bump, by}` and **the process may have both old and new messages temporarily mixed**, so we need to handle both."[^mixrelease]

즉 코드를 이렇게 써야 한다.

```elixir
# 새 메시지와 옛 메시지를 *동시에* 처리할 수 있어야 한다
def handle_call(:bump, {counter, max}), do: {:reply, :ok, {counter + 1, max(max, 1)}}
def handle_call({:bump, by}, {counter, max}), do: {:reply, :ok, {counter + by, max(max, by)}}

# 그리고 옛 상태를 새 상태로 옮기는 코드도 따로 필요하다
def code_change(_, counter, _), do: {:ok, {counter, 0}}
```

이 부담이 **시스템의 모든 프로세스, 모든 애플리케이션에** 적용된다. 문서의 표현대로 "it must be taken into account by every process and application being upgraded in the system".[^mixrelease]

여기서 드러나는 본질은 이것이다. 핫 업그레이드는 **배포 기법이 아니라 코딩 규율** 이다. 배포 시점에 결정할 수 있는 게 아니라, 애플리케이션 전체를 그 전제로 써야 한다.

---

# 3. 쿠버네티스 파드 교체는 무엇을 다르게 하나

쿠버네티스의 Deployment 는 기본 전략이 `RollingUpdate` 이고, 두 개의 손잡이로 교체 속도를 조절한다.[^k8sdeploy]

- **`maxUnavailable`** — 업데이트 중 사용 불가 상태를 허용할 파드 수
- **`maxSurge`** — 원하는 수보다 추가로 만들 수 있는 파드 수

새 파드가 뜨고, readiness 를 통과하고, 그다음에 옛 파드가 내려간다. 상태는 **이전되지 않는다.** 대신 애초에 상태를 프로세스 밖(DB·캐시·객체 스토리지)에 두도록 강제된다.

핵심 차이를 정리하면 이렇다.

| 축 | Erlang/OTP 핫 업그레이드 | 쿠버네티스 롤링 업데이트 |
|---|---|---|
| 교체 단위 | **모듈** (프로세스 유지) | **프로세스/컨테이너 전체** |
| 인메모리 상태 | `code_change/3` 로 **이전** | **버림** (외부 저장소 전제) |
| 연결 | 유지됨 | 드레이닝 후 재연결 |
| 필요한 사전 작업 | `.appup` · `.relup` + 모든 프로세스의 업그레이드 대비 코딩 | readiness/liveness 프로브, 무상태 설계 |
| 롤백 | `relup` 의 downgrade 경로 (역시 수작업) | **이전 ReplicaSet 으로 되돌리기** |
| 검증 방법 | 스테이징에서 A→B 전이 자체를 테스트해야 함 | **새 이미지 자체를 테스트** (전이가 아님) |
| 언어 종속성 | BEAM 전용 | 언어 무관 |
| 실패 시 폭발 반경 | 노드 전체가 이상 상태에 빠질 수 있음 | 파드 하나 |

가장 중요한 줄은 **검증 방법** 이다. 파드 교체 모델에서 테스트 대상은 "새 버전" 하나다. 핫 업그레이드에서 테스트 대상은 **"A 에서 B 로 가는 전이"** 이고, 이건 버전 조합만큼 늘어난다. `A→B`, `B→C` 가 각각 통과해도 `A→C` 는 별개다.

---

# 4. 그렇다면 핫 업그레이드는 죽은 기술인가

아니다. **파드를 교체할 수 없는 곳** 이 여전히 있다.

- **임베디드/IoT** — 현장에 나간 장비를 재부팅할 수 없거나, 재부팅 자체가 위험한 경우. Nerves 계열이 여기 해당한다.
- **통신 장비** — 진행 중인 통화 세션을 끊을 수 없는 스위치. 애초에 Erlang 이 태어난 도메인이다.
- **상태가 곧 서비스인 시스템** — 수십만 개의 장기 연결이 프로세스 안에 살아 있고, 재연결 폭풍(thundering herd)이 재기동보다 더 위험한 경우.

공통점은 **상태를 밖으로 뺄 수 없다**는 것이다. 반대로 말하면, 상태를 밖으로 뺄 수 있다면 파드 교체가 거의 언제나 더 싸다. Elixir 문서가 "most teams" 라고 쓴 이유가 이것이다.[^mixrelease]

그리고 `mix release` 는 핫 업그레이드를 **금지** 하지 않는다. 문서는 이렇게 끝맺는다.

> "However, hot code upgrades can still be achieved by teams who desire to implement those steps on top of `mix release` in their projects or as separate libraries."[^mixrelease]

기본값에서 뺐을 뿐, 필요한 팀은 그 위에 쌓으라는 것이다. 좋은 기본값 설계다.

## 4.1 파드 교체도 공짜가 아니다 — 현장의 반례

균형을 위해 적어둘 것이 있다. 필자가 운영하는 K3s 클러스터에서 최근 이런 일이 있었다.

한 Spring Boot 서비스가 **12일 동안 17번 재시작** 했다. 원인은 코드가 아니라 **헬스체크 프로브 설정** 이었다 — `timeoutSeconds` 가 지정되지 않아 쿠버네티스 기본값 1초로 동작했고, 헬스 엔드포인트가 DB 상태까지 확인하느라 가끔 1초를 넘겼다. 그러면 kubelet 이 "죽었다" 고 판단하고 컨테이너를 죽인다.

즉 **파드 교체 모델은 "언제 죽일 것인가" 라는 판단을 인프라에 위임하는 대가** 를 치른다. 핫 업그레이드가 코딩 규율을 요구한다면, 파드 교체는 **운영 설정의 규율** 을 요구한다. 공짜인 쪽은 없다.

---

# 5. 하이브리드 — Rust 와 Python 은 같은 문으로 들어온다

주제를 바꾸자. Elixir 는 왜 Rust 와 궁합이 좋다고들 하는가? 그리고 Python 조합은 무엇이 다른가?

출발점은 같다. **둘 다 NIF(Native Implemented Function) 라는 같은 문으로 들어온다.** 그리고 그 문에는 Erlang 공식 문서가 붙여둔 경고문이 있다.

> **Warning — Use this functionality with extreme care.**
> "A native function is executed as a direct extension of the native code of the VM. Execution is not made in a safe environment. **The VM cannot provide the same services as provided when executing Erlang code, such as pre-emptive scheduling or memory protection.** If the native function does not behave well, the whole VM will misbehave.
> - **A native function that crashes will crash the whole VM.**
> - An erroneously implemented native function can cause a VM internal state inconsistency…"[^erlnif]

그리고 시간 제약이 있다.

> "usually a well-behaving native function is to **return to its caller within 1 millisecond**"[^erlnif]

1ms 를 넘길 수밖에 없는 작업은 **dirty NIF** 로 선언해 별도 스케줄러(dirty scheduler)에서 돌려야 한다.[^erlnif]

여기서 핵심을 잡아야 한다. **NIF 는 BEAM 의 가장 큰 자산인 "격리" 를 포기하는 지점이다.** Erlang 시스템 문서는 더 직설적이다 — NIF 는 "the fastest way of calling C-code from Erlang … **But it is also the least safe, because a crash in a NIF brings the emulator down too.**"[^erlnifsys]

이제 Rust 와 Python 이 이 문 앞에서 각각 무엇을 하는지 보자.

---

# 6. Elixir + Rust — 문을 안전하게 만든다

Rustler 의 공식 소개문은 그 목적을 한 문장으로 말한다.

> "Rustler is a library for writing Erlang NIFs in **safe Rust code**. That means **there should be no ways to crash the BEAM** (Erlang VM). The library … **catches rust panics before they unwind into C**."[^rustler]

저장소의 Safety 절은 더 짧다.

> "The code you write in a Rust NIF **should never be able to crash the BEAM**."[^rustler]

무슨 일이 벌어지는지 정리하면 이렇다.

1. NIF 는 원래 **BEAM 을 통째로 죽일 수 있는** 위험 지점이다 (공식 경고)
2. Rust 는 컴파일 타임에 메모리 안전성을 보장한다 — use-after-free, 버퍼 오버런, 데이터 레이스가 타입 시스템에서 걸린다
3. Rustler 는 여기에 더해 **panic 이 C 경계를 넘기 전에 잡는다**
4. 결과적으로 **NIF 를 쓰면서도 BEAM 의 크래시 격리를 유지** 할 수 있다

긴 작업은 어노테이션 한 줄로 dirty 스케줄러에 보낸다.[^rustlernif]

```rust
#[nif(schedule = "DirtyCpu")]
pub fn my_lengthy_work() -> i64 { /* ... */ }
```

**궁합이 좋다는 말의 실체가 이것이다.** Rust 가 Elixir 의 약점(네이티브 성능)을 메우는 것도 있지만, 더 중요한 건 **Rust 가 NIF 라는 위험한 문에서 BEAM 의 핵심 속성을 지켜준다**는 점이다. C 로 같은 일을 하면 그 속성이 사라진다.

**기대효과**

- CPU 집약 연산(암호화, 압축, 파싱, 이미지·오디오 처리)을 BEAM 밖의 성능으로
- 기존 Rust 생태계(수많은 crate)를 그대로 활용
- **크래시 안전성을 잃지 않음** — 이게 C 대비 결정적 차이
- 정적 타입 · 컴파일 타임 검증이 NIF 경계의 실수를 줄임

**대가**

- 빌드 파이프라인에 Rust 툴체인이 들어온다 (크로스 컴파일, 타깃별 프리컴파일 바이너리 관리)
- 여전히 같은 OS 프로세스다 — Rustler 가 막아주는 건 *안전한 Rust* 의 범위이고, `unsafe` 블록이나 FFI 로 부른 C 라이브러리는 그대로 위험하다
- 1ms 규칙과 dirty 스케줄러를 이해하지 못하면 스케줄러 균형이 깨진다

---

# 7. Elixir + Python — 문은 열리지만, 다른 축이 무너진다

2025년 1월, Dashbit(Livebook 팀)이 **Pythonx** 를 발표했다.[^pythonx-blog][^pythonx-repo] 접근이 대담하다 — **CPython 인터프리터를 BEAM 과 같은 OS 프로세스 안에 임베드** 한다.

> "Elixir provides C/C++ interoperability via Erlang NIFs and that's exactly what Pythonx uses to embed Python, which means **the Python interpreter operates in the same OS process as Elixir itself**. By living in the same memory space, passing data between Elixir and Python is cheap. Pythonx ties Python and Erlang garbage collection…"[^pythonx-blog]

여기까지는 Rust 조합과 구조가 같다. 그런데 발표 글 자신이 곧바로 경고를 단다.

> "**Pythonx usage in actual projects must be done with care due to Python's global interpreter lock (GIL).** The GIL prevents multiple threads from executing Python code at the same time, so **calling `Pythonx` from multiple Elixir processes does not provide the concurrency you might expect and thus it can be a source of bottlenecks.**"[^pythonx-blog]

그리고 사용 조건을 명시한다.

> "if you are using this library to integrate with Python, make sure it happens in **a single Elixir process** or that its underlying libraries can deal with concurrent invocation."[^pythonx-blog]

## 7.1 두 조합은 정반대 방향으로 위험하다

여기가 이 글의 두 번째 반전이다. 같은 NIF 문을 통과하지만 **깨지는 속성이 다르다.**

| | Elixir + Rust | Elixir + Python (Pythonx) |
|---|---|---|
| 위협받는 BEAM 속성 | **크래시 격리** (fault isolation) | **동시성** (concurrency) |
| 그 위협을 다루는 방식 | Rustler 가 **막아준다** (safe Rust, panic catch) | GIL 은 **막을 수 없다** — 설계 제약이라 회피만 가능 |
| 권장 사용 형태 | 일반적인 함수 호출, dirty 스케줄러 활용 | **단일 Elixir 프로세스** 로 직렬화 |
| 공식 문서의 톤 | "should never be able to crash the BEAM"[^rustler] | "must be done with care", "source of bottlenecks"[^pythonx-blog] |
| 주 용도 | 성능 핫패스, 네이티브 라이브러리 바인딩 | **Livebook · 스크립트 · 프로토타이핑** (발표 글의 명시적 1차 목표) |

Rust 는 문제를 **해결** 하고, Python 은 문제를 **관리** 한다. Elixir 의 핵심 가치가 "수십만 개의 경량 프로세스를 동시에" 인데, GIL 은 정확히 그 축을 직렬화한다. 발표 글이 Pythonx 의 1차 목표를 "Livebook 워크플로와 스크립트" 라고 못 박은 것은 겸손이 아니라 **정확한 범위 설정** 이다.[^pythonx-blog]

다만 탈출구는 있다. GIL 은 **네이티브 구현으로 내려가면 풀린다.**

> "Packages with CPU-intense functionality, such as `numpy`, have native implementation of many functions and **invoking those releases the GIL**. The GIL is also released when waiting on I/O operations."[^pythonx-blog]

즉 Python 코드가 얇은 접착제 역할만 하고 실제 계산이 numpy/torch 안에서 벌어진다면 병목은 크게 완화된다. 반대로 **순수 파이썬 루프를 여러 Elixir 프로세스에서 부르는 패턴은 최악** 이다.

**기대효과**

- 파이썬 생태계(ML 모델, 데이터 도구, 과학 계산)를 **네트워크 홉 없이** 사용
- 직렬화·프로세스 경계 비용이 없음 — 같은 메모리 공간
- 프로토타이핑 속도: Livebook 안에서 Elixir 셀과 Python 셀을 섞어 쓸 수 있다[^pythonx-blog]
- 마이그레이션 경로: Python 으로 먼저 만들고 핫패스만 Elixir 네이티브로 옮기는 점진 전략이 가능

**대가**

- **GIL** — 동시성 모델의 근본적 충돌
- 같은 프로세스 = 파이썬 쪽 세그폴트가 BEAM 을 죽인다 (NIF 의 일반 위험)
- 파이썬 런타임·의존성이 배포 산출물에 들어온다 (Pythonx 는 `uv` 로 가상환경을 관리한다[^pythonx-repo])

---

# 8. 세 번째 사례 — JVM 은 같은 문제를 *플랫폼 차원* 에서 고치고 있다

BEAM 만 이 문제를 겪는 게 아니다. JVM 의 **JNI(Java Native Interface)** 는 NIF 와 구조적으로 같은 위치에 있다 — 네이티브 코드를 같은 프로세스에 링크해 부르고, 잘못되면 런타임 전체가 죽는다.

흥미로운 건 **해결 방향이 BEAM 진영과 다르다** 는 점이다.

## 8.1 Panama — JNI 를 대체하는 공식 API

Oracle 공식 문서는 FFM(Foreign Function & Memory) API 를 이렇게 소개한다.

> "This API enables Java programs to call native libraries and process native data **without the brittleness and danger of JNI**."[^ffmdoc]

FFM API 는 **JEP 454** 로 **JDK 22 에서 정식(final)** 이 됐다.[^jep454] 프리뷰로는 JDK 19(JEP 424) → 20(JEP 434) → 21(JEP 442) 을 거쳤다.[^jep454]

## 8.2 그리고 JNI 자체를 제약하기 시작했다

여기가 진짜 중요한 대목이다. **JEP 472 "Prepare to Restrict the Use of JNI"** 가 **JDK 24 에 반영** 됐다.[^jep472] 목표를 원문 그대로 옮기면:

> "Prepare the Java ecosystem for a future release that **disallows interoperation with native code by default**, whether via JNI or the FFM API. As of that release, application developers will have to **explicitly enable** the use of JNI and the FFM API at startup."[^jep472]

단계도 명시돼 있다.

> "In JDK 24, we will restrict the loading and linking steps in JNI so that they also cause a **warning** to be issued at run time by default. … We will strengthen the effect of native access restrictions over time. Rather than issue warnings, **a future JDK release will throw exceptions by default** when Java code uses JNI or the FFM API to load and link native libraries."[^jep472]

이 모든 것의 명분은 한 단어다 — **integrity by default**. JEP 472 는 이것이 `sun.misc.Unsafe` 메모리 접근 제거(JEP 471), 에이전트 동적 로딩 제한(JEP 451)과 함께 가는 **장기 조율 작업** 이라고 밝힌다.[^jep472]

그리고 권한 부여의 주체를 못 박는다.

> "Under the policy of integrity by default, it is **the application developer** (or perhaps deployer …) **who enables native access, not library developers.**"[^jep472]

`--enable-native-access` 로 켜야 하고, 클래스패스 전체에 여는 `ALL-UNNAMED` 보다 **모듈 단위로 좁히라** 고 권고한다.[^jep472]

## 8.3 세 플랫폼을 나란히 놓으면

| | BEAM — NIF | JVM — JNI | JVM — FFM (Panama) |
|---|---|---|---|
| 실패 시 | **VM 전체 크래시**[^erlnif] | JVM 크래시 | 경계 검사·Arena 로 상당 부분 완화[^ffmdoc] |
| 공식 문서의 태도 | "Use with **extreme care**"[^erlnif] | 대체 대상으로 지정[^jep454] | **권장 대안**[^jep472] |
| 권한 모델 | 없음 (로드하면 끝) | JDK 24 부터 **경고**, 이후 예외[^jep472] | **restricted methods + 명시적 opt-in**[^jep472] |
| 완화 주체 | **커뮤니티** (Rustler 같은 라이브러리) | — | **플랫폼 자신** |
| 스케줄러 배려 | dirty NIF 로 분리[^erlnif] | 별도 개념 없음 | 별도 개념 없음 |

읽어낼 수 있는 대비가 선명하다.

- **BEAM 은 이 문제를 언어 선택으로 푼다.** "NIF 는 위험하다" 고 경고하고, 안전하게 쓰고 싶으면 **Rust 를 고르라** 는 것이 사실상의 답이다. 플랫폼은 문을 그대로 두고, 커뮤니티가 안전한 문고리(Rustler)를 만들었다.
- **JVM 은 이 문제를 플랫폼 정책으로 푼다.** 더 안전한 API(FFM)를 새로 만들고, 옛 문(JNI)에 경고를 붙이고, 결국 **기본값을 "금지" 로 바꾸겠다** 고 예고했다.

어느 쪽이 낫다기보다, **BEAM 쪽은 여전히 개발자의 선택에 의존한다** 는 점을 인식하는 게 실무적으로 중요하다. Elixir 에는 아직 `--enable-native-access` 같은 게 없다. NIF 를 로드하는 순간 격리는 사라지고, 그것을 막아줄 플랫폼 장치는 없다. Rustler 를 쓰는 것이 **규율** 인 이유다.

## 8.4 그래서 Java + C/C++ 조합의 기대효과는

**기대효과**

- 기존 C/C++ 자산(수십 년치 라이브러리)을 JVM 에서 직접 사용
- FFM 이후로는 **JNI 보일러플레이트(헤더 생성, 수동 참조 관리)가 사라진다** — 순수 자바 코드로 네이티브 함수를 바인딩
- `MemorySegment`/`Arena` 로 **네이티브 메모리의 수명을 명시적으로 관리** — JNI 시절의 누수·해제 실수를 구조적으로 줄임
- 벡터화·SIMD·GPU 라이브러리 등 JVM 밖 성능에 접근

**대가**

- 여전히 같은 프로세스 — 네이티브 쪽 세그폴트는 JVM 을 죽인다
- **JDK 24+ 에서는 경고, 향후 예외** — 배포 옵션(`--enable-native-access`) 관리가 운영 항목으로 들어온다[^jep472]
- 크로스 플랫폼 빌드/배포 부담은 Rustler 조합과 동일

## 8.5 네 조합을 한 표로

| 조합 | 안전 장치 | 주 위험 | 성숙도 |
|---|---|---|---|
| **Elixir + Rust (Rustler)** | 언어 수준 메모리 안전 + panic catch[^rustler] | `unsafe`/FFI 로 부른 C 는 그대로 위험 | 성숙, 사실상 표준 |
| **Elixir + Python (Pythonx)** | 없음 — **회피**(단일 프로세스)만 가능[^pythonx-blog] | **GIL 로 동시성 붕괴** | 2025년 등장, 목표 범위가 명시적으로 좁음 |
| **Java + C/C++ (JNI)** | 없음 | 크래시·누수, **향후 기본 금지 예정**[^jep472] | 레거시 |
| **Java + C/C++ (FFM)** | restricted methods + opt-in + Arena[^jep472][^ffmdoc] | 같은 프로세스라는 근본 한계 | JDK 22 정식[^jep454] |

---

# 9. 그래서 무엇을 골라야 하나

세 가지 선택지를 축으로 정리하면 이렇다.

| 상황 | 권장 | 이유 |
|---|---|---|
| 성능 핫패스, 라이브러리 바인딩 | **Rust (Rustler)** | 안전성을 지키면서 네이티브 속도 |
| 파이썬에만 있는 모델·도구를 **가끔** 호출 | **Pythonx** (단일 프로세스로) | 통합 비용이 가장 낮음 |
| 파이썬 워크로드를 **높은 동시성** 으로 | **프로세스 분리** (Port · gRPC · 별도 서비스) | GIL 을 프로세스 격리로 우회 |
| 수치 연산·ML 을 상시 운영 | **Nx 생태계 검토** | BEAM 네이티브, GIL 없음 |

마지막 줄이 최근 흐름이다.

---

# 10. 최신 트렌드 (2025–2026)

**① Elixir 가 점진적 타입 언어가 됐다.** 2026년 6월 3일 **Elixir v1.20** 이 릴리스되며 "now a gradually typed language" 를 선언했다. 타입 주석 없이 모든 Elixir 프로그램에 대해 타입 추론과 검사를 수행하고, 실행되면 반드시 실패하는 "verified bugs" 와 죽은 코드를 보고한다.[^elixir120] 다음 단계는 타입 있는 구조체(v1.21, 2026년 11월 예정)와 타입 시그니처(v1.22, 2027년 5월 예정)다.[^inference15]

하이브리드 관점에서 이게 중요한 이유는, **NIF 경계가 원래 타입 검증의 사각지대** 이기 때문이다. Elixir 쪽 타입 정보가 강해질수록 "이 값이 Rust NIF 로 넘어가도 되는가" 를 컴파일 타임에 더 많이 잡을 수 있다.

**② 네이티브 대안이 자리를 잡았다.** Nx(수치 연산)[^nx] · Axon · Bumblebee(허깅페이스 모델) · Explorer(데이터프레임) · EXLA 는 이제 "파이썬 대신" 을 진지하게 검토할 수 있는 수준이다. State of Elixir 2025 커뮤니티 설문에서 **Nx 사용률은 32.8%** 로 집계됐다.[^survey2025]

**③ FLAME — 서버리스를 BEAM 안으로.** Chris McCord(Phoenix)의 FLAME 은 애플리케이션의 일부 모듈을 **수명이 짧은 인프라에서 탄력적으로 실행** 한다.[^flame] ML 추론처럼 무겁고 간헐적인 워크로드를 별도 서버리스 스택 없이 처리하려는 접근이다. 같은 설문에서 **"서버리스 사용이 드물다"** 는 결과가 나왔는데, 해설은 이를 "개발자들이 BEAM 의 탄력적 동시성·확장·복원력·격리를 활용해 서버리스를 선택할 이유를 제거하고 있다" 고 읽는다.[^survey2025]

**④ 커뮤니티의 요구는 "네이티브 AI 도구".** 같은 설문의 자유 응답에서는 Elixir 네이티브 AI 프레임워크(에이전트, MCP 서버)에 대한 요구가 두드러진다. 동시에 LSP 안정성·컴파일 속도 같은 기초 도구에 대한 불만도 크다.[^survey2025] 즉 **하이브리드는 과도기 전략** 이라는 인식이 공유되고 있다.

---

# 11. 세 주제를 잇는 하나의 잣대

핫 업그레이드와 하이브리드는 별개의 주제처럼 보이지만, 판단 기준이 같다.

> **BEAM 의 격리를 지키는가, 포기하는가.**

- **파드 교체** 는 BEAM *바깥* 에서 격리를 다시 얻는 방법이다. 노드가 통째로 죽어도 다른 파드가 산다. 대신 인메모리 상태를 포기한다.
- **핫 업그레이드** 는 BEAM *안* 의 연속성을 지키는 대신, 전이 검증이라는 비용과 노드 전체가 이상 상태에 빠질 위험을 진다.
- **NIF(Rust/Python)** 는 BEAM *안* 의 격리를 포기하는 지점이다. Rust 는 그 포기를 되돌려주고, Python 은 되돌려주지 못한 채 다른 축(동시성)까지 가져간다.

Elixir 공식 문서가 핫 업그레이드를 기본에서 빼고 언어 무관 배포 기법을 권한 것,[^mixrelease] Rustler 가 "should never be able to crash the BEAM" 을 첫 문장에 둔 것,[^rustler] Pythonx 발표 글이 "must be done with care" 를 곧바로 붙인 것[^pythonx-blog] — 셋 다 같은 원칙의 다른 표현이다.

**기능이 있다는 것과 그 기능을 기본값으로 두는 것은 다른 문제다.** 좋은 플랫폼은 그 둘을 구분한다.

---

## References

**Erlang/OTP · Elixir 공식**

[^mixrelease]: `mix release` — Mix 공식 문서, "Hot Code Upgrades" 절. <https://hexdocs.pm/mix/Mix.Tasks.Release.html>
[^systools]: `systools` — SASL 공식 문서(`make_relup/3`). <https://www.erlang.org/doc/apps/sasl/systools.html>
[^erlnif]: `erl_nif` — ERTS 공식 문서, 상단 Warning 및 Long-running NIFs / Dirty NIF 절. <https://www.erlang.org/doc/apps/erts/erl_nif.html>
[^erlnifsys]: NIFs — Erlang System Documentation. <https://www.erlang.org/docs/29/system/nif.html>
[^issue8612]: elixir-lang/elixir issue #8612 — Releases (José Valim 의 핫 코드 업그레이드 제외 결정). <https://github.com/elixir-lang/elixir/issues/8612>
[^elixir120]: *Elixir v1.20 released: now a gradually typed language* (2026-06-03). <https://elixir-lang.org/blog/2026/06/03/elixir-v1-20-0-released/>
[^inference15]: José Valim, *Type inference of all constructs and the next 15 months* (2026-01-09). <https://elixir-lang.org/blog/2026/01/09/type-inference-of-all-and-next-15/>
[^nx]: Nx 공식 문서. <https://hexdocs.pm/nx/Nx.html>

**Kubernetes 공식**

[^k8sdeploy]: *Deployments* — Rolling Update 전략과 `maxUnavailable` / `maxSurge`. <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>

**JVM 네이티브 인터페이스 — 1차 자료**

[^jep454]: JEP 454: Foreign Function & Memory API — Status: Closed/Delivered, Release **22**. <https://openjdk.org/jeps/454>
[^jep472]: JEP 472: Prepare to Restrict the Use of JNI — Status: Closed/Delivered, Release **24**. <https://openjdk.org/jeps/472>
[^ffmdoc]: Oracle, *Foreign Function and Memory API* (JDK 22 코어 라이브러리 가이드). <https://docs.oracle.com/en/java/javase/22/core/foreign-function-and-memory-api.html>

**하이브리드 — 1차 자료**

[^rustler]: Rustler — 공식 저장소 및 API 문서("safe Rust code", Safety 절). <https://github.com/rusterlium/rustler> · <https://docs.rs/rustler/latest/rustler/>
[^rustlernif]: `#[nif]` 매크로 — dirty 스케줄러 지정. <https://docs.rs/rustler/latest/rustler/attr.nif.html>
[^pythonx-blog]: Dashbit, *Embedding Python in Elixir, it's Fine* (Pythonx 발표 글, GIL 주의사항 포함). <https://dashbit.co/blog/running-python-in-elixir-its-fine>
[^pythonx-repo]: livebook-dev/pythonx — 저장소(2025). <https://github.com/livebook-dev/pythonx>
[^flame]: FLAME — phoenixframework/flame. <https://github.com/phoenixframework/flame>

**커뮤니티 조사 (2차 자료 — 표본 기반 설문이므로 경향 참고용)**

[^survey2025]: *State of Elixir 2025 Results — Community Survey*, Elixir Hub. <https://elixir-hub.com/surveys/2025>
