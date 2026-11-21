---
layout: post
title: "위성DMB·LTE·5G 는 같은 주파수의 세 시대다 — 2.6GHz 가 걸어온 길"
date: 2026-11-21 17:21:52 +0900
categories: [network, telecom]
tags: [위성DMB, LTE, 5G, 주파수, 2.6GHz, eMBMS, 5G-MBS, NTN, 3GPP, ITU]
---

## 한 줄 요약

위성DMB, LTE, 5G 의 관계는 기술 계보로 보면 잘 안 보이고 **주파수 장부**로 보면 한 줄로 이어진다.

- 위성DMB 가 쓰던 **2.6GHz 대역**은 서비스가 끝난 뒤 회수돼 **LTE 광대역 주파수**로 경매됐다.
- 그 LTE 주파수는 5G 를 LTE 에 기대 돌리는 **NSA** 방식의 앵커 역할을 했다.
- 2025년 12월 정부는 이 대역을 **2029년까지 3년만** 재할당하고, 이후 **TDD 로 바꿔 6G 후보로** 내놓을 수 있다고 밝혔다.

위성DMB 가 하려던 두 가지, *모바일 방송*과 *위성에서 폰으로 직접 쏘기*도 사라지지 않았다. 둘 다 이제는 이동통신 표준 안으로 들어가 있다. 방송은 eMBMS 와 5G MBS 가, 위성 직결은 5G NTN 이 맡는다.

---

## 1. 위성DMB 란 무엇이었나

위성DMB(Satellite Digital Multimedia Broadcasting) 는 정지궤도 위성이 휴대 단말로 직접 방송을 쏘는 서비스였다.

