---
layout: post
title: "GPU 0장짜리 홈 클러스터를 쿠버네티스 AI 컨포먼스로 채점했다 — 9개 MUST 중 절반은 GPU와 무관하게 떨어진다"
date: 2026-08-13 16:00:00 +0900
categories: [kubernetes, AI]
tags: [kubernetes, ai-conformance, dra, gateway-api, gang-scheduling, k3s, cncf]
---

"쿠버네티스와 AI"를 검색하면 대부분 GPU 이야기가 나온다. GPU 노드풀, MIG 파티셔닝, 타임슬라이싱. 그래서 GPU가 한 장도 없는 내 홈 클러스터는 이 주제와 무관하다고 생각했다.

그런데 CNCF가 2025년 11월에 만든 **Certified Kubernetes AI Conformance** 체크리스트를 열어보니 생각이 바뀌었다. 필수 요구사항(MUST) 9개 중 GPU가 있어야만 판정 가능한 건 4개였다. 나머지 5개는 GPU가 0장이어도 통과하거나 떨어질 수 있는 항목이었고, 내 클러스터는 **그중 3개에서 명백히 떨어졌다.**

이 글은 그 채점 과정이다. 채점표는 CNCF 공식 저장소의 YAML을 그대로 썼고, 점수는 전부 실제 클러스터에 `kubectl` 을 쳐서 매겼다.

---

## 0. 먼저 사실관계 하나 — DRA는 언제 GA가 됐나

본론에 들어가기 전에, 이 글을 쓰면서 만난 출처 충돌부터 정리하고 간다. 이게 글 전체의 태도이기도 하다.

Dynamic Resource Allocation(DRA)은 GPU·FPGA·NIC 같은 특수 장치를 쿠버네티스에서 다루는 새 API다. 그런데 GA 시점이 자료마다 다르게 적혀 있었다.

- CNCF 블로그(2026-07-01)에는 "DRA recently reached GA in Kubernetes **v1.35**"라고 적혀 있다.[^cncf-dra]
- 쿠버네티스 **공식 릴리스 블로그**(2025-09-01)의 제목은 "Kubernetes **v1.34**: DRA has graduated to GA"다.[^k8s-dra-ga]

둘 중 하나는 틀렸고, 판단 기준은 간단하다. **프로젝트가 자기 릴리스에 대해 쓴 글이 1차 출처다.** CNCF 블로그는 커뮤니티 기고 채널이고, 릴리스 블로그는 릴리스 팀이 쓴다. 그래서 이 글은 **DRA GA = v1.34** 로 쓴다. Google Cloud 블로그도 "DRA reached 'stable' status in Kubernetes OSS 1.34"로 같은 값을 적고 있다.[^gcp-dra]

사소해 보이지만, 이런 한 칸 차이가 "우리 클러스터는 1.34니까 DRA를 쓸 수 있다/없다"는 정반대 결론을 만든다. 버전 숫자는 항상 릴리스 블로그나 CHANGELOG에서 확인하는 게 맞다.

---

## 1. 채점표의 정체

CNCF는 2025년 11월 11일 KubeCon NA(애틀랜타)에서 **Certified Kubernetes AI Conformance Program** 을 발표했다.[^cncf-launch] 목적은 한 줄로 요약된다 — _"AI 애플리케이션이 어느 컨포먼트 플랫폼에서 돌면 다른 데서도 돌아야 한다."_[^repo]

구조는 기존 쿠버네티스 컨포먼스와 같다. 다만 두 가지는 알고 시작해야 한다.

1. **베이스 조건이 있다.** AI 컨포먼스는 기존 Kubernetes Conformance 위에 얹힌다. 쿠버네티스 컨포먼트가 아니면 시작도 못 한다.[^repo]
2. **아직 자기평가(self-assessment)다.** 저장소가 명시한다 — _"Today, certification is based on self-assessment. Automated conformance tests are planned for 2026."_[^repo] 즉 현재의 "인증"은 벤더가 체크리스트 YAML에 증거 URL을 채워 PR을 올리고 CNCF가 리뷰하는 방식이다. 자동 테스트 스위트가 채점하는 게 아니다.

