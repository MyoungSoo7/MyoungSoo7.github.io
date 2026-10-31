---
title: "정보보안기사 학습 문제 13 — TLS 1.3·XSS·사고 대응"
date: 2026-11-01 02:53:00 +0900
categories: [정보보안기사, 네트워크·애플리케이션]
tags: [TLS, XSS, 사고대응]
---

이번 글의 세 문항은 공개 기출문제의 원문을 재현하지 않은 **창작 문제**다. 정답과 해설은 게시 시점에 확인한 IETF RFC와 OWASP·NIST 공개 문서를 근거로 작성했다.

## 문제 1 — TLS 1.3 핸드셰이크

### 문제
TLS 1.3 핸드셰이크의 핵심 기능을 가장 정확하게 설명한 것은?

### 선택지
1. 서버의 파일시스템 권한을 자동으로 설정한다.
2. 키 교환·암호 매개변수 협상·인증을 수행하고 공유 키 자료를 확립한다.
3. 모든 애플리케이션 데이터를 평문으로 전송한 뒤 마지막에 해시한다.
4. 데이터베이스 계정의 비밀번호를 중앙에서 변경한다.

### 정답
**2번**

### 해설
IETF RFC 8446은 TLS 핸드셰이크를 통신 상대를 인증하고 암호 모드·매개변수를 협상하며 공유 키 자료를 확립하는 프로토콜로 설명한다. 핸드셰이크가 끝나면 설정된 키로 애플리케이션 트래픽을 보호한다.

### 오답 포인트
TLS는 운영체제 권한이나 데이터베이스 계정을 관리하는 프로토콜이 아니다. 또한 TLS의 목적은 전송 중 도청·변조·위조를 막는 보안 채널 제공이지, 데이터를 먼저 평문으로 전송하는 것이 아니다.

### 출처 또는 검증 근거
IETF RFC 8446, *The Transport Layer Security (TLS) Protocol Version 1.3*, Abstract·§4: [https://datatracker.ietf.org/doc/html/rfc8446](https://datatracker.ietf.org/doc/html/rfc8446)

## 문제 2 — XSS 출력 인코딩

### 문제
사용자가 입력한 문자열을 HTML 본문에 텍스트로 표시할 때 XSS 위험을 줄이는 기본 통제는?

### 선택지
1. 입력을 Base64로 바꾸고 그대로 HTML에 삽입한다.
2. 브라우저가 코드가 아닌 데이터로 해석하도록 HTML 문맥에 맞는 출력 인코딩을 적용한다.
3. 모든 입력을 URL 인코딩한 뒤 JavaScript 코드로 실행한다.
4. 오류 메시지에 원본 입력을 그대로 출력한다.

### 정답
**2번**

### 해설
OWASP는 신뢰할 수 없는 입력을 사용자에게 데이터로 표시하고 코드로 실행되지 않게 하려면 출력 문맥에 맞는 인코딩을 사용하라고 설명한다. HTML 본문에는 HTML 엔터티 인코딩을 적용하며, HTML·JavaScript·URL·CSS 문맥은 서로 다른 인코딩 규칙을 사용한다.

### 오답 포인트
Base64는 일반적인 XSS 방어 통제가 아니며 디코딩 후에는 다시 위험한 값이 될 수 있다. URL 인코딩을 모든 문맥에 적용할 수도 없고, 사용자 입력을 JavaScript로 실행하면 오히려 코드 주입 위험이 커진다.

### 출처 또는 검증 근거
OWASP, *Cross Site Scripting Prevention Cheat Sheet*: [https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

## 문제 3 — 사고 대응과 개선

### 문제
NIST가 설명하는 사고 대응에서 사고를 처리한 뒤 재발 방지와 대응 역량 향상을 위해 수행할 활동은?

### 선택지
1. 증거와 기록을 즉시 삭제해 저장공간을 확보한다.
2. 후속 보고서와 교훈 도출을 통해 개선사항을 식별하고 반영한다.
3. 복구가 끝나면 모든 모니터링을 영구 중단한다.
4. 같은 사고가 재발할 때까지 대응 절차를 변경하지 않는다.

### 정답
**2번**

### 해설
NIST의 최신 사고 대응 설명은 Detect·Respond·Recover 활동과 함께 지속적 개선을 강조한다. 사고 후 보고와 교훈 도출은 원인·영향·대응의 문제를 확인하고 통제와 절차를 개선하는 근거가 된다.

### 오답 포인트
증거 삭제는 조사와 책임성 확보를 훼손한다. 복구 완료는 모니터링 종료의 근거가 아니며, 사고 후 학습을 미루면 같은 취약점과 절차 오류가 반복될 수 있다.

### 출처 또는 검증 근거
NIST, *Incident Response* (SP 800-61 Rev. 3 안내): [https://csrc.nist.gov/Projects/incident-response](https://csrc.nist.gov/Projects/incident-response)
