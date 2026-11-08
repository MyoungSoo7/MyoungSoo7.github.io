---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-09"
date: 2026-11-09 08:30:01 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-09 08:30 KST. 수집 범위는 11-07~11-09 공개 자료입니다. 11-05~11-08 브리핑과 겹치는 소식은 새 진전이 있을 때만 다룹니다. 오늘(11-09)·어제(11-08)가 아닌 항목은 날짜를 붙이고 "최신 아님"으로 표시합니다. 주말 직후 월요일 아침이라 공식 릴리스가 적습니다.

**표기 규칙:** [사실] 공식·1차 출처로 확인 / [벤더 주장]·[회사 자체 주장] 벤더·회사 자체 수치·평가 / [보도] 언론 보도 / [추론] 필자 판단 / [미확인] 원문 확인 불가.

## 오늘의 핵심

1. **Claude Code의 "Yes, and don't ask again" 승인이 비밀값을 공개 저장소로 흘린다는 연구가 나왔습니다.** Apiiro가 공개 저장소의 `.claude/settings.local.json`을 조사해 DB 비밀번호·클라우드 키 등 1,379개의 고유 비밀값을 찾았습니다. 연구는 11-05, 보도는 11-07입니다. [1]
2. **LNbits가 공격이 이어지자 모든 운영자에게 서버를 즉시 내리라고 요청했습니다(11-08).** 호스팅 인스턴스도 모두 중지됐고, 패치는 24~48시간 안에 나온다고 했습니다. CVE와 GitHub 권고는 아직 없습니다. [2]
3. **Apache Axis 1.x에 인증 없이 원격 클래스를 생성시키는 취약점(CVE-2026-90436, critical)이 공개됐습니다.** EOL 제품이라 수정 릴리스는 나오지 않고, 이전 또는 패치 커밋 적용만 남았습니다. 오래된 Java SOAP 시스템을 운영한다면 확인해야 합니다. [3][4]
4. **KubeCon + CloudNativeCon NA 2026이 현지 시각 오늘(11-09) Salt Lake City에서 시작합니다.** 첫날은 공동 개최 행사이고 본 행사는 11-10부터입니다. 새로 AI Inference + Agentic 트랙이 생겼습니다. [6][7]
5. **CrewAI 1.15.38이 나왔습니다(11-08).** 기본 모델이 gpt-6-luna로 바뀌었고, headless 평가용 옵션과 평가 관련 수정이 들어갔습니다. [8]

---

## 1. AI & ML

**Claude Platform·Anthropic 공식 채널** [9]

- [사실] Claude Platform 릴리스 노트의 마지막 항목은 11-05입니다(IP 허용 목록 베타, Admin API 전체 로그아웃 베타). 11-06~11-09에는 새 항목이 없습니다.
- [사실] 예정된 일정은 그대로입니다. Opus 4.8 fast mode 제거와 Sonnet 4.5 퇴역이 모두 11-30입니다. 이 모델 ID를 쓰는 배치·에이전트는 이번 달 안에 바꿔야 합니다.
- [사실] Anthropic 연구 페이지에는 11-06 이후 새 글이 없습니다.
- [미확인] 국내 매체가 11-08에 Claude Projects의 코딩 작업 분할 기능(Pro/Max/Ultra 베타)을 보도했습니다. 다만 이 기능의 롤아웃은 9월에 시작됐고, 이번 회차에 Anthropic 원문 공지는 찾지 못해 새 소식으로 다루지 않습니다.

## 2. AI 에이전트 프레임워크

**CrewAI 1.15.38 (11-08 19:39 UTC)** [8]

- [사실] 기능 변경:
  - 기본 모델이 모든 경로에서 gpt-6-luna로 바뀌었습니다.
  - 에이전트 입력에 스프레드시트 URL을 넣으면 그 내용을 읽습니다.
  - 평가 사용량 span에 대상과 평가별 id 태그가 붙습니다.
  - `crewai eval`에 `--no-open` 옵션이 생겨 브라우저 없이 돌릴 수 있습니다.
- [사실] 수정 사항:
  - 평가 오류를 run_failed로 집계합니다.
  - 평가가 tracing을 켤 때 만드는 프로젝트 `.env`의 권한이 소유자 전용입니다.
  - OpenAI 호환 공급자의 키를 첫 호출 시점에 검사합니다.
  - 메모이즈된 crew 메서드가 인스턴스 단위로 캐시됩니다.
  - `crewai run` 스크립트가 실패하면 0이 아닌 종료 코드를 돌려줍니다.
