---
layout: post
title: "지금 르무엘·루이스·일원은 각자 무슨 일을 하나 — 22시 43분 스냅샷"
date: 2026-10-27 22:44:52 +0900
categories: [devops, kubernetes]
tags: [k3s, homelab, node-roles, github-actions, self-hosted-runner, elasticsearch, kafka, argocd]
---

오늘 [etcd 를 1대로 줄이고 안 쓰는 서비스를 내린 뒤](/2026/10/27/homelab-slimming-day-etcd-plane-opik/), 클러스터 노드 세 대(lemuel·louise·ilwon)가 **지금 이 순간 무엇을 하고 있는지** 실측했다. 기준 시각은 2026-10-27 22:43 KST 다. 수치는 `kubectl top`, `kubectl get pods --field-selector spec.nodeName=…`, 각 노드에 SSH 로 들어가 본 `ps`·`free`·`docker ps`·`systemctl` 결과다. 한 번 찍은 스냅샷이라 평균값이 아니다.

## 한눈에

| | ilwon | lemuel | louise |
|---|---|---|---|
| K3s 역할 | **server** (control-plane + etcd) | agent | agent |
| 실행 중 파드 | 22 | 26 | 35 |
| CPU (kubectl top) | 812m, 7% | 1655m, 55% | 4725m, 67% |
| 메모리 (kubectl top) | 18.2GiB, 65% | 9.1GiB, 31% | 7.9GiB, 64% |
| load avg (1/5/15분) | 0.41 / 0.80 / 0.93 | 2.48 / 3.13 / 4.25 | 5.70 / 6.05 / 6.33 |
| 루트 디스크 | 86G / 457G (20%) | 159G / 394G (43%) | 267G / 466G (60%) |
| 호스트 도커 | 0개 | 0개 | 5개 (CI 테스트 3 + 샌드박스 2) |
| GitHub Actions 러너 | helm-deploy | — | settlement, watchman-agent |
| 한 줄 요약 | **기록 보관소** — 상태·로그·지표·이벤트 | **정산 서비스 본체** | **배포 지휘소 + CI 빌드 공장** |

세 대의 성격이 꽤 분명하게 갈렸다. ilwon 은 메모리를 많이 쓰지만 CPU 는 한가하다. lemuel 은 사용자 요청을 처리한다. louise 는 클러스터를 관리하고 코드를 빌드한다.

## ilwon — 모든 기록이 모이는 곳

