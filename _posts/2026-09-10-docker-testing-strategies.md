---
layout: post
title: "Docker로 다양한 테스트하기: 컨테이너·통합 테스트·빌드 검증을 하나의 흐름으로"
date: 2026-09-10 22:50:34 +0900
categories: [DevOps, Testing]
tags: [Docker, Testcontainers, Integration Test, CI/CD, Spring Boot, Docker Compose]
---

# Docker로 다양한 테스트하기

Docker는 애플리케이션을 실행하는 포장 도구로만 쓰이지 않는다. 개발·테스트·CI 환경에서 데이터베이스, 메시지 브로커, 외부 API 대체 서버, 애플리케이션 이미지까지 격리해 반복 가능한 검증 환경을 만들 수 있다.

핵심은 “Docker로 테스트한다”가 아니라, **어떤 불확실성을 어떤 테스트 계층에서 줄일 것인가**를 정하는 것이다.

```text
정적 검증       → Dockerfile·build 설정·secret 노출
단위 테스트     → 함수·도메인 로직
컴포넌트 테스트 → 애플리케이션 경계
통합 테스트     → 실제 DB·브로커·검색엔진
E2E 테스트      → 실행 중인 컨테이너와 API 흐름
운영 유사 검증  → 이미지·네트워크·healthcheck·배포 설정
```

Docker 공식 문서는 Testcontainers를 Docker 컨테이너 안에서 실제 서비스를 띄워 테스트 의존성으로 사용하는 라이브러리 모음으로 설명한다.[1] Testcontainers의 목적은 mock이나 in-memory 대체물만 사용하는 대신, 운영에서 사용하는 종류의 서비스와 통합 동작을 검증하는 것이다.[4]

## 1. 테스트 피라미드와 Docker의 위치

### 단위 테스트

가장 빠른 계층이다.

- 순수 함수
- 도메인 규칙
- validation
- 상태 전이
- 예외 처리

Docker가 필요하지 않은 테스트까지 컨테이너에서 실행하면 피드백이 느려진다.

### 통합 테스트

실제 PostgreSQL, Redis, Kafka, Elasticsearch 등을 연결해 다음을 검증한다.

- SQL 문법과 실제 DB dialect
- transaction과 isolation
- index·constraint·migration
- serialization
- consumer·producer 계약
- 외부 시스템 timeout과 retry

### E2E 테스트

API gateway 또는 실제 애플리케이션 컨테이너를 띄우고 사용자의 흐름을 검증한다.

```text
HTTP client
   ↓
API container
   ↓
PostgreSQL container
   ↓
Kafka / Redis / external stub containers
```

E2E는 가치가 크지만 느리고 실패 원인 범위가 넓다. 따라서 모든 조건을 E2E 하나로 해결하지 말고, 실패 원인을 좁힐 수 있도록 단위·통합 테스트와 함께 운영한다.

## 2. Dockerfile 자체를 테스트하기

이미지를 빌드할 수 있다는 것과 안전하고 운영 가능한 이미지라는 것은 다르다.

### Docker build check

Docker Build checks는 Dockerfile과 build option을 실제 빌드 전에 검사하는 linting·dry-run 계층이다. `docker build --check .`로 빌드 실행 없이 설정 문제를 확인할 수 있고, check 위반을 오류로 승격할 수도 있다.[2]

```bash
docker buildx build --check .
```

Dockerfile에서 검사 실패를 빌드 실패로 만들려면 다음과 같이 사용할 수 있다.

```dockerfile
# syntax=docker/dockerfile:1
# check=error=true

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY build/libs/app.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
```

대표적으로 확인할 항목:

- shell form `CMD`·`ENTRYPOINT`로 인한 signal 처리 문제
- 잘못된 `FROM`·platform 설정
- 불필요한 build context
- stage 이름과 layer 구성
- secret을 `ARG`나 `ENV`로 전달하는 위험
- root 사용자 실행
- 과도하게 큰 이미지

### 이미지 정적 검사

```bash
docker build -t shop-api:test .
docker inspect shop-api:test
# 조직 표준에 맞는 이미지 취약점 스캐너 실행
```

검증할 내용:

- 예상한 base image와 digest인가
- 실행 사용자가 non-root인가
- debug 도구·compiler가 runtime image에 남지 않았는가
- secret·token·private key가 layer에 남지 않았는가
- healthcheck가 존재하고 의미가 맞는가
- 포트·환경변수·entrypoint가 기대와 같은가

## 3. Docker Compose로 다중 서비스 테스트

Compose는 로컬에서 API와 의존 서비스를 한 번에 구성할 때 유용하다.

```yaml
services:
  api:
    build: .
    environment:
      DATABASE_URL: postgres://app:app@postgres:5432/app
      REDIS_URL: redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
```

