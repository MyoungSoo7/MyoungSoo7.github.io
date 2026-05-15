---
layout: post
title: "Load 5.09 → 0.92, sed 한 줄로 — K3s coredns Addon 재적용 무한루프 잡기"
date: 2026-05-16 03:30:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k3s, coredns, addon, manifest, troubleshooting, postmortem]
---

5/15 밤, 텔레그램 서버모니터 봇이 르무엘(K3s 마스터 노드, 4코어/31GB) CPU 부하를 4번 연속 ⚠️로 표시했다. 첫 알람은 가볍게 봤는데 두 번, 세 번 계속 떴고, **간격이 점점 짧아지고 강도가 점점 세지는** 패턴이었다. 결국 마지막 알람은 *Load 5.09 / 4 cores (127%)*. 라이브로 잡고 들어가 보니 원인은 docker 런타임도, etcd compaction도 아닌 — **K3s Addon controller가 매니페스트 한 줄 때문에 15초마다 재적용을 시도하고 매번 실패하는 무한루프**였다.

> 이 글에서 다루는 것
> - K3s `/var/lib/rancher/k3s/server/manifests/` 의 작동 방식과 함정
> - `.skip` 파일이 *언제* 안 먹히는지 (Addon CRD 객체가 있을 때)
> - `Service "kube-dns" is invalid: spec.clusterIPs[0]: may not change once set` 의 의미
> - 라이브 부하 캡처 → 로그 정렬 → 매니페스트 비교 순서로 좁히기
> - sed 한 줄짜리 핫픽스가 가능했던 이유 + OS 재설치 없이 끝낸 결정

---

## TL;DR

| 항목 | 값 |
|---|---|
| 증상 | 5분~100분 간격으로 르무엘 Load 평균 3.5–5.1 스파이크, 시간 지날수록 빈도↑ |
| 진짜 원인 | K3s Addon controller가 `coredns.yaml` 매니페스트를 매번 재적용 시도, 매번 실패 |
| 실패 이유 | 매니페스트의 `clusterIP: 169.254.20.10` ≠ 운영중 Service의 `clusterIP: 10.43.0.10` |
| 추가 제약 | K8s 규칙상 `spec.clusterIPs[0]: may not change once set` → 영원히 거부 |
| 핫픽스 | 매니페스트 IP를 운영중 값으로 sed 치환 |
| 결과 | Load 5.09 → 0.92, dockerd CPU 33% → 0%, K3s 에러 로그 즉시 정지 |
| 소요 | 진단 30분, 핫픽스 1분 |

---

## 1. 증상 — "왜 점점 자주, 점점 심하게?"

서버모니터(`server-monitor` Go 데몬, 5분 watch 모드)에서 텔레그램으로 알람이 떴다:

```
22:40 ⚠️ Load 4.16
00:21 ⚠️ Load 3.72
01:03 ⚠️ Load 3.53
01:28 ⚠️ Load 5.09  ← 가장 심함
01:34 ⚠️ Load 3.90
```

간격: 101분 → 41분 → 26분 → **6분**. 강도도 누적되는 듯한 추세. 단순한 일회성 스파이크가 아니라는 신호다.

> 운영 직감: **간격이 짧아지는 패턴은 보통 "재시도 백오프가 풀린다"는 뜻**이다. 어딘가에서 실패한 작업이 계속 retry되고, retry 큐가 자랐다고 의심해야 한다.

---

## 2. 첫 가설 — docker daemon 오버헤드 (반은 맞고 반은 틀림)

르무엘만 클러스터에서 유일하게:

- K3s **v1.34** (나머지 노드 v1.35)
- **docker** 런타임 (나머지 containerd)
- Ubuntu **24.04** (나머지 26.04)

다른 노드는 v1.35 + containerd로 깔끔한데 르무엘만 docker shim 통한 컨테이너 관리라 오버헤드가 클 거라고 의심했다. 첫 번째 캡처에서:

```text
PID 2133    dockerd       33.3% CPU
PID 3777642 k3s-server    33.3% CPU
zombie 프로세스 18개
```

`dockerd`가 한 코어 통째로 먹고 있다. "역시 docker 런타임이 문제구나" — *반은 맞았다. 하지만 진짜 원인을 가린 좋은 미끼였다.*

이때 OS 재설치(Ubuntu 26.04 + containerd) 옵션도 검토 중이었는데, 다행히 `journalctl -u k3s` 먼저 봤다.

---

## 3. 라이브 캡처 — 스파이크와 정확히 일치하는 K3s 로그

