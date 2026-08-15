---
layout: post
title: "쿠버네티스 관리자가 알아야 할 A to Z — 조용히 실패하는 것들"
date: 2026-08-12 02:30:00 +0900
categories: [kubernetes, operations]
tags:
  [
    kubernetes,
    k3s,
    argocd,
    prometheus-operator,
    velero,
    elasticsearch,
    networkpolicy,
    gitops,
  ]
---

> 사설망 주소는 `<lan>` · `<mgmt>` 로 가렸다. 호스트 옥텟과 각 줄의 의미는 원본 실측 그대로다.

[앞 글](/2026/08/12/infra-admin-a-to-z/)에서는 쿠버네티스 _아래_ 층을 봤다. 네트워크, 방화벽, 디스크, 쿼럼처럼 `kubectl`로는 안 보이는 것들이었다. 이번엔 같은 6노드 클러스터를 **안쪽에서** 본다.

이 글을 관통하는 주제가 하나 있다. **쿠버네티스의 실패는 대부분 시끄럽지 않다.** 오브젝트는 `Created`라고 하고, 파드는 `Running`이고, `kubectl get`은 초록색인데 실제로는 아무 일도 일어나지 않는다. 아래 사례는 전부 그런 종류다.

측정은 2026년 8월 12일, K3s v1.35.4, 6노드, 네임스페이스 56개, ArgoCD Application 64개 기준이다.

---

## A. 컨트롤러가 없으면 오브젝트는 그냥 장식이다

이번 조사에서 가장 놀란 것부터.

```
$ kubectl get ingress -A --no-headers | wc -l
6

$ kubectl get ingressclass
No resources found

$ kubectl get pods -A | grep -Ei 'traefik|ingress-nginx|contour|haproxy'
(빈 출력)
```

**Ingress가 6개 있는데 인그레스 컨트롤러는 0개다.** LoadBalancer 타입 Service도 0개, k3s의 `svclb` 파드도 0개다. 저 6개는 어떤 트래픽도 처리하지 않는다.

쿠버네티스는 이걸 오류로 알려주지 않는다. `Ingress`는 **선언**일 뿐이고, 그 선언을 실행하는 건 컨트롤러다. 컨트롤러가 없으면 API 서버는 오브젝트를 기쁘게 저장하고 끝낸다.

NetworkPolicy 문서가 같은 원리를 아주 직설적으로 말한다.[^1]

> "Network policies are implemented by the network plugin. To use network policies, you must be using a networking solution which supports NetworkPolicy. **Creating a NetworkPolicy resource without a controller that implements it will have no effect.**"

> "POSTing this to the API server for your cluster **will have no effect** unless your chosen networking solution supports network policy."

이 문장의 "NetworkPolicy" 자리에 Ingress, HPA, PDB, VPA, 커스텀 CRD 무엇을 넣어도 참이다. **쿠버네티스에서 리소스 생성이 성공했다는 건 "저장됐다"는 뜻이지 "동작한다"는 뜻이 아니다.**

**교훈.** 새 리소스 종류를 도입할 때는 항상 두 개를 확인하라 — 오브젝트가 있는가, 그리고 **그걸 읽는 컨트롤러가 떠 있는가.**

---

## B. `status`는 컨트롤러가 쓴다 — 컨트롤러가 죽으면 status는 거짓말을 한다

A절이 무서운 진짜 이유는 이거다. 저 6개 Ingress는 **비어 보이지 않는다.**

```
$ kubectl -n settlement-prod get ingress payment-webhook -o jsonpath='{.status}'
{"loadBalancer":{"ingress":[{"ip":"<lan>.101"},{"ip":"<lan>.105"},
{"ip":"<lan>.110"},{"ip":"<lan>.111"},{"ip":"<lan>.113"}]}}
```

`ADDRESS` 칸에 노드 IP 5개가 찍혀 있다. 대시보드로 보면 완벽하게 건강해 보인다.

