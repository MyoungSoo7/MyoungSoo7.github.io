---
layout: post
title: "[CS300 #020] 정보이론 — 엔트로피와 부호화"
date: 2026-10-10 18:20:00 +0900
categories: [cs]
tags: [cs300, math, information-theory, entropy, huffman]
---

컴퓨터공학 300 주제 시리즈의 020번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

엔트로피는 확률분포의 "평균 놀라움" 이자, 그 분포에서 나온 기호를 무손실로 부호화할 때 기호당 필요한 평균 비트 수의 하한이다. 허프만 부호는 이 하한에 1 비트 이내로 다가가는 최적의 접두 부호이며, 교차 엔트로피와 KL 발산은 머신러닝의 손실 함수로 그대로 쓰인다.

## 왜 필요한가

zip, gzip, PNG 가 파일을 얼마나 줄일 수 있는지에는 수학적 한계가 있다. 이미 압축된 파일이나 암호화된 데이터를 다시 압축해도 거의 줄지 않는 이유, 무작위 비밀번호의 강도를 "비트" 로 말하는 이유, 분류 모델이 교차 엔트로피 손실로 학습하는 이유가 모두 같은 개념에서 나온다.

정보이론은 1948 년 섀넌의 논문 "A Mathematical Theory of Communication" 에서 시작됐다([Shannon, 1948](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf)). 이 글은 그 핵심인 정보량, 엔트로피, 원천 부호화 정리, 허프만 부호를 다루고, 파트 1 의 확률(013–015번 글)이 어디로 이어지는지 보여 준다.

## 핵심 개념

### 정보량: 드문 사건일수록 정보가 많다

확률 p 인 사건이 일어났을 때 얻는 **정보량(자기 정보)** 은

```
I(p) = −log₂ p   (단위: 비트)
```

다. 확률 1/2 인 사건(동전 앞면)은 1 비트, 1/8 이면 3 비트, 확률 1 인 사건은 0 비트다. 이 정의는 "독립 사건 두 개의 정보량은 더해진다" 는 성질을 만족하도록 고른 것이다. 확률은 곱해지고 로그는 곱을 합으로 바꾸기 때문이다.

### 엔트로피

확률변수 X 가 값 xᵢ 를 확률 pᵢ 로 가질 때 **엔트로피**는 정보량의 기댓값이다(014번 글).

```
H(X) = −Σ pᵢ log₂ pᵢ
```

| 분포 | 엔트로피 |
|---|---|
| 공정한 동전 (1/2, 1/2) | 1 비트 |
| 치우친 동전 (0.9, 0.1) | 약 0.469 비트 |
| 확실한 결과 (1, 0) | 0 비트 |
| 공정한 주사위 6 면 | log₂6 ≈ 2.585 비트 |
| n 개 값이 모두 같은 확률 | log₂n 비트 (최대) |

엔트로피는 결과가 고르게 퍼질수록 크고, 한쪽으로 쏠릴수록 작다. n 개 값을 갖는 분포의 엔트로피는 균등분포일 때 최대 log₂n 이다.

### 원천 부호화 정리

**섀넌의 원천 부호화 정리(요지).** 엔트로피가 H 인 원천에서 나온 기호를 무손실로 부호화할 때, 기호당 평균 비트 수는 H 보다 작을 수 없다. 그리고 기호를 충분히 길게 묶어 부호화하면 H 에 얼마든지 가까워질 수 있다.

엔트로피는 "이 데이터를 줄일 수 있는 바닥" 이다. 영문 텍스트를 글자당 8 비트 ASCII 로 저장하면 낭비가 많지만, 균등한 무작위 바이트는 이미 바이트당 8 비트의 엔트로피를 가지므로 더 줄일 수 없다. 007번 글에서 비둘기집 원리로 "모든 입력을 줄이는 압축은 없다" 를 보였는데, 원천 부호화 정리는 "평균적으로 얼마까지 줄일 수 있는가" 를 정확히 말해 준다.

### 접두 부호와 허프만 부호

가변 길이 부호를 쓰려면 경계 없이 이어 붙인 비트열을 하나로 해독할 수 있어야 한다. 어떤 부호어도 다른 부호어의 앞부분이 아니면 **접두 부호(prefix code)** 이며, 앞에서부터 읽으면서 바로 해독할 수 있다. 접두 부호는 이진 트리의 잎으로 표현된다(010번 글). 왼쪽 가지를 0, 오른쪽 가지를 1 로 읽는다.

