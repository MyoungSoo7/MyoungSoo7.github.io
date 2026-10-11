---
layout: post
title: "[SE100 #059] 소프트웨어 공급망 보안 — SBOM 과 SLSA"
date: 2026-10-11 17:03:42 +0900
categories: [software-engineering]
tags: [se100, delivery, supply-chain-security, sbom, slsa]
---

소프트웨어 공학 100 주제 시리즈의 59번째 글이다. (카테고리: 형상 관리와 전달)

## 한 줄 요약

SBOM 은 "이 소프트웨어 안에 무엇이 들어 있는가" 의 목록이고, SLSA 는 "이 산출물이 정말 그 소스에서 그 절차로 만들어졌는가" 를 단계별로 보증하는 프레임워크다. 하나는 **성분표**, 다른 하나는 **제조 이력**이다. 둘 다 결국 형상 관리의 식별과 감사를 조직 경계 밖까지 확장한 것이다.

## 왜 필요한가

공격 지점 지도, 의존성 해시 고정, SBOM 과 SLSA 의 기초는 [공급망 보안]({% post_url 2026-10-10-cs300-257-software-supply-chain-security %})에서 다뤘다. 이 글은 표준과 정책의 맥락, SLSA 명세의 실제 요구 사항, 그리고 그것을 빌드 파이프라인에 넣는 방법을 다룬다.

