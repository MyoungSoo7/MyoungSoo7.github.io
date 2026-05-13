---
layout: post
title: "라이브 patch → Git 영구화 — selfHeal 안전화 운영 패턴 (settlement-staging 11 env 사례)"
date: 2026-05-14 02:00:00 +0900
categories: [infra, kubernetes, gitops, devops]
tags: [argocd, gitops, drift, helm, self-heal, incident, postmortem]
---

장애가 났을 때 `kubectl set env` / `kubectl patch` / `kubectl edit` 으로 즉시 막는 게 운영의 본능입니다. 그런데 GitOps 체제에서 selfHeal 이 켜져 있으면, 그 라이브 변경은 **다음 reconcile 사이클에서 깔끔하게 사라집니다.** 5 분 동안 잘 동작하던 앱이 갑자기 다시 죽기 시작하는, 한 번 겪으면 잊을 수 없는 경험.

이 글은 라이브로 친 변경을 **Git 으로 거꾸로 영구화** 하는 운영 패턴을 정리합니다. 오늘 settlement-staging 환경변수 11 개를 1 시간만에 영구화하면서 정리한 체크리스트와 함정 두 가지를 그대로 공유합니다.

> 이 글에서 다루는 것
> - 왜 라이브 patch 가 생기고, 왜 위험한가
> - 영구화 3 단계 (detect → translate → verify)
> - 오늘 사례: settlement-staging 11 env vars + ES heap/limits/SC
> - immutable 필드 drift 의 selfHeal 잠금 사례 (실전)
> - 영구화하면 안 되는 값 (secrets) 의 분리 처리

---

## 1. 왜 라이브 patch 가 위험한가

운영 중 장애가 났을 때의 자연스러운 흐름:

```
1. 알람이 울린다 → 앱 CrashLoop
2. `kubectl logs` 로 원인 파악 → env 누락
3. `kubectl set env deploy/foo BAR=baz`
4. 5 분 후 앱 정상화
5. "나중에 git 에 박아두자" 라고 메모 (← 함정)
```

이 5 번이 안 박힌 채로 selfHeal=true 가 켜지면 일이 터집니다. ArgoCD 가 git 의 chart 와 클러스터 상태를 비교해서 drift 를 발견 → "git 이 진실" 이라는 GitOps 원칙에 따라 라이브 BAR 환경변수를 **삭제** 합니다. 앱은 다시 CrashLoop.

