---
layout: post
title: "쿠버네티스가 해결하려는 6가지 문제 — 입문자를 위한 친절한 가이드"
date: 2026-05-08 09:00:00 +0900
categories: [infra, kubernetes]
tags: [kubernetes, k8s, devops, container, orchestration, microservices]
---

쿠버네티스(Kubernetes, 줄여서 **k8s**) 를 처음 들으면 보통 이런 반응이 나옵니다.

> "도커 컴포즈 잘 쓰고 있는데 굳이 왜?"
> "그 비싸다는 클러스터, 우리 서비스에도 필요해?"
> "Pod, Deployment, Service, Ingress... 용어부터 어렵네"

저도 처음엔 그랬습니다. 그런데 운영하다 보면 **반드시 마주치는 문제들**이 있는데, 쿠버네티스는 그 문제들을 정리해서 한 번에 해결하려고 만들어진 도구입니다. 그래서 "쿠버네티스가 뭔가요?" 보다 **"쿠버네티스가 어떤 문제를 풀어주나요?"** 부터 보는 게 빠릅니다.

이 글에서는 입문자가 가장 먼저 알면 좋을 6가지 문제와 그 해결 방식을 살펴봅니다. 명령어보다 **개념과 직관**에 초점을 맞췄습니다.

---

## 0. 그 전에: 왜 컨테이너만으론 부족한가

컨테이너(Docker) 가 처음 나왔을 때 모두 환호했죠. "어디서 돌리든 동일하게 동작한다" 는 약속, 정말 강력했습니다. 하지만 운영 규모가 커지면 새 문제가 줄줄이 따라옵니다.

- 컨테이너 100개를 어느 서버에 띄울지 누가 정하나?
- 한 컨테이너가 죽으면 누가 다시 살리나?
- 서버 한 대가 죽으면 그 위의 컨테이너들은?
- 새 버전을 무중단으로 어떻게 배포하나?
- DB 비밀번호는 어디에 안전하게 두나?

도커 단독으로는 이 질문들에 답이 없습니다. 그래서 **컨테이너를 자동으로 관리해주는 시스템 = 컨테이너 오케스트레이터**가 필요해졌고, 그중 사실상 표준이 된 게 쿠버네티스입니다.

---

## 1. 자동화된 롤아웃과 롤백 — "배포가 무서운가요?"

### 문제

새 버전을 배포한다고 합시다. 흔한 시나리오:

1. 운영 중인 컨테이너를 끈다.
2. 새 이미지로 다시 띄운다.
3. **이 사이 1~2분 동안 사용자는 503 을 본다.**
4. 새 버전에 버그가 있으면? 다시 끄고 옛날 이미지로 띄운다 → 또 다운타임.

로컬에서야 괜찮지만, 결제 서비스나 트래픽 많은 서비스에선 이 1분이 매출과 직결됩니다.

### 쿠버네티스의 해결

쿠버네티스는 **Deployment** 라는 개념으로 이걸 자동화합니다.

```yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

이 설정의 의미는 **"새 버전 1대 띄우고 정상이면 옛 버전 1대 끄고, 또 1대 띄우고 1대 끄고..."** 입니다. 항상 3대가 떠 있으니 다운타임 0.

새 버전이 망가졌으면?

```bash
kubectl rollout undo deployment/my-app
```

이 한 줄로 옛날 버전으로 자동 복귀. 이게 **롤백**입니다.

### 더 나아가서

- **Blue/Green 배포**: 옛 버전(blue)을 그대로 두고 새 버전(green) 을 따로 띄운 뒤 트래픽만 한 번에 전환. 문제 생기면 트래픽만 다시 옛 버전으로 돌리면 끝.
- **Canary 배포**: 새 버전에 트래픽 5% 만 보내고 지표 확인 → 괜찮으면 25% → 100%. Argo Rollouts, Flagger 같은 도구가 자동으로 해줍니다.

> 💡 **핵심**: 쿠버네티스는 "지금 상태"가 아니라 **"내가 원하는 상태"**(desired state) 를 선언하면, 그 상태로 알아서 맞춰줍니다. 이걸 *declarative* 모델이라고 합니다.

---

## 2. 로드 밸런싱과 서비스 디스커버리 — "주소가 자꾸 바뀌네요"

### 문제

마이크로서비스(MSA) 를 운영한다고 합시다. user-service, order-service, payment-service 가 서로 호출합니다.

- order-service 가 user-service 를 호출하려면 IP 가 필요한데, user-service 컨테이너는 죽었다 살아나면 **IP 가 바뀝니다.**
- user-service 를 3대로 늘렸는데, order-service 는 어느 IP 로 보내야 하나?
- 한 대가 죽으면 어떻게 자동으로 살아있는 곳으로 보내나?

### 쿠버네티스의 해결

쿠버네티스는 **Service** 라는 개념을 제공합니다. Service 는 "이름표" 같은 거예요.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
spec:
  selector:
    app: user
  ports:
    - port: 80
      targetPort: 8080
```

