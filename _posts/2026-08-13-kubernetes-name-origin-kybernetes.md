---
layout: post
title: "쿠버네티스라는 이름은 어디서 왔나 — 마지막 날 차 안에서 정한 이름이 하필 제어이론의 어원이었던 사건"
date: 2026-08-13 20:20:00 +0900
categories: [kubernetes, infra, history]
tags: [kubernetes, k8s, borg, omega, cybernetics, control-theory, container, cncf, etymology]
---

> 쿠버네티스라는 이름은 **출시 마감 전날, 출근길 차 안에서** 정해졌다. 앞선 13개 후보가 전부 법무팀에서 반려된 뒤였다.
> 그런데 그렇게 급하게 고른 그리스어 단어가, 하필이면 **제어이론(control theory)의 어원**이었다.
> 이름이 나중에 아키텍처를 따라잡은 게 아니라, 아키텍처가 이미 그 이름이었다.

k3s 클러스터를 6노드로 굴리면서도 정작 이 이름의 뜻을 제대로 찾아본 적이 없었다. 찾아보니 흔히 도는 "그리스어로 조타수래요" 한 줄보다 훨씬 재미있는 이야기가 1차 출처에 남아 있었다.

## 1. 13개가 반려되고 남은 마지막 하루

공동 창시자 Joe Beda 가 2016년 GeekWire 인터뷰에서 직접 밝힌 경위다.

> "우리는 구글 법무팀을 통과하지 못한 이름이 13개나 있었어요. 마지막 날이었고, 뭐라도 골라야 했습니다. 출근길에 운전하면서 생각했죠. '이건 컨테이너선을 모는 것과 비슷한데. 그럼 조타수를 뭐라고 부르지?' 그래서 뭔가 이국적인 걸 찾아보려 했어요. 그리스어로 뭔지 전혀 몰랐고, 찾아봐야 했습니다."[^geekwire]

작명 과정에 대단한 서사는 없었다. 마감에 쫓긴 개발자가 사전을 뒤진 것이다. 재미있는 건 그다음이다.

## 2. κυβερνήτης — 조타수

쿠버네티스는 고대 그리스어 **κυβερνήτης (kybernḗtēs)** 에서 왔고, 뜻은 **조타수(helmsman) 또는 키잡이(pilot)** 다. 공식 문서가 그대로 밝히고 있다.[^k8sdocs]

2014년 최초 공개 당시 Eric Brewer 가 쓴 구글 오픈소스 블로그 발표문에는 친절하게도 발음까지 괄호로 달려 있다.

> "(궁금해하실 분들을 위해, Kubernetes (koo-ber-nay'-tace) 는 배의 '조타수'를 뜻하는 그리스어입니다.)"[^googleblog]

지금 아무도 그렇게 발음하지 않는다는 게 함정이다.

그리고 다들 쓰는 **K8s** 는 약자가 아니라 **글자 수 세기**다. K 와 s 사이에 글자가 8개(`ubernete`) 있어서 K8s 다.[^k8sdocs] i18n(internationalization), a11y(accessibility) 와 같은 방식이다.

## 3. 여기서부터가 진짜 — 같은 어원에서 '사이버네틱스'와 '거버너'가 나왔다

Joe Beda 가 급하게 고른 이 단어에는, 그가 몰랐을 내력이 붙어 있다.

1948년 노버트 위너(Norbert Wiener)는 새로운 학문 분야에 이름을 붙이면서 **정확히 같은 그리스어 단어**를 골랐다. 『Cybernetics: Or Control and Communication in the Animal and the Machine』 초판 서문이다.

> "우리는 제어와 통신 이론 전체를, 그것이 기계에서든 동물에서든, **Cybernetics** 라 부르기로 결정했다. 이는 그리스어 **κυβερνήτης**, 즉 조타수에서 만든 말이다. 이 용어를 택하면서 우리는 피드백 메커니즘에 관한 최초의 중요한 논문이 1868년 클러크 맥스웰이 발표한 거버너(governor)에 관한 글이라는 점, 그리고 **governor 자체가 κυβερνήτης 의 라틴어 변형에서 유래했다**는 점을 함께 기리고자 한다. 또한 배의 조타 기관이야말로 가장 이르고 가장 잘 발달한 피드백 메커니즘 중 하나라는 사실을 언급하고 싶다."[^wiener]

