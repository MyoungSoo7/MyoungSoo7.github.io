---
layout: post
title: "러너 업그레이드가 고쳐 온 것들 — 깃랩과 깃헙은 반대편에서 출발해 같은 답에 도착했다"
date: 2026-09-15 23:36:01 +0900
categories: [DevOps, CI/CD]
tags: [GitLab Runner, GitHub Actions, ARC, Autoscaling, Kubernetes, Self-hosted Runner, 보안]
---

CI 러너는 조용히 바뀐다. 파이프라인 YAML 은 3년 전 그대로인데, 그 밑에서 도는 러너는 세 번쯤 구조가 갈렸다. 이 글은 **깃랩 러너와 깃헙 액션 러너가 각자의 업그레이드에서 무엇을 고쳐 왔는지**를 1차 출처만으로 맞대어 본 것이다.

먼저 결론부터. 두 제품은 **반대편에서 출발했다.** 깃랩은 러너가 클라우드 VM 까지 직접 띄우는 "인프라 프로비저너" 쪽에서, 깃헙은 러너가 그냥 등록해 놓고 기다리는 "워커 프로세스" 쪽에서 시작했다. 그런데 업그레이드를 몇 번 거친 지금, 둘은 **같은 세 가지 답**에 도착해 있다 — ① 일회용 러너를 기본으로, ② 공유 토큰을 폐기하고 인스턴스 단위 신원으로, ③ 스케일링 판단을 추측이 아니라 실제 큐 신호로.

각자 어떤 경로로 거기 왔는지가 이 글의 본론이다.

이 블로그에 이미 있는 [깃헙과 깃랩, 결국 러너가 어디서 도느냐의 문제]({% post_url 2026-09-10-github-vs-gitlab-where-the-runner-lives %}) 는 *어디에* 러너를 둘지를, [러너 한 대로는 왜 안 됐나]({% post_url 2026-09-13-static-runner-to-arc-what-changed %}) 는 홈랩 실측을 다뤘다. 이 글은 겹치지 않는 축 하나만 본다 — **시간축. 버전이 올라가면서 무엇이 실제로 고쳐졌나.**

---

## 1. 깃랩: 죽은 의존성을 걷어내는 데 4년이 걸렸다

깃랩 러너의 오토스케일은 오랫동안 **Docker Machine executor** 였다. 문제는 이게 깃랩 것이 아니라는 데 있었다. Docker 가 업스트림 Docker Machine 을 사장(deprecate)시키자 깃랩은 자체 포크를 떠안았고, 결국 이렇게 정리했다.[^gldm]

> Docker Machine 은 GitLab 17.5 에서 deprecated 되었고 **GitLab 20.0 (2027년 5월) 에 제거**될 예정이다.

Docker Machine 이 실제로 무엇이 나빴는지는 문서가 아주 구체적으로 적어 뒀다. 스케일링 모델 자체가 경직돼 있었다.[^gldm]

> Docker Machine 오토스케일러는 **`limit` 과 `concurrent` 설정과 무관하게 VM 하나당 컨테이너 하나**를 만든다.

이 한 줄이 왜 아픈지는 수식으로 보면 분명하다. 깃랩 러너의 동시성은 전역 `concurrent` 와 각 `[[runners]]` 워커의 `limit` 으로 정해진다.[^gladv]

$$N_{\max} \;=\; \min\!\Bigl(\texttt{concurrent},\ \sum_{i} \texttt{limit}_i\Bigr)$$

그런데 Docker Machine 에서는 이 값이 곧 **VM 개수**였다. 작업 20개를 동시에 돌리려면 VM 20대를 띄워야 했다. VM 한 대에 4개씩 태우고 싶어도 방법이 없었다. 부팅 시간도 VM 20대분이었다.

### 대체제 — fleeting 플러그인

