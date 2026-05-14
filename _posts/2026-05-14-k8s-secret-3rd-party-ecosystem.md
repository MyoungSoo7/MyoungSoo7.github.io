---
layout: post
title: "K8s 가 의도적으로 비워둔 자리 — Secret 관리 3rd-party 생태계 정리"
date: 2026-05-14 17:00:00 +0900
categories: [infra, kubernetes, security]
tags: [kubernetes, secrets, sops, age, sealed-secrets, eso, vault, gitops, security]
---

> Kubernetes 의 `Secret` 리소스를 처음 만났을 때 "이게 secret 관리의 답" 이라고 생각했습니다. base64 디코드 한 줄로 모든 게 평문이라는 걸 알기 전까진. 이 글은 K8s 가 네이티브로 무엇을 제공하고 무엇을 의도적으로 비워뒀는지, 그리고 그 빈자리를 채우는 3rd-party 들이 어떤 trade-off 를 제시하는지 정리한 글입니다.

## 1. K8s 네이티브가 제공하는 것 — 그리고 한계

K8s 의 secret 관련 네이티브 기능은 셋뿐입니다.

### (1) `Secret` 리소스

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=   # ← 그냥 base64
```

`base64 -d` 한 줄에 평문이 나옵니다. **"암호화" 가 아니라 "이진 데이터를 텍스트로 안전하게 옮기기 위한 인코딩"** 일 뿐입니다. 이걸 Git 에 넣으면 평문을 넣은 것과 동등합니다.

### (2) etcd 암호화 — `EncryptionConfiguration`

kube-apiserver 의 `--encryption-provider-config` 로 활성화. etcd 디스크에 저장되는 Secret 객체를 AES-CBC / AES-GCM 등으로 암호화합니다.

```yaml
# encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: [secrets]
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-32바이트-키>
      - identity: {}   # fallback
```

이건 **디스크 노출에 대한 방어**. etcd 백업이나 노드 탈취 시나리오는 막아주지만, Git 보관 문제와는 무관합니다. 게다가 키 자체는 control-plane 의 파일 시스템에 평문 보관 (KMS 연동 안 하면).

### (3) RBAC + ServiceAccount

`get/list secrets` 권한을 누가 가질지 제어. 운영자 외엔 못 보게 막지만, 운영자 본인은 평문으로 보게 됩니다.

### 빠진 것

K8s 가 답을 안 주는 영역:
- **개발자가 Git 에 secret 을 어떻게 보관할 것인가**
- **팀원 가입/이탈 시 secret 접근권은 어떻게 관리할 것인가**
- **secret 을 주기적으로 어떻게 로테이션할 것인가**
- **외부 비밀 저장소 (Vault, AWS Secrets Manager) 와 어떻게 연동할 것인가**

이 빈자리들이 3rd-party 생태계를 만든 이유입니다.

## 2. K8s 가 그 자리를 일부러 비운 이유

처음엔 "K8s 가 이걸 왜 안 해줘?" 라고 생각했는데, 곰곰이 보면 **의도적 분리** 입니다.

| K8s 의 책임 영역 | K8s 가 양보한 영역 |
|----------------|----------------|
| Secret 의 런타임 사용 (Pod 주입) | Git 에서의 보관 |
| etcd 디스크 암호화 | 키 관리 정책 |
| RBAC 권한 제어 | 외부 저장소 연동 |
| API 객체 생명주기 | 로테이션 자동화 |

이런 분리 덕분에:
- 회사 정책 / 컴플라이언스 / 인프라 (AWS vs GCP vs on-prem) 에 맞춰 다양한 도구 조합 가능
- K8s 코어가 비대해지지 않음
- 새 도구 채택에 K8s 업그레이드가 필요 없음

대신 **선택 부담** 이 사용자에게 옵니다. 그래서 정리가 필요합니다.

## 3. 빈자리를 채우는 5개의 패턴

### 패턴 A — 파일 암호화 (SOPS + age)

```
[Git: 암호화된 파일]
     ↓ kubectl apply
[클러스터: 평문 K8s Secret]
```

**대표 도구**
- `mozilla/sops` (파일 안의 일부 필드만 암호화)
- `FiloSottile/age` (현대적 파일 암호화, X25519 + ChaCha20-Poly1305)
- 클러스터 측: `isindir/sops-secrets-operator` (CRD `SopsSecret` 을 평문 Secret 으로 변환)

**작동**
```bash
sops --encrypt --in-place secrets/myapp.sops.yaml  # 평문 → ENC[AES256_GCM,...]
git commit && git push                              # 암호화된 채로 Git
# 클러스터: 운영자가 SopsSecret CR 감지 → 복호화 → K8s Secret 생성
```

**적합한 경우**
- 1~5명 소규모 팀
- 외부 의존성 0 (Vault/AWS 안 씀)
- 풀 Git 추적 원함

**한계**
- 멤버 늘면 `.sops.yaml` 의 `age:` 필드에 public key 나열 → 추가/제거마다 `sops updatekeys` 필요
- 멤버 이탈 시 secret 자체도 로테이션해야 함 (이미 복호화한 걸 가져갔다고 가정)

### 패턴 B — 클러스터 키쌍 (Sealed Secrets)

```
[Git: 봉인된 SealedSecret]
     ↓ ArgoCD sync