정리하면 하나의 어근에서 세 갈래가 나왔다.

| 갈래 | 결과 | 경로 |
| --- | --- | --- |
| κυβερνήτης | **cybernetics** (사이버네틱스) | 위너가 1948년에 직접 조어 |
| κυβερνήτης | **governor** (조속기·통치자) | 라틴어 *gubernator* 를 거쳐 |
| κυβερνήτης | **Kubernetes** | 2014년, 출근길 차 안에서 |

`cyber-` 로 시작하는 현대의 모든 단어 — 사이버공간, 사이보그 — 가 이 조타수에서 나왔다. 그리고 쿠버네티스도 같은 곳에서 나왔다. **사촌지간이다.**

## 4. 우연이 아니었을지도 모른다: 컨트롤러는 문자 그대로 피드백 루프다

또 다른 공동 창시자 Craig McLuckie 는 2015년 CNCF KubeWeekly 에서 작명을 회고하며 한 마디를 덧붙였다.

> "컨테이너 쪽에서 떠오르던 항해 테마를 유지하고 싶었고 'Kubernetes'(그리스어로 조타수)가 적당해 보였습니다. **그 단어가 현대 제어이론에 강한 뿌리를 두고 있다는 점도 좋았고요.**"[^kubeweekly]

이 부분이 이 글에서 가장 하고 싶은 이야기다. 위너가 조타수를 고른 이유는 낭만이 아니라 **기술적인 이유**였다. 배의 키는 피드백 제어의 원형이다. 목표 침로가 있고, 현재 침로를 관측하고, 그 차이만큼 키를 꺾고, 다시 관측한다. 바람과 조류가 계속 배를 밀어내기 때문에 이 루프는 절대 끝나지 않는다.

쿠버네티스 컨트롤러가 하는 일이 정확히 이것이다.

```
목표 상태(spec)  ─┐
                 ├─→ 차이(diff) ─→ 조치(act) ─┐
현재 상태(status)─┘                            │
       ↑                                       │
       └───────────── 관측(observe) ←──────────┘
```

`replicas: 3` 이라고 선언하면 컨트롤러는 "3개를 만들어라"라는 명령을 한 번 실행하고 끝내지 않는다. 계속 관측하고, 계속 차이를 좁힌다. 파드 하나가 죽으면 다시 만든다. 노드가 빠지면 다시 스케줄한다. **바람과 조류에 맞서 침로를 유지하는 것과 같은 구조다.** 명령형이 아니라 선언형인 이유, `kubectl apply` 가 "실행"이 아니라 "선언"인 이유가 여기 있다.

마감에 쫓겨 고른 이름이 시스템의 작동 원리를 정확히 서술하게 된 셈이다.

## 5. 감춰진 진짜 이름: 보그, 그리고 세븐 오브 나인

공개된 이름이 조타수라면, 내부 코드명은 완전히 다른 세계관이었다.

구글의 내부 클러스터 관리 시스템 이름이 **Borg** — 스타트렉의 그 종족이다. 그래서 후속 오픈소스 프로젝트의 코드명도 스타트렉에서 가져왔다. 공동 창시자 Craig McLuckie 가 구글 클라우드 공식 블로그에 쓴 글이다.

> "보그 테마를 유지하는 차원에서, 우리는 그것을 **Project Seven of Nine** 이라 이름 붙였다. (참고: 원래 이름에 대한 오마주로, **이것이 쿠버네티스 로고가 7각형인 이유이기도 하다**.)"[^origin]

세븐 오브 나인은 스타트렉 보이저에 나오는, 보그 집단에서 해방된 인물이다. Joe Beda 의 설명이 의도를 더 분명히 한다.