깃랩이 내놓은 답은 **GitLab Runner Autoscaler** 다. Instance executor 와 Docker Autoscaler executor 두 갈래로 나뉘고, 그 밑에 **fleeting** 이라는 플러그인 계층이 깔린다.[^glautoscaler][^gldocker] fleeting 은 AWS·GCP·Azure 의 인스턴스 그룹 API 를 하나의 인터페이스로 추상화하는 층이다. 즉 깃랩은 "죽은 서드파티 도구를 포크해서 끌고 가는" 구조를, **"클라우드별 플러그인을 우리가 정의한 인터페이스에 맞춰 붙이는"** 구조로 바꿨다.

설치 경험도 이때 같이 고쳐졌다. **GitLab Runner 16.11 이후**로는 플러그인을 손으로 받아 경로를 맞출 필요가 없다.[^gldocker]

```bash
gitlab-runner fleeting install
```

그 전 버전에서는 `fleeting-plugin-aws` 같은 이름을 직접 적어 설치해야 했다. 작은 변화 같지만, 러너 매니저를 여러 대 굴리는 팀에서는 프로비저닝 스크립트가 통째로 줄어드는 차이다.

### 그리고 여기서 "일회용" 이 설정 두 줄이 됐다

Docker Autoscaler 문서가 보안 기본값으로 제시하는 조합은 이렇다.[^gldocker]

```toml
[runners.autoscaler]
  capacity_per_instance = 1
  max_use_count = 1
```

> 각 작업에 **다른 작업의 영향을 받을 수 없는 안전한 일회용 인스턴스**가 주어지고, 작업이 끝나면 **즉시 삭제**된다.

인스턴스 수는 이렇게 결정된다.

$$N_{\text{instances}} \;=\; \left\lceil \frac{N_{\text{jobs}}}{\texttt{capacity\_per\_instance}} \right\rceil$$

`capacity_per_instance = 1` 이면 Docker Machine 시절과 숫자가 같아진다. 차이는 **그게 강제가 아니라 선택**이 됐다는 것이다. 신뢰할 수 있는 내부 코드만 도는 러너라면 `capacity_per_instance` 를 올려 VM 한 대에 여러 작업을 태우고, 포크 MR 을 받는 러너는 1로 잠근다. 예전에는 이 선택지가 아예 없었다.

대신 새로 생긴 함정도 있다. 문서가 못 박는다 — **오토스케일러 설정 하나마다 전용 ASG/인스턴스 그룹/스케일 셋이 있어야 한다.** 두 설정이 같은 그룹을 공유하면 서로 모순되는 스케일 명령을 보낸다.[^gldocker] 그리고 **러너 매니저 자체는 스팟 인스턴스에 두면 안 된다.** 깃랩닷컴이 `saas-linux-small-amd64` 에 쓰는 구성도 같은 태그를 공유하는 러너 매니저 2대 이상이다.[^glautoscaler]

---

## 2. 깃랩: 공유 등록 토큰의 폐기

두 번째로 크게 바뀐 건 **신원**이다. 예전 깃랩 러너는 프로젝트·그룹마다 하나씩 있는 **registration token** 으로 등록했다. 토큰 하나가 유출되면 누구든 그 스코프에 러너를 등록할 수 있었고, 어느 러너가 어느 호스트인지 구분되지 않았다.

새 워크플로에서는 UI 에서 러너를 먼저 만들고, 그 러너에 귀속된 **authentication token**(`glrt-` 접두사)을 받는다.[^glnewtoken] 여기에 **system ID** 가 붙어서, 같은 인증 토큰을 여러 호스트에서 재사용해도 깃랩이 각 호스트를 구분한다.

전환은 강제되지 않았지만 관리자에게 스위치가 생겼다 — **GitLab 17.0 부터 관리자와 그룹 오너가 레거시 등록을 꺼 버릴 수 있다.** 끈 뒤에 옛 방식으로 등록을 시도하면 이렇게 돌아온다.[^glnewtoken]

```
410 Gone - runner registration disallowed
```

