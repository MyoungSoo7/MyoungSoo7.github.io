---
layout: post
title: "ping 은 가는데 SSH 는 *no route to host* — macOS 26 의 NECP 가 unsigned Go binary 의 사설망 outbound 만 *침묵 차단* 한 사례 진단·우회기"
date: 2026-06-06 23:50:00 +0900
categories: [macos, networking, debugging]
tags: [macos, necp, network-extension, local-network-privacy, codesign, ssh, golang, launchd, controlmaster, sandbox, debugging, sre]
---

내 macOS 에서 1년 넘게 잘 돌던 *집 LAN 서버 모니터링 봇* 이 어느 날 갑자기 5 분 단위로 *"no route to host"* 만 토해내기 시작했다. 그런데 같은 셸에서 `ping`, `nc`, `ssh` 로 *같은 호스트·같은 포트* 를 두드리면 *1 ms* 안에 응답이 온다. *"같은 시스템에서 같은 목적지로 — 어떤 프로세스는 가고, 어떤 프로세스는 못 간다"* — 이 *비대칭* 이 무엇인지 추적해 들어가니, 결국 *macOS 26 의 NECP* 라는 거의 문서화되지 않은 커널 정책 엔진과 *Local Network Privacy*, *코드 사인*, *unsigned Go binary* 의 3 자 충돌이었다.

이 글은 **(1) 1차 오인 — cron + keychain 격리**, **(2) 2차 오인 — 라우팅·firewall**, **(3) 진짜 단서 — `log show` 의 kernel NECP drop**, **(4) 원인 — macOS Local Network Privacy + unsigned binary**, **(5) 우회 옵션 비교**, **(6) 채택안 — `/usr/bin/ssh` 외부 호출 + ControlMaster multiplexing**, **(7) 교훈** 순으로 정리한다. *"내 컴퓨터인데도 내가 모르는 정책이 통신을 끊고 있다"* 는 *2026 년 macOS 디버깅의 새 일상* 에 대한 기록이다.

---

## TL;DR

**문제.** macOS 26 (Tahoe 후속) 에서 *unsigned 로컬 빌드 Go binary* 가 *사설망(192.168.x.x)* 으로 보내는 *outbound TCP* 가 *NECP* (Network Extension Control Policy) 에 의해 *SYN 직후 즉시 drop*. 사용자에게 보이는 에러는 *connect: no route to host* — 마치 *네트워크가 끊긴 것처럼 가장* 한다.

**핵심 단서.** `log show --predicate '...'` 로 kernel 의 tcp 드롭 로그를 직접 떴더니 *reason: NECP* 한 줄.

```
tcp drop outgoing [src:port<->dst:port] interface: en0
so_error: 0 reason: NECP   ← 이 한 줄이 모든 걸 설명한다
```

**원인.** macOS Local Network Privacy (Sequoia 15 도입, 26 강화) 가 *코드 사인되지 않은 binary* 를 *권한 등록 대상으로도 못 잡아서* 다이얼로그 없이 *침묵으로 차단*. `tccutil` 에 항목조차 안 뜬다. ad-hoc 사인만으로는 우회 불가.

**우회.** SSH 호출 부분을 `golang.org/x/crypto/ssh` 의 `ssh.Dial` 에서 *Apple 코드사인된 시스템 바이너리* `/usr/bin/ssh` 외부 호출로 교체. ControlMaster=auto + ControlPersist=60 으로 첫 연결만 비싸고 후속 명령은 *multiplex* 해서 성능 손실 0.

**교훈.** *"내 binary 가 outbound 를 못 보낸다"* 는 이슈는 *방화벽·라우팅·소켓 API* 만 보지 말고 *kernel log* 의 `reason:` 필드를 보라. macOS 는 *NECP·TCC·NEFilterProvider·App Sandbox* 네 layer 가 별개로 작동하며 *어느 하나만 막아도 사용자에게는 똑같이 "no route to host" 로 보인다*.

---

## 0. 발단 — 봇이 응답을 안 한다

