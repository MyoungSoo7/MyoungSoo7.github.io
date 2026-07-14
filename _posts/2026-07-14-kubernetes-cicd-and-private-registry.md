---
layout: post
title: "쿠버네티스 CI/CD 와 Private Registry — push 한 줄 이 배포 되기 까지"
date: 2026-07-14 23:10:00 +0900
categories: [devops, kubernetes, cicd]
tags: [kubernetes, cicd, gitops, argocd, image-updater, ghcr, private-registry, github-actions, docker, deployment]
---

`git push` 한 줄 이 어떻게 클러스터 의 파드 로 바뀌는가. 그 사이 에 **CI(빌드·테스트)** 와 **CD(배포)**, 그리고 그 둘 을 잇는 **Private Registry** 가 있다. 이 글 은 온프레미스 K3s 에서 실제로 굴리는 파이프라인 — GitHub Actions → ghcr → ArgoCD Image Updater → K3s rollout → 외부 검증 — 을 흐름 대로 따라가며, 그 과정 에서 밟은 함정 들 을 정리 한다. ([6노드 클러스터 운영]({% post_url 2026-07-14-operating-a-6-node-onprem-k3s-cluster %}) 의 배포 층 에 해당 한다.)

---

## 0. 전체 그림

```
개발자 push
   │
   ▼  (CI) GitHub Actions
빌드 → 테스트 → 이미지 스캔 → 멀티스테이지 Docker build
   │
   ▼  push
Private Registry (ghcr.io) — main-<sha7> 태그
   │
   ▼  (CD) ArgoCD Image Updater 가 새 태그 감지
git 매니페스트 자동 갱신 → ArgoCD sync
   │
   ▼
K3s rollout (RollingUpdate)
   │
   ▼  외부 검증
실제 도메인 이 새 바이트 를 서빙 하는지 확인
```

핵심 은 **"git = 진실"** 이다. 사람 이 클러스터 에 직접 `kubectl apply` 하지 않는다. 원하는 상태 를 git 에 적고, 자동화 가 거기로 *수렴* 시킨다.

---

## 1. Private Registry — CI 와 CD 의 이음매

빌드 한 이미지 를 어딘가 에 둬야 클러스터 가 당겨 쓴다. 그 창고 가 레지스트리다. 왜 *private* 인가.

- **내 코드 는 남 이 못 당기게** — public 레지스트리 에 사내 이미지 를 올리면 코드·구성 이 새어 나간다.
- **`imagePullSecret`** — 클러스터 가 private registry 에서 당기려면 인증 이 필요하다. pull 전용 토큰 을 Secret 으로 두고 ServiceAccount 에 붙인다. (push 권한 은 CI 만, 클러스터 는 pull-only — 권한 분리.)
- **pull-through 미러** — 같은 이미지 를 노드마다 매번 외부 에서 당기면 느리고 rate limit 에 걸린다. 클러스터 안 에 **registry 미러(캐시)** 를 두면 첫 당김 이후 는 로컬 에서 나눠 갖는다. 온프레미스 에서 특히 체감 이 크다.

우리 는 GitHub 의 **ghcr.io** 를 private registry 로 쓰고, 클러스터 안 에 pull-through 미러 를 둔다.

---

## 2. CI — 빌드 만 하는 게 아니다

CI 의 임무 는 "이 커밋 이 배포 가능 한가" 를 *증명* 하는 것.

- **테스트 게이트** — 유닛·통합·아키텍처 규칙(ArchUnit 등). 실패 하면 이미지 를 안 만든다. (테스트 없이 이미지 만 뽑는 *긴급 빌드* 는 예외 경로 로 따로 둔다 — 뒤에서.)
- **이미지 스캔** — Trivy 로 CVE 스캔, 심각 취약점 은 차단.
- **멀티스테이지 Docker build** — 빌드 스테이지(무거운 SDK) 와 런타임 스테이지(슬림 JRE) 를 분리 해 최종 이미지 를 작게. 모노-MSA 라면 `--build-arg MODULE=` 로 한 Dockerfile 에서 여러 서비스 이미지 를 뽑기도 한다.
- **태그 전략 이 핵심** — `latest` 는 *무엇 이 떠 있는지 모르게* 만든다. 커밋 SHA 로 고정(`main-<sha7>`) 하면 "지금 운영 에 뜬 게 정확히 어느 커밋" 인지 가 1:1 로 추적 된다. 롤백 도 태그 하나 로.

---

## 3. CD — GitOps 로 당긴다(push 가 아니라 pull)

전통적 CD 는 CI 가 클러스터 에 *밀어넣었다*(push). GitOps 는 반대다 — 클러스터 안 의 **ArgoCD 가 git 을 지켜보다 스스로 당긴다**(pull).

