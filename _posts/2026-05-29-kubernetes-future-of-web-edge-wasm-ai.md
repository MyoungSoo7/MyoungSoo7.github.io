---
layout: post
title: "Kubernetes 와 웹의 미래 — *서버는 어디에 사는가*: Edge, WASM, AI 추론이 다시 그리는 *런타임의 지도*"
date: 2026-05-29 00:35:00 +0900
categories: [kubernetes, web, future]
tags: [k8s, edge-computing, wasm, ai-inference, serverless, vercel, cloudflare, webassembly, kubeedge]
---

> *''서버는 어디에 사는가?''* — 이 질문은 25 년간 단 한 번도 같은 답을 가진 적이 없다. *''내 컴퓨터 밑에 있는 본체''* 에서 시작해서 *''랙 끝의 1U 서버''*, *''AWS 의 한 리전''*, *''엣지의 PoP''*, *''사용자 브라우저''* 까지 — *서버의 거주지* 는 계속 *사용자 쪽으로 움직여 왔다*. 그리고 그 이동의 매 단계마다 **Kubernetes** 는 *옆에 있었다*.

이 글은 *웹의 미래* 를 *런타임 위치의 이동* 이라는 시선으로 풀어본다. *서버리스, Edge, WASM, AI 추론* — 한 번씩 *''이것이 K8s 의 종말이다''* 라는 헤드라인을 만들어낸 흐름들이, *왜* 다시 *K8s 안으로 흡수되고 있는가*. 그리고 *K8s 가 플랫폼의 OS* 가 된 다음, 웹 개발자는 *무엇을 잃고 무엇을 얻는가*.

---

## 1. 웹의 *서버* 가 옮겨다닌 30 년

웹의 *''서버''* 는 한 번도 같은 곳에 있지 않았다:

| 시대 | 서버의 거주지 | 대표 도구 |
|---|---|---|
| 1995 | 사무실 책상 밑 본체 | Apache + PHP, *내 컴퓨터를 24/7 켜두기* |
| 2000 | 코로케이션 데이터센터 | *''호스팅 업체''* 시대 |
| 2008 | 퍼블릭 클라우드 (AWS EC2) | *''탄력적''* 서버, 하지만 여전히 VM |
| 2014 | 컨테이너 + 스케줄러 | Docker + Kubernetes |
| 2017 | 서버리스 함수 | AWS Lambda, Vercel Functions |
| 2020 | Edge PoP | Cloudflare Workers, Fastly Compute |
| 2023+ | 브라우저 (WASM) | Pyodide, WebContainer, *서버 없이 도는 백엔드* |

매 단계의 *''서버의 위치 변화''* 는 *지연 시간을 줄이는 방향* 이었다. *''사용자 옆에 더 가까이''*. 그러나 그 *각 위치* 는 *서로 죽이지 못했다* — 정적 사이트도 쓰이고, EC2 도 쓰이고, Lambda 도 쓰이고, Edge 도 쓰인다. *모든 위치가 공존* 하는 것이 *2026 년 웹의 현실* 이다.

그리고 *이 모든 위치를 한 plane 으로 묶는* 흐름이 *K8s 의 다음 챕터* 다.

## 2. *''서버리스가 K8s 를 죽인다''* — 그 다음 5 년이 보여준 것

2018 년 *''Lambda 가 K8s 를 끝낸다''* 라는 헤드라인이 유행했다. *''YAML 7 백 줄 쓰지 말고, 함수 하나만 던지면 끝''* 이라는 단순한 매력. 실제로 Vercel, Netlify, AWS Lambda 가 *프론트엔드 진영* 의 디폴트가 되었다.

그러나 5 년이 지나자 *반대편* 의 이야기가 흘러나오기 시작한다:

- **DHH 의 *Cloud Exit*** (2023) — 37signals 가 AWS 에서 자체 베어메탈로 회귀. *''Lambda 청구서가 EC2 보다 훨씬 비싸다''*
- **Cloudflare 의 *Workers for Platforms*** — 결국 *''서버리스''* 의 백엔드는 *컨테이너* 였다. *Cloudflare Workers* 는 V8 isolate 이지만, *그 isolate 들* 을 스케줄하는 plane 은 *Borg 닮은 시스템*
- **Vercel 의 *Fluid Compute*** (2024) — *''함수''* 가 *''long-running 컨테이너''* 로 진화. *결국 컨테이너 모델로 회귀*

*서버리스* 가 *K8s 를 죽이지 못한 이유* 는 단순하다:

