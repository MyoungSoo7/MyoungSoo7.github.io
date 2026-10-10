---
layout: post
title: "[CS300 #213] 웹 성능 최적화 — 사용자 지표로 재고, 병목 단계를 줄인다"
date: 2026-10-10 21:33:00 +0900
categories: [cs]
tags: [cs300, web, performance, core-web-vitals, caching]
---

컴퓨터공학 300 주제 시리즈의 213번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

웹 성능 최적화는 "빨라 보이는가"를 LCP·INP·CLS 같은 사용자 중심 지표로 측정하고, 네트워크(덜 보내고 가깝게), 렌더링(막지 않고), 메인 스레드(오래 잡지 않고) 세 곳의 병목을 줄이는 작업이다.

## 왜 필요한가

개발자의 노트북과 사무실 회선에서는 대부분의 사이트가 빠르다. 실제 사용자는 오래된 휴대폰, 지하철의 흔들리는 회선, 수십 개의 브라우저 탭 속에서 페이지를 연다. 개발 환경의 체감과 사용자의 경험은 다르다.

성능 문제는 막연한 "느림"으로 신고된다. 이것을 고치려면 두 가지가 필요하다.

1. **무엇을 잴 것인가**: 서버 응답 시간만 재면 브라우저에서 일어나는 대부분의 지연을 놓친다.
2. **어디를 고칠 것인가**: 렌더링 파이프라인(201번)과 이벤트 루프(204번)의 어느 단계가 병목인지 알아야 한다.

측정 없이 하는 최적화는 대개 엉뚱한 곳을 고친다.

## 핵심 개념

### 사용자 중심 지표: Core Web Vitals

web.dev 의 Core Web Vitals 는 세 가지 경험을 지표로 정의한다.

| 지표 | 무엇을 재나 | 좋음 기준 |
|---|---|---|
| LCP (Largest Contentful Paint) | 화면에서 가장 큰 콘텐츠(대표 이미지, 제목 블록)가 그려진 시점 | 2.5초 이내 |
| INP (Interaction to Next Paint) | 클릭·탭·키 입력 후 다음 화면이 그려지기까지의 지연 | 200ms 이하 |
| CLS (Cumulative Layout Shift) | 예상치 못한 레이아웃 이동의 누적 점수 | 0.1 이하 |

판정은 평균이 아니라 **75번째 백분위**로 한다. 사용자 넷 중 셋 이상이 좋은 경험을 해야 통과다. 평균은 소수의 매우 빠른 경험이 느린 사용자를 가려 버린다.

CLS 의 개별 점수는 "움직인 요소가 차지한 화면 비율(영향 비율) × 움직인 거리 비율(거리 비율)"이다. 거리 비율은 이동 거리를 뷰포트의 긴 변으로 나눈다. 1초 안쪽 간격으로 이어지는(최대 5초) 이동을 한 묶음으로 보고, 가장 큰 묶음의 합을 CLS 로 쓴다.

### 실험실 측정과 현장 측정

| 구분 | 도구 예 | 장점 | 한계 |
|---|---|---|---|
| 실험실(lab) | Lighthouse, 개발자 도구 Performance | 재현 가능, 원인 분석 | 실제 사용자 환경과 다름 |
| 현장(field, RUM) | `PerformanceObserver` 로 수집 | 실제 분포 | 원인 분석이 어려움 |

INP 처럼 실제 상호작용이 있어야 나오는 지표는 현장 데이터가 기준이다. 실험실에서는 원인을 찾고, 현장에서는 개선이 실제로 효과가 있었는지 확인한다. 브라우저의 Navigation Timing, Resource Timing API 가 현장 수집의 기반이다.

### 네트워크: 덜, 가깝게, 다시 받지 않게

- **압축**: HTML·CSS·JS 같은 텍스트는 gzip 이나 Brotli 로 크게 줄어든다.
- **이미지**: 표시 크기에 맞는 해상도(`srcset`, `sizes`), 효율적인 형식(WebP·AVIF), 화면 밖 이미지는 `loading="lazy"`. 단, LCP 이미지에는 lazy 를 쓰지 않는다. 오히려 `fetchpriority="high"` 로 먼저 받게 한다.
- **캐시**: 파일 이름에 내용 해시를 넣고(`app.3f9a1c.js`) `Cache-Control: max-age=31536000, immutable` 로 길게 캐시한다. HTML 은 짧게 캐시하거나 재검증(`no-cache` + ETag)한다. 캐시 의미는 RFC 9111 이 정의한다.
- **가까이**: 정적 자원은 CDN 에서 내보내 왕복 시간을 줄인다.
- **연결 미리 열기**: 다른 도메인의 핵심 자원은 `<link rel="preconnect">` 로 DNS·TCP·TLS 를 미리 끝낸다.

