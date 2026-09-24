---
layout: post
title: "NVIDIA Nemotron — GPU 회사는 왜 모델을 공짜로 푸는가?"
date: 2026-09-25 02:30:42 +0900
categories: [AI, LLM]
tags: [Nemotron, NVIDIA, Open Weights, Mamba, MoE, Hybrid Architecture, NVFP4, LLM]
---

NVIDIA 는 모델을 팔아서 돈을 버는 회사가 아니다. 그런데 **가중치·학습 데이터·레시피까지 공개하는 오픈 모델 패밀리**를 가장 공격적으로 내놓는 회사 중 하나가 되었다. 그 이름이 Nemotron 이다.

이 글의 주장은 이렇다. **Nemotron 은 "좋은 무료 모델" 이기 전에 "NVIDIA 하드웨어에서 추론이 가장 싸지는 설계" 의 레퍼런스 구현이다.** 이걸 알고 보면 아키텍처 선택, 벤치마크 방식, 라이선스까지 한 줄로 꿰어진다.

## 1. 계보 — 이름부터 헷갈린다

먼저 함정 하나. Hugging Face 에는 2023년 11월에 올라온 `nemotron-3-8b-base-4k` 가 있다.[^old3] 2025년 12월 발표된 **Nemotron 3 패밀리**와는 **다른 세대의 모델**이다. 검색해서 "Nemotron 3" 를 받을 때 등록일부터 확인하자.

주요 흐름만 추리면 이렇다.

| 시기 | 모델 | 핵심 |
|---|---|---|
| 2024.06 | Nemotron-4 340B | Base/Instruct/Reward 공개. 정렬 데이터의 98% 이상이 합성 데이터[^n4] |
| 2025.04 | Nemotron-H (8B, 56B/47B) | 대부분의 어텐션을 **Mamba** 로 교체한 하이브리드[^nh] |
| 2025.08 | Nemotron Nano 2 (9B) | 하이브리드 추론 모델, 단일 A10G 에서 128k 추론 목표[^nano2] |
| 2025.12 | **Nemotron 3** Nano (30B-A3B) | Nemotron 3 패밀리 시작[^news] |
| 2026.03 | Nemotron 3 Super (120B, 12B 활성) | LatentMoE, NVFP4 사전학습, MTP[^super] |
| 2026.04 | Nemotron 3 Nano Omni | 텍스트·이미지·비디오에 오디오까지[^omni] |
| 2026.06 | Nemotron 3 Ultra (550B, 55B 활성) | 패밀리 최대, 1M 컨텍스트[^ultra] |

(시기는 기술 보고서 날짜 또는 Hugging Face 등록일 기준)

## 2. 설계 — 모든 선택이 "추론 비용" 을 향한다

### 2.1 하이브리드 Mamba-Transformer

트랜스포머의 어텐션은 토큰을 하나 생성할 때마다 지금까지의 KV 캐시 전체를 본다. 컨텍스트가 길어질수록 메모리와 계산이 함께 늘어난다. Nemotron-H 논문은 이 병목을 정면으로 겨냥했다.[^nh]

> *"we replace the majority of self-attention layers in the common Transformer model architecture with Mamba layers that perform constant computation and require constant memory per generated token."*

Mamba 는 고정 크기 상태로 시퀀스를 처리하는 상태공간모델(SSM) 계열이다. 전부 Mamba 로 바꾸면 정확도가 떨어지므로 **어텐션 층을 일부만 남기는** 하이브리드로 간다. Nemotron 3 Super 보고서도 KV 캐시의 증가를 *"The primary systems bottleneck"* 이라 부르며 Mamba-2 블록을 주력으로 쓴다고 설명한다.[^super]

### 2.2 MoE — 크게 만들고 조금만 쓴다

Nemotron 3 는 여기에 MoE(Mixture-of-Experts)를 얹었다. Super 는 전체 120B 중 토큰당 12B 만, Ultra 는 550B 중 55B 만 활성화된다.[^super][^ultra] NVIDIA 는 이를 **LatentMoE** 라 부르며, *"accuracy per FLOP and accuracy per parameter"* 를 함께 최적화하는 구조라고 설명한다.[^super]

### 2.3 NVFP4 와 MTP — 하드웨어와 맞물리는 부분