저 값은 **Traefik이 살아 있던 시절 Traefik이 써넣은 것**이다. 쿠버네티스에서 `status`는 컨트롤러가 소유하는 필드다. 그리고 컨트롤러가 사라질 때 **자기가 쓴 status를 지우고 가지 않는다.** 아무도 갱신하지 않으니 마지막 값에서 그대로 굳는다.

그래서 이런 규칙이 나온다. **`status`는 "지금 상태"가 아니라 "마지막으로 누군가 관찰한 상태"다.** 그 누군가가 아직 살아 있는지는 별도로 확인해야 한다.

실제 트래픽은 `cloudflared` 파드 3개가 Service로 직접 넣고 있고, 외부에서 재보면 `HTTP/2 200`이 온다. **Ingress는 경로에 없다.** 저 6개를 지금 수정해도 아무 일도 일어나지 않는다.

**교훈.** 헬스 판단을 `status` 필드에 걸지 마라. 트래픽 경로는 **실제 요청**으로 검증해야 한다.

---

## C. 패키지 애드온은 지워도 부활한다

Traefik은 왜 있다가 없어졌나. K3s에서 이건 유명한 함정이다.

K3s 공식 문서를 보자.[^2]

> "On server nodes, any file found in `/var/lib/rancher/k3s/server/manifests` will automatically be deployed to Kubernetes in a manner similar to `kubectl apply`, both on startup and when the file is changed on disk. **Deleting files out of this directory will not delete the corresponding resources from the cluster.**"

> "Manifests for packaged components are managed by K3s, and should not be altered. **The files are re-written to disk whenever K3s is started**, in order to ensure their integrity."

즉 `kubectl delete`로 Traefik을 지워도, **서버를 재시작하면 매니페스트가 디스크에 다시 쓰이고 다시 배포된다.** 지운 게 아니라 잠깐 없앤 것이다.

제대로 된 방법은 둘이다.

**1) `--disable` 플래그 (권장)**[^2]

> "Disabled AddOns are **actively uninstalled** from the cluster, and the source files deleted from the `manifests` directory. For example, to disable traefik from being installed on a new cluster, or to uninstall it and remove the manifest from an existing cluster, you can start K3s with `--disable=traefik`."

**2) `.skip` 파일**[^2]

> "For any file under `/var/lib/rancher/k3s/server/manifests`, you can create a `.skip` file which will cause K3s to ignore the corresponding manifest. **The contents of the `.skip` file do not matter, only its existence is checked.** Note that creating a `.skip` file after an AddOn has already been created **will not remove or otherwise modify it**..."

둘의 차이가 중요하다. `--disable`은 **적극적으로 제거**하고, `.skip`은 **그냥 무시**한다. 이미 배포된 리소스가 있다면 `.skip`은 그걸 건드리지 않는다.

`.skip`이 유용한 다른 경우도 있다. 내 클러스터에서는 CoreDNS 애드온이 부팅마다 apply에 실패하며 무한 재시도를 돌았다. 매니페스트 파일을 고쳐도 소용없었다 — 위 문서대로 **K3s가 재시작 때마다 파일을 다시 써버리기 때문**이다. `coredns.yaml.skip`을 만드는 게 정답이었다.

**교훈.** 관리 주체가 따로 있는 리소스는 `kubectl delete`로 지워지지 않는다. **누가 이 파일/리소스를 소유하는지**를 먼저 물어라.

---

## D. 선언적 시스템은 당신의 손을 되돌린다

같은 원리가 GitOps에서 훨씬 빠르게 나타난다.

내 클러스터의 ArgoCD Application 64개 중 **59개가 `selfHeal: true`**다. 이게 무슨 뜻인지 공식 문서가 명확히 적는다.[^3]

> "By default, changes that are made to the live cluster will not trigger automated sync. To enable automatic sync when the live cluster's state deviates from the state defined in Git, run: `argocd app set --self-heal`"

> "If the `selfHeal` flag is set to true, then the sync will be attempted again after **self-heal timeout (5 seconds by default)** which is controlled by `--self-heal-timeout-seconds` flag of `argocd-application-controller` deployment."

