---
layout: post
title: "머신러닝은 지식을 굽고, 위키는 지식을 고친다 — 에이전트가 그 사이에서 하는 일"
date: 2026-08-11 17:05:00 +0900
categories: [AI, Agent]
tags: [머신러닝, 에이전트, LLM위키, RAG, 컨텍스트엔지니어링, 지식그래프, 하네스]
---

"머신러닝과 에이전트와 LLM위키는 무슨 상관인가."

층위가 다른 세 단어처럼 들린다. 하나는 학습 알고리즘, 하나는 실행 구조, 하나는 마크다운 파일 더미다. 그런데 셋은 같은 문제를 푼다. **모델이 모르는 것을 어떻게 알게 하는가.** 다르게 푸는 게 아니라 _서로 다른 갱신 주기로_ 푼다.

이 글은 그 분업을 1차 문헌으로 정리하고, 그다음에 내가 실제로 굴리고 있는 LLM-Wiki(`~/wiki`) 71개 파일을 직접 세어서 그 이론이 어디서 지켜지고 어디서 깨졌는지 확인한다. 측정 스크립트는 글 끝에 그대로 붙였다.

---

## 1. 같은 문제, 세 개의 갱신 주기

| 층                           | 지식이 사는 곳   | 갱신 수단        | 갱신 비용 | 출처 추적        |
| ---------------------------- | ---------------- | ---------------- | --------- | ---------------- |
| 머신러닝 (사전학습·파인튜닝) | 모델 파라미터    | 경사하강         | 재학습    | 불가             |
| LLM위키                      | 저장소의 파일    | 텍스트 편집      | 커밋 1개  | 가능 (경로·해시) |
| 에이전트                     | 지식을 갖지 않음 | 런타임 선택 정책 | 매 턴     | 실행 로그        |

이 구분의 원전은 RAG 논문이다. Lewis 등은 2020년에 파라메트릭 메모리와 비파라메트릭 메모리를 명시적으로 갈라놓았다 — "the parametric memory is a pre-trained seq2seq model and the non-parametric memory is a dense vector index of Wikipedia."[^1]

같은 논문의 결론부에 이 글의 핵심 문장이 있다.

> "we illustrated how the retrieval index can be hot-swapped to update the model without requiring any retraining."[^1]

색인을 갈아 끼우면 재학습 없이 지식이 갱신된다. 위키가 하는 일이 정확히 이것이다. **위키는 재학습의 열등한 대체재가 아니라, 재학습이 감당하지 못하는 변화 속도 구간을 맡는 별도의 저장 장치다.** 어제 클러스터에서 터진 사고는 다음 모델 학습 때까지 기다릴 수 없다.

## 2. 그러면 다 밀어 넣으면 되나 — 아니다

컨텍스트 창이 커졌으니 위키를 통째로 붙이면 되지 않느냐는 말이 나온다. 이건 실험으로 반박된다.

Liu 등은 관련 정보의 *위치*만 바꿔가며 다문서 QA를 측정해 U자 곡선을 찾아냈다. 앞이나 뒤에 있으면 잘 쓰고, 가운데 있으면 급격히 못 쓴다. 절정은 이 대목이다.

> "when relevant information is placed in the middle of its input context, GPT-3.5-Turbo's performance on the multi-document question task is lower than its performance when predicting without any documents (i.e., the closed-book setting; 56.1%)."[^2]

문서를 20–30개 넣어준 쪽이, **아무것도 안 넣어준 쪽보다 못했다.** 같은 논문은 확장 컨텍스트 모델이 반드시 컨텍스트를 더 잘 쓰는 것도 아니라고 덧붙인다.

따라서 지식 저장소의 일차 임무는 모으는 것이 아니다. **무엇을 안 읽을지 정하는 것이다.** 내 위키의 `concepts/knowledge-repo-leverage.md`도 같은 근거로 첫 번째 지렛대를 "검색 범위"로 잡아두었다.

## 3. 에이전트는 그 선택을 실행하는 층이다

Park 등의 Generative Agents는 이 선택 정책을 가장 노골적으로 구현했다. 관찰 원본을 전부 쌓아두는 memory stream이 있고, 그 위에 세 성분으로 점수를 매기는 retrieval이 있고(recency는 감쇠계수 0.995의 지수감쇠, importance는 모델에게 1–10 정수로 직접 물어봄), 최근 사건들의 중요도 합이 임계치 150을 넘으면 reflection이 생성돼 다시 스트림에 들어간다. 저자들은 ablation으로 관찰·계획·반성이 각각 기여함을 보였다.[^3]

