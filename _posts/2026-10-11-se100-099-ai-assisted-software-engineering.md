---
layout: post
title: "[SE100 #099] AI 보조 개발과 소프트웨어 공학"
date: 2026-10-11 17:10:49 +0900
categories: [software-engineering]
tags: [se100, evolution-and-people, ai-assisted-development, empirical-software-engineering, code-security, llm]
---

소프트웨어 공학 100 주제 시리즈의 99번째 글이다. (카테고리: 유지보수·진화·사람)

## 한 줄 요약

AI 코딩 도구의 효과에 대한 증거는 **누가, 어떤 설계로, 무엇을 쟀는가** 에 따라 정반대로 나온다. 벤더 실험은 큰 속도 향상을, 독립 무작위 실험은 숙련자의 감속을, 동료심사 보안 연구는 취약 코드와 과신을 보고한다. 소프트웨어 공학의 기존 도구 — 리뷰, 테스트, 공급망 통제, 측정 — 는 사라지지 않고 더 중요해진다.

## 왜 필요한가

"AI 로 생산성 55% 향상" 같은 문장이 도입 결정의 근거가 된다. 그런데 이 수치가 어떤 과제에서, 누구를 대상으로, 누가 잰 것인지 묻지 않으면 다음 일이 생긴다.

- 작은 독립 과제에서 잰 속도를 수년 된 대형 코드베이스의 유지보수에 그대로 기대한다.
- 개발자의 체감("빨라진 것 같다")을 측정치로 착각한다.
- 생성된 코드를 사람이 쓴 코드보다 덜 검토한다. 보안 결함과 존재하지 않는 패키지가 그대로 들어온다.

## 핵심 개념

### 증거를 읽는 틀

| 질문 | 왜 중요한가 |
|---|---|
| 누가 수행했나 (벤더 / 벤더 소속 연구자 / 독립 기관 / 학계) | 이해 상충 |
| 동료심사를 거쳤나 (학회·저널 / 프리프린트 / 블로그) | 방법론 검증 여부 |
| 설계는 무엇인가 (무작위 대조 실험 / 관찰 / 설문 / 벤치마크) | 인과 주장 가능 여부 |
| 과제는 무엇인가 (작은 신규 과제 / 실제 저장소의 실제 이슈) | 외적 타당도 |
| 무엇을 쟀나 (완료 시간 / 체감 / 결함 / 보안) | 산출과 결과의 구분 |

