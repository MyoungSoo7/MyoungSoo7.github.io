---
layout: post
title: "비밀번호 금고를 직접 띄웠는데 두 달을 안 썼다 — Vaultwarden 사용법, 그리고 안 쓸 때의 사용법"
date: 2026-08-25 06:57:39 +0900
categories: [security, self-hosting]
tags: [vaultwarden, bitwarden, password-manager, self-hosted, kdf, argon2id, hardening]
---

6월에 자체 호스팅 비밀번호 관리자를 하나 띄웠다. 오늘 안을 들여다봤더니 데이터
디렉터리가 300KB 였고, SQLite 파일의 마지막 수정 시각이 **띄운 날 그대로**였다.
두 달 동안 비밀번호가 하나도 들어가지도 나가지도 않았다는 뜻이다.

설치는 끝났는데 사용은 시작된 적이 없었다. 이 글은 그래서 "설치법" 이 아니라
**사용법** 이다. 그리고 마지막에 하나 더 — 안 쓰기로 했을 때 해야 하는 것도
사용법의 일부다. 이쪽이 사실 더 급했다.

---

## 1. Vaultwarden 은 "서버만" 바꾸는 물건이다

먼저 정체부터 정확히. Vaultwarden 은 **Bitwarden Client API 의 대체 서버 구현**이고,
Rust 로 작성됐으며, AGPL-3.0 이다. 공식 Bitwarden 클라이언트와 호환되는 것을 목표로
하며, 프로젝트 스스로 "공식 Bitwarden 서비스를 돌리는 것이 부담스러운 셀프호스팅
배포에 적합" 하다고 소개한다.[^1] 예전 이름은 `bitwarden_rs` 였고, 공식 서버와의 혼동과
상표 문제를 피하기 위해 개명했다.[^1]

여기서 초보가 가장 많이 헷갈리는 지점을 짚고 가자.

> **클라이언트는 새로 만들지 않는다.** 브라우저 확장·모바일 앱·데스크톱 앱·CLI 는
> **Bitwarden 공식 것을 그대로 쓴다.**[^2] 바뀌는 건 그 앱들이 붙는 **서버 주소** 하나뿐이다.

그래서 "Vaultwarden 앱" 을 스토어에서 찾으면 안 나온다. 찾을 것은 Bitwarden 앱이다.

기능 범위는 넓다. 개인 볼트, Send, 첨부파일, 웹사이트 아이콘, 개인 API 키, 조직(컬렉션·
공유·역할·그룹·이벤트 로그·정책), 2단계 인증(인증 앱·이메일·FIDO2 WebAuthn·YubiKey·Duo),
긴급 접근까지 "거의 완전한 구현" 이라고 README 가 열거한다.[^1]

**중요한 단서 하나.** 이 프로젝트는 Bitwarden, Inc. 와 무관하다고 README 가 명시한다.
그리고 업스트림은 **"어떤 클라이언트를 쓰든 버그·제안은 우리에게 보고하고, Bitwarden
공식 지원 채널을 쓰지 말라"** 고 못 박는다.[^1] 공식 앱을 쓰지만 공식 지원 대상은 아니다 —
이 비대칭을 이해하고 시작해야 한다.

---

## 2. 사용법 ① — 클라이언트를 내 서버에 붙이기

여기가 실제 "첫 사용" 이다. Bitwarden 공식 문서가 클라이언트별 절차를 정리해 두었다.[^2]

**브라우저 확장**
로그인/가입 화면에서 `Logging in on` 드롭다운 → `Self-hosted` 선택 → Server URL 에
`https://` 를 포함한 도메인 입력 → Save.[^2]

**모바일 앱**
같은 드롭다운에서 `Self-hosted` → Server URL 입력. 서버가 요구하면 인증서를 업로드할
수 있다.[^2]

**데스크톱 앱**
`Accessing` 드롭다운에서 `Self-hosted` 선택 → Server URL 입력 → Save. 계정마다 서로
다른 서버에 붙일 수 있다.[^2]

**CLI**

```bash
bw logout
bw config server https://your.domain.example
```

서비스별로 URL 을 따로 지정해야 하는 특수한 구성이라면 `--web-vault` `--api`
`--identity` `--icons` `--notifications` `--events` `--key-connector` 를 각각 줄 수 있다.[^2]