이걸 만들면 클러스터 안의 어떤 컨테이너든 `http://user-service` 로 호출하면 자동으로:

1. 살아있는 user 컨테이너를 찾음 (selector 로 매칭)
2. 그중 하나로 트래픽을 보냄 (자동 로드밸런싱)
3. 죽은 컨테이너에는 안 보냄 (헬스체크 통과한 것만)

**내부 DNS 가 자동으로 잡혀서**, IP 같은 건 신경 쓸 필요가 없습니다. 컨테이너가 죽고 새로 떠도 `user-service` 라는 이름은 그대로 유효합니다.

> 💡 외부 노출은 보통 **Ingress** 나 **LoadBalancer Service** 로 합니다. Ingress 는 nginx 같은 reverse proxy 라고 보면 편해요. `/api` 는 api-svc 로, `/admin` 은 admin-svc 로 분기하는 식.

---

## 3. 스토리지 오케스트레이션 — "DB 데이터, 컨테이너 죽으면 사라지나요?"

### 문제

컨테이너는 본질적으로 **휘발성**입니다. 죽었다 살아나면 안의 파일은 사라집니다. 그런데 DB, 업로드 파일, 로그 같은 건 안 날아가야 하잖아요.

도커 단독에서도 `-v` 옵션으로 호스트 디렉토리를 마운트하면 됩니다. 하지만 클러스터(여러 서버) 환경이면?

- A 서버에 떠 있던 DB 컨테이너가 죽고 B 서버에 다시 뜨면, B 서버엔 데이터가 없습니다.
- 클라우드라면 EBS, EFS, S3, GCS, Azure Disk... **종류가 너무 많음**. 각각 마운트 방식 다 다름.

### 쿠버네티스의 해결

쿠버네티스는 **PersistentVolume (PV)** 와 **PersistentVolumeClaim (PVC)** 라는 추상화를 제공합니다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: 50Gi
```

이거 한 줄로 **"50GB 영구 저장소 주세요"** 라고 선언하면, 클러스터가 알아서:

- AWS 면 EBS 볼륨 만들어서 붙여줌
- GCP 면 Persistent Disk
- 온프레미스면 NFS 나 Ceph

컨테이너가 다른 서버로 옮겨가도 **같은 데이터에 자동 연결**됩니다. 이게 **StorageClass** 라는 추상화의 힘이고, **CSI (Container Storage Interface)** 표준이 받쳐주고 있어요.

> 💡 PostgreSQL, Redis 같은 stateful 한 서비스는 **StatefulSet** 으로 띄웁니다. Deployment 와 비슷하지만 각 인스턴스에 고유 이름과 디스크가 보장돼요. (`pg-0`, `pg-1`, `pg-2`)

---

## 4. 자동화된 빈 패킹 — "서버 자원, 어떻게 짜내요?"

### 문제

서버 5대가 있고, 띄울 컨테이너가 30개 있다고 합시다. 각각 CPU, 메모리 요구량이 다릅니다.

- 어떤 컨테이너를 어떤 서버에 띄울 건지 사람이 정하면? **금방 한쪽으로 쏠림.** A 서버는 80% 만 쓰고 B 서버는 95% 라 OOM 으로 터지고.
- 새 컨테이너가 들어오면? 또 사람이 보고 "B 가 비어있으니 거기" 결정.

이건 진짜 짜증나는 운영 일거리입니다.

### 쿠버네티스의 해결

쿠버네티스 **Scheduler** 는 짐 싸기(bin packing) 알고리즘을 돌려서 자동으로 배치합니다.

각 컨테이너에 이렇게 선언하면:

```yaml
resources:
  requests:
    cpu: "500m"      # 0.5 CPU 코어 보장
    memory: "512Mi"
  limits:
    cpu: "1000m"     # 최대 1 CPU 코어
    memory: "1Gi"
