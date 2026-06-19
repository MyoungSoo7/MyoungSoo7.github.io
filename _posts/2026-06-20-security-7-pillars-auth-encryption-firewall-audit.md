---
layout: post
title: "*보안* 의 *7 기둥* — *인증 / 인가 / 암호화 / 위변조 검증 / 방화벽 / 감사 로그 / 시큐어 코딩*"
date: 2026-06-20 02:45:00 +0900
categories: [security, backend, devsecops]
tags: [authentication, authorization, encryption, hmac, firewall, audit-log, secure-coding, owasp, spring-security, oauth2, jwt, tls, aes, rbac, abac]
---

> *"보안 은 *문제 가 생긴 후에 *생각 하는 것"* — 이 발상 자체 가 *문제 의 시작* 이다.
>
> 보안은 *기능* 이 아니라 *속성*. *한 번 *추가 하고 끝* 나는 것이 아니라 *모든 계층 에 *얇게 *스며들어야 하는 *횡단 관심사 (cross-cutting concern)*. *인증 가 *되어 있어도 *인가 가 *허술* 하면 뚫리고, *인가 까지 다 잡았어도 *암호화 안 된 통신* 으로 *세션 토큰 이 새면* 의미 없다.
>
> 그래서 보안은 *7 가지 기둥* 으로 *각각 따로 *동시에* 설 수 있어야 한다 — *어느 하나 가 무너져도 *다른 6 개 가 *받쳐주는 *defense in depth*.
>
> 이 글은 *백엔드 개발자 의 *현실적 관점* 에서 *7 기둥 각각 의 *왜 → 어떻게 → Spring Boot 코드 → 함정* 까지 *체계적 으로 *분해* 한다.