**기본 5초다.** 그러니 `kubectl set env`, `kubectl scale`, `kubectl edit`으로 한 임시 조치는 대부분 살아남지 못한다. 나도 스케줄 잡을 강제로 돌리려고 환경변수를 바꿨다가 90초쯤 뒤에 원상 복구된 걸 보고서야 이 구조를 이해했다.

리컨실 주기는 따로 있다.[^4]

> "Application reconciliation timeout is the amount of time spent before Argo tries to discover if a new manifests version got published to the repository... **Two minutes by default with additional jitter**... `timeout.reconciliation: 120s`" / "`timeout.reconciliation.jitter: 60s`"

**여기서 자주 인용되는 `180s`는 지금 기준으로는 틀린 값이다.** 현재 stable 문서는 `120s` + jitter `60s`(실효 120~180초)다. 예전 릴리스에서는 180초가 기본이었으니, 오래된 블로그를 보고 있다면 이 숫자를 의심해야 한다.

**그래서 실무 규칙이 나온다.** selfHeal이 켜진 앱에서 일회성 작업이 필요하면, 관리 대상 리소스를 건드리지 말고 **관리 대상이 아닌 일회용 오브젝트**를 따로 만들어라(배포 이미지로 Pod를 하나 띄우되, Service selector에 걸리지 않게 라벨을 다르게 준다). 그러면 컨트롤러가 되돌릴 게 없다.

**교훈.** 선언적 시스템에서 "손으로 고쳤다"는 대부분 "5초 동안 고쳤다"는 뜻이다.

---

## E. 관측 배선은 두 홉이고, 둘 다 조용히 실패한다

Prometheus Operator의 ServiceMonitor는 초보자가 반드시 한 번은 데는 곳이다. **선택이 두 단계**이기 때문이다.

**1홉: Prometheus → ServiceMonitor.** Prometheus CR이 어떤 ServiceMonitor를 볼지 고른다.[^5]

> "serviceMonitorSelector defines the serviceMonitors to be selected for target discovery. **An empty label selector matches all objects. A null label selector matches no objects.**"

`{}`(빈 것)와 미지정(null)의 의미가 정반대다. 전자는 전부, 후자는 아무것도 아니다.

**2홉: ServiceMonitor → Service.** 여기가 진짜 함정이다.[^6]

> "**Note: The ServiceMonitor references a Service (not a Deployment, or a Pod), by labels and by the port name in the Service.** This port name is optional in Kubernetes, but must be specified for the ServiceMonitor to work. It is not the same as the port name on the Pod or container, although it can be."

두 가지가 한꺼번에 들어 있다.

- 셀렉터는 **Pod 라벨이 아니라 Service의 `metadata.labels`**를 본다. 파드 라벨을 맞춰놓고 왜 안 되냐고 하는 경우가 대부분 이것이다.
- 포트는 **번호가 아니라 이름**으로 참조한다. Service에 포트 이름이 없으면 영영 안 붙는다.

그래서 나는 **27개 ServiceMonitor 전부를 감사하는 스크립트**를 짰다. 각 ServiceMonitor의 셀렉터가 실제로 Service를 잡는지, 그 Service가 요구된 포트 *이름*을 갖는지 확인하는 것이다.

**그리고 내 스크립트가 오진했다.** 이 이야기를 그대로 적는 게 이 절의 핵심이다.

스크립트는 `claude-telemetry-prod`를 "깨졌다"고 보고했다. 셀렉터가 잡은 Service에 `metrics`라는 포트 이름이 없다는 것이었다. 그런데 발표하기 전에 Prometheus API로 실제 타깃을 조회해봤다.

```
pool   : serviceMonitor/monitoring/claude-telemetry-prod/0
url    : http://10.42.1.205:8889/metrics
health : up
```

**멀쩡히 붙어 있었다.** 원인은 내 논리 오류였다. 셀렉터가 Service를 **두 개** 잡고 있었던 것이다.

