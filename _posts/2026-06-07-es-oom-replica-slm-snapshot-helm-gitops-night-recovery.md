---
layout: post
title: "ES OOMKilled / SPOF / 백업 부재 — *하룻밤* 안에 production 약점 4 가지를 *진단 → 처방 → 코드 박제* 까지 끝낸 흐름"
date: 2026-06-07 04:50:00 +0900
categories: [kubernetes, sre, gitops]
tags: [elasticsearch, oomkilled, statefulset, immutable-fields, pod-anti-affinity, slm, snapshot-lifecycle-management, minio, helm, argocd, gitops, helm-hook, idempotent, codesign-isolation, sre]
---

봇이 *르무엘 CPU 부하 알림* 을 보낸 새벽 0 시. 단순한 CPU 확인으로 시작한 *production 서비스 점검* 이 *4 가지 약점 동시 발견 → 진단 → 처방 → 검증 → GitOps 코드 박제* 까지 *5 시간 안에* 끝나는 *압축 운영 사이클* 이 됐다. *ES OOMKilled / replica 1 SPOF / 백업 부재 / 런타임-코드 drift* 네 가지를 *순서대로 추적* 한 기록이다.

이 글의 가치는 *각 처방의 성공* 이 아니라 *중간에 부딪힌 함정* 들에 있다. **(1) StatefulSet 의 volumeClaimTemplates 가 immutable 이라 ArgoCD sync 가 락업된 사고**, **(2) ES image 의 config 디렉토리가 layer 그대로라 keystore 가 *매 컨테이너 재시작마다 초기화* 되는 문제**, **(3) 런타임에 손으로 푼 정책이 *코드와 어긋난 상태로 영원히 잊혀지는* GitOps drift 의 위험**. 이 셋이 *오늘 새벽의 진짜 학습* 이었다.

---

## TL;DR

| # | 약점 | 처방 | 함정 |
|---|---|---|---|
| P0 | ES OOMKilled (16h / 6 회) | heap 512m → 768m, mem limit 1Gi → 1.5Gi | — |
| P1 | backend / frontend replica 1 (SPOF) | replica 1 → 2 | — |
| P2 | ES snapshot 백업 없음 | SLM + S3-compatible repo + 자동 정책 | ES image config layer 가 keystore 를 *재시작마다 초기화* |
| P3 | helm chart 와 클러스터 PVC storageClass *drift* | values 정렬 시도 | *STS volumeClaimTemplates 가 immutable* — sync 락업, *롤백 불가피* |

**핵심 발견 1.** `OOMKilled (137)` 는 *JVM heap* 만의 문제가 아님. *Lucene mmap + ES native* 까지 합산해 *컨테이너 memory limit* 을 넘어야 죽는다. 안전 비율은 *heap : limit ≈ 50%* 가 정공.

**핵심 발견 2.** StatefulSet 의 `spec.volumeClaimTemplates.spec.storageClassName` 은 *immutable*. PVC 만 immutable 인 줄 알았는데 *STS template 자체* 도 막혀 있다. *git 한 줄 변경* 이 *ArgoCD 전체 sync 락업* 으로 번질 수 있다.

**핵심 발견 3.** ES 8.x image 의 `/usr/share/elasticsearch/config/` 는 *image layer* — *매 컨테이너 재시작마다 elasticsearch.keystore 가 초기화*. *런타임 keystore add* 는 *재시작 한 번이면 휘발*. *컨테이너 command 오버라이드* 로 매 시작 시 keystore 등록이 *가장 작은 surface* 의 정공.

**핵심 발견 4.** 클러스터에 *손으로 정책을 등록* 하는 순간 *코드와 어긋난다*. 운영 즉시 효과는 좋지만 *재현성 0*. GitOps 의 의미는 *helm install 한 번으로 같은 정책 자동 복원* — 이걸 위해 *post-install Hook Job + 멱등 PUT* 으로 *코드에 박제* 한다.

