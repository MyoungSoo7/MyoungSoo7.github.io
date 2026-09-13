---
layout: post
title: "러너 한 대로는 왜 안 됐나 — 과금 차단에서 ARC 까지, 홈랩 CI 실측"
date: 2026-09-13 21:54:22 +0900
categories: [DevOps, Kubernetes]
tags: [GitHub Actions, Self-hosted Runner, ARC, Kubernetes, CI/CD, K3s]
---

자체 호스팅 러너 이야기는 보통 "왜 쓰면 좋은가" 로 시작한다. 우리 쪽은 그렇게 시작하지 않았다. **CI 가 죽어서** 시작했다.

이 글은 K3s 홈랩에서 GitHub Actions 러너가 *노드 위 systemd 프로세스 한 대* → *클러스터 안 ARC 스케일셋* 으로 옮겨간 기록이다. 설치 방법이 아니라 **왜 그게 필요했고, 옮기고 나서 무엇이 실제로 달라졌는지** 두 축으로만 쓴다. 숫자는 전부 자체 실측이고, 출처가 필요한 주장은 공식 문서를 달았다.

## 1. 등장 이유 — 비공개 리포에서는 분(minute)이 돈이다

GitHub 공식 문서의 문장이 이 글의 출발점이다.

> GitHub Actions usage is **free** for **self-hosted runners** and for **public repositories** that use standard GitHub-hosted runners. For **private repositories**, each GitHub account receives a quota of free minutes... Any usage beyond the included amounts is billed to your account.
>
> — [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

즉 축은 공개/비공개이지 개인/조직이 아니다. 두 리포가 여기에 걸렸다.

**`helm-deploy`** — 2026년 8월 13일부터 **잡이 시작조차 안 됐다.** 실패가 아니라 미시작이다. 워크플로는 멀쩡한데 빨간불도 안 들어오니, 모르고 보면 "CI 가 통과했다" 고 착각하기 딱 좋다. 이 리포의 커밋 기록에 그대로 남아 있다.

```
e907635 ci: chart-ci 를 일원 자체호스팅 러너로 이전 (과금 차단으로 2026-08-13부터 잡 미시작)
```

**`settlement`** — 이쪽은 차단이 아니라 비용 구조가 문제였다. 2026-09-12 오전에 최근 CI 런 6건을 재보니 **백엔드 테스트 잡 하나가 124분으로 전체 잡 시간의 8할**이었다(그다음이 GHCR 푸시 12분). 비공개 리포라 이 124분이 전부 유료다. 그래서 *무거운 것 하나만* 자체 호스팅으로 옮기고 나머지 잡은 `ubuntu-latest` 에 남겼다. 러너 노드가 죽어도 나머지 게이트는 계속 돌게 하려는 의도다.

여기서 공식 경고를 하나 같이 읽어둘 필요가 있다.

> We recommend that you only use self-hosted runners with private repositories. This is because forks of your public repository can potentially run dangerous code on your self-hosted runner machine.
>
> — [Adding self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners)

과금을 피하려고 자체 호스팅을 택하는 동기와, 보안상 자체 호스팅이 권장되는 대상이 **둘 다 비공개 리포** 라는 건 우연이 아니다. 공개 리포는 애초에 GitHub 호스팅이 무료라 옮길 이유가 없다.

## 2. 1차 해법과 그 대가 — 정적 러너 한 대

먼저 한 노드에 러너를 systemd 서비스로 붙였다. 지금도 `helm-deploy` 는 이렇게 돈다.

```
actions.runner.MyoungSoo7-helm-deploy.ilwon.service   active (running)
```

차트 렌더와 가드만 도는 가벼운 CI 라 이걸로 충분하다. 오늘 실행 기록을 보면 35~128초에 끝난다.

문제는 `settlement` 였다. 여기 백엔드 테스트는 6~7개 모듈 매트릭스에 Testcontainers 까지 붙는다. 정적 러너 1대에 올렸더니 대가가 두 가지 나왔고, 워크플로 주석에 그대로 적어뒀었다.

**① `max-parallel` 이 무의미해진다.** 러너가 1대니 매트릭스가 직렬로 돈다. "러너를 늘리면 되지 않나" 싶지만 그게 안 됐다. 서비스 컨테이너(postgres·elasticsearch)가 **5432·9200 을 호스트 포트로 고정 게시**하기 때문에, 같은 호스트에 잡을 두 개 올리면 포트가 부딪힌다. 한 대에서는 구조적으로 못 늘린다.

러너 저널이 이걸 있는 그대로 보여준다. `Running job` 다음에 반드시 `completed` 가 와야 다음 `Running job` 이 나온다.

```
15:08:20Z: Running job: Backend - Test (order-service)
15:18:25Z: Job Backend - Test (order-service) completed with result: Failed
15:18:33Z: Running job: Backend - Test (settlement-service)
```

**② 러너가 꺼져 있으면 잡은 실패가 아니라 대기한다.** PR 에서는 영원히 도는 것처럼 보이고 로그에 이유가 안 남는다. 이 대기에는 공식적으로 상한이 있다.

> After 24 hours the GitHub Actions Service unassigns the job if no runner accepts it.
>
> — [Actions Runner Controller](https://docs.github.com/en/actions/concepts/runners/actions-runner-controller)

즉 최악의 경우 하루를 버린 뒤에야 잡이 사라진다. CI 가 멈춰 보이면 코드가 아니라 러너부터 볼 것 — 이게 정적 러너 1대의 진짜 비용이었다.

## 3. 2차 해법 — 클러스터 안의 ARC

그래서 ARC(Actions Runner Controller)로 옮겼다. 잡마다 러너 **파드**가 뜨고 끝나면 사라지는 구조다. 컨트롤러와 리스너가 상주하고, 잡이 올 때만 러너가 생긴다.

지금 클러스터 상태는 이렇다.

```
arc-system   arc-gha-rs-controller-...        1/1 Running
arc-system   isagal-arc-c87c6449-listener     1/1 Running
arc-runners  autoscalingrunnerset/isagal-arc  min=0 max=3  현재 0
```

유휴일 때 러너가 0이라는 게 핵심이다. CI 가 안 돌면 메모리를 한 톨도 안 먹는다. 리스너 로그를 전수로 세어 보면 실제로 0↔3 사이를 오갔다.

```
544회  decision=0 currentRunnerCount=0     ← 유휴
114회  decision=3 currentRunnerCount=3     ← 3대까지 올라감
 34회  decision=2 currentRunnerCount=2
  3회  decision=1 currentRunnerCount=1
```

앞의 대가 ①이 여기서 사라진다. **파드마다 네트워크 네임스페이스가 따로**라 여러 잡이 같은 5432·9200 을 동시에 써도 부딪히지 않는다. 2026-09-12 19:22 스모크에서 finance 와 external-data 가 서로 다른 파드에서 실제로 겹쳐 돌았다. 대가 ②도 사라진다 — `minRunners=0` 이라 잡이 올 때 띄우고, 노드 후보가 둘이라 한 대가 죽어도 나머지가 받는다.

### 속도 델타 (2026-09-12 스모크, 캐시 예열 후)

| 모듈 | ARC |
|---|---|
| gateway-service | 16초 |
| external-data-service | 1분 27초 |
| operation-service | 1분 32초 |
| order-service | 5분 23초 |
| finance-service | 7분 20초 |
| settlement-service | 8분 |

정적 러너에서 order-service 가 약 10분이었으니 절반이다. 다만 이 숫자에는 조건이 붙는다 — **그래들·도커 이미지 캐시를 노드 hostPath 에 남겨서 나온 값**이고, 캐시를 지우면 콜드 빌드는 16~22분으로 돌아간다. 캐시 없는 ARC 는 정적 러너보다 오히려 느리다. 이건 ARC 의 공로가 아니라 캐시의 공로다.

## 4. 실제로 걸린 함정 여덟 개

설치 문서에 안 나오는, 직접 부딪혀서 알게 된 것들이다.

**① `isagal-arc` 는 노드 이름이 아니라 스케일셋 이름이다.** 이름 때문에 러너가 isagal 노드에서 돈다고 오해하기 쉬운데 아니다. 러너 파드는 david·ilwon 에 뜬다. 자체 호스팅 러너가 **라벨 배열**(`runs-on: [self-hosted, isagal]`)로 지정되는 것과 달리, 스케일셋은 **이름 하나**(`runs-on: isagal-arc`)로 지정한다. 문법이 비슷해서 더 헷갈린다.

**② ArgoCD 로 배포하면 `controllerServiceAccount` 를 명시해야 한다.** 이 차트는 기본적으로 *살아 있는 클러스터를 조회해서* 컨트롤러의 ServiceAccount 를 찾는다. 그런데 ArgoCD 는 `helm template` 으로 렌더링하므로 조회가 안 된다. 안 적으면 렌더 단계에서 죽는다.

```
No gha-rs-controller deployment found using label
(app.kubernetes.io/part-of=gha-rs-controller)
```

로컬 `helm template` 로 그대로 재현된다. ArgoCD 를 쓰는 쪽이라면 거의 확실히 밟는다.

**③ dind 사이드카에 리소스를 덧댈 수가 없다.** 서비스 컨테이너와 Testcontainers 는 러너가 아니라 **dind 데몬이 띄우므로 dind 컨테이너의 cgroup 에 잡힌다.** 그래서 dind 에 메모리를 줘야 하는데, `containerMode.type: dind` 로 자동 주입된 컨테이너에는 값을 덧댈 방법이 없었다. values 에 같은 이름으로 적으면 차트가 병합하지 않고 **뒤에 덧붙여서** 이름이 겹친 컨테이너가 2개 되고, 그 파드 스펙은 API 서버가 거부한다. **렌더는 통과한다** — 이게 고약한 지점이다. 결국 dind 모드의 렌더 출력을 그대로 베껴 적고 리소스만 더했다(렌더 차분으로 한 글자도 다르지 않음을 확인).

참고로 이 dind 는 k8s 네이티브 사이드카로 들어간다. `initContainers` 에 `restartPolicy: Always` 를 준 형태다 — [쿠버네티스 공식 문서](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/) 기준 v1.28 에 처음 들어와 **v1.29부터 기본 활성**, v1.33에서 stable 이다. 클러스터는 v1.35 라 그냥 쓴다.

**④ 로케일을 안 잡아주면 한글 클래스명이 *컴파일* 에서 죽는다.** 러너 이미지를 맨몸으로 띄우면 `LC_CTYPE="POSIX"`, 즉 ASCII 다. `ubuntu-latest` 러너는 `LANG=C.UTF-8` 로 온다. 이 차이로 이런 게 터졌다.

```
error: error while writing ChargebackServiceTest.Open_멱등:
bad filename RelativeFile[...ChargebackServiceTest$Open_멱등.class]
```

테스트 실패가 아니라 **컴파일 실패**다. javac 가 클래스 파일의 *이름* 을 파일시스템 인코딩으로 적어야 하는데 ASCII 로는 못 적는다. 한글로 중첩 테스트 클래스명을 쓰는 코드베이스라면 `LANG`·`LC_ALL` 을 `C.UTF-8` 로 박아야 한다.

**⑤ hostPath 캐시는 소유자가 안 맞는다.** hostPath 는 `root:root 0755` 로 생기는데 러너는 uid 1001 로 돈다. 그대로 두면 그래들이 `~/.gradle` 에 쓰지를 못해 빌드가 아예 안 돈다. `chown 1001:1001` 하는 init 컨테이너를 목록 맨 앞에 둬서 dind 보다 먼저 돌게 했다.

**⑥ 리스너를 아무 노드에나 두면 안 된다.** 리스너는 GitHub 에 long-poll 만 하는 작은 상주 파드라 아무 데나 둬도 될 것 같지만, 무선 노드에 떨어지면 **58MB 이미지를 받는 데 10분이 넘고** 그동안 `ContainerCreating` 에 머문다. 리스너가 안 뜨면 러너도 0에서 안 올라간다. 그래서 유선 노드에만 붙였다.

**⑦ 노드당 러너 1개로 잠근 이유는 포트가 아니라 메모리다.** 잡이 도는 중에 RSS 를 재보니 테스트 포크 JVM 1654Mi + 638Mi, 그래들 JVM 1438Mi — 합계 약 3.7Gi 였다. 한 노드에 둘이 뜨면 포트가 아니라 메모리가 먼저 터진다. `podAntiAffinity` 를 hard 로 걸었다.

**⑧ 그래서 `maxRunners: 3` 은 사실상 2다.** 후보 노드가 둘인데 노드당 1개로 잠갔으니 동시에 *Running* 이 될 수 있는 건 2개다. 세 번째는 Pending 으로 남는다. 스케일셋 설정과 스케줄링 제약이 각각 따로 말이 되면서 합쳐서는 안 맞는 전형적인 경우다. 그래도 직렬 1대보다는 낫다.

## 5. 지금 상태 — 정직하게

과장하지 않기 위해 현재 위치를 정확히 적는다.

- **`helm-deploy`** — 노드 위 정적 러너로 돈다. 오늘도 잘 돌고 있다(35~128초).
- **`settlement`** — 무거운 백엔드 테스트가 ARC 로 간다. 실제로 최근 런에서 6개 모듈이 `isagal-arc` 러너 파드에 배정됐고, 나머지 한 모듈과 다른 잡들은 `ubuntu-latest` 에 남아 있다.
- **다만 이 변경은 아직 `main` 에 없다.** 기본 브랜치의 워크플로는 전부 `ubuntu-latest` 이고, ARC 로 가는 설정은 PR 브랜치에서 돌고 있다. 머지 전이다.

즉 "ARC 로 이전을 마쳤다" 가 아니라 "이전 중이고 PR 에서 실측 중" 이 맞는 표현이다.

## 6. 남는 교훈

**과금 차단은 빨간불로 오지 않는다.** 잡이 아예 시작을 안 하므로 워크플로 목록이 조용하다. 2026-08-13 이후 `helm-deploy` 가 그랬다. CI 가 초록이라서가 아니라 *아무것도 안 돌아서* 조용한 것과 구분이 안 된다.

**"러너를 늘리면 되지" 가 안 되는 이유는 대개 호스트 자원의 유일성이다.** 포트든 파일 락이든 캐시 디렉터리든, 한 호스트에 하나뿐인 것을 잡 두 개가 동시에 요구하면 병렬화가 막힌다. 컨테이너로 격리하면 풀리는데, 이게 ARC 를 쓰는 실질적 이유였다 — 오토스케일링보다 **네임스페이스 분리**가 먼저였다.

**캐시를 빼고 속도를 자랑하면 안 된다.** 위 표의 절반짜리 숫자는 캐시가 만든 것이고, 캐시를 지우면 16~22분으로 돌아간다. 러너를 바꿔서 빨라진 부분과 캐시를 붙여서 빨라진 부분은 따로 세야 한다.

## References

- [GitHub Actions billing — GitHub Docs](https://docs.github.com/en/billing/concepts/product-billing/github-actions) — 자체 호스팅 러너·공개 리포는 무료, 비공개 리포는 할당량 초과 시 과금
- [Adding self-hosted runners — GitHub Docs](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners) — 자체 호스팅 러너는 비공개 리포에만 권장(포크 PR 의 임의 코드 실행 위험)
- [Actions Runner Controller — GitHub Docs](https://docs.github.com/en/actions/concepts/runners/actions-runner-controller) — 스케일셋 동작 순서, 24시간 후 잡 unassign
- [Sidecar Containers — Kubernetes Documentation](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/) — `initContainers` + `restartPolicy: Always`, v1.28 도입 / v1.29 기본 활성 / v1.33 stable

본문의 소요 시간·메모리·러너 동작 수치는 모두 자체 홈랩(K3s v1.35, ARC 차트 0.14.2)에서 측정한 값이며 일반적인 벤치마크가 아니다. 하드웨어·네트워크·캐시 상태에 따라 크게 달라진다.
