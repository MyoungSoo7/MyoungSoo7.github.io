---
layout: post
title: "쿠버네티스·도커·일반 서버 — 사다리가 아니라, 서로 다른 계약서다"
date: 2026-09-10 22:55:22 +0900
categories: [engineering, kubernetes]
tags: [kubernetes, docker, container, systemd, linux, devops, 인프라선택]
---

"일반 서버 → 도커 → 쿠버네티스" 순으로 그린 그림을 자주 봅니다. 아래로 갈수록 낡았고 위로 갈수록 발전했다는 그림입니다. 이 순서가 틀렸다고는 못 하겠습니다. 실제로 뒤의 것이 앞의 것의 한계를 보고 나왔으니까요.

그런데 이 그림은 중요한 걸 가립니다. **세 방식은 성능의 계단이 아니라 서로 다른 계약서**입니다. 각각이 "이건 내가 할 테니 저건 네가 해라" 하고 제안하는 범위가 다릅니다. 위로 올라갈수록 플랫폼이 더 많이 가져가는데, 그 대가로 내가 새로 배워야 할 것과 새로 감시해야 할 것도 같이 늘어납니다. 그래서 이건 "더 나은 걸 고르는" 문제가 아니라 **"내가 어떤 항목에 서명할 수 있는가"** 하는 문제입니다.

이 글은 세 방식을 그 관점에서 씁니다. 무엇을 쓰는가가 아니라, 무엇을 **떠안게 되는가** 로요.

---

## 0. 먼저 — 컨테이너는 도커의 기능이 아닙니다

이 논의의 출발점부터 자주 틀립니다. 컨테이너는 도커가 만든 기술이 아니라 **리눅스 커널 기능**입니다.

리눅스 `namespaces(7)` 맨페이지는 네임스페이스를 이렇게 정의합니다[^ns]:

> A namespace wraps a global system resource in an abstraction that makes it appear to the processes within the namespace that they have their own isolated instance of the global resource. (...) **One use of namespaces is to implement containers.**

즉 컨테이너는 네임스페이스의 *사용처 중 하나* 입니다. 커널이 격리하는 항목은 PID, 네트워크, 마운트, IPC, UTS(호스트네임), 사용자, 시간, cgroup — 이렇게 나뉘어 있습니다[^ns].

여기에 자원 **한도**를 붙이는 게 cgroups 입니다. `cgroups(7)` 은 "프로세스를 계층적 그룹으로 묶어 각종 자원 사용량을 제한하고 감시할 수 있게 하는 리눅스 커널 기능"이라고 정의합니다[^cg].

그래서 정확히 말하면 이렇습니다.

- **커널**: 격리(namespaces) + 한도(cgroups) 를 제공
- **도커**: 그걸 이미지·레지스트리·CLI·데몬으로 **쓸 만하게** 포장
- **쿠버네티스**: 그 컨테이너들을 **여러 대에 걸쳐** 배치·유지

이 구분이 왜 중요하냐면, "도커를 안 쓰면 컨테이너를 못 쓴다"거나 "쿠버네티스를 쓰면 도커를 써야 한다"는 오해가 여기서 갈리기 때문입니다. 둘 다 아닙니다.

---

## 1. 일반 서버 — 프로세스를 직접 기른다

### 사용 방법

패키지 매니저로 런타임을 깔고, 애플리케이션을 빌드해서 서버에 올리고, systemd 유닛 파일을 하나 써서 `systemctl enable --now` 합니다. 배포는 새 바이너리(혹은 jar)를 올려놓고 `systemctl restart` 입니다. 리버스 프록시(nginx 등)로 앞을 막고, 로그는 journald 나 파일로 떨어뜨립니다.

### 장점

**첫째, 층이 얇습니다.** 문제가 나면 볼 곳이 적습니다. 프로세스가 죽었는지, 포트가 열렸는지, 디스크가 찼는지 — 대부분 세 개 안에서 끝납니다. 컨테이너 런타임도, 오버레이 네트워크도, 스케줄러도 용의자 목록에 없습니다.

