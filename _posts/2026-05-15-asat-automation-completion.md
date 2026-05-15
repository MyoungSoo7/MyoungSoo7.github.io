---
layout: post
title: "청각재활 시스템 관리 자동화 완성 — 면접관 1-클릭부터 ELK 알람까지 하루 만에"
date: 2026-05-15 14:00:00 +0900
categories: [project, kubernetes, devops, asat]
tags: [asat, inter-asat, gitops, argocd, k3s, jwt, spring-boot, nextjs, elk, telegram-alert, automation]
---

ASAT (Auditive Spatial Adaptive Training — 청각재활 훈련 시스템) 은 이명 환자와 청각 재활 대상자를 위한 연구용 웹 애플리케이션입니다. Java 25 + Spring Boot 4 + Next.js 16 스택에 PostgreSQL/Redis/MinIO 보조 인프라, 5-노드 K3s 홈랩 위에서 GitOps 로 운영합니다. 어제 오후부터 오늘 새벽까지 하루 안에 **관리·운영 자동화 사이클 전체** 를 완성했고, 그 기록을 정리합니다.

> 이 글에서 다루는 것
> - **요청 → 코드 → 배포 → 검증** 한 사이클을 자동화하는 GitOps 흐름 (inter-asat → GHCR → ArgoCD Image Updater → helm-deploy → 자동 롤아웃)
> - 면접관/심사위원이 회원가입·로그인 없이 한 번에 둘러보는 **데모 로그인** 백엔드/프론트 풀스택 구현 (asat.auth.demo-mode-enabled 플래그 게이트)
> - 한국식 "자동로그인 체크박스" — 영속 쿠키 vs 세션 쿠키 분기, 그리고 백그라운드 토큰 복원이 "안 보이는 자동로그인" 으로 끝나지 않게 라우팅까지 묶기
> - Gmail SMTP 로 이메일 인증 메일 발송 가동 + 인증 링크 frontend-url 절대화
> - Next.js standalone 빌드의 `rewrites()` 빌드 시점 베이크 함정과 catch-all route handler 우회
> - 24+ 네임스페이스 로그를 ELK 로 집계 + 5분 윈도 ERROR 스파이크 Telegram 알람
> - 운영자가 PR 만 보내면 되는 "선언적 운영" 상태에 도달

전체 작업 시간 약 **8 시간**, 그 중 손이 가는 시간은 절반. 나머지는 빌드/롤아웃 대기 + 외부 도구 점검입니다.

---

## 1. 출발점 — 무엇이 빠져 있었는가

ASAT 자체는 잘 돌아가는 상태였습니다.

- Java 25 + Spring Boot 4.0.4 백엔드 (JWT Access 15min + Refresh 7day httpOnly cookie)
- Next.js 16 App Router 프론트엔드 (Web Audio API + Zustand + TanStack Query)
- PostgreSQL 16 / Redis 7 / MinIO 보조 인프라
- K3s 5-노드 위에 5 개 파드(app / frontend / postgres / redis / minio) 분산 운영
- ArgoCD + Image Updater 가 GHCR newest-build 전략으로 자동 sync

문제는 **운영 자동화의 마지막 1 마일** 이 비어 있었습니다.

1. 면접관/심사위원이 portfolio 사이트에 접속해도 회원가입 메일 인증을 거쳐야 내부 진입 가능 → 진입 장벽 너무 높음
2. 회원가입 흐름은 코드상으로 있지만 SMTP 미설정으로 인증 메일이 발송되지 않음 (로그만 찍힘)
3. 인증 메일에 박힌 링크가 `http://localhost:3000/verify-email?token=...` 로 절대화 안 됨
4. 로그인 후 사용자가 "자동 로그인 유지" 를 선택할 수 있는 UI 없음
5. 클러스터 로그가 한 곳에 모이지 않아 운영 이슈 추적은 `kubectl logs` 노가다
6. eln.lemuel.co.kr 의 `/api/*` 가 docker-compose 폐기 후 어디로도 안 가는 dead nginx 라우팅 상태

