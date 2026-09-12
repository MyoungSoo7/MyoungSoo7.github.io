---
layout: post
title: "Terraform·Ansible·Helm 사용사례와 장단점: 인프라부터 Kubernetes 애플리케이션까지"
date: 2026-09-12 23:13:00 +0900
categories: [DevOps, IaC, Kubernetes]
tags: [Terraform, Ansible, Helm, Kubernetes, IaC, Automation]
---

# Terraform·Ansible·Helm 사용사례와 장단점

Terraform, Ansible, Helm은 모두 자동화 도구로 분류되지만 해결하려는 문제가 다르다.

- Terraform: 인프라 자원의 **생성·변경·삭제**
- Ansible: 서버와 노드의 **설정·배포·운영 작업**
- Helm: Kubernetes 애플리케이션의 **패키징·설치·업그레이드**

세 도구를 같은 역할로 비교하면 선택이 흔들린다. 이 글에서는 각 도구의 경계, 실제로 적용하기 좋은 사용사례, 장점과 단점, 함께 사용할 때의 책임 분리를 정리한다.

## 한눈에 비교

| 도구 | 주 대상 | 핵심 상태 | 대표 명령/개념 | 잘 맞는 문제 |
|---|---|---|---|---|
| Terraform | Cloud·On-prem·SaaS·Kubernetes 리소스 | State | `plan`, `apply`, provider, module | VPC, VM, DNS, DB, cluster 기반 인프라 |
| Ansible | Linux·Windows·network device·애플리케이션 | Managed host 상태 | inventory, playbook, module, role | OS 설정, 패키지, 보안 기준, 순차 배포 |
| Helm | Kubernetes resource manifest | Release revision | chart, values, release, upgrade, rollback | 동일 애플리케이션의 환경별 배포 |

Terraform은 cloud와 on-prem 리소스를 사람이 읽을 수 있는 설정 파일로 정의하고 provider API를 통해 관리한다.[1] Ansible playbook은 여러 머신에 반복 가능한 설정과 배포 절차를 실행하는 YAML 기반 자동화 방식이다.[4] Helm chart는 관련 Kubernetes 리소스를 하나의 패키지로 묶고 values와 template으로 배포 구성을 재사용한다.[6]

## 1. Terraform

## Terraform이 해결하는 문제

Terraform은 인프라를 코드로 정의하고 `Write → Plan → Apply` 흐름으로 변경을 검토한 뒤 적용한다.[1]

```text
Terraform configuration
        │
        ▼
terraform plan
        │  변경 예정 확인
        ▼
terraform apply
        │
        ▼
Cloud / On-prem / SaaS / Kubernetes resource
```

Terraform은 state를 사용해 설정의 resource instance와 실제 원격 객체를 연결한다.[2] 따라서 state는 단순한 캐시가 아니라 협업과 변경 계산에 영향을 주는 운영 데이터다.

## 사용사례 1: 네트워크와 Kubernetes 기반 인프라

```hcl
module "network" {
  source = "./modules/network"

  environment = "prod"
  cidr_block  = "10.0.0.0/16"
}

module "cluster" {
  source = "./modules/cluster"

  environment = "prod"
  network_id  = module.network.id
}
```

실제 구성에서는 VPC 또는 사설 네트워크, subnet, firewall/security group, load balancer, Kubernetes cluster, node pool, DNS 등을 provider와 module로 관리할 수 있다. 반복되는 개발·스테이징·운영 환경은 module과 변수로 표준화한다. HashiCorp 문서도 반복적으로 생성하는 네트워크 자원 묶음을 module로 캡슐화하면 표준화와 예측 가능한 provisioning에 도움이 된다고 설명한다.[3]

## 사용사례 2: 공통 서비스 자원

- object storage bucket
- managed database
- cache
- DNS record
- monitoring workspace
- IAM role/policy
- registry와 secret store 연결

