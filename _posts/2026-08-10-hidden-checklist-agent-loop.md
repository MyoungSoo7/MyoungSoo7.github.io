---
layout: post
title: "에이전트에게 체크리스트를 숨겨야 하는가: Hidden Checklist와 자기개선 루프"
date: 2026-08-10 17:10:00 +0900
categories: [ai-agent, harness, evaluation]
tags: [hidden-checklist, self-improvement, skill, evaluator, postmortem, agent-loop]
---

이번 글은 첨부된 그림의 1~5번 구조를 중심으로, 에이전트의 작업 지시와 검증 기준을 분리하는 설계를 정리한 것이다.

![에이전트 작업 루프와 Hidden Checklist 개념](/assets/images/agent-hidden-checklist-loop.jpg)

## 핵심 요약

> 에이전트에게는 목표를 주고, 검증 에이전트에게는 acceptance checklist를 준다. 작업 에이전트가 체크리스트를 직접 보지 않게 하면, 결과를 기준에 맞추는 것보다 실제 목표를 수행하는지 검증할 수 있다는 주장이다.

다만 이 방식은 강력한 장점과 중요한 위험을 함께 가진다. 체크리스트를 숨기는 것이 항상 좋은 것은 아니며, 안전·권한·형식 계약처럼 작업자가 반드시 알아야 하는 규칙까지 숨겨서는 안 된다.

## 1. 기본 구조: 목표를 주고 루프를 돌린다

그림의 첫 번째 메시지는 단순하다.

```text
Agent에게 작업 공간 제공
→ 목표 설정
→ 실행
→ 평가
→ 실패 이유 전달
→ 개선·재실행
→ 목표에 수렴
```

이 구조의 핵심은 한 번의 긴 프롬프트가 아니라 반복 가능한 feedback loop다.

```text
one-shot:
  prompt → output

loop:
  goal → output → evaluation → feedback → revised output
```

에이전트가 매번 새로 추론하는 대신, 실패 원인을 다음 실행의 개선 입력으로 사용한다.

## 2. 예시: 포스트모템 보고서와 다섯 가지 기준

작업자는 다음처럼 간단한 목표만 받는다.

```text
포스트모템 보고서를 작성해줘.
```

검증자는 별도의 acceptance checklist를 가진다.

| 번호 | 검증 기준 |
| --- | --- |
| 1 | 슬라이드는 다섯 장을 넘을 것 |
| 2 | 첫 장에 결론과 핵심 수치가 보일 것 |
| 3 | 핵심 지표 표를 추출하고 원문 그대로 사용할 것 |
| 4 | 다음 할 일과 담당자가 포함될 것 |
| 5 | 슬라이드가 간결하고 불릿은 3개로 제한될 것 |

검증 실패 시에는 단순히 “다시 해”가 아니라 구체적인 실패 이유를 전달한다.

```text
실패:
  첫 장에 핵심 수치가 없음

개선:
  첫 장에 결론·핵심 수치·범위를 배치

재실행:
  수정된 작업 지시와 함께 다시 생성
```

## 3. 왜 체크리스트를 숨기는가

그림의 핵심 주장은 체크리스트를 작업 에이전트에게 그대로 주면 체크리스트가 곧 프롬프트가 된다는 것이다.

이때 발생할 수 있는 문제가 있다.

```text
Agent가 실제 목표보다 checklist 통과에 최적화
표면적인 형식만 맞춤
평가 기준에 포함되지 않은 품질을 무시
특정 모델의 프롬프트 해석 방식에 결합
```

즉 평가 기준을 그대로 노출하면 agent가 목표를 수행하는 대신 evaluator를 공략하는 방향으로 움직일 수 있다. 이는 reward hacking 또는 specification gaming과 유사한 위험이다.

## 4. 모델이 바뀌어도 검증 기준을 유지한다는 발상

프롬프트는 모델의 능력·문맥·도구 사용 방식에 영향을 받는다. 모델이 바뀌면 같은 프롬프트가 같은 결과를 보장하지 않는다.

반면 외부 검증 기준은 모델에 독립적인 계약으로 유지할 수 있다.

```text
검증 기준:
  결론이 첫 장에 있는가?
  핵심 수치가 원문과 일치하는가?
  담당자와 next action이 있는가?

모델 A:
  기준에 맞는 skill A 생성

모델 B:
  같은 기준으로 skill B 재생성
```

이 구조의 장점은 모델이 바뀔 때 사람이 프롬프트를 처음부터 다시 쓰는 대신, 새 모델이 동일한 acceptance contract를 통과하도록 조정할 수 있다는 점이다.

그러나 모델 독립적인 것은 체크리스트이지, 자동으로 생성되는 skill의 품질은 아니다. 새 모델이 기준을 통과해도 사실을 틀리게 쓰거나, 원문을 잘못 인용하거나, 권한을 과도하게 사용할 수 있다. 따라서 내용 정확성·보안·권한 검증은 별도의 gate로 둬야 한다.

