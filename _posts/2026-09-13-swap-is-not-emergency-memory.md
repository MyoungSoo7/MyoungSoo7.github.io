---
layout: post
title: "스왑은 비상 메모리가 아니다 — 서버는 왜 스왑을 끄고, 리눅스는 왜 스왑을 옹호하는가"
date: 2026-09-13 03:23:53 +0900
categories: [infra, linux]
tags: [linux, swap, memory, kubernetes, k3s, oom, swappiness]
---

새벽에 홈랩 K3s 노드를 점검하다가 익숙한 장면을 만났다. RAM 30GiB 중 21GiB 사용, 스왑 0B. Elasticsearch JVM 두 개와 Logstash, Prometheus가 메모리의 절반을 먹고 있는 노드다. "스왑이 없네, 위험한 거 아닌가?"라는 질문이 자연스럽게 나오지만, 답은 생각보다 재미있다. **이 상태는 쿠버네티스 세계의 표준이면서, 동시에 리눅스 메모리 관리 관점에서는 오랜 논쟁거리다.** 이 글은 그 양쪽 논리를 1차 출처 기준으로 정리한다.

## 오해부터 걷어내기: 스왑은 "느린 추가 RAM"이 아니다

스왑에 대한 가장 흔한 이해는 "메모리가 모자랄 때 쓰는 비상용 디스크 메모리"다. 커널 cgroup v2 개발에 참여해 온 Chris Down은 널리 인용되는 글 [In defence of swap: common misconceptions](https://chrisdown.name/2018/01/02/in-defence-of-swap.html)(2018)에서 이 통념을 정면으로 반박한다. 요지는 이렇다.

- 스왑의 본질은 비상 메모리가 아니라 **메모리 회수(reclamation)를 공평하고 효율적으로 만드는 장치**다. 오히려 스왑을 "비상 메모리"로 쓰는 것이 해롭다.
- 리눅스의 메모리 페이지는 크게 두 종류다. 디스크에 원본이 있는 **파일 페이지**(실행 파일, 페이지 캐시)와, `malloc` 등으로 할당돼 디스크에 원본이 없는 **익명 페이지**(힙, 스택). 파일 페이지는 버려도 나중에 디스크에서 다시 읽으면 되지만, 익명 페이지는 스왑이 없으면 **회수할 방법 자체가 없다** — 아무리 오래 안 쓴 페이지라도 RAM에 못 박힌다.
- 그래서 스왑을 꺼도 메모리 압박 상황의 디스크 I/O 폭주는 사라지지 않는다. **익명 페이지 대신 파일 페이지를 쥐어짜는 쪽으로 옮겨갈 뿐이고**, 회수 후보 풀이 좁아진 만큼 오히려 더 비효율적일 수 있다.

`vm.swappiness`의 실제 의미도 여기서 나온다. [커널 문서](https://docs.kernel.org/admin-guide/sysctl/vm.html)가 정의하는 이 값은 "스왑을 얼마나 적극적으로 쓸지"라는 막연한 게이지가 아니라, **익명 페이지 회수와 파일 페이지 회수의 상대 비용 비율**이다. Chris Down의 설명대로 SSD에서는 둘의 비용이 비슷해 높은 값이 자연스럽고, 회전 디스크에서는 스왑 읽기가 랜덤 I/O라 낮은 값이 맞다. 기본값 60은 그 사이의 절충이다.

## 그런데 쿠버네티스는 왜 스왑을 껐나

리눅스 진영이 "스왑은 유익하다"고 말하는 동안, 쿠버네티스는 정반대의 선택을 했다. kubelet은 **리눅스 노드에 스왑이 켜져 있으면 아예 기동을 거부하는 것이 기본 동작**이다([공식 문서](https://kubernetes.io/docs/concepts/cluster-administration/swap-memory-management/)). 이유는 철학이 아니라 회계다. [KEP-2400](https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/2400-node-swap)의 서두가 명시하듯, 스왑이 끼는 순간 **파드의 메모리 사용량을 보장하고 계량하기 어려워지기 때문에** 초기 설계에서 스왑 지원을 범위 밖으로 밀어둔 것이다.

쿠버네티스의 자원 모델은 "파드가 memory request/limit을 선언하면 스케줄러와 kubelet이 그 약속 위에서 배치·격리·축출을 결정한다"는 전제 위에 서 있다. 스왑이 있으면 실제 워킹셋이 RAM에 있는지 디스크에 있는지에 따라 같은 "사용량"의 의미가 달라지고, QoS 보장과 eviction 판단이 흐려진다. 예측 가능성을 위해 커널의 유연성을 포기한 트레이드오프다.

다만 이 이야기에는 후속편이 있다. 쿠버네티스는 스왑 지원을 다시 들여오는 작업을 수년에 걸쳐 진행했다:

- **v1.22** (2021): `NodeSwap` 피처 게이트 알파 도입 ([공식 블로그](https://kubernetes.io/blog/2021/08/09/run-nodes-with-swap-alpha/))
- **v1.28** (2023): 베타 승격, cgroup v2 기반 재정비 ([공식 블로그](https://kubernetes.io/blog/2023/08/24/swap-linux-beta/))
- **v1.32** (2025): 안정화 개선 — 고우선순위 파드 스왑 금지, `UnlimitedSwap` 제거 등 ([공식 블로그](https://kubernetes.io/blog/2025/03/25/swap-linux-improvements/))
- **v1.34**: `NodeSwap` GA ([kubernetes/kubernetes#132651](https://github.com/kubernetes/kubernetes/pull/132651))

GA가 됐어도 기본값은 여전히 `NoSwap`(워크로드 스왑 금지)이고, `LimitedSwap`을 켜더라도 스왑을 쓸 수 있는 건 **Burstable QoS의 비(非)고우선순위 파드뿐**이다. 허용량도 관리자가 정하는 게 아니라 `(컨테이너 memory request ÷ 노드 총 메모리) × 노드 스왑 총량`으로 자동 계산된다. 스왑을 "다시 허용"하되, 회계 가능성이 깨지지 않는 좁은 통로로만 열어준 셈이다. 공식 문서는 스케줄러가 아직 스왑을 배치 판단에 반영하지 않는다는 한계도 명시하고 있다.

## 스왑 없는 노드에서 실제로 일어나는 일

그럼 내 노드처럼 스왑 0B로 운영하면 무엇을 감수하는 건가. Chris Down의 글과 커널 문서를 종합하면 두 가지다.

**첫째, 완충지대가 없다.** 메모리가 부족해지면 시스템이 서서히 느려지는 대신, 파일 캐시를 쥐어짜다가 한계에 도달하는 순간 커널 OOM killer가 개입해 프로세스를 즉시 죽인다. 우아한 퇴장이 아니라 급사다. 흥미롭게도 Chris Down은 이것을 단점으로만 보지 않는다 — 스왑이 있으면 OOM 도달이 *느려질 뿐* 결과는 같으므로, 어차피 죽을 상황이면 빨리 죽고 빨리 복구되는 쪽이 나을 수 있다. 쿠버네티스가 정확히 이 철학이다: 파드는 죽고, 재스케줄되고, 시스템은 예측 가능하게 유지된다.

**둘째, 오래 안 쓰는 익명 페이지가 RAM을 영구 점유한다.** JVM처럼 시작 시 크게 할당하고 일부만 뜨겁게 쓰는 워크로드에서는, 차가운 익명 페이지를 내보낼 수단이 없으니 그만큼 파일 캐시가 좁아진다. Elasticsearch처럼 페이지 캐시 의존이 큰 애플리케이션에는 이중으로 아픈 지점이다.

내 결론은 "그래도 스왑 없이 간다"였다. K3s 노드에 스왑을 넣으려면 kubelet의 `failSwapOn`을 끄고 swapBehavior를 관리해야 하는데, 가용 메모리가 아직 9GiB 남은 노드에서 그 복잡도를 지불할 이유가 없다. 대신 감시 지표를 바꿨다. 스왑이 없는 노드에서 볼 것은 "메모리 사용률"이 아니라 **available 메모리의 추세**다. 상시 3~4GiB 밑으로 내려오기 시작하면 그때 JVM 힙 축소나 파드 재배치로 대응하면 된다.

## 정리

- 스왑은 비상 메모리가 아니라 익명 페이지를 회수 가능하게 만드는 장치다. 일반 리눅스 서버·데스크톱이라면 적당한 스왑이 있는 쪽이 메모리 관리에 유리하다는 것이 커널 쪽의 오랜 논지다.
- 쿠버네티스가 스왑을 끄는 것은 성능 미신이 아니라 자원 회계 때문이다. 그리고 그 제약은 v1.22→v1.34에 걸쳐 `NoSwap`/`LimitedSwap`이라는 통제된 형태로 완화됐다.
- 스왑 없는 노드의 비용은 "급사형 OOM"과 "차가운 익명 페이지의 RAM 점유"다. 이를 알고 감수하는 것과 모르고 운영하는 것은 다르다.

같은 "스왑 0B"라도 그 뒤에 있는 판단을 알고 있느냐가 운영의 차이를 만든다.

## References

- Chris Down, [In defence of swap: common misconceptions](https://chrisdown.name/2018/01/02/in-defence-of-swap.html) (2018)
- Linux kernel documentation, [Documentation for /proc/sys/vm/ — swappiness](https://docs.kernel.org/admin-guide/sysctl/vm.html)
- Kubernetes documentation, [Swap memory management](https://kubernetes.io/docs/concepts/cluster-administration/swap-memory-management/)
- Kubernetes documentation, [Linux Node Swap Behaviors](https://kubernetes.io/docs/reference/node/swap-behavior/)
- Kubernetes Enhancement Proposal, [KEP-2400: Node memory swap support](https://github.com/kubernetes/enhancements/tree/master/keps/sig-node/2400-node-swap)
- Kubernetes blog, [New in Kubernetes v1.22: alpha support for using swap memory](https://kubernetes.io/blog/2021/08/09/run-nodes-with-swap-alpha/) (2021)
- Kubernetes blog, [Kubernetes 1.28: Beta support for using swap on Linux](https://kubernetes.io/blog/2023/08/24/swap-linux-beta/) (2023)
- Kubernetes blog, [Fresh Swap Features for Linux Users in Kubernetes 1.32](https://kubernetes.io/blog/2025/03/25/swap-linux-improvements/) (2025)
- kubernetes/kubernetes, [PR #132651: GA the NodeSwap feature gate](https://github.com/kubernetes/kubernetes/pull/132651) (merged 2025-07, milestone v1.34)
