---
layout: post
title: "[CS300 #079] 문자열 탐색 — KMP, 이미 읽은 글자를 다시 읽지 않기"
date: 2026-10-10 19:19:00 +0900
categories: [cs]
tags: [cs300, algorithms, string-matching, kmp, failure-function]
---

컴퓨터공학 300 주제 시리즈의 079번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

KMP(Knuth–Morris–Pratt) 알고리즘은 패턴을 미리 분석해 "불일치가 나면 패턴을 얼마나 밀어도 되는가" 를 실패 함수로 저장한다. 덕분에 텍스트의 포인터가 절대 뒤로 가지 않고, 길이 n 텍스트에서 길이 m 패턴을 Θ(n + m) 에 찾는다.

## 왜 필요한가

텍스트에서 패턴을 찾는 가장 단순한 방법은 모든 시작 위치에서 패턴을 한 글자씩 맞춰 보는 것이다. 보통의 영어 문장에서는 첫 한두 글자에서 대부분 어긋나니 충분히 빠르다. 그런데 입력이 반복적이면 이야기가 다르다.

텍스트가 "AAAA…AB"(10만 글자), 패턴이 "AAA…AB"(천 글자)라고 하자. 단순 방법은 각 위치에서 A 를 999번 맞춘 뒤 마지막에 어긋난다. 비교가 약 1억 번이다. 로그, DNA 서열, 바이너리 데이터처럼 반복이 많은 입력에서는 실제로 이런 일이 생긴다. 그리고 공격자가 입력을 고를 수 있다면 일부러 이런 입력을 만들 수 있다.

KMP 는 1977년 Knuth, Morris, Pratt 가 함께 발표했다. 최악에도 선형 시간을 보장한다.

## 핵심 개념

### 단순 탐색이 낭비하는 것

```
텍스트:  A B A B A B C ...
패턴:    A B A B C
         ✓ ✓ ✓ ✓ ✗       ← 5번째에서 어긋남
단순:      A B A B C     ← 한 칸 밀고 처음부터 다시
```

어긋나기 전에 "ABAB" 를 이미 맞췄다. 즉 텍스트의 그 구간이 "ABAB" 라는 걸 안다. 그런데 단순 방법은 이 정보를 버리고 텍스트를 다시 읽는다.

"ABAB" 의 뒷부분 "AB" 는 패턴의 앞부분 "AB" 와 같다. 그러므로 패턴을 두 칸 밀면 앞의 "AB" 는 이미 맞은 상태로 이어서 비교할 수 있다.

```
텍스트:  A B A B A B C
패턴:        A B A B C   ← 두 칸 밀고, 앞 2글자는 맞은 것으로 치고 3번째부터 비교
```

### 실패 함수(접두사 함수)

패턴 p 의 각 위치 i 에 대해

```
fail[i] = p[0..i] 의 진접두사이면서 동시에 접미사인 문자열 중 가장 긴 것의 길이
```

"진" 접두사는 자기 자신 전체를 빼는 것이다. 예를 들어 p = "ABABCABAB":

| i | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| p[i] | A | B | A | B | C | A | B | A | B |
| fail[i] | 0 | 0 | 1 | 2 | 0 | 1 | 2 | 3 | 4 |

fail[3] = 2 는 "ABAB" 의 접두사 "AB" 와 접미사 "AB" 가 같다는 뜻이다. fail[8] = 4 는 "ABABCABAB" 의 앞 4글자와 뒤 4글자가 "ABAB" 로 같다는 뜻이다.

### 탐색 과정

패턴의 앞 k 글자가 맞은 상태에서 텍스트 다음 글자 c 를 본다.

- c == p[k] 이면 k 를 1 늘린다. k == m 이면 매치를 찾은 것이다.
- 다르면 k = fail[k−1] 로 줄이고 다시 비교한다. k 가 0 이 되면 그냥 다음 글자로 간다.

텍스트 인덱스는 매 단계 한 칸씩만 앞으로 간다. 절대 뒤로 가지 않는다. 그래서 스트림으로 들어오는 데이터에도 쓸 수 있다.