---

## 0. 시작 — 봇이 던진 한 줄

새벽 0 시, 봇이 알림을 보냈다:

```
⚠️ ServerX
CPU 4코어 Load 6.7
✅ 메모리 4.9GB/31.2GB (16%)
✅ 디스크 121G/394G (33%)
⚠️ CPU 부하 높음: 6.66/4코어
```

*메모리는 16% 만 쓰는데 CPU 부하 6.66 = 코어당 1.66*. *CPU bound*. 봇에 `/탑 ServerX` 를 보내 프로세스 Top 10 을 받았더니 — *K3s control-plane 베이스 부하 + 모니터링 데몬 누수 + iwlwifi IRQ* 가 누적된 *4 코어 노드의 한계*. 그 노드는 *노트북 master* 였다. *etcd 가 노트북 위에서 돈다는 사실 자체* 가 가장 큰 부채.

여기서 시야가 *클러스터 전체 health* 로 넓어졌다. 같은 호스트에 떠 있는 *한 production 서비스 (jen)* 의 상태를 *바로 확인* 했고 — *Spring Boot + ES + frontend* 의 3 컴포넌트 production 이었다. 봇·CPU 알림에서 시작한 *깊이 내려가는* 운영 점검의 시작.

---

## 1. P0 — ES OOMKilled, *heap : limit 비율* 이라는 정공

### 1-1. 발견

```
$ kubectl describe pod settlement-elasticsearch-0 -n jen-prod
Last State:     Terminated
  Reason:       OOMKilled
  Exit Code:    137
  Started:      Sat, 06 Jun 2026 04:45:21 +0900
  Finished:     Sat, 06 Jun 2026 08:36:33 +0900
Ready:          True
Restart Count:  6
Limits:
  cpu:     2
  memory:  1Gi
```

*16 시간 사이 6 회 재시작*. 평균 ~2.7 시간에 한 번. *Exit 137 = SIGKILL by OOMKiller*. 동시에 `kubectl top pod` 의 평상시 사용량:

```
settlement-elasticsearch-0    1022Mi
```

*limit 1Gi 의 99%*. 즉 *평상시 사용량 자체가 한계에 붙어 있다가 Lucene mmap 같은 *순간 증가* 가 일어나면 즉시 OOM*.

### 1-2. 진단

차트의 ES 설정:

```yaml
elasticsearch:
  javaOpts: "-Xms512m -Xmx512m"   # JVM heap
  resources:
    limits:
      memory: 1Gi                  # container limit
```

*heap : limit = 50%* 가 *교과서적 안전선*. 그런데 1Gi 컨테이너에 512m heap 만 줬으니 *비율은 50% 가 맞지만 절댓값이 작다*. ES 는 *heap 외에* :

- *Lucene mmap (off-heap)* — index 가 클수록 커짐
- *ES native code 메모리*
- *thread stack* (수 MB)
- *내부 metadata 캐시*

이 총합이 *heap 의 1 ~ 2 배* 까지 갈 수 있다. *1Gi 컨테이너 + 512m heap* 은 *데이터 1G + 인덱스 약간만* 으로도 즉사한다.

### 1-3. 처방

heap 을 *너무 키우면 container 한계 초과*. limit 을 키우는 게 정공:

```yaml
# values-prod.yaml diff
- javaOpts: "-Xms512m -Xmx512m"
- resources:
-   limits: { memory: 1Gi }
+ javaOpts: "-Xms768m -Xmx768m"
+ resources:
+   limits: { memory: 1536Mi }
```

*heap 768m / limit 1.5Gi = 50% 비율 유지*. 768m heap = 색인 1G 까지 buffer pool + Lucene 작업 충분.

### 1-4. 머지 + 검증

PR 머지 → ArgoCD sync → STS rolling update → 새 pod 떠서 30 분 후 `kubectl top`:

