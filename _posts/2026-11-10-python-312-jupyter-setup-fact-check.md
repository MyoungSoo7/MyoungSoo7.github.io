---
layout: post
title: "Python 3.12 + Jupyter 설치 가이드, 2026년 11월 기준으로 다시 읽기 — 그대로 따라 하면 막히는 세 군데"
date: 2026-11-10 22:10:00 +0900
categories: [python, devenv]
tags: [python, jupyter, venv, pep-668, pymanager, windows, macos, ubuntu]
---

패스트캠퍼스 강의 혜택자료로 배포된 「Python 3.11/3.12 & Jupyter — OS별 환경 구축 완벽 가이드」(이한울)를 받았다. 10쪽짜리 슬라이드로, Windows·macOS·Ubuntu 에서 파이썬을 깔고 `pip install notebook` → `jupyter notebook` 으로 첫 셀을 돌리기까지를 다룬다.

입문자에게 필요한 흐름은 다 들어 있다. 다만 파이썬 배포 방식이 최근 1년 사이 꽤 바뀌어서, **2026년 11월에 그대로 따라 하면 막히거나 위험한 지점이 세 군데** 있다. 이 글은 가이드의 흐름을 요약하고, 각 단계를 공식 문서와 대조해 고친 판을 정리한 것이다. (원본 PDF 는 강의 자료라 여기 다시 올리지 않는다. 원문은 해당 강의에서 받을 수 있다.)

## 1. 가이드의 뼈대 — 요약

| 단계 | Windows | macOS | Ubuntu |
| --- | --- | --- | --- |
| 파이썬 설치 | python.org 설치 파일, **Add python.exe to PATH 체크** | python.org `universal2` .pkg | `apt` + deadsnakes PPA 로 `python3.12` |
| 확인 | `python --version` | `python3 --version` | — |
| 가상환경 | (없음) | (없음) | `python3.12 -m venv .venv` → `source .venv/bin/activate` |
| Jupyter | `pip install notebook` → `jupyter notebook` | `pip3 install notebook` (권한 오류 시 `sudo`) | venv 안에서 `pip install notebook` |
| 검증 | 새 노트북에서 `import sys; print(sys.version)` 실행 | 같음 | 같음 |

FAQ 세 개도 실려 있다. 명령어가 안 먹히면 PATH 체크를 빠뜨린 것이고, 노란 pip WARNING 은 대개 무시해도 된다. 3.11 과 3.12 중에서는 "3.12가 최신이라 호환성이 높으니 충돌 날 때만 3.11"을 쓰라고 한다.

검증 단계(`sys.version` 출력)와 "Linux 에선 가상환경을 쓰라"는 조언은 지금도 그대로 맞다. 고칠 곳은 아래 셋이다.

## 2. 막히는 곳 ① — "최신 3.12 설치 파일을 받으세요"는 이제 불가능하다

가이드는 python.org 에서 "최신 3.11.x 혹은 3.12.x" 설치 파일을 받으라고 한다. 그런데 **3.12 는 2025년 4월 3.12.10 을 끝으로 설치 파일 배포가 끝났다.**