애플리케이션이 의존하는 기반 자원을 코드 리뷰와 `terraform plan`으로 변경할 수 있다. 여러 provider를 조합하면 cloud resource와 DNS·GitHub·monitoring SaaS를 하나의 workflow로 관리할 수도 있다. 다만 provider가 지원한다고 해서 모든 운영 변경을 Terraform에 넣어야 하는 것은 아니다.

## Terraform의 장점

### 1. 변경 전 계획을 확인할 수 있음

`terraform plan`은 생성·변경·삭제 예정 자원을 보여주므로 수동 콘솔 변경보다 변경 범위를 검토하기 쉽다.[1]

### 2. 인프라를 버전 관리할 수 있음

HCL 설정을 Git으로 관리하면 누가 언제 어떤 인프라 의도를 변경했는지 추적할 수 있다.

### 3. 의존성 그래프와 병렬 처리

Terraform은 resource dependency graph를 구성해 의존하지 않는 작업을 병렬로 처리한다.[1]

### 4. module로 반복을 줄일 수 있음

팀 표준 네트워크, cluster, database 구성을 reusable module로 만들 수 있다.[3]

## Terraform의 단점과 주의점

### 1. State가 운영상 핵심 위험

로컬 state는 협업이 어렵고 state 손실 위험이 있다. remote backend와 locking, 접근 통제가 필요하다.[2] State에 민감한 값이 포함될 수 있으므로 Git 저장소에 무심코 commit해서는 안 된다.[2]

### 2. Drift와 수동 변경 충돌

콘솔에서 직접 바꾼 resource와 코드·state가 달라지면 다음 plan에 예상하지 못한 변경이 나타날 수 있다. Terraform이 관리하는 범위와 수동 운영 범위를 명확히 해야 한다.

### 3. 잘못된 apply는 큰 영향

네트워크, IAM, database, cluster 삭제 계획은 애플리케이션 배포보다 훨씬 넓은 장애 범위를 가질 수 있다. CI에서는 plan artifact 검토, 승인 단계, state lock, backup을 운영해야 한다.

### 4. 모든 운영 작업의 도구는 아님

로그 확인, 순차적인 노드 조치, 일회성 데이터 변환, 애플리케이션 내부 migration은 Terraform보다 다른 도구가 적합할 수 있다.

## 2. Ansible

## Ansible이 해결하는 문제

Ansible playbook은 반복 가능하고 재사용 가능한 configuration management와 multi-machine deployment를 제공한다.[4] inventory는 관리 대상 host와 group, 변수의 출처를 정의한다.[5]

```text
Inventory
  ├─ web
  ├─ worker
  └─ database
       │
       ▼
Playbook → Task → Module → Managed host
```

## 사용사례 1: 노드 초기화와 공통 설정

```yaml
- name: Configure worker nodes
  hosts: workers
  become: true
  tasks:
    - name: Install required packages
      ansible.builtin.package:
        name:
          - curl
          - jq
        state: present

    - name: Configure time synchronization
      ansible.builtin.service:
        name: chronyd
        state: started
        enabled: true
```

예를 들어 Kubernetes worker를 추가할 때 OS package, time synchronization, kernel parameter, container runtime, log rotation, monitoring agent, security baseline을 노드 그룹별로 적용할 수 있다.

## 사용사례 2: 애플리케이션과 운영 설정 배포

```yaml
- name: Deploy service configuration
  hosts: app
  become: true
  tasks:
    - name: Install service package
      ansible.builtin.package:
        name: my-service
        state: present

    - name: Render service configuration
      ansible.builtin.template:
        src: my-service.yml.j2
        dest: /etc/my-service/config.yml
        mode: "0640"
      notify: Restart service

  handlers:
    - name: Restart service
      ansible.builtin.service:
        name: my-service
        state: restarted
```

운영 환경별 inventory와 group variable을 분리하면 같은 playbook으로 test·staging·production의 차이를 관리할 수 있다. 단, production secret은 Vault나 secret manager와 연계하고 playbook이나 로그에 평문으로 남기지 않아야 한다.

## 사용사례 3: 장애 대응과 반복 운영 작업

