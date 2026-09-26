---
layout: post
title: "IoT 보안 — 미라이가 쓴 비밀번호 62개가 10년 뒤 법 조문이 되기까지"
date: 2026-09-26 14:25:52 +0900
categories: [Security]
tags: [IoT Security, Mirai, ETSI EN 303 645, NIST IR 8259A, Cyber Resilience Act, PSTI, OWASP]
---

2016년 가을, 인터넷에서 가장 힘없는 기기들이 인터넷에서 가장 잘 방어된 사이트 몇 곳을 쓰러뜨렸다. 공유기·IP 카메라·DVR 로 이루어진 봇넷 **미라이(Mirai)** 다. 이 공격에는 제로데이가 없었다. 공장에서 나올 때 박혀 있던 기본 비밀번호면 충분했다.

그로부터 10년이 지난 2026년 9월 11일, EU 에서는 디지털 제품 제조사가 **실제로 악용되는 취약점을 24시간 안에 신고해야 하는 의무**가 시행됐다. 이 글은 그 사이를 잇는다. IoT 보안이 왜 PC·서버 보안과 다른 문제인지, 그리고 업계 권고가 어떻게 법 조문이 되었는지를 1차 출처로 따라간다.

## 1. 미라이는 무엇을 증명했나

가장 권위 있는 분석은 구글·클라우드플레어·아카마이 연구자들과 대학 연구진이 함께 쓴 *Understanding the Mirai Botnet*(USENIX Security 2017)이다. 7개월 동안 네트워크 텔레스코프, 인터넷 전역 스캔, 허니팟, C2 명령 수집, DDoS 피해자 로그를 엮어 측정했다. ([Antonakakis et al., 2017](https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/antonakakis))

논문이 밝힌 동작은 놀라울 만큼 단순하다.

- 임의의 IPv4 주소에 **Telnet(23, 2323번 포트)** SYN 을 뿌린다.
- 응답이 오면 **미리 박아 둔 62개 아이디/비밀번호 쌍** 가운데 10개를 골라 로그인을 시도한다.
- 성공하면 보고 서버에 알리고, 별도 로더가 기기 아키텍처에 맞는 악성코드를 내려보낸다.

이 정도로 첫 20시간에 약 6만 5천 대를 감염시켰고, 정점에는 **60만 대**에 이르렀다. 크렙스 온 시큐리티를 향한 첫 공격은 600Gbps 를 넘었다. 같은 논문은 감염이 **재부팅을 넘어 유지되지 않았다**는 점도 적는다. 다만 재부팅 뒤에도 비밀번호는 그대로다. 그러니 기기는 다시 같은 문으로 들어올 공격을 기다리는 상태로 돌아갈 뿐이다. *(이 문장은 논문의 관찰을 바탕으로 한 필자의 추론이다.)*

논문의 결론은 기술보다 생태계를 겨눈다. 데스크톱 웜을 겪으며 20년간 쌓은 보안 관행이 IoT 에는 없었다. 그리고 IoT 에는 **자동 업데이트, 지원 종료(end-of-life), 사용자 통지**라는 고유한 난제가 있다고 지적한다.

## 2. IoT 가 서버와 다른 이유

미라이 논문의 지적을 풀어 쓰면, IoT 가 구조적으로 불리한 지점은 세 가지다.

| 서버·PC 에서는 | IoT 에서는 |
|---|---|
| 관리자가 계정을 만들고 비밀번호를 정한다 | 화면도 키보드도 없다. 공장 기본값이 곧 운영값이 되기 쉽다 |
| OS 가 업데이트 채널을 제공한다 | 제조사가 업데이트 경로를 만들지 않으면 **영원히** 그 펌웨어다 |
| 교체 주기가 짧고 자산 목록이 있다 | 벽에 붙은 카메라는 10년을 간다. 누가 지원을 끝냈는지 사용자는 모른다 |

그래서 IoT 보안의 핵심 질문은 "어떤 암호 알고리즘을 쓰는가"가 아니다. **출고 순간의 기본값, 그리고 출고 뒤 몇 년 동안 누가 책임지는가**다.

## 3. 권고 — 같은 결론에 도달한 세 문서

미라이 이후 여러 기관이 기준을 냈다. 출발점은 달라도 맨 앞에 놓은 항목은 거의 같다.

