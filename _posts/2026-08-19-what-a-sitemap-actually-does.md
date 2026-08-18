---
layout: post
title: "sitemap.xml 을 켰다 — 그리고 666개 URL 을 전부 열어봤다"
date: 2026-08-19 01:05:00 +0900
last_modified_at: 2026-08-19 01:40:00 +0900
categories: [engineering, web]
tags: [sitemap, seo, jekyll, github-pages, robots-txt, 검증]
---

어제 이 블로그의 `sitemap.xml` 은 **404** 였다. `_config.yml` 에 한 줄 넣었더니 **200** 이 됐다.

여기서 끝내면 딱 좋은 이야기다. 그런데 나는 바로 앞 글에서 [수치가 "어떻게 뽑았냐"는 질문을 견디는가](/2026/08/18/numbers-that-survive-being-asked-how/) 를 따졌다. 그 기준을 내가 방금 만든 파일에 적용하지 않으면 그 글은 거짓말이 된다. 그래서 생성된 666개 URL 을 전부 열어봤다.

**결론부터: 200 은 켜졌다는 뜻이지, 맞다는 뜻이 아니었다.** 결함 두 개를 찾았다.

---

## 1. 사이트맵이 실제로 하는 일 — 그리고 하지 않는 일

사이트맵은 2005년에 나온 프로토콜이고, 15년 넘게 사실상 바뀌지 않았다.[^ping] 표준이 요구하는 건 놀랄 만큼 적다. `<urlset>` 과 URL 당 `<loc>` 하나가 **필수의 전부**이고, `<lastmod>` · `<changefreq>` · `<priority>` 는 전부 선택이다.[^spec]

구글의 설명은 이렇다 — "사이트맵은 사이트에서 **당신이 중요하다고 생각하는** 페이지와 파일이 무엇인지 검색 엔진에 알려준다."[^gsc-overview] 색인해 준다는 약속이 아니라, 크롤 스케줄링에 쓰이는 **입력값**이다.

하지 않는 일 쪽이 더 중요하다.

- **`priority` 는 순위에 영향이 없다.** 표준 문서 자체가 "당신이 매긴 priority 가 검색 결과에서 URL 의 위치에 영향을 줄 가능성은 낮다" 고 못 박는다.[^spec] 구글은 2023년 공지에서 더 직설적으로 썼다 — "구글은 여전히 `changefreq` 나 `priority` 요소를 **전혀 사용하지 않는다**."[^ping]
- **`changefreq` 는 명령이 아니다.** 표준은 "힌트이지 명령이 아니다(a hint and not a command)" 라고 표현한다.[^spec]
- **애초에 필요 없을 수도 있다.** 구글은 "사이트가 작고(대략 500페이지 이하) 내부 링크가 충분하면 사이트맵이 필요 없을 수도 있다" 고 안내한다.[^gsc-overview]

마지막 항목은 그냥 넘길 게 아니라 **내 사이트에 대입해 봐야 하는 조건**이다. 뒤에서 숫자로 확인한다.

---

## 2. 666개를 세어서 대사(對査)했다

생성된 파일을 받아서 태그를 전수 집계했다.

```
$ grep -o "<[a-z:]*>" sitemap.xml | sort | uniq -c | sort -rn
 666 <url>
 666 <loc>
 603 <lastmod>
```

`changefreq` 0개, `priority` 0개. 구글이 안 쓴다고 명시한 두 필드를 애초에 만들지 않는다 — 플러그인의 판단이 옳다.

그 다음, **666이라는 숫자가 어디서 왔는지** 를 리포와 대사했다. 숫자가 딱 맞아떨어지지 않으면 어딘가 조용히 빠지거나 새고 있다는 뜻이다.

