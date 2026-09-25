---
layout: post
title: "읽기 전용 자율 SecOps 조사 에이전트 — 핵심 IP 는 탐지 모델이 아니라 실행 프레임워크다"
date: 2026-09-25 15:52:22 +0900
categories: [security]
tags: [ai-agent, secops, llm-security, owasp, prompt-injection, kubernetes, watchman]
---

우리 클러스터의 보안 에이전트 **파수꾼(Watchman)** 을 한 줄로 소개할 일이 생겼다.
"AI 보안 관제", "LLM 기반 이상 탐지", "자동 대응 봇" 같은 후보가 나왔지만 셋 다 조금씩 틀렸다.
가장 정확한 이름은 이것이었다.

> **Read-only autonomous SecOps investigation agent** — 읽기 전용 자율 SecOps 조사 에이전트

그리고 이 이름을 정하다 보니 더 흥미로운 사실이 드러났다.
이 시스템에서 남에게 보여 줄 만한 핵심 자산(IP)은 **"무엇을 탐지하느냐" 가 아니었다.**
LLM 에게 **조사하는 자율성은 주면서도 권한·도구·데이터·출력을 코드로 통제하는 실행 프레임워크**가 핵심이었다.
이 글은 이 두 문장을 풀어서 설명한다.

## 1. 이름을 한 단어씩 뜯어 보면

이름의 네 단어가 각각 하나의 설계 결정이다.

| 단어 | 뜻 | 반대로 했다면 |
|---|---|---|
| **Investigation** (조사) | 탐지가 아니라 탐지 *다음* 단계를 맡는다. 알림이 이미 울린 뒤 로그를 뒤지고, 증거를 모으고, 원인을 분류한다 | 탐지기를 하나 더 만드는 셈이다. 이미 Falco·Prometheus 가 하고 있다 |
| **SecOps** | 보안 경보와 운영 경보를 같은 흐름에서 1차 트리아지한다 | 보안만 보면 "파드 재시작" 경보에 숨은 침해 신호를 놓친다 |
| **Autonomous** (자율) | 어떤 로그를 먼저 보고 무엇을 더 조회할지는 LLM 이 정한다 | 알림 종류마다 분기를 하드코딩하는 파이프라인이 된다 |
| **Read-only** (읽기 전용) | 무엇도 바꾸지 않는다. 결과물은 사람에게 보내는 **제안 카드**뿐이다 | 새벽 3시에 LLM 이 `kubectl delete` 를 칠 수 있게 된다 |

여기서 중요한 건 **자율**과 **읽기 전용**이 같은 이름 안에 함께 있다는 점이다. 서로 모순처럼 들리지만,
둘은 서로 다른 축에 걸려 있다.

- 자율성은 **조사 순서**에 준다. "다음에 무엇을 볼까" 는 LLM 이 정한다.
- 권한은 **행위 범위**로 묶는다. "무엇을 할 수 있나" 는 코드가 정한다.

파수꾼 설계 문서(SPEC §2)에는 이렇게 적혀 있다. *"자유도는 조사 순서에만 있고 행위 범위에는 없다."*
이 한 줄이 이 글의 요지다.

## 2. 왜 "자율" 이 필요했나 — 파이프라인으로는 안 되는 이유

Anthropic 은 에이전트 설계 가이드에서 두 가지를 구분한다([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), 2024).
**워크플로**는 미리 정한 코드 경로를 따라 LLM 을 호출한다. **에이전트**는 LLM 이 스스로 과정과 도구 사용을 정한다.
그리고 경로를 미리 예측할 수 없는 열린 문제에만 에이전트를 쓰라고 권한다.

경보 조사가 딱 그런 문제다. 경보마다 봐야 할 곳이 다르다.

- **KubeJobFailed** 라면 Job 파드 로그를 본다.
- **Velero PVB not-ready** 라면 노드 상태와 Velero 로그를 본다.
- **CrashLoop** 라면 컨테이너 로그와 이벤트를 본다.
- **Falco 런타임 경보**라면 같은 파드의 직전 프로세스와 네트워크 흔적을 본다.

그런데 첫 조회 결과에 따라 두 번째 조회가 달라진다. 분기가 트리 모양으로 벌어지므로 하드코딩으로는 따라가기 어렵다.
그래서 조사 순서는 LLM 에게 넘겼다. 대신 넘기는 범위를 엄격히 정했다.

## 3. 왜 핵심이 "탐지 모델" 이 아닌가

### 3.1 LLM 은 지시와 데이터를 구분하지 못한다