이걸 하나씩 채워서 **"git push 만 하면 자동로 사이트가 나타나고, 면접관은 클릭 한 번에 둘러보고, 에러 나면 텔레그램으로 알람 오는"** 상태로 끌어올리는 게 목표.

---

## 2. GitOps 사이클 — 코드 → 배포 → 검증의 자율화

ASAT 의 배포 파이프라인 한 줄 요약:

```text
inter-asat git push (master)
  → .github/workflows/k3s-images.yml 이 GHCR 에 backend/frontend 이미지 빌드+푸시
  → ArgoCD Image Updater (newest-build 전략) 가 helm-deploy 리포의
     charts/asat/values.yaml 의 image.tag 를 새 SHA 로 자동 갱신 (write-back-method=argocd)
  → ArgoCD 가 asat-prod Application 을 자동 동기화
  → kubectl rollout 자동, 1~2 분 안에 새 파드로 무중단 교체
```

[이전 글](/2026/05/14/argocd-self-management-app-of-apps/) 에서 다룬 App-of-Apps 패턴 위에 올라가 있어서, **사람이 손대는 부분은 코드 작성과 PR review 뿐** 입니다. 새 기능 하나 추가에 4 번의 push → 4 번의 무중단 배포가 자동으로 흘러갔습니다.

작업 사이클의 정의는 메모리에 박아두었습니다.

> 사용자가 inter-asat 관련 기능을 요청하면:
> 1. inter-asat 리포에 변경사항 push
> 2. K3s 자동배포(ArgoCD) 가 적용되는지 확인 — 롤아웃/이미지/파드 상태 점검
> 3. **eln.lemuel.co.kr 실 서비스에서 기능이 동작하는지 확인** (단순 빌드 성공이나 파드 Ready 만으로 끝내지 않음)
> 4. 위 결과를 사용자에게 경과 보고

"빌드 통과" 가 곧 "배포 완료" 가 아니라는 점이 중요합니다.

---

## 3. 자동로그인 (rememberMe) — 백엔드/프론트의 영속/세션 쿠키 분기

기존 백엔드는 **모든 로그인에 7 일 영속 refresh 쿠키** 를 발급했습니다. 보안상 한 가지 흠 — 공용 PC 에서 로그인한 후 브라우저를 닫지 않으면 7 일간 다른 사람이 접근 가능. 한국식 "자동로그인" 패턴은 사용자가 명시적으로 선택할 수 있어야 합니다.

### 3-1. LoginRequest 에 rememberMe 필드 추가

Java record 에 새 필드를 더하면 기존 클라이언트(필드 미전송)가 500 으로 깨집니다. Jackson 기본 동작상 missing primitive boolean 은 deserialization 실패. `@JsonCreator` 로 명시적 팩토리 메서드를 두고 `Boolean` 로 받아 null→false 변환합니다.

```java
public record LoginRequest(
        @NotBlank @Email String email,
        @NotBlank String password,
        boolean rememberMe
) {
    @JsonCreator
    public static LoginRequest of(
            @JsonProperty("email") String email,
            @JsonProperty("password") String password,
            @JsonProperty("rememberMe") @Nullable Boolean rememberMe
    ) {
        return new LoginRequest(email, password, Boolean.TRUE.equals(rememberMe));
    }
}
```

이 패턴은 다른 API 들에도 유용 — record + Jackson 조합에서 새 필드를 안전하게 추가하는 표준.

### 3-2. AuthController 의 쿠키 발급 분기

