---
layout: post
title: "디지털 트윈을 작게 세 개 만들어 봤다 — 지하철·노드 드레인·원장 리플레이"
date: 2026-08-27 06:11:53 +0900
categories: [engineering]
tags: [digital-twin, kubernetes, event-sourcing, bitemporal, kotlin, simulation]
---

운영 대시보드는 "지금 어떻게 돌고 있나"에 답한다. 그런데 정작 사람이 밤에 궁금해하는 건
그 질문이 아니다.

- **"이 노드를 빼면 뭐가 죽나?"** — 빼 보기 전에는 모른다. 빼 본 뒤에 알면 늦다.
- **"이 정산 숫자가 어떻게 나온 건가?"** — DB 에 값은 있는데 유래가 없다.
- **"관측이 끊긴 3분 동안 열차는 어디까지 갔나?"** — 대시보드는 마지막으로 본 자리에 열차를 세워 둔다.

셋 다 *지금 상태*를 더 예쁘게 그린다고 풀리지 않는다. 원본과 **따로 굴러가는 모형**이
있어야 답할 수 있는 질문들이다. 그래서 작은 걸 세 개 만들었다. 이 글은 만든 자랑이 아니라,
"디지털 트윈"이라는 말이 원래 무엇을 뜻했고 내가 만든 게 그 정의를 어디까지 지키고
어디서 못 지키는지에 대한 기록이다.

## 원래 정의부터 — 대시보드는 트윈이 아니다

이 단어의 널리 인용되는 정의는 NASA Langley 의 Glaessgen 과 미 공군과학연구소의 Stargel 이
2012년 AIAA 논문에서 내놓은 것이다.[^1]

> A Digital Twin is an integrated multiphysics, multiscale, probabilistic simulation of an
> as-built vehicle or system that uses the best available physical models, sensor updates,
> fleet history, etc., to mirror the life of its corresponding flying twin.

문장이 길지만 뜯어보면 요구 조건이 셋이다.

1. **모델** — 원본의 물리/규칙을 흉내 내는 시뮬레이션이 있을 것
2. **센서 갱신** — 실제 관측이 계속 흘러들어와 모형을 교정할 것
3. **이력** — 과거 기록을 함께 쓸 것

그리고 같은 논문은 트윈의 쓸모를 이렇게 적는다 — **예측과 실제 반응을 대조해서 아직
드러나지 않은 문제를 미리 찾아내는 것**.[^1] 이 대목이 핵심이다. 대조하지 않는 트윈,
즉 자기가 얼마나 틀렸는지 재지 않는 트윈은 **검증할 수 없는 주장**일 뿐이다. GitHub 에서
"digital twin" 을 검색하면 나오는 것 대부분이 여기서 걸린다. 원본을 떼어 놓으면 아무것도
못 하는 실시간 대시보드다.

그래서 세 개를 만들 때 규칙을 하나 두었다. **원본 없이도 혼자 굴러가야 한다.** 셋 다
인증키·클러스터·카프카 없이 명령 하나로 돌아간다. 내장된 합성 세계가 있고, 난수는 고정
시드다. 이건 데모 편의가 아니라 위 정의의 1번을 지켰는지 확인하는 시험이다. 모델이
원본에 기생하고 있으면 원본을 떼는 순간 멈춘다.

---

## 트윈 1 — 지하철 2호선 (twinkit)

서울 지하철 2호선 순환선을 대상으로, 20초마다 관측을 받아 열차 위치를 갱신하고, **다음
관측이 오기 전까지는 모델이 혼자 열차를 굴린다.** 그리고 다음 관측이 도착하면 자기 예측이
얼마나 빗나갔는지를 잰다.

이게 왜 필요한지는 데이터 원천의 공식 문서가 그대로 설명해 준다. 서울 열린데이터광장의
지하철 실시간 도착정보 API 는 주의사항에 이렇게 적어 두었다.[^2]

> 출력값 중 `recptnDt`(열차 도착정보를 생성한 시각)는 데이터가 생성된 시간을 의미하며
> 현재시각과 `recptnDt` 의 차이 만큼 열차가 더 진행한 것으로 보정해서 사용해야 합니다.

즉 **API 를 그대로 화면에 그리면 이미 틀린 그림**이다. 데이터가 만들어진 시각과 내가 그것을
받아 본 시각이 다르고, 그 사이에 열차는 계속 갔다. 공식 문서가 "보정해서 쓰라"고 말하는
그 보정이 곧 모델이다. 대시보드와 트윈이 갈리는 지점이 여기다.