내 *5 편 성능 / 인프라 연작* 의 *후속 자매편* :
- [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
- [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
- [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
- [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
- [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)

성능 / 관측 / 비동기 의 *기술 적 깊이* 위에 *보안 의 횡단 관심사* 가 *마지막 으로 *얹혀야 *프로덕션* 이 *완성* 된다.

---

## TL;DR — *한 줄 결론*

> 보안은 *7 개 기둥* 의 합 :
> - **인증** (*Authentication*) — *너 누구야?* — *비밀번호 + MFA + JWT/OAuth2*.
> - **인가** (*Authorization*) — *너 *그거 *해도 돼?* — *RBAC + ABAC + 자원 단위 권한*.
> - **데이터 암호화** (*Encryption*) — *읽으려면 키를 가져와* — *TLS + AES-256-GCM + KMS*.
> - **위변조 검증** (*Integrity*) — *바꿨는지 *알 수 있어야 해* — *HMAC + 디지털 서명 + Merkle tree*.
> - **방화벽** (*Network Defense*) — *오지 말아야 할 곳은 *못 오게* — *L3/L4 + L7 WAF + Zero Trust*.
> - **감사 로그** (*Audit Log*) — *누가 *언제 *뭘 *했는지 *기록* — *append-only + 무결성 보호*.
> - **시큐어 코딩** (*Secure Coding*) — *처음부터 *틈 을 *만들지 않기* — *OWASP Top 10 + 입력 검증 + Least Privilege*.
>
> *7 개 가 *각자 *제대로 서 있을 때* *어느 하나 가 *뚫려도 *다른 6 개 가 *받쳐 준다*. *defense in depth* 가 *현대 보안 의 *유일한 신뢰 모델*.

---

## 1. *왜 *7 가지 인가* — *Defense in Depth 의 철학*

### 1.1 *단일 방어 의 *함정*

> *"우리는 *VPN 뒤에 있어서 *안전 합니다"* — 2025 년의 *대부분 *유출* 사고 의 *공통 변명*.

| 단일 방어 | 무너지는 시나리오 |
|---|---|
| *방화벽 만 의존* | *내부자* 침해 / *VPN 자격증명 탈취* 시 *내부 평문 통신 노출* |
| *HTTPS 만 의존* | *세션 토큰 탈취* (XSS / CSRF) — *암호화 와 무관* |
| *인증 만 의존* | *권한 검증 누락* → *IDOR* (Insecure Direct Object Reference) |
| *암호화 만 의존* | *키 관리 실패* / *암호화된 백업 노출* → 결국 평문 |
| *코드 리뷰 만 의존* | *런타임 의 *invariant 깨짐* 못 잡음 (입력 변조) |

→ *어느 단일 layer 도 *충분 하지 않다*. *NIST Cybersecurity Framework* 와 *ISO 27001* 의 *공통 권고* : *layered defense*.

### 1.2 *Zero Trust 의 *원칙*

NIST SP 800-207 의 *7 원칙* 중 핵심 :

1. *모든 자원 접근 은 *resource session 단위* 로 인증*.
2. *내부/외부 구분 *없이* *모두 검증*.
3. *최소 권한* (Least Privilege).
4. *암호화 가 *기본*. 평문 은 *예외*.
5. *지속적 모니터링 + 검증*.

> *"내부 네트워크" = "안전"* 가설은 *2010 년대 사고* 들이 깨뜨렸다. *Equifax (2017)*, *SolarWinds (2020)*, *MOVEit (2023)* 모두 *내부 침투 후 *내부 통신 의 *허술함 을 이용*.

---

## 2. *기둥 1 — 인증 (Authentication)*

> *너 *누구야?*

### 2.1 *3 요소 (Factors of Authentication)*

| 종류 | 예시 | 특징 |
|---|---|---|
| **Knowledge** (*아는 것*) | 비밀번호, PIN, 비밀 질문 | 약함 — 노출 / 추측 / phishing |
| **Possession** (*가진 것*) | OTP, 하드웨어 키 (YubiKey), SMS | 중간 — 분실 / SIM swap |
| **Inherence** (*있는 것*) | 지문, 얼굴, 홍채 | 강함 — 위조 어려움, 그러나 *복구 불가능* (망막은 패치 못 함) |

→ **MFA** = *2 가지 이상의 요소 조합*. 비밀번호 + OTP 가 *현실의 최소 기준*.

### 2.2 *비밀번호 저장 — *해시 함수 의 *진화*

```text
1990 년대 : SHA1, MD5             ← rainbow table 으로 1초 안에 깨짐 (오늘날)
2000 년대 : SHA256 + salt          ← GPU farm 으로 초당 100억 시도 가능
2010 년대 : bcrypt, scrypt         ← 의도적 *느린* 함수 (work factor)
2020 년대 : Argon2id ★            ← 메모리-hard, 시간-hard, GPU 무력화
```

```java
// Spring Security — Argon2 권장
@Bean
public PasswordEncoder passwordEncoder() {
    // 메모리 19MB, iteration 2, parallelism 1 — OWASP 권장값
    return new Argon2PasswordEncoder(16, 32, 1, 19456, 2);
}

// 사용
String hashed = passwordEncoder.encode("plaintext");
boolean matches = passwordEncoder.matches("plaintext", hashed);
```

> **절대 하지 말 것**:
> - 평문 저장 (당연)
> - MD5 / SHA1 / SHA256 만 (rainbow table)
> - 자체 구현 해시 ("내가 더 잘 만들 수 있어")
> - Salt 재사용 / 짧은 salt
> - Pepper 만 (server-side secret) 으로 충분 하다고 믿기

### 2.3 *세션 vs 토큰 — *상태 관리*

```text
[Stateful Session]                    [Stateless JWT]
┌───────────────────────┐             ┌───────────────────────┐
│ Client : SESSION_ID    │              │ Client : JWT (subject, │
│ Server : SESSION_ID →   │              │           exp, claims, │
│          user, role,    │              │           signature)   │
│          last_access    │              │ Server : verify        │
└───────────────────────┘             │          signature only │
                                       └───────────────────────┘
* 단점: Sticky session 또는              * 단점: Revoke 어려움 (만료 전까지 유효)
        외부 store 필요                            Refresh token 별도 필요
* 장점: 즉시 revoke 가능                 * 장점: 서버 무상태, 스케일 쉬움
```

**OAuth 2.1 + OpenID Connect (OIDC) 가 *현재의 표준*** :

- *Authorization Code Flow + PKCE* — 클라이언트 secret 없는 SPA / mobile 의 표준.
- *Refresh Token rotation* — refresh token 도 *한 번 쓰면 즉시 무효화*.
- *ID Token* (OIDC) — JWT 형태, *사용자 신원* 표현.
- *Access Token* — *자원 접근* 용. 짧은 expiry (5~15분).

```java
// Spring Security 6 — OAuth2 resource server
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain api(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(a -> a
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .oauth2ResourceServer(o -> o.jwt(j -> j
                .jwkSetUri("https://auth.example.com/.well-known/jwks.json")))
            .csrf(c -> c.disable())  // Stateless API
            .build();
    }
}
```

### 2.4 *흔한 함정*

- **JWT 의 `alg: none`** — *서명 검증 우회* (2015 년 CVE-2015-9235 의 *전설*).
- **HS256 비밀 키 누출** — JWT 검증 키 가 *Gateway 와 서비스 가 공유* → 한 서비스 침해 시 *모든 JWT 위조*. **RS256 / ES256** (비대칭) 권장.
- **Refresh token 영구 저장** — *revoke 메커니즘 없이* DB 에 보관 → 탈취 시 *영구 접근*.
- **MFA SMS 만** — SIM swap 공격 *유효*. *TOTP (Google Authenticator) 또는 WebAuthn (FIDO2)* 권장.
- **Brute force 무방어** — *rate limit + 점진적 lockout*. *Spring Security Resilience4j*.

---

## 3. *기둥 2 — 인가 (Authorization)*

> *너 *그거 *해도 돼?* — *인증 과 *분리* 되어야 한다.

### 3.1 *3 가지 모델*

| 모델 | 의미 | 예시 |
|---|---|---|
| **RBAC** (Role-Based) | 사용자 → 역할 → 권한 | `ADMIN`, `EDITOR`, `VIEWER` |
| **ABAC** (Attribute-Based) | 속성 ( 사용자 / 자원 / 환경 ) 기반 동적 정책 | `IF user.dept == resource.dept AND time < 18:00` |
| **ReBAC** (Relationship-Based) | 자원 간 관계 그래프 | Google Zanzibar — *"문서 X 의 소유자 의 *친구* 의 *팀원"* |

대부분 *RBAC 으로 시작* → *복잡해지면 ABAC 또는 ReBAC 으로 진화*.

### 3.2 *RBAC 의 *흔한 함정*

```java
// 안티 패턴 — 컨트롤러 마다 역할 체크
@GetMapping("/admin/users/{id}")
public User getUser(@PathVariable Long id, Principal p) {
    if (!hasRole(p, "ADMIN")) throw new ForbiddenException();
    return userRepo.findById(id);
}
// 문제: *모든 endpoint* 마다 *수동 체크* → *한 endpoint 가 누락* 되면 *바로 IDOR*

// 올바름 — declarative 한 정책
@GetMapping("/admin/users/{id}")
@PreAuthorize("hasRole('ADMIN')")    // Spring Security AOP
public User getUser(@PathVariable Long id) {
    return userRepo.findById(id);
}

// 더 세밀하게 — 자원 단위
@GetMapping("/documents/{id}")
@PreAuthorize("@authz.canRead(#id, authentication)")
public Document get(@PathVariable Long id) {
    return docRepo.findById(id);
}
```

### 3.3 *IDOR (Insecure Direct Object Reference)*

가장 흔한 *인가 실수* :

```java
// 안티 — userId 가 URL 의 path variable
@GetMapping("/users/{userId}/orders")
public List<Order> orders(@PathVariable Long userId) {
    return orderRepo.findByUserId(userId);
    // 누가 호출 했는지 *체크 안 함* → URL 의 userId 바꾸면 *남의 주문 조회*
}

// 올바름
@GetMapping("/users/{userId}/orders")
@PreAuthorize("#userId == authentication.principal.id or hasRole('ADMIN')")
public List<Order> orders(@PathVariable Long userId) {
    return orderRepo.findByUserId(userId);
}

// 더 안전 — userId 받지 말기
@GetMapping("/me/orders")
public List<Order> myOrders(Authentication auth) {
    return orderRepo.findByUserId(((User) auth.getPrincipal()).getId());
}
```

→ **OWASP Top 10 2021 #1** : *Broken Access Control* — *전체 사고 의 *94%* 가 이 카테고리*.

### 3.4 *Privilege Escalation 방지*

```text
[수직 escalation] — 일반 사용자 → 관리자
[수평 escalation] — 사용자 A → 사용자 B (같은 권한 이지만 *다른 자원*)
```

대부분의 IDOR 는 *수평 escalation*. *Tenant 격리* 가 *핵심* :

```java
// 멀티 테넌트 — 모든 query 에 *tenant_id* 필터 강제
@Query("SELECT o FROM Order o WHERE o.tenantId = :tenantId AND o.id = :id")
Order findByIdScoped(@Param("tenantId") Long tenantId, @Param("id") Long id);

// 또는 Hibernate Filter 로 *전역 적용*
@FilterDef(name = "tenantFilter", parameters = @ParamDef(name = "tenantId", type = "long"))
@Filter(name = "tenantFilter", condition = "tenant_id = :tenantId")
@Entity
public class Order { ... }

// Aspect 에서 매 요청 시작 시 활성화
session.enableFilter("tenantFilter")
    .setParameter("tenantId", currentTenant());
```

---

## 4. *기둥 3 — 데이터 암호화 (Encryption)*

> *읽으려면 *키를 가져와*.

### 4.1 *3 가지 상태*

| 상태 | 예시 | 표준 알고리즘 |
|---|---|---|
| **In Transit** (전송 중) | API 호출, DB 연결, 내부 RPC | TLS 1.3 + ECDHE + AES-GCM |
| **At Rest** (저장 중) | DB row, 파일, 백업 | AES-256-GCM (data) + RSA-4096 / KMS (key) |
| **In Use** (사용 중) | 메모리 안 데이터 | Intel SGX, AMD SEV (Confidential Computing) |

### 4.2 *TLS 의 *현실*

```text
TLS 1.0 / 1.1 : *deprecated* (2020 RFC 8996). 사용 시 PCI-DSS 위반.
TLS 1.2 : *최소 허용*. 그러나 *cipher 선택 조심* (no CBC, no RC4).
TLS 1.3 ★ : *기본 추천*. cipher 단순화, handshake 1-RTT.
```

**Spring Boot 설정** :
```yaml
server:
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-type: PKCS12
    protocol: TLS
    enabled-protocols: TLSv1.3,TLSv1.2
    ciphers:
      - TLS_AES_256_GCM_SHA384      # TLS 1.3
      - TLS_CHACHA20_POLY1305_SHA256
      - TLS_AES_128_GCM_SHA256
```

**Mutual TLS (mTLS) — 서비스 간 통신** :
- 클라이언트 도 *자신의 cert 제출*. 서버 가 *그 cert 검증*.
- *Service mesh* (Istio, Linkerd) 가 *자동 적용*.
- *Zero Trust 의 핵심 도구*.

### 4.3 *Symmetric vs Asymmetric*

| | Symmetric | Asymmetric |
|---|---|---|
| 키 종류 | *1 개 공유* | *공개키 + 개인키* |
| 대표 알고리즘 | **AES-256-GCM** | **RSA-4096**, **ECDSA-P256**, **Ed25519** |
| 속도 | *수십~수백 GB/s* | *MB/s 수준* |
| 키 분배 | *어려움* (out-of-band) | *공개키 만 배포* |
| 용도 | *대용량 데이터 암호화* | *키 교환, 서명, TLS handshake* |

**실전 패턴** : *Hybrid* — *Asymmetric 으로 *대칭 키* 교환, 그 후 *Symmetric 으로 데이터 암호화*. *TLS 내부 가 정확히 이 패턴*.

### 4.4 *At Rest — *DB 저장 시*

**1) Application-level (envelope encryption)** :
```java
// AES-256-GCM 으로 *개별 row 암호화*
@Converter
public class PiiEncryptor implements AttributeConverter<String, String> {
    @Override
    public String convertToDatabaseColumn(String plain) {
        if (plain == null) return null;
        byte[] iv = SecureRandom.getInstanceStrong().generateSeed(12);
        SecretKey dataKey = kms.getDataKey();  // KMS 에서 가져옴
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, dataKey, new GCMParameterSpec(128, iv));
        byte[] ciphertext = c.doFinal(plain.getBytes(StandardCharsets.UTF_8));
        // IV 와 ciphertext 결합 → Base64
        return Base64.getEncoder().encodeToString(concat(iv, ciphertext));
    }
    @Override
    public String convertToEntityAttribute(String stored) { ... }
}

// 적용
@Entity
public class User {
    @Convert(converter = PiiEncryptor.class)
    private String email;
    @Convert(converter = PiiEncryptor.class)
    private String phone;
}
```

**2) DB-level — *TDE (Transparent Data Encryption)*** :
- PostgreSQL : `pgcrypto` 또는 *block-level TDE* (Cybertec, EDB).
- *디스크 도난 시점* 만 방어. *DB 접근 권한* 자체 가 뚫리면 *무력*.

**3) KMS — 키 의 *분리*** :
- AWS KMS, GCP Cloud KMS, HashiCorp Vault.
- *DEK (Data Encryption Key) 와 *KEK (Key Encryption Key) 분리*.
- *DEK 는 *데이터 와 함께 *암호화 되어 저장* (KEK 으로 암호화). *KEK 는 *KMS 안에서만 보존*.

```text
[Envelope encryption]

Plaintext data → AES-GCM → Ciphertext data
                     ↑
                  DEK (256-bit)
                     ↑
                AES-Wrap → encrypted DEK (DB 에 함께 저장)
                     ↑
                  KEK (KMS 안에 영원히 보관)
```

→ **DB 덤프 가 *유출* 되어도 *KMS 접근 없이는 복호화 불가*. *최후의 방어선*.

### 4.5 *흔한 함정*

- **ECB 모드** — *동일 평문 → 동일 암호문* → 패턴 노출 (펭귄 사진 의 전설).
- **PKCS5 padding + CBC 모드** — *padding oracle 공격* (POODLE, Lucky 13). *GCM 모드 사용*.
- **고정 IV** — *2 번 같은 IV 로 같은 키 사용* → AES-GCM *완전 깨짐*. *반드시 random IV*.
- **자체 구현 암호화** — *KMS 에 위임*. 직접 구현 절대 금지.
- **로그 / 에러 메시지 에 평문 노출** — DEK, IV, secret 이 *로그에 찍히는 사고* 흔함.

---

## 5. *기둥 4 — 위변조 검증 (Integrity)*

> *바꿨는지 *알 수 있어야 한다*. *암호화 와 *별개 임무*.

### 5.1 *암호화 vs 위변조 검증 의 차이*

| | 암호화 (Confidentiality) | 위변조 검증 (Integrity) |
|---|---|---|
| 막는 것 | *읽지 못하게* | *바꾸지 못하게 (또는 알아채기)* |
| 도구 | AES, RSA | HMAC, Digital Signature, Hash |
| 키 | 필요 | *HMAC*: 필요. *서명*: 필요. *Hash*: 불필요 |
| 부산물 | *암호문* | *MAC / 서명 / 다이제스트* |

→ **AES-GCM 같은 *AEAD (Authenticated Encryption)* 는 *둘 다 동시에* 제공** — *암호화 + integrity tag*. 이것이 *현대 권장*.

### 5.2 *HMAC — *Message Authentication Code*

```text
HMAC(key, message) = Hash(key XOR opad || Hash(key XOR ipad || message))
```

대표 : **HMAC-SHA256** — *키 + 메시지* → *256-bit MAC*. *키 없으면 위조 불가*.

**용도** :
- *Webhook 서명* — Stripe, GitHub 의 webhook 이 정확히 이 패턴.
- *API request 서명* — AWS Signature V4.
- *세션 쿠키 무결성* — *서버 비밀 키 로 *서명*, *클라이언트 가 *내용 바꾸면 *서명 깨짐*.

```java
// 예 : Webhook 서명 검증
public boolean verifyWebhook(String body, String receivedSignature, String secret) {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
    byte[] computed = mac.doFinal(body.getBytes(StandardCharsets.UTF_8));
    String computedHex = HexFormat.of().formatHex(computed);
    // *constant-time* 비교 — timing attack 방지
    return MessageDigest.isEqual(
        computedHex.getBytes(StandardCharsets.UTF_8),
        receivedSignature.getBytes(StandardCharsets.UTF_8)
    );
}
```

> **함정** : *`equals()` 로 비교* 하면 *timing attack* — 차이 나는 첫 바이트 위치 에 따라 *응답 시간 가 다름* → 공격자 가 *바이트 별 추측 가능*. *반드시 `MessageDigest.isEqual()` 같은 constant-time 비교*.

### 5.3 *Digital Signature — *비대칭*

| | HMAC | Digital Signature |
|---|---|---|
| 키 | *공유 비밀 키* | *개인키 (서명) + 공개키 (검증)* |
| 부인 방지 | 불가 (둘 다 비밀키 보유) | **가능** (개인키 보유자만 서명 생성) |
| 속도 | 빠름 | 느림 (10~100x) |
| 대표 알고리즘 | HMAC-SHA256 | RSA-PSS, ECDSA, **Ed25519** |

**용도** :
- *코드 서명* (Apple Notarization, Authenticode).
- *Git commit 서명* (`git commit -S`, GPG).
- *Software supply chain* (Sigstore, in-toto).
- *Blockchain 트랜잭션 서명*.

### 5.4 *Merkle Tree — *대규모 데이터 의 무결성*

```text
                Root hash
               /         \
          H(AB)            H(CD)
         /     \          /     \
       H(A)   H(B)     H(C)   H(D)
        |      |        |      |
      data A data B  data C data D
```

→ *N 개 데이터* 의 *위변조 여부* 를 *log(N) 개 해시* 만 확인 하면 됨.

**용도** :
- *Git 의 *모든 commit / tree*.
- *Cassandra 의 anti-entropy repair*.
- *블록체인* (Bitcoin, Ethereum).
- *Certificate Transparency 로그*.

### 5.5 *Hash 의 *현실*

| 알고리즘 | 상태 | 용도 |
|---|---|---|
| MD5 | **깨짐** (2004) | *사용 금지* |
| SHA1 | **깨짐** (2017, SHAttered) | *사용 금지* |
| SHA-256 | 안전 | *대부분 표준* |
| SHA-3 (Keccak) | 안전 | *방어적* 선택 |
| BLAKE3 | 안전 + 빠름 | *고성능 워크로드* |

**비밀번호 와 *일반 Hash 의 차이*** :
- *비밀번호* — *느려야 함* (Argon2, bcrypt).
- *데이터 integrity* — *빨라야 함* (SHA-256, BLAKE3).

→ *비밀번호 에 *SHA-256 만 쓰는 사고* 가 *흔함*. *Argon2id 사용*.

---

## 6. *기둥 5 — 방화벽 (Firewall) + 네트워크 방어*

> *오지 말아야 할 곳은 *못 오게*.

### 6.1 *층별 방어*

| Layer | 방어 도구 | 막는 것 |
|---|---|---|
| L3/L4 (네트워크/전송) | iptables, ufw, AWS Security Group | *IP / 포트 / 프로토콜* 차단 |
| L7 (애플리케이션) | WAF (Cloudflare, ModSecurity, AWS WAF) | SQL injection, XSS, OWASP rule |
| DNS | *DNS 필터링* (Cloudflare 1.1.1.1 for Families) | C2 도메인, 멀웨어 |
| Endpoint | EDR (CrowdStrike, SentinelOne) | 호스트 내부 위협 |
| Identity | *Zero Trust gateway* (Cloudflare Access, BeyondCorp) | *접근 자격* 검증 |

### 6.2 *L3/L4 — *호스트 방화벽*

```bash
# Ubuntu / Debian — ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.0.0/16 to any port 22   # SSH from LAN only
sudo ufw allow 443/tcp                                # HTTPS public
sudo ufw enable

# iptables 직접
iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

> *기본 정책 = DROP*, *예외만 ALLOW*. *whitelist 방식*. 우리 K3s 클러스터 의 *ufw 정책* 도 정확히 이 패턴.

### 6.3 *L7 — *WAF (Web Application Firewall)*

```text
[Internet]
    ↓
[WAF (Cloudflare / ModSecurity)]
    ├ SQL injection pattern        → BLOCK
    ├ XSS pattern                  → BLOCK
    ├ Path traversal (../)         → BLOCK
    ├ Rate limit (100 req/min/IP)  → BLOCK
    ├ Bot detection (CAPTCHA)      → CHALLENGE
    └ Geographic restriction       → BLOCK (특정 국가)
    ↓
[Application]
```

**OWASP Core Rule Set (CRS)** — ModSecurity 의 *기본 룰셋*. *수천 개 의 패턴* 으로 *알려진 공격* 차단.

### 6.4 *Zero Trust — *Gateway 패턴*

기존 *VPN 모델 의 한계* :
- *접속 자격* (VPN 통과) = *내부 자원 모든 접근 허용*.
- *내부자 위협* 또는 *VPN credential 탈취* 시 *광범위 침해*.

Zero Trust :
- *모든 요청* 마다 *인증 + 인가 검증*.
- *Application 별 *별도 정책*.
- *Identity-aware proxy* (Google BeyondCorp, Cloudflare Access).

```yaml
# Cloudflare Access policy 예
- name: admin-only-from-corp-network
  include:
    - email_domain: "company.com"
  require:
    - mfa: true
    - country: KR
    - device_posture: corp-managed
```

→ 우리 클러스터 의 *Cloudflare Tunnel + Cloudflare Access* 조합 이 정확히 이 패턴.

### 6.5 *Egress 제어 — *내보내지 않는 것 도 방어*

대부분 사고 가 *내부에서 *외부 C2 (Command & Control)* 로 *나가는 트래픽* 으로 *데이터 유출*. *Egress 화이트리스트* 가 *현대의 새 표준*.

```yaml
# Kubernetes NetworkPolicy — egress 제한
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-egress
spec:
  podSelector:
    matchLabels:
      app: my-service
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 10.0.0.0/8     # 내부망
    - ports:
        - port: 443              # 외부는 HTTPS 만
      to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 169.254.0.0/16   # link-local 차단
              - 224.0.0.0/4      # multicast 차단
```

---

## 7. *기둥 6 — 감사 로그 (Audit Log)*

> *누가 *언제 *뭘 *했는지 *기록*. *침해 후 *조사 의 *유일한 길*.

### 7.1 *왜 *별도 감사 로그 인가*

> *애플리케이션 로그 와 *감사 로그 는 *별개 의 존재 이유* 가 있다.

| 일반 로그 | 감사 로그 |
|---|---|
| *디버깅 / 모니터링* | *법적 / 규제 / 침해 조사* |
| *덮어쓰기 OK* (rotation) | *append-only, immutable* |
| *손실 OK* (best-effort) | *손실 절대 금지 (보관 의무)* |
| 자유 형식 | *구조화 (action, actor, resource, timestamp)* |

### 7.2 *감사 로그 의 *필수 필드*

```json
{
  "timestamp": "2026-06-20T02:45:12.123Z",   // ISO 8601, UTC
  "request_id": "req_abc123",                  // 트레이싱 연계
  "actor": {
    "user_id": 42,
    "username": "alice",
    "ip": "203.0.113.5",
    "session_id": "sess_xyz"
  },
  "action": "DELETE",
  "resource": {
    "type": "Order",
    "id": 1000023,
    "owner_id": 89
  },
  "outcome": "SUCCESS",   // or DENIED, FAILED
  "reason": "user-initiated",
  "metadata": {
    "user_agent": "Mozilla/5.0",
    "before": {...},      // 변경 전 상태
    "after": {...}        // 변경 후 상태
  }
}
```

### 7.3 *Append-only 보장 — *Trigger / Outbox*

PostgreSQL :
```sql
-- audit_log 테이블 — 절대 수정 / 삭제 못 함
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT now(),
    actor JSONB NOT NULL,
    action TEXT NOT NULL,
    resource JSONB NOT NULL,
    metadata JSONB
);

