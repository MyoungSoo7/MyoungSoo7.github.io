---
layout: post
title: "[CS300 #221] 클라우드 서비스 모델 — IaaS·PaaS·SaaS, 누가 무엇을 책임지는가"
date: 2026-10-10 21:41:00 +0900
categories: [cs]
tags: [cs300, devops, cloud, iaas, paas, saas]
---

컴퓨터공학 300 주제 시리즈의 221번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

IaaS·PaaS·SaaS 는 "어디까지를 사업자가 관리하고, 어디부터를 내가 관리하는가"의 경계선이다. 기능 목록이 아니라 책임의 분할로 읽어야 한다.

## 왜 필요한가

"클라우드로 옮기자"는 말은 너무 넓다. 가상 머신을 빌리는 것도, 코드만 올리면 돌아가는 플랫폼을 쓰는 것도, 완성된 메일 서비스를 구독하는 것도 모두 클라우드다. 그런데 셋은 운영 부담이 완전히 다르다.

- 가상 머신을 빌리면 OS 보안 패치는 내 일이다.
- 플랫폼을 쓰면 OS 패치는 사업자 일이지만 애플리케이션 버그는 내 일이다.
- 완성된 서비스를 쓰면 코드는 없지만 계정·권한·데이터 설정은 여전히 내 일이다.

장애가 났을 때 누구에게 전화해야 하는지, 보안 감사에서 무엇을 증명해야 하는지가 이 구분에서 나온다. 그래서 용어부터 정확히 잡아야 한다.

## 핵심 개념

### NIST 의 정의

가장 널리 인용되는 정의는 미국 NIST 의 SP 800-145 (2011)다. 이 문서는 클라우드 컴퓨팅을 다섯 가지 필수 특성, 세 가지 서비스 모델, 네 가지 배치 모델로 설명한다.

필수 특성 다섯 가지는 다음과 같다.

| 특성 | 뜻 |
|---|---|
| On-demand self-service | 사람 개입 없이 사용자가 직접 자원을 할당받는다 |
| Broad network access | 표준 네트워크 수단으로 접근한다 |
| Resource pooling | 여러 사용자가 자원 풀을 나눠 쓴다(멀티테넌시) |
| Rapid elasticity | 수요에 따라 빠르게 늘고 준다 |
| Measured service | 사용량이 계량되고 보고된다 |

이 다섯이 없으면 데이터센터에 서버를 둔 것과 다르지 않다. 예를 들어 서버 한 대를 신청하는 데 담당자 결재와 일주일이 걸린다면 "self-service"도 "rapid elasticity"도 아니다.

### 세 가지 서비스 모델

NIST 정의를 요약하면 이렇다.

- **SaaS (Software as a Service)**: 사업자의 애플리케이션을 쓴다. 사용자는 네트워크·서버·OS·스토리지는 물론 애플리케이션 기능도 관리하지 않는다. 사용자별 설정 정도만 만진다.
- **PaaS (Platform as a Service)**: 사업자가 지원하는 언어·라이브러리·도구로 만든 내 애플리케이션을 올린다. 하부 인프라는 관리하지 않지만, 배포한 애플리케이션과 그 실행 환경 설정은 내가 관리한다.
- **IaaS (Infrastructure as a Service)**: 처리 능력·스토리지·네트워크 같은 기본 자원을 받는다. 그 위에 OS 부터 애플리케이션까지 임의 소프트웨어를 올린다. 하부 클라우드 인프라는 관리하지 않지만 OS·스토리지·배포 애플리케이션은 내가 관리한다.

### 책임 스택으로 보기

아래 그림이 핵심이다. 왼쪽부터 내가 관리하는 범위가 줄어든다.

```
             온프레미스   IaaS        PaaS        SaaS
데이터/권한    [나]        [나]        [나]        [나]
애플리케이션   [나]        [나]        [나]        사업자
런타임         [나]        [나]        사업자      사업자
OS             [나]        [나]        사업자      사업자
가상화         [나]        사업자      사업자      사업자
서버/스토리지  [나]        사업자      사업자      사업자
네트워크/건물  [나]        사업자      사업자      사업자
```