Helm 차트를 쓰는 쪽은 시크릿 필드 이름도 같이 바뀌었다 (`runner-registration-token` → `runner-token`).[^glnewtoken]

**여기까지가 개선이고, 문서가 스스로 적어 둔 미해결 사항도 있다.** 토큰 로테이션 시 **러너 매니저가 여럿이면 첫 번째 것만 갱신**되고, GitLab Operator 의 CRD 는 로테이션에 맞춰 업데이트되지 않는다.[^glnewtoken] "옮겼으니 끝" 이 아니라는 뜻이다.

---

## 3. 깃랩: 쿠버네티스 실행기는 관측성을 먼저 고쳤다

깃랩 러너의 Kubernetes executor 는 작업 하나당 파드 하나를 띄우고, 그 안에 build·helper·service 컨테이너를 넣는다.[^glk8s] 최근 업그레이드에서 고쳐진 건 기능보다 **"왜 안 도는지 안 보인다"** 쪽이었다.

- **Informers (GitLab Runner 17.9.0)** — 파드 상태 변화를 폴링 대신 watch 로 받는다. 클러스터 권한에 `pods` 의 `list` 와 `watch` 가 필요하고, **없으면 경고를 로그에 남기고 기존 방식으로 조용히 되돌아간다.**[^glk8s] 권한을 안 줬는데 "왜 안 빨라지지" 하게 되는 지점이라 기억해 둘 만하다.
- **`FF_PRINT_POD_EVENTS`** — 파드 이벤트를 작업 로그에 찍는다. 스케줄 실패·이미지 풀 실패가 "작업이 그냥 멈춤" 으로 보이던 걸 고친 플래그다.[^glk8s]
- **`FF_USE_LEGACY_KUBERNETES_EXECUTION_STRATEGY=false`** — attach 전략으로 전환한다. `pods/attach` 권한이 필요하다.[^glk8s]
- **`namespace_per_job`**, **`pod_disruption_budget`** — 작업 간 격리와 노드 드레인 중 작업 보호.[^glk8s]
- **별칭 기반 서비스 컨테이너 이름 (17.9)** — 서비스 컨테이너를 인덱스가 아니라 별칭으로 부른다.[^glk8s]

패턴이 보인다. 깃랩 쪽 업그레이드는 대체로 **"기능 플래그를 켜면 좋아지는데, 권한이 없으면 조용히 예전 동작"** 형태다. 켰다고 믿고 넘어가면 아무것도 안 바뀐 채로 몇 달이 간다.

---

## 4. 깃헙: 커뮤니티 오토스케일러에서 1차 API 로

깃헙 쪽 출발점은 정반대였다. 자체호스팅 러너는 그냥 `config.sh` 로 등록하고 대기하는 프로세스였고, 쿠버네티스에서 자동 확장하려면 **커뮤니티 프로젝트인 ARC(actions-runner-controller)** 를 써야 했다. 이 프로젝트는 지금 `actions` 조직 아래 있지만, 원래는 외부 메인테이너들이 만든 것이다.[^arcrepo]

바뀐 지점은 **runner scale set** 의 등장이다. ARC 저장소가 직접 적는다.[^arcrepo]

> autoscaling runner scale sets 의 도입으로, 기존 오토스케일링 모드들은 이제 **레거시**다. 레거시 모드는 특정 용도가 있어 **커뮤니티에 의해서만** 계속 유지보수된다.

즉 같은 저장소 안에 **깃헙이 지원하는 모드**와 **커뮤니티가 지원하는 모드**가 공존하고, Helm 차트 이름(`gha-runner-scale-set-controller` / `gha-runner-scale-set`)으로 갈린다.[^arcdocs] 오래된 블로그를 보고 `RunnerDeployment` CRD 로 시작하면 레거시 쪽에 들어가게 된다 — 지금 새로 까는 사람이 가장 흔히 밟는 함정이다.

### 무엇이 구조적으로 달라졌나

