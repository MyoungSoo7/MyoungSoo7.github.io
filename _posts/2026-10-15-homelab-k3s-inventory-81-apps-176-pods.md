---
layout: post
title: "홈랩 쿠버네티스 한 장 지도 — 6노드에 앱 81개, 파드 176개가 어떻게 나뉘어 도는가"
date: 2026-10-15 00:40:00 +0900
categories: [devops]
tags: [kubernetes, k3s, homelab, argocd, gitops, capacity, inventory]
---

"지금 쿠버네티스에 서비스가 몇 개 돌지?" 라는 질문을 받았다. 대답은 생각보다 간단하지 않다.
네임스페이스를 셀지, ArgoCD 앱을 셀지, 파드를 셀지에 따라 숫자가 54, 81, 176으로 달라진다.

이 글은 2026-10-15 00:55 KST 에 우리 홈랩 k3s 클러스터를 실측한 스냅숏이다. 숫자는 모두 `kubectl` 출력 그대로다.
"무엇을 세는가"를 같이 정리해 두면, 다음에 같은 질문을 받았을 때 숫자 하나가 무엇을 뜻하는지 바로 말할 수 있다.

## 1. 숫자부터 — 무엇을 세느냐에 따라 다르다

| 단위 | 개수 | 상태 |
|---|---|---|
| 노드 | 6 | 모두 Ready |
| 네임스페이스 | 54 | — |
| ArgoCD Application | 81 | **81개 모두 Synced + Healthy** |
| Deployment | 99 | 모두 목표 레플리카 충족 |
| StatefulSet | 24 | 모두 목표 레플리카 충족 |
| DaemonSet | 10 | — |
| Service | 129 | — |
| 파드 | 176 Running + 22 Completed | 비정상 0 |

각 단위가 무엇인지 짧게 짚고 가자.

- **Deployment** 는 상태 없는 앱을 원하는 개수만큼 유지하는 컨트롤러다([공식 문서](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)). 웹 서버·API 가 여기에 해당한다.
- **StatefulSet** 은 파드마다 고정된 이름과 저장소가 필요한 워크로드용이다([공식 문서](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)). 우리 클러스터에선 DB, Elasticsearch, Kafka, Prometheus 가 여기 있다.
- **DaemonSet** 은 노드마다 하나씩 뜨는 파드다([공식 문서](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)). 로그 수집기, 보안 감시(Falco), 백업 에이전트처럼 "모든 노드에 있어야 하는 것"이다.
- **Completed 22개**는 장애가 아니다. 백업 저장소 정리 같은 일회성 Job 이 끝나고 남긴 기록이다.

그래서 "서비스 몇 개냐"에 대한 정직한 답은 이렇다. **사람이 쓰는 운영 앱은 24개, 그걸 받치는 것까지 합친 배포 단위는 81개, 실제 프로세스는 176개.**

## 2. 앱 81개는 무엇인가 — 세 무리로 나눈다

### 운영 앱 (`-prod` 네임스페이스 24개)

정산(settlement), 블로그 검색, 사진 보관(immich), 비밀번호 관리(vaultwarden), 프로젝트 관리(plane), 업타임 감시(uptime-kuma), 메모(memos), 랜딩 페이지,
코딩 테스트, 분석, 미디어 검색, 블로그(ghost) 등이다. 파드 수로는 정산과 plane 이 각각 11개로 가장 크다.

이 중 crypto·trading 두 네임스페이스는 남아 있지만 **파드가 0개**다. 쓰지 않는 서비스를 내려 메모리를 확보하면서, 다시 올릴 수 있게 껍데기만 둔 상태다.

### 플랫폼·운영 도구

ArgoCD(배포), monitoring(Prometheus·Grafana·Tempo), logging(Elasticsearch·Logstash), Falco(런타임 보안), Velero(백업), Kafka, n8n(자동화),
cloudflared(외부 노출 터널), 레지스트리 미러, sops-operator(비밀값 복호화), NFS 서버 등이다.

파드 수 상위를 보면 이 무리가 얼마나 무거운지 보인다.

| 네임스페이스 | Running 파드 |
|---|---|
| kube-system | 19 |
| agent-system | 15 |
| monitoring | 13 |
| logging | 12 |
| settlement-prod | 11 |
| plane-prod | 11 |
| argocd | 8 |
| velero | 7 |
| falco | 7 |

상위 9개 중 운영 앱은 둘뿐이다. 홈랩에서도 **앱을 돌리는 비용보다 앱을 지켜보고 지키는 비용이 더 크다.**

### 에이전트·실험

보안 분석 에이전트(agent-system), CI 러너(arc-runners), IoT 실험(iot), 반도체 팹 실험(fab-lab) 등이다.
fab-lab 은 며칠 전 [팹 IoT 연구]({% post_url 2026-10-12-fab-iot-2-fdc-detector-comparison %})로 돌린 장비 이상 감지 실험을 실제 클러스터에 올린 것이다.

## 3. 6노드에 어떻게 나뉘어 있나

| 노드 | 코어 | 메모리 | 역할 | Running 파드 | CPU 사용 | 메모리 사용 |
|---|---|---|---|---|---|---|
| lemuel | 4 | 32GB | 컨트롤 플레인 | 36 | **60%** | 50% |
| ilwon | 12 | 32GB | 컨트롤 플레인 | 25 | 8% | **85%** |
| david | 6 | 16GB | 워커 | 39 | 4% | 51% |
| louise | 8 | 16GB | 워커 | 32 | 7% | 47% |
| isagal | 40 | 16GB | 워커 | 23 | 1% | 59% |
| solomon | 4 | 16GB | 워커 | 21 | 21% | 55% |

