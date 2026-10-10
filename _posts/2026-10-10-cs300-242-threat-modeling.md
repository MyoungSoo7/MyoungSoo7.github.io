---
layout: post
title: "[CS300 #242] 위협 모델링 — 코드보다 먼저 무엇이 잘못될 수 있는지 그린다"
date: 2026-10-10 22:02:00 +0900
categories: [cs]
tags: [cs300, security, threat-modeling, stride, risk]
---

컴퓨터공학 300 주제 시리즈의 242번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

위협 모델링은 시스템을 그림으로 그리고, 신뢰 경계마다 "무엇이 잘못될 수 있나" 를 체계적으로 묻고, 각 위협에 대한 대응을 정한 뒤, 그 결과를 검토하는 설계 단계의 습관이다.

## 왜 필요한가

취약점을 코드 리뷰나 침투 테스트에서 찾으면 고치는 비용이 크다. 설계가 이미 굳어 있기 때문이다. "관리자 API 를 인터넷에 열어 둔 구조" 는 코드 한 줄 고친다고 해결되지 않는다. 위협 모델링은 이런 구조적 결함을 화이트보드 단계에서 잡는다.

또 하나의 이유는 우선순위다. 보안 예산은 늘 부족하다. 모든 것을 막을 수 없으니 어떤 위협이 이 시스템에 실제로 해당하는지, 그중 무엇이 먼저인지 정해야 한다. 앞 글의 CIA 3요소가 "무엇을 지키나" 라면 위협 모델링은 "무엇으로부터, 어디서부터" 를 정한다.

## 핵심 개념

### 네 가지 질문

OWASP 위협 모델링 치트시트는 Adam Shostack 이 정리한 네 질문을 뼈대로 쓴다.

1. **무엇을 만들고 있나?** — 시스템 모델링. 보통 데이터 흐름도(DFD)를 그린다.
2. **무엇이 잘못될 수 있나?** — 위협 식별. STRIDE 같은 분류를 쓴다.
3. **그래서 무엇을 할 건가?** — 대응 결정.
4. **충분히 잘했나?** — 검토와 갱신.

방법론 이름은 여러 가지(STRIDE, PASTA, LINDDUN, 공격 트리 등)지만 이 네 질문을 벗어나지 않는다.

### 데이터 흐름도와 신뢰 경계

DFD 는 네 가지 요소만 쓴다.

```
[외부 개체]  사각형   사용자, 외부 API
(프로세스)   원       웹 서버, 워커
=데이터 저장소=  두 줄   DB, 파일, 큐
──>          화살표   데이터 흐름
- - - - -    점선     신뢰 경계
```

예시:

```
                신뢰 경계(인터넷 | 사내)
[브라우저] ──HTTPS──> : (API 서버) ──SQL──> =PostgreSQL=
                      :      │
                      :      └──> =로그 파일=
```

**신뢰 경계**는 권한 수준이 바뀌는 곳이다. 인터넷과 서버 사이, 컨테이너와 호스트 사이, 일반 사용자와 관리자 기능 사이. 위협은 대부분 경계를 넘는 흐름에서 생긴다. 경계를 넘어 들어오는 데이터는 전부 검증 대상이다.

### STRIDE

Microsoft 가 만든 분류로, 각 글자가 깨뜨리는 보안 속성과 짝을 이룬다.

| 위협 | 의미 | 깨지는 속성 | 대표 대책 |
|---|---|---|---|
| Spoofing | 다른 주체로 위장 | 진정성 | 인증, 상호 TLS |
| Tampering | 데이터·코드 변조 | 무결성 | 서명, MAC, 접근 통제 |
| Repudiation | 한 일을 부인 | 부인 방지 | 감사 로그, 서명 |
| Information disclosure | 허가 없는 노출 | 기밀성 | 암호화, 최소 권한 |
| Denial of service | 서비스 거부 | 가용성 | 속도 제한, 이중화 |
| Elevation of privilege | 권한 상승 | 인가 | 입력 검증, 샌드박스 |

DFD 요소마다 해당하는 글자만 묻는 방식을 STRIDE-per-element 라 한다. 예를 들어 데이터 흐름은 스스로 "위장" 할 주체가 아니므로 변조·노출·서비스 거부만 묻는다.

| 요소 | 적용 글자 |
|---|---|
| 외부 개체 | S, R |
| 프로세스 | S, T, R, I, D, E |
| 데이터 저장소 | T, I, D (+ 로그 저장소라면 R) |
| 데이터 흐름 | T, I, D |

### 대응의 네 가지

OWASP 치트시트가 소개하는 Shostack 의 대응 분류다.

- **완화(Mitigate)**: 위험을 줄이는 통제를 넣는다.
- **제거(Eliminate)**: 기능 자체를 뺀다. 안 쓰는 관리자 엔드포인트를 없애는 식이다.
- **이전(Transfer)**: 책임을 다른 주체에 넘긴다. 결제를 PG 사에 맡기는 식이다.
- **수용(Accept)**: 위험을 알고 받아들인다. 반드시 문서로 남기고 책임자를 정한다.

### 우선순위: 가능성 × 영향

