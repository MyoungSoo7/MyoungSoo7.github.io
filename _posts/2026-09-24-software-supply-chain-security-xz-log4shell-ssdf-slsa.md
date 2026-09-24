---
layout: post
title: "내 코드가 아니라 내가 가져다 쓴 코드가 뚫린다 — 소프트웨어 공급망 보안 (xz·Log4Shell 에서 SSDF·SLSA·SBOM·Sigstore 까지)"
date: 2026-09-24 19:50:47 +0900
categories: [Security]
tags: [security, supply-chain, sbom, slsa, ssdf, sigstore, owasp, devsecops]
---

시큐어코딩 글([지난 글](/2026/09/10/secure-coding/))은 "내가 쓰는 코드"에서 취약점을 막는 이야기였다.
이번 글은 그 반대편 — **내가 쓰지 않았지만 내 제품 안에 들어가 돌아가는 코드**의 이야기다.

요즘 백엔드 서비스 하나를 빌드하면 직접 짠 코드보다 의존성·베이스 이미지·빌드 도구·CI 액션이
훨씬 많다. 공격자 입장에선 방어가 단단한 앱 하나를 뚫는 것보다, 수천 개 앱이 함께 끌어다 쓰는
부품 하나를 오염시키는 편이 효율적이다. 이걸 **소프트웨어 공급망 공격**이라 부른다.

