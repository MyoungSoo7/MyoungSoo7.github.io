---
layout: post
title: "AI 칩은 왜 검사를 더 많이 하게 만드나 — 반도체 테스트 소켓과 리노공업의 2026년"
date: 2026-11-08 21:08:34 +0900
categories: [semiconductor, ai]
tags: [semiconductor, ai, test-socket, ate, hbm, advanced-packaging, leeno, isc, advantest, teradyne]
---

AI 반도체 이야기는 대부분 칩을 **만드는** 쪽에서 끝난다. GPU, HBM, 2나노, CoWoS 같은 이야기들이다. 그런데 칩은 출하되기 전에 반드시 **검사**를 거친다. 2026년 반도체 공급망에서 가장 조용하게 커진 영역이 이 검사다. 이 글은 세 겹으로 내려가며 정리한다.

1. **시장**: 반도체 호황 속에서 검사 장비 시장은 얼마나 커졌나
2. **기술**: AI 칩은 왜 검사를 "더 많이, 더 어렵게" 만드나
3. **회사**: 검사용 소모품을 만드는 리노공업(코스닥 058470)은 그 흐름을 얼마나 타고 있나. 그리고 왜 하필 올해 62일 동안 공장이 멈췄나

출처는 등급을 나눠 표시했다. **[공식]** 은 공시·업계 단체·회사 IR 자료, **[벤더]** 는 검사 장비 회사가 자기 시장에 대해 한 말, **[증권사]** 는 애널리스트 추정, **[보도]** 는 언론 보도다.

---

## 1. 시장 — 반도체 +90%, 검사 장비 +31%

