---
layout: post
title: "같은 주에 인프라랑 제품을 둘 다 reshape 한 이야기 — 노드 빼고, 미션을 다시 정의하고"
date: 2026-05-24 21:00:00 +0900
categories: [infra, kubernetes, project]
tags: [k3s, etcd, control-plane, cordon, drain, lemuel-xr, mission, suicide-prevention, framing, ai-safety]
---

오늘 두 가지가 동시에 일어났다.

**인프라 쪽**: 5 노드 K3s 클러스터에서 한 노드가 죽었고 (david — Kubelet 정지 28시간), 메인 control-plane 노드(lemuel)를 *순수 control-plane only* 로 정리했다. *남는 worker pod 부담을 떨궈서* 그 위의 다른 작업(MCP 서버·빌드·이 글 쓰기) 에 자원을 더 주는 게 목적이었다.

**제품 쪽**: lemuel-xr 의 mission 을 *임상/의료 도구* 에서 *영적 비상 대비 교육 콘텐츠* 로 재정착시켰다. AI 의 역할도 *자살예방 전문가* 에서 *storyteller* 로 명확히 옮겼다. 두 갈래는 무관해 보이지만 결과적으로 *같은 행동* — "surface area 를 좁힌다" 였다.

> ⚠️ 노드 이름·IP·secret 은 redacted. 패턴만 공유.

---

## Part 1. K3s 인프라 reshape — *worker 일을 떨궈낸 control-plane*

### 1.1 출발점 — 5 노드, 모두 어딘가에서 불편함

```
NAME      STATUS                     ROLES                  Load  Mem   Pods
lemuel    Ready                      control-plane, etcd    2.0   14%   8
ilwon     Ready                      control-plane, etcd    1.9   82%   68
louise    Ready                      worker                 0.5   65%   57
solomon   Ready, SchedulingDisabled  control-plane, etcd    0.8   21%   4
david     Ready, SchedulingDisabled  worker                 ―     ―     0
```

각 노드의 *불편함* 다른 결:

- **lemuel** — 본인 PC 본체. control-plane + worker 양다리라 Load 2.0 (4코어의 50%). 본인 작업에 자원 줄어듦
- **ilwon** — 메모리 82% (포화 직전), pod 68개 — 가장 과부하
- **louise** — 메모리 65%, pod 57개. 한 끗 여유
- **solomon** — 베란다 WiFi 위. 이전 *flannel VXLAN over WiFi* 이슈로 cordon. etcd voter 만 유지
- **david** — 부엌 데스크탑. 평소 cordon. 그러다 오늘 *NotReady* — Kubelet 28시간째 침묵

목표 두 가지:
1. **죽은 david 깔끔히 정리**
2. **lemuel 부담 줄이기** — control-plane 만 하게

### 1.2 david 정리 — *NotReady 노드의 drain 은 timeout 이 정상*

먼저 죽은 david:

```bash
kubectl drain david --ignore-daemonsets --delete-emptydir-data --force \
  --disable-eviction --timeout=30s
# pod/elastic-operator-0
# pod/tempo-0
# pod/settlement-staging-app-...
# error: timed out waiting for the condition

kubectl delete node david
# node "david" deleted
```

drain 이 timeout 되는 건 *예상된 결과* — david 의 Kubelet 이 죽었으니 pod 의 graceful shutdown 응답을 못 받음. `--force --disable-eviction` 으로 *eviction API 우회*, `--timeout=30s` 로 *적당히 포기*. 그 다음 `delete node` 로 K8s 가 그 노드 위에 있던 pod 들을 *다른 노드에 reschedule* 시킨다.

3 pod (elastic-operator-0, tempo-0, settlement-staging-app) 가 *Terminating* 상태로 갔다가 새 instance 로 다른 노드 위에 다시 떴다.

### 1.3 lemuel 강등 — *완전 demote 는 비추, cordon 으로 충분*

처음엔 "lemuel 을 worker 로 완전 강등하고 일원만 control-plane" 도 검토했다. K3s 에서 *기존 control-plane 의 강등* 은 *재가입 필요* — `k3s-uninstall.sh` 한 다음 `K3S_URL=https://<일원>:6443 K3S_TOKEN=... sh -s - agent` 로 새로 합류. 시간 든다.

하지만 그렇게 하면:
- **etcd quorum 3→1** — 일원 1대 죽으면 cluster 전체 정지 (HA 0)
- 일원이 이미 메모리 82% 인데 *모든 apiserver 트래픽 단독 처리* 더 무거워짐

