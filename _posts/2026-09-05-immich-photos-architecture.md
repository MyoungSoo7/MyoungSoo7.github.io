---
layout: post
title: "photos.lemuel.co.kr로 보는 Immich 사진 플랫폼의 작동원리와 구조"
date: 2026-09-05 05:35:00 +0900
categories: [AI, Infrastructure, Media]
tags: [Immich, 사진관리, Kubernetes, PostgreSQL, Redis, Machine Learning]
---

`photos.lemuel.co.kr`은 자체 호스팅 사진·동영상 백업 서비스인 **Immich**에 연결된 개인 미디어 플랫폼이다. 현재 공개 접속 화면은 Immich 로그인 페이지이며, 클러스터 구성과 공식 문서를 함께 보면 이 서비스는 단순한 파일 업로드 화면이 아니라 웹·모바일 클라이언트, API 서버, 작업 큐, 데이터베이스, 미디어 저장소, 머신러닝 서비스가 결합된 시스템이다.[1][2]

이 글에서는 공개된 현재 접속 화면, 배포 구성, Immich 공식 아키텍처 문서를 근거로 작동원리와 운영 구조를 설명한다.

## 1. 전체 처리 흐름

사진 한 장을 모바일 앱이나 웹에서 올리면 대략 다음 경로를 거친다.

```text
웹/모바일 클라이언트
  ↓ HTTPS
Immich Server(API + Web UI)
  ├─ 파일을 미디어 라이브러리에 저장
  ├─ 메타데이터·권한·앨범 정보를 PostgreSQL에 기록
  └─ 후속 작업을 Redis 큐에 등록
          ↓
Immich Microservices
  ├─ 썸네일 생성
  ├─ EXIF·미디어 정보 처리
  ├─ 검색용 분석 작업
  └─ 머신러닝 요청
          ↓
Immich Machine Learning
  ├─ 얼굴 인식
  ├─ 객체·이미지 분석
  └─ smart search용 임베딩·분류
```

Immich 공식 문서는 전통적인 client-server 구조와 전용 데이터베이스를 사용한다고 설명한다. 서버는 Redis, PostgreSQL, 머신러닝 서비스, 파일 시스템과 repository interface를 통해 통신하며, API 요청을 처리하는 `immich-server`와 Redis 작업을 처리하는 `immich-microservices`가 분리되어 있다.[2]

## 2. 현재 Lemuel 배포 구조

현재 GitOps 구성에서 `photos.lemuel.co.kr`은 `immich-prod` 네임스페이스의 `immich-server` 서비스로 연결된다. 배포 구성은 다음 네 가지 컴포넌트로 나뉜다.

| 컴포넌트 | 역할 | 현재 구성 |
| --- | --- | --- |
| immich-server | 메인 API와 웹 UI | 포트 2283, NodePort 30054 |
| immich-machine-learning | 얼굴 인식·객체 탐지·smart search | CPU 기반, worker 1개 |
| PostgreSQL | 사용자·권한·앨범·asset·설정·벡터 검색 데이터 | pgvector 포함 이미지 |
| Redis/Valkey | 백그라운드 작업 큐·작업 상태 전달 | Valkey 8 Alpine |

배포 설정상 네 컴포넌트는 `isagal` 노드에 배치되도록 지정되어 있다. 사진 라이브러리는 100Gi, 머신러닝 모델 캐시는 10Gi, PostgreSQL 영속 볼륨은 10Gi로 설정되어 있다. 이 값은 배포 구성의 용량 계획이지, 현재 실제 사용량이나 남은 공간을 뜻하지 않는다.

## 3. 서버와 백그라운드 작업의 분리

사진 업로드 요청에서 사용자가 기다려야 하는 API 응답과 시간이 오래 걸리는 후속 처리를 분리하는 것이 핵심이다.

```text
동기 경로:
  로그인·업로드·앨범·검색 요청
  → Immich Server
  → 빠른 API 응답

비동기 경로:
  썸네일·EXIF·얼굴·객체·임베딩 분석
  → Redis 작업 큐
  → Microservices
  → 필요 시 Machine Learning 호출
```

