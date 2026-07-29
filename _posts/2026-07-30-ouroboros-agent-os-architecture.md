---
layout: post
title: "*Agent OS* 는 무엇을 커널이라 부르는가 — *Ouroboros* 의 3층 구조와 *결정론적 실행* 의 근거"
date: 2026-07-30 01:00:00 +0900
categories: [architecture, ai-agent, event-sourcing]
tags: [Ouroboros, AgentOS, EventSourcing, Determinism, Provenance, MCP, ControlPlane, IOJournal, RFC]
---

# 한 장의 그림에서 시작한다

```text
+-------------------------------------------------------------------+
|                Installable UserLevel Programs                      |
|  github-pr-ops   merge-assistant   jira-sync   linear-triage       |
|  slack-incident  release-coordinator  customer-debugger  ...       |
+-------------------------------+-----------------------------------+
                                | plugin contract / declared scopes
                                v
+-------------------------------------------------------------------+
|                First-party UserLevel Programs                      |
|  ooo auto     ooo run     ooo pm     ooo review?     ...           |
+-------------------------------+-----------------------------------+
                                | stable OS primitives
                                v
+-------------------------------------------------------------------+
|                     Ouroboros Core / OS                            |
|  Seed  Ledger  State  Runtime  MCP                                 |
|  Provenance  Safety Boundaries  Progress/Status  Handoff           |
+-------------------------------------------------------------------+
```

이 그림은 감상용 다이어그램이 아니다. Ouroboros 저장소의 `docs/rfc/userlevel-plugins.md`, **"Layer Model"** 절에 있는 그림이고, 그 RFC 는 **2026-05-07 Accepted** 상태로 못 박혀 있다.[^rfc]

운영체제 계층도와 똑같은 모양이다. 맨 아래가 커널, 가운데가 기본 유저랜드, 맨 위가 서드파티 프로그램. 그리고 층 사이에는 경계 계약이 하나씩 있다 — `stable OS primitives`, `plugin contract / declared scopes`.

이 글이 답하려는 것은 두 가지다.

1. 여기서 **"OS" 가 비유인지 아닌지**
2. 이 구조 위에서 에이전트 실행이 **어떻게 결정론적이고 증거 기반이 되는가**

둘 다 감상이 아니라 **저장소의 문서와 소스에 적힌 것만으로** 답한다.

