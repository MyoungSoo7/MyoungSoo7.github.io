---
layout: post
title: "Cloudflare 는 대역폭으로 돈을 받지 않는다 — 그럼 과금은 어디서 발생하나"
date: 2026-09-15 08:18:03 +0900
categories: [infra]
tags: [cloudflare, billing, cdn, workers, r2, zero-trust, finops, homelab]
---

"무제한 대역폭"이라고 써 있는데 청구서가 온다. 이 모순처럼 보이는 상황은 사실 모순이 아니다. **Cloudflare 의 과금 축이 대역폭이 아니기 때문**이다.

공식 빌링 문서는 한 줄로 못박는다 — "**Bandwidth: Included in all plans. Cloudflare does not charge for bandwidth.**"[^accrue] 오리진↔Cloudflare 구간도 마찬가지다. "No charge for data transfer between Cloudflare and your origin (no egress fees)."[^accrue]

그러면 돈은 어디서 나가나. 이 글은 **청구가 발생하는 지점을 요청의 흐름 위에 하나씩 찍어보는** 글이다.

---

## 0. 먼저 두 가지를 구분한다 — "과금"과 "제한"

"무제한인데 왜 돈을 받나"라는 질문 안에는 사실 **서로 다른 두 개의 메커니즘**이 섞여 있다.

**(가) 과금** — 계량되는 자원을 쓰면 청구된다. 이 글의 주제다.

**(나) 용도 제한** — 대역폭은 공짜지만, **CDN 을 아무 용도로나 쓸 수는 없다.** 예전에 Self-Serve Subscription Agreement **§2.8 "Limitation on Serving Non-HTML Content"** 로 불리던 조항이다. 2023년 Cloudflare 는 이 조항을 약관 전체에 걸린 위치에서 빼내 **CDN 전용 조항**으로 옮기고, "HTML vs non-HTML" 이라는 낡은 구분을 없앴다고 공식 블로그에 밝혔다.[^tos2023]

현재 조항의 실제 문구는 이렇다:

> "Enterprise 고객이 아니라면, 비디오와 기타 대용량 파일을 CDN 으로 제공하기 위해서는 Cloudflare 가 제공하는 특정 유료 서비스(예: Developer Platform, Images, Stream)를 **사용해야 한다.** … 그런 유료 서비스 없이 비디오나 불균형한 비율의 이미지·오디오·대용량 파일을 제공하는 것으로 **의심되는 경우에도**, Cloudflare 는 CDN 사용을 비활성화하거나 제한할 권리를 유보한다."[^sst]

즉 이 축의 결과는 **청구서가 아니라 차단**이다. 홈랩에 동영상 서버를 올려놓고 Cloudflare 프록시로 쏘는 구성이 여기 걸린다. 돈을 더 내는 게 아니라 **막힌다.** 두 축을 섞어 생각하면 "무제한이라며?"에서 영원히 답이 안 나온다.

## 1. 과금은 세 개의 축으로 들어온다

| 축 | 성격 | 예시 |
| --- | --- | --- |
| **플랜 구독** | **선불 정액**, 다음 달치를 미리 | Pro / Business / Enterprise, Page Rules 같은 애드온 |
| **사용량 과금** | **후불 종량**, 지난 기간 사용분 | Workers, R2, Argo, Load Balancing, Images, Stream … |
| **좌석(Seat)** | 사용자 수 기준 | Zero Trust (Access / Gateway) |

공식 문서가 선불/후불 차이를 명시한다 — "이것은 다가올 달에 대해 선불 정액으로 청구되는 다른 서비스(예: **플랜과 Page Rules**)와 다르다."[^usage] 그래서 **Workers 를 1일에 켜고 청구일이 15일이면, 다음 청구서에 1~15일치가 붙는다.** 이 시차가 "왜 이번 달에 갑자기?"의 흔한 정체다.

## 2. 요청 한 건이 청구서가 되는 10단계

Cloudflare 문서에는 **요청 하나가 어느 지점에서 계량되는지를 순서대로 적어놓은 페이지**가 있다.[^accrue] 요약하면 이렇다.

