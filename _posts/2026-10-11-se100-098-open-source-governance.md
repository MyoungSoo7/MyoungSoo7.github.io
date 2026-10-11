---
layout: post
title: "[SE100 #098] 오픈소스 거버넌스와 기여 프로세스"
date: 2026-10-11 17:10:48 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, open-source-governance, contribution-process, dco, maintainers]
---

소프트웨어 공학 100 주제 시리즈의 98번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

오픈소스 라이선스는 "코드를 어떻게 쓸 수 있는가" 를 정하고, 거버넌스는 "**누가 어떻게 결정하는가**" 를 정한다. 오래 살아남는 프로젝트는 결정 방식, 기여 경로, 메인테이너의 진입·이탈, 출처 증명을 문서로 갖고 있다.

## 왜 필요한가

라이선스는 [소프트웨어 라이선스와 오픈소스]({% post_url 2026-10-10-cs300-291-software-licenses-and-open-source %}) 글에서 다뤘다. 그런데 라이선스가 완벽해도 프로젝트는 다른 이유로 무너진다.

- 메인테이너 한 명이 모든 PR 을 승인한다. 그가 지치거나 떠나면 프로젝트가 멈춘다.
- 한 회사가 핵심 인력을 모두 고용하고 있다. 회사 전략이 바뀌면 로드맵이 바뀐다.
- 외부 기여자는 PR 을 올렸지만 몇 달째 답이 없다. 기준도 절차도 없어서 왜 거절됐는지도 모른다.
- 기여된 코드의 저작권 출처가 불분명해 나중에 법적 문제가 된다.

우리가 의존하는 라이브러리의 거버넌스는 곧 우리의 **공급망 위험** 이다.

## 핵심 개념

### 오픈소스의 정의부터

