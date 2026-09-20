---
layout: post
title: "네 줄 다 ✓ 인데 모델이 틀렸다 — 샌드박스 egress 허용목록 검증표 읽는 법"
date: 2026-09-20 19:08:38 +0900
categories: [ai, security]
tags: [nemoclaw, openshell, openclaw, sandbox, network-policy, allowlist, egress, verification, proxy]
---

샌드박스 밖으로 나가는 연결 네 개를 **정책 파일을 보고 먼저 예측**한 다음, 실제로 쳐보고 결과를 적은 표다. 세 번째 칸은 네 줄 모두 ✓ 다.

![샌드박스 egress 허용목록 예측·관측 대조표. github.com 은 brew 프리셋에 있어 허용 예측, 관측 200; api.github.com 은 github 프리셋 비활성이라 거부 예측, 관측 CONNECT 403; pypi.org 은 pypi 활성이라 허용 예측, 관측 200; integrate.api.nvidia.com 은 어느 프리셋에도 없다는 이유로 거부 예측, 관측 403. 네 줄 모두 일치 ✓]({{ '/assets/images/egress-allowlist-verification-table.jpg' | relative_url }})

| 예측 (정책에서) | 관측 | 일치 |
| --- | --- | --- |
| `github.com` — brew 프리셋에 있음 → 허용 | `200` | ✓ |
| `api.github.com` — github 프리셋 비활성 → 거부 | `CONNECT 403` | ✓ |
| `pypi.org` — pypi 활성 → 허용 | `200` | ✓ |
| `integrate.api.nvidia.com` — 어느 프리셋에도 없음 → 거부 | `403` | ✓ |

먼저 이 표를 칭찬하고 시작해야 공평하다. **예측을 먼저 썼다**는 것이 이 표의 자산이다. 결과를 보고 난 뒤에 쓰는 설명은 언제나 맞는다 — 틀릴 수가 없는 형식이기 때문이다. 그리고 네 줄 중 **둘이 거부 예상**이라는 점도 중요하다. 전부 허용 예상인 표는 "프록시가 아예 꺼져 있다"와 구별되지 않는다. 거부가 절반이면 음성 대조군이 있는 셈이다.

그런데 이 표가 증명한 것은 "정책을 이해했다"가 아니다. 네 번째 줄의 **이유가 틀렸다**. 그리고 그 사실은 같은 표의 두 번째 칸에 이미 적혀 있다.

## 네 번째 줄: 그 호스트는 baseline 에 있다

NemoClaw 는 샌드박스 네트워크 정책을 리포의 YAML 로 선언하고, 런타임 강제는 OpenShell 이 한다.[^1] 그 baseline 파일 `nemoclaw-blueprint/policies/openclaw-sandbox.yaml` 의 첫 블록이 이것이다.[^2]

```yaml
network_policies:
  nvidia:
    name: nvidia
    endpoints:
      - host: integrate.api.nvidia.com
        port: 443
        protocol: rest
        enforcement: enforce
        rules:
          - allow: { method: POST, path: "/v1/chat/completions" }
          - allow: { method: POST, path: "/v1/completions" }
          - allow: { method: POST, path: "/v1/embeddings" }
          - allow: { method: GET,  path: "/v1/models" }
          - allow: { method: GET,  path: "/v1/models/**" }
    binaries:
      - { path: /usr/local/bin/openclaw }
```

`integrate.api.nvidia.com` 은 **어느 프리셋에도 없는 호스트가 아니라, 프리셋보다 아래층인 baseline 에 들어 있는 호스트**다. 그리고 baseline 은 티어 선택과 무관하게 **항상** 적용된다 — Restricted 를 골라도 남아 있다.[^3] 프리셋은 그 위에 얹히는 것이다.

그러면 왜 거부됐나. 두 군데 중 하나다.

- `binaries` 가 `/usr/local/bin/openclaw` **한 줄뿐**이다. 테스트를 `curl` 로 쳤다면 호스트는 맞지만 호출한 바이너리가 안 맞는다.
- `protocol: rest` + `enforcement: enforce` 이므로 요청 단위로 method·path 를 본다. 허용된 조합은 위 다섯 개뿐이다. 루트 경로에 대한 평범한 `GET /` 은 그중 어디에도 없다.

