---
layout: post
title: "AWS 3계층 인프라 설계서 — 가상의 예약 서비스로 쓰는 '왜 이 사양인가'"
date: 2026-10-26 08:13:42 +0900
categories: [Cloud, AWS]
tags: [aws, vpc, ec2, rds, alb, acm, route53, security-group, architecture, capacity-planning]
---

인프라 과제의 요구 항목은 대개 이렇게 생겼다.

- AWS 인프라 구성 설계
- 서버 사양 선정과 선정 근거
- WEB / AP / DB 서버 구축
- 네트워크·보안 구성
- HTTPS·도메인 구성
- 그리고 각 항목에 **설계 이유와 근거**를 덧붙일 것

이 글은 **가상의 목표**를 하나 세우고, 위 항목을 순서대로 채운 설계서다. 핵심은 마지막 줄이다. 구성도는 누구나 비슷하게 그린다. 차이는 "왜 이 사양인지", "왜 이 방식인지" 를 **목표에서 거꾸로 끌어낼 수 있느냐**에서 난다.

> 이 글의 서비스·트래픽 수치는 모두 설명을 위해 만든 **가상값**이다. 인스턴스 사양 같은 AWS 수치만 공식 문서에서 확인한 사실이다.

---

## 0. 가상의 목표 — 모든 근거의 출발점

| 항목 | 가정 |
| --- | --- |
| 서비스 | 동네 병원 진료 예약 웹 서비스 (조회·예약·취소) |
| 사용자 | 일 활성 사용자 5,000명 |
| 피크 | 오전 9시 접수 오픈 직후, 초당 요청 100건 |
| 평균 응답 | AP 처리 기준 0.1초 |
| 가용성 목표 | 서버 한 대 또는 가용 영역(AZ) 하나가 죽어도 예약은 계속 받는다 |
| 데이터 | 예약·환자 연락처 등 개인정보 포함 → 외부 노출 금지 |
| 운영 인력 | 1명. 사람이 손으로 하는 일(인증서 갱신, 서버 접속 키 관리)을 최소화한다 |
| 리전 | 서울(ap-northeast-2), AZ 2개 사용 |

설계 원칙은 AWS Well-Architected Framework 의 여섯 축을 따른다[^wa]. 운영 우수성, 보안, 안정성, 성능 효율성, 비용 최적화, 지속 가능성이다. 이 글의 모든 선택은 **위 표의 어느 한 줄**로 거슬러 올라간다.

---

## 1. 전체 구성

```
                 사용자
                   │  https://booking.example.com
              Route 53 (Alias)
                   │
        ┌──────────┴──────────┐   ← 퍼블릭 서브넷 (AZ-a, AZ-c)
        │  외부 ALB (TLS 종료)  │      ACM 인증서
        └──────────┬──────────┘
          ┌────────┴────────┐       ← 프라이빗 앱 서브넷
       WEB-a              WEB-c        nginx (정적 파일 + 리버스 프록시)
          └────────┬────────┘
        ┌──────────┴──────────┐
        │   내부 ALB (AP 앞)   │
        └──────────┬──────────┘
          ┌────────┴────────┐
        AP-a               AP-c        Spring Boot
          └────────┬────────┘
        ┌──────────┴──────────┐   ← 프라이빗 DB 서브넷
        │ RDS PostgreSQL       │      Multi-AZ (주 a / 대기 c)
        └─────────────────────┘
  아웃바운드: 프라이빗 → NAT 게이트웨이 → 인터넷
  S3 접근:   Gateway 엔드포인트 (NAT 우회)
```

**3계층을 다른 서브넷에 두는 이유**는 한 가지다. 바깥에서 닿을 수 있는 건 외부 ALB 하나뿐이어야 하기 때문이다. WEB·AP·DB 는 공인 IP 가 없고, 바로 앞 계층에서 오는 트래픽만 받는다.

---

## 2. 서버 사양 선정과 근거