```java
private void setRefreshCookie(HttpServletResponse response, String token, boolean rememberMe) {
    String cookie;
    if (rememberMe) {
        long maxAge = tokenProvider.getRefreshTokenValidityMs() / 1000;  // 7d
        cookie = String.format(
                "refresh_token=%s; HttpOnly; Secure; SameSite=Strict; Path=%s; Max-Age=%d",
                token, REFRESH_COOKIE_PATH, maxAge);
    } else {
        // 세션 쿠키 — Max-Age 미지정 → 브라우저 종료 시 자동 삭제
        cookie = String.format(
                "refresh_token=%s; HttpOnly; Secure; SameSite=Strict; Path=%s",
                token, REFRESH_COOKIE_PATH);
    }
    response.addHeader("Set-Cookie", cookie);
}
```

curl 로 검증:

```text
rememberMe=true  → Set-Cookie ... Path=/api/v1/auth; Max-Age=604800
rememberMe=false → Set-Cookie ... Path=/api/v1/auth   (Max-Age 없음 = 세션 쿠키)
```

### 3-3. 프론트엔드 — 진짜 함정은 UX 쪽이었다

체크박스 추가는 단순합니다. 문제는 다른 곳에 있었습니다.

Providers.tsx 가 앱 부팅 시 `/auth/refresh` 를 시도해서 access token 을 복원합니다. 영속 쿠키가 살아있으면 성공하지만 — **사용자는 여전히 `/login` 페이지를 보고 있습니다**. 자동로그인이 백그라운드로 일어나도 라우팅이 따라가지 않으면 "안 됨" 으로 느낍니다.

수정:

```tsx
// app/(auth)/login/page.tsx
useEffect(() => {
  if (isAuthenticated) {
    router.replace("/dashboard");
  }
}, [isAuthenticated, router]);

// app/page.tsx — 랜딩 페이지도 client component 로 전환
"use client";
const { isAuthenticated } = useAuth();
useEffect(() => {
  if (isAuthenticated) router.replace("/dashboard");
}, [isAuthenticated, router]);
```

이제 영속 쿠키가 살아있는 사용자가 다시 방문하면 — 로그인 페이지가 잠깐 깜빡한 뒤 자동으로 대시보드로 이동합니다.

```text
[브라우저 종료]
[다음 날 https://eln.lemuel.co.kr 진입]
  → Providers 가 /auth/refresh 호출 (쿠키 존재)
  → 200 + accessToken 발급 → isAuthenticated=true
  → /login 또는 / 의 useEffect 가 router.replace('/dashboard')
  → 사용자는 "어 자동으로 들어갔네" 경험
```

UX 가 마지막 1 줄에 달려있다는 교훈.

---

## 4. 면접관용 1-클릭 데모 로그인

자동로그인은 이미 가입한 사용자용이지만, 처음 방문한 면접관은 회원가입조차 거치기 싫어합니다. "관리자 화면 보여줘" 와 "어떻게 들어가지" 사이의 1 분 침묵이 prequal 단계의 평가를 좌우합니다.

### 4-1. 백엔드 데모 로그인 엔드포인트

```java
@Transactional(readOnly = true)
public LoginResult demoLogin(UserRole role) {
    if (!demoModeEnabled) {
        throw new BusinessException(ErrorCode.INVALID_CREDENTIALS);
    }
    String seedEmail = role == UserRole.ADMIN ? "admin@asat.com" : "trainee@asat.com";
    User user = userRepository.findByEmail(seedEmail)
            .filter(u -> u.isActive() && u.isEmailVerified() && u.getRole() == role)
            .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));

    String accessToken = tokenProvider.createAccessToken(user.getId(), user.getEmail(), user.getRole().name());
    String refreshToken = tokenProvider.createRefreshToken(user.getId());
    return new LoginResult(new TokenResponse(accessToken), refreshToken, false);
}
```

핵심 — `demoModeEnabled` 환경 플래그 (`asat.auth.demo-mode-enabled=true` 일 때만 동작). 운영 보안이 중요한 환경에서는 절대 켜선 안 되는 기능이지만 portfolio 사이트에서는 의도된 노출입니다.

helm-deploy `values.yaml` 에서:

```yaml
app:
  env:
    ASAT_AUTH_DEMO_MODE_ENABLED: "true"  # portfolio only
```