한 가지 전제가 있다. **HTTPS 는 선택이 아니다.** 웹 볼트가 Web Crypto API 를 쓰는데
이건 secure context 에서만 동작하므로, HTTPS 를 켜지 않으면 아예 작동하지 않는다.
업스트림도 리버스 프록시 사용을 권한다.[^1]

---

## 3. 사용법 ② — 무엇을 담고, 무엇이 자동으로 되는가

붙이고 나면 그 다음은 평범한 비밀번호 관리자다. 습관 쪽이 훨씬 중요하다.

- **로그인 항목**: 사이트마다 *서로 다른* 랜덤 비밀번호를 생성기로 만들어 저장한다.
  이게 비밀번호 관리자를 쓰는 유일한 이유다. 같은 비번을 계속 쓸 거면 금고가 필요 없다.
- **TOTP(2단계 인증 6자리)**: 항목 안에 인증 키를 넣어두면 클라이언트가 코드를 생성한다.[^3]
  다만 이러면 "비번" 과 "두 번째 요소" 가 한 금고에 같이 있게 된다. 편의와 분리 중
  무엇을 살지는 각자 결정할 문제다.
- **Send**: 텍스트·파일을 만료 조건과 함께 일회성 링크로 전달하는 기능.[^4] 카톡으로
  비번 보내는 습관을 대체할 수 있는 자리다.
- **첨부·조직·컬렉션**: 가족 계정 공유 같은 용도. Vaultwarden 은 이 영역도 구현한다.[^1]

그리고 **마스터 비밀번호는 딱 하나만 외운다.** 나머지를 전부 금고가 기억하기 때문에
사이트마다 다른 32자 랜덤 비번을 쓰는 게 가능해진다.

---

## 4. 사용법 ③ — 유일하게 직접 눌러야 하는 보안 스위치, KDF

비밀번호 관리자에서 사용자가 실제로 조정할 수 있는 암호학적 손잡이는 사실상 하나다.
**마스터 비밀번호로부터 키를 유도하는 함수(KDF)의 작업량.**

Bitwarden 은 PBKDF2 와 Argon2id 둘을 제공한다.[^5]

| 알고리즘 | 기본값 | 근거 |
| --- | --- | --- |
| PBKDF2-HMAC-SHA256 | **600,000 회** | OWASP 권고를 따른 값 |
| Argon2id | 메모리 32 MiB · 반복 6 · 병렬 4 | 문서상 "현행 OWASP 권고보다 높음" |

Bitwarden 문서는 PBKDF2 를 NIST 권고 기반으로 설명하면서, 기본값을 낮추지 않는 한
FIPS-140 요건을 만족한다고 적는다. 또 클라이언트-서버 간 설정값 외에 추가 반복을 더
수행해 마스터 비밀번호 해시가 총 기본 **700,000 회**가 된다고 밝힌다.[^5] Argon2id 는
2015 Password Hashing Competition 우승 알고리즘이며, OWASP 권고에 따라 Argon2id 변종을
구현했다고 설명한다.[^5]

**2026.2.1 릴리스에서 Bitwarden 은 PBKDF2 최소 반복 횟수를 기본값인 600,000 으로
올렸다.**[^5] 즉 옛날에 만든 계정이 낮은 반복 횟수로 남아 있을 수 있다. 설정 →
보안 → 키 에서 현재 값을 한 번 확인할 가치가 있다.

다만 문서 자신이 붙이는 단서를 그대로 옮긴다 — **반복 횟수 상향은 강한 마스터
비밀번호의 대체재가 아니다.** 언제나 강한 마스터 비밀번호가 첫 번째이자 최선의
방어선이다.[^5] 그리고 KDF 를 바꾸면 보호된 대칭키가 재암호화되고 인증 해시가
갱신되므로, 문서는 필수는 아니라면서도 변경 전 백업을 권한다.[^5]

---

## 5. 사용법 ④ — 띄운 직후에 반드시 끄는 것들

여기가 내가 틀렸던 부분이다. 나는 이걸 **"나중에"** 로 미뤄뒀고, 두 달간 그 상태였다.

### ① 신규 가입을 막는다