### 2-1. 필요한 동시 처리량부터 계산한다

사양을 고르기 전에 **동시에 몇 건을 처리해야 하는지**부터 정한다. 리틀의 법칙을 쓰면 된다[^little].

$$
L = \lambda W
$$

여기서 $\lambda$ 는 초당 도착 요청 수, $W$ 는 요청 하나가 시스템에 머무는 시간, $L$ 은 평균 동시 처리 건수다. 가정값을 넣으면 이렇다.

$$
L = 100\ \text{req/s} \times 0.1\ \text{s} = 10
$$

즉 피크에도 AP 전체가 동시에 들고 있는 요청은 **평균 10건**이다. 여기에 순간 몰림과 느린 쿼리를 감안해 여유를 5배 두고, **AP 전체에서 동시 50건**을 설계값으로 잡는다. 두 대로 나누면 대당 25건이다.

이 숫자가 사양을 정한다. 톰캣 스레드 25~50개와 DB 커넥션 풀 10~20개면 충분하다. **CPU 를 많이 쓰는 작업이 아니라 I/O 대기가 대부분인 서비스**라는 뜻이기도 하다.

### 2-2. 선정 결과

| 계층 | 인스턴스 | vCPU / 메모리 | 대수 | 근거 |
| --- | --- | --- | --- | --- |
| WEB | `t4g.small` | 2 / 2 GiB | 2 (AZ별 1) | nginx 는 메모리를 수십 MB 만 쓴다. 이중화가 목적이지 성능이 목적이 아니다 |
| AP | `t4g.medium` | 2 / 4 GiB | 2 (AZ별 1) | JVM 힙 2 GiB + 메타스페이스·스레드 스택·OS 여유 |
| DB | `db.t4g.medium` (RDS) | 2 / 4 GiB | Multi-AZ 1쌍 | 예약 데이터는 작아 수 GB 수준. 커넥션 40개(AP 2대 × 20)를 감당 |
| 디스크 | gp3 | 기본 3,000 IOPS / 125 MiB/s | — | 기본 성능으로 충분, 필요하면 용량과 따로 올릴 수 있다 |

메모리 수치는 AWS 범용 인스턴스 사양표에서 확인했다[^ec2gp]. gp3 기본 성능도 EBS 문서 기준이다[^gp3].

**왜 Graviton(`g` 계열)인가.** Java·nginx·PostgreSQL 은 모두 ARM64 를 공식 지원한다. 그래서 아키텍처를 바꿀 비용이 거의 없다. AWS 는 같은 성능에서 x86 보다 가격 대비 성능이 좋다고 밝히는데[^t4g], 이건 **벤더의 주장**이다. 그러니 실제 도입 전에 우리 워크로드로 직접 부하 테스트를 돌려 확인하는 것을 전제로 한다.

**왜 버스터블(`t` 계열)인가, 그리고 그 함정.** 예약 서비스는 하루 중 오전 피크 한두 시간에 부하가 몰리고 나머지는 한가하다. 버스터블 인스턴스는 한가할 때 CPU 크레딧을 모아 두었다가 피크에 쓴다[^burst]. 이런 패턴에 맞는다.

다만 크레딧이 바닥나면 CPU 가 기준선으로 묶인다. 그래서 두 가지를 같이 건다.

- **CloudWatch 경보:** `CPUCreditBalance` 가 낮아지면 알림을 보낸다.
- **unlimited 모드:** 크레딧이 바닥나도 추가 요금을 내고 성능을 유지한다.

평균 CPU 가 기준선을 계속 넘는다면 그건 버스터블에 맞지 않는 워크로드라는 신호다. 그때는 `m7g.large`(2 vCPU / 8 GiB)[^m7g] 같은 고정 성능 인스턴스로 옮긴다. **이 전환 기준을 미리 적어 두는 것까지가 사양 선정이다.**

