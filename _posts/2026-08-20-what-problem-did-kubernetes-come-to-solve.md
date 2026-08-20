---
layout: post
title: "쿠버네티스는 어떤 문제를 풀러 왔나 — 컨테이너가 남긴 빈칸과, 도입 전/후"
date: 2026-08-20 14:16:00 +0900
categories: [engineering, kubernetes]
tags: [kubernetes, borg, docker, container, declarative, scheduling, history]
---

쿠버네티스 설명은 대개 "무엇을 하는가"에서 시작합니다. 파드가 있고, 디플로이먼트가 있고, 서비스가 있고 — 하지만 그건 **답**입니다. 답만 먼저 보면 문제를 못 봅니다.

이 글은 순서를 뒤집습니다. 쿠버네티스가 나오기 직전에 무엇이 안 풀린 채 남아 있었는지부터 짚고, 그 빈칸에 무엇이 들어왔는지, 그래서 도입 전과 후가 실제로 무엇이 다른지를 봅니다.

결론부터 쓰면 이렇습니다. **컨테이너는 "한 대 안의 문제"를 풀었고, 쿠버네티스는 "여러 대 사이의 문제"를 풀러 왔습니다.** 그리고 그 해법의 핵심은 기능 목록이 아니라 **누가 결정하는가**를 바꾼 것입니다.

---

## 1. 컨테이너 이전 — 자원의 경계가 없던 시대

쿠버네티스 공식 문서는 배포의 역사를 세 시대로 나눕니다. 첫 시대에 대한 서술이 정확합니다.

> Early on, organizations ran applications on physical servers. There was no way to define resource boundaries for applications in a physical server, and this caused resource allocation issues.[^k8s-overview]

핵심은 **"경계를 정의할 방법이 없었다"** 입니다. 한 서버에서 앱 하나가 자원을 다 먹으면 나머지가 굶습니다. 그래서 당시의 해법은 격리를 **하드웨어로 사는 것**이었습니다 — 앱마다 서버 한 대. 문서는 그 대가도 같이 적습니다. "this did not scale as resources were underutilized, and it was expensive."

가상화가 다음 답이었습니다. VM은 경계를 만들어 줬고, 한 물리 서버에 여러 개를 얹을 수 있게 했습니다. 다만 경계 하나를 만들려고 **OS를 통째로 하나 더** 복제하는 값을 치릅니다.

컨테이너는 그 값을 깎았습니다.

> Containers are similar to VMs, but they have relaxed isolation properties to share the Operating System (OS) among the applications. Therefore, containers are considered lightweight.[^k8s-overview]

| 시대 | 격리를 무엇으로 샀나 | 대가 |
| --- | --- | --- |
| 물리 서버 | 서버를 따로 삼 | 자원 놀림, 비용, 확장 불가 |
| 가상 머신 | OS를 통째로 복제 | 부팅 시간, 메모리·디스크 오버헤드 |
| 컨테이너 | 커널을 공유하고 네임스페이스로 나눔 | 격리 강도가 VM보다 약함 |

## 2. 컨테이너가 푼 문제와, 남긴 문제

Docker는 **2013년 3월 20일** 오픈소스로 공개됐습니다. 처음엔 LXC를 실행 환경으로 썼고, 1년 뒤 0.9 버전에서 Go로 만든 자체 컴포넌트 libcontainer로 교체합니다.[^wiki-docker]

Docker가 실제로 지운 통증은 하나로 요약됩니다 — **"내 노트북에서는 되는데"**. 런타임, 라이브러리, 경로, 버전을 이미지 안에 봉해서 어디서 실행해도 같게 만들었습니다.

그런데 이건 **한 대 안에서 끝나는 문제**입니다. 컨테이너를 실제로 굴리기 시작하면 다음 질문들이 남습니다.

| 남은 질문 | 컨테이너가 답하나 |
| --- | --- |
| 이 컨테이너를 **어느 기계**에 놓을 것인가 | 안 함 |
| 죽으면 **누가** 다시 띄우나 | 안 함 |
| 주소가 매번 바뀌는데 다른 서비스가 **어떻게 찾나** | 안 함 |
| 10개를 100개로 늘리려면 **누가 세나** | 안 함 |
| 버전을 바꾸는 동안 **트래픽은 어디로** | 안 함 |
| 기계 한 대가 통째로 죽으면 **그 위의 것들은** | 안 함 |

여섯 줄 전부 **여러 대 사이의 문제**입니다. 컨테이너는 이 칸을 비워 둔 채로 업계에 퍼졌고, 2013~2014년의 현장은 이 빈칸을 셸 스크립트와 사람의 당직으로 메우고 있었습니다.