체크리스트는 쿠버네티스 마이너 버전별로 따로 있다. 내 클러스터 서버 버전이 v1.35이므로 `AIConformance-1.35.yaml` 을 그대로 받아 썼다.

```bash
$ curl -sL -o aiconf-1.35.yaml \
    https://raw.githubusercontent.com/cncf/k8s-ai-conformance/main/docs/AIConformance-1.35.yaml
$ grep -c "level: MUST" aiconf-1.35.yaml
9
$ grep -c "level: SHOULD" aiconf-1.35.yaml
3
```

**MUST 9개, SHOULD 3개.** 이 9개가 오늘의 시험 범위다. 항목은 가속기(accelerators)·네트워킹·스케줄링·관측·보안·오퍼레이터 6개 영역에 걸쳐 있다.[^yaml135]

---

## 2. 피시험체 — 6노드, 74 vCPU, GPU 0장

집에 있는 K3s 클러스터다. 노트북 두 대, 데스크탑 한 대, 2014년형 맥 미니 한 대가 섞여 있다.

```bash
$ kubectl version -o json | jq -r '.serverVersion.gitVersion'
v1.35.4+k3s1

$ kubectl get nodes -o custom-columns=\
N:.metadata.name,CPU:.status.capacity.cpu,MEM:.status.capacity.memory,GPU:'.status.capacity.nvidia\.com/gpu' --no-headers
david     6     15786532Ki   <none>
ilwon     12    32170568Ki   <none>
isagal    40    15761320Ki   <none>
lemuel    4     32759988Ki   <none>
louise    8     16229284Ki   <none>
solomon   4     15758208Ki   <none>
```

합계 74 vCPU, 약 120GiB RAM, **GPU 0장.** 서버 버전이 체크리스트 버전(v1.35)과 정확히 일치하니 채점 조건은 깔끔하다.

이 클러스터에도 AI 서비스가 돌고 있다. 정산 시스템에 붙인 RAG 챗봇(`settlement-ai`)과 그 벡터 저장소(`ai-postgres`, pgvector)다. 추론은 클러스터가 하지 않는다. 외부 LLM API에 위임하고, 클러스터는 **상태·검색·오케스트레이션**만 맡는다. 이 구조가 채점에서 어떻게 나오는지가 이 글의 후반부다.

---

## 3. 채점 결과

| #   | 요구사항 (MUST)             | 영역       | 판정            | 근거                                            |
| --- | --------------------------- | ---------- | --------------- | ----------------------------------------------- |
| 1   | `dra_support`               | 가속기     | **△ 형식 통과** | `resource.k8s.io/v1` 존재. 단 ResourceSlice 0개 |
| 2   | `ai_inference`              | 네트워킹   | **✗ 실패**      | Gateway API CRD는 있으나 GatewayClass 0개       |
| 3   | `gang_scheduling`           | 스케줄링   | **✗ 실패**      | Kueue·Volcano 등 미설치                         |
| 4   | `cluster_autoscaling`       | 스케줄링   | **N/A**         | 오토스케일러 미제공(조건부 MUST)                |
| 5   | `pod_autoscaling`           | 스케줄링   | **미검증**      | HPA 오브젝트 0개, 가속기 없음                   |
| 6   | `accelerator_metrics`       | 관측       | **N/A**         | 가속기 부재                                     |
| 7   | `ai_service_metrics`        | 관측       | **✓ 통과**      | Prometheus Operator + ServiceMonitor 27개       |
| 8   | `secure_accelerator_access` | 보안       | **N/A**         | 가속기 부재                                     |
| 9   | `robust_controller`         | 오퍼레이터 | **✗ 실패**      | AI 오퍼레이터(Ray·Kubeflow 등) 없음             |

**실질 통과 1개, 형식 통과 1개, 명백한 실패 3개, 판정 불가 4개.**

