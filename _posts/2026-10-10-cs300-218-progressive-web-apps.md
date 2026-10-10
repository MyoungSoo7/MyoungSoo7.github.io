---
layout: post
title: "[CS300 #218] PWA — 설치되고 오프라인에서도 열리는 웹 앱"
date: 2026-10-10 21:38:00 +0900
categories: [cs]
tags: [cs300, web, pwa, service-worker, offline]
---

컴퓨터공학 300 주제 시리즈의 218번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

PWA(Progressive Web App)는 웹 앱 매니페스트로 "설치 가능한 앱"의 정보를 선언하고, 서비스 워커로 네트워크 요청을 가로채 캐시·오프라인·백그라운드 기능을 더해, 일반 웹 페이지를 앱처럼 동작하게 만드는 방식이다.

## 왜 필요한가

웹은 배포가 쉽다. 스토어 심사도, 사용자 업데이트도 필요 없이 서버에 올리면 모두가 새 버전을 본다. 반면 앱에 비해 약점이 있었다.

- 네트워크가 끊기면 "연결 없음" 공룡 화면만 남는다.
- 홈 화면 아이콘이 없어 다시 찾아오기 번거롭다.
- 주소창과 탭 때문에 앱 같은 몰입감이 없다.
- 반복 방문해도 자원을 다시 받는 경우가 많다.

PWA 는 이 약점을 웹 표준으로 메운다. 별도 네이티브 앱을 만들 만큼은 아니지만 자주 쓰는 도구, 회선이 불안정한 환경의 업무 앱, 콘텐츠 사이트에서 특히 쓸모가 있다.

## 핵심 개념

### 구성 요소 세 가지

| 요소 | 역할 |
|---|---|
| HTTPS | 서비스 워커는 보안 컨텍스트(HTTPS, 개발용 localhost)에서만 동작한다 |
| 웹 앱 매니페스트 | 이름, 아이콘, 시작 주소, 표시 모드 등 설치 정보 |
| 서비스 워커 | 페이지와 네트워크 사이의 프로그래밍 가능한 프록시 |

### 매니페스트

```json
{
  "name": "홈랩 상태판",
  "short_name": "상태판",
  "start_url": "/?source=pwa",
  "scope": "/",
  "display": "standalone",
  "theme_color": "#1E3A5F",
  "background_color": "#FFFFFF",
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

```html
<link rel="manifest" href="/manifest.webmanifest">
```

`display: standalone` 이면 설치 후 주소창 없이 독립된 창으로 열린다. 설치를 제안하는 조건과 UI 는 브라우저마다 다르므로, 특정 브라우저의 설치 버튼 동작에 기능을 의존하지 않는다.

### 서비스 워커의 생명주기

서비스 워커는 페이지와 별도의 스레드에서 도는 자바스크립트이고, DOM 에 접근하지 못한다. 등록된 범위(scope) 안의 모든 요청이 서비스 워커의 `fetch` 이벤트를 거친다.

```
 navigator.serviceWorker.register("/sw.js")
        │
   install   ← 오프라인에 필요한 핵심 자원을 미리 캐시
        │
   waiting   ← 옛 서비스 워커가 제어하는 탭이 남아 있으면 대기
        │
   activate  ← 옛 캐시 정리
        │
   fetch 이벤트를 받아 요청마다 응답을 결정