```
claude-telemetry-prod-ingest    otlp-http,otlp-grpc
claude-telemetry-prod-metrics   metrics
```

하나는 수집 포트, 하나는 메트릭 포트다. **셀렉터가 여러 Service를 매칭하는 건 정상**이고, 그중 하나만 해당 포트 이름을 가지면 된다. 내 스크립트는 "하나라도 없으면 실패"로 판정했다. 고쳐서 다시 돌린 결과가 진짜 값이다.

```
ServiceMonitors total: 27   Services total: 129
HOP-B OK: 27    HOP-B BROKEN: 0
```

Prometheus 쪽 교차 검증도 같은 답을 줬다 — 스크레이프 풀 31개, **타깃 전부 `up`**.

여기에 한 겹 더 있다. 공식 트러블슈팅 문서는 "설정에 있는 것"과 "타깃이 잡힌 것"을 구분한다.[^6]

> "**It is in the configuration but not on the Service Discovery page.** ServiceMonitors pointing to Services that do not exist (e.g. nothing matching `.spec.selector`) will lead to this ServiceMonitor not being added to the Service Discovery page."

즉 Prometheus 설정 파일을 grep해서 이름이 나오는 것만으로는 부족하다. 실제로 내 클러스터에서도 `serviceMonitor/monitoring/claude-telemetry-prod`는 설정에 **있었다.** 설정에 있는 것과 타깃이 붙은 것은 다른 사건이다.

**교훈 두 개.** 첫째, 관측 배선은 홉마다 따로 검증하라. 둘째 — 이게 더 중요한데 — **자기 감사 스크립트도 감사하라.** 나는 하마터면 멀쩡한 걸 고장 났다고 발표할 뻔했다.

---

## F. 메모리는 압축 불가능한 자원이다

CPU와 메모리는 초과했을 때 결과가 완전히 다르다. 공식 문서가 나란히 설명한다.[^7]

> "`cpu` limits are enforced by **CPU throttling**. When a container approaches its `cpu` limit, the kernel will restrict access to the CPU..."

> "`memory` limits are enforced by the kernel with **out of memory (OOM) kills**. When a container uses more than its `memory` limit, the kernel may terminate it."

> "Last State: Terminated / Reason: **OOMKilled** / Exit Code: **137**"

**CPU를 초과하면 느려지고, 메모리를 초과하면 죽는다.** 그래서 메모리 limit은 CPU limit보다 훨씬 신중하게 정해야 한다.

내 클러스터의 백업 컴포넌트(Velero node-agent)가 이걸 정확히 보여줬다. 메모리 limit이 512Mi였는데 44번 연속 OOMKilled 됐고, 2Gi로 올려서 해결했다. 지금도 그대로 있다.

```
$ kubectl -n velero get ds node-agent -o jsonpath='{.spec.template.spec.containers[0].resources}'
{"limits":{"cpu":"500m","memory":"2Gi"},"requests":{"cpu":"100m","memory":"512Mi"}}
```

**그런데 문서를 확인하다가 두 가지를 발견했다. 둘 다 내가 틀렸던 쪽이다.**

**첫째, 업스트림은 이 컴포넌트에 limit을 아예 안 건다.** Velero 공식 문서다.[^8]

> "For node-agent pod, **by default it doesn't have CPU/memory request/limit**, so that the backups/restores won't break due to resource throttling."

업스트림이 _의도적으로_ 비워둔 자리에 우리가 512Mi를 채웠고, 그래서 죽은 것이다. **OOM의 원인은 워크로드가 아니라 우리가 건 족쇄였다.**

**둘째, 같이 넣었던 튜닝 하나는 아마 아무 일도 안 하고 있다.** 그 DaemonSet에는 이런 환경변수가 박혀 있다.

```
KOPIA_PARALLEL_FILE_READS=2
```

그런데 **Velero 공식 문서에도, Kopia 공식 문서에도 그런 이름의 환경변수는 없다.** Kopia가 문서화한 환경변수는 `KOPIA_BYTES_STRING_BASE_2` 하나뿐이고, 병렬 읽기는 환경변수가 아니라 정책/플래그로 노출된다.

