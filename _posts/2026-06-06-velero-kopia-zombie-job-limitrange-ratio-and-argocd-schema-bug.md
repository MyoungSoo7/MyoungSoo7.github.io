---
layout: post
title: "Velero Kopia *'실패한 Job' 알람이 풀리지 않은* 진짜 이유 — LimitRange.maxLimitRequestRatio 가 만든 *admission 함정*, 그리고 같은 파일이 ArgoCD root-app 까지 *연쇄 정지* 시킨 *한 줄 스키마 버그*"
date: 2026-06-06 23:50:00 +0900
categories: [sre, kubernetes, postmortem]
tags: [kubernetes, velero, kopia, limitrange, admission-controller, argocd, gitops, postmortem, root-cause-analysis, prometheus]
---

토요일 저녁 7시쯤, 텔레그램으로 *익숙한 형태* 의 알람 3건이 도착했다.

```
[resolved] KubeJobFailed
severity: warning
namespace: velero
Job failed to complete.
Job velero/argocd-default-kopia-9nkv7-maintain-job-1778421891769 failed to complete.
Removing failed job after investigation should clear this alert.
... (× 3, ~5분 간격)
```

*[resolved]* 가 붙어 있어서 *이미 풀린* 알람이다. 그런데 *세 건이 연속* 으로 떴고, 메시지 자체가 *"investigation should clear this alert"* — 즉 *알람이 스스로 풀린 게 아니라 *Velero/Kopia 가 알아서 처리해서 풀린 *것도 아니다*. 무언가가 *실패 → 자동 회복* 의 *형태로 위장* 하고 있다는 *신호*.

결과적으로 이 알람의 진짜 원인을 잡는 데는 *3번의 가설 변경* 이 필요했고, 그 과정에서 *전혀 별개로 보였던 ArgoCD root-app 의 sync 정지* 까지 한 파일이 동시에 일으킨 것을 발견했다. 이 글은 그 *진단 흐름의 *postmortem* — *가설 → 반증 → 진짜 원인* 의 3 단계와, *교과서적인 *Kubernetes admission 함정*, 그리고 *YAML 한 줄 위치* 가 어떻게 *GitOps 전체* 를 멈출 수 있는지에 대한 기록.

---

## TL;DR

**한 줄 요약**

> Velero/Kopia 의 *maintenance Job* 이 *실패한 게 아니라*, 한 달 전에 *한 번 실패한 Job 오브젝트가 *치워지지 않은 채로 *Prometheus 가 *주기적으로 점화·해소* 를 반복하고 있었다.

**왜 실패했나 (한 달 전 그날)**

> velero ns 의 `LimitRange` 가 *memory ratio cap = 2* 인데, *defaults* 가 *limit 512Mi / request 128Mi (ratio 4.0)*. Velero 의 Kopia maintenance Pod 가 *`resources: {}` (명시 X)* 로 들어와서 *LimitRange defaults* 가 적용 → admission controller 가 *ratio 4.0 > 2* 로 *거부*.

**보너스 — 같은 파일이 GitOps 까지 멈췄던 이유**

> 그 차트의 *ArgoCD Application yaml* 이 `spec.syncOptions` 를 *잘못된 위치* 에 두고 있었다 (정확히는 *`spec.syncPolicy.syncOptions`*). ServerSideApply 가 켜진 상태에서 K8s 가 *"field not declared in schema"* 로 거부 → *root-app 자체가 sync Failed* → *다른 변경 사항도 그동안 못 반영*. 같은 차트 삭제로 자연 치유.

**오늘 한 일 (총 4 단계)**

| # | 작업 | 영향 |
|---|------|------|
| 1 | 좀비 Job 4개 삭제 | KubeJobFailed 점화원 제거 |
| 2 | velero ns 의 `LimitRange` 삭제 | 시스템 ns 정책 면제 |
| 3 | 6개 운영 ns 의 `LimitRange.default.memory` 512Mi → 256Mi | ratio 2.0 강제, 잠재 admission 거부 봉쇄 |
| 4 | helm-deploy 에서 velero-local-bsl 차트·앱 제거 PR | root-app sync 정상화, ArgoCD 65 → 64 |

