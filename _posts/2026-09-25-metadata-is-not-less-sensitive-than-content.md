---
layout: post
title: "메타데이터의 착각 — '내용은 안 봤다' 는 말은 왜 아무것도 보장하지 않는가?"
date: 2026-09-25 02:37:35 +0900
categories: [Security, Privacy]
tags: [Metadata, Privacy, EXIF, IMDS, SSRF, Cloud Security, Re-identification]
---

"통화 내용은 수집하지 않았습니다. 메타데이터만 봤습니다." 이 문장은 오랫동안 안심시키는 말로 쓰였다. 이 글의 주장은 반대다. **메타데이터는 데이터 "에 관한" 데이터라서 덜 민감한 게 아니라, 구조화되어 있고 자동으로 붙기 때문에 오히려 더 쉽게 새고 더 쉽게 분석된다.**

메타데이터가 사고로 이어지는 경로를 네 가지로 나눠 보자.

| 경로 | 예 | 누가 모르고 넘기나 |
|---|---|---|
| 1. 파일에 붙는 메타데이터 | 사진 EXIF 위치, 문서 작성자·수정 이력 | 파일을 보내는 사람 |
| 2. 행위의 메타데이터 | 통화 기록, 위치 기록 | "내용은 없다" 고 믿는 정책 |
| 3. 인프라의 메타데이터 | 클라우드 인스턴스 메타데이터 서비스 | 서버 코드를 쓰는 개발자 |
| 4. 운영의 메타데이터 | 로그, 헤더, 파일명 | 모두 |

## 1. 파일에 붙는 메타데이터 — 보낸 사람도 모르는 정보

### 사진의 EXIF

디지털 카메라와 스마트폰 사진의 메타데이터 형식인 Exif 는 CIPA 표준으로 정의된다. 표준에는 GPS 정보를 담는 전용 영역(GPS Info IFD)이 있고, 여기에 `GPSLatitude`, `GPSLongitude`, `GPSAltitude`, `GPSTimeStamp` 같은 태그가 정의돼 있다.[^exif]

즉 위치 기록이 켜진 폰으로 찍은 사진 한 장은 **"어디서, 언제"** 를 기계가 읽을 수 있는 형태로 담고 있을 수 있다. 집에서 찍은 중고거래 사진, 사무실에서 찍은 화이트보드 사진이 그대로 올라가면 사진보다 메타데이터가 더 많은 것을 말한다. 업로드하는 서비스에 따라 이 정보가 제거되기도 하지만, **메일 첨부, 메신저의 "원본 전송", 자체 구축한 업로드 서버**는 그렇지 않을 수 있다.

개발자 입장의 교훈은 명확하다. **사용자 이미지를 받는 서비스라면 서버에서 EXIF 를 제거한 뒤 저장·재배포**해야 한다. 클라이언트가 지웠으리라는 가정은 통하지 않는다.

### 문서의 속성과 이력

Microsoft 는 Office 문서에 숨은 정보를 점검하는 "문서 검사" 기능을 두고, 그 대상을 이렇게 나열한다.[^msdoc] 주석, 변경 추적 이력, 문서 버전 정보, 작성자·제목 같은 문서 속성, **마지막으로 저장한 사람의 이름**, 이메일 헤더, 서버 속성, 템플릿 이름 등이다.

"최종본.docx" 를 외부에 보내는 순간, 그 파일에는 누가 작성했고 누가 고쳤고 어떤 문구가 삭제됐는지가 함께 갈 수 있다. 외부로 나가는 문서는 **PDF 변환만으로 충분하다고 가정하지 말고** 문서 검사로 정리하는 절차를 두는 게 안전하다.

## 2. 행위의 메타데이터 — "내용 없음" 은 "정보 없음" 이 아니다

### 통화 메타데이터

스탠퍼드의 Mayer, Mutchler, Mitchell 은 실제 참가자들의 전화 메타데이터(누가, 누구에게, 언제, 얼마나)를 분석해 PNAS 에 발표했다. 결론은 이렇다.[^pnas]

> *"We find that telephone metadata is densely interconnected, can trivially be reidentified, enables automated location and relationship inferences, and can be used to determine highly sensitive traits."*

