---
layout: post
title: "WildFly 41 — 애플리케이션 서버는 메이저 스펙 전환을 어떻게 배포 전략으로 푸는가"
date: 2026-09-19 04:47:00 +0900
categories: [backend]
tags: [wildfly, jakarta-ee, ee11, java, was, galleon, redhat]
---

앞서 [JBoss · WildFly · Tomcat 층위 정리](/2026/09/15/jboss-wildfly-tomcat-three-way/)에서 "무엇과 무엇을 비교해야 하는지"를 다뤘다. 이번 글은 WildFly 하나를 깊게 본다. 2026년 WildFly 는 프로젝트 역사에서 몇 안 되는 **메이저 스펙 세대 교체** — Jakarta EE 10 → EE 11 — 를 통과하는 중인데, 그 과정 자체가 "호환성을 깨는 전환을 어떻게 사용자에게 강요하지 않고 넘기는가"의 교과서적 사례라서다. 벤치마크 숫자는 이번에도 없다. 전부 wildfly.org 공식 발표문과 릴리스 노트에서 확인한 사실만 쓴다.

---

## 1. 2026년 타임라인 — 세 번의 릴리스

| 날짜 | 릴리스 | 핵심 |
| --- | --- | --- |
| 2026-05-21 | **WildFly 40** | 표준 배포판이 **EE 11 로 전환**. 동시에 임시 "WildFly EE 10" 변형 신설 |
| 2026-07-16 | **WildFly 41** | 정상 분기 주기 복귀. 클라우드 bootable jar, JDK 25 이미지 |
| 2026-08-27 | **WildFly 41.0.1** | 버그픽스 (EE 10/EE 11 양쪽 컴포넌트 동시 패치) |

WildFly 는 원래 **1월/4월/7월/10월 분기 릴리스**가 표준 주기다. WildFly 40 은 EE 11 지원을 릴리스 조건으로 걸었기 때문("feature-boxed") 한 달 넘게 늦은 5월에 나왔고, 41 에서 개발 기간을 줄여 7월 주기로 복귀했다.[^wf41]

## 2. 전환의 3단 구조 — Preview 부화 → 본선 교체 → 임시 변형

WildFly 가 EE 11 로 넘어간 방식은 세 단계다.

**① Preview 에서 부화.** WildFly 는 표준 배포판과 별개로 **WildFly Preview** 라는 기술 미리보기 배포판을 항상 같이 낸다. EE 11 구현은 WildFly Preview 32 부터 Preview 에만 먼저 실렸고, 여덟 개 버전에 걸쳐 부화한 뒤에야 본선에 들어왔다.[^wf40] 스펙 구현이 성숙하기 전에 표준 사용자를 실험대에 올리지 않는다는 얘기다.

**② 본선 교체.** WildFly 40 에서 표준 배포판(대부분의 사용자가 쓰는 `wildfly-ee` feature-pack)이 EE 11 API 를 제공하도록 바뀌었다.[^wf40]

**③ 갈아탈 시간을 파는 임시 변형.** 여기가 흥미로운 부분이다. 표준이 EE 11 로 가는 순간 EE 10 에 묶인 사용자는 낙오된다. WildFly 는 이를 위해 **`wildfly-ee-10` feature-pack** (Maven GAV `org.wildfly:wildfly-ee-10-feature-pack`)과 그걸로 빌드한 서버 zip/tar 를 따로 낸다. EE API 만 10 에 고정하고, **EE 와 무관한 기능·버그픽스는 최신 릴리스와 공유**한다.[^wf41] 그리고 수명을 처음부터 못박았다 — 40.0.0 / 40.0.1 / 41.0.0 / 41.0.1 네 번만 내고, **2026년 가을 WildFly 42 에서 폐지**한다.[^wf41] "임시 지원을 열어두되 끝을 명시해서 이주를 미루지 못하게 한다"는 설계다.

## 3. EE 11 로 가면 뭐가 달라지나

WildFly 40 발표문이 꼽은 EE 11 의 핵심은 두 가지다.[^wf40]

- **Jakarta Data** — 영속성 계층의 repository 패턴이 표준 스펙이 됐다. WildFly 구현체는 Hibernate Data Repositories. Spring Data 스타일의 인터페이스 선언형 repository 를 표준 EE 에서 쓰게 된 것.
- **Jakarta Persistence 3.2** — 다수의 개선.

한 가지 함정도 발표문에 명시돼 있다. EE 11 은 XML·Webservices 계열 스펙 다수를 **플랫폼에서 제거**했다. 다만 해당 스펙들은 독립 Jakarta 스펙으로 존속하고, WildFly 는 서브시스템을 기본 설정에 그대로 유지한 채 계속 지원한다.[^wf40] "스펙에서 빠짐 = 서버에서 사라짐"이 아니다.

## 4. WildFly 41 자체의 변화

짧은 개발 주기였는데도 목록이 실하다.[^wf41]