레거시 ARC 는 **깃헙 API 를 폴링**해서 대기 중인 작업 수를 보고 러너 수를 조절했다. 새 scale set 은 그렇지 않다. 깃헙 공식 문서가 기술한 흐름은 이렇다.[^arcdocs]

1. 리스너 파드가 깃헙 액션 서비스에 **HTTPS long poll 연결**을 열고 유휴 상태로 대기한다.
2. 워크플로가 트리거되면 액션 서비스가 `runs-on` 이 맞는 스케일 셋으로 작업을 배정하고 **`Job Available` 메시지를 내려보낸다.**
3. 리스너가 확장 가능 여부를 판단해 메시지를 ACK 하고, `EphemeralRunnerSet` 의 replica 수를 패치한다.
4. `EphemeralRunner` 컨트롤러가 **JIT(Just-in-Time) configuration token** 을 요청해 러너를 등록하고 파드를 만든다. 파드가 `failed` 면 **최대 5회 재시도**한다.
5. 작업이 끝나면 컨트롤러가 삭제 가능 여부를 확인하고 러너를 지운다.

세 가지가 한꺼번에 고쳐진 셈이다. **폴링이 푸시가 됐고**(추측 대신 신호), **등록 토큰이 JIT 토큰이 됐고**(러너 하나짜리 수명), **러너가 태생부터 ephemeral 이 됐다**.

그리고 큐 대기 시간에 관한 숫자가 문서에 박혀 있다 — **24시간 안에 어떤 러너도 작업을 받지 않으면 액션 서비스가 배정을 취소한다.**[^arcdocs] 자체호스팅 러너 일반에 대해서도 같은 값이다.[^ghselfhosted]

> 온라인·유휴 상태의 매칭 러너를 찾으면 작업이 배정된다. 러너가 **60초 안에** 배정된 작업을 집어가지 않으면 작업은 다시 큐로 돌아간다. (…) 작업이 **24시간** 넘게 큐에 남으면 실패한다.

### 쿠버네티스 밖으로도 나갔다

최근에는 scale set API 자체를 외부에 열었다. **GitHub Actions Runner Scale Set Client** 는 Go 모듈로, 깃헙 API 와의 상호작용은 클라이언트가 맡고 **인프라 프로비저닝은 사용자가 정의**한다.[^ghselfhosted] 문서가 ARC 와의 관계를 분명히 못 박아 둔다 — 대체재가 아니라 보완재이고, **쿠버네티스에서는 ARC 가 여전히 레퍼런스 구현이자 권장안**이다.[^ghselfhosted]

> 러너 스케일 셋 클라이언트는 ARC 의 대체재가 아니다. ARC 는 스케일 셋 API 의 레퍼런스 구현이자 쿠버네티스에서 러너를 오토스케일하는 권장 솔루션으로 남는다.

재미있는 건 이 지점에서 **두 제품이 정확히 반대 방향으로 움직였다**는 것이다. 깃랩은 러너가 클라우드 API 를 직접 호출해 인스턴스를 띄우는 쪽으로(fleeting), 깃헙은 프로비저닝을 사용자에게 넘기고 배정 신호만 제공하는 쪽으로 갔다.

---

## 5. 깃헙: 영구 러너를 "권장하지 않음" 으로 강등했다

깃헙 문서에서 가장 세게 적힌 문장은 오토스케일링 챕터에 있다.[^ghselfhosted]

> 깃헙은 **일회용(ephemeral) 자체호스팅 러너로 오토스케일링할 것을 권장한다. 영구 러너로의 오토스케일링은 권장하지 않는다.** 특정 상황에서 깃헙은 **러너가 종료되는 동안 작업이 배정되지 않는다는 것을 보장할 수 없다.** 일회용 러너라면 깃헙이 러너 하나당 작업 하나만 배정하므로 이것이 보장된다.

