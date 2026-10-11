---
layout: post
title: "[SE100 #087] 시큐어 코딩과 OWASP Top 10"
date: 2026-10-11 17:08:56 +0900
categories: [software-engineering]
tags: [se100, quality-reliability, owasp, asvs, secure-coding, cwe]
---

소프트웨어 공학 100 주제 시리즈의 87번째 글이다. (카테고리: 품질·신뢰성·보안)

## 한 줄 요약

OWASP Top 10 은 **인식(awareness) 문서**이지 검증 기준이 아니다. 팀이 실제로 지킬 수 있는 시큐어 코딩은 Top 10 의 위험을 **ASVS 의 검증 가능한 요구사항**으로 바꾸고, 그것을 코드 패턴과 자동 검사로 고정하는 데서 나온다.

## 왜 필요한가

"OWASP Top 10 을 준수한다" 는 문장은 자주 보이지만 검증할 방법이 없다. Top 10 의 각 항목은 수십 개 CWE 를 묶은 **위험 범주**라서, "Injection 을 준수한다" 가 무엇을 뜻하는지 정의되어 있지 않다. 그 결과는 대개 이렇다.

- 보안 교육 자료에는 Top 10 이 있지만 코드 리뷰 체크리스트에는 아무 항목도 없다.
- 침투 테스트 보고서가 올 때마다 같은 유형(IDOR, 상세 오류 노출)이 반복된다.
- 정적 분석 도구 경고 수백 개가 쌓여 있지만 무엇이 차단 기준인지 정해져 있지 않다.

Top 10 범주와 개별 취약점(SQL 인젝션, XSS·CSRF, 접근 통제)의 기초, 그리고 SSDF 개요는 CS300 [OWASP Top 10 개관]({% post_url 2026-10-10-cs300-250-owasp-top-10-overview %}), [시큐어 코딩]({% post_url 2026-10-10-cs300-254-secure-coding %}), [접근 통제 실패와 IDOR]({% post_url 2026-10-10-cs300-253-broken-access-control-and-idor %}) 에서 다뤘다. 이 글은 그것을 **팀의 엔지니어링 기준**으로 바꾸는 방법을 다룬다.

## 핵심 개념

### 세 층: 위험, 약점, 요구사항

