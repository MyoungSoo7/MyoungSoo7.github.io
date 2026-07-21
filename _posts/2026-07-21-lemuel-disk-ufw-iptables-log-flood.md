---
layout: post
title: "디스크가 99% 찼는데 로그 설정을 꺼도 안 멈춘다: 유령 iptables LOG 규칙 추적기"
date: 2026-07-21 23:30:00 +0900
categories: [Infra, SRE]
tags: [K3s, Linux, UFW, iptables, Disk, Troubleshooting, Homelab]
---

# 394GB 디스크의 261GB가 방화벽 로그였다

홈랩 k3s 노드 `lemuel`의 디스크가 **99%**(371G/394G)까지 찼습니다. 이 글은 원인을 추적하다 **한 번 오진하고**, 진짜 범인(유령처럼 남아있던 iptables 규칙)을 잡아 **250GB를 회수**한 과정의 기록입니다.

## 증상: 남은 공간 6GB

```
$ df -h /
Filesystem                         Size  Used Avail Use% Mounted on
/dev/mapper/ubuntu--vg-ubuntu--lv  394G  371G  6.1G  99% /
```

`du`로 파고드니 범인의 윤곽이 잡혔습니다.

```
$ sudo du -xh -d1 /var
261G    /var/log      ← 여기
62G     /var/lib
```

`/var/log`가 **261GB**. 그 안을 보니:

```
39G  /var/log/kern.log     45G  /var/log/kern.log.1
39G  /var/log/syslog       46G  /var/log/syslog.1
39G  /var/log/ufw.log      45G  /var/log/ufw.log.1
```

kern.log / syslog / ufw.log가 **각각 ~84GB씩, 셋이 동시에** 폭증하고 있었습니다. 셋이 똑같이 커진다는 건 하나의 소스가 세 파일에 동시에 쏟아진다는 신호입니다.

## 로그 내용: etcd가 자기 자신과 대화한 기록

```
[UFW INPUT] IN=lo SRC=127.0.0.1 DST=127.0.0.1 PROTO=TCP SPT=2379 DPT=... ACK PSH
```

`IN=lo`(loopback), `127.0.0.1 → 127.0.0.1`, **포트 2379는 etcd**. 즉 k3s의 etcd가 localhost에서 자기들끼리 통신하는 패킷을 방화벽이 **한 줄도 빠짐없이 로그로 남기고** 있었습니다. 샘플 1만 줄 중 loopback이 53%, etcd가 40%. 남길 이유가 전혀 없는 노이즈입니다.

## 1차 오진: "UFW 로깅 레벨이 높구나"

`UFW LOGLEVEL=medium`을 확인하고, 당연히 이게 원인이라 생각했습니다. 그래서:

```bash
sudo ufw logging low   # 차단 패킷만 남기도록
```

그런데 — **안 멈췄습니다.** 심지어 `ufw logging off`로 완전히 꺼도:

```
$ b=$(stat -c%s /var/log/ufw.log); sleep 10; a=$(stat -c%s /var/log/ufw.log)
$ echo $((a-b))
1933761   # off인데도 10초에 1.9MB씩 계속 증가 (≈15GB/일)
```

UFW 로깅을 완전히 껐는데도 `[UFW INPUT]` 로그가 계속 쌓였습니다. **UFW 설정이 원인이 아니었던 겁니다.**

## 진짜 범인: 유령 iptables LOG 규칙

`iptables`를 직접 들여다봤습니다.

```
$ sudo iptables -S INPUT | grep "j LOG"
-A INPUT -j LOG --log-prefix "[UFW INPUT] "
-A INPUT -j LOG --log-prefix "[UFW INPUT] "
-A INPUT -j LOG --log-prefix "[UFW INPUT] "
-A INPUT -j LOG --log-prefix "[UFW INPUT] "     ← 조건도 rate 제한도 없이 4개 중복
```

정상적인 UFW 로깅은 `ufw-before-logging-input` 같은 **서브체인 안에서 조건을 걸어** 동작합니다. 그런데 여기엔 그 밖에, INPUT 체인 끝에 **조건도 rate 제한도 없는 맨몸 `-j LOG` 규칙이 4개나 중복**으로 붙어 있었습니다(FORWARD 체인도 4개). 이것들이 loopback etcd를 포함한 **모든 패킷**을 무제한으로 로깅하고 있었죠. UFW 설정과 완전히 독립적이라 `ufw logging off`가 안 통했던 것입니다.

## 해결

`LOG` 타깃은 비종단(non-terminating)이라 패킷 필터링(ACCEPT/DROP)에는 영향이 없습니다. 안전하게 제거할 수 있습니다.

```bash
# 1. 유령 LOG 규칙 전부 제거 (있는 만큼 반복 삭제)
while sudo iptables -C INPUT -j LOG --log-prefix "[UFW INPUT] " 2>/dev/null; do
  sudo iptables -D INPUT -j LOG --log-prefix "[UFW INPUT] "
done
while sudo iptables -C FORWARD -j LOG --log-prefix "[UFW FORWARD] " 2>/dev/null; do
  sudo iptables -D FORWARD -j LOG --log-prefix "[UFW FORWARD] "
done

# 2. 회전된 옛 로그는 삭제, 현재 로그는 truncate (프로세스가 열고 있어 rm 아닌 truncate)
sudo rm -f /var/log/*.1
sudo truncate -s 0 /var/log/kern.log /var/log/syslog /var/log/ufw.log

# 3. UFW발 재삽입 방지
sudo ufw logging off
```

제거 직후 재측정:

```
10초간 ufw.log +0바이트, kern.log +0바이트   # 완전 정지
```

디스크는 **99% → 32%**(371G → 121G), **250GB 이상 회수**했습니다.

## 남은 교훈

- **로그를 끄라고 했는데도 로그가 쌓이면, 설정이 아니라 `iptables`를 직접 봐라.** UFW는 iptables의 얇은 래퍼일 뿐, UFW 밖에서 삽입된 규칙은 UFW 설정으로 못 끈다.
- **열려 있는 로그 파일은 `rm`이 아니라 `truncate`.** rsyslog가 붙들고 있는 파일을 `rm`하면 inode가 살아있어 공간이 안 비고, 프로세스 재시작 전까지 그대로다.
- **loopback은 로깅 대상이 아니다.** etcd가 localhost에서 초당 수천 패킷을 주고받는데 그걸 다 남기면 디스크는 며칠이면 찬다.
- **규칙이 4개나 중복됐다는 건 과거에 여러 번 재삽입됐다는 뜻.** 재발 가능성이 있으니, 다른 노드에도 같은 유령 규칙이 있는지 스윕하고 재발 시 삽입 주범(ufw reload 트리거·커스텀 스크립트)을 추적할 필요가 있다.
