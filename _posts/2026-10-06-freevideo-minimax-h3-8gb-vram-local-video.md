---
layout: post
title: "FreeVideo — 8GB VRAM 그래픽카드로 MiniMax H3 영상 생성하기 (그리고 한국 사용자가 먼저 봐야 할 라이선스 한 줄)"
date: 2026-10-06 23:50:00 +0900
categories: [AI]
tags: [freevideo, minimax-h3, video-generation, comfyui, local-ai, vram, open-source, license]
---

> **GitHub: <https://github.com/FlashML-org/FreeVideo>**

"8GB 그래픽카드에서도 영상 생성이 된다"는 소개가 돌고 있다. 주인공은 오픈소스 프로젝트 **FreeVideo** 다. 대형 영상 생성 모델 **MiniMax H3** 를 소비자용 GPU 에서 로컬로 돌리게 해 주는 추론 엔진이다.

이 글에서는 소셜에 도는 요약 수치를 저장소의 README·문서 원문과 하나씩 대조했다. 대부분 맞다. 다만 **속도 수치 하나는 조건이 섞여 있었고**, 무엇보다 **한국에서 쓰려는 사람이 반드시 알아야 할 라이선스 조항**이 있었다. 그것부터 쓴다.

> 기준: 2026-10-06, FreeVideo v0.2.3 시점 저장소.

---

## ⚠️ 먼저: 모델 가중치 라이선스가 한국을 제외한다

FreeVideo **코드**는 Apache License 2.0 이다. 하지만 README 마지막 줄은 이렇게 적는다.

> "The model weights are licensed under the MiniMax H3 Community License, which includes territorial and acceptable-use restrictions."

