---
layout: post
title: "EDR 은 기록하는 눈이다 — CrowdStrike·Defender·SentinelOne 이 보는 것과 못 보는 것"
date: 2026-09-24 20:26:45 +0900
categories: [Security]
tags: [edr, crowdstrike, microsoft-defender, sentinelone, byovd, mitre-attack, ransomware]
---

백신(AV)은 "이 파일이 나쁜가"를 묻는다. EDR(Endpoint Detection and Response)은 **"이 PC 에서 무슨 일이 일어났는가"** 를 묻는다. 프로세스가 뜨고, 파일을 쓰고, 네트워크로 나가고, 레지스트리를 고치는 모든 사건을 **기록**하고, 그 기록에서 수상한 흐름을 **탐지**하고, 사람이나 자동화가 **대응**하게 해 준다.

이 글은 시장 대표 3종인 **CrowdStrike Falcon**, **Microsoft Defender for Endpoint(MDE)**, **SentinelOne Singularity** 가 무엇을 하는지, 그리고 **구조적으로 무엇을 못 하는지**를 1차 자료로 정리한다. 제품 우열을 가리는 글은 아니다. 뒤에서 설명하듯 그걸 가릴 중립 데이터가 2025년에 오히려 줄었다.

> 관련 글: 백신 제품군의 한계는 [안랩 보안의 한계](/2026/09/24/ahnlab-limits-where-the-last-one-percent-comes-from/), 모바일 쪽은 [모바일 백신의 한계](/2026/09/24/mobile-antivirus-alyac-limits-sandbox/)에서 다뤘다.

## 1. EDR 이 하는 일 — 세 제품의 공통 뼈대

