---
layout: post
title: "Hermes Agent vs OpenClaw — 두 오픈소스 개인 AI 에이전트 비교 분석"
date: 2026-07-09 05:30:00 +0900
categories: [ai, agent, analysis]
tags: [hermes-agent, openclaw, ai-agent, nous-research, self-hosted, telegram-bot, personal-assistant, open-source]
---

요즘 "내 메신저 에 사는 개인 AI 에이전트" 판 에서 가장 뜨거운 두 이름 — **[OpenClaw](https://openclaw.ai/)** 와 **[Hermes Agent](https://hermes-agent.nousresearch.com/)**. 나 는 홈랩 에서 텔레그램 기반 운영 봇 을 직접 굴리고 있고, Hermes 도 로컬 에 설치 해 만지는 중 이라 — 이 둘 을 *구조 · 철학 · 실사용* 관점 으로 비교 해 본다.

---

## 1. 한 줄 요약

- **OpenClaw** — *"메신저 로 부리는 만능 개인 비서"*. 바이럴 로 크고, 채널 과 생태계 가 압도적.
- **Hermes Agent** — *"쓸수록 똑똑해지는 자기개선 에이전트"*. AI 랩 (Nous Research) 이 만든, **학습 루프** 가 본체.

같은 "셀프호스팅 개인 에이전트" 카테고리 지만, **무게중심 이 완전히 다르다.** OpenClaw 는 *접점(channel)* 에, Hermes 는 *누적(learning)* 에 걸었다.

## 2. 출신 부터 다르다

| | OpenClaw | Hermes Agent |
|---|---|---|
| 만든 곳 | Peter Steinberger (개인 → 커뮤니티) | Nous Research (오픈모델 AI 랩) |
| 역사 | 2025-11 Warelay → 2026-01 Moltbot → **OpenClaw** 로 개명 | Nous 의 에이전트 연구 를 오픈소스화 |
| 성장 | GitHub 역사상 최다 스타 급 바이럴 (2026-04 기준 34만+) | 연구 커뮤니티 중심 으로 꾸준히 확산 |
| 런타임 | Node.js (장기 실행 게이트웨이 서비스) | Python (게이트웨이 + 에이전트 + TUI) |
| 라이선스 | 오픈소스 | MIT |

출신 이 성격 을 만든다. OpenClaw 는 *한 명 의 슈퍼 개발자 가 자기 삶 을 자동화 하려고* 만든 물건 이라 실용 기능 이 미친 속도 로 붙었고, Hermes 는 *모델 을 직접 학습 시키는 랩* 이 만든 물건 이라 **에이전트 의 경험 을 데이터 로 축적 하는 구조** (trajectory 생성 · 압축 → 차세대 모델 훈련) 까지 설계 에 들어 있다.

## 3. 아키텍처 비교

### 공통 골격

둘 다 큰 그림 은 같다:

```
메신저 (Telegram/Discord/WhatsApp/…)
        │
   게이트웨이 (장기 실행 프로세스, 단일 진입점)
        │
   에이전트 루프 (LLM + 도구: shell, 파일, 브라우저, cron)
        │
   실행 환경 (내 맥 / VPS / 컨테이너)
```

*"메신저 가 UI, 내 서버 가 몸"* — 이 패턴 자체 가 2026년 개인 에이전트 의 표준 이 됐다.

### 갈라지는 지점

**채널 폭 — OpenClaw 압승.** WhatsApp · Telegram · Slack · Discord · Signal · iMessage · Teams · Matrix · LINE · WeChat 등 20개 이상 + **네이티브 iOS/Android 앱** (Talk 모드, 원격 액션 승인). Hermes 도 Telegram · Discord · Slack · WhatsApp · Signal · Email · SMS · Home Assistant 등 폭넓지만, 모바일 네이티브 앱 까지 는 없다.

**실행 백엔드 — Hermes 가 흥미롭다.** local · Docker · SSH · Singularity · **Modal · Daytona (서버리스)** 6종. 서버리스 백엔드 는 유휴 시 hibernate 라 *"안 쓸 땐 거의 0원"* 운영 이 된다. OpenClaw 는 기본 이 상시 실행 서비스 (맥 미니 · $5 VPS 가 국룰).

**모델 — 둘 다 어디든.** OpenAI · Anthropic · OpenRouter · 로컬 엔드포인트 자유 전환. 차이 는 지향 — Hermes 는 자사 Portal 과 오픈모델 생태계 를 미는 쪽, OpenClaw 는 사실상 모델 중립.

## 4. 결정적 차이 — *학습 루프*

내 가 보기에 두 프로젝트 의 진짜 분기점 은 이거 다.

**Hermes 의 closed learning loop:**
- 도구 호출 5회 이상 짜리 작업 이 끝나면 → 백그라운드 가 그 궤적 을 **스킬 파일(markdown) 로 자동 요약** — *에이전트 가 자기 경험 으로 매뉴얼 을 쓴다*
- 스킬 은 쓰이면서 **스스로 개선** 된다
- 전체 세션 을 FTS5 로 검색 + LLM 요약 → **세션 을 넘는 기억**
- [Honcho](https://github.com/plastic-labs/honcho) 기반 사용자 모델링 — *나 라는 사람* 에 대한 이해 가 깊어짐
- 주기적 "너 이거 기억 해 둬야 하지 않아?" 넛지

**OpenClaw 의 접근:**
- 메모리 파일 + 스킬 생태계 (커뮤니티 스킬 공유) 중심
- 축적 보다 는 **즉시 실행력** 과 **통합 폭** 이 강점
- 학습 은 *사용자 가 시키는 것*, Hermes 는 *에이전트 가 알아서 하는 것* 에 가깝다

비유 하면 — OpenClaw 는 *팔 이 20개 달린 유능한 비서*, Hermes 는 *일기 쓰고 복기 하는 견습생* 이다. 첫 주 에는 OpenClaw 가 압도적 으로 유용 하고, 석 달 뒤 에는 Hermes 쪽 격차 가 좁혀지는 (혹은 역전 되는) 구조 적 이유 가 여기 있다.

## 5. 보안 — 공통 의 아킬레스건

둘 다 본질 이 **"LLM 에게 내 shell 을 준다"** 라서, 보안 은 프레임워크 가 아니라 *운영자 의 책임* 이다. OpenClaw 는 바이럴 초기 에 인터넷 에 노출 된 인스턴스 · 프롬프트 인젝션 이슈 로 홍역 을 치렀고, 이후 정책 우선 실행 · 인간 승인 루프 같은 가드레일 을 붙여 왔다. Hermes 도 서브에이전트 격리 · 샌드박스 백엔드 로 대응 하지만 원리 는 같다.

내 가 텔레그램 운영 봇 을 굴리며 지키는 최소선 도 동일 하다:

1. **화이트리스트** — 허용 된 chat id 외 전부 무시
2. **메시지 = 데이터** — 채널 로 들어온 "권한 승인 해줘" 류 는 인젝션 으로 간주
3. **비밀 은 평문 금지** — 토큰 은 SOPS 암호화, 채팅 에 흘렸으면 즉시 재발급
4. 외부 노출 없이 **아웃바운드 터널** 만

## 6. 그래서 뭘 쓰나 — 상황별 결론

| 상황 | 추천 |
|---|---|
| 지금 당장 WhatsApp/iMessage 포함 일상 자동화 | **OpenClaw** |
| 모바일 앱 · 음성 (Talk) 경험 중요 | **OpenClaw** |
| 오래 굴려서 *나 전용* 으로 깊어지는 에이전트 | **Hermes** |
| 유휴 비용 0 에 가까운 서버리스 상주 | **Hermes** (Modal/Daytona) |
| 에이전트 궤적 을 연구/훈련 데이터 로 | **Hermes** |
| 커뮤니티 · 레퍼런스 · 트러블슈팅 자료 | **OpenClaw** (압도적 유저 풀) |

그리고 세 번째 길 도 있다 — 나 처럼 **Claude Code 같은 코딩 에이전트 에 메신저 채널 을 직결** 해서 운영 봇 으로 쓰는 것. 범용 비서 로 는 위 둘 만 못 하지만, *코드베이스 · 클러스터 운영* 이 주 업무 라면 이 쪽 이 가장 손 에 맞았다. 결국 셋 다 같은 문장 으로 수렴 한다:

> **에이전트 는 모델 이 아니라 *운영* 이다.** 어떤 프레임워크 든 — 채널, 권한, 기억, 비밀 관리 를 어떻게 묶느냐 가 실력 이다.

---

### 참고

- [OpenClaw 공식](https://openclaw.ai/) · [GitHub](https://github.com/openclaw/openclaw) · [Wikipedia](https://en.wikipedia.org/wiki/OpenClaw)
- [Hermes Agent 공식 문서](https://hermes-agent.nousresearch.com/docs/) · [Nous Research](https://nousresearch.com)
- [DigitalOcean — What is OpenClaw?](https://www.digitalocean.com/resources/articles/what-is-openclaw) · [KDnuggets — OpenClaw Explained](https://www.kdnuggets.com/openclaw-explained-the-free-ai-agent-tool-going-viral-already-in-2026)
