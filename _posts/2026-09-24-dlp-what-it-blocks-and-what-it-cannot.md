---
layout: post
title: "DLP(자료 반출 통제) — 무엇을 막고, 무엇은 끝내 못 막는가"
date: 2026-09-24 20:25:10 +0900
categories: [Security]
tags: [DLP, 정보유출방지, 내부자위협, MITRE ATT&CK, NIST 800-53, Purview, CASB]
---

보안 담당자가 "USB 막고, 메일 첨부 검사하고, 웹 업로드 통제하면 유출은 끝" 이라고 말하면 반은 맞고 반은 틀리다. DLP(Data Loss Prevention)는 **실수로 새는 것**은 꽤 잘 막는다. 하지만 **작정한 내부자**를 막는 도구는 아니다.

이 글은 DLP 가 어떤 채널을 어떤 방식으로 통제하는지 정리하고, 구조적으로 막을 수 없는 지점을 공식 문서 기준으로 짚는다.

## 반출 경로부터 — 공격자 관점의 지도

방어를 보기 전에 "무엇이 반출 경로인가" 를 정리해 두면 DLP 의 빈칸이 잘 보인다. [MITRE ATT&CK](https://attack.mitre.org/tactics/TA0010/)은 반출(Exfiltration, TA0010)을 *"techniques that adversaries may use to steal data from your network"* 로 정의하고, 이렇게 나눈다.

| 경로 | ATT&CK 기법 | 예 |
|---|---|---|
| 물리 매체 | [T1052 Exfiltration Over Physical Medium](https://attack.mitre.org/techniques/T1052/) (.001 USB) | USB, 외장 디스크, 휴대폰 |
| 정상 웹 서비스 | [T1567 Exfiltration Over Web Service](https://attack.mitre.org/techniques/T1567/) | 코드 저장소(.001), 클라우드 스토리지(.002), 텍스트 공유 사이트(.003), 웹훅(.004) |
| 다른 프로토콜 | [T1048 Exfiltration Over Alternative Protocol](https://attack.mitre.org/techniques/T1048/) | FTP, SMTP, DNS, SMB 등 |

반출 전 준비 단계도 중요하다. [T1560 Archive Collected Data](https://attack.mitre.org/techniques/T1560/)는 공격자가 *"compress and/or encrypt data that is collected prior to exfiltration"*, 즉 반출 전에 압축하거나 암호화한다고 적는다. 이 한 줄이 뒤에서 DLP 의 가장 큰 한계로 돌아온다.

통제 요구사항 쪽에서는 [NIST SP 800-53 Rev.5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)의 세 통제가 DLP 와 직접 맞닿는다.

- **AC-4 Information Flow Enforcement:** 정보 흐름 통제
- **MP-7 Media Use:** 매체 사용 통제
- **SC-7(10) Boundary Protection | Prevent Exfiltration:** 경계에서의 반출 방지

## DLP 는 세 곳에 선다

| 구성 | 위치 | 주로 보는 것 |
|---|---|---|
| **엔드포인트 DLP** | PC 에 설치한 에이전트 | USB 복사, 프린트, 클립보드, 로컬 앱의 업로드 |
| **네트워크 DLP** | 메일 게이트웨이, 웹 프록시 | SMTP 첨부·본문, HTTP(S) 업로드. HTTPS 는 TLS 복호화가 전제 |
| **클라우드 DLP (CASB/SSE)** | SaaS API 연동 | 드라이브·메신저의 외부 공유, 공개 링크 |

예를 들어 Microsoft Purview 의 [엔드포인트 DLP 문서](https://learn.microsoft.com/en-us/purview/endpoint-dlp-learn-about)는 통제할 수 있는 활동으로 다음을 든다.

- 제한된 클라우드 도메인 업로드, 브라우저 붙여넣기, 클립보드 복사
- USB 이동식 장치 복사, 네트워크 공유 복사, 인쇄
- 허용되지 않은 블루투스 앱과 RDP 를 통한 복사
- 제한된 앱의 접근

같은 제품의 [DLP 개요](https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp)는 정책 적용 위치를 Exchange 메일, SharePoint·OneDrive, Teams 채팅, 기기(Windows·macOS), 온프레미스 저장소 등으로 나열한다. **한 제품이 세 층을 모두 덮으려 한다**는 뜻이다.

구글 워크스페이스도 [Drive DLP](https://knowledge.workspace.google.com/admin/security/about-dlp-for-drive)로 *"prevent data leaks and control the sharing of sensitive data in Drive files"*, 즉 드라이브 파일의 민감정보 공유를 규칙으로 통제한다.

## 채널별로 할 수 있는 것

**USB·저장매체**
- 전면 차단, 읽기 전용, 등록된 장치만 허용
- 복사할 때 자동 암호화, 복사 이력과 원본 보관

**이메일**
- 첨부와 본문 내용 검사
- 차단, 결재 후 발송, 자동 암호화
- 외부 도메인 발송만 골라서 통제

**웹 업로드**
- 웹메일, 게시판, 파일공유 사이트 업로드 통제
- 최근에는 **생성형 AI 서비스에 붙여넣기·업로드**를 통제하는 수요가 크다

**클라우드**
- 개인 계정 드라이브 업로드 차단(회사 테넌트만 허용)
- "링크가 있는 누구나" 공유를 탐지하고 회수

**공통**
- 인쇄·화면 워터마크. 막는 도구가 아니라 **누가 흘렸는지 추적**하는 도구다

## 무엇을 근거로 판단하나

Microsoft 의 [데이터 분류 개요](https://learn.microsoft.com/en-us/purview/data-classification-overview)를 기준으로 하면 탐지 방식은 크게 이렇다.

- **민감정보 유형(패턴):** 주민번호, 카드번호, 계좌번호 같은 정형 패턴. 체크섬 검증을 곁들인다.
- **정확한 데이터 일치(EDM):** 실제 고객 DB 의 값과 정확히 일치하는 문자열을 찾는다.
- **학습형 분류기:** 샘플을 학습시켜 계약서, 이력서, 소스코드 같은 **문서 유형**을 추정한다.
- 여기에 문서 핑거프린팅(원본 일부만 옮겨도 탐지), 분류 라벨, 사용자·기기·목적지 같은 **맥락** 조건을 조합한다.

## 한계 — 구조적으로 못 막는 것들

### 1. 에이전트가 없는 곳은 보이지 않는다

Purview 문서는 이렇게 명시한다. *"You need to onboard all the devices you want to use as locations in your DLP policies."* 정책 위치로 쓰려면 기기를 등록해야 한다는 것이다.

개인 PC, 개인 폰, 등록되지 않은 BYOD 는 엔드포인트 DLP 밖이다. 같은 문서에는 이런 문장도 있다. *"If data is never saved to a file on the local device, Endpoint DLP cannot scan or classify it."* 파일로 저장되지 않고 화면에만 떠 있는 데이터는 엔드포인트가 검사하지 못한다.

### 2. 암호화하면 내용 검사는 끝난다

T1560 이 말한 "반출 전 압축·암호화" 가 정확히 여기를 찌른다.

- 구글 Drive DLP 문서는 검사하지 않는 대상에 *"Contents of password-protected files"* 를 올려 두었다.
- Microsoft 도 [DLP 정책 레퍼런스](https://learn.microsoft.com/en-us/purview/dlp-policy-reference)에서 암호로 보호된 파일을 "스캔할 수 없는 문서" 조건으로 따로 다룬다.

대응은 보통 **"검사할 수 없는 파일은 반출 차단"** 이다. 하지만 그 순간 협력사에 암호 걸린 압축파일을 보내던 정상 업무도 같이 막힌다. 보안과 업무 마찰 사이의 줄다리기가 시작된다.

이미지 속 텍스트, 인코딩(base64), 파일 분할도 같은 계열의 우회다.

### 3. 허용된 채널은 반출 채널이기도 하다

T1567 의 하위 기법들을 다시 보자. 코드 저장소, 클라우드 스토리지, 웹훅이다. 모두 **업무에 쓰는 정상 서비스**다.

- 회사가 GitHub 를 허용하면 개인 저장소로의 push 와 업무 push 를 네트워크 수준에서 구분하기 어렵다.
- 회사 테넌트 드라이브에 올린 뒤 외부 공유하는 경로는 클라우드 DLP 가 따로 봐야 한다.

소스코드는 특히 어렵다. 주민번호처럼 정형 패턴이 없어서 분류기와 핑거프린트에 기대야 하고, 오탐도 많다.

### 4. 네트워크 DLP 의 사각지대

- HTTPS 내용을 보려면 TLS 복호화가 필요하다. 그런데 인증서 고정(pinning) 앱이나 금융·의료 사이트처럼 복호화 예외로 두는 구간이 반드시 생긴다.
- T1048 이 든 DNS 같은 대체 프로토콜, 그리고 **개인 폰 테더링**으로 회사망 자체를 우회하면 게이트웨이는 아예 보지 못한다.

### 5. 아날로그 반출

모니터를 폰 카메라로 찍는 것, 손으로 옮겨 적는 것은 기술적으로 막을 수 없다. 워터마크는 사후 추적을 가능하게 할 뿐이다.

### 6. 권한 있는 내부자와 저속 반출

- 관리자 권한이 있으면 에이전트를 끄거나 예외를 등록할 수 있다.
- 퇴사 예정자가 몇 주에 걸쳐 조금씩 가져가는 방식은 건별 정책의 임계값에 걸리지 않는다.

CMU SEI 의 [Common Sense Guide to Mitigating Insider Threats, 7th Ed.](https://www.sei.cmu.edu/library/common-sense-guide-to-mitigating-insider-threats-seventh-edition/)(2022)가 기술 통제만이 아니라 인사, 법무, 물리 보안, 모니터링을 아우르는 권고로 구성된 이유가 이것이다.

### 7. 오탐·미탐과 운영 부담

- 패턴 탐지는 오탐이 많다. 알림 피로가 쌓이면 정책은 결국 느슨해진다.
- 오탐을 줄이려고 조건을 좁히면 미탐이 늘어난다. 튜닝은 끝나는 작업이 아니라 **상시 운영 비용**이다.
- 엔드포인트 에이전트는 성능 저하와 호환성 문제를 만든다.
- TLS 복호화와 내용 검사는 임직원 개인정보와 통신 비밀 문제를 건드린다. 도입 전에 고지·동의 절차와 법무 검토가 필요하다.

그리고 가장 흔한 실패 원인은 기술이 아니다. **데이터 분류가 안 된 조직은 무엇을 막을지부터 정하지 못한다.**

## 그래서 DLP 는 어디에 두어야 하나

| 층 | 역할 | DLP 의 몫 |
|---|---|---|
| 데이터 분류·최소 권한 | 애초에 못 보게 한다 | 분류 라벨을 정책 조건으로 활용 |
| **DLP** | 실수를 막고, 모든 반출 시도를 기록한다 | 핵심 |
| 로그·행위 분석(UEBA) | 저속 반출, 평소와 다른 행동을 잡는다 | DLP 로그가 주요 입력 |
| 인사·교육·서약·감사 | 억제하고 책임을 묻는다 | 추적 증거 제공 |

DLP 의 진짜 가치는 "완벽 차단" 이 아니라 두 가지다.

1. **실수에 의한 유출을 대부분 막는다.** 잘못된 수신자, 공개 링크, 개인 드라이브 업로드 같은 것들이다.
2. **모든 반출 시도에 흔적을 남긴다.** 작정한 내부자도 흔적은 남기므로 사후 대응과 억제가 가능해진다.

"DLP 를 샀으니 유출은 막혔다" 는 말은 틀렸다. 맞는 말은 이쪽이다. **"DLP 덕분에 실수는 줄었고, 무엇이 어디로 나갔는지는 알 수 있다."**

## References

- MITRE ATT&CK — [TA0010 Exfiltration](https://attack.mitre.org/tactics/TA0010/) · [T1052](https://attack.mitre.org/techniques/T1052/) · [T1567](https://attack.mitre.org/techniques/T1567/) · [T1048](https://attack.mitre.org/techniques/T1048/) · [T1560](https://attack.mitre.org/techniques/T1560/)
- NIST — [SP 800-53 Rev.5, Security and Privacy Controls for Information Systems and Organizations](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) (AC-4, MP-7, SC-7(10))
- Microsoft Learn — [Learn about Endpoint DLP](https://learn.microsoft.com/en-us/purview/endpoint-dlp-learn-about) · [Learn about DLP](https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp) · [Data classification overview](https://learn.microsoft.com/en-us/purview/data-classification-overview) · [DLP policy reference](https://learn.microsoft.com/en-us/purview/dlp-policy-reference)
- Google Workspace — [DLP for Drive](https://knowledge.workspace.google.com/admin/security/about-dlp-for-drive)
- CMU SEI — [Common Sense Guide to Mitigating Insider Threats, Seventh Edition](https://www.sei.cmu.edu/library/common-sense-guide-to-mitigating-insider-threats-seventh-edition/) (2022)