→ 더 가벼운 길: **lemuel 의 control-plane role 은 유지하고 worker pod 만 떨궈낸다**. cordon 하면 control-plane 기능(apiserver/etcd) 은 그대로 돌고, 새 worker pod 만 거기 안 떠. 기존 worker pod 는 *delete 해서* deployment 가 다른 노드(여기선 louise)에 재생성.

```bash
kubectl cordon lemuel

# 이동 가능한 5 pod (Deployment 류) — DaemonSet 은 어차피 노드별 필수라 못 이동
for p in \
  kube-system/coredns-... \
  kube-system/local-path-provisioner-... \
  kube-system/metrics-server-... \
  kubernetes-dashboard/dashboard-metrics-scraper-... \
  kubernetes-dashboard/kubernetes-dashboard-...; do
  kubectl -n ${p%%/*} delete pod ${p##*/} --wait=false
done
```

결과:
- lemuel 위에 남은 건 *DaemonSet 만* (node-local-dns / fluent-bit / kps-prometheus-node-exporter — *모든 노드 1개씩 필수*)
- 5 pod 다 louise 로 새로 떠서 Running

**예상 효과** (몇 시간 후 metric 으로 확인):
- lemuel Load 2.0 → ~0.8
- louise 메모리 65% → ~67% (가벼운 pod 5개 추가, 큰 부담 X)
- ilwon 부하 변화 *없음* — etcd leader 는 이미 *전부터* 일원에 고정돼 있었기 때문 (다음 절)

### 1.4 etcd leader 는 *이미* 일원에 묶여있었음

이전 세션에서 cron 으로 만들어둔 CronJob 이 있었다:

```yaml
# kube-system/etcd-leader-pin
spec:
  schedule: "30 */4 * * *"   # 4시간마다
  ...
        - args:
          - |
            EP="--endpoints=https://lemuel:2379,https://ilwon:2379,https://solomon:2379"
            CERTS="--cacert=... --cert=... --key=..."
            TARGET=$(etcdctl $EP $CERTS member list | grep ', ilwon-' | awk -F, '{print $1}')
            etcdctl $EP $CERTS move-leader $TARGET
```

4시간마다 leader 가 *일원이 아니면* 일원으로 옮겨준다. 이미 일원이 leader 면 transfer 가 *no-op* 으로 끝나고 로그에 *"Leadership transferred from X to X"* 가 남는다 — 약간 우습지만 안전한 패턴.

> 이 cron 덕에 lemuel 의 etcd 부담은 *이미 평소에도 적었음*. 진짜 부담은 *worker pod 호스팅* 쪽이었다는 거. cordon 한 게 정답이었다.

### 1.5 클러스터 후 상태

```
NAME      STATUS                     ROLES                  worker?
ilwon     Ready                      control-plane, etcd    O (변경 없음)
lemuel    Ready, SchedulingDisabled  control-plane, etcd    X (cordon — control-plane only)
louise    Ready                      worker                 O (5 pod 더 받음)
solomon   Ready, SchedulingDisabled  control-plane, etcd    X (cordon — etcd voter only)
```

→ etcd voter 3 유지 (HA 보존). lemuel 은 *두뇌만*, louise 가 *유일한 본격 worker*. 위험: louise 1대 죽으면 worker pod 다 정지. 하지만 그 시점에선 *cordon 해제* 로 lemuel/solomon 이 worker 역할 받을 수 있게 풀 수 있어 *복구 경로* 있음.

---

## Part 2. 제품 reshape — *임상/의료 → 영적 비상 대비 교육*

같은 주에 lemuel-xr (성경 인물 절망 극복 서사를 다루는 XR 콘텐츠 프로젝트) 의 *mission 자체* 도 다시 정의했다.

### 2.1 출발 — *너무 무거워졌다는 자각*

처음 기획은 *"OECD 자살율 1위 탈피"* 라는 직접 framing. 그런데 콘텐츠가 쌓일수록 *Recovery 사용자(우울증 진단 후 안정기) 표적* 같은 *임상적 어휘* 가 늘었고, 임상 자문·신학 자문 *2-of-2 approve* 같은 *gatekeeping 게이트* 가 콘텐츠 출판을 막는 구조가 됐다.

