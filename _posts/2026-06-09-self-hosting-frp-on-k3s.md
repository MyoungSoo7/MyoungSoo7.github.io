---
layout: post
title: "K3s 에 frp 깔다가 5번 망한 이야기 — image tag · TOML scope · seccomp · entrypoint wrapper"
date: 2026-06-09 00:30:00 +0900
categories: [kubernetes, networking, debugging]
tags: [frp, reverse-tunnel, k3s, helm, argocd, gitops, troubleshooting, seccomp, toml]
---

> 자체 reverse tunnel 서버를 K3s 안에 깔고 싶었다. Cloudflare Tunnel 의 *self-host 카운터파트* 로.
> 한 번에 될 줄 알았다. *5번 PR* 거쳐서 됐다. 그 5번 다 *다른 종류의 함정* 이었다.

---

## TL;DR

| # | 함정 | 시간 |
|---|------|------|
| 1 | Helm chart 처음 작성, ArgoCD sync 실패 (단순) | 30분 |
| 2 | `snowdreamtech/frps:0.61.0` → Docker Hub 에 존재 안 함 | 15분 |
| 3 | TOML `[auth]` 다음의 `allowPorts` 가 *auth.allowPorts* 로 파싱 | 30분 |
| 4 | K8s seccomp 가 `su-exec` 의 `setgroups(2)` 차단 | 40분 |
| 5 | 위 해결책 — *entrypoint wrapper 우회*, `command:[/usr/bin/frps]` | 10분 |

각각 하나만 보면 *알 만한* 함정. 하지만 *순차적으로* 만나서 매번 *새로운 에러 메시지* 로 redirect 됨. 이게 *실 운영의 디버깅* 의 본질.

---

## 0. 배경 — 왜 자체 reverse tunnel 인가

이미 Cloudflare Tunnel 로 14 개 도메인을 외부 노출하고 있다. 잘 동작한다. 그런데 *왜 굳이 자체 reverse tunnel* ?

**이유 1 — 학습.**
Cloudflare Tunnel 은 *블랙박스*. 잘 동작하지만 *왜 잘 동작하는지* 모른다. token 만 박으면 끝. 반면 frp 는 *bindPort, control connection, proxy multiplexing, allowed port range* 같은 *모든 게 보임*. portfolio 의 *기술 깊이* 차원.

**이유 2 — GitOps.**
Cloudflare 의 hostname route 추가는 *대시보드 GUI 작업*. PR review 안 됨, 자동 rollback 안 됨, 코드로 재현 안 됨. frp 의 route 는 `frpc.toml` — git 으로 관리됨.

**이유 3 — 비교 시연.**
"같은 외부 노출 문제에 *2 가지 솔루션* 운영해 봤습니다" — 면접 자료. 단일 솔루션 의존이 아닌 *기술 선택의 trade-off* 를 안다는 증거.

이상 3 가지. 시작.

---

## 1. 함정 1 — chart 처음 작성, 의외로 잘 됨

helm chart 새로 만들 때 보통 *typo 1~2 개* 로 한 번은 실패한다. 이번엔 *helm lint 통과 + ArgoCD 가 sync* 까지 갔다. *너무 잘 풀려서* 오히려 불안했다. 이게 *함정 2 의 복선*.

```bash
helm lint charts/frp
# 1 chart(s) linted, 0 chart(s) failed
```

```
NAME       SYNC     HEALTH        REV
frp-prod   Synced   Progressing   ...
```

`Progressing` 인 채 *Pod 가 CrashLoopBackOff*. 다음 단계.

---

## 2. 함정 2 — Docker Hub 의 tag 가 없는 줄도 모르고

```bash
kubectl logs deploy/frp-frps
# json: unknown field "allowPorts"
```