실행 예:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --no-color api
docker compose run --rm api ./gradlew test
docker compose down -v
```

### Compose 테스트에서 주의할 점

`depends_on`은 컨테이너 시작 순서를 도와줄 뿐 애플리케이션이 모든 준비를 마쳤다는 뜻은 아니다. healthcheck, 애플리케이션 retry, 명시적인 readiness 확인을 함께 사용해야 한다.

또한 테스트가 끝난 뒤 volume과 network를 정리하지 않으면 다음 실행에 이전 데이터가 남는다. 재현성이 필요하면 ephemeral volume과 고유 project name을 사용하고, 테스트 종료 시 정리 결과를 확인한다.

## 4. Testcontainers로 실제 DB 테스트하기

Testcontainers는 테스트 코드가 필요한 시점에 PostgreSQL 같은 실제 서비스를 Docker 컨테이너로 시작하고, 테스트가 끝나면 정리하는 방식이다. 사전 구축된 공용 통합 테스트 환경 없이도 각 테스트 실행이 독립된 의존성을 가질 수 있다.[1][4]

### Spring Boot + PostgreSQL 예시

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class CustomerApiTest {

    @Container
    static PostgreSQLContainer<?> postgres =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Test
    void createsAndReadsCustomer() {
        // 실제 PostgreSQL에 migration과 API를 연결해 검증
    }
}
```

Docker 공식 Spring Boot REST API 가이드는 Spring Data JPA와 PostgreSQL을 연결하고, Testcontainers로 PostgreSQL을 띄운 뒤 `@DynamicPropertySource`로 Spring datasource 속성을 주입하는 흐름을 보여준다.[3]

### Testcontainers가 해결하는 문제

- H2와 PostgreSQL dialect 차이
- 개발자별 로컬 DB 상태 차이
- 공유 테스트 DB의 데이터 오염
- CI에서 사전 DB 설치 필요성
- migration·constraint·index의 실제 동작 미검증

Testcontainers가 모든 문제를 해결하는 것은 아니다. Docker runtime 의존성, image pull 시간, resource 사용량, parallel 실행 격리, 테스트 데이터 초기화 전략을 함께 관리해야 한다.

## 5. 다양한 의존성 테스트

### PostgreSQL·MySQL

- schema migration
- unique constraint
- transaction rollback
- isolation level
- pagination·sorting
- query plan과 index

### Redis

- TTL
- cache miss/hit
- serialization
- distributed lock
- 장애 시 fallback

### Kafka

- producer serialization
- consumer group
- offset commit
- retry와 dead-letter topic
- 중복 이벤트 처리
- 순서 보장 범위

### Elasticsearch

- index mapping
- analyzer
- refresh 정책
- query 결과
- bulk indexing 오류
- mapping conflict

### 외부 API

MockServer·WireMock 같은 컨테이너를 사용해 다음을 재현할 수 있다.

- 정상 응답
- timeout
- 429 rate limit
- 500·502
- malformed JSON
- 느린 응답
- 중복 응답
- TLS·인증 실패

중요한 것은 “외부 API가 성공한다”만 테스트하지 않는 것이다. 실패·재시도·보상·timeout·부분 성공이 실제 운영에서 더 위험한 경로다.

## 6. 이미지 자체를 대상으로 하는 테스트

애플리케이션 소스 테스트와 최종 이미지 테스트는 다르다.

```bash
docker build -t api:test .
docker run -d --name api-test -p 18080:8080 api:test

curl --fail --retry 10 --retry-delay 1 http://localhost:18080/actuator/health
curl --fail http://localhost:18080/api/health

docker inspect api-test
docker logs api-test
docker rm -f api-test
```

검증 항목:

- 이미지가 실제 runtime에서 부팅되는가
- 환경변수가 없는 경우 안전하게 실패하는가
- health endpoint가 실제 의존성 상태를 정확히 반영하는가
- graceful shutdown이 동작하는가
- non-root user로 파일 권한이 충분한가
- 잘못된 설정에서 민감한 값이 로그에 나오지 않는가

### Healthcheck의 함정

프로세스가 살아 있다는 것은 HTTP API가 정상이라는 뜻이 아닐 수 있다. 반대로 DB가 일시적으로 지연된다고 컨테이너를 무조건 재시작하면 장애를 증폭시킬 수 있다. liveness, readiness, startup health의 목적을 분리한다.

## 7. 네트워크와 장애 주입 테스트

Docker network를 이용하면 서비스 간 연결을 실제처럼 시험할 수 있다.

```bash
docker network create test-net
docker run -d --network test-net --name db postgres:16
docker run --rm --network test-net api:test
```

검증할 장애:

- DB connection refused
- DNS 이름 해석 실패
- 네트워크 지연
- 응답 중단
- connection pool 고갈
- 브로커 재시작
- upstream 503
- 잘못된 TLS 인증서

장애 주입은 개발·CI 전용 격리 환경에서 수행한다. 운영 네트워크나 실제 고객 데이터에 임의로 장애를 주입해서는 안 된다.

## 8. CI/CD에 Docker 테스트 넣기

권장 파이프라인:

