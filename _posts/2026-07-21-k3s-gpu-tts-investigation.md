---
layout: post
title: "홈랩 k3s에서 TTS를 GPU로 돌리려다: '안 하기로 한' 엔지니어링 결정"
date: 2026-07-21 23:00:00 +0900
categories: [Infra, SRE]
tags: [K3s, GPU, NVIDIA, TTS, XTTS, Homelab, PyTorch, CUDA]
---

# 3GB짜리 GTX 1060에 XTTS를 얹을 수 있을까

홈랩 k3s 클러스터에서 도는 `lemuel-xr`의 TTS 사이드카(Coqui XTTS-v2)가 노드 하나를 메모리로 짓누르고 있었습니다. 이 글은 "그럼 GPU로 돌리면 되지 않나?"라는 자연스러운 아이디어를 끝까지 파고들어, 결국 **하지 않기로 결정한** 과정의 기록입니다. 때로는 가장 좋은 엔지니어링 결정이 "안 한다"일 때가 있습니다.

## 발단: TTS가 david 노드를 86%까지 밀어올림

`lemuel-xr-tts`는 XTTS-v2 신경망 모델을 부팅 시 RAM에 통째로 올려두고 상주시킵니다. idle 상태에서도 **약 3.5GB**를 점유하는데, 이게 15GB짜리 소형 워커 노드 `david`의 메모리를 86%까지 밀어올렸습니다.

누수가 아니라 원가입니다. 모델을 요청마다 로드하면 매 합성이 수 분 걸리니, warm 상태로 상주시키는 게 의도적 설계죠. 문제는 이 3.5GB가 작은 노드에겐 너무 무겁다는 것.

## 1차 해결: 여유 노드로 이동 (그런데 함정이 있었다)

가장 여유로운 노드로 옮기면 됩니다. `kubectl top nodes`로 보니 `lemuel`이 32GB 중 12%밖에 안 쓰고 있었습니다. 바로 `nodeSelector`로 핀했더니 — **Pending**.

```
0/6 nodes are available: 2 node(s) had untolerated taint(s), ...
```

`lemuel`은 **control-plane 노드(NoSchedule 테인트)** 였습니다. RAM이 텅 비어 있던 것도 워크로드를 안 돌리기 때문이었죠. 심지어 처음 후보였던 `solomon`도 `dedicated=NoSchedule` 테인트가 걸려 있었습니다.

결국 control-plane 테인트에 대한 `toleration`을 붙여 lemuel로 이동시켰고, david는 **86% → 59%**로 해방됐습니다. (홈랩 한정 조치 — 교과서적으론 control-plane에 워크로드를 얹지 않습니다.)

## 진짜 질문: GPU로 옮기면 더 근본적이지 않을까

CPU 추론은 모델 가중치가 전부 시스템 RAM에 상주합니다. 하지만 **GPU로 돌리면 가중치가 VRAM으로 가서 시스템 RAM 부담이 사라지고**, 합성 속도도 빨라집니다. 즉 TTS를 david로 되돌려도 메모리 압박 없이 쓸 수 있게 됩니다. 매력적이죠.

### 노드별 GPU 실측

먼저 어느 노드에 쓸 수 있는 GPU가 있는지 `lspci`와 `nvidia-smi`로 전수 조사했습니다.

| 노드 | GPU 하드웨어 | 드라이버 | 판정 |
|------|------|------|------|
| **david** | NVIDIA GTX 1060 3GB | ✅ 580.159.03 | **유일하게 사용 가능** |
| louise | NVIDIA MX150 (2GB) | ❌ 미설치 | 드라이버 깔면 후보 |
| lemuel | AMD Radeon (모바일) | — | CUDA 아님 → XTTS 불가 |
| solomon / ilwon / isagal | 없음 | — | 불가 |

"나머지는 GPU 있을걸?"이라는 기대와 달리, 실제로 쓸 수 있는 NVIDIA GPU는 **david의 GTX 1060 하나뿐**이었습니다.

### 게다가 k8s가 GPU를 아예 못 본다

```
$ kubectl get nodes -o custom-columns='NODE:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu'
NODE      GPU
david     <none>
...
```

전 노드 `nvidia.com/gpu = none`. **NVIDIA device plugin이 설치돼 있지 않아서**, david에 GPU가 물리적으로 있어도 쿠버네티스가 파드에 할당하지 못하는 상태였습니다.