```
settlement-elasticsearch-0    1241Mi    (limit 1536Mi)
```

*1241 / 1536 = 80% 사용*. 마진 295Mi 확보. *Restart count 0* 유지. 2 시간 후도 안정.

---

## 2. 함정 — *StatefulSet volumeClaimTemplates 가 immutable*

P0 PR 본문에 *"PVC immutable 이라 기존 PVC 영향 없음"* 이라고 *낙천적으로 단 한 줄 추가* 한 게 있었다 — `storageClass: local-path → ssd-local`. 클러스터의 실제 PVC 는 이미 *수동으로 ssd-local 로 만들어진 상태* 였고, *helm chart 가 local-path 로 적혀 있어 git ↔ 클러스터 drift* 가 있던 걸 *깔끔하게 정렬* 한다는 의도.

머지 직후 ArgoCD 가 *sync 실패*:

```
StatefulSet.apps "settlement-elasticsearch" is invalid:
spec: Forbidden: updates to statefulset spec for fields other than
  'replicas', 'ordinals', 'template', 'updateStrategy',
  'revisionHistoryLimit', 'persistentVolumeClaimRetentionPolicy'
  and 'minReadySeconds' are forbidden (retried 3 times).
```

*PVC 만 immutable* 이 아니라 **StatefulSet 의 `spec.volumeClaimTemplates` 전체** 가 immutable. *storageClassName 한 단어 변경* 이 *STS 의 허용되지 않은 spec 변경* 으로 판정되어 *전체 sync 락업*.

심각도: *같은 PR 의 ES OOM fix (heap / memory) 도 적용 안 됨*. STS 의 다른 변경까지 *옮겨가지 못함*.

### 즉시 롤백

```yaml
# diff (revert)
- storageClass: ssd-local
+ storageClass: local-path
```

머지 후 ArgoCD *Synced + Healthy* 회복. P0 변경이 그제서야 적용.

### 학습

| 잘못 알고 있었던 것 | 실제 |
|---|---|
| PVC 가 immutable 이니까 helm 의 storageClass 변경은 *git 만 정렬* 된다 | STS 의 volumeClaimTemplates 도 immutable. *helm 변경 자체가 거부* 됨 |
| ArgoCD sync 가 일부 리소스 실패해도 *다른 리소스는 진행* 한다 | retry 후 *전체 sync 실패* 로 떨어지면 *모든 변경 묶음이 적용 안 됨* |

**정공.** STS 의 volumeClaimTemplates 변경은 *kubectl delete sts --cascade=orphan* 으로 *STS 만 삭제* 후 helm install/sync 로 *재생성*. PVC 는 orphan 이라 살아남는다. *별도 작업으로 분리*.

---

## 3. P1 — *replica 1 → 2 의 진짜 의미*

prod values 의 backend / frontend:

```yaml
app:
  replicaCount: 1   # "메모리 절약 위해 1 대로 시작 (스케일 필요시 늘림)"
frontend:
  replicaCount: 1
```

그런데 같은 chart 에는:

- `PodDisruptionBudget { maxUnavailable: 1 }`
- `PodAntiAffinity preferred topologyKey=hostname`
- `RollingUpdate maxSurge=1, maxUnavailable=0`

*replica 1 인 한 이 3 가지가 모두 무의미*. PDB 는 *1 / 1 = 100% 다운* 허용이라 어차피 보호 없음. AntiAffinity 는 *비교 대상이 없음*. RollingUpdate 는 *replica 0 → 1 = 어차피 다운*.

### 변경 한 줄

```yaml
- replicaCount: 1
+ replicaCount: 2
```

frontend 도 동일. *7Mi 만 쓰는 정적 자원* 이라 부담 0.

### 머지 후 자동 분산 확인

```
$ kubectl get pod -n jen-prod -o wide | grep settlement-app
settlement-app-...-2jk6b   Running   david    (방금 떴음, 36s)
settlement-app-...-npkk9   Running   louise   (3 시간 전부터)
```

