---
layout: post
title: "외부 IP 없이 집 클러스터 를 공개 하기 — 홈랩 K3s 를 프로덕션 처럼 운영 한다는 것"
date: 2026-07-14 23:40:00 +0900
categories: [devops, kubernetes, homelab]
tags: [kubernetes, k3s, cloudflare-tunnel, homelab, ingress, gitops, observability, operations]
image: /assets/images/k3s-cluster-overview-live-services.jpg
---

집 에 있는 K3s 클러스터 가 실제 도메인 으로 서비스 를 *공개* 한다. 공인 IP 도 없고, 공유기 에 포트포워딩 도 안 한다. 그런데 어떻게 인터넷 에서 접속 이 될까. 이 글 은 그 "한 장 요약" 을 뜯어보며, **홈랩 을 프로덕션 처럼 운영 한다** 는 게 구체적 으로 무슨 뜻 인지 를 정리 한다.

![K3s Cluster 개요 — 6/6 Ready 노드, 60 네임스페이스, 330+ 파드, GitOps(ArgoCD)·GitHub Actions 배포, Prometheus·Grafana·ELK 관측, Cloudflare Tunnel 인그레스. 그리고 lemuel.co.kr·jen.co.kr 등 공개 서비스 목록](/assets/images/k3s-cluster-overview-live-services.jpg)

한 장 에 다 있다 — **6노드 / 60 네임스페이스 / 330+ 파드**, 배포 는 GitOps, 관측 은 Prometheus·Grafana·ELK, 그리고 인그레스 는 **Cloudflare Tunnel (외부 IP 없이 공개)**. 그 밑 으로 실제 서비스 도메인 들 이 붙어 있다.

---

## 1. 핵심 트릭 — Cloudflare Tunnel, "외부 IP 없이 공개"

홈랩 을 인터넷 에 여는 전통적 방법 은 *공유기 포트포워딩* 이다. 그런데 이건:

- 공인 IP 가 필요 하고(가정용 은 유동 IP 라 불안정),
- 공유기 에 구멍 을 뚫는 순간 **전 세계 스캐너 의 표적** 이 되고,
- 내 홈 네트워크 의 실제 IP 가 노출 된다.

**Cloudflare Tunnel** 은 이 방향 을 뒤집는다. 클러스터 안 의 `cloudflared` 가 Cloudflare 로 **바깥쪽 으로(outbound)** 만 연결 을 연다. 외부 트래픽 은 Cloudflare 엣지 로 들어와 그 터널 을 타고 내 클러스터 로 들어온다.

- **인바운드 포트 를 하나도 안 연다** — 공유기 방화벽 은 닫힌 채. 열린 구멍 이 없으니 스캔·직접 공격 표면 이 사라진다.
- **공인 IP 불필요** — 유동 IP·CGNAT 뒤 에 있어도 된다.
- **홈 IP 은닉** — 방문자 는 Cloudflare IP 만 본다. 내 집 주소 는 안 보인다.
- 덤 으로 Cloudflare 의 TLS·DDoS 완충·WAF 를 공짜 로 얹는다.

즉 "외부 IP 없이 공개" 는 마법 이 아니라, **공개 방향 을 inbound→outbound 로 뒤집은** 것 이다. 홈랩 보안 의 [7개 층]({% post_url 2026-07-14-kubernetes-security-onprem-layers %}) 중 API·인그레스 노출 을 근본적 으로 줄이는 선택 이다.

> 인그레스 흐름: `사용자 → Cloudflare 엣지 → (터널) → cloudflared → K8s Service → 파드`. 터널 자격증명(토큰·UUID) 은 SOPS 로 암호화 해 git 에 둔다 — *공개 는 하되 열쇠 는 안 흘린다.*

---

## 2. 서비스 카탈로그 — 공개 서비스 vs 내부 운영 도구

한 클러스터 가 성격 이 다른 두 종류 를 함께 서빙 한다.

**공개 서비스(제품).** 실제 사용자 가 쓰는 것.

| 서비스 | 역할 |
|---|---|
| 메인 홈페이지 | 랜딩 |
| 정산 서비스 | 결제·정산 도메인 |
| 이커머스 AI 챗 | 상품·챗 |
| 청각재활 서비스 | 도메인 앱 |

