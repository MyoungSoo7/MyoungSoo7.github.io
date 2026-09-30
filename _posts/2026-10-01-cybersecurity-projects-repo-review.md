---
layout: post
title: "CarterPerez-dev/Cybersecurity-Projects 살펴보기 — 흐름 수집 다음에 무엇을 붙여 볼까"
date: 2026-10-01 00:12:00 +0900
categories: [security, homelab]
tags: [cybersecurity, github, honeytoken, ja4, c2, packet-capture, agpl]
---

**리포:** <https://github.com/CarterPerez-dev/Cybersecurity-Projects>

어제 [Packetbeat 흐름 수집 3일 파일럿 글](/2026/09/30/packetbeat-flow-pilot-canary/)을 썼다. 결론은 이랬다. flow 는 "누가 누구와 얼마나"만 알려 준다. "무엇이, 어떤 도구로" 통신했는지는 다음 단계의 몫이다. 그 다음 단계를 고민하던 중에 이 리포를 봤다. 보안 도구를 직접 만들어 보는 프로젝트 모음이다.

이 글은 리포 전체를 요약하지 않는다. **홈랩 관측 파이프라인에 붙여 볼 만한 것**만 골라, 무엇을 주장하는지와 쓸 때 조심할 점을 정리한다. 아래 프로젝트들은 **직접 실행해 보지 않았다.** 기능 설명은 모두 각 프로젝트 README 의 주장이다.

## 1. 리포 개요

| 항목 | 값 (2026-10-01 조회) |
|---|---|
| 설명 | "Building 70 Projects ranging from beginner to advanced…" |
| 스타 | 약 7.5k |
| 라이선스 | **GNU AGPL v3.0** |
| 주 언어 | Go (Python·Rust·Zig·C++·TypeScript 혼재) |
| 최근 push | 2026-09-23 |
| 구성 | `PROJECTS/`(소스), `SYNOPSES/`(개요 문서), `ROADMAPS/`(자격증 로드맵), `RESOURCES/` |

"70개"는 **목표치로 읽는 게 맞다.** README 프로젝트 표를 세어 보니 다음과 같았다.

- 항목은 56개다.
- 그중 소스 링크가 달린 건 36개다.
- 나머지 20개는 `SYNOPSES/` 의 개요 문서만 있다.
- `PROJECTS/` 아래 디렉터리는 foundations 3 · beginner 17 · intermediate 11 · advanced 11 로 42개다.

제목만 보고 고르지 말고 **소스가 있는 항목인지 먼저 확인**할 필요가 있다.

소스가 있는 프로젝트는 대개 README 와 `learn/` 문서가 짝을 이룬다. `learn/` 에는 원리·아키텍처 설명이 있다. 일부 프로젝트는 README 머리에 다른 기여자 표기가 있다. 한 사람이 쓴 코드 모음이 아니라는 뜻이다.

## 2. 같은 "카나리", 다른 질문 — Canary Token Generator

[`PROJECTS/beginner/canary-token-generator`](https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/canary-token-generator)

README 에 따르면 이 프로젝트는 **허니토큰 생성기**다. 공격자가 실제로 써 볼 만한 모양의 미끼 일곱 종류를 만든다.

- 웹 버그
- 지연 리다이렉트
- PDF
- DOCX
- 가짜 `.env`
- 가짜 **kubeconfig**
- MySQL v10 핸드셰이크를 실제로 말하는 미끼 리스너

누군가 미끼를 건드리면 Telegram·웹훅으로 알림이 온다. 같은 `{토큰, 출발 IP}` 조합은 Redis 에서 15분간 중복 억제한다.

어제 글의 카나리와 이름은 같지만 **묻는 질문이 반대**다.

| | 트래픽 카나리 (어제 글) | 허니토큰 (이 프로젝트) |
|---|---|---|
| 누가 건드리나 | 운영자가 일부러 | 공격자가 모르고 |
| 증명하는 것 | 감시 장치가 **보고 있다** | 누군가 **들어왔다** |
| 오탐 | 거의 없음 (정답을 앎) | 거의 없음 (정상 사용자는 건드릴 이유가 없음) |

