---
layout: post
title: "[CS300 #231] Infrastructure as Code — Terraform 의 선언, 상태, 계획"
date: 2026-10-10 21:51:00 +0900
categories: [cs]
tags: [cs300, devops, terraform, iac, infrastructure]
---

컴퓨터공학 300 주제 시리즈의 231번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

IaC 는 서버·네트워크·DB 같은 인프라를 코드로 선언하고 버전 관리하는 방식이다. Terraform 은 설정(원하는 상태), 상태 파일(마지막으로 알고 있는 실제 상태), 실제 인프라 셋을 비교해 "무엇을 만들고 바꾸고 지울지" 계획을 세운 뒤 적용한다.

## 왜 필요한가

클라우드 콘솔에서 마우스로 서버를 만들면 처음에는 빠르다. 하지만 이런 질문에 답할 수 없게 된다.

- 운영 환경과 똑같은 스테이징을 하나 더 만들 수 있는가?
- 이 보안 그룹 규칙은 누가, 언제, 왜 열었는가?
- 리전 하나가 통째로 사라지면 몇 시간 안에 다시 만들 수 있는가?

손으로 만든 인프라는 문서와 실제가 어긋나고, 서버마다 미세하게 달라지는 "눈송이 서버(snowflake server)"가 된다. IaC 는 인프라에 코드의 장점을 그대로 가져온다. 리뷰, 이력, 재현, 자동화.

## 핵심 개념

### 선언형 vs 명령형

| 방식 | 기술 내용 | 예 |
|---|---|---|
| 명령형 | 무엇을 할지 순서대로 | 셸 스크립트, 클라우드 CLI 호출 나열 |
| 선언형 | 최종 상태가 어떠해야 하는지 | Terraform, CloudFormation, 쿠버네티스 매니페스트 |

명령형 스크립트를 두 번 실행하면 서버가 두 대 생길 수 있다. 선언형 도구는 "서버 한 대"라고 적혀 있으면 몇 번을 실행해도 한 대다. 이 성질을 **멱등성(idempotency)** 이라 한다.

### Terraform 의 구성 요소

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "example-tf-state"
    key    = "prod/network.tfstate"
    region = "ap-northeast-2"
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-northeast-2"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "main" }
}

resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.main.id      # 참조 = 암묵적 의존성
  cidr_block = "10.0.1.0/24"
}