**둘째, 자가 치유가 이미 있습니다.** 쿠버네티스의 셀링 포인트로 자주 나오는 "죽으면 다시 띄운다"는 systemd 에 이미 있습니다. `systemd.service(5)` 의 `Restart=` 는 이렇게 설명됩니다[^sd]:

> Configures whether the service shall be restarted when the service process exits, is killed, or a timeout is reached.

`Restart=on-failure` 한 줄이면 프로세스 단위 자가 치유는 끝납니다. 쿠버네티스가 더 하는 건 **프로세스가 아니라 노드가 죽었을 때** 다른 기계에서 다시 띄우는 부분입니다. 이 차이를 뭉개고 "자가 치유"를 통째로 쿠버네티스의 것으로 소개하는 글이 많습니다.

**셋째, 자원 한도도 이미 있습니다.** systemd 는 `systemd.resource-control(5)` 로 유닛에 cgroup 한도를 걸 수 있습니다[^sd]. 컨테이너가 아니어도 CPU·메모리 제한은 됩니다.

### 단점

**첫째, 환경이 서버에 눌어붙습니다.** "내 노트북에선 되는데"의 고전적 원인입니다. 런타임 버전, 시스템 라이브러리, 환경변수, 커널 파라미터가 서버마다 조금씩 다르게 쌓이고, 그 차이는 문서에 안 남습니다. 서버 대수가 늘면 이 차이는 지수적으로 관리하기 어려워집니다.

**둘째, 서버가 특별해집니다.** 3년 굴린 서버는 아무도 갈아엎지 못합니다. 무엇이 설치돼 있는지 아무도 전부 알지 못하기 때문입니다. 재현 가능한 절차가 없으면 그 서버는 자산이 아니라 부채입니다.

**셋째, 여러 대로 넘어가는 순간 전부 수작업입니다.** 어느 서버에 무엇을 올릴지, 배포 순서를 어떻게 할지, 한 대가 죽으면 트래픽을 어디로 뺄지 — 전부 사람이 정하고 사람이 실행합니다. 이게 다음 두 방식이 풀려고 한 문제입니다.

---

## 2. 도커 — 재현 가능한 상자, 다만 한 대 안에서

### 사용 방법

`Dockerfile` 로 이미지를 굽고, 레지스트리에 올리고, 서버에서 `docker run` 하거나 `compose.yaml` 하나로 여러 컨테이너를 같이 띄웁니다. 배포는 이미지 태그를 바꾸고 `docker compose up -d` 입니다.

도커 공식 문서는 도커를 이렇게 설명합니다[^dk]:

> Docker provides the ability to package and run an application in a **loosely isolated** environment called a container.

"loosely isolated" 라는 표현을 공식 문서가 직접 쓰고 있다는 점은 기억해 둘 만합니다. 컨테이너는 VM 이 아닙니다. 커널을 호스트와 **공유**합니다.

### 장점

**첫째, 앞 절의 첫 번째 단점이 사라집니다.** 런타임·라이브러리·설정이 이미지 안으로 들어가므로, 서버에 무엇이 깔려 있든 같은 이미지는 같게 뜹니다. "재현 가능"이 도커가 실제로 판 물건입니다.

**둘째, 배포 단위가 파일 하나가 아니라 이미지가 됩니다.** 롤백이 "이전 태그로 되돌리기"가 됩니다. 이전 jar 를 어디에 백업해 뒀는지 찾을 필요가 없습니다.

**셋째, 밀도가 올라갑니다.** 도커 문서는 하이퍼바이저 기반 VM 의 "cost-effective alternative" 로 스스로를 위치시킵니다[^dk]. 커널을 공유하니 VM 보다 가볍습니다. 한 대에 여러 서비스를 촘촘히 올릴 때 유리합니다.