```text
1. format / lint
2. unit test
3. docker build --check
4. application image build
5. image scan
6. Testcontainers integration test
7. container smoke test
8. E2E test
9. SBOM·signature·artifact 검증
10. 배포 전 승인
```

GitHub Actions 개념 예:

```yaml
- name: Docker build checks
  run: docker buildx build --check .

- name: Unit tests
  run: ./gradlew test

- name: Integration tests
  run: ./gradlew integrationTest

- name: Build image
  run: docker build -t app:${{ github.sha }} .

- name: Smoke test
  run: ./scripts/smoke-test.sh
```

Testcontainers 테스트는 Docker API에 접근할 수 있는 CI runner가 필요하다. 이미지 캐시·registry rate limit·parallel 실행 수·cleanup 실패를 CI 운영 항목으로 관리해야 한다.[1]

## 9. 무엇을 Docker로 테스트하고 무엇을 하지 않을까

### Docker가 적합한 영역

- 실제 DB·브로커·검색엔진 통합
- 최종 runtime image
- 네트워크·서비스 discovery
- migration과 schema
- 외부 API 실패 시나리오
- 동일 의존성의 개발·CI 환경 재현

### Docker가 과한 영역

- 순수 함수
- 간단한 DTO 변환
- 빠른 validation 단위 테스트
- 매 commit마다 실행하는 수천 개의 초고속 테스트
- Docker와 무관한 알고리즘 테스트

최적의 구조는 모든 테스트를 컨테이너화하는 것이 아니라, **실제 외부 의존성이 필요한 경계만 컨테이너로 격리하는 것**이다.

## 10. 흔한 실패 패턴

### H2만 쓰고 PostgreSQL이라고 믿기

in-memory DB가 빠르다는 이유로 실제 DB dialect·constraint·index·migration 차이를 확인하지 않으면 배포 후 실패할 수 있다.

### `Running`만 보고 테스트 통과 판정

컨테이너가 Running이어도 API가 준비되지 않았거나 DB migration이 실패했을 수 있다. health endpoint와 실제 API 요청을 검증한다.

### `depends_on`만 믿기

프로세스 시작 순서와 서비스 readiness는 다르다. healthcheck와 애플리케이션 retry를 함께 둔다.

### 테스트 환경을 공유하기

여러 pipeline이 같은 DB를 쓰면 데이터 오염과 flaky test가 발생한다. 실행별 격리된 컨테이너와 cleanup을 사용한다.

### 이미지 build 성공을 배포 성공으로 착각

이미지 build·push만으로 운영 반영을 주장하지 않는다. 배포된 digest, readiness, smoke test, 실제 endpoint를 확인한다.

### 테스트 데이터와 로그에 secret 포함

Docker 환경변수·compose 파일·container logs·artifact에 token과 password를 남기지 않는다. 테스트용 credential도 범위를 제한하고 실행 후 폐기한다.

## 결론

Docker로 다양한 테스트를 한다는 것은 컨테이너를 많이 띄우는 일이 아니다. 각 테스트의 목적에 맞는 실제 경계를 재현하고, 테스트가 끝난 뒤 환경을 폐기하며, build·image·runtime·external dependency를 각각 검증하는 일이다.

- 단위 테스트는 빠르게 유지한다.
- Testcontainers로 실제 DB·브로커·검색엔진을 검증한다.
- Compose로 로컬 다중 서비스 시나리오를 재현한다.
- Docker build checks로 Dockerfile을 빌드 전에 검사한다.
- 최종 이미지를 실제로 실행해 health와 API를 확인한다.
- 실패·지연·timeout·retry·중복 처리까지 테스트한다.
- CI에서는 artifact digest와 배포된 runtime까지 확인한다.

테스트의 목적은 “컨테이너가 떴다”를 증명하는 것이 아니라, **실제 운영 환경에서 발생할 경계 조건과 실패를 배포 전에 발견하는 것**이다.

## 참고 자료

[1] Docker Docs, Testcontainers — 실제 서비스 기반 통합 테스트  
[2] Docker Docs, Build Checks — Dockerfile·build 설정 사전 검증  
[3] Docker Docs, Testing Spring Boot REST API with Testcontainers  
[4] Testcontainers, Introducing Testcontainers — 통합 테스트 환경 격리와 lifecycle

## 출처

- Docker Testcontainers: https://docs.docker.com/testcontainers/
- Docker Build Checks: https://docs.docker.com/build/checks/
- Spring Boot REST API Testcontainers: https://docs.docker.com/guides/testcontainers-java-spring-boot-rest-api/
- Introducing Testcontainers: https://testcontainers.com/guides/introducing-testcontainers/

## Sources

[1] https://docs.docker.com/testcontainers — Docker Testcontainers
[2] https://docs.docker.com/build/checks — Docker Build Checks
[3] https://docs.docker.com/guides/testcontainers-java-spring-boot-rest-api — Spring Boot REST API Testcontainers
[4] https://testcontainers.com/guides/introducing-testcontainers — Introducing Testcontainers