-- immutability trigger
CREATE OR REPLACE FUNCTION reject_audit_modify() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION reject_audit_modify();
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION reject_audit_modify();
```

→ 우리 *settlement 프로젝트* 의 *settlement_immutability_trigger* 가 정확히 이 패턴.

### 7.4 *외부 저장 — *분리 의 원칙*

> *침해된 시스템 의 *감사 로그 가 *침해된 시스템 의 *DB 에만* 있다면, *공격자 가 *흔적을 지운다*.

**해결** :
- *별도 외부 저장* (CloudWatch, Loki, Splunk, S3 with object lock).
- *write-once, append-only* (S3 Object Lock 의 *Compliance mode*).
- *해시 체이닝* — *각 로그 의 hash 가 *다음 로그 에 포함* (Merkle chain) → *중간 삭제 즉시 탐지*.

```text
log[N+1].prev_hash = SHA256(log[N].content || log[N].prev_hash)
```

### 7.5 *PII / 민감 정보 의 *마스킹*

```java
// 감사 로그 에서 비밀번호 / 카드번호 등 마스킹
public class AuditLogger {
    private static final Pattern CARD = Pattern.compile("\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b");

    public void log(String action, Object payload) {
        String json = mapper.writeValueAsString(payload);
        // PAN 마스킹 — 카드 번호 의 가운데 8 자리 만 *
        json = CARD.matcher(json).replaceAll(m -> {
            String s = m.group().replaceAll("[- ]", "");
            return s.substring(0,4) + "********" + s.substring(12);
        });
        auditStore.write(action, json);
    }
}
```

> *PCI-DSS* 는 *PAN 의 처음 6 + 마지막 4 자리 만* 저장 허용. *전체 저장 시 *위반*.

---

## 8. *기둥 7 — 시큐어 코딩 (Secure Coding)*

> *처음부터 *틈 을 만들지 않기*.

### 8.1 *OWASP Top 10 — 2021 판*

| # | 카테고리 | 예방 |
|---|---|---|
| A01 | Broken Access Control | RBAC + IDOR 방어 (위 기둥 2) |
| A02 | Cryptographic Failures | TLS 1.3 + AES-GCM + KMS (기둥 3) |
| A03 | Injection (SQL, XSS, OS cmd, LDAP) | **Prepared statements + 입력 검증** |
| A04 | Insecure Design | *Threat Modeling*, *최소 권한 설계* |
| A05 | Security Misconfiguration | *기본값 검토*, *secrets 관리* |
| A06 | Vulnerable and Outdated Components | *SBOM + dependency scan* |
| A07 | Identification and Authentication Failures | MFA + 강한 해시 (기둥 1) |
| A08 | Software and Data Integrity Failures | *Sigstore, in-toto, CI/CD 서명* |
| A09 | Security Logging and Monitoring Failures | 기둥 6 |
| A10 | Server-Side Request Forgery (SSRF) | *URL 화이트리스트, 내부망 차단* |

### 8.2 *Injection — *가장 흔한 단일 사고 원인*

```java
// 안티 — SQL injection 가능
String sql = "SELECT * FROM users WHERE name = '" + userInput + "'";
stmt.executeQuery(sql);
// userInput = "'; DROP TABLE users; --" → 테이블 삭제