> "우리는 그걸 '세븐 오브 나인'으로 소개했어요. 보그 드론이었다가 벗어난 스타트렉 보이저 캐릭터죠. 보그는 구글 내부판 쿠버네티스의 코드명이었고요. 완전히 덕후 문화입니다. **우리는 좀 더 친근한 보그를 원했어요.**"[^geekwire]

McLuckie 는 그냥 'Seven' 으로 부르고 싶었지만 "뻔한 이유로 잘 되지 않았다"고 적었다.[^kubeweekly] 파라마운트의 상표권을 통과할 리 없었다.

그래서 지금, 여러분이 매일 보는 그 조타륜 로고의 **살이 7개인 것은 우연이 아니다.** 상표권 때문에 지울 수밖에 없었던 이름이 도형의 개수로 살아남았다.

## 6. 계보: Borg → Omega → Kubernetes

이름만 물려받은 게 아니다. 구글은 컨테이너 관리 시스템을 세 번 만들었고, 그 계보를 창시자들이 직접 논문으로 정리했다.[^bok]

**Borg** 는 2015년 EuroSys 논문으로 공개됐다. 수십만 개의 job 을, 각각 수만 대 규모인 여러 클러스터에서 돌리는 시스템이다.[^borg] 논문에 나오는 구성요소 이름을 보면 지금 우리가 쓰는 것들의 조상이 그대로 보인다.

| Borg (C++) | Kubernetes (Go) |
| --- | --- |
| Borgmaster | kube-apiserver / controller-manager |
| Borglet (모든 머신에 상주하는 에이전트) | kubelet |
| Task | Pod |
| Cell | Cluster |

**Borglet → kubelet** 은 이름까지 거의 그대로 넘어왔다. Borg 의 모든 구성요소는 C++ 로 작성됐고,[^borg] 쿠버네티스는 Go 로 다시 쓰였다.

세 번째 시스템에 대해 창시자들은 이렇게 정리한다. Borg 와 Omega 가 순수 구글 내부용으로 개발된 것과 대조적으로 쿠버네티스는 오픈소스이고, Omega 가 저장소를 신뢰된 컨트롤 플레인 컴포넌트에 직접 노출한 것과 달리 **쿠버네티스의 상태는 오직 REST API 를 통해서만 접근된다**는 것이다.[^bok] 오늘날 우리가 `kubectl` 로 하는 모든 일이 결국 API 서버 한 곳을 지나는 이유가 여기서 결정됐다.

## 7. 최초 커밋에 남아 있는 증거

Joe Beda 는 4주년 기념 글에서 이렇게 썼다.

> "2014년 6월 6일, 나는 훗날 쿠버네티스의 공개 저장소가 될 것의 첫 커밋을 체크인했다. (…) 그 시점의 쿠버네티스 버전은 앞으로 될 것의 그림자에 불과했다. 핵심 개념은 있었지만 매우 거칠었다. **예를 들어 Pod 는 Task 라고 불렸다. 그건 공개 하루 전에 바뀌었다.**"[^4years]

이건 지금도 직접 확인할 수 있다. 최초 커밋 `2c4b3a5` (2014-06-06T23:40:48Z, 250개 파일, +47,501줄) 의 파일 목록에는 `pod` 이라는 단어가 없고 대신 이런 파일들이 있다.[^firstcommit]

```
api/doc/task-schema.json
api/examples/task.json
api/examples/task-list.json
```

Borg 의 용어인 **Task** 가 그대로 들어 있다. 공개 하루 전에야 Pod 으로 바뀐 것이다. 구글 내부 시스템의 언어가 마지막 순간까지 남아 있었다는 증거가 커밋 하나에 박제돼 있는 셈이다.

Brendan Burns 의 프로토타입은 원래 **Java** 로 작성됐고, 팀이 이를 Go 로 다시 썼다.[^4years] 공개 발표는 2014년 6월 10일, 첫 DockerCon 에서 Eric Brewer 의 키노트로 이뤄졌다.[^4years]

## 정리

