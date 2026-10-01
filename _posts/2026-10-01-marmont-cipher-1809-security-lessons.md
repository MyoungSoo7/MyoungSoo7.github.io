---
layout: post
title: "217년 만에 풀린 마르몽 장군의 암호 편지 — 보안 엔지니어가 읽어야 할 일곱 가지 교훈"
date: 2026-10-01 22:29:50 +0900
categories: [Security, Cryptography]
tags: [암호학, 동음이자치환, 암호분석, 케르크호프스, 섀넌, 시뮬레이티드어닐링, AI, 양자내성암호, 재현성]
---

> 이 글은 AI(Claude)가 작성했습니다. Carter Church의 해독기를 제 말로 요약하고, 암호·보안 관점의 해설을 덧붙였습니다. 해독 결과와 과정에 대한 서술은 모두 **원저자의 주장**입니다. 해독문을 제3자가 다시 검증한 자료는 찾지 못했습니다. 다만 역사 암호 목록 사이트 Cryptiana가 이 편지를 '해독됨(Solved)'으로 옮겨 적어 두었습니다.

**원문:** Carter Church, 「The Letter to Marmont」 (2026-09-18) — <https://carter.church/writeups/the-letter-to-marmont/>

원문의 저작권은 원저자에게 있습니다. 아래는 번역이나 전재가 아니라 요약과 해설입니다. 판독표, 해독 전문, 검증 스크립트는 원문에서 확인해 주세요.

---

## 1. 무슨 일이 있었나

### 한 장짜리 도판만 남은 편지

