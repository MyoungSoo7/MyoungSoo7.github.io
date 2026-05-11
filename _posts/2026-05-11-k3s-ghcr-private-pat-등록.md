---
layout: post
title: "K3s 가 ghcr.io 의 private 이미지를 pull 못 할 때 — PAT 등록이 표준"
date: 2026-05-11 20:00:00 +0900
categories: [infra, kubernetes, k3s, ci-cd]
tags: [k3s, ghcr, github-actions, imagepullsecret, registries-yaml, pat]
---

GitHub Actions 가 `ghcr.io/myoungsoo7/dart-analytics:latest` 를 잘 push 했는데, K3s 가 `unauthorized: 403 Forbidden` 으로 pull 못 합니다. "패키지를 public 으로 바꾸면 되는데" 하는 빠른 해결책도 있지만, 운영 클러스터에서는 **Personal Access Token(PAT) 을 K3s 에 등록** 하는 게 표준입니다. 둘의 차이와 K3s 의 docker/containerd 런타임별 등록 방법을 정리합니다.

> 이 글에서 다루는 것
> - 왜 ghcr push 한 이미지가 K3s 에서 unauthorized 인가
> - 빠른 해결책 1: 패키지 public 변경 (간단하지만 보안 X)
> - 빠른 해결책 2: imagePullSecret + dockerconfigjson (잘 안 됨)
> - 표준 해결책: PAT + `/etc/rancher/k3s/registries.yaml` 또는 `docker login`
> - K3s 의 docker runtime vs containerd runtime 차이

---

## 1. 증상 — `unauthorized` 또는 `403 Forbidden`

GitHub Actions 워크플로우가 빌드 후 push 성공:

```
docker push ghcr.io/myoungsoo7/dart-analytics:latest
The push refers to repository [ghcr.io/myoungsoo7/dart-analytics]
...
latest: digest: sha256:abc... size: 1234
```

→ ghcr 에 이미지 올라감 확인. 그러나 K3s 에서 Pod 생성하면:

```
Events:
  Failed to pull image "ghcr.io/myoungsoo7/dart-analytics:latest":
  Error response from daemon: unknown: failed to resolve reference
  "ghcr.io/myoungsoo7/dart-analytics:latest": unexpected status from HEAD
  request to https://ghcr.io/v2/myoungsoo7/dart-analytics/manifests/latest:
  403 Forbidden
```

핵심: **새로 push 된 ghcr 패키지는 기본적으로 private**. 익명 접근 거부됨.

```bash
$ curl -s -o /dev/null -w "%{http_code}\n" \
    https://ghcr.io/v2/myoungsoo7/dart-analytics/manifests/latest
401
```

---

## 2. 빠른 해결책 1 — 패키지를 public 으로 바꾸기

GitHub UI 에서:

1. https://github.com/users/<username>/packages/container/<name>/settings
2. 가장 아래 **Danger Zone** → **Change visibility** → Public

장점: 5초 안 걸림. 인증 설정 없이 K3s 에서 pull 됨.

단점:
- **누구나 이미지 다운로드 가능** (소스 코드는 아니지만 실행 가능한 binary 노출)
- 이미지 안에 환경변수, configmap 같은 게 들어있으면 그것도 같이 노출 위험
- 운영 이미지엔 비추, **테스트/포트폴리오 용에만** 권장

> ⚠️ 함정: 리포지토리 settings 의 visibility 와 **컨테이너 패키지의 visibility 는 별개** 입니다. 리포가 public 이어도 패키지가 private 일 수 있고, 그 반대도 가능.

---

## 3. 빠른 해결책 2 — imagePullSecret (잘 안 되는 이유)

표준 Kubernetes 방식:

```bash
kubectl create secret -n <ns> generic ghcr-pull \
  --from-file=.dockerconfigjson=~/.docker/config.json \
  --type=kubernetes.io/dockerconfigjson
```

```yaml
spec:
  imagePullSecrets:
    - name: ghcr-pull
```

이 방식이 표준이지만, **K3s 의 docker runtime 노드에서는 자주 실패** 합니다:

```
Warning FailedToRetrieveImagePullSecret  kubelet
  Unable to retrieve some image pull secrets (ghcr-pull);
  attempting to pull the image may not succeed.
```

이유: K3s 가 `containerd` 가 아니라 `docker` runtime 을 쓰는 노드에서는 imagePullSecret 의 dockerconfigjson 을 cri-dockerd 가 제대로 못 받습니다.

확인:

```bash
$ kubectl get nodes -o custom-columns=NAME:.metadata.name,RUNTIME:.status.nodeInfo.containerRuntimeVersion
NAME      RUNTIME
lemuel    docker://29.1.1        ← 이런 노드에서 imagePullSecret 안 됨
louise    docker://29.1.3        ← 같음
david     containerd://2.2.2     ← 이건 OK
ilwon     containerd://2.2.3     ← OK
solomon   containerd://2.2.3     ← OK
```