## 5. Agent와 Evaluator의 역할 분리

권장 구조는 다음과 같다.

```text
Worker Agent:
  목표를 해석하고 결과를 생성

Evaluator:
  acceptance criteria·출처·형식·안전 기준 검증

Harness:
  실행 trace·artifact·판정 결과 저장

Human:
  기준·권한·위험한 변경의 최종 책임
```

여기서 Evaluator도 완전히 믿어서는 안 된다. Evaluator가 같은 모델·같은 편향·같은 입력을 공유하면 독립적인 검증이 아닐 수 있다.

```text
독립 evaluator
결정적 schema 검사
원문 대조
테스트 실행
권한·side effect 검사
```

를 함께 사용해야 한다.

## 6. 숨겨도 되는 기준과 숨기면 안 되는 기준

모든 체크리스트를 숨기는 것은 위험하다.

### 숨겨도 되는 기준

```text
내부 품질 점수
비공개 평가 순서
추가적인 품질 비교 항목
후보 결과 간 선호 기준
```

### 반드시 알려야 하는 기준

```text
금지된 행동
필수 보안 규칙
개인정보 처리 규칙
권한 범위
출력 schema
법적·규제 의무
사용자 승인 필요 조건
```

예를 들어 운영 Kubernetes 작업에서 “사용자 승인 없이 apply/delete/cordon 금지”를 숨겨서는 안 된다. 이것은 evaluator가 나중에 실패시키는 내부 평가 기준이 아니라, 작업 시작 전에 명시해야 하는 Policy다.

## 7. 이미지의 포스트모템 예시를 운영에 적용하기

포스트모템 산출물은 다음 세 층으로 나누는 것이 좋다.

```text
작업 목표:
  포스트모템 보고서 작성

공개 계약:
  사실·추론·미확정 분리
  원문 수치 보존
  담당자·next action 명시
  credential 제거

Evaluator 내부 기준:
  첫 장 결론 배치
  핵심 수치 대조
  불릿 수 제한
  누락 section 검사
```

현재 Hermes RCA에도 같은 구조를 적용할 수 있다.

```text
Agent 목표:
  최근 24시간 RCA 작성

공개 규칙:
  read-only
  최신 Trace 우선
  운영 변경 금지

Evaluator:
  collected_at 존재
  lookback 일치
  현재 Pod·endpoint·업무 성공 확인
  restartCount 단독 승격 금지
  stale reference는 정리 후보로 분리
```

## 8. 자기개선 루프의 안전한 형태

“사람은 skill과 workflow를 손대지 않는다”는 표현은 자동화의 장점을 강조하지만, 운영 시스템에 그대로 적용하면 위험하다. 자기개선은 다음처럼 제한하는 편이 안전하다.

```text
1. 실패 Trace 수집
2. 실패 유형 분류
3. 개선 patch 제안
4. sandbox에서 테스트
5. evaluator·regression 통과
6. diff와 권한 검토
7. 승인된 artifact만 promotion
```

특히 다음은 자동 promotion하지 않는다.

```text
권한 변경
외부 전송·게시
Kubernetes write
DB schema 변경
금융 거래·지급
Credential·secret 접근
```

## 9. 결론

첨부 이미지가 설명하는 Hidden Checklist의 가치는 **작업 목표와 평가 기준을 분리해 모델 교체에 강한 Harness를 만드는 것**이다.

```text
Worker:
  목표를 수행

Evaluator:
  기준으로 검증

Harness:
  trace와 receipt를 저장

Human:
  정책·권한·위험을 책임
```

체크리스트를 숨기는 것만으로 품질이 보장되지는 않는다. 가장 안전한 설계는 다음 세 가지를 분리하는 것이다.

```text
Policy:
  반드시 사전에 알려야 하는 금지·권한·안전 규칙

Acceptance Criteria:
  결과를 평가하는 품질 기준

Implementation Hint:
  작업을 돕는 구체적 방법
```

> **모델이 바뀌어도 살아남아야 하는 것은 특정 프롬프트가 아니라, 독립적으로 검증 가능한 계약과 Trace다.**

## References

- [첨부 이미지와 연결된 원문 맥락](https://blog.gaebal-gajae.dev/posts/2026-08-10-daily-reflection-design-the-cleanup-before-scaling.html)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/docs)
- [Ouroboros](https://github.com/Q00/ouroboros)
- [Model Context Protocol](https://modelcontextprotocol.io/)

*이미지의 내용을 요약·재구성한 글이며, 원문 전체를 복제하지 않았다.*

*공개 글에는 credential, token, private IP, 내부 endpoint를 포함하지 않았다.*

*첨부 이미지는 사용자의 제공 이미지이며, 블로그 assets에 저장해 본문에 삽입했다.*