[그 라이선스 원문](https://huggingface.co/OpenVDN/vdn-minimax-h3-edge/blob/main/LICENSE)을 열어 보면 적용 지역이 이렇게 정의돼 있다.

- "Applicable Territory" means **worldwide, excluding the Excluded Territories.**
- "Excluded Territories" means **the European Union, the United Kingdom, the Republic of Korea and the United States of America.**

즉 이 라이선스가 사용·복제·배포 권한을 주는 지역에 **대한민국이 포함되지 않는다.** 미국·EU·영국도 마찬가지다. 라이선스 본문은 제외 지역에서 배포를 원하면 MiniMax 에 별도로 문의하라고 안내한다.

코드가 Apache 2.0 이라서 "오픈소스니까 써도 된다"고 생각하기 쉽다. 하지만 **실제로 영상을 만드는 건 가중치**이고, 가중치의 사용 조건은 별개다. 개인 실험이든 업무든, 한국에서 쓰기 전에 라이선스를 직접 확인하자. 이 글은 법률 자문이 아니다.

---

## FreeVideo 가 하는 일

README 의 소개는 이렇다. 4 단계로 나눠 보면 다음과 같다.

1. FreeVideo 는 MiniMax H3 를 위한 **로컬 추론 엔진**이다.
2. 실제로 돌리는 모델은 [OpenVDN](https://github.com/OpenVDN)의 **8 스텝 VDN-H3** 모델이다([Hugging Face](https://huggingface.co/OpenVDN/vdn-minimax-h3)).
3. 그 모델은 [Video DeltaNet](https://openvdn.github.io/)의 하이브리드 어텐션을 쓴다(논문: [arXiv:2609.20744](https://arxiv.org/abs/2609.20744)).
4. 사용 형태는 **ComfyUI 플러그인**이다. Windows·macOS 런처가 있고, Linux 는 명령줄로 쓴다.

### 공유된 요약 vs 원문

| 공유된 요약 | README·문서 원문 | 판정 |
|---|---|---|
| 8GB VRAM·16GB RAM 으로 실행 가능 | "as little as 8 GB of VRAM and 16 GB of RAM" | ✅ 최소 사양 기준 |
| 필요한 부분만 그때그때 불러옴 | 가중치 스트리밍·비동기 프리페치·청크 계산으로 피크 메모리를 낮춤 | ✅ |
| ComfyUI 지원, 텍스트·첫/마지막 프레임·이미지·영상·오디오 레퍼런스 | "Text prompts, first and last frames, and image, video and audio references", ComfyUI 통합 | ✅ |
| RTX 4060 Ti 에서 1344×768 영상 약 9 분 | 4060 Ti **16GB** + RAM 32GB 에서 558 초(약 9.3 분) | ⚠️ 8GB 카드 수치가 아님 |

### 속도 수치의 실제 조건

[실행 계획 문서](https://github.com/FlashML-org/FreeVideo/blob/main/docs/execution-planning.md)의 End-to-end 표 조건은 **Windows, 1344×768, 10 초 길이, two-pass 샘플링**이다.

| GPU | VRAM + RAM | 시간 |
|---|---|---|
| RTX 5090 | 32GB + 64GB | 122 초 |
| RTX 5060 Ti | 16GB + 32GB | 486 초 |
| RTX 4060 Ti | **16GB** + 32GB | 558 초 |
| RTX 4060 Ti (커뮤니티 보고 [#22](https://github.com/FlashML-org/FreeVideo/issues/22)) | **8GB** + **64GB** | 603 초 |

"약 9 분"은 4060 Ti **16GB 모델** 결과다. **8GB 카드로 돌린 커뮤니티 보고는 약 10 분(603 초)이고, 그때 시스템 RAM 은 64GB 였다.** VRAM 이 작으면 모델 블록을 시스템 메모리에 두고 매 스텝 GPU 로 복사하기 때문에, RAM 이 넉넉해야 속도가 나온다. 문서상 "8GB/16GB" 는 **돌아가는 최소선**이지, 표에 나온 속도를 내는 조건이 아니다.

### 메모리를 어떻게 아끼나

같은 문서가 동작 방식을 꽤 자세히 적어 두었다.

- GPU 아키텍처마다 FP8 경로를 고른다. 네이티브 FP8 연산을 쓰거나, 가중치는 FP8 로 저장하고 연산은 BF16 으로 한다. 쓸 수 있는 어텐션 커널도 자동으로 탐색한다.
- 트랜스포머 블록 중 VRAM 에 상주시킬 개수를 남은 VRAM 예산으로 계산한다. 나머지 블록은 호스트 메모리에 두고(고정 메모리 최대 22GB) **매 스텝 GPU 로 복사**한다.
- `./freevideo plan --vram-gib 8 --ram-gib 16` 을 실행하면 가중치를 올리지 않고도 내 사양에서 어떤 계획이 나오는지 볼 수 있다.

용량별 성능은 NVIDIA H200 에서 VRAM·호스트 메모리를 8~32GiB 로 인위적으로 제한해 측정했다고 밝힌다. **진짜 8GB 카드 실측이 아니라 큰 GPU 에서 제한을 건 측정**이라는 점은 알고 보자.

### Mac 도 된다 (프리뷰)

v0.1.2 부터 Apple Silicon 맥 프리뷰가 있다. [Mac 가이드](https://github.com/FlashML-org/FreeVideo/blob/main/docs/Mac.md) 기준으로 M5·통합 메모리 24GB(가용 약 14GB)에서 걸린 시간은 다음과 같다.

| 해상도 | 길이 | 시간 |
|---|---|---|
| 1344×768 | 10 초 | 약 42 분 |
| 960×544 | 10 초 | 약 22 분 |
| 512×512 | 1.6 초 | 약 3 분 |

M5 이전 맥은 BF16 으로 돌아서 더 오래 걸린다. 맥 앱은 아직 Apple 공증 전이라 처음 실행할 때 macOS 가 막는다.

---

## 설치 방법 요약

- **Windows**: Releases 의 `FreeVideo.exe` 실행 → ComfyUI 폴더 선택 또는 새로 설치 → Install & launch.
- **기존 ComfyUI**: `ComfyUI/custom_nodes` 에서 `git clone https://github.com/FlashML-org/FreeVideo.git` 한 뒤 재시작. Workflow → Browse Templates → FreeVideo 로 들어간다.
- **Linux**: `./setup.sh` 로 설치한 뒤 `./freevideo generate --prompt-file prompt.txt --out video.mp4` 로 생성한다.
- 품질은 v0.2.0 부터 Light / Medium / High / Max 4 단계다. 높을수록 오래 걸린다.

---

## 정리

- **기술적으로는 의미 있는 진전이다.** 대형 영상 모델을 8GB VRAM 에서 "돌아가게" 만든 핵심은 가중치 스트리밍과 하드웨어별 실행 계획이다.
- **속도는 시스템 RAM 에 크게 좌우된다.** 8GB 카드라면 RAM 을 넉넉히 두는 게 사실상 필수다. 공유된 "9 분"은 16GB 카드 수치다.
- **한국에서는 가중치 라이선스가 먼저다.** 코드는 Apache 2.0 이지만, 가중치 라이선스(MiniMax H3 Community License)는 대한민국을 적용 지역에서 제외한다.

---

## References

1. FlashML-org, *FreeVideo* (README, v0.2.3). <https://github.com/FlashML-org/FreeVideo>
2. FreeVideo, *Adaptive Execution Planner* (docs/execution-planning.md). <https://github.com/FlashML-org/FreeVideo/blob/main/docs/execution-planning.md>
3. FreeVideo, *Mac guide* (docs/Mac.md). <https://github.com/FlashML-org/FreeVideo/blob/main/docs/Mac.md>
4. FreeVideo Issue #22 (RTX 4060 Ti 8GB 커뮤니티 보고). <https://github.com/FlashML-org/FreeVideo/issues/22>
5. OpenVDN, *VDN-H3* (Hugging Face). <https://huggingface.co/OpenVDN/vdn-minimax-h3>
6. *MiniMax H3 Community License* (vdn-minimax-h3-edge LICENSE). <https://huggingface.co/OpenVDN/vdn-minimax-h3-edge/blob/main/LICENSE>
7. MiniMaxAI, *MiniMax-H3* (Hugging Face). <https://huggingface.co/MiniMaxAI/MiniMax-H3>
8. H. Xi et al., *Video DeltaNet: A Video-Native Hybrid Attention for Livestream Video Generation*, arXiv:2609.20744, 2026. <https://arxiv.org/abs/2609.20744>
