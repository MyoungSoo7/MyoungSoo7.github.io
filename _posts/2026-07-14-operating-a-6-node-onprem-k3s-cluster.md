---
layout: post
title: "6노드 온프레미스 K3s 를 운영 한다는 것 — 노드 를 그림 으로 읽기"
date: 2026-07-14 22:00:00 +0900
categories: [devops, kubernetes, homelab]
tags: [kubernetes, k3s, etcd, eck, argocd, gitops, node-affinity, taints, operations, observability]
image: /assets/images/cluster/node_ilwon.png
---

집 에 K3s 클러스터 를 6노드 로 굴린다. 노트북·데스크탑·2014년 맥미니 가 섞인 *이기종* 온프레미스 다. 클라우드 처럼 노드 가 균일 하지 않으니, 운영 의 핵심 은 **"어느 워크로드 를 어느 노드 에 둘 것인가"** 로 수렴 한다. 이 글 은 그 클러스터 를 *노드별 한 장 씩* 그림 으로 뜯어 보며, 온프레미스 K3s 운영 에서 실제로 부딪힌 것 들 을 정리 한다.

> 아래 6장 은 지금 이 순간 의 클러스터 를 `kubectl` 로 긁어 코드 로 렌더 한 것 이다. 각 도형 하나 = 파드 하나, 도형 모양 이 종류 를 뜻한다 — **원기둥=DB · 육각=백엔드(Spring Boot) · 삼각=프론트 · 오각=etcd/메시징 · 사각=인프라**. 무리 하나 = 네임스페이스. (팔란티어 스타일 라인아트 를 순수 코드 로 그리는 렌더러 는 별도 프로젝트 다.)

---

## 1. 골격 — 3 control-plane + 3 worker, 그리고 etcd 3표

6노드 는 역할 이 갈린다. **lemuel · ilwon · solomon** 이 control-plane 겸 etcd voter(3표), **david · isagal · louise** 가 worker.

etcd 는 왜 3 인가. 쿼럼(과반) 을 위해서다 — 3표 중 2표 가 살아 있으면 클러스터 가 유지 된다. 그래서 voter 는 *홀수* 로 둔다(2 는 한 대 만 죽어도 과반 붕괴, 4 는 3 과 내구성 이 같은데 비용 만 는다). 이 3표 를 드는 게 control-plane 노드 의 *진짜 임무* 다 — 파드 를 많이 얹는 게 아니라.

---

## 2. control-plane 은 일부러 *비운다* (lemuel · solomon)

lemuel 과 solomon 을 보면 파드 가 4개 밖에 없다.

![lemuel — 4 pods, control-plane 전용](/assets/images/cluster/node_lemuel.png)

![solomon — 4 pods, control-plane 전용](/assets/images/cluster/node_solomon.png)

고장 이 아니다. **의도된 격리** 다. 두 노드 에 taint 를 걸어 일반 워크로드 를 안 받게 막아 뒀다.

- lemuel: `node-role.kubernetes.io/control-plane:NoSchedule` — 컨트롤플레인 전용. DaemonSet 과 traefik 만 뜬다.
- solomon: `dedicated:NoSchedule` — 전용 노드. 여기엔 로그 cold 티어(ES) 를 일부러 고정 했다.

왜 비우나. solomon 은 2014년 맥미니 라 클러스터 에서 제일 약하다. 약한 노드 에 앱 을 얹었다가 걔 가 흔들리면 etcd 표결 까지 위태롭다. 그래서 **표결 만 시키고 부하 는 최소 로** 둔다. 온프레미스 이기종 의 첫 교훈 — *가장 약한 노드 는 가장 중요한 일(합의) 만 시켜라.*

taint 를 안 걸고 그냥 두면? 스케줄러 가 "빈 노드" 로 보고 파드 를 밀어 넣는다. `NoSchedule` 이 "여긴 특별한 용도" 라는 선언 이다.

---

## 3. 무거운 건 센 노드 에 — 특화 (ilwon · david · isagal)

worker 3대 는 성격 이 뚜렷 하게 갈린다. 그림 의 *도형 구성* 만 봐도 읽힌다.

**ilwon — DB · 관측 허브.** 원기둥(DB) 무리 가 압도적 이다. 각 프로젝트 의 postgres/mysql/redis/elasticsearch 가 여기 로 몰려 있고, monitoring·argocd·logging 도 얹혀 있다.

![ilwon — DB/관측 허브, 원기둥(DB) 다수](/assets/images/cluster/node_ilwon.png)

**david · isagal — 백엔드.** 육각(Spring Boot) 이 지배적 이다. logistic·academy·sparta 같은 MSA 서비스 파드 가 여기 산다.

![david — 백엔드(Boot) 중심](/assets/images/cluster/node_david.png)

![isagal — 백엔드 + 프론트](/assets/images/cluster/node_isagal.png)

**louise — 혼합.** 정산·전자상거래 등 여러 도메인 이 섞인다.

![louise — 혼합 워크로드](/assets/images/cluster/node_louise.png)

이 특화 는 우연 이 아니라 `nodeSelector` / affinity / 로컬 PV 로 *묶어 둔* 결과 다. DB 는 로컬 디스크 성능 이 중요 하니 SSD 붙은 노드 에, 백엔드 는 CPU 여유 있는 노드 에. 이기종 이라 *균등 분산* 이 아니라 **적재적소** 가 답 이다.