// 올바름 — PreparedStatement
String sql = "SELECT * FROM users WHERE name = ?";
PreparedStatement ps = conn.prepareStatement(sql);
ps.setString(1, userInput);
ResultSet rs = ps.executeQuery();
```

> JPA / MyBatis 도 *`@Query` 안 의 `'${param}'`* (literal injection) 은 *위험*. *`:param`* (bind) 만 사용.

### 8.3 *Input Validation — *경계에서 *모두 검증*

```java
// Bean Validation (Jakarta Validation)
public class UserCreateRequest {
    @NotBlank
    @Size(min = 3, max = 20)
    @Pattern(regexp = "^[a-zA-Z0-9_]+$")  // 알파벳/숫자/_ 만
    private String username;

    @Email
    @Size(max = 254)
    private String email;

    @Min(0) @Max(150)
    private int age;
}

@PostMapping("/users")
public User create(@Valid @RequestBody UserCreateRequest req) {
    // 통과 한 시점 에 *유효성 검증 완료*
    return userService.create(req);
}
```

> **검증 의 *위치*** : *경계 (controller / API gateway)* 가 *공식 검증*. *internal service 가 *재검증 하는 것 도 *안전* (defense in depth).

### 8.4 *Secrets 관리*

```text
[Anti-pattern]
.env file 에 password 평문
git commit -m "add config"
git push                          ← 공개 저장소 면 *공격자 자동 스캔 후 1분 내 탈취*

