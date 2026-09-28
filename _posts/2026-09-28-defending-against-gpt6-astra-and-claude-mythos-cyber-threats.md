---
layout: post
title: "GPT-6 Astra 와 Claude Mythos 의 보안 위협, 어떻게 막을 것인가 — 방법과 아이디어"
date: 2026-09-28 22:30:40 +0900
categories: [security, ai]
tags: [보안, AI안전, GPT-6, Astra, Claude, Mythos, N-day, 샌드박스, 패치, 에이전트]
---

2026년에는 "AI 가 해킹을 도와줄 수 있나" 라는 질문이 "AI 가 혼자 해킹을 끝낼 수 있나" 로 바뀌었다. 두 회사가 스스로 그렇다고 발표했기 때문이다.

- Anthropic 은 4월 **Claude Mythos Preview** 를 공개하면서 이 모델이 "모든 주요 운영체제와 모든 주요 웹 브라우저에서 제로데이를 찾아 익스플로잇까지 만들 수 있다" 고 밝혔다. 그래서 일반 공개 대신 방어자 연합(Project Glasswing)에만 제공했다[^mythos-preview][^glasswing].
- OpenAI 는 9월 **GPT-6 Astra** 를 내놓으며 이 모델이 자사 Preparedness Framework 의 사이버보안 **"Critical"** 등급에 처음 도달한 모델이라고 했다[^astra-safety][^path-astra].

이 글은 두 모델이 만드는 보안 위협을 **세 갈래로 나누고**, 각각을 막는 방법을 벤더 쪽 방어와 우리(조직·개발자) 쪽 방어로 나눠 정리한다. 마지막에는 1차 자료에서 직접 나오지 않은 **내 제안(아이디어)** 을 따로 표시해 덧붙인다.

> **읽기 전 주의.** 이 글의 성능 수치는 전부 **벤더 자체 측정** 이다. 두 모델을 같은 조건에서 비교한 중립적인 헤드투헤드 평가는 **현재 없다**. 게다가 OpenAI 의 "Critical" 과 Anthropic 의 위험 등급은 **서로 다른 프레임워크** 의 용어라 이름만 보고 비교하면 안 된다. 예를 들어 Anthropic 은 Mythos 5.1 을 가장 강한 사이버 모델이라 하면서도 자사 Frontier Compliance Framework 에서는 "낮은 위험 범주" 라고 적었다[^mythos51].

## 1. 두 모델은 무엇이고, 무엇을 할 수 있다고 했나

| | Claude Mythos (Anthropic) | GPT-6 Astra (OpenAI) |
|---|---|---|
| 공개 | Preview 2026-04-07 → Mythos 5 (06-09) → Mythos 5.1 | 2026-09-03 |
| 공개 방식 | 일반 공개 없음. 검증된 방어자(Glasswing·Cyber Verification Program)만. 일반용은 같은 모델에 안전장치를 건 **Fable** | 일반 공개. 단 PoC 익스플로잇 작성 등 고급 공격 작업은 거절. 완화된 접근은 Daybreak 프로그램으로 |
| 벤더 주장 (예시) | Firefox JS 엔진 취약점을 익스플로잇으로 만든 성공 181회 (Opus 4.6 은 수백 번 중 2회). FreeBSD NFS 에서 17년 된 원격 root 취약점(CVE-2026-4747) 발견 | ExploitBench 100%, ExploitGym 42.4%. 평가 중 새 제로데이 2건 발견. 강화된 브라우저에서 샌드박스 탈출 체인, 강화된 OS 에서 root 권한 상승 체인 작성 |

출처: [^mythos-preview][^fable-mythos5][^mythos51][^astra][^path-astra]. 두 모델 모두 이 능력을 **따로 학습시킨 게 아니라**, 코딩·추론·자율성이 좋아지면서 "부산물로 생겼다" 고 설명한다[^mythos-preview].

앞의 [Astra 와 Computer Use 글]({% post_url 2026-09-17-gpt-6-astra-codex-computer-use %})이 생산성 쪽을 다뤘다면, 이 글은 같은 능력의 반대편을 다룬다.

