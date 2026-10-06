---
layout: post
title: "OWASP Cheat Sheet Series — 개발자가 필요한 칸만 골라 보는 무료 보안 레퍼런스 (분야별 링크 모음)"
date: 2026-10-06 23:40:00 +0900
categories: [security]
tags: [owasp, secure-coding, authentication, kubernetes, ci-cd, api-security, sql-injection]
---

보안 가이드는 대개 두껍다. 그래서 정작 필요할 때 펼쳐 보지 않는다.
[OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)는 그 반대다. 주제 하나에 페이지 하나, 무료로 공개돼 있다.
프로젝트 소개문 그대로 옮기면 *"특정 애플리케이션 보안 주제에 대해 가치가 높은 정보를 간결하게 모은 것"*이고, 각 주제의 전문가들이 썼다.

이 글은 분야별로 **실제로 펼쳐 볼 치트시트 링크**와, 각 문서에서 바로 가져다 쓸 한 줄을 정리한다.
마침 이번 주에 겪은 일들(은행 연쇄 해킹, 클러스터 CI 러너, 쿠버네티스 보안 점검)과 바로 이어지는 문서가 많아서 같이 적었다.

## 1. 인증 · 비밀번호 · 세션

| 치트시트 | 바로 가져다 쓸 것 |
|---|---|
| [Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) | 로그인 흐름 전반의 기준 |
| [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) | 요약 권고: **Argon2id, 메모리 최소 19MiB · 반복 2 · 병렬 1**. Argon2id 를 못 쓰면 scrypt |
| [Multifactor Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html) | 2단계 인증 설계 |
| [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) | 쿠키 `Secure`·`HttpOnly`·`SameSite` 속성, 세션 만료 |

## 2. 인가(권한) — 이번 주에 가장 아팠던 칸

인증은 "누구냐"이고, 인가는 "**그 사람이 이것을 볼 자격이 있냐**"다. 이번 주 [은행 연쇄 해킹]({% post_url 2026-10-06-korean-bank-breaches-2026-cause-and-defense %})에서
뚫린 게 바로 이 칸이었다. 식별값을 바꿔 넣어 남의 고객 정보를 불러올 수 있었다.

| 치트시트 | 바로 가져다 쓸 것 |
|---|---|
| [Insecure Direct Object Reference Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html) | IDOR 은 *"사용자가 특정 데이터에 접근해도 되는지 검증하는 접근통제 검사가 빠져서"* 생긴다. 객체·그 객체를 가리키는 ID·검사 누락, 세 가지가 재료다 |
| [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | 기본 거부, 요청마다 서버에서 권한 확인 |

## 3. Docker · Kubernetes

| 치트시트 | 바로 가져다 쓸 것 |
|---|---|
| [Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) | `/var/run/docker.sock` 은 Docker API 의 입구이고, *"여기 접근 권한을 주는 건 호스트에 제한 없는 root 권한을 주는 것과 같다."* TCP 로 데몬 소켓을 열지 말 것 |
| [Kubernetes Security](https://cheatsheetseries.owasp.org/cheatsheets/Kubernetes_Security_Cheat_Sheet.html) | 내장 RBAC 로 역할별 권한 정의, 네트워크 정책, 비밀 관리 |
| [Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) | 비밀값의 저장·회전·폐기 수명주기 |

Docker 소켓 문장은 우리 클러스터에서 CI 러너 계정을 docker 그룹에 넣을 때 그대로 따져 본 내용이다.
docker 그룹 = 사실상 root 라서, 러너는 비공개 리포에만 붙이고 러너와 그 컨테이너에 자원 상한을 따로 걸었다.

## 4. 언어·프레임워크별

| 치트시트 | 대상 |
|---|---|
| [Java Security](https://cheatsheetseries.owasp.org/cheatsheets/Java_Security_Cheat_Sheet.html) | Java |
| [PHP Configuration](https://cheatsheetseries.owasp.org/cheatsheets/PHP_Configuration_Cheat_Sheet.html) | PHP 설정 |
| [Node.js Security](https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html) | Node.js |

쓰는 스택 하나만 골라서 처음부터 끝까지 한 번 읽어 보길 권한다. 프레임워크 기본값 중 무엇을 꼭 바꿔야 하는지가 정리돼 있다.

## 5. GitHub Actions · CI/CD

| 치트시트 | 바로 가져다 쓸 것 |
|---|---|
| [GitHub Actions Security](https://cheatsheetseries.owasp.org/cheatsheets/GitHub_Actions_Security_Cheat_Sheet.html) | `pull_request_target`·`workflow_run` 같은 위험한 트리거 피하기, **서드파티 액션은 커밋 해시로 고정**, `GITHUB_TOKEN` 권한 최소화, 정적 자격증명 제거, **self-hosted 러너는 각별히 주의**하고 러너 그룹·라벨로 분리 |
| [CI/CD Security](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html) | 파이프라인 계정의 최소 권한과 신원 수명주기(생성~폐기) 관리 |

"self-hosted 러너는 각별히 주의"라는 항목은 이번 주 우리 클러스터에 리포별 self-hosted 러너를 붙이면서 실제로 고민한 지점이다.
러너가 실행하는 건 결국 GitHub 에서 받아 온 코드다.

## 6. API · GraphQL

| 치트시트 | 바로 가져다 쓸 것 |
|---|---|
| [REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) | 엔드포인트별 접근통제, 입력 검증, 민감정보를 URL 에 넣지 않기 |
| [GraphQL](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html) | 흔한 공격으로 인젝션, DoS, **잘못된 인가**를 꼽고, 운영 환경의 과도한 에러·introspection·GraphiQL 같은 설정 노출을 경고 |

## 7. SQL · 데이터베이스

| 치트시트 | 바로 가져다 쓸 것 |
|---|---|
| [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) | 1차 방어 첫 번째가 **Prepared Statements (파라미터화 쿼리)** |
| [Query Parameterization](https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html) | 언어별 파라미터화 예제 모음 |
| [Database Security](https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html) | DB 계정 권한·연결 보안·설정 |

## 읽는 법

치트시트는 처음부터 다 읽는 책이 아니다. 추천하는 순서는 이렇다.

1. **지금 만들고 있는 기능의 칸 하나**를 연다. 로그인을 만들면 Authentication 과 Password Storage, API 를 만들면 Authorization 과 IDOR.
2. 문서의 **체크 항목을 지금 코드에 대 본다.** "우리는 이걸 하고 있나?"만 묻는다.
3. 못 하고 있는 항목 하나를 **이슈로 만든다.** 한 번에 다 고치려 하지 않는다.

이번 주 은행 사고의 원인은 결국 IDOR 치트시트 첫 문단에 적힌 그대로였다. 레퍼런스가 없어서 생긴 사고가 아니라, **펼쳐 보지 않아서** 생긴 사고에 가깝다.

## References

- OWASP Cheat Sheet Series (메인) — <https://cheatsheetseries.owasp.org/>
- 본문 표의 각 치트시트 링크 (모두 cheatsheetseries.owasp.org)
