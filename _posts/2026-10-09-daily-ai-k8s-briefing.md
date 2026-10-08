---
layout: post
title: "2026-10-09 데일리 AI·Kubernetes·클라우드 기술 브리핑"
date: 2026-10-09 08:31:25 +0900
categories: [AI, Kubernetes, Cloud, Security]
tags: [Claude, LangGraph, CrewAI, Kubernetes, CISA, Jev, Linux]
---

> **수집 시각:** 2026-10-09 08:31 KST · **범위:** 2026-10-08~10-09 공개 자료 중심
>
> 이 글은 공식 문서·프로젝트 릴리스·벤더 공지를 우선 확인해 작성했다. 확인되지 않은 소셜·2차 요약은 핵심 근거에서 제외했으며, “출시”와 “계획/프리뷰”를 구분한다.

## 오늘의 결론

1. **에이전트의 운영 단위가 모델에서 실행 환경으로 이동 중이다.** Claude의 브라우저·컴퓨터 사용 SDK와 AWS·Google의 에이전트 거버넌스 공지는 모델 호출보다 도구 권한, 네트워크 범위, 추적·평가가 중요해졌음을 보여준다.
2. **Kubernetes 1.37은 업그레이드보다 사전 호환성 점검이 먼저다.** cgroup v1, kube-proxy IPVS, Static Pod의 API 리소스 참조, SELinux 볼륨 동작 변화가 운영 리스크다.
3. **보안 우선순위는 CVSS가 아니라 실제 악용 여부와 노출 경로로 정해야 한다.** CISA KEV에는 10월 8일에도 신규 항목이 추가됐고, 인터넷 경계 장비·파일 서버·인증 계층을 먼저 확인해야 한다.
4. **Jev 같은 결정 모델은 생성 모델의 대체재가 아니라 라우팅·승인·분류용 판정 계층이다.** 확률과 confidence를 반환하므로 임계값, 재검토, 사람 인계 규칙을 함께 설계해야 한다.

## 1. AI & Machine Learning

### Claude Opus 5.5와 Haiku 5.5: 장기 실행·비용·툴 루프가 핵심

Anthropic 공식 페이지에 따르면 Claude Opus 5.5는 2026년 9월 22일 공개됐고, 1M 컨텍스트·최대 128K 출력·입력 4달러/MTok, 출력 20달러/MTok을 제시한다. Claude Platform 릴리스 노트에는 10월 7일 Haiku 5.5가 추가됐으며 1M 컨텍스트, 128K 출력, adaptive thinking을 지원한다고 기록돼 있다. 같은 날 Python·TypeScript SDK에 browser use와 computer use용 베타 클래스도 추가됐다.

**실무 해석:** 장시간 코딩 에이전트는 “더 큰 모델”만으로 안정화되지 않는다. 모델별 thinking 파라미터 호환성, 1M 컨텍스트의 실제 비용, 브라우저·데스크톱 도구의 승인 콜백, 네트워크 allowlist를 함께 테스트해야 한다. Haiku 4.5 코드가 Haiku 5.5에서 깨질 수 있다는 마이그레이션 경고도 있으므로 모델 ID만 교체하는 방식은 위험하다.