**이 빈칸이 쿠버네티스가 태어난 자리입니다.**

## 3. 구글은 이 문제를 10년 먼저 겪었다

빈칸의 답은 새로 발명된 게 아니라 이미 사내에서 돌고 있었습니다. Borg입니다. 2015년 EuroSys에 공개된 논문 「Large-scale cluster management at Google with Borg」가 그 시스템을 서술합니다.[^borg]

규모부터가 다릅니다.

> runs hundreds of thousands of jobs, from many thousands of different applications, across a number of clusters each with up to tens of thousands of machines.[^borg]

수만 대 규모에서는 **사람이 배치를 결정할 수 없습니다.** 어느 기계에 무엇을 올릴지 사람이 고르는 방식은 그 규모에서 그냥 작동을 멈춥니다. 구글은 그래서 남들보다 10년 먼저 그 방식을 포기해야 했습니다.

Borg가 쓴 방법은 논문 초록에 나열돼 있습니다 — admission control, efficient task-packing, over-commitment, machine sharing with process-level performance isolation. 그리고 사용자 쪽 도구로 이게 붙습니다.

> a declarative job specification language[^borg]

**선언형 명세.** 이게 쿠버네티스가 물려받은 진짜 유전자입니다. 나머지는 구현 세부지만, 이건 사고방식입니다.

## 4. 등장 — 날짜로 정리

| 시점 | 사건 |
| --- | --- |
| 2013-03-20 | Docker 오픈소스 공개 (LXC 기반)[^wiki-docker] |
| 2014-06-06 | 구글, 쿠버네티스 발표 — Joe Beda, Brendan Burns, Craig McLuckie[^wiki-k8s] |
| 2014 | Docker 0.9, LXC → libcontainer 교체[^wiki-docker] |
| 2015-07-21 | 쿠버네티스 v1.0[^wiki-k8s] |
| 2015 | CNCF 설립, 쿠버네티스를 seed technology로 제공[^wiki-k8s] |

Docker 공개와 쿠버네티스 발표 사이가 **1년 3개월**입니다. 빈칸이 드러나고 답이 나오기까지 걸린 시간이 그 정도였습니다.

한 가지 더 짚을 게 있습니다. Borg는 C++로 쓰였고, 쿠버네티스는 Go로 쓰였습니다.[^wiki-k8s] **이식이 아니라 재작성**입니다. 구글 내부 인프라에 묶인 전제를 떼고, 밖에서도 서는 형태로 다시 지었다는 뜻입니다.

## 5. 도입 전 / 후 — 실제로 바뀌는 것

공식 문서가 쿠버네티스가 제공한다고 말하는 목록은 서비스 디스커버리와 로드 밸런싱, 스토리지 오케스트레이션, 자동 롤아웃/롤백, 자동 빈 패킹, 자가 치유, 시크릿·설정 관리입니다.[^k8s-overview] 이걸 전/후로 다시 배열하면 이렇게 됩니다.

| 항목 | 도입 전 | 도입 후 | 뒷면 |
| --- | --- | --- | --- |
| **관리 단위** | 개별 서버 — "3번 장비" | 파드 — 어느 기계인지 대체로 안 봄 | 추상화는 아래로 샌다 |
| **배치 결정** | 사람이 고름 | 스케줄러가 자원 요청 보고 꽂음 | 요청값을 틀리게 적으면 전부 틀어짐 |
| **설정 방식** | 명령형 — 접속해서 명령 | 선언형 — 원하는 상태를 적음 | 손으로 내린 명령이 오답이 됨 |
| **장애 대응** | 사람이 깨서 확인하고 재시작 | 컨트롤러가 재시작·교체 | 원인이 아니라 증상만 사라짐 |
| **확장** | 서버 증설 후 수동 투입 | 레플리카 수를 바꾸거나 HPA | 상태 있는 것은 그대로 어려움 |
| **배포** | 중단 후 교체, 롤백은 역순 수작업 | 롤링 업데이트와 롤백이 기본 동작 | 롤백돼도 데이터 마이그레이션은 안 돌아옴 |
| **디스커버리** | IP·호스트명을 설정에 박음 | DNS 이름으로 서비스 참조 | DNS가 죽으면 전부가 동시에 죽음 |

왼쪽에서 오른쪽으로 가면서 사라진 게 뭔지 한 단어로 말하면 — **사람의 개입 지점**입니다. 그게 이득이자 동시에 비용입니다.

## 6. 표에 안 적히는 진짜 전환 — 명령형에서 선언형으로

