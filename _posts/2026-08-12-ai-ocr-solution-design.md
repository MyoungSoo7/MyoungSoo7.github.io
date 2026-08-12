---
layout: post
title: "AI OCR 솔루션 분석·설계 — 제품 비교표 대신 제약에서 시작한다"
date: 2026-08-12 11:30:00 +0900
categories: [engineering, ai]
tags:
  [
    ocr,
    document-ai,
    tesseract,
    paddleocr,
    donut,
    layoutlm,
    vlm,
    개인정보보호법,
    라이선스,
  ]
---

AI OCR을 도입한다고 하면 대개 제일 먼저 나오는 게 제품 비교표다. 정확도 몇 %, 페이지당 얼마, 한국어 지원 O/X. 그런데 그 표는 대부분 쓸모가 없다.

이유는 두 가지다. 첫째, **이 분야엔 중립 제3자 헤드투헤드 벤치마크가 사실상 없다.** 이번 글을 쓰면서 Tesseract·PaddleOCR·EasyOCR을 같은 조건에서 비교한 독립 평가를 찾으려 했지만 확인하지 못했다. 돌아다니는 수치는 거의 전부 벤더 자체 측정이고, 재현 조건(입력 해상도·전처리·문서 종류)이 공개되지 않는다. 둘째, **OCR의 정확도는 모델보다 입력 문서가 결정한다.** 같은 엔진이 300 DPI 스캔본에서 잘 돌다가 휴대폰으로 비스듬히 찍은 사진에서 무너진다. 이건 내 경험담이 아니라 Tesseract 공식 문서가 스스로 적어둔 내용이다.[^tessquality]

그래서 이 글은 "무엇이 제일 좋은가"를 묻지 않는다. 대신 **선택지를 실제로 좁히는 제약**에서 출발한다.

## 1. 설계를 강제하는 네 가지 제약

경험상 OCR 아키텍처는 취향이 아니라 다음 네 개로 거의 결정된다.

**① 문서 종류.** 정형(고정 양식 — 신청서, 세금계산서), 반정형(같은 정보가 위치는 다른 곳에 — 영수증, 청구서), 자유형(계약서, 보고서). 정형이면 좌표 기반 룰이 여전히 가장 싸고 정확하다. 자유형일수록 레이아웃 이해 모델이나 VLM 쪽으로 밀린다.

**② 개인정보 등급.** 신분증·통장·건강보험증을 다루면 고유식별정보다. 이건 성능 문제가 아니라 **클라우드 API를 쓸 수 있느냐 없느냐**의 문제이고, 아키텍처 결정 중 되돌리기가 가장 어렵다.

**③ GPU 유무.** 자체 모델 서빙의 전제다. 없으면 CPU 추론이거나 클라우드다.

**④ 좌표(bounding box)가 필요한가.** 이게 실무에서 가장 과소평가되는 축이다. 값만 뽑으면 되는지, 아니면 "이 값이 원본 어디에서 왔는지"를 표시하고 사람이 검수해야 하는지. 후자면 좌표를 못 주는 방식은 탈락이다.

내 경우 ③은 이미 답이 나와 있다. 운영 중인 K3s 클러스터 6대 전부 GPU가 없다. 그래서 이 글은 "GPU를 산다면"이 아니라 **GPU가 없는 상태에서 무엇이 가능한가**를 기준으로 쓴다.

## 2. 세 갈래 — 파이프라인 / OCR-free / VLM

### 2-1. 전통 파이프라인: 검출 → 인식

가장 오래됐고 여전히 가장 예측 가능한 구조다. 이미지에서 글자 영역을 **검출(detection)** 하고, 잘라낸 조각을 **인식(recognition)** 한다.

인식 쪽의 표준이 된 건 CRNN이다. 특징 추출·시퀀스 모델링·전사를 하나의 학습 가능한 네트워크로 합쳐서, 문자 단위로 자르지 않고 임의 길이 시퀀스를 처리한다.[^crnn] 검출 쪽에서는 DBNet이 분기점이었다. 세그멘테이션 기반 검출의 병목이던 이진화 후처리를 네트워크 안으로 집어넣어 임계값을 적응적으로 학습시켰다.[^dbnet]

**Tesseract**는 이 계열의 맏형이다. 현재 안정 버전은 5.5.3(2026-07-24)이고,[^tessrel] LSTM 신경망 엔진은 4.0(2018-10-29)에서 들어왔다.[^tess4] 라이선스는 Apache-2.0이다 — GPL이라는 오해가 꽤 퍼져 있는데 리포의 LICENSE 파일은 Apache-2.0 전문이다.[^tesslic] 한국어 `kor.traineddata`와 세로쓰기용 `kor_vert.traineddata`가 공식 제공되고, 학습 데이터도 Apache-2.0이다.[^tessdata]

Tesseract를 후보에 넣을지는 **공식 문서가 스스로 적어둔 한계**를 읽고 정하는 게 빠르다. 이만큼 솔직한 벤더 문서는 드물다.

- 필기체: "할 수는 있지만 잘 안 된다. Tesseract는 인쇄된 텍스트용으로 설계됐다."[^tessfaq]
- 바코드: 지원 안 함.[^tessfaq]
- 표: "커스텀 세그멘테이션/레이아웃 분석 없이는 표에서 텍스트·데이터를 인식하는 데 문제가 있는 것으로 알려져 있다."[^tessquality]
- 해상도: 300 DPI 이상에서 가장 잘 동작.[^tessquality]
- 기울어짐: "페이지가 너무 기울면 라인 세그멘테이션 품질이 크게 떨어지고, 이는 OCR 품질에 심각한 영향을 준다."[^tessquality]
- 반전 이미지: 3.05까지는 어두운 배경+밝은 글씨를 처리했지만 4.x부터는 밝은 배경+어두운 글씨를 쓰라고 명시.[^tessquality]
- 사전: 기본값이 "문장"에 최적화돼 있어서, **영수증·가격표·코드류는 사전을 꺼야 인식률이 오른다.**[^tessquality]

마지막 항목은 전표 처리 설계에 직접 영향을 준다. 그리고 하나 더 — 품질이 안 나올 때 재학습부터 떠올리기 쉬운데, 공식 문서가 먼저 못을 박는다. "아주 특이한 폰트나 새 언어가 아니라면, Tesseract 재학습이 도움이 될 가능성은 낮다."[^tessquality]

**PaddleOCR**은 현재 이 계열에서 가장 활발하다. 최신 릴리스 v3.7.0(2026-06-11), 코드 Apache-2.0.[^paddlerel][^paddlelic] 원조 PP-OCR 논문은 "검출(DB) + 박스 보정(방향 분류) + 인식(CRNN/CTC)" 3부 구조를 명시한다.[^ppocr] 다만 **현행 3.x 문서는 이걸 그대로 쓰지 않는다.** 5개 모듈(문서 방향 분류·이미지 왜곡 보정·텍스트라인 방향 분류·검출·인식, 앞 3개 선택)로 재구성됐고 기본 모델은 PP-OCRv6_medium이다.[^paddlepipe] 조사 과정에서 확인한 건데, v6 검출 모듈 설명에는 `PPLCNetV4 + RepLKFPN`이라고만 적혀 있고 "DB/DBNet"이라는 단어가 나오지 않는다. **"PaddleOCR = DBNet"이라고 현재형으로 말하면 안 된다** — 그건 2020년 논문 기준이다.

한국어 전용 인식 모델(`korean_PP-OCRv5_mobile_rec`)이 공식 제공되고 모델카드에 한국어 데이터셋 88.0%가 적혀 있는데,[^paddlekor] 이건 **벤더 자체 측정**이라 그대로 기대치로 삼으면 안 된다.

**EasyOCR**은 검출에 CRAFT, 인식에 CRNN(ResNet/VGG + LSTM + CTC)을 쓴다고 README가 밝힌다.[^easyarch] 한국어는 `ko` 코드로 전용 가중치가 있다.[^easycfg] 다만 도입 전에 볼 게 있다 — **최신 릴리스가 v1.7.2(2024-09-24)로 약 2년간 새 릴리스가 없다.**[^easyrel] 필기체는 여전히 로드맵 상태다.[^easyroad] 기능 문제라기보다 유지보수 리스크로 계산에 넣어야 한다.

### 2-2. OCR-free: 파이프라인을 아예 없앤다

Donut(NAVER CLOVA 주도, ECCV 2022)은 다른 질문을 던진다. 텍스트를 읽는 단계를 왜 따로 두는가?[^donut]

저자들이 기존 OCR 기반 접근의 문제로 든 근거는 정확히 셋이다. (1) OCR 사용에 드는 높은 연산 비용, (2) 언어나 문서 종류에 대한 OCR 모델의 경직성, (3) **OCR 오류가 후속 처리로 전파되는 것**.[^donut] 세 번째가 핵심이다. 파이프라인 구조에서는 인식이 한 글자 틀리면 그 뒤 파싱·검증이 전부 그 위에서 돌아간다.

Donut은 이미지에서 곧바로 구조화된 출력을 생성한다. 코드는 MIT, 가중치(`naver-clova-ix/donut-base`)도 MIT라 상용 관점에서 가장 깔끔한 조합이다.[^donutlic][^donutw] 다국어·도메인 확장을 위한 합성 데이터 생성기(SynthDoG)도 함께 공개됐다.[^donut]

주의할 건, Donut 논문 초록의 "state-of-the-art" 주장은 저자 자체 평가이고 이번 조사에서 비교표 수치를 원문 텍스트로 회수하지 못했다는 점이다. 성능 우위를 단정하지 않는다.

### 2-3. 레이아웃까지 읽는 계열 — 그리고 라이선스 함정

LayoutLM 계열은 텍스트만이 아니라 **위치(2D bbox)와 이미지**를 함께 사전학습한다. v1은 텍스트+레이아웃 공동 사전학습에 이미지 피처를 부가하고,[^lmv1] v2는 셋을 2-스트림 멀티모달 Transformer로 사전학습 단계에서 통합하며 spatial-aware self-attention을 도입했고,[^lmv2] v3는 CNN과 영역 감독을 제거하고 linear patch로 통일했다.[^lmv3]

여기서 이 글에서 가장 실무적인 경고가 나온다.

