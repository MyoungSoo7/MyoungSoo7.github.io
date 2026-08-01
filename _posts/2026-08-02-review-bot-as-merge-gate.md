---
layout: post
title: "머지 게이트가 CI가 아니라 LLM 리뷰 봇일 때 — 리뷰 루프를 재현 가능하게 만든 이야기"
date: 2026-08-02 05:55:00 +0900
categories: [Engineering, Tooling, LLM]
tags: [Code Review, LLM-as-a-Judge, CI, pytest, Automation]
---

CI 가 머지를 막으면 고칠 방법은 명확하다. 로그를 보고, 실패한 테스트를 로컬에서 재현하고, 고치면 된다. 실패는 결정적(deterministic)이고, 재현은 무료다.

그런데 머지를 막는 게 **LLM 리뷰 봇**이면 이야기가 완전히 달라진다. 봇의 판정은 매번 새로 계산되고, "무엇이 blocker 인지"는 룰북에 적혀 있지 않으며, 같은 코드에 같은 리뷰가 두 번 온다는 보장도 없다. 그러면 개발자는 이런 루프에 갇힌다.

> 고친다 → 푸시한다 → 20분 뒤 봇이 _다른_ 지적을 한다 → 고친다 → 또 다른 지적 → …

이 글은 그 루프를 손으로 도는 대신 도구로 만든 이야기다. 도구 이름은 `ouropr`, 대상은 [Q00/ouroboros](https://github.com/Q00/ouroboros) 라는 공개 레포이고, 그 레포의 머지 게이트는 CI 가 아니라 `ouroboros-agent[bot]` 이라는 리뷰 봇이다.

---

## 0. 전제: "봇은 스타일 지적을 하지 않는다"

먼저 관측부터. 이 봇의 리뷰 234건을 훑어 보면, **blocker 가 하나도 없는 리뷰는 45건**이었다. 대략 19%. 즉 **한 번에 통과할 확률이 5분의 1**이라는 뜻이다.

> ⚠️ 이 수치는 내가 한 레포 하나에서 직접 센 값이다. 벤더 발표 수치도, 제3자 벤치마크도 아니다. 다른 레포·다른 리뷰 봇에 일반화되지 않는다.

그리고 blocker 로 잡히는 것들엔 뚜렷한 결이 있었다. 스타일·문서 불일치·"이것도 방어하면 좋겠다" 류는 **막지 않는다.** 막는 건 딱 세 부류였다.

1. **신뢰할 수 없는 모델 출력이 권위 있는 상태(authoritative state)가 되는 경로**
2. **fail-closed 여야 할 곳이 fail-open 인 구멍**
3. **기존 테스트가 실제로 깨지는 것**

봇이 반복해서 쓰는 표현이 있다. _"can still convert malformed model output into evolution state or verification evidence."_ 이 한 문장이 사실상 이 봇의 룰북이다.

이걸 알고 나면 전략이 정해진다. **봇이 볼 것을 봇보다 먼저 보고, 봇이 요구할 증거를 미리 만들어 두는 것.** 도구는 그 두 가지만 한다.

---

## 1. 전체 구조: 한 라운드가 도는 모양

`ouropr` 는 파이썬 단일 파일(약 1,000줄)에 `profile.json` 하나를 물린 CLI 다. 라운드 하나는 이렇게 흐른다.

```
ouropr status   →  지금 PR 이 어떤 상태인가 (봇 판정 + CI + 미해결 blocker)
ouropr audit    →  봇 흉내를 내서 "다음 blocker" 를 미리 찾는다  (5개 lens 병렬)
   (사람이 고치고 커밋)
ouropr gate     →  A1~A10 을 다 통과해야 푸시 허용
ouropr push     →  게이트 green 일 때만
ouropr comment  →  봇에게 증거를 붙여 재리뷰 요청
ouropr learn    →  이번 라운드에서 배운 것을 다음 audit 프롬프트에 접어 넣는다
```

핵심은 **`gate` 가 `push` 앞을 막는다**는 것이다. 게이트가 빨간불이면 푸시 명령 자체가 거부된다. 리뷰 봇에게 물어보는 건 라운드당 20분짜리 비용이라서, 그 20분을 쓰기 전에 로컬에서 확실히 걸러내야 한다.

`profile.json` 은 레포마다 다른 것들만 담는다 — 대상 레포, 워크트리 경로, 파이썬, 리뷰어 봇 계정명, 테스트 명령, 커밋 제목 정규식, 그리고 **머지 프로토콜**:

```json
"merge_protocol": "Human maintainer merges. Never self-merge on green CI.
                   Human APPROVED reviews do not override the bot."
```

마지막 문장이 중요하다. 사람이 APPROVE 를 눌러도 봇이 막고 있으면 머지 대상이 아니다. 도구는 이걸 프로필에 명시적으로 박아 두고, 스스로 머지하지 않는다.

---

## 2. `audit` — 봇을 먼저 흉내 내기

가장 비싼 부분이자 가장 효과가 큰 부분이다. `audit` 은 서브 에이전트를 띄워서 **리뷰 봇 역할을 대신 시킨다.** 프롬프트에 세 가지를 주입한다.

**(a) 역엔지니어링한 룰북.** 위의 3부류 + "이건 blocker 가 아니다" 목록. 애매하면 봇 기준으로 판정하도록.

**(b) 이미 이 레포에서 재현된 결함 클래스 목록** (`knowledge/invariants.md`). 지금 14개가 쌓여 있다. 이름만 옮기면 이런 것들이다 — _Fragment promotion out of malformed syntax_, _Memoized rejection_, _Vacuous regressions_, _Partial gate on one exit_, _Claims outrunning evidence_, _A fix lost in the rewrite that followed it_. 각 항목은 인스턴스가 아니라 **클래스**로 적혀 있다. 파일명·심볼·PR 번호를 다 벗겨서, 식별자가 전혀 겹치지 않는 코드에도 대볼 수 있게.

**(c) lens 하나.** 5개를 병렬로 돌린다.

| lens        | 보는 것                                                                                       |
| ----------- | --------------------------------------------------------------------------------------------- |
| `extractor` | 파싱 경계 — 깨진/잘린 텍스트가 그래도 payload 를 뱉는 모든 경로                               |
| `state`     | 모델 텍스트가 영속 상태가 되는 파서 — 부분적으로 깨진 응답이 "조각으로" 수용되는가            |
| `evidence`  | 검증 경로 — 모델이 준 값이 PASS 를 날조할 수 있는가, 증거 부재가 fail-closed 인가             |
| `exits`     | **이번 PR 이 추가한 가드의 폭발 반경** — 같은 결과를 내는 _다른_ 분기들이 그대로 열려 있는가  |
| `tests`     | 봇 기준의 테스트 품질 — private 메서드에서만 증명된 보장, 되돌려도 통과하는 vacuous assertion |

`exits` lens 는 실전에서 가장 자주 먹혔다. 이 봇이 제일 좋아하는 blocker 패턴이 **"한 분기만 막고 형제 분기는 열어 둔 부분 수정"** 이기 때문이다. 봇은 그걸 미완성 수정으로 읽고 재차단한다.

그리고 프롬프트에 하드하게 박아 둔 규칙이 하나 있다.

> 모든 후보 결함에 대해 **공개 소비 경로(public consumer path)로 실제로 구동하는 probe 를 작성하라.** 추측은 가치가 없다. 단순히 payload 가 유실되거나 우아하게 폴백하는 건 blocking 이 아니다 — 그렇게 말하고 등급을 내려라. 아무것도 없으면 "없다"고 말하라. **결함을 만들어내지 마라.**

리뷰 봇 자신이 매 라운드 직접 probe 를 짜서 재현해 보고 막기 때문에, 재현되지 않는 지적은 봇도 안 하고 우리도 할 필요가 없다.

---

## 3. `gate` — A1~A10, 재현이 없으면 푸시도 없다

게이트는 10개 항목이다. 하나라도 실패하면 `push` 가 거부된다.

|     | 검사                                                                                                                            | 왜                                    |
| --- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| A1  | 변경 파일이 리뷰 범위 안에 있는가                                                                                               | 범위 밖 파일은 그 자체로 blocker 사유 |
| A2  | 새 테스트가 실제로 추가됐는가                                                                                                   |                                       |
| A3  | **새 테스트가 baseline 에서 FAIL 하는가**                                                                                       | ← 아래 참조                           |
| A4  | 수정본에서는 PASS 하는가                                                                                                        |                                       |
| A5  | 타깃 스위트                                                                                                                     |                                       |
| A6  | 전체 스위트 (CI 와 동일한 호출)                                                                                                 |                                       |
| A7  | 변경 파일에 [ruff](https://docs.astral.sh/ruff/) + [mypy](https://mypy.readthedocs.io/en/stable/)                               |                                       |
| A8  | 워킹트리 clean · [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) 준수 · fast-forward (force-push 불필요) |                                       |
| A9  | 과거에 이 PR 을 막았던 모든 입력이 여전히 닫히는가                                                                              |                                       |
| A10 | 적대적 audit 이 **바로 이 커밋**을 커버하는가                                                                                   |                                       |

**A3 가 이 게이트의 심장이다.** 하는 일이 좀 과격하다. 변경된 소스 파일들을 잠시 baseline 버전으로 **되돌려 놓고**, 새로 추가한 테스트만 골라 돌린다. 여기서 테스트가 통과하면 그 테스트는 아무것도 증명하지 못한다 — 수정 없이도 초록불이니까. 그 다음 원본을 복구한다(`finally` 블록으로).

여기에 한 겹이 더 있다. 전체 실행 요약만 보면 "새 케이스가 **전부** baseline 에서 실패"와 "그 중 **하나만** 실패"를 구분할 수 없다. 그래서 [pytest 노드 단위](https://docs.pytest.org/en/stable/how-to/usage.html)로 다시 돌려서 개별 outcome 을 세고, PR 본문에는 **그 숫자**를 인용하게 한다. baseline 에서 통과해 버린 케이스는 이름을 하나씩 찍어 주고 이렇게 말한다.

> 이건 과잉거부 방지 가드이거나(그럼 PR 본문에 그렇게 쓰라), 애초에 실패할 수 없는 케이스다(그럼 고쳐라).

---

## 4. `corpus` / `replay` — 리뷰 봇의 probe 를 훔쳐서 회귀 스위트로

이게 개인적으로 가장 마음에 드는 부분이다.

리뷰 봇은 blocker 를 쓸 때 **자기가 무슨 입력으로 재현했는지를 그대로 적는다.** 깨진 JSON 조각, 잘린 컨테이너, 프롬프트 예시가 섞인 응답 같은 것들이. 그건 그냥 리뷰 코멘트가 아니라 **"이 PR 을 실제로 한 번 막은 적 있는 입력"** 이다. 회귀 코퍼스로서 이보다 값진 게 없다.

`ouropr corpus` 는 [GitHub REST 의 PR 리뷰 목록 API](https://docs.github.com/en/rest/pulls/reviews) 로 봇의 리뷰 본문을 다 긁어서, Blockers 표의 코드 스팬 중 JSON 구분자를 포함한 것만 추출해 `knowledge/corpus.jsonl` 에 쌓는다. 지금 12건.

파싱에서 한 번 데였다. 봇은 probe 입력을 **백틱 1개짜리 스팬 안에 펜스 블록을 통째로 넣어서** 쓰는 습관이 있다. `` `- ```json ... ``` Actual: {...}` `` 같은 모양. 순진하게 ``[^`]*`` 로 쪼개면 입력 하나가 여러 조각으로 찢어지고, **그 조각 하나하나가 replay 에서 전부 leak 으로 보인다.** 그래서 백틱 런을 길이로 페어링하도록 고쳐야 했다 — N개짜리 런은 다음에 나오는 _정확히 N개짜리_ 런과 짝짓는다.

그리고 각 입력은 **자기 레이어에서만** 의미가 있다. extractor 가 정당하게 반환한 payload 를, 그걸 읽는 파서는 거부해야 할 수 있다. 전부 extractor 에서 단언하면 false positive 와 false negative 를 동시에 만든다. 그래서 레코드마다 `target` (어느 소비자에 쏠 입력인지)을 붙인다.

마지막 함정 하나 더. **모든 입력이 "거부되어야" 하는 건 아니다.** 어떤 건 _미끼 payload 가 진짜를 이겨서_ 막혔던 거고, 고쳐진 동작은 "진짜를 반환하는 것"이다. 여기에 "거부"만 단언하면 **방금 고친 걸 정확히 다시 부순다.** 그래서 `expect: closed` 외에 `expect_value` 를 따로 둔다.

---

## 5. `learn` / `calibrate` — 루프가 실제로 복리로 도는가

라운드가 끝나면 `learn` 이 결과를 `knowledge/rounds.jsonl` 에 남기고, 봇이 잡은 blocker 를 **재사용 가능한 결함 클래스 한 문단**으로 증류해서 `invariants.md` 에 붙인다. 다음 라운드의 audit 프롬프트가 그걸 먼저 읽는다.

이걸 자동화한 이유는 단순하다. 손으로 `--invariant` 를 적게 두면, **적어야 할 때 가장 안 적힌다** — 라운드가 막 망한 직후니까.

증류 출력은 그냥 믿지 않는다. 서브 세션 stdout 에는 환경 공지 같은 게 섞여 들어올 수 있고, 실제로 첫 실행 때 그런 문장이 `invariants.md` 에 그대로 박혔다. 그래서 `<invariant>` 태그로 감싸게 하고, 태그 밖은 버리고, 900자 제한과 시작 형식(`**이름.**`)을 검사해서 통과 못 하면 **추가하지 않는다**.

`calibrate` 는 이 루프가 실제로 작동하는지를 잰다. 봇이 막은 지점을 우리 audit 이 이미 짚었었나?

- 짚었는데 안 고쳤다 → **triage 실패**
- 아예 못 봤다 → **recall 실패**

둘은 고치는 방향이 정반대라서 따로 센다. 그리고 여기 미묘한 함정이 있다. **audit 이 그 리뷰보다 먼저 존재했을 때만 크레딧을 준다.** 안 그러면 blocker 를 보고 나서 쓴 audit 이 "그걸 예측했다"고 스스로에게 점수를 준다. 실제로 초기 버전이 그렇게 과대평가하고 있었다.

---

## 6. 게이트가 자기 자신을 세 번 잡았다

PR #1828 라운드에서 게이트가 잡은 것 중 셋은 **대상 레포의 결함이 아니라 `ouropr` 자신의 결함**이었다.

1. **A10 은 애초에 통과할 수 없었다.** 미해결 BLOCKING 행을 찾는 매칭이 앵커되지 않아서, 해결 표시된 행까지 미해결로 셌다.
2. **A9 가 가짜 회귀를 냈다.** 위에서 말한 그 케이스 — 코퍼스 항목이 `expect=closed` 로 잘못 붙어 있었는데, 고쳐진 동작은 진짜 payload 를 반환하는 것이었다.
3. **`calibrate` 가 recall 을 과대평가했다.** 사후에 쓴 audit 에 크레딧을 줬다.

라운드 기록에 남긴 메모는 이거다.

> round 1 REQUEST_CHANGES: `_qa_passed` 만 가드했고 converged + max-gen 형제 exit 은 열려 있었다. **근본 실패는 프로세스 쪽** — audit 도 gate 도 아예 돌리지 않고 푸시했다.

라운드 2는 APPROVE 였고, 차이는 단 하나였다. **푸시 전에 audit 을 돌렸다.** 5개 lens 전부가 같은 fail-open 을 짚었고, 봇에게 물어보기 전에 닫았다.

---

## 7. 일부러 안 하는 것들

- **머지하지 않는다.** 사람 메인테이너가 머지한다. CI 초록불로 self-merge 하지 않는다.
- **force-push 하지 않는다.** 게이트가 fast-forward 여부를 검사하는 이유이기도 하다. 리뷰 봇은 커밋 히스토리를 참조하는데, 히스토리를 갈아엎으면 이전 라운드의 증거가 같이 사라진다.
- **대상 레포의 소스를 audit 이 수정하지 못한다.** audit 은 read-only 다. probe 스크립트는 스크래치 디렉터리에만 쓴다.
- **`ouroboros auto` 위에 얹지 않았다.** 대상 레포 자체가 에이전트 루프 프레임워크지만, 리뷰 루프 드라이버는 그것과 독립이어야 한다. 검증 대상과 검증 도구가 같은 코드를 공유하면 둘이 같이 틀린다.

---

## 8. 한계

정직하게 적어 둔다.

- **n 이 작다.** 라운드 기록은 지금 2건, 코퍼스 12건, invariant 14건이다. "19% 원샷 통과율"은 234건 리뷰에서 센 값이지만 **레포 하나, 봇 하나**의 값이다.
- **룰북은 역엔지니어링이다.** 봇의 실제 프롬프트를 본 적 없다. 관측된 행동에서 추론한 것이고, 봇이 바뀌면 틀린다.
- **LLM 판정은 결정적이지 않다.** 같은 diff 에 같은 판정이 다시 온다는 보장이 없다. LLM 을 판정자로 쓸 때의 위치 편향·장황함 편향·자기선호 편향은 Zheng 등(NeurIPS 2023)이 정량적으로 보고했다 — GPT-4 조차 순서를 바꿨을 때 65% 에서만 일관된 판정을 냈다.[^1] 그래서 이 도구의 목표는 "봇을 예측하는 것"이 아니라 **"봇이 무엇을 물어보든 이미 답이 있게 만드는 것"** 이다. A3(재현 증명)와 A9(과거 blocker 재생)가 확률적 판정자 앞에서 결정적으로 남는 유일한 부분이다.
- **비용이 든다.** audit 한 번에 lens 5개짜리 서브 에이전트가 돈다. 라운드 20분을 아끼려고 쓰는 비용이라 나한텐 남는 장사지만, 공짜는 아니다.

---

## 정리

리뷰어가 사람이든 봇이든, 좋은 PR 의 조건은 안 변한다. **범위를 지키고, 재현되는 증거를 붙이고, 고친 걸 되돌리면 실제로 깨지는 테스트를 넣는 것.**

달라지는 건 하나다. 사람 리뷰어는 그걸 안 지켜도 봐줄 수 있지만, **봇은 안 봐준다.** 그래서 그 조건들을 문서가 아니라 **푸시를 막는 게이트**로 만들 수밖에 없었다. 그러고 나니 부수 효과가 있었다 — 그 게이트는 봇이 없는 레포에서도 그대로 유용하다.

---

## References

- Zheng, L., Chiang, W.-L., Sheng, Y., et al. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." _NeurIPS 2023 Datasets and Benchmarks Track._ [proceedings.neurips.cc](https://proceedings.neurips.cc/paper_files/paper/2023/file/91f18a1287b398d378ef22505bf41832-Paper-Datasets_and_Benchmarks.pdf) · [arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
- GitHub Docs — [REST API: Pull request reviews](https://docs.github.com/en/rest/pulls/reviews)
- GitHub Docs — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- pytest — [How to invoke pytest: specifying which tests to run](https://docs.pytest.org/en/stable/how-to/usage.html)
- [Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)
- Ruff — [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) · mypy — [mypy.readthedocs.io](https://mypy.readthedocs.io/en/stable/)
- 대상 레포: [Q00/ouroboros](https://github.com/Q00/ouroboros) (public)

> **출처 등급에 대해:** 위 References 는 공식 문서와 동료심사 논문이다. 반면 본문의 수치(리뷰 234건 중 blocker 0 이 45건, invariant 14개, 코퍼스 12건, 라운드 2건)와 리뷰 봇의 룰북 재구성은 **내가 한 레포에서 직접 측정·추론한 값**이며 중립 제3자 검증은 없다. 도구 `ouropr` 자체는 개인용 비공개 도구라 링크할 공개 저장소가 없다.

[^1]: Zheng et al., Table 2 — 기본 프롬프트에서 두 답변의 순서를 바꿨을 때 판정이 유지된 비율. Claude-v1 23.8%, GPT-3.5 46.2%, GPT-4 65.0%.
