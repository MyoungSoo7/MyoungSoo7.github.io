---
layout: post
title: "[CS300 #258] 침해 사고 대응 — 터진 뒤 몇 시간이 피해 규모를 정한다"
date: 2026-10-10 22:18:00 +0900
categories: [cs]
tags: [cs300, security, incident-response, forensics, nist]
---

컴퓨터공학 300 주제 시리즈의 258번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

침해 사고 대응은 **준비 → 탐지·분석 → 봉쇄·제거·복구 → 사후 활동** 의 순환이며, 사고 당일의 판단보다 사고 전에 정해 둔 역할·연락망·로그·백업·절차가 결과를 더 많이 좌우한다.

## 왜 필요한가

모든 침입을 막을 수는 없다. 그렇다면 다음 질문은 "얼마나 빨리 알아채고, 얼마나 작게 끝내느냐" 다. 사고 현장에서 흔히 보는 실수는 대개 준비 부족에서 나온다.

- 감염된 서버를 바로 재설치해 공격 경로를 알 수 있는 증거가 사라진다.
- 누가 결정권자인지 몰라 서버를 내릴지 말지 몇 시간을 논쟁한다.
- 공격자가 이미 쓰고 있는 메일·메신저로 대응을 논의해 계획이 새어 나간다.
- 로그 보존 기간이 짧아 최초 침입 시점까지 거슬러 올라갈 수 없다.
- 백업도 함께 암호화되어 복구할 게 없다.

절차가 몸에 익어 있으면 이런 실수가 줄어든다. 그래서 사고 대응은 기술이면서 동시에 조직 운영이다.

## 핵심 개념

### 생애 주기

NIST SP 800-61 Rev.2(2012)는 사고 대응을 네 단계로 설명했다. 오랫동안 업계 표준 모델로 쓰였다.

```
 ┌─────────┐   ┌──────────────┐   ┌──────────────────────┐   ┌────────────┐
 │ 1. 준비  │ → │ 2. 탐지·분석  │ → │ 3. 봉쇄·제거·복구     │ → │ 4. 사후 활동 │
 └─────────┘   └──────────────┘   └──────────────────────┘   └────────────┘
      ↑                 ↑______________________|                    │
      └─────────────────────────────────────────────────────────────┘
```

2025년 4월 발표된 Rev.3 은 이를 대체하며, 사고 대응을 NIST 사이버보안 프레임워크(CSF) 2.0 의 여섯 기능(Govern, Identify, Protect, Detect, Respond, Recover)에 맞춰 위험 관리 전반에 녹여 넣는 방향으로 다시 썼다. 사고 대응이 보안팀만의 별도 절차가 아니라 평소 운영의 일부라는 관점이다. 아래는 이해하기 쉬운 네 단계로 설명한다.

### 1. 준비

- **사고 대응 계획**: 사고의 정의와 심각도 등급, 역할(지휘자, 기술 분석, 커뮤니케이션, 법무), 결정 권한, 외부 연락처(법무·규제기관·보험·외부 대응 업체).
- **대체 소통 채널**: 회사 계정이 장악됐을 때 쓸 채널.
- **가시성**: 로그 수집·보존(다음 글의 SIEM), 자산 목록, 네트워크 구성도.
- **복구 능력**: 오프라인·불변(immutable) 백업과 **복구 훈련**. 복구해 본 적 없는 백업은 백업이 아니다.
- **플레이북**: 랜섬웨어, 계정 탈취, 키 유출, 웹 셸 같은 유형별 절차.

### 2. 탐지와 분석

- 단서는 경보, 사용자 신고, 외부 통보(고객, 보안 연구자, 수사기관)에서 온다.
- 진짜 사고인지 판별하고, 범위(어떤 시스템·계정·데이터)를 정하고, **타임라인**을 만든다.
- 모든 행동과 시각을 기록한다. 나중의 보고서와 법적 절차의 근거가 된다.

### 3. 봉쇄·제거·복구

| 단계 | 목표 | 예 |
|---|---|---|
| 봉쇄 | 확산 중지 | 네트워크 격리, 계정 잠금, 유출 키 폐기, 악성 도메인 차단 |
| 제거 | 원인 제거 | 악성 파일·계정·지속성 장치 삭제, 취약점 패치 |
| 복구 | 정상화 | 깨끗한 이미지로 재구축, 백업 복원, 감시 강화 상태로 서비스 재개 |

