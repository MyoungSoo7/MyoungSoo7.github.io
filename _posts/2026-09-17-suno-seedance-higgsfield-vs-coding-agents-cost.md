---
layout: post
title: "Suno·Seedance·Higgsfield vs 코딩 에이전트 — 과금 모양이 다른 이유는 '검증 가능성'이다"
date: 2026-09-17 21:30:00 +0900
categories: [AI, Cost]
tags: [suno, seedance, higgsfield, codex, claude-code, pricing, benchmark, metr, swe-bench]
---

오늘(2026-09-17) 한국시각 오후 3시에 조용히 가격이 오른 게 하나 있다. BytePlus ModelArk 의 Seedance 2.5 1080p 출력이다. 8월 14일부터 걸려 있던 "정가 대비 28% 할인" 창이 **UTC+8 기준 9월 17일 14:00** 에 닫혔다[^bp-price]. 할인가는 초당 약 **USD 0.41**, 정가는 초당 **USD 0.569** 다. 같은 5초 클립이 어제 $2.05 였다가 오늘 $2.843 이 됐다. 1.39 배다.

이 글은 그 숫자를 출발점으로, 세 가지를 붙여 본다.

1. **Suno**(AI 음악)와 **Seedance**(AI 영상)는 과금 모양이 어떻게 다른가
2. **Higgsfield** 는 그 둘과 어떤 관계인가 — 결론부터: *경쟁자가 아니라 Seedance 를 되파는 층*이다
3. 이걸 **Codex·Claude Code 같은 코딩 에이전트**와 분야별로 견줄 때, 무엇이 비교 가능하고 무엇이 비교 불가능한가

먼저 사실 관계부터 정리하고, 마지막에 "왜 이렇게 생겼나"를 본다.

---

## 0. 이 글의 출처 규칙

- 가격·사양은 **벤더 공식 페이지만** 인용했다. 요약 블로그·가격 애그리게이터는 쓰지 않았다. Higgsfield 구독 가격을 두고 인터넷에 돌아다니는 숫자들은 서로 모순되는데(같은 플랜 이름조차 다르다), 그건 4장에서 따로 다룬다.
- 벤치마크는 **중립 제3자**(Artificial Analysis, SWE-bench) 와 **벤더 자체 벤치마크**를 구분해 표시했다.
- 내가 계산한 값은 "유도값"이라고 명시했고, 가능한 경우 벤더의 공식 예제와 교차 검증했다.
- 확인 못 한 숫자는 **적지 않았다.** 특히 Higgsfield 구독 가격이 그렇다.

---

## 1. Suno — 생성이 아니라 '반출'을 판다

Suno 의 공식 가격 페이지(연간 결제 기준)[^suno-pricing]:

| | Free | Pro | Premier |
|---|---|---|---|
| 가격 | $0 | **$8**/월 | **$24**/월 |
| 모델 | 무료 모델(v6-mini) | 최상위 모델(v6, v6-wild) | 최상위 모델 |
| 크레딧 | **하루 50** | **월 2,500** | **월 10,000** |
| **월 다운로드** | **없음** | **20곡** | **60곡** |
| 상업적 이용권 | **없음** | 있음 | 있음 |
| 동시 생성 | 공용 큐 4 | 우선 큐 10 | 우선 큐 10 |
| 스템 분리 | 없음 | 2종 | 3종 |
| 업로드 길이 | 8분 | 8분 | 30분 |

여기에 Suno 헬프센터의 한 줄이 결합되면 전체 그림이 나온다. **"무료 플랜은 매일 갱신되는 50 크레딧을 준다. 하루 10곡을 만들기 충분하다"**[^suno-plans]. 즉 **1곡 = 5 크레딧**이다.

이걸로 유도하면:

| | 월 생성 가능 곡수 | 생성 1건당 | 다운로드 1곡당 |
|---|---|---|---|
| Pro | 2,500 ÷ 5 = **500곡** | $8/500 = **$0.016** | $8/20 = **$0.40** |
| Premier | 10,000 ÷ 5 = **2,000곡** | $24/2000 = **$0.012** | $24/60 = **$0.40** |

두 유료 요금제의 **다운로드 1곡당 비용이 정확히 $0.40 으로 같다.** 우연이 아니다. Premier 가 Pro 보다 파는 것은 "싼 곡"이 아니라 Suno Studio·30분 업로드·고급 스템 분리 같은 *기능*이고, 곡의 단가는 건드리지 않았다.

더 중요한 건 **생성 대 다운로드 비율**이다.