- [추론] 기본 모델 변경은 모델을 명시하지 않은 crew의 비용과 출력이 조용히 바뀐다는 뜻입니다. 업그레이드 전에 `llm=`을 명시했는지 확인하는 편이 안전합니다. 종료 코드 수정은 CI가 그동안 실패를 성공으로 보고 있었을 수 있다는 뜻이기도 합니다.
- LangGraph·Devin: 11-08 브리핑의 LangGraph 1.2.20 이후 새 릴리스는 확인하지 못했습니다.

## 3. Kubernetes & Cloud Native

**KubeCon + CloudNativeCon North America 2026 (11-09~12, Salt Lake City)** [6][7]

- [사실] 월요일(11-09)은 공동 개최 행사 날입니다. Agentics Day: MCP + Agents, ArgoCon, BackstageCon, CiliumCon, Cloud Native AI + Inference Day, FluxCon, Kubernetes on Edge Day, Observability Day, Open Source SecurityCon, OpenTofu Day, Platform Engineering Day가 열립니다.
- [사실] 본 행사는 화요일(11-10)에 시작합니다. 이번에 AI Inference + Agentic 트랙이 새로 생겼습니다.
- [사실] 온라인 참가는 없고, 세션 녹화는 2주 안에 YouTube에 올라옵니다.
- [추론] Salt Lake City(MST)의 11-09 오전은 한국 시각으로 11-10 0시 이후입니다. 기술 발표 대부분은 이번 주 화~목 밤(KST)에 나올 가능성이 큽니다.
- [사실] Kubernetes 공식 블로그는 10-29 "AI Conformance" 글 이후 새 글이 없습니다. v1.38.0-beta.0과 v1.37.2는 이전 브리핑에서 다뤘습니다. [10]

## 4. 사이버 보안

**Claude Code "Yes, and don't ask again"과 비밀값 노출 (Apiiro 연구 11-05, 보도 11-07, 최신 아님)** [1]

- [보도] 무엇이 문제인가:
  - 이 버튼을 누르면 승인한 명령이 `.claude/settings.local.json`에 그대로 저장됩니다. 명령 안의 토큰·비밀번호도 평문 그대로 저장됩니다.
  - Claude Code는 이 파일을 전역 git exclude에만 추가하고 프로젝트의 `.gitignore`에는 넣지 않습니다. 그래서 다른 환경에서 clone하거나 exclude 설정이 없으면 커밋될 수 있습니다.
  - Apiiro는 Opus 5.5와 Fable 5.1에서 재현했다고 밝혔습니다.
- [보도] Apiiro의 집계:
  - 공개 사본 104,185개(103,617개 저장소)를 조사했고, 그중 1,122개(1.1%)에 비밀값이 있었습니다.
  - 고유 비밀값은 1,379개입니다. DB 비밀번호 379개, SSH 로그인 43개, GitHub/GitLab/npm 토큰 42개, AWS 키 23개가 포함됩니다.
  - 이력에만 남은 비밀값도 509개 저장소에서 734개가 더 나왔습니다.
  - 이 파일을 바꾼 커밋 중 Claude가 공동 작성자로 들어간 경우가 추적된 1,105개 저장소 중 539개였습니다.
- [보도] Apiiro는 발견한 자격 증명을 직접 사용해 보지 않았습니다. 통보받은 한 회사는 키가 실제로 유효했다고 확인했습니다.
- 권고:
  - 노출된 키를 먼저 교체합니다.
  - `git rm --cached .claude/settings.local.json`으로 추적을 해제하고 프로젝트 `.gitignore`에 추가합니다.
  - 비밀값은 환경 변수로 넘깁니다.
  - 정확한 명령 대신 `Bash(npm run *)` 같은 패턴으로 승인합니다.
- [미확인] 11-08 기준 Anthropic의 공식 수정 공지는 찾지 못했습니다.
- 근거 한계: 수치는 Apiiro의 자체 조사이고, 중립 제3자의 재현은 부재합니다.
- [추론] 직접 점검하려면 `git log --all -- .claude/settings.local.json`으로 이 파일이 커밋된 적이 있는지 확인합니다.

**LNbits 긴급 서버 중지 요청 (11-08)** [2]

- [보도] 시간순 경과(UTC):
  - 12:33: 운영자들에게 Paywall 확장을 끄라고 안내했습니다.
  - 13:56: 공식 X 계정에 다음 글이 올라왔습니다. "All LNbits users should stop their LNbits servers IMMEDIATELY... Following a wave of attacks, we have a number of security patches to push."
  - 17:18: my.lnbits.com의 호스팅 인스턴스를 모두 중지했습니다. 24시간 안에 재개하는 것이 목표입니다.
