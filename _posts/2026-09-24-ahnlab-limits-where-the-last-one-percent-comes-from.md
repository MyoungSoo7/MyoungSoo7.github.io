---
layout: post
title: "안랩 보안의 한계 — V3 가 99% 를 막아도 남는 구멍은 어디서 오는가?"
date: 2026-09-24 20:16:11 +0900
categories: [Security]
tags: [AhnLab, V3, Antivirus, Endpoint Security, KSA, AV-TEST, CVE, Supply Chain]
---

먼저 공정하게 시작하자. **안랩 V3 는 독립 시험에서 잘 막는다.** 이 글은 "V3 가 나쁘다" 는 글이 아니다. 오히려 반대로, **잘 만든 백신도 구조적으로 넘을 수 없는 선이 어디인지** 를 안랩이라는 구체적 사례로 짚어 보려는 글이다.

한계는 제품 품질보다 네 개의 층에서 나온다.

| 층위 | 무엇이 문제인가 | 근거 |
|---|---|---|
| 1. 시험 점수 | 99% 는 "시험 샘플" 에 대한 숫자다 | AV-TEST 인증 결과 |
| 2. 탐지기 자체 | 파일을 해석하는 코드가 곧 공격면이다 | IEEE S&P 2012, NVD CVE |
| 3. 중앙 관리 서버 | 전사 PC 를 제어하는 서버는 공격자에게도 최고의 표적이다 | CISA 권고, NVD CVE |
| 4. 의무 설치 생태계 | "깔아야만 은행을 쓰는" 구조가 만든 위험 | USENIX Security 2025 |

## 1. 독립 시험 — 잘 막는다, 그리고 그게 전부는 아니다

독립 시험기관 AV-TEST 는 보호·성능·사용성을 각 6점 만점으로 평가한다. 최근 두 차례 Windows 11 시험에서 AhnLab V3 Internet Security 9.0 의 결과는 이렇다.[^avtest2510][^avtest2602]

| 시험 | 제로데이 방어 (Real-World) | 업계 평균 | 최근 4주 유포 악성코드 탐지 | 보호 점수 |
|---|---|---|---|---|
| 2025년 9월 | 99.4% | 99.3% | 100% | 6.0 / 6.0 |
| 2025년 10월 | 100% | 99.3% | 100% | |
| 2026년 1월 | 99.8% | 99.7% | 100% | 5.5 / 6.0 |
| 2026년 2월 | 98.9% | 99.7% | 100% | |

(보호 점수는 두 달 묶음 기준. 제로데이 표본은 각 358개, 285개)

업계 평균과 비슷하거나 그 위에 있고, 한 달은 평균을 약간 밑돌았다. **세계적으로 경쟁력 있는 수준**이라는 게 공정한 평가다.

하지만 이 숫자가 말하지 않는 것도 분명하다.

- 제로데이 표본은 **수백 개**다. 시험기관이 수집한 "유포 중인" 위협이지, 특정 기업을 겨냥해 한 번만 쓰는 표적형 악성코드가 아니다.
- 1% 의 미탐은 개인 PC 한 대에는 작지만, **PC 수만 대를 가진 조직에는 매일 일어나는 사건**이다.
- 탐지율은 "악성 파일이 들어왔을 때" 의 이야기다. 탈취한 정상 계정, 정상 관리 도구만 쓰는 공격은 애초에 탐지 대상이 아닐 수 있다.

## 2. 탐지기 자체가 공격면이다

백신은 압축 파일, 실행 파일, 문서를 **모두 열어 본다.** 즉, 인터넷에서 온 가장 신뢰할 수 없는 입력을 가장 높은 권한으로 파싱하는 프로그램이다.

2012년 IEEE S&P 에서 Jana 와 Shmatikov 는 이 구조의 약점을 체계적으로 보였다.[^jana] 탐지기가 파일 형식을 판단하는 방식과, 실제 OS·애플리케이션이 파일을 해석하는 방식의 **차이**를 이용하면, 악성코드를 한 바이트도 난독화하지 않고도 탐지를 피할 수 있다.

> *"we discovered 45 new evasion exploits and tested them against 36 popular antivirus scanners, all of which proved vulnerable to various chameleon and werewolf attacks."*

이 연구에서 파생된 CVE 중 일부에는 AhnLab V3 가 Kaspersky, Sophos, Symantec 등과 **나란히** 올라 있다. 예를 들어 CVE-2012-1462 는 *"allows remote attackers to bypass malware detection via a ZIP file containing an invalid block of data at the beginning"* 이라고 기록돼 있다.[^cve1462] 안랩만의 결함이 아니라 **업계 공통의 설계 문제**였다는 점이 핵심이다.

