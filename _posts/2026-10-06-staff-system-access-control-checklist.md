---
layout: post
title: "직원·협력사용 시스템 접근통제 점검표 — '로그인했는가'가 아니라 '이 데이터를 볼 자격이 있는가'"
date: 2026-10-06 23:51:17 +0900
categories: [security]
tags: [access-control, idor, bola, owasp, mfa, spring-security, defense]
---

고객용 앱은 보안 점검을 자주 받는다. 반면 직원 업무지원 화면, 대출모집인·협력사 포털, 내부용 조회 API 는 "내부 사람만 쓴다"는 이유로 점검에서 빠지기 쉽다. 그런데 이런 시스템이 인터넷에서 접근된다면 공격자 입장에서는 그냥 또 하나의 웹 서비스일 뿐이다.

이 글은 그런 시스템에 대한 **방어 점검표**다. 배경으로 함께 읽을 자료는 두 가지다.

- 앞선 글: [2026년 10월 은행 연쇄 해킹 — 뚫린 곳은 '직원·대출모집인용 뒷문'이었다](https://myoungsoo7.github.io/2026/10/06/korean-bank-breaches-2026-cause-and-defense/)
- 숭실대 AI안전성연구센터의 격리 환경 재현 실험 보도: [ZDNet Korea, 2026-10-06](https://zdnet.co.kr/view/?no=20261006095704) (대학 자체 발표를 언론이 전한 것이며, 보고서 원문·동료심사는 아직 없다)

결론은 하나다. 공격 도구가 AI 든 스크립트든, **막는 지점은 같다.** 서버가 매 요청마다 "이 사용자가 이 객체를 볼 자격이 있는가"를 확인하면 된다.

## 1. 왜 이게 1순위인가

[OWASP Top 10 (2021)](https://owasp.org/Top10/A01_2021-Broken_Access_Control/) 은 *Broken Access Control* 을 1위(A01)에 올렸다. API 쪽 목록인 [OWASP API Security Top 10 (2023)](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/) 의 1위도 *Broken Object Level Authorization(BOLA)* 이다. BOLA 는 흔히 IDOR(Insecure Direct Object Reference)라고 부르는 문제와 같은 계열이다. 요청에 들어온 ID 만 믿고 객체를 돌려주는 것이다.

이 취약점이 위험한 이유는 **겉으로는 정상 요청과 구별이 안 된다**는 점이다. 문법적으로 올바른 요청이고, 로그인도 됐을 수 있다. 단지 *남의* 번호를 넣었을 뿐이다. 그래서 WAF 시그니처로는 잘 안 잡히고, 애플리케이션의 인가 로직에서만 막을 수 있다.

## 2. 점검표

### ① 자산 목록 — "내부용"도 외부 노출이면 목록에 넣는다

- 인터넷에서 닿는 모든 호스트·경로를 목록화한다. 직원용·협력사용·모바일 업무앱 백엔드·레거시 조회 페이지를 빠뜨리지 않는다.
- 각 항목에 **소유 부서, 사용자 유형, 인증 방식, 다루는 개인정보 종류**를 적는다.
- 외부 노출이 꼭 필요 없는 것은 VPN·사설망 뒤로 옮긴다. 가장 확실한 방어는 노출 면적을 줄이는 것이다.

### ② 인증 — 직원·협력사 계정에도 MFA

- 고객용 서비스에 MFA 가 있는데 직원·협력사용에 없다면 그쪽이 가장 약한 고리다.
- 피싱 저항형 인증(FIDO2/패스키 등)을 우선 검토한다. 인증 강도 기준은 [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html) 를 참고한다.
- 퇴사·계약 종료 시 계정과 권한을 즉시 회수하는 절차가 실제로 돌고 있는지 확인한다.

### ③ 인가 — 매 요청, 서버에서, 객체 단위로

[OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) 와 [IDOR Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html) 의 핵심을 요약하면 다음과 같다.

- **기본 거부(deny by default).** 명시적으로 허용된 경우만 통과시킨다.
- **객체 단위 확인.** "로그인했는가"로 끝내지 않는다. "이 사용자(또는 이 협력사)가 *이 레코드* 에 대한 권한이 있는가"를 매번 확인한다.
- **클라이언트를 믿지 않는다.** 화면에서 버튼을 숨기는 것은 통제가 아니다. 요청 파라미터·헤더·숨은 필드에 든 사용자·지점·권한 값은 무시하고, 서버 세션의 신원에서 다시 계산한다.
- **추측하기 어려운 ID(UUID 등)는 보조 수단일 뿐이다.** 번호를 순서대로 매기지 않으면 대입이 어려워지지만, 그것만으로 권한 확인을 대신할 수는 없다.
- 조회 결과도 **필요한 필드만** 돌려준다. 목록 API 가 전체 주민번호·연락처를 통째로 내보내지 않게 한다.

Spring 예시로 보면, 차이는 쿼리 한 줄이다.

```java
// ❌ ID 만 믿는다 — 로그인한 누구든 아무 번호나 조회 가능
@GetMapping("/applications/{id}")
public ApplicationDto get(@PathVariable Long id) {
    return ApplicationDto.from(repo.findById(id).orElseThrow());
}

// ✅ 소유 관계를 조회 조건에 넣는다 — 남의 것은 '없는 것'과 같게 응답
@GetMapping("/applications/{id}")
public ApplicationDto get(@PathVariable Long id, @AuthenticationPrincipal Agent me) {
    return repo.findByIdAndAgentId(id, me.getId())
               .map(ApplicationDto::from)
               .orElseThrow(NotFoundException::new);  // 403 대신 404: 존재 여부도 숨긴다
}
```

그리고 **거부되는 경우를 테스트로 고정**한다. 허용 케이스만 테스트하면 인가 회귀는 잡히지 않는다.

```java
@Test
void 다른_모집인의_신청건은_조회할_수_없다() throws Exception {
    mvc.perform(get("/applications/{id}", 남의신청건Id).with(user(모집인A)))
       .andExpect(status().isNotFound());
}
```

### ④ 남용 탐지 — "한 계정이 몇 개의 서로 다른 객체를 봤는가"

인가가 제대로 되어 있어도, 탐지는 따로 필요하다.

- 요청 *횟수* 만 세지 말고, **계정·세션별로 조회한 서로 다른 객체 수**를 센다. 정상 업무는 담당 건 몇 개를 반복해 보는데, 대입 공격은 넓고 얕게 훑는다.
- 같은 계정이 짧은 시간에 여러 IP·국가에서 오면 경보를 낸다. IP 차단은 응급조치일 뿐이고 공격자는 IP 를 바꾼다. 그래서 **계정·행동 단위 통제**가 더 오래 간다.
- 조회 API 에 계정 단위 속도 제한을 두고, 임계값을 넘으면 차단보다 **추가 인증 요구**로 대응하면 정상 사용자 불편이 적다.
- 이런 자동화 위협의 분류는 [OWASP Automated Threats to Web Applications](https://owasp.org/www-project-automated-threats-to-web-applications/) 를 참고한다. 대량 계정 대입은 [Credential Stuffing Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html) 가 정리돼 있다.
- 개인정보 조회 로그(누가, 언제, 어떤 객체를)는 사고 후 유출 범위를 확정하는 데 필수다. 보존 기간과 무결성을 확인해 둔다.

### ⑤ 검증 — 정기적으로, 허가된 범위에서

- 접근통제는 코드가 바뀔 때마다 깨질 수 있다. 위 ③의 거부 테스트를 CI 에 넣는다.
- 외부 노출 자산은 정기적으로 **허가된** 모의해킹·취약점 진단 범위에 포함시킨다. "내부용이라 제외"를 없앤다.
- 점검 결과는 "로그인 없이 볼 수 있는가"와 "로그인 후 *남의 것* 을 볼 수 있는가"를 따로 기록한다. 두 번째가 더 자주 빠진다.

## 3. AI 공격 도구 시대에 달라진 것과 안 달라진 것

**달라진 것:** 숭실대 재현 실험 보도가 강조한 점은, 이런 취약점을 찾는 데 전문 지식이 덜 필요해졌다는 것이다. 공격의 진입 장벽이 낮아지면, "누가 이걸 찾겠어"라는 가정은 더 빨리 깨진다.

**안 달라진 것:** 막는 방법이다. 국내 보안 전문가들도 이번 사고에서 AI 도구 사용 여부보다 **부가 시스템의 기본 통제 부재**가 본질이라고 지적했다([한겨레, 2026-10-04](https://www.hani.co.kr/arti/economy/it/1280877.html)). 객체 단위 인가, MFA, 행동 기반 탐지는 공격자가 사람이든 스크립트든 AI 든 똑같이 작동한다.

> **한계.** 이 글은 일반적인 방어 원칙을 정리한 것이다. 특정 기관의 실제 시스템 구조나 사고 원인을 확정하는 글이 아니며, 사고 조사는 진행 중이다.

## References

1. OWASP, *Top 10:2021 — A01 Broken Access Control*. <https://owasp.org/Top10/A01_2021-Broken_Access_Control/>
2. OWASP, *API Security Top 10 2023 — API1 Broken Object Level Authorization*. <https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/>
3. OWASP Cheat Sheet Series, *Authorization Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html>
4. OWASP Cheat Sheet Series, *Insecure Direct Object Reference Prevention Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html>
5. OWASP Cheat Sheet Series, *Credential Stuffing Prevention Cheat Sheet*. <https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html>
6. OWASP, *Automated Threats to Web Applications*. <https://owasp.org/www-project-automated-threats-to-web-applications/>
7. NIST, *SP 800-63B Digital Identity Guidelines: Authentication and Authenticator Management*. <https://pages.nist.gov/800-63-4/sp800-63b.html>
8. ZDNet Korea, 숭실대 AI안전성연구센터 재현 실험 보도 (2026-10-06, 학계 발표의 언론 보도). <https://zdnet.co.kr/view/?no=20261006095704>
9. 한겨레, 전문가 인터뷰 (2026-10-04, 언론 보도). <https://www.hani.co.kr/arti/economy/it/1280877.html>
