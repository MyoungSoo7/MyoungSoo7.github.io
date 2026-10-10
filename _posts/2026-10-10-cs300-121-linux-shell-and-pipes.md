---
layout: post
title: "[CS300 #121] 리눅스 셸과 파이프 — 작은 프로그램을 잇는 가장 오래된 병렬 처리"
date: 2026-10-10 20:01:00 +0900
categories: [cs]
tags: [cs300, distributed-systems, linux, shell, pipe, unix]
---

컴퓨터공학 300 주제 시리즈의 121번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

셸은 프로그램을 실행해 주는 명령 해석기이고, 파이프(`|`)는 한 프로세스의 표준 출력을 다음 프로세스의 표준 입력으로 커널 버퍼를 통해 흘려보내는 장치다. 파이프로 이어진 명령들은 동시에 실행된다.

## 왜 필요한가

Part 7 은 "한 대에서 여러 대로" 넘어가는 이야기다. 그 출발점은 의외로 아주 익숙한 곳에 있다. `cat access.log | grep 500 | wc -l` 같은 한 줄이다.

이 한 줄에는 세 개의 프로세스가 있다. 셋은 순서대로 하나씩 실행되는 것이 아니라 동시에 뜬다. `cat` 이 쓰는 동안 `grep` 이 읽고, `grep` 이 쓰는 동안 `wc` 가 센다. 데이터는 커널이 관리하는 작은 버퍼를 지나간다. 생산자가 너무 빠르면 버퍼가 차서 생산자가 멈추고, 소비자가 너무 빠르면 버퍼가 비어서 소비자가 멈춘다.

생산자-소비자, 역압(backpressure), 스트리밍, 단계별 분업. 분산 데이터 처리에서 다시 만날 개념이 전부 이 한 줄 안에 들어 있다. 셸과 파이프를 정확히 이해하면 뒤의 주제가 훨씬 덜 낯설다.

## 핵심 개념

### 셸이 하는 일

셸(bash, zsh, dash 등)은 사용자가 친 문자열을 해석해 프로그램을 실행한다. 대략 다음 순서다.

1. 문자열을 토큰으로 자른다.
2. 변수·명령 치환·글로브(`*.log`) 같은 확장을 한다.
3. 리다이렉션(`>`, `<`, `2>&1`)과 파이프를 해석한다.
4. `fork()` 로 자식 프로세스를 만들고, 자식에서 `execve()` 로 실제 프로그램을 올린다.
5. 포그라운드면 `wait` 로 끝나기를 기다린다.

이 규칙은 POSIX 표준의 "Shell Command Language" 에 정의되어 있다. bash 는 그 위에 확장을 얹은 구현이다.

### 표준 스트림과 파일 디스크립터

모든 프로세스는 기본으로 세 개의 파일 디스크립터(fd)를 가지고 시작한다.

| fd | 이름 | 기본 연결 |
|---|---|---|
| 0 | stdin | 터미널 입력 |
| 1 | stdout | 터미널 출력 |
| 2 | stderr | 터미널 출력 |

리다이렉션은 이 번호에 무엇을 연결할지 바꾸는 일이다. `cmd > out.txt 2>&1` 은 "fd 1 을 out.txt 로, fd 2 를 지금의 fd 1 과 같은 곳으로" 라는 뜻이다. 순서가 중요하다. `cmd 2>&1 > out.txt` 는 stderr 를 원래 터미널에 남긴다.

### 파이프의 동작

`A | B` 를 만나면 셸은 대략 이렇게 한다.

```
pipe(fds)            # fds[0]=읽기 끝, fds[1]=쓰기 끝
fork() -> 자식 A:   dup2(fds[1], 1); close 나머지; exec A
fork() -> 자식 B:   dup2(fds[0], 0); close 나머지; exec B
부모:               두 끝 모두 close; wait
```

```
  +-----+   stdout    +---------------+   stdin   +-----+
  |  A  | ----------> | 커널 파이프 버퍼 | --------> |  B  |
  +-----+             +---------------+           +-----+
```

Linux `pipe(7)` 매뉴얼이 정하는 핵심 규칙은 다음과 같다.

- 버퍼가 가득 차면 쓰기가 블록된다. 비어 있으면 읽기가 블록된다.
- 모든 쓰기 끝이 닫히면 읽는 쪽은 EOF(0바이트 read)를 받는다.
- 모든 읽기 끝이 닫힌 상태에서 쓰면 쓰는 쪽에 `SIGPIPE` 가 가고, 무시하면 `EPIPE` 오류가 난다.
- `PIPE_BUF` 바이트 이하의 쓰기는 원자적이다. 여러 프로세스가 동시에 써도 그 크기 이하면 서로 섞이지 않는다. POSIX 는 최소 512바이트를 요구하고 Linux 는 4096바이트다.
- Linux 의 기본 파이프 용량은 16페이지, 즉 페이지 크기가 4096바이트인 시스템에서 65536바이트이고 `fcntl(F_SETPIPE_SZ)` 로 바꿀 수 있다.

부모가 쓰기 끝을 닫지 않으면 B 는 영원히 EOF 를 받지 못한다. 파이프 프로그래밍에서 가장 흔한 버그다.

### SIGPIPE 와 `head`

`yes | head -n 3` 은 바로 끝난다. `head` 가 세 줄을 읽고 종료하면 읽기 끝이 사라진다. 그 뒤 `yes` 가 쓰려는 순간 `SIGPIPE` 를 받고 죽는다. 무한 생산자를 멈추는 장치가 바로 이 시그널이다.