**허프만 알고리즘**은 기호 빈도가 주어졌을 때 평균 길이가 최소인 접두 부호를 만든다.

```
1. 각 기호를 빈도를 가진 잎 노드로 만든다.
2. 빈도가 가장 작은 두 노드를 꺼내 하나의 부모로 합친다(빈도는 합).
3. 노드가 하나 남을 때까지 반복한다.
```

빈도가 높은 기호는 뿌리 가까이(짧은 부호), 낮은 기호는 깊이(긴 부호) 놓인다. 허프만 부호의 평균 길이 L 은 H ≤ L < H + 1 을 만족한다. 기호 하나마다 정수 비트를 써야 하므로 1 비트 이내의 손실이 생기며, 이를 줄이려면 기호를 묶거나 산술 부호화를 쓴다.

DEFLATE(zip, gzip, PNG 가 쓰는 형식)는 LZ77 로 반복 문자열을 찾아 바꾼 뒤 그 결과를 허프만 부호로 부호화한다([RFC 1951, DEFLATE Compressed Data Format Specification](https://www.rfc-editor.org/rfc/rfc1951)).

### 교차 엔트로피와 KL 발산

실제 분포가 p 인데 분포 q 를 가정하고 부호를 설계하면 기호당 평균 비트 수는 **교차 엔트로피**가 된다.

```
H(p, q) = −Σ pᵢ log₂ qᵢ
D_KL(p ‖ q) = H(p, q) − H(p) = Σ pᵢ log₂ (pᵢ / qᵢ)  ≥ 0
```

KL 발산은 "틀린 분포를 가정해서 낭비한 비트" 이고 항상 0 이상이며, p = q 일 때만 0 이다. 분류 모델의 학습은 정답 분포 p 와 모델 예측 q 사이의 교차 엔트로피를 최소화하는 것이다. H(p) 는 모델과 무관한 상수이므로, 이는 KL 발산을 최소화하는 것과 같다. 머신러닝에서는 보통 자연로그(단위 nat)를 쓰지만 밑만 다를 뿐 같은 양이다.

## 직접 해 보기

문자열의 엔트로피를 계산하고, 허프만 부호를 `heapq` 로 만들어 평균 길이를 엔트로피와 비교한다. 마지막으로 `zlib`(DEFLATE)으로 텍스트와 무작위 바이트를 압축해 본다.

```python
import heapq, math, os, zlib
from collections import Counter

def entropy(text):
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in Counter(text).values())

def huffman(text):
    freq = Counter(text)
    heap = [(f, i, {ch: ""}) for i, (ch, f) in enumerate(freq.items())]
    heapq.heapify(heap)
    tie = len(heap)
    while len(heap) > 1:
        f1, _, c1 = heapq.heappop(heap)
        f2, _, c2 = heapq.heappop(heap)
        merged = {ch: "0" + code for ch, code in c1.items()}
        merged.update({ch: "1" + code for ch, code in c2.items()})
        heapq.heappush(heap, (f1 + f2, tie, merged))
        tie += 1
    return heap[0][2]

text = "abracadabra alakazam " * 20
codes = huffman(text)
avg = sum(len(codes[ch]) for ch in text) / len(text)
print("엔트로피:", round(entropy(text), 4), "허프만 평균:", round(avg, 4))
print(sorted(codes.items(), key=lambda kv: len(kv[1]))[:3])

# 동전의 엔트로피
H = lambda p: 0 if p in (0, 1) else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
print([round(H(p), 3) for p in (0.5, 0.9, 0.99)])

# 압축: 반복 많은 텍스트 vs 무작위 바이트
data_text = text.encode()
data_rand = os.urandom(len(data_text))
for name, d in [("text", data_text), ("random", data_rand)]:
    print(name, len(d), "->", len(zlib.compress(d, 9)))
```

실행 결과다(무작위 바이트의 압축 결과는 실행마다 몇 바이트 다를 수 있다).

```
엔트로피: 2.7481 허프만 평균: 2.8095
[('a', '0'), ('l', '1000'), ('k', '1001')]
[1.0, 0.469, 0.081]
text 420 -> 33
random 420 -> 431
```

허프만 평균 길이 2.81 비트는 엔트로피 2.75 비트 바로 위에 있다(H ≤ L < H + 1). 전체의 40% 가 넘는 가장 흔한 'a' 가 1 비트짜리 부호를 받는다. 압축 실험에서는 반복이 많은 텍스트가 420 바이트에서 33 바이트로 줄지만, 무작위 바이트는 오히려 조금 늘어난다. 줄일 정보가 없는 데이터에 형식 머리말이 붙은 것이다.

## 현업에서는

- **압축과 암호화의 순서.** 암호문은 무작위 바이트처럼 보이므로 압축되지 않는다. 그래서 압축이 필요하면 암호화 전에 한다. 다만 공격자가 입력 일부를 조절할 수 있는 상황에서 비밀과 그 입력을 함께 압축한 뒤 암호화하면, 압축된 길이로 비밀이 샌다. TLS 압축을 이용한 CRIME 공격이 대표 사례다([RFC 7457, 2.6절 Compression Attacks](https://www.rfc-editor.org/rfc/rfc7457#section-2.6)).
- **로그와 백업 압축.** 반복이 많은 로그는 크게 줄고, 이미 압축된 이미지·동영상·아카이브는 거의 줄지 않는다. 백업 파이프라인에서 압축이 CPU 만 쓰고 효과가 없는 데이터를 구분하면 시간을 아낀다. Zstandard 같은 최신 압축 형식도 허프만 부호와 FSE 라는 엔트로피 부호화를 핵심 단계로 쓴다([RFC 8478, Zstandard Compression](https://www.rfc-editor.org/rfc/rfc8478)).
- **비밀번호와 토큰의 강도.** 무작위로 고른 토큰의 강도는 엔트로피로 잰다. 62 개 문자에서 균등하게 20 자를 뽑으면 20 × log₂62 ≈ 119 비트다. 사람이 고른 비밀번호는 균등하지 않으므로 길이만으로 계산한 값보다 실제 엔트로피가 훨씬 낮다. 파이썬에서 토큰을 만들 때는 암호학적으로 안전한 난수를 쓰는 `secrets` 모듈을 쓴다([Python, secrets](https://docs.python.org/3/library/secrets.html)).
- **분류 모델의 손실.** 교차 엔트로피 손실이 크게 튀면, 모델이 정답 클래스에 거의 0 에 가까운 확률을 준 샘플이 있다는 뜻이다. −log q 는 q → 0 에서 무한대로 가기 때문이다. 라벨 오류를 찾는 실마리가 되기도 한다.

## 확인 문제

1. 확률 (1/2, 1/4, 1/8, 1/8) 인 분포의 엔트로피는?
2. 1 번 분포에 대해 허프만 부호를 만들고 평균 길이를 구하라.
3. 256 가지 값이 균등하게 나오는 바이트 열을 무손실 압축으로 줄일 수 있는가?
4. 실제 분포 p = (1/2, 1/2) 인데 q = (3/4, 1/4) 를 가정해 부호를 만들면 KL 발산은 몇 비트인가?

### 풀이

1. 0.5·1 + 0.25·2 + 0.125·3 + 0.125·3 = 1.75 비트.
2. 0, 10, 110, 111. 평균 길이 1.75 비트로 엔트로피와 정확히 같다(확률이 모두 2 의 거듭제곱이기 때문).
3. 평균적으로는 줄일 수 없다. 엔트로피가 이미 바이트당 8 비트로 최대다.
4. 0.5·log₂(0.5/0.75) + 0.5·log₂(0.5/0.25) = 0.5·(−0.585) + 0.5·1 ≈ 0.208 비트.

## 더 읽을거리 (References)

- C. E. Shannon, [A Mathematical Theory of Communication](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf), *Bell System Technical Journal*, 27, 1948
- [RFC 1951, DEFLATE Compressed Data Format Specification version 1.3](https://www.rfc-editor.org/rfc/rfc1951)
- [Python Documentation, zlib — Compression compatible with gzip](https://docs.python.org/3/library/zlib.html)
- Thomas M. Cover, Joy A. Thomas, *Elements of Information Theory*, 2판, Wiley, 2·5장