OWASP 도 이 흐름을 반영했다. 최신판인 [OWASP Top 10:2025](https://top10.owasp.org/2025/) 에는
**A03:2025 – Software Supply Chain Failures** 가 독립 항목으로 들어가 있고,
**A08:2025 – Software or Data Integrity Failures** 도 같은 계열의 문제를 다룬다.

## TL;DR

- 공급망 사고는 두 종류다. **① 선의의 부품에 난 구멍** (Log4Shell) 과 **② 부품 자체를 악의적으로 오염** (xz 백도어).
- ①은 "무엇이 들어 있는지 아는 것" (SBOM + 스캐닝) 으로 대응 속도가 갈린다.
- ②는 "이 산출물이 정말 그 소스에서, 그 방식으로 빌드됐는가" (SLSA provenance + 서명) 로 막는다.
- 조직 차원의 체크리스트가 필요하면 NIST **SSDF (SP 800-218)** 가 표준 틀이다.

---

## 1. 사례 ① — Log4Shell: 모두가 쓰던 부품에 난 구멍

[CVE-2021-44228](https://nvd.nist.gov/vuln/detail/CVE-2021-44228) 은 Apache Log4j2 의 JNDI 기능에서
비롯된 원격 코드 실행 취약점이다. NVD 기술(記述)에 따르면 영향 범위는
**2.0-beta9 부터 2.15.0 까지** (보안 릴리스 2.12.2, 2.12.3, 2.3.1 제외) 이고, CVSS 3.1 점수는
**10.0 (Critical)** 이다.

Log4Shell 이 남긴 교훈은 취약점 자체보다 **"우리 시스템 어디에 log4j 가 들어 있지?"에 답하는 데
걸린 시간**이었다. 직접 의존성이 아니라 A 라이브러리가 끌고 온 B 가 끌고 온 log4j 라면,
`pom.xml` 을 눈으로 훑어서는 찾을 수 없다. 이 질문에 즉시 답하게 해 주는 게 뒤에서 볼 **SBOM** 이다.

## 2. 사례 ② — xz Utils 백도어: 부품 자체가 오염되다

[CVE-2024-3094](https://nvd.nist.gov/vuln/detail/CVE-2024-3094) 는 성격이 전혀 다르다. NVD 는
"**Malicious code was discovered in the upstream tarballs of xz, starting with version 5.6.0**" 이라고
적고 있고, 영향 버전은 **5.6.0 과 5.6.1**, CVSS 3.1 **10.0** 이다. 실수로 난 버그가 아니라
의도적으로 심은 코드(CWE-506, Embedded Malicious Code)다.

발견 경위가 유명하다. Andres Freund 가 2024년 3월 29일
[oss-security 메일링 리스트에 올린 보고](https://www.openwall.com/lists/oss-security/2024/03/29/4)는
"ssh 로그인이 CPU 를 많이 먹고, valgrind 에러가 난다"는 이상 징후에서 출발한다.

이 사건에서 기술적으로 가장 중요한 한 줄은 이거다:

> "One portion of the backdoor is *solely in the distributed tarballs*"

백도어의 페이로드 일부는 테스트 파일로 위장해 git 저장소에도 들어가 있었지만, **그걸 빌드에
엮어 넣는 트리거(`build-to-host.m4` 의 한 줄)는 배포용 tarball 에만 있었다.** 즉 git 소스를
리뷰한 사람은 트리거를 볼 수 없었고, tarball 로 빌드한 배포판만 오염됐다.

→ **"소스를 봤다"와 "내가 받은 바이너리가 그 소스에서 나왔다"는 다른 말이다.**
이 간극을 메우는 게 SLSA 와 서명이다.

---

## 3. 대응 틀 ① — NIST SSDF: 조직이 해야 할 일의 목차

[NIST SP 800-218, Secure Software Development Framework (SSDF) v1.1](https://csrc.nist.gov/pubs/sp/800/218/final)
은 2022년 2월 최종판이 나온 안전한 개발 실무 프레임워크다. 실무를
[네 그룹](https://csrc.nist.gov/projects/ssdf)으로 묶는다.

| 그룹 | 뜻 | 공급망 관점에서의 예 |
|---|---|---|
| **PO** – Prepare the Organization | 조직 준비 | 의존성 도입 기준, 보안 역할 정의 |
| **PS** – Protect the Software | 소프트웨어 보호 | 소스·빌드 환경 접근 통제, 릴리스 무결성 보장 |
| **PW** – Produce Well-Secured Software | 안전하게 생산 | 서드파티 컴포넌트 검증, 빌드 도구 설정 |
| **RV** – Respond to Vulnerabilities | 취약점 대응 | 신규 CVE 식별·분석·패치 |

SSDF 는 "무엇을 해야 하는가"의 목차다. "어떻게 증명하는가"는 아래 도구들이 채운다.

## 4. 대응 틀 ② — SBOM: 무엇이 들어 있는지 기계가 읽게

SBOM(Software Bill of Materials)은 소프트웨어의 부품 명세서다. 미국 NTIA 가 2021년 7월 발표한
[The Minimum Elements For a Software Bill of Materials](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom)
는 최소 요소를 세 범주 — **Data Fields, Automation Support, Practices and Processes** — 로 나누고,
각 컴포넌트에 대해 추적할 기본 데이터 필드로 다음을 든다.

- Supplier Name
- Component Name
- Version of the Component
- Other Unique Identifiers
- Dependency Relationship
- Author of SBOM Data
- Timestamp

핵심은 **Dependency Relationship** 과 **Automation Support** 다. 전이 의존성까지 기계가 읽을 수 있는
형태(CycloneDX, SPDX 등)로 남겨 두면, 다음 Log4Shell 이 터졌을 때 "어디에 있지?"가 grep 한 번으로 끝난다.

실무 팁 하나. SBOM 을 **만드는 것**과 그걸로 **실제로 막는 것**은 별개다. CI 에 SBOM 생성과 스캐너를
붙여 놓고도 스텝 순서 때문에 게이트가 아무것도 검사하지 않은 채 초록불이 뜬 경험은
[이전 글](/2026/08/14/jacoco-sbom-trivy-green-light-that-ran-nothing/)에 적었다.
"skip 은 통과가 아니다."

## 5. 대응 틀 ③ — SLSA: 이 산출물은 어디서 어떻게 빌드됐나

[SLSA](https://slsa.dev/) (Supply-chain Levels for Software Artifacts) 는 빌드 무결성을 단계로 정의한다.
[v1.0 Build Track](https://slsa.dev/spec/v1.0/levels) 기준 (현재 최신은 v1.2):

| 레벨 | 요구 |
|---|---|
| **L0** | 요구 없음 — SLSA 미적용 상태 |
| **L1** | 패키지가 어떻게 빌드됐는지 보여 주는 **provenance** 존재 |
| **L2** | **호스티드 빌드 플랫폼이 생성하고 서명한** provenance |
| **L3** | **강화된 빌드 플랫폼** — 빌드 실행 간 간섭 차단, 서명 비밀키를 사용자 정의 빌드 스텝에서 격리 |

xz 사례에 대입해 보면 요점이 선명해진다. 배포물이 "어떤 커밋에서, 어떤 빌드 절차로" 나왔는지
검증 가능한 provenance 가 있고 소비자가 그걸 확인했다면, git 에 없는 파일이 끼어든 tarball 은
의심받을 여지가 커진다. SLSA 가 모든 공격을 막는 건 아니지만(git 에 들어간 페이로드 자체는 코드 리뷰의 몫이다),
**"소스와 산출물 사이의 틈"을 좁히는 게** SLSA 의 역할이다.

## 6. 대응 틀 ④ — Sigstore: 키 관리 없이 서명하기

서명은 오래전부터 있었지만, 개인키를 안전하게 보관·교체하는 부담 때문에 오픈소스에선 잘 안 쓰였다.
[Sigstore](https://docs.sigstore.dev/) 는 이 문제를 세 컴포넌트로 푼다.

- **Cosign** — 서명·검증 클라이언트 (컨테이너 이미지, blob 등)
- **Fulcio** — 인증기관. **OIDC 신원 토큰**을 받아 **단기 인증서**를 발급한다
- **Rekor** — 서명 기록을 남기는 **변경 불가·추가 전용(append-only) 투명성 로그**

즉 장기 개인키를 들고 있는 대신, "GitHub Actions 의 이 워크플로가 서명했다" 같은 **신원**에
서명을 묶고, 그 사실을 공개 로그에 남긴다. 소비자는 "이미지가 서명됐는가"가 아니라
"**내가 기대한 신원이** 서명했는가"를 검증해야 의미가 있다 — 이 부분을 빼먹으면 아무나 서명한
이미지도 통과한다.

---

## 7. 백엔드 팀이 이번 주에 할 수 있는 것

거창한 도입 전에, 작게 시작하는 순서:

1. **의존성 버전 고정** — lockfile 커밋, 베이스 이미지는 태그 대신 digest 로.
2. **빌드마다 SBOM 생성** 후 산출물과 함께 보관 (CycloneDX/SPDX).
3. **SBOM 기반 취약점 스캔을 CI 게이트로** — 그리고 스캔이 *실제로 돌았는지* 확인하는 단계를 둔다.
4. **CI 액션·빌드 도구도 의존성으로 취급** — 서드파티 액션은 커밋 SHA 로 고정.
5. **릴리스 산출물에 서명 + provenance** — Cosign keyless 로 시작하고, 배포 측에서 신원까지 검증.
6. **취약점 대응 절차(RV) 문서화** — 새 CVE 가 떴을 때 누가, 무엇으로(SBOM), 얼마 안에 확인하는지.

## 맺으며

CISA 의 [Secure by Design](https://www.cisa.gov/resources-tools/resources/secure-by-design) 원칙 첫 줄은
"**Take Ownership of Customer Security Outcomes**" 다. 공급망 보안은 "그건 라이브러리 버그라서"라는
말이 더는 면책이 되지 않는다는 선언에 가깝다. 내 제품 안에서 돌아가면, 내가 쓴 코드든 아니든 내 책임이다.

---

## References

1. OWASP, *OWASP Top 10:2025* — <https://top10.owasp.org/2025/>
2. NIST NVD, *CVE-2021-44228* (Log4Shell) — <https://nvd.nist.gov/vuln/detail/CVE-2021-44228>
3. NIST NVD, *CVE-2024-3094* (xz Utils) — <https://nvd.nist.gov/vuln/detail/CVE-2024-3094>
4. Andres Freund, "backdoor in upstream xz/liblzma leading to ssh server compromise", oss-security, 2024-03-29 — <https://www.openwall.com/lists/oss-security/2024/03/29/4>
5. NIST, *SP 800-218: Secure Software Development Framework (SSDF) Version 1.1*, Feb 2022 — <https://csrc.nist.gov/pubs/sp/800/218/final>
6. NIST CSRC, *SSDF Project* — <https://csrc.nist.gov/projects/ssdf>
7. NTIA, *The Minimum Elements For a Software Bill of Materials (SBOM)*, July 2021 — <https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom>
8. SLSA, *Security levels (v1.0)* — <https://slsa.dev/spec/v1.0/levels>
9. Sigstore Documentation — <https://docs.sigstore.dev/>
10. CISA, *Secure by Design* — <https://www.cisa.gov/resources-tools/resources/secure-by-design>
