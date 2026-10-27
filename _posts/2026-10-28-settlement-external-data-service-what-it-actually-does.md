---
layout: post
title: "external-data-service 는 실제로 무엇을 하나 — 외부 기관 8곳을 긁어 하루 한 번 내 DB 로 옮기는 창구"
date: 2026-10-28 02:22:05 +0900
categories: [architecture, settlement]
tags: [msa, spring-boot, hexagonal, batch, open-api, settlement]
---

정산 프로젝트에는 자바 MSA 가 다섯 개 있습니다. 그중 `external-data-service` 는 이름만 봐서는 하는 일을 짐작하기 어렵습니다. "외부 데이터"는 범위가 너무 넓기 때문입니다. 이 글은 코드와 ADR, 그리고 오늘 새벽 운영 클러스터에서 잰 수치로 이 서비스가 **실제로** 무엇을 하는지 정리합니다. 서비스가 어떻게 여기까지 모였는지는 [정산 18→6 통합 글]({% post_url 2026-10-27-settlement-18-to-6-the-consumers-nobody-listed %})에서 다뤘습니다.

한 줄로 줄이면 이렇습니다. **정부·공공기관 API 를 정해진 시각에 긁어 `lemuel_external` DB 에 쌓고, 그걸 인증 없는 GET API 로 다시 내보내는 읽기 전용 창구**입니다. 주문·결제·정산 같은 돈의 흐름에는 직접 손대지 않습니다. 다만 대출 심사와 투자 점수가 쓰는 금리·재무 숫자가 여기서 나옵니다.

## 1. 무엇을 긁어 오나 — 외부 출처 8곳, 수집 스케줄 7개

코드에 하드코딩된 상류 주소를 모으면 출처는 여덟 곳입니다(정산 레포는 비공개라 경로만 적습니다). 시각은 모두 KST 입니다.

| 슬라이스 | 출처 | 무엇을 | 언제 |
|---|---|---|---|
| `market` | 금융위원회 주식시세정보 (data.go.kr `1160100`) | 상장 종목 일별 시세 | 매일 07:30 |
| `economics` | 한국은행 ECOS | 기준금리 등 경제지표 11종 | 매일 08:00 |
| `financial` | 금융감독원 OpenDART | 기업 개황 · 재무제표 | 매월 1일 05:00 · 매주 일 04:00 |
| `commondata` | 한국천문연구원 특일정보 (data.go.kr `B090041`) | 공휴일 | 매일 02:00 |
| `commondata` | 국세청 사업자 상태조회 (odcloud) | 휴·폐업 여부 | 요청 시 |
| `commondata` | 공정위 통신판매사업자 (data.go.kr `1130000`) · 국토부 아파트 실거래 (`1613000`) · 서울 열린데이터 | 등록 상태 · 담보 시세 | 매일 08:30 등록 소스 순회 |
| `commondata` | Frankfurter (ECB 기준환율) | 환율 5종 | 매일 08:30 |
| `company` | OpenDART 공시 · 네이버 뉴스 검색 | 공시 피드 · 기업별 기사 | 관리자 트리거 |

