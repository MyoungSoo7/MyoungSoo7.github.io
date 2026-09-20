---
layout: post
title: "NemoClaw 대시보드 한 장 — 4 vCPU 짜리 상자가 120B 모델을 '돌리는' 방법"
date: 2026-09-20 18:33:22 +0900
categories: [AI, Infrastructure]
tags: [NemoClaw, OpenShell, OpenClaw, Nemotron, OCSF, Agent, Security]
---

앞 글들은 전부 **문서를 읽고 쓴 글**이었다 — [정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/), [GPU 를 빌린다는 것](https://myoungsoo7.github.io/2026/09/20/nvidia-brev-gpu-stop-is-a-capacity-bet/). 그리고 직전 글은 Brev 콘솔에서 **밖에서 본** 그 기계 한 대였다.

이번엔 같은 기계의 **안쪽**이다. 그 위에 올라간 NemoClaw 대시보드를 한 장 찍은 것.

![NemoClaw v0.1.0 대시보드 개요 화면 — PROCESSING POWER 34% (AMD EPYC 7B13, 4 vCPU), MEMORY USAGE 1.3 GB / 15.6 GB, DISK 16.4 GB / 266.3 GB, SECURITY STATUS 에 ALLOWED SITES 20 · NETWORK POLICIES 12, MY-ASSISTANT 가 nvidia/nemotron-3-super-120b-a12b 로 RUNNING, 하단에 OCSF 로그 스트림과 SERVICES 7/7](/assets/images/nemoclaw/nemoclaw-dashboard-overview.jpg)

한 장인데 읽을 게 꽤 있다. 위에서부터 내려가 보자.

## 1. 가장 이상한 줄 — GPU 가 없는데 120B 가 "RUNNING"

화면이 동시에 말하고 있는 두 가지다.

| 패널 | 화면에 찍힌 값 |
| --- | --- |
| PROCESSING POWER | `34%` · `AMD EPYC 7B13 // 4 vCPU` · `ACTIVITY: 1.37` |
| MEMORY USAGE | `1.3 GB / 15.6 GB` · `DISK: 16.4 GB / 266.3 GB` |
| MY-ASSISTANT | `RUNNING` · `NVIDIA/NEMOTRON-3-SUPER-120B-A12B` · `UPTIME: 51 minutes` |

GPU 패널은 없다. CPU 4개에 램 15.6 GB 다. 그런데 에이전트 옆에 붙은 모델 이름은 `nemotron-3-super-120b-a12b` 다.

NVIDIA 가 공개한 이 모델의 모델카드를 보면 숫자가 이렇다.

| 항목 | 값 |
| --- | --- |
| 파라미터 | 120B 전체 / 12B 활성 |
| 아키텍처 | LatentMoE — Mamba-2 + MoE + Attention 하이브리드, MTP 포함 |
| 컨텍스트 | 최대 1M 토큰 |
| **최소 GPU 요구사항** | **8× H100-80GB** |

— [NVIDIA-Nemotron-3-Super-120B-A12B 모델카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard)

H100 여덟 장이 최소인 모델이 H100 0장짜리 상자에서 "RUNNING" 으로 뜬다. 모순이 아니라, **이 화면이 말하는 "RUNNING" 은 모델이 아니라 에이전트**라는 뜻이다.

NemoClaw 문서가 이 부분을 명시적으로 적어놨다.

> Inference requests from the agent never leave the sandbox directly. OpenShell intercepts every inference call and routes it to the configured provider. (…) The sandbox then talks to `inference.local`, while the host owns the actual provider credential and upstream endpoint.
>
> — [NemoClaw Architecture Overview](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/about/how-it-works)

즉 샌드박스 안의 에이전트는 `https://inference.local/v1/...` 만 안다. 그게 실제로 어디로 나가는지 — NVIDIA 호스팅 엔드포인트인지, NIM 컨테이너인지, 로컬 Ollama 인지 — 는 게이트웨이가 정하고, **자격증명은 샌드박스 밖에 있다.** 에이전트는 자기가 쓰는 모델의 키를 가진 적이 없다.

그래서 이 4 vCPU 상자가 하는 일은 추론이 아니다. 에이전트 프로세스, 게이트웨이, 정책 엔진, 로그 파이프라인을 돌리는 일이다. 무거운 건 전부 밖에 있다.

> 화면의 모델 이름 옆에 `UNAVAILABLE` 이 하나 더 붙어 있다. NemoClaw 문서 기준으로 `status` 의 추론 라인은 샌드박스 **안에서** `https://inference.local/v1/models` 를 찔러 본 결과다([Monitor Sandbox Activity](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/monitoring/monitor-sandbox-activity)). 이 배지가 정확히 그 프로브인지까지는 화면만으로 단정할 수 없어 여기서는 "추론 경로 표시가 비어 있다" 정도로만 적는다.

## 2. SECURITY STATUS — 숫자 둘과 빈칸 하나

| 칸 | 값 |
| --- | --- |
| BLOCKED | `Unavailable` |
| ALLOWED SITES | `20` |
| NETWORK POLICIES | `12` |
| 각주 | `1 AGENT · DENIAL TELEMETRY UNAVAILABLE` |

`20 ALLOWED SITES` 가 이 스택의 성격을 그대로 보여준다. NemoClaw 가 기본으로 까는 정책은 **전부 막고 목록에 적힌 것만 연다**.

> NemoClaw ships a default policy in `nemoclaw-blueprint/policies/openclaw-sandbox.yaml` that denies all network egress except explicitly listed endpoints.
>
> — [NVIDIA/NemoClaw README](https://github.com/NVIDIA/NemoClaw)

목록에 없는 데를 에이전트가 찌르면 그 자리에서 막히고, 운영자에게 승인해 달라고 TUI 에 뜬다. 승인해도 그 세션에만 살고 baseline 정책 파일에는 안 적힌다(같은 문서). 에이전트가 자기 감옥의 열쇠를 못 만든다는 뜻이다.

문제는 `BLOCKED: Unavailable` 쪽이다. **막은 횟수를 못 세고 있다.** 허용 목록은 20개라고 말할 수 있는데, 실제로 몇 번 거부했는지는 빈칸이다.

여기부터는 화면만으로 단정할 수 없어 추측으로 적는다 — 근거는 OpenShell 문서에 있는 두 줄이다. 하나는 게이트웨이의 로그 버퍼가 **디스크에 안 남고 바운드돼 있다**는 것, 다른 하나는 완전한 OCSF JSON 내보내기가 **기본값이 아니라 옵트인**(`ocsf_json_enabled`)이라는 것이다([Accessing Logs](https://docs.nvidia.com/openshell/dev/observability/accessing-logs), [OCSF JSON Export](https://docs.nvidia.com/openshell/observability/ocsf-json-export)). 거부 건수를 세려면 이벤트가 어딘가 쌓여 있어야 하는데, 기본 상태에서는 쌓이는 곳이 휘발성 버퍼뿐이다.

그게 맞다면 교훈은 단순하다. **막는 기능과 막은 걸 세는 기능은 별개고, 후자는 켜야 생긴다.** 보안 화면에서 제일 중요한 숫자가 기본값으로 비어 있다.

## 3. LOGS — OCSF 한 줄 읽는 법

하단 로그 패널에 같은 모양이 계속 흐른다.

```
AGT 18:24:18 [1789896258.484] [sandbox] [OCSF ] [ocsf] NET:OPEN  [INFO] 127.0.0.1:18789/tcp
AGT 18:24:18 [1789896258.488] [sandbox] [OCSF ] [ocsf] NET:CLOSE [INFO] 127.0.0.1:18789/tcp
```

이건 NemoClaw 가 만든 포맷이 아니라 **OpenShell 의 표준 로그 라인**이다. 문서의 예시와 열 배치가 그대로 같다([Accessing Logs](https://docs.nvidia.com/openshell/dev/observability/accessing-logs)).

`OCSF` 는 **Open Cybersecurity Schema Framework** — 보안 텔레메트리를 도구 간에 정규화하는 공개 표준이고, OpenShell 은 샌드박스 이벤트를 여기에 매핑한다. 클래스 표는 이렇다.

| 접두사 | OCSF 클래스 | Class UID | 담는 것 |
| --- | --- | --- | --- |
| `NET:` | Network Activity | 4001 | TCP CONNECT 터널, 우회 탐지, DNS 실패 |
| `HTTP:` | HTTP Activity | 4002 | L7 요청과 그 판정 |
| `SSH:` | SSH Activity | 4007 | 핸드셰이크·인증·채널 |
| `PROC:` | Process Activity | 1007 | 프로세스 시작·종료·타임아웃 |
| `FINDING:` | Detection Finding | 2004 | 보안 발견(논스 재사용, 프록시 우회 등) |
| `CONFIG:` | Device Config State Change | 5019 | 정책 로드/리로드, Landlock, TLS, 추론 라우트 |
| `LIFECYCLE:` | Application Lifecycle | 6002 | 샌드박스 수퍼바이저 기동 |

— [OpenShell Sandbox Logging](https://docs.nvidia.com/openshell/observability/logging)

대괄호 안의 `[INFO]` 는 심각도다. 같은 문서의 표에 따르면 `[INFO]` 는 허용된 연결·성공한 동작, **거부는 `[MED]`, 보안 발견은 `[HIGH]`, 프로세스 타임아웃 킬은 `[CRIT]`** 이다. 그래서 이 화면의 로그를 훑는 법은 간단하다 — `[MED]` 이상만 눈에 걸리면 된다. 지금 화면엔 하나도 없다.

## 4. 로그가 자기 자신을 보고 있다

이 로그에서 진짜 재미있는 건 목적지다. 전부 `127.0.0.1:18789` 다.

18789 는 **NemoClaw 대시보드가 쓰는 기본 포트**다.

> The NemoClaw dashboard uses port `18789` by default and the gateway uses port `8080`.
>
> — [NemoClaw Troubleshooting](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/reference/troubleshooting)

그러니까 지금 로그 패널에 흐르는 건 외부 트래픽이 아니라 **내가 보고 있는 이 대시보드가 자기 백엔드를 폴링하는 소리**다. 화면이 열리면 로그가 생기고, 그 로그가 화면에 뜬다.

양이 만만치 않다. 화면에 찍힌 스무 줄 남짓이 전부 같은 초(`18:24:18`) 안이고, 에포크 소수부로 보면 `.484` 부터 `.668` 까지 — **0.2초도 안 되는 사이**다. OPEN/CLOSE 가 쌍이니 연결 자체는 그 절반이지만, 그래도 초당 수십 건이 찍히는 속도다.

(참고로 저 에포크는 진짜다. `date -r 1789896258` 을 돌리면 `2026-09-20 18:24:18 KST` 가 나온다 — 줄 앞머리의 `18:24:18` 과 정확히 같은 시각이다.)

그래서 앞 절의 추측이 여기서 한 번 더 힘을 받는다. 게이트웨이의 로그 버퍼는 바운드돼 있고 넘치면 **블로킹이 아니라 드롭**한다고 문서에 적혀 있다(같은 Accessing Logs 문서). 루프백 폴링이 초당 수십 건씩 같은 버퍼를 지나간다면, 정작 봐야 할 `[MED]` 거부 한 건이 그 안에서 밀려날 수 있다. 문서가 권하는 해법도 같은 자리에 있다 — 오래 남길 거면 샌드박스 안의 로그 파일을 보거나 OCSF JSON 내보내기를 켜서 밖으로 실어내라는 것.

## 5. SERVICES 7/7 — 스택이 몇 층인지

우측 하단 목록이 이 상자에 실제로 뭐가 떠 있는지 말해준다.

```
DOCKER
GATEWAY
OPENCLAW
OPENSHELL
NEMOCLAW CLI
NODE.JS
PYTHON
```

이름만 봐도 층이 갈린다.

- **OPENSHELL** — 런타임. 샌드박스 컨테이너, 자격증명 보관 게이트웨이, 추론 프록시, 정책 집행.
- **OPENCLAW** — 그 안에서 도는 에이전트 하네스.
- **NEMOCLAW CLI** — 이 둘을 묶어 온보딩·수명주기·정책을 굴리는 호스트 쪽 도구.

NVIDIA 가 제품 FAQ 에서 이 구분을 한 문장으로 정리해놨다.

> NemoClaw is the full agent deployment package—models, harness, tools, and runtime. OpenShell is the secure runtime inside it that enforces what the agent can access: files, networks, credentials, and tools.
>
> — [NVIDIA NemoClaw 제품 페이지](https://www.nvidia.com/en-us/ai/nemoclaw/)

그리고 `GATEWAY` 가 하나 더 헷갈리는 자리인데, 문서 기준으로 게이트웨이는 **둘**이다. 호스트 쪽 OpenShell 게이트웨이(샌드박스 수명주기·포트 포워드·정책)와, 샌드박스 **안**의 OpenClaw 게이트웨이(대시보드·에이전트 API). 기동 순서는 컨테이너 → OpenShell 게이트웨이 → OpenClaw 게이트웨이다([Troubleshooting](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/reference/troubleshooting)). 장애를 볼 때 "게이트웨이가 죽었다"는 말이 두 가지를 가리킬 수 있다는 뜻이라 적어둔다.

`NODE.JS` 와 `PYTHON` 이 서비스 목록에 같이 있는 것도 우연이 아니다. NemoClaw 의 OpenClaw 통합 레이어는 TypeScript 패키지고, 블루프린트 러너 쪽은 Python 아티팩트다(위 아키텍처 문서·README). 한 상자에 두 런타임이 다 필요한 구조다.

## 6. 화면만으로는 모르는 것

정직하게 남겨둔다.

- **이 대시보드가 어디에 바인딩돼 있는지.** 문서 기본값은 루프백(`127.0.0.1`)이고 원격 노출은 명시적 옵트인이다([Gateway and Secret Controls](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/security/security-controls/gateway-authentication-controls)). 화면에 보이는 주소가 전부 `127.0.0.1` 인 건 기본값과 일관되지만, 그것만으로 "외부에 안 열려 있다"고 결론 낼 수는 없다.
- **`ALLOWED SITES 20` 의 내용.** 개수만 보이고 목록은 안 보인다. 20개가 뭔지는 정책 YAML 을 봐야 안다.
- **`34%` 를 누가 먹고 있는지.** 에이전트인지, 로그 파이프라인인지, 대시보드 폴링 자체인지 화면은 말해주지 않는다.
- **NemoClaw 는 알파다.** README 가 그렇게 적어놨다 — "early preview starting March 16, 2026. This software is not production-ready. Interfaces, APIs, and behavior may change without notice."

## 마무리

한 장에서 건진 건 결국 하나다. **이 화면에서 "돌고 있다"고 말하는 것과, 실제로 이 상자에서 돌고 있는 것은 다르다.**

120B 모델은 여기 없다. 여기 있는 건 그 모델을 부를 자격을 *에이전트에게 주지 않은 채* 대신 불러주는 층이다. 4 vCPU 로 충분한 이유가 그거고, `20 ALLOWED SITES` 가 숫자로 떠 있는 이유도 그거다.

그리고 그 층이 남기는 기록은 기본값으로는 휘발성이다. 막는 건 켜져 있는데, **막은 걸 세는 건 따로 켜야 한다.**

## References

- [NVIDIA/NemoClaw — GitHub README](https://github.com/NVIDIA/NemoClaw) — 기본 정책(전면 차단 + 명시 허용), 알파 고지, 구성요소 표
- [NVIDIA NemoClaw 제품 페이지](https://www.nvidia.com/en-us/ai/nemoclaw/) — NemoClaw 와 OpenShell 의 역할 구분
- [NemoClaw — Architecture Overview](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/about/how-it-works) — `inference.local` 라우팅, 자격증명이 샌드박스 밖에 있는 구조, 보호 계층 표
- [NemoClaw — Overview](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/about/overview) — 지원 에이전트와 제공 범위
- [NemoClaw — Troubleshooting](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/reference/troubleshooting) — 대시보드 기본 포트 18789, 게이트웨이 두 개의 기동 순서
- [NemoClaw — Monitor Sandbox Activity](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/monitoring/monitor-sandbox-activity) — `status` 의 추론 프로브 동작
- [NemoClaw — Gateway and Secret Controls](https://docs.nvidia.com/nemoclaw/user-guide/openclaw/security/security-controls/gateway-authentication-controls) — 루프백 바인딩 기본값
- [OpenShell — Sandbox Logging](https://docs.nvidia.com/openshell/observability/logging) — OCSF 클래스 표, 심각도 태그 의미
- [OpenShell — Accessing Logs](https://docs.nvidia.com/openshell/dev/observability/accessing-logs) — CLI 로그 라인 포맷, 바운드 버퍼와 드롭 동작
- [OpenShell — OCSF JSON Export](https://docs.nvidia.com/openshell/observability/ocsf-json-export) — `ocsf_json_enabled` 옵트인
- [NVIDIA-Nemotron-3-Super-120B-A12B 모델카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard) — 120B/12B, 최소 8× H100-80GB
- 오늘 앞선 글: [에이전트 정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/) · [GPU 를 빌린다는 것](https://myoungsoo7.github.io/2026/09/20/nvidia-brev-gpu-stop-is-a-capacity-bet/)

> 화면의 수치(34%, 1.3 GB / 15.6 GB, 20, 12, 51 minutes 등)는 모두 2026-09-20 18:24 KST 에 찍힌 저 한 장에서 읽은 것이고, 재현 가능한 벤치마크가 아니다. NemoClaw 와 OpenShell 의 동작 설명은 전부 NVIDIA 1차 문서를 근거로 했으며, 문서로 확인되지 않은 부분은 본문에 "추측"이라고 표시했다.
