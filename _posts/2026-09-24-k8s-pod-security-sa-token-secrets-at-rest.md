---
layout: post
title: "파드 하나가 뚫린 다음 — 네트워크 말고 권한: Pod Security·ServiceAccount 토큰·Secret 을 실측했다"
date: 2026-09-24 20:18:57 +0900
categories: [security]
tags: [kubernetes, k3s, pod-security-standards, rbac, serviceaccount, secrets, encryption-at-rest, hardening]
---

오늘 앞서 올라온 [NetworkPolicy 편](/2026/09/24/flat-cluster-network-networkpolicy/)은 "파드 하나가 뚫리면 _네트워크로_ 어디까지 닿나"를 쟀다. 이 글은 같은 질문을 다른 축으로 잰다. **뚫린 파드가 _권한으로_ 무엇을 할 수 있나.** 네트워크를 다 막아도 파드는 세 개의 문을 더 갖고 있다.

1. **노드로 가는 문** — 파드가 privileged 이거나 호스트 경로·호스트 네트워크를 쓰면, 컨테이너 탈출이 곧 노드 장악이다.
2. **API 서버로 가는 문** — 파드 안에는 기본적으로 ServiceAccount 토큰이 마운트돼 있고, 그 토큰의 RBAC 권한이 곧 공격자의 권한이다.
3. **저장소로 가는 문** — Secret 은 etcd 에 들어가는데, 거기서 평문인지 아닌지.

대상은 연구용 K3s 홈랩 클러스터(v1.35.4+k3s1, 노드 6대, 네임스페이스 51개, 실행 중 파드 163개)다. 전부 2026-09-24 에 읽기 전용 조회와 **server-side dry-run** 으로 쟀고, 클러스터에는 아무것도 적용하지 않았다.

## 1. 노드로 가는 문 — Pod Security Standards

### 쿠버네티스는 무엇을 풀려고 이걸 만들었나

예전엔 PodSecurityPolicy 가 이 역할을 했지만 1.25 에서 제거됐고, 그 자리를 **Pod Security Admission(PSA)** 이 이어받았다. PSA 는 1.25 부터 GA 이고 별도 설치 없이 켜져 있다([Kubernetes, Enforce Pod Security Standards by Configuring the Built-in Admission Controller](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/)). 규칙 자체는 **Pod Security Standards** 세 단계다([Kubernetes, Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)).

- **Privileged** — 제한 없음. 알려진 권한 상승도 허용. 시스템·인프라 워크로드용.
- **Baseline** — 알려진 권한 상승만 막는 최소 제한. 기본값 그대로 만든 파드는 통과한다.
- **Restricted** — 현행 하드닝 모범사례를 따르는 강한 제한.

네임스페이스에 `pod-security.kubernetes.io/enforce=<level>` 라벨을 달면 그 단계를 강제한다. 이전과 달라진 점은 분명하다. 별도 정책 엔진 없이 **라벨 한 줄**로 "이 네임스페이스엔 privileged 파드가 못 뜬다"를 보장할 수 있게 됐다.

### 실측 — 라벨이 붙은 네임스페이스는 51개 중 1개

| 항목 | 값 |
| --- | --- |
| PSA 라벨이 있는 네임스페이스 | **1 / 51** (velero — 그것도 `enforce=privileged`, 즉 명시적으로 "제한 없음") |
| privileged 컨테이너가 있는 파드 | 23개 (5개 네임스페이스) |
| hostPath 볼륨 | 36개 파드 |
| hostPID / hostNetwork | 17 / 18개 파드 |
| `runAsNonRoot` 도 `runAsUser≠0` 도 아닌 파드 | 114 / 163 |

기능이 있다는 것과 쓰고 있다는 것은 다르다. 이 클러스터는 PSA 를 사실상 안 쓰고 있었다.

### 라벨을 달면 뭐가 깨지나 — dry-run 으로 미리 본다

PSA 의 좋은 점은 **미리 재 볼 수 있다**는 것이다. `kubectl label --dry-run=server` 로 라벨을 달아 보면, API 서버가 실제로 적용하진 않고 "지금 떠 있는 파드 중 무엇이 이 단계를 위반하는지"를 경고로 돌려준다. 파드가 떠 있는 네임스페이스 47개에 전부 돌려 봤다.

| 단계 | 위반 없이 달 수 있는 네임스페이스 |
| --- | --- |
| baseline | **38 / 47** |
| restricted | **3 / 47** |

