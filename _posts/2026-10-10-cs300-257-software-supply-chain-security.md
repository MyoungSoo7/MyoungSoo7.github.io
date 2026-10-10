---
layout: post
title: "[CS300 #257] 공급망 보안 — 내가 쓰지 않은 코드가 내 서버에서 돈다"
date: 2026-10-10 22:17:00 +0900
categories: [cs]
tags: [cs300, security, supply-chain, sbom, slsa]
---

컴퓨터공학 300 주제 시리즈의 257번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

소프트웨어 공급망 보안은 내 제품에 들어가는 **남의 코드(의존성)와 그것을 만들고 옮기는 과정(빌드·배포)** 을 믿을 근거를 만드는 일이며, 핵심 도구는 의존성 고정과 해시 검증, SBOM, 빌드 출처 증명(provenance), 그리고 서명과 검증이다.

## 왜 필요한가

현대 애플리케이션 코드의 대부분은 직접 쓴 것이 아니다. 패키지 관리자로 받은 라이브러리, 그 라이브러리의 라이브러리, 기반 컨테이너 이미지, CI 에서 쓰는 액션과 플러그인. 이 중 하나만 오염돼도 내 서비스가 오염된다. 공격자 입장에서 인기 라이브러리 하나를 노리면 수천 곳을 한 번에 칠 수 있으니 효율이 좋다.

실제 사례가 이를 보여 준다. 2024년 공개된 xz 압축 라이브러리 사건(CVE-2024-3094)에서 NVD 설명에 따르면 악성 코드가 xz 5.6.0 부터 **업스트림 배포 tarball** 에 들어 있었고, 소스 안의 위장된 테스트 파일에서 미리 빌드된 객체를 꺼내 liblzma 함수를 변조하는 방식이었다. 저장소의 코드를 읽는 것만으로는 잡기 어려웠다. 빌드 과정과 배포물 자체를 검증해야 한다는 교훈이다.

OWASP Top 10:2025 는 이를 반영해 "소프트웨어 공급망 실패" 를 새 범주로 3위에 올렸다.

## 핵심 개념

### 공격 지점 지도

```
[개발자] → [소스 저장소] → [빌드 시스템] → [패키지·이미지 저장소] → [배포] → [운영]
   │            │               │                  │
 계정 탈취    악성 커밋      빌드 스크립트 변조   바꿔치기, 유사 이름 패키지
                                                   의존성 혼동
```

| 공격 | 설명 | 대책 |
|---|---|---|
| 타이포스쿼팅 | `requests` 대신 `reqeusts` 같은 유사 이름 패키지 | 의존성 추가 리뷰, 허용 레지스트리 |
| 의존성 혼동 | 사내 패키지 이름을 공개 저장소에 더 높은 버전으로 올림 | 사내 패키지는 사내 레지스트리로만, 네임스페이스 고정 |
| 관리자 계정 탈취 | 정상 패키지에 악성 버전 게시 | 레지스트리 MFA, 신규 버전 지연 반영 |
| 빌드 시스템 침해 | 소스는 깨끗한데 빌드 산출물이 오염 | 격리된 빌드, 출처 증명 |
| 취약한 구성 요소 | 악의는 없지만 알려진 취약점 포함 | SBOM, 취약점 스캔, 업데이트 체계 |

### 의존성 고정과 해시 검증

버전 범위(`>=1.2`)로 설치하면 빌드할 때마다 다른 코드가 들어올 수 있다. **잠금 파일**(package-lock.json, poetry.lock, go.sum 등)로 정확한 버전을, 가능하면 **해시까지** 고정한다. pip 는 `--require-hashes` 모드에서 요구 사항 파일의 해시와 다르면 설치를 거부한다.

### SBOM