> "Kopia CLI users can change this setting by running the `kopia policy set [target] **--max-parallel-file-reads=#**` command... By default, Kopia sets this setting to the number of logical cores your machine's CPU has."[^9]

Velero 쪽에서도 `velero backup create --parallel-files-upload <NUM>` 또는 node-agent ConfigMap의 `uploaderConfig`로 조절한다.[^10] **즉 우리가 넣은 환경변수는 인식되지 않는 이름일 가능성이 크고, 실제로 OOM을 잡은 것은 메모리 limit 조정 쪽이다.**

이건 흔한 실패 유형이다. 여러 조치를 한꺼번에 넣고 증상이 사라지면, **어느 것이 실제로 작동했는지 모른 채 전부를 신봉하게 된다.** 그리고 문서에 없는 환경변수는 오타여도 아무도 알려주지 않는다. 쿠버네티스는 모르는 환경변수를 조용히 받아들인다.

**교훈.** 조치는 한 번에 하나씩. 그리고 **설정 키 이름은 공식 문서에서 존재를 확인하라.** 없는 키는 에러가 아니라 침묵으로 돌아온다.

---

## G. 시크릿은 파드를 부팅 전에 막는다

암호화 키 하나가 없어서 서비스가 CrashLoop에 빠진 적이 있다. 이 동작은 공식 문서에 정확히 정의돼 있다.[^11]

> "By default, Secrets are required. **None of a Pod's containers will start until all non-optional Secrets are available.**"

> "If a Pod references a specific key in a non-optional Secret and that Secret does exist, but is **missing the named key, the Pod fails during startup.**"

두 문장의 차이가 실무에서 중요하다.

- 시크릿 **자체가 없으면** → 컨테이너가 아예 시작 안 됨(이벤트에 표시됨, 비교적 찾기 쉬움)
- 시크릿은 있는데 **키가 없으면** → 시작하다 실패(원인이 애플리케이션 로그에 묻히기 쉬움)

후자가 훨씬 고약하다. 애플리케이션은 "키가 없다"가 아니라 "빈 문자열로 초기화 실패"처럼 자기 방식으로 죽기 때문이다.

**교훈.** 새 시크릿 키를 요구하는 코드를 배포할 때는 **키 추가가 배포보다 먼저** 나가야 한다. 그리고 그 키를 GitOps에 영속화하지 않으면, 다음 클러스터 재구성 때 똑같이 죽는다.

---

## H. 서비스 이름이 환경변수를 오염시킨다

이건 알고 나면 허무한데, 모르면 며칠 잡아먹는다.

쿠버네티스는 파드를 띄울 때 **각 Service에 대한 Docker 링크 스타일 환경변수를 자동 주입한다.**[^12]

> "EnableServiceLinks indicates whether information about services should be injected into pod's environment variables, matching the syntax of Docker links. **Optional: Defaults to true.**"

그리고 공식 튜토리얼이 충돌 가능성을 직접 언급한다.[^13]

> "If the service environment variables are not desired (**because possible clashing with expected program ones**, too many variables to process, only using DNS, etc) you can disable this mode by setting the `enableServiceLinks` flag to `false` on the pod spec."

무슨 일이 벌어지냐면 — Service 이름이 `data-api`면 파드 안에 `DATA_API_PORT` 같은 변수가 생긴다. 그런데 애플리케이션이 마침 `DATA_API_PORT`를 자기 설정으로 읽고 있었다면? 애플리케이션은 `8080`을 기대하는데 `tcp://10.43.x.x:8080`을 받는다. 그리고 죽는다.

**기본값이 `true`라는 게 핵심이다.** 아무것도 안 해도 이 주입은 일어난다. Service 이름과 애플리케이션 환경변수 이름이 겹치는 순간 터진다.

