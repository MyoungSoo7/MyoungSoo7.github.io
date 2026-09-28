---
layout: post
title: "PyTorch 10년 — Lua Torch 에서 torch.compile·PyTorch 재단까지, 역사와 핵심 기능"
date: 2026-09-28 22:40:11 +0900
categories: [ai]
tags: [pytorch, deep-learning, autograd, torch-compile, pytorch-foundation]
---

PyTorch 는 지금 딥러닝 연구와 LLM 인프라의 사실상 공용어다. vLLM·DeepSpeed 같은 추론·학습 엔진도 그 위에 서 있다. 이 글은 **PyTorch 가 어떤 문제를 풀려고 나왔고, 판마다 무엇이 바뀌었는지**를 공식 블로그·GitHub 릴리스·논문만으로 정리한다. 날짜는 전부 GitHub 릴리스 기록이나 공식 블로그 게시일이다.

## 1. 연표 한눈에

| 시점 | 사건 | 출처 |
| --- | --- | --- |
| 2002 / 2011 | Torch(C++, Collobert·Bengio·Mariéthoz, IDIAP) → **Torch7**(Lua, Collobert·Kavukcuoglu·Farabet) | IDIAP-RR 02-46, [Torch7 논문](https://ronan.collobert.com/pub/2011_torch7_nipsw.pdf) |
| 2016 | Lua Torch 커뮤니티 사람들이 PyTorch 개발 시작 (Meta 중심, NVIDIA·Twitter 등 참여) | [PyTorch 재단 이전 공지](https://pytorch.org/blog/pytorchfoundation/) |
| 2017-01 | **공개 릴리스** (1주년 글이 2018-01-19) | [PyTorch, a year in](https://pytorch.org/blog/a-year-in/) |
| 2017-08 ~ 2018-04 | 0.2 → 0.3 → **0.4** (Variable 과 Tensor 통합) | [GitHub Releases](https://github.com/pytorch/pytorch/releases), [Road to 1.0](https://pytorch.org/blog/the-road-to-1_0/) |
| 2018-05-02 | **Caffe2 와 합친다**는 1.0 로드맵 발표, torch.jit 예고 | [The road to 1.0](https://pytorch.org/blog/the-road-to-1_0/) |
| 2018-12-07 | **1.0.0** 출시 | [v1.0.0](https://github.com/pytorch/pytorch/releases/tag/v1.0.0) |
| 2019-12 | 설계 논문 NeurIPS 2019 | [Paszke et al.](https://arxiv.org/abs/1912.01703) |
| 2022-09-12 | 리눅스 재단 산하 **PyTorch Foundation** 으로 이전 | [공지](https://pytorch.org/blog/pytorchfoundation/) |
| 2023-03-15 | **2.0** — torch.compile | [2.0 릴리스 블로그](https://pytorch.org/blog/pytorch-2.0-release/) |
| 2024-04 | torch.compile 설계 논문 ASPLOS 2024 | [Ansel et al.](https://doi.org/10.1145/3620665.3640366) |
| 2025-05-07 | 재단이 **우산 재단**으로 확장, vLLM·DeepSpeed 합류 | [보도자료](https://pytorch.org/blog/press-release-pytorch-foundation-expands-welcomes-projects-vllm-deepspeed/) |
| 2026-09-02 | 현재 최신 **2.14.0** | [v2.14.0](https://github.com/pytorch/pytorch/releases/tag/v2.14.0) |

2.x 이후로는 대체로 2~3개월마다 마이너 버전이 나왔다(2.10 2026-01-21, 2.11 03-23, 2.12 05-13, 2.13 07-08, 2.14 09-02 — GitHub 릴리스 기준).

## 2. 무슨 문제를 풀려고 나왔나 — "정의하면서 실행(define-by-run)"

2016년 무렵 주류였던 TensorFlow 1.x 와 Theano 는 **계산 그래프를 먼저 선언하고 나중에 돌리는** 방식이었다. 그래프가 고정돼 있어 최적화에는 유리했다. 하지만 조건문·반복문이 모델 안에 들어가거나 입력마다 구조가 바뀌면(가변 길이 RNN, 트리 구조 등) 그래프 전용 제어문을 따로 써야 했고, 디버거로 중간값을 들여다보기 어려웠다.

PyTorch 논문은 목표를 이렇게 정리한다. **"사용성을 최우선에 두되 성능을 크게 희생하지 않는다."** 모델은 그냥 파이썬 코드이고, 실행되는 순간 연산이 기록된다(define-by-run). 이 아이디어는 Chainer 가 먼저 보였고, PyTorch 논문도 Chainer·Torch 등 선행 연구를 계보로 밝힌다. ([Paszke et al., 2019](https://arxiv.org/abs/1912.01703))

그래서 **달라진 것**은 다음과 같다.

- if/for 가 그냥 파이썬 제어문이다. 입력마다 모델 구조가 달라도 된다.
- pdb·print 로 텐서를 바로 본다. 에러가 난 줄이 곧 문제의 줄이다.
- 1주년 글에 따르면 공개 직후 며칠 만에 커뮤니티가 논문 구현을 PyTorch 로 올리기 시작했다(CycleGAN·OpenNMT·AllenNLP·Pyro 등). ([a year in](https://pytorch.org/blog/a-year-in/))

**새로 생긴 비용**도 있다. 파이썬 인터프리터가 연산 하나하나를 디스패치하므로 작은 연산이 많은 모델에서는 오버헤드가 크다. 그래프가 없으니 연산을 합치는 커널 융합 같은 전역 최적화를 하기도 어렵다. 이후의 역사는 이 비용을 줄이는 과정이다.

## 3. 핵심 기능 — 무엇이 PyTorch 를 이루나

### 3.1 Tensor 와 디스패처

numpy 와 비슷한 n차원 배열인데 **장치(CPU·CUDA·MPS·XPU 등)와 자료형**을 가진다. 연산 호출은 내부 디스패처가 장치·dtype·autograd 여부 같은 키를 보고 해당 커널로 보낸다. 새 하드웨어 백엔드가 이 디스패처에 커널을 등록하는 방식으로 붙는다. 2.14 에는 Apple Silicon 선형대수(SVD·eigh·QR·Cholesky) 네이티브 커널과 Intel XPU 그래프 캡처가 들어갔다. ([v2.14.0 릴리스 노트](https://github.com/pytorch/pytorch/releases/tag/v2.14.0))

### 3.2 autograd — 역방향 자동미분

forward 를 실행하면 각 연산이 그래디언트 함수를 테이프처럼 연결해 두고, `loss.backward()` 가 그 그래프를 거꾸로 훑는다. 그래프는 매 반복마다 새로 만들어지고 버려진다. 논문은 이를 **테이프 기반 역방향 모드 자동미분**으로 설명한다. ([Paszke et al.](https://arxiv.org/abs/1912.01703))

```python
import torch
x = torch.randn(3, requires_grad=True)
y = (x ** 2).sum() if x.sum() > 0 else x.abs().sum()   # 파이썬 조건문 그대로
y.backward()
print(x.grad)
```

0.4 에서 옛 `Variable` 래퍼가 Tensor 로 통합되면서 이 코드처럼 텐서에 바로 `requires_grad` 를 붙이는 형태가 됐다. ([Road to 1.0](https://pytorch.org/blog/the-road-to-1_0/))

### 3.3 nn.Module · optim · DataLoader

- `nn.Module`: 파라미터와 하위 모듈을 담는 파이썬 클래스. `forward` 만 쓰면 된다.
- `torch.optim`: SGD·Adam 등. 모듈의 `parameters()` 를 받아 갱신한다.
- `torch.utils.data`: Dataset/DataLoader 로 멀티프로세스 로딩.

이 세 가지가 "파이썬 클래스 하나 = 모델" 이라는 PyTorch 특유의 코드 모양을 만든다.

### 3.4 1.0 의 과제 — 연구에서 프로덕션으로 (torch.jit)

1.0 로드맵 글은 약점을 솔직하게 적었다. **프로덕션 지원**이 부족했다. C++ 전용 런타임으로 내보내기, 모바일 최적화, 커널 융합, 8비트 양자화 추론 같은 것들이다. 한편 Facebook 에는 이미 Caffe2 가 데이터센터와 10억 대 넘는 휴대폰에서 돌고 있었다. 그래서 둘을 합치고, 파이썬 모델을 파이썬 없는 환경으로 내보내는 `torch.jit`(TorchScript)을 **옵트인**으로 도입했다. ([The road to 1.0](https://pytorch.org/blog/the-road-to-1_0/))

TorchScript 는 파이썬의 부분집합만 이해했다. 그래서 실제로는 "모델을 TorchScript 가 받아주는 형태로 고쳐 쓰는" 비용이 생겼다. 2.x 에서는 이 경로를 `torch.compile`·`torch.export` 가 대신한다.

### 3.5 2.0 — torch.compile: eager 를 그대로 두고 컴파일러를 밑에 깐다

2.0 의 핵심은 **API 는 그대로 두고 내부를 컴파일러로 바꾼 것**이다. 공식 블로그 표현으로 `torch.compile` 은 "완전히 추가적(additive)이고 선택적인" 기능이라 2.0 은 정의상 100% 하위호환이다. ([2.0 릴리스](https://pytorch.org/blog/pytorch-2.0-release/))

```python
model = MyModel().cuda()
model = torch.compile(model)   # 한 줄 추가
```

밑에서 도는 구성요소는 다음과 같다. ([Ansel et al., ASPLOS 2024](https://doi.org/10.1145/3620665.3640366))

- **TorchDynamo**: 파이썬 바이트코드 실행을 가로채 PyTorch 연산 구간을 FX 그래프로 떼어낸다. 처리 못 하는 코드를 만나면 거기서 그래프를 끊고(graph break) 원래 파이썬으로 돌려서 **정확성을 유지**한다. TorchScript 와 결정적으로 다른 점이다.
- **AOTAutograd**: backward 그래프까지 미리 만들어 forward 와 함께 최적화한다.
- **TorchInductor**: 그래프를 받아 GPU 에서는 **OpenAI Triton**, CPU 에서는 C++/OpenMP 코드를 생성한다.

2.x 이후에도 이 축이 계속 넓어졌다. 2.14 에서는 Inductor 가 Triton·ATen 과 함께 CUTLASS 커널(NVGEMM)을 오토튜닝 후보로 쓴다. `torch.cond` 를 다방향 분기로 일반화한 `torch.switch` 가 들어왔고, `@dynamic_spec` 으로 동적 shape 을 선언적으로 지정하게 됐다. 복소수 텐서 컴파일도 실험적으로 지원한다. ([v2.14.0 릴리스 노트](https://github.com/pytorch/pytorch/releases/tag/v2.14.0))

**새로 생긴 비용**: 첫 호출의 컴파일 시간, graph break·재컴파일 원인 추적, 컴파일된 코드의 디버깅 난이도. "한 줄이면 빨라진다" 는 말은 벤치마크에 따라 맞기도 하고 틀리기도 한다. 속도 향상 수치는 공식 자료도 모델 세트와 하드웨어에 따라 다르게 보고하므로, 이 글에서는 숫자를 옮기지 않는다.

### 3.6 분산 학습

`torch.distributed`(c10d)가 NCCL·Gloo 등 통신 백엔드 위에서 DDP, FSDP, DTensor 기반 텐서 병렬을 제공한다. 2.0 에서 DTensor·TensorParallel 이 프로토타입으로 들어왔다. ([2.0 릴리스](https://pytorch.org/blog/pytorch-2.0-release/)) 2.14 는 결함 허용을 c10d 의 일급 개념으로 올렸다. 프로세스 그룹을 제자리에서 재구성하고, 일방향 RMA 윈도우를 쓰고, 백엔드 무관 Flight Recorder 로 추적한다. torchcomms 에서 이식한 새 NCCL 백엔드도 프리뷰로 들어갔다. ([v2.14.0](https://github.com/pytorch/pytorch/releases/tag/v2.14.0))

## 4. 거버넌스 — 회사 프로젝트에서 재단으로

2022-09-12, PyTorch 는 리눅스 재단 최상위 프로젝트인 **PyTorch Foundation** 으로 옮겼다. 설립 당시 이사회는 AMD·AWS·Google Cloud·Meta·Microsoft Azure·NVIDIA 로 구성됐다. **비즈니스 결정은 재단이, 기술 결정은 개별 메인테이너가** 내리는 구조다. ([공지](https://pytorch.org/blog/pytorchfoundation/))

2025-05-07 에는 재단이 **우산 재단**으로 확장해 PyTorch 코어 외의 프로젝트도 직접 호스팅하기 시작했다. 첫 호스팅 프로젝트가 **vLLM**(추론)과 **DeepSpeed**(분산 학습)다. 발표 시점 기준 회원사 30곳 이상, 생태계 프로젝트 120개다. ([보도자료](https://pytorch.org/blog/press-release-pytorch-foundation-expands-welcomes-projects-vllm-deepspeed/))

"PyTorch" 가 라이브러리 하나가 아니라 **학습 → 컴파일 → 서빙까지 이어지는 스택의 중심**이 됐다는 뜻이다.

## 5. 정리

| 문제 | PyTorch 의 답 | 남은 비용 |
| --- | --- | --- |
| 정적 그래프는 쓰고 디버깅하기 어렵다 | define-by-run, 파이썬이 곧 모델 (2017) | 파이썬 오버헤드, 전역 최적화 불가 |
| 연구 코드를 프로덕션에 못 올린다 | Caffe2 통합 + TorchScript (1.0, 2018) | 파이썬 부분집합에 맞춰 코드를 고쳐야 함 |
| eager 는 느리다 | torch.compile — Dynamo/Inductor/Triton (2.0, 2023) | 컴파일 시간, graph break 추적 |
| 한 회사 프로젝트라는 리스크 | 리눅스 재단 이전(2022) → 우산 재단(2025) | 이해관계자가 많아진 만큼의 조율 |

PyTorch 10년의 흐름은 한 문장으로 줄일 수 있다. **"사용성은 절대 내주지 않고, 성능은 밑에서 따라잡는다."** 1.0 로드맵이 "사용성과 절대 맞바꾸지 않는다" 를 설계 제약으로 적었고, 2.0 은 그 제약을 지킨 채 컴파일러를 넣었다.

## References

1. R. Collobert, S. Bengio, J. Mariéthoz, "Torch: a modular machine learning software library," IDIAP Research Report 02-46, 2002.
1. R. Collobert, K. Kavukcuoglu, C. Farabet, "Torch7: A Matlab-like Environment for Machine Learning," BigLearn, NIPS Workshop, 2011. <https://ronan.collobert.com/pub/2011_torch7_nipsw.pdf>
2. A. Paszke et al., "PyTorch: An Imperative Style, High-Performance Deep Learning Library," NeurIPS 2019. <https://arxiv.org/abs/1912.01703>
3. J. Ansel et al., "PyTorch 2: Faster Machine Learning Through Dynamic Python Bytecode Transformation and Graph Compilation," ASPLOS 2024. <https://doi.org/10.1145/3620665.3640366>
4. S. Tokui et al., "Chainer: a Next-Generation Open Source Framework for Deep Learning," LearningSys, NIPS Workshop, 2015.
5. PyTorch Blog, "PyTorch, a year in…," 2018-01-19. <https://pytorch.org/blog/a-year-in/>
6. PyTorch Blog, "The road to 1.0: production ready PyTorch," 2018-05-02. <https://pytorch.org/blog/the-road-to-1_0/>
7. PyTorch Blog, "PyTorch strengthens its governance by joining the Linux Foundation," 2022-09-12. <https://pytorch.org/blog/pytorchfoundation/>
8. PyTorch Blog, "PyTorch 2.0: Our next generation release…," 2023-03-15. <https://pytorch.org/blog/pytorch-2.0-release/>
9. PyTorch Foundation, "PyTorch Foundation Expands to Umbrella Foundation and Welcomes vLLM and DeepSpeed Projects," 2025-05-07. <https://pytorch.org/blog/press-release-pytorch-foundation-expands-welcomes-projects-vllm-deepspeed/>
10. pytorch/pytorch GitHub Releases (v0.2.0 ~ v2.14.0 게시일, v2.14.0 릴리스 노트). <https://github.com/pytorch/pytorch/releases>
