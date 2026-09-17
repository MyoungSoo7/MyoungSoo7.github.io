---
layout: post
title: "로컬 MySQL과 Docker MySQL 비교: 사용법·장단점·테스트 전략"
date: 2026-09-17 19:14:23 +0900
categories: [Database, Docker, Backend]
tags: [MySQL, Docker, Docker Compose, Testcontainers, Database]
---

# 로컬 MySQL과 Docker MySQL 비교

로컬 MySQL과 Docker MySQL은 모두 MySQL 서버를 실행하지만, 설치 위치와 실행 환경의 관리 방식이 다르다.

- 로컬 MySQL: 운영체제에 직접 설치
- Docker MySQL: Docker 컨테이너 안에서 실행

Docker 공식 문서는 컨테이너화된 데이터베이스가 격리된 환경과 재현 가능한 설정을 제공하고, volume으로 데이터를 보존할 수 있다고 설명한다.[1][2]

## 1. 구조 차이

### 로컬 MySQL

```text
Host OS
 └─ MySQL Server
     └─ Database
```

macOS에서는 Homebrew 서비스로 실행할 수 있다.

```bash
brew install mysql
brew services start mysql
mysql -u root -p
```

Linux에서는 systemd 또는 배포판 패키지 관리자로 설치하고 서비스를 관리한다.

### Docker MySQL

```text
Host OS
 └─ Docker Engine
     └─ MySQL Container
         └─ Database
```

```bash
docker run -d \
  --name mysql-dev \
  -e MYSQL_ROOT_PASSWORD='change-me' \
  -e MYSQL_DATABASE=app \
  -p 3306:3306 \
  -v mysql-data:/var/lib/mysql \
  mysql:8.4
```

MySQL 공식 이미지는 `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` 등으로 초기 설정을 받을 수 있다. 단, 이미 데이터 디렉터리에 데이터베이스가 존재하면 초기화 환경변수는 기존 데이터에 다시 적용되지 않는다.[1]

## 2. 연결 주소가 다르다

Docker MySQL을 사용할 때 가장 흔한 오류는 `localhost`의 의미를 혼동하는 것이다.

```text
호스트에서 접근       → localhost:3306
같은 Compose의 app    → mysql:3306
```

Compose 네트워크 안에서 `mysql`은 서비스 이름이다.

```yaml
services:
  app:
    environment:
      DB_HOST: mysql
      DB_PORT: 3306

  mysql:
    image: mysql:8.4
```

컨테이너 내부에서 `localhost:3306`은 MySQL 컨테이너가 아니라 현재 애플리케이션 컨테이너 자신을 가리킨다. Docker 문서도 Compose 네트워크에서 서비스 이름으로 다른 컨테이너를 찾는 방식을 설명한다.[2]

## 3. 한눈에 비교

| 항목 | 로컬 MySQL | Docker MySQL |
|---|---|---|
| 설치 | 운영체제에 직접 설치 | 이미지·컨테이너로 실행 |
| 격리 | 상대적으로 낮음 | 컨테이너 단위 격리 |
| 시작·종료 | OS 서비스 관리 | Docker 명령·Compose |
| 버전 전환 | 설치와 데이터 관리 필요 | image tag 변경 가능 |
| 초기화 | 직접 설정 | 환경변수·Compose로 코드화 |
| 데이터 보존 | 로컬 데이터 디렉터리 | named volume 또는 bind mount |
| 팀 재현성 | 개발자별 차이 발생 가능 | 설정 파일로 통일 가능 |
| 호스트 도구 연결 | `localhost:3306` | 포트 매핑 필요 |
| 성능 경로 | 직접 실행 | Docker 네트워크·스토리지 계층 |
| 테스트 격리 | 별도 DB 준비 필요 | 컨테이너 생성·폐기 가능 |

## 4. 로컬 MySQL의 장점

### 4.1 단순한 성능 경로

MySQL이 운영체제에서 직접 실행되므로 Docker 네트워크나 volume 계층을 거치지 않는다. 대형 dump import, 반복적인 SQL 실행, 로컬 성능 측정에서는 단순한 구성이 장점이 될 수 있다.

### 4.2 도구 연결이 쉽다