$$\text{Pro} = \frac{500}{20} = 25:1 \qquad \text{Premier} = \frac{2{,}000}{60} \approx 33:1$$

요금제 설계 자체가 **"25~33번 뽑아서 1곡 건진다"** 는 히트율을 전제하고 있다. 그리고 무료 플랜은 매일 10곡을 영원히 생성할 수 있지만 **다운로드는 0곡, 상업적 권리도 없다.** Suno 가 파는 것은 계산 자원이 아니라 **결과물을 밖으로 꺼내 쓸 권리**다.

크레딧은 이월되지 않는다. 공식 문구 그대로: *"구독에 포함된 크레딧은 날짜나 달을 넘겨 이월되지 않는다. 별도 구매한 톱업 크레딧은 만료되지 않지만 사용하려면 활성 구독이 필요하다."*[^suno-pricing]

---

## 2. Seedance — 계산 자원만 판다, 대신 해상도가 제곱으로 들어온다

Seedance 는 반대편 극단이다. 다운로드 쿼터도, 권리 게이트도 없다. **토큰만 센다.** BytePlus ModelArk 공식 문서의 산식[^bp-price]:

$$\text{tokens} = \frac{(\,T_{in} + T_{out}\,) \times W \times H \times \text{fps}}{1024}$$

$$\text{price} = \text{token unit price} \times \text{tokens}$$

여기서 $T_{in}$ 은 입력 영상 길이, $T_{out}$ 은 출력 영상 길이다. 문서는 세 가지를 덧붙인다. **성공한 생성만 과금**되고(콘텐츠 검수로 실패하면 무료), **실제 소비량은 호출 후 반환되는 `usage.completion_tokens` 가 기준**이며, 2.0/2.5 계열은 **입력에 영상이 포함되면 최소 토큰 하한**이 걸린다.

24fps 기준으로 초당 토큰을 직접 계산해 보면:

| 해상도 | 픽셀 | 초당 토큰 |
|---|---|---|
| 480p (854×480) | 409,920 | 9,607.5 |
| 720p (1280×720) | 921,600 | 21,600 |
| 1080p (1920×1080) | 2,073,600 | 48,600 |

토큰 단가(USD / 1M tokens, 온라인 추론, 영상 입력 없음)[^bp-price]:

| 모델 | 480p·720p | 1080p | 4K |
|---|---|---|---|
| Dreamina Seedance 2.5 | 10.70 | 11.7 | — |
| Dreamina Seedance 2.0 | 7.0 | 7.7 | 4.0 |
| Dreamina Seedance 2.0 fast | 5.6 (25% 할인 중) | 미지원 | 미지원 |
| Dreamina Seedance 2.0 mini | 3.5 (60% 할인 중) | 미지원 | 미지원 |
| Seedance 1.5 pro | 2.4(음성) / 1.2(무음) | | |
| Seedance 1.0 pro | 2.5 | | |
| Seedance 1.0 pro fast | 1.0 | | |

교차 검증을 해 보자. 720p, Seedance 2.5, 영상 입력 없음:

$$21{,}600 \times \frac{10.70}{10^6} = \$0.23112\ \text{/sec} \;\Rightarrow\; 5\text{초} = \$1.1556$$

BytePlus 공식 예제 표의 값은 **$1.156 per video / $0.231 per second** 다. 소수 셋째 자리까지 일치한다. 1080p 도 마찬가지로 $48{,}600 \times 11.7/10^6 = \$0.56862$/초 → 5초 $2.843 로 공식 표와 정확히 맞는다. **산식과 단가를 제대로 읽었다는 증거**로 삼을 만하다.

공식 예제 표(영상 입력 없음, 16:9, 출력 5초)[^bp-price]:

| 모델 | 480p | 720p | 1080p | 4K |
|---|---|---|---|---|
| Seedance 2.5 | $0.514 ($0.103/s) | $1.156 ($0.231/s) | $2.843 ($0.569/s) | — |
| Seedance 2.0 | $0.35 ($0.07/s) | $0.76 ($0.15/s) | $1.87 ($0.37/s) | $3.89 ($0.78/s) |
| Seedance 2.0 fast | $0.28 ($0.06/s) | $0.60 ($0.12/s) | 미지원 | 미지원 |
| Seedance 2.0 mini | $0.18 ($0.04/s) | $0.38 ($0.08/s) | 미지원 | 미지원 |