둘 다 **"정답을 아는 입력"** 을 쓴다는 점에서 뿌리가 같다. 이 리포 README 는 방어 기만 기술의 틀로 [MITRE Engage](https://engage.mitre.org/) 를 걸어 두었다.

쿠버네티스 홈랩이라면 가짜 kubeconfig 토큰이 특히 흥미롭다. 노드 홈 디렉터리나 백업 경로에 두면, 그 파일을 읽고 **실제로 써 본** 순간을 잡을 수 있다. 단, 알림 경로가 외부 서비스를 거친다면 그 서비스가 새로운 공격 면이 된다.

## 3. flow 다음 단계 — JA3/JA4 TLS 핑거프린팅

[`PROJECTS/intermediate/ja3-ja4-tls-fingerprinting`](https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/intermediate/ja3-ja4-tls-fingerprinting)

flow 기록은 "이 노드가 외부 443 포트로 3MB 를 보냈다"까지 말해 준다. 그게 브라우저였는지, `curl` 이었는지, 악성 도구였는지는 모른다. TLS 핑거프린팅이 여기에 답한다.

- TLS 연결의 첫 메시지 ClientHello 에는 클라이언트가 고른 버전·암호 스위트·확장 목록이 그대로 드러난다. 그 선택을 해시한 값이 핑거프린트다.
- 같은 소프트웨어는 같은 값을 낸다. 그래서 IP·도메인·인증서가 바뀌어도 같은 도구를 알아볼 수 있다.

이 프로젝트 README 는 Rust 로 만든 **수동(passive) 센서**라고 소개한다. 다음 핑거프린트를 계산한다고 한다.

- JA3/JA3S
- JA4/JA4S
- JA4H(HTTP)
- JA4X(인증서)
- JA4T/JA4TS(TCP 스택)

README 가 JA4 가 필요한 이유로 드는 설명도 있다. Chrome 이 연결마다 확장 순서를 섞기 시작하자, 확장을 전송 순서대로 해시하는 JA3 는 매번 다른 값을 냈다. JA4 는 정렬한 뒤 해시해서 이 문제를 피한다.

**라이선스를 먼저 봐야 한다.** 원 개발사 FoxIO 의 저장소 설명은 이렇다([FoxIO-LLC/ja4](https://github.com/FoxIO-LLC/ja4)).

- **JA4(TLS 클라이언트)** 는 BSD 3-Clause 다.
- JA4S·JA4H·JA4X·JA4T 등 나머지 **JA4+** 는 FoxIO License 1.1 이다.
- FoxIO License 1.1 은 학술·내부 업무 용도에는 허용적이다. 하지만 **수익화(monetization)에는 허용적이지 않다.**

홈랩·내부 관측에는 문제가 없다. 이걸 넣은 제품이나 유료 서비스를 만들 계획이라면 FoxIO 라이선스 FAQ 부터 확인해야 한다.

## 4. 탐지를 시험할 "공격 쪽" 트래픽 — Simple C2 Beacon

[`PROJECTS/beginner/c2-beacon`](https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/c2-beacon)

README 에 따르면 WebSocket 기반 C2(Command and Control) 서버와 비콘이다.

- 통신은 XOR+Base64 로 인코딩한다.
- 명령은 MITRE ATT&CK 에 매핑돼 있다(셸 실행·파일 업/다운로드·스크린샷·키로깅·지속성 등).
- 재접속은 지수 백오프이고, 대기 간격에 **지터(jitter)** 를 준다.

방어 쪽에서 이 프로젝트의 쓸모는 **탐지 규칙을 시험할 기준 트래픽**이다. C2 는 ATT&CK 에서 독립된 전술([TA0011](https://attack.mitre.org/tactics/TA0011/))이다. 대표 기법은 정상 애플리케이션 프로토콜에 섞여 통신하는 [T1071](https://attack.mitre.org/techniques/T1071/)이다. WebSocket 비콘은 흐름 기록에서 다음과 같은 모양으로 남을 것이다.

- 하나의 오래 사는 연결
- 또는 끊겼다 다시 붙는 규칙적인 연결

어제 글에서 `flows.period` 를 끄지 않은 이유(끝나지 않는 연결이 끝날 때까지 안 보인다)를 이런 트래픽으로 직접 시험해 볼 수 있다.

주의할 점은 분명하다.

- 키로깅·지속성 설치 기능이 들어 있다. **본인이 소유한 격리된 실습 환경에서만** 돌린다.
- 운영 클러스터 노드에 비콘을 올리는 건 시험이 아니라 사고다.
- 돌릴 때는 탐지 도구(Falco 등)가 무엇을 잡고 무엇을 놓치는지 **예상을 먼저 적어 두고** 비교해야 의미가 있다.

## 5. 패킷 캡처를 원리부터 — Network Traffic Analyzer, Zingela

- [`network-traffic-analyzer`](https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/network-traffic-analyzer)
  - Python(Scapy)판과 C++판이 있다.
  - 인터페이스에서 패킷을 잡아 프로토콜 분포·상위 통신 주체(top talkers)·대역폭을 보여 주는 CLI 다.
  - Packetbeat flow 가 내부에서 하는 일을 손으로 한 번 만들어 보기에 적당한 크기다.
- [`zig-stateless-scanner`](https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/advanced/zig-stateless-scanner) (Zingela)
  - masscan·zmap 계열의 무상태 대량 포트 스캐너다.
  - 흥미로운 건 README 의 "정직한 포지셔닝" 절이다. 기본 리눅스에서는 커널 `AF_PACKET` 송신 경로가 단일 코어 초당 약 150만~250만 패킷에서 막힌다고 한다. masscan·zmap·자기 도구 모두 그 벽에 부딪힌다고 **스스로** 적어 두었다.
  - 이 수치는 프로젝트 쪽 주장이고 여기서 재현하지는 않았다.
  - 스캐너는 **허가된 대상에만** 쓴다.

## 6. 쓰기 전에 — AGPL 과 "그대로 복사해도 된다"는 문구

리포 설명에는 "learn from, build upon, use as a reference, or even copy directly"라는 문구가 있다. 그런데 라이선스는 **AGPL v3.0** 이다.

- AGPL 은 GPL 에 "원격 네트워크 상호작용" 조항(제13조)을 더한 라이선스다.
- **수정한 프로그램을 네트워크 서비스로 사용자에게 제공하면, 그 사용자에게도 소스를 제공해야 한다.**
- 참고용으로 읽거나 개인 실습으로 돌리는 데에는 부담이 없다.
- 하지만 코드를 떼어 사내 서비스나 공개 서비스에 넣는 순간 이 의무가 따라온다.
- "그대로 복사"는 **라이선스 조건을 지키는 한에서** 라고 읽어야 한다.

(라이선스 본문: <https://www.gnu.org/licenses/agpl-3.0.html>)

## 7. 정리 — 내 파이프라인에 붙인다면

| 순서 | 무엇 | 채우는 구멍 | 전제 |
|---|---|---|---|
| 1 | kubeconfig 허니토큰 | "들어왔나"를 오탐 거의 없이 | 알림 경로가 새 공격 면이 되지 않게 |
| 2 | JA4 수동 센서 | flow 에 "어떤 도구로"를 추가 | JA4+ 는 FoxIO License, 수익화 불가 |
| 3 | C2 비콘 (격리 환경) | 탐지 규칙의 기준 트래픽 | 운영 노드 금지, 예상을 먼저 적기 |

아직 안 풀린 것도 있다. 이 리포의 프로젝트들은 **학습용 구현**이다. 운영 환경 부하에서 얼마나 버티는지, 보안 업데이트가 얼마나 꾸준할지는 README 로는 알 수 없다. 운영에 넣을 도구로 고를지는 따로 판단해야 한다. 원리를 익히고 기준 입력을 만드는 데에는 충분히 쓸 만해 보인다. 운영 센서는 검증된 구현(Suricata·Zeek 등)과 나란히 놓고 비교할 계획이다.

## References

1. CarterPerez-dev. *Cybersecurity-Projects* (README, 2026-10-01 조회). <https://github.com/CarterPerez-dev/Cybersecurity-Projects>
2. 같은 리포. *Canary Token Generator* README. <https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/canary-token-generator>
3. 같은 리포. *JA3/JA4 TLS Fingerprinting* README. <https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/intermediate/ja3-ja4-tls-fingerprinting>
4. 같은 리포. *Simple C2 Beacon* README. <https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/c2-beacon>
5. 같은 리포. *Network Traffic Analyzer* / *Zingela Stateless Scanner* README. <https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/beginner/network-traffic-analyzer>, <https://github.com/CarterPerez-dev/Cybersecurity-Projects/tree/main/PROJECTS/advanced/zig-stateless-scanner>
6. FoxIO. *JA4+ Network Fingerprinting* (Licensing 절). <https://github.com/FoxIO-LLC/ja4>
7. MITRE ATT&CK. *TA0011 Command and Control*. <https://attack.mitre.org/tactics/TA0011/>
8. MITRE ATT&CK. *T1071 Application Layer Protocol*. <https://attack.mitre.org/techniques/T1071/>
9. MITRE. *Engage*. <https://engage.mitre.org/>
10. Free Software Foundation. *GNU Affero General Public License v3.0*. <https://www.gnu.org/licenses/agpl-3.0.html>
11. 이 블로그. [Packetbeat 흐름 수집 3일 파일럿 — 초록불 말고 카나리로 판정하기](/2026/09/30/packetbeat-flow-pilot-canary/)

*프로젝트 기능·성능 서술은 각 README 의 주장이며 직접 실행·재현하지 않았다. 스타 수·항목 수는 조회 시점 값이다.*