**microsoft/unilm 리포 코드는 MIT지만, LayoutLMv2와 LayoutLMv3의 공개 가중치는 CC BY-NC-SA 4.0 — 비상업 라이선스다.**[^lmv2w][^lmv3w] v1 가중치만 MIT다.[^lmv1w] 리포 라이선스가 MIT라는 걸 확인하고 넘어가면 그대로 위반이다. 상용 제품에 넣으려면 (a) v1을 쓰거나, (b) 아키텍처만 가져와 자체 데이터로 처음부터 사전학습하거나, (c) Donut·PaddleOCR로 대체해야 한다.

같은 함정이 TrOCR에도 있다. TrOCR은 CNN+RNN+외부 언어모델 조합을 버리고 사전학습된 이미지 Transformer(인코더)와 텍스트 Transformer(디코더)로 wordpiece 단위 생성을 하는 인식기인데,[^trocr] `microsoft/trocr-base-handwritten`에는 `license: mit`이 있지만 `microsoft/trocr-base-printed`의 모델카드에는 **license 필드 자체가 없다.** 게다가 두 카드 모두 "TrOCR을 공개한 팀은 이 모델의 모델카드를 작성하지 않았으므로 이 카드는 Hugging Face 팀이 작성했다"고 명시한다 — **MIT 표기조차 원저자 진술이 아니다.**[^trocrhw][^trocrpr]

그리고 파이프라인 설계상 중요한 사실 하나. TrOCR 논문은 검출을 다루지 않는다. "이 논문에서는 문서 이미지의 텍스트 인식 태스크에 집중하고 텍스트 검출은 향후 과제로 남긴다."[^trocr] 인식기만 가져다가 OCR 전체를 대체할 수 있다고 생각하면 안 된다.

정리하면 이렇다.

| 대상                | 코드 라이선스 | 가중치 라이선스                  | 상용          |
| ------------------- | ------------- | -------------------------------- | ------------- |
| Tesseract           | Apache-2.0    | Apache-2.0 (tessdata)            | 안전          |
| PaddleOCR           | Apache-2.0    | Apache-2.0 (확인한 4종)          | 안전          |
| EasyOCR             | Apache-2.0    | 배포 가중치 라이선스 문서 미확인 | 주의          |
| Donut               | MIT           | MIT                              | 안전          |
| TrOCR               | MIT (unilm)   | 모델별로 갈림, 원저자 진술 아님  | 주의          |
| LayoutLM v1         | MIT           | MIT                              | 안전          |
| **LayoutLMv2 / v3** | **MIT**       | **CC BY-NC-SA 4.0**              | **상용 불가** |

교훈은 한 줄이다. **코드 라이선스와 가중치 라이선스는 별개 문서다. 리포 LICENSE만 보고 판단하면 안 된다.**

### 2-4. 범용 VLM에 그냥 이미지를 던지는 방식

지금 가장 많이 시도되는 접근이다. GPT·Claude·Gemini나 Qwen2.5-VL·InternVL 같은 오픈 VLM에 페이지 이미지를 넣고 "표를 JSON으로 뽑아줘"라고 시킨다. 파이프라인이 필요 없고, 프롬프트만으로 "이 영수증에서 공급가액과 부가세를 뽑아라" 같은 과제를 바로 붙일 수 있다. 실제로 잘 되는 구간이 분명히 있다.

문제는 **어디서 무너지는지가 잘 알려져 있지 않다**는 것이다. 그래서 이 절은 벤더 마케팅이 아니라 **논문 본문·공식 리포·공식 모델카드가 스스로 인정한 한계만** 모았다.

먼저 알아둘 메타사실이 하나 있다. 조사한 VLM 논문 12편(Qwen2.5-VL, Qwen2-VL, Qwen3-VL, InternVL2.5, InternVL3, InternVL3.5, GOT-OCR2.0, dots.ocr, PaddleOCR-VL, DeepSeek-OCR, Florence-2, olmOCR 2) 중 **"Limitations" 제목의 절을 가진 논문은 하나도 없다.** 한계 진술은 Conclusion·Discussion·Appendix에 흩어져 있고, 모델카드 중 명시적 `## Limitations`를 가진 건 Qwen2-VL-7B-Instruct 하나뿐이었다. 한계를 찾으려면 본문을 뒤져야 한다.

**(1) 반복 생성 붕괴 — 독립된 세 출처가 같은 실패를 보고한다.**

이게 가장 근거가 단단한 실패 모드다. 학습 쪽에서 InternVL2.5 논문은 "우리가 식별한 이상 현상 중 반복 생성이 가장 해로운 문제 하나"라고 적었다. 파인튜닝 데이터에 반복 패턴 샘플이 **수천 개만 섞여도** 모델이 반복 루프에 빠지며, 특히 긴 출력에서 그렇다고 한다.[^ivl25rep] 운영 쪽에서 Ai2의 olmOCR 논문은 더 직설적이다. "olmOCR을 개발하면서 가장 흔하게 겪은 실패는 출력이 같은 토큰·줄·문단의 끝없는 반복으로 퇴화하는 것"이다.[^olmrep] 문서 전용 모델인 Meta의 Nougat도 같은 걸 보고한다 — "모델이 같은 문장을 계속 반복하는 상태로 퇴화하며, **스스로 이 상태에서 빠져나오지 못한다**." 테스트셋의 1.5% 페이지에서 관측됐고 도메인 밖 문서에서는 빈도가 올라간다. 특히 **"비라틴 문자 언어는 즉시 반복을 유발한다"**고 명시한다.[^nougatrep] 한국어 문서를 다룬다면 이 문장을 그냥 넘기면 안 된다.

즉 VLM 직접 처리 설계에서 **반복 감지와 재시도 루프는 선택이 아니라 필수**다.

**(2) "JSON 스키마를 강제하면 안전하다"는 통념은 틀렸다.**

구조화 출력을 강제하는 게 안전장치라고 흔히 생각한다. olmOCR 논문은 정반대를 보고한다 — "시퀀스를 특정 스키마로 강제 디코딩하도록 설계된 오픈소스 도구들이 신뢰할 수 없으며, **모델이 기대하는 것과 조금만 어긋난 스키마를 강제해도 생성이 도메인 밖으로 벗어나거나 반복으로 붕괴**할 수 있다"는 것이다.[^olmschema] 같은 논문이 재시도의 대가도 적어뒀다. 재시도가 잦으면 전체 처리량이 크게 떨어진다.[^olmretry]

**(3) 컨텍스트를 늘리면 좌표가 깨진다 — Qwen 공식 자백.**

긴 문서를 한 번에 넣으려고 컨텍스트를 32,768 토큰 이상으로 확장하는 YaRN rope_scaling에 대해, Qwen2.5-VL 공식 리포는 이렇게 적는다. "다만 이 방법은 **시간적·공간적 위치추정 과제의 성능에 상당한 영향을 미치므로 사용을 권장하지 않는다.**"[^qwenyarn] **"긴 문서 + 좌표"를 동시에 요구하는 설계는 벤더가 권장하지 않는 경로다.**

**(4) 문자를 읽는 게 아니라 단어를 추측한다.**

OCRBench 논문의 실험 하나가 이걸 정면으로 보여준다. 각 단어의 **글자 순서를 뒤섞자** VLM들의 정확도가 평균 **57.0% 떨어졌다.** 같은 조건에서 전통적인 장면 텍스트 인식 SOTA 모델은 **약 4.6%만** 떨어졌다.[^ocrbnst] 해석은 하나뿐이다 — VLM은 글자를 하나씩 읽는 게 아니라 **언어모델의 사전지식으로 "그럴듯한 단어"를 복원하고 있다.** 그래서 사전에 없는 문자열, 즉 **고유명사·계좌번호·사업자등록번호·제품 코드값이 위험 구간**이다. 정확히 우리가 OCR로 뽑고 싶어 하는 것들이다.

같은 논문에 더 무서운 관찰이 있다. **이미지에 있는 텍스트 그대로 답하라고 명시적으로 요청해도** Gemini가 "02/02/2018"을 일관되게 "2 February 2018"로 해석해 내놓았다는 것이다.[^ocrbverbatim] 정산·회계처럼 원문 문자열 보존이 요구되는 도메인에서는 그 자체로 사고다.

**(5) 회전과 저빈도 텍스트.**

OCRBench v2는 DocVQA 이미지를 회전시키자 InternVL3-14B의 성능이 **90.9%에서 35.2%로, 55.7%p 떨어졌다**고 보고한다. 같은 모델이 고빈도 텍스트에서 79.1%인데 저빈도 텍스트에서는 46.7%로 떨어진다.[^ocrb2find] 스캐너에서 뒤집혀 들어온 페이지 한 장이 이 정도 차이를 만든다.

여기서 국내 설계에 결정적인 문장이 하나 나온다. **OpenAI가 공식 문서에 한국어를 직접 취약 언어로 지목해 뒀다.** "**Non-English:** 모델은 일본어나 한국어 같은 비라틴 알파벳 텍스트가 있는 이미지를 다룰 때 최적으로 동작하지 않을 수 있다." 같은 목록에 회전 텍스트 오독, 정밀한 공간 위치추정의 어려움, 작은 글씨 문제가 함께 적혀 있다.[^oailimits] Anthropic도 같은 성격의 한계를 공식 문서에 적는다 — 저품질·회전·200픽셀 미만의 아주 작은 이미지에서 환각하거나 실수할 수 있고, **"좌표와 위치추정 출력은 근사값"**이며, "특히 고위험 용도에서는 항상 주의 깊게 검토·검증하라"고 한다.[^claudelimits]

### 2-5. 좌표(bounding box) — VLM 접근의 가장 큰 구멍

1장에서 좌표 필요 여부를 네 축 중 하나로 꼽은 이유가 여기 있다. **VLM은 "답이 대충 어디 있는지는 알지만 정확히 짚지는 못한다."** 그리고 이걸 보여주는 숫자 한 쌍이 있다.

OCRBench v2 저자들의 보고다. InternVL3-14B는 위치 정보를 포함한 VQA 과제에서 **응답 정확도 78.3%**를 내는데, 같은 과제에서 **답이 있는 영역의 IoU 점수는 12.9%**다. 저자들의 해석 그대로 — "LMM이 답이 어디 있는지 대략은 식별할 수 있지만 정확한 영역을 출력하는 데는 어려움을 겪는다."[^ocrb2iou]

