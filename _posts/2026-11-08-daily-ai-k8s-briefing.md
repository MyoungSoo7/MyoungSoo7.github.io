---
layout: post
title: "데일리 AI·Kubernetes·프리랜서 브리핑 — 2026-11-08"
date: 2026-11-08 08:30:00 +0900
categories: [AI, Kubernetes, Cloud, Freelance]
tags: [AI, Claude, Kubernetes, MCP, MLOps, 보안, Java, Spring]
---

> 기준 시각: 2026-11-08 08:30 KST. 수집 범위는 11-06~11-07 공개 자료이며, 11-07 브리핑과 겹치는 소식은 새 진전이 있을 때만 다룹니다. 오늘(11-08)·어제(11-07)가 아닌 항목은 날짜를 붙이고 "최신 아님"으로 표시합니다. 일요일 아침이라 공식 릴리스가 적은 날입니다.

**표기 규칙:** [사실] 공식·1차 출처로 확인 / [벤더 주장]·[회사 자체 주장] 벤더·회사 자체 수치·평가 / [보도] 언론 보도 / [추론] 필자 판단 / [미확인] 원문 확인 불가.

## 오늘의 핵심

1. **OpenSSH 10.6p2가 "sshole" 인증 우회(CVE-2026-123158)를 고쳤습니다.** musl libc에 PAM 없이 빌드한 sshd(대표적으로 Alpine)에서 257~1024바이트 길이의 아무 비밀번호로 로그인이 됩니다. 11-05 공개분으로 이전 브리핑에서 놓친 항목입니다. [1][2][3][4]
2. **SonicWall이 악용 중인 SSLVPN MFA 우회 취약점의 수정 펌웨어를 냈습니다.** 11-07 브리핑의 미확인 항목(수정 빌드)이 보도로 채워졌습니다. 우회책은 없습니다. [8]
3. **Chainalysis 침해로 전 고객의 자격 증명이 노출됐습니다.** 비밀번호 재설정과 API 키 교체가 필요하며, 회사는 공격자가 "offensive agentic techniques"를 썼다고 밝혔습니다. [9]
4. **Anthropic이 에이전트 메모리 연구 "The components of agent memory"를 공개했습니다.** 오프라인 정리 단계("dreaming")와 CL-Bench 1.0 결과를 담았으며, 수치는 벤더 주장입니다. [12]
5. **카카오가 3B 멀티모달 의사결정 모델 Kanana-2-v-decide를 오픈소스로 공개했습니다.** Jev 호환 API를 쓰며, 자세한 내용은 맨 끝 8번 특별 섹션에 있습니다. [44]

---

## 1. AI & ML

**Anthropic, "The components of agent memory" (11-06, 최신 아님)** [12]

- [사실] 이 글은 에이전트 메모리를 세 요소로 나눕니다. 메모를 기록하는 단계, 무엇을 남길지 정하는 중요도(salience) 판단, 세션 밖에서 기록을 재정리하는 오프라인 통합("dreaming")입니다. 오프라인 통합은 Letta·UC Berkeley의 sleep-time compute 연구를 인용합니다.
- [벤더 주장] Claude Managed Agents 위에서 CL-Bench 1.0으로 평가했습니다. Anthropic은 Opus 5가 처음으로 "학습 루프"를 닫았고, Opus 5.5와 Sonnet 5.5도 루프를 닫는다고 밝혔습니다. 두 모델은 메모리 없이도 메모리를 쓴 Opus 5와 비슷한 점수를 냈다고 합니다.
- [벤더 주장] 포켓몬 레드 사례:
  - Sonnet 3.7은 폴더 225개에 파일 413개를 남기고 배지 1개를 얻었습니다.
  - Fable 5는 폴더 2개에 파일 9개와 global.md만 남기고 배지 4개를 얻었습니다.
  - Opus 5.5는 게임을 끝까지 클리어했습니다.
- [벤더 주장] "실패만 기록하라"는 규칙은 Opus 5와 4.7의 메모리 이득을 줄였습니다. 메모리 사용법을 지시하는 조향(steering)은 구형 모델에서 효과가 가장 컸습니다.
- 근거 한계: CL-Bench 점수표는 본문 텍스트로 확인한 범위만 옮겼습니다. 외부 집계 사이트에만 있는 수치는 쓰지 않았고, 중립 제3자의 재현은 부재합니다.

