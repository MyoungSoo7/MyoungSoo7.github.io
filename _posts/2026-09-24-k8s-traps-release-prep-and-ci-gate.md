---
layout: post
title: "k8s-traps 공개 준비기 — 토큰 없는 배포 파이프라인, 그리고 우리 CI 에 먼저 물려 본 결과"
date: 2026-09-24 04:24:26 +0900
categories: [kubernetes, mcp]
tags: [k8s-traps, mcp, mcp-registry, pypi, trusted-publishing, github-actions, argocd, server-side-apply, secrets]
---

린터는 통과하는데 운영에서 조용히 깨지는 쿠버네티스 매니페스트가 있다. 그런 함정 7개를 잡는 도구 [k8s-traps](https://github.com/MyoungSoo7/k8s-traps) 를 만들었다. CLI 이면서 MCP 서버라서, AI 에이전트가 YAML 을 내보내기 전에 물어볼 수 있다.

이 글은 두 가지 기록이다.

1. [PyPI](https://pypi.org/) 와 [공식 MCP 레지스트리](https://registry.modelcontextprotocol.io/) 에 올릴 파이프라인을 **API 토큰 한 줄 없이** 짠 과정.
2. 공개하기 전에 **우리 운영 리포의 CI 에 먼저 물려 본 결과.** 실제 비밀번호 3건을 잡았고, 도구가 놓친 것도 1건 있었다.

**현재 상태를 먼저 적는다.** 이 글을 쓰는 시점(2026-09-24)에 k8s-traps 는 아직 PyPI 와 MCP 레지스트리에 **없다.** 파이프라인은 준비됐고, 남은 일은 PyPI 에 "pending publisher" 를 등록하는 것 하나다. 이건 PyPI 계정 로그인이 필요해서 사람이 해야 한다. 등록 후 결과는 이 글 끝에 덧붙인다. 그 전까지는 GitHub 에서 바로 설치할 수 있다(아래 [설치](#설치)).

## 무엇을 만들었나

7개 함정은 전부 우리 K3s 클러스터에서 실제로 겪은 장애에서 나왔다.

| ID | 함정 | 기본 심각도 |
| --- | --- | --- |
| T01 | Service 이름이 앱 설정 이름과 겹쳐, 쿠버네티스가 주입하는 `<SVC>_PORT=tcp://…` 환경변수가 설정을 덮어씀 | high |
| T02 | ServiceMonitor 가 Service 가 아니라 파드 라벨을 골라 아무것도 수집하지 않음 | high |
| T03 | 워크로드는 있는데 NetworkPolicy 가 하나도 없는 네임스페이스 | medium |
| T04 | `subPath` 로 마운트한 ConfigMap·Secret 이 갱신되지 않음 | low |
| T05 | 호스트명 두 개가 같은 백엔드로 라우팅됨 (죽은 규칙이 남의 앱을 200 으로 서빙) | medium |
| T06 | replicas 가 노드 분산을 *선호*만 함 | medium |
| T07 | 비밀값이 평문으로 적힘 (출력에는 값을 싣지 않음) | high |

T01 은 쿠버네티스 문서에 명시된 동작이다. kubelet 은 파드가 뜰 때 같은 네임스페이스의 Service 마다 `{SVCNAME}_SERVICE_HOST`, `{SVCNAME}_PORT` 같은 변수를 넣어 준다 ([Kubernetes: Service — Environment variables](https://kubernetes.io/docs/concepts/services-networking/service/#environment-variables)). Service 이름이 `server` 이면 `SERVER_PORT=tcp://10.x.x.x:80` 이 들어온다. Spring Boot 는 그걸 자기 포트 설정으로 읽으려다 죽는다.

Kubescape·kube-linter 같은 범용 스캐너는 리소스 한도나 권한 같은 기본 점검을 잘한다. 이 도구는 그것들을 대체하지 않는다. 그것들이 보지 않는, *문법상 멀쩡한* 설정만 본다. 입력으로 받은 YAML 만 오프라인으로 읽고, 클러스터에는 접속하지 않는다.

## 공개 전에: 오탐부터 줄였다

첫 버전을 우리 helm-deploy 리포의 차트 40개를 렌더한 결과(렌더 성공 39개)에 돌려 보니 T01 HIGH 가 **207건** 나왔다. 거의 전부 오탐이었다. 원인은 셋이었다.

1. **namespace 가 없는 렌더를 한 네임스페이스로 묶었다.** `helm template` 출력에는 대개 `metadata.namespace` 가 없다. 이걸 전부 같은 네임스페이스로 보면 차트 39개의 Service 가 서로에게 환경변수를 주입하는 것처럼 계산된다. 입력 하나(파일 하나 또는 렌더 하나)를 네임스페이스 하나로 보도록 바꿨다.
2. **"이름이 같으면 위험" 을 HIGH 로 뒀다.** 진짜 HIGH 는 컨테이너가 `<PREFIX>_PORT` 같은 변수를 실제로 *참조* 할 때뿐이다. 알려진 충돌(`server`→Spring 의 `SERVER_PORT`, `kafka`, `jenkins`)은 MEDIUM 으로, 이름만 같은 경우는 LOW 로 내렸다.
3. **같은 워크로드를 컨테이너마다 반복 보고했다.** 워크로드당 1건으로 줄였다.

T07 도 `DISABLE_ADMIN_TOKEN=false` 를 비밀값으로 잡았다. 이름에 TOKEN 이 들어갔을 뿐 값은 불리언이다. `true/false`·숫자만 있는 값은 빼도록 고쳤다.

테스트는 40개다. 함정마다 *잡아야 하는* 케이스와 *잡으면 안 되는* 케이스를 하나 이상 둔다.

## 배포 설계: 비밀을 두지 않는 파이프라인

올릴 곳은 두 군데다.

- **PyPI**: 실제 패키지(휠)가 올라가는 곳.
- **MCP 레지스트리**: 패키지를 호스팅하지 않고 *메타데이터만* 둔다. 레지스트리 문서가 이 점을 분명히 한다 — "The MCP Registry only hosts metadata, not artifacts" ([MCP Registry quickstart](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)). 그래서 순서가 정해진다. PyPI 가 먼저다.

두 곳 다 GitHub Actions 의 OIDC 토큰으로 인증할 수 있다. 그래서 장기 토큰을 하나도 만들지 않았다. 저장소에도, GitHub Secrets 에도 없다.

### 1. PyPI: 신뢰할 수 있는 게시자(Trusted Publishing)

PyPI 의 Trusted Publishing 은 CI 가 발급한 OIDC 토큰을 PyPI 가 검증하고, **15분짜리** 단기 API 토큰으로 바꿔 주는 방식이다 ([PyPI Docs: Trusted Publishers](https://docs.pypi.org/trusted-publishers/)). 유출돼도 곧 만료된다.

아직 없는 프로젝트는 "pending publisher" 로 시작한다. 계정 설정에서 프로젝트 이름·소유자·리포·워크플로 파일·environment 를 등록해 두면, 첫 게시 때 프로젝트가 만들어진다 ([Creating a PyPI Project with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)).

| 항목 | 값 |
| --- | --- |
| PyPI Project Name | `k8s-traps` |
| Owner | `MyoungSoo7` |
| Repository name | `k8s-traps` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

함정이 하나 있다. 같은 문서에 따르면 pending publisher 는 **이름을 예약하지 않는다.** 등록해 두고 첫 게시 전에 누가 그 이름을 먼저 가져가면 무효가 된다. 그래서 등록과 첫 태그 push 는 붙여서 하기로 했다. 이 글을 쓰는 지금 등록을 미뤄 둔 이유이기도 하다. 파이프라인이 먼저 준비돼 있어야 등록 직후 바로 태그를 올릴 수 있다.

### 2. MCP 레지스트리: 이름 증명과 OIDC 로그인

레지스트리는 두 가지를 확인한다.

**이름 공간 소유.** GitHub 로 인증하면 서버 이름은 `io.github.<사용자>/` 로 시작해야 한다. 그래서 이름은 `io.github.MyoungSoo7/k8s-traps` 다.

**패키지 소유.** PyPI 패키지는 PyPI 에 올라간 README(= PyPI 의 long description)에 `mcp-name: <서버 이름>` 문자열이 있어야 한다. 주석 안에 숨겨도 되지만, 토큰 뒤에는 줄바꿈·공백·`-->` 같은 경계가 와야 한다 ([MCP Registry: Package Types — PyPI](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx)). README 에는 이렇게 넣었다.

```html
<!-- mcp-name: io.github.MyoungSoo7/k8s-traps -->
```

레지스트리는 *PyPI 에 올라간* README 를 본다. 로컬 README 만 고치고 PyPI 버전을 다시 올리지 않으면 레지스트리 등록은 계속 실패한다.

메타데이터는 `server.json` 한 파일이다.

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.MyoungSoo7/k8s-traps",
  "title": "k8s-traps",
  "description": "Finds Kubernetes manifest traps that pass linters and still break production. Offline, read-only.",
  "repository": { "url": "https://github.com/MyoungSoo7/k8s-traps", "source": "github" },
  "version": "0.1.0",
  "packages": [{
    "registryType": "pypi", "identifier": "k8s-traps", "version": "0.1.0",
    "runtimeHint": "uvx", "transport": { "type": "stdio" },
    "packageArguments": [{ "type": "named", "name": "--mcp" }]
  }]
}
```

로컬에서 `mcp-publisher validate` 로 스키마를 확인했다. 로그인은 `mcp-publisher login github-oidc` 다. 워크플로에 `id-token: write` 권한만 주면 되고 비밀은 필요 없다. 레지스트리 문서도 PAT 보다 OIDC 를 권장한다 ([MCP Registry: GitHub Actions](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx)).

### 3. 한 워크플로로 묶기

`v*` 태그를 push 하면 `release.yml` 이 세 잡을 순서대로 돌린다.

```text
test  ──►  pypi  ──►  mcp-registry
(CI 재사용)  (빌드 + 게시)  (PyPI 반영 대기 → 로그인 → publish)
```

- **test**: 평소 CI(`ci.yml`)를 `workflow_call` 로 그대로 재사용한다. 파이썬 3.10·3.12·3.14 매트릭스다.
- **pypi**: environment `pypi` 에서 돈다. 먼저 태그 버전이 `pyproject.toml` 과 `server.json` 두 곳의 버전과 같은지 확인하고, 다르면 멈춘다. 레지스트리에는 `server.json` 의 버전이, PyPI 에는 `pyproject.toml` 의 버전이 올라가기 때문이다. 둘이 어긋나면 레지스트리가 존재하지 않는 PyPI 버전을 가리키게 된다. 확인이 끝나면 `pipx run build` 로 빌드하고 [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish) 로 올린다.
- **mcp-registry**: PyPI 가 새 버전을 JSON API 로 내줄 때까지 기다린다(최대 5분). 안 기다리면 레지스트리가 README 를 확인하러 갔을 때 패키지가 아직 없을 수 있다. 그다음 `mcp-publisher` 를 받아 로그인하고 게시한다.

### 4. 게시 전에 찾은 버그: uvx 는 어떤 스크립트를 띄우나

`runtimeHint: "uvx"` 를 보고 클라이언트는 `uvx k8s-traps` 를 실행한다. uvx 는 패키지와 이름이 같은 스크립트를 띄운다. 이 패키지에서 그 이름은 MCP 서버(`k8s-traps-mcp`)가 아니라 CLI(`k8s-traps`)다. 그대로 올렸다면 레지스트리를 보고 설치한 사람은 stdin 을 YAML 로 읽으려는 CLI 를 받았을 것이다. `mcp-publisher validate` 는 이걸 못 잡는다. 스키마상으로는 문제가 없기 때문이다.

그래서 CLI 에 `--mcp` 플래그를 넣고, `server.json` 의 `packageArguments` 로 그 플래그를 넘기게 했다. 레지스트리는 `uvx k8s-traps --mcp` 를 실행하게 된다. 이 경로가 실제로 MCP `initialize` 에 응답하는지는 서브프로세스 테스트로 고정했다.

## 공개 전에 우리 CI 에 먼저 물렸다

남에게 쓰라고 내놓기 전에 우리 운영 리포(helm-deploy, ArgoCD 가 배포하는 차트 40여 개)의 CI 게이트로 먼저 붙였다. 결과는 세 가지였다.

### 차트 기본값이 아니라 "배포되는 모양" 을 검사해야 한다

차트를 기본 values 로 렌더하면 운영과 다른 것을 검사하게 된다. 그래서 게이트는 ArgoCD Application 마다 그 릴리스명·네임스페이스·valueFiles 로 렌더한다. 결과는 36개 앱, 오브젝트 251개였다.

namespace 도 직접 넣었다. 위에서 "입력 하나 = 네임스페이스 하나" 로 오탐을 줄였는데, 우리 리포에서는 그 가정이 틀린다. 서로 다른 차트 두 개가 같은 네임스페이스에 배포되기 때문이다. T01(Service 링크 변수는 네임스페이스 전체에서 주입된다)과 T03(NetworkPolicy 가 다른 차트에 있을 수 있다)은 네임스페이스 단위로 봐야 맞다. 그래서 각 오브젝트에 Application 의 destination 네임스페이스를 박아 넣고 한 번에 검사한다.

게이트는 HIGH 만 막는다. 처음엔 MEDIUM·LOW 를 집계로 같이 찍었다. 그런데 "NetworkPolicy 없는 네임스페이스 33건" 같은 줄이 매번 똑같이 나와서 소음이 됐다. 지금은 HIGH 만 출력한다.

CI 쪽에서도 하나 걸렸다. 게이트 앞 단계(기존 차트 가드)가 다른 이유로 빨간불이면, 뒤 단계인 k8s-traps 는 **skipped** 가 된다. 실패가 아니라 "안 돌았음" 이라 눈에 잘 안 띈다. 스텝에 `if: ${{ !cancelled() }}` 를 달아 앞 단계 결과와 상관없이 돌게 했다 ([GitHub Docs: Status check functions](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions)).

### 잡은 것: 실제 DB 비밀번호 3건

첫 실행에서 HIGH 는 T07 3건이었다. 세 서비스(crypto·sns·trading)의 DB 비밀번호가 `values.yaml` 에 평문으로 있었다. 확인해 보니 자리표시자가 아니라 **운영 중인 실제 값**이었다. 리포가 비공개라 바로 사고로 이어지진 않았지만, 리포 접근 권한이 곧 DB 접근 권한이었던 셈이다.

두 단계로 고쳤다.

1. **참조 방식 바꾸기.** 값은 그대로 두고 env 를 `valueFrom.secretKeyRef` 로 바꿨다. 클러스터에 이미 같은 값의 Secret 이 있어서(값은 출력하지 않고 해시만 비교했다) 파드 재시작만으로 끝난다. 쿠버네티스도 비밀값은 Secret 에 두라고 권한다 ([Kubernetes: Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)).
2. **비밀번호 교체.** git 기록에는 옛 평문이 남는다. 그래서 세 DB 모두 새 랜덤값으로 바꿨다. 순서는 `ALTER USER` → Secret 갱신 → 앱 재시작이다. 확인은 양쪽으로 했다. 옛 비밀번호는 `password authentication failed` 로 거부되고, 새 비밀번호로는 접속된다. 비밀번호는 명령행 인자가 아니라 stdin 으로 넘겨서, 프로세스 목록에도 남지 않게 했다.

### 반영 중 걸린 것: ArgoCD 가 sync 를 못 했다

git 을 고쳐 push 했는데 세 앱 모두 ArgoCD 상태가 `Unknown` 이 됐다. 메시지는 이랬다.

```text
Deployment.apps "crypto-app" is invalid:
spec.template.spec.containers[0].env[4].valueFrom: Invalid value: "":
may not be specified when `value` is not empty
```

우리 ArgoCD 는 Server-Side Diff 를 쓴다. 리소스마다 Server-Side Apply 를 dry-run 으로 돌려서 예상 결과를 만들고, 그걸 라이브 상태와 비교한다 ([Argo CD: Diff Strategies](https://argo-cd.readthedocs.io/en/stable/user-guide/diff-strategies/)).

문제는 Server-Side Apply 의 필드 소유 규칙이다. 매니페스트에서 필드를 빼고 apply 하면, 그 필드는 **다른 매니저가 소유하지 않을 때만** 지워진다 ([Kubernetes: Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/)). 옛 평문 `value` 는 예전 Update 작업이 소유하고 있었다. 그래서 새 매니페스트에 없어도 지워지지 않았다. 결국 한 env 항목에 옛 `value` 와 새 `valueFrom` 이 같이 남은 모양이 됐고, API 서버가 그걸 거부했다. 클라이언트 측 apply 에서 옮겨 온 필드가 이렇게 "안 지워지는" 문제는 쿠버네티스 이슈로도 보고돼 있다 ([kubernetes#99003](https://github.com/kubernetes/kubernetes/issues/99003)).

해결은 그 env 항목 하나를 라이브 오브젝트에서 git 과 똑같은 모양으로 교체하는 것이었다(`kubectl patch --type=json` 의 `replace`). 그 뒤 세 앱 모두 Synced/Healthy 가 됐다. 평문 `value` 를 `valueFrom` 으로 바꾸는 변경은 GitOps 만으로는 끝나지 않을 수 있다는 걸 알아 두면 좋다.

### 놓친 것: JWT 서명키

같은 리포를 사람이 다시 훑다가 하나를 더 찾았다. 한 서비스의 JWT 서명키가 `SWKEY` 라는 이름으로 `values.yaml` 에 있었다. 값은 `sns-jwt-secret-placeholder-…` 로 시작하는 **자리표시 문자열 그대로**였다. 리포를 읽을 수 있으면 로그인 토큰을 위조할 수 있는 상태였다.

k8s-traps 는 이걸 못 잡았다. T07 은 이름에 `PASSWORD`·`SECRET`·`TOKEN`·`KEY` 같은 단어가 들어간 변수를 본다. `SWKEY` 는 그 어느 패턴에도 걸리지 않는다. 이름 기반 휴리스틱의 한계이고, README 에도 "휴리스틱이라 오탐·미탐이 있다" 고 적어 두었다.

서명키는 새 랜덤값으로 바꿔 SOPS 로 암호화한 Secret 으로 옮겼다. 대가로 기존 로그인 토큰은 전부 무효가 되어 사용자가 다시 로그인해야 한다. 파드 안의 키가 새 값과 같은지는 값 대신 해시로 비교했다.

정리하면 첫 적용에서 이 도구는 HIGH 3건을 잡았고, 같은 종류의 문제 1건을 놓쳤다. "도구가 0건이라고 했다" 가 "문제가 없다" 는 뜻은 아니다.

## 결과

2026-09-24 04:22 KST 기준 실측이다.

- **helm-deploy CI 게이트**: 동작 중이다. HIGH 3건을 해소했고, 지금은 `HIGH 0건 / OK` 다.
- **PyPI**: `https://pypi.org/pypi/k8s-traps/json` → 404. 아직 게시 전이다.
- **MCP 레지스트리**: `servers?search=k8s-traps` → `"count":0`. 아직 게시 전이다.
- **남은 일**: PyPI pending publisher 등록(사람) → `v0.1.0` 태그 push. 나머지는 워크플로가 한다. 결과가 나오면 이 글에 덧붙인다.

## 설치

PyPI 게시 전까지는 GitHub 에서 바로 설치한다. 빈 가상환경에서 아래 명령으로 설치되고 두 실행 파일(`k8s-traps`, `k8s-traps-mcp`)이 생기는 것을 확인했다.

```bash
pip install "git+https://github.com/MyoungSoo7/k8s-traps"
helm template my-chart | k8s-traps            # stdin
k8s-traps manifests/ --fail-on high           # 파일·디렉터리, 기준 이상이면 exit 1
k8s-traps --list
```

예를 들어 env 에 평문 비밀번호가 있는 Deployment 를 넣으면 이렇게 나온다. 값 자체는 출력하지 않고 길이만 알려 준다.

```text
[HIGH] T07 Deployment/demo/api (container api)
  env DB_PASSWORD has a literal value (17 chars, not shown).
  fix: Move the value into a Secret (ideally encrypted in git with SOPS or sealed-secrets) and reference it with valueFrom.secretKeyRef or envFrom.secretRef.
```

MCP 클라이언트 설정(설치 후):

```json
{ "mcpServers": { "k8s-traps": { "command": "k8s-traps-mcp" } } }
```

## 정리

- MCP 레지스트리는 메타데이터만 둔다. PyPI 가 먼저고, 레지스트리 게시는 그 뒤에 온다.
- PyPI 패키지의 소유 증명은 *PyPI 에 올라간 README* 의 `mcp-name:` 한 줄이다. 로컬 README 가 아니다.
- PyPI 와 MCP 레지스트리 둘 다 GitHub OIDC 로 인증할 수 있다. 그래서 저장소 어디에도 장기 토큰이 없다. 사람이 할 일은 PyPI 에 pending publisher 를 등록하는 것 하나다.
- 스키마 검증은 "실행하면 뭐가 뜨는가" 를 보지 않는다. `uvx` 가 CLI 를 띄우는 버그는 실행 테스트로만 잡혔다.
- 남에게 내놓기 전에 자기 운영 리포에 먼저 물려 보는 게 가장 싼 검증이었다. 오탐 207건과 진짜 비밀번호 3건, 그리고 놓친 1건이 거기서 나왔다.

## References

1. Kubernetes Documentation, *Service — Environment variables*. <https://kubernetes.io/docs/concepts/services-networking/service/#environment-variables>
2. Kubernetes Documentation, *Secrets*. <https://kubernetes.io/docs/concepts/configuration/secret/>
3. Kubernetes Documentation, *Server-Side Apply*. <https://kubernetes.io/docs/reference/using-api/server-side-apply/>
4. kubernetes/kubernetes, *Server-side apply: migration from client-side apply leaves stuck fields in the object* (#99003). <https://github.com/kubernetes/kubernetes/issues/99003>
5. Argo CD Documentation, *Diff Strategies*. <https://argo-cd.readthedocs.io/en/stable/user-guide/diff-strategies/>
6. GitHub Docs, *Evaluate expressions in workflows and actions — Status check functions*. <https://docs.github.com/en/actions/reference/workflows-and-actions/expressions>
7. PyPI Docs, *Publishing to PyPI with a Trusted Publisher*. <https://docs.pypi.org/trusted-publishers/>
8. PyPI Docs, *Creating a PyPI Project with a Trusted Publisher*. <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>
9. Model Context Protocol, *Quickstart: Publish an MCP Server to the MCP Registry*. <https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx>
10. Model Context Protocol, *MCP Registry Supported Package Types*. <https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx>
11. Model Context Protocol, *How to Automate Publishing with GitHub Actions*. <https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx>
12. PyPA, *gh-action-pypi-publish*. <https://github.com/pypa/gh-action-pypi-publish>
13. k8s-traps source. <https://github.com/MyoungSoo7/k8s-traps>
