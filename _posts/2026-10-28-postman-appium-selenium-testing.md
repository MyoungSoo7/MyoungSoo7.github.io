---
layout: post
title: "Postman·Appium·Selenium 비교 — API·모바일·웹 테스트를 하나의 품질 파이프라인으로 묶기"
date: 2026-10-28 00:54:50 +0900
categories: [Testing, QA, Automation, DevOps]
tags: [Postman, Appium, Selenium, API Testing, Mobile Testing, Web Testing, CI]
---

> 기준 시각: 2026-10-28 00:54 KST. Postman·Appium·Selenium 공식 문서를 기준으로 정리했다. 제품별 최신 기능과 요금·한도는 변경될 수 있으며, 아래 비교는 도구의 역할과 공식 인터페이스 중심이다.

## 결론

**Postman은 API 계약·기능·모니터링, Appium은 네이티브·모바일 웹·하이브리드 앱, Selenium은 웹 브라우저 자동화와 분산 실행**에 초점을 둔다.[1][2][3] 셋은 경쟁 제품이라기보다 테스트 피라미드와 CI/CD 파이프라인의 서로 다른 계층을 맡기는 조합이다.

```text
API contract / integration  → Postman
Mobile native / hybrid      → Appium
Desktop web / cross-browser → Selenium
CI/CD orchestration         → test runner + artifacts + reports
```

## 1. 도구별 핵심 역할

| 도구 | 주 대상 | 핵심 인터페이스 | 대표 검증 |
| --- | --- | --- | --- |
| Postman | HTTP API·서비스 워크플로우 | request·collection·post-response script | status·schema·body·인증·응답시간 |
| Appium | Android·iOS·모바일 웹·하이브리드 | WebDriver 기반 core·driver·client·plugin | 화면 요소·제스처·앱 상태·WebView 전환 |
| Selenium | 데스크톱 웹 브라우저 | W3C WebDriver·WebDriver BiDi·Grid | UI 흐름·브라우저 호환성·회귀·병렬 실행 |

Postman은 요청을 collection으로 묶고 테스트·모니터·CLI 실행으로 확장한다.[1] Appium은 Core, Drivers, Clients, Plugins로 나뉘며 대상 플랫폼용 driver와 언어별 client가 필요하다.[2] Selenium은 브라우저를 실제 사용자처럼 제어하는 WebDriver와 원격·분산 실행을 위한 Grid를 제공한다.[3]

## 2. Postman: API 테스트와 운영 모니터링

### 2.1 Collection은 요청 모음이 아니라 테스트 단위

Postman collection은 저장된 요청을 그룹화한 단위이면서 workflow 또는 test suite로 사용할 수 있다.[1]

```text
로그인
  → access token 추출
  → 사용자 조회
  → 주문 생성
  → 주문 상태 확인
  → 오류·권한·응답시간 검증
```

Postman post-response script에서 요청 결과를 검증하고, collection·folder·request 수준의 공통 테스트를 재사용할 수 있다.[1]

```javascript
pm.test("status is successful", () => {
  pm.expect(pm.response.code).to.be.oneOf([200, 201]);
});

pm.test("response time is acceptable", () => {
  pm.expect(pm.response.responseTime).to.be.below(1000);
});
```

실제 프로젝트에서는 status code만 확인하지 말고 다음도 함께 검증한다.

- JSON schema와 필수 필드
- business status와 오류 코드
- 인증 만료·권한 경계
- idempotency·중복 생성 여부
- 응답시간 p95/p99
- 민감정보가 response·log에 노출되지 않는지

### 2.2 CI와 Monitor

Postman collection은 수동 실행·예약 실행·Postman CLI·Monitors·performance testing·webhook으로 실행할 수 있다.[4] Monitors는 collection 요청과 테스트를 주기적으로 실행하고 실패·오류·timeout을 기록한다.[5]

```text
개발자 로컬
  → Collection Runner
CI pipeline
  → Postman CLI
주기적 상태 확인
  → Monitor
배포 후 검증
  → smoke collection + endpoint read-back
```

Postman CLI와 Newman을 혼동하지 않는 것도 중요하다. 공식 문서는 새 CI/CD 흐름에는 Postman CLI를 사용하고, 기존 Newman workflow는 별도 마이그레이션을 검토하라고 안내한다.[4]

## 3. Appium: 모바일 앱과 하이브리드 테스트

Appium은 모바일·웹·데스크톱 등 여러 플랫폼의 UI 자동화를 목표로 하며, JS·Java·Python 등 여러 언어로 테스트 코드를 작성할 수 있다.[2]