output "subnet_id" {
  value = aws_subnet.app.id
}
```

| 블록 | 역할 |
|---|---|
| `provider` | 특정 API(클라우드, 쿠버네티스, DNS 등)와 대화하는 플러그인 |
| `resource` | 관리할 인프라 객체 하나 |
| `data` | 이미 있는 것을 읽기만 함 |
| `variable` / `output` | 입력과 출력 |
| `module` | 재사용 가능한 리소스 묶음 |
| `backend` | 상태 파일을 어디에 둘지 |

설정 언어는 HCL(HashiCorp Configuration Language) 이다. 파일 순서는 의미가 없다. Terraform 은 참조 관계(`aws_vpc.main.id`)로 **의존성 그래프**를 만들고, 그래프 순서대로, 독립적인 것은 병렬로 처리한다.

### 상태(state)

Terraform 은 `terraform.tfstate` 라는 상태 파일에 "설정의 이 리소스가 실제 세계의 어느 객체(ID)인가"를 기록한다. 상태가 필요한 이유는 다음과 같다.

- 설정의 `aws_vpc.main` 과 클라우드의 `vpc-0abc...` 를 짝짓는다.
- 설정에서 리소스를 지우면, 무엇을 지워야 하는지 상태를 보고 안다.
- 리소스 속성을 캐시해 큰 인프라에서도 계획을 빠르게 세운다.

상태 파일에는 비밀값(DB 비밀번호 등)이 평문으로 들어갈 수 있다. 그래서 Git 에 커밋하지 않는다. 팀에서는 원격 백엔드(S3, GCS, Terraform Cloud 등)에 두고, 동시에 두 사람이 적용하지 못하도록 **잠금(locking)** 을 쓴다.

### 작업 흐름

```bash
terraform init       # 프로바이더·모듈 다운로드, 백엔드 초기화
terraform fmt        # 포맷 정리
terraform validate   # 문법·참조 검사
terraform plan       # 변경 계획 출력(아무것도 바꾸지 않음)
terraform apply      # 계획을 확인 후 적용
terraform destroy    # 전부 삭제
```

`plan` 의 기호를 읽을 줄 알아야 한다.

| 기호 | 뜻 |
|---|---|
| `+` | 생성 |
| `~` | 제자리 수정(update in-place) |
| `-` | 삭제 |
| `-/+` | 삭제 후 재생성(replace). 그 자리에서 바꿀 수 없는 속성이 바뀌었을 때 |

가장 주의할 것은 `-/+` 다. 이름이나 리전처럼 바꿀 수 없는 속성을 고치면 Terraform 은 리소스를 지우고 새로 만든다. DB 라면 데이터가 날아간다. `lifecycle { prevent_destroy = true }` 로 중요한 리소스를 보호할 수 있다.

### drift

누군가 콘솔에서 손으로 설정을 바꾸면 실제 인프라와 상태·설정이 어긋난다. `plan` 은 먼저 실제 상태를 새로 읽어(refresh) 이 차이를 찾아내고, 설정대로 되돌리는 변경을 계획에 넣는다. 손으로 바꾼 것을 유지하고 싶다면 설정 코드를 고쳐야 한다.

## 직접 해 보기

`plan` 의 핵심 로직을 파이썬으로 흉내 내 보자. 설정과 상태를 비교해 생성·수정·교체·삭제를 고르고, 의존성 순서로 정렬한다.

```python
from graphlib import TopologicalSorter

FORCE_NEW = {"aws_db_instance": {"engine"}, "aws_subnet": {"cidr_block"}}

config = {
    "aws_vpc.main":        {"cidr_block": "10.0.0.0/16", "tags": "main-v2"},
    "aws_subnet.app":      {"cidr_block": "10.0.2.0/24", "deps": ["aws_vpc.main"]},
    "aws_db_instance.db":  {"engine": "postgres", "size": "large",
                            "deps": ["aws_subnet.app"]},
    "aws_s3_bucket.logs":  {"acl": "private"},
}
state = {
    "aws_vpc.main":        {"cidr_block": "10.0.0.0/16", "tags": "main"},
    "aws_subnet.app":      {"cidr_block": "10.0.1.0/24"},
    "aws_db_instance.db":  {"engine": "postgres", "size": "small"},
    "aws_instance.legacy": {"type": "t3.micro"},
}

def attrs(d):
    return {k: v for k, v in d.items() if k != "deps"}

def plan(config, state):
    actions = {}
    for addr in config.keys() | state.keys():
        if addr not in state:
            actions[addr] = "+"
        elif addr not in config:
            actions[addr] = "-"
        else:
            want, have = attrs(config[addr]), state[addr]
            changed = {k for k in want if want[k] != have.get(k)}
            rtype = addr.split(".")[0]
            if changed & FORCE_NEW.get(rtype, set()):
                actions[addr] = "-/+"
            elif changed:
                actions[addr] = "~"
    return actions

actions = plan(config, state)
graph = {a: set(config.get(a, {}).get("deps", [])) for a in config}
order = list(TopologicalSorter(graph).static_order())
for addr in order + sorted(set(state) - set(config)):
    if addr in actions:
        print(f"{actions[addr]:>3} {addr}")
counts = {s: list(actions.values()).count(s) for s in ["+", "~", "-/+", "-"]}
print("Plan:", counts)
```

결과는 다음과 같다.

```
  ~ aws_vpc.main
  + aws_s3_bucket.logs
-/+ aws_subnet.app
  ~ aws_db_instance.db
  - aws_instance.legacy