파서 우회보다 더 무거운 건 **커널 권한**이다. 백신은 커널 드라이버로 동작하므로, 그 드라이버의 버그는 곧 권한 상승 경로가 된다. NVD 의 CVE-2013-3947 은 V3 Internet Security 8.0 의 드라이버에서 *"allows local users to gain privileges via a crafted ... IOCTL call"* 이라고 기록한다.[^cve3947]

NVD 에서 "AhnLab" 으로 검색되는 CVE 는 이 글을 쓰는 시점에 17건이고,[^nvdsearch] 대부분 2005~2013년의 오래된 것들이다. 숫자가 많다고 보기는 어렵다. 요점은 개수가 아니라 **"보안 제품은 보안 경계 밖에 있지 않다"** 는 원칙이다.

## 3. 중앙 관리 서버 — 방어의 사령부는 공격의 사령부가 된다

기업 환경에서 백신은 혼자 돌지 않는다. 관리 서버가 수천 대 PC 에 정책을 내리고, 업데이트를 배포하고, 로그를 모은다. 편리한 만큼 위험하다. **그 서버를 장악하면 전사 PC 에 코드를 배포할 수 있기 때문이다.**

2013년 3월 20일 국내 방송사·금융사 PC 의 디스크(MBR)를 지운 이른바 3.20 전산대란 이후, 미국 CISA(당시 US-CERT)는 권고문에서 이렇게 경고했다.[^cisa]

> *"Recognize that without proper internal monitoring, an organization's 'Enterprise Trust Anchors' ... and centralized management services (remote helpdesk access, patch management and asset inventory suites, etc.) could be compromised and used to subvert all other security controls."*

이 교훈은 지금도 유효하다. NVD 에는 최근에도 안랩의 기업용 관리 제품에 대한 기록이 올라왔다. CVE-2023-49440 은 AhnLab EPP 1.0.15 의 SQL Injection,[^cve49440] CVE-2025-60357 은 AhnLab EPP Management 의 NoSQL Injection 이다.[^cve60357] 이 역시 안랩만의 문제가 아니다. **관리 콘솔은 웹 애플리케이션이고, 웹 애플리케이션의 흔한 취약점을 그대로 물려받는다.**

실무적 함의는 간단하다. 백신 관리 서버는 "보안 장비" 가 아니라 **도메인 컨트롤러급 핵심 자산**으로 다뤄야 한다. 망 분리, 관리자 MFA, 접근 로그 감시, 빠른 패치가 모두 필요하다.

## 4. 의무 설치 생태계 — 한국만의 한계

한국에서 은행·증권·공공 사이트를 쓰면 여러 개의 보안 프로그램을 설치하게 된다. 안랩의 **AhnLab Safe Transaction(ASTx)** 도 그중 하나로, 안랩은 이를 키보드 보안, 악성코드 감지, 네트워크 차단, 피싱·파밍 차단을 묶은 "Non-Active X 기반의 온라인 통합 보안 제품" 으로 소개한다.[^astx]

USENIX Security 2025 에 실린 KAIST·고려대·성균관대·티오리 공동 연구는 이런 의무 설치 보안 프로그램 묶음(KSA 2.0)을 전면 분석했다.[^ksa] 연구의 출발점은 2023년 북한이 실제로 이 프로그램들을 악용한 해킹 사건이었다.

> *"We identified 19 vulnerabilities that expose users to serious risks, such as keylogging, man-in-the-middle attacks, private key leakage, remote code execution, and device fingerprinting."*

**중요한 단서:** 이 논문은 제품명을 PRODUCT A~G 로 **익명화**했다. 따라서 위 19개 취약점 중 어느 것이 안랩 제품의 것인지, 혹은 하나라도 해당되는지는 논문만으로 알 수 없다. 이 글도 그것을 안랩의 결함으로 단정하지 않는다. 취약점은 모두 보고되어 패치되었다.

그러나 논문이 지적한 **구조적 문제**는 개별 제품을 넘어선다.

- 설문 참가자 400명 중 은행 이용자의 **97%** 가 설치했지만, **59%** 는 그 기능을 이해하지 못했다.
- 48명의 PC 를 직접 분석하니 1인당 평균 **9개**가 설치돼 있었고, 다수가 **2022년 이전의 구버전**이었다.
- 각 제품은 로컬 TLS 를 위해 자체 루트 CA 를 등록하는데, 분석한 7개 제품 중 2개를 뺀 나머지는 **프로그램을 삭제해도 루트 CA 인증서를 지우지 않았다.**