집에서 돌리는 LAN 서버 모니터링 봇 (Go) 이 텔레그램으로 `/서버` 명령을 받으면 *5 대 서버의 CPU·메모리·디스크·컨테이너 상태* 를 SSH 로 긁어서 응답해주는 구조다. 어느 날 멍하니 *"안녕?"* 을 봇에게 보내봤더니 — *침묵*. `/서버` 도 *침묵*.

봇 자체가 죽었나? 그렇다면 1차로 *왜 죽었는지* 부터.

---

## 1. 1차 오인 — *cron 에서는 Keychain 이 안 열린다*

봇은 `cron` 의 1 분 supervise 스크립트로 살아 있는지 점검·재기동되도록 설계돼 있었다. `daemon.log` 를 열어 보니 *매분 같은 줄* 이 찍히고 있다:

```
2026/06/06 21:54:00 봇 모드에는 telegram.bot_token 설정 필요
```

즉 봇이 매분 *띄워졌다가 토큰 없음으로 즉시 종료* 되고 있었다. 토큰은 `~/.config` 가 아니라 **macOS Keychain** 의 generic-password 항목에 넣어 두고, 시작 시 `security find-generic-password -s ... -a ... -w` 로 꺼내 쓰도록 돼 있었다. 그런데 *셸에서는 잘 꺼내지는 토큰* 이 *cron 안에서는 빈 문자열* 로 떨어진다.

원인은 macOS 의 *Keychain 격리 정책*. cron 데몬은 *GUI 로그인 세션의 user keychain* 에 접근할 수 없다 — 권한 모달을 띄울 GUI 컨텍스트가 없기 때문에 *자동 실패*. 이는 macOS 의 *문서화된 의도된 동작* 이고, *workaround 는 정공이 두 가지*:

1. **dotenv 평문 파일**: `~/.config/sm.env` 에 600 권한으로 저장, supervise 스크립트가 `source` 후 export. 가장 단순. Keychain 의 보안 이점은 잃는다.
2. **launchd LaunchAgent 로 전환**: cron 을 버리고 사용자 GUI 세션 컨텍스트에서 직접 띄움. Keychain 접근 가능, KeepAlive·RunAtLoad·로그 통합까지 따라옴.

cron 자체가 BSD 호환용 *레거시* 인 macOS 에서는 *launchd 가 정공*. 다음과 같은 plist 한 장으로 끝.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.example.mybot</string>

    <key>ProgramArguments</key>
    <array>
        <string>/path/to/mybot</string>
        <string>-mode</string>
        <string>bot</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>BOT_TOKEN</key>
        <string>__TOKEN__</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>/path/to</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>StandardOutPath</key>
    <string>/path/to/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/daemon.log</string>
</dict>
</plist>
```

`~/Library/LaunchAgents/` 아래 600 권한으로 두고 `launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.example.mybot.plist`. 로드되면 *PPID=1 (launchd)* 자식으로 떠 *부모 종료에 영향 받지 않고*, KeepAlive=true 라 SIGKILL 받아도 *ThrottleInterval (10s) 안에 자동 재기동*.

> 💡 *Tip.* cron 에서 동작하던 1 분 supervise 스크립트는 launchd 전환과 동시에 *무용지물* 이지만, `crontab -e` 가 macOS 의 *TCC (Full Disk Access)* 권한을 요구하면서 *headless 셸에서는 GUI 프롬프트로 stuck* 되는 안전선이 있다. *cron 라인을 못 지우는 상황* 이면 *스크립트 자체를 `exit 0` 으로 비워서 무해화* 하는 것이 실용적 차선. 사용자 GUI 터미널에서는 정상 동작하므로 *진짜 정리는 사용자가 터미널에서 `crontab -e`*.

여기까지가 *1차 오인 해결*. 봇은 다시 떴다. `/서버` 가 응답 — 하지만 응답 *내용* 이 *모든 서버 SSH 실패*. *문제가 끝난 줄 알았는데 끝이 아니었다*.

---

## 2. 2차 오인 — 라우팅·방화벽·네트워크 환경

응답이 이렇게 왔다:

```
❌ ServerA — SSH 연결 실패: dial tcp 192.168.x.x:NNNN:
   connect: no route to host
❌ ServerB — SSH 연결 실패: dial tcp 192.168.x.y:22:
   connect: no route to host
