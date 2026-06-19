---
layout: post
title: "*모두의 창업 · 패스트캠퍼스 · 쿠팡* — *2026 보안 사태 3 건* 의 *공통 원인* 과 *웹 · 백엔드 · 네트워크* *방어법 의 총정리*"
date: 2026-06-19 12:30:00 +0900
categories: [security, backend, network, devsecops, incident-analysis]
tags: [security-breach, jwt, secret-management, insider-threat, zero-trust, owasp, github-secrets, vibe-coding, korean-incidents-2026]
---

> 2025 년 *11 월* — *쿠팡 3,370 만 명* 개인정보 유출.
> 2026 년 *5~6 월* — *데이원컴퍼니 (패스트캠퍼스 모회사)* 의 *GitHub 키* 탈취 → *콜로소 · 제로베이스 등* *전 서비스* 유출.
> 2026 년 *6 월 15 일* — *중기부 모두의 창업* 합격자 *5,000 명* 의 *아이디어 + 심사평* 유출.
>
> *7 개월 안 에 *세 번*. *피해 규모 · 도메인 · 공격 벡터* 가 모두 다른데, *원인 의 *뿌리* 는 *놀랍게도 거의 동일* 하다.

이 글은 *세 사건* 을 *원인 → 방어법* 의 관점 에서 분석한다. *웹 / 백엔드 / 네트워크* 의 *세 레이어 별* 로 *지금 당장 *내 시스템에 적용* 할 *체크리스트* 를 정리.

*내 [어제 글 — *바이브 코딩 과 시니어 7 가지 기준*](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html)* 의 *기술적 후속편*. *바이브 코딩의 위험* 이 *2026 모두의 창업 사태* 에서 *현실로 터졌다* 는 이야기 도 포함.

---

## TL;DR — *한 줄 결론*

> *2026 한국 3 대 보안 사태* 는 *기술적 미스* 가 아니라 *프로세스 미스*. *제로데이 도, 신규 익스플로잇 도 아니다*. *퇴사자 키 회수 실패 (쿠팡)*, *GitHub 시크릿 노출 (데이원)*, *권한 분리 누락 (모두의 창업)* — *모두 *2003 년부터 알려진 패턴*. *AI 가 코드를 빠르게 만들 수 있어도 *보안 의 *책임 의 시야* 는 *AI 가 대체 못 한다*. *지금 당장 *3 분 안 에 할 수 있는 *7 가지* 부터*.

---

## 1. *사건 의 *팩트 정리***

### 1.1 *쿠팡 — *2025 년 11 월 발표 / 3,370 만 명***

*공격 벡터* :
- *중국 국적 의 *전 직원 개발자* 가 *재직 중* 시스템 접근용 *JWT 서명키* 보유
- *퇴사 시 *키 회수 / 무효화 절차 부재*
- 퇴사 후 *5 개월간* *동일 키* 로 *외부에서 서버 접근*
- *이름 · 주소 · 전화 · 이메일 · 주문 정보* *무제한 조회*

*핵심 실패* :
1. *JWT 서명키 = 서비스 마스터키* 인데 *개발자 개인이 직접 보유*
2. *키 로테이션* 정책 없음
3. *비정상 접근 패턴 탐지* 없음 (*외부 IP 에서 5 개월간 무한 조회 가 모니터링 통과*)
4. *퇴사 프로세스 의 *기술 자격증명 회수* 가 *HR 체크리스트* 에 없음