**같은 날 올라온 Anthropic 연구 글 (11-06)** [13]

- "AI for scientific discovery: How researchers use Claude"와 객원 글 "Teaching AI to build scientific models"(Macke·Gedon·Wahl)가 연구 목록에 올라왔습니다.
- [미확인] 첫 글은 본문 수집에 실패해 세션 수 등 수치를 옮기지 않았습니다.

**Anthropic IPO 관련 보도 (11-07)** [14]

- [보도] CNBC는 Anthropic이 11월 중순 나스닥 상장을 노리고 있으며, 목표 기업가치가 1조~1.5조 달러라고 보도했습니다. 수정 증권신고서에는 약 8,954억 달러 규모의 컴퓨트·인프라 약정이 적혀 있다고 합니다.
- [보도] 같은 기사는 이번 중간선거에서 데이터센터 관련 주민투표 41건 가운데 40건이 반대로 결론 났다고 전했습니다.
- [미확인] 상장 시점과 가치는 회사가 확정 발표한 내용이 아닙니다.
- Claude Platform 릴리스 노트는 11-05 이후 새 항목이 없습니다. [15]

## 2. AI 에이전트 프레임워크

- [사실] **CrewAI 1.15.37 (11-07 02:18 UTC)**: crewai-files가 스프레드시트를 읽을 수 있게 됐고, 독립 실행형 에이전트 프로젝트를 스캐폴딩하고 로드하는 기능이 추가됐습니다. [16]
- LangGraph는 11-07 브리핑의 SDK 0.4.14 / CLI 0.4.42 이후 새 릴리스가 없습니다. [17]
- Devin 릴리스 노트도 변동이 없습니다. [18]

## 3. Kubernetes & Cloud Native

- [사실] v1.38.0-beta.0(11-06) 이후 새 태그가 없습니다. 최신 패치는 1.37.2, 1.36.6, 1.35.10(모두 10-28)입니다. [19][20]
- 공식 블로그의 마지막 글은 10-29입니다. v1.36/1.37 운영 지침에는 새로 바뀐 내용이 없습니다. [21]
- [추론] 다음 월간 패치는 11월 중순 예정 일정에 맞춰 나올 가능성이 높습니다. 운영 클러스터는 그 패치를 기다리는 것이 무난합니다.

## 4. 사이버 보안

**OpenSSH 10.6p2 — sshole, CVE-2026-123158 (11-05 공개, 최신 아님, 이전 브리핑 누락분)**

- [사실] OpenSSH 릴리스 노트에 따르면 10.6p2는 PAM 없이 musl libc로 빌드한 Linux용 긴급 수정입니다. OpenSSH는 AI가 찾은 버그 보고가 많이 들어오고 있어 릴리스를 더 자주 내겠다고 밝혔습니다. [1]
- [사실] NVD 설명: 10.6p2 이전 버전에서는 일부 계정 구성에서 256~1024자 길이의 어떤 비밀번호든 인증에 성공합니다. CNA(MITRE) 점수는 8.1이고, NVD 자체 평가는 아직 없습니다. [2]
- [사실] Alpine 권고가 밝힌 공격 조건은 다음을 모두 만족할 때입니다. [3]
  - PAM 없는 `openssh-server`를 쓰거나, `openssh-server-pam`을 `UsePAM no`로 씁니다.
  - `PasswordAuthentication yes`입니다(OpenSSH 기본값).
  - 비밀번호 필드가 `*`인 계정이 있습니다. 기본 이미지의 `root`, 비밀번호 없이 만든 키 전용 계정, 디렉터리 서비스 사용자, 공식 tiny-cloud 이미지의 `alpine` 사용자가 여기에 해당합니다.
  - 다른 로컬 계정 하나 이상이 `$5$`나 `$6$` 해시를 갖고 있습니다.
