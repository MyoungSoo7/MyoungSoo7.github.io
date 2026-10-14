---
layout: post
title: "리눅스마스터 2급 2026~2027 시험일정과 공부 방법 — 2027년 버전 변경까지"
date: 2026-10-15 00:54:07 +0900
categories: [linux, certification]
tags: [linux-master, 리눅스마스터, kait, rocky-linux, certification, study-plan]
---

리눅스마스터 2급은 한국정보통신진흥협회(KAIT)가 시행하는 공인민간자격이다. 이 글은 **2026년 남은 일정**과 **2027년에 바뀌는 것**(출제 리눅스 버전, 검정수수료)을 KAIT 공식 공고 기준으로 정리하고, 시험 구성에 맞춘 공부 방법을 제안한다. 모든 일정·수치는 2026-10-15 에 [KAIT 자격검정 사이트](https://www.ihd.or.kr/guidecert1.do)에서 확인한 값이다. 일정은 바뀔 수 있으니 접수 전에 반드시 원문을 다시 확인하자.

## 한눈에 보기

- **지금 바로**: 2026년 마지막 회차(2604회) **2급 1차 접수 마감은 2026-10-16(금)**, 시험은 **10-31(토) 14:00 온라인**이다.
- **2027년 일정은 아직 발표 전**이다. KAIT 는 "2027년 리눅스마스터 정기검정 시험일정 등은 2026년 10월 말 공지될 예정" 이라고 밝혔다 ([검정수수료 인상안내, 2026-10-02](https://www.ihd.or.kr/noticeview.do?board_no=6121)).
- **2027년부터 출제 버전이 바뀐다**: 필기는 커널 5.x 이상(RHEL/Rocky Linux 9, Ubuntu 22.04 이상) ([버전변경 안내, 2026-05-15](https://www.ihd.or.kr/noticeview.do?board_no=6052)).
- **2027-01-01 시행분부터 수수료가 오른다**: 2급 1차 22,000 → 33,000원, 2급 2차 44,000 → 55,000원. 2701회는 **2026-12-28 접수분부터** 인상 금액이 적용된다 ([같은 공지](https://www.ihd.or.kr/noticeview.do?board_no=6121)).

## 시험 구성

[종목 안내 페이지](https://www.ihd.or.kr/introducesubject1.do) 기준이다.

| 차수 | 방식 | 문항 | 시간 | 합격 기준 | 응시 지역 |
|---|---|---|---|---|---|
| 2급 1차 | 온라인(비대면) 객관식 사지선다 | 50 | 60분 | 60점 이상 | 온라인 접속 가능한 모든 지역 |
| 2급 2차 | 필기 사지선다 | 80 | 100분 | 60점 이상, **과목당 40% 미만 과락** | 서울·부산·대구·광주·대전·인천·수원·제주 |

- 1차는 응시 제한이 없다. 2차는 **1차 합격자만**, 성적공개일 기준 **2년 안에** 응시할 수 있다.
- 2급 2차의 과목은 세 개다: **리눅스 일반**, **리눅스 운영 및 관리**, **리눅스 활용**. 과락이 있으니 한 과목을 버리는 전략은 통하지 않는다.

### 2급 1차는 "지정 시각 실시간 감독" 온라인 시험이다

2602회부터 방식이 바뀌었다 ([온라인시험 방식 변경안내, 2026-02-24](https://www.ihd.or.kr/noticeview.do?board_no=5950)).

- 기존: 지정 기간(10일) 안에 아무 때나 응시
- 변경: **지정된 토요일 14시**에 온라인 감독관이 실시간으로 감독하는 비대면 시험

준비물과 환경 조건이 까다롭다 ([응시 방법 및 유의사항, 2026-04-13](https://www.ihd.or.kr/noticeview.do?board_no=5980)).

- PC/노트북(크롬), **마이크 있는 웹캠**, 원격 감독용 **스마트폰**이 필요하다. 듀얼 모니터는 쓸 수 없다.
- 1인 1실 공간(자택·기숙사·회사 회의실)에서 응시해야 한다. 사무실·도서관 열람실·카페·PC방·스터디룸은 안 된다.
- **사전 환경 점검**을 시험 전에 끝내야 하고, 13:30 까지 입장해야 한다. 입실 완료 시간(13:50) 이후에는 응시할 수 없다.
- 리눅스마스터 2급 1차는 시험 중 **종이를 사용할 수 없다**.

시험 공부만큼 **응시 환경 점검**이 중요하다. 네트워크 끊김, 카메라 위치 이탈도 부정행위로 간주될 수 있다고 공지돼 있다.

## 2026년 일정 (2급)

[KAIT 정기검정 일정](https://www.ihd.or.kr/guidecert1.do) 원문 그대로다.

| 회차 | 차수 | 접수 | 시험 | 합격 발표 |
|---|---|---|---|---|
| 2601회 | 1차 | 01.26 ~ 02.04 | 01.27 ~ 02.05 | 시험 종료 즉시 |
| 2601회 | 2차 | 01.27 ~ 02.06 | 03.14(토) | 04.03 |
| 2602회 | 1차 | 04.06 ~ 04.17 | 05.02(토) | 시험 종료 즉시 |
| 2602회 | 2차 | 04.28 ~ 05.08 | 06.13(토) | 07.03 |
| 2603회 | 1차 | 07.06 ~ 07.17 | 08.01(토) | 08.05 |
| 2603회 | 2차 | 07.28 ~ 08.07 | 09.12(토) | 10.02 |
| **2604회** | **1차** | **10.05 ~ 10.16** | **10.31(토)** | **11.04** |
| **2604회** | **2차** | **10.27 ~ 11.06** | **12.12(토)** | **12.31** |

시험 시간은 2급 1차 14:00~15:00(60분), 2급 2차 14:00~15:40(100분)이다. 수험표는 시험일 5일 전부터 출력할 수 있다.

남은 2604회의 흐름을 보면, 1차(10/31) 합격 발표가 11/04 인데 2차 접수는 10/27 부터 11/06 까지다. 1차 결과를 확인하고 2차를 접수할 시간이 11/04~11/06 사흘뿐이니 날짜를 미리 달력에 넣어 두자.

## 2027년 일정과 바뀌는 것

### 일정: 10월 말 공지 예정

이 글을 쓰는 시점(2026-10-15)에 2027년 정기검정 일정은 **공개되지 않았다**. KAIT 는 10월 말에 공지할 예정이라고 했다. 2026년 2급은 1차가 1·4·7·10월 무렵, 2차가 3·6·9·12월 무렵에 있었지만, 이는 참고일 뿐 2027년이 같다는 보장은 없다. 공지가 나오면 [정기검정 일정 페이지](https://www.ihd.or.kr/guidecert1.do)를 확인하자.

### 출제 리눅스 버전

[2027년도 출제문제 버전변경 안내](https://www.ihd.or.kr/noticeview.do?board_no=6052) 원문의 표다.

| 구분 | 리눅스 커널 버전 |
|---|---|
| 필기 | 커널 5.x 이상 (레드햇 계열: RHEL/Rocky Linux 9, 데비안 계열: Ubuntu 22.04 이상) |
| 실기 | Rocky Linux 9.7 이상 |

공지에는 "2027년 1급 2차 시험버전이며, 매년 변경될 수 있습니다" 라는 주석이 붙어 있다. 2급은 실기가 없으니 2급 응시자에게 해당하는 것은 **필기 행**이다.

참고로 2026년 시험 대비용으로 KAIT 가 게시한 [「리눅스마스터 2급 1차 핵심 개념 가이드」](https://www.ihd.or.kr/noticeview.do?board_no=6119)(2026-09-28)는 **Rocky Linux 8 기준**으로 정리된 자료다. 따라서:

- **2026년 10/31·12/12 응시자**: 공식 가이드처럼 Rocky Linux 8 기준으로 공부하면 된다.
- **2027년 응시자**: RHEL/Rocky 9 와 Ubuntu 22.04 이후의 변화를 추가로 챙겨야 한다. 예를 들어 RHEL 9 부터 NetworkManager 는 새 연결 프로필을 `/etc/sysconfig/network-scripts/` 의 ifcfg 형식이 아니라 `/etc/NetworkManager/system-connections/` 의 **keyfile 형식**으로 저장하고, ifcfg 형식은 사용 중단 예정(deprecated) 상태다 ([Red Hat, Considerations in adopting RHEL 9 — Networking](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/considerations_in_adopting_rhel_9/assembly_networking_considerations-in-adopting-rhel-9)). Ubuntu 계열은 [netplan](https://netplan.readthedocs.io/en/stable/) 으로 네트워크를 설정한다. 오래된 수험서의 "설정 파일 경로" 문제는 이 지점에서 답이 바뀔 수 있다.

### 검정수수료

| 구분 | 인상 전 | 인상 후 (2027-01-01 시행) |
|---|---|---|
| 2급 1차 | 22,000원 | 33,000원 |
| 2급 2차 | 44,000원 | 55,000원 |
| 1급 1차 | 55,000원 | 60,000원 |
| 1급 2차 | 77,000원 | 100,000원 |

출처: [리눅스마스터 검정수수료 인상안내](https://www.ihd.or.kr/noticeview.do?board_no=6121). 2701회 접수는 2026-12-28 부터 인상 금액이 일괄 적용된다. 비용만 보면 2026년 2604회에 1·2차를 끝내는 쪽이 2급 기준 22,000원 싸다.

## 공부 방법

### 1. 범위는 공식 출제 기준 표에서 시작한다

[종목 안내](https://www.ihd.or.kr/introducesubject1.do)의 2급 검정 내용을 그대로 체크리스트로 쓴다.

| 과목 | 검정 항목 | 검정 내용 |
|---|---|---|
| 리눅스 일반 | 리눅스의 이해 | 개요, 역사, 철학 |
| | 리눅스 설치 | 기본 설치 및 유형, 파티션과 파일 시스템, Boot Manager |
| | 기본 명령어 | 사용자 생성 및 계정 관리, 디렉터리 및 파일, 기타 명령어 |
| 리눅스 운영 및 관리 | 파일 시스템 관련 명령어 | 권한 및 그룹 설정, 파일 시스템의 관리 |
| | Shell | 개념 및 종류, 환경 설정 |
| | 프로세스 관리 | 개념 및 유형, 프로세스 Utility |
| | 에디터 | 에디터의 종류, 에디터 활용 |
| | 소프트웨어 설치 | 개념 및 사용법, 설치 및 삭제 |
| | 장치 설정 | 주변장치 연결 및 설정, 활용 |
| 리눅스 활용 | X 윈도 | 개념 및 사용법, 활용 |
| | 인터넷 활용 | 네트워크 개념, 인터넷 서비스 종류와 설정 |
| | 응용분야 | 기술동향, 활용기술 |

2차는 과목당 40% 과락이 있으므로, 세 과목 모두 최소선을 넘는 것이 먼저다. 특히 "리눅스 활용"(X 윈도, 네트워크, 기술동향)은 실무에서 덜 쓰는 내용이 섞여 있어 실무자가 오히려 과락을 맞기 쉬운 과목이다.

### 2. 가상머신 하나 띄워 놓고 손으로 친다

사지선다라도 문제의 상당수는 "이 명령의 결과는?", "이 옵션의 뜻은?" 꼴로 나온다고 보고 준비하는 게 안전하다. 외운 것보다 쳐 본 것이 오래 간다.

- 2026년 응시: Rocky Linux 8 VM
- 2027년 응시: Rocky Linux 9 VM + Ubuntu 22.04 이후 VM(또는 컨테이너)

공식 문서는 [Rocky Linux 문서](https://docs.rockylinux.org/), 명령어 옵션은 [man7.org 의 Linux man-pages](https://man7.org/linux/man-pages/index.html)와 [GNU Coreutils 매뉴얼](https://www.gnu.org/software/coreutils/manual/coreutils.html), 셸은 [GNU Bash 매뉴얼](https://www.gnu.org/software/bash/manual/bash.html), 디렉터리 구조는 [Filesystem Hierarchy Standard 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs-3.0.html)을 기준으로 삼는다. 수험서끼리 설명이 엇갈리면 이 1차 문서가 정답이다.

출제 기준 항목별로 직접 쳐 볼 것의 예:

```bash
# 사용자·그룹 (기본 명령어 / 권한 및 그룹 설정)
useradd -m -s /bin/bash kim && passwd kim
usermod -aG wheel kim; id kim; grep kim /etc/passwd /etc/shadow /etc/group
chage -l kim

# 권한 (8진수·기호 표기, 특수 권한, umask)
touch f; chmod 754 f; ls -l f; chmod u+s,g+s,o+t f; ls -l f
umask; umask 027; touch g; ls -l g

# 파일 시스템 (파티션·마운트·용량)
lsblk; df -hT; du -sh /var/log
cat /etc/fstab; mount | grep ' / '

# 프로세스
ps -ef | head; ps aux --sort=-%mem | head
kill -l; nice -n 10 sleep 300 & renice -n 5 -p $!; jobs; fg

# 소프트웨어 설치 (RPM/DNF 와 DEB/APT 를 함께)
rpm -qa | head; rpm -qi bash; dnf info vim-enhanced
# Ubuntu: dpkg -l | head; apt show vim

# 셸 환경
echo $SHELL $PATH; cat ~/.bashrc; alias ll='ls -l'; history | tail
```

`vi`/`vim` 은 따로 시간을 잡는다. 모드 전환, `:wq`/`:q!`, 검색(`/`), 치환(`:%s/old/new/g`), 줄 번호(`:set nu`) 같은 기본 조작이 에디터 항목에 해당한다.

### 3. 일정별 학습 계획 예시

**2604회(1차 10/31, 2차 12/12) 응시자 — 남은 기간 기준**

| 기간 | 할 일 |
|---|---|
| 10/15 ~ 10/16 | 1차 접수 (마감 10/16). 웹캠·스마트폰·응시 공간 확보 확인 |
| 10/17 ~ 10/29 | 공식 [핵심 개념 가이드](https://www.ihd.or.kr/noticeview.do?board_no=6119) 1회독, VM 에서 명령어 실습, 출제 기준 표 체크 |
| 10/30 ~ 10/31 정오 | **사전 환경 점검 완료** (10/31 정오 마감) |
| 10/31 14:00 | 1차 응시 |
| 11/04 ~ 11/06 | 합격 확인 후 2차 접수 (마감 11/06) |
| 11/07 ~ 12/11 | 2차 대비: 과목별 약점 보강, 특히 "리눅스 활용" 과락 방지 |
| 12/12 | 2차 응시 |

**2027년 응시자 — 10월 말 일정 공지 전후로**

1. **지금 ~ 일정 공지**: Rocky Linux 9 VM 을 만들고 위 실습을 9 버전으로 반복한다. 8 과 9 에서 결과가 다른 부분(네트워크 설정 방식 등)은 따로 노트한다.
2. **일정 공지 후**: 첫 1차 회차를 목표로 6~8주 계획을 세운다. 1주차 리눅스 일반, 2~4주차 운영 및 관리, 5주차 리눅스 활용, 6주차 이후 전 범위 복습.
3. **수수료 인상 전 응시를 원하면**: 2026년 2604회가 마지막 기회다.

### 4. 문제 공개 상황을 알고 기출에 기대지 않는다

- KAIT 는 2급 1차 비대면 시험 안내에서 "2022년부터 본 자격종목은 문제공개가 되지 않는다" 고 밝혔다 ([10/31 시험 안내](https://www.ihd.or.kr/noticeview.do?board_no=6120)).
- 반면 [문제공개 게시판](https://www.ihd.or.kr/guidequestion.do)에는 2급 2차의 **모범답안(가답안)** 파일이 회차별로 올라온다(예: 제2603회 2급2차, 2026-09-14).

인터넷의 "복원 기출" 은 정확성이 보장되지 않고, 2027년부터는 출제 버전이 바뀌므로 오래된 문제의 정답이 지금과 다를 수 있다. 기출은 **유형 파악용**으로만 쓰고, 정답은 위의 1차 문서로 확인하는 습관을 들이자.

## 접수 전 체크리스트

- [ ] [정기검정 일정](https://www.ihd.or.kr/guidecert1.do)에서 회차·접수 기간 재확인
- [ ] 2027년 응시라면 10월 말 일정 공지와 인상된 수수료 확인
- [ ] (1차) 마이크 있는 웹캠, 스마트폰 거치, 1인 1실 공간, 안정적인 네트워크
- [ ] (1차) 시험 전 사전 환경 점검 완료, 시험일 13:30 까지 입장
- [ ] (2차) 1차 성적공개일로부터 2년 안인지 확인, 응시 지역(8개 시) 선택
- [ ] 연기·환불: 100% 연기/환불은 입금부터 시험일 10일 전까지 ([10/31 시험 안내](https://www.ihd.or.kr/noticeview.do?board_no=6120))

## References

- KAIT 자격검정, [리눅스마스터 정기검정 일정](https://www.ihd.or.kr/guidecert1.do) (2026-10-15 확인)
- KAIT 자격검정, [리눅스마스터 종목 안내 — 검정과목·합격기준·출제기준·수수료](https://www.ihd.or.kr/introducesubject1.do)
- KAIT 공지, [리눅스마스터 검정수수료 인상안내](https://www.ihd.or.kr/noticeview.do?board_no=6121) (2026-10-02)
- KAIT 공지, [2027년도 리눅스마스터 출제문제 버전변경 안내](https://www.ihd.or.kr/noticeview.do?board_no=6052) (2026-05-15)
- KAIT 공지, [리눅스마스터 2급1차 온라인시험 방식 변경안내(제2602회차부터)](https://www.ihd.or.kr/noticeview.do?board_no=5950) (2026-02-24)
- KAIT 공지, [온라인시험(비대면) 응시 방법 및 유의사항 안내](https://www.ihd.or.kr/noticeview.do?board_no=5980) (2026-04-13)
- KAIT 공지, [26년 10월 31일 리눅스마스터 2급 1차 온라인(비대면) 안내](https://www.ihd.or.kr/noticeview.do?board_no=6120) (2026-10-02)
- KAIT 공지, [리눅스마스터 2급1차 핵심개념 가이드 안내](https://www.ihd.or.kr/noticeview.do?board_no=6119) (2026-09-28)
- KAIT 자격검정, [문제공개](https://www.ihd.or.kr/guidequestion.do)
- Red Hat, [Considerations in adopting RHEL 9 — Chapter 19. Networking](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/considerations_in_adopting_rhel_9/assembly_networking_considerations-in-adopting-rhel-9)
- [Rocky Linux Documentation](https://docs.rockylinux.org/)
- [Linux man-pages (man7.org)](https://man7.org/linux/man-pages/index.html)
- GNU, [Coreutils Manual](https://www.gnu.org/software/coreutils/manual/coreutils.html), [Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html)
- Linux Foundation, [Filesystem Hierarchy Standard 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs-3.0.html)
- [Netplan documentation](https://netplan.readthedocs.io/en/stable/)
