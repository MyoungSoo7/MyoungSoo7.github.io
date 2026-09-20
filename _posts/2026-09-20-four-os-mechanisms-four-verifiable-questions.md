---
layout: post
title: "네 가지 OS 메커니즘, 네 가지 검증 가능한 질문 — 표 한 장을 커널 문서로 되짚다"
date: 2026-09-20 19:05:47 +0900
categories: [Security, Linux]
tags: [Landlock, seccomp, netns, OPA, Sandbox, Agent, Linux, Kernel]
---

오늘 네 편을 쓰는 동안 같은 결론이 계속 돌아왔다. **정책은 에이전트가 만질 수 없는 곳에 둬야 한다.** [브라우저 자바스크립트에 있던 가드레일](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/)도, [워크스페이스의 `POLICY.md`](https://myoungsoo7.github.io/2026/09/20/openclaw-workspace-files-and-the-memory-canary/)도 같은 이유로 실패한다.

그런데 "만질 수 없는 곳"이 대체 어디냐. 이 표가 그 답을 네 칸으로 적어놨다.

![네 가지 OS 메커니즘 = 네 가지 검증 가능한 질문](/assets/images/sandbox/four-os-mechanisms.jpg)

옮겨 적으면 이렇다.

| 질문 | 메커니즘 | 내용 |
| --- | --- | --- |
| 어디로 연결할 수 있나? | `netns` + CONNECT proxy + OPA | 격리된 네트워크 스택, 기본 닫힘, 유일한 출구는 HTTP CONNECT 프록시, OPA 가 binary·host·port·path 로 판정 |
| 어떤 파일에 닿나? | `Landlock` | LSM, 정책이 준 경로로 새 파일 연산 제한 (compat 모드·OverlayFS·미리 연 핸들은 주의) |
| 어떤 커널 연산을 요청할 수 있나? | `seccomp` | BPF 허용목록, 거부 시 실행 전 EPERM. ptrace·mount·setuid 제외 |
| 시작 권한은? | non-root sandbox 유저 | 익스플로잇도 낮은 권한에서 시작 (escalation 불가능의 증명은 아님) |

이 글은 이 네 줄을 리눅스 커널 문서·man7·OPA 1차 문서로 되짚은 기록이다. 결론부터 적으면, **이 표가 넷으로 나뉜 건 취향이 아니라 각 메커니즘이 "볼 수 있는 것"이 서로 다르기 때문이다.**

## 1. 왜 하필 넷인가 — 각자 볼 수 있는 게 다르다

제일 먼저 짚을 건 seccomp 의 한계다. 커널 문서가 직접 적는다.

> BPF programs may **not dereference pointers** which constrains all filters to solely evaluating the system call arguments directly.
> — [Seccomp BPF (SECure COMPuting with filters), The Linux Kernel documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html)

이 한 문장이 표의 구조를 결정한다. seccomp 필터는 시스템콜 번호와 **인자 값**만 본다. `openat()` 의 두 번째 인자는 *경로 문자열이 있는 메모리 주소*인데, 필터는 그 포인터를 따라갈 수 없다. 그래서 seccomp 는 **"`openat` 을 허용할지"는 정해도 "`/workspace` 아래만 허용할지"는 정하지 못한다.**

포인터를 못 따라가는 게 성의 부족이 아니라 설계다. 같은 문서가 이유를 붙여놨다 — 인자를 나중에 다시 읽으면 TOCTOU(time-of-check-time-of-use) 공격이 열리기 때문이고, 값만 보게 강제하면 그 부류가 원천적으로 사라진다.

경로를 봐야 하는 일은 그래서 다른 층으로 간다. 그게 Landlock 이다. 그리고 커널 문서는 seccomp 에 대해 아예 이렇게 못 박는다.

> **System call filtering isn't a sandbox.** It provides a clearly defined mechanism for minimizing the exposed kernel surface. **It is meant to be a tool for sandbox developers to use.**

넷으로 나뉜 이유가 여기 다 있다. 넷 중 어느 하나도 혼자서는 샌드박스가 아니다. 표를 "네 가지 방어"로 읽으면 과장이고, **"네 가지 다른 질문에 답하는 네 가지 도구"로 읽으면 정확하다.** 표 제목이 실제로 그렇게 쓰여 있다는 게 이 표의 가장 좋은 점이다.

## 2. 한 줄씩

### ① 어디로 연결할 수 있나 — netns + CONNECT 프록시 + OPA

`netns` 가 무엇을 격리하는지는 man7 이 나열한다.

> Network namespaces provide isolation of the system resources associated with networking: network devices, IPv4 and IPv6 protocol stacks, IP routing tables, firewall rules, the `/proc/net` directory …, port numbers (sockets), and so on. In addition, network namespaces isolate the UNIX domain **abstract** socket namespace.
> — [network_namespaces(7)](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)

"기본 닫힘"이 공짜로 나오는 지점이 여기다. 새 네트워크 네임스페이스에는 루프백 말고 아무 장치도 없다. 밖으로 나가려면 누가 `veth` 쌍을 놓아주거나 물리 장치를 옮겨줘야 한다 — 그리고 man7 이 적듯 **물리 장치는 정확히 한 네임스페이스에만 존재할 수 있다.** 아무것도 안 하면 밖이 없는 상태가 기본값이라, 방화벽 규칙을 잘 써서 막는 것과는 성격이 다르다.

그 위에 "유일한 출구는 HTTP CONNECT 프록시"가 온다. 여기서 이 표를 읽을 때 **가장 먼저 물어봐야 할 것**이 생긴다. CONNECT 의 요청 타깃은 RFC 가 정한 대로 host:port 뿐이다.

> The CONNECT method requests that the recipient establish a tunnel to the destination origin server identified by the request target and, if successful, thereafter restrict its behavior to **blind forwarding of data**, in both directions, until the tunnel is closed.
> CONNECT uses a special form of request target … consisting of only the **host and port number** of the tunnel destination, separated by a colon.
> — [RFC 9110 §9.3.6](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6)

그런데 표는 OPA 가 **binary·host·port·path** 로 판정한다고 적는다. `path` 가 문제다. TLS 터널이 서면 프록시는 그 뒤를 "blind forwarding" 할 뿐이라 URL 경로를 볼 수 없다. 그러니 둘 중 하나여야 한다 — **프록시가 TLS 를 종료하고 내용을 본다**(즉 샌드박스 안에 프록시의 CA 를 심어야 한다), 혹은 **경로 판정은 터널이 아닌 평문 요청에만 적용된다.** 어느 쪽인지는 표만 보고는 알 수 없다. 이건 흠이 아니라, 이런 설계를 받았을 때 **첫 번째로 확인해야 할 질문**이다. 전자라면 "샌드박스 안에 벤더 CA 가 들어간다"는 뜻이고, 그건 별도로 감수할지 말지 정해야 하는 항목이다.

OPA 의 역할도 정확히 적어둘 값이 있다.

> Services **offload policy decisions** to OPA by executing queries. OPA evaluates policies and data to **produce query results (which are sent back to the client).**
> — [OPA Philosophy, Open Policy Agent](https://www.openpolicyagent.org/docs/philosophy)

**OPA 는 판정하고, 집행은 프록시가 한다.** 이 분리가 이 표에서 중요한 이유는, 오늘 반복된 결론이 여기서도 한 번 더 성립하기 때문이다. 정책을 서비스 코드에서 떼어내 따로 읽고 쓰고 버전 관리할 수 있게 하는 게 OPA 의 존재 이유고(문서의 표현으로는 *decouple policy from that software service*), 그건 정책이 **집행자 바깥에** 있어야 한다는 말과 같다.

### ② 어떤 파일에 닿나 — Landlock

> The goal of Landlock is to enable restriction of ambient rights … Because Landlock is a **stackable LSM**, it makes it possible to create safe security sandboxes as new security layers in addition to the existing system-wide access-controls. … Landlock empowers **any process, including unprivileged ones, to securely restrict themselves.**
> — [Landlock: unprivileged access control, The Linux Kernel documentation](https://docs.kernel.org/userspace-api/landlock.html)

핵심은 "자기 자신을 제한한다"는 쪽이다. root 가 아니어도 스스로 권한을 깎을 수 있고, 한 번 깎으면 그 스레드와 **이후의 자식**에게 상속된다. 표에 적힌 "정책이 준 경로로 새 파일 연산 제한"이 이걸 가리킨다.

표가 괄호로 달아둔 주의사항이 실제 문서의 *Current limitations* 와 맞는다. 다만 문서 쪽이 더 구체적이라 그대로 옮긴다.

- **미리 연 핸들.** `LANDLOCK_ACCESS_FS_IOCTL_DEV` 는 *newly opened* 장치 파일에만 걸린다. 문서의 표현으로는 *"pre-existing file descriptors like stdin, stdout and stderr are unaffected"* — 이미 열린 fd 를 물려받았다면 그건 Landlock 밖이다.
- **`chroot` 는 안 막는다.** 파일시스템 토폴로지 변경(`mount`, `pivot_root`)은 막지만 *"However, `chroot(2)` calls are not denied."*
- **파이프·소켓은 명시적으로 못 막는다.** `/proc/<pid>/fd/*` 로 닿는, 사용자 가시 파일시스템에서 오지 않은 객체들은 현재 규칙으로 표현할 수 없다(ptrace 제약으로 간접적으로 가려질 뿐이다).
- **16층 한계.** 스택 가능한 LSM 이라 계속 쌓을 수 있지만 16 층에서 `E2BIG` 다. 셸이나 컨테이너 매니저처럼 *자식도 자기를 샌드박싱하는* 프로그램을 돌릴 거면 문서가 대놓고 주의를 준다.

한 가지 표를 보완할 것도 있다. **Landlock 은 파일만 하는 게 아니다.** 커널 문서는 규칙 유형이 둘이라고 적는다 — 파일시스템 규칙, 그리고 *"Network rules (since ABI v4 for TCP and v10 for UDP)"*. 즉 TCP 포트 bind/connect 제한은 Landlock 으로도 된다. 그런데도 이 설계가 네트워크를 netns + 프록시로 뺀 건 커널이 못 해서가 아니라 **"어느 호스트냐"를 판정하려면 포트 번호로는 부족하기 때문**이라고 읽는 게 맞다. 이건 표가 생략한 배경이지 오류는 아니다.

### ③ 어떤 커널 연산을 요청할 수 있나 — seccomp

허용목록 방식과 "거부 시 실행 전 `EPERM`" 은 `SECCOMP_RET_ERRNO` 의 동작 그대로다. 필터가 그 값을 돌려주면 시스템콜은 **실행되지 않고** 지정한 errno 로 돌아간다.

표에 없지만 같이 알아야 할 게 둘 있다.

**첫째, `no_new_privs` 가 전제다.**

> Prior to use, the task must call `prctl(PR_SET_NO_NEW_PRIVS, 1)` or run with `CAP_SYS_ADMIN` privileges in its namespace. If these are not true, `-EACCES` will be returned. This requirement ensures that filter programs cannot be applied to child processes with **greater privileges** than the task that installed them.

이게 네 번째 줄(non-root)과 세 번째 줄을 묶는 고리다. 비특권 프로세스가 seccomp 를 걸려면 `no_new_privs` 를 켜야 하고, 그게 켜지면 SUID 바이너리를 실행해도 권한이 올라가지 않는다. 표의 두 줄이 사실은 한 덩어리다.

**둘째, 아키텍처를 안 보면 뚫린다.**

> The biggest pitfall to avoid during use is filtering on system call number **without checking the architecture value.** … If the numbers in the different calling conventions overlap, then checks in the filters may be abused. **Always check the arch value!**

허용목록을 썼다는 사실만으로는 안전이 보장되지 않는다는 뜻이다. 이 표를 받았을 때 검증할 수 있는 구체적 항목이기도 하다.

### ④ 시작 권한은 — non-root

이 줄에서 제일 값이 나가는 건 메커니즘이 아니라 괄호다. **"escalation 불가능의 증명은 아님."**

보안 설명에서 이런 문장은 잘 안 보인다. 보통은 "non-root 로 실행하여 안전합니다"에서 끝난다. 낮은 권한에서 시작한다는 건 익스플로잇의 **출발점**을 낮추는 것이지 **도착점**을 막는 게 아니고, 이 표는 그걸 스스로 적어뒀다. 앞의 셋이 다 커널 기능인데 이 줄만 운영 관행인 것도 솔직한 배치다.

## 3. 이 표의 진짜 값 — 왼쪽 열이 질문형이다

기술 문서에서 보안 설계를 설명할 때 흔한 형태는 "우리는 A·B·C 를 씁니다"다. 이 표는 왼쪽 열이 **질문**이다. 그 차이가 실무에서 크다. 각 행이 **따로 테스트 가능한 명제**가 되기 때문이다.

| 질문 | 확인 방법 (샌드박스 안에서) |
| --- | --- |
| 어디로 연결할 수 있나? | 프록시를 거치지 않고 임의 IP:포트로 직접 연결 시도 → 실패해야 한다. 허용 안 된 호스트로 CONNECT → 거부여야 한다 |
| 어떤 파일에 닿나? | 정책 경로 밖 절대경로로 쓰기 시도 → `EACCES`. 그리고 **물려받은 fd** 로도 같은 일을 해본다 (여기가 문서가 경고한 구멍) |
| 어떤 커널 연산을 요청할 수 있나? | `ptrace`·`mount`·`setuid` 호출 → 실행 전 `EPERM` 이어야 한다 |
| 시작 권한은? | `id` 로 uid 확인, `/proc/self/status` 의 `NoNewPrivs` 가 `1` 인지 확인 |

네 줄 모두 "믿어주세요"가 아니라 관측으로 끝난다. 오늘 앞 글에서 에이전트의 기억을 [카나리아 토큰 한 줄로 검증](https://myoungsoo7.github.io/2026/09/20/openclaw-workspace-files-and-the-memory-canary/)했던 것과 같은 성격이다 — **자연어 확언 대신 검증 가능한 출력을 요구한다.**

## 4. 넷을 다 해도 안 막히는 것

정직하게 남겨둘 항목들이다. 표와 커널 문서에서 직접 나오는 것만 적는다.

- **이미 열린 파일 디스크립터.** Landlock 이 서기 전에 열린 핸들은 계속 쓸 수 있다. 샌드박스를 세우는 순서가 곧 보안 경계다.
- **`/proc/<pid>/fd/*` 로 닿는 파이프·소켓.** 현재 Landlock 규칙으로는 명시적 제한 대상이 아니다.
- **허용된 출구로 나가는 유출.** OPA 가 허락한 호스트로 민감한 데이터를 보내는 건 네 메커니즘 중 어느 것도 막지 않는다. 이건 *어디로* 의 문제지 *무엇을* 의 문제가 아니고, 표는 *어디로*만 다룬다.
- **커널 자체의 버그.** seccomp 는 노출 면적을 줄이는 도구이지 면적을 0 으로 만드는 도구가 아니다. 커널 문서가 스스로 "샌드박스가 아니다"라고 쓴 이유다.
- **효과 크기에 대한 중립 측정은 이 글에 없다.** "이런 샌드박스를 쓰면 사고가 몇 % 줄어드는가"에 대한 제3자 측정치는 찾지 못했다. 이 글이 주장하는 건 효과가 아니라 **구조**다.

## 마무리

표 한 장을 커널 문서로 되짚어보니, 넷으로 쪼갠 게 가장 잘한 선택이었다. seccomp 는 포인터를 못 따라가서 경로를 모르고, Landlock 은 파일 계층을 보지만 상대 호스트가 누군지 모르고, 프록시는 호스트를 알지만 어떤 바이너리가 부르는지 판단하지 않고, 그 판단을 OPA 로 뺐다. **각자 못 보는 것이 있어서 넷이 된 것이다.**

그리고 오늘 네 편 내내 돌아온 문장이 여기서 가장 구체적인 형태를 얻는다. 정책이 있어야 할 "에이전트가 만질 수 없는 곳"은 결국 **프로세스가 자기 권한을 깎아둔 커널 쪽과, 그 판정을 밖으로 빼놓은 정책 엔진**이다. 워크스페이스의 마크다운 파일이 아니라.

---

## References

- [Landlock: unprivileged access control — The Linux Kernel documentation](https://docs.kernel.org/userspace-api/landlock.html) — stackable LSM, 규칙 유형 두 가지(파일시스템 / 네트워크 ABI v4·v10), Current limitations (chroot 미차단, `/proc/<pid>/fd/*`, 16층 `E2BIG`, IOCTL 은 newly opened 만)
- [Seccomp BPF (SECure COMPuting with filters) — The Linux Kernel documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html) — "isn't a sandbox", 포인터 역참조 불가와 TOCTOU, `no_new_privs` 전제, arch 확인 pitfall, vDSO·vsyscall caveat
- [network_namespaces(7) — man7.org](https://man7.org/linux/man-pages/man7/network_namespaces.7.html) — 격리 대상 목록, 물리 장치는 한 네임스페이스에만, veth
- [OPA Philosophy — Open Policy Agent](https://www.openpolicyagent.org/docs/philosophy) — 정책 판정의 오프로드, 결과를 호출자에게 돌려주는 구조
- [RFC 9110 §9.3.6 CONNECT — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.3.6) — 요청 타깃은 host:port, 성립 후 blind forwarding
- 같은 날 앞선 글: [정책은 브라우저에 남았다](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/) · [에이전트 정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/) · [워크스페이스 파일 일곱 개](https://myoungsoo7.github.io/2026/09/20/openclaw-workspace-files-and-the-memory-canary/)

*(커널 문서·man7·OPA·RFC 인용은 모두 2026-09-20 확인 시점 기준이다. 표 자체의 출처 제품은 명시되어 있지 않아 이 글에서는 특정하지 않았고, 표에 적힌 내용의 참·거짓은 위 1차 문서로만 따졌다.)*
