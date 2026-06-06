---
layout: post
title: "내 K3s 클러스터 의 *거의 모든 부품* 이 Go 였다 — Go 가 *왜* Kubernetes 생태계를 정복했는가"
date: 2026-06-07 00:00:00 +0900
categories: [golang, kubernetes, sre]
tags: [go, k3s, etcd, containerd, runc, prometheus, helm, argocd, gc, goroutine, runtime]
---

> 어제 SSD 마이그레이션을 하다가, 문득 *내가 만진 모든 프로세스* 가 다 Go 였다.
> K3s, etcd, containerd, runc, kubelet, kube-apiserver, kube-proxy, Prometheus, Alertmanager, Grafana 의 백엔드, ArgoCD, Helm, cert-manager, kube-state-metrics. *전부* Go.
> *왜* 이 생태계는 *그렇게까지 Go 일색* 인가. 이 글은 그 *왜* 를 *언어 설계 / 컨테이너 친화 / 운영 친화* 의 세 축에서 풀어본다.

---

## TL;DR — *한 줄 결론*

> **"Go 의 *single static binary* + *goroutine 의 cheap concurrency* + *gofmt 가 정해주는 한 가지 스타일* 이 *컨테이너 오케스트레이션* 이라는 *동시 수만 connection / 멀티 OS 빌드 / 다중 팀 협업* 문제를 *가장 적게 고통* 으로 풀어줬다.** *Rust 가 그 자리에 못 간 이유* 와 *Java 가 잠시 도전하다 물러난 이유* 까지 같이 본다.

---

## 1. *내 클러스터 의 Go 인벤토리*

K3s 한 노드에 `ss -tlnp` + `ps fauxz` 만 돌려도 *얼마나* Go 가 깔려있는지 보인다 :

| 컴포넌트 | 역할 | Go? |
|---|---|---|
| **K3s** (`k3s server`/`agent`) | 단일 바이너리 안에 *control-plane + kubelet + containerd + flannel + traefik* 다 압축 | ✅ |
| **etcd** (embedded in K3s) | cluster state store, raft consensus | ✅ |
| **containerd** | OCI 런타임 (이미지/snapshot/exec) | ✅ |
| **runc** (또는 crun) | low-level container 실행 (`clone(2)` / cgroup / namespace) | ✅ runc Go, crun C |
| **kube-apiserver** | REST + admission + auth | ✅ |
| **kube-scheduler** | pod → node 매칭 | ✅ |
| **kube-controller-manager** | reconcile loops 30+ 종 | ✅ |
| **kubelet** | 노드 단위 pod 라이프사이클 | ✅ |
| **kube-proxy** | service ClusterIP → endpoint iptables/IPVS | ✅ |
| **CoreDNS** | cluster 내부 DNS | ✅ |
| **Flannel / Calico** | CNI 네트워크 | ✅ |
| **MetalLB / cilium / linkerd** | LB/Mesh | ✅ |
| **Prometheus** | 메트릭 수집 / 저장 | ✅ |
| **Alertmanager** | 알림 라우팅 / dedup | ✅ |
| **node-exporter** | 노드 메트릭 노출 | ✅ |
| **kube-state-metrics** | k8s 리소스 메트릭화 | ✅ |
| **Grafana** | UI 는 React, 백엔드 = Go | ✅ |
| **ArgoCD** | GitOps controller / API server | ✅ |
| **ArgoCD Image Updater** | 컨테이너 이미지 자동 sync | ✅ |
| **Helm** | 패키지 매니저 (`helm install`) | ✅ |
| **cert-manager** | TLS 인증서 자동화 | ✅ |
| **external-secrets** | 클라우드 secret 동기화 | ✅ |
| **MinIO** | S3 호환 object storage | ✅ |
| **Loki / Tempo / Mimir** | 로그 / trace / metric (Grafana 패밀리) | ✅ |
| **Vector / fluent-bit** | 로그 수집 | Vector ✅ (Rust), fluent-bit C |
| **Velero** | k8s 백업 | ✅ |
| **Trivy** | 컨테이너 보안 스캔 | ✅ |

대략 *내 노드 의 사용자 영역 RAM 의 60~70%* 가 Go 프로세스. *Java JVM 하나 도 없다* (애플리케이션 단 빼고).

> *내 K3s 클러스터 의 *운영 표면* 은 *사실상 Go 의 거대 생태계** 다.

---

