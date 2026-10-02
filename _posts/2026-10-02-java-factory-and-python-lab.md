---
layout: post
title: "자바공장과 파이썬연구소 — 한쪽은 재현하는 법을, 한쪽은 틀려도 되는 법을 안다. 문제는 둘 사이의 복도다"
date: 2026-10-02 21:30:00 +0900
categories: [reflection, career, communication]
tags: [java, python, culture, reproducibility, mlops, jupyter, team, communication]
---

자바공장 이야기를 두 편 썼다. [1편]({% post_url 2026-10-02-communication-and-the-java-factory %})은 "질문 없이 만드는 습관",
[2편]({% post_url 2026-10-02-java-factory-trust-passion-and-the-managers-job %})은 그 습관을 바꾸는 신뢰·열정·관리자의 조율이었다.
이번엔 거울을 하나 세워 본다. **파이썬연구소**다.

물론 둘 다 캐리커처다. Java 로 연구하는 사람도, Python 으로 공장을 돌리는 사람도 많다.
여기서 말하는 건 언어가 아니라 **일하는 문화의 두 극단**이다.

| | 자바공장 | 파이썬연구소 |
|---|---|---|
| 목표 | 같은 걸 **안정적으로 반복** 생산 | **아직 모르는 걸** 알아내기 |
| 대표 산출물 | 배포된 서비스, API 계약 | 노트북, 실험 결과, 그래프 |
| 미덕 | 재현성, 절차, 계약, 테스트 | 속도, 탐색, 가설 검증 |
| 흔한 말버릇 | "명세에 없는데요" | "제 노트북에선 돌았는데요" |

두 문화는 서로의 약점을 정확히 쥐고 있다.

## 연구소의 약점 — "한 번 돌았던 노트북"

연구소의 대표 산출물은 Jupyter 노트북이다. 코드, 설명, 결과를 한 문서에 담고 공유하기 좋다. 그런데 **다시 돌려도 같은 결과가 나올까?**

