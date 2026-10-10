---
layout: post
title: "[CS300 #256] 컨테이너와 쿠버네티스 보안 — 커널을 나눠 쓰는 격리의 한계와 보완"
date: 2026-10-10 22:16:00 +0900
categories: [cs]
tags: [cs300, security, kubernetes, container-security, pod-security]
---

컴퓨터공학 300 주제 시리즈의 256번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

컨테이너는 가상 머신이 아니라 **커널을 공유하는 프로세스**이므로, 격리는 리눅스 기능(네임스페이스·cgroup·capability·seccomp)을 얼마나 조여 쓰느냐에 달려 있고, 쿠버네티스에서는 이를 Pod Security Standards·RBAC·NetworkPolicy·시크릿 관리로 클러스터 전체에 강제한다.

## 왜 필요한가

컨테이너가 배포 단위가 되면서 공격 표면이 바뀌었다. 이미지 안의 오래된 패키지, root 로 도는 프로세스, 노드의 도커 소켓을 마운트한 파드, 모든 시크릿을 읽을 수 있는 서비스 어카운트. 하나의 웹 앱 취약점이 이런 설정을 만나면 **컨테이너 → 노드 → 클러스터 전체**로 번진다.

쿠버네티스의 기본값은 호환성을 위해 상당히 열려 있다. 아무 설정 없이 만든 파드는 root 로 실행될 수 있고, 서비스 어카운트 토큰이 자동 마운트되며, 다른 모든 파드와 네트워크로 통신할 수 있다. 보안은 "켜야 생기는" 설정이 많다. 그래서 무엇을 켜야 하는지 아는 것이 곧 쿠버네티스 보안이다.

## 핵심 개념

### 컨테이너 격리를 만드는 리눅스 기능

| 기능 | 하는 일 | 깨지면 |
|---|---|---|
| 네임스페이스(pid, net, mnt, user 등) | 보이는 범위를 나눈다 | hostPID·hostNetwork 로 공유하면 노드 프로세스·네트워크가 보인다 |
| cgroup | 자원 사용량 제한 | limit 이 없으면 한 컨테이너가 노드 메모리를 다 쓴다 |
| capability | root 권한을 잘게 나눈다 | `privileged` 는 사실상 전부 허용 |
| seccomp | 호출 가능한 시스템 콜 제한 | 커널 취약점 공격 표면이 넓어진다 |
| LSM(AppArmor, SELinux) | 파일·자원 접근 강제 통제 | 추가 방어선이 사라진다 |

가상 머신과 결정적으로 다른 점은 **커널이 하나**라는 것이다. 커널 취약점 하나가 모든 컨테이너의 경계를 무너뜨릴 수 있다. NIST SP 800-190 이 컨테이너 보안을 이미지·레지스트리·오케스트레이터·컨테이너·호스트 OS 다섯 층의 위험으로 나눠 보는 것도 이 때문이다.

### 이미지 보안

- **작은 기반 이미지**: 셸·패키지 관리자가 없는 distroless·최소 이미지는 공격자가 쓸 도구도, 스캐너가 찾을 취약점도 적다.
- **취약점 스캔**: 빌드 시와 레지스트리 보관 중에 주기적으로 스캔한다. 오늘 깨끗한 이미지도 내일 새 CVE 가 나온다.
- **비밀 금지**: 이미지 레이어에 들어간 키는 이후 레이어에서 지워도 남는다.
- **다이제스트 고정**: `app:latest` 대신 `app@sha256:...` 로 참조하면 같은 내용이 보장된다. 서명 검증은 다음 글(공급망 보안)에서 다룬다.

### 파드 보안: Pod Security Standards

쿠버네티스는 세 단계의 표준 프로파일을 정의한다.

| 프로파일 | 대상 | 요지 |
|---|---|---|
| Privileged | 시스템·인프라 컴포넌트 | 제한 없음 |
| Baseline | 일반 앱의 최소선 | 알려진 권한 상승 막기: privileged·host 네임스페이스·hostPath 금지, 위험 capability 추가 금지 |
| Restricted | 보안 중시 앱 | Baseline + non-root 실행, `allowPrivilegeEscalation: false`, capability 전부 drop(`NET_BIND_SERVICE` 추가만 허용), seccomp `RuntimeDefault` 또는 `Localhost` |

