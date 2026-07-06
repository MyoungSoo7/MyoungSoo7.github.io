---
layout: post
title: "주니어 RFC vs 시니어 RFC — 같은 기능, 다른 *문서*"
date: 2026-07-07 11:00:00 +0900
categories: [backend, architecture, communication]
tags: [rfc, design-decision, communication, junior-vs-senior, trade-off, documentation]
image: /assets/images/communication/junior-vs-senior-rfc.jpg
---

같은 기능 을 설계 했다. **파일 업로드** — POST 엔드포인트 하나, S3 저장, DB 메타, URL 반환. 코드 로 짜면 비슷 하다. 근데 RFC 는 *완전히 다르다*.

![주니어 RFC "구현 노트" vs 시니어 RFC "결정의 기록"](/assets/images/communication/junior-vs-senior-rfc.jpg)

---

## 두 RFC 나란히

왼쪽 이 주니어 RFC, 오른쪽 이 시니어 RFC 다. *같은 파일 업로드* 를 설계 했다.

### 주니어 RFC — "구현 노트"

```
## Design
- POST /files 엔드포인트 추가
- multipart/form-data 받기
- S3에 저장
- DB에 메타 저장
- 응답에 url 반환

## API
POST /files
- file: multipart
- response: { id, url }

## DB
files 테이블 추가
- id, user_id, url, size, created_at
```

*"이제 전부. 읽는 사람은 '그래서 왜?' 를 5번 묻는다."*

**결과:** S3 버킷 IAM 잘못 설정 가능성 노출, 동영상 허용 여부 모호, 롤백 절차 없음.

---

### 시니어 RFC — "결정의 기록"

```
## Context
CS팀이 이미지 첨부를 이메일로 올기는 데 주당 4h 씀.
하루 ~200건, 한 건 평균 3MB.

## Goals / Non-goals
- DO: 단일 이미지 업로드 + 단용 URL
- DON'T: 동영상, 폴더, 공유 권한

## Trade-offs
S3 직접 업로드(presigned)로 갑니다.
서버 거치는 대안보다 코드 배줄 ↑,
대신 서버 대역폭/메모리 안전.

## Alternatives
A. 서버 프록시 – 단순, 트래픽 위험
B. presigned URL – 채택
C. CDN 업로드 – 비용 과다

## Risks / Rollback
S3 IAM 잘못 설정 시 공개 노출 위험.
첫 주 access log 모니터.
롤백: 엔드포인트 비활성, DB 보존.
```

**결과:** 리뷰에서 IAM 정책 검토 요구가 나옴 → 사전 보안 검토 → 사고 0건으로 출시.

---

## 차이의 해부

두 RFC 의 차이 를 섹션 단위 로 뜯어보면:

| 섹션 | 주니어 | 시니어 |
|------|--------|--------|
| **배경** | 없음 | CS팀 주당 4h 낭비, 하루 200건 |
| **목표** | 없음 | 이미지만, URL 반환만 (동영상 NO) |
| **선택지** | 없음 | A/B/C 비교, 채택 이유 명시 |
| **트레이드오프** | 없음 | presigned vs 서버 프록시 vs CDN |
| **위험** | 없음 (숨어있음) | IAM 노출 명시 + 대응 + 롤백 |

주니어 RFC 는 *"뭘 만드나"* 를 담았다. 시니어 RFC 는 *"왜 이걸 만드나"* + *"왜 이렇게 만드나"* + *"뭐가 터질 수 있나"* 를 담았다.

---

## 주니어 RFC 의 진짜 문제

주니어 RFC 가 나쁜 건 *정보 가 부족해서* 가 아니다. **읽는 사람 이 혼자 질문 을 메꿔야 한다** 는 게 문제 다.

팀원 이 리뷰 하면서 **이 5가지 를 스스로 물어야** 한다:

1. *왜 지금 이걸?* — 배경 없음
2. *동영상 은 되나?* — 범위 불명확
3. *서버 거치면 안 되나?* — presigned 선택 이유 없음
4. *IAM 잘못 설정 하면?* — 리스크 없음
5. *잘못되면 어떻게 되돌려?* — 롤백 없음

이 질문 들 이 리뷰 에서 터지면, 리뷰 가 *"검토"* 가 아니라 *"인터뷰"* 가 된다. 시간 낭비 고, 신뢰 손실 이다.

---

## 시니어 RFC 가 리뷰 를 바꾸는 방법

시니어 RFC 는 저 5가지 를 *문서 안 에 먼저 답해 놓는다*. 그러면 리뷰어 가 할 일 이 달라진다:

- **주니어 RFC 리뷰어:** *"왜 presigned 인가요? IAM 은요? 동영상 은요?"* → 설계자 를 붙잡고 앉아야 함
- **시니어 RFC 리뷰어:** *"IAM 정책 은 Bucket Policy 로 할지 IAM Role 로 할지 방향 도 적어주면 좋겠네요"* → 진짜 검토

시니어 RFC 의 IAM Risks 섹션 하나 가 *"리뷰에서 IAM 정책 검토 요구 → 사전 보안 검토 → 사고 0건"* 을 만들었다. 주니어 RFC 의 결과 는 *"S3 버킷 IAM 잘못 설정 가능성, 동영상 모호, 롤백 없음"* 이었다.

---

## 핵심 한 줄

> **주니어 RFC 는 *구현 노트* 고, 시니어 RFC 는 *결정 의 기록* 이다.**

구현 노트 는 *"이렇게 짜겠다"* 를 담는다. 결정 의 기록 은 *"왜 이렇게 짜는지, 뭘 버렸는지, 뭐가 위험한지"* 를 담는다. 코드 는 시간 이 지나면 바뀌지만, **결정 의 맥락** 은 바뀌지 않는다. 6개월 뒤 "왜 이렇게 했지?" 에 답 하는 건 코드 가 아니라 RFC 다.

---

_관련: [RFC 템플릿 — 설계 결정을 한 장에 담는 법]({% post_url 2026-07-07-rfc-template-one-pager-design-decision %})_
