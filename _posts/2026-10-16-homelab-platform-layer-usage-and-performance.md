---
layout: post
title: "앱 밑에 깔린 19개 — 홈랩 K3s 운영 기반의 사용법과 실측 성능"
date: 2026-10-16 00:31:08 +0900
categories: [kubernetes, operations]
tags: [k3s, argocd, cloudflared, sops, velero, prometheus, elasticsearch, falco, kafka, strimzi, buildkit, arc, homelab]
---

우리 K3s 클러스터(노드 5대)에는 사람이 직접 쓰는 앱 말고도 앱을 *돌리기 위한* 네임스페이스가 19개 있다.
배포(ArgoCD), 외부 연결(cloudflared), 시크릿(sops-operator), 백업(velero), 빌드(buildkitd·ARC·registry-mirror),
관측(Prometheus·ELK·Falco)과 그 밖의 공용 부품(Kafka·OpenViking·NFS·Dashboard·echo)이다.

이 글은 각각을 **어떻게 쓰는지**와 **지금 실제로 어떤 성능·비용을 내는지**를 정리한다.
수치는 모두 2026-10-16 00:10~00:27 KST 에 클러스터에서 직접 잰 값이다. 바로 전날 isagal 노드를 퇴역시킨 직후의 상태다
([isagal 퇴역 글]({% post_url 2026-10-15-isagal-retirement-cluster-6-to-5-power-savings %})).

먼저 결론 세 가지.

1. **운영 기반이 클러스터 메모리의 3분의 1을 쓴다.** 그 가운데 절반 이상이 로깅(ELK) 하나다.
2. **잘 돌던 것 2개는 사실 일을 안 하고 있었다.** registry-mirror 는 141일째 떠 있는데 어느 노드도 그걸 미러로 쓰지 않는다. velero 는 10/13 에 의도적으로 멈춰 지금 클러스터 백업이 0개다.
3. **버전이 낡은 곳이 두 군데 있다.** Kubernetes Dashboard 는 업스트림이 아카이브됐고, Prometheus 는 아직 2.x 다.

---

## 0. 한눈에 보기

`kubectl top pods` 를 네임스페이스별로 합산한 값이다(순간값).

| 네임스페이스 | 핵심 구성 (버전) | CPU (m) | 메모리 (Mi) |
| --- | --- | ---: | ---: |
| logging | Elasticsearch·Kibana·Logstash 8.16.1, Fluent Bit 5.0.5 | 145 | 9,982 |
| monitoring | Prometheus v2.55.0, Grafana 11.2.2, Alertmanager v0.27.0, Tempo 2.7.1, OTel Collector 0.156.0 | 134 | 2,267 |
| kafka | Strimzi 0.51.0, Kafka 4.2.0 (KRaft) | 165 | 1,736 |
| argocd | Argo CD v3.4.1, Image Updater v0.16.0 | 149 | 804 |
| openviking | OpenViking v0.3.12 + Ollama | 8 | 547 |
| falco | Falco 0.45.0 ×5, Falcosidekick 2.32.0 | 272 | 521 |
| velero | Velero v1.18.1 (+ node-agent ×5) | 19 | 299 |
| ghstats · elastic-system · analytics-prod · nfs-server · arc-system · lemuel-monitor · sops-operator · cloudflared · kubernetes-dashboard · build · echo-webhook · registry-mirror | (아래 본문) | 64 | 489 |
| **합계** | | **952** | **16,645** |

같은 시각 노드 5대의 메모리 사용 합계는 50,250Mi 였다. 그러므로

$$
\frac{16{,}645}{50{,}250} \approx 33\%,\qquad \frac{9{,}982}{50{,}250} \approx 20\%
$$

즉 운영 기반이 클러스터 메모리의 약 3분의 1을 쓰고, 로깅 하나가 5분의 1을 쓴다.
CPU 쪽은 합쳐도 1코어가 안 되므로 이 클러스터에서 운영 기반의 비용은 거의 전부 **메모리**다.

---

## 1. 배포와 연결

### ArgoCD — git 이 곧 클러스터

