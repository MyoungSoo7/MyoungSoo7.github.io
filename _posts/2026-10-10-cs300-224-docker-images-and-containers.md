---
layout: post
title: "[CS300 #224] 도커 이미지와 컨테이너 — 읽기 전용 레이어와 격리된 프로세스"
date: 2026-10-10 21:44:00 +0900
categories: [cs]
tags: [cs300, devops, docker, container, oci]
---

컴퓨터공학 300 주제 시리즈의 224번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

이미지는 내용 주소(해시)로 식별되는 읽기 전용 레이어의 묶음이고, 컨테이너는 그 위에 쓰기 레이어 하나를 얹고 네임스페이스와 cgroup 으로 격리해 실행한 **프로세스**다.

## 왜 필요한가

"내 컴퓨터에서는 되는데요" 문제는 실행 환경이 달라서 생긴다. 라이브러리 버전, 설정 파일, OS 패키지가 서버마다 조금씩 다르다. 컨테이너 이미지는 애플리케이션과 그 실행에 필요한 파일 전체를 하나의 불변 묶음으로 만든다. 같은 이미지는 어디서 돌려도 같은 파일을 본다.

또 하나의 이유는 밀도다. 가상 머신은 게스트 OS 커널을 통째로 띄운다. 컨테이너는 호스트 커널을 공유하는 평범한 프로세스라 가볍고 빨리 뜬다.

## 핵심 개념

### 컨테이너는 VM 이 아니다

```
   가상 머신                         컨테이너
+--------+--------+            +--------+--------+
| App A  | App B  |            | App A  | App B  |
| libs   | libs   |            | libs   | libs   |
| 게스트OS| 게스트OS|            +--------+--------+
+--------+--------+            |  컨테이너 런타임  |
|   하이퍼바이저    |            |  호스트 OS 커널   |
|   하드웨어        |            |  하드웨어         |
+-----------------+            +-----------------+
```

컨테이너는 리눅스 커널의 두 기능으로 만들어진다.

- **네임스페이스(namespace)**: 프로세스가 "보는 것"을 나눈다. PID, 네트워크, 마운트, UTS(호스트명), IPC, 사용자, cgroup 네임스페이스 등이 있다. PID 네임스페이스 안의 첫 프로세스는 자신이 PID 1 이라고 본다.
- **cgroup**: 프로세스가 "쓰는 양"을 제한한다. CPU, 메모리, I/O 한도를 건다.

그래서 호스트에서 `ps` 를 치면 컨테이너 안의 프로세스가 그대로 보인다. 격리는 커널이 해 주는 시야와 자원의 칸막이일 뿐, 별도 커널이 아니다. 이 점은 보안 경계를 생각할 때 중요하다.

### 이미지 = 레이어 + 설정

OCI(Open Container Initiative) 이미지 명세에 따르면 이미지는 다음으로 구성된다.

| 구성 요소 | 내용 |
|---|---|
| 레이어(layer) | 파일시스템 변경분을 담은 tar 아카이브. 순서대로 쌓인다 |
| 설정(config) | 실행 명령, 환경 변수, 작업 디렉터리, 레이어 목록 등 |
| 매니페스트(manifest) | 설정과 레이어를 digest 로 가리키는 목록 |
| 인덱스(index) | 아키텍처별(amd64, arm64 등) 매니페스트를 묶는 목록 |

모든 것은 **digest**(예: `sha256:...`)로 가리킨다. 내용의 해시가 곧 이름이므로, 같은 내용은 같은 이름을 갖고, 한 바이트라도 바뀌면 이름이 바뀐다. 이것을 내용 주소 지정(content addressing)이라 한다.

### 태그와 digest

`nginx:1.27` 같은 **태그**는 사람이 읽기 쉬운 별명이고, 가리키는 대상이 바뀔 수 있다. `latest` 는 특별한 의미가 없는 기본 태그일 뿐이다. 운영 환경에서 정확히 같은 이미지를 보장하려면 `nginx@sha256:...` 처럼 digest 로 고정한다.

### 유니언 파일시스템과 복사 후 쓰기

컨테이너가 시작되면 런타임은 이미지 레이어들을 읽기 전용으로 겹쳐 놓고 맨 위에 얇은 쓰기 가능 레이어를 하나 얹는다. 리눅스에서는 overlay2 스토리지 드라이버가 흔히 쓰인다.

```
  [컨테이너 쓰기 레이어]   <- 컨테이너마다 하나, 컨테이너 삭제 시 사라짐
  [레이어 3: app 복사]     \
  [레이어 2: pip install]   > 읽기 전용, 여러 컨테이너가 공유
  [레이어 1: 베이스 OS]    /
```

- 파일을 읽으면 위에서부터 찾아 처음 발견된 것을 쓴다.
- 아래 레이어의 파일을 고치면 그 파일을 쓰기 레이어로 **복사한 뒤** 고친다(copy-on-write).
- 아래 레이어의 파일을 지우면 쓰기 레이어에 "지워졌음" 표시(whiteout)를 남긴다. 아래 레이어의 실제 바이트는 그대로 있다.

마지막 항목이 중요하다. 한 레이어에서 큰 파일을 받아 놓고 다음 레이어에서 지우면, 이미지 크기는 줄지 않는다. 다음 글(Dockerfile 작성법)에서 다시 다룬다.

### 컨테이너는 일회용이다

쓰기 레이어는 컨테이너와 함께 사라진다. 지속해야 할 데이터는 볼륨에 둔다. 컨테이너는 언제든 지우고 같은 이미지로 새로 띄울 수 있어야 한다. 이 "가축(cattle)처럼 다루기" 원칙이 쿠버네티스 운영의 바탕이다.