1. *콜드 스타트* — 함수 모델은 *''첫 호출 200ms''* 의 비용을 지운다. AI 추론 같은 *''모델 메모리에 올리는데만 5초''* 인 워크로드엔 *치명적*
2. *상태 유지 비용* — *''상태 없는 함수''* 라는 환상은 *''Redis/RDS 에 떠넘긴 상태''* 일 뿐. 그 상태를 운영하려면 결국 *컨테이너*
3. *벤더 종속* — Lambda 에 묶이면 *Lambda 만 쓰는 코드* 가 됨. *K8s 는 어디든 돈다*

결국 *''서버리스 vs K8s''* 가 아니라, *서버리스의 *내부 구현* 이 K8s 닮아간다* 가 진짜 흐름이 되었다.

## 3. Edge Computing — *PoP 안의 K8s*

2020 년대 초반의 *Edge 혁명* 은 두 가지 길로 갈라졌다:

### 3.1. *경량 런타임* 길 — Cloudflare, Fastly

V8 isolate 또는 WASM 런타임을 *전 세계 PoP* 에 깔고, *''작은 함수''* 만 돌린다. 시작 시간 *5ms*, 메모리 *128MB* 같은 제약. *''CDN 옆의 코드 실행''*.

장점: *극단적으로 빠른 콜드 스타트, 압도적인 분산*
단점: *''Node.js full API''* 가 안 됨, *npm 패키지 절반이 안 돌아감*, *상태 유지 어려움*

### 3.2. *경량 K8s* 길 — K3s, KubeEdge, microk8s

*''엣지에 작은 K8s 를 깔자''*. 5G 기지국, 산업용 게이트웨이, 매장의 NUC 같은 곳에 *K3s* 가 *상주*. 중앙에서 *manifest 만 푸시* 하면 *전국 매장에 동시에 배포*.

장점: *기존 K8s 생태계 그대로*, *상태 유지 가능*, *복잡한 워크로드 OK*
단점: *''isolate 5ms''* 같은 콜드 스타트는 불가능. 운영 부담 있음

**두 길의 화해** — 2024 년 이후 *''Edge K8s 안에 WASM 런타임''* 이라는 *합성 패턴* 이 등장한다. **wasmCloud**, **SpinKube**, **Fermyon Spin on K8s** 같은 프로젝트들이 *''K8s pod 가 WASM 모듈을 호스팅''* 하는 모델을 표준화한다.

즉 *''K8s 가 컨테이너만 돌리는 게 아니라 WASM 모듈도 돌린다''* 가 가능해진다. *''컨테이너 = K8s 의 유일한 런타임''* 시대가 끝나가는 신호다.

## 4. WASM — *컨테이너 다음의 단위*

WebAssembly 는 원래 *''브라우저에서 C++ 돌리려고''* 만들어진 기술이었다. 그러나 *서버사이드 WASM* 이 발견된 후 *전혀 다른 의미* 를 갖게 된다:

| 비교 | Docker 컨테이너 | WASM 모듈 |
|---|---|---|
| 시작 시간 | 100ms~수초 | *0.1ms* |
| 크기 | 보통 100MB+ | *수 KB ~ 수 MB* |
| 격리 | Linux 커널 namespace | *런타임 자체 (capability 기반)* |
| 호스트 의존성 | 리눅스 커널 ABI | *없음* (WASI 표준) |
| 멀티 아키텍처 | 빌드 시점 분리 | *바이너리 그대로 어디든* |

*WASM 의 진짜 매력* 은 *''크기와 속도''* 보다 *''격리 모델''* 이다. 컨테이너는 *''리눅스를 작게 자른 것''* 이지만, WASM 은 *''리눅스가 필요 없는 격리''* 다. *어떤 OS 든, 어떤 아키텍처든* — *.wasm* 파일은 *변경 없이* 돈다.

이게 *멀티 클라우드, 엣지, 브라우저* 를 *''같은 바이너리''* 로 묶을 수 있는 *유일한 모델* 이다. *''서버에서 돌던 함수를 그대로 브라우저로 옮긴다''* 가 *WASM 만의 가능성*.

K8s 는 이걸 *''pod 안의 wasm runtime''* 으로 받아들이는 중이다. **runwasi**, **WasmEdge**, **wasmtime** 같은 *containerd shim* 들이 K8s 와 WASM 사이를 연결한다. *2026 년 현재* — 같은 K8s 클러스터에 *컨테이너 pod 와 WASM pod 가 공존* 한다.