- [보도] 개발자 Ben Arc는 패치가 24~48시간 안에 나온다고 했습니다.
- [보도] BitTipBot 운영자는 09:22~14:00 UTC 사이에 새로 만든 계정들을 통해 2,285,545 sats를 잃었다고 밝혔습니다. 피해 당사자의 자체 주장입니다.
- [미확인] 수집 시점에 GitHub 보안 권고와 CVE는 없고, 최신 릴리스는 여전히 v1.6.2(09-18)입니다. 취약점의 성격도 공개되지 않았습니다.
- [추론] LNbits를 직접 운영한다면 공지대로 서버를 멈추고, 패치가 나오면 공식 저장소에서만 받는 것이 맞습니다.

**Apache Axis 1.x CVE-2026-90436 (11-06, 최신 아님, critical)** [3][4]

- [사실] SOAP Fault의 `<detail><exceptionName>`에 적힌 클래스를 Axis가 로드합니다. String `<data>`가 함께 있으면, AxisFault인지 검사하기 전에 String 생성자로 객체를 만듭니다.
  - 클래스를 로드하기만 해도 static initializer가 실행됩니다.
  - classpath에 알맞은 클래스가 있으면 원격 코드 실행으로 이어집니다.
- [사실] 이 파싱은 서비스별 핸들러 체인보다 먼저 일어납니다. 그래서 서비스에 설정한 인증 핸들러로는 막을 수 없습니다.
- [사실] 1.4까지 모든 1.x가 영향을 받습니다. 프로젝트는 Axis 1.x 수정 릴리스를 내지 않을 계획입니다. 대응은 둘 중 하나입니다.
  - Axis2/Java 같은 다른 SOAP 엔진으로 이전합니다.
  - 패치 커밋(41f3b4e)을 적용해 직접 빌드합니다.
- [사실] 같은 날 Axis2/Java의 XXE·SSRF·XSS·요청 본문 무제한 버퍼링 등 7건과 Apache James의 WebAdmin 무인증 노출(Docker 기본값) 등 7건도 oss-security에 공개됐습니다. [5]
- [추론] Axis 1.4는 금융·공공의 오래된 Java 연계 모듈에 아직 남아 있는 경우가 많습니다. 의존성 트리에서 `axis:axis`와 `org.apache.axis:axis`를 검색해 보는 것이 첫 단계입니다.

**CISA KEV** [11]

- [사실] 11-06 이후 KEV 신규 등재는 확인하지 못했습니다. 11-06에 등재된 SonicWall CVE-2026-19868은 11-20이 기한입니다.
- [사실] 11-04에 등재된 Apple CVE-2024-27834는 11-18이 기한입니다.
- [미확인] 이번 주 다른 기한(Adobe Commerce·Brotli 11-10, VMware ESX 11-11, Ivanti Connect Secure 11-13)은 2차 집계로만 봤습니다. CISA 카탈로그 원문에서 하나씩 대조하지 못했습니다.
- 기타 IBM API Connect 대량 패치, Langflow, LXD, Node-RED 관련 소식은 집계 사이트로만 확인돼 이번 회차에서 다루지 않았습니다.

## 5. CSP

- AWS·Azure·GCP·네이버클라우드: 11-07~11-09(주말)에 새 공식 발표를 확인하지 못했습니다. SageMaker MIG와 카카오클라우드 Container Registry 장애(11-05)는 이전 브리핑에서 다뤘습니다.
- [추론] KubeCon 기간(11-10~12)에는 CSP의 매니지드 Kubernetes·추론 관련 발표가 몰리는 경향이 있습니다. 내일부터 확인할 대상입니다.

## 6. 개발 언어

- Python·Rust·React·Vue·Java·Kotlin·JS·TS: 11-07~11-09에 새 정식 릴리스를 확인하지 못했습니다.
- Java 생태계 관련으로는 4번의 Apache Axis 1.x·Axis2 공지가 이번 회차의 실질적인 소식입니다. [3][5]

## 7. Infrastructure & Linux

- [사실] 11-06 oss-security에 Python 3.14.10 FIPS 해시 알고리즘 강제 회귀(CVE-2026-119170)와 Perl HTTP::Body 트레일러 2차 시간 파싱(CVE-2026-121006)이 공개됐습니다. 11-06, 최신 아님. [5]
- OpenSSH "sshole"과 Xen XSA-526~528은 이전 브리핑에서 다뤘습니다.

## 9. AI 안전·정렬