NIST SP 800-30 은 위험을 위협이 일어날 가능성과 그때의 영향의 조합으로 평가한다. 정밀한 숫자보다 "높음/보통/낮음" 격자가 실무에서 더 잘 작동한다. 영향 축은 앞 글의 CIA 영향도를 그대로 쓰면 된다.

## 직접 해 보기

작은 DFD 를 코드로 적고 STRIDE-per-element 로 위협 후보 목록을 뽑는다. 신뢰 경계를 넘는 흐름은 우선순위를 올린다.

```python
STRIDE = {
    "external": "SR",       # 외부 개체: 위장, 부인
    "process":  "STRIDE",   # 프로세스: 여섯 가지 모두
    "store":    "TRID",     # 데이터 저장소: 변조, (로그라면)부인, 노출, 서비스 거부
    "flow":     "TID",      # 데이터 흐름: 변조, 노출, 서비스 거부
}
NAMES = {"S": "위장", "T": "변조", "R": "부인", "I": "정보 노출",
         "D": "서비스 거부", "E": "권한 상승"}

elements = [
    ("브라우저 사용자", "external", False),
    ("API 서버", "process", False),
    ("PostgreSQL", "store", False),
    ("브라우저 -> API (HTTPS)", "flow", True),   # 신뢰 경계를 넘는다
    ("API -> PostgreSQL", "flow", False),
]

threats = []
for name, kind, crosses in elements:
    for letter in STRIDE[kind]:
        prio = "높음" if crosses else "보통"
        threats.append((prio, name, NAMES[letter]))

for prio, name, t in sorted(threats, key=lambda x: x[0] != "높음"):
    print(f"[{prio}] {name}: {t}")
print("위협 후보 수:", len(threats))
```

출력 앞부분:

```
[높음] 브라우저 -> API (HTTPS): 변조
[높음] 브라우저 -> API (HTTPS): 정보 노출
[높음] 브라우저 -> API (HTTPS): 서비스 거부
[보통] 브라우저 사용자: 위장
...
위협 후보 수: 18
```

다섯 개 요소에서 18개 후보가 나왔다. 이건 **질문 목록**이지 결론이 아니다. 각 줄에 대해 "이미 막혀 있나? 어떻게?" 를 적는다. 예를 들어 "브라우저 → API: 변조" 는 TLS 로 완화됨, "API 서버: 권한 상승" 은 SQL 인젝션·역직렬화 경로를 점검해야 함, 하는 식이다. 답을 못 쓰는 줄이 진짜 할 일이다.

## 현업에서는

- **설계 리뷰 템플릿**: 새 서비스 설계 문서에 DFD 한 장과 STRIDE 표 한 장을 필수로 두는 팀이 많다. 두 시간짜리 회의 한 번이면 충분하다. 완벽한 모델보다 매 설계마다 하는 습관이 중요하다.
- **변경 시 갱신**: 위협 모델은 한 번 쓰고 끝나는 문서가 아니다. 새 외부 연동, 새 저장소, 인증 방식 변경이 생기면 DFD 가 바뀌므로 다시 본다. 네 번째 질문 "충분히 잘했나?" 가 이 갱신을 뜻한다.
- **쿠버네티스 위에서**: 홈랩 k3s 같은 환경에서도 신뢰 경계가 뚜렷하다. 인그레스(인터넷과 클러스터), 파드와 노드(컨테이너 탈출), 네임스페이스 간(네트워크 정책 유무), 그리고 API 서버(서비스 어카운트 토큰). "이 파드가 털리면 무엇까지 닿는가" 를 그려 보는 것만으로 과한 RBAC 권한이 드러난다.
- **공격자 관점 보강**: STRIDE 로 놓친 것은 MITRE ATT&CK 같은 공격 기법 목록으로 교차 확인한다.

## 확인 문제

1. 위협 모델링의 네 가지 질문을 순서대로 적어라.
2. DFD 에서 신뢰 경계가 중요한 이유는?
3. 감사 로그가 없는 관리자 API 에서 가장 먼저 떠올려야 할 STRIDE 글자는 무엇인가?
4. "위험 수용" 을 선택할 때 반드시 함께 해야 할 일은?

### 풀이

1. 무엇을 만들고 있나 → 무엇이 잘못될 수 있나 → 무엇을 할 건가 → 충분히 잘했나.
2. 권한 수준이 바뀌는 지점이라 공격이 들어오는 입구가 되기 때문이다. 경계를 넘는 데이터는 검증·인증 대상이다.
3. R(부인). 누가 무엇을 했는지 증명할 수 없다. 관리자 기능이므로 E(권한 상승)도 함께 본다.
4. 수용 근거와 책임자를 문서로 남기고, 다시 검토할 시점을 정한다.

## 더 읽을거리 (References)

- OWASP, [Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)
- OWASP, [Threat Modeling (Community page)](https://owasp.org/www-community/Threat_Modeling)
- Microsoft, [Microsoft Threat Modeling Tool threats (STRIDE)](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- NIST, [SP 800-30 Rev. 1: Guide for Conducting Risk Assessments](https://csrc.nist.gov/pubs/sp/800/30/r1/final)
- 교과서: Adam Shostack, *Threat Modeling: Designing for Security*, Wiley, 2014.