| 단계 | 과금되나 |
| --- | --- |
| ① DNS 조회 | **무료.** 단 Load Balancing 을 쓰면 LB 호스트명에 대한 DNS 쿼리가 계량된다 (50만 건 포함) |
| ② 엣지 도착 · TLS 종료 | **무료.** 단 Advanced Certificate Manager, SSL for SaaS 는 별도 |
| ③ **캐시 히트** | **여기서 끝나면 사실상 0원** — 대역폭 무료 |
| ③′ 캐시 미스 | 아래 단계로 계속 진행 |
| ④ Argo Smart Routing (켜져 있으면) | **오리진과 주고받은 GB 당 계량.** 최초 1 GB 포함 |
| ⑤ Worker 실행 (라우트에 걸려 있으면) | **요청 수 + CPU 밀리초** 각각 계량. KV 읽기/쓰기는 또 별도 |
| ⑥ 오리진 페치 | **무료** (egress 없음) |
| ⑦ R2 접근 | **Class A(쓰기) / Class B(읽기) / 저장용량** 각각 계량. **egress 는 무료** |
| ⑧ 캐시 기록 | Cache Reserve 를 켰다면 **쓰기가 계량** |
| ⑨ 이미지 변환 | 변환 건수 계량 |
| ⑩ 응답 전달 | 추가 과금 없음 |

문서 자신이 내린 결론이 정확히 핵심이다:

> "핵심 요점: **캐시된 응답이 가장 싼 경로다.** 모든 캐시 히트는 오리진 페치 비용, Argo 라우팅 요금, Workers 실행, R2 오퍼레이션을 전부 회피한다. 캐시 적중률 최적화가 사용량 기반 요금을 줄이는 **가장 효과적인 단일 수단**이다."[^accrue]

바꿔 말하면 — **Cloudflare 청구서는 트래픽 총량의 함수가 아니라, 요청이 지나간 경로의 함수다.** 같은 100만 요청이라도 전부 캐시 히트면 0원이고, 전부 미스면 Argo GB + Worker 요청 + Worker CPU + R2 오퍼레이션이 한꺼번에 붙는다.

## 3. 계량되는 제품 13종 — 그리고 무료 포함량

공식 "Usage-based billing" 문서의 표를 그대로 옮긴다.[^usage]

| 제품 | 계량 단위 | 무료 포함량 |
| --- | --- | --- |
| Workers | 요청 수, CPU 시간 | 1,000만 요청 + 3,000만 CPU-ms |
| R2 | 저장용량, 오퍼레이션 | 10 GB + Class A 100만 + Class B 1,000만 |
| Argo Smart Routing | 데이터 전송량 | **첫 1 GB** |
| **Cache Reserve** | 읽기·쓰기·저장 | **없음(None)** |
| Load Balancing | DNS 쿼리 | 첫 50만 |
| Stream | 저장 분·시청 분 | 플랜별 상이 |
| Images | 변환 수·저장 | 플랜별 상이 |
| **Spectrum** | 데이터 전송량 | **없음(None)** |
| Rate Limiting | 룰 적용 요청 수 | 플랜별 상이 |
| Log Explorer | 로그 저장·쿼리 | 플랜별 상이 |
| Zero Trust | 좌석 + 사용량 서비스 | 플랜별 상이 |
| Vectorize | 저장 차원·조회 벡터 | 플랜별 상이 |
| Analytics Engine | 데이터 포인트 읽기·쓰기 | 플랜별 상이 |

**볼드 두 개가 중요하다.** Cache Reserve 와 Spectrum 은 **무료 포함량이 "없음"** 이다. 켜는 순간부터 1원 단위로 계량이 시작된다. "일단 켜보고 무료 한도 넘으면 끄지 뭐"가 이 둘에는 통하지 않는다.

## 4. 숫자로 — Workers 와 R2

**Workers**[^workers]

