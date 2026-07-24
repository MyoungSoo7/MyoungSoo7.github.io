---
layout: post
title: "AI Repo Radar로 발견해 홈랩에 올린 것 — Opik, 오픈소스 LLM 관측"
date: 2026-07-25 05:00:00 +0900
categories: [AI, Observability]
tags: [Opik, LLMObservability, RAG, Langfuse, AIRepoRadar, Curation, SelfHosting, HomeLab]
---

# 큐레이션으로 발견 → 검증 → 스택에 추가

좋은 도구를 만나는 경로는 두 가지다 — 남이 떠먹여 주거나, *잘 걸러진 목록에서 직접 고르거나.* 이 글은 후자의 실전 기록이다: **AI Repo Radar** 라는 큐레이션 사이트에서 **Opik**(오픈소스 LLM 관측 도구)을 발견해, 우리 홈랩에 실제로 올리기까지.

---

## Part 1. AI Repo Radar — 매일 뜨는 AI 오픈소스를 '실전점수'로 큐레이션

🔗 <https://ai-repo-radar-1u7.pages.dev/>

GitHub에 매일 올라오는 AI 오픈소스는 홍수다. 별점만 보면 마케팅에 휩쓸린다. AI Repo Radar는 그걸 **실전점수(prod_score)** 로 걸러 준다.

- **규모**: 최근 30일·50+ 스타 기준 **약 4,500개** repo (내가 본 스냅샷 기준 4,571개)
- **분류**: MCP·Agent·RAG·Eval·MLOps·Code-AI·LLM·Framework·Prompt 등 **21개 카테고리**
- **데이터**: 프론트는 정적 SPA이고, 실제 목록은 `data/repos.json`(약 5MB)로 로드된다. 각 repo에 `prod_score`, `star_velocity`, `summary_ko/en`, `topics`, `license` 등 메타가 붙어 있다.

**실제로 써 본 소감** — 유용하지만 함정도 있다. 별점 값이 일부 비현실적이고(예: 어떤 repo가 23만 스타로 표시), `prod_score`가 상위권에 포화돼 있어 최상단만 보면 변별이 안 된다. 그래서 나는 **카테고리 + 설명 기반으로 우리 프로젝트(하네스·멀티에이전트·RAG·관측·MCP)에 맞는 것만 손으로 큐레이션**했다. 큐레이션 사이트도 *한 번 더 큐레이션*해서 써야 한다.

그 손큐레이션에서 "LLM 관측" 버킷의 상위로 올라온 것이 **Opik**이었다.

---

## Part 2. Opik — 오픈소스 LLM/RAG 관측·평가

### 무엇인가
Opik은 **Comet ML이 만든 오픈소스 LLM 애플리케이션 관측·평가 플랫폼**이다. LLM 호출과 RAG 파이프라인을 **추적(trace)** 하고 **평가(eval)** 한다. [앞서 정리한 LLM 관측 3대장(Langfuse·LangSmith·Arize)](/2026/07/23/llm-observability-langfuse-langsmith-arize/)에 **오픈소스 계열 하나가 더 추가된 셈**이다.

### 무엇을 '관측'하나 — 인프라 관측과 다른 층
여기가 핵심이다. Opik의 "관측"은 CPU·메모리·파드 같은 **인프라 지표가 아니라, LLM/RAG 애플리케이션 계층 그 자체**를 본다.

- **LLM 트레이스**: 요청 하나의 호출 트리 — 입력 프롬프트·출력 원문, **토큰(in/out)·비용·지연**, 도구 호출, 에이전트 단계, 에러/재시도
- **RAG 관측**: 질의 임베딩 → 벡터 검색 → **실제 검색된 청크와 유사도 점수** → 프롬프트 조립 → 응답. 그리고 **groundedness/faithfulness**(답이 검색 문서에 근거했나, 아니면 환각인가)
- **평가(eval)**: LLM-as-judge·코드 기반·사람 라벨로 출력 품질 채점, 데이터셋·실험 비교
- **프로덕션 모니터링**: 트레이스·비용·품질 지표 대시보드