[Correct]
- secrets/.env  (gitignore)
- HashiCorp Vault / AWS Secrets Manager / Sealed Secrets / SOPS+age
- *환경 변수 도 *유출 위험* — Docker inspect, /proc/<pid>/environ
- *애플리케이션 시작 시 KMS 에서 *fetch* → 메모리 에만 유지
```

우리 클러스터 의 *SOPS + age* 조합 — *secrets 를 *git 안에 *암호화 보관*, *6 머신 의 age 키 만 *복호화 가능*.

### 8.5 *Dependency 관리*

- **Dependabot / Renovate** — 자동 PR 로 *취약 의존성* 업데이트.
- **Snyk / Trivy / OWASP Dependency-Check** — CI 에서 *CVE 스캔*.
- **SBOM** (Software Bill of Materials) — *내가 쓰는 *모든 라이브러리 의 목록*. CycloneDX, SPDX 표준.
- **License compliance** — GPL 같은 *카피레프트* 의존성 *모니터링*.

```yaml
# GitHub Actions — Trivy 로 의존성 + 컨테이너 이미지 스캔
- name: Run Trivy
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    severity: 'CRITICAL,HIGH'
    exit-code: '1'
```

### 8.6 *Least Privilege — *코드 / 서비스 / 컨테이너*

```yaml
# Kubernetes Pod 의 *비-root 실행*
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    readOnlyRootFilesystem: true   # 파일시스템 *read-only*
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL                       # 모든 Linux capability 제거
```

> *컨테이너 가 *root 로 도는 것 은 *2026 년 에는 *허용되지 않아야 한다*. *기본 deny*.

### 8.7 *CSRF 와 *CORS — *흔한 오해*

```text
CSRF (Cross-Site Request Forgery)
  - 피해자가 *로그인 된 상태* 에서 *공격자 사이트 방문* → 자동 요청 발사
  - 방어: CSRF 토큰 (cookie+header 더블 제출) 또는 SameSite=Strict cookie