| 구성                                | 개수    | 확인 방법                                  |
| ----------------------------------- | ------- | ------------------------------------------ |
| `_posts/` 의 글 파일                | 604     | `ls _posts/*.md \| wc -l`                  |
| − `published: false` (미발행)       | −2      | 두 파일 front matter 확인, 실제 URL 도 404 |
| = 사이트맵의 글 URL                 | **602** | `/YYYY/MM/DD/…` 패턴 매칭                  |
| + 페이지네이션 `/page2/`…`/page61/` | +60     | `paginate: 10` 설정의 부산물               |
| + `/`, `/about/`, `/categories/`    | +3      |                                            |
| + PDF 1개                           | +1      | `/assets/files/…​.pdf`                     |
| **합계**                            | **666** | ✔ 일치                                     |

한 건도 남지 않고 맞았다. 즉 **사이트맵은 리포가 아니라 빌드된 사이트를 반영한다.** `published: false` 인 글 2개는 사이트맵에도 없고 실제로도 404다 — 이건 정상 동작이다.

PDF 가 왜 들어갔는지도 확인했다. 플러그인 소스에 포함 확장자가 하드코딩돼 있다 — `.htm .html .xhtml .pdf .xml`.[^plugin-src] 우연이 아니라 설계다.

크기도 한계 대비로 보면 여유롭다. 표준 한 파일 상한은 **50,000 URL / 50MB(비압축)** 인데[^spec] 내 파일은 666 URL / 93,911 바이트 — URL 상한의 1.3%, 용량 상한의 0.2%다. 사이트맵 인덱스로 쪼갤 일은 당분간 없다.

그리고 아까 미룬 질문: 구글의 "500페이지 이하면 필요 없을 수도" 기준에 내 사이트는 걸리는가. 구글은 이 계수에 대해 "**검색 결과에 나와야 한다고 생각하는 페이지만** 총계에 넣으라" 고 단서를 단다.[^gsc-overview] 페이지네이션 60개와 인덱스 3개를 빼면 602. 그래도 500을 넘는다. 켤 이유는 있었다.

---

## 3. 결함 ① — `lastmod` 가 전부 "수정일"이 아니라 "발행일"이다

표준 문서는 `lastmod` 에 대해 이렇게 쓴다 — "**해당 날짜는 링크된 페이지가 마지막으로 수정된 날짜여야 하며, 사이트맵이 생성된 날짜가 아니다.**"[^spec]

내 사이트맵에서 바로 앞 글의 항목은 이렇다.

```xml
<loc>https://myoungsoo7.github.io/2026/08/18/numbers-that-survive-being-asked-how/</loc>
<lastmod>2026-08-18T21:15:00+09:00</lastmod>
```

그런데 그 파일의 마지막 수정은 git 이 알고 있다.

```
$ git log -1 --format="%ad" --date=iso -- _posts/2026-08-18-numbers-that-survive-being-asked-how.md
2026-08-19 00:25:11 +0900
```

**어긋난다.** 나는 그 글을 어젯밤에 고쳤는데(다른 글로 가는 상호 참조를 넣었다), 사이트맵은 여전히 발행 시각을 말하고 있다.

우연이 아니라 구조적이다. 플러그인 문서가 `lastmod` 의 우선순위를 명시한다 — ① `jekyll-last-modified-at` 플러그인의 파일시스템 수정시각(단 **GitHub Pages 자동 빌드와 비호환**), ② front matter 의 `last_modified_at:`, ③ 없으면 **글의 작성일(`post.date`)**.[^plugin] 내 리포에서 `last_modified_at` 을 쓰는 글은 **604개 중 0개**다. 그러니 604개 전부가 ③으로 떨어진다. 내 사이트맵의 `lastmod` 는 전량 발행일이다.

대가는 무엇인가. 구글은 "`lastmod` 값이 **일관되고 검증 가능하게**(예: 페이지의 실제 마지막 수정과 대조해서) 정확할 때 그 값을 사용한다" 고 쓴다.[^gsc-build] 2023년 공지는 더 구체적이다 — "현실과 일관되게 맞아야 한다. 페이지가 7년 전에 바뀌었는데 `lastmod` 에 어제 바뀌었다고 말하면, 결국 우리는 당신의 마지막 수정일을 더 이상 믿지 않게 된다."[^ping]

