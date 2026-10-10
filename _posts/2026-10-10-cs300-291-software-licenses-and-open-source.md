---
layout: post
title: "[CS300 #291] 소프트웨어 라이선스와 오픈소스 — 공개된 코드와 쓸 수 있는 코드는 다르다"
date: 2026-10-10 22:51:00 +0900
categories: [cs]
tags: [cs300, hci, open-source, license, spdx]
---

컴퓨터공학 300 주제 시리즈의 291번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

코드는 저작물이고, 라이선스는 저작권자가 남에게 주는 사용 허락의 조건이다. 오픈소스 라이선스는 크게 "조건이 적은 허용형"과 "파생물도 같은 조건으로 공개하라는 카피레프트"로 나뉜다.

## 왜 필요한가

현대 소프트웨어의 대부분은 남이 만든 코드 위에 있다. `pip install`, `npm install` 한 줄로 수백 개 패키지가 들어온다. 각 패키지에는 라이선스가 있고, 조건을 지키지 않으면 그 코드를 쓸 권리가 없다.

현업에서 실제로 벌어지는 일이다.

- 제품 출시 직전 법무 검토에서 GPL 의존성이 발견돼 일정이 밀린다.
- GitHub 에서 찾은 코드를 복사했는데 라이선스 파일이 없다. 써도 되는지 모른다.
- 사내 도구를 오픈소스로 공개하려는데 어떤 라이선스를 붙일지 정하지 못한다.
- 도커 이미지를 고객에게 배포했는데 그 안의 패키지 고지 의무를 빠뜨렸다.

이 글은 법률 자문이 아니다. 개발자가 위험 신호를 알아보고 적절한 사람에게 물어볼 수 있을 만큼의 기본을 다룬다.

## 핵심 개념

### 기본값은 "허락 없음"

저작권은 창작과 동시에 생긴다. 라이선스가 없는 코드는 공개 저장소에 있어도 기본적으로 저작권자가 모든 권리를 가진다. GitHub 문서도 라이선스가 없으면 기본 저작권법이 적용되어 다른 사람이 복제·배포·파생물 작성을 할 수 없다고 안내한다. "공개되어 있다"와 "써도 된다"는 다른 말이다.

### 자유 소프트웨어와 오픈소스

두 흐름이 있다.

- 자유 소프트웨어 재단(FSF)은 네 가지 자유를 말한다. 실행할 자유(0), 연구하고 수정할 자유(1), 재배포할 자유(2), 수정본을 배포할 자유(3). 1과 3에는 소스 코드 접근이 전제된다.
- 오픈소스 이니셔티브(OSI)는 오픈소스 정의(OSD)의 10가지 기준을 둔다. 자유로운 재배포, 소스 코드 제공, 파생 저작물 허용, 개인·집단·사용 분야에 대한 차별 금지 등이다. OSI 가 승인한 라이선스 목록이 사실상 "오픈소스 라이선스"의 기준이다.

"상업적 사용 금지"나 "특정 회사 사용 금지" 조건이 붙은 라이선스는 OSD 의 차별 금지 기준에 어긋나므로 오픈소스가 아니다. 소스가 공개됐더라도 그렇다. 이런 것을 흔히 "소스 공개(source-available)"라고 부른다.

### 라이선스의 스펙트럼

| 분류 | 대표 | 핵심 조건 |
|---|---|---|
| 허용형(permissive) | MIT, BSD-2/3-Clause, Apache-2.0 | 저작권·라이선스 고지 유지. Apache-2.0 은 변경 사항 표시, NOTICE 파일 유지, 특허 허락 포함 |
| 약한 카피레프트 | LGPL, MPL-2.0 | 그 라이브러리(LGPL)나 파일(MPL) 자체의 수정본은 공개. 이를 쓰는 내 코드는 다른 라이선스 가능 |
| 강한 카피레프트 | GPL-2.0, GPL-3.0 | 배포하는 파생 저작물 전체를 같은 라이선스로, 소스와 함께 |
| 네트워크 카피레프트 | AGPL-3.0 | 네트워크로 서비스만 제공해도 사용자에게 수정된 소스를 제공 |
| 퍼블릭 도메인 유사 | CC0, Unlicense | 권리를 최대한 포기 |