측정 결과는 이렇게 남는다(내장 합성 세계, 열차 24대, 20초 폴링):

```
  관측    경과     정확도   평균오차   p90    학습구간
  ────────────────────────────────────────────────────
     50     16분     90.5%     0.10역    0.0역    86/86
    100     33분     92.8%     0.07역    0.0역    86/86
    400    133분     92.6%     0.07역    0.0역    86/86
```

숫자 자체보다 **정확도 칸이 존재한다는 것**이 요점이다. 틀린 정도를 계속 적어 두지 않으면
모형이 언제 쓸모없어졌는지 알 수 없다.

---

## 트윈 2 — 노드 드레인 (kube-drain-twin)

`kubectl drain` 은 정직한 명령이다. 실행하면 진짜로 빠진다. 문제는 **빼 보기 전에는 결과를
모른다**는 것이고, 결과가 "파드 영구 Pending" 이면 그때는 이미 서비스가 내려간 뒤다.

이 트윈은 클러스터에 **접속하지 않는다.** 스냅샷 한 장(`kubectl get nodes,pods,pv,pvc,pdb -A -o json`)을
받아서 그 안에서만 계산한다. 읽기 권한조차 요구하지 않는 게 설계 결정이다 — 시뮬레이터가
운영 클러스터에 붙을 이유가 없고, 붙는 순간 "시뮬레이션인 줄 알았는데 실제였다" 사고의
씨앗이 된다.

계산해야 할 것이 왜 자명하지 않은지는 Kubernetes 공식 문서가 잘 보여 준다. PodDisruptionBudget 은
직관과 어긋나는 데가 많다.

- **PDB 는 자발적 중단만 막는다.** 비자발적 중단은 막지 못하지만 **예산에서는 차감된다.**[^3]
- **Deployment 나 Pod 를 그냥 지우면 PDB 를 우회한다.** PDB 를 존중하는 건 Eviction API 를
  거치는 도구뿐이다.[^3]
- **`maxUnavailable: 0`(또는 `minAvailable: 100%`)이면 자발적 축출이 0 건**이라, 그 파드가
  올라가 있는 노드는 **드레인이 영영 끝나지 않는다.** 문서는 이것이 버그가 아니라 PDB
  의미론상 허용된 동작이라고 못 박는다.[^4]
- **기본 정책은 `IfHealthyBudget`** 이라, `CrashLoopBackOff` 처럼 망가진 파드가 오히려
  드레인을 막는다. 그래서 문서는 `AlwaysAllow` 를 권한다.[^3]
- **컨트롤러 없는 맨 파드**에는 정수형 `minAvailable` 만 쓸 수 있다. 총 개수를 유도할 수
  없기 때문이다.[^4]

이 다섯 개를 머리로 조합해서 "이 노드 빼도 되나"를 맞히는 건 사람이 할 일이 아니다. 그리고
PDB 말고도 발목을 잡는 게 하나 더 있는데, 실은 이쪽이 더 무섭다.

```
── 1단계: 지금 무엇이 못 박혀 있나 ──
⛔ 데이터가 노드에 있다 — 매니페스트를 고쳐도 안 풀린다 (2건)
  worker-b
    data/postgres-0  볼륨 → worker-b
    data/redis-0     볼륨 → worker-b

⚠️  스펙으로 묶임 — 매니페스트를 고치면 풀린다 (1건)
  worker-c
    batch/nightly-import  nodeSelector tier=batch
```

두 종류를 갈라 놓은 게 이 도구에서 제일 쓸모 있는 부분이다. `nodeSelector` 로 묶인 건
매니페스트를 고치면 풀린다. **로컬 볼륨에 묶인 건 안 풀린다** — 데이터가 그 디스크에
있으니까. 노드 정비 계획을 세울 때 이 둘을 같은 목록에 섞어 놓으면 판단을 그르친다.

---

## 트윈 3 — 원장 리플레이 (replay-twin)

정산 사고는 대개 이런 모양으로 온다. 판매자가 "정산액이 안 맞는다"고 한다. DB 를 열어
본다. 값은 그럴듯하다. **그런데 그 값이 어떻게 나온 건지 아무도 모른다.**

이벤트 소싱을 쓰고 있다면 답은 로그 안에 있다. Fowler 가 정리한 그대로, 이벤트 소싱의
쓸모는 "무엇이 현재 상태인가"가 아니라 **"어떻게 여기까지 왔는가"** 이고, 로그가 있으면
과거 상태를 재구성할 수 있다.[^5] 문제는 그 "다시 접기"를 실제로 해 볼 도구가 대개 없다는
것이다. 그래서 로그는 쌓여 있는데 아무도 안 접는다.