**사용법.** 모든 차트와 매니페스트는 `helm-deploy` 리포에 있다. `root-app` 이 `argocd-applications/` 폴더를 보고 있다가
그 안의 `Application` 파일 개수만큼 앱을 만든다. 이른바 *App of Apps* 패턴이다.
`automated.prune` 과 `selfHeal` 이 켜져 있어서 다음처럼 동작한다.

- 파일을 지우고 push 하면 Application 이 사라진다.
- 손으로 `kubectl set env` 같은 변경을 하면 90초 안에 되돌아간다.

다만 우리 Application 에는 finalizer 가 없다. 그래서 Application 이 지워져도 그 아래 리소스까지 함께 지워지지는(cascade) 않는다.
어제 network-agent 를 내릴 때도 네임스페이스는 따로 지웠다.

```bash
# 강제 재조정
kubectl -n argocd annotate application root-app argocd.argoproj.io/refresh=hard --overwrite
# 전체 상태 집계
kubectl -n argocd get applications -o jsonpath='{range .items[*]}{.status.sync.status}/{.status.health.status}{"\n"}{end}' | sort | uniq -c
```

**실측.**

- 앱 **73개가 전부 Synced/Healthy** 다.
- 파드 8개가 합쳐 CPU 149m, 메모리 804Mi 를 쓴다.
- 컨트롤러·repo-server 가 모두 louise 한 노드에 있다. 공식 HA 매니페스트([Argo CD HA 문서][argocd-ha])와 달리 단일 레플리카 구성이다.

한계도 있다. ArgoCD 메트릭(`argocd_app_reconcile_*`)은 Prometheus 가 수집하고 있지 않다. 그래서 재조정 지연 시간은 이번에 잴 수 없었다.
그리고 "Healthy" 가 "쓰이고 있다"는 뜻은 아니다. 파드가 0개인 앱도 Healthy 로 뜬다.

### cloudflared — 포트 하나 안 여는 공개 도메인

**사용법.** 집 공유기에는 열린 포트가 없다. 클러스터 안의 cloudflared 가 Cloudflare 엣지로 **나가는** 연결을 맺어 두고,
`*.lemuel.co.kr` 요청을 그 연결을 거꾸로 타고 받아 들인다([Cloudflare Tunnel 문서][cf-tunnel]).
라우팅 규칙은 대시보드 원격 설정(remote config)에 있어서, 바꿀 때는 API 로 config 를 `PUT` 한다.

- 규칙 목록의 마지막 줄은 항상 `http_status:404` catch-all 이어야 한다.

**실측.** `--metrics 0.0.0.0:2000` 의 Prometheus 엔드포인트([메트릭 문서][cf-metrics])에서 읽었다.

- 리소스: 레플리카 1개, CPU 2m, 메모리 32Mi.
- 엣지 연결: `ha_connections=4`, 서울 엣지(icn01·icn06 등)에 붙어 있다.
- 프로세스 가동 577.5시간 동안 응답 **252,987건**. 평균하면 시간당 약 438건($$252{,}987 / 577.5 \approx 438$$)이다.

| 상태 코드 | 건수 | 비율 |
| --- | ---: | ---: |
| 2xx | 223,637 | 88.4% |
| 3xx | 11,081 | 4.4% |
| 4xx | 18,243 | 7.2% |
| 5xx | 26 | 0.01% |

5xx 26건은 내부 서비스가 내린 응답을 cloudflared 가 그대로 전달한 것이다.
터널 자체 오류(`cloudflared_tunnel_request_errors`)는 따로 2,116건이 집계됐다. 원점(origin)에 닿지 못한 요청들인데, 이번에는 원인별로 나눠 보지 않았다.

### sops-operator — git 에 넣어도 되는 시크릿

**사용법.** 시크릿은 [SOPS][sops] + age 로 값만 암호화한 YAML 로 git 에 올린다.
클러스터 안의 [sops-secrets-operator][sops-op] 가 `SopsSecret` CR 을 복호화해 일반 `Secret` 으로 만든다.
그래서 ArgoCD 는 평문을 한 번도 보지 않는다.