**교훈.** 앱 고유 환경변수는 접두어를 붙여라(`MYAPP_`). 그리고 DNS만 쓰는 앱이라면 `enableServiceLinks: false`가 기본값이어야 할 이유는 충분하다.

---

## I. NetworkPolicy — k3s에서는 실제로 강제된다

A절에서 "컨트롤러 없으면 무효"라고 했는데, NetworkPolicy에 대해 **k3s는 컨트롤러를 기본 탑재한다.**[^14]

> "K3s includes an **embedded network policy controller**. The underlying implementation is kube-router's netpol controller library (no other kube-router functionality is present)... To disable it, start each server with the `--disable-network-policy` flag."

Flannel 자체는 NetworkPolicy를 구현하지 않지만, k3s가 별도 컨트롤러를 같이 넣어준다. 그래서 **k3s에서 NetworkPolicy는 별도 설정 없이 실제로 동작한다.** 내 클러스터에는 현재 9개가 걸려 있다.

이게 운영상 재미있는 성질을 하나 준다. ArgoCD `selfHeal`이 되돌리는 필드(replicas 같은 것)와 달리, **네트워크 정책은 GitOps 관리 밖에서 만들면 그대로 남는다.** 그래서 급하게 트래픽을 끊어야 할 때 실효성 있는 수단이 된다. 물론 그 사실 자체가 위험이기도 하다 — 아무도 모르는 차단 규칙이 클러스터에 남을 수 있다.

**교훈.** "이 리소스 종류는 우리 클러스터에서 실제로 강제되는가"를 종류별로 확인해두라. 답이 배포판마다 다르다.

---

## J. CronJob은 100번 놓치면 조용히 포기한다

마지막으로 짧지만 잘 안 알려진 것.[^15]

> "For every CronJob, the CronJob Controller checks how many schedules it missed in the duration from its last scheduled time until now. **If there are more than 100 missed schedules, then it does not start the Job and logs the error.**"

> 에러 문구: "**too many missed start times. Set or decrease .spec.startingDeadlineSeconds or check clock skew**"

컨트롤 플레인이 오래 죽어 있었거나 시계가 어긋났다면, 복구 후에도 CronJob이 **영영 안 돈다.** 파드가 안 뜨는데 이유는 로그 한 줄에만 있다.

`startingDeadlineSeconds`를 설정하면 계산 기준이 바뀐다.[^15]

> "if the `startingDeadlineSeconds` field is set (not nil), the controller counts how many missed Jobs occurred **from the value of startingDeadlineSeconds until now** rather than from the last scheduled time until now."

**교훈.** 장애 복구 후에는 CronJob이 다시 도는지 **직접 확인**하라. 조용히 포기하는 컴포넌트가 있다.

---

## 보너스: 로그 파이프라인의 침묵 — Bulk 200은 성공이 아니다

관측 이야기가 나온 김에 하나 더. Elasticsearch로 로그를 넣을 때 겪은 것이다.

쿠버네티스 라벨처럼 **키가 임의로 늘어나는 필드**를 그대로 매핑하면 필드 수가 폭발한다. Elastic이 이 문제 때문에 `flattened` 타입을 만들었다.[^16]

> "This data type can be useful for indexing objects with **a large or unknown number of unique keys**. Only one field mapping is created for the whole JSON object, which can help **prevent a mappings explosion** from having too many distinct field mappings."

한계도 명시돼 있다.[^17]

> "The maximum number of fields in an index... **The default value is `1000`.** Beyond this limit, Elasticsearch returns the error `Limit of total fields [X] has been exceeded`."

그래서 `kubernetes.labels`를 `flattened`로 매핑하지 않으면 어느 순간 색인이 거부되기 시작한다.

**그런데 진짜 문제는 이게 조용하다는 것이다.** Bulk API는 개별 항목 실패를 **항목별로** 돌려준다.[^18]

> "`errors` boolean Required — If `true`, one or more of the operations in the bulk request **did not complete successfully**."
> "`status` number Required — The HTTP status code returned for **the operation**." (items[] 안의 필드)