- **Kubernetes** = 그리스어 κυβερνήτης = 조타수. 마감 전날 출근길에 급히 정해졌고, 그전에 13개 후보가 법무팀에서 반려됐다.
- 같은 어원에서 **cybernetics**(위너, 1948)와 **governor**(라틴어 gubernator 경유)가 나왔다. 위너가 이 단어를 고른 이유는 **배의 키가 피드백 제어의 원형**이기 때문이었다.
- 그래서 쿠버네티스 컨트롤러의 조정 루프(reconciliation loop)는 이름과 정확히 같은 구조다. 우연치고는 지나치게 잘 맞고, McLuckie 본인도 "제어이론의 뿌리"를 언급했다.
- **K8s** 는 K 와 s 사이 글자 8개.
- 코드명은 **Project Seven of Nine**(보그에서 해방된 스타트렉 캐릭터)이었고, 상표 문제로 지워진 그 이름이 **7각형 로고**로 남았다.
- 계보는 **Borg(C++) → Omega → Kubernetes(Go)**. Borglet 은 kubelet 이 되었고, Task 는 Pod 이 되었다 — 공개 하루 전에.

집에서 k3s 를 굴리든 GKE 를 쓰든, `kubectl apply` 를 칠 때마다 우리는 2500년 된 조타수에게 침로를 맡기고 있는 셈이다. 바람은 계속 분다. 그래서 루프는 멈추지 않는다.

---

## References

[^geekwire]: Dan Richman, ["How did they ever come up with that kooky 'Kubernetes' name? Here's the inside story"](https://www.geekwire.com/2016/ever-come-kooky-kubernetes-name-heptio/), GeekWire, 2016-11-17. 공동 창시자 Craig McLuckie·Joe Beda 인터뷰.
[^k8sdocs]: Kubernetes 공식 문서, ["Overview"](https://kubernetes.io/docs/concepts/overview/). "The name Kubernetes originates from Greek, meaning helmsman or pilot. K8s as an abbreviation results from counting the eight letters between the 'K' and the 's'."
[^googleblog]: Eric Brewer, ["An update on container support on Google Cloud Platform"](https://opensource.googleblog.com/2014/06/an-update-on-container-support-on.html), Google Open Source Blog, 2014년 6월. 쿠버네티스 최초 공개 발표문.
[^wiener]: Norbert Wiener, *Cybernetics: Or Control and Communication in the Animal and the Machine*, 1948, 서론. 원문 스캔: [Monoskop](https://www.monoskop.org/images/0/08/Wiener_Norbert_1948_Cybernetics.pdf).
[^kubeweekly]: ["KubeWeekly #12"](https://www.cncf.io/kubeweekly/kubeweekly-12/), CNCF, 2015-06-02. Craig McLuckie 의 작명 회고 코멘트 인용.
[^origin]: Craig McLuckie, ["From Google to the world: The Kubernetes origin story"](https://cloud.google.com/blog/products/containers-kubernetes/from-google-to-the-world-the-kubernetes-origin-story), Google Cloud Blog, 2016-07-23.
[^bok]: Brendan Burns, Brian Grant, David Oppenheimer, Eric Brewer, John Wilkes, ["Borg, Omega, and Kubernetes"](https://cacm.acm.org/practice/borg-omega-and-kubernetes/), *Communications of the ACM* / ACM Queue, 2016.
[^borg]: Abhishek Verma, Luis Pedrosa, Madhukar Korupolu, David Oppenheimer, Eric Tune, John Wilkes, ["Large-scale cluster management at Google with Borg"](https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/), EuroSys '15, Bordeaux, France, 2015. DOI [10.1145/2741948.2741964](https://doi.org/10.1145/2741948.2741964).
[^4years]: Joe Beda, ["4 Years of K8s"](https://kubernetes.io/blog/2018/06/06/4-years-of-k8s/), Kubernetes Blog, 2018-06-06.
[^firstcommit]: kubernetes/kubernetes 최초 커밋 [`2c4b3a562ce34cddc3f8218a2c4d11c7310e6d56`](https://github.com/kubernetes/kubernetes/commit/2c4b3a562ce34cddc3f8218a2c4d11c7310e6d56) (jbeda, 2014-06-06T23:40:48Z, 250 files, +47,501). 파일 목록에서 `task-schema.json` 등 확인 가능.