... (5 대 전부)
```

*no route to host* 는 평소 *L2/L3 단절* — 케이블 빠짐, 라우터 다운, VPN 끊김 — 을 의심하는 메시지다. 일단 *내 Mac 의 네트워크 상태* 부터.

```
$ ifconfig en0 | grep inet
   inet 192.168.x.z netmask 0xffffff00 broadcast 192.168.x.255

$ route -n get 192.168.x.x
   destination: 192.168.x.x
     interface: en0
         flags: <UP,HOST,DONE,LLINFO,WASCLONED,IFSCOPE,IFREF>

$ ping -c 2 192.168.x.x
   64 bytes from 192.168.x.x: icmp_seq=0 ttl=64 time=2.948 ms

$ nc -z -G 3 192.168.x.x NNNN
   Connection to 192.168.x.x port NNNN succeeded!

$ ssh -p NNNN user@192.168.x.x "uptime"
   23:20:47 up 53 days, ...
```

*전부 정상.* 라우팅 OK, ARP OK, ICMP OK, TCP OK, SSH OK. *그런데 봇만 안 된다*. 

봇 코드는 `golang.org/x/crypto/ssh` 의 `ssh.Dial("tcp", addr, cfg)` 를 쓰는 평범한 구조. 같은 *바이너리* 를 셸에서 *직접* 실행해도 결과는 *동일하게 5 대 다 실패*.

```
$ /path/to/mybot -mode servers
❌ ServerA — connect: no route to host
❌ ServerB — connect: no route to host
... (5 대 전부)
```

*launchd 격리* 도 아니고 *봇 모드* 만의 문제도 아니다. *이 바이너리만* 라우팅이 안 된다.

확인해본 의심 후보들:

| 의심 | 결과 |
|---|---|
| 다른 inode/경로면 풀리나? `cp` 후 `/tmp/`에서 실행 | ❌ 동일 |
| ad-hoc 코드사인하면 풀리나? `codesign -s - --force` | ❌ 동일 |
| Application Firewall (ALF)? `socketfilterfw --getglobalstate` | ❌ stealth off, blockall off, app permitted |
| Little Snitch / LuLu / Sophos 류 3rd party? | ❌ `/Library/LaunchDaemons/` 에 흔적 0 |
| Lockdown Mode? | ❌ 그러면 `ping` 도 막힌다 |
| Quarantine 속성? | △ `com.apple.provenance:` 보임 (그러나 outbound 차단과 무관한 출처 추적) |

여기서 더 들어갈 곳은 *kernel 레벨 로그* 밖에 없다.

---

## 3. 진짜 단서 — kernel 의 *reason* 필드

macOS 는 `log show --predicate ...` 로 *unified log* 를 끌어올 수 있다. 봇이 *지금* SYN 을 쏘게 만든 다음, 그 PID 로 *방금 1 분간의 모든 tcp drop 메시지* 를 끌어 본다.

```
$ log show --predicate 'composedMessage CONTAINS "mybot"' --last 10m
```

쏟아진 로그 중에서 *핵심* 은 다음 세 줄이었다:

```
kernel: [com.apple.xnu:skywalk] SK[4]: flow_entry_alloc fe "..."
         ipver=4,src=<IPv4-redacted>.53118,
         dst=<IPv4-redacted>.NNNN,proto=0x06"

kernel: [com.apple.xnu.net.tcp:] tcp drop outgoing
         [src:port<->dst:port] interface: en0 (skipped: 0)
         so_gencnt: 57549 t_state: SYN_SENT
         process: mybot:48423
         t_state: SYN_SENT so_error: 0 reason: NECP   ← ★

kernel: [com.apple.xnu.net.tcp:] tcp connect outgoing
         [src:port<->dst:port] ...
         error: 65 so_error: 0