**왜 처음부터 크게 잡지 않는가.** 클라우드에서는 인스턴스 타입을 나중에 바꿀 수 있다. 그래서 "모자라면 어떻게 아는가(경보)" 와 "모자라면 무엇으로 바꾸는가(전환 기준)" 를 정해 두는 쪽이, 처음부터 크게 사는 것보다 비용 최적화 원칙에 맞는다[^wa].

---

## 3. WEB / AP / DB 서버 구축

### 3-1. WEB — nginx

- **역할:** 정적 파일(JS·CSS·이미지) 서빙, `/api/*` 요청을 내부 ALB 로 넘기기, 요청 크기 제한
- **WEB 계층을 따로 두는 이유:** 정적 파일을 AP 의 JVM 이 서빙하지 않게 한다. 그리고 AP 를 배포할 때 사용자 앞단이 흔들리지 않게 한다.
- **대안:** 정적 파일만 있다면 S3 + CloudFront 가 운영 부담이 더 적다. 이 과제는 WEB 서버 구축이 요구 항목이라 EC2 로 두었지만, 실무라면 1순위 검토 대상이다.

### 3-2. AP — Spring Boot

- **WEB 와 AP 사이에 내부 ALB 를 두는 이유:** nginx 에 AP 주소를 직접 적으면 AP 가 교체될 때마다 설정을 고쳐야 한다. 내부 ALB 는 헬스체크로 죽은 AP 를 자동으로 뺀다[^alb].
- **JVM 설정:** `-Xmx2g`. 나머지 2 GiB 는 힙 밖 메모리와 OS 몫으로 남긴다.
- **설정과 비밀값:** DB 비밀번호 같은 값은 AMI 나 코드에 넣지 않는다. Secrets Manager 나 Parameter Store 에서 읽는다.
- **배포:** Auto Scaling 그룹에 최소 2대·최대 4대를 둔다. 인스턴스가 죽으면 같은 AZ 에 자동으로 다시 만든다.

### 3-3. DB — RDS PostgreSQL Multi-AZ

- **DB 를 EC2 에 직접 설치하지 않는 이유:** 운영 인력이 1명이라는 가정 때문이다. 백업, 패치, 장애 조치를 사람이 직접 하지 않는 것이 목표다.
- **Multi-AZ:** 다른 AZ 에 동기 복제되는 대기 인스턴스를 둔다. 주 인스턴스가 있는 AZ 가 죽으면 대기 쪽으로 자동 전환된다. 이때 DNS 이름(엔드포인트)은 그대로라서 애플리케이션 설정을 바꿀 필요가 없다[^rdsmaz].
- **대기 인스턴스는 읽기를 받지 않는다.** 읽기 부하 분산은 Multi-AZ 의 역할이 아니다. 읽기 부하가 생기면 읽기 전용 복제본을 따로 붙인다.
- **기타:** 자동 백업과 시점 복구(PITR)를 켠다. 스토리지 암호화(KMS)를 켠다. 퍼블릭 액세스는 끈다.

---

## 4. 네트워크와 보안

### 4-1. VPC 와 서브넷

| 서브넷 | AZ-a | AZ-c | 들어가는 것 |
| --- | --- | --- | --- |
| 퍼블릭 | 10.0.0.0/24 | 10.0.1.0/24 | 외부 ALB, NAT 게이트웨이 |
| 앱 (프라이빗) | 10.0.10.0/24 | 10.0.11.0/24 | WEB, 내부 ALB, AP |
| DB (프라이빗) | 10.0.20.0/24 | 10.0.21.0/24 | RDS |

- **아웃바운드:** 프라이빗 서브넷은 NAT 게이트웨이를 통해서만 인터넷으로 나간다(패키지 설치, 외부 API 호출)[^nat]. 바깥에서 먼저 연결을 걸어 들어올 수는 없다.
- **NAT 를 AZ 마다 둘지:** 가용성 목표("AZ 하나가 죽어도 계속")를 지키려면 AZ 마다 하나씩 둔다. 한 개만 두면 비용은 줄지만, 그 AZ 가 죽을 때 다른 AZ 의 아웃바운드도 같이 끊긴다. **이건 비용과 가용성의 교환이고, 목표 표에 따라 정한다.**
- **S3 접근:** Gateway 엔드포인트로 보낸다[^gwep]. 그러면 S3 트래픽이 NAT 를 타지 않아 NAT 처리 비용이 붙지 않는다.