### 카피레프트의 방아쇠는 "배포"다

GPL 의 의무는 대체로 소프트웨어를 다른 사람에게 배포(전달)할 때 생긴다. 사내에서만 쓰고 밖으로 나가지 않으면 소스 공개 의무가 생기지 않는 것이 일반적 해석이다. 반면 서버에서 돌리기만 하고 사용자에게 바이너리를 주지 않는 SaaS 는 GPL 의 배포 조건을 피할 수 있었고, 이 틈을 막으려고 만든 것이 AGPL 이다.

"배포"의 범위, "파생 저작물"의 경계(정적 링크, 동적 링크, 별도 프로세스 통신)는 해석이 갈리는 영역이다. 판단이 필요하면 법무 검토를 받는다.

### 호환성

서로 다른 라이선스의 코드를 섞어 하나로 배포하려면 조건이 동시에 만족되어야 한다. 허용형 코드는 대개 GPL 프로젝트에 넣을 수 있다. 반대로 GPL 코드를 MIT 로 배포하는 프로젝트에 넣을 수는 없다. Apache 재단과 FSF 는 Apache-2.0 이 GPL-3.0 과는 호환되지만 GPL-2.0 과는 호환되지 않는다고 본다.

### SPDX: 라이선스를 기계가 읽게

SPDX 는 라이선스마다 표준 식별자를 정한다(`MIT`, `Apache-2.0`, `GPL-3.0-only`, `GPL-3.0-or-later`). 소스 파일 머리에 한 줄로 적는다.

```python
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Example Project Contributors
```

`MIT OR Apache-2.0` 처럼 식(expression)으로 이중 라이선스도 표현한다. `OR` 는 받는 쪽이 하나를 골라도 된다는 뜻이고, `AND` 는 둘 다 지켜야 한다는 뜻이다. Rust 생태계의 많은 크레이트가 `MIT OR Apache-2.0` 을 쓴다.

## 직접 해 보기

의존성 목록의 SPDX 식을 회사 정책(허용·검토·금지)에 따라 분류하는 작은 검사기를 만든다. CI 에 붙이는 라이선스 검사 도구가 하는 일의 핵심이다. 실제 SPDX 식 문법(괄호, `WITH` 예외 등)은 이보다 복잡하니 실무에서는 검증된 도구를 쓴다.

```python
deps = [
    ("requests", "Apache-2.0"),
    ("numpy", "BSD-3-Clause"),
    ("some-gui-lib", "GPL-3.0-only"),
    ("dual-lib", "MIT OR GPL-2.0-or-later"),
    ("font-pack", "OFL-1.1"),
    ("mystery", "NOASSERTION"),
]

ALLOW = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC"}
REVIEW = {"OFL-1.1", "LGPL-2.1-or-later", "MPL-2.0"}
DENY = {"GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "AGPL-3.0-only"}

def classify(expr):
    # 단순화: OR 는 가장 좋은 선택지, AND 는 가장 나쁜 조건을 따른다
    if " OR " in expr:
        results = [classify(e) for e in expr.split(" OR ")]
        for level in ("allow", "review", "deny", "unknown"):
            if level in results:
                return level
    if " AND " in expr:
        results = [classify(e) for e in expr.split(" AND ")]
        for level in ("unknown", "deny", "review", "allow"):
            if level in results:
                return level
    lic = expr.strip("() ")
    if lic in ALLOW:
        return "allow"
    if lic in REVIEW:
        return "review"
    if lic in DENY:
        return "deny"
    return "unknown"

for name, expr in deps:
    print(f"{name:13s} {expr:28s} -> {classify(expr)}")
```

실행 결과다.