판정은 맞았고, 이유는 다른 곳에서 왔다. 그리고 세 번째 칸은 그걸 잡아낼 수 없다 — **"거부/허용"만 비교하기 때문이다.**

## 관측 칸이 이미 답을 적어 놨다 — 403 두 개는 같은 403 이 아니다

두 번째 줄은 `CONNECT 403`, 네 번째 줄은 그냥 `403` 이다. 표를 쓴 사람이 이 차이를 **적어 놓고도** 예측 칸에 반영하지 않았다.

둘은 서로 다른 층에서 난 거부다.

- **`CONNECT 403`** — HTTPS 목적지에 대해 클라이언트는 먼저 프록시에 터널을 요청한다. 어느 정책 블록에서도 그 (호스트, 포트) 가 매칭되지 않으면 터널 자체가 거절된다. 이 응답은 **프록시만이 줄 수 있다.** 목적지 서버는 이 대화에 참여조차 못 했다.
- **맨 `403`** — 터널이 열린 뒤 HTTP 요청이 거부된 모양이다. `protocol: rest` 엔드포인트는 프록시가 TLS 를 종단해서 요청마다 method·path 규칙을 검사한다.[^4] 즉 호스트는 통과했고 **요청이** 막혔다.

그래서 네 번째 줄이 정말로 "어느 정책에도 없는 호스트"였다면 두 번째 줄과 **같은 모양으로** 거부됐어야 한다. 모양이 다르다는 것이 예측의 이유가 틀렸다는 증거다.

덧붙여, 맨 `403` 은 원 서버가 줬을 가능성도 열려 있다. 게이트웨이가 막은 403 과 목적지가 준 403 은 클라이언트 입장에서 구별이 안 된다. `CONNECT 403` 은 그 애매함이 없다. **거부 하나로 "누가 막았는가"까지 주장하려면 이 구별이 필요하다.**

## 허용목록은 호스트의 집합이 아니다

첫 줄로 가자. `github.com` 이 brew 프리셋 때문에 열렸다는 예측은 맞다. 실제 `presets/brew.yaml` 에 그 호스트가 있다.[^5] 그런데 같은 파일의 아래쪽이 더 흥미롭다.

```yaml
      - host: github.com
        port: 443
        access: full
      ...
    # System git is intentionally excluded; git-based Homebrew
    # operations require the github preset.
    binaries:
      - { path: /usr/bin/curl }
      - { path: /usr/local/bin/brew }
      - { path: /home/linuxbrew/.linuxbrew/bin/brew }
      - { path: /home/linuxbrew/.linuxbrew/bin/* }
      - { path: /home/linuxbrew/.linuxbrew/Homebrew/bin/* }
```

`/usr/bin/git` 이 **의도적으로 빠져 있다.** 그러니 같은 샌드박스, 같은 호스트, 같은 443 포트에서

- `curl https://github.com` → 허용 (표의 첫 줄이 이것이다)
- `git clone https://github.com/...` → **거부**

호출한 바이너리 하나가 판정을 뒤집는다. OpenShell 정책은 엔드포인트와 바이너리가 **같은 블록 안에서 동시에** 맞아야 허용한다.

두 번째 줄에도 같은 함정이 있다. `github` 프리셋의 바이너리 목록은 `/usr/bin/git` **하나뿐**이다.[^6] 즉 이 표의 예측이 은근히 깔고 있는 반사실 — "github 프리셋을 켰으면 통과했을 것" — 은 `curl` 로 친 테스트에 대해서는 **거짓**이다. 켜도 `curl https://api.github.com` 은 막힌다. (그 프리셋 파일의 주석은 `gh` CLI 도 예전엔 목록에 있었지만 베이스 이미지가 `gh` 를 설치하지 않아 빼버렸다고 적는다.)

세 번째 줄의 `pypi.org` 도 "허용"보다 훨씬 좁다. GET 과 HEAD 만, `/**` 에 대해서다.[^7] `POST` 는 맨 403 이 된다.

정리하면, 실제 판정 함수는 이렇다.