스파이크 도중에 떠있는 동안 K3s 로그를 동시에 잡았다:

```
May 16 01:28:58 lemuel k3s[3777642]: Event ... reason="ApplyingManifest"
   message="Applying manifest at \"/var/lib/rancher/k3s/server/manifests/coredns.yaml\""
May 16 01:28:58 lemuel k3s[3777642]: Event ... reason="ApplyManifestFailed"
   message="failed: failed to update kube-system/kube-dns ... Service \"kube-dns\" is invalid:
            spec.clusterIPs[0]: Invalid value: [\"169.254.20.10\"]: may not change once set"
```

스파이크 시각 **01:28:55** ↔ 매니페스트 적용 실패 **01:28:58** — 3초 차이. 노이즈가 아니라 신호다.

```
May 16 02:34:50 ...  (15초 후 재시도)
May 16 02:35:05 ...
May 16 02:35:21 ...
May 16 02:35:37 ...
May 16 02:35:52 ...
```

K3s Addon controller가 **15초 주기로** 재적용을 시도하고 있다. 매번 같은 에러로 실패. 매번 dockerd/k3s-server가 일을 하느라 CPU를 쓴다.

> 진단 키워드: *스파이크 시점에 떠있는 동안 `top`과 `journalctl --since "30 seconds ago"` 를 같이 캡처하라.* 상관관계가 보이면 가설 좁히기가 빨라진다.

---

## 4. 진짜 원인 — manifest vs 운영중 Service의 clusterIP 충돌

에러 메시지 핵심 두 구절:

1. `Invalid value: ["169.254.20.10"]` — *매니페스트가 적용하려는 값*
2. `may not change once set` — *K8s가 거부하는 이유*

대조 확인:

```bash
# 현재 운영 중인 Service
$ kubectl get svc -n kube-system kube-dns -o yaml | grep clusterIP
clusterIP: 10.43.0.10
clusterIPs:
- 10.43.0.10

# 매니페스트가 적용하려는 값
$ sudo grep clusterIP /var/lib/rancher/k3s/server/manifests/coredns.yaml
clusterIP: 169.254.20.10
clusterIPs: [169.254.20.10]
```

**충돌이 명확하다.** K3s는 매번 `169.254.20.10`으로 바꾸려고 하고, 쿠버네티스는 *Service의 ClusterIP는 한번 설정되면 변경 불가*라는 불변 제약 때문에 거부한다.

추가로 `/etc/rancher/k3s/config.yaml`을 보면:

```yaml
cluster-dns: 169.254.20.10
kubelet-arg:
  - cluster-dns=169.254.20.10
```

설정 의도는 명확하다 — *node-local-dns* (각 노드에 DNS 캐시 daemon이 169.254.20.10에서 응답하게 하는 패턴). 하지만 운영중인 `kube-dns` Service는 그 의도가 적용되기 *전에* 이미 10.43.0.10으로 생성돼있었다. 새 IP로 바꿀 수 없는 상태로 굳어버린 것.

> 함정의 본질: **"의도된 미래 설정"이 "이미 굳어진 현재 상태"와 충돌할 때, K3s Addon은 무한히 그 차이를 메우려고 한다.**

---

## 5. 왜 `.skip` 파일이 안 먹혔나

K3s 공식 문서에는 `${manifest}.yaml.skip` 파일을 두면 해당 매니페스트 reconcile을 건너뛴다고 적혀있다. 첫 시도는 이거였다:

```bash
sudo touch /var/lib/rancher/k3s/server/manifests/coredns.yaml.skip
```

**효과 없었다.** 로그를 보면 그 후로도 15초마다 똑같은 에러가 찍힌다. 왜?

```bash
$ kubectl get addons -A
NAMESPACE     NAME      SOURCE                                                    CHECKSUM
kube-system   coredns   /var/lib/rancher/k3s/server/manifests/coredns.yaml        f3292b6e...
```

K3s는 `addons.k3s.cattle.io` 라는 CRD에 매니페스트 파일을 *등록*한다. 한번 등록된 Addon 객체는 *그 자체로* reconcile 루프에 들어가 있다. `.skip` 파일은 새 매니페스트가 추가될 때 등록을 *건너뛰는* 메커니즘이지, **이미 등록된 Addon 객체의 재적용을 멈추는 메커니즘이 아니다.**

> 정확한 동작: `.skip` = "이 파일을 새로 등록하지 마라"  
> 필요했던 것 = "이미 등록된 Addon 객체를 처리하지 마라" → 다른 방법 필요

---

## 6. 핫픽스 — sed 한 줄

