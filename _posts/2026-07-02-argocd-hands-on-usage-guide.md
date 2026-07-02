---
layout: post
title: "ArgoCD 실전 사용 가이드 — GitOps 의 얼굴, *클릭 3 번 으로 배포·롤백·삭제*"
date: 2026-07-02 17:40:00 +0900
categories: [devops, argocd, gitops, kubernetes]
tags: [argocd, gitops, kubernetes, helm, image-updater, sops, deploy, rollback]
---

내 6 노드 K3s 클러스터 는 *55 개 앱* 이 *모두 ArgoCD 로 관리* 된다. *helm CLI 를 직접 치는 일 은 거의 없음* — *운영 의 90%* 는 *ArgoCD UI 클릭 3 번* 으로 끝. 이 글 은 *ArgoCD 의 실전 사용법* + *`codingtest-prod` 앱 을 예시* 로 *tree view / sync / diff / rollback / delete* 를 *실 스크린샷 과 함께* 정리.

![ArgoCD UI - codingtest-prod tree view](/assets/images/argocd/argocd-codingtest-tree.jpg)

---

## 1. ArgoCD 가 *무엇 을 해결* 하는가

**전통 적 배포**:
```bash
$ helm upgrade myapp charts/myapp -n prod --values values-prod.yaml
$ kubectl get pods -n prod
$ kubectl logs -n prod deploy/myapp
$ helm rollback myapp 3 -n prod   # 롤백
```

**문제**:
- *누가 언제 뭘 배포 했는지* 추적 어려움
- *cluster 상태* 와 *git 상태* 가 어긋 나면 감지 못 함
- *신입 이 kubectl 배우기 부담*

**ArgoCD 의 답 (GitOps)**:
- **git = 진리 의 소스**. 배포 = *git commit + push*
- ArgoCD 가 *git 을 폴링* (기본 3분) → *cluster 와 diff* → *자동 or 수동 sync*
- **모든 변경 이 git log 에 기록** — 감사 자동
- **웹 UI** 로 배포 상태 시각화

---

## 2. 로그인 + 첫 화면

**URL**: `https://argocd.lemuel.co.kr` (또는 자신 의 도메인)

**초기 계정**:
```bash
Username: admin
Password: kubectl get secret -n argocd argocd-initial-admin-secret \
    -o jsonpath='{.data.password}' | base64 -d
```

*로그인 즉시 비밀번호 변경 + Vaultwarden 같은 password manager 에 저장 권장*.

**첫 화면** — *Applications* 대시보드. 55 개 앱 이 *tile* 로 배치. 각 tile 은:
- **App Health** — 🟢 Healthy / 🟡 Progressing / 🔴 Degraded / ⚫ Suspended / ⚪ Missing / ❓ Unknown
- **Sync Status** — 🟢 Synced / 🟡 OutOfSync

---

## 3. Application 상세 — *tree view 의 의미*

위 스크린샷 의 *`codingtest-prod`* app 예시:

```
[App]
 └─ codingtest-prod (Application CRD)
     ├─ codingtest-data       (PVC — 영속 스토리지)
     ├─ codingtest-app        (Service — 네트워크 endpoint)
     └─ codingtest-app        (Deployment)
         ├─ codingtest-app-6954589db8   (ReplicaSet, rev.6 ← 현재)
         │   └─ codingtest-app-6954589db8-...  (Pod, running 1/1)
         ├─ codingtest-app-c85c6fb8f    (ReplicaSet, rev.5 — 옛)
         ├─ codingtest-app-6b4979d748   (ReplicaSet, rev.4)
         ├─ codingtest-app-5ccdcd6567   (ReplicaSet, rev.3)
         └─ codingtest-app-969f7fcd8    (ReplicaSet, rev.1)
```

**핵심 이해**:
- **App = 최상위 부모** — Application CRD (custom resource)
- **PVC / Service / Deployment** — Kubernetes 표준 리소스
- **ReplicaSet 5 개** — 옛 배포 이력. 새 image push 마다 새 ReplicaSet 생성 + 옛 것 은 replicas=0 로. **rollback 시 즉시 사용 가능**
- **Pod** — 실제 컨테이너 (1개 만 running)