## 5. AI 추론 워크로드 — *왜 다시 K8s 인가*

2023 년 LLM 폭발 이후 *''AI 워크로드는 어디서 돌리지?''* 가 핵심 질문이 되었다. 그리고 *2026 년의 답* 은 *대부분 K8s* 다. 이유:

### 5.1. *GPU 스케줄링은 sched 의 영역*

LLM 추론은 *''GPU 한 장 = 한 모델''* 이라는 단순한 모델이 안 통한다. *vLLM*, *TensorRT-LLM* 같은 엔진들은 *''여러 요청을 한 GPU 에 묶어 처리 (continuous batching)''* 를 한다. 이걸 효율적으로 운영하려면 *''GPU 메모리 사용량 기반 스케줄링''* 이 필요한데, *Kubernetes Device Plugin* + *NVIDIA GPU Operator* 만큼 잘 푸는 도구가 없다.

### 5.2. *추론 비용 = 사실상 컴퓨팅 비용*

OpenAI 호출 1 백만 번이 *수십~수백만원* 단위인 시대다. *''내 모델을 내가 호스팅하면 1/10 이 된다''* 는 산수가 *실제로 맞다*. 그래서 *self-hosted inference* 가 다시 흥하고 있고, 그건 *K8s + GPU 풀* 이라는 형태다.

### 5.3. *KServe, Triton, Ray 모두 K8s 위에서 돈다*

추론 서빙 표준 도구들 — **KServe** (Kubeflow), **NVIDIA Triton**, **Ray Serve**, **vLLM Production Stack** — *전부 K8s 네이티브*. *''내 LLM 을 운영한다''* 는 곧 *''K8s 위에 KServe 를 깐다''* 와 거의 동의어가 되었다.

## 6. *MCP, AI Agent, 그리고 K8s 의 새로운 부하*

2024 년 Anthropic 이 발표한 **MCP (Model Context Protocol)** 이후 *''AI 가 다른 도구를 호출한다''* 라는 패턴이 빠르게 표준화됐다. *Tool use*, *Function calling*, *Agent loop* — 표현은 다르지만 *공통 구조* 는 *''LLM 추론 + 도구 호출의 무한 반복''* 이다.

이게 K8s 에 의미하는 바:

1. *워크로드 패턴이 변한다* — 기존엔 *''사용자 요청 → 응답''* 이 *수 백 ms*. 이제는 *''agent 실행 → 5 분 도구 호출 chain''*. **long-running task** 가 디폴트가 됨
2. *내부 트래픽 폭증* — 한 사용자 요청이 *10 개의 내부 API 호출* 로 펼쳐짐. *Service Mesh, mTLS, Observability* 의 부담이 *10 배* 가 됨
3. *Stateful inference cache* — KV cache 공유, 모델 weight 공유, RAG 인덱스 공유 — *''pod 가 stateless 다''* 는 더 이상 사실이 아님

이 셋이 모이면서 *K8s 의 다음 5 년 진화* 가 결정된다. *Stateful workload* 를 *cloud-native* 하게 다루는 것 — *''statefulset 으로 충분하지 않다''* 가 *현재의 합의*. 새 abstraction 이 필요하고, *KubeVirt, KubeRay, Volcano* 같은 *''상태가 있는 워크로드를 위한 K8s 확장''* 이 메인 스트림으로 올라온다.

## 7. *그러면 웹 개발자는 어디에 있어야 하나?*

여기까지 읽으면 *''결국 다 K8s 다''* 라는 결론으로 보일 수 있다. *반은 맞고 반은 틀리다*.

웹 개발자 입장에서 *2026 년 현실적 분포* 는 이렇다:

| 워크로드 | 어디 사는 게 자연스러운가 |
|---|---|
| 정적 사이트 / 마케팅 페이지 | *Vercel / Cloudflare Pages / GitHub Pages* — K8s 가 *과한 곳* |
| API 백엔드, 중간 규모 SaaS | *K8s 위의 컨테이너* — 비용·관측·이식성 최선 |
| Edge 함수 (지오 라우팅, A/B) | *Cloudflare Workers, Vercel Edge* — *낮은 지연이 진짜 가치* |
| 상태 있는 시스템 (DB, MQ, 캐시) | *K8s + Operator* 또는 *매니지드 서비스*. *Lambda 절대 아님* |
| AI 추론 | *K8s + KServe/vLLM* — *self-host 의 의미가 큰 영역* |
| 백그라운드 워커 / 큐 처리 | *K8s Jobs / Argo Workflows* — *오래 도는 일은 K8s* |