| 단계 | 하는 일 | 1차 자료에서 확인한 예 |
|---|---|---|
| **기록** | 커널/OS 알림을 받아 프로세스·파일·네트워크·레지스트리 이벤트를 수집 | CrowdStrike 의 `csagent.sys` 는 파일시스템 필터 드라이버로, 보안 관련 시스템 활동의 **실시간 알림을 OS 에 등록**해 받는다. 부팅 초기에 올라가 사용자 모드 프로세스보다 먼저 뜨는 악성코드도 본다 ([CrowdStrike RCA, 2024-08-06](https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf)) |
| **상관 분석** | 흩어진 이벤트를 하나의 공격 흐름으로 묶음 | SentinelOne **Storyline**: 관련 프로세스·파일·네트워크·ID 이벤트를 하나의 공격 서사로 자동 연결 ([SentinelOne](https://www.sentinelone.com/platform/endpoint-protection-platform/)) |
| **탐지 콘텐츠 갱신** | 새 공격 기법에 맞춘 규칙을 수시로 배포 | CrowdStrike Channel File 은 새 TTP 대응으로 **하루에도 여러 번** 갱신된다 ([CrowdStrike 기술 설명](https://www.crowdstrike.com/en-us/blog/falcon-update-for-windows-hosts-technical-details/)) |
| **헌팅** | 쿼리로 과거 이벤트를 뒤짐 | MDE **Advanced hunting**: 최근 30일 원시 데이터를 쿼리 ([Microsoft Learn](https://learn.microsoft.com/en-us/defender-xdr/advanced-hunting-overview)) |
| **대응** | 격리·프로세스 종료·격리조치·원복 | MDE **EDR in block mode**: 다른 백신이 주력이어도 침해 후 행위 탐지를 차단 (Plan 2 전용, [Microsoft Learn](https://learn.microsoft.com/en-us/defender-endpoint/edr-in-block-mode)). SentinelOne **Rollback**: Windows 볼륨 섀도 복사본(VSS)으로 랜섬웨어 이전 상태 복원 ([SentinelOne FAQ](https://www.sentinelone.com/faq/)) |
| **자기 보호** | 에이전트 무력화 시도 차단 | MDE **Tamper protection**: 프로세스 종료, 서비스 정지, 레지스트리·예외 설정 변경, DLL 조작 등을 막는다 ([Microsoft Learn](https://learn.microsoft.com/en-us/defender-endpoint/tamper-resiliency)) |

요약하면 EDR 은 **엔드포인트에 앉은 블랙박스이자 CCTV**다. 이 비유에서 한계가 그대로 나온다. CCTV 는 **달린 곳만 찍고**, **꺼질 수 있고**, **녹화본은 언젠가 지워지고**, **누가 보고 있어야 의미가 있다.**

## 2. 한계 ① — 에이전트가 없는 곳은 못 본다

EDR 은 에이전트를 설치한 OS 만 본다. VPN 장비, 방화벽, 프린터, IoT, 관리 밖의 개인 기기, SaaS 계정은 사각지대다.

이게 이론이 아니라는 걸 보여 주는 사례가 있다. Huntress 가 2026년 2월에 대응한 침해에서 공격자는 **탈취한 SonicWall SSL-VPN 계정으로 들어왔다** ([Huntress, 2026-02](https://www.huntress.com/blog/encase-byovd-edr-killer), 벤더 사고 분석). 진입 지점인 VPN 장비엔 EDR 이 없다. EDR 이 처음 본 것은 이미 내부에 들어온 공격자였다.

CrowdStrike 자체 보고서도 같은 방향을 가리킨다. 2024년 CrowdStrike 가 관측한 탐지의 **79% 가 악성코드 없는(malware-free) 공격**이었고, 2019년엔 40% 였다. 공격자가 훔친 계정으로 정상 사용자처럼 로그인해 움직였다는 뜻이다 ([CrowdStrike 2025 Global Threat Report](https://www.crowdstrike.com/en-us/press-releases/crowdstrike-releases-2025-global-threat-report/), **벤더 자체 관측치**이며 외부에서 재현할 수 없다). 정상 계정, 정상 도구(RDP·PowerShell·원격관리툴)로 하는 행동은 기록은 되지만 **"수상하다"고 판정하기 어렵다.**

## 3. 한계 ② — EDR 은 꺼질 수 있다 (EDR Killer 와 BYOVD)

EDR 도 결국 OS 위의 소프트웨어다. 공격자가 관리자 권한을 얻으면 가장 먼저 하는 일 중 하나가 **EDR 끄기**다. MITRE ATT&CK 은 이를 [T1562.001 Impair Defenses: Disable or Modify Tools](https://attack.mitre.org/techniques/T1562/001/)로 분류한다.

현재 주류 수법은 **BYOVD(Bring Your Own Vulnerable Driver)** 다. 서명은 정상이지만 취약점이 있는 옛 드라이버를 올려 커널 권한을 얻고, 거기서 EDR 프로세스를 죽인다. 커널에서 오는 요청은 PPL(보호 프로세스) 같은 사용자 모드 보호를 우회한다.

- Sophos 는 RansomHub 공격에서 **EDRKillShifter** 를 발견했다. 취약 드라이버를 떨어뜨린 뒤 목록에 있는 보안 프로세스를 무한 루프로 계속 종료하는 도구다. 이 사례에선 Sophos 의 행위 탐지가 막았다 ([Sophos X-Ops, 2024-08](https://www.sophos.com/en-us/blog/edr-kill-shifter)).
- ESET 은 실제로 쓰이는 EDR Killer 약 90종을 추적했고, 그중 54종이 BYOVD 방식으로 35개 취약 드라이버를 악용한다고 밝혔다 ([ESET, 2026-04](https://www.eset.com/blog/en/business-topics/threat-landscape/what-are-edr-killers/), 벤더 연구).
- 앞의 Huntress 사례에서 쓰인 드라이버는 **인증서가 이미 폐기된** 포렌식 도구(EnCase) 드라이버였다. 그런데도 Windows 가 로드했다. 커널은 암호학적 서명 체인만 검증하고 폐기 여부는 확인하지 않기 때문이라고 Huntress 는 분석했다 (벤더 분석).

**막는 장치는 있다. 다만 완전하지 않다고 Microsoft 스스로 말한다.**

Microsoft 취약 드라이버 차단 목록은 Windows 11 2022 업데이트부터 기본으로 켜져 있다. 그러나 공식 문서에 따르면 이 목록은 **"취약한 드라이버를 모두 막는다고 보장하지 않는다."** 호환성 때문에 **일부 차단을 일부러 보류**하기도 하고, 갱신은 분기 단위다 ([Microsoft Learn — 권장 드라이버 차단 규칙](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/microsoft-recommended-driver-block-rules)). ESET 도 드라이버 차단은 공격 체인의 **마지막 순간**에 일어나며, 실패한 공격자는 다른 도구로 바꿔 다시 시도할 뿐이라고 지적한다.

## 4. 한계 ③ — 커널에 있다는 것은 양날의 칼이다

EDR 이 깊이 보려면 커널에 들어가야 한다. 커널에 있다는 건 **EDR 의 실수가 곧 OS 의 죽음**이라는 뜻이기도 하다.

2024년 7월 19일 CrowdStrike 는 Channel File 291 콘텐츠 업데이트를 배포했다. 센서 코드는 입력값 20개를 넘겼는데, 새 템플릿은 21번째 값을 읽으려 했다. 그 결과 커널에서 **범위 밖 메모리 읽기**가 일어나 시스템이 멈췄다 ([CrowdStrike RCA](https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf)). 문제 파일은 04:09~05:27 UTC 사이 78분간 배포됐다. Microsoft 는 영향받은 Windows 기기를 **약 850만 대**로 추산했다 ([Microsoft 공식 블로그, 2024-07-20](https://blogs.microsoft.com/blog/2024/07/20/helping-our-customers-through-the-crowdstrike-outage/)).

이후 Microsoft 는 **Windows Resiliency Initiative** 를 시작했다. 그 일환으로 백신·EDR 이 **커널 밖(사용자 모드)에서 돌 수 있는 Windows endpoint security platform** 의 비공개 프리뷰를 MVI 파트너에게 제공하겠다고 발표했다. 파트너에게는 링 단위 점진 배포(Safe Deployment Practices)도 의무화했다 ([Windows 블로그, 2025-06-26](https://blogs.windows.com/windowsexperience/2025/06/26/the-windows-resiliency-initiative-building-resilience-for-a-future-ready-enterprise/)). 이 전환이 탐지력에 어떤 영향을 줄지는 **아직 공개된 중립 평가가 없다.**

## 5. 한계 ④ — 녹화본은 지워진다

EDR 기록에는 보존 기한이 있다. 침입은 흔히 몇 주, 몇 달 뒤에야 발견된다.

- **MDE**: 포털 데이터는 180일 보존된다. 그러나 Advanced hunting 으로 쿼리할 수 있는 원시 데이터는 **30일**뿐이다. 더 길게 보려면 Sentinel 이나 스트리밍 API 로 따로 보내야 한다 ([Microsoft Learn — 데이터 보존](https://learn.microsoft.com/en-us/defender-xdr/data-privacy)).
- **SentinelOne**: "최대 365일" EDR 컨텍스트 보존을 내세운다 ([SentinelOne](https://www.sentinelone.com/platform/endpoint-protection-platform/), **벤더 주장**, "최대"는 라이선스·구성에 따라 다르다).

**30일 전에 들어온 공격자를 오늘 발견했다면, 기본 설정의 헌팅 화면엔 그 시작점이 이미 없을 수 있다.** 보존 기간은 기능표에서 가장 덜 읽히는 줄이지만, 사고 조사에서는 가장 먼저 부딪히는 벽이다.

## 6. 한계 ⑤ — 탐지는 대응이 아니다

EDR 은 알람을 만든다. 알람을 보고 판단하는 건 사람(SOC)이거나 사람이 미리 정한 자동화 정책이다.

CrowdStrike 보고서에 따르면 eCrime 침입자가 첫 호스트에서 다른 곳으로 옮겨 가는 **breakout time 은 평균 48분, 가장 빠른 사례는 51초**였다 (위 보고서, 벤더 관측치). 새벽 3시에 뜬 알람을 아침 9시에 보면 이미 늦다. 24시간 관제(MDR)나 자동 격리 정책이 없는 EDR 은 **사후 조사 도구**에 가깝다.

## 7. 한계 ⑥ — 원복에도 전제 조건이 있다

SentinelOne 의 롤백은 Windows **VSS 섀도 복사본**에 기대며 Windows 전용이다 ([SentinelOne FAQ](https://www.sentinelone.com/faq/), 벤더 설명). 반대로 말하면 macOS·Linux 에선 같은 방식의 원복을 기대할 수 없다. 에이전트가 먼저 죽으면(3장) 보호도 함께 사라진다. **EDR 롤백은 백업을 대신하지 못한다.**

MDE 도 비슷한 조건이 붙는다. EDR in block mode 는 Plan 2 라이선스가 필요하다. Defender 백신이 수동(passive) 모드이면 실시간 보호, 네트워크 보호, ASR 규칙이 **동작하지 않는다**고 문서에 명시돼 있다 ([Microsoft Learn](https://learn.microsoft.com/en-us/defender-endpoint/edr-in-block-mode)). 같은 제품 이름이어도 **어떤 라이선스로 어떻게 켰는지**에 따라 보호 범위가 다르다.

## 8. 그래서 누가 더 잘 잡나 — 중립 데이터가 줄었다

EDR 비교에서 가장 많이 인용되는 건 [MITRE ATT&CK Evaluations](https://evals.mitre.org/)다. 2025년 엔터프라이즈 라운드 참가사는 Acronis, AhnLab, CrowdStrike, Cyberani, Cybereason, Cynet, ESET, Sophos, Trend Micro, WatchGuard, WithSecure 11곳이다. MITRE 는 **"벤더 순위를 매기지 않는다"** 고 명시한다 ([MITRE 발표, 2025-12-10](https://www.globenewswire.com/news-release/2025/12/10/3203306/0/en/MITRE-ATT-CK-Evaluations-Advance-Cloud-Security-and-Counter-Espionage-Capabilities-in-Latest-Round.html)).

**Microsoft 와 SentinelOne(그리고 Palo Alto)은 2025년 라운드에 불참했다.** Microsoft 는 6월, SentinelOne·Palo Alto 는 9월에 불참을 알렸다 ([Infosecurity Magazine](https://www.infosecurity-magazine.com/news/cyber-vendors-pull-out-mitre/), [SecurityWeek](https://www.securityweek.com/mitre-posts-results-of-2025-attck-enterprise-evaluations/)). 그래서 **이 글이 다루는 세 제품을 같은 조건에서 비교한 2025년 중립 결과는 없다.** 참가 벤더들이 내세우는 "100% 탐지" 같은 문구는 특정 시나리오·카테고리에 한정된 수치다. 전체 성능 우열의 근거로 읽으면 안 된다.

## 9. 정리

| EDR 에 기대하는 것 | 현실 |
|---|---|
| 모든 공격을 본다 | 에이전트가 깔린 OS 만 본다. VPN 장비, SaaS, 훔친 계정은 사각지대다 |
| 공격자가 끌 수 없다 | BYOVD 로 커널에서 끈다. 드라이버 차단 목록은 완전하지 않다고 Microsoft 스스로 명시한다 |
| 깊이 볼수록 좋다 | 커널에 있으면 EDR 의 버그가 OS 장애가 된다 (2024-07, 약 850만 대) |
| 과거를 언제든 뒤질 수 있다 | MDE 기본 헌팅은 30일이다. 더 길게 보려면 별도 저장소가 필요하다 |
| 알아서 막아 준다 | 탐지와 대응은 별개다. 평균 48분 안에 판단할 사람이나 정책이 필요하다 |
| 랜섬웨어도 되돌린다 | VSS·OS·에이전트 생존이 전제다. 백업을 대신하지 못한다 |
| A 가 B 보다 낫다 | 2025년 MITRE 에서 MS·SentinelOne 이 빠져 세 제품을 비교한 중립 결과가 없다 |

**실무 체크리스트**

1. **커버리지부터 센다.** EDR 이 깔린 자산 수와 전체 자산 수를 비교한다. 네트워크 장비와 계정(IdP)은 별도 로그로 메운다.
2. **변조 방지와 드라이버 차단을 켠다.** Tamper protection, HVCI(메모리 무결성), 취약 드라이버 차단 목록, ASR "Block abuse of exploited vulnerable signed drivers" 규칙을 켠다.
3. **"센서가 조용해짐"을 알람으로 만든다.** 에이전트가 꺼지거나 텔레메트리가 끊기는 것 자체가 EDR Killer 의 흔적이다.
4. **보존 기간을 사고 탐지 시점에 맞춘다.** 30일로 부족하면 SIEM 이나 스트리밍으로 원시 로그를 따로 쌓는다.
5. **새벽 3시 알람은 누가 보는가**에 답한다. 답이 없으면 자동 격리 정책이나 MDR 을 검토한다.
6. **백업은 EDR 과 별개로, 오프라인으로** 둔다.

EDR 은 가장 강력한 눈이다. 다만 **눈은 달린 곳만 보고, 감길 수 있고, 본 것을 오래 기억하지 못한다.**

## References

- CrowdStrike, *External Technical Root Cause Analysis — Channel File 291* (2024-08-06) — <https://www.crowdstrike.com/wp-content/uploads/2024/08/Channel-File-291-Incident-Root-Cause-Analysis-08.06.2024.pdf>
- CrowdStrike, *Technical Details: Falcon Update for Windows Hosts* (2024-07-20) — <https://www.crowdstrike.com/en-us/blog/falcon-update-for-windows-hosts-technical-details/>
- CrowdStrike, *2025 Global Threat Report* (벤더 자체 관측치) — <https://www.crowdstrike.com/en-us/press-releases/crowdstrike-releases-2025-global-threat-report/>
- Microsoft, *Helping our customers through the CrowdStrike outage* (2024-07-20) — <https://blogs.microsoft.com/blog/2024/07/20/helping-our-customers-through-the-crowdstrike-outage/>
- Microsoft, *The Windows Resiliency Initiative* (2025-06-26) — <https://blogs.windows.com/windowsexperience/2025/06/26/the-windows-resiliency-initiative-building-resilience-for-a-future-ready-enterprise/>
- Microsoft Learn, *EDR in block mode* — <https://learn.microsoft.com/en-us/defender-endpoint/edr-in-block-mode>
- Microsoft Learn, *Tamper resiliency with Defender for Endpoint* — <https://learn.microsoft.com/en-us/defender-endpoint/tamper-resiliency>
- Microsoft Learn, *Advanced hunting overview* — <https://learn.microsoft.com/en-us/defender-xdr/advanced-hunting-overview>
- Microsoft Learn, *Data security and retention in Microsoft Defender XDR* — <https://learn.microsoft.com/en-us/defender-xdr/data-privacy>
- Microsoft Learn, *Microsoft recommended driver block rules* — <https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/microsoft-recommended-driver-block-rules>
- SentinelOne, *Singularity Endpoint* (벤더) — <https://www.sentinelone.com/platform/endpoint-protection-platform/>
- SentinelOne, *FAQ* (벤더) — <https://www.sentinelone.com/faq/>
- SecurityWeek, *MITRE Posts Results of 2025 ATT&CK Enterprise Evaluations* — <https://www.securityweek.com/mitre-posts-results-of-2025-attck-enterprise-evaluations/>
- MITRE ATT&CK, *T1562.001 Impair Defenses: Disable or Modify Tools* — <https://attack.mitre.org/techniques/T1562/001/>
- MITRE, *ATT&CK Evaluations Enterprise 2025 발표* (2025-12-10) — <https://www.globenewswire.com/news-release/2025/12/10/3203306/0/en/MITRE-ATT-CK-Evaluations-Advance-Cloud-Security-and-Counter-Espionage-Capabilities-in-Latest-Round.html>
- MITRE, *ATT&CK Evaluations 결과* — <https://evals.mitre.org/>
- Infosecurity Magazine, *Cyber vendors pull out of MITRE evaluations* — <https://www.infosecurity-magazine.com/news/cyber-vendors-pull-out-mitre/>
- Sophos X-Ops, *EDRKillShifter* (벤더 연구, 2024-08) — <https://www.sophos.com/en-us/blog/edr-kill-shifter>
- ESET, *What are EDR killers?* (벤더 연구, 2026-04) — <https://www.eset.com/blog/en/business-topics/threat-landscape/what-are-edr-killers/>
- Huntress, *EnCase BYOVD EDR killer* (벤더 사고 분석, 2026-02) — <https://www.huntress.com/blog/encase-byovd-edr-killer>
