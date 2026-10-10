---
layout: post
title: "[CS300 #296] 기술 문서 작성 — 독자와 목적이 문서의 형태를 정한다"
date: 2026-10-10 22:56:00 +0900
categories: [cs]
tags: [cs300, hci, technical-writing, documentation, diataxis]
---

컴퓨터공학 300 주제 시리즈의 296번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

좋은 기술 문서는 "누가, 무엇을 하려고 읽는가"에서 출발한다. 배우려는 사람, 일을 끝내려는 사람, 정확한 사양을 찾는 사람, 이유를 이해하려는 사람에게는 서로 다른 문서가 필요하다.

## 왜 필요한가

코드는 컴퓨터에게 무엇을 할지 알려 주고, 문서는 사람에게 왜·어떻게를 알려 준다. 문서가 없거나 틀리면 비용은 다른 곳에서 나온다.

- 신입이 환경 설정에 사흘을 쓴다.
- 같은 질문이 메신저에 매주 올라온다.
- 새벽 장애 때 아무도 롤백 절차를 모른다.
- 6개월 전 설계 결정의 이유를 아무도 기억하지 못해 같은 논쟁을 반복한다.

문서는 팀의 기억이고, 시간을 넘어 하는 커뮤니케이션이다. 그리고 미래의 나도 독자다.

## 핵심 개념

### 독자부터 정한다

글을 쓰기 전에 세 가지를 적어 본다.

```
독자:  누구인가? 무엇을 이미 아는가? (예: k8s 기초를 아는 백엔드 개발자)
목적:  읽고 나서 무엇을 할 수 있어야 하는가? (예: 스테이징에 혼자 배포한다)
범위:  다루지 않는 것은 무엇인가? (예: 클러스터 구축은 다루지 않는다)
```

Google 의 기술 글쓰기 교육 과정도 독자 정의와 문서 범위 명시를 첫 단계로 둔다. 독자를 정하지 않으면 전문가에게는 지루하고 초보에게는 불친절한 문서가 된다.

### Diátaxis: 문서의 네 종류

Diátaxis 프레임워크는 문서를 사용자의 필요에 따라 네 종류로 나눈다.

| 종류 | 독자의 상태 | 목적 | 형태 |
|---|---|---|---|
| 튜토리얼(tutorial) | 처음 배운다 | 학습 | 따라 하면 반드시 성공하는 수업 |
| 방법 안내(how-to guide) | 일을 끝내려 한다 | 과업 | 특정 목표를 위한 단계 |
| 참조(reference) | 정확한 사실을 찾는다 | 정보 | API·설정값·명령어의 건조한 기술 |
| 설명(explanation) | 이해하려 한다 | 이해 | 배경, 설계 이유, 대안 비교 |

가장 흔한 실패는 섞는 것이다. 튜토리얼 중간에 설계 철학 세 문단이 들어가면 따라 하던 사람이 길을 잃는다. 참조 문서에 "먼저 이것을 이해해야 합니다"가 들어가면 찾으려던 값을 못 찾는다. 섞인 내용은 다른 문서로 옮기고 링크한다.

### 문장 수준의 원칙

- 한 문장에 한 생각. 긴 문장은 나눈다.
- 능동태와 명확한 주어. "설정이 변경되어야 한다"보다 "관리자가 설정을 바꾼다".
- 용어를 하나로 고정한다. 한 문서에서 "노드", "서버", "호스트"를 섞으면 독자는 셋이 다른 것인지 고민한다.
- 단계는 번호 목록으로, 한 단계에 한 동작.
- 명령과 예상 출력을 함께 보여 준다. 독자는 자기 결과와 비교해 제대로 됐는지 안다.
- 링크 텍스트는 목적지를 말한다. "여기를 클릭" 대신 "롤백 절차".

### 요구사항의 강도: RFC 2119

명세 문서에서는 "해야 한다"와 "하는 게 좋다"가 다르다. IETF 의 RFC 2119 는 MUST, SHOULD, MAY 같은 키워드의 의미를 정의하고, RFC 8174 는 이 키워드가 대문자로 쓰였을 때만 그 특별한 의미를 갖는다고 명확히 했다.

| 키워드 | 의미 |
|---|---|
| MUST / REQUIRED / SHALL | 절대적 요구 |
| SHOULD / RECOMMENDED | 타당한 이유가 있으면 예외 가능하나, 함의를 이해하고 판단 |
| MAY / OPTIONAL | 선택 |

한국어 문서에서도 "반드시", "권장", "선택" 같은 단어를 정해 두고 일관되게 쓰면 같은 효과가 있다.

### 개발자가 자주 쓰는 문서

| 문서 | 들어갈 것 |
|---|---|
| README | 이게 무엇인지, 빠른 시작, 요구 사항, 라이선스, 더 볼 곳 |
| 런북(runbook) | 증상, 확인 명령, 조치 단계, 롤백, 연락처 |
| ADR(Architecture Decision Record) | 맥락, 결정, 결과. 짧게, 결정 하나에 한 문서 |
| API 참조 | 엔드포인트, 매개변수, 오류 코드, 예시 요청·응답 |
| 변경 기록(CHANGELOG) | 버전별 추가·변경·제거·수정 |
| 독스트링 | 함수가 하는 일, 인자, 반환값, 예외 |

ADR 은 Michael Nygard 가 2011년 글에서 제안한 형식으로 널리 쓰인다. 코드 옆에 마크다운 파일로 두고 리뷰를 거친다.

### 문서도 코드처럼