주목할 지점은 실패한 3개다. `ai_inference`·`gang_scheduling`·`robust_controller` — **셋 다 GPU와 무관하다.** GPU를 한 장 사서 꽂아도 이 세 개는 그대로 떨어진다. "AI 컨포먼스 = GPU 체크리스트"라는 통념이 여기서 깨진다.

---

## 4. 실패 해부 ① — API는 GA인데 장치는 0개

가장 먼저 확인한 건 DRA다.

```bash
$ kubectl api-resources --api-group=resource.k8s.io
NAME                     APIVERSION           NAMESPACED   KIND
deviceclasses            resource.k8s.io/v1   false        DeviceClass
resourceclaims           resource.k8s.io/v1   true         ResourceClaim
resourceclaimtemplates   resource.k8s.io/v1   true         ResourceClaimTemplate
resourceslices           resource.k8s.io/v1   false        ResourceSlice
```

`v1` 이다. beta가 아니라 GA. v1.34에서 GA가 된 이후 기본 활성이므로 K3s v1.35에도 그대로 들어와 있다.[^k8s-dra-ga] 체크리스트의 요구사항 문구는 _"Support Dynamic Resource Allocation (DRA) APIs to enable more flexible and fine-grained resource requests beyond simple counts"_ 이고, API는 확실히 있다.

그런데 다음 줄에서 실체가 드러난다.

```bash
$ kubectl get resourceslices
No resources found
```

**ResourceSlice가 0개다.** DRA의 동작 모델은 4단계로 정리돼 있다 — 벤더가 `ResourceSlice` 로 장치 능력을 광고(modeling)하고, 사용자가 `ResourceClaim` 으로 요구(requesting)하고, 스케줄러가 매칭(scheduling)하고, 드라이버가 장치를 준비(actuation)한다.[^wg-device] 이 중 1단계를 수행하는 주체가 **DRA 드라이버**인데, 내 클러스터엔 광고할 장치도 드라이버도 없다.

즉 이 상태는 이렇게 읽어야 정확하다.

> API 표면은 100% 존재한다. 그 API가 가리킬 수 있는 하드웨어는 0개다.

이건 운영에서 반복적으로 사람을 속이는 패턴이다. `kubectl api-resources` 로 확인하면 "지원함"이라는 답이 나오고, 그 답만 보고 넘어가면 실제로는 아무것도 할 수 없는 상태를 통과 처리하게 된다. 자기평가 기반 컨포먼스에서 이 항목이 특히 위험한 이유이기도 하다. **증거로 제출해야 하는 건 API 목록이 아니라 ResourceSlice와 실제로 스케줄된 Pod다.**

---

## 5. 실패 해부 ② — CRD는 v1.4.0인데 구현체가 없다

두 번째 실패는 더 노골적이다. 네트워킹 MUST(`ai_inference`)는 Gateway API 기반의 추론 트래픽 관리를 요구한다. 가중치 분배, OpenAI 프로토콜 헤더 기반 라우팅 같은 것들이다.[^yaml135]

```bash
$ kubectl api-resources | grep gateway.networking
gatewayclasses    gc    gateway.networking.k8s.io/v1   false   GatewayClass
gateways          gtw   gateway.networking.k8s.io/v1   true    Gateway
httproutes              gateway.networking.k8s.io/v1   true    HTTPRoute
grpcroutes              gateway.networking.k8s.io/v1   true    GRPCRoute
```

있다. 그것도 표준 채널 v1.4.0이다.

```bash
$ kubectl get crd gateways.gateway.networking.k8s.io -o jsonpath='{.metadata.annotations}'
{"gateway.networking.k8s.io/bundle-version":"v1.4.0",
 "gateway.networking.k8s.io/channel":"standard",
 "meta.helm.sh/release-name":"traefik-crd", ...}
```

그런데 실제로 무엇이 돌고 있는지 물으면 답이 이렇다.

```bash
$ kubectl get gatewayclass
No resources found
$ kubectl get gateway -A
No resources found
$ kubectl get httproute -A
No resources found
```