```

*reason: NECP*. 그리고 `error: 65` = `EHOSTUNREACH` — 사용자에게 *"no route to host"* 로 보이는 그 에러.

**NECP** 가 정체였다.

---

## 4. NECP 가 뭐냐 — *암묵적 outbound 정책 엔진*

**NECP (Network Extension Control Policy)** 는 macOS 의 *커널 내부* 네트워크 정책 매칭 엔진이다. iOS/macOS 의 다양한 네트워크 기능 (VPN, Per-App VPN, Content Filter, *Local Network Privacy*) 이 *내부적으로 NECP rule* 을 등록해 *어떤 프로세스* 가 *어떤 목적지* 로 *어떤 행동* 을 할 수 있는지 *socket 단위* 로 결정한다. 사용자가 *명시적으로 설정* 하는 layer 가 아니라 *시스템이 자동 등록* 하는 *암묵 layer*.

오늘 우리를 친 NECP rule 의 출처는 **Local Network Privacy** — macOS Sequoia 15 에서 도입되어 26 에서 강화된 정책. 의도는 *"앱이 사용자의 사설망 (192.168.x.x / 10.x / 172.16-31.x / mDNS / Bonjour) 을 멋대로 스캔/접근하지 못하게"* — 정당한 보안 강화. 새 binary 가 사설망으로 첫 connect 를 시도하면 *시스템 다이얼로그* 가 떠야 한다:

> *"mybot" 이 로컬 네트워크의 기기를 검색하고 연결하려고 합니다. 허용하시겠습니까?*

사용자가 *허용* 을 누르면 **시스템 설정 → 개인정보 보호 및 보안 → 로컬 네트워크** 에 그 앱이 등록되어 *이후 통신 허용*. 거부하면 *NECP 가 outbound drop*.

**그런데 unsigned binary 는 이 다이얼로그를 *트리거하지 못한다***. 이유:

- macOS 는 *권한 부여 대상* 을 **codesign identity** (`team-identifier` + `bundle-id` + `signing-id`) 로 추적한다.
- 코드사인 없는 binary 는 *identity 가 없으므로* *권한을 줄 수 있는 항목 자체로 등록되지 않는다*.
- 다이얼로그 트리거에는 `Info.plist` 의 `NSLocalNetworkUsageDescription` 키도 필요한데, Go 의 단일 Mach-O 바이너리는 *Info.plist 자체가 없다*.
- 결과: 시스템이 *권한을 물어볼 대상이 없다* 고 판단 → *silent deny* → NECP drop.

내가 ad-hoc 사인 (`codesign -s -`) 을 시도했을 때도 풀리지 않은 이유는, ad-hoc identity 는 *cdhash (코드 해시) 만 등록* 되고 *signed by* 가 없어 *Local Network Privacy 의 entitlement 인정 대상이 아니기 때문*. 정식 *Apple Developer ID* 사인 + `NSLocalNetworkUsageDescription` 이 들어간 *.app 번들* 정도 되어야 *권한 다이얼로그가 떴다 → 사용자 승인 → 등록* 흐름이 도는데, 이는 사실상 *앱으로 배포할 때만* 의미가 있다.

> ⚠️ *왜 어제까지는 잘 되다가 갑자기 막혔나?* 일반적으로 OS 가 *NECP 캐시·정책 데이터베이스* 를 백그라운드에서 *주기 갱신/리빌드* 한다. 그 갱신 타이밍에 unsigned binary 가 *모르는 사이* 차단 대상으로 재분류될 수 있다. 빌드 자체는 몇 주 전에 끝났더라도, *어느 날 갑자기* 새벽이나 시스템 idle 시간에 *조용히* 끊긴다. 콘솔 로그에 *언제* 정책이 갱신됐는지 흔적이 거의 안 남는다는 게 디버깅을 어렵게 한다.

---

## 5. 우회 옵션 4가지 비교

| 옵션 | 난이도 | 보장 | 적합성 |
|---|---|---|---|
| A. 시스템 설정에서 토글 켜기 | 1 (사용자 GUI) | unsigned binary 는 *항목 자체가 안 뜸* | ✗ |
| B. macOS 재부팅 (NECP 캐시 리셋 기대) | 1 | 다음 번 빌드에서 다시 막힐 위험 | △ 임시 |
| C. *Developer ID* 정식 사인 + `.app` 패키징 + `NSLocalNetworkUsageDescription` | 5 | ✓ 정공 | 앱 배포할 때만 의미 |
| D. **`/usr/bin/ssh` 외부 호출로 우회** | 2 | ✓ Apple 코드사인된 시스템 바이너리는 NECP 통과 | ✅ |

자가용으로 돌리는 *개인 운영 도구* 라 D 채택. C 는 *공개 배포* 할 때라야 비용 대비 효용이 맞는다.

---

## 6. 채택안 — `/usr/bin/ssh` 외부 호출 + ControlMaster multiplexing

원래 코드는 이런 모양이다.

```go
import "golang.org/x/crypto/ssh"