*preferred antiAffinity 가 의도대로 작동* — 두 pod 가 *다른 노드* (david, louise) 로 분산. 메모리 사용률이 높은 *ilwon 노드 (75%)* 는 *자동으로 피했다*.

### *required 까지 안 간 이유*

`preferred → required` 로 강제하면 *노드 변경 시 schedule 깨질 risk*. 노트북 master → 데스크톱/iDRAC 으로 클러스터 토폴로지 재구성이 임박해 있어, *현재는 preferred 유지* + 노드 안정화 후 *values 토글 + required* 별도 PR.

---

## 4. P2 — SLM Snapshot, 그리고 *ES image config layer* 라는 함정

### 4-1. SLM 이 뭐냐

**Snapshot Lifecycle Management.** Elasticsearch 의 *내장 cron* 같은 것. 사용자가 cron 안 짜도 *ES 가 매일 정한 시간에 스스로 snapshot* 하고 *retention 정책에 따라 자동 삭제*. 외부 백업 인프라 없이 *ES 안에서 백업 자동화* 가 완결.

`PUT _slm/policy/daily-snapshots`:

```json
{
  "schedule": "0 30 2 * * ?",
  "name": "<daily-snap-{now/d}>",
  "repository": "snapshot-repo",
  "config": {
    "indices": ["*"],
    "include_global_state": true
  },
  "retention": {
    "expire_after": "14d",
    "min_count": 7,
    "max_count": 30
  }
}
```

이걸 보장하려면 *snapshot 저장소* 가 있어야 한다. ES 의 S3-compatible repository 가 *가장 표준*. 자가 호스트면 *MinIO*, 외부면 *Cloudflare R2 / AWS S3*.

### 4-2. 저장소 결정 — MinIO 재사용

옵션 비교 시점에서 *클러스터 안에 이미 떠 있는 MinIO* 가 있었다. 다른 도메인의 MinIO 였지만 *bucket 하나 추가* 만으로 재사용 가능.

| 옵션 | 장 | 단 |
|---|---|---|
| 🅐 *재사용 MinIO* + 새 bucket | 5 분 작업, 추가 인프라 0 | 같은 클러스터 사고 시 백업도 함께 잃음 |
| 🅑 *전용 MinIO* | 도메인 분리 깨끗 | 추가 stateful + 디스크 + 노드 부담 |
| 🅒 *외부 (Cloudflare R2)* ★ | *진짜 외부 백업*, 무료 tier 충분 | 외부 가입 + access key 발급 + 도메인 매핑 |

*새벽 4 시 + 클러스터 토폴로지 재구성 예정 + 즉시 효과* 라는 맥락에서 🅐 채택. 🅒 는 *이사 후 iDRAC 셋업 안정화* 시점에 정공으로 마이그레이션.

### 4-3. 함정 — ES image 의 config 디렉토리

S3 자격증명을 ES 에 어떻게 주입하나? ES 8.x 는 *plaintext 환경변수* 거부 — 반드시 **elasticsearch-keystore** (security-hardened 내장 KV store) 사용.

```
$ bin/elasticsearch-keystore add s3.client.default.access_key
$ bin/elasticsearch-keystore add s3.client.default.secret_key
$ curl -XPOST localhost:9200/_nodes/reload_secure_settings
```

*수동으로 한 번 등록하면 끝* — 인 줄 알았다. 그런데 *ES image 의 `/usr/share/elasticsearch/config/` 가 emptyDir / PVC 가 아니라 image layer 그대로 마운트* 되어 있다는 사실을 STS volume 구조 확인 후 발견.

```
$ kubectl get sts settlement-elasticsearch \
    -o jsonpath='{.spec.template.spec.containers[0].volumeMounts}'
[{"mountPath":"/usr/share/elasticsearch/data","name":"data"}]
```

