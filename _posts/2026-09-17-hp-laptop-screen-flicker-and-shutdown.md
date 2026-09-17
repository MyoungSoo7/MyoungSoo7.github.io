---
layout: post
title: "HP 노트북 화면 흔들림과 갑작스런 꺼짐 — 공식 문서로 짜는 진단 트리"
date: 2026-09-17 19:18:00 +0900
categories: [hardware, troubleshooting]
tags: [HP, 노트북, 화면깜빡임, 과열, 드라이버, WindowsEventLog, 하드웨어진단]
---

HP 노트북에서 "화면이 흔들린다(깜빡인다)" 와 "쓰다가 갑자기 꺼진다" 는 별개 증상처럼 보이지만, 진단의 첫 질문은 같다 — **소프트웨어 문제인가, 하드웨어 문제인가.** 이 갈림길을 감으로 넘으면 드라이버 재설치를 열 번 해도 패널 불량을 못 잡고, 반대로 멀쩡한 보드를 수리 보내게 된다. 이 글은 HP 와 Microsoft 의 공식 지원 문서만으로 두 증상의 진단 트리를 짠다. **격리(isolation)부터 하고, 고치는 건 그 다음이다.**

## 1. 화면 흔들림 — 첫 번째 분기: 작업 관리자 테스트

Microsoft 공식 문서가 제시하는 첫 테스트는 도구가 필요 없다. `Ctrl+Alt+Del` 로 **작업 관리자를 띄워 놓고 관찰**한다[^ms-flicker]:

- **작업 관리자까지 같이 깜빡인다** → 원인은 대개 **디스플레이 드라이버**다. 드라이버를 업데이트하거나, 최근 업데이트 직후 시작됐다면 롤백하거나, 제거 후 재설치한다.
- **화면은 깜빡이는데 작업 관리자는 멀쩡하다** → 원인은 대개 **호환성이 깨진 특정 앱**이다. 최근 설치·업데이트한 앱부터 하나씩 업데이트하거나 제거하며 좁힌다.

이 한 번의 관찰로 "드라이버 계열이냐 앱 계열이냐" 가 갈린다. HP 의 자체 트러블슈팅 글도 같은 순서를 권한다 — 안전 모드에서 그래픽 드라이버 제거 후 재설치, 디스플레이 재생 빈도(refresh rate) 확인, 클린 부트로 백그라운드 앱 격리[^hp-flicker].

## 2. 화면 흔들림 — 두 번째 분기: 하드웨어 격리 3종

작업 관리자 테스트는 소프트웨어 안에서의 분기다. 그 전에, 애초에 소프트웨어 층이 아닐 가능성을 걸러내는 물리적 격리가 세 가지 있다.

1. **외부 모니터 연결.** HDMI/USB-C 로 외부 화면을 물렸을 때 **외부는 멀쩡하고 내장 화면만 깜빡이면** GPU·드라이버가 아니라 **내장 패널 또는 디스플레이 케이블** 쪽이다. 외부 모니터까지 같이 깜빡이면 GPU·드라이버 계열로 돌아간다.
2. **BIOS 화면 관찰.** 부팅 직후 BIOS 설정 화면은 Windows 도 드라이버도 올라오기 전이다. **여기서도 깜빡이면 소프트웨어는 무죄** — 하드웨어다.
3. **힌지 틸트 테스트.** 화면을 천천히 여닫으며 각도에 따라 **증상이 변하면** 힌지를 지나는 **디스플레이 케이블의 접촉 문제**를 강하게 시사한다.

HP 공식 화면 문제 문서는 세로줄·가로줄, 색 왜곡, 깜빡임 등 증상별 절차를 제공하며, 일부 패턴은 절차 끝에서 **"수리가 필요하다(requires repair)"** 로 귀결된다고 명시한다[^hp-screen]. 즉 모든 깜빡임이 사용자 선에서 끝나는 게 아니다 — 격리 결과가 하드웨어를 가리키면 거기서 멈추고 4절로 간다.

## 3. 갑작스런 꺼짐 — 첫 용의자는 과열, 판별 도구는 이벤트 로그

**과열부터 본다.** HP 공식 과열 문서는 내부 열이 올라갔을 때의 증상으로 **"사용 중 Windows 가 응답하지 않거나, 갑자기 재시작되거나, 오류 메시지를 표시한다"** 를 명시한다[^hp-heat]. 갑작스런 꺼짐·재시작은 과열 보호 동작의 전형적 얼굴이라는 뜻이다. 같은 문서의 처방:

- **통풍구 청소.** 압축 공기(캔 에어)로 통풍구의 먼지를 분다 — 본체를 열 필요 없다고 문서가 명시한다.
- **단단하고 평평한 표면에서 사용.** 이불·소파·무릎 위는 통풍구를 막는다. 문서는 천으로 흡기가 막히면 과열로 **손상까지 갈 수 있다**고 경고한다.
- **BIOS 업데이트.** 팬 제어 로직 개선이 BIOS 로 배포되는 경우가 있다.
- **HP 소프트웨어(CoolSense / Command Center 등)** 로 열 관리 프로파일을 조정한다.

