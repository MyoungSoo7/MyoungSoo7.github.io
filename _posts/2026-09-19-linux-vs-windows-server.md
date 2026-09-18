---
layout: post
title: "리눅스 서버와 윈도우 서버는 무엇이 다른가 — 1차 출처로 짚는 실무 차이"
date: 2026-09-19 03:35:33 +0900
categories: [infra, os]
tags: [linux, windows-server, licensing, server-core, container, hotpatch, lifecycle]
---

"리눅스 서버랑 윈도우 서버 뭐가 달라요?" 라는 질문에 흔히 돌아오는 답은 "리눅스는 공짜고 CLI, 윈도우는 유료고 GUI" 정도다. 틀린 말은 아니지만, 실제로 운영을 시작하면 이 요약은 거의 쓸모가 없다. 비용이 어디서 발생하는지, 재부팅을 언제 해야 하는지, 컨테이너를 몇 개까지 돌릴 수 있는지, 3년 뒤에 이 OS가 아직 패치를 받는지 — 결정을 바꾸는 건 이런 것들이다.

이 글은 그 차이를 **벤더 1차 문서와 공식 사양**만으로 정리한다. 가격표는 지역·계약 형태에 따라 달라지므로 금액은 적지 않고, 대신 **"무엇을 세어서 돈을 내는가"** 라는 과금 구조를 본다. 성능 우열은 다루지 않는다 — 동일 조건에서 두 OS를 비교한 중립적 제3자 벤치마크가 공개적으로 부재하기 때문에, 그런 주장은 근거를 댈 수 없다.

---

## 1. 과금 단위가 다르다 — 코어+접속자 vs 인스턴스

가장 큰 구조적 차이는 여기서 시작한다. **윈도우 서버는 "서버의 코어 수"와 "접속하는 사람/기기 수"를 따로 센다.**

Microsoft 공식 라이선스 가이드에 따르면 Windows Server 2025 Standard·Datacenter는 코어 기반(core-based) 모델이며, 물리 코어 기준으로 라이선스할 경우:

- 서버의 **모든 물리 코어**를 라이선스해야 한다
- **물리 프로세서당 최소 8 코어**
- **서버당 최소 16 코어**