봉쇄에는 균형이 필요하다. 너무 일찍 요란하게 막으면 공격자가 눈치채고 흔적을 지우거나 다른 경로로 숨는다. 너무 늦으면 피해가 커진다. 이 판단을 미리 정한 결정권자가 한다.

### 증거 보존

RFC 3227 은 **휘발성 순서**대로 수집하라고 권한다. 레지스터·캐시 → 라우팅 테이블·ARP·프로세스 목록·메모리 → 임시 파일시스템 → 디스크 → 원격 로그 → 물리 구성 → 보관 매체. 전원을 끄거나 재설치하면 앞쪽 증거가 먼저 사라진다. 수집한 증거는 해시를 기록하고 누가 언제 다뤘는지(관리 연속성, chain of custody)를 남긴다. NIST SP 800-86 이 포렌식 절차를 더 자세히 다룬다.

### 4. 사후 활동

비난 없는(blameless) 회고로 "무엇이 일어났나, 무엇이 잘 됐나, 무엇을 바꿀까" 를 정리하고, 탐지 규칙·플레이북·설정을 고친다. 이 결과가 다시 1단계 준비로 들어간다. 이 고리가 돌지 않으면 같은 사고가 반복된다.

## 직접 해 보기

사고 분석의 첫 작업은 흩어진 로그를 **하나의 시간축**에 놓는 것이다. 형식과 시간대가 제각각인 로그 네 줄을 UTC 로 정규화해 타임라인을 만들고, 원본의 해시를 증거로 기록한다. 주소는 문서용 대역이다.

```python
import hashlib, json, re
from datetime import datetime, timezone, timedelta

# 형식과 시간대가 제각각인 로그 (주소는 문서용 대역)
nginx = '203.0.113.50 - - [10/Oct/2026:23:58:41 +0900] "POST /api/upload HTTP/1.1" 200 512'
app   = '{"ts":"2026-10-10T14:58:43Z","level":"WARN","msg":"file saved","path":"/uploads/x.php"}'
auth  = '2026-10-11 00:03:10 KST sshd: Accepted publickey for deploy from 203.0.113.50'
k8s   = '{"stageTimestamp":"2026-10-10T15:05:02.120Z","verb":"create","objectRef":{"resource":"pods","namespace":"web"},"user":{"username":"system:serviceaccount:web:default"}}'

KST = timezone(timedelta(hours=9))
events = []
m = re.search(r'\[(.+?)\] "(\S+) (\S+)', nginx)
events.append((datetime.strptime(m[1], "%d/%b/%Y:%H:%M:%S %z"), "nginx", f"{m[2]} {m[3]}"))
a = json.loads(app)
events.append((datetime.fromisoformat(a["ts"].replace("Z", "+00:00")), "app", f'{a["msg"]} {a["path"]}'))
t = datetime.strptime(auth[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
events.append((t, "sshd", auth[24:]))
k = json.loads(k8s)
events.append((datetime.fromisoformat(k["stageTimestamp"].replace("Z", "+00:00")), "k8s-audit",
               f'{k["user"]["username"]} {k["verb"]} {k["objectRef"]["resource"]}'))

print("== 타임라인 (UTC 로 정규화) ==")
for ts, src, msg in sorted(events):
    print(ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), f"{src:<9}", msg)

# 증거 보존: 수집한 원본의 해시를 기록해 두면 나중에 변조 여부를 증명할 수 있다
evidence = "\n".join([nginx, app, auth, k8s]).encode()
print("evidence sha256:", hashlib.sha256(evidence).hexdigest())
```

실행 결과(Python 3.12):

```
== 타임라인 (UTC 로 정규화) ==
2026-10-10T14:58:41Z nginx     POST /api/upload
2026-10-10T14:58:43Z app       file saved /uploads/x.php
2026-10-10T15:03:10Z sshd      sshd: Accepted publickey for deploy from 203.0.113.50
2026-10-10T15:05:02Z k8s-audit system:serviceaccount:web:default create pods
evidence sha256: ae0d77afd76d7216eede88c9ae6aac12c6b1e307f66492ae6b53fa16c0a0fc4b
```

