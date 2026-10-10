---
layout: post
title: "[CS300 #216] 모바일 앱 아키텍처 — 언제든 죽을 수 있는 프로세스 위에 짓기"
date: 2026-10-10 21:36:00 +0900
categories: [cs]
tags: [cs300, web, mobile, android, ios, architecture]
---

컴퓨터공학 300 주제 시리즈의 216번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

모바일 앱 아키텍처는 운영체제가 언제든 화면을 다시 만들고 프로세스를 죽일 수 있으며 네트워크는 수시로 끊긴다는 전제 위에서, UI 계층과 데이터 계층을 나누고, 로컬 저장소를 단일 진실 공급원으로 삼아 단방향으로 상태를 흘리는 구조다.

## 왜 필요한가

웹 서버 개발자가 처음 모바일 앱을 만들면 낯선 버그를 만난다.

- 화면을 가로로 돌렸더니 입력하던 내용과 불러온 목록이 사라졌다.
- 다른 앱을 잠깐 쓰고 돌아왔더니 앱이 처음 화면부터 다시 시작했다.
- 지하철에서 앱을 열었더니 빈 화면에 로딩 표시만 돈다.
- 서버 API 를 바꿨는데 업데이트하지 않은 몇 달 전 버전 사용자들이 오류를 낸다.

이것들은 버그라기보다 모바일 플랫폼의 기본 성질이다. 메모리가 제한된 기기에서 운영체제는 사용자가 보고 있지 않은 앱의 자원을 거리낌 없이 회수한다. 아키텍처는 이 성질을 견디도록 설계되어야 한다.

## 핵심 개념

### 생명주기: 화면과 프로세스는 내 것이 아니다

Android 의 Activity(화면 단위)는 운영체제가 상태를 바꿀 때마다 콜백을 받는다.

```
 onCreate → onStart → onResume  (사용자와 상호작용 중)
                         │
                      onPause   (일부 가려짐)
                         │
                      onStop    (보이지 않음) ──▶ onDestroy
                         │
       시스템이 메모리 부족 시 프로세스를 종료할 수 있음
```

중요한 사실 두 가지가 있다.

1. **구성 변경(configuration change)**: 화면 회전, 다크 모드 전환, 언어 변경 때 Android 는 기본적으로 Activity 를 파괴하고 다시 만든다. Activity 필드에 들고 있던 데이터는 사라진다.
2. **프로세스 종료**: 백그라운드에 있는 앱은 메모리 확보를 위해 프로세스째 종료될 수 있다. 사용자가 돌아오면 시스템은 마지막 화면을 복원하려 하지만, 메모리에 있던 객체는 전부 없다.

iOS 도 비슷하다. 앱은 활성(active), 비활성(inactive), 백그라운드, 일시 중지(suspended) 상태를 오가고, 일시 중지된 앱은 경고 없이 종료될 수 있다. Apple 문서는 앱이 백그라운드로 갈 때 상태를 저장하고 돌아올 때 복원하라고 안내한다.

그래서 상태를 수명에 따라 나눠 둔다.

| 상태 | 예 | 어디에 |
|---|---|---|
| 일시적 UI 상태 | 스크롤 위치, 펼침 여부 | 화면 객체 (없어져도 됨) |
| 화면 데이터 | 불러온 목록, 로딩 여부 | ViewModel (구성 변경을 견딤) |
| 복원용 작은 값 | 검색어, 선택한 탭, 항목 ID | 저장된 인스턴스 상태 (프로세스 종료를 견딤) |
| 영속 데이터 | 주문 목록, 초안 | 로컬 DB·파일 (앱 재시작을 견딤) |

Android 의 `ViewModel` 은 구성 변경 동안 살아남고, `SavedStateHandle` 은 프로세스 종료 후 복원에 쓰인다.

### 계층 구조

Android 공식 아키텍처 가이드는 다음 구조를 권한다.

```
 ┌─────────── UI 계층 ────────────┐
 │  화면(View/Compose, SwiftUI)    │  ◀── UiState 를 그리기만 한다
 │        ▲ 상태        │ 이벤트   │
 │  ViewModel (상태 보관·가공)     │
 └────────▲──────────────┼────────┘
          │              ▼
 ┌─────── 도메인 계층 (선택) ───────┐  여러 화면이 쓰는 비즈니스 로직
 └────────▲──────────────┼────────┘
          │              ▼
 ┌─────────── 데이터 계층 ─────────┐
 │  Repository                      │  ◀── 여러 데이터 소스를 숨기는 창구
 │   ├ 로컬 데이터 소스 (DB)          │
 │   └ 원격 데이터 소스 (API)        │
 └──────────────────────────────────┘
```