2024년 3월의 xz 사건이 이 주제의 핵심을 잘 보여 준다. Andres Freund 가 [oss-security 메일링 리스트에 보고](https://www.openwall.com/lists/oss-security/2024/03/29/4)한 바에 따르면, upstream xz 저장소와 배포 tarball 이 백도어에 감염되었고, 백도어의 한 부분은 **배포 tarball 에만** 들어 있었다. Git 저장소의 소스를 아무리 리뷰해도 보이지 않는 곳이었다. [NVD 의 CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094) 설명대로, 악성 코드는 5.6.0 버전부터 upstream tarball 에 있었고, 빌드 과정이 위장된 테스트 파일에서 미리 만든 오브젝트 파일을 꺼내 liblzma 의 함수를 변조했다.

"우리가 리뷰한 소스" 와 "우리가 실행하는 바이너리" 사이의 간극. 이것이 공급망 보안이 다루는 문제다.

## 핵심 개념

### 정책의 맥락: EO 14028

미국 대통령 행정명령 [14028 *Improving the Nation's Cybersecurity*](https://www.federalregister.gov/documents/2021/05/17/2021-10460/improving-the-nations-cybersecurity)(2021년 5월 12일 서명)는 연방 정부에 납품하는 소프트웨어의 공급망 보안을 요구하며 SBOM 을 명시적으로 다뤘다. 이 명령에 따라 미국 상무부 산하 NTIA 가 2021년 7월 [SBOM 최소 요소(The Minimum Elements For a Software Bill of Materials)](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom) 보고서를 발표했다. 이후 SBOM 은 규제 대응 문서이자 업계 표준 관행이 되었다.

### SBOM 의 최소 요소

NTIA 보고서는 최소 요소를 세 영역으로 정의한다.

| 영역 | 내용 |
|---|---|
| 데이터 필드 | 공급자 이름, 구성 요소 이름, 구성 요소 버전, 기타 고유 식별자, 의존 관계, SBOM 데이터 작성자, 타임스탬프 |
| 자동화 지원 | 자동 생성과 기계 판독 가능성. 형식으로 SPDX, CycloneDX, SWID 태그를 든다 |
| 실천과 절차 | 생성 빈도, 깊이, 알려진 미지(known unknowns), 배포와 전달, 접근 통제, 오류 수정 |

"알려진 미지" 는 실무에서 특히 중요하다. 모든 전이 의존성을 다 알 수는 없으므로, **모르는 부분이 어디인지를 명시**하라는 요구다. 빈칸과 "의존성 없음" 은 다른 말이다.

### 두 가지 표준 형식

| | SPDX | CycloneDX |
|---|---|---|
| 주관 | Linux Foundation | OWASP Foundation 이 개발, Ecma TC54 에서 표준화 |
| 국제 표준 | [ISO/IEC 5962:2021](https://spdx.dev/) | [ECMA-424](https://ecma-international.org/publications-and-standards/standards/ecma-424/) (1판 2024년 6월, 2판 2025년 12월은 CycloneDX v1.7) |

[ECMA-424 페이지](https://ecma-international.org/publications-and-standards/standards/ecma-424/)는 2판이 소프트웨어·하드웨어 구성 요소, 서비스, 의존성, 취약점, 암호 자산, 머신러닝 모델 등의 인벤토리를 표현한다고 설명한다. 어느 형식이든 생성 도구가 성숙해 있으므로, 형식 선택보다 **언제, 무엇을 대상으로 생성하는가** 가 더 중요하다.

생성 시점도 중요하다. 소스의 선언만 보면 실제로 들어간 버전을 놓치고, 완성된 이미지만 분석하면 정적 링크된 구성 요소를 놓칠 수 있다. 가장 정확한 것은 **빌드 도중, 빌드 도구가 해석한 그대로** 생성하는 SBOM 이다.

### SLSA: 빌드의 무결성 단계

[SLSA](https://slsa.dev/spec/v1.2/)(Supply-chain Levels for Software Artifacts, "살사")는 산출물의 무결성을 단계별로 보증하는 명세다. 현재 승인된 버전은 v1.2 로, **빌드 트랙**과 v1.2 에서 다시 도입된 **소스 트랙**으로 구성된다. 명세의 설명에 따르면 이전 버전은 SLSA 1~4 의 단일 트랙이었고, v1.0 에서 소스 측면을 빼고 빌드 트랙에 집중했다가, v1.2 에서 소스 트랙이 돌아왔다.

[빌드 트랙](https://slsa.dev/spec/v1.2/build-track-basics)의 수준:

| 수준 | 요지 | 막는 위협 |
|---|---|---|
| Build L0 | 보증 없음 | — |
| Build L1: Provenance exists | 패키지에 어떻게 빌드되었는지 보여 주는 출처 증명(provenance)이 있음. 우회·위조는 쉬움 | 실수 (예: 업스트림에 없는 커밋에서 빌드) |
| Build L2: Hosted build platform | 호스팅된 빌드 플랫폼이 출처 증명을 **생성하고 서명**. 소비자는 진위를 검증 | 빌드 **이후**의 변조 |
| Build L3: Hardened builds | 같은 프로젝트 안에서도 실행 간 영향 차단, 출처 증명 서명 비밀을 사용자 정의 빌드 단계가 접근 못 하게 | 빌드 **도중**의 변조(내부자, 탈취된 자격 증명, 다른 테넌트) |

L1 의 출처 증명에는 누가 빌드했는지, 어떤 빌드 절차를 썼는지, 최상위 입력이 무엇이었는지가 담긴다. 명세는 L3 를 "대부분의 소프트웨어 릴리스" 를 위한 수준으로 보지만, 기존 빌드 플랫폼의 큰 변경이 필요하다고 쓴다.

[소스 트랙](https://slsa.dev/spec/v1.2/source-requirements)의 수준은 L1 버전 관리(Version controlled), L2 이력과 출처 증명(History & Provenance), L3 지속적인 기술적 통제(Continuous technical controls), L4 2인 검토(Two-party review)로 이어진다. 형상 관리(SE100 #051 에서 다룬다)의 변경 통제를 보안 명세의 언어로 옮긴 것이라 보면 된다.

### 출처 증명, 서명, 투명성 로그

출처 증명은 형식이 있어야 검증할 수 있다. [in-toto](https://in-toto.io/)는 소프트웨어가 시작부터 설치까지 어떤 단계를, 누가, 어떤 순서로 거쳤는지 투명하게 만드는 프레임워크로 CNCF 졸업 프로젝트다. [SLSA 빌드 출처 증명 형식](https://slsa.dev/spec/v1.2/build-provenance)도 in-toto 증명(attestation)의 파싱 규칙을 따른다.

서명은 [Sigstore](https://docs.sigstore.dev/about/overview/)가 사실상 표준이 되었다. 공식 개요의 흐름은 이렇다.

```
1. 클라이언트(cosign 등)가 키 쌍 생성
2. OIDC 신원 토큰(사람의 이메일 또는 CI 워크플로 신원)과 함께
   인증 기관 Fulcio 에 인증서 요청
3. Fulcio 가 토큰을 검증하고 그 신원에 묶인 단기(short-lived) 인증서 발급
4. 서명 후, 산출물 다이제스트·서명·인증서를 투명성 로그 Rekor(추가 전용 원장)에 기록
검증: 서명 확인 + 인증서의 신원이 기대한 신원인지 + Sigstore 신뢰 루트 + Rekor 포함 증명
```

장기 비밀 키를 보관할 필요가 없고(키 유출 위험 감소), 모든 서명이 공개 로그에 남아 사후 감사가 가능하다는 것이 핵심이다. 검증 단계의 "기대한 신원인지" 확인이 빠지면 **누구나 서명할 수 있다**는 점을 잊으면 안 된다.

## 실무 적용

### 빌드 파이프라인에 넣기 (GitHub Actions 예)

```yaml
permissions:
  contents: read
  id-token: write          # OIDC 토큰 (Sigstore 서명용)
  attestations: write
steps:
  - uses: actions/checkout@v4
  - run: ./gradlew bootJar && ./scripts/make-sbom.sh   # 산출물과 SBOM 을 같은 빌드에서 (SBOM 경로는 도구에 따라 다름)
  - name: 빌드 출처 증명
    uses: actions/attest@v4
    with:
      subject-path: build/libs/app.jar
  - name: SBOM 증명
    uses: actions/attest@v4
    with:
      subject-path: build/libs/app.jar
      sbom-path: build/sbom/bom.cdx.json
```

[GitHub 문서](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds)에 따르면 이렇게 하면 바이너리나 컨테이너 이미지의 빌드 출처를 확립하는 증명과 서명된 SBOM 증명이 생성되고, 소비자는 `gh attestation verify` 로 검증할 수 있다.

### 소비자 측 점검표

```
[ ] 내려받는 산출물을 다이제스트로 고정하고, 서명·출처 증명을 검증한다
[ ] 검증 정책에 "기대하는 빌더 신원(저장소, 워크플로)" 을 명시한다
[ ] 내가 배포하는 모든 산출물에 SBOM 을 같은 빌드에서 생성해 함께 보관한다
[ ] SBOM 을 취약점 DB(예: [OSV](https://osv.dev/))와 정기 대조해, 새 CVE 공개 시 영향 범위를 즉시 찾는다
[ ] 소스 저장소와 배포 tarball 이 다를 수 있는 의존성은 저장소에서 직접 빌드하거나 차이를 검사한다
[ ] 빌드 플랫폼의 서명 비밀이 사용자 정의 빌드 단계에 노출되지 않는다 (L3 요구)
```

xz 사례의 교훈이 네 번째와 다섯 번째 항목에 있다. 저장소와 tarball 의 차이는 재현 가능한 빌드(SE100 #053 에서 다룬다)와 출처 증명이 함께 있을 때 기계적으로 드러난다.

## 흔한 오해와 함정

- **"SBOM 이 있으면 안전하다."** SBOM 은 목록일 뿐이다. 취약점 대조, 갱신, 대응 절차와 연결되지 않으면 서랍 속 문서다. NTIA 보고서 자체도 SBOM 이 모든 보안 문제를 풀지는 않으며 그 위에 다른 도구와 실천을 쌓을 기초 데이터 계층이라고 말한다.
- **"서명했으니 믿을 수 있다."** 서명은 "누가" 를 증명할 뿐 "무엇을 어떻게" 는 증명하지 않는다. 출처 증명과 신원 검증 정책이 함께 필요하다.
- **SLSA 수준을 산출물 품질로 오해.** SLSA Build L3 는 빌드 과정의 무결성 보증이지 코드에 취약점이나 백도어가 없다는 뜻이 아니다. xz 처럼 소스 자체에 악성 코드가 들어오면 빌드 트랙만으로는 막지 못한다. 소스 트랙과 리뷰가 필요한 이유다.
- **알려진 미지를 숨김.** 분석하지 못한 부분을 "없음" 으로 쓰면 SBOM 은 거짓 안심을 준다.

## 확인 문제

1. SBOM 과 SLSA 출처 증명은 각각 어떤 질문에 답하는가?
2. NTIA 최소 요소의 데이터 필드 일곱 가지를 나열하라.
3. SLSA Build L2 와 L3 는 각각 어떤 시점의 변조를 막는가? L3 의 빌드 플랫폼 요구 두 가지는?
4. xz 백도어가 Git 소스 리뷰로 발견되기 어려웠던 이유와, 이를 기계적으로 드러낼 수 있는 실천은?
5. Sigstore 로 서명된 산출물을 검증할 때 서명 자체의 유효성 외에 반드시 확인해야 하는 것은?

### 풀이

1. SBOM: 이 소프트웨어에 어떤 구성 요소가 어떤 버전으로 들어 있는가. 출처 증명: 이 산출물을 누가, 어떤 절차로, 어떤 입력에서 빌드했는가.
2. 공급자 이름, 구성 요소 이름, 구성 요소 버전, 기타 고유 식별자, 의존 관계, SBOM 데이터 작성자, 타임스탬프.
3. L2 는 빌드 이후의 변조(서명된 출처 증명), L3 는 빌드 도중의 변조. L3 요구: 같은 프로젝트 안에서도 실행 간 상호 영향 차단, 출처 증명 서명 비밀을 사용자 정의 빌드 단계가 접근 못 하게.
4. 백도어의 일부가 배포 tarball 에만 있고 Git 저장소에는 없었다. 저장소에서 직접 재현 가능하게 빌드한 결과와 배포 산출물을 비교하거나, 출처 증명으로 산출물이 어느 소스에서 나왔는지 검증하면 차이가 드러난다.
5. 인증서에 묶인 신원이 기대한 신원(예: 특정 저장소의 특정 워크플로)인지, 그리고 Rekor 투명성 로그에 포함되었는지. 신원 확인이 없으면 아무나 한 서명도 통과한다.

## 더 읽을거리 (References)

- The White House, [Executive Order 14028: Improving the Nation's Cybersecurity](https://www.federalregister.gov/documents/2021/05/17/2021-10460/improving-the-nations-cybersecurity), Federal Register, 2021
- NTIA, [The Minimum Elements For a Software Bill of Materials (SBOM)](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom), 2021
- SLSA, [Specification v1.2](https://slsa.dev/spec/v1.2/), [Build Track Basics](https://slsa.dev/spec/v1.2/build-track-basics), [Source Track Requirements](https://slsa.dev/spec/v1.2/source-requirements)
- SPDX, [spdx.dev](https://spdx.dev/) (ISO/IEC 5962:2021)
- Ecma International, [ECMA-424 CycloneDX Bill of materials specification](https://ecma-international.org/publications-and-standards/standards/ecma-424/)
- [in-toto](https://in-toto.io/)
- Sigstore, [Overview](https://docs.sigstore.dev/about/overview/)
- Andres Freund, [backdoor in upstream xz/liblzma leading to ssh server compromise](https://www.openwall.com/lists/oss-security/2024/03/29/4), oss-security, 2024
- NIST NVD, [CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)
- GitHub Docs, [Using artifact attestations to establish provenance for builds](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds)
- CS300: [공급망 보안]({% post_url 2026-10-10-cs300-257-software-supply-chain-security %})
