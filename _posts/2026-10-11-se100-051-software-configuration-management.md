---
layout: post
title: "[SE100 #051] 형상 관리(SCM)의 개념"
date: 2026-10-11 17:03:34 +0900
categories: [software-engineering]
tags: [se100, delivery, configuration-management, version-control, baseline]
---

소프트웨어 공학 100 주제 시리즈의 51번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

형상 관리(Software Configuration Management, SCM)는 "지금 운영 중인 것이 정확히 무엇으로 이루어져 있는가" 와 "그것이 언제, 왜, 누구 승인으로 바뀌었는가" 에 언제든 답할 수 있게 만드는 규율이다. Git 은 그 일부를 담당하는 도구일 뿐이다.

## 왜 필요한가

Git 사용법은 [Git 기초]({% post_url 2026-10-10-cs300-194-git-basics %})에서 다뤘다. 그런데 Git 을 잘 쓰는 팀도 다음 질문 앞에서는 자주 막힌다.

- 어제 밤 장애가 난 운영 환경에 떠 있던 바이너리는 어느 커밋에서, 어떤 컴파일러와 어떤 의존성 버전으로 만들어졌는가?
- 고객사 A 에 납품한 2.3 버전과 고객사 B 의 2.3-hotfix 는 정확히 무엇이 다른가?
- 누군가 운영 DB 의 설정 값을 바꿨다. 그 변경은 승인을 거쳤는가? 기록은 있는가?

소스 코드만 버전 관리하고 빌드 스크립트·설정·인프라·문서는 관리하지 않으면, 이 질문들에 "아마도" 로밖에 답하지 못한다. SCM 은 이 "아마도" 를 없애는 공학 활동이다. 감사(audit)를 받는 규제 산업에서는 이 기록이 그대로 증빙 자료가 되고, 장애 대응에서는 "무엇이 바뀌었나" 라는 첫 질문에 대한 답이 된다.

## 핵심 개념

### 정의와 표준