**해상도가 면적으로 들어오므로 가격은 선형이 아니다.** 480p → 1080p 는 세로·가로 각각 2.25배가 아니라 픽셀 수가 5.06배이고, 2.5 기준 초당 단가는 $0.103 → $0.569 로 **5.5배**다(1080p 단가가 10.70 이 아니라 11.7 이라 5.06배보다 조금 더 튄다). 영상 쪽에서 "일단 고해상도로 뽑고 보자"가 위험한 건 이 지수 때문이다.

그리고 서두의 그 할인 창들. 문서에 명시된 조건이 셋 다 다르다[^bp-price]:

| 대상 | 기간(UTC+8) | 할인 | 적용 범위 |
|---|---|---|---|
| Seedance 2.5 1080p | 2026-08-14 14:00 → **2026-09-17 14:00** | 28% | 기업·개인 모두, 토큰 상한 없음 |
| Seedance 2.0 mini 480p·720p | 2026-08-07 → 2026-10-07 | 60% | **기업 전용**, 상한 초과 시 정가 |
| Seedance 2.0 fast 480p·720p | 2026-08-07 → 2026-10-07 | 25% | **기업 전용**, 상한 초과 시 정가 |

2.5 의 할인 창은 이 글을 쓰는 시점 기준 약 6시간 전에 닫혔다. 견적을 캐싱해 두는 파이프라인이 있다면 오늘 밤 원가가 39% 튄다.

---

## 3. 세 제품은 같은 축에 있지 않다

여기서 질문의 전제를 한 번 고쳐야 한다. "Suno vs Seedance" 는 음악 대 영상이라 **애초에 같은 축이 아니다.** 그리고 Higgsfield 는 이 둘의 경쟁자가 아니다.

Higgsfield 공식 API 문서를 열어 보면 엔드포인트가 이렇게 생겼다[^hf-docs]:

```
POST https://api.higgsfield.ai/bytedance/seedance-2.5/text-to-video
POST https://api.higgsfield.ai/bytedance/seedance-2.0/text-to-video
```

**Higgsfield 는 Seedance 를 되판다.** 카탈로그에는 Seedance 2.0/2.5 외에 Kling 3.0, Wan 3.0, Grok Image 2.0, Recraft V4.1, 자체 모델 SOUL 계열이 함께 들어 있다. 즉 구도는 이렇다.

```
        [ 음악 ]              [ 영상 ]
        Suno                  BytePlus ModelArk (Seedance 1차 공급)
                                      ↑ 되팔기
                              Higgsfield (애그리게이터 + 자체 모델)
```

그래서 "Higgsfield 와 가격 비교"는 **경쟁사 대비 표**가 아니라 **중간 유통 마진을 얼마나 지불하느냐**의 문제가 된다. 그리고 그걸 확인하려 할 때 벽에 부딪힌다.

한 가지 더. Higgsfield 의 2.5 엔드포인트는 문서상 **480p 또는 720p** 만 지원한다[^hf-docs]. BytePlus 1차에는 1080p 가 있다. 되팔기 층은 설정 공간이 더 좁다.

---

## 4. Higgsfield — 가격을 읽을 수 없다는 것 자체가 결과다

Higgsfield 는 **완전히 분리된 두 개의 제품**을 판다. 공식 헬프센터 문구다[^hf-api-help]:

> higgsfield.ai 의 구독과 API 는 별개의 제품이고 과금도 별개다. 플랜·크레딧·Unlimited 접근은 웹사이트에만 존재하고, API 는 자체 USD 잔액으로 돌아간다.

**(a) API — 숫자로 말한다.** 선불 USD 잔액, 최소 충전 $5, **영상은 출력 초당 과금**, 이미지는 장당, 실패·NSFW 는 환불, 잔액은 1년 후 만료, 키 발급 시 동시 요청 20건[^hf-api-help]. 실행 전 비용을 미리 알려주는 `estimate` 엔드포인트까지 있다[^hf-docs]:

```bash
curl --request POST \
  --url https://api.higgsfield.ai/estimate/higgsfield-ai/soul/v2/standard \
  --header "Authorization: Key ${HF_API_KEY_ID}:${HF_API_KEY_SECRET}" \
  --data '{"prompt": "Editorial portrait in soft daylight"}'
```
```json
{ "credits": "1.500", "usd": "0.094" }
```

문서는 이 응답에 대해 *"위 값들은 응답 형식을 보여주기 위한 것"* 이라고 못 박아 둔다. 그래서 **이 $0.094 를 실제 단가로 인용하면 안 된다.** 다만 구조적 사실 하나는 분명하다 — 세 제품 중 **실행 전 견적 API 를 가진 건 Higgsfield 뿐**이다. BytePlus 는 산식을 공개하되 실제 소비량은 *호출 후* `usage.completion_tokens` 로 알려주고, Suno 는 곡당 크레딧이 고정이라 견적이라는 개념 자체가 없다.