[클러스터: 컨트롤러가 private key 로 복호화]
     ↓
[K8s Secret]
```

**대표 도구**
- `bitnami-labs/sealed-secrets`
- CLI: `kubeseal`

**작동 원리**
1. 컨트롤러가 RSA 키쌍 자체 생성 (private key 는 컨트롤러 내부, public key 는 노출)
2. 개발자: `kubeseal` 로 public key 가져와서 Secret 을 SealedSecret 으로 봉인
3. SealedSecret 을 Git commit → ArgoCD sync → 컨트롤러가 private key 로 복호화

```bash
kubectl create secret generic foo --from-literal=KEY=val --dry-run=client -o yaml > foo.yaml
kubeseal < foo.yaml > foo-sealed.yaml   # 자동으로 클러스터에서 public key fetch
rm foo.yaml
git add foo-sealed.yaml
```

**적합한 경우**
- 팀 5~20명 (멤버 키 관리하기 싫음)
- 클러스터 1~2개
- 외부 의존성 도입 부담스러움

**한계**
- 클러스터당 키쌍 1개 → multi-cluster 면 각 클러스터마다 따로 봉인 필요
- 컨트롤러 private key 분실 = 모든 SealedSecret 영구 복호화 불가 → 백업 필수
- Secret 자동 로테이션 X

### 패턴 C — 외부 저장소 동기화 (External Secrets Operator)

```
[외부 저장소: Vault / AWS SM / GCP / Azure]
     ↑ polling
[클러스터: ESO 가 ExternalSecret CR 보고 fetch]
     ↓
[K8s Secret 자동 생성/갱신]
```

**대표 도구**
- `external-secrets/external-secrets` (CNCF Incubation)
- 백엔드: HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, 1Password Connect, Akeyless, etc.

**작동**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: myapp-secret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
  target:
    name: myapp-app-secret
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: secret/myapp/db
        property: password
```

→ Git 에는 **secret 의 평문도 암호문도 들어가지 않음**. 그냥 "Vault 의 어디서 가져와라" 라는 포인터.

**적합한 경우**
- 팀 20명+ 또는 SOC2 / ISO27001 등 컴플라이언스
- 회사가 이미 AWS/GCP/Vault 인프라 사용 중
- secret 자동 로테이션 필요 (DB 비번 매월 변경 등)
- Multi-cluster / multi-region

**한계**
- 외부 저장소 의존 → 다운타임 시 secret refresh 불가
- 외부 저장소 비용 (Vault 자체 호스팅 비용 / AWS Secrets Manager $0.40 per secret/month)
- 셋업 복잡: 외부 저장소 + IAM/RBAC + 네트워크 + ServiceAccount workload identity

### 패턴 D — Pod 단위 주입 (Vault Agent Injector / CSI Drivers)

```
[Pod 스폰 시점]
     ↓ initContainer / CSI volume
[외부 저장소에서 직접 가져와서 메모리에 마운트]
     ↓
[K8s Secret 자체를 거치지 않음]
```

**대표 도구**
- `hashicorp/vault-k8s` (Vault Agent Injector)
- `kubernetes-sigs/secrets-store-csi-driver` + AWS / GCP / Azure 프로바이더

**작동**
- Pod annotation 으로 "이 secret 을 마운트해줘" 선언
- Webhook 또는 CSI 가 Pod 스폰 시 외부에서 fetch
- 결과는 Pod 의 emptyDir/tmpfs 에만 존재 → etcd 에 안 남음

**적합한 경우**
- 가장 보안 강한 요구
- Dynamic credentials (DB 비번이 매번 새로 발급, TTL 짧음)
- 컴플라이언스 감사 (어디서 누가 언제 fetch 했는지 로그)

**한계**
- 운영 복잡도 ↑↑
- 디버깅 어려움 (Pod 안에서만 보임)
- 외부 저장소 의존성이 가장 큼

### 패턴 E — GitOps 와 직접 충돌하는 그 외

- **Plain kubectl create + .gitignore** — 가장 단순. 코드 따로, secret 따로. GitOps 의 "Git 이 single source of truth" 원칙과 충돌.
- **Helm `--set` 으로 인자 주입** — CI 환경변수에 secret 보관 → CI 침해 시 노출.
- **Argo CD plugin (kustomize-sops 등)** — ArgoCD repo-server 에 SOPS 키 주입해서 sync 시점 복호화. 패턴 A 의 변형.