| 층 | 대표 자료 | 단위 | 쓰임 |
|---|---|---|---|
| 위험 범주 | [OWASP Top 10:2025](https://owasp.org/Top10/2025/) | 10개 범주 | 교육, 우선순위 소통 |
| 약점 유형 | [CWE Top 25 (2025)](https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html) | 개별 CWE | 도구 결과 분류, 근본 원인 분석 |
| 검증 요구사항 | [OWASP ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/) | 번호가 붙은 요구사항 | 설계·리뷰·테스트 기준, 조달 계약 |

Top 10:2025 페이지는 스스로를 "개발자와 웹 애플리케이션 보안을 위한 표준 **인식** 문서" 이자 가장 중요한 위험에 대한 폭넓은 합의라고 소개한다. 반면 ASVS 는 웹 애플리케이션 기술적 보안 통제를 **테스트하는 기준**과 개발자를 위한 보안 요구사항 목록을 제공하는 것을 목표로 한다. 이 차이 때문에 "Top 10 준수" 가 아니라 "ASVS 레벨 X 충족" 이 검증 가능한 문장이 된다.

### Top 10:2025 에서 코딩과 직결되는 변화

2025년판 목록은 A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging and Alerting Failures, A10 Mishandling of Exceptional Conditions 이다.

- [A01 Broken Access Control](https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/) 은 1위를 유지했고, 테스트한 애플리케이션의 100% 에서 어떤 형태로든 접근 통제 결함이 발견됐다고 적는다. SSRF(CWE-918)도 이 범주에 들어갔다. 대책의 첫 줄은 "공개 자원을 제외하면 기본 거부(deny by default)" 다.
- [A10 Mishandling of Exceptional Conditions](https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/) 는 새 범주로 24개 CWE 를 묶는다. 부적절한 오류 처리, 논리 오류, **실패 시 열림(failing open, CWE-636)** 이 핵심이다. 다단계 거래 도중 오류가 나면 전체를 롤백하는 **fail closed** 를 요구하고, 오류 처리를 함수마다 따로 하지 말고 한곳에서 일관되게 하라고 권한다.

A10 은 시큐어 코딩이 입력 검증만의 문제가 아니라 **예외 경로 설계**의 문제임을 공식화했다는 점에서 의미가 있다.

### ASVS 의 레벨

[ASVS 5.0 의 "What is the ASVS" 장](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x03-What-is-the-ASVS.md)은 세 레벨을 정의한다.

| 레벨 | 성격 | 규모 |
|---|---|---|
| L1 | 최소한의 첫 방어선, 진입 장벽을 낮추는 것이 목표 | 전체 요구사항의 약 20% |
| L2 | **대부분의 애플리케이션이 목표로 해야 할 수준** | 약 50% 추가 → L1+L2 로 약 70% |
| L3 | 최고 수준의 보안을 입증해야 하는 애플리케이션 | 나머지 약 30% |

같은 장은 레벨을 처방하지 않고 조직이 위험에 따라 정하라고 하면서, 민감 데이터가 적은 초기 스타트업은 L1, 온라인 뱅킹은 L3 미만을 정당화하기 어렵다는 예를 든다. 요구사항은 버전과 함께 `v5.0.0-1.2.5` 처럼 인용하라고 권한다. 번호가 버전마다 바뀔 수 있기 때문이다.

### 범주 → 요구사항 → 코드 패턴

| Top 10:2025 | ASVS 5.0.0 요구사항 (요지) | 코드 패턴 |
|---|---|---|
| A05 Injection | 1.2.4 DB 질의는 파라미터화 쿼리·ORM 등으로 인젝션을 방지 (L1) | 바인드 변수, 문자열 연결 금지 |
| A05 Injection | 1.2.5 OS 명령 인젝션 방지: 파라미터화된 OS 호출 또는 문맥별 인코딩 (L1) | 셸 미경유, 인자 배열 |
| A01 Access Control | 8.2.2 데이터 항목 단위 접근을 명시적 권한으로 제한해 IDOR/BOLA 완화 (L1) | 조회 쿼리에 소유자 조건 포함 |
| A01 Access Control | 8.3.1 인가 규칙은 신뢰할 수 있는 서비스 계층에서 강제 (L1) | 클라이언트 숨김 버튼에 의존 금지 |
| A01 / 데이터 노출 | 15.3.1 데이터 객체 전체가 아니라 필요한 필드만 반환 (L1) | 응답 DTO 분리 |
| A10 Exceptional | 16.5.1 예상치 못한 오류에는 일반 메시지, 스택·쿼리·키 노출 금지 (L2) | 전역 예외 처리기 |
| A10 Exceptional | 16.5.3 예외 시에도 안전하게 실패, fail-open 방지 (L2) | 트랜잭션 롤백, 기본 거부 |

이 표가 팀의 리뷰 체크리스트와 테스트 계획의 뼈대가 된다.

## 예제

### 객체 단위 인가 (ASVS 8.2.2)

```kotlin
// 나쁜 예: id 만으로 조회 → 다른 사용자의 주문도 열람 가능 (IDOR, CWE-639)
@GetMapping("/orders/{id}")
fun get(@PathVariable id: Long) = orderRepo.findById(id).orElseThrow()

// 좋은 예: 소유자 조건을 '조회 자체'에 넣고, 엔티티 대신 DTO 반환 (15.3.1)
@GetMapping("/orders/{id}")
fun get(@PathVariable id: Long, @AuthenticationPrincipal user: AppUser): OrderView =
    orderRepo.findByIdAndOwnerId(id, user.id)
        ?.let(OrderView::from)
        ?: throw NotFoundException()      // 존재 여부도 흘리지 않도록 403 대신 404
```

조회 후 `if (order.ownerId != user.id)` 로 검사하는 방식도 동작하지만, 목록 API·통계 API 를 추가할 때 검사를 빠뜨리기 쉽다. **조건을 데이터 접근 계층에 넣으면** 빠뜨릴 자리가 줄어든다.

### fail closed (ASVS 16.5.3, Top 10 A10)

```kotlin
// 나쁜 예: 한도 조회 실패를 삼키고 진행 → 장애 시 한도 무시 (fail open)
val limit = try { limitClient.remaining(userId) } catch (e: Exception) { Long.MAX_VALUE }

// 좋은 예: 판단 불가면 거절, 상태 변경은 한 트랜잭션으로
@Transactional
fun transfer(cmd: TransferCommand) {
    val limit = limitClient.remaining(cmd.userId)          // 실패 시 예외 → 전체 롤백
    require(cmd.amount <= limit) { "한도 초과" }
    accounts.debit(cmd.from, cmd.amount)
    accounts.credit(cmd.to, cmd.amount)
    ledger.append(cmd)
}

@RestControllerAdvice
class GlobalErrors {
    @ExceptionHandler(Exception::class)
    fun unexpected(e: Exception): ResponseEntity<ApiError> {
        log.error("unexpected", e)                          // 상세는 내부 로그로
        return ResponseEntity.status(500).body(ApiError("요청을 처리할 수 없습니다"))  // 16.5.1
    }
}
```

`catch` 블록에서 "기본값으로 계속 진행" 하는 코드는 리뷰에서 가장 먼저 의심할 대상이다. 그 기본값이 권한·한도·검증 결과라면 거의 항상 fail-open 이다.

### 검증 자동화의 배치

NIST [SSDF (SP 800-218)](https://csrc.nist.gov/pubs/sp/800/218/final) 는 실천 항목을 PO(조직 준비), PS(소프트웨어 보호), PW(잘 보호된 소프트웨어 생산), RV(취약점 대응) 네 묶음으로 나눈다. PW 안에서 PW.5 는 시큐어 코딩 관행 준수, PW.7 은 사람이 읽는 코드의 리뷰·분석, PW.8 은 실행 코드 테스트를 다룬다. 이를 파이프라인에 놓으면 다음과 같다.

```
 커밋 ──▶ PR ──────────────────────────▶ 머지 ──▶ 스테이징 ──────────▶ 운영
          │ SAST (PW.7, CWE 매핑)            │ DAST·API 퍼징 (PW.8)
          │ SCA·SBOM (A03 공급망)            │ ASVS 기반 수동 테스트(L2 항목 샘플)
          │ 리뷰 체크리스트 (위 표)          │
          └ 차단 기준: CWE Top 25 해당 + 높은 신뢰도
```

도구 경고 전부를 차단 기준으로 삼으면 팀은 곧 경고를 무시한다. **CWE Top 25 에 속하고 도구 신뢰도가 높은 것만 차단**하고 나머지는 추세로 관리하는 식으로 기준을 좁혀야 지속된다. 2025년 CWE Top 25 의 1~4위는 CWE-79(XSS), CWE-89(SQL 인젝션), CWE-352(CSRF), CWE-862(인가 누락)다.

## 흔한 오해와 함정

- **"Top 10 준수 인증"** — Top 10 은 검증 기준이 아니다. 계약이나 감사에 쓸 기준이 필요하면 ASVS 레벨을 지정한다.
- **입력 검증으로 모든 인젝션을 막는다** — 허용 목록 검증은 유용하지만, 인젝션의 근본 대책은 데이터와 명령을 분리하는 **파라미터화**와 출력 문맥별 인코딩이다.
- **프런트엔드에서 버튼을 숨기면 인가 완료** — ASVS 8.3.1 이 정확히 이것을 금한다. 인가는 서버의 신뢰 계층에서.
- **예외를 삼키는 "안정성" 코드** — 장애 시 계속 돌아가게 하려는 catch 가 보안 통제를 끄는 스위치가 된다.
- **스캐너 0건 = 안전** — 접근 통제·비즈니스 로직 결함은 도구가 잘 못 찾는다. 위협 모델링(SE100 #086)과 리뷰가 필요하다.

## 확인 문제

1. OWASP Top 10 과 ASVS 의 목적 차이를 한 문장씩 쓰라.
2. ASVS L2 를 충족하려면 전체 요구사항의 대략 몇 % 를 구현해야 하는가?
3. 다음 코드의 문제와 관련 Top 10:2025 범주는? `val allowed = try { authz.check(u, r) } catch (e: Exception) { true }`
4. 조회 후 소유자 비교보다 조회 쿼리에 소유자 조건을 넣는 방식이 나은 이유는?

### 풀이

1. Top 10 은 가장 중요한 웹 애플리케이션 보안 위험에 대한 인식과 합의를 위한 문서이고, ASVS 는 보안 통제를 검증하고 개발 요구사항으로 쓰기 위한 번호 붙은 요구사항 표준이다.
2. L1(약 20%)과 L2(약 50%)를 합친 약 70%.
3. 인가 서비스 장애 시 모두 허용하는 fail-open 이다. A10 Mishandling of Exceptional Conditions(CWE-636)이며 결과적으로 A01 접근 통제 실패로 이어진다. 판단 불가 시 거부해야 한다.
4. 새 API·새 쿼리를 추가할 때 별도 검사를 빠뜨릴 여지가 줄고, 존재 여부 자체를 노출하지 않으며, 불필요한 데이터를 메모리로 읽지 않는다.

## 더 읽을거리 (References)

- OWASP, [Top 10:2025](https://owasp.org/Top10/2025/) ([A01](https://owasp.org/Top10/2025/A01_2025-Broken_Access_Control/), [A10](https://owasp.org/Top10/2025/A10_2025-Mishandling_of_Exceptional_Conditions/))
- OWASP, [Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/) ([5.0 — What is the ASVS](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x03-What-is-the-ASVS.md))
- OWASP Cheat Sheet Series, [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [Error Handling](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html), [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- MITRE, [2025 CWE Top 25](https://cwe.mitre.org/top25/archive/2025/2025_cwe_top25.html), [CWE-636 Not Failing Securely](https://cwe.mitre.org/data/definitions/636.html), [CWE-639](https://cwe.mitre.org/data/definitions/639.html)
- NIST, [SP 800-218 Secure Software Development Framework v1.1](https://csrc.nist.gov/pubs/sp/800/218/final)