CORS (Cross-Origin Resource Sharing)
  - *방어가 아닌 *완화*. 브라우저 가 *허용 origin* 에서만 *credentials 동반 요청 허용*
  - `Access-Control-Allow-Origin: *` + `credentials: true` 조합 *불가능*
  - *서버 측 인가 검증 의 대체 가 *아님* (CORS 우회 가능)
```

> *흔한 실수* : "CORS 를 풀어줬는데 *공격 받아요"* — CORS 는 *방어 가 아니다*. *인증 / 인가 / CSRF 토큰* 이 *진짜 방어*.

---

## 9. *7 기둥 의 *통합* — *Defense in Depth 의 실제*

### 9.1 *사용자 가 API 호출 할 때 — *전체 사슬*

```text
[User] → [DNS]
  ↓ DNS 필터링 (악성 도메인 차단)
[Cloudflare WAF]
  ↓ OWASP CRS, rate limit, bot
[Cloudflare Access]
  ↓ MFA, country, device posture (Zero Trust)
[Cloudflare Tunnel]
  ↓ TLS 1.3, mutual auth
[Ingress / Gateway]
  ↓ TLS 종료, JWT 검증 (인증)
[Application]
  ↓ @PreAuthorize (인가)
  ↓ Input validation (시큐어 코딩)
  ↓ Audit log emit