### 렌더링: 첫 화면을 막지 않기

- 첫 화면에 필요한 CSS 만 먼저, 나머지는 나중에.
- 스크립트는 `defer` 또는 `type="module"`. 분석·광고 스크립트는 `async`.
- 웹 폰트는 `font-display: swap` 등으로 글자가 안 보이는 시간을 줄인다.
- 이미지·광고·임베드에는 `width`/`height` 나 `aspect-ratio` 로 자리를 미리 잡아 CLS 를 막는다.

### 메인 스레드: 오래 잡지 않기

INP 를 나쁘게 만드는 것은 대부분 긴 자바스크립트 작업이다.

- 번들 줄이기: 쓰지 않는 코드 제거, 라우트별 코드 분할, 무거운 라이브러리 교체.
- 긴 작업 쪼개기: 입력 처리에서 화면 반영에 필요한 일만 먼저 하고 나머지는 양보한 뒤 처리.
- 무거운 계산은 Web Worker 로.
- 큰 목록은 보이는 부분만 렌더링(가상 스크롤).

### 순서: 측정 → 가장 큰 병목 → 다시 측정

```
현장 데이터에서 나쁜 지표 확인 (예: 모바일 LCP p75 = 4.1s)
   └▶ 실험실에서 재현, 워터폴·Performance 패널로 원인 단계 찾기
        └▶ 가장 큰 원인 하나만 고치기 (예: LCP 이미지 1.8MB → 180KB)
             └▶ 배포 후 현장 지표가 실제로 내려왔는지 확인
```

## 직접 해 보기

세 가지를 숫자로 확인한다. 레이아웃 이동 점수 계산, 평균과 p75 의 차이, 텍스트 압축 효과다.

```python
import gzip, random, statistics

# 1) 레이아웃 이동 점수 = 영향 비율 × 거리 비율
def layout_shift(vw, vh, el_top, el_h, moved):
    """세로로만 움직이는 전체 너비 요소. 화면 밖 부분은 잘라낸다."""
    top = el_top
    bottom = min(vh, el_top + el_h + moved)          # 이전 위치 ∪ 새 위치
    impact = vw * max(0, bottom - top) / (vw * vh)
    distance = moved / max(vw, vh)
    return impact, distance, impact * distance

for label, moved in [("광고가 늦게 끼어들어 본문이 200px 밀림", 200),
                     ("자리를 미리 잡아 둠(aspect-ratio)", 0)]:
    i, d, s = layout_shift(400, 800, el_top=100, el_h=500, moved=moved)
    print(f"{label}: impact={i:.3f} distance={d:.3f} score={s:.3f}")

# 2) 평균이 아니라 75번째 백분위로 본다
random.seed(7)
lcp = [random.lognormvariate(0.5, 0.45) for _ in range(1000)]   # 가상의 LCP(초)
lcp += [random.uniform(5, 9) for _ in range(300)]               # 느린 회선 사용자 약 23%
p75 = statistics.quantiles(lcp, n=100)[74]
print(f"평균 {statistics.mean(lcp):.2f}s, 중앙값 {statistics.median(lcp):.2f}s, p75 {p75:.2f}s "
      f"-> {'좋음' if p75 <= 2.5 else '개선 필요'}")

# 3) 텍스트 리소스 압축
html = "".join(f"<li class='item'><a href='/p/{n}'>상품 {n}</a><span class='price'>{n}00원</span></li>\n"
               for n in range(500))
raw = html.encode()
print(f"HTML {len(raw):,} B -> gzip {len(gzip.compress(raw)):,} B")
```

실행 결과:

