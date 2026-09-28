---
layout: post
title: "헤르메스·키로·Claude Code·코덱스 협업 시나리오 — 넷을 한 팀으로 쓰는 법"
date: 2026-09-28 22:53:27 +0900
categories: [ai]
tags: [multi-agent, hermes-agent, kiro, claude-code, codex, orchestration, agent-collaboration]
---

에이전트 넷을 같이 쓰면 가장 먼저 부딪히는 문제는 **누가 무엇을 끝까지 책임지느냐**다.
어느 에이전트가 더 똑똑하냐는 그다음 문제다.
이 글은 우리 집 맥에서 실제로 돌리고 있는 넷을 다룬다.
**Hermes Agent, Kiro, Claude Code, Codex CLI** 다.
넷의 역할을 나누고, 일감 종류별로 **넘겨주기(hand-off) 시나리오** 네 개를 정리했다.

이론 쪽은 전에 따로 썼다.
[조율 패턴]({% post_url 2026-07-23-multi-agent-coordination-patterns %})과
[멀티에이전트가 손해인 경우]({% post_url 2026-07-24-when-multi-agent-is-a-loss %})가 그 글들이다.
하루 동안 벌어진 사고 장면은 [협업 현장기]({% post_url 2026-09-24-agent-collaboration-field-notes %})에 있다.
그래서 이번 글은 *설계도* 쪽에 집중한다.
도구별 기능은 각 공식 문서를 근거로 했다.
"우리 환경에서 관측"이라고 적은 내용은 로컬 로그와 설정 파일에서 확인한 사실이다.
"필자 제안"이라고 적은 내용은 검증된 사실이 아니라 설계 의견이다.

---

## 1. 넷의 자리 — 무엇을 잘하고, 어디에 두나

공식 문서에 적힌 성격부터 정리한다.

| 도구 | 공식 문서가 말하는 핵심 | 이 팀에서 맡는 자리 |
|---|---|---|
| **Hermes Agent** (Nous Research) | `delegate_task` 로 자식 에이전트를 띄운다. 자식은 대화 이력 없이 *새 컨텍스트*로 시작하고, 부모에게는 **최종 요약만** 돌아간다.[^hermes-deleg] ACP 서버로 동작해 다른 호스트와 stdio JSON-RPC 로 붙을 수도 있다.[^hermes-acp] | **허브 / 디스패처 / 최종 검증자** |
| **Kiro** (AWS) | 스펙이 `requirements.md`·`design.md`·`tasks.md` 세 파일로 생긴다. 요구사항 → 설계 → 태스크 3단계를 거치고, 의존성이 없는 태스크는 병렬로 돈다.[^kiro-specs] CLI 는 `--no-interactive` headless 모드를 지원한다.[^kiro-headless] | **스펙 작성자 · 1차 구현자** |
| **Claude Code** (Anthropic) | `-p` 로 비대화 실행이 된다.[^cc-headless] 훅이 도구 호출 전후에 셸 명령을 끼워 넣는다.[^cc-hooks] 서브에이전트·워크트리로 작업을 격리한다.[^cc-agents] | **실행자 — 셸을 쥔 손, 그리고 게이트** |
| **Codex CLI** (OpenAI) | `codex exec` 는 사람 개입 없이 끝나는 스크립트·CI용 실행이다. 기본값이 **읽기 전용 샌드박스**다.[^codex-exec] | **임시 반대 검토자** |

한 줄로 줄이면 역할은 이렇게 나뉜다.

- **Hermes 는 판정한다.**
- **Kiro 는 설계하고 초안을 쓴다.**
- **Claude Code 는 실제로 실행한다.**
- **Codex 는 반박한다.**

이렇게 나눈 이유는 도구의 기본값에 있다.
Codex 의 `exec` 는 기본이 읽기 전용이다. 그래서 *고치지 말고 보기만 하는* 역할에 마찰 없이 맞는다.
Kiro 의 스펙 3파일은 사람이 읽고 승인할 수 있는 **중간 산출물**이다. 그래서 넘겨주기의 계약서로 쓰기 좋다.
Claude Code 는 훅으로 *실행 직전에* 막을 수 있다. 그래서 운영 쓰기 권한을 맡긴다.