공식 리더보드의 Text Spotting(텍스트와 위치를 동시에 맞히는 과제) 열은 더 극적이다. 2025.06 비공개 세트 영문 기준으로, 종합 점수는 40~50점대로 비슷한 모델들의 Spotting 점수가 이렇게 갈린다.[^ocrb2lb]

| 모델                | Average | Spotting |
| ------------------- | ------- | -------- |
| GPT-4o              | 47.6    | **0.0**  |
| InternVL3-8B        | 45.3    | 0.2      |
| Qwen2-VL-7B         | 42.3    | 1.5      |
| Claude3.5-sonnet    | 47.5    | 2.5      |
| Gemini1.5-Pro       | 51.6    | 6.6      |
| Nemotron-Nano-VL-8B | 56.4    | **68.6** |

0.0에서 68.6까지다. **좌표 능력은 "VLM 일반의 능력"이 아니라 모델 개별 속성이다.** 최신 회차에서는 크게 개선됐지만(Gemini 3 Pro Preview: Average 63.4 / Spotting 80.8) 같은 표에서 Gemini-2.5-Pro는 Spotting 13.4다.[^ocrb2lb] "요즘 모델은 다 된다"고 뭉뚱그리면 사실오류다.

여기에 세 가지 함정이 더 붙는다.

**모델마다 좌표계가 다르고, 같은 벤더의 다음 세대에서도 바뀐다.** Qwen2-VL은 [0,1000) 정규화 좌표를 `<|box_start|>` 토큰으로 감쌌고,[^qwen2coord] Qwen2.5-VL은 **절대 픽셀로 바꿨다** — "정규화하는 기존 방식과 달리 입력 이미지의 실제 크기를 직접 쓴다. 상대 좌표는 이미지 안 객체의 원래 크기와 위치를 효과적으로 표현하지 못한다"는 이유였다.[^qwen25coord] 그런데 **Qwen3-VL은 다시 상대 좌표로 돌아갔다.**[^qwen3coord] InternVL은 0~1000 정규화(공식 평가 스크립트가 `/1000` 후처리를 한다),[^ivlcoord] DeepSeek-OCR과 Florence-2도 1000 bin이다. **모델 교체가 곧 좌표 파서 교체**라는 뜻이다.

**좌표 점수는 프롬프트 포맷에 크게 좌우된다 — 그리고 두 공식 출처가 정반대를 권장한다.** OCRBench v2 운영진은 Qwen2.5-VL에 그 모델이 학습된 절대좌표 포맷(`{"bbox_2d": [...], "text_content": "..."}`)으로 프롬프트를 바꾸자 Spotting 점수가 공개 데이터에서 **51.6까지 올랐다**고 공지했다.[^ocrb2prompt] 그런데 벤치마크의 표준 프로토콜 자체는 [0,1000] 정규화다.[^ocrb2norm] 반대로 **Anthropic은 정규화 좌표를 명시적으로 비권장한다** — "Claude는 절대 픽셀 좌표에서 가장 잘 동작한다. 명시적으로 요청하라… `0에서 1000 사이의 bounding box 좌표를 반환하라` 같은 정규화 좌표를 요구하면 잘 동작하지 않는다."[^claudecoord] 리더보드의 좌표 점수는 모델 능력이 아니라 **"모델 × 프롬프트 규약" 조합의 점수**다.

**좌표를 받아도 원본에 되돌려 붙이는 게 별개의 문제다.** Anthropic 문서는 반환 좌표가 "Claude가 리사이즈한 뒤의 이미지 기준 픽셀 위치"라고 밝힌다. 130 DPI로 스캔한 A4는 1075×1520인데 양변이 1568px 미만인데도 2145 비주얼 토큰이 들어 924×1307로 리사이즈된다. 게다가 패딩이 28의 배수로 붙으므로 **"패딩된 크기가 아니라 리사이즈된 크기로 환산하라"**고 경고한다.[^claudecoord] 결정적으로 — **"PDF 지원에서는 페이지가 서버 측에서 여러분이 제어할 수 없는 크기로 래스터화되므로, 반환된 좌표를 페이지에 신뢰성 있게 되돌려 매핑할 수 없다."**[^claudecoord] 즉 **PDF를 그대로 넣고 좌표를 받는 설계는 공식적으로 불가능하다고 문서화돼 있다.** 좌표가 필요하면 클라이언트가 직접 래스터화해야 한다.

그래서인지, **좌표를 잘 내는 쪽은 대체로 "좌표 전용 단계"를 따로 둔다.** PaddleOCR-VL은 이름만 VLM이지 내부는 파이프라인이다 — 먼저 레이아웃 검출과 읽기 순서 예측으로 좌표를 얻고, 그 위치로 요소를 잘라 0.9B 인식 모델에 넣는다. 저자들은 이 구조가 "grounding과 시퀀스 출력에 의존하는 멀티모달 방식(예: MinerU2.5, Dolphin)에 비해 추론이 빠르고 학습 비용이 낮으며 새 레이아웃 범주로 확장하기 쉽다"고 밝힌다.[^ppvlpipe] olmOCR은 아예 좌표를 **출력이 아니라 입력으로** 받는다 — PDF 바이너리에서 뽑은 위치 정보를 페이지 이미지와 함께 넣는 document-anchoring 방식이다.[^olmanchor] GOT-OCR2.0도 좌표는 관심영역 지정용 입력이다.[^gotbox] 반대로 dots.ocr는 블록별 `[x1,y1,x2,y2]`를 단일 JSON으로 출력하고,[^dotsjson] DeepSeek-OCR은 `<|grounding|>` 프롬프트를 줄 때만 선택적으로 낸다.

**"VLM 직접 처리"라는 분류 자체를 조심해야 한다는 뜻이다.** 좌표가 필요하면 후보를 "좌표를 출력하는 모델"로 먼저 거른 다음, 그 좌표계가 무엇인지 확인해야 한다.

### 2-6. 오픈 VLM 라이선스 — 여기가 진짜 지뢰밭이다

2-3절의 LayoutLMv2/v3 함정은 예고편이다. 자가호스팅 상용화를 검토한다면 HF 프론트매터와 raw LICENSE를 직접 읽어야 한다. 확인한 결과는 이렇다.

**Qwen2.5-VL은 같은 세대 안에서 크기별로 라이선스가 다르다.**

| 모델                        | 라이선스                                    | 상용                               |
| --------------------------- | ------------------------------------------- | ---------------------------------- |
| Qwen2.5-VL-**3B**-Instruct  | `qwen-research` (`license:` 키 자체가 없음) | **불가 (연구·평가 전용)**          |
| Qwen2.5-VL-**7B**-Instruct  | Apache-2.0                                  | 가능                               |
| Qwen2.5-VL-**72B**-Instruct | `other` / `qwen`                            | 조건부 (MAU 1억 초과 시 별도 허가) |
| Qwen3-VL 2B/8B/235B-A22B    | Apache-2.0                                  | 가능                               |

**가장 만만해 보이는 3B가 유일하게 상용으로 못 쓰는 크기다.** LICENSE 원문이 "Qwen RESEARCH LICENSE AGREEMENT"이고 "'Non-Commercial'은 연구 또는 평가 목적만을 의미한다", "상업적으로 사용하려면 우리에게 라이선스를 요청해야 한다"고 적혀 있다.[^qwen3blic] PoC를 3B로 돌려보고 그대로 운영에 올리는 흐름이 자연스럽기 때문에 특히 위험하다. 72B는 MAU 1억 초과 시 별도 허가에 더해 **"Built with Qwen" 표기 의무**가 붙는다.[^qwen72blic] Qwen3-VL 세대에서는 이 분화가 해소돼 전부 Apache-2.0이다.[^qwen3vllic]

**MinerU2.5는 AGPL-3.0이다.**[^minerulic] 네트워크 서비스로 제공하면 소스 공개 의무가 붙는 copyleft다. SaaS 설계에서 가장 위험한 항목인데, 모델 성능만 보고 고르면 놓친다.

**GOT-OCR2.0은 실제 라이선스 문서가 없다.** GitHub 리포에 LICENSE 파일이 없고 GitHub API의 `license` 필드가 `null`이다. README의 코드 라이선스 배지 링크는 자기 프로젝트가 아니라 **stanford_alpaca의 LICENSE 파일**을 가리킨다.[^gotlic] HF 태그만 보고 "Apache-2.0"이라고 단정하면 안 된다.

**InternVL3-8B는 카드 안에서 값이 서로 모순된다.** 프론트매터 `license: apache-2.0`, `license_name: qwen`, `license_link`는 Qwen2.5-72B의 LICENSE, 그런데 본문은 "This project is released under the MIT License"라고 적는다.[^ivl3lic] 네 값이 다르고 어느 것이 유효한지 1차 출처만으로 확정할 수 없다. **상용 자가호스팅 전 별도 문의가 필요하다.** InternVL3-78B는 `license: other` / `license_name: qwen`으로 **대형 모델에만 Qwen 라이선스가 전이된다.**[^ivl378lic] InternVL3.5는 Qwen3 베이스로 정리돼 일관되게 Apache-2.0이다.[^ivl35lic]

문서 전용 오픈모델 쪽은 상대적으로 깨끗하다 — dots.ocr(MIT),[^dotslic] PaddleOCR-VL(Apache-2.0),[^ppvllic] DeepSeek-OCR(MIT),[^dsocrlic] olmOCR 2(Apache-2.0),[^olmlic] Florence-2(MIT)[^flolic]는 코드와 가중치 라이선스가 일치한다.

### 2-7. 그래서 VLM이 파이프라인보다 나은가 — 답할 수 없다

**단일 방향의 우열 결론을 뒷받침하는 1차 출처를 찾지 못했다.** 그리고 이건 조사가 부족해서가 아니다. 파이프라인과 VLM을 같은 자로 재는 벤치마크(OmniDocBench, CVPR 2025)가 **스스로 문서 유형에 따라 강약이 뒤집힌다고 밝히고 있다.**

