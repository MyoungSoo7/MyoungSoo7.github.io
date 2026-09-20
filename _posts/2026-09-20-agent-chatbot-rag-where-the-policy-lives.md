---
layout: post
title: "해커톤 에이전트 챗봇 — 검색은 서버로 옮겼는데, 정책은 브라우저에 남았다"
date: 2026-09-20 11:28:40 +0900
categories: [AI, Architecture]
tags: [RAG, LLM, Agent, NVIDIA NIM, Pinecone, Hackathon, Security]
---

해커톤 리포 하나를 처음부터 끝까지 읽었다. [kyungsikjeung/hackathon-agent-chatbot](https://github.com/kyungsikjeung/hackathon-agent-chatbot) — "BuildMate", 소프트웨어 개발 상담을 받아주는 에이전트 챗봇이다. 커밋 7개, 파이썬 두 개, 자바스크립트 한 줌. 규모는 작지만 **RAG 서비스가 실제로 어디서 갈라지는지**를 아주 선명하게 보여주는 표본이라서 적어둔다.

결론부터: 이 팀은 **검색(retrieval)을 서버로 옮기는 데는 성공했고, 정책(policy)은 브라우저에 남겨뒀다.** 그리고 그 둘의 차이가 이 글의 전부다.

## 1. 흐름은 이렇다

리포를 읽어서 복원한 런타임 경로다.

```
브라우저 위젯 (Netlify 정적 호스팅)
  └─ config.js (빌드 타임에 환경변수로 생성, gitignore)
       ↓  ngrok 공개 터널 (발표 시간에만 기동)
  backend.py  :8643      ← RAG 프록시
       ├─ NIM embeddings (nvidia/nemotron-3-embed-1b)
       ├─ Pinecone topK=3
       └─ 검색 결과를 system 메시지로 주입
       ↓
  Hermes 게이트웨이 127.0.0.1:8642
       ↓
  NVIDIA NIM — nvidia/nemotron-3-super-120b-a12b
```

지식 베이스는 `knowledge/services.json` 한 파일이다. 서비스 5종(랜딩페이지·챗봇/예약·쇼핑몰·모바일앱 등)에 각각 `min_price_krw`와 `typical_duration`이 붙어 있고, `ingest.py`가 그걸 임베딩해서 Pinecone 인덱스 `buildmate-knowledge`에 올린다.

모델 선택은 합리적이다. NVIDIA 모델 카드 기준으로 `nemotron-3-super-120b-a12b`는 총 120B / 활성 12B의 LatentMoE 구조이고, 카드가 명시한 "Best For" 항목에 **agentic workflows, tool use, RAG**가 들어 있다([NVIDIA 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard)). 상담 에이전트에 갖다 붙이기에 어긋나는 선택이 아니다.

## 2. 잘한 것 — `input_type`을 정확히 나눴다

RAG에서 조용히 성능을 깎아먹는 대표적인 실수가 **색인할 때와 질의할 때 임베딩 타입을 똑같이 주는 것**이다. 이 리포는 그걸 안 했다.

```python
# ingest.py:39 — 문서를 넣을 때
"input_type": "passage",

# backend.py:45 — 질문을 임베딩할 때
"input_type": "query"
```

NVIDIA의 `nemotron-3-embed-1b` 문서는 이 파라미터를 선택 사항으로 두지 않는다. 색인에는 `passage`, 검색에는 `query`를 쓰라고 명시하고, 그렇게 하지 않으면 검색 정확도가 크게 떨어진다고 경고한다([모델 문서](https://build.nvidia.com/nvidia/nemotron-3-embed-1b/modelcard)). 해커톤 속도로 짜면서 여기를 맞춘 건 문서를 실제로 읽었다는 증거다.

주입 방식도 정직하다. 검색 결과를 유저 메시지에 이어 붙이는 게 아니라, **마지막 유저 턴 바로 앞에 `system` 역할로 끼워 넣는다.**

```python
# backend.py — 주석이 의도를 그대로 적어뒀다
# Inject retrieved context as a system message right
# before the latest user turn, so the model sees it
# as authoritative background, not user-supplied text.
messages.insert(insert_at, {"role": "system", "content": context_block})
```

그리고 검색이 실패해도 대화는 안 끊는다.

```python
except Exception as e:
    # RAG lookup is best-effort; never block the chat on failure.
    print("RAG lookup failed:", e)
```

여기까지는 프로덕션 코드에 그대로 둬도 논쟁거리가 별로 없다.

## 3. 남은 것 — 에이전트 정책 전부가 브라우저에 있다

이 프로젝트에서 **가장 지키고 싶었을 규칙**은 예산 가드레일이다. 고객이 "50만원에 쇼핑몰 만들어주세요" 하면 그냥 넘어가지 말고, 일반적인 비용에 못 미친다고 먼저 알리고, 축소 MVP 같은 대안을 1~2개 제시하고, 최종 승인은 사람에게 넘기라는 것. 프롬프트에 이렇게 적혀 있다.

> 최종 승인/거절은 AI가 하지 않습니다.

좋은 설계다. AI에게 계약 결정권을 주지 않았다.

문제는 **그 문장이 어디에 있느냐**다. `frontend/chat-widget.js`, 위젯 스크립트의 `history[0]`이다. 참고 최소가(랜딩페이지 50만원 / 챗봇·예약 150만원 / 쇼핑몰 300만원 / 모바일앱 500만원)도 같은 자리에 있다. 즉 이 규칙 전체가 **브라우저가 서버로 보내주는 값**이다. 서버는 그걸 검사하지 않는다 — `backend.py`가 `messages`를 건드리는 유일한 지점은 검색 컨텍스트를 끼워 넣는 곳뿐이고, 첫 번째 system 메시지가 원본 그대로인지는 확인하지 않는다.

같은 경계선 위에 두 가지가 더 얹혀 있다.

**① 게이트웨이 키가 브라우저로 간다.** `frontend/config.example.js`를 보면 `API_KEY`가 클라이언트 설정에 들어 있다.

```javascript
// From: nemohermes hermespatched gateway-token --quiet
API_KEY: "REPLACE-WITH-GATEWAY-TOKEN",
```

`config.js`는 `.gitignore`에 올바르게 들어가 있다. 하지만 gitignore가 막는 건 *리포에 커밋되는 것*이지 *브라우저로 전송되는 것*이 아니다. Netlify가 빌드 타임에 환경변수로 이 파일을 만들어 정적 호스팅하면, 그 값은 페이지를 연 모든 사람이 읽을 수 있다.

**② CORS가 전면 개방이다.**

```python
# backend.py:84
self.send_header("Access-Control-Allow-Origin", "*")
```

셋을 합치면 한 문장이 된다. **누구든 위젯을 거치지 않고 터널 주소로 직접 요청을 보낼 수 있고, 그때 예산 가드레일은 존재하지 않는다.**

공정하게 덧붙이면, 이건 해커톤 데모다. ngrok 터널은 발표 시간에만 뜨고, 뒤에 붙은 건 실제 결제나 고객 DB가 아니라 NIM 추론이다. 실질 피해 규모는 "누가 남의 API 크레딧을 쓸 수 있다" 수준이다. 리포 스스로도 README에서 시연용 구성임을 밝히고 있다. **그래서 이건 사고 보고서가 아니라 경계선 이야기다.**

## 4. 옮기는 건 어렵지 않다

고칠 게 많아 보이지만, 이미 `backend.py`라는 서버가 있기 때문에 실제로는 짧다.

1. **system 프롬프트를 `backend.py`로 옮긴다.** 클라이언트가 보낸 `messages`에서 role이 `system`인 항목은 전부 버리고, 서버가 가진 정책 문자열을 맨 앞에 새로 넣는다. 위젯은 유저 발화만 보낸다.
2. **참고 최소가를 프롬프트가 아니라 데이터에서 읽는다.** `knowledge/services.json`에 이미 `min_price_krw`가 있다. 프롬프트에 숫자를 복붙해 두면 지식 베이스와 프롬프트가 따로 논다 — 가격을 고칠 때 두 군데를 고쳐야 하고, 한 군데를 잊으면 모델이 옛날 가격으로 상담한다.
3. **키를 브라우저에서 뺀다.** 위젯은 `backend.py`만 호출하고, 상류 게이트웨이 토큰은 서버 안에 둔다. 프록시가 이미 있으니 구조 변경이 아니라 헤더 한 줄 이동이다.
4. **`Access-Control-Allow-Origin`을 Netlify 도메인으로 좁힌다.** 와일드카드를 고정 문자열로 바꾸는 일이다.

핵심은 "보안을 추가"하는 게 아니다. **이 팀은 이미 서버를 세웠다.** 검색은 그 서버 안으로 들어갔는데 정책만 밖에 남았을 뿐이고, 남은 작업은 나머지를 같은 선 안쪽으로 당기는 것이다.

## 5. 덤 — `docs/TROUBLESHOOTING.md`

이 리포에서 의외로 값이 나가는 파일은 챗봇 코드가 아니라 트러블슈팅 문서다. 개발 환경을 세우다 부딪힌 것들을 재현 절차와 함께 적어뒀고, **대부분 업스트림 이슈 번호까지 달려 있어서 검증이 된다.**

- **macOS에서 GPU 패치가 `getent unable to find entry "0:0" in passwd`로 실패** — NemoClaw 이슈 [#12010](https://github.com/NVIDIA/NemoClaw/issues/12010) ("Docker receipt transfer rejects seed user 0:0 on Engine 27"). 수정 PR [#12015](https://github.com/NVIDIA/NemoClaw/pull/12015)가 2026-09-19에 머지됐다. 문서는 `lkg` 태그가 수정보다 뒤처져 있어 머지 커밋 `e38726c8`을 직접 핀으로 박아 우회했다고 적는다 — 태그가 아니라 커밋을 고정하는 이유로 정확한 설명이다.
- **대시보드 포트포워드 타임아웃** — 이슈 [#11963](https://github.com/NVIDIA/NemoClaw/issues/11963). 확인 시점 기준 **아직 열려 있다.** 문서가 "안 고쳐졌다"고 적은 게 사실이었다. 우회는 `timeouts.ts`의 프로브/오퍼레이션 타임아웃을 60s/120s로 늘리고 CLI를 다시 빌드하는 것.
- **Docker Desktop 컨텍스트가 재시작마다 `desktop-linux`로 되돌아감** — 매번 `docker context use default`.

문서는 검증 범위도 스스로 한정한다. macOS Apple Silicon M1 Pro + Docker Desktop에서만 확인했고 Windows는 미검증이라고 적혀 있다. 해커톤 산출물에서 이 정도로 범위를 정직하게 좁힌 문서는 흔치 않다.

## 마무리

RAG 파이프라인을 서버로 옮기는 건 이제 잘 알려진 작업이다. 이 팀도 며칠 만에 해냈다. 하지만 **에이전트에서 진짜 지켜야 하는 건 검색 결과가 아니라 행동 규칙**이고, 그건 "검색을 서버로 옮겼다"에 딸려 오지 않는다. 별도로 옮겨야 한다.

가드레일이 클라이언트에 있으면 그건 가드레일이 아니라 **기본값**이다. 대부분의 사용자에게는 똑같이 작동하고, 굳이 우회하려는 한 명에게만 없다. 그 한 명이 문제가 되는 순간이 오기 전까지는 둘의 차이가 보이지 않는다는 게 이 구조의 유일한 위험이다.

---

## References

- 분석 대상 리포: [kyungsikjeung/hackathon-agent-chatbot](https://github.com/kyungsikjeung/hackathon-agent-chatbot) — 커밋 `2dce013`~`d34e475` 기준
- [NVIDIA-Nemotron-3-Super-120B-A12B 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-super-120b-a12b/modelcard) — 파라미터 수, 아키텍처, 권장 용도
- [NVIDIA-Nemotron-3-Embed-1B 모델 카드](https://build.nvidia.com/nvidia/nemotron-3-embed-1b/modelcard) — `input_type` (`passage`/`query`) 필수 사용 안내
- [NVIDIA/NemoClaw 이슈 #12010](https://github.com/NVIDIA/NemoClaw/issues/12010) / [PR #12015](https://github.com/NVIDIA/NemoClaw/pull/12015) — Docker Engine 27 seed user 문제 및 수정
- [NVIDIA/NemoClaw 이슈 #11963](https://github.com/NVIDIA/NemoClaw/issues/11963) — OpenShell 대시보드 포워드 타임아웃 (2026-09-20 확인 시점 open)
- [MDN — Access-Control-Allow-Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Access-Control-Allow-Origin)
