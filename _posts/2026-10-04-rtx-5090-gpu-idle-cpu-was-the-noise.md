---
layout: post
title: "5090 이 아니라 CPU 가 울고 있었다 — VRAM 은 찼는데 GPU 사용률 0% 인 AI 장비 한 장"
date: 2026-10-04 20:32:46 +0900
categories: [AI, Infrastructure]
tags: [GPU, RTX5090, LocalLLM, Ollama, llama.cpp, nvidia-smi, StreamDeck]
---

링크드인에서 **Chris Han** 이 자기 AI 작업 장비 사진 한 장을 올렸다. 공개한 정보는 두 가지다. GPU 는 **RTX 5090** 이고, 장비 소음이 커서 "일 잘 되고 있나" 싶어 봤더니 **소리를 낸 건 GPU 가 아니라 CPU 였다.** CPU 모델은 밝히지 않았다.

그 순간이 책상 위 스트림덱에 그대로 찍혀 있다.

![스트림덱 15키에 띄운 시스템 모니터 — 윗줄 CPU 93% · 80°C, GPU 0% · 8W · 31°C, VRAM 40% · 12.9/31.8GB, RAM 70% · 121.2GB. 둘째·셋째 줄은 날씨, 마이크 음소거, 캡처, 잠금, 오디오, 볼륨, 모니터, 블루투스 버튼](/assets/images/ai-rig/stream-deck-rtx5090-cpu93-gpu0.jpg)

*사진: Chris Han (LinkedIn 공개 게시물). 본인이 밝힌 사실(5090, CPU 소음)과 화면에 찍힌 숫자만 쓰고, 나머지는 추정이라고 표시했다.*

## 1. 화면에 찍힌 숫자

윗줄 다섯 칸이 모니터링 위젯이다. 읽히는 대로 옮기면 이렇다.

| 칸 | 표시 | 읽을 수 있는 것 |
| --- | --- | --- |
| CPU | **93%** · 80°C (전력은 `NO PWR`, 측정 안 됨) | 거의 꽉 차서 돌고 있다 |
| GPU | **0%** · 8W · 31°C | 놀고 있다 |
| VRAM | **40%** · 12.9 / 31.8 GB | 그런데 메모리는 차 있다 |
| RAM | **70%** · 앞자리 잘림 / 121.2 GB | 시스템 메모리도 꽤 쓰고 있다 |

VRAM 전체 31.8GB 는 [RTX 5090 공식 사양](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/)의 **32 GB GDDR7** 과 맞는다. 같은 사양표에서 이 카드의 Total Graphics Power 는 **575W** 다. 화면의 8W 는 그 1.4% 다. 일하는 카드의 전력이 아니다.

RAM 칸은 사용량 앞자리가 잘려 있어서 정확한 값을 옮길 수 없다. 70% × 121.2GB 로 계산하면 약 85GB 지만, 이건 **화면 값이 아니라 내 계산**이다.

## 2. "VRAM 이 찼다" 와 "GPU 가 일한다" 는 다른 말이다

이 사진에서 제일 헷갈리기 쉬운 칸이 VRAM 40% 다. 메모리가 12.9GB 차 있으니 GPU 가 뭔가 하고 있다고 읽기 쉽다.

GPU 사용률이 무엇을 재는지 보면 그렇지 않다는 걸 알 수 있다. `nvidia-smi` 와 대부분의 모니터링 도구가 읽는 NVML 은 GPU 사용률을 이렇게 정의한다.