```

`waiting` 단계가 중요하다. 새 버전 서비스 워커는 옛 버전이 제어 중인 페이지가 모두 닫힐 때까지 활성화되지 않는다. 한 페이지 안에서 옛 코드와 새 코드가 섞이는 것을 막기 위한 설계다. 그래서 "배포했는데 사용자는 옛 화면을 본다"는 PWA 의 단골 문제가 생긴다. `skipWaiting()` 과 `clients.claim()` 으로 즉시 교체할 수 있지만, 이미 열린 페이지와 새 캐시가 맞지 않을 위험을 감수해야 한다. 보통은 "새 버전이 있습니다, 새로 고침" 안내를 띄운다.

### 최소 서비스 워커

```js
const CACHE = "static-v3";
const CORE = ["/", "/app.css", "/app.js", "/offline.html"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    // 페이지 이동: 네트워크 우선, 실패하면 오프라인 페이지
    event.respondWith(fetch(event.request).catch(() => caches.match("/offline.html")));
    return;
  }
  // 정적 자원: 캐시 우선
  event.respondWith(
    caches.match(event.request).then((hit) => hit || fetch(event.request))
  );
});
```

### 캐시 전략

| 전략 | 동작 | 맞는 자원 |
|---|---|---|
| 캐시 우선 | 캐시에 있으면 그것, 없으면 네트워크 | 해시 붙은 JS·CSS, 폰트, 아이콘 |
| 네트워크 우선 | 네트워크 시도, 실패하면 캐시 | HTML, 자주 바뀌는 API |
| stale-while-revalidate | 캐시로 즉시 응답하고 뒤에서 갱신 | 조금 낡아도 되는 목록, 아바타 |
| 네트워크만 | 캐시 안 함 | 결제, 로그인 등 민감한 요청 |

HTTP 캐시(213번 주제)와 서비스 워커 캐시는 별개다. 서비스 워커는 요청이 HTTP 캐시에 닿기 전에 먼저 가로채므로, 둘의 규칙이 겹치면 디버깅이 어려워진다. 캐시 이름에 버전을 붙이고 `activate` 에서 옛 캐시를 지우는 습관이 중요하다.

### 그 밖의 기능과 한계

푸시 알림(Push API), 백그라운드 동기화, 공유 대상 등록 같은 기능도 서비스 워커 위에서 동작한다. 다만 지원 범위가 브라우저·운영체제마다 다르므로 기능 감지(`'serviceWorker' in navigator`)를 하고, 없으면 일반 웹 페이지로 동작하게 만든다. 이름의 "Progressive"가 바로 이 점진적 향상을 뜻한다.

## 직접 해 보기

세 가지 캐시 전략이 "첫 방문 → 재방문 → 서버 배포 → 다시 방문 → 오프라인" 시나리오에서 어떻게 다르게 응답하는지 파이썬으로 흉내 낸다.

```python
class Network:
    def __init__(self): self.online, self.version, self.calls = True, 1, 0
    def fetch(self, url):
        self.calls += 1
        if not self.online: raise ConnectionError
        return f"{url}@v{self.version}"

def cache_first(url, cache, net):
    if url in cache: return cache[url], "cache"
    cache[url] = net.fetch(url); return cache[url], "network"

def network_first(url, cache, net):
    try:
        cache[url] = net.fetch(url); return cache[url], "network"
    except ConnectionError:
        return (cache[url], "cache(오프라인 대체)") if url in cache else ("오프라인 페이지", "fallback")

def stale_while_revalidate(url, cache, net):
    cached = cache.get(url)
    try:
        cache[url] = net.fetch(url)          # 실제로는 응답을 준 뒤 백그라운드에서 갱신
    except ConnectionError:
        pass
    return (cached, "cache(갱신은 다음 번에 반영)") if cached else (cache.get(url, "오프라인 페이지"), "network")

scenario = [("첫 방문", True, 1), ("재방문", True, 1), ("서버 배포 v2", True, 2),
            ("다시 방문", True, 2), ("오프라인", False, 2)]
for strategy in (cache_first, network_first, stale_while_revalidate):
    net, cache = Network(), {}
    print(f"== {strategy.__name__}")
    for label, online, ver in scenario:
        net.online, net.version = online, ver
        body, src = strategy("/news", cache, net)
        print(f"  {label:10} -> {body:12} ({src})")
```

실행 결과:

```
== cache_first
  첫 방문       -> /news@v1     (network)
  재방문        -> /news@v1     (cache)
  서버 배포 v2   -> /news@v1     (cache)
  다시 방문      -> /news@v1     (cache)
  오프라인       -> /news@v1     (cache)
== network_first
  첫 방문       -> /news@v1     (network)
  재방문        -> /news@v1     (network)
  서버 배포 v2   -> /news@v2     (network)
  다시 방문      -> /news@v2     (network)
  오프라인       -> /news@v2     (cache(오프라인 대체))
== stale_while_revalidate
  첫 방문       -> /news@v1     (network)
  재방문        -> /news@v1     (cache(갱신은 다음 번에 반영))
  서버 배포 v2   -> /news@v1     (cache(갱신은 다음 번에 반영))
  다시 방문      -> /news@v2     (cache(갱신은 다음 번에 반영))
  오프라인       -> /news@v2     (cache(갱신은 다음 번에 반영))
