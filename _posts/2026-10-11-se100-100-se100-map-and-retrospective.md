---
layout: post
title: "[SE100 #100] 소프트웨어 공학 100편 — 전체 지도와 정리"
date: 2026-10-11 17:13:28 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, roadmap, software-engineering, index]
---

소프트웨어 공학 100 주제 시리즈의 100번째이자 마지막 글이다. 앞의 99편을 한 장의 지도로 묶고, 읽는 순서와 전체를 꿰는 질문을 정리한다.

## 한 줄 요약

소프트웨어 공학은 "코드를 잘 짜는 법" 이 아니라 **여러 사람이 오랜 시간 동안 바뀌는 요구에 맞춰 믿을 만한 소프트웨어를 만들고 고쳐 나가는 법**이다. 100편은 그 일을 무엇을(요구사항), 어떻게 나누고(설계), 어떻게 짜고(구현), 어떻게 믿고(테스트·품질), 어떻게 내보내고(전달), 어떻게 일하고(프로세스·관리), 어떻게 오래 살리는가(유지보수·사람)로 쪼개 본 것이다.

## 이 시리즈의 위치

컴퓨터공학 전반을 다룬 [CS300 시리즈]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %})의 Part 10(181–200)이 소프트웨어 공학의 기초 — 생명주기, 애자일·스크럼, SOLID, 디자인 패턴, TDD, Git, CI/CD, DDD, 기술 부채 — 를 다뤘다. SE100 은 그 위에서 한 단계 내려가, **원전과 표준과 실무 판단**을 중심에 뒀다.