## 4. 네이티브로 착각하기 쉬운 다른 사례들

CRD 가 너무 잘 통합돼서 K8s 자체 기능처럼 보이는 3rd-party 들:

| 도구 | 추가하는 CRD | 진짜 K8s? |
|------|-------------|----------|
| Prometheus Operator | ServiceMonitor / PodMonitor / PrometheusRule | ❌ CoreOS → CNCF |
| cert-manager | Certificate / Issuer / ClusterIssuer | ❌ Jetstack → CNCF |
| ArgoCD | Application / AppProject | ❌ Intuit → CNCF |
| Strimzi | Kafka / KafkaTopic / KafkaUser | ❌ Red Hat → CNCF |
| Sealed Secrets | SealedSecret | ❌ Bitnami |
| External Secrets | ExternalSecret / SecretStore | ❌ CNCF Incubation |
| Velero | Backup / Restore / Schedule | ❌ Heptio → VMware |

이걸 알아두면 면접에서 "이건 K8s 가 하는 거고, 이건 X 가 하는 거다" 를 깔끔하게 설명할 수 있습니다.

## 5. 선택 매트릭스

|  | SOPS+age | Sealed Secrets | ESO+Vault | Vault Injector |
|--|---------|---------------|-----------|---------------|
| Git 에 들어가는 것 | 암호화된 secret | 봉인된 secret | 포인터만 | 포인터만 |
| 키 보유자 | 사람(들) | 클러스터 | 외부 저장소 | 외부 저장소 |
| 멤버 추가 | .sops.yaml + updatekeys | 불필요 | IAM | IAM |
| 멤버 이탈 | public key 제거 + 재암호화 + secret 로테이션 | secret 로테이션 | IAM 제거 | IAM 제거 |
| Multi-cluster | OK (단일 키) | 클러스터별 봉인 | OK | OK |
| 자동 로테이션 | X | X | ✅ | ✅ (dynamic) |
| 외부 의존성 | 없음 | 없음 | 큼 | 가장 큼 |
| 운영 복잡도 | 낮음 | 낮음 | 중~높음 | 높음 |
| 적합 규모 | 1~5명 | 5~20명 | 20명+ | 보안 강한 환경 |

## 6. 내 환경에서 SOPS+age 를 골랐던 이유

본인의 르무엘 인프라 (1인 운영, 온프레미스 K3s 5노드, 외부 의존 최소화) 에는 SOPS+age 가 가장 잘 맞았습니다. 이유는:

- 외부 저장소 (Vault/AWS) 추가하면 운영 비용 + 다운타임 risk + 셋업 시간 너무 큼
- 클러스터 컨트롤러 (Sealed Secrets) 의 키 관리도 결국 비슷한 부담
- 1인 운영이라 "멤버 추가/제거" 시나리오가 없음
- Git 에 모든 게 추적되는 GitOps 원칙 100% 유지하고 싶음

설치 흐름은 단순했습니다:
1. age 키쌍 생성 (`age-keygen -o ~/.config/sops/age/keys.txt`)
2. `.sops.yaml` 로 암호화 정책 정의 (data/stringData 만 암호화, age public key 등록)
3. K3s 에 sops-secrets-operator 설치 + age private key 를 K8s Secret 으로 주입
4. 첫 SopsSecret 작성/암호화/배포 → 운영자가 자동 복호화하는지 검증

[관련 작업 로그: 2026-05-14, helm-deploy repo 의 SOPS.md 참고]

## 7. 회고 — "K8s 가 다 해줄 거" 는 위험한 가정

K8s 도입 초기에 흔히 빠지는 함정:

- ❌ "Secret 리소스가 있으니 secret 관리 끝"
- ❌ "etcd 암호화 켜놓으면 안전"
- ❌ "RBAC 만 잘하면 안전"

이 셋만으로는 **Git 에 secret 이 평문으로 들어가는 문제** 가 안 풀립니다. K8s 가 의도적으로 비워둔 자리이고, 그 빈자리를 3rd-party 가 채웁니다.

면접에서 "K8s Secret 관리는 어떻게?" 라고 물으면:
> "K8s 네이티브로는 base64 인코딩과 RBAC 뿐이라 Git 기반 GitOps 환경에선 부족합니다. 팀 규모/컴플라이언스에 따라 SOPS+age (소규모), Sealed Secrets (중규모), External Secrets Operator + Vault (대규모) 를 골라 씁니다. 핵심은 'Git 에 평문 secret 0' 라는 GitOps 원칙입니다."

이 정도 답하시면 깔끔합니다.

---

**다음 글 예고**: SOPS+age 를 실제 운영 secret 으로 점진 마이그레이션 — opt-in 전략과 함정