**여기서 정직하게 짚자.** 구글이 경고하는 건 _과대_ 신고(안 바뀌었는데 바뀌었다고 하는 것)이고, 내 경우는 반대인 _과소_ 신고다. 그러니 "신뢰를 잃는" 시나리오는 내게 해당하지 않는다. 내가 실제로 치르는 비용은 다른 쪽이다 — **고친 글이 고쳐졌다고 말하지 못한다.** `lastmod` 는 이미 크롤된 URL 의 재크롤 스케줄링 신호인데[^ping] 내 신호는 영원히 발행일에 고정돼 있다.

고치는 방법은 문서에 있다: 수정할 때 front matter 에 `last_modified_at:` 을 같이 갱신하는 것.[^plugin] 604개를 소급할 생각은 없고, 앞으로 실질적으로 고치는 글에만 붙이려 한다. 구글도 "확신이 있는 페이지에만 `lastmod` 를 써도 된다", "사이드바나 푸터의 사소한 변경이면 갱신하지 않아도 된다" 고 허용한다.[^ping] → 실제로 적용한 결과는 [8. 후기](#postscript).

---

## 4. 결함 ② — 페이지네이션 60개가 들어가 있다

`/page2/` 부터 `/page61/` 까지, 글 목록을 10개씩 끊어 보여주는 페이지 60개가 사이트맵에 있다. 전체의 **9%**다.

구글의 지침은 "사이트맵에는 **구글 검색 결과에 나오기를 원하는** URL 을 넣으라" 이다.[^gsc-build] `/page37/` 이 검색 결과에 뜨기를 원하는 사람은 없다. 그 페이지에 고유한 내용은 없고, 이미 사이트맵에 개별 URL 로 다 들어있는 글들의 요약 목록일 뿐이다.

플러그인은 제외 방법을 제공한다 — front matter 에 `sitemap: false`, 또는 `_config.yml` 의 `defaults` 로 경로 글로브 지정.[^plugin] 내 리포에서 `sitemap: false` 를 쓰는 파일은 현재 **0개**다.

처음 이 글을 올릴 때는 "제외하는 정확한 방법은 별도로 측정해서 확인할 문제" 라고 미뤄 뒀다. 30분 뒤에 확인했고, 예상과 달랐다. → [8. 후기](#postscript)

---

## 5. 함정 — Gemfile 에 넣어도 GitHub Pages 에선 안 먹는다

나는 어제 두 파일을 고쳤다. `_config.yml` 의 `plugins:` 목록과 `Gemfile` 의 `gem "jekyll-sitemap"`.

**둘 중 하나만 일했다.** 플러그인 README 가 명시한다 — "GitHub Pages gem 은 **Gemfile 에 포함된 모든 플러그인을 무시한다.** `_config.yml` 에도 넣지 않고 Gemfile 에만 `jekyll-sitemap` 을 넣으면 **플러그인은 동작하지 않는다.**"[^plugin]

즉 사이트맵을 켠 것은 `_config.yml` 한 줄이고, Gemfile 한 줄은 배포되는 빌드에 아무 영향이 없다. 로컬에서 `bundle exec jekyll serve` 를 돌릴 때의 일관성 정도가 전부다. 남겨두긴 했지만 **효과가 있다고 말하면 거짓말**이라 적어둔다.

README 가 이 문단을 따로 둔 이유가 짐작된다. Gemfile 에만 넣고 "설치했는데 안 되네" 하는 사람이 많았을 것이다. 실패가 조용하다 — 에러도, 경고도 없고, 그냥 `sitemap.xml` 이 404 로 남는다.

---

## 6. 덤 — `robots.txt` 도 같이 생긴다

리포에는 `robots.txt` 가 없다. 그런데 사이트는 200으로 응답한다.

```
$ curl https://myoungsoo7.github.io/robots.txt
Sitemap: https://myoungsoo7.github.io/sitemap.xml
```

플러그인 소스를 보면 이유가 한 줄이다.[^plugin-src]

```ruby
@site.pages << sitemap unless file_exists?("sitemap.xml")
@site.pages << robots  unless file_exists?("robots.txt")
```

**이미 있으면 안 건드리고, 없으면 만든다.** 그리고 그 `robots.txt` 는 사이트맵 위치를 가리키는 한 줄이다.

이게 왜 유용한가. 구글은 사이트맵을 알리는 경로로 **robots.txt 와 Search Console** 두 가지를 든다.[^ping] 그리고 예전에 쓰이던 세 번째 경로 — 사이트맵 URL 을 검색엔진 엔드포인트에 HTTP 로 찔러 넣는 "ping" — 은 **2023년에 폐기됐다.** 구글은 인증 없는 제출의 "대다수가 스팸으로 이어졌다" 는 이유를 들며 6개월 후 404 를 반환하겠다고 공지했다.[^ping]

그러니 지금 사이트맵을 알리는 실질적 수단은 robots.txt 와 Search Console 뿐이고, 그중 하나는 플러그인이 자동으로 처리해 준 것이다. 반대로 말하면 — **이미 `robots.txt` 를 직접 관리하는 사이트라면 플러그인이 손대지 않으므로, `Sitemap:` 줄은 직접 넣어야 한다.**

---

## 7. 정리

시간 순으로 실제 일어난 일은 이렇다.

1. `_config.yml` 에 `- jekyll-sitemap` 한 줄 추가 → 푸시
2. GitHub Pages 재빌드 대기 — 20초 간격으로 폴링해 **약 2분** 만에 404 → 200
3. `sitemap.xml` 다운로드, 666개 URL 전수 확인
4. 결함 2건 발견 (`lastmod` 전량 발행일, 페이지네이션 60개 포함)
5. 함정 1건 확인 (Gemfile 줄은 배포 빌드에 무효)

2단계에서 멈췄으면 "사이트맵 켰음 ✅" 으로 끝났을 것이다. 그리고 그 체크 표시는 **틀리지 않았다** — 파일은 실제로 200이고 666개 URL 이 들어있다. 다만 그 체크 표시가 **답하지 않는 질문**이 있었을 뿐이다. 안에 들어간 게 맞는 URL 인가? 날짜가 사실인가? 내가 고친 두 파일이 둘 다 일을 했는가?

앞 글에서 나는 "아무도 지키지 않는 수치는 조용히 거짓이 된다" 고 썼다. 여기서 지키는 사람은 아무도 없었다. 사이트맵은 조용히 생성되고(플러그인 설명 문구 자체가 "silently generate" 다), 조용히 배포되고, 아무도 열어보지 않는다. **200 은 문이 열렸다는 신호이지, 안에 있는 게 맞다는 신호가 아니다.**

---

## 8. 후기 — 30분 뒤 실제로 고쳤다 {#postscript}

이 글을 올린 직후에 4절(페이지네이션)과 3절(`lastmod`)을 실제로 손봤다. **4절은 예상이 틀렸다.**

### ① 페이지네이션 제외 — `defaults` 글로브로는 불가능하다

플러그인 README 는 제외 방법으로 `_config.yml` 의 `defaults` 경로 글로브를 안내한다.[^plugin] 나도 그걸 쓸 생각이었다. 안 된다.

이유는 `jekyll-paginate` 의 소스 한 줄에 있다.[^paginate-src]

```ruby
newpage = Page.new(site, site.source, page.dir, page.name)
newpage.dir = Pager.paginate_path(site, num_page)
```

**페이지네이션 페이지는 `index.html` 의 Page 객체를 그대로 복제해서 만든다.** 출력 경로(`dir`)만 `/page2/` 로 바꿀 뿐, 소스 파일은 여전히 `index.html` 이다. Jekyll 의 `defaults` 는 _소스 경로_ 로 매칭하므로, `path: index.html` 글로브는 **홈과 페이지네이션 61개를 하나도 구분하지 못한다.** 둘 중 하나만 고르는 방법이 없다.

같은 이유로, 쓸 수 있는 수단은 하나로 좁혀진다 — `index.html` front matter 에 `sitemap: false` 를 두는 것. 복제된 Page 들이 front matter 까지 상속하므로 **61개가 한꺼번에 빠진다. 홈까지 포함해서.**

그 대가를 받아들이기로 했다. 루트 URL 은 모든 페이지의 nav 에서 링크되고 `robots.txt` 가 가리키는 호스트 자체다. 사이트맵에서 빠져도 발견성 손실이 사실상 없다.

측정 결과, 예측과 정확히 일치했다.

|                                | 이전 | 이후        |
| ------------------------------ | ---- | ----------- |
| 전체 URL                       | 667  | **606**     |
| `/pageN/`                      | 60   | **0**       |
| 홈 `/`                         | 있음 | 없음 (의도) |
| `/about/`, `/categories/`, PDF | 있음 | 있음        |

667 − 61 = 606. 한 건도 어긋나지 않았다. (앞 절들의 666 은 이 글이 올라가기 전 숫자이고, 667 은 이 글이 추가된 뒤 숫자다.)

**중요한 구분** — 사이트맵에서 빼는 것은 `noindex` 가 아니다. 배포된 사이트에서 두 URL 은 그대로 살아있다.

```
$ curl -o /dev/null -w '%{http_code}' https://myoungsoo7.github.io/        # 200
$ curl -o /dev/null -w '%{http_code}' https://myoungsoo7.github.io/page2/  # 200
```

"크롤해 달라고 목록에 올리지 않는 것" 과 "색인하지 말라고 지시하는 것" 은 다른 일이다. 후자를 원했다면 `robots` 메타 태그를 썼어야 한다.

### ② `lastmod` — 이제 사실을 말한다

3절에서 지적한 대로, 앞 글의 `lastmod` 는 발행 시각(`21:15`)이었지만 실제 수정은 `00:25` 였다. front matter 에 git 이 아는 실제 값을 넣었다.

```yaml
last_modified_at: 2026-08-19 00:25:11 +0900
```

배포 후 사이트맵을 다시 받아 확인했다.

```xml
<loc>https://myoungsoo7.github.io/2026/08/18/numbers-that-survive-being-asked-how/</loc>
<lastmod>2026-08-19T00:25:11+09:00</lastmod>
```

**어제 21:15 → 오늘 00:25.** 이제 그 날짜는 사실이다. 604개를 소급하지는 않았다 — 앞으로 실질적으로 고치는 글에만 붙인다. 그리고 지금 읽고 있는 이 글에도 붙였다. 이 절을 추가한 것이 곧 "실질적인 수정" 이니까.

### 배운 것

미리 단정하지 않고 "별도로 측정해서 확인할 문제" 로 미뤄 둔 판단이 맞았다. 확인해 보니 **문서가 안내한 방법이 이 조합에서는 통하지 않았고**, 실제 해법은 "홈을 사이트맵에서 포기한다" 는 _트레이드오프_ 였다. 미뤄두지 않고 "글로브 한 줄이면 된다" 고 써 버렸다면, 그 문장은 앞 글에서 내가 비판한 것과 똑같은 종류의 — 아무도 확인하지 않은 — 주장이 됐을 것이다.

---

### 검증 방법

이 글의 모든 수치는 아래로 재현된다. 사이트 주소만 바꾸면 다른 Jekyll 사이트에도 그대로 쓸 수 있다.

```bash
curl -s https://myoungsoo7.github.io/sitemap.xml -o sitemap.xml
grep -o "<[a-z:]*>" sitemap.xml | sort | uniq -c | sort -rn   # 태그 전수 집계
grep -c "<url>" sitemap.xml                                    # URL 총수
wc -c < sitemap.xml                                            # 50MB 한계 대비
curl -s https://myoungsoo7.github.io/robots.txt                # Sitemap: 줄 존재 확인
ls _posts/*.md | wc -l                                         # 리포 글 수 (대사용)
grep -rl "last_modified_at" _posts/ | wc -l                    # lastmod 정확도의 상한
```

`lastmod` 가 사실인지 보는 건 마지막 한 줄이다. **0이 나오면 당신의 사이트맵 날짜도 전부 발행일이다.**

---

[^spec]: sitemaps.org, _Sitemaps XML format_ — <https://www.sitemaps.org/protocol.html>. 필수/선택 태그 정의, `lastmod` 는 "링크된 페이지가 마지막으로 수정된 날짜여야 하며 사이트맵 생성 시각이 아니다", `changefreq` 는 "a hint and not a command", `priority` 는 "검색 결과에서 URL 위치에 영향을 줄 가능성은 낮다", 파일당 50,000 URL / 50MB 상한.

[^gsc-overview]: Google Search Central, _Learn about sitemaps_ — <https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview>. "사이트맵은 사이트에서 당신이 중요하다고 생각하는 페이지와 파일이 무엇인지 검색 엔진에 알려준다", "약 500페이지 이하의 작은 사이트… 에는 필요 없을 수도 있다(검색 결과에 나와야 한다고 생각하는 페이지만 총계에 포함)".

[^gsc-build]: Google Search Central, _Build and submit a sitemap_ — <https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap>. "Google uses the `lastmod` value if it's consistently and verifiably … accurate", "Google ignores `changefreq` and `priority` values", "사이트맵에는 구글 검색 결과에 나오기를 원하는 URL 을 넣으라", 50MB/50,000 URL 한계.

[^ping]: Gary Illyes, _Sitemaps ping endpoint is going away_, Google Search Central Blog, 2023-06-26 — <https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping>. ping 엔드포인트 폐기 및 사유("대다수가 스팸으로 이어졌다"), robots.txt·Search Console 제출은 유지, `lastmod` 는 "이미 발견한 URL 의 재크롤 스케줄링 신호", "현실과 일관되게 맞아야 한다", "changefreq·priority 를 전혀 사용하지 않는다".

[^plugin]: jekyll/jekyll-sitemap README — <https://github.com/jekyll/jekyll-sitemap>. GitHub Pages gem 은 Gemfile 의 플러그인을 무시하므로 `_config.yml` 의 `plugins` 에 반드시 넣어야 함, `lastmod` 우선순위 3단계, `sitemap: false` 및 `defaults` 글로브를 통한 제외.

[^paginate-src]: jekyll-paginate 소스, `lib/jekyll-paginate/pagination.rb` — <https://github.com/jekyll/jekyll-paginate/blob/master/lib/jekyll-paginate/pagination.rb>. `Page.new(site, site.source, page.dir, page.name)` 로 index.html 의 Page 를 복제하고 `dir` 만 `Pager.paginate_path` 로 교체한다 — 그래서 소스 경로가 index.html 로 동일해진다.

[^plugin-src]: jekyll-sitemap 소스, `lib/jekyll/jekyll-sitemap.rb` — <https://github.com/jekyll/jekyll-sitemap/blob/master/lib/jekyll/jekyll-sitemap.rb>. `unless file_exists?` 조건부 생성, `INCLUDED_EXTENSIONS = .htm .html .xhtml .pdf .xml`.

_이 글의 수치는 2026-08-19 01:00 KST 기준으로 이 블로그의 실제 배포본을 측정한 값이다. 666 · 604 · 602 · 60 · 603 · 93,911 은 모두 위 "검증 방법" 절의 명령으로 그 시점에 직접 얻었다. 1~7절의 숫자는 **결함을 고치기 전** 배포본 기준이다. 8절(후기)의 숫자는 고친 뒤 같은 명령으로 다시 측정한 값이므로, 지금 사이트맵을 받아보면 **606 / `/pageN/` 0개** 가 나온다._

## References

1. sitemaps.org — _Sitemaps XML format (protocol 0.9)_. <https://www.sitemaps.org/protocol.html>
2. Google Search Central — _Learn about sitemaps_. <https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview>
3. Google Search Central — _Build and submit a sitemap_. <https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap>
4. Gary Illyes — _Sitemaps ping endpoint is going away_. Google Search Central Blog, 2023-06-26. <https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping>
5. jekyll/jekyll-sitemap — README 및 `lib/jekyll/jekyll-sitemap.rb`. <https://github.com/jekyll/jekyll-sitemap>
6. jekyll/jekyll-paginate — `lib/jekyll-paginate/pagination.rb`. <https://github.com/jekyll/jekyll-paginate>
