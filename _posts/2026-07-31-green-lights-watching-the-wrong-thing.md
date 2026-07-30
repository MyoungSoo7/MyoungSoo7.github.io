---
layout: post
title: "정적 검증을 전부 통과했는데 런타임엔 네 군데가 틀렸다 — 초록불의 출처를 의심하라"
date: 2026-07-31 07:20:00 +0900
categories: [infra, kubernetes, observability]
tags:
  [
    k3s,
    prometheus,
    alerting,
    chroot,
    namespaces,
    configmap,
    self-healing,
    verification,
    homelab,
  ]
---

노드 자가치유 에이전트와 데이터 보호 서킷 브레이커를 하룻밤에 만들어 6노드 K3s 클러스터에 올렸다. 올리기 전에 검증을 꽤 했다고 생각했다 — 파이썬 829줄 문법 검사, PromQL 24개를 실제 Prometheus 에 던져 전부 `success` 확인, `kubectl apply --dry-run=server` 로 오브젝트 21개, LimitRange admission 까지.

전부 초록불이었다. 그리고 배포하고 로그를 읽었더니 **네 군데가 틀려 있었다.**

더 불편한 건 이거였다. 네 개가 전부 같은 병이었고, **그 병은 어떤 정적 검증으로도 잡히지 않는 종류**였다.

> ⚠️ 보안 — 내부 IP·토큰·엔드포인트는 모두 제외했다. 노드명과 패턴만 공유한다.

이 글은 [「Production agent 가 '끝났다' 고 말하기까지 — 내부 신호 vs 외부 검증 루프」](/2026/05/20/production-agent-goal-completed-external-verification/)(2026-05-20)의 후속이다. 그 글이 _"배포는 됐는데 사용자가 보는 게 다르다"_ 였다면, 이 글은 한 층 아래다 — **"검증 도구는 다 통과했는데, 코드가 애초에 엉뚱한 것을 보고 있었다."**

---

## TL;DR — 네 가지, 그리고 덤 하나

1~4번은 자가치유·서킷브레이커에서 나온 것이고, 5번은 같은 밤 다른 시스템(LLM 게이트웨이)에서 나왔다. 시스템은 달랐는데 병은 똑같았다.

| #   | 증상                                       | 진짜 원인                                             | 왜 안 잡혔나                                                         |
| --- | ------------------------------------------ | ----------------------------------------------------- | -------------------------------------------------------------------- |
| 1   | 6노드 전원이 "오버레이 네트워크 없음" 보고 | `chroot` 는 **네트워크 네임스페이스를 바꾸지 않는다** | 문법·스키마 모두 정상. 코드가 보는 _대상_ 이 틀렸을 뿐               |
| 2   | 디스크 알럿이 한 번도 안 울림              | 감시 대상이 **엉뚱한 디스크**(3.7TB)였다. 진짜는 984G | PromQL 은 정상 실행되고 값도 반환한다. 값이 _다른 디스크의 값_ 일 뿐 |
| 3   | 에이전트 전멸 시 알럿이 **침묵**           | `count(x) < 6` 은 `x` 가 사라지면 빈 벡터가 된다      | 평시엔 정확히 동작한다. 최악의 순간에만 조용해진다                   |
| 4   | 설정을 고쳤는데 동작이 그대로              | 프로세스가 **기동 시 한 번만** 설정을 읽는다          | 파일은 갱신됐고, 로그엔 오류가 없고, 메트릭도 값이 나온다            |
| 5   | 모델 목록에 있는데 호출하면 404            | `ListModels` 응답 ≠ 실제 호출 가능 목록               | 목록 조회는 200 이다. 실체는 호출해 봐야 안다                        |

관통하는 한 문장:

> **관측 대상이 틀리면, 모든 지표가 초록불이다.** 초록불은 "정상"의 증거가 아니라 "무언가를 관측했다"의 증거일 뿐이고, 그 무언가가 내가 의도한 대상인지는 별도로 증명해야 한다.

---

## 1. `chroot` 는 파일시스템 루트만 바꾼다 — 네트워크는 안 바꾼다

노드 자가치유 에이전트는 호스트의 `systemctl`·`ufw`·`crictl` 을 만져야 한다. kubelet 이 죽은 노드는 쿠버네티스 계층의 어떤 컨트롤러도 손대지 못하니, 호스트 네임스페이스에서 도는 무언가가 필요했다.