세계반도체시장통계기구(WSTS)의 2026년 봄 전망은 올해 세계 반도체 시장을 **1조 5,100억 달러(+90%)** 로 봤다 **[공식]** ([WSTS](https://www.wsts.org/76/103/Global-Semiconductor-Market-Surges-Beyond-15T-2026)). 그런데 성장은 고르지 않다.

| 구분 (WSTS 2026 전망) | 증가율 |
| --- | --- |
| 메모리 | 약 +250% (8,000억 달러 이상, AI·HBM 주도) |
| 로직 | +37% |
| 마이크로프로세서 | +20% |
| 아날로그 | +10% |

+90%의 대부분은 **메모리 가격**이 만든 숫자다. 칩 값이 오른 것과 칩을 만들고 검사하는 **작업량**이 늘어난 것은 서로 다른 이야기다. 작업량은 장비 시장을 보면 보인다.

SEMI의 2026년 중간 전망 **[공식]** ([SEMI, 2026-07-14](https://www.semi.org/en/semi-press-release/global-semiconductor-equipment-sales-forecast-to-reach-a-record-229-billion-dollars-in-2028-semi-reports)):

| 장비 분야 | 2025 | 2026 전망 | 2028 전망 |
| --- | --- | --- | --- |
| 전체 반도체 장비 | — | 1,659억 달러 (+23.2%) | 2,295억 달러 |
| **테스트 장비** | +55.3% | **153억 달러 (+31.0%)** | 208억 달러 |
| 조립·패키징 장비 | +20.8% | 67억 달러 (+9.6%) | 86억 달러 |

SEMI는 테스트 장비 성장의 이유로 "디바이스 복잡도 증가, 첨단·이종 패키징 확산, AI·HBM 디바이스의 더 엄격한 성능·신뢰성 요구"를 든다. 2025년 12월 전망에서 2026년 테스트 장비 성장률은 +12.0%였다 ([SEMI, 2025-12-16](https://www.semi.org/en/semi-press-release/global-semiconductor-equipment-sales-projected-to-reach-a-record-of-156-billion-dollars-in-2027-semi-reports)). 반년 만에 +31%로 올라간 셈이다.

검사 장비(ATE) 양대 업체의 실적도 같은 방향이다.

- **Advantest**: 회계연도 2026년 1분기(4~6월) 매출 3,675억 엔(+39.3%), 영업이익 1,900억 엔(+53.3%)으로 분기 최고치를 냈다 **[공식]** ([결산 자료](https://www.advantest.com/document/en/investors/ir-library/result/E_FR_FY2026_1Q.pdf)). 10월에는 연간 매출 전망을 1조 7,140억 엔에서 1조 8,630억 엔으로 다시 올렸다 ([실적 전망](https://www.advantest.com/en/investors/financial-highlights/forecast/)).
- **Teradyne**: 2026년 3분기 매출 13억 600만 달러(+70%)를 기록했다. 이 중 반도체 테스트가 10억 7,200만 달러다 **[공식]** ([보도자료, 2026-10-27](https://investors.teradyne.com/news-events/press-releases/detail/455/teradyne-reports-third-quarter-2026-results)).

Teradyne CEO는 실적 발표에서 반도체 설비투자 중 테스트가 차지하는 비중이 **2025년 6.4%에서 2026년 1~8월 8.1%로** 올랐다고 말했다 **[벤더]** ([컨퍼런스콜 녹취, Motley Fool](https://www.fool.com/earnings/call-transcripts/2026/10/28/teradyne-ter-q3-2026-earnings-call-transcript/)). 회사 자체 집계로 보이며, 산정 방법은 공개되지 않았다.

---

## 2. 기술 — AI 칩이 검사를 늘리는 세 가지 경로

Advantest는 테스터 수요의 구조적 동인을 이렇게 요약한다. 칩 **생산량**만이 아니라 세대마다 늘어나는 **테스트 콘텐츠(test content)와 테스트 삽입 횟수(test insertions)** 가 더 중요하다는 것이다 **[벤더]** ([Q1 FY2026 발표 노트](https://www.advantest.com/document/en/investors/ir-library/result/JE_BIZ_260729_note.pdf)). 이를 풀면 세 가지 경로가 된다.

### ① 비싼 다이를 붙이기 전에 걸러야 한다 — Known Good Die

AI 가속기는 한 패키지 안에 로직 다이와 HBM 스택 여러 개, I/O 다이를 같이 넣는다(2.5D/3D, 칩렛). 불량 다이 하나가 패키지에 들어가면 같이 붙은 멀쩡한 고가 다이까지 전부 버리게 된다. 그래서 **붙이기 전에** 웨이퍼 단계 검사를 늘리고, 붙인 뒤에도 패키지 전체를 다시 검사한다. LS증권은 "후공정까지 불량이 유출될 경우 발생하는 손실비용이 크게 증가"해 적층·패키징 이전 웨이퍼 테스트의 테스트 강도가 높아지고 있다고 정리했다 **[증권사]** ([LS증권 산업 리포트](https://www.hankyung.com/koreamarket/consensus/pdf/2026-09-959b0b1f57cc1a75c3a46e72ccdf7a8e)).

### ② 패키지가 커지고 핀이 많아진다 — 소켓 사양이 올라간다

최종 검사(Final Test)에서는 칩을 **테스트 소켓**에 꽂아 검사 장비와 연결한다. AI 칩은 이 소켓에 요구하는 조건을 동시에 끌어올린다. 같은 LS증권 리포트의 정리는 다음과 같다.

- **고전류**: 수백 와트를 쓰는 칩에 안정적으로 전력을 공급해야 한다.
- **고속 신호**: 데이터 전송 속도가 올라가 신호 손실과 노이즈를 줄여야 한다.
- **대형화·미세 피치**: 패키지는 커지고 핀은 많아지며, 핀 사이 간격은 좁아진다.

결국 범용 소켓보다 고주파·고전류·미세 피치를 감당하는 **고사양 소켓**의 비중이 커지고, 단가도 올라간다.

### ③ 실제 환경 검사가 한 단계 더 붙는다 — SLT

기능 검사만으로는 부족해서, 칩을 실제 시스템과 비슷한 보드에 올려 소프트웨어를 돌려 보는 **시스템 레벨 테스트(SLT)** 가 늘고 있다. 같은 칩이 소켓을 한 번 더 거치는 것이다. Teradyne은 GPU 차세대 제품의 SLT를, ISC는 북미 고객사 플래그십 AP용 SLT 소켓 수주를 언급했다(아래 4장).

이 세 경로는 **모바일 칩에도 그대로 내려온다.** 북미 스마트폰 업체의 플래그십 AP에 WMCM(Wafer-level Multi-Chip Module) 패키징이 적용되면서, 여러 칩을 웨이퍼 단계에서 묶어 연결 상태와 개별 칩 기능을 동시에 검증해야 하게 됐다. 그만큼 소켓의 핀 수와 단가도 올라간다 **[증권사]** ([iM증권, 2026-10-12](https://file.alphasquare.co.kr/media/pdfs/market-report/%EB%A6%AC%EB%85%B8%EA%B3%B5%EC%97%85AI20261012iM%EC%A6%9D%EA%B6%8C.pdf); [메리츠증권, 2026-02-11](https://file.alphasquare.co.kr/media/pdfs/company-report/20260211210405640K_02.pdf)).

---

## 3. 회사 — 리노공업은 이 흐름의 어디에 있나

### 무엇을 파나

리노공업은 1978년 '리노공업사'로 출발해 2001년 코스닥에 상장했다. 주력 제품은 두 가지다. 검사용 프로브(**LEENO PIN**)와 **IC TEST SOCKET**으로, 둘 다 원래 전량 수입하던 것을 자체 브랜드로 만들었다 **[공식]** ([KIND, 2026년 1분기 보고서](https://kind.krx.co.kr/external/2026/05/14/000390/20260514000861/11013.htm)). 공시는 이 두 제품을 테스트 장비가 다양한 칩과 호환되도록 **인터페이스 역할을 하는 소모성 부품이자 다품종 주문생산 제품**으로 설명한다. 이 산업에 대해서는 기술 축적에 오랜 시간이 걸리는 진입장벽 높은 산업이라고 쓴다. 같은 보고서의 "시장여건"에는 AI·데이터센터 확장으로 "테스트 공정 난이도가 상승함에 따라" 수요도 함께 성장할 것으로 기대한다고 적혀 있다.

소모품이라는 점이 핵심이다. 칩이 수없이 꽂혔다 빠지는 동안 핀과 소켓이 닳고, **새 칩이 나올 때마다 그 칩에 맞춰 새로 설계**해야 한다. 그래서 매출은 칩 가격보다 **새 칩 개발 건수와 검사 물량**에 가깝게 움직인다. 증권사들은 리노공업이 출하하는 테스트 소켓 중 R&D(신규 칩 개발)용과 양산용 비중을 6:4 정도로 추정한다 **[증권사]** ([메리츠증권, 2026-08-15](http://home.imeritz.com/include/resource/research/WorkFlow/20260815161718430K_02.pdf); iM증권).

### 숫자 — 2024 → 2026 상반기 [공식]

| 기간 | 매출 | 영업이익 | 소켓 비중 | 비고 |
| --- | --- | --- | --- | --- |
| 2024년 | 2,782억 원 | — | 61.77% | PIN 27.02% |
| 2025년 | 3,725억 원 | — | 65.48% | PIN 23.38% |
| 2026년 1분기 | 998억 원 | 473억 원 | 64.10% | |
| 2026년 2분기 | 1,432억 원 | 735억 원 | 약 71.5% | 분기 최대, 영업이익률 51.3% |
| 2026년 상반기 | 2,430억 원 | 1,208억 원 | 68.48% | 매출 +27.2%, 영업이익 +36.7% |

2024~2025년 매출과 제품 비중은 사업보고서, 2분기와 상반기 수치는 반기보고서를 인용한 보도에서 가져왔다([스마트투데이](https://www.smarttoday.co.kr/ko-kr/articles/112501), [위키트리](https://www.wikitree.co.kr/articles/1152796)). 영업이익률 50%는 제조업에서 드문 수준이다.

### AI와의 거리 — 직접 수혜가 아니라 '간접 수혜'

여기서 오해가 생기기 쉽다. **리노공업의 최대 응용처는 데이터센터 AI 가속기가 아니라 스마트폰 AP다.** 증권사들은 북미 스마트폰 고객사를 가장 큰 고객으로 보고, 매출의 60% 이상이 스마트폰용 AP·모뎀이라는 추정도 있다 **[증권사]**. 메리츠증권은 2분기 실적을 두고 이렇게 분석했다. 소켓 매출 증가는 모바일 양산 성수기에 WMCM 적용에 따른 단가 상승이 더해진 결과다. 그 위에 HPC/AI용 대형 소켓과 중화권 네트워크 칩용 소켓이 성장을 보탰다. 같은 리포트는 네트워크·HPC/AI 같은 "비모바일 차세대 칩 개발"에 리노의 소켓이 활발히 쓰이고 있다고 썼다.

정리하면 리노공업의 AI 수혜는 두 갈래다.

1. **온디바이스 AI**: 스마트폰 AP가 AI 기능 때문에 복잡해지고(2나노, WMCM) 소켓 단가가 오른다.
2. **AI 칩 개발 붐**: 빅테크의 자체 ASIC 개발이 늘면서 R&D용 소켓 주문이 늘어난다.

반면 데이터센터 AI 칩 **양산** 검사에서는 경쟁사 ISC가 더 직접적으로 노출돼 있다. ISC는 3분기 매출 718억 원 중 AI 관련이 626억 원(87%)이고 그중 AI 데이터센터가 530억 원이었다고 밝혔다 **[공식·회사 발표]** ([머니투데이/더벨](https://www.mt.co.kr/index.php/stock/2026/10/27/2026102711089649410); [세종기업데이터 컨퍼런스콜 정리](https://sejongdata.com/insights/159)). 두 회사는 소켓 방식부터 다르다. 리노공업은 금속 핀을 쓰는 **포고(pogo) 소켓**에서, ISC는 **실리콘 러버 소켓**에서 출발했다.

AI 반도체와 리노공업의 실적은 같은 방향을 향하지만 **같은 속도로 움직이지는 않는다.** 시장이 +90%일 때 리노공업은 +27%였다. 검사 장비 시장(+31%)과 비교하면 비슷한 속도다. 메모리 가격이 아니라 검사 작업량을 따라간다고 보면 숫자가 맞는다.

---

## 4. 62일 파업 — 수요가 아니라 공급이 끊겼다

2분기 최대 실적이 나온 바로 그 여름, 공장이 멈췄다 **[보도]** ([연합뉴스, 2026-09-22](https://www.yna.co.kr/view/AKR20260922104200051)).

- 노조(금속노조 부산양산지부 리노공업지회)는 7월 하순 무기한 전면파업에 들어갔다. 파업 대상 665명 중 약 340명이 참여했다.
- 핵심 쟁점은 **성과급 지급 조건 변경**이었다.
- 9월 8일 잠정합의가 최종 문구에서 무산됐고, 노조원 약 300명이 9월 23일 복귀했다. 전면파업 62일 만이다. 노조는 이를 "전술 변경"이라고 밝혔다.
- 회사는 "감당할 수 있는 최대치를 제시했다"는 입장이다([부산일보](https://www.busan.com/view/section/view.php?code=2026092218334780701)). 노조는 회사가 인사 조항에서 입장을 바꿨다고 주장한다([인베스트뉴스](https://www.investnews.co.kr/news/articleView.html?idxno=3002856)). 10월 20일 제13차 교섭도 결렬됐다([위키트리](https://www.wikitree.co.kr/articles/1167663)).

이 사건은 2장의 구조와 정확히 맞물린다. **주문생산 소모품이라 재고로 버틸 수 없다.** 고객의 새 칩 일정은 기다려 주지 않는다. 생산이 멈추면 고객은 다른 공급사로 간다.

실제로 경쟁사 쪽에서 신호가 나왔다. 디일렉에 따르면 ISC는 북미 최대 스마트폰 고객사 내 소켓 점유율을 **20%에서 40%로** 늘렸다. 기사는 그 이유를 "기존 주요 공급사가 납기를 맞추지 못하자 고객사가 물량을 분산"했기 때문으로 설명한다 **[보도]** ([디일렉, 2026-10-27](https://www.thelec.kr/news/articleView.html?idxno=64326)). ISC가 이 고객사에 공급한 것은 리노공업의 주력과 같은 **포고 소켓**이다. 다만 기사는 그 "기존 공급사"가 어디인지 밝히지 않았다. 리노공업 파업과 시기가 겹친다는 것은 **추론**이지 확인된 사실이 아니다. 위키트리는 파업 기간 물량 일부가 해외 경쟁사로 넘어갔다고 보도했지만, 이 역시 회사나 고객사가 확인한 내용은 아니다.

### 3분기 — 증권사 추정치 [증권사]

3분기 실적은 11월 8일 현재 미발표다. 아래 숫자는 공시가 아니라 **추정치**다.

| 출처 | 3Q26 매출 | 3Q26 영업이익 |
| --- | --- | --- |
| 메리츠증권 (8/15, 파업 장기화 전) | — | 560억 원 |
| SK증권 (10월 초) | 855억 원 | 385억 원 |
| 메리츠증권 (10/10) | 862억 원 | 386억 원 |
| DS투자증권 (10/6) | 842억 원 | 396억 원 |

출처: [메리츠 8/15](http://home.imeritz.com/include/resource/research/WorkFlow/20260815161718430K_02.pdf), [핀포인트뉴스(SK증권 인용)](https://www.pinpointnews.co.kr/news/articleView.html?idxno=494167), [메리츠 10/10](https://file.alphasquare.co.kr/media/pdfs/company-report/20261010173001526K_02.pdf), [파이낸셜뉴스(DS 인용)](https://www.fnnews.com/news/202610060835530838).

같은 증권사(메리츠)의 추정이 8월 560억 원에서 10월 386억 원으로 내려갔다. **약 170억 원**이 시장이 매긴 파업 비용의 첫 근사치다. SK증권은 파업이 3분기 가동일의 50~60%에 영향을 줬고, 환율 하락도 겹쳤다고 봤다. 세 곳 모두 비수기인 4분기에 밀린 생산을 따라잡는다는 시나리오를 깔고 있다. 다만 이 추정들은 10월 20일 교섭 결렬과 ISC 점유율 보도 **이전**에 나왔다.

---

## 5. 정리 — 무엇을 보면 되나

1. **검사는 AI 반도체의 숨은 비용 항목이다.** SEMI 기준 테스트 장비는 2025년 +55%, 2026년 +31%로 반도체 장비 전체(+23%)보다 빠르게 큰다. 칩이 복잡해질수록 붙이기 전, 붙인 뒤, 시스템에 올린 뒤로 검사 횟수가 는다.
2. **소모품 회사의 강점과 약점은 같은 곳에 있다.** 칩마다 새로 설계해야 하니 진입장벽이 높고 마진이 좋다. 하지만 재고로 버틸 수 없으니 생산이 멈추면 고객 프로젝트가 넘어간다. 한번 넘어간 칩은 그 칩의 수명 동안 돌아오지 않을 수 있다.
3. **리노공업에서 다음에 확인할 것:**
   - 3분기 실적 공시(11월 중순 예상, 작년은 11월 13일 — [KIND](https://kind.krx.co.kr/external/2025/11/13/000310/20251113000790/11013.htm))와 추정치 380억~400억 원의 차이
   - 노사 합의 여부와 부분파업 재개 여부
   - 11월 예정인 신공장 이전([메리츠 2/11](https://file.alphasquare.co.kr/media/pdfs/company-report/20260211210405640K_02.pdf)), 그리고 4분기·내년 상반기에 북미 모바일 고객 물량이 돌아오는지

## 근거의 한계

- **AI 수혜 비중**: 리노공업은 응용처별(모바일/데이터센터/네트워크) 매출을 공시하지 않는다. "스마트폰 60% 이상", "R&D:양산 6:4"는 모두 증권사 추정이다.
- **물량 이탈**: ISC의 점유율 확대 기사는 원인 제공 공급사를 밝히지 않았다. 리노공업과 연결 짓는 것은 시기에 근거한 추론이다.
- **벤더 발언**: "테스트 콘텐츠·삽입 횟수 증가"(Advantest)와 "테스트 비중 6.4%→8.1%"(Teradyne)는 장비 회사가 자기 시장에 대해 한 말이다. 독립 기관의 검증은 찾지 못했다.
- **전망치**: WSTS와 SEMI 수치는 전망이며 연말에 수정된다(WSTS 가을 전망은 12월 1일 예정).
- **3분기 숫자**: 모두 증권사 추정이다. 세 곳의 추정이 비슷한 것이 독립적 검증을 뜻하지는 않는다.
- 2024·2025년 영업이익은 이 글에서 공시 원문으로 직접 대조하지 못해 표에서 비워 두었다.

> 이 글은 공개 자료를 정리한 것으로 특정 종목의 매수·매도를 권유하지 않는다.

## References

**[공식] 공시·업계 단체·회사 IR**
1. 리노공업, 2026년 1분기 보고서 — [KIND](https://kind.krx.co.kr/external/2026/05/14/000390/20260514000861/11013.htm)
2. 리노공업, 2024 사업보고서 — [KIND](https://kind.krx.co.kr/external/2025/03/18/000255/20250318001398/11011.htm)
3. 리노공업, 2025년 3분기 보고서 — [KIND](https://kind.krx.co.kr/external/2025/11/13/000310/20251113000790/11013.htm)
4. WSTS, Spring 2026 Forecast — [wsts.org](https://www.wsts.org/76/103/Global-Semiconductor-Market-Surges-Beyond-15T-2026)
5. SEMI, Mid-Year Total Semiconductor Equipment Forecast (2026-07-14) — [semi.org](https://www.semi.org/en/semi-press-release/global-semiconductor-equipment-sales-forecast-to-reach-a-record-229-billion-dollars-in-2028-semi-reports)
6. SEMI, Year-End Equipment Forecast (2025-12-16) — [semi.org](https://www.semi.org/en/semi-press-release/global-semiconductor-equipment-sales-projected-to-reach-a-record-of-156-billion-dollars-in-2027-semi-reports)
7. Advantest, FY2026 1Q Consolidated Financial Results — [PDF](https://www.advantest.com/document/en/investors/ir-library/result/E_FR_FY2026_1Q.pdf) / Earnings Forecast — [advantest.com](https://www.advantest.com/en/investors/financial-highlights/forecast/)
8. Teradyne, Third Quarter 2026 Results (2026-10-27) — [investors.teradyne.com](https://investors.teradyne.com/news-events/press-releases/detail/455/teradyne-reports-third-quarter-2026-results)

**[벤더] 장비 회사 발언**
9. Advantest, Q1 FY2026 presentation notes — [PDF](https://www.advantest.com/document/en/investors/ir-library/result/JE_BIZ_260729_note.pdf)
10. Teradyne Q3 2026 earnings call transcript — [Motley Fool](https://www.fool.com/earnings/call-transcripts/2026/10/28/teradyne-ter-q3-2026-earnings-call-transcript/)

**[증권사] 애널리스트 리포트·추정**
11. LS증권, 반도체 인프라·테스트 밸류체인 리포트 (2026-09) — [PDF](https://www.hankyung.com/koreamarket/consensus/pdf/2026-09-959b0b1f57cc1a75c3a46e72ccdf7a8e)
12. 메리츠증권, 리노공업 2Q26 리뷰 (2026-08-15) — [PDF](http://home.imeritz.com/include/resource/research/WorkFlow/20260815161718430K_02.pdf) / 4Q25 리뷰 (2026-02-11) — [PDF](https://file.alphasquare.co.kr/media/pdfs/company-report/20260211210405640K_02.pdf) / 3Q26 프리뷰 (2026-10-10) — [PDF](https://file.alphasquare.co.kr/media/pdfs/company-report/20261010173001526K_02.pdf)
13. iM증권, 리노공업 Company Brief (2026-10-12) — [PDF](https://file.alphasquare.co.kr/media/pdfs/market-report/%EB%A6%AC%EB%85%B8%EA%B3%B5%EC%97%85AI20261012iM%EC%A6%9D%EA%B6%8C.pdf)
14. 핀포인트뉴스, SK증권 3분기 전망 인용 — [pinpointnews.co.kr](https://www.pinpointnews.co.kr/news/articleView.html?idxno=494167)
15. 파이낸셜뉴스, DS투자증권 목표주가 상향 (2026-10-06) — [fnnews.com](https://www.fnnews.com/news/202610060835530838)

**[보도] 언론**
16. 연합뉴스, 리노공업 노조 현장 복귀 (2026-09-22) — [yna.co.kr](https://www.yna.co.kr/view/AKR20260922104200051)
17. 부산일보, 리노공업 파업 (2026-09-22) — [busan.com](https://www.busan.com/view/section/view.php?code=2026092218334780701)
18. 인베스트뉴스, 노조 측 입장 (2026-10-19) — [investnews.co.kr](https://www.investnews.co.kr/news/articleView.html?idxno=3002856)
19. 위키트리, 상반기 실적 (2026-08-16) — [wikitree.co.kr](https://www.wikitree.co.kr/articles/1152796) / 13차 교섭 결렬 (2026-10-20) — [wikitree.co.kr](https://www.wikitree.co.kr/articles/1167663)
20. 스마트투데이, 분기 최대 실적 직후 멈춘 공장 (2026-10-12) — [smarttoday.co.kr](https://www.smarttoday.co.kr/ko-kr/articles/112501)
21. 디일렉, ISC 북미 최대 스마트폰 고객사 점유율 두 배로 (2026-10-27) — [thelec.kr](https://www.thelec.kr/news/articleView.html?idxno=64326)
22. 머니투데이(더벨), ISC 3분기 실적 (2026-10-27) — [mt.co.kr](https://www.mt.co.kr/index.php/stock/2026/10/27/2026102711089649410) / 세종기업데이터, ISC 3Q26 컨퍼런스콜 정리 — [sejongdata.com](https://sejongdata.com/insights/159)