func SSHConnect(srv ServerConfig) (*ssh.Client, error) {
    cfg := &ssh.ClientConfig{
        User:            srv.User,
        Auth:            []ssh.AuthMethod{ssh.PublicKeys(signer)},
        HostKeyCallback: ssh.InsecureIgnoreHostKey(),
        Timeout:         10 * time.Second,
    }
    return ssh.Dial("tcp", addr, cfg)
}

func SSHRun(client *ssh.Client, cmd string) string {
    session, _ := client.NewSession()
    defer session.Close()
    out, _ := session.CombinedOutput(cmd)
    return string(out)
}
```

이걸 *동등 시그니처를 유지* 하면서 내부만 `/usr/bin/ssh` 호출로 바꾼다. 시그니처 유지가 핵심인 이유 — 호출 site 가 40 곳이 넘기 때문. *호출자는 `client, err := SSHConnect(srv)` 의 타입 추론 덕에 변경 0 줄*. 패치 surface 를 최소화한다.

```go
package monitor

import (
    "fmt"
    "os/exec"
    "path/filepath"
    "strconv"
    "strings"
    "time"
)

// Client 는 /usr/bin/ssh 외부 호출 기반의 SSH 세션 래퍼.
// 기존 *ssh.Client 자리를 그대로 대체하도록 시그니처를 유지한다.
//
// 배경:
//   macOS 26 의 NECP (Network Extension Control Policy) 가
//   unsigned Go binary 의 사설망(192.168.x.x) outbound 를 즉시 drop.
//   golang.org/x/crypto/ssh 의 ssh.Dial 이 ENOROUTE 로 떨어짐.
//   Apple 코드사인된 /usr/bin/ssh 는 NECP 통과 → 우회.
//
// 성능: ControlMaster=auto + ControlPersist=60 으로 첫 연결만 비싸고
//      후속 명령은 같은 SSH 세션을 multiplex.
type Client struct {
    host        string
    port        int
    user        string
    keyPath     string
    controlPath string
}

func (c *Client) Close() error {
    if c == nil || c.controlPath == "" {
        return nil
    }
    _ = exec.Command("/usr/bin/ssh",
        "-O", "exit",
        "-o", "ControlPath="+c.controlPath,
        fmt.Sprintf("%s@%s", c.user, c.host),
    ).Run()
    return nil
}

func sshArgs(c *Client, cmd string) []string {
    args := []string{
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10",
        "-o", "ControlMaster=auto",
        "-o", "ControlPath=" + c.controlPath,
        "-o", "ControlPersist=60",
    }
    if c.keyPath != "" {
        args = append(args, "-i", c.keyPath)
    }
    args = append(args, "-p", strconv.Itoa(c.port))
    args = append(args, fmt.Sprintf("%s@%s", c.user, c.host))
    args = append(args, cmd)
    return args
}

func SSHConnect(srv ServerConfig) (*Client, error) {
    port := srv.Port
    if port == 0 {
        port = 22
    }
    c := &Client{
        host:    srv.Host,
        port:    port,
        user:    srv.User,
        keyPath: srv.KeyPath,
        controlPath: filepath.Join("/tmp",
            fmt.Sprintf("sm-ssh-%d-%s-%d", port, srv.Host, port)),
    }

    var lastErr error
    for attempt := 1; attempt <= 3; attempt++ {
        out, err := exec.Command("/usr/bin/ssh", sshArgs(c, "true")...).CombinedOutput()
        if err == nil {
            return c, nil
        }
        msg := strings.TrimSpace(string(out))
        if msg == "" {
            lastErr = fmt.Errorf("dial tcp %s:%d: %w", srv.Host, port, err)
        } else {
            lastErr = fmt.Errorf("%s", msg)
        }
        if attempt < 3 {
            time.Sleep(2 * time.Second)
        }
    }
    return nil, lastErr
}