[Database]
  ↓ Connection encrypted (TLS)
  ↓ Application-level field encryption (PII)
  ↓ Row-level security
  ↓ Audit trigger (immutability)
[Storage]
  ↓ KMS-managed key
  ↓ S3 Object Lock
```

→ *어느 한 layer 가 *뚫려도* *다음 layer 가 *받쳐 준다*. *Defense in depth*.

### 9.2 *대표적 보안 사고 의 *공통 패턴*

거의 모든 큰 사고 가 *2~3 개 기둥 의 동시 실패* :

| 사고 | 무너진 기둥 |
|---|---|
| Equifax 2017 (143M) | A06 (Apache Struts CVE 미적용) + A09 (탐지 76일 지연) |
| Capital One 2019 (100M) | A05 (IAM 잘못 설정 + SSRF) + A04 (메타데이터 service 신뢰) |
| SolarWinds 2020 | A08 (CI/CD 서명 부재) + A07 (개발자 자격증명 탈취) |
| MOVEit 2023 | A03 (SQL injection 0-day) + A09 (며칠 후에야 발견) |

→ *단일 기둥 만 *튼튼* 해도 *나머지 가 *허술* 하면 *결국 뚫린다*.

---

## 10. *백엔드 개발자 의 *보안 체크리스트* — *15 가지*

내가 *PR 머지 전 / 프로덕션 배포 전* 에 *반드시 확인* 하는 *15 가지* :

**인증 / 인가**:
1. *비밀번호 가 *Argon2id / bcrypt* 로 해싱 되는가
2. *JWT 의 `alg`* 가 *RS256 또는 ES256* (대칭 키 공유 위험 없음) 인가
3. *모든 endpoint 에 *@PreAuthorize 또는 *명시적 권한 검증* 이 있는가
4. *path variable 의 *userId / orderId* 가 *현재 사용자 자원인지* 검증 되는가 (IDOR)

**암호화 / 무결성**:
5. *PII 컬럼 (email, phone, address)* 이 *application-level 암호화* 되는가
6. *TLS 1.3 + 강한 cipher* 만 enable 되어 있는가
7. *Webhook / API 서명* 이 *constant-time HMAC 비교* 인가

**시큐어 코딩**:
8. *SQL query 가 *PreparedStatement 또는 *JPA bind* 만 사용 하는가
9. *입력 검증 (`@Valid` + Bean Validation)* 이 *모든 controller* 에 있는가
10. *URL 받는 코드 (SSRF)* 에 *허용 호스트 화이트리스트* 가 있는가
11. *컨테이너 가 *root 가 아닌 사용자* 로 도는가 (`runAsNonRoot: true`)

**방화벽 / 네트워크**:
12. *Egress 화이트리스트* 가 있는가 (외부로 *나가는 트래픽* 도 제한)
13. *NetworkPolicy* 로 *서비스 간 통신 제한* 되어 있는가

**감사 / 모니터링**:
14. *민감 작업 (DELETE, 권한 변경, 결제)* 에 *audit log* 가 *남는가*
15. *비정상 로그인 / rate limit 위반* 등 *알람* 이 *작동* 하는가

---

## 11. *결론 — *보안은 *기능 이 아니라 *속성*

> *"보안 모듈 다 추가 했어요"* 라는 말 자체 가 *위험 신호*. 보안은 *추가하는 것* 이 아니라 *모든 줄 의 코드 에 *스며들어 있는 것*.

7 기둥 정리 :
1. **인증** — *너 누구야* (MFA + 강한 해시 + JWT 적절 사용)
2. **인가** — *너 그거 해도 돼* (RBAC + IDOR 방어 + tenant 격리)
3. **암호화** — *읽으려면 키를* (TLS + AES-GCM + KMS envelope)
4. **위변조 검증** — *바꿨는지 알아야* (HMAC + 서명 + immutable log)
5. **방화벽** — *오지 마* (L3/L4 + WAF + Zero Trust + egress)
6. **감사 로그** — *흔적 남기기* (append-only + 외부 저장 + 해시 체인)
7. **시큐어 코딩** — *처음부터 안 만들기* (OWASP Top 10 + input validation + least priv)

> *defense in depth* 는 *"한 layer 가 *완벽* 하기 를 기대 하지 않는다"* 는 *겸손 의 원칙*. *7 기둥 이 *각자 *80% 만 *작동* 해도 *전체* 는 *통과 확률 (0.2)^7 = 0.00128%*.

*그래서 *7 가지 가 *각자 80% 가 *어느 한 가지 가 *99%* 보다 *훨씬 안전* 하다.

*보안 은 *제품 매니저 가 *요구 안 해도 *백엔드 개발자 가 *의무 적으로 *지켜야 하는 기본기*. *Performance 와 *같은 위계* 의 *횡단 관심사*. *작은 사고 하나 가 *회사 를 *끝낼 수 있는 시대* 에 *우리 가 *덜 보안 한 *코드 를 *덜 짜야 한다*.

---

## *참고*

- *OWASP Top 10 — 2021*, [owasp.org/Top10/](https://owasp.org/Top10/).
- *OWASP Application Security Verification Standard (ASVS) v4.0.3*.
- *NIST SP 800-207*, *Zero Trust Architecture*.
- *NIST SP 800-63B*, *Digital Identity Guidelines — Authentication*.
- *PCI-DSS v4.0* — 결제 카드 처리 표준.
- *Bruce Schneier, *Applied Cryptography*.
- *Spring Security Reference* — Spring Boot 의 실전 구현.
- *Real World Cryptography* (David Wong) — 현대 암호 의 *실무 reference*.
- 자매편 :
  - [*CPU 의 *L1 / L2 / L3 캐시*](/2026/06/18/cpu-l1-l2-l3-cache-and-bottleneck-analysis.html)
  - [*I/O 병목 어떻게 해결하지?*](/2026/06/18/io-bottleneck-how-to-solve.html)
  - [*Virtual Thread* 와 *Carrier Thread* 의 *관계*](/2026/06/19/virtual-thread-and-carrier-thread-relationship.html)
  - [*Prometheus* 가 *수집* 하고 *Grafana* 가 *대답* 한다*](/2026/06/19/prometheus-grafana-metrics-visualization.html)
  - [*논블로킹 I/O 서버*](/2026/06/19/non-blocking-io-server-deep-dive.html)
