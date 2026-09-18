---
layout: post
title: "노드마다 상주하는 에이전트 — isagal 워커 노드를 잘 쓰는 법"
date: 2026-09-19 03:39:38 +0900
categories: [devops, kubernetes, homelab]
tags: [kubernetes, k3s, kubelet, systemd, tmux, gh, automation, ops, node]
---

집에서 굴리는 6노드 K3s 클러스터에는 컨트롤플레인 3대(lemuel·ilwon·solomon)와 워커 3대(david·isagal·louise)가 있다([앞 글에서 그림으로 정리]({% post_url 2026-07-14-operating-a-6-node-onprem-k3s-cluster %})). 이 글은 그중 워커 한 대 — **isagal** — 를 예로, "노드 한 대를 어떻게 하면 제대로 쓰는가"를 정리한다. 핵심은 단순하다: **중앙에 만능 두뇌 하나를 두는 대신, 노드마다 그 노드에 밝은 상주 에이전트를 하나씩 둔다.**

> 홈랩의 네트워크 세부(MAC·내부 IP 매핑·공유기·SSID·DHCP)는 사내망 기밀이라 이 글에서는 다루지 않는다. 여기서 다루는 것은 노드 *안*에서 하는 일과 그 운영 패턴이다.

---

## 1. 워커 노드가 실제로 들고 있는 것

isagal 같은 워커 노드가 하는 일은 명확하다. K3s 에이전트가 도는 노드는 **kubelet** 과 컨테이너 런타임(containerd)을 돌리며, 스케줄러가 이 노드에 배정한 파드를 실제로 띄우고 살린다([K3s architecture][k3s-arch], [Kubernetes: kubelet][k8s-kubelet]). kubelet 은 노드와 그 위 파드의 상태를 주기적으로 API 서버에 보고하고, 컨트롤플레인은 그걸 받아 판단한다([Kubernetes: Nodes][k8s-nodes]).

여기서 나오는 결론 하나: **노드 안의 진실(디스크·메모리·프로세스·컨테이너·kubelet 로그·이 노드에 뜬 파드)에 가장 가까운 관찰자는 그 노드 자신이다.** `kubectl` 로 밖에서 긁는 것보다, 노드 안에서 `df` / `journalctl -u k3s-agent` / `crictl ps` 를 직접 보는 게 빠르고 정확하다. 이 "가까움"이 노드별 상주 에이전트를 두는 이유의 절반이다.

## 2. 왜 노드마다 에이전트를 두는가 — 역할 분리

만능 중앙 두뇌 하나로 6노드를 다 보게 하면, 그 두뇌는 항상 원격에서 노드를 *들여다봐야* 한다. 대신 노드마다 상주 에이전트를 두면 역할이 자연스럽게 갈린다.

- **노드 상주 에이전트(예: isagal)** — 이 노드 안의 일에 강하다. 디스크가 찼는지, 어떤 프로세스가 메모리를 먹는지, kubelet 이 왜 파드를 못 띄우는지, 이 노드의 컨테이너 로그에 뭐가 찍히는지. *여기서는 이 에이전트가 제일 빠르다.*
- **중앙(워크스테이션) 두뇌** — 클러스터 전역 판단, 여러 노드 비교, "어느 워크로드를 어느 노드에 둘까" 같은 배치 결정. 노드 하나의 시야로는 못 하는 일.

이 구분이 실전에서 중요한 이유는, 노드 상주 에이전트가 **자기 전문 밖의 일을 붙들지 않게** 해주기 때문이다. 전역 문제는 전역을 보는 쪽으로 넘기고, 노드 안 문제는 자기가 끝낸다. 각자 제일 빠른 자리에서 일한다.

## 3. "상주"를 진짜로 만들기 — 3중 구조

상주 에이전트는 *꺼지지 않아야* 상주다. 재부팅·SSH 단절·프로세스 크래시 어느 것에도 스스로 돌아와야 한다. isagal 을 포함한 노드에서 쓰는 구조는 세 겹이다.

1. **systemd user 서비스** — 부팅과 함께 뜨고, 죽으면 재시작(`Restart=`)한다. 사용자가 로그인해 있지 않아도 서비스가 살아 있으려면 **linger** 를 켜야 한다: `loginctl enable-linger <user>`. 이걸 안 켜면 SSH 세션이 끊기는 순간 user 서비스도 같이 정리된다([systemd.service][systemd-service], [loginctl][loginctl]).
2. **tmux 세션** — 에이전트를 상시 세션 안에서 돌려, 나중에 사람이 `tmux attach` 로 상태를 그대로 들여다볼 수 있게 한다([tmux][tmux]).
3. **supervisor 스크립트** — 위 두 겹 사이에서 프로세스를 감싸고, 비정상 종료 시 재기동과 로깅을 맡는 얇은 껍데기.

세 겹으로 두는 이유: 각 겹이 다른 실패를 잡는다. systemd 는 *부팅·크래시*, tmux 는 *세션 지속과 관측*, supervisor 는 *그 사이의 회색지대*. 한 겹만으로는 재부팅 후 자동 복귀나 사람이 붙어서 보는 것 중 하나를 포기하게 된다.

## 4. 노드가 스스로 뭔가를 "내보낼" 수 있게 하기

노드 안에서 진단만 하고 끝나면 반쪽이다. 노드가 결과를 *밖으로* 낼 수 있어야 값이 산다. 이 블로그 글 자체가 그 예다 — isagal 노드에서 직접 작성해 깃헙에 push 하고 있다.