> Percent of time over the past sample period during which one or more kernels was executing on the GPU.
> — [NVIDIA NVML API Reference, `nvmlUtilization_t`](https://docs.nvidia.com/deploy/nvml-api/structnvmlUtilization__t.html)

즉 GPU 사용률은 **커널이 실행되고 있던 시간의 비율**이다. 메모리에 무엇이 올라가 있는지는 이 숫자와 상관이 없다. 모델 가중치를 VRAM 에 올려 둔 채 CPU 쪽 일을 기다리고 있으면 **VRAM 40%, GPU 0%** 가 정확히 이렇게 찍힌다.

## 3. 왜 이런 모양이 나오나 — 흔한 원인 세 가지

사진 한 장으로 원인을 확정할 수는 없다. 그 시점에 어떤 프로그램이 돌았는지 모르기 때문이다. 다만 "GPU 는 놀고 CPU 는 꽉 찬" 모양을 만드는 흔한 경우는 정해져 있다.

**① 모델 일부가 CPU 에 있다 (부분 오프로드).** 로컬 LLM 런타임은 모델이 VRAM 에 다 안 들어가면 남은 층을 시스템 메모리에 두고 CPU 로 돌린다.
- Ollama 는 `ollama ps` 의 `PROCESSOR` 열에 이걸 그대로 보여준다. [공식 FAQ](https://docs.ollama.com/faq) 의 설명대로 `100% GPU`, `100% CPU`, 그리고 `48%/52% CPU/GPU` 처럼 나뉜 상태가 있다.
- llama.cpp 는 `--n-gpu-layers` 로 VRAM 에 둘 층 수를 정하고, `--cpu-moe` / `--n-cpu-moe` 로 MoE 전문가 가중치를 CPU 에 남길 수 있다([server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)).
- 이렇게 나뉘면 토큰 하나를 만들 때마다 CPU 쪽 층이 끝나야 다음으로 넘어간다. 느린 쪽이 전체 속도를 정하고, 빠른 쪽인 GPU 는 그동안 기다린다.
- RAM 을 많이 쓰고 VRAM 도 일부 찬 이 화면은 이 경우와 **모양이 맞는다.** 맞는다는 것이지, 그랬다는 증거는 아니다.

**② 데이터를 CPU 가 준비하느라 GPU 가 기다린다.** 학습이나 일괄 추론에서 흔하다. PyTorch `DataLoader` 의 기본값은 `num_workers=0` 이고, [PyTorch 성능 튜닝 가이드](https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html)는 이 경우 *"the main training process has to wait for the data to be available"* 라고 적는다. 디코딩·토크나이징·증강이 CPU 에서 막히면 GPU 사용률이 바닥에 붙는다.

**③ 애초에 GPU 일이 아니다.** 빌드·압축·인덱싱·임베딩 전처리처럼 CPU 만 쓰는 작업이 그 순간 돌고 있었을 수도 있다. 모델은 VRAM 에 올려 둔 채로 말이다. 이 경우엔 고칠 것도 없다.

## 4. 소리로 판단하지 말고 숫자로

이 사진의 진짜 요점은 원인이 아니라 **확인한 방법**이다. 5090 을 들인 장비에서 팬 소리가 크면 누구든 "GPU 가 일하는구나" 라고 생각한다. 이 경우 실제로 돌던 건 80°C 의 CPU 였다.

GPU 가 정말 일할 때는 숫자가 다르게 나온다. 사용률은 위로 붙고, 전력은 수백 와트대로 올라가고, 온도도 따라 오른다. 8W·31°C 인 카드에서는 소리가 날 이유가 없다.

같은 판단을 터미널에서 하려면 이 정도면 된다.

```bash
# 1초마다 GPU 사용률·전력·온도·메모리를 같이 본다
nvidia-smi --query-gpu=utilization.gpu,power.draw,temperature.gpu,memory.used --format=csv -l 1

# Ollama 라면: 모델이 GPU 에 다 올라갔는지
ollama ps          # PROCESSOR 열이 100% GPU 인지 확인
```

`utilization.gpu` 가 0 근처인데 `memory.used` 만 크면, 그건 "일하는 GPU" 가 아니라 **"짐을 맡아 둔 GPU"** 다.

스트림덱 위젯이 한 일이 바로 이거다. 비싼 장비일수록 "돌고 있겠지" 라고 믿기 쉬운데, 눈앞에 숫자 다섯 개를 상시로 띄워 두니 그 믿음을 한 번에 깰 수 있었다.

## 5. 지난번과 같은 교훈

지난달 [「GPU Environments 인데 CPU 가 떠 있다」](https://myoungsoo7.github.io/2026/09/20/brev-gpu-environments-but-a-cpu-is-running/)에서 클라우드 콘솔 한 화면을 두고 비슷한 얘기를 했다. 이름에 GPU 가 붙어 있어도 실제로 돌고 있는 건 CPU 였다.

이번에는 책상 위에서 똑같은 일이 일어났다. 둘 다 결론은 같다. **"GPU 가 있다" 와 "GPU 가 일한다" 는 따로 확인해야 한다.**

## 마무리

- RTX 5090(32GB, 575W) 장비에서 소음의 주인은 CPU 였다(Chris Han 공개 내용). 화면에는 CPU 93%·80°C, GPU 0%·8W 가 찍혀 있다.
- GPU 사용률은 **커널 실행 시간 비율**이라, VRAM 이 차 있어도 0% 일 수 있다.
- 흔한 원인은 부분 오프로드, CPU 쪽 데이터 준비 병목, 그리고 애초에 GPU 일이 아닌 작업이다. 이 사진만으로는 셋 중 무엇인지 알 수 없다.
- 확인은 소리가 아니라 `utilization` · `power` · `ollama ps` 로 한다.

## References

1. NVIDIA, *GeForce RTX 5090 Graphics Cards — Specs* (32 GB GDDR7, Total Graphics Power 575W). <https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/>
2. NVIDIA, *NVML API Reference Guide — `nvmlUtilization_t`* (GPU 사용률 정의). <https://docs.nvidia.com/deploy/nvml-api/structnvmlUtilization__t.html>
3. Ollama, *FAQ — How can I tell if my model was loaded onto the GPU?* <https://docs.ollama.com/faq>
4. ggml-org, *llama.cpp server README* (`--n-gpu-layers`, `--cpu-moe`, `--n-cpu-moe`). <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
5. Szymon Migacz, *PyTorch Performance Tuning Guide* (DataLoader `num_workers`). <https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html>
6. 사진 및 장비 정보: Chris Han, LinkedIn 공개 게시물 (2026-10).
