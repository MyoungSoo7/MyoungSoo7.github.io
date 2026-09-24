---
layout: post
title: "모바일 백신의 한계 — 알약M 은 옆 앱의 속을 볼 수 없다"
date: 2026-09-24 20:23:28 +0900
categories: [Security]
tags: [mobile-security, antivirus, alyac, android, ios, sandbox, smishing, voice-phishing]
---

PC 백신은 운영체제 깊숙이 들어가 모든 프로세스와 파일을 들여다본다. 폰에 까는 백신 앱(국내에선 이스트시큐리티 **알약M**, 안랩 **V3 Mobile** 이 대표적이다)도 이름이 같으니 같은 일을 할 거라고 생각하기 쉽다. **그렇지 않다.** 모바일 백신은 운영체제가 모든 앱에 채우는 격리 안에서 똑같이 돌아가는 **평범한 앱 하나**다. 이 글은 그 구조 때문에 생기는 한계를 공식 문서와 공공 자료로 정리한다.

> 범위: 이 글은 **모바일 백신 앱이라는 제품군의 구조적 한계**를 다룬다. 알약M 을 예로 들지만, 여기서 말하는 한계 대부분은 V3 Mobile 등 다른 제품에도 똑같이 적용된다. 안랩 제품군의 PC·기업 쪽 한계는 [안랩 보안의 한계](/2026/09/24/ahnlab-limits-where-the-last-one-percent-comes-from/)에서, 폰 설정 체크리스트는 [핸드폰 보안, 안드로이드와 iOS 따로 챙기기](/2026/09/24/smartphone-security-android-vs-ios/)에서 다뤘다.

## 1. 구조 — 백신도 샌드박스 안에 갇혀 있다