위 표에서 한 줄만 남겨야 한다면 "설정 방식" 줄입니다. 나머지는 대체로 그 결과입니다.

도입 전에는 **내가 시스템에게 무엇을 하라고** 말합니다. 재시작해라, 늘려라, 이 버전으로 바꿔라. 시스템은 시킨 것만 하고, 시킨 다음에 벌어지는 일은 내 책임입니다.

도입 후에는 **시스템에게 어때야 하는지**를 말합니다. "이 앱은 항상 3개 떠 있어야 한다." 그리고 현재 상태와 그 선언 사이의 차이를 메우는 일은 시스템이 계속 반복합니다. 컨트롤 루프입니다.

이 차이가 실무에서 어떻게 나타나냐면 — **내 손이 오답이 됩니다.** 지난 글에 적었듯이 저는 스케줄 잡 하나를 임시로 고치려고 `kubectl set env` 를 썼다가 90초 만에 원복당한 적이 있습니다. 잘못된 건 시스템이 아니라 저였습니다. 선언형에서 "지금 이 클러스터가 어때야 하는가"의 정본은 제 터미널이 아니니까요.

그래서 정확한 요약은 "쿠버네티스가 운영을 자동화한다"가 아니라 이겁니다 — **결정권이 사람의 손에서 저장소의 선언으로 옮겨갑니다.** 재현성을 사고, 즉흥적으로 손댈 자유를 팝니다. 좋은 거래지만, 거래인 건 맞습니다.

## 7. 다만 '자가 치유'는 치유가 아닙니다

전/후 표에서 가장 오해가 큰 줄입니다. 공식 정의를 그대로 옮기면 이렇습니다.

> Kubernetes restarts containers that fail, replaces containers, kills containers that don't respond to your user-defined health check, and doesn't advertise them to clients until they are ready to serve.[^k8s-overview]

**재시작하고, 교체하고, 죽이고, 준비될 때까지 트래픽을 안 줍니다.** 문장 어디에도 "고친다"는 말이 없습니다. 전부 증상에 대한 조치고, 원인은 그대로 남습니다.

그래서 도입 후의 진짜 위험은 장애가 아니라 **은폐된 장애**입니다. 제 클러스터에는 재시작 65회를 기록한 오퍼레이터가 지금도 `Running` 상태로 초록불을 켜고 있습니다. 이 이야기와 6노드 클러스터의 실제 숫자는 지난 글에 따로 적어 두었습니다 — [쿠버네티스 도입 전/후 표에 없는 열](/2026/08/18/what-the-kubernetes-before-after-table-does-not-price/).

## 8. 정리

- 컨테이너는 **한 대 안의 재현성**을 풀었고, **여러 대 사이의 배치·복구·발견·확장**은 빈칸으로 남겼습니다.
- 구글은 수만 대 규모 때문에 그 문제를 10년 먼저 만났고, Borg에서 **선언형 명세와 제어 루프**라는 답에 도달했습니다.
- 쿠버네티스는 그 답을 Go로 다시 써서 밖으로 내놓은 것입니다. 발표 2014-06-06, v1.0 2015-07-21.
- 도입 전/후의 본질적 차이는 기능 목록이 아니라 **누가 결정하는가**입니다. 사람의 명령에서 저장소의 선언으로 옮겨갑니다.
- 그리고 자동화되는 것은 **대응**이지 **원인**이 아닙니다. 초록불은 "정상"이 아니라 "지금은 응답한다"는 뜻입니다.

쿠버네티스를 쓸지 말지를 정할 때 물어야 할 질문은 "우리가 이 기능들이 필요한가"가 아니라 이쪽에 가깝습니다 — **우리가 즉흥적으로 손대는 자유를 내주고 재현성을 살 준비가 됐는가.** 그 거래를 받아들일 수 없는 조직에서는, 도구가 아무리 좋아도 매일 self-heal과 싸우게 됩니다.

---

[^k8s-overview]: Kubernetes Documentation, "Overview" — <https://kubernetes.io/docs/concepts/overview/>
[^wiki-k8s]: Wikipedia, "Kubernetes" — <https://en.wikipedia.org/wiki/Kubernetes>
[^wiki-docker]: Wikipedia, "Docker (software)" — <https://en.wikipedia.org/wiki/Docker_(software)>
[^borg]: Abhishek Verma, Luis Pedrosa, Madhukar R. Korupolu, David Oppenheimer, Eric Tune, John Wilkes, "Large-scale cluster management at Google with Borg", *Proceedings of the European Conference on Computer Systems (EuroSys)*, ACM, Bordeaux, France, 2015 — <https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/>
