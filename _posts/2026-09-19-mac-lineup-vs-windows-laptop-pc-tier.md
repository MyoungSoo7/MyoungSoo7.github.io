---
layout: post
title: "맥미니·맥북·맥프로·맥스튜디오를 윈도우 기준으로 줄 세우면 — 노트북급과 PC급의 경계"
date: 2026-09-19 03:55:30 +0900
categories: [hardware, apple]
tags: [mac, apple-silicon, windows, geekbench, laptop, desktop, workstation]
---

"맥미니, 맥북, 맥프로, 맥스튜디오 — 이게 노트북이야 PC야?" 라는 질문은 생각보다 답하기 까다롭다. 윈도우 세계에서는 이 구분이 비교적 선명하다. 그런데 그 선명함의 근거를 그대로 맥에 가져다 대면, 애플의 라인업은 그 경계선을 일부러 흐트러뜨리고 있다는 걸 알게 된다.

이 글은 그 경계를 **애플·인텔·AMD의 공식 사양과 중립적 제3자 벤치마크**만으로 정리한다. 검증되지 않은 집계 수치는 쓰지 않았고, 벤더 자체 주장에는 라벨을 붙였다. 가격은 지역·구성에 따라 달라지므로 다루지 않는다.

---

## 1. 윈도우에선 "노트북이냐 PC냐"를 **칩**이 가른다

윈도우 PC를 살 때 노트북과 데스크톱을 가르는 건 단순히 화면이 붙어 있느냐가 아니다. 근본적으로 **탑재되는 CPU 자체가 다른 부품**이다.

- 노트북용은 저전력 라인이다. 인텔은 Core Ultra의 H·U 시리즈, AMD는 Ryzen의 HX·HS·U 시리즈를 노트북에 넣는다.
- 데스크톱용은 소켓에 꽂는 별도 부품이다. 인텔 Core Ultra 285K, AMD Ryzen 9 9950X 같은 것들이고, 훨씬 높은 전력 예산과 지속 성능을 전제로 한다.

즉 윈도우에서 "노트북 CPU"와 "데스크톱 CPU"는 이름도, 소켓도, 전력 등급도 다른 서로 별개의 제품군이다. 그리고 데스크톱은 대개 PCIe 슬롯·메모리 슬롯을 통한 **확장성**을 더 갖는다. 이 세 축 — 전력 등급, 폼팩터, 확장성 — 이 윈도우식 "노트북 vs PC" 구분의 뼈대다.

## 2. 맥의 반전 — **같은 칩**이 노트북에도 데스크톱에도 들어간다

애플 실리콘은 이 뼈대를 정면으로 깬다. 하나의 칩이 노트북과 데스크톱을 넘나든다.