- 특정 노드의 로그·디스크·서비스 상태 수집
- 여러 서버의 설정 drift 점검
- 인증서 배포와 만료 전 교체
- 운영 agent 재시작
- maintenance mode 진입과 복구
- patch window 동안의 순차 업데이트

Ansible은 task 결과와 각 host의 성공·실패·변경 여부를 반환하므로 수동 SSH 반복 작업보다 실행 결과를 남기기 쉽다.[4]

## Ansible의 장점

### 1. Agentless 운영

일반적인 SSH 기반 Linux 관리에서는 대상 host에 별도 agent를 상주시키지 않고 중앙에서 playbook을 실행할 수 있다.

### 2. 절차를 읽기 쉬움

YAML playbook, inventory, module 조합은 대상과 작업 순서를 드러낸다. Ansible 공식 문서도 playbook을 YAML로 표현하고 task가 module을 호출한다고 설명한다.[4]

### 3. 노드 단위의 세밀한 제어

특정 group, host pattern, 순차 처리, batch size, handler 등으로 운영 절차를 조절할 수 있다.

### 4. 구성 관리와 배포에 적합

OS와 middleware 설정처럼 이미 존재하는 호스트를 원하는 상태로 맞추는 작업에 강하다.

## Ansible의 단점과 주의점

### 1. 연결·권한·환경 의존성

SSH, WinRM, Python, become 권한, 네트워크 접근이 준비되지 않으면 playbook이 실행되지 않는다.

### 2. Idempotency를 직접 보장해야 함

module을 올바르게 사용하면 반복 실행에 강하지만, 무분별한 `shell`·`command` 사용은 같은 playbook을 재실행할 때 중복·부작용을 만들 수 있다.

### 3. 대규모 병렬 실행의 복잡성

수백·수천 host를 한 번에 처리하면 controller의 connection, fork, fact gathering, 로그량이 병목이 될 수 있다. batch와 serial deployment, 실패 시 중단 정책을 설계해야 한다.

### 4. 상태의 단일 진실 공급원이 약함

Terraform처럼 전체 인프라 객체와 state를 중심으로 변경을 계산하는 도구가 아니다. 여러 사람이 playbook 외부에서 변경하면 실제 구성 drift를 별도로 점검해야 한다.

### 3. Helm

## Helm이 해결하는 문제

Helm chart는 Kubernetes 리소스와 template, values, dependency를 패키지로 묶는다. chart는 단순한 pod부터 HTTP server·database·cache가 포함된 복합 stack까지 설명할 수 있다.[6]

```text
Chart
  ├─ Chart.yaml
  ├─ values.yaml
  ├─ values.schema.json
  ├─ templates/
  └─ charts/
       │
       ▼
helm install / upgrade
       │
       ▼
Kubernetes release
```

Helm은 chart를 release로 설치하고 `upgrade`, `rollback`, `status`, `get` 등으로 release lifecycle을 관리한다.[7]

## 사용사례 1: 환경별 애플리케이션 배포

```yaml
# values-prod.yaml
replicaCount: 3
image:
  repository: registry.example.com/shop
  tag: "2026.09.12"
resources:
  requests:
    cpu: 200m
    memory: 512Mi
ingress:
  enabled: true
```

```bash
helm upgrade --install shop ./charts/shop \
  --namespace shop-prod \
  --create-namespace \
  -f values-prod.yaml \
  --wait
```

같은 chart에 `values-dev.yaml`, `values-stage.yaml`, `values-prod.yaml`을 적용하면 환경별 replica, image, resource, ingress, external service endpoint를 분리할 수 있다.

## 사용사례 2: 공통 플랫폼 컴포넌트

- Prometheus와 Grafana
- Elasticsearch·Logstash·Kibana
- ingress controller
- cert-manager
- Kafka operator
- GitHub Actions Runner Controller
- database·cache operator

공식 또는 community chart를 사용하면 복잡한 Kubernetes manifest를 처음부터 작성하는 부담을 줄일 수 있다. 다만 chart version, appVersion, CRD, values schema, dependency를 반드시 고정하고 검증해야 한다.

