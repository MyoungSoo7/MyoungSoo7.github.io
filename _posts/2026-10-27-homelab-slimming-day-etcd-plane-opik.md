---
layout: post
title: "홈랩 다이어트 하루 — etcd 3→1, plane·media-search·opik 정지, 디스크 51GB 회수"
date: 2026-10-27 22:40:00 +0900
categories: [devops, kubernetes]
tags: [k3s, etcd, argocd, server-side-diff, testcontainers, docker, opik, homelab]
---

2026-10-27 하루 동안 K3s 홈랩에서 덜어낸 것들을 적는다. 어제 [3멤버 vs 1멤버 etcd 비교 글](/2026/10/26/k3s-etcd-3-vs-1-member-ops-physical/)에서 내린 결론을 오늘 실제로 실행했다. 그 김에 "지금 안 쓰는데 돌고 있는 것"을 하나씩 찾아 내렸다. 숫자는 전부 이날 `kubectl`·`docker`로 직접 잰 값이다.

## 요약

| 작업 | 전 | 후 |
|---|---|---|
| etcd 멤버 | 3 (lemuel·ilwon·solomon) | 1 (ilwon), 나머지는 agent |
| plane-prod (이슈관리) | 워크로드 11개 | 0개, PVC 4개 보존 |
| media-search-prod | 1 | 0 |
| lemuel 호스트 도커 (opik 8 + qdrant 1) | 9개, 약 2.7GB | 0개 |
| lemuel 디스크 | 210G (56%) | 159G (43%) |
| louise 찌꺼기 테스트 컨테이너 | 3개 (8~9일 방치) | 0개 |

## 1. etcd 3 → 1