주목할 점은 맨 위 줄이다. SaaS 를 써도 데이터와 접근 권한은 사용자 책임으로 남는다. 클라우드 사업자들이 "공동 책임 모델(shared responsibility model)"이라고 부르는 것이 이 그림이다. 공유 링크를 "누구나 보기"로 열어 둔 사고는 SaaS 사업자의 잘못이 아니다.

### 배치 모델

서비스 모델과 별개 축으로 배치 모델이 있다. NIST 는 네 가지를 든다.

- Private cloud: 한 조직이 독점해서 쓴다.
- Community cloud: 관심사를 공유하는 여러 조직이 함께 쓴다.
- Public cloud: 일반 대중에게 열려 있다.
- Hybrid cloud: 둘 이상을 묶되, 데이터·애플리케이션 이식성을 갖춘 형태다.

"프라이빗 IaaS"처럼 두 축을 조합해서 말할 수 있다. 사내 서버 몇 대에 쿠버네티스를 깔아 팀원들이 직접 네임스페이스를 받아 쓰게 했다면, 규모는 작아도 프라이빗 클라우드의 성격을 띤다.

### 경계가 흐려진 영역

현실의 서비스는 세 칸에 딱 맞지 않는다.

- **CaaS (컨테이너)**: 관리형 쿠버네티스는 IaaS 와 PaaS 사이다. 컨트롤 플레인은 사업자가, 워크로드와 노드 설정 일부는 내가 맡는다.
- **FaaS (서버리스 함수)**: 함수 코드만 올린다. PaaS 의 극단적 형태로 볼 수 있다. 실행 시간 단위로 과금된다.
- **관리형 DB**: DB 엔진 패치·백업 자동화는 사업자가, 스키마·인덱스·쿼리는 내가 책임진다.

이런 이름(CaaS, FaaS)은 NIST 정의에 없는 업계 용어다. 새 용어를 만나면 "어느 층부터 내 책임인가"를 물어보면 된다.

### 무엇을 고를까

| 기준 | IaaS 쪽 | SaaS 쪽 |
|---|---|---|
| 통제권 | 높다 | 낮다 |
| 운영 부담 | 크다 | 작다 |
| 이식성 | 상대적으로 높다 | 데이터 반출에 의존 |
| 맞춤 | 무엇이든 가능 | 제공 기능 안에서만 |

차별화가 필요한 핵심 기능은 위로(IaaS·PaaS), 회계·메일·메신저 같은 범용 기능은 아래로(SaaS) 보내는 것이 일반적인 판단이다.

## 직접 해 보기

책임 스택을 코드로 표현해 보자. 계층 목록과 모델별 경계를 정해 두면 "이 사고는 누구 책임인가"를 자동으로 판정할 수 있다.

```python
LAYERS = ["network", "server", "virtualization", "os",
          "runtime", "application", "data_access"]

# 각 모델에서 사용자가 관리하기 시작하는 계층 인덱스
USER_STARTS_AT = {
    "on-prem": 0,
    "iaas": LAYERS.index("os"),
    "paas": LAYERS.index("application"),
    "saas": LAYERS.index("data_access"),
}

def owner(model, layer):
    return "user" if LAYERS.index(layer) >= USER_STARTS_AT[model] else "provider"

incidents = [
    ("iaas", "os", "커널 보안 패치 누락"),
    ("paas", "runtime", "언어 런타임 취약점"),
    ("saas", "data_access", "공유 링크 전체 공개"),
    ("paas", "application", "SQL 인젝션"),
]
for model, layer, desc in incidents:
    print(f"{model:5} {layer:12} {owner(model, layer):8} {desc}")

print()
print("model   user-managed layers")
for m in USER_STARTS_AT:
    print(f"{m:7} {LAYERS[USER_STARTS_AT[m]:]}")
```

실행 결과는 다음과 같다.