- **NVFP4 사전학습** — Super 는 Nemotron 3 중 처음으로 4비트 부동소수 형식으로 사전학습했다. 배포용 체크포인트도 *"FP8 (W8A8) for Hopper and NVFP4 (W4A4) for Blackwell"* 로 나뉜다.[^super] 즉 가장 싼 정밀도의 이점은 **Blackwell 세대 GPU** 에서 온다.
- **MTP(Multi-Token Prediction)** — 별도 초안 모델 없이 모델 자체가 여러 토큰을 미리 제안하는 투기적 디코딩으로 처리량을 올린다.[^super]

하이브리드는 KV 캐시를 줄이고, MoE 는 활성 계산을 줄이고, NVFP4 와 MTP 는 NVIDIA 최신 하드웨어에서 토큰당 비용을 더 줄인다. **모든 층이 같은 방향을 가리킨다.**

## 3. "오픈" 의 범위 — 가중치만이 아니다

Nemotron 이 다른 오픈 웨이트 모델과 구별되는 지점은 **데이터와 레시피**다.

- Super 보고서: 데이터셋과 base·post-trained·quantized 체크포인트를 Hugging Face 에 공개했다고 밝힌다.[^super]
- Ultra 보고서: *"We open-source the base, post-trained, and quantized checkpoints, along with the training data and recipe"*.[^ultra]
- 사전학습 데이터의 한 축인 **Nemotron-CC** 는 Common Crawl 을 정제하는 방법 자체를 논문으로 공개했다.[^cc]

재현 가능성이라는 측면에서 이건 가중치만 던지는 공개와 질적으로 다르다.

### 라이선스는 두 갈래다

Hugging Face 모델 카드를 보면 라이선스가 세대 안에서도 갈린다.

| 모델 | 라이선스 |
|---|---|
| Nemotron 3 Nano, Super | NVIDIA Nemotron Open Model License[^nano-card][^super-card] |
| Nemotron 3 Ultra, 3.5 Lightning | OpenMDW-1.1[^ultra-card][^l35-card] |

NVIDIA 라이선스는 상업적 사용과 파생물 배포를 허용하고 출력물의 소유권을 주장하지 않는다. 다만 이 모델이나 그 출력물이 특허·저작권을 침해한다며 **소송을 제기하면 라이선스가 종료**되는 조항과, 재배포 시 **"Licensed by NVIDIA Corporation under the NVIDIA Nemotron Model License."** 고지 의무가 있다.[^nvlic] OpenMDW-1.1 은 모델과 관련 데이터·문서·소프트웨어를 저작권·특허·데이터베이스 권리까지 포함해 *"without restriction"* 으로 허락하고, 재배포 시 라이선스 사본과 고지 유지를 요구하는 더 단순한 형태다.[^openmdw] 도입 전에 **어느 모델이 어느 라이선스인지** 를 모델 단위로 확인해야 한다.

## 4. 한계 — 벤더 보고서를 읽는 법

### 4.1 처리량 수치는 서로 다른 엔진으로 쟀다

Ultra 보고서는 GLM-5.1, Kimi-K2.6, Qwen-3.5 대비 각각 **5.9배, 4.8배, 1.6배** 높은 처리량을 주장한다(8K 입력 / 64K 출력).[^ultra] 그런데 측정 조건 각주가 중요하다.

> *"All throughput numbers are reported at max-throughput using NVFP4 precision on GB200. For Nemotron 3 Ultra, throughput numbers are obtained from TRT-LLM, while all other model numbers use vLLM."*

즉 **자사 모델은 자사 추론 엔진(TensorRT-LLM), 경쟁 모델은 vLLM** 이고, 하드웨어는 자사 최신 GB200 이다. 아키텍처 이점이 실재하더라도, 이 배수에는 엔진 최적화의 차이가 섞여 있다. 이 글은 이를 **벤더 주장**으로 읽는다. 동일 엔진·동일 하드웨어의 중립적 제3자 측정은 확인하지 못했다.

### 4.2 이득은 NVIDIA 최신 세대에서 가장 크다

NVFP4 체크포인트는 Blackwell 용이다.[^super] 구세대 GPU 나 타사 가속기에서는 FP8·BF16 체크포인트를 써야 하고, 그만큼 보고서의 처리량 그래프와 거리가 생긴다. 오픈 모델이지만 **최적 경로는 특정 하드웨어로 이어진다.** GPU 회사가 모델을 공짜로 푸는 이유가 여기에 있다.

### 4.3 한국어는 공식 지원이 아닌 경우가 많다

모델 카드의 공식 지원 언어를 보면 차이가 크다.

