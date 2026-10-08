---
layout: post
title: "파수꾼이 '돈 문제'를 보안 경보로 받았을 때 — 원인은 맞혔고, 조치 초안은 '격리'였다"
date: 2026-10-08 19:40:00 +0900
categories: [Security, AI]
tags: [watchman, secops-agent, alert-triage, human-in-the-loop, prometheus, kubernetes, llm-agent]
---

이 블로그에서 **파수꾼(Watchman)**을 여러 번 다뤘다. 홈랩 K3s 클러스터의 경보를 받아 원인을 조사하고 조치를 **제안만** 하는 읽기 전용 SecOps 조사 에이전트다([설계 글](/2026/09/25/read-only-autonomous-secops-agent-execution-framework/)). 지난 글들은 같은 오탐 반복([26 번 조사](/2026/09/24/watchman-same-false-positive-26-times/)), 피드백 버튼의 의미([👍 174 번](/2026/10/04/watchman-thumbs-up-means-seen/)), 판정 재사용([♻️](/2026/10/06/watchman-verdict-reuse/))을 다뤘다.

이번 경보는 성격이 다르다. **보안 사건이 아니라 결제 문제**였다. 파수꾼이 이걸 어떻게 처리했는지 보면 이 구조에서 무엇이 잘 동작하고 무엇이 아직 거친지가 선명하게 드러난다.

> 경보 원문의 시크릿 이름·감사 로그 ID 같은 내부 식별자는 가렸다.

---

## 1. 경보: 품질 지표가 100% 를 찍었다

경보 이름은 `LemuelXrGoldenSetAbstainHigh` 다. 클러스터의 PrometheusRule 을 직접 열어 보면 정의는 이렇다.

```yaml
expr: grounding_goldenset_abstain_rate{job="lemuel-xr-backend"} > 0.5
for: 30m
summary: 근거성 골든셋 판정 불가 비율 …
```

`lemuel-xr` 백엔드는 정기적으로 **골든셋**(정답을 아는 평가 문항)을 돌려 생성 결과의 근거성(grounding)을 채점한다. 채점하지 못한 문항, 즉 "판정 불가(INCONCLUSIVE)" 비율이 30 분 넘게 50% 를 넘으면 이 경보가 울린다. 본래는 **품질 경보**다.

이번에는 그 비율이 **100%** 였다.

---

## 2. 파수꾼의 판단: 원인은 정확했다

파수꾼이 텔레그램으로 보낸 분류(요지)는 이렇다.

> **분류:** Gemini API 선불 크레딧 소진으로 임베딩 호출이 `402 Payment Required` 를 반환하고, 그래서 골든셋 임베딩이 전부 실패해 판정 불가 비율이 100% 에 도달함 (신뢰도 높음)

근거로는 같은 초에 연달아 찍힌 백엔드 로그 3 줄을 붙였다.

```text
WARN … EvaluateGroundingUseCase - 임베딩 실패 → INCONCLUSIVE (purpose=meditation):
402 Payment Required: "{ "error": { "code": 402,
"message": "Your prepayment credits are depleted. Please go to AI Studio at hxxps://ai[.]studio/projects …
```

이 판단이 좋은 이유는 세 가지다.

1. **경보 이름에 끌려가지 않았다.** 이름만 보면 "모델 품질 저하"로 읽힌다. 파수꾼은 로그에서 HTTP 402 를 찾아 **품질 문제가 아니라 결제 문제**라고 다시 분류했다. 품질 지표가 100% 를 찍는 건 대개 품질이 아니라 **측정 파이프라인이 죽었다**는 신호다.
2. **영향 범위를 넓혀 봤다.** 제안 1 에서 같은 API 키를 **AI·TTS 파드도 공유한다**고 짚었다. 임베딩만의 문제가 아니라 같은 키를 쓰는 기능 전체가 위험하다는 뜻이다.
3. **링크를 무력화했다.** 로그에 있던 URL 을 `hxxps://ai[.]studio` 로 바꿔 보냈다(defang). 경보 메시지 속 링크를 무심코 누르게 하지 않는, 보안 도구다운 습관이다.

그리고 스스로의 한계도 적었다.

> 확인한 증거 1/5 — 못 본 것: 파드 상태·스펙, 컨테이너 로그, 네임스페이스 이벤트, 워크로드 정의(변조 여부)

"신뢰도 높음"이라고 하면서도 **다섯 가지 증거 중 하나만 봤다**고 밝혔다. 판단과 증거 범위를 분리해 보고하는 이 형식이 사람이 결론을 검토할 때 가장 쓸모 있다.

---

## 3. 문제는 조치 초안이었다: 결제 문제에 '네트워크 격리'

같은 메시지 아래쪽에는 이런 조치 초안이 붙어 있었다.

```diff
@@ metadata.labels @@
+    watchman.io/quarantine: "true"
+++ networkpolicy/lemuel-xr-prod/watchman-quarantine (승인 시)
+spec: {podSelector: {matchLabels: {watchman.io/quarantine: "true"}},
+       policyTypes: [Ingress, Egress]}
```