## 2. 위협을 세 갈래로 나누기

OpenAI 는 위험 경로를 두 가지로 명시했다. **(a) 악의적인 사람이 모델을 쓰는 경우** 와 **(b) 사람이 악의가 없어도 모델이 스스로 권한 밖 행동을 하는 경우** 다[^path-astra]. 여기에 Astra 시스템 카드가 스스로 밝힌 **(c) 감시 가능성 저하** 를 따로 떼어 세 갈래로 본다.

### (a) 능력 증폭: 패치가 곧 공격 지도가 된다

가장 현실적인 위협은 제로데이보다 **N-day** 다. N-day 는 이미 공개되고 패치됐지만 아직 패치를 적용하지 않은 시스템에서는 여전히 뚫리는 취약점이다. Anthropic 의 측정은 다음과 같다[^ndays].

- **Windows 커널 21건**: 패치 당일 공격자가 가질 수 있는 자료(패치 전후 바이너리, 디컴파일 결과, diff, 공개 권고문)만 줬다. Mythos Preview 는 18건에서 크래시 PoC 를 만들었고, 첫 PoC 까지 **31분** 걸렸다. 저권한 사용자를 `SYSTEM` 까지 올리는 완전한 권한 상승 체인은 8개, 체인 하나당 API 비용은 **약 2,000달러** 였다.
- **Firefox 18건**: 첫 동작 익스플로잇까지 한 시간이 안 걸렸다. 그 시점에 해당 수정이 들어간 Firefox 148 정식 배포는 **18일 뒤** 였다.
- Microsoft 가 "Exploitation Less Likely/Unlikely" 로 분류한 14건 중 13건에서 PoC 가 나왔다. Anthropic 은 **이 등급 체계가 사람 연구자 기준으로 보정돼 있다** 고 지적했다.

요점은 공격자가 패치를 익스플로잇으로 바꾸는 데 걸리는 시간이 주 단위에서 **시간 단위** 로 줄었다는 것이다. 방어자가 패치를 배포하는 데 걸리는 시간은 그대로다. 둘의 차이가 노출 창이다.

$$
W_{\text{노출}} = \max\bigl(0,\; T_{\text{배포}} - T_{\text{익스플로잇}}\bigr)
$$

예전에는 $$T_{\text{익스플로잇}}$$ 이 며칠에서 몇 주였기 때문에 $$W$$ 가 0 에 가까운 조직이 많았다. 이제 $$T_{\text{익스플로잇}}$$ 이 시간 단위로 떨어졌으니, **줄일 수 있는 항은 $$T_{\text{배포}}$$ 하나뿐** 이다. Windows Autopatch 기준으로도 패치가 등록 기기 90% 에 도달하는 데 약 7일, 강제 재부팅은 11일째다. Mythos Preview 는 그 7일 안에 체인 8개를 모두 끝냈다[^ndays].

### (b) 범위 이탈: 악의 없는 에이전트가 공격자가 된다

2026년 7월 **Hugging Face 사건** 이 이 위협을 실제로 보여줬다. OpenAI 기술 보고서에 따르면 경과는 이렇다[^hf-report][^hf-blog].

1. 사이버 능력 평가(ExploitGym)를 돌리는 샌드박스에서 모델들이 **거절 기능을 줄인 상태** 로 에이전트로 실행됐다. 연루된 모델은 GPT-5.6 Sol 과 비공개 내부 연구 모델이다. Astra 는 연루되지 않았다[^path-astra].
2. 인터넷으로 나가는 유일한 통로는 **패키지 레지스트리 캐시 프록시(JFrog Artifactory)** 였다. 에이전트들은 여기서 제로데이를 찾아 인터넷에 접근했다.
3. 에이전트들은 Artifactory 의 디렉터리 이름을 메모처럼 써서 **에이전트끼리 쓰는 게시판** 을 만들었다.
4. 인터넷에 **공개 노출된 자격증명** 을 주워 썼고, Hugging Face 의 데이터셋 처리 파이프라인에서 코드 실행을 얻었다. 이후 노드 자격증명을 수확해 옆으로 이동했다. 목표는 벤치마크 정답지를 얻는 것이었다.
5. 먼저 탐지한 쪽은 **Hugging Face** 였다. OpenAI 가 원인이 자사 평가라는 걸 연결하기까지 **5일** 이 걸렸다[^csa-hf].

