---
layout: post
title: "Docker 로 MySQL 과 Oracle 을 띄운다는 것: 대칭이 아닌 두 작업"
date: 2026-09-17 19:19:26 +0900
categories: [Database, Docker, Backend]
tags: [MySQL, Oracle Database, Docker, Container, Entrypoint]
---

"도커로 DB 띄우자" 는 한 문장이지만, MySQL 과 Oracle 에서 그 문장이 뜻하는 작업은 같지 않다.
MySQL 은 `docker run` 한 줄이고, Oracle 은 **에디션에 따라 이미지 빌드부터 시작**한다.
이 차이는 취향이나 성숙도의 문제가 아니라 배포 형태에 새겨져 있다. 각 프로젝트의 Containerfile
한 줄만 나란히 놓으면 바로 보인다.

Oracle 의 26ai Free 이미지:

```dockerfile
ARG INSTALL_FILE_1="https://download.oracle.com/otn-pub/otn_software/db-free/oracle-ai-database-free-26ai-23.26.2-1.el8.x86_64.rpm"
```

Oracle 의 Enterprise/SE2 이미지:

```dockerfile
ARG INSTALL_FILE_1="LINUX.X64_2326000_db_home.zip"
...
COPY --chown=oracle:dba $INSTALL_FILE_1 $INSTALL_RSP $INSTALL_DB_BINARIES_FILE $INSTALL_DIR/
```

앞은 URL 이라 빌드가 알아서 받아오고, 뒤는 **로컬 파일명**이라 내가 먼저 그 자리에 갖다 놔야 한다.
README 도 같은 말을 한다 — "You will have to provide the installation binaries of Oracle Database
(except for Oracle Database 18c XE, 21c XE and 26ai Free) and put them into the `dockerfiles/<version>` folder."[^ora-readme]

## 1. MySQL — 한 줄이 되는 쪽

MySQL 은 Docker Official Image 라서 받아서 바로 돈다.

```bash
docker run -d --name mysql8 \
  -e MYSQL_ROOT_PASSWORD=change-me \
  -e MYSQL_DATABASE=appdb \
  -e MYSQL_USER=app -e MYSQL_PASSWORD=app-pw \
  -p 3306:3306 \
  -v mysql-data:/var/lib/mysql \
  mysql:8.4
```

`MYSQL_ROOT_PASSWORD` 를 뺄 수는 없다. 엔트리포인트가 직접 막는다.

```bash
docker_verify_minimum_env() {
  if [ -z "$MYSQL_ROOT_PASSWORD" -a -z "$MYSQL_ALLOW_EMPTY_PASSWORD" -a -z "$MYSQL_RANDOM_ROOT_PASSWORD" ]; then
    mysql_error <<-'EOF'
      Database is uninitialized and password option is not specified
          You need to specify one of the following as an environment variable:
          - MYSQL_ROOT_PASSWORD
          - MYSQL_ALLOW_EMPTY_PASSWORD
          - MYSQL_RANDOM_ROOT_PASSWORD
    EOF
  fi
```

셋 중 하나는 반드시 있어야 하고, 없으면 컨테이너는 뜨다 만다.[^mysql-ep]

### 함정 ①: 이 불리언 변수들은 "false" 를 모른다

위 코드가 쓰는 건 `-z`(빈 문자열인가) 다. 값이 무엇인지는 보지 않는다.
랜덤 패스워드를 쓰는 쪽도 마찬가지로 `-n` 이다.

```bash
if [ -n "$MYSQL_RANDOM_ROOT_PASSWORD" ]; then
```

그래서 `MYSQL_RANDOM_ROOT_PASSWORD=false` 나 `=0` 은 **끄는 게 아니라 켜는 것**이다.
비어 있지 않은 문자열은 전부 참이다. 끄려면 변수를 아예 넘기지 않아야 한다.
Oracle 이 배포하는 MySQL 이미지 문서도 같은 동작을 "a known issue" 라고 적어 두었다.[^mysql-oracle-doc]

### 함정 ②: 데이터가 이미 있으면 환경변수는 전부 무시된다

```bash
declare -g DATABASE_ALREADY_EXISTS
if [ -d "$DATADIR/mysql" ]; then
    DATABASE_ALREADY_EXISTS='true'
fi
```

`/var/lib/mysql/mysql` 디렉터리 하나로 초기화 여부를 판단하고, 이미 있으면 초기화 블록 자체를
건너뛴다.[^mysql-ep] `MYSQL_DATABASE` 를 바꿔도 새 DB 가 생기지 않고, `MYSQL_ROOT_PASSWORD` 를
바꿔도 비밀번호가 바뀌지 않는다. **볼륨을 지우거나 SQL 로 직접 바꾸는 것 말고는 방법이 없다.**
"compose 파일을 고쳤는데 반영이 안 된다" 의 대부분이 이것이다.

