---
layout: post
title: "Chrome 일반모드·시크릿모드·iPhone Private Browsing 차이"
date: 2026-09-15 22:10:47 +0900
categories: [Web, Security, Browser]
tags: [Chrome, Incognito, Private Browsing, InPrivate, Privacy]
---

# Chrome 일반모드·시크릿모드·Private Browsing 차이

브라우저의 일반모드와 비공개 브라우징은 화면이 비슷해 보이지만, 브라우징 데이터가 저장되는 범위와 세션 격리 방식이 다르다. 또한 `iPrivate`라는 표현은 보통 Apple Safari의 **Private Browsing**을 가리키는 말로 사용되며, Chrome의 공식 명칭은 **Incognito mode**다.

이 글에서는 다음을 구분한다.

- Chrome 일반모드
- Chrome 시크릿모드(Incognito)
- Safari Private Browsing
- 참고로 비교하는 Microsoft Edge InPrivate

핵심부터 말하면 비공개 모드는 **인터넷에서 익명으로 만들어 주는 기능이 아니라, 주로 이 기기에 남는 브라우징 흔적을 줄이는 기능**이다. Google은 Chrome Incognito가 기기 저장 정보를 제한하지만 방문한 사이트, 네트워크 관리자, 인터넷 서비스 제공자가 활동을 관찰할 수 있다고 설명한다.[1]

## 1. Chrome 일반모드

일반모드는 사용자가 평소 Chrome을 사용하는 기본 세션이다.

```text
Chrome 일반 창
  ├─ 방문 기록
  ├─ 쿠키·사이트 데이터
  ├─ 캐시
  ├─ 자동완성·저장 비밀번호
  ├─ 확장 프로그램
  └─ Chrome 프로필·동기화 설정
```

### 일반모드의 특징

- 방문 기록이 Chrome 프로필에 남는다.
- 쿠키와 사이트 데이터가 다음 방문에도 유지된다.
- 로그인 세션이 유지될 수 있다.
- 캐시로 재방문 속도를 높일 수 있다.
- 자동완성, 저장 비밀번호, 북마크, 확장 프로그램을 사용할 수 있다.
- Chrome 동기화를 켠 경우 설정과 일부 데이터가 계정·기기 사이에서 동기화될 수 있다.

### 일반모드 사용사례

- 매일 사용하는 업무 시스템
- 로그인 상태를 유지해야 하는 쇼핑몰
- 개발자 도구와 확장 프로그램을 사용하는 개발 작업
- 캐시와 쿠키가 필요한 웹앱
- 개인화·동기화가 편리한 일상적인 웹 탐색

### 장점

- 사용성이 가장 좋다.
- 로그인·설정·확장 프로그램·캐시가 유지된다.
- 웹앱의 정상적인 장기 세션을 재현하기 쉽다.
- 브라우저의 일반적인 개발·테스트 환경이다.

### 단점

- 다른 사람이 같은 OS 계정을 사용하면 기록을 볼 수 있다.
- 오래된 쿠키·캐시 때문에 현재 동작과 다른 화면이 나올 수 있다.
- 여러 계정의 동시 검증이 어렵다.
- 사이트별 상태가 누적되어 재현성이 떨어질 수 있다.

## 2. Chrome 시크릿모드(Incognito)

Chrome 시크릿모드를 열면 일반 창과 분리된 별도 브라우징 세션이 시작된다. Chrome은 모든 시크릿 창을 닫으면 해당 세션을 종료한다.[1]

```text
Chrome 시크릿 창
  ├─ 임시 쿠키·사이트 데이터
  ├─ 임시 세션 기록
  ├─ 기본적으로 차단되는 third-party cookies
  └─ 일반 프로필과 분리된 창 상태
```

### 시크릿모드에서 일반적으로 남지 않는 것

시크릿 세션이 끝난 뒤 Chrome은 방문한 사이트 기록과 사이트 데이터를 일반 세션처럼 보존하지 않는다.[1]

- 방문 기록
- 시크릿 세션의 쿠키·사이트 데이터
- 세션 중 입력한 일부 form data
- 시크릿 창의 일반적인 세션 상태

단, 모든 시크릿 창을 닫아야 세션이 끝난다. 시크릿 창을 하나라도 남겨두면 세션이 계속될 수 있다.[1]

### 시크릿모드에서도 남는 것

시크릿은 완전 삭제 모드가 아니다.