$$\text{allow}(c)\iff\exists\,g\in\mathcal{G}:\ (h_c,p_c)\in E_g\ \wedge\ b_c\in B_g\ \wedge\ (m_c,\text{path}_c)\in R_g$$

반면 표의 예측 칸이 쓴 모델은 이것이다.

$$\text{allow}'(c)\iff h_c\in\bigcup_{g\in\mathcal{G}} E_g$$

## 네 줄이 전부 맞은 건 두 모델이 이 네 줄에서 구별되지 않기 때문이다

$\text{allow}$ 와 $\text{allow}'$ 는 이 표의 네 입력에 대해 **같은 답을 낸다.** 세 줄은 진짜로 호스트 유무로 갈렸고, 네 번째 줄은 호스트 유무 판단이 틀렸는데 결과만 우연히 맞았다. 관측적으로 동치인 두 모델을 구별하려면 **둘이 갈리는 입력**을 넣어야 한다. 확인 사례를 몇 줄 더 쌓는 것으로는 영원히 구별되지 않는다.

갈리는 줄의 후보는 위에 이미 다 나왔다.

| 시도 | 호스트 전용 모델 | 실제 정책 | 갈리는 이유 |
| --- | --- | --- | --- |
| `git clone https://github.com/...` | 허용 | 거부 | brew 프리셋에 `/usr/bin/git` 없음 |
| `curl -X POST https://pypi.org/` | 허용 | 거부 | 규칙이 GET·HEAD 뿐 |
| openclaw 바이너리로 `GET https://integrate.api.nvidia.com/v1/models` | 거부(예측 칸 기준) | 허용 | baseline `nvidia` 블록에 명시 |

마지막 줄이 특히 결정적이다. 예측 칸의 주장("어느 프리셋에도 없다")이 맞다면 이건 **거부돼야 한다.** 허용되면 그 주장은 그 자리에서 끝난다.

## 그래서 표에 칸이 하나 모자란다

세 칸짜리 표는 판정만 대조한다. 네 번째 칸이 필요하다 — **어느 규칙이 막았는가.**

| 목적지 | 예측 (근거 규칙까지) | 관측 | 거부 층 | 일치 |
| --- | --- | --- | --- | --- |
| `github.com` (curl) | brew 블록 · curl 허용 | `200` | — | ✓ |
| `api.github.com` (curl) | 매칭 블록 없음 | `CONNECT 403` | 터널 | ✓ |
| `pypi.org` (curl GET) | pypi 블록 · GET 허용 | `200` | — | ✓ |
| `integrate.api.nvidia.com` (curl GET /) | baseline 에 호스트 있음 · **바이너리·경로 불일치** | `403` | 요청 | ✓(이유 수정) |

칸이 하나 늘면 네 번째 줄은 그냥 ✓ 가 아니라 "✓, 단 이유는 다름"이 된다. 그리고 그 차이는 운영에서 처방을 바꾼다. 호스트가 없어서 막힌 것이면 처방은 **프리셋 추가**이고, 바이너리·경로가 안 맞아 막힌 것이면 프리셋을 아무리 추가해도 안 풀린다. OpenShell 쪽에서 실제로 무엇이 막혔는지는 차단 로그와 TUI 승인 화면에서 **호스트·포트·요청 바이너리**로 보여준다 — 추측할 필요가 없는 부분이다.[^8]

## 남는 것

- ✓ 는 **판정**의 일치이지 **모델**의 일치가 아니다. 모델을 검증하려면 두 모델이 갈리는 줄을 넣어야 한다.
- 거부의 **모양**이 데이터다. `CONNECT 403` 과 맨 `403` 은 서로 다른 층에서 나오고, 전자는 프록시만 줄 수 있다.
- 허용목록의 원소는 호스트가 아니라 (호스트, 포트, 바이너리, method, path) 다. 같은 URL 이 `curl` 로는 200, `git` 으로는 거부일 수 있다.
- 그럼에도 예측을 먼저 쓴 표는 사후 설명보다 압도적으로 낫다. 고칠 것은 방법이 아니라 칸의 개수다.

### 근거와 그 한계