즉 4코어짜리 1소켓 장비여도 16 코어 라이선스를 사야 한다. 코어 라이선스는 2개 팩과 16개 팩으로 판매된다. 가상 머신 단위 라이선스도 2022년 10월에 추가됐는데, 이건 구독 라이선스 또는 Software Assurance가 활성화된 고객만 선택할 수 있고 VM당 최소 8 코어다.<sup>[[1]](#ref1)</sup>

그리고 **여기서 끝이 아니다.** 코어 라이선스를 다 샀어도, 그 서버에 접근하는 사용자 또는 장치마다 **CAL(Client Access License)** 이 별도로 필요하다. 원격 데스크톱을 쓰려면 기본 CAL 위에 RDS CAL이 추가로 붙는다(Additive CAL). 외부 사용자는 CAL 대신 External Connector로 묶을 수도 있다.<sup>[[1]](#ref1)</sup><sup>[[2]](#ref2)</sup>

Microsoft 자신의 문서가 이 구조를 명확히 대비시켜 준다. SQL Server 같은 순수 Per Core 모델은 "방화벽 안팎에서 무제한 사용자 접속을 허용하며 CAL이 필요 없다"고 적혀 있는 반면, Windows Server는 **Per Core/CAL** 모델이라 둘 다 필요하다.<sup>[[2]](#ref2)</sup>

반면 **리눅스는 OS 자체에 접속자 과금 개념이 없다.** 커널은 GPL-2.0 only로 배포되고(syscall 예외 포함), 소스 파일마다 SPDX 식별자로 라이선스가 명시된다.<sup>[[3]](#ref3)</sup> 배포판 벤더에 돈을 낸다면 그건 라이선스가 아니라 **구독(subscription)** 이다.

Red Hat의 과금 단위는 "설치/실행되는 인스턴스" 다. Red Hat은 자사 구독 모델 FAQ에서 "설치되거나 실행 중인 리소스 수를 세고 각 인스턴스에 구독료를 적용한다"고 직접 설명한다. 물리 배포는 소켓 페어(2소켓) 기준, 가상 배포는 가상 노드 기준이다.<sup>[[4]](#ref4)</sup><sup>[[5]](#ref5)</sup> 구독은 특정 버전이 아니라 "Red Hat Enterprise Linux"라는 제품에 대한 것이라, 새 버전이 나와도 추가 라이선스 구매 없이 올라갈 수 있다.<sup>[[5]](#ref5)</sup>

정리하면 이렇다.

| | Windows Server 2025 | RHEL |
|---|---|---|
| 세는 대상 | 물리 코어(또는 VM의 vCPU) | 설치 인스턴스 (소켓 페어 / 가상 노드) |
| 최소 단위 | 프로세서당 8, 서버당 16 코어 | 소켓 페어당 1 구독 |
| 접속자 과금 | **있음 (CAL / External Connector)** | 없음 |
| 미결제 상태 | 라이선스 위반 | 소프트웨어는 동작, **리포지터리 접근 불가** |

마지막 줄이 실무적으로 중요하다. RHEL은 등록하지 않으면 리포지터리에 접근할 수 없어 **보안 업데이트·버그 픽스를 받을 수 없다.** 구독의 본질은 "실행 권한"이 아니라 "업데이트와 지원에 대한 접근권"이다.<sup>[[6]](#ref6)</sup>

Ubuntu는 또 다른 지점을 찍는다. LTS는 구독 없이도 5년간 Main 저장소 패키지에 대한 보안 유지보수를 받는다. 그 이상은 Ubuntu Pro 구독이고, 개인 용도로는 최대 5대까지 무료다.<sup>[[7]](#ref7)</sup>

---

## 2. GUI는 옵션이고, 되돌릴 수 없다

"윈도우는 GUI, 리눅스는 CLI"는 2026년 기준으로는 절반만 맞다. Windows Server는 설치 시점에 **Server Core**와 **Server with Desktop Experience** 중 하나를 고르는데, Microsoft 공식 문서의 권고는 명확하다:

> "추가적인 UI 요소와 그래픽 관리 도구가 특별히 필요한 경우가 아니라면 **Server Core 설치 옵션을 선택할 것을 권장합니다.**"<sup>[[8]](#ref8)</sup>

Server Core에는 데스크톱이 아예 없다. GUI 셸 패키지(`Microsoft-Windows-Server-Shell-Package` 등)가 빠져 있고, 접근성 도구·오디오 지원·OOBE도 없다. 관리는 PowerShell, SConfig, 또는 원격으로 RSAT·Windows Admin Center를 쓴다.<sup>[[9]](#ref9)</sup>

그 대가로 얻는 건 디스크 사용량 감소와 **공격 표면 축소**다. Microsoft는 비교표에 "잠재적 공격 표면: 대폭 감소 / 감소 없음"이라고 직접 적어 뒀다.<sup>[[8]](#ref8)</sup>

**여기에 함정이 하나 있다.** 과거 버전과 달리 지금은 설치 후 Server Core ↔ Desktop Experience **전환이 불가능하다.** 나중에 마음이 바뀌면 클린 설치를 다시 해야 한다.<sup>[[8]](#ref8)</sup> 리눅스에서 `apt install ubuntu-desktop` 한 줄로 GUI를 얹거나 걷어내는 것과는 성격이 완전히 다른 결정이다. 설치 화면에서 내리는 이 선택이 사실상 되돌릴 수 없는 아키텍처 결정이라는 점을, 처음 윈도우 서버를 세우는 사람이 가장 많이 놓친다.

또 하나 주의할 점: Server Core에는 모든 역할이 들어 있지 않다. 예를 들어 **Remote Desktop Session Host는 Server Core 이미지에 포함되지 않는다.** 일부 기능은 App Compatibility Feature on Demand(FOD)로 따로 설치해야 한다.<sup>[[9]](#ref9)</sup><sup>[[10]](#ref10)</sup>

---

## 3. 재부팅 — 오래된 격차가 최근에 좁혀졌다

"리눅스는 커널 빼고 재부팅이 거의 없는데 윈도우는 매달 재부팅한다"는 인식은 오랫동안 사실에 가까웠다. 이 격차는 양쪽 다 라이브 패칭으로 메우고 있다.

**리눅스 쪽.** Red Hat은 구독에 포함된 `kpatch`를 "재부팅 없이 실행 중인 커널을 패치"하는 수단으로 명시한다. 장시간 작업이 끝나기를, 사용자가 로그아웃하기를, SLA 윈도우가 열리기를 기다리지 않고 긴급 커널 보안 패치를 즉시 적용할 수 있다는 것이다.<sup>[[5]](#ref5)</sup> Canonical도 Ubuntu Pro에 Kernel Livepatch를 포함한다.<sup>[[7]](#ref7)</sup>

**윈도우 쪽.** Windows Server 2025부터 **Hotpatch**가 들어왔다. 실행 중인 프로세스의 **인메모리 코드를 패치**해서, 프로세스 재시작도 머신 재부팅도 없이 OS 보안 업데이트를 설치한다.<sup>[[11]](#ref11)</sup>

다만 조건이 붙는다. 이건 구조를 정확히 알아야 계획을 세울 수 있다:

- Windows Server 2025 **Standard 또는 Datacenter** 여야 한다
- 머신이 **Azure Arc에 연결**되어 있어야 한다 (온프레미스·타 클라우드 포함)
- **VBS(가상화 기반 보안)가 활성화**되어 있어야 하고, VBS를 켠 뒤에는 재부팅이 필요하다
- **분기마다 baseline 재부팅이 있다.** 1·4·7·10월에는 누적 보안 업데이트를 설치하고 반드시 재부팅해야 하며, 나머지 두 달만 무재부팅 hotpatch를 받는다 — 연 8회 hotpatch, 4회 재부팅
- **자동 롤백이 없다.** 문제가 생기면 최신 업데이트를 제거하고 마지막 정상 baseline을 설치해야 하며, 이 과정은 재부팅을 요구한다<sup>[[11]](#ref11)</sup>

Azure Arc 연결 머신에 대해 이 기능은 **추가 비용 없이** 제공된다고 Microsoft가 공지했다.<sup>[[12]](#ref12)</sup>

실무적 함의는 이렇다. 윈도우 서버의 무재부팅 패칭은 이제 "가능"하지만, **Azure 관리 평면에 서버를 등록한다는 전제 조건**이 붙는다. 완전 격리 온프레미스 환경이라면 이 선택지는 사라진다. 리눅스의 kpatch/Livepatch는 벤더 구독만 있으면 되고 클라우드 관리 평면 연결을 요구하지 않는다는 점이, 지금 시점에서 가장 실질적인 차이다.

---

## 4. 컨테이너 — 커널이 곧 경계다

컨테이너는 커널 기능 위에 서 있으므로, 커널이 다르면 컨테이너도 다르다.

Windows 컨테이너에는 두 가지 격리 모드가 있고, Microsoft 문서가 그 차이를 솔직하게 서술한다.

**프로세스 격리(process isolation)** — 네임스페이스와 리소스 제어로 격리하며, **컨테이너들이 호스트와 커널을 공유한다.** Microsoft는 이것을 "리눅스 컨테이너가 동작하는 방식과 대략 같다"고 설명한다.<sup>[[13]](#ref13)</sup>

**Hyper-V 격리** — 각 컨테이너가 고도로 최적화된 VM 안에서 돌고 **사실상 자체 커널을 갖는다.** 하드웨어 수준 격리를 제공한다.<sup>[[13]](#ref13)</sup>

보안 문서는 더 직설적이다. Microsoft는 프로세스 격리 Windows 컨테이너와 리눅스 컨테이너 **둘 다** 견고한 보안 경계로 보지 않으며, 적대적 멀티테넌트 환경에서는 사용하지 말라고 못박는다. 그래서 프로세스 격리 컨테이너의 탈출은 MSRC 보안 프로세스가 아니라 일반 서비싱으로 처리된다.<sup>[[14]](#ref14)</sup>

여기서 **라이선스가 아키텍처를 제약하는 지점**이 나온다. Windows 컨테이너 이미지 EULA에 따른 호스트 OS 에디션별 실행 한도는 다음과 같다:<sup>[[15]](#ref15)</sup>

| 호스트 OS | 프로세스 격리 | Hyper-V 격리 |
|---|---|---|
| Windows Server Standard | 무제한 | **2개** |
| Windows Server Datacenter | 무제한 | 무제한 |

즉 신뢰할 수 없는 워크로드를 격리해서 돌려야 하는데 Standard를 샀다면, 노드당 2개가 상한이다. 리눅스 쪽에는 이런 형태의 OS 라이선스에 의한 컨테이너 개수 제한이 없다 — 대신 커널 공유라는 동일한 보안 한계를 갖고, 그 해법으로 gVisor·Kata Containers 같은 별도 런타임을 얹는다.

이미지 자체도 호환되지 않는다. 컨테이너 안의 바이너리는 호스트 커널의 API를 쓰므로, **리눅스 컨테이너 이미지는 윈도우 커널 위에서 그대로 돌지 않는다.** 윈도우에서 리눅스 컨테이너를 돌린다는 건 실제로는 경량 VM 안의 리눅스 커널 위에서 돌린다는 뜻이다.

---

## 5. 수명주기 — 3년 뒤를 결정하는 표

OS 선택은 사실상 "언제 마이그레이션할 것인가"를 함께 정하는 일이다.

**Windows Server 2025** 는 Fixed Lifecycle Policy를 따른다. 2024년 11월 1일 출시, **메인스트림 지원 종료 2029년 11월 13일**, **확장 지원 종료 2034년 11월 14일** — 총 10년이다.<sup>[[16]](#ref16)</sup><sup>[[17]](#ref17)</sup>

참고로 **Windows Server 2022의 메인스트림 지원은 2026년 10월 13일에 끝난다.** 이 글을 쓰는 2026년 9월 기준으로 한 달 남았다.<sup>[[17]](#ref17)</sup> 2022로 신규 구축을 검토 중이라면 이 날짜를 먼저 봐야 한다.

**RHEL** 은 모든 구독이 메이저 릴리스당 10년 지원을 제공한다. 추가 구독으로 특정 마이너 릴리스에 머무를 수 있는 옵션도 있다.<sup>[[5]](#ref5)</sup>

**Ubuntu LTS** 는 층이 가장 많다. 2년마다 LTS가 나오고, 무상 표준 보안 유지보수 5년 → Ubuntu Pro의 ESM으로 10년 → Legacy 애드온으로 **최대 15년**까지 간다.<sup>[[7]](#ref7)</sup><sup>[[18]](#ref18)</sup>

| | 무상 지원 | 유상 포함 최대 |
|---|---|---|
| Windows Server 2025 | — (라이선스 자체가 유상) | 10년 (2034-11-14) |
| RHEL | — | 10년 / 메이저 릴리스 |
| Ubuntu LTS | 5년 | 15년 (Pro + Legacy) |

Windows Server 칸의 "무상 지원 없음"은 비난이 아니라 모델의 차이다. 윈도우는 라이선스를 사는 순간 10년치 지원이 따라오고, 리눅스는 OS를 무상으로 쓰되 지원을 별도로 산다. **총비용을 비교하려면 "OS 값"이 아니라 "10년치 지원 + 접속자 수 + 코어 수"를 같은 테이블에 올려야 한다.**

---

## 6. 그래서 어떻게 고르는가

기술적 우월이 아니라 제약 조건에서 답이 나온다.

**윈도우 서버가 정답인 경우**
- Active Directory 도메인 서비스가 조직의 인증 축이고, 그룹 정책으로 클라이언트를 관리한다
- .NET Framework(‑Core가 아닌) 레거시 앱, MSMQ, IIS 특화 스택, COM+ 의존 앱을 그대로 들고 가야 한다
- 이미 Microsoft EA/구독 계약이 있어 CAL 비용이 한계비용으로 작게 잡힌다
- 관리 인력의 숙련도가 PowerShell·Windows Admin Center 쪽에 쌓여 있다

**리눅스가 정답인 경우**
- 워크로드가 컨테이너·쿠버네티스 기반이고 노드 수가 늘었다 줄었다 한다 (코어 최소치 16과 CAL이 스케일에 그대로 곱해진다)
- 접속 주체가 사람이 아니라 서비스라서 CAL 모델이 개념적으로 안 맞는다
- 완전 격리 환경이라 Azure Arc 연결을 전제할 수 없는데 무재부팅 패칭은 필요하다
- 이미지 빌드·설정 관리 전 과정을 코드로 재현해야 한다

**혼재가 정상인 경우 (대부분)**
현실의 조직은 대개 도메인 컨트롤러와 파일 서버는 윈도우, 애플리케이션 런타임과 쿠버네티스 노드는 리눅스다. 이때 검토할 것은 "어느 쪽으로 통일하나"가 아니라 **경계를 어디에 그어야 인증·백업·모니터링이 두 벌로 갈라지지 않는가** 이다. 두 OS를 다 쓰는 비용은 라이선스가 아니라 **운영 도구의 이중화**에서 나온다.

---

## 마치며

세 가지만 남기고 싶다.

1. **비용은 "OS 가격"이 아니라 "과금 단위"의 문제다.** 코어 최소치 16과 접속자별 CAL은 스케일 아웃 설계에서 예상 밖으로 크게 곱해진다. 반대로 접속 주체가 소수이고 노드가 몇 대 안 되는 환경에서는 무시할 만한 차이일 수도 있다. 자기 토폴로지에 대입해 보기 전에는 아무것도 결정된 게 아니다.
2. **"윈도우 = GUI"라는 전제를 버려라.** Microsoft 본인이 Server Core를 권장하고, 그 선택은 설치 후 되돌릴 수 없다.
3. **재부팅 격차는 좁혀졌지만 조건부다.** Windows Server 2025의 Hotpatch는 실제로 동작하지만 Azure Arc 연결과 VBS를 요구하고 분기 재부팅이 남는다.

그리고 아직 답이 없는 부분도 분명히 해 두자. **동일 하드웨어·동일 워크로드에서 두 OS를 비교한, 벤더 중립적이고 재현 가능한 공개 벤치마크는 사실상 존재하지 않는다.** 그래서 이 글에는 성능 비교가 없다. "리눅스가 더 빠르다" 류의 주장을 보면 측정 조건과 주체를 먼저 확인하는 편이 낫고, 대부분의 경우 그 조건은 공개되어 있지 않다.

---

## References

1. <a id="ref1"></a>Microsoft, *Windows Server 2025 Licensing Guidance* — [microsoft.com/licensing/guidance/Windows-Server-2025](https://www.microsoft.com/licensing/guidance/Windows-Server-2025)
2. <a id="ref2"></a>Microsoft, *Core Based Licensing Models — Licensing Guidance* — [microsoft.com/licensing/guidance/Core-based-licensing-models](https://www.microsoft.com/licensing/guidance/Core-based-licensing-models)
3. <a id="ref3"></a>The Linux Kernel, *Linux kernel licensing rules* — [docs.kernel.org/process/license-rules.html](https://www.kernel.org/doc/html/latest/process/license-rules.html)
4. <a id="ref4"></a>Red Hat, *Red Hat subscription model FAQ* — [redhat.com/en/about/subscription-model-faq](https://www.redhat.com/en/about/subscription-model-faq)
5. <a id="ref5"></a>Red Hat, *Red Hat Enterprise Linux subscription guide* (PDF) — [redhat.com](https://www.redhat.com/rhdc/managed-files/li-red-hat-enterprise-linux-subscription-guide-2562450pr-202511-en.pdf)
6. <a id="ref6"></a>Red Hat Documentation, *Configuring basic system settings — Registering the system and managing subscriptions (RHEL 9)* — [docs.redhat.com](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_basic_system_settings/assembly_registering-the-system-and-managing-subscriptions_configuring-basic-system-settings)
7. <a id="ref7"></a>Canonical, *Ubuntu release cycle* — [ubuntu.com/about/release-cycle](https://ubuntu.com/about/release-cycle)
8. <a id="ref8"></a>Microsoft Learn, *Server Core vs Server with Desktop Experience install options* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-server/get-started/install-options-server-core-desktop-experience)
9. <a id="ref9"></a>Microsoft Learn, *What is Server Core?* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-server/administration/server-core/what-is-server-core)
10. <a id="ref10"></a>Microsoft Learn, *Roles, Role Services, and Features included in Windows Server — Server Core* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-server/administration/server-core/server-core-roles-and-services)
11. <a id="ref11"></a>Microsoft Learn, *Hotpatch for Windows Server* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-server/get-started/hotpatch)
12. <a id="ref12"></a>Microsoft Learn, *Enable Hotpatch for Azure Arc-enabled servers* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows-server/get-started/enable-hotpatch-azure-arc-enabled-servers)
13. <a id="ref13"></a>Microsoft Learn, *Isolation modes (Windows containers)* — [learn.microsoft.com](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/hyperv-container)
14. <a id="ref14"></a>Microsoft Learn, *Secure Windows containers* — [learn.microsoft.com](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-security)
15. <a id="ref15"></a>Microsoft Learn, *Windows containers FAQ* — [learn.microsoft.com](https://learn.microsoft.com/en-us/virtualization/windowscontainers/about/faq)
16. <a id="ref16"></a>Microsoft Lifecycle, *Windows Server 2025* — [learn.microsoft.com/lifecycle/products/windows-server-2025](https://learn.microsoft.com/en-us/lifecycle/products/windows-server-2025)
17. <a id="ref17"></a>Microsoft Learn, *Windows Server release information* — [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/release-health/windows-server-release-info)
18. <a id="ref18"></a>Canonical, *Ubuntu Expanded Security Maintenance* — [ubuntu.com/security/esm](https://ubuntu.com/security/esm)

> 본문의 라이선스·수명주기 수치는 모두 위 1차 문서에서 확인한 값이며, 2026년 9월 기준이다. 라이선스 조건은 계약 형태(EA, CSP, OEM)와 지역에 따라 달라질 수 있으므로 실제 구매 전에는 Microsoft Product Terms 및 Red Hat Enterprise Agreement 원문을 확인해야 한다.