저자들의 Discussion 원문 요지는 이렇다. 범용 VLM은 학술 논문 같은 표준 문서에서는 전용 파이프라인·전문 모델에 뒤처지지만, **노트 같은 비정형 포맷에 더 잘 일반화하고 흐릿한 스캔 같은 열화 조건에서 더 강건하다.** 반대로 **신문처럼 텍스트 밀도가 높은 문서에서는 입력 해상도와 토큰 길이 한계 때문에 고전하는데,** 파이프라인 도구는 레이아웃 기반 분할로 요소를 하나씩 처리하므로 복잡한 레이아웃에서 정확도를 유지한다.[^odbdisc] 같은 절에 "대부분의 VLM이 신문을 다룰 때 인식에 실패한다", "범용 VLM은 텍스트 회전이나 혼합 언어 시나리오를 잘 처리하지 못한다"는 관찰도 있다.[^odbdisc]

같은 벤치마크 Table 3의 문서 유형별 텍스트 인식 편집거리(낮을수록 좋음)를 보면 뒤집힘이 눈에 보인다.[^odbtab3]

| 문서 유형       | MinerU(파이프라인) | GPT-4o | Qwen2-VL-72B |
| --------------- | ------------------ | ------ | ------------ |
| **신문**        | **0.171**          | 0.751  | 0.676        |
| **손글씨 노트** | 0.984              | 0.607  | **0.168**    |
| **슬라이드**    | 0.124              | 0.163  | **0.061**    |

**같은 지표, 같은 벤치마크, 문서 유형만 바꿨는데 최고와 최저가 자리를 바꾼다.** 신문에서 5.7배 앞서던 파이프라인이 손글씨 노트에서는 5.9배 뒤진다. 이것이 이 글이 "제품 순위표"를 만들지 않는 이유의 가장 단단한 근거다.

장문서 벤치마크(MMLongBench-Doc, NeurIPS 2024)도 비슷한 결을 보고한다. 평균 47.5페이지 문서 135건에서 최고 성능 모델 GPT-4o가 F1 **44.9%**에 그쳤고, **GPT-4o와 GPT-4V를 제외한 12개 LVLM이 "손실 있게 파싱된 OCR 문서를 넣은 LLM 대조군보다도 못한 성능을 보였다.**"[^mmlbresult] 다만 이 실험은 47.5페이지를 **1~5장 이미지로 이어붙여 넣은 조건**이라[^mmlbsetup] 오늘날의 100~600페이지 API 한도와 전제가 다르다. "VLM은 장문서에 약하다"의 일반 근거로 쓰면 안 된다. 이 논문도 문서 유형별로 갈린다고 적는다 — OCR을 붙인 LLM이 산업 문서·학술 논문·브로슈어에서 대등하거나 더 낫고, 엔드투엔드 LVLM은 튜토리얼·연구 보고서·가이드라인에서 앞선다.[^mmlbtype]

### 2-8. 벤치마크 점수를 인용하기 전에 알아야 할 것

위에서 숫자를 여럿 인용했으니, 그 숫자들이 무엇을 재는지도 밝혀야 공정하다. **문서 벤치마크의 채점 방식은 생각보다 관대하다.**

**DocVQA는 애초에 OCR 오류를 봐주도록 설계됐다.** 논문이 직접 적는다 — "완벽한 OCR은 없으므로, OCR 오류에서 비롯된 사소한 답 불일치가 심하게 감점되지 않도록 ANLS를 주 평가 지표로 제안한다."[^docvqaanls] ANLS는 편집거리 기반 유사도이고 **0.5 미만이면 부분점수 없이 0점**이 되는 임계값을 쓴다.[^anlsdef] 그리고 DocVQA는 "이미지 안 텍스트를 그대로 뽑아 답하는" 추출형 과제로 정의돼 있다.[^docvqaext] 즉 DocVQA 90점대는 "이 모델이 문서를 이해한다"가 아니라 "관대한 지표에서 추출형 QA를 잘한다"에 가깝다.

**OCRBench v1은 더 관대하다.** 채점 기준이 정답 문자열이 모델 출력에 **포함되는지 여부**다. 논문이 그 이유를 밝힌다 — LMM 출력에는 설명이 많이 섞이므로 exact match나 ANLS가 적합하지 않다는 것. 오탐을 줄이려고 4자 미만 정답은 아예 제외했다.[^ocrbscore] **장황하게 답할수록 유리한 채점이다.** 게다가 논문 Table 4의 수치들은 자체 측정이 아니라 "다른 논문들에서 가져온 것"이라고 캡션에 적혀 있다.[^ocrbsrc]

**OCRBench v2는 과제마다 지표가 다르다** — 표 파싱은 TEDS, 텍스트 참조는 IoU, 키 정보 추출은 F1, 계산 과제는 L1 거리, 일반 VQA는 짧은 답이면 포함 여부·5단어 이상이면 ANLS다.[^ocrb2metric] **"OCRBench v2 점수"를 단일 숫자로 인용하면 무엇을 인용한 건지 알 수 없다.** 참고로 저자들의 총평은 "대부분의 LMM이 100점 만점에 50점 미만"이다.[^ocrb2abs]

마지막으로 **벤더 자체 비교표를 인용하면 안 되는 이유를 벤더가 직접 써 뒀다.** Qwen3-VL 논문은 이렇게 적는다 — "자원과 API 제약으로 평가 시 사용한 입력 프레임 수가 제한되었기 때문에(Gemini 2.5 Pro 512, GPT-5 256, Claude Opus 4.1 100) **우리의 비교가 완전한 공정성을 보장할 수 없다는 점을 밝혀 둔다.**"[^qwen3fair] 벤더 표의 경쟁사 점수는 그 벤더가 그 조건에서 잰 값이다.

## 3. 한국어라서 생기는 문제

영어권에서 설계된 인식기를 그대로 가져오면 한국어에서 먼저 부딪히는 게 **출력 클래스 수**다.

유니코드 Hangul Syllables 블록은 U+AC00–U+D7AF지만, 실제로 배정된 음절은 U+AC00–U+D7A3의 **11,172자**다.[^ucdblocks][^ucddata] 블록 크기(11,184)와 배정 수(11,172)가 다르다는 것도 사소하지만 알아둘 값이다. 11,172 = 초성 19 × 중성 21 × 종성 28이다.

문제는 이게 인식기 마지막 층의 분류 클래스 수가 된다는 점이다. 알파벳 26자를 전제로 만든 구조에 클래스가 400배 넘게 들어간다. 게다가 실제 문서에서 글자 빈도는 극단적으로 치우쳐 있어서, 드문 글자는 학습 데이터에 거의 안 나온다.

해법으로 제안된 게 **자소 분해**다. 한글 11,172자는 자소 52개의 조합으로 표현되므로, 인식 타깃을 음절에서 자소로 바꾸면 11,172 클래스 분류 문제가 52 클래스 문제로 바뀐다.[^grapheme] 효과가 수치로 보고돼 있는데, 클래스 불균형 지표인 Gini 계수가 0.8644에서 0.6687로 내려가고, **학습 때 한 번도 보지 못한 글자에 대한 정확도가 0.0%에서 73.6%로 올라간다.**[^grapheme] 음절 단위로 학습하면 못 본 글자는 원리적으로 맞힐 수가 없지만, 자소 단위면 조합으로 도달할 수 있기 때문이다.

한국어 학습 데이터는 AI Hub가 사실상 유일한 공개 대규모 출처다. 「한국어 글자체 이미지」는 2019년 구축으로 현대 한글 11,172자를 폰트 50종으로 커버하고 총 600만 규모다.[^aihub81] 구축 사유부터가 "공개된 한국어 글자체 데이터셋이 없어 기관, 기업의 연구개발에 어려움이 있음"이었다.[^aihub81] 그 밖에 「야외 실제 촬영 한글 이미지」 50만 장,[^aihub105] 「공공행정문서 OCR」 90만 장 / 2,500만 단어,[^aihub88] 「다양한 형태의 한글 문자 OCR」 117만여 건이 있다.[^aihub91]

**라이선스는 반드시 등급을 구분해서 읽어야 한다.** 위 OCR 데이터셋들이 속한 「지능정보산업 인프라 조성」 사업 데이터는 "영리적・비영리적 연구・개발 목적으로 활용할 수 있"다.[^aihubpolicy] 다만 같은 문서가 조건도 함께 건다 — 용도는 "인공지능 학습모델의 학습용으로만", 데이터 자체의 판매 등 상업적 이용은 수행기관과 별도 협의, 제3자 재배포 금지, **국외 반출과 국외 소재 법인의 이용은 별도 합의 필요.**[^aihubpolicy] 마지막 항목은 해외 클라우드에서 학습을 돌릴 계획이라면 먼저 확인해야 할 부분이다. 「공공행정문서 OCR」은 아예 "내국인만 데이터 신청이 가능"하다.[^aihub88]

그리고 같은 정책 페이지 안에서도 **타 기관 제공 데이터는 "비상업적인 목적의 연구나 개발에만" 쓸 수 있다고 따로 규정한다.**[^aihubpolicy] "AI Hub 데이터는 상업적으로 쓸 수 있다"고 뭉뚱그리면 사실오류가 된다.

## 4. 평가 — 무엇을 정확도라고 부를 것인가

계약서에 "정확도 95% 이상"이라고 적기 전에 정의부터 맞춰야 한다. OCR의 정확도는 단일 숫자가 아니다.

**CER(Character Error Rate)** 은 편집거리 기반으로 정의된다. `CER = (i + s + d) / n`, 여기서 n은 전체 문자 수, i·s·d는 정답 텍스트를 OCR 출력으로 바꾸는 데 필요한 최소 삽입·대치·삭제 횟수다.[^cer] 이 계보는 Stephen V. Rice의 박사학위논문으로 거슬러 올라간다.[^cer] **WER(Word Error Rate)** 도 같은 구조로, NIST 공식 평가계획서는 삭제+삽입+대치 오류의 합을 정답 단어 수로 나눈 값으로 정의한다.[^wer] 참고로 NIST sclite의 기본 정렬 비용은 correct/insertion/deletion/substitution = 0/3/3/4다 — 대치를 삽입·삭제보다 무겁게 본다.[^sclite]

