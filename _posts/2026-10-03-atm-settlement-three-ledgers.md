---
layout: post
title: "ATM 정산은 세 장부의 대사다 — 승인·방출·실사 현금이 어긋나는 지점을 설계로 다루기"
date: 2026-10-03 21:56:16 +0900
categories: [아키텍처, 금융]
tags: [ATM, 정산, 대사, ISO8583, XFS4IoT, 지급결제, 차액결제, RegE, 시스템설계]
---

## 0. 카드 결제와 무엇이 다른가

가맹점 카드 결제에서 승인이 났다는 건 대체로 거래가 일어났다는 뜻이다. ATM은 그렇지 않다. 호스트가 승인을 내준 뒤에도 기계 안에서 지폐가 카세트에서 빠져나오고, 출금구로 나가고, 고객이 집어 가야 거래가 끝난다. 이 중 어느 단계에서든 멈출 수 있다.

그래서 ATM 정산은 금액을 더하는 문제가 아니다. **서로 다른 세 기록이 같은 이야기를 하는지 맞춰 보는 문제**다.

1. **호스트 거래 로그**: 승인과 취소 전문이 남는다.
2. **단말 기록**: 전자저널(EJ)과 장치 카운터. 기계가 실제로 무엇을 했는지 남는다.
3. **실사 현금**: 현송 때 카세트를 열어 세어 본 지폐 수.