이건 편의 기능 얘기가 아니라 **경쟁 조건(race)** 얘기다. 스케일 인 중인 러너에게 작업이 날아가면 그 작업은 잃어버린다. 등록 시 `--ephemeral` 을 붙이면 액션 서비스가 작업 하나를 처리한 뒤 러너를 자동으로 등록 해제한다.[^ghselfhosted]

같은 챕터에 자주 놓치는 경고가 하나 더 있다.[^ghselfhosted]

> 일회용 러너의 러너 애플리케이션 로그 파일은 **반드시 외부 로그 저장소로 전달되어야 한다.**

파드가 사라지면 로그도 사라진다. 프로덕션에 일회용 러너를 깔기 전에 로그 파이프라인이 먼저 있어야 한다는 뜻이다.

그리고 운영상 알아 둘 것 하나 — 자체호스팅 러너는 기본적으로 **자동 업데이트**된다. 컨테이너 기반 일회용 러너에서는 새 버전이 나올 때마다 매번 업데이트가 반복되므로 `--disableupdate` 로 끄고 이미지에서 직접 관리하는 게 낫다. 다만 끄면 **새 버전 공개 후 30일 안에 직접 올려야 한다.**[^ghselfhosted]

---

## 6. 깃헙에만 있었던 업그레이드 — stdout 이 신뢰 경계였다는 것

이건 깃랩에 대응물이 없는, 깃헙 쪽만의 수정이다. 예전 액션은 스텝 출력을 **표준출력에 특수한 문자열을 찍어서** 전달했다.

```bash
echo "::set-output name=fruit::banana"
```

문제가 뭔지는 깃헙의 사장 공지가 직접 말한다.[^ghsetoutput]

> **의도하지 않은 상태에서 신뢰할 수 없는 로그 데이터가 `save-state` 와 `set-output` 워크플로 명령을 사용하는 것을 막기 위해**, 상태와 출력을 관리하는 새 환경 파일 집합을 도입했다.

즉 빌드 로그에 섞여 들어온 남의 문자열이 워크플로 명령으로 해석될 수 있었다. 테스트가 출력한 문자열 하나가 스텝 출력을 바꿔치기할 수 있었다는 뜻이다. 고친 방식은 채널 자체를 stdout 밖으로 옮기는 것이었다.

```bash
echo "fruit=banana" >> "$GITHUB_OUTPUT"
echo "key=value"    >> "$GITHUB_STATE"
```

타임라인도 기록해 둘 만하다. **러너 2.298.2 부터 경고**가 뜨기 시작했고 2023년 5월 31일 완전 비활성화가 예고됐지만, 2023년 7월 24일 깃헙은 **사용량이 여전히 많다는 이유로 제거를 연기**했다. 지금도 경고만 뜨고 동작은 한다.[^ghsetoutput][^ghsetoutput2]

> 텔레메트리상 이 명령들의 사용량이 상당해서 제거를 연기하기로 결정했다.

**이건 "개선" 이면서 동시에 "미완" 이다.** 보안 동기로 시작한 사장이 생태계 관성 때문에 3년 넘게 마무리되지 않고 있다. 내 워크플로에 `set-output` 이 남아 있다면 지금도 조용히 도는 중일 것이고, 위 취약점도 그대로 남아 있다.

---

## 7. 나란히 놓고 보기