이 트윈은 이벤트 로그를 다시 접어 장부를 만들고 운영 DB 스냅샷과 대조한다.

```
  주문 상태  117/120 일치 (97.5%)
  판매자 잔액 3/6 일치 · 최대 차이 195,000 원

  ⛔ 어긋난 곳 9건

  [STATUS] 3건
    ord-0007: 리플레이 AUTHORIZED ↔ DB SHIPPED
      → DB 는 매입 뒤로 갔는데 매입 이벤트가 로그에 없다
```

**둘이 다르면 원인은 셋 중 하나다** — 이벤트가 유실됐거나, 소비자가 잘못 접었거나, 누가
DB 를 직접 고쳤거나. 어느 쪽인지는 어긋난 *모양*이 말해 준다. 위 예처럼 DB 만 앞서 가
있으면 발행이 빠진 쪽을 먼저 의심한다.

### 시간 축이 두 개라는 사실

여기서 제일 재미있었던 부분. 이벤트에는 시각이 두 개 있다. **언제 벌어졌나(`occurredAt`)** 와
**언제 기록됐나(`recordedAt`)**. Fowler 는 이걸 bitemporal 이라 부르며 *actual history* 와
*record history* 로 갈라 놓는다 — 앞의 것은 정보 전달이 완벽했다면 어땠을 역사이고, 뒤의
것은 **우리의 지식이 어떻게 변해 왔는가**의 기록이다.[^6]

같은 로그를 어느 축으로 접느냐에 따라 장부가 달라진다. 내장 예제에서는 이렇게 벌어진다.

```
  기준(발생시각 순)  매입 10,945,000 원 · 이상 4건
  분기(기록시각 순)  매입  9,005,000 원 · 이상 46건
  차이               매입 -1,940,000 원
```

**두 값의 차이가 곧 "늦게 온 데이터가 과거를 바꾼 양"** 이다. 마감 배치가 틀리는 이유가
대개 여기 있다. 마감 시점에 아직 도착하지 않은 이벤트는 그 마감에 반영되지 못했는데,
나중에 같은 기간을 다시 조회하면 이제는 반영되어 있다. 두 숫자 다 맞고, 그래서 더
곤란하다. 지연 분포를 같이 보면 규모가 잡힌다.

```
  p50 3초 · p90 47초 · p99 4시간 2분 · 최대 4시간 25분
```

p50 이 3초라고 안심할 일이 아니다. **마감을 망치는 건 p99 의 4시간짜리 꼬리**다.

그리고 앞서 지하철 API 의 `recptnDt` 주의사항[^2]이 정확히 같은 이야기였다는 것도 여기서
드러난다. 도메인이 지하철이든 정산이든, **사건이 벌어진 시각과 내가 그걸 알게 된 시각은
다르다.** 셋을 따로 만들다가 같은 벽을 두 번 만났다.

---

## 셋에 공통으로 둔 규칙

- **프레임워크를 안 쓴다.** HTTP 화면은 JDK 에 들어 있는 `com.sun.net.httpserver` 로 붙였다.
  화면 하나 붙이자고 웹 프레임워크를 끌어오면 "외부 의존이 거의 없다"는 성질이 깨지고
  이미지가 몇 배가 된다.
- **입력을 저장하지 않는다.** 붙여넣은 로그와 스냅샷은 그 요청 안에서만 산다.
- **원본에 접속하지 않는다**(드레인 트윈·리플레이 트윈). 시뮬레이터에 운영 접근 권한을
  주지 않는다.
- **난수는 고정 시드다.** 문서에 적은 숫자가 그대로 재현되지 않으면 그 문서는 거짓말이다.

### 올려놓고 바로 밟은 함정 하나

세 개를 공개 주소에 올린 뒤, 브라우저로는 멀쩡히 열리는데 링크가 죽은 것처럼 보이는
증상을 만났다. 원인은 라우터였다. 라우트 표에 `GET <경로>` 와 `POST <경로>` 만 담아 두어서
**`HEAD` 요청은 어떤 경로든 404** 였다.

RFC 9110 은 HEAD 를 이렇게 정의한다.[^7]

> The HEAD method is identical to GET except that the server MUST NOT send content in the
> response. HEAD is used to obtain metadata about the selected representation without
> transferring its representation data, **often for the sake of testing hypertext links** or
> finding recent modifications.