**OWASP IoT Top 10 (2018).** 1번이 *I1 Weak, Guessable, or Hardcoded Passwords* 다. 그 뒤로 불필요한 네트워크 서비스(I2), 안전한 업데이트 수단 부재(I4), 낡은 컴포넌트(I5), 장치 관리 부재(I8), 안전하지 않은 기본 설정(I9)이 이어진다. 미라이가 건드린 곳이 곧 1·2·9번이다. ([OWASP](https://owasp.org/www-project-internet-of-things/))

**ETSI EN 303 645 V2.1.1 (2020-06).** 소비자 IoT 의 유럽 표준이다. 13개 보안 조항 가운데 앞의 셋이 이렇다. ([ETSI](https://www.etsi.org/deliver/etsi_en/303600_303699/303645/02.01.01_60/en_303645v020101p.pdf))

1. 5.1 범용 기본 비밀번호 금지 (*No universal default passwords*)
2. 5.2 취약점 신고를 처리할 수단 마련
3. 5.3 소프트웨어를 최신으로 유지

나머지는 민감한 보안 파라미터의 안전한 저장, 안전한 통신, 노출된 공격면 최소화, 소프트웨어 무결성, 개인정보 보호, 장애 복원력, 텔레메트리 점검, 사용자 데이터 삭제, 쉬운 설치·유지보수, 입력 검증이다.

**NIST IR 8259A (2020-05).** 미국 NIST 는 "기기가 스스로 갖춰야 할 기술 역량"을 6가지로 정의했다. ([Fagan et al., NIST](https://doi.org/10.6028/NIST.IR.8259A))

| 역량 | 요지 |
|---|---|
| Device Identification | 논리적·물리적으로 고유하게 식별된다 |
| Device Configuration | 권한 있는 주체만 설정을 바꾸고, 안전한 설정으로 되돌릴 수 있다 |
| Data Protection | 저장·전송 데이터를 보호한다 |
| Logical Access to Interfaces | 네트워크·로컬 인터페이스 접근을 제한한다 |
| Software Update | 업데이트를 받고, **설치 전에 검증·인증**하고, 권한 있는 주체만 수행한다 |
| Cybersecurity State Awareness | 자기 보안 상태를 권한 있는 주체에게 알릴 수 있다 |

세 문서를 겹쳐 보면 공통 분모가 선명하다. **고유한 자격증명, 신고 창구, 업데이트.** 미라이가 뚫고 들어온 구멍과 정확히 대응한다.

## 4. 권고가 법이 되다

### 영국 PSTI — 2024년 4월 29일 시행

영국은 ETSI 의 앞 세 조항을 사실상 그대로 법으로 만들었다. *Product Security and Telecommunications Infrastructure Act 2022* 와 2023년 시행규칙이 2024년 4월 29일부터 적용된다. 제조사·수입사·유통사 모두 의무 주체다. ([GOV.UK](https://www.gov.uk/government/publications/the-uk-product-security-and-telecommunications-infrastructure-product-security-regime))

1. **비밀번호.** 제품마다 고유하거나 사용자가 정해야 한다. 고유 비밀번호라도 `password1`·`password2` 같은 증가 카운터, 공개 정보, 시리얼 번호 같은 식별자에서 파생하면 안 된다. 식별자는 업계 관행으로 인정되는 암호화나 키 기반 해시를 거친 경우만 예외다.
2. **보안 문제 신고 방법**을 공개한다. 접수 확인과 진행 상황 안내를 언제까지 받을 수 있는지도 함께 공개한다.
3. **최소 보안 업데이트 기간**(defined support period)을 공개한다. 정부 안내는 이를 종료 날짜로 밝히도록 한다. 기간을 늘리면 새 기간을 가능한 한 빨리 다시 공개해야 한다. ([PSTI Regulations 2023, Schedule 1](https://www.legislation.gov.uk/uksi/2023/1007/schedule/1/made))

3번이 특히 흥미롭다. 미라이 논문이 난제로 꼽은 "지원 종료"를 기술이 아니라 **공시 의무**로 풀었다. 업데이트를 영원히 하라고 강제하지는 않는다. 대신 언제 끝나는지 구매 전에 알게 한다.

### EU 사이버복원력법(CRA) — 신고 의무가 2주 전 시작됐다

EU 의 *Cyber Resilience Act* 는 범위가 훨씬 넓다. 베이비 모니터부터 스마트워치, 앱과 소프트웨어까지 "디지털 요소가 있는 제품" 전체가 대상이다. 설계·개발·유지보수 전 단계에 필수 보안 요구사항을 걸고, 적합성은 CE 마크로 표시한다. ([European Commission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act))

| 시점 | 내용 |
|---|---|
| 2024-12-10 | 발효 |
| **2026-09-11** | **신고 의무 적용** — 실제로 악용되는 취약점과 심각한 사고 |
| 2027-12-11 | 주요 의무 전면 적용 |

신고 절차는 구체적이다. 인지 후 **24시간 안에 조기 경보, 72시간 안에 본 신고**를 한다. 악용 취약점이면 수정 조치가 나온 뒤 **14일 안에** 최종 보고서를 낸다. 창구는 ENISA 가 운영하는 단일 신고 플랫폼(SRP) 하나이고, 이 플랫폼도 2026년 9월 11일부터 운영된다. ([European Commission — CRA reporting](https://digital-strategy.ec.europa.eu/en/policies/cra-reporting))

ETSI 5.2 "취약점 신고를 처리할 수단"이 권고에서 **시한이 붙은 법적 의무**로 바뀐 셈이다.

## 5. 쓰는 쪽에서 할 수 있는 것

법은 새로 **파는** 제품을 겨눈다. 이미 집과 사무실에 붙어 있는 기기는 쓰는 사람이 챙겨야 한다. 위 문서들을 사용자 입장으로 옮기면 이렇다.

- **기본 비밀번호부터 바꾼다.** 미라이의 62개 사전은 지금도 공개된 소스 코드에 그대로 있다.
- **쓰지 않는 원격 서비스를 끈다.** Telnet, 외부에서 여는 관리 페이지, 공유기의 UPnP 자동 포트 개방이 대표적이다(OWASP I2·I9).
- **IoT 기기를 별도 네트워크로 분리한다.** 게스트 Wi-Fi 나 VLAN 으로 PC·NAS 와 떼어 놓으면 한 대가 뚫려도 번지는 범위가 줄어든다.
- **살 때 지원 종료일을 본다.** PSTI 시장에서는 제조사가 이 날짜를 공개해야 한다. 날짜를 찾을 수 없다면 그것 자체가 정보다.
- **기기의 로그를 밖으로 뺀다.** NIST 의 *Cybersecurity State Awareness* 를 쓰는 쪽에서 살리는 방법이다. 기기 안에만 있는 로그는 기기가 뚫리면 같이 사라진다. *(뒷문장은 필자의 운영 경험이다.)*

## 6. 한계와 남은 질문

- **효과 측정은 아직 없다.** PSTI 시행 이후 기본 비밀번호 기반 감염이 얼마나 줄었는지 보여 주는 중립적 실측을 찾지 못했다. 이 글은 법의 효과를 주장하지 않는다.
- **이미 팔린 기기는 법의 바깥이다.** 두 법 모두 시장에 새로 나오는 제품의 의무를 정한다. 10년 가는 카메라에게 이 공백은 길다. *(필자의 해석이다.)*
- **미라이 수치는 2016~2017년 측정이다.** 봇넷 규모와 기기 구성은 그 뒤로 달라졌다. 여기서는 공격이 얼마나 **단순했는지**를 보이려고 인용했고, 오늘의 위협 규모로 읽으면 안 된다.

## 정리

미라이가 증명한 것은 공격 기술의 정교함이 아니라 **기본값의 위력**이었다. 그 뒤 10년 동안 OWASP, ETSI, NIST 는 저마다 다른 길로 같은 세 줄에 도달했다. 고유한 자격증명, 신고 창구, 업데이트. 영국은 그 세 줄을 2024년에 법으로 만들었고, EU 는 2026년 9월부터 신고에 시계를 달았다.

IoT 보안의 질문은 여전히 "이 기기가 얼마나 강한가"보다 **"이 기기를 출고 뒤 몇 년 동안 누가 책임지는가"**에 가깝다.

## References

1. Antonakakis, M. et al. *Understanding the Mirai Botnet.* 26th USENIX Security Symposium, 2017. <https://www.usenix.org/conference/usenixsecurity17/technical-sessions/presentation/antonakakis>
2. ETSI. *EN 303 645 V2.1.1 — Cyber Security for Consumer Internet of Things: Baseline Requirements*, 2020-06. <https://www.etsi.org/deliver/etsi_en/303600_303699/303645/02.01.01_60/en_303645v020101p.pdf>
3. Fagan, M., Megas, K., Scarfone, K., Smith, M. *NISTIR 8259A — IoT Device Cybersecurity Capability Core Baseline.* NIST, 2020-05. <https://doi.org/10.6028/NIST.IR.8259A>
4. OWASP. *Internet of Things Project — OWASP IoT Top 10 2018.* <https://owasp.org/www-project-internet-of-things/>
5. UK Government. *The UK Product Security and Telecommunications Infrastructure (Product Security) regime.* <https://www.gov.uk/government/publications/the-uk-product-security-and-telecommunications-infrastructure-product-security-regime>
6. *The Product Security and Telecommunications Infrastructure (Security Requirements for Relevant Connectable Products) Regulations 2023*, Schedule 1. <https://www.legislation.gov.uk/uksi/2023/1007/schedule/1/made>
7. European Commission. *Cyber Resilience Act.* <https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act>
8. European Commission. *Cyber Resilience Act — Reporting obligations.* <https://digital-strategy.ec.europa.eu/en/policies/cra-reporting>