### 4-2. 보안 그룹 체인 — IP 가 아니라 "누가 보냈나" 로 허용

| 보안 그룹 | 인바운드 허용 |
| --- | --- |
| `sg-alb-ext` | 0.0.0.0/0 → 443, 80 (80 은 443 리다이렉트용) |
| `sg-web` | `sg-alb-ext` 에서 오는 80 만 |
| `sg-alb-int` | `sg-web` 에서 오는 80 만 |
| `sg-ap` | `sg-alb-int` 에서 오는 8080 만 |
| `sg-db` | `sg-ap` 에서 오는 5432 만 |

보안 그룹은 출발지로 **다른 보안 그룹**을 지정할 수 있다[^sg]. 그래서 AP 가 오토스케일링으로 늘어나 IP 가 바뀌어도 규칙을 고칠 필요가 없다.

DB 에 닿을 수 있는 경로는 **AP 를 거치는 것 하나뿐**이다. "개인정보를 외부에 노출하지 않는다" 는 목표를 네트워크 구조로 강제하는 셈이다.

네트워크 ACL 은 서브넷 단위의 상태 비저장(stateless) 방화벽이다[^nacl]. 기본값(전체 허용)으로 두고, 접근 통제는 보안 그룹 한 곳에서 한다. 규칙을 두 군데 나눠 두면 장애 때 원인 찾는 시간이 길어지기 때문이다. 특정 IP 대역을 통째로 막아야 할 때만 ACL 을 쓴다.

### 4-3. 서버 접속 — SSH 키도 배스천 호스트도 없다

- **22번 포트는 어디에도 열지 않는다.** 서버 접속은 Systems Manager Session Manager 로 한다[^ssm]. 접속 권한은 IAM 으로 관리하고 세션은 기록으로 남는다. 잃어버릴 SSH 키도, 패치해야 할 배스천 호스트도 없다. **운영 인력 1명이라는 가정에 직접 대응하는 선택이다.**
- **IMDSv2 필수:** 인스턴스 메타데이터 서비스는 v2(토큰 방식)만 허용한다[^imds]. SSRF 취약점이 있어도 인스턴스 자격 증명을 빼가기 어렵게 만든다.
- **최소 권한:** AP 의 IAM 역할에는 필요한 Secrets Manager 경로와 S3 버킷 읽기만 준다.

---

## 5. HTTPS 와 도메인

1. **도메인:** Route 53 에 호스팅 영역 `example.com` 을 만든다.
2. **인증서:** ACM 에서 `booking.example.com` 공인 인증서를 **DNS 검증**으로 발급받는다. 검증용 CNAME 레코드를 남겨 두면 ACM 이 만료 전에 자동으로 갱신한다[^acmdns][^acm]. 사람이 손으로 갱신하는 일은 없다.
3. **TLS 종료:** 외부 ALB 의 443 리스너에 인증서를 붙인다. 보안 정책은 TLS 1.3 을 지원하는 `ELBSecurityPolicy-TLS13-1-2-2021-06` 으로 한다[^albtls].
4. **HTTP 리다이렉트:** 80 리스너는 301 로 443 으로 보낸다.
5. **레코드:** `booking.example.com` 을 ALB 로 가리키는 **Alias A 레코드**를 만든다[^r53alias]. CNAME 과 달리 Alias 는 도메인 최상위(apex)에도 쓸 수 있고, ALB 의 IP 가 바뀌어도 따라간다.