선택지가 셋이었다:

1. **Addon CRD 객체를 삭제** — 그러면 K3s가 다시 만듦. 의미 없음.
2. **`/etc/rancher/k3s/config.yaml`의 `cluster-dns` 항목 제거** — 의도(node-local-dns)는 포기. K3s 재시작 필요.
3. **매니페스트의 clusterIP를 운영중 값으로 맞춤** — sed 한 줄, K3s 재시작 불필요, 다음 reconcile에서 성공하고 조용해짐.

3번 선택. 이유: K3s 재시작은 control-plane 노드 재기동이고 etcd 쿼럼에 영향을 준다. 핫픽스 단계에서는 가장 *작은 변경*이 원칙.

```bash
# 백업
sudo cp /var/lib/rancher/k3s/server/manifests/coredns.yaml \
        /var/lib/rancher/k3s/server/manifests/coredns.yaml.bak.$(date +%Y%m%d_%H%M%S)

# 매니페스트 IP를 운영중 값(10.43.0.10)으로 치환
sudo sed -i \
  "s|clusterIP: 169.254.20.10|clusterIP: 10.43.0.10|;\
   s|clusterIPs: \[169.254.20.10\]|clusterIPs: [10.43.0.10]|" \
  /var/lib/rancher/k3s/server/manifests/coredns.yaml

# .skip 제거 (어차피 효과 없었음)
sudo rm -f /var/lib/rancher/k3s/server/manifests/coredns.yaml.skip
```

> "운영중 값에 맞춘다"는 게 핵심이다. 매니페스트가 *현실*과 일치하면 K3s는 변경할 게 없다고 판단하고 조용히 reconcile을 성공시킨다.

---

## 7. 검증 — 즉시 회복

핫픽스 직후 라이브 캡처:

```text
$ uptime
02:36:58 up 31 days, 8:21, load average: 0.92, 1.42, 1.33
```

부하 추이 (직전 ↔ 직후):

| 시각 | Load (1분) | dockerd CPU | k3s 에러 메시지 |
|---|---|---|---|
| 01:28:55 (spike) | **5.09** | 33.3% | "Failed to process..." 15초마다 |
| 02:36:58 (fix 직후) | **0.92** | **0.0%** | (정지) |

K3s 로그에서 02:35:53 이후 `coredns` 관련 에러 0건. Reconcile이 *조용히* 성공하니까 로그조차 안 찍힌다.

→ 부하 81% 감소, OS 재설치 0%, K3s 재시작 0%.

---

## 8. 보너스 — 같은 밤의 다른 두 발견

같은 디버깅 세션에서 부수적으로 잡은 것들:

### 8.1 봇 토큰 평문 저장 → macOS Keychain 이관

서버모니터 `config.yml`에 텔레그램 봇 토큰이 평문으로 박혀있는 걸 발견했다. Git에 들어갈 일은 없는 로컬 설정이지만, 백업/공유 시점에 노출 위험이 있다. macOS 사용자라면 시스템 Keychain이 가장 자연스럽다:

```bash
# Keychain 저장
security add-generic-password -U \
  -s "server-monitor" -a "telegram-bot-token" -w "<TOKEN>"

# 조회 (테스트)
security find-generic-password -s "server-monitor" -a "telegram-bot-token" -w
```

Go 쪽 통합은 단순하다. config 로더가 `bot_token` 비었으면 env → Keychain 순으로 폴백:

```go
const (
    keychainService = "server-monitor"
    keychainAccount = "telegram-bot-token"
)

func loadTokenFromKeychain() (string, error) {
    out, err := exec.Command("security", "find-generic-password",
        "-s", keychainService, "-a", keychainAccount, "-w").Output()
    if err != nil {
        return "", err
    }
    return strings.TrimSpace(string(out)), nil
}

// config.Load 안에서
if cfg.Telegram.BotToken == "" {
    if env := strings.TrimSpace(os.Getenv("TELEGRAM_BOT_TOKEN")); env != "" {
        cfg.Telegram.BotToken = env
    } else if tok, err := loadTokenFromKeychain(); err == nil {
        cfg.Telegram.BotToken = tok
    }
}
```

`config.yml`은 `bot_token: ""` 로 비워둔다. 토큰을 바꾸려면 `security add-generic-password -U`로 덮어쓰면 끝.

### 8.2 컨테이너 카운트 0개? — docker vs containerd 런타임 차이

서버모니터의 watch 출력에서 일원/솔로몬/루이스가 `🐳 컨테이너: 0개`로 표시되는 게 이상했다. 실제로는 일원이 48 pods를 돌리는 가장 바쁜 노드인데 0이라니.