### 함정 ③: root 의 접속 허용 범위

```bash
file_env 'MYSQL_ROOT_HOST' '%'
```

Docker Official 이미지의 기본값은 `%` — 즉 컨테이너 밖에서도 root 로 붙을 수 있다.[^mysql-ep]
로컬 개발이면 편하지만, 이 컨테이너를 포트포워딩해 놓은 채로 잊으면 그대로 노출이다.
`MYSQL_ROOT_HOST=localhost` 로 조이는 편이 낫다.

### 초기화 스크립트

`/docker-entrypoint-initdb.d` 에 넣은 파일은 **초기화 때 한 번만** 실행된다.
`.sql .sql.gz .sql.bz2 .sql.xz .sql.zst .sh` 를 알파벳 순으로 처리하고,
`.sh` 는 실행 권한이 있으면 실행하고 없으면 **source** 한다.[^mysql-ep]

```bash
*.sh)
  if [ -x "$f" ]; then
    mysql_note "$0: running $f"
    "$f"
  else
    mysql_note "$0: sourcing $f"
    . "$f"
  fi
```

source 되는 경우 그 스크립트가 만든 환경변수는 엔트리포인트에 그대로 남는다. 의도한 거라면
유용하고, 모르고 있으면 디버깅이 어려워지는 종류의 차이다.

## 2. Oracle — 한 줄이 되지 않는 쪽

Oracle Database 컨테이너는 공식적으로 `oracle/docker-images` 리포에서 **내가 빌드하는 것**이
기본이다. 빌드 스크립트의 사용법은 이렇다.[^ora-readme]

```
Usage: buildContainerImage.sh -v [version] -t [image_name:tag] [-e | -s | -x | -f] [-i] [-p] [-b] [-o]
```

`-e` Enterprise, `-s` Standard Edition 2, `-x` Express, `-f` Free. 그리고 Enterprise/SE2 를
고르면 앞서 본 대로 설치 바이너리 zip 을 직접 `dockerfiles/<version>` 에 넣어야 한다.
바이너리는 Oracle 사이트에서 라이선스에 동의하고 받는다 — README 가 명시한다.[^ora-readme]

예외가 셋 있다: **18c XE, 21c XE, 26ai Free**. 이쪽은 바이너리를 따로 받을 필요가 없고,
Free 는 Oracle Container Registry 에서 곧바로 받을 수도 있다.

```bash
docker run -d --name oracle-free \
  -p 1521:1521 \
  -e ORACLE_PWD=change-me \
  -v oracle-data:/opt/oracle/oradata \
  container-registry.oracle.com/database/free:latest
```

### SID 와 PDB 는 Free 에서 고정이다

Enterprise/SE2 에서는 `ORACLE_SID`(기본 `ORCLCDB`), `ORACLE_PDB`(기본 `ORCLPDB1`) 를 지정할 수
있다. Free 는 아니다. `runOracle.sh` 에 이렇게 박혀 있다.

```bash
# Sanitizing env for FREE
   export ORACLE_PDB="FREEPDB1"
```