## 사용사례 3: 배포 이력과 rollback

```bash
helm history shop -n shop-prod
helm status shop -n shop-prod
helm rollback shop 4 -n shop-prod --wait
```

Helm release revision을 이용하면 chart와 values 변경의 배포 이력을 확인하고 이전 revision으로 되돌릴 수 있다. 단, rollback 명령이 데이터베이스 schema migration이나 외부 side effect를 자동으로 되돌리는 것은 아니다.

## Helm의 장점

### 1. Kubernetes manifest 재사용

template과 values로 여러 환경의 차이를 하나의 chart 구조에 담을 수 있다.[6]

### 2. 패키지와 dependency 관리

chart를 versioned archive로 배포할 수 있고 chart dependency도 선언할 수 있다.[6]

### 3. release lifecycle 제공

설치·업그레이드·상태 확인·rollback이라는 Kubernetes 애플리케이션 lifecycle을 하나의 CLI 경험으로 제공한다.[7]

### 4. Kubernetes 생태계와 잘 맞음

운영 도구와 platform component가 chart로 배포되는 경우가 많아 도입 장벽이 낮다.

## Helm의 단점과 주의점

### 1. Template 복잡성

Go template, YAML indentation, scope, merge 규칙이 겹치면 manifest를 읽고 디버깅하기 어려워진다.

### 2. values 폭발

환경과 예외가 늘어날수록 values 파일이 거대해지고 어떤 값이 최종 적용됐는지 추적하기 어려워진다. `helm template`, `helm diff`, schema validation, rendered manifest artifact를 CI에 넣는 것이 좋다.

### 3. Helm 성공과 애플리케이션 정상은 다름

Helm command가 성공하거나 release 상태가 `deployed`라고 해서 Pod readiness, 외부 endpoint, 실제 API 기능까지 정상이라는 뜻은 아니다. Helm 문서도 install이 모든 resource가 Running이 될 때까지 기다리지 않고 종료할 수 있다고 설명한다.[7]

### 4. CRD와 데이터 변경의 위험

chart upgrade가 CRD, PVC, webhook, migration에 영향을 줄 수 있다. rollback이 모든 상태를 원상복구한다고 가정해서는 안 된다.

## 4. 세 도구를 함께 사용하는 구조

세 도구는 경쟁 관계라기보다 계층이 다르다.

```text
Terraform
  └─ network, VM, Kubernetes cluster, DNS, IAM
       │
       ▼
Ansible
  └─ node bootstrap, OS baseline, runtime, operational maintenance
       │
       ▼
Helm
  └─ Kubernetes application, operator, monitoring stack
```

예시 workflow:

1. Terraform으로 network·node·cluster·DNS 기반 자원을 생성한다.
2. Ansible로 node package, runtime, kernel과 운영 기준을 맞춘다.
3. Helm으로 ingress, monitoring, operator, application을 배포한다.
4. CI에서 각 단계의 plan·lint·render·test·smoke를 검증한다.
5. 변경 후 실제 cluster 상태와 외부 endpoint를 read-back한다.

## 책임 경계

| 작업 | 우선 도구 | 이유 |
|---|---|---|
| VPC, subnet, VM, managed DB | Terraform | API resource lifecycle과 state |
| OS package, kernel, service config | Ansible | host 단위 설정과 순차 절차 |
| Kubernetes Deployment, Service, Ingress | Helm | chart·values·release |
| Kubernetes node 생성 | Terraform 또는 cloud provider | infrastructure lifecycle |
| node 초기화 | Ansible | OS와 runtime configuration |
| 애플리케이션 rollout | Helm | Kubernetes release lifecycle |
| 일회성 장애 조사 | kubectl·로그·관측 도구 | 선언형 provisioning 도구의 역할 아님 |

## 선택 기준

### Terraform을 먼저 선택할 때

- 인프라 resource를 만들고 없애야 한다.
- cloud와 SaaS를 함께 관리한다.
- 변경 전 plan과 state 기반 협업이 중요하다.

