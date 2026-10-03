---
layout: post
title: "ATM 관리 시스템이 지키는 두 가지 — 관리 기능 자체가 공격면이 될 때, 그리고 현금이 떨어지지 않게 하는 예측"
date: 2026-10-03 22:00:14 +0900
categories: [아키텍처, 금융]
tags: [ATM, XFS, XFS4IoT, jackpotting, 재킹팟, Ploutus, 현금수요예측, 보충최적화, PCI, 시스템설계]
---

ATM 관리 시스템은 앞선 두 글에서 이미 다뤘다. [여섯 계층](/2026/09/09/atm-management-system-six-layers/)에서는 통신, 데이터 수집, 운영 서버, 관리 화면, 배포·설정, 외부 연동이 각각 왜 생겼는지를 봤다. [로컬 테스트가 재현하지 못하는 것](/2026/09/09/global-atm-management-beyond-local-testing/)에서는 두 세대의 표준(XFS 3.x / XFS4IoT), ISO 8583, 키 관리, 유럽의 물리 공격 통계를 봤다.

이번 글은 그 두 글이 비워 둔 자리 두 곳을 채운다.

1. **관리 기능 자체가 공격면이 되는 문제.** 원격으로 장비를 다루는 능력이 그대로 공격자의 능력이 된다.
2. **현금이 떨어지지 않게 하는 문제.** ATM 관리의 운영 비용 대부분은 소프트웨어가 아니라 현금의 이자, 수송, 보험에서 나온다.

정산(거래 대사·회계 처리)은 범위 밖이다.

---

## 0. 배경 — 줄어드는 단말, 커지는 대당 관리 비용