추가로 `GET /api/v1/auth/demo-mode` 는 `{"enabled": true|false}` 만 반환해서 — **프론트가 버튼을 노출할지 결정** 할 수 있도록.

### 4-2. 프론트엔드 — 면접관용 카드

로그인 페이지 상단에 amber 톤 카드와 큰 버튼 2 개를 띄웠습니다.

![ASAT 로그인 — 면접관 데모 카드 + 자동로그인 체크박스](/assets/images/asat-automation/02-asat-login-demo-buttons.png)

- "면접관 / 심사위원이신가요?" 헤더
- "회원가입 없이 클릭 한 번으로 내부 화면을 둘러볼 수 있습니다"
- [관리자로 둘러보기] [훈련자로 둘러보기]

클릭하면 `POST /api/v1/auth/demo-login {"role":"ADMIN"|"TRAINEE"}` → 200 + 토큰 + 쿠키 → router.push('/dashboard'). 면접 자리에서 5 초면 끝.

```text
$ curl -X POST https://eln.lemuel.co.kr/api/v1/auth/demo-login \
    -H "Content-Type: application/json" -d '{"role":"ADMIN"}'
HTTP/2 200
Set-Cookie: refresh_token=eyJ...; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth
{"accessToken":"eyJ...","tokenType":"Bearer"}
```

---

## 5. Gmail SMTP — 회원가입 인증 메일 가동

`spring-boot-starter-mail` 은 의존성이 있었는데 SMTP host/port/user/pw 설정이 비어 있어 EmailService 가 콘솔에만 로그를 찍고 있었습니다.

```text
WARN EmailService: JavaMailSender not configured.
Verification email for iamipro@naver.com (token in URL):
http://localhost:3000/verify-email?token=SQRIhTlxSa...
```

두 가지 동시 수정:

### 5-1. Gmail App Password + K8s Secret

Gmail 은 2022 년부터 일반 비밀번호로 SMTP 접속을 거부합니다. App Password 16 자리를 발급받아 K8s secret 에 직접 patch:

```bash
$ kubectl -n asat-prod patch secret asat-app-secret --type=merge \
    -p '{"data":{"SPRING_MAIL_PASSWORD":"'$(echo -n 'zpjpzbyfxwoitbwz' | base64)'"}}'
```

비번 자체는 Git 에 절대 들어가지 않게 secret 으로만. values.yaml 에는 비번 외 모두:

```yaml
app:
  env:
    ASAT_FRONTEND_URL: "https://eln.lemuel.co.kr"
    ASAT_EMAIL_FROM: "jinsim37@gmail.com"
    SPRING_MAIL_HOST: "smtp.gmail.com"
    SPRING_MAIL_PORT: "587"
    SPRING_MAIL_USERNAME: "jinsim37@gmail.com"
    SPRING_MAIL_PROPERTIES_MAIL_SMTP_AUTH: "true"
    SPRING_MAIL_PROPERTIES_MAIL_SMTP_STARTTLS_ENABLE: "true"
    SPRING_MAIL_PROPERTIES_MAIL_SMTP_STARTTLS_REQUIRED: "true"
```

### 5-2. 즉시 검증

```bash
$ curl -X POST https://eln.lemuel.co.kr/api/v1/auth/resend-verification \
    -d '{"email":"iamipro@naver.com"}'
HTTP=200

$ kubectl -n asat-prod logs deploy/asat-app --since=30s | grep -i mail
INFO i.c.rd.application.service.EmailService : Verification email sent to iamipro@naver.com
```

수신함 확인 → 도착 ✓. STARTTLS 587 + App Password 조합으로 발송 성공.

이제 인증 메일 흐름:

```text
회원가입 → token_hash 저장 + @TransactionalEventListener(AFTER_COMMIT) 발행
  → EmailService 가 Gmail SMTP 로 발송 (https://eln.lemuel.co.kr/verify-email?token=... 절대 URL)
  → 사용자 클릭 → email_verified=true → 로그인 가능
```

