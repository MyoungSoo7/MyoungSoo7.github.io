---
layout: post
title: "핸드폰 보안, 안드로이드와 iOS 따로 챙기기 — 공식 문서로 정리한 설정 체크리스트"
date: 2026-09-24 20:10:00 +0900
categories: [security]
tags: [mobile-security, android, ios, iphone, 2fa, theft-protection]
---

핸드폰 보안 조언은 대개 "업데이트 하세요, 이상한 앱 깔지 마세요"에서 끝난다. 틀린 말은 아니지만,
실제로 **어떤 스위치를 켜야 하는지**는 안드로이드와 iOS 가 다르다. 이 글은 구글·애플의 **공식 문서만** 근거로,
두 플랫폼에서 각각 켤 것을 정리한다. 기능 이름과 조건은 모두 원문에서 확인한 것이다.

## 공통 — 플랫폼보다 먼저

1. **OS 업데이트** — 보안 패치는 업데이트로만 온다.
2. **화면 잠금 + 생체 인증** — 아래 도난 보호 기능들이 전부 이걸 전제로 한다.
3. **계정 2단계 인증** — 폰을 잃어도 계정(Apple 계정, Google 계정)은 지켜야 한다.
   [Apple](https://support.apple.com/en-us/102660)도 [Google](https://support.google.com/accounts/answer/185839)도 공식적으로 켜기를 권한다.
4. **앱은 공식 스토어에서** — 이유는 플랫폼별로 아래에서 다룬다.

도둑이 노리는 건 기계보다 **잠금이 풀린 폰과 그 안의 계정**이다. 그래서 요즘 두 플랫폼 모두 "잠금이 풀린 채 빼앗긴 상황"을 대비하는 기능을 따로 두고 있다.

---

## iOS (iPhone)

### 구조적으로 이미 해 주는 것

- **Secure Enclave** — [Apple 플랫폼 보안 문서](https://support.apple.com/guide/security/secure-enclave-sec59b0b31ff/web)에 따르면, 메인 프로세서와 분리된 전용 보안 서브시스템이다. 민감한 사용자 데이터를 보호한다. 사용자가 켤 건 없다.

### 켜야 하는 것

**1. 도난 기기 보호 (Stolen Device Protection)** — [Apple 문서](https://support.apple.com/en-us/120340)

- iOS 17.3 이상. **잃어버리기 전에 켜 둬야** 효과가 있다.
- 집·회사 같은 익숙한 장소를 벗어나면 규칙이 강해진다.
  - 저장된 비밀번호나 카드 정보 접근에는 Face ID/Touch ID 가 필요하다. **암호로 대체할 수 없다.**
  - Apple 계정 비밀번호 변경 같은 중요한 작업은 **1시간을 기다린 뒤** 생체 인증을 한 번 더 해야 한다(Security Delay).
- 켜려면 2단계 인증, 기기 암호, Face ID/Touch ID, 위치 서비스의 '중요 위치'가 필요하다.
- 의미: 어깨너머로 암호를 훔쳐본 도둑이 폰을 빼앗아도, 그 1시간 동안 주인이 분실 처리를 할 수 있다.

**2. 보안 키 (Security Keys for Apple Account)** — [Apple 문서](https://support.apple.com/en-us/102637)

- 물리 보안 키로 Apple 계정 로그인을 보호한다. 피싱에 강하다.
- **FIDO 인증 키 최소 2개**가 필요하고, 로그인된 모든 기기가 iOS 16.3 / macOS 13.2 이상이어야 한다.

**3. iCloud 고급 데이터 보호 (Advanced Data Protection)** — [Apple 문서](https://support.apple.com/en-us/108756)

- iCloud 데이터 대부분을 **종단 간 암호화**한다. Apple 도 볼 수 없고, 클라우드 쪽에서 유출이 나도 안전하다.
- 대가도 있다. **Apple 이 복구를 도와줄 수 없다.** 켜기 전에 복구 연락처나 복구 키를 반드시 설정하게 되어 있다.

**4. 차단 모드 (Lockdown Mode)** — [Apple 문서](https://support.apple.com/en-us/105120)

- 소수의 표적 대상을 위한 **극단적 보호**다. 직업이나 신분 때문에 고도의 공격을 받을 수 있는 사람들이 대상이다. Apple 스스로 "대부분의 사람은 이런 공격의 표적이 되지 않는다"고 쓴다.
- 켜면 일부 앱·웹사이트·기능이 엄격히 제한된다. iOS 16 이상.
- 기자, 활동가, 고위 임원이 아니라면 보통은 1~3번으로 충분하다.

---

## Android

### 구조적으로 이미 해 주는 것

- **앱 샌드박스** — [AOSP 문서](https://source.android.com/docs/security/app-sandbox)에 따르면, 앱마다 고유한 사용자 ID(UID)를 주고 별도 프로세스로 실행한다. 커널이 앱 사이를 격리하므로, 기본적으로 앱끼리는 서로 간섭할 수 없다.
- **Verified Boot** — [AOSP 문서](https://source.android.com/docs/security/features/verifiedboot)에 따르면, 하드웨어 신뢰 루트부터 부트로더, 시스템 파티션까지 부팅 단계마다 다음 단계를 검증한다. 실행되는 코드가 신뢰할 수 있는 출처에서 왔는지 확인하는 구조다.

### 확인하고 켜야 하는 것

**1. 보안 업데이트 날짜 확인** — [Google 도움말](https://support.google.com/android/answer/7680439)

안드로이드는 제조사를 거쳐 업데이트가 배포된다. 그래서 iOS 보다 **"내 폰이 아직 패치를 받고 있는가"**를 직접 확인하는 게 중요하다.
설정 → 휴대전화 정보에서 Android 버전과 **보안 업데이트 상태**를 볼 수 있다.
구글은 [Android 보안 게시판](https://source.android.com/docs/security/bulletin)에 패치 내역을 공개한다.

**2. Google Play 프로텍트 유지** — [Google Play 도움말](https://support.google.com/googleplay/answer/2812853)

- 설치된 앱을 검사하는 기능이다. Play 스토어 설정에서 "Play 프로텍트로 앱 검사"를 켜 둔다.
- 구글은 Play 프로텍트가 하루 2,000억 개의 앱을 검사한다고 밝힌다([Google 개발자 문서](https://developers.google.com/android/play-protect), **벤더 자체 수치**).
- 안드로이드는 스토어 밖 설치(출처를 알 수 없는 앱)가 가능하다. 자유로운 만큼, 문자나 메신저로 온 링크의 APK 를 설치하는 건 검증을 건너뛰는 일이다. 사용자가 가장 쉽게 피할 수 있는 위험이기도 하다.

**3. 도난 보호 3종** — [Google 도움말](https://support.google.com/android/answer/15146908)

- **도난 감지 잠금 (Theft Detection Lock)** — AI, 모션 센서, Wi-Fi, 블루투스로 "누가 손에서 채서 달아나는" 상황을 감지해 화면을 자동으로 잠근다.
- **오프라인 기기 잠금 (Offline Device Lock)** — 도둑이 인터넷을 끊어 위치 추적을 피하려 하면, 오프라인 상태로 잠시 쓰인 뒤 자동으로 잠긴다.
- **본인 확인 (Identity Check)** — 신뢰할 수 있는 장소 밖에서 민감한 작업을 하거나 Google 계정 설정을 바꿀 때 생체 인증을 요구한다. 일부 기기에서만 제공된다.
- iOS 의 도난 기기 보호와 목적이 같다. 설정의 '도난 방지' 메뉴에 해당 항목이 없으면 그 기기는 지원하지 않는 것이다.

**4. 고급 보호 (Advanced Protection)** — [Google 도움말](https://support.google.com/android/answer/16339980)

iOS 의 차단 모드에 대응하는, 한 번에 켜는 강화 모드다. 문서에 적힌 효과 중 일부는 다음과 같다.

- 출처를 알 수 없는 앱 **설치 차단**. 그런 경로로 설치된 앱의 업데이트도 차단한다.
- 화면이 잠긴 동안 **USB 를 통한 무단 접근 차단**
- 보안이 약한 **2G 네트워크 연결 차단** (지원 기기)
- 메모리 손상 공격을 막는 **MTE** (지원 앱, 성능 저하 가능)
- **사기 탐지** 필수 활성화 (피싱 메시지 경고)

차단 모드만큼 극단적이지는 않다. 사이드로딩을 하지 않는 사용자라면 불편이 크지 않은 편이다.

---

## 한눈에 비교

| 목적 | iOS | Android |
|---|---|---|
| 잠금 풀린 채 도난 | 도난 기기 보호 (1시간 지연, 생체 필수) | 도난 감지 잠금 · 오프라인 잠금 · 본인 확인 |
| 계정 탈취 방지 | 2단계 인증 + 보안 키 | 2단계 인증 |
| 클라우드 데이터 | 고급 데이터 보호 (E2E, 복구 책임은 본인) | — |
| 악성 앱 | 스토어 중심 배포 | Play 프로텍트 + 출처 불명 앱 주의 |
| 표적 공격 대비 모드 | 차단 모드 | 고급 보호 |
| 사용자가 꼭 확인할 것 | 도난 기기 보호가 켜져 있는가 | **보안 업데이트 날짜가 최근인가** |

## 오늘 할 일 (5분)

- **iPhone**: 설정 → Face ID 및 암호 → **도난 기기 보호**가 켜져 있는지 확인한다. Apple 문서에 따르면 기본으로 켜져 있을 수도 있다. 복구 수단을 준비할 수 있다면 고급 데이터 보호도 검토한다.
- **Android**: 설정 → 휴대전화 정보에서 **보안 업데이트 날짜** 확인 → 보안 설정에서 **도난 방지** 3종 켜기 → Play 프로텍트가 켜져 있는지 확인한다.
- **둘 다**: 계정 2단계 인증. 이미 켰다면 복구 수단(복구 이메일·번호·키)이 지금도 유효한지 확인한다.

※ 삼성 등 제조사별 추가 보안 기능은 이 글에서 다루지 않았다. 여기 적은 건 구글·애플 공식 문서로 확인한 기능뿐이다.
메뉴 이름과 위치는 OS 버전과 제조사에 따라 다를 수 있다.

## References

- Apple, *About Stolen Device Protection for iPhone* — <https://support.apple.com/en-us/120340>
- Apple, *About Security Keys for Apple Account* — <https://support.apple.com/en-us/102637>
- Apple, *How to turn on Advanced Data Protection for iCloud* — <https://support.apple.com/en-us/108756>
- Apple, *About Lockdown Mode* — <https://support.apple.com/en-us/105120>
- Apple, *Two-factor authentication for Apple Account* — <https://support.apple.com/en-us/102660>
- Apple Platform Security, *The Secure Enclave* — <https://support.apple.com/guide/security/secure-enclave-sec59b0b31ff/web>
- Android Open Source Project, *Application Sandbox* — <https://source.android.com/docs/security/app-sandbox>
- Android Open Source Project, *Verified Boot* — <https://source.android.com/docs/security/features/verifiedboot>
- Android Open Source Project, *Android Security Bulletins* — <https://source.android.com/docs/security/bulletin>
- Google, *Check & update your Android version* — <https://support.google.com/android/answer/7680439>
- Google, *Protect your personal data against theft* — <https://support.google.com/android/answer/15146908>
- Google, *Advanced Protection for Android* — <https://support.google.com/android/answer/16339980>
- Google, *Use Google Play Protect* — <https://support.google.com/googleplay/answer/2812853>
- Google for Developers, *Play Protect* — <https://developers.google.com/android/play-protect>
- Google, *Turn on 2-Step Verification* — <https://support.google.com/accounts/answer/185839>