원본만 보면 nginx 는 23시대(KST), sshd 는 다음 날 0시대(KST), 나머지는 UTC 라 서로 관련이 없어 보인다. 정규화하면 6분 남짓 사이의 한 줄기 이야기가 된다. 업로드 → PHP 파일 저장(웹 셸 의심) → 같은 주소에서 배포 계정으로 SSH 로그인 → 기본 서비스 어카운트로 파드 생성. 그렇다면 "배포 계정의 SSH 키는 어떻게 얻었나", "기본 서비스 어카운트에 왜 파드 생성 권한이 있나" 가 다음 질문이 된다. 타임라인은 답보다 **질문**을 먼저 준다.

## 현업에서는

- **시간 동기화가 전제**: 서버 시계가 몇 분씩 어긋나면 타임라인이 거짓말을 한다. 모든 노드에 NTP 동기화를 걸고, 로그는 시간대를 포함한 형식(ISO 8601)이나 UTC 로 남긴다.
- **쿠버네티스에서의 증거**: 파드는 지우면 끝이다. 침해 의심 파드는 삭제하지 말고 레이블을 바꿔 서비스에서 빼고(봉쇄), NetworkPolicy 로 격리한 뒤 파일시스템과 로그를 확보한다. 노드 수준 증거가 필요하면 노드를 cordon 하고 그대로 둔다. API 서버 감사 로그가 켜져 있지 않으면 "누가 무엇을 만들었나" 를 나중에 알 길이 없다.
- **키 유출 대응**: 깃 저장소에 키가 올라간 경우 커밋을 지우는 것이 아니라 **키를 즉시 폐기·교체**하는 것이 봉쇄다. 그다음 그 키로 무엇이 접근됐는지 로그로 확인한다.
- **훈련**: 테이블탑 연습(시나리오를 말로 따라가는 회의)을 분기마다 한 시간만 해도 연락망 누락, 권한 부족, 백업 복구 절차의 빈 곳이 드러난다.

## 확인 문제

1. 사고 대응 생애 주기 네 단계를 쓰고 각 단계의 핵심 산출물을 하나씩 들라.
2. 감염 서버를 즉시 재설치하면 어떤 문제가 생기는가?
3. RFC 3227 의 휘발성 순서에서 디스크보다 메모리를 먼저 수집하는 이유는?
4. 봉쇄를 너무 이르게 할 때와 너무 늦게 할 때의 위험은?
5. 타임라인 작성 전에 반드시 맞춰야 할 것은?

### 풀이

1. 준비(대응 계획·플레이북·로그·백업), 탐지·분석(범위와 타임라인), 봉쇄·제거·복구(격리 조치, 원인 제거, 정상화), 사후 활동(회고와 개선 항목).
2. 메모리·디스크의 증거가 사라져 침입 경로와 범위를 알 수 없고, 같은 취약점으로 재침입당할 수 있다.
3. 메모리는 전원이 꺼지거나 시간이 지나면 사라지는 반면 디스크는 상대적으로 오래 남는다. 실행 중인 악성 프로세스·네트워크 연결은 메모리에만 있는 경우가 많다.
4. 이르면 공격자가 눈치채 흔적을 지우거나 다른 거점으로 옮기고, 늦으면 확산·유출로 피해가 커진다.
5. 시간대와 시계 동기화. 모든 이벤트를 같은 기준(UTC 등)으로 정규화해야 한다.

## 더 읽을거리 (References)

- NIST, [SP 800-61 Rev. 3: Incident Response Recommendations and Considerations for Cybersecurity Risk Management](https://csrc.nist.gov/pubs/sp/800/61/r3/final)
- NIST, [SP 800-61 Rev. 2: Computer Security Incident Handling Guide](https://csrc.nist.gov/pubs/sp/800/61/r2/final)
- IETF, [RFC 3227: Guidelines for Evidence Collection and Archiving](https://www.rfc-editor.org/rfc/rfc3227)
- NIST, [SP 800-86: Guide to Integrating Forensic Techniques into Incident Response](https://csrc.nist.gov/pubs/sp/800/86/final)
