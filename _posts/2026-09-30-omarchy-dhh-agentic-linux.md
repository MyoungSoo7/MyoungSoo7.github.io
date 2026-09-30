---
layout: post
title: "Omarchy — DHH 가 만든 '에이전트가 고치는' 리눅스는 왜 생겼나"
date: 2026-09-30 22:16:00 +0900
categories: [linux]
tags: [omarchy, dhh, arch-linux, hyprland, quickshell, ai-agent, claude-code]
---

> 공식 사이트: **[omarchy.org](https://omarchy.org/)** · 소스: [github.com/omacom/omarchy](https://github.com/omacom/omarchy) (MIT)

Rails 를 만든 DHH(David Heinemeier Hansson)의 리눅스 배포판 **Omarchy** 가 2026년 8월 4.0(코드명 *Quattro*)을 냈다. 공식 사이트의 문구는 이렇게 바뀌었다. *"Beautiful, fun & agentic Linux"*, *"The malleable OS for the age of agents"*. 처음엔 Arch 설치 후 돌리는 설정 스크립트였다. 그게 1년 남짓 만에 "코딩 에이전트가 OS 를 고친다"를 전면에 내건 배포판이 됐다.

이 글은 기능을 나열하지 않는다. **"그 전엔 어땠고, 뭐가 문제였고, 그래서 뭐가 나왔는가"** 순서로 따라간다. 모든 사실은 1차 출처(공식 사이트·GitHub 릴리스 노트·DHH 본인 블로그)만 인용했다.

> ⚠️ 필자는 Omarchy 를 직접 설치해 보지 않았다. 아래의 설치 시간·다운로드 수·후원액은 전부 **프로젝트가 스스로 밝힌 수치**다. 중립적인 제3자 벤치마크는 찾지 못했다.

---

## 1. Before — 리눅스 데스크톱은 "조립 키트"였다

Arch Linux 와 Hyprland 조합은 성능과 미감으로 유명하다. 대신 **아무것도 들어 있지 않다.** DHH 는 2025년 6월 처음 이 조합을 만져 본 주말을 이렇게 적었다([Omarchy: Bottling that inspiration…](https://world.hey.com/dhh/omarchy-bottling-that-inspiration-before-it-spoils-cd75e26b), 2025-06-02).

- Arch 설치는 터미널에 떨어뜨려 놓고 방향을 거의 주지 않는다. 와이파이 잡는 것부터 일이다.
- Hyprland 는 *"로그인 화면도, 메뉴 바도, 알림 시스템도, 파일 관리자도, 설정 앱도 없다. 텍스트 설정 파일 하나와 위키뿐"*이다.
- 그래서 처음부터 직접 꾸미면 **"설치와 설정에만 최소 10시간 이상"** 이 든다.

당시의 우회책은 둘 중 하나였다. 주말을 통째로 바쳐 dotfiles 를 직접 조립하거나, r/unixporn 에 올라온 남의 설정 스크립트를 받아 쓰는 것. 후자도 결국 손으로 채울 게 많았다.

DHH 가 처음 시도한 것도 아니다. 1년 앞서 macOS 를 떠나면서 우분투용 설정 스크립트 **Omakub** 를 만들었다. Omarchy 는 그 자매 프로젝트로 출발했다([Omarchy is out](https://world.hey.com/dhh/omarchy-is-out-4666dd31), 2025-06-26).

## 2. 문제 — 선택지가 너무 많다는 것 자체가 비용이었다

DHH 가 짚은 핵심은 "Hyprland 가 어렵다"가 아니다. **너무 쪼개져 있다(atomized)** 는 것이다. 잠금 화면, 유휴 타이머, 메뉴 바, 블루투스 설정을 전부 각자 다른 프로그램으로 골라 붙여야 한다. 그리고 프로그램마다 설정 형식과 테마 방식이 다르다.

그래서 Omarchy 의 처방은 이름 그대로 **오마카세(omakase, 주방장 특선)** 다. 주방장이 코스를 정하지만 마음에 안 드는 접시는 돌려보내도 된다. 공식 사이트도 같은 비유를 쓴다([omarchy.org](https://omarchy.org/)).

## 3. 등장 — 스크립트에서 배포판으로 (2025)

| 시점 | 무엇이 바뀌었나 | 출처 |
| --- | --- | --- |
| 2025-06-26 | 첫 공개. "Arch + Hyprland 의 의견 있는(opinionated) 설정" | [DHH 블로그](https://world.hey.com/dhh/omarchy-is-out-4666dd31) |
| 2025-08-05 | 공개 6주 만에 릴리스 18회, PR 250개 처리 | [Omarchy is on the move](https://world.hey.com/dhh/omarchy-is-on-the-move-8f848fa4) |
| 2025-08-26 | 2.0. 설치 후 스크립트에서 **ISO + 전용 패키지 저장소** 를 갖춘 배포판으로 | [Omarchy 2.0](https://world.hey.com/dhh/omarchy-2-0-16fefc15) |
| 2025-10-16 | 최근 30일간 ISO 전송량 1PB(DHH 추산 약 15만 설치) | [A petabyte worth of Omarchy](https://world.hey.com/dhh/a-petabyte-worth-of-omarchy-in-a-month-a1fc538e) |

여기까지의 가치는 "남이 10시간 들일 일을 한 번에 끝내 준다" 였다. 2026년 4.0 에서 축이 바뀐다.

## 4. After — 4.0 Quattro: 데스크톱을 하나의 코드베이스로, 에이전트를 시스템 시민으로

[v4.0.0 릴리스 노트](https://github.com/omacom/omarchy/releases/tag/v4.0.0)(2026-08-14)의 변화는 크게 셋이다.

### 4-1. 여덟 개 프로그램이 셸 하나로

Waybar(바), Walker(런처), Mako(알림), SwayOSD, hyprlock, hypridle, swaybg, polkit-gnome 이 **전부 빠졌다.** 대신 [Quickshell](https://quickshell.org/) 기반의 장시간 실행 셸 프로세스 하나에 플러그인으로 들어갔다. 2절에서 말한 "쪼개짐" 문제를 정면으로 없앤 것이다. 이제 테마를 하나 고르면 터미널·바·알림·배경이 한 번에 바뀐다.

또 Omarchy 자체가 git 체크아웃에서 **시스템 패키지(pacman)** 로 옮겨갔다. 릴리스 노트의 표현으로는 "사용자 수정분을 안전하게 분리하기 위해서"다. 이제 "그냥 dotfiles 모음"이라는 말은 사실과 맞지 않는다.

### 4-2. 코딩 에이전트가 OS 의 기본 부품이 됐다

릴리스 노트에서 에이전트 관련 항목만 뽑으면 이렇다.

- **기본 에이전트 선택**: Claude Code, Codex, OpenCode, Pi, Oh My Pi, Gemini, Grok, Copilot, Crush 중 하나를 `Setup > Defaults > Agent` 에서 고른다. 처음 쓸 때 설치(lazy install)되고, `SUPER + SHIFT + CTRL + A` 나 터미널의 `a` 한 글자로 부른다.
- **모델 사용량 위젯**: 상단 바가 Claude Code·Codex·Fireworks 사용량을 보여준다.
- **크래시 진단**: 앱이 죽으면 알림이 뜨고, 그걸 누르면 기본 에이전트가 코어 덤프를 받아 원인을 분석하고 버그 리포트까지 돕는다(공식 사이트 "Make sense of a crash").
- **OS 를 고치는 스킬**: 에이전트가 앱·플러그인·테마를 만들 수 있게 스킬이 기본으로 들어 있다.

DHH 의 한 줄 요약은 이렇다. *"어떤 앱이든 바이브 코딩할 수 있다면, 운영체제도 바이브 코딩할 수 있어야 한다."* ([omarchy.org](https://omarchy.org/))

### 4-3. "완벽하지 않다, 하지만 이제 다 고칠 수 있다"

공식 사이트는 *"It's not perfect... yet. But we can fix everything now."* 라고 적는다. 리눅스 데스크톱의 오랜 약점은 "문제가 생기면 혼자 위키를 뒤져야 한다" 였다. Omarchy 는 그 약점을 **없애는 대신 에이전트에게 넘기는 쪽**을 골랐다. 이 선택이 1절의 before 와 가장 크게 갈리는 지점이다.

## 5. 규모와 돈 — 프로젝트가 밝힌 숫자

- **다운로드**: Quattro 출시 18일 만에 ISO 20만 건([omarchy.org 뉴스](https://omarchy.org/), 2026-09-02 항목).
- **재단**: 2026년 8월 DHH 가 비영리 **Omacom Foundation** 을 세웠다. 상표를 보유하고, 인프라에 돈을 대고, Omarchy 가 의존하는 오픈소스와 개발자를 후원하는 곳이다. 공지 페이지 기준 약정·기부 총액은 약 2,170만 달러다. 개인 후원자에는 Shopify·Stripe·Cloudflare·Dropbox CEO 등이 있고, 기업 후원자로 OpenAI·DigitalOcean·Alibaba Cloud 등이 이름을 올렸다([Omacom Foundation launches](https://omarchy.org/news/2026/08/omacom-foundation-launches-with-8-million/)).
- **커널**: 재단의 첫 정규직으로 커널 개발자가 합류했다. [v4.0.4](https://github.com/omacom/omarchy/releases/tag/v4.0.4)(2026-09-15)부터 자체 튜닝 커널 `linux-omarchy` 가 기본 부팅 항목이 됐다.

> 위 금액은 **약정(pledge)** 이 포함된 자체 발표 수치이고, 일부는 현금이 아니라 API 토큰 형태다(공지에 "or $1.5 million in tokens" 로 명시). 외부 감사 자료는 확인하지 못했다.

## 6. 누구에게 맞고, 무엇을 조심해야 하나

**맞는 사람**
- 키보드 중심의 타일링 작업 방식을 원하는 개발자
- 이미 Claude Code·Codex 같은 에이전트를 매일 쓰는 사람. 에이전트 계층이 OS 에 붙어 있다는 점이 다른 배포판과의 가장 큰 차이다.
- 오래된 노트북을 살리고 싶은 사람. 공식 사이트는 2GB 램 ThinkPad X220 과 인텔 맥도 지원 대상으로 든다.

**조심할 점**
- **Arch 는 롤링 릴리스다.** 4.0 은 셸을 통째로 다시 쓴 메이저 버전이라, 초기 포인트 릴리스(4.0.1~4.0.4)가 잇달아 나왔다. 유일한 업무용 기기라면 백업부터 하자. 릴리스 노트도 *"Always take a backup of important data!"* 라고 적는다.
- **pacman 을 직접 치지 말 것.** 4.0 부터 업데이트는 `omarchy update` 경로로 가도록 돼 있다.
- **윈도우 VM 은 업무용이다.** 공식 사이트가 "GPU 가속·패스스루 없음, 게임용 아님"이라고 명시한다.
- **에이전트에게 OS 를 맡긴다는 것은 권한을 맡긴다는 것이다.** 크래시 덤프에는 메모리 내용이 들어 있다. 그걸 외부 LLM 에 넘기는 흐름이라면, 무엇이 밖으로 나가는지 알고 켜는 게 맞다. 이건 필자의 의견이며 Omarchy 문서가 따로 경고하는 내용은 아니다.

## 정리

| | Before | After (Omarchy 4) |
| --- | --- | --- |
| 초기 구성 | Arch + Hyprland 수동 조립, 10시간 이상 | ISO 에서 질문 5개로 끝 (공식 주장: 빠른 기기 35초, 대부분 2분 이내) |
| 데스크톱 구성 요소 | 프로그램 8개, 설정 형식 제각각 | Quickshell 셸 1개 + 플러그인 |
| 문제가 생기면 | 위키·포럼 검색 | 에이전트에게 크래시 덤프를 넘겨 진단 |
| 커스터마이징 | 설정 파일 직접 편집 | "이렇게 바꿔줘" → 에이전트가 테마·플러그인 작성 |

Omarchy 가 "리눅스 데스크톱의 해"를 정말 가져올지는 아직 모른다. 그래도 방향은 분명하다. 리눅스의 약점이었던 "알아서 고쳐 써야 한다"를 에이전트 시대의 강점으로 뒤집으려는 시도다. 관심이 가면 공식 사이트의 VM 체험판부터 돌려 보자 → **[omarchy.org](https://omarchy.org/)**

---

## References

1. Omarchy 공식 사이트 — <https://omarchy.org/> (2026-09-30 조회)
2. omacom/omarchy GitHub 저장소 (MIT) — <https://github.com/omacom/omarchy>
3. Omarchy v4.0.0 "The Quattro Release" 릴리스 노트, 2026-08-14 — <https://github.com/omacom/omarchy/releases/tag/v4.0.0>
4. Omarchy v4.0.4 릴리스 노트, 2026-09-15 — <https://github.com/omacom/omarchy/releases/tag/v4.0.4>
5. D. H. Hansson, "Omarchy: Bottling that inspiration before it spoils", HEY World, 2025-06-02 — <https://world.hey.com/dhh/omarchy-bottling-that-inspiration-before-it-spoils-cd75e26b>
6. D. H. Hansson, "Omarchy is out", HEY World, 2025-06-26 — <https://world.hey.com/dhh/omarchy-is-out-4666dd31>
7. D. H. Hansson, "Omarchy is on the move", HEY World, 2025-08-05 — <https://world.hey.com/dhh/omarchy-is-on-the-move-8f848fa4>
8. D. H. Hansson, "Omarchy 2.0", HEY World, 2025-08-26 — <https://world.hey.com/dhh/omarchy-2-0-16fefc15>
9. D. H. Hansson, "A petabyte worth of Omarchy in a month", HEY World, 2025-10-16 — <https://world.hey.com/dhh/a-petabyte-worth-of-omarchy-in-a-month-a1fc538e>
10. DHH, "Omacom Foundation launches with $21.7 million", Omarchy News, 2026-08-21 — <https://omarchy.org/news/2026/08/omacom-foundation-launches-with-8-million/>