func SSHRun(c *Client, cmd string) string {
    if c == nil {
        return ""
    }
    out, err := exec.Command("/usr/bin/ssh", sshArgs(c, cmd)...).CombinedOutput()
    if err != nil {
        return ""
    }
    return string(out)
}
```

핵심 3가지:

**1. `/usr/bin/ssh` 는 Apple 코드사인된 시스템 바이너리.** NECP 가 *system component* 로 인식해서 통과시킨다. Go 의 net/socket syscall 이 거부당하는 것과 *완전히 다른 경로*. 같은 목적지·같은 패킷이지만 *호출 주체가 다르다*.

**2. ControlMaster + ControlPersist 로 성능 유지.** 매 SSH 호출마다 새 TCP 세션·키 교환을 하면 서버 5 대 × 명령 8 개 = *40 회 핸드셰이크* 가 발생해 10 초 작업이 50 초로 늘어난다. `ControlMaster=auto + ControlPersist=60` 으로 *첫 연결만 비싸고 이후 60 초 동안은 같은 socket 위로 multiplex*. 실측은 *기존 Go SSH 와 동등*.

**3. 시그니처 유지로 호출자 0 줄 수정.** `*ssh.Client` 를 `*Client` 로만 바꿔도, 호출 site 가 `client, err := SSHConnect(srv)` 처럼 *타입 추론* 으로 쓰고 `client.Close()` 와 `SSHRun(client, "...")` 만 호출하면 *전혀 손댈 필요가 없다*. 40 곳 안 만지고 monitor 패키지 한 곳만 갈아치웠다.

빌드 → 교체 → launchd 재시작 → 검증.

```
$ go build -o /tmp/mybot.new ./cmd
$ /tmp/mybot.new -mode servers
━━━ ServerA ━━━
  ✅ CPU: 4코어 | Load: 1.82
  ✅ 메모리: 5.1GB / 31.2GB (16.4%)
... (5대 전부 ✅)
```

해결.

---

## 7. 교훈

### 7-1. *kernel log 의 `reason:` 필드는 신성하다*

이번 진단의 분기점은 `log show` 의 *한 줄* 이었다. `tcp drop outgoing ... reason: NECP`. *이 필드를 안 봤더라면* 나는 `pf` rule, ALF, 3rd-party EDR, Go SSH 라이브러리 버그를 모두 의심하면서 *몇 시간을 더 헤맸을* 것이다. macOS 디버깅에서 *socket·dns·라우팅 layer 가 멀쩡한데 특정 프로세스만 막힌다* 면 무조건 *unified log* 의 net.tcp / NECP / appfirewall 카테고리부터 떠야 한다.

쓸만한 쿼리들:

```
# 특정 프로세스 관련 모든 메시지
log show --predicate 'composedMessage CONTAINS "mybot"' --last 10m

# NECP drop 만
log show --predicate 'composedMessage CONTAINS "reason: NECP"' --last 1h

# ALF 거부
log show --predicate 'process == "appfirewall"' --last 1h