- 3.12 일정표(PEP 693)에 따르면 3.12.10(2025-04-08)이 "바이너리 설치 파일이 있는 마지막 버그픽스 릴리스"다. 이후 3.12.11~3.12.16 은 **소스 전용 보안 릴리스**이고, 지원은 2028년 10월까지 이어진다([PEP 693](https://peps.python.org/pep-0693/)).
- 3.12.11 이후 릴리스 페이지에도 "binary installers are no longer provided"라고 적혀 있다([python.org — Python 3.12.13](https://www.python.org/downloads/release/python-31213/)).
- Windows 새 설치 관리자도 마찬가지다. `py install 3.12` 를 하면 3.12.10 이 깔린다. 코어 개발자는 "보안 전용 단계의 릴리스는 빌드해서 배포하지 않는다, 예전부터 그랬다"고 답했다([python/pymanager #230](https://github.com/python/pymanager/issues/230)).

FAQ 의 "3.12가 최신"도 더는 맞지 않는다. python.org 의 현재 표에서 3.15 와 3.14 가 bugfix 단계이고, 3.13·3.12·3.11 은 security 단계다([python.org/downloads](https://www.python.org/downloads/)).

**고친 판:** 강의나 라이브러리가 3.12 를 요구하지 않는다면 bugfix 단계 버전(3.14 이상)을 쓴다. 3.12 가 꼭 필요하면 python.org 의 3.12.10 설치 파일이나 OS 패키지(Ubuntu 24.04 의 기본 3.12, 아래 ③)를 쓴다. 이때 "보안 패치가 반영된 바이너리는 공식 채널에서 나오지 않는다"는 점은 알고 쓴다.

### Windows 는 설치 방식 자체가 바뀌었다

가이드의 Windows 스크린숏을 자세히 보면 python.org 페이지 맨 위에 "Python install manager"가 이미 떠 있다. PEP 773 으로 Windows 설치 경로가 **Python Install Manager(`py`)** 하나로 통합됐다. 예전 `.exe` 설치 파일은 단계적으로 폐지되고 있다([PEP 773](https://peps.python.org/pep-0773/), [Using Python on Windows](https://docs.python.org/3/using/windows.html)).

```text
py install 3.14        # 또는 py install 3.12 (→ 3.12.10)
py list                # 설치된 런타임 확인
py -V:3.12 --version   # 특정 버전 실행
```

공식 문서도 "기존에 설치한 파이썬이 있거나 `PATH` 를 손댔다면 그 설정을 제거하거나 되돌려야 할 수 있다"고 안내한다. 즉 가이드 FAQ 의 "PATH 체크박스를 꼭 확인하세요"는 **구식 `.exe` 설치 파일에만 해당하는 이야기**다. 새 관리자를 쓸 때는 오히려 예전 PATH 설정이 충돌 원인이 된다.

## 3. 막히는 곳 ② — macOS 에서 `sudo pip3` 는 하지 말 것

가이드의 macOS 슬라이드에는 "권한 문제 발생 시 명령어 앞에 `sudo` 를 붙여주세요"라고 적혀 있다. 이건 따르지 않는 게 맞다.

- 권한 오류의 상당수는 실제로는 **PEP 668 "externally managed environment"** 오류다. 배포판이나 패키지 관리자가 관리하는 파이썬에 `EXTERNALLY-MANAGED` 표식을 넣어 두면, 가상환경 밖에서 pip 가 설치하는 걸 막는다. 우회 플래그 `--break-system-packages` 는 "위험하다는 뉘앙스를 가져야 한다"고 사양에 적혀 있다([PEP 668](https://peps.python.org/pep-0668/)). Homebrew 파이썬도 이 표식을 단다.
- `sudo` 는 실행 계정만 바꿀 뿐 이 표식을 지나가지 못한다. 표식이 없는 파이썬이라면 시스템 경로에 root 소유 파일을 흩뿌리게 된다. 둘 다 나쁘다.

**고친 판:** Linux 슬라이드에만 있는 가상환경 단계를 **모든 OS 에 똑같이** 적용한다. 공식 튜토리얼도 프로젝트별 가상환경을 기본으로 안내한다([Python Tutorial — Virtual Environments and Packages](https://docs.python.org/3/tutorial/venv.html)).

```text
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install notebook
jupyter notebook

# Windows (PowerShell)
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install notebook
jupyter notebook
```

`pip` 대신 `python -m pip` 를 쓰면 "지금 켜진 그 파이썬"의 pip 가 확실히 불린다. 가이드에서 macOS 만 `pip3` 를 따로 쓰던 혼란도 사라진다.

## 4. 막히는 곳 ③ — Ubuntu 24.04 에서 deadsnakes PPA 는 필요 없다

가이드의 Linux 슬라이드는 `software-properties-common` → `add-apt-repository ppa:deadsnakes/ppa` → `apt install python3.12 python3.12-venv` 순서다.

- Ubuntu 24.04(noble)의 기본 `python3` 가 **이미 3.12(3.12.3)**다([packages.ubuntu.com — python3 in noble](https://packages.ubuntu.com/noble/python3)).
- deadsnakes 는 공식 저장소가 아니다. PPA 설명에 noble 용으로는 **3.12 를 제공하지 않는다**고 적혀 있다(우분투 본 저장소가 제공하므로). 또 "보안 문제에 대한 적시 업데이트를 보장하지 않으니 운영 서버에선 본인 책임"이라는 면책도 붙어 있다([deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa)).

**고친 판 (Ubuntu 24.04):**

```text
sudo apt update
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install notebook
```

PPA 는 "배포판 기본과 **다른** 버전이 꼭 필요할 때"만 쓰는 선택지다. 그 경우에도 위 면책 문구를 감안해야 한다.

## 5. Jupyter 쪽 — 가이드 그대로 써도 된다, 선택지 하나만 추가

`pip install notebook` → `jupyter notebook` 은 Project Jupyter 공식 설치 안내와 같다. 공식 안내는 다음 세대 인터페이스인 JupyterLab(`pip install jupyterlab` → `jupyter lab`)을 먼저 소개한다([jupyter.org/install](https://jupyter.org/install)). 강의 화면이 클래식 노트북 기준이면 `notebook` 을, 아니면 `jupyterlab` 을 고르면 된다. 둘 다 반드시 **가상환경 안에서** 설치한다.

검증 셀은 가이드 그대로다.

```python
import sys
print("환경 설정 성공!")
print(sys.version)   # 여기 찍힌 버전이 의도한 버전인지 꼭 본다
```

마지막 줄이 가장 중요하다. 여러 버전이 깔린 기계에서는 노트북 커널이 기대와 다른 파이썬으로 뜨는 일이 흔하다. 그래서 "실행됐다"가 아니라 **"내가 고른 버전이 실행됐다"**를 확인해야 한다.

## 6. 정리 — 고친 판 한 장

| 단계 | 2026-11 기준 권장 |
| --- | --- |
| 버전 | 특별한 요구가 없으면 bugfix 단계(3.14+). 3.12 가 필요하면 공식 바이너리는 3.12.10 이 마지막임을 인지 |
| Windows 설치 | Python Install Manager → `py install <버전>` (PATH 체크박스는 구식 설치 파일 얘기) |
| macOS 설치 | python.org 설치 파일 또는 Homebrew. **`sudo pip` 금지** |
| Ubuntu 24.04 | 기본 `python3`(3.12) + `python3-venv`. PPA 불필요 |
| 공통 | 모든 OS 에서 `venv` → `python -m pip install notebook` |
| 검증 | `sys.version` 이 의도한 버전인지 확인 |

## 아직 확인 못 한 것

- 이 글의 명령은 공식 문서와 대조한 것이다. **세 OS 모두에서 직접 처음부터 설치해 보지는 않았다.** 특히 Windows Install Manager 의 실제 화면 흐름은 문서 기준이다.
- 가이드가 3.11/3.12 를 고른 이유(강의 실습 코드나 라이브러리 호환성)는 원본에 적혀 있지 않다. 그래서 "3.14 로 올려도 실습이 그대로 도는지"는 이 글이 보장하지 않는다. 강의 요구 버전이 있다면 그걸 따른다.

## References

- 원본: 이한울, 「Python 3.11/3.12 & Jupyter — OS별 환경 구축 완벽 가이드 (Windows, Mac, Linux)」, FastCampus 강의 혜택자료 (PDF, 10쪽)
- [PEP 693 – Python 3.12 Release Schedule](https://peps.python.org/pep-0693/)
- [python.org — Python 3.12.13 release (No installers)](https://www.python.org/downloads/release/python-31213/)
- [python.org — Download Python (Active Python releases)](https://www.python.org/downloads/)
- [PEP 773 – A Python Installation Manager for Windows](https://peps.python.org/pep-0773/)
- [Python Docs — Using Python on Windows](https://docs.python.org/3/using/windows.html)
- [python/pymanager issue #230 — security-only 릴리스 바이너리 미제공](https://github.com/python/pymanager/issues/230)
- [PEP 668 – Marking Python base environments as "externally managed"](https://peps.python.org/pep-0668/)
- [Python Tutorial — Virtual Environments and Packages](https://docs.python.org/3/tutorial/venv.html)
- [packages.ubuntu.com — python3 in noble](https://packages.ubuntu.com/noble/python3)
- [Launchpad — deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa)
- [Project Jupyter — Installing Jupyter](https://jupyter.org/install)
