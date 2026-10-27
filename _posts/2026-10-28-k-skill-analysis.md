---
layout: post
title: "k-skill 분석 — 한국 생활형 AI 에이전트 스킬을 안전하게 운영하는 법"
date: 2026-10-28 00:29:04 +0900
categories: [AI, Agent, Korea, Automation]
tags: [k-skill, Claude Code, Codex, OpenCode, OpenClaw, MCP, 한국형 에이전트]
---

> 기준 시각: 2026-10-28 00:29 KST. NomaDamas/k-skill 공개 저장소의 README·설치·설정·보안 문서를 확인해 정리했다. 저장소의 최신 커밋·스킬 수·스타 수는 계속 변할 수 있으므로 조회 시점의 스냅샷으로 구분한다.

## 결론

[k-skill](https://github.com/NomaDamas/k-skill)은 Claude Code·Codex·OpenCode·OpenClaw/ClawHub 등 여러 코딩 에이전트에서 사용할 수 있도록 한국 생활·공공·금융·쇼핑·문서·개발 업무 스킬을 모아 둔 공개 저장소다.[1][2]

핵심 가치는 “한국에서 실제로 자주 쓰는 서비스와 공공데이터를 에이전트의 호출 가능한 작업 단위로 바꾸는 것”이다. 다만 스킬이 조회 전용인지, 예약·결제·신청을 수행하는지, API key·로그인·브라우저·프록시를 요구하는지는 기능별로 다르므로 설치 수보다 **권한·데이터 흐름·실행 결과 검증**이 중요하다.[2][5]

## 1. 무엇을 제공하는가

README는 KTX·KBO·로또·당근·쿠팡·카카오톡·정부24·홈택스 등 한국 생활 영역을 대상으로 한 스킬 모음을 소개하고, 총 125개 스킬을 카테고리별로 정리한다.[2]

주요 영역은 다음과 같다.

- 이동·교통·여행
- 부동산·주택
- 법률·공공
- 사업·상권·세무
- 정부지원·조달
- 채용·일자리
- 금융·투자·경제통계
- 건강·의료
- 쇼핑·중고거래
- 날씨·환경·생활
- 개발자·문서 도구
- 공통 설정·관리

GitHub 페이지에는 약 **8.2k stars**, **987 forks**, **49 contributors**, 최신 커밋과 스킬 목록이 표시됐지만, 이 값은 조회 시점에 따라 달라질 수 있다.[1]

## 2. 설치 구조

기본 설치 흐름은 전체 스킬을 먼저 설치한 뒤 `k-skill-setup`으로 공통 설정과 credential 환경을 확인하고, 필요한 개별 스킬을 호출하는 방식이다.[2][3]

```bash
# 전체 스킬 설치
npx --yes skills add NomaDamas/k-skill --all -g

# 특정 스킬만 설치
npx --yes skills add NomaDamas/k-skill --skill railway-timetable -g

# CLI·에이전트 스킬 갱신
npx -y @nomadamas/k-skill@0 update
```

설치 문서는 Node.js 18 이상과 `npx`를 기본 요구사항으로 제시하며, 철도 시간표 helper처럼 일부 기능은 Python 3.11 이상과 `uv`가 추가로 필요하다고 설명한다.[3]

Claude Code에서는 Marketplace를 통해 다음처럼 설치할 수 있다.[2]

```text
/plugin marketplace add NomaDamas/k-skill
/plugin install k-skill@k-skill
```

k-skill은 각 SKILL.md의 선택 정보와 전체 instruction을 분리해 CLI가 런타임에 조립하는 구조도 제공한다.[3]

```bash
npx -y @nomadamas/k-skill@0 instruct <skill-name>
npx -y @nomadamas/k-skill@0 list
npx -y @nomadamas/k-skill@0 version
npx -y @nomadamas/k-skill@0 exec <skill> <script> -- --help
npx -y @nomadamas/k-skill@0 read <skill> references/<file>
```

## 3. 조회와 실행을 구분해야 한다

k-skill 목록에는 조회형 기능과 실제 상태 변경 가능성이 있는 기능이 함께 존재한다. 예를 들어 KTX 철도 시간표는 README에서 공식 공개 시간표 조회 전용이며, 로그인·예약·결제·취소를 수행하지 않는다고 명시한다.[2]

반면 고속버스·시외버스·숲나들e 등은 좌석·요금·임시 선점·예약 흐름을 다룰 수 있고, 법원·등기·팝빌·증권·채용 기능은 로그인·유료 열람·제출·과금 조건을 확인해야 한다.[2][3]

따라서 스킬을 다음 네 종류로 분류해 사용하는 것이 안전하다.

| 유형 | 예시 | 실행 원칙 |
| --- | --- | --- |
| 조회 전용 | 시간표·날씨·주식·공공 통계 | 원문·조회시각·출처 확인 |
| 조회+비교 | 쇼핑·부동산·채용·공고 | 최신 여부·가격·조건·링크 read-back |
| 예약·제출 보조 | 버스·시설·등기·법원 | 최종 제출·결제 전 사용자 승인 |
| 계정·금융·민감정보 | 증권·팝빌·카카오톡·기업정보 | vault·BYOK·최소권한·로그 비출력 |

## 4. 데이터 흐름과 Hosted Proxy

일부 기능은 사용자가 API key를 직접 넣지 않고 `k-skill-proxy.nomadamas.org` 같은 hosted proxy를 통해 사용할 수 있도록 구성돼 있다. README와 setup 문서는 기능별로 hosted proxy를 사용하는 경우 사용자 key가 불필요할 수 있으며, self-host 또는 direct 호출에서는 별도 key가 필요하다고 구분한다.[2][4][5]

이 구조는 설치 마찰을 줄이지만, 운영 관점에서 다음을 확인해야 한다.

```text
Agent
  → k-skill helper / proxy
  → 공공 API·공식 사이트·서비스
  → 결과 반환
```

- 어떤 데이터가 proxy를 통과하는가
- proxy의 로그·보존·접근정책은 무엇인가
- hosted proxy 장애 시 direct/self-host 대안이 있는가
- API key가 사용자 환경이 아니라 proxy 운영자 환경에 있는가
- 반환 결과에 개인정보·인증정보가 포함되는가

README는 공개 API proxy의 개인정보 처리방침 링크와 CLI usage analytics 정책을 별도로 안내하며, CLI analytics는 명령 인자·원문 입력·파일 내용·인증정보를 수집하지 않고 `KSKILL_ANALYTICS_DISABLED=1`로 거부할 수 있다고 설명한다.[2]

## 5. 보안·시크릿 정책

보안 문서는 credential resolution order를 다음과 같이 제시한다.[5]

1. Dolshoi credential mode의 vault capability
2. credential 입력 UI를 통한 vault provision
3. 이미 주입된 환경변수·host vault
4. 1Password·Bitwarden·macOS Keychain 등 host vault
5. `~/.config/k-skill/secrets.env` fallback

Fallback 파일은 plain dotenv이므로 `0600` 권한을 요구한다.[5]

```bash
mkdir -p ~/.config/k-skill
chmod 0600 ~/.config/k-skill/secrets.env
```

운영 원칙은 분명하다.

- 채팅에 비밀번호·API key·토큰을 평문으로 받지 않기
- 실제 secret을 문서·PR·로그·URL·CLI 인자에 남기지 않기
- 필요한 기능에만 credential을 공급하기
- hosted proxy와 direct/BYOK 경로를 혼동하지 않기
- 시크릿이 없다고 비공식 우회 사이트를 자동 채택하지 않기

## 6. 한국 생활형 스킬의 강점

### 공공데이터 접근성

한국 법령·특허·KOSIS·K-Startup·부동산·주식·공공시설 등은 데이터 출처와 호출 방식이 제각각이다. k-skill은 이런 기능을 에이전트가 호출할 수 있는 단위로 묶고, 일부는 hosted proxy로 키 설정 부담을 낮춘다.[2][4]

### 생활 작업의 조합

단일 질문에 검색만 하는 것이 아니라 다음처럼 여러 기능을 연결할 수 있다.

```text
지역 확인
 → 교통·날씨·주차 조회
 → 공고·가격·시설 비교
 → 공식 원문 링크 확인
 → 사용자가 최종 결정
```

### 한국어·한국 제도 맥락

일반적인 글로벌 스킬보다 국내 공공기관·쇼핑·교통·법률·금융 서비스 명칭과 조회 흐름에 맞춰진 점이 차별점이다.

## 7. 한계와 운영 위험

### 스킬 수가 품질을 보장하지 않는다

125개 스킬이라는 숫자는 범위의 지표이지, 모든 기능이 동일한 수준의 안정성·최신성·공식 API 지원을 갖췄다는 뜻은 아니다.[2]

기능마다 다음을 별도로 확인해야 한다.

- 원문 출처가 공식인지
- API가 현재 동작하는지
- 로그인·결제·CAPTCHA가 필요한지
- 결과에 조회시각이 있는지
- 실패와 “데이터 없음”을 구분하는지
- 페이지 구조 변경에 취약한지

### “정상”과 “판정”을 구분

사업자 상태 정상, 제재 0건, 검색 노출, 공고 발견은 각각 제한된 사실이다. 이것만으로 참여 자격·법적 적합성·투자 가치·채용 가능성을 확정하면 안 된다. README도 사업자 실사·조달·법률 관련 기능에서 사실 조회와 판단 경계를 구분하는 방향을 제시한다.[1][2]

### 자동 실행의 범위

예약·주문·결제·제출·계좌·증권·법원 업무는 실행 전 승인과 read-back이 필요하다. 조회 결과를 얻었다고 실제 예약·결제·신청이 끝난 것이 아니다.

## 8. Hermes와 k-skill 조합

Hermes는 도구·스킬·cron·메시징·브라우저·파일·MCP를 오케스트레이션하고, k-skill은 한국 생활·공공·업무 도메인 capability를 추가하는 조합으로 볼 수 있다.

```text
Telegram / CLI
       ↓
Hermes Orchestrator
       ↓
k-skill skill 선택
       ↓
공식 API·공식 웹·hosted proxy·직접 helper
       ↓
출처·시각·상태·실패 경로 검증
       ↓
사용자 승인 또는 결과 전달
```

권장 운영은 다음과 같다.

1. `k-skill-setup`으로 환경과 credential 경계를 확인
2. 필요한 스킬만 선택하거나 전체 설치 후 기능별 로드
3. 조회 전용·변경 가능 기능을 분리
4. 공식 원문·조회시각·응답 상태를 보존
5. 외부 상태 변경은 사용자 승인 뒤 실행
6. 성공 호출이 아니라 실제 결과 read-back으로 완료 판정
7. proxy·helper·공식 API 중 어느 경로를 사용했는지 기록

## 9. 기여·라이선스·운영 거버넌스

GitHub 저장소는 기본 라이선스를 MIT로 표시하지만, `packages/k-skill-proxy/`와 `infra/k-skill-proxy-dashboard/`는 AGPL-3.0-only라고 명시한다.[2]

따라서 저장소 전체를 하나의 라이선스로 취급하면 안 된다. 스킬만 사용하는 경우와 proxy를 수정·배포하는 경우의 의무가 다를 수 있으므로 해당 디렉터리의 LICENSE를 확인해야 한다.

또한 저장소는 Changesets·release workflow·기여 가이드·스킬별 문서를 운영한다. 외부 기여나 내부 fork에서는 기능 코드뿐 아니라 문서·credential 정책·테스트·proxy 계약까지 함께 검토해야 한다.[1][3]

## 최종 평가

k-skill은 한국 사용자의 생활형 업무를 AI 에이전트가 다룰 수 있도록 **도메인 지식·실행 절차·도구 연결·안전 규칙을 스킬 단위로 패키징한 저장소**다.

가장 큰 장점은 한국 서비스와 공공데이터에 대한 접근 문턱을 낮추는 것이다. 가장 큰 위험은 기능 수가 많아질수록 인증·공식성·최신성·실행 권한을 기능별로 따로 확인해야 한다는 점이다.

실전에서는 “전체 설치 후 아무거나 자동 실행”보다 다음 전략이 적절하다.

```text
전체 스킬 인벤토리 확인
→ k-skill-setup
→ 조회 전용 기능으로 smoke test
→ 필요한 기능만 활성화
→ credential 최소화
→ 변경 작업은 승인
→ 공식 결과 read-back
```

## 확인된 사실과 미확인 범위

- **저장소 확인:** k-skill은 Claude Code·Codex·OpenCode·OpenClaw/ClawHub 지원과 한국 생활·공공·업무 영역 스킬 모음을 제공한다.[1][2]
- **설치 확인:** 전체 설치·개별 설치·CLI update·`k-skill-setup` 순서를 공식 문서에서 확인했다.[2][3][4]
- **보안 확인:** vault 우선 credential resolution, `0600` secrets fallback, 평문 secret 금지 원칙을 문서에서 확인했다.[5]
- **미확인:** 모든 125개 스킬의 현재 API 성공률·운영 uptime·각 프록시의 실제 로그 보존기간·각 기능의 법적 적합성은 이 글에서 전수 검증하지 않았다.

## 참고 자료

[1] [GitHub — NomaDamas/k-skill](https://github.com/NomaDamas/k-skill)

[2] [k-skill README](https://raw.githubusercontent.com/NomaDamas/k-skill/main/README.md)

[3] [k-skill 설치 방법](https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/install.md)

[4] [k-skill 공통 설정 가이드](https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/setup.md)

[5] [k-skill 보안·시크릿 정책](https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/security-and-secrets.md)

> ※ 이 글은 공개 저장소 문서 기반 분석이며, k-skill의 모든 기능을 이 환경에서 전수 실행·검증한 결과가 아니다.

## Sources

[1] https://github.com/NomaDamas/k-skill
[2] https://raw.githubusercontent.com/NomaDamas/k-skill/main/README.md
[3] https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/install.md
[4] https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/setup.md
[5] https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/security-and-secrets.md