- 무료 플랜: 하루 10만 요청, 요청당 CPU 10 ms. 초과하면 과금이 아니라 **에러 1027** 이 난다.
- 유료 플랜: 계정당 **최소 월 $5**. 1,000만 요청 + 3,000만 CPU-ms 포함, 초과분은 100만 요청당 $0.30 / 100만 CPU-ms 당 $0.02.
- **데이터 전송(egress)·대역폭에 대한 추가 과금은 없다.**

공식 계산 예시 — 월 1,500만 요청, 요청당 CPU 7 ms:
구독 $5.00 + 요청 초과 $1.50 + CPU 초과 $1.50 = **$8.00**[^workers]

**R2**[^r2]

- Standard: 저장 **$0.015/GB-월**, Class A **$4.50/백만**, Class B **$0.36/백만**, **egress 무료**
- 무료 티어: 10 GB-월, Class A 100만, Class B 1,000만

여기서 비용 구조의 성격이 드러난다. **R2 는 전송량보다 오퍼레이션 수에 민감하다.** 1 GB 짜리 객체 하나를 읽으면 Class B 오퍼레이션 **1건**이고, 1 KB 객체 100만 개를 읽으면 **100만 건**이다. 내려간 바이트는 같은데 계량되는 숫자가 100만 배 다르다. 그래서 공식 최적화 가이드에도 "객체별 읽기 대신 **R2 오퍼레이션을 배치로 묶으라**"가 들어 있다.[^usage]

같은 이유로 **객체를 잘게 쪼개는 설계가 곧 비용 설계**가 된다. 용량 단가($0.015/GB-월)만 보고 "싸다"고 판단하면 오퍼레이션 축을 통째로 빠뜨리는 셈이다.

## 5. Zero Trust 좌석 — 관리자가 추가해서가 아니라, 로그인해서 잡힌다

홈랩에서 가장 헷갈리는 축이다.

- 무료 플랜: **50 사용자까지 $0**[^zt]
- Pay-as-you-go: **$7/사용자/월**
- Gateway 데이터: 첫 10 GB 무료, 이후 GB 당 $1[^zt]

그런데 좌석이 **언제** 소모되는지가 함정이다. 공식 FAQ 는 이렇게 적는다:

> "Zero Trust 구독은 계정의 사용자가 소비하는 **좌석**으로 구성된다. 사용자가 **애플리케이션에 인증하거나** 디바이스를 Cloudflare One Client 에 **등록하면**, 활성 좌석 하나를 소모한다."[^ztfaq]

즉 **누군가 로그인하는 행위 자체가 좌석을 쓴다.** 초대 목록에 몇 명을 올려놨느냐가 아니다. 그리고 좌석이 다 찼으면 구매 좌석 수를 줄이기 전에 먼저 사용자를 제거해야 한다는 조건도 같은 문서에 있다.

DNS 필터링 쪽에는 별도 상한도 있다 — 유료 계약 기준으로 **좌석당 월평균 DNS 쿼리 150,000건**(좌석당 하루 5,000건)을 넘으면 Cloudflare 가 좌석 추가 구매를 요구할 수 있다고 서비스 약관에 명시돼 있다.[^ztterms]

## 6. 조용히 청구를 만드는 것들

정리하면, "무료 플랜인데 돈이 나간다"의 현실적 후보는 거의 이 목록 안에 있다.

1. **Argo Smart Routing** — 대시보드 토글 하나. 켜는 순간 오리진 왕복 트래픽이 GB 단위로 계량된다(첫 1 GB 만 포함).
2. **Cache Reserve** — 무료 포함량 **0**. 읽기·쓰기·저장 셋 다 계량.
3. **Load Balancing** — DNS 쿼리 50만 이후. 헬스체크 주기를 촘촘히 잡으면 쿼리가 는다.
4. **Workers 유료 전환** — 한 번 유료로 올리면 **사용량이 0이어도 계정당 월 $5** 는 고정이다.
5. **Zero Trust 좌석** — §5.
6. **Images / Stream** — 변환 수·시청 분 계량.
7. **플랜 구독 자체** — Pro/Business 는 **존(도메인) 단위**다. 도메인을 여러 개 올리고 각각 Pro 로 올리면 그만큼 곱해진다.
8. **청구 시차** — 종량 항목은 **지난 기간분**이 붙는다. 이번 달에 끈 기능이 다음 청구서에 한 번 더 나올 수 있다.[^usage]