### 종료 상태와 `pipefail`

파이프라인의 종료 상태는 기본적으로 마지막 명령의 것이다. `false | true` 는 성공(0)으로 끝난다. 앞단의 실패를 놓치지 않으려면 bash 에서 `set -o pipefail` 을 쓴다. 그러면 0이 아닌 상태로 끝난 가장 오른쪽 명령의 상태가 파이프라인의 상태가 된다. 각 명령의 상태는 `PIPESTATUS` 배열에 남는다.

### 유닉스 철학

작은 도구 하나가 한 가지 일을 하고, 텍스트 스트림으로 서로 이어진다. 이 설계 덕분에 `sort | uniq -c | sort -rn | head` 같은 조합이 별도 프로그램 없이 "단어 빈도 상위 10개" 를 만든다. 각 단계는 독립 프로세스라서 멀티코어에서 동시에 돈다.

## 직접 해 보기

셸이 파이프를 만드는 과정을 파이썬으로 재현해 보자. `os.pipe`, `os.fork`, `os.dup2`, `os.execvp` 만 쓴다.

```python
import os

def run_pipeline(cmd1, cmd2):
    r, w = os.pipe()
    p1 = os.fork()
    if p1 == 0:                 # 자식 1: stdout -> 파이프
        os.dup2(w, 1)
        os.close(r); os.close(w)
        os.execvp(cmd1[0], cmd1)
    p2 = os.fork()
    if p2 == 0:                 # 자식 2: 파이프 -> stdin
        os.dup2(r, 0)
        os.close(r); os.close(w)
        os.execvp(cmd2[0], cmd2)
    os.close(r); os.close(w)    # 부모가 닫지 않으면 cmd2 가 EOF 를 못 받는다
    for p in (p1, p2):
        _, status = os.waitpid(p, 0)
        print(p, "exit", os.waitstatus_to_exitcode(status))

run_pipeline(["printf", "b\\na\\nc\\na\\n"], ["sort"])
```

실행하면 `a a b c` 가 정렬되어 나오고 두 자식의 종료 코드가 0으로 찍힌다. 마지막 `os.close(r); os.close(w)` 를 지우고 다시 돌려 보자. `sort` 는 입력이 끝났다는 사실을 알 수 없어서 멈춘다(Ctrl+C 로 끊는다).

`SIGPIPE` 도 확인할 수 있다.

```
$ yes | head -n 2; echo "${PIPESTATUS[@]}"
y
y
141 0
```

141 은 128 + 13(SIGPIPE) 이다. 시그널로 죽은 프로세스의 상태를 셸이 이렇게 표시한다.

## 현업에서는

- **로그 분석.** 서버에 들어가 `journalctl -u app | grep -i error | tail` 를 치는 일은 지금도 가장 빠른 1차 진단이다. 쿠버네티스 환경이라면 `kubectl logs ... | grep` 이 같은 역할을 한다.
- **CI 스크립트.** 빌드 스크립트 첫 줄에 `set -euo pipefail` 을 두는 관행이 있다. 파이프 중간이 실패했는데 마지막 `tee` 가 성공해 CI 가 초록불이 되는 사고를 막는다.
- **컨테이너 로그.** 컨테이너 런타임은 컨테이너의 stdout·stderr 를 파이프로 받아 파일로 남긴다. 그래서 컨테이너 앱은 로그를 파일 대신 stdout 에 쓰는 것이 기본 관례다.
- **스트리밍 사고방식.** `pg_dump db | gzip | aws s3 cp - s3://...` 처럼 중간 파일 없이 흘려보내면 디스크를 거의 쓰지 않는다. 파이프의 역압 덕분에 메모리도 폭주하지 않는다.

## 확인 문제

1. `cmd > f 2>&1` 과 `cmd 2>&1 > f` 의 차이는 무엇인가?
2. 부모 프로세스가 파이프의 쓰기 끝을 닫지 않으면 어떤 일이 생기는가?
3. `yes | head -n 1` 에서 `yes` 가 종료되는 이유는?
4. `false | true; echo $?` 의 출력을 `pipefail` 설정 전후로 비교하라.
5. 여러 프로세스가 같은 파이프에 동시에 써도 메시지가 섞이지 않으려면 어떤 조건이 필요한가?

### 풀이

1. 앞은 stdout 과 stderr 모두 f 로 간다. 뒤는 stderr 를 먼저 원래 stdout(터미널)으로 복제한 다음 stdout 만 f 로 바꾸므로 stderr 는 터미널에 남는다.
2. 쓰기 끝이 하나라도 열려 있으면 읽는 쪽은 EOF 를 받지 못해 영원히 블록된다.
3. `head` 가 끝나면 읽기 끝이 모두 닫히고, 그 뒤 `yes` 의 쓰기가 `SIGPIPE` 를 받아 종료된다.
4. 기본은 0, `set -o pipefail` 뒤에는 1이다.
5. 한 번의 `write` 크기가 `PIPE_BUF` 이하여야 한다. 그러면 원자적으로 기록된다.

## 더 읽을거리 (References)

- [pipe(7) — Linux man-pages (man.archlinux.org)](https://man.archlinux.org/man/pipe.7)
- [pipe(2) — Linux man-pages (man.archlinux.org)](https://man.archlinux.org/man/pipe.2)
- [POSIX Shell Command Language (The Open Group)](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html)
- [os — Python 공식 문서 (pipe, fork, dup2, exec)](https://docs.python.org/3/library/os.html)
