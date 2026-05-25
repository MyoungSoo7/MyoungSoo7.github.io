---
layout: post
title: "bitnami/kubectl 이 Docker Hub 에서 사라진 사건 + *미봉책의 수명* — pod-restart-cleanup CronJob 폐기 회고"
date: 2026-05-26 03:00:00 +0900
categories: [infra, kubernetes, ops]
tags: [bitnami, docker-hub, cronjob, kubectl, k3s, gitops, argocd, postmortem]
---

`pod-restart-cleanup` 이라는 CronJob 이 `ImagePullBackOff` 였다. 5월 초까지는 잘 도는 CronJob 이었는데 어느 날부터 *이미지를 찾을 수 없다고* 한다. 디버깅을 시작하기 직전에 잠시 멈추고 *''이 CronJob 이 왜 존재했지?''* 라고 물어보니, *그 존재 이유가 이미 사라졌다*는 사실을 깨달았다. *수정* 이 아니라 *폐기* 가 정답인 케이스였다.

이 글은 *짧다* — 사건 자체는 작지만 *교훈* 은 일반적이다.

---

## TL;DR

| 항목 | 내용 |
|---|---|
| 직접 원인 | `bitnami/kubectl:1.31` 이미지가 Docker Hub 에서 *제거됨* (Bitnami 가 2026-05 부터 free image 회수) |
| 즉시 해법 | 이미지 변경 (`rancher/kubectl:v1.31.0` 또는 `alpine/k8s:1.31.1`) |
| 결정 | **CronJob 자체 폐기**. 존재 이유 (ECK operator restart 폭주) 가 *근본 해결됨* |
| 효과 | helm-deploy 레포에서 `cluster-ops/pod-restart-cleanup.yaml` 파일 삭제 → ArgoCD `prune:true` 가 cluster 에서 자동 제거 |

---

## 1. 증상

```bash
$ kubectl get pods -n kube-system | grep restart-cleanup
pod-restart-cleanup-29656157-52rs6   0/1   ImagePullBackOff   0   11m
```

```bash
$ kubectl describe pod pod-restart-cleanup-29656157-52rs6 -n kube-system | grep -A2 Events:
Warning  Failed   8m25s   kubelet
  Failed to pull image "bitnami/kubectl:1.31": rpc error: code = NotFound
  desc = failed to pull and unpack image "docker.io/bitnami/kubectl:1.31":
  failed to resolve reference "docker.io/bitnami/kubectl:1.31":
  docker.io/bitnami/kubectl:1.31: not found
```

`not found` — *이미지 자체가 registry 에 없다*. *''pull 실패''* 가 아니라 *''존재하지 않음''*.

---

## 2. 배경 — *Bitnami free image 회수 사건* (2026-05)

Bitnami (VMware 산하) 가 2026-05-01 부터 *공개 무료 컨테이너 이미지* 의 상당수를 *Bitnami Premium* 으로 옮겼다. `docker.io/bitnami/<name>:<version>` 의 *수많은 태그* 가 *동시에 404*. 영향:

- `bitnami/kubectl:*` — 거의 모든 minor 태그
- `bitnami/nginx:*`, `bitnami/postgresql:*`, `bitnami/redis:*` — 다수
- 새 태그는 `bitnamilegacy/...` 또는 *Premium subscription* 필요

당시 *수많은 helm chart* 가 *bitnami 이미지를 기본값* 으로 썼기 때문에 *helm 의존성 트리* 전체에서 *동시에* `ImagePullBackOff` 가 발생.

> *교훈 1*: *third-party 이미지 의존* 은 *대규모 비대칭 위험* 이다. *벤더 정책 변경 1 회* 가 *수만 클러스터에 동시 영향*. mirror 또는 vendored copy 가 필수.

---

## 3. *''왜 이 CronJob 이 있었지''* — 존재 이유 재확인

`pod-restart-cleanup` 의 정의 (요약):

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pod-restart-cleanup
  namespace: kube-system