## 2. *왜* Go 가 이 자리를 가져갔는가 — *3 축*

### 2.1 *축 1 : 배포 = "한 개 의 파일"*

컨테이너 이미지의 *기본 단위* 는 *static binary*. *바이너리 + libc* 만 있으면 어디서나 돈다. 그러려면 언어가 :

1. *외부 .so 의존성 없이* 컴파일
2. *cross-compile* (mac 에서 linux/arm64 빌드)
3. *binary size* 가 너무 크지 않을 것

Go 의 *기본* 이 정확히 이 셋.

```bash
# 5MB짜리 hello world 가 alpine 이미지로 16MB 컨테이너가 됨
$ go build -ldflags="-s -w" main.go
$ ls -la main
-rwxr-xr-x  1 me  staff  5_242_880  ...
$ docker build -f - . <<< "FROM scratch
COPY main /main
ENTRYPOINT [\"/main\"]"
```

*scratch* (빈 베이스) 위에 *Go 바이너리 한 개* 만 올려도 *진짜 동작* 하는 컨테이너. *Java 는 JRE 200MB+, Python 은 인터프리터 + 라이브러리 트리* 가 필요. *Rust 는 같음* (그래서 Rust 도 일부 도구는 이 자리에 들어옴 — 다음 절).

**컨테이너 친화는 Go 의 *기본값*. 다른 언어는 의식적으로 노력해야 비슷해진다.**

### 2.2 *축 2 : 동시성 = "수만 개 의 cheap goroutine"*

Kubernetes 의 *심장* 은 :

- **Watch** — 클라이언트가 *long-poll* 로 API 서버에 매달려서 변화를 받음. 수천 개 watch 가 동시에 떠 있다.
- **Reconcile loop** — 각 controller 가 *자기 리소스 종류* 마다 무한 루프.
- **Lease renewal** — kubelet, controller manager 등이 *주기적으로* etcd 에 lease 갱신.

각각이 *대기 시간이 길고 수가 많다*. OS thread 하나당 *1~2MB 스택* 을 잡으면 *thread 수천 개* 가 *기가바이트 RAM*. *Java 의 platform thread* 가 정확히 이 문제로 *reactive* 로 갔다 (참고 : *Virtual Threads 가 Java 21 에서 해결*. [Virtual Threads 글]({% post_url 2026-06-06-virtual-threads-vs-coroutines-junior-friendly %})).

Go 의 *goroutine* 은 *2KB 스택* 으로 시작 → 필요 시 확장. *1000 개 = 2MB*. *수만 개 동시 가능*. 그래서 :

```go
// kube-apiserver 의 단순화된 watch handler
func (s *server) Watch(req Request) {
    ch := make(chan Event, 100)
    go s.subscribe(req.Filter, ch)  // ← 새 goroutine
    for event := range ch {
        s.send(req.Conn, event)
    }
}
```

*100 만 갈래* 의 *기다림* 이 *수십 GB 가 아니라 수 GB* 안에서 처리됨. 이게 *제어 평면 의 cost* 를 *결정* 한다.

### 2.3 *축 3 : 협업 = "한 가지 스타일 만"*

Go 는 *언어 차원에서 *한 가지 포매팅** (`gofmt`), *한 가지 에러 모델* (`if err != nil`), *한 가지 의존성 도구* (`go mod`). *코드 리뷰* 에서 *세미콜론 어디 찍을지* 같은 *bike-shedding* 이 *불가능*.

이게 *분산팀 / OSS* 에서 *enormous productivity*. K8s 는 *2014 년 Google 에서 시작* 해서 *2024 년 기준 5000 명 contributor* — *스타일 통일* 없으면 코드 베이스 가 *지옥*.

> *gofmt, golangci-lint 가 매일 코드 베이스 의 *통일성* 을 유지*. Java 의 *Checkstyle / Spotless* 가 *플러그인 의 선택사항* 이라면, Go 의 `gofmt` 는 *언어 표준 의 도구*.

---

## 3. *반대 측 — Go 가 *덜 적합한* 자리*

Go 가 *정복* 했다고 *모든 자리* 가 Go 인 건 아니다.

### 3.1 *Rust 가 들어온 곳*