---

## 1. 1차 가설 — *"Kopia maintenance 가 깨졌다"* (틀렸음)

처음 텔레그램 알람을 봤을 때 머릿속에 떠오른 가설은 *교과서적인 것* 들이었다.

| 가설 | 근거 | 확인 명령 |
|------|------|-----------|
| Repo lock 경합 | 이전 maintenance 가 lock 잡고 안 풀어줌 | `kubectl -n velero logs job/... \| grep -i lock` |
| 오브젝트 스토리지 5xx | S3 호환 endpoint 일시 장애 | `kubectl get backupstoragelocation -o wide` |
| OOMKilled | Kopia maintenance 가 메모리 많이 먹음 | `describe pod` 의 reason |
| 자격증명 만료 | IRSA / static key 회전 직후 | velero deployment 로그 |
| BSL Unavailable | BackupStorageLocation 가 잠시 Unhealthy | `kubectl get bsl` |

이 가설들은 모두 *"Kopia 라는 컴포넌트의 *내재적인 *동작* 이 깨졌다"* 는 *전제* 를 공유한다. 알람 메시지에 *"Kopia"*, *"velero"*, *"Job"* 이 적혀 있으니 자연스럽게 그쪽을 의심한다.

**결과: 전부 빗나감.** 클러스터에 들어가 보니 *36 개의 BackupRepository 가 모두 Ready* 였고, *최근 1 시간 내에 maintenance 가 정상 완료* 되어 있었다. *BSL 도 Available*. Kopia 인프라 자체는 *완벽하게 멀쩡* 했다.

**여기서 첫 번째 *진단 함정*:**

> *알람 메시지의 단어 (Kopia, velero, maintain-job)* 가 *원인의 위치* 를 *암시* 하는 것 같지만 — 그건 *대상의 이름* 일 뿐 *원인의 좌표* 가 아니다.

---

## 2. 2차 가설 — *"도구의 거짓말"* (진단을 방해한 진짜 적)

가설을 다시 짜기 전에 *클러스터에 직접 들어가서 확인* 이 필요했다. 그런데 여기서 *예상 못한 함정* 이 등장했다.

```
$ kubectl get nodes
Unable to connect to the server: dial tcp <master>:6443:
  connect: no route to host
```

*no route to host?* 마스터 노드가 죽었나? *그런데 ping 은 정상.* *curl 은 200* 으로 응답한다.

```
$ curl -k -s -w "%{http_code} %{time_total}s\n" \
       -o /dev/null https://<master>:6443/version
401 0.05s
```

*같은 주소* 에 대해 *kubectl 은 EHOSTUNREACH*, *curl 은 200*. 둘 다 *같은 Mac* 에서 도는데 *결과가 다르다*. *재현 100%*.

같은 시각에 ICMP 핑으로 *주변 IP* 들을 훑어 보니 *몇 개가 응답 없음* 으로 나왔고 — *순간적으로 "노드 절반이 다운" 이라는 잘못된 결론* 으로 빠질 뻔했다. 알고 보니 *훑은 IP 범위에 클러스터 노드가 아닌 LAN 의 무관한 호스트* 들이 섞여 있었을 뿐. *시각 도구 (ping 스캔)* 가 *진단 가설에 잘못된 가중치* 를 주는 *전형적인 패턴*.

**여기서 두 번째 *진단 함정*:**

> 도구가 *일관성 없게 거짓말* 할 때, *도구를 신뢰* 하면 *반대 방향* 으로 가설을 짠다.

해법은 *우회 경로* — `~/.kube/config` 의 *client cert* 를 추출해서 *curl 로 직접 API 호출*:

```bash
python3 -c "
import yaml, base64
c = yaml.safe_load(open('~/.kube/config'))
u = c['users'][0]['user']
open('client.crt','wb').write(base64.b64decode(u['client-certificate-data']))
open('client.key','wb').write(base64.b64decode(u['client-key-data']))
open('ca.crt','wb').write(base64.b64decode(c['clusters'][0]['cluster']['certificate-authority-data']))
"

curl -s --cert client.crt --key client.key --cacert ca.crt \
     https://<master>:6443/api/v1/nodes | jq '.items[].metadata.name'
```

