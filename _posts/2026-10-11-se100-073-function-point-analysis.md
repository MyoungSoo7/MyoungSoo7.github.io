---
layout: post
title: "[SE100 #073] 기능 점수(Function Point) 분석"
date: 2026-10-11 17:06:56 +0900
categories: [software-engineering]
tags: [se100, project-management, function-point, software-sizing, cosmic]
---

소프트웨어 공학 100 주제 시리즈의 73번째 글이다. (카테고리: 프로젝트 관리와 추정)

## 한 줄 요약

기능 점수(Function Point, FP)는 소프트웨어의 크기를 **코드 줄 수가 아니라 사용자에게 제공하는 기능의 양**으로 재는 방법이다. 요구사항 단계에서 셀 수 있고, 언어와 무관하다. 대신 "무엇을 하나로 세는가" 에 대한 규칙을 익혀야 한다.

## 왜 필요한가

크기를 모르면 추정도, 생산성 비교도 할 수 없다. 가장 쉬운 크기 척도는 소스 줄 수(SLOC)지만 두 가지 문제가 있다.

1. **코드가 생기기 전에는 셀 수 없다.** 추정이 가장 필요한 시점이 요구사항 단계인데, 그때는 코드가 없다.
2. **언어와 스타일에 따라 달라진다.** 같은 기능이 어셈블리로는 수백 줄, 고수준 언어로는 수십 줄이다. SLOC 로 생산성을 재면 장황한 언어를 쓴 팀이 더 생산적으로 보인다.

FP 는 두 문제를 동시에 피한다. 사용자 관점의 입력·출력·조회·데이터 묶음만 보면 되므로 요구사항 문서로 셀 수 있고, 구현 언어는 계산에 들어가지 않는다.

## 핵심 개념

### 기원과 표준

