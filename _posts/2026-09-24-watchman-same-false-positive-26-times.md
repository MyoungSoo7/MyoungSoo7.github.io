---
layout: post
title: "파수꾼 관제 90분 — AI 보안 분석가는 같은 오탐을 26번 조사했다"
date: 2026-09-24 02:55:00 +0900
categories: [security]
tags: [ai-agent, falco, soc, alert-triage, llm, kubernetes]
---

우리 클러스터의 보안 알림은 사람보다 먼저 AI 에이전트 **파수꾼(Watchman)** 이 받는다.
알림은 [Falco](https://falco.org/docs/) 런타임 탐지와 Prometheus 경보에서 온다. 파수꾼은 알림마다
로그와 상태를 직접 조회해 증거를 모으고, 정상인지 위협인지 분류한 뒤 사람에게 카드로 보낸다.
동작 현황은 [공개 관제 뷰](https://security.lemuel.co.kr/)에서 읽기 전용으로 볼 수 있다.

이번에는 관제 뷰에 남아 있는 최근 기록 50건을 뜯어봤다. 시간으로는 약 90분
(2026-09-24 01:35–03:05 KST)이다. **일주일치가 아니라 90분짜리 스냅샷**이라는 점을 먼저 밝혀 둔다.

## 결과

- 50건 중 45건 완료, 1건 부분 결과(LLM 응답 시간 초과), 3건 복구 필요, 1건 진행 중
- 실제 위협으로 판정한 건: **0건**
- 분석 1건당 소요시간 중앙값: **84초**

## 잘한 것

- CI 러너 컨테이너에서 "BPFDoor 백도어 패턴" 알림이 떴다. 파수꾼은 이것이
  [Docker-in-Docker](https://hub.docker.com/_/docker) 데몬의 정상적인 소켓 필터 동작이고, 해당 파드는
  이미 종료된 일회성 [GitHub Actions 러너](https://github.com/actions/actions-runner-controller)라는
  근거로 오탐 판정했다.
- 호스트에서 `/etc/shadow` 를 읽었다는 알림([`Read sensitive file untrusted`](https://github.com/falcosecurity/rules/blob/main/rules/falco_rules.yaml))은
  예약된 보안 감사 도구의 정기 점검이었다. 파수꾼은 이것을 cron 기록에서 찾아냈다.

## 못한 것 — 이번 글의 진짜 주제

50건 중 **29건이 같은 알림**이었다. DB 컨테이너가 [초기화(initdb)](https://www.postgresql.org/docs/current/app-initdb.html)
중에 로케일을 확인하려고 셸을 한 번 띄우는 정상 동작이, Falco 기본 규칙
[`Run shell untrusted`](https://github.com/falcosecurity/rules/blob/main/rules/falco_rules.yaml)에 걸린 것이다.

파수꾼은 그중 완료된 26건을 **매번 처음 보는 것처럼** 새로 조사했고, 결론은 26번 모두 사실상 같았다.

| 항목 | 값 |
|---|---|
| 같은 오탐 조사 횟수 (완료) | 26건 |
| 사용 토큰 | 약 35만 / 전체 48만 (**73%**) |
| 누적 분석 시간 | 약 46분 |
| 신뢰도 분포 (같은 사건) | 높음 6 · 중간 17 · 낮음 3 |

마지막 줄이 특히 아프다. 같은 사건, 같은 결론인데 신뢰도가 매번 달랐다. 증거가 달라서가 아니라
매번 처음부터 추론했기 때문이다.

## 다음 할 일

"이미 판정한 것과 같은 알림"을 알아보는 기억, 즉 **중복 억제**가 필요하다. 알림의 지문(규칙 + 프로세스 계보 +
워크로드 종류)이 최근 판정과 일치하면, 새로 조사하지 않고 이전 판정을 참조해 짧게 확인만 하는 식이다.

에이전트가 얼마나 똑똑한지만큼 중요한 건, **같은 걸 두 번 생각하지 않는가**이다.

---

- 사용 모델: NVIDIA Nemotron 3 계열 (관제 뷰에 표시되는 값 기준)
- 수치는 모두 파수꾼 관제 뷰의 최근 50건 기록을 직접 집계한 것이다. 네임스페이스·노드·파드 이름과
  탐지 규칙 세부 조건은 공개하지 않는다.

## References

- 파수꾼 공개 관제 뷰 — <https://security.lemuel.co.kr/> (이 글 수치의 1차 출처)
- Falco 공식 문서 — <https://falco.org/docs/>
- Falco 기본 규칙 (`Run shell untrusted`, `Read sensitive file untrusted`) — <https://github.com/falcosecurity/rules/blob/main/rules/falco_rules.yaml>
- PostgreSQL `initdb` 문서 — <https://www.postgresql.org/docs/current/app-initdb.html>
- Docker 공식 이미지 (dind) — <https://hub.docker.com/_/docker>
- Actions Runner Controller — <https://github.com/actions/actions-runner-controller>