*kubectl 이 Go net 의 어떤 캐싱 결함 으로 죽어 있어도, curl 은 그 위에서 정상으로 돌았다.*

---

## 3. 3차 가설 — *진짜 원인은 admission*

curl 로 우회해서 *velero ns 의 events* 를 긁었더니, *제대로 된 단서* 가 한 줄 나왔다 — *2026-05-10 14:24:55 UTC* 의 *warning*:

```
Warning  FailedCreate
Error creating: pods "argocd-default-kopia-9nkv7-maintain-job-...-87klc"
is forbidden:
  memory max limit to request ratio per Container is 2,
  but provided ratio is 4.0
```

*Kubernetes admission controller 가 Pod 생성을 거부한 것*. *Kopia 가 실패한 게 아니다*. *Pod 가 *생성조차 못 됐다*. *Job 컨트롤러* 는 *backoff* 를 다 쓴 뒤 *Failed* 로 표시했고, 그 *Job 오브젝트* 가 *그 후 한 달 동안* 클러스터에 *그대로 남아 있었다*.

### 3.1 LimitRange.maxLimitRequestRatio 의 동작

`LimitRange` 는 *namespace 단위로 Pod 의 resources 를 강제* 하는 정책 오브젝트. *4 가지 영역* 을 정의할 수 있다.

| 필드 | 의미 |
|------|------|
| `max` | 컨테이너 *최대* limit |
| `min` | 컨테이너 *최소* request |
| `default` | *limit 미설정* 시 자동 부여 |
| `defaultRequest` | *request 미설정* 시 자동 부여 |
| `maxLimitRequestRatio` | *limit / request* 비율 *상한* |

이 클러스터의 velero ns 에 박혀 있던 LimitRange `lemuel-default` 는:

```yaml
spec:
  limits:
    - type: Container
      max:        { cpu: 4,     memory: 4Gi    }
      min:        { cpu: 50m,   memory: 64Mi   }
      default:        { cpu: 500m, memory: 512Mi }   # limit 기본값
      defaultRequest: { cpu: 100m, memory: 128Mi }   # request 기본값
      maxLimitRequestRatio: { cpu: 8, memory: 2 }    # ★ ratio 2 상한
```

*문제 조합*:
- 정책상 *memory ratio ≤ 2*
- 하지만 *기본값 ratio* = 512Mi / 128Mi = **4.0**
- 즉 *resources 를 명시하지 않은 Pod 는 자동으로 *정책 위반 상태로 들어옴*

Velero 의 *Kopia maintenance Pod template* 은 `resources: {}` 였다. 그러니 *기본값이 적용 → ratio 4.0 → admission 거부* 라는 *기계적인 결과*.

### 3.2 *그렇다면 왜 새 Job 은 통과하고 있나*?

이 부분이 *가장 헷갈렸다*. 같은 클러스터에서 *지금 다른 BackupRepository 들의 maintenance Job* 은 *전부 성공* 하고 있었다. 즉 *5/10 의 그 사건 이후 *5/10 에 어떤 *조건이 바뀌었다*. 들여다보니:

- 그 사건 이후로 *velero ns 에 새 Job 오브젝트가 생성되지 않았다*.
- 다른 *BackupRepository* 의 *maintenance* 는 *Velero CR 기반 워크플로* 를 통해 처리되고 있었다.
- 즉 *Job 객체로 표면화* 하는 *오래된 경로* 는 *5/10 시점에 깨진 채로 남아 있고*, *새 경로* 는 *완전히 다른 mechanism* 으로 돌아간다.

이건 *컴포넌트 진화의 흔한 패턴* — *옛 경로의 사고가 *새 경로* 와 *분리* 되어 *침묵한다*. *옛 Job 오브젝트만 남아 *알람만 계속 떠오른다*.