검출 쪽은 완전히 다른 지표를 쓴다. ICDAR 2015 Robust Reading은 IoU 0.5 초과 + 단어 단위를 기준으로 하고,[^icdar15] ICDAR2019 MLT는 Hmean(F-measure)에 IoU 50% 기준을 쓴다.[^mlt] 즉 **"정확도"라는 한 단어 안에 인식 오류율과 검출 F1이 섞여 있다.** 어느 쪽을 말하는지 합의하지 않으면 검수 단계에서 반드시 분쟁이 난다.

국내 공공사업의 합격선이 실제로 어떻게 잡히는지도 참고가 된다. AI Hub 「공공행정문서 OCR」의 검수 기준은 F1-Score@IoU 0.5, 기준값 0.7에 측정값 0.935였고,[^aihub88] 「다양한 형태의 한글 문자 OCR」은 F1-Score@IoU 0.8, 기준값 0.74에 측정값 0.961이었다.[^aihub91] **같은 공공 구축사업인데 IoU 임계값 자체가 다르다.** 지표 이름만 같다고 비교하면 안 된다는 뜻이다.

한 가지 정직하게 남겨둔다. 한글에서 CER을 **음절 단위로 셀지 자소 단위로 셀지**에 따라 분모가 달라지고 같은 오류가 다른 숫자로 나오는데, 이 차이를 직접 정량화한 1차 자료는 이번 조사에서 찾지 못했다. 위 자소 분해 논문은 _모델의 타깃 인코딩_ 문제를 다룬 것이지 _평가 단위_ 문제를 다룬 게 아니다. 두 논점을 섞으면 논문이 하지 않은 주장을 만들게 되므로, 여기서는 "계약 전에 세는 단위를 명시하라"까지만 말한다.

## 5. 규제 — 아키텍처를 되돌릴 수 없게 만드는 축

앞의 네 제약 중 ②가 왜 가장 무거운지는 조문을 보면 분명해진다. 이 절의 조문은 전부 법제처 원문으로 확인했다.

**고유식별정보는 원칙적으로 처리 금지다.** 개인정보 보호법 제24조 제1항은 별도 동의나 법령상 근거가 없으면 고유식별정보를 처리할 수 없다고 정하고, 제3항에서 암호화 등 안전성 확보조치를 의무화한다.[^pipa24] 범위는 시행령 제19조가 주민등록번호·여권번호·운전면허번호·외국인등록번호 4종으로 한정한다.[^pipaenf19] 더 강한 건 그다음이다 — **주민등록번호는 동의를 받아도 처리할 수 없다.** 제24조의2는 법률·대통령령 등의 구체적 근거, 급박한 생명·신체·재산 이익, 보호위 고시가 아니면 처리 자체를 금지한다.[^pipa242] 신분증 OCR을 만들면서 "동의받으면 되지 않나"로 접근하면 여기서 막힌다.

신분증 얼굴 사진도 걸린다. 특정 개인을 알아볼 목적으로 기술적 수단을 통해 생성한 신체적·생리적·행동적 특징 정보는 민감정보다.[^pipa23]

그리고 클라우드 OCR을 쓴다면 이 조문이 결정적이다. **개인정보 보호법 제28조의8 제1항은 국외 "제공(조회되는 경우를 포함한다)"을 원칙적으로 금지한다.**[^pipa288] 괄호가 핵심이다. 데이터를 해외에 저장하지 않고 API로 보내 결과만 받아와도 **조회에 해당하므로 국외 이전이다.** 동의를 받는다면 이전 항목·국가·시기·방법·이전받는 자·이용목적·보유기간·거부 방법을 모두 고지해야 한다.[^pipa288] "우린 저장 안 하니까 괜찮다"는 흔한 오해다.

저장 단계도 정해져 있다. 개인정보의 안전성 확보조치 기준 제7조 제2항은 주민등록번호·여권번호·운전면허번호·외국인등록번호·신용카드번호·계좌번호·생체인식정보 7종을 암호화해 저장하도록 한다.[^safety7] OCR로 뽑아낸 결과가 그대로 이 목록이다.

금융권이면 한 겹 더 있다. 전자금융감독규정 제15조 제1항 제5호는 전산실 정보처리시스템과 직접 접속 단말기를 외부통신망에서 **물리적으로** 분리하라고 한다.[^efs15] 클라우드에는 예외가 있는데, 제14조의2 제7항 본문이 정해진 절차를 거친 클라우드 제공자의 전산실에 대해 이 망분리 조항을 적용하지 않는다고 한다. **다만 같은 항 단서가 되돌린다** — 고유식별정보 또는 개인신용정보를 클라우드로 처리하는 경우에는 "해당 정보처리시스템을 국내에 설치하여야 한다".[^efs142]

이게 실무적으로 뜻하는 바는 명확하다. **신분증·통장 OCR을 금융 서비스에서 클라우드로 돌리려면 국내 리전이 강제된다.** 벤더가 한국어를 얼마나 잘 읽는지와 무관하게, 서울 리전에서 그 기능을 제공하지 않으면 후보에서 탈락한다. 가격 비교는 그다음 문제다.

마이데이터를 붙일 계획이라면 하나 더. 신용정보법 제33조의2 제2항 제3호는 전송요구 대상을 "개인신용정보를 기초로 별도로 생성하거나 가공한 신용정보가 아닐 것"으로 한정한다.[^cia332] **OCR로 추출·정규화한 결과는 가공된 정보이므로 전송요구 대상이 아니다.**

마지막으로 공공 조달을 노린다면 알아둘 실무 정보가 있다. 조달청 세부품명 체계에 "AI OCR"이라는 품명은 **없다.** 하드웨어 쪽에 「광학문자판독장치」(물품분류번호 43211717 / 세부품명번호 4321171701)가 있지만 등록 품목 대부분이 장표·투표지 판독기다.[^g2bcls] AI OCR 소프트웨어는 세부품명 4323269801 「인공지능(AI)소프트웨어」와 4323349901 「유틸리티소프트웨어」 아래에 등록된다.[^g2bprod] 품명을 잘못 잡으면 검색에 잡히지도 않는다.

## 6. 클라우드를 고른다면 — 가격은 마지막에 본다

상용 API 5종(Google Document AI, AWS Textract, Azure AI Document Intelligence, NAVER CLOVA OCR, Upstage Document AI)의 공식 문서를 조회일 2026-08-12 기준으로 확인했다. 결론부터 말하면 **가격표에 도달하기 전에 후보가 절반으로 줄어든다.**

### 게이트 1 — 한국어를 읽는가

AWS Textract 공식 문서는 이렇게 적는다. "Amazon Textract supports English, French, German, Italian, Portuguese, and Spanish text detection."[^textractlimits] **한국어가 없다.** 같은 페이지에 필기체는 영어만, 세로쓰기 미지원, 라틴 계열 문자셋만이라고 명시돼 있다. 한국어 문서 파이프라인에서는 여기서 끝이다 — 가격도 정확도도 볼 필요가 없다.

한 가지 단서는 Google 쪽이다. 한국어(`ko`)는 OCR·Form Parser·Layout Parser에서 지원되지만, **생성형 AI 추출은 영어만 공식 지원한다.**[^gcplang] "Document AI가 한국어를 지원한다"는 말이 기능 전체에 걸리는 게 아니다.

### 게이트 2 — 한국 리전이 있는가

5장에서 본 대로 금융권에서 고유식별정보를 클라우드로 처리하면 국내 설치가 강제된다. 그래서 리전 목록이 곧 후보 목록이 된다.

Google Document AI의 처리 리전은 멀티리전 `us`·`eu`와 단일리전 `asia-south1`(뭄바이)·`asia-southeast1`(싱가포르)·`australia-southeast1`·`europe-west2/3/4`·`northamerica-northeast1`·`us-central1`이다.[^gcpregions] **서울(`asia-northeast3`)이 없다.** 직접 확인했다. 즉 신분증 OCR을 금융 서비스에 넣는 시나리오에서 Document AI는 기능과 무관하게 탈락한다.

Azure는 Korea Central이 있고, 공식 문서가 "들어오는 데이터는 Document Intelligence 리소스가 생성된 것과 같은 리전에서 처리된다"고 명시한다.[^azureprivacy] NAVER CLOVA OCR은 "한국 리전, 일본 리전에서 서비스를 제공"한다.[^clovaoverview] Upstage는 온프레미스 배포 옵션이 있어 국외이전 문제를 아예 우회할 수 있다.[^upstagedocs] 다만 `api.upstage.ai` 자체의 처리 리전은 공식 문서에서 확인하지 못했다.

### 게이트 3 — 내 문서로 모델을 학습시키는가

여기가 가격보다 먼저 봐야 하는데 대부분의 비교글이 건너뛰는 지점이다. 네 벤더의 정책이 전부 다르다.

**Google**은 계약서에 못을 박아뒀다. "Google will not use Customer Data to train or fine-tune any AI/ML models without Customer's prior permission or instruction."[^gcpterms]

**AWS Textract는 반대로 기본값이 '사용'이다.** FAQ 원문 — 서비스 제공·유지 및 "Amazon Textract와 다른 Amazon 머신러닝/인공지능 기술의 품질 개선·개발"을 위해 입력 문서와 이미지를 저장·사용할 수 있으며, **AWS Organizations 옵트아웃 정책으로 거부해야 한다.**[^textractfaq] 같은 FAQ가 옵트아웃 전에는 콘텐츠가 다른 AWS 리전에 저장될 수 있다고도 밝힌다. 한국어 미지원으로 이미 탈락이지만, 이 구조는 다른 AWS AI 서비스에도 같은 방식으로 적용되므로 알아둘 값이다.

**Azure**는 "분석 작업 완료 후 24시간 동안 입력 데이터와 분석 결과를 저장하고, 보존 기간이 지나면 자동으로 삭제한다"고 명시한다.[^azureprivacy]

**NAVER**는 가장 강한 문구를 쓴다. "사용자가 전송한 이미지나 문서는 클라우드 상에 저장되지 않으며, 엔진 성능 개선이나 데이터를 활용한 패턴 분석의 목적으로 활용하지 않습니다. 반환되는 텍스트 결과값은 로그 데이터에 포함되지 않으며, OCR 호출 Access 이력에 대해서만 보관합니다."[^clovafaq]