- **사업자:** TU미디어. 2005년 5월 상용화했다.
- **위성:** '한별(MBSat)'. SK텔레콤과 일본 MBCo 가 공동으로 2004년 3월 쏘아 올렸다 ([뉴시스, 2012-07-05](https://www.newsis.com/view/NISX20120705_0011251056)).
- **주파수:** 2630–2655MHz, 폭 25MHz ([디지털타임스, 2012-07-03](https://www.dt.co.kr/article/10722679); [헤럴드경제, 2012-07-04](https://biz.heraldcorp.com/article/10252002)).

이 대역은 국제적으로도 근거가 있다. ITU 전파규칙(RR) 각주 5.418 은 제3지역 일부 국가에서 2535–2655MHz 를 방송위성업무(BSS, 음성)에 쓸 수 있게 했다. ITU 결의 528 은 그 사용을 **상단 25MHz, 즉 2630–2655MHz** 로 제한한다 ([BAKOM, RR footnotes](https://www.bakom.admin.ch/en/footnotes-of-rr-eca)). 비정지궤도 BSS(음성)는 결의 539(Rev.WRC-19)가 2605–2655MHz 에 대해 따로 다룬다 ([ITU, Resolution 539](https://www.itu.int/dms_pub/itu-r/oth/0c/0a/R0C0A00000F00119PDFE.pdf)).

정리하면 위성DMB 는 *위성 방송용으로 국제적으로 비워 둔 칸*에 들어간 서비스였다.

## 2. 왜 끝났나

보도된 숫자로 보면 흐름은 단순하다.

- 가입자는 2009년 200만 명을 넘겼다가 2012년 6월 3만9천 명까지 줄었다.
- 누적 적자는 3,318억 원이었다 ([부산일보, 2012-07-07](https://www.busan.com/view/busan/view.php?code=20120707000012); [뉴시스](https://www.newsis.com/view/NISX20120705_0011251056)).
- 원인으로는 스마트폰 확산과 무료 지상파DMB 앱이 꼽혔다.
- 방송통신위원회는 2012년 8월 31일자 폐업을 받아들였고, 서비스는 그날 끝났다.

위성DMB 는 *한 곳에서 많은 사람에게 같은 화면을 뿌리는* 방송형 모델이었다. 스마트폰은 *각자 원하는 걸 받는* 유니캐스트 모델이었다. 이용자가 후자로 옮겨 가면서 위성DMB 는 설 자리를 잃었다.

## 3. 회수된 주파수가 LTE 로 간다

### 회수 (2013년 2월)

위성DMB 용 2.6GHz 대역은 SK텔레콤에 *위성망 임대용*으로 할당돼 있었다.

- 이용기간은 2004년 7월 21일부터 2016년 7월 20일까지였고, 대가는 78억 원이었다.
- 정부는 이를 조기 회수하면서 전파법 제7조 제5항에 따라 21억5천만 원을 돌려줬다 ([ZDNet, 2013-02-20](https://zdnet.co.kr/view/?no=20130220150042); [디지털데일리, 2013-02-20](https://www.ddaily.co.kr/page/view/2013022016093428669); [이투데이](https://www.etoday.co.kr/news/view/693815)).

### 왜 2.6GHz 가 "황금주파수"였나

2.6GHz 의 하향 2620–2690MHz 는 LTE **Band 7**(FDD)의 하향 링크와 겹친다 ([3GPP TS 36.101](https://www.3gpp.org/DynaReport/36101.htm)). 위성DMB 의 2630–2655MHz 가 바로 이 안에 들어 있다.

당시 보도는 GSA 자료(2012년 6월)를 인용해 상용 LTE 사업자 80곳 중 절반 가까이가 이 대역을 쓴다고 전했다 ([디지털타임스, 2012-07-03](https://www.dt.co.kr/article/10722679)). 전 세계가 같이 쓰는 대역이면 단말 수급과 로밍이 쉬워진다. 국내에서 '황금주파수'라고 부른 이유다.

### 두 번의 경매

| 경매 | 낙찰 | 폭 | 금액 | 출처 |
| --- | --- | --- | --- | --- |
| 2013-08-30 | LG유플러스 (B2 블록) | 40MHz | 4,788억 원 | [과기정통부(당시 미래부) 보도자료](https://www.msit.go.kr/bbs/view.do?bbsSeqNo=94&mId=113&mPid=112&nttSeqNo=1212765&pageIndex=1&sCode=user&searchOpt=ALL&searchTxt=%EC%A3%BC%ED%8C%8C%EC%88%98); [연합뉴스](https://www.yna.co.kr/view/AKR20130830080400017) |
| 2016-05-02 | SK텔레콤 (D 블록) | 40MHz | 9,500억 원 | [과기정통부 보도자료](https://www.msit.go.kr/bbs/view.do?bbsSeqNo=94&mId=113&mPid=238&nttSeqNo=1296354&sCode=user); [연합뉴스](https://www.yna.co.kr/view/AKR20160502092400017) |
| 2016-05-02 | SK텔레콤 (E 블록) | 20MHz | 3,277억 원 | 같은 출처 |

2013년 경매 총액은 2조4,289억 원이었다. 1.8GHz 는 SKT(35MHz, 1조500억 원)와 KT(15MHz, 9,001억 원)가 가져갔다 ([디지털데일리](https://www.ddaily.co.kr/page/view/2013083020490046269); [KBS](https://news.kbs.co.kr/news/view.do?ncd=2716246)). 2016년 총액은 2조1,106억 원이었고 700MHz 는 유찰됐다 ([ZDNet](https://zdnet.co.kr/view/?no=20160502124359); [Korea Herald](https://www.koreaherald.com/article/947155)).

같은 2.6GHz 인데 낙찰가가 크게 다르다. 최초 낙찰가를 MHz·연 단위로 나누면 다음과 같다(이용기간은 SKT 10년, LG유플러스 8년, [디지털타임스, 2025-11-19](https://www.dt.co.kr/article/12030281) 기준).

$$
\text{SKT} = \frac{12{,}777\ \text{억 원}}{60\ \text{MHz} \times 10\ \text{년}} \approx 21.3\ \text{억 원/MHz·년}
$$

$$
\text{LG U+} = \frac{4{,}788\ \text{억 원}}{40\ \text{MHz} \times 8\ \text{년}} \approx 15.0\ \text{억 원/MHz·년}
$$

이 차이는 2025년 재할당 때 두 회사가 다툰 쟁점이 됐다(5절).

## 4. 5G 는 처음에 LTE 위에 올라탔다

국내 5G 는 대부분 **NSA(비단독모드)** 로 시작했다. 신호 처리는 LTE 가 맡고, 5G 는 데이터 통로를 보태는 구조다. 과기정통부도 2025년 12월 브리핑에서 "다수 사업자들이 여전히 5G 서비스에 LTE 를 함께 사용하는" NSA 중심이라고 직접 밝혔다 ([정책브리핑, 2025-12-10](https://www.korea.kr/briefing/policyBriefingView.do?newsId=156734418)).

그래서 2.6GHz 같은 LTE 주파수는 LTE 가입자만 받친 게 아니다. **5G 서비스의 바닥**도 받쳤다. 같은 브리핑에서 정부는 LTE 가 5G 매출에 얼마나 기여하는지 통계로 떼어 내기가 가장 어려웠다고 설명했다.

## 5. 2025년 재할당: "3년만 쓰고 비워라"

2026년에 이용기간이 끝나는 3G·LTE 주파수 370MHz 에 대해 과기정통부가 2025년 12월 10일 세부 방안을 확정했다 ([정책브리핑](https://www.korea.kr/briefing/policyBriefingView.do?newsId=156734418); [연합뉴스](https://www.yna.co.kr/view/AKR20251210081551017); [전자신문](https://www.etnews.com/20251210000335)).

- **5G SA 의무화.** 지금까지 구축한 5G 무선국을 2026년 말까지 5G 단독모드 코어에 연결해야 한다. 이행점검은 2027년부터다.
- **재할당 대가.** 기준가격 3조6천억 원에서 14.8% 낮춘 약 3조1천억 원이다. 근거는 SA 로 가면 LTE 가 5G 에 기여하는 몫이 줄어든다는 것이다. 실내 5G 무선국을 2만 국 이상 지으면 약 2조9천억 원까지 내려간다.
- **2.6GHz(100MHz) 와 1.8GHz(20MHz) 는 이용기간 3년.** 나머지 250MHz 는 5년이다.
- **5G 로 전환 허용.** 이용자 보호에 문제가 없으면 재할당 주파수를 5G 이상 방식으로 쓸 수 있게 고시를 미리 고친다.

2.6GHz 를 3년으로 자른 이유는 브리핑에 그대로 나온다. 정부는 예전 스펙트럼 플랜에서부터 **TDD 전환을 통한 광대역화**를 말해 왔고, 3년 뒤 이 대역을 **6G 후보 대역**으로 제시할 수도 있다고 했다.

2.6GHz 100MHz 는 SKT 60MHz 와 LG유플러스 40MHz 를 합친 폭이다. 정부는 SKT 가 요구한 '동일 대역 동일 대가'를 받아들이지 않고 14.8% 할인율을 일괄 적용했다 ([전자신문](https://www.etnews.com/20251210000335)). 이 산정 방식은 2028년 3.5GHz 재할당을 앞두고 제도 개선 연구반에서 다시 다뤄지고 있다 ([전자신문, 2026-09-14](https://www.etnews.com/20260914000315); [디지털데일리, 2026-10-28](https://www.ddaily.co.kr/page/view/2026102817520622437)).

이렇게 보면 같은 25MHz 칸이 세 번 쓰임새를 바꾼다.

1. 위성 방송(2005–2012)
2. LTE 광대역이자 5G NSA 의 앵커(2013–2029)
3. 6G 후보(2029 이후 검토)

## 6. 방송의 귀환: eMBMS → 5G MBS

위성DMB 가 포기한 *한 번에 여럿에게 뿌리는* 전송은 이동통신 규격 안으로 들어왔다.

- **LTE eMBMS.** KT 와 삼성전자는 2014년 1월 'LTE eMBMS' 를 상용화했다('올레 LTE 플레이'). 서울 송파구에서 갤럭시노트3 로 시작했다 ([삼성전자 뉴스룸, 2014-01-26](https://news.samsung.com/kr/%ec%82%bc%ec%84%b1%ec%a0%84%ec%9e%90-kt-%ec%84%b8%ea%b3%84-%ec%b5%9c%ec%b4%88-lte-embms-%ea%b8%b0%ec%88%a0-%ea%b0%9c%eb%b0%9c-%ec%84%b1%ea%b3%b5-%eb%b0%8f-%ec%83%81%ec%9a%a9%ed%99%94-%ec%84%9c); [전자신문](https://www.etnews.com/201401260140)). '세계 최초', 'DMB 대비 10배 화질'은 **벤더 주장**이고, 이 글에서 따로 검증하지 않았다.
- **3GPP 의 진화.** 3GPP 에 따르면 eMBMS 는 Rel-9 부터 Rel-16 까지 계속 보강됐다. Rel-14 이후 FeMBMS 가 나왔고, Rel-16 에서 LTE 기반 '5G 지상 방송'이 정리됐다. Rel-17 에서는 5G 코어 위에 **NR MBS** 구조(TS 23.247)가 들어왔다 ([3GPP, Broadcast & Multicast](https://www.3gpp.org/technologies/broadcast-multicast1); [5G-MAG](https://www.5g-mag.com/docs/5g-broadcast.pdf)).
- **방송 전용 대역.** 방송 전용 UHF 대역(band 108, 470–698MHz)은 Rel-18 에서 추가됐다 ([인도 TEC 기술보고서, 2024-03](https://tec.gov.in/pdf/TR/TEC_Technical_Report_on_Direct_Broadcasting_To_Mobile_Devices_2024_March.pdf)).

위성DMB 는 방송망과 통신망이 *따로* 있었다. 지금의 방송은 같은 기지국과 코어 안의 *전송 모드 하나*다. 이용자가 적으면 유니캐스트로, 많으면 멀티캐스트로 바꿔 보낸다.

## 7. 위성의 귀환: 5G NTN

*위성에서 폰으로 직접* 보내는 것도 다시 돌아왔다. 이번에는 별도 방송 규격이 아니라 5G 표준의 일부다.

- **Rel-17.** NTN 규범 요구사항이 처음 들어간 릴리스다(ASN.1 동결 2022년 6월). 투명(transparent) 페이로드만 다룬다. 위성용 FDD 대역 **n255(L대역)** 와 **n256(S대역, 상향 1980–2010 / 하향 2170–2200MHz)** 이 새로 생겼다 ([3GPP, NTN overview](https://www.3gpp.org/technologies/ntn-overview); [3GPP Release 17](https://www.3gpp.org/specifications-technologies/releases/release-17)).
- **Rel-18.** 30MHz 채널 대역폭과 **n254**(상향 1610–1626.5 / 하향 2483.5–2500MHz)를 추가했다 ([3GPP, NTN overview](https://www.3gpp.org/technologies/ntn-overview)).
- **ITU-R M.2177-0(2026-02).** NR-NTN 과 IoT-NTN 으로 이뤄진 '5G-NTN' 을 IMT-2020 의 위성 무선 인터페이스로 규정했다 ([ITU-R M.2177-0](https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.2177-0-202602-I)).
- **두 갈래.** GCF 는 위성 직결을 둘로 나눈다. 지상 이동통신 대역을 써서 개조하지 않은 폰에 붙는 **D2D-IMT** 와, NTN 전용 위성 대역을 쓰는 **D2D-MSS** 다 ([GCF, 2026-07-30](https://www.globalcertificationforum.org/news/blog/3gpp-non-terrestrial-networks-the-role-of-gcf-certification.html)).

한별 위성은 *위성DMB 전용 단말*만 받을 수 있었다. NTN 은 *같은 5G 칩셋*이 지상 기지국과 위성을 모두 상대하도록 설계됐다. 위성DMB 가 겪은 단말 생태계 문제를 표준 단계에서 피해 가려는 설계다.

## 8. 상관관계 정리

| 축 | 위성DMB (2005–2012) | LTE (2013–) | 5G (2019–) |
| --- | --- | --- | --- |
| 2.6GHz 의 역할 | 위성 방송 하향(2630–2655MHz) | Band 7 광대역 FDD | NSA 앵커 → 2029년 이후 TDD·6G 후보 검토 |
| 방송형 전송 | 전용 위성 방송 | eMBMS(Rel-9~) | 5G Broadcast(Rel-16) · NR MBS(Rel-17) |
| 위성→단말 직결 | 한별, 전용 단말 | — | NTN(Rel-17 n255/n256, Rel-18 n254) |
| 망 구조 | 방송망 따로, 통신망 따로 | 통신망 안의 방송 모드 | 5G 코어 안의 PTM/PTP 전환 |

세 기술은 서로 대체한 게 아니다. 한 기술이 실패한 *자리*(주파수)와 *발상*(방송, 위성 직결)을 다음 기술이 이어받았다.

## 근거의 한계

- **블록 대응은 확인하지 못했다.** 위성DMB 의 2630–2655MHz 가 2013·2016년 경매의 어느 블록(A/B, D/E)에 정확히 들어갔는지 1차 자료로 확인하지 못했다. 이 글은 "2.6GHz 대역이 회수돼 LTE 로 경매됐다"까지만 주장한다.
- **가입자·적자 수치는 언론 보도 기준이다.** 원자료(TU미디어·방통위 공시)는 확인하지 못했다.
- **'세계 최초'와 화질 비교는 벤더 주장이다.** eMBMS 의 '세계 최초', 'DMB 대비 10배 화질'은 삼성전자·KT 발표이고, 중립 제3자의 검증은 찾지 못했다.
- **MHz·연 단가는 단순 비교다.** 최초 낙찰가만 이용기간으로 나눈 값이다. 2021년 재할당 할인 등은 반영하지 않았다.
- **6G 전환은 확정이 아니다.** 2.6GHz 의 TDD 전환과 6G 후보화는 정부가 "검토"한다고 밝힌 수준이다.

## References

1. 과학기술정보통신부, 「이동통신 주파수 재할당 세부 정책방안」 브리핑, 대한민국 정책브리핑, 2025-12-10. <https://www.korea.kr/briefing/policyBriefingView.do?newsId=156734418>
2. 미래창조과학부, 2013 LTE 주파수 할당 결과 보도자료. <https://www.msit.go.kr/bbs/view.do?bbsSeqNo=94&mId=113&mPid=112&nttSeqNo=1212765&pageIndex=1&sCode=user&searchOpt=ALL&searchTxt=%EC%A3%BC%ED%8C%8C%EC%88%98>
3. 미래창조과학부, 2016 주파수 경매 결과 보도자료. <https://www.msit.go.kr/bbs/view.do?bbsSeqNo=94&mId=113&mPid=238&nttSeqNo=1296354&sCode=user>
4. ITU-R, Resolution 539 (Rev.WRC-19). <https://www.itu.int/dms_pub/itu-r/oth/0c/0a/R0C0A00000F00119PDFE.pdf>
5. BAKOM (스위스 연방통신청), Footnotes of the ITU Radio Regulations. <https://www.bakom.admin.ch/en/footnotes-of-rr-eca>
6. ITU-R, Recommendation M.2177-0 (02/2026). <https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.2177-0-202602-I>
7. 3GPP, Broadcast & Multicast. <https://www.3gpp.org/technologies/broadcast-multicast1>
8. 3GPP, NTN overview. <https://www.3gpp.org/technologies/ntn-overview>
9. 3GPP, Release 17. <https://www.3gpp.org/specifications-technologies/releases/release-17>
10. 3GPP, TS 36.101 (E-UTRA UE radio transmission and reception). <https://www.3gpp.org/DynaReport/36101.htm>
11. 5G-MAG, 5G Broadcast. <https://www.5g-mag.com/docs/5g-broadcast.pdf>
12. TEC (인도 통신공학센터), Technical Report on Direct Broadcasting to Mobile Devices, 2024-03. <https://tec.gov.in/pdf/TR/TEC_Technical_Report_on_Direct_Broadcasting_To_Mobile_Devices_2024_March.pdf>
13. GCF, 3GPP Non-Terrestrial Networks: the role of GCF certification, 2026-07-30. <https://www.globalcertificationforum.org/news/blog/3gpp-non-terrestrial-networks-the-role-of-gcf-certification.html>
14. 삼성전자 뉴스룸, 삼성전자·KT LTE eMBMS 상용화(벤더 발표), 2014-01-26. <https://news.samsung.com/kr/%ec%82%bc%ec%84%b1%ec%a0%84%ec%9e%90-kt-%ec%84%b8%ea%b3%84-%ec%b5%9c%ec%b4%88-lte-embms-%ea%b8%b0%ec%88%a0-%ea%b0%9c%eb%b0%9c-%ec%84%b1%ea%b3%b5-%eb%b0%8f-%ec%83%81%ec%9a%a9%ed%99%94-%ec%84%9c>
15. 언론 보도: [뉴시스 2012-07-05](https://www.newsis.com/view/NISX20120705_0011251056) · [디지털타임스 2012-07-03](https://www.dt.co.kr/article/10722679) · [헤럴드경제 2012-07-04](https://biz.heraldcorp.com/article/10252002) · [부산일보 2012-07-07](https://www.busan.com/view/busan/view.php?code=20120707000012) · [ZDNet 2013-02-20](https://zdnet.co.kr/view/?no=20130220150042) · [디지털데일리 2013-02-20](https://www.ddaily.co.kr/page/view/2013022016093428669) · [이투데이](https://www.etoday.co.kr/news/view/693815) · [연합뉴스 2013-08-30](https://www.yna.co.kr/view/AKR20130830080400017) · [디지털데일리 2013-08-30](https://www.ddaily.co.kr/page/view/2013083020490046269) · [KBS](https://news.kbs.co.kr/news/view.do?ncd=2716246) · [연합뉴스 2016-05-02](https://www.yna.co.kr/view/AKR20160502092400017) · [ZDNet 2016-05-02](https://zdnet.co.kr/view/?no=20160502124359) · [Korea Herald](https://www.koreaherald.com/article/947155) · [전자신문 2014-01-26](https://www.etnews.com/201401260140) · [디지털타임스 2025-11-19](https://www.dt.co.kr/article/12030281) · [연합뉴스 2025-12-10](https://www.yna.co.kr/view/AKR20251210081551017) · [전자신문 2025-12-10](https://www.etnews.com/20251210000335) · [전자신문 2026-09-14](https://www.etnews.com/20260914000315) · [디지털데일리 2026-10-28](https://www.ddaily.co.kr/page/view/2026102817520622437)
