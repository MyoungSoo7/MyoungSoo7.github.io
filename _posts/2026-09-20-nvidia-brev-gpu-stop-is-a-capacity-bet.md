---
layout: post
title: "NVIDIA Brev — GPU 를 빌린다는 것, 그리고 '정지'가 안전하지 않은 이유"
date: 2026-09-20 17:28:27 +0900
categories: [AI, Infrastructure]
tags: [NVIDIA, Brev, GPU, Nemotron, CUDA, Cloud, LLM]
---

오늘 두 편을 썼다. 하나는 [해커톤 챗봇 리포](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/), 하나는 [build.nvidia.com 과 OpenShell 이 나눠놓은 두 층](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/). 두 글 다 **남의 GPU 위에서 추론만 하는** 세계를 전제로 했다. API 키 하나 받아서 엔드포인트를 때리면 끝이고, GPU 가 몇 장인지는 알 필요도 없다.

<https://brev.nvidia.com/> 은 그 전제를 깨는 자리다. **여기서 빌리는 건 추론이 아니라 GPU 그 자체다.** 그러면 숫자가 붙기 시작한다.

## 1. Nemotron 을 "직접" 돌린다는 게 뭘 요구하나

아침 글에서 본 그 해커톤 챗봇은 `nvidia/nemotron-3-super-120b-a12b` 를 썼다. NIM 엔드포인트로 호출했으니 노트북 한 대로 충분했다. 그런데 같은 모델을 내 인스턴스에 올리려면 모델 카드에 이렇게 적혀 있다.

> Minimum GPU Requirement: **8× H100-80GB**
> — [NVIDIA-Nemotron-3-Super-120B-A12B 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard)

총 120B / 활성 12B 짜리 MoE 인데도 최소 8장이다. MoE 는 *계산량*을 줄이지 총 파라미터를 메모리에서 지워주지 않기 때문이다. 활성 12B 만 곱해지는 건 FLOPs 쪽이고, 가중치는 120B 전체가 어딘가에 올라가 있어야 한다.

Brev 문서도 같은 얘기를 훨씬 단순한 산식으로 적어둔다.

