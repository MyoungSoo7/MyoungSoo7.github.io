---
layout: post
title: "2026-10-10 데일리 AI·Kubernetes·클라우드 기술 브리핑"
date: 2026-10-10 08:30:17 +0900
categories: [AI, Kubernetes, Cloud, Security]
tags: [Claude, LangGraph, Devin, Kubernetes, CISA, Python, Linux, Jev]
---

> **수집 시각:** 2026-10-10 08:30 KST · **범위:** 2026-10-09~10 공개 자료 중심
>
> 공식 문서·프로젝트 릴리스·벤더 공지를 우선 확인했다. 확인하지 못한 항목은 출시 사실처럼 쓰지 않고 별도 표기한다.

## 오늘의 결론

1. **AI 모델 경쟁의 실무 축은 성능만이 아니라 비용·속도·안전한 실행 경계다.** Anthropic은 Opus 5.5와 Haiku 5.5를 연이어 공개했고, 사이버 보안용 접근은 별도 검증 프로그램으로 분리했다.
2. **Kubernetes 업그레이드의 핵심은 cgroup v2와 메모리 동작의 사전 검증이다.** v1.37은 Memory QoS를 Beta·기본 활성화했지만, 실제 throttling과 reservation은 설정 여부에 따라 달라진다.
3. **보안 대응은 KEV의 실제 악용·기한·포렌식 요구를 자산 노출과 연결해야 한다.** CISA는 10월 8일 ProFTPD와 ONLYOFFICE Docs를 KEV에 추가했고 두 항목 모두 10월 11일 기한을 제시한다.
4. **Jev는 생성 모델이 아니라 결정 경계다.** 텍스트를 생성하지 않고 typed answer와 확률을 반환하므로, 허용·검토·거부 라우팅에 적합하지만 임계값과 fail-closed 정책이 필수다.

## 1. AI & Machine Learning

### Claude Opus 5.5·Haiku 5.5: 비용과 실행 경계의 분리

Anthropic 공식 Newsroom 기준 Claude Opus 5.5는 2026년 9월 22일, Claude Haiku 5.5는 10월 7일 공개됐다. Anthropic은 Opus 5.5를 이전 Opus 5보다 40% 저렴한 모델로, Haiku 5.5를 고속·저비용·고처리량 용도의 소형 모델로 소개한다.

또한 10월 6일 공개된 Cyber Verification Program은 일반 모델 사용과 별도로, 심사를 거친 보안 전문가에게 방어·레드팀 작업 수준에 따른 접근 계층을 제공한다. 이는 모델 능력과 도구 권한을 하나의 “기본 허용”으로 묶지 않고, 사용자·목적·실행 범위별로 분리하는 운영 패턴이다.

**실무 해석:** 에이전트 설계에서 모델 선택은 `quality × latency × cost`의 문제인 동시에, 브라우저·셸·네트워크·자격증명 권한을 어디까지 부여할지의 문제다. 모델 교체 전에는 SDK 호환성, thinking 설정, 도구 승인 콜백, 감사 로그를 함께 회귀 테스트해야 한다.