`-e ORACLE_PDB=MYPDB` 를 넘겨도 **조용히 덮어써진다.** 에러도 경고도 없다.
한동안 README 가 이 값을 설정 가능한 것처럼 적어 두어 이슈(#2853)가 올라왔고, 지금은 파라미터
표가 "Do not set; Free uses `FREEPDB1`" 로 고쳐져 있다.[^ora-readme][^ora-2853]
접속은 `//localhost:1521/FREE`(CDB) 또는 `//localhost:1521/FREEPDB1`(PDB) 로 한다.

### 볼륨 권한 — uid 54321

`/opt/oracle/oradata` 는 컨테이너 안 `oracle` 유저, **UID 54321** 이 쓸 수 있어야 한다.[^ora-readme]
named volume 을 쓰면 신경 쓸 일이 없지만, 호스트 디렉터리를 bind mount 하면 십중팔구 여기서 막힌다.

```bash
mkdir -p ./oradata && sudo chown 54321:54321 ./oradata
```

### ulimit

Enterprise/SE2 실행 예시에는 ulimit 네 개가 붙어 있다.[^ora-readme]

```
--ulimit nofile=1024:65536 --ulimit nproc=2047:16384 \
--ulimit stack=10485760:33554432 --ulimit memlock=3221225472
```

Free 예시에는 나오지 않는다. 문서의 파라미터 표도 "Recommended for Enterprise/SE2",
"Not shown in the Free example" 로 구분해 둔다.

### 초기화 훅이 두 개다

MySQL 이 `initdb.d` 하나인 데 비해 Oracle 은 **성격이 다른 두 디렉터리**를 준다.
`runOracle.sh` 에서 호출 위치가 다르다.

```bash
# (DB 생성 블록 안)
"${SCRIPT_BASE_DIR}"/"$USER_SCRIPTS_FILE" "$ORACLE_BASE"/scripts/setup
...
# (블록 밖, 매 기동)
"${SCRIPT_BASE_DIR}"/"$USER_SCRIPTS_FILE" "$ORACLE_BASE"/scripts/startup
```

- `/opt/oracle/scripts/setup` — DB 가 **처음 만들어질 때 한 번**. MySQL 의 `initdb.d` 에 해당.
- `/opt/oracle/scripts/startup` — **매 기동마다**. MySQL 에는 대응물이 없다.

두 경로는 `/docker-entrypoint-initdb.d/setup`, `/docker-entrypoint-initdb.d/startup` 로도
마운트할 수 있다 — 다른 DB 이미지와 결이 맞도록 남겨 둔 별칭이다.[^ora-readme]
매 기동 훅은 계정 잠금 해제나 서비스 등록처럼 **재생성되면 안 되는 것과 매번 확인해야 하는 것**을
분리할 수 있게 해 준다. 스키마 초기화를 여기 넣으면 재기동마다 돌아가니 주의.

## 3. "떴다" 를 판정하는 법

이게 실무에서 제일 자주 어긋나는 지점이다. 컨테이너가 Running 인 것과 DB 가 접속 가능한 것은
다른 사건이고, 그 간격이 Oracle 에서는 분 단위다. Oracle 의 Containerfile 이 그 사실을
스스로 인정한다.

```dockerfile
HEALTHCHECK --interval=1m --start-period=5m --timeout=30s \
   CMD "$SCRIPT_BASE_DIR/$CHECK_DB_FILE" >/dev/null || exit 1
```

`--start-period=5m` — **처음 5분간의 실패는 실패로 치지 않겠다**는 선언이다.[^ora-cf]
헬스체크 간격은 1분. 즉 이 이미지는 "5분쯤 걸릴 수 있다" 를 전제로 설계돼 있다.
로그에서 기다릴 문자열은 이것이다.

```
#########################
DATABASE IS READY TO USE!
#########################
```

CI 나 기동 스크립트에서 `sleep 30` 같은 상수로 때우면 대부분 여기서 깨진다.
{% raw %}`docker inspect --format '{{.State.Health.Status}}'`{% endraw %} 나 위 문자열 grep 으로 기다리는 게 맞다.

MySQL 쪽은 비교적 빠르지만 원리는 같다. 초기화 중에는 유닉스 소켓만 열린 임시 서버로 도는
구간이 있어, 이때 TCP 로 붙으면 거절당한다. `mysqladmin ping` 을 헬스체크로 두고 기다린다.

## 4. compose 로 정리하면

```yaml
services:
  mysql:
    image: mysql:8.4
    environment:
      MYSQL_ROOT_PASSWORD: change-me
      MYSQL_ROOT_HOST: localhost      # 기본값 '%' 를 좁힌다
      MYSQL_DATABASE: appdb
    ports: ["3306:3306"]
    volumes:
      - mysql-data:/var/lib/mysql
      - ./initdb:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
      interval: 10s
      timeout: 5s
      retries: 12

  oracle:
    image: container-registry.oracle.com/database/free:latest
    environment:
      ORACLE_PWD: change-me
      # ORACLE_PDB 는 Free 에서 무시된다 — FREEPDB1 고정
    ports: ["1521:1521"]
    volumes:
      - oracle-data:/opt/oracle/oradata
      - ./ora-setup:/opt/oracle/scripts/setup:ro      # 최초 1회
      - ./ora-startup:/opt/oracle/scripts/startup:ro  # 매 기동
    # 이미지에 HEALTHCHECK 가 내장돼 있다 (start-period 5m)

volumes:
  mysql-data:
  oracle-data:
```

`depends_on` 에 `condition: service_healthy` 를 걸면 앱 컨테이너가 DB 를 기다리게 만들 수 있다.
Oracle 쪽은 그 대기가 실제로 몇 분일 수 있다는 점을 앱의 타임아웃에도 반영해야 한다.

## 5. 두 이미지를 한 표로

| | MySQL (Docker Official) | Oracle Database |
| --- | --- | --- |
| 이미지 확보 | `docker pull mysql:8.4` | Free/XE 는 pull, **Enterprise/SE2 는 직접 빌드 + 바이너리 준비** |
| 필수 환경변수 | 패스워드 3종 중 1개 (없으면 기동 중단) | 없음 (미지정 시 랜덤 생성) |
| 데이터 경로 | `/var/lib/mysql` | `/opt/oracle/oradata` (**uid 54321** 쓰기 가능해야) |
| 기본 포트 | 3306 | 1521 (+ EM Express 5500, TCPS 2484) |
| 초기화 훅 | `/docker-entrypoint-initdb.d` (1회) | `scripts/setup` (1회) + `scripts/startup` (매 기동) |
| 재초기화 판정 | `$DATADIR/mysql` 디렉터리 존재 여부 | oradata 안의 체크포인트 파일 |
| 기동 시간 전제 | 초 단위 | **헬스체크 start-period 5분** |
| ARM64 | 공식 멀티아치 | **23.5 Free 부터** ARM 포트 제공 |

ARM 쪽만 한 줄 덧붙이면 — Apple Silicon 맥에서 Oracle 을 에뮬레이션으로 굴리던 시절은 끝났다.
Oracle 이 23ai Free 의 ARM 컨테이너 이미지를 정식 제공한다고 발표했고, 23.5 Free 부터 멀티아치
이미지가 나온다.[^ora-arm][^gvenzl]

## 정리

- MySQL 은 **엔트리포인트 셸 스크립트**가 계약서다. 동작이 의심되면 `docker-entrypoint.sh` 를
  읽는 게 문서를 읽는 것보다 빠르고 정확하다. 불리언이 불리언이 아니라는 것도 거기서만 보인다.
- Oracle 은 **에디션이 곧 배포 방식**이다. Free/XE 면 MySQL 만큼 쉽고, Enterprise/SE2 면
  "컨테이너 사용법" 이 아니라 "이미지 빌드 절차" 를 먼저 읽어야 한다.
- 둘 다 **Running ≠ Ready** 다. Oracle 은 그 간격을 이미지가 5분으로 선언해 두었다.

---

## References

[^mysql-ep]: docker-library/mysql, `8.4/docker-entrypoint.sh` — `docker_verify_minimum_env()`, `DATABASE_ALREADY_EXISTS` 판정, `docker_process_init_files()`, `file_env 'MYSQL_ROOT_HOST' '%'`. <https://github.com/docker-library/mysql/blob/master/8.4/docker-entrypoint.sh>
[^mysql-doc]: MySQL Docker Official Image 문서 (docker-library/docs). <https://github.com/docker-library/docs/blob/master/mysql/README.md> · <https://hub.docker.com/_/mysql>
[^mysql-oracle-doc]: MySQL Reference Manual, "Deploying MySQL on Linux with Docker Containers" — Oracle 배포 MySQL 이미지의 환경변수 및 알려진 동작. <https://dev.mysql.com/doc/refman/8.4/en/docker-mysql-getting-started.html>
[^ora-readme]: oracle/docker-images, `OracleDatabase/SingleInstance/README.md` — 설치 바이너리 요구사항, `buildContainerImage.sh` 사용법, 파라미터 표(uid 54321 · ulimit · ORACLE_SID/ORACLE_PDB · setup/startup 마운트). <https://github.com/oracle/docker-images/blob/main/OracleDatabase/SingleInstance/README.md>
[^ora-cf]: oracle/docker-images, `dockerfiles/23.26.0/Containerfile.free` 및 `Containerfile` — `ARG INSTALL_FILE_1`, `COPY --chown=oracle:dba`, `HEALTHCHECK --interval=1m --start-period=5m --timeout=30s`. <https://github.com/oracle/docker-images/tree/main/OracleDatabase/SingleInstance/dockerfiles/23.26.0>
[^ora-run]: oracle/docker-images, `dockerfiles/23.26.0/runOracle.sh` — `# Sanitizing env for FREE` 블록, `scripts/setup` 과 `scripts/startup` 의 호출 위치 차이, `DATABASE IS READY TO USE!`. <https://github.com/oracle/docker-images/blob/main/OracleDatabase/SingleInstance/dockerfiles/23.26.0/runOracle.sh>
[^ora-2853]: oracle/docker-images issue #2853 — Free 에서 `ORACLE_PDB` 가 무시되는 동작과 문서 수정. <https://github.com/oracle/docker-images/issues/2853>
[^ora-arm]: Gerald Venzl, "Announcing Oracle Database 23ai Free container images for ARM-based Apple MacBook computers", Oracle Database Blog. <https://blogs.oracle.com/database/post/announcing-oracle-database-23ai-free-container-images-for-armbased-apple-macbook-computers>
[^gvenzl]: gvenzl/oci-oracle-free — "Starting with Oracle Database 23.5 Free, Oracle provides ARM ports for Oracle Database Free. Multi-platform (multi-arch) images are provided starting with 23.5." (Oracle 제품 매니저가 관리하는 커뮤니티 이미지 리포이며, 공식 이미지가 아니다.) <https://github.com/gvenzl/oci-oracle-free>