- 각 출처가 무엇을 주는지는 기관 문서를 따랐습니다([OpenDART 개발가이드](https://opendart.fss.or.kr/guide/main.do), [ECOS Open API](https://ecos.bok.or.kr/api/), [Frankfurter](https://frankfurter.dev/), [네이버 검색 API](https://developers.naver.com/docs/serviceapi/search/news/news.md)).
- 표의 시각은 `@Scheduled` cron 기본값입니다.
- 코드 규모는 자바 파일 307개입니다. 슬라이스별로는 `company` 94 · `financial` 62 · `commondata` 55 · `economics` 41 · `market` 38 · 공통 설정 16 입니다.
- 모든 슬라이스가 같은 헥사고날 골격(`adapter/in` → `application/port` → `domain` ← `adapter/out`)을 따릅니다.

### 오늘 새벽의 실제 수집 결과

운영 파드 로그(10/27 기준 지난 30시간)에서 확인한 수치입니다.

- **KRX 시세**: 07:30 실행이 최근 7일(`lookback-days=7`)을 다시 훑었습니다. 10/20~10/23 은 거래일마다 2,867~2,870 종목을 upsert 했고 실패는 0건입니다. 하루치가 약 17초 걸립니다.
- **ECOS**: 지표 11개를 스캔해 127행을 upsert 했고, 스킵 1건 · 실패 0건입니다.
- **환율**: 5행 upsert, 실패 0건입니다.
- **공휴일**: 2026·2027·2028년 세 해 모두 **실패**했습니다. 원인은 6절에서 봅니다.

## 2. 누가 쓰나 — 소비자는 둘이다

ADR 0046 은 원래 "소비자가 finance 하나뿐이니 finance 에 합치자"는 질문에서 시작한 문서입니다. 실제로 세어 보니 그 전제가 틀렸습니다.

**① 브라우저 (공개 GET).** 운영 프론트 nginx 가 `/api/{market,economics,financial,common-data,company}` 를 이 서비스 `:8086` 으로 곧장 보냅니다. `SecurityConfig` 는 이 GET 경로를 전부 `permitAll()` 로 열어 둡니다. 수집을 트리거하는 `/admin/**` 만 API 키 필터로 막습니다. 그래서 오늘 새벽 공개 도메인에서 그대로 응답이 옵니다.

```
GET /api/market/stocks/005930/latest            → 200  삼성전자 2026-10-23 종가 215,500
GET /api/economics/indicators/BASE_RATE/latest  → 200  기준금리 3.0000 (관측일 2026-10-24)
GET /api/common-data/holidays?year=2026         → 200  collected=true, 15건
```

프론트 쪽 호출 함수는 33개이고, 이를 쓰는 화면은 8개(기업 조회, CEO 인사이트 등)입니다(ADR 0046 실측).

**② finance-service (서비스 간 호출).** finance 디플로이먼트에는 external-data 를 가리키는 환경변수가 11개 있습니다(`APP_LOAN_*_BASE_URL`, `APP_REPUTATION_EXTERNAL_DATA_BASE_URL` 등). 쓰임새는 세 가지로 나뉩니다.

| 용도 | 방식 | 오늘 실측 |
|---|---|---|
| 대출·투자 스냅샷 갱신 | 하루 1회 배치가 지표·종목 전체를 복사 | 10/27 09:11 지표 11 · 종목 2,661 갱신, missing 0, **74.3초** |
| 평판 재산정 | 배치가 종목 목록을 받아 점수 재계산 | 2,661 중 **500만** 처리 (5절) |
| 담보평가·종가·뉴스 | 요청 또는 배치 경로에서 동기 GET | — |

## 3. 왜 요청 경로에서 부르지 않나 — ADR 0045 의 스냅샷

2026-08-26 이전에는 대출 심사 스레드가 external-data 를 **동기 GET** 했습니다. 상류가 느려지면 심사가 그만큼 멈췄습니다. 더 나쁜 건 상류 장애가 화면에 오류로 드러나지 않고 **판정 결과로 둔갑**했다는 점입니다(ADR 0045).

- 기준금리 조회가 실패하면 설정값 3.5% 로 폴백했습니다. 반환값만 봐서는 진짜 관측치와 구분할 수 없습니다.
- 재무제표 조회가 실패하면 `Optional.empty()` 를 돌려줬습니다. 기업 대출에서 "재무자료 없음"은 사실상 거절입니다.

결정은 "요청 경로는 자기 DB 의 스냅샷만 읽고, 상류 호출은 갱신 배치로 옮긴다"였습니다. 서킷 브레이커도 검토했습니다. 그러나 서킷 브레이커는 기다리는 시간만 줄일 뿐, 폴백값으로 판정한다는 사실은 그대로 남아서 채택하지 않았습니다.

이렇게 외부 데이터를 요청 시점이 아니라 미리 복사해 두는 방식은 Sam Newman 이 *Building Microservices* 2판에서 말한 "데이터 복제(로컬 사본)" 패턴과 같은 계열입니다. 대신 데이터가 그만큼 늦게 반영됩니다([Newman, 2021](https://samnewman.io/books/building_microservices_2nd_edition/)).

여기서 하나가 분명해집니다. external-data 가 죽어도 **대출 심사는 멈추지 않습니다.** 대신 스냅샷이 하루씩 낡아 갑니다. finance 는 이 상태를 `StaleSnapshotExceptionHandler` 로 드러냅니다. 결국 이 서비스의 가용성은 실시간 SLA 가 아니라 **"오늘 배치가 돌았나"**로 판정하는 게 맞습니다.

## 4. 왜 finance 에 합치지 않았나 — ADR 0046

7개를 6개로 줄이자는 압력은 있었습니다(2인 팀). 그래도 분리를 유지한 이유는 두 가지입니다.

1. **보안 자세가 정반대입니다.** external-data 는 인증 없는 공개 읽기 서비스이고, finance 는 JWT 로 보호되는 여신·회계 서비스입니다. 둘을 합치면 같은 프로세스 안에서 `permitAll` 경로와 여신 쓰기 경로가 필터 체인 하나를 같이 써야 합니다.
2. **실패 방식이 다릅니다.** 외부 기관은 키 만료, 레이트리밋, 포맷 변경으로 *자주* 실패합니다. 그 실패가 여신 서비스 안에 있으면 장애 격리가 깨집니다.

반대 방향의 통합(ADR 0038)은 이미 했습니다. 재무·경제·시장·공통데이터 위성 4개를 이 서비스 하나로 합쳤습니다. 근거는 넷 사이에 Outbox·Kafka·계약 스키마가 **하나도 없다**는 실측이었습니다. 지금도 external-data 에는 `KafkaTemplate` 과 `@KafkaListener` 가 0개입니다. 이벤트를 주고받지 않는 순수 HTTP 읽기 서비스입니다.

## 5. 지금 조용히 잘리고 있는 것 — 평판 재산정 상한 500

finance 로그에는 매일 아래 경고가 찍힙니다.

```
평판 재산정 대상이 상한에 걸려 잘림 — total=2661 loaded=500 truncated=2161
(app.company.reputation.max-companies=500)
```

external-data 는 종목 2,661개를 다 내주는데, 받는 쪽이 앞의 500개만 씁니다. 나머지 **81%(2,161개)는 평판 점수가 갱신되지 않습니다.**

$$
\frac{2161}{2661} \approx 0.812
$$

코드 주석을 보면 2026-10-03 전까지는 이게 *경고조차 없이* 잘렸고, 지금은 WARN 으로 드러나기만 합니다. 이 상한이 의도한 비용 제한인지, 종목 수가 늘면서 넘어선 낡은 값인지는 레포에 근거가 없습니다. 이건 external-data 문제가 아니라 소비자 쪽 설정 문제이고, 정할 사람이 정해야 하는 값입니다.

## 6. 내년 1월 1일에 터질 것 — 공휴일 키와 "늑대 소년"

공휴일 수집이 실패하는 이유는 로그에 그대로 나옵니다.

```
HolidaySyncScheduler : 공휴일 수집 실패 year=2026
HttpClientErrorException$Forbidden: 403 ... "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" (등록되지 않은 서비스키)
```

data.go.kr 이 이 서비스키를 특일정보 API 에 **등록되지 않은 키**로 판정한 것입니다. 2026년 공휴일은 예전에 이미 받아 둬서(15건) 지금은 문제가 드러나지 않습니다. 하지만 공개 API 로 보면 2027·2028년은 `collected=false, count=0` 입니다.

이 공휴일 표를 쓰는 곳이 시세 수집기입니다. `MarketSyncScheduler.reportEmptyDay` 는 시세가 0건인 날을 세 가지로 나눕니다.

- 주말이면 정상으로 봅니다.
- 공휴일이면 휴장이라 정상으로 봅니다.
- 둘 다 아니면 **결손**으로 보고 `emptyTradingDay` 카운터를 올립니다.

주석에는 이렇게 만든 이유가 적혀 있습니다. 예전에는 공휴일 0건이 매년 15번 넘게 섞여 경고가 일상이 됐고, 진짜 결손이 그 안에 묻혔습니다("늑대 소년"). 그리고 공휴일을 모르면 평일을 거래일로 보라고 되어 있습니다.

그래서 키를 고치지 않으면 **2027-01-01 아침 07:30 부터 공휴일마다 가짜 결손 경고가 다시 찍힙니다.** 막으려고 만든 늑대 소년이 해가 바뀌면서 돌아오는 셈입니다. 고치는 방법은 data.go.kr 마이페이지에서 특일정보 활용신청을 다시 확인하거나 키를 재발급하는 것입니다. 코드는 바꿀 필요가 없습니다.

참고로 10/27 실행은 10/26(월) 시세를 결손으로 기록했습니다. 금융위 시세 API 가 그 시각에 아직 하루 전 데이터를 내놓지 않았을 가능성이 있습니다. 수집기가 7일을 매번 다시 훑으므로 다음 실행에서 채워질 수 있습니다. 이 글을 쓰는 시점(10/28 02시)에는 확인하지 못했습니다.

## 7. 정리

| 질문 | 답 |
|---|---|
| 한 줄 정의 | 공공·금융 API 8곳을 cron 으로 긁어 `lemuel_external` 에 쌓고, 인증 없는 GET 으로 다시 내보내는 읽기 서비스 |
| 돈을 만지나 | 직접은 아님. 대출 금리·재무 판정의 **입력값**을 공급 |
| 죽으면 | 화면의 시세·지표·기업 조회가 멈춤. 대출 심사는 스냅샷으로 계속 돌지만 숫자가 낡음 |
| 이벤트 | 없음 (Kafka 0) |
| 운영 상태 | 파드 1개, 메모리 요청 512Mi / 한도 1Gi. 시세·지표·환율 수집 실패 0 |
| 당장 볼 것 | ① 공휴일 서비스키 403 (2027-01-01 오탐 예고) ② 평판 재산정 500/2,661 상한 |

같은 정산 레포의 Go 서비스는 [market-stream 해부 글]({% post_url 2026-10-27-settlement-market-stream-anatomy-healthy-but-unreachable %})에서 다뤘습니다. 두 서비스는 대조적입니다. market-stream 은 코드는 멀쩡한데 운영 경로가 없었습니다. external-data 는 경로도 수집도 멀쩡하고, **실패는 바깥쪽 계약(서비스키, 받는 쪽 상한)에서** 나고 있습니다.

## References

- 금융감독원, *OpenDART 개발가이드*. <https://opendart.fss.or.kr/guide/main.do>
- 한국은행, *ECOS Open API 서비스*. <https://ecos.bok.or.kr/api/>
- 공공데이터포털, *한국천문연구원_특일 정보* (`B090041/openapi/service/SpcdeInfoService`). <https://www.data.go.kr/data/15012690/openapi.do>
- 공공데이터포털, *금융위원회_주식시세정보* (`1160100/service/GetStockSecuritiesInfoService`). <https://www.data.go.kr/data/15094808/openapi.do>
- Frankfurter, *Exchange rates API (ECB reference rates)*. <https://frankfurter.dev/>
- NAVER Developers, *검색 API — 뉴스*. <https://developers.naver.com/docs/serviceapi/search/news/news.md>
- Sam Newman, *Building Microservices*, 2nd ed., O'Reilly, 2021. <https://samnewman.io/books/building_microservices_2nd_edition/>
- 정산 프로젝트(비공개 레포): ADR 0038 (C그룹 통합), 0045 (로컬 스냅샷), 0046 (존치 재판정); `external-data-service` `MarketSyncScheduler`, `SecurityConfig`; `finance-service` `ExternalDataCompanyClient`, `ExternalDataSnapshotRefresher` — origin/main `ea5886bd` 기준
- 실측: settlement-prod 파드 로그(external-data · finance, 2026-10-26~27), 공개 도메인 curl(2026-10-28 02:21 KST), 운영 nginx ConfigMap `settlement-frontend-nginx`