즉 **전체 응답이 200이어도 개별 문서는 얼마든지 실패했을 수 있다.** 보내는 쪽이 `errors` 플래그와 `items[].status`를 확인하지 않으면, 로그는 사라지는데 파이프라인은 초록불이다.

_(정직하게 덧붙이면 — "전체 HTTP 200이 전부 성공을 의미하지 않는다"는 문장 자체를 공식 문서에서 그대로 찾지는 못했다. 위 두 필드 정의가 공식이고, 그 해석은 내가 붙인 것이다.)_

**교훈.** 전송 계층의 성공과 처리의 성공을 구분하라. 파이프라인 헬스체크는 **"보냈다"가 아니라 "색인됐다"**를 재야 한다.

---

## K. 쿠버네티스 관리자 체크리스트

1. **오브젝트가 있다고 동작하는 게 아니다.** 그 종류를 처리하는 컨트롤러가 떠 있는지 확인하라.
2. **`status`는 마지막 관찰자의 기록이다.** 관찰자가 살아 있는지 따로 확인하라.
3. **패키지 애드온은 `kubectl delete`로 안 없어진다.** `--disable` 또는 `.skip`을 써라.
4. **selfHeal이 켜져 있으면 손으로 한 수정은 기본 5초짜리다.** 일회성 작업은 관리 대상 밖 오브젝트로 하라.
5. **ServiceMonitor는 Pod가 아니라 Service의 라벨을 본다.** 그리고 포트는 번호가 아니라 이름이다.
6. **빈 셀렉터 `{}`와 미지정(null)은 정반대 의미다.**
7. **메모리 limit은 죽음을, CPU limit은 지연을 만든다.** 업스트림이 비워둔 limit을 함부로 채우지 마라.
8. **설정 키 이름은 공식 문서에서 존재를 확인하라.** 없는 키는 침묵으로 무시된다.
9. **시크릿 키 추가는 코드 배포보다 먼저.** 키 누락은 애플리케이션 로그에 묻힌다.
10. **앱 환경변수에는 접두어를 붙여라.** Service 이름과 충돌하면 원인 찾기 어렵다.
11. **장애 복구 후 CronJob이 다시 도는지 확인하라.** 100번 놓치면 포기한다.
12. **파이프라인은 "전송 성공"이 아니라 "처리 성공"을 재라.**
13. **자기 진단 스크립트도 검증하라.** 오탐은 멀쩡한 걸 고치게 만든다.

---

## 이 글의 한계

- **단일 클러스터(6노드 K3s v1.35.4, 홈랩 규모)의 관측이다.** 매니지드 EKS/GKE와는 배포판 기본값이 다를 수 있다. 특히 C절(패키지 애드온)과 I절(내장 netpol 컨트롤러)은 **k3s 고유 동작**이다.
- **`KOPIA_PARALLEL_FILE_READS`가 "무시된다"는 것은 문서상 부재로부터의 추론이다.** 나는 Velero/Kopia 공식 문서에 그 이름이 없다는 것까지만 확인했고, 런타임에서 실제로 무시되는지 코드 레벨로 검증하지는 않았다. "미문서화 키"라고 읽는 게 정확하다.
- **Velero OOM 44회와 512Mi→2Gi 조정은 이전 기록이고 이번에 재현한 것이 아니다.** 이번에 재측정한 것은 현재 DaemonSet의 resources와 env 값이다.
- **Elasticsearch Bulk 절의 "200이 전부 성공은 아니다"라는 표현은 공식 문장이 아니라 내 해석이다.** 근거로 쓴 `errors` / `items[].status` 필드 정의만 공식이다.
- **`{SVCNAME}_PORT=tcp://...` 형식**은 kubernetes.io 산문에 그대로 나오지는 않는다. 메커니즘과 충돌 위험은 공식 문서로 확인했고, 정확한 문자열 형식은 소스 레벨 사항이다.
- **ArgoCD `180s`는 과거 기본값이다.** 현재 stable 기준 `120s` + jitter `60s`로 바로잡아 적었다.

---