| 축 | 깃랩 러너 | 깃헙 액션 러너 |
| --- | --- | --- |
| 오토스케일 1세대 | Docker Machine executor (업스트림 사장) | 커뮤니티 ARC (API 폴링) |
| 현재 권장 | Instance / Docker Autoscaler + fleeting 플러그인[^glautoscaler] | `gha-runner-scale-set` (리스너 long poll)[^arcdocs] |
| 1세대 상태 | 17.5 deprecated → **20.0 (2027-05) 제거 예정**[^gldm] | **레거시**, 커뮤니티 유지보수만[^arcrepo] |
| 스케일 신호 | 러너가 잡을 폴링 (`check_interval` 기본 3초)[^gladv] | 액션 서비스가 `Job Available` 푸시[^arcdocs] |
| 인프라 프로비저닝 | 러너가 클라우드 API 호출 (fleeting)[^gldocker] | 클러스터/사용자 몫 (Scale Set Client)[^ghselfhosted] |
| 러너 신원 | 공유 registration token → **`glrt-` 인증 토큰 + system ID**[^glnewtoken] | 등록 토큰 → **JIT configuration token**[^arcdocs] |
| 일회용 | `capacity_per_instance=1` + `max_use_count=1`[^gldocker] | `--ephemeral` / scale set 기본[^ghselfhosted] |
| 유실 작업 한도 | — | 60초 미수령 시 재큐, **24시간 후 실패**[^ghselfhosted] |
| 관측성 개선 | Informers·`FF_PRINT_POD_EVENTS` (17.9)[^glk8s] | 일회용 러너 로그 **외부 전송 필수** 경고[^ghselfhosted] |

**수렴한 지점 세 가지.**

1. **일회용이 기본이 됐다.** 깃랩은 설정 두 줄로, 깃헙은 아키텍처로. 동기는 같다 — 앞 작업이 남긴 것이 뒤 작업에 새어 들어가는 것을 구조적으로 막는 것.
2. **공유 비밀이 인스턴스 신원으로 바뀌었다.** 깃랩의 `glrt-` + system ID, 깃헙의 JIT 토큰. 둘 다 "토큰 하나로 아무나 러너를 붙일 수 있던" 상태를 끝냈다.
3. **스케일 판단이 추측에서 신호로 옮겨갔다.** 깃헙은 long poll 푸시로 완전히 갈아탔고, 깃랩은 폴링을 유지한 채 `IdleScaleFactor`·`MaxGrowthRate` 같은 조절 손잡이를 붙이는 쪽을 택했다.[^glautoscaler]

**아직 안 수렴한 지점.** 깃랩 러너 매니저는 **상태를 가진 장기 프로세스**라 스팟에 두면 안 되고 이중화가 권장된다.[^glautoscaler] 깃헙은 컨트롤러가 죽어도 작업이 액션 서비스 큐에 24시간 남는다 — 대기 비용을 서비스 쪽이 흡수한다.[^arcdocs] 자체호스팅을 얼마나 무겁게 운영해야 하는가에서 두 제품의 부담 분배는 여전히 다르다.

---

## 8. 그래서 지금 뭘 봐야 하나

버전별로 좋아진 것들을 나열해 봤자 내 러너가 그걸 쓰고 있지 않으면 소용이 없다. 실제로 확인할 것만 추리면 이렇다.

**깃랩 쪽이라면**

- `config.toml` 에 `docker+machine` executor 가 있는가 — 있다면 2027년 5월 시한이 이미 시작됐다.[^gldm]
- 러너 토큰이 아직 registration token 인가 — 17.0 부터 관리자가 레거시 등록을 끌 수 있고, 그때 `410 Gone` 이 뜬다.[^glnewtoken]
- Kubernetes executor 라면 서비스 어카운트에 `pods` 의 `list`/`watch` 가 있는가 — 없으면 Informers 가 **경고만 남기고 예전 방식으로 돌아간다.**[^glk8s]
- 오토스케일러 설정마다 **전용** ASG/인스턴스 그룹이 있는가.[^gldocker]

**깃헙 쪽이라면**

- ARC 를 `RunnerDeployment` CRD 로 깔았는가 — 그렇다면 커뮤니티 유지보수 모드에 있는 것이다.[^arcrepo]
- 러너가 정말 ephemeral 인가 — 영구 러너 오토스케일링은 **공식적으로 권장되지 않는다.**[^ghselfhosted]
- 일회용 러너의 **로그를 밖으로 보내고 있는가.**[^ghselfhosted]
- `set-output` 경고가 아직 애노테이션에 뜨는가 — 기능은 돌지만 취약점은 그대로다.[^ghsetoutput]
- 자동 업데이트를 껐다면 **30일 규칙**을 지키고 있는가.[^ghselfhosted]