### 단점 — 그리고 정확히 어디서 끊기는가

여기가 이 글에서 제일 중요한 지점입니다. 도커만으로 운영하는 구성이 어디까지 유효한지, **도커 공식 문서가 직접 선을 긋고 있습니다.** Compose 문서의 "Single host deployments" 항목입니다[^cp]:

> Compose supports production deployments on **single hosts**.

단일 호스트입니다. 즉 도커/Compose 조합은 **한 대 안에서의 오케스트레이션**입니다. 그래서 이런 것들이 계약서에 없습니다.

- **그 한 대가 죽으면 끝납니다.** 컨테이너가 죽으면 `restart: always` 가 살리지만, 호스트가 죽으면 살릴 주체가 없습니다. 다른 기계로 옮겨 줄 사람이 없습니다.
- **여러 대에 걸친 배치 결정이 없습니다.** 서버가 두 대가 되는 순간 "무엇을 어디에" 는 다시 사람 몫입니다.
- **서비스 디스커버리가 호스트 밖으로 안 나갑니다.** Compose 네트워크 안의 이름 해석은 그 호스트 안에서만 유효합니다.
- **무중단 배포가 기본이 아닙니다.** `up -d` 로 컨테이너를 갈아 끼우는 사이의 공백은 직접 메워야 합니다.

정리하면 도커는 **"무엇을 실행할 것인가"를 재현 가능하게** 만들었지만, **"어디서 실행할 것인가"** 는 여전히 사람에게 남겨 뒀습니다. 이 빈칸이 다음 절의 존재 이유입니다.

---

## 3. 쿠버네티스 — 여러 대를 한 대처럼

### 사용 방법

매니페스트(YAML)로 *원하는 상태* 를 적어서 API 서버에 제출합니다. "이 이미지를 3개 띄우고, 이 포트를 서비스로 열고, CPU 는 이만큼 쓴다" 를 적으면, 컨트롤러들이 현재 상태를 그 상태로 계속 끌고 갑니다. 배포는 이미지 태그를 바꿔 커밋하는 것으로 끝나고(GitOps 를 얹었다면), 나머지는 클러스터가 합니다.

### 장점

쿠버네티스 공식 문서가 스스로 나열하는 목록이 정확합니다 — 서비스 디스커버리와 로드밸런싱, 스토리지 오케스트레이션, 자동 롤아웃/롤백, 자동 빈 패킹, 자가 치유, 시크릿·설정 관리, 배치 실행, 수평 확장[^k8s].

이 중 앞 절과 비교해서 **진짜로 새로 생기는 것** 은 셋입니다.

1. **노드 장애를 넘어서는 복구.** 기계 한 대가 죽으면 그 위의 워크로드가 다른 기계에서 다시 뜹니다. 도커에 없던 항목입니다.
2. **배치 결정의 자동화(빈 패킹).** 컨테이너가 요구하는 CPU/메모리를 적어 두면 어느 노드에 넣을지 스케줄러가 정합니다.
3. **명령형에서 선언형으로.** "이걸 해라"가 아니라 "이 상태여야 한다"를 적습니다. 그래서 상태가 어긋나면 사람이 고치는 게 아니라 컨트롤러가 되돌립니다.

세 번째가 왜 그렇게 큰 전환이었는지는 계보를 보면 분명합니다. 구글의 Borg 논문은 자기 시스템을 "admission control, efficient task-packing, over-commitment, machine sharing" 을 조합해 **높은 이용률(high utilization)** 을 달성하는 클러스터 매니저로 설명하고, 사용자에게는 "declarative job specification language" 를 제공한다고 씁니다[^borg]. 쿠버네티스가 물려받은 게 이겁니다 — **선언형 명세 + 이용률**.

### 단점 — 공식 문서가 직접 부인하는 것들