이 구조가 내 위키의 디렉터리 배치와 거의 그대로 겹친다.

- `incidents/`, `raw/` = 관찰 원본 (tmux로 캡처된 에이전트 토론 로그, 세션 트랜스크립트)
- `concepts/`, `entities/` = reflection (원본에서 증류된 개념·대상 페이지)
- `index.md` = retrieval 진입점

MemGPT는 여기에 운영체제 은유를 붙였다. main context(물리 메모리)와 external context(디스크)를 나누고, 함수 호출로 그 사이를 페이징한다.[^4] 이 틀에서 보면 `index.md`는 페이지 테이블이다.

벤더 공식 문서도 같은 처방을 쓴다. Anthropic은 2025년 9월 글에서 컨텍스트를 "유한한 주의 예산"으로 규정하고, 사전에 다 넣는 대신 가벼운 식별자만 들고 있다가 런타임에 끌어오는 just-in-time 방식, compaction, 그리고 컨텍스트 밖 파일에 적어두는 structured note-taking을 권한다.[^5]

**여기서 수치의 등급을 갈라야 한다.**

- ② 벤더 1차 벤치마크 (자체 평가셋, 외부 재현 불가): Anthropic은 memory tool과 context editing을 함께 쓰면 내부 에이전틱 검색 평가에서 베이스라인 대비 +39%, context editing 단독으로 +29%, 100턴 웹검색에서 토큰 84% 절감이라고 밝혔다.[^6] 멀티에이전트 구성은 단일 에이전트 대비 +90.2%지만 채팅 대비 토큰을 약 15배 쓴다고 같은 회사가 적었다.[^7]
- ③ 중립 제3자 헤드투헤드: **확인하지 못했다.** 위 숫자들은 "벤더가 자기 평가셋에서 얻었다고 밝힌 값"으로만 읽어야 한다. 방향성의 근거는 되지만 크기의 근거는 되지 못한다.

## 4. 그래서 내 위키를 실제로 재봤다

여기까지는 남의 논문이다. 이론이 내 저장소에서도 성립하는지는 세어봐야 안다.

측정 대상은 `~/wiki`, 커밋 `3c74480`(2026-08-10 16:19 KST), 워킹트리 clean. 측정 시각 2026-08-11 17:00 KST. 아래 숫자는 전부 글 끝의 스크립트로 재현된다.

| 항목                          | 값                 |
| ----------------------------- | ------------------ |
| 마크다운 파일                 | 71                 |
| frontmatter 있음              | 54 (76.1%)         |
| `type` 필드 있음              | 26 (36.6%)         |
| 초판 스키마 7필드 완비        | 26                 |
| frontmatter 아예 없음         | 17                 |
| 위키링크 출현                 | 181회              |
| 고유 링크 타깃                | 68                 |
| 실체 없는 타깃(dangling)      | 20 (29.4%)         |
| provenance 표기 `^[…]`        | 15회               |
| `graph_data.json` 노드 / 엣지 | 57 / 108           |
| 엣지 relation 종류            | 1종 (`references`) |
| 그래프에 없는 파일 basename   | 14                 |
| 전체 커밋                     | 41                 |
| 그중 `auto: wiki snapshot`    | 33 (80.5%)         |

디렉터리별로는 `categories/` 21, `concepts/` 15, `incidents/` 10, 루트 7, `raw/` 6, `roadmaps/` 5, `entities/` 4, `comparisons/` 1, `governance/` 1, `templates/` 1이다.

## 5. 숫자가 드러낸 세 가지

### (a) 자동화된 것은 저장이지 정제가 아니다

커밋 41개 중 33개(80.5%)가 `auto: wiki snapshot`이다. launchd가 `StartInterval` 3600초로 `scripts/git-autocommit.sh`를 돌려 변경이 있을 때만 커밋하고 푸시한다. 잘 돌아간다. 유실은 안 난다.