내장 Pod Security Admission 이 네임스페이스 레이블로 이를 강제한다.

```
kubectl label ns my-app \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted
```

`enforce` 는 위반 파드 생성을 거부하고, `warn`·`audit` 은 경고와 감사 기록만 남긴다. 기존 네임스페이스에 적용할 때는 `warn` 으로 먼저 영향을 본다.

### 클러스터 수준

- **RBAC 최소 권한**: 와일드카드(`*`) 권한, `cluster-admin` 바인딩, 시크릿 `list`·`watch` 권한, 파드 생성 권한(파드를 만들 수 있으면 그 네임스페이스의 시크릿과 서비스 어카운트를 쓸 수 있다)을 특히 경계한다.
- **서비스 어카운트 토큰**: API 를 안 쓰는 파드는 `automountServiceAccountToken: false`.
- **시크릿**: 저장 시 암호화를 켜고, 시크릿을 읽을 수 있는 주체를 최소화한다. 환경 변수보다 파일 마운트가 로그·덤프로 덜 샌다.
- **NetworkPolicy**: 네임스페이스 기본 거부 후 필요한 흐름만.
- **API 서버와 kubelet**: 인터넷에 직접 노출하지 않는다. 감사 로그를 켠다.

## 직접 해 보기

파드 매니페스트를 읽어 Restricted 프로파일과 운영 모범 사례 위반을 찾는 작은 검사기다. PyYAML 이 필요하다(`yaml.safe_load` 를 쓴다는 점도 앞 글의 시큐어 코딩과 이어진다).

```python
import yaml   # PyYAML

BAD = """
apiVersion: v1
kind: Pod
metadata: {name: legacy-app}
spec:
  hostNetwork: true
  containers:
  - name: app
    image: example.registry/app:latest
    securityContext:
      privileged: true
    volumeMounts: [{name: docker, mountPath: /var/run/docker.sock}]
  volumes:
  - name: docker
    hostPath: {path: /var/run/docker.sock}
"""

GOOD = """
apiVersion: v1
kind: Pod
metadata: {name: hardened-app}
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    seccompProfile: {type: RuntimeDefault}
  containers:
  - name: app
    image: example.registry/app@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: {drop: [ALL]}
    resources:
      limits: {memory: 256Mi, cpu: 500m}
"""

def lint(doc):
    pod = yaml.safe_load(doc); spec = pod["spec"]; psc = spec.get("securityContext", {})
    out = []
    for k in ("hostNetwork", "hostPID", "hostIPC"):
        if spec.get(k): out.append(f"{k}: 노드 네임스페이스 공유")
    if any("hostPath" in v for v in spec.get("volumes", [])):
        out.append("hostPath 볼륨: 노드 파일시스템 노출")
    if spec.get("automountServiceAccountToken", True):
        out.append("SA 토큰 자동 마운트(필요 없으면 끄기)")
    for c in spec["containers"]:
        sc = c.get("securityContext", {})
        n = c["name"]
        if sc.get("privileged"): out.append(f"[{n}] privileged")
        if sc.get("allowPrivilegeEscalation", True): out.append(f"[{n}] allowPrivilegeEscalation 미차단")
        if not (sc.get("runAsNonRoot") or psc.get("runAsNonRoot")): out.append(f"[{n}] runAsNonRoot 아님")
        if "ALL" not in sc.get("capabilities", {}).get("drop", []): out.append(f"[{n}] capabilities drop ALL 아님")
        seccomp = sc.get("seccompProfile") or psc.get("seccompProfile") or {}
        if seccomp.get("type") not in ("RuntimeDefault", "Localhost"): out.append(f"[{n}] seccomp 프로파일 없음")
        if "@sha256:" not in c["image"]: out.append(f"[{n}] 이미지가 다이제스트로 고정되지 않음")
        if "limits" not in c.get("resources", {}): out.append(f"[{n}] 자원 limit 없음")
    return out

for name, doc in (("BAD", BAD), ("GOOD", GOOD)):
    r = lint(doc)
    print(f"{name}: {len(r)}건"); [print("  -", x) for x in r]
```