**전부 0개.** 이 CRD들은 내가 설치한 게 아니라 K3s 번들 Traefik 차트(`traefik-crd`)가 딸려 들여온 것이다. 컨트롤러가 GatewayClass를 하나도 등록하지 않았으니, API는 있는데 **그 API를 처리할 주체가 없다.** `kubectl apply` 로 Gateway를 만들어봐야 영원히 `PROGRAMMED=False` 로 남는다.

여기에 추론 특화 계층이 하나 더 있다. **Gateway API Inference Extension** 은 SIG-Network 산하 WG-Serving이 주도하는 공식 프로젝트로, `InferencePool` 이라는 별도 리소스와 Endpoint Picker(EPP)를 통해 모델 서버 파드 사이의 부하분산을 최적화한다. `InferencePool` 은 `inference.networking.k8s.io/v1` 로 GA(v1.0.0)에 도달했다.[^gie-pool][^gie-intro]

```bash
$ kubectl api-resources | grep -i inferencepool
(출력 없음)
```

정리하면 이 항목의 실패는 3층 구조다. **CRD 있음 → 구현체 없음 → 추론 확장은 설치조차 안 됨.** 그리고 이 세 층은 `kubectl get crd` 한 줄로는 절대 구분되지 않는다.

> 나는 이전에 ServiceMonitor 때문에 같은 방식으로 75일을 날린 적이 있다. 오브젝트는 존재했고, Prometheus는 살아 있었고, 수집만 되지 않았다. 존재 확인과 동작 확인은 다른 명령이다.

---

## 6. 실패 해부 ③ — 갱 스케줄링, 그리고 왜 이게 MUST인가

세 번째 실패는 갱 스케줄링이다. 요구사항은 _"at least one gang scheduling solution that ensures all-or-nothing scheduling for distributed AI workloads (e.g. Kueue, Volcano, etc.)"_ 이다.[^yaml135]

```bash
$ kubectl get crd | grep -iE "kueue|volcano|podgroup"
(출력 없음)
```

없다. 그런데 왜 이게 **MUST** 일까. 분산 학습 잡의 특성 때문이다.

워커 파드 $n$ 개가 서로를 기다려야 한 스텝이 진행되는 잡을 생각하자. 각 파드가 독립적으로 스케줄될 확률을 $p$ 라 하면, 갱 스케줄링 없이 전부 자리를 잡을 확률은 대략 이렇다.

$$P_{\text{all}} = p^{\,n}$$

$p = 0.9$ 로 꽤 여유 있는 클러스터라도 $n = 8$ 이면 $P_{\text{all}} \approx 0.43$ 이다. 절반 이상의 시도에서 **일부만 뜬 채 나머지를 기다리며 GPU를 점유**하게 된다. 그리고 그 점유가 다른 잡의 $p$ 를 떨어뜨려 서로를 굶기는 교착으로 간다. (물론 실제 스케줄링은 파드 간 독립이 아니므로 이 식은 직관용 모형이지, 예측용 공식이 아니다.)

그래서 all-or-nothing이 필요하고, 지금까지는 Kueue·Volcano 같은 외부 스케줄러가 그 역할을 해왔다. 흥미로운 건 이게 **인트리로 들어오고 있다**는 점이다. 쿠버네티스 v1.36은 정적 템플릿인 `Workload` API와 런타임 상태를 다루는 `PodGroup` API를 분리해 도입했고, `kube-scheduler` 에 PodGroup 스케줄링 사이클을 추가했다. 갱 스케줄링은 `GangScheduling` 피처 게이트로, 토폴로지 인식 스케줄링은 `TopologyAwareWorkloadScheduling` 으로 켠다(둘 다 알파).[^k8s-136-sched]

내 서버는 v1.35라 이 기능들이 아예 없다. 즉 이 항목은 "설치를 안 했다"가 아니라 **"이 버전에선 외부 솔루션 말고 선택지가 없다"** 가 정확한 진단이다.

---

## 7. 유일하게 진짜로 통과한 항목

9개 중 실체까지 통과한 건 `ai_service_metrics` 하나다. 요구사항은 _"Prometheus exposition format 같은 표준 포맷으로 노출하는 워크로드의 메트릭을 발견·수집할 수 있는 모니터링 시스템"_ 이다.[^yaml135]

