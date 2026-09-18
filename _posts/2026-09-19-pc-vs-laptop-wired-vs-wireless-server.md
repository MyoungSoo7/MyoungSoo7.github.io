---
layout: post
title: "PC냐 노트북이냐, 유선이냐 무선이냐 — 서버로 쓸 때 성능 차이는 어디서 오나"
date: 2026-09-19 03:45:10 +0900
categories: [infra, hardware]
tags: [home-server, laptop, desktop, ethernet, wifi, ecc, thermal-throttling]
---

집에 남는 데스크톱 PC나 안 쓰는 노트북을 서버로 올려보려 할 때 두 가지 질문이 꼭 나온다.
**"데스크톱과 노트북 중 뭐가 서버로 낫나"**, 그리고 **"유선과 무선 중 뭘 써야 하나"**.

둘 다 "당연히 데스크톱, 당연히 유선" 으로 뭉뚱그리기 쉽지만, 실제 차이가 **어디서
오는지** 를 물리 계층까지 내려가 보면 선택 기준이 또렷해진다. 이 글은 마케팅 수치가 아니라
표준 사양과 공개 연구 자료에 근거해 그 차이를 정리한다.

---

## 1. PC vs 노트북 — 서버 관점의 네 가지 축

### (1) 지속 부하와 발열: 노트북의 근본적 약점

서버 워크로드는 짧게 튀는 벤치마크가 아니라 **장시간 지속되는 부하**다. 여기서 노트북과
데스크톱이 갈린다.