---

## 9. 근거의 한계

- **성능 수치를 하나도 쓰지 않았다.** "fleeting 이 Docker Machine 보다 몇 배 빠르다", "scale set 이 레거시 ARC 보다 스케일업이 몇 초 빠르다" 같은 수치는 **재현 가능한 중립 측정치를 확인하지 못했다.** 문서가 말하는 구조적 차이(VM 당 컨테이너 1개 제약이 사라짐, 폴링이 푸시로 바뀜)만 옮겼다.
- **두 제품의 버전 타임라인은 서로 대응하지 않는다.** GitLab 17.5 와 ARC 의 scale set 도입 시점을 나란히 놓은 건 **같은 시기라서가 아니라 같은 문제를 푼 변화라서**다. "누가 먼저였나" 는 이 글이 주장하지 않는다.
- **양쪽 다 벤더 자기 문서다.** 무엇이 좋아졌는지는 상세히 적혀 있지만, 무엇이 나빠졌거나 마이그레이션에서 깨졌는지는 훨씬 덜 기록된다. 그래서 문서가 스스로 적어 둔 미해결 사항(깃랩의 토큰 로테이션 결함, 깃헙의 `set-output` 제거 연기)을 일부러 본문에 남겼다.
- **"반대편에서 같은 답에 도착했다" 는 내 해석이다.** 인용한 문장들은 전부 1차 출처지만, 세 가지 수렴점으로 묶은 건 어느 한 문서가 그렇게 적어 둔 게 아니라 내가 대조해서 끌어낸 구조다.
- **셀프호스팅 관점만 봤다.** 깃헙 호스티드 러너 이미지(`runner-images`)의 세대 교체나 깃랩닷컴 SaaS 러너의 사양 변화는 다루지 않았다. 축이 다르다.
- **실측하지 않았다.** 이 글의 모든 주장은 문서 대조이고, 내 홈랩 클러스터에서의 실측은 [별도의 글]({% post_url 2026-09-13-static-runner-to-arc-what-changed %})에 있다.

---

## References

[^gldm]: GitLab 공식 문서 — [Docker Machine executor autoscale configuration](https://docs.gitlab.com/runner/configuration/autoscale/)
[^glautoscaler]: GitLab 공식 문서 — [GitLab Runner Autoscaler](https://docs.gitlab.com/runner/runner_autoscale/)
[^gldocker]: GitLab 공식 문서 — [Docker Autoscaler executor](https://docs.gitlab.com/runner/executors/docker_autoscaler/)
[^glnewtoken]: GitLab 공식 문서 — [Runner registration token deprecation / new runner creation workflow](https://docs.gitlab.com/ci/runners/new_creation_workflow/)
[^glk8s]: GitLab 공식 문서 — [Kubernetes executor](https://docs.gitlab.com/runner/executors/kubernetes/)
[^gladv]: GitLab 공식 문서 — [Advanced configuration (`config.toml`)](https://docs.gitlab.com/runner/configuration/advanced-configuration/)
[^arcdocs]: GitHub 공식 문서 — [Actions Runner Controller](https://docs.github.com/en/actions/concepts/runners/actions-runner-controller)
[^arcrepo]: GitHub 공식 저장소 — [actions/actions-runner-controller — README](https://github.com/actions/actions-runner-controller)
[^ghselfhosted]: GitHub 공식 문서 — [Self-hosted runners reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)
[^ghsetoutput]: GitHub Changelog (2022-10-11) — [GitHub Actions: Deprecating save-state and set-output commands](https://github.blog/changelog/2022-10-10-github-actions-deprecating-save-state-and-set-output-commands/)
[^ghsetoutput2]: GitHub Changelog (2023-07-24) — [GitHub Actions: Update on save-state and set-output commands](https://github.blog/changelog/2023-07-24-github-actions-update-on-save-state-and-set-output-commands/)