**Upstage는 호출 경로별로 정책이 갈린다.** 실시간(동기) API는 메모리에서 처리하고 저장하지 않으며 학습에 쓰지 않는다. 비동기 API는 입력 최대 3일·출력 최대 30일 보관하되 학습에는 쓰지 않는다. **문제는 Playground·Demo다 — 계정 해지 시까지 보관되며 "서비스 개선과 AI R&D에 사용될 수 있다"고 적혀 있고, 공식 문서가 직접 경고한다. "Do not send production data or PII to Playground endpoints."**[^upstagedocs] 프로토타입 단계에서 실제 신분증을 Playground에 올려보는 건 흔한 일이라, 이 한 줄은 실무에서 사고로 직결된다.

### 게이트 4 — 그제서야 가격

여기서 중요한 경고를 먼저 해야 한다. **다섯 벤더의 과금 단위가 서로 달라서 숫자를 나란히 놓고 비교할 수 없다.** Google은 1,000페이지당이면서 특화 파서는 "count"당이고 1 count가 최대 10페이지다.[^gcppricing] AWS는 페이지당, Azure는 1,000페이지당, **NAVER는 호출 건당 + 월 정액**, Upstage는 페이지당이다. 통화도 USD와 KRW로 갈린다. 아래는 각 벤더 공식 가격 문서의 조회일(2026-08-12) 기준 값이며, **환산해서 비교하지 말 것.**

- **Google Document AI** — Enterprise Document OCR 1,000페이지당 $1.50(월 1,000페이지까지 무료, 500만 초과분 $0.60). Form Parser·Custom Extractor는 1,000페이지당 $30.00. 송장·영수증·신분증 등 특화 파서는 count당 $0.10이고 1 count = 최대 10페이지.[^gcppricing]
- **Azure AI Document Intelligence** (Korea Central, S0) — Read 1,000페이지당 $1.50, 1,000페이지 초과분 $0.60. Prebuilt/Layout $10.00, Custom $30.00, 애드온 $6.00. 무료 F0은 월 500페이지.[^azureprices]
- **NAVER CLOVA OCR** (VAT 별도) — General OCR 글자 추출 3원/건(월 100건 무료), 표 추출 22원/건. 표를 뽑으면 글자 추출이 같이 호출되므로 실질 25원/건이다. Document OCR(영수증·신용카드·명함·사업자등록증·신분증 5종 동일 요금)은 Basic 월 18,000원에 300건 포함, 초과 100원/건.[^clovapricing]
- **Upstage** (VAT 10% 별도) — Document OCR 페이지당 $0.0015, Document Parse Standard $0.01, Enhanced $0.03, Information Extract Standard $0.04.[^upstagepricing]

NAVER에는 구조적으로 주의할 점이 둘 있다. Free를 제외한 Template·Document OCR은 **이용량이 0이어도 월 정액이 청구되고**, CLOVA OCR은 API Gateway 사용량에 따라 별도 과금된다.[^clovapricing] 그리고 **Document OCR은 사전 신청·승인 절차가 필요하다** — "개인정보/민감 정보가 포함되어 있을 수 있어" 그렇다는 게 공식 설명이다.[^clovapricing] 일정 산정에 넣어야 한다.

동기 호출의 페이지 상한도 설계를 바꾼다. Google Enterprise Document OCR 온라인 15페이지 / 배치 500페이지,[^gcplimits] Azure S0 500MB·2,000페이지,[^azurelimits] NAVER는 PDF가 API 호출 시 최대 10페이지·Batch 최대 30페이지,[^clovageneral] Upstage는 동기 100페이지·비동기 1,000페이지다.[^upstagedocs] 수백 페이지짜리 계약서를 다룬다면 이 숫자가 곧 아키텍처(동기 처리 가능 여부, 분할 로직 필요 여부)다.

국내 문서를 다룬다면 Upstage에 하나 더 있다. 지원 포맷에 **HWP·HWPX가 명시된 유일한 곳이다.**[^upstagedocs] 공공·기업 문서가 한글 파일로 오는 환경이면 이건 정확도 이전의 문제다.

정확도는 어떤가? **다섯 벤더 어느 곳도 재현 가능한 한국어 벤치마크 수치를 공식 문서에 게시하지 않는다.** 중립 제3자 헤드투헤드도 확인하지 못했다. 그래서 이 글은 정확도 순위를 매기지 않는다 — **PoC로 직접 재보는 것 외에 방법이 없다.** 다만 위 게이트를 통과한 후보만 재면 되므로, 대개 두세 개로 줄어 있을 것이다.

## 7. 그래서 어떻게 고르는가

앞의 제약을 순서대로 통과시키면 후보가 줄어든다. 순서가 중요하다 — **되돌리기 어려운 제약부터** 본다.

**1단계 — 고유식별정보를 다루는가.** 신분증·통장·건강보험증이면 국외 이전 문제가 걸린다(5장). 금융권이면 국내 설치가 강제된다. 여기서 걸리면 남는 건 **온프레미스 오픈소스**, **국내 리전 상용 API**, **온프레미스 지원 벤더** 셋뿐이다. 이 판단을 나중으로 미루면 아키텍처를 통째로 갈아야 한다.

**2단계 — 좌표가 필요한가.** 사람이 검수 화면에서 "이 값이 원본 어디서 왔는지" 봐야 한다면, 좌표를 못 주거나 못 되돌리는 방식은 탈락이다. 특히 **PDF를 그대로 넣고 좌표를 받는 설계는 Anthropic 기준 공식적으로 불가능**하다(2-5). 이 요구가 있으면 전통 파이프라인이나 좌표 출력 모델(dots.ocr, PaddleOCR-VL)로 좁혀진다.

**3단계 — 문서가 정형인가.** 고정 양식이면 좌표 기반 룰이 여전히 가장 싸고 정확하다. 굳이 VLM을 쓸 이유가 없다. 반정형·자유형으로 갈수록 레이아웃 모델이나 VLM 쪽 값어치가 커진다.

**4단계 — 원문 문자열을 그대로 보존해야 하는가.** 계좌번호·사업자등록번호·제품 코드처럼 사전에 없는 문자열이 핵심이면 VLM 단독은 위험하다. 글자 순서를 뒤섞으면 57% 무너진다는 실험이 그 이유다(2-4). 이 경우 VLM을 쓰더라도 **전통 OCR과 교차검증**하는 구조가 낫다.

**5단계 — GPU가 있는가.** 없으면 자체 VLM 서빙은 사실상 빠진다. CPU에서 현실적인 건 Tesseract·PaddleOCR·EasyOCR 계열이다. 내 클러스터가 여기다.

**6단계 — 상용 배포인가.** 그제서야 라이선스를 본다. LayoutLMv2/v3 가중치(CC BY-NC-SA), Qwen2.5-VL-3B(연구 전용), MinerU2.5(AGPL-3.0)가 여기서 걸린다.

가격은 그다음이다. 대부분의 경우 여기까지 오면 후보가 두세 개밖에 안 남아서, **PoC로 직접 재보는 게 비교표를 읽는 것보다 빠르다.** 그리고 그게 유일하게 신뢰할 수 있는 방법이다 — 중립 벤치마크가 없으니까.

한 가지 덧붙이면, 이 글의 어떤 절도 "하나만 골라라"라고 말하지 않는다. 실제로 잘 도는 구조는 대개 혼합이다. 정형 구간은 룰, 자유형 구간은 모델, 저신뢰 구간은 사람. **OmniDocBench가 문서 유형별로 순위가 뒤집힌다고 밝힌 이상**(2-7), 문서 유형이 섞인 파이프라인에서 단일 엔진을 고집할 근거가 없다.

## 8. 확인 실패 — 쓰지 못한 것들

이 글을 쓰면서 확인하려다 실패한 항목을 남긴다. 여기 적힌 건 **모르는 상태로 남겨둔 것**이지, 반대로 입증된 게 아니다.

- **중립 제3자 헤드투헤드 벤치마크를 끝내 찾지 못했다.** Tesseract·PaddleOCR·EasyOCR·상용 API를 같은 조건에서 비교한 독립 평가를 확인하지 못했다. 이 글이 순위표를 만들지 않는 이유이자, 이 글의 가장 큰 한계다.
- **상용 API 5종 중 어느 곳도 재현 가능한 한국어 정확도 수치를 공식 문서에 게시하지 않는다.** 그래서 정확도 비교를 쓰지 않았다.
- **KS X 1001의 한글 음절 2,350자라는 널리 알려진 숫자를 표준 원문에서 확인하지 못했다.** 표준 본문 자체를 회수하지 못해 2차 출처만 있었고, 규칙상 인용하지 않았다.
- **음절 단위 CER과 자소 단위 CER의 분모 차이를 정량화한 1차 출처를 찾지 못했다.** 한국어 CER이 계산 단위에 따라 달라진다는 건 정의상 자명하지만, 그 격차를 수치로 밝힌 1차 출처는 확보하지 못했다.
- **OmniDocBench는 arXiv v3와 CVPR 카메라레디의 수치가 다르다.** 이 글은 CVPR 카메라레디 값을 인용했다. 같은 표를 다른 판본에서 보면 숫자가 다를 수 있다.
- **OmniDocBench 공식 리더보드는 계속 갱신된다.** 인용한 순위·점수는 조회 시점(2026-08-12) 기준이다.
- **OCRBench v1 공식 리더보드의 백업 데이터는 2025-06-23 이후 갱신이 멈춰 있다.** 최신 모델의 OCRBench v1 점수는 리더보드 등재값이 아니라 각 벤더 자체 보고치다. OCRBench 논문 자신도 표의 수치가 다른 논문들에서 가져온 것이라고 밝힌다.
- **InternVL3의 라이선스는 1차 출처 안에서 서로 모순된다.** 프론트매터·`license_name`·`license_link`·본문 네 값이 다르다. 상용 자가호스팅 전 별도 문의가 필요하다.
- **GOT-OCR2.0의 실제 라이선스를 확정하지 못했다.** 리포에 LICENSE 파일이 없다.
- **AWS Textract 가격은 Price List API 응답의 `publicationDate`가 2024-10-29였다.** 최신이 아닐 수 있다. 다만 한국어 미지원으로 이미 후보에서 빠지므로 결론에 영향은 없다.
- **Azure와 NAVER의 가격은 렌더된 가격 페이지가 아니라 공식 가격 API 응답에서 얻었다.** 표시 가격과 다를 수 있다.
- **Upstage의 클라우드 처리 리전은 공식 문서에서 확인하지 못했다.** 온프레미스 옵션이 있다는 것만 확인했다.
- **Qwen2.5-VL 공식 리포의 YaRN 경고 문장은 현재 `main` 브랜치 README에 없다.** 해당 README가 Qwen3-VL 내용으로 교체됐기 때문이며, 이 글은 커밋 고정 URL로 인용했다.
- **조사한 VLM 논문 12편 어디에도 "Limitations" 제목의 절이 없다.** 따라서 어떤 모델에 대해서도 "논문에 Limitations 섹션이 있다"고 쓰지 않았다.