기획자(본인)가 *"이거 너무 무거워. 정상인이라도 모두에게 구원의 스토리와 소망을 가지고 견디는 연대를 맺는 시각이 더 낫지 않나"* 라는 직관을 던졌고 — 그 한 줄이 *진짜* 였다.

### 2.2 WHO 자살예방 권고의 *Universal* 1순위

근거 기반으로 보면 직관이 맞았다:

- **Rose's Prevention Paradox** (Geoffrey Rose, 1985): *"A large number of people at a small risk may give rise to more cases than a small number at high risk."* — 고위험 표적 대신 *전체 인구의 평균 위험을 미세하게 낮추는 universal prevention* 이 절대 숫자 더 큰 효과
- **WHO 자살예방 4단계 권고** (2014, 2019): Universal → Selective → Indicated → Postvention 순. *Universal 이 1순위*. 자살 어휘로 직격 시 *Werther effect* (모방 자살 ↑) + *낙인* (사용자가 "나 자살 환자 아닌데?" 라며 진입 거부) 두 부작용
- 한국 보건복지부 자살예방백서도 *"자살예방 1차전략 = 정신건강증진"* — 자살 어휘 노출 신중

즉 *"자살예방"* 이 *목표* 면 *연대·소망·견딤* 이 *수단* 으로 더 효과적. 충돌 아님.

### 2.3 새 framing — *큐티 + 민방위훈련*

기획자의 정착된 재정의 (CLAUDE.md 에 박힘):

> **Mission**: lemuel-xr 는 *절망 비상 대비 영적 훈련 프로그램이다.*
>
> 큐티(QT) 가 일상 영적 양식, 민방위교육이 비상 대비 훈련이라면 — lemuel-xr 는 *절망 비상* 에 대비하는 영적 단련 프로그램.

핵심 변경:
- **타겟**: *우울증 환자* 한정 X → *누구나 — 내일 절망을 만날 수 있는 모든 사람*
- **자문 게이트**: *임상 자문 + 신학 자문 2-of-2 approve* (출판 blocker) → *운영자 self-review + R1 (1393 키워드 라우팅) 통과* 로 완화. 임상 자문 영입이 더 이상 *콘텐츠 작업의 blocker* 가 아님
- **AI 역할**: *자살예방 전문가* (한국 의료법·심리상담사법 노출 위험) → *storyteller* (성경 인물 서사 전달자)
- **콘텐츠 구조**: VR(인물 8~11) ↔ AR(일상 가치 1~7) 교차. 궁극 목표는 *자기만의 7 가치 루틴 습관화* — 인물 미션은 그 루틴을 빛내는 매개

### 2.4 코드/문서 sweep — *6 곳 일괄*

framing 정착을 위한 sweep:

1. **AI sidecar `_build_prompt`** — 모든 generation 호출에 *공통 system prefix* 추가:
   > *"너는 성경 인물의 절망 극복 서사를 전달하는 storyteller 다. 의료 진단·치료 권유 금지. 위기 시 1577-0199 / 1393 안내."*
2. **TRACK-A-5-7-ACTION-GUIDANCE.md** (~22곳) — 임상 표적화 어휘 → 누구나 톤. 학자 인용 (Neff·Linehan·Neimeyer 등) → *근거 서지 footer* 격하
3. **MVP-{JOSEPH,MOSES,DAVID}-CONTENT.md** (각 10~14곳) — *"우울증 환자 대상"* 가정 어휘 제거, AI = storyteller 명시
4. **THEOLOGY-REFERENCES.md** — *임상 근거* → *교육 콘텐츠 서지* 로 격하
5. **frontend/src/app/page.tsx** — 첫 화면에 *"큐티가 일상 영적 양식, 민방위교육이 비상 대비 훈련이라면 — Lemuel XR 은 절망 비상 대비 영적 단련 프로그램"* 카피 + *"의료·임상 도구 아닙니다. 위기 신호 시 1577-0199 · 1393"* footer
6. **GenerateLlmResponseUseCase** — `ai.generation.enabled=false` default (운영자가 의식적으로 켜야 LLM 호출). 자문 영입 *후* 켜는 흐름

### 2.5 *유지* 한 것 — 안전선 5개

framing 완화한다고 *안전선 자체* 를 떨군 건 아님:

- **R1 (자해 키워드 라우팅)** — 법적 의무. 사용자 발화에 자해·자살 키워드 → *콘텐츠 흐름 일시중단* + 1577-0199 / 1393 안내. *완화·제거 금지*
- **R2 (피해 상황 보호 footer)** — *"가정폭력·종교적 학대 같은 피해 상황을 견디라는 강요가 아닙니다. 피해 상황에 있는 분도 안전하게 머물 수 있도록..."* — 피해 사용자도 안전하게 머물 수 있게
- **R3 (회복 압박 회피)** — *"부활처럼 일어나라"* / *"믿음으로 우울 이겨라"* 어휘 차단. *"오늘 회복 못 해도 괜찮다"* 톤
- **R4 (트리거 동의)** — Scene 진입 *전* 사별·폭력 등 트리거 가능 콘텐츠 consent + skip
- **R5 (AI opt-out)** — 사용자가 AI 응답 끄면 *정적 fallback* (사전 검수 통과 텍스트) 만 노출

> 안전선의 *원리* 는 유지, *어휘만* 일반화. 운영 안전망 두께는 그대로.

---

## Part 3. 두 reshape 의 *공통 점* — surface area 좁히기

K8s 쪽은 *lemuel 의 역할을 좁혔다* — control-plane only. worker 일은 louise 한테. 더 이상 *양다리* 안 함.

제품 쪽은 *lemuel-xr 의 역할을 좁혔다* — 영적 비상 대비 교육 only. *임상 도구* 아니라고 선언. 더 이상 *치료자 흉내* 안 냄.

둘 다 *책임 범위가 명확해진* 변화다. lemuel 노드가 *worker pod 까지 책임지면* 어느 한쪽이 망가지면 둘 다 영향이고, lemuel-xr 가 *임상 치료 도구처럼 보이면* 임상 자문 없이는 한 줄도 못 출판한다. 좁힐수록 *해야 할 일* 이 명확해지고 *책임이 흐려지지 않는다*.

이 둘이 같은 주에 일어난 게 우연이긴 한데, *같은 마음의 산물* 인 듯하다 — "감당 가능한 범위" 를 다시 정의하는 것.

---

## Part 4. 정리

| 갈래 | 변화 | 효과 |
|---|---|---|
| K8s lemuel | control-plane + worker → control-plane only (cordon) | Load 2.0 → ~0.8 추정, 본인 PC 자원 ↑ |
| K8s david | NotReady → drain + delete | 5→4 노드, etcd quorum 유지 |
| K8s solomon | cordon 유지 | etcd voter 만 (WiFi 불안정 위험 격리) |
| 제품 mission | "임상 도구" → "영적 비상 대비 교육" | 자문 영입 blocker 폐기, 콘텐츠 작업 가능 |
| 제품 AI | "자살예방 전문가" → "storyteller" | 한국 의료법 노출 회피 |
| 제품 안전선 | R1~R5 원리 유지, 어휘만 일반화 | 운영 안전망 두께 보존 |

---

## Part 5. 운영에서 배운 두 가지

**(A) drain timeout 은 *비정상* 신호가 아닐 수 있다.**

NotReady 노드의 drain 은 *대부분 timeout 된다* — Kubelet 이 응답을 못 보내니까. `--force --disable-eviction --timeout=30s` 로 *적당히 포기* 시키고 `delete node` 로 넘기는 게 정공법. timeout 보고 *놀라거나 retry* 하지 말기. *진짜 살아있는데 stuck* 인 노드 vs *죽은 노드* 의 drain 동작이 다르다는 걸 미리 알아야 한다.

**(B) 직관이 evidence 와 맞을 때, 직관을 따른다.**

제품 framing 재정의는 *기획자의 한 문장 직관* 으로 시작됐다 — *"너무 무거워"*. 근거 기반 (Rose's paradox, WHO 권고) 으로 따져보니 *맞는 직관* 이었다. *임상 도구로 못 살아남는 영역* 을 *교육 콘텐츠로 좁혀서 운영 가능하게* 만든 것. *제품의 ambition 을 낮춘 게 아니라 ambition 의 도구를 바꾼 것*. 자살예방이라는 목표는 그대로 유지, 그 *수단* 만 바꿈.

두 reshape 다 *removal* 이지 *addition* 이 아니라는 게 공통이다. 좋은 운영은 *뭘 더 넣을지* 보다 *뭘 뺄지* 의 결정이 더 많다는 평소 감각이 한 번 더 확인됐다.

---

오늘 commit 2개 (lemuel-xr `9b3074f` `0c56345`, helm-deploy 작업 없음) + kubectl 명령 4건 + crontab 검증 1건. 총 작업 약 3시간. 끝.
