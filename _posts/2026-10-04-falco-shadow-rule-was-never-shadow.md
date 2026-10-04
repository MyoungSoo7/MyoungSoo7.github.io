---
layout: post
title: "섀도 룰이라더니 8일 동안 카드 78장 — BPFDoor 경보의 정체는 로그인 화면이 3시간마다 띄운 snap 이었다"
date: 2026-10-04 21:19:32 +0900
categories: [security]
tags: [falco, falcosidekick, bpf, bpfdoor, snapd, cgroup, watchman, alert-triage]
---

오늘 밤 9시, 텔레그램에 보안 카드가 한 장 왔다.

> 🔔 [BPF program loaded by unexpected process (BPFDoor pattern)] falco
> 분류: snap-confine 이 정당한 스냅 샌드박스 작업 중 BPF 프로그램을 로드한 것으로 보이며, 이는 BPFDoor 규칙에 대한 오탐이다 (신뢰도 높음)
> 🟡 판단 보류 — 사람 확인 필요 (판정 의심)
> ⚠ BPFDoor 계열 룰 — 실행 경로 /snap/snapd/28254/usr/lib/snapd/snap-confine 가 시스템 경로 밖. 모델은 '오탐' 이라 했지만 '의심' 으로 올림

AI 분석가 [파수꾼(watchman)](https://myoungsoo7.github.io/2026/09/24/watchman-same-false-positive-26-times/)은 "오탐" 이라고 판정했다. 그런데 결정론 규칙이 그 판정을 "의심" 으로 끌어올렸다. 이 카드를 보고 "누가 맞나" 를 따지기 전에 확인할 것이 하나 있었다.

**이 룰은 알림이 나가면 안 되는 룰이다.** 9월 27일 내가 넣은 *섀도 룰*이기 때문이다.

## 1. 섀도 룰이란

[Falco](https://falco.org/docs/) 는 노드의 시스템 호출을 보고 룰에 걸리면 이벤트를 낸다. 이 클러스터에서는 이벤트가 `falcosidekick → Alertmanager → 파수꾼 → 텔레그램` 으로 흐른다.

9월 27일, BPFDoor 계열 탐지를 보강하려고 룰 두 개를 추가했다.

- (a) `SO_ATTACH_BPF` — eBPF 소켓 필터를 소켓에 붙이는 순간
- (b) `bpf(BPF_PROG_LOAD)` — 커널에 BPF 프로그램을 올리는 순간

(b)는 정상 사용자가 많다. runc 는 컨테이너가 뜰 때마다 cgroup 장치 제어용 BPF 프로그램을 올리고, systemd 와 Falco 자신도 올린다. 그래서 바로 알림을 걸지 않고 **섀도 모드**로 시작했다. 우선순위를 `INFORMATIONAL` 로 두면 알림은 안 나가고 로그(Elasticsearch)에만 쌓인다. 7일 동안 무엇이 얼마나 걸리는지 센 다음 예외를 다듬고 `WARNING` 으로 올린다는 계획이었다. 오늘이 그 7일째다.

룰 파일 주석에는 이렇게 적었다.

```yaml
# 아래 두 룰은 INFORMATIONAL 로 시작한다. falcosidekick minimumpriority(notice)보다 낮아
# 알림(Alertmanager → watchman)은 안 나가고, falco stdout → fluent-bit → Logstash →
# logstash-k8s-* 에만 남는다
```

이 주석이 틀렸다.

## 2. 실측 — 섀도였던 적이 없다

파수꾼은 받은 경보를 전부 감사 로그(`audit.jsonl`)에 남긴다. 거기서 `priority: Informational` 인 경보를 셌다.

| 날짜 (UTC) | 9/26 | 9/27 | 9/28 | 9/29 | 9/30 | 10/1 | 10/2 | 10/3 | 10/4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Informational 경보 | 3 | 10 | 10 | 10 | 10 | 10 | 13 | 10 | 9 |

- **85건** 전부가 이번 섀도 룰 두 개에서 나왔다. 다른 Informational 룰은 없었다.
- 그중 **78건**이 텔레그램 카드로 나갔다. 7건은 같은 사건으로 묶여 억제됐다.
- 파수꾼이 이걸 조사하느라 LLM 을 **279번** 불렀다.

배포 첫날부터 하루 10건씩 알림이 나가고 있었다. "알림 없이 조용히 센다" 는 섀도 모드는 처음부터 작동하지 않았다.

## 3. 왜 새어 나갔나 — 없는 설정 키

Helm values 에는 분명히 이렇게 있다.

```yaml
falcosidekick:
  config:
    alertmanager:
      endpoint: /api/v2/alerts
      hostport: http://kps-alertmanager.monitoring:9093
    minimumpriority: notice
```

그런데 떠 있는 sidekick 의 설정(secret)을 열어 보면 값이 비어 있다.

```
ALERTMANAGER_MINIMUMPRIORITY ''
```

falcosidekick 2.32.0 소스를 받아서 확인했다.

- **전역 `minimumpriority` 라는 설정은 없다.** 우선순위 하한은 출력 대상마다 따로 있다(`alertmanager.minimumpriority`, `slack.minimumpriority` …). [config_example.yaml](https://github.com/falcosecurity/falcosidekick/blob/2.32.0/config_example.yaml) 에도 출력별로만 나온다. 그러니 `config.minimumpriority: notice` 는 어디서도 읽지 않는 키다. 에러도 나지 않는다.
- Alertmanager 로 보낼지는 [`handlers.go`](https://github.com/falcosecurity/falcosidekick/blob/2.32.0/handlers.go) 의 이 한 줄이 정한다.
  ```go
  falcopayload.Priority >= types.Priority(config.Alertmanager.MinimumPriority)
  ```
- 빈 문자열은 [`types/priority.go`](https://github.com/falcosecurity/falcosidekick/blob/2.32.0/types/priority.go) 에서 `Default` 로 바뀌고, `Default` 는 0 이다. `Debug` 가 1, `Informational` 이 2 다.

그래서 하한이 0 이 되고, **모든 우선순위가 통과한다.** 섀도 룰의 Informational 도 그대로 Alertmanager 로 갔다.

이 설정 키를 쓴 사람도, 그걸 근거로 "알림 안 나감" 이라는 주석을 쓴 사람도 나다. 배포 날 확인한 건 "ES 에 첫 문서가 들어오는가" 였다. "알림이 안 나가는가" 는 확인하지 않았다. 로그 쪽 경로만 보고 알림 쪽 경로는 안 본 것이다.

## 4. 그럼 그 경보는 뭐였나

85건을 노드와 실행 경로로 나누면 이렇다.

| 노드 | 실행 파일 | 건수 |
| --- | --- | --- |
| david | `/snap/snapd/<rev>/usr/lib/snapd/snap-confine` | **64** |
| 그 외 4대 | `snap-confine` (같은 경로 또는 `/usr/lib/snapd/`) | 8 |
| isagal | `/usr/bin/buildkit-runc` (CI 이미지 빌드) | 5 |
| lemuel | netdata `ebpf.plugin` | 4 |
| isagal | `systemd-networkd` | 2 |
| isagal | `python3` (배포 날 일부러 돌린 카나리) | 2 |

snap-confine 이 72건, 전체의 85% 다. 그중 64건이 david 한 대에서 나왔다.

### snap-confine 은 왜 BPF 를 올리나

snap-confine 은 snap 앱을 샌드박스에 넣고 실행하는 snapd 의 실행기다. cgroup v2 에서는 장치 접근 제어를 cgroup 설정 파일로 하지 않는다. `BPF_PROG_TYPE_CGROUP_DEVICE` 프로그램을 cgroup 에 붙여서 한다([커널 문서 — cgroup v2 Device controller](https://docs.kernel.org/admin-guide/cgroup-v2.html)).

snapd 2.77.1 소스가 정확히 그렇게 한다.

- [`device-cgroup-support.c`](https://github.com/canonical/snapd/blob/2.77.1/cmd/libsnap-confine-private/device-cgroup-support.c) 247행: `bpf_load_prog(BPF_PROG_TYPE_CGROUP_DEVICE, …)`
- 588행: `bpf_prog_attach(BPF_CGROUP_DEVICE, cgroup_fd, …)`
- 그 안에서 결국 `sys_bpf(BPF_PROG_LOAD, …)` 를 부른다([`bpf-support.c`](https://github.com/canonical/snapd/blob/2.77.1/cmd/libsnap-confine-private/bpf-support.c) 131행).

david 는 cgroup v2(`cgroup2fs`) 다. 그러니 snap 앱이 하나 뜰 때마다 BPF_PROG_LOAD 가 한 번씩 찍히는 게 정상이다.

경로가 `/usr/` 가 아니라 `/snap/snapd/28254/…` 인 이유도 있다. snapd 는 시스템 패키지보다 snapd snap 쪽이 새 버전이면 그쪽 바이너리로 다시 실행한다([`snapdtool/tool_linux.go`](https://github.com/canonical/snapd/blob/2.77.1/snapdtool/tool_linux.go) `ExecInSnapdOrCoreSnap`). 그래서 경로에 리비전 번호가 들어가고, snapd 가 갱신되면 숫자가 바뀐다. 감사 로그에도 27738 에서 28254 로 바뀐 게 그대로 보인다.

### 왜 3시간마다, 왜 david 인가

경보 시각은 UTC 00:00, 03:00, 06:00 … 정각에 몰려 있다. david 에서 원인을 찾았다.

```text
snap.firmware-updater.firmware-notifier.timer   (systemd 사용자 타이머)
OnCalendar = 매일 00, 03, 06, 09, 12, 15, 18, 21시
```

`firmware-updater` snap 의 알림 앱이 **사용자 타이머**로 3시간마다 뜬다. 경보에 찍힌 uid 60578 은 `gdm-greeter`, 곧 GNOME **로그인 화면**의 계정이었다. david 는 `graphical.target` 으로 부팅되고 GDM 이 떠 있다. 아무도 로그인하지 않은 로그인 화면의 사용자 세션이 3시간마다 펌웨어 알림 앱을 띄웠고, 그 앱을 샌드박스에 넣느라 snap-confine 이 BPF 프로그램을 올린 것이다.

정리하면 오늘 밤 카드는 이렇게 만들어졌다.

1. 서버 노드의 로그인 화면이 펌웨어 알림 snap 을 띄웠다.
2. 그 snap 을 샌드박스에 넣느라 snap-confine 이 BPF 프로그램을 올렸다.
3. 그게 BPFDoor 룰에 걸렸다.
4. 섀도여야 했던 룰이 설정 키 하나 때문에 알림으로 나갔다.

## 5. 모델과 규칙, 누가 맞았나

이번 경우 사실관계는 모델 쪽이 맞았다. snap-confine 의 BPF 로드는 정상 동작이다.

그래도 규칙이 판정을 "의심" 으로 끌어올린 건 잘못이 아니다. 그 하한은 일부러 만든 것이다.

- BPFDoor 는 정상 프로세스 이름으로 위장해서 돈다. Trend Micro 도 탐지할 때 *"should not rely on the process name"* 이라고 적는다([Trend Micro, 2023](https://www.trendmicro.com/en/research/23/g/detecting-bpfdoor-backdoor-variants-abusing-bpf-filters.html)).
- 그래서 우리 룰의 예외는 "이름 일치 **AND** 시스템 경로" 일 때만 적용된다. 경로가 시스템 경로 밖이면, 모델이 "이름을 보니 정상" 이라고 해도 그 말을 받지 않는다.
- 같은 이유로 이 계열은 이전 판정을 다시 쓰지 않는다. 그래서 3시간마다 새로 조사했고, 그게 LLM 279번이다.

문제는 하한 쪽이 아니었다. **사람이 보면 안 되는 경보가 사람에게 갔다**는 게 문제였다. 카드는 사고 번호와 대응 안내까지 붙어서 온다. 그런 무게의 오탐이 하루 10번 이런 무게로 오면, 진짜가 왔을 때 사람은 이미 무뎌져 있다. 이 시스템이 막으려는 게 바로 그 상태다.

하나 덧붙인다. 이 룰 (b)에 "BPFDoor pattern" 이라는 이름을 붙인 것도 정확하지 않았다. 지금까지 분석된 BPFDoor 리눅스 샘플은 `setsockopt(SO_ATTACH_FILTER)` 로 **고전 BPF(cBPF)** 필터를 붙인다([Trend Micro, 2023](https://www.trendmicro.com/en/research/23/g/detecting-bpfdoor-backdoor-variants-abusing-bpf-filters.html); [Elastic Security Labs, 2022](https://www.elastic.co/security-labs/a-peek-behind-the-bpfdoor)). 이 경로는 `bpf(BPF_PROG_LOAD)` 를 거치지 않는다. 그건 따로 있는 `SO_ATTACH_FILTER` 룰(WARNING)이 본다. (b)가 실제로 겨누는 건 eBPF 프로그램을 올리는 변종과 루트킷이다. 이름이 실제보다 무섭게 붙어 있으면 카드도 그만큼 무겁게 읽힌다.

## 6. 고칠 것 (아직 적용 안 함)

7일 측정은 의도와 다른 경로로나마 끝났다. 표본이 생각보다 깨끗하다. 85건 중 정체를 모르는 건 0건이다.

1. **sidekick 하한을 진짜 키에 쓴다.** `config.minimumpriority` 를 `config.alertmanager.minimumpriority: notice` 로 옮긴다. 그 전에 Informational 을 쓰는 다른 룰이 없는지 본다. 감사 로그 기준으로는 이 두 룰뿐이다.
2. **고친 다음 "안 나가는지" 를 직접 확인한다.** 이번 사고는 반대쪽 경로만 확인해서 생겼다. 섀도 룰 하나를 일부러 울리고, ES 에는 들어가지만 파수꾼 감사 로그에는 `alert_in` 이 안 생기는 것까지 봐야 한다.
3. **snap-confine 예외는 경로째로 좁게 준다.** `/snap/snapd/<rev>/` 는 읽기 전용 squashfs 마운트다(david 실측: `squashfs ro`). 그래서 이름 AND `/snap/snapd/*/usr/lib/snapd/snap-confine` 또는 `/usr/lib/snapd/snap-confine` 일 때만 뺀다. 한계도 적어 둔다. root 를 가진 공격자는 그 경로에 다른 이미지를 마운트할 수 있다. 하지만 그건 `/usr` 예외도 똑같이 가진 한계다.
4. **근본적으로는 서버에 로그인 화면이 필요한지 묻는다.** 이건 오너가 정할 일이다.

나머지 예외(buildkit-runc 와 `systemd-network` 는 15자로 잘린 comm 이름)도 같은 "이름 AND 경로" 방식으로 처리한 다음 WARNING 으로 승격한다.

## 마무리

- "섀도 모드" 는 8일 동안 한 번도 섀도가 아니었다. 읽지 않는 설정 키(`config.minimumpriority`) 하나 때문에 Informational 경보 85건이 그대로 Alertmanager 로 갔고, 카드 78장이 나갔다.
- 원인은 falcosidekick 이 하한을 **출력별로만** 받고, 빈 값을 0(전부 통과)으로 읽는 데 있다. 에러는 나지 않는다.
- 오늘 밤 BPFDoor 경보의 정체는 david 의 로그인 화면이 3시간마다 띄운 펌웨어 알림 snap 이었다. snap-confine 이 cgroup v2 장치 제어용 BPF 프로그램을 올린 것이다.
- 모델의 판정은 맞았고, 규칙이 그걸 "의심" 으로 끌어올린 것도 설계대로였다. 틀린 건 그 경보가 사람에게 갔다는 것이다.
- 교훈: 섀도 모드를 검증할 때는 **들어가야 할 곳에 들어갔는지**와 **나가면 안 되는 곳으로 안 나갔는지**를 둘 다 본다.

## References

1. falcosecurity, *falcosidekick 2.32.0 — `handlers.go`* (Alertmanager 전송 조건). <https://github.com/falcosecurity/falcosidekick/blob/2.32.0/handlers.go>
2. falcosecurity, *falcosidekick 2.32.0 — `types/priority.go`* (빈 문자열 → `Default`=0). <https://github.com/falcosecurity/falcosidekick/blob/2.32.0/types/priority.go>
3. falcosecurity, *falcosidekick 2.32.0 — `config_example.yaml`* (출력별 `minimumpriority`). <https://github.com/falcosecurity/falcosidekick/blob/2.32.0/config_example.yaml>
4. Canonical, *snapd 2.77.1 — `cmd/libsnap-confine-private/device-cgroup-support.c`, `bpf-support.c`*. <https://github.com/canonical/snapd/tree/2.77.1/cmd/libsnap-confine-private>
5. Canonical, *snapd 2.77.1 — `snapdtool/tool_linux.go`* (snapd snap 으로 재실행). <https://github.com/canonical/snapd/blob/2.77.1/snapdtool/tool_linux.go>
6. The Linux Kernel documentation, *Control Group v2 — Device controller* (`BPF_PROG_TYPE_CGROUP_DEVICE`). <https://docs.kernel.org/admin-guide/cgroup-v2.html>
7. Trend Micro, *Detecting BPFDoor Backdoor Variants Abusing BPF Filters* (2023-07). <https://www.trendmicro.com/en/research/23/g/detecting-bpfdoor-backdoor-variants-abusing-bpf-filters.html>
8. Elastic Security Labs, *A peek behind the BPFDoor* (2022-07). <https://www.elastic.co/security-labs/a-peek-behind-the-bpfdoor>
9. 실측 데이터: 2026-10-04, 파수꾼 감사 로그(`audit.jsonl`, 2026-09-26 ~ 10-04 의 Informational `alert_in` 85건), 떠 있는 falcosidekick secret, helm-deploy `argocd-applications/falco.yaml`, david 노드의 systemd 타이머·`findmnt`·`getent passwd`. IP·계정·내부 주소는 싣지 않았다.