## 7. 그래서 홈랩은 왜 대체로 $0 인가

역으로 보면 **홈랩에서 Cloudflare 가 공짜인 이유**도 같은 구조로 설명된다.

- 대역폭·DNS 쿼리·TLS 종료·기본 WAF·DDoS 방어 — 전부 플랜 포함 항목이라 계량되지 않는다
- 프록시된 HTML/API 트래픽은 §0 의 용도 제한에도 걸리지 않는다
- 사용자가 50명 아래면 Zero Trust 좌석도 $0
- **Developer Platform(Workers/R2/Images/Stream)을 안 켜면 종량 축 자체가 열리지 않는다**

즉 홈랩에서 과금이 시작되는 지점은 거의 항상 **"엣지에서 뭔가를 실행하거나 저장하기 시작할 때"** 다. 통과시키는 것은 공짜고, **연산하거나 보관하면 돈**이다. 이 한 문장이 Cloudflare 요금 모델의 요약이다.

## 8. 예방 — 사후 확인이 아니라 임계 알림

공식 문서가 권하는 도구는 셋이다.[^usage]

1. **Billable usage 대시보드** — Pay-as-you-go 계정은 **일 단위**로 제품별 사용량과 무료 한도 소진분을 본다
2. **Budget alerts** — 계정 전체 **달러 임계치**를 넘으면 메일
3. **제품별 사용량 알림** — Professional 이상. 예: Argo 는 "총 전송 바이트 초과 시", Load Balancing 은 "총 DNS 쿼리 수 초과 시"

두 종류를 헷갈리지 말 것 — **사용량 알림은 단일 제품의 단위(바이트·요청·분)를 보고, 총 지출 금액을 보려면 budget alerts** 를 써야 한다. 그리고 문서 자신이 단서를 단다: "이메일 알림은 정보 제공용이다. 실제 사용량과 청구는 다를 수 있다. **월 청구서가 가장 신뢰할 수 있는 근거다.**"[^usage]

## 9. 이 글이 말하지 않은 것

- **구체적 요율은 바뀐다.** Cloudflare 문서 자신이 "Pricing can change" 를 페이지 상단에 달아둔다.[^accrue] 이 글의 숫자는 2026년 9월 기준이고, 실제 판단은 각 제품 pricing 페이지에서 다시 확인해야 한다.
- **특정 계정의 청구 원인을 진단하지 않았다.** 그건 Billable usage 대시보드에서 제품별로 봐야 한다. 이 글은 **어디를 봐야 하는지의 지도**다.
- **Enterprise 계약 조건**은 별도다. 위 무료 티어·용도 제한 서술은 self-serve(Free/Pro/Business) 기준이다.
- **환율·세금**은 다루지 않았다.

---

## 마무리

세 문장으로 줄이면 이렇다.

1. **대역폭은 과금 대상이 아니다.** 대신 CDN 을 대용량 파일 배포에 쓰는 것은 **차단** 대상이다 — 요금이 아니라 약관 축이다.
2. **청구서는 트래픽 총량이 아니라 요청의 경로를 따라 만들어진다.** 캐시 히트에서 끝나면 0원, 미스로 빠지면 Argo·Workers·R2 가 줄줄이 계량된다.
3. **통과는 공짜, 연산과 보관은 유료.** 홈랩에서 $0 이 유지되는 이유도, 깨지는 이유도 전부 이 선 위에 있다.

---

### References