표준도 이 부분은 비워 둔다. ATM과 카드 호스트 사이의 전문 표준인 ISO 8583:2023은 적용 범위에서 "메시지가 전송되는 방식이나 정산이 이뤄지는 방식은 이 문서의 범위가 아니다"라고 적는다([ISO 8583:2023 Abstract](https://www.iso.org/standard/79451.html)). 전문의 모양은 표준이 정해 주지만, 정산은 각 기관이 설계해야 한다.

이 글은 그 정산·대사 계층만 다룬다. ATM 관리 시스템의 전체 계층 구조는 [ATM 종합관리시스템의 여섯 계층]({% post_url 2026-09-09-atm-management-system-six-layers %})에, 글로벌 운영의 함정은 [글로벌 ATM 종합관리시스템 설계 노트]({% post_url 2026-09-09-global-atm-management-beyond-local-testing %})에 정리했다.

---

## 1. 승인과 방출 사이: 거래는 상태 기계다

ATM 장치 제어 표준인 XFS4IoT(CEN CWA 17852)는 출금을 명령 하나로 처리하지 않는다. `CashDispenser.Dispense`(카세트에서 꺼내 쌓기), `CashDispenser.Present`(출금구로 내보내기), `CashManagement.Retract`(못 가져간 지폐를 회수)가 각각 따로 있고, `ItemsPresentedEvent`, `ItemsTakenEvent`, `IncompleteDispenseEvent` 같은 이벤트가 진행 상황을 알린다([CWA 17852 XFS4IoT Specification](https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA17852/cwa17852_2024-03-release_2025.pdf) 목차의 8~9장).

정산 쪽에서 보면 출금 한 건은 대략 아래와 같은 상태 기계가 된다. 상태 이름은 설명을 위해 붙인 것이고, 표준이 정한 이름이 아니다.

```text
AUTHORIZED ──dispense ok──▶ DISPENSED ──present──▶ PRESENTED ──taken──▶ COMPLETED
     │                          │                       │
     │ timeout/거절             │ incomplete dispense   │ 고객 미수취 → retract
     ▼                          ▼                       ▼
  REVERSED                 PARTIAL / SUSPECT        RETRACTED (금액 "?")
```

계좌 차감을 확정해도 되는 상태는 `COMPLETED` 하나뿐이다. 나머지 상태는 모두 다른 장부와 대조해 봐야 결론이 난다.

### 회수된 돈은 금액을 믿을 수 없다

가장 까다로운 상태는 `RETRACTED`다. 단말과 호스트 사이의 위변조 방지 토큰을 정의한 XFS E2E 명세는 출금 결과 토큰(Present Status)에 `PRESENTED`(지폐가 기계 밖으로 접근 가능했는지)와 `RETRACTEDAMOUNT` 필드를 둔다. 그리고 다음과 같이 정한다([XFS E2E Programmer's Reference v1.1.1](https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA%20E2E/cen-ws-xfs_cwa-e2e-programmersreference1-1-1workingdocument.pdf)).

- 지폐가 고객 손에 닿을 수 있었던 순간부터 그 금액은 믿을 수 없다. 고객이 일부만 가져갔거나, 위폐로 바꿔 넣었을 수 있기 때문이다. 그래서 회수 금액은 `"?"`로 보고된다.
- 실제 금액이 들어가는 경우는 입금 겸용 장치처럼 회수된 지폐를 하드웨어가 다시 감별할 수 있을 때뿐이다.
- `DISPENSEID`가 승인 때 받은 토큰과 맞지 않으면, 수신 측은 그 거래를 **suspect**로 간주하고 현금이 고객에게 노출됐을 수 있다고 봐도 된다.

정산 설계에서 중요한 건 이 `"?"`다. 회수 거래는 **자동으로 원복하면 안 된다.** 금액이 미확정인 suspect로 분류해 두고, 현송 때 회수함을 실사한 결과로 결론을 낸다. 이 거래를 자동으로 원복하는 시스템은 고객이 지폐 일부를 빼고 나머지를 회수시키는 수법에 그대로 노출된다.

---

## 2. 타임아웃과 취소: 응답이 없을 때 누가 무엇을 하나

통신이 끊기는 지점에 따라 두 장애가 생긴다.

| 끊긴 지점 | 호스트 상태 | 단말 상태 | 결과 |
| --- | --- | --- | --- |
| 승인 요청이 호스트에 못 감 | 거래 없음 | 응답 없음 → 미출금 | 무해 |
| 승인 응답이 단말에 못 옴 | **차감 완료** | 응답 없음 → 미출금 | 고객 손해 |
| 출금 후 완료 통지 유실 | 차감 완료 | 출금 완료 | 무해(후속 대사로 확인) |

두 번째 줄이 핵심이다. 단말은 응답을 못 받으면 돈을 내주지 않고, **원거래를 지목하는 취소(reversal) 전문**을 보낸다. 이 취소 전문은 받았다는 확인이 올 때까지 단말 저장소에 쌓아 두고 재전송한다(store-and-forward). ISO 8583 계열에서는 이 흐름을 요청/응답 메시지와 별도의 취소·통지(advice) 메시지 클래스로 나눈다. 다만 표준 본문은 유료이고, 필드와 값의 정의는 유지관리기관(MA)이 관리한다([ISO 8583:2023](https://www.iso.org/standard/79451.html)). 그래서 이 글은 특정 MTI 값이나 필드 번호를 원문과 대조해 인용하지 않는다.

호스트 쪽 요구사항은 결제 시스템의 멱등성과 같지만, 순서가 뒤집혀 올 수 있다는 점이 더 어렵다.

```java
// 취소 처리: 원거래 키 = (단말ID, 거래일련번호, 영업일)
@Transactional
public ReversalResult reverse(ReversalAdvice adv) {
    var key = OriginalKey.of(adv.terminalId(), adv.stan(), adv.businessDate());

    // 1) 같은 취소의 재전송 → 처음 결과를 그대로 돌려준다
    var prior = reversals.findByKey(key);
    if (prior.isPresent()) return prior.get().result();

    var original = txns.findForUpdate(key);

    // 2) 원거래보다 취소가 먼저 도착한 경우: 지우지 말고 '선취소'로 남긴다
    if (original.isEmpty()) {
        reversals.save(Reversal.orphan(key, adv));   // 나중에 원거래가 오면 즉시 상쇄
        return ReversalResult.ACK;                   // 단말의 재전송 루프는 끝내 준다
    }

    // 3) 정상: 원거래를 지우지 않고 반대 분개를 추가한다
    ledger.append(Entry.reversalOf(original.get(), adv.reversedAmount()));
    reversals.save(Reversal.applied(key, adv));
    return ReversalResult.ACK;
}
```

세 가지를 지켜야 한다.

- **재전송된 취소는 같은 응답으로 끝낸다.** 두 번 원복하면 고객 계좌에 돈이 생긴다.
- **원거래 없이 도착한 취소를 버리지 않는다.** 네트워크 경로가 다르면 순서가 뒤집힌다. 버리면 뒤늦게 도착한 원거래가 그대로 차감된다.
- **부분 출금은 일부 취소로 처리한다.** 10만 원을 승인했는데 6만 원만 나왔다면 4만 원만 반대 분개한다. 원거래 금액과 실제 지급 금액을 별도 필드로 둔다.

원장은 지우지 않고 반대 분개만 추가한다는 원칙은 [정산과 보안은 같은 통제면이다]({% post_url 2026-10-03-settlement-and-security-one-control-surface %})의 1절과 같다. ATM에서는 이 원칙이 선택이 아니다. 취소가 원거래보다 먼저 올 수 있으니, 원거래를 지우는 모델로는 처리 자체가 성립하지 않는다.

---

## 3. 세 장부 대사: 카세트 단위로 맞춘다

대사의 단위는 계좌가 아니라 **단말 × 카세트 × 장전 주기**다. 현송원이 카세트를 넣을 때부터 다음에 꺼낼 때까지가 한 주기다.

```text
기대 잔량(카세트 k) = 장전 매수
                    − Σ 호스트 확정 출금 매수 (COMPLETED + 확정된 PARTIAL)
                    − 리젝트함 이동 매수
차이(k)            = 실사 매수 − 기대 잔량
```

세 장부를 서로 비교하면 차이가 어디서 왔는지가 갈린다.

| 호스트 로그 | 단말 EJ·카운터 | 실사 현금 | 해석 |
| --- | --- | --- | --- |
| 차감 | 출금 완료 | 맞음 | 정상 |
| 차감 | 출금 기록 없음 | 남음(over) | 승인 응답 유실 → **고객 환급 대상** |
| 취소 | 출금 완료 | 모자람(short) | 취소가 잘못 나감 → 고객 재청구·분쟁 |
| 차감 | 회수(`?`) | 회수함 실사로 판정 | suspect → 실사 결과로 확정 |
| 기록 없음 | 기록 없음 | 모자람 | 현송·물리 보안 사고 → 정산 밖으로 이관 |

설계에서 지킬 점은 다음과 같다.

- **EJ는 단말이 쓰는 증거라 위변조 방지가 필요하다.** E2E 토큰처럼 HMAC이 붙은 출금 결과를 호스트가 함께 보관하면, 대사 때 단말이 사후에 쓴 기록과 거래 시점의 기록을 구별할 수 있다([XFS E2E](https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA%20E2E/cen-ws-xfs_cwa-e2e-programmersreference1-1-1workingdocument.pdf)).
- **차이를 0으로 맞추는 조정 분개는 사유 코드 없이는 허용하지 않는다.** "기타 조정"이 쌓이는 계정이 내부 횡령이 숨는 자리다.
- **over와 short를 서로 상계하지 않는다.** 단말 A의 남는 돈과 단말 B의 모자란 돈은 서로 다른 고객의 서로 다른 사건이다. 합계가 0이어도 건별로는 둘 다 미결이다.
- **실사는 사람이 하므로 실사 기록도 이중 서명이나 사진 같은 증거를 함께 남긴다.** 이건 기술보다 운영 통제의 영역이지만, 스키마에 그 필드가 없으면 운영도 남길 방법이 없다.

---

## 4. 영업일과 컷오버

ATM은 24시간 돌지만 회계는 영업일 단위로 닫힌다. 거래 시각(단말 시계 기준)과 회계 영업일은 다른 필드여야 하고, 둘 사이의 대응은 호스트가 정한다.

- **컷오버 경계 거래**: 23:59:58에 승인되고 00:00:03에 출금 완료된 거래는 어느 영업일에 속하는가? 기준을 승인 시각으로 할지 완료 시각으로 할지 하나로 정하고, 취소도 **원거래의 영업일**을 따라가게 한다. 그렇지 않으면 원거래는 어제 장부에, 취소는 오늘 장부에 실려 양쪽 일계가 모두 틀어진다.
- **단말 시계는 믿지 않는다.** 대사 키에 단말 시계를 넣으면 시계가 틀어진 단말의 거래가 엉뚱한 날에 실린다. 영업일은 호스트가 응답 전문에 실어 내려보내는 값을 쓴다.
- **장전 주기와 영업일은 서로 정렬되지 않는다.** 카세트 대사는 장전 주기로, 계좌 정산은 영업일로 닫는다. 두 축을 억지로 맞추면 현송이 없는 날의 대사가 미결로 쌓인다.

이 절의 내용은 특정 표준을 인용한 게 아니라 설계 관행을 정리한 것이다.

---

## 5. 은행 간 정산: 고객 계좌 밖의 두 번째 장부

A은행 카드로 B은행 ATM에서 돈을 뽑으면, B은행은 현금을 내주고 A은행은 고객 계좌를 차감한다. 은행 사이에는 채권·채무가 남는다. 국내에서는 이 거래가 금융결제원이 운영하는 금융공동망 중 하나인 **CD공동망**을 탄다. 한국은행은 CD공동망의 주요 서비스를 "소액 인출·입금·송금"으로 분류한다([한국은행, 우리나라의 지급결제제도](https://www.bok.or.kr/portal/main/contents.do?menuNo=200347)).

정산은 건별로 하지 않는다. 역할 분담은 다음과 같다(같은 출처).

- **금융결제원**: 참가기관 간 지급지시의 확인·중계와 **차액정산**
- **한국은행**: 차액결제 승인, 결제 대상 거래 결정, 차액결제리스크 관리제도 운영

소액결제시스템의 고객 간 자금이체는 건수가 많고 건당 금액이 적다. 그래서 금융기관 간 주고받을 금액을 상계한 뒤 **차액만 한은금융망(BOK-Wire+)에서 최종 결제**한다. 참가기관은 순이체한도를 설정하고, 그 한도의 일정 비율만큼 증권을 한국은행에 담보로 낸다([한국은행 지급결제보고서 2022](https://www.bok.or.kr/portal/cmmn/file/fileDown.do?atchFileId=1d7232abb2ea89e4ee7d8e5a8806b592&fileSn=4)). 한국은행은 2016년부터 단계적으로 올려 온 이 담보제공비율을 최종 목표인 100%로 인상했다([한국은행, 2025년도 지급결제보고서](https://www.bok.or.kr/portal/bbs/P0000600/view.do?depth=200072&menuNo=200072&nttId=10097493&oldMenuNo=201150&programType=newsData&relate=Y)).

국제 기준으로 보면 이 구조는 CPMI-IOSCO의 금융시장인프라 원칙(PFMI)이 말하는 이연차액결제(DNS)형 소액지급시스템이다. PFMI는 원칙 8에서 "늦어도 결제일 종료 시까지 명확하고 확정적인 최종 결제"를, 원칙 9에서 "실무상 가능하면 중앙은행 화폐로 결제"를 요구한다([PFMI, BIS](https://www.bis.org/publications/principles-financial-market-infrastructures.pdf)). 담보 100%는 DNS의 고유 위험, 곧 결제 시점에 한 참가기관이 차액을 못 내면 이미 상계한 결과 전체가 흔들리는 위험을 막는 장치로 읽을 수 있다. 이것은 이 글의 해석이고, 한국은행 문서에 그렇게 적혀 있다는 뜻은 아니다.

이 구조가 기관 내부 설계에 주는 요구는 세 가지다.

1. **기관 내 장부는 두 개다.** 고객 원장(계좌별)과 대외 정산 원장(상대 기관별 채권·채무). 고객 거래 하나가 두 장부에 동시에 기록돼야 하고, 하루를 닫을 때 대외 원장의 기관별 순액이 금융결제원이 통보한 차액과 일치해야 한다.
2. **공동망 정산 파일과의 대사는 세 장부 대사와 별개의 작업이다.** 카세트가 맞아도 대외 차액이 틀릴 수 있다. 예를 들어 취소가 우리 쪽에선 반영됐는데 공동망에는 원거래만 실린 경우다.
3. **최종 결제가 난 뒤의 오류는 원장 수정이 아니라 다음 결제 주기의 조정 거래로 처리한다.** 확정된 결제를 되돌리지 않는다는 원칙 8의 취지와도 맞는다.

---

## 6. 분쟁: 대사가 끝나지 않은 채 고객이 먼저 묻는다

"돈이 안 나왔는데 차감됐다"는 민원은 대사가 끝나기 전에 들어온다. 그래서 분쟁 처리 기한이 대사 주기를 거꾸로 제약한다.

미국 Regulation E가 이 제약을 숫자로 명시한 좋은 사례다([12 CFR 1005.11, eCFR](https://www.ecfr.gov/current/title-12/chapter-X/part-1005/subpart-A/section-1005.11)).

- 금융기관은 오류 통지를 받은 날부터 **10영업일 안에** 오류 여부를 판단해야 한다.
- 10영업일 안에 끝내지 못하면 최대 **45일**까지 조사할 수 있다. 단, 10영업일 안에 주장 금액을 **가지급(provisional credit)** 해야 한다.
- 오류로 판정되면 **1영업일 안에** 바로잡아야 한다.
- POS 직불 거래는 기한이 90일로 늘어나지만, CFPB 공식 해석은 이 연장이 **ATM 거래에는 적용되지 않는다**고 명시한다. 가맹점 안에 있는 ATM이어도 마찬가지다([CFPB, §1005.11 Official Interpretation](https://www.consumerfinance.gov/rules-policy/regulations/1005/11)).

설계 쪽 함의는 이렇다. **현송 주기가 10영업일보다 길면, 실사로 확정하기 전에 가지급부터 해야 하는 단말이 생긴다.** 그래서 분쟁 시스템은 대사 시스템의 결과를 기다리는 구조가 아니라, 다음처럼 동작해야 한다.

- 민원이 접수되면 해당 거래의 세 장부 상태를 즉시 조회한다. EJ와 E2E 토큰만으로 결론이 나는 경우(예: `PRESENTED=NO`)는 바로 처리한다.
- 결론이 나지 않으면 가지급을 하고, 그 가지급을 해당 카세트 주기의 미결 항목으로 연결한다.
- 실사 결과가 나오면 가지급을 확정하거나 회수한다. 회수할 때도 Reg E는 통지와 5영업일 유예를 요구한다(§1005.11(d)(2)).

국내 전자금융거래법상 처리 기한과 절차는 이 글에서 원문을 대조하지 않았다. 위 숫자는 미국 규정의 예시로만 읽어야 한다.

---

## 7. 정리

| 어긋나는 지점 | 원인 | 설계 대응 |
| --- | --- | --- |
| 승인 ≠ 출금 | 장치 단계별 실패 | 출금 상태 기계, `COMPLETED`만 확정 |
| 회수 금액 `"?"` | 고객 접근 후 금액 불확실 | 자동 원복 금지, suspect로 실사 판정 |
| 응답 유실 | 통신 단절 | 단말 측 취소 store-and-forward, 호스트 멱등 처리 |
| 취소가 원거래보다 먼저 도착 | 경로별 순서 뒤집힘 | 선취소 보관 후 원거래 도착 시 상쇄 |
| 카세트 over/short | 위 항목 전부 + 물리 사고 | 세 장부 대사, 건별 미결, 상계 금지 |
| 영업일 경계 | 24시간 운영 vs 일 단위 회계 | 호스트가 영업일 부여, 취소는 원거래 영업일 |
| 은행 간 차액 | 공동망 차액결제 | 대외 정산 원장, 금결원 차액과 일일 대사 |
| 분쟁 기한 | 대사보다 민원이 빠름 | 가지급 → 실사로 확정·회수 |

## 근거의 한계

- **ISO 8583 본문은 대조하지 않았다.** 유료 표준이고 메시지·필드 정의는 유지관리기관이 관리한다. 이 글은 취소·통지 클래스가 따로 있다는 구조만 언급했고, MTI 값이나 필드 번호는 쓰지 않았다.
- **CD공동망의 전문 형식, 정산 파일 양식, 차액결제 시각은 금융결제원의 참가기관용 자료**라 공개 출처로 확인하지 못했다. 5절은 한국은행 공개 문서의 역할 분담과 차액결제 구조까지만 다룬다.
- 1~4절의 상태 이름, 코드, 대사 표는 **설명용 설계 예시**다. 특정 기관의 실제 시스템을 확인한 결과가 아니다. 내 settlement 프로젝트에는 ATM 관련 코드가 없다.
- 실제 기관의 suspect 거래 비율이나 현송 차이 금액 같은 중립적인 운영 통계는 찾지 못했다. 그래서 수치를 쓰지 않았다.

## References

1. ISO, *ISO 8583:2023 Financial-transaction-card-originated messages — Interchange message specifications*, Abstract. <https://www.iso.org/standard/79451.html>
2. CEN, *CWA 17852 Extensions for Financial Services (XFS) — XFS4IoT Specification* (2024-03 release). <https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA17852/cwa17852_2024-03-release_2025.pdf>
3. CEN/ISSS XFS Workshop, *End-to-End (E2E) for XFS/XFS4IoT Programmer's Reference v1.1.1*. <https://www.cencenelec.eu/media/CEN-CENELEC/AreasOfWork/CEN%20sectors/Digital%20Society/CWA%20Download%20Area/XFS/CWA%20E2E/cen-ws-xfs_cwa-e2e-programmersreference1-1-1workingdocument.pdf>
4. 한국은행, 「우리나라의 지급결제제도」. <https://www.bok.or.kr/portal/main/contents.do?menuNo=200347>
5. 한국은행, 「지급결제보고서」(2022년도). <https://www.bok.or.kr/portal/cmmn/file/fileDown.do?atchFileId=1d7232abb2ea89e4ee7d8e5a8806b592&fileSn=4>
6. 한국은행, 「2025년도 지급결제보고서」. <https://www.bok.or.kr/portal/bbs/P0000600/view.do?depth=200072&menuNo=200072&nttId=10097493&oldMenuNo=201150&programType=newsData&relate=Y>
7. 금융결제원, 「전자금융업무 — CD공동망」. <https://community.kftc.or.kr/kftc/business/BusinessFncJoin.do>
8. CPSS-IOSCO, *Principles for Financial Market Infrastructures* (2012), Principles 8·9. <https://www.bis.org/publications/principles-financial-market-infrastructures.pdf>
9. eCFR, *12 CFR 1005.11 Procedures for resolving errors*. <https://www.ecfr.gov/current/title-12/chapter-X/part-1005/subpart-A/section-1005.11>
10. CFPB, *§ 1005.11 Procedures for resolving errors — Official Interpretation*. <https://www.consumerfinance.gov/rules-policy/regulations/1005/11>