백엔드 파드에 격리 라벨을 붙이고, 그 파드의 **인그레스·이그레스를 모두 막는** NetworkPolicy 를 만드는 초안이다. 침해가 의심되는 파드라면 표준적인 첫 조치다.

하지만 이번 원인은 **크레딧 소진**이다. 이 초안을 적용하면 어떻게 될까.

- 백엔드가 외부 API 를 아예 못 부른다. 크레딧을 충전해도 임베딩은 계속 실패한다.
- 인그레스도 막혀 **실서비스 요청까지 끊긴다.**
- 원래는 "평가 지표만 죽은" 사건이 **서비스 장애**로 커진다.

분류는 "결제 문제"로 정확했는데, 조치 초안은 그 분류와 상관없이 **경보가 붙은 파드를 격리하는 기본 템플릿**이 나온 것으로 보인다. 메시지 끝의 "킬체인 단계 미상"도 같은 맥락이다. 보안 사건이 아닌데 보안 사건 틀에 끼워 넣다 보니 생긴 빈칸이다.

### 그래서 '자동 실행 안 함'이 설계의 핵심이다

경보에는 다음 문구가 붙어 있었다.

> ⚠ 자동 실행 안 함 — 제안만. 판단·신고·격리는 사람이 한다.
> 📝 조치 제안 초안 — 텍스트뿐, 실행 경로 없음. 사람이 검토해 직접 적용 (적용 전 대상 되읽기·dry-run 먼저)

이번 사례가 이 원칙이 왜 필요한지 정확히 보여 준다. 만약 파수꾼이 "신뢰도 높음"이면 초안을 자동 적용하도록 설계돼 있었다면, **정확한 진단 + 잘못된 조치**가 그대로 서비스 장애가 됐을 것이다. 진단의 신뢰도와 조치의 적합성은 다른 축이다. 에이전트가 진단을 잘한다고 해서 조치 실행 권한까지 줄 근거는 되지 않는다.

---

## 4. 덤으로 보인 것: 경보가 꺼졌다고 해결된 게 아니다

이 글을 쓰면서 지금 상태를 다시 확인했다(2026-10-08 19:40 KST).

- 해당 경보는 **firing 상태가 아니다.**
- 백엔드 파드는 10 시간 전에 새로 떴다.
- `grounding_goldenset_abstain_rate` 의 현재 값은 **`NaN`** 이다.

`NaN > 0.5` 는 거짓이라 경보가 울리지 않는다. 새 파드가 아직 골든셋 평가를 한 번도 돌리지 않아 비율이 0/0 인 상태로 보인다. 즉 **경보가 사라진 건 크레딧이 충전돼서가 아니라 측정값이 없어서일 수 있다.** 크레딧 상태는 다음 평가 주기의 로그를 봐야 안다.

이건 파수꾼의 문제라기보다 경보 규칙 쪽의 사각지대다. 비율 지표 경보에는 **"측정이 멈췄다"를 따로 잡는 규칙**이 필요하다. 예를 들어 `absent()` 나 평가 실행 횟수 카운터의 증가 여부를 보는 식이다.

---

## 5. 고칠 것 세 가지

1. **조치 초안을 분류에 맞추기.** "결제/쿼터/외부 의존성 장애"로 분류되면 격리 대신 다음을 초안으로 낸다. 크레딧 충전 요청, 키 사용처 목록, 호출 빈도 제한, 실패 시 우아한 저하(graceful degradation). 격리 템플릿은 보안 분류일 때만 나오게 한다.
2. **사건 유형을 보안/운영으로 먼저 나누기.** 보안이 아닌 사건에 킬체인 단계를 묻지 않는다. "킬체인 미상"이라는 빈칸이 사람에게 불필요한 긴장을 준다.
3. **측정 정지 경보 추가.** 비율 경보 옆에 "평가가 N 시간 동안 한 번도 안 돌았다" 경보를 둔다. 품질 지표가 조용한 이유가 좋아져서인지 멈춰서인지 구분해야 한다.

---

## 정리

- 파수꾼은 품질 경보를 **결제 문제로 정확히 재분류**했다. 같은 키를 쓰는 다른 기능까지 영향 범위를 넓혔고, 자신이 본 증거가 1/5 뿐이라고도 밝혔다. 진단은 잘했다.
- 조치 초안은 분류와 무관한 **격리 템플릿**이었다. 적용했다면 평가 장애가 서비스 장애로 커졌을 것이다.
- 그래서 "제안만, 실행은 사람"이라는 선이 장식이 아니라 **필수 안전장치**다. 진단 신뢰도는 실행 권한의 근거가 아니다.

---

## References

1. Prometheus Docs, *Alerting rules*. <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>
2. Prometheus Docs, *Query functions — absent()*. <https://prometheus.io/docs/prometheus/latest/querying/functions/#absent>
3. Kubernetes Docs, *Network Policies*. <https://kubernetes.io/docs/concepts/services-networking/network-policies/>
4. MDN, *402 Payment Required*. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/402>
5. MyoungSoo7, *watchman-secops-agent* (해커톤 제출 스냅샷). <https://github.com/MyoungSoo7/watchman-secops-agent>