## 2. 넘겨주기는 말이 아니라 파일로 한다

넷이 서로 "다 됐어요"라고 *말로* 넘기면 협업은 금방 무너진다.
그래서 이 팀은 넘겨주기마다 **남는 산출물**을 정해 둔다.

| 넘겨주는 쪽 → 받는 쪽 | 넘겨주는 물건 | 받는 쪽이 확인할 것 |
|---|---|---|
| 사람/Hermes → Kiro | 목표 한 문단, 제약, 완료 조건 | 없음(출발점) |
| Kiro → 사람 | `requirements.md`·`design.md`·`tasks.md` | 인수 조건(acceptance criteria)이 검증 가능한 문장인지 |
| Kiro → Claude Code | 브랜치/워크트리의 diff | **테스트를 직접 돌린 결과**(Kiro 가 보고한 숫자 아님) |
| Claude Code → Codex | diff + 테스트 로그 경로 | 반례·누락·보안 구멍 |
| 모두 → Hermes | 구조화된 보고(아래) | 핵심 주장을 **독립적으로 재검증** |

맨 아래 줄이 가장 중요하다.
우리 환경의 Hermes fanout 정책 파일은 워커에게 다음 항목을 보고하라고 강제한다(우리 환경에서 관측).

- `run_id`
- 실제 실행한 동작
- 증거(명령·경로·exit code)
- 바뀐 파일
- 테스트 결과
- 모르는 것과 위험
- `PASS/WARN/FAIL/UNVERIFIED` 중 하나
- 끝 신호 `FANOUT_DONE`

같은 문서의 문장 하나가 이 설계 전체를 요약한다.

> Worker claims are hypotheses until Hermes verifies them with runtime trace, logs, source, or command output.

워커의 주장은 검증되기 전까지 **가설**이다.
Hermes 공식 문서도 같은 전제를 깔고 있다.
자식은 부모의 대화를 전혀 모르고, 부모가 `goal`·`context` 에 넣어준 것만 안다고 적혀 있다.[^hermes-deleg]
그래서 넘길 때는 파일 경로, 에러 메시지, 제약을 **명시적으로** 넣어야 한다.[^hermes-patterns]
"아까 말한 그 버그 고쳐줘"는 자식에게 아무 뜻도 없다.

---

## 3. 시나리오 A — 기능 추가: Kiro 설계 → Claude Code 실행 → Codex 반박 → Hermes 판정

가장 흔한 일감이다. "좋아요 중복을 DB 제약으로 막아줘" 같은 요청을 예로 든다.

```text
[사람] 목표·제약
   │
   ▼
[Kiro] requirements.md / design.md / tasks.md  ──(사람 승인)──┐
   │                                                           │
   ▼                                                           │
[Kiro] 워크트리에서 구현 (kiro-cli --no-interactive)            │
   │ diff                                                      │
   ▼                                                           │
[Claude Code] 테스트 전부 실행 · 숫자 재확인 · 훅 게이트        │
   │ diff + 로그                                               │
   ▼                                                           │
[Codex] codex exec --sandbox read-only  "이 diff 의 반례를 찾아라"│
   │ 반박 목록                                                  │
   ▼                                                           │
[Hermes] 모순 대조 · 핵심 주장 재검증 · 최종 보고 ◀─────────────┘
```

**단계별 주의점**

1. **Kiro 는 스펙부터 쓴다.**
   인수 조건을 "잘 동작한다"처럼 쓰면 안 된다.
   "같은 사용자가 같은 글에 두 번 누르면 두 번째는 `ALREADY_LIKED` 를 받는다"처럼 **검증 가능한 문장**으로 쓴다.
   이 파일이 뒤 단계 모두의 계약서다.
