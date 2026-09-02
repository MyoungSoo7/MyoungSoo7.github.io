---
layout: post
title: Java의 역사 — Oak에서 현대까지
date: 2026-09-02 22:59:04 +0900
categories: [Java]
tags: [java, history, programming-language, sun-microsystems]
---

## 초기 — Oak와 Green Project (1990–1995)

Java의 시작은 Oak라는 프로젝트명으로 거슬러 올라간다. Sun Microsystems의 James Gosling, Mike Sheridan, Patrick Naughton은 1990년대 초반부터 [가정용 전자제품에 탑재할 수 있는 플랫폼 독립적인 프로그래밍 언어](https://docs.oracle.com/javase/tutorial/java/nutsandbolts/index.html)를 개발하기 시작했다. 당시 목표는 TV, 냉장고, 오디오 기기 같은 장비를 제어할 수 있는 상호운용 가능한 시스템을 만드는 것이었다.

Oak라는 이름은 회사 근처의 참나무에서 영감을 받았으며, 나중에 상표권 충돌로 인해 **Green**으로 개명되었다. 그리고 마침내 **Java**라는 이름이 정해졌는데, 개발 팀이 즐겨 마시던 커피의 산지인 자바 섬에서 비롯되었다.

## 공식 공개 (1995–1996)

Sun Microsystems는 1995년 5월 23일 Java를 공식 공개했다. 이는 Netscape와의 전략적 제휴를 통해 웹 브라우저에서 실행할 수 있는 애플릿(applet) 형태로 소개되었다. "**Write Once, Run Anywhere (WORA)**" 라는 슬로건이 Java의 핵심 철학을 대변했다 — 한 번 작성하면 Java Virtual Machine(JVM)이 설치된 모든 플랫폼에서 실행된다는 개념이었다.

1996년 1월, **JDK 1.0** (Java Development Kit)이 정식 출시되었다. 이는 Java 컴파일러, 런타임, 그리고 기본 라이브러리를 포함했다.

## 1990년대 후반 — 엔터프라이즈로의 진입

1998년 **J2SE 1.2** (Java 2 Standard Edition)가 출시되면서 Java는 단순한 웹 애플릿 언어에서 벗어나 서버 측 애플리케이션, 데스크톱 애플리케이션 개발이 가능한 범용 언어로 진화했다.

이 시기에 다음이 추가되었다:
- **Swing** — 크로스 플랫폼 GUI 라이브러리
- **Collections API** — 데이터 구조 표준화
- **Reflection API** — 런타임 자기 검사(introspection) 기능

## 2000년대 — 엔터프라이즈 표준으로의 확립

2000년대는 Java가 엔터프라이즈 백엔드 개발의 사실상 표준이 되던 시기다.

**2004년 J2SE 1.5 (Tiger)** 는 게임체인저였다:
- **Generics** — 타입 안정성 강화
- **Annotations** — 메타데이터 선언
- **Varargs** — 가변 인자
- **Enum** — 열거형
- **Enhanced for loop** — for-each 루프

이 버전은 Java의 역사에서 가장 큰 언어 개선 중 하나로 평가된다.

Sun Microsystems는 또한 서버 측 개발을 위해 **J2EE (Java 2 Enterprise Edition)** 를 정의했고, 이는 EJB, Servlet, JSP 등의 표준을 포함했다. Tomcat, JBoss, WebLogic 같은 애플리케이션 서버들이 뒤따랐다.

## 2007년 — 오픈소스로의 전환

2006년 Sun Microsystems는 Java를 **GNU General Public License (GPL)** 로 오픈소스화하기로 결정했다. 이는 Java 생태계에 큰 영향을 미쳤으며, 오픈소스 커뮤니티의 참여를 폭발적으로 증가시켰다.

## 2008년 이후 — Java 모던화

**2008년 Java 6** 부터 버전 번호 체계가 단순화되기 시작했다. 이후:

- **2011년 Java 7** — NIO.2, Fork/Join Framework
- **2014년 Java 8** — **Lambda expressions, Stream API** 가 함수형 프로그래밍 패러다임 도입
- **2017년 Java 9** — **Module System (Project Jigsaw)** 추가

## 2018년 이후 — 빠른 릴리스 사이클

Oracle이 Sun을 인수한 후, Java는 **6개월마다 새 버전을 출시** 하는 방식으로 변경되었다:

- 짝수 버전 (8, 11, 17, 21, ...) — **LTS (Long Term Support, 5년 지원)**
- 홀수 버전 — 단기 지원 (6개월)

**Java 11 (2018)** 과 **Java 17 (2021)** 은 LTS 버전으로 광범위하게 채택되었다.

최근 버전들:
- **Java 21 (2023, LTS)** — 가상 스레드(Virtual Threads), 기록(Records), 패턴 매칭
- **Java 25 (2025, 최신)** — 추가 미리보기 기능들

## 현재의 Java

2026년 현재 Java는:
- **클라우드 네이티브** 개발의 핵심 언어 (Spring Boot, Quarkus)
- **Kubernetes** 환경에서의 컨테이너 기반 마이크로서비스 개발
- **대규모 엔터프라이즈** 백엔드 시스템의 표준
- **금융, 전자상거래, 텔레콤** 등 미션 크리티컬 시스템에서 광범위하게 사용

여전히 가장 널리 사용되는 프로그래밍 언어 중 하나이며, JVM 생태계(Kotlin, Scala, Clojure)의 기반을 제공한다.

## References

- [The Java Language](https://docs.oracle.com/javase/tutorial/) — Oracle Official Java Tutorial
- [Java Platform, Standard Edition Documentation](https://docs.oracle.com/javase/17/)
- [Java Release Notes](https://www.oracle.com/java/technologies/javase-jdk-archive-downloads.html)