---

## 6. Next.js standalone 의 rewrites 베이크 함정

이게 오늘 작업 중 **가장 까다로웠던 부분** 입니다.

eln.lemuel.co.kr 의 nginx 가 `/api/*` 를 죽은 docker-compose 포트 `127.0.0.1:8082` 로 보내고 있었습니다. 클러스터 마이그레이션 후 라우팅 정리가 안 된 상태. 모든 로그인 시도가 사실상 작동하지 않았습니다.

가장 깔끔한 해결: **Next.js 가 같은 origin 으로 들어온 `/api/*` 를 백엔드 서비스로 프록시**. nginx/Cloudflare 가 라우팅을 분기할 필요 없이 그냥 Next.js 한 곳으로 다 보내면 됨.

처음 시도 — `next.config.ts` 에 rewrites:

```ts
const internalApiUrl = process.env.NEXT_INTERNAL_API_URL || "http://localhost:8183";

const nextConfig: NextConfig = {
  rewrites: async () => [
    { source: "/api/:path*", destination: `${internalApiUrl}/api/:path*` },
  ],
};
```

helm 차트에서 `NEXT_INTERNAL_API_URL=http://asat-app:8080` 을 frontend pod 의 환경변수로 주입. 깔끔하다 — 같았으면.

배포 후 ECONNREFUSED 127.0.0.1:8183 가 떴습니다. pod 에는 env var 가 분명히 들어가 있는데(`kubectl exec ... env` 로 확인) Next.js 는 localhost:8183 으로 가고 있음.

원인: **`output: "standalone"` 빌드는 `next.config` 의 rewrites destination 을 빌드 시점에 평가해서 server.js 에 베이크합니다.** 런타임 환경변수는 무시됩니다.

```bash
$ kubectl -n asat-prod exec deploy/asat-frontend -- \
    grep -o 'localhost:[0-9]*' server.js | sort -u
localhost:8183
```

런타임에 결정되어야 하는 destination 은 catch-all route handler 로 우회해야 합니다.

```ts
// frontend/src/app/api/[...path]/route.ts
export const dynamic = "force-dynamic";

const BACKEND = (process.env.NEXT_INTERNAL_API_URL ?? "http://localhost:8183").replace(/\/$/, "");

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const url = new URL(req.url);
  const target = `${BACKEND}/api/${path.join("/")}${url.search}`;
  const headers = new Headers(req.headers);
  ["host", "connection", "content-length", "accept-encoding"].forEach((h) => headers.delete(h));

  const init: RequestInit = { method: req.method, headers, redirect: "manual" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }
  const upstream = await fetch(target, init);
  const respHeaders = new Headers(upstream.headers);
  respHeaders.delete("content-encoding");
  respHeaders.delete("transfer-encoding");
  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: respHeaders,
  });
}

type Ctx = { params: Promise<{ path: string[] }> };
export async function GET(req: NextRequest, ctx: Ctx)    { return proxy(req, (await ctx.params).path); }
export async function POST(req: NextRequest, ctx: Ctx)   { return proxy(req, (await ctx.params).path); }
export async function PUT(req: NextRequest, ctx: Ctx)    { return proxy(req, (await ctx.params).path); }
export async function PATCH(req: NextRequest, ctx: Ctx)  { return proxy(req, (await ctx.params).path); }
export async function DELETE(req: NextRequest, ctx: Ctx) { return proxy(req, (await ctx.params).path); }
export async function OPTIONS(req: NextRequest, ctx: Ctx){ return proxy(req, (await ctx.params).path); }
```

route handler 안에서 `process.env` 는 **요청마다** 평가됩니다. 그래서 helm 차트가 env var 만 바꾸면 즉시 반영. Set-Cookie/Authorization 헤더도 그대로 통과시킵니다 (refresh 쿠키 흐름 보존).