*data 만 PVC, config 는 image layer*. 즉 *컨테이너 재시작마다* `/usr/share/elasticsearch/config/elasticsearch.keystore` 가 *image 기본값으로 초기화*. *내가 손으로 add 한 keystore 가 휘발*.

### 4-4. 정공 옵션 비교

| 옵션 | 작업량 | 위험 |
|---|---|---|
| A. config 를 emptyDir 로 분리 + initContainer 가 image config 복사 + keystore add | 큼 (STS 다중 변경) | 중간 (config 복사 누락 시 ES 부팅 실패) |
| B. RBAC ServiceAccount + Job 이 kubectl exec 로 keystore 추가 | 중 (Role / RoleBinding 추가) | 중 (Job 실행 시점 + ES Ready 동기화 필요) |
| C. *메인 컨테이너 command 오버라이드* — 시작 시 매번 keystore add 후 docker-entrypoint 실행 | *최소* | 낮음 (`-fx` 옵션으로 멱등) |

C 채택:

```yaml
containers:
- name: elasticsearch
  image: ...
  command:
    - sh
    - -c
    - |
      echo "$S3_ACCESS_KEY" | bin/elasticsearch-keystore add -fx s3.client.default.access_key
      echo "$S3_SECRET_KEY" | bin/elasticsearch-keystore add -fx s3.client.default.secret_key
      exec /usr/local/bin/docker-entrypoint.sh eswrapper
  env:
    - name: S3_ACCESS_KEY
      valueFrom: { secretKeyRef: { name: es-snapshot-s3, key: access_key } }
    - name: S3_SECRET_KEY
      valueFrom: { secretKeyRef: { name: es-snapshot-s3, key: secret_key } }
```

핵심:
- `-fx` 옵션 = force overwrite + read from stdin. *기존 값 있어도 안전*
- `exec` = 마지막에 ES image 의 *원래 entrypoint* 그대로 실행 → 다른 부팅 로직 그대로 보존
- *매 재시작마다 매번 실행* — 멱등이라 안전

### 4-5. SLM / Repository 등록의 자동화 — Helm Hook

keystore 가 등록된 다음에는 *ES API 두 번 호출* 로 완성:

1. `PUT _snapshot/<repo>` — S3 repository 메타 등록
2. `PUT _slm/policy/<name>` — 정책 등록

이걸 *helm chart 의 post-install / post-upgrade hook Job* 으로 박는다:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: settlement-es-slm-bootstrap
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "10"
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
spec:
  backoffLimit: 5
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: bootstrap
        image: curlimages/curl
        env:
          - { name: ES_HOST, value: "http://release-elasticsearch:9200" }
          - name: ES_PASSWORD
            valueFrom: { secretKeyRef: { name: ..., key: password } }
        command:
        - sh
        - -c
        - |
          set -e
          AUTH="-u elastic:$ES_PASSWORD"

          # ES Ready 대기
          for i in $(seq 1 30); do
            if curl -fsS $AUTH "$ES_HOST/_cluster/health?wait_for_status=yellow" >/dev/null 2>&1; then
              echo "ES ready"; break
            fi
            sleep 5
          done

          # 멱등 PUT
          curl -fsS $AUTH -H Content-Type:application/json \
            -XPUT "$ES_HOST/_snapshot/$REPO_NAME" -d "{...}"

          curl -fsS $AUTH -H Content-Type:application/json \
            -XPUT "$ES_HOST/_slm/policy/$SLM_POLICY" -d "{...}"