### 3.3 Prometheus 가 *깜빡* 였던 이유

`kube_job_failed{}` 메트릭은 *Job 오브젝트가 실패 상태로 존재하면* *값 1* 로 잡힌다. 이 메트릭 위에 얹혀 있던 *KubeJobFailed* 알람 룰이 *for 윈도우* 안에서 *간헐적으로 점화/해소* 를 반복했다. *알람* 입장에서는 *살아있는 사고* 가 아니라 *지속되는 사실* 이었지만, *Prometheus 의 평가 사이클* 과 *alertmanager 의 group_interval* 이 *상태를 출렁이게* 만들었다.

> 이 패턴은 *내가 알아야 할 새로운 mental model* — *알람이 [resolved] 를 반복* 한다는 건 *사고가 일어났다 풀렸다* 가 아니라 *대상이 *영구적으로 깨진 상태로 박혀 있다* 일 가능성.

---

## 4. 수습 — *3 단계 fix*

원인을 잡았으니 fix 는 *간단했다*. *세 단계로 분해* 하면 *재발 방지* 까지 같이 끝난다.

### Step 1 — *좀비 Job 청소*

5/10 의 좀비 Job 4개를 *그대로 삭제*. 이게 *알람 점화원의 직접 제거*.

```bash
kubectl -n velero delete job \
  argocd-default-kopia-9nkv7-maintain-job-1778421891769 \
  argocd-default-kopia-9nkv7-maintain-job-1778422195762 \
  argocd-default-kopia-9nkv7-maintain-job-1778422499870 \
  argocd-default-kopia-9nkv7-maintain-job-1778422803112
```

다음 Prometheus 평가 사이클부터 *kube_job_failed = 0* → 알람 *영구 해소*.

### Step 2 — *velero ns 의 LimitRange 제거*

*시스템 네임스페이스* 에 *프로젝트 정책 LimitRange* 가 들어가 있는 게 *그 자체로 잘못된 결합*. velero 같은 *백업 인프라* 는 *그날그날 다른 형태의 Pod* (maintenance, restore, dataMover) 가 *예측 불가능하게 들어왔다 나간다*. 거기에 *프로젝트용 ratio 정책* 을 박으면 *나중에 또 비슷한 충돌*.

```bash
kubectl -n velero delete limitrange lemuel-default
```

### Step 3 — *나머지 6 ns 의 LimitRange 정규화*

같은 *`lemuel-default`* 가 *운영 6 ns* 에도 *raw kubectl apply* 로 들어가 있었다. *지금은 admission 통과* 하고 있지만, *resources 를 명시 안 한 Pod* 가 *언제든 같은 ratio 4.0 충돌* 에 걸릴 수 있다. *defaults 의 ratio 자체를 2.0 으로 만드는 게 *정책 의도와 정합* 한다.

```yaml
# BEFORE
default:        { memory: 512Mi }   # limit
defaultRequest: { memory: 128Mi }   # request → ratio 4.0  ❌

# AFTER
default:        { memory: 256Mi }   # limit
defaultRequest: { memory: 128Mi }   # request → ratio 2.0  ✅
```

6개 ns 전부 *Python + curl* 로 *get-modify-put* 패치. *kubectl 이 죽어 있는 환경* 에서도 *cert + curl 한 사이클이면 운영 변경 가능* 하다는 것 — 이게 *대안 도구의 가치*.

```python
for ns in 6_namespaces:
    obj = curl_get(f"/api/v1/namespaces/{ns}/limitranges/lemuel-default")
    obj["spec"]["limits"][0]["default"]["memory"] = "256Mi"
    curl_put(f"/api/v1/namespaces/{ns}/limitranges/lemuel-default", obj)
```

---

## 5. *보너스 발견* — 같은 차트가 *GitOps 까지 멈췄던 이유*

여기서 *이야기는 끝* 인 줄 알았는데, *수습 중에 들여다본 ArgoCD apps 목록* 에 *눈에 띄는 미세한 신호* 가 있었다.

```
velero-local-bsl   health=Missing   sync=OutOfSync
```