통화 내용 없이도 **관계, 위치, 민감한 특성**이 추론된다. 연구의 출발점 자체가 "내용과 메타데이터를 구분하는 정책" 이 실제로 프라이버시를 지키는지 검증하는 것이었다.

### 위치 메타데이터

MIT 의 de Montjoye 등은 150만 명의 이동 기록을 분석했다. 기지국 수준 해상도와 시간 단위 기록에서는 **네 개의 시공간 점만으로 95% 의 사람을 유일하게 식별**할 수 있었다.[^unique]

> *"four spatio-temporal points are enough to uniquely identify 95% of the individuals."*

같은 논문은 해상도를 낮춰도 유일성이 해상도의 대략 1/10 제곱으로만 줄어든다고 보고한다. 이름을 지우고 해상도를 조금 낮추는 것만으로는 **익명화가 되지 않는다**는 뜻이다. 서비스 로그에 위치·시간을 남기면서 "개인정보는 없다" 고 말하기 어려운 이유다.

## 3. 인프라의 메타데이터 — 클라우드 서버의 가장 위험한 URL

클라우드 VM 안에서는 `169.254.169.254` 라는 링크 로컬 주소로 **인스턴스 메타데이터 서비스(IMDS)** 에 접근할 수 있다. 인스턴스 ID, 네트워크 정보, 그리고 결정적으로 **그 인스턴스에 부여된 역할의 임시 자격 증명**이 여기서 나온다.

Azure 문서는 이 서비스의 성격을 분명히 적는다.[^azure]

> *"IMDS is not a channel for sensitive data. The API is unauthenticated and open to all processes on the VM."*

문제는 **SSRF(Server-Side Request Forgery)** 다. 사용자가 준 URL 을 서버가 대신 가져오는 기능(미리보기, 웹훅, 이미지 가져오기)에 취약점이 있으면, 공격자는 서버에게 `169.254.169.254` 를 요청하게 만들어 **서버의 클라우드 자격 증명을 빼낼 수 있다.** OWASP 는 SSRF 를 Top 10 의 독립 항목으로 올렸다.[^owasp-ssrf]

### 클라우드 3사의 방어는 같은 발상이다

| 클라우드 | IMDS 요청 조건 |
|---|---|
| AWS (IMDSv2) | 먼저 **PUT** 으로 세션 토큰 발급 → 토큰을 헤더에 넣어 조회. `X-Forwarded-For` 가 붙은 PUT 은 거부. 응답 hop limit 기본 1[^aws-how] |
| Google Cloud | `Metadata-Flavor: Google` 헤더 필수. `X-Forwarded-For` 가 있으면 거부[^gcp] |
| Azure | `Metadata: true` 헤더 필수. `X-Forwarded-For` 가 있으면 거부[^azure] |

세 곳 모두 **"평범한 GET 한 번으로는 안 열린다"** 는 원칙을 공유한다. 단순한 SSRF 는 보통 공격자가 메서드나 헤더를 마음대로 정할 수 없고, 프록시를 거친 요청에는 `X-Forwarded-For` 가 붙는 경우가 많다는 점을 이용한 것이다. AWS 는 보안 블로그에서 PUT 을 고른 이유를 오픈 WAF·리버스 프록시가 PUT 을 거의 중계하지 않기 때문이라고 설명한다.[^aws-blog]

### 실무 함의

- **AWS 에서는 IMDSv1 을 끄고 IMDSv2 만 허용**한다. AWS 문서에 따르면 기본값은 v1·v2 둘 다 허용이고, 인스턴스별로 v2 만 받도록 설정할 수 있다.[^aws-how]
- **컨테이너 환경에서 hop limit 을 함부로 올리지 않는다.** AWS 문서는 컨테이너 서비스와의 호환을 위해 hop limit 을 늘려야 할 수 있다고 적는다.[^aws-how] 늘리는 순간 **노드의 역할 자격 증명이 파드에서도 보일 수 있다.** 파드에는 노드 역할이 아니라 워크로드 단위 자격 증명을 주는 방식이 원칙이다.
- **URL 을 가져오는 기능에는 목적지 허용 목록**을 두고, 링크 로컬·사설 대역을 명시적으로 막는다. OWASP SSRF 방어 치트시트가 구체적 방법을 정리해 두었다.[^owasp-cs]

## 4. 운영의 메타데이터 — 로그가 가장 큰 메타데이터 저장소다