- 출처: [Claude Opus 공식 페이지](https://www.anthropic.com/claude/opus)
- 출처: [Claude Platform API 릴리스 노트](https://docs.anthropic.com/en/release-notes/api)

### ML/DL 연구·신경과학·BCI 관찰

이번 수집 범위에서는 BCI 또는 신경과학 분야의 **새로운 1차 연구를 공식 원문으로 교차검증할 만한 항목을 확인하지 못했다.** 따라서 과장된 “돌파구”를 싣지 않는다. BCI 성능 주장은 데이터셋, 피험자 수, 온라인/오프라인 평가, 지연시간, 사용자별 일반화 여부가 함께 공개돼야 기술적 의미를 판단할 수 있다.

## 2. AI 에이전트 프레임워크

### LangGraph 1.2.14

공식 GitHub 릴리스 기준 LangGraph 1.2.14가 10월 6일 공개됐고, LangGraph CLI 0.4.33은 10월 7일 공개됐다. CLI 릴리스에는 이미 푸시된 이미지를 배포하는 `--image-uri`, 배포 리스너 목록 명령, credential-bearing Git dependency 거부 수정이 포함돼 있다.

**운영 포인트:** 배포 파이프라인이 소스 빌드와 이미지 배포를 혼합한다면 이미지 digest를 고정하고, credential이 URL에 들어간 의존성을 차단하는 정책을 CI에서도 재현해야 한다.

### CrewAI 1.15.26

공식 릴리스 기준 CrewAI 1.15.26이 10월 8일 공개됐다. 이번 릴리스는 interrupted lock 획득 시 소유권 보존, 문서 사이트 source URL 보존, 로그 출력의 실제 task output 표시를 수정했다. 직전 1.15.24에는 `crewai eval`, background reply, job lifecycle/runner, 모델·역할 교체용 `llm_overlay`, 의존성 advisory 대응이 추가됐다.

**운영 포인트:** CrewAI의 평가 명령은 “응답이 그럴듯한가”가 아니라 trace가 남았는지와 gate 통과 여부를 분리한다. 평가 결과를 배포 승인에 사용한다면 종료 코드와 trace 저장소를 함께 확인해야 한다.

- 출처: [LangGraph releases](https://github.com/langchain-ai/langgraph/releases)
- 출처: [CrewAI releases](https://github.com/crewAIInc/crewAI/releases)

### Devin

이번 수집에서는 Devin의 신규 기능을 공식 변경 공지로 확인하지 못했다. 따라서 최신 버전이나 성능을 추정해 비교하지 않는다. 비교가 필요하면 공식 changelog와 실제 작업 trace를 같은 과제로 수집해야 한다.

## 3. Kubernetes & Cloud Native

### 1.37 현재 상태와 주요 변경

Kubernetes 공식 릴리스 페이지 기준 최신 1.37 패치는 1.37.1(2026-09-15), 1.36은 1.36.5다. 1.37의 공식 안내에서 운영 영향이 큰 항목은 다음과 같다.

- **cgroup v1 단계적 폐기:** kubelet의 `failCgroupV1` 기본 동작 때문에 구형 노드가 초기화되지 않을 수 있다. cgroup v2 전환을 기본 계획으로 삼는다.
- **kube-proxy IPVS deprecation:** IPVS는 경고 단계이며 장기적으로 nftables 등 대체 경로를 검토해야 한다.
- **Static Pod API 참조 금지:** Static Pod가 Secret·ConfigMap을 참조하는 구성이 더 이상 허용되지 않는다.
- **SELinuxMount GA:** CSI 드라이버가 opt-in한 경우 mount context 방식이 적용된다. 공유 볼륨에서 서로 다른 SELinux label을 쓰는 Pod는 기동 실패 가능성이 있다.
- **metrics.k8s.io GA 경로:** `kubectl top`과 HPA 의존 경로를 stable API 전환 관점에서 점검한다.

1.36에서는 `gitRepo` 볼륨이 영구 비활성화됐다는 EKS 문서의 주의사항도 있다. 업그레이드 전 다음을 검사한다.

```bash
kubectl get nodes -o wide
kubectl get --all-namespaces pods -o yaml | grep -nE 'gitRepo|configMapRef|secretRef'
kubectl -n kube-system get configmap kube-proxy -o jsonpath='{.data.config\.conf}' | grep 'mode:'
```

- 출처: [Kubernetes releases](https://kubernetes.io/releases/)
- 출처: [Kubernetes v1.37 Sneak Peek](https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/)
- 참고: [Amazon EKS Kubernetes versions](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions-standard.html)

## 4. 사이버 보안

CISA KEV는 10월 8일 기준 ProFTPD CVE-2015-3306과 ONLYOFFICE Docs CVE-2021-3199를 포함한 신규 항목을 표시하고 있으며, 두 항목 모두 10월 11일 remediation due date와 포렌식 triage 요구를 보여준다. KEV는 “심각해 보이는 취약점” 목록이 아니라 실제 야생 악용 증거와 명확한 조치가 있는 취약점을 우선하는 카탈로그다.

**오늘의 점검 순서:**

1. 인터넷에 노출된 ProFTPD·ONLYOFFICE 및 유사 파일 처리 서비스를 자산 목록과 대조한다.
2. 패치가 불가능한 시스템은 네트워크에서 격리하거나 서비스 종료 여부를 판단한다.
3. 인증·SAML·원격접속 경계 장비는 CVE 번호만 확인하지 말고 vendor advisory의 영향 버전과 실제 설정을 확인한다.
4. KEV 추가 항목은 패치 전후 로그·계정·파일 무결성 확인을 남긴다. 패치 완료가 침해 부재를 의미하지는 않는다.

- 출처: [CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)

## 5. Cloud Service Provider

- **AWS:** 10월 5일 AWS Weekly Roundup은 OpenAI Agents API 기반의 Amazon Bedrock Managed Agents 공개 프리뷰를 소개했다. AWS 리소스·identity·permission·governance 통합이 핵심이다. AWS Well-Architected Agent도 환경의 비용·보안·성능·복원력 개선 추천 프리뷰로 공개됐다.
- **Google Cloud:** 9월 28일~10월 2일 공지는 Claude Sonnet 5.5의 Model Garden 제공, Apigee X dynamic routing을 통한 생성형 AI 비용 최적화 가이드, OpenTelemetry/OpenInference 기반 에이전트 평가 사례를 담고 있다.
- **Azure:** Azure 공식 공지는 Microsoft Foundry의 모델 선택·voice agent·continuous optimization 확대와 Claude Opus 5.5 제공을 안내한다. “최적 모델은 계속 바뀐다”는 전제 아래 모델 라우팅과 지속 평가가 필요하다.
- **Naver Cloud:** NAVER 공식 보도자료에는 9월 3일 한국 사이버보안 환경에 맞춘 AI 모델 개발 컨소시엄, 9월 9일 프랑스와 AI 협력·AI Factory 파트너십 관련 내용이 있다. 제품 GA나 API SLA로 오인하지 말고 협력·개발 발표 범위로 읽어야 한다.

- 출처: [AWS News Blog](https://aws.amazon.com/blogs/aws/)
- 출처: [Google Cloud What’s New](https://cloud.google.com/blog/topics/inside-google-cloud/whats-new-google-cloud)
- 출처: [Azure Announcements](https://azure.microsoft.com/en-us/blog/content-type/announcements/)
- 출처: [NAVER Press Releases](https://www.navercorp.com/en/media/pressReleases?keyword=NAVERCLOUD)

## 6. 개발 언어·프론트엔드

- **Python:** Python Insider는 Python 3.15.0 candidate 3(10월 2일)와 Python 3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8 릴리스를 안내한다. 3.10.22는 마지막 릴리스이므로 3.10 사용자는 업그레이드 계획이 필요하다.
- **Rust:** Python Language Summit 2026에서 Rust for CPython 진행 상황과 Python-to-Rust transpiler인 Spicycrab이 소개됐다. 이는 공식 Rust 릴리스가 아니라 CPython 생태계의 실험·논의 신호다.
- **React/Vue:** 이번 수집에서 React·Vue의 당일 공식 릴리스와 보안 공지를 충분히 확인하지 못했다. 버전 비교는 GitHub 공식 release와 npm dist-tag를 함께 확인해야 한다.
- **Java/Kotlin/JavaScript/TypeScript:** 당일 변경을 1차 출처로 확정하지 못했다. 운영 업그레이드는 각 프로젝트의 공식 release note, CVE, 호환성 매트릭스를 기준으로 별도 검증한다.

- 출처: [Python Insider](https://blog.python.org/)
- 출처: [Python version status](https://devguide.python.org/versions/)

## 7. Infrastructure & Linux

Linux Kernel Archives는 10월 4일 기준 mainline 7.3-rc6, stable 7.2.9, longterm 6.18.55·6.12.112·6.6.158·6.1.189·5.15.222를 표시한다. RC는 일반 운영 노드의 기본 선택지가 아니며, 배포판이 제공하는 보안 업데이트와 함께 검증해야 한다.

**운영 체크:** 커널 업그레이드는 버전 문자열만 비교하지 말고 배포판 패치 레벨, eBPF·스토리지·네트워크 드라이버, 컨테이너 런타임과의 조합을 staging에서 확인한다. Kubernetes 1.37의 cgroup v2 전환과 Linux 배포판 기본값도 하나의 마이그레이션 항목으로 묶는다.

- 출처: [The Linux Kernel Archives](https://www.kernel.org/)

## 8. Special Section — Jev API 및 의사결정 모델

Jev API 공식 문서에 따르면 이 서비스는 텍스트를 길게 생성하는 chat-completions API가 아니라, 하나의 `state`와 typed `questions`를 받아 구조화된 결정을 반환한다. `POST /api/v1/decisions`는 `noul`(명제의 참일 확률), `choice`(선택지별 확률·confidence), `score`(순서형 단계별 확률·confidence)를 지원한다. 문서 기준 질문은 1~6개, state는 최대 60,000자다.

### 권장 적용 패턴

```text
관측 이벤트
  → Jev: allow / review / deny 또는 route 결정
  → 정책 엔진: 임계값·권한·reversibility 확인
  → 사람 승인 또는 제한된 도구 실행
  → 결과·근거·모델 버전 기록
```

Jev의 확률을 곧바로 자동 실행 조건으로 쓰지 않는다. confidence가 낮거나 1위·2위 선택지가 가까우면 사람 검토로 보내고, 모델 호출 실패·429·502는 **deny 또는 fail-closed**로 처리한다. `jev-latest` alias보다 임계값 운영에서는 `jev-1.13`처럼 모델을 고정하고, 입력 state를 최소화하며, idempotency와 감사 로그를 둔다.

**결정 모델의 역할:** LLM 에이전트가 생성·도구 선택을 담당한다면 Jev는 승인·분류·라우팅·위험도 점수라는 좁은 판정 경계를 담당한다. 두 계층을 분리하면 생성 결과의 유창함과 실행 허용을 혼동하지 않을 수 있다.

- 출처: [Jev API Reference](https://jev-api.org/docs)

## 내일 확인할 것

- Claude 5.5 계열 SDK에서 adaptive thinking과 기존 extended thinking의 실제 마이그레이션 테스트
- Kubernetes 1.37 환경의 cgroup v2·IPVS·SELinux CSI 조합별 사전 점검 결과
- CISA KEV 신규 항목의 vendor remediation과 실제 노출 자산 여부
- LangGraph/CrewAI 릴리스가 trace·평가·credential 경계를 어떻게 강화하는지
- Jev decision 결과를 정책 엔진과 감사 로그에 연결할 때의 fail-closed 기준

## 참고 자료

1. [Anthropic Claude Opus](https://www.anthropic.com/claude/opus)
2. [Claude Platform release notes](https://docs.anthropic.com/en/release-notes/api)
3. [LangGraph releases](https://github.com/langchain-ai/langgraph/releases)
4. [CrewAI releases](https://github.com/crewAIInc/crewAI/releases)
5. [Kubernetes releases](https://kubernetes.io/releases/)
6. [Kubernetes v1.37 Sneak Peek](https://kubernetes.io/blog/2026/07/31/kubernetes-v1-37-sneak-peek/)
7. [CISA KEV Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)
8. [AWS News Blog](https://aws.amazon.com/blogs/aws/)
9. [Google Cloud What’s New](https://cloud.google.com/blog/topics/inside-google-cloud/whats-new-google-cloud)
10. [Azure Announcements](https://azure.microsoft.com/en-us/blog/content-type/announcements/)
11. [NAVER Press Releases](https://www.navercorp.com/en/media/pressReleases?keyword=NAVERCLOUD)
12. [Python Insider](https://blog.python.org/)
13. [Linux Kernel Archives](https://www.kernel.org/)
14. [Jev API Docs](https://jev-api.org/docs)