그런데 **스냅샷은 지식을 만들지 않는다.** 의미 있는 커밋 8개 — 최초 커밋, SCHEMA 개정, 7대 강제 원칙 신설, Leopard 스킬 동기화 등록, Hermes 토론 오케스트레이션 문서화 — 는 전부 사람이나 에이전트가 의도를 갖고 개입한 것이다. 자동화율 80.5%는 자랑이 아니라, 자동화가 파이프라인의 _뒤쪽_(보존)에만 걸려 있고 _앞쪽_(원본 → 개념으로의 증류)은 여전히 수동이라는 뜻이다. Generative Agents 용어로 옮기면, 관찰은 자동으로 쌓이는데 reflection 트리거가 없다.

### (b) 규격은 문서에만 있으면 조용히 사라진다

이게 가장 뼈아팠다.

초판 `SCHEMA.md`(커밋 `fe3a7e8`)에는 프론트매터 템플릿 7필드, 태그 분류, 페이지 생성 임계, 그리고 "`[[wikilinks]]`를 통한 상호 연결 필수 (페이지당 최소 2개)"라는 규약이 있었다. 그런데 2026-08-03 충돌 해소 머지 커밋 `a772439` 이후 현재 `SCHEMA.md`는 **717바이트**이고, 필드 목록도 위키링크 규약도 남아 있지 않다.

규격이 사라졌는데 **아무 빌드도 깨지지 않았다.** 아무도 몰랐다. 실효 텍스트는 git 히스토리와 파일들의 관행에만 남았다.

이 위키의 `concepts/harness-engineering.md`는 스스로 이렇게 적어두었다.

> "중요한 규칙일수록 프롬프트에서 코드로 옮긴다."

`SCHEMA.md`의 소실은 그 문장의 반례이자 증명이다. 규칙이 코드(린터·CI 게이트)로 옮겨지지 않았기 때문에, 마크다운 한 번의 머지 충돌로 증발했다. 같은 저장소의 `governance/7-enforcement-rules.md`가 ArchUnit·계약 테스트·UNIQUE 제약으로 강제되는 7개 원칙을 열거하는 동안, 정작 위키 자신의 스키마에는 게이트가 하나도 없었다.

### (c) 인덱스는 지식보다 느리다

`graph_data.json`은 2026-07-30 커밋 이후 재생성되지 않았다. 12일이 지났고, 그 사이 추가된 파일 14개(`7-enforcement-rules`, `leopard-skill-family`, `canonical-agent-skill-sync`, `agent-artifact-provenance`, 8월 토론 로그들)가 그래프에 없다. 노드 57개 중 34개는 `type`이 `unknown`이다.

그리고 엣지 108개의 `relation` 값은 **전부 `references` 한 종류**다. 관계 타입이 하나뿐인 그래프는 지식 그래프가 아니라 인용 그래프다. "A가 B를 언급한다"만 알 수 있고 "A가 B를 대체한다 / 반박한다 / 구현한다"는 표현할 수 없다. 링크 타깃 68개 중 20개(29.4%)는 실체 없는 placeholder다.

인덱스의 신선도는 저장소가 커질수록 검색 품질을 직접 깎는다. 2절의 결론 — 위키의 일은 안 읽을 것을 정하는 것 — 을 수행하는 주체가 바로 이 인덱스이기 때문이다.

## 6. 규율이 실제로 지켜진 곳

여기서 반대 방향의 숫자가 하나 나온다.

"페이지당 최소 2개 위키링크" 규약의 전체 준수율은 71개 중 26개, **36.6%**다. 링크가 0개인 파일이 42개다. 참담해 보인다.

그런데 `concepts/`만 떼어보면 **15개 중 13개(86.7%)**다.

링크 0개 파일 42개는 대부분 2026-04-07에 만들어진 레거시 `categories/` 21개와, frontmatter 자체가 없는 `incidents/` 원문 로그 10개다. 즉 **규율은 정제된 층에서만 지켜졌고, 원본 층에서는 지켜지지 않았다.**

그리고 그건 실패가 아니라 설계일 가능성이 높다. tmux로 캡처한 토론 원문에 스키마를 강요하면 원본성이 훼손된다. RAG의 어법으로는 비파라메트릭 메모리의 *색인*에는 규격이 필요하고 *원문*에는 필요 없다.

다만 그렇다면 "전체 준수율 36.6%"라는 지표 자체가 무의미해진다. 층마다 다른 게이트가 필요하다 — `raw/`·`incidents/`는 무규격 append-only, `concepts/`·`entities/`는 필드·링크·provenance 강제. 지금은 그 구분이 문서로도 코드로도 명시돼 있지 않다.