IEEE 의 형상 관리 표준은 [IEEE 828-2012 *Standard for Configuration Management in Systems and Software Engineering*](https://standards.ieee.org/ieee/828/5367/)이다. 표준 소개문에 따르면 이 개정판은 이전 판(828-2005)이 "SCM 계획서의 내용" 만 정의하던 것에서 확장되어, **형상 항목의 식별과 획득, 변경 통제, 형상 항목 상태 보고, 그리고 소프트웨어 빌드와 릴리스 엔지니어링**까지 CM 활동으로 설명한다. 또 어떤 CM 활동을, 생명주기의 언제, 어떤 계획과 자원으로 할지를 다룬다고 밝힌다. (IEEE SA 페이지 기준 828-2012 는 현재 "Inactive-Reserved" 상태이고 후속 P828 프로젝트가 진행 중이다.)

[SWEBOK Guide V4.0](https://www.computer.org/education/bodies-of-knowledge/software-engineering)(IEEE Computer Society, 2024)도 18개 지식 영역 중 8장을 "Software Configuration Management" 에 할애한다. 학술적으로는 Bersoff 의 [Elements of Software Configuration Management](https://doi.org/10.1109/TSE.1984.5010202)(IEEE TSE, 1984)가 고전으로 꼽히며, 여기서 정리된 **식별·통제·상태 기록·감사** 네 기능이 오늘날까지 교과서의 뼈대다.

### 네 가지 기본 활동

| 활동 | 묻는 질문 | 오늘날의 구현 예 |
|---|---|---|
| 형상 식별(identification) | 관리 대상은 무엇이고 어떻게 이름 붙이는가? | 저장소 구조, 버전 번호, 태그, 이미지 다이제스트 |
| 형상 통제(control) | 변경은 누가 어떤 절차로 승인하는가? | PR 리뷰, 보호 브랜치, 변경 요청(CR), CAB |
| 상태 기록(status accounting) | 지금 어떤 상태이고 무엇이 바뀌었나? | 커밋 이력, 릴리스 노트, 배포 기록, 이슈 링크 |
| 형상 감사(audit) | 기록과 실물이 일치하는가? | 산출물 해시 대조, SBOM, 드리프트 탐지 |

네 활동은 서로 맞물린다. 식별이 없으면 통제할 대상을 특정할 수 없고, 통제가 없으면 기록이 의미 없으며, 감사가 없으면 기록이 실물과 어긋나도 모른다.

### 형상 항목과 베이스라인

**형상 항목(Configuration Item, CI)** 은 형상 관리의 단위로 지정된 산출물이다. 소스 파일만이 아니라 요구사항 명세, 설계 문서, 빌드 스크립트, 컴파일러 버전, 설정 파일, 테스트 데이터, 인프라 정의, 납품 문서까지 될 수 있다. 무엇을 CI 로 지정할지는 프로젝트가 정한다. 기준은 "이것이 바뀌면 결과물이 달라지는가, 그리고 나중에 그 차이를 설명해야 하는가" 다.

**베이스라인(baseline)** 은 공식 검토를 거쳐 합의된 CI 들의 특정 시점 스냅숏이다. 이후 변경은 정해진 통제 절차를 통해서만 들어간다.

```
요구사항 베이스라인 ──▶ 설계 베이스라인 ──▶ 제품(릴리스) 베이스라인
      │                    │                       │
   SRS v1.0            아키텍처 문서 v1.2        태그 v2.3.0
                                                + 빌드 산출물 해시
                                                + 배포 매니페스트
```

Git 의 태그는 "소스 트리의 스냅숏" 을 식별할 뿐이다. 릴리스 베이스라인은 여기에 빌드 환경, 의존성 잠금 파일, 산출물 해시, 배포 설정까지 묶어야 완성된다. 이 차이를 메우는 기술이 재현 가능한 빌드(SE100 #053 에서 다룬다)다.

### 버전 모델: 버전과 변형

Conradi 와 Westfechtel 의 서베이 [Version models for software configuration management](https://doi.org/10.1145/280277.280280)(ACM Computing Surveys, 1998)는 SCM 의 버전 개념을 두 축으로 나눈다.

- **개정(revision)**: 시간 축의 버전. v1 → v2 → v3 처럼 이전 것을 대체한다.
- **변형(variant)**: 공간 축의 버전. 같은 시점에 공존한다. 예: Windows 판과 Linux 판, 고객사별 커스터마이징, 무료판과 기업판.

변형을 브랜치로 관리하면 브랜치 수가 곱셈으로 늘고 같은 수정을 여러 곳에 반복 적용해야 한다. 현대 실무가 변형을 가급적 **빌드 설정이나 피처 플래그**(SE100 #057 에서 다룬다)로 처리하고, 브랜치는 시간 축(릴리스 유지보수)에만 쓰려는 이유다.

### 버전 관리 도구의 세대

[Pro Git 의 About Version Control](https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control) 장은 도구를 세 단계로 설명한다.

| 세대 | 구조 | 예 | 약점 |
|---|---|---|---|
| 로컬 | 한 컴퓨터 안의 버전 DB | RCS | 협업 불가 |
| 중앙집중식 | 단일 서버에 이력 | CVS, Subversion, Perforce | 서버가 단일 실패 지점 |
| 분산 | 모든 클론이 전체 이력 보유 | Git, Mercurial | 대용량 바이너리·거대 저장소에 약함 |

Estublier 의 [Software configuration management: a roadmap](https://doi.org/10.1145/336512.336576)(ICSE Future of SE, 2000)은 SCM 이 단순한 버전 저장을 넘어 프로세스 지원, 작업 공간 관리, 분산 협업으로 확장되어 온 흐름을 정리한다. 오늘날 "SCM 도구" 라고 하면 Git 저장소 호스팅에 리뷰, CI, 보호 규칙, 릴리스 관리, 아티팩트 저장소가 결합된 플랫폼 전체를 가리키는 경우가 많다.

## 실무 적용

### 무엇을 형상 항목으로 지정할까 — 체크리스트

```
[ ] 애플리케이션 소스 (당연)
[ ] 빌드 정의: Gradle/Maven/package.json, Dockerfile, CI 워크플로
[ ] 의존성 잠금 파일: gradle.lockfile, package-lock.json, poetry.lock
[ ] 툴체인 버전: .java-version, .nvmrc, rust-toolchain.toml
[ ] 런타임 설정: 환경별 설정 파일 (비밀 값은 제외, 참조만)
[ ] 인프라 정의: Terraform, Kubernetes 매니페스트, Helm values
[ ] DB 스키마 마이그레이션 스크립트
[ ] 릴리스 노트, 운영 런북
[ ] 빌드 산출물: 저장소에 넣지 않고 아티팩트 저장소에 불변(immutable)으로, 커밋 해시와 연결
```

비밀(secret)은 형상 항목이지만 저장소에 평문으로 두지 않는다. "어떤 비밀이 어느 버전으로 어디에 주입되는가" 라는 **참조**를 형상 관리하고, 값은 비밀 저장소가 관리한다.

### 변경 통제를 코드로

과거의 형상 통제위원회(CCB)가 하던 일 상당 부분은 오늘날 저장소 규칙으로 자동화된다.

```yaml
# 예: 보호 브랜치 정책을 문서화한 형태 (도구 중립적 의사 설정)
branch: main
rules:
  require_pull_request: true
  required_approvals: 1
  require_code_owner_review: true      # 경로별 책임자 승인
  required_status_checks: [build, test, sbom]
  forbid_force_push: true
  require_linear_history: true          # 상태 기록을 읽기 쉽게
```

여기서 중요한 것은 규칙의 개수가 아니라 **우회 경로가 없는가**다. 운영 서버에 SSH 로 들어가 설정을 고칠 수 있다면, 저장소 규칙이 아무리 엄격해도 형상 통제는 뚫려 있다.

### 상태 기록과 감사의 최소 구현

```bash
# 배포 시점에 "무엇이 나갔는가" 를 한 줄로 남긴다
echo "$(date -u +%FT%TZ) service=order version=v2.3.0 \
commit=$(git rev-parse HEAD) image=registry/order@${DIGEST} \
approver=${APPROVER}" >> deploy-ledger.log

# 감사: 운영에 떠 있는 이미지 다이제스트가 기록과 같은가
kubectl get deploy order -o jsonpath='{.spec.template.spec.containers[0].image}'
```

태그(`:v2.3.0`)는 다시 가리키는 대상이 바뀔 수 있으므로, 감사 기준은 내용 해시인 **다이제스트**로 잡는다.

## 흔한 오해와 함정

- **"Git 을 쓰니까 형상 관리를 한다."** Git 은 식별과 기록의 일부를 준다. 무엇을 CI 로 삼을지, 누가 승인하는지, 실물과 기록이 맞는지 확인하는 일은 Git 이 대신하지 않는다.
- **소스만 관리하고 환경은 방치.** 같은 커밋이라도 컴파일러, 기반 이미지, 의존성 버전이 다르면 다른 제품이다. 툴체인과 잠금 파일도 CI 다.
- **변형을 브랜치로 관리.** 고객사별 장기 브랜치는 수정 사항 이식 비용을 곱셈으로 키운다.
- **변경 통제 = 느린 승인 회의.** 통제의 목적은 추적 가능성과 위험 관리이지 대기 시간이 아니다. 자동 검사와 작은 변경으로 통제를 빠르게 만드는 것이 현대적 해법이다.
- **감사는 연례 행사.** 드리프트 탐지, 다이제스트 대조처럼 매 배포마다 자동으로 도는 감사가 실제로 사고를 막는다.

## 확인 문제

1. 형상 관리의 네 가지 기본 활동을 들고, 각각이 답하는 질문을 한 문장으로 써라.
2. Git 태그 `v2.3.0` 만으로 릴리스 베이스라인이 완성되지 않는 이유는?
3. 개정(revision)과 변형(variant)의 차이를 예와 함께 설명하라. 변형을 장기 브랜치로 관리하면 어떤 비용이 생기는가?
4. 저장소에는 엄격한 보호 브랜치 규칙이 있지만 운영 서버에 SSH 접근이 열려 있다. 형상 관리 관점에서 무엇이 문제인가?
5. 감사 기준으로 이미지 태그 대신 다이제스트를 쓰는 이유는?

### 풀이

1. 식별: 무엇을 관리 대상으로 삼고 어떻게 이름 붙이는가. 통제: 변경을 누가 어떤 절차로 승인하는가. 상태 기록: 지금 무엇이 어떤 상태이고 무엇이 바뀌었는가. 감사: 기록과 실물이 일치하는가.
2. 태그는 소스 트리 스냅숏만 식별한다. 같은 소스라도 툴체인, 의존성 해석 결과, 빌드 설정, 배포 설정이 다르면 결과물이 달라진다. 베이스라인은 이것들과 산출물 해시까지 묶어야 한다.
3. 개정은 시간 축 버전(v1 다음 v2), 변형은 동시에 공존하는 버전(OS별 판, 고객사별 판). 변형을 장기 브랜치로 두면 공통 수정을 모든 브랜치에 반복 이식해야 하고, 브랜치 간 차이가 계속 벌어져 병합 비용이 커진다.
4. 통제 절차를 거치지 않는 변경 경로가 존재한다. 기록에 남지 않은 변경이 생기고, 기록과 실물이 어긋나(드리프트) 감사가 무력화된다.
5. 태그는 가변 참조라 같은 이름이 다른 이미지를 가리키도록 바뀔 수 있다. 다이제스트는 내용의 해시라 내용이 같을 때만 같다.

## 더 읽을거리 (References)

- IEEE, [IEEE 828-2012 Standard for Configuration Management in Systems and Software Engineering](https://standards.ieee.org/ieee/828/5367/)
- IEEE Computer Society, [Guide to the Software Engineering Body of Knowledge (SWEBOK) V4.0](https://www.computer.org/education/bodies-of-knowledge/software-engineering), 2024 — 8장 Software Configuration Management
- Edward H. Bersoff, [Elements of Software Configuration Management](https://doi.org/10.1109/TSE.1984.5010202), IEEE Transactions on Software Engineering, 1984
- Reidar Conradi, Bernhard Westfechtel, [Version models for software configuration management](https://doi.org/10.1145/280277.280280), ACM Computing Surveys, 1998
- Jacky Estublier, [Software configuration management: a roadmap](https://doi.org/10.1145/336512.336576), ICSE Future of Software Engineering, 2000
- Scott Chacon, Ben Straub, [Pro Git — About Version Control](https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control)
- CS300: [Git 기초]({% post_url 2026-10-10-cs300-194-git-basics %})