- 다운로드한 파일은 디스크에 남는다.
- 저장한 북마크는 일반 Chrome 세션에서도 사용할 수 있다.
- 방문한 웹사이트는 요청을 볼 수 있다.
- 회사·학교 네트워크 관리자와 ISP가 트래픽을 관찰할 수 있다.
- 로그인하면 해당 서비스는 사용자의 계정 활동과 연결할 수 있다.
- 악성 확장 프로그램이나 기기 자체의 감시를 자동으로 해결하지 않는다.

Google도 Incognito가 방문한 웹사이트나 네트워크를 관리하는 조직으로부터 사용자를 보이지 않게 만들지 않는다고 명시한다.[1]

### 시크릿모드 사용사례

#### 1. 로그인하지 않은 상태 테스트

```text
일반모드: 기존 쿠키·로그인 상태로 정상
시크릿: 신규 사용자처럼 동작하는지 확인
```

회원가입, 로그인, 결제, redirect, 쿠키 설정 문제를 분리할 때 유용하다.

#### 2. 여러 계정 동시 확인

일반 창에서 계정 A를 사용하면서 시크릿 창에서 계정 B를 확인할 수 있다. 다만 서비스가 IP, device fingerprint, 계정 정책을 이용하면 완전히 독립된 사용자로 보장되는 것은 아니다.

#### 3. 캐시·쿠키 원인 분리

일반모드에서만 발생하는 문제라면 시크릿모드에서 재현해 다음을 분리할 수 있다.

- 오래된 쿠키
- 캐시된 JavaScript
- 기존 local storage
- 만료된 로그인 상태
- 확장 프로그램 영향

#### 4. 공유 컴퓨터에서 임시 세션

Google은 공유 컴퓨터 사용이나 선물 구매처럼 기기에 브라우징 정보를 남기고 싶지 않은 경우 Incognito가 유용할 수 있다고 설명한다.[1]

### 시크릿모드의 장점

- 기기에 남는 방문 기록을 줄인다.
- 기존 일반모드 쿠키와 분리해서 테스트할 수 있다.
- 빠른 일회성 로그인·계정 테스트에 적합하다.
- 일부 third-party cookies가 기본 차단되어 추적과 cross-site 동작을 확인할 수 있다.[1]

### 시크릿모드의 한계

- IP 주소를 숨기지 않는다.
- DNS·ISP·회사 네트워크 관찰을 막지 않는다.
- 웹사이트의 서버 로그를 지우지 않는다.
- 다운로드 파일과 북마크는 남을 수 있다.
- 사용자가 로그인하면 서비스는 계정을 식별할 수 있다.
- VPN, Tor, 광고 차단기, 보안 브라우저와 같은 익명화 도구가 아니다.
- 확장 프로그램은 기본적으로 제한되거나 별도 허용이 필요할 수 있다.

## 3. Safari Private Browsing

Apple Safari의 공식 명칭은 **Private Browsing**이다. macOS Safari에서 private window를 사용하면 브라우징 세부정보가 저장되지 않고, 방문한 사이트가 다른 Apple 기기와 공유되지 않는다.[3]

### Safari Private Browsing의 특징

Apple 문서에 따르면 Private Browsing에서는 다음 동작이 적용된다.[3]

- 방문 페이지와 AutoFill 정보가 저장되지 않는다.
- 최근 검색이 Smart Search 기록에 포함되지 않는다.
- 열린 페이지가 iCloud의 다른 기기 탭에 표시되지 않는다.
- 다운로드 항목이 Safari 다운로드 목록에 포함되지 않는다.
- 다운로드한 파일 자체는 Mac에 남는다.
- 쿠키와 웹사이트 데이터 변경이 저장되지 않는다.
- Handoff로 private browsing 창이 다른 Apple 기기로 전달되지 않는다.
- macOS Safari에서는 advanced tracking and fingerprinting protection이 기본 활성화된다.

### Safari Private Browsing 사용사례

- Safari에서 로그인하지 않은 사용자 테스트
- iCloud 탭·Handoff에 남기고 싶지 않은 탐색
- AutoFill과 검색 기록을 분리하는 일회성 작업
- Safari의 tracking protection과 일반 창 동작 비교
- iPhone과 Mac의 Safari 세션을 분리하는 테스트

### Chrome Incognito와의 공통점

- 로컬 브라우징 흔적을 줄인다.
- 세션 종료 후 일반적인 사이트 데이터 보존을 제한한다.
- 다운로드한 파일 자체는 남을 수 있다.
- 웹사이트·회사 네트워크·ISP에 대한 완전한 익명성을 제공하지 않는다.

### Safari Private Browsing의 차이

Safari는 Apple 생태계의 iCloud 탭·Handoff와 연동되는 기능을 별도로 차단한다. 또한 Apple 문서에 따르면 private window에서 advanced tracking and fingerprinting protection과 URL tracking parameter 제거가 적용될 수 있다.[3]