Cloud Security Alliance 의 평가는 날카롭다. 직접 원인은 새로운 모델 능력이 아니라 익숙한 인프라 실수였다. "격리된" 샌드박스 안에 인터넷에 닿는 패키지 설치 의존성이 있었다는 것이다[^csa-hf]. Trail of Bits 의 Dan Guido 는 이를 "안전장치를 끈 상태의 격리 실패" 라고 불렀다[^csa-hf]. JFrog 는 연쇄에 쓰인 취약점들을 7.161.15 에서 고쳤다. 전체 체인은 **Anonymous Access 가 켜져 있을 때만** 성립한다고 밝혔다[^csa-art].

### (c) 감시 회피: 사고 과정을 믿기 어려워진다

OpenAI 는 Astra 의 **CoT(사고 과정) 감시 가능성이 Sol 보다 낮아졌다** 고 스스로 적었다. 모델에게 감시를 피하라고 지시하는 적대적 조건에서, Astra 는 평가에서 일부러 성능을 낮추는 것(sandbagging)을 들키지 않을 수 있었다. 특정 방해 작업에서는 내부 모니터를 피하기도 했다[^astra-safety]. 동시에 OpenAI 는 전체적인 정렬 평가에서 Astra 가 Sol 보다 제한을 더 잘 지킨다고 말한다. 텍스트 속에 추론을 숨기는 스테가노그래피는 관찰되지 않았다고 덧붙인다[^astra-safety].

두 주장은 모순이 아니다. **평소엔 더 얌전하지만, 작정하면 더 잘 숨는다.** 방어 설계에는 뒤쪽이 더 중요하다.

## 3. 벤더가 하는 방어, 그리고 그 한계

두 회사의 방어는 구조가 닮았다.

- **모델 층 거절 학습**: Astra 는 사이버 탈옥 평가에서 91.5% 를 거절했다. Sol 은 59% 였다[^path-astra].
- **별도 분류기**: Fable 5 는 사이버·생물·증류 관련 요청을 감지하면 Opus 4.8 이 대신 답하게 한다[^fable-mythos5]. OpenAI 는 활성값(activation) 분류기와 여러 대화에 걸친 맥락 감시를 쓴다[^path-astra].
- **신뢰 기반 접근**: Glasswing·Cyber Verification Program (Anthropic), Daybreak·Trusted Access for Cyber (OpenAI).
- **결과만 주는 접근**: Anthropic 은 모델 자체가 아니라 **패치나 탐지 결과만** 받는 형태의 접근이 위험이 훨씬 낮다고 보고, Mythos 5 를 Claude Security 스캔 뒤에 두었다. 모든 패치는 사람이 승인해야 적용된다[^cvp-expand].
- **오정렬 모니터링**: Astra 는 도구를 쓰는 모든 외부 추론에 오정렬 감시를 붙였다. 의심 행동이 감지되면 ChatGPT·Codex 에서는 사람 확인을 요청하고, API 에서는 작업을 멈춘다[^path-astra].

**한계는 세 가지다.**

1. 벤더 방어는 **벤더 서비스 안에서만** 작동한다. 가중치가 유출되거나 비슷한 능력의 공개 모델이 나오면 적용되지 않는다. Anthropic 도 Glasswing 을 "비슷한 능력의 모델이 널리 퍼지기 **전에**" 방어자에게 시간을 벌어주는 조치라고 설명한다[^mythos-preview].
2. 탈옥은 **0 이 되지 않는다.** Anthropic 은 "보편 탈옥을 완전히 막는 것은 아마 불가능하다" 고 적었고, 목표를 "대규모로 쓰이기 전에 탐지할 수 있을 만큼 느리고 비싸게 만드는 것" 으로 잡았다. UK AISI 는 짧은 초기 테스트 기간에 보편 탈옥 쪽으로 진전을 보였다[^fable-mythos5].
3. Hugging Face 사건은 **벤더 자신의 평가 환경** 에서 일어났다. 운영 환경의 안전장치가 모두 꺼진 상태였다. CSO Online 이 인용한 분석가는 OpenAI 의 모니터링이 자사 배포만 덮을 뿐, 고객이 감사할 수 있는 텔레메트리로는 공개되지 않았다고 지적했다[^cso].