이 분리의 장점은 대용량 사진을 올릴 때 웹 요청이 이미지 분석 시간만큼 붙잡히지 않는다는 점이다. 반면 Redis 큐가 정체되거나 머신러닝 서비스가 느리면 업로드는 끝났지만 검색·얼굴 분류·썸네일 처리가 늦게 완료될 수 있다.

Immich 문서에 따르면 머신러닝 서비스는 Python과 FastAPI로 작성되며, 각 요청에는 작업 종류와 모델 정보 등이 전달된다. 모델은 요청을 처리하기 위해 다운로드·로드·설정되고, 로드된 모델은 이후 요청에서 재사용되도록 캐시된다. 모델 형식은 ONNX다.[2]

## 4. PostgreSQL과 pgvector가 필요한 이유

Immich의 PostgreSQL에는 다음과 같은 시스템 정보가 저장된다.

```text
사용자·인증·권한
앨범과 공유 설정
사진·동영상 asset 메타데이터
시스템 설정
검색·분석 관련 데이터
```

원본 사진과 동영상 자체는 미디어 라이브러리에 저장되지만, 그 파일을 누가 소유하고 어떤 앨범에 속하는지, 어떤 분석 작업이 끝났는지는 데이터베이스가 관리한다. 그래서 데이터베이스와 미디어 파일 중 하나만 복구하면 완전한 사진 서비스 복구가 되지 않는다.

현재 배포는 PostgreSQL에 pgvector가 포함된 이미지를 사용한다. 이 구조는 이미지·텍스트 표현을 벡터로 저장하거나 검색하는 기능과 연결될 수 있다. 다만 “smart search가 실제로 어떤 모델과 색인 상태로 동작 중인가”는 로그인 후 설정·작업 상태를 확인해야 하며, 배포 파일만으로 현재 분석 완료율을 단정할 수 없다.

## 5. 사진 검색은 무엇을 검색하는가

사진 검색은 하나의 기능처럼 보이지만 내부적으로는 여러 층이 결합된다.

```text
파일 검색:
  라이브러리 경로와 asset 메타데이터

시간·장소 검색:
  촬영 시각·GPS·EXIF 메타데이터

얼굴 검색:
  얼굴 검출·특징 벡터·사람 그룹화

내용 검색:
  머신러닝 분석·임베딩·벡터 유사도
```

따라서 사진을 업로드했다고 즉시 모든 검색 기능이 완성되는 것은 아니다. 원본 저장은 먼저 끝나도, EXIF 처리·썸네일·얼굴 인식·smart search용 분석은 백그라운드 작업으로 나중에 완료될 수 있다. 검색 품질은 모델뿐 아니라 사진 해상도, 조명, 중복 사진, EXIF 보존 여부, 분석 작업의 성공 여부에도 영향을 받는다.

## 6. 중복 업로드와 무결성

사진 백업 서비스에서 중요한 것은 같은 파일을 여러 번 올렸을 때 라이브러리가 불필요하게 커지지 않는 것이다. Immich의 클라이언트·서버는 업로드 시 파일 식별과 asset 정보를 관리하고, 운영 자동화에서는 체크섬 기반 중복 응답을 별도로 확인하도록 구성되어 있다.

다만 다음은 서로 구분해야 한다.

```text
파일 중복 방지:
  같은 미디어가 실제로 다시 저장되는가

앨범 중복:
  같은 파일이 여러 앨범 관계에 표시되는가

업로드 응답:
  API가 created/duplicate를 반환했는가

실제 라이브러리 변화:
  asset 통계가 증가했는가
```

따라서 자동 업로드 결과는 HTTP `201 Created` 개수만 세어 성공으로 판정하면 안 된다. 실제 asset 통계와 대상 앨범·파일을 되읽어야 한다. 특히 여러 작업자가 같은 사진을 서로 다른 앨범 이름으로 처리하면 파일은 중복되지 않아도 앨범 관계가 분산될 수 있다.

## 7. 저장소와 백업의 구조

현재 배포 파일은 사진 라이브러리와 PostgreSQL을 각각 영속 볼륨으로 관리한다. 사진 서비스에서 백업은 다음 세 층을 함께 고려해야 한다.