2. **Kiro 의 보고 숫자는 믿지 않는다.**
   우리 환경에서 셸 없이 돌던 Kiro 가 테스트 개수를 실제와 다르게 보고한 일이 있다(보고 349, 실제 329).
   그 뒤로 테스트 결과는 **Claude Code 가 CI 와 같은 명령을 그대로 전부 돌려서** 다시 센다.
   게이트를 몇 개만 골라 돌리면 초록불이 의미가 없다.
3. **모델 지정은 로그로 확인한다.**
   우리 환경의 kiro-cli 2.24.1 에서 겪은 일이다(우리 환경에서 관측).
   기본 엔진(v2)은 `--model` 을 받아도 `failed to set model` 경고만 남기고 auto 모델로 돌았다.
   `--agent-engine v1` 을 붙이면 지정한 모델이 적용됐다.
   공식 문서에 엔진 선택 플래그가 있다는 사실[^kiro-cli-ref]만으로는 이 동작을 알 수 없다.
   실행 로그 첫 줄을 봐야 한다.
4. **Codex 는 읽기 전용으로 부르고, 끝나면 내린다.**
   `codex exec` 는 기본이 읽기 전용 샌드박스다.
   공식 문서는 `--dangerously-bypass-approvals-and-sandbox` 를 격리된 러너 밖에서 쓰지 말라고 명시한다.[^codex-exec]
   반대 검토자에게는 쓰기 권한이 필요 없다.
   `--output-last-message` 로 결론만 파일로 받고 프로세스를 끝낸다.
   **상주시키지 않는다.**

## 4. 시나리오 B — 운영 장애 원인 분석: Hermes 팬아웃 + 읽기 전용 워커

"어떤 노드의 파드만 느리다" 같은 일감이다.
이런 일은 병렬로 여러 가설을 동시에 확인하면 이득이 크다.

우리 환경의 fanout 정책은 워커 넷에 역할을 고정해 둔다(우리 환경에서 관측).

| 워커 | 역할 |
|---|---|
| 1 | 구현·클러스터 관측 |
| 2 | Helm/GitOps/DB **읽기 전용** 분석 |
| 3 | 원인 분석(RCA)·보안·**반대 검토** |
| 4 | 테스트·인수 조건·완료 검증 |

규칙은 세 가지다.

- **기본 범위는 읽기 전용이다.** apply/delete/patch/scale/rollout, DB 쓰기, etcd 변경은 명시 승인이 있어야 한다.
- **바쁜 워커에게는 일을 밀어 넣지 않는다.** 먼저 상태를 본다.
- **사용자에게 결론을 내는 건 Hermes 하나뿐이다.** 워커는 텔레그램에 직접 말하지 않는다.

Hermes 공식 문서의 기본값도 같은 방향이다.
병렬 자식은 기본 3개이고(`max_concurrent_children`), 기본 깊이는 1(평평한 위임)이다.
자식은 `delegate_task`·`clarify`·`memory`·`send_message`·`cronjob` 을 못 쓴다.[^hermes-deleg]
**자식이 사용자에게 직접 말하거나 일을 또 퍼뜨리지 못하게** 막아 둔 것이다.

원인이 좁혀지면 **쓰기는 Claude Code 봇 한 곳에서만** 한다.
이때 우리 환경에서는 Claude Code 의 `PreToolUse` 훅(cluster-coordinator)이 게이트 역할을 한다.
kubectl·helm 쓰기나 노드 SSH 가 다른 봇 작업과 겹치면 실행 *직전에* 막는다.
훅은 도구 호출 전에 끼어들어 호출을 막을 수 있다. 이건 Claude Code 공식 기능이다.[^cc-hooks]
여러 에이전트에게 "조심해"라고 부탁하는 것보다 **한 지점에서 기계적으로 막는 것**이 낫다.

## 5. 시나리오 C — 판단이 갈리는 질문: Claude 가 주도하고 Codex 가 임시로 반박