```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
sops -d secrets/foo.sops.yaml          # 확인
sops -e --filename-override secrets/foo.sops.yaml plain.yaml > secrets/foo.sops.yaml
```

어제 겪은 함정이 하나 있다. 여러 문서가 `---` 로 이어진 sops 파일은 **MAC 이 파일 전체에 걸려 있다.**
그래서 문서 하나를 sed 로 잘라내면 복호화가 MAC mismatch 로 실패한다. 반드시 복호화 → 편집 → 재암호화 순서로 해야 한다.

**실측.** `SopsSecret` 70개를 CPU 2m, 메모리 37Mi 로 처리한다. 운영 기반 가운데 비용 대비 효과가 가장 크다.

---

## 2. 빌드

### ARC (Actions Runner Controller) — 0까지 줄어드는 러너

**사용법.** GitHub Actions 잡이 들어올 때만 러너 파드를 띄우는 스케일 셋 방식이다([GitHub ARC 문서][arc]).
워크플로에서 `runs-on: watchman-arc` 처럼 스케일 셋 이름을 지정하면 된다.

**실측.**

- 컨트롤러 0.14.2 와 리스너 2개(합계 3m, 47Mi)만 상주한다.
- 스케일 셋은 `watchman-arc`(최소 0, 최대 1)와 `xr-arc`(최소 0, 최대 2) 두 개다.
- 측정 시점의 러너 수는 0개였다. 잡이 없을 때 러너가 차지하는 메모리는 0이다.

나머지 리포의 러너는 클러스터 밖, louise 호스트의 self-hosted 러너가 맡는다. 이쪽은 메모리가 약한 노드를 보호하려고 전역 뮤텍스로 한 번에 잡 하나만 돌린다.

### buildkitd — 클러스터 안 이미지 빌드

**사용법.** [rootless BuildKit][buildkit-rootless] v0.20.2 을 solomon 에 하나 띄워 두고, `buildctl --addr tcp://...` 로 원격 빌드한다.
rootless 라 특권 컨테이너가 필요 없다.

**실측.** 대기 상태에서 CPU 4m, 메모리 19Mi 다. 빌드할 때의 피크는 이번 측정 범위 밖이다.

### registry-mirror — 141일 동안 아무도 안 썼다

**사용법(의도).** CNCF Distribution(`registry:2.8.3`)을 `proxy.remoteurl: https://ghcr.io` 로 띄운 *pull-through 캐시*다([Distribution 문서][dist-mirror]).
처음 받은 이미지를 보관해 두었다가 두 번째부터는 로컬에서 내주려는 용도다.

**실측.**

- 파드 나이는 141일이다.
- 그런데 저장소 크기는 **4.0K** 다.
- 지난 30일 로그에서 kube-probe 를 뺀 요청은 9줄뿐이다.

원인은 노드 쪽에 있다. K3s 는 각 노드의 `/etc/rancher/k3s/registries.yaml` 에 `mirrors:` 항목이 있어야 그 미러로 받는다([K3s 문서][k3s-registry]).
그런데 노드 5대 모두에 `mirrors` 항목이 없었다. 미러 서버는 떠 있지만, 그걸 미러로 쓰라고 설정된 노드가 하나도 없다.

비용은 CPU 1m, 메모리 12Mi 로 미미하다. 하지만 "떠 있으니 쓰이고 있겠지"라는 착각을 만든다는 점이 진짜 비용이다.
선택지는 둘이다. 노드 5대에 `mirrors."ghcr.io".endpoint` 를 넣고 k3s 를 재시작하거나, 내리거나.

---

## 3. 백업 — velero 는 지금 멈춰 있다

**사용법.** [Velero][velero-ref] 스케줄 두 개가 정의돼 있다.

- `daily-with-volumes`: 매일 03:00, 보관 30일, 전체 네임스페이스 + 볼륨(node-agent 의 [파일시스템 백업][velero-fsb]/Kopia).
- `hourly-critical`: 이름과 달리 4시간마다(`0 */4 * * *`), 보관 7일. 정산 DB·asat·argocd·n8n 이 대상이다.

저장 위치는 Cloudflare R2(S3 호환)다.

**실측.**