- 새로 공개된 1차 자료는 확인하지 못했습니다.
- [추론] 4번의 Claude Code 사례는 모델 정렬 문제가 아니라 에이전트 도구의 권한 영속화 설계 문제입니다. 다만 "사용자 승인 결과를 어디에, 어떤 형태로 저장하는가"는 에이전트 안전 설계에서 점점 중요해지는 축입니다. [1]

## 10. MCP 에코시스템

- [사실] KubeCon 첫날 공동 개최 행사 중 하나가 "Agentics Day: MCP + Agents"입니다. [6]
- 11-07~11-09에 MCP 사양이나 공식 SDK의 새 릴리스는 확인하지 못했습니다.

## 11. MLOps·피처스토어

- MLflow 3.18.0 이후 새 릴리스는 확인하지 못했습니다(이전 브리핑에서 다룸).
- [사실] 2번의 CrewAI 1.15.38에 들어간 평가(eval) 개선은 에이전트 평가 파이프라인을 CI에 붙이는 쪽의 변화입니다. [8]

## 12. 에이전트 관측성

- Langfuse·Phoenix: 11-08 브리핑 이후 새 릴리스는 확인하지 못했습니다.
- [사실] CrewAI 1.15.38은 평가 사용량 span에 대상·평가 id 태그를 붙입니다. OTel 기반 관측 도구에서 평가 실행별 비용을 나눠 보기 쉬워집니다. [8]
- [사실] KubeCon 첫날 Observability Day가 열립니다. [6]

## 13. 그린 컴퓨팅

- 이번 회차에 새로 공개된 1차 자료는 확인하지 못했습니다.

## 14. 한국 기업 기술 블로그

- 11-07~11-09에 네이버 D2, 카카오, LINE(LY), 쿠팡, 우아한형제들, 당근, 토스, 두나무의 새 글은 확인하지 못했습니다. 주말이라 발행이 없었던 것으로 보입니다.
- 카카오클라우드 Container Registry 장애(11-05)와 카카오페이증권 ClickStack 로깅 글(11-06)은 이전 브리핑에서 다뤘습니다.
- [미확인] 카카오와 두나무 기술 블로그는 이번 회차에도 목록 페이지를 수집하지 못했습니다.

## 15. Java/Spring 프리랜서

수집일: 2026-11-09. 위시켓 공개 상세 페이지 기준이며, 로그인이 필요한 정보는 수집하지 않았습니다.

**오늘 확인된 검증 가능 공고 없음.** 11-07~11-09에 새로 등록된 Java/Spring 공고는 확인하지 못했습니다. 아래는 이전 브리핑에서 다룬 공고의 모집 상태를 다시 확인한 것입니다.

| 플랫폼 | 제목 | 기술 스택 | 계약·근무 형태 | 금액(공개분) | 상태 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | React/Java/Spring 기반 보험사 계정계 개발 및 운영 | Java, Spring, React (6~15년) | 기간제 360일, 서울 종로구, 계약 직후 시작 | 월 6,500,000원 | 11-06 등록, 11-20 마감, 모집 중 | [12] |
| 위시켓 | Spring 기반 보험사 AI 대화형 질의응답 서비스 개발 (중급) | Spring (6~8년) | 기간제 90일, 서울 종로구, 2026-11-16 시작 | 월 5,500,000원 | 11-02 등록, 11-16 마감, 모집 중 | [13] |
| 위시켓 | AI 웹 SaaS 무역 플랫폼 풀스택 개발 | Java, Spring 포함 (주니어 1~3년) | 기간제 180일, 서울 강서구, 2027-01-04 시작 | 월 3,500,000원 | 10-28 등록, 11-20 마감, 모집 중 | [14] |

- 위시켓 159507(11-06 등록, AI 챗봇 공공기관 기술지원)은 인프라 엔지니어 공고라 제외했습니다.
- [미확인] 이랜서 공고 몇 건(CJ 차세대 JAVA, 신한투자증권 차세대 등)이 집계 사이트에 보였습니다. 원문 페이지를 확인하지 못해 싣지 않았습니다. 프리모아도 이번 회차에 검증하지 못했습니다.

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- [사실] Jev Changelog의 마지막 항목은 여전히 Jev 1.14(10-14, 모델 ID `jev-1.14.0`)입니다. [15]
  - 다국어 지원을 개선했습니다.
  - 이미지에서 위치를 찾아 바운딩 박스로 답하는 Box 질문 유형을 추가했습니다(Jev 1.14 전용).
  - 이미지를 `state`·`instructions`·`criteria`에 넣을 수 있습니다.
  - long-context 헤더를 보내면 컨텍스트 한도가 262k 토큰으로 늘어납니다.
  - 마지막 두 기능은 Jev 1.13에서도 동작합니다.