이 글에서 정책 내용에 관한 주장은 전부 **NVIDIA 의 1차 자료**다 — NemoClaw 리포의 정책 YAML 원문과 공식 문서이며, 접근일은 2026년 9월 20일, 브랜치는 `main` 이다. 리포의 `main` 은 움직이는 목표라 나중에 열면 다를 수 있다.

표의 **관측 칸은 내가 재현한 것이 아니다.** 사용자가 제공한 단 한 번의 실행 기록이고, 어떤 바이너리로 어떤 경로를 쳤는지는 표에 적혀 있지 않다. 그래서 네 번째 줄의 거부 원인을 "바이너리 불일치" 와 "경로 불일치" 중 하나로 특정하지 않고 둘 다 남겨 뒀다. 이 두 갈래를 가르는 건 어렵지 않다 — `GET /v1/models` 를 같은 방식으로 한 번 더 치면 된다. 경로가 문제였다면 통과하고, 바이너리가 문제였다면 여전히 막힌다.

이 정책 모델에 대한 **중립적인 제3자 검증 자료는 찾지 못했다.** 공개된 것은 벤더의 코드와 문서이며, 다행히 이 경우는 코드가 공개돼 있어 문서를 그대로 믿을 필요 없이 YAML 을 직접 펴볼 수 있다 — 위 인용은 전부 그렇게 한 것이다.

## References

[^1]: NVIDIA, *Customize the Network Policy*, NemoClaw docs (`docs/network-policy/customize-network-policy.mdx`), 2026-09-20 접근. "NemoClaw declares sandbox policy in YAML, and NVIDIA OpenShell enforces it at runtime." <https://github.com/NVIDIA/NemoClaw/blob/main/docs/network-policy/customize-network-policy.mdx>
[^2]: NVIDIA, `nemoclaw-blueprint/policies/openclaw-sandbox.yaml`, NemoClaw, branch `main`, 2026-09-20 접근. 위 인용은 파일의 `network_policies.nvidia` 블록 원문. <https://github.com/NVIDIA/NemoClaw/blob/main/nemoclaw-blueprint/policies/openclaw-sandbox.yaml>
[^3]: NVIDIA, *Network Policies* (`docs/reference/network-policies.mdx`), "Policy Tiers" 절, 2026-09-20 접근. "The baseline policy is always applied regardless of the selected tier." <https://github.com/NVIDIA/NemoClaw/blob/main/docs/reference/network-policies.mdx>
[^4]: 같은 문서, "All endpoints use TLS termination and are enforced at port 443." `protocol: rest` 엔드포인트에서 프록시가 TLS 를 종단해 요청 단위로 규칙을 검사한다는 서술. 정책 스키마는 NVIDIA, *Policies*, OpenShell 문서 <https://docs.nvidia.com/openshell/sandboxes/policies> 참조.
[^5]: NVIDIA, `nemoclaw-blueprint/policies/presets/brew.yaml`, NemoClaw, branch `main`, 2026-09-20 접근. 인용한 주석("System git is intentionally excluded…")은 파일 원문. <https://github.com/NVIDIA/NemoClaw/blob/main/nemoclaw-blueprint/policies/presets/brew.yaml>
[^6]: NVIDIA, `nemoclaw-blueprint/policies/presets/github.yaml`, 같은 브랜치·접근일. `binaries` 는 `/usr/bin/git` 단일 항목이며, 주석은 과거 `github.com`·`api.github.com` 이 베이스 정책에 암묵적으로 포함돼 있었음(issue #1583)을 기록한다. <https://github.com/NVIDIA/NemoClaw/blob/main/nemoclaw-blueprint/policies/presets/github.yaml>
[^7]: NVIDIA, `nemoclaw-blueprint/policies/presets/pypi.yaml`, 같은 브랜치·접근일. <https://github.com/NVIDIA/NemoClaw/blob/main/nemoclaw-blueprint/policies/presets/pypi.yaml>
[^8]: NVIDIA, *Network Policies*, "operator approval flow" 절, 2026-09-20 접근. 차단된 요청은 로그에 남고 OpenShell TUI 가 호스트·포트·요청 바이너리를 보여주며 승인 시 실행 중 정책에 엔드포인트가 추가된다.