- [사실] Alpine은 점검한 모든 릴리스(3.21~3.24, edge)와 정기 업데이트가 끝난 3.16~3.20이 영향을 받는다고 밝혔습니다. 패키지만 올리고 sshd를 재시작하지 않으면 실행 중인 데몬은 그대로 취약합니다. [3]
- [사실] 즉시 패치할 수 없다면 `PasswordAuthentication no`로 바꾸고 sshd를 재시작하면 됩니다. 수정 커밋은 openssh-portable 4353fdc43입니다. [3][4][5]
- [보도] SecurityWeek와 BleepingComputer는 연구자 Özgün Kültekin이 발견했다고 전했습니다. tiny-cloud의 `alpine` 사용자는 비밀번호 없이 doas를 쓸 수 있어, 이 계정으로 들어오면 root 권한까지 이어질 수 있습니다. [6][7]
- [미확인] 실제 악용 여부: 일부 2차 매체가 악용 사례를 언급했지만 1차 근거를 확인하지 못했습니다.
- [추론] glibc 기반 배포판과 PAM을 쓰는 구성은 조건에서 벗어납니다. Alpine 기반 VM·베어메탈 sshd, 그리고 sshd를 띄운 컨테이너를 우선 점검하십시오.

**SonicWall SSLVPN MFA 우회 — 수정 펌웨어 공개 (11-07, 새 진전)** [8]

- [보도] 수정 버전은 7.3.4-7013(Gen7)과 8.2.3-8015(Gen8)입니다. 영향 범위는 Gen7 7.3.3-7015 이하와 Gen8 8.2.2-8015 이하입니다.
- [보도] 이번 권고에는 취약점 7건이 함께 묶였고 우회책은 없습니다. 발견자는 The Electronic Office의 Ryan Harris입니다.
- [미확인] SonicWall PSIRT 원문은 이번에도 본문 수집에 실패해 보도 기준으로 정리했습니다. KEV 기한(11-20)은 11-07 브리핑과 같습니다. [11]

**Chainalysis 침해 (11-06 보도)** [9]

- [보도] 모든 사용자의 이름, 사용자명, 비밀번호 해시, 유효한 토큰이 노출됐습니다. 회사는 이를 "on-path attack"으로 설명했고, 공격자가 "offensive agentic techniques"를 썼다고 밝혔습니다.
- [보도] Reactor, KYT 등 주요 제품과 포털을 오프라인으로 내렸습니다. 고객은 비밀번호를 재설정하고 API 키를 교체한 뒤 신뢰 IP를 제출해야 합니다.

**Crédit Mutuel Arkéa 탈취 사건 (11-07 보도)** [10]

- [보도] 공격자는 서비스 제공업체의 플랫폼을 거쳐 은행 자체 계정으로 자금을 빼냈습니다. 블록체인 조사자 ZachXBT는 피해액을 약 1억 1,800만 유로(1억 3,300만 달러)로 추정했고, 은행은 규모의 자릿수만 인정했습니다.
- [보도] 은행은 11-04에 공지했고 고객 자산은 영향이 없다고 밝혔습니다.
- [추론] 이번 주 Chainalysis와 이 사건 모두 제3자 플랫폼이 침투 경로였습니다. 공급자 계정의 권한 범위와 세션 토큰 수명을 다시 점검할 만합니다.

**Microsoft Entra Device Registration — CVE-2026-109469 (11-06 공개, 최신 아님)** [22]

- [사실] NVD에 따르면 Entra Device Registration에서 사용자가 제어하는 키로 인가를 우회하는(CWE-639) 원격 권한 상승입니다. CNA(Microsoft) 점수는 10.0이고 NVD 평가는 대기 중입니다.
- [사실] "Exclusively Hosted Service"로 분류돼 Microsoft가 서비스 측에서 조치하는 유형입니다.
- [미확인] MSRC 원문은 로드에 실패했습니다. 고객 조치가 필요한지는 확인하지 못했습니다.

- CISA 권고 페이지의 마지막 항목은 11-06이고, 11-07에는 KEV 추가가 없습니다. [11]

## 5. CSP

**AWS (11-06 미국 시간, 최신 아님)**