구조는 다음과 같다.

```text
Appium Core
   ├─ Driver: Android / iOS / target platform
   ├─ Client: Java / Python / JS / C# 등
   └─ Plugin: 기능 확장
```

Appium을 시작하려면 Appium 자체뿐 아니라 대상 플랫폼 driver와 언어 client를 설치해야 하며, 필요할 때 plugin을 추가한다.[2]

### 3.1 네이티브·모바일 웹·하이브리드

- Android 네이티브: Android driver·emulator/real device
- iOS 네이티브: XCUITest 기반 driver·simulator/real device
- Android Chrome·iOS Safari: 모바일 웹 자동화
- Hybrid: native context와 WebView context 사이 전환

Appium의 기본 API는 WebDriver 기반이지만, 모든 웹 브라우저 명령이 네이티브 앱에서 동일하게 지원되는 것은 아니다. 플랫폼별 driver가 실제 명령을 구현하며, capability와 실행 환경을 정확히 맞춰야 한다.[2]

```text
NATIVE_APP
   ↓ context switch
WEBVIEW_<id>
   ↓ WebDriver selectors
웹 콘텐츠 조작
```

### 3.2 모바일 테스트의 현실적인 검증 포인트

- OS·device·screen size 조합
- 앱 설치·권한·초기화 상태
- emulator와 real device 차이
- 네트워크 전환·백그라운드 복귀
- 권한 dialog·알림·키보드
- WebView debug 설정과 driver 호환성
- 테스트 후 앱·세션·데이터 정리

모바일 UI 테스트는 selector가 바뀌거나 animation·네트워크 상태가 달라질 때 flaky해지기 쉽다. 고정 sleep보다 명시적 wait·상태 기반 assertion·실패 시 화면·로그·device artifact를 남기는 방식이 안전하다.

## 4. Selenium: 웹 브라우저와 Grid

Selenium WebDriver는 브라우저 vendor가 제공하는 자동화 API를 통해 실제 사용자가 조작하는 것처럼 브라우저를 제어한다.[3]

```python
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
driver = webdriver.Chrome(options=options)
try:
    driver.get("https://example.com")
    assert "Example" in driver.title
finally:
    driver.quit()
```

Selenium Manager가 driver·browser 관리를 자동화할 수 있어 직접 driver를 내려받는 부담을 줄인다.[3]

### 4.1 Grid로 병렬·크로스 브라우저

Selenium Grid는 WebDriver 명령을 원격 browser instance로 라우팅해 여러 머신·브라우저·운영체제에서 병렬 실행할 수 있다.[3]

```text
Test Runner
     ↓ Remote WebDriver
Selenium Grid
  ├─ Chrome node
  ├─ Firefox node
  └─ Edge node
```

Grid 운영 시에는 다음을 별도로 관리한다.

- browser capability와 실제 node 일치
- session timeout·queue·max concurrency
- node별 CPU·메모리·shared memory
- 영상·스크린샷·console log·network artifact
- 원격 파일 upload/download 경로
- 테스트 격리와 session 종료

Grid는 병렬화를 가능하게 하지만 flaky test를 자동으로 고쳐 주지는 않는다. 병렬 실행 전에 테스트 데이터·계정·브라우저 profile을 격리해야 한다.

## 5. 세 도구를 함께 쓰는 테스트 피라미드

```text
                         E2E / UI
              Selenium (web) + Appium (mobile)
                         ▲
                  API workflow / contract
                         Postman
                         ▲
                unit / component / service tests
```

### 추천 파이프라인

1. **Pull Request**: unit·component 테스트와 빠른 Postman smoke collection
2. **main merge**: API integration collection·contract·schema 검증
3. **staging deploy**: Selenium web smoke와 Appium 핵심 mobile flow
4. **release candidate**: 브라우저·OS·device matrix와 회귀 테스트
5. **production**: Postman Monitor 기반 health·critical workflow 점검
6. **장애 분석**: request ID·browser/device artifact·server log를 시간축으로 결합

Postman 성공은 API 계약이 통과했다는 뜻이고, Selenium·Appium 성공은 특정 UI·브라우저·device 조합이 통과했다는 뜻이다. 어느 하나가 통과했다고 전체 시스템 품질을 보장하지 않는다.

## 6. 실패 분석과 flaky 관리

### Postman 실패

- DNS·TLS·connection timeout
- status code 불일치
- schema·business field 불일치
- token·environment 변수 오류
- 이전 request의 데이터 전달 실패
- server 처리 지연·retry 중복

