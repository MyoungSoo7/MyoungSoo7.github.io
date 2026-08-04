---
layout: post
title: "Graphify 소개 — 코드베이스를 질의 가능한 지식 그래프로 바꾸는 Graph RAG"
date: 2026-08-04 22:46:33 +0900
categories: [ai, rag, developer-tools, architecture]
tags: [Graphify, Graph-RAG, Knowledge-Graph, AST, Claude-Code, MCP, RAG]
---

> **Graphify는 코드·문서·SQL 스키마·설정·PDF·이미지를 분석해 질의 가능한 지식 그래프로 변환하는 오픈소스 도구다.**

[Graphify GitHub 저장소](https://github.com/Graphify-Labs/graphify)

## 1. Graphify란 무엇인가

일반적인 RAG는 문서를 잘게 나누고 임베딩한 뒤, 질문과 유사한 벡터를 검색한다.

```text
문서 → Chunk → Embedding → Vector Search → 답변
```

Graphify는 여기에 다른 접근을 취한다.

```text
코드·문서·SQL·설정·PDF·이미지
        ↓
개념·엔티티·호출·의존·인용 관계 추출
        ↓
지식 그래프 생성
        ↓
질의·경로·관계 설명·구조 분석
```

따라서 단순히 “비슷한 문서”를 찾는 것이 아니라, **어떤 개념과 코드가 연결되고 그 연결이 왜 생겼는지**를 탐색하는 데 초점을 둔다.

## 2. 핵심 기능

Graphify 저장소의 README와 공개 설명 기준으로 다음 기능을 제공한다.

| 기능 | 설명 |
|---|---|
| 코드 분석 | tree-sitter AST와 호출 그래프 기반 관계 추출 |
| 문서 분석 | Markdown·TXT·RST의 개념과 관계 추출 |
| PDF 분석 | 인용·개념·문서 간 연결 추출 |
| 이미지 분석 | 스크린샷·다이어그램·화이트보드 이미지 분석 |
| 그래프 질의 | 개념 연결, 경로, 관계 설명 |
| 시각화 | HTML·SVG·GraphML 출력 |
| Wiki 출력 | 에이전트가 탐색 가능한 Markdown Wiki 생성 |
| 증분 처리 | SHA256 캐시로 변경된 파일만 재처리 |
| 자동 동기화 | `--watch`와 Git commit hook 지원 |
| 연동 | MCP stdio 서버·Neo4j Cypher 출력 지원 |

Graphify는 Python, TypeScript, Java, Go, Rust, C/C++, Ruby, C#, Kotlin, Scala, PHP 등 다양한 코드 확장을 지원하며, NetworkX·Leiden·tree-sitter·Claude·vis.js를 사용한다. 구체적인 언어별 지원 범위와 동작은 버전별로 확인해야 한다.

## 3. 사용 방법

설치 후 현재 프로젝트를 분석하는 기본 흐름은 다음과 같다.

```bash
pip install graphifyy
graphify install
```

PyPI 패키지명은 현재 `graphifyy`이며, CLI 명령은 `graphify`다. macOS의 externally-managed Python 환경에서는 `pipx install graphifyy` 방식이 적합할 수 있다.

```bash
/graphify .
```

주요 명령 예시는 다음과 같다.

```bash
/graphify ./raw
/graphify ./raw --mode deep
/graphify ./raw --update
/graphify query "무엇이 attention과 optimizer를 연결하는가?"
/graphify path "DigestAuth" "Response"
/graphify explain "SwinTransformer"
/graphify ./raw --wiki
/graphify ./raw --mcp
graphify hook install
```

실행 결과에는 다음과 같은 산출물이 포함될 수 있다.

```text
graphify-out/
├── graph.html
├── graph.json
├── GRAPH_REPORT.md
├── obsidian/
├── wiki/
└── cache/
```

## 4. Vector RAG와의 차이

Graphify는 Vector RAG를 무조건 대체하는 도구라기보다, **관계 중심 탐색이 필요한 영역을 보완하는 Graph RAG 계층**으로 이해하는 편이 정확하다.

| 질문 유형 | Vector Search | Graphify식 Graph Search |
|---|---|---|
| 유사한 문서 찾기 | 강점 | 보조적 |
| 특정 키워드 설명 | 적합 | 적합 |
| A가 B에 의존하는 이유 | 제한적 | 강점 |
| 코드 호출 경로 추적 | 제한적 | 강점 |
| 문서·코드·논문 연결 | 추가 설계 필요 | 그래프 구조로 표현 |
| 최신 원문 검색 | 적합 | 원문 동기화 필요 |
| 관계의 근거 설명 | 검색 결과에 의존 | edge 유형과 설명으로 표현 |

특히 Graphify가 `EXTRACTED`, `INFERRED`, `AMBIGUOUS` 같은 관계 상태를 구분하는 방식은 중요한 장점이다. 자동 생성된 관계를 모두 사실처럼 취급하지 않고, **직접 추출된 사실과 모델 추론을 구별**할 수 있기 때문이다.

## 5. Settlement 프로젝트에 적용한다면

Lemuel Settlement처럼 서비스·이벤트·ADR·DB·운영 문서가 많은 프로젝트에 적용하면 다음과 같은 탐색이 가능하다.

```text
settlement
  → order/payment projection
  → Kafka topic
  → outbox_events
  → settlement aggregate
  → ledger entry
  → payout
  → reconciliation
```

예상 질의:

```text
"payment.captured 이벤트가 정산 원장에 도달하는 경로는?"
"settlement-service와 order-service의 결합 지점은 어디인가?"
"이 payout 상태를 변경하는 코드와 정책 문서는 무엇인가?"
"ADR 0020의 결정이 실제 코드에 어떻게 반영됐는가?"
"복식부기 원장과 역분개에 연결된 테스트는 무엇인가?"
```

이런 질의는 단순 파일명 검색보다 **호출 관계·이벤트 관계·문서 근거·데이터 흐름**을 함께 봐야 답할 수 있다.

## 6. Hermes·LION·Leopard와의 연결

Graphify는 현재 운영 중인 Agent 체계와 결합할 여지가 크다.

```text
Graphify
  → 프로젝트 구조·관계 그래프
  → Hermes/MCP 질의 인터페이스
  → LION의 15개 CS 렌즈 평가
  → Leopard의 전략·조직·생산성 분석
  → GitHub Wiki/Obsidian 지식베이스
```

### Hermes

Hermes가 Graphify의 MCP 서버 또는 생성된 Wiki를 도구로 사용하면, 프로젝트를 매번 처음부터 읽지 않고 관계 그래프를 기반으로 질문할 수 있다.

### LION

LION은 구조·보안·네트워크·데이터베이스·분산시스템 등을 종합 평가한다. Graphify는 LION이 요구하는 증거 경로를 찾는 탐색 계층으로 활용할 수 있다.

### Leopard

Leopard가 기업·기술·생산성·조직을 분석할 때 Graphify를 사용하면 코드·문서·ADR·운영 기록의 연결을 구조화해 기술 전략의 근거를 더 명확히 제시할 수 있다.

## 7. 기대 효과와 주의점

### 기대 효과

- 대규모 코드베이스의 구조적 탐색
- 코드·문서·SQL·설정·PDF의 통합 분석
- 에이전트가 재사용할 수 있는 영속 그래프 생성
- 변경 파일만 재처리하는 증분 분석
- 관계의 추출·추론·모호성 구분
- Obsidian·Wiki·MCP·Neo4j로 확장 가능

### 주의점

- 그래프가 생성됐다고 관계가 모두 정확한 것은 아니다.
- `INFERRED`와 `AMBIGUOUS` edge는 반드시 원문·코드와 대조해야 한다.
- 71.5배 토큰 절감 수치는 저장소가 제시한 특정 벤치마크이며, 모든 프로젝트에 그대로 적용된다고 볼 수 없다.
- 작은 프로젝트에서는 그래프 구축 비용보다 직접 읽는 방식이 효율적일 수 있다.
- 대규모 프로젝트에서는 그래프 최신성, 캐시 무결성, 삭제 파일 처리, 권한·민감정보 필터를 별도로 검증해야 한다.
- Claude Vision과 LLM 분석을 사용하는 경로에서는 민감한 코드·문서·이미지의 외부 전송 여부를 확인해야 한다.

## 8. 운영 적용 제안

개인 프로젝트에 바로 전체 그래프를 만들기보다 다음 순서가 안전하다.

1. `settlement-service` 또는 `shared-common`처럼 범위가 명확한 모듈부터 분석
2. `graph.json`, `GRAPH_REPORT.md`, `wiki/` 결과를 검토
3. `EXTRACTED` 관계와 `INFERRED` 관계를 샘플링 검증
4. 개인정보·시크릿·운영 설정이 그래프에 포함되는지 확인
5. Git hook이나 `--watch` 적용 전 처리 비용 측정
6. 검증된 결과만 Hermes/MCP에 연결
7. LION 보고서의 증거 링크와 Graphify 경로를 연결

## 결론

Graphify는 단순한 코드 검색기가 아니다. 코드·문서·데이터 스키마·설정·이미지 사이의 관계를 보존해, 에이전트가 프로젝트를 **파일 묶음이 아니라 연결된 시스템**으로 이해하도록 돕는 도구다.

특히 Hermes·LION·Leopard·Settlement처럼 Agent 운영, 구조 평가, 분산 시스템, 지식 관리가 결합된 환경에서는 다음과 같은 역할을 할 수 있다.

```text
Graphify = 관계 추출 계층
Hermes   = Agent 실행·도구 계층
LION     = 기술·CS 종합 평가 계층
Leopard  = 전략·조직·생산성 분석 계층
Wiki     = 사람이 읽고 재사용하는 지식 계층
```

> **Vector RAG가 “비슷한 내용을 찾는” 데 강하다면, Graph RAG는 “무엇이 무엇과 어떻게 연결되는가”를 설명하는 데 강하다.**

## References

1. [Graphify GitHub Repository](https://github.com/Graphify-Labs/graphify)
2. [Graphify README](https://raw.githubusercontent.com/Graphify-Labs/graphify/main/README.md)
3. [Graphify Website](https://www.graphify.com/)

*이 글은 Graphify 저장소의 공개 README와 GitHub 페이지를 바탕으로 작성했으며, 실제 프로젝트 적용 전에는 버전·라이선스·LLM 데이터 전송 경로·벤치마크를 별도로 검증해야 한다.*