K3s 공식 문서는 server 를 "`k3s server` 를 실행하고 control-plane 과 데이터스토어를 가진 호스트", agent 를 "그 둘이 없는 호스트"로 정의한다 ([K3s — Architecture](https://docs.k3s.io/architecture)). 오늘부터 이 클러스터의 server 는 ilwon 한 대다. 호스트에서 가장 무거운 프로세스 목록을 보면 이 노드의 역할이 그대로 보인다.

| 프로세스 (RSS 순) | RSS | 정체 |
|---|---|---|
| Elasticsearch (`logs-es-hot-0`) | 5.2GiB | 클러스터 로그의 hot 티어 |
| Logstash (`logs-ls-0`) | 3.3GiB | 로그 수집 파이프라인 |
| `k3s server` | 1.9GiB | API 서버 + etcd (클러스터 상태 전체) |
| Prometheus | 1.8GiB | 지표 저장 |
| Elasticsearch (`settlement-elasticsearch-0`) | 1.2GiB | settlement 검색 인덱스 |
| Kafka (`lemuel-dual-role-0`) | 1.0GiB | settlement 이벤트 백본 (Strimzi) |

여기에 settlement DB 인 `jen-postgres-0`, `database-mysql-0`, Alertmanager·Grafana 도 ilwon 에 있다. 정리하면 이렇다.

- **클러스터 상태**: etcd
- **업무 데이터**: Postgres·MySQL·Kafka
- **관측 데이터**: 로그·지표·알림

이 세 가지가 전부 ilwon 의 NVMe 에 있다. 반면 CPU 는 7%, load 는 0.41 이다. 계산할 일은 거의 없고 받아 적는 일만 하는 노드다.

메모리 65% 의 대부분은 ES 와 Logstash 몫이다. Kafka 도 `kubectl top` 으로는 174m CPU, 1GiB 정도다. 이 노드가 메모리 때문에 위험해진다면, 원인은 업무 서비스가 아니라 **로깅 스택**일 가능성이 높다.

이 구성의 비용도 분명하다. 오늘 etcd 를 1대로 줄이면서 ilwon 이 단일 장애점이 됐다. 위 표의 데이터가 모두 같은 디스크에 있으니, ilwon 디스크를 잃으면 클러스터 상태와 업무 DB 와 로그를 한꺼번에 잃는다. etcd 스냅샷만 맥으로 복사하게 해 둔 상태다. DB 는 velero 백업에 의존한다.

ilwon 에는 helm-deploy 리포용 Actions 러너도 하나 떠 있다. 차트를 렌더하고 검증하는 잡이라 가볍다.

## lemuel — 정산 서비스가 실제로 도는 곳

lemuel 의 파드 26개 중 7개가 `settlement-prod` 다.

- settlement 본체
- settlement-app
- finance
- operation
- external-data
- market-stream
- frontend

`kubectl top` 기준으로 CPU 를 가장 많이 쓰는 파드도 settlement-finance(296m)·query(128m)·operation(103m) 순이었다. 호스트 `ps` 에서도 메모리 상위 6개 프로세스 가운데 5개가 이 서비스들의 JVM(각 0.5~0.7GiB)이었다.

나머지는 워크플로 자동화 n8n, 보안 에이전트 watchman·sentinel, analytics 의 Postgres, ECK·sops 오퍼레이터 같은 클러스터 부속품이다. 오늘 오후까지 이 노드에 붙어 있던 호스트 도커(opik 8개 + qdrant)는 모두 내렸다. 그래서 이제 lemuel 의 일은 **쿠버네티스 파드만으로 설명된다.**

다만 CPU 는 파드 합계(약 0.86코어)보다 노드 전체(1.66코어)가 거의 두 배였다. 차이의 일부는 호스트 상주 프로그램이다.

- netdata (14%)
- falco (14%)
- k3s-agent (14%)
- Suricata (IDS, 0.5GiB)

측정하던 순간에는 `fail2ban-client status …` 가 순간적으로 175% 를 찍기도 했다. 몇 초 뒤 다시 보니 14% 였고, jail 별로 상태를 조회하는 짧은 호출이 연달아 뜨는 모양이었다. 무엇이 그 호출을 내는지는 이번에 확인하지 못했다.

## louise — 배포를 지휘하고, 코드를 빌드하는 곳

louise 의 파드 35개는 두 덩어리로 나뉜다.

**하나는 클러스터 운영 도구다.**

- ArgoCD 8개(application-controller 265m 로 louise 파드 중 CPU 1위, repo-server, image-updater…)
- velero
- cloudflared 커넥터
- uptime-kuma
- 텔레그램 봇 하트비트
- Actions Runner Controller(arc-system)

git 의 상태를 클러스터에 맞추고, 외부 트래픽을 들여오고, 백업을 찍는 일이 여기서 일어난다. 업무 서비스는 receipt-ocr·codingtest·database-app 처럼 작은 것들뿐이다.

**다른 하나는 쿠버네티스 밖에 있다.** louise 의 CPU 4.7코어 중 파드 몫은 약 0.6코어였다. 나머지는 호스트에 직접 설치된 GitHub Actions 셀프호스티드 러너 두 개(settlement, watchman-agent)가 썼다.

측정 시점에 settlement 러너는 Gradle 테스트 JVM 2개를 돌리고 있었다(CPU 311%·77%, 각각 0.8~1GiB). 테스트용으로 띄운 컨테이너도 3개 있었다.

- Testcontainers postgres:17 (5분째)
- postgres:17-alpine (7초째)
- Elasticsearch 8.11 (5분째)

GitHub 공식 문서는 셀프호스티드 러너를 "GitHub Actions 사용은 무료지만, 러너 머신 유지 비용은 사용자 책임"이라고 설명한다 ([GitHub Docs — Self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners)). louise 의 load 6 이 바로 그 "유지 비용"이다.

오늘 저녁 상황이 이것을 잘 보여 준다. GitHub 호스티드 러너의 월 무료 분이 소진되자, 봇3 가 settlement CI 의 가벼운 잡 8개를 louise 로 옮기는 PR #395 를 머지했다. 22:43 기준 settlement 리포의 Actions 에는 #395 머지 후 develop 에서 돈 `ci` run 과 그 브랜치의 `ci` run 이 **`queued`** 로 남아 있었다. louise 의 settlement 러너가 다른 잡을 처리하는 동안 차례를 기다리는 것으로 보인다. 분은 안 쓰게 됐지만, 그 대신 **기다리는 시간**이 생겼다.

샌드박스 컨테이너 2개(`openshell-…watchman`)는 4주째 떠 있는 watchman 에이전트의 격리 실행 환경이다.

## 이 스냅샷에서 읽히는 것

1. **"노드 부하 = 파드 부하"가 아니다.** louise 는 CPU 의 약 87%, lemuel 은 약 48% 를 파드가 아닌 프로세스가 썼다. 쿠버네티스 대시보드만 보면 louise 는 한가한 노드로 보인다.
2. **기록은 ilwon 에, 계산은 lemuel 에, 지휘와 빌드는 louise 에** 모여 있다. 의도해서 이렇게 나눈 건 아니다. 로컬 볼륨 위치, 노드 퇴역(isagal·david), 오늘의 etcd 축소가 쌓여서 이렇게 됐다.
3. **CI 를 louise 로 옮긴 비용은 louise 가 낸다.** ArgoCD 컨트롤러와 같은 호스트에서 테스트 JVM 이 3코어를 쓴다. 빌드가 몰리는 시간에는 배포 동기화가 느려질 수 있다. 아직 확인한 사례는 없고, 다음에 지켜볼 지점이다.

참고로, 측정 범위 밖의 네 번째 노드 solomon 은 22:35 에 cordon 됐고 22:38 부터 NotReady(ping·SSH 무응답) 상태였다. 그래서 이 글에서는 다루지 않았다.

## References

- K3s Documentation — [Architecture: Servers and Agents](https://docs.k3s.io/architecture)
- K3s Documentation — [High Availability Embedded etcd](https://docs.k3s.io/datastore/ha-embedded)
- GitHub Docs — [Self-hosted runners](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners) (무료 사용, 머신 유지 비용은 사용자 부담)
- GitHub Docs — [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- Kubernetes Documentation — [Resource metrics pipeline (`kubectl top`)](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)
- 같은 날 글 — [홈랩 다이어트 하루 — etcd 3→1, 서비스 정지, Actions 분 소진까지](/2026/10/27/homelab-slimming-day-etcd-plane-opik/)