### 왜 Θ(n + m) 인가

탐색 중 k 는 텍스트 글자 하나당 최대 1 증가한다. 그러므로 전체 증가량은 n 이하다. `k = fail[k-1]` 은 k 를 적어도 1 줄인다. 줄어든 총량은 늘어난 총량을 넘을 수 없으므로 후퇴 횟수도 n 이하다. 비교는 최대 약 2n 번이다. 분할 상환 분석의 전형이다. 실패 함수 계산도 같은 논리로 Θ(m).

### 실패 함수를 만드는 법

실패 함수 계산은 "패턴 자신에서 패턴을 찾는" KMP 와 같은 코드다. 위치 i 까지의 경계 길이 k 를 알고 있을 때, p[i] == p[k] 면 k+1 로 늘리고, 아니면 더 짧은 경계 fail[k−1] 로 후퇴해 다시 비교한다.

### 다른 문자열 탐색 알고리즘

| 알고리즘 | 아이디어 | 최악 | 특징 |
|---|---|---|---|
| 단순 | 모든 위치에서 비교 | Θ(nm) | 보통 텍스트에선 빠름 |
| KMP | 실패 함수로 밀기 | Θ(n + m) | 텍스트 포인터가 뒤로 안 감 |
| Boyer–Moore | 패턴 뒤에서부터 비교, 불일치 글자로 크게 건너뜀 | 변형에 따라 선형 | 실제 텍스트에서 글자를 건너뛰어 매우 빠름 |
| Rabin–Karp | 롤링 해시 비교 | 기대 Θ(n + m) | 여러 패턴 동시 탐색에 유리 |
| Aho–Corasick | 여러 패턴의 트라이 + 실패 링크 | Θ(n + m + 매치 수) | KMP 를 다중 패턴으로 일반화 |

## 직접 해 보기

실패 함수와 KMP 를 구현하고, 반복적인 입력에서 단순 탐색과 비교 횟수를 센다. python3 로 실행해 확인했다.

```python
def failure(p):
    """fail[i] = p[:i+1] 의 가장 긴 진접두사이면서 접미사인 길이."""
    fail = [0] * len(p)
    k = 0
    for i in range(1, len(p)):
        while k and p[i] != p[k]:
            k = fail[k - 1]               # 더 짧은 경계로 후퇴
        if p[i] == p[k]:
            k += 1
        fail[i] = k
    return fail

def kmp_search(t, p):
    fail, k, hits, cmp = failure(p), 0, [], 0
    for i, ch in enumerate(t):
        while k and ch != p[k]:
            cmp += 1
            k = fail[k - 1]
        cmp += 1
        if ch == p[k]:
            k += 1
            if k == len(p):
                hits.append(i - len(p) + 1)
                k = fail[k - 1]           # 겹치는 다음 매치도 찾는다
    return hits, cmp

def naive_search(t, p):
    hits, cmp = [], 0
    for s in range(len(t) - len(p) + 1):
        j = 0
        while j < len(p):
            cmp += 1
            if t[s + j] != p[j]:
                break
            j += 1
        if j == len(p):
            hits.append(s)
    return hits, cmp

print("fail(ABABCABAB) =", failure("ABABCABAB"))
print(kmp_search("ABABDABABCABABCABAB", "ABABCABAB"))

t = "A" * 100000 + "B"
p = "A" * 1000 + "B"
h1, c1 = naive_search(t, p)
h2, c2 = kmp_search(t, p)
print("일치 위치 같음:", h1 == h2, h2)
print(f"단순 비교 {c1:,}회 vs KMP 비교 {c2:,}회")
```

출력:

```
fail(ABABCABAB) = [0, 0, 1, 2, 0, 1, 2, 3, 4]
([5, 10], 21)
일치 위치 같음: True [99000]
단순 비교 99,100,001회 vs KMP 비교 199,001회
```