```

- `post-install,post-upgrade`: helm install 또는 helm upgrade 시 한 번 실행
- `hook-delete-policy: hook-succeeded`: 성공 후 자동 삭제 (클러스터에 Job 잔존 X)
- `멱등 PUT`: 이미 등록된 정책과 동일해도 *no-op* 으로 안전

### 4-6. 결과

```
$ curl localhost:9200/_slm/policy/daily-snapshots
{
  "daily-snapshots": {
    "policy": {...},
    "last_success": {
      "snapshot_name": "daily-snap-2026.06.06-...",
      "start_time": 1780773902772
    },
    "next_execution_millis": 1780799400000,
    "stats": { "snapshots_taken": 2, "snapshots_failed": 0 }
  }
}
```

*next_execution = 다음 새벽 02:30*. *자동* 으로 매일 snapshot. *MinIO 의 bucket 에 실제 데이터* (snap-*.dat, meta-*.dat, indices/) 가 *증분 dedup* 으로 저장. *14 일 보관 / 최소 7 개 / 최대 30 개* retention 으로 자동 관리.

---

## 5. *root creds 분리* — svcacct 발급

처음에는 *MinIO root credential* 을 settlement-prod Secret 으로 *복사* 해서 사용했다. *빠른 적용* 의 trade-off. 새벽이긴 했지만 *root 가 settlement-prod 의 Secret 에 평문으로 노출되는 건 분명한 보안 후퇴*. 그래서 즉시 정공으로 진화:

```
$ mc admin user svcacct add <minio-alias> root-user \
    --access-key settlement-snap-prod \
    --secret-key <random>
```

*svcacct (Service Account)* = MinIO 의 *부모 user 정책 inherit + 별도 disposable key*. 부모는 root 그대로지만 *전용 access key* 라 revoke 시 root 영향 0. ES keystore 의 자격을 새 svcacct 로 교체 + reload — *통신 비단절* 로 전환. 새 key 로 snapshot 한 번 더 실행해 *state=SUCCESS* 확인.

---

## 6. GitOps 단일 진실원 — *런타임 등록을 코드로 박제*

오늘의 가장 중요한 메시지. *클러스터에 손으로 정책을 등록하는 순간* — *코드와 어긋난다*. 동작은 잘 한다. 하지만:

- *다른 사람이* `helm template ...` 으로 chart 를 살펴봐도 *snapshot 정책의 존재* 를 모른다
- *클러스터를 갈아엎고* (재해, 이사, K3s 재설치) *helm install* 만 해도 *정책이 자동 복원되지 않는다*
- *변경 이력* 이 *클러스터 안 ES 의 API 응답* 에만 있고 git log 에 없다

GitOps 의 의미는 *"git 만으로 클러스터를 재현"* — 이를 만족시키지 못하면 *반쪽 운영*. 그래서 *런타임에 손으로 등록한 정책* 을 *그대로* helm chart 의 templates 에 박는 마지막 PR 을 만들었다.

머지 후 검증:

```
$ kubectl get app settlement-prod -n argocd \
    -o jsonpath='{.status.sync.status} {.status.health.status}'