### 기본 명령

```bash
docker pull nginx:1.27            # 레지스트리에서 이미지 받기
docker image inspect nginx:1.27   # 레이어 digest, 설정 보기
docker run -d --name web -p 8080:80 --memory 256m nginx:1.27
docker exec -it web sh            # 실행 중인 컨테이너 안에서 셸
docker logs web                   # 표준 출력·에러
docker stop web && docker rm web  # SIGTERM -> 유예 후 SIGKILL, 그리고 삭제
```

## 직접 해 보기

레이어 쌓기, 내용 주소, whiteout 을 파이썬으로 흉내 내 보자. 실제 OCI 레이어는 tar 아카이브이고 whiteout 은 `.wh.` 접두사 파일로 표현되지만, 원리는 같다.

```python
import hashlib, json

def digest(obj):
    data = json.dumps(obj, sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()[:16]

WHITEOUT = None  # 이 경로는 지워졌다는 표시

layers = [
    {"/etc/os-release": "debian", "/bin/sh": "x" * 10},
    {"/tmp/big.tar.gz": "y" * 5000},             # 큰 파일 다운로드
    {"/opt/app/main.py": "print('hi')", "/tmp/big.tar.gz": WHITEOUT},
]

def merged_view(layers):
    view = {}
    for layer in layers:                 # 아래에서 위로
        for path, content in layer.items():
            if content is WHITEOUT:
                view.pop(path, None)
            else:
                view[path] = content
    return view

def size(layer):
    return sum(len(c) for c in layer.values() if c is not WHITEOUT)

print("layer digests:")
for l in layers:
    print(" ", digest(l), f"{size(l):5} bytes")

view = merged_view(layers)
print("visible files:", sorted(view))
print("visible bytes:", sum(len(c) for c in view.values()))
print("image bytes  :", sum(size(l) for l in layers))

# 같은 내용 -> 같은 digest, 한 글자 다르면 다른 digest
print(digest({"a": "1"}) == digest({"a": "1"}), digest({"a": "1"}) == digest({"a": "2"}))
```

실행 결과는 다음과 같다(digest 는 앞 16자리만 잘라 표시했다).

```
layer digests:
  sha256:eea997e9385e1aaf    16 bytes
  sha256:1a2acf878367bcaa  5000 bytes
  sha256:8875e8ad6a0693a6    11 bytes
visible files: ['/bin/sh', '/etc/os-release', '/opt/app/main.py']
visible bytes: 27
image bytes  : 5027
True False
```

컨테이너 안에서는 `/tmp/big.tar.gz` 가 보이지 않는다. 그런데 이미지가 차지하는 바이트는 5,027 이다. 지운 파일의 5,000 바이트가 두 번째 레이어에 그대로 남아 있기 때문이다.

## 현업에서는

- **"latest 를 썼더니 어제와 다른 게 떴다".** 태그는 움직인다. 배포 매니페스트에는 버전 태그를, 엄격한 환경에서는 digest 를 쓴다.
- **노드 디스크가 이미지로 찬다.** 이미지를 자주 빌드·배포하는 클러스터에서는 쓰지 않는 이미지가 노드의 `/var/lib` 아래에 쌓인다. kubelet 은 디스크 사용률 기준으로 이미지 가비지 컬렉션을 하지만, 기준을 넘기 전에 경보를 받는 편이 낫다.
- **멀티 아키텍처.** 인텔 노드와 ARM 노드가 섞인 클러스터에서는 이미지 인덱스가 아키텍처별 매니페스트를 갖고 있어야 한다. 한쪽 아키텍처로만 빌드한 이미지는 다른 노드에서 `exec format error` 로 죽는다.
- **컨테이너는 보안 경계로서 VM 보다 약하다.** 커널을 공유하므로 root 로 실행하지 않기, 불필요한 권한(capability) 빼기, 읽기 전용 루트 파일시스템 같은 조치를 겹쳐서 쓴다.

## 확인 문제

1. 컨테이너 격리를 만드는 리눅스 커널 기능 두 가지와 각각의 역할은?
2. 이미지 태그와 digest 의 차이는? 운영 배포에서 digest 가 더 안전한 이유는?
3. 이미지 아래 레이어의 파일을 컨테이너가 수정하면 무슨 일이 일어나는가?
4. 한 레이어에서 받은 1GB 파일을 다음 레이어에서 지웠다. 이미지 크기는 어떻게 되는가?
5. 컨테이너를 지우면 그 안에서 쓴 파일은 어떻게 되는가? 남기려면?

### 풀이

1. 네임스페이스(보이는 범위 격리: PID·네트워크·마운트 등), cgroup(자원 사용량 제한).
2. 태그는 바뀔 수 있는 별명이고 digest 는 내용의 해시다. digest 는 내용이 바뀌면 이름이 바뀌므로 정확히 같은 이미지를 보장한다.
3. 파일이 쓰기 레이어로 복사된 뒤 수정된다(copy-on-write). 원본 레이어는 그대로다.
4. 줄지 않는다. 아래 레이어에 바이트가 남고 위 레이어에는 whiteout 표시만 추가된다.
5. 쓰기 레이어와 함께 사라진다. 볼륨(또는 바인드 마운트)에 써야 남는다.

## 더 읽을거리 (References)

- Docker Docs, [What is an image?](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/)
- Docker Docs, [Storage drivers](https://docs.docker.com/engine/storage/drivers/)
- Open Container Initiative, [OCI Image Format Specification](https://specs.opencontainers.org/image-spec/)
- Linux man-pages (Debian), [namespaces(7)](https://manpages.debian.org/bookworm/manpages/namespaces.7.en.html)