(`kubectl top nodes` 한 시점 값. 사용률은 순간값이라 시간대에 따라 움직인다.)

이 표에서 읽을 것이 세 가지다.

1. **파드 수는 부하를 말해 주지 않는다.** 파드가 가장 많은 david 는 CPU 4% 이고, 파드가 21개뿐인 solomon 이 21% 다. 무거운 파드 하나가 가벼운 파드 열 개보다 크다.
2. **병목은 노드마다 다르다.** lemuel 은 CPU(2코어 노트북이 컨트롤 플레인과 쿠버네티스 밖 스택까지 진다), ilwon 은 메모리(85%)다. "클러스터 전체 사용률"로 평균을 내면 둘 다 안 보인다.
3. **40코어 isagal 은 CPU 1% 다.** 코어는 남지만 메모리는 16GB 라, 병렬 작업을 많이 올리면 메모리부터 막힌다. 실제로 이 노드는 36병렬 시뮬레이션에 메모리가 넘쳐 멈춘 적이 있다.

쿠버네티스 스케줄러는 사용률이 아니라 파드가 선언한 **requests** 를 보고 자리를 잡는다([공식 문서](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)).
그래서 requests 를 실제보다 작게 적은 파드가 많으면, 스케줄러 눈에는 여유가 있는데 실제 노드는 85% 가 되는 일이 생긴다. ilwon 의 85% 는 그 방향으로 먼저 의심해 볼 숫자다.

## 4. 저장소 — 7개 StorageClass

| StorageClass | 방식 | 용도 |
|---|---|---|
| local-path (기본) | k3s 기본 동적 프로비저너 | 일반 PVC |
| solomon-local | local-path | solomon 전용 |
| elk-hot / elk-warm / elk-cold | 수동 볼륨 | Elasticsearch 데이터 계층 |
| ssd-local | 수동 볼륨 | SSD 가 필요한 워크로드 |
| nfs-shared | 수동 볼륨 | 여러 파드가 공유 |

k3s 는 노드 로컬 디스크를 쓰는 Local Path Provisioner 를 기본으로 넣어 준다([k3s 저장소 문서](https://docs.k3s.io/storage)).
편하지만 볼륨이 **그 노드에 묶인다**는 뜻이기도 하다. 노드가 죽으면 그 위의 PVC 를 쓰던 StatefulSet 도 같이 멈춘다.
그래서 이 클러스터에서는 Velero 로 볼륨을 매일 백업한다. 그 백업이 최근 [R2 요금의 주범](https://developers.cloudflare.com/r2/pricing/)이었다는 건 별도로 정리할 이야기다.
(백업 147GiB 중 117GiB 가 지표·로그 볼륨이었다.)

## 5. 81개가 전부 Healthy 인 이유

81개 앱이 동시에 Synced + Healthy 인 건 운이 아니라 구조다.

- **GitOps.** 모든 앱은 Git 리포의 매니페스트를 ArgoCD 가 클러스터에 맞춘다. 81개 중 77개는 자동 동기화의 self-heal 이 켜져 있어서, 노드에서 손으로 고친 것을 ArgoCD 가 Git 상태로 되돌린다([ArgoCD 자동 동기화](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)).
  그래서 "Synced" 는 "Git 에 적힌 대로 떠 있다"는 뜻이다.
- **Health 는 리소스 종류별 규칙이다.** Deployment 는 목표 레플리카가 다 준비됐는지, StatefulSet 은 롤아웃이 끝났는지를 본다([ArgoCD 헬스 체크](https://argo-cd.readthedocs.io/en/stable/operator-manual/health/)).
  "Healthy" 는 앱이 *사용자에게 잘 동작한다*는 뜻이 아니라 *쿠버네티스가 원하는 상태에 도달했다*는 뜻이다. 사용자 쪽 동작은 uptime-kuma 와 모니터링이 따로 본다.
- **사람이 매일 보지 않는다.** 노드 봇의 감시 스크립트가 클러스터 상태와 쿠버네티스 이벤트(파드 재시작 등)를 보고 텔레그램으로 알린다. 81개를 사람이 매일 열어 보는 건 불가능하다.

## 정리

| 질문 | 답 |
|---|---|
| 서비스 몇 개? | 운영 앱 24 / 배포 단위 81 / 파드 176 |
| 다 정상? | ArgoCD 81/81 Synced·Healthy, 비정상 파드 0 |
| 어디가 빠듯한가? | lemuel CPU 60%, ilwon 메모리 85% |
| 가장 무거운 무리는? | 앱이 아니라 감시·로그·보안·백업 |
| 다음에 볼 것 | ilwon 메모리(requests 와 실사용 차이), 지표·로그 백업 범위 |

"서비스가 몇 개냐"는 질문은 결국 **어디까지를 내가 책임지는 단위로 볼 것인가**의 질문이었다. 숫자를 하나만 말해야 한다면 81이다.
ArgoCD 앱 하나가 Git 의 디렉터리 하나이고, 그게 고치고 되돌리고 백업하는 단위이기 때문이다.

## References

- Kubernetes 공식 문서, *Deployments* — <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
- Kubernetes 공식 문서, *StatefulSets* — <https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/>
- Kubernetes 공식 문서, *DaemonSet* — <https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/>
- Kubernetes 공식 문서, *Resource Management for Pods and Containers* — <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>
- K3s 문서, *Volumes and Storage* — <https://docs.k3s.io/storage>
- Argo CD 문서, *Automated Sync Policy* — <https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/>
- Argo CD 문서, *Resource Health* — <https://argo-cd.readthedocs.io/en/stable/operator-manual/health/>
- Cloudflare 문서, *R2 pricing* — <https://developers.cloudflare.com/r2/pricing/>
