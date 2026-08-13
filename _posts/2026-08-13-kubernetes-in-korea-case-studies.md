---
layout: post
title: "한국 기업의 쿠버네티스 사용 사례를 1차 출처로만 읽어봤다 — 공통점은 '클라우드로 갔다'가 아니었다"
date: 2026-08-13 17:00:00 +0900
categories: [kubernetes, case-study]
tags: [kubernetes, kakao, karrot, woowahan, toss, cilium, karpenter, eks, on-premise]
---

"국내 쿠버네티스 도입 사례"를 검색하면 상당수가 컨설팅사·솔루션 벤더의 요약 글이다. 그래서 이번에는 규칙을 하나 정하고 읽었다. **회사가 자기 이름으로 쓴 기술 글, CNCF 공식 케이스 스터디, KubeCon 공식 세션 프로그램만 본다.** 제3자 요약 블로그는 인용하지 않는다.

그렇게 읽고 나니 예상과 다른 그림이 나왔다. 한국 대기업의 쿠버네티스 이야기는 "IDC를 정리하고 클라우드로 갔다"가 아니었다. **거의 전부가 온프레미스를 그대로 두고, 그 위에서 쿠버네티스를 확장한 이야기**다.

---

## 1. 가장 큰 사례는 퍼블릭 클라우드가 아니다 — 카카오