저는 오늘 이걸 약간 다른 형태로 겪었습니다. settlement-staging 의 selfHeal 을 `true` 로 켰는데, ArgoCD 가 sync 를 영구히 실패시키더군요. 원인은 `StatefulSet.volumeClaimTemplates[*].storageClassName` 이 immutable 필드여서 patch 가 불가능했던 것. 깔끔하게 망가져서 lock-up 상태가 됩니다. 이 사례는 [별도 글](/2026/05/14/argocd-self-management-app-of-apps#5-selfheal-의-함정--immutable-필드-충돌) 5 절에 정리했습니다.

핵심 교훈: **selfHeal 을 켜기 전에 git 과 라이브의 drift 를 0 으로 만들어야 한다.** drift 를 발견하는 즉시 영구화하지 않으면, 나중에 selfHeal 활성화 작업 자체가 사고 트리거가 됩니다.

---

## 2. 영구화 3 단계 패턴

```
[detect]  →  [translate]  →  [verify]
   ↑                              ↓
   └──── close the loop ──────────┘
```

### 2.1. detect — 모든 라이브 patch 흔적 찾기

체계적으로 찾는 방법 3 가지:

```bash
# (1) git 차트의 chart-rendered 결과와 라이브 deploy 의 spec 비교
helm template charts/settlement -f values.yaml -f values-staging.yaml \
    > /tmp/chart.yaml
kubectl get -n settlement-staging deploy,sts,svc,ingress,cm,secret -o yaml \
    > /tmp/live.yaml
diff /tmp/chart.yaml /tmp/live.yaml | less

# (2) ArgoCD UI 의 OutOfSync 표시 — 가장 빠름
kubectl get app -n argocd settlement-staging \
    -o jsonpath='{.status.resources[?(@.status=="OutOfSync")]}'

# (3) Application 의 conditions — 어떤 필드가 immutable 충돌인지
kubectl get app -n argocd settlement-staging -o yaml | grep -A5 conditions
```

오늘 사례에서 ArgoCD UI 가 "Deployment settlement-staging-app — OutOfSync" 로 잡아준 게 시작이었습니다. UI 클릭 → DIFF 탭 → 한 화면에 모든 drift 가 보입니다.

```diff
                                  spec.template.spec.containers[0].env:
                                  - name: SPRING_PROFILES_ACTIVE
                                    value: staging
                                  - name: SPRING_DATASOURCE_URL
                                    value: jdbc:postgresql://...
+                                 - name: SPRING_DATASOURCE_USERNAME
+                                   value: settlement
+                                 - name: SPRING_DATASOURCE_PASSWORD
+                                   value: CHANGEME-via-sops
+                                 - name: JWT_TTL_SECONDS
+                                   value: "86400"
+                                 - name: APP_JWT_SECRET
+                                   value: ...32+ bytes...
+                                 - name: SPRING_JPA_HIBERNATE_DDL_AUTO
+                                   value: update
+                                 - name: TOSS_SECRET_KEY
+                                   value: staging-toss-placeholder-key
+                                 - name: TOSS_CLIENT_KEY
+                                   value: staging-toss-placeholder
+                                 - name: KAKAO_REST_API_KEY
+                                   value: staging-placeholder
+                                 - name: GOOGLE_CLIENT_ID
+                                   value: staging-placeholder
+                                 - name: GOOGLE_CLIENT_SECRET
+                                   value: staging-placeholder
```

11 개 env. 라이브에는 있고 chart 가 만든 Deployment 에는 없음. 이 11 개가 git 으로 들어가야 selfHeal 이 안전합니다.

### 2.2. translate — chart 구조에 맞게 번역

이 단계가 가장 중요합니다. 단순히 환경변수를 추가하는 게 아니라, **chart 의 추상화 레이어에 맞게 번역** 해야 합니다.

settlement chart 의 app.yaml 템플릿은 이렇게 생겼습니다.

```yaml
env:
  - { name: SPRING_PROFILES_ACTIVE, value: {{ .Values.app.springProfile | quote }} }
  - name: SPRING_DATASOURCE_URL
    value: jdbc:postgresql://...
  - { name: SPRING_ELASTICSEARCH_URIS, value: "..." }
  # ... 고정 env ...
  {{- range $k, $v := .Values.app.extraEnv }}
  - name: {{ $k }}
    value: {{ $v | quote }}
  {{- end }}
```

`app.extraEnv` 라는 dict 를 통해 추가 env 를 주입할 수 있는 구조입니다. 11 개 env 를 그냥 app.yaml 템플릿에 직접 추가하면 안 됩니다. chart 가 다른 환경 (prod/staging) 에서 다르게 동작해야 하니까, **values-staging.yaml 의 extraEnv 에 추가** 해야 합니다.

```yaml
# values-staging.yaml
app:
  replicaCount: 1
  springProfile: staging
  resources:
    requests: { cpu: 200m, memory: 512Mi }
    limits:   { cpu: 1000m, memory: 768Mi }
  # 라이브 patch 영구화 — selfHeal=true 안전화 (2026-05-14)
  # placeholder 들은 staging 용 더미값. prod 는 envFromSecret 사용.
  extraEnv:
    SPRING_DATASOURCE_USERNAME: settlement
    SPRING_DATASOURCE_PASSWORD: CHANGEME-via-sops
    SPRING_JPA_HIBERNATE_DDL_AUTO: update
    JWT_TTL_SECONDS: "86400"
    JWT_SECRET: settlement-staging-jwt-secret-key-must-be-at-least-32-bytes-long-for-hmac-sha256
    APP_JWT_SECRET: settlement-staging-jwt-secret-key-must-be-at-least-32-bytes-long-for-hmac-sha256
    TOSS_SECRET_KEY: staging-toss-placeholder-key
    TOSS_CLIENT_KEY: staging-toss-placeholder
    KAKAO_REST_API_KEY: staging-placeholder
    GOOGLE_CLIENT_ID: staging-placeholder
    GOOGLE_CLIENT_SECRET: staging-placeholder
```

여기서 중요한 디테일:

**디테일 1 — 환경별 분리 유지.** prod 는 `envFromSecret: settlement-app-env` 패턴을 쓰고 있어서 extraEnv 가 비어있습니다. staging 만 extraEnv 를 채웁니다. chart 자체는 안 건드리고 values 만 환경별 다르게 갑니다.

**디테일 2 — placeholder 처리.** `staging-toss-placeholder-key` 같은 값은 보안적으로 git 에 박혀도 됩니다 (실제 토스 키가 아니니까). 진짜 시크릿이면 Sealed Secrets / SOPS 로 가야 합니다 (다음 절 참조).

**디테일 3 — quote 처리.** `JWT_TTL_SECONDS: "86400"` 의 따옴표가 필수입니다. extraEnv 가 문자열을 기대하는데 숫자로 넣으면 Helm 이 `value: 86400` 으로 렌더링하고, Deployment 가 invalid (env value 는 string 만) 가 됩니다. 잘 안 보이는 함정.

### 2.3. verify — helm template 으로 검증 후 push

git push 전에 차트 결과물이 라이브와 일치하는지 확인해야 합니다.

```bash
helm template charts/settlement \
  -f charts/settlement/values.yaml \
  -f charts/settlement/values-staging.yaml \
  | grep -E "JWT_TTL|TOSS_SECRET|storageClassName|Xmx768m"
```

기대 출력:

```
- name: JWT_TTL_SECONDS
- name: TOSS_SECRET_KEY
- { name: ES_JAVA_OPTS, value: "-Xms768m -Xmx768m" }
storageClassName: solomon-local
storageClassName: solomon-local
```

이 단계를 안 하고 push 했다가 chart 가 다른 결과를 내서 sync 가 또 실패한 경우, 디버깅 시간이 2 배가 됩니다.

push 후 ArgoCD 에서 수동 sync 트리거:

```bash
kubectl patch -n argocd app settlement-staging --type merge \
  -p '{"operation":{"sync":{"revision":"master"}}}'
```

자동 sync 가 켜져있어도 3 분 정도 reconcile 사이클을 기다리기 싫으면 이걸로 즉시.

---

## 3. 오늘 사례 — settlement-staging full audit

세 종류의 drift 가 한꺼번에 있었습니다.

### Drift A — Deployment env 11 개 (mutable, 처리 쉬움)

위 2.2 절에서 정리한 11 개 env. extraEnv 에 모두 박아넣고 commit.

### Drift B — StatefulSet ES heap + resources (mutable)

```diff
- name: ES_JAVA_OPTS
-  value: "-Xms256m -Xmx256m"
+  value: "-Xms768m -Xmx768m"

resources:
-  requests: { cpu: 200m, memory: 384Mi }
-  limits:   { cpu: 1000m, memory: 512Mi }
+  requests: { cpu: 100m, memory: 1Gi }
+  limits:   { cpu: 1000m, memory: 1500Mi }
```

elasticsearch 가 256m heap 으로는 startup 도 못 했어서 라이브에서 768m 으로 올린 흔적. chart 의 `values-staging.yaml > elasticsearch` 섹션에 그대로 반영.

### Drift C — StatefulSet storageClassName (immutable, 함정)

```diff
volumeClaimTemplates:
  - metadata: { name: data }
    spec:
      accessModes: [ReadWriteOnce]
-     storageClassName: local-path
+     storageClassName: solomon-local
```

이게 immutable 필드입니다. ArgoCD 가 patch 시도 → 영구 실패 → selfHeal 잠금.

해결: chart 의 values 가 라이브 값과 일치하도록 만듭니다.

```yaml
# values-staging.yaml
elasticsearch:
  storage: 3Gi
  storageClass: solomon-local   # ← 라이브와 일치, drift 0
  javaOpts: "-Xms768m -Xmx768m"
  resources:
    requests: { cpu: 100m, memory: 1Gi }
    limits:   { cpu: 1000m, memory: 1500Mi }
```

이러면 ArgoCD 의 desired state 가 라이브와 정확히 같으므로 patch 시도 자체가 안 일어납니다. **selfHeal 잠금 해제.**

원래는 chart 가 `local-path` 였는데, 어제 solomon 노드에서 disk 이전하면서 volumeClaimTemplates 의 SC 를 라이브에서 갈았던 흔적. 24 시간 동안 git 에 안 박혀있던 거.

세 종류 drift 를 한 커밋에 영구화: [a4c3d31](https://github.com/MyoungSoo7/helm-deploy/commit/a4c3d31). 18 줄 추가, 3 줄 삭제.

---

## 4. 영구화하면 안 되는 값 — 진짜 secrets

위 11 개 env 중 `staging-toss-placeholder` 같은 건 git 박아도 됩니다 — 더미니까. 그런데 prod 에 같은 작업을 한다면 진짜 토스 secret key 가 라이브에 patch 되어 있을 겁니다. 그걸 git 에 박으면 안 됩니다.

3 가지 분리 패턴:

| 패턴 | 용도 | git 보관 형태 |
|---|---|---|
| extraEnv 평문 | staging placeholder, public config | values-staging.yaml 평문 |
| envFromSecret | 진짜 secrets, prod | Secret name 참조만 git, Secret 실체는 클러스터 |
| Sealed Secrets / SOPS | secrets 도 git 으로 추적 | 암호화된 형태로 git, 클러스터에서 복호화 |

settlement chart 는 prod 용으로 envFromSecret 패턴을 이미 갖고 있습니다.

```yaml
# values-prod.yaml
app:
  envFromSecret: settlement-app-env   # 이 이름의 Secret 이 별도로 클러스터에 있음
  extraEnv: {}                         # prod 는 비움
```

```yaml
# templates/app.yaml
{{- if .Values.app.envFromSecret }}
envFrom:
  - secretRef:
      name: {{ .Values.app.envFromSecret }}
{{- end }}
```

Secret 자체는 클러스터에 `kubectl create secret generic settlement-app-env --from-literal=KEY=value` 로 직접 만들고, git 에는 secret name 만 들어갑니다. selfHeal 이 envFrom 블록만 보장하고, Secret 의 내용은 별도 관리 (사람이 sops 로, 또는 External Secrets Operator 로 vault 에서 동기화).

이 글에서는 staging 케이스라 평문 placeholder 로 끝났지만, prod 였다면 envFromSecret 으로 분리하는 게 정답입니다.

---

## 5. 영구화 체크리스트

운영 노트로 정리한 1 페이지 체크리스트:

```
[ ] kubectl get / argocd diff 로 drift 전부 나열
[ ] drift 분류:
    - mutable env/resources/probe → values 의 적절한 키로 번역
    - immutable spec (STS VCT, PV/PVC bind) → 라이브가 진실, git 을 라이브로 맞춤
    - 진짜 secrets → envFromSecret / Sealed Secrets 분리
[ ] helm template 결과가 라이브와 일치하는지 grep 검증
[ ] commit + push
[ ] argocd app sync 트리거
[ ] argocd app 의 sync.status == "Synced" 확인
[ ] selfHeal=true 로 flip (이제 안전)
[ ] 며칠 후 다시 OutOfSync 안 났는지 확인 → 진짜 영구화
```

마지막 2 단계가 중요합니다. selfHeal 을 켠 직후엔 안 보이던 drift 가 나중에 발견될 수 있어서, 며칠 운영해보고 OutOfSync 안 뜨는 걸 확인해야 진짜 영구화 완료.

---

## 6. 결론 — drift 는 부채, 영구화는 상환

라이브 patch 자체는 운영의 현실이고 막을 수 없습니다. 장애가 나면 즉시 막아야 하고, 즉시 git 으로 가는 변경은 너무 느립니다 (PR + review + merge + ArgoCD sync = 30 분). `kubectl patch` 5 초가 합리적입니다.

문제는 **그 변경을 갚지 않고 쌓아두는 것** 입니다. 한 달 동안 라이브 patch 가 30 건 쌓이면, 어느 날 selfHeal 켜자고 마음먹은 순간 30 건의 drift 와 immutable 필드 충돌과 secret 분리 결정이 한꺼번에 닥칩니다.

저는 이제 **라이브 patch 친 직후 동일 세션에서 git PR 까지 올리는 규칙** 으로 운영합니다. 운영 노트에 "TODO: env 11 개 git 영구화" 라고 적어두지 않습니다. 적어두면 영원히 미뤄집니다. 패치 즉시 PR 까지 푸시.

이 글의 원래 목적이 ArgoCD 셀프 관리에서 selfHeal 활성화하는 거였는데, 활성화 작업이 곧 영구화 작업이라는 걸 오늘 settlement-staging 에서 다시 확인했습니다. selfHeal 은 단순한 플래그가 아니라 **drift 부채를 0 으로 만들었다는 선언** 입니다.

다음 글에서는 staging-jen 환경 부활 후기 — settlement-staging 을 0 replicas 에서 1 시간만에 살린 디버깅 일지를 다룰 예정입니다. 오늘 영구화 작업의 원인이 되었던 부활 작업의 회고입니다.