- 백업 오브젝트가 **0개**다.
- 두 스케줄 모두 `spec.paused: true` 이고, 컨트롤러 로그에는 1분마다 `schedule ... is paused, skip` 이 찍힌다.
- 마지막 성공은 10/13 이다.

사고는 아니다. 10/13 커밋에서 일부러 멈춘 것이다. 포트폴리오용 홈랩이라 유료 오프사이트 백업은 필요 없다고 판단했고, 같은 날 R2 에 있던 기존 백업도 지웠다.
Velero 문서도 `paused` 를 "새 백업을 만들지 않는 상태"로 정의한다([Schedule API][velero-schedule]).
그래도 **결과는 결과다. 지금 이 클러스터에서 PV 가 망가지면 되돌릴 사본이 없다.** 이건 클러스터를 연구용으로 두고 장애를 감수한다는 결정의 연장선이다.

멈추기 전 7일간의 소요 시간은 히스토그램 버킷으로 보간한 중앙값으로만 남아 있다.

- daily 약 1,350초
- hourly-critical 약 393초

버킷 경계로 보간한 추정치라 정밀한 값은 아니다.

멈춘 상태인데도 리소스는 쓰고 있다. 상주하는 node-agent 5개와 서버 1개가 합쳐 CPU 19m, 메모리 299Mi 를 쓴다.

---

## 4. 관측

### Prometheus 스택 (kube-prometheus-stack)

**사용법.** [kube-prometheus-stack][kps] 차트로 Prometheus·Alertmanager·Grafana·kube-state-metrics·node-exporter 를 한 번에 띄운다.
수집 대상은 `ServiceMonitor` 로 선언한다. 같은 네임스페이스에 OTel Collector(Claude Code 텔레메트리 수신)와 Tempo(트레이스)도 있다.

```bash
kubectl -n monitoring port-forward svc/kps-prometheus 9090
curl -s --get localhost:9090/api/v1/query --data-urlencode 'query=count(up==0)'
```

**실측.**

| 지표 | 값 |
| --- | --- |
| 스크레이프 대상 | 67개, 다운 0 |
| 헤드 시계열 수 | 286,175 |
| 수집 속도 | 초당 약 7,717 샘플 |
| 블록 저장 크기 | 14.2GB (보관 15일 / 상한 25GB) |
| `/api/v1/query` p50 | 약 50ms (24시간, 버킷 보간) |
| `/api/v1/query_range` p90 | 약 90ms (24시간, 버킷 보간) |
| 리소스 (네임스페이스 합) | CPU 134m, 메모리 2,267Mi |

[공식 스토리지 문서][prom-storage]는 `--storage.tsdb.retention.time`(시간 기준)과 `retention.size`(크기 기준) 가운데 **먼저 걸리는 쪽**이 적용된다고 설명한다.
지금은 14.2GB 로 25GB 상한까지 여유가 있다. 따라서 실제로 적용되는 건 15일 보관 쪽이다.

버전은 v2.55.0 이다. Prometheus 3.0 은 2024년 11월에 나왔고([3.0 발표][prom3]) 새 UI 와 UTF-8 메트릭 이름 등이 기본값으로 바뀌었다.
메이저 버전 업그레이드라 따로 계획이 필요하다.

### ELK — 메모리의 5분의 1

**사용법.**

- 수집: [Fluent Bit][fluentbit] DaemonSet 이 노드마다 컨테이너 로그를 읽는다.
- 가공·저장: Logstash 가 가공해 Elasticsearch 로 보낸다. ES 는 [ECK 오퍼레이터][eck] 2.16.1 가 관리한다.
- 보관: [ILM][ilm] 으로 `logstash-k8s-*` 인덱스를 7일 뒤 삭제한다.
- 조회: Kibana.
- 알림: `log-error-alerter` CronJob 이 에러 급증을 텔레그램으로 알린다.

설계 배경은 [로깅 거시·미시 글]({% post_url 2026-10-15-k8s-logging-elk-macro-micro %})에 따로 정리했다.

**실측.**