SBOM(Software Bill of Materials)은 제품에 들어간 구성 요소의 목록이다. 새 취약점이 발표됐을 때 "우리 제품 중 어디에 이 라이브러리가 들어 있나" 에 몇 분 만에 답하게 해 준다. 대표 형식은 **SPDX** 와 **CycloneDX** 이고, 구성 요소는 보통 **purl**(package URL, 예: `pkg:pypi/requests@2.32.3`)로 식별한다.

### SLSA: 빌드의 무결성 단계

SLSA(Supply-chain Levels for Software Artifacts) v1.0 은 빌드 트랙을 네 단계로 정의한다.

| 단계 | 이름 | 의미 |
|---|---|---|
| Build L0 | No guarantees | 보장 없음 |
| Build L1 | Provenance exists | 어떻게 빌드됐는지 기술한 출처 증명이 있다 |
| Build L2 | Hosted build platform | 호스팅된 빌드 플랫폼이 출처 증명을 생성·서명한다 |
| Build L3 | Hardened builds | 빌드끼리 격리되고 서명 키가 빌드 스크립트로부터 보호된다 |

**출처 증명(provenance)** 은 "이 산출물은 이 저장소의 이 커밋을 이 빌드 플랫폼에서 이 절차로 만들었다" 는 서명된 기록이다. 배포 단계에서 이를 검증하면 개발자 노트북에서 몰래 만든 바이너리가 운영에 들어가는 것을 막는다.

### 서명과 검증

Sigstore 의 cosign 은 컨테이너 이미지와 아티팩트에 서명한다. 키리스(keyless) 방식은 OIDC 신원으로 단기 인증서를 받아 서명하고, 그 기록을 투명성 로그에 남긴다. 중요한 건 **검증을 강제하는 쪽**이다. 서명만 하고 배포 단계에서 확인하지 않으면 아무 효과가 없다. 쿠버네티스에서는 어드미션 정책으로 "우리 CI 신원으로 서명된 이미지만 실행" 을 강제한다.

## 직접 해 보기

두 가지를 해 본다. (1) 잠금 파일의 해시로 바꿔치기된 배포물을 거부하기 (2) 현재 파이썬 환경의 설치 패키지로 CycloneDX 형태의 최소 SBOM 만들기.

```python
import hashlib, json, os, tempfile
from importlib import metadata

# 1) 해시 고정 설치 흉내: 잠금 파일의 해시와 내려받은 파일을 대조한다
#    (pip install --require-hashes 가 하는 일의 핵심)
art = os.path.join(tempfile.mkdtemp(), "demo_pkg-1.0.0.tar.gz")
open(art, "wb").write(b"original release contents")
LOCK = {"demo_pkg==1.0.0": "sha256:" + hashlib.sha256(b"original release contents").hexdigest()}

def install(spec, path):
    got = "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()
    if got != LOCK.get(spec):
        raise RuntimeError(f"{spec}: 해시 불일치, 설치 중단")
    return f"{spec}: 해시 일치, 설치"

print(install("demo_pkg==1.0.0", art))
open(art, "wb").write(b"original release contents + backdoor")   # 저장소에서 바꿔치기됐다고 가정
try:
    install("demo_pkg==1.0.0", art)
except RuntimeError as e:
    print(e)

# 2) 지금 환경의 설치 패키지로 CycloneDX 형태의 최소 SBOM 만들기
comps = []
for dist in metadata.distributions():
    name, ver = dist.metadata["Name"], dist.version
    if name:
        comps.append({"type": "library", "name": name, "version": ver,
                      "purl": f"pkg:pypi/{name.lower()}@{ver}"})
comps.sort(key=lambda c: c["name"].lower())
sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "components": comps}
print("구성 요소 수:", len(comps))
print(json.dumps(sbom["components"][:2], ensure_ascii=False, indent=1))
```

실행 결과(Python 3.12. 구성 요소 수와 목록은 환경마다 다르다):

```
demo_pkg==1.0.0: 해시 일치, 설치
demo_pkg==1.0.0: 해시 불일치, 설치 중단
구성 요소 수: 127
[
 {
  "type": "library",
  "name": "acme",
  "version": "2.9.0",
  "purl": "pkg:pypi/acme@2.9.0"
 },
 ...
]
```