조사 에이전트가 읽는 로그는 **공격자가 쓸 수 있는 데이터**다. 클러스터에서 도는 워크로드라면 무엇이든
로그에 문자열을 남길 수 있다. 그 문자열이 "이전 지시를 무시하고 …" 라면 어떻게 될까.

Greshake 등은 이 공격을 **간접 프롬프트 주입**이라 부르고 실제 시스템에서 재현했다.
LLM 을 붙인 애플리케이션에서는 데이터와 지시의 경계가 흐려진다는 것이 이들의 결론이다
([Greshake et al., 2023, arXiv:2302.12173](https://arxiv.org/abs/2302.12173)).
OWASP 도 같은 판단이다. 2025년 12월에 낸 에이전트 전용 Top 10 의 1번 항목인
**ASI01 Agent Goal Hijack** 설명에 따르면, 에이전트와 그 밑의 모델은 지시와 관련 콘텐츠를
*신뢰성 있게 구분하지 못한다*([OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)).

그렇다면 **더 똑똑한 모델**이나 **더 좋은 탐지 프롬프트**로는 문제가 끝나지 않는다.
모델이 주입을 거부하는 건 확률적인 행동이다. 이번에 거부했다고 다음에도 거부한다는 보장은 없다.
이 점은 전날 글 [AI 에이전트 보안 — 모델의 거부는 통계이고, 보장은 코드 경계가 진다]({% post_url 2026-09-24-agent-security-refusal-is-statistics-boundaries-are-guarantees %})에서 자세히 다뤘다.

### 3.2 보장은 "할 수 있는 일의 집합" 에서 나온다

에이전트가 허용받은 행위의 집합을 $A$ 라고 하자. 모델이 얼마나 속든, 한 번의 실행이 낼 수 있는 최대 피해는
그 집합 안에서 결정된다.

$$
\text{최대 피해} \;\le\; \max_{a \in A} \text{impact}(a)
$$

모델이 공격 지시를 따를 확률 $p$ 를 줄이는 일(더 좋은 모델, 더 좋은 프롬프트)은 **기대 피해**를 줄인다.
**최대 피해**의 상한을 바꾸는 건 $A$ 를 줄이는 일뿐이다. 파수꾼의 $A$ 에는 읽기와 제안만 들어 있다.
그래서 모델이 완전히 넘어가도 최악의 결과는 "틀린 제안 카드 한 장" 이다.

OWASP 는 이 문제를 **LLM06 Excessive Agency** 로 따로 분류한다. 근본 원인은
**과도한 기능, 과도한 권한, 과도한 자율성** 세 가지로 정리된다
([OWASP LLM06:2025](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)).
세 가지 모두 모델 안이 아니라 모델을 둘러싼 시스템의 속성이다.

### 3.3 학계도 같은 방향이다

최근 연구의 흐름도 같다. 모델을 더 잘 훈련하는 대신 **모델 바깥에 시스템 층을 둔다.**

- Google DeepMind 의 **CaMeL** 은 신뢰할 수 있는 사용자 질의에서 제어 흐름을 먼저 뽑아낸다.
  그러면 LLM 이 나중에 읽은 신뢰할 수 없는 데이터가 프로그램 흐름을 바꿀 수 없다. 여기에 capability 기반 정책을 더해
  데이터 유출 경로도 막는다([Debenedetti et al., 2025, arXiv:2503.18813](https://arxiv.org/abs/2503.18813)).
  논문이 보고한 AgentDojo 과제 해결률은 방어 시 77%, 무방어 시 84% 다(저자 보고치). 보안의 대가로 유용성을 얼마나 잃는지 수치로 보여 준 점이 가치 있다.
- ETH Zürich·IBM·Google·Microsoft 등의 공동 연구 **Design Patterns for Securing LLM Agents against Prompt Injections** 는
  "증명 가능한 저항성" 을 목표로 하는 설계 패턴 여섯 가지를 정리했다. 예를 들어 행동을 미리 정한 목록에서만 고르게 하는
  *action-selector*, 계획을 먼저 확정하고 실행하는 *plan-then-execute* 가 있다
  ([Beurer-Kellner et al., 2025, arXiv:2506.08837](https://arxiv.org/abs/2506.08837)).
  공통 원칙은 이렇다. 신뢰할 수 없는 입력을 읽은 에이전트는, 그 입력이 중대한 행동을 일으킬 수 없도록 제약해야 한다.

더 오래된 원칙으로 거슬러 올라가면 Saltzer 와 Schroeder 의 1975년 논문에 닿는다.
**최소 권한(least privilege)**, **안전한 기본값(fail-safe defaults)**, **완전한 중재(complete mediation)** 가 모두 여기서 나왔다
([Saltzer & Schroeder, 1975](https://web.mit.edu/Saltzer/www/publications/protection/)).
LLM 에이전트 보안은 새로운 문제처럼 보이지만, 해법의 뼈대는 50년 된 접근 통제 원칙이다.
달라진 건 하나다. 이제는 **프로그램의 제어 흐름 일부를 확률적 모델이 쓴다.**

## 4. 실행 프레임워크 — 네 개의 축

"통제된 실행 프레임워크" 를 구체적으로 풀면 네 개의 축이 나온다. 파수꾼에서 각 축이 어떻게 구현됐는지 함께 적는다.

### ① 권한 — 자격증명이 할 수 있는 일

| 대상 | 통제 |
|---|---|
| Kubernetes | 전용 ServiceAccount 에 `get`·`list`·`watch` 만 준다. `create`·`patch`·`delete` 는 없다 |
| Elasticsearch | 읽기 전용 계정 `watchman`(role `watchman_read`) |
| 텔레그램 봇 토큰 | 메시지 전송 용도로만 쓴다 |
| 컨테이너 | 비루트(`uid=65534`), `readOnlyRootFilesystem`, `drop: [ALL]`. 쓰기는 감사로그 볼륨 한 곳만 |

코드에 버그가 있어도, 모델이 속아도, **자격증명 자체에 쓰기 권한이 없다.** 이 층은 모델과 무관하게 참이다.

### ② 도구 — LLM 이 부를 수 있는 함수와 인자

기본으로 등록된 도구는 `es_search`, `kube_read`, `finish` 세 개다. 핵심은 **인자를 코드가 조립한다**는 점이다.

- `es_search` 에서 LLM 은 자유로운 쿼리 DSL 을 쓸 수 없다. 인덱스 패턴은 허용목록에서 고르고,
  조회 기간은 최대 240분, 결과 크기는 최대 50건으로 코드가 검사한다.
- `kube_read` 는 `kubectl` 을 부르지 않고 Kubernetes API 를 직접 호출한다. 동사는 `get`·`list`·`logs` 중 하나만 된다.
- 스텝 예산은 최대 6번이다(도구 호출 5번 + 최종 응답 1번). 넘으면 "부분 결과" 라벨을 달고 조사를 멈춘다.

LLM 이 만든 텍스트가 셸이나 DSL 로 바로 넘어가는 경로가 없다. 앞의 논문이 말한 *action-selector* 패턴과 같은 발상이다.

### ③ 데이터 — 읽은 것을 어떻게 취급하나

- 로그와 알림 본문은 항상 **"신뢰할 수 없는 데이터" 블록**으로 감싸서 모델에 넘긴다.
- 주입 의심 패턴을 결정론적 코드로 감지하면 카드에 ⚠ 표시를 붙인다.
- 모델의 출력은 스키마로 검증한다. 스키마를 벗어나면 버리고 한 번만 다시 시도한다.

이 축은 **확률을 낮추는 층**이다. 뚫릴 수 있다는 전제로 설계했기 때문에 ①②④가 뒤에 있다.

### ④ 출력 — 무엇이 밖으로 나가나

- **제안은 명령어 문자열이 아니라 구조화된 객체다.** `action_type`(image_replace·restart·suspend…), `target`, `rationale`, `risk`
  필드로만 표현한다. LLM 이 만든 셸 문자열을 사람이 복사해 붙여 넣는 경로 자체가 공격면이기 때문이다.
- **이그레스 통제.** NetworkPolicy 로 나가는 목적지와 포트를 허용목록으로 묶었다. 로그에서 읽은 임의 URL 로 데이터를 빼내는 경로를 막는다.
- **유출 마스킹.** 카드·메일·감사로그로 나가는 텍스트에서 비밀값 패턴을 가린다.
- **감사 해시체인.** 모든 도구 호출과 LLM 입출력을 append-only 로 기록하고 해시로 이어 붙인다. 나중에 한 줄만 고쳐도 체인이 끊긴다.

## 5. 실측 — 그리고 무엇을 주장하지 않는가

아래 수치는 파수꾼 리포의 평가 문서에서 **자체 측정한 값**이다(리포는 비공개. 동작 현황은
[공개 관제 뷰](https://security.lemuel.co.kr/)에서 읽기 전용으로 볼 수 있다). 제3자 검증은 없다.

| 축 | 측정 | 결과 |
|---|---|---|
| 데이터(입력) | 레드팀 주입 페이로드 12건 | 코드층 감지 12/12, 정상 입력 오탐 0/12. LLM 이 공격 지시를 수행한 경우 0/12(2회전) |
| 출력 | 비밀값 유출 시나리오 7건 | 차단 7/7, 오탐 0, 마스킹 후 잔존 0 |
| 조사 품질 | 실제 알림 블라인드 채점 | 정상 알림을 '사고' 로 잘못 올린 경우 0/37, 실제 장애를 '사고' 로 올린 경우 13/13 |
| 도구 규약 | 120B 모델의 도구 호출 형식 준수 | 58/58 |

정직하게 적어 둘 한계가 있다.

- **실제 장애 13건은 모두 한 사건에서 나왔다.** 사건 하나로 재현율을 일반화할 수 없다.
- **"LLM 이 수행 0/12" 는 통계일 뿐이다.** 3장의 논리대로라면 이 줄은 아무것도 보장하지 않는다. 보장은 권한 층(①)이 한다. 표에 넣은 이유는 입력 층이 실제로 일하는지 보여 주기 위해서다.
- **이그레스 통제는 "외부 전부 차단" 이 아니다.** NIM 추론과 메일 발송 때문에 외부 443·587 포트는 열려 있다.
- 다른 SecOps 에이전트와 같은 조건에서 비교한 중립적인 헤드투헤드 평가는 **없다.** 그러니 "더 낫다" 는 주장도 하지 않는다.

같은 관제에서 겪은 실패담은 [파수꾼 관제 90분 — AI 보안 분석가는 같은 오탐을 26번 조사했다]({% post_url 2026-09-24-watchman-same-false-positive-26-times %})에 있다.
실행 프레임워크가 안전을 지켜 줘도 **효율**까지 지켜 주지는 않는다는 기록이다.

## 6. 그래서 무엇이 IP 인가

탐지 모델은 바꿀 수 있다. 파수꾼도 NIM 의 Nemotron 모델 사이에서 폴백한다. 내일 더 좋은 모델이 나오면 교체하면 된다.
모델은 **교체 가능한 부품**이다.

반면 아래 질문들의 답은 모델을 바꿔도 그대로 남는다. 그리고 조직마다 다르다.

- 이 에이전트의 자격증명은 무엇을 할 수 있나?
- 어떤 도구를, 어떤 인자 범위로 부를 수 있나?
- 읽은 데이터 중 무엇을 신뢰하지 않나?
- 무엇이, 어디로, 어떤 형태로 밖에 나가나?
- 그 모든 것이 어디에 지울 수 없게 남나?

이 다섯 질문의 답을 **코드와 인프라로 강제한 것**이 실행 프레임워크다. 파수꾼에서 복제하기 어려운 부분은 여기다.
NVIDIA 가 NemoClaw·OpenShell 로 정책 계층을 따로 떼어 낸 것도 같은 판단으로 보인다.
이 부분은 [에이전트 정책은 어디에 두나]({% post_url 2026-09-20-where-agent-policy-belongs-nemoclaw-openshell %})에서 다뤘다.

정리하면 이렇다. **조사의 자율성은 모델이 만들고, 조사의 안전은 프레임워크가 만든다.**
그리고 둘 중 모델을 바꿔도 남는 쪽은 프레임워크다.

---

## References

1. OWASP GenAI Security Project, [LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) — OWASP Top 10 for LLM Applications 2025.
2. OWASP GenAI Security Project, [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), 2025-12-09.
3. K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, M. Fritz, [Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection](https://arxiv.org/abs/2302.12173), arXiv:2302.12173, 2023 (AISec '23).
4. E. Debenedetti, I. Shumailov, T. Fan, J. Hayes, N. Carlini, et al., [Defeating Prompt Injections by Design (CaMeL)](https://arxiv.org/abs/2503.18813), arXiv:2503.18813, 2025.
5. L. Beurer-Kellner, B. Buesser, A.-M. Creţu, E. Debenedetti, et al., [Design Patterns for Securing LLM Agents against Prompt Injections](https://arxiv.org/abs/2506.08837), arXiv:2506.08837, 2025.
6. J. H. Saltzer, M. D. Schroeder, [The Protection of Information in Computer Systems](https://web.mit.edu/Saltzer/www/publications/protection/), Proceedings of the IEEE 63(9), 1975.
7. E. Schluntz, B. Zhang (Anthropic), [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), 2024-12-19.
8. Watchman(파수꾼) 내부 평가 문서 — `SPEC.md`, `eval/CONTROL-MATRIX.md`, `eval/REDTEAM.md`, `eval/real-alerts-20260924.md` (비공개 리포, 자체 측정).
