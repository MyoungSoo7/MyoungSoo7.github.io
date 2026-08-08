---
layout: post
title: "Linux에서 오픈소스 MCP를 쓰는 법: Agent와 내부 도구 사이의 안전한 연결 계층"
date: 2026-08-09 09:20:00 +0900
categories: [AI, Linux, DevOps]
tags: [MCP, Model Context Protocol, Linux, Open Source, Agent, RAG, Security]
---

# Linux에서 오픈소스 MCP를 쓰는 법

## MCP는 무엇을 해결하는가

LLM Agent가 실제 업무를 하려면 모델만으로는 부족하다.

```text
모델
→ 파일·Git·DB·API·Kubernetes·브라우저
```

를 연결해야 한다. 과거에는 모델별·애플리케이션별로 도구 호출 포맷을 따로 만들었다. MCP(Model Context Protocol)는 이 연결을 공통 프로토콜로 정리한다.

MCP는 AI 모델 자체나 RAG 프레임워크가 아니다. 공식 아키텍처는 다음 참여자로 구성된다.

```text
MCP Host
  └─ MCP Client
       └─ MCP Server
            ├─ Tools
            ├─ Resources
            └─ Prompts
```

- **Host**: Claude Code, Claude Desktop, IDE, 자체 Agent 애플리케이션
- **Client**: Host가 MCP 서버와 연결을 유지하는 구성요소
- **Server**: 파일·Git·DB·API·내부 스크립트 같은 context와 capability를 제공하는 프로세스

공식 문서 기준 MCP의 데이터 계층은 JSON-RPC 기반이고, 핵심 primitive는 tools·resources·prompts다. MCP는 LLM의 추론 방식이나 RAG 알고리즘 자체를 정하지 않는다. **모델과 외부 실행·데이터 계층 사이의 계약을 표준화한다.**

## Linux에서 특히 유용한 이유

Linux는 MCP 서버를 실행하기 좋은 환경이다.

```text
systemd
Docker/Podman
uv/uvx
Node.js/npx
SSH
Unix socket
Kubernetes
PostgreSQL·Redis·Elasticsearch
```

를 모두 조합할 수 있기 때문이다.

홈랩을 예로 들면 다음과 같은 구조를 만들 수 있다.

```text
클라우드 또는 로컬 LLM
        ↓
MCP Host/Client
        ↓
Linux 내부 MCP Server
 ├─ read-only K3s 조회
 ├─ LLM Wiki 검색
 ├─ Git diff/테스트 조회
 ├─ DB schema 조회
 ├─ 로그 검색
 └─ 허용된 스크립트 실행
```

중요한 것은 **LLM에 Linux shell 전체를 주는 것과 MCP 도구를 제한적으로 제공하는 것은 다르다**는 점이다.

## 오픈소스 MCP 생태계

공식 `modelcontextprotocol/servers` 저장소에는 filesystem, git, GitHub, PostgreSQL 등을 포함한 참조 서버가 있다. 공식 SDK도 Python·TypeScript뿐 아니라 C#, Go, Kotlin, PHP, Ruby, Rust, Swift 등으로 제공된다.

Linux에서 시작하기 좋은 선택은 다음과 같다.

| 목적 | 선택지 | 권장 범위 |
|---|---|---|
| 파일 읽기 | Filesystem MCP | 특정 디렉터리 allowlist |
| Git 분석 | Git MCP | 특정 repository read-only |
| GitHub | GitHub MCP | issue·PR·코드 조회부터 시작 |
| PostgreSQL | PostgreSQL MCP | read-only DB role·schema 제한 |
| 내부 서비스 | 자체 Python MCP | 좁은 API와 명시적 입력 schema |
| 공공데이터 | Public Data Lens MCP | 읽기 전용 데이터셋 탐색 |

공식 참조 서버는 시작점이지, 운영 보안이 자동으로 보장된다는 의미는 아니다. 서버의 유지 상태·라이선스·권한 모델·외부 dependency·로그 정책을 각각 확인해야 한다.

## Linux 설치 패턴

### Python MCP 서버

공식 튜토리얼은 Python 3.10 이상과 Python MCP SDK 2.0.0 이상을 요구한다. `uv`를 쓰면 시스템 Python을 오염시키지 않고 격리된 실행환경을 만들기 쉽다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv init linux-mcp-demo
cd linux-mcp-demo
uv venv
source .venv/bin/activate
uv add "mcp[cli]"
```

서버 실행은 일반적으로 다음과 같다.

```bash
uv run server.py
```

### 참조 서버 실행

공식 저장소는 Python 서버를 `uvx`, Node 서버를 `npx`로 실행하는 패턴을 안내한다.

```bash
uvx mcp-server-git --repository /srv/repos/example
```

Node 기반 서버는 MCP Host 설정에서 다음과 같이 등록한다.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/srv/agent-readonly"
      ]
    }
  }
}
```