- 원전: Brooks, Parnas, Royce, Lehman, Conway, Boehm, Fagan 같은 1960~80년대 논문을 직접 읽고, 흔히 알려진 요약과 원문이 어디서 갈라지는지 짚었다. (#002, #004, #006, #009 가 대표적이다.)
- 표준: ISO/IEC 25010, ISO/IEC/IEEE 29148·42010·14764, IEEE 730, DO-178C 같은 표준이 무엇을 요구하고 무엇은 요구하지 않는지 구분했다.
- 실무 판단: 각 글의 "흔한 오해와 함정" 섹션에 도구나 기법을 잘못 쓰는 전형적 방식을 모았다.

분류는 IEEE Computer Society 의 [SWEBOK Guide V4.0](https://www.computer.org/education/bodies-of-knowledge/software-engineering/v4) 지식 영역을 참고했지만 그대로 따르지는 않았다. SWEBOK 자체는 #005 에서 다뤘다.

## 전체 지도

### Part 1. 기초와 역사 (001–010)

소프트웨어 공학이라는 말이 왜 생겼고, 반세기 전 고전들이 지금도 왜 유효한지.

| 번호 | 주제 |
|---|---|
| 001 | [소프트웨어 공학의 탄생 — 1968 NATO 회의와 소프트웨어 위기]({% post_url 2026-10-11-se100-001-software-engineering-origins-nato-1968 %}) |
| 002 | [No Silver Bullet — 본질적 복잡성과 우연적 복잡성]({% post_url 2026-10-11-se100-002-no-silver-bullet %}) |
| 003 | [맨먼스 미신과 Brooks 의 법칙]({% post_url 2026-10-11-se100-003-mythical-man-month-brooks-law %}) |
| 004 | [Parnas 의 정보 은닉 — 모듈을 나누는 기준]({% post_url 2026-10-11-se100-004-parnas-information-hiding %}) |
| 005 | [SWEBOK — 소프트웨어 공학 지식 체계]({% post_url 2026-10-11-se100-005-swebok-body-of-knowledge %}) |
| 006 | [Lehman 의 소프트웨어 진화 법칙]({% post_url 2026-10-11-se100-006-lehman-laws-of-software-evolution %}) |
| 007 | [Conway 의 법칙 — 조직 구조가 시스템 구조가 된다]({% post_url 2026-10-11-se100-007-conways-law %}) |
| 008 | [소프트웨어 공학 윤리 — ACM/IEEE-CS 윤리 강령]({% post_url 2026-10-11-se100-008-acm-ieee-software-engineering-ethics %}) |
| 009 | [폭포수의 오해 — Royce 1970 원문 다시 읽기]({% post_url 2026-10-11-se100-009-royce-1970-waterfall-misread %}) |
| 010 | [실패에서 배우기 — Therac-25 와 Ariane 5]({% post_url 2026-10-11-se100-010-therac25-ariane5-case-studies %}) |

### Part 2. 요구사항 공학 (011–020)

무엇을 만들지 정하는 일. 대부분의 재작업은 여기서 시작된다.

| 번호 | 주제 |
|---|---|
| 011 | [요구사항 공학 프로세스 — 도출·분석·명세·검증]({% post_url 2026-10-11-se100-011-requirements-engineering-process %}) |
| 012 | [비기능 요구사항과 ISO/IEC 25010 품질 모델]({% post_url 2026-10-11-se100-012-nonfunctional-requirements-iso25010 %}) |
| 013 | [유스케이스 제대로 쓰기 — Cockburn 방식]({% post_url 2026-10-11-se100-013-use-case-writing-cockburn %}) |
| 014 | [사용자 스토리와 INVEST 기준]({% post_url 2026-10-11-se100-014-user-stories-invest %}) |
| 015 | [인수 기준과 BDD — Given-When-Then]({% post_url 2026-10-11-se100-015-acceptance-criteria-bdd-gherkin %}) |
| 016 | [좋은 요구사항 문장 — ISO/IEC/IEEE 29148]({% post_url 2026-10-11-se100-016-iso-29148-requirements-specification %}) |
| 017 | [요구사항 우선순위 — MoSCoW 와 Kano 모델]({% post_url 2026-10-11-se100-017-prioritization-moscow-kano %}) |
| 018 | [이벤트 스토밍으로 도메인 발견하기]({% post_url 2026-10-11-se100-018-event-storming-domain-discovery %}) |
| 019 | [요구사항 추적성 — 요구에서 테스트까지]({% post_url 2026-10-11-se100-019-requirements-traceability %}) |
| 020 | [프로토타이핑과 요구사항 검증]({% post_url 2026-10-11-se100-020-prototyping-requirements-validation %}) |

### Part 3. 설계와 아키텍처 (021–030)

시스템을 어떻게 나누고, 그 결정을 어떻게 기록하고 평가하는가.

| 번호 | 주제 |
|---|---|
| 021 | [응집도와 결합도 — 설계 품질의 두 축]({% post_url 2026-10-11-se100-021-cohesion-and-coupling %}) |
| 022 | [소프트웨어 아키텍처란 — ISO/IEC/IEEE 42010]({% post_url 2026-10-11-se100-022-what-is-software-architecture-42010 %}) |
| 023 | [4+1 뷰 모델 — 아키텍처를 여러 시점으로]({% post_url 2026-10-11-se100-023-kruchten-4plus1-view-model %}) |
| 024 | [C4 모델로 아키텍처 그리기]({% post_url 2026-10-11-se100-024-c4-model %}) |
| 025 | [아키텍처 결정 기록(ADR)]({% post_url 2026-10-11-se100-025-architecture-decision-records %}) |
| 026 | [품질 속성 시나리오와 ATAM]({% post_url 2026-10-11-se100-026-quality-attributes-atam %}) |
| 027 | [헥사고날·클린 아키텍처 — 포트와 어댑터]({% post_url 2026-10-11-se100-027-hexagonal-and-clean-architecture %}) |
| 028 | [이벤트 기반 아키텍처와 CQRS·이벤트 소싱]({% post_url 2026-10-11-se100-028-event-driven-architecture-cqrs %}) |
| 029 | [API 설계 — 리소스 모델·버전·하위 호환성]({% post_url 2026-10-11-se100-029-api-design-compatibility %}) |
| 030 | [계약에 의한 설계 — 사전조건·사후조건·불변식]({% post_url 2026-10-11-se100-030-design-by-contract %}) |

### Part 4. 구현과 코드 품질 (031–040)

코드 한 줄 수준에서 변경 비용을 낮추는 습관과 도구.

| 번호 | 주제 |
|---|---|
| 031 | [코딩 컨벤션과 정적 분석]({% post_url 2026-10-11-se100-031-coding-conventions-static-analysis %}) |
| 032 | [코드 스멜 카탈로그 — 무엇이 냄새인가]({% post_url 2026-10-11-se100-032-code-smells-catalog %}) |
| 033 | [순환 복잡도와 코드 메트릭]({% post_url 2026-10-11-se100-033-cyclomatic-complexity-code-metrics %}) |
| 034 | [방어적 프로그래밍과 에러 처리 전략]({% post_url 2026-10-11-se100-034-defensive-programming-error-handling %}) |
| 035 | [불변성과 부수효과 관리]({% post_url 2026-10-11-se100-035-immutability-and-side-effects %}) |
| 036 | [의존성 주입과 제어의 역전]({% post_url 2026-10-11-se100-036-dependency-injection-ioc %}) |
| 037 | [레거시 코드 다루기 — 심(seam)과 특성 테스트]({% post_url 2026-10-11-se100-037-working-with-legacy-code-seams %}) |
| 038 | [페어 프로그래밍과 몹 프로그래밍]({% post_url 2026-10-11-se100-038-pair-and-mob-programming %}) |
| 039 | [주석과 API 문서 — 무엇을 왜 남기는가]({% post_url 2026-10-11-se100-039-comments-and-api-documentation %}) |
| 040 | [의존성 관리와 시맨틱 버저닝]({% post_url 2026-10-11-se100-040-dependency-management-semver %}) |

### Part 5. 소프트웨어 테스팅 (041–050)

무엇을, 어디까지, 어떤 기법으로 확인해야 "믿을 만하다" 고 말할 수 있는가.

| 번호 | 주제 |
|---|---|
| 041 | [테스트 기본 용어 — 오류·결함·고장]({% post_url 2026-10-11-se100-041-testing-terminology-error-fault-failure %}) |
| 042 | [블랙박스 기법 — 동등 분할과 경계값 분석]({% post_url 2026-10-11-se100-042-equivalence-partitioning-boundary-value %}) |
| 043 | [화이트박스 기법 — 커버리지 기준과 MC/DC]({% post_url 2026-10-11-se100-043-coverage-criteria-mcdc %}) |
| 044 | [테스트 피라미드와 테스트 포트폴리오]({% post_url 2026-10-11-se100-044-test-pyramid-and-portfolio %}) |
| 045 | [테스트 더블 — 목·스텁·페이크·스파이]({% post_url 2026-10-11-se100-045-test-doubles-mock-stub-fake %}) |
| 046 | [속성 기반 테스트]({% post_url 2026-10-11-se100-046-property-based-testing %}) |
| 047 | [뮤테이션 테스팅 — 테스트를 테스트하기]({% post_url 2026-10-11-se100-047-mutation-testing %}) |
| 048 | [소비자 주도 계약 테스트]({% post_url 2026-10-11-se100-048-consumer-driven-contract-testing %}) |
| 049 | [성능·부하 테스트]({% post_url 2026-10-11-se100-049-performance-and-load-testing %}) |
| 050 | [탐색적 테스팅과 테스트 오라클 문제]({% post_url 2026-10-11-se100-050-exploratory-testing-test-oracle %}) |

### Part 6. 형상 관리와 전달 (051–060)

커밋에서 운영까지 — 변경을 안전하고 반복 가능하게 내보내는 방법.

| 번호 | 주제 |
|---|---|
| 051 | [형상 관리(SCM)의 개념]({% post_url 2026-10-11-se100-051-software-configuration-management %}) |
| 052 | [트렁크 기반 개발]({% post_url 2026-10-11-se100-052-trunk-based-development %}) |
| 053 | [재현 가능한 빌드]({% post_url 2026-10-11-se100-053-reproducible-builds %}) |
| 054 | [빌드 시스템 — Make 에서 Bazel 까지]({% post_url 2026-10-11-se100-054-build-systems-make-to-bazel %}) |
| 055 | [지속적 전달과 지속적 배포]({% post_url 2026-10-11-se100-055-continuous-delivery-vs-deployment %}) |
| 056 | [배포 전략 — 롤링·블루그린·카나리]({% post_url 2026-10-11-se100-056-deployment-strategies-bluegreen-canary %}) |
| 057 | [피처 플래그 — 배포와 출시를 분리하기]({% post_url 2026-10-11-se100-057-feature-flags %}) |
| 058 | [Infrastructure as Code]({% post_url 2026-10-11-se100-058-infrastructure-as-code %}) |
| 059 | [소프트웨어 공급망 보안 — SBOM 과 SLSA]({% post_url 2026-10-11-se100-059-supply-chain-security-sbom-slsa %}) |
| 060 | [릴리스 관리와 체인지로그]({% post_url 2026-10-11-se100-060-release-management-changelog %}) |

### Part 7. 프로세스와 방법론 (061–070)

팀이 일하는 방식을 고르고, 측정하고, 고치는 방법.

| 번호 | 주제 |
|---|---|
| 061 | [프로세스 모델 비교 — 폭포수·V 모델·점증·나선]({% post_url 2026-10-11-se100-061-process-models-waterfall-v-spiral %}) |
| 062 | [Boehm 의 나선형 모델과 위험 주도 개발]({% post_url 2026-10-11-se100-062-boehm-spiral-risk-driven %}) |
| 063 | [익스트림 프로그래밍(XP)의 가치와 실천]({% post_url 2026-10-11-se100-063-extreme-programming-xp %}) |
| 064 | [칸반과 흐름 — 리틀의 법칙과 WIP 제한]({% post_url 2026-10-11-se100-064-kanban-flow-littles-law %}) |
| 065 | [린 소프트웨어 개발 — 낭비와 흐름]({% post_url 2026-10-11-se100-065-lean-software-development %}) |
| 066 | [DevOps 의 원칙 — CALMS 와 세 가지 방법]({% post_url 2026-10-11-se100-066-devops-principles-three-ways %}) |
| 067 | [CMMI 와 프로세스 성숙도]({% post_url 2026-10-11-se100-067-cmmi-process-maturity %}) |
| 068 | [회고 — 팀이 스스로 개선하는 장치]({% post_url 2026-10-11-se100-068-retrospectives %}) |
| 069 | [통합 프로세스(UP/RUP) — 단계와 반복]({% post_url 2026-10-11-se100-069-unified-process-rup %}) |
| 070 | [DORA 지표 — 소프트웨어 전달 성과 측정]({% post_url 2026-10-11-se100-070-dora-metrics %}) |

### Part 8. 프로젝트 관리와 추정 (071–080)

얼마나 걸릴지 말하는 일의 어려움과, 그 불확실성을 다루는 도구.

| 번호 | 주제 |
|---|---|
| 071 | [추정은 왜 어려운가 — 불확실성의 원뿔]({% post_url 2026-10-11-se100-071-cone-of-uncertainty %}) |
| 072 | [COCOMO II — 알고리즘 기반 비용 추정]({% post_url 2026-10-11-se100-072-cocomo-ii %}) |
| 073 | [기능 점수(Function Point) 분석]({% post_url 2026-10-11-se100-073-function-point-analysis %}) |
| 074 | [스토리 포인트와 플래닝 포커]({% post_url 2026-10-11-se100-074-story-points-planning-poker %}) |
| 075 | [소프트웨어 위험 관리]({% post_url 2026-10-11-se100-075-software-risk-management %}) |
| 076 | [WBS 와 일정 계획 — 임계 경로]({% post_url 2026-10-11-se100-076-wbs-and-scheduling %}) |
| 077 | [처리량 기반 몬테카를로 예측]({% post_url 2026-10-11-se100-077-monte-carlo-forecasting %}) |
| 078 | [이해관계자 관리와 프로젝트 커뮤니케이션]({% post_url 2026-10-11-se100-078-stakeholder-management %}) |
| 079 | [범위·일정·품질의 트레이드오프]({% post_url 2026-10-11-se100-079-scope-time-quality-tradeoffs %}) |
| 080 | [진척 관리 — 획득가치(EVM)와 번다운]({% post_url 2026-10-11-se100-080-evm-progress-tracking %}) |

### Part 9. 품질·신뢰성·보안 (081–090)

품질을 "느낌"이 아니라 정의·측정·검증 가능한 것으로 만드는 방법.

| 번호 | 주제 |
|---|---|
| 081 | [품질 보증(QA)과 품질 관리(QC)]({% post_url 2026-10-11-se100-081-sqa-vs-quality-control %}) |
| 082 | [정형 검토 — Fagan 인스펙션]({% post_url 2026-10-11-se100-082-fagan-inspection-reviews %}) |
| 083 | [신뢰성 공학 — MTBF·MTTR·가용성]({% post_url 2026-10-11-se100-083-reliability-mtbf-availability %}) |
| 084 | [SLI·SLO·에러 버짓]({% post_url 2026-10-11-se100-084-sli-slo-error-budget %}) |
| 085 | [관측 가능성 — 로그·메트릭·트레이스]({% post_url 2026-10-11-se100-085-observability-logs-metrics-traces %}) |
| 086 | [위협 모델링과 STRIDE]({% post_url 2026-10-11-se100-086-threat-modeling-stride %}) |
| 087 | [시큐어 코딩과 OWASP Top 10]({% post_url 2026-10-11-se100-087-secure-coding-owasp %}) |
| 088 | [정형 기법 — TLA+ 와 모델 체킹]({% post_url 2026-10-11-se100-088-formal-methods-tla-model-checking %}) |
| 089 | [안전 필수 소프트웨어 — DO-178C 와 IEC 61508]({% post_url 2026-10-11-se100-089-safety-critical-do178c-iec61508 %}) |
| 090 | [카오스 엔지니어링]({% post_url 2026-10-11-se100-090-chaos-engineering %}) |

### Part 10. 유지보수·진화·사람 (091–099)

출시 이후가 소프트웨어 수명의 대부분이다. 그리고 그것을 만드는 건 사람이다.

| 번호 | 주제 |
|---|---|
| 091 | [유지보수의 네 유형 — ISO/IEC/IEEE 14764]({% post_url 2026-10-11-se100-091-maintenance-types-iso14764 %}) |
| 092 | [스트랭글러 피그 — 점진적 교체]({% post_url 2026-10-11-se100-092-strangler-fig-pattern %}) |
| 093 | [레거시 현대화와 데이터 마이그레이션]({% post_url 2026-10-11-se100-093-legacy-modernization-migration %}) |
| 094 | [API 폐기(deprecation) 정책]({% post_url 2026-10-11-se100-094-api-deprecation-policy %}) |
| 095 | [개발자 생산성 측정 — SPACE 프레임워크]({% post_url 2026-10-11-se100-095-developer-productivity-space %}) |
| 096 | [팀 토폴로지와 인지 부하]({% post_url 2026-10-11-se100-096-team-topologies-cognitive-load %}) |
| 097 | [심리적 안전감과 팀 효과성]({% post_url 2026-10-11-se100-097-psychological-safety %}) |
| 098 | [오픈소스 거버넌스와 기여 프로세스]({% post_url 2026-10-11-se100-098-open-source-governance %}) |
| 099 | [AI 보조 개발과 소프트웨어 공학]({% post_url 2026-10-11-se100-099-ai-assisted-software-engineering %}) |

## 읽는 순서 제안

100편을 번호 순서대로 읽을 필요는 없다. 목적에 따라 세 갈래를 권한다.

**1. 처음 소프트웨어 공학을 체계적으로 보려는 경우** — 역사에서 시작해 "왜" 를 먼저 잡는다.

```
001 → 002 → 003 → 004 → 007 → 009      (왜 어려운가)
011 → 014 → 015                         (무엇을 만드는가)
021 → 022 → 025 → 027                   (어떻게 나누는가)
041 → 042 → 044 → 045                   (어떻게 믿는가)
055 → 056 → 057                         (어떻게 내보내는가)
```

**2. 지금 팀의 전달 속도와 안정성이 문제인 경우** — 측정에서 시작한다.

```
070 (DORA) → 084 (SLO) → 052 (트렁크) → 057 (피처 플래그)
→ 056 (배포 전략) → 064 (칸반·WIP) → 068 (회고) → 096 (팀 토폴로지)
```

**3. 오래된 시스템을 물려받은 경우** — 변경을 안전하게 만드는 것부터.

```
006 (Lehman) → 037 (seam·특성 테스트) → 032 (코드 스멜) → 047 (뮤테이션)
→ 092 (스트랭글러 피그) → 093 (마이그레이션) → 094 (API 폐기) → 091 (유지보수 유형)
```

## 100편을 꿰는 다섯 개의 질문

카테고리는 열 개지만, 반복해서 나온 질문은 다섯 개 정도로 줄어든다.

| 질문 | 대표 글 | 요지 |
|---|---|---|
| 본질적 복잡성은 어디에 있는가 | #002, #011, #018 | 도구는 우연적 복잡성을 줄인다. 무엇을 만들지 합의하는 어려움은 남는다. |
| 변경 비용을 무엇이 결정하는가 | #004, #021, #027, #036 | 바뀔 가능성이 높은 결정을 숨기고 경계 뒤에 두면 변경이 국소화된다. |
| "된다" 를 어떻게 아는가 | #041, #043, #047, #050, #088 | 테스트는 결함의 존재를 보일 뿐 부재를 보이지 못한다. 그래서 여러 기법을 겹쳐 쓴다. |
| 불확실성을 어떻게 다루는가 | #062, #071, #075, #077 | 추정을 한 숫자로 약속하지 말고 범위와 확률로 말하며, 위험이 큰 것부터 먼저 줄인다. |
| 조직이 시스템을 어떻게 만드는가 | #003, #007, #096, #097 | 사람을 더 넣는 것, 팀을 나누는 방식, 말할 수 있는 분위기가 모두 소프트웨어 구조와 품질에 그대로 찍힌다. |

## 소프트웨어 공학은 끝난 학문인가

1968년 NATO 회의 보고서는 "소프트웨어 공학" 이라는 말을 일부러 도발적으로 골랐다고 적는다(#001). 반세기가 지난 지금도 그 도발은 유효하다. 다른 공학처럼 재료의 성질이 안정되어 있지 않고, 요구는 계속 바뀌며, 도구는 몇 년마다 세대가 바뀐다.

가장 최근의 변화는 AI 보조 개발이다(#099). 그 글에서 정리했듯, 효과에 대한 증거는 누가 어떤 설계로 무엇을 쟀는지에 따라 크게 엇갈린다. 하지만 이 시리즈의 관점에서 보면 질문 자체는 새롭지 않다. 코드를 빨리 쓰게 해 주는 도구가 본질적 복잡성까지 줄이는가(#002), 늘어난 코드를 무엇으로 믿을 것인가(#041–#050), 그 변경을 얼마나 안전하게 내보낼 것인가(#051–#060). 도구가 바뀌어도 이 질문들은 남는다.

## 확인 문제

1. SE100 과 CS300 Part 10 의 역할은 어떻게 다른가?
2. "오래된 시스템을 물려받은 경우" 의 읽기 경로가 Lehman 의 법칙(#006)에서 시작하는 이유는?
3. 다섯 질문 중 "'된다' 를 어떻게 아는가" 에 정형 기법(#088)이 포함된 이유는?
4. AI 보조 개발이 이 시리즈의 질문을 바꾸지 않는다고 본 근거를 하나 들라.

### 풀이

1. CS300 Part 10 은 소프트웨어 공학의 기본 개념을 한 번씩 소개한다. SE100 은 그 위에서 원전·표준·실무 판단을 중심으로 각 주제를 깊게 다룬다.
2. 계속 쓰이는 시스템은 계속 바뀌어야 하고, 바뀔수록 복잡도가 늘어난다는 관찰이 레거시 작업의 출발점이기 때문이다. 이 관찰을 받아들여야 "한 번에 갈아엎기" 대신 점진적 개선을 택하게 된다.
3. 테스트는 고른 입력에 대해서만 확인한다. 정형 기법은 모델의 모든 상태를 탐색하거나 증명해, 테스트로는 닿기 어려운 동시성·설계 수준의 결함을 찾는 다른 종류의 근거를 준다.
4. 예: 코드 작성 속도가 빨라져도 무엇을 만들지 합의하는 본질적 어려움(#002)과, 늘어난 변경을 검증하고 안전하게 배포해야 하는 필요(#041–#060)는 그대로 남는다.

## 더 읽을거리 (References)

- P. Naur, B. Randell (eds.), [*Software Engineering: Report on a conference sponsored by the NATO Science Committee*](http://homepages.cs.ncl.ac.uk/brian.randell/NATO/nato1968.PDF), Garmisch, 1968
- F. P. Brooks, Jr., [*No Silver Bullet: Essence and Accidents of Software Engineering*](https://www.cs.unc.edu/techreports/86-020.pdf), UNC TR86-020, 1986
- IEEE Computer Society, [*Guide to the Software Engineering Body of Knowledge (SWEBOK Guide) V4.0*](https://www.computer.org/education/bodies-of-knowledge/software-engineering/v4), 2024
- F. P. Brooks, Jr., *The Mythical Man-Month: Essays on Software Engineering*, Anniversary ed., Addison-Wesley, 1995 (서지 정보)