FP 는 Allan Albrecht 가 1970년대 말 IBM 에서 고안했다. Albrecht 와 John Gaffney 는 1983년 [IEEE TSE 논문](https://doi.org/10.1109/TSE.1983.235271)에서 FP 와 SLOC, 개발 노력 사이의 관계를 검증했다. 이후 국제 기능 점수 사용자 그룹 [IFPUG](https://ifpug.org/) 가 측정 규칙을 *Counting Practices Manual* 로 관리해 왔다. 기능 크기 측정(FSM) 방법은 ISO/IEC 14143 계열이 일반 원칙을 정하고, 개별 방법은 각각 ISO 표준으로 등록되어 있다.

| 방법 | 관리 주체 | ISO 표준 |
|---|---|---|
| IFPUG FPA | IFPUG | ISO/IEC 20926 |
| NESMA FPA | [NESMA](https://nesma.org/) | ISO/IEC 24570 |
| COSMIC | [COSMIC](https://cosmic-sizing.org/) | ISO/IEC 19761 |

(ISO 카탈로그는 자동 접근을 막아 두어 여기서는 번호만 적는다.)

### 다섯 가지 기능 유형

아래 정의와 표는 [COCOMO II Model Definition Manual](http://web.archive.org/web/20090206135819/http://sunset.usc.edu:80/csse/research/COCOMOII/cocomo2000.0/CII_modelman2000.0.pdf) 2.2절에서 가져왔다. 이 매뉴얼은 IFPUG 1994년판 정의를 따른다고 밝힌다.

| 유형 | 약어 | 무엇을 세나 |
|---|---|---|
| 내부 논리 파일 | ILF | 시스템이 **유지·관리하는** 논리적 데이터 묶음 |
| 외부 인터페이스 파일 | EIF | 다른 시스템이 관리하고 이 시스템은 **참조만** 하는 데이터 묶음 |
| 외부 입력 | EI | 경계 안으로 들어오는 고유한 데이터·제어 입력 |
| 외부 출력 | EO | 경계 밖으로 나가는 고유한 데이터·제어 출력 |
| 외부 조회 | EQ | 입력이 즉시 출력을 만드는 고유한 입출력 조합 |

```
            ┌──────────────── 측정 경계 ────────────────┐
  사용자 ──EI──▶                                          │
  사용자 ◀──EO──    [ ILF: 회원 ]  [ ILF: 도서 ]           │
  사용자 ──EQ──▶◀─                                        │
            │                         ──참조──▶ [ EIF: 외부 시스템의 데이터 ]
            └────────────────────────────────────────────┘
```

### 복잡도와 가중치

각 기능은 데이터 요소 수(DET)와 참조 파일 수(FTR) 또는 레코드 요소 수(RET)로 낮음·보통·높음 중 하나로 분류한다. 그다음 아래 가중치를 곱해 합하면 **미조정 기능 점수(UFP)** 가 된다(매뉴얼 Table 3).

| 유형 | 낮음 | 보통 | 높음 |
|---|---|---|---|
| ILF | 7 | 10 | 15 |
| EIF | 5 | 7 | 10 |
| EI | 3 | 4 | 6 |
| EO | 4 | 5 | 7 |
| EQ | 3 | 4 | 6 |

예를 들어 ILF/EIF 는 레코드 요소가 2~5개이고 데이터 요소가 20~50개면 '보통' 이다. 데이터 묶음(ILF)의 가중치가 트랜잭션보다 큰 점이 눈에 띈다. 저장 구조를 설계하고 유지하는 비용을 크게 본다는 뜻이다.

### 조정 계수(VAF) — 그리고 COCOMO II 가 쓰지 않는 이유

전통적 절차는 UFP 에 14개 일반 시스템 특성(분산 처리, 성능, 재사용성 등)의 영향도를 반영한다. COCOMO II 매뉴얼의 설명에 따르면 각 특성은 0.00~0.05 로 평가하고, 14개를 더한 값에 0.65 를 더해 0.65~1.35 범위의 조정 계수를 만든다. 흔히 각 특성을 0~5 로 매긴 합(TDI)으로 `VAF = 0.65 + 0.01 × TDI` 라고 쓰는 것과 같은 식이다.

COCOMO II 는 이 조정을 **쓰지 않고 UFP 만 쓴다**. 매뉴얼은 이유를 이렇게 든다. 각 특성의 영향이 최대 5% 로 묶이는데, 예컨대 재사용의 영향이 5% 를 넘지 못한다는 것은 COCOMO 의 경험과 맞지 않는다. 그래서 재사용·분산 같은 효과는 COCOMO 의 비용 동인으로 반영한다(SE100 #072 에서 다뤘다).

### FP 에서 SLOC 로 — 백파이어링

COCOMO II 는 UFP 를 언어별 환산표로 SLOC 로 바꾼다. 매뉴얼 Table 4 의 값 몇 개를 보면 C 128, C++ 55, Java 53, Visual Basic 5.0 은 29 SLOC/UFP 다. 매뉴얼은 이 비율이 Capers Jones(1996)의 자료라고 밝히고, **자기 조직의 비율을 직접 구하라**고 권한다.

### COSMIC — 데이터 이동을 세는 2세대 방법

[COSMIC 방법](https://cosmic-sizing.org/cosmic-sizing/intro/)은 기능 프로세스 안의 **데이터 이동**만 센다. 이동 유형은 넷이다.

| 이동 | 뜻 | 크기 |
|---|---|---|
| Entry | 기능 사용자 → 경계 안 기능 프로세스로 데이터 묶음 이동 | 1 CFP |
| Exit | 기능 프로세스 → 경계 밖 기능 사용자 | 1 CFP |
| Read | 영속 저장소 → 기능 프로세스 | 1 CFP |
| Write | 기능 프로세스 → 영속 저장소 | 1 CFP |

복잡도 등급표가 없다. 그래서 측정자 간 주관이 끼어들 여지가 줄고, 임베디드·실시간 소프트웨어에도 같은 규칙을 적용할 수 있다.

## 예제

도서 대출 시스템의 요구사항에서 기능을 식별했다고 하자.

```python
# UFP 계산 — 가중치는 COCOMO II 매뉴얼 Table 3 (IFPUG 1994 정의를 따름)
W = {"ILF": (7, 10, 15), "EIF": (5, 7, 10), "EI": (3, 4, 6),
     "EO": (4, 5, 7), "EQ": (3, 4, 6)}
LV = {"low": 0, "avg": 1, "high": 2}

items = [
    ("ILF", "회원", "low"), ("ILF", "도서", "avg"), ("ILF", "대출", "avg"),
    ("EIF", "외부 결제 이력", "low"),
    ("EI", "회원 등록", "avg"), ("EI", "도서 등록", "avg"),
    ("EI", "대출 처리", "high"), ("EI", "반납 처리", "avg"),
    ("EO", "연체료 고지서", "avg"), ("EO", "월간 대출 통계", "high"),
    ("EQ", "도서 검색", "low"), ("EQ", "내 대출 조회", "low"),
]
ufp = sum(W[t][LV[lv]] for t, _, lv in items)
tdi = 3 * 14                      # 14개 특성을 모두 '보통(3)' 으로 가정
vaf = 0.65 + 0.01 * tdi
print(f"UFP={ufp}  VAF={vaf:.2f}  AFP={ufp * vaf:.1f}  Java≈{ufp * 53} SLOC")
```

실행 결과:

```
UFP=68  VAF=1.07  AFP=72.8  Java≈3604 SLOC
```

68 UFP 라는 숫자 자체보다 **식별 목록**이 더 쓸모 있다. "월간 대출 통계가 '높음' 인 이유는 참조 파일이 4개이기 때문" 같은 근거가 남기 때문이다. 범위 협상을 할 때 "통계 출력을 빼면 7점이 줄어든다" 처럼 기능 단위로 이야기할 수 있다.

### 셀 때 자주 틀리는 것

| 상황 | 올바른 처리 |
|---|---|
| 같은 화면의 저장·수정·삭제 | 처리 논리가 다르면 각각 별개의 EI |
| 목록 화면 + 상세 화면 | 계산·파생 데이터가 없으면 EQ, 있으면 EO |
| 데이터베이스 테이블 = ILF? | 아니다. 사용자가 인식하는 **논리적** 묶음 단위로 센다 |
| 로그인 | 보안 기능은 사용자 요구라면 센다. 프레임워크가 주는 것이면 경계 밖 |
| 기술 작업(캐시, 리팩터링) | 기능 크기에 포함되지 않는다. 노력 추정에서 따로 다룬다 |

## 흔한 오해와 함정

- **"FP 는 노력이다."** FP 는 **크기**다. 노력은 크기에 생산성(조직의 실측 값)을 곱해서 얻는다. FP 가 같아도 팀과 기술에 따라 노력은 크게 다르다.
- **"측정자가 달라도 같은 숫자가 나온다."** 규칙을 훈련받지 않으면 경계와 논리 파일을 다르게 그어 차이가 커진다. 그래서 인증 제도와 상세한 사례집이 있다.
- **"FP 는 낡은 방법이다."** 공공 발주나 아웃소싱 계약처럼 크기를 객관적으로 합의해야 하는 곳에서는 여전히 표준으로 쓰인다. 기능 단위로 범위를 협상하는 도구로도 유용하다.
- **"비기능 요구사항도 FP 에 들어간다."** 성능·보안 같은 품질 요구는 기능 크기와 별도로 다룬다. 전통 방식의 VAF 가 일부를 반영하지만 COCOMO II 처럼 아예 비용 동인으로 빼는 접근도 있다.
- **"백파이어링 비율은 정확하다."** 언어별 SLOC/UFP 는 평균값이고 조직마다 다르다. 매뉴얼도 자기 비율을 구하라고 권한다.

## 확인 문제

1. SLOC 대신 FP 를 쓰면 해결되는 두 가지 문제는?
2. ILF 와 EIF 의 차이를 설명하라.
3. 평균 복잡도의 ILF 2개, EI 3개, 낮은 EQ 2개의 UFP 는?
4. COCOMO II 가 FP 의 조정 계수(VAF)를 쓰지 않는 이유는?
5. COSMIC 이 세는 네 가지 데이터 이동과 단위는?

### 풀이

1. 코드가 생기기 전(요구사항 단계)에 셀 수 있고, 구현 언어와 스타일에 따라 크기가 달라지지 않는다.
2. ILF 는 측정 대상 시스템이 유지·관리하는 논리 데이터 묶음이고, EIF 는 다른 시스템이 관리하며 이 시스템은 참조만 하는 묶음이다.
3. 2×10 + 3×4 + 2×3 = 20 + 12 + 6 = 38 UFP.
4. 각 특성의 영향이 최대 5% 로 제한되는데, 재사용 같은 효과가 5% 에 묶인다는 것이 COCOMO 의 경험과 맞지 않기 때문이다. 대신 비용 동인과 규모 인자로 반영한다.
5. Entry, Exit, Read, Write. 각 데이터 이동이 1 CFP(COSMIC Function Point)다.

## 더 읽을거리 (References)

- Allan J. Albrecht, John E. Gaffney, [Software Function, Source Lines of Code, and Development Effort Prediction: A Software Science Validation](https://doi.org/10.1109/TSE.1983.235271), *IEEE Transactions on Software Engineering* SE-9(6), 1983
- USC Center for Software Engineering, [COCOMO II Model Definition Manual v2.1](http://web.archive.org/web/20090206135819/http://sunset.usc.edu:80/csse/research/COCOMOII/cocomo2000.0/CII_modelman2000.0.pdf), 2.2–2.3절 (인터넷 아카이브 사본)
- [IFPUG — International Function Point Users Group](https://ifpug.org/)
- [COSMIC — Introduction to the COSMIC Software Sizing Methodology](https://cosmic-sizing.org/cosmic-sizing/intro/)
- [NESMA](https://nesma.org/)