# TCP drop / connect 실패 전반
log show --predicate 'composedMessage CONTAINS "tcp drop"' --last 1h
```

### 7-2. *"no route to host" 의 의미가 layer 마다 다르다*

전통적으로 *connect: no route to host* 는 *ICMP unreachable* 또는 *ARP 미해소* 를 뜻했다. *2026 년 macOS* 에서는 *"NECP 가 너의 socket 을 끊었다"* 도 같은 메시지로 사용자에게 노출된다. 이걸 *추상화 누수* 라고 부른다 — *상위 layer 의 정책 거부* 가 *하위 layer 의 라우팅 실패* 처럼 보인다.

같은 함정이 *EHOSTUNREACH (65)* 외에 *EPERM (1)*, *EACCES (13)*, *ECONNREFUSED (61)* 등으로 다양하게 나타날 수 있다. *errno 만으로 원인을 단정하지 말 것*. *프로세스·바이너리 identity 가 뭐냐* 를 같이 봐야 한다.

### 7-3. *macOS 는 4 개의 독립 보안 layer 가 동시에 본다*

1. **Application Firewall (ALF, `socketfilterfw`)** — inbound 중심, GUI 토글
2. **NECP** — outbound 정책, kernel layer, *Local Network Privacy* 가 여기 위에 얹힘
3. **TCC** — privacy DB (`~/Library/Application Support/com.apple.TCC/TCC.db`), 카메라/마이크/연락처/사진 등
4. **App Sandbox + Hardened Runtime + Notarization** — entitlement 기반

*어느 한 layer 가 막아도 사용자에게는 "차단됐다" 로만 보인다*. 한 layer 만 보고 *"firewall 은 꺼져 있으니 firewall 문제는 아니다"* 라고 단정해선 안 된다. 오늘 사례에서 ALF 는 *enabled 지만 outbound 와 무관*, 막은 건 NECP 였다.

### 7-4. *시스템 바이너리 호출은 강력한 우회 도구다*

내가 짠 Go binary 가 정책에 막힐 때, *Apple 사인된 시스템 바이너리* (`/usr/bin/ssh`, `/usr/bin/curl`, `/usr/sbin/scutil` ...) 를 *fork/exec* 로 외부 호출하는 것은 *완전히 합법적이고 권장되는* 우회 방식이다. *내 프로세스의 권한* 이 아니라 *시스템 컴포넌트의 권한* 으로 socket 이 열리므로 NECP·TCC 가 인정한다. 다만 *성능*·*외부 의존*·*에러 메시지 파싱* 의 trade-off 가 있으니, 코드 hot path 가 아니라 *관리·진단성* 코드에 더 잘 맞는다.

### 7-5. *cron 은 macOS 에서 2 등 시민이다*

이번엔 1차 오인의 원인이기도 했다 — *cron 환경에서는 Keychain 이 안 열린다*. macOS 에서 *데몬을 띄우려면 거의 항상 launchd 가 정공*. cron 은 *호환성 alias* 일 뿐이고, *권한·로깅·재시작·환경 변수* 어디서도 launchd 만 못하다. 새 자동화를 *cron 으로 시작하지 말고 launchd 로 시작하자* — 이 사례 하나로 충분히 비싸게 배웠다.

### 7-6. *"왜 어제까진 됐지?"* 가 가장 어려운 질문이다

*"binary 도 그대로, 코드도 그대로, 네트워크도 그대로인데 갑자기 막혔다"* 가 *macOS 정책 갱신* 의 전형 패턴. 이건 *나의 변경* 이 원인이 아니라 *OS 의 백그라운드 변경* 이 원인이다. 이런 부류의 사건은 *재현 불가능* 한 것처럼 보이지만, 사실 *재현 조건이 외부 (OS) 에 있어서 내가 모르는 것* 뿐. 이런 상황에서 *내 코드의 최근 diff* 만 들여다보는 *터널 비전* 에 빠지지 말 것. *수도꼭지 (외부 정책) 를 의심하자*.

---

## 마무리

오늘 *3 시간짜리 정답* 은 *코드 5 줄 추가* 였지만, 그 5 줄에 도달하기 위한 *진단 경로* 는 *cron 격리 → launchd 전환 → 라우팅·firewall·코드사인·바이너리 무결성 검증 → kernel unified log 분석 → NECP 정체 파악 → 우회 옵션 비교 → 시스템 바이너리 외부 호출 채택 → ControlMaster 성능 보존* 의 *여덟 단계* 였다.

이 글을 쓰는 진짜 이유는 — *6 개월 뒤의 나, 또는 이걸 검색하다 들어온 누군가가* 같은 *"no route to host 인데 ping 은 가는데 내 binary 만 안 가는 미스터리"* 에 빠졌을 때 *`log show ... reason: NECP` 한 줄에 도달하기까지 걸리는 시간을 30 분으로 줄이기 위해서*. macOS 가 *조용히 내 socket 을 끊는 시대* 가 시작됐고, 우리는 *그 조용함을 떠들썩하게* 만들어 두는 수밖에 없다.

*"내 컴퓨터인데도 내가 모르는 정책이 통신을 끊고 있다"* — 이 *문장 자체를 기억* 하자. 이게 *2026 년 macOS 디버깅의 시작* 이다.