국내 은행 ATM 은 빠르게 줄고 있다. 국회의원실이 금융감독원에서 받은 자료를 보도한 기사에 따르면, 15개 은행의 ATM 은 2019년 말 36,146대에서 2024년 7월 말 27,076대로 25% 줄었다 ([연합뉴스, 2024-09-16](https://www.yna.co.kr/view/AKR20240914040800002)). 2025년 7월 말에는 25,987대다 ([매일경제, 2025-09-22](https://www.mk.co.kr/news/economy/11425581)). 은행들은 그 이유로 관리·냉난방 같은 유지 비용을 든다.

한국은행은 이 흐름을 **현금 접근성** 문제로 본다. 2021년 기준 ATM 의 41.3% 가 수도권에 있고, 단위면적당 ATM 수는 서울과 강원·경북·전남 사이에 약 92배 차이가 난다 ([한국은행, *현금접근성에 대해 알고 계시나요?*](https://www.bok.or.kr/portal/bbs/P0000547/view.do?depth=200387&menuNo=200387&nttId=10083214&oldMenuNo=201150&programType=newsData&relate=Y)).

관리 시스템 관점에서 이 숫자가 뜻하는 것은 단순하다. **대수가 줄면 한 대가 멈췄을 때의 영향이 커지고, 남은 단말 한 대당 관리 비용을 낮추라는 압력도 커진다.** 그래서 "원격으로 얼마나 많이 다룰 수 있나" 가 핵심 경쟁력이 된다. 그런데 바로 그 원격 능력이 아래 1장의 문제를 만든다.

---

## 1. 관리 기능이 공격면이 될 때

### 1-1. XFS 는 "돈을 내보내라" 를 말할 수 있는 계층이다

ATM 애플리케이션은 디스펜서, 카드 리더, PIN 패드 같은 장치를 직접 다루지 않는다. CEN 이 표준화한 **XFS(eXtensions for Financial Services)** 미들웨어를 거쳐 명령을 보낸다. 제조사가 달라도 같은 애플리케이션이 돌게 하려는 설계다.

미국 FBI 는 2026년 2월 FLASH 경보에서 이 구조가 정확히 공격 경로가 된다고 설명한다 ([FBI FLASH, 2026-02-19](https://www.ic3.gov/CSA/2026/260219.pdf)).

> Ploutus 악성코드는 XFS 를 악용한다. 정상 거래에서는 ATM 애플리케이션이 XFS 를 통해 명령을 보내기 전에 은행 승인을 받는다. 공격자가 XFS 에 직접 명령을 내릴 수 있으면 은행 승인을 통째로 건너뛰고 현금 배출을 지시할 수 있다. (FBI FLASH 요지)

같은 경보의 수치:

- 2020년 이후 보고된 ATM 재킹팟(jackpotting) 사건은 **약 1,900건** 이다.
- 그중 **700건 이상이 2025년 한 해** 에 발생했고, 2025년 손실은 **2,000만 달러 이상** 이다.

감염 경로는 대부분 물리적이다. **시중에 도는 범용 열쇠로 상단 함체를 연다.** 그다음 하드디스크를 빼서 악성코드를 복사해 다시 넣거나, 악성코드가 미리 담긴 디스크로 바꿔 끼우고 재부팅한다 ([FBI FLASH](https://www.ic3.gov/CSA/2026/260219.pdf)).

### 1-2. 블랙박스 — 소프트웨어를 아예 건너뛴다

더 거친 방식도 있다. Diebold Nixdorf 는 2020년 보안 경보에서, 공격자가 함체를 부수고 **디스펜서와 ATM PC 사이의 USB 케이블을 뽑아 자기 장치("블랙박스")에 연결** 하는 사례를 보고했다. 이 장치에서 디스펜서로 직접 배출 명령을 보낸다 ([Diebold Nixdorf Security Alert, 2020-07-15](https://s3.documentcloud.org/documents/6989897/Diebold-Nixdorf-warning-of-new-ATM-attacks.pdf)). 블랙박스 안에서 해당 ATM 소프트웨어 스택 일부가 발견되기도 했다. Diebold 는 **암호화되지 않은 하드디스크를 오프라인으로 털었을 가능성** 을 언급했다.

이 경로는 XFS 보호도 우회한다. 그래서 대책은 디스펜서 쪽에 있다. **디스펜서와 PC 사이의 통신을 암호화하고, 둘을 물리적으로 인증(페어링)** 해서, 모르는 장치가 붙으면 배출을 거부하게 하는 것이다.

### 1-3. 원격 관리 도구(RMS) 자체가 털린다

관리 시스템 설계자에게 가장 뼈아픈 사례는 이것이다. 미국 비밀경호국(USSS)은 2024년 경보에서 **소매점 ATM 의 원격 관리 소프트웨어(Remote Management Solutions, RMS)** 를 노린 공격을 보고했다 ([USSS GIOC Alert #24-006-I, 2024](https://www.oba.com/wp-content/uploads/2024/06/24-006-I-New-Jackpotting-Attack-Vector-TLP-Green-Alert.pdf)).

- 공격자는 악성 IP 에서 RMS 를 사칭해 중간자(MiTM) 공격을 했다.
- 이를 통해 **최대 인출 한도를 올리고, 거절된 거래를 모두 승인으로 바꿨다.**
- 그 결과 카드 계좌가 아니라 **ATM 운영자 쪽이 차감** 됐다.
- 경보의 권고는 기본 비밀번호 변경과 RMS 의 SSL 활성화다. 무선 회선을 쓰는 ATM 은 특히 그렇다.

여기서 교훈은 구조적이다. **"원격으로 한도를 바꿀 수 있다" 는 관리 기능은, 인증이 약하면 "원격으로 돈을 빼낼 수 있다" 와 같은 말이 된다.** 관리 시스템의 설정 변경 API 는 거래 승인 API 와 같은 등급으로 보호해야 한다.

### 1-4. 유럽은 줄었는데 미국은 늘었다 — 위협은 지역 변수다

[이전 글](/2026/09/09/global-atm-management-beyond-local-testing/)에서 본 EAST 의 2024년 유럽 통계에서는 ATM 논리 공격이 7건에서 3건으로 줄었고 손실은 0이었다. 반면 FBI 는 2025년 미국에서만 700건 이상을 보고했다. 두 자료는 집계 기관, 범위, 정의가 달라 직접 비교할 수 없다. 다만 **"논리 공격은 끝난 위협" 이라고 일반화하면 안 된다** 는 점은 분명하다. 글로벌 관리 시스템이라면 위협 모델을 지역별 설정값으로 둬야 한다.

### 1-5. 관리 시스템이 할 수 있는 방어

FBI, USSS, Diebold, 미국 인디애나주 금융감독국의 권고를 **관리 시스템이 직접 맡을 수 있는 것** 만 추리면 다음과 같다 ([FBI FLASH](https://www.ic3.gov/CSA/2026/260219.pdf); [USSS #24-005-I](https://www.oba.com/wp-content/uploads/2024/06/24-005-I-Uptick-in-Jackpotting-Alert-TLP-Green.pdf); [Diebold Nixdorf](https://s3.documentcloud.org/documents/6989897/Diebold-Nixdorf-warning-of-new-ATM-attacks.pdf); [Indiana DFI Advisory 2025-04](https://www.in.gov/dfi/files/DFI-Advisory-Letter-2025-04-ATM-or-ITM-Jackpotting-Occurrences.pdf)).

| 신호 / 통제 | 관리 시스템에서의 구현 | 출처 |
| --- | --- | --- |
| **골드 이미지 무결성** | 배포 시 서명된 기준 이미지의 해시를 보관하고, 단말이 정기 보고하는 해시와 대조한다. 어긋나면 침해로 간주한다 | FBI |
| **이동식 저장장치 감사** | Windows 고급 감사 정책 'Audit Removable Storage' → 이벤트 ID 6416, SACL 을 건 파일 접근 → 4663 을 중앙으로 수집한다 | FBI |
| **함체 개방 이벤트** | 상단 함체(top hat) 개방이 정비 일정과 맞지 않으면 즉시 경보를 띄우고, 필요하면 전원을 차단한다 | Diebold, Indiana DFI |
| **디스펜서 연결 끊김** | 디스펜서 통신 단절 후 거래 패턴이 이상하면 조사한다(블랙박스 징후) | Diebold |
| **IOC 조합 시 자동 정지** | 여러 징후가 겹치면 단말을 자동으로 "서비스 중지" 로 돌려 배출을 막는다 | FBI |
| **이상 배출 패턴** | 카드 없는 대량 인출, 예고 없는 오프라인 전환에 경보를 띄운다 | Indiana DFI |
| **원격 관리 채널** | 기본 비밀번호를 금지하고, TLS 와 메시지 인증(MAC)을 쓰고, 정비 인력은 2단계 인증 | USSS, Diebold |
| **하드디스크 암호화** | 오프라인 공격(디스크를 빼서 털기)을 막는다. 상태는 관리 시스템이 상시 점검한다 | USSS, Diebold |

표의 공통점은 **대부분 "이벤트를 모아서 대조하는 일"** 이라는 것이다. 단말 한 대 안에서는 정상처럼 보여도, 중앙에서 정비 일정·해시 기준선·거래 패턴과 맞춰 보면 이상이 드러난다. 보안 측면에서 관리 시스템의 본업은 이 **대조** 다.

PCI SSC 의 *ATM Security Guidelines* (2013) 도 같은 맥락이다. 하드웨어 통합, 기본 소프트웨어, 애플리케이션 관리와 나란히 **"장치 관리·운영"** 을 독립 영역으로 둔다. 제조 단계, 보관 중, 배치된 단말군, 단말별 보안 설정을 각각 관리 대상으로 명시한다 ([PCI SSC 보도자료, 2013-01-30](https://www.pcisecuritystandards.org/about_us/press_releases/pci-security-standards-council-publishes-atm-security-guidelines/); [Information Supplement PDF](https://listings.pcisecuritystandards.org/pdfs/PCI_ATM_Security_Guidelines_Info_Supplement.pdf)).

### 1-6. XFS4IoT 는 이 문제를 어떻게 다루나

XFS 의 다음 세대인 **XFS4IoT** (CEN CWA 17852) 는 Windows 전용 바이너리 API 를 **WebSocket 위의 JSON 메시지** 로 바꾸고 OS 독립을 목표로 한다. 장치를 로컬뿐 아니라 클라우드 애플리케이션에서도 제어·감시할 수 있게 하는 것이 공식 목표다 ([CEN-CENELEC, CWA 17852](https://www.cencenelec.eu/areas-of-work/xfs_cwa17852_release2021-1/); [XFS4IoT Specification 2024-03](https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA17852/cwa17852_2024-03-release_2025.pdf)).

보안 관점에서 중요한 점은 사양의 요구사항에 **"애플리케이션 수준 종단 간(E2E) 보안 지원"** 이 들어가 있다는 것이다. E2E 토큰을 `CashDispenser.Dispense` 같은 명령에 실어 보내고, 서비스는 그 토큰을 검증한다 ([XFS4IoT Specification](https://xfs4iot.github.io/Specifications-Preview.github.io/html/index.html)). 1-1 의 "XFS 에 직접 명령을 넣으면 승인을 건너뛴다" 는 구멍을, **배출 명령 자체가 승인 증거를 들고 다니게** 해서 막으려는 설계로 읽힌다.

다만 양면이 있다. 원격·클라우드 제어가 쉬워진다는 것은 1-3 의 RMS 사례처럼 **네트워크 공격면이 넓어진다** 는 뜻이기도 하다. E2E 보안을 제대로 구현했는지가 XFS4IoT 도입의 실질적인 보안 수준을 정한다. 이 부분은 필자 해석이며, XFS4IoT 배치에 대한 중립적인 보안 평가 자료는 찾지 못했다.

---

## 2. 현금이 떨어지지 않게 — 수요 예측과 보충 최적화

### 2-1. 무엇을 최적화하나

ATM 현금 관리는 두 비용 사이의 줄타기다.

- **많이 넣고 드물게 보충** → 수송비는 줄지만, 묶인 현금의 이자(기회비용)와 보험료가 는다.
- **적게 넣고 자주 보충** → 이자·보험은 줄지만, 수송비가 늘고 **현금 품절(고객 불만)** 위험이 커진다.

옥스퍼드 수학연구소 스터디그룹(ESGI 99)이 세르비아 Credit Agricole 은행의 ATM 망을 분석한 보고서도 비용을 **현금 동결 비용, 수송비, 보험료** 세 가지로 나눴다. 보고서는 여러 대를 한 경로(route)로 묶어 같은 시간에 보충하므로 보충량뿐 아니라 경로도 함께 고려해야 한다고 짚는다 ([Oxford MIIS, ESGI 99 보고서](https://miis.maths.ox.ac.uk/636/1/ATMs_report.pdf)).

### 2-2. 예측 — 단말 하나보다 묶음이 낫다

인출 수요에는 뚜렷한 주기가 있다. 요일(월·금 많음), 월초, 명절과 휴가철. 연구들이 공통으로 짚는 어려움은 **개별 단말 수요가 너무 출렁인다** 는 점이고, 공통 처방은 **비슷한 단말끼리 묶어서 예측** 하는 것이다.

- **Ekinci, Lu, Duman (2015, *Expert Systems with Applications*)** — 이스탄불 ATM 데이터에서 개별 단말 수요의 변동이 너무 커 기존 방식(지수가중이동평균 → 최적화)이 잘 안 맞았다. 가까운 위치끼리 묶고, 일별이 아닌 보충 주기 단위로 합산해 예측하는 방법을 제안했고, 사례 연구에서 비용이 더 낮았다고 보고한다 ([DOI: 10.1016/j.eswa.2014.12.011](https://dl.acm.org/doi/10.1016/j.eswa.2014.12.011)).
- **Kamini, Ravi, Prinzie, Van den Poel** — 요일별 인출 패턴이 비슷한 ATM 을 군집으로 묶은 뒤 신경망으로 예측했다. 공개 벤치마크인 NN5 대회 데이터셋에서 GRNN 이 SMAPE 18.44% 로 가장 좋았고, 군집 없이 전체를 바로 예측할 때보다 오차가 훨씬 작았다고 보고한다 ([Ghent University Working Paper 13/865](https://ideas.repec.org/p/rug/rugwps/13-865.html)).

### 2-3. 보충 — 점 예측 대신 구간으로

예측이 틀리는 건 전제다. 그래서 최근 연구는 **예측 구간을 그대로 최적화에 넣는다.**

- **Ekinci, Serban, Duman (2021, *Operational Research*)** — 이스탄불 한 은행의 ATM 98대 일별 인출 데이터로, 점 예측 대신 **예측 구간** 을 쓰고 선형계획 기반 **강건 최적화(robust optimization)** 로 보충량을 정했다. 현업의 일반적인 전략보다 비용이 크게 줄었다고 보고한다 ([DOI: 10.1007/s12351-019-00466-4](https://link.springer.com/article/10.1007/s12351-019-00466-4)).
- **Simutis 외 (카우나스 공과대)** — 단말별 신경망 예측에 담금질 기법(simulated annealing) 최적화를 붙였다. **시뮬레이션** 에서 금리가 높고 수송비가 낮은 시나리오는 유지비가 약 18% 줄었지만, 다른 시나리오에서는 2% 에 그쳤다 ([Information Technology and Control](https://itc.ktu.lt/index.php/ITC/article/download/11829/18478)).

마지막 결과가 중요하다. **최적화의 효과는 알고리즘보다 금리와 수송비라는 외부 변수에 크게 좌우된다.** 금리가 높을 때는 "현금을 덜 넣는" 최적화의 가치가 커지고, 금리가 낮으면 작아진다. 관리 시스템에 예측·최적화 모듈을 넣는다면 금리와 수송 단가를 **설정값으로 노출** 해야 하는 이유다.

> 위 논문들의 개선 수치는 **각 저자가 자기 데이터나 시뮬레이션으로 보고한 값** 이다. 서로 다른 데이터·조건이라 수치를 직접 비교할 수 없고, 같은 데이터로 여러 방법을 맞붙인 중립 비교 자료는 찾지 못했다.

### 2-4. 보안과 현금 관리가 만나는 지점

두 주제는 따로 노는 것 같지만, 관리 시스템 안에서는 같은 데이터를 쓴다. **현금 잔량의 시계열** 이다.

- 예측 모델에는 "이 단말은 이 시간대에 이만큼 빠진다" 가 학습돼 있다.
- 재킹팟은 그 예측과 정반대로 **수 분 만에 카세트가 비는** 사건이다.

그래서 예측 모델의 잔차(예측 대비 실제 인출의 이탈)를 그대로 보안 신호로 쓸 수 있다. FBI 가 말한 "IOC 조합 시 자동 정지" 의 한 축으로, **승인 거래 로그와 맞지 않는 잔량 감소** 를 넣는 것이다. 이 연결은 필자의 설계 제안이며, 이를 실제로 구현해 효과를 측정한 공개 자료는 확인하지 못했다.

---

## 3. 정리 — 관리 시스템 설계 체크리스트

| 영역 | 질문 |
| --- | --- |
| 원격 관리 | 한도·설정 변경 API 가 거래 승인과 같은 등급의 인증(상호 TLS, 메시지 인증, 2단계 인증)으로 보호되는가? |
| 무결성 | 단말마다 골드 이미지 해시 기준선이 있고, 정기 대조하는가? |
| 물리 이벤트 | 함체 개방, USB 장치 연결, 디스펜서 연결 끊김이 정비 일정과 대조되는가? |
| 자동 대응 | 징후가 겹치면 사람이 보기 전에 단말이 스스로 서비스를 중지하는가? |
| 디스펜서 | PC 와 디스펜서 사이 통신이 암호화되고 서로 인증되는가? |
| 위협 모델 | 지역별 위협 통계(미국: 논리 공격 증가 / 유럽: 물리 공격 중심)를 설정으로 반영하는가? |
| 현금 예측 | 단말 군집 단위로 예측하고, 점 예측이 아닌 구간으로 보충량을 정하는가? |
| 외부 변수 | 금리와 수송 단가를 설정값으로 바꿀 수 있는가? |
| 교차 활용 | 예측 잔차를 보안 경보에 쓰는가? |

---

## 근거의 한계

- **필자는 실제 ATM 망을 운영해 본 적이 없다.** 이 글은 공개된 경보, 표준, 논문을 관리 시스템 설계 관점에서 엮은 것이다.
- **보안 수치는 미국 자료다.** FBI 의 1,900건 / 700건 / 2,000만 달러는 미국 내 보고 기준이다. 국내 재킹팟 통계는 공개 자료로 찾지 못했다.
- **국내 ATM 대수** 는 국회의원실이 금감원에서 받은 자료를 언론이 보도한 2차 인용이다. 원자료(금감원 제출 자료)는 직접 확인하지 못했다.
- 1-6 의 XFS4IoT 보안 효과 해석과 2-4 의 예측 잔차 → 보안 신호 연결은 **필자 해석·제안** 이다.
- 현금 예측 논문의 개선 수치는 저자 보고값이며, 중립적인 헤드투헤드 비교는 없다.
- 공격 기법은 공개 경보가 설명하는 수준까지만 다뤘다.

---

## References

1. FBI, *FLASH: Increase in Malware Enabled ATM Jackpotting Incidents Across United States*, 2026-02-19. <https://www.ic3.gov/CSA/2026/260219.pdf> — 1차·공식
2. U.S. Secret Service GIOC, *Alert #24-006-I: New Jackpotting Attack Vector* (TLP:GREEN), 2024. <https://www.oba.com/wp-content/uploads/2024/06/24-006-I-New-Jackpotting-Attack-Vector-TLP-Green-Alert.pdf> — 1차 (협회 재게시본)
3. U.S. Secret Service GIOC, *Alert #24-005-I: Uptick in ATM Jackpotting Attacks*, 2024-03. <https://www.oba.com/wp-content/uploads/2024/06/24-005-I-Uptick-in-Jackpotting-Alert-TLP-Green.pdf> — 1차 (협회 재게시본)
4. Diebold Nixdorf, *Active Security Alert: Jackpotting with Black Box in Europe*, 2020-07-15. <https://s3.documentcloud.org/documents/6989897/Diebold-Nixdorf-warning-of-new-ATM-attacks.pdf> — 벤더 1차
5. Indiana Department of Financial Institutions, *Advisory Letter 2025-04: ATM/ITM Jackpotting Occurrences*, 2025-10-14. <https://www.in.gov/dfi/files/DFI-Advisory-Letter-2025-04-ATM-or-ITM-Jackpotting-Occurrences.pdf> — 1차·공식
6. PCI Security Standards Council, *ATM Security Guidelines Information Supplement*, 2013-01. <https://listings.pcisecuritystandards.org/pdfs/PCI_ATM_Security_Guidelines_Info_Supplement.pdf> — 1차·공식
7. CEN-CENELEC, *CWA 17852 — XFS4IoT*. <https://www.cencenelec.eu/areas-of-work/xfs_cwa17852_release2021-1/> — 1차·표준
8. CEN, *XFS4IoT Specification — 2024-03 Release* (CWA 17852, 2025-04-23 재발행). <https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA17852/cwa17852_2024-03-release_2025.pdf> — 1차·표준
9. XFS4IoT Specification (preview). <https://xfs4iot.github.io/Specifications-Preview.github.io/html/index.html>
10. Ekinci, Y., Lu, J.-C., Duman, E. *Optimization of ATM cash replenishment with group-demand forecasts*. Expert Systems with Applications 42(7), 2015. <https://doi.org/10.1016/j.eswa.2014.12.011>
11. Ekinci, Y., Serban, N., Duman, E. *Optimal ATM replenishment policies under demand uncertainty*. Operational Research 21, 999–1029, 2021. <https://doi.org/10.1007/s12351-019-00466-4>
12. Kamini, V., Ravi, V., Prinzie, A., Van den Poel, D. *Cash Demand Forecasting in ATMs by Clustering and Neural Networks*. Ghent University Working Paper 13/865. <https://ideas.repec.org/p/rug/rugwps/13-865.html>
13. Simutis, R., Dilijonas, D., Bastina, L., Friman, J., Drobinov, P. *Optimization of Cash Management for ATM Network*. Information Technology and Control. <https://itc.ktu.lt/index.php/ITC/article/download/11829/18478>
14. Oxford Mathematical Institute (ESGI 99), *Optimization of ATMs filling-in*. <https://miis.maths.ox.ac.uk/636/1/ATMs_report.pdf>
15. 한국은행, *현금접근성에 대해 알고 계시나요?* (화폐이야기). <https://www.bok.or.kr/portal/bbs/P0000547/view.do?depth=200387&menuNo=200387&nttId=10083214&oldMenuNo=201150&programType=newsData&relate=Y> — 1차·공식
16. 연합뉴스, *은행 ATM 5년새 9천대 줄어*, 2024-09-16 (금감원 제출 자료, 유영하 의원실). <https://www.yna.co.kr/view/AKR20240914040800002>
17. 매일경제, *디지털화에 빠르게 사라지는 은행 ATM*, 2025-09-22 (금감원 제출 자료, 추경호 의원실). <https://www.mk.co.kr/news/economy/11425581>