| 지표 | 값 |
| --- | --- |
| 클러스터 상태 | green, 노드 1, 샤드 85, 미할당 0 |
| 문서 수 / 저장 크기 | 12,760,858 / 5.28GB |
| 일일 유입 (`logstash-k8s-*`) | 하루 136만~186만 건, 570~893MB |
| 평균 색인 시간 | 문서당 약 0.25ms |
| 평균 검색 시간 | 쿼리당 약 0.40ms (29,595건) |
| ES 파드 리소스 | 요청·한도 모두 메모리 6Gi |
| 리소스 (네임스페이스 합) | CPU 145m, 메모리 9,982Mi |

색인·검색 평균은 `_stats` 의 누적값을 나눈 것이다.

$$
\frac{2{,}950{,}651\ \text{ms}}{11{,}670{,}531\ \text{docs}} \approx 0.25\ \text{ms},\qquad
\frac{11{,}729\ \text{ms}}{29{,}595\ \text{queries}} \approx 0.40\ \text{ms}
$$

이 값은 ES 내부 처리 시간이다. Fluent Bit 에서 Kibana 에 보이기까지의 종단 간 지연은 아니다.
실제 검색량은 하루에 많지 않다. 그런데 메모리는 6Gi 를 상시 예약한다. **이 클러스터에서 가장 비싼 상주 비용은 "거의 안 보는 로그를 언제든 검색할 수 있게 해 두는 것"이다.**

### Falco — 커널에서 본 이상 행동

**사용법.** [Falco][falco] 0.45.0 이 노드마다 커널 이벤트(syscall)를 규칙과 대조하고,
걸린 이벤트를 [Falcosidekick][sidekick] 이 메트릭과 알림으로 내보낸다.
파수꾼(watchman)은 일부러 규칙에 걸리는 카나리 파드를 띄워서 탐지 경로가 살아 있는지 확인한다.

**실측.** sidekick 기동(10/4 16:13 UTC) 이후 약 11일간 이벤트는 **1,687건**이다(warning 1,499, notice 188).

| 규칙 | 건수 |
| --- | ---: |
| Read sensitive file untrusted | 1,305 |
| BPF filter attached to socket (BPFDoor pattern) | 166 |
| Contact K8S API Server From Container | 146 |
| Packet socket created on host | 36 |
| Clear Log Activities | 27 |
| Terminal shell in container | 4 |

상위 항목에는 `watchman-falco-canary-*` 파드 이름이 찍힌 것이 많다. 일부러 낸 이벤트라는 뜻이다.
`Contact K8S API` 는 API 서버를 부르는 것이 본업인 파드에서도 나오므로 건수만으로 위협이라 볼 수 없다.

비용은 노드당 CPU 0.03~0.17코어로, 네임스페이스 합계 272m 다.
**운영 기반 가운데 CPU 를 가장 많이 쓴다.** syscall 을 전수 검사하니 당연한 결과다.

### 작은 것들

- **lemuel-monitor** — 노드마다 도는 alpine 텔레그램 감시 봇 4개. 합계 33m, 43Mi.
- **analytics-prod** — 분석용 PostgreSQL 16 단일 인스턴스. 4m, 62Mi.
- **ghstats** — GitHub README 통계 카드를 자체 호스팅. 1m, 70Mi.

---

## 5. 그 밖의 공용 부품

### Kafka (Strimzi)

**사용법.** [Strimzi][strimzi] 0.51.0 오퍼레이터가 Kafka 4.2.0 을 **KRaft** 모드로 띄운다.
ZooKeeper 가 없고, 컨트롤러와 브로커를 겸하는 dual-role 노드 1개짜리 구성이다.
토픽과 사용자도 `KafkaTopic`/`KafkaUser` CR 로 git 에 선언한다. 정산 서비스의 Transactional Outbox 이벤트가 주된 사용처다.

**실측.**

- 내부 토픽을 뺀 토픽 144개, 컨슈머 그룹 16개.
- 복제 계수 1 이다. 브로커가 하나뿐이라 그 노드가 죽으면 그동안 Kafka 전체가 멈춘다.
- 리소스: CPU 165m, 메모리 1,736Mi (브로커 요청 1Gi / 한도 2Gi).
- 브로커 처리량 메트릭(`kafka_server_brokertopicmetrics_*`)은 수집되고 있지 않아 메시지 처리량은 잴 수 없었다.