| 컴포넌트 | 왜 Rust? |
|---|---|
| **Vector** (로그 수집) | *throughput 이 극단적* + *GC pause 절대 비허용* |
| **firecracker** (microVM) | *security boundary* + *zero-copy* + *no GC* |
| **wasmtime** (WASM runtime) | *언어 안전성* + *임베디드* |
| **TiKV** (분산 KV) | etcd 보다 *큰 스케일* + *jitter 회피* |
| **bottlerocket** (OS) | *secure-by-default* OS |

공통점 : *GC pause* 가 *치명적* 이거나 *security boundary* 가 *언어 차원* 에서 필요한 곳. Go 의 *concurrent GC* 는 *2 ms 미만* 까지 줄였지만, *0 은 아니다*. Rust 는 *0*.

### 3.2 *C / C++ 가 남아있는 곳*

| 컴포넌트 | 왜 C? |
|---|---|
| **runc 의 syscall 부분** | `clone(2)`, `unshare(2)`, `setns(2)` 의 *thin wrapper* 가 필요 |
| **crun** | runc 의 *C 재구현* — *10 배 빠른 컨테이너 start* |
| **CRI-O** (containerd 대안) | kubelet 의 CRI 인터페이스 — 일부 hot path C |
| **fluent-bit** | *극단적 throughput* 의 로그 수집 |

*낮은 레이어 + 극단적 성능* 자리. Go 가 다 가져갈 순 없는 구간.

### 3.3 *그래서 Go 가 가져간 자리 의 정의*

> *Go 는 "L7 control-plane + middleware + tool" 의 자리* 를 가져갔다.
> *L4 이하 (네트워크 패킷 처리 / OS syscall hot loop / GC 가 죽이는 자리) 는 Rust/C 가 남았다*.

K3s 의 *대부분* 은 *L7 control-plane* 이라 Go. 그래서 *클러스터의 60~70%* 가 Go.

---

## 4. *Go runtime 이 cluster operability 에 *어떻게* 영향 미치나*

Go 가 *주류* 라 *Go 의 특성 이해 = 클러스터 운영 이해*. 세 가지 실전 포인트.

### 4.1 *GC pause — etcd 가 가장 예민*

Go 1.20+ 의 GC 는 *concurrent mark + concurrent sweep + 짧은 STW(Stop-The-World)*. STW 는 *마이크로~수 ms*. 보통은 무시 가능. *그러나 etcd* 같이 *fsync round 의 timing* 이 중요한 곳은 *수 ms STW 도 raft heartbeat 놓침*.

확인 :
```bash
# etcd 의 prometheus metric
go_gc_pause_seconds_count
go_gc_pause_seconds_sum
# 평균 STW
sum_over_time(go_gc_pause_seconds_sum[5m])
  / sum_over_time(go_gc_pause_seconds_count[5m])
```

*평균 1 ms* 면 OK. *10 ms* 가 자주 보이면 :
- `GOGC` 환경변수 조정 (`GOGC=50` 이면 *더 자주 GC* → *각 GC 가 짧음*)
- *메모리 부족* 의 신호 (allocation 폭주 → GC 가 자주 트리거)
- *goroutine leak* (오래된 goroutine 의 *루트* 가 *대량 메모리 stay alive*)

### 4.2 *Goroutine leak — 가장 흔한 메모리 누수*

Java 의 thread leak 은 *눈에 띈다* (스레드덤프 가 *수천 줄*). Go 의 goroutine leak 은 *조용하다*. 메트릭 :

```bash
go_goroutines  # 현재 goroutine 수
```

*kube-apiserver 의 정상치* 가 *수백* 인데 *수만* 이면 *클라이언트 가 watch 끊지 않고 떠난* 가능성.

진단 :
```bash
# 모든 Go 컴포넌트는 pprof 가 활성화돼있다
kubectl port-forward -n kube-system kube-apiserver-<node> 8080:6443
go tool pprof http://localhost:8080/debug/pprof/goroutine
# (pprof) top
# (pprof) list <func>
# 어디서 goroutine 이 *block 된 채로* 누적되는지 line:column 까지 보임
```

이 *진단 도구가 기본* 인 게 *Go ecosystem 의 큰 장점*. Java 는 *JFR + APM* 까지 필요한 정보가 *Go 는 한 줄 curl*.

### 4.3 *Memory ballast — large heap 용 옛 트릭*

Go 1.18 이전엔 *큰 heap* 워크로드에서 *small spike* 만으로 *GC 가 자주 트리거* 되는 문제. 우회로 *처음 부팅 시 fake allocation* 해서 baseline 을 올리는 *ballast* 패턴 :