IDE, GUI 클라이언트, 로컬 script가 기본적으로 `localhost:3306`에 연결되므로 별도의 컨테이너 네트워크 설정이 적다.

### 4.3 장기간 데이터를 유지하기 쉽다

로컬 개발 데이터를 오래 유지하면서 schema와 데이터를 직접 살펴보는 작업에는 편리하다.

### 4.4 OS 서비스로 자동 시작 가능

macOS Homebrew service나 Linux systemd를 이용하면 운영체제 시작 시 MySQL을 자동으로 올릴 수 있다.

## 5. 로컬 MySQL의 단점

### 5.1 개발자별 환경 차이

다음 설정이 서로 다를 수 있다.

- MySQL 버전
- SQL mode
- 문자셋과 collation
- timezone
- authentication plugin
- 사용자 계정과 권한
- `my.cnf` 설정

그 결과 한 개발자의 로컬에서는 성공하지만 CI나 다른 개발자 환경에서는 실패할 수 있다.

### 5.2 버전 전환이 번거롭다

MySQL 5.7, 8.0, 8.4를 번갈아 테스트하려면 설치된 서비스, 데이터 디렉터리, 포트와 설정을 함께 관리해야 한다.

### 5.3 상태가 테스트를 오염시킬 수 있다

이전 migration, seed data, 사용자 권한과 캐시가 남으면 테스트 결과가 실행 순서에 따라 달라진다.

```text
이미 적용된 migration
오래된 schema
남아 있는 seed data
기존 계정·권한
```

### 5.4 포트와 서비스 충돌

이미 실행 중인 MySQL, MariaDB, 다른 프로젝트가 `3306`을 사용하면 충돌한다.

## 6. Docker MySQL의 장점

### 6.1 버전과 설정을 코드로 통일

```yaml
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: app
      MYSQL_USER: app
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    ports:
      - "3307:3306"
    volumes:
      - mysql-data:/var/lib/mysql

volumes:
  mysql-data:
```

Compose 파일을 공유하면 팀원이 같은 이미지와 기본 구조로 개발을 시작할 수 있다. 비밀번호는 예시처럼 환경변수로 외부화하고 `.env`를 Git에 commit하지 않는다.

### 6.2 프로젝트별 격리

```text
project-a → MySQL 8.0 → host port 3307
project-b → MySQL 8.4 → host port 3308
```

프로젝트별 컨테이너와 volume을 사용하면 호스트의 MySQL 설치를 바꾸지 않고도 여러 버전을 병행할 수 있다.

### 6.3 초기화·삭제·재구성이 쉽다

```bash
docker compose up -d mysql
docker compose logs -f mysql
docker compose down
```

완전 초기화는 다음처럼 할 수 있지만 volume과 데이터가 삭제된다.

```bash
docker compose down -v
docker compose up -d mysql
```

`down -v`는 개발용 disposable 데이터에만 사용하고, 중요한 데이터에는 백업과 복구 확인을 먼저 해야 한다.

### 6.4 CI와 유사한 DB 환경

로컬과 GitHub Actions에서 같은 image tag와 initialization script를 사용할 수 있어 환경 차이를 줄이기 좋다.

### 6.5 Testcontainers와 결합

Testcontainers for Java는 MySQL module로 실제 MySQL 컨테이너를 테스트 코드에서 생성할 수 있다.[4]

```java
MySQLContainer<?> mysql =
        new MySQLContainer<>("mysql:8.0.36");
```

테스트 전용 DB를 만들고 종료 시 폐기하는 방식은 로컬 MySQL의 기존 상태에 덜 의존한다.

## 7. Docker MySQL의 단점

### 7.1 Volume 없이는 데이터가 사라질 수 있다

컨테이너를 제거하면 컨테이너 내부에만 저장한 데이터도 함께 잃을 수 있다.

```bash
docker rm -f mysql-dev
```

개발 데이터를 유지하려면 named volume을 사용한다.

```bash
-v mysql-data:/var/lib/mysql
```

Docker는 MySQL 데이터 디렉터리(`/var/lib/mysql`)를 volume에 연결하는 방식을 공식 예제로 안내한다.[2]

### 7.2 컨테이너 Running과 MySQL Ready는 다르다

```bash
docker ps
```