**안드로이드.** [AOSP 공식 문서](https://source.android.com/docs/security/app-sandbox)에 따르면 안드로이드는 앱마다 고유한 UID 를 주고 커널 수준 샌드박스로 격리한다. 기본적으로 앱끼리는 서로 간섭할 수 없고, 앱 A 는 앱 B 의 데이터를 읽을 수 없다. 안드로이드 9 부터는 앱별 SELinux 샌드박스(MAC)가 한 겹 더 씌워진다. 이 규칙에는 **백신 앱도 예외가 아니다.**

**iOS.** [Apple Platform Security](https://support.apple.com/guide/security/security-of-runtime-process-sec15bfe098e/web)는 모든 서드파티 앱이 샌드박스에 갇혀 있어 다른 앱이 저장한 정보를 모으거나 바꿀 수 없다고 명시한다. 다른 앱을 수정하도록 권한을 올려 주는 API 도 없다. 그래서 **iOS 의 "보안 앱"은 다른 앱을 검사한다는 의미의 백신이 될 수 없다.** 할 수 있는 건 URL·문자 필터링, 와이파이 점검 같은 주변 기능뿐이다.

이게 핵심이다. PC 백신은 "시스템 위에서 감시하는 존재"지만 모바일 백신은 **감시 대상과 같은 층에 있는 이웃**이다.

## 2. 그럼 알약M 은 무엇으로 보나

샌드박스 밖을 못 보는 앱이 쓸 수 있는 창은 운영체제가 명시적으로 열어 준 것뿐이다.

| 창 | 무엇이 보이나 | 근거 |
|---|---|---|
| 설치된 앱 목록 (`QUERY_ALL_PACKAGES`) | 어떤 패키지가 깔려 있는지, APK 파일 | 구글은 이 권한을 "개인적이고 민감한 정보"로 보고 기기 검색·**백신**·파일 관리자·브라우저 등에만 허용한다 ([Play Console 도움말](https://support.google.com/googleplay/android-developer/answer/10158779), [Android Developers](https://developer.android.com/training/package-visibility/declaring)) |
| 알림 접근 권한 | 다른 앱이 띄운 **알림의 내용** | 알약 공식 블로그: 스미싱 탐지는 모든 앱의 알림을 읽는 방식이라 **알림 접근 권한이 없으면 동작하지 않는다** ([알약 블로그, 2019](https://blog.alyac.co.kr/2236)) |
| 공유 저장소 파일 | 사용자가 받은 파일 | 저장소 권한 범위 안에서만 |

즉 알약M 의 검사는 **"설치된 앱이 무엇인가(시그니처·평판)"** 와 **"들어온 알림·링크가 무엇인가"** 에 대한 판단이다. 실행 중인 다른 앱의 메모리, 그 앱의 내부 데이터, 그 앱이 지금 무엇을 하고 있는지는 **보이지 않는다.**

제조사가 내세우는 기능은 가족 보호, 바이러스 검사, 스미싱 탐지, 와이파이 보안, 앱 잠금, 정리 기능 등이다 ([이스트시큐리티 알약M 제품 페이지](https://www.estsecurity.com/public/product/alyacm/android)). 같은 페이지의 "모바일 보안앱 이용자 수 국내 1위", "국내 최대 스미싱 탐지 DB" 같은 문구는 **벤더 주장**이며, 이 글에선 검증하지 않았다.

## 3. 할 수 없는 것들

### 3-1. 이미 설치된 악성앱이 "무엇을 하는지" 못 본다

백신이 탐지하는 건 주로 설치 시점의 **파일**이다. 설치 후 원격 서버에서 새 기능을 받아 오거나 동작을 바꾸는 앱은 파일만으로 판별하기 어렵다. 경찰청은 보이스피싱 조직이 **탐지 회피를 위해 기능을 쪼갠 악성앱 여러 개를 한 번에 뿌리고, 짧게는 하루 단위로 업데이트하며, 돈을 뺏은 뒤엔 악성앱 통신을 스스로 끊는다**고 밝혔다 ([전기통신금융사기 통합대응단 보도자료, 2025-04-28](https://www.counterscam112.go.kr/bbs002/board/boardDetail.do?pstSn=60)). 시그니처 기반 검사는 하루짜리 변종과 늘 경주를 한다.

### 3-2. 악성앱은 백신부터 노린다

같은 층에 있으니 공격자도 백신 앱을 방해할 수 있다. 알약M 이 과거 업데이트에서 **"알약 실행을 방해하는 악성앱"에 대응**하는 기능을 넣은 것 자체가 그런 시도가 실제로 있었다는 뜻이다. 접근성 권한을 얻은 악성앱은 화면을 읽고 사용자 대신 버튼을 누를 수 있다. 구글도 접근성 설정을 켜 주면 앱이 "화면의 내용을 읽고 사용자 대신 앱과 상호작용할 수 있다"고 경고한다 ([Android 도움말 — 제한된 설정](https://support.google.com/android/answer/12623953)). 이 정도 권한을 가진 악성앱 앞에서 같은 층의 백신이 이긴다는 보장은 없다.

### 3-3. 사람을 속이는 공격은 파일이 아니다

경찰청 발표에 따르면 2025년 1분기 보이스피싱은 5,878건, 피해액 3,116억 원으로 전년 같은 기간보다 각각 17%, 120% 늘었다. 기관 사칭형이 51% 였다 ([정책브리핑, 2025-04-28](https://www.korea.kr/news/policyNewsView.do?newsId=148942500)). 수법의 시작은 **전화로 피해자를 설득해 악성앱을 직접 깔게 하는 것**이다. 이때 사용자는 경고를 무시하도록 이미 설득당한 상태다. 백신이 "위험한 앱입니다"라고 띄워도 전화 너머의 "검찰 수사관"이 "그건 무시하고 설치하세요"라고 말하면 그걸로 끝이다.

앱 설치가 전혀 없는 공격도 있다. 가짜 사이트에 사용자가 직접 계좌 정보를 입력하거나, 전화로 불러 주는 대로 이체하는 경우엔 **백신이 개입할 지점이 아예 없다.**

### 3-4. 권한을 줄수록 백신 자신이 위험해진다

스미싱을 잡으려면 모든 앱의 알림을 읽어야 하고, 앱을 검사하려면 설치된 앱 목록 전체를 봐야 한다. 구글은 둘 다 민감 권한으로 분류한다. 보안 앱은 **폰에서 가장 많이 보는 앱 중 하나**가 되고, 그만큼 그 앱과 그 회사의 서버를 믿어야 한다. 탐지기 자체가 공격면이 된다는 점은 [안랩 글](/2026/09/24/ahnlab-limits-where-the-last-one-percent-comes-from/)에서 PC 쪽 사례로 다뤘는데, 모바일에서도 같은 원리다.

### 3-5. iOS 에서는 거의 아무것도 못 한다

1장에서 봤듯이 iOS 샌드박스는 다른 앱 검사를 허용하지 않는다. 아이폰에서 "백신"이라는 이름의 앱이 할 수 있는 건 문자·웹 필터링 수준이다. iOS 의 방어는 앱 검사가 아니라 **앱스토어 심사와 샌드박스 자체**에 달려 있다.

## 4. 얼마나 잘 잡나 — 중립 데이터가 없다

모바일 백신을 비교할 때 가장 많이 인용되는 독립 시험은 [AV-TEST 안드로이드 시험](https://www.av-test.org/en/antivirus/mobile-devices/android/july-2026/)이다. 2026년 격월 시험(1·3·5·7월)에는 안랩 V3 Mobile Security 와 구글 Play Protect 등이 포함돼 있다. 그러나 **알약M 은 2026년 AV-TEST 안드로이드 시험 대상 목록에 없다.** 따라서 **알약M 의 모바일 탐지율을 중립 기관 수치로 말할 수 있는 근거는 찾지 못했다.**

참고로 Virus Bulletin 의 [VB100 시험(2026-07-23)](https://www.virusbulletin.com/uploads/vb100/test-reports/vb100-test-report-2026-07-23-estsecurity-alyac.pdf)에는 알약이 나오지만, 이건 **Windows 판(ALYac 5.1.25)** 결과다. 모바일 알약M 에 적용할 수 없으므로 이 글의 근거로 쓰지 않는다.

이건 알약M 이 나쁘다는 뜻이 아니다. **좋은지 나쁜지 외부에서 확인할 방법이 없다**는 뜻이다. "국내 1위"는 설치 수에 대한 주장이지 탐지율에 대한 주장이 아니다.

## 5. 그래서 실제로 막아 주는 건 누구인가

샌드박스 안의 앱보다 **샌드박스를 만드는 쪽**, 즉 운영체제와 스토어가 더 많은 권한을 갖는다.

- **Play Protect** 는 구글 플레이 서비스 수준에서 동작하며 기기 전체의 앱을 검사한다 ([Google 도움말](https://support.google.com/googleplay/answer/2812853)). 금융위원회에 따르면 과기정통부와 구글이 MOU 를 맺고, 악성앱이 자동으로 설치되지 않게 막는 보안 프로그램을 **국내 안드로이드폰 3,500만 대에 적용**했다(2025-11-18) ([금융위원회 보도자료, 2025-12-30](https://www.fsc.go.kr/no010101/85959)).
- **제한된 설정.** 안드로이드 13 부터는 스토어 밖에서 설치한 앱이 접근성 같은 민감한 설정을 바로 켤 수 없다. 사용자가 앱 정보에서 "제한된 설정 허용"을 직접 눌러야 한다 ([Android 도움말](https://support.google.com/android/answer/12623953)). **누군가 전화로 이 버튼을 누르라고 하면 그게 곧 사기다.**
- **통신망 차단.** 정부는 문자사업자, 이동통신망, 단말기로 이어지는 3중 차단 체계를 운영하고, 범죄에 쓰인 번호를 신고 후 10분 안에 차단한다 ([정책브리핑, 2025-08-28](https://www.korea.kr/news/policyNewsView.do?newsId=148948340)).

모바일 백신은 이 층들 **위에 얹는 한 겹**이다. 스미싱 링크 경고, 알 수 없는 APK 평판 조회 같은 역할에서는 쓸모가 있다. 하지만 "백신을 깔았으니 안전하다"는 생각이 가장 큰 구멍이다.

## 6. 정리

| 기대 | 현실 |
|---|---|
| 폰 전체를 감시한다 | 다른 앱과 같은 샌드박스 안에 있고, 설치 목록·파일·알림만 본다 |
| 설치된 악성앱의 행동을 막는다 | 설치 시점 판별이 중심이며, 하루 단위 변종·통신 차단형엔 취약하다 |
| 보이스피싱을 막는다 | 사람을 설득하는 공격엔 개입 지점이 없다 |
| 아이폰도 지켜 준다 | iOS 에선 구조상 다른 앱을 검사할 수 없다 |
| 국내 1위라 잘 잡는다 | 설치 수 주장(벤더)이다. 모바일 중립 시험 결과는 찾지 못했다 |

**실무 조언은 세 줄이다.**

1. Play Protect 를 끄지 않는다.
2. 스토어 밖 설치, "제한된 설정 허용", 접근성 권한을 요구받으면 멈춘다.
3. 전화로 앱 설치나 설정 변경을 시키면 끊고 112 에 확인한다.

백신은 그 다음이다.

## References

- Android Open Source Project, *Application sandbox* — <https://source.android.com/docs/security/app-sandbox>
- Apple, *Apple Platform Security — Security of runtime process* — <https://support.apple.com/guide/security/security-of-runtime-process-sec15bfe098e/web>
- Google Play Console Help, *Use of the broad package (App) visibility (QUERY_ALL_PACKAGES) permission* — <https://support.google.com/googleplay/android-developer/answer/10158779>
- Android Developers, *Declare package visibility needs* — <https://developer.android.com/training/package-visibility/declaring>
- Android Help, *Learn about restricted settings* — <https://support.google.com/android/answer/12623953>
- Google Play Help, *Use Google Play Protect* — <https://support.google.com/googleplay/answer/2812853>
- AV-TEST, *Android antivirus tests, July 2026* — <https://www.av-test.org/en/antivirus/mobile-devices/android/july-2026/>
- Virus Bulletin, *VB100 test report — ESTsecurity ALYac (Windows), 2026-07-23* — <https://www.virusbulletin.com/uploads/vb100/test-reports/vb100-test-report-2026-07-23-estsecurity-alyac.pdf>
- 이스트시큐리티, *알약M (Android)* 제품 페이지 (벤더) — <https://www.estsecurity.com/public/product/alyacm/android>
- 알약 블로그, 스미싱 탐지와 알림 접근 권한 (벤더, 2019) — <https://blog.alyac.co.kr/2236>
- 경찰청·전기통신금융사기 통합대응단, 보이스피싱 악성앱 수법 보도자료 (2025-04-28) — <https://www.counterscam112.go.kr/bbs002/board/boardDetail.do?pstSn=60>
- 대한민국 정책브리핑, 2025년 1분기 보이스피싱 피해 (2025-04-28) — <https://www.korea.kr/news/policyNewsView.do?newsId=148942500>
- 대한민국 정책브리핑, 보이스피싱 근절 종합대책 (2025-08-28) — <https://www.korea.kr/news/policyNewsView.do?newsId=148948340>
- 금융위원회, 「보이스피싱 근절 종합대책」 추진상황 점검 (2025-12-30) — <https://www.fsc.go.kr/no010101/85959>
