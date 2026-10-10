---
layout: post
title: "[CS300 #217] 크로스플랫폼 개발 — 무엇을 공유하고 무엇을 각자 만들까"
date: 2026-10-10 21:37:00 +0900
categories: [cs]
tags: [cs300, web, cross-platform, react-native, flutter, kotlin-multiplatform]
---

컴퓨터공학 300 주제 시리즈의 217번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

크로스플랫폼 개발은 하나의 코드베이스로 iOS·Android(때로는 웹·데스크톱)를 함께 만드는 일이고, 접근법은 "무엇을 공유하느냐"에 따라 웹뷰, 네이티브 컴포넌트를 쓰는 자바스크립트 런타임(React Native), 자체 렌더링 엔진(Flutter), 로직만 공유(Kotlin Multiplatform)로 나뉜다.

## 왜 필요한가

같은 앱을 iOS 는 Swift 로, Android 는 Kotlin 으로 두 번 만들면 다음 비용이 든다.

- 기능 하나를 두 팀이 두 번 구현하고 두 번 테스트한다.
- 두 플랫폼의 동작이 미묘하게 달라진다. 할인 계산 로직이 한쪽에만 고쳐지는 식이다.
- 출시 일정이 느린 쪽에 맞춰진다.

크로스플랫폼은 이 중복을 줄인다. 대신 "추상화 계층"이라는 새 비용을 들인다. 플랫폼의 새 기능을 바로 쓰기 어렵고, 성능 문제가 생기면 계층 아래까지 내려가야 하며, 결국 플랫폼 지식이 필요해진다. 어디까지 공유할지가 핵심 결정이다.

## 핵심 개념

### 네 가지 접근법

```
              공유 범위 →  (많이)                                (적게)
 ┌──────────────┬──────────────────┬──────────────────┬──────────────────┐
 │ 웹뷰 하이브리드  │ JS + 네이티브 UI   │ 자체 렌더링 엔진    │ 로직만 공유         │
 │ (Capacitor 등) │ (React Native)    │ (Flutter)         │ (Kotlin MP)       │
 ├──────────────┼──────────────────┼──────────────────┼──────────────────┤
 │ HTML/CSS 를   │ JS 가 네이티브      │ 엔진이 픽셀을       │ 비즈니스 로직만     │
 │ 웹뷰가 그림    │ 컴포넌트를 조작     │ 직접 그림          │ 공유, UI 는 각자    │
 └──────────────┴──────────────────┴──────────────────┴──────────────────┘
```

| 접근 | UI 를 누가 그리나 | 언어 | 강점 | 약점 |
|---|---|---|---|---|
| 웹뷰 하이브리드 | 웹뷰 (브라우저 엔진) | HTML/CSS/JS | 웹 코드 재사용 최대 | 네이티브 느낌·성능 한계 |
| React Native | 플랫폼 네이티브 컴포넌트 | JS/TS + React | 웹 개발자 진입 쉬움, 네이티브 모양 | JS 와 네이티브 경계 비용 |
| Flutter | 자체 엔진이 직접 렌더링 | Dart | 플랫폼 간 동일한 화면, 일관된 성능 | 플랫폼 UI 와 미묘한 차이, 앱 크기 |
| Kotlin Multiplatform | 각 플랫폼 UI (선택적으로 Compose Multiplatform) | Kotlin | 로직 공유 + 완전한 네이티브 UI | UI 는 따로 만들어야 함 |

### React Native: 경계를 얼마나 싸게 넘나

React Native 는 자바스크립트로 React 컴포넌트를 작성하면 실제로는 iOS·Android 의 네이티브 뷰가 그려진다. 따라서 성능의 관건은 자바스크립트와 네이티브 사이의 통신이다.

예전 구조에서는 둘 사이를 **비동기 브리지**가 이었다. 호출을 직렬화한 메시지로 주고받았기 때문에, 작은 호출이 많거나 큰 데이터를 넘기면 직렬화 비용이 들고, 결과를 동기로 받을 수 없었다. React Native 공식 문서에 따르면 새 아키텍처는 이 비동기 브리지를 없애고 **JSI(JavaScript Interface)** 로 바꿨다. JSI 는 자바스크립트가 C++ 객체의 참조를 직접 들고 메서드를 호출할 수 있게 하는 인터페이스다. 새 렌더러(Fabric)와 네이티브 모듈 체계도 이 위에 다시 만들어졌고, React Native 0.76 부터 새 아키텍처가 기본값이 되었다.

### Flutter: 플랫폼 위젯을 쓰지 않는다

