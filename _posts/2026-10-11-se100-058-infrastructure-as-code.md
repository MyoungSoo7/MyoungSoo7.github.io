---
layout: post
title: "[SE100 #058] Infrastructure as Code"
date: 2026-10-11 17:03:41 +0900
categories: [software-engineering]
tags: [se100, delivery, infrastructure-as-code, immutable-infrastructure, configuration-drift]
---

소프트웨어 공학 100 주제 시리즈의 58번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

Infrastructure as Code(IaC)는 서버·네트워크·클러스터 같은 인프라를 **소스 코드로 정의하고, 그 코드를 일반 소프트웨어와 똑같이** 버전 관리·리뷰·테스트·지속적 전달의 대상으로 다루는 접근이다. 핵심은 도구가 아니라 "사람이 서버에 로그인해 손으로 고치지 않는다" 는 규율이다.

## 왜 필요한가

Terraform 의 선언·상태·계획·드리프트 같은 기본기는 [Infrastructure as Code — Terraform]({% post_url 2026-10-10-cs300-231-infrastructure-as-code-terraform %})에서, Git 을 원하는 상태의 원천으로 삼는 운영은 [GitOps 와 ArgoCD]({% post_url 2026-10-10-cs300-230-gitops-and-argocd %})에서 다뤘다. 이 글은 도구 아래의 원칙, 즉 왜 인프라를 코드로 다뤄야 하는지와 그때 지켜야 할 공학적 실천에 집중한다.