"이 아키텍처로 가도 되나", "이 정책은 누구에게 이득인가" 같은 질문에는 정답이 없다.
이럴 때 우리 환경은 Leopard 저장소의 하브루타 규칙을 따른다(우리 환경에서 관측).

- **주 분석자는 Claude(또는 Hermes)이고, Codex 는 임시 자문 검토자다.**
  양쪽이 번갈아 주장하는 전면 토론 라운드는 사용자가 명시적으로 원할 때만 연다.
- 라운드 수에는 **상한**이 있다. 끝나면 Codex 프로세스를 **종료**한다.
- 실행 로그·상태·산출물이 없으면 "토론이 돌았다"고 **주장하지 않는다.**
  라운드 수·모델 이름·비용을 지어내지 않는다.

이 설계에는 이유가 있다.
같은 모델 둘을 붙이면 같은 맹점을 공유할 가능성이 크다. 이건 필자 추정이다.
다른 회사 모델을 *반대편*에 세우는 편이 반례를 더 잘 뽑는다고 본다.
다만 "모델이 달라야 반박 품질이 오른다"를 중립적으로 비교한 연구는 찾지 못했다.
그래서 여기서는 **설계 의견**으로만 둔다.

## 6. 시나리오 D — 글 발행 같은 "딱 한 번" 일: 조사는 병렬, 발행은 하나

이 글 자체가 이 시나리오의 예다.
조사·검증·검토는 여럿이 나눠 해도 된다.
하지만 **발행은 한 세션만** 한다.

우리 집에는 같은 리포에 글을 쓰는 봇이 여러 개 있다.
같은 요청이 여러 봇에 동시에 뿌려진 날, 그날 글이 그 수만큼 나간 적이 있다(우리 환경에서 관측).
락으로 순서를 세워도 발행량은 줄지 않는다.
필요한 건 **소유권 선언**이다.
우리 환경에서는 각 봇이 공용 상태 디렉터리의 자기 파일에 `agent / state / task` 를 적는다.
그걸 보고 누가 이미 그 일을 잡았는지 확인한다.
노드 쪽 봇이 "맥 봇 둘이 같은 작업을 동시에 하는 것 같다"고 알려 준 날도 있었다.
그날 해결책은 속도를 맞추는 게 아니었다. 한쪽이 일을 **내려놓는** 것이었다.

---

## 7. 이렇게 하면 깨진다 — 실제로 밟은 지뢰 다섯

| 증상 | 원인 | 규칙 |
|---|---|---|
| 봇 세션은 살아 있는데 메시지 수신이 0 | 봇 안에서 CLI 에이전트를 또 띄웠다. 자식이 환경변수를 **상속해** 살아 있던 메신저 폴러를 밀어냈다(우리 환경에서 관측) | 에이전트 안에서 같은 에이전트를 띄울 땐 상태 디렉터리 환경변수를 격리한다 |
| 남의 변경이 내 커밋에 섞임 | 공유 체크아웃에는 인덱스가 하나뿐이라 `add → commit` 이 원자적이지 않다 | `git commit --only <경로>` 를 쓰거나 워크트리로 격리한다. Claude Code·Hermes 둘 다 워크트리 격리를 지원한다[^cc-agents][^hermes-deleg] |
| 크루가 "N/N 통과"라고 보고했는데 실제로는 아무것도 안 바뀜 | 사람 없이 돈 Kiro 크루 실행에서 쓰기가 전부 권한 거부됐는데도 성공으로 보고했다(우리 환경에서 관측) | 완료 판정은 **diff 와 exit code** 로 한다. 에이전트의 자기 보고로 하지 않는다 |
| 지정한 모델이 안 쓰임 | 엔진 버전에 따라 `--model` 이 무시됐다(위 3절) | 실행 로그에서 모델을 확인한다 |
| 헤드리스 실행에서 예상 못 한 훅이 돎 | Claude Code `-p` 는 신뢰 대화상자 없이 폴더를 신뢰된 것으로 취급한다. 그래서 리포에 커밋된 `.claude/settings.json` 훅이 실행된다[^cc-hooks] | 남의 리포를 자동으로 돌릴 땐 `--bare` 를 쓴다[^cc-headless] |

