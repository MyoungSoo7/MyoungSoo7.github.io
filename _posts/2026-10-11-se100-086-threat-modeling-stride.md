---
layout: post
title: "[SE100 #086] 위협 모델링과 STRIDE"
date: 2026-10-11 17:08:54 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, threat-modeling, stride, data-flow-diagram, security-design]
---

소프트웨어 공학 100 주제 시리즈의 86번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

STRIDE 는 "무엇이 잘못될 수 있는가" 를 빠짐없이 묻기 위한 **위협 분류 체크리스트**다. 데이터 흐름도(DFD)의 요소마다 해당 범주를 적용하면 위협 목록이 체계적으로 나오고, 각 범주는 깨지는 보안 속성 하나에 대응하므로 대책의 방향도 바로 정해진다.

## 왜 필요한가

보안 결함 중 상당수는 코드 한 줄의 실수가 아니라 **설계 단계의 누락**이다. 웹훅 수신 엔드포인트에 서명 검증이 아예 없는 것, 관리자 API 가 내부망이라는 이유로 인증이 없는 것, 감사 로그를 남기지 않아 "누가 환불 버튼을 눌렀는가" 에 답할 수 없는 것. 이런 결함은 코드 리뷰에서 잘 보이지 않는다. 리뷰어는 있는 코드를 보지, **없어야 할 것이 아니라 있어야 하는데 없는 것**을 찾기 어렵다.

위협 모델링은 설계를 그림으로 놓고 체계적으로 질문해서 이 누락을 찾는 활동이다. 개념과 네 가지 질문, 기본 STRIDE 표는 CS300 [위협 모델링]({% post_url 2026-10-10-cs300-242-threat-modeling %}) 에서 다뤘다. 이 글은 STRIDE 의 원전과 구조, **요소별 적용**, 다른 기법과의 조합을 다룬다.

## 핵심 개념

### 원전: Kohnfelder 와 Garg, 1999