**아이콘 뜻**:
- 💚 하트 = 리소스 Healthy
- ✔️ 체크 = git 과 sync 됨

---

## 4. 상단 상태 바 (Screenshot 의 최상단)

```
APP HEALTH: 💚 Healthy
SYNC STATUS: ✅ Synced to master (479aae1)
LAST SYNC: ✅ Sync OK to eca9246 - Sun Jun 07 2026 02:47:19
```

**해석**:
- **APP HEALTH** — 모든 리소스 (pod, service, PVC) 가 *desired state 도달*
- **SYNC STATUS** — *cluster 리소스 == git 리소스* + *현재 git commit 은 `479aae1`*
- **LAST SYNC** — *마지막 성공 sync 는 `eca9246`* + *author + timestamp*

Author + Comment 표시 는 *git blame* 처럼 *누가 언제 무엇 을 배포* 했는지 즉시 확인.

내 스크린샷 에서 마지막 sync commit 은:
- `479aae1` — *"secrets(gemini): unify sparta + lemuel-xr Gemini API key (drift"* — *오늘 한 SOPS 갱신*

---

## 5. 액션 버튼 6 개

상단 툴바 (Screenshot 참고):

### **DETAILS** 
- App 의 *상세 설정* (source path, destination, sync policy, project)
- 편집 하면 git 이 아니라 *cluster 의 Application CRD 만* 변경 됨 (일반적 으로 git 편집 권장)

### **DIFF** 🟢 *가장 자주 씀*
- **live cluster** 와 **git manifests** 의 *실 diff* 를 line-by-line 표시
- YAML unified diff — 어떤 field 가 다른지 색상 표시
- *OutOfSync* 상태 원인 진단 의 *결정 적 도구*

### **SYNC**
- git 상태 → cluster 로 *적용*
- 옵션 3 가지 (아래 6 절 참고)

### **SYNC STATUS**
- 최근 sync 이력 시간 순
- 성공 / 실패 / partial 필터

### **HISTORY AND ROLLBACK** 🟢 *복구 무기*
- *과거 배포* 리스트
- 각 항목 클릭 → *`ROLLBACK`* 버튼 → *그 시점 image 로 즉시 복귀*
- **주의** — auto-sync 활성화 면 *자동 으로 다시 최신 git 을 push 함*. rollback 하려면 먼저 auto-sync 끄기 또는 git revert.

### **DELETE**
- **Foreground** (권장) — 리소스 완전 삭제 대기
- **Background** — 즉시 응답, 리소스 는 background 삭제
- **Non-cascading** — Application CRD 만 삭제, K8s 리소스 유지 (재 declare 가능)

### **REFRESH**
- git polling 을 *즉시 트리거* (평소 3분 마다 자동)
- **Hard refresh** (드롭다운) — cluster 상태 도 재 조회

---

## 6. SYNC 의 옵션

```
[✓] PRUNE — git 에 없는 리소스 삭제 (권장 켜기)
[✓] DRY RUN — 실제 apply 안 하고 diff 만 확인
[  ] APPLY ONLY — sync hook 건너뜀
[  ] FORCE — desired 강제 재적용
[  ] REPLACE — kubectl replace 사용 (default: apply)
```

**전형 적 시나리오**:
- **정상 배포** — `PRUNE ✓` + 나머지 기본
- **의심 스러운 변경** — `DRY RUN ✓` 로 먼저 확인 → 문제 없으면 다시 apply
- **stuck resource** — `FORCE ✓` — 종종 CRD immutable field 변경 시

---

## 7. 좌측 사이드바 — Resource Filters

Screenshot 왼쪽 에 보이는 필터:

**KINDS** — 특정 리소스 타입 만 표시 (Pod, Service, Deployment 등)

**SYNC STATUS**:
- 🟢 Synced — 3 개
- 🟡 OutOfSync — 0 개