```
iaas  os           user     커널 보안 패치 누락
paas  runtime      provider 언어 런타임 취약점
saas  data_access  user     공유 링크 전체 공개
paas  application  user     SQL 인젝션

model   user-managed layers
on-prem ['network', 'server', 'virtualization', 'os', 'runtime', 'application', 'data_access']
iaas    ['os', 'runtime', 'application', 'data_access']
paas    ['application', 'data_access']
saas    ['data_access']
```

실제 계약에서는 경계가 이보다 세밀하다. 예를 들어 PaaS 에서 런타임 버전 선택은 사용자가 하고, 그 버전의 패치는 사업자가 한다. 표를 만들 때는 계약서와 사업자 문서의 책임 분할표를 기준으로 삼아야 한다.

## 현업에서는

- **보안 점검표가 모델별로 다르다.** IaaS 가상 머신이 있으면 OS 패치 주기, SSH 접근 통제, 방화벽 규칙이 점검 대상이다. SaaS 만 쓰면 SSO·MFA 강제, 외부 공유 정책, 감사 로그 보존이 핵심이다.
- **장애 원인 분류.** 관리형 DB 가 느려졌을 때 사업자 상태 페이지를 먼저 보는 사람과, 쿼리 실행 계획부터 보는 사람이 있다. 책임 스택을 알면 순서가 정해진다. 엔진 장애는 사업자 쪽, 느린 쿼리는 내 쪽이다.
- **홈랩도 같은 언어로 설명된다.** 집에 노드 몇 대로 k3s 클러스터를 꾸리면 하드웨어·네트워크·OS·쿠버네티스까지 전부 내 책임인 온프레미스다. 그 위에서 팀원이 매니페스트만 올려 서비스를 띄운다면 그 팀원에게 이 클러스터는 PaaS 에 가깝다. 같은 시스템이 보는 사람에 따라 다른 모델이 된다.
- **비용 구조.** IaaS 는 켜 둔 시간만큼, 서버리스는 실행된 만큼, SaaS 는 사용자 수만큼 내는 경우가 많다. 트래픽이 들쭉날쭉하면 실행량 과금이 유리하고, 꾸준하면 예약형 인스턴스가 유리할 수 있다. 이 계산은 240번 FinOps 주제로 이어진다.

## 확인 문제

1. NIST SP 800-145 가 제시한 클라우드의 필수 특성 다섯 가지를 쓰라.
2. PaaS 에서 OS 보안 패치는 누구 책임인가? 애플리케이션 의존 라이브러리의 취약점은?
3. SaaS 를 쓰는데 데이터가 유출됐다. 사업자 책임이 아닐 수 있는 대표적 경우를 하나 들라.
4. "하이브리드 클라우드"는 서비스 모델인가, 배치 모델인가?
5. 관리형 쿠버네티스는 왜 IaaS 와 PaaS 중 하나로 딱 떨어지지 않는가?

### 풀이

1. On-demand self-service, broad network access, resource pooling, rapid elasticity, measured service.
2. OS 패치는 사업자 책임이다. 내가 넣은 라이브러리는 애플리케이션의 일부이므로 내 책임이다.
3. 접근 권한·공유 설정을 사용자가 잘못 연 경우. 데이터·접근 통제 계층은 SaaS 에서도 사용자 책임이다.
4. 배치 모델이다. 서비스 모델(IaaS·PaaS·SaaS)과 독립된 축이다.
5. 컨트롤 플레인은 사업자가 관리하지만 워크로드 정의와 노드·네트워크 정책 일부는 사용자가 관리하기 때문이다. 경계가 계층 중간에 있다.

## 더 읽을거리 (References)

- P. Mell, T. Grance, [NIST SP 800-145: The NIST Definition of Cloud Computing](https://csrc.nist.gov/pubs/sp/800/145/final), NIST, 2011.
- [NIST SP 800-145 원문 PDF](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-145.pdf)
- AWS, [Overview of Amazon Web Services — Types of Cloud Computing](https://docs.aws.amazon.com/whitepapers/latest/aws-overview/types-of-cloud-computing.html)