**(b) 구독 — 숫자로 말하지 않는다.** higgsfield.ai/pricing 은 클라이언트 렌더링 앱이다. 브라우저 User-Agent 로 curl 하면 HTTP 200 에 73,903 바이트가 오는데, 그 안에 **가격 숫자가 한 개도 없다.** JavaScript 를 실행해야만 요금이 그려진다. 그리고 Higgsfield 자신의 헬프센터도 가격을 적기를 거부하고 Pricing 페이지로 넘긴다 — *"모든 플랜과 현재 가격은 Pricing 페이지에 있다."*

대신 헬프센터가 적어 주는 **구조**는 꽤 상세하다[^hf-credits]:

| 크레딧 종류 | 출처 | 리셋 | 만료 |
|---|---|---|---|
| 구독 크레딧 | 플랜 포함 | 매 결제 주기 | **갱신 시 소멸(이월 없음)** |
| Credit Pack | 1회 구매 | 없음 | 90일 |
| Auto-Refill | 자동 충전 | 없음 | 90일 |
| Promo | 프로모·보상 | 없음 | 고지된 날짜 |
| Boost | 동시성 팩 동봉 | 없음 | 90일 |

소비 순서는 구독 → Credit Pack → promo → Auto-Refill 이다. 그리고 **자동화 관점에서 가장 중요한 한 줄**:

> 크레딧은 web, MCP, CLI, Canvas, Supercomputer 의 모든 생성에서 차감된다. … **Unlimited 접근은 higgsfield.ai 에서만 적용된다. MCP, CLI, Canvas, Supercomputer 등 그 바깥에서 이뤄진 생성은 플랜과 무관하게 항상 크레딧을 차감한다.**[^hf-credits]

즉 **Claude Code 나 Cursor 에서 MCP 로 Higgsfield 를 돌리는 순간, 요금제의 "무제한" 혜택은 통째로 증발한다.** 에이전트로 자동화할수록 그 제품의 최대 세일즈 포인트에서 멀어지는 구조다. 이건 가격표를 못 읽어도 확실히 말할 수 있는, 그리고 실무에 직접 영향을 주는 사실이다.

**인터넷에 떠도는 Higgsfield 구독 가격은 쓰지 않았다.** 확인해 보면 요약 블로그마다 $19/270크레딧과 $9/120크레딧이 갈리고, 플랜 이름조차 Starter/Plus/Ultra 와 Basic/Plus/Max 로 갈린다. 서로 모순되는 출처는 하나를 고르는 게 아니라 **전부 버리는 게** 맞다. 이 글에서 Higgsfield 구독 가격은 **미확인**이다.

---

## 5. 중립 지표 — 내가 틀렸던 부분

이 글을 시작할 때 나는 "코딩엔 SWE-bench 같은 공개 벤치마크가 있지만 음악·영상엔 대응하는 중립 지표가 없다"는 가설을 갖고 있었다. **확인해 보니 틀렸다.** 세 분야 다 중립 리더보드가 있다.

Artificial Analysis 는 음악·영상·이미지 모두에 대해 **블라인드 쌍대 비교 → Bradley-Terry 최대우도추정 → Elo 스케일 재조정** 이라는 동일한 방법론을 쓰고, 95% 신뢰구간과 표본 수를 함께 공개하며, 레이팅을 **매시간 재계산**한다[^aa-video-method][^aa-music-method].

**Music Arena — Vocals** (2026-09-17 21:45 KST 직접 조회)[^aa-music]:

| 순위 | 제작사 | 모델 | Elo | 95% CI | 표본 |
|---|---|---|---|---|---|
| 1 | Suno | **Suno V5.5** | 1172 | ±7 | 9,630 |
| 2 | Mureka | Mureka V9 | 1150 | ±14 | 2,909 |
| 3 | Mureka | Mureka V8 | 1139 | ±6 | 10,618 |
| 4 | StepFun | StepAudio 3 Music | 1107 | ±15 | 2,043 |
| 5 | MiniMax | MiniMax Music 2.5+ | 1098 | ±6 | 10,398 |

**Text to Video (With Audio)** (같은 시각 직접 조회)[^aa-video]:

| 순위 | 제작사 | 모델 | Elo | 95% CI | 표본 | API 가격 |
|---|---|---|---|---|---|---|
| 1 | Google | Gemini Omni Flash | 1233 | ±7 | 15,172 | $6.00/min |
| 2 | Alibaba | Wan 3.0 | 1229 | ±9 | 6,011 | $12.00/min |
| 3 | Fal | Minimax H3 Max | 1227 | ±9 | 5,689 | $2.40/min |
| 4 | MiniMax | MiniMax H3 | 1220 | ±8 | 8,602 | $7.80/min |
| 5 | ByteDance Seed | **Dreamina Seedance 2.0 720p** | 1210 | ±6 | 20,345 | **$9.07/min** |

여기서 반가운 교차 검증이 하나 나온다. 내가 2장에서 BytePlus 1차 자료로 유도한 Seedance 2.0 720p 단가는 초당 $0.15 였다. 분당으로 환산하면:

$$21{,}600 \times \frac{7.0}{10^6} \times 60 = \$9.072\ \text{/min}$$

Artificial Analysis 가 독립적으로 표기한 값은 **$9.07/min** 이다. 서로 다른 두 경로가 같은 숫자에 도달했다.

### 하지만 중립 지표에는 두 가지 함정이 있다

**(1) 중립 지표는 항상 한 세대 뒤를 잰다.** Music Arena 1위는 **Suno V5.5** 인데, Suno 가 지금 파는 건 **v6 / v6-wild / v6-mini** 다. Video Arena 5위는 **Seedance 2.0 720p** 인데, BytePlus 의 현행 플래그십은 **2.5** 다. 크라우드 투표는 표본이 쌓여야 CI 가 좁아지므로, 구조적으로 **당신이 돈 내고 쓰는 그 모델의 중립 점수는 존재하지 않는다.** 벤더가 신모델 출시 때 내놓는 수치는 대체로 자체 벤치마크다 — 예컨대 Seedance 1.0 의 공식 소개 페이지는 내부 벤치마크 **SeedVideoBench-1.0** 과 Artificial Analysis 스냅샷을 함께 제시한다[^seed-marketing]. 앞의 것은 벤더 주장이고, 뒤의 것은 특정 시점 인용이다.

**(2) 재는 것이 다르다.** 이게 핵심이다.

| | 측정 대상 | 방식 | 재현 가능? |
|---|---|---|---|
| Music/Video Arena | **선호** | 블라인드 쌍대 투표 → Bradley-Terry | 표본 다시 모아야 함, 매시간 변동 |
| SWE-bench Verified | **통과/실패** | 실제 GitHub 이슈 500건에 테스트 패치 적용 | 결정적, 같은 하네스면 같은 수 |

SWE-bench Verified 는 원본 SWE-bench 에서 **사람이 걸러낸 500건**의 부분집합이다. 공식 설명 그대로 — *문제 설명이 명확한지, 테스트 패치가 올바른지, 주어진 정보로 풀 수 있는지를 사람이 검토했다.* 각 항목은 **% Resolved**, 즉 푼 인스턴스 비율만 보고한다. 그리고 모델 간 사과 대 사과 비교를 위해 **mini-SWE-agent** 라는 최소 하네스(*도구도 특수 스캐폴드도 없이, 그냥 bash 셸 하나와 문제만 준 ReAct 루프*)로 통일해 재는 별도 뷰를 둔다[^swebench].

(공식 리더보드 표 자체는 자바스크립트 뷰어라 이 글에서 점수표를 옮겨 적지 않았다. 애그리게이터 사이트마다 숫자가 갈리므로 인용하지 않는다.)

---

## 6. 진짜 비대칭 — 검증 가능성이 과금 모양을 정한다

이제 세 과금 모델을 나란히 놓으면 왜 이렇게 생겼는지가 보인다.

| | Suno | Seedance(BytePlus) | Higgsfield | Codex / Claude Code |
|---|---|---|---|---|
| **파는 것** | 반출 권리 | 계산 자원 | 둘 다(분리) | 계산 자원 |
| 과금 단위 | 곡당 크레딧 + **다운로드 쿼터** | 토큰(해상도×fps×길이) | 크레딧 / USD 잔액 | 토큰 or 구독 사용량 창 |
| 실행 전 견적 | 개념 없음(고정) | 산식 공개, 실측은 사후 | **`estimate` API** | 사전 견적 없음 |
| 실패 시 과금 | — | 안 함 | 안 함(자동 환불) | 함(토큰은 소모됨) |
| 미사용분 이월 | **안 됨** | 해당 없음(종량) | 구독분 **안 됨** | 창 단위 리셋 |
| 자동화 시 | — | 동일 | **Unlimited 무효화** | 오히려 주 용도 |

패턴이 보인다.