```bash
$ kubectl get servicemonitor -A --no-headers | wc -l
27
```

kube-prometheus-stack이 돌고 있고 ServiceMonitor가 27개다. 다만 이 통과에도 각주를 달아야 한다. **ServiceMonitor의 존재는 수집의 증거가 아니다.** 셀렉터는 Service의 `metadata.labels` 를 봐야 하고, 엔드포인트 인증도 통과해야 한다. 둘 중 하나가 조용히 어긋나면 오브젝트는 그대로 있고 시계열만 비어간다. 자기평가 체크리스트에 증거로 올려야 하는 건 ServiceMonitor 목록이 아니라 **`/api/v1/targets` 의 up=1** 이다.

`accelerator_metrics`(MUST)는 가속기가 없으니 N/A다. 그런데 N/A는 능력의 증명이 아니라 **부재의 기록**이다. 체크리스트도 N/A일 때는 사유를 반드시 적으라고 요구한다(_"Must provide a justification when status is N/A"_).[^yaml135] GPU를 한 장이라도 꽂는 순간 이 항목은 즉시 살아나고, DCGM exporter 같은 걸 붙여야 통과할 수 있다.

---

## 8. GPU 없이 AI를 한다는 것

이 클러스터의 AI 서비스는 추론을 하지 않는다. 외부 LLM API를 호출하고, 클러스터는 이런 것들을 맡는다.

- **검색**: pgvector 위의 임베딩 조회 (전용 Postgres 인스턴스)
- **상태**: 대화 이력, 멱등성, 아웃박스
- **오케스트레이션**: 배포·롤아웃·시크릿·관측

컨포먼스 관점에서 이 아키텍처의 의미는 분명하다. 9개 MUST 중 **가속기에 직접 묶인 4개(1·6·8, 그리고 5의 가속기 조건)는 아예 무대에 오르지 않는다.** 하지만 나머지는 그대로 남는다. 추론을 위임했다고 해서 트래픽 관리(`ai_inference`)나 오퍼레이터 신뢰성(`robust_controller`), 메트릭 수집(`ai_service_metrics`)이 면제되지는 않는다.

오히려 이 구조에서 `ai_inference` 는 더 중요해진다. 외부 API와 자체 호스팅 모델을 나중에 섞으려면 그 경계에 라우팅 계층이 있어야 하는데, Inference Extension이 정확히 그 자리를 노린다 — 자체 호스팅 모델을 "model-as-a-service 제공자와 나란히" 통합하는 것.[^gie-intro] 지금 Gateway API가 CRD만 남아 있는 상태라는 건, **미래에 하이브리드로 갈 때 지불해야 할 빚이 이미 쌓여 있다**는 뜻이다.

---

## 9. 그래서 무엇을 할 것인가

채점 결과에서 나온 우선순위는 이렇다. GPU 구매는 목록에 없다.

1. **Gateway API를 결정한다.** 구현체를 올려 실제로 쓰거나, 안 쓸 거면 CRD가 왜 남아 있는지 문서에 적는다. 지금은 "설치돼 있지만 아무도 처리하지 않는 API"가 클러스터에 떠 있는 상태이고, 이건 다음 사람에게 "쓸 수 있다"는 잘못된 신호를 준다.
2. **관측 통과를 증거로 고정한다.** ServiceMonitor 개수가 아니라 타깃 `up` 상태를 대시보드에 박아둔다.
3. **갱 스케줄링은 v1.36 업그레이드까지 보류한다.** 지금 Kueue를 올리면 v1.36의 인트리 PodGroup과 중복 개념이 생긴다. 다만 이건 "안 함"이 아니라 "언제 할지 정함"이다.
4. **N/A 항목에 사유를 남긴다.** 가속기 없음은 사실이지만, 기록되지 않은 부재는 나중에 통과로 오독된다.

---

## 마치며

이 글에서 가장 놀란 건 점수가 낮다는 사실이 아니라, **떨어진 이유가 GPU와 무관했다**는 점이다.