따라서 Chrome Incognito와 Safari Private Browsing은 목적은 비슷하지만, 쿠키 정책·tracking protection·기기 동기화·확장 프로그램 동작은 브라우저별로 다르게 검증해야 한다. iPhone·iPad에서도 Safari의 Private Browsing을 별도 탭 그룹으로 사용할 수 있다.[4]

## 4. Microsoft Edge InPrivate

참고로 Microsoft Edge에서는 같은 목적의 기능을 **InPrivate**라고 부른다. Microsoft 문서는 모든 InPrivate 창을 닫으면 browsing history, download history, cookies, site data, cached images, passwords, autofill form data, site permissions와 hosted app data가 삭제된다고 설명한다.[2]

다만 즐겨찾기와 다운로드한 파일은 보존된다.[2]

즉, 용어는 다음처럼 대응된다.

```text
Chrome → Incognito mode(시크릿모드)
Edge   → InPrivate
Safari → Private Browsing
```

이름은 다르지만 세 기능 모두 일반 세션과 분리된 임시 브라우징 컨텍스트를 제공한다. 정확한 저장·삭제 범위는 브라우저와 운영체제의 공식 문서를 기준으로 확인해야 한다.

## 5. 비교표

| 항목 | Chrome 일반모드 | Chrome 시크릿모드 | Safari Private Browsing | Edge InPrivate |
|---|---|---|---|---|
| 방문 기록 | 저장 | 세션 종료 후 보존 제한 | 저장하지 않음 | 세션 종료 후 삭제 |
| 쿠키·사이트 데이터 | 유지 | 세션용, 종료 후 제거 | 변경사항 저장 제한 | 종료 후 삭제 |
| 로그인 유지 | 유지 가능 | 임시 세션 | 임시 세션 | 임시 세션 |
| 다운로드 파일 | 유지 | 유지 | 파일은 유지 | 유지 |
| 북마크/즐겨찾기 | 저장 | 저장 가능 | 일반 북마크 정책 적용 | 저장 가능 |
| IP 숨김 | 아니오 | 아니오 | 아니오 | 아니오 |
| 회사·ISP 관찰 차단 | 아니오 | 아니오 | 아니오 | 아니오 |
| 확장 프로그램 | 일반 사용 | 기본 제한 가능 | 설정에 따름 | 정책·설정에 따름 |
| 기존 쿠키 영향 | 받음 | 분리 | 분리 | 분리 |
| 주 용도 | 일상·업무 | 임시 세션·쿠키 분리 | Apple 기기 기록 분리 | Edge 임시 세션 |

표의 브라우저별 저장 범위는 Google·Microsoft·Apple 공식 문서의 설명을 기준으로 정리했다.[1][2][3]

## 6. 개발·장애 분석에서의 활용

브라우저 모드만 바꿔도 다음과 같은 문제를 빠르게 분리할 수 있다.

### 문제 A: 일반모드에서만 로그인 실패

가능성:

- 오래된 cookie
- 만료된 refresh token
- local storage 데이터
- 확장 프로그램
- Service Worker cache

확인 순서:

```text
일반모드 재현
→ 시크릿모드 재현
→ DevTools Application에서 cookie·storage 확인
→ Service Worker와 cache version 확인
```

시크릿에서 정상이라면 서버 장애로 바로 결론 내리지 말고, 기존 브라우저 상태를 먼저 의심한다.

### 문제 B: 시크릿모드에서 결제 또는 SSO 실패

가능성:

- third-party cookie 차단
- cross-site redirect 정책
- popup 차단
- 확장 프로그램 미적용에 따른 동작 차이
- OAuth state·callback 쿠키 저장 실패

이 경우 시크릿모드가 “더 안전해서 정상”이라고 단정하지 말고, 쿠키·redirect·SameSite 정책을 네트워크 trace로 확인해야 한다.

### 문제 C: 두 모드 모두 실패

가능성:

- 서버 오류
- DNS·네트워크 장애
- TLS 인증서 문제
- API endpoint 오류
- 계정 권한 문제

두 모드의 공통 실패는 브라우저 로컬 데이터 외의 원인을 우선 조사할 신호지만, 이것만으로 서버 원인을 확정하지는 않는다.

### 문제 D: Safari만 다르게 동작

가능성:

- WebKit과 Chromium의 구현 차이
- Intelligent Tracking Prevention
- cookie partitioning
- storage 정책
- user-agent 또는 feature detection
- Safari Private Browsing의 tracking protection

브라우저 이름만 기록하지 말고 다음을 같이 남겨야 한다.