```text
1. 미디어 원본:
   사진·동영상 파일

2. 데이터베이스:
   사용자·앨범·asset·공유·분석 메타데이터

3. 머신러닝 캐시·설정:
   재생성 가능한 모델·설정·작업 상태
```

보통 모델 캐시는 다시 받을 수 있지만, 미디어 원본과 PostgreSQL은 재생성할 수 없다. 따라서 백업 정책은 “Pod가 살아 있는가”가 아니라 원본과 메타데이터를 함께 복원할 수 있는가를 기준으로 설계해야 한다. 또한 저장소 용량 100Gi는 확장 전 한계이므로 사진 수가 늘면 용량·백업 주기·보존정책을 함께 점검해야 한다.

## 8. 보안 경계

`photos.lemuel.co.kr`은 개인 사진과 동영상을 다루므로 일반 웹 서비스보다 민감도가 높다.

```text
Cloudflare/Ingress:
  외부 접근 경계

Immich 인증:
  사용자·세션·권한 경계

PostgreSQL:
  메타데이터·권한 저장소

미디어 라이브러리:
  원본 파일 저장소

Machine Learning:
  이미지가 분석되는 처리 경계
```

운영 시에는 다음 원칙이 필요하다.

- Cloudflare Access와 Immich 계정의 역할을 혼동하지 않는다.
- API key·비밀번호·세션 쿠키를 URL이나 로그에 남기지 않는다.
- 외부 공유 링크와 개인 라이브러리 권한을 별도로 점검한다.
- 머신러닝 분석 대상과 보존 기간을 확인한다.
- 백업 파일에도 원본 사진과 개인정보가 포함된다는 점을 전제로 암호화·접근통제를 적용한다.

## 9. 현재 확인된 것과 확인하지 않은 것

### 확인됨

```text
photos.lemuel.co.kr 공개 화면:
  Immich 로그인 페이지 응답

배포 구조:
  server·machine learning·PostgreSQL·Redis/Valkey 4컴포넌트

설정된 저장 용량:
  library 100Gi, ML cache 10Gi, PostgreSQL 10Gi

공식 구조:
  client-server + database + microservices + ML
```

### 아직 확인하지 않음

```text
실제 로그인 계정의 사진 수
실제 라이브러리 사용량
백그라운드 작업 대기열
얼굴·객체·smart search 분석 완료율
실제 백업 복원 테스트 결과
현재 외부 공유 링크 목록
```

로그인 페이지가 HTTP 200으로 나온다는 사실만으로 사진 저장·검색·백업이 정상이라고 판단할 수 없다. 운영 상태는 별도의 인증된 조회와 통계·작업·복원 테스트로 확인해야 한다.

## 결론

`photos.lemuel.co.kr`은 Immich를 기반으로 한 자체 호스팅 사진·동영상 플랫폼이다. 작동원리는 다음 한 줄로 요약할 수 있다.

```text
미디어 업로드
  → Server가 파일·메타데이터를 접수
  → PostgreSQL이 권한·asset 정보를 관리
  → Redis가 후속 작업을 전달
  → Microservices와 Machine Learning이 분석
  → 썸네일·얼굴·객체·smart search 결과를 제공
```

이 구조의 핵심은 사진 파일만 저장하는 것이 아니라 **파일, 메타데이터, 비동기 작업, 분석 모델, 권한을 하나의 일관된 시스템으로 운영하는 것**이다. 개인 사진 백업의 품질은 UI의 편리함보다 원본 보존, 데이터베이스 복구, 분석 상태, 중복 처리, 접근통제와 복원 검증에 의해 결정된다.

## References

[1] [Lemuel Photos — Immich 로그인 화면](https://photos.lemuel.co.kr/)

[2] [Immich Architecture — Official Documentation](https://docs.immich.app/developer/architecture)

[3] [Immich Environment Variables — Official Documentation](https://docs.immich.app/install/environment-variables)

*이 글의 Lemuel 배포 구성은 공개된 GitOps 설정을 기준으로 분석했으며, 로그인 계정 내부의 실제 사진 수·작업 큐·검색 인덱스·백업 복원 결과를 확인했다고 주장하지 않는다. 공개 URL의 로그인 화면과 배포 설정은 운영 데이터의 정상성을 보증하지 않는다.*