실행 결과(Python 3.12, PyYAML 6):

```
BAD: 10건
  - hostNetwork: 노드 네임스페이스 공유
  - hostPath 볼륨: 노드 파일시스템 노출
  - SA 토큰 자동 마운트(필요 없으면 끄기)
  - [app] privileged
  - [app] allowPrivilegeEscalation 미차단
  - [app] runAsNonRoot 아님
  - [app] capabilities drop ALL 아님
  - [app] seccomp 프로파일 없음
  - [app] 이미지가 다이제스트로 고정되지 않음
  - [app] 자원 limit 없음
GOOD: 0건
```

BAD 매니페스트의 `hostPath: /var/run/docker.sock` 은 특히 위험하다. 컨테이너 런타임 소켓에 접근하면 노드 위에 원하는 컨테이너를 마음대로 띄울 수 있어, 사실상 노드 root 와 같다. 이 검사기는 교육용이다. 실제로는 Pod Security Admission 으로 강제하고, 더 넓은 규칙은 Kyverno·OPA Gatekeeper 같은 정책 엔진이나 kube-score·Trivy 같은 검사 도구를 쓴다.

## 현업에서는

- **단계적 적용**: 전 네임스페이스에 `warn=restricted`, `enforce=baseline` 부터 걸고, 경고가 사라진 네임스페이스부터 `enforce=restricted` 로 올린다. CNI·스토리지·모니터링 에이전트처럼 노드 권한이 진짜 필요한 것은 별도 네임스페이스에 `privileged` 로 격리한다.
- **홈랩 k3s 에서 흔한 구멍**: 헬름 차트 기본값이 root 실행·쓰기 가능한 루트 파일시스템인 경우가 많다. `values.yaml` 의 `securityContext` 를 반드시 확인한다. 또 노드 디스크를 쓰려고 hostPath 를 쉽게 쓰는데, 경로를 좁히고 `readOnly` 로 마운트한다.
- **자원 limit 도 보안이다**: 메모리 limit 없는 파드 하나가 노드를 OOM 으로 몰면 같은 노드의 다른 서비스까지 멈춘다. 가용성 침해다.
- **런타임 탐지**: Falco 같은 도구로 "컨테이너 안에서 셸 실행", "민감 파일 읽기" 같은 이벤트를 감지해 SIEM 으로 보낸다.

## 확인 문제

1. 컨테이너 격리가 가상 머신보다 약하다고 하는 근본 이유는?
2. Pod Security Standards 의 세 프로파일을 대상과 함께 설명하라.
3. 파드에 컨테이너 런타임 소켓을 hostPath 로 마운트하는 것이 위험한 이유는?
4. API 를 호출하지 않는 앱 파드에서 서비스 어카운트 토큰 자동 마운트를 끄는 이유는?
5. 기존 클러스터에 Restricted 를 바로 `enforce` 하지 않고 `warn` 부터 거는 이유는?

### 풀이

1. 모든 컨테이너가 호스트 커널 하나를 공유하므로 커널 취약점이나 과한 권한 설정이 곧 경계 붕괴로 이어진다.
2. Privileged(시스템 컴포넌트, 제한 없음), Baseline(일반 앱, 알려진 권한 상승 경로 차단), Restricted(보안 중시 앱, non-root·capability 전부 drop·seccomp 등 하드닝 강제).
3. 런타임 API 로 노드에 임의 컨테이너(특권 포함)를 띄울 수 있어 노드 root 권한과 같다.
4. 앱이 털렸을 때 공격자가 토큰으로 쿠버네티스 API 를 호출하는 경로를 없앤다.
5. 기존 워크로드가 위반하면 재배포·재시작 때 파드 생성이 거부되어 장애가 난다. 경고로 영향 범위를 먼저 확인한다.

## 더 읽을거리 (References)

- Kubernetes, [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- Kubernetes, [Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- Kubernetes, [Role Based Access Control Good Practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)
- NIST, [SP 800-190: Application Container Security Guide](https://csrc.nist.gov/pubs/sp/800/190/final)