```go
func main() {
    ballast := make([]byte, 10<<30) // 10GB
    _ = ballast
    // ... 실제 서버 시작
}
```

Go 1.19 에 `GOMEMLIMIT` 환경변수 도입 → *공식 해결*. 이제 :
```bash
GOMEMLIMIT=8GiB ./my-server
```
*heap 이 8GiB 가까이* 가면 *적극적 GC*, *그 미만* 이면 *느슨한 GC*. *etcd 의 권장 튜닝* 도 이걸 쓴다.

> 운영 팁 : *Go 컴포넌트 OOM 으로 죽으면* `GOMEMLIMIT` *없는지* *먼저* 확인. Pod limit 가 *heap + native + stack* 전체인데 `GOMEMLIMIT` 가 없으면 Go runtime 이 *limit 모르고 heap 부풀림* → OOM.

---

## 5. *클러스터 안의 *연쇄* — *한 Go 부품* 이 *다른 Go 부품* 에 어떻게 의존하나*

K3s 부팅 시퀀스를 *Go 의존성 그래프* 로 그려보면 :

```
                            ┌──────────────────────┐
                            │  K3s binary (Go)     │
                            │  단일 프로세스 (트리)    │
                            └──────┬───────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
            etcd (Go)        kubelet (Go)      kube-proxy (Go)
                                   │
                                   ▼
                          containerd (Go)
                                   │
                                   ▼
                            runc (Go)
                                   │
                                   ▼
                     [clone/unshare/cgroup syscall]
                          ↑ 이 아래만 C 영역
```

*모든 화살표 가 Go → Go*. 같은 *gRPC stub*, 같은 *protobuf*, 같은 *log format* (`klog`/`logr`). *언어 통일* 의 *직접적 이득* :

1. 같은 *error type* (`fmt.Errorf("...: %w", err)`) 으로 *원인 체인 전파*
2. 같은 *graceful shutdown* 패턴 (`context.Context` 의 cancel propagation)
3. 같은 *retry/backoff* 라이브러리 (`k8s.io/client-go/util/wait`)
4. 같은 *metrics endpoint* (`/metrics` 의 Prometheus 형식)

*하나 의 변경* 이 *전체 트리* 에 자연스럽게 *호환* 된다.

> *언어 통일* 의 *진짜 가치* 는 *코드 재사용* 이 아니라 *디버깅 모델 의 통일* 이다.
> apiserver 에서 *context deadline exceeded* 를 보면, containerd 에서도 같은 의미. runc 도 같은 의미. *코드만 안 봐도 패턴 추론* 가능.

---

## 6. *Go 가 *덜 좋은 부분* — 정직한 시각*

내가 Go 를 사랑한다고 단점이 없는 건 아니다.

### 6.1 *Generic 의 늦은 도입 (1.18, 2022)*

10 년 동안 *interface{}* 와 *code generation* 으로 견뎠다. K8s `client-go` 의 *수만 줄 boilerplate* 가 그 흔적. Java/C# 의 generic 이 *25 년 전 도입* 된 걸 생각하면 *늦었다*.

### 6.2 *Error handling 의 *지루함**

```go
result, err := step1()
if err != nil {
    return nil, fmt.Errorf("step1: %w", err)
}
result2, err := step2(result)
if err != nil {
    return nil, fmt.Errorf("step2: %w", err)
}
// ... 무한 반복
```

Rust 의 `?` 연산자 / Java 의 *checked exception* 비교 시 *코드 부피* 가 *1.5~2배*. 다만 *명시성* 이라는 *반대 가치* 가 있어 *호불호* 의 영역.

### 6.3 *Reflection 으로 표현되는 metadata*

K8s API 의 *struct tag* :
```go
type Pod struct {
    Spec PodSpec `json:"spec" yaml:"spec" protobuf:"bytes,1,opt,name=spec"`
}
```

*string 안에* metadata 가 들어가서 *컴파일 타임 검증* 이 안 된다. Rust 의 *derive macro* / Java 의 *annotation* 비교 시 *덜 견고*. *오타 한 글자* 가 *런타임 에러* 가 된다.

### 6.4 *Math / scientific computing*

Go 는 *비교적 약한 영역* — `math` 패키지 가 *기본 수준*, *SIMD intrinsics* 가 *제한적*. Python (NumPy/SciPy) / Rust (ndarray) / C++ (Eigen) 이 *훨씬 강함*.

