---
layout: post
title: "위키독스 무료 AI 서적 5종 정리 — Codex·Claude·Veo3·n8n·Claude 아키텍트 인증"
date: 2026-11-04 01:26:08 +0900
categories: [ai, books]
tags: [wikidocs, codex, gpt-5.6, claude, claude-code, veo3, n8n, claude-certified-architect]
---

텔레그램 채널 [AI Innovation Studio](https://t.me/aiinnovationstudio) 가 위키독스에 무료 전자책 5종을 공개했다는 공지를 올렸다. 이 글은 각 책의 **위키독스 목차와 GitHub 저장소를 직접 열어 본 결과**를 정리한 것이다. 책마다 무엇을 다루는지, 언제 기준으로 썼는지, 그리고 그 내용이 지금(2026-11-04)도 공식 문서와 맞는지를 확인했다.

확인 방법은 다음과 같다.

- 별 수·라이선스·생성일·마지막 push 는 2026-11-04 01:25 KST 에 GitHub REST API 로 조회했다.
- 책의 저자 표기는 모두 `AI_Innovation_Studio` 다.
- 책 속 사실 중 **바뀌기 쉬운 것들**은 OpenAI·Anthropic·Google 의 1차 문서와 맞대어 봤다. 모델 이름, 시험 규정, API 사양 같은 것들이다.
- 책의 품질이나 정확도를 전수 검사하지는 않았다. 목차 수준의 소개와 일부 사실 대조까지가 이 글의 범위다.

## 한눈에

| # | 책 | 위키독스 | GitHub | 라이선스 | ★ | 기준 시점 |
|---|---|---|---|---|---|---|
| 0 | GPT & Codex 기초부터 고급까지 100 | [book/20375](https://wikidocs.net/book/20375) | [lsszz2100/Codex_King](https://github.com/lsszz2100/Codex_King) | MIT | 50 | GPT-5.6 / Codex CLI (2026-08) |
| 1 | Claude 기초부터 고급까지 100 | [book/19729](https://wikidocs.net/book/19729) | [lsszz2100/Claude_100](https://github.com/lsszz2100/Claude_100) | MIT | 65 | 2026-05-03 |
| 2 | 처음 시작하는 Google Veo 3 | [book/19471](https://wikidocs.net/book/19471) | [astrabit-dev/New_Veo3](https://github.com/astrabit-dev/New_Veo3) | **없음** | 21 | 2026-04-03 (Veo 3.1·Lite 반영) |
| 3 | n8n AI 자동화 가이드 | [book/19485](https://wikidocs.net/book/19485) | [lsszz2100/n8n_Auto_Guide](https://github.com/lsszz2100/n8n_Auto_Guide) | MIT | 17 | 저장소 마지막 push 2026-04-05 |
| 4 | Claude Architect 자격증 준비 가이드 | [book/19518](https://wikidocs.net/book/19518) | [lsszz2100/Claude-architect-Certification](https://github.com/lsszz2100/Claude-architect-Certification) | **없음** | 41 | 저장소 마지막 push 2026-04-05 |

다섯 권 모두 같은 구조를 쓴다. GitHub 저장소에 `TOC.md` + `pages/*.md` 로 마크다운 원고를 두고, 그것을 위키독스로 출판한다. 위키독스가 웹 화면이고 GitHub 가 원본인 셈이다.

라이선스는 두 갈래다. 0·1·3번은 MIT 다. 2번 Veo 와 4번 Architect 저장소에는 **라이선스 파일이 없다.** GitHub 문서에 따르면 라이선스가 없는 저장소는 기본 저작권법이 적용된다. 열람과 포크는 할 수 있지만, 복제·배포·2차 저작에 대한 허락은 주어지지 않은 상태다([GitHub Docs — Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)). 원고를 사내 교육 자료로 가공해 쓰려는 경우라면 이 차이가 중요하다.

## 0. GPT & Codex 기초부터 고급까지 100

**구성.** 초급(1–30) → 중급(31–60) → 고급(61–) → 실전 프로젝트 → 부록 순서다. 1인 SaaS 「TaskFlow」 하나를 관통 예제로 처음부터 끝까지 만든다. README 기준 분량은 100개 절, 본문 약 19만 자다.

**다루는 범위.**

- 초급: 설치·로그인·`/diff`·세션 관리 같은 기본기
- 중급: `config.toml`, `AGENTS.md`, 샌드박스 3모드, 승인 정책, MCP, Skills, `codex exec`
- 고급: Codex 내부 구조. Rust 모노레포, SQ/EQ 큐 프로토콜, compaction 원리, `apply_patch` 포맷, execpolicy(Starlark), OS 샌드박스(Seatbelt/landlock), Hooks, SDK(TS·Python), app-server JSON-RPC

공식 사용법을 넘어 **엔진 내부까지 들어간다**는 점이 다른 입문서와 다르다.

**사실 대조.**

- **모델 이름.** 책은 GPT-5.6 Sol·Terra·Luna 를 기준으로 한다. OpenAI 는 2026-07-09 에 이 세 가지를 일반 공개했고, 숫자는 세대, Sol·Terra·Luna 는 성능 등급이라고 설명한다([OpenAI — GPT‑5.6](https://openai.com/index/gpt-5-6/)). 책의 기준과 맞는다.
- **가격.** 공지 이후 OpenAI 가 Luna·Terra(7/30), Sol(8/21) 가격을 내렸다고 같은 페이지에 갱신해 두었다. 책에 적힌 가격은 공식 페이지에서 다시 확인하는 게 좋다.
- **AGENTS.md 32KiB.** 35절 제목의 "32KiB" 는 공식 문서에 적힌 `project_doc_max_bytes` 기본값과 같다([Codex — AGENTS.md](https://developers.openai.com/codex/guides/agents-md)). 다만 이 한도는 **파일별이 아니라 루트부터 현재 디렉터리까지 모든 AGENTS.md 를 합친 누적 한도**다. 큰 루트 파일이 예산을 다 쓰면 하위 디렉터리의 파일은 통째로 빠진다. 이 동작은 OpenAI 저장소 이슈에서 코드로 확인됐다([openai/codex#36371](https://github.com/openai/codex/issues/36371)). 이 부분을 읽을 때 같이 보면 좋다.

## 1. Claude 기초부터 고급까지 100

**구성.** 제목은 100이지만 실제 목차는 000–120 이다. 101–120 이 템플릿·체크리스트·최종 프로젝트 10개 같은 부록이다. 위키독스 소개는 다음 순서의 학습 경로를 제시한다.

1. 기본 개념(001–010)
2. 프롬프트 구조(011–020)
3. Claude Code 안전 습관(021–030)
4. 프로젝트 메모리(031–037)
5. 업무별 프롬프트(038–055)
6. 비용·컨텍스트(056–065)
7. Skills·Hooks·MCP·Subagents(066–100)

**눈에 띄는 점.**

- 저장소에 `tools/check_wikidocs_book.ps1` 검증 스크립트가 있다. 커밋 전에 링크·이미지 경로, 페이지 번호와 TOC 순서, **토큰·private key 패턴**을 검사한다. 원고 저장소에 시크릿 스캔을 넣어 둔 것은 다른 책 저장소에서도 참고할 만하다.
- 팀 도입이 목적이라면 083(MCP)·092(Subagents)·100(운영 전략)·118(팀 도입 가이드)부터 보라고 권한다.

**시점.** 기준일이 2026-05-03 이고, 저장소 마지막 push 는 2026-08-03 이다. Claude Code 는 업데이트가 잦다. 그래서 명령어·설정 키 같은 세부 사항은 [Claude Code 공식 문서](https://docs.claude.com/en/docs/claude-code/overview)와 대조하면서 읽는 편이 안전하다.

## 2. 처음 시작하는 Google Veo 3

**구성.** 18개 파트에 약 130쪽이다. 기초 → Google Flow 사용법 → 핵심 기능 → 프롬프트 공식 순서로 진행한다. 프롬프트 공식은 캐릭터·행동·카메라·조명·장르·모션·환경·색상의 8요소다. 그다음 오디오·대화, 카메라 마스터클래스, 장르별 템플릿, JSON 프롬프트, 플랫폼별 최적화, 크레딧 절약, 수익화, 윤리·법률이 이어진다. **도구 사용법보다 프롬프트 예시와 템플릿 비중이 큰 책**이다.

**사실 대조.** 책이 다루는 기능 이름들은 Google 공식 자료와 일치한다.

- 8초 클립, 네이티브 오디오, SynthID 워터마크, 클립 연장(Extend), 첫·끝 프레임
- 출처: [Google Developers Blog — Veo 3.1](https://developers.googleblog.com/introducing-veo-3-1-and-new-creative-capabilities-in-the-gemini-api/), [Gemini API — Veo](https://ai.google.dev/gemini-api/docs/veo)
- Veo 3.1 Lite 는 2026-03-31 에 공개됐다. 4·6·8초 길이와 720p·1080p 를 지원한다([Google — Veo 3.1 Lite](https://blog.google/innovation-and-ai/technology/ai/veo-3-1-lite/)).

**⚠️ 시점 주의.** Gemini API 문서 상단에 새 공지가 붙었다. Veo 3.1 Preview 모델 3종(`veo-3.1-generate-preview`·`-fast-`·`-lite-`)이 **2026-10-22 에 Gemini API 에서 종료**됐다는 내용이다. Gemini Omni Flash 나 Enterprise 플랫폼의 GA 모델로 옮기라고 안내한다([Gemini API — Veo](https://ai.google.dev/gemini-api/docs/veo)). 책은 2026-04 기준이라 이 변화가 반영돼 있지 않다.

- **Flow·Gemini 앱으로 쓰는 독자:** 프롬프트 기법 부분은 여전히 쓸모가 있다.
- **API 로 연동하려는 독자:** 모델 ID 부분은 현재 문서로 바꿔 읽어야 한다.

저장소 마지막 push 는 2026-04-05 다.

## 3. n8n AI 자동화 가이드

**구성.** 10개 챕터, 78쪽이다(README 기준).

- 기초(1–4장): 자동화 개념 → 설치(Cloud·Docker·npm) → 노드·JSON·표현식·HTTP Request → 분기·루프·에러 처리
- AI(5장·7장): AI Agent 노드, LLM 체인, 메모리, OpenAI·Claude 연동, RAG, 멀티 에이전트
- 실전(6장): Gmail·Slack·Telegram·Sheets·Notion
- 운영(8–9장): Sub-workflow·API·커스텀 노드, 백업·업그레이드·권한·모니터링

**참고할 점.**

- 2장의 "Cloud vs Self-Hosting" 을 고를 때는 n8n 의 라이선스도 같이 봐야 한다. n8n 은 OSI 오픈소스가 아니라 **Sustainable Use License(fair-code)** 를 쓴다. 내부 업무용 셀프호스팅은 허용되지만, n8n 을 상품으로 재판매·호스팅하는 데는 제한이 있다([n8n — LICENSE.md (Sustainable Use License)](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)).
- 책 README 와 위키독스 첫 화면에는 "템플릿 수천 개 무료 증정" 카카오톡 오픈채팅 안내가 크게 들어가 있다. 공지에 적힌 "n8n 프롬프트 팩"은 아직 "제공 예정" 상태다.

## 4. Claude Architect 자격증 준비 가이드

**대상 시험.** Anthropic 의 **Claude Certified Architect – Foundations** 다. 공식 소개에 따르면 Claude Code·Claude Agent SDK·Claude API·MCP 에 걸친 기초 지식과, 실제 구현에서의 트레이드오프 판단을 평가한다([Anthropic Academy — 시험 페이지](https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request)).

**책의 시험 정보는 공식 시험 가이드와 일치했다.**

| 항목 | 책 README | 공식 Exam Guide |
|---|---|---|
| 형식 | 4지선다, 오답 감점 없음 | 정답 1 + 오답 3, 추측 감점 없음 |
| 합격 | 720 / 1000 | scaled 100–1,000 중 720 |
| 시나리오 | 6개 중 4개 랜덤 | 6개 중 4개 무작위 |
| 도메인 비중 | 27 / 18 / 20 / 20 / 15% | Agentic Architecture 27, Tool Design & MCP 18, Claude Code 20, Prompt Eng. & Structured Output 20, Context Mgmt & Reliability 15 |

([공식 Exam Guide PDF](https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F8lsy243ftffjjy1cx9lm3o2bw%2Fpublic%2F1773274827%2FClaude+Certified+Architect+%E2%80%93+Foundations+Certification+Exam+Guide.pdf))

**구성.** 장 구성이 시험 도메인을 그대로 따라간다. 도메인 1–5 를 Chapter 4–16 에 대응시켰고, 그 안에 다음 주제가 들어 있다.

- `stop_reason`
- Hub-and-Spoke 멀티에이전트
- Agent SDK Hooks, `fork_session`
- `tool_choice`
- `.claude/rules/`
- Message Batches API
- Lost-in-the-Middle

그 뒤로 공식 가이드의 6개 시나리오(고객 지원·코드 생성·멀티에이전트 연구·개발 생산성·CI/CD·구조화 추출)를 장마다 하나씩 다룬다. 샘플 문제 해설, 도메인별 연습 문제 50선, 12주 학습 계획이 이어진다.

**주의할 점.**

- 응시 자격·가격·시험 시간 같은 운영 정보는 책보다 **공식 시험 페이지를 기준으로** 확인해야 한다. 시험 가이드 버전이 바뀔 수 있고, 책 저장소의 마지막 push 는 2026-04-05 다. 위키독스 쪽은 2026-11-03 까지 편집 기록이 있다.
- 책의 연습 문제 50선은 저자가 만든 문제다. 공식 문항이 아니다. 공식 가이드에 실린 예시 문항과는 따로 구분해서 봐야 한다.

## 이렇게 고르면 된다

- **에이전트 코딩을 처음 시작한다면:** 0번(Codex)이나 1번(Claude) 가운데 실제로 쓰는 도구 쪽을 고르면 된다. 둘 다 초급 → 고급 → 실전 프로젝트 순서라 구조가 비슷하다. 내부 구조까지 파고드는 쪽은 0번이다.
- **노코드 자동화를 하고 싶다면:** 3번(n8n)이다.
- **AI 영상 프롬프트를 배우고 싶다면:** 2번(Veo)이다. API 부분은 10/22 이후 바뀐 모델 상황을 감안해야 한다.
- **Anthropic 자격증을 준비한다면:** 4번이다. 시험 범위 대응표로 쓰기 좋다. 다만 원본은 공식 Exam Guide 다.

다섯 권 모두 무료로 공개돼 있다. 하지만 다루는 도구들의 버전 주기가 몇 주 단위라서, 책의 기준일을 먼저 보고 읽는 게 가장 중요하다.

## References

**원 공지·저자**
- AI Innovation Studio (Telegram) — <https://t.me/aiinnovationstudio>

**책 (위키독스 / GitHub)**
- GPT & Codex 기초부터 고급까지 100 — <https://wikidocs.net/book/20375> · <https://github.com/lsszz2100/Codex_King>
- Claude 기초부터 고급까지 100 — <https://wikidocs.net/book/19729> · <https://github.com/lsszz2100/Claude_100>
- 처음 시작하는 Google Veo 3 — <https://wikidocs.net/book/19471> · <https://github.com/astrabit-dev/New_Veo3>
- n8n AI 자동화 가이드 — <https://wikidocs.net/book/19485> · <https://github.com/lsszz2100/n8n_Auto_Guide>
- Claude Architect 자격증 준비 가이드 — <https://wikidocs.net/book/19518> · <https://github.com/lsszz2100/Claude-architect-Certification>

**1차 출처 (사실 대조용)**
- OpenAI — [GPT‑5.6: Frontier intelligence that scales with your ambition](https://openai.com/index/gpt-5-6/) (2026-07-09, 이후 가격 갱신 포함)
- OpenAI Developers — [Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- openai/codex — [Issue #36371: project_doc_max_bytes 는 누적 한도](https://github.com/openai/codex/issues/36371)
- Anthropic Academy — [Claude Certified Architect – Foundations](https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request) · [Exam Guide (PDF)](https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2F8lsy243ftffjjy1cx9lm3o2bw%2Fpublic%2F1773274827%2FClaude+Certified+Architect+%E2%80%93+Foundations+Certification+Exam+Guide.pdf)
- Anthropic — [Claude Code documentation](https://docs.claude.com/en/docs/claude-code/overview)
- Google Developers Blog — [Introducing Veo 3.1](https://developers.googleblog.com/introducing-veo-3-1-and-new-creative-capabilities-in-the-gemini-api/) (2025-10-15)
- Google — [Veo 3.1 Lite](https://blog.google/innovation-and-ai/technology/ai/veo-3-1-lite/) (2026-03-31)
- Google AI for Developers — [Generate videos with Veo 3.1 in Gemini API](https://ai.google.dev/gemini-api/docs/veo) (Preview 2026-10-22 종료 공지)
- n8n — [LICENSE.md (Sustainable Use License)](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- GitHub Docs — [Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
- GitHub REST API — 저장소 메타데이터 조회 (2026-11-04 01:25 KST)