앞 글(SE100 #095)의 SPACE 관점으로 보면, 대부분의 생산성 연구는 **활동(Activity)과 효율(Efficiency)** 차원의 일부만 잰다. 성과(Performance) — 결함, 보안, 장기 유지보수성 — 를 함께 잰 연구는 드물다.

### 1) 벤더 및 벤더 소속 연구자의 결과

| 출처 | 성격 | 결과 |
|---|---|---|
| GitHub 블로그, [Research: quantifying GitHub Copilot's impact](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/) (2022, 2024 갱신) | **벤더 주장** | 95명 대상 실험에서 Copilot 사용 그룹이 과제를 55% 빨리 완료(1시간 11분 대 2시간 41분). 2,000명 이상 설문에서 다수가 더 빨라졌다고 체감 |
| Peng, Kalliamvakou, Cihon, Demirer, [The Impact of AI on Developer Productivity: Evidence from GitHub Copilot](https://arxiv.org/abs/2302.06590) (2023) | 프리프린트, 저자 중 셋이 Microsoft Research·GitHub 소속 | JavaScript 로 HTTP 서버 구현 과제에서 처리 그룹이 55.8% 빨리 완료 |
| Google, [How much does AI impact development speed? An enterprise-based randomized controlled trial](https://arxiv.org/abs/2410.12944) (2024) | 프리프린트, 자사 도구를 자사 엔지니어 96명에게 실험 | 과제 소요 시간 약 21% 단축 추정, 저자 스스로 신뢰구간이 크다고 밝힘 |

공통점은 **도구를 파는 쪽이 설계·수행했고**, 과제가 **잘 정의된 단일 과제** 라는 것이다. 무작위 대조 설계는 견고하지만 다른 과제·코드베이스로의 일반화에는 한계가 있다. Google 논문도 실험실 결과가 더 넓게 적용된다고 가정할 수 없다고 명시한다.

### 2) 독립 기관의 무작위 대조 실험

비영리 연구기관 METR 의 Becker, Rush, Barnes, Rein 은 [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity](https://arxiv.org/abs/2507.09089) (2025, 프리프린트)에서 다른 질문을 던졌다. 숙련 개발자가 **자기가 평균 5년간 기여해 온 성숙한 오픈소스 저장소** 의 실제 이슈를 처리할 때는 어떤가.

- 개발자 16명, 과제 246개, 과제마다 AI 허용/금지를 무작위 배정
- AI 허용 시 주로 Cursor Pro 와 Claude 3.5/3.7 Sonnet 사용
- 개발자들은 시작 전 **24% 단축** 을 예상했고, 끝난 뒤에도 **20% 단축** 됐다고 추정
- 실제로는 완료 시간이 **19% 증가**
- 경제학 전문가는 39%, ML 전문가는 38% 단축을 예측했었다

가장 큰 교훈은 감속 자체보다 **체감과 실측의 괴리** 다. 체감 설문 기반 주장을 그대로 믿으면 안 되는 이유다. 동시에 이 연구도 동료심사 전 프리프린트이고 표본이 16명이며, 저자들은 실험 설계의 영향을 완전히 배제할 수는 없다고 적는다. 반대 방향의 일반 법칙으로 읽어서도 안 된다.

### 3) 동료심사를 거친 보안·신뢰성 연구

| 연구 | 게재 | 결과 |
|---|---|---|
| Pearce 외, [Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions](https://arxiv.org/abs/2108.09293) | IEEE S&P 2022 | 고위험 CWE 관련 89개 시나리오에서 1,689개 프로그램을 생성, 약 40% 가 취약 |
| Perry, Srivastava, Kumar, Boneh, [Do Users Write More Insecure Code with AI Assistants?](https://arxiv.org/abs/2211.03622) | ACM CCS 2023 | AI 보조(codex-davinci-002) 사용자가 유의하게 덜 안전한 코드를 작성했고, **자기 코드가 안전하다고 믿을 가능성은 더 높았다**. AI 를 덜 신뢰하고 프롬프트를 적극 조정한 참가자는 취약점이 적었다 |
| Spracklen 외, [We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs](https://arxiv.org/abs/2406.10279) | USENIX Security 2025 | 16개 모델로 576,000개 코드 샘플 생성. 존재하지 않는 패키지 추천 비율 평균이 상용 모델 최소 5.2%, 오픈 모델 21.7%. 고유한 환각 패키지 이름 205,474개 |

세 연구는 모델 세대가 지금과 다르다. 수치를 현재 도구에 그대로 대입하면 안 된다. 그러나 **구조적 위험** — 학습 데이터의 취약 패턴 재생산, 사용자의 과신, 존재하지 않는 의존성 — 은 모델이 바뀌어도 통제가 필요한 범주다. 특히 패키지 환각은 공격자가 그 이름으로 악성 패키지를 등록할 수 있다는 점에서 공급망 문제다.

### 4) 벤치마크와 조직 수준 조사

- [SWE-bench](https://arxiv.org/abs/2310.06770) (Jimenez 외, ICLR 2024)는 12개 Python 저장소의 실제 GitHub 이슈 2,294개로 모델을 평가한다. 발표 당시 최고 모델(Claude 2)의 해결률은 1.96% 였다. 이후 [리더보드](https://www.swebench.com/)의 수치는 크게 올랐지만, 벤치마크 점수는 **특정 과제 분포에서의 능력** 이지 팀 생산성이 아니다.
- [DORA 2024 보고서](https://dora.dev/research/2024/dora-report/)는 AI 도입이 개인 생산성·몰입·직무 만족을 높이지만 **소프트웨어 전달 안정성과 처리량에는 부정적** 영향을 보였다고 요약하고, 작은 배치와 견고한 테스트 같은 기본기를 강조한다. [DORA 2025 보고서](https://dora.dev/research/2025/dora-report/)는 AI 의 주된 역할을 조직의 기존 강점과 약점을 **증폭** 하는 것으로 정리한다. 다만 DORA 는 설문 기반 연구이고, 2025년판 연구 파트너에 GitHub, GitLab 같은 도구 기업이 포함되어 있다.

## 실무 적용

### AI 생성 코드를 "신뢰되지 않은 기여" 로 다룬다

외부 기여자의 PR 과 같은 기준으로 다룬다. 출처가 사람인지 모델인지보다 **검증 경로** 가 중요하다.

| 위험 | 통제 |
|---|---|
| 취약 패턴 | SAST, 보안 리뷰 체크리스트, 위험 영역(인증·암호·입력 처리) CODEOWNERS |
| 과신 | 리뷰어가 "AI 가 썼으니 맞겠지" 를 막는 리뷰 규칙, 작성자가 설명 못 하는 코드는 병합 금지 |
| 존재하지 않는/악성 패키지 | 새 의존성은 별도 승인, 내부 미러·허용 목록, 잠금 파일 |
| 테스트 없는 대량 변경 | 작은 배치, 변경과 테스트를 함께, CI 필수 |
| 비밀정보 유출 | 프롬프트·컨텍스트에 비밀 금지, 비밀 스캐너 |

생성형 AI 를 다루는 개발 조직의 보안 관행은 NIST 의 [SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final) (생성형 AI·이중용도 기반 모델을 위한 SSDF 커뮤니티 프로필)가 참고가 된다.

### 예: 새 의존성 게이트

PR 에서 새로 추가된 Python 의존성이 허용 목록에 없으면 CI 를 실패시킨다.

```python
# ci/check_new_deps.py
import re, subprocess, sys, tomllib

ALLOW = set(open("ci/allowed-packages.txt").read().split())

def deps(ref: str) -> set[str]:
    raw = subprocess.run(["git", "show", f"{ref}:pyproject.toml"],
                         capture_output=True, text=True, check=True).stdout
    spec = tomllib.loads(raw)["project"].get("dependencies", [])
    return {re.split(r"[<>=!~\[; ]", d, maxsplit=1)[0].lower() for d in spec}

added = deps("HEAD") - deps("origin/main")
unknown = sorted(added - ALLOW)
if unknown:
    print("허용 목록에 없는 새 의존성:", ", ".join(unknown))
    print("레지스트리 실재 여부, 메인테이너, 다운로드 이력, 라이선스를 확인하고 승인 PR 을 따로 올릴 것")
    sys.exit(1)
```

### 측정은 실측으로

- 도입 전후를 **같은 지표** 로 비교한다. 체감 설문만으로 판단하지 않는다. METR 결과가 보여 준 괴리 때문이다.
- SPACE 의 성과 차원(변경 실패율, 결함, 보안 이슈)을 함께 본다.

## 흔한 오해와 함정

- **"55% 빨라진다."** 벤더가 설계한 단일 신규 과제의 결과다. 숙련자가 익숙한 대형 저장소에서 일할 때 독립 실험은 반대 결과를 냈다. 어느 쪽도 보편 법칙이 아니다.
- **"개발자들이 빨라졌다고 하니 빨라진 것이다."** METR 실험에서 개발자는 19% 느려졌는데 20% 빨라졌다고 추정했다.
- **"최신 모델이니 옛 보안 연구는 무관하다."** 수치는 낡아도 위험 범주는 남는다. 과신은 모델이 아니라 사용자 쪽 현상이다.
- **리뷰를 AI 에 맡겨 리뷰 부담을 없앤다.** 생성과 검토가 같은 맹점을 공유할 수 있다. 사람의 책임 있는 승인은 남긴다.

## 확인 문제

1. AI 생산성 연구를 읽을 때 확인할 다섯 질문을 쓰라.
2. Peng 외(2023)와 METR(2025) 연구의 결과가 다른 이유를 과제와 대상의 차이로 설명하라.
3. Perry 외(CCS 2023)의 두 핵심 발견은 무엇이며, 리뷰 프로세스에 주는 시사점은?
4. 패키지 환각이 공급망 위험인 이유와 통제 방법은?
5. DORA 2024 보고서의 AI 관련 요약을 SPACE 차원으로 해석하라.

### 풀이

1. 누가 수행했나, 동료심사를 거쳤나, 설계는 무엇인가, 과제는 무엇인가, 무엇을 쟀나.
2. Peng 외는 모집된 개발자가 새 HTTP 서버를 구현하는 잘 정의된 단일 과제였고(벤더 소속 저자 포함), METR 은 숙련 개발자가 오래 기여한 성숙한 대형 저장소의 실제 이슈를 처리했다. 맥락 이해와 품질 기준이 중요한 환경에서는 결과가 다를 수 있다.
3. AI 보조 사용자가 덜 안전한 코드를 썼고, 동시에 더 안전하다고 믿었다. 작성자의 확신을 품질 신호로 쓰지 말고, 보안 민감 코드에 독립 리뷰와 자동 분석을 의무화해야 한다.
4. 모델이 존재하지 않는 패키지를 추천하면 공격자가 그 이름으로 악성 패키지를 등록해 설치를 유도할 수 있다. 새 의존성 승인 절차, 허용 목록·내부 미러, 잠금 파일로 통제한다.
5. 개인 생산성·몰입·만족 향상은 Satisfaction 과 개인 수준 Efficiency 에, 전달 안정성·처리량 저하는 시스템 수준 Performance 와 Efficiency 에 해당한다. 개인 수준의 개선이 시스템 수준의 개선으로 자동 이어지지 않는다는 뜻이다.

## 더 읽을거리 (References)

- S. Peng, E. Kalliamvakou, P. Cihon, M. Demirer, [The Impact of AI on Developer Productivity: Evidence from GitHub Copilot](https://arxiv.org/abs/2302.06590), arXiv, 2023
- GitHub, [Research: quantifying GitHub Copilot's impact on developer productivity and happiness](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-on-developer-productivity-and-happiness/) (벤더 주장)
- Google, [How much does AI impact development speed? An enterprise-based randomized controlled trial](https://arxiv.org/abs/2410.12944), arXiv, 2024
- J. Becker, N. Rush, E. Barnes, D. Rein, [Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity](https://arxiv.org/abs/2507.09089), arXiv, 2025 / [METR 요약](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
- H. Pearce 외, [Asleep at the Keyboard?](https://arxiv.org/abs/2108.09293), IEEE S&P 2022
- N. Perry, M. Srivastava, D. Kumar, D. Boneh, [Do Users Write More Insecure Code with AI Assistants?](https://arxiv.org/abs/2211.03622), ACM CCS 2023
- J. Spracklen 외, [We Have a Package for You!](https://arxiv.org/abs/2406.10279), USENIX Security 2025
- C. E. Jimenez 외, [SWE-bench](https://arxiv.org/abs/2310.06770), ICLR 2024
- DORA, [2024 Accelerate State of DevOps Report](https://dora.dev/research/2024/dora-report/) / [2025 State of AI-assisted Software Development](https://dora.dev/research/2025/dora-report/)
- NIST, [SP 800-218A](https://csrc.nist.gov/pubs/sp/800/218/a/final)
- [AI 에이전트와 도구 사용]({% post_url 2026-10-10-cs300-277-ai-agents-and-tool-use %}) (CS300 #277), [소프트웨어 공급망 보안]({% post_url 2026-10-10-cs300-257-software-supply-chain-security %}) (CS300 #257)
