---
layout: post
title: "AWS SAA(Solutions Architect – Associate) 자격증: 시험 구조와 '선택지를 고르는 기준'으로 공부하기"
date: 2026-09-25 02:10:00 +0900
categories: [Cloud]
tags: [AWS, SAA-C03, Certification, Solutions Architect, Well-Architected, 자격증]
---

AWS Certified Solutions Architect – Associate(SAA)는 AWS 자격증 중 가장 많이 거론되는 시험이다. 이 글은 두 부분으로 나뉜다. 앞부분은 **AWS 공식 문서에서 확인한 시험 사실**이고, 뒷부분은 그 구조에 맞춘 **공부 전략**이다. 뒷부분은 필자의 의견이며, 의견이라고 따로 표시했다.

> 기준 시점: 2026-09-25. 시험 정보는 바뀔 수 있으니 응시 전에 [공식 자격증 페이지](https://aws.amazon.com/certification/certified-solutions-architect-associate/)를 다시 확인하자. AWS 는 "시험 가이드 개정은 실제 시험 반영 최소 한 달 전에 공개한다"고 밝히고 있다([Certification FAQ](https://aws.amazon.com/certification/faqs/)).

## TL;DR

| 항목 | 내용 |
|---|---|
| 현행 시험 코드 | **SAA-C03** (확인 시점 기준, 후속 버전 공지 없음) |
| 문항 / 시간 | 65 문항(채점 50 + 비채점 15), **130 분** |
| 합격선 | 100–1,000 척도 중 **720** |
| 응시료 | **150 USD** (원화 고시가 ₩197,287, 세금 별도) |
| 한국어 시험 | **가능** (시험 중 영어 원문 토글 가능) |
| 유효 기간 | **3 년** |
| 가장 비중 큰 도메인 | 보안 아키텍처 설계 **30%** |

---

## 1. 시험 구조 (공식 사실)

### 형식

[공식 시험 가이드](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html)에 따르면 다음과 같다.

- **65 문항** 가운데 **50 문항만 점수에 반영**된다. 나머지 **15 문항은 비채점 문항**이고 어느 문항인지 표시되지 않는다. 모든 문항을 똑같이 성실하게 풀어야 하는 이유다.
- 문항 형식은 두 가지다. **단일 선택**은 정답 1 개에 오답 3 개, **복수 선택**은 보기 5 개 이상 중 정답 2 개 이상이다.
- **안 푼 문항은 오답으로 처리되고, 찍어서 틀려도 감점은 없다.** 빈칸은 절대 남기지 않는다.
- 점수는 100–1,000 척도로 환산되고 **720 이상이면 합격**이다. 채점은 **보상형(compensatory)**이라 도메인별 과락 없이 총점만 넘기면 된다.
- 시험 시간은 **130 분**이다([자격증 페이지](https://aws.amazon.com/certification/certified-solutions-architect-associate/)).

참고로 AWS 공통 FAQ 에는 "합격 점수를 공개하지 않는다"는 문구가 있다. 하지만 SAA-C03 전용 시험 가이드는 720 을 명시하고 있으므로 이 글은 시험 가이드를 따랐다.

### 도메인과 비중

| 도메인 | 비중 | 태스크 |
|---|---|---|
| 1. 보안 아키텍처 설계 (Design Secure Architectures) | **30%** | 1.1 AWS 리소스에 대한 안전한 접근 설계 · 1.2 안전한 워크로드·애플리케이션 설계 · 1.3 적절한 데이터 보안 통제 결정 |
| 2. 복원력 있는 아키텍처 설계 (Resilient) | **26%** | 2.1 확장 가능하고 느슨하게 결합된 아키텍처 · 2.2 고가용성·내결함성 아키텍처 |
| 3. 고성능 아키텍처 설계 (High-Performing) | **24%** | 3.1 스토리지 · 3.2 컴퓨팅 · 3.3 데이터베이스 · 3.4 네트워크 · 3.5 데이터 수집·변환 |
| 4. 비용 최적화 아키텍처 설계 (Cost-Optimized) | **20%** | 4.1 스토리지 · 4.2 컴퓨팅 · 4.3 데이터베이스 · 4.4 네트워크 |

출처: 시험 가이드의 [Domain 1](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain1.html)~[Domain 4](https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03-domain4.html) 페이지.

도메인 3 과 4 는 스토리지·컴퓨팅·DB·네트워크라는 **같은 네 영역**을 한 번은 성능 관점에서, 한 번은 비용 관점에서 묻는다. 이 구조가 뒤에서 설명할 공부법의 핵심이다.

### 응시료·언어·응시 방식

- **응시료**는 150 USD 이고, [시험 정책 페이지](https://aws.amazon.com/certification/policies/before-testing/)의 원화 고시가는 ₩197,287 이다(세금 별도, 1 회 응시 기준). AWS 자격증을 하나 취득하면 **다음 시험 50% 할인** 바우처가 나온다.
- **응시 방식**은 Pearson VUE 시험장 또는 온라인 감독 시험 중에서 고른다. 다만 온라인 감독관 지원 언어에 **한국어는 없다**(영어·일본어·스페인어·중국어). 감독관과의 소통은 영어로 해야 한다는 뜻이다.
- **시험 언어**에는 **한국어가 포함**된다. 번역본으로 응시하면 시험 중에 문제를 **영어 원문으로 토글**해 볼 수 있다. 번역이 애매할 때 유용하다.
- **ESL +30**: 비영어권 응시자가 **영어로** 시험을 보면 30 분 연장을 신청할 수 있다. 한 번만 신청하면 이후 모든 응시에 적용되고, 시험 등록 **전에** 계정 페이지의 "Request Exam Accommodations"에서 신청한다([정책 페이지](https://aws.amazon.com/certification/policies/before-testing/)). 한국어 시험에 적용된다는 문구는 찾지 못했다.
- **재응시**는 불합격 후 **14 일**이 지나야 가능하다([FAQ](https://aws.amazon.com/certification/faqs/)).

### 권장 경력과 유효 기간

- 시험 가이드가 권장하는 경력은 **"AWS 서비스를 사용한 클라우드 솔루션 설계 실무 1 년 이상"**이다. 자격증 페이지는 IT 실무 경험이 전혀 없다면 Cloud Practitioner 부터 따는 게 도움이 된다고 안내하고, 이 시험이 "깊은 코딩 경험을 요구하지 않는다"고도 밝힌다.
- **유효 기간은 3 년**이다. 갱신 방법은 [재인증 페이지](https://aws.amazon.com/certification/recertification/) 기준으로 세 가지다.
  1. 최신 버전 SAA 재응시: 3 년 연장
  2. **Solutions Architect – Professional 취득**: SAA 가 자동 갱신되고 3 년 연장
  3. Skill Builder 유료 구독으로 유지 과정 이수: 1 년 연장, 만료 90 일 이내에만 가능

---

## 2. 무료 공식 자료

[AWS 자격증 준비 페이지](https://aws.amazon.com/certification/certification-prep/)는 다음 자료를 무료로 안내한다.

- **Official Practice Question Sets**: AWS 가 만든 20 문항 세트
- **Exam Prep 강좌**(무료 버전 약 2 시간)
- **AWS Cloud Quest**

실전 모의고사(Official Practice Exam)와 확장판 Exam Prep 은 Skill Builder 구독(개인 월 29 USD 부터)이 필요하다. SAA-C03 전용 4 단계 학습 플랜은 [자격증 페이지](https://aws.amazon.com/certification/certified-solutions-architect-associate/)에서 Skill Builder 로 연결된다.

**1 차 자료는 시험 가이드 자체다.** 각 태스크 아래의 "Knowledge of / Skills in" 목록이 곧 출제 범위다. 이 목록을 체크리스트로 만들어 두고 공부하는 것이 가장 효율적이다.

---

## 3. 공부 전략 (여기부터 필자 의견)

### 3-1. SAA 는 '서비스 암기'가 아니라 '선택 기준' 시험이다

SAA 문제는 대개 이런 모양이다. 상황 설명 → 제약 조건 하나(비용 최소, 운영 부담 최소, 가용성 최대, 지연 최소…) → 그럴듯한 보기 4 개. 보기는 모두 **작동은 하는** 아키텍처다. 차이는 **문제가 강조한 제약에 가장 잘 맞느냐**뿐이다.

그래서 문제를 읽을 때 가장 먼저 **제약 키워드**에 밑줄을 긋는다.

- "MOST cost-effective" → 도메인 4 관점
- "LEAST operational overhead" → 관리형·서버리스 쪽
- "highly available" / "fault tolerant" → Multi-AZ, 디커플링
- "lowest latency" → 캐시, 엣지, 리전 근접성

이 키워드는 [Well-Architected Framework 의 6 개 기둥](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html)(운영 우수성·보안·안정성·성능 효율성·비용 최적화·지속 가능성)과 대응된다. 시험 도메인 네 개가 이 중 보안·안정성·성능·비용 네 기둥과 거의 그대로 겹친다.

### 3-2. 자주 갈리는 판단 기준: 공식 문서로 확인한 것들

외워야 할 것은 서비스 목록이 아니라 **"A 와 B 중 언제 무엇을 고르나"**다. 대표적인 판단 기준을 공식 문서 근거와 함께 정리했다.

**RDS Multi-AZ vs 읽기 전용 복제본**
- Multi-AZ **DB 인스턴스** 배포의 대기 복제본은 **동기** 복제되고 **읽기 트래픽을 받지 않는다**. 목적은 가용성이다.
- 읽기 전용 복제본(Read Replica)은 **비동기** 복제되며 읽기 부하를 분산한다. 목적은 성능이다.
- Multi-AZ **DB 클러스터** 배포는 읽기 가능한 리더 인스턴스 2 개를 두고 **반동기** 복제한다.
- 근거: [Multi-AZ DB instance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html), [Read replicas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html), [Multi-AZ DB cluster](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html)
- 문제에 "장애 시 자동 전환"이 나오면 Multi-AZ, "읽기 성능"이 나오면 복제본 쪽이다.

**SQS 표준 vs FIFO**
- 표준 큐는 **최소 1 회 전달**과 **최선 노력 순서**를 제공한다. 중복 메시지가 올 수 있으니 소비자가 멱등해야 한다.
- FIFO 큐는 **정확히 1 회 처리**를 제공하고, 순서는 **메시지 그룹 단위**로 보장된다.
- 근거: [SQS 큐 유형](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-types.html)
- "느슨한 결합(decouple)"이 보이면 SQS, "순서·중복 금지"가 보이면 FIFO 다.

**VPC 게이트웨이 엔드포인트 vs 인터페이스 엔드포인트**
- S3·DynamoDB 용 **게이트웨이 엔드포인트는 추가 요금이 없다.**
- 인터페이스 엔드포인트(PrivateLink)는 AZ 별 시간당 요금과 GB 당 처리 요금이 붙는다.
- 근거: [Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html), [Interface endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html)
- "프라이빗 서브넷에서 S3 접근 + 비용 최소"라면 NAT 게이트웨이보다 게이트웨이 엔드포인트다.

**S3 스토리지 클래스**
- **Glacier Deep Archive** 는 AWS 에서 가장 저렴한 스토리지다. 표준 복원은 통상 **12 시간** 이내, 대량(Bulk) 복원은 48 시간 이내다.
- **Intelligent-Tiering** 은 객체당 소액의 모니터링 요금을 받고 접근 패턴에 따라 자동으로 계층을 옮긴다. 검색 요금은 없다. 단, **128 KB 미만 객체는 자동 계층화 대상이 아니다.**
- 근거: [Glacier storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/glacier-storage-classes.html), [Storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html)
- "접근 패턴을 모른다·변한다"면 Intelligent-Tiering, "규정상 수년 보관하고 거의 안 꺼낸다"면 Deep Archive 다.

**EC2 스팟 인스턴스**
- 스팟은 중단되기 **2 분 전**에 중단 알림을 받는다. 다만 알림은 최선 노력 기준이고, 중단 동작을 최대 절전(hibernate)으로 설정하면 2 분 경고가 없다.
- 근거: [Spot interruption notices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html)
- "중단돼도 되는 배치 작업 + 비용 최소"면 스팟, "중단 불가"면 온디맨드나 예약·Savings Plans 쪽이다.

### 3-3. 학습 순서 제안

1. **시험 가이드를 먼저 읽는다.** 태스크별 Knowledge/Skills 목록을 스프레드시트로 옮긴다.
2. **도메인 1(30%)부터 시작한다.** IAM(정책 평가, 역할, 교차 계정), KMS, VPC 보안(보안 그룹 vs NACL)이 기본이 되고, 이 내용이 나머지 도메인 문제에도 섞여 나온다.
3. **네 영역을 두 번 돌린다.** 스토리지·컴퓨팅·DB·네트워크를 한 번은 "가장 빠른 것", 한 번은 "가장 싼 것" 관점으로 정리한다. 도메인 3·4 의 구조가 그렇다.
4. **공식 무료 문제 세트 → 오답 노트**. 틀린 문제는 "어느 제약 키워드를 놓쳤나"로 기록한다. 해설을 읽고 넘어가지 말고 **해당 서비스의 공식 문서 문장**을 찾아 붙인다.
5. **직접 한 번씩 만들어 본다.** VPC 에 퍼블릭·프라이빗 서브넷, NAT, 게이트웨이 엔드포인트, ALB + Auto Scaling, RDS Multi-AZ 까지 한 번 구성해 보면 문제 지문이 그림으로 보이기 시작한다. 실습이 끝나면 **리소스를 반드시 삭제**한다. NAT 게이트웨이와 인터페이스 엔드포인트는 시간당 과금이다.

### 3-4. 시험장 팁

- 빈칸은 남기지 않는다. 감점이 없다.
- 복수 선택 문제는 **정답 개수가 지문에 명시**된다("Choose two"). 개수를 꼭 확인한다.
- 모르는 문제는 표시(flag)하고 넘어간다. 130 분에 65 문항이면 문항당 2 분 남짓이다.
- 한국어로 응시하더라도 **번역이 어색하면 영어 토글**로 원문을 확인한다. 서비스 이름과 제약 키워드는 원문이 더 정확하다.

---

## 마치며

SAA 는 "AWS 서비스를 몇 개나 아느냐"보다 **"제약이 주어졌을 때 무엇을 버리고 무엇을 고르는가"**를 묻는 시험이다. 그래서 합격하고 나서도 실무 설계 리뷰에서 그대로 쓰인다. 시험 가이드를 체크리스트로 삼고, 판단 기준마다 공식 문서 한 문장씩 근거를 달아 두면 시험 준비와 실무 역량이 같이 쌓인다.

---

## References

1. AWS, *AWS Certified Solutions Architect – Associate* (자격증 페이지). <https://aws.amazon.com/certification/certified-solutions-architect-associate/>
2. AWS, *AWS Certified Solutions Architect – Associate (SAA-C03) Exam Guide*. <https://docs.aws.amazon.com/aws-certification/latest/solutions-architect-associate-03/solutions-architect-associate-03.html>
3. AWS, *Before testing — exam policies (pricing, ESL +30, delivery)*. <https://aws.amazon.com/certification/policies/before-testing/>
4. AWS, *Recertification*. <https://aws.amazon.com/certification/recertification/>
5. AWS, *AWS Certification FAQs*. <https://aws.amazon.com/certification/faqs/>
6. AWS, *Certification Prep*. <https://aws.amazon.com/certification/certification-prep/>
7. AWS, *Well-Architected Framework — The pillars of the framework*. <https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html>
8. AWS, *Amazon RDS — Multi-AZ DB instance deployments*. <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html>
9. AWS, *Amazon RDS — Working with read replicas*. <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html>
10. AWS, *Amazon RDS — Multi-AZ DB cluster deployments*. <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/multi-az-db-clusters-concepts.html>
11. AWS, *Amazon SQS queue types*. <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-types.html>
12. AWS, *Gateway endpoints*. <https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html>
13. AWS, *Access AWS services through AWS PrivateLink (interface endpoints)*. <https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-access-aws-services.html>
14. AWS, *Amazon S3 Glacier storage classes*. <https://docs.aws.amazon.com/AmazonS3/latest/userguide/glacier-storage-classes.html>
15. AWS, *Amazon S3 storage classes*. <https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html>
16. AWS, *Spot Instance interruption notices*. <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html>