> **먼저 밝혀둘 것**: Ouroboros 는 필자의 프로젝트가 아니다. [Q00](https://github.com/Q00) 이 MIT 라이선스로 공개한 오픈소스이고, 2026-07-30 기준 GitHub 스타 5,197 개, 커밋 이력상 Q00(482) · shaun0927(100) · JunghwanNA(58) 등이 참여하고 있다.[^repo] 이 글은 그 프로젝트의 **구조 분석**이며, 모든 인용은 업스트림 저장소를 가리킨다.
>
> **기준 버전**: 이 글은 **v0.50.6**(2026-07-24 릴리스, 커밋 `4e8ba60d`) 및 그 시점의 `main` 문서를 기준으로 한다. 특히 5절의 RFC 구현 상태 매트릭스는 **시점 의존적**이므로, 이후 버전에서는 달라져 있을 수 있다. (버전 근거는 git 태그·GitHub Releases·PyPI `ouroboros-ai` 세 곳이 일치. 저장소의 `CHANGELOG.md` 는 최신 버전 섹션이 `[0.41.0]` 에 멈춰 있어 버전 확인용으로 적합하지 않다.)

---

# 1. 이 그림의 진짜 주장은 "플러그인 층은 배관이다"

보통 이런 3층 그림은 "생태계를 키우자"는 뜻으로 읽힌다. 이 RFC 는 정확히 반대를 말한다.

> "The plugin layer exists to **keep core small**, not to grow ecosystem surface area."[^rfc]

그리고 성공 지표에서 플러그인 개수를 명시적으로 제외한다.

> "We do not pursue plugin count, marketplace dynamics, or 'ecosystem health' as success metrics. The success metric for Ouroboros remains the strength of the spec-first discipline (Interview / Seed / Evolve / Provenance) and the quality of execution under that discipline."[^rfc]

> "The plugin layer is **plumbing**. It exists invisibly to prevent core bloat. **It is not a product surface.**"[^rfc]

즉 맨 위 칸(`github-pr-ops`, `jira-sync` …)은 자랑거리가 아니라 **코어에 들어오지 못하게 막아둔 것들의 보관소** 다. "이건 코어에 넣어야 하나?" 라는 논쟁이 생길 때 참조하라고 만든 문서라고 RFC 스스로 밝힌다.[^rfc]

가운데 층의 설명도 같은 톤이다 — first-party 프로그램조차 "core 위의 프로그램이지 core 자체가 아니다"(`still programs above core rather than core itself`).[^rfc]

이 관점에서 보면 그림의 두 화살표가 다르게 읽힌다. 저것은 기능 흐름이 아니라 **무엇이 커널에 들어올 수 없는지를 정하는 두 개의 방화선** 이다.

---

# 2. "OS" 는 비유가 아니라 *잠긴 어휘* 다

대부분의 "AI Agent OS" 는 마케팅 표현이다. Ouroboros 가 다른 지점은, 커널 용어를 문서로 고정해 **PR 리뷰 기준으로 쓴다**는 것이다. `docs/contributing/agent-os-kernel-terminology.md` 의 첫 문단이 목적을 직접 말한다.

> "This document **locks** the kernel-level vocabulary for the Agent OS workstream. It exists so review comments and stacked PRs use the same words for runtime context, control decisions, transport, and journaled observability."[^kernel]

정의된 여섯 용어는 문서 자신이 OS 구성요소에 대응시킨다.[^kernel]

| 용어 | 계층 | 문서가 붙인 OS 대응 |
|---|---|---|
| `AgentRuntimeContext` | 런타임 컨텍스트 | process execution envelope |
| `ControlPlane` | 커널 제어 계층 | kernel control layer |
| `ControlContract` | 제어 불변식 | **syscall contract** |
| `Directive` | 제어 어휘 | command vocabulary |
| `ControlBus` | 제어 전송 | one local delivery mechanism |
| `IOJournal` | 관측 저널 | **replayable black box** |

눈여겨볼 규칙이 하나 있다. **"`ControlBus` 를 최상위 개념으로 쓰지 말라"**(Do not use `ControlBus` as the top-level concept).[^kernel] 명명 취향이 아니다. 전송과 제어 평면을 같은 이름으로 부르면 *"메시지가 전달됐다"* 와 *"결정이 내려졌다"* 가 구분되지 않는다. 그 구분이 무너지면 뒤에 나올 결정론이 성립하지 않는다.

`Directive` 어휘도 작고 고정돼 있다 — `CONTINUE`, `RETRY`, `WAIT`, `CANCEL`, `CONVERGE`.[^kernel] 명령 집합이 유한하다는 것이 결정론의 첫 조건이다.

---

# 3. 결정론은 선언이 아니라 *불변식* 으로 만들어진다

"우리 시스템은 결정론적입니다" 는 아무것도 보장하지 않는다. 검증 가능한 것은 불변식뿐이다. 커널 문서는 여섯 개를 나열한다.[^kernel]

1. **Terminal directives are terminal** — `CANCEL`/`CONVERGE` 이후에는 같은 실행에 새 작업을 시작할 수 없다. 새 contract ID 할당이나 명시적 재실행이 있어야 한다.
2. **Retry belongs to the control contract** — `RETRY` 는 재시도 예산을 지키고, **왜 재시도했는지 설명할 수 있을 만큼의 맥락과 함께 저널에 남아야** 한다.
3. **`WAIT` means no forward progress** — 대기 중에는 전진하지 않는다.
4. **Resume must preserve the original execution envelope** — 런타임 백엔드, LLM 백엔드, 작업 디렉터리, MCP 브리지 권한, 안전 옵션이 **조용히 바뀌면 안 된다**.
5. **Every durable control decision must be reconstructable from the event store** — "`ControlBus` 를 통한 반응형 전달은 영속화의 대체재가 아니다."
6. **External I/O that influences a decision must be reconstructable from the `IOJournal`** — 가능하면 요청/응답이 짝지어진 이벤트로.

한 문장으로 압축하면 이렇게 된다.

> **결정에 영향을 준 모든 것은 나중에 재구성될 수 있어야 한다.**

4번이 특히 실전적이다. 실행을 중단했다 재개할 때 모델 티어나 작업 디렉터리가 슬쩍 바뀌면 같은 입력에 다른 출력이 나오는데, 그 차이는 로그 어디에도 "바뀌었다"고 적히지 않는다. 문서가 **"resume drift 는 CLI 다듬기 이슈가 아니라 control-contract 버그"** 라고 규정한 것은,[^kernel] 재현 불가능성을 기능 결함이 아니라 **계약 위반** 으로 취급하겠다는 선언이다.

---

# 4. 증거 기반의 실제 구현

## 4.1 append-only 이벤트 스토어

상태 계층은 이벤트 소싱이다. 아키텍처 문서는 State Layer 를 "SQLite event store with append-only writes, Full replay capability" 로 설명하고,[^arch] 코드 주석도 같은 말을 반복한다. 트랜잭션 롤백 경로에조차 이렇게 적혀 있다.

> `events remain in the store (event sourcing is append-only)` — `src/ouroboros/persistence/uow.py`[^uow]

**작업이 실패해도 "실패했다는 사실" 은 지워지지 않는다.** 애플리케이션 상태의 모든 변경을 이벤트 시퀀스로 남겨 언제든 재생으로 복원한다는, 이벤트 소싱의 표준 정의를 그대로 따른다.[^fowler]

## 4.2 파생 상태를 저장하지 않는다

증거 기반 설계가 가장 자주 깨지는 곳은 **파생 데이터 캐싱** 이다. 요약본을 따로 저장하면 원본과 어긋나는 순간 무엇이 진실인지 알 수 없다.

계보(lineage) 모듈은 이 문제를 규칙으로 못 박는다.

> "All models are frozen (immutable). … **OntologyLineage is a read model projected from events — never persisted directly, always reconstructed via `LineageProjector`.**" — `src/ouroboros/core/lineage.py`[^lineage]

그림의 `Provenance` 칸이 실제로 무엇인지 이 한 줄이 말해준다. 출처 추적은 별도 테이블이 아니라 **이벤트 로그의 투영(projection)** 이다. 원본이 하나뿐이라 어긋날 수가 없다.

## 4.3 스키마에 버전이 있고, 그 버전이 계약이다

이벤트를 남기는 것만으로는 부족하다. 스키마가 바뀌면 과거 이벤트를 잘못 읽게 된다. 모든 페이로드에 `event_version` 이 들어가고, 안정성 보장이 문서화돼 있다.

> "**Stability guarantee:** fields documented under a given version will not be removed or renamed within that version."[^events]

소비자 행동까지 규정한다 — 지원하지 않는 버전을 만나면 **조용히 오해석하지 말고 명시적으로 실패하라**.[^events] 구현도 일관적이다. `event_version` 은 별도 컬럼이 아니라 `payload` JSON 안에 사는데, 문서는 그 이유를 "스키마 마이그레이션을 피하고 변경을 가산적으로 유지하기 위해" 라고 밝힌다.[^events] 감사 로그를 마이그레이션하지 않겠다는 것 — append-only 원칙과 같은 결이다.

---

# 5. 이 글에서 가장 인상적이었던 것: 프로젝트가 자기 자신에게 증거를 요구한다

지금까지는 "이 시스템이 실행을 어떻게 기록하는가" 였다. 더 흥미로운 건 **문서가 문서 자신의 구현 여부를 기록하는 방식** 이다.

RFC 는 "Accepted" 의 의미를 먼저 좁힌다.

> "'Accepted' means the **design** is locked; it does **not** mean every artifact named below already exists in the repository. This RFC is the **target contract** … readers SHOULD interpret unbuilt artifacts as RFC-2119 **MUST** (the implementation must conform when it lands), **not as a description of `main` today**."[^rfc]

그리고 아티팩트별 구현 상태를 표로 남긴다. RFC 병합 시점 기준이다.[^rfc]

| 아티팩트 | 상태 |
|---|---|
| 플러그인 매니페스트 스키마 (`schemas/0.1/`) | **Shipped upstream** |
| `src/ouroboros/plugin/manifest.py` (로더) | Not yet present |
| `src/ouroboros/plugin/firewall.py:invoke_plugin` (호출 계약) | Not yet present |
| `ooo plugin {add,install,trust,disable,remove}` | Not yet present |
| `~/.ouroboros/plugins.lock` + trust store | Not yet present |
| `github-pr-ops` E2E 계약 증명 | Not yet present |

문서 안의 경로들이 **현재 경로가 아니라 목표 경로** 임도 명시한다("target paths, not current paths, unless this matrix marks them as shipped").[^rfc]

같은 규율이 `ControlJournal` 문서에도 나온다.

> "The contract is deliberately narrowed to **what current HEAD actually implements** plus the forward semantics that any future producer or subscriber must honor. **It does not retroactively claim a publish pipeline that does not exist yet**; it locks the direction so that the publish pipeline, when it lands, has only one shape it can legally take."[^journal]

이것이 이 프로젝트의 진짜 특징이라고 생각한다. 아키텍처 문서가 **희망과 현실을 같은 네모로 그리지 않는다.** 그림에서 `ooo review?` 에만 물음표가 붙어 있는 것도 우연이 아니다 — 실제로 `src/ouroboros/cli/main.py` 의 서브커맨드 등록부에는 `auto`, `run`, `pm` 은 있지만 `review` 는 없다.[^cli]

```python
app.add_typer(auto.app, name="auto")
app.add_typer(run.app, name="run")
...
app.add_typer(pm.app, name="pm")
```

그림 한 칸의 물음표 하나가 코드와 일치한다. 다이어그램에 대해 이보다 좋은 신호는 드물다.

참고로 그림의 `Ledger` · `Provenance` 는 RFC 본문에서 **"durable substrate (ledger, provenance, seed history)"** 로 함께 언급되며, 이 프로젝트의 락인이 플러그인 개수가 아니라 이 기반에서 나온다고 적혀 있다.[^rfc]

---

# 6. 선언형 권한 모델 4종 비교 — Android · Kubernetes RBAC · 브라우저 확장 · Ouroboros

`plugin contract / declared scopes` 라는 화살표는 새로운 발명이 아니다. 같은 문제를 먼저 푼 시스템이 최소 셋 있다. **무엇을 할 수 있는지 미리 선언하게 하고, 선언하지 않은 일은 막는다**는 구조다. 넷을 나란히 놓으면 Ouroboros 가 어디를 빌려왔고 어디서 갈라지는지가 분명해진다.

먼저 각 시스템이 권한을 선언하는 자리다.

- **Android** — 앱 매니페스트에 `<uses-permission>` 으로 선언한다. 위험(dangerous) 권한은 설치 시점이 아니라 **런타임에 사용자에게 요청** 해야 하고, 사용자는 언제든 설정에서 취소할 수 있다.[^android]
- **Kubernetes RBAC** — `Role`/`ClusterRole` 에 규칙을 쓰고 `RoleBinding` 으로 주체에 묶는다. 권한을 받는 쪽이 선언하는 게 아니라 **클러스터 관리자가 정의** 한다.[^k8s]
- **브라우저 확장** — `manifest.json` 의 `permissions` 배열에 선언한다. 선언하지 않은 API 는 호출할 수 없고, 일부는 사용자 동의를 요구한다.[^chrome][^mdn]
- **Ouroboros** — 플러그인 매니페스트에 `permissions` 와 `capabilities` 를 **필수 필드로** 선언한다. RFC 기준 매니페스트는 필수 8개 + 선택 2개이며, 선택 필드인 `audit` 은 기본값으로 `plugin.invoked` · `plugin.permission_used` · `plugin.completed` · `plugin.failed` 를 갖는다.[^rfc]

## 6.1 축별 비교

| 축 | Android | K8s RBAC | 브라우저 확장 | Ouroboros |
|---|---|---|---|---|
| 선언 위치 | 앱 매니페스트 | Role/ClusterRole (클러스터 리소스) | `manifest.json` | 플러그인 매니페스트 |
| 승인 주체 | **최종 사용자** | **클러스터 관리자** | **최종 사용자** | **최종 사용자** (`ooo plugin trust`) |
| 승인 시점 | 런타임 요청 (dangerous) | 사전 정의 | 설치 시 + optional | `discovered → installed → trusted` |
| 기본 정책 | 미선언이면 불가 | **순수 가산, deny 규칙 없음** | 미선언이면 불가 | 미신뢰 `required` 권한이면 호출 거부 |
| 강제 지점 | OS 프레임워크 (프로세스/UID 격리) | API server 인가 모듈 | 브라우저 런타임 (프로세스 격리) | **`firewall.py:invoke_plugin` 단일 래퍼** |
| 거부의 흔적 | 앱이 콜백으로 처리 | API 403 (+감사 로그 설정 시) | API 호출 실패 | **`plugin.failed`(`status="blocked"`) 이벤트** |
| 권한 *사용* 기록 | Privacy Dashboard 등 사용자 UI | 감사 로그를 켜야 함 | 제한적 | **`plugin.permission_used` 가 기본 감사 이벤트** |

## 6.2 Ouroboros 가 갈라지는 세 지점

**(1) 강제 지점이 함수 하나로 좁혀져 있다.**
RFC 는 "Every UserLevel plugin command flows through **one wrapper** — `src/ouroboros/plugin/firewall.py:invoke_plugin`" 라고 못 박고, 그 래퍼의 책임 순서까지 규정한다 — ① 비활성/설치 주체 다이제스트 검증 ② 사전 신뢰 검사 ③ 취소 검사.[^rfc] Android 와 브라우저는 강제 지점이 OS·런타임 전반에 흩어져 있고, K8s 는 API server 라는 넓은 관문에서 처리한다. Ouroboros 는 그것을 **한 함수의 진입 검사** 로 축소했다.

**(2) 거부가 "일어나지 않은 일" 로 남지 않는다.**
가장 인상적인 규정은 이것이다. `required: true` 권한이 신뢰되지 않았을 때, 래퍼는 `plugin.failed` 를 `result.status="blocked"` 로 내보내면서 **부족한 스코프 이름과 실행해야 할 정확한 `ooo plugin trust ...` 명령을 메시지에 담는다**. 그리고 이렇게 덧붙인다.

> "**No `plugin.invoked` is emitted** — the plugin never started."[^rfc]

즉 *차단된 호출* 과 *시작했다가 실패한 호출* 이 이벤트 수준에서 구분된다. K8s 도 403 을 남기지만 그것을 영구 기록으로 남기려면 감사 로깅을 따로 켜야 하고,[^k8sauthz] Android·브라우저에서 거부의 기록은 대체로 애플리케이션 코드의 성실성에 달려 있다.

**(3) 권한의 *사용* 이 기본 감사 이벤트다.**
`plugin.permission_used` 가 매니페스트 `audit` 필드의 **기본값에 포함** 돼 있다.[^rfc] 권한을 *부여* 한 기록과 권한을 *실제로 쓴* 기록은 다른 문제인데, 후자를 기본값으로 두는 설계는 드물다. Android 12 이후의 Privacy Dashboard 가 비슷한 목적을 갖지만 그쪽은 사용자 대상 UI 이고, 여기서는 **재생 가능한 이벤트 스트림의 일부** 다.

이 세 가지는 앞 절의 5·6번 불변식과 정확히 같은 방향이다 — *결정에 영향을 준 것은 나중에 재구성 가능해야 한다.*

## 6.3 반대로, Ouroboros 가 명백히 약한 지점

비교를 공정하게 하려면 이쪽도 적어야 한다.

- **격리 강도가 다르다.** Android 의 권한은 커널의 UID/프로세스 격리 위에 서 있고, 브라우저 확장도 프로세스 경계로 보호된다. 반면 `invoke_plugin` 은 **같은 프로세스 안의 파이썬 래퍼** 다. 악의적 플러그인이 파이썬 런타임 수준에서 우회를 시도하면 함수 하나가 막아줄 수 있는 범위는 제한적이다. 이 층은 **사고 방지(safety)** 에 가깝지 적대적 공격 방어(security)와 같은 급으로 두면 안 된다.
- **K8s 의 "deny 규칙 없음" 은 단순함의 대가로 얻은 것이다.** 공식 문서는 "Permissions are purely additive (there are no 'deny' rules)" 라고 명시한다.[^k8s] 규칙이 가산적이면 "이 주체가 무엇을 할 수 있나" 를 합집합으로 계산할 수 있어 추론이 쉽다. Ouroboros 는 `disabled` 상태에서 required 권한을 신뢰 테이블에서 **제거(strip)** 하는 방식을 쓰는데,[^rfc] 이는 표현력이 크지만 상태 조합이 늘어난다.
- **대부분 아직 구현되지 않았다.** 5절의 매트릭스대로 `firewall.py`, 매니페스트 로더, `ooo plugin` CLI, 신뢰 저장소는 RFC 병합 시점에 전부 "Not yet present" 였다.[^rfc] Android·K8s·브라우저의 권한 모델은 수억 대 기기와 수많은 클러스터에서 검증된 것들이고, 이쪽은 **설계 문서가 검증된 단계** 다. 같은 표에 놓고 비교하되 성숙도는 같지 않다.

---

# 7. 이 설계가 막는 사고 — 운영 현장의 두 사례

추상적으로 들릴 수 있으니, 필자가 운영 중인 K3s 클러스터에서 최근 겪은 두 사고에 대응시켜 본다. 둘 다 **결정의 근거가 재구성 불가능해서** 벌어진 일이다.

**사고 1 — 근거가 주석에만 살아 있었다.** 로그 수집기(Logstash)의 JVM 힙을 2GB → 1GB 로 줄이려 했다. 처리량이 초당 3건 미만이었으니 합리적으로 보였다. 그런데 설정 파일에 주석이 있었다.

> `2026-07-24: heap 1g→2g. 매핑 오류로 400 폭주 → 재시도가 1g 힙을 소진 → OOM → CrashLoop(35회)`

닷새 전 장애의 대응값이었다. 되돌렸다면 같은 장애를 재현했을 것이다. 이 지식이 살아남은 건 **누군가 주석에 적어뒀기 때문** 이지 시스템이 보장한 게 아니다.

Ouroboros 의 2번 불변식 — "`RETRY` 는 **왜 재시도했는지 설명할 수 있을 만큼의 맥락과 함께** 저널에 남아야 한다" — 이 겨냥하는 실패가 정확히 이것이다. 결정의 *이유* 를 사람의 성실성이 아니라 계약에 맡긴다.

**사고 2 — 실패가 관측되지 않았다.** 백업이 **63회 연속 실패** 하는 동안 아무도 몰랐다. 알림 파이프라인은 살아 있었고 규칙도 132개 있었지만, 정작 그 도구의 메트릭은 수집조차 되지 않고 있었다. 기록되지 않은 실패는 일어나지 않은 일과 구분되지 않는다.

5번 불변식 — "모든 영속적 제어 결정은 이벤트 스토어에서 재구성 가능해야 한다. **반응형 전달은 영속화의 대체재가 아니다**" — 는 이 함정에 정확히 이름을 붙인다. *알림이 갔다* 와 *기록이 남았다* 는 다른 문제다.

---

# 8. 한계와, 이 글이 검증하지 못한 것

- **성능·비용 수치는 다루지 않았다.** 이 글은 구조와 계약만 본다. 실행 속도나 토큰 절감률 같은 주장은 중립적 재현 결과 없이는 인용하지 않는 편이 낫다.
- **불변식은 문서이지 강제가 아니다.** 커널 용어 문서는 "PR 리뷰 가이드" 로 쓰여 있다. 이를 CI 에서 기계적으로 강제하는 장치가 있는지는 확인하지 못했다. 문서로만 존재하는 규칙은 사람이 바쁠 때 가장 먼저 무너진다.
- **플러그인 층은 대부분 미구현이다.** 위 표대로 매니페스트 스키마 외에는 RFC 병합 시점에 "Not yet present" 였다. 필자는 그 이후 진척도를 개별 이슈까지 추적하지 않았다.
- **결정론에는 상한이 있다.** 이벤트 재생으로 복원되는 것은 *결정의 이력* 이지 *LLM 의 출력* 이 아니다. 같은 프롬프트에 같은 응답이 온다는 보장은 이 구조가 주지 않으며, 줄 수도 없다. 이 설계가 주는 것은 **"왜 그렇게 결정했는지 나중에 설명할 수 있다"** 이지 **"언제나 같은 답이 나온다"** 가 아니다. 둘을 혼동하면 안 된다.

---

# 9. 정리

그림의 3층 구조가 말하는 것은 결국 **경계** 다.

- 맨 아래 `Ouroboros Core / OS` 는 바뀌지 않는 것들을 담는다 — 불변 Seed, append-only 이벤트, 고정된 Directive 어휘.
- 가운데 first-party 층은 그 원시타입 위에 서고, 없는 것은 물음표로 표시한다.
- 맨 위 설치형 층은 `plugin contract / declared scopes` 라는 **선언된 권한** 을 통해서만 내려온다. 그리고 그 층의 존재 이유는 확장이 아니라 **코어를 작게 유지하는 것** 이다.

그래서 여기서 "결정론적"의 의미는 이렇게 정리된다.

> 같은 답이 나온다는 뜻이 아니라, **어떤 답이 왜 나왔는지 나중에 재구성할 수 있다**는 뜻이다.

에이전트가 코드를 잘 쓰는 것보다, 에이전트가 내린 결정을 사람이 **나중에 반박할 수 있는 형태로 남기는 것** 이 훨씬 어렵고 훨씬 중요하다. 커널 문서의 여섯 불변식과, 구현 상태를 표로 남기는 RFC 의 태도가 겨냥하는 지점이 정확히 그것이다.

---

## References

**1차 자료 — Ouroboros 저장소 (MIT License, © 2025 Q00)**

[^repo]: 프로젝트 저장소. <https://github.com/Q00/ouroboros> — 스타 수·기여자 커밋 분포는 2026-07-30 기준 `gh repo view` · `git log` 로 확인.
[^rfc]: *RFC: UserLevel Plugin Layer* (Accepted 2026-05-07), `docs/rfc/userlevel-plugins.md`. <https://github.com/Q00/ouroboros/blob/main/docs/rfc/userlevel-plugins.md> — 본문의 Layer Model 다이어그램·구현 상태 매트릭스·"plumbing" 논지의 출처.
[^kernel]: *Agent OS Kernel Terminology*, `docs/contributing/agent-os-kernel-terminology.md`. <https://github.com/Q00/ouroboros/blob/main/docs/contributing/agent-os-kernel-terminology.md>
[^journal]: *ControlJournal Delivery & Outbox Semantics* (Direction locked 2026-05-28), `docs/agentos/control-journal.md`. <https://github.com/Q00/ouroboros/blob/main/docs/agentos/control-journal.md>
[^events]: *Event Payload Schema Reference*, `docs/events.md`. <https://github.com/Q00/ouroboros/blob/main/docs/events.md>
[^arch]: *Ouroboros Architecture*, `docs/architecture.md`. <https://github.com/Q00/ouroboros/blob/main/docs/architecture.md>
[^uow]: `src/ouroboros/persistence/uow.py` — Unit of Work 의 append-only 주석.
[^lineage]: `src/ouroboros/core/lineage.py` — 모듈 독스트링의 read-model projection 규칙.
[^cli]: `src/ouroboros/cli/main.py` — Typer 서브커맨드 등록부.

**외부 공식 자료**

[^fowler]: Martin Fowler, *Event Sourcing*. <https://martinfowler.com/eaaDev/EventSourcing.html>
[^android]: Android Developers, *Permissions on Android*. <https://developer.android.com/guide/topics/permissions/overview>
[^k8s]: Kubernetes, *Using RBAC Authorization* — "Permissions are purely additive (there are no 'deny' rules)". <https://kubernetes.io/docs/reference/access-authn-authz/rbac/>
[^k8sauthz]: Kubernetes, *Authorization*. <https://kubernetes.io/docs/reference/access-authn-authz/authorization/>
[^chrome]: Chrome for Developers, *Declare permissions*. <https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions>
[^mdn]: MDN, *manifest.json — permissions*. <https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/permissions>

- Model Context Protocol 명세 — <https://modelcontextprotocol.io/specification/2025-06-18>
- Pydantic, *Models — Faux Immutability*(`frozen=True` 의 의미와 한계) — <https://docs.pydantic.dev/latest/concepts/models/#faux-immutability>