- 11-06 카카오 Kanana-2-v-decide 공개 이후 Jev 관련 새 1차 자료(릴리스, 논문, 중립 벤치마크)는 확인하지 못했습니다.
- [추론] 의사결정 모델 API를 에이전트 도구로 쓴다면 이번 주 KubeCon의 AI Inference + Agentic 트랙에서 서빙·평가 관련 발표를 볼 만합니다. 다만 Jev를 직접 다루는 세션은 일정에서 확인하지 못했습니다. [7]
- 근거 한계: Jev와 대안 모델의 우열을 가릴 중립 제3자 헤드투헤드 비교는 여전히 부재합니다.

---

## 사실 · 추론 · 미확인 정리

**사실 (공식 출처 확인)**

- Apache Axis 1.x CVE-2026-90436의 영향 범위와 대응책, 같은 날 공개된 Axis2·James·Python·Perl 공지 [3][4][5]
- KubeCon NA 2026 일정과 공동 개최 행사, 새 트랙 [6][7]
- CrewAI 1.15.38 변경 사항 [8]
- Claude Platform 릴리스 노트에 11-06 이후 새 항목이 없다는 점, 11-30 모델 일정 [9]
- 위시켓 공고 3건의 공개 조건과 모집 상태, Jev 1.14 변경 내용 [12][13][14][15]

**벤더·당사자 주장 (독립 검증 부재)**

- Apiiro의 노출 건수 집계 [1]
- BitTipBot 운영자의 피해 규모 [2]

**보도**

- Claude Code 설정 파일 노출 연구, LNbits 긴급 중지 경과 [1][2]

**추론 (필자 판단)**

- CrewAI 기본 모델 변경의 영향, Axis 1.4 잔존 가능성과 점검 방법, KubeCon 발표가 KST로 언제 나올지, 에이전트 권한 영속화 설계에 대한 해석

**미확인**

- Anthropic의 공식 수정 공지, LNbits 취약점의 성격과 CVE [1][2]
- KEV 기한 일부, IBM API Connect 등 집계 사이트로만 본 보안 소식
- Claude Projects 작업 분할 기능의 공식 공지, 이랜서·프리모아 공고, 카카오·두나무 블로그 목록

---

## References

1. The Hacker News, Claude Code's "Don't Ask Again" file leaks secrets (Apiiro 연구 보도, 2026-11-07). <https://thehackernews.com/2026/11/claude-codes-dont-ask-again-file.html>
2. Bitcoin.com News, Lightning Network security scare forces LNbits servers offline (2026-11-08). <https://news.bitcoin.com/security/lightning-network-security-scare-forces-lnbits-servers-offline/>
3. oss-security, CVE-2026-90436: Apache Axis 1.x (EOL): unauthenticated remote class instantiation via SOAP fault exceptionName (2026-11-06). <https://www.openwall.com/lists/oss-security/2026/11/06/12>
4. NVD, CVE-2026-90436. <https://nvd.nist.gov/vuln/detail/CVE-2026-90436>
5. oss-security, 2026-11-06 메일링 리스트 목록. <https://www.openwall.com/lists/oss-security/2026/11/06/>
6. CNCF, KubeCon + CloudNativeCon North America 2026: Your week in Salt Lake City. <https://www.cncf.io/blog/2026/09/11/kubecon-cloudnativecon-north-america-2026-your-week-in-salt-lake-city/>
7. CNCF, CNCF reveals KubeCon + CloudNativeCon North America 2026 schedule, adds new AI Inference + Agentic track. <https://www.cncf.io/announcements/2026/08/10/cncf-reveals-kubecon-cloudnativecon-north-america-2026-schedule-adds-new-ai-inference-agentic-track/>
8. GitHub crewAIInc/crewAI, Release 1.15.38. <https://github.com/crewAIInc/crewAI/releases/tag/1.15.38>
9. Anthropic, Claude Platform release notes. <https://platform.claude.com/docs/en/release-notes/overview>
10. Kubernetes Blog. <https://kubernetes.io/blog/>
11. CISA, Known Exploited Vulnerabilities Catalog. <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
12. 위시켓, React/Java/Spring 기반 보험사 계정계 개발 및 운영. <https://www.wishket.com/project/159506/>
13. 위시켓, Spring 기반 보험사 AI 대화형 질의응답 서비스 개발 (중급). <https://www.wishket.com/project/159408/>
14. 위시켓, AI 웹 SaaS 무역 플랫폼 풀스택 개발. <https://www.wishket.com/project/159312/>
15. TypeSafe, Jev Model changelog. <https://docs.typesafe.ai/changelog>