STRIDE 는 Microsoft 의 Loren Kohnfelder 와 Praerit Garg 가 1999년 4월 1일자 사내 문서 [The threats to our products](https://shostack.org/files/microsoft/The-Threats-To-Our-Products.docx) 에서 제안했다. 문서는 Microsoft Security Task Force 가 모든 제품 팀에 권고하는 보안 위협 모델로 S.T.R.I.D.E. 를 소개하며, 이를 **설계 단계**에서 제품이 노출될 수 있는 위협 유형을 식별하는 데 쓰라고 한다. 위협 식별이 사전 보안 분석의 첫 단계이고, 그다음이 구현의 취약점 식별과 대책이라는 순서도 이때 이미 제시됐다.

### 여섯 범주와 깨지는 속성

Adam Shostack 은 [threat modeling 리소스 페이지](https://shostack.org/resources/threat-modeling)에서 각 범주를 그것이 침해하는 속성과 짝지어 설명한다. Microsoft 의 [Threat Modeling Tool 문서](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)도 같은 여섯 범주를 정의한다.

| 범주 | 뜻 | 침해되는 속성 | 대책의 방향 |
|---|---|---|---|
| **S**poofing | 다른 사람·다른 무엇인 척하기 | 진정성(authenticity) | 인증: 비밀번호+MFA, mTLS, 서명 |
| **T**ampering | 허가 없이 바꾸기 | 무결성(integrity) | 해시·MAC·서명, 접근 통제, 불변 저장 |
| **R**epudiation | 하지 않았다고 주장하기 | 부인 방지(non-repudiation) | 감사 로그, 서명, 타임스탬프 |
| **I**nformation disclosure | 봐선 안 될 사람에게 정보 노출 | 기밀성(confidentiality) | 암호화, 최소 노출, 접근 통제 |
| **D**enial of service | 필요한 자원을 고갈시키기 | 가용성(availability) | 속도 제한, 쿼터, 격리, 오토스케일 |
| **E**levation of privilege | 허가되지 않은 일을 하게 되기 | 인가(authorization) | 최소 권한, 서버 측 권한 검사, 샌드박스 |

이 대응표가 STRIDE 의 실용적 가치다. 위협을 범주로 분류하는 순간 "어떤 종류의 통제가 필요한가" 가 정해진다.

### DFD 의 요소

STRIDE 는 대개 데이터 흐름도 위에서 적용한다. DFD 의 요소는 다섯 가지다.

```
 [외부 개체]  ── 데이터 흐름 ──▶  ( 프로세스 )  ── 데이터 흐름 ──▶  ═ 데이터 저장소 ═
  사용자, 외부 시스템              우리 코드                         DB, 파일, 큐
 - - - - - - - - - - - - - 신뢰 경계(trust boundary) - - - - - - - - - - - - -
```

신뢰 경계는 권한·소유자·네트워크 영역이 바뀌는 곳이다. 위협은 대부분 **경계를 넘는 흐름**에서 생긴다. 경계가 하나도 없는 DFD 는 거의 항상 뭔가를 빠뜨린 그림이다.

### STRIDE-per-element

요소 유형마다 의미 있는 범주가 다르다. Shostack 의 *Threat Modeling: Designing for Security* (Wiley, 2014)가 정리한 대응은 다음과 같다.

| 요소 | S | T | R | I | D | E |
|---|---|---|---|---|---|---|
| 외부 개체 | ✓ | | ✓ | | | |
| 프로세스 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 데이터 흐름 | | ✓ | | ✓ | ✓ | |
| 데이터 저장소 | | ✓ | △ | ✓ | ✓ | |

(△: 저장소가 감사 로그를 담고 있을 때 부인 문제가 생긴다.)

외부 개체는 우리가 통제하지 않으므로 "그것이 위조되는가(S), 자기 행동을 부인하는가(R)" 만 묻는다. 데이터 흐름은 위조나 권한 상승의 주체가 아니라 변조·노출·차단의 대상이다. 이렇게 하면 요소 n 개에 대해 질문 목록이 기계적으로 생성되어, 회의가 "생각나는 위협 말하기" 에서 "표 채우기" 로 바뀐다. 흐름의 양 끝을 함께 보는 STRIDE-per-interaction 변형도 있다.

### 네 가지 질문과 선언문

[Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/)는 위협 모델링을 "보안·프라이버시 특성에 관한 우려를 드러내기 위해 시스템의 표현을 분석하는 것" 으로 정의하고 네 질문을 둔다. 무엇을 만들고 있는가, 무엇이 잘못될 수 있는가, 그에 대해 무엇을 할 것인가, 충분히 잘했는가. STRIDE 는 두 번째 질문에 답하는 도구 중 하나일 뿐이다. 선언문은 피해야 할 안티패턴도 든다.

- **영웅 위협 모델러(Hero Threat Modeler)** — 특별한 재능이 있어야 하는 일이 아니다. 누구나 할 수 있고 해야 한다.
- **문제에 대한 감탄(Admiration for the Problem)** — 분석에서 멈추지 말고 실용적인 해법까지 간다.
- **과도한 집중(Tendency to Overfocus)** — 공격자·자산·기법 하나에 매몰되지 않는다.
- **완벽한 표현(Perfect Representation)** — 하나의 이상적인 그림은 없다. 여러 표현이 서로 다른 문제를 비춘다.

### 함께 쓰는 기법

| 기법 | 관점 | STRIDE 와의 관계 |
|---|---|---|
| [공격 트리](https://www.schneier.com/academic/archives/1999/12/attack_trees.html) (Schneier, Dr. Dobb's Journal, 1999) | 공격자 목표를 루트로, 달성 방법을 잎으로 분해 | STRIDE 로 찾은 고위험 위협 하나를 깊이 파고들 때 |
| [LINDDUN](https://linddun.org/) (KU Leuven) | 프라이버시 위협: Linking, Identifying, Non-repudiation, Detecting, Data Disclosure, Unawareness, Non-compliance | STRIDE 가 다루지 않는 프라이버시 축. 개인정보를 다루면 함께 쓴다 |
| [MITRE ATT&CK](https://attack.mitre.org/) | 실제 관찰된 공격자 전술·기법 지식 기반 | 운영 환경의 탐지·대응 설계 쪽 |

흥미롭게도 LINDDUN 에서 부인 방지(Non-repudiation)는 **위협**이다. 보안에서는 사용자가 행동을 부인하지 못하게 하는 것이 목표지만, 프라이버시에서는 사용자가 원치 않게 자기 행동을 증명당하는 것이 피해다. 두 관점이 충돌하는 지점은 설계에서 명시적으로 결정해야 한다.

## 예제

### 결제 웹훅 수신기

외부 PG 사가 결제 완료를 우리 서버에 HTTP 로 알려 주고, 우리는 주문 상태를 바꾼다.

```
 [PG 사] ──(1) POST /webhook──▶ (웹훅 핸들러) ──(2) UPDATE──▶ ═ 주문 DB ═
                 ↑ 신뢰 경계: 인터넷 → 우리 VPC        │
                                                     └──(3) 이벤트──▶ ═ 감사 로그 ═
```

요소별로 표를 채운 결과의 일부다.

| 요소 | 범주 | 위협 | 대책 |
|---|---|---|---|
| PG 사(외부 개체) | S | 공격자가 PG 사인 척 "결제 완료" 를 보낸다 | 공유 비밀 기반 HMAC 서명 검증, 가능하면 발신 IP 허용 목록 |
| PG 사 | R | PG 사가 통지를 보낸 적 없다고 주장 | 원문 페이로드·서명·수신 시각을 감사 로그에 저장 |
| 흐름 (1) | T | 중간에서 금액 필드 변조 | TLS + 서명 검증, **금액은 통지값이 아니라 PG 조회 API 로 재확인** |
| 흐름 (1) | D | 통지 폭주로 핸들러 마비 | 속도 제한, 큐로 비동기 처리 |
| 웹훅 핸들러 | T | 같은 통지를 재전송(replay)해 중복 처리 | 이벤트 ID 멱등 처리, 타임스탬프 허용 창 |
| 웹훅 핸들러 | E | 핸들러의 DB 계정이 주문 외 테이블도 수정 가능 | 전용 DB 계정, 필요한 컬럼만 UPDATE 권한 |
| 웹훅 핸들러 | I | 검증 실패 시 상세 오류에 내부 정보 노출 | 외부에는 일반 오류만, 상세는 내부 로그로 |
| 감사 로그(저장소) | T | 침입자가 흔적 삭제 | 추가 전용(append-only) 저장소, 별도 계정 |

"금액 재확인" 처럼 STRIDE 표를 채우다 보면 원래 설계에 없던 요구사항이 나온다. 이것이 위협 모델링의 산출물이다. 코드를 짜기 전에 나와야 싸다.

### 위협 모델을 코드로

OWASP 의 [pytm](https://github.com/OWASP/pytm) 은 DFD 를 파이썬으로 기술하고 위협 후보와 다이어그램을 생성한다. 설계가 바뀌면 PR 로 함께 바뀌게 할 수 있다.

```python
from pytm import TM, Actor, Server, Datastore, Dataflow, Boundary

tm = TM("payment-webhook")
tm.description = "PG 결제 완료 웹훅 수신"
internet, vpc = Boundary("Internet"), Boundary("VPC")

pg = Actor("PG provider");      pg.inBoundary = internet
handler = Server("Webhook handler"); handler.inBoundary = vpc
orders = Datastore("Order DB");  orders.inBoundary = vpc

notify = Dataflow(pg, handler, "POST /webhook (payment.completed)")
notify.protocol = "HTTPS"; notify.dstPort = 443
update = Dataflow(handler, orders, "UPDATE order status")
update.protocol = "SQL"

tm.process()   # --dfd 로 다이어그램, --report 로 위협 보고서
```

GUI 를 선호하면 [OWASP Threat Dragon](https://owasp.org/www-project-threat-dragon/) 도 있다. 도구보다 중요한 것은 **설계 변경 PR 에 위협 모델 갱신이 따라오는 습관**이다.

## 흔한 오해와 함정

- **"STRIDE = 위협 모델링"** — STRIDE 는 두 번째 질문용 체크리스트다. 대책 결정과 사후 검증이 빠지면 위협 목록만 남는다.
- **DFD 없이 STRIDE** — 대상 없이 범주를 읊으면 일반론("DoS 가 있을 수 있다")만 나온다. 요소별로 적용해야 구체적 위협이 나온다.
- **한 번 하고 끝** — 선언문의 가치처럼 위협 모델은 "스냅숏이 아니라 여정" 이다. 새 경계(외부 연동, 새 저장소)가 생길 때마다 갱신한다.
- **모든 위협을 다 막으려 함** — 대응에는 완화 외에 제거(기능 삭제), 이전(외부 서비스에 위임), 수용(기록하고 감수)도 있다. 수용도 **명시적 결정**이면 정당하다.
- **공격자 상상에만 몰두** — 정교한 국가급 공격 시나리오보다 "서명 검증이 없다" 같은 기본 누락이 훨씬 흔하다.

## 확인 문제

1. STRIDE 의 각 범주가 침해하는 보안 속성을 짝지어 보라.
2. STRIDE-per-element 에서 외부 개체에 S 와 R 만 적용하는 이유는?
3. 웹훅 예에서 HMAC 서명 검증을 해도 남는 Tampering 계열 위협은 무엇이며, 대책은?
4. 보안 관점의 부인 방지와 LINDDUN 의 Non-repudiation 위협이 충돌하는 예를 들라.

### 풀이

1. Spoofing–진정성, Tampering–무결성, Repudiation–부인 방지, Information disclosure–기밀성, Denial of service–가용성, Elevation of privilege–인가.
2. 외부 개체는 우리가 통제하지 않는 대상이라 그 내부의 변조·노출·권한 문제는 우리 설계 범위 밖이다. 우리가 물어야 할 것은 그것이 진짜인지(S)와 자기 행동을 부인할 수 있는지(R)다.
3. 정상 서명이 붙은 과거 메시지를 다시 보내는 재전송(replay). 이벤트 ID 기반 멱등 처리와 타임스탬프 허용 창으로 막는다.
4. 익명 제보 시스템에서 운영자는 악용 대응을 위해 제보자 행동을 추적·증명하고 싶지만(보안의 부인 방지), 제보자에게는 자기가 제보했다는 사실이 증명 가능해지는 것 자체가 프라이버시 피해다.

## 더 읽을거리 (References)

- Loren Kohnfelder, Praerit Garg, [The threats to our products](https://shostack.org/files/microsoft/The-Threats-To-Our-Products.docx), Microsoft, 1999-04-01
- Microsoft, [Microsoft Threat Modeling Tool threats](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- Adam Shostack, [Threat Modeling resources](https://shostack.org/resources/threat-modeling)
- Adam Shostack, *Threat Modeling: Designing for Security*, Wiley, 2014 (서지 정보)
- [Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/)
- OWASP, [Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html), [pytm](https://github.com/OWASP/pytm), [Threat Dragon](https://owasp.org/www-project-threat-dragon/)
- Bruce Schneier, [Attack Trees](https://www.schneier.com/academic/archives/1999/12/attack_trees.html), Dr. Dobb's Journal, 1999
- [LINDDUN privacy threat modeling](https://linddun.org/)
- MITRE, [ATT&CK](https://attack.mitre.org/)