마지막으로 **면책 하나.** 이 글은 어떤 제품이 다른 제품보다 정확하다고 주장하지 않는다. 그럴 근거가 없기 때문이다. 확인한 건 **무엇이 어떤 제약에서 탈락하는가**뿐이고, 탈락하지 않은 후보들 사이의 우열은 각자의 문서로 재봐야 한다.

## References

[^tessquality]: Tesseract 공식 문서, _Improving the quality of the output_ — <https://github.com/tesseract-ocr/tessdoc/blob/main/ImproveQuality.md>

[^tessfaq]: Tesseract 공식 FAQ — <https://github.com/tesseract-ocr/tessdoc/blob/main/FAQ.md>

[^tessrel]: Tesseract 릴리스 (GitHub Releases API, `tag_name: 5.5.3`, `published_at: 2026-07-24`) — <https://api.github.com/repos/tesseract-ocr/tesseract/releases/latest>

[^tess4]: Tesseract README 및 4.0.0 릴리스(2018-10-29) — <https://github.com/tesseract-ocr/tesseract>

[^tesslic]: Tesseract LICENSE (Apache-2.0) — <https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE>

[^tessdata]: tessdata README ("All data in the repository are licensed under the Apache-2.0 License") — <https://github.com/tesseract-ocr/tessdata>

[^crnn]: Shi, Bai, Yao, _An End-to-End Trainable Neural Network for Image-based Sequence Recognition and Its Application to Scene Text Recognition_, arXiv:1507.05717 — <https://arxiv.org/abs/1507.05717>

[^dbnet]: Liao et al., _Real-time Scene Text Detection with Differentiable Binarization_, arXiv:1911.08947 (AAAI 2020) — <https://arxiv.org/abs/1911.08947>

[^paddlerel]: PaddleOCR 릴리스 v3.7.0 (2026-06-11) — <https://github.com/PaddlePaddle/PaddleOCR>

[^paddlelic]: PaddleOCR LICENSE (Apache-2.0) — <https://github.com/PaddlePaddle/PaddleOCR>

[^ppocr]: Du et al., _PP-OCR: A Practical Ultra Lightweight OCR System_, arXiv:2009.09941 — <https://arxiv.org/abs/2009.09941>

[^paddlepipe]: PaddleOCR 3.x 공식 문서, General OCR Pipeline — <https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/OCR.en.md>

[^paddlekor]: `PaddlePaddle/korean_PP-OCRv5_mobile_rec` 모델카드 (벤더 자체 측정) — <https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec>

[^easyarch]: EasyOCR README — <https://github.com/JaidedAI/EasyOCR>

[^easycfg]: EasyOCR `easyocr/config.py` — <https://github.com/JaidedAI/EasyOCR>

[^easyrel]: EasyOCR 릴리스 v1.7.2 (2024-09-24) — <https://github.com/JaidedAI/EasyOCR>

[^easyroad]: EasyOCR README, "What's coming next" — <https://github.com/JaidedAI/EasyOCR>

[^donut]: Kim et al., _OCR-free Document Understanding Transformer_, arXiv:2111.15664 (ECCV 2022) — <https://arxiv.org/abs/2111.15664>

[^donutlic]: Donut LICENSE (MIT, NAVER Corp.) — <https://github.com/clovaai/donut>

[^donutw]: `naver-clova-ix/donut-base` 모델카드 (`license: mit`) — <https://huggingface.co/naver-clova-ix/donut-base>

[^lmv1]: Xu et al., _LayoutLM: Pre-training of Text and Layout for Document Image Understanding_, arXiv:1912.13318 — <https://arxiv.org/abs/1912.13318>

[^lmv2]: Xu et al., _LayoutLMv2_, arXiv:2012.14740 — <https://arxiv.org/abs/2012.14740>

[^lmv3]: Huang et al., _LayoutLMv3_, arXiv:2204.08387 — <https://arxiv.org/abs/2204.08387>

[^lmv1w]: `microsoft/layoutlm-base-uncased` (`license: mit`) — <https://huggingface.co/microsoft/layoutlm-base-uncased>

[^lmv2w]: `microsoft/layoutlmv2-base-uncased` (`license: cc-by-nc-sa-4.0`) — <https://huggingface.co/microsoft/layoutlmv2-base-uncased>

[^lmv3w]: `microsoft/layoutlmv3-base` (`license: cc-by-nc-sa-4.0`) — <https://huggingface.co/microsoft/layoutlmv3-base>

[^trocr]: Li et al., _TrOCR_, arXiv:2109.10282 (AAAI 2023) — <https://arxiv.org/abs/2109.10282>

[^trocrhw]: `microsoft/trocr-base-handwritten` 모델카드 — <https://huggingface.co/microsoft/trocr-base-handwritten>

[^trocrpr]: `microsoft/trocr-base-printed` 모델카드 (license 필드 부재) — <https://huggingface.co/microsoft/trocr-base-printed>

[^ucdblocks]: Unicode Character Database, _Blocks.txt_ — <https://www.unicode.org/Public/UCD/latest/ucd/Blocks.txt>

[^ucddata]: Unicode Character Database, _UnicodeData.txt_ (배정된 음절 U+AC00–U+D7A3) — <https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt> / 코드차트 <https://www.unicode.org/charts/PDF/UAC00.pdf>

[^grapheme]: Kim, Son, Lee, Min, "Character decomposition to resolve class imbalance problem in Hangul OCR", arXiv:2208.06079 — <https://arxiv.org/abs/2208.06079>

[^aihub81]: AI Hub, 「한국어 글자체 이미지」 — <https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=81>

[^aihub105]: AI Hub, 「야외 실제 촬영 한글 이미지」 — <https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=105>

[^aihub88]: AI Hub, 「공공행정문서 OCR」 — <https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=88>

[^aihub91]: AI Hub, 「다양한 형태의 한글 문자 OCR」 — <https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=91>

[^aihubpolicy]: AI Hub, _데이터 이용정책_ — <https://aihub.or.kr/intrcn/guid/usagepolicy.do?currMenu=151&topMenu=105>

[^cer]: Neudecker et al., "A survey of OCR evaluation tools and metrics", HIP'21, ACM — <https://doi.org/10.1145/3476887.3476888> (PDF: <https://www.primaresearch.org/www/assets/papers/HIP21_CNeudecker_OcrEvalSurvey.pdf>)

[^wer]: NIST, _OpenASR20 Evaluation Plan v1.5_ — <https://www.nist.gov/system/files/documents/2021/08/03/OpenASR20_EvalPlan_v1_5.pdf>

[^sclite]: NIST SCTK, _sclite_ 문서 — <https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm>

[^icdar15]: ICDAR 2015 Robust Reading Competition — <https://rrc.cvc.uab.es/files/Robust_Reading_2015_v02.pdf>

[^mlt]: ICDAR2019 Robust Reading Challenge on Multi-lingual Scene Text (MLT), Tasks — <https://rrc.cvc.uab.es/?ch=15&com=tasks>

[^pipa24]: 「개인정보 보호법」 제24조 (고유식별정보의 처리 제한) — 법제처 국가법령정보센터 <https://www.law.go.kr/법령/개인정보보호법>

[^pipaenf19]: 「개인정보 보호법 시행령」 제19조 (고유식별정보의 범위) — <https://www.law.go.kr/법령/개인정보보호법시행령>

[^pipa242]: 「개인정보 보호법」 제24조의2 (주민등록번호 처리의 제한) — <https://www.law.go.kr/법령/개인정보보호법>

[^pipa23]: 「개인정보 보호법」 제23조 (민감정보의 처리 제한) — <https://www.law.go.kr/법령/개인정보보호법>

[^pipa288]: 「개인정보 보호법」 제28조의8 (개인정보의 국외 이전) — <https://www.law.go.kr/법령/개인정보보호법>

[^safety7]: 「개인정보의 안전성 확보조치 기준」 제7조 (개인정보의 암호화) — 개인정보보호위원회 고시, 법제처 <https://www.law.go.kr/행정규칙/개인정보의안전성확보조치기준>

[^efs15]: 「전자금융감독규정」 제15조 제1항 제5호 (해킹 등 방지대책) — 금융위원회 고시, 법제처 <https://www.law.go.kr/행정규칙/전자금융감독규정>

[^efs142]: 「전자금융감독규정」 제14조의2 제7항 (클라우드컴퓨팅서비스 이용절차 등) — <https://www.law.go.kr/행정규칙/전자금융감독규정>

[^cia332]: 「신용정보의 이용 및 보호에 관한 법률」 제33조의2 제2항 제3호 (개인신용정보의 전송요구) — <https://www.law.go.kr/법령/신용정보의이용및보호에관한법률>

[^g2bcls]: 조달청 나라장터 물품분류 검색 (물품분류번호 43211717 「광학문자판독장치」) — <https://goods.g2b.go.kr/search/classificationSearch.do>

[^g2bprod]: 조달청 나라장터 물품 검색 (세부품명 4323269801 「인공지능(AI)소프트웨어」, 4323349901 「유틸리티소프트웨어」) — <https://goods.g2b.go.kr/search/productSearch.do>

[^textractlimits]: AWS, _Amazon Textract — Document Limits_ (지원 언어) — <https://docs.aws.amazon.com/textract/latest/dg/limits-document.html>