### Ansible을 먼저 선택할 때

- 이미 존재하는 서버를 설정해야 한다.
- OS·package·service·파일을 관리한다.
- 노드별 순차 절차와 운영 작업이 중요하다.

### Helm을 먼저 선택할 때

- 대상이 Kubernetes resource다.
- 환경별 values로 같은 애플리케이션을 배포한다.
- chart release와 revision을 관리해야 한다.

## 운영 품질 체크리스트

### Terraform

- [ ] remote state와 locking
- [ ] state 접근 권한과 secret 노출 검토
- [ ] plan artifact review
- [ ] module version 고정
- [ ] destructive change 승인
- [ ] drift 점검

### Ansible

- [ ] inventory 환경 분리
- [ ] `check`/dry-run 가능한 task 설계
- [ ] `shell`·`command` 최소화
- [ ] idempotency 테스트
- [ ] serial/batch와 rollback 절차
- [ ] secret log 노출 방지

### Helm

- [ ] chart와 dependency version 고정
- [ ] `helm lint`
- [ ] `helm template` 결과 검토
- [ ] values schema 검증
- [ ] resource·probe·securityContext 명시
- [ ] rollout readiness와 실제 endpoint 검증
- [ ] CRD·PVC·migration 영향 검토

## 결론

Terraform·Ansible·Helm은 자동화라는 공통점이 있지만 소유해야 하는 상태가 다르다.

- Terraform은 **인프라 자원과 state**를 관리한다.
- Ansible은 **호스트 구성과 운영 절차**를 실행한다.
- Helm은 **Kubernetes chart와 release**를 관리한다.

가장 큰 실수는 세 도구를 섞어 같은 자원을 동시에 관리하는 것이다. 한 자원의 lifecycle owner를 정하고, Terraform이 만든 것을 Ansible이 임의로 바꾸거나 Helm release를 Terraform과 수동 manifest가 동시에 소유하지 않도록 해야 한다.

자동화 도구를 도입했다는 사실보다 중요한 것은 다음의 검증이다.

```text
계획 확인 → 변경 승인 → 실행 → 실제 상태 read-back → 서비스 영향 확인
```

`apply`, `playbook` 성공, `helm upgrade` 성공만으로 운영 성공을 선언하지 말고, resource 상태·로그·readiness·외부 endpoint·업무 기능까지 확인해야 한다.

## 참고 자료

[1] Terraform Introduction — Terraform의 provider, Write·Plan·Apply, module, state 개요  
[2] Terraform State — state의 역할, remote backend, locking과 보안 주의사항  
[3] Terraform Modules — 반복 인프라 구성을 module로 표준화하는 방법  
[4] Ansible Playbooks — playbook, task, module, multi-machine deployment  
[5] Ansible Inventory — host·group·변수와 inventory 구성  
[6] Helm Charts — chart 구조, values, templates, dependency, version  
[7] Using Helm — install, upgrade, rollback, status와 release 동작

## 출처

- Terraform Introduction: https://developer.hashicorp.com/terraform/intro
- Terraform State: https://developer.hashicorp.com/terraform/language/state
- Terraform Modules: https://developer.hashicorp.com/terraform/language/modules
- Ansible Playbooks: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html
- Ansible Inventory: https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html
- Helm Charts: https://helm.sh/docs/topics/charts/
- Using Helm: https://helm.sh/docs/intro/using_helm/

## Sources

[1] https://developer.hashicorp.com/terraform/intro — Terraform Introduction
[2] https://developer.hashicorp.com/terraform/language/state — Terraform State
[3] https://developer.hashicorp.com/terraform/language/modules — Terraform Modules
[4] https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html — Ansible Playbooks
[5] https://docs.ansible.com/ansible/latest/inventory_guide/intro_inventory.html — Ansible Inventory
[6] https://helm.sh/docs/topics/charts — Helm Charts
[7] https://helm.sh/docs/intro/using_helm — Using Helm