두 번째 줄은 위치 5 와 10 에서 겹치는 두 매치를 모두 찾았다. 매치 뒤에 k 를 0 이 아니라 fail[k−1] 로 돌려놓았기 때문이다. 반복적인 입력에서 단순 탐색은 약 1억 번, KMP 는 약 20만 번(텍스트 길이의 2배 이내) 비교했다. 순수 Python 으로 1억 번 비교는 체감할 만큼 느리다. 직접 돌려 보면 차이를 시간으로도 느낄 수 있다.

## 현업에서는

- **표준 라이브러리 `find` 는 이미 똑똑하다.** CPython 의 문자열 탐색 구현(`Objects/stringlib/fastsearch.h`) 주석을 보면 Boyer–Moore 와 Horspool 을 섞은 방식을 기본으로 쓰고, 문자열이 충분히 길면 Crochemore–Perrin 의 Two-Way 알고리즘을 쓴다고 적혀 있다. Two-Way 는 KMP 처럼 최악 선형을 보장하면서 상수 공간만 쓴다. 직접 KMP 를 짤 일은 드물지만, 왜 표준 함수가 반복 입력에도 버티는지 이해할 수 있다.
- **정규식과 최악 시간.** 백트래킹 방식 정규식 엔진은 특정 패턴과 입력에서 지수 시간이 걸릴 수 있다(ReDoS). 사용자 입력에 정규식을 적용하는 서비스라면 패턴을 단순하게 유지하고, 가능하면 선형 시간을 보장하는 엔진을 고려한다. KMP 가 보여 준 "텍스트를 뒤로 읽지 않는" 성질이 선형 보장의 핵심이다.
- **로그·패킷 검사.** 침입 탐지처럼 수천 개 시그니처를 한꺼번에 찾을 때는 KMP 를 다중 패턴으로 확장한 Aho–Corasick 계열을 쓴다.
- **스트림 처리.** 텍스트 포인터가 뒤로 가지 않으므로 네트워크로 들어오는 바이트를 버퍼에 다 쌓지 않고도 구분자나 경계 문자열을 찾을 수 있다. HTTP multipart 경계 탐지가 그런 예다.

## 확인 문제

1. p = "AABAAA" 의 실패 함수를 구하라.
2. KMP 의 탐색 단계에서 비교 횟수가 2n 을 넘지 않는 이유를 한 문장으로 말하라.
3. 매치를 찾은 뒤 k 를 0 으로 초기화하면 무엇을 놓치는가?
4. 패턴 길이가 1 이면 KMP 와 단순 탐색의 차이는?

### 풀이

1. [0, 1, 0, 1, 2, 2]. i=5 에서 "AABAAA" 의 경계: "AA" 가 접두사이자 접미사다("AAB…" 와 "…AAA" 의 뒤 두 글자). 길이 3 "AAB" vs "AAA" 는 다르다.
2. k 는 글자당 최대 1 증가하므로 총 증가 ≤ n 이고, 후퇴는 매번 k 를 줄이므로 총 후퇴 ≤ 총 증가 ≤ n 이기 때문이다.
3. 겹치는 매치를 놓친다. 예를 들어 "AAAA" 에서 "AA" 를 찾으면 위치 0, 1, 2 가 모두 매치인데, 0 으로 초기화하면 0 과 2 만 찾는다.
4. 차이가 없다. 실패 함수가 [0] 이고 둘 다 텍스트를 한 번 훑는다.

## 더 읽을거리 (References)

- Donald E. Knuth, James H. Morris, Vaughan R. Pratt, "Fast Pattern Matching in Strings", *SIAM Journal on Computing* 6(2), 1977.
- NIST Dictionary of Algorithms and Data Structures, [Knuth-Morris-Pratt algorithm](https://xlinux.nist.gov/dads/HTML/knuthMorrisPratt.html)
- CPython 소스, [Objects/stringlib/fastsearch.h](https://raw.githubusercontent.com/python/cpython/main/Objects/stringlib/fastsearch.h) — 표준 문자열 탐색 구현과 Two-Way 알고리즘 주석
- Robert S. Boyer, J. Strother Moore, "A Fast String Searching Algorithm", *Communications of the ACM* 20(10), 1977.