> Model size: Ensure VRAM exceeds model parameters (7B params ~ 14GB for fp16)
> — [GPU Types, NVIDIA Brev Documentation](https://docs.nvidia.com/brev/reference/gpu-types)

파라미터당 2바이트. 여기에 KV 캐시와 활성화가 더 붙는다. **"모델이 작아 보인다"와 "한 장에 올라간다"는 전혀 다른 문장이다.**

## 2. Brev 가 없애는 마찰은 정확히 무엇인가

Brev 문서는 자기 구성을 세 단어로 정리한다 — GPU Instances, Environments, Launchables.

인스턴스에 기본으로 들어가는 것들:

> NVIDIA GPU(s) with CUDA drivers / Python 3.10+ with pip / Docker and Docker Compose / JupyterLab / SSH access
> — [GPU Instances](https://docs.nvidia.com/brev/concepts/gpu-instances)

드라이버·CUDA 버전 맞추다 반나절 태워본 사람이면 이 목록의 가치를 안다. 없애주는 마찰은 **환경 구성**이지 GPU 가격이 아니다.

그 위에 Launchable 이 있다.

> Launchables bundle compute hardware, software environments, and code into one-click deployable packages. Share a link, and anyone can spin up an identical environment.
> — [Launchables](https://docs.nvidia.com/brev/concepts/launchables)

하드웨어 + 소프트웨어 + 코드를 **링크 하나**로 묶는다. 런타임 모드는 VM / 단일 컨테이너 / Docker Compose / 단일 노드 쿠버네티스(베타) 네 가지고, README 에 붙일 "Launch on Brev" 마크다운 배지도 제공한다.

### 여기서 앞 글과 만난다

Launchable 설계에서 눈에 띄는 게 **Launch parameters** 다.

> Launch parameters let a Launchable creator define values that each deployer provides when starting the Launchable. Use them for API keys, image tags, model IDs, feature flags, and other configuration that should not be fixed in the Launchable.

즉 **API 키를 공유 링크 안에 박지 말고, 배포하는 사람이 자기 값을 넣게 하라**는 구조다. 아침 글에서 지적한 그 문제 — 게이트웨이 토큰이 `config.js` 로 브라우저에 실려 나가던 것 — 의 정반대 방향이다. 공유 가능한 아티팩트를 만들 때 "설정을 값으로 굳히지 않고 파라미터로 뚫어두는" 건 Brev 만의 얘기가 아니라 일반 원칙이다.

접근 범위도 셋으로 나뉜다 — 조직 내부만 / 링크를 가진 사람 / 공개(Explore 검색에 노출). 새로 만든 Launchable 의 기본값은 **"링크를 가진 사람"** 이다. 기본이 조직 내부가 아니라는 점은 알고 쓰는 게 좋다.

## 3. 함정 — `stop` 은 일반 VM 의 `stop` 이 아니다

이 글을 쓰기로 한 진짜 이유가 이거다. EC2 든 GCE 든, 인스턴스를 멈추는 건 **안전한 동작**이다. 요금이 멎고, 디스크는 남고, 켜면 돌아온다. Brev 에서는 다르다.

> When you stop an instance, Brev releases the GPU back to the cloud provider while preserving your data. You avoid compute charges, but **your data remains bound to the original provider and region.**
>
> Restarting a stopped instance: Brev attempts to provision the same GPU type in the same provider and region. **If capacity is unavailable, the restart fails, and your data remains inaccessible.** You must wait for capacity or delete the instance (losing data).
>
> **Capacity risk:** GPU availability varies by provider and region. Popular GPU types frequently hit capacity limits. If you stop an instance and capacity becomes unavailable, you cannot access your data until capacity returns. Push important work to Git before stopping.

읽고 나면 `stop` 의 성격이 바뀐다. 이건 일시정지가 아니라 **용량에 거는 베팅**이다. GPU 를 풀에 반납하는 순간 내 자리는 사라지고, 데이터는 그 provider·region·GPU 타입 조합에 묶인 채로 남는다. 돌아오려면 **같은 조합의 빈자리가 있어야** 한다.

그리고 이 리스크는 인기 있는 타입일수록 크다. 즉 H100·H200·B200 처럼 **비싸고 아쉬운 카드일수록 정지 후 복귀가 어렵다.** 1절에서 본 "Nemotron 3 Super = 최소 8×H100" 같은 요구와 정확히 같은 지점에서 부딪힌다.

문서가 내놓는 판단표는 이렇다.

| 상황 | 권고 | 이유 |
| --- | --- | --- |
| 몇 시간 자리 비움 | Stop | 같은 용량을 되찾을 가능성이 높음 |
| 하룻밤·주말 | 주의해서 Stop | **먼저 Git 에 푸시할 것**, 용량이 바뀔 수 있음 |
| 며칠 이상 | Delete | 스토리지 비용과 용량 락인 회피 |
| GPU 타입 변경 | Delete | 정지 상태에서는 타입을 못 바꿈 |
| 최대한 유연하게 | Delete | provider·region 제약 없음 |

"주말이면 지우는 게 낫다"는 권고가 벤더 문서에 적혀 있는 건 흔치 않다. 정직한 문서다.

## 4. 같이 알아둘 것 셋

**① 살아남는 디렉터리는 하나다.** 문서의 영속성 표는 `/home/ubuntu/workspace` 만 stop 을 통과한다고 적는다. `/tmp` 는 stop 에서도 날아가고, 시스템 패키지와 Docker 이미지는 stop 은 통과하지만 delete 에서는 전부 사라진다. **delete 열은 전부 No 다.**

**② 크레딧이 떨어지면 자동으로 정리된다.**

> If your organization runs out of credits, Brev may stop stoppable running instances and **delete non-stoppable resources.** If credits are not added during the grace period, Brev may delete remaining resources. Deleted instances and their data cannot be recovered.

정지 가능한 건 정지, 정지 불가능한 건 **삭제**다. 그리고 유예 기간이 지나면 나머지도 삭제다. 크레딧 잔량은 요금 문제가 아니라 **데이터 보존 문제**다.

**③ 두 NVIDIA 1차 문서의 H100 표기가 서로 다르다.** Brev 의 GPU 카탈로그는 H100 을 `96GB HBM3` 로 적고, Nemotron 모델 카드의 최소 요구는 `8× H100-80GB` 라고 적는다. H100 은 SKU 에 따라 메모리가 다른 카드라 어느 쪽도 틀렸다고 단정할 수 없다. **추측하지 말고, 할당받은 인스턴스에서 `nvidia-smi` 로 실측하고 용량 계획을 세우는 게 맞다.** 덧붙여 그 카탈로그 페이지는 스스로 `Last updated: 2026-04-06` 을 표시한다 — 표에 없는 카드가 콘솔에 있을 수도, 반대일 수도 있다.

## 5. 그래서 언제 무엇을 쓰나

오늘 세 편에서 나온 주소들을 한 줄씩 정리하면 이렇게 된다.

| 필요한 것 | 가는 곳 | 붙는 비용 |
| --- | --- | --- |
| 추론 결과만 필요 | [build.nvidia.com](https://build.nvidia.com/) NIM 엔드포인트 | 호출 단위 (사이트는 "Free inference with leading models" 로 안내) |
| 가중치를 만지고 싶다 (파인튜닝·양자화·커스텀 서빙) | [brev.nvidia.com](https://brev.nvidia.com/) GPU 인스턴스 | **시간당, 켜져 있는 내내** |
| 남이 그대로 재현하게 하고 싶다 | Brev Launchable 링크 | 배포하는 사람이 부담 |
| 에이전트에 권한 경계를 두고 싶다 | [NemoClaw / OpenShell](https://www.nvidia.com/en-us/ai/nemoclaw/) | 별도 층 |

첫 줄과 둘째 줄의 차이가 이 글의 요점이다. 엔드포인트는 **안 부르면 아무 일도 안 일어나고**, 인스턴스는 문서가 명시한 대로 **켜져 있는 동안 시간당 과금**된다. 그래서 "일단 띄워놓고 나중에 정지하지 뭐" 라는 습관이 생기는데, 3절에서 본 대로 Brev 에서 그 정지는 공짜가 아니다. **켤 때가 아니라 끌 때 판단이 필요한 서비스다.**

## 마무리

GPU 를 빌린다는 건 계산 능력을 빌리는 일처럼 보이지만, 실제로 계약하는 건 **자리**다. 그 자리는 provider 와 region 과 카드 종류에 묶여 있고, 손을 놓는 순간 남이 앉는다.

그래서 Brev 문서에서 가장 실용적인 문장은 GPU 표도 Launchable 설명도 아니고 이 한 줄이었다.

> Push important work to Git before stopping.

---

## References

- [NVIDIA Brev 콘솔](https://brev.nvidia.com/) · [Brev — NVIDIA Developer](https://developer.nvidia.com/brev)
- [NVIDIA Brev Documentation — GPU Instances](https://docs.nvidia.com/brev/concepts/gpu-instances) — 라이프사이클, 용량 리스크, 데이터 영속성, 과금·크레딧 정책
- [NVIDIA Brev Documentation — Launchables](https://docs.nvidia.com/brev/concepts/launchables) — 런타임 모드, Launch parameters, 접근 범위
- [NVIDIA Brev Documentation — GPU Types](https://docs.nvidia.com/brev/reference/gpu-types) — GPU 카탈로그 및 VRAM 산식 (페이지 표기 `Last updated: 2026-04-06`)
- [NVIDIA-Nemotron-3-Super-120B-A12B 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard) — 최소 GPU 요구 `8× H100-80GB`
- 같은 날 앞선 글: [해커톤 에이전트 챗봇](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/) · [에이전트 정책은 어디에 두나](https://myoungsoo7.github.io/2026/09/20/where-agent-policy-belongs-nemoclaw-openshell/)
