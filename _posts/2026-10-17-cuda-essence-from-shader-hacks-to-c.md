---
layout: post
title: "CUDA 의 본질 — 셰이더를 속이던 시대에서 '스레드 하나짜리 C 함수'로"
date: 2026-10-17 18:07:55 +0900
categories: [gpu]
tags: [cuda, gpu, gpgpu, brook, cudnn, triton, hip, essence]
---

CUDA 를 "엔비디아 GPU 로 병렬 계산하는 API" 라고만 설명하면 왜 이게 20년 가까이 해자(moat)가 됐는지 설명이 안 된다.
이 글은 CUDA 의 **기능**을 나열하지 않는다. 대신 두 가지 축으로 본다.

1. **등장 이유** — CUDA 이전에 GPU 로 계산하려면 무엇을 견뎌야 했나.
2. **등장 전후 델타** — CUDA 가 나온 뒤 실제로(검증 가능하게) 무엇이 바뀌었나.

SIMT·코얼레싱·점유율·루프라인 같은 하드웨어 이야기는 [GPU 구조 글]({% post_url 2026-10-10-cs300-099-gpu-architecture %})에 따로 정리해 두었다.

---

## 1. CUDA 이전: GPU 에게 "이건 그림이야" 라고 속여야 했다

2000년대 초 GPU 는 프로그래머블 셰이더를 갖추면서 부동소수점 연산량이 커졌다. 문제는 그 연산 장치에 닿는 **유일한 문**이 그래픽스 API(OpenGL·Direct3D) 였다는 점이다.
Owens 등의 GPGPU 서베이([Owens et al., 2007](https://doi.org/10.1111/j.1467-8659.2007.01012.x))가 정리한 당시 관행은 이렇다.

- **배열 = 텍스처.** 입력 데이터를 텍스처 이미지로 올린다.
- **루프 = 화면 크기만 한 사각형 그리기.** 사각형을 래스터화하면 픽셀마다 프래그먼트 셰이더가 한 번씩 돈다. 이게 곧 "원소마다 한 번씩 실행" 이다.
- **결과 저장 = 렌더 투 텍스처.** 출력 픽셀을 텍스처에 그리고, 다음 단계에서 그걸 다시 입력 텍스처로 읽는다.

계산 하나를 하려면 그래픽스 파이프라인 전체를 의인화해야 했다. 프로그래머는 수치 해석가이면서 동시에 셰이더 언어(Cg·HLSL·GLSL)와 그래픽스 상태 머신 전문가여야 했다.
게다가 프래그먼트 셰이더는 **자기 픽셀 하나만 쓸 수 있다** — 임의 주소에 쓰기(scatter)가 자연스럽지 않고, 이웃 스레드와 값을 주고받을 공유 메모리도 없었다.

### 중간 단계: Brook — "언어는 C 로, 번역은 컴파일러가"

스탠퍼드의 Ian Buck 등은 이 번역 작업을 컴파일러에 넘기는 시도를 했다. [Brook for GPUs (SIGGRAPH 2004)](https://dl.acm.org/doi/10.1145/1015706.1015800) 는 C 에 *스트림*과 *커널*을 더한 언어였고, 컴파일러가 이를 Cg/HLSL 셰이더로 바꿔 그래픽스 API 위에서 돌렸다. 저자들은 일부 응용에서 CPU 대비 최대 7배 빠르다고 보고했다(저자 자체 측정).

Brook 은 "그래픽스를 몰라도 된다" 는 방향을 증명했지만, 바닥은 여전히 그래픽스 API 였다. 텍스처 크기 제약, 셰이더 모델의 쓰기 제약이 그대로 언어의 제약이 됐다.
그리고 Brook 의 제1저자 Ian Buck 은 4년 뒤 CUDA 를 소개한 논문([Nickolls, Buck, Garland, Skadron, 2008](https://queue.acm.org/detail.cfm?id=1365500))에 엔비디아 소속 공저자로 다시 등장한다.

**정리하면 CUDA 이전의 문제는 성능이 아니라 '접근 경로'였다.** 연산기는 이미 거기 있었는데, 거기 가는 길이 그래픽스로만 나 있었다.

---

## 2. CUDA 의 답: 왜 하필 그런 모양인가

엔비디아는 2007년 CUDA 를 공개했다([Nickolls et al., 2008](https://queue.acm.org/detail.cfm?id=1365500)). 핵심은 그래픽스 API 를 우회하는 게 아니라 **아예 거치지 않는** 것이다. 하드웨어(Tesla 아키텍처) 자체가 그래픽스와 계산을 통합한 구조로 바뀌었고, 그 위에 C 를 최소한으로 확장한 언어가 올라갔다.

같은 논문은 CUDA 가 주는 추상화를 정확히 **세 개**로 요약한다.

> "a hierarchy of thread groups, shared memories, and barrier synchronization"

이 셋이 각각 1장의 어떤 고통을 없앴는지 대응시키면 CUDA 의 모양이 왜 그런지 보인다.

| CUDA 이전의 고통 | CUDA 의 추상화 | 효과 |
| --- | --- | --- |
| 계산을 "사각형 그리기" 로 위장 | **grid → block → thread 계층** | 원소마다 한 번 = 스레드 하나. 그래픽스 개념이 사라짐 |
| 이웃 픽셀과 값을 나눌 방법 없음 | **블록 단위 shared memory** | 블록 안 스레드가 온칩 메모리로 협력 |
| 단계 사이 동기화 = 렌더 패스 분리 | **`__syncthreads()` 배리어** | 커널 안에서 단계를 나눌 수 있음 |

### 커널은 "스레드 하나짜리 C 함수" 다

논문의 SAXPY(`y ← a·x + y`) 예시가 이 설계를 가장 잘 보여준다.

```c
// 직렬 버전
void saxpy_serial(int n, float a, float *x, float *y) {
    for (int i = 0; i < n; ++i)
        y[i] = a * x[i] + y[i];
}

// CUDA 버전 — 루프 한 바퀴가 스레드 하나가 된다
__global__ void saxpy_parallel(int n, float a, float *x, float *y) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) y[i] = a * x[i] + y[i];
}

int nblocks = (n + 255) / 256;
saxpy_parallel<<<nblocks, 256>>>(n, 2.0, x, y);
```

저자들의 표현으로는 "커널의 텍스트는 그저 순차 스레드 하나를 위한 C 함수" 다. 프로그래머는 *한 원소에 대한 일*만 쓰고, 몇 개를 띄울지는 실행 구성(`<<<블록 수, 블록당 스레드>>>`)으로 따로 말한다. 각 반복이 독립인 루프는 기계적으로 커널이 된다.

### 진짜 핵심: "블록은 서로 독립이어야 한다"

CUDA 의 가장 중요한 결정은 기능이 아니라 **제약**이다. 같은 논문은 이렇게 쓴다.

> 블록은 어떤 순서로든, 병렬로든 직렬로든 실행될 수 있어야 한다. 서로 다른 블록은 직접 통신할 수단이 없다.

이 제약 덕분에 같은 컴파일된 프로그램이 코어 수가 다른 GPU 어디서든 돈다 — 저자들 표현으로 "물리 프로세서 수는 런타임 시스템만 알면 된다." 블록 수는 데이터 크기가 정하고, 그 블록들을 몇 개의 SM 에 어떻게 뿌릴지는 하드웨어 스케줄러가 정한다.
GPU 세대가 바뀌어 코어가 늘어나도 코드를 다시 쓸 필요가 없다는 것, 이게 2008년 논문 제목의 "Scalable" 이 뜻하는 바다.

같은 이유로 포기한 것도 명시돼 있다(2008년 논문 기준): 커널 안에서 새 스레드 생성 불가, 재귀 불가, 블록 간 통신은 전역 메모리 원자 연산이나 커널 재실행으로만. 즉 **표현력 일부를 내주고 확장성과 단순한 스케줄러를 샀다.** (이후 버전에서 일부 제약은 풀렸다 — 현재 사양은 [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/) 참조.)

---

## 3. 등장 전후 델타: 무엇이 검증 가능하게 바뀌었나

### 델타 ① — "GPU 로 계산한다" 의 진입 비용이 그래픽스 지식에서 C 지식으로

이게 가장 직접적인 변화다. 1장의 텍스처·렌더 투 텍스처 절차가 `cudaMalloc` / `cudaMemcpy` / 커널 호출로 바뀌었다(위 논문의 런타임 API 설명). 논문은 2008년 시점에 이미 계산화학, 희소 행렬 솔버, 정렬, 탐색, 물리 모델 등에서 응용이 나왔다고 기록한다.

### 델타 ② — 딥러닝이 GPU 위에서 '발견' 됐다

2012년 AlexNet 논문([Krizhevsky, Sutskever, Hinton, NIPS 2012](https://papers.nips.cc/paper_files/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html))은 초록에서부터 "매우 효율적인 GPU 구현" 을 성과 요인으로 꼽는다. 본문에는 네트워크가 한 GPU 메모리에 다 안 들어가서 **GTX 580 3GB 두 장에 나눠 올렸고, 학습에 5~6일 걸렸다**고 적혀 있다. 그리고 "더 빠른 GPU 와 더 큰 데이터셋을 기다리기만 해도 결과가 좋아질 것" 이라고 덧붙인다.

여기서 중요한 건 이 GPU 들이 *게이밍 카드*였다는 점이다. CUDA 가 소비자용 그래픽카드까지 같은 프로그래밍 모델로 열어 두지 않았다면, 대학 연구실이 이 실험을 할 수 있었을지 의문이다. (단, "CUDA 가 없었으면 딥러닝이 없었다" 같은 반사실 주장은 검증할 수 없으므로 하지 않는다.)

### 델타 ③ — 해자는 언어가 아니라 라이브러리로 옮겨갔다

2014년 엔비디아 연구진이 낸 [cuDNN 논문 (Chetlur et al., arXiv:1410.0759)](https://arxiv.org/abs/1410.0759) 의 문제 정의가 흥미롭다.

> 딥러닝 커널 최적화는 어렵고, 병렬 아키텍처가 바뀔 때마다 다시 최적화해야 한다. HPC 에는 BLAS 가 있었지만 딥러닝에는 그런 라이브러리가 없다.

즉 CUDA 가 *쓰기 쉬움*을 해결하자, 다음 병목은 *빠르게 쓰기*가 됐다. 엔비디아는 그 답을 cuBLAS·cuDNN 같은 라이브러리로 냈고, 프레임워크들이 그 위에 올라탔다. 논문은 Caffe 에 cuDNN 을 붙였을 때 표준 모델에서 36% 빨라졌다고 보고한다 — **벤더(엔비디아) 저자의 자체 측정**이다.

이 시점부터 경쟁의 단위가 바뀐다. 다른 회사가 CUDA 와 비슷한 *언어*를 만드는 건 어렵지 않다. 어려운 건 세대마다 다시 튜닝된 *라이브러리 커널 묶음*과 그 위에 이미 쌓인 프레임워크다.

### 델타 ④ — 대안들이 오히려 CUDA 의 모양을 증명한다

- **AMD HIP.** AMD 문서는 HIP 를 "AMD GPU 를 위한 C++ 런타임 API 이자 커널 언어" 라고 설명하고([What is HIP?](https://rocm.docs.amd.com/projects/HIP/en/latest/what_is_hip.html)), CUDA 코드를 HIP 로 옮기는 변환 도구 [HIPIFY](https://rocm.docs.amd.com/projects/HIPIFY/en/latest/) 를 함께 제공한다. hipBLAS·hipFFT 처럼 이름부터 CUDA 라이브러리에 대응한다. 경쟁자가 *다른 모델*이 아니라 *CUDA 와 대응되는 모델*을 택했다는 사실 자체가, grid/block/thread 추상화가 업계 표준 어휘가 됐다는 증거다.
- **Triton.** [Tillet, Kung, Cox (MAPL 2019)](https://www.eecs.harvard.edu/~htk/publication/2019-mapl-tillet-kung-cox.pdf) 의 동기는 정확히 델타 ③ 의 반대편에 있다 — "cuBLAS·cuDNN 같은 벤더 라이브러리를 활용할 수 없는 연산은, 전문가가 직접 구현하지 않는 한 장치 활용률이 낮을 위험이 있다." Triton 은 스레드가 아니라 **타일**(정적 모양의 다차원 부분 배열)을 프로그래밍 단위로 올려, 스레드·공유 메모리 배치를 컴파일러에 맡긴다. 저자들은 행렬곱·합성곱에서 벤더 라이브러리와 대등한 성능을 보였다고 보고한다(저자 자체 측정).

Triton 의 등장은 CUDA 의 본질을 거꾸로 비춘다. CUDA 는 그래픽스 API 라는 *잘못된 추상화*를 걷어내고 스레드를 프로그래머에게 줬다. 20년이 지나자 이번엔 그 스레드 수준이 너무 낮다는 불만이 생겼고, 한 단계 위(타일)를 노리는 도구가 나왔다. **추상화의 위치가 한 칸 올라간 것이지, CUDA 가 해결한 문제가 되돌아간 건 아니다.**

> ⚠️ 근거의 한계: CUDA·HIP·Triton 의 성능을 같은 하드웨어·같은 워크로드로 비교한 **중립 제3자 헤드투헤드 자료는 이 글에서 인용하지 않았다**. 위 성능 수치는 모두 각 논문 저자의 자체 보고이며, 이 글은 우열을 주장하지 않는다.

---

## 요약

| 축 | CUDA 이전 | CUDA 이후 |
| --- | --- | --- |
| 계산 단위 | 픽셀(프래그먼트) | 스레드 — "스레드 하나짜리 C 함수" |
| 데이터 | 텍스처 | `cudaMalloc` 으로 잡은 메모리 |
| 협력 | 불가(자기 픽셀만 씀) | 블록 공유 메모리 + 배리어 |
| 확장 | 그래픽스 드라이버 재량 | 블록 독립성 → 코어 수와 무관하게 실행 |
| 경쟁 지점 | 누가 셰이더 트릭을 아나 | 누가 라이브러리 커널 생태계를 가졌나 |

CUDA 의 본질은 "GPU 로 계산하는 API" 가 아니다. **이미 있던 연산기에 그래픽스를 거치지 않는 문을 내고, 그 문의 모양(블록 독립성)으로 하드웨어 세대 교체를 프로그래머에게서 숨긴 것** — 그리고 그 결과 경쟁이 언어에서 라이브러리로 옮겨간 것이다.

---

## References

1. J. Nickolls, I. Buck, M. Garland, K. Skadron. "Scalable Parallel Programming with CUDA." *ACM Queue* 6(2), 2008. <https://queue.acm.org/detail.cfm?id=1365500>
2. I. Buck, T. Foley, D. Horn, J. Sugerman, K. Fatahalian, M. Houston, P. Hanrahan. "Brook for GPUs: Stream Computing on Graphics Hardware." *ACM Transactions on Graphics* 23(3):777–786, SIGGRAPH 2004. <https://dl.acm.org/doi/10.1145/1015706.1015800>
3. J. D. Owens, D. Luebke, N. Govindaraju, M. Harris, J. Krüger, A. E. Lefohn, T. J. Purcell. "A Survey of General-Purpose Computation on Graphics Hardware." *Computer Graphics Forum* 26(1):80–113, 2007. <https://doi.org/10.1111/j.1467-8659.2007.01012.x>
4. A. Krizhevsky, I. Sutskever, G. E. Hinton. "ImageNet Classification with Deep Convolutional Neural Networks." *NIPS 2012*. <https://papers.nips.cc/paper_files/paper/2012/hash/c399862d3b9d6b76c8436e924a68c45b-Abstract.html>
5. S. Chetlur, C. Woolley, P. Vandermersch, J. Cohen, J. Tran, B. Catanzaro, E. Shelhamer. "cuDNN: Efficient Primitives for Deep Learning." arXiv:1410.0759, 2014. <https://arxiv.org/abs/1410.0759>
6. P. Tillet, H. T. Kung, D. Cox. "Triton: An Intermediate Language and Compiler for Tiled Neural Network Computations." *MAPL '19*, 2019. <https://doi.org/10.1145/3315508.3329973>
7. NVIDIA. *CUDA C++ Programming Guide*. <https://docs.nvidia.com/cuda/cuda-c-programming-guide/>
8. AMD. *What is HIP?* ROCm documentation. <https://rocm.docs.amd.com/projects/HIP/en/latest/what_is_hip.html>
9. AMD. *HIPIFY* documentation. <https://rocm.docs.amd.com/projects/HIPIFY/en/latest/>