```
광고가 늦게 끼어들어 본문이 200px 밀림: impact=0.875 distance=0.250 score=0.219
자리를 미리 잡아 둠(aspect-ratio): impact=0.625 distance=0.000 score=0.000
평균 2.99s, 중앙값 1.93s, p75 4.08s -> 개선 필요
HTML 44,170 B -> gzip 4,143 B
```

읽는 법은 다음과 같다.

- 400×800 화면에서 500px 높이 본문이 200px 밀리면, 이전 위치와 새 위치를 합친 영역이 화면의 87.5% 이고 이동 거리는 긴 변 800px 의 25% 라 점수는 약 0.22 다. 이 한 번만으로 좋음 기준 0.1 을 넘는다. 자리를 미리 잡아 두면 이동 거리가 0 이라 점수도 0 이다.
- 가상의 LCP 분포에서 중앙값은 1.93초로 좋아 보이지만, 느린 회선 사용자가 섞이자 p75 는 4.08초가 됐다. 평균이나 중앙값만 보고 있었다면 놓쳤을 문제다.
- 반복이 많은 HTML 은 gzip 으로 약 10분의 1 이 됐다. 실제 비율은 내용에 따라 다르다.

브라우저에서는 개발자 도구 콘솔에 `PerformanceObserver` 를 등록해 `largest-contentful-paint`, `layout-shift` 항목을 직접 받아 볼 수 있다.

## 현업에서는

- **성능 예산**: "메인 번들 gzip 후 몇 KB 이하", "LCP p75 2.5초 이하" 같은 예산을 정하고 CI 에서 넘으면 빌드를 실패시킨다. 성능은 한번 고쳐도 기능이 쌓이며 다시 나빠지기 때문이다.
- **이미지가 1순위인 경우가 많다**: LCP 요소가 대표 이미지인 페이지가 흔하고, 원본 사진을 그대로 올린 경우가 많다. 이미지 변환 파이프라인 하나로 큰 개선을 얻는다.
- **캐시 헤더 점검**: 해시가 붙은 파일에 캐시가 꺼져 있거나, 반대로 HTML 이 길게 캐시되어 배포 후에도 옛 화면이 보이는 사고가 반복된다. 응답 헤더를 직접 확인한다.
- **홈랩 서비스**: k3s 위의 웹 서비스도 인그레스 컨트롤러에서 압축을 켜고, 정적 자원에 캐시 헤더를 주는 것만으로 느린 회선에서의 체감이 달라진다. 서버 CPU 가 한가한데 느리다면 대개 클라이언트 쪽 병목이다.

## 확인 문제

1. Core Web Vitals 세 지표와 각각의 "좋음" 기준을 쓰라.
2. 성능 지표를 평균이 아니라 75번째 백분위로 보는 이유는?
3. LCP 이미지에 `loading="lazy"` 를 주면 안 되는 이유는?
4. 해시가 붙은 정적 파일과 HTML 문서의 캐시 정책은 어떻게 달라야 하는가.
5. INP 가 나쁠 때 가장 먼저 의심할 원인과 대응 두 가지는?

### 풀이

1. LCP 2.5초 이내, INP 200ms 이하, CLS 0.1 이하.
2. 평균은 빠른 다수가 느린 소수를 가린다. p75 는 사용자 넷 중 셋 이상이 그 수준 이하의 경험을 하는지를 보여 준다.
3. 지연 로딩은 이미지가 화면 근처에 올 때까지 요청을 미루므로 가장 중요한 콘텐츠가 늦게 뜬다. LCP 이미지는 오히려 우선순위를 높인다.
4. 해시 파일은 내용이 바뀌면 이름이 바뀌므로 아주 길게(immutable) 캐시하고, HTML 은 새 배포를 바로 반영하도록 짧게 캐시하거나 매번 재검증한다.
5. 메인 스레드의 긴 자바스크립트 작업. 작업을 쪼개 양보하거나 Web Worker 로 옮기고, 번들·렌더링 양을 줄인다.

## 더 읽을거리 (References)

- web.dev, *Web Vitals*: <https://web.dev/articles/vitals>
- web.dev, *Cumulative Layout Shift (CLS)*: <https://web.dev/articles/cls>
- W3C, *Navigation Timing Level 2*: <https://www.w3.org/TR/navigation-timing-2/>
- RFC 9111, *HTTP Caching*: <https://www.rfc-editor.org/rfc/rfc9111>