경로는 반드시 허용 범위로 고정해야 한다. `/`, `/home`, 운영 Secret 디렉터리 전체를 무심코 노출하면 안 된다.

## 직접 만드는 최소 read-only MCP 서버

Linux의 특정 디렉터리 안에 있는 Markdown만 조회하는 서버를 생각해보자. 핵심은 기능을 많이 넣는 것이 아니라 경계를 좁히는 것이다.

```python
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wiki-readonly")
ROOT = Path("/srv/llm-wiki").resolve()

@mcp.tool()
def read_note(relative_path: str) -> str:
    """Read one Markdown note below the configured wiki root."""
    target = (ROOT / relative_path).resolve()
    if ROOT not in target.parents and target != ROOT:
        raise ValueError("path outside allowed wiki root")
    if target.suffix.lower() != ".md":
        raise ValueError("only Markdown files are allowed")
    return target.read_text(encoding="utf-8")

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

실제 구현에서는 다음도 추가한다.

```text
파일 크기 제한
심볼릭 링크 탈출 방지
숨김·Secret 파일 차단
허용 확장자 제한
읽기 timeout
감사 로그
```

## stdio와 Streamable HTTP

### stdio

```text
Host가 MCP Server subprocess를 직접 실행
stdin/stdout으로 JSON-RPC 통신
```

장점:

- 네트워크 포트가 없음
- 로컬 Linux에서 빠름
- 프로세스별 권한·환경변수 분리 가능
- 개인 개발환경과 단일 Agent에 적합

주의할 점은 매우 중요하다.

> stdio MCP 서버는 stdout을 JSON-RPC transport로 사용한다. 로그를 stdout에 쓰면 프로토콜이 깨진다. 로그는 stderr 또는 Python logging으로 보내야 한다.

### Streamable HTTP

```text
Host/Client
  → HTTPS
  → 원격 MCP Server
```

여러 Client가 공유하는 내부 Gateway나 원격 서비스에 적합하다. 대신 인증·TLS·세션·rate limit·네트워크 정책이 필요하다.

```text
인터넷에 직접 공개
= 기본 금지

내부망 HTTPS + 인증 + allowlist
= 검토 가능한 운영 방식
```

## MCP 설정 예시

Hermes 같은 MCP Host는 서버 이름과 transport를 설정한다.

```yaml
mcp_servers:
  wiki:
    command: "uv"
    args: ["run", "--directory", "/srv/wiki-mcp", "server.py"]
    timeout: 30
    connect_timeout: 20

  git_readonly:
    command: "uvx"
    args: ["mcp-server-git", "--repository", "/srv/repos/settlement"]
    timeout: 60

  public_data_lens:
    url: "https://service.datahub.kr/projects/public-data-lens/mcp"
    timeout: 120
    connect_timeout: 30
```

Host마다 설정 형식은 다르므로 해당 Host의 최신 문서를 확인해야 한다. 핵심은 다음이다.

```text
서버 이름
transport
실행 명령 또는 URL
허용 환경변수
timeout
인증
```

## Linux 운영 배치

### systemd + stdio

대부분의 Host가 stdio 서버를 직접 자식 프로세스로 관리하므로 별도 systemd가 필요하지 않을 수 있다. 여러 Agent가 공용으로 사용하는 HTTP MCP Gateway라면 systemd가 적합하다.

```ini
[Unit]
Description=Internal MCP Gateway
After=network-online.target

[Service]
User=mcp-readonly
WorkingDirectory=/srv/mcp-gateway
ExecStart=/srv/mcp-gateway/.venv/bin/python server.py --transport streamable-http --port 8080
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ReadWritePaths=/var/lib/mcp-gateway

[Install]
WantedBy=multi-user.target
```

반드시 실제 서비스 전에 권한·파일 접근·네트워크·로그를 검증한다.

### Docker/Podman

```bash
docker run --rm \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  -v /srv/llm-wiki:/data:ro \
  ghcr.io/example/wiki-mcp:stable
```

컨테이너가 정말 read-only로 동작하는지, image digest를 고정했는지, base image 취약점이 없는지 확인해야 한다.

## 보안 설계

MCP는 권한을 자동으로 안전하게 만들어주지 않는다. Tool schema가 곧 권한 경계가 되므로 이름과 입력을 좁게 설계한다.

나쁜 예:

```text
run_shell(command: string)
```

더 나은 예:

```text
get_pod_status(namespace: enum)
get_pod_log(namespace: enum, pod: validated_string, tail: integer<=200)
read_db_schema(service: enum)
run_test_suite(name: enum)
```

필수 원칙:

- read-only를 기본값으로 한다.
- DB는 별도 read-only 계정을 사용한다.
- Secret·token·개인정보를 tool response에 넣지 않는다.
- shell 전체 실행 대신 목적별 도구를 만든다.
- namespace·repository·table allowlist를 둔다.
- 입력 길이·파일 크기·결과 행 수를 제한한다.
- 모든 호출에 actor·tool·input hash·시간·결과 상태를 기록한다.
- 승인 필요한 write tool은 별도 서버로 분리한다.
- MCP 서버 로그와 LLM 대화 로그의 보존기간을 정한다.

## DB MCP를 쓸 때

DB를 바로 노출하지 말고 다음 계층을 둔다.

```text
LLM
 ↓