Flutter 는 플랫폼의 버튼·목록 컴포넌트를 쓰지 않고, 위젯 트리를 자체 엔진으로 직접 그린다. 공식 아키텍처 문서에 따르면 모바일에서는 앱과 함께 배포되는 Impeller 가 렌더링을 맡고, 웹 대상에서는 Skia 엔진의 WebAssembly 빌드를 쓴다. 개발 중에는 VM 위에서 핫 리로드로 돌고, 릴리스 빌드에서는 Dart 코드가 기계어로 직접 컴파일된다. 화면이 모든 플랫폼에서 픽셀 단위로 같다는 것이 장점이지만, 플랫폼이 새 UI 동작을 내놓으면 Flutter 쪽에서 다시 구현해야 따라간다. 카메라·블루투스 같은 플랫폼 기능은 **플랫폼 채널**로 네이티브 코드와 메시지를 주고받아 쓴다.

### Kotlin Multiplatform: 공유는 로직에서 멈춘다

Kotlin Multiplatform 은 네트워크, 저장소, 비즈니스 규칙처럼 화면이 아닌 부분을 Kotlin 으로 한 번 쓰고, iOS 에서는 네이티브 프레임워크로, Android 에서는 일반 라이브러리로 쓴다. 플랫폼마다 다른 구현이 필요한 곳은 `expect`/`actual` 선언으로 나눈다.

```kotlin
// 공통 코드
expect fun platformName(): String

// Android
actual fun platformName(): String = "Android"

// iOS
actual fun platformName(): String = "iOS"
```

UI 는 SwiftUI 와 Jetpack Compose 로 각자 만들 수 있고, 원하면 Compose Multiplatform 으로 UI 까지 공유할 수도 있다. 기존 네이티브 앱에 점진적으로 도입하기 쉽다는 것이 특징이다.

### 고르는 기준

1. **팀의 기술**: 웹 팀이 주력이면 React Native, 새로 꾸리는 팀이면 Flutter 도 후보, 이미 네이티브 팀이 두 개 있으면 Kotlin Multiplatform 으로 로직부터 합치기.
2. **화면의 성격**: 플랫폼 관례를 그대로 따라야 하는가, 브랜드 디자인이 플랫폼보다 중요한가.
3. **네이티브 기능 비중**: 카메라 실시간 처리, 백그라운드 위치, 블루투스처럼 플랫폼 API 를 깊게 쓸수록 공유 이득이 줄고 네이티브 코드가 늘어난다.
4. **장기 유지보수**: 프레임워크 메이저 업그레이드를 따라갈 인력이 있는가. 크로스플랫폼은 "플랫폼 업데이트 + 프레임워크 업데이트" 두 가지를 따라가야 한다.

어느 접근을 택하든 "네이티브를 몰라도 된다"는 기대는 맞지 않는다. 빌드 설정, 스토어 배포, 권한, 플랫폼별 버그를 다루려면 결국 양쪽 플랫폼을 이해하는 사람이 필요하다.

## 직접 해 보기

React Native 의 옛 브리지와 JSI 의 차이를 파이썬으로 흉내 낸다. 한쪽은 호출마다 JSON 으로 직렬화해 큐로 넘기고 나중에 결과를 받고, 다른 쪽은 객체 참조를 잡고 바로 호출한다. 실제 React Native 의 구현이 아니라 비용 구조를 보여 주는 모형이다.

```python
import json, time
from collections import deque

class NativeCamera:                       # '네이티브 쪽' 모듈이라고 가정
    def brightness(self, frame_id):
        return (frame_id * 37) % 256

native = NativeCamera()

# (1) 옛 방식 흉내: 호출을 JSON 문자열로 직렬화해 큐에 넣고, 반대편이 꺼내 역직렬화
outbox, inbox = deque(), deque()
def bridge_call(module, method, *args):
    outbox.append(json.dumps({"m": module, "f": method, "a": args}))
def native_side_drain():
    while outbox:
        msg = json.loads(outbox.popleft())
        result = getattr(native, msg["f"])(*msg["a"])
        inbox.append(json.dumps(result))
def js_side_drain():
    return [json.loads(inbox.popleft()) for _ in range(len(inbox))]

# (2) 새 방식 흉내: 네이티브 객체 참조를 직접 잡고 동기 호출 (JSI 의 아이디어)
def direct_call(i):
    return native.brightness(i)

N = 100_000
t = time.perf_counter()
for i in range(N): bridge_call("Camera", "brightness", i)
native_side_drain(); r1 = js_side_drain()
bridge_ms = (time.perf_counter() - t) * 1000

t = time.perf_counter()
r2 = [direct_call(i) for i in range(N)]
direct_ms = (time.perf_counter() - t) * 1000

print(f"결과 동일: {r1 == r2}")
print(f"직렬화 브리지: {bridge_ms:7.1f} ms  (비동기: 결과는 큐를 비운 뒤에야 받음)")
print(f"직접 호출    : {direct_ms:7.1f} ms  (동기: 호출 즉시 값)")
```