```

- **캐시 우선**은 가장 빠르지만 서버가 v2 를 배포해도 영원히 v1 을 준다. 그래서 내용이 바뀌면 이름도 바뀌는(해시) 파일에만 쓴다.
- **네트워크 우선**은 항상 최신이지만 매번 네트워크를 기다린다. 오프라인에서는 마지막으로 받은 v2 로 버틴다.
- **stale-while-revalidate**는 즉시 캐시로 응답하고 뒤에서 갱신하므로, 새 버전이 "한 번 늦게" 보인다. 오프라인일 때는 갱신만 실패하고 이미 캐시에 있던 v2 로 응답한다.

브라우저에서는 개발자 도구 Application 패널에서 서비스 워커 상태(installed, waiting, activated)와 Cache Storage 내용을 직접 볼 수 있고, Network 패널의 Offline 체크로 오프라인을 시험한다.

## 현업에서는

- **"배포했는데 안 바뀌어요"**: 서비스 워커가 `index.html` 을 캐시 우선으로 주고 있거나, 새 워커가 waiting 에 머물러 있는 경우가 대부분이다. HTML 은 네트워크 우선으로 두고, `sw.js` 파일 자체는 HTTP 캐시를 짧게 둔다.
- **서비스 워커 제거 계획**: 잘못된 서비스 워커는 사용자 브라우저에 남아 계속 옛 화면을 준다. 제거할 때도 "자기 자신을 등록 해제하는 워커"를 같은 경로에 배포해야 한다. 처음 도입할 때부터 빠져나갈 길을 생각해 둔다.
- **내부 도구에 잘 맞는다**: 홈랩 k3s 의 상태판이나 메모 도구를 PWA 로 만들어 두면 휴대폰 홈 화면에서 앱처럼 열리고, 집 밖에서 VPN 이 끊겨도 마지막으로 본 상태가 남는다. 다만 서비스 워커는 HTTPS 가 필요하므로 내부망에서도 인증서를 갖춰야 한다.
- **민감한 데이터 캐시 금지**: 공용 PC 에서 로그아웃한 뒤에도 Cache Storage 에 개인 정보 응답이 남을 수 있다. 인증이 필요한 API 응답은 캐시하지 않거나 로그아웃 때 지운다.

## 확인 문제

1. PWA 를 이루는 세 가지 요소를 쓰라.
2. 새 서비스 워커가 설치된 뒤 바로 활성화되지 않고 waiting 상태에 머무는 이유는?
3. 해시가 붙은 JS 파일과 HTML 문서에 각각 어울리는 캐시 전략은?
4. stale-while-revalidate 에서 새 버전이 "한 번 늦게" 보이는 이유는?
5. 서비스 워커를 HTTP 페이지에서 등록할 수 없는 이유를 보안 관점에서 설명하라.

### 풀이

1. HTTPS(보안 컨텍스트), 웹 앱 매니페스트, 서비스 워커.
2. 옛 서비스 워커가 제어하는 페이지가 열려 있는 동안 교체하면 한 페이지 안에서 옛 코드·캐시와 새 코드가 섞일 수 있어서, 옛 페이지가 모두 닫힐 때까지 기다린다.
3. 해시 JS 는 캐시 우선, HTML 은 네트워크 우선.
4. 요청 시점에는 캐시된 옛 응답을 즉시 돌려주고, 새 응답은 백그라운드에서 받아 캐시만 갱신하므로 다음 요청에서야 쓰인다.
5. 서비스 워커는 범위 안의 모든 요청을 가로채고 응답을 바꿀 수 있는 강력한 권한을 가진다. 평문 HTTP 에서 등록을 허용하면 중간자가 악성 워커를 심어 이후 방문까지 장악할 수 있기 때문이다.

## 더 읽을거리 (References)

- W3C, *Service Workers*: <https://www.w3.org/TR/service-workers/>
- W3C, *Web Application Manifest*: <https://www.w3.org/TR/appmanifest/>
- MDN, *Using Service Workers*: <https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers>
- web.dev, *Learn PWA*: <https://web.dev/learn/pwa>