이 질문에 숫자로 답한 연구가 있다. Pimentel 외, [「A Large-scale Study about Quality and Reproducibility of Jupyter Notebooks」](https://leomurta.github.io/papers/pimentel2019a.pdf)(MSR 2019)는
GitHub 의 노트북 140만 개를 분석했다. 실행 순서와 Python 버전이 명확한 노트북 **863,878개를 실제로 돌려 본 결과**는 이랬다.

- 오류 없이 끝까지 실행된 것: **24.11%**
- 원래와 **같은 결과**를 낸 것: **4.03%**

연구소의 결과물 상당수는 "그때 그 사람의 그 컴퓨터에서 한 번 돌았던 기록"이다. 셀을 위아래로 오가며 실행한 순서, 기록되지 않은 패키지 버전,
로컬에만 있던 데이터 파일이 결과의 일부가 된다. **공장이 수십 년 동안 다듬어 온 재현성 습관이 연구소에는 없다.**

## 공장의 약점 — 틀려도 되는 공간이 없다

반대로 공장은 탐색에 서투르다. 모든 변경이 티켓, 리뷰, 배포 절차를 거친다. 안정성에는 좋지만, "이게 될까?"를 하루 만에 확인해 볼 공간이 없다.
그리고 [1편]({% post_url 2026-10-02-communication-and-the-java-factory %})에서 말한 습관, 정해진 걸 질문 없이 끝까지 만드는 습관은 **명세 자체가 틀렸을 가능성**을 다루지 못한다.

연구소는 처음부터 "틀릴 수 있다"를 전제로 일한다. 가설을 세우고, 실험하고, 버린다.
[2편]({% post_url 2026-10-02-java-factory-trust-passion-and-the-managers-job %})에서 말한 "더 빨리 틀리기"를 연구소는 원래 하고 있다.
**공장에 없는 건 이 '틀려도 되는 공간'이다.**

## 진짜 문제는 둘 사이의 복도

회사 안에는 대개 둘 다 있다. 데이터·AI 팀은 연구소처럼 일하고, 서비스 개발팀은 공장처럼 일한다.
사고는 **연구소의 결과물이 공장으로 넘어가는 복도**에서 난다.

Google 의 Sculley 외 [「Hidden Technical Debt in Machine Learning Systems」](https://papers.nips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html)(NeurIPS 2015)는
이 복도의 비용을 정면으로 다룬다. 논문 초록의 표현으로는, ML 이 주는 빠른 성과를 **공짜로 여기는 건 위험하며**, 실제 ML 시스템에는
**막대한 유지보수 비용이 지속적으로 쌓이는 경우가 흔하다.** 논문이 꼽는 위험 요인에는 경계 침식(boundary erosion), 얽힘(entanglement),
숨은 피드백 루프, **선언되지 않은 소비자(undeclared consumers)**, 데이터 의존성 같은 것들이 있다.

이 목록을 다시 읽어 보면 대부분이 기술 문제이기 전에 **소통 문제**다.

- "선언되지 않은 소비자" — 연구소의 결과를 공장의 누가 쓰고 있는지 **아무도 말하지 않았다.**
- "데이터 의존성" — 이 모델이 어떤 데이터를 전제로 하는지 **문서로 넘어가지 않았다.**
- "경계 침식" — 어디까지가 연구소의 책임이고 어디부터가 공장의 책임인지 **합의한 적이 없다.**

콘웨이의 법칙대로, 두 팀 사이에 대화가 없으면 두 시스템 사이에도 계약이 없다.

## 우리 집에서도 일어난 일

이건 남의 이야기만이 아니다. 내 홈랩에서 돌아가는 보안 에이전트 **파수꾼**은 연구소식으로 만들어졌다. Python 으로 빠르게 실험하고, 하루에도 여러 번 고친다.
그런데 그게 돌아가는 곳은 공장이다. GitOps(ArgoCD), 런타임 탐지(Falco), 배포 전략까지 정해진 쿠버네티스 클러스터다.

어느 새벽, 새 버전에 import 가 하나 추가됐는데 그 파일이 배포 묶음에서 빠졌고, 파수꾼은 기동하자마자 죽었다.
연구소의 속도로 고친 코드가 공장의 배포 경로를 거치면서 생긴 사고였다
([에이전트 협업 글]({% post_url 2026-09-24-agent-collaboration-field-notes %})).

반대 방향의 다리도 있다. 최근에 써 본 [Spicycrab]({% post_url 2026-10-02-spicycrab-python-to-rust-transpiler-hands-on %})은
Python 코드를 Rust 로 바꿔 성능을 얻으려는 도구다. 연구소의 언어로 쓰고 공장의 성능을 얻겠다는 시도다.
하지만 직접 돌려 보니 "변환 성공"과 "같은 동작" 사이에 간극이 있었다. **복도는 도구 하나로 사라지지 않는다.**

## 서로에게서 빌려 올 것

**연구소가 공장에서 빌려 올 것**

- 노트북을 위에서부터 한 번에 다시 실행해서 같은 결과가 나오는지 확인한다(위 연구의 4% 안에 들기).
- 패키지 버전과 데이터 출처를 고정하고 적는다.
- 넘길 때는 노트북이 아니라 **입력·출력이 정해진 함수와 테스트**로 넘긴다.

**공장이 연구소에서 빌려 올 것**

- 운영과 분리된 **실험 공간**(스파이크, 프로토타입 브랜치)을 공식적으로 둔다. 거기서는 틀려도 된다.
- "왜 이렇게 했는지"뿐 아니라 **"무엇을 시도했다가 버렸는지"**도 적는다. 연구 노트처럼.
- 명세도 가설이라는 걸 인정한다. 그래서 만들기 전에 묻는다.

**복도에 둘 것**

- 넘기는 쪽과 받는 쪽이 함께 쓰는 **계약**: 입력 데이터의 전제, 출력의 의미, 실패했을 때의 동작, 누가 소비하는지.
- 그리고 그 계약을 대신 써 줄 수는 없어도 쓰게 만들 수는 있는 사람, [2편]({% post_url 2026-10-02-java-factory-trust-passion-and-the-managers-job %})의 **번역하는 관리자**.

## 정리

자바공장은 **재현하는 법**을 안다. 파이썬연구소는 **틀려도 되는 법**을 안다. 어느 쪽도 상대를 비웃을 처지가 아니다.
연구소의 노트북 넷 중 셋은 다시 돌지 않고, 공장의 명세는 종종 처음부터 틀려 있다.

좋은 팀은 둘 중 하나를 고르지 않는다. **둘 사이의 복도에 불을 켠다.** 그 불은 결국 대화이고, 대화가 굳으면 계약이 된다.

## References

- J. F. Pimentel, L. Murta, V. Braganholo, J. Freire, *A Large-scale Study about Quality and Reproducibility of Jupyter Notebooks*, MSR 2019 — <https://leomurta.github.io/papers/pimentel2019a.pdf>
- D. Sculley et al., *Hidden Technical Debt in Machine Learning Systems*, NeurIPS 2015 — <https://papers.nips.cc/paper_files/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html>
- Melvin E. Conway, *How Do Committees Invent?*, Datamation, April 1968 — <http://www.melconway.com/Home/Committees_Paper.html>