### Appium 실패

- driver·OS·device capability 불일치
- 앱 설치·권한·초기화 실패
- selector·context·WebView 오류
- emulator와 real device 동작 차이
- animation·network·keyboard timing

### Selenium 실패

- browser·driver·Grid node mismatch
- stale element·implicit/explicit wait 혼용
- 테스트 데이터·계정 공유
- headless와 headed 렌더링 차이
- 원격 node 자원·shared memory 부족

### 공통 원칙

- 재시도 횟수보다 최초 실패 원인을 먼저 보존
- retry로 통과한 테스트를 무조건 PASS로 숨기지 않기
- timeout·assertion·infrastructure failure 분리
- 테스트별 trace ID와 환경 metadata 저장
- flaky 비율·p95 실행시간·실패 재현률 추적

## 7. 어떤 도구를 선택할까

| 상황 | 우선 도구 | 이유 |
| --- | --- | --- |
| REST/GraphQL API 빠른 검증 | Postman | collection·script·CLI·monitor |
| API workflow와 배포 smoke | Postman CLI | CI/CD·환경변수·리포트 |
| Android/iOS 네이티브 앱 | Appium | mobile driver·client·device 자동화 |
| 모바일 웹 | Appium 또는 Selenium | device/browser 조건에 따라 선택 |
| 데스크톱 웹 회귀 | Selenium | WebDriver·브라우저 호환성 |
| 여러 브라우저·OS 병렬 | Selenium Grid | 원격 node·분산 session |
| 전체 사용자 여정 | Postman + Selenium/Appium | API와 UI를 분리 검증 후 결합 |

## 8. Hermes·Kubernetes·CI에 연결하기

Hermes는 테스트 작업을 분해하고 Postman CLI·Selenium Grid·Appium 실행을 조율할 수 있다. Kubernetes에서는 Selenium Grid·Appium device farm·API test runner를 namespace와 Job으로 격리할 수 있지만, 실제 `apply`·rollout·삭제는 별도 승인과 read-back이 필요하다.

```text
Hermes Orchestrator
  ├─ Postman API collection
  ├─ Selenium Grid job
  ├─ Appium device job
  ├─ test artifact collector
  └─ 최종 PASS/WARN/FAIL/UNVERIFIED 판정
```

최종 판정에 포함할 증거는 다음과 같다.

- 실행 commit·환경·브라우저·device·OS
- Postman collection·environment 버전
- request/response 상태·schema·응답시간
- Selenium/Appium screenshot·video·console·device log
- CI job ID·최종 exit code·재시도 횟수
- 배포된 artifact 또는 endpoint read-back

## 확인된 사실과 미확인 범위

- **공식 문서 확인:** Postman은 collection·script·CLI·monitor·performance test를 지원하고, Appium은 Core·Drivers·Clients·Plugins 구조로 모바일·웹·데스크톱 자동화를 구성하며, Selenium은 WebDriver와 Grid로 브라우저 자동화·분산 실행을 제공한다.[1][2][3][4][5]
- **설계 해석:** 세 도구를 API·모바일·웹 계층으로 나눠 CI/CD 파이프라인에 배치하는 것은 문서 기능을 테스트 운영 구조로 재구성한 권장안이다.
- **미확인:** 특정 프로젝트의 최적 병렬 수, 실행시간, 비용, flaky 비율, 디바이스 커버리지는 실제 저장소·환경에서 측정해야 한다.

## 참고 자료

[1] [Postman Docs — Get started](https://learning.postman.com/docs/getting-started/introduction/)

[2] [Appium Docs — Appium in a Nutshell](https://appium.io/docs/en/latest/intro/)

[3] [Selenium Documentation](https://www.selenium.dev/documentation/)

[4] [Postman Docs — Test your API functionality](https://learning.postman.com/docs/tests-and-scripts/running-collections/running-collections-overview)

[5] [Postman Docs — Monitors](https://learning.postman.com/docs/tests-and-scripts/run-tests/test-with-monitors)

> ※ 이 글은 도구별 공식 문서를 바탕으로 한 비교·설계 정리이며, 특정 프로젝트에서 세 도구를 실제 실행한 결과나 성능 벤치마크가 아니다.

## Sources

[1] https://learning.postman.com/docs/getting-started/introduction
[2] https://appium.io/docs/en/latest/intro
[3] https://www.selenium.dev/documentation
[4] https://learning.postman.com/docs/tests-and-scripts/running-collections/running-collections-overview
[5] https://learning.postman.com/docs/tests-and-scripts/run-tests/test-with-monitors
