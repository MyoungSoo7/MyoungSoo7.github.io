---
layout: post
title: "DBeaver 무료판 vs 유료판 — 무엇이 갈리고, 얼마이고, 언제 사야 하나"
date: 2026-09-17 19:10:27 +0900
categories: [Engineering, Database]
tags: [DBeaver, SQL, 데이터베이스, 라이선스, 도구비교]
---

DBeaver 는 JDBC 만 있으면 대부분의 DB 에 붙는 범용 SQL 클라이언트다. 무료판(Community)만 써도 하루 업무가 굴러가기 때문에, "돈을 낼 이유"를 찾기가 오히려 어렵다.

그런데 유료판 라인업은 Lite / Enterprise / Ultimate / CloudBeaver / Team 다섯 갈래고, 연간 $113 에서 $1,630 까지 **14배** 차이가 난다. 이 글은 *기능 차이*보다 **결제 결정에 실제로 영향을 주는 지점**을 공식 문서 기준으로 정리한다. 가격과 기능표는 모두 [dbeaver.com](https://dbeaver.com/edition/) 공식 페이지를 2026-09-17 에 직접 확인한 값이다.

---

## 결론부터

| 상황 | 답 |
|---|---|
| 혼자 RDB 몇 개 붙여서 쿼리 짠다 | **Community**. 돈 낼 이유 없음 |
| MongoDB·Cassandra·Redis 를 같은 툴에서 봐야 한다 | **Enterprise** ($255/년) |
| 스키마 비교·마이그레이션·Git 연동을 쓴다 | **Enterprise** |
| AWS/GCP/Azure 네이티브 연동, 클라우드 스토리지 | **Ultimate** ($510/년) |
| 조회·export 만 하는 비개발 직군 | **Lite** ($113/년) |
| 학생·교원 | **Academic** — Enterprise 를 **무료**로 |
| 폐쇄망·오프라인 | 월간 말고 **연간** 구독 (아래 참조) |

---

## 1. 가격 (2026-09-17 공식 확인)

| 에디션 | 연간 | 월간 |
|---|---|---|
| Community | **무료** (Apache-2.0) | — |
| Lite | $113 | $12 |
| Enterprise | $255 | $26 |
| Ultimate | $510 | 월간 없음 |
| CloudBeaver Enterprise | $1,025 | 별도 옵션 |
| Team Edition | $1,630 | 월간 없음 |

전부 **named user** 기준이다 — 동시 접속자 수가 아니라 "그 사람" 단위로 센다. 한 사람이 여러 워크스테이션에 깔아 쓰는 건 허용되지만, 그 워크스테이션들을 **그 사람만** 쓸 때만이다.

월간이 연간보다 싸 보이지만 12개월이면 Lite $144, Enterprise $312 로 연간보다 비싸다. 그리고 월간에는 뒤에 나올 함정이 하나 더 붙는다.

원화 환산은 넣지 않았다. 환율이 결제 시점에 정해지고 VAT 처리도 국가별로 달라, 지금 적어두면 틀린 숫자가 된다.

---

## 2. Community 로 어디까지 되나

DBeaver Community 는 [Apache License 2.0](https://github.com/dbeaver/dbeaver) 오픈소스다. 2026-09-17 기준 GitHub 스타 51,789 개, 최신 릴리스는 **26.2.0** (2026-08-30).

공식 [Community → PRO 비교표](https://dbeaver.com/switch-to-dbeaver-pro/) 가 말하는 경계선은 이렇다.

**Community 에 있는 것**

- SQL 데이터베이스 지원
- SQL Editor / Data Editor
- Task management (기본 태스크)
- Database maintenance tools

**Community 에 없는 것 (Enterprise 부터)**

- **NoSQL / BigData 데이터베이스 지원** ← 현실적으로 가장 큰 벽
- Advanced security (마스터 패스워드, 자격증명 암호화, SAML·SSO·OKTA·Kerberos)
- Visual Query Builder
- AI assistant in SQL
- Advanced development tools
- Database performance visual tools
- Multi-component task management
- **Task Scheduler**

**Ultimate 부터**

- AWS / Google Cloud / Azure 네이티브 지원
- Cloud storage 지원

즉 Community 가 막히는 지점은 대개 셋 중 하나다 — **NoSQL 을 붙여야 할 때**, **태스크를 스케줄로 돌려야 할 때**, **엔터프라이즈 인증을 써야 할 때**.

> AI 기능은 이분법이 아니다. 공식 문서에 따르면 Community 에도 AI Chat 과 `@ai` 커맨드 수준은 열려 있고, AI query suggestion·error explanation·smart metadata description, 그리고 Azure OpenAI·Gemini·Ollama·Claude·Bedrock 같은 **추가 프로바이더 선택**이 PRO 배지가 붙은 항목이다. ([AI Smart assistance](https://github.com/dbeaver/dbeaver/wiki/AI-Smart-assistance))

---

## 3. Lite / Enterprise / Ultimate 는 무엇으로 갈리나

공식 [제품 비교표](https://dbeaver.com/edition/) 의 항목을 옮기면 이렇다.

| 기능 | Lite | Enterprise | Ultimate |
|---|:--:|:--:|:--:|
| SQL / NoSQL·BigData DB 지원 | O | O | O |
| SQL Editor, Visual Query Builder, 데이터 편집 | O | O | O |
| ER 다이어그램 (보기) | O | O | O |
| 엔터프라이즈 인증, Advanced security | O | O | O |
| **Task scheduler / 멀티컴포넌트 태스크** | X | O | O |
| **DB 백업 도구 지원, 데이터 마이그레이션** | X | O | O |
| **서버 헬스 대시보드, 유지보수 도구** | X | O | O |
| **ERD 편집 모드 (스키마 설계)** | X | O | O |
| **Mock 데이터 생성** | X | O | O |
| **SQL 디버거 (PostgreSQL)** | X | O | O |
| **스키마 비교/마이그레이션, 테이블 데이터 비교** | X | O | O |
| **Git 저장소 프로젝트 동기화** | X | O | O |
| Tableau 연동 | X | O | O |
| **AWS/GCP/Azure 네이티브, 클라우드 탐색기·스토리지** | X | X | O |

한 줄로 줄이면:

- **Lite** = *보는 사람*용. 개발 도구가 빠져 있다. 공식 설명도 "No access to development tools" 다.
- **Enterprise** = *만드는 사람*용. DBA 도구 + 개발 도구 + Git. 가격표에 "Most popular" 가 붙어 있는 자리다.
- **Ultimate** = Enterprise + **클라우드**. 그 외 차이는 없다.

그래서 Enterprise($255) → Ultimate($510) 의 +$255 는 **오직 클라우드 네이티브 연동 값**이다. AWS 콘솔이나 `aws` CLI 로 이미 해결하고 있다면 그 배는 안 타도 된다.

---

## 4. 가격표에 안 나오는 함정 네 개

여기가 이 글의 본론이다. 기능표만 보고 고르면 놓친다.

### (1) 영구 라이선스는 이미 끝났다

DBeaver 는 **버전 23.3 이후 신규 영구(perpetual) 라이선스를 판매하지 않는다.** 기존 보유자는 계속 쓸 수 있지만, 새 버전과 기술지원을 받으려면 연 단위 연장을 해야 한다. 그리고 **90일 넘게 연장하지 않으면 영구 라이선스로는 복구되지 않고 연간 구독으로만 재활성화된다.**

"한 번 사두고 계속 쓰는" 선택지는 신규 구매자에게 더는 없다. 이건 총소유비용 계산을 통째로 바꾸는 사실이다.

### (2) 월간 구독은 인터넷을 요구한다 — 폐쇄망이면 탈락

공식 라이선스 문서의 표현이 명확하다.

- **월간 구독**: 최초 활성화와 **매 갱신 때마다** 워크스테이션에 인터넷 접속이 필요하다. 활성화 없이는 제품을 쓸 수 없다. 게다가 **개인 사용자 전용**이고 양도·공유가 안 된다.
- **연간 구독**: 워크스테이션에 인터넷이 **필요 없다.** 오프라인이나 사내 방화벽 뒤에서 돌릴 수 있다.

금융·제조처럼 망분리된 환경이면 이 한 줄이 월간/연간 선택을 끝내버린다. 가격 비교의 문제가 아니다.

### (3) Early Access 는 "무료 PRO" 가 아니다

트라이얼 14일이 끝나면 Early Access Program 에 들어가 PRO 기능을 무료로 계속 쓸 수 있다. 다만 제약이 실무를 막는 수준이다.

- 동시 DB 연결 **3개** (넘으면 앱이 아예 안 뜬다)
- 태스크 **5개**
- **CI/CD 용 CLI 실행 불가**
- **Task Scheduler 사용 불가**
- 워크스페이스·프로젝트 각 **1개**만
- 각 빌드는 생성일로부터 **1개월** 후 만료 → 계속 새 빌드를 받아야 한다
- 안정판이 아니라 **프리릴리스 빌드**이고, 사용 통계 수집에 동의해야 한다

"공짜로 PRO 쓰는 법" 으로 돌아다니지만, 연결 3개 제한과 스케줄러 차단 때문에 업무용으로는 대부분 못 쓴다. 학습·평가용으로 보는 게 맞다.

### (4) 학생·교원은 Enterprise 가 무료다

Academic 라이선스는 **DBeaver Enterprise 전체 기능**을 1년간 무료로 준다. 조건이 붙는다.

- 학생·교원 **전용**, 학술 목적에 한함. **기업 환경에서 사용 금지**
- **기술지원 없음**
- 대학 이메일로 신청·검증 (없으면 학생증 등 서류 첨부), 수동 심사 **약 3영업일**
- 1년 만료 후 **연장 불가** — 신분을 다시 증명해 새로 신청해야 한다

연 $255 짜리를 0원에 쓰는 길이 열려 있는데 의외로 안 알려져 있다.

---

## 5. 팀 단위로 가면 계산이 달라진다

| 제품 | 형태 | 최소 인원 |
|---|---|---|
| Group Yearly Subscription | 데스크톱 DBeaver, 단일 키로 N명 | 제한 없음 |
| CloudBeaver Enterprise | 브라우저 기반, 서버 설치 | **5명** |
| Team Edition | CloudBeaver + Ultimate + 협업·권한 관리 | — |

Group 라이선스는 활성 기간 중 **인원 추가는 가능**하지만 **감축은 다음 갱신 전에만** 된다. 인원을 넉넉히 잡아 사두면 1년 동안 못 줄인다는 뜻이다. 보수적으로 시작해 늘리는 쪽이 유리하다.

Team Edition($1,630) 은 "Ultimate + CloudBeaver" 를 합친 값이다. 따로 사면 $510 + $1,025 = $1,535 이므로, 두 개를 다 쓸 게 확실할 때만 의미가 있다. 실제로 필요한 건 **실시간 데이터 협업, 공유 스크립트·커넥션, SAML/Azure AD 통합 접근, 역할 관리**다. 이게 없어도 된다면 Ultimate 에서 멈추는 게 맞다.

---

## 6. 공식 문서끼리 어긋나는 곳이 있다

정직하게 적어둔다. 같은 dbeaver.com 안에서도 두 표의 값이 다르다.

- [제품 비교표](https://dbeaver.com/edition/) 는 **Database maintenance tools** 를 Lite 에서 **미지원(x)**, Enterprise 부터 지원으로 표기한다.
- [Community → PRO 비교표](https://dbeaver.com/switch-to-dbeaver-pro/) 는 같은 이름의 항목을 **Community 에서 지원(O)** 으로 표기한다.

두 표가 같은 기능을 다른 범위로 세고 있다고 보는 게 합리적이지만, 어느 쪽이 맞는지 공개 문서만으로는 확정할 수 없다. **"maintenance tools" 가 결제 사유라면 구매 전에 14일 트라이얼로 직접 확인하라.** 이 글에서 단정하지 않는 이유다.

---

## 7. 그래서 어떻게 정하나

순서대로 물어보면 대부분 3번 안에 끝난다.

1. **NoSQL·BigData 를 이 툴로 봐야 하나?** → 아니오면 Community 로 충분하다. 여기서 끝나는 경우가 제일 많다.
2. **태스크를 스케줄로 돌리거나 CI 에서 CLI 로 실행해야 하나?** → 예면 Enterprise 이상. Lite 도 EAP 도 스케줄러가 없다.
3. **스키마 비교·마이그레이션·ERD 편집·SQL 디버거를 쓰나?** → 예면 Enterprise.
4. **클라우드 네이티브 연동이 필요한가?** → 예면 Ultimate. 아니면 여기서 $255 를 아낀다.
5. **망분리 환경인가?** → 예면 월간은 후보에서 빼고 연간으로.
6. **학생·교원인가?** → Academic 신청. 0원.

무엇을 고르든 **14일 트라이얼이 먼저다.** 버전마다 한 번씩 받을 수 있고 신용카드도 필요 없다. 위 (6)번 같은 문서 불일치는 실제로 켜 보는 것 말고 해소할 방법이 없다.

---

## References

- [DBeaver — Compare Products & Pricing](https://dbeaver.com/edition/) (2026-09-17 확인)
- [DBeaver — Switch from Community to PRO](https://dbeaver.com/switch-to-dbeaver-pro/) (2026-09-17 확인)
- [DBeaver — License types](https://dbeaver.com/license-types/) (2026-09-17 확인)
- [DBeaver — Buy a license](https://dbeaver.com/buy/)
- [DBeaver — Supported Databases](https://dbeaver.com/databases/)
- [dbeaver/dbeaver — GitHub (Apache-2.0)](https://github.com/dbeaver/dbeaver)
- [DBeaver Wiki — AI Smart assistance](https://github.com/dbeaver/dbeaver/wiki/AI-Smart-assistance)
- [dbeaver.io — Community Edition](https://dbeaver.io/)
