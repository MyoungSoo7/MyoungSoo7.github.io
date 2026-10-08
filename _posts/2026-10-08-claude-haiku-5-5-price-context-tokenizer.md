---
layout: post
title: "Claude Haiku 5.5 출시 — '90% 인하'와 '100만 컨텍스트'를 청구서 기준으로 다시 읽기"
date: 2026-10-08 19:30:00 +0900
categories: [AI]
tags: [anthropic, claude, haiku-5-5, llm-pricing, context-window, tokenizer, prompt-caching]
---

Anthropic 이 2026-10-07 **Claude Haiku 5.5** 를 발표했다([공식 발표](https://www.anthropic.com/claude-haiku-5-5)). 요약하면 "반복적인 요약·분류·쿼리 작업용 경량 모델, 10 만 토큰 이하 가격 90% 인하, 컨텍스트 100 만 토큰"이다. 세 가지 모두 공식 문서로 확인된다. 다만 **청구서에 찍히는 숫자**로 바꿔 보려면 조건 몇 가지를 같이 봐야 한다. 이 글은 그 조건을 정리한다.

> 기준: Anthropic 공식 발표·모델 문서·가격 문서, 2026-10-08 조회. 가격 단위는 USD / 100 만 토큰(MTok).

---

## 1. 무엇이 나왔나

[발표](https://www.anthropic.com/claude-haiku-5-5)는 Haiku 5.5 를 이렇게 소개한다. "요약, 컴팩션, 데이터베이스 쿼리, 분류 요청 같은 **빠르고 반복적인 작업**을 안정적으로 처리한다." [모델 문서](https://platform.claude.com/docs/en/models/haiku-5-5/overview)도 분류·추출·라우팅 같은 대량·저지연 작업을 용도로 든다.

| 항목 | Haiku 5.5 | Haiku 4.5 |
|---|---|---|
| API 모델 ID | `claude-haiku-5-5` | `claude-haiku-4-5-20251001` |
| 컨텍스트 창 | **1M** 토큰 | 200K 토큰 |
| 최대 출력 | 128K (Batch API + 베타 헤더 시 300K) | 64K |
| 지식 기준(reliable cutoff) | 2026 년 6 월 | 2025 년 2 월 |
| 사고 방식 | Adaptive thinking, 기본 effort `medium` | Extended thinking |
| 프롬프트 캐싱 최소 길이 | **512** 토큰 | 4,096 토큰 |

출처는 [모델 개요](https://platform.claude.com/docs/en/about-claude/models/overview)와 [프롬프트 캐싱 문서](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)다. 제공 플랫폼은 Claude API, Amazon Bedrock, Google Cloud, Microsoft Foundry 등이다.

캐싱 최소 길이가 4,096 → 512 토큰으로 내려간 것도 실무에서 크다. 짧은 시스템 프롬프트와 분류 지침도 이제 캐시 대상이 된다.

---

## 2. 가격: Haiku 5.5 만 '프롬프트 길이별 2 단 가격'이다

[가격 문서](https://platform.claude.com/docs/en/about-claude/pricing) 기준이다.

| (USD/MTok) | Haiku 5.5 · 프롬프트 ≤100K | Haiku 5.5 · 프롬프트 >100K | Haiku 4.5 |
|---|---|---|---|
| 입력 | **$0.10** | $0.50 | $1 |
| 캐시 쓰기 (5 분) | $0.125 | $0.625 | $1.25 |
| 캐시 쓰기 (1 시간) | $0.20 | $1 | $2 |
| 캐시 읽기 | **$0.01** | $0.05 | $0.10 |
| 출력 | **$0.50** | $2.50 | $5 |

Batch API 는 입력·출력 모두 50% 할인이다.

- **10 만 토큰 이하 구간은 모든 단가가 Haiku 4.5 의 정확히 10%**다. "90% 인하"는 이 구간 얘기다.
- **10 만 토큰을 넘는 구간은 50% 인하**에 그친다(발표 각주 2).
- 가격 문서는 이렇게 명시한다. "Claude 4.6 이후 모델은 1M 컨텍스트 전체를 표준 가격으로 제공하지만 **Haiku 5.5 는 예외**이며, 10 만 토큰을 넘는 프롬프트는 더 높은 가격을 낸다."

즉 **"100 만 컨텍스트"와 "90% 인하"는 동시에 성립하지 않는다.** 긴 문서를 통째로 넣는 순간 50% 인하 구간으로 넘어간다.

---

## 3. 숨은 변수: 같은 글이 토큰 30% 더 나온다

[Haiku 5.5 모델 문서](https://platform.claude.com/docs/en/models/haiku-5-5/overview)의 문장이다.

> "It uses the same newer tokenizer as Claude 4.7 and later models, so the same text counts as approximately 30% more tokens than on Claude Haiku 4.5."

토큰 단가가 내려가도 **같은 텍스트가 약 30% 더 많은 토큰으로 세어진다.** 그래서 발표 본문은 평균 절감을 90% 가 아니라 **"평균 약 75%"**라고 적는다. 각주 2 는 그 계산에 토큰 사용량 변화가 반영됐다고 밝힌다. 이전 Haiku 요청의 약 90% 가 10 만 토큰 이하였다는 점도 함께 적혀 있다.

여기에 실무적인 함정이 하나 더 있다. **10 만 토큰 경계도 새 토크나이저 기준으로 센다.** 예전 토크나이저로 약 7.7 만 토큰이던 프롬프트가 새 기준으로는 약 10 만 토큰이 된다(30% 가정 시 산술). 예전엔 넉넉히 저가 구간이던 요청이 경계를 넘을 수 있다.

### 산술 예시 (가정 명시)

공식 단가와 "토큰 약 30% 증가"를 입출력 모두에 적용한 **가상** 계산이다.

**① 짧은 요청을 대량으로 보내는 경우**
- 가정: 요청당 입력 1 만·출력 1 천 토큰(Haiku 4.5 토크나이저 기준), 월 100 만 건, 캐시 미사용.
- Haiku 4.5: 입력 100 억 × $1 + 출력 10 억 × $5 = **$15,000**
- Haiku 5.5: 입력 130 억 × $0.10 + 출력 13 억 × $0.50 = **$1,950** → 약 **87% 절감**

**② 긴 문서를 넣는 경우**
- 가정: 요청당 입력 15 만·출력 1 천 토큰(4.5 기준). 5.5 기준으로는 19.5 만 토큰이 돼 >100K 구간에 들어간다.
- Haiku 4.5: $0.155 / 요청
- Haiku 5.5: $0.101 / 요청 → 약 **35% 절감**

같은 모델 교체인데 워크로드 모양에 따라 절감률이 87% 와 35% 로 갈린다. 실제 토큰 증가율은 콘텐츠마다 다르다고 가격 문서가 명시하므로, **이 숫자는 공식 단가로 한 산술이지 실측이 아니다.** 내 워크로드로 확인하려면 같은 요청을 두 모델에 보내 `usage` 의 토큰 수를 비교하면 된다.

---

## 4. 성능은 어느 정도인가 (Anthropic 발표 수치)

아래는 [발표 페이지](https://www.anthropic.com/claude-haiku-5-5)에 실린 Anthropic 측 수치다. 중립 제 3 자 검증 수치가 아니라는 점을 감안해야 한다.

| 벤치마크 | Haiku 5.5 | Haiku 4.5 | Sonnet 5.5 |
|---|---|---|---|
| OSWorld 2.1 (offline subset) | 72.4% | 15.7% | 83.9% |
| Terminal-Bench 4.0 | 39.2% | 0.0% | 70.6% |
| Humanity's Last Exam (도구 사용) | 57.4% | 18.7% | 64.5% |

전작 대비 폭은 크다. 하지만 에이전트형 코딩(Terminal-Bench)에서는 여전히 Sonnet 5.5 와 차이가 뚜렷하다. 발표가 내세우는 자리, 즉 **대량·반복·저지연 작업용 기본 모델**이 정확한 위치 설정으로 보인다.

---

## 5. 언제 바꿀까

- **바로 바꿀 만한 곳**: 분류·라우팅·요약·추출처럼 프롬프트가 짧고 호출이 많은 작업. 캐시 최소 길이가 512 토큰으로 내려가 짧은 지침도 캐싱된다. 캐시 읽기 $0.01 이다.
- **계산해 보고 바꿀 곳**: 긴 문서·대용량 컨텍스트 작업. 10 만 토큰을 넘으면 절감 폭이 50%(토큰 증가 반영 시 더 작게)로 줄어든다. 그래도 더 싸지만, 컨텍스트를 10 만 아래로 잘라 넣을 수 있다면 단가가 5 배 차이 난다.
- **모델 ID 갱신**: `claude-haiku-4-5` → `claude-haiku-5-5`. 문서상 Haiku 4.5 는 "2026-10-15 이후 퇴역 가능"으로 표시돼 있다. 4.5 를 쓰는 코드가 있다면 미뤄 둘 일이 아니다.

---

## References

1. Anthropic, *Introducing Claude Haiku 5.5*, 2026-10-07. <https://www.anthropic.com/claude-haiku-5-5>
2. Anthropic Docs, *Claude Haiku 5.5 overview*. <https://platform.claude.com/docs/en/models/haiku-5-5/overview>
3. Anthropic Docs, *Models overview*. <https://platform.claude.com/docs/en/about-claude/models/overview>
4. Anthropic Docs, *Pricing*. <https://platform.claude.com/docs/en/about-claude/pricing>
5. Anthropic Docs, *Prompt caching*. <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
6. Anthropic Docs, *Claude Haiku 4.5 overview*. <https://platform.claude.com/docs/en/models/haiku-4-5/overview>