**코딩 에이전트의 출력은 기계가 검증한다.** 테스트가 통과하거나 안 하거나다. 그래서 사람이 매 출력을 볼 필요가 없고, 밤새 돌려도 되고, **토큰으로 종량 과금하는 게 자연스럽다.** SWE-bench 가 "% Resolved" 라는 이진 지표로 성립하는 것과 같은 이유다.

**음악·영상의 출력은 기계가 검증할 수 없다.** 곡이 좋은지에 대한 단위 테스트는 없다. 그래서 중립 지표조차 결국 **사람의 선호 투표**로 갈 수밖에 없었고(Bradley-Terry), 벤더의 과금도 **사람 병목**에 맞춰 설계된다. Suno 가 생성이 아니라 **다운로드 20곡**을 제한하는 이유, Higgsfield 가 동시성과 크레딧을 팔면서 **"Unlimited 은 우리 사이트 안에서만"** 이라고 못 박는 이유가 여기 있다. 사람이 듣고 보고 고르는 단계를 거쳐야 하니, 무한 자동화를 전제로 한 가격표를 만들 수 없는 것이다.

Seedance 가 예외처럼 보이는데, 그건 Seedance 가 **소비자 제품이 아니라 인프라 API** 이기 때문이다. 같은 모델이 Higgsfield 라는 소비자 층에 얹히는 순간 다시 크레딧·동시성·Unlimited 게이트가 붙는다. **모양을 정하는 건 모델이 아니라 판매 계층이다.**

---

## 7. 그래서 생산성은 어떻게 비교하나

### 코딩 쪽에는 1차 출처로 된 1인당 월 비용이 있다

OpenAI 헬프센터가 직접 적어 둔 문장이다[^codex-cost]:

> 평균적으로 Codex 는 개발자 1인당 월 **약 $100–$200** 의 비용이 든다. 실제 비용은 사용 모델, 동시 인스턴스 수, 자동화, fast mode 에 따라 크게 달라진다.

플랜 쪽 1차 숫자[^codex-pricing][^chatgpt-plans]:

| | 가격 | 비고 |
|---|---|---|
| ChatGPT Plus | $20/월 | Codex 포함 |
| ChatGPT Pro | $100/월(5x), $200/월(20x) | |
| ChatGPT Business | $25/사용자·월(월간 결제) | 연간은 더 저렴 |
| Claude Pro | **$17/월**(연간, $200 선결제) / $20(월간) | Claude Code 포함 |
| Claude Max | **"From $100/월"** — Pro 대비 5x 또는 20x | 20x 가격은 페이지에 미표기 |
| Claude Team | 표준 $20/석·월(연간) / 프리미엄 $100/석·월(연간) | |

Codex 는 2026-04-02 부터 메시지 과금에서 **토큰 기반 크레딧**으로 바뀌었고, 사용 한도는 고정 횟수가 아니라 **5시간 창당 메시지 수의 범위**로 고지된다(예: GPT-5.6 Sol 은 Plus 10–100). Anthropic 쪽 API 단가는 MTok 기준 Opus 5 $5/$25, Sonnet 5 $2/$10, Haiku 4.5 $1/$5 다[^anthropic-pricing].

주의할 점 하나. OpenAI 의 서로 다른 1차 페이지 두 곳이 GPT-5.6 계열 크레딧 단가를 **다르게** 적고 있다(1M 토큰당 입력 100 vs 125, 출력 500 vs 750). 어느 쪽이 맞는지 나는 판정할 수 없어서, 여기서는 **불일치가 있다는 사실만** 적는다.

### 분야를 가로지르는 환산

$100–$200/개발자·월 이라는 코딩 쪽 앵커를 다른 분야 단위로 바꿔 보면 규모 감각이 생긴다.

| 같은 예산으로 | $100 | $200 |
|---|---|---|
| Seedance 2.5 720p 5초 클립 | 86편 = **약 7분 12초** | 173편 = **약 14분 25초** |
| Seedance 2.0 720p 5초 클립 | 131편 = 약 11분 | 263편 = 약 22분 |
| Suno Pro 다운로드 곡 | **250곡** | **500곡** |
| Sonnet 5 출력 토큰 | 1,000만 토큰 | 2,000만 토큰 |

반대 방향도 재미있다. **5초짜리 720p 클립 하나($1.156)의 값은 Sonnet 5 출력 토큰 약 11.6만 개**다. 어지간한 리팩터링 한 건이 통째로 들어간다. **Suno 다운로드 1곡($0.40)은 출력 토큰 4만 개**다.

