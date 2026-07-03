---
layout: post
title: "쿠버네티스 운영 을 *KPI* 로 말하기 — 6 노드 홈랩 을 지표 로 증명"
date: 2026-07-03 20:50:00 +0900
categories: [devops, kubernetes, k3s]
tags: [kubernetes, k3s, gitops, argocd, observability, sre, kpi, homelab]
---

"쿠버네티스 운영 잘 한다" 는 말 은 공허 하다. **무엇 을, 어떤 지표 로 개선 했는지** 가 있어야 한다. 이 글 은 내 6 노드 K3s 홈랩(75 ArgoCD 앱 / 60 namespace / 188 running pod) 을 **5 개 KPI** 로 나눠, 각각 을 *어떻게 측정 하고 어떻게 끌어올렸는지* 정리한다.

| KPI | 한 줄 | 도구 |
|---|---|---|
| 운영 효율 | 사람 손 없이 배포·복구 | ArgoCD · Helm |
| 운영 표준화 | 모든 앱 이 같은 방식 | Helm chart · SOPS |
| 서비스 안정성 | 죽기 전 에 알고, 죽어도 복구 | Prometheus · ELK · Velero |
| 장애 대응 | 반복 장애 를 0 으로 | 근본원인 튜닝 |
| 배포 리드타임 | 커밋 → 검증 된 프로덕션 | post-deploy E2E |

---

## ① 운영 효율 — *75 개 앱 을 혼자 굴린다*

홈랩 은 **운영자 가 나 하나** 다. 그래서 자동화 가 곧 생존이다.

- **GitOps 100%** — 75 개 앱 *전부* ArgoCD 자동 sync. 수동 `kubectl apply` 로 배포 하는 앱 은 0 개.
- `git push` → image build → ghcr → ArgoCD 픽업 → rollout 까지 *사람 개입 없음*.
- **100% 온프렘** — 클라우드 비용 $0. 노트북·맥미니·데스크탑 6 대 로 클라우드 급 워크로드.

📏 측정: "배포 1 건 에 드는 사람 손 시간" → *0*. "클러스터 재현 시간"(git 에서 복구) → 분 단위.

---

## ② 운영 표준화 — *모든 앱 이 같은 모양*

앱 마다 배포 방식 이 다르면 40 개 서비스 는 40 개 의 특수 케이스 가 된다. 그래서 *한 틀* 로 강제 한다.

- **Helm chart 표준** — 모든 앱 이 같은 chart 구조(`helm-deploy/charts/*`) + values 로 배포. 새 앱 추가 = 같은 패턴 복제.
- **ArgoCD Application** — 배포 정의 자체 를 선언적 YAML 로. syncPolicy 도 통일된 원칙(자동 sync + `prune:false`).
- **SOPS + age** — 시크릿 15 개 를 *전부 암호화* 해서 git 에. 앱 마다 제각각 secret 관리 하지 않음.

📏 측정: "새 서비스 온보딩 시간" → 기존 패턴 복제 로 단축. "설정 drift" → GitOps 라 *구조적 으로 0*.

---

## ③ 서비스 안정성 — *관측 3 층*

죽는 걸 못 막아도, *죽기 전 에 알고 죽어도 복구* 하면 안정 이다. 세 층 으로 본다:

- **메트릭** — Prometheus + Grafana (kube-prometheus-stack). 노드·pod 리소스 추세.
- **로그** — ELK (ES hot/warm/cold + Kibana). 초당 수십 건, ~1,500 만 건 색인.
- **상태 요약** — 직접 만든 대시보드(k3s.lemuel.co.kr) + uptime-kuma 로 외부 가용성 상시 감시.
- **백업** — Velero 로 볼륨·리소스 정기 백업.

📏 측정: "장애 감지 까지 시간(MTTD)" → 알림 으로 분 단위. "가동률" → uptime-kuma 로 99.x%.

---

## ④ 장애 대응 — *반복 장애 를 0 으로*

안정성 의 진짜 지표 는 "장애 가 없다" 가 아니라 **"같은 장애 가 반복 되지 않는다"** 다. 실제 사례:

- 🔥 **Velero node-agent OOMKilled 44 회 반복** → 원인(과다 병렬 파일 읽기) 진단 → 메모리 512Mi→2Gi + `KOPIA_PARALLEL_FILE_READS=2` 튜닝 → **0 회 안정화**
- 🔧 **재부팅 후 ufw 가 VXLAN 차단** → pod-to-pod 죽음 → 원인 파악 후 방화벽 정책 고정
- 🗄️ **etcd orphan member** → cluster-reset 후 재가입 절차 표준화(토큰 sync + 옛 member 강제 제거)

📏 측정: "동일 장애 재발 횟수" → 근본원인 수정 후 *0*. 44 → 0 처럼 **숫자 로 증명 되는 트러블슈팅**.

---

## ⑤ 배포 리드타임 — *커밋 에서 "검증 된" 프로덕션 까지*

빠른 배포 는 쉽다. 어려운 건 *빠르면서 안전한* 배포. 그래서 배포 뒤 에 **자동 품질 게이트** 를 뒀다:

- settlement 는 main 머지 → ArgoCD rollout → **운영 도메인(jen.lemuel.co.kr) 에 직접 Playwright E2E**.
- 단위테스트 가 못 잡는 nginx/CORS/JWT 통합 결함 을 배포 직후 *자동* 감지.
- image-updater 폴링 주기 를 고려한 대기(180s) 로 *옛 이미지 오탐* 방지.

📏 측정: "커밋 → 프로덕션 반영" 자동화 로 분 단위. "배포 실패 를 사용자 보다 먼저 감지" → E2E 게이트 로 확보.

---

## 한 줄 정리

쿠버네티스 운영 을 KPI 로 바꾸면 이렇게 말할 수 있다:

- **효율**: 75 앱 100% GitOps, 배포 사람손 0
- **표준화**: Helm+ArgoCD+SOPS 단일 틀
- **안정성**: 관측 3 층 + Velero 백업
- **장애대응**: OOM 44→0 같은 근본원인 수정
- **리드타임**: 배포 후 외부도메인 E2E 게이트

*"많이 돌린다"* 가 아니라 *"지표 로 나아졌다"* — 그게 운영 이다.

---

_시리즈: 다음 글 은 [정산 시스템 을 KPI 로](#) · [AI 를 KPI 로](#)._