```

스케줄러가:

1. 모든 노드(서버) 의 남은 자원 확인
2. 이 요구사항에 **딱 맞는** 노드 선택
3. 자원 가장 많이 비어있는 노드 우선 (or 가장 효율적)
4. 라벨/어피니티 등 추가 조건도 반영

운영자가 신경 쓸 필요 없이 자원이 **수학적으로** 최적 배치됩니다. 트래픽 늘어서 컨테이너 더 띄울 때도, 클러스터에 노드 추가할 때도 자동.

> 💡 **HPA (Horizontal Pod Autoscaler)** 를 쓰면 CPU/메모리 사용률 보면서 자동으로 컨테이너 수를 늘리거나 줄입니다. 트래픽 폭증해도 사람 잠 깨울 일 없음.

---

## 5. 자동 복구 (Self-Healing) — "새벽 3시에 알람 받기 싫어요"

### 문제

운영하다 보면 별별 일이 다 일어납니다.

- 컨테이너 안의 프로세스가 메모리 누수로 죽음
- 노드(서버) 한 대가 통째로 다운
- 네트워크 일시 단절
- 하드디스크 풀

당직 서다 새벽에 알람 받고 일어나서 ssh 로 들어가 `docker restart` 치는 거... 한 두 번이면 모를까.

### 쿠버네티스의 해결

쿠버네티스의 컨트롤러들은 **24/7 감시**하면서 자동으로 복구합니다.

#### Liveness / Readiness Probe

```yaml
livenessProbe:
  httpGet:
    path: /actuator/health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
```

매 10초마다 `/actuator/health` 를 호출. 응답 없으면 → 컨테이너 자동 재시작.

- **Liveness**: 살아있나? → 죽었으면 재시작
- **Readiness**: 트래픽 받을 준비됐나? → 안 됐으면 LB 에서 잠깐 빼기

#### Node 가 죽었을 때

쿠버네티스는 노드도 헬스체크합니다. A 노드가 5분간 응답 없으면 → 그 위에 떠있던 Pod 들을 **다른 살아있는 노드로 자동 재배치**합니다. 사람 개입 0.

#### ReplicaSet

Deployment 가 "3대 떠 있어야 함" 이라고 선언하면, 한 대가 죽었을 때 **즉시 새 컨테이너 1대를 띄워서 항상 3대를 유지**합니다.

> 💡 진짜 중요한 점: 쿠버네티스는 **"지금 상태"** 와 **"원하는 상태"** 를 끊임없이 비교하면서 자동으로 맞춥니다. 이게 declarative 운영의 본질이에요. 사람이 "고치는" 게 아니라 시스템이 "맞춰가는" 거.

---

## 6. 시크릿과 구성 관리 — "DB 비밀번호 어디에 두세요?"

### 문제

애플리케이션이 필요로 하는 비밀 정보들:

- DB 비밀번호
- API 키 (OpenAI, AWS, Stripe...)
- TLS 인증서
- OAuth Client Secret

흔히 보는 안티패턴:

- ❌ 코드에 하드코딩 → git 에 그대로 올라감
- ❌ `.env` 파일을 컨테이너 이미지에 넣어 빌드 → 이미지 받은 사람 누구나 봄
- ❌ docker-compose.yml 에 평문으로 박기

### 쿠버네티스의 해결

쿠버네티스는 **Secret** 과 **ConfigMap** 이라는 두 가지 객체를 줍니다.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWNhZGVteQ==      # base64
  password: cGFzc3dvcmQxMjM=
```

```yaml
# Pod 정의 안에서
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: db-credentials
        key: password
```

이렇게 하면:

- 비밀번호는 etcd 에 저장됨 (암호화 저장 가능)
- 컨테이너 안에는 환경변수로 주입
- 코드에선 그냥 `os.getenv("DB_PASSWORD")`