원인: 모니터 코드가 `docker stats`로 컨테이너를 세고 있었는데, 일원/솔로몬/루이스는 **containerd 런타임**을 쓴다. `docker` 명령은 그쪽에서 작동하지 않으니 0개로 잡힌다. 르무엘만 docker라서 16개로 잡혔다.

수정: 봇 호스트의 로컬 `kubectl`을 써서 노드별 K8s pod 카운트를 직접 조회. 30초 캐시 추가.

```go
func GetK8sPodCounts() map[string]int {
    if time.Since(podCountCachedAt) < podCountCacheTTL && podCountCache != nil {
        return podCountCache
    }
    counts := make(map[string]int)
    cmd := exec.Command("kubectl", "get", "pods", "--all-namespaces",
        "-o", "custom-columns=NODE:.spec.nodeName", "--no-headers")
    out, err := cmd.Output()
    if err != nil {
        return counts
    }
    for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
        node := strings.TrimSpace(line)
        if node != "" && node != "<none>" {
            counts[strings.ToLower(node)]++
        }
    }
    podCountCache = counts
    podCountCachedAt = time.Now()
    return counts
}
```

출력 포맷도 명시적으로 바꿨다:

```
📦 K8s pods: 48개 | 🐳 docker containers: 0개
```

이제 일원이 *실제로* 가장 일을 많이 한다는 사실이 메트릭에 드러난다. (직전엔 "0개"라 워크로드 분산이 잘못된 것처럼 보였다 — 잘못된 메트릭이 잘못된 의사결정을 부른다는 좋은 사례다.)

---

## 9. 운영 습관 — 이 incident에서 남겨둔 것들

> **A. "간격이 짧아지는 알람"은 retry backoff 풀린 신호로 의심하라.**  
> 일회성 스파이크는 무시할 수 있지만, 점점 잦아지는 알람은 *어딘가의 재시도가 누적되고 있다*는 뜻이다. 본 사례는 K3s Addon의 15초 retry가 매번 실패했고, 누적된 retry 비용이 도드라진 케이스.

> **B. 스파이크 도중 `top`과 `journalctl`을 동시에 잡아라.**  
> 사후 분석은 *상관관계*가 옅어진다. 살아있을 때 라이브로 잡으면 시각이 맞물려서 1차 가설이 빠르게 뜬다.

> **C. K3s의 `/var/lib/rancher/k3s/server/manifests/`는 Addon CRD로 등록되는 진입점이다.**  
> 파일을 옮기거나 `.skip`을 둬도 *이미 등록된 Addon 객체*는 계속 reconcile된다. 진짜로 멈추려면 Addon 객체를 들여다보거나, 매니페스트 내용을 운영중 상태와 정합시켜야 한다.

> **D. `Service`의 `clusterIP`는 *immutable* 이다.**  
> 한번 만들어지면 IP를 못 바꾼다. node-local-dns 같은 패턴을 사후에 적용하려면 Service 재생성이 필요하고, 이건 클러스터 DNS 다운타임을 동반한다. *처음 만들 때 결정*해두는 게 가장 싸다.

> **E. 메트릭이 0이면 "정말 0인지" 의심하라.**  
> Containerd 노드에서 `docker ps`는 정상적으로 0개를 반환한다. 0과 "측정 실패"를 구분하지 못하면 잘못된 그림을 그리게 된다. 런타임이 섞인 클러스터는 *통합 메트릭 소스*(kubelet/kubectl)를 쓰는 게 안전하다.

---

## 마무리

OS 재설치(르무엘을 Ubuntu 26.04 + containerd + K3s v1.35로 재구축)도 계획에 있었다. 하지만 진짜 원인은 매니페스트 한 줄이었고, sed 1줄로 끝났다. **"근본 해결"이라는 명분으로 큰 작업을 먼저 잡으면, 작은 진짜 원인을 영영 못 보게 되는 경우가 많다.** 이번에는 라이브 캡처 덕분에 그 함정에 안 빠졌다.

> **TL;DR** — 부하 스파이크가 점점 잦아지면 retry loop를 의심해라. K3s의 Addon controller는 `/var/lib/rancher/k3s/server/manifests/` 의 yaml을 15초마다 reconcile하고, `Service.clusterIP`가 immutable이라는 K8s 규칙을 만나면 매번 실패한 채로 자원을 태운다. 매니페스트를 *현재 운영중인 값*에 맞춰주면 즉시 조용해진다.
