---
layout: post
title: "free-claude-code 는 무엇을 우회하는가 — 그리고 무엇을 우회하지 않는가"
date: 2026-09-11 23:38:54 +0900
categories: [AI, Engineering]
tags: [Claude Code, LLM Gateway, 프록시, ANTHROPIC_BASE_URL, OpenAI 호환, 오픈소스]
---

![free-claude-code 리포지터리 README 화면 — Drop-in proxy for Claude Code's Anthropic API calls, 열 개 프로바이더 백엔드, 모델별 라우팅, 네이티브 /model 피커 지원, Quick Start 의 npm install -g @anthropic-ai/claude-code](/assets/images/free-claude-code-readme.jpg)

주소는 이것이다 — **<https://github.com/Alishahryar1/free-claude-code>**

화면의 첫 줄이 이 리포의 전부를 요약한다. *"Drop-in proxy for Claude Code's Anthropic API calls."* 그런데 이 한 줄을 보고 대부분의 사람이 두 가지를 동시에 오해한다. 하나는 **"뭔가 뚫는 거구나"**, 다른 하나는 **"Claude 를 공짜로 쓰는 거구나"**. 둘 다 틀렸다. 이 글은 이 도구가 실제로 무엇을 우회하고 무엇을 우회하지 *않는지*를, 공식 문서와 리포의 설정 파일을 근거로 가른다.

---

## 1. 먼저: 이건 뚫린 문이 아니라 열려 있는 문이다

가장 흔한 오해부터 정리한다. Claude Code 를 다른 엔드포인트로 보내는 것은 **공식 문서에 적힌 기능**이다.

Anthropic 의 Claude Code 문서 "Other LLM gateways" 페이지는 이렇게 적는다 — *"Any gateway that exposes a supported API format works."* 그리고 그 연결에 쓰는 변수를 명시한다: **`ANTHROPIC_BASE_URL` is the variable that points Claude Code at the gateway.**[^1]

이 기능이 왜 있냐면, 조직이 자기 게이트웨이를 앞에 두고 싶어 하기 때문이다. 같은 문서가 게이트웨이가 제공하는 것을 네 가지로 정리한다 — 자격증명을 서버 쪽에 두기, 사용량을 개발자·팀 단위로 귀속, 예산·레이트리밋을 한 곳에서 강제, 모든 모델 요청 감사 로깅.[^1]

그러니까 **free-claude-code(이하 FCC)가 하는 일의 뼈대는 취약점 이용이 아니라, 문서화된 확장점을 쓰는 것**이다. 이걸 먼저 못 박아야 나머지 논의가 선정적으로 흐르지 않는다.

---

## 2. 그럼 정확히 무슨 구조인가

FCC 는 **로컬에 프록시 서버를 하나 띄우고, Claude Code 를 거기로 보낸다.** 리포는 `fcc-server` 로 프록시를 띄우고 `fcc-claude` 로 Claude Code 를 붙이는 런처를 제공한다. 모델 선택·키 입력은 로컬 Admin UI 에서 하고, Claude Code 의 **네이티브 `/model` 피커**가 프록시의 모델 목록 엔드포인트를 읽어 그대로 동작한다.[^2]

핵심은 프록시 안에서 벌어지는 **번역**이다. 리포의 `.env.example` 을 열어 보면 이 구조가 아주 선명하게 드러난다. 프로바이더 설정 주석이 거의 전부 같은 말로 끝난다:[^3]

```
# DeepSeek Config (OpenAI-compatible Chat Completions at api.deepseek.com)
# Kimi Config (OpenAI-compatible Chat Completions at api.moonshot.ai/v1)
# MiniMax Config (OpenAI-compatible Chat Completions at api.minimax.io/v1)
# Hugging Face Inference Providers Config (OpenAI-compatible Chat Completions at router.huggingface.co/v1)
# Fireworks AI Config (OpenAI-compatible Chat Completions at api.fireworks.ai/inference/v1)
```

즉 FCC 의 본체는 이 변환기다:

$$\text{Claude Code} \xrightarrow{\;\text{Anthropic Messages API}\;} \text{FCC 프록시} \xrightarrow{\;\text{OpenAI Chat Completions}\;} \text{각 프로바이더}$$

왼쪽 화살표는 한 종류, 오른쪽 화살표는 프로바이더마다 조금씩 다른 방언. 그 사이를 메우는 게 이 프로젝트가 실제로 파는 물건이다. 그리고 여기가 어려운 지점이다 — 단순히 텍스트만 옮기는 게 아니라 **스트리밍, 툴 사용(tool use), thinking 블록, 이미지 입력**을 손실 없이 옮겨야 에이전트가 제대로 돈다. README 가 "agent capabilities stay intact" 를 따로 강조하는 이유가 이것이다.[^2]

리포 메타데이터는 2026년 9월 11일 기준 이렇다 — MIT 라이선스, 2026-01-28 생성, 스타 52,565, 포크 8,438, 열린 이슈 368.[^4] README 상단에는 *"Independent open-source project. Not affiliated with or endorsed by Anthropic."* 라는 문구가 직접 붙어 있다.[^2]

---

## 3. 무엇이 바뀌고 무엇이 남는가 — 이름이 만드는 착시

여기가 이 글에서 제일 중요한 절이다.

FCC 를 붙이면 **Claude Code 라는 껍데기는 그대로 남는다.** 터미널 UI, 파일 편집, 툴 호출, 슬래시 명령, 권한 모델 — 이 에이전트 하네스가 계속 쓰인다. 바뀌는 건 **그 안에서 생각하는 모델**이다. 리포가 문서에 적어 둔 기본 모델은 `nvidia_nim/nvidia/nemotron-3-super-120b-a12b` 이고, 프로바이더 표의 예시 모델도 Qwen·DeepSeek·Grok·GLM 같은 것들이다.[^2]

그러니까 정확한 문장은 이렇게 된다.

> **"Free Claude Code" 는 "무료 Claude" 가 아니다. Claude Code 하네스는 계속 쓰되, 지능은 다른 모델에서 사오는 것이다.**

이름이 이 구분을 흐린다. 실제로 사는 물건은 *"Claude Code 의 에이전트 루프를 다른 모델에 씌우는 어댑터"* 이고, 그 결과물의 품질은 Claude 가 아니라 **당신이 고른 그 모델의 품질**이다.

---

## 4. Anthropic 이 문서에 직접 그어 둔 선

1절에서 "열린 문"이라고 했다. 그런데 같은 공식 문서에 선도 같이 그어져 있고, 이 선이 FCC 의 용법을 정확히 가른다.

> *"Anthropic doesn't endorse, maintain, or audit third-party gateway products, and doesn't support routing Claude Code to non-Claude models through any gateway."*[^1]

문장을 둘로 쪼개면 이렇다. ① 서드파티 게이트웨이 제품은 앤트로픽이 보증·유지·감사하지 않는다 ② **어떤 게이트웨이를 통하든 Claude Code 를 비(非)Claude 모델로 라우팅하는 것은 지원 대상이 아니다.** FCC 가 하는 일이 정확히 ②다.

"지원하지 않는다"는 "금지한다"와 같은 말이 아니다. 그러나 실무적으로는 같은 결론에 이른다 — **깨졌을 때 물어볼 곳이 없다.** 같은 문서가 그 이유까지 적어 둔다:

> *"Claude Code adds capabilities with each release, and a gateway that doesn't forward them breaks the corresponding features, so the gateway product needs to be kept updated as Claude Code evolves."*[^1]

이게 구조적 부채다. Claude Code 는 계속 기능을 추가하고, 그 기능은 요청·헤더·이벤트 형식으로 나타난다. 중간 프록시는 **영원히 추격자**다. 스타 5만 개짜리 활발한 프로젝트라 해도 이 추격은 끝나지 않는다. 열린 이슈 368개[^4]는 그 추격의 크기를 짐작하게 하는 숫자다(이슈 수 자체가 품질 지표는 아니다).

덧붙여 구독과의 상호작용도 문서에 적혀 있다. 게이트웨이 자격증명이나 `apiKeyHelper` 가 활성인 동안에는 **claude.ai 구독이 그 세션에 쓰이지 않는다.** 반대로 `ANTHROPIC_BASE_URL` 만 설정하고 자격증명을 안 넣으면 저장된 claude.ai 로그인이 여전히 활성 자격증명으로 남아 구독의 사용 한도와 과금이 그대로 적용된다.[^1] "프록시를 앞에 뒀으니 구독과 무관하다"는 자동으로 참이 아니다.

---

## 5. 같은 구조를 한 달 굴려 보고 알게 된 것

나는 이 아키텍처 자체는 이미 쓰고 있다. 집 K3s 클러스터에 **LiteLLM 프록시**를 LLM 게이트웨이로 올려 두고 한 달을 굴렸다([그때 부딪힌 벽 세 겹 기록](/2026/09/04/litellm-proxy-blank-screen-three-walls/), [Opik 로 관측 붙인 기록](/2026/09/05/litellm-gateway-opik-observability/)).

거기서 배운 것 중 FCC 를 볼 때 그대로 적용되는 게 하나 있다. **게이트웨이의 주인공은 사람이 보는 화면이 아니라 `/v1/chat/completions` 다.** 예쁜 Admin UI 가 있다는 사실은 번역 계층이 정확하다는 증거가 전혀 아니다. 판단해야 할 것은 UI 가 아니라, 스트리밍 중간에 툴 호출이 끼었을 때·thinking 블록이 왔을 때·이미지가 실렸을 때 저쪽 끝에서 무엇이 나오느냐다.

그리고 그건 **써 봐야만 안다.** 그래서 이 글은 FCC 의 품질을 평가하지 않는다. 나는 설치해서 돌려 보지 않았고, README 와 `.env.example` 과 앤트로픽 공식 문서를 읽었을 뿐이다.

---

## 6. 붙이기 전에 계산해야 할 것

기능이 아니라 **위험의 목록**으로 적는다. 각각은 FCC 만의 문제가 아니라 *"내 에이전트 앞에 남의 프록시를 둔다"*는 결정에 따라오는 공통 항목이다.

- **설치가 `curl … | sh` 다.** README 는 설치 스크립트를 먼저 읽어 보라고 안내하고 실제 링크도 준다.[^2] 그 안내를 실행하는 사람이 몇이나 되는지가 진짜 질문이다.
- **프록시는 전부를 본다.** 프롬프트, 소스코드, 파일 경로, 툴 호출 인자가 전부 그 프로세스를 지나간다. 로컬에서 돌더라도 "내가 읽어보지 않은 코드가 내 리포 전체를 본다"는 사실은 남는다.
- **키가 한곳에 모인다.** 프로바이더 수십 개의 API 키가 하나의 로컬 설정으로 집중된다. 프록시 자체의 인증(bearer token)은 **옵션**이고 Admin 에서 켜야 한다.[^2]
- **폴백은 돈을 쓴다.** README 가 직접 경고한다 — 실패한 요청이 성공하기까지 **둘 이상의 프로바이더 사용량을 소비할 수 있다.**[^2]
- **"무료"의 주어는 앤트로픽이 아니다.** 무료 티어는 각 프로바이더가 정하고 바꾼다. README 도 *"Free-tier availability and limits are controlled by each provider and may change"* 라고 적어 둔다.[^2]
- **프로젝트의 자기 주장과 사실을 구분해야 한다.** "50개 ToS-friendly 프로바이더", "매달 13억+ 무료 토큰" 은 **프로젝트가 자기 README 에 적은 주장**이다.[^2] 제3자가 검증한 수치가 아니고, 각 프로바이더의 약관은 각자 확인해야 한다.

---

## 7. 그래서 언제 말이 되나

정직하게 양쪽을 적는다.

**말이 되는 경우.** Claude Code 의 *하네스*(툴 루프, 권한 모델, 터미널 UX)가 마음에 들어서 그 UX 로 다른 모델을 쓰고 싶을 때. 로컬 모델이나 사내 모델을 같은 인터페이스로 붙이고 싶을 때. 프로바이더 장애 때 자동 폴백이 필요할 때. 실험·학습 목적으로 여러 모델을 같은 하네스에서 비교하고 싶을 때.

**말이 안 되는 경우.** "Claude 를 공짜로 쓰려고" — 그건 이 도구가 제공하지 않는다. 업무 코드베이스에 붙이는데 프록시 코드를 감사할 여력이 없을 때. 깨졌을 때 벤더 지원이 필요한 환경일 때 — 앤트로픽 문서가 미지원을 명시했으므로 그 경로는 닫혀 있다.[^1] 조직 차원에서 게이트웨이가 필요한 거라면, 애초에 **문서가 상정한 용법**(자기 게이트웨이 + Claude 모델)이 따로 있다.

---

## 8. 이 글의 한계

- **돌려 보지 않았다.** 설치·실행·측정 없이 공개 문서만 읽고 쓴 글이다. 따라서 번역 정확도·성능·안정성에 대해서는 아무 주장도 하지 않는다.
- **리포 지표는 시점값이다.** 스타 52,565·포크 8,438·이슈 368 은 2026년 9월 11일 GitHub API 응답 기준이며, 이 수치들은 품질 지표가 아니라 관심도 지표다.[^4]
- **약관 판단은 하지 않는다.** 각 프로바이더의 무료 티어 약관과 Claude Code 구독 약관의 해석은 이 글의 범위 밖이다. 리포는 스스로를 "ToS-friendly" 라고 부르지만 그건 리포의 주장이고, 확인 책임은 쓰는 사람에게 있다.
- **코드를 읽지 않았다.** 근거는 README, `.env.example`, GitHub API 메타데이터, 그리고 앤트로픽 공식 문서다.

---

## 남는 질문

FCC 가 흥미로운 건 우회 기법이라서가 아니다. **에이전트 하네스와 모델이 분리 가능한 물건이라는 사실을 5만 명이 동시에 확인해 준 사건**이라서다. 지금까지 우리는 "어떤 모델을 쓸까"를 골랐는데, 이 도구는 "어떤 *하네스*를 쓸까"를 따로 고를 수 있다고 말한다.

그렇다면 다음 질문은 이거다 — 에이전트의 품질에서 모델이 차지하는 몫과 하네스가 차지하는 몫은 각각 얼마인가. 이건 취향으로 답할 문제가 아니라 측정해야 할 문제이고, 아직 아무도 제대로 측정해서 공개하지 않았다.

---

## References

[^1]: Anthropic, Claude Code Docs — "Other LLM gateways". `ANTHROPIC_BASE_URL` 이 게이트웨이를 가리키는 변수라는 설명, 게이트웨이가 제공하는 네 가지, *"Anthropic doesn't endorse, maintain, or audit third-party gateway products, and doesn't support routing Claude Code to non-Claude models through any gateway."*, 릴리스 추격 부담, 구독·자격증명 상호작용. <https://code.claude.com/docs/en/llm-gateway>
[^2]: Alishahryar1, `free-claude-code` README (main 브랜치, 2026-09-11 열람). 로컬 프록시·Admin UI·`fcc-server`/`fcc-claude` 런처, 네이티브 `/model` 피커, 기본 모델 `nvidia_nim/nvidia/nemotron-3-super-120b-a12b`, 폴백이 복수 프로바이더 사용량을 소비할 수 있다는 경고, 프록시 인증이 옵션이라는 점, 무료 티어는 프로바이더가 통제한다는 문구, 앤트로픽 비제휴 고지, "50 ToS-friendly providers / 1.3B+ free tokens" 주장(프로젝트 자체 주장). <https://github.com/Alishahryar1/free-claude-code>
[^3]: 같은 리포의 `.env.example` (main, 2026-09-11 열람). 프로바이더 대부분이 "OpenAI-compatible Chat Completions" 로 기재되어 있어 프록시의 번역 방향을 드러낸다. <https://raw.githubusercontent.com/Alishahryar1/free-claude-code/main/.env.example>
[^4]: GitHub API 리포지터리 메타데이터 (2026-09-11 조회) — MIT 라이선스, 2026-01-28 생성, 스타 52,565, 포크 8,438, 열린 이슈 368.

*스크린샷은 본인이 브라우저에서 직접 촬영한 해당 리포 README 화면이다. 이 글은 도구의 사용을 권하지도 말리지도 않으며, 구조와 공식 문서에 적힌 제약을 정리하는 데 목적이 있다.*
