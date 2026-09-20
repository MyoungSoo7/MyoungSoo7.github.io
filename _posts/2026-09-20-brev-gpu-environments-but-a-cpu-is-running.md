---
layout: post
title: "GPU Environments 인데 CPU 가 떠 있다 — NemoClaw 환경 한 장이 고쳐준 것들"
date: 2026-09-20 18:32:07 +0900
categories: [AI, Infrastructure]
tags: [NVIDIA, Brev, NemoClaw, GPU, Agent, Cloud]
---

오늘 세 편을 썼다. [해커톤 챗봇](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/), [build.nvidia.com 과 OpenShell 의 두 층](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/), [Brev 에서 GPU 를 빌린다는 것](https://myoungsoo7.github.io/2026/09/20/nvidia-brev-gpu-stop-is-a-capacity-bet/). 셋 다 **문서를 읽고 쓴 글**이다.

그리고 마지막 글을 올린 직후에 실제로 한 대가 떠 있는 화면을 봤다. 한 장인데, 앞 글에서 내가 쓴 것을 세 군데 고쳐야 했다.

![NVIDIA Brev 콘솔의 GPU Environments 목록 — nemoclaw 환경 한 개가 Running 상태이며 컴퓨트는 CPU 4코어·16GiB RAM·275GB·GCP us-west1·$0.25/hr, 컨테이너는 VM Mode 로 Built, 우측에 NemoClaw 버튼](/assets/images/brev/brev-nemoclaw-environment.jpg)

*인스턴스 ID 와 사용자 식별자는 가렸다. 나머지는 원본 그대로다.*

## 1. 첫 번째 교정 — "GPU Environments" 인데 CPU 가 돌고 있다

페이지 제목은 **GPU Environments** 다. 설명도 *"Provision GPU environments, monitor logs, SSH with the Brev CLI, access JupyterLab, and more!"* 라고 적혀 있다. 그런데 그 아래 **Running** 인 환경 하나는 이렇다.

| 항목 | 값 |
| --- | --- |
| 이름 | `nemoclaw-…` |
| 컴퓨트 | **CPU** · 4 CPUs · 16 GiB RAM |
| 아키텍처·디스크 | x86_64 · 275 GB |
| 클라우드·리전 | GCP · `us-west1` |
| 단가 | **$0.25/hr** |
| 컨테이너 | **VM Mode**, Built |

GPU 가 없다. 오타도 실수도 아니고, **이게 맞는 구성이다.**

아침 글에서 인용한 NVIDIA 자신의 정의를 다시 보면 이유가 바로 나온다.

> NemoClaw is the full agent deployment package—models, harness, tools, and runtime.
> — [NVIDIA NemoClaw 제품 페이지](https://www.nvidia.com/en-us/ai/nemoclaw/)

여기서 GPU 를 먹는 건 넷 중 **models** 하나뿐이다. harness·tools·runtime 은 전부 평범한 프로세스고, 모델을 [build.nvidia.com](https://build.nvidia.com/) 의 엔드포인트로 부르면 **가중치는 내 기계에 안 올라온다.** 그러면 남는 건 4 vCPU 짜리 리눅스 박스다.

직전 글에서 내가 그린 표에는 두 줄뿐이었다 — "추론 결과만 필요 → NIM 엔드포인트", "가중치를 만지고 싶다 → GPU 인스턴스". 이 화면은 그 사이에 있어야 했던 줄을 보여준다.

| 필요한 것 | 컴퓨트 | 모델은 어디서 |
| --- | --- | --- |
| 추론 결과만 | 없음 (내 노트북) | 원격 엔드포인트 |
| **에이전트 런타임을 돌린다** | **CPU 인스턴스** | **원격 엔드포인트** |
| 가중치를 만진다 (파인튜닝·양자화·자체 서빙) | GPU 인스턴스 | 로컬 |

"에이전트를 클라우드에 올린다"와 "모델을 클라우드에 올린다"는 전혀 다른 청구서다. 전자는 시간당 0.25 달러, 후자는 [8× H100-80GB](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard) 부터 시작한다.

## 2. $0.25/hr 은 "쓴 만큼"이 아니다

화면에 `● $0.25/hr` 과 `● Running` 이 나란히 붙어 있다. 생성 시각은 오후 5시 27분, 이 글을 쓰는 지금 한 시간째 켜져 있다. 25센트다. 아무것도 아니다.

그게 함정인 지점이다. 이건 **호출당이 아니라 벽시계 시간당**이다. 화면의 단가를 그대로 곱하면 이렇게 된다.

- 1시간 = $0.25
- 하루 방치 = $6
- 한 달 방치 = **$180**

에이전트를 안 부른 시간에도 똑같이 붙는다. 앞 글의 결론 — *"켤 때가 아니라 끌 때 판단이 필요한 서비스다"* — 가 이 화면에서는 소수점 둘째 자리로 보인다. 그래서 더 안 끈다.

### 다만 앞 글을 한 군데 완화해야 한다

직전 글에서 Brev 의 `stop` 을 "용량에 거는 베팅"이라고 썼다. 문서 근거는 이거였다.

> Capacity risk: GPU availability varies by provider and region. **Popular GPU types frequently hit capacity limits.**
> — [GPU Instances](https://docs.nvidia.com/brev/concepts/gpu-instances)

그런데 이 화면의 인스턴스는 **GCP us-west1 의 4 vCPU 박스**다. H100 자리를 되찾는 것과 범용 vCPU 자리를 되찾는 것은 난이도가 같지 않다. 문서가 위험의 크기를 *GPU 타입의 인기*에 걸어놨으니, **위험은 카드의 희소성에 비례한다**고 읽는 게 맞다.

즉 앞 글의 권고는 이렇게 다듬는다 — `stop` 이 위험한 건 Brev 라서가 아니라 **내가 쥔 카드가 귀할수록**이다. B200·H200·H100 이면 주말엔 지우고 Git 에 밀어두는 게 맞고, CPU 환경이면 그 정도 긴장은 과하다. (그래도 데이터가 provider·region 에 묶이는 성질 자체는 같다.)

## 3. VM Mode — 문서에 표가 있다

컨테이너 칸의 `VM Mode` 는 임의 표기가 아니라 Brev 의 배포 모드 이름이다.

| Mode | Environment | Preinstalled Software |
| --- | --- | --- |
| VM Mode | Full Ubuntu VM | Python 3.10+, CUDA, Docker, NVIDIA Container Toolkit |
| Container Mode | Single Docker container | Depends on your base image. |
| Compose Mode | Multi-container Docker Compose | Depends on service images. |

— [Environments, NVIDIA Brev Documentation](https://docs.nvidia.com/brev/concepts/environments)

VM Mode 를 고르면 전체 우분투 VM 을 받고, 문서 기준 CUDA 툴킷과 NVIDIA Container Toolkit 까지 얹혀 나온다. **GPU 가 없는 인스턴스에서도 그게 그대로 깔리는지는 이 화면만으로는 알 수 없다** — 확인하려면 들어가서 `nvidia-smi` 와 `nvcc --version` 을 쳐보는 수밖에 없고, 나는 안 해봤다. 문서가 말하는 건 모드의 이미지 구성이지 이 인스턴스의 상태가 아니다.

그리고 작업 디렉터리 규칙은 앞 글에서 강조한 그대로다.

> Your default working directory is `/home/ubuntu/workspace`. This is where you should store all your work, as it persists across instance stops.

## 4. 두 번째 교정 — 내가 모르던 탭이 하나 있다

화면 상단에 탭이 둘이다. `Environments` 옆에 **`Registered compute` (NEW)**, 우측 상단에 **Register Compute** 버튼. 앞 글을 쓸 때 나는 이 기능을 못 봤고, 그래서 Brev 를 "GPU 를 빌리는 곳"으로만 썼다. **반대 방향이 있다.**

문서에서는 이름이 이미 바뀌어 있었다. **Brev Connect** 다.

> Brev Connect lets you bring hardware you own into NVIDIA Brev. Connect any Linux machine — DGX Spark, DGX Station, or any other node — to get SSH access, team sharing, and port forwarding through the Brev platform.
>
> This is designed for hardware you own and manage — **Brev handles connectivity and access control, not the machine's lifecycle.**
> — [Brev Connect](https://docs.nvidia.com/brev/concepts/brev-connect)

개명이 아직 진행 중이라 흔적이 남아 있다 — 개념 문서는 `/concepts/brev-connect` 로 옮겨갔는데 가이드 경로는 여전히 `/guides/registered-compute/…` 이고, 콘솔 탭 라벨은 옛 이름 그대로다. 참고로 검색엔진이 들고 있는 옛 주소 `/concepts/registered-compute` 는 지금 **404** 다. 인용하기 전에 한 번 눌러봐야 하는 이유가 이거다.

### 이 표가 앞 글의 절반을 지운다

문서가 둘을 직접 비교해놨다.

| Feature | Brev Connect | Cloud GPU Instances |
| --- | --- | --- |
| SSH access | Yes | Yes |
| Team sharing | Yes | Yes |
| Port forwarding | Yes | Yes |
| Hardware auto-detection | Yes | N/A (predefined) |
| **Launchables** | **No** | Yes |
| **Managed environments** | **No** | Yes |
| **Start/stop/delete lifecycle** | **No** | Yes |
| **Billing** | **No compute charges** | Per-hour billing |

아래 네 줄이 오늘 쓴 앞 글 전체와 맞물린다.

- `Start/stop/delete lifecycle: No` — **`stop` 함정이 아예 성립하지 않는다.** 반납할 자리가 없으니 용량에 걸 베팅도 없다.
- `Billing: No compute charges` — 2절의 시간당 시계가 멎는다. 전기값은 내가 내지만 그건 Brev 청구서가 아니다.
- `Launchables: No` / `Managed environments: No` — 그런데 이 둘은 **앞 글에서 내가 칭찬했던 바로 그것들**이다. 링크 하나로 동일 환경을 복제하는 것, 드라이버·CUDA 가 맞춰진 채로 나오는 것.

거래가 대칭이다. **시간당 요금과 용량 리스크를 버리는 대신, 재현 가능한 환경과 원클릭 공유를 버린다.** 그러니 선택 기준은 "며칠 쓸 것인가"가 아니라 **"이 환경을 남이 그대로 복제해야 하는가"** 쪽이다.

### 여기서 오늘 아침 글과 다시 만난다

등록은 CLI 한 줄인데, 그 한 줄이 하는 일이 셋이다.

> 1. **Installs NetBird** — A mesh VPN agent that provides secure connectivity between your machine and Brev users
> 2. **Profiles hardware** — Auto-detects GPUs (via NVML), CPU, RAM, storage, OS, and interconnects like NVLink and PCIe
> 3. **Registers with Brev** — Makes the machine visible in your Brev organization

1번은 그냥 지나칠 문장이 아니다. **메시 VPN 에이전트(NetBird)를 `https://pkgs.netbird.io/install.sh` 로 받아 systemd 서비스로 설치한다.** 문서도 숨기지 않는다 — *"Requires `sudo` access. Linux only."* 그리고 SSH 를 여는 단계가 하나 더 있다.

> **brev enable-ssh** — Enable SSH on a registered machine by **installing the Brev certificate authority** for a Linux user and opening the SSH port.
> — [Brev Connect Commands](https://docs.nvidia.com/brev/cli/brev-connect)

**내 기계의 SSH 신뢰에 벤더 CA 가 들어간다.** 아침 글에서 OpenShell 이 통제한다고 열거한 축이 넷이었다 — **파일·네트워크·자격증명·툴.** 그 글에서는 *에이전트*를 그 네 축으로 가뒀다. `brev register` + `brev enable-ssh` 는 같은 축을 **반대 방향**으로 쓴다. 이번엔 내 기계의 **네트워크**(메시 VPN)와 **자격증명**(CA + 조직원에게 발급되는 SSH 접근)을 플랫폼 쪽으로 여는 것이다.

이게 위험하다는 얘기가 아니다. NVIDIA 가 파는 관리형 접근 계층이고, 문서가 설치물·설치 경로(`/etc/brev/device_registration.json`)·제거 절차(`brev deregister` 가 서버 등록 해제·SSH 엔트리 제거·NetBird 제거·등록 파일 삭제 넷을 다 한다)까지 적어뒀다. 되돌릴 수 있게 만든 건 좋은 설계다. 요점은 **결정의 성격이 다르다**는 것이다. 클라우드 인스턴스를 빌리는 건 *돈* 결정이고, 내 노드를 등록하는 건 *경계* 결정이다. 집에 굴리는 리눅스 노드에 걸어볼 생각이 있었는데(`any Linux node` 라니까), 그건 요금표 보는 마음가짐으로 누를 버튼이 아니라는 걸 이 문단 쓰면서 알았다.

## 5. 작은 것 하나 — `(Shared)`

인스턴스 메타 줄 끝에 `(Shared)` 가 붙어 있고, 목록 위에는 `Mine` / `Team` 토글이 있다. 앞 글에서 Launchable 의 기본 공개 범위가 "링크를 가진 사람"이라고 적었는데, 환경 쪽에도 같은 축이 있다는 뜻이다. 혼자 쓰는 계정이면 `(Shared)` 가 붙어 있을 이유가 없으니, **한 번은 눌러서 확인할 값**이다.

## 덤 — 이 글의 인용은 이렇게 검증했다

Brev 문서는 **아무 페이지 URL 뒤에 `.md` 를 붙이면 렌더 전 마크다운 원문**이 나온다. 전체 색인은 `https://docs.nvidia.com/brev/llms.txt` 에 있고, 문서 상단이 안내하는 대로 MCP 엔드포인트(`/brev/_mcp/server`)도 열려 있다.

오늘 낮에 DLI 코스 페이지가 자바스크립트로만 그려져서 본문 확인이 안 됐던 일이 있었는데([그 글](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/)에서 해당 수치를 통째로 뺐다), 이런 함정을 피하는 데는 `.md` 쪽이 훨씬 낫다. 이 글의 인용문은 전부 `.md` 원문에서 가져왔고, 본문에 건 링크는 렌더 페이지 기준으로 따로 200 을 확인했다.

## 마무리

문서만 읽고 쓴 글 세 편이 화면 한 장에 세 군데 수정을 받았다.

- "GPU Environments" 에 떠 있던 건 **CPU** 였다 → 에이전트 런타임과 모델 호스팅은 다른 청구서다.
- `stop` 의 위험은 Brev 의 성질이 아니라 **카드의 희소성**에 비례한다.
- Brev 에는 **반대 방향**(Brev Connect)이 있었다 → 시간당 요금과 `stop` 함정이 사라지는 대신, Launchable 과 관리형 환경을 잃고 `sudo` 로 메시 VPN 과 벤더 CA 를 들인다.

교훈은 진부하지만 매번 맞다. **한 대 띄워보기 전에는 표가 한 줄씩 비어 있다.**

---

## References

- [NVIDIA Brev 콘솔](https://brev.nvidia.com/) — 본문 스크린샷 출처 (2026-09-20 확인, 식별자 마스킹)
- [NVIDIA Brev Documentation — Environments](https://docs.nvidia.com/brev/concepts/environments) — 배포 모드별 사전 설치 소프트웨어, `/home/ubuntu/workspace` 영속성
- [NVIDIA Brev Documentation — GPU Instances](https://docs.nvidia.com/brev/concepts/gpu-instances) — 용량 리스크, stop/delete 판단
- [NVIDIA Brev Documentation — Brev Connect](https://docs.nvidia.com/brev/concepts/brev-connect) — 비교표, NetBird 설치, 하드웨어 프로파일링, `/etc/brev/device_registration.json`
- [NVIDIA Brev Documentation — Brev Connect Commands](https://docs.nvidia.com/brev/cli/brev-connect) · [Managing Brev Connect](https://docs.nvidia.com/brev/guides/registered-compute/managing-brev-connect) — `brev register` / `enable-ssh` / `grant-ssh` / `deregister`
- [NVIDIA NemoClaw 제품 페이지](https://www.nvidia.com/en-us/ai/nemoclaw/) — NemoClaw 구성 정의 (models, harness, tools, runtime)
- [NVIDIA-Nemotron-3-Super-120B-A12B 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard) — 최소 GPU 요구
- 오늘 앞선 글: [해커톤 에이전트 챗봇](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/) · [에이전트 정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/) · [GPU 를 빌린다는 것](https://myoungsoo7.github.io/2026/09/20/nvidia-brev-gpu-stop-is-a-capacity-bet/)
