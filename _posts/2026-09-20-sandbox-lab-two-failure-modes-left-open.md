---
layout: post
title: "막힌 것 넷보다, 안 막힌 것 둘이 중요하다 — 샌드박스 실습 정리 한 장"
date: 2026-09-20 19:14:21 +0900
categories: [AI, Security]
tags: [Agent, Sandbox, Landlock, seccomp, OPA, Prompt Injection, Lethal Trifecta, OpenShell]
---

[바로 앞 글](https://myoungsoo7.github.io/2026/09/20/four-os-mechanisms-four-verifiable-questions/)에서 표 한 장을 커널 문서로 되짚었다. 네 가지 OS 메커니즘 — netns, Landlock, seccomp, non-root — 이 각각 어떤 질문에 답하는지까지가 그 글이었다. 그건 **설계도**였다.

이번 그림은 그 설계도를 실제로 만져본 결과다. 그런데 읽고 나서 눈에 남은 건 "네 개 다 잘 동작했다"가 아니었다. 표의 네 번째 항목 — **열려 있는 실패 모드 두 개** — 였다.

![4a 실습 정리 — 직접 확인한 것](/assets/images/sandbox/sandbox-lab-findings.jpg)

*그림에 보이는 `10.200.0.1:3128` 은 일회용 샌드박스 컨테이너 내부의 게이트웨이 주소다. 내 홈랩이나 개인 네트워크 주소가 아니라서 그대로 둔다.*

## 0. 그림에 적힌 것

읽기 쉽게 옮기면 이렇다.

| # | 항목 | 내용 |
| --- | --- | --- |
| 1 | 네 메커니즘의 흔적 | non-root(uid 998) / 출구는 프록시 `10.200.0.1:3128` 하나(netns) / 허용 외 호스트는 CONNECT 403(OPA) / `/opt` 쓰기 거부 |
| 2 | 실패 원인 분류를 실제로 함 | `sudo`·docker 없음(소프트웨어 부재) ≠ apt root 필요(권한) ≠ 403(정책) ≠ 404(허용 호스트의 앱 에러) |
| 3 | 정책 편집권은 샌드박스 밖에만 | 에이전트에겐 `nemoclaw`/`openshell` 바이너리 자체가 없음 |
| 4 | 열려 있는 실패 모드 둘 | ① Persona tamper — `SOUL.md` 가 sandbox 소유 `rw` ② 허용 채널 = 양방향 — `pip install` 성공은 PyPI 로 바이트를 보낼 수 있다는 뜻 |
| 5 | Claude Code 세팅과의 대응 | 하네스 분류기 층과 커널 층은 **대체가 아니라 누적** |

1·2·3번은 "잘 막혔다"이고 4번은 "안 막혔다"다. 이 글은 4번에 무게를 둔다. 막힌 걸 세는 건 쉽고, 안 막힌 걸 적어두는 게 어렵기 때문이다.

## 1. 흔적 넷 — 각 관측이 어느 층의 서명인가

1번의 네 관측은 우연히 넷이 아니라, 앞 글의 네 메커니즘에 하나씩 대응한다.

| 관측된 것 | 서명한 층 | 근거 |
| --- | --- | --- |
| `uid 998` | non-root | root 가 아니면 `CAP_*` 대부분이 없다 |
| 출구가 프록시 하나 | 네트워크 네임스페이스 | netns 는 네트워크 장치·라우팅 테이블·방화벽 규칙을 통째로 분리한다 |
| 허용 외 호스트에 `CONNECT 403` | 정책 엔진(OPA류) | 403 은 연결 실패가 아니라 **결정**이다 |
| `/opt` 쓰기 거부 | Landlock(또는 마운트) | 경로 단위 접근 제한 |

네 번째 항목 `403` 을 따로 볼 만하다. 네트워크가 끊겼으면 타임아웃이나 `ECONNREFUSED` 가 났을 것이다. **403 이 돌아왔다는 건 프록시가 살아서 요청을 받고, 판단하고, 거절했다는 뜻이다.** OPA 문서가 자기 역할을 정의하는 방식 그대로다.

> Services offload policy decisions to OPA by executing queries. OPA evaluates policies and data to produce query results (which are sent back to the client).
> — [OPA Philosophy](https://www.openpolicyagent.org/docs/philosophy)

즉 이 403 은 "못 갔다"가 아니라 "가면 안 된다고 누가 정했다"의 증거다. 둘은 전혀 다른 사실이고, 그 구분이 바로 2번의 주제다.

## 2. 이 실습의 진짜 기술은 2번이다

샌드박스를 테스트할 때 제일 흔한 오진이 이거다 — **"안 되네 = 막혔네."**

실제로는 안 되는 이유가 최소 네 가지고, 셋은 보안 통제가 아니다.

| 증상 | 진짜 원인 | 어느 층인가 | 구분하는 법 |
| --- | --- | --- | --- |
| `sudo: command not found` | **소프트웨어 부재** | 이미지 구성 | `command -v` 로 바이너리 유무 확인. 없으면 통제가 아니라 그냥 안 깔린 것 |
| `apt` 가 root 를 요구 | **권한** | non-root(DAC) | `id` 로 uid 확인, `EACCES`/`EPERM` |
| `CONNECT` 에 `403` | **정책** | 프록시·OPA | HTTP 상태 코드가 돌아옴 = 중간자가 살아 있음 |
| 허용 호스트인데 `404` | **앱 에러** | 원격 서버 | 통제를 통과한 뒤 발생. 오히려 "뚫렸다"는 증거 |

마지막 줄이 중요하다. **허용된 호스트에서 404 를 받았다는 건 통제가 실패한 게 아니라 성공적으로 통과했다는 뜻이다.** 이걸 "막혔다"로 기록하면 샌드박스가 실제보다 강해 보인다.

반대 방향 오진도 있다. `sudo` 가 없는 걸 "sudo 가 차단됐다"로 적으면, 나중에 누군가 이미지에 `sudo` 를 넣는 순간 조용히 사라지는 통제를 통제로 세어둔 셈이 된다. **부재는 통제가 아니다.** 통제는 있는 걸 못 쓰게 만드는 것이다.

## 3. 3번은 필요조건이지 충분조건이 아니다

"정책 편집권은 샌드박스 밖에만 있다"는 결론은 맞는 방향인데, 제시된 증거 — `nemoclaw`/`openshell` 바이너리가 없음 — 는 **약한 증거**다. 2번의 첫 줄에서 방금 경계한 그 패턴, 소프트웨어 부재이기 때문이다.

정책이 정말 밖에 있다는 걸 말하려면 부재보다 강한 성질이 필요하다. 다행히 커널 문서에 그 성질이 적혀 있다.

> Each time a thread enforces a ruleset on itself, it updates its Landlock domain with a new layer of policy. This complementary policy is **stacked** with any other rulesets potentially already restricting this thread. A sandboxed thread can then safely **add more constraints** to itself with a new enforced ruleset.
> — [Landlock, Linux kernel documentation](https://docs.kernel.org/userspace-api/landlock.html)

핵심은 *stacked* 와 *add more constraints* 다. 레이어는 쌓이기만 하고, 한 번 쌓인 층을 푸는 동작이 API 에 없다. 그래서 샌드박스 안에서 바이너리를 구해오든 코드를 짜든 **자기 Landlock 도메인은 느슨해지지 않는다.** seccomp 도 같은 성질을 다른 방식으로 확보한다 — 필터를 붙이려면 `no_new_privs` 를 켜거나 `CAP_SYS_ADMIN` 이 있어야 하고([seccomp 문서](https://docs.kernel.org/userspace-api/seccomp_filter.html)), 켜진 `no_new_privs` 는 setuid 로 권한을 되찾는 길을 막는다.

**"밖에만 있다"의 증거는 "안에 파일이 없다"가 아니라 "안에서는 되돌리는 연산 자체가 없다"여야 한다.** 전자는 이미지를 고치면 깨지고, 후자는 커널 계약이다.

다만 이것도 범위가 있다. 프록시 allowlist 는 커널이 아니라 프록시 쪽 설정이므로, 위 논리는 Landlock/seccomp 에만 적용된다. 네트워크 정책이 밖에 있다는 건 별도로 확인해야 할 사실이다.

## 4. 열려 있는 두 개 — 이 글의 본론

### ① Persona tamper: `SOUL.md` 가 `rw` 다

[오늘 앞 글](https://myoungsoo7.github.io/2026/09/20/openclaw-workspace-files-and-the-memory-canary/)에서 `MEMORY.md` 에 카나리 문자열을 쓰게 해서 "에이전트가 자기 워크스페이스에 쓸 수 있다"를 확인했다. 같은 권한이 `SOUL.md` 에도 걸려 있다는 게 이번 관측이다. 즉 **에이전트가 자기 행동 규칙 파일을 고칠 수 있다.**

여기서 짚을 건 이게 네 메커니즘 중 어느 것의 실패도 아니라는 점이다. Landlock 은 정책이 준 만큼 정확히 통제했고, 정책이 워크스페이스를 `rw` 로 줬다. **커널 통제는 정책의 상한을 집행할 뿐 정책의 품질을 고쳐주지 않는다.**

그래서 앞 글의 문장이 여기서 다시 성립한다 — 에이전트가 고칠 수 있는 파일에 적힌 규칙은 규칙이 아니라 **기본값**이다. 워크스페이스 안의 `SOUL.md` 는 프롬프트 인젝션이 들어왔을 때 공격자가 다음 세션까지 지속시키는 자리가 된다. 통제를 걸고 싶으면 그 파일이 읽기 전용이어야 하고, 읽기 전용으로 만드는 건 커널이 아니라 정책을 쓰는 사람이다.

### ② 허용 채널은 양방향이다

두 번째가 더 근본적이다. `pip install` 이 성공했다 = `pypi.org` 가 allowlist 에 있다 = **그 호스트로 HTTP 요청을 보낼 수 있다.** 요청에는 바이트가 실린다.

프롬프트 인젝션이라는 용어를 만든 Simon Willison 이 이 지점을 가장 짧게 적어뒀다.

> If a tool can make an HTTP request—to an API, or to load an image, or even providing a link for a user to click—that tool can be used to pass stolen information back to an attacker.
> — [The lethal trifecta for AI agents](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/), 2025-06-16

그가 말하는 치명적 삼요소는 이렇다.

1. **Access to your private data**
2. **Exposure to untrusted content**
3. **The ability to externally communicate in a way that could be used to steal your data**

셋이 동시에 있으면 성립한다. 그리고 그의 결론은 완화가 아니라 회피다.

> The only way to stay safe there is to avoid that lethal trifecta combination entirely.

이 실습 환경에 대보면 세 번째 다리가 살아 있다. 그리고 앞 글에서 확인한 대로, 프록시가 CONNECT 터널을 열어준 뒤에는 내용을 볼 수 없다.

> ...only the host and port number... blind forwarding of data
> — [RFC 9110 §9.3.6 CONNECT](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6)

**allowlist 는 목적지를 좁힐 뿐, 그 목적지로 무엇이 나가는지는 모른다.** 그림에 적힌 "정책은 pypi.org 허용만 알지 그 위로 뭐가 지나가는지 모름" 이 정확히 이 얘기다. PyPI 는 패키지를 올릴 수도 있는 사이트이고, 업로드가 아니어도 URL·헤더·본문에 데이터를 실을 자리는 많다.

그렇다면 이걸 어떻게 다루나. 최근 연구는 "모델이 알아서 거르게 한다"를 포기하고 **구조로 막는** 쪽을 제안한다.

> ...once an LLM agent has ingested untrusted input, it must be constrained so that it is impossible for that input to trigger any consequential actions.
> — [Design Patterns for Securing LLM Agents against Prompt Injections](https://arxiv.org/abs/2506.08837) (arXiv:2506.08837)

*impossible* 이라는 단어가 요점이다. 탐지·필터링이 아니라 **불가능하게 만드는 구조**다. 실무 번역은 대략 이렇게 된다 — 신뢰 못 할 내용을 읽은 세션과 외부로 나갈 수 있는 세션을 분리하거나, 의존성 설치를 에이전트 런타임 밖(빌드 단계)으로 빼서 실행 중에는 `pypi.org` 자체를 닫아버리는 것. 어느 쪽이든 "잘 판단하도록 지시한다"가 아니라 **채널을 없애는** 방향이다.

## 5. 두 층은 누적이지 대체가 아니다 — 그림의 5번

그림의 마지막 항목이 이 세션 얘기를 한다. 이 대화에서 나는 `curl` 을 마음대로 썼고(내 PC 엔 프록시 allowlist 가 없다), 대신 하네스 분류기가 민감한 패턴을 막았다. OpenShell 식 환경이었다면 같은 명령이 분류기를 통과했더라도 커널이 `EPERM` 이나 403 을 냈을 것이다.

두 층의 성격을 나란히 놓으면 왜 "누적"이 맞는지가 보인다.

| | 하네스 분류기 | 커널·프록시 통제 |
| --- | --- | --- |
| 판단 대상 | 명령의 **모양**(패턴·의미) | 프로세스의 **능력**(syscall·경로·목적지) |
| 우회 방법 | 다르게 표현, 인코딩, 분할 | 없음 — 표현을 바꿔도 능력이 안 생김 |
| 못 막는 것 | 평범해 보이는 위험한 일 | **허용된 일을 나쁜 의도로** 하는 것 |
| 실패 시 | 조용히 통과 | 명시적 거부(`EPERM`/403) |

**실패 모드가 서로 다르다는 게 핵심이다.** 분류기는 재표현에 약하고 커널은 재표현에 강하다. 반대로 커널은 의도를 볼 수 없고 분류기는 의도를 본다. 겹치는 부분이 적으니 두 층을 쌓는 건 중복이 아니다.

다만 정직하게 덧붙이면, **누적이 곱셈은 아니다.** 4절의 두 구멍은 두 층 모두 못 막는다. `SOUL.md` 수정은 정책이 허락한 쓰기이고, PyPI 로의 유출은 정책이 허락한 통신이다. 층을 아무리 쌓아도 *허용 범위 안에서 벌어지는 일*은 그 범위를 좁히는 것 말고 방법이 없다.

## 마무리 — 이 그림이 잘한 것

이 정리표에서 내가 가장 높게 치는 건 1·2·3번이 아니라 **4번을 적어뒀다는 사실 자체**다.

보안 실습 기록은 막은 걸 세는 쪽으로 기울기 쉽다. 막힌 건 눈에 보이고(403, `Permission denied`), 안 막힌 건 아무 일도 안 일어나서 안 보인다. "`pip install` 이 됐다"는 보통 성공 로그로 적히지 열린 출구로 적히지 않는다. 그걸 실패 모드 칸에 옮겨 적은 게 이 표의 실력이다.

남은 숙제도 정직하게 적어두면 이렇다.

- **3번의 증거를 바꿔야 한다.** 바이너리 부재 말고, 안에서 정책을 되돌리는 연산이 없다는 쪽으로.
- **네트워크 정책의 소유 위치는 아직 미확인이다.** 커널 계약으로 보장되는 Landlock/seccomp 와 달리 프록시 설정은 별도 확인이 필요하다.
- **효과 크기 숫자는 이 글에 없다.** 이런 샌드박스가 실제 사고를 얼마나 줄이는지에 대한 중립 제3자 측정을 찾지 못했다. 구조 얘기까지가 이 글의 범위다.

---

## References

- [The lethal trifecta for AI agents: private data, untrusted content, and external communication](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) — Simon Willison, 2025-06-16. 세 요소의 정의와 "HTTP 요청이 가능하면 유출도 가능하다"
- [Design Patterns for Securing LLM Agents against Prompt Injections](https://arxiv.org/abs/2506.08837) — arXiv:2506.08837, Beurer-Kellner 외
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [Landlock — Linux kernel documentation](https://docs.kernel.org/userspace-api/landlock.html) — 정책 레이어 stacking, 제약은 추가만 가능
- [Seccomp BPF — Linux kernel documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html) — `no_new_privs` 요구 사항
- [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html) — netns 가 분리하는 것들
- [Open Policy Agent — Philosophy](https://www.openpolicyagent.org/docs/philosophy) — 정책 결정의 오프로드
- [RFC 9110 §9.3.6 CONNECT](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6) — 터널은 호스트·포트만 알고 내용은 blind forwarding
- 같은 날 앞선 글: [네 가지 OS 메커니즘, 네 가지 검증 가능한 질문](https://myoungsoo7.github.io/2026/09/20/four-os-mechanisms-four-verifiable-questions/) · [에이전트가 자기 파일 일곱 개를 설명했다](https://myoungsoo7.github.io/2026/09/20/openclaw-workspace-files-and-the-memory-canary/) · [에이전트 정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/)