쿠버네티스 문서에는 "What Kubernetes is not" 이라는 절이 따로 있습니다. 이 절이 사실상 도입 검토서의 리스크 목록입니다[^k8s]. 쿠버네티스는 —

- **소스를 배포하지도, 빌드하지도 않습니다.** CI/CD 는 따로 만들어야 합니다.
- **미들웨어·데이터 처리 프레임워크·데이터베이스·캐시·클러스터 스토리지를 내장 서비스로 제공하지 않습니다.** DB 를 클러스터 안에서 굴릴지 밖에 둘지는 여전히 내 결정이고, 굴린다면 그 운영은 내 몫입니다.
- **로깅·모니터링·알림 솔루션을 정해 주지 않습니다.** "proof of concept 수준의 통합과 지표를 수집·내보내는 메커니즘"까지만 줍니다.
- **포괄적인 머신 설정·유지보수·관리·자가 치유 시스템을 제공하거나 강제하지 않습니다.** — 이 문장이 특히 중요합니다. **노드 자체는 여전히 내가 관리합니다.** 커널 업데이트, 디스크, 네트워크 인터페이스, 전원. 쿠버네티스는 컨테이너 레벨에서 동작하지 하드웨어 레벨에서 동작하지 않는다고 문서가 명시합니다.

여기에 **구조적 비용**이 하나 더 붙습니다. 클러스터를 굴린다는 건 컨트롤 플레인을 굴린다는 뜻입니다. 공식 문서 기준 구성 요소는 kube-apiserver, etcd, kube-scheduler, kube-controller-manager (그리고 선택적으로 cloud-controller-manager), 각 노드의 kubelet·kube-proxy·컨테이너 런타임입니다[^comp]. 애플리케이션이 한 줄도 안 돌아도 이것들이 계속 떠 있어야 합니다.

특히 **etcd 가 쿼럼(과반)을 요구한다**[^etcd]는 사실이 실무에서 제일 자주 사람을 놀라게 합니다. 컨트롤 플레인 노드를 3대로 구성했다면 2대가 살아 있어야 클러스터가 동작합니다. 2대가 내려가면 애플리케이션 컨테이너가 멀쩡히 돌고 있어도 `kubectl` 이 붙지 않습니다. 일반 서버에는 이런 실패 모드가 아예 없습니다. **가용성을 올리려고 도입한 것이 새로운 종류의 전면 장애를 하나 만들어 낸 셈**입니다.

### 겪어 보고 알게 된 것 하나

집에서 굴리는 6노드 k3s 클러스터에서 오늘 노드들을 재부팅했습니다. 노드가 돌아온 뒤에도 파드 26개가 이미지를 못 받아 와서 `ImagePullBackOff` 로 멈춰 있었는데, 원인은 쿠버네티스가 아니라 **그 노드의 DNS 해석 실패** 하나였습니다. 이미지 레지스트리 도메인이 안 풀리니 컨테이너가 안 떴고, 하필 거기 ArgoCD 가 얹혀 있어서 GitOps 동기화까지 같이 멈췄습니다.

교훈은 이겁니다. **쿠버네티스는 "노드가 정상 동작한다"를 전제로 그 위를 자동화합니다.** 그 전제가 깨지면 자동화는 아무것도 구해 주지 않고, 오히려 원인을 한 겹 더 덮습니다. 파드 26개가 실패한 화면에서 "노드의 resolv.conf" 까지 내려가는 데 걸리는 시간 — 그게 추가된 층의 비용입니다.

---

## 4. 그래서 진짜 차이는 "무엇을 내가 소유하는가"