실행 결과(오래된 2코어 노트북 기준, 숫자는 기기마다 다르다):

```
결과 동일: True
직렬화 브리지:  2395.3 ms  (비동기: 결과는 큐를 비운 뒤에야 받음)
직접 호출    :    36.6 ms  (동기: 호출 즉시 값)
```

결과는 같지만, 작은 호출 10만 번에서 직렬화·역직렬화 비용이 대부분의 시간을 차지했다. 그리고 브리지 쪽은 큐를 비울 때까지 결과를 받을 수 없어서, "이 값을 보고 바로 다음 동작을 결정"하는 코드를 쓰기 어렵다. 실제 앱에서 스크롤에 맞춘 애니메이션, 카메라 프레임 처리처럼 경계를 자주 넘는 작업이 옛 구조의 약점이었던 이유다. 반대로 경계를 드물게 넘는 일반적인 화면에서는 이 차이가 체감되지 않을 수 있다. React Native 문서도 직렬화가 모든 앱의 병목은 아니었다고 적고 있다.

## 현업에서는

- **"공유율"을 목표로 삼지 않는다**: 코드 90% 공유를 목표로 플랫폼 관례를 억지로 맞추면 양쪽 사용자 모두 어색해한다. 로직은 최대한, UI 는 필요한 만큼 공유한다.
- **네이티브 모듈 담당자**: 크로스플랫폼 팀에도 iOS·Android 네이티브를 다룰 줄 아는 사람이 있어야 한다. 서드파티 라이브러리가 새 OS 버전에서 깨지면 직접 고쳐야 하는 일이 생긴다.
- **업그레이드 비용**: 프레임워크 메이저 버전을 오래 미루면 의존 라이브러리 호환성이 엉켜 한 번에 큰 비용을 치른다. 정기적으로 조금씩 올린다.
- **백엔드는 공통**: 앱이 무엇으로 만들어졌든 백엔드 API 는 같다. 홈랩 k3s 에 올린 API 서버 하나를 웹·iOS·Android 클라이언트가 함께 쓰는 구성에서는, 클라이언트 기술보다 API 하위 호환(216번 주제)이 더 자주 문제가 된다.

## 확인 문제

1. React Native 와 Flutter 는 화면을 그리는 방식에서 어떻게 다른가.
2. React Native 새 아키텍처가 옛 비동기 브리지 대신 도입한 것은 무엇이며, 무엇이 달라지는가.
3. Kotlin Multiplatform 의 `expect`/`actual` 은 어떤 문제를 푸는가.
4. 플랫폼 API(카메라, 블루투스)를 깊게 쓰는 앱에서 크로스플랫폼의 이득이 줄어드는 이유는?
5. 이미 iOS·Android 네이티브 팀이 있는 회사가 중복을 줄이려 할 때 무난한 첫 단계는?

### 풀이

1. React Native 는 플랫폼의 네이티브 컴포넌트를 조작해 그리고, Flutter 는 플랫폼 위젯을 쓰지 않고 자체 엔진으로 직접 픽셀을 그린다.
2. JSI. 자바스크립트가 C++ 객체 참조를 직접 잡고 호출하므로 메시지 직렬화가 사라지고 동기 호출이 가능해진다.
3. 공통 코드에서 선언한 기능을 플랫폼마다 다른 구현으로 제공해야 할 때, 선언(`expect`)과 플랫폼별 구현(`actual`)을 분리해 준다.
4. 그 기능들은 결국 플랫폼별 네이티브 코드와 연결 계층을 따로 작성·유지해야 하므로 공유되는 코드 비중이 줄고 경계 비용이 늘기 때문이다.
5. UI 는 각자 유지하고 네트워크·데이터·비즈니스 로직부터 Kotlin Multiplatform 같은 방식으로 공유하는 것.

## 더 읽을거리 (References)

- React Native, *About the New Architecture*: <https://reactnative.dev/architecture/landing-page>
- React Native Blog, *New Architecture is here*: <https://reactnative.dev/blog/2024/10/23/the-new-architecture-is-here>
- Flutter, *Flutter architectural overview*: <https://docs.flutter.dev/resources/architectural-overview>
- Kotlin, *Expected and actual declarations*: <https://kotlinlang.org/docs/multiplatform/multiplatform-expect-actual.html>