**꺼짐의 "종류" 는 이벤트 로그가 말해 준다.** Windows 이벤트 뷰어에서 **Kernel-Power, Event ID 41** 은 "시스템이 정상 종료 절차 없이 재부팅됐다" 는 기록이다[^ms-41]. 꺼진 뒤 이 이벤트가 남아 있으면 전원이 물리적으로 끊긴 것(과열 보호, 배터리·전원부, 강제 전원 차단)이고, 반대로 정상 종료 로그가 남아 있으면 소프트웨어가 종료를 명령한 것이라 수사 방향이 완전히 달라진다. "갑자기 꺼졌다" 는 한 문장을 두 갈래로 쪼개 주는 계기판이다.

## 4. 하드웨어 자가 진단 — HP PC Hardware Diagnostics

격리 결과가 하드웨어를 가리키면, 수리 접수 전에 HP 가 제공하는 자가 진단을 돌린다. **전원을 켜자마자 `Esc` 를 연타해 스타트업 메뉴에 들어가 `F2`** 를 누르면 HP PC Hardware Diagnostics 가 뜬다(Windows 가 안 떠도 UEFI 버전이 실행된다)[^hp-diag]. 화면 문제엔 **Display Test**, 꺼짐 문제엔 배터리·전원·온도를 포함한 **System Test** 를 돌리면 부품 단위 판정과 함께 **실패 ID(failure ID)** 가 나오는데, 이 코드가 있으면 수리 접수가 훨씬 빨라진다.

## 5. 진단 트리 한 장 정리

| 관찰 | 가리키는 곳 | 다음 행동 |
| --- | --- | --- |
| BIOS 화면에서도 깜빡임 | 하드웨어 | Diagnostics Display Test → 수리 |
| 외부 모니터는 정상, 내장만 깜빡임 | 패널/케이블 | 힌지 틸트 테스트 → 수리 |
| 작업 관리자도 같이 깜빡임 | 디스플레이 드라이버 | 업데이트/롤백/재설치[^ms-flicker] |
| 작업 관리자는 멀쩡 | 특정 앱 | 최근 앱부터 격리[^ms-flicker] |
| 꺼짐 + Event ID 41 | 전원 급차단 (과열 의심 1순위) | 통풍구 청소·표면·BIOS[^hp-heat][^ms-41] |
| 꺼짐 + 정상 종료 로그 | 소프트웨어 종료 명령 | 업데이트·전원 설정·앱 조사 |
| 자가 조치 후에도 재발 | 부품 불량 | Diagnostics 실패 ID 들고 수리 접수 |

한 줄 요약 — **깜빡임은 "작업 관리자·BIOS·외부 모니터" 세 관찰로, 꺼짐은 "Event ID 41 유무" 로 소프트웨어와 하드웨어를 먼저 갈라라.** 격리 없이 시작한 수리는 복불복이고, 격리를 마친 수리는 한 번에 끝난다.

---

## 근거의 한계

- support.hp.com 은 일반 HTTP 클라이언트를 차단해, HP 문서 두 건(화면 문제·과열)의 본문은 검색 엔진 경유 수집으로 확인했다. 문서 URL 과 인용 문구는 그 수집 본문 기준이다.
- 힌지 틸트·BIOS 화면 관찰 같은 격리 기법의 일부는 HP 지원 커뮤니티(HP 도메인의 사용자 포럼)에서 반복 확인되는 절차로, HP 의 공식 매뉴얼 문구는 아니다. 판정의 근거가 아니라 관찰 요령으로만 썼다.
- 통풍구 청소·BIOS 업데이트의 효과 크기(온도 몇 도 하락 등) 정량 수치는 검증 가능한 출처가 없어 싣지 않았다.
- 모델·세대에 따라 스타트업 키(Esc/F2)와 제공 소프트웨어(CoolSense vs Command Center)는 다를 수 있다 — 자기 모델의 매뉴얼이 우선이다.

## References

[^ms-flicker]: Microsoft 공식 문서 — [Troubleshoot screen flickering in Windows](https://support.microsoft.com/en-us/windows/hardware/display-graphics/troubleshoot-screen-flickering-in-windows) (작업 관리자 테스트: 같이 깜빡이면 드라이버, 아니면 앱)
[^hp-flicker]: HP 공식 Tech Takes — [How to Stop Laptop Screen Flickering](https://www.hp.com/us-en/tech-takes/laptops/troubleshooting/how-to-stop-laptop-screen-flickering.html) (안전 모드 드라이버 재설치·재생 빈도·클린 부트)
[^hp-screen]: HP 공식 지원 문서 — [Troubleshooting screen issues (Windows 11, 10)](https://support.hp.com/us-en/document/ish_7096250-7096363-16) (증상별 절차, 일부 조건은 "requires repair")
[^hp-heat]: HP 공식 지원 문서 — [Reduce heat inside the laptop to prevent overheating](https://support.hp.com/us-en/document/ish_3894569-1692683-16) (과열 증상에 "갑작스런 재시작" 명시, 통풍구 청소·표면·BIOS·열 관리 소프트웨어)
[^ms-41]: Microsoft 공식 문서 — [Advanced troubleshooting for Event ID 41 — unexpected restart](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/event-id-41-restart) (정상 종료 절차 없는 재부팅의 기록)
[^hp-diag]: HP 공식 — [HP PC Hardware Diagnostics](https://support.hp.com/us-en/help/hp-pc-hardware-diagnostics) (부팅 시 Esc → F2, UEFI 진단·컴포넌트 테스트)
