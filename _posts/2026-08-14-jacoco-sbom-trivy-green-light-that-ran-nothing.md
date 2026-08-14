---
layout: post
title: "초록불인데 아무것도 안 했다 — JaCoCo·SBOM·Trivy 를 CI 에 붙이며 배운 것"
date: 2026-08-14 13:40:00 +0900
categories: [ci, security, testing]
tags: [jacoco, sbom, cyclonedx, trivy, sca, github-actions, gradle, supply-chain]
---

CI 에 검증 도구를 붙이는 일은 대개 이렇게 끝난다. 워크플로에 스텝을 추가하고, 초록불이 뜨고, "커버리지 측정 중 / SCA 돌고 있음" 이라고 README 에 적는다.

그런데 초록불은 **검사가 통과했다** 는 뜻이 아니라 **스텝이 0 으로 종료했다** 는 뜻이다. 검사를 하고 통과한 것과, 검사를 안 하고 종료한 것은 종료 코드가 같다.

이 글은 정산 시스템 백엔드([settlement](https://github.com/MyoungSoo7/settlement), 17개 서비스 Gradle 멀티모듈) 에 세 가지 도구를 붙이면서 실제로 겪은 기록이다.

1. **JaCoCo 커버리지 리포트 수집** — 테스트가 어느 줄을 실행했는지 XML 로 남긴다
2. **SBOM 생성 (CycloneDX)** — 이 빌드에 들어간 의존성 전체를 기계가 읽는 목록으로 뽑는다
3. **Trivy SCA 스캔** — 그 SBOM 을 훑어 HIGH/CRITICAL 취약점이 있으면 막는다

셋 다 붙이는 것 자체는 각각 몇 줄이다. 정작 시간을 잡아먹은 건 **붙였는데 안 도는 상태를 발견하는 일** 이었고, 세 도구가 각자 다른 방식으로 같은 실패를 저질렀다. 그 얘기를 하려고 한다.

---

## 1. JaCoCo — 커버리지는 두 번 만들어진다

JaCoCo 는 클래스 로딩 시점에 Java agent 로 바이트코드를 **on-the-fly 계측**한다. 원본 클래스를 고치지 않고, 메서드마다 `boolean[]` 배열에 표시를 남기는 프로브(probe) 를 끼워 넣는다. JaCoCo 문서에 따르면 프로브는 메서드 종료 지점과 진입 간선이 둘 이상인 지점에만 삽입되며, 클래스 파일 크기는 약 30% 늘고 실행 시간 오버헤드는 통상 10% 미만이다.[^1][^2]

여기서 첫 번째 함정. **라인 커버리지는 디버그 정보가 있어야만 계산된다.** JaCoCo 가 세는 최소 단위는 소스 줄이 아니라 바이트코드 명령이고, 명령을 소스 줄에 매핑하려면 컴파일 시 line number 정보가 class 파일에 박혀 있어야 한다. 없으면 instruction/branch 커버리지는 나오지만 line 은 안 나온다.[^3]

두 번째 함정이 실제로 나를 물었다. **`.exec` 는 리포트가 아니다.** 테스트를 돌리면 실행 데이터(`.exec`)가 생기지만, 다른 도구가 읽는 건 `jacocoTestReport` 가 만드는 XML 이다. 이 둘을 이어주지 않으면 테스트는 정상적으로 다 돌고, 커버리지도 실제로 측정되고, 그런데 **SonarCloud 에는 0.0% 로 뜬다.**

```kotlin
tasks.named<JacocoReport>("jacocoTestReport") {
    reports { xml.required.set(true) }
}
tasks.test { finalizedBy(tasks.named("jacocoTestReport")) }
```

```properties
sonar.coverage.jacoco.xmlReportPaths=**/build/reports/jacoco/test/jacocoTestReport.xml
```

이 프로퍼티 한 줄이 없어서 커버리지가 0.0% 로 잡혀 있었다. 화면상으로는 "SonarCloud 연동 완료 · 분석 성공" 이었고, 다만 커버리지 숫자만 0 이었다. **연동은 성공했는데 전달된 게 없었다.**

멀티모듈에서는 이게 더 잘 깨진다. settlement 는 모듈별로 매트릭스 잡을 나눠 돌린 뒤, 집계 잡이 아티팩트를 원래 경로로 되돌려 놓아야 Sonar 의 글롭이 XML 을 찾는다. 배선이 한 칸이라도 어긋나면 "복원된 XML 0개" 인 채로 조용히 진행된다. 그래서 가드를 넣었다.

```bash
count=$(ls -1 */build/reports/jacoco/test/jacocoTestReport.xml 2>/dev/null | wc -l)
echo "복원된 커버리지 XML: ${count}개"
# 0 개면 Sonar 커버리지가 조용히 0% 로 잡히고 PR 코멘트도 빈손이 된다 — 침묵시키지 않는다.
if [ "$count" -eq 0 ] && [ "${{ needs.backend-test.result }}" = "success" ]; then
  echo "::error::모듈 테스트는 통과했는데 커버리지 XML 이 하나도 복원되지 않았다"
  exit 1
fi
```

**"테스트는 통과했는데 산출물이 0개"** 는 정상 상태가 아니다. 이걸 에러로 만들지 않으면 영영 모른다.

---

## 2. SBOM — 의존성 목록을 사람이 아니라 기계가 읽게

SBOM(Software Bill of Materials) 은 미국 행정명령 14028 이 "소프트웨어에 들어간 구성요소와 공급망 관계를 담은 공식 기록" 으로 정의하면서 사실상 표준 용어가 됐고, NTIA 가 최소 요소를 ▲데이터 필드 ▲자동화 지원 ▲운영 관행 세 축으로 규정했다.[^4][^5] 핵심은 **자동화 지원** 이다. NTIA 는 스프레드시트로 수기 관리하는 방식은 조직 경계를 넘어 확장되지 않는다고 못 박았고, 기계가 읽을 수 있는 포맷으로 SPDX·CycloneDX·SWID 세 가지를 지목했다.[^4]

settlement 는 CycloneDX 를 골랐다. OWASP 프로젝트로 시작해 지금은 Ecma International 표준 **ECMA-424** 로 발행돼 있고, SBOM 뿐 아니라 VEX·CBOM·ML-BOM 까지 같은 스키마로 다룬다.[^6][^7] 포맷 선택에 대단한 근거가 있었던 건 아니고, Gradle 플러그인이 루트에 한 줄이면 끝나서였다.

```kotlin
plugins { id("org.cyclonedx.bom") version "3.4.1" }
```

```yaml
- name: Generate SBOM (CycloneDX)
  run: ./gradlew cyclonedxBom --no-daemon
```

루트에 적용하면 17개 서비스를 전부 합친 **aggregate BOM** 하나가 `build/reports/cyclonedx/bom.json` 에 떨어진다. 실측 **451개 컴포넌트.** 손으로는 절대 안 셌을 숫자다.

그리고 여기서 세 번째 함정이 나왔다. 업로드 스텝에 `if: always()` 가 붙어 있었다.

```yaml
- name: Upload SBOM
  uses: actions/upload-artifact@...  # v7.0.1
  with:
    name: backend-sbom
    path: build/reports/cyclonedx/bom.json
```

`always()` 를 뗀 이유는 run **31599697053** 이다. 그 실행에서 **Generate 는 skipped, Upload 는 success** 였다. SBOM 을 안 만들었는데 업로드가 돌아서 빈손으로 성공했고, 워크플로 화면에는 초록 체크가 하나 더 늘었다. `if-no-files-found` 기본값이 `warn` 이라 경고만 남기고 넘어간다.

**아티팩트 업로드 스텝은 앞 스텝의 실패를 숨기는 데 특히 좋은 자리다.** `always()` 는 "결과를 남기고 싶다" 는 선의로 붙이지만, 남길 결과가 없을 때 그 사실을 지운다.

---

## 3. Trivy — 목록을 훑어 실제로 막기

SBOM 은 그 자체로는 그냥 JSON 파일이다. 값이 생기는 건 이걸 취약점 DB 와 대조할 때다. Trivy 는 `scan-type: sbom` 으로 CycloneDX/SPDX 파일을 직접 입력으로 받는다.

```yaml
- name: SCA — Trivy SBOM scan (HIGH/CRITICAL gate)
  uses: aquasecurity/trivy-action@...  # v0.36.0
  with:
    version: v0.73.0
    scan-type: sbom
    scan-ref: build/reports/cyclonedx/bom.json
    scanners: vuln
    severity: HIGH,CRITICAL
    ignore-unfixed: true
    trivyignores: .trivyignore.yaml
    exit-code: "1"
```

`exit-code: "1"` 이 이 스텝을 리포트가 아니라 **게이트**로 만든다. 이게 없으면 Trivy 는 취약점을 예쁘게 표로 찍고 0 으로 종료한다.

`ignore-unfixed: true` 도 중요하다. 패치가 아직 없는 취약점까지 막으면 개발자가 손쓸 수 없는 이유로 머지가 막히고, 그러면 두 주 안에 누군가 게이트를 꺼버린다. **끄고 싶어지지 않는 게이트만 살아남는다.**

### Snyk 을 걷어낸 이유

원래 SCA 는 Snyk 이었다. run **31432558450** 로그를 열어보고 갈아탔다.

```
ERROR  Authentication error (SNYK-0005)
✗ 21/21 detected Gradle manifests did not return dependencies
```

토큰이 무효라 스캔 자체가 시작되지 않았고, 의존성 해석도 전부 실패했다. 그런데 스텝에 `continue-on-error: true` 가 붙어 있어서 둘 다 삼켜졌다. 남은 건 **"SCA 가 돌고 있다"는 초록불** 하나였다. 얼마나 오래 그 상태였는지는 모른다.

### 베이스라인은 "무시" 가 아니라 "만료가 있는 유예"

처음 게이트를 켰을 때 **48건**(CRITICAL 5 · HIGH 43) 이 걸렸다. 전부 무시 목록에 넣고 초록불을 만들 수도 있었지만, 그건 게이트를 끄는 것과 같다. 대신 실제로 고칠 수 있는 것부터 고쳤다.

- Spring Boot `4.0.4 → 4.0.7` — **40건 해소**
- `bcprov-jdk18on 1.81 → 1.84` — CVE-2025-14813 해소
- 남은 **7건**(전부 HIGH, **CRITICAL 0**) 만 `.trivyignore.yaml` 에 등재

대부분은 버전 하나 올리면 사라진다. 무시 목록에 먼저 손이 가면 이걸 영영 모른다.

그리고 남긴 7건에는 각각 `statement`(왜 지금 안 고치는지) 와 `expired_at`(2026-09-30) 을 붙였다. **만료가 없는 예외는 예외가 아니라 삭제다.** 만료일이 지나면 게이트가 다시 빨개지고, 그때 다시 판단하게 된다.

재측정은 로컬에서 두 줄이면 된다.

```bash
./gradlew cyclonedxBom
trivy sbom build/reports/cyclonedx/bom.json --severity HIGH,CRITICAL --ignore-unfixed
```

---

## 4. 스텝 순서가 보안 게이트를 지웠다

가장 배운 게 많았던 사고. 원래 순서는 `SonarCloud → SBOM → Trivy` 였다.

2026-08-12, run **31602739861** 에서 `SONAR_TOKEN` 이 만료돼 Sonar 스텝이 HTTP 403 으로 실패했다. 그러자 뒤따르던 SBOM 생성과 Trivy 스캔이 **통째로 skip** 됐다. GitHub Actions 의 기본 동작이다 — 앞 스텝이 실패하면 뒤는 안 돈다.

즉 **품질 분석 도구의 인증 토큰이 만료됐다는 이유로, 무관한 보안 게이트가 사라졌다.** 그날 그 브랜치는 SCA 검사를 한 번도 받지 않고 통과할 수 있었다.

고친 건 간단하다. 순서를 뒤집었다.

```
SCA (SBOM → Trivy)  →  SonarCloud
```

보안 게이트를 앞에 두면 품질 도구의 사정과 무관하게 항상 판정된다. **막아야 하는 것을, 막지 않아도 되는 것 뒤에 두지 않는다.**

덧붙여, 같은 리포에서 SonarCloud 는 더 조용히 죽어 있었다. sonarqube 플러그인 5.1.0.4882 가 Gradle 9 에서 `NoSuchMethodError` 로 13초 만에 죽었는데 `continue-on-error` 가 이것도 삼켰다. 확인해보니 **분석 결과가 업로드된 적이 한 번도 없었다.**

---

## 5. skip 은 통과가 아니다

이 사고들을 정리하다 보니 같은 모양이 하나 더 보였다. GitHub 의 필수 상태 체크(required status check) 에서 **skip 된 잡은 통과로 취급된다.** 그리고 `needs` 로 묶인 잡의 기본 동작은 선행 잡이 실패하면 **skip** 이다.

둘을 곱하면: 모듈 하나가 깨져서 선행 잡이 실패 → 집계 잡이 skip → 필수 체크는 통과로 기록 → **머지 가능.**

```yaml
backend-ci:
  needs: [changes, backend-shared, backend-test]
  if: always() && !cancelled() && needs.changes.outputs.backend == 'true'
  steps:
    - name: 모듈 테스트 결과 집계
      run: |
        set -euo pipefail
        for result in "${{ needs.backend-shared.result }}" "${{ needs.backend-test.result }}"; do
          case "$result" in
            success|skipped) ;;
            *) echo "::error::백엔드 모듈 테스트가 통과하지 않았다 (result=$result)"; exit 1 ;;
          esac
        done
```

`always()` 로 잡을 살려두고, **선행 결과를 직접 읽어서 판정한다.** 변경 없음으로 인한 `skipped` 만 허용하고 `failure`/`cancelled` 는 여기서 떨어뜨린다. 앞에서는 `always()` 를 뗐고 여기서는 붙였는데, 원칙은 같다 — **판정하는 스텝은 항상 돌고, 산출물을 다루는 스텝은 산출물이 있을 때만 돈다.**

---

## 정리

세 도구를 붙이며 나온 사고를 나열해보면 결이 하나다.

| 실패 | 화면에 보인 것 | 실제 |
|---|---|---|
| `xmlReportPaths` 누락 | 분석 성공 | 커버리지 0.0% |
| Generate skipped + `always()` 업로드 | 초록 체크 | 빈 아티팩트 |
| Snyk 인증 실패 + `continue-on-error` | SCA 통과 | 스캔 미실행 |
| Sonar 403 → 후속 스텝 skip | 잡 실패 1개 | 보안 게이트 소멸 |
| 필수 체크의 skip | 통과 | 검사 안 함 |

전부 **"검사를 통과했다" 가 아니라 "검사를 안 했다"** 다. 그리고 CI 화면에서 이 둘은 똑같이 생겼다.

그래서 도구를 붙일 때 마지막에 하는 일이 하나 늘었다. **일부러 깨뜨려 보는 것.**

커버리지 임계값을 100% 로 올려보고 빨개지는지, 테스트에 `assertEquals(1, 2)` 를 넣어보고 빨개지는지, `.trivyignore.yaml` 을 잠깐 비워보고 7건이 그대로 뜨는지. 한 번도 빨개진 적 없는 게이트는 게이트가 아니라 장식이고, **초록불은 그것이 빨개질 수 있다는 걸 확인한 뒤에야 정보가 된다.**

---

### References

[^1]: JaCoCo, "Implementation Design". <https://www.jacoco.org/jacoco/trunk/doc/implementation.html>
[^2]: JaCoCo, "Control Flow Analysis" (Marc R. Hoffmann, 2011) — 프로브 삽입 전략, 클래스 크기 약 30% 증가, 실행 오버헤드 통상 10% 미만. <https://www.jacoco.org/jacoco/trunk/doc/flow.html>
[^3]: JaCoCo, "Coverage Counters" — 라인 커버리지는 디버그 정보로 컴파일된 클래스 파일에서만 계산 가능. <https://www.jacoco.org/jacoco/trunk/doc/counters.html>
[^4]: NTIA, *The Minimum Elements For a Software Bill of Materials (SBOM)*, 2021-07-12. <https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom>
[^5]: Executive Order 14028, *Improving the Nation's Cybersecurity*, 2021-05-12. <https://www.federalregister.gov/d/2021-10460>
[^6]: Ecma International, *ECMA-424: CycloneDX Bill of Materials Specification*. <https://ecma-international.org/publications-and-standards/standards/ecma-424/>
[^7]: OWASP CycloneDX 프로젝트. <https://owasp.org/www-project-cyclonedx/>
[^8]: Trivy, "Java coverage" 및 SBOM 스캔 문서. <https://trivy.dev/latest/docs/coverage/language/java/>

본문의 수치·run ID·버전은 모두 [MyoungSoo7/settlement](https://github.com/MyoungSoo7/settlement) 의 `.github/workflows/ci.yml`, `build.gradle.kts`, `.trivyignore.yaml` 에서 실측한 값이며 해당 파일에 주석으로 남아 있다. 단일 리포 사례이므로 일반화된 벤치마크가 아니다.