baseline 을 위반하는 9개는 이유가 전부 설명된다 — 로그 수집기(fluent-bit, hostPath), Elasticsearch 의 `vm.max_map_count` 를 올리는 `sysctl` init 컨테이너(privileged), NFS 서버(privileged), 노드 익스포터·Falco 같은 노드 관측 도구(hostPID·hostPath), 컨테이너 이미지 빌더(buildkitd). 예를 들어 정산 운영 네임스페이스에 dry-run 을 걸면 이렇게 나온다.

```
Warning: existing pods in namespace "settlement-prod" violate the new PodSecurity enforce level "baseline:latest"
Warning: settlement-elasticsearch-0: privileged
```

같은 네임스페이스에 restricted 를 걸면 20개 파드가 `allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile` 로 걸린다. 여기서 얻는 결론은 두 가지다.

- **baseline 은 거의 공짜다.** 38개 네임스페이스는 오늘 라벨을 달아도 떠 있는 파드가 하나도 안 깨진다. 그런데도 안 달려 있었다.
- **restricted 는 공짜가 아니다.** 파드 스펙마다 `securityContext` 를 채워야 하고, 이미지가 root 로 돌도록 만들어져 있으면 이미지부터 고쳐야 한다.

라벨은 `enforce` 전에 `warn`·`audit` 으로 먼저 달 수 있다. 새로 배포되는 파드부터 경고가 쌓이게 한 다음 enforce 로 올리면 된다([Kubernetes, Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)).

## 2. API 서버로 가는 문 — ServiceAccount 토큰과 RBAC

### 토큰은 기본으로 들어가 있다

파드를 만들면 쿠버네티스는 ServiceAccount 자격증명을 파드 안에 자동으로 넣는다. 끄려면 파드나 ServiceAccount 에 `automountServiceAccountToken: false` 를 명시해야 한다([Kubernetes, Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/); [Configure Service Accounts for Pods](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)).

실측: 실행 중 파드 **163개 중 149개**에 토큰이 마운트돼 있다. 대부분의 앱 ServiceAccount 는 RBAC 권한이 없어서 이 토큰으로 할 수 있는 게 거의 없다. 정산 운영 네임스페이스의 `default` SA 로 `kubectl auth can-i --list` 를 돌리면 자기 권한 조회 외엔 아무것도 안 나온다. 그러니 이 숫자 자체보다 중요한 건 **"권한이 센 토큰이 어느 파드에 들어가 있나"** 다.

### 센 토큰은 어디에 있나

| 권한 | 개수 | 누구 |
| --- | --- | --- |
| `cluster-admin` 바인딩 | 4 | `system:masters` 그룹, 백업(velero), 쿠버네티스 대시보드 관리자 SA, 운영 에이전트 SA |
| 클러스터 전역 Secret 읽기(`get/list/watch`) | 11 | ArgoCD 3종, Grafana, kube-state-metrics, Prometheus operator, ECK·Strimzi·SOPS operator |

두 번째 줄이 흔히 과소평가된다. 쿠버네티스 공식 문서는 이렇게 경고한다. `get` 이 Secret 내용을 읽게 해 준다는 건 명백하지만, **`list` 와 `watch` 도 사실상 Secret 내용을 드러낸다** — List 응답에는 모든 Secret 의 내용이 들어 있기 때문이다([Kubernetes, RBAC Good Practices — Listing secrets](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)).

Operator 들은 Secret 을 만들고 관리하는 게 일이라 이 권한이 필요하다. 눈여겨볼 건 **Grafana** 다. 대시보드·데이터소스를 Secret/ConfigMap 에서 자동으로 읽어 오는 사이드카 때문에 클러스터 전역 Secret 읽기 권한을 갖고 있는데, Grafana 는 사람이 브라우저로 접속하는 웹 앱이고 그 파드에도 토큰이 마운트돼 있다. **웹 앱 하나가 뚫리면 클러스터의 모든 Secret 이 나간다**는 뜻이다. 같은 문서는 강한 권한을 가진 SA 를 파드에 붙이지 말고, 꼭 필요하면 그 파드를 신뢰할 수 없는 파드와 떼어 놓으라고 권한다(같은 문서, *Minimize distribution of privileged tokens*). 고치는 방향은 사이드카의 탐색 범위를 특정 네임스페이스로 좁히는 것이다.

하나 더. 워크로드를 **만들 수 있는** 권한은 그 네임스페이스의 Secret 을 **읽을 수 있는** 권한과 같다. Secret 을 마운트하는 파드를 띄우면 되기 때문이다(같은 문서, *Workload creation*). CI 러너나 배포 봇에 "파드 생성만" 줬다고 안심하면 안 된다.

## 3. 저장소로 가는 문 — Secret 은 etcd 에 평문이다

