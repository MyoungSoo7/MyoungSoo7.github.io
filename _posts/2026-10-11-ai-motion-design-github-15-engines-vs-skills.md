---
layout: post
title: "AI 를 모션 디자인 스튜디오로 — GitHub 프로젝트 15선, 실제로 열어 보니 무엇이 엔진이고 무엇이 스킬인가?"
date: 2026-10-11 21:22:38 +0900
categories: [AI, Tools]
tags: [Claude Code, Motion Design, Remotion, Hyperframes, GSAP, Motion, Agent Skills, Video]
---

텔레그램 채널에서 "AI 를 모션 디자인 스튜디오로 바꾸는 GitHub 프로젝트 15선" 이라는 정리 그림을 받았다. Claude Code 같은 AI 코딩 에이전트에 모션 디자인 능력을 더하는 저장소들을 다섯 분야로 묶은 것이다.

![AI 모션 디자인 스튜디오 — GitHub 프로젝트 15선](/assets/images/posts/ai-motion-design-github-15.jpg)

*그림 출처: [t.me/aiinnovationstudio](https://t.me/aiinnovationstudio) (AI 모션 디자인 스튜디오 가이드)*

목록만 보면 15개가 비슷해 보인다. 그래서 2026년 10월 11일 기준으로 **15개 저장소를 하나씩 GitHub API 로 열어** 스타 수, 라이선스, 마지막 업데이트를 확인했다. 결론부터 말하면 이 15개는 성격이 두 층으로 갈린다.

- **엔진(라이브러리·렌더러)**: 실제로 영상을 만들거나 애니메이션을 돌리는 본체. Remotion, Hyperframes, Motion, GSAP.
- **스킬(에이전트용 지침)**: 그 엔진을 AI 에이전트가 **잘 쓰게 가르치는** 문서·예제 묶음. 나머지 대부분.

## 1. 15개 저장소 실측표

수치는 2026-10-11 GitHub API 조회값이다. 스타 수는 계속 바뀐다.

| 분야 | 저장소 | 저장소 설명 (원문 요약) | ★ | 라이선스 | 최근 푸시 |
|---|---|---|---|---|---|
| 제품 소개 영상 | [AbubakrChan/product-launch-motion](https://github.com/AbubakrChan/product-launch-motion) | 제품 런칭 영상용 Claude Code 스킬 | 147 | MIT | 2026-08-27 |
| | [charlie947/motion-graphics-skills](https://github.com/charlie947/motion-graphics-skills) | 런칭급 모션 그래픽용 Claude Code 스킬 13개 | 187 | MIT | 2026-10-11 |
| | [howseen-ai/claude-motion-design](https://github.com/howseen-ai/claude-motion-design) | HTML + Playwright + ffmpeg 로 모션 영상을 만드는 스킬 | 426 | MIT | 2026-10-04 |
| 기존 영상 편집 | [nateherkai/hyperframes-student-kit](https://github.com/nateherkai/hyperframes-student-kit) | Codex·Claude Code 로 영상·쇼츠 편집, 스킬 14개 | 1,304 | MIT | 2026-09-28 |
| | [Barty-Bart/motion-graphics](https://github.com/Barty-Bart/motion-graphics) | Claude Code·Codex 용 모션 그래픽 스킬 | 593 | MIT | 2026-10-08 |
| 짧은 애니메이션 | [cth9191/animate](https://github.com/cth9191/animate) | 단일 파일 캔버스 영상으로 만드는 절차적 애니메이션 | 459 | MIT | 2026-10-05 |
| | [whaleyxbt/claude-motion](https://github.com/whaleyxbt/claude-motion) | 코딩 에이전트용 모션 디자인 툴킷 | 304 | MIT | 2026-10-09 |
| | [haidrrrry/claude-remotion-skill](https://github.com/haidrrrry/claude-remotion-skill) | Claude 가 Remotion 영상을 만들게 하는 스킬 | 375 | MIT | 2026-08-12 |
| 웹 애니메이션 | [motiondivision/motion](https://github.com/motiondivision/motion) | **엔진** — React·JavaScript 애니메이션 라이브러리 | 33,959 | MIT | 2026-10-09 |
| | [199-biotechnologies/motion-dev-animations-skill](https://github.com/199-biotechnologies/motion-dev-animations-skill) | Motion.dev 용 Claude Code 스킬 | 152 | MIT | 2026-03-30 |
| 핵심 도구·공식 | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | **엔진** — *"Write HTML. Render video. Built for agents."* | 60,589 | Apache-2.0 | 2026-10-11 |
| | [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | **엔진** — *"Make videos programmatically with React"* | 63,178 | Remotion License ⚠️ | 2026-10-11 |
| | [remotion-dev/skills](https://github.com/remotion-dev/skills) | Remotion 공식 에이전트 스킬 | 5,020 | 파일 없음 ⚠️ | 2026-10-07 |
| | [greensock/gsap-skills](https://github.com/greensock/gsap-skills) | GSAP 공식 AI 스킬 | 16,177 | MIT | 2026-07-29 |
| | [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) | 타이밍·이징·안무 같은 모션 원칙을 AI 에 적용 | 2,102 | MIT | 2026-05-18 |

15개 모두 실제로 존재하고, 보관(archived) 상태인 저장소는 없었다. 두 저장소(hyperframes-student-kit, motion-graphics)는 GitHub 가 라이선스를 자동 판별하지 못했지만, LICENSE 파일을 열어 보니 MIT 였다.

## 2. 무엇이 엔진이고 무엇이 스킬인가

스타 수가 두 자릿수 차이로 갈리는 이유가 여기 있다. Remotion(약 6.3만), Hyperframes(약 6.1만), Motion(약 3.4만)은 **영상·애니메이션을 실제로 만드는 엔진**이다. 나머지 대부분은 그 엔진을 AI 에이전트가 다루도록 돕는 **스킬**이다. 예를 들어 [claude-remotion-skill](https://github.com/haidrrrry/claude-remotion-skill) 과 [remotion-dev/skills](https://github.com/remotion-dev/skills) 는 Remotion 이 있어야 의미가 있고, [motion-dev-animations-skill](https://github.com/199-biotechnologies/motion-dev-animations-skill) 은 Motion 을 전제로 한다.

이 구분이 실무에서 중요한 이유는 두 가지다.

1. **스킬은 엔진 버전에 묶인다.** 엔진 API 가 바뀌면 스킬의 예제가 낡는다. 위 표에서 엔진은 대부분 조회 당일에도 푸시가 있었고, 스킬 중에는 몇 달째 멈춘 것도 있다. 스킬을 고를 때는 **엔진의 공식 스킬**(remotion-dev/skills, greensock/gsap-skills)이 있는지 먼저 본다.
2. **라이선스는 엔진 쪽에서 결정된다.** 스킬이 MIT 라도, 결과물을 만드는 엔진의 라이선스를 따라야 한다.

## 3. 라이선스에서 꼭 볼 것

### Remotion — "무료" 의 범위

Remotion 의 LICENSE 는 MIT 같은 표준 라이선스가 아니라 자체 **Remotion License** 다. 원문은 이렇게 시작한다.

> *"Individuals and small companies are allowed to use Remotion to create videos for free (even commercial), while a company license is required for for-profit organizations of a certain size."*

무료 대상은 개인, **직원 3명 이하** 영리 조직, 비영리 조직, 상업적으로 쓰기 전 평가 단계다. 그보다 큰 영리 조직은 회사 라이선스가 필요하다. 또 *"It is not allowed to copy or modify Remotion code for the purpose of selling, renting, licensing, relicensing, or sublicensing your own derivate of Remotion."* 이라는 금지 조항도 있다. 개인 실험에는 문제가 없지만, 회사 업무에 도입하려면 이 조건부터 확인해야 한다.

### remotion-dev/skills — 라이선스 파일이 없다

공식 저장소지만 조회 시점에 라이선스 파일이 없었다. GitHub 문서에 따르면 라이선스가 없으면 *"the default copyright laws apply, meaning that you retain all rights to your source code and no one may reproduce, distribute, or create derivative works from your work."* 이다. 내부 참고용으로 읽는 것과, 복사해 재배포하는 것은 다른 문제다.

그림 하단의 안내 문구 *"설치 전 각 저장소의 README와 라이선스를 확인하세요"* 가 장식이 아니라는 뜻이다.

## 4. 스킬 설치는 "코드 실행" 과 같다

에이전트 스킬은 문서처럼 보이지만, 실제로는 에이전트가 **그대로 따라 실행할 지시**다. 스킬 안에 "이 스크립트를 실행하라", "이 패키지를 설치하라" 가 들어 있으면 에이전트는 그 일을 한다. 그래서 출처가 개인 저장소인 스킬은 설치 전에 이렇게 본다.

- 스킬 파일(보통 `SKILL.md`)과 함께 들어 있는 **스크립트**를 직접 읽는다.
- **외부 네트워크 호출**(다운로드, 업로드, API 키 요구)이 있는지 본다.
- 가능하면 **공식 스킬**을 먼저 쓰고, 개인 스킬은 필요한 부분만 참고한다.
- 처음엔 격리된 폴더나 컨테이너에서 돌려 본다.

## 5. 어디서 시작할까

그림의 추천은 목적별로 이렇다. 위 실측을 반영해 한 줄씩 덧붙인다.

| 목적 | 그림의 추천 | 덧붙일 점 |
|---|---|---|
| 제품 소개 영상 | Remotion · Hyperframes | 회사에서 쓰면 Remotion License 조건 확인. Hyperframes 는 Apache-2.0 |
| 웹 애니메이션 | Motion · GSAP | 둘 다 엔진. GSAP 은 공식 AI 스킬(gsap-skills, MIT)이 있다 |
| 디자인 원칙·연출 | LottieFiles 스킬 | 특정 엔진에 묶이지 않는 원칙(타이밍·이징) 위주라 다른 스킬과 같이 쓰기 좋다 |

## 맺으며

"15선" 같은 목록은 출발점으로 좋지만, 목록의 항목은 같은 무게가 아니다. 몇 개는 수만 명이 쓰는 엔진이고, 나머지는 그 엔진 위에 얹는 얇은 지침이다. 무엇을 고르든 순서는 같다. **엔진을 먼저 정하고, 그 엔진의 라이선스를 확인하고, 공식 스킬이 있으면 그것부터 쓴다.** 개인 스킬은 그다음, 읽어 본 뒤에.

---

## References

- 그림: AI 모션 디자인 스튜디오 가이드, <https://t.me/aiinnovationstudio>
- 각 저장소 정보: GitHub REST API 조회 (2026-10-11) — 위 표의 링크
- Remotion License 원문: <https://github.com/remotion-dev/remotion/blob/main/LICENSE.md>
- GitHub Docs, *Licensing a repository*: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository>