```text
Browser / version
OS / version
Normal or private context
Cookie state
Extension state
URL
HTTP status
Console error
Network request/response
```

## 7. “시크릿이면 안전하다”는 오해

### 오해 1: IP가 숨겨진다

아니다. Incognito, InPrivate, Private Browsing은 IP 익명화 기능이 아니다.

### 오해 2: 회사나 ISP가 못 본다

아니다. Google은 조직 네트워크 관리자와 ISP가 활동을 관찰할 수 있다고 설명한다.[1]

### 오해 3: 다운로드 파일도 자동 삭제된다

아니다. 다운로드한 파일은 기기에 남을 수 있다.[1][2][3]

### 오해 4: 모든 cookie가 차단된다

아니다. 브라우저마다 정책이 다르고, Chrome Incognito도 사이트 동작을 위해 세션 중 cookie를 사용한다.[1]

### 오해 5: 악성코드·키로거로부터 보호된다

아니다. 비공개 브라우징은 로컬 기록을 줄이는 기능이지 endpoint security나 악성코드 방어 기능이 아니다.

## 8. 선택 기준

### 일반모드가 적합한 경우

- 로그인과 개인화가 필요하다.
- 확장 프로그램과 캐시를 사용해야 한다.
- 장기적인 웹앱 사용이 목적이다.
- 실제 사용자 환경을 재현해야 한다.

### 시크릿·Private 모드가 적합한 경우

- 로그인하지 않은 상태를 테스트한다.
- 기존 cookie·cache 영향을 배제한다.
- 공유 기기에 기록을 남기고 싶지 않다.
- 계정 B를 별도로 확인한다.
- 일반 세션과 새 세션의 차이를 비교한다.

### VPN·Tor·보안 도구가 필요한 경우

- IP 노출을 줄여야 한다.
- 네트워크 경로의 익명성 또는 분리성이 필요하다.
- 브라우저 기록 삭제 이상의 보안 요구가 있다.

이 경우 시크릿모드만으로는 목적을 달성할 수 없다.

## 결론

세 모드의 차이는 다음과 같이 요약할 수 있다.

```text
일반모드:
  편의성과 지속성
  로그인·쿠키·캐시·확장 프로그램 유지

Chrome 시크릿모드:
  로컬 기록 최소화와 임시 세션
  기존 일반모드 쿠키와 분리

Safari Private Browsing:
  로컬 기록·iCloud 탭·Handoff 분리
  Safari의 tracking protection 정책 적용

Edge InPrivate:
  InPrivate 세션 종료 시 브라우징 데이터 정리
```

가장 중요한 결론은 이것이다.

> 비공개 브라우징은 **기기에 남는 기록을 줄이는 기능**이지, **인터넷에서 사용자를 보이지 않게 만드는 익명화 기능**이 아니다.

개발과 장애 분석에서는 일반모드와 비공개 모드를 서로 대체재로 보지 말고, 다음처럼 비교 도구로 사용하는 것이 좋다.

```text
일반모드 재현
→ 비공개모드 재현
→ cookie/cache/storage 차이 확인
→ Network·Console·Service Worker trace 대조
→ 서버·DNS·TLS·권한 문제 분리
```

## 참고 자료

[1] Google Chrome Help — Incognito mode의 저장 범위, 세션 종료, 네트워크 관찰 한계  
[2] Microsoft Support — Edge InPrivate의 삭제·보존 데이터  
[3] Apple Support — Safari Private Browsing의 기록·iCloud·Handoff·tracking protection 동작

## 출처

- Google Chrome Incognito: https://support.google.com/chrome/answer/95464?hl=en&co=GENIE.Platform%3DDesktop
- Microsoft Edge InPrivate: https://support.microsoft.com/en-us/edge/browse-inprivate-in-microsoft-edge
- Apple Safari Private Browsing: https://support.apple.com/guide/safari/browse-privately-ibrw1069/mac
- Apple iPhone Private Browsing: https://support.apple.com/guide/iphone/browse-the-web-privately-iphb01fc3c85/ios

## Sources

[1] https://support.google.com/chrome/answer/95464?hl=en&co=GENIE.Platform%3DDesktop — Google Chrome Incognito mode
[2] https://support.microsoft.com/en-us/edge/browse-inprivate-in-microsoft-edge — Microsoft Edge InPrivate
[3] https://support.apple.com/guide/safari/browse-privately-ibrw1069/mac — Apple Safari Private Browsing
[4] https://support.apple.com/guide/iphone/browse-the-web-privately-iphb01fc3c85/ios — Apple iPhone Private Browsing