Plan: {'+': 1, '~': 2, '-/+': 1, '-': 1}
```

서브넷의 CIDR 을 바꾸자 교체(`-/+`)가 나왔다. 실제 Terraform 에서 서브넷 교체는 그 안에 있는 리소스에도 영향을 준다. `plan` 결과의 `-/+` 와 `-` 줄은 반드시 한 줄씩 읽고 적용한다.

## 현업에서는

- **plan 을 PR 에 붙인다.** 인프라 변경 PR 에 CI 가 `terraform plan` 결과를 댓글로 남기게 하면, 리뷰어가 코드 diff 와 실제 변경(생성 몇 개, 교체 몇 개)을 함께 본다. 승인 후 merge 시점에 apply 한다.
- **상태 파일 분리.** 네트워크, DB, 애플리케이션 인프라를 하나의 상태에 몰아 넣으면 작은 변경에도 plan 이 느리고, 실수의 파급 범위(blast radius)가 커진다. 계층·환경별로 상태를 나눈다.
- **쿠버네티스와의 경계.** 클러스터·노드 그룹·VPC·DNS 같은 바깥 인프라는 Terraform 으로, 클러스터 안의 워크로드는 헬름·ArgoCD 로 관리하는 분업이 흔하다. 같은 리소스를 두 도구가 관리하면 서로의 변경을 되돌리며 싸운다.
- **온프레미스·홈랩.** 클라우드가 없어도 IaC 는 유효하다. 하이퍼바이저, DNS, 인증서 같은 것도 프로바이더가 있으면 Terraform 으로 관리할 수 있다. 베어메탈 서버 설정은 Ansible 같은 구성 관리 도구가 맡는 경우가 많다. 원칙은 같다. 손으로 고치지 말고, 코드로 고치고, 이력을 남긴다.
- **라이선스 참고.** HashiCorp 는 2023년 8월 Terraform 의 라이선스를 MPL 에서 BSL(Business Source License v1.1)로 바꿨고, 이에 대응해 Linux Foundation 산하의 포크 OpenTofu 가 만들어졌다([OpenTofu 매니페스토](https://opentofu.org/manifesto/)). 개념과 HCL 문법은 대부분 같다.

## 확인 문제

1. 선언형 IaC 가 명령형 스크립트보다 재실행에 안전한 이유는?
2. Terraform 상태 파일이 하는 일 두 가지는? Git 에 커밋하면 안 되는 이유는?
3. `plan` 에서 `~` 와 `-/+` 의 차이는? 어느 쪽이 더 위험한가?
4. 파일 안의 리소스 순서를 바꾸면 적용 순서가 바뀌는가?
5. 누군가 콘솔에서 보안 그룹 규칙을 하나 추가했다. 다음 `terraform apply` 에서 무슨 일이 일어나는가?

### 풀이

1. 최종 상태를 기술하므로 이미 그 상태면 아무것도 하지 않는다(멱등성).
2. 설정 리소스와 실제 객체 ID 의 매핑, 삭제 대상 파악, 속성 캐시. 비밀값이 평문으로 들어갈 수 있고 동시 수정 충돌이 나므로 원격 백엔드+잠금을 쓴다.
3. `~` 는 제자리 수정, `-/+` 는 삭제 후 재생성이다. `-/+` 가 더 위험하다(데이터 손실, 다운타임).
4. 바뀌지 않는다. 순서는 참조로 만든 의존성 그래프가 정한다.
5. refresh 로 drift 를 감지하고, 설정에 없는 그 규칙을 지우는 변경을 계획해 적용한다(해당 리소스를 Terraform 이 관리하는 경우).

## 더 읽을거리 (References)

- HashiCorp, [Terraform Language Documentation](https://developer.hashicorp.com/terraform/language)
- HashiCorp, [State](https://developer.hashicorp.com/terraform/language/state)
- HashiCorp, [terraform plan command](https://developer.hashicorp.com/terraform/cli/commands/plan)
- K. Morris, *Infrastructure as Code*, 2nd ed., O'Reilly, 2020.