## 마무리

두 글을 관통하는 결론은 하나다. **쿠버네티스는 실패를 크게 알려주지 않는다.**

Ingress는 주소를 보여주면서 아무것도 안 하고, 환경변수는 오타여도 침묵하고, Bulk API는 200을 주면서 문서를 버리고, CronJob은 로그 한 줄 남기고 포기한다. 이 시스템에서 관리자의 실력은 **초록불을 얼마나 안 믿느냐**로 결정된다.

그래서 A to Z 중 Z는 이것이다. **"동작한다"는 것을 오브젝트가 아니라 결과로 확인하라.** 요청을 보내보고, 타깃 수를 세보고, 색인된 문서를 조회해보라.

그리고 이번 글을 쓰며 가장 크게 배운 것 — **자기 측정 도구를 의심하는 것도 그 습관에 포함된다.** 나는 27개 중 1개가 고장 났다고 발표할 뻔했고, 실제로 고장 난 건 내 스크립트였다.

---

## References

[^1]: Kubernetes 공식 문서, "Network Policies" (1차·공식). <https://kubernetes.io/docs/concepts/services-networking/network-policies/>

[^2]: K3s 공식 문서, "Packaged Components" (1차·공식). <https://docs.k3s.io/installation/packaged-components>

[^3]: Argo CD 공식 문서, "Automated Sync Policy" (1차·공식). <https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/>

[^4]: Argo CD 공식 문서, `argocd-cm.yaml` 레퍼런스 (1차·공식). <https://argo-cd.readthedocs.io/en/stable/operator-manual/argocd-cm-yaml/> · 고가용성 문서 <https://argo-cd.readthedocs.io/en/latest/operator-manual/high_availability/>

[^5]: Prometheus Operator 공식 API 레퍼런스 (1차·공식). <https://prometheus-operator.dev/docs/api-reference/api/> · 설계 문서 <https://prometheus-operator.dev/docs/getting-started/design/>

[^6]: Prometheus Operator 공식 트러블슈팅 문서 (1차·공식). <https://prometheus-operator.dev/docs/platform/troubleshooting/>

[^7]: Kubernetes 공식 문서, "Resource Management for Pods and Containers" (1차·공식). <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/> · QoS <https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/>

[^8]: Velero 공식 문서, "Customize Installation" (1차·공식). <https://velero.io/docs/main/customize-installation/> · File System Backup <https://velero.io/docs/main/file-system-backup/>

[^9]: Kopia 공식 FAQ 및 CLI 레퍼런스 (1차·공식). <https://kopia.io/docs/faqs/> · <https://kopia.io/docs/reference/command-line/common/policy-set/> · 환경변수 목록 <https://kopia.io/docs/reference/command-line/>

[^10]: Velero 공식 문서, node-agent ConfigMap (1차·공식). <https://velero.io/docs/main/supported-configmaps/node-agent-configmap/>

[^11]: Kubernetes 공식 문서, "Secrets" (1차·공식). <https://kubernetes.io/docs/concepts/configuration/secret/>

[^12]: Kubernetes 공식 API 레퍼런스, Pod v1 (1차·공식). <https://kubernetes.io/docs/reference/kubernetes-api/core/pod-v1/>

[^13]: Kubernetes 공식 튜토리얼, "Connecting Applications with Services" (1차·공식). <https://kubernetes.io/docs/tutorials/services/connect-applications-service/>

[^14]: K3s 공식 문서, "Networking Services" (1차·공식). <https://docs.k3s.io/networking/networking-services>

[^15]: Kubernetes 공식 문서, "CronJob" (1차·공식). <https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/>

[^16]: Elastic 공식 문서, `flattened` 필드 타입 (1차·공식). <https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/flattened>

[^17]: Elastic 공식 문서, "Mapping limit settings" (1차·공식). <https://www.elastic.co/docs/reference/elasticsearch/index-settings/mapping-limit>

[^18]: Elastic 공식 API 레퍼런스, Bulk API (1차·공식). <https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk>