---

## 4. 표준 해결책 — runtime 별로 PAT 등록

### Step 1: PAT 발급

1. https://github.com/settings/tokens/new
2. Note: `k3s-ghcr-pull`
3. Expiration: 1 year (또는 No expiration)
4. 권한: ☑️ **read:packages** (이것만!)
5. Generate token → `ghp_xxxx...`

### Step 2A — containerd 노드: `/etc/rancher/k3s/registries.yaml`

```bash
PAT="ghp_xxxx..."

sudo mkdir -p /etc/rancher/k3s
cat <<EOF | sudo tee /etc/rancher/k3s/registries.yaml
configs:
  ghcr.io:
    auth:
      username: <github-username>
      password: $PAT
EOF
sudo chmod 600 /etc/rancher/k3s/registries.yaml

# K3s agent 재시작 (워커 노드)
sudo systemctl restart k3s-agent
# (또는 control-plane 이면 k3s)
```

> ⚠️ `daemon-reload` 가 필요할 수도 있습니다. systemctl 이 unit file changed 경고를 띄우면 `sudo systemctl daemon-reload` 후 `restart`.

### Step 2B — docker runtime 노드: `docker login`

containerd 와 달리, docker runtime 노드는 호스트 docker daemon 의 인증을 사용:

```bash
echo "$PAT" | sudo docker login ghcr.io -u <github-username> --password-stdin
```

`/root/.docker/config.json` 에 토큰이 저장되고, K3s 가 image pull 할 때 그 인증을 사용합니다.

### Step 3: 검증

```bash
# 다른 노드에서 수동 pull 시도
sudo docker pull ghcr.io/<user>/<image>:latest
# 또는 containerd:
sudo ctr -n k8s.io image pull ghcr.io/<user>/<image>:latest

# K3s Pod 재생성
kubectl delete pod -n <ns> -l app=<app>
# → 새 Pod 자동 생성, pull 성공
```

---

## 5. 한 번에 5 노드 설정 — 스크립트

```bash
#!/bin/bash
PAT="ghp_xxxx..."
USER="myoungsoo7"

NODES=(
  "iamipro@lemuel.example -p [비공개SSH포트]  docker"
  "louise@louise.example          docker"
  "david@david.example            containerd"
  "ilwon@ilwon.example            containerd"
  "solomon@solomon.example        containerd"
)

for entry in "${NODES[@]}"; do
  read -r host runtime <<< "$entry"
  echo "=== $host ($runtime) ==="

  if [ "$runtime" = "docker" ]; then
    ssh "$host" "echo '$PAT' | sudo docker login ghcr.io -u $USER --password-stdin"
  else
    ssh "$host" "sudo mkdir -p /etc/rancher/k3s &&
      cat <<EOF | sudo tee /etc/rancher/k3s/registries.yaml
configs:
  ghcr.io:
    auth:
      username: $USER
      password: $PAT
EOF
      sudo chmod 600 /etc/rancher/k3s/registries.yaml
      sudo systemctl daemon-reload
      sudo systemctl restart k3s-agent"
  fi
done
```

5 노드 5 분 안에 모두 등록.

---

## 6. PAT 보안 주의 사항

1. **권한 최소화**: 오직 `read:packages` 만 체크. 다른 권한 (repo, workflow 등) 절대 X.
2. **rotate 주기**: 1 년에 1 번 재발급 권장. 코드/스크립트에 PAT 가 흘러들어갔으면 즉시 revoke.
3. **노출 시 대처**: 노출되면 https://github.com/settings/tokens 에서 revoke + 새 PAT 발급 + 모든 K3s 노드 갱신.
4. **별도 ssh user**: 호스트 `/root/.docker/config.json` 에 토큰이 평문 저장됨. 노드 root 접근하는 사람이 토큰 볼 수 있음 (의도된 동작).

---

## 7. 정리 — 어느 방법을 쓸 것인가

| 상황 | 방법 |
|---|---|
| 데모/포트폴리오/CI 테스트 | 패키지 **public 변경** |
| 운영 클러스터, 1~2 개 노드 | imagePullSecret (containerd 만이면) |
| 운영 클러스터, 5 노드+ 혼합 runtime | **PAT + registries.yaml/docker login** ⭐ |
| 멀티 클러스터 / 멀티 organization | PAT 를 SOPS 로 암호화 + GitOps |

PAT 방식이 가장 표준. **패키지 visibility 신경 안 써도 됨** + 차트마다 매번 GitHub UI 작업 X.

---

## 다음 글

오늘 K3s 5 케이스 마이그하면서 빠진 함정은 ufw, PAT 외에도 LimitRange ratio 충돌, /actuator/health 404, postgres-secret placeholder 등 여러 개. 다음 글에서 정리합니다.