AI 워크로드를 쿠버네티스에 올린다는 건 가속기를 꽂는 일이 아니라 **트래픽·스케줄링·관측·오퍼레이터라는 오래된 네 가지를 AI 형태의 부하에 맞게 다시 세우는 일**에 가깝다. CNCF의 체크리스트가 9개 MUST를 6개 영역에 나눠 놓은 것도 그래서일 것이다. 가속기 영역의 MUST는 9개 중 **하나**뿐이다.

그리고 이 채점을 하면서 두 번, 같은 종류의 함정을 만났다. `resource.k8s.io/v1` 은 GA인데 ResourceSlice가 0개였고, Gateway API CRD는 v1.4.0인데 GatewayClass가 0개였다. 둘 다 "지원한다"는 질문에는 예라고 답하고, "동작한다"는 질문에는 아니오라고 답한다. 자기평가로 운영되는 인증 프로그램에서 이 차이는 그대로 리스크가 된다. 저장소가 `MUST` 항목에 대해 `status` 뿐 아니라 **`evidence` 를 공개 URL로 요구하는 이유**도 여기 있을 것이다.[^instructions]

내 클러스터는 아직 인증을 신청할 수준이 아니다. 다만 무엇이 없는지는 이제 아홉 줄로 안다.

---

## References

[^k8s-dra-ga]: Kubernetes Blog, "Kubernetes v1.34: DRA has graduated to GA", 2025-09-01. <https://kubernetes.io/blog/2025/09/01/kubernetes-v1-34-dra-updates/>

[^cncf-dra]: CNCF Blog, "Understanding dynamic resource allocation in Kubernetes", 2026-07-01. <https://www.cncf.io/blog/2026/07/01/understanding-dynamic-resource-allocation-in-kubernetes/> (본문에 "GA in Kubernetes v1.35"로 기재 — 공식 릴리스 블로그와 불일치)

[^gcp-dra]: Google Cloud Blog, "DRA: A new era of Kubernetes device management with Dynamic Resource Allocation", 2026-03-25. <https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-device-management-with-dra-dynamic-resource-allocation> (벤더 1차 자료)

[^wg-device]: Kubernetes Blog, "Spotlight on WG Device Management", 2026-06-24. <https://kubernetes.io/blog/2026/06/24/wg-device-management-spotlight-2026/>

[^k8s-136-sched]: Kubernetes Blog, "Kubernetes v1.36: Advancing Workload-Aware Scheduling", 2026-05-13. <https://kubernetes.io/blog/2026/05/13/kubernetes-v1-36-advancing-workload-aware-scheduling/>

[^cncf-launch]: CNCF, "CNCF Launches Certified Kubernetes AI Conformance Program to Standardize AI Workloads on Kubernetes", 2025-11-11. <https://www.cncf.io/announcements/2025/11/11/cncf-launches-certified-kubernetes-ai-conformance-program-to-standardize-ai-workloads-on-kubernetes/>

[^repo]: cncf/k8s-ai-conformance, README. <https://github.com/cncf/k8s-ai-conformance>

[^yaml135]: cncf/k8s-ai-conformance, `docs/AIConformance-1.35.yaml`. <https://github.com/cncf/k8s-ai-conformance/blob/main/docs/AIConformance-1.35.yaml>

[^instructions]: cncf/k8s-ai-conformance, `instructions.md`. <https://github.com/cncf/k8s-ai-conformance/blob/main/instructions.md>

[^gie-pool]: Kubernetes Gateway API Inference Extension, "InferencePool". <https://gateway-api-inference-extension.sigs.k8s.io/api-types/inferencepool/>

[^gie-intro]: Kubernetes Gateway API Inference Extension, "Introduction". <https://gateway-api-inference-extension.sigs.k8s.io/>

_본문의 클러스터 수치·`kubectl` 출력은 2026-08-13 자체 클러스터(K3s v1.35.4+k3s1, 6노드)에서 직접 실행한 결과다. 갱 스케줄링 확률식은 직관 설명용 모형이며 실제 스케줄러 동작을 예측하지 않는다._