평범한 서버의 파이썬 환경에도 백 개가 넘는 패키지가 있다. 이 목록 없이 "우리는 영향받지 않는다" 를 확인할 방법은 없다. 다만 해시 고정에는 한계가 있다. xz 사례처럼 **정상 게시자가 처음부터 오염된 배포물을 올리면** 해시는 그 오염본과 일치한다. 해시는 "고정한 그것과 같다" 만 보장하고 "그것이 안전하다" 는 보장하지 않는다. 그래서 출처 증명·평판 지표·변경 리뷰가 함께 필요하다. 실무에서는 손으로 짠 SBOM 대신 Syft, cdxgen 같은 도구가 이미지·잠금 파일까지 분석해 표준 형식으로 만든다.

## 현업에서는

- **CI 의 서드파티 액션**: CI 워크플로가 참조하는 외부 액션을 태그(`@v4`)가 아니라 커밋 SHA 로 고정한다. 태그는 옮겨질 수 있다. CI 토큰 권한도 최소화한다.
- **이미지 업데이트 자동화**: Renovate·Dependabot 같은 도구로 의존성 업데이트 PR 을 자동으로 만들되, 새 버전 게시 직후 며칠은 기다렸다 반영하는 지연 정책을 두는 팀도 있다. 악성 버전이 발견되고 삭제될 시간을 버는 것이다.
- **홈랩에서도**: 헬름 차트와 컨테이너 이미지를 다이제스트로 고정하고, 레지스트리에서 받아 오는 이미지 목록을 주기적으로 스캔한다. `latest` 태그는 언제 무엇이 바뀌었는지 추적할 수 없게 만든다.
- **취약점 대응 속도**: 큰 라이브러리 취약점이 공개되면 SBOM 이 있는 조직은 영향 범위를 즉시 파악하고, 없는 조직은 서버마다 들어가 찾는다.

## 확인 문제

1. 의존성 혼동(dependency confusion) 공격의 원리와 대책은?
2. 해시 고정이 막는 공격과 막지 못하는 공격을 하나씩 들라.
3. SBOM 이 사고 대응에서 주는 가치는?
4. SLSA Build L1 과 L3 의 차이는?
5. 이미지 서명만 하고 검증을 강제하지 않으면 왜 의미가 없는가?

### 풀이

1. 사내 전용 패키지 이름을 공개 저장소에 더 높은 버전으로 올려 패키지 관리자가 공개본을 고르게 한다. 사내 패키지는 사내 레지스트리에서만 받도록 출처를 고정하고 네임스페이스를 선점한다.
2. 막는 것: 저장소나 전송 중 배포물 바꿔치기. 못 막는 것: 정상 게시자가 처음부터 악성 버전을 올린 경우(해시가 그 악성본과 일치).
3. 새 취약점이 공개됐을 때 영향받는 제품·버전을 빠르게 찾을 수 있다.
4. L1 은 출처 증명이 존재하는 수준이고, L3 는 빌드 플랫폼이 빌드 간 격리와 서명 키 보호까지 보장해 출처 증명 위조가 어렵다.
5. 공격자가 서명 없는 이미지나 다른 키로 서명한 이미지를 넣어도 배포가 진행된다. 효과는 검증 시점에서 생긴다.

## 더 읽을거리 (References)

- SLSA, [SLSA v1.0 Security Levels](https://slsa.dev/spec/v1.0/levels)
- Sigstore, [Cosign Signing Overview](https://docs.sigstore.dev/cosign/signing/overview/)
- OWASP CycloneDX, [Specification Overview](https://cyclonedx.org/specification/overview/)
- NIST NVD, [CVE-2024-3094 (xz)](https://nvd.nist.gov/vuln/detail/CVE-2024-3094)
- pip, [Secure installs (--require-hashes)](https://pip.pypa.io/en/stable/topics/secure-installs/)