에서 컨테이너가 `Up`이어도 MySQL 초기화가 끝나 접속을 받을 준비가 됐다는 뜻은 아니다.

잘못된 구성:

```yaml
services:
  app:
    depends_on:
      - mysql
```

Compose의 짧은 `depends_on`은 시작 순서만 표현하고 dependency가 실제로 healthy인지 기다리지 않는다. Docker 문서는 `healthcheck`와 `condition: service_healthy`를 함께 사용해야 readiness를 기다릴 수 있다고 설명한다.[3]

```yaml
services:
  app:
    build: .
    depends_on:
      mysql:
        condition: service_healthy

  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    healthcheck:
      test:
        ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p$${MYSQL_ROOT_PASSWORD}"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 20s
```

애플리케이션에도 연결 retry와 migration 실패 처리를 두는 것이 좋다. healthcheck가 통과해도 실제 schema migration이나 애플리케이션 권한이 정상이라는 뜻은 아니기 때문이다.

### 7.3 Docker Desktop의 I/O 오버헤드

macOS와 Windows의 Docker Desktop은 Linux VM을 거칠 수 있다. MySQL data directory를 호스트 bind mount로 연결하면 파일 I/O가 느려질 수 있다.

일반적으로 다음과 같은 named volume을 먼저 검토한다.

```yaml
volumes:
  - mysql-data:/var/lib/mysql
```

다음처럼 호스트 디렉터리를 직접 bind mount하는 방식은 파일을 쉽게 확인할 수 있지만 성능과 권한을 함께 점검해야 한다.

```yaml
volumes:
  - ./mysql-data:/var/lib/mysql
```

### 7.4 네트워크와 secret 관리가 추가된다

- 호스트 포트와 컨테이너 포트 구분
- Compose 서비스 이름 DNS
- container network
- `.env`와 secret 파일
- root 계정 노출 방지

을 함께 관리해야 한다.

## 8. Docker Compose 사용 예시

```yaml
services:
  app:
    build: .
    environment:
      DB_HOST: mysql
      DB_PORT: 3306
      DB_NAME: app
      DB_USER: app
      DB_PASSWORD: ${MYSQL_PASSWORD}
    depends_on:
      mysql:
        condition: service_healthy

  mysql:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: app
      MYSQL_USER: app
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    ports:
      - "3307:3306"
    volumes:
      - mysql-data:/var/lib/mysql
    healthcheck:
      test:
        ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p$${MYSQL_ROOT_PASSWORD}"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  mysql-data:
```

접속 주소는 실행 위치에 따라 다르다.

```text
Host OS의 GUI client → 127.0.0.1:3307
app container        → mysql:3306
```

포트 매핑의 왼쪽은 호스트 포트이고 오른쪽은 컨테이너 포트다.

## 9. 통합 테스트에서는 Docker가 유리한 이유

통합 테스트는 테스트마다 깨끗한 DB와 명확한 schema가 필요하다.

```text
테스트 시작
  ↓
MySQL 컨테이너 생성
  ↓
schema migration
  ↓
통합 테스트
  ↓
컨테이너 정리
```

Testcontainers Java MySQL module은 다음처럼 사용할 수 있다.[4]

```java
@Testcontainers
class UserRepositoryTest {

    @Container
    static MySQLContainer<?> mysql =
            new MySQLContainer<>("mysql:8.0.36")
                    .withDatabaseName("test")
                    .withUsername("test")
                    .withPassword("test");
}
```

또는 Testcontainers JDBC URL을 사용할 수 있다.

```text
jdbc:tc:mysql:8.0.36:///databasename
```

장점:

- 테스트마다 격리된 DB 사용
- MySQL 버전 명시
- 로컬 DB 상태 의존 감소
- CI와 로컬의 DB 실행 방식 통일
- 테스트 종료 후 cleanup 가능

단점:

- Docker 실행 환경 필요
- 첫 image pull 시간이 추가됨
- CI의 Docker 권한과 image cache 필요
- 컨테이너 startup 시간이 테스트 시간에 포함됨

## 10. 로컬 MySQL과 Docker MySQL 선택 기준

### 로컬 MySQL이 적합한 경우