- 출처: [Anthropic Newsroom](https://www.anthropic.com/news)
- 출처: [Claude Opus 5.5](https://www.anthropic.com/claude-opus-5-5)
- 출처: [Expanding the Cyber Verification Program](https://www.anthropic.com/news/cyber-verification-program)

### ML/DL 연구·신경과학·BCI

이번 수집 범위에서는 BCI 또는 신경과학 분야의 새로운 1차 발표를 공식 원문으로 교차검증할 만한 항목을 확인하지 못했다. 따라서 성능 돌파구를 추정하지 않는다. BCI 주장은 피험자 수, 온라인/오프라인 평가, 지연시간, 사용자 간 일반화, 대조군을 함께 확인해야 한다.

## 2. AI 에이전트 프레임워크

### LangGraph 1.2.14와 CLI 0.4.33

공식 GitHub 릴리스에서 LangGraph 1.2.14는 10월 6일, LangGraph CLI 0.4.33은 10월 7일 공개됐다. CLI 변경에는 이미 푸시된 이미지를 배포하는 `--image-uri`, 배포 listener 조회 명령, credential-bearing Git dependency 거부 수정이 포함됐다.

**운영 포인트:** 소스 빌드와 이미지 배포를 혼합하지 말고 이미지 digest를 고정한다. Git dependency URL에 자격증명이 들어가는 경로는 개발 PC뿐 아니라 CI 정책에서도 차단해야 한다.

- 출처: [LangGraph releases](https://github.com/langchain-ai/langgraph/releases)

### Devin: 알림·터미널·리뷰 거버넌스 강화

Devin 공식 2026 릴리스 노트는 10월 7일 Notification Inbox를 추가했다. 세션 완료·사용자 주의 필요 이벤트를 모으고 모바일 알림 여부를 설정할 수 있다. 같은 릴리스 노트에는 Command Palette 정비, merge queue 상태 표시, private key 문자열의 명령 출력 마스킹 강화, Teams/Slack 보안 프로파일 조정이 기록돼 있다.

**실무 해석:** 장기 실행 에이전트는 “작업을 시작했는가”보다 “완료·대기·승인 필요 상태를 운영자가 놓치지 않는가”가 중요하다. 알림 이벤트와 실제 세션 상태·PR 상태를 별도 trace로 저장해야 한다.

- 출처: [Devin 2026 Release Notes](https://docs.devin.ai/release-notes/2026)

### CrewAI

이번 수집 범위에서 CrewAI의 신규 변경을 공식 릴리스 원문으로 충분히 교차검증하지 못했다. 따라서 버전이나 기능을 추정하지 않는다. 도입·업그레이드 시에는 공식 release, 의존성 advisory, 평가 trace를 함께 고정해 확인한다.

## 3. Kubernetes & Cloud Native

### Kubernetes v1.36/v1.37: cgroup v2·Memory QoS

Kubernetes 공식 문서는 cgroup v1을 deprecated로 설명하며, v1.35부터 `failCgroupV1` 기본값이 `true`여서 cgroup v1 노드에서 kubelet이 시작되지 않을 수 있다고 안내한다. v1.36에서는 cgroup v2 기반 Memory QoS와 tiered memory protection이 계속 중요한 실험·운영 검토 항목이다.

v1.37에서는 Memory QoS가 Beta이고 feature gate가 기본 활성화됐다. 다만 `memoryThrottlingFactor` 기본값이 `null`이므로 명시적으로 설정하지 않으면 `memory.high` throttling이 자동으로 적용되지 않는다. `memoryReservationPolicy: TieredReservation`을 설정하면 `memory.min`·`memory.low` 예약이 활성화되며, 노드의 모든 Pod에 영향을 준다.

**업그레이드 전 점검:**

```bash
kubectl get nodes -o wide
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{" cgroup="}{.status.nodeInfo.containerRuntimeVersion}{"\n"}{end}'
kubectl get --all-namespaces pods -o yaml | grep -nE 'gitRepo|configMapRef|secretRef'
```

위 명령만으로 cgroup 모드나 실제 kubelet 설정을 확정할 수는 없다. 노드 OS의 `/sys/fs/cgroup` 형태, kubelet 설정, CRI·OCI 런타임, staging 부하 테스트를 함께 확인해야 한다.

- 출처: [The Shift to cgroup v2 in Kubernetes](https://kubernetes.io/blog/2026/10/06/kubernetes-cgroups-v2-shift/)
- 출처: [Kubernetes v1.37 Memory QoS Beta](https://kubernetes.io/blog/2026/09/14/kubernetes-v1-37-memory-qos-graduates-to-beta/)
- 출처: [Kubernetes v1.37 Sneak Peek](https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/)

## 4. 사이버 보안

CISA KEV 공식 카탈로그는 10월 8일 다음 항목을 추가했다.

| 항목 | 영향 | 추가일 | 기한 | 추가 대응 |
| --- | --- | --- | --- | --- |
| ProFTPD CVE-2015-3306 | 임의 파일 읽기·쓰기 가능성이 있는 접근 제어 취약점 | 2026-10-08 | 2026-10-11 | 포렌식 triage 필요 |
| ONLYOFFICE Docs CVE-2021-3199 | JWT 사용 시 경로 순회 및 원격 코드 실행 가능성 | 2026-10-08 | 2026-10-11 | 포렌식 triage 필요 |

**운영 순서:** 인터넷 노출 자산과 버전을 먼저 대조하고, 패치 전후 계정·프로세스·파일 무결성·접근 로그를 보존한다. 패치 완료는 침해 부재의 증명이 아니므로 KEV의 포렌식 요구를 별도로 처리한다.

- 출처: [CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)

## 5. Cloud Service Provider

- **AWS:** AWS Weekly Roundup은 OpenAI Agents API 기반 Amazon Bedrock Managed Agents 공개 프리뷰를 소개했다. AWS 리소스와 identity·permission·governance 통합이 핵심이며, 별도로 AWS Well-Architected Agent 프리뷰도 공개됐다.
- **Google Cloud:** 이번 수집에서 10월 9일 기준 특정 신규 기능을 상세한 공식 원문으로 확정하지 못했다. Google Cloud What’s New를 기준으로 리전·GA/Preview 상태를 재확인해야 한다.
- **Azure:** 같은 기준으로 Azure의 10월 9일 신규 GA 항목을 충분히 교차검증하지 못했다. Azure Announcements와 Microsoft Foundry 변경을 실제 배포 리전과 함께 확인해야 한다.
- **Naver Cloud:** 이번 범위에서 제품 GA·API SLA로 확정할 신규 항목을 확인하지 못했다. 협력·컨소시엄 발표를 제품 출시로 해석하지 않는다.

**공통 해석:** 클라우드 에이전트는 모델 API보다 identity, permission boundary, 실행 로그, 비용·보안 평가가 운영 품질을 결정한다.

- 출처: [AWS News Blog](https://aws.amazon.com/blogs/aws/)
- 출처: [Google Cloud What’s New](https://cloud.google.com/blog/topics/inside-google-cloud/whats-new-google-cloud)
- 출처: [Azure Announcements](https://azure.microsoft.com/en-us/blog/content-type/announcements/)
- 출처: [NAVER Cloud 보도자료](https://www.navercorp.com/en/media/pressReleases?keyword=NAVERCLOUD)

## 6. 개발 언어·프론트엔드

- **Python:** Python Insider는 10월 9일 Python 3.15.0 정식 출시를 발표했다. 3.15 도입 전에는 C 확장, typing, free-threading 관련 의존성의 호환성을 검증한다.
- **Rust:** Python Language Summit 2026에서 Rust for CPython 진행 상황과 Python-to-Rust transpiler Spicycrab이 소개됐다. 이는 공식 Rust 안정 릴리스가 아니라 CPython 생태계의 개발 방향·실험 신호다.
- **React/Vue:** 이번 범위에서 React·Vue의 신규 공식 릴리스 또는 보안 공지를 확정하지 못했다.
- **Java/Kotlin/JavaScript/TypeScript:** 이번 범위에서 각 프로젝트의 당일 변경을 1차 출처로 확정하지 못했다. 운영 업그레이드는 프로젝트 공식 release note와 CVE를 기준으로 별도 검증한다.

- 출처: [Python Insider 2026 posts](https://blog.python.org/blog/year/2026/)
- 출처: [Python 3.15.0 final](https://blog.python.org/2026/10/python-3150-final-is-here)
- 출처: [Rust Blog](https://blog.rust-lang.org/)

## 7. Infrastructure & Linux

Linux Kernel Archives는 10월 4일 기준 mainline `7.3-rc6`, stable `7.2.9`, longterm `6.18.55`, `6.12.112`, `6.6.158`, `6.1.189`, `5.15.222`, `5.10.271`을 표시하며, 10월 8일 linux-next는 `next-20261008`이다.

RC와 linux-next는 일반 운영 노드의 기본 선택지가 아니다. 커널 업그레이드는 배포판 패치 레벨, eBPF·스토리지·네트워크 드라이버, CRI 런타임, Kubernetes cgroup 모드 조합을 staging에서 확인한 뒤 진행한다.

- 출처: [Linux Kernel Archives releases.json](https://www.kernel.org/releases.json)

## 8. Special Section — Jev API 및 의사결정 모델

Jev API 문서 기준 hosted endpoint는 `POST https://jev-api.org/api/v1/decisions`이며, `state`와 typed `questions`를 받아 `noul`, `choice`, `score` 형태의 구조화된 답을 반환한다. 이 endpoint의 문서상 모델 ID는 `jev-1.13` 또는 `jev-latest`이고, 질문은 1~6개, Choice 선택지는 2~8개, state는 최대 60,000자다. TypeSafe 자체 API인 `POST https://api.typesafe.ai/v1/systemone`과는 endpoint·키·제한·과금이 다르므로 혼동하지 않는다.

### 권장 실행 경계

```text
관측 이벤트
  → Jev: allow / review / deny 또는 route 결정
  → 정책 엔진: 임계값·권한·가역성 확인
  → 사람 승인 또는 제한된 도구 실행
  → 결과·근거·모델 버전·입력 해시 기록
```

Jev 확률을 곧바로 자동 실행 조건으로 사용하지 않는다. 1위·2위 선택지가 가깝거나 결과가 임계값 주변이면 사람 검토로 보낸다. 호출 실패·429·502·스키마 오류는 **deny 또는 fail-closed**로 처리하고, `jev-latest` alias를 사용하는 경우에도 감사 로그에 실제 응답 모델과 정책 버전을 남긴다.

**결정 모델의 역할:** LLM이 생성·도구 선택을 담당한다면 Jev는 승인·분류·라우팅·위험도 점수라는 좁은 판정 경계를 담당한다. 이 분리는 유창한 생성 결과를 실행 허용으로 오인하는 사고를 줄인다.

- 출처: [Jev API Reference](https://jev-api.org/docs)
- 출처: [TypeSafe System One](https://docs.typesafe.ai/concepts/system-one)

## 내일 확인할 것

- Claude 5.5 계열 SDK의 모델·thinking 설정 마이그레이션 실측
- Kubernetes v1.37 cgroup v2·Memory QoS의 실제 노드 설정과 부하 결과
- CISA KEV 10월 11일 기한 항목의 자산 노출·포렌식 처리 상태
- LangGraph 이미지 digest 배포와 credential-bearing dependency 차단의 CI 적용
- Jev 결정 결과와 정책 엔진의 fail-closed·재검토 기준

## 참고 자료

1. [Anthropic Newsroom](https://www.anthropic.com/news)
2. [Anthropic Cyber Verification Program](https://www.anthropic.com/news/cyber-verification-program)
3. [LangGraph releases](https://github.com/langchain-ai/langgraph/releases)
4. [Devin 2026 Release Notes](https://docs.devin.ai/release-notes/2026)
5. [Kubernetes cgroup v2](https://kubernetes.io/blog/2026/10/06/kubernetes-cgroups-v2-shift/)
6. [Kubernetes v1.37 Memory QoS](https://kubernetes.io/blog/2026/09/14/kubernetes-v1-37-memory-qos-graduates-to-beta/)
7. [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
8. [AWS News Blog](https://aws.amazon.com/blogs/aws/)
9. [Python Insider](https://blog.python.org/blog/year/2026/)
10. [Linux Kernel Archives](https://www.kernel.org/releases.json)
11. [Jev API Reference](https://jev-api.org/docs)
12. [TypeSafe System One](https://docs.typesafe.ai/concepts/system-one)