*핵심* 은 *''K8s 가 모든 걸 한다''* 가 아니라, *''K8s 가 *플랫폼 OS* 로서 다른 도구들이 그 위에 산다''* 가 정확한 그림이다. *Vercel 도 내부적으론 K8s 닮은 plane 위에 산다*. 사용자가 *모르는 것* 일 뿐.

웹 개발자가 *직접* K8s yaml 을 만질 필요는 *대부분의 경우 없다*. 그러나 *''내 시스템이 *어디* 사는지''* 에 대한 *직관* 은 필요하다. *Cloudflare 의 무료 티어가 왜 무료인지*, *Vercel 함수가 왜 콜드 스타트 비용이 있는지*, *왜 RDS 가 Lambda 보다 EC2 위에 더 잘 어울리는지* — 이 *직관* 들이 *비용·성능·이식성* 을 가른다.

## 8. *예측* — 2030 년 웹은 어떻게 생겼을까

*확실히 일어나는 일* 과 *확실하지 않은 일* 을 나눠보자.

### 확실히 일어나는 일

- *K8s 는 *''플랫폼의 플랫폼''* 으로 자리잡는다* — 사용자가 안 보지만 어디나 있음
- *WASM 이 *''두 번째 컨테이너''* 가 된다* — 같은 K8s 에 컨테이너 pod 와 WASM pod 가 공존
- *AI 추론 비용이 *지배적인 클라우드 비용 항목* 이 된다* — *''GPU 시간 = 새로운 통화''*
- *Edge 와 클라우드의 경계가 *흐려진다* — *''같은 manifest 가 PoP 도 데이터센터도''*

### 확실하지 않은 일

- *완전한 *self-host AI* 가 일반화될까* — GPU 가격이 충분히 떨어질까? 모델 사이즈가 진정될까? *모름*
- *서버리스 vs K8s 의 *대중 인식* 이 어떻게 갈릴까* — *''Lambda 가 좋다''* 의 마케팅 영향
- *브라우저 안의 백엔드 (WebContainer, Pyodide) 가 *어디까지* 가능해질까* — 보안·성능 한계
- *유럽·중국·미국의 *규제 차이* 가 *기술적 분기* 를 만들까* — *''데이터 주권''* 이 클라우드 디자인을 결정할 수도

## 9. 정리 — *K8s 의 진짜 정체*

처음에 던진 질문 — *''서버는 어디에 사는가?''* — 의 *2026 년 답안* 은 *''어디에든''* 이다. 책상 밑이든, AWS 리전이든, PoP 의 isolate 이든, 사용자 브라우저든. 그러나 *''어디에든 같은 manifest 로 배포 가능하다''* 는 *한 가지 사실* 이 *지난 10 년의 성과* 다.

**Kubernetes 는 *컨테이너 오케스트레이터* 가 아니다.** 그 시절은 2018 년에 끝났다. 지금의 K8s 는 *''분산 워크로드를 선언형으로 다루는 표준 API''* — 그리고 *컨테이너, WASM, VM, AI 모델, 외부 클라우드 자원* 까지 *모두 같은 모델 안에서 다룬다*.

웹의 미래는 *''K8s 위의 웹''* 이 아니라, *''K8s 라는 *플랫폼 OS* 위에서 웹이 어디에든 산다''* 가 정확한 표현이다. 사용자가 그 OS 의 존재를 *모를수록* — *그게 좋은 OS 의 정의* 다.

> *''The best infrastructure is the one you don't have to think about.''* — 그리고 K8s 는 그 *''생각 안 해도 되는 OS''* 가 되어가는 중이다.

---

## 더 읽을 거리

- *Wasm Is Going to Replace Containers* — Solomon Hykes (Docker 창업자), 2019 — *https://twitter.com/solomonstre/status/1111004913222324225*
- *CNCF WG: WebAssembly* — *https://github.com/cncf/tag-runtime/tree/main/wg/wasm*
- *KubeEdge 공식 — Edge K8s 의 표준 candidates*
- *vLLM Production Stack* — *self-host LLM serving 의 현재 best practice*
- *Vercel Fluid Compute* — 서버리스가 *컨테이너 모델로 회귀* 한 케이스 스터디
- *Cloudflare Workers Internals* — Workers 가 어떻게 *isolate 기반으로 V8 을 호스팅* 하는지

*다음 글 예고: 자가 호스팅 AI 추론 — 미니 PC 5대로 LLM 을 띄우는 비용·아키텍처 분석*