"링크가 살아 있는지 시험하려고" 쓰는 메서드라고 규격이 직접 말하고 있다. 링크 미리보기
크롤러와 헬스체크 도구가 바로 그 용도로 HEAD 를 먼저 던지고, 그때 404 를 받으면 멀쩡한
주소가 죽은 링크로 보인다. 고친 방식은 라우트를 두 벌 등록하는 게 아니라 조회 키만 바꾸는
것이다.

{% raw %}
```kotlin
fun handle(method: String, path: String, req: Req): Res {
    // HEAD 는 GET 과 같은 헤더를 몸통 없이 돌려주는 게 규약이다(RFC 9110 §9.3.2).
    val key = if (method == "HEAD") "GET $path" else "$method $path"
    return routes[key]?.invoke(req)
        ?: Res(404, "text/plain; charset=utf-8", "없는 경로: $method $path")
}
```
{% endraw %}

응답을 보낼 때는 몸통을 생략하되 `Content-Length` 는 GET 이었을 때의 크기로 적어 준다.
규격이 "GET 이었다면 보냈을 헤더를 그대로 보내라(SHOULD)"고 하기 때문이다.[^7] 고친 뒤
실측하면 `HEAD /` 가 200 에 `Content-Length: 6567`, 본문 0바이트로 GET 과 정확히 맞는다.

작지만 이런 게 진짜 배움이었다. **화면이 잘 보인다고 서버가 옳게 대답하고 있는 건 아니다.**

---

## 아직 안 풀린 것

정직하게 적어 둔다. 위의 정의[^1]에 비추면 내가 만든 셋은 **온전한 트윈이 아니다.**

- **센서 갱신이 계속 들어오는 건 지하철 트윈뿐이다.** 나머지 둘은 스냅샷을 사람이 붙여넣는
  배치다. 정의의 2번을 절반만 지켰다.
- **오차를 재는 것도 지하철 트윈뿐이다.** 드레인 트윈은 "이렇게 될 것"이라고 말하지만,
  실제로 드레인한 뒤 그 예측이 맞았는지 되먹임하는 고리가 없다. 트윈에서 제일 중요한
  부분[^1]이 빠져 있는 셈이다.
- **이력이 얕다.** 셋 다 한 번의 요청 안에서만 살고 아무것도 축적하지 않는다. "지난달에
  이 노드를 뺐을 때 뭐가 일어났더라"에는 아직 답하지 못한다.

다음에 손볼 곳은 두 번째다. 드레인을 실제로 돌린 뒤의 결과를 다시 넣어 예측과 대조하는
고리를 붙이는 것. 그게 붙기 전까지 이건 **트윈이라기보다 잘 만든 계산기**다. 그 구분을
흐리지 않으려고 이 절을 남긴다.

---

## References

[^1]: Glaessgen, E. H., & Stargel, D. S. (2012). *The Digital Twin Paradigm for Future NASA and U.S. Air Force Vehicles.* AIAA Paper 2012-1818, 53rd AIAA/ASME/ASCE/AHS/ASC Structures, Structural Dynamics and Materials Conference. NASA Technical Reports Server: <https://ntrs.nasa.gov/citations/20120008178>
[^2]: 서울특별시. *서울시 지하철 실시간 도착정보* (서울 열린데이터광장, 교통정보과 TOPIS 제공). 데이터셋 안내의 주의사항 항목. <https://data.seoul.go.kr/dataList/OA-12764/F/1/datasetView.do>
[^3]: Kubernetes Documentation. *Disruptions.* <https://kubernetes.io/docs/concepts/workloads/pods/disruptions/>
[^4]: Kubernetes Documentation. *Specifying a Disruption Budget for your Application.* <https://kubernetes.io/docs/tasks/run-application/configure-pdb/>
[^5]: Fowler, M. *Event Sourcing.* martinfowler.com. <https://martinfowler.com/eaaDev/EventSourcing.html>
[^6]: Fowler, M. (2021). *Bitemporal History.* martinfowler.com. <https://martinfowler.com/articles/bitemporal-history.html>
[^7]: Fielding, R., Nottingham, M., & Reschke, J. (Eds.) (2022). *HTTP Semantics.* RFC 9110, §9.3.2 (HEAD). <https://www.rfc-editor.org/rfc/rfc9110.html#name-head>

*세 저장소(`twinkit`, `kube-drain-twin`, `replay-twin`)는 현재 비공개다. 본문의 출력은 모두
각 저장소에 내장된 고정 시드 합성 데이터를 실제로 돌린 결과이며, 운영 데이터가 아니다.*