## 7. 되먹임 금지 — 위키는 학습 코퍼스가 아니다

이 위키는 압도적으로 에이전트가 쓴다. `index.md` 꼬리말은 스스로를 "Managed by `wiki_master.py` & `harness_distiller.py`"라고 적고, `pending_rules.md`에는 증류기가 뱉은 모델명 정규화 경고 문자열까지 그대로 찍혀 있다.

그러면 자연스러운 유혹이 생긴다. _이걸 학습 데이터로 쓰면 모델이 우리 시스템을 알게 되지 않을까._

Shumailov 등이 Nature에 실은 결과가 그 유혹에 대한 답이다. 모델 생성물을 무분별하게 학습에 되먹이면 'model collapse'가 일어난다 — 분포의 꼬리가 먼저 사라지고, 세대를 거치며 원본과 닮지 않은 저분산 분포로 수렴한다. 저자들은 "access to the original data distribution is crucial"이라고 못박고, 인터넷에서 긁은 데이터의 provenance 추적 문제를 정면으로 제기한다.[^8]

그래서 1절의 세 층 분리는 취향이 아니라 안전장치다. **위키는 읽히는 비파라메트릭 메모리로 남아야 한다.** 파라미터로 구워지는 순간 출처 추적도, 되돌리기도, 삭제도 불가능해진다. 이 위키가 provenance 캐럿 표기 `^[raw/…]`를 도입한 이유가 여기 있다 — 다만 실측 15회로, 아직 규율이라 부르기엔 얇다.

## 8. 그래서 상관관계는 무엇인가

한 문장으로:

> **머신러닝은 지식을 굽고, 위키는 지식을 고치고, 에이전트는 매 턴 둘 중 무엇을 쓸지 고른다.**

셋은 경쟁 관계가 아니라 갱신 주기의 분업이다. 파라미터는 몇 달, 파일은 몇 초, 선택은 매 턴.

그리고 실제로 세어보면 병목은 대개 세 번째가 아니라 두 번째에 있었다. 모델은 충분히 좋고 에이전트 루프도 돈다. 저장은 시간당 자동 커밋으로 자동화됐다. 그런데 **정제·규격·인덱스는 여전히 사람 손에 남아 있고, 그중 하나(스키마)는 이미 조용히 무너져 있었다.**

이 글에서 얻은 실행 항목 세 가지는 그래서 전부 두 번째 층에 있다.

1. `SCHEMA.md`의 프론트매터·링크 규약을 복원하고, 문서가 아니라 **CI 린터**로 강제한다. 문서에만 있으면 다음 머지 충돌에 또 사라진다.
2. `graph_data.json` 재생성을 autocommit 훅에 붙인다. 인덱스가 12일 늦으면 검색이 12일 늦는다.
3. 층별 게이트를 명시한다. `raw/`·`incidents/`는 무규격, `concepts/`·`entities/`는 필드·링크·provenance 필수.

## 9. 한계

- **단일 저장소 71개 파일의 관찰이다.** 일반 법칙이 아니라 한 사례의 구조 진단이다.
- **이 위키가 에이전트 성능을 실제로 얼마나 올렸는지는 측정하지 않았다.** before/after 평가셋이 없다. 위 표는 저장소의 구조적 상태이지 효과 크기가 아니다. 효과를 주장하려면 같은 과제를 위키 있음/없음으로 돌린 대조 실험이 필요하고, 그건 아직 없다.
- **인용한 개선폭(+39%, +29%, 84%, +90.2%, 15배)은 전부 벤더 자체 평가다.** 중립 제3자 재현은 확인하지 못했다.
- 측정 스크립트는 정규식 기반이라 코드블록 안의 `[[`도 링크로 셀 수 있다. 파일 수·커밋 수·그래프 통계는 이 오차의 영향을 받지 않지만, 위키링크 181회는 소폭 과대일 수 있다.
- 3절의 "디렉터리 배치가 Generative Agents 구조와 겹친다"는 관찰이지 인과가 아니다. 이 위키가 그 논문을 보고 설계됐다는 근거는 없다.

## 재현 방법