privileged DaemonSet 에 호스트 루트를 `hostPath` 로 붙이고 `chroot /host` 로 호스트 바이너리를 호출하는 방식을 썼다. 배포 전에 실제로 파드를 띄워 확인까지 했다 — `systemctl` 정상, `ufw` 조회 정상, `crictl ps` 로 컨테이너 40건 확인. 잘 되는 줄 알았다.

배포하니 **6노드 전원**이 이렇게 보고했다.

```
CHECK overlay = 이상 (flannel.1 없음)
CHECK wifi_link = 이상 (eth0:?)
CHECK apiserver_local = 이상 (fail)
```

파드끼리 통신은 멀쩡한데 오버레이 인터페이스가 없다니 말이 안 됐다. `chroot` 안에서 인터페이스를 직접 찍어 봤다.

```
lo
eth0@if716
default via 10.42.x.x dev eth0     # ← 파드 네트워크다
```

호스트에서 같은 명령을 치면 `flannel.1`, `bond0`, 무선 인터페이스가 다 보인다. 즉 **에이전트는 호스트가 아니라 자기 자신을 점검하고 있었다.**

원인은 `chroot(2)` 의 정의 그대로다. man page 는 이보다 더 분명할 수 없다.

> `chroot()` changes the root directory of the calling process to that specified in path. ... **This call changes an ingredient in the pathname resolution process and does nothing else.**
> — [chroot(2), Linux man-pages](https://man7.org/linux/man-pages/man2/chroot.2.html)

_and does nothing else._ 경로 해석만 바꾼다. 그리고 Linux 에서 네트워크는 **별도의 네임스페이스**다 — [namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html) 의 표를 보면 Mount 네임스페이스(`CLONE_NEWNS`, 마운트 포인트)와 Network 네임스페이스(`CLONE_NEWNET`, "Network devices, stacks, ports, etc.")는 완전히 다른 축이다.

파일시스템만 호스트 것으로 바꾸고 네트워크는 파드 것을 그대로 쓰는 상태 — 그게 내가 만든 것이었다.

**고친 방법**: DaemonSet 에 `hostNetwork: true` 추가. 호스트 네트워크 네임스페이스에 들어가야 `flannel.1` 이 보인다. `dnsPolicy: ClusterFirstWithHostNet` 을 같이 줘야 클러스터 DNS 로 API 서버를 계속 찾을 수 있다.

**왜 정적 검증이 못 잡았나**: 문법도 스키마도 완벽했다. `dry-run=server` 도 통과했다. 코드는 정확히 "네트워크 인터페이스를 조회하라"는 명령을 수행했다. 다만 _누구의_ 네트워크인지가 틀렸을 뿐이다. 그건 실행해서 결과를 눈으로 보기 전에는 알 수 없다.

### 곁가지 — 프로브가 `ok` 를 기대하면 안 되는 이유

같은 배치에서 API 서버 도달성 점검도 틀렸다. `/livez` 응답 본문에 `ok` 가 있는지 보게 짰는데, 익명 호출에는 **401** 이 돌아온다(실측). 살아 있는 API 서버를 죽었다고 판정하고 있었다.

도달성 점검의 목적은 인증 성공이 아니라 "서버가 응답하는가"다. HTTP 코드가 `000`(연결 실패)이 아니면 TCP·TLS·HTTP 계층이 살아 있다는 뜻이다. `curl -o /dev/null -w "%{http_code}"` 로 바꿨다.

---

## 2. 알럿이 엉뚱한 디스크를 감시하고 있었다

데이터베이스가 담긴 디스크가 차면 PostgreSQL 은 쓰기를 거부하고 멈춘다. 그래서 디스크 여유 알럿을 걸었다. PromQL 은 정상 실행됐고, 값도 반환했고, 임계에 걸리지 않아 조용했다. 완벽해 보였다.

문제는 `mountpoint=~"/var/lib/rancher.*"` 라는 매처였다. 그 노드에서 그 패턴에 걸리는 건 **로컬 스토리지 경로(여유 3.7TB)** 였다. 정작 데이터베이스가 얹힌 디스크는 별도 NVMe 마운트(984G)였다.

즉 **진짜 디스크가 100% 차도 이 알럿은 영원히 침묵한다.** 데이터 보호를 위해 만든 알럿이 데이터 보호에 실패하는, 조용한 false negative.

정적 검증이 이걸 놓친 이유는 잔인할 만큼 단순하다. PromQL 은 문법이 맞았고 실행도 됐고 **시계열도 1건 반환했다.** 반환된 값이 내가 지키려던 디스크의 값이 아니었을 뿐이다. 쿼리가 0건을 반환했다면 오히려 즉시 알아챘을 것이다. 1건이 나왔기 때문에 못 봤다.

**교훈**: 알럿을 만들 때 "쿼리가 도나?" 는 절반이다. 나머지 절반은 **"지금 반환된 이 숫자가, 내가 지키려는 바로 그 대상의 숫자가 맞나?"** 다. 나는 디스크 총량(984G vs 3.7TB)을 눈으로 대조하고 나서야 알았다.

---

## 3. 최악의 순간에만 조용해지는 알럿

6노드 DaemonSet 이니 에이전트는 항상 6개다. 하나라도 빠지면 그 노드는 무방비가 된다. 그래서 이렇게 썼다.

```promql
count(lemuel_selfheal_up) < 6
```

평시엔 정확히 동작한다. 5개가 되면 즉시 발화한다. 그런데 **6개가 전부 죽으면?**

`lemuel_selfheal_up` 시계열 자체가 사라진다. `count()` 는 빈 입력에 대해 빈 벡터를 반환하고, 빈 벡터에 `< 6` 을 비교하면 결과도 빈 벡터다. 발화 조건이 성립하지 않는다. **모든 에이전트가 죽은 바로 그 순간, 알럿은 완전히 침묵한다.**

Prometheus 는 이 상황을 위한 함수를 명시적으로 제공한다.

> `absent(v instant-vector)` returns an empty vector if the vector passed to it has any elements ... and a 1-element vector with the value 1 if the vector passed to it has no elements. **This is useful for alerting on when no time series exist for a given metric name and label combination.**
> — [Prometheus, Query functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)

```promql
absent(lemuel_selfheal_up) or count(lemuel_selfheal_up) < 6
```

이건 자가치유 에이전트만의 문제가 아니다. **"N개 중 M개 미만"을 세는 모든 알럿이 같은 구멍을 갖는다.** 대상이 부분적으로 죽으면 울리고, 전멸하면 침묵한다. 정확히 거꾸로다.

지속 시간까지 보려면 [`absent_over_time()`](https://prometheus.io/docs/prometheus/latest/querying/functions/) 이 더 낫다. 스크랩 한 번 걸렀다고 발화하는 걸 막아 준다.

---

## 4. 설정을 고쳤는데, 프로세스는 옛 설정으로 돌고 있었다

2번의 디스크 매처를 고쳐 ConfigMap 을 갱신하고 배포했다. 그리고 값을 확인했더니 — **여전히 옛 디스크의 숫자(94.46%)가 나왔다.**

파드에 들어가 마운트된 파일을 직접 열어 보니 내용은 분명히 새것이었다. 로그에도 오류가 없었다. 메트릭 엔드포인트도 정상 응답했다. `errors_total` 은 0이었다. 겉으로 드러나는 모든 신호가 정상이었다.

원인은 코드 한 줄이었다.

```python
def main():
    signals = json.load(open("/etc/breaker/signals.json"))   # 기동 시 딱 한 번
    while True:
        evaluate(signals)      # 영원히 옛 설정으로 평가한다
```

쿠버네티스 문서가 이 함정을 정확히 서술하고 있다.

> When you have a ConfigMap that is mapped into a running Pod ... and you update that ConfigMap, the running Pod sees the update almost immediately. **However, your application only sees the change if it is written to either poll for changes, or watch for file updates. An application that loads its configuration once at startup will not notice a change.**
> — [Kubernetes, Updating Configuration via a ConfigMap](https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/)

같은 문서군에는 함께 알아둘 제약이 더 있다. ConfigMap 을 **환경변수**로 주입한 경우엔 "not updated automatically and require a pod restart" 이고, **`subPath` 마운트**는 아예 갱신을 받지 못한다([ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/)).

내가 이 버그를 몇 시간이나 못 본 이유도 기록해 둘 만하다. **같은 배치의 DaemonSet 은 정상 반영됐기 때문이다.** 그쪽은 `hostNetwork: true` 를 추가하느라 파드 spec 이 바뀌어 롤아웃이 일어났고, 그래서 _우연히_ 새 설정을 읽었다. ConfigMap 만 바뀐 Deployment 는 롤아웃 트리거가 없어 그대로였다. 한쪽이 우연히 동작한 탓에 다른 쪽의 침묵이 묻혔다.

**고친 방법**: 매 사이클 설정을 다시 읽고, 파싱 실패 시 마지막 정상 설정을 유지한다. 깨진 편집이 프로세스를 죽이면 안 되니까.

```python
def load_config():
    try:
        _CFG["signals"] = json.load(open("/etc/breaker/signals.json"))
    except Exception as e:
        if _CFG["signals"] is None:
            raise                    # 최초 로드 실패는 기동 실패로
        log(f"재로드 실패(직전 설정 유지): {e}")
    return _CFG["signals"]
```

대안은 파드 템플릿에 설정 해시를 어노테이션으로 박아 ConfigMap 이 바뀌면 롤아웃이 자동으로 도는 방식이다. Helm 차트에서 흔히 쓰는 `checksum/config` 패턴. 둘 중 하나는 **반드시** 있어야 한다. 없으면 "고쳤다고 믿는데 안 고쳐진" 상태가 조용히 유지된다.

이 부류의 버그가 특히 나쁜 건 **증상이 없다**는 점이다. 크래시도, 에러 로그도, 메트릭 이상도 없다. 나중에 임계값을 조정하고 "왜 안 바뀌지?" 하며 몇 시간을 태우게 된다.

---

## 5. 목록에 있다고 쓸 수 있는 게 아니다

같은 밤에 LLM 게이트웨이도 하나 올렸다. 모델 목록을 등록하려고 프로바이더의 `ListModels` 를 호출해 실재하는 ID 만 골라 넣었다. 추측하지 않았으니 안전하다고 생각했다.

호출하니 404 가 났다.

```
This model models/<...> is no longer available to new users.
```

목록 조회에는 나오는데 실제 생성 호출은 거부되는 모델이 있었다. 결국 후보를 하나씩 실제로 호출해 보고, **응답이 돌아온 것만** 등록했다. 목록 API 는 "존재"를 말하지 "내가 쓸 수 있음"을 말하지 않는다.

덤으로 하나 더. 검증 스크립트에서 한 모델만 빈 응답을 냈길래 모델 문제인 줄 알았는데, **내 테스트가 틀린 것**이었다. `max_tokens: 16` 으로 호출했더니 추론(thinking) 토큰이 13개를 먹고 본문에 0개가 남았다. `finish_reason: length`, `content: null`.

```json
"completion_tokens_details": { "reasoning_tokens": 13, "text_tokens": 0 }
```

**검증이 실패했을 때 첫 번째 용의자는 검증 자신이다.** 토큰 예산을 늘리니 정상 응답했다.

---

## 관통하는 패턴 — 초록불의 출처

다섯 개를 늘어놓고 보니 공통 구조가 보인다. 전부 **"관측이 성공했다"와 "의도한 대상을 관측했다"를 혼동한 오류**다.

| 층위          | 초록불이 증명하는 것  | 초록불이 증명하지 **못** 하는 것      |
| ------------- | --------------------- | ------------------------------------- |
| 문법 검사     | 파싱된다              | 의도한 동작을 한다                    |
| 스키마 검증   | API 서버가 받아들인다 | 파드가 뜬다 (admission·리소스는 별개) |
| 쿼리 실행     | 시계열을 반환한다     | 그게 내가 지키려는 대상의 시계열이다  |
| 프로세스 기동 | 크래시하지 않는다     | 내가 방금 고친 설정으로 돌고 있다     |
| 목록 조회 200 | 그 항목이 존재한다    | 내가 그 항목을 실제로 쓸 수 있다      |

5월의 글에서 얻은 문장이 _"완료는 내부 신호로 판단할 수 없다"_ 였다면, 이번에 추가된 문장은 이거다.

> **초록불은 관측의 성공을 뜻할 뿐, 관측 대상의 정당성은 뜻하지 않는다.**

### 그래서 체크리스트에 넣은 것

이번 일 뒤로 배포 후 다음 다섯 개를 습관으로 만들었다. 전부 **5분 안에** 끝난다.

1. **로그를 읽는다.** 파드가 `Running` 인 것과 하는 일이 맞는 것은 다르다. 오늘 발견한 네 개 중 세 개가 첫 로그 사이클에 드러나 있었다.
2. **알럿이 보는 대상의 정체를 대조한다.** 쿼리가 도는지가 아니라, 반환된 숫자가 지키려는 그것인지. 총량·라벨을 눈으로 맞춰 본다.
3. **"전부 죽으면?" 을 대입한다.** 카운트 기반 알럿에는 `absent()` 를 함께 건다.
4. **설정 반영 경로를 확인한다.** 재로드하거나, 설정 해시로 롤아웃을 트리거하거나. 둘 다 없으면 그 설정은 장식이다.
5. **검증이 실패하면 검증을 먼저 의심한다.** 5번 항목의 빈 응답은 모델이 아니라 내 토큰 예산이 문제였다.

마지막으로, 이번 밤의 가장 정직한 수확은 이거다. **정적 검증을 아무리 겹겹이 쌓아도 "실제로 한 번 돌려서 결과를 눈으로 보는 것"을 대체하지 못한다.** 문법 검사 829줄, 쿼리 24개, dry-run 21개가 전부 통과한 코드가 네 군데 틀려 있었고, 그 넷은 배포 후 로그 한 화면에 다 드러나 있었다.

---

## 용어 사전

- **namespace (네임스페이스)** — 전역 자원을 프로세스 그룹별로 격리하는 리눅스 커널 기능. Mount·Network·PID·UTS 등 **종류마다 축이 다르다**. 하나를 바꿨다고 다른 게 따라오지 않는다. ([namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html))
- **`chroot`** — 호출 프로세스의 **경로 해석 기준 루트만** 바꾸는 시스템 콜. 격리 수단이 아니며 man page 스스로 "보안 목적으로 쓸 의도가 아니다"라고 못박는다.
- **`hostNetwork: true`** — 파드를 호스트의 네트워크 네임스페이스에서 실행. 호스트 인터페이스·포트가 그대로 보인다. 포트 충돌을 미리 확인해야 한다.
- **instant vector (인스턴트 벡터)** — PromQL 이 다루는 "지금 이 순간의 시계열 집합". **비어 있을 수 있고**, 빈 벡터에 대한 비교 연산 결과도 비어 있다. 3번 함정의 뿌리.
- **`absent()`** — 시계열이 **하나도 없을 때** 1을 반환하는 함수. "대상이 사라진 것" 자체를 알럿 조건으로 만들 수 있다.
- **false negative (거짓 음성)** — 문제가 있는데 없다고 판정하는 것. 모니터링에서 false positive(오탐)보다 훨씬 위험하다. 오탐은 시끄럽지만, 이건 조용하다.
- **admission (어드미션)** — API 서버가 오브젝트를 받아들이기 전 거치는 검사 단계. `LimitRange` 같은 정책은 **파드 생성 시점**에 적용되므로, Deployment 의 `dry-run` 통과가 파드 생성 성공을 보장하지 않는다.

---

## 참고 문헌

**1차 출처 (공식 문서·매뉴얼)**

- [chroot(2) — Linux manual page](https://man7.org/linux/man-pages/man2/chroot.2.html) — "changes an ingredient in the pathname resolution process and does nothing else"
- [namespaces(7) — Linux manual page](https://man7.org/linux/man-pages/man7/namespaces.7.html) — 네임스페이스 종류별 격리 대상 표
- [Prometheus — Query functions (`absent`, `absent_over_time`)](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [Kubernetes — Updating Configuration via a ConfigMap](https://kubernetes.io/docs/tutorials/configuration/updating-configuration-via-a-configmap/) — "An application that loads its configuration once at startup will not notice a change"
- [Kubernetes — ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/) — 환경변수 주입 시 미갱신, `subPath` 마운트 미갱신

**이 블로그의 선행 글**

- [Production agent 가 "끝났다" 고 말하기까지 — 내부 신호 vs 외부 검증 루프](/2026/05/20/production-agent-goal-completed-external-verification/) (2026-05-20) — 이 글의 직전 편
- [K3s flannel · ufw 8472 cross-node 함정](/2026/05/11/k3s-flannel-ufw-8472-cross-node-함정/) (2026-05-11) — 이번 자가치유 에이전트가 자동화한 바로 그 사고

**측정 환경 고지** — 본문의 수치(노드 6대, 파이썬 829줄, PromQL 24개, 오브젝트 21개, 디스크 984G/3.7TB, 추론 토큰 13개 등)는 2026-07-31 새벽 필자의 개인 K3s 홈랩에서 직접 관측한 값이다. 벤더 벤치마크나 제3자 재현이 아니며, 다른 환경에서 같은 수치가 나온다는 보장은 없다. 인용한 동작(‌`chroot` 의 네임스페이스 비변경, `absent()` 의 의미, ConfigMap 갱신 규칙)은 위 공식 문서에 근거한다.