쿠버네티스 문서의 Secret 페이지 맨 위에 경고가 있다. **Secret 은 기본적으로 API 서버의 저장소(etcd)에 암호화되지 않은 채 저장된다**([Kubernetes, Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)). 저장 시 암호화는 `EncryptionConfiguration` 으로 따로 켜야 한다([Kubernetes, Encrypting Confidential Data at Rest](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)).

K3s 에서는 서버 기동 플래그 `--secrets-encryption` 하나로 AES-CBC 키 생성과 설정 파일 생성, API 서버 연결까지 자동으로 해 준다. 단 **기존 서버에서는 재시작 없이는 켤 수 없다**([K3s, Secrets Encryption](https://docs.k3s.io/security/secrets-encryption)).

실측:

```
$ sudo k3s secrets-encrypt status
Encryption Status: Disabled, no configuration file found
```

git 에 들어가는 Secret 은 SOPS 로 암호화하고 있지만(그건 _리포지토리_ 문제를 푼다), 클러스터에 적용된 순간부터 etcd 스냅샷과 백업 안에서는 평문이다. 노드 디스크나 etcd 스냅샷, 백업 버킷 중 하나라도 새면 Secret 전부가 샌다. 공격 난이도는 1·2절보다 높지만, 터지면 피해 범위는 가장 넓다.

## 4. 오탐으로 끝난 것 — 평문 비밀번호 env

"이름에 PASSWORD·SECRET·TOKEN·API_KEY 가 들어간 env 에 값이 직접 박혀 있는가"로 훑어 보면 6건이 걸린다. 열어 보면 **6건 모두 비밀이 아니었다** — Secret 의 _이름_(`…_SECRET_NAME`), 비밀번호 파일의 _경로_(`PROBE_PASSWORD_PATH`), 불리언 플래그였다. 실제 비밀번호를 env 에 평문으로 박은 파드는 0개였다. 이름만 보는 검사는 이렇게 시끄럽다. 반대로 이름이 평범한 env 에 비밀이 들어 있으면 이 검사로는 못 잡는다.

## 5. 문 밖에서 들어오는 길 — 인증 게이트 없는 관리 화면 1건

측정하다가 진짜 노출도 하나 찾았다. 같은 관리 화면으로 가는 공개 호스트명이 두 개 있었는데, **하나는 Cloudflare Access(이메일 인증) 뒤에 있고 다른 하나는 게이트 없이 로그인 화면이 인터넷에 그대로 떠 있었다.** 로그인에는 Bearer 토큰이 필요하고, 해당 관리자 SA 의 장기 토큰 Secret 은 없다는 것도 확인했다. 그래서 곧바로 뚫리는 상태는 아니었다. 하지만 그 SA 의 권한이 `cluster-admin` 이라 토큰이 한 번이라도 새거나 화면 자체에 취약점이 나오면 곧바로 클러스터 전체가 넘어간다.

**2026-09-24 이 글을 쓰는 도중에 막았다.** 게이트 없던 호스트명의 터널 규칙과 DNS 레코드를 지우고, 같은 화면은 Access 가 걸린 호스트명으로만 들어가게 일원화했다. 지운 뒤 그 호스트명은 터널의 catch-all 404 를 돌려주고, Access 쪽 호스트명은 여전히 인증 페이지로 302 리다이렉트되는 것을 확인했다. 같은 대조를 공개 호스트명 전체에 돌려 보니, 자체 로그인만 있고 Access 는 없는 관리 화면이 더 있어서 별도로 정리하고 있다.

교훈은 1~3절과 성격이 다르다. 클러스터 _안_ 의 설정을 아무리 조여도, 호스트명 하나를 추가하면서 게이트를 빠뜨리면 그 앞에서 끝난다. 이런 건 "새 호스트명에는 Access 가 붙어 있는가"를 **목록 전체에 대해 기계로 대조**해야 잡힌다. 사람이 하나씩 추가하는 구조에서는 빠뜨린 하나가 조용히 열려 있다. (앞서 쓴 [SonarCloud 편](/2026/09/24/sonarcloud-security-limits-sast-cannot-see-intent/)의 인가 매처 누락과 똑같은 모양이다.)

## 6. 고치는 순서 — 비용이 싼 것부터

| 순서 | 조치 | 비용 | 막는 것 |
| --- | --- | --- | --- |
| 1 | 게이트 없는 공개 관리 화면 제거·게이트 추가 | 작음 | 외부에서 관리 화면 직행 |
| 2 | 위반 0인 38개 네임스페이스에 `enforce=baseline` (먼저 `warn`) | 작음 — dry-run 으로 영향 0 확인됨 | 새 privileged/hostPath 파드 |
| 3 | 권한 없는 앱 SA 에 `automountServiceAccountToken: false` | 작음 | 토큰 유출 자체 |
| 4 | Grafana 사이드카의 Secret 탐색 범위를 네임스페이스로 한정 | 중간 | 웹 앱 1개 → 전 Secret |
| 5 | K3s `--secrets-encryption` | 중간 — 컨트롤플레인 재시작, 기존 Secret 재기록 필요 | 스냅샷·백업 유출 |
| 6 | 앱 네임스페이스 restricted 전환 | 큼 — 파드 스펙·이미지 수정 | 컨테이너 탈출 경로 대부분 |

## 7. 새로 생기는 비용

- **PSA 는 파드 _생성_ 시점에만 본다.** 라벨을 달아도 이미 떠 있는 파드는 쫓겨나지 않는다. 대신 다음 롤아웃 때 파드가 안 뜬다. 그래서 enforce 전 `warn`/`audit` 단계와 dry-run 이 필수다. 이걸 건너뛰면 보안 조치가 장애가 된다.
- **예외 목록이 새 관리 대상이 된다.** 로그 수집기·노드 익스포터·스토리지처럼 원래 노드에 닿아야 하는 것들은 영원히 baseline 을 못 통과한다. 이들을 별도 네임스페이스에 모으고, 그 네임스페이스에 누가 파드를 만들 수 있는지를 RBAC 로 좁혀야 예외가 구멍이 안 된다.
- **저장 시 암호화는 키 관리 문제를 새로 만든다.** 암호화 키는 서버 노드에 파일로 놓인다. etcd 스냅샷만 새는 경우는 막지만, 노드 디스크가 통째로 새면 키도 같이 샌다. 키 회전 절차도 새로 생긴다.

## 8. 이 글의 한계

- 클러스터 **하나**의 실측이다. 연구용 홈랩이라 운영 조직 클러스터의 일반 분포를 대표하지 않는다.
- privileged·hostPath 같은 _설정_ 은 쟀지만, 실제 컨테이너 탈출을 시도해 보지는 않았다. "노드로 가는 문이 있다"이지 "열어 봤다"가 아니다.
- RBAC 는 ClusterRoleBinding 기준으로 셌다. 네임스페이스 단위 RoleBinding 으로 준 Secret 권한과 aggregated ClusterRole 은 이 표에 다 반영되지 않았을 수 있다.
- CIS Benchmark·NSA/CISA 하드닝 가이드 항목별 대조는 하지 않았다. 여기서는 쿠버네티스·K3s 공식 문서에 있는 기준만 썼다.

## 한 줄

**NetworkPolicy 가 "어디까지 닿나"를 정한다면, Pod Security·토큰·저장 시 암호화는 "닿은 다음 무엇을 할 수 있나"를 정한다.** 이 클러스터에서 가장 싼 조치(baseline 라벨 38개, 영향 0)가 가장 오래 안 돼 있었다. 보안은 기능이 없어서가 아니라, 켜는 사람이 없어서 비어 있는 경우가 많다.

## References

1. Kubernetes Documentation, *Pod Security Standards*. <https://kubernetes.io/docs/concepts/security/pod-security-standards/>
2. Kubernetes Documentation, *Pod Security Admission*. <https://kubernetes.io/docs/concepts/security/pod-security-admission/>
3. Kubernetes Documentation, *Enforce Pod Security Standards by Configuring the Built-in Admission Controller* (PSA 1.25 GA). <https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/>
4. Kubernetes Documentation, *Service Accounts* / *Configure Service Accounts for Pods* (`automountServiceAccountToken`). <https://kubernetes.io/docs/concepts/security/service-accounts/> · <https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/>
5. Kubernetes Documentation, *Role Based Access Control Good Practices* (Listing secrets · Workload creation · Minimize distribution of privileged tokens). <https://kubernetes.io/docs/concepts/security/rbac-good-practices/>
6. Kubernetes Documentation, *Secrets* (기본적으로 etcd 에 암호화 없이 저장). <https://kubernetes.io/docs/concepts/configuration/secret/>
7. Kubernetes Documentation, *Encrypting Confidential Data at Rest*. <https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/>
8. K3s Documentation, *Secrets Encryption* (`--secrets-encryption`, 기존 서버는 재시작 필요). <https://docs.k3s.io/security/secrets-encryption>
9. 1차 데이터: 대상 클러스터(v1.35.4+k3s1) 읽기 전용 조회 — `kubectl get ns,pods,clusterrolebindings,clusterroles -o json`, `kubectl auth can-i --list`, 네임스페이스별 `kubectl label --dry-run=server … pod-security.kubernetes.io/enforce=<level>`, `k3s secrets-encrypt status`. 2026-09-24.