[^textractfaq]: AWS, _Amazon Textract FAQs_ (데이터 저장·모델 개선 이용 및 옵트아웃) — <https://aws.amazon.com/textract/faqs/>

[^gcplang]: Google Cloud, _Document AI — Language support_ — <https://cloud.google.com/document-ai/docs/languages>

[^gcpregions]: Google Cloud, _Document AI — Regional and multi-regional support_ — <https://docs.cloud.google.com/document-ai/docs/regions>

[^gcpterms]: Google Cloud, _Service Specific Terms_ (Training Restriction) — <https://cloud.google.com/terms/service-terms>

[^gcppricing]: Google Cloud, _Document AI pricing_ — <https://cloud.google.com/document-ai/pricing>

[^gcplimits]: Google Cloud, _Document AI — Quotas and limits_ — <https://cloud.google.com/document-ai/limits>

[^azureprivacy]: Microsoft, _Data, privacy, and security for Document Intelligence_ — <https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/document-intelligence/data-privacy-security>

[^azureprices]: Microsoft, _Azure Retail Prices API_ 응답 (Korea Central, S0) — <https://prices.azure.com/api/retail/prices> / 표시 가격 <https://azure.microsoft.com/pricing/details/ai-document-intelligence/>

[^azurelimits]: Microsoft, _Document Intelligence service quotas and limits_ — <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits>

[^clovaoverview]: NAVER Cloud Platform, _CLOVA OCR 개요_ — <https://guide.ncloud-docs.com/docs/clovaocr-overview>

[^clovafaq]: NAVER Cloud Platform, _CLOVA OCR FAQ_ (데이터 저장·활용 정책) — <https://guide.ncloud-docs.com/docs/clovaocr-faq>

[^clovageneral]: NAVER Cloud Platform, _CLOVA OCR General_ (PDF 페이지 제한) — <https://guide.ncloud-docs.com/docs/clovaocr-general>

[^clovapricing]: NAVER Cloud Platform, _CLOVA OCR 상품 가격_ — <https://www.ncloud.com/product/aiService/ocr>

[^upstagedocs]: Upstage, _Document AI 공식 문서_ (지원 포맷·페이지 한도·데이터 보존 정책) — <https://console.upstage.ai/api/docs/for-agents/raw>

[^upstagepricing]: Upstage, _API Pricing_ — <https://www.upstage.ai/pricing/api>

[^ivl25rep]: Chen et al., "Expanding Performance Boundaries of Open-Source Multimodal Models" (InternVL2.5), arXiv:2412.05271 §4.3 — <https://arxiv.org/abs/2412.05271>

[^olmrep]: Poznanski et al., "olmOCR: Unlocking Trillions of Tokens in PDFs with Vision Language Models", arXiv:2502.18443 — <https://arxiv.org/abs/2502.18443>

[^olmschema]: 같은 논문 — <https://arxiv.org/abs/2502.18443>

[^olmretry]: 같은 논문 — <https://arxiv.org/abs/2502.18443>

[^olmanchor]: 같은 논문 (document-anchoring) — <https://arxiv.org/abs/2502.18443>

[^nougatrep]: Blecher et al., "Nougat: Neural Optical Understanding for Academic Documents", ICLR 2024, arXiv:2308.13418 — <https://arxiv.org/abs/2308.13418>

[^qwenyarn]: QwenLM/Qwen2.5-VL README (커밋 고정) — <https://github.com/QwenLM/Qwen2.5-VL/blob/6e98a0a62bce167c5802ae6f5f95fcd97d2634cf/README.md>

[^ocrbnst]: Liu et al., "OCRBench: on the hidden mystery of OCR in large multimodal models", Sci. China Inf. Sci. 67, 220102 (2024), arXiv:2305.07895 — <https://arxiv.org/abs/2305.07895>

[^ocrbverbatim]: 같은 논문 — <https://arxiv.org/abs/2305.07895>

[^ocrbscore]: 같은 논문 (채점 기준) — <https://arxiv.org/abs/2305.07895>

[^ocrbsrc]: 같은 논문 Table 4 캡션 — <https://arxiv.org/abs/2305.07895>

[^ocrb2find]: Fu et al., "OCRBench v2", NeurIPS 2025 D&B, arXiv:2501.00321 (Findings 3·4) — <https://arxiv.org/abs/2501.00321>

[^ocrb2iou]: 같은 논문 Finding 2 — <https://arxiv.org/abs/2501.00321>

[^ocrb2metric]: 같은 논문 (과제별 지표 정의) — <https://arxiv.org/abs/2501.00321>

[^ocrb2abs]: 같은 논문 초록 — <https://arxiv.org/abs/2501.00321>

[^ocrb2norm]: 같은 논문 (좌표 정규화 프로토콜) — <https://arxiv.org/abs/2501.00321>

[^ocrb2lb]: OCRBench v2 공식 리더보드 (2026-08-12 조회) — <https://99franklin.github.io/ocrbench_v2/>

[^ocrb2prompt]: 같은 리더보드 페이지의 운영진 공지 — <https://99franklin.github.io/ocrbench_v2/>

[^oailimits]: OpenAI, _Images and vision_ (Limitations) — <https://platform.openai.com/docs/guides/images-vision>

[^claudelimits]: Anthropic, _Vision_ (Limitations) — <https://docs.claude.com/en/docs/build-with-claude/vision>

[^claudecoord]: Anthropic, _Vision — coordinates_ — <https://docs.claude.com/en/docs/build-with-claude/vision-coordinates>

[^qwen2coord]: Wang et al., "Qwen2-VL", arXiv:2409.12191 — <https://arxiv.org/abs/2409.12191>

[^qwen25coord]: Bai et al., "Qwen2.5-VL Technical Report", arXiv:2502.13923 §2.1.2 — <https://arxiv.org/abs/2502.13923>

[^qwen3coord]: QwenLM/Qwen3-VL 공식 리포 README — <https://github.com/QwenLM/Qwen3-VL>

[^qwen3fair]: "Qwen3-VL Technical Report", arXiv:2511.21631 — <https://arxiv.org/abs/2511.21631>

[^ivlcoord]: OpenGVLab/InternVL 공식 평가 스크립트 `evaluate_grounding.py` — <https://github.com/OpenGVLab/InternVL/blob/main/internvl_chat/eval/refcoco/evaluate_grounding.py>

[^ppvlpipe]: Cui et al., "PaddleOCR-VL", arXiv:2510.14528 — <https://arxiv.org/abs/2510.14528>

[^gotbox]: Wei et al., "General OCR Theory: Towards OCR-2.0 via a Unified End-to-end Model" (GOT-OCR2.0), arXiv:2409.01704 §3.4.1 — <https://arxiv.org/abs/2409.01704>

[^dotsjson]: rednote-hilab/dots.ocr 공식 모델카드 (레이아웃 프롬프트) — <https://huggingface.co/rednote-hilab/dots.ocr>

[^qwen3blic]: Qwen2.5-VL-3B-Instruct LICENSE (Qwen RESEARCH LICENSE AGREEMENT) — <https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/main/LICENSE>

[^qwen72blic]: Qwen2.5-VL-72B-Instruct LICENSE — <https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct/blob/main/LICENSE>

[^qwen3vllic]: Qwen3-VL-8B-Instruct 모델카드 (`license: apache-2.0`) — <https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct>

[^minerulic]: MinerU2.5-2509-1.2B 모델카드 (`license: agpl-3.0`) — <https://huggingface.co/opendatalab/MinerU2.5-2509-1.2B>

[^gotlic]: Ucas-HaoranWei/GOT-OCR2.0 공식 리포 (LICENSE 파일 부재) — <https://github.com/Ucas-HaoranWei/GOT-OCR2.0>

[^ivl3lic]: InternVL3-8B 모델카드 — <https://huggingface.co/OpenGVLab/InternVL3-8B>

[^ivl378lic]: InternVL3-78B 모델카드 — <https://huggingface.co/OpenGVLab/InternVL3-78B>

[^ivl35lic]: InternVL3_5-8B 모델카드 — <https://huggingface.co/OpenGVLab/InternVL3_5-8B>

[^dotslic]: rednote-hilab/dots.ocr 공식 리포 LICENSE AGREEMENT — <https://github.com/rednote-hilab/dots.ocr>

[^ppvllic]: PaddleOCR-VL 모델카드 (`license: apache-2.0`) — <https://huggingface.co/PaddlePaddle/PaddleOCR-VL>

[^dsocrlic]: DeepSeek-OCR 모델카드 (`license: mit`) — <https://huggingface.co/deepseek-ai/DeepSeek-OCR>

[^olmlic]: olmOCR-2-7B-1025 모델카드 (`license: apache-2.0`) — <https://huggingface.co/allenai/olmOCR-2-7B-1025>

[^flolic]: Florence-2-large 모델카드 (`license: mit`) — <https://huggingface.co/microsoft/Florence-2-large>

[^odbdisc]: Ouyang et al., "OmniDocBench", CVPR 2025, arXiv:2412.07626 §5.1 Discussion — <https://arxiv.org/abs/2412.07626>

[^odbtab3]: 같은 논문 Table 3 (CVPR 카메라레디 기준) — <https://arxiv.org/abs/2412.07626>

[^mmlbresult]: Ma et al., "MMLongBench-Doc", NeurIPS 2024 D&B, arXiv:2407.01523 — <https://arxiv.org/abs/2407.01523>

[^mmlbsetup]: 같은 논문 (입력 구성 조건) — <https://arxiv.org/abs/2407.01523>

[^mmlbtype]: 같은 논문 (문서 유형별 결과) — <https://arxiv.org/abs/2407.01523>

[^docvqaanls]: Mathew, Karatzas, Jawahar, "DocVQA: A Dataset for VQA on Document Images", WACV 2021, arXiv:2007.00398 — <https://arxiv.org/abs/2007.00398>

[^docvqaext]: 같은 논문 (추출형 QA 정의) — <https://arxiv.org/abs/2007.00398>

[^anlsdef]: ST-VQA 공식 챌린지 페이지 (ANLS 정의, τ=0.5) — <https://rrc.cvc.uab.es/?ch=11&com=tasks>