| 항목 | 일반 서버 | 도커 (단일 호스트) | 쿠버네티스 |
|---|---|---|---|
| 실행 환경 재현 | 내 몫 (문서·스크립트) | **플랫폼** (이미지) | **플랫폼** (이미지) |
| 프로세스 재시작 | **플랫폼** (systemd `Restart=`) | **플랫폼** (`restart:`) | **플랫폼** |
| 노드 장애 시 재배치 | 내 몫 (수작업) | 내 몫 (수작업) | **플랫폼** |
| 배치 결정 | 내 몫 | 내 몫 | **플랫폼** (스케줄러) |
| 무중단 배포 | 내 몫 | 내 몫 | 플랫폼 (설정하면) |
| CI/CD | 내 몫 | 내 몫 | **내 몫** (문서가 명시) |
| 로깅·모니터링 | 내 몫 | 내 몫 | **내 몫** (문서가 명시) |
| OS·커널·디스크·네트워크 | 내 몫 | 내 몫 | **내 몫** (문서가 명시) |
| 컨트롤 플레인 운영 | 없음 | 없음 | **내 몫** (새로 생김) |

오른쪽으로 갈수록 "플랫폼" 칸이 늘어나는 건 맞습니다. 그런데 **맨 아래 줄은 오른쪽 끝에서만 새로 생깁니다.** 그리고 "내 몫" 으로 남는 줄이 생각보다 많습니다. 위 표에서 굵게 칠한 "내 몫" 중 위 세 줄(CI/CD·로깅 및 모니터링·OS 및 머신 관리)은 전부 쿠버네티스 공식 문서가 직접 자기 책임이 아니라고 밝힌 항목입니다[^k8s]. 맨 아래 줄은 문서가 말하지 않은, 도입하는 순간 새로 생기는 몫입니다.

---

## 5. 그럼 무엇을 고르나 — 다섯 개의 질문

기능 목록을 비교하는 대신, 답이 갈리는 질문을 놓겠습니다.

**Q1. 서버가 몇 대인가?**
한 대라면 쿠버네티스가 푸는 문제의 절반(노드 간 배치·노드 장애 복구)이 애초에 없습니다. 한 대에 컨트롤 플레인까지 얹으면 순수 손해입니다.

**Q2. 한 대가 죽었을 때 몇 분 안에 복구돼야 하나?**
"사람이 알아채고 손으로 옮겨도 되는" 수준이면 도커로 충분합니다. "자동으로 다른 기계에서 떠야 한다"가 요구사항이면 그때부터 쿠버네티스가 값을 합니다. 이 질문 하나가 사실상 도커와 쿠버네티스의 경계선입니다.

**Q3. 컨트롤 플레인을 새벽에 고칠 사람이 있나?**
etcd 쿼럼, 인증서 만료, CNI, 스토리지 클래스 — 이건 애플리케이션 지식이 아니라 별개의 전문 영역입니다. 이걸 감당할 사람이 없다면 매니지드 서비스를 쓰거나, 도입 자체를 미루는 게 맞습니다.

**Q4. 배포 빈도가 얼마나 되나?**
한 달에 한 번 배포하는 시스템에서 무중단 롤아웃의 가치는 크지 않습니다. 하루에 여러 번 배포한다면 얘기가 완전히 달라집니다.

**Q5. 지금 겪는 고통이 정확히 무엇인가?**
"환경이 서버마다 다르다" → 도커가 답입니다.
"서버가 죽으면 새벽에 일어나야 한다" → 쿠버네티스가 답입니다.
"배포가 무섭다" → 셋 다 답이 아닙니다. 그건 테스트와 롤백 절차의 문제입니다.

마지막 줄이 제일 자주 틀리는 지점입니다. **도구를 바꿔서 풀리는 문제와 안 풀리는 문제를 구분하지 않으면, 도입 후에 고통은 그대로인데 관리할 층만 하나 늘어납니다.**

---

## 6. 이 글이 답하지 못하는 것

정직하게 남겨 둡니다.