모바일 CPU·GPU도 데스크톱과 같은 정션 온도 한계(대개 95~100°C)를 갖지만, 냉각 시스템의
용량이 작아 그 한계에 **훨씬 빨리, 더 자주** 도달한다. 한계에 닿으면 칩은 손상을 막기 위해
클럭을 낮추는데 이것이 **thermal throttling** 이다. 리뷰 매체
[Notebookcheck](https://www.notebookcheck.net/Opinion-It-s-time-we-talked-about-throttling-in-reviews.234232.0.html)
은 "점점 더 많은 노트북이 지속 부하에서 광고된 성능을 유지하지 못한다"고 지적하며, 순간
성능만 재는 리뷰의 한계를 짚는다.

데스크톱은 방열판 면적과 케이스 공기 흐름의 여유가 커서 부스트 클럭을 훨씬 오래 유지한다.
즉 **10초 벤치마크에서는 비슷해 보여도, 몇 시간 돌리는 서버에서는 차이가 벌어진다.**

### (2) 전력과 지속성: 노트북에도 강점이 있다

그렇다고 노트북이 서버로 불리하기만 한 것은 아니다.

- **저전력 유휴(idle)**: 노트북은 배터리 구동을 전제로 설계돼 유휴 전력이 매우 낮다.
  24시간 켜두는 홈서버에서 전기요금과 발열 모두에 유리하다.
- **내장 UPS 효과**: 노트북에는 배터리가 붙어 있다. 순간 정전이나 전압 변동에도 꺼지지
  않는다. 데스크톱은 같은 안정성을 얻으려면 별도 UPS를 사야 한다. 조용하고 작은 상시
  서비스(홈 자동화, 소규모 웹/DB, 모니터링)라면 노트북이 오히려 실용적이다.

### (3) 확장성: 데스크톱의 압도적 우위

데스크톱은 RAM 슬롯, PCIe 레인, 드라이브 베이가 넉넉하다. 램 증설, 10GbE NIC나 GPU
추가, 디스크 여러 개로 RAID 구성 — 전부 데스크톱에서 자연스럽다. 노트북은 대개 RAM이
온보드로 납땜돼 증설이 불가하고, 확장은 USB/Thunderbolt 외장에 의존한다.

### (4) 신뢰성 메모리(ECC): 24/7 서버에서 갈리는 부분

일반 소비자 PC와 노트북이 서버·워크스테이션과 구조적으로 다른 지점이 **ECC 메모리**다.
ECC(Error Correction Code)는 64비트당 8비트의 정정 코드를 붙여 **1비트 오류는 정정하고
2비트 오류는 검출**하는 SECDED 방식으로 동작한다
([Kingston 기술 설명](https://www.kingston.com/en/blog/servers-and-data-centers/what-is-ecc-memory-ssd-enterprise),
벤더 자료).

이게 왜 중요한가? 대규모 데이터센터를 분석한
[공개 연구](https://arxiv.org/pdf/1901.03401)(Meza 외, *Large Scale Studies of Memory,
Storage, and Network Failures in a Modern Data Center*)는 DRAM 오류가 현대 서버 오류의
중요한 원인임을 실측으로 보여준다. 며칠씩 켜두는 서버에서는 우주선(cosmic ray)이나 노후로
인한 비트 뒤집힘이 누적되는데, ECC가 없으면 이런 오류가 **조용히** 데이터를 오염시키거나
커널 패닉을 일으킨다. 대부분의 소비자용 데스크톱·노트북은 ECC를 지원하지 않는다.

### PC vs 노트북 요약

| 항목 | 데스크톱 PC | 노트북 |
|---|---|---|
| 지속 부하 성능 | 우위 (오래 유지) | 발열로 throttling 쉬움 |
| 유휴 전력 | 상대적으로 높음 | 매우 낮음 (유리) |
| 정전 대비 | 별도 UPS 필요 | 내장 배터리 = UPS |
| 확장성(RAM·PCIe·디스크) | 우위 | 제한적 |
| ECC 메모리 | 워크스테이션급에서 가능 | 대부분 불가 |
| 유선 NIC | 기본 탑재 | 무선 위주, 유선은 어댑터 |

**결론:** 지속적인 CPU/GPU 부하나 확장이 필요하면 데스크톱. 조용하고 저전력인 상시
경량 서비스라면 내장 UPS까지 덤으로 얻는 노트북도 충분히 좋은 선택이다.

---

## 2. 유선 vs 무선 — 매체의 근본 차이

노트북을 서버로 쓸 때 자연스럽게 부딪히는 문제가 **네트워크**다. 요즘 노트북은 유선 포트가
없는 경우가 많아 무선으로 붙이게 되는데, 서버 역할에서 유선과 무선의 차이는 "속도 숫자"
이상이다.

### (1) 전이중 vs 반이중 — 여기서 거의 모든 게 갈린다

- **이더넷(IEEE 802.3)**: 스위치에 연결된 현대 이더넷은 **전이중(full-duplex)** 이다.
  별도의 선 쌍으로 송신과 수신을 **동시에** 하며, 충돌 자체가 없어 CSMA/CD가 비활성화된다
  ([이더넷 기술 요약, Emory Univ.](https://www.cs.emory.edu/~cheung/Courses/558/Syllabus/00/CSMA/00-Others/ethernet3.htm)).
- **Wi-Fi(IEEE 802.11)**: 무선은 하나의 채널을 여러 기기가 나눠 쓰는 **공유 매체**이고
  **반이중(half-duplex)** 이다. 라디오는 송신 중에는 수신할 수 없어 충돌을 "감지"할 수
  없으므로, 대신 **CSMA/CA**(회피)로 채널이 빌 때까지 기다렸다가 랜덤 백오프 후 전송한다.
  같은 순간 한 기기만 성공적으로 송신할 수 있다.

이 하나의 차이가 처리량·지연·안정성 전부에 파급된다.

### (2) 처리량: 표시 속도와 실효 속도는 다르다

Wi-Fi의 PHY(표시) 속도는 프레임 헤더·ACK·프레임 간 간격·랜덤 백오프 같은 오버헤드를 빼기
전 숫자다. 실제 TCP 처리량은 오버헤드와 채널 경쟁 때문에 **표시 속도의 대략 1/3~1/2**
수준으로 떨어진다. 학술 분석
([*Cross-layer Optimization for Next Generation Wi-Fi*](https://arxiv.org/pdf/1301.4691))은
MAC 효율(=실효 처리량÷PHY 속도)이 **PHY 속도가 올라갈수록 오히려 나빠진다**고 지적한다.
반면 스위치 이더넷은 전이중·전용 회선이라 회선 속도에 근접한 실효 처리량을 낸다.

### (3) 지연과 지터: 서버가 진짜 민감해하는 부분

서버는 평균 속도보다 **일관성**이 중요할 때가 많다. Wi-Fi는 채널 경쟁, 백오프, 재전송
때문에 지연이 크고 **변동(jitter)** 이 심하다. 옆집 공유기·전자레인지·거리·벽 같은 요인에
그때그때 흔들린다. 데이터베이스 복제나 클러스터 하트비트처럼 지연의 일관성이 중요한
워크로드에서 이 변동은 유선의 안정적인 sub-millisecond 지연보다 다루기 까다롭다.

### 유선 vs 무선 요약

| 항목 | 유선(이더넷) | 무선(Wi-Fi) |
|---|---|---|
| 통신 방식 | 전이중, 전용 회선 | 반이중, 공유 매체 |
| 매체 접근 | 충돌 없음 | CSMA/CA 경쟁·백오프 |
| 실효 처리량 | 회선 속도에 근접 | 표시 속도의 약 1/3~1/2 |
| 지연·지터 | 낮고 일관적 | 높고 변동 큼 |
| 서버 적합성 | 우선 권장 | 불가피할 때만 |

---

## 3. 그래서 어떻게 조합하나

- **하드웨어**: 확장·지속부하 위주면 데스크톱, 조용한 저전력 상시 서비스면 노트북(내장 UPS
  덤). 어느 쪽이든 24/7이면 ECC 지원 여부를 확인할 가치가 있다.
- **네트워크**: 서버 역할이라면 **가능한 한 유선**. 노트북에 포트가 없어도 USB/Thunderbolt
  이더넷 어댑터로 유선화하는 편이, 무선으로 붙이는 것보다 지연·안정성에서 거의 항상 낫다.
- **무선이 불가피하면**: 최신 규격(Wi-Fi 6/6E/7)과 좋은 AP 위치로 오버헤드·간섭을 최소화하되,
  지연에 민감한 워크로드는 애초에 그 노드에 두지 않는 설계가 안전하다.

정리하면, "PC냐 노트북이냐" 는 **발열·확장·전력**의 트레이드오프이고, "유선이냐 무선이냐" 는
**전이중이냐 반이중이냐** 라는 매체의 근본 차이다. 남는 장비로 서버를 꾸릴 때 이 두 축을
구분해서 보면, 무엇을 감수하고 무엇을 얻는지가 분명해진다.

---

## References

- Notebookcheck, *Opinion: It's time we talked about throttling in reviews* — <https://www.notebookcheck.net/Opinion-It-s-time-we-talked-about-throttling-in-reviews.234232.0.html>
- Kingston Technology, *What Is ECC in Memory and SSD?* (벤더 기술 설명) — <https://www.kingston.com/en/blog/servers-and-data-centers/what-is-ecc-memory-ssd-enterprise>
- Meza et al., *Large Scale Studies of Memory, Storage, and Network Failures in a Modern Data Center*, arXiv:1901.03401 — <https://arxiv.org/pdf/1901.03401>
- *Ethernet Technical Summary — Full/Half Duplex & CSMA*, Emory University — <https://www.cs.emory.edu/~cheung/Courses/558/Syllabus/00/CSMA/00-Others/ethernet3.htm>
- *Cross-layer Optimization for Next Generation Wi-Fi* (MAC efficiency vs PHY rate), arXiv:1301.4691 — <https://arxiv.org/pdf/1301.4691>
- IEEE 802.3 (Ethernet) / IEEE 802.11 (Wi-Fi) 표준 사양