*Missing* — *ArgoCD 가 기대하는 리소스* 가 *클러스터에 없음*. 보통 *의도된 보류* 거나 *sync 실패* 인데, 이 앱은 *2026-05-27 추가* 후 *10일째 같은 상태*. 들여다보니 *Velero 의 보조 BSL (로컬 HDD MinIO)* 차트로, *credentials 검증 후 활성화* 라는 주석이 박혀 있었다.

운영 BSL 이 이미 *S3 호환 객체 스토리지* 로 정상 작동 중이라 *우선순위에서 밀려난 차트*. *지우는 게 합리적*.

그래서 *helm-deploy 레포에서 PR* 을 만들고 머지했다. 그런데 *root-app 상태를 확인했을 때 발견한 이상한 신호*:

```
root-app  sync=Unknown  rev=bf9b059 (한 commit 전)  lastOp phase=Failed
  msg: failed to create typed patch object (argocd/velero-local-bsl;
       argoproj.io/v1alpha1, Kind=Application):
       .spec.syncOptions: field not declared in schema (retried 5 times)
```

***root-app 가 오늘 새벽부터 sync Failed 로 묶여 있었다.*** 원인은 *내가 지운 그 차트의 ArgoCD Application yaml* 한 줄.

```yaml
# argocd-applications/velero-local-bsl.yaml — *잘못된 위치*
spec:
  destination: { ... }
  # ↓ 여기 위치 잘못됨 ← spec 직속 (잘못)
  syncOptions:
    - CreateNamespace=true
    - ServerSideApply=true
```

`syncOptions` 는 *반드시* `spec.syncPolicy.syncOptions` 아래로 들어가야 한다. *ServerSideApply 가 켜진* 상태에서 K8s 는 *spec.syncOptions 라는 필드 자체* 를 *schema 에 없음* 으로 *typed patch 거부*. 그 거부가 *root-app 의 *sync task* 를 *Failed* 로 만들고, *그 후로 root-app 가 retry → 5회 backoff → 정지*.

즉, *한 줄 위치 오타* 가 *루트 GitOps 컨트롤러를 통째로 정지* 시켰다. *내가 그 차트를 삭제하면서 *자연 치유* 가 일어났고, *force refresh* 로 *몇 분 안에 sync=Synced*.

### *왜 발견하기 어려웠나*

- *root-app 의 health 는 *Healthy 그대로* 였다. *sync 만 *Unknown / Failed*.
- *대시보드 메인 화면* 에서 *health 가 노란불* 만 *시각화* 하면 *놓친다*.
- *operationState.message* 안에 *진짜 단서* 가 들어 있는데, *operation 이 14:48 (UTC) 의 *오래된 timestamp* 라 *눈에 안 들어옴*.

> *GitOps 컨트롤러의 *health 와 sync 는 *독립적* — *health: Healthy* 가 *모든 게 정상* 을 의미하지 *않는다*. *sync: Unknown* + *operation: Failed* 가 *같은 무게의 신호* 다.

---

## 6. 학습 압축 — *다음에 비슷한 알람을 받으면*

이 사건을 *재현 가능한 *체크리스트* 로 압축하면:

### KubeJobFailed 알람 도착 시

1. *알람 message 의 단어* 를 *원인의 좌표로 해석하지 말 것*. *"Kopia maintain job failed"* = *"이름이 Kopia 인 Job 객체가 failed 상태"* 일 뿐.
2. 먼저 *Job 객체의 *생성 시각* 을 *확인*. *24 시간 이내* 면 *실제 컴포넌트 사고* 가능성이 높고, *그 이상* 이면 *좀비* 가능성을 *동등하게 의심*.
3. *describe pod* 또는 *events* 에서 *FailedCreate* 가 보이면 *컴포넌트 사고가 아니라 *admission 사고*. *왜 admission 거부*. LimitRange / ResourceQuota / PSP / OPA 가 흔한 후보.
4. *kube_job_failed 메트릭* 이 *주기적으로 [resolved] 반복* 하면 *좀비 가능성 100%*. *오래된 Job 객체부터 청소*.