- **비용 비교를 못 했습니다.** 세 방식의 총소유비용은 인건비·클라우드 요금·장애 시간 가치에 좌우되는데, 이건 조직마다 다르고 공개된 중립 비교 데이터가 없습니다. "쿠버네티스가 싸다/비싸다"는 주장은 그 조직의 수치 없이는 검증이 안 됩니다.
- **성능 비교를 안 했습니다.** 컨테이너 오버헤드나 CNI 별 네트워크 성능은 벤치마크가 필요한 영역이고, 벤더 자체 벤치마크 외에 재현 가능한 중립 head-to-head 자료를 이 글을 쓰며 찾지 못했습니다. 그래서 아예 다루지 않았습니다.
- **중간 선택지들을 뺐습니다.** Nomad, Docker Swarm, 매니지드 컨테이너 서비스, 그리고 "VM + Ansible" 조합은 실제로 많이 쓰이는 답인데 세 축을 선명하게 두려고 생략했습니다.
- **"쿠버네티스를 언제 걷어내야 하는가"** 는 다루지 못했습니다. 도입 사례는 많은데 철수 사례는 공개 자료가 드뭅니다. 이건 저도 답을 모릅니다.

---

## References

[^ns]: The Linux man-pages project, ["namespaces(7) — overview of Linux namespaces"](https://man7.org/linux/man-pages/man7/namespaces.7.html). 네임스페이스 정의, 격리 대상 목록(Cgroup/IPC/Network/Mount/PID/Time/User/UTS), "One use of namespaces is to implement containers."

[^cg]: The Linux man-pages project, ["cgroups(7) — Linux control groups"](https://man7.org/linux/man-pages/man7/cgroups.7.html). cgroup 정의 및 자원 제한·감시 메커니즘, v1/v2 구분.

[^sd]: The systemd project, ["systemd.service(5)"](https://man7.org/linux/man-pages/man5/systemd.service.5.html). `Restart=` 지시자 정의(`no`, `on-success`, `on-failure`, `on-abnormal`, `on-watchdog`, `on-abort`, `always`), 자원 제어는 `systemd.resource-control(5)` 참조.

[^dk]: Docker Docs, ["What is Docker?"](https://docs.docker.com/get-started/docker-overview/). 벤더 1차 문서. "loosely isolated environment called a container", 클라이언트–데몬 아키텍처, VM 대비 위치 설정. 성능·비용 우위 서술은 벤더 자체 주장이므로 이 글에서는 수치로 인용하지 않았습니다.

[^cp]: Docker Docs, ["Why use Compose?"](https://docs.docker.com/compose/intro/features-uses/). 벤더 1차 문서. "Compose supports production deployments on single hosts."

[^k8s]: Kubernetes Documentation, ["Overview"](https://kubernetes.io/docs/concepts/overview/). 기능 목록 및 "What Kubernetes is not" 절 — CI/CD·애플리케이션 서비스·로깅/모니터링·머신 관리에 대한 비책임 명시.

[^comp]: Kubernetes Documentation, ["Kubernetes Components"](https://kubernetes.io/docs/concepts/overview/components/). 컨트롤 플레인(kube-apiserver, etcd, kube-scheduler, kube-controller-manager, cloud-controller-manager) 및 노드 구성 요소(kubelet, kube-proxy, container runtime).

[^borg]: Abhishek Verma, Luis Pedrosa, Madhukar Korupolu, David Oppenheimer, Eric Tune, John Wilkes, ["Large-scale cluster management at Google with Borg"](https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/), *Proceedings of the European Conference on Computer Systems (EuroSys)*, ACM, Bordeaux, France, 2015. 동료심사 논문. admission control·task-packing·over-commitment·machine sharing 조합을 통한 이용률 확보, declarative job specification language.

[^etcd]: etcd Documentation, ["FAQ"](https://etcd.io/docs/v3.6/faq/). 프로젝트 1차 문서. "an etcd cluster needs a majority of nodes, a quorum, to agree on updates to the cluster state" — 3 멤버 구성의 과반은 2이며, 따라서 허용 가능한 동시 장애는 1대입니다.