이걸로 eln.lemuel.co.kr/api/* → Next.js → asat-app:8080 가 안정적으로 작동. nginx 라우팅 분기는 깔끔하게 제거.

이 함정은 별도로 메모리에 박았습니다 — Next.js standalone + 런타임 환경변수 destination 조합이면 일단 route handler 의심.

---

## 7. ELK 로 24+ 네임스페이스 로그 집계 + Telegram 알람

이건 [별도 글](/2026/05/15/elk-on-k3s-3node-hot-warm-cold/) 로 정리했지만 ASAT 관점에서 의미는 명확합니다.

작업 사이클에 마지막으로 필요한 게 **운영 가시성** 이었습니다. asat-app 의 ERROR 가 어디서 터지는지, 5xx 비율이 어떻게 변하는지, settlement-prod 의 Exception 패턴이 ASAT 에도 번지는지 — `kubectl logs` 로는 답이 안 나오는 질문들.

ELK 가 들어간 후 ASAT 관점에서 달라진 것:

```text
# 자동 수집: asat-prod stdout → Fluent Bit → logs-k8s-* 인덱스
$ kubectl -n logging exec logs-es-hot-0 -- \
    curl -k -u elastic:$ES_PASS \
    "https://localhost:9200/logs-k8s-*/_search?size=0" \
    -H "Content-Type: application/json" \
    -d '{"query":{"term":{"kubernetes.namespace_name":"asat-prod"}}}'
# {"hits":{"total":{"value":33,...}}}
```

5 분 윈도로 `level=ERROR` 또는 `message=~Exception` 카운트가 namespace 별 임계치(default 20) 초과하면 Telegram 으로 알림이 옵니다. ASAT 가 평소에는 ERROR 가 거의 없지만 — 만약 DB 커넥션이 깨지거나 Spring 컨텍스트가 죽으면 5 분 안에 봇이 잡아채줍니다.

![ELK Discover — 24 네임스페이스 통합 로그, 48,025 hits](/assets/images/asat-automation/01-kibana-asat-logs.png)

---

## 8. 결과 — 사람이 손대는 부분이 거의 없어졌다

오늘 끝낸 상태에서 ASAT 운영 사이클은 이렇게 압축됩니다.

```text
[기능 요청]                "X 기능 추가해줘"
    ↓ (사람: 코드 작성)
[git push origin master]   inter-asat 리포에 push
    ↓ (자동)
[GHCR 빌드]               k3s-images.yml workflow
    ↓ (자동)
[ArgoCD Image Updater]    helm-deploy values.yaml image.tag 갱신
    ↓ (자동)
[ArgoCD sync]             asat-prod namespace 에 새 파드 롤아웃
    ↓ (자동)
[운영]                    eln.lemuel.co.kr 에서 새 기능 즉시 사용 가능
    ↓ (자동)
[관측]                    Fluent Bit → ELK 인덱싱
    ↓ (자동 — 임계치 초과 시만)