백신 입장에서 이 구조는 역설적이다. 보안 프로그램이 많을수록 **커널 드라이버·로컬 서버·루트 인증서 같은 고권한 공격면이 늘어난다.** 사용자는 무엇이 깔렸는지 모르고, 업데이트되지 않은 구버전이 PC 에 남는다. 개별 제품이 아무리 좋아도 **생태계 전체의 공격면**은 커진다.

## 5. 실무자를 위한 체크리스트

1. **백신은 한 층일 뿐이다.** EDR·로그 수집·네트워크 탐지 등 "탐지 실패 이후" 를 보는 층을 따로 둔다.
2. **백신 관리 서버를 최고 등급 자산으로 격리한다.** 관리 콘솔은 인터넷에 노출하지 않고, 관리자 계정에 MFA 를 건다.
3. **보안 제품 자체의 패치를 추적한다.** 보안 제품은 "알아서 최신" 이라는 가정을 버리고 NVD·벤더 공지를 모니터링한다.
4. **안 쓰는 금융 보안 프로그램은 지운다.** 설치된 목록을 주기적으로 점검하고, 남은 루트 인증서도 확인한다.
5. **점수표를 읽을 때 표본 크기를 본다.** "100%" 는 그 달 수백 개 표본에 대한 결과다.

## 맺으며 — 많이 깔린 보안 제품이 짊어진 것

안랩의 한계는 대부분 **안랩만의 한계가 아니다.** 파서 우회는 36개 스캐너 전부의 문제였고, 관리 서버의 위험은 모든 중앙 집중형 보안 제품의 문제이며, 의무 설치 생태계는 규제가 만든 구조다.

다만 안랩은 한국의 대표 보안 기업이고 그 제품은 금융 거래 경로에까지 깔려 있다. 그만큼 **공격자가 먼저 연구할 이유가 있는 대상**이기도 하다. 설치 수가 많다는 건 방어 범위가 넓다는 뜻이자, 뚫렸을 때의 피해 범위가 넓다는 뜻이다.

좋은 백신을 쓰는 건 필요조건이다. 충분조건이 되는 순간 — "V3 깔려 있으니 괜찮다" 라고 말하는 순간 — 백신은 방어 수단이 아니라 **안심 장치**가 된다. 한계는 제품이 아니라 그 믿음에서 시작된다.

---

## References

[^avtest2510]: AV-TEST, *Test AhnLab V3 Internet Security 9.0 for Windows 11 (October 2025)*. <https://www.av-test.org/en/antivirus/home-windows/windows-11/october-2025/ahnlab-v3-internet-security-9.0-251501/>
[^avtest2602]: AV-TEST, *Test AhnLab V3 Internet Security 9.0 for Windows 11 (February 2026)*. <https://www.av-test.org/en/antivirus/home-windows/windows-11/february-2026/ahnlab-v3-internet-security-9.0-261101/>
[^jana]: Suman Jana, Vitaly Shmatikov, *Abusing File Processing in Malware Detectors for Fun and Profit*, IEEE S&P 2012. <https://www.cs.cornell.edu/~shmat/shmat_oak12av.pdf>
[^cve1462]: NIST NVD, *CVE-2012-1462*. <https://nvd.nist.gov/vuln/detail/CVE-2012-1462>
[^cve3947]: NIST NVD, *CVE-2013-3947*. <https://nvd.nist.gov/vuln/detail/CVE-2013-3947>
[^nvdsearch]: NIST NVD, CVE API keyword search "AhnLab" (2026-09-24 조회). <https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=AhnLab>
[^cisa]: CISA (US-CERT), *South Korean Malware Attack* (2013). <https://www.cisa.gov/sites/default/files/publications/South%20Korean%20Malware%20Attack.pdf>
[^cve49440]: NIST NVD, *CVE-2023-49440*. <https://nvd.nist.gov/vuln/detail/CVE-2023-49440>
[^cve60357]: NIST NVD, *CVE-2025-60357*. <https://nvd.nist.gov/vuln/detail/CVE-2025-60357>
[^astx]: AhnLab, *AhnLab Safe Transaction (ASTx)* 제품 소개. <https://www.ahnlab.com/ko/product/astx>
[^ksa]: Taisic Yun et al., *Too Much of a Good Thing: (In-)Security of Mandatory Security Software for Financial Services in South Korea*, USENIX Security 2025. <https://www.usenix.org/conference/usenixsecurity25/presentation/yun>