**TLS 를 ALB 에서 끝내는 이유:** 인증서를 한 곳에서만 관리하면 된다. 그리고 WEB·AP 에서 TLS 처리 부담이 빠진다.

대신 **ALB 뒤 VPC 내부 구간은 평문 HTTP 다.** 규정상 전 구간 암호화가 필요하면, ALB 에서 WEB·AP 로 가는 구간에도 TLS 를 건다(대상 그룹을 HTTPS 로). 이건 요구사항에 따라 결정할 항목으로 남긴다.

---

## 6. 목표 → 설계 추적표

과제가 요구한 "설계 이유와 근거" 를 한 장으로 모으면 이렇다.

| 목표 (0절) | 이 목표 때문에 한 선택 |
| --- | --- |
| AZ 하나가 죽어도 예약 계속 | 전 계층 2개 AZ, RDS Multi-AZ, AZ 별 NAT, ALB 헬스체크 |
| 피크 초당 100건 | 리틀의 법칙으로 동시 50건 설계 → AP 2대 × 스레드 25 |
| 개인정보 외부 노출 금지 | 프라이빗 서브넷, 보안 그룹 체인, RDS 퍼블릭 액세스 끔, 암호화 |
| 운영 인력 1명 | RDS 관리형, ACM 자동 갱신, Session Manager, Auto Scaling 자동 교체 |
| 비용 | Graviton + 버스터블, S3 Gateway 엔드포인트, 크레딧 경보 기반 증설 |

---

## 한계

- **트래픽 수치는 전부 가정이다.** 실제 설계에서는 부하 테스트로 $W$(응답 시간)를 직접 측정해 리틀의 법칙에 다시 넣어야 한다.
- **Graviton 의 가격 대비 성능 우위는 AWS 가 밝힌 수치다.** 중립적인 제3자 비교는 이 글에서 확인하지 못했다.
- **비용은 리전과 시점에 따라 달라진다.** 그래서 금액은 적지 않았다. AWS Pricing Calculator 로 따로 산출해야 한다.

---

## References

[^wa]: AWS, "AWS Well-Architected Framework". <https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html>
[^little]: J. D. C. Little, "A Proof for the Queuing Formula: L = λW", *Operations Research* 9(3):383–387, 1961. doi:10.1287/opre.9.3.383
[^ec2gp]: AWS, "Specifications for Amazon EC2 general purpose instances". <https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html>
[^gp3]: AWS, "Amazon EBS General Purpose SSD volumes" (gp3 baseline 3,000 IOPS / 125 MiB/s). <https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html>
[^t4g]: AWS, "Amazon EC2 T4g Instances" (벤더 주장). <https://aws.amazon.com/ec2/instance-types/t4/>
[^burst]: AWS, "Burstable performance instances". <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html>
[^m7g]: AWS, "Amazon EC2 M7g Instances". <https://aws.amazon.com/ec2/instance-types/m7g/>
[^alb]: AWS, "What is an Application Load Balancer?". <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html>
[^rdsmaz]: AWS, "Multi-AZ DB instance deployments for Amazon RDS". <https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html>
[^nat]: AWS, "NAT gateways". <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html>
[^gwep]: AWS, "Gateway endpoints". <https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html>
[^sg]: AWS, "Control traffic to your AWS resources using security groups". <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html>
[^nacl]: AWS, "Control subnet traffic with network access control lists". <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>
[^ssm]: AWS, "AWS Systems Manager Session Manager". <https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html>
[^imds]: AWS, "Configure the Instance Metadata Service options". <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html>
[^acmdns]: AWS, "AWS Certificate Manager DNS validation". <https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html>
[^acm]: AWS, "What is AWS Certificate Manager?". <https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html>
[^albtls]: AWS, "Security policies for your Application Load Balancer". <https://docs.aws.amazon.com/elasticloadbalancing/latest/application/describe-ssl-policies.html>
[^r53alias]: AWS, "Routing traffic to an ELB load balancer". <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-elb-load-balancer.html>