## De-risk: k3s를 건드리기 전에 docker로 먼저 검증

여기서 중요한 판단을 했습니다. GPU를 k8s에 물리려면 `nvidia-container-toolkit` 설치 → k3s containerd에 nvidia 런타임 등록 → device plugin 배포가 필요한데, **k3s-agent를 재시작하면 david 위의 프로덕션 파드 58개**(settlement, sparta, 각종 postgres 등)가 잠깐 영향을 받습니다.

그래서 그 무거운 작업을 하기 전에, **david에 마침 따로 돌고 있던 docker**(k8s 파드와 별개)로 XTTS가 3GB VRAM에 실제로 들어가는지부터 검증하기로 했습니다.

- `nvidia-container-toolkit` 설치 → docker 런타임 구성
- `docker run --gpus all`로 컨테이너에서 GPU 접근 확인 → ✅ `GPU 0: NVIDIA GeForce GTX 1060 3GB`
- 컨테이너 내부 torch도 CUDA 인식 → ✅ `cuda_available: True`

여기까지는 순조로웠습니다.

## 진짜 걸림돌: 프로덕션 이미지는 'CPU 전용' torch로 빌드돼 있었다

XTTS를 실제로 CUDA에 올려보려는데, 프로덕션 이미지의 `requirements.txt`가 발목을 잡았습니다.

```python
# torch 2.6부터 torch.load의 weights_only 기본값이 True로 바뀌어
# Coqui TTS 0.22.0의 XTTS 체크포인트 로딩이 실패한다 → CrashLoop의 진짜 원인.
# weights_only가 아직 False이던 마지막 계열로 고정.
torch==2.5.1        # ← CPU 빌드
transformers==4.40.2  # BeamSearchScorer가 제거되기 전 마지막 버전
```

즉 이 이미지의 torch는 과거 CrashLoop을 잡느라 **의도적으로 CPU 전용 2.5.1로 고정**돼 있었습니다. `.to("cuda")` 한 줄 추가한다고 되는 게 아니라, weights_only 호환(2.5.1)과 transformers 핀(4.40.2)을 **동시에 유지하면서 CUDA 빌드(2.5.1+cu121)로 이미지를 통째 리빌드**해야 GPU를 쓸 수 있다는 뜻이었습니다.

## 결론: 지금은 하지 않는다

GPU 전환에 실제로 필요한 일을 늘어놓으면:

1. TTS 이미지를 CUDA torch로 리빌드 (핀 호환을 맞춰가며 — 까다로움)
2. `app.py`에 `.to("cuda")` 추가
3. k3s GPU 셋업 — nvidia 런타임 등록 시 **david k3s-agent 재시작 → 프로덕션 58개 파드 영향** + device plugin 배포
4. TTS를 david+GPU로 핀
5. 그리고 **GTX 1060의 VRAM 3GB는 XTTS에 빠듯** — 짧은 문장은 되지만 긴 합성은 GPU OOM 여지가 있어, 리빌드 없이는 이 리스크를 검증조차 할 수 없음

반면 얻는 것은? **이미 lemuel 이동으로 해결된 메모리 문제**를, 훨씬 큰 리스크를 지고 다시 푸는 것뿐입니다.

> 엔지니어링에서 "할 수 있다"와 "해야 한다"는 다릅니다. 이번 건은 **명백히 할 수 있지만, 지금 할 이유가 없는** 케이스였습니다.

david에는 toolkit과 런타임 구성만 무해하게 남겨뒀습니다(나중에 VRAM 큰 GPU가 생기거나 TTS를 Piper 같은 경량 모델로 교체할 때 재활용). 테스트 임시파일은 모두 정리했고요.

## 남은 교훈

- **여유 자원처럼 보이는 노드를 의심하라.** RAM이 텅 빈 노드는 control-plane이라 워크로드가 안 붙는 경우가 많다. 테인트를 먼저 확인.
- **파괴적인 인프라 변경 전에, 격리된 곳에서 먼저 검증하라.** 이번엔 k8s와 무관한 docker로 먼저 찔러본 덕에 프로덕션 58파드를 건드리지 않고 결론에 도달했다.
- **핀은 이유가 있다.** `torch==2.5.1 CPU`는 그냥 게으른 게 아니라 과거 CrashLoop을 해결한 결과였다. 바꾸기 전에 왜 그렇게 됐는지부터 읽어야 한다.