다섯 줄의 공통점은 하나다.
**에이전트의 말과 시스템의 상태가 어긋났다.**
그래서 협업 설계는 결국 *말을 믿지 않고 상태를 확인하는 경로*를 어디에 둘지 정하는 일이다.

## 8. 필자 제안 — 넷을 처음 묶는다면

아래는 검증된 모범 사례가 아니라 필자의 운영 의견이다.

1. **판정자는 하나만 둔다.**
   Hermes 든 사람이든, 사용자에게 결론을 말하는 입은 하나여야 한다.
2. **쓰기 권한은 한 도구에 몰고, 그 앞에 훅을 둔다.**
   Codex 는 읽기 전용으로, Kiro 는 워크트리 안에서만 쓰게 한다.
   운영 쓰기는 Claude Code 에만 준다.
3. **넘겨주기 계약은 파일로 남긴다.**
   스펙 3파일, diff, JSON 보고, 그리고 `PASS/WARN/FAIL/UNVERIFIED` 판정을 남긴다.
   "UNVERIFIED" 를 쓸 수 있는 칸을 만들어 두는 게 핵심이다. 그 칸이 없으면 모두가 PASS 를 쓴다.
4. **반대 검토자는 임시로 띄운다.**
   상주하는 검토자는 점점 동료가 된다. 매번 새 컨텍스트로 띄우고 끝나면 내린다.
   Hermes 자식이 새 컨텍스트로 시작하는 것도 같은 이유다.[^hermes-patterns]
5. **숫자는 재실행으로만 확인한다.**
   테스트 개수, 통과율, 성공 건수는 받는 쪽이 직접 다시 센다.

## 한계

- 이 글의 시나리오는 **한 가정의 한 환경**(맥 1대 + 노드 봇들)에서 나왔다.
  규모가 큰 조직이나 다른 도구 조합에 그대로 들어맞는다는 근거는 없다.
- 넷의 협업 효과(생산성·결함률)를 중립적으로 비교한 측정은 찾지 못했다. 그래서 수치 주장을 하지 않았다.
- 도구 버전이 빠르게 바뀐다.
  Kiro 엔진별 `--model` 동작 같은 관측은 **kiro-cli 2.24.1 기준**이다. 이후 버전에서는 다를 수 있다.

## References

[^hermes-deleg]: Nous Research, "Subagent Delegation", *Hermes Agent Docs*. <https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation>
[^hermes-patterns]: Nous Research, "Delegation & Parallel Work", *Hermes Agent Docs*. <https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns>
[^hermes-acp]: Nous Research, "ACP Host Integration", *Hermes Agent Docs*. <https://hermes-agent.nousresearch.com/docs/user-guide/features/acp> · Agent Client Protocol <https://agentclientprotocol.com/>
[^kiro-specs]: Kiro, "Specs", *Kiro Docs*. <https://kiro.dev/docs/specs/>
[^kiro-headless]: Kiro, "Headless mode", *Kiro CLI Docs*. <https://kiro.dev/docs/cli/headless/>
[^kiro-cli-ref]: Kiro, "CLI commands", *Kiro Docs*. <https://kiro.dev/docs/reference/cli-commands/>
[^cc-headless]: Anthropic, "Run Claude Code programmatically (headless)", *Claude Code Docs*. <https://code.claude.com/docs/en/headless>
[^cc-hooks]: Anthropic, "Hooks reference", *Claude Code Docs*. <https://code.claude.com/docs/en/hooks>
[^cc-agents]: Anthropic, "Subagents", *Claude Code Docs*. <https://code.claude.com/docs/en/sub-agents>
[^codex-exec]: OpenAI, "Command line options – Codex CLI", *OpenAI Developers*. <https://developers.openai.com/codex/cli/reference>