문서를 코드 저장소에 두고, 같은 PR 에서 코드와 함께 고치고, 리뷰하고, CI 에서 검사한다. 이를 docs-as-code 라고 부른다. 링크 깨짐, 맞춤법, 코드 예제 실행 여부를 자동으로 검사할 수 있다. 문서가 코드와 떨어진 위키에 있으면 금방 낡는다.

## 직접 해 보기

마크다운 문서의 흔한 문제를 잡는 아주 작은 검사기를 만든다. 실무에서는 Vale, markdownlint 같은 도구가 이 일을 한다.

~~~python
import re

doc = """# 배포 가이드
이 문서는 서비스를 배포하는 방법을 설명하는데 먼저 이미지를 빌드하고 레지스트리에 올린 다음 매니페스트의 태그를 바꾸고 클러스터에 적용한 후 상태를 확인해야 하며 실패하면 롤백해야 합니다.
```
kubectl apply -f deploy.yaml
```
설정 파일은 반드시 검토 해야 한다. TODO: 롤백 절차 추가
자세한 내용은 [여기](./rollback.md)를 보세요.
"""

rules = []
def rule(f):
    rules.append(f)
    return f

@rule
def long_sentence(lines):
    for i, line in enumerate(lines, 1):
        for s in re.split(r"(?<=[.!?다])\s", line):
            if len(s) > 80:
                yield i, f"문장이 너무 길다({len(s)}자). 나눌 것"

@rule
def code_without_lang(lines):
    inside = False
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            if not inside and line.strip() == "```":
                yield i, "코드 블록에 언어 표시가 없다"
            inside = not inside

@rule
def todo_left(lines):
    for i, line in enumerate(lines, 1):
        if "TODO" in line:
            yield i, "TODO 가 남아 있다"

@rule
def vague_link(lines):
    for i, line in enumerate(lines, 1):
        for text in re.findall(r"\[([^\]]+)\]\(", line):
            if text.strip() in ("여기", "이곳", "click here", "here"):
                yield i, f"링크 텍스트 '{text}' 는 목적지를 말하지 않는다"

lines = doc.splitlines()
for r in rules:
    for lineno, msg in r(lines):
        print(f"{lineno}행: {msg}")
~~~

실행 결과다.

```
2행: 문장이 너무 길다(105자). 나눌 것
3행: 코드 블록에 언어 표시가 없다
6행: TODO 가 남아 있다
7행: 링크 텍스트 '여기' 는 목적지를 말하지 않는다
```

2행을 고쳐 쓰면 이렇게 된다.

```
서비스는 다음 순서로 배포한다.

1. 이미지를 빌드해 레지스트리에 올린다.
2. 매니페스트의 이미지 태그를 바꾼다.
3. 클러스터에 적용한다: `kubectl apply -f deploy.yaml`
4. 롤아웃 상태를 확인한다: `kubectl rollout status deploy/web`
5. 실패하면 롤백 절차(rollback.md)를 따른다.
```

규칙 검사는 기계적인 문제만 잡는다. 독자에게 필요한 내용이 빠졌는지, 순서가 맞는지는 실제 독자에게 문서만 주고 따라 하게 해 봐야 안다. 사용성 테스트를 문서에도 하는 셈이다.

## 현업에서는

- 장애 대응 런북은 새벽 3시의 졸린 사람이 독자다. 설명보다 복사해 붙일 수 있는 명령과 "이 출력이 나오면 정상"이 중요하다. 홈랩 k3s 를 운영하며 노드 재부팅 절차를 런북으로 적어 두면, 몇 달 뒤의 자신이 고마워한다.
- PR 템플릿에 "문서 갱신 여부" 체크 항목을 넣는다. 기능은 바뀌었는데 문서는 그대로인 상태가 가장 해롭다. 틀린 문서는 없는 문서보다 나쁘다.
- 문서 예제 코드는 테스트한다. Python 의 `doctest` 처럼 문서 속 예제를 실행하는 도구를 쓰거나, 예제를 별도 파일로 두고 CI 에서 돌린 뒤 문서에 포함한다.
- 문서에 비밀번호, 토큰, 내부 IP 같은 민감 정보를 예시로 넣지 않는다. `example.com`, 문서용 IP 대역(RFC 5737) 같은 예약된 값을 쓴다.

## 확인 문제

1. Diátaxis 의 네 문서 종류를 독자의 필요와 함께 적어라.
2. 튜토리얼에 설계 배경 설명을 길게 넣으면 생기는 문제는?
3. RFC 8174 가 RFC 2119 에 덧붙인 내용은?
4. ADR 에 들어가는 세 요소는?
5. 문서를 코드 저장소에 두면 좋은 이유 두 가지는?

### 풀이

1. 튜토리얼(학습), 방법 안내(과업 완수), 참조(정확한 정보), 설명(이해).
2. 따라 하던 학습자의 흐름이 끊기고 무엇을 해야 하는지 놓친다. 설명은 별도 문서로 분리하고 링크한다.
3. 키워드가 대문자로 쓰였을 때만 RFC 2119 의 특별한 의미를 갖는다는 점.
4. 맥락(context), 결정(decision), 결과(consequences).
5. 코드 변경과 같은 PR 에서 함께 고치고 리뷰할 수 있고, CI 로 링크·예제·형식을 자동 검사할 수 있다.

## 더 읽을거리 (References)

- Google for Developers, [Technical Writing courses](https://developers.google.com/tech-writing)
- [Diátaxis](https://diataxis.fr/) — 문서 체계 프레임워크
- IETF, [RFC 2119: Key words for use in RFCs to Indicate Requirement Levels](https://www.rfc-editor.org/rfc/rfc2119), [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)
- M. Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), 2011.