- **클라우드 bootable jar** — `wildfly-cloud-galleon-pack` + `wildfly-maven-plugin` 조합으로 클라우드 최적화가 적용된 bootable jar 패키징 지원. 앱서버를 단일 실행 jar 로 말아 컨테이너에 넣는 경로가 정식으로 넓어졌다.
- **JDK 25 컨테이너 이미지** — JDK 25 기반 컨테이너/S2I 빌더/런타임 이미지 신설. **기존 JDK 17 이미지는 더 이상 갱신되지 않는다.** 베이스도 `ubi9-minimal` → `ubi10-minimal` 로 이동.
- **안정성 등급 승급** — WildFly 는 기능마다 `preview` → `community` → `default` 안정성 등급을 붙이는데, OIDC 추가 scope 설정·서명/암호화된 OIDC 요청 객체(→ community), JGroups TCP 전송 TLS·OIDC 로그아웃(→ default)이 승급했다.
- **운영 디테일 두 가지** — JGroups `FD_SOCK2` 장애감지 포트를 OS ephemeral 포트 대역 밖으로 옮겨 충돌을 막았고(`port_range` 0 으로 결정적 바인딩), `transactions` 서브시스템에 `transactions-recovery-graceful-shutdown` 속성을 추가해 graceful shutdown 중에도 트랜잭션 복구가 계속 돌게 할 수 있다. 진행 중 트랜잭션의 데이터 손실 방지 목적.
- **CVE 대응 의존성 일괄 업그레이드** — Apache MINA SSHD 2.18.0 (CVE-2026-48827), Artemis 2.54 (CVE-2026-32642), CXF·Jackson·Netty 다수 CVE 해소, Hibernate ORM 7.4.5 등.

## 5. Java SE 지원 — 권고와 인증을 분리해서 말한다

WildFly 41 의 SE 정책은 문구가 정직해서 그대로 옮길 가치가 있다.[^wf41]

- **실행 권고: SE 25** (최신 LTS 라는 일반 원칙 때문).
- **EE 11 호환성 인증: SE 17 / SE 21 에서만.** 발표문 원문 — "We do not claim to be compatible with EE 11 on SE 25." TCK 를 SE 25 에서 돌려본 결과에 만족해서 권고는 하지만, 인증 주장은 하지 않는다. TCK 통과가 중요한 조직은 17/21 을 쓰라고 명시한다.
- 인증 증빙은 [WildFly Certifications 리포](https://github.com/wildfly/certifications)에 공개돼 있다.

"권장 버전"과 "호환성을 주장하는 버전"을 분리해서 말하는 벤더는 드물다. 이 구분을 안 하는 문서를 읽을 때 무엇을 의심해야 하는지 보여주는 반례이기도 하다.

## 6. 다음 순서 — EE 12 는 이미 줄 서 있다

WildFly Preview 42 부터 EE 12 API 의 초기 마일스톤을 Preview 에 넣기 시작할 계획이라고 41 발표문에 예고돼 있다.[^wf41] 즉 ①Preview 부화 → ②본선 교체 → ③임시 변형이라는 사이클이 EE 12 에서 그대로 반복될 것이다. WildFly 42(2026년 가을)에서 EE 10 변형이 폐지되는 것과 맞물려, 한 릴리스 안에서 "직전 세대의 퇴장"과 "다음 세대의 입장"이 동시에 일어난다.

## 정리

WildFly 의 EE 11 전환에서 가져갈 수 있는 일반 교훈은 배포 전략 그 자체다.

1. **깨지는 변화는 별도 채널에서 오래 부화시킨다** (Preview 32→40, 여덟 버전).
2. **전환 시점엔 구세대 변형을 임시로 병행하되, 폐지 시점을 처음부터 공표한다** (EE 10 변형, 42 에서 폐지).
3. **권고와 인증을 분리해서 말한다** (SE 25 권고 / SE 17·21 인증).

프레임워크든 사내 플랫폼이든, 메이저 버전을 올릴 때 이 세 가지를 갖추면 사용자를 절벽에서 밀지 않고 이주시킬 수 있다.

---

## References

- Brian Stansberry, [WildFly 40 is released!](https://www.wildfly.org/news/2026/05/21/WildFly-40-is-released/) — wildfly.org, 2026-05-21
- Brian Stansberry, [WildFly 41 is released!](https://www.wildfly.org/news/2026/07/16/WildFly-41-is-released/) — wildfly.org, 2026-07-16
- Darran Lofthouse, [WildFly 41.0.1 is released!](https://www.wildfly.org/news/2026/08/27/WildFly-41-0-1-is-released/) — wildfly.org, 2026-08-27
- [WildFly Downloads](https://www.wildfly.org/downloads/) — 배포판 목록 (standard / EE10 / Preview)
- [WildFly Certifications](https://github.com/wildfly/certifications) — EE 호환성 증빙 리포

[^wf40]: Brian Stansberry, "WildFly 40 is released!", wildfly.org, 2026-05-21.
[^wf41]: Brian Stansberry, "WildFly 41 is released!", wildfly.org, 2026-07-16.