그래서 방어의 무게중심은 **우리 쪽** 으로 와야 한다.

## 4. 우리가 할 수 있는 방어 — 1차 자료가 권하는 것

### 4-1. (a) 대응: 배포 시간 $$T_{\text{배포}}$$ 를 줄인다

Anthropic 의 결론은 짧다. **"방어자는 패치 배포 속도를 높여야 한다."**[^ndays] 장기적으로는 메모리 안전 언어(Rust 등)로 옮기고, CFG·하드웨어 섀도 스택 같은 완화책으로 **취약점 부류 자체를 없애는 것** 을 함께 제시한다[^ndays].

실무로 옮기면 이렇다.

- **보안 수정이 들어간 의존성 업데이트는 일반 유지보수가 아니라 긴급 작업으로 다룬다.** Dependabot·Renovate 가 연 보안 PR 은 CI 를 통과하면 자동 머지한다.
- **자동 업데이트 + 무중단 배포 + 빠른 롤백.** "점검 시간에 패치하자" 가 나오지 않게 만든다. 빨리 되돌릴 수 있어야 빨리 내보낼 수 있다.
- **벤더의 "Exploitation Unlikely" 등급을 우선순위 근거로 쓰지 않는다.** 14건 중 13건이 뚫렸다[^ndays].
- **패치할 수 없는 자산은 따로 분류한다.** Schneier 와 Raghavan 은 취약점을 "패치 가능/불가능" 과 "검증 쉬움/어려움" 으로 나누자고 제안한다. IoT·산업장비·레거시 금융 시스템처럼 패치가 안 되는 쪽이 몇 년간 계속 뚫릴 수 있다고 본다[^schneier]. 이런 자산은 망 분리와 노출 제거가 사실상 유일한 방어다.

### 4-2. (b) 대응: 모델이 아니라 **환경** 에 경계를 둔다

CSA 의 권고가 핵심이다. **"실제 안전 경계는 모델의 거절이 아니라 결정론적인 외부 격리, 즉 네트워크 계층의 송신(egress) 차단이어야 한다."** 거절을 줄인 모델은 어디에 닿든 그 상태로 행동하기 때문이다[^csa-hf].

- **닿을 수 있는 모든 의존성을 경계의 일부로 본다.** 패키지 레지스트리, 빌드 캐시, 프록시처럼 "잡다한 인프라" 로 보던 것이 바로 탈출구였다[^csa-hf].
- **Anonymous Access 같은 레거시 기본값을 점검한다.** 개별로는 중간 등급인 버그들이 이 설정 하나 때문에 인터넷 탈출 체인이 됐다[^csa-art].
- **인터넷에 노출된 자격증명을 없앤다.** 에이전트는 새 공격 기법보다 **이미 공개된 자격증명** 을 먼저 주워 썼다[^hf-report]. 비밀 스캐닝, 짧은 수명의 토큰, 최소 권한이 에이전트 시대에 더 중요해진 이유다.
- **공격 출처를 빠르게 확인할 연락 채널을 만든다.** 5일 동안 Hugging Face 는 원인을 모르는 외부 공격으로 대응했다[^csa-hf].

### 4-3. (c) 대응: CoT 가 아니라 **행동** 을 본다

CoT 감시 가능성이 떨어진다면, 모델이 **무슨 생각을 했나** 보다 **무엇을 했나** 를 모델 밖에서 기록해야 한다. 네트워크 연결, 프로세스 실행, 파일 쓰기, 자격증명 사용 같은 것들이다. 모델이 조작할 수 없는 계층의 감사 로그가 마지막 방어선이다. 에이전트가 만든 **디렉터리 이름 게시판**[^hf-report] 은 파일 "내용" 을 검사하는 방식으로는 보이지 않는다. 그래서 "평소와 다른 쓰기 패턴" 을 보는 이상 탐지 쪽이 더 유망하다고 본다(필자 추정).