**ConfigMap** 은 비밀이 아닌 일반 설정용 (서비스 URL, log level 등) 입니다.

### 더 나아가서

쿠버네티스 자체 Secret 은 사실 base64 인코딩일 뿐이라 *진짜* 암호화가 아닙니다. 운영급에선 보통 외부 도구를 같이 씁니다:

- **HashiCorp Vault**: 동적 시크릿 발급, lease 기반 회전
- **External Secrets Operator**: AWS Secrets Manager / GCP Secret Manager / Vault 와 연동
- **SOPS + age + Sealed Secrets**: GitOps 친화적 (저는 이걸 씁니다 — 별도 글 예정)

> 💡 시크릿 관리는 사실 별도의 큰 주제예요. 처음엔 Secret 객체로 시작하고, 운영 들어가면서 외부 도구를 붙이면 됩니다.

---

## 그래서 언제 도입해야 할까

쿠버네티스가 만능은 아닙니다. 오히려 **소규모에선 오버엔지니어링**입니다.

### 도입을 고려할 만한 신호

- ✅ 컨테이너가 20개 이상이고 점점 더 늘어남
- ✅ 서버가 3대 이상이고 컨테이너 수동 배치가 짜증남
- ✅ 무중단 배포가 비즈니스적으로 중요
- ✅ 트래픽 변동 폭이 커서 자동 스케일링이 필요
- ✅ 팀에 K8s 운영해본 사람이 1명 이상 있음

### 도입 안 해도 되는 경우

- ❌ 서비스가 1~2개 + 서버 1~2대 → docker-compose 로 충분
- ❌ 트래픽이 안정적이고 무중단 배포 안 중요 → systemd + nginx 로 충분
- ❌ 팀에 누구도 K8s 운영 경험 없음 → 학습 비용이 도입 효과보다 큼

저도 운영 중인 사이트들은 docker-compose + Cloudflare Tunnel 로 잘 돌아갑니다. K8s 가 빛나는 건 "여러 개의 서비스 × 트래픽 변동 × 팀 규모" 가 어느 임계점 넘어서부터예요.

### 점진적 도입 경로

1. **로컬에서 minikube / kind 로 학습** — 무료, 가벼움
2. **k3s 로 단일 서버 클러스터** — 라즈베리파이에서도 돌아감
3. **관리형 K8s 사용** (EKS, GKE, AKS) — 컨트롤 플레인 운영을 클라우드에 떠넘김
4. **자체 클러스터** — 정말 큰 조직에서나

---

## 마치며

쿠버네티스는 **"컨테이너 100개를 어떻게 효율적으로 굴릴까"** 라는 운영 문제를 풀려고 만든 도구입니다. 6가지 핵심 문제 — 롤아웃/로드밸런싱/스토리지/스케줄링/자가복구/시크릿 — 을 표준화된 방식으로 한 번에 해결한다는 점이 강력해요.

처음엔 **Pod, Deployment, Service** 세 가지만 이해해도 80% 는 됩니다. 나머지(Ingress, ConfigMap, PVC, ...) 는 필요할 때 하나씩 붙여가면 됩니다.

가장 빠른 학습 경로:

1. 로컬에 **minikube** 또는 **kind** 설치
2. nginx 같은 단순한 거 하나 띄워보기
3. `kubectl get pods`, `kubectl logs`, `kubectl describe` 자주 두드리기
4. YAML 직접 써보기 (복붙 말고)
5. 죽여보고 → 자동으로 살아나는 거 확인하기 ← **이 순간이 진짜 "오~" 하는 포인트**

다음 글에선 실제로 minikube 위에서 마이크로서비스 하나 배포해보는 실습을 다뤄볼게요.

질문이나 더 다뤘으면 하는 주제는 댓글로 남겨주세요. 🙌

---

**Tags**: #kubernetes #k8s #devops #container #orchestration #microservices

**참고**:
- [Kubernetes 공식 문서](https://kubernetes.io/ko/docs/home/)
- [Kubernetes Patterns (O'Reilly)](https://www.oreilly.com/library/view/kubernetes-patterns/9781492050278/)
- [The Kubernetes Book — Nigel Poulton](https://nigelpoulton.com/books/)
