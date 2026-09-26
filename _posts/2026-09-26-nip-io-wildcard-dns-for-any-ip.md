---
layout: post
title: "nip.io — 도메인 없이 IP 에 이름을 붙이는 와일드카드 DNS"
date: 2026-09-26 21:03:43 +0900
categories: [DevOps, Networking]
tags: [nip.io, sslip.io, DNS, Wildcard DNS, Let's Encrypt, DNS Rebinding, Kubernetes Ingress]
---

`127.0.0.1.nip.io` 를 조회하면 `127.0.0.1` 이 돌아온다. 설정도 가입도 없다. 이름 안에 적은 IP 를 DNS 가 그대로 돌려준다. **nip.io** 는 이것만 하는 공개 DNS 서비스다.

기능은 한 줄이지만 쓰임새는 넓다. 로컬 개발, 쿠버네티스 인그레스 테스트, 도메인 없이 받는 TLS 인증서에 쓰인다. 이 글은 공식 페이지와 소스, 그리고 직접 돌린 `dig` 결과로 이 서비스를 정리한다.

## 1. 무엇을 하나 — 이름 안의 IP 를 되돌려준다

원래 nip.io 페이지의 첫 문장은 "`/etc/hosts` 편집을 그만두라"다. 서버마다 hosts 파일에 이름과 IP 를 적는 대신, IP 를 이름에 박아 넣으면 된다. ([nip.io](https://nip.io/))

표기법은 세 가지다. 앞에 아무 이름이나 붙여도 된다. 2026-09-26 에 필자가 직접 조회한 결과다.

| 조회한 이름 | 돌아온 주소 | 표기 |
|---|---|---|
| `127.0.0.1.nip.io` | `127.0.0.1` | 점(dot) |
| `app-10-0-0-1.nip.io` | `10.0.0.1` | 대시(dash) + 이름 |
| `app-c0a801fc.nip.io` | `192.168.1.252` | 16진수(hex) + 이름 |
| `7f000001.nip.io` | `127.0.0.1` | 16진수 |
| `--1.nip.io` (AAAA) | `::1` | IPv6 — 콜론 대신 대시 |

IPv6 는 점을 쓸 수 없어서 콜론을 대시로 바꾼다. 연속 콜론 `::` 는 `--` 가 된다. ([sslip.io](https://sslip.io/))

## 2. 누가 운영하나 — 주인이 바뀌었다

이 부분이 가장 헷갈린다.

- **원조 nip.io** 는 Exentrique Solutions 가 무료로 운영했다. PowerDNS 에 파이썬 PipeBackend(`backend.py`)를 붙인 구조이고, Apache 2.0 오픈소스다. ([GitHub: exentriquesolutions/nip.io](https://github.com/exentriquesolutions/nip.io))
- 지금 nip.io 페이지 맨 위에는 **"nip.io 는 이제 sslip.io 가 호스팅한다"**고 적혀 있다. 원래 페이지는 nip.io 를 만들고 운영한 고(故) Roopinder Singh 을 기리는 기념 페이지로 남았다. ([nip.io](https://nip.io/))
- **sslip.io** 는 2015년 8월 11일 Pivotal 사내 해커톤(Hack Day)에서 Brian Cunnie, Tyler Schultz, Alvaro Perez-Shirley 가 만들었다. Go 로 쓴 자체 DNS 서버이고, 역시 Apache 2.0 이다. 이름은 원조 격인 **xip.io** 를 만든 Sam Stephenson 이 제안했다. ([sslip.io](https://sslip.io/), [GitHub: cunnie/sslip.io](https://github.com/cunnie/sslip.io))

지금 `nip.io` 의 NS 레코드를 조회하면 `ns-00.nip.io`, `ns-01.nip.io`, `ns-ovh.sslip.io` 가 나온다. sslip.io 소스의 기본 네임서버 목록과 같다. 운영 주체가 넘어갔다는 안내를 DNS 로도 확인할 수 있다.

### 운영자가 바뀌며 달라진 동작

nip.io 페이지는 경고를 따로 붙여 두었다. **해석 방향이 오른쪽→왼쪽에서 왼쪽→오른쪽으로 바뀌었다.** 그래서 `1.127.0.0.1.nip.io` 는 이제 `127.0.0.1` 이 아니라 `1.127.0.0` 으로 풀린다. 필자가 조회해도 `1.127.0.0` 이 나왔다.

앞에 붙이는 이름에 숫자와 점을 섞어 쓰던 설정이 있다면, 조용히 엉뚱한 주소를 가리킬 수 있다.

## 3. 어디에 쓰나

### 로컬·사설망 개발

서비스를 여러 개 띄우면 이름으로 나눠 부르고 싶어진다. `api.127.0.0.1.nip.io`, `web.127.0.0.1.nip.io` 처럼 쓰면 hosts 파일 없이도 가상 호스트 라우팅을 시험할 수 있다. 팀원 PC 에도 같은 이름이 그대로 통한다. 이름이 IP 를 품고 있기 때문이다.

### 쿠버네티스 인그레스 테스트

인그레스는 보통 `Host` 헤더로 라우팅한다. 클러스터 진입 IP 가 `203.0.113.10` 이라면 호스트를 `grafana.203-0-113-10.nip.io` 로 주면 된다. 도메인 등록 없이 호스트 기반 라우팅을 바로 확인할 수 있다. *(예시 IP 는 문서용 대역 [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) 이다.)*

### 도메인 없이 TLS 인증서

공인 IP 가 있는 서버라면 `64-176-22-9.nip.io` 같은 이름으로 Let's Encrypt 인증서를 받을 수 있다. 운영자는 HTTP-01 챌린지로 이름마다 따로 발급받으라고 안내한다. 원조 페이지도 대시·16진수 표기가 "nip.io 의 평범한 서브도메인이라 Let's Encrypt 에 특히 유용하다"고 적는다. ([sslip.io](https://sslip.io/), [nip.io](https://nip.io/))

다만 레이트 리밋이 걸린다. Let's Encrypt 의 기본 한도는 **등록 도메인 하나당 7일에 50장**이고, 전 세계 모든 계정의 발급이 이 한도를 함께 쓴다. ([Let's Encrypt — Rate Limits](https://letsencrypt.org/docs/rate-limits/)) 모두가 같은 `nip.io` 아래서 발급받으니 기본값이면 금방 동난다. 운영자는 Let's Encrypt 가 nip.io 한도를 25만 장까지 올려 줬고, 50만 장 요청은 거절당했다고 적는다. *(운영자 주장이다. Let's Encrypt 측 공개 자료로는 확인하지 못했다.)* 막히면 `sslip.io` 쪽 이름이나 IP 주소 인증서를 쓰라는 게 운영자 안내다.

### 자기 도메인에 붙이기, 직접 띄우기

`nip.example.com` 같은 서브도메인의 NS 를 nip.io 네임서버 세 대로 위임하면, 자기 도메인에서 같은 기능을 쓸 수 있다. 외부에 기대기 싫으면 sslip.io DNS 서버를 바이너리나 Docker 이미지로 직접 띄울 수도 있다. 인터넷이 없는(air-gapped) 환경을 위한 `-nameservers`·`-addresses` 플래그도 있다. 원조 nip.io 도 `NIPIO_WHITELIST` 로 답할 IP 대역을 제한하는 환경변수를 제공했다. ([sslip.io](https://sslip.io/), [cunnie/sslip.io README](https://github.com/cunnie/sslip.io), [nip.io README](https://github.com/exentriquesolutions/nip.io))

## 4. 알고 써야 할 함정

### 공유기가 사설 IP 응답을 막는다 — DNS 리바인딩 보호

`192-168-0-10.nip.io` 가 어떤 네트워크에서는 안 풀린다. 일부 리졸버·포워더·공유기에는 **DNS 리바인딩 보호**가 있다. 공인 도메인이 사설 IP 를 돌려주면 그 응답을 버리는 기능이다. nip.io 페이지는 이 경우 서비스가 동작하지 않는다고 명시한다. 해결책으로는 로컬 nip.io 인스턴스를 띄우라고 안내한다. ([nip.io](https://nip.io/))

거꾸로 보면 이 보호 기능이 왜 있는지가 보인다. 외부 도메인이 사설 주소로 풀리게 두면, 브라우저에서 돈 스크립트가 내부망 기기에 닿는 공격(DNS rebinding)의 발판이 된다. nip.io 는 그걸 **누구나 할 수 있게 만든** 서비스이기도 하다. *(이 문단의 뒷부분은 필자의 해석이다.)*

### 조회가 제3자 DNS 로 나간다

`app-10-0-0-1.nip.io` 를 조회하면 그 이름이 재귀 리졸버를 거쳐 nip.io 네임서버까지 간다. 이름에는 **내부 IP 와 서비스 이름이 평문으로** 들어 있다. 사내 주소 체계나 서비스 이름이 민감하다면 공개 nip.io 대신 직접 띄운 인스턴스를 쓰는 게 맞다. *(DNS 의 일반 동작에서 끌어낸 필자의 추론이다.)*

### 외부 서비스 하나에 기대게 된다

nip.io 가 응답하지 않으면 그 이름을 쓰는 모든 환경이 같이 멈춘다. 무료 서비스이고 SLA 는 없다. 운영자가 한 번 바뀌었고, 그때 해석 규칙도 바뀌었다. 개발·데모에는 편하지만 운영 경로에 넣을 물건은 아니다.

### 피싱에도 쓰인다

누구나 아무 IP 에 그럴듯한 이름을 붙일 수 있으니 악용 신고 창구가 있다. 운영자는 `abuse@nip.io` 로 온 신고에 24시간 안에 응답한다고 적는다. ([sslip.io](https://sslip.io/))

### 2015년의 와일드카드 키 유출

sslip.io 는 2015년에 일주일 동안 자기 와일드카드 인증서의 **개인키를 공개**한 적이 있다. 인증서는 곧 폐기됐다. 지금은 와일드카드 인증서 자체를 운영하지 않는다. 그래서 "sslip.io 인증서는 위험하다"는 검색 결과는 옛날 이야기다. 이름마다 따로 받는 인증서의 개인키는 발급받은 사람의 서버에만 있다. ([sslip.io](https://sslip.io/))

## 5. 규모에 대해

운영자는 초당 2만 건 넘는 쿼리를 받고, Google·IBM·AMD·Cisco·Oracle 등의 문서가 자기를 언급한다고 적는다. *(운영자 자신이 밝힌 수치다. 제3자 측정은 찾지 못했다.)* GitHub 저장소의 별 수는 2026-09-26 기준 원조 nip.io 약 1,750개, sslip.io 약 1,070개다.

## 정리

| 질문 | 답 |
|---|---|
| 무엇인가 | 이름에 박힌 IP 를 그대로 돌려주는 공개 와일드카드 DNS |
| 표기 | 점 · 대시 · 16진수, IPv6 는 대시 |
| 운영 | 원조는 Exentrique Solutions. 지금은 sslip.io(Brian Cunnie)가 호스팅 |
| 좋은 곳 | 로컬 개발, 인그레스 테스트, 공인 IP 서버의 임시 TLS |
| 조심할 곳 | 리바인딩 보호로 사설 IP 가 안 풀림, 내부 이름이 외부로 나감, SLA 없음, 해석 규칙 변경 |

hosts 파일 한 줄을 없애 주는 서비스다. 그 한 줄을 인터넷 너머의 남의 DNS 에 맡기는 것이기도 하다. 개발 도구로 쓰고, 운영에 들일 거면 직접 띄우자.

## References

1. nip.io (원조 페이지, 기념 페이지로 보존). <https://nip.io/>
2. exentriquesolutions/nip.io — 소스 및 README (Apache 2.0). <https://github.com/exentriquesolutions/nip.io>
3. sslip.io — 공식 사이트 (nip.io 현 호스팅). <https://sslip.io/>
4. cunnie/sslip.io — Go DNS 서버 소스 및 README (Apache 2.0). <https://github.com/cunnie/sslip.io>
5. Let's Encrypt. *Rate Limits.* <https://letsencrypt.org/docs/rate-limits/>
6. RFC 5737 — IPv4 Address Blocks Reserved for Documentation. <https://www.rfc-editor.org/rfc/rfc5737>