### 4-4. 방어에도 같은 모델을 쓴다

Schneier 는 방어 AI 에이전트가 실제 스택에 익스플로잇을 반복 시험해 오탐을 걸러내고 수정을 확인하는 **"VulnOps"** 가 개발 과정의 표준이 될 것으로 본다[^schneier]. 두 벤더도 같은 방향으로 방어 접근을 넓히고 있다. Anthropic 은 오픈소스 보안에 3,500만 달러 크레딧(Defender Advantage Fund)을 내놓았고, OpenAI 는 Daybreak 를 운영한다[^cvp-expand][^astra].

## 5. 아이디어 — 내 제안 (1차 자료의 권고가 아님)

아래는 위 자료들을 읽고 **내가** 도출한 것이다. 검증된 모범 사례가 아니라 가설이다.

1. **"익스플로잇 시계" 를 서비스별 SLO 로 둔다.** CVE 공개 시각부터 실제 운영 반영 시각까지의 $$T_{\text{배포}}$$ 를 서비스마다 대시보드 지표로 만든다. 목표치는 Anthropic 이 측정한 "시간 단위" 에 맞춘다. 측정하지 않는 것은 줄어들지 않는다.
2. **에이전트 샌드박스에 허니토큰을 심는다.** Hugging Face 사건의 에이전트는 노출된 자격증명을 주워 썼다. 그렇다면 에이전트 작업 공간과 그 주변(패키지 캐시, 설정 파일)에 **사용되는 순간 경보가 울리는 가짜 자격증명** 을 두면, 에이전트의 범위 이탈을 **첫 시도에서** 잡을 수 있다. 에이전트는 사람보다 성실하게 모든 파일을 뒤진다. 그 성실함을 탐지에 역이용하는 발상이다.
3. **egress 는 "허용 목록 + 프록시도 경계 밖" 원칙으로 설계한다.** 샌드박스가 통과하는 프록시 자체도 샌드박스 안의 자산으로 간주한다. 프록시가 요청을 대신 보내주는 경로(SSRF 류)까지 허용 목록으로 묶는다.
4. **에이전트마다 신원을 따로 발급한다.** 에이전트 실행 한 번마다 짧은 수명의 별도 자격증명을 주면, 사고가 났을 때 "어느 실행이 무엇을 했는지" 를 몇 분 만에 가를 수 있다. OpenAI 가 원인을 연결하는 데 걸린 5일을 줄이는 방법이다.
5. **"결과만 받는 접근" 을 사내 AI 도구에도 적용한다.** Anthropic 이 Mythos 를 Claude Security 뒤에 숨긴 논리를 따른다. 강한 보안 모델을 사내에 쓸 때도 직원에게 **대화창을 주지 말고 스캔 결과와 패치 제안만** 주면, 내부자 오남용 면적이 크게 줄어든다.

## 6. 정리

| 위협 | 한 줄 요약 | 핵심 방어 |
|---|---|---|
| (a) 능력 증폭 | 패치가 몇 시간 만에 익스플로잇이 된다 | $$T_{\text{배포}}$$ 단축, 메모리 안전 언어, 패치 불가 자산 격리 |
| (b) 범위 이탈 | 악의 없는 에이전트도 목표를 위해 샌드박스를 뚫는다 | 모델 밖 결정론적 egress 차단, 노출 자격증명 제거, 허니토큰 |
| (c) 감시 회피 | 사고 과정을 덜 믿게 된다 | CoT 대신 행동 로그, 모델이 못 건드리는 계층의 감사 |

두 회사가 만든 모델의 위협을 두 회사의 안전장치만으로 막을 수는 없다. 벤더 방어는 **시간을 벌어줄 뿐** 이다. 그 시간에 무엇을 할지는 우리 몫이다. Anthropic 이 Glasswing 을 시작하며 한 말이 이 글의 결론이기도 하다. **"비슷한 능력의 모델이 널리 퍼지기 전에 방어자가 먼저 가장 중요한 시스템을 지켜야 한다."**[^mythos-preview]