### OpenViking + Ollama

봇들의 장기 기억(메모리 파일 470개)을 검색하는 컨텍스트 DB([OpenViking][openviking]) v0.3.12 와 로컬 임베딩용 Ollama 다.
두 개가 louise 에서 합계 8m, 547Mi 를 쓴다. LLM 호출은 클러스터 안의 LiteLLM 을 경유한다.

### nfs-server · Kubernetes Dashboard · echo-webhook

- **nfs-server** — 여러 파드가 같은 디렉터리를 쓸 때(RWX)를 위한 alpine NFS. 6m, 54Mi.
- **Kubernetes Dashboard** v2.7.0 — 3m, 30Mi. **업스트림 프로젝트가 아카이브됐다.** 공식 문서와 쿠버네티스 블로그가 Headlamp 로 옮길 것을 권한다([K8s 문서][k8s-dashboard], [전환 안내 블로그][headlamp]). 보안 패치가 더 나오지 않는 웹 UI 를 계속 띄워 둘 이유는 약하다.
- **echo-webhook** — 받은 요청을 그대로 돌려주는 [http-https-echo][echo]. 웹훅 디버깅용이다. 0m, 16Mi.

---

## 6. 정리 — 무엇을 할 것인가

| 항목 | 현재 상태 | 제안 |
| --- | --- | --- |
| registry-mirror | 141일째 아무도 사용하지 않음 (4K) | 노드 `registries.yaml` 에 미러 연결, 또는 내림 |
| velero | 의도적 정지, 백업 0개 | 결정 유지. 단 상주 비용(299Mi)과 "백업 없음"을 인지할 것 |
| Kubernetes Dashboard | 업스트림 아카이브 | Headlamp 로 교체, 또는 내림 |
| Prometheus 2.55 | 3.x 미전환 | 업그레이드 별도 계획 |
| ArgoCD·Kafka 메트릭 | 수집 안 됨 | ServiceMonitor 추가 (재조정 지연·처리량 확보) |
| ELK | 메모리 20% | 7일 보관과 6Gi 가 실제 검색량에 맞는지 재검토 |

운영 기반의 비용은 거의 전부 메모리다. 상위 세 개(ELK 9.98Gi, Prometheus 스택 2.27Gi, Kafka 1.74Gi)가 운영 기반 메모리의 약 84%를 차지한다.
반대로 sops-operator·cloudflared·ARC 처럼 수십 Mi 로 큰 역할을 하는 부품도 있다.
**성능 문제보다 "떠 있지만 일을 안 하는 것"을 찾는 쪽이 더 큰 수확이었다.**

## 측정 방법과 한계

- 리소스는 `kubectl top`(metrics-server)의 **순간값**이다. 피크나 평균이 아니다.
- p50·p90 은 Prometheus 히스토그램의 `histogram_quantile` 결과다. 버킷 경계 사이를 선형 보간한 추정치다.
- cloudflared·ES·Falco 수치는 각 프로세스의 **기동 이후 누적 카운터**다. 기간이 서로 다르다(577시간, 인덱스 보관 7일, 약 11일).
- ArgoCD 재조정 지연, Kafka 처리량, buildkitd 빌드 피크는 메트릭이 없거나 측정 범위 밖이라 싣지 않았다.
- 컴포넌트 사이의 성능 비교(예: ELK 대 Loki)는 이 글의 범위가 아니다. 같은 하드웨어에서 맞붙여 잰 중립 벤치마크도 없다.

## References