spec:
  schedule: "@hourly"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: kubectl
            image: bitnami/kubectl:1.31
            command: [sh, -c]
            args:
              - |
                kubectl get pods -A -o json | python3 -c "
                # restart count > 200 인 pod 찾기
                import json, sys
                THRESHOLD = 200
                data = json.load(sys.stdin)
                for p in data['items']:
                    rc = sum(cs.get('restartCount', 0)
                             for cs in p.get('status', {}).get('containerStatuses', []))
                    if rc > THRESHOLD:
                        print(f\"{p['metadata']['namespace']}/{p['metadata']['name']}\")
                " | xargs -I {} kubectl delete pod {} --namespace $(echo {} | cut -d/ -f1)
```

요약: *''restart count 가 200 을 넘은 pod 를 매시간 강제 재생성''*. 왜?

git blame 확인:

```
ad58b3f  2026-05-12  ECK operator 406회 재시작 — kubelet alert 가 너무 시끄러워서
                     restart count 가 큰 pod 를 주기적으로 cleanup.
```

*ECK operator 가 leader election lease 갱신 실패로 8분마다 자기 종료를 반복* 하던 사건의 *증상 완화책*. *근본 원인* 은 *leader election timeout* 이었고, 그건 *2026-05-21* 에 `--leader-election-lease=30s` 패치로 해결됐다.

즉:
- 2026-05-12: 증상 완화책 도입 (CronJob)
- 2026-05-21: 근본 원인 해결 (lease 패치)
- 2026-05-25: bitnami 이미지 사라짐 → CronJob 깨짐

*''잘못된 이미지''* 가 알람 보낸 게 *역설적으로 도움* — 그 알람이 *이 CronJob 의 존재가 더 이상 필요 없다는 사실* 을 다시 보게 했다.

---

## 4. 폐기 결정

세 가지 옵션을 평가:

**옵션 A — 이미지 교체**

`alpine/k8s:1.31.1` 로 바꾸면 됨. sh + kubectl + jq 다 포함. python3 코드를 jq 로 다시 쓰면 작동.

```yaml
image: alpine/k8s:1.31.1
args:
  - |
    kubectl get pods -A -o json |
    jq -r '.items[] | select(
      [.status.containerStatuses[]?.restartCount // 0] | add > 200
    ) | "\(.metadata.namespace) \(.metadata.name)"' |
    xargs -L1 kubectl delete pod -n
```

장점: *동작 유지*. 단점: *불필요한 코드 유지보수*.

**옵션 B — `rancher/kubectl:v1.31.0`**

이미 다른 CronJob (eck-leader-elect-patch) 에서 사용 중. *그 CronJob 은 distroless 라 `sh` 가 없어서* 추가 작업 필요. *python3* 도 없음. *불편*.

**옵션 C — CronJob 폐기**

*가장 단순*. *근본 원인 해결됨* → *증상 완화책 불필요*.

선택: **C**.

> *교훈 2*: *증상 완화책의 수명* 은 *''근본 원인 해결될 때까지''* 다. 근본 원인이 해결됐는데도 *습관처럼* 유지되는 미봉책은 *코드 부채*. 사라진 이유가 사라졌으면 *코드도 사라져야* 한다.

---

## 5. 폐기 절차 — ArgoCD `prune:true` 의 우아함

`cluster-ops` ArgoCD app 의 sync 정책:

```yaml
spec:
  syncPolicy:
    automated:
      prune: true       # ← git 에서 사라진 리소스 자동 삭제
      selfHeal: true
```

`prune:true` 덕분에 *git 에서 파일을 지우면* ArgoCD 가 자동으로 *클러스터에서도 삭제*. *수동 `kubectl delete cronjob` 불필요*.

```bash
$ cd /Users/lms/helm-deploy
$ git rm cluster-ops/pod-restart-cleanup.yaml
$ git commit -m "$(cat <<'EOF'
chore: pod-restart-cleanup CronJob 폐기

ECK leader-election lease 패치(25s)로 restart count 폭주 근본 원인 해결됨.
이 CronJob 은 증상 완화책이었고, bitnami/kubectl:1.31 이미지가
Docker Hub 에서 사라져 ImagePullBackOff 상태였음. 더 이상 필요 없음.
EOF
)"
$ git push
```

```bash
$ kubectl -n argocd patch application cluster-ops --type merge \
    -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
# ~30 초 후
$ kubectl -n kube-system get cronjob pod-restart-cleanup
Error from server (NotFound)
$ kubectl -n argocd get application cluster-ops
NAME          SYNC STATUS   HEALTH STATUS
cluster-ops   Synced        Healthy
```

GitOps 가 *원래* 의도한 그림 — *git 이 truth 다. 클러스터는 git 을 따라간다*. 수동 `delete` 가 *''ArgoCD 가 self-heal 로 다시 만들지 않을까''* 같은 *방어적 사고* 없이도 안전.

---

## 6. 일반화 — *미봉책 폐기 루틴*

홈랩이든 production 이든, 미봉책은 *주기적으로 폐기 가능성을 검토* 해야 한다. 체크리스트:

1. **존재 이유** — git blame / commit message 에서 *왜 이 코드가 추가됐는지* 확인. 이유 없는 코드는 *그 자체로 의심*.
2. **근본 원인 해결 여부** — 도입 당시의 *상황* 이 *지금도 유효* 한지. 모니터링 알람의 임계치, 운영 환경, 의존성 등.
3. **삭제 시 영향** — 폐기했을 때 *''뭐가 튀어 나오는지''*. 영향 없으면 폐기, 있으면 *대체 메커니즘* 확인.
4. **점진적 폐기** — *비활성화 → 1 주 모니터링 → 삭제* 의 단계. 갑자기 지우는 것보다 *없어도 됨* 을 시간으로 증명.

이번 케이스는 4 번을 생략했다 — *''bitnami 가 이미 1 주 동안 폐기시켰음''* 이라는 *자연 실험* 이 이미 진행됐고, 그동안 *문제 없었음* 이 확인됐기 때문.

---

## 7. 마무리

*''이미지가 사라졌으니 다른 이미지로 갈자''* 가 자연스러운 첫 반응이다. 하지만 *''사라져서 알람이 떴다''* 가 *''이 코드가 필요한가''* 라는 질문을 *공짜로* 가져온다. *그 질문에 답하는 게 수정보다 빠를 때도 있다*.

작은 미봉책일수록 잊혀지기 쉽다. *큰 미봉책은 무게 때문에 정기적으로 review 되지만, 작은 CronJob, 짧은 if-branch, 작은 bash one-liner 는 ''존재 자체를 잊혀'' 영원히 살아남는다*. 그래서 *''image 가 사라졌다는 알람''* 같은 *외부 이벤트* 가 *''이거 필요한가''* 를 묻는 좋은 트리거가 된다.

이번 사건의 *진짜 효과* 는 `cluster-ops` ArgoCD app 이 *Degraded → Healthy* 로 바뀐 것이다. 어제부터 며칠째 Degraded 였던 게, *원인 (사라진 이미지) 을 알고도 ''고친다''* 가 아닌 *''필요 없으니 삭제''* 라는 더 단순한 답으로 풀렸다.

---

> 작성: 2026-05-26. 환경: ArgoCD 2.16.1, K3s v1.35.4, helm-deploy 레포 master 브랜치. 관련 PR: helm-deploy `a2d2933` — *''chore: pod-restart-cleanup CronJob 폐기''*.
