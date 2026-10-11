---
layout: post
title: "블로그의 정점 5선 — 데이터·성능·개념·LLM·아키텍처를 1차 출처로 쓰는 개인 블로그"
date: 2026-10-12 00:20:56 +0900
categories: [Blog, Recommendation]
tags: [Tech Blog, Writing, Performance, Linux, LLM, Architecture]
---

[앞 글](https://myoungsoo7.github.io/2026/10/12/github-pages-tech-blogs-worth-learning-from/)에서는 **저장소까지 공개된** GitHub Pages 블로그 여섯 곳을 골랐다. 이번 다섯 곳은 기준이 다르다. 호스팅 방식과는 상관없다. 한 사람이 오랫동안 쓰면서 **그 분야에서 다른 글들이 근거로 인용하는 출처**가 된 개인 블로그들이다.

다섯 곳 모두 2026-10-12 에 직접 열어 확인했다. 아래 링크는 전부 그날 응답 200 을 받았고, 본문에 적은 사실은 링크된 페이지에서 확인한 것만 썼다.

| # | 블로그 | 한 줄 요약 | 이런 사람에게 |
|---|---|---|---|
| 7 | [danluu.com](https://danluu.com/) | 직접 잰 데이터로 통념을 깬다 | 주장보다 측정을 믿는 사람 |
| 8 | [brendangregg.com](https://www.brendangregg.com/) | 리눅스 성능 분석의 1차 출처 | 서버·노드를 튜닝하는 사람 |
| 9 | [jvns.ca](https://jvns.ca/) | 어려운 개념을 짧고 재밌게 | 네트워크·리눅스가 막막한 사람 |
| 10 | [simonwillison.net](https://simonwillison.net/) | LLM 도구를 매일 실험하고 기록 | AI 에이전트 흐름을 따라가려는 사람 |
| 11 | [martinfowler.com](https://martinfowler.com/) | 아키텍처·리팩터링의 고전 | 설계 용어의 원전을 찾는 사람 |

## 7. danluu.com — 데이터로 통념을 깨는 글

**[danluu.com](https://danluu.com/)** · Dan Luu

첫 화면에는 꾸밈이 없다. 날짜와 글 제목만 나열돼 있다. 대신 글마다 **직접 측정한 데이터**가 들어 있다.

- **[Keyboard latency](https://danluu.com/keyboard-latency/)**: "게이밍 키보드는 빠르다" 는 광고 문구를 로직 애널라이저로 직접 잰다. 동기부터가 측정이다. 옛 컴퓨터가 더 빠르게 느껴진다는 감각을 믿지 않고 고속 카메라로 키 입력부터 화면 갱신까지의 지연을 쟀다. 결과적으로 70~80년대 컴퓨터는 30~50ms 수준이었고, 현대 컴퓨터는 터미널에서 키를 누를 때 100~200ms 인 경우가 많았다고 보고한다.
  - 같은 계열의 [Terminal latency](https://danluu.com/term-latency/) 도 있다.
- **[In defense of simple architectures](https://danluu.com/simple-architectures/)**: 저자가 다닌 회사가 Python 모놀리스와 Postgres 로 된 평범한 CRUD 구조로 규모를 키운 경험을 바탕으로, 단순한 구조를 옹호한다.
- **[Major errors on this blog (and their corrections)](https://danluu.com/corrections/)**: 이 블로그에서 가장 배울 만한 페이지다. 2021년에 만든 **자기 글의 중대 오류 목록**이다. 무엇이 틀렸는지, 왜 틀렸는지를 분류해서 공개하고, 앞으로도 목록이 늘어날 거라고 적어 둔다.

**배울 점:** "검증된 수치만 쓴다" 는 원칙을 가장 극단까지 밀어붙인 사례다. 키보드 글에는 이런 문장이 있다. *성능을 주장하면서 벤치마크가 없으면, 그 주장은 아마 사실이 아니다.* 더 중요한 건 정정 페이지다. 틀린 걸 조용히 고치는 데서 끝내지 않고 **틀렸다는 기록을 남긴다.** 이 블로그에 그대로 들여올 만한 습관이다.

## 8. brendangregg.com — 리눅스 성능 분석의 1차 출처

**[brendangregg.com](https://www.brendangregg.com/)** · Brendan Gregg

홈페이지 소개에 따르면 저자는 현재 OpenAI 에서 ChatGPT 의 데이터센터 성능을 맡고 있고, 그 전에는 Netflix 에 있었다. 이 사이트는 블로그라기보다 **성능 분석 자료의 색인**에 가깝다.

- **[The USE Method](https://www.brendangregg.com/usemethod.html)**: 요약하면 *"모든 자원에 대해 사용률(Utilization)·포화(Saturation)·오류(Errors)를 확인하라"* 는 한 문장이다. 보잉 707 비상 체크리스트를 본떠 만든 점검 방법론이다. 저자는 이 방법으로 "서버 문제의 약 80% 를 5% 의 노력으로" 푼다고 쓴다. 이 수치는 저자 본인의 경험치이고 통제된 측정이 아니다.
- **[Linux Performance](https://www.brendangregg.com/linuxperf.html)**: 관측·벤치마크·튜닝 도구 지도를 모아 둔 페이지다. 그 밖에 다음 자료로 가는 링크가 한곳에 모여 있다.
  - Netflix 성능팀과 함께 쓴 *Linux Performance Analysis in 60,000 Milliseconds*(장애 초기 10개 명령)
  - 로드 애버리지 해설
  - 책 *Systems Performance* 2판(2020)과 *BPF Performance Tools*
- **[Flame Graphs](https://www.brendangregg.com/flamegraphs.html)**: 프로파일 결과를 한 장으로 보여주는 플레임 그래프를 만든 사람의 원문이다.

**배울 점:** 홈랩 노드를 볼 때 바로 쓸 수 있다. 노드가 느려지면 지표를 무작정 훑지 않는다. CPU·메모리·디스크·네트워크 각각에 USE 세 질문을 던지면 점검 순서가 생긴다. 무선 링크도 하나의 "자원" 으로 놓고 포화와 오류를 따로 재면, 대역폭 숫자 하나로 판단하는 실수를 피할 수 있다.

## 9. jvns.ca — 네트워크·리눅스를 짧고 재밌게

**[jvns.ca](https://jvns.ca/)** · Julia Evans

2026년 9월에도 새 글이 올라온 현역 블로그다. 첫 화면에 지금까지 쓴 모든 글이 주제별로 정리돼 있다. 프로그래밍 개념을 손그림 만화로 설명하는 [Wizard Zines](https://wizardzines.com/) 의 저자이기도 하다. *How DNS Works*, *Bite Size Networking!* 같은 진(zine)이 있고, 흑백 표지 진은 무료다.

- **[tcpdump is amazing](https://jvns.ca/blog/2016/03/16/tcpdump-is-amazing/)**: 시작부터 고백이다. tcpdump 출력을 처음 보고 겁먹어 포기했고, 지금도 그 필드의 뜻을 대부분 모른다고 쓴다. 그런 다음 "녹화는 tcpdump 로, 분석은 덜 무서운 Wireshark 로" 라는 실용적인 우회로를 보여준다.
- **[A debugging manifesto](https://jvns.ca/blog/2022/12/08/a-debugging-manifesto/)**: 디버깅 진의 서문이다. 첫 원칙은 *"Inspect, don't squash"* 다. 버그를 바로 덮지 말고, 무슨 일이 일어났는지 이해한 다음에 고치라는 뜻이다.

**배울 점:** **모른다는 걸 인정하고 시작하는 글쓰기**다. 전문가인 척하지 않는다. 그래서 독자는 "나만 모르는 게 아니구나" 하고 끝까지 읽는다. 기술 글은 아는 걸 과시하는 순간 읽히지 않는다는 걸 잘 보여준다.

## 10. simonwillison.net — LLM 도구를 매일 실험하고 기록

**[simonwillison.net](https://simonwillison.net/)** · Simon Willison

[소개 페이지](https://simonwillison.net/about/)에 따르면 저자는 Django 웹 프레임워크의 공동 창시자이고, 데이터 탐색 도구 Datasette 를 만들었다. 2002년부터 이 사이트에 글을 써 왔다.

- **[llms 태그](https://simonwillison.net/tags/llms/)**: 조회 시점에 이 태그에만 1,982편이 달려 있었다. 긴 에세이는 소수이고, 대부분은 새 모델·도구를 직접 돌려 본 짧은 기록, 인용, 링크 메모다.
- **[LLM](https://llm.datasette.io/)**: 저자가 만든 명령줄 도구다. 여러 회사의 모델과 로컬 모델에 같은 인터페이스로 프롬프트를 보내고, 프롬프트와 응답을 SQLite 에 저장한다.
- **[TIL](https://til.simonwillison.net/)**: "오늘 배운 것" 을 짧게 남기는 별도 사이트다.

**배울 점:** 두 가지다.

1. **이해충돌 공개 방식.** 소개 페이지에 이런 내용을 구체적으로 적어 둔다.
   - 후원 배너를 받기 시작한 시점
   - LLM 회사들로부터 사전 공개·무료 크레딧을 받는다는 사실
   - 돈을 받은 단 한 번의 예외

   AI 도구를 리뷰하는 글이라면 이 정도의 투명성이 기준선이다.
2. **짧게, 자주.** 완성된 장문만 글이 아니다. 실험 하나를 하면 그 결과를 바로 기록한다. 그렇게 쌓인 기록이 곧 그 분야의 연대기가 된다.

## 11. martinfowler.com — 아키텍처·리팩터링의 고전

**[martinfowler.com](https://martinfowler.com/)** · Martin Fowler

[소개 페이지](https://martinfowler.com/aboutMe.html)에 따르면 저자는 Thoughtworks 의 Chief Scientist 이고, 《Refactoring》과 《Patterns of Enterprise Application Architecture》를 썼다. 사이트에서 가장 자주 인용되는 건 두 종류다.

- **[Microservices](https://martinfowler.com/articles/microservices.html)**(James Lewis 와 공저, 2014-03-25): "마이크로서비스" 라는 말이 무엇을 가리키는지 정리한 글이다. 업계가 이 용어를 쓸 때 원전처럼 인용한다.
- **[Bliki](https://martinfowler.com/bliki/)**: 블로그와 위키를 합친 말로, 2003년에 시작했다. 용어 하나를 짧은 글 하나로 정의한다. 예를 들어 최근 글 [Sensible Default](https://martinfowler.com/bliki/SensibleDefault.html)(2026-09-29)는 "베스트 프랙티스" 대신 이 말을 쓰자고 한다. 맥락이 바뀌면 다시 따져 볼 수 있는 **출발점**이라는 뉘앙스가 있기 때문이다.
- 리팩터링 기법 목록은 별도 사이트 [refactoring.com](https://refactoring.com/) 에 있다.

**배울 점:** 저자는 소개 페이지에서 스스로 독창적인 아이디어를 내는 사람이 아니라고 말한다. 대신 남의 아이디어를 **알아보고 포장하는** 데 능하다고 쓴다. 용어 하나에 글 하나를 붙이는 Bliki 형식은 앞 글에서 본 위키형 블로그와 같은 발상이다. 개념이 흩어져 있다면 정의 페이지부터 만들고, 다른 글이 그 페이지를 가리키게 하면 된다.

## 다섯 곳의 공통점

1. **1차 출처가 된다.** 남의 글을 요약하지 않는다. 직접 재거나(danluu), 도구를 만들거나(Gregg·Willison), 용어를 정의한다(Fowler).
2. **틀림을 다루는 방식이 있다.** danluu 는 정정 목록을 둔다. Gregg 는 자기 수치를 경험치로 밝힌다. Evans 는 모른다고 먼저 말한다. Willison 은 이해충돌을 공개한다.
3. **오래 쓴다.** 다섯 곳 모두 몇 년이 아니라 십수 년 단위로 쌓인 아카이브다.

이 중 하나만 따라 한다면 danluu 의 **정정 페이지**를 권한다. 비용은 거의 들지 않는다. 그런데도 블로그 전체의 신뢰도를 바꾼다.

## References

- Dan Luu, [Major errors on this blog (and their corrections)](https://danluu.com/corrections/) · [Keyboard latency](https://danluu.com/keyboard-latency/) · [Terminal latency](https://danluu.com/term-latency/) · [In defense of simple architectures](https://danluu.com/simple-architectures/)
- Brendan Gregg, [Homepage](https://www.brendangregg.com/) · [The USE Method](https://www.brendangregg.com/usemethod.html) · [Linux Performance](https://www.brendangregg.com/linuxperf.html) · [Flame Graphs](https://www.brendangregg.com/flamegraphs.html)
- Julia Evans, [jvns.ca](https://jvns.ca/) · [tcpdump is amazing](https://jvns.ca/blog/2016/03/16/tcpdump-is-amazing/) (2016) · [A debugging manifesto](https://jvns.ca/blog/2022/12/08/a-debugging-manifesto/) (2022) · [Wizard Zines](https://wizardzines.com/)
- Simon Willison, [About](https://simonwillison.net/about/) · [llms 태그](https://simonwillison.net/tags/llms/) · [LLM CLI](https://llm.datasette.io/) · [TIL](https://til.simonwillison.net/)
- Martin Fowler, [About](https://martinfowler.com/aboutMe.html) · James Lewis & Martin Fowler, [Microservices](https://martinfowler.com/articles/microservices.html) (2014) · [Bliki](https://martinfowler.com/bliki/) · [Sensible Default](https://martinfowler.com/bliki/SensibleDefault.html) (2026) · [refactoring.com](https://refactoring.com/)