- [사실] Moonshot AI의 Kimi K3.1 Pro(Highspeed 포함)를 Amazon Bedrock에서 쓸 수 있게 됐습니다. 모델 성능 서술은 Moonshot의 벤더 주장입니다. [23]
- [사실] AWS Agent Registry가 GovCloud(US-West)에서 GA됐습니다. [24]
- [사실] Amazon Redshift SUPER 타입의 최대 크기가 1,600만 바이트로 늘었습니다. [25]
- [사실] AWS Glue Data Catalog가 Iceberg REST 페더레이션에서 카탈로그가 발급하는 자격 증명(catalog-vended credentials)을 지원합니다. [26]
- [사실] AWS Security Hub에서 SBOM 인벤토리를 볼 수 있습니다. [27]

**Google Cloud (11-06)** [28]

- [사실] Agent Registry의 독립 실행형 스킬(Skill·SkillRevision·Publisher)이 GA됐습니다.
- [사실] 스킬 리비전 보안 스캔과 조직 정책 기반 스캔 강제가 추가됐습니다. 스킬 페이로드 CMEK 암호화는 Preview입니다.
- [사실] BigQuery Graph와 GQL을 온디맨드 요금제에서 쓸 수 있습니다. Shopify 전송 커넥터의 일부 필드는 2027-01-31에 지원이 끝납니다.
- [추론] AWS와 GCP가 같은 날 에이전트 레지스트리 기능을 내놓았습니다. 에이전트·스킬을 배포 전에 등록하고 스캔하는 거버넌스 계층이 CSP 표준 기능이 되어 가는 흐름입니다.

**Azure·Naver Cloud**

- Azure 블로그에서는 11-07 브리핑 이후 새 항목을 확인하지 못했습니다. [29]
- 네이버 클라우드 공지의 마지막 항목은 10-23(장기 미로그인 서브계정 비밀번호 초기화, 11-24 시행)이며 변동이 없습니다. [30]

## 6. 개발 언어

- 네이버 D2가 "2026년과 이후 JavaScript의 동향" 연재 두 편을 11-06에 공개했습니다(최신 아님). [31][32]
  - [사실] 라이브러리·프레임워크 편은 React가 우위를 굳혔다고 보고, 공통 흐름으로 Signals, 서버로의 회귀, Rust 기반 빌드 도구, 웹 표준의 기능 흡수, AI 도구를 꼽습니다.
  - [회사 자체 집계] npm 주간 다운로드를 2020-11과 2026-09-28~10-04 사이로 비교했습니다. react는 8,869,607에서 224,422,510으로, vue는 1,962,540에서 20,397,470으로 늘었습니다. @angular/core는 2,076,121에서 7,300,962로, svelte는 101,464에서 7,724,778로 늘었습니다.
  - 두 번째 편은 WebAssembly를 다룹니다.
- Python, Rust, React, Vue, Kotlin, Spring Boot, TypeScript 모두 11-07 브리핑 이후 새 릴리스가 없습니다. [33][34][35][36][37][38]

## 7. Infrastructure & Linux

- 리눅스 7.3.3(11-06) 이후 새 안정판이 없고, linux-next는 next-20261105입니다. [39]
- 이번 주 인프라 쪽 조치는 4번 섹션의 OpenSSH 10.6p2가 가장 급합니다. Alpine은 3.16 이상 브랜치에 백포트 패키지를 냈습니다. [3]

## 9. AI 안전·정렬

- [벤더 주장] Anthropic 메모리 연구에서 메모리 사용을 지시하는 조향과 기록 규칙에 따라 성능이 크게 달라졌습니다. 이는 메모리가 장기 행동에 영향을 주는 경로라는 뜻이기도 합니다. [12]
- [보도] Chainalysis는 공격자가 에이전트형 공격 기법을 썼다고 밝혔고, OpenSSH는 AI가 찾은 버그 보고가 늘었다고 밝혔습니다. [1][9]
- [추론] AI가 공격과 취약점 발견 양쪽의 속도를 높이고 있다는 신호입니다. 패치 주기를 짧게 가져가는 것이 방어 측의 현실적 대응입니다.
- 이 기간 새 정렬 논문 가운데 따로 다룰 만한 항목은 확인하지 못했습니다.