나폴레옹 시대 프랑스군이 마르몽(Marmont) 장군에게 보낸 암호 편지가 있습니다. 미해독 역사 암호 목록에는 "Encoded Letter to Marshal Marmont (1807)"로 올라 있었습니다. 남은 것은 원본이 아니라 **도판 한 장**입니다. J. Vilcoq이 1969년 *Revue historique des Armées*에 쓴 논문 「Le Chiffre sous le Premier Empire」에 실린 그림이고, 지금은 Persée에서 디지털본으로 볼 수 있습니다([Persée](https://www.persee.fr/doc/rharm_0035-3299_1969_num_25_4_8686)).

도판의 첫 줄은 평문 프랑스어이고, 그 아래로 24줄의 암호가 이어집니다.

### 암호의 정체: 동음이자 치환(homophonic substitution)

원저자가 집계한 규모는 다음과 같습니다.

- 암호 단위 약 1,300개, 서로 다른 기호 155종
- 기호 하나가 **단어 하나**를 뜻하는 경우가 29종 (de, que, les, vous, général 등)
- 겹친 S(ss)를 뜻하는 기호 2종
- 아무 의미 없는 **널(null)** 기호와, 서기가 만들어 낸 듯한 표식 약 70종

출발점은 프랑스 암호학회(ARCSI)에 Daniel Tant이 정리해 둔 당대 암호표였습니다([ARCSI, Codes anciens n°373](https://www.arcsi.fr/doc/Tant/373.pdf)). 이 표로 문자 값 33개를 알 수 있었고, 이것만으로 전체 단위의 약 33%(435개)를 읽을 수 있었습니다. 나머지 약 67%는 **편지 자체에서** 값을 찾아내야 했습니다. 14번째 줄에는 "CONSEQUENT"라는 단어가 암호화되지 않은 채 끼어 있었습니다.

### 어떻게 풀었나

원저자에 따르면 GPT-6 Astra와 함께 약 6시간이 걸렸습니다. 과정은 다음과 같습니다.

1. **전사(transcription):** 도판을 줄 단위로 잘라 기호를 하나씩 받아 적었습니다. 임시 라벨 175개를 붙인 뒤, 같은 기호로 판명된 것들을 합쳤습니다.
2. **탐색:** 프랑스어 3·4·5-그램 통계를 점수로 삼아 **시뮬레이티드 어닐링**으로 키를 찾았습니다. 통계는 위고, 뒤마, 마르몽 회고록에서 뽑았습니다. 동음이자 치환을 이 방식으로 푸는 것은 학계에서 확립된 기법입니다([Kopal, HistoCrypt 2019](https://ep.liu.se/ecp/158/012/ecp19158012.pdf); Dhavare·Low·Stamp, *Cryptologia* 37(3), 2013).
3. **단어 기호 찾기:** 다른 부분은 그럴듯한 프랑스어인데 특정 기호에서만 문장이 깨진다면, 그 기호를 '단어 하나'로 가정하고 시험했습니다.
4. **도판 대조:** 제안된 값마다 그 기호가 나오는 **모든 자리**를 도판에서 다시 확인했습니다.
5. **강건성 검사:** 언어 모델에서 나폴레옹 시대 문헌을 모두 빼고 다시 돌렸는데도 같은 키가 나왔습니다. 모델이 역사를 '외워서' 맞춘 것이 아니라는 주장입니다.
6. **공개:** 키(key.tsv), 수정된 전사본, 검증·재현 스크립트를 묶은 zip을 SHA-256 해시와 함께 공개했습니다.

### 무엇이 적혀 있었나

원저자는 작성 시점을 **1809년 3월 말**로 고쳐 잡았습니다. 근거는 1809년 3월 16일 나폴레옹이 외젠 공에게 내린 명령입니다. 이 명령에는 내용을 "암호 편지로, 그리고 영리한 장교를 통해" 보내라는 지시가 있습니다. 실제로 해독문에 나온 7개 부대와 병력 수치가 그 명령과 같습니다.

흥미로운 대목은 "러시아군이 진군 중"이라는 문장입니다. 원저자는 이것이 **의도된 허위 정보**였다고 설명합니다. 나폴레옹이 3월 21일 이 소문을 신문에 퍼뜨리라고 지시했기 때문입니다. 또 출간된 나폴레옹 서한집에서 점선으로 비어 있던 대목이 해독문으로 채워졌다고 합니다.

Cryptiana의 미해독 암호 목록은 이 편지를 해독됨으로 옮기면서 "2026년 9월 20일 Carter Church가 해독을 알려 왔다"고 적었고, 연도도 1809년으로 고쳐야 한다고 덧붙였습니다([Cryptiana](http://cryptiana.web.fc2.com/code/unsolved.htm)).

원저자도 한계를 분명히 밝힙니다. **저해상도 도판 한 장을 한 가지로 읽은 결과**이고, 아직 값을 정하지 못한 기호가 5종 남아 있습니다.

---

## 2. 보안 엔지니어의 관점에서 — 일곱 가지 교훈

여기부터는 원문에 없는 제 해설입니다.

### 교훈 ① 동음이자 치환은 '확률적 암호화'의 조상이다

단순 치환 암호는 E가 늘 같은 기호로 바뀌기 때문에 빈도 분석에 무너집니다. 동음이자 치환은 자주 쓰는 글자에 **여러 기호를 배정**하고 그중 하나를 골라 씁니다. 같은 평문이 매번 다른 암호문이 되게 해서 빈도를 평평하게 만들려는 시도입니다.

현대 암호학은 이 직관을 정식으로 다듬었습니다. Goldwasser와 Micali는 **결정적(deterministic) 암호화로는 의미론적 안전성을 달성할 수 없고, 암호화에 무작위성이 필요하다**는 점을 보였습니다([Goldwasser & Micali, *Probabilistic Encryption*, JCSS 1984](https://doi.org/10.1016/0022-0000(84)90070-9)). 오늘날 AES-GCM에 매번 새로운 nonce를 쓰는 이유도 같은 계보입니다.

그런데 동음이자 치환은 왜 졌을까요? 무작위성이 **글자 단위에만** 있었기 때문입니다. 3·4·5-그램 같은 **문맥 통계는 그대로 남았습니다.** 시뮬레이티드 어닐링은 바로 그 문맥 통계를 점수로 씁니다. 현대 시스템에 옮기면, 개별 값을 암호화해도 **패턴(길이, 순서, 반복)** 이 남는다면 누출이라는 뜻입니다. 결정적 암호화된 DB 컬럼이나 검색 가능 암호화에서 빈도 분석 공격이 계속 연구되는 이유입니다.

### 교훈 ② 케르크호프스 원칙 — 암호표는 결국 샌다

케르크호프스는 1883년에 **"시스템은 비밀일 필요가 없어야 하며, 적의 손에 넘어가도 문제가 없어야 한다"** 는 원칙을 제시했습니다([Kerckhoffs, *La cryptographie militaire*, 1883](https://www.petitcolas.net/kerckhoffs/)).

이 사례에서 당대의 표(Tant이 정리한 ARCSI 문서)는 **시스템의 일부가 새어 나간 상태**와 같습니다. 그것만으로 3분의 1이 읽혔습니다. 코드북 방식의 문제는 시스템과 키가 한 몸이라는 점입니다. 코드북이 일부만 새도 키 일부가 새는 것과 같습니다. 현대 암호는 알고리즘을 공개하고 **비밀을 짧은 키 하나에 모읍니다.** 그래야 유출됐을 때 키만 교체하면 됩니다.

### 교훈 ③ 평문 섞기는 공격자에게 주는 선물이다

이 편지에는 첫 줄 평문과 본문 속 "CONSEQUENT"가 있었습니다. 둘 다 해독의 단서, 즉 **크립(crib)** 이 됩니다. 원문이 비교 사례로 드는 1811년 마르몽 코드도 같은 길을 걸었습니다. 영국의 조지 스코벨은 서기들이 섞어 쓴 평문 단어에 힘입어 이틀 만에 그 코드를 깼다고 원문은 전합니다.

현대에도 같은 실수가 반복됩니다.

- 본문은 암호화하면서 **제목, 파일명, 메타데이터는 평문**으로 두는 경우
- 고정 헤더나 예측 가능한 프로토콜 필드(=알려진 평문)
- TLS를 쓰지만 일부 리소스는 HTTP로 불러오는 혼합 콘텐츠

현대 블록 암호는 알려진 평문 공격에 안전하도록 설계되므로 크립 하나로 키가 깨지지는 않습니다. 하지만 **평문으로 둔 메타데이터는 그 자체로 정보**라는 점은 변하지 않습니다.

### 교훈 ④ 짧은 암호문은 '유일 해독 거리'의 문제다

섀넌은 1949년 논문에서 암호문이 충분히 길어지면 가능한 키가 하나로 좁혀지는 지점, 즉 **유일 해독 거리(unicity distance)** 개념을 제시했습니다([Shannon, *Communication Theory of Secrecy Systems*, 1949](https://doi.org/10.1002/j.1538-7305.1949.tb00928.x)). 동음이자 치환은 키 공간을 키워 이 거리를 늘리는 장치입니다.

1,300개 단위면 짧지 않지만, 155종 기호에 단어 기호와 널까지 섞인 시스템에서는 **해(解)가 하나인지** 자체가 쟁점이 됩니다. 원저자가 "한 가지 읽기"라고 조심스럽게 쓴 것도 이 맥락에서 이해할 수 있습니다. 이 암호의 정확한 유일 해독 거리를 계산한 자료는 찾지 못했으므로 수치는 적지 않습니다.

### 교훈 ⑤ 기밀성은 진실성이 아니다

해독문 속 "러시아군 진군"은 사실이 아니라 **의도적 허위 정보**였습니다. 암호화된 채널로 왔다고 해서 내용이 참이라는 보장은 없습니다.

현대 보안의 언어로 바꾸면 이렇습니다.

- **기밀성(confidentiality):** 남이 못 읽는다
- **무결성·인증(integrity / authenticity):** 중간에 바뀌지 않았고, 말한 사람이 그 사람이다
- **진실성:** 말한 사람이 사실을 말했다 — **어떤 암호 기술로도 보장되지 않음**

그래서 현대 프로토콜은 암호화와 인증을 묶은 AEAD를 기본으로 씁니다. 하지만 AEAD도 "보낸 사람이 맞다"까지만 보장합니다. 위협 모델에 **내부자나 정당한 발신자가 거짓을 말하는 경우**가 있다면, 그것은 암호가 아니라 검증 절차와 교차 확인으로 다뤄야 합니다. LLM 에이전트가 '신뢰된 채널'로 들어온 문서를 지시로 착각하는 프롬프트 인젝션도 같은 구조의 문제입니다.

### 교훈 ⑥ '공격 비용'이라는 가정은 무너진다

1809년의 암호는 "적이 이걸 풀 시간과 인력이 없다"는 가정 위에 서 있었습니다. 217년 동안은 그 가정이 맞았습니다. 그런데 원저자의 보고대로라면 이번에는 AI와 함께 **반나절**이 걸렸습니다. 같은 모델이 1941년 독일군 무선 메시지를 풀었다는 보도도 있습니다([The Decoder](https://the-decoder.com/openais-gpt-6-astra-decrypts-a-nazi-radio-message-in-ten-hours-that-went-unsolved-for-83-years/)).

이 사례들은 역사 암호이고, AES 같은 현대 암호가 AI로 깨진다는 증거는 **아닙니다.** 하지만 교훈은 분명합니다. **"아무도 이걸 들여다볼 수고를 하지 않을 것"** 이라는 가정은 보안 근거가 될 수 없습니다. 난독화, 비공개 프로토콜, 사람이 손으로 하기 귀찮은 작업에 기댄 보안이 모두 여기에 해당합니다.

같은 논리가 **"지금 수집하고 나중에 해독한다(harvest now, decrypt later)"** 위협에도 적용됩니다. 오늘 안전한 암호문도 수십 년 뒤의 계산 능력 앞에 놓입니다. NIST가 2024년 8월 13일 양자내성암호 표준 FIPS 203·204·205를 확정한 것도 이 때문입니다([NIST CSRC](https://csrc.nist.gov/news/2024/postquantum-cryptography-fips-approved)). 오래 비밀이어야 하는 데이터일수록 지금 전환 계획을 세워야 합니다.

### 교훈 ⑦ 재현 가능성은 보안 관행이다

이 해독기에서 가장 좋은 부분은 결과를 **검증 가능한 형태로 공개**했다는 점입니다.

| 원저자의 조치 | 보안 분야의 대응 관행 |
|---|---|
| 키 파일 + 검증 스크립트 공개 | 공격 재현 PoC, 테스트 벡터 |
| 배포물 SHA-256 해시 공개 | 아티팩트 무결성 확인, 서명된 릴리스 |
| 역사 문헌을 뺀 모델로 재실행 | 데이터 누수(leakage) 통제, 대조군 실험 |
| 미해결 기호 5종을 숨기지 않음 | 한계와 잔여 위험의 명시 |

특히 세 번째가 중요합니다. AI가 답을 맞혔을 때 "추론한 것인가, 학습 데이터에서 본 것인가"는 언제나 의심해야 합니다. 원저자는 그 의심을 실험으로 배제하려 했습니다. AI로 보안 분석을 할 때도 같은 기준이 필요합니다. **"AI가 찾았다"는 근거가 아니고, 재현 가능한 절차가 근거입니다.**

---

## 3. 읽을 때 주의할 점

- 해독문, 1809년 재연대, 허위 정보 해석은 모두 **원저자 한 사람의 분석**입니다. 독립된 재검증은 아직 확인되지 않았습니다. Cryptiana의 등재는 "해독을 알려 왔다"는 기록이지 내용 검증은 아닙니다.
- 6시간, 33%, 155종 같은 수치도 원저자의 보고입니다.
- AI가 역사 암호를 풀었다는 사례를 **현대 암호의 취약성**으로 확대 해석하면 안 됩니다. 두 암호는 설계 원리부터 다릅니다.

## References

1. Carter Church, "The Letter to Marmont", 2026-09-18. <https://carter.church/writeups/the-letter-to-marmont/> — 해독 과정·결과·수치의 출처(원저자 주장)
2. J. Vilcoq, "Le Chiffre sous le Premier Empire", *Revue historique des Armées* 25(4), 1969. <https://www.persee.fr/doc/rharm_0035-3299_1969_num_25_4_8686>
3. Daniel Tant, ARCSI *Codes anciens* n°373. <https://www.arcsi.fr/doc/Tant/373.pdf>
4. Cryptiana, "Unsolved Codes and Ciphers". <http://cryptiana.web.fc2.com/code/unsolved.htm>
5. G. Kopal, "Cryptanalysis of Homophonic Substitution Ciphers Using Simulated Annealing with Fixed Temperature", *HistoCrypt 2019*, pp. 107–116. <https://ep.liu.se/ecp/158/012/ecp19158012.pdf>
6. A. Dhavare, R. M. Low, M. Stamp, "Efficient Cryptanalysis of Homophonic Substitution Ciphers", *Cryptologia* 37(3), 2013, pp. 250–281.
7. A. Kerckhoffs, "La cryptographie militaire", *Journal des sciences militaires*, 1883. <https://www.petitcolas.net/kerckhoffs/>
8. C. E. Shannon, "Communication Theory of Secrecy Systems", *Bell System Technical Journal* 28(4), 1949. <https://doi.org/10.1002/j.1538-7305.1949.tb00928.x>
9. S. Goldwasser, S. Micali, "Probabilistic Encryption", *Journal of Computer and System Sciences* 28(2), 1984. <https://doi.org/10.1016/0022-0000(84)90070-9>
10. NIST CSRC, "Post-Quantum Cryptography FIPS Approved", 2024-08-13. <https://csrc.nist.gov/news/2024/postquantum-cryptography-fips-approved>
11. The Decoder, "OpenAI's GPT-6 Astra decrypts a Nazi radio message…". <https://the-decoder.com/openais-gpt-6-astra-decrypts-a-nazi-radio-message-in-ten-hours-that-went-unsolved-for-83-years/>