단, 이 표에는 정직한 한계가 있다. **세 분야는 공통 분모가 없다.**

- 영상만 **초**라는 자연스러운 단위를 갖는다.
- 음악은 곡당 과금인데 **Suno 가 곡 길이를 공식 사양으로 공개하지 않아** 분당 단가를 계산할 수 없다.
- 코드는 **시간 단위 자체가 없다.**

그래서 위 표는 "예산이 각 분야에서 몇 단위를 사는가"까지만 말하고, "어느 쪽이 생산적인가"는 말하지 않는다.

### 그리고 벤치마크 점수는 생산성 주장이 아니다

이 지점에서 반드시 붙여야 할 반례가 있다. METR 의 무작위 대조 시험(RCT)이다[^metr].

경험 많은 오픈소스 개발자 16명이 **자기가 평균 5년간 기여해 온 대형 저장소**(평균 23,000 스타)에서 실제 이슈 **246건**(평균 2시간짜리)을 처리했다. 각 이슈는 AI 사용 허용/금지로 **무작위 배정**됐다. 결과:

| | 값 |
|---|---|
| 개발자 사전 예측 | 24% **단축** |
| 경제학 전문가 34명 예측 | 39% 단축 |
| ML 전문가 54명 예측 | 38% 단축 |
| 개발자 사후 체감 | 20% 단축 |
| **실측** | **19% 증가(느려짐)** |

$$\text{speedup} = \frac{E[T_{\text{AI}}]}{E[T_{\text{no AI}}]} - 1 = +0.188,\quad \text{CI}_{95\%} = (0.013,\ 0.395)$$

논문이 스스로 적은 함의가 중요하다. *"이 관측된 감속은, 실사용 환경에서의 AI 능력이 흔히 쓰이는 벤치마크가 시사하는 것보다 낮을 수 있다는 증거가 된다."* 그리고 **직접 겪고 난 뒤에도** 개발자들은 여전히 20% 빨라졌다고 믿었다.

당연히 한계도 명확하다. 2025년 2–6월 프런티어(주로 Cursor Pro + Claude 3.5/3.7 Sonnet) 기준이고, 참가자 16명이며, **본인이 최고 수준으로 익숙한 성숙한 코드베이스**라는 특수한 조건이다. 신규 프로젝트나 낯선 코드에 일반화되지 않는다. 그럼에도 이 연구가 여기서 갖는 역할은 분명하다 — **SWE-bench 점수가 높다는 것과 그 도구가 당신을 빠르게 만든다는 것은 별개의 주장**이며, 이 구분은 Elo 1172 짜리 음악 모델에도 똑같이 적용된다.

---

## 8. 실무 규칙 네 가지

**1. 영상은 해상도를 마지막에 올린다.** 픽셀 면적이 그대로 토큰이라 480p→1080p 가 5배 이상이다. 구도·컷·타이밍을 480p($0.103/초)로 확정하고, 확정된 것만 1080p($0.569/초)로 다시 뽑는다. 초안 단계에서 1080p 로 20번 재시도하면 확정본 1회의 100배를 쓴다.

**2. 음악은 다운로드 쿼터가 진짜 한도다.** 크레딧(월 500곡)이 아니라 다운로드(월 20곡)에서 먼저 막힌다. 생성은 후하게, **다운로드 결정은 25:1 을 전제로** 고르라는 게 요금제의 설계 의도다.

**3. 에이전트로 자동화할 거면 애그리게이터의 "Unlimited" 를 예산에 넣지 마라.** MCP·CLI 경유 생성은 플랜과 무관하게 항상 크레딧을 먹는다. 자동화 물량은 종량 API 기준으로 잡아야 한다.

**4. 할인 창은 만료일을 코드 주석이 아니라 캘린더에 적는다.** 오늘 15:00 KST 에 Seedance 2.5 1080p 가 $0.41/초에서 $0.569/초로 돌아갔다. 견적 로직에 단가를 하드코딩해 뒀다면 오늘 밤 실제 청구가 39% 어긋난다.

---

## 9. 이 글이 말하지 않은 것

- **Higgsfield 구독 가격**: 확인 불가. 공식 페이지는 JS 렌더링이고 헬프센터는 가격 표기를 거부하며, 제3자 숫자들은 서로 모순된다.
- **Suno 곡 길이**: 공식 사양 미공개라 분당 단가를 내지 않았다.
- **모델 품질의 우열**: 각 분야 최신 모델의 중립 점수는 존재하지 않는다(리더보드는 한 세대 뒤를 잰다). 이 글은 가격 구조와 측정 방법론만 다뤘다.
- **SWE-bench 점수표**: 공식 뷰어가 JS 앱이라 옮겨 적지 않았다. 애그리게이터 수치는 서로 달라 인용하지 않았다.
- **한국 원화 환산**: 환율 변동분을 다루지 않았다. 모두 USD 표기 그대로다.