**HEALTH STATUS** (내 클러스터 실 수):
- 🔵 Progressing — 0
- 🟠 Suspended — 0
- 🟢 Healthy — 9 (예시)
- 🔴 Degraded — 0
- 🔴 Missing — 0
- ❓ Unknown — 0

*이 filter 만 잘 활용 해도 55 개 앱 중 *문제 되는 것 만* 즉시 필터링*.

---

## 8. Auto-Sync Policy

**설정 방법**:
```yaml
# argocd-applications/settlement-prod.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: settlement-prod
spec:
  syncPolicy:
    automated:
      prune: true      # git 에 없는 리소스 자동 삭제
      selfHeal: true   # 수동 kubectl edit 감지 시 git 값 으로 되돌림
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
```

**함정**:
- `selfHeal: true` + `prune: true` 조합 은 *실 운영* 에 강력 하지만 *수동 kubectl edit 이 초 단위 로 revert 됨* — 디버깅 시 헷갈림
- 그 때는 UI 에서 ***Disable Auto-Sync*** 잠깐 클릭 후 조사

---

## 9. App-of-Apps 패턴 — *55 개 앱 을 한 번 에 관리*

수십 개 앱 을 *각각 CLI 로 배포* 하기 는 지옥. 해결 — **App-of-Apps**:

```yaml
# root-app.yaml (하나 만 배포)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
spec:
  source:
    repoURL: https://github.com/MyoungSoo7/helm-deploy
    path: argocd-applications
  destination:
    namespace: argocd
    server: https://kubernetes.default.svc
```

`argocd-applications/` 폴더 안 에 *55 개 Application CRD 파일*. root-app 이 그 폴더 를 sync 하면 → *55 개 앱 이 자동 배포*.

내 클러스터 의 *initial bootstrap* 은 *`kubectl apply root-app.yaml` 한 줄*. 그 뒤 는 *git 만 편집*.

---

## 10. Image Updater — *배포 자동화 의 마지막 조각*

*코드 push 하면 자동 배포* 를 완성 하는 것:

```yaml
# annotation on Application CRD
annotations:
  argocd-image-updater.argoproj.io/image-list: myapp=ghcr.io/myoungsoo7/myapp
  argocd-image-updater.argoproj.io/myapp.update-strategy: newest-build
  argocd-image-updater.argoproj.io/write-back-method: git
```

**흐름**:
1. GitHub Actions 가 새 image 를 `ghcr.io` 로 push
2. Image Updater 가 *3분 마다* ghcr 검사
3. 새 tag 감지 → helm-deploy 리포 의 `values.yaml` 을 *자동 편집 + commit*
4. ArgoCD 가 git 변경 감지 → auto-sync → *rolling update*

**전 자동 배포 = 코드 push → 5분 후 프로덕션 반영**.

---

## 11. 내 클러스터 의 *실 사고 회고*

### (1) *out-of-sync 에서 자동 복구 실패* (2026-04)
- ArgoCD 가 image tag 를 push 했으나 *ghcr PAT 만료* → image pull backoff
- selfHeal 이 무한 재시도 → alert 폭증
- **해결** — ArgoCD UI 에서 *DELETE* → *재 CREATE* + 새 PAT

### (2) *`stuck rollout` 진단* (오늘)
- `sparta-product` 의 새 image 가 *ES 설정 부재* 로 CrashLoopBackOff
- ArgoCD *DIFF* 로 확인 — desired vs live 는 동일 (git 대로 배포 됨) 
- 문제 는 *git 자체* 에 있음 (helm chart 의 ES env 누락)
- ArgoCD *HISTORY AND ROLLBACK* 클릭 3 번 으로 이전 revision 복귀 준비 완료 상태

### (3) *drift 감지* (오늘 SOPS 사고)
- `sparta-app-secret` 이 *cluster 값* 과 *SOPS git 값* 이 어긋남 (누군가 kubectl edit)
- ArgoCD 는 *K8s Secret data field* 는 diff 무시 (encrypted_regex) — drift 감지 안 됨
- **교훈** — Secret 은 *cluster 에서 직접 kubectl edit 금지* + SOPS 만 유일 source of truth