K3s 공식 문서에 따르면 내장 etcd HA 의 쿼럼은 `(n/2)+1` 이다. 그래서 짝수 대를 두면 오히려 손해다 ([K3s docs — HA Embedded etcd](https://docs.k3s.io/datastore/ha-embedded)). 우리 클러스터는 3멤버 중 2대(lemuel 유선, solomon 무선)가 불안정했다. 그러면 3멤버는 고가용성이 아니라 장애 지점이 셋인 구조가 된다. 어제 글의 결론이 이것이었고, 오늘 실행했다.

순서는 이렇다.

1. 노드에 `etcd.k3s.cattle.io/remove=true` 애노테이션을 달아 멤버를 제거한다.
2. 그 노드의 `k3s` server 서비스를 멈추고 비활성화한다.
3. server 전용 설정 drop-in 과 `/var/lib/rancher/k3s/server` 를 지우지 않고 `/root/k3s-server-retired-*` 로 옮겨 둔다.
4. `K3S_URL=https://<ilwon>:6443` 로 `k3s-agent` 를 켠다.

결과는 멤버 1, 노드 4/4 Ready, 파드 재시작 0, ArgoCD 앱 69/69 정상이었다.

대신 생긴 비용이 있다. **ilwon 디스크가 곧 클러스터 상태의 전부가 됐다.** K3s 는 기본으로 하루 두 번(00:00·12:00) 스냅샷을 찍고 노드 로컬 디스크에 5개를 보관한다 ([K3s docs — etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot)). 로컬 사본만으로는 ilwon 디스크가 죽는 경우를 못 막는다. 그래서 맥 LaunchAgent 가 스냅샷 직후(00:40·12:40) 최신 스냅샷을 끌어와 sha256 을 검증하고 14개를 보관하게 했다. 터널, 워치독, node-self-healer, wifi-probe 처럼 옛 server IP 를 바라보던 곳도 전부 ilwon 하나로 바꿨다.

## 2. plane-prod 내리기 — 0 을 넣으면 1 이 되는 차트

plane-ce 차트 템플릿은 `replicas: {{ .Values.X.replicas | default 1 }}` 형태다. Helm 의 `default` 는 0 을 "비어 있음"으로 보기 때문에, values 에 0 을 넣어도 1 이 렌더된다. StatefulSet 4개(pgdb·redis·rabbitmq·minio)는 replicas 값을 받는 자리조차 없었다.

차트를 포크하지 않고 이렇게 우회했다.

- Application 에 `/spec/replicas` 를 `ignoreDifferences` 로 걸었다.
- `RespectIgnoreDifferences=true` 를 줘서 sync 할 때도 그 필드를 덮어쓰지 않게 했다 ([Argo CD — Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/)).
- 그다음 `kubectl scale --replicas=0` 으로 내렸다.

두 번째 함정이 있었다. 이 클러스터는 Argo CD 의 **Server-Side Diff** 를 전역으로 켜 두었다. Server-Side Diff 는 리소스마다 Server-Side Apply 를 dry-run 으로 실행해서 diff 를 만든다 ([Argo CD — Diff Strategies](https://argo-cd.readthedocs.io/en/stable/user-guide/diff-strategies/)). 그런데 plane 에는 이미 완료된 마이그레이션 Job(`plane-api-migrate-1`)이 있다. Job 의 pod template 은 바꿀 수 없는 필드다. dry-run 이 `field is immutable` 로 거부되자 앱 전체가 `ComparisonError` 와 `Unknown` 상태에 빠졌다. 이 앱 하나에만 `argocd.argoproj.io/compare-options: ServerSideDiff=false` 를 달아 레거시 diff 로 돌려서 풀었다.

결과는 이렇다.

- 11개 워크로드가 모두 0 이 됐다.
- PVC 4개는 그대로 Bound 상태라 이슈 데이터는 남아 있다.
- 되살릴 때는 `kubectl -n plane-prod scale deploy,sts --all --replicas=1` 한 줄이면 된다.

같은 날 homelab-dashboard 에서도 "바꿀 수 없는 필드" 때문에 막혔다. 이쪽은 PVC 였다. 이미 바인딩된 PVC 의 `volumeName`·`storageClassName` 을 차트가 렌더하지 않아서 dry-run 이 거부됐다. 차트에 `persistence.volumeName` 을 추가해 해결했다. 대시보드는 replicas 0 으로 멈춰 둔 상태다.

## 3. 노드를 하나 뺄 수 있나 — 숫자로 보면

4대(lemuel·louise·ilwon·solomon)의 실사용률과 요청량을 비교했다.

| 노드 | CPU 실사용 | 메모리 실사용 | 메모리 요청량 | 로컬 PV |
|---|---|---|---|---|
| ilwon | 7% | 73% | 77% | 17 |
| lemuel | 62% | 37% | 17% | 8 |
| louise | 110% | 79% | 82% | 10 |
| solomon | 10% | 21% | 40% | 10 |

- **ilwon** 은 이제 유일한 server 라서 뺄 수 없다.
- **louise** 는 제일 바쁘다.
- **solomon** 이 제일 한가하다. 하지만 로컬 볼륨 10개가 묶여 있고, IoT 연구용 무선 노드라는 역할이 있다.
- **lemuel** 은 analytics·plane 이 빠지면 묶인 볼륨이 n8n·watchman 감사로그 정도만 남는다. 다만 그 경우 나머지 3대의 메모리 요청량이 약 81% 까지 올라가 빠듯하다.

결론은 당장은 4대 유지였다. 그래도 이 표를 만들면서 쿠버네티스 지표에 안 잡히는 부하 두 가지를 발견했다.

### 3-1. louise 110% 의 정체 — 파드가 아니었다

`kubectl top pods` 로 보면 가장 무거운 파드도 0.3코어였다. 원인은 호스트에 직접 설치된 **GitHub Actions 셀프호스티드 러너**(settlement 용, watchman-agent 용)였다. settlement CI 테스트가 돌면서 Gradle 테스트 JVM 이 각각 250%·240% CPU 를 쓰고 있었고, load 는 10.4 였다. isagal 퇴역 뒤 러너가 louise 로 옮겨 온 결과다. 서비스 부하가 아니라 빌드가 돌 때만 오르는 부하다.

옆에는 Testcontainers 가 띄운 postgres 컨테이너 3개가 **8~9일째** 떠 있었다(`org.testcontainers=true` 라벨, 10/17·10/19 생성). 셋 다 5432 포트를 `0.0.0.0` 에 열어 둔 상태였다. Testcontainers 는 원래 Ryuk 라는 리퍼 컨테이너가 테스트가 끝나면 컨테이너를 치운다. Ryuk 는 `TESTCONTAINERS_RYUK_DISABLED` 로 끌 수 있다 ([Testcontainers — Container runtime requirements](https://java.testcontainers.org/supported_docker_environment/)). 이번 세 개가 왜 안 치워졌는지(Ryuk 비활성인지, 잡이 강제 종료됐는지)는 **확인하지 못했다.** 라벨과 생성 시각을 확인한 뒤 지웠다. 지금 돌고 있는 CI 컨테이너는 건드리지 않았다.

### 3-2. lemuel — 쿠버네티스 밖의 도커 9개

lemuel 의 CPU 62% 중 파드 몫은 0.6코어 정도였다. 나머지는 호스트 docker compose 로 띄운 것들이었다.

- **opik** 8컨테이너: Comet ML 의 오픈소스 LLM 관측 플랫폼이다. clickhouse·mysql·minio·redis·zookeeper 를 포함하고, memory-qa 의 Gemini 호출을 trace 로 기록하던 용도다.
- **qdrant** 1컨테이너: RAG 실습용 벡터 DB 다.

실사용을 재 보니 이랬다.

- opik 은 8/12 연동 이후 trace 가 **누적 33건**이었고, 마지막 기록은 10/25 였다.
- qdrant 는 컬렉션 1개에 **벡터 2개**뿐이었다.

질문 33번을 기록하려고 DB 5종을 상시 돌린 셈이다. 사용자가 "GPU 로 LLM 안 돌리면 필요 없지?" 하고 물었는데, 결론은 맞지만 이유는 다르다. opik 은 API 형 LLM(Gemini 등)도 관측하는 도구라 GPU 와는 상관이 없다. 접은 이유는 **사용량**이다.

정지는 이렇게 했다.

- 컨테이너를 `docker stop` 으로 멈췄다. 재시작 정책이 `unless-stopped` 라 재부팅해도 다시 뜨지 않는다. 데이터와 compose 파일은 남겼다.
- memory-qa 는 `OPIK_BASE=""` 로 바꿔 트레이싱을 껐다.
  - memory-qa 는 처음부터 "관측이 관측 대상을 죽이지 않게" 설계돼 있다. 백엔드가 비어 있으면 트레이서가 통째로 꺼지고, 백엔드가 느리면 기다리지 않고 drop 한다. 그래서 이 전환은 위험이 없었다.
  - 교체 후 `/health` 는 `opik.enabled=False` 를 보였다.

같은 노드의 안 쓰는 이미지(10.2GB)와 빌드 캐시(37.5GB)는 `docker image prune -a`, `docker builder prune -a` 로 지웠다 ([Docker docs — builder prune](https://docs.docker.com/reference/cli/docker/builder/prune/)). 디스크는 210G 에서 159G 로 줄었다. 멈춰 있는 컨테이너 22개와 볼륨 38개(42GB)는 데이터가 있을 수 있어 남겨 두었다.

## 4. 오늘 배운 것

1. **"바꿀 수 없는 필드"는 Server-Side Diff 를 앱 단위로 마비시킨다.** 완료된 Job 의 template 이나 바인딩된 PVC 의 volumeName 처럼 실제로 바꿀 게 없는 리소스여도, dry-run 이 거부되면 앱 상태 자체가 Unknown 이 된다. 해법은 차트가 실제 값을 렌더하게 고치거나(PVC), 그 앱만 레거시 diff 로 돌리는 것이다(Job).
2. **Helm `default` 는 0 을 삼킨다.** replicas 를 0 으로 내리려면 차트가 그걸 허용하는지부터 봐야 한다.
3. **노드 부하표는 `kubectl top` 만으로 못 그린다.** louise 의 CI 러너와 lemuel 의 compose 스택은 쿠버네티스 지표에 나오지 않았다. 노드를 뺄지 판단할 때는 `docker ps` 와 `ps --sort=-pcpu` 를 함께 봐야 한다.
4. **"설치해 둔 관측 도구"도 사용량으로 다시 평가한다.** opik 은 고장이 아니라 쓰임이 적어서 접었다. 다시 쓸 시점은 LLM 을 붙인 서비스가 여럿이 되어 비용·지연을 비교해야 할 때다.

## References

- K3s Documentation — [High Availability Embedded etcd](https://docs.k3s.io/datastore/ha-embedded) (쿼럼 `(n/2)+1`, 홀수 server)
- K3s Documentation — [etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot) (기본 00:00·12:00, 로컬 5개 보관)
- Argo CD Documentation — [Diff Strategies](https://argo-cd.readthedocs.io/en/stable/user-guide/diff-strategies/) (Server-Side Diff = SSA dry-run)
- Argo CD Documentation — [Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/) (`RespectIgnoreDifferences`)
- Kubernetes Documentation — [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- Testcontainers for Java — [General Container runtime requirements](https://java.testcontainers.org/supported_docker_environment/) (Ryuk, `TESTCONTAINERS_RYUK_DISABLED`)
- Docker Documentation — [docker builder prune](https://docs.docker.com/reference/cli/docker/builder/prune/)
- 이전 글 — [K3s etcd 3멤버 vs 1멤버, 운영·물리 구조로 본 차이](/2026/10/26/k3s-etcd-3-vs-1-member-ops-physical/)
