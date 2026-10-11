---
layout: post
title: "배울 만한 GitHub Pages 기술 블로그 6선 — 글뿐 아니라 저장소까지 열어 볼 수 있는 블로그들"
date: 2026-10-12 00:17:39 +0900
categories: [Blog, Recommendation]
tags: [GitHub Pages, Jekyll, Hugo, Gatsby, Tech Blog, Machine Learning, Writing]
---

이 블로그도 GitHub Pages 위에서 Jekyll 로 돈다. 그래서 다른 GitHub Pages 블로그를 볼 때 좋은 점이 하나 있다. **글만이 아니라 블로그를 만든 저장소까지 공개돼 있다**는 것이다. 어떤 생성기를 쓰는지, 글을 어떻게 나누고 묶는지, 설정을 어떻게 했는지 직접 열어 볼 수 있다.

배울 점이 분명한 GitHub Pages 블로그 여섯 곳을 골랐다. 사이트와 저장소는 2026-10-12 에 직접 열어 확인했다.

| 블로그 | 분야 | 생성기 | 저장소 |
|---|---|---|---|
| [Lil'Log](https://lilianweng.github.io/) | 머신러닝 연구 장문 | Hugo (페이지 메타 태그 기준) | [lilianweng/lilianweng.github.io](https://github.com/lilianweng/lilianweng.github.io) |
| [기계인간 John Grib](https://johngrib.github.io/) | 한국어, 개발·독서 위키 | Jekyll | [johngrib/johngrib.github.io](https://github.com/johngrib/johngrib.github.io) |
| [Andrej Karpathy blog](https://karpathy.github.io/) | 딥러닝 | Jekyll | [karpathy/karpathy.github.io](https://github.com/karpathy/karpathy.github.io) |
| [Jay Alammar](https://jalammar.github.io/) | 머신러닝 시각화 | Jekyll | [jalammar/jalammar.github.io](https://github.com/jalammar/jalammar.github.io) |
| [colah's blog](https://colah.github.io/) | 신경망 해석·시각화 | 정적 HTML (생성 결과물) | [colah/colah.github.io](https://github.com/colah/colah.github.io) |
| [Evans Library](https://evan-moon.github.io/) | 한국어, 프론트엔드·CS | Gatsby (페이지 메타 태그 기준) | [evan-moon/evan-moon.github.io](https://github.com/evan-moon/evan-moon.github.io) |

생성기는 저장소에 `_config.yml`·`_posts` 가 있으면 Jekyll 로, 그렇지 않으면 페이지의 `<meta name="generator">` 값으로 판별했다. Hugo 와 Gatsby 블로그의 저장소에는 빌드 결과물이 올라가 있어서, 원본 글 파일까지는 볼 수 없다.

## 1. Lil'Log — 출처를 다는 글의 교과서

**[lilianweng.github.io](https://lilianweng.github.io/)**

머신러닝의 한 주제를 잡으면 관련 연구를 끝까지 정리하는 장문 블로그다. 예를 들어 [LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) 는 에이전트를 계획(Planning)·기억(Memory)·도구 사용(Tool Use)으로 나눠 정리한 글이다. 2026년 7월 글 *Scaling Laws, Carefully* 처럼 최근까지 글이 올라온다.

**배울 점:** 주장마다 논문을 붙이고, 글 끝에 참고문헌을 모은다. "검증한 것만 쓴다" 는 원칙을 장문에서 어떻게 지키는지 보여준다.

## 2. 기계인간 John Grib — 글끼리 엮이는 위키형 블로그

**[johngrib.github.io](https://johngrib.github.io/)**

한국어 블로그다. Jekyll 로 만들었는데 일반 블로그처럼 날짜순 글(`_posts`)만 있는 게 아니라, **위키 문서**(`_wiki`)를 따로 두고 문서끼리 촘촘하게 링크한다. 저장소의 `_wiki` 폴더 최상위에만 항목이 334개다. 저장소도 활발해서 조회 이틀 전에도 푸시가 있었다.

**배울 점:** 이 블로그와 구조가 가장 비슷하다(Jekyll, GitHub Pages). 시간순 글과 주제별로 계속 고쳐 쓰는 문서를 **분리하는 방식**은 그대로 가져올 만하다. 같은 주제를 여러 글에서 다룰 때, 위키 문서 하나를 허브로 두고 글들이 그곳을 가리키게 하면 된다.

## 3. Andrej Karpathy blog — 적게 쓰고 오래 남는 글

**[karpathy.github.io](https://karpathy.github.io/)**

저장소의 `_posts` 에 글이 23편뿐이다. 그런데 그중 여러 편이 딥러닝 입문자에게 고전처럼 읽힌다. [The Unreasonable Effectiveness of Recurrent Neural Networks](https://karpathy.github.io/2015/05/21/rnn-effectiveness/)(2015), [A Recipe for Training Neural Networks](https://karpathy.github.io/2019/04/25/recipe/)(2019)가 대표적이고, 최근 글로 *microgpt* 가 있다.

**배울 점:** 기본 Jekyll 구성에 가까운 단순한 저장소다. 화려한 테마 없이도 **글 자체로** 읽히는 블로그가 된다는 증거다. 실험 코드를 직접 짜서 결과를 보여주는 방식은 홈랩 실험 글에도 그대로 통한다.

## 4. Jay Alammar — 그림으로 설명하기

**[jalammar.github.io](https://jalammar.github.io/)**

사이트 제목 그대로 *"Visualizing machine learning one concept at a time."* 다. 대표작 [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/) 는 트랜스포머를 단계별 그림으로 풀어낸 글이다. 저장소가 MIT 라이선스로 공개돼 있다.

**배울 점:** 복잡한 구조를 설명할 때 **그림 한 장이 문단 열 개를 대신한다.** 아키텍처나 데이터 흐름을 다룰 때 다이어그램부터 그리고 글을 붙이는 순서를 참고할 만하다.

## 5. colah's blog — 이해를 위한 시각화

**[colah.github.io](https://colah.github.io/)**

신경망을 "왜 그렇게 동작하는지" 로 설명하는 블로그다. [Understanding LSTM Networks](https://colah.github.io/posts/2015-08-Understanding-LSTMs/)(2015)가 가장 유명하고, 첫 화면에는 *Transformer Circuits*, *Multimodal Neurons*, *Circuits* 같은 신경망 해석 연구가 올라와 있다. 저장소 마지막 푸시가 2024년이라 갱신은 뜸하다.

**배울 점:** 오래된 글도 **설명이 정확하면** 계속 읽힌다. 유행을 좇는 글보다 개념을 바로 세우는 글이 수명이 길다.

## 6. Evans Library — 한국어로 CS 를 쉽게

**[evan-moon.github.io](https://evan-moon.github.io/)**

한국어 블로그다. 프론트엔드와 컴퓨터 과학 기초를 친절하게 풀어 쓴다. Gatsby 로 만들어 저장소에는 빌드 결과물이 올라가 있고, 조회 이틀 전에도 갱신이 있었다.

**배울 점:** 같은 GitHub Pages 라도 생성기에 따라 **저장소에서 배울 수 있는 범위가 다르다.** Jekyll 블로그는 원본 글과 설정이 보이고, 빌드 결과만 올리는 블로그는 화면과 글로 배워야 한다.

## 이 블로그에 가져올 것

| 출처 | 가져올 것 |
|---|---|
| Lil'Log | 큰 주제는 연재 후 **종합편** 하나로 묶고, 참고문헌을 모은다 |
| John Grib | 시간순 글과 별도로 **주제 허브 문서**를 두고 내부 링크를 촘촘히 |
| Karpathy | 테마보다 **직접 돌린 실험과 결과**를 앞세운다 |
| Jay Alammar | 구조 설명은 **다이어그램 먼저** |
| colah | 유행보다 **개념을 바로 세우는** 글 |

좋은 기술 블로그의 공통점은 화려한 디자인이 아니었다. **무엇을 주장하고, 어떻게 확인했고, 다른 글과 어떻게 이어지는지**가 분명하다는 것. 그리고 GitHub Pages 블로그라면, 그 비결이 저장소에 그대로 열려 있다.

---

## References

- 각 블로그 사이트와 GitHub 저장소 (위 표의 링크, 2026-10-12 조회)
- 생성기 판별: 저장소 파일 구성(`_config.yml`, `_posts`) 및 각 페이지의 `<meta name="generator">` 값