같은 M4 Max를 예로 들면, 이 칩은 노트북인 **MacBook Pro** 에도 들어가고 데스크톱인 **Mac Studio** 에도 들어간다.<sup>[[4]](#ref4)</sup><sup>[[5]](#ref5)</sup> 윈도우라면 노트북용 H 칩과 데스크톱용 K 칩으로 갈렸을 자리에, 애플은 **동일한 다이(die)** 를 그대로 쓴다. 아래는 전부 애플 공식 사양이다.

| 제품 | 폼팩터 | 탑재 칩(2024–2025) | 최대 통합 메모리 |
|---|---|---|---|
| MacBook Air (M4, 2025) | 노트북 | M4 | 32GB<sup>[[3]](#ref3)</sup> |
| MacBook Pro (2024) | 노트북 | M4 / M4 Pro / M4 Max | 128GB (M4 Max)<sup>[[4]](#ref4)</sup> |
| Mac mini (2024) | 소형 데스크톱 | M4 / M4 Pro | 64GB (M4 Pro)<sup>[[1]](#ref1)</sup> |
| Mac Studio (2025) | 데스크톱 | M4 Max / M3 Ultra | 512GB (M3 Ultra)<sup>[[5]](#ref5)</sup><sup>[[7]](#ref7)</sup> |
| Mac Pro (2023) | 타워·랙 워크스테이션 | M2 Ultra | 192GB<sup>[[8]](#ref8)</sup> |

핵심은 두 가지다.

- **M4·M4 Pro·M4 Max는 노트북에도 데스크톱에도 쓰인다.** M4는 MacBook Air·MacBook Pro·Mac mini에 공통으로 들어가고,<sup>[[1]](#ref1)</sup><sup>[[3]](#ref3)</sup><sup>[[4]](#ref4)</sup> M4 Max는 MacBook Pro와 Mac Studio에 공통으로 들어간다.<sup>[[4]](#ref4)</sup><sup>[[5]](#ref5)</sup> 윈도우식 "노트북 칩 vs 데스크톱 칩" 이분법이 여기선 성립하지 않는다.
- **Ultra 등급만 데스크톱 전용이다.** M3 Ultra는 두 개의 Max 다이를 UltraFusion으로 이어 붙인 칩이라 노트북에 들어가지 않고, Mac Studio에만 탑재된다.<sup>[[7]](#ref7)</sup> M2 Ultra 역시 데스크톱(Mac Pro) 전용이다.<sup>[[8]](#ref8)</sup>

## 3. 그래서 기준표는 이렇게 나온다

폼팩터와 확장성 기준으로 윈도우 세계에 대응시키면 이렇게 정리된다.

| 맥 제품 | 윈도우로 치면 | 성격 |
|---|---|---|
| MacBook Air / Pro | 노트북 | 노트북 그대로 |
| Mac mini | 미니PC·SFF 데스크톱 | 데스크톱 폼팩터에 **노트북급 칩** (M4/M4 Pro) |
| Mac Studio | 데스크톱 워크스테이션 | Max/Ultra 칩, 확장 슬롯은 없음 |
| Mac Pro | 타워·랙 워크스테이션 | 유일하게 **PCIe 확장** 보유 |

특히 **Mac mini** 가 흥미롭다. 높이 2인치(5cm)·가로세로 5인치(12.7cm)의 손바닥만 한 상자에<sup>[[1]](#ref1)</sup> MacBook Pro와 같은 계열의 M4/M4 Pro 칩이 들어간다. 윈도우로 치면 노트북 CPU를 넣은 미니PC(NUC 같은 부류)에 가장 가깝다 — 데스크톱 폼팩터이되 실리콘은 노트북 등급인 셈이다.

**Mac Pro** 는 반대편 끝이다. 타워형 기준 풀렁스 PCIe Gen 4 슬롯 6개(×16 두 개, ×8 네 개)와 하프렝스 슬롯 1개, 총 7개의 확장 슬롯을 갖는다.<sup>[[8]](#ref8)</sup> 이 PCIe 확장성은 다른 맥에는 없는, Mac Pro만의 남은 차별점이다.

## 4. 성능 실측 — 노트북에 들어가는 칩이 윈도우 데스크톱 플래그십을 넘어선 지점

여기서 가장 눈에 띄는 사실이 나온다. **노트북(MacBook Pro)에도 들어가는 M4 Max가, 윈도우 데스크톱 플래그십 CPU들을 Geekbench 6에서 앞선다.**

Tom's Hardware가 2024년 11월 공개한 Geekbench 6 비교표 기준이다.<sup>[[9]](#ref9)</sup>

| CPU | 등급 | GB6 싱글코어 | GB6 멀티코어 |
|---|---|---|---|
| Apple M4 Max | 맥 노트북·데스크톱 공용 | **4,060** | **26,675** |
| Intel Core Ultra 9 285K | 윈도우 데스크톱 | 3,422 | 22,954 |
| AMD Ryzen 9 9950X | 윈도우 데스크톱 | 3,434 | 21,399 |

싱글코어·멀티코어 모두 M4 Max가 두 윈도우 데스크톱 플래그십을 앞선다. "노트북에 들어가는 칩"이 소켓형 데스크톱 최상위 부품을 제친다는 건, 윈도우식 노트북/데스크톱 위계로는 잘 설명되지 않는 지점이다.

데스크톱 전용인 Ultra 등급은 멀티코어에서 한 단계 더 올라간다. AppleInsider가 Geekbench 결과로 보도한 수치는 다음과 같다.<sup>[[10]](#ref10)</sup>

| CPU | 제품(폼팩터) | GB6 싱글코어 | GB6 멀티코어 |
|---|---|---|---|
| Apple M3 Ultra | Mac Studio (데스크톱) | 3,221 | **27,749** |
| Apple M2 Ultra | Mac Pro (데스크톱) | 2,777 | 21,351 |

멀티코어 총량에서는 M3 Ultra가 가장 높지만, 싱글코어는 오히려 M4 Max가 위다. 세대(M4 vs M3)가 코어 수 총량을 이기는 경우다.

> **수치에 대한 주의.** 위 두 표는 서로 다른 출처의 서로 다른 측정 실행값이다(Tom's Hardware, AppleInsider). Geekbench 점수는 냉각·구성·측정 시점에 따라 흔들리는 집계값이므로 절대적 순위표로 읽지 말 것. 실제로 윈도우 노트북 CPU(예: Core Ultra 9 285H)의 Geekbench 6 집계치는 출처마다 싱글코어 2,600대~3,000대로 편차가 커서, 이 글에서는 하나의 확정 수치로 표기하지 않았다. Cinebench 등 다른 벤치마크도 신뢰할 1차 출처를 확정하지 못해 제외했다.

## 5. 그래서 어떻게 고를까 — 진짜 갈림길은 성능이 아니라 메모리와 확장성

Geekbench 한두 점 차이보다 결정을 실제로 바꾸는 건 두 축이다.

- **통합 메모리 상한.** M4 Max 노트북/스튜디오는 128GB,<sup>[[4]](#ref4)</sup><sup>[[5]](#ref5)</sup> M3 Ultra Mac Studio는 **최대 512GB** 까지 간다.<sup>[[7]](#ref7)</sup> 대용량 통합 메모리가 필요한 작업(대형 모델 로컬 구동 등)에서는 이 상한 자체가 다른 어떤 맥으로도 대체 불가능한 기준이 된다.
- **PCIe 확장.** 내부 카드 증설(캡처·네트워크·스토리지 등)이 필요하면 선택지는 사실상 Mac Pro 하나다.<sup>[[8]](#ref8)</sup> 다만 Mac Pro의 M2 Ultra는 2023년 6월 실리콘이라, 순수 CPU/GPU 성능만 보면 더 최신인 Mac Studio(M3 Ultra/M4 Max)에 밀린다. 즉 2026년 9월 현재 Mac Pro를 고를 이유는 성능이 아니라 **확장 슬롯** 이다.

정리하면, 윈도우식 "노트북이냐 PC냐" 라는 질문 자체가 맥에서는 반쯤 무력해진다. 맥북과 맥미니·맥스튜디오·맥프로는 상당 부분 **같은 계열의 칩**을 공유하고, 갈림길은 폼팩터·메모리 상한·확장성이라는 다른 축에서 생긴다. "노트북급 성능"이라는 표현이 무색하게, 노트북에 들어가는 M4 Max가 윈도우 데스크톱 최상위 CPU를 이미 넘어서 있기 때문이다.

*(참고: 2026년 9월 19일 현재 M3/M4 세대의 Mac Pro는 출시되지 않았다. Mac Pro는 여전히 2023년 M2 Ultra 상태다. 애플 공식 발표 기준.)*

---

## References

<a name="ref1">[1]</a> Apple, "Mac mini (2024) — 기술 사양." <https://support.apple.com/en-us/121555>

<a name="ref2">[2]</a> Apple Newsroom, "Apple's new Mac mini is more mighty, more mini," 2024-10-29. <https://www.apple.com/newsroom/2024/10/apples-new-mac-mini-is-more-mighty-more-mini-and-built-for-apple-intelligence/>

<a name="ref3">[3]</a> Apple, "MacBook Air (13-inch, M4, 2025) — 기술 사양." <https://support.apple.com/en-us/122209>

<a name="ref4">[4]</a> Apple, "MacBook Pro (14-inch, 2024) — 기술 사양 (M4 Pro/M4 Max)." <https://support.apple.com/en-us/121553>

<a name="ref5">[5]</a> Apple, "Mac Studio (2025) — 기술 사양." <https://support.apple.com/en-us/122211>

<a name="ref6">[6]</a> Apple Newsroom, "Apple unveils new Mac Studio, the most powerful Mac ever," 2025-03-05. <https://www.apple.com/newsroom/2025/03/apple-unveils-new-mac-studio-the-most-powerful-mac-ever/>

<a name="ref7">[7]</a> Apple Newsroom, "Apple reveals M3 Ultra, taking Apple silicon to a new extreme," 2025-03-05. <https://www.apple.com/newsroom/2025/03/apple-reveals-m3-ultra-taking-apple-silicon-to-a-new-extreme/>

<a name="ref8">[8]</a> Apple, "Mac Pro (2023) — 기술 사양." <https://support.apple.com/en-us/111343>

<a name="ref9">[9]</a> Tom's Hardware, "Apple's M4 Max is the single-core performance king in Geekbench 6," 2024-11-02. <https://www.tomshardware.com/pc-components/cpus/apples-m4-max-is-the-single-core-performance-king-in-geekbench-6-m4-max-beats-the-core-ultra-9-285k-and-ryzen-9-9950x>

<a name="ref10">[10]</a> AppleInsider, "First Mac Studio M3 Ultra benchmarks significantly outpace the M2 Ultra," 2025-03-07. <https://appleinsider.com/articles/25/03/07/first-mac-studio-m3-ultra-benchmarks-significantly-outpace-the-m2-ultra>
</content>