---

## 4. 노드 를 *읽는* 법 — 관측 이 먼저다

운영 에서 제일 많이 하는 건 배포 가 아니라 **"지금 무슨 일 이 어디서 나는가" 를 읽는 것** 이다. 위 6장 처럼 클러스터 를 한눈 에 지도 화 하면, 사고 가 났을 때 *어느 노드 의 어느 종류* 가 문제인지 빠르게 좁혀 진다.

실제 로 이 지도 가 사고 를 풀어 준 적 이 있다. "ilwon 메모리 90% 초과" 알림 이 떴을 때, 지도 를 보면 ilwon 에 DB(원기둥) 와 관측 스택 이 몰려 있는 게 한눈 에 보인다 → 범인 은 앱 힙 이 아니라 *다수 의 DB/ES* 라는 게 즉시 좁혀 진다. 노드 를 읽을 수 있으면 진단 이 반 은 끝난다. 로그·메트릭 을 여러 각도 로 모으는 이야기 는 [로그 수집 여러 각도]({% post_url 2026-07-11-log-collection-many-angles %}) 에서 따로 다뤘다.

---

## 5. 실전 에서 밟은 함정 하나 — "워커 = 노드 코어 수"

관측 이 사고 를 좁혀 준 뒤, 실제 로 고친 사례 하나. logging 파이프라인 의 Logstash 파드 가 메모리 한계(2Gi) 에 딱 붙어 **OOMKilled 를 수백 번 반복** 하고 있었다.

원인 은 엉뚱 한 데 있었다. Logstash 의 `pipeline.workers` 를 명시 안 하면 **기본값 이 "노드 의 CPU 코어 수"** 다. 그런데 이 파드 는 12코어 짜리 노드(ilwon) 에 떠 있어서, cpuLimit 은 1 인데도 **워커 를 12개** 띄우고 있었다. 워커 × 배치 = 12 × 125 = *동시 처리 이벤트 1500개* 가 힙 을 짓눌렀다.

고친 건 한 줄 씩 둘 이다:

```yaml
pipelines:
  - pipeline.id: main
    pipeline.workers: 2      # cpuLimit=1 에 맞춤 (기본=코어수 함정 회피)
    pipeline.batch.size: 125
```

in-flight 를 1500 → 250 으로 줄이니 RSS 가 *100% → 81%* 로 내려가 안정 됐다. 노드 에 메모리 를 더 주는 게 아니라, **컨테이너 가 노드 전체 코어 를 제 것 으로 착각 하는 기본값** 을 바로잡은 것. 컨테이너 안 의 JVM/런타임 이 *cgroup 한도* 가 아니라 *호스트 스펙* 을 보고 튜닝 하는 함정 은 Logstash 만 의 얘기 가 아니다 — JVM 힙, GC 스레드, 각종 워커 풀 이 다 이 지점 에서 샌다.

---

## 6. 이 모든 걸 굳히는 것 — GitOps + operator

위 Logstash 수정 도 노드 에 직접 kubectl 로 꽂은 게 아니다. **helm 차트 를 고쳐 git 에 push → ArgoCD 가 동기화 → ECK operator 가 반영** 하는 GitOps 흐름 을 탄다. 클러스터 의 *바람직한 상태* 는 항상 git 에 있고, 손 으로 바꾼 건 operator 가 되돌린다.

- **ArgoCD** — git = 진실. selfHeal 로 드리프트 자동 교정.
- **ECK**(Elastic Cloud on K8s) — ES/Logstash/Kibana 를 CR 로 선언, operator 가 라이프사이클 관리.
- **velero** — 정기 백업(그림 의 사각 무리 중 상당수 가 완료된 백업 파드 다).

온프레미스 라도 "노드 에 ssh 로 들어가 고치는" 시대 는 지났다. *선언 하고, operator/GitOps 가 수렴 시키게* 하는 게 6노드 든 600노드 든 같은 원리 다.

---

## 정리

- **etcd 는 홀수(3)** — voter 는 파드 호스팅 이 아니라 합의 가 임무.
- **약한 노드 는 taint 로 비운다** — 격리 는 고장 이 아니라 설계.
- **이기종 은 균등 분산 이 아니라 적재적소** — DB 는 SSD 노드, 백엔드 는 CPU 노드.
- **노드 를 읽을 수 있으면 진단 이 반** — 클러스터 를 지도 화 하라.
- **컨테이너 기본값 은 노드 전체 를 제 것 으로 착각** 한다 — 워커·힙·GC 를 cgroup 에 맞춰 명시.
- **모든 변경 은 GitOps 로** — 손 이 아니라 선언 으로.

6노드 짜리 집 클러스터 지만, 여기서 배우는 원리 는 규모 와 무관 하다. 오히려 *제약 이 많은 이기종* 이라 "어디에 무엇 을" 이 더 선명 하게 드러난다.

---

*그림 은 실 클러스터 상태 를 코드 로 렌더 한 것 — running 파드 기준, 종류 분류 는 이름 규칙 휴리스틱 이라 근사치. 필드·수치 는 시점 에 따라 달라진다.*