- 개인 개발 환경이다.
- MySQL 한 버전만 사용한다.
- 대용량 dump와 SQL을 반복 처리한다.
- Docker Desktop의 I/O 성능이 병목이다.
- 애플리케이션도 로컬에서 직접 실행한다.
- 장기간 유지할 개발 데이터가 있다.

### Docker MySQL이 적합한 경우

- 팀 전체의 DB 환경을 통일해야 한다.
- 프로젝트마다 MySQL 버전이 다르다.
- 개발 환경을 빠르게 재생성해야 한다.
- CI에서 동일한 DB를 띄워야 한다.
- 통합 테스트마다 깨끗한 DB가 필요하다.
- 호스트 OS에 DB를 직접 설치하고 싶지 않다.

### 운영 환경

단순히 Docker로 MySQL을 실행한다고 운영에 적합해지는 것은 아니다.

- 영속 volume
- 정기 backup
- 복구 테스트
- replication 또는 고가용성
- slow query·resource monitoring
- 디스크 용량 알림
- credential rotation
- 네트워크 접근 제한
- upgrade·rollback 계획
- 데이터 무결성 검증

을 별도로 설계해야 한다. 개발용 `docker compose up`과 운영용 데이터베이스 플랫폼은 동일한 문제로 취급하면 안 된다.

## 11. 운영에 가까운 최소 원칙

```text
image tag 고정
+ named volume
+ non-root 애플리케이션 계정
+ healthcheck
+ readiness 대기
+ secret 외부화
+ backup·restore 검증
+ 로그·metric 수집
```

다음 구성은 편리하지만 운영 기본값으로 보기 어렵다.

```bash
docker run -d \
  -e MYSQL_ROOT_PASSWORD='secret' \
  -p 3306:3306 \
  mysql:latest
```

문제는 다음과 같다.

- `latest`가 버전 고정이 아님
- root 계정만 사용
- secret이 명령줄·shell history에 노출될 수 있음
- backup과 restore 정책이 없음
- healthcheck와 resource limit이 없음
- 데이터 보존·복구 경로가 불명확함

## 결론

```text
로컬 MySQL:
  빠르고 단순함
  장기 개발 데이터와 대용량 SQL 작업에 편리함
  환경 재현성과 격리는 약할 수 있음

Docker MySQL:
  버전·설정·초기화를 통일하기 좋음
  팀 개발·CI·통합 테스트에 유리함
  volume·readiness·네트워크·Docker 성능을 관리해야 함
```

선택 기준은 다음과 같이 정리할 수 있다.

```text
개인 장기 개발 + 단일 버전:
  로컬 MySQL

팀 개발 + 프로젝트 격리:
  Docker MySQL

통합 테스트:
  Testcontainers 또는 Docker Compose

대용량 로컬 SQL 작업:
  로컬 MySQL 또는 Docker named volume을 실측 비교

운영:
  백업·복구·모니터링·고가용성까지 포함해 설계
```

가장 중요한 원칙은 다음이다.

> Docker MySQL 컨테이너가 살아 있다는 것과 MySQL이 요청을 받을 준비가 됐다는 것은 다르다. `volume`, `healthcheck`, `readiness`, `backup`, `복구 테스트`를 함께 설계해야 한다.

## 참고 자료

[1] MySQL Docker Official Image — image tag, 환경변수, 데이터 디렉터리와 dump  
[2] Docker Docs — 컨테이너화된 데이터베이스, 포트 매핑, volume, Compose  
[3] Docker Compose Startup Order — `depends_on`, `healthcheck`, `service_healthy`  
[4] Testcontainers for Java MySQL Module — MySQL container와 JDBC URL

## 출처

- MySQL Docker Official Image: https://hub.docker.com/_/mysql
- Docker containerized databases: https://docs.docker.com/guides/databases/
- Docker Compose startup order: https://docs.docker.com/compose/how-tos/startup-order/
- Testcontainers Java MySQL: https://java.testcontainers.org/modules/databases/mysql/

## Sources

[1] https://hub.docker.com/_/mysql — MySQL Official Image
[2] https://docs.docker.com/guides/databases — Docker Containerized Databases
[3] https://docs.docker.com/compose/how-tos/startup-order — Docker Compose Startup Order
[4] https://java.testcontainers.org/modules/databases/mysql — Testcontainers Java MySQL Module