- Nano 30B-A3B: 영어, 독일어, 스페인어, 프랑스어, 이탈리아어, 일본어[^nano-card]
- Super 120B: 위에 중국어 추가[^super-card]
- Ultra 550B: **한국어 포함** 10개 언어[^ultra-card]

한국어 서비스에 Nano·Super 를 쓰려면 "되긴 하는지" 가 아니라 **자체 평가셋으로 직접 검증**해야 한다.

### 4.4 Mamba 계층은 생태계 지원을 탄다

Mamba 층과 LatentMoE 는 순수 트랜스포머에 비해 새로운 구조다. 추론 엔진, 양자화 도구, 파인튜닝 프레임워크가 이 구조를 지원하는지는 **사내 서빙 스택의 버전 단위로** 따로 확인해야 한다. 표준 트랜스포머처럼 "어디서나 그냥 돈다" 고 가정하면 안 된다.

## 5. 언제 고려할 만한가

1. **긴 출력·긴 컨텍스트 에이전트** — KV 캐시 부담이 큰 워크로드일수록 하이브리드의 이점이 실제로 나타날 여지가 크다.
2. **NVIDIA 최신 GPU 를 이미 쓰는 온프레미스** — NVFP4·TRT-LLM 경로를 온전히 탈 수 있다.
3. **데이터·레시피 재현이 필요한 연구·규제 환경** — 공개 범위가 넓다.
4. 반대로, **한국어 중심 서비스를 작은 모델로** 하려면 공식 지원 언어부터 확인하고 자체 평가를 먼저 돌린다.

## 맺으며 — 공짜 모델의 청구서

Nemotron 은 오픈 모델 생태계에 분명한 기여를 한다. 데이터와 레시피까지 여는 대형 벤더는 흔치 않다. 하이브리드 Mamba-MoE 라는 설계 방향도 논문과 공개 체크포인트로 누구나 검증할 수 있다.

하지만 공짜 모델에도 청구서는 있다. 그 청구서는 라이선스가 아니라 **하드웨어 로드맵**에 적혀 있다. 보고서의 가장 인상적인 숫자는 Blackwell, NVFP4, TRT-LLM 이 모두 맞물린 조건에서 나온다. Nemotron 을 쓴다는 건 모델 하나를 고르는 일이면서, 동시에 **그 숫자를 재현할 스택**을 고르는 일이다.

---

## References

[^old3]: Hugging Face, *nvidia/nemotron-3-8b-base-4k* (2023-11-14 등록). <https://huggingface.co/nvidia/nemotron-3-8b-base-4k>
[^n4]: NVIDIA, *Nemotron-4 340B Technical Report*, arXiv:2406.11704. <https://arxiv.org/abs/2406.11704>
[^nh]: NVIDIA, *Nemotron-H: A Family of Accurate and Efficient Hybrid Mamba-Transformer Models*, arXiv:2504.03624. <https://arxiv.org/abs/2504.03624>
[^nano2]: NVIDIA, *NVIDIA Nemotron Nano 2: An Accurate and Efficient Hybrid Mamba-Transformer Reasoning Model*, arXiv:2508.14444. <https://arxiv.org/abs/2508.14444>
[^news]: NVIDIA Newsroom, *NVIDIA Debuts Nemotron 3 Family of Open Models* (2025-12-15). <https://nvidianews.nvidia.com/news/nvidia-debuts-nemotron-3-family-of-open-models>
[^super]: NVIDIA, *Nemotron 3 Super: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning* (2026-04-03). <https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Super-Technical-Report.pdf>
[^omni]: NVIDIA, *Nemotron 3 Nano Omni: Efficient and Open Multimodal Intelligence* (2026-04-27). <https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Omni-report.pdf>
[^ultra]: NVIDIA, *Nemotron 3 Ultra: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning* (2026-06-09). <https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf>
[^cc]: Su et al., *Nemotron-CC: Transforming Common Crawl into a Refined Long-Horizon Pretraining Dataset*, arXiv:2412.02595. <https://arxiv.org/abs/2412.02595>
[^nano-card]: Hugging Face, *nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16* model card. <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16>
[^super-card]: Hugging Face, *nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16* model card. <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16>
[^ultra-card]: Hugging Face, *nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16* model card. <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16>
[^l35-card]: Hugging Face, *nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16* model card. <https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16>
[^nvlic]: NVIDIA, *NVIDIA Nemotron Open Model License*. <https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/>
[^openmdw]: OpenMDW, *OpenMDW License Agreement, version 1.1*. <https://openmdw.ai/license/1-1/>
