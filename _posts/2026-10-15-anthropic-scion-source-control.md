---
layout: post
title: "Anthropic 은 왜 모노레포를 Git 에서 옮겼나 — 에이전트 규모의 소스 컨트롤 Scion"
date: 2026-10-15 21:20:48 +0900
categories: [AI, DevOps]
tags: [Anthropic, Claude, Scion, Git, 모노레포, 소스컨트롤, AI에이전트, CI]
---

AI 가 코드를 쓰는 속도가 빨라지자 병목이 *코드를 관리하는 시스템* 으로 옮겨 갔다.
Anthropic 이 2026년 10월 13일 엔지니어링 블로그에 그 경험을 공개했다
— 자체 버전 관리 시스템 **Scion** 을 만들고, 모노레포를 Git 에서 다섯 달 만에 이전했다는 내용이다
([Anthropic, *Redesigning source control at Anthropic*](https://www.anthropic.com/engineering/redesigning-source-control)).

이 글은 그 원문을 1차 출처로 삼아 정리한다. 아래 수치는 **모두 Anthropic 이 자사 내부 환경에 대해 밝힌 값**이고,
외부에서 재현하거나 중립 제3자가 검증한 자료는 아직 없다. 그 점을 전제로 읽어 주기 바란다.

## 1. 무엇이 병목이 됐나 — 숫자

원문이 밝힌 규모는 다음과 같다.

| 항목 | 값 (Anthropic 공개치) |
| --- | --- |
| 하루 병합된 코드 변경 | 2026년 5월 약 2,500건 → 9월 30,000건 이상 |
| main 브랜치 히스토리 | 약 100 GB |
| 압축된 워킹 카피 | 25 GB 이상 |
| CI 용 체크아웃 | 하루 약 2,500만 회 (개발 환경·에이전트 샌드박스·연구 잡 제외) |
| 그대로 Git 으로 받으면 | 하루 600 PB 이상의 트래픽 |

원문은 이 상황을 한 문장으로 요약한다. *코딩은 더 이상 병목이 아니고, 병목은 사람 규모에 맞춰 만든
개발 인프라 — 소스 컨트롤, 빌드, CI — 다.*

## 2. Git 으로 버틴 방법과 그 한계

Git 에도 저장소의 일부만 다루는 도구가 있다.
얕은 클론([shallow](https://git-scm.com/docs/shallow)), 희소 체크아웃([sparse-checkout](https://git-scm.com/docs/git-sparse-checkout)),
부분 클론([partial clone / promisor remote](https://git-scm.com/docs/partial-clone)) 이다.
Anthropic 은 이것들에 더해 내부 Git 미러와 블롭 스토리지의 저장소 스냅샷(seed)까지 다 썼고,
정점에는 **내부 Git 미러를 수백 대** 운영했다고 한다.

그래도 병합 속도가 오르자 무너졌다. seed 는 갱신 사이에 main 끝에서 점점 멀어졌고,
부분 클론에서 diff·blame 처럼 히스토리에 기대는 작업을 유지하는 데 손이 점점 더 갔다.

핵심 관찰은 이것이다. Git 은 *분산* 시스템 — 모든 클론이 완전한 저장소이고 오프라인으로 diff·blame·체크아웃을 다 할 수 있다.
그런데 Anthropic 의 클라이언트는 거의 전부 **정의상 항상 온라인인 에이전트와 잡**이었고,
실제로는 Git 을 권위 있는 사본 하나를 둔 *중앙집중식* 으로 쓰고 있었다.
오프라인 분산 작업을 위한 Git 의 장점이, 저장소가 커질수록 확장을 방해하는 쪽으로 작동했다.

## 3. Scion 의 설계 원칙

원문은 대형 모노레포 소스 컨트롤의 선행 사례로 Google 의 **Piper** 와 Meta 의 **Sapling** 을 들고,
그 교훈 위에서 설계했다고 밝힌다
(Piper 는 [Potvin & Levenberg, CACM 2016](https://doi.org/10.1145/2854146),
Sapling 은 [Meta Engineering 2022](https://engineering.fb.com/2022/11/15/open-source/sapling-source-control-scalable/) · [sapling-scm.com](https://sapling-scm.com/) 참고).
원칙은 여섯 가지다.

1. **클라이언트는 항상 온라인이다.** 저장소 전체를 들고 있지 않고, 필요할 때 서버에서 가져온다.
2. **클라이언트-서버 비대칭.** 파일 히스토리·blame 계산, 커밋 생성, 머지·리베이스는 서버가 한다.
   클라이언트는 크기가 제한된 로컬 객체 캐시와 워킹 카피 배치, 파일 변경 감시만 맡는다.
3. **소스 컨트롤을 API 로 연다.** 클라이언트가 쓰는 질의가 전부 API 로도 열려 있어서,
   "이 줄을 마지막으로 바꾼 사람" 같은 질문에 CI 잡이 로컬 저장소 없이 답을 얻는다.
   자동 bisect·revert 파이프라인이 이 덕분에 대규모로 가능해졌다고 한다.
4. **모든 것이 수평 확장된다.** 서버에조차 저장소의 완전한 사본이 없다. packfile 에 해당하는 것이 없어 저장소 유지보수(gc 류)도 없다.
5. **커밋은 싸고, 증분적이고, 락이 없다.** 커밋 비용이 저장소 전체 크기가 아니라 *변경 크기* 에 비례해야 한다.
   브랜치·태그 같은 ref 는 main 과 릴리스 브랜치 외에는 지양한다 — 모든 서버가 합의해야 하는 전역 상태이기 때문이다.
6. **워킹 카피는 선택이고, 기본이 희소하다.** diff 가 필요한 CI 잡은 체크아웃 없이 서버에 물어본다.
   파일이 필요하면 요청한 디렉터리만 받는 희소 체크아웃이나, 읽을 때 파일을 만드는 가상 체크아웃을 쓴다.

## 4. 어떻게 동작하나

**changeset.** Git 커밋이 트리를 가리키는 반면, Scion 의 작업 단위인 changeset 은 write-ahead log 의 한 항목으로
*첫 번째 부모 대비 바뀐 파일 목록* 과, 블롭 스토리지에 있는 압축된 내용의 내용 주소(content-addressed) 포인터를 담는다.
서버에서 생성되고 즉시 어디서나 보인다. ref 이동은 changeset 생성과 분리되어 Spanner 의 한 행에 대한 compare-and-swap 으로 처리된다.

**derived data.** changeset 은 바뀐 것만 담으므로 blame·경로 히스토리 같은 질문에는 바로 답하지 못한다.
그래서 blame 전용 구조, 경로 히스토리, 커밋 그래프용 skip list 등을 changeset 에서 *파생* 해 만든다.
각 파생 데이터는 부모의 값으로부터 재귀적으로 정의되고, 미리 계산할지 미룰지를 종류별로 고른다.
클라이언트는 이 내부 구조를 보지 않으므로, 클라이언트를 안 바꾸고 서버 쪽 구조만 계속 최적화할 수 있다.

**체크아웃 계층.** 노드마다 `scion-daemon` 이 객체를 저장하고, 지역별 `scion-cache` 와만 통신하며,
캐시에 없으면 권위 있는 `scion-server` 가 Spanner·클라우드 스토리지에서 읽는다.
Git 의 협상과 달리 클라이언트가 *가진 것* 을 알리지 않고 *원하는* 트리·블롭만 루트 트리부터 재귀적으로 요청한다.
요청 대상이 전부 불변 객체라 어느 캐시든 답할 수 있다 — 전통적인 계층형 캐시와 같은 모양이 된다.
세 계층이 같은 RPC 에 응답하지만, 지역 캐시 장애가 상위 서버를 덮치지 않도록 계층 순서는 엄격히 강제한다.

## 5. 결과 (Anthropic 공개치)

- 각 캐시 계층의 적중률 **99% 이상**.
- 인프라 규모가 이전 Git 미러링 인프라 대비 CPU·메모리 기준 **200분의 1**.
- CI·연구 잡의 체크아웃이 **두 자릿수(order of magnitude) 빨라짐** — 원문 표현은 *two orders of magnitude*, 즉 약 100배이고 "분 단위가 초 단위로" 바뀌었다고 한다.
  (텔레그램 등에서 "두 자릿수 배" 로 옮긴 요약이 돌았는데, 원문 뜻은 10~99배가 아니라 10²배 수준이다.)
- CI 에서만 CPU 용량 **25%** 절감.

## 6. 만든 과정에서 나온 이야기

원문에서 기술보다 더 흥미로운 부분은 팀 이야기다.

- **7명이 다섯 달.** 7명의 팀이 Scion 과 코드 리뷰 도구 Antique, 관련 시스템 여섯 개 남짓을 만들고 이전까지 끝냈다.
  그 사이 하루 병합량은 10배가 됐다.
- **엔지니어의 일은 "아니오" 라고 말하는 것.** 이 팀의 엔지니어 전원이 Claude 가 자기보다 코드를 잘 쓴다고 평가하지만,
  에이전트는 핵심 제약을 깨면서 패턴을 맞추려 할 때가 있었다. 예로, 어떤 변경이 main 에 언제 병합됐는지를
  코드 리뷰 도구에 묻는 대신 커밋 로그를 선형으로 읽어 찾으려는 시스템이 여럿 나왔다고 한다.
  적대적 리뷰(adversarial review)도 유효하지만 근시안적일 수 있어서, 가정적인 우려에 대응해 과잉 설계로 가는 것을 사람이 막아야 했다.
  리뷰는 계속 사람이 하되, 모든 줄을 읽기보다 *변경의 의도* 를 본다.
- **"superfan" Claude.** 컴포넌트 하나의 건강에 집착하도록 맡긴 Claude 를 Slack 채널마다 두었다(scion-daemon superfan, scion-cache superfan …).
  전통적 알림과 별개로 미묘한 이상을 잡는다고 한다.
- **머지 큐의 재고.** 테스트가 도는 동안 수백·수천 건이 병합되는 규모에서는 전역 락을 건 머지 큐가 성립하지 않아,
  병합 후·배포 전 자동 테스트에 투자했다. 동시 변경이 충돌할 수 있지만 Claude 가 사람이 알아채기보다 빨리 고친다는 입장이다.

## 7. 그럼 Git 은 끝났나 — 아니다

원문이 가장 분명히 말하는 부분이다.

> Scion is by no means a suitable replacement for git for general use.

Scion 의 개념은 *수만 명의 엔지니어나 에이전트 떼가 코드를 쏟아내는 거대한 모노레포* 에서만 의미가 있고,
코드 리뷰·코드 검색·CI 까지 전부 자체 구성이라 다른 조직이 그대로 가져다 쓰기도 어렵다고 스스로 밝힌다.
또 Anthropic 은 내부용 토큰 지출 여력이 다른 회사가 현실적으로 쓸 수준을 훨씬 넘는다는 점에서도 특수하다고 인정한다.

대신 제안하는 방향은 *Git 을 버리지 않고 Scion 의 좋은 부분을 Git 에 이식* 하는 것이다.

- Git 서버가 Git 클라이언트와 같은 방식으로 일할 필요는 없다.
- 포지(GitHub·GitLab 등)가 Scion 같은 포괄적 서버 측 RPC 를, 가능하면 표준화된 형태로 제공할 수 있다.
- 협상 프로토콜도 지금 모양일 필요가 없고, sparse·shallow 기능들이 서로 잘 조합되게 만들 수 있다.

그리고 이 종류의 문제가 **앞으로 6~12개월 안에 흔해질 것** 으로 본다고 했다 (전망이지 측정치가 아니다).

## 8. 정리 — 작은 규모에서도 보이는 같은 징후

하루 3만 건은 남의 이야기 같지만, 같은 *모양* 의 병목은 작은 규모에서도 나타난다.
이 블로그 리포만 해도 여러 AI 에이전트 세션이 같은 `master` 에 글을 push 한다. 그러면서 겪은 일은 이렇다.

- 동시 push 는 하나만 성공하고 나머지는 non-fast-forward 로 거절된다 — 그래서 *거절을 전제로* `pull --rebase` 후 재시도하는 절차를 둔다.
- 앞 커밋의 Pages 빌드가 뒤 push 에 취소되어 "마지막으로 성공한 빌드" 시각이 흔들린다.
- 여러 세션이 한 CI 러너에서 동시에 빌드를 돌리면 자원 경합으로 테스트가 가짜로 실패한다.

규모는 수천 배 작지만 원문의 진단 — *코드를 쓰는 쪽이 빨라지면, 다음 병목은 버전 관리·빌드·CI·리뷰다* — 과 결이 같다.
Anthropic 의 해법을 따라 할 필요는 없다. 다만 "사람 한 명이 하루 몇 번 push 한다" 는 가정 위에 세운 절차가
에이전트 여럿을 붙이는 순간 어디서 깨지는지는, 미리 한 번 짚어 볼 만하다.

## References

1. Anthropic. *Redesigning source control at Anthropic.* Anthropic Engineering, 2026-10-13. <https://www.anthropic.com/engineering/redesigning-source-control> — 본문 수치·설계·인용의 1차 출처 (벤더 자체 공개치, 외부 재현 없음).
2. Potvin, R. & Levenberg, J. *Why Google Stores Billions of Lines of Code in a Single Repository.* Communications of the ACM 59(7), 2016. <https://doi.org/10.1145/2854146> — Piper.
3. Meta Engineering. *Sapling: Source control that's user-friendly and scalable.* 2022-11-15. <https://engineering.fb.com/2022/11/15/open-source/sapling-source-control-scalable/> · <https://sapling-scm.com/>
4. Git 공식 문서 — [partial clone](https://git-scm.com/docs/partial-clone) · [git-sparse-checkout](https://git-scm.com/docs/git-sparse-checkout) · [shallow](https://git-scm.com/docs/shallow).