[알람]                    Telegram 봇이 5분 윈도로 ERROR 스파이크 감지
```

사람의 손이 들어가는 자리는 코드 작성과 PR review **단 2 곳**. 그 외 모두 시스템이 알아서 합니다.

추가로 면접/심사 시나리오는:

```text
[면접관] eln.lemuel.co.kr 접속
[클릭] "관리자로 둘러보기"
[5초] 대시보드 진입 (회원가입/로그인 없음)
[탐색] 통계/차트/사용자 관리/내보내기 등 둘러봄
[종료] 브라우저 닫음 → 세션 쿠키 자동 소멸 (흔적 없음)
```

기존 가입자는:

```text
[로그인 시 "자동로그인" 체크]
[다음 방문] 브라우저 닫고 새로 열어도 자동으로 /dashboard 진입
[공용 PC] "자동로그인" 해제 → 브라우저 닫으면 세션 종료
```

---

## 9. 회고 — 자동화는 "사람이 안 끼는 자리" 의 수로 측정한다

오늘 작업의 핵심은 새 기능 추가가 아니라 **운영 자동화의 마지막 1 마일 채우기** 였습니다.

3 일 전까지의 상태와 비교:

| 항목 | 3 일 전 | 지금 |
|------|---------|------|
| 배포 | git push 후 손으로 `kubectl set image` | 자동 (Image Updater → ArgoCD) |
| 면접관 진입 | 회원가입 + 메일 인증 필수 | 1-클릭 데모 로그인 |
| 이메일 인증 | SMTP 미설정, 로그만 찍힘 | Gmail STARTTLS 587 가동 |
| API 라우팅 | nginx → dead 8082 | Next.js catch-all 프록시 → asat-app |
| 자동로그인 UX | 백그라운드 복원만, 라우팅 안 따라감 | 영속/세션 쿠키 + 라우팅 동기화 |
| 로그 집계 | `kubectl logs` 노가다 | ELK 24 ns 통합 인덱싱 |
| 에러 알람 | 없음 (사람이 모니터링) | Telegram 5분 윈도 자동 알람 |
| 백업 | Velero (워크로드) | + ES R2 snapshot SLM |

자동화 수준은 **"사람이 끼지 않아도 되는 자리의 수"** 로 측정합니다. 이 기준에서는 오늘 작업 후 5 군데 이상 사람 없이 굴러갑니다.

---

## 10. 남은 작업

다음 라운드에서 작업할 것들:

1. **Fluent Bit Lua 필터로 민감 필드 마스킹** — 현재 modify 필터 syntax 문제로 password/JWT/Authorization 마스킹이 빠져있음. lua 로 재구현.
2. **Kibana Lens 대시보드 자동 import** — saved_objects API + kbn-bulk 로 ASAT 전용 대시보드(5xx rate, response p95, login attempt) 자동 생성
3. **GHCR PAT 만료 대비 자동 갱신** — 현재 PAT 가 만료되면 ImagePullBackOff 가 나는 위험. dependabot 같은 패턴으로 분기별 갱신 알림
4. **e2e 회귀 테스트 자동화** — Playwright 로 데모 로그인 → 대시보드 진입 → 훈련 시작 → 로그아웃 시나리오를 매 PR 마다 자동 실행
5. **AB 테스트 인프라** — feature flag(growthbook) 로 train-V1 vs train-V2 패러다임 비교

GitOps 위에 다 녹일 수 있는 작업들이라 각각 PR 1~2 개로 끝날 예정입니다.

---

## 부록 — 오늘 작업 커밋 히스토리

```text
$ git log --oneline inter-asat (오늘분)
0a161d3 fix(auth): 자동로그인 복원 시 로그인/랜딩 페이지에서 대시보드로 즉시 이동
cb03265 fix(frontend): /api/* 런타임 프록시 라우트로 우회
28d1ddf feat(frontend): same-origin API + Next.js /api 프록시
6e68fd1 feat(auth): 포트폴리오용 데모 1-클릭 로그인 추가
95f9a9b fix(auth): rememberMe 누락 시 false 로 기본화 (하위호환)
f314d81 feat(auth): 자동로그인 체크박스 추가 (rememberMe)

$ git log --oneline helm-deploy (오늘분)
ec3d910 asat: Gmail SMTP + 회원가입 인증 메일 활성화
53fafca asat: frontend NEXT_INTERNAL_API_URL → 백엔드 서비스 프록시
79afec6 asat: enable ASAT_AUTH_DEMO_MODE_ENABLED for portfolio demo
```

총 inter-asat 6 커밋 + helm-deploy 3 커밋 = 9 번의 자동 무중단 배포. 사람이 손댄 건 git push 9 번뿐.

> **TL;DR** — 청각재활 시스템(ASAT) 의 운영 자동화 마지막 1 마일을 하루 안에 완성했다. 면접관용 데모 로그인부터 ELK 알람까지, 사람이 손대는 자리는 코드 작성과 PR review 2 곳만 남았다.