**기본값이 열림이다.** 업스트림 위키가 그대로 적는다 — "기본적으로 당신의 인스턴스에
접근할 수 있는 누구나 새 계정을 등록할 수 있다."[^6] 끄는 법은 환경변수 한 줄이다.

```
SIGNUPS_ALLOWED=false
```

하드닝 가이드도 첫 사용자 등록 후 이걸 끄라고 권한다.[^7] 특정 도메인만 허용하려면
`SIGNUPS_DOMAINS_WHITELIST` 를 쓰는데, **이 값을 설정하면 `SIGNUPS_ALLOWED` 는
무시된다**는 함정이 있다.[^6] 가짜 이메일 등록을 막으려면 `SIGNUPS_VERIFY=true` 도
함께 고려한다.[^6]

그리고 하나 더 — `SIGNUPS_ALLOWED=false` 여도 **조직 소유자/관리자인 기존 사용자는
여전히 새 사용자를 초대할 수 있다.**[^6] 초대까지 막으려면 별도 설정이 필요하다.

### ② 비밀번호 힌트 노출을 끈다

Vaultwarden 은 SMTP 가 없는 소규모 배포를 배려해 **로그인 페이지에 비밀번호 힌트를
표시**하는데, 하드닝 가이드는 이것이 공격자의 비밀번호 추측을 도울 수 있다며 끄기를
권한다.[^7]

### ③ Admin 페이지를 함부로 열지 않는다

`/admin` 패널은 서버 설정 변경, 전체 사용자·조직 조회 및 삭제, 가입이 막혀 있어도
초대 발송이 가능한 **강력한 관문**이다.[^8] 그래서:

- 이 기능을 켜기 전에 **HTTPS 를 먼저 활성화**하라고 위키가 강하게 권고한다(MITM 위험).[^8]
- `ADMIN_TOKEN` 은 `openssl rand -base64 32` 같은 길고 무작위한 문자열로 만든다.[^8]
- 설정은 대개 **평문으로 저장**되므로, `vaultwarden hash` 나 `argon2` CLI 로
  **argon2id PHC 문자열**을 만들어 해시 형태로 두는 것이 권장된다.[^8]
- 세션은 JWT 라 **토큰을 바꿔도 이미 로그인한 세션은 무효화되지 않는다.** 전부 끊으려면
  데이터 폴더의 `rsa_key.pem` 을 지우고 재시작해 RSA 키를 재생성해야 한다.[^8]
  기본 세션 수명은 20분이며, 이유 없이 늘리지 않는 게 좋다.[^8]

### ④ TLS 는 리버스 프록시에 맡긴다

하드닝 가이드는 Vaultwarden 내장 Rocket TLS 사용을 피하라고 하면서 Rocket 자신의 경고를
인용한다 — 내장 TLS 는 **개발용이지 프로덕션용으로 간주되지 않는다**는 것. strict SNI 와
ECC 인증서도 지원하지 않는다고 덧붙인다.[^7]

같은 문서가 **strict SNI** 를 권하는 이유도 명확하다. IP 주소로 직접 접근이 가능하면
상시 스캐닝에 노출되어 표적이 되기 쉽다는 것이다.[^7]

### ⑤ 로그에 남는 토큰을 지운다

알림용 WSS 연결이 `access_token` 을 **쿼리 파라미터**로 실어 GET 요청을 보낸다.
리버스 프록시가 액세스 로그를 저장하거나 외부 로그 스토어로 보낸다면 이 값을 마스킹하라고
가이드가 권고한다.[^7] 로그 파이프라인을 갖춘 홈랩일수록 실수하기 쉬운 지점이다.

---

## 6. 그리고 — 안 쓸 때의 사용법

내 경우로 돌아온다. 데이터는 300KB, 마지막 쓰기는 두 달 전. 여기서 선택지는 둘이었다.

**(A) 쓰기 시작한다.** 그러면 위 5장을 전부 먼저 하고 시작해야 한다.
**(B) 안 쓴다.** 그러면 **접근 경로를 닫는 것까지가 사용법이다.**