```python
import os, re, json, subprocess, collections
W = '/Users/lms/wiki'

mds = []
for root, dirs, files in os.walk(W):
    dirs[:] = [d for d in dirs if d != '.git']
    mds += [os.path.join(root, f) for f in files if f.endswith('.md')]

FM = ['title', 'created', 'updated', 'type', 'tags', 'sources', 'confidence']
has_fm = has_type = full7 = 0
for p in mds:
    t = open(p, encoding='utf-8').read()
    if not t.startswith('---'):
        continue
    end = t.find('\n---', 3)
    if end < 0:
        continue
    has_fm += 1
    keys = set(re.findall(r'^([A-Za-z_]+):', t[3:end], re.M))
    has_type += 'type' in keys
    full7 += all(k in keys for k in FM)

links = [m.group(1).strip()
         for p in mds
         for m in re.finditer(r'\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]',
                              open(p, encoding='utf-8').read())]
basenames = {os.path.splitext(os.path.basename(p))[0] for p in mds}
uniq = set(links)

g = json.load(open(os.path.join(W, 'graph_data.json')))
log = subprocess.run(['git', '-C', W, 'log', '--pretty=%s'],
                     capture_output=True, text=True).stdout.strip().split('\n')
auto = [s for s in log if s.startswith('auto: wiki snapshot')]

print('md', len(mds), '| fm', has_fm, '| type', has_type, '| full7', full7)
print('links', len(links), '| uniq', len(uniq),
      '| dangling', len(uniq - basenames))
print('graph', len(g['nodes']), len(g['links']),
      collections.Counter(l['relation'] for l in g['links']))
print('missing from graph', len(basenames - {n['id'] for n in g['nodes']}))
print('commits', len(log), 'auto', len(auto))
```

---

## References

- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_. NeurIPS 33. [arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401) · [NeurIPS PDF](https://proceedings.neurips.cc/paper/2020/file/6b493230205f780e1bc26945df7481e5-Paper.pdf)
- Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2024). _Lost in the Middle: How Language Models Use Long Contexts_. TACL 12, 157–173. [aclanthology.org/2024.tacl-1.9](https://aclanthology.org/2024.tacl-1.9/) · [arxiv.org/abs/2307.03172](https://arxiv.org/abs/2307.03172)
- Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). _Generative Agents: Interactive Simulacra of Human Behavior_. UIST '23. [dl.acm.org/doi/10.1145/3586183.3606763](https://dl.acm.org/doi/10.1145/3586183.3606763) · [arxiv.org/abs/2304.03442](https://arxiv.org/abs/2304.03442)
- Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). _MemGPT: Towards LLMs as Operating Systems_. [arxiv.org/abs/2310.08560](https://arxiv.org/abs/2310.08560)
- Shumailov, I., Shumaylov, Z., Zhao, Y., Papernot, N., Anderson, R., & Gal, Y. (2024). _AI models collapse when trained on recursively generated data_. Nature 631, 755–759. [doi.org/10.1038/s41586-024-07566-y](https://doi.org/10.1038/s41586-024-07566-y)
- Anthropic (2025-09-29). _Effective context engineering for AI agents_. [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic (2025-09-29). _Managing context on the Claude Developer Platform_. [anthropic.com/news/context-management](https://www.anthropic.com/news/context-management)
- Anthropic (2025-06-13). _How we built our multi-agent research system_. [anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)

측정 대상 저장소는 공개돼 있지 않은 개인 지식베이스(`~/wiki`, 커밋 `3c74480`)이며, 인용한 내부 문장은 해당 저장소의 파일에서 그대로 옮긴 것이다.

[^1]: Lewis et al. (2020), 초록 및 결론. 인용 문장은 NeurIPS 게재본 기준.

[^2]: Liu et al. (2024), §2.3. GPT-3.5-Turbo, 다문서 QA, 20·30문서 설정.

[^3]: Park et al. (2023), §4.1 Memory and Retrieval, §4.2 Reflection. 감쇠계수 0.995, 중요도 1–10, 반성 임계 150은 논문이 밝힌 자체 구현값이다.

[^4]: Packer et al. (2023), §3 main context / external context.

[^5]: Anthropic, _Effective context engineering for AI agents_ (2025-09-29).

[^6]: Anthropic, _Managing context on the Claude Developer Platform_ (2025-09-29). 자사 내부 평가셋 기준으로 발표된 값이며 외부 재현 결과는 확인하지 못했다.

[^7]: Anthropic, _How we built our multi-agent research system_ (2025-06-13). 역시 자사 내부 리서치 평가 기준.

[^8]: Shumailov et al. (2024), Nature 631, 755–759.