Synced Healthy
```

클러스터 상태와 git revision 의 *완전 일치*. 머지해도 *동작 변화 0* (모든 등록이 멱등 PUT 이라 no-op), 하지만 *재현 가능성은 100%*.

---

## 7. *7 가지 교훈*

### 7-1. OOMKilled 의 진단은 *heap 한 변수* 가 아니라 *비율 한 쌍* 이다

`-Xmx` 만 보지 말고 *컨테이너 memory limit* 과 *함께* 봐야 한다. *비율 50%* 가 *Lucene mmap + ES native* 까지 흡수하는 안전선. *heap 만 키우면 limit 초과 → 즉사*, *limit 만 키우면 heap 작아서 GC 폭주*. 둘은 *한 쌍* 이다.

### 7-2. *immutable 필드 목록은 외워야 한다*

StatefulSet 의 immutable 필드:
- `serviceName`
- `podManagementPolicy`
- `selector`
- **`volumeClaimTemplates`**

이 중 하나만 *git 한 줄 변경* 해도 *ArgoCD 전체 sync 락업*. 같은 PR 의 다른 변경까지 *옮겨가지 못한다*. immutable 필드 변경은 *항상 별도 PR + STS 수동 재생성 (orphan delete) + ArgoCD sync* 의 *3 단계 절차*.

### 7-3. *replica 1 인 chart 의 모든 HA 설정은 거짓말*

PDB / antiAffinity / RollingUpdate maxSurge — *replica 1 인 한 모두 무의미*. *replica 를 2 로 올리는 순간* 그제서야 의미가 생긴다. 차트 리뷰 때 *replica 1 옆에 붙은 PDB / antiAffinity* 를 발견하면 *우선 replica 부터 의심* 해야 한다.

### 7-4. *컨테이너 image 의 디렉토리 구조는 *컨테이너 재시작* 에 휘발한다*

ES 의 config 디렉토리처럼 *PVC / emptyDir 분리 안 된 image layer* 안의 파일은 *컨테이너 재시작 한 번이면 사라진다*. *kubectl exec 로 수동 변경한 모든 것* 이 *영원* 하지 않다. *영속화 가 필요한 작업* 은 *항상 컨테이너 부팅 시점에 자동 실행* 되도록 박아야 한다.

### 7-5. *해법의 surface 가 작은 것을 고르라*

ES keystore 자동화 옵션 A (config emptyDir + initContainer) 보다 옵션 C (메인 command 오버라이드) 가 *작은 surface*. 같은 결과를 얻는데 *변경 라인 수가 적은 쪽* 이 *디버깅·롤백 비용이 작다*. 멱등성만 확보되면 *덜 우아한 해법이 정공* 일 때가 많다.

### 7-6. *root creds 를 잠시라도 노출하지 마라*

"빠른 적용" 의 욕심에 root creds 를 다른 namespace 의 Secret 으로 *복사* 하는 순간 *보안 layer 가 한 계단 떨어진다*. 일단 그렇게 풀었다면 *같은 세션 안에서* svcacct / sub-key 로 *교체* 해야 한다. *"내일 분리하겠다"* 는 *대부분 안 분리* 된다.

### 7-7. *runtime 등록은 GitOps 의 부채*

`curl -XPUT _slm/policy/...` 하나가 *코드 없이 운영 효과* 를 낸다. 편리하지만 *git 에 없는 사실* 은 *6 개월 뒤 잊혀진다*. *모든 런타임 등록은 같은 세션 안에서 helm chart 에 박제* 까지가 정공. 그래야 *helm install 한 번* 으로 *클러스터 100% 재현*. 이게 *GitOps 의 진짜 가치*.

---

## 마무리

새벽 0 시 *봇 CPU 알림* 에서 시작해 새벽 5 시 *helm chart 통합 PR 머지* 까지 — *5 시간짜리 운영 진화 사이클* 이었다. *각 처방의 성공* 보다 *중간에 부딪힌 함정* 들이 더 가치 있었다:

- *PVC 만 immutable 이 아니다* — STS 의 volumeClaimTemplates 도 immutable
- *ES image config 디렉토리는 layer 그대로* — keystore 가 *재시작마다 휘발*
- *replica 1 의 HA 설정은 거짓말* — 우선 replica 부터 의심
- *런타임 등록은 GitOps 의 부채* — 같은 세션 안에 helm 에 박제

*"내 컴퓨터인데 내가 모르는 정책이 통신을 끊고 있다"* 던 그제 새벽 [macOS NECP 사례](#) 와, *"내 chart 인데 내가 모르는 immutable 필드가 sync 를 락업한다"* 던 오늘 새벽 STS 사례 — 둘 다 *시스템의 *암묵 규약* 이 내 코드보다 강하다* 는 같은 교훈이다. 운영의 본질은 *그 암묵 규약을 *명시화* 하는 글쓰기* 이고, 이 글이 *6 개월 뒤의 나를 그 함정에서 30 분 일찍 꺼내줄* 것이다.
