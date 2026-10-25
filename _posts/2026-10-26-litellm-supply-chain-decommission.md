---
layout: post
title: "LiteLLM 1.107.0 공급망 사고 — 안 맞았는데 왜 걷어냈나"
date: 2026-10-26 01:08:37 +0900
categories: [security, kubernetes]
tags: [litellm, supply-chain, llm-gateway, argocd, cloudflare, n8n, incident-response]
---

2026-10-21, LLM 프록시 LiteLLM 의 릴리스 파이프라인이 탈취돼 악성 `1.107.0` 이 PyPI 와 공식 컨테이너 레지스트리에 올라갔다. 우리 홈랩 클러스터도 LiteLLM 을 게이트웨이로 쓰고 있었다. 결론부터:

- **감염되지 않았다.** 근거는 이미지 digest 와 기동 시각, 두 가지다.
- **그런데도 LiteLLM 을 통째로 걷어냈다.** 안 맞은 이유가 설계가 아니라 *운*이었기 때문이다.

이 글은 판정 근거, 제거 절차, 도중에 밟은 함정을 순서대로 적는다.

## 1. 무슨 일이 있었나 — 1차 출처 기준

LiteLLM 공식 사고 공지([LiteLLM, 2026-10-21](https://docs.litellm.ai/blog/security-incident-oct-21-2026))가 밝힌 오염 범위는 다음과 같다.

- **PyPI**: `litellm==1.107.0` 휠 7개. 11:39:51 ~ 13:23 UTC 동안 게시돼 있었다.
- **Docker Hub**: `v1.107.0` · `latest` · `main-latest` · `main-stable` 태그가 악성 이미지 인덱스 `sha256:1bbcb144…` 를 가리켰다. 11:46:56 ~ 14:20 UTC.
- **GHCR**: 같은 태그들이 11:46:56 부터 13:51 UTC 사이에 오염돼 있었다.
- **GitHub 소스**: 공식 `v1.107.0` 소스 태그에는 악성 파일이 없다. 공격자 저장소(`Berri-AI/litellm`, 하이픈 하나 차이)에서 빌드됐다.

페이로드는 OSV 항목 [MAL-2026-2144](https://osv.dev/vulnerability/MAL-2026-2144)와 [Microsoft Security Blog (2026-10-23)](https://www.microsoft.com/en-us/security/blog/2026/10/23/inside-the-litellm-1-107-0-supply-chain-compromise-credential-theft-through-python-startup-hooks/)가 분석했다.

- 휠이 site-packages 루트에 `cook.pth` 를 깐다. `.pth` 는 **파이썬 인터프리터가 뜰 때마다** 실행되므로 `import litellm` 을 하지 않아도 돈다.
- 그 안의 정보 탈취기가 수집해 외부로 보내는 것:
  - SSH 키, 클라우드 자격증명, 환경변수
  - Kubernetes·CI 시크릿
  - `~/.claude` · `~/.cursor` 같은 AI 개발도구 설정
- `sitecustomize.py` 는 매시간 원격 코드를 받아 실행하는 데몬을 띄운다.

LiteLLM 공지의 대응 지침도 단호하다. "오염 구간에 이미지를 기동했다면 침해된 것으로 간주하라." 그리고 회전 대상으로 *프록시 DB 에 저장된 모든 프로바이더 키, 마스터 키, `DATABASE_URL` 비밀번호* 를 꼽는다.

### 첫 보도와 최종 RCA 가 다르다

10/21 첫 공지는 탈취 경로를 이렇게 추정했다. 내부 LiteLLM 배포의 로그에 GitHub CLI 토큰이 찍혔고, 공격자가 그 로그에서 토큰을 가져갔다는 것이다. 이틀 뒤 나온 최종 RCA([LiteLLM, 2026-10-23](https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain))가 이를 정정했다. 확정된 경로는 이렇다.

1. **5/27**: 내부 실험 서비스(Agent Platform)의 마스터 키가 공개 저장소에 커밋됐다. 바로 force-push 로 덮었지만 **키 자체는 회전하지 않았다.**
2. **10/10**: 공격자가 그 키로 Agent Platform API 를 호출했다. 응답에 조직 소유자의 GitHub CLI OAuth 토큰이 들어 있었다.
3. 그 토큰으로 일회용 워크플로를 돌려 CI 시크릿을 빼냈다. 이렇게 메인테이너 토큰 2개를 추가로 얻었다.
4. **10/21**: 소유자 토큰으로 브랜치 보호를 끄고 릴리스 워크플로의 소스를 가짜 저장소로 바꿨다. 두 번째 메인테이너 토큰으로 프로덕션 게이트를 승인했다. 세 번째 토큰으로 실행 기록을 지웠다.

RCA 의 자평은 이렇다. *"이 사고는 노출됐을 수 있는 키를 회전하지 않는 것의 위험을 강하게 보여 준다."* 서명·불변 태그·물리적으로 묶인 퍼블리셔 계정까지 갖춘 파이프라인이었다. 그런데 무너진 지점은 다섯 달 묵은 키 하나였다.

> 첫 공지만 읽고 "로그에 토큰이 찍혀서" 라고 정리했다면 틀린 교훈을 가져갔을 것이다. 진행 중인 사고 공지는 *그 시점의 가설*이다. 최종 RCA 를 다시 확인할 것.

## 2. 우리 판정 — 안 맞았다. 근거 두 개

우리 배포는 `ghcr.io/berriai/litellm:main-latest` 를 쓰고 있었다. **정확히 오염된 태그다.**

| 확인 항목 | 값 | 판정 |
| --- | --- | --- |
| 돌던 컨테이너의 이미지 digest | `79b03d…` | 악성 GHCR 인덱스 `1bbcb144…` 와 다름 |
| 컨테이너 기동 시각 | 10/18 | 오염 구간(10/21 11:46~13:51 UTC)보다 이전. 그 뒤 재시작 없음 |

둘 다 맞으니 악성 이미지는 실행되지 않았다. LiteLLM 공지의 판정 기준은 "오염 구간에 *기동*했는가"와 "그 digest 를 실행했는가"다. 우리는 둘 다 해당하지 않는다.

## 3. 그런데 왜 걷어냈나 — 운이었다

배포 매니페스트를 다시 보면 `image: …:main-latest` 에 `imagePullPolicy: IfNotPresent`, 그리고 특정 노드 고정이었다.

- 같은 노드에서 컨테이너만 재시작하면 → 캐시된 옛 이미지를 다시 쓴다. 안전하다.
- 노드가 바뀌어 **새로 pull 하면** → 그 시각에 `main-latest` 가 가리키던 이미지를 받는다.

이 파드의 재시작 횟수는 26회였다. 그 노드는 무선 링크라 흔들리는 노드다. 10/21 낮 두 시간 사이에 노드가 바뀌었다면 악성 이미지를 끌어왔을 것이다. 그 이미지는 프로바이더 키 전부가 담긴 envFrom Secret 을 들고 기동했을 것이다.

즉 우리를 지킨 건 아무도 설계하지 않은 캐시 동작이다. 고쳐서 계속 쓰는 길도 있었다. 버전 고정과 digest 고정, 키 회전이다. 하지만 먼저 질문이 하나 있었다. **"이게 아직 필요한가?"**

### 소비자를 셌다

LiteLLM 은 호출마다 `LiteLLM_SpendLogs` 에 기록을 남긴다. 30일치를 키별로 집계했다.

- 10/04 까지는 사내 에이전트·메모리 QA·지식베이스 VLM 이 여러 경로로 쓰고 있었다.
- **10/05 이후 남은 소비자는 n8n 워크플로 2개뿐**이었다. 하나는 코딩테스트 일일 풀이, 하나는 자격증 문제 생성이다.
- 메모리 QA 는 설정상 LiteLLM 을 거쳤지만, 실제로는 호출이 일어나지 않고 있었다(아래 4-②).

프로바이더 키 4종을 한 곳에 모아 쥔 게이트웨이가 있었다. 인터넷 쪽 인그레스와 Access 앱까지 달려 있었다. 그런데 정작 하는 일은 하루 몇 번의 호출 전달뿐이었다. 걷어내는 쪽이 공격면이 가장 많이 줄어드는 선택이었다.

## 4. 제거 절차 — 소비자부터, 리소스는 맨 나중에

순서는 이렇게 잡았다.

1. 소비자를 프로바이더 직접 호출로 옮긴다.
2. 남은 소비자가 0인지 확인한다.
3. replicas 0 으로 내린다.
4. 전부 삭제한다.

뒤집으면 장애가 난다.

### ① n8n — 워크플로를 다시 넣으면 비활성화된다

워크플로 2개의 HTTP 노드 URL 을 `https://api.openai.com/v1/chat/completions` 로 바꾸고, 새 헤더 인증 자격증명을 붙였다. n8n 2.x CLI 로 작업할 때 함정이 있다.

- `import:workflow` 는 가져온 워크플로를 **비활성화**한다. 출력에 `Deactivating workflow …` 가 찍힌다.
- 그래서 `publish:workflow --id=…` 로 다시 활성화하고 n8n 을 재시작해야 한다.
- "가져오기 성공"만 보고 끝내면 다음 날 아침 크론이 조용히 안 돈다. 확인은 DB 에서 `active=1` 이고 `activeVersionId = versionId` 인지로 했다.

### ② 메모리 QA — 이미 고장 나 있었다

직접 호출로 바꾸며 테스트했더니 `gemini-2.5-flash` 가 404 를 돌려줬다. 메시지는 "no longer available to new users". 즉 LiteLLM 경유 경로도 이미 실패하고 있었다는 뜻이다. 모델을 `gemini-3-flash-preview` 로 올리고 파드 안에서 같은 호출을 재현해 200 을 확인했다.

게이트웨이가 있으면 "어느 모델이 실제로 죽었는지"가 한 겹 가려진다. 걷어낸 덕에 드러난 고장이다.

### ③ ArgoCD — `prune: false` 면 git 에서 지워도 안 지워진다

LiteLLM 매니페스트를 담은 ArgoCD 앱 두 개는 `prune: false` + `selfHeal: true` 였다. 이 조합에서는:

- git 에서 파일을 지워도 클러스터 리소스는 그대로 남는다. 앱은 OutOfSync 가 된다.
- 반대로 git 반영 전에 `kubectl delete` 를 하면 selfHeal 이 되살린다.

그래서 순서는 이렇게 갔다.

1. git 커밋·push
2. 앱이 새 리비전을 보는지 확인
3. `kubectl scale --replicas=0`
4. `kubectl delete`: Ingress → Service → Deployment → ConfigMap → SopsSecret 순
5. 두 앱이 다시 Synced/Healthy 로 돌아오는지 확인

SOPS 로 관리하던 Secret 은 SopsSecret CR 을 지우면 ownerReference 로 실제 Secret 까지 같이 사라진다.

### ④ Cloudflare 터널 — PUT 은 전체 교체다

원격 관리 터널의 ingress 설정은 `PUT /cfd_tunnel/{id}/configurations` 로 바꾼다. 이 API 는 **부분 수정이 아니라 전체 교체**다. 절차는 이렇게 했다.

1. 현재 설정을 GET 으로 받는다.
2. 해당 hostname 한 줄만 뺀다.
3. 마지막 규칙이 catch-all(`http_status:404`)인지 assert 한다.
4. PUT 으로 올린다.
5. 다시 GET 해서 14→13 줄과 catch-all 위치를 확인한다.

DNS CNAME 과 Access 앱도 지웠다. 그 Access 앱에만 쓰이던 서비스 토큰도 다른 앱 정책에서 참조하는지 전수 확인한 뒤 삭제했다.

### ⑤ 지우면 우는 것들

도메인이 사라지면 우리 쪽 감시가 오탐을 낸다. 미리 지운 것들:

- **도메인 헬스체크**: n8n 워크플로가 30분마다 호스트 24개를 찌른다. 거기서 해당 호스트를 뺐다.
- **랜딩 페이지 카드**: 지웠다. 헬스체크는 본문 크기 ±50% 허용이라 카드 하나 빠지는 건 알람이 아니다.
- **에이전트(Hermes) 설정**: 남아 있던 provider 블록과 env 키를 지웠다.

### ⑥ DB 는 백업 검증 후 DROP

지우기 전에 남긴 것:

- `pg_dump -Fc` 덤프
- 리소스 매니페스트 사본

둘 다 권한 700 디렉터리에 뒀다. 덤프는 `pg_restore -l` 로 목차가 읽히는지(테이블 데이터 102개) 확인한 뒤에야 `DROP DATABASE` 했다. 접속 세션 수가 0 인 것도 먼저 봤다.

### 최종 실측

| 확인 | 결과 |
| --- | --- |
| NodePort | 클러스터 전체에서 해당 포트를 쓰는 Service 0개 |
| 공개 도메인 | DNS 응답 없음, 접속 불가 |
| ArgoCD | 관련 앱 3개 Synced/Healthy, 새 리비전 |
| 클러스터 객체 | 이름에 litellm 이 들어간 리소스 0개 |
| n8n | 워크플로 3개(헬스체크 포함) active |
| 직접 호출로 옮긴 서비스 | 파드 Running, 파드 안에서 실호출 200 |

## 5. 아직 안 풀린 것

- **프로바이더 키는 회전하지 않았다.** 악성 이미지가 실행되지 않았다는 판정에 기댄 결정이다. 판정 근거는 digest 와 기동 시각 두 가지뿐이다. 이 판정이 틀렸다면 회전하지 않은 키가 그대로 남는다. RCA 가 강조한 바로 그 실패 모드다.
- **백업 디렉터리에 살아 있는 키가 있다.** 마스터 키는 이제 의미가 없다. 하지만 같은 Secret 사본에 든 OpenAI·Gemini 키는 지금도 유효하다. 백업도 비밀로 취급해야 하고, 보관 기한을 정해야 한다.
- **직접 호출로 옮기면서 잃은 것**이 있다. 호출당 비용·지연 로그를 한 곳에서 보던 기능이 사라졌다. 이제 프로바이더별 대시보드를 따로 봐야 한다.
- LiteLLM 공지에는 엔터프라이즈 레지스트리로 먼저 배포된 **별도 취약점의 공개일(10/27)**이 적혀 있다. 우리에겐 이제 무관하다. 하지만 셀프호스팅 LiteLLM 을 계속 쓰는 곳이라면 그날 공지를 확인해야 한다.

## 정리

- 공급망 사고에서 첫 질문은 "맞았나?"다. 판정은 digest 와 기동 시각으로 할 수 있었다.
- 두 번째 질문은 **"안 맞은 게 설계 덕인가, 운 덕인가?"**였다. 가변 태그에 `IfNotPresent` 라면 운이다.
- 세 번째 질문이 결정을 바꿨다. **"이게 아직 필요한가?"** 사용 로그를 세 보니 답은 "아니다"였다. 키를 한 곳에 모아 쥔 구성 요소는 고치는 것보다 없애는 편이 공격면을 더 줄인다.

## References

1. LiteLLM, *Contained: Oct 21, 2026 LiteLLM release v1.107.0 Compromised* (2026-10-21, 진행 중 기록). <https://docs.litellm.ai/blog/security-incident-oct-21-2026>
2. LiteLLM (O. Jensen, M. Wang), *The attack chain behind the v1.107.0 LiteLLM release* (2026-10-23, 최종 RCA). <https://docs.litellm.ai/blog/security-incident-oct-21-2026-attack-chain>
3. Microsoft Security Blog, *Inside the LiteLLM 1.107.0 supply chain compromise: Credential theft through Python startup hooks* (2026-10-23). <https://www.microsoft.com/en-us/security/blog/2026/10/23/inside-the-litellm-1-107-0-supply-chain-compromise-credential-theft-through-python-startup-hooks/>
4. OSV / OpenSSF Malicious Packages, *MAL-2026-2144 — Malicious code in litellm (PyPI)*. <https://osv.dev/vulnerability/MAL-2026-2144>
5. Kubernetes 공식 문서, *Images — Image pull policy*. <https://kubernetes.io/docs/concepts/containers/images/#image-pull-policy>
6. Cloudflare 공식 문서, *Configure a remotely-managed tunnel (API)*. <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel-api/>
7. Argo CD 공식 문서, *Automated Sync Policy — prune / selfHeal*. <https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/>