애플리케이션 로그에는 IP, User-Agent, 요청 경로, 타임스탬프, 사용자 ID 가 쌓인다. 하나하나는 무해해 보여도, 2장의 연구들이 보여주듯 **시간과 위치가 결합되면 사람을 특정**한다. "개인정보는 DB 에만 있다" 는 가정은 로그 수집 파이프라인이 생기는 순간 깨진다.

- 로그에 무엇을 남기는지 **필드 단위로 목록화**한다.
- IP·정밀 위치는 **보존 기간을 짧게** 하고, 분석용으로는 절삭하거나 가명화한다.
- 로그 저장소 접근 권한을 운영 DB 만큼 엄격하게 관리한다.

## 5. 체크리스트

1. 사용자 업로드 이미지는 **서버에서 EXIF 제거** 후 저장한다.
2. 외부 반출 문서는 **문서 검사**로 작성자·이력·주석을 정리한다.
3. "메타데이터만 수집" 하는 기능도 **개인정보 영향 평가 대상**에 넣는다.
4. 클라우드는 **IMDSv2 강제**, 컨테이너 hop limit 은 최소로 유지한다.
5. URL 을 가져오는 서버 기능에는 **목적지 허용 목록**과 링크 로컬 차단을 넣는다.
6. 로그 필드를 목록화하고 **위치·IP 보존 기간**을 정한다.

## 맺으며 — "그냥 메타데이터" 의 비용

메타데이터가 위험한 이유는 역설적으로 그것이 **편리하기 때문**이다. 자동으로 붙고, 구조화되어 있고, 기계가 바로 읽는다. 내용을 이해하려면 사람이 읽어야 하지만, 메타데이터는 조인하고 집계하면 끝난다.

그래서 "내용은 안 봤다" 는 말은 보안이나 프라이버시의 보증이 아니다. 클라우드의 메타데이터 서비스가 **자격 증명을 내주는 URL** 이듯, 사진의 메타데이터는 **집 주소를 내주는 태그**일 수 있다. 메타데이터를 "부가 정보" 가 아니라 **1급 데이터로 분류하는 것**, 그게 이 글의 결론이다.

---

## References

[^exif]: CIPA, *Exchangeable image file format for digital still cameras: Exif Version 2.32* (CIPA DC-X008-Translation-2019). <https://www.cipa.jp/std/documents/e/DC-X008-Translation-2019-E.pdf>
[^msdoc]: Microsoft Support, *Remove hidden data and personal information by inspecting documents, presentations, or workbooks*. <https://support.microsoft.com/en-us/office/remove-hidden-data-and-personal-information-by-inspecting-documents-presentations-or-workbooks-356b7b5d-77af-44fe-a07f-9aa4d085966f>
[^pnas]: Jonathan Mayer, Patrick Mutchler, John C. Mitchell, *Evaluating the privacy properties of telephone metadata*, PNAS 113(20), 2016. <https://doi.org/10.1073/pnas.1508081113>
[^unique]: Yves-Alexandre de Montjoye et al., *Unique in the Crowd: The privacy bounds of human mobility*, Scientific Reports 3, 1376 (2013). <https://www.nature.com/articles/srep01376>
[^azure]: Microsoft Learn, *Azure Instance Metadata Service*. <https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service>
[^owasp-ssrf]: OWASP, *A10:2021 – Server-Side Request Forgery (SSRF)*. <https://owasp.org/Top10/A10_2021-Server-Side_Request_Forgery_%28SSRF%29/>
[^aws-how]: AWS, *Use the Instance Metadata Service to access instance metadata* (Amazon EC2 User Guide). <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-metadata-v2-how-it-works.html>
[^gcp]: Google Cloud, *Access VM metadata* (Compute Engine documentation). <https://cloud.google.com/compute/docs/metadata/querying-metadata>
[^aws-blog]: AWS Security Blog, *Add defense in depth against open firewalls, reverse proxies, and SSRF vulnerabilities with enhancements to the EC2 Instance Metadata Service*. <https://aws.amazon.com/blogs/security/defense-in-depth-open-firewalls-reverse-proxies-ssrf-vulnerabilities-ec2-instance-metadata-service/>
[^owasp-cs]: OWASP Cheat Sheet Series, *Server-Side Request Forgery Prevention Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>