CNCF가 2024년 7월에 공개한 [Kakao 케이스 스터디](https://www.cncf.io/case-studies/kakao/)의 숫자는 이렇다.

- 클러스터 **7,000개 이상**
- 노드 **120,000대 이상** (멀티 존)
- 국내 월간 활성 사용자 **1억 250만 명**

그런데 이 문서에서 정작 눈에 띄는 건 규모가 아니라 이 한 문장이다.

> "They run the platform on-premise, managing over 7,000 clusters and 120,000 nodes."
> — [CNCF, Kakao Case Study](https://www.cncf.io/case-studies/kakao/)

플랫폼은 **OpenStack 위에 자체 구축**되었고, 사내에 Kubernetes as a Service 형태로 제공된다. 초대규모 쿠버네티스 사례라고 하면 보통 EKS/GKE/AKS를 전제하는데, 국내 최대 사례는 그 반대편에 있다.

기술적 결정도 그 선택의 연장선이다. 카카오는 처음에 Cilium을 쓰면서 kube-proxy와 Nginx Ingress를 함께 얹었고, 그 조합이 문제를 만들었다.

> "우리는 이미 Cilium을 쓰고 있었지만 kube-proxy와 결합해서 썼고, 그게 많은 네트워크 문제를 일으켰습니다. 네트워크 이슈 콜이 오면 kube-proxy와 Cilium, 그리고 L7 정책을 위한 Nginx Ingress까지 파고들어야 했기 때문에 해결이 어려웠습니다."
> — Kwang Hun Choi, Cloud Engineer, Kakao Corp ([CNCF Kakao Case Study](https://www.cncf.io/case-studies/kakao/))

재평가에서 Calico·Flannel과 다시 비교한 끝에 Cilium을 택했고, 이번에는 **kube-proxy 완전 대체(full kube-proxy replacement) 모드**로 갔다. 커널을 직접 관리할 수 있는 온프레미스 환경이라 eBPF 기반 데이터플레인을 택하기 쉬웠다는 점은, 앞의 "on-premise"와 따로 떼어 읽기 어렵다.

### 왜 클러스터를 7,000개로 쪼갰나 — 화재라는 국내 고유 변수

KubeCon + CloudNativeCon Europe 2024 공식 프로그램에 올라온 카카오 세션 초록에는 이런 문장이 있다.

> "Due to a data center fire that occurred last year, we experienced significant economic and social impacts. ... Therefore, cluster high-availability has become an important consideration."
> — [Architecting Resilience: Lessons from Managing 7K+ Kubernetes Clusters at Scale](https://kccnceu2024.sched.com/event/1YeLc/architecting-resilience-lessons-from-managing-7k+-kubernetes-clusters-at-scale-kwanghun-choi-gyutae-bae-kakao), Kwanghun Choi & Gyutae Bae, Kakao

해외 컨퍼런스 자료에서 국내 데이터센터 화재가 HA 설계의 직접적 동기로 명시된 문서다. 성장 속도도 공식 프로그램에서 확인된다 — 2022년 KubeCon NA 세션 초록은 **1년 사이 클러스터 2,000개·노드 20,000대에서 7,000개 이상·노드 100,000대 이상으로** 늘었다고 적고 있다([Surviving From Endless Issues Coming From 7K+ Kubernetes Clusters](https://kccncna2022.sched.com/event/182G8/surviving-from-endless-issues-coming-from-7k+-kubernetes-clusters-wanhae-lee-seok-yong-hong-kakao-corp)).

---

## 2. 하이브리드는 과도기가 아니라 목적지 — 카카오페이증권·토스

카카오페이 기술 블로그의 [멀티 & 하이브리드 클러스터 글](https://tech.kakaopay.com/post/multi-cluster/)에 따르면, 카카오페이증권의 서비스는 **AWS EKS, IDC Kubernetes, KakaoCloud Kubernetes Engine 세 플랫폼**에서 동시에 돈다. 그리고 이건 "언젠가 하나로 합칠 중간 상태"로 서술되지 않는다.

- 즉각적 스케일링이나 매니지드 서비스 연동이 필요하면 클라우드 클러스터
- 내부 시스템만 호출하는 서비스는 비용·운영 효율상 IDC 클러스터
- 배포 명세의 `platform` 항목을 `aws-app`에서 `[aws-app, idc-app]`으로 바꾸는 것만으로 멀티 클러스터 배포
- 플랫폼 단위 장애는 GSLB가 헬스체크 실패 IP를 빼고 나머지에 비율을 재조정해 흡수

여기서 한 발 더 나간 게 **하이브리드 클러스터**다. AWS Auto Scaling Group 노드, KakaoCloud VM 노드, IDC 물리 장비 노드를 **하나의 논리적 쿠버네티스 클러스터**로 묶는다. 심지어 control plane도 그렇게 구성해서 etcd와 제어 컴포넌트를 여러 플랫폼·존에 흩어 놓는다. 목적은 명확하다 — stateful 서비스를 단일 클러스터 수준에서 다루면서도 특정 클라우드 장애에 클러스터 전체가 흔들리지 않게 하는 것.

토스도 같은 전제 위에 있다. toss.tech의 [제로트러스트 보안 고도화 글](https://toss.tech/article/42675)은 컨테이너 런타임 보안을 환경별로 나눠 설명한다 — **IDC 쿠버네티스 환경에는 Falco**, **AWS 환경에는 GuardDuty 컨테이너 런타임 보안**. 보안 아키텍처를 두 벌 유지한다는 건, 하이브리드가 잠깐 참는 상태가 아니라는 뜻이다.

---

## 3. 공개된 수치는 대부분 '성능'이 아니라 '리소스 효율'이다

읽은 글들에서 회사가 스스로 숫자를 밝힌 대목을 모아 보면 방향이 한쪽으로 쏠린다.

**카카오페이증권 — Dr.Pym 프로젝트** ([if(kakaoAI)2024 발표 정리](https://tech.kakaopay.com/post/ifkakao2024-dr-pym-project/))
Prometheus 지표를 주 단위로 분석해 CPU/메모리 추천값을 계산하고, KEDA로 이벤트 기반 스케일링을 붙였다. 결과로 밝힌 수치는 **EKS 약 21% 비용 절감**, IDC는 비용 대신 **노드 기준 약 18%의 여유 확보**(100대 기준 약 18대). 발표 당시 스케일 임계값을 150%로 소개했다가 안정성을 이유로 100%로 낮춰 운영 중이라는 정정까지 글에 적어 두었다.

**우아한형제들 — Spark on Kubernetes** ([기술블로그](https://techblog.woowahan.com/10291/))
EMR on EKS로 옮기며 얻은 것으로 **클러스터 프로비저닝 15분 → 2분**을 든다. 성능은 조심스럽게 적었다 — 대용량 셔플 쿼리에서는 오히려 낮았고, scratch space를 `emptyDir`에서 `hostPath`로 바꿔 **약 10%** 회복했다는 식이다. driver는 온디맨드, executor는 스팟에 두고 Graceful Executor Decommissioning으로 스팟 회수를 흡수한다.

성능이 좋아졌다는 주장보다 **낭비를 줄였다는 주장이 압도적으로 많다.** 이건 온프레미스를 함께 굴리는 조직의 손익 구조와 맞아떨어진다 — IDC에서 아낀 자원은 청구서가 아니라 여유 노드로 돌아온다.

---

## 4. 규모가 커지면 애플리케이션이 아니라 노드 하부가 터진다 — 당근

가장 구체적인 실패 기록은 당근 기술 블로그의 [EKS Job 노드그룹 오토스케일링 글](https://medium.com/daangn/our-journey-to-autoscaling-eks-node-groups-for-job-workloads-e8a6a7ed845e)(2026-04)이다. Job 워크로드는 한번 시작하면 중단하기 어려워서, scale-in을 하려면 파드를 여러 노드에 고루 퍼뜨리는 대신 **몇 대에 몰아넣는(bin-packing)** 전략이 필요하다. PodAffinity로 뭉치게 하고, 실행 중인 Job이 있는 노드는 오토스케일러가 scale-in 대상에서 제외하도록 어노테이션을 붙였다.

알파 환경에서는 잘 돌았다. 프로덕션에서는 매시 정각에 Job 파드가 한꺼번에 생성되면서 네 가지가 순서대로 터졌다.

| 증상 | 원인 | 대응 |
| --- | --- | --- |
| kubelet 과부하 (`kubelet_pleg_relist_duration_seconds` 급등) | 요청량보다 실제 CPU를 많이 쓰는 파드가 한 노드에 과밀 | kubelet `maxPods`를 60으로 제한 |
| `ImagePullBackOff` 빈발 | 레지스트리 풀 요청 병목 | `registryPullQPS` 5 → 40, `registryBurst` 10 → 60 |
| EBS 볼륨 스로틀링 | 동시 기동 시 IO 폭증 | IOPS 3,000 → 8,000, 처리량 150MB/s → 800MB/s |
| CNI 플러그인 IP 할당 지연 | 파드마다 IP를 새로 배정 | Host Network Mode로 할당 과정 자체를 우회 |

주목할 점은 **네 개 전부 애플리케이션 코드 밖의 문제**라는 것이다. 그리고 "Pod Right-sizing이 가장 이상적이지만 모든 Job에 적용하는 건 현실적이지 않다고 판단했다"고 솔직히 적은 뒤 차선책으로 `maxPods`를 택한 서술이, 이 글을 다른 성공담들과 구별해 준다.

같은 회사의 [검색 엔진 ECK 이관기](https://medium.com/daangn/%EB%8B%B9%EA%B7%BC%EB%A7%88%EC%BC%93-%EA%B2%80%EC%83%89-%EC%97%94%EC%A7%84-%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%EB%A1%9C-%EC%89%BD%EA%B2%8C-%EC%9A%B4%EC%98%81%ED%95%98%EA%B8%B0-bdf2688df267)(2023)도 비슷한 태도다. 약 5개월이 걸렸고, 마지막에 OKR **달성률 7~80%, 100%는 못 했다**고 적었다.

---

## 5. 벤더 채널의 사례는 등급을 나눠 읽어야 한다

AWS 한국 기술 블로그에도 국내 사례가 여럿 있다. [우아한형제들 Data on EKS](https://aws.amazon.com/ko/blogs/tech/woowa-brothers-amazon-data-on-eks-data-platform/)(2024-11)는 Airflow를 먼저 옮겨 EKS 역량을 쌓은 뒤 나머지를 이관한 순서, Karpenter + KEDA 조합, IDC GPU 서버에 **EKS Anywhere**를 얹은 구성, Apache YuniKorn의 bin packing·gang scheduling 활용을 설명한다. [마이다스인의 ECS → EKS 전환기](https://aws.amazon.com/ko/blogs/tech/midas-eks-migration-idp-journey-with-amazon-q-part1/)(2026-01)는 자원 활용률 40% → 70% 이상, 환경 생성 4시간 → 5분, Spot + binpacking으로 최대 25% 절감을 제시한다.

내용 자체는 구체적이고 유용하다. 다만 **출처 등급이 다르다.** 이 글들은 AWS가 자사 서비스 채택 사례로 게재한 것이고, 수치는 고객사 자체 보고이며, 대조군이 있는 실험이 아니다. 앞의 자사 기술 블로그 글들과 같은 무게로 인용하면 안 된다. 이 글에서는 "그 회사가 이렇게 구성했다"는 아키텍처 서술만 가져오고, 절감률은 **벤더 채널의 자체 보고 수치**라고 라벨을 붙여 둔다.

---

## 정직하게 남겨 둘 한계

- **생존 편향.** 여기 인용된 건 전부 *공개하기로 결정한* 회사의 *공개하기로 결정한* 프로젝트다. 실패해서 되돌린 이관, 쿠버네티스를 걷어낸 조직은 글로 남지 않는다.
- **자체 보고 수치.** 21%, 47%, 25% 같은 숫자는 전부 해당 조직이 자기 환경에서 측정해 밝힌 값이다. 재현 가능한 벤치마크가 아니고, 조건도 공개되지 않았다.
- **중립 통계의 부재.** "국내 기업 쿠버네티스 도입률"처럼 이 글의 결론을 뒷받침할 만한 **중립 제3자의 한국 대상 조사**는 이번에 찾지 못했다. 그래서 위의 "공통점"은 국내 전체의 경향이 아니라, **공개된 소수 대형 사례에서 반복 관찰된 패턴**으로만 읽어야 한다.
- 카카오가 온프레미스를 택한 *이유*는 CNCF 케이스 스터디에 명시되어 있지 않다. 규모·주권·비용·커널 제어 같은 추정은 가능하지만, 근거가 있는 서술은 "온프레미스로 운영한다"까지다.

---

## 그래서 내가 가져가는 것

내 홈랩은 노드 5대짜리 K3s다. 카카오의 7,000 클러스터와 비교할 대상이 아니다. 그런데 위 글들에서 **규모와 무관하게 반복되는 것**이 셋 있었다.

1. **온프레미스를 부끄러워하지 않는다.** 국내 최대 사례가 온프레미스다. 홈랩이든 IDC든, "언젠가 클라우드로 갈 임시 상태"로 다룰 이유는 없다.
2. **장애의 폭발 반경을 먼저 설계한다.** 화재 한 번이 카카오의 HA 전략을 바꿨고, 카카오페이증권은 control plane까지 흩어 놓았다.
3. **터지는 곳은 아래쪽이다.** kubelet, CNI, 디스크 처리량. 당근이 프로덕션에서 만난 네 가지는 모두 노드 하부였다. 내 홈랩에서 시간을 가장 많이 잡아먹은 것들도 애플리케이션이 아니라 [node-local DNS 캐시 설정](/2026/05/11/k3s-nodelocal-dns-cluster-dns-디버깅/)이나 노드 링크 품질 쪽이었다. 이건 규모를 타지 않는 교훈으로 보인다.

---

## References

**1차·공식**

- CNCF, [Kakao Case Study](https://www.cncf.io/case-studies/kakao/), 2024-07-25
- KubeCon + CloudNativeCon Europe 2024 공식 프로그램, [Architecting Resilience: Lessons from Managing 7K+ Kubernetes Clusters at Scale](https://kccnceu2024.sched.com/event/1YeLc/architecting-resilience-lessons-from-managing-7k+-kubernetes-clusters-at-scale-kwanghun-choi-gyutae-bae-kakao) (Kwanghun Choi, Gyutae Bae — Kakao)
- KubeCon + CloudNativeCon North America 2022 공식 프로그램, [Surviving From Endless Issues Coming From 7K+ Kubernetes Clusters](https://kccncna2022.sched.com/event/182G8/surviving-from-endless-issues-coming-from-7k+-kubernetes-clusters-wanhae-lee-seok-yong-hong-kakao-corp) (Wanhae Lee, Seok-yong Hong — Kakao Corp)

**각 사 자체 기술 블로그 (자사 사례에 대한 1차 보고, 수치는 자체 측정)**

- 카카오페이 기술 블로그, [99.999%를 향한 집착: 멀티 & 하이브리드 클러스터로 살아남기](https://tech.kakaopay.com/post/multi-cluster/)
- 카카오페이 기술 블로그, [if(kakaoAI)2024 — 카카오페이증권의 Kubernetes 지능형 리소스 최적화 (feat. Dr.Pym Project 공유)](https://tech.kakaopay.com/post/ifkakao2024-dr-pym-project/)
- 당근 테크 블로그, [Our Journey to Autoscaling EKS Node Groups for Job Workloads](https://medium.com/daangn/our-journey-to-autoscaling-eks-node-groups-for-job-workloads-e8a6a7ed845e), 2026-04
- 당근 테크 블로그, [당근마켓 검색 엔진, 쿠버네티스로 쉽게 운영하기](https://medium.com/daangn/%EB%8B%B9%EA%B7%BC%EB%A7%88%EC%BC%93-%EA%B2%80%EC%83%89-%EC%97%94%EC%A7%84-%EC%BF%A0%EB%B2%84%EB%84%A4%ED%8B%B0%EC%8A%A4%EB%A1%9C-%EC%89%BD%EA%B2%8C-%EC%9A%B4%EC%98%81%ED%95%98%EA%B8%B0-bdf2688df267), 2023-08
- 우아한형제들 기술블로그, [Spark on Kubernetes로 이관하기](https://techblog.woowahan.com/10291/), 2023-01
- 토스 기술 블로그, [경계 보안부터 제로트러스트 보안까지, 고도화 여정](https://toss.tech/article/42675)

**벤더 채널의 고객 사례 (AWS 게재, 수치는 고객사 자체 보고 — 대조군 없음)**

- AWS 기술 블로그, [우아한형제들의 Data on EKS 중심의 데이터 플랫폼 구축 사례](https://aws.amazon.com/ko/blogs/tech/woowa-brothers-amazon-data-on-eks-data-platform/), 2024-11
- AWS 기술 블로그, [마이다스인의 플랫폼 혁신 여정, Part1: Amazon EKS 전환](https://aws.amazon.com/ko/blogs/tech/midas-eks-migration-idp-journey-with-amazon-q-part1/), 2026-01