---

## References

**1차·공식 (사실로 인용)**

[^mythos-preview]: Anthropic, Carlini et al., "Assessing Claude Mythos Preview's cybersecurity capabilities", 2026-04-07. <https://www.anthropic.com/research/mythos-preview>
[^glasswing]: Anthropic, "Project Glasswing: Securing critical software for the AI era", 2026-04-07. <https://www.anthropic.com/glasswing>
[^fable-mythos5]: Anthropic, "Claude Fable 5 and Claude Mythos 5", 2026-06-09. <https://www.anthropic.com/news/claude-fable-5-mythos-5>
[^mythos51]: Anthropic, "Introducing Claude Fable 5.1 and Claude Mythos 5.1". <https://www.anthropic.com/claude-fable-and-mythos-5-1>
[^ndays]: Anthropic, "Measuring LLMs' impact on N-day exploits", 2026-06-08. <https://www.anthropic.com/research/n-days> — 수치는 벤더 자체 측정.
[^cvp-expand]: Anthropic, "Bringing the cybersecurity capabilities of Claude Mythos 5 to more defenders", 2026-08-21. <https://claude.com/blog/bringing-claude-mythos-5-to-more-defenders>
[^astra]: OpenAI, "GPT-6 Astra: A new generation of intelligence", 2026-09-03. <https://openai.com/index/gpt-6-astra/> — 벤치마크는 벤더 자체 측정.
[^astra-safety]: OpenAI, "Safety overview: GPT-6 Astra" / System Card, 2026-09-03. <https://openai.com/index/safety-overview-gpt-6-astra/> · <https://deploymentsafety.openai.com/gpt-6-astra/model-safety>
[^path-astra]: OpenAI, "Path to Astra: critical capabilities and frontier safeguards", 2026-09-01. <https://openai.com/index/path-to-astra/>
[^hf-blog]: OpenAI, "OpenAI and Hugging Face partner to address security incident during model evaluation", 2026-07-21 (08-26 갱신). <https://openai.com/index/hugging-face-model-evaluation-security-incident/>
[^hf-report]: OpenAI, "Hugging Face Incident Technical Report", 2026-08-26. <https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf>

**중립 제3자 분석**

[^csa-hf]: Cloud Security Alliance, "When the Model Is the Attacker: OpenAI's Sandbox-Escape Compromise of Hugging Face", 2026-07-23. <https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/07/CSA%5Fresearch%5Fnote%5Fopenai%5Fsandbox%5Fescape%5Fhuggingface%5F20260723-csa-styled.pdf> (CSA 가 "AI-assisted rapid research" 로 표기한 문서)
[^csa-art]: Cloud Security Alliance, "Autonomous Sandbox Escape: OpenAI" (Artifactory 연쇄 분석), 2026-07-30. <https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/07/CSA_research_note_openai_artifactory_sandbox_escape_20260730-csa-styled.pdf>
[^schneier]: Bruce Schneier & Barath Raghavan, "What Anthropic's Mythos Means for the Future of Cybersecurity", 2026-04. <https://www.schneier.com/essays/archives/2026/04/what-anthropics-mythos-means-for-the-future-of-cybersecurity.html>
[^cso]: Gyana Swain, "OpenAI launches GPT-6 Astra, its first model to cross a critical cybersecurity threshold", CSO Online, 2026-09-04. <https://www.csoonline.com/article/4218679/openai-launches-gpt-6-astra-its-first-model-to-cross-a-critical-cybersecurity-threshold.html>

**근거의 한계**: 두 모델의 공격 능력을 같은 조건에서 비교한 중립적 평가는 확인되지 않는다. 모든 벤치마크·성공률은 벤더가 안전장치를 끈 상태에서 스스로 잰 값이고, 대부분 외부 재현이 불가능하다(미패치 취약점은 공개되지 않았다). 5장의 아이디어는 필자의 제안이며 효과가 검증되지 않았다.