- **ArgoCD** — git 매니페스트 = 목표 상태. 실제 클러스터 가 어긋나면(drift) `selfHeal` 로 되돌린다. 누가 손 으로 바꿔도 원복 → *무결성* 이 유지 된다.
- **Image Updater** — CI 가 새 이미지(`main-<sha7>`) 를 push 하면, Image Updater 가 레지스트리 를 폴링 해 새 태그 를 감지 하고 **git 매니페스트 의 이미지 태그 를 자동 커밋** → ArgoCD 가 sync → rollout. 개발자 는 코드 만 push 하면 나머지 가 자동 으로 흐른다.
- **RollingUpdate** — 새 파드 가 Ready 될 때까지 옛 파드 를 유지 → 무중단.

---

## 4. 실전 에서 밟은 함정 들

교과서 흐름 은 위 대로 다. 하지만 현장 은 늘 어긋난다.

**① newest-build 태그 경합.** 두 배포 가 거의 동시 에 나가면, Image Updater 가 *더 최신 태그* 를 고르는 규칙 때문 에 **먼저 낸 fix 가 나중 빌드 에 묻혀** 배포 가 안 되는 사고 가 난다. "머지 했는데 왜 안 바뀌지?" 의 흔한 정체. → 배포 는 직렬화 하거나, 무엇 이 실제로 떴는지 를 *태그 로 확인* 해야 한다.

**② 프론트/백엔드 skew.** paths-filter 로 "바뀐 쪽 만 빌드" 하면 CI 는 빨라지지만, 프론트 만 배포 되고 백엔드 는 옛 버전 이 남아 *계약 이 어긋나는* 스큐 가 생긴다. 없는 API 경로 를 프론트 가 부르면 500. → 계약 이 바뀌는 배포 는 양쪽 을 함께.

**③ 빌드타임 에 박히는 값.** 예: `NEXT_PUBLIC_*` 는 *빌드 시점* 에 번들 에 inline 된다. 잘못된 도메인 이 박히면 런타임 env 를 아무리 바꿔도 안 고쳐지고, 운영 화면 이 빈 채로 뜬다. → 빌드 ARG 와 런타임 env 의 경계 를 정확히 알아야 한다.

**④ 내부 신호 만 믿지 마라.** "ArgoCD Healthy · API 200" 은 *클러스터 내부* 관점 이다. 정작 사용자 가 보는 도메인 이 **옛 바이트 를 서빙** 하고 있을 수 있다(캐시·CDN·미러 지연). → 배포 검증 은 실제 공개 도메인 의 *served bytes* 까지 외부 에서 확인.

---

## 5. 긴급 경로 — 안전장치 는 *우회 가능* 해야

정상 파이프라인 은 테스트 게이트 를 통과 해야 이미지 가 나온다. 그런데 CI 가 *인프라 사정*(러너 행, 무관 한 flaky 테스트) 으로 막혔는데 **운영 스큐 를 당장 풀어야** 할 때 가 있다.

이럴 때 를 위해 *테스트 skip* 하는 **긴급 이미지 빌드** 를 수동 dispatch 전용 으로 둔다. 정상 태그 규칙 그대로 이미지 만 뽑아 Image Updater 가 픽업 하게. — 단, 이건 "코드 신뢰 도 는 직전 CI/로컬 검증 으로 판단" 한다는 전제 의 *비상구* 다. 비상구 를 상시 문 처럼 쓰면 게이트 가 무의미 해진다.

> 얼마 전 실제로, 무관 한 flaky 테스트 가 CI 를 막아 검증 끝난 fix 가 배포 못 되던 상황 에서 이 긴급 빌드 로 먼저 내보내고, flaky 는 별도 로 고쳐 정상 게이트 를 복구 했다. *비상구 는 있되, 반드시 정상 문 을 다시 연다.*

---

## 정리

- **git = 진실** — push 가 아니라 GitOps pull(ArgoCD) 로 수렴.
- **Private Registry** — pull-only 권한 분리 + pull-through 미러.
- **태그 는 SHA 로** — 무엇 이 떴는지 1:1 추적, 롤백 도 한 줄.
- **CI 는 증명** — 테스트·스캔 게이트 통과 한 것 만 이미지화.
- **함정** — 태그 경합·프론트백 skew·빌드타임 inline·내부신호 맹신.
- **비상구 는 두되 상시화 하지 마라.**

`git push` 한 줄 뒤 에 이 만큼 이 자동 으로 돈다는 것 — 그게 잘 설계 된 파이프라인 의 힘 이다. 그리고 그 자동화 를 *믿되 외부 에서 검증* 하는 습관 이, 조용한 배포 사고 를 막는다.

---

*파이프라인 구체 는 사용하는 CI(Actions/GitLab)·CD(ArgoCD/Flux)·레지스트리 에 따라 다르다. 이 글 은 특정 리포 의 시크릿·토큰 을 담지 않으며, 흐름 과 원칙 위주 다.*