- Cloudflare Billing Docs. *How charges accrue*. <https://developers.cloudflare.com/billing/understand/how-charges-accrue/>
- Cloudflare Billing Docs. *Usage-based billing*. <https://developers.cloudflare.com/billing/understand/usage-based-billing/>
- Cloudflare Workers Docs. *Pricing*. <https://developers.cloudflare.com/workers/platform/pricing/>
- Cloudflare R2 Docs. *R2 pricing*. <https://developers.cloudflare.com/r2/pricing/>
- Cloudflare. *Service-Specific Terms — Application Services (CDN)*. <https://www.cloudflare.com/service-specific-terms-application-services/>
- Cloudflare. *Service-Specific Terms — Zero Trust Services*. <https://www.cloudflare.com/service-specific-terms-zero-trust-services/>
- The Cloudflare Blog (2023-05-16). *Goodbye, section 2.8 and hello to Cloudflare's new terms of service*. <https://blog.cloudflare.com/updated-tos/>
- Cloudflare. *Zero Trust & SASE Plans & Pricing*. <https://www.cloudflare.com/plans/zero-trust-services/>
- Cloudflare One Docs. *Getting started with Cloudflare Zero Trust FAQ*. <https://developers.cloudflare.com/cloudflare-one/faq/getting-started-faq/>
- Cloudflare. *Plans*. <https://www.cloudflare.com/plans/>

[^accrue]: Cloudflare Billing Docs, "How charges accrue" (최종 갱신 2026-04-24). 요청 수명주기 10단계별 과금 항목표, "Bandwidth — Included in all plans. Cloudflare does not charge for bandwidth", "No charge for data transfer between Cloudflare and your origin (no egress fees)", 그리고 "The key takeaway: cached responses are the cheapest path…" 결론 문단. 페이지 상단 "Pricing can change" 단서 포함.
[^tos2023]: The Cloudflare Blog, "Goodbye, section 2.8 and hello to Cloudflare's new terms of service" (2023-05-16). §2.8 을 Self-Serve Subscription Agreement 에서 Service-Specific Terms 의 CDN 전용 절로 이동하고 HTML/non-HTML 구분을 폐기했다는 공식 설명.
[^sst]: Cloudflare, "Service-Specific Terms — Application Services" 의 CDN 절. 비디오·대용량 파일 제공 시 유료 서비스(Developer Platform, Images, Stream) 사용 요구와, 위반이 의심될 경우 CDN 접근을 비활성화·제한할 수 있다는 조항.
[^usage]: Cloudflare Billing Docs, "Usage-based billing" (최종 갱신 2026-05-29). 선불 정액(플랜·Page Rules) vs 후불 종량의 구분과 청구 시차 예시, 종량 과금 제품 13종 표와 무료 포함량(Cache Reserve·Spectrum = None), 최적화 전략표(배치 R2 오퍼레이션 등), Billable usage 대시보드·budget alerts·제품별 사용량 알림, "월 청구서가 가장 신뢰할 수 있는 근거"라는 단서.
[^workers]: Cloudflare Workers Docs, "Pricing". 무료 플랜 하루 10만 요청·요청당 CPU 10 ms 및 초과 시 Error 1027, 유료 플랜 계정당 최소 월 $5, 1,000만 요청 + 3,000만 CPU-ms 포함, $0.30/백만 요청 및 $0.02/백만 CPU-ms, "There are no additional charges for data transfer (egress) or throughput (bandwidth)", 월 1,500만 요청 기준 $8.00 계산 예시.
[^r2]: Cloudflare R2 Docs, "R2 pricing". Standard $0.015/GB-월, Class A $4.50/백만, Class B $0.36/백만, 전 스토리지 클래스 egress 무료, 무료 티어 10 GB-월 + Class A 100만 + Class B 1,000만.
[^zt]: Cloudflare, "Zero Trust & SASE Plans & Pricing". Free 플랜 50 사용자 한도 $0, Pay-as-you-go $7/사용자/월, Gateway 데이터 첫 10 GB 무료 후 GB 당 $1.
[^ztfaq]: Cloudflare One Docs, "Getting started with Cloudflare Zero Trust FAQ". "Cloudflare Zero Trust subscriptions consist of seats that users in your account consume. When users authenticate to an application or enroll their agent into the Cloudflare One Client, they count against one of your active seats."
[^ztterms]: Cloudflare, "Service-Specific Terms — Zero Trust Services" §2.3. Gateway DNS 전용 사용 시 좌석당 월평균 DNS 쿼리 150,000건(일 5,000건) 상한과 초과 시 좌석 추가 구매 요구 조항, 계산 예시 포함.
