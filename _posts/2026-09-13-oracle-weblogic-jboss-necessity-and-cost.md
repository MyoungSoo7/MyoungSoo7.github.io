---
layout: post
title: "오라클·웹로직·JBoss 는 아직 필요한가 — 개발자의 관점과 비용의 관점"
date: 2026-09-13 04:25:35 +0900
categories: [java, infra]
tags: [oracle, weblogic, jboss, wildfly, spring-boot, postgresql, licensing, tco]
---

한국 SI·금융권에서 "엔터프라이즈 자바"는 오랫동안 하나의 정형이었다. DB 는 오라클, WAS 는 웹로직 아니면 JBoss, 그 위에 자바 애플리케이션. 셋 다 돈을 내는 제품이고, 그 비용은 시스템 규모에 따라 수억 원 단위로 커진다. 그런데 지금 새 시스템을 설계한다면 이 셋에 돈을 낼 이유가 얼마나 남아 있을까. 자바 백엔드 개발자의 관점과 비용의 관점, 두 축으로 따져 본다.

가격은 전부 오라클이 공개한 [Oracle Technology Global Price List](https://www.oracle.com/corporate/pricing/) **2026년 8월 3일자 문서에서 직접 확인한 정가(USD)** 다. 실구매가는 협상 할인이 붙으므로 이보다 낮은 게 보통이지만, 할인율은 공개되지 않으니 비교의 기준선은 정가로 잡는 것이 정직하다.

## 세 제품은 각각 무엇을 파는가

**오라클 DB.** Enterprise Edition 이 **프로세서당 $47,500**, 연간 지원료(Software Update License & Support)가 **$10,450 — 정확히 라이선스의 22%** 다. 여기서 "프로세서"는 물리 CPU 개수가 아니라 **코어 수 × 코어 팩터**로, 인텔 제온·AMD EPYC 등 x86 서버 칩의 팩터는 [공식 코어 팩터 표](https://www.oracle.com/us/corporate/contracts/processor-core-factor-table-070634.pdf) 기준 0.5 다. 그리고 EE 가격에는 고가용성(RAC, **+$23,000/프로세서**)도 파티셔닝(**+$11,500/프로세서**)도 포함돼 있지 않다 — 전부 별매 옵션이다. 하드웨어 제약을 받는 대신 싼 Standard Edition 2($17,500/프로세서)가 있지만, RAC 같은 EE 옵션은 붙일 수 없다([라이선스 문서](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)).

**웹로직.** 같은 가격표에서 Standard Edition **$10,000**, Enterprise Edition **$25,000**(클러스터링 포함), WebLogic Suite **$45,000**(Coherence 포함) — 모두 프로세서당이고 지원료 22% 구조도 동일하다.

**JBoss EAP.** 구조가 다르다. Red Hat 의 [JBoss Enterprise Application Platform](https://www.redhat.com/en/technologies/jboss-middleware/application-platform) 은 라이선스를 파는 게 아니라 **구독(subscription)** 을 판다. 코드 자체는 오픈소스이고 업스트림 커뮤니티 프로젝트인 [WildFly](https://www.wildfly.org/) 로 공개돼 있다. 즉 JBoss EAP 에 내는 돈의 대상은 소프트웨어가 아니라 **테스트·패치·보안 대응·수명주기 보장과 기술지원**이다. 구독료는 공개 정가표가 없어(영업 견적) 이 글의 수치 비교에서는 제외한다.

## 개발자 관점: WAS 가 팔던 것은 이미 언어·프레임워크로 내려왔다

웹로직과 JBoss 같은 풀스택 WAS 가 팔던 가치는 분명했다. 분산 트랜잭션(JTA/2PC), EJB 컨테이너, 세션 클러스터링, 관리 콘솔, 그리고 "벤더가 인증하고 책임지는 실행 환경". 2000년대의 자바 백엔드는 이 컨테이너 없이는 성립하지 않았다.

지금은 두 가지가 근본적으로 바뀌었다.

첫째, **배포 모델이 뒤집혔다.** Spring Boot 는 톰캣·제티·언더토우를 애플리케이션 안에 내장해 실행하는 것이 기본이고, WAR 를 만들어 외부 WAS 에 얹는 쪽이 오히려 예외 경로다([Spring Boot 공식 문서](https://docs.spring.io/spring-boot/how-to/webserver.html)). 서블릿 컨테이너로 충분한 워크로드에는 무료인 [Apache Tomcat](https://tomcat.apache.org/) 이 사실상 표준이 됐고, 컨테이너(도커)·쿠버네티스 환경에서는 "앱 = 프로세스 하나"라는 내장형 모델이 운영 모델과도 맞아떨어진다.

둘째, **스펙의 주도권이 벤더를 떠났다.** Java EE 는 오라클 손을 떠나 Eclipse 재단의 [Jakarta EE](https://jakarta.ee/about/) 가 됐다. "표준 엔터프라이즈 자바 = 상용 앱서버" 라는 등식이 성립하던 제도적 기반 자체가 사라진 것이다.

그렇다고 개발자 관점에서 유료 제품의 필요가 0 이 됐다는 뜻은 아니다. 남는 경우는 대략 셋이다.

1. **레거시 결합.** EJB, JTA 분산 트랜잭션, 벤더 고유 디스크립터에 깊이 묶인 기존 시스템은 WAS 를 걷어내는 비용이 유지 비용보다 클 수 있다.
2. **지원과 책임의 요건.** 장애 시 벤더 SLA 지원이 감사·규제·계약상 요구되는 조직이라면, JBoss EAP 모델(오픈소스 + 유료 지원)이 정확히 그 요건을 겨냥한 상품이다. WildFly 를 쓰면 코드 계열은 같지만 그 책임 주체가 없다.
3. **오라클 DB 의 자산.** 수십만 줄의 PL/SQL, RAC 전제의 HA 설계, 오라클 특화 튜닝 노하우는 실재하는 자산이다. 반면 신규 시스템 기준으로 보면 PostgreSQL 이 대부분의 백엔드 워크로드를 커버하고, 라이선스는 [자유·무료](https://www.postgresql.org/about/licence/)다. 어느 쪽이 맞는지는 기술 우열이 아니라 **가진 자산의 크기**가 결정한다. (오라클과 PostgreSQL 의 중립적 헤드투헤드 성능 비교는 신뢰할 만한 공개 자료가 없다 — 성능을 근거로 어느 쪽을 단정하는 글은 걸러 읽는 게 좋다.)

## 비용 관점: 22% 가 복리처럼 쌓인다

정가표 숫자로 보수적인 예를 하나만 계산해 본다. x86 32코어 서버 1대(코어 팩터 0.5 → **16 프로세서 라이선스**) 기준:

| 항목 | 라이선스(1회) | 지원료(매년) |
| --- | --- | --- |
| 오라클 DB EE | 16 × $47,500 = **$760,000** | $167,200 |
| + RAC 옵션 | 16 × $23,000 = **$368,000** | $80,960 |
| 웹로직 EE | 16 × $25,000 = **$400,000** | $88,000 |

DB EE + RAC + 웹로직 EE 조합이면 라이선스만 약 **$1.53M**, 지원료가 **매년 약 $336K** 다. 5년을 운영하면 지원료 누계가 라이선스의 110% — **처음 산 값을 5년마다 한 번씩 다시 내는 구조**다. 게다가 RAC 는 노드 수만큼 라이선스가 배수로 붙고, 클라우드로 옮겨도 오라클 라이선스 산정 규칙은 vCPU 를 따라온다. 코어가 늘어나는 요즘 하드웨어 추세에서 "프로세서당 과금 × 코어 팩터" 모델은 시간이 갈수록 구매자에게 불리해지는 방향이다.

이 표에서 비용 절감의 우선순위도 자연히 나온다.

- **가장 이행이 쉬운 층은 WAS 다.** 애플리케이션이 이미 Spring Boot 라면 웹로직이 하는 일은 서블릿 컨테이너 + 운영 콘솔 정도로 줄어 있는 경우가 많다. 내장 톰캣으로 가면 $400K + 연 $88K 항목이 0 이 되고, 표준 Jakarta EE 기능이 필요하면 WildFly 라는 무료 경로가 있다. "지원은 필요하다" 면 JBoss EAP 구독이 라이선스 모델보다 예측 가능한 절충안이다.
- **DB 는 자산 규모가 손익분기를 정한다.** PL/SQL·튜닝 자산이 얇은 신규 시스템이라면 PostgreSQL 로 시작해 위 표의 가장 큰 두 줄을 지울 수 있다. 반대로 자산이 두꺼운 시스템의 강제 이관은 마이그레이션 비용(재작성·검증·병행 운영)이 라이선스 절감을 넘어설 수 있다 — 절감액만 보고 결정하면 안 되는 이유다.
- **현실적인 전략은 전면 탈피가 아니라 신규부터 비종속이다.** 기존 시스템은 지원 계약을 유지하되, 새로 짓는 시스템의 기본값을 "PostgreSQL + 내장 컨테이너"로 두면 유료 스택의 면적이 시간이 지나며 자연 감소한다.

## 정리

- **개발자 관점**: WAS 가 팔던 기능적 가치는 대부분 프레임워크(내장 컨테이너)와 오픈소스(WildFly)로 내려왔다. 남는 구매 이유는 기능이 아니라 **레거시 결합과 지원 책임**이다. 오라클 DB 는 예외적으로 기능 자산(PL/SQL·RAC)이 여전히 실질 가치지만, 그 가치는 신규 시스템에는 승계되지 않는다.
- **비용 관점**: 정가 기준 프로세서당 과금 + 연 22% 지원료 구조는 5년 주기로 라이선스를 다시 사는 것과 같다. 절감은 WAS 층에서 시작해서, DB 층은 자산 크기와 마이그레이션 비용을 저울질해 결정한다.
- 요약하면 — **"필요한가"의 답은 제품이 아니라 조직에 달려 있다.** 벤더가 책임져야 하는 조직은 여전히 사야 하고, 그 요건이 없는 조직이 관성으로 사고 있다면 그 돈은 매년 22%씩 새고 있는 것이다.

## References

- Oracle, [Oracle Technology Global Price List](https://www.oracle.com/corporate/pricing/) (2026-08-03자 PDF, 본문 가격 전부 이 문서에서 실측)
- Oracle, [Processor Core Factor Table](https://www.oracle.com/us/corporate/contracts/processor-core-factor-table-070634.pdf)
- Oracle, [Database Licensing Information User Manual (19c)](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)
- Red Hat, [JBoss Enterprise Application Platform](https://www.redhat.com/en/technologies/jboss-middleware/application-platform)
- WildFly 프로젝트, [wildfly.org](https://www.wildfly.org/)
- Spring Boot 공식 문서, [Embedded Web Servers](https://docs.spring.io/spring-boot/how-to/webserver.html)
- Apache Software Foundation, [Apache Tomcat](https://tomcat.apache.org/)
- Eclipse Foundation, [About Jakarta EE](https://jakarta.ee/about/)
- PostgreSQL Global Development Group, [PostgreSQL Licence](https://www.postgresql.org/about/licence/)

*JBoss EAP 구독료는 공개 정가표가 없어 수치 비교에서 제외했다. 표의 계산은 정가 기준이며 실구매가는 협상에 따라 달라진다.*
