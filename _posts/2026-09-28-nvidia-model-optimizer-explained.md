---
layout: post
title: "NVIDIA Model Optimizer(ModelOpt) 정리 — 학습 끝난 모델을 '배포용'으로 줄이는 라이브러리"
date: 2026-09-28 22:32:43 +0900
categories: [AI]
tags: [NVIDIA, ModelOpt, Quantization, NVFP4, FP8, Distillation, Pruning, SpeculativeDecoding, TensorRT-LLM, vLLM, SGLang]
---

> 리포: **[github.com/NVIDIA/Model-Optimizer](https://github.com/NVIDIA/Model-Optimizer)** · 문서: [nvidia.github.io/Model-Optimizer](https://nvidia.github.io/Model-Optimizer/) · PyPI: [`nvidia-modelopt`](https://pypi.org/project/nvidia-modelopt/)

모델을 학습시키는 것과 **그 모델을 싸고 빠르게 서빙하는 것**은 다른 문제입니다. 가중치가 BF16이면 파라미터 1개에 2바이트가 들고, 수천억 파라미터 모델은 GPU 몇 장을 채우고 시작합니다. NVIDIA Model Optimizer(줄여서 **ModelOpt**)는 이 간극을 메우는 도구로, **학습이 끝난 모델을 양자화·가지치기·증류 등으로 줄여 추론 프레임워크가 바로 올릴 수 있는 체크포인트로 내보내는 라이브러리**입니다. 이 글은 리포 README, 공식 문서, 릴리스 노트(0.47.0), NVIDIA 기술 블로그만 근거로 정리했습니다.

---

## 1. 한 줄 정의와 위치

README의 정의를 옮기면, ModelOpt는 양자화(quantization), 가지치기(pruning), 신경망 구조 탐색(NAS), 증류(distillation), 추측 디코딩(speculative decoding), 희소성(sparsity) 같은 **모델 최적화 기법을 모아 둔 라이브러리**입니다([README](https://github.com/NVIDIA/Model-Optimizer#readme)).

흐름은 세 단계로 설명됩니다.

| 단계 | 내용 |
| --- | --- |
| **Input** | Hugging Face, PyTorch, ONNX 모델 |
| **Optimize** | 위 기법들을 Python API로 조합. Megatron-Bridge, Megatron-LM, HF Accelerate 와 연동해 학습이 필요한 기법(QAT·증류)도 수행 |
| **Export** | 최적화된 체크포인트를 **TensorRT-LLM, TensorRT, vLLM, SGLang** 에서 바로 배포. HF 통합 export 는 transformers·diffusers 모델 모두 지원 |

즉 ModelOpt 자체는 **서빙 엔진이 아닙니다.** 모델을 "줄이는 공장"이고, 실제 서빙은 TensorRT-LLM·vLLM·SGLang 같은 엔진이 맡습니다. 이 분업이 이 도구를 이해하는 핵심입니다.

### 연혁 (README "Latest News" 기준)

- 2024-04: 리포 생성 (GitHub API `createdAt`), 2024-05 정식 공개 발표([NVIDIA 블로그](https://developer.nvidia.com/blog/accelerate-generative-ai-inference-performance-with-nvidia-tensorrt-model-optimizer-now-publicly-available/))
- 2025-01-28: **오픈소스화**, 같은 날 **NVFP4 지원** 추가
- 2025-12-08: 이름이 **"NVIDIA TensorRT Model Optimizer" → "NVIDIA Model Optimizer"** 로 변경. TensorRT 전용 도구가 아니라 vLLM·SGLang까지 겨냥한다는 방향 전환이 이름에 반영된 것으로 읽힙니다(해석).
- 2026-09-23: 최신 릴리스 **0.47.0** ([릴리스 노트](https://github.com/NVIDIA/Model-Optimizer/releases/tag/0.47.0))

라이선스는 **Apache 2.0** 입니다.

---

## 2. 기법 6가지 — 무엇을 줄이나

| 기법 | 하는 일 | 학습 필요? |
| --- | --- | --- |
| **PTQ** (Post-Training Quantization) | 학습 끝난 가중치·활성값을 FP8/NVFP4/INT8/INT4 등으로 낮춤. README 는 "모델 크기 2~4배 압축"이라고 설명 | ✗ (소량 캘리브레이션만) |
| **QAT / QAD** (Quantization-Aware Training / Distillation) | 양자화로 잃은 정확도를 짧은 추가 학습으로 회복. QAD 는 원본 모델을 선생으로 삼아 증류 | ○ |
| **Pruning** | 불필요한 가중치·레이어·차원을 제거 (Minitron, 2026-05 추가된 Puzzletron 등) | 보통 증류와 함께 |
| **Distillation** | 큰 모델(teacher)의 동작을 작은 모델(student)에게 학습 | ○ |
| **Speculative Decoding** | 작은 draft 모듈이 토큰을 미리 여러 개 예측하고 본 모델이 검증 → 지연시간 단축 | ○ (draft 학습) |
| **Sparsity** | 0이 아닌 값과 위치만 저장해 압축 | 경우에 따라 |

이 중 가장 많이 쓰이고 README 뉴스의 대부분을 차지하는 건 **양자화**입니다.

---

## 3. 핵심 기능: 양자화, 그리고 NVFP4

### 3.1 코드는 이 정도로 짧다

공식 PTQ 예제의 골자입니다([examples/hf_ptq](https://github.com/NVIDIA/Model-Optimizer/tree/main/examples/hf_ptq)).

```python
import modelopt.torch.quantization as mtq
from modelopt.torch.export import export_hf_checkpoint

model = AutoModelForCausalLM.from_pretrained("...")
calib_set = get_dataloader(num_samples=calib_size)  # 보통 128~512 샘플

def forward_loop(model):
    for batch in calib_set:
        model(batch)

# 1) 양자화 모듈로 교체 + 캘리브레이션
model = mtq.quantize(model, mtq.NVFP4_DEFAULT_CFG, forward_loop)

# 2) HF 통합 체크포인트로 내보내기 → TRT-LLM / vLLM / SGLang 에서 로드
with torch.inference_mode():
    export_hf_checkpoint(model, export_dir)
```

`forward_loop` 로 소량의 데이터를 흘려 보내 **각 층의 값 범위(amax)를 측정하고 스케일을 정하는 것**이 캘리브레이션입니다. 문서는 기본 캘리브레이션 데이터로 `cnn_dailymail` 과 `nemotron-post-training-dataset-v2` 를 섞어 쓴다고 밝히고, PTQ 정확도는 캘리브레이션 데이터 선택에 대체로 둔감하다고 설명합니다.

실무 팁도 문서에 있습니다. NVFP4 는 `NVFP4_DEFAULT_CFG` 보다 **`NVFP4_MLP_ONLY_CFG`(MLP·MoE 만 양자화), `NVFP4_EXPERTS_ONLY_CFG`(MoE 전문가만)** 를 권장합니다. 민감한 어텐션 QKV 프로젝션은 높은 정밀도로 남겨 두고 압축 이득이 큰 부분만 줄이자는 전략입니다.

### 3.2 NVFP4 가 뭔데

NVFP4 는 **Blackwell 세대에서 도입된 NVIDIA 의 4비트 부동소수점 형식**입니다([NVIDIA 기술 블로그, 2025-06-24](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/)).

- 값 자체는 **E2M1**(부호 1, 지수 2, 가수 1비트), 표현 범위는 대략 −6~6
- **16개 값마다 FP8(E4M3) 스케일 1개** + **텐서 전체에 FP32 스케일 1개**의 2단 스케일링
- 비교 대상인 **MXFP4** 는 32개 값마다 2의 거듭제곱 스케일(E8M0) 1개를 씁니다

블록을 16개로 더 잘게 나누고, 스케일을 2의 거듭제곱이 아닌 **소수 표현이 가능한 FP8** 로 두어 양자화 오차를 줄이는 것이 설계의 요지입니다. 같은 블로그는 메모리가 **FP16 대비 약 3.5배, FP8 대비 약 1.8배** 줄고, DeepSeek-R1-0528 에서 FP8 대비 정확도 하락이 1% 이하였다고 밝힙니다 — **벤더 1차 수치**입니다.

### 3.3 "4비트로 떨어뜨리면 멍청해지지 않나" — QAD

공격적인 W4A4(가중치·활성값 모두 4비트)는 정확도를 깎습니다. ModelOpt 가 최근 가장 밀고 있는 답이 **QAD(양자화 인지 증류)** 입니다. 양자화된 모델을 학생으로, 원본 BF16 모델을 선생으로 두고 짧게 증류해 잃은 정확도를 되찾습니다. 2026-08 에는 Nemotron 3.5 Lightning 을 NVFP4 + QAD 로 만든 사례가 [NVIDIA 블로그](https://developer.nvidia.com/blog/developing-nemotron-3-5-lightning-nvfp4-with-qad-using-nvidia-model-optimizer/)로 나왔고, 2026-09-16 에는 Qwen3.6-35B-A3B 의 W4A4 NVFP4 + QAD 튜토리얼이 리포에 추가됐습니다.

### 3.4 AutoQuantize — 층마다 다른 정밀도

모든 층을 같은 형식으로 누를 필요는 없습니다. **AutoQuantize** 는 층별로 NVFP4/FP8/BF16 중 무엇을 쓸지 **"유효 비트 수" 예산 안에서 자동 탐색**하는 혼합 정밀도 기능입니다([공식 소개글](https://nvidia.github.io/Model-Optimizer/announcements/autoquantize.html)). 0.47.0 에서는 이 설정이 CLI 플래그에서 **YAML recipe** 방식으로 완전히 옮겨졌습니다(아래 5절).

---

## 4. 실제 어디에 쓰였나 (벤더·고객 발표)

아래는 전부 NVIDIA 또는 해당 고객사의 **1차 발표 수치**이고, 중립 제3자의 재현 결과는 확인하지 못했습니다.

| 사례 | 주장 | 출처 |
| --- | --- | --- |
| Nemotron-3-Nano-30B-A3B | 가지치기 + 2단계 증류 + FP8 → vLLM 처리량 2.6배, 메모리 2.6배 절감 | [리포 튜토리얼](https://github.com/NVIDIA/Model-Optimizer/tree/main/examples/megatron_bridge/tutorials/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16) |
| Qwen3.6-35B-A3B | W4A4 NVFP4 + QAD → BF16 대비 vLLM 처리량 최대 1.30배, 체크포인트 3.1배 축소 | [리포 튜토리얼](https://github.com/NVIDIA/Model-Optimizer/tree/main/examples/megatron_bridge/tutorials/Qwen3.6-35B-A3B) |
| Bielik Minitron 7B | Minitron 가지치기+증류 → 33% 작고 50% 빠르며 품질 90% 유지 | [Bielik.AI](https://bielik.ai/en/nvidia-gtc-bielik-minitron-premiere/) |
| Domyn Colosseum | 355B → 260B 압축 | [Domyn 블로그](https://www.domyn.com/blog/domyn-large-the-journey-of-a-european-sovereign-ai-model-for-regulated-industries) |

흥미로운 점은 두 번째 사례입니다. **4비트로 체크포인트는 3.1배 줄었지만 처리량은 1.30배**에 그쳤습니다. 크기 감소가 곧바로 같은 배율의 속도 향상으로 이어지지는 않는다는 걸 벤더 스스로 보여 주는 수치라 오히려 믿을 만합니다. 처리량은 배치 크기, 디코드/프리필 비중, 커널 지원에 좌우됩니다.

바로 쓸 수 있는 **사전 양자화 체크포인트**도 Hugging Face 의 [NVIDIA 컬렉션](https://huggingface.co/collections/nvidia/inference-optimized-checkpoints-with-model-optimizer)에 올라와 있습니다(예: DeepSeek-R1-FP4, Llama-3.1-405B-Instruct-FP8, Nemotron-3-Super NVFP4).

---

## 5. 최신 0.47.0 (2026-09-23) 에서 볼 것

[릴리스 노트](https://github.com/NVIDIA/Model-Optimizer/releases/tag/0.47.0)에서 방향성이 보이는 항목만 추렸습니다.

- **"조용한 실패"를 막는 변경** — 설정은 가중치 양자화를 요구하는데 패턴이 모델의 어떤 모듈과도 매칭되지 않으면, 이전엔 캘리브레이션까지 돌고 **양자화 안 된 체크포인트(`"quant_algo": null`)** 를 내보냈습니다. 이제 `mtq.quantize` 가 에러를 냅니다. 모듈 이름이 다른 신규 아키텍처(예: Step-3.7 의 전문가 층)를 다룰 때 특히 중요합니다.
- **MoE 전문가별 스케일** — Transformer Engine 의 fused MoE(`TEGroupedLinear`)가 전문가 전체가 하나의 amax 를 공유하던 방식에서 **전문가마다 독립 amax** 로 바뀌었습니다. 대신 **0.47 이전 체크포인트와 호환되지 않아** PTQ 를 다시 돌려야 합니다.
- **NVFP4 활성값 캘리브레이션 `nvfp4_act_headroom`** — 캘리브레이션 중 본 최댓값에 스케일을 딱 맞추면 실전에서 더 큰 활성값이 들어올 때 포화됩니다. 분포의 낮은 백분위에 스케일을 고정해 여유(headroom)를 남기는 알고리즘입니다.
- **Recipe 체계로 이관** — AutoQuantize 의 `--auto_quantize_*` 플래그, 옛 `--qformat` 단축명들이 제거되고 `modelopt_recipes/` 의 YAML recipe 로 일원화됐습니다.
- **ONNX Autotune** — INT8/FP8 Q/DQ 를 넣었을 때 TensorRT 에서 기본 1.02배 이상 빨라지지 않으면 양자화하지 않은 모델을 저장합니다. "양자화했는데 오히려 느려지는" 경우를 걸러 내는 장치입니다.

---

## 6. 쓰기 전에 알아둘 제약

1. **아직 0.x, 호환성이 자주 깨진다.** README 의 Deprecation Policy 는 1.0 이전이라 **deprecate 후 1릴리스(약 1개월)** 만 유예하고 마이너 버전에서도 breaking change 가 있을 수 있다고 명시합니다. 0.47 한 번에도 제거 항목이 여럿이었습니다. 버전 고정이 필수입니다.
2. **하드웨어가 형식을 정한다.** NVFP4 는 Blackwell 세대에서 도입된 형식입니다([NVFP4 블로그](https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/)). 이전 세대 GPU 에서는 FP8·INT8·INT4 AWQ 쪽을 봐야 합니다. 어떤 모델이 어떤 형식을 지원하는지는 [support matrix](https://github.com/NVIDIA/Model-Optimizer/tree/main/examples/hf_ptq#support-matrix)에서 모델별로 다릅니다.
3. **서빙 엔진 쪽 지원이 따라와야 한다.** 예를 들어 0.47 의 FP8 Vision Encoder recipe 는 "양자화된 비전 인코더 Linear 를 지원하는 런타임"이 있어야 한다고 릴리스 노트가 명시합니다. ModelOpt 로 만들 수 있다고 모든 엔진에서 돌아가는 건 아닙니다.
4. **NVIDIA 생태계 중심.** 입력은 HF/PyTorch/ONNX 로 열려 있지만, 최적화 이득이 가장 크게 나오는 경로는 NVIDIA GPU + TensorRT-LLM/vLLM/SGLang 입니다.
5. **벤치마크는 대부분 벤더 발표.** 4절의 수치는 NVIDIA·고객사 발표이며, 다른 양자화 도구와의 **중립적 헤드투헤드 비교는 찾지 못했습니다.**

---

## 7. 덤: 에이전트 스킬 제공

README 에는 **Claude Code / Codex 용 플러그인**을 리포에서 바로 설치하는 방법이 있습니다.

```bash
claude plugin marketplace add https://github.com/NVIDIA/Model-Optimizer.git
claude plugin install modelopt@modelopt
```

라이브러리가 "코딩 에이전트가 쓸 스킬"까지 같이 배포하는 흐름이 요즘 오픈소스 리포의 새 관행이 되어 가는 모습입니다.

---

## 정리

- ModelOpt 는 **학습과 서빙 사이의 압축 공장**이다. 서빙은 TRT-LLM·vLLM·SGLang 이 한다.
- 중심은 **양자화**, 그중에서도 Blackwell 의 **NVFP4** 이고, 4비트의 정확도 손실을 **QAD**(증류)로 회복하는 쪽으로 무게가 옮겨 가고 있다.
- 몇 줄의 API(`mtq.quantize` → `export_hf_checkpoint`)로 쓸 수 있지만, **0.x 의 잦은 호환성 변경**과 **하드웨어·엔진 지원 매트릭스**를 먼저 확인해야 한다.

---

## References

1. NVIDIA, *Model-Optimizer* GitHub 리포지토리 README — <https://github.com/NVIDIA/Model-Optimizer>
2. NVIDIA, *Model Optimizer Documentation* — <https://nvidia.github.io/Model-Optimizer/>
3. NVIDIA, *ModelOpt 0.47.0 Release Notes* (2026-09-23) — <https://github.com/NVIDIA/Model-Optimizer/releases/tag/0.47.0>
4. NVIDIA, *Post-training quantization (PTQ) — examples/hf_ptq* — <https://github.com/NVIDIA/Model-Optimizer/tree/main/examples/hf_ptq>
5. E. Alvarez, *Introducing NVFP4 for Efficient and Accurate Low-Precision Inference*, NVIDIA Technical Blog (2025-06-24) — <https://developer.nvidia.com/blog/introducing-nvfp4-for-efficient-and-accurate-low-precision-inference/>
6. NVIDIA, *AutoQuantize: A Fast Automatic Mixed-Precision Assignment* — <https://nvidia.github.io/Model-Optimizer/announcements/autoquantize.html>
7. NVIDIA Technical Blog, *Developing Nemotron 3.5 Lightning NVFP4 with QAD Using NVIDIA Model Optimizer* — <https://developer.nvidia.com/blog/developing-nemotron-3-5-lightning-nvfp4-with-qad-using-nvidia-model-optimizer/>
8. NVIDIA Technical Blog, *Accelerate Generative AI Inference Performance with NVIDIA TensorRT Model Optimizer, Now Publicly Available* (2024-05) — <https://developer.nvidia.com/blog/accelerate-generative-ai-inference-performance-with-nvidia-tensorrt-model-optimizer-now-publicly-available/>
9. Bielik.AI, *NVIDIA GTC Bielik Minitron premiere* (고객 발표) — <https://bielik.ai/en/nvidia-gtc-bielik-minitron-premiere/>
10. Domyn, *Domyn Large: the journey of a European sovereign AI model* (고객 발표) — <https://www.domyn.com/blog/domyn-large-the-journey-of-a-european-sovereign-ai-model-for-regulated-industries>