즉 "RAG가 엉뚱한 답을 하면 *검색이 틀렸나, LLM이 문서를 무시했나*"를 구분해 준다 — 인프라 관측으로는 절대 안 보이는 정보다.

### 무겁나 — 자체 호스팅 구조
Opik self-host는 컴포넌트가 많다: 백엔드 + python-backend + 프론트엔드 + **ClickHouse**(트레이스 분석 DB) + **ZooKeeper**(ClickHouse 복제) + MySQL + Redis + MinIO. K8s용 Helm 차트(`opik/opik`)와 docker-compose(`./opik.sh`) 두 경로가 있다.

---

## 그래서 홈랩에 올렸다 — 실전 배포 노트

큐레이션에서 발견한 걸로 끝내지 않고 **실제로 우리 [홈랩 K3s 클러스터](/2026/07/23/elk-node-placement-strategy/)에 배포**했다. 그 과정에서 배운 것:

- **배포 방식 선택**: K8s로 올리려 했으나, 클러스터 메모리가 타이트(여유 노드가 control-plane taint 하나뿐)하고 **Opik 차트가 서브차트의 nodeSelector를 노출하지 않아** 8개 컴포넌트를 한 노드에 핀하기가 취약했다. → **docker-compose로 여유 있는 단일 노드에 배포**하는 게 훨씬 견고했다. *무거운 다중컴포넌트 앱은 때로 K8s보다 docker-compose가 정답이다.*
- **실측 footprint**: 걱정과 달리 **총 ~2.7Gi**(ClickHouse가 idle에서 500MiB대). 홈랩 트레이스 볼륨엔 넉넉.
- **노출·인증**: Cloudflare Tunnel + **Cloudflare Access(이메일 OTP)** 게이트. 무인증 노출 창이 생기지 않도록 **"DNS → Access 정책 → 터널 ingress" 순서**로 열었다. 검증: 무인증 접속 시 302로 Access 로그인으로 리다이렉트되는 걸 확인.

*배포는 "발견"의 완성이다 — 큐레이션 → 실전점수 검증 → 우리 스택에서 실제 동작까지 가야 도구가 자산이 된다.*

---

## 한 줄 결론

**AI Repo Radar** 같은 큐레이션은 정보 홍수 속 좋은 진입점이지만, *별점·prod_score를 맹신하지 말고 내 워크로드 기준으로 한 번 더 걸러야* 한다. 그렇게 걸러 발견한 **Opik**은 인프라가 아니라 **LLM/RAG 호출의 의미적 신호(프롬프트·토큰·비용·검색근거)를 관측**하는 오픈소스 도구이고, 우리 홈랩에 docker-compose + CF Access로 올려 자산화했다. 다음은 실제 에이전트/RAG 호출을 여기로 흘려보내 트레이싱하는 일이다.

---

## 출처

- AI Repo Radar (큐레이션 사이트): <https://ai-repo-radar-1u7.pages.dev/>
- Opik (공식): Comet ML, **opik** — 오픈소스 LLM 관측·평가: <https://github.com/comet-ml/opik> · 문서 <https://www.comet.com/docs/opik/>
- 관련 본인 정리글: [LLM 관측 3대장 Langfuse·LangSmith·Arize](/2026/07/23/llm-observability-langfuse-langsmith-arize/) · [홈랩 K3s ELK 노드 배치](/2026/07/23/elk-node-placement-strategy/)

> 참고: repo 개수·prod_score 등은 조회 시점(2026-07-24) 스냅샷 기준이며, Opik의 컴포넌트·기능은 self-host 문서 기준이다. 별점 등 일부 지표는 신뢰도가 낮아 본문은 설명·공식 문서 기반으로 기술했다.
