---
layout: post
title: "리눅스는 공짜인데 RHEL 은 무엇을 파는가 — 무료판·유료판 비교와 구독이 필요한 순간"
date: 2026-09-13 05:12:34 +0900
categories: [infra, linux]
tags: [rhel, ubuntu, ubuntu-pro, centos, rocky, almalinux, licensing, subscription]
---

[앞 글](/2026/09/13/oracle-weblogic-jboss-necessity-and-cost/)에서 오라클·웹로직·JBoss 의 유료 필요성을 따졌다. 그 연장선에서 자연스러운 다음 질문 — OS 층은 어떤가. 리눅스 커널은 [GPL v2 자유 소프트웨어](https://www.kernel.org/category/faq.html)이고 우분투는 공짜로 설치하는데, Red Hat Enterprise Linux(RHEL) 구독은 [공식 스토어](https://store.redhat.com/en/products/red-hat-enterprise-linux-server) 기준 서버 한 대에 **연 $383.90 부터** 시작한다. 코드가 무료인 세계에서 이 돈은 무엇에 대한 값이고, 언제 낼 가치가 있는가. 미들웨어 편과 같은 두 관점 — 개발·운영자 관점과 비용 관점 — 으로 정리한다.

## 전제: 파는 것은 코드가 아니다

리눅스 세계의 유료화 구조는 오라클과 근본적으로 다르다. 오라클 DB 는 코드 자체가 상용이지만, RHEL 의 소스는 GPL 계열이라 Red Hat 도 코드를 독점할 수 없다. 그래서 유료 리눅스가 실제로 파는 것은 네 가지다.

1. **수명주기.** RHEL 은 메이저 버전 하나를 [10년](https://access.redhat.com/support/policy/updates/errata)(Full Support → Maintenance Support) 지원하고, 그 뒤로도 유료 연장(ELS)이 있다. 이 10년 동안 커널·패키지 버전을 못 박은 채 보안 패치만 백포트해 주는 것 — "재검증 없이 오래 쓰는 권리"가 상품의 몸통이다.
2. **인증.** FIPS 140-3 같은 암호 모듈 인증, 하드웨어·상용 소프트웨어(ISV) 벤더의 지원 매트릭스는 대부분 RHEL·SLES 같은 상용 배포판을 기준으로 발급된다. 규제 산업에서는 이것이 선택이 아니라 입장권이다.
3. **지원 SLA.** 새벽에 커널 패닉이 나면 전화를 받아 주고, 필요하면 핫픽스를 만들어 줄 책임 주체.
4. **관리 도구.** 패치 오케스트레이션(Red Hat Satellite, Canonical Landscape), 무중단 커널 패치(kpatch, Livepatch) 같은 부속.

거꾸로 말하면 — 이 넷이 필요 없는 조직에게 유료 리눅스는 **기능적으로 무료판과 같은 물건**이다. 미들웨어 편의 JBoss EAP ↔ WildFly 관계가 OS 층에서 그대로 반복된다.

## 진영별 무료판·유료판 지도

**Red Hat 계열.** 유료판은 RHEL 하나지만 무료 경로가 셋이다. ① [CentOS Stream](https://www.redhat.com/en/blog/centos-stream-building-innovative-future-enterprise-linux) — 2020년 전환 이후 "RHEL 의 복제본"이 아니라 "다음 RHEL 이 될 코드"(업스트림)로 재정의됐다. 무료지만 RHEL 그 자체는 아니다. ② [Rocky Linux](https://rockylinux.org/)·[AlmaLinux](https://almalinux.org/) — CentOS 소멸 후 나온 커뮤니티 리빌드. 다만 2023년 Red Hat 의 소스 접근 방식 변경 이후 AlmaLinux 는 [1:1 복제를 포기하고 ABI 호환으로 노선을 바꿨다](https://almalinux.org/blog/future-of-almalinux/) — "완전히 같은 바이너리"가 아니라 "애플리케이션이 똑같이 도는 호환 OS"다. ③ 의외로 모르는 사람이 많은 공식 무료 경로 — [Red Hat Developer Subscription for Individuals](https://developers.redhat.com/articles/faqs-no-cost-red-hat-enterprise-linux). 개인 명의로 **진짜 RHEL 을 최대 16대까지 무료**로 쓸 수 있고, Red Hat 스스로 "small production use" 를 허용 용도로 명시한다. 바이너리는 유료 구독과 동일하다.

**Ubuntu 계열.** 배포판 자체가 전부 무료이고, 유료는 [Ubuntu Pro](https://ubuntu.com/pro) 구독 하나로 통일돼 있다. 차이는 보안 패치의 **범위와 기간**이다. [공식 릴리스 주기](https://ubuntu.com/about/release-cycle) 기준 무료 LTS 는 Main 저장소 패키지에 5년 보안 유지보수를 주고, Pro 를 붙이면 Universe 저장소(약 2만+ 패키지)까지 포함해 10년, Legacy 애드온까지 얹으면 최대 15년으로 늘어난다. Livepatch 와 FIPS 140-3 인증 패키지도 Pro 에 묶여 있다. [공개 가격표](https://ubuntu.com/pricing/pro) 기준 셀프서포트가 데스크톱 연 $25, 서버 연 $500(VM 무제한), 24/7 기술지원을 얹으면 서버당 연 $1,775(인프라)~$3,400(풀 스택)이다. 그리고 여기도 공식 무료 경로가 있다 — **개인 용도는 5대까지 Pro 가 무료**다(우분투 커뮤니티 멤버는 50대).

**SUSE 계열.** 구조는 Red Hat 과 같다. 유료 [SLES](https://www.suse.com/products/server/) 와 무료 openSUSE(Leap/Tumbleweed)가 코드 계열을 공유하고, 돈은 수명주기·인증·지원에 낸다.

요컨대 세 진영 모두 같은 문장으로 요약된다: **코드는 무료, 돈은 시간(수명주기)과 책임(지원·인증)에 낸다.**

## 개발·운영자 관점: 언제 유료판이어야 하는가

솔직한 기준선부터. 애플리케이션 입장에서 RHEL 과 AlmaLinux, Ubuntu 무료판과 Pro 는 **API·ABI 수준에서 같은 실행 환경**이다. 컨테이너 시대에는 더 그렇다 — 워크로드가 도커 이미지 안에 들어 있으면 호스트 배포판의 차이는 커널 버전 정도로 좁아진다. 개발자 경험만 놓고 유료판을 살 이유는 사실상 없다.

유료가 필요조건이 되는 경우는 명확히 셋이다.

1. **규제·감사가 배포판 이름을 요구할 때.** FIPS 인증 모듈, 벤더 지원 계약 증빙, 상용 솔루션의 지원 매트릭스("RHEL 8/9 에서만 지원") — 이건 기술이 아니라 문서의 문제고, 무료판으로는 그 문서가 안 나온다.
2. **패치를 10년 받아야 하는 시스템.** 한 번 검증하면 못 건드리는 시스템(금융 코어, 산업 설비)은 "버전 고정 + 보안 백포트 10년"이라는 상품 자체가 필요하다. 무료 LTS 5년으로는 모자라는 지점부터가 유료 구간이다.
3. **OS 장애의 책임 주체가 필요할 때.** 사내에 커널을 디버깅할 인력이 없고, 장애 시 "우리가 벤더에 티켓을 열었다"가 조직적으로 의미를 갖는 곳.

반대로 — 쿠버네티스 노드처럼 **소가 아니라 가축(cattle)으로 다루는 서버**, 즉 죽으면 고치는 게 아니라 갈아끼우는 노드에는 유료 구독의 가치 대부분(장기 수명주기, 개별 장애 지원)이 애초에 성립하지 않는다. 내가 운영하는 홈랩 K3s 6노드가 전부 무료 우분투인 이유이기도 하다 — 노드는 재설치가 복구 절차이고, 이 규모는 어차피 개인 Pro 무료 범위(5대) 언저리다.

## 비용 관점: OS 층은 미들웨어 층보다 싸지만, 대수로 곱해진다

단가만 보면 OS 구독은 오라클에 비하면 푼돈이다 — RHEL 연 $383.90 는 오라클 DB EE 프로세서 라이선스($47,500)의 1% 도 안 된다. 함정은 **곱하는 수가 다르다**는 것. DB 라이선스는 DB 서버에만 붙지만 OS 구독은 전체 서버 대수에 붙는다. 서버 200대면 셀프서포트 최저가 기준으로도 RHEL 연 $76,780, 24/7 지원 티어의 Ubuntu Pro 라면 연 $355,000~$680,000 이다. 그리고 라이선스(1회 구매 + 22% 지원료)가 아니라 **전액이 매년 나가는 구독**이라 5년 TCO 는 단순히 5배다.

절감 판단의 실무 절차는 이렇게 된다.

- **서버를 역할별로 나눈다.** 규제·인증이 배포판 이름을 요구하는 시스템(위의 셋에 해당)만 유료 풀에 남긴다.
- **나머지는 무료 경로의 등급을 고른다.** RHEL 호환이 필요하면 AlmaLinux/Rocky(단, 1:1 이 아니라 ABI 호환임을 알고), 그 제약도 없으면 Ubuntu LTS·Debian. 16대 이하의 실험·소규모 운영이라면 공식 무료 RHEL(개인 개발자 구독)이 가장 정직한 답이다.
- **"5년 뒤"를 미리 계산한다.** 무료 LTS 의 실질 비용은 5년마다 오는 메이저 업그레이드 공수다. 업그레이드를 감당할 자동화(IaC, 이미지 빌드)가 있으면 무료가 싸고, 없으면 Pro/RHEL 의 10년이 그 공수를 돈으로 사는 것이다. 즉 **구독료의 경쟁 상대는 배포판이 아니라 자기 조직의 자동화 수준**이다.

## 정리

- 리눅스 유료판이 파는 것은 코드가 아니라 **수명주기·인증·지원 책임**이다. 그래서 무료판과의 기능 차이는 (의도적으로) 거의 없다.
- 오라클 편과 같은 결론이 OS 층에서도 성립한다 — 책임 요건이 있는 조직은 사야 하고, 없는 조직이 관성으로 사고 있다면 그 구독은 매년 전액이 새는 비용이다.
- 다만 리눅스가 미들웨어·DB 와 결정적으로 다른 점: **무료 경로가 벤더 공식이다.** RHEL 16대 무료(소규모 프로덕션 포함 명시), Ubuntu Pro 개인 5대 무료 — 벤더 스스로 "이 범위는 돈 내지 마라"고 선을 그어 놓았다. 그 선 안에 있는데 돈을 내고 있다면, 그건 안전이 아니라 낭비다.

## References

- kernel.org, [Frequently Asked Questions](https://www.kernel.org/category/faq.html) — 커널의 GPL v2 라이선스
- Red Hat Store, [Red Hat Enterprise Linux Server](https://store.redhat.com/en/products/red-hat-enterprise-linux-server) — "Starting at US$383.90" (2026-09-13 실측)
- Red Hat, [Red Hat Enterprise Linux Life Cycle](https://access.redhat.com/support/policy/updates/errata) — 10년 수명주기
- Red Hat 공식 블로그, [CentOS Stream: Building an innovative future for enterprise Linux](https://www.redhat.com/en/blog/centos-stream-building-innovative-future-enterprise-linux) (2020)
- Red Hat Developer, [No-cost RHEL Individual Developer Subscription: FAQs](https://developers.redhat.com/articles/faqs-no-cost-red-hat-enterprise-linux) — 16대·소규모 프로덕션 허용
- AlmaLinux 공식 블로그, [The Future of AlmaLinux is Bright](https://almalinux.org/blog/future-of-almalinux/) (2023) — 1:1 → ABI 호환 전환
- Rocky Linux, [rockylinux.org](https://rockylinux.org/)
- Canonical, [Ubuntu release cycle](https://ubuntu.com/about/release-cycle) — LTS 5년, Pro 10년, Legacy 최대 15년
- Canonical, [Ubuntu Pro](https://ubuntu.com/pro) — 개인 5대 무료
- Canonical, [Ubuntu Pro pricing](https://ubuntu.com/pricing/pro) — 데스크톱 $25·서버 $500·지원 티어 $1,775~$3,400 (2026-09-13 실측)
- SUSE, [SUSE Linux Enterprise Server](https://www.suse.com/products/server/)

*가격은 모두 각 벤더 공개 페이지에서 글 작성일에 직접 확인한 정가(USD)이며, 실구매가는 volume 협상에 따라 달라진다. RHEL 과 리빌드 배포판 간의 중립적 성능 비교는 의미 있는 공개 자료가 없다 — 같은 코드 계열이라 성능이 아니라 지원·수명주기가 비교축이다.*