손으로 관리한 서버는 시간이 지날수록 각자 다른 상태가 된다. 누군가 급하게 커널 파라미터를 바꾸고, 다른 누군가 패키지를 하나 더 설치하고, 그 기록은 아무 데도 없다. 이 서버가 죽으면 똑같이 다시 만들 수 없다. 형상 관리(SE100 #051 에서 다룬다)의 관점에서 보면 이것은 **식별도 통제도 기록도 되지 않는 형상 항목**이다.

## 핵심 개념

### 정의와 실천

Martin Fowler 의 [InfrastructureAsCode](https://martinfowler.com/bliki/InfrastructureAsCode.html)(2016)는 IaC 를 "컴퓨팅과 네트워크 인프라를 소스 코드로 정의하고, 그것을 다른 소프트웨어 시스템과 똑같이 다루는 접근" 으로 정의한다. 그 코드는 소스 관리에 두어 감사 가능성과 재현 가능한 빌드를 얻고, 테스트 실천과 지속적 전달의 규율 전체를 적용받는다. Fowler 는 이 분야의 핵심 문헌으로 Kief Morris 의 책 *Infrastructure as Code*(O'Reilly)를 꼽는다. 글이 정리한 실천은 다음과 같다.

| 실천 | 내용 |
|---|---|
| 정의 파일 사용 | 모든 설정은 실행 가능한 정의 파일(셸 스크립트, Ansible 플레이북, Chef 레시피, Puppet 매니페스트 등)로. **누구도 서버에 로그인해 즉석에서 고치지 않는다** |
| 자기 문서화 | 사람이 읽고 수행하는 문서 대신, 더 정확하고 일관되게 실행되는 코드 |
| 모든 것을 버전 관리 | 모든 설정과 변경이 감사용으로 기록됨 |
| 지속적 테스트 | 인프라 코드에도 배포 파이프라인을 두고 지속적 전달 |
| 큰 묶음 대신 작은 변경 | 변경이 클수록 오류가 많고 찾기 어렵다 |
| 서비스의 지속적 가용성 | 블루그린, 병행 변경 같은 기법으로 무중단 갱신 |

### 눈송이, 불사조, 불변 서버

IaC 의 동기는 Fowler 의 bliki 세 편으로 잘 설명된다.

**[SnowflakeServer](https://martinfowler.com/bliki/SnowflakeServer.html)(2012)**: 오랫동안 손으로 조금씩 고쳐 온 서버는 세상에 하나뿐인 눈송이가 된다. 스키장에는 좋지만 데이터센터에는 나쁘다. 재현하기 어렵고, 디스크 이미지를 떠 두어도 그 안의 어떤 설정이 중요한지 모른다.

**[PhoenixServer](https://martinfowler.com/bliki/PhoenixServer.html)(2012)**: 처방은 서버를 정기적으로 **가상으로 불태우는** 것이다. 서버는 재에서 다시 태어나는 불사조처럼, 정의 코드로부터 언제든 새로 만들 수 있어야 한다. 주된 이점은 설정 드리프트(configuration drift)를 막는 것이다.

**[ImmutableServer](https://martinfowler.com/bliki/ImmutableServer.html)(Kief Morris, 2013)**: 불사조를 끝까지 밀면, 한 번 배포된 서버는 **절대 수정하지 않고** 새 인스턴스로 교체만 하는 불변 서버가 된다.

```
가변 인프라(mutable)                    불변 인프라(immutable)
┌────────┐ 패치  ┌────────┐ 설정변경    ┌────────┐   교체   ┌────────┐
│ srv v1 │ ────▶ │ srv v1'│ ────▶ ...   │ img v1 │ ──────▶ │ img v2 │
└────────┘       └────────┘             └────────┘          └────────┘
 상태 = 초기 + 모든 변경 이력의 합          상태 = 이미지 정의 그 자체
 → 드리프트 누적                         → 드리프트 원천 차단, 롤백 = 이전 이미지
```

컨테이너 이미지와 Kubernetes 파드 교체가 일상이 된 오늘날, 불변 인프라는 애플리케이션 계층에서는 사실상 기본값이다. 하지만 VM, 네트워크 장비, 관리형 DB 설정처럼 여전히 가변으로 다루는 계층이 남아 있고, IaC 의 전장은 주로 그쪽이다.

### 명령형과 선언형, 그리고 그 사이

Kubernetes [Object Management](https://kubernetes.io/docs/concepts/overview/working-with-objects/object-management/) 문서는 객체를 관리하는 세 가지 기법을 비교한다. IaC 전반에도 그대로 적용되는 구분이다.

| 기법 | 예 | 특징 |
|---|---|---|
| 명령형 커맨드 | `kubectl create deployment ...` | 빠르지만 기록이 남지 않음 |
| 명령형 객체 설정 | `kubectl create -f app.yaml`, `kubectl replace -f` | 파일을 Git 에 둘 수 있음. 동작이 단순 |
| 선언형 객체 설정 | `kubectl apply -f dir/` | 원하는 상태를 선언, 도구가 차이를 계산. 디렉터리 단위로 동작 |

문서는 선언형 객체 설정의 장점으로, 설정 파일에 반영되지 않은 운영 객체의 직접 변경도 유지된다는 점을 든다. 거꾸로 말하면 그 직접 변경은 **코드에 없는 상태**로 남는다는 뜻이고, 이것이 드리프트다. 그래서 IaC 운영은 "누가 손으로 바꾼 것" 을 탐지하고 되돌리는 장치(정기 plan, GitOps 의 자동 동기화)를 함께 둔다.

### 도구 생태계와 라이선스 변화

| 계층 | 대표 도구 |
|---|---|
| 프로비저닝(클라우드 리소스 생성) | Terraform, OpenTofu, Pulumi, CloudFormation |
| 구성 관리(서버 내부 설정) | Ansible, Chef, Puppet, Salt |
| 이미지 굽기 | Packer, Dockerfile |
| 클러스터 내부 상태 | Kubernetes 매니페스트, Helm, Kustomize, Argo CD |

2023년의 변화도 알아 둘 만하다. [OpenTofu 선언문](https://opentofu.org/manifesto/)에 따르면 Terraform 은 2014년 MPL 2.0 으로 공개되었는데, 2023년 8월 10일 HashiCorp 가 라이선스를 오픈소스가 아닌 Business Source License(BUSL) 1.1 로 바꾸었다. 이에 반발한 커뮤니티가 마지막 MPL 버전을 포크해 Linux Foundation 산하의 [OpenTofu](https://opentofu.org/docs/)로 이어 가고 있다. 도구 선택이 형상 관리의 일부라는 점, 그리고 핵심 인프라 도구의 라이선스도 의존성 위험이라는 점을 보여 준 사건이다.

## 실무 적용

### IaC 파이프라인의 단계

```
PR 생성
  ├─ fmt / validate              문법·형식
  ├─ lint (tflint 등)             흔한 실수
  ├─ 정책 검사 (OPA/Conftest 등)   "퍼블릭 버킷 금지", "태그 필수"
  ├─ 보안 스캔                     취약 설정 탐지
  └─ plan → PR 코멘트로 게시        사람이 "무엇이 바뀌는가" 를 리뷰
머지
  └─ apply (저장된 plan 그대로)     리뷰한 plan 과 적용 내용 일치 보장
정기 실행
  └─ plan (드리프트 탐지)           변경 사항이 있으면 경보
```

리뷰 대상은 코드 diff 보다 **plan 출력**이다. 코드 한 줄 변경이 리소스 교체(삭제 후 재생성)를 일으킬 수 있고, 그것은 plan 에서만 보인다. [Terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan)은 계획을 파일로 저장해 나중에 그대로 적용하는 방식을 지원한다.

### 정책을 코드로 (Rego 예)

```rego
# OPA 1.0 (Rego v1) 문법
package terraform.s3

# 퍼블릭 읽기 ACL 을 가진 S3 버킷 생성을 거부한다
deny contains msg if {
  rc := input.resource_changes[_]
  rc.type == "aws_s3_bucket_acl"
  rc.change.after.acl == "public-read"
  msg := sprintf("%s: public-read ACL 금지", [rc.address])
}
```

### 원칙 체크리스트

```
[ ] 운영 환경에 사람이 쓰기 권한으로 접근하는 경로가 "비상용" 으로만 존재하고, 사용 시 기록·사후 코드 반영이 강제되는가
[ ] 상태 파일은 원격 저장 + 잠금 + 암호화, 비밀 값은 상태에 남지 않게
[ ] 환경(dev/stg/prod)은 같은 모듈 + 다른 변수, 복사-붙여넣기 금지
[ ] 모듈과 공급자(provider) 버전을 잠금 파일로 고정
[ ] 파괴적 변경(replace/destroy)은 plan 단계에서 별도 승인
[ ] 드리프트 탐지가 정기적으로 돈다
[ ] 전체 환경을 코드로부터 새로 만드는 연습을 해 본 적이 있다
```

마지막 항목이 가장 중요한 시험이다. 한 번도 처음부터 다시 만들어 본 적이 없는 인프라는, 코드가 있어도 여전히 눈송이일 수 있다.

## 흔한 오해와 함정

- **"Terraform 파일이 있으면 IaC."** 콘솔에서 손으로 바꾸는 일이 계속되면 코드는 현실과 갈라진 문서일 뿐이다.
- **"선언형이면 멱등하고 안전하다."** 선언형 도구도 리소스 교체, 순서 의존, 외부 API 의 최종 일관성 때문에 실패하거나 예상 밖 동작을 한다. plan 리뷰가 필요한 이유다.
- **거대한 단일 상태.** 모든 인프라를 하나의 상태로 관리하면 plan 이 느려지고, 한 실수의 폭발 반경이 전체가 된다. 수명 주기와 소유 팀 기준으로 나눈다.
- **비밀을 코드에.** 저장소에 들어간 비밀은 이력에서 지우기 어렵다. 비밀 저장소 참조만 코드에 둔다.
- **테스트 없는 인프라 코드.** 정적 검사, 정책 검사, 임시 환경에 실제로 적용해 보는 통합 테스트까지, 애플리케이션 코드와 같은 수준의 검증이 필요하다.

## 확인 문제

1. Fowler 가 정리한 IaC 실천 중 "정의 파일 사용" 이 금지하는 행동은 무엇이고, 왜 금지하는가?
2. 눈송이 서버, 불사조 서버, 불변 서버를 각각 한 문장으로 설명하라.
3. Kubernetes 의 세 가지 객체 관리 기법 중 선언형 객체 설정의 장점이 동시에 드리프트의 원인이 되는 이유는?
4. IaC 의 PR 리뷰에서 코드 diff 보다 plan 출력이 중요한 이유는?
5. Terraform 라이선스 변경 사건이 형상 관리 관점에서 주는 교훈은?

### 풀이

1. 서버에 로그인해 즉석에서 설정을 바꾸는 것. 그런 변경은 기록되지 않아 서버를 재현할 수 없게 만들고(눈송이), 코드와 실제 상태를 갈라놓는다.
2. 눈송이: 손으로 오래 고쳐 와서 재현 불가능한 유일한 서버. 불사조: 정의 코드로부터 정기적으로 새로 만들어 드리프트를 없애는 서버. 불변 서버: 배포 후 절대 수정하지 않고 새 인스턴스로 교체만 하는 서버.
3. 설정 파일에 반영되지 않은 운영 객체의 직접 변경이 유지되므로, 코드에 없는 상태가 운영에 남아 코드와 현실이 어긋난다.
4. 같은 코드 변경이라도 실제로 어떤 리소스가 생성·수정·교체·삭제되는지는 현재 상태와의 차이로 결정되며, 그것은 plan 에서만 보인다. 특히 교체(삭제 후 재생성)는 데이터 손실이나 장애로 이어질 수 있다.
5. 핵심 도구 자체도 형상 항목이자 외부 의존성이다. 버전을 고정하고, 라이선스와 거버넌스 변화를 의존성 위험으로 관리하며, 대체 경로를 알고 있어야 한다.

## 더 읽을거리 (References)

- Martin Fowler, [InfrastructureAsCode](https://martinfowler.com/bliki/InfrastructureAsCode.html), 2016
- Martin Fowler, [SnowflakeServer](https://martinfowler.com/bliki/SnowflakeServer.html), [PhoenixServer](https://martinfowler.com/bliki/PhoenixServer.html), 2012
- Kief Morris, [ImmutableServer](https://martinfowler.com/bliki/ImmutableServer.html), 2013
- Kief Morris, *Infrastructure as Code*, O'Reilly (서지 정보)
- Kubernetes, [Kubernetes Object Management](https://kubernetes.io/docs/concepts/overview/working-with-objects/object-management/)
- HashiCorp, [Terraform Language](https://developer.hashicorp.com/terraform/language), [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan)
- Open Policy Agent, [Policy Language (Rego)](https://www.openpolicyagent.org/docs/policy-language)
- OpenTofu, [The OpenTofu Manifesto](https://opentofu.org/manifesto/), [Documentation](https://opentofu.org/docs/)
- CS300: [Infrastructure as Code — Terraform]({% post_url 2026-10-10-cs300-231-infrastructure-as-code-terraform %}), [GitOps 와 ArgoCD]({% post_url 2026-10-10-cs300-230-gitops-and-argocd %})