**내부 운영 도구(플랫폼).** 나를 위한 것 — 클러스터 를 *굴리는* 콘솔.

| 도구 | 역할 |
|---|---|
| ArgoCD | GitOps 배포 상태 |
| K8s Dashboard | 클러스터 리소스 |
| Grafana | 메트릭 모니터링 |
| Kibana | 로그 분석(ELK) |

운영 관점 에서 이 둘 은 **노출 정책 이 달라야** 한다. 제품 은 공개, 운영 콘솔(ArgoCD·Dashboard·Grafana·Kibana) 은 인증 뒤 로 숨기거나 접근 을 제한 한다 — 대시보드 하나 가 열려 있으면 클러스터 내부 가 통째로 들여다 보인다. Cloudflare Access(또는 앱 자체 인증) 로 운영 도구 앞 에 문 을 하나 더 둔다.

---

## 3. 그 공개 를 *지탱* 하는 세 기둥

도메인 이 떠 있다 = 그 뒤 에 이걸 굴리는 자동화 가 있다 는 뜻.

- **배포 — GitOps(ArgoCD) + GitHub Actions.** push → 빌드 → 레지스트리 → ArgoCD 가 당겨 rollout. 사람 이 클러스터 를 손 으로 안 만진다. (자세히는 [CI/CD 와 Private Registry]({% post_url 2026-07-14-kubernetes-cicd-and-private-registry %}))
- **관측 — Prometheus · Grafana · ELK.** 메트릭 은 Prometheus→Grafana, 로그 는 Fluent Bit→Logstash→Elasticsearch→Kibana. "무슨 일 이 어디서 나는가" 를 상시 본다.
- **토폴로지 — 6노드 이기종 배치.** 어느 워크로드 를 어느 노드 에 둘지 가 홈랩 운영 의 핵심. (자세히는 [6노드 클러스터 운영]({% post_url 2026-07-14-operating-a-6-node-onprem-k3s-cluster %}))

이 셋 이 없으면 "집 서버 에 도커 몇 개 띄운 것" 이고, 있으면 **프로덕션** 이다. 차이 는 규모 가 아니라 *운영 이 자동화·관측·선언 으로 굴러가느냐* 다.

---

## 4. 홈랩 을 프로덕션 처럼 — 왜?

60 네임스페이스, 330 파드 를 집 에서 굴리는 게 과할까. 하지만 얻는 게 크다.

- **실제 문제 를 실제 로 만난다** — 노드 메모리 압박, OOM 루프, 배포 경합, 인증서 만료. 튜토리얼 이 아니라 *운영* 을 한다.
- **엔드투엔드 를 다 진다** — 매니지드 클라우드 가 대신 해주던 컨트롤플레인·네트워크·백업 을 내가 다 짊어지니, 각 층 이 어떻게 맞물리는지 가 몸 에 붙는다.
- **비용 은 전기세** — 노트북·데스크탑·중고 맥미니 로 3-master HA 를.

"외부 IP 없이 공개" 한 줄 뒤 에 이 만큼 이 서 있다. 홈랩 이지만 운영 의 원리 는 규모 와 무관 하다 — 오히려 *제약 이 많은 환경* 이라 무엇 이 본질 인지 가 더 선명 하게 드러난다.

---

## 정리

- **Cloudflare Tunnel** = 공개 방향 을 inbound→outbound 로 뒤집어, *포트 를 안 열고·공인 IP 없이·홈 IP 은닉* 하며 공개.
- **공개 서비스 와 운영 콘솔 은 노출 정책 을 분리** — 대시보드 는 인증 뒤 로.
- 공개 를 지탱 하는 건 **GitOps 배포 · 관측 스택 · 이기종 토폴로지** 세 기둥.
- 홈랩 을 프로덕션 처럼 = 규모 가 아니라 **자동화·관측·선언** 으로 굴린다는 것.

---

*터널 자격증명·도메인 별 라우팅 등 민감 설정 은 이 글 에 담지 않는다. Cloudflare Tunnel 구성 은 공식 문서(cloudflared / Zero Trust) 로 확인 하는 게 정확 하다.*