- [argocd-ha]: Argo CD — High Availability. <https://argo-cd.readthedocs.io/en/stable/operator-manual/high_availability/>
- [cf-tunnel]: Cloudflare — Cloudflare Tunnel. <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/>
- [cf-metrics]: Cloudflare — Tunnel metrics. <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/monitor-tunnels/metrics/>
- [sops]: getsops/sops. <https://github.com/getsops/sops>
- [sops-op]: isindir/sops-secrets-operator. <https://github.com/isindir/sops-secrets-operator>
- [arc]: GitHub Docs — Actions Runner Controller. <https://docs.github.com/en/actions/concepts/runners/actions-runner-controller>
- [buildkit-rootless]: moby/buildkit — Rootless mode. <https://github.com/moby/buildkit/blob/master/docs/rootless.md>
- [dist-mirror]: CNCF Distribution — Registry as a pull through cache. <https://distribution.github.io/distribution/recipes/mirror/>
- [k3s-registry]: K3s — Private Registry Configuration. <https://docs.k3s.io/installation/private-registry>
- [velero-ref]: Velero v1.18 — Backup Reference. <https://velero.io/docs/v1.18/backup-reference/>
- [velero-fsb]: Velero v1.18 — File System Backup. <https://velero.io/docs/v1.18/file-system-backup/>
- [velero-schedule]: Velero v1.18 — Schedule API Type. <https://velero.io/docs/v1.18/api-types/schedule/>
- [kps]: prometheus-community — kube-prometheus-stack. <https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack>
- [prom-storage]: Prometheus — Storage. <https://prometheus.io/docs/prometheus/latest/storage/>
- [prom3]: Prometheus Blog — Announcing Prometheus 3.0 (2024-11-14). <https://prometheus.io/blog/2024/11/14/prometheus-3-0/>
- [fluentbit]: Fluent Bit Manual. <https://docs.fluentbit.io/manual>
- [eck]: Elastic — Elastic Cloud on Kubernetes. <https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s>
- [ilm]: Elastic — Index lifecycle management. <https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management>
- [falco]: Falco Documentation. <https://falco.org/docs/>
- [sidekick]: falcosecurity/falcosidekick. <https://github.com/falcosecurity/falcosidekick>
- [strimzi]: Strimzi — Deploying and Managing. <https://strimzi.io/docs/operators/latest/deploying>
- [openviking]: volcengine/OpenViking. <https://github.com/volcengine/OpenViking>
- [k8s-dashboard]: Kubernetes — Deploy and Access the Kubernetes Dashboard. <https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/>
- [headlamp]: Kubernetes Blog — From Kubernetes Dashboard to Headlamp (2026-06-01). <https://kubernetes.io/blog/2026/06/01/dashboard-to-headlamp/>
- [echo]: mendhak/docker-http-https-echo. <https://github.com/mendhak/docker-http-https-echo>

[argocd-ha]: https://argo-cd.readthedocs.io/en/stable/operator-manual/high_availability/
[cf-tunnel]: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/
[cf-metrics]: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/monitor-tunnels/metrics/
[sops]: https://github.com/getsops/sops
[sops-op]: https://github.com/isindir/sops-secrets-operator
[arc]: https://docs.github.com/en/actions/concepts/runners/actions-runner-controller
[buildkit-rootless]: https://github.com/moby/buildkit/blob/master/docs/rootless.md
[dist-mirror]: https://distribution.github.io/distribution/recipes/mirror/
[k3s-registry]: https://docs.k3s.io/installation/private-registry
[velero-ref]: https://velero.io/docs/v1.18/backup-reference/
[velero-fsb]: https://velero.io/docs/v1.18/file-system-backup/
[velero-schedule]: https://velero.io/docs/v1.18/api-types/schedule/
[kps]: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack
[prom-storage]: https://prometheus.io/docs/prometheus/latest/storage/
[prom3]: https://prometheus.io/blog/2024/11/14/prometheus-3-0/
[fluentbit]: https://docs.fluentbit.io/manual
[eck]: https://www.elastic.co/docs/deploy-manage/deploy/cloud-on-k8s
[ilm]: https://www.elastic.co/docs/manage-data/lifecycle/index-lifecycle-management
[falco]: https://falco.org/docs/
[sidekick]: https://github.com/falcosecurity/falcosidekick
[strimzi]: https://strimzi.io/docs/operators/latest/deploying
[openviking]: https://github.com/volcengine/OpenViking
[k8s-dashboard]: https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/
[headlamp]: https://kubernetes.io/blog/2026/06/01/dashboard-to-headlamp/
[echo]: https://github.com/mendhak/docker-http-https-echo