두 가지 원칙이 이 구조를 관통한다.

- **단방향 데이터 흐름(UDF)**: 상태는 아래에서 위로(데이터 → UI), 이벤트는 위에서 아래로(UI → 데이터) 흐른다. 화면은 상태를 직접 고치지 않고 이벤트만 보낸다. 207번 주제의 상태 관리 원칙과 같다.
- **단일 진실 공급원(SSOT)**: 각 데이터에는 주인이 하나 있다. 오프라인을 고려하면 그 주인은 대개 로컬 DB 다. 네트워크 응답은 화면으로 바로 가지 않고 로컬 DB 를 갱신하며, 화면은 언제나 로컬 DB 를 읽는다.

### 오프라인 우선

로컬 DB 를 진실 공급원으로 두면 다음이 자연스럽게 된다.

- 앱을 열면 지난번 데이터가 즉시 보인다. 새로 고침은 그 뒤에 조용히 일어난다.
- 네트워크가 끊겨도 읽기는 된다. 화면에는 "오프라인" 표시만 붙인다.
- 쓰기는 로컬에 먼저 기록하고 대기열에 넣어, 연결되면 서버와 동기화한다. 이때 충돌 해결 규칙(마지막 쓰기 우선, 서버 우선, 병합)을 미리 정해야 한다.

### 서버와의 계약: 옛 버전은 사라지지 않는다

웹은 배포하면 모든 사용자가 새 버전을 받지만, 모바일은 스토어 심사를 거치고, 사용자가 업데이트할 때까지 옛 버전이 계속 돈다. 그래서 다음이 필요하다.

- API 는 하위 호환을 유지한다. 필드는 추가만 하고, 지울 때는 오래 공지한다.
- 앱은 모르는 필드·열거값을 만나도 죽지 않게 만든다.
- 최소 지원 버전을 서버가 알려 주고, 그보다 낮으면 업데이트를 강제하는 장치를 처음부터 넣는다.
- 기능 플래그로 기능을 서버에서 켜고 끈다. 문제가 생긴 기능을 앱 업데이트 없이 끌 수 있다.

### 그 밖의 제약

배터리와 데이터 요금 때문에 백그라운드 작업은 운영체제가 강하게 제한한다. 주기 작업은 Android 의 WorkManager 같은 플랫폼 스케줄러에 맡기고, 서버가 알려야 할 일은 푸시 알림으로 깨운다. 권한(위치, 카메라, 알림)은 필요한 순간에 이유와 함께 요청한다.

## 직접 해 보기

Repository·ViewModel·UiState 구조를 파이썬으로 축소해 오프라인, 화면 회전, 프로세스 종료를 흉내 낸다.

```python
from dataclasses import dataclass, field

# ---- 데이터 계층: 로컬 DB 가 단일 진실 공급원, 네트워크는 그걸 갱신할 뿐
class Remote:
    online = True
    def fetch(self):
        if not self.online: raise ConnectionError("network down")
        return ["주문 #3", "주문 #2", "주문 #1"]

class Repository:
    def __init__(self, remote, local_db):
        self.remote, self.db = remote, local_db
    def orders(self):
        return list(self.db.get("orders", []))       # 화면은 항상 로컬에서 읽는다
    def refresh(self):
        self.db["orders"] = self.remote.fetch()       # 성공하면 로컬을 덮어쓴다

# ---- UI 계층: 불변 UiState 를 만들어 내보낸다 (단방향 데이터 흐름)
@dataclass(frozen=True)
class UiState:
    items: list = field(default_factory=list)
    offline: bool = False
    query: str = ""

class OrdersViewModel:
    def __init__(self, repo, saved_state):
        self.repo, self.saved = repo, saved_state      # saved_state: 프로세스 종료에도 남는 작은 값
        self.state = UiState(query=saved_state.get("query", ""))
    def on_event(self, event, arg=None):              # 화면 → 이벤트 → 상태
        offline = self.state.offline
        if event == "search":
            self.saved["query"] = arg
        if event in ("refresh", "search"):
            try:
                self.repo.refresh(); offline = False
            except ConnectionError:
                offline = True
        q = self.saved.get("query", "")
        items = [o for o in self.repo.orders() if q in o]
        self.state = UiState(items, offline, q)

def render(tag, vm):
    s = vm.state
    print(f"[{tag:14}] query={s.query!r:6} offline={s.offline!s:5} items={s.items}")

remote, disk, saved = Remote(), {}, {}
vm = OrdersViewModel(Repository(remote, disk), saved)
vm.on_event("refresh");          render("첫 실행", vm)
remote.online = False
vm.on_event("search", "#2");     render("지하철(오프라인)", vm)
same_vm = vm                     # 화면 회전: Activity 는 다시 만들어져도 ViewModel 은 유지
render("화면 회전", same_vm)
vm = OrdersViewModel(Repository(remote, disk), saved)   # 프로세스 종료 후 복귀
vm.on_event("load");             render("프로세스 복귀", vm)
```

