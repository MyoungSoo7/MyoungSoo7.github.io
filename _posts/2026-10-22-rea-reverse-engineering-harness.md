---
layout: post
title: "역공학 하네스 REA 와 리버스 엔지니어링 — 에이전트가 바이너리를 뜯을 때 필요한 건 모델보다 '증거의 구조'다"
date: 2026-10-22 11:22:24 +0900
categories: [AI, Security]
tags: [Reverse Engineering, REA, MCP, Harness, Ghidra, IDA, Hopper, JADX, Interoperability]
---

요즘 코딩 에이전트 주변에서 가장 많이 언급되는 리포 중 하나가 [REA(Reverse Engineer Anything)](https://github.com/morluto/rea)다. 에이전트에게 소스 코드가 없는 프로그램 — 네이티브 바이너리, Electron 앱, APK, 펌웨어, 패킷 캡처 — 을 뜯어보게 해 주는 MCP 서버이자 CLI 다. 2026-10-22 에 GitHub API 로 조회했을 때 스타가 약 35만 8천 개였다.

이 글은 두 가지를 정리한다. 하나는 **리버스 엔지니어링이 원래 무엇이었는가**, 다른 하나는 **REA 가 거기에 무엇을 얹었는가**다. 결론부터 말하면 REA 가 새로 만든 건 디컴파일러가 아니다. Ghidra 도 IDA 도 Hopper 도 이미 있었다. REA 가 만든 건 그 도구들을 에이전트가 쓸 수 있게 묶고, 결과를 **"본 것 / 추론한 것 / 모르는 것"** 으로 나눠 돌려주는 **하네스**다.

## 1. 리버스 엔지니어링은 "고치는 일" 이 아니라 "다시 그리는 일" 이다

용어의 기준점으로 자주 인용되는 건 Chikofsky 와 Cross 의 1990년 IEEE Software 논문 「Reverse engineering and design recovery: a taxonomy」다.[^chikofsky] 이 논문은 리버스 엔지니어링을 대략 이렇게 정의한다. **대상 시스템을 분석해 구성 요소와 그 관계를 식별하고, 그 시스템을 다른 형태나 더 높은 추상 수준으로 표현하는 과정.**

두 가지가 중요하다.

- **산출물은 "표현" 이다.** 바이너리를 의사코드로, 의사코드를 호출 그래프로, 호출 그래프를 "이 기능은 이렇게 동작한다" 는 설명으로. 단계마다 추상 수준이 올라간다.
- **대상을 바꾸지 않는다.** 이 논문의 분류에서 리버스 엔지니어링은 조사(examination)이고, 바꾸는 건 그다음 단계(재구조화, 리엔지니어링)의 일이다.

이 관점으로 보면 디컴파일러는 출발점일 뿐이다. 진짜 일은 그 출력에서 **어디까지가 확인된 사실이고 어디부터가 해석인지**를 가르는 데 있다. 사람 분석가는 이걸 머릿속과 노트로 해 왔다. 에이전트에게 맡기면 이 구분이 가장 먼저 무너진다. 언어 모델은 그럴듯한 설명을 확신에 찬 문장으로 내놓는 데 능하기 때문이다.

## 2. REA 가 하는 일

README 의 한 줄 소개는 이렇다. "One MCP for reverse engineering across binaries, applications, and runtime behavior."[^readme]

### 도구를 한 인터페이스로

REA 는 기존 분석 도구들을 MCP 서버 하나 뒤에 묶는다. 같은 워크플로를 터미널 CLI(`rea`)로도 쓸 수 있다. README 의 대상 표에서 몇 개만 뽑으면 이렇다.[^readme]

| 대상 | REA 가 돌려주는 것 | 필요한 도구 |
|---|---|---|
| 네이티브 바이너리 | 의사코드, 어셈블리, 문자열, 심볼, 호출·참조 | Hopper, Ghidra 또는 IDA |
| JavaScript / Electron | 모듈, import, 소스맵, 라우트, IPC, 네이티브 애드온 관계 | Node.js, npm |
| Android APK | 매니페스트, 클래스, 디컴파일된 메서드, 참조 | JADX + JDK |
| 기록된 패킷 | 선택 필드, 반복 값, 필터 | TShark (Linux) |
| .NET 어셈블리 | 메타데이터, CIL 명령, 네이티브 의존성 | 없음 (정적 분석만) |
| 펌웨어 | 영역, 추출 결과, 네이티브 분석으로 넘기기 | Binwalk / Unblob (Linux) |

설치는 `npx rea-agents setup` 한 줄이다. 실행하면 에이전트를 고르게 하고, 바꿀 설정을 보여 준 뒤 **승인을 받아** MCP 서버 등록과 조사용 워크플로 지침을 넣는다. 기존 설정은 백업한다.[^readme]

### 증거 레코드 — REA 의 핵심

REA 의 CLI 문서는 결과물인 Evidence 레코드를 이렇게 설명한다.[^cli]

> Evidence records retain artifact identity, source locations, observations, inferences and unresolved findings.

즉 모든 결과에 **어떤 파일(아티팩트)의 어느 위치에서 나왔는지**가 붙고, 그 안에서 **관찰(observation)·추론(inference)·미해결(unresolved)** 이 섞이지 않게 분리돼 있다. README 도 "results include the evidence and limitations behind each conclusion" 이라고 강조한다.[^readme]

이 구조가 1장의 문제를 정면으로 겨냥한다. 에이전트가 "이 함수는 사운드 패닝을 계산한다" 고 말할 때, 그게 디컴파일 출력에서 **본 것**인지, 이름과 호출 패턴에서 **추론한 것**인지, 아직 **모르는 것**인지를 사람이 되짚을 수 있다. Evidence 는 파일로 내보내고(`evidence-export`), 다시 들여오고(`evidence-import`), 두 번들을 비교(`compare`)할 수도 있다.[^cli] 버전이 다른 두 바이너리를 비교하는 워크플로가 여기서 나온다.

### 쇼케이스 — 프로젝트 자신이 보고한 사례

README 에 실린 사례 중 하나는 DX-Ball 의 사운드 패닝 계산이다. 사운드 호출을 따라가 위치→패닝 헬퍼를 찾고, 불완전한 의사코드를 C 로 재구성했다. 프로젝트 보고에 따르면 재구성한 코드는 **원본 x86 대비 3,205개 케이스를 통과했고, 컴파일된 함수 바이트 63개를 모두 재현했다.**[^readme] 검증 방식이 "그럴듯해 보인다" 가 아니라 **원본과의 입출력 대조, 컴파일 결과 바이트 대조**라는 점이 이 사례의 요점이다. (수치는 프로젝트 측 보고이고, 내가 재현한 건 아니다.)

## 3. 왜 "하네스" 인가

에이전트에게 Ghidra 를 쥐여 주는 것만으로는 부족하다. 실제로 필요한 건 세 겹이다.

1. **도구 호출의 표준화** — 디컴파일러마다 다른 API·출력 형식을 MCP 도구 하나의 계약으로 맞춘다.
2. **조사 절차** — setup 이 에이전트 설정에 "대상을 어떻게 조사할지" 의 지침을 함께 설치한다. 파일을 무작정 뒤지는 대신 기능 → 진입점 → 호출 경로 순으로 좁혀 가도록.
3. **증거의 구조** — 관찰·추론·미해결을 분리하고 출처 위치를 남긴다.

모델이 바뀌어도 이 세 겹은 그대로 남는다. 모델을 더 좋은 걸로 바꾸면 추론이 좀 나아지겠지만, **확인된 것과 추측을 가르는 구조**는 모델이 아니라 하네스가 보장한다. 리버스 엔지니어링처럼 "틀린 확신" 의 비용이 큰 영역일수록 이 차이가 커진다.

## 4. 조심할 곳 — 프로젝트 문서가 직접 적어 둔 것들

REA 의 [DISCLAIMER.md](https://github.com/morluto/rea/blob/main/DISCLAIMER.md) 는 꽤 길고 구체적이다.[^disclaimer] 쓰기 전에 읽을 가치가 있는 부분만 옮긴다.

**결과는 틀릴 수 있다.**

> Decompilation, reconstruction, heuristics, and AI-assisted analysis may be incomplete or incorrect.

증거 레코드가 있는 이유가 바로 이것이다. 결론이 아니라 증거를 보고 판단하라는 것.

**"로컬 분석" 이 "외부로 안 나간다" 는 뜻은 아니다.** README FAQ 의 답은 이렇다.[^readme]

> REA analyzes targets locally. Your agent receives the tool results, and its model provider has its own data policy.

분석 자체는 로컬에서 돌지만, 그 결과(의사코드, 문자열, 심볼 등)는 에이전트를 거쳐 **모델 제공자에게 간다.** 사내 바이너리나 고객 펌웨어를 넣을 땐 이 경로가 보안 검토 대상이다.

**런타임 작업은 대상을 건드린다.** 정적 분석과 달리 일부 워크플로는 프로그램을 실행하고, 트래픽을 캡처하고, 연결된 장치를 조작한다. 면책 문서는 "아티팩트를 들여다볼 권한이 실행·가로채기·장치 변경 권한까지 주는 건 아니다" 라고 분명히 한다.[^disclaimer] 신뢰할 수 없는 대상은 격리된 환경에서 돌릴 것.

**상용 도구 라이선스는 따로다.** IDA Pro·Hex-Rays, Hopper, JEB 는 각자 정식으로 확보해야 하고, REA 는 어떤 라이선스나 키도 주지 않는다. 체험판·데모의 자동화 제한도 벤더 약관을 따른다.[^readme]

## 5. 법의 경계 — "기능을 이해하는 것" 과 "코드를 가져오는 것" 은 다르다

README 의 첫 문장은 도발적이다. "See a feature you like. Understand how it works, down to the binary level." 그리고 에이전트가 그 기능의 "a version for your project" 를 만들어 줄 수 있다고 한다.[^readme]

같은 프로젝트의 면책 문서는 지원하지 않는 용도를 명시한다. DRM·라이선스 검사·안티치트 같은 기술적 보호 조치 우회, 게임 치트, 권한 없는 시스템의 인증 우회, 그리고 **"copying proprietary software or reproducing its protected code and assets"**.[^disclaimer] 또 "분석 결과물을 얻었다고 원래 프로그램이나 생성된 출력에 대한 권리가 생기는 건 아니다" 라고 적는다.

즉 프로젝트 스스로 그은 선은 이렇다. **동작 원리를 이해하는 건 되고, 보호되는 코드와 자산을 베끼는 건 안 된다.** 법도 대체로 이 선 근처에서 예외를 둔다. 대표적인 두 예가 **상호운용성(interoperability)** 예외다.

- **미국** — DMCA 17 U.S.C. §1201(f) 는 프로그램 사본을 적법하게 사용할 권리를 얻은 사람이, 독자적으로 만든 프로그램과 다른 프로그램의 **상호운용에 필요한 요소를 식별·분석하는 목적에 한해** 접근 통제 기술을 우회할 수 있다고 정한다. 그 요소가 이미 쉽게 얻을 수 있는 게 아니어야 하고, 침해가 되지 않는 범위여야 한다.[^dmca]
- **EU** — 컴퓨터 프로그램 지침(Directive 2009/24/EC) 제6조는 독자 프로그램의 상호운용에 필요한 정보를 얻는 데 **불가결한** 경우 권리자 허락 없는 디컴파일을 허용한다. 조건은 적법한 사용자일 것, 그 정보를 이전에 쉽게 얻을 수 없었을 것, 필요한 부분에 한정할 것. 얻은 정보로 **실질적으로 유사한 프로그램을 만들거나** 상호운용 외 목적에 쓰는 건 금지된다.[^eu]
- **한국** — 저작권법에도 상호운용 목적의 "프로그램코드역분석" 조항이 있다. 다만 이 글을 쓰며 법령 원문을 직접 확인하지 못해 조문 내용은 옮기지 않는다. 국내에서 작업한다면 [국가법령정보센터](https://www.law.go.kr/)에서 저작권법 해당 조문을 직접 읽어 보길 권한다.

공통점이 보인다. 예외는 **"독자적으로 만든 프로그램이 다른 프로그램과 함께 동작하게 하려고"** 라는 목적에 묶여 있고, **"비슷한 걸 만들려고"** 는 그 목적에 들어가지 않는다(EU 지침은 이걸 명시적으로 금지한다). README 의 "마음에 드는 기능을 내 제품에" 라는 문구를 그대로 실행에 옮기기 전에, 그게 어느 쪽에 속하는지 먼저 따져야 한다. 소프트웨어 라이선스 약관이 리버스 엔지니어링 자체를 금지하는 경우도 있으니 그것도 함께 봐야 한다. (이 절은 법률 자문이 아니다.)

## 6. 정리

| 질문 | 답 |
|---|---|
| REA 는 디컴파일러인가? | 아니다. Ghidra·IDA·Hopper·JADX·TShark 등을 MCP·CLI 하나로 묶는 **하네스**다. |
| 핵심 가치는? | 결과를 **출처 위치 + 관찰·추론·미해결**로 나눈 Evidence 레코드. 에이전트의 확신과 사실을 분리한다. |
| 분석은 로컬인가? | 분석은 로컬. 하지만 **결과는 모델 제공자에게 간다.** |
| 무엇이든 해도 되나? | 아니다. 프로젝트가 DRM 우회·치트·인증 우회·보호 코드 복제를 명시적으로 지원하지 않고, 법의 예외도 대체로 **상호운용성** 목적에 묶여 있다. |

리버스 엔지니어링의 본질은 1990년의 정의에서 크게 바뀌지 않았다. 대상을 바꾸지 않고, 더 높은 수준의 표현으로 다시 그리는 일. 에이전트가 들어오면서 바뀐 건 그 "다시 그리기" 의 속도이고, 그만큼 **틀린 그림을 확신 있게 그리는 속도**도 빨라졌다. REA 가 하네스로서 의미가 있는 건, 그 그림의 선마다 "본 것인지, 추측한 것인지" 를 표시하게 만든다는 점이다.

## References

[^chikofsky]: E. J. Chikofsky, J. H. Cross II, "Reverse engineering and design recovery: a taxonomy", _IEEE Software_, 7(1), pp. 13–17, Jan. 1990. doi:10.1109/52.43044. <https://doi.org/10.1109/52.43044>
[^readme]: morluto/rea, README. <https://github.com/morluto/rea>
[^cli]: morluto/rea, "CLI and Evidence". <https://github.com/morluto/rea/blob/main/docs/cli.md>
[^disclaimer]: morluto/rea, DISCLAIMER.md. <https://github.com/morluto/rea/blob/main/DISCLAIMER.md>
[^dmca]: 17 U.S.C. §1201(f) "Reverse engineering", Legal Information Institute (Cornell Law School). <https://www.law.cornell.edu/uscode/text/17/1201>
[^eu]: Directive 2009/24/EC on the legal protection of computer programs, Article 6 "Decompilation". EUR-Lex: <https://eur-lex.europa.eu/eli/dir/2009/24/oj>. 조문 확인은 legislation.gov.uk 판본으로 했다: <https://www.legislation.gov.uk/eudr/2009/24/article/6>