---

## 12. *helm CLI 직접 조작* — *언제 필요 한가*

ArgoCD 가 있어도 *helm CLI 가 필요 한 상황*:

**필요 함**:
- *새 chart 최초 생성* — `helm create myapp` 로 Chart.yaml + templates/ 뼈대
- *template 로컬 렌더링 검증* — `helm template myapp charts/myapp -f values.yaml`
- *dry-run diff* — `helm diff upgrade` (플러그인)
- *복잡 한 template logic* 개발 (`{{ if }}` `{{ range }}` `{{ include }}`)
- *chart dependencies* 관리 — `helm dependency update`
- *values.schema.json* 생성 및 검증

**불필요 함** (ArgoCD 가 다 함):
- 기존 앱 배포 / 업데이트 / 삭제
- rollback / history
- 여러 replicas scale
- values.yaml *값* 변경 (git 편집 → ArgoCD 자동)

→ **helm CLI = *chart 개발자* 도구**, **ArgoCD = *운영자* 도구**.

---

## 13. 실전 팁 5 가지

### (1) 검색 을 잘 쓰자
상단 검색 창 에 *namespace 이름* 또는 *app prefix* 입력. 55 개 중 필요 한 것 만 즉시.

### (2) URL 로 앱 직접 진입
`argocd.lemuel.co.kr/applications/argocd/settlement-prod` — 북마크 하면 편함.

### (3) CLI 도 필요 할 때 있음
```bash
brew install argocd
argocd login argocd.lemuel.co.kr
argocd app list
argocd app sync settlement-prod
argocd app diff settlement-prod
```

### (4) *Notifications* 설정
Slack / Telegram 으로 sync 결과 알림. 실패 시 즉각 인지.

### (5) *SSO* 통합 (선택)
GitHub OAuth 또는 Dex 로 팀 계정 관리 — 개인 클러스터 이면 admin 로 충분.

---

## 14. 마치며 — *"kubectl 을 잊어도 된다"*

*운영 의 90%* 가 ArgoCD UI 클릭 만 으로 가능. *디버깅* 을 위해 *kubectl* 은 여전히 필요 하지만, *배포 / 롤백 / 삭제 / diff* 같은 *일상 작업* 은 UI 가 훨씬 안전 + 감사 자동 + 팀 협업 용이.

내 클러스터 의 *14 개월 운영 경험* — *ArgoCD 없이 K3s 6 노드 55 앱* 을 유지 하는 것 은 *상상 불가*. *GitOps 의 진짜 힘* 은 *git commit 하나 로 배포 완료* + *언제든 rollback 가능* + *상태 가 시각화* 되는 *3 축 완성*.

**핵심 메시지**: *"kubectl 을 잊어도 되는 세상 이 왔다. ArgoCD 를 배우는 것 = *운영 시간 의 90% 절감 + 사고 대응 속도 3 배*"*.

---

## 참고

- *Argo CD 공식 문서* — [argo-cd.readthedocs.io](https://argo-cd.readthedocs.io)
- *GitOps 원리* — [opengitops.dev](https://opengitops.dev)
- *Argo CD Image Updater* — [argocd-image-updater.readthedocs.io](https://argocd-image-updater.readthedocs.io)
- *ArgoCD Kata* — [argocd.example.com/kata](https://argoproj.github.io/)
- 자매편:
    - [K3s vs K8s 현실 비교](/2026/06/24/k3s-vs-k8s-realistic-comparison.html)
    - [쿠버네티스 컨테이너 오케스트레이션 활용](/2026/06/24/kubernetes-container-orchestration-in-practice.html)
    - [GitHub PAT 만료 13 pod 다운 — 3 예방 패턴](/2026/06/21/github-pat-expiry-13-pods-down-3-prevention-patterns.html)