### LimitRange 를 새 ns 에 박을 때

1. *maxLimitRequestRatio* 와 *default / defaultRequest 의 ratio* 가 *서로 모순* 되지 않는지 *계산*. *default / defaultRequest > maxLimitRequestRatio* 면 *resources 미설정 Pod 가 자동 위반*.
2. *시스템 / 인프라 ns* (kube-system, velero, ingress 등) 에는 *프로젝트 정책 LimitRange 박지 말 것*. 그 ns 의 Pod 는 *외부 컨트롤러가 자동 생성* 해서 *resources 명세를 신경 못 쓴다*. 정책의 *수혜자가 아니라 *피해자*.

### ArgoCD Application yaml 쓸 때

1. *syncOptions* 는 *반드시* `spec.syncPolicy.syncOptions`. *spec.syncOptions* 가 *문법적으로는 통과* 해도 *ServerSideApply 가 거부*.
2. *root-app 의 health 가 Healthy 라도 *sync 가 Unknown* 이면 *operation 이 Failed* 일 가능성을 *동등하게 의심*. *대시보드의 1차 시각화에 속지 말 것*.
3. *App-of-Apps 패턴* 에서 *자식 yaml 한 줄 오타* 가 *부모를 통째로 정지* 시킬 수 있다는 *blast radius* 를 잊지 말 것.

### *kubectl 이 거짓말할 때*

1. *no route to host* 가 *kubectl* 에서만 떨어지고 *curl 은 200* 이면 *Go net 의 *EHOSTUNREACH 캐싱* 의심.
2. *해법* — `~/.kube/config` 의 *client cert / key / CA* 를 *base64 decode* 해서 *curl --cert / --key / --cacert* 로 *API 직접 호출*. *kubectl 이 회복될 때까지 *block 하지 않는다*.
3. *jq / python* 으로 *응답 파싱* 하면 *kubectl get / describe* 와 *동등한 기능* 을 *한 단계 더 낮은 layer* 에서 수행.

---

## 7. 끝맺음 — *동시 사고의 정합성*

이 사건의 *흥미로운 점* 은 *두 개의 layer 가 서로 다른 면에서* *같은 yaml 파일* 의 *오래된 버그* 에 의해 *동시에 깨져 있었다* 는 것.

| Layer | 깨진 형태 | 같은 yaml 의 어디 |
|-------|-----------|-------------------|
| Workload | velero ns 의 *Job admission 거부* (5/10 사건의 좀비) | velero/lemuel-default LimitRange ↔ maint Pod template |
| GitOps | root-app 의 *sync Failed* (오늘 새벽부터) | argocd-applications/velero-local-bsl.yaml 의 spec.syncOptions 위치 |

*레이어가 분리* 되어 있어 *겉으로는 무관한 두 사고* 처럼 보였지만 — *해결의 매개체* 는 *같은 차트 한 묶음* 이었다. *Workload layer* 의 *좀비 Job* 을 청소하고 *LimitRange 의 ratio* 를 *정규화* 하면서, *GitOps layer* 의 *root-app 정지* 도 *부수효과로 함께* 풀렸다.

> *분산 시스템의 사고는 *한 가지 root cause* 가 아니라 *여러 layer 의 *동시 약점이 만나는 *합성점* 인 경우가 많다*.

오늘 작업 끝낼 무렵의 클러스터 상태:

```
nodes         5/5 Ready
pods          156 Running / 33 Succeeded / 0 problem
argocd apps   64 total / 55 Healthy+Synced
velero ns     jobs=0, limitranges=0
KubeJobFailed 알람                                 영구 해소
root-app                                           Synced + Healthy
```

알람이 *진짜로 풀렸을 때만* *[resolved]* 가 *의미* 를 갖는다는 것 — 그것까지가 *오늘의 학습*.

---

*다음 글:* *admission webhook* 자체의 mental model — *LimitRange / ResourceQuota / OPA Gatekeeper / Kyverno* 를 *언제 무엇으로* 쓸 것인가.