나는 (B) 를 골랐고, 파드도 데이터도 백업도 그대로 둔 채 **외부 라우팅만** 제거했다.
확인은 실측으로 했다 — 외부에서 200 이던 응답이 404 가 됐고, 같은 경로를 쓰는 다른
서비스들은 그대로 200 이었으며, 컨테이너 내부에서는 여전히 200 이 나왔다. 즉 서비스는
살아 있고 문만 닫혔다.

이 선택에는 이유가 있다. **안 쓰는 금고는 자산이 아니라 표면이다.** 로그인 화면이
인터넷에 열려 있고, 신규 가입이 허용돼 있고, 아무도 그 화면을 매일 보지 않는다면 —
거기서 무슨 일이 생겨도 알아차릴 사람이 없다. 반면 닫아두면 잃는 것은 "언제든 접속할 수
있다" 는 편의뿐이고, 그 편의는 두 달간 한 번도 쓰이지 않았다.

셀프호스팅에서 진짜 비용은 설치가 아니다. **띄워놓고 잊은 서비스의 수** 다.

---

## 근거의 한계

- **이 글은 사용법과 공식 문서의 권고를 정리한 것이지, 보안 감사 결과가 아니다.**
  Vaultwarden 에 대한 공개된 제3자 보안 감사 보고서를 이 글은 인용하지 않는다 —
  찾아 확인하지 못했으므로 "감사받았다/받지 않았다" 어느 쪽도 주장하지 않는다.
- Vaultwarden 은 **Bitwarden, Inc. 와 무관한 비공식 구현**이며, README 는 데이터 손실에
  대해 책임질 수 없다고 명시하고 정기 백업을 강력히 권한다.[^1] 공식 서버와 동일한
  보증을 기대하면 안 된다.
- 성능·자원 사용량 비교 수치는 넣지 않았다. README 의 "resource-heavy" 표현은 프로젝트
  자신의 서술이고,[^1] 재현 가능한 중립 벤치마크를 확인하지 못했다.
- KDF 기본값·최소값은 클라이언트 버전에 따라 바뀐다. 위 표는 인용 시점의 공식 문서
  기준이며, 실제 값은 각자의 설정 화면에서 확인하는 것이 정본이다.
- 구체적인 호스트명·네트워크 구성은 의도적으로 적지 않았다.

---

### References

[^1]: dani-garcia/vaultwarden — README (Features · Usage · Disclaimer · Bitwarden_RS 개명). <https://github.com/dani-garcia/vaultwarden>
[^2]: Bitwarden Help — *Connect Individual Clients* (브라우저 확장·모바일·데스크톱·CLI 의 self-hosted 서버 지정). <https://bitwarden.com/help/change-client-environment/>
[^3]: Bitwarden Help — *Authenticator Keys (TOTP)*. <https://bitwarden.com/help/authenticator-keys/>
[^4]: Bitwarden Help — *About Send*. <https://bitwarden.com/help/about-send/>
[^5]: Bitwarden Help — *Encryption Key Derivation* (PBKDF2 600,000 · 총 700,000 · Argon2id 32MiB/6/4 · 2026.2.1 최소 반복 상향 · 강한 마스터 비밀번호 우선). <https://bitwarden.com/help/kdf-algorithms/>
[^6]: Vaultwarden Wiki — *Disable registration of new users* (`SIGNUPS_ALLOWED` · `SIGNUPS_DOMAINS_WHITELIST` 우선순위 · 조직 초대). <https://github.com/dani-garcia/vaultwarden/wiki/Disable-registration-of-new-users>
[^7]: Vaultwarden Wiki — *Hardening Guide* (가입 차단 · 비밀번호 힌트 · strict SNI · Rocket 내장 TLS 경고 · access_token 로그 마스킹). <https://github.com/dani-garcia/vaultwarden/wiki/Hardening-Guide>
[^8]: Vaultwarden Wiki — *Enabling admin page* (HTTPS 선행 권고 · ADMIN_TOKEN 생성 및 argon2id 해시 · JWT 세션과 `rsa_key.pem` · 기본 세션 20분). <https://github.com/dani-garcia/vaultwarden/wiki/Enabling-admin-page>
- Bitwarden Security White Paper. <https://bitwarden.com/help/bitwarden-security-white-paper/>
- OWASP Cheat Sheet Series — *Password Storage Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html>
- Bitwarden 공식 클라이언트 다운로드. <https://bitwarden.com/download/>