당황. frp 의 *server config schema 에 `allowPorts` 가 없다* 는 메시지. 분명 [공식 docs](https://github.com/fatedier/frp) 에는 있는데?

*Docker Hub tag list* 를 보고 알았다 :

```
0.69.1, 0.69, 0.68.1, 0.52.3, 0.52.1, ...
```

내가 박은 `0.61.0` *없다*. Docker Hub 가 *없는 tag 에 대해 어떤 fallback* 하는지 명확하지 않은데, 어쨌든 *옛 frp 가 받아짐*. 옛 frp 는 *v0 config schema* — `allowPorts` 가 *다른 위치* 또는 *없음*. 그래서 "unknown field".

교훈 : **image tag 는 *반드시* 실재하는 것만**. `0.61.0` 같은 *그럴듯한 버전번호* 가 *없을 수 있다*. Docker Hub Tags API 로 *사전 확인* 또는 `latest` 명시.

수정 :
```yaml
image:
  repository: snowdreamtech/frps
  tag: "0.69.1"   # 실재하는 tag
```

다음 PR. 잘 되겠지.

---

## 3. 함정 3 — TOML section scope 의 이해 부족

```
kubectl logs deploy/frp-frps
# json: unknown field "allowPorts"
```

또?? 같은 에러? *image 는 진짜 0.69.1* 인데?

```bash
kubectl describe pod frp-frps-...
# Image: docker.io/snowdreamtech/frps:0.69.1   ← 맞음
```

그렇다면 `allowPorts` 가 정말 *해당 schema 에 없는* 거. 근데 *공식 docs* 에는 있다고? 다시 본다 :

> [frp v0.52+ config](https://github.com/fatedier/frp/blob/master/conf/frps_full_example.toml)

```toml
bindPort = 7000

[auth]
method = "token"
token = "..."

allowPorts = [{ start = 6000, end = 6100 }]
```

내 config 도 *겉보기엔* 동일. 그런데 *TOML spec 다시 읽기* :

> A table (or *section*) declared with `[name]` includes *all the subsequent key-value pairs* until the next `[name]` is declared.

**아.**

내 config :

```toml
bindPort = 7000

[auth]               ← 여기서부터 auth section 시작
method = "token"
token = "..."

allowPorts = [...]   ← 여전히 auth section!! → auth.allowPorts
```

frp 는 *auth.allowPorts* 라는 field 를 찾지 못함 → "unknown field allowPorts".

수정 :
```toml
bindPort = 7000
allowPorts = [{ start = 6000, end = 6100 }]   ← top-level 로 이동

[auth]
method = "token"
token = "..."
```

교훈 : **TOML 의 section 은 *명시적으로 끝나지 않음***. 다음 section 또는 *파일 끝* 까지 이어진다. top-level scalar 는 *모든 section 선언 이전에* 와야 함. JSON 의 *plain object* 처럼 *flat structure* 라고 헷갈리지 말 것.

다음 PR. 진짜 잘 되겠지.

---

## 4. 함정 4 — su-exec : Operation not permitted

```
kubectl logs deploy/frp-frps
# su-exec: setgroups(0): Operation not permitted
```

이건 *완전히 다른 차원*. config 가 아니라 *권한*.

분석 :
- `snowdreamtech/frps` 이미지의 entrypoint 는 `/entrypoint.sh`
- 내부 동작 : `exec su-exec frp:frp /usr/bin/frps -c /etc/frp/frps.toml`
- 즉 *root 로 시작 → su-exec 으로 unprivileged user (frp) 강하 → frps 실행*

이 패턴은 *Docker 환경* 에선 잘 동작. 왜 *K8s 에서 안 되는지*?

답 : **K8s 의 기본 seccomp profile 이 `setgroups(2)` 차단**. su-exec 는 *유효 group ID 를 바꾸려고* setgroups 호출 → seccomp 가 차단 → su-exec 가 *Operation not permitted* 출력 후 종료.

확인 :
```yaml
securityContext:
  runAsUser: 0   # 명시적 root 로 시작 시도해도
                 # seccomp 가 *system call level* 에서 차단하므로 root 도 의미 없음
```

해결책 후보 :
- **A. seccomp profile 변경** — `unconfined` 로. 보안 후퇴, 비추.
- **B. CAP_SYS_ADMIN 추가** — *훨씬* 위험. 절대 안 함.
- **C. entrypoint wrapper 우회** — su-exec 자체를 안 거치고 *frps 바이너리 직접* 실행.

C 가 정답. **이건 K8s 운영에서 *자주 만나는* 패턴**. 외부 image 의 entrypoint 가 *Docker 환경 가정* 으로 작성되면 K8s 의 *strict seccomp* 와 충돌. *image 의 custom entrypoint 를 신뢰하지 말고 직접 command 명시*.

---

## 5. 해결 5 — command: 로 직접 호출

Deployment 의 *args 만 박혀 있던* 부분을 *command + args 명시* 로 변경 :

```yaml
containers:
  - name: frps
    image: snowdreamtech/frps:0.69.1
    # image 의 ENTRYPOINT (/entrypoint.sh) 가 su-exec wrapper.
    # K8s seccomp 와 충돌 → 직접 frps 바이너리 호출.
    command: ["/usr/bin/frps"]
    args: ["-c", "/etc/frp/frps.toml"]
    securityContext:
      runAsUser: 0          # frps 가 root 로 실행
      runAsGroup: 0
      capabilities:
        drop: [ALL]         # 그러나 capability 가 *모두 없으므로*
                            # 의미상 비특권. setgroups 도 호출 안 함.
      allowPrivilegeEscalation: false
```

deploy. 로그 :

```
[I] frps uses config file: /etc/frp/frps.toml
[I] frps tcp listen on 0.0.0.0:7000
[I] frps started successfully
[I] dashboard listen on 0.0.0.0:7500
```

**됐다.**

---

## 6. 검증 — *진짜* 동작하는지

frpc 를 Mac 에서 띄워서 `localhost:7780` (Python http server) 를 frps 의 6001 로 reverse tunnel :

```toml
# frpc.toml on Mac
serverAddr = "<node-ip>"
serverPort = 30070

[auth]
method = "token"
token = "..."

[[proxies]]
name = "demo-http"
type = "tcp"
localIP = "127.0.0.1"
localPort = 7780
remotePort = 6001
```

cluster 안에서 frps pod 의 6001 호출 :

```bash
kubectl -n frp-prod exec deploy/frp-frps -- wget -q -O - http://localhost:6001/
# <h1>frpc reverse tunnel demo</h1>
# <p>이 HTML 은 Mac localhost:7780 에서 나옵니다.</p>
```

**Mac 의 localhost 가 K3s cluster 안에서 응답.** reverse tunnel 의 *정의 그대로*.

dashboard 도 :
```json
{"clientCounts": 1, "proxyTypeCount": {"tcp": 1}}
```

---

## 7. portfolio 자족화 — Mac 의존 제거

위 검증은 *Mac 의존*. Mac 자면 demo 죽음. 면접관이 *주간에* 접속하면 dashboard `clientCount=0` — *비어있어 보임*.

해결 : **frpc 도 cluster 안 Deployment 로**. 같은 chart 에 `frpc.yaml` 추가, `frpc.enabled` 토글. 노출 대상은 cluster 안의 `landing-prod` nginx :

```yaml
# values.yaml
frpc:
  enabled: true
  server: { addr: frp-frps, port: 7000 }   # 같은 ns 의 ClusterIP
  proxies:
    - name: landing-demo
      type: tcp
      localIP: landing.landing-prod.svc.cluster.local
      localPort: 8080
      remotePort: 6001
```

이러면 dashboard 가 *24/7 clientCount=1* 유지. Mac 안 꺼져도 됨.

---

## 8. 회고 — 5 함정의 *공통 구조*

순서대로 다시 보면 :

| # | layer | 원인 | 검증 방식 |
|---|-------|------|-----------|
| 1 | chart 작성 | 단순 typo | helm lint |
| 2 | image / registry | *없는 tag* fallback | Docker Hub Tags API |
| 3 | config schema (frp) | TOML section scope | 공식 example diff |
| 4 | runtime / OS | K8s seccomp ↔ su-exec | strace / pod logs |
| 5 | entrypoint convention | Docker 가정 wrapper | image inspect + command 명시 |

5 가지가 *서로 다른 layer* 의 함정. *상위 layer 의 에러 메시지가 하위 layer 를 가린다* — 가장 흔히 보던 디버깅 패턴.

내가 다음에 같은 *카테고리* 의 함정을 만나면 더 빨리 알아챌 거. 하지만 *새 카테고리* 가 또 있을 거. 그게 *시스템 운영의 본질*.

---

## 9. 부수 효과

- chart 가 *5 PR 의 디버깅 history* 로 *문서화*. README + 블로그 글 (=이 글) cross-link.
- *Cloudflare Tunnel vs frp 비교* 의 *실 운영 경험* 확보.
- *seccomp / capability / TOML / Docker Hub* 4 layer 의 *실 함정 카탈로그*.
- portfolio 의 14 번째 도메인 (frp.lemuel.co.kr) 추가.

소요 시간 : 약 2 시간 (디버깅 1.5h + portfolio 자족화 0.5h).
*함정 1 개당 평균 18분*. *함정 없었으면 30분*. 즉 *디버깅 비용 3 배*.

---

## 10. 마치며

> "이 코드는 *5 번 실패한* 끝에 돈다" 는 말이 *부끄러운 게 아니라 정직한* 거. *0 번 실패해서 돈다* 면 운이 좋거나 거짓말.

K8s 안에 외부 image 를 깔 때 *항상 4 가지를 의심* :

1. **image tag 가 실재하는가** (Docker Hub Tags API 로 확인)
2. **config 의 schema 가 진짜 그 위치에 있는가** (TOML section / JSON path)
3. **entrypoint 가 K8s seccomp 와 호환되는가** (su-exec / gosu / tini 같은 wrapper 의심)
4. **권한 모델이 *image 가정* 과 *K8s 정책* 모두 만족하는가**

이 4 개 다 만족하는 chart 는 *처음부터 1 회만에 동작*. 안 만족하면 *5 회 PR*. 무엇이 *얼마나 만족 안 되는지* 사전에 알 방법은 없음. 그래서 *디버깅 능력* 이 *작성 능력* 만큼 중요한 거.

→ chart 보기 : `charts/frp/` ([helm-deploy repo](https://github.com/MyoungSoo7/helm-deploy/tree/master/charts/frp))
→ 동작 확인 : https://frp.lemuel.co.kr (dashboard, admin 인증)