```
requests      Apache-2.0                   -> allow
numpy         BSD-3-Clause                 -> allow
some-gui-lib  GPL-3.0-only                 -> deny
dual-lib      MIT OR GPL-2.0-or-later      -> allow
font-pack     OFL-1.1                      -> review
mystery       NOASSERTION                  -> unknown
```

`dual-lib` 은 GPL 이 섞여 있지만 `OR` 이므로 MIT 를 골라 쓸 수 있다. `mystery` 처럼 라이선스를 모르는 패키지는 "허용"으로 처리하면 안 된다. 모르는 것은 금지보다 위험하다. 금지는 적어도 알고 있다.

여기서 정책 분류는 예시다. 어떤 라이선스를 허용할지는 제품을 어떻게 배포하는지(SaaS, 설치형, 임베디드)와 회사 정책에 따라 달라진다.

## 현업에서는

- 많은 회사가 CI 에서 SBOM(소프트웨어 자재 명세서)을 만들고 라이선스를 검사한다. SPDX 와 CycloneDX 가 대표적인 SBOM 형식이다. 보안 취약점 추적에도 같은 SBOM 을 쓴다.
- 컨테이너 이미지는 OS 패키지까지 포함해 배포하는 것이다. 고객에게 이미지를 넘기면 그 안의 GPL 패키지에 대한 소스 제공 의무도 생각해야 한다. 홈랩 k3s 처럼 공개 이미지를 내려받아 자기만 쓰는 경우는 배포가 아니어서 사정이 다르다.
- 오픈소스 프로젝트에 기여할 때 CLA(기여자 라이선스 계약)나 DCO(`git commit -s` 로 서명하는 Developer Certificate of Origin)를 요구하는 경우가 있다. 회사 업무 시간에 쓴 코드는 저작권이 회사에 있을 수 있으니 사내 규정을 먼저 확인한다.
- 새 프로젝트를 공개할 때는 저장소 루트에 `LICENSE` 파일을 두고, 패키지 메타데이터에 SPDX 식별자를 적는다. 라이선스를 직접 만들지 말고 OSI 승인 라이선스 중에서 고른다.
- 생성형 AI 가 만든 코드에도 학습 데이터 출처와 라이선스 문제가 거론된다. 회사 정책이 있으면 따른다.

## 확인 문제

1. GitHub 에 공개된 저장소에 라이선스 파일이 없다. 이 코드를 내 제품에 복사해도 되는가?
2. "비상업적 용도로만 사용 가능"한 라이선스가 OSI 의 오픈소스 정의를 만족하지 못하는 이유는?
3. GPL 라이브러리를 수정해 사내 서버에서만 쓰는 경우와, AGPL 라이브러리를 수정해 외부 사용자에게 웹 서비스로 제공하는 경우의 차이는?
4. SPDX 식 `MIT OR Apache-2.0` 과 `MIT AND Apache-2.0` 의 의미 차이는?

### 풀이

1. 기본적으로 안 된다. 라이선스가 없으면 저작권자가 권리를 모두 가지므로 별도 허락이 필요하다.
2. OSD 는 사용 분야(field of endeavor)에 대한 차별을 금지하는데, 상업적 사용 금지는 특정 분야를 배제한다.
3. GPL 은 배포가 없으면 소스 공개 의무가 생기지 않는 것이 일반적 해석이다. AGPL 은 네트워크로 상호작용하는 사용자에게 수정된 소스를 제공할 의무가 있다.
4. OR 는 둘 중 하나를 골라 그 조건만 지키면 되고, AND 는 두 라이선스 조건을 모두 지켜야 한다.

## 더 읽을거리 (References)

- Open Source Initiative, [The Open Source Definition](https://opensource.org/osd)
- SPDX, [SPDX License List](https://spdx.org/licenses/)
- Apache Software Foundation, [Apache License v2.0 and GPL Compatibility](https://www.apache.org/licenses/GPL-compatibility.html)
- GitHub Docs, [Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
