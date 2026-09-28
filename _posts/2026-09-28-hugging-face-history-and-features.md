---
layout: post
title: "허깅페이스(Hugging Face)의 역사와 기능 — 10대용 챗봇 앱이 'AI의 깃허브'가 되기까지"
date: 2026-09-28 22:40:19 +0900
categories: [AI]
tags: [HuggingFace, Transformers, Hub, OpenSource, BLOOM, Gradio, llama.cpp, LeRobot, safetensors]
---

🤗 이모지가 회사 이름인 곳이 있습니다. 지금은 오픈 모델을 받으려면 거의 반드시 거쳐 가는 곳이고, 흔히 **"AI의 깃허브"**라고 불립니다([CNBC, 2023](https://www.cnbc.com/2023/08/24/google-amazon-nvidia-amd-other-tech-giants-invest-in-hugging-face.html)). 그런데 이 회사의 출발은 **10대를 위한 수다 떠는 챗봇 앱**이었습니다. 이 글은 허깅페이스가 어떻게 여기까지 왔는지(역사)와 지금 무엇을 제공하는지(기능)를 공식 블로그, GitHub 릴리스 기록, 주요 언론 보도로 정리한 것입니다.

---

## 1부. 역사

### 1-1. 2016~2018: "AI 절친" 챗봇 앱

허깅페이스는 2016년 뉴욕에서 프랑스 출신의 **클레망 들랑그(Clément Delangue, CEO), 쥘리앵 쇼몽(Julien Chaumond, CTO), 토마 울프(Thomas Wolf, CSO)**가 세웠습니다. 사명은 🤗(U+1F917 HUGGING FACE) 이모지에서 따왔는데, CNBC 는 이 이름이 **아이폰용 챗봇 앱을 만들던 시절**에서 왔다고 설명합니다([CNBC](https://www.cnbc.com/2023/08/24/google-amazon-nvidia-amd-other-tech-giants-invest-in-hugging-face.html)).

TechCrunch 에 따르면 이 앱은 2017년 초 출시됐고, 사용자가 **디지털 친구를 만들어 문자를 주고받는** 방식이었습니다. 단순히 말뜻을 알아듣는 데 그치지 않고 **감정을 감지해 답을 조절**하려 했다는 점이 특징이었습니다([TechCrunch, 2019-12-17](https://techcrunch.com/2019/12/17/hugging-face-raises-15-million-to-build-the-definitive-natural-language-processing-library/)).

앱이 대박이 나지는 않았지만, 이 시절에 쌓은 **자연어 처리 기술과 "만든 걸 공개하는 습관"**이 다음 단계의 밑천이 됩니다.

### 1-2. 2018~2019: BERT 한 편이 회사를 바꾸다

전환점은 2018년 10월 구글의 **BERT** 공개였습니다. BERT 는 텐서플로(TensorFlow)로 나왔는데, 허깅페이스는 이를 **파이토치(PyTorch)로 옮긴 구현을 오픈소스로 공개**합니다. 지금의 `transformers` 리포는 **2018년 10월 29일** 생성됐습니다(GitHub API `created_at`). 허깅페이스 스스로도 2022년 투자 발표문에서 "2018년 PyTorch BERT 를 처음 오픈소스로 공개한 뒤 먼 길을 왔다"고 회고합니다([HF 블로그, Series C](https://huggingface.co/blog/series-c)).

이름이 바뀐 과정에 확장 방향이 그대로 드러납니다([GitHub 릴리스](https://github.com/huggingface/transformers/releases)).

| 날짜 | 릴리스 | 의미 |
| --- | --- | --- |
| 2018-10 | `pytorch-pretrained-bert` | BERT 의 파이토치 포팅 |
| 2019-07-16 | v1.0.0 → **`pytorch-transformers`** | XLNet·XLM 추가, 모델·토크나이저 API 통일 |
| 2019-09-26 | v2.0.0 → **`transformers`** | TensorFlow 2.0 ↔ PyTorch 상호운용 |
| 2020-11-30 | v4.0.0 | Fast tokenizer, 파일 구조 재정비 |
| 2026-01-26 | **v5.0.0** | 5년 만의 메이저 버전 |

"BERT 한 모델의 포팅"에서 **"모든 트랜스포머 모델의 공통 인터페이스"**로 이름이 넓어진 것입니다.

2019년 12월 **Lux Capital 주도로 1,500만 달러**를 투자받으면서 방향 전환이 공식화됩니다. 당시 TechCrunch 는 회사를 "10대용 인공 절친 앱을 만들던 곳"으로 소개하면서, Transformers 가 **100만 회 이상 다운로드, GitHub 스타 1만 9천 개**를 기록했고 Monzo 의 고객지원 챗봇과 Microsoft Bing 이 프로덕션에서 쓰고 있다고 전했습니다([TechCrunch](https://techcrunch.com/2019/12/17/hugging-face-raises-15-million-to-build-the-definitive-natural-language-processing-library/)).

### 1-3. 2020~2022: 라이브러리에서 "허브"로

코드만으로는 부족했습니다. 학습된 모델은 각자의 컴퓨터나 **깨진 구글 드라이브 링크**로 떠돌았습니다. 허깅페이스는 2020년 **Hub** 첫 버전을 만들고, 2020년 말 Hub 접근 코드를 `transformers` 에서 떼어 내 **`huggingface_hub`** 라이브러리로 분리합니다. 목표는 "모델 공유를 깃허브에서 코드 공유하듯 쉽게"였습니다([HF 블로그, huggingface_hub v1.0](https://huggingface.co/blog/huggingface-hub-v1)). 이 무렵 **`datasets`**(2020-03 리포 생성)도 나옵니다.

- **2021-12-21: Gradio 인수.** 브라우저에서 모델 데모를 몇 줄로 만드는 도구입니다. 지금 **Spaces**(모델 데모 호스팅)에서 가장 흔히 쓰이는 SDK 중 하나가 됐습니다([HF 블로그](https://github.com/huggingface/blog/blob/main/gradio-joins-hf.md)).
- **2022-05: 시리즈 C 1억 달러.** Lux Capital 주도, Sequoia·Coatue 참여. 발표 시점 Hub 에 **사전학습 모델 10만 개, 데이터셋 1만 개**, 사용 기업 1만 곳 이상([HF 블로그, Series C](https://huggingface.co/blog/series-c)).
- **2022-07-12: BLOOM 공개.** 허깅페이스가 2021년 봄 시작한 공개 연구 프로젝트 **BigScience** 의 결과물입니다. **1,760억 파라미터, 자연어 46개 + 프로그래밍 언어 13개**, 70여 개국 250여 기관 1,000명 이상의 연구자가 참여했고, 프랑스 슈퍼컴퓨터 **Jean Zay** 에서 117일간 학습했습니다(CNRS·GENCI 컴퓨팅 지원). 중간 체크포인트와 옵티마이저 상태까지 공개했습니다([HF 블로그, BLOOM](https://huggingface.co/blog/bloom), [CNRS 보도자료](https://www.cnrs.fr/en/press/release-largest-trained-open-science-multilingual-language-model-ever)).

BLOOM 은 "대형 언어모델은 몇몇 빅테크만 만든다"는 구도에 **공개 과학으로 맞선 첫 대형 시도**라는 상징성이 컸습니다.

### 1-4. 2023~2024: 빅테크가 모두 투자한 중립지대

**2023년 8월 시리즈 D 2억 3,500만 달러, 기업가치 45억 달러.** Salesforce Ventures 주도에 **구글, 아마존, 엔비디아, AMD, 인텔, 퀄컴, IBM** 이 함께 들어왔습니다([TechCrunch](https://techcrunch.com/2023/08/24/hugging-face-raises-235m-from-investors-including-salesforce-and-nvidia/), [IBM 보도자료](https://newsroom.ibm.com/2023-08-24-IBM-to-Participate-in-235M-Series-D-Funding-Round-of-Hugging-Face)). TechCrunch 는 이 가치가 2022년 5월의 두 배이고, 보도에 따르면 연환산 매출의 100배가 넘는다고 전했습니다.

눈여겨볼 점은 **서로 경쟁하는 클라우드·칩 회사들이 한꺼번에 투자했다**는 것입니다. 허깅페이스가 특정 진영이 아니라 **모두가 모델을 올리고 받아 가는 중립 플랫폼**이라는 위치를 보여 줍니다(해석).

- **2024-08: XetHub 인수.** Hub 는 처음에 Git LFS 위에 지어졌는데, AI 파일은 "크기만 큰 게 아니라 매우매우 크다"는 게 문제였습니다. XetHub 의 **청크 단위 저장·중복 제거**를 쓰면, 10GB Parquet 파일에 행 하나만 추가해도 10GB 를 다시 올릴 필요 없이 바뀐 청크만 올리면 됩니다. 발표 당시 Hub 는 **모델 130만, 데이터셋 45만, Spaces 68만 개**, LFS 저장량 12PB, 하루 요청 10억 건이었습니다([HF 블로그, XetHub](https://huggingface.co/blog/xethub-joins-hf)).

### 1-5. 2025~2026: 로봇, 로컬 AI, 그리고 "내려놓기"

- **로봇 진출.** 2024년 테슬라 옵티머스 출신 레미 카덴(Remi Cadene)을 영입해 오픈소스 로봇 라이브러리 **LeRobot** 을 냈고, 2025-04 프랑스의 **Pollen Robotics 를 인수**했습니다. 허깅페이스의 **다섯 번째 인수**이자 첫 하드웨어 판매입니다([HF 블로그](https://huggingface.co/blog/hugging-face-pollen-robotics-acquisition), [Fortune](https://fortune.com/2025/04/14/ai-company-hugging-face-buys-humanoid-robot-company-pollen-robotics-reachy-2/)). 2025-07 에는 **$399(Lite)·$499(무선)** 짜리 데스크톱 로봇 **Reachy Mini** 를 발표했습니다([HF 블로그, Reachy Mini](https://huggingface.co/blog/reachy-mini)).
- **2025-10: `huggingface_hub` v1.0.** 5년 만의 1.0입니다. 발표 시점 **공개 모델 200만+, 데이터셋 50만+, Spaces 100만+**를 뒷받침하고, 새 `hf` CLI 와 Xet 기반 전송(`hf_xet`)으로 전환했습니다([HF 블로그](https://huggingface.co/blog/huggingface-hub-v1)).
- **2025-12 / 2026-01: Transformers v5.** 발표문에 따르면 하루 pip 설치 **300만 회**(v4 시절 하루 2만 회), 누적 12억 회 이상, 지원 아키텍처 40개 → 400개 이상입니다([HF 블로그, Transformers v5](https://huggingface.co/blog/transformers-v5)).
- **2026-02-20: GGML·llama.cpp 합류.** 로컬 추론의 표준인 llama.cpp 팀이 허깅페이스에 합류했습니다. 게오르기 게르가노프(Georgi Gerganov) 팀은 계속 100% llama.cpp 에 전념하고 기술 방향의 자율권을 유지하며, 프로젝트는 100% 오픈소스로 남는다고 밝혔습니다. 목표는 transformers 의 모델 정의를 거의 "원클릭"으로 llama.cpp 에 옮기는 것입니다([HF 블로그](https://huggingface.co/blog/ggml-joins-hf)).
- **2026-04-08: safetensors 를 PyTorch Foundation 에 이관.** 허깅페이스가 만든 안전한 가중치 포맷을 리눅스 재단 산하로 넘겨 **특정 회사가 아닌 커뮤니티 소유**로 만들었습니다([HF 블로그](https://huggingface.co/blog/safetensors-joins-pytorch-foundation)).
- **TGI 유지보수 모드.** 자체 추론 서버 Text Generation Inference 는 유지보수 모드로 들어갔고, README 는 앞으로 **vLLM·SGLang·llama.cpp·MLX** 를 쓰라고 권합니다([TGI README](https://github.com/huggingface/text-generation-inference)).

마지막 두 항목이 흥미롭습니다. 허깅페이스는 **자기 것을 끝까지 쥐기보다 표준이 된 것은 재단에 넘기고, 남이 더 잘하는 영역(추론 엔진)은 물려주는** 쪽을 택하고 있습니다. 대신 **"모델 정의의 원천(source of truth)"**이라는 자리, 곧 transformers 와 Hub 에 집중합니다(해석).

---

## 2부. 기능 — 지금 무엇을 제공하나

### 2-1. Hub: 세 가지 저장소

Hub 의 모든 것은 **Git 기반 저장소**이고 버전, 커밋, diff, 브랜치, 토론, 카드(README)를 갖습니다([huggingface_hub v1.0 블로그](https://huggingface.co/blog/huggingface-hub-v1)).

| 저장소 | 담는 것 | 예 |
| --- | --- | --- |
| **Models** | 가중치 + 설정 + 모델 카드 | `bigscience/bloom` |
| **Datasets** | 학습·평가 데이터 + 데이터셋 카드 | Parquet, JSONL 등 |
| **Spaces** | Gradio·Streamlit·Docker 로 만든 데모 앱 | 모델을 브라우저에서 바로 시연 |

모델 카드에 라이선스, 학습 데이터, 한계를 적게 한 문화가 "어떤 모델을 써도 되는가"를 판단하는 기본 정보가 되었습니다.

### 2-2. 오픈소스 라이브러리

| 라이브러리 | 역할 |
| --- | --- |
| **transformers** | 모델 정의의 표준. `pipeline()` 한 줄로 추론 |
| **huggingface_hub** / `hf` CLI | Hub 업로드·다운로드·저장소 관리 |
| **datasets** | 대용량 데이터셋 로드·스트리밍·전처리 |
| **diffusers** | 이미지·영상 생성(디퓨전) 모델 |
| **safetensors** | 임의 코드 실행이 불가능한 가중치 포맷 (현재 PyTorch Foundation 소속) |
| **gradio** | 몇 줄로 만드는 모델 데모 UI |
| **lerobot** | 로봇 학습용 모델·데이터셋·시뮬레이터 |

safetensors 는 보안 측면에서 특히 중요합니다. 예전의 pickle 기반 포맷은 **파일을 여는 순간 악성 코드가 실행될 수 있었습니다.** safetensors 는 크기 제한이 있는 JSON 헤더와 날것의 텐서 데이터만 담아 이 위험을 구조적으로 없앴고, 지금은 Hub 의 기본 배포 포맷입니다([HF 블로그](https://huggingface.co/blog/safetensors-joins-pytorch-foundation)).

가장 짧은 사용 예:

```python
from transformers import pipeline

clf = pipeline("sentiment-analysis")  # Hub 에서 기본 모델 자동 다운로드
print(clf("허깅페이스 덕분에 모델 받기가 쉬워졌다"))
```

```bash
pip install -U huggingface_hub
hf download bigscience/bloom-560m   # v1.0 의 새 CLI (옛 huggingface-cli 대체)
```

### 2-3. 추론: 직접 안 돌려도 된다

- **Inference Providers** — 여러 추론 업체(Cerebras, Groq, Together, Fireworks, Replicate 등)의 모델을 **허깅페이스 토큰 하나와 같은 API** 로 호출합니다. 특정 업체에 묶이지 않는 것이 핵심 주장입니다([공식 문서](https://huggingface.co/docs/inference-providers/index)).
- **Inference Endpoints** — Hub 의 모델을 전용 인프라에 올려 API 로 서빙하는 관리형 서비스입니다.
- 자체 추론 서버(TGI)는 앞서 말한 대로 유지보수 모드이고, 서빙은 **vLLM·SGLang·llama.cpp** 쪽으로 넘어갔습니다.

### 2-4. 수익 모델

Contrary Research 는 허깅페이스를 **"프리미엄·오픈 코어"** 모델로 분석합니다. 라이브러리·Hub 같은 핵심 자산은 무료로 공개해 개발자를 모으고, 기업용 기능, 관리형 추론, 컴퓨팅으로 수익을 냅니다([Contrary Research](https://research.contrary.com/report/hugging-face)).

---

## 3부. 정리 — 허깅페이스가 성공한 이유 (해석)

1. **모델을 만들지 않고 모델을 "쓸 수 있게" 만들었다.** BERT 를 발명한 건 구글이지만, 모두가 쓰게 만든 건 허깅페이스의 파이토치 포팅이었습니다.
2. **라이브러리 → 허브 → 데모 → 추론으로 한 단계씩 층을 올렸다.** 각 층이 다음 층의 사용자를 데려왔습니다.
3. **중립성.** 경쟁하는 빅테크들이 모두 투자하고 모두 모델을 올리는 곳이 되었습니다.
4. **내려놓을 줄 안다.** safetensors 는 재단에, 추론 엔진은 vLLM·SGLang 에, 로컬 추론은 llama.cpp 팀의 자율에 맡기고 자신은 "원천"의 자리를 지킵니다.

반대로 볼 대목도 있습니다. 2023년 시리즈 D 가치가 매출의 100배를 넘는다는 보도처럼 **오픈 생태계를 수익으로 바꾸는 문제**는 여전히 숙제이고, Hub 에 올라오는 방대한 모델의 **라이선스·안전성 검증 책임**이 어디까지인지도 계속 논쟁거리입니다. 이 글의 수치는 대부분 허깅페이스 자체 발표이며, 중립적인 제3자 감사 수치는 찾지 못했습니다.

---

## References

1. Hugging Face, *We Raised $100 Million for Open & Collaborative Machine Learning* (2022-05-09) — <https://huggingface.co/blog/series-c>
2. Hugging Face / BigScience, *Introducing The World's Largest Open Multilingual Language Model: BLOOM* (2022-07-12) — <https://huggingface.co/blog/bloom>
3. CNRS, *Release of largest trained open-science multilingual language model ever* (2022-07-12) — <https://www.cnrs.fr/en/press/release-largest-trained-open-science-multilingual-language-model-ever>
4. Hugging Face, *XetHub is joining Hugging Face!* (2024-08-08) — <https://huggingface.co/blog/xethub-joins-hf>
5. Hugging Face, *Hugging Face to sell open-source robots thanks to Pollen Robotics acquisition* (2025-04-14) — <https://huggingface.co/blog/hugging-face-pollen-robotics-acquisition>
6. Hugging Face, *Reachy Mini – The Open-Source Robot for Today's and Tomorrow's AI Builders* (2025-07-09) — <https://huggingface.co/blog/reachy-mini>
7. Hugging Face, *huggingface_hub v1.0: Five Years of Building the Foundation of Open Machine Learning* (2025-10-27) — <https://huggingface.co/blog/huggingface-hub-v1>
8. Hugging Face, *Transformers v5: Simple model definitions powering the AI ecosystem* (2025-12-01) — <https://huggingface.co/blog/transformers-v5>
9. Hugging Face, *GGML and llama.cpp join HF to ensure the long-term progress of Local AI* (2026-02-20) — <https://huggingface.co/blog/ggml-joins-hf>
10. Hugging Face, *Safetensors is Joining the PyTorch Foundation* (2026-04-08) — <https://huggingface.co/blog/safetensors-joins-pytorch-foundation>
11. Hugging Face, *Gradio is joining Hugging Face!* (2021-12-21) — <https://github.com/huggingface/blog/blob/main/gradio-joins-hf.md>
12. Hugging Face, *Inference Providers* 문서 — <https://huggingface.co/docs/inference-providers/index>
13. huggingface/transformers GitHub 릴리스 기록 — <https://github.com/huggingface/transformers/releases>
14. huggingface/text-generation-inference README (유지보수 모드 공지) — <https://github.com/huggingface/text-generation-inference>
15. R. Dillet, *Hugging Face raises $15 million to build the definitive natural language processing library*, TechCrunch (2019-12-17) — <https://techcrunch.com/2019/12/17/hugging-face-raises-15-million-to-build-the-definitive-natural-language-processing-library/>
16. K. Wiggers, *Hugging Face raises $235M from investors, including Salesforce and Nvidia*, TechCrunch (2023-08-24) — <https://techcrunch.com/2023/08/24/hugging-face-raises-235m-from-investors-including-salesforce-and-nvidia/>
17. K. Leswing, *Google, Amazon, Nvidia and other tech giants invest in AI startup Hugging Face*, CNBC (2023-08-24) — <https://www.cnbc.com/2023/08/24/google-amazon-nvidia-amd-other-tech-giants-invest-in-hugging-face.html>
18. IBM Newsroom, *IBM to Participate in $235M Series D Funding Round of Hugging Face* (2023-08-24) — <https://newsroom.ibm.com/2023-08-24-IBM-to-Participate-in-235M-Series-D-Funding-Round-of-Hugging-Face>
19. J. Kahn, *AI company Hugging Face buys humanoid robot company Pollen Robotics*, Fortune (2025-04-14) — <https://fortune.com/2025/04/14/ai-company-hugging-face-buys-humanoid-robot-company-pollen-robotics-reachy-2/>
20. Contrary Research, *Hugging Face Business Breakdown & Founding Story* (2026-01-15) — <https://research.contrary.com/report/hugging-face>