다만 *클러스터 부품* 은 *scientific computing 거의 안 함* 이라 *문제 안 됨*.

---

## 7. *그래서 — *주니어가 알아야 할 한 줄**

> **Kubernetes 를 운영하는 *모두* 는 *Go 의 일부* 라도 *읽을 수 있어야* 한다.**

문제 진단 시 *최종 경로* 가 *Go 코드 의 한 줄* 이다. `kubectl describe pod` 의 *Events* 가 *기대와 다르면* → controller-manager 의 *해당 controller 의 Go 코드* 가 *진실*. K3s 의 *embedded etcd* 가 *이상한 로그* 를 찍으면 → etcd Go 코드 의 *trace level* 이 *답*.

*Java 만* 하는 개발자가 *Spring Boot 마이크로서비스* 를 K8s 에 올리면, *애플리케이션은 Java* 지만 *그 위의 모든 인프라는 Go*. *그 인프라 진단* 을 못 하면 *문제 의 절반 만 본다*.

```go
// 한 줄 만 익히자
if err != nil {
    return fmt.Errorf("context: %w", err)
}
```

*이 패턴 하나* 만 알아도 *K3s / etcd / containerd* 의 *에러 로그* 가 *읽힌다*.

---

## 8. *마무리*

내가 어제 디스크 마이그레이션 하면서 *멈추고 다시 켠 모든 프로세스* 가 Go 였다 — K3s, embedded etcd, embedded containerd, embedded runc. *동시에 죽은 알림* 을 띄운 Prometheus 도 Go, *재시작 자동화* 를 한 systemd unit 의 *내용* 도 Go 바이너리.

*Go 가 *왜* 이 자리를 가져갔나* 의 답은 *세 가지* :

1. **컨테이너 친화** — single static binary, cross-compile, scratch 베이스에 5MB
2. **동시성 친화** — goroutine 의 *2KB 스택* 으로 *수만 개 동시* watch / reconcile
3. **협업 친화** — gofmt, golangci-lint, go mod 의 *single way of doing things*

*Rust 가 점진적으로 잠식하는 자리* (Vector, firecracker, TiKV) 도 있고, *C 가 끝까지 남는 자리* (syscall, hot loop) 도 있다. 하지만 *L7 control-plane + middleware + tool* 의 *압도적 비중* 은 *앞으로도 Go*.

*K3s 클러스터 하나* 는 *Go 의 거대한 데모* 이자, *Go 가 *왜* 마지막 10 년 의 *infrastructure 언어** 가 됐는지의 *살아있는 증거*.

---

## 부록 — *바로 써먹는 Go pprof 스니펫*

### A. *어떤 Go 프로세스가 메모리 먹나*

```bash
ps aux | sort -k4 -nr | head -10
# RSS 큰 Go 프로세스 잡기
sudo lsof -p <PID> | grep -E "TCP|REG" | head
```

### B. *kubectl 로 pprof endpoint 접근*

```bash
kubectl port-forward -n kube-system pod/<pod> 8080:10256
# kube-proxy 같은 경우 10256 이 metrics+pprof
go tool pprof http://localhost:8080/debug/pprof/heap
go tool pprof http://localhost:8080/debug/pprof/goroutine
go tool pprof http://localhost:8080/debug/pprof/profile?seconds=30  # CPU
```

### C. *goroutine 수 추세*

Prometheus 쿼리 :
```promql
sum by (job) (go_goroutines)
# 갑자기 우상향 = leak 의심
```

### D. *GC pause 분포*

```promql
histogram_quantile(0.99,
  sum by (le, job) (
    rate(go_gc_pause_seconds_bucket[5m])
  )
)
```

p99 가 *10 ms 넘어가면* 적신호.

### E. *Memory limit / GOMEMLIMIT 매핑 확인*

```bash
kubectl get pod <pod> -o yaml | grep -A 3 limits
# Pod 의 memory limit
kubectl exec <pod> -- env | grep GOMEMLIMIT
# Go runtime 의 GOMEMLIMIT 설정 — 없으면 Pod limit 와 mismatch 위험
```

---

*다음 글 예고* — *Go 의 stretch goal* : 같은 도구 체인으로 *eBPF 를 짠다* (`cilium/ebpf` 라이브러리). *Go binary 가 *커널 안에서 도는* eBPF byte code 를 빌드/로드* 하는 *시대 의 의미*.