가격은 오늘(2026-09-17) 기준이고, 방금 본 것처럼 **하루 안에도 바뀐다.**

---

## References

[^bp-price]: BytePlus, *ModelArk — Seedance 모델 가격 및 토큰 산식*, docs.byteplus.com/en/docs/ModelArk/1099320 (문서 최종 수정 2026-08-31, 2026-09-17 조회). 토큰 산식, 모델별 토큰 단가, 해상도별 공식 가격 예제, 시한 할인 조건 전부 이 페이지 기준.
[^suno-pricing]: Suno, *Pricing*, suno.com/pricing (2026-09-17 조회, 연간 결제 기준). 플랜 표·크레딧 이월 정책.
[^suno-plans]: Suno Help Center, *What type of plan do I have?*, help.suno.com/en/articles/2410049 (최종 수정 2025-12-19). "50 크레딧 = 하루 10곡" → 곡당 5크레딧.
[^hf-docs]: Higgsfield, *API Docs* — 모델 카탈로그·빌링·레이트리밋, docs.higgsfield.ai (2026-09-17 조회). Seedance 2.0/2.5 엔드포인트, `estimate` 응답 형식, 동시성 한도.
[^hf-api-help]: Higgsfield Help Center, *What is the Higgsfield API and how do I get started*, higgsfield.ai/creator-hub/help-center/integrations/what-is-the-higgsfield-api (2026-09-16 갱신). 구독/API 분리, 초당 과금, 최소 충전 $5, 실패 환불.
[^hf-credits]: Higgsfield Help Center, *How credits work*, higgsfield.ai/creator-hub/help-center/credits-and-usage/how-credits-work. 크레딧 종류·만료·소비 순서, "Unlimited 은 higgsfield.ai 에서만".
[^aa-music]: Artificial Analysis, *Vocals Music Leaderboard*, artificialanalysis.ai/music/leaderboard/vocals (2026-09-17 21:45 KST 직접 조회). 레이팅은 매시간 재계산되므로 스냅샷임.
[^aa-video]: Artificial Analysis, *Text to Video Leaderboard (With Audio)*, artificialanalysis.ai/video/leaderboard/text-to-video (같은 시각 직접 조회). API 가격 각주: "모델 제작사 API 에서 기본 설정으로 1분 영상을 생성하는 비용".
[^aa-music-method]: Artificial Analysis, *Music Generation Benchmarking Methodology*, artificialanalysis.ai/music/methodology. Bradley-Terry MLE, 95% CI, 모달리티·장르별 분리.
[^aa-video-method]: Artificial Analysis, *Video Generation Benchmarking Methodology*, artificialanalysis.ai/video/methodology. 모달리티별 독립 Elo 풀, 시간 단위 재계산.
[^swebench]: SWE-bench, *SWE-bench Verified*, swebench.com/verified. OpenAI 협업으로 사람이 검수한 500건 부분집합, % Resolved, mini-SWE-agent 통일 하네스.
[^codex-cost]: OpenAI Help Center, *Codex 과금 및 크레딧* (help.openai.com/en/articles/20001106, /11481834). "개발자 1인당 월 약 $100–$200", 2026-04-02 토큰 크레딧 전환, 5시간 창 사용 한도.
[^codex-pricing]: OpenAI, *Codex Pricing*, chatgpt.com/codex/pricing 및 developers.openai.com/codex/pricing.
[^chatgpt-plans]: OpenAI, *ChatGPT 요금제*, learn.chatgpt.com/docs/pricing.
[^anthropic-pricing]: Anthropic, *Pricing*, claude.com/pricing (2026-09-17 조회). 구독 요금 및 모델별 MTok 단가.
[^seed-marketing]: ByteDance Seed, *Seedance* 소개 페이지, seed.bytedance.com/en/seedance. **벤더 자체 벤치마크(SeedVideoBench-1.0)** 와 Artificial Analysis 특정 시점 스냅샷을 함께 제시 — 벤더 주장으로 분류.
[^metr]: Becker, J., Rush, N., Barnes, E. A., Rein, D. B., *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, METR, arXiv:2507.09089 (2025-07). RCT, 개발자 16명·이슈 246건, 실측 +19% 소요시간 증가, CI (0.013, 0.395).
