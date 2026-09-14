---
layout: post
title: "요약이 원본보다 2.4배 컸다 — LLM 에게 시키면 안 되는 일 한 가지"
date: 2026-09-15 08:18:53 +0900
categories: [infra, llm]
tags: [llm, cost, rag, cache, openviking, kubernetes]
---

어제 [제미나이 API 청구서 ₩183,711 의 근본원인](https://myoungsoo7.github.io/2026/09/14/gemini-api-bill-root-cause-openviking/)을 썼다.
거기까지는 "누가, 얼마나 자주 썼나" 였다. 남은 질문이 하나 있었다.

> **그래서 그 요약은 대체 무엇을 요약하고 있었나.**

오늘 아침에 그걸 실물로 열어봤다. 결론부터 적는다. 요약 대상 원본은 **1,768바이트**였고,
LLM 이 만들어낸 요약은 **4,258바이트**였다. 요약이 원본보다 2.4배 크다.

---

## 1. 요약 대상 — 봇 하트비트 7개

문제의 디렉터리를 그대로 뜬 것이다.

```
$ ls -la .../agent/default/memories/bus
-rw-r--r-- 256   .abstract.md      <- LLM 산출물
-rw-r--r-- 4002  .overview.md      <- LLM 산출물
-rw-r--r-- 162   bus-lemuel.md
-rw-r--r-- 161   bus-ilwon.md
-rw-r--r-- 163   bus-solomon.md
-rw-r--r-- 162   bus-louise.md
-rw-r--r-- 161   bus-david.md
-rw-r--r-- 162   bus-isagal.md
-rw-r--r-- 797   bus-mac.md
                 ─────────────
                 원본 합계 1,768 B
```

`bus-david.md` 의 **전체** 내용이다. 발췌가 아니라 파일 전부다.

```json
{"host":"david","ts":1789382121,"agents":[
 {"agent":"(봇)","state":"idle","ts":1789382101,
  "task":"세션 떠 있음 · 최근 프롬프트 없음"}]}
```

에이전트 하트비트다. "어느 기계의 봇이 지금 놀고 있나." 7대가 1분마다 자기 파일 하나를
덮어쓴다. 사람이 읽는 문서가 아니고, 코드도 아니고, 대화 로그도 아니다.
**이미 구조화가 끝난 상태 값**이다.

## 2. 요약 산출물 — 실제로 나온 문장

`.overview.md` 에서 잘라온 것이다. 손대지 않았다.

```
- bus-lemuel.md: This document is a status report for the Lemuel host,
  detailing its current idle state with no recent prompts. It includes
  agent information, focusing on the Lemuel host's operational status.
  The target audience is system administrators or users monitoring the
  Lemuel host's performance. No prerequisite knowledge is required.
  Key concepts include host status and agent state.
```

162바이트짜리 JSON 한 줄을 읽는 데 **선수지식이 필요한지**를 LLM 이 판정해 줬다.
그리고 같은 판정을 파일 7개에 대해 각각 반복했다. `No prerequisite knowledge is
required.` 라는 문장이 한 파일 안에 일곱 번 들어 있다.

| | 바이트 |
| --- | ---: |
| 원본 7개 합계 | 1,768 |
| `.overview.md` | 4,002 |
| `.abstract.md` | 256 |
| **산출물 합계** | **4,258** |
| 비율 | **2.41배** |

압축이 아니라 팽창이다. 요약의 정의상 이 시점에서 이미 실패다.

## 3. 캐시는 왜 못 막았나

라이브러리가 캐시를 안 만든 게 아니다. 두 층이나 있다. 설치본(v0.3.12)을 직접 읽었다.

**(a) 파일 단위 캐시** — `storage/queuefs/semantic_processor.py`

```python
for idx, file_path in enumerate(file_paths):
    file_name = file_path.split("/")[-1]
    if file_path not in changed_files and file_name in existing_summaries:
        file_summaries[idx] = {"name": file_name, "summary": existing_summaries[file_name]}
    else:
        pending_indices.append((idx, file_path))
```

바뀐 파일만 다시 요약한다. 제대로 만들어져 있다.

**(b) 디렉터리 단위 증분** — `storage/queuefs/semantic_dag.py` 의 `_check_dir_children_changed`

```python
for current_file in current_files:
    if self._file_change_status.get(current_file, True):
        return True          # 하나라도 바뀌면 "바뀜"
```

그리고 호출부는 이렇다.

```python
if not children_changed:
    need_vectorize = False
    overview, abstract = await self._read_existing_overview_abstract(dir_uri)
if overview is None or abstract is None:
    ...
    overview = await self._processor._generate_overview(...)   # LLM
```

여기가 핵심이다. **하트비트 디렉터리는 "하나라도 바뀌는 것"이 존재 이유다.**
그러니 (b)는 매번 True 다 — 설계상 도달할 수 없는 캐시다. (a)가 7개 중 6개를
아껴줘도, `overview` 전체 재생성과 재임베딩은 **매 쓰기마다** 일어난다.

즉 쓰기 1회의 비용 바닥이 0이 아니다. 최소 LLM 2콜(바뀐 파일 요약 1 + overview 1)에
임베딩이 붙는다. 실측 평균은 그보다 나빴다 — LLM 호출 22,664회 ÷ 쓰기 2,833회 ≈
**쓰기당 8회**.

그래서 비용이 **데이터 크기가 아니라 쓰기 빈도**를 따라갔다. 1,768바이트가 하루
258회의 요약 사이클이 됐고, 그게 한 달 ₩183,711 이 됐다. 쓰기 1회당 약 ₩65 다.
(청구액 ÷ 실측 쓰기 횟수로 내가 나눈 값이고, 벤더가 준 수치가 아니다.)

## 4. "이 디렉터리는 요약하지 마" 스위치는 없었다

그럼 끄면 되지 않나 — 찾아봤다.

`skip_vectorization` 플래그가 `semantic_msg.py` 에 있다. 그런데 두 가지가 걸린다.

1. 이름 그대로 **임베딩만** 건너뛴다. 비싼 쪽인 LLM 요약 생성은 그대로 돈다.
2. 유일한 쓰기 경로인 `storage/content_write.py` 가 두 자리에서 `skip_vectorization=False`
   를 **하드코딩**한다. 공개 쓰기 API 로는 켤 방법이 없다.

경로 기반 제외 설정도 없다. `queuefs` 가 읽는 설정 키를 전수로 뽑으면 이렇다.

```
account_id  added  agent_id  changes  context_type  deleted  id
is_code_repo  level  lifecycle_lock_handle_id  modified  name
recursive  role  semantic_msg_id  size  skip_vectorization
summary  target_uri  telemetry_id  uri  user  user_id
```

"이 경로는 요약 대상에서 빼라"에 해당하는 키가 없다.

라이브러리를 탓할 일은 아니다. 이건 **문서·지식을 담으라고 만든 스토어**다.
거기에 초 단위로 갱신되는 하트비트를 넣은 내 설계가 틀렸다.

## 5. 모델만 바꿔서는 안 풀린다

비용은 로컬 Ollama(`qwen2.5:3b`)로 내려서 0이 됐다. 그런데 지금 `.abstract.md` 가
이렇게 생겼다.

```
1. **Title** (H1): bus
2. **Brief Description** (plain text paragraph, 50-150 words):
- This directory contains status reports for various hosts, including
  Lemuel, Louise, Isagal, Mac, David, Ilwon, and Solomon. ...
```

프롬프트의 **지시문 틀을 그대로 베껴 출력**한다. 내용은 맞다 — 노드 이름도 idle
상태도 정확히 짚었다. 형식만 깨졌다.

그게 왜 치명적이냐면, 앞의 (a) 캐시가 `_parse_overview_md(old_overview)` 로
**직전 overview 를 다시 파싱해서** 동작하기 때문이다. 형식이 깨지면 파싱 결과가
0건이 되고, 그러면 7개 전부가 pending 이 된다. 로그가 정확히 그렇게 찍혔다.

```
Parsed 0 existing summaries from overview.md
Generating summaries for 7 changed files (reused 0 cached)
```

Gemini 로 돌 때는 `Parsed 7` → `reused 6` 이 찍혔다. 같은 코드, 같은 데이터,
모델만 다르다.

**작은 모델을 붙일 때 먼저 깨지는 건 지식이 아니라 형식 준수다.** 그리고 그 결과가
캐시 무력화라면 싼 모델이 느린 모델이 된다 — 쓰기 1회가 36초에서 **4분 37초**가 됐다.
(CPU 추론 실측 5.1 tok/s, `OLLAMA_NUM_PARALLEL=1` 이라 7개 요약이 줄을 선다.)

## 6. 그래서 규칙 하나

> **이미 구조화된 데이터를 LLM 에게 산문으로 요약시키지 말 것.**

넣기 전에 볼 것 네 가지.

- **원본이 JSON·CSV·메트릭인가** → 답은 파서다. LLM 이 아니다.
- **산출물을 사람이 읽는가** → 아무도 안 읽으면 만들지 마라. 나도 봇 상태는 원본
  JSON 을 보지 요약을 보지 않았다.
- **산출물이 원본보다 커지는가** → 그건 요약이 아니다.
- **갱신 주기가 초·분 단위인가** → 요약 캐시가 갱신 주기를 못 이긴다.

특히 마지막. RAG·에이전트 메모리 계열은 대체로 "문서는 가끔 바뀐다"를 전제로 캐시를
설계한다. 그 전제를 깨는 데이터(하트비트, 큐 깊이, 센서 값)를 같은 스토어에 넣으면
캐시는 영구 miss 다. 비용이 데이터 크기가 아니라 **쓰기 빈도**에 비례하기 시작하는
지점이 정확히 여기다.

## 남는 것

- 하트비트를 쓰던 7대는 전부 꺼둔 상태다. 다시 켠다면 이 경로는 메모리 스토어 밖
  (평범한 파일이나 Redis)으로 뺀다. 요약이 필요 없는 데이터니까.
- 임베딩은 아직 Gemini 다. 3072차원 컬렉션을 유지해야 해서 손대지 않았다. 쓰기가
  멈춰 있어 지금은 과금이 없지만, **구조적으로는 아직 안 막혔다.**
- 예산 하드캡은 여전히 없다. 그게 다음 숙제다.

---

### References

- OpenViking v0.3.12 소스 — [github.com/volcengine/OpenViking](https://github.com/volcengine/OpenViking) (AGPL-3.0).
  본문에 인용한 `semantic_processor.py` · `semantic_dag.py` · `content_write.py` ·
  `semantic_msg.py` 코드와 설정 키 목록은 운영 중인 컨테이너 이미지
  `ghcr.io/volcengine/openviking:v0.3.12` 안의 설치본을 직접 읽은 것이다.
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) — 공식 가격표.
  모델별 과금 행의 제목이 문자 그대로 "Output price (including thinking tokens)" 이다.
- 선행 글 — [제미나이 API 청구서 ₩183,711 — 근본원인을 찾아 막기까지](https://myoungsoo7.github.io/2026/09/14/gemini-api-bill-root-cause-openviking/)

**근거의 한계.** 바이트 수·로그 문자열·소스 라인은 전부 운영 환경에서 직접 뜬 1차
관측이다. 반면 "쓰기당 ₩65", "쓰기당 LLM 8회" 는 청구 총액과 실측 횟수를 내가 나눈
값이라 모델별 단가 분해가 아니다. 그리고 여기 적은 캐시 동작은 v0.3.12 기준이며,
상류에서 바뀔 수 있다.