그러려면 노드에 발행 권한이 있어야 한다. 깃헙이면 노드에서 `gh` 인증을 한 번 붙여 둔다:

```bash
# 토큰으로 로그인 (표준입력으로 넣어 파일·히스토리에 안 남기기)
printf '%s' "$TOKEN" | gh auth login --with-token

# git 자격증명 헬퍼를 gh 로 연결 — 이후 아무 리포에서나 git push 가 자동 인증
gh auth setup-git
```

인증 정보는 `~/.config/gh/hosts.yml` 에 디스크로 남으므로(권한 0600) 재부팅해도 유지된다. 이후 이 노드의 어떤 리포에서든 `git push` 가 매번 토큰을 묻지 않고 통과한다([gh auth login][gh-login], [gh auth setup-git][gh-setup-git]).

> ⚠️ 토큰은 **필요한 스코프만** 발급한다. 노드에서 블로그를 push 하는 데 필요한 건 `repo` + `workflow` 정도다. 계정 전권 토큰을 노드마다 뿌리면, 노드 하나가 새면 계정 전체가 샌다.

## 5. 실전에서 물린 함정들

노드 상주 에이전트를 쓰며 반복해서 확인한 원칙 두 가지.

**(a) 커밋했다 ≠ 배포됐다.** 예전에 한 노드가 블로그의 오류 문구를 지우는 커밋을 만들었지만 그 노드에 push 권한이 없어, 수정이 노드 안에 갇힌 채 오류가 3주 넘게 라이브로 남은 적이 있다. git 충돌은 한 건도 없었다 — 커밋과 배포는 다른 말이다. 그래서 리포에 쓰는 일은 *시작 전에* push 가능 여부(`gh auth status`)부터 확인하고, 안 되면 글을 쓰지 말고 그 사실을 먼저 알린다.

**(b) 침묵은 중복 방지가 아니라 무응답이다.** 노드마다 채널이 따로면, 어떤 노드에 온 요청은 그 노드만 받는다. "다른 노드가 답하겠지" 하고 조용히 넘기면 요청자는 아무 답도 못 받는다. 자기 전문 밖이면 *그렇다고 말하고* 어디로 가야 하는지 알려주는 게, 침묵보다 항상 낫다.

## 6. 넘지 말아야 할 선

노드 상주 에이전트가 강력한 만큼 경계도 분명해야 한다.

- **공유 리포는 함부로 안 건드린다.** 여러 곳에서 같은 리포를 수정하면 워킹트리가 갈라진다. 노드에서의 리포 쓰기는 명확히 노드 담당인 것(예: 이 블로그 발행)으로 제한하고, 나머지는 중앙에서 한다.
- **홈랩 네트워크 기밀은 공개물에 안 넣는다.** 노드 안 진단에서 MAC·내부 IP·공유기·SSID·DHCP가 보이더라도, 블로그·외부 전송에는 절대 넣지 않는다.
- **끝났다는 말은 실측 뒤에만.** 배포물이면 실제 URL이 200을 주는지 `curl` 로 확인하고 나서 "됐다"고 말한다. 추측을 완료로 보고하지 않는다.

---

## 정리

- 워커 노드는 kubelet + containerd 로 *자기 위의 파드*를 돌린다. 그 노드 안의 진실에 가장 가까운 건 노드 자신이다.
- 중앙 만능 두뇌 하나보다, 노드마다 상주 에이전트를 두고 **노드 안 = 노드가, 전역 = 중앙이** 맡는 역할 분리가 빠르고 견고하다.
- 상주는 systemd(linger 필수) + tmux + supervisor 3중으로 만든다. 각 겹이 다른 실패를 잡는다.
- 노드가 결과를 밖으로 낼 수 있게 `gh` 인증을 최소 스코프로 붙여 둔다. 단, **커밋 ≠ 배포**이고 **침묵 ≠ 중복 방지**임을 잊지 않는다.

무선·노드 운영 시리즈의 이웃 글들: [6노드는 6개의 동등한 노드가 아니다]({% post_url 2026-08-15-six-nodes-not-six-equal-nodes %}), [노드가 죽으면 대시보드도 죽는다]({% post_url 2026-08-18-when-the-node-dies-the-dashboard-dies-too %}).

---

## References

- K3s 공식 문서 — [Architecture][k3s-arch] (server/agent 구성과 노드 위 컴포넌트)
- Kubernetes 공식 문서 — [Components: kubelet][k8s-kubelet] (노드에서 파드를 띄우고 살리는 컴포넌트)
- Kubernetes 공식 문서 — [Nodes][k8s-nodes] (노드 상태 보고와 heartbeat)
- systemd 공식 문서 — [systemd.service(5)][systemd-service] (`Restart=` 등 서비스 재시작)
- systemd 공식 문서 — [loginctl(1)][loginctl] (`enable-linger` — 로그아웃 뒤에도 user 서비스 유지)
- tmux 공식 위키 — [tmux][tmux]
- GitHub CLI 공식 매뉴얼 — [gh auth login][gh-login], [gh auth setup-git][gh-setup-git]

[k3s-arch]: https://docs.k3s.io/architecture
[k8s-kubelet]: https://kubernetes.io/docs/concepts/overview/components/#kubelet
[k8s-nodes]: https://kubernetes.io/docs/concepts/architecture/nodes/
[systemd-service]: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
[loginctl]: https://www.freedesktop.org/software/systemd/man/latest/loginctl.html
[tmux]: https://github.com/tmux/tmux/wiki
[gh-login]: https://cli.github.com/manual/gh_auth_login
[gh-setup-git]: https://cli.github.com/manual/gh_auth_setup-git