## 10. MCP 에코시스템

- MCP 공식 블로그의 마지막 글은 10-30(Ruby SDK Tier 1)입니다. TypeScript SDK 2.4.0(10-23)과 Python SDK 2.3.0(10-02) 이후 새 릴리스가 없습니다. [40][41][42]
- [추론] GCP Agent Registry의 스킬 스캔·CMEK 기능은 MCP 서버·스킬을 조직 단위로 등록하고 통제하려는 팀이 함께 검토할 만합니다. [28]

## 11. MLOps·피처스토어

- MLflow 3.18.0과 Feast 0.67.0 이후 새 릴리스가 없습니다. [43][45]

## 12. 에이전트 관측성

- [사실] **arize-phoenix-otel v0.17.3 (11-06 23:31 UTC)**: Python과 TS가 `.env.phoenix`를 같은 방식으로 파싱하고(#17075), OTLP 프로토콜을 한 번만 결정합니다(#17531). [46]
- [사실] **arize-phoenix-client 7.18.2 (11-07 00:08 UTC)**: 프롬프트 변수 안의 리터럴 `$` 시퀀스를 그대로 보존합니다. [46]
- Langfuse는 v4.76.0 이후 변동이 없습니다. [47]

## 13. 그린 컴퓨팅

- Green Software Foundation 기사 목록은 11-05 물 사용 지표 글 이후 새 글이 없습니다. [48]

## 14. 한국 기업 기술 블로그

| 회사 | 제목 | 발행일 | 요약 | 링크 |
| --- | --- | --- | --- | --- |
| 카카오 | AI 에이전트를 위한 멀티모달 의사결정 모델 'Kanana-2-v-decide' 오픈소스 공개 | 2026-11-06 | 3B 멀티모달 의사결정 모델을 공개한 글입니다. Jev 호환 API를 쓰며, 8번 섹션에서 자세히 다룹니다. | [44] |
| LINE (LY Corp) | 녹화 버튼 뒤에서 일어나는 일: LINE 프리미엄콜 개발기 | 2026-11-06 | Android VoIP 통화 녹화 기능의 구현기입니다. 아래에 정리했습니다. | [49] |
| 네이버 D2 | 2026년과 이후 JavaScript의 동향 (라이브러리·프레임워크 / WebAssembly) | 2026-11-06 | 6번 섹션 참조. | [31][32] |

**LINE 프리미엄콜 녹화 (11-06)** [49]

- [사실] 처음부터 오디오·비디오 트랙을 모두 준비한 단일 파일로 녹화하고, 영상이 없는 구간에는 프로필 프레임을 넣습니다.
- [사실] 음성↔영상 전환 중에도 녹화 세션을 유지하고, 로컬과 원격 입력을 따로 처리합니다. 입력 해상도가 바뀌어도 출력 프레임 크기는 고정합니다.
- [사실] 온디바이스 STT(일본어 전용)는 다운샘플한 스트림을 모델에 넣고, 재생용 음질은 그대로 둡니다. 일본·대만·태국에서 LINE Labs 기능으로 제공됩니다.

**변동 없음**

- 토스의 마지막 글은 10-27, 당근의 마지막 글은 11-03입니다. 우아한형제들의 마지막 글(11-06 AI 거버넌스)은 11-07 브리핑에서 다뤘습니다. [50][51][52]
- 쿠팡의 공식 Medium은 2024년 이후 새 글이 없습니다. 두나무는 이번 회차에 확인하지 못했습니다.

## 15. Java/Spring 프리랜서

수집일: 2026-11-08. 위시켓 공개 상세 페이지 기준이며, 로그인이 필요한 정보는 수집하지 않았습니다.

| 플랫폼 | 제목 | 기술 스택 | 계약·근무 형태 | 금액(공개분) | 상태 | 링크 |
| --- | --- | --- | --- | --- | --- | --- |
| 위시켓 | React/Java/Spring 기반 보험사 계정계 개발 및 운영 | Java, Spring, React (중급 6~15년) | 기간제 360일, 서울 종로구 상주, 계약 직후 시작 | 월 6,500,000원 | 11-06 등록, 11-20 마감, 모집 중 (지원 8명) | [53] |
| 위시켓 | Java(EJB)/MiPlatform 기반 보험사 상품업무 시스템 운영 개발자 (고급) | Java(EJB), MiPlatform (고급 8~10년) | 기간제 360일, 종각역 인근 상주, 2026-12-01 시작 | 월 7,000,000원 | 11-05 등록(최신 아님), 11-19 마감, 모집 중 (지원 1명) | [54] |

- 첫 공고는 11-07 브리핑에서 목록만 확인했던 건입니다. 이번에 상세 페이지로 조건을 확인했습니다(새 진전).
- 두 번째 공고는 이번에 처음 싣지만, 등록일이 11-05라 새 공고가 아닙니다.
- 11-06 브리핑에서 다룬 위시켓 159482·159484·159485는 수집 시점에 아직 모집 중입니다. [55]
- 같은 목록의 인프라 엔지니어 공고와 하드웨어 PM 공고는 Java/Spring이 아니어서 제외했습니다.
- [미확인] 이랜서와 프리모아는 공개 목록에서 프로젝트 식별자를 읽지 못했습니다. 두 곳의 공고는 이번 회차에 검증하지 못했습니다.

---

## 8. 특별 섹션 — Jev API와 의사결정 모델

- [사실] Jev Changelog의 마지막 항목은 Jev 1.14(10-14)로 변동이 없습니다. [56]

**카카오 Kanana-2-v-decide 오픈소스 공개 (11-06 08:00 KST, 최신 아님)** [44]

- [사실] kanana-2-v-3b를 기반으로 한 3B 멀티모달 의사결정 모델입니다. Hugging Face에는 `kakaocorp/kanana-2-v-decide-3b-2611`로 공개됐습니다.
- [사실] Noul·Choice·Score 구조의 Jev 호환 API를 쓰며, 한 요청에 여러 질문을 묶을 수 있습니다.
- [사실] 선택지를 임베딩으로 처리합니다. 그래서 255개 선택지 제한이 없고 선택지 순서에 영향을 받지 않으며, 선택지 임베딩을 재사용할 수 있다고 설명합니다. 비교 대상은 Jev와 vLLM SR d3입니다.
- [사실] 학습에는 여러 교사 모델로 on-policy 증류하는 MOPD를 썼고, 안전 데이터 비중은 약 5%입니다.
- [회사 자체 주장] 다음 수치는 모두 카카오가 직접 측정한 값입니다.
  - 속도: H200 1장에서 결정당 약 42ms로, "GPT-6 Luna보다 43배 빠르다"고 밝혔습니다.
  - 트롤리 평가: 불필요한 해를 끼치는 선택은 286건에서 77건으로, 모순은 1,343건에서 851건으로 줄었습니다.
  - 보정: ECE가 2.06%에서 1.12%로 낮아졌습니다.
  - Kanana Decision Bench(텍스트): 72.62점으로 Microsoft-Decision-1(71.98), Jev 1.14.0(71.66)보다 높았습니다.
  - Decision Index 공개 텍스트 세트: 61.35점으로 Jev(60.70)보다 높았습니다.

**근거 한계와 해석**

- 모든 성능 수치는 회사가 직접 만든 벤치마크와 프로토콜에서 나온 값입니다. 중립 제3자의 헤드투헤드 비교와 독립 재현은 부재합니다.
- 점수 차이(0.6~1.0점대)가 통계적으로 유의한지는 글에서 확인하지 못했습니다.
- [추론] 3B 규모, Jev 호환 API, 저지연이라는 조합은 Jev를 쓰던 파이프라인에 온프레미스 대안을 시험하는 데 쓸 만합니다. 다만 11-07 브리핑의 JevBreak 같은 슬롯 공격 내성과 라이선스 조건을 먼저 확인해야 합니다.
- 11-05 이후 Jev 관련 새 arXiv 프리프린트는 확인하지 못했습니다.

---

## 사실 · 추론 · 미확인 정리

**사실 (공식 출처 확인)**

- OpenSSH 10.6p2 릴리스, CVE-2026-123158의 NVD 설명, Alpine 권고의 영향 조건과 완화책 [1][2][3]
- CVE-2026-109469의 NVD 기재 내용 [22]
- AWS 5건, GCP Agent Registry·BigQuery 업데이트 [23]–[28]
- CrewAI 1.15.37, Phoenix 릴리스 [16][46]
- 카카오·LINE·네이버 D2 글의 존재와 내용 [31][32][44][49]
- 위시켓 공고 2건의 공개 조건 [53][54]

**벤더·회사 주장 (독립 검증 부재)**

- Anthropic 메모리 연구의 모델 비교와 포켓몬 사례 [12]
- Kanana-2-v-decide의 속도·벤치마크·보정 수치, D2의 npm 자체 집계 [44][31]
- Kimi K3.1 Pro의 성능 서술 [23]

**보도**

- SonicWall 수정 빌드, Chainalysis와 Crédit Mutuel Arkéa 침해, Anthropic IPO 일정과 가치 [8][9][10][14]

**추론 (필자 판단)**

- Alpine 기반 sshd를 우선 점검하라는 권고, 제3자 플랫폼 경유 침해에 대한 점검 제안
- 에이전트 레지스트리가 CSP 표준 기능이 되어 간다는 해석, Kanana-2-v-decide의 활용 방안

**미확인**

- sshole의 실제 악용 여부, SonicWall PSIRT 원문, MSRC의 CVE-2026-109469 고객 조치 여부 [8][22]
- Anthropic "AI for scientific discovery" 본문 수치 [13]
- 이랜서·프리모아 공고, 두나무 기술 블로그

---

## References

1. OpenSSH, Release Notes (10.6p2). <https://www.openssh.com/releasenotes.html>
2. NVD, CVE-2026-123158. <https://nvd.nist.gov/vuln/detail/CVE-2026-123158>
3. Alpine Linux, Security advisory: openssh-server password authentication bypass. <https://alpinelinux.org/posts/2026-11-05-openssh-password-authentication-bypass/>
4. oss-security, OpenSSH 10.6p2 (2026-11-05). <https://openwall.com/lists/oss-security/2026/11/05/3>
5. openssh-portable, commit 4353fdc43. <https://github.com/openssh/openssh-portable/commit/4353fdc43ef646c43a8dda7025cc1a898caf1482>
6. SecurityWeek, OpenSSH rushes patches for sshole authentication bypass. <https://www.securityweek.com/openssh-rushes-patches-for-sshole-authentication-bypass/>
7. BleepingComputer, OpenSSH flaw lets attackers log into password-disabled Linux accounts. <https://www.bleepingcomputer.com/news/security/openssh-flaw-lets-attackers-log-into-password-disabled-linux-accounts/>
8. SecurityWeek, SonicWall patches exploited SonicOS bug that weakens VPN logins. <https://www.securityweek.com/sonicwall-patches-exploited-sonicos-bug-that-weakens-vpn-logins/>
9. BleepingComputer, Chainalysis says breach exposed credentials for all customers. <https://www.bleepingcomputer.com/news/security/chainalysis-says-breach-exposed-credentials-for-all-customers/>
10. BleepingComputer, Hackers pull off $133 million French bank heist via service provider. <https://www.bleepingcomputer.com/news/security/hackers-pull-off-133-million-french-bank-heist-via-service-provider/>
11. CISA, Known Exploited Vulnerabilities Catalog. <https://www.cisa.gov/known-exploited-vulnerabilities-catalog>
12. Anthropic, The components of agent memory. <https://www.anthropic.com/research/components-of-agent-memory>
13. Anthropic, Research. <https://www.anthropic.com/research>
14. CNBC, Anthropic IPO and AI data center backlash (2026-11-07). <https://www.cnbc.com/2026/11/07/anthropic-ipo-ai-data-center-backlash.html>
15. Anthropic, Claude Platform Release Notes. <https://platform.claude.com/docs/en/release-notes/overview>
16. CrewAI, Releases. <https://github.com/crewAIInc/crewAI/releases>
17. LangGraph, Releases. <https://github.com/langchain-ai/langgraph/releases>
18. Devin, API Release Notes. <https://docs.devin.ai/api-reference/release-notes>
19. Kubernetes, Releases (GitHub). <https://github.com/kubernetes/kubernetes/releases>
20. Kubernetes, Patch Releases. <https://kubernetes.io/releases/patch-releases/>
21. Kubernetes, Blog. <https://kubernetes.io/blog/>
22. NVD, CVE-2026-109469. <https://nvd.nist.gov/vuln/detail/CVE-2026-109469>
23. AWS, Moonshot AI Kimi K3.1 Pro on Amazon Bedrock. <https://aws.amazon.com/about-aws/whats-new/2026/11/moonshot-ai-kimi-k3-1-pro-on-amazon-bedrock>
24. AWS, AWS Agent Registry in GovCloud (US-West). <https://aws.amazon.com/about-aws/whats-new/2026/11/aws-agent-registry-govcloud-us-west/>
25. AWS, Amazon Redshift expands SUPER to 16 million bytes. <https://aws.amazon.com/about-aws/whats-new/2026/11/amazon-redshift-expands-super-to-16-million-bytes/>
26. AWS, Glue Data Catalog catalog-vended credentials for Iceberg. <https://aws.amazon.com/about-aws/whats-new/2026/11/glue-catalog-vended-credentials-iceberg/>
27. AWS, Security Hub SBOM inventory. <https://aws.amazon.com/about-aws/whats-new/2026/11/security-hub-sbom-inventory/>
28. Google Cloud, Release Notes (2026-11-06). <https://docs.cloud.google.com/release-notes>
29. Microsoft, Azure Blog. <https://azure.microsoft.com/en-us/blog/>
30. 네이버 클라우드 플랫폼, 공지사항. <https://www.ncloud.com/support/notice/all>
31. 네이버 D2, 2026년과 이후 JavaScript의 동향 - 라이브러리와 프레임워크. <https://d2.naver.com/helloworld/0627744>
32. 네이버 D2, 2026년과 이후 JavaScript의 동향 - WebAssembly. <https://d2.naver.com/helloworld/7770448>
33. Python, Downloads. <https://www.python.org/downloads/>
34. Rust, Blog. <https://blog.rust-lang.org/>
35. React, Releases. <https://github.com/facebook/react/releases>
36. Vue, Releases. <https://github.com/vuejs/core/releases>
37. Kotlin, Releases. <https://github.com/JetBrains/kotlin/releases>
38. Spring Boot, Releases. <https://github.com/spring-projects/spring-boot/releases>
39. kernel.org. <https://kernel.org/>
40. MCP, Blog. <https://blog.modelcontextprotocol.io/>
41. MCP, TypeScript SDK Releases. <https://github.com/modelcontextprotocol/typescript-sdk/releases>
42. MCP, Python SDK Releases. <https://github.com/modelcontextprotocol/python-sdk/releases>
43. MLflow, Releases. <https://github.com/mlflow/mlflow/releases>
44. 카카오, AI 에이전트를 위한 멀티모달 의사결정 모델 'Kanana-2-v-decide' 오픈소스 공개. <https://tech.kakao.com/posts/846>
45. Feast, Releases. <https://github.com/feast-dev/feast/releases>
46. Arize, Phoenix Releases. <https://github.com/Arize-ai/phoenix/releases>
47. Langfuse, Releases. <https://github.com/langfuse/langfuse/releases>
48. Green Software Foundation, Articles. <https://greensoftware.foundation/articles/>
49. LY Corporation, 녹화 버튼 뒤에서 일어나는 일: LINE 프리미엄콜 개발기. <https://techblog.lycorp.co.jp/ko/line-premium-call-recording>
50. 토스, Tech Blog. <https://toss.tech/>
51. 당근, Medium. <https://medium.com/daangn>
52. 우아한형제들, 기술 블로그. <https://techblog.woowahan.com/>
53. 위시켓, 프로젝트 159506. <https://www.wishket.com/project/159506/>
54. 위시켓, 프로젝트 159483. <https://www.wishket.com/project/159483/>
55. 위시켓, 프로젝트 목록. <https://www.wishket.com/project/>
56. TypeSafe, Changelog. <https://docs.typesafe.ai/changelog>