실행 결과(한글 폭 때문에 정렬은 조금 어긋날 수 있다):

```
[첫 실행          ] query=''     offline=False items=['주문 #3', '주문 #2', '주문 #1']
[지하철(오프라인)     ] query='#2'   offline=True  items=['주문 #2']
[화면 회전         ] query='#2'   offline=True  items=['주문 #2']
[프로세스 복귀       ] query='#2'   offline=False items=['주문 #2']
```

볼 점은 이렇다.

- 오프라인에서 검색했지만 로컬 DB 에 지난 데이터가 있어 결과가 나왔고, 화면에는 오프라인 표시만 붙었다.
- 화면 회전에서는 같은 ViewModel 이 유지되어 상태가 그대로다.
- 프로세스가 죽고 ViewModel 이 새로 만들어져도, 작은 복원용 값(`saved` 의 검색어)과 로컬 DB(`disk`)가 남아 있어 사용자가 보던 화면을 되살렸다. 새 ViewModel 은 아직 네트워크를 시도하지 않았으므로 오프라인 표시는 꺼진 상태로 시작한다.

## 현업에서는

- **"회전하면 API 를 다시 불러요"**: 네트워크 호출을 Activity·Fragment 에서 직접 하면 회전마다 반복된다. ViewModel 로 옮기면 사라진다.
- **프로세스 종료 테스트**: Android 개발자 옵션의 "활동 유지 안 함"을 켜거나 `adb` 로 백그라운드 프로세스를 종료시켜 복원을 시험한다. 이 테스트를 하지 않은 앱은 실제 사용자 기기에서 빈 화면이나 크래시를 낸다.
- **API 버전 관리**: 백엔드 팀과 "앱 최소 지원 버전" 정책을 함께 정한다. 서버에 사용자 에이전트별 앱 버전 분포를 집계해 두면 옛 API 를 언제 내려도 되는지 판단할 수 있다.
- **홈랩 백엔드**: 개인 프로젝트 앱의 백엔드를 홈랩 k3s 에 두면 집 회선이나 노드가 내려갈 때가 생긴다. 오프라인 우선으로 만든 앱은 이런 순간에도 마지막 데이터를 보여 주고, 다시 연결되면 동기화한다.

## 확인 문제

1. Android 에서 화면 회전 시 Activity 필드의 데이터가 사라지는 이유는?
2. ViewModel 과 저장된 인스턴스 상태(SavedStateHandle)는 각각 어떤 상황을 견디는가.
3. 단방향 데이터 흐름에서 상태와 이벤트는 각각 어느 방향으로 흐르는가.
4. 오프라인 우선 앱에서 단일 진실 공급원을 로컬 DB 로 두는 이유는?
5. 모바일 앱이 쓰는 API 를 변경할 때 웹보다 신중해야 하는 이유는?

### 풀이

1. 회전은 구성 변경이고, Android 는 기본적으로 구성 변경 시 Activity 를 파괴하고 다시 만들기 때문이다.
2. ViewModel 은 구성 변경(회전 등)을 견디고, 저장된 인스턴스 상태는 시스템에 의한 프로세스 종료 후 복원까지 견딘다. 단 후자에는 작은 값만 넣는다.
3. 상태는 데이터 계층에서 UI 로, 이벤트는 UI 에서 ViewModel·데이터 계층으로 흐른다.
4. 네트워크 상태와 관계없이 화면이 항상 같은 곳을 읽게 되어, 오프라인에서도 동작하고 네트워크 응답과 화면이 어긋나지 않는다.
5. 사용자가 업데이트하지 않은 옛 버전 앱이 오랫동안 계속 API 를 호출하기 때문이다. 하위 호환을 유지하거나 최소 버전 강제 장치가 필요하다.

## 더 읽을거리 (References)

- Android Developers, *Guide to app architecture*: <https://developer.android.com/topic/architecture>
- Android Developers, *The activity lifecycle*: <https://developer.android.com/guide/components/activities/activity-lifecycle>
- Android Developers, *Build an offline-first app*: <https://developer.android.com/topic/architecture/data-layer/offline-first>
- Apple Developer, *Managing your app's life cycle*: <https://developer.apple.com/documentation/uikit/managing-your-app-s-life-cycle>