MCP schema/query tool
 ↓
SQL validator / allowlist
 ↓
read-only DB role
 ↓
DB
```

운영 원장·개인정보 DB에서는 자유로운 `query(sql)`보다 다음처럼 고정된 조회 도구가 안전하다.

```text
get_table_structure(table)
get_index_summary(table)
get_migration_history(service)
get_masked_sample(table, limit<=20)
```

실제 INSERT·UPDATE·DELETE는 기본 금지한다. INSERT SQL을 읽는 것과 INSERT를 실행하는 것은 다르다.

## MCP와 RAG의 관계

MCP와 RAG는 경쟁 관계가 아니다.

```text
RAG
= 문서를 chunk·embedding·retrieval하는 방법

MCP
= Agent가 검색·도구·업무 시스템에 접근하는 표준 연결 계층
```

예:

```text
MCP Wiki Search Tool
→ 검색 결과 반환
→ Agent가 context로 사용
→ LLM이 출처와 함께 답변
```

우리의 Graphify·LION 구조와 연결하면:

```text
Graphify
= 코드·문서 관계 추출

LION
= CS·보안·운영 렌즈 평가

MCP
= Agent가 graph·Wiki·K3s·DB schema를 호출하는 계층

LLM Wiki
= 근거·결정·문서 저장
```

## 디버깅 체크리스트

### 서버가 연결되지 않을 때

```bash
which uv
which node
python3 --version
uvx mcp-server-git --help
```

확인 순서:

```text
명령 경로
작업 디렉터리
환경변수
권한
transport
timeout
```

### stdio가 깨질 때

```text
stdout에 print/log를 쓰지 않았는가?
stderr로 로그를 보내는가?
JSON-RPC 외 문자가 출력되는가?
```

### 도구가 보이지만 실행이 실패할 때

```text
입력 schema가 실제 함수와 맞는가?
파일 allowlist가 맞는가?
서버 사용자의 권한이 충분한가?
외부 endpoint DNS/TLS가 되는가?
응답 크기가 제한을 넘지 않는가?
```

MCP Inspector 같은 개발 도구로 `tools/list`, 각 tool의 입력·출력·오류를 확인하는 것이 좋다.

## 홈랩에 적용하는 권장 단계

```text
1단계: read-only Wiki MCP
2단계: Git·코드 그래프 MCP
3단계: K3s 상태·로그 MCP
4단계: DB schema MCP
5단계: Public Data Lens MCP
6단계: 승인형 write tool
```

처음부터 다음을 제공하지 않는다.

```text
kubectl apply/delete/patch
DB write
Secret read
임의 shell
방화벽 변경
서비스 재시작
```

특히 홈랩에서는 중앙 Hermes가 MCP Gateway가 되고, 6개 노드는 MCP endpoint·collector·worker로 운영하는 구조가 적합하다.

## 결론

Linux 오픈소스 MCP의 가치는 “AI가 명령을 대신 실행한다”에 있지 않다.

```text
Agent와 내부 시스템 사이에
재사용 가능하고 관찰 가능한 계약을 만든다
```

는 데 있다.

좋은 MCP 운영은 다음 조건을 만족한다.

```text
도구가 작고 명확하다
권한이 좁다
read-only부터 시작한다
결과에 provenance가 있다
실패가 명시적이다
로그가 stderr/감사 계층으로 분리된다
write에는 사람 승인과 rollback이 있다
```

Linux에서는 `uv/uvx + stdio + systemd/Docker + read-only allowlist` 조합이 가장 현실적인 출발점이다. 이후 Git·Wiki·K3s·DB schema·Public Data Lens를 MCP로 연결하면, 단순 채팅봇이 아니라 근거와 도구를 가진 운영 Agent 플랫폼으로 확장할 수 있다.

## 참고 자료

- [MCP Architecture Overview](https://modelcontextprotocol.io/docs/learn/architecture)
- [Build an MCP Server](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP Specification](https://modelcontextprotocol.io/specification/latest)
- [Official MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Anthropic: Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Public Data Lens](https://github.com/hike-lab/public-data-lens)

> 이 글은 공식 MCP 문서와 공식 참조 저장소를 기준으로 작성했다. MCP 서버가 오픈소스라는 사실만으로 해당 서버의 권한·보안·운영 품질이 보장되는 것은 아니다.