(참고 : *[2025 보안 사고 결산 — 쿠팡 사건](https://m.boannews.com/html/detail.html?idx=141221)*, *[법무법인 지향 분석](https://www.jihyanglaw.com/?p=3678)*)

### 1.2 *데이원컴퍼니 — *2026 년 5~6 월 / 패스트캠퍼스 · 콜로소 · 제로베이스 등***

*공격 벡터* :
- *5 월 9 일* — *GitHub 서비스 마스터 계정 키값* 탈취
- *1 개월간* 침투 미감지
- *6 월 8 일* 사고 인지 후 차단
- *이름 · 이메일 · 전화 · 암호화된 비밀번호* 유출
- 영향 서비스 : *패스트캠퍼스, 콜로소, 제로베이스, 마이라이트, 뉴스프레소, 리스픽, 샤이니영어, 워너스픽* — *데이원 운영 전부*

*핵심 실패* :
1. *GitHub 마스터 토큰* 이 *전 서비스 의 *동일 권한*. *권한 분리 없음*
2. *토큰 의 *어디서 새었는지* 가 *추적 불가* (Personal Access Token 의 광범위 scope)
3. *1 개월간* *서비스 측에서 *비정상 API 호출 / 비정상 로그인* *감지 못 함*
4. *암호화된 비밀번호* — 이 자체는 다행이나 *전체 user 테이블 export* 가 *경보 없이* 가능했다는 것 자체가 *데이터 거버넌스 의 부재*

(참고 : *[ZDNet 보도](https://zdnet.co.kr/view/?no=20260611163532)*, *[디지털데일리 보도](https://www.ddaily.co.kr/page/view/2026061115551484107)*)

### 1.3 *모두의 창업 — *2026 년 6 월 15 일 / 합격자 5,000 명***

*공격 벡터* :
- 중기부 운영 *모두의 창업* 사이트
- *합격자 비공개 정보* 에 *접근 시도* 감지
- *이메일 · 아이디어 요약 · 심사평* 유출 (이름 · 연락처는 미유출)
- 일부 보도에 따르면 *AI 코딩 (Claude Code)* 으로 *빠르게* 만든 사이트

*핵심 실패* :
1. *역할 기반 접근 제어 (RBAC) 누락* — *합격자 본인* 만 봐야 할 *심사평* 이 *다른 사용자 토큰* 에 노출
2. *전형적 *IDOR (Insecure Direct Object Reference)* 또는 *권한 검사 누락* 패턴 추정
3. *AI 가 만든 코드* — *기능 은 동작, 보안 검토 는 부재* 의 가능성
4. *5 천 명 의 *프로젝트 IP (지적 재산)* 가 *유출* — *심사평 + 아이디어* 는 *돈으로 환산 어려운 손해*

(참고 : *[파이낸셜뉴스 보도](https://www.fnnews.com/news/202606181438581363)*, *[이코노믹리뷰 — 클로드코드로 만든](https://www.econovill.com/news/articleView.html?idxno=742857)*, *[한국경제 보도](https://www.hankyung.com/article/202606184626i)*)

---

## 2. *세 사건 의 *공통 패턴 *— *놀라울 정도 의 *동일성***

| 항목 | 쿠팡 | 데이원 | 모두의 창업 |
|---|---|---|---|
| *근본 원인 카테고리* | 자격증명 관리 | 자격증명 관리 | 권한/인가 |
| *공격 형태* | 내부자 → 외부 접근 | 외부 → GitHub 키 | 외부 → 권한 우회 |
| *탐지까지 시간* | *5 개월* | *1 개월* | *수 시간 ~ 수 일* |
| *기술적 신규성* | 0 (퇴사자 키 미회수) | 0 (GitHub 시크릿 유출) | 0 (IDOR 추정) |
| *피해 깊이* | 3,370 만 행 | 수백만 행 추정 | 5,000 행 + IP |

**놀라운 사실** — *제로데이 익스플로잇* 도, *고급 APT* 도 아니다. *2003 년 OWASP Top 10* 에 이미 있는 항목들 :
- *A01 — Broken Access Control* (모두의 창업)
- *A02 — Cryptographic Failures* (간접 — 키 관리)
- *A07 — Identification and Authentication Failures* (쿠팡, 데이원)

*"공격자 가 *고도화* 되어서 막을 수 없다"* 는 *현실 과 다르다*. *우리가 *3 년 전 부터 알고 있던 것* 을 *안 했다* 가 *현실*.

---

## 3. *웹 보안 레이어 *— *프론트엔드 · API 의 *공격 면***

### 3.1 *OWASP Top 10 (2021)* — *체크리스트 기준***

| # | 카테고리 | 2026 사건 관련 |
|---|---|---|
| A01 | *Broken Access Control* | *모두의 창업* — *내 합격 정보 의 URL 을 *바꾸면 *남의 정보* 가 나오나? |
| A02 | *Cryptographic Failures* | *쿠팡, 데이원* — *서명키 / API 키* 의 *저장 + 회전* 정책 |
| A03 | *Injection* | *모두의 창업* — *심사평 검색 의 *SQLi* 가능성 (보도 단계라 미확정) |
| A04 | *Insecure Design* | *세 사건 모두* — *"실수해도 막아주는 디자인"* 의 부재 |
| A05 | *Security Misconfiguration* | *데이원* — *GitHub 토큰 scope* 가 *전 권한* |
| A07 | *Identification and Authentication Failures* | *쿠팡* — *JWT 의 *만료 + revoke* 미구현 |

### 3.2 *프론트엔드 가 *해야 하는 7 가지***

```ts
// 1. CSP 헤더 — XSS 의 *최후 방어선*
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{random}';

// 2. HttpOnly + Secure + SameSite=Strict 쿠키
Set-Cookie: session=...; HttpOnly; Secure; SameSite=Strict;

// 3. CSRF token (Same-Site 만으론 *부족* 한 케이스 존재)

// 4. Subresource Integrity (외부 스크립트 의 *변조 방지*)
<script src="https://cdn.example.com/lib.js"
        integrity="sha384-..." crossorigin="anonymous"></script>

// 5. *민감 데이터 의 *localStorage 저장 금지* — *XSS 1 발 에 토큰 전체 탈취*

// 6. *클라이언트 검증 ≠ *서버 검증*. *항상 *서버에서 다시*

// 7. *모든 API 응답 에 *X-Content-Type-Options: nosniff*
```

### 3.3 *서버사이드 인가 *— *IDOR 방어 *의 *코드 패턴***

```kotlin
// ❌ 위험 — 모두의 창업 추정 패턴
@GetMapping("/applications/{id}")
fun getApplication(@PathVariable id: Long): Application =
    applicationRepository.findById(id).orElseThrow()
// → 누구든 id 만 알면 남의 신청서 조회 가능

// ✅ 안전 — 권한 검증 추가
@GetMapping("/applications/{id}")
fun getApplication(
    @PathVariable id: Long,
    @AuthenticationPrincipal user: AuthUser
): Application {
    val app = applicationRepository.findById(id).orElseThrow()
    require(app.applicantId == user.id || user.hasRole("REVIEWER")) {
        throw AccessDeniedException("Not yours")
    }
    return app
}

// 더 안전 — *조회 자체* 를 *내 것만* 으로 좁힘
@GetMapping("/applications/{id}")
fun getApplication(@PathVariable id: Long, @AuthenticationPrincipal user: AuthUser) =
    applicationRepository.findByIdAndApplicantId(id, user.id)
        ?: throw NotFoundException()  // 권한 없음 = 존재 안 함 (정보 누출 0)
```

*마지막 패턴 의 핵심* — *"권한 없음"* 이 아니라 *"존재 하지 않음"* 으로 응답. *공격자 가 *id 가 *실제 존재 하는지* 도 *못 알아냄*. *information disclosure* 차단.

---

## 4. *백엔드 보안 레이어 *— *자격증명 · 인증 · 로깅***

### 4.1 *시크릿 관리 *— *쿠팡 · 데이원 의 *진짜 교훈***

```
[ 안티 패턴 ]                                          [ 권장 패턴 ]

env 변수 에 *영구 JWT 키*                              → KMS / Vault 의 *동적 키*
GitHub Personal Access Token *전 권한*                 → *Fine-grained PAT* 또는 *GitHub App*
"우리 시크릿 어디 있나" *모름*                          → *모든 시크릿* 의 *registry + owner + rotation 주기*
로테이션 *한 번도 안 함*                                → *90 일 자동 로테이션*
퇴사자 키 회수 *수동*                                  → *IdP 연동* — 계정 비활성화 = 자동 invalidation
```

### 4.2 *JWT 의 *함정 5 가지***

쿠팡 사건의 *핵심* — *JWT 가 *공격 표면 이 되는 이유*.

1. **무한 만료 토큰** — *Long-lived JWT* 는 *훔치면 영원히 사용*. *Access 는 15 분 / Refresh 는 7 일* 권장.
2. **서명키 의 *영구 사용*** — *키 가 한 번 새면 *기존 발급 토큰 전부 유효*. *Key rotation 가능 한 구조* 필요.
3. **`none` 알고리즘 허용** — *2015 년 부터 알려진 *고전 취약점*. 라이브러리에서 *명시적 차단* 필수.
4. **Stateless 의 *함정* — revoke 불가** — *비밀번호 변경* 이나 *퇴사 처리* 시 *세션 즉시 무효* 못 함. *Redis 의 *revoke list* 또는 *짧은 만료 + Refresh* 로 보완.
5. **Claims 에 *민감 정보** — JWT 의 payload 는 *base64* 일 뿐 *평문*. *비밀번호 / 주민번호 절대 금지*.

### 4.3 *Spring Boot 의 *시크릿 관리 패턴***

```yaml
# ❌ application.yml 에 평문
jwt:
  secret: my-super-secret-key
  
# ✅ AWS Secrets Manager + 환경 마다 다른 키
spring:
  config:
    import: "aws-secretsmanager:lemuel/${spring.profiles.active}/secrets"
  
# 코드에선 — 키 가 *코드 어디 에도 없음*
@Value("${jwt.secret}")
private lateinit var secret: String
```

추가 — *Vault 의 *dynamic database credentials* 패턴* — *DB 비밀번호 도 *5 분 짜리 동적 발급*. *유출 돼도 5 분 후 *자동 만료*.

### 4.4 *로깅 + 이상 탐지 *— *쿠팡 5 개월 침묵 의 *진짜 원인***

쿠팡 의 *근본 실패* — *외부 IP* 에서 *5 개월간 *비정상 API 패턴* 이 *감지 통과*.

```
[ 정상 트래픽 의 *시그니처* ]            [ 비정상 의 *시그니처* ]
- 한국 IP 90%                            - 중국 IP 에서 *마스터 API* 호출
- 모바일 UA 60%                          - curl/python UA
- 분당 *몇 건 의 본인 데이터*             - 분당 *수천 건 의 *전체 사용자* 조회
- *세션 의 lifecycle* 정상                - *세션 없이 raw JWT* 만 사용
```

*이상 탐지 의 *기본 메트릭* * :

1. *비정상 비율 의 *조회 / 변경 비율* — *읽기 의 *폭증*
2. *비정상 의 *지리적 위치*
3. *비정상 의 *시간대 패턴*
4. *API 키 사용 빈도 의 *돌연변이*
5. *4xx / 5xx 비율 의 *돌연변이*

*Falco* (eBPF), *Wazuh* (오픈소스 SIEM), *AWS GuardDuty*, *클라우드 의 *CloudTrail* — *오픈소스 만으로도 *기본은 구축*.

### 4.5 *코드 의 *시크릿 누출 방지* — *데이원 의 교훈***

```sh
# 1. pre-commit hook — *시크릿 패턴* 차단
brew install gitleaks
gitleaks protect --staged  # 커밋 전 자동 검사

# 2. CI 에서 *재검사*
- name: Secret scan
  uses: gitleaks/gitleaks-action@v2

# 3. GitHub 의 *Push Protection*
설정 → Code security → Push protection 활성화
  → *AWS 키 / Stripe / GitHub PAT* 등 *수십 패턴* 자동 차단

# 4. 이미 PR 된 시크릿 도 *주기적 스캔*
trufflehog git file://. --since-commit HEAD~100
```

*"시크릿이 한 번 새면 *복구 불가*"* — *git 의 *불변성* 때문에 *commit 해도 *amend 로 못 지움*. *반드시 *로테이션* 까지 해야 *진짜 차단*.

---

## 5. *네트워크 보안 레이어 *— *제로 트러스트 의 *현실***

### 5.1 *전통 모델 *— *왜 깨졌는가***

```
[ 옛날 모델 ]                              [ 현재 ]
- 사내망 = 신뢰                              - 사내망 ≠ 신뢰
- VPN 으로 들어오면 *모든 내부 접근* OK     - VPN ≠ 인증
- 방화벽 *경계 안* 은 안전                    - *경계 의 의미* 가 사라짐
                                                (클라우드 + SaaS + 재택)
```

쿠팡 사건의 *네트워크 관점* — *전 직원 의 키* 가 *외부 IP* 에서 *내부 API* 를 *호출 가능 했던 구조*. *제로 트러스트 였다면* *키 가 정상이어도 *기기 + IP + 행동* 이 *비정상이면 차단*.

### 5.2 *제로 트러스트 의 *5 원칙* (NIST SP 800-207)*

1. *모든 데이터 / 서비스* 는 *리소스*
2. *모든 통신* 은 *위치 와 무관* 하게 *보안* 적용
3. *세션 단위* 의 *접근 권한*. *상시 유효 ≠ 영구 유효*
4. *접근 결정* 은 *정책 + 동적 신호* (디바이스 / IP / 행동)
5. *모든 자산* 의 *무결성 + 보안 상태* *지속 모니터링*

### 5.3 *현실적 구현 — *오늘 할 수 있는 것***

```
[ 짧은 항목별 ]

✅ VPN → *Cloudflare Access* / *Tailscale ACL* — *애플리케이션 단위 인증*
✅ DB 직접 노출 → *프라이빗 서브넷 + Bastion + SSO 로그인*
✅ 사내 도구 → *SSO (Okta / Google Workspace) + MFA 강제*
✅ 서버 간 통신 → *mTLS* (서로 의 인증서 검증)
✅ 외부 API 키 → *IP 화이트리스트* + *rate limit*
✅ Kubernetes 의 *NetworkPolicy* — *Pod 간 통신* 도 *명시적 허용 만*
```

### 5.4 *Kubernetes 의 *네트워크 분리* *— *내 클러스터 경험***

[내 *Lemuel K3s 클러스터*](/2026/05/04/homelab-infrastructure.html) 의 5 노드 (lemuel/louise/david/ilwon/solomon) 도 *동일 원칙* 적용 :

```yaml
# settlement-prod 의 *모든 Pod* 는 *명시적 허용된 트래픽 만*
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: settlement-deny-all
  namespace: settlement-prod
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
# → 같은 namespace 안 에서도 *기본 차단*. *허용 NetworkPolicy* 를 *추가 명시 해야 통신*
```

*결과* — *공격자 가 *한 Pod 를 *침투* 해도 *수평 이동 (lateral movement)* 이 *원천 차단*. *데이원 사건* 의 *"GitHub 키 1 개 로 *전 서비스* 영향"* 패턴 의 *근본 차단*.

---

## 6. *내부자 위협 *— *쿠팡 사건 의 *진짜 의미***

*외부 해킹* 보다 *훨씬 어려운 문제*. *접근 권한이 *합법적인 사람* 이 *악의* 를 가질 때.

### 6.1 *통제 의 *4 단계***

1. **Need-to-know** — *알 필요 없는 데이터* 는 *조회 자체 차단*
2. **Need-to-do** — *실행 필요 없는 작업* 은 *권한 없음*
3. **Separation of Duties** — *돈 만지는 사람 ≠ *감사 하는 사람*
4. **Just-in-Time access** — *24 시간 영구 권한 X*. *티켓 발급 시 *2 시간* 만 부여*

### 6.2 *퇴사 프로세스 의 *기술 체크리스트***

쿠팡 의 *결정적 실패* — *HR 의 퇴사 처리 ≠ 기술 자격증명 회수*.

*제대로 된 *오프보딩* * :

```
[ HR 시스템 ] → 퇴사 처리
    ↓ (자동 트리거)
[ IdP (Okta/Workspace) ] → 계정 비활성화
    ↓ (SCIM)
[ 각 시스템 자동 회수 ]
    ├─ AWS IAM 사용자 비활성화
    ├─ GitHub 조직 멤버 제거
    ├─ Slack / Notion / Linear 비활성화
    ├─ VPN 인증서 revoke
    ├─ JWT signing key — *그 사람 한정* 의 키는 *즉시 폐기*
    └─ DB 직접 계정 비활성화 + 비밀번호 변경
```

*Just-in-Time 접근* 이라면 *애초에 *영구 키 가 없음*. *퇴사 처리* 가 *자동* 으로 *접근 종료*.

### 6.3 *감시 ≠ 신뢰 부족** — *왜 받아들여야 하는가***

*"개발자 를 *감시 한다" 는 *문화 적 거부감* — *이해함*. 하지만 :
- *Audit log* 는 *공격자 가 아닌 *개발자 의 *알리바이*. *내가 안 했다* 의 *증명 수단*
- *명시적 *행동 정책* + *투명한 로깅* + *오프보딩 자동화* = *모두 의 *책임 의 균형*

*"신뢰 한다" 는 *통제 의 *반대* 가 아니다*. *통제 가 있어야 *신뢰 가 가능*.

---

## 7. *AI 시대 의 *새로운 공격면 *— *모두의 창업 사례***

*[이코노믹리뷰 보도](https://www.econovill.com/news/articleView.html?idxno=742857)* — *"클로드코드로 만든 모두의 창업 사이트, 5,000 명 정보 줄줄"*.

이게 *2026 의 *진짜 변곡점*. *AI 가 코드 를 빠르게 만들 수 있는데 *보안 검토 의 *시야 가 빠진다* 면 *결과는 이렇다*.

### 7.1 *AI 코드 의 *전형적 보안 누락* 5 가지*

1. **인가 검사 누락** — *기능 은 동작*. *"내 데이터" 라는 가드 가 빠짐*
2. **IDOR** — *URL 의 *id* 가 *그대로 쿼리* 에 들어감*
3. **민감 데이터 의 *기본 노출* — *response 에서 *불필요 한 필드* 까지 다 내려옴*
4. **로깅 부재 또는 *과잉* — *민감 정보 가 *로그 에 남음*
5. **rate limit / brute force 방어 누락**

### 7.2 *방어 — *AI 가 만든 코드 의 *체크 의무***

내 *[어제 글 — 시니어 7 가지 기준](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html)* 의 *3 번 — *코드 리뷰* * 가 *바로 이것*. *AI 가 만든 코드 도 *보안 시야* 를 *반드시 통과*.

*최소한* :

```
[ AI 코드 의 *보안 체크 리스트* ]

□ 모든 GET/PUT/DELETE 가 *본인 데이터 만 / 권한 있는 데이터 만* 보장 하는가
□ 모든 입력 이 *서버 측 검증* 을 거치는가
□ 모든 SQL 이 *Prepared Statement / ORM 파라미터화*
□ 응답 의 모든 필드 가 *공개해도 되는 것* 인가
□ Rate limit 가 *민감 endpoint* 에 있는가
□ 시크릿 이 *코드 / 환경변수* 에 *평문 없는가*
□ 인증 토큰 의 *만료 + revoke* 가 가능 한가
□ Audit log 가 *민감 작업* 에 남는가
```

이 *8 가지* 를 *AI 에게 *추가 검토* 시킬 수도 있다. 다만 *최종 판단* 은 *사람 의 시야*. 위 *모두의 창업* 사례 가 *그 시야 의 *부재* 가 *어떤 결과* 를 낳는지 의 *증거*.

---

## 8. *지금 당장 *3 분 안 에 할 수 있는 *7 가지***

내 시스템 / 회사 의 *최소한* :

- [ ] *GitHub* 설정 → Code security → *Push protection* + *Dependabot* 활성화
- [ ] *gitleaks pre-commit hook* 설치 — `brew install gitleaks` + `gitleaks protect --staged`
- [ ] *.env / *.key / *.pem* 가 *.gitignore 에 있는지* 확인
- [ ] *내 *Personal Access Token* 의 scope 가 *전 권한* 인지 확인 → *fine-grained* 로 좁히기
- [ ] *DB 의 *root 비밀번호* 가 *코드 에 평문* 인지 확인 → *최소한 환경변수, 가능 하면 Vault*
- [ ] *내 프로젝트 의 *기본 endpoint* — *"GET /users/{id}"* 가 *내 거 만 보장* 인지 점검
- [ ] *퇴사자 의 *접근 권한* — *지난 6 개월 퇴사자* 의 *GitHub / AWS / DB* 권한 *남아 있는지* 확인

가장 짧고 가장 효과 큰 7 가지. *세 사건 모두* *이 7 가지 만 있었어도* *피해 의 *80% 이상* 막힌다*.

---

## 9. *맺음 — *세 사건 의 *공통 교훈***

| 사건 | 표면 원인 | *진짜 원인* |
|---|---|---|
| 쿠팡 | 퇴사자 키 미회수 | *오프보딩 의 *기술-HR 분리* |
| 데이원 | GitHub 키 유출 | *시크릿 의 *권한 분리 + 모니터링* 부재 |
| 모두의 창업 | IDOR 추정 | *AI 빠른 개발 의 *보안 검토 의 부재* |

*공통 점 의 *진짜 원인* * : *기술 이 아니라 *프로세스*.

*제로데이 가 무서운 게 아니다*. *우리가 *3 년 전 부터 알고 있던 것 을 안 한다* 가 *진짜 위험*. *AI 가 코드 를 만들어 줄수록*, *시니어 의 *보안 시야* 의 *상대 가치* 가 *더 올라간다*. *바이브 코딩 의 시대* 일수록 *보안 책임 의 시야* 가 *희소 자원*.

내 *Settlement 시스템* 도 *이 세 사건 의 패턴* 으로 *역으로 점검 한다* :
- *Outbox 의 *event_id UNIQUE 가 *idempotency* 의 *3 단 방어*
- *JWT 의 *15 분 / Refresh 7 일*
- *Audit log* 의 *민감 작업 100% 기록*
- *Read-only Projection* 으로 *settlement ↔ order* 의 *코드 의존 0*

*같은 원리* 가 *이 글 의 모든 레이어*. *내 시스템* 도, *우리 회사 시스템* 도, *내가 만드는 다음 시스템* 도 — *같은 7 가지 체크리스트* 부터.

내일 *내 시스템 이 *세 사건 의 4 번째* 가 되지 않으려면* — *오늘 *3 분* 부터*.

---

## *출처 / Further reading*

*쿠팡* :
- [2025 보안 사고·이슈 결산-13 — 쿠팡 민낯 3,370 만 명 (보안뉴스)](https://m.boannews.com/html/detail.html?tab_type=1&idx=141221)
- [쿠팡 3,370 만 개인정보 유출, 5 가지 충격적 진실 (법무법인 지향)](https://www.jihyanglaw.com/?p=3678)
- [2026 내부자 위협 대응 리포트 — 쿠팡 해킹 사태 의 경고 (보안뉴스)](https://m.boannews.com/html/detail.html?idx=142906)

*데이원컴퍼니 / 패스트캠퍼스* :
- [데이원컴퍼니 도 개인정보 유출 — 규모 파악 중 (ZDNet)](https://zdnet.co.kr/view/?no=20260611163532)
- [성인교육 플랫폼 데이원컴퍼니 개인정보 유출 (디지털데일리)](https://www.ddaily.co.kr/page/view/2026061115551484107)
- [2026 보안 핫 키워드-3 — 모두 다 털린 대한민국, 긴급 자물쇠는 2 차 인증 (보안뉴스)](https://m.boannews.com/html//detail.html?idx=141319)

*모두의 창업* :
- [모두의 창업 합격자 5 천 명 아이디어·심사평 유출 (파이낸셜뉴스)](https://www.fnnews.com/news/202606181438581363)
- [클로드코드로 만든 모두의 창업 사이트, 5,000 명 정보 줄줄 (이코노믹리뷰)](https://www.econovill.com/news/articleView.html?idxno=742857)
- [중기부 모두의 창업 합격자 정보 유출 확인 (한국경제)](https://www.hankyung.com/article/202606184626i)
- [6 만 명 몰린 모두의 창업, 개인정보 유출 의혹 (머니투데이)](https://www.mt.co.kr/amp/future/2026/06/17/2026061713382194585)

---

*관련 글*

- [*바이브 코딩* 과 *AI 시대 시니어 개발자* 의 *7 가지 기준*](/2026/06/18/vibe-coding-and-senior-developer-7-criteria.html) — *모두의 창업* 의 *AI 코드 의 *보안 부재* 의 *프레임*
- [*Transactional Outbox 패턴 *과 비동기 통합 *깊이 들여다 보기*](/2026/06/15/transaction-outbox-pattern-async-integration-deep-dive.html) — *3 단 멱등 방어* 의 *교과서 패턴*
- [*Kafka 의 운영 — settlement 의 실전 패턴*](/2026/06/17/kafka-in-production-settlement.html) — *이벤트 시스템 의 *보안 경계*