[Open Source Definition](https://opensource.org/osd) (OSI)은 오픈소스 라이선스의 조건 10가지(자유로운 재배포, 소스 제공, 파생 저작물 허용, 차별 금지, 기술 중립성 등)를 정한다. 이 정의는 **사용 권리** 를 보장할 뿐, 프로젝트가 누구의 의견을 듣고 무엇을 받아들일지는 말하지 않는다. 그 빈자리가 거버넌스다.

### 거버넌스 모델의 스펙트럼

| 모델 | 결정권 | 예 | 위험 |
|---|---|---|---|
| 단일 메인테이너 | 한 사람 | 많은 소규모 라이브러리 | 버스 팩터 1, 번아웃 |
| BDFL(자비로운 종신 독재자) | 창시자 최종 결정 | 2018년 이전의 Python | 승계 문제 |
| 선출 위원회 | 선출된 소수 | Python Steering Council | 선거·임기 운영 비용 |
| 능력주의 + 합의 | 기여로 권한 획득, 합의 중심 | Apache 프로젝트 | 의사결정 속도 |
| 재단 + 단계 심사 | 재단 기준 충족 시 승격 | CNCF 프로젝트 | 형식화 |
| 단일 기업 주도 | 후원 기업 | 다수 기업 오픈소스 | 기업 전략 변화에 종속 |

### Python: BDFL 에서 운영위원회로

[PEP 13 – Python Language Governance](https://peps.python.org/pep-0013/) 에 따르면 Guido van Rossum 이 2018년 7월 BDFL 에서 물러난 뒤, Python 은 2018년 12월 이 모델을 채택했다. 핵심 규정은 다음과 같다.

- 운영위원회(steering council)는 **5인** 이며, 매 기능 릴리스 후 선거를 한다.
- **한 고용주 소속은 최대 2명.** 상위 득표자 셋이 같은 회사면 가장 낮은 순위자가 탈락하고 다음 후보가 들어간다.
- 코어 팀이 후보를 추천하고 투표한다.

고용주 상한 조항이 눈여겨볼 부분이다. 특정 회사가 프로젝트를 사실상 지배하는 것을 구조로 막는다.

### Apache: 능력주의와 합의

[The Apache Way](https://www.apache.org/theapacheway/) 는 원칙을 이렇게 요약한다. 누구나 참여할 수 있지만 영향력은 **공개적으로 얻은 능력(earned authority)** 에 기반한다. 참여 단위는 조직이 아니라 개인이다. 코드와 의사결정에 관한 모든 소통은 공개된다. 재단은 엄격히 **벤더 중립** 이다. 그리고 "커뮤니티가 코드보다 우선" 이다. 건강한 커뮤니티는 코드 문제를 언제든 고칠 수 있기 때문이다.

결정 방식은 [Voting](https://www.apache.org/foundation/voting.html) 문서에 구체적으로 적혀 있다.

| 투표 대상 | 규칙 |
|---|---|
| 코드 변경 | +1 세 표 필요(게으른 합의 적용 시 예외). 자격 있는 투표자의 -1 은 **거부권** 이며, 반드시 **기술적 근거** 를 함께 제시해야 한다. 근거 없는 거부권은 효력이 없다 |
| 절차 문제 | 단순 다수 |
| 패키지 릴리스 | PMC 위원 최소 3명 찬성, 구속력 있는 찬성이 반대보다 많아야 함. **릴리스는 거부권 대상이 아니다** |

**게으른 합의(lazy consensus)** 는 "며칠 안에 이의가 없으면 진행한다" 는 방식으로, 반대 없는 일상 결정을 빠르게 처리한다.

### CNCF: 성숙도 단계와 졸업 조건

CNCF 는 프로젝트를 [Sandbox, Incubating, Graduated, Archived](https://contribute.cncf.io/projects/lifecycle/) 로 구분한다. [졸업 신청 템플릿](https://github.com/cncf/toc/blob/main/.github/ISSUE_TEMPLATE/template-graduation-application.md)의 거버넌스 항목은 실무 체크리스트로 쓸 만하다.

- 명확하고 찾기 쉬운 거버넌스 문서, 실제 활동과 일치할 것
- 프로젝트 방향의 **벤더 중립성** 명시
- 리더십 역할, 기여 수용, 거버넌스 변경의 결정 방식 문서화
- 메인테이너 생애주기(역할, 온보딩, 오프보딩, 명예 메인테이너) 문서화와 실제 사용 사례
- **최소 2개 조직** 의 메인테이너 (생존성)
- 단일 조직이 거버넌스 결정을 지배하지 못하게 하는 조직 균형 장치
- 행동 강령 채택, [OpenSSF Best Practices](https://www.bestpractices.dev/) passing 배지(필수)

### 기여의 법적 경로: DCO 와 CLA

기여된 코드에 대한 권리를 확인하는 방법은 두 가지다.

- **CLA(Contributor License Agreement)**: 기여자가 프로젝트(또는 재단·회사)와 별도 계약을 맺는다. 서명 절차가 필요하다.
- **DCO(Developer Certificate of Origin)**: [DCO 1.1](https://developercertificate.org/) 은 기여자가 커밋마다 (a) 직접 작성했고 해당 오픈소스 라이선스로 제출할 권리가 있거나, (b) 적절한 오픈소스 라이선스의 기존 작업에 기반하거나, (c) 그런 인증을 한 다른 사람에게서 받았고 수정하지 않았으며, (d) 기여와 서명 기록이 공개·보존됨을 이해한다고 **인증** 하는 문서다.

Linux 커널의 [Submitting patches](https://docs.kernel.org/process/submitting-patches.html) 문서가 DCO 의 대표 사용처다. 패치 설명 끝에 `Signed-off-by:` 줄을 달고(`git commit -s`), 익명 기여는 받지 않으며, 서명 체인은 패치가 메인테이너를 거쳐 간 **실제 경로** 를 반영해야 한다. 

### 메인테이너 신뢰가 공급망이다: xz 사건

2024년 3월 공개된 [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094) 는 xz 의 업스트림 tarball 5.6.0 부터 악성 코드가 들어 있던 사건이다. Andres Freund 는 [oss-security 메일링 리스트](https://www.openwall.com/lists/oss-security/2024/03/29/4)에 sshd 의 이상한 지연과 valgrind 오류를 추적하다 백도어를 발견했다고 보고했다. 원 메인테이너 Lasse Collin 의 [사건 페이지](https://tukaani.org/xz-backdoor/)에 따르면 백도어가 든 5.6.0, 5.6.1 릴리스 tarball 은 공동 메인테이너 계정 "Jia Tan" 이 만들고 서명한 것이었다.

거버넌스 관점의 교훈은 기술보다 사람 쪽에 있다. 널리 쓰이는 핵심 라이브러리에서 **누가 릴리스 권한을 얻는가**, 그 권한 부여가 검증되는가, 릴리스 산출물이 저장소의 소스와 같은지 확인하는가. 공급망 보안 일반은 [소프트웨어 공급망 보안]({% post_url 2026-10-10-cs300-257-software-supply-chain-security %}) 글에서 다뤘다.

## 실무 적용

### 저장소에 둘 거버넌스 파일

GitHub 은 이런 파일을 [커뮤니티 건강 파일](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)로 인식한다.

```
.
├── LICENSE              # 사용 권리 (SPDX 식별자와 일치)
├── README.md
├── CONTRIBUTING.md      # 기여 절차, 개발 환경, 커밋 규칙, DCO/CLA
├── CODE_OF_CONDUCT.md   # 예: Contributor Covenant
├── GOVERNANCE.md        # 역할, 결정 방식, 메인테이너 진입/이탈
├── MAINTAINERS.md       # 이름, 연락처, 담당 영역, 소속
├── SECURITY.md          # 취약점 비공개 보고 경로
└── .github/
    └── CODEOWNERS       # 경로별 필수 리뷰어
```

[CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) 는 경로별 소유자를 지정해 PR 에 리뷰를 자동 요청한다. 브랜치 보호와 결합하면 소유자 승인 없이는 병합되지 않는다. 문서상의 거버넌스와 실제 권한이 일치하게 만드는 장치다.

```
# .github/CODEOWNERS
*                   @org/core-maintainers
/docs/              @org/docs-team
/crypto/            @alice @bob          # 보안 민감 영역은 두 명
/.github/workflows/ @org/release-team    # CI 변경은 릴리스 팀 승인
```

### GOVERNANCE.md 최소 골격

```markdown
## 역할
- Contributor: PR 을 올린 누구나
- Reviewer: 특정 영역 리뷰 권한. 6개월간 의미 있는 리뷰 10건 이상 + 메인테이너 추천
- Maintainer: 병합·릴리스 권한. 메인테이너 2/3 찬성으로 임명
- Emeritus: 1년 활동 없으면 전환 (권한 없음)

## 결정
- 일상 변경: 메인테이너 1인 승인 + 72시간 게으른 합의
- 호환성 깨는 변경: 메인테이너 과반 + RFC 문서
- 거버넌스 변경: 메인테이너 2/3

## 조직 균형
- 한 조직 소속 메인테이너는 투표권의 절반을 넘지 않는다

## 릴리스
- 서명된 태그, CI 에서 재현 가능한 빌드로만 산출물 생성
```

숫자는 예시다. 핵심은 문서와 실제 운영의 일치다.

### 의존성의 거버넌스 점검

[OpenSSF Scorecard](https://scorecard.dev/) 는 저장소의 보안 관행을 자동 점검한다. 점검 항목에는 Branch-Protection, Code-Review, Contributors(여러 조직의 기여자), Maintained, Security-Policy, Signed-Releases, Dangerous-Workflow, Token-Permissions 등이 있다. 핵심 의존성에 돌려 보고, 점수보다 **어느 항목이 비었는지** 를 본다.

## 흔한 오해와 함정

- **"오픈소스니까 누구나 고칠 수 있으니 안전하다."** 고칠 수 있는 것과 고치는 사람이 있는 것은 다르다. 메인테이너 수와 소속 다양성을 본다.
- **"라이선스가 거버넌스다."** OSD 는 사용 권리만 보장한다. 결정 구조는 별도 문서가 필요하다.
- **거부권을 근거 없이 쓴다.** Apache 규칙처럼 거부권에는 기술적 근거가 필요하다는 원칙이 없으면 한 사람이 프로젝트를 멈출 수 있다.
- **메인테이너 이탈 절차가 없다.** 활동 없는 계정의 권한은 공격 표면이다. 명예 전환을 제도화한다.
- **릴리스 산출물을 검증하지 않는다.** xz 사건의 백도어는 릴리스 tarball 에 있었다. 저장소 소스와 배포 산출물이 같은지, 누가 서명했는지를 확인한다.

## 확인 문제

1. OSD 가 보장하는 것과 거버넌스가 다루는 것의 차이를 설명하라.
2. PEP 13 에서 특정 기업의 지배를 막는 조항은 무엇인가?
3. Apache 의 코드 변경 투표에서 -1 의 의미와 조건은? 릴리스 투표와는 어떻게 다른가?
4. DCO 와 CLA 의 차이를 기여자 입장에서 설명하라.
5. CNCF 졸업 조건 중 "최소 2개 조직의 메인테이너" 가 요구되는 이유는?

### 풀이

1. OSD 는 라이선스가 재배포·소스 제공·파생 허용·차별 금지 등 사용 권리를 보장하는지를 정한다. 거버넌스는 누가 어떤 절차로 기여를 받아들이고 방향을 결정하며 권한을 얻고 잃는지를 정한다.
2. 운영위원회 5인 중 한 고용주 소속은 최대 2명이라는 조항.
3. 자격 있는 투표자의 -1 은 거부권이며 기술적 근거를 함께 제시해야 효력이 있다. 릴리스 투표는 PMC 3인 이상 찬성과 찬성 우위의 다수결이며 거부권 대상이 아니다.
4. DCO 는 커밋마다 Signed-off-by 줄로 권리를 인증하는 가벼운 방식이고 별도 계약이 없다. CLA 는 프로젝트 측과 별도 계약에 서명해야 한다.
5. 한 조직이 철수하거나 전략을 바꿔도 프로젝트가 살아남을 수 있는지(생존성)를 보기 위해서다. 단일 조직 의존은 벤더 중립성과 지속성을 해친다.

## 더 읽을거리 (References)

- Open Source Initiative, [The Open Source Definition](https://opensource.org/osd)
- Apache Software Foundation, [The Apache Way](https://www.apache.org/theapacheway/) / [Voting](https://www.apache.org/foundation/voting.html)
- [PEP 13 – Python Language Governance](https://peps.python.org/pep-0013/)
- CNCF, [Project lifecycle](https://contribute.cncf.io/projects/lifecycle/) / [Graduation application template](https://github.com/cncf/toc/blob/main/.github/ISSUE_TEMPLATE/template-graduation-application.md)
- [Developer Certificate of Origin 1.1](https://developercertificate.org/)
- Linux kernel, [Submitting patches](https://docs.kernel.org/process/submitting-patches.html)
- GitHub Docs, [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Contributor Covenant](https://www.contributor-covenant.org/)
- OpenSSF, [Scorecard](https://scorecard.dev/)
- NVD, [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094); Lasse Collin, [XZ Utils backdoor](https://tukaani.org/xz-backdoor/)
