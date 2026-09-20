---
layout: post
title: "에이전트 정책은 어디에 두나 — build.nvidia.com 과 OpenShell 이 나눠놓은 두 층"
date: 2026-09-20 11:53:39 +0900
categories: [AI, Architecture]
tags: [Agent, NemoClaw, OpenShell, NVIDIA NIM, Nemotron, Security, Runtime]
---

오늘 아침에 해커톤 챗봇 리포를 하나 뜯어보고 글을 하나 썼다([링크](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/)). 결론은 한 문장이었다 — **가드레일이 클라이언트에 있으면 그건 가드레일이 아니라 기본값이다.**

그 글은 질문을 하나 남겨두고 끝났다. 그러면 **정책은 어디에 둬야 하나?**

답을 내 머리에서 짜내는 대신, 같은 문제를 제품으로 만들어 파는 쪽이 어떻게 층을 나눠놨는지 보기로 했다. 참고한 주소는 둘이다.

- **모델을 얻는 층** — <https://build.nvidia.com/>
- **에이전트가 무엇을 할 수 있는지 정하는 층** — [Securing Agents with NemoClaw and OpenShell (NVIDIA DLI, `DLI+S-FX-43+V1`)](https://learn.nvidia.com/courses/course-detail?course_id=course-v1:DLI+S-FX-43+V1)

이 두 주소가 서로 다른 일을 한다는 게 이 글의 전부다.

## 1. build.nvidia.com — 여기서 얻는 건 "능력"이다

첫 화면이 하는 말은 단순하다. *"Start Building Your AI Here."* 그리고 바로 아래 **Use Inference Endpoints — "Free inference with leading models"**.

2026-09-20 확인 시점에 전면에 걸려 있던 모델 타일들이다.

| 모델 | 붙어 있는 태그 |
| --- | --- |
| `moonshotai/kimi-k3` | Mixture-of-Experts, Multimodal, Reasoning, Image-to-Text |
| `deepseek-ai/deepseek-v4-pro-0813` | MoE, agentic, coding, reasoning |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | Long-running agents, Open, Text-to-Text |
| `nvidia/nemotron-3-ultra-550b-a55b` | Frontier, Long Context, MoE, Reasoning |

같은 페이지의 **Use Agentic Skills** 섹션은 스킬을 분야별로 세어서 보여준다 — AI and Machine Learning 169, Physical AI 69, Accelerated Computing 31, Developer Tools 30. (숫자는 카탈로그가 늘면 바뀐다. 확인 시점만 적어둔다.)

여기서 중요한 건 카탈로그 자체가 아니라 **성격**이다. 이 층에서 얻는 건 전부 *능력*이다. 더 긴 컨텍스트, 더 나은 추론, 더 많은 스킬. 능력은 "무엇을 할 수 있는가"를 늘린다. **"무엇을 하면 안 되는가"는 하나도 정하지 않는다.**

아침 글의 그 리포가 정확히 이 층만 쓰고 있었다. NIM 엔드포인트에 붙었고, 임베딩을 제대로 나눠 썼고, 검색 컨텍스트를 `system` 역할로 주입했다. 능력 쪽은 잘 했다. 그런데 "무엇을 하면 안 되는가"(예산 미달이면 그냥 넘어가지 말 것)는 브라우저 자바스크립트의 문자열에 있었다.

## 2. 두 번째 층 — NVIDIA 는 이걸 아예 다른 물건으로 분리해놨다

NemoClaw 제품 페이지의 FAQ에 이 글에서 제일 값이 나가는 문장이 있다.

> NemoClaw is the full agent deployment package—models, harness, tools, and runtime. OpenShell is the secure runtime inside it that enforces what the agent can access: files, networks, credentials, and tools.
> — [NVIDIA NemoClaw 제품 페이지](https://www.nvidia.com/en-us/ai/nemoclaw/)

읽는 방식에 따라 마케팅 문구로 넘길 수도 있는데, 나는 **설계 분류표**로 읽었다. OpenShell 이 통제한다고 열거한 항목이 넷이다 — **파일, 네트워크, 자격증명, 툴.**

이 넷을 아침의 해커톤 리포에 그대로 대보면 이렇게 된다.

| OpenShell 이 통제한다는 축 | 그 리포의 상태 |
| --- | --- |
| **credentials** | 게이트웨이 토큰이 `config.js` 로 브라우저에 실려 나감 |
| **networks** | `Access-Control-Allow-Origin: *` — 호출자가 누구든 상관없음 |
| **tools** | 툴 실행이 없으니 해당 없음 |
| **files** | 파일 접근이 없으니 해당 없음 |

네 축 중 실제로 쓰이는 두 축이 둘 다 비어 있었다. 이건 그 팀이 게을렀다는 얘기가 아니다. **그 층 자체를 세우지 않았다**는 얘기고, 해커톤 일정 안에서 그건 지극히 정상이다. 요점은 그 층이 "나중에 여유 있으면 붙이는 보안 옵션"이 아니라 **별도의 층**이라는 것 — NVIDIA 가 제품을 아예 두 개 이름으로 쪼개서 파는 것도 그래서다.

같은 페이지의 다른 문장도 이 분리를 반복한다.

> Each blueprint includes NVIDIA Agent Toolkit components such as NVIDIA Nemotron and other frontier models, NVIDIA NeMo for specialization and optimization, and **NVIDIA OpenShell for runtime policy controls.**

모델, 특화, **런타임 정책 통제** — 셋이 나란히 열거된다. 같은 상자에 들어가지만 같은 물건이 아니다.

## 3. 그래서 DLI 코스

NVIDIA 자신의 NemoClaw FAQ 가 위의 "NemoClaw 와 OpenShell 의 차이" 답변 바로 아래에 이렇게 붙여놨다.

> Learn the difference with a self-paced workshop on how to build and configure a safer autonomous agent with NemoClaw and Nemotron.

그 self-paced workshop 이 이거다.

**Securing Agents with NemoClaw and OpenShell** — <https://learn.nvidia.com/courses/course-detail?course_id=course-v1:DLI+S-FX-43+V1>

강의 카탈로그 상세(시간·가격·선수과목)는 페이지가 자바스크립트로 그려서 본문 텍스트로 확인이 안 됐다. **그래서 이 글에는 안 적는다** — 링크를 열어서 직접 보는 쪽이 맞다. 내가 텍스트로 확인한 건 코스 제목과 코스 ID(`course-v1:DLI+S-FX-43+V1`), 그리고 NVIDIA 제품 페이지가 이걸 self-paced workshop 으로 안내한다는 사실까지다.

덧붙이면, 아침 글에서 본 그 리포의 `docs/TROUBLESHOOTING.md` 가 고생한 대상이 바로 이 NemoClaw 설치였다. 이슈 [#12010](https://github.com/NVIDIA/NemoClaw/issues/12010)(Docker Engine 27 seed user), 이슈 [#11963](https://github.com/NVIDIA/NemoClaw/issues/11963)(OpenShell 대시보드 포워드 타임아웃, 확인 시점 기준 열려 있음). **런타임 통제층을 세우는 건 아직 매끄럽지 않다.** 이 글이 "그러니 OpenShell 붙이면 끝"이라고 말하려는 게 아닌 이유이기도 하다.

## 4. 공정하게 — 이건 벤더 1차 자료다

위 인용은 전부 NVIDIA 가 자기 제품에 대해 쓴 글이다. 그래서 다음을 구분해야 한다.

- **사실로 받아도 되는 것**: 제품의 구성·경계 정의. "OpenShell 이 통제하는 축은 파일·네트워크·자격증명·툴이다"는 제품이 스스로 정한 범위라 다툴 여지가 없다.
- **벤더 주장으로 라벨을 붙여야 하는 것**: 같은 페이지에 있는 "Cadence 가 RTL 검증을 몇 주에서 몇 시간으로 줄였다" 같은 성과. 재현 조건·기준선이 텍스트에 없어 검증이 안 된다. **여기서는 인용만 하고 근거로 쓰지 않는다.**
- **부재를 밝혀야 하는 것**: OpenShell 류 런타임 샌드박스를 쓴 쪽과 안 쓴 쪽을 비교한 **중립 제3자 측정은 찾지 못했다.** "런타임 통제가 실제로 사고를 몇 % 줄이는가"에 대한 숫자는 이 글에 없다.

즉 이 글이 주장하는 건 효과 크기가 아니라 **구조**다. 능력을 얻는 곳과 권한을 제한하는 곳은 다른 층이고, 전자만 해도 데모는 돌아가지만 후자는 저절로 따라오지 않는다.

## 마무리

아침 글의 문장을 다시 쓰면 이렇게 된다.

**build.nvidia.com 에서 얻는 건 에이전트가 할 수 있는 일이다. 에이전트가 하면 안 되는 일은 그 주소에 없다.** 그건 런타임에서 정하는 것이고, NVIDIA 는 그걸 OpenShell 이라는 별도 이름으로 부른다.

작은 프로젝트에 OpenShell 을 통째로 들이라는 얘기가 아니다. 아침 리포의 경우엔 이미 `backend.py` 라는 자기 서버가 있었고, 거기서 system 프롬프트를 서버 소유로 바꾸고 CORS 를 도메인으로 좁히는 것만으로 두 축이 채워진다. **중요한 건 도구 이름이 아니라, 그 층이 존재해야 한다는 자각이다.** 그리고 그 자각이 있으면 코드 몇 줄이고, 없으면 영영 안 붙는다.

---

## References

- [NVIDIA NIM APIs — build.nvidia.com](https://build.nvidia.com/) — 무료 추론 엔드포인트, 모델 카탈로그, Agentic Skills (2026-09-20 확인)
- [Securing Agents with NemoClaw and OpenShell — NVIDIA DLI, `course-v1:DLI+S-FX-43+V1`](https://learn.nvidia.com/courses/course-detail?course_id=course-v1:DLI+S-FX-43+V1)
- [NVIDIA NemoClaw 제품 페이지](https://www.nvidia.com/en-us/ai/nemoclaw/) — NemoClaw/OpenShell 경계 정의, Agent Toolkit 구성, self-paced workshop 안내
- [NVIDIA/NemoClaw 이슈 #12010](https://github.com/NVIDIA/NemoClaw/issues/12010) · [이슈 #11963](https://github.com/NVIDIA/NemoClaw/issues/11963)
- 앞선 글: [해커톤 에이전트 챗봇 — 검색은 서버로 옮겼는데, 정책은 브라우저에 남았다](https://myoungsoo7.github.io/2026/09/20/agent-chatbot-rag-where-the-policy-lives/)
