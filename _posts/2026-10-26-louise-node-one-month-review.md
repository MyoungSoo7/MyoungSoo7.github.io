---
layout: post
title: "louise 노드 한 달 점검 — 디스크·메모리·로그·파드에 무엇이 남았나"
date: 2026-10-26 05:35:46 +0900
categories: [Infrastructure, Kubernetes, Homelab]
tags: [k3s, kubelet, earlyoom, sysstat, journalctl, crictl, observability]
---

홈랩 k3s 클러스터의 워커 노드 `louise`(2018년식 노트북, 메모리 15Gi)에서 지난 한 달(2026-09-25 ~ 10-26) 동안 무엇이 바뀌었는지 노드 안에 남은 기록으로 정리했다. 별도 대시보드는 쓰지 않았다. 노드 자신의 `journalctl`, `sar`, `crictl` 출력만 근거로 삼았다.

## 결론

- **재부팅은 한 번뿐**이다. 09-15 07:00 에 커널 업데이트(6.8.0-124 → 6.8.0-139)로 재부팅했고, 이후 40일째 무중단이다.
- **메모리 고갈 사고는 없었다.** 커널 OOM-kill, soft lockup, earlyoom 강제 종료가 모두 0건이다.
- **한 달 중 가장 큰 사건은 10-18 저녁의 무선 링크 단절**이다. 이 노드는 무선으로 붙어 있어서 링크가 끊긴 동안 API 서버에 닿지 못했다. 같은 시간대에 프로브 실패와 컨테이너 재시작, 에러 로그가 한꺼번에 몰렸다.
- 디스크는 59% 를 쓰고 있다. 대부분은 k3s 데이터(`/var/lib/rancher`)다.

## 1. 가동 이력

`last -x reboot` 결과, 기간 안에 있는 부팅 기록은 09-15 한 건뿐이다. 그 앞 부팅(06-23)은 84일을 유지했다. 이 노드는 커널 업데이트 말고는 재부팅할 일이 거의 없다는 뜻이다.

## 2. 메모리

현재 값(10-26 02:38): 전체 15Gi, 사용 7.7Gi, buff/cache 7.3Gi, 가용(available) 7.8Gi, 스왑 4.0Gi 중 1.0Gi 사용.

`sar` 일평균은 [sysstat](https://sysstat.github.io/) 보존 기간(`HISTORY=7`) 때문에 최근 7일치만 있다.

| 날짜 | %memused | %commit | 스왑 사용 % |
|---|---|---|---|
| 10-19 | 41.9 | 108.4 | 25.4 |
| 10-20 | 37.5 | 104.8 | 28.7 |
| 10-21 | 35.4 | 101.1 | 27.9 |
| 10-22 | 34.1 | 99.9 | 27.4 |
| 10-23 | 33.6 | 98.5 | 24.7 |
| 10-24 | 34.2 | 98.9 | 24.7 |
| 10-25 | 35.4 | 100.4 | 24.9 |

10-18 사건 직후 파드가 한꺼번에 다시 뜬 다음 날(10-19) 사용률이 가장 높았다. 이후 33~35% 대로 내려와 안정됐다. commit 이 100% 언저리라는 건 프로세스가 약속받은 메모리 총량이 물리 메모리와 비슷하다는 뜻이다. 실제 사용량은 그보다 훨씬 낮다.

### 방어 장치는 한 번도 발동하지 않았다

09-27 에 다른 노드가 자원 고갈로 멈춘 일이 있었다. 그 뒤 이 노드에 두 겹의 방어를 넣었다.

- [earlyoom](https://github.com/rfjakob/earlyoom): 가용 메모리가 6% 이하로 떨어지면 SIGTERM, 3% 이하면 SIGKILL 을 보낸다. k3s·containerd·sshd 는 대상에서 뺐다.
- kubelet 예약과 [노드 압박 축출(eviction)](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/): system·kube 몫을 예약하고, hard 기준 `memory.available<1Gi`, soft 기준 `<2Gi` 를 걸었다.

설정 이후 earlyoom 로그에는 시작 메시지만 있고 종료 신호를 보낸 기록이 없다. 커널 로그(`journalctl -k`)에서도 `oom-kill`·`soft lockup` 은 0건이다. 장치를 넣은 뒤로 실제로 메모리 위기는 없었다.

## 3. CPU 와 I/O

최근 7일 중 3일을 표본으로 보면 평균 idle 은 65~80% 이고 iowait 은 10~12% 로 꾸준하다. CPU 는 여유가 있다. iowait 이 계속 두 자릿수인 건 디스크 대기가 일상적이라는 뜻이라 계속 지켜볼 항목이다.

## 4. 디스크

| 마운트 | 크기 | 사용 | 사용률 |
|---|---|---|---|
| `/` | 466G | 263G | 59% |
| `/boot` | 2.0G | 215M | 12% |

주요 사용처는 `/var/lib/rancher` 186G, `/var/log` 3.1G(이 중 journal 2.4G), 홈 디렉터리 4.4G 다.

한 달 전 사용량은 따로 기록해 두지 않아서 **정확한 증가량은 말할 수 없다.** 대신 최근 31일 안에 생긴 500MB 이상 파일을 찾았더니 세 개였다.

- 10-04: 로컬 LLM 모델 블롭 1.2G. PV 경로와 kubelet 마운트 경로 양쪽에 보이지만 같은 볼륨이다.
- 10-17: 컨테이너 이미지 레이어 0.7G

kubelet 의 디스크 축출 기준(nodefs 10%, imagefs 15%)까지는 아직 여유가 크다. 다음 달 비교를 위해 일별 `df` 기록을 남기는 게 다음 과제다.

## 5. 로그

`journalctl -p err` 를 날짜별로 세면 평소에는 하루 2~8건이다. 대부분 반복되는 두 가지다.

- `fwupd-refresh.service` 시작 실패. 펌웨어 메타데이터를 갱신하는 타이머다.
- `systemd-networkd-wait-online` 타임아웃. NetworkManager 를 쓰는 노드에서 흔히 보이는 무해한 경고다.

튀는 날은 이틀이다.

| 날짜 | err 건수 | 내용 |
|---|---|---|
| 10-15 | 15 | 대부분 network-wait-online 타임아웃 반복 |
| 10-18 | 106 | 거의 전부 SSH 포트 포워딩 대상에 연결하지 못한 오류. 링크 단절 시간대와 겹친다 |

## 6. 파드

현재 Ready 상태 파드 샌드박스는 46개다. 생성일로 묶으면 다음과 같다.

| 생성일 | 개수 | 설명 |
|---|---|---|
| 09-15 ~ 09-17 | 17 | 재부팅 직후 다시 뜬 파드 (argocd, coredns, ghost 등) |
| 10-06 ~ 10-16 | 11 | 새 워크로드 배치 (팹 시뮬레이션, 백업, 보안 감시 등) |
| 10-17 ~ 10-19 | 16 | **10-18 사건 전후 재배치** |
| 10-26 | 2 | 일상 배포 |

### 재시작 횟수 상위와 원인

`crictl ps -a` 로 컨테이너 시도 번호(attempt)를 보면 두 개가 유독 높다.

| 컨테이너 | 누적 재시작 | 마지막 종료 |
|---|---|---|
| node-exporter | 193 | 10-18 20:21, exit 143 |
| node-self-healer | 101 | 10-18 20:19, exit 143 |

exit 143 은 [128 + 15](https://tldp.org/LDP/abs/html/exitcodes.html), 즉 SIGTERM 을 받고 끝났다는 뜻이다. 프로그램이 스스로 죽은 게 아니라 kubelet 이 종료시킨 것이다.

kubelet 로그(`journalctl -u k3s-agent`)에서 이 컨테이너들의 재시작·kill·프로브 실패 기록을 날짜별로 세면, **기간 안의 기록 293건이 모두 10-18 하루에 몰려 있다.** 시간대는 17시 48건, 18시 201건, 19시 175건, 20시 126건이다.

같은 시각의 NetworkManager 로그에는 무선 링크 타임아웃이 두 번(17:49, 20:20) 찍혀 있다. kubelet 로그에는 로컬 API 프록시로 보낸 요청이 `EOF` 로 끊긴 기록이 이어진다. 순서를 맞추면 이렇다.

1. 17:49 무선 링크 끊김 → 노드가 컨트롤 플레인과 단절
2. kubelet 이 이벤트를 보내지 못하고, 프로브가 실패하고, 컨테이너 재시작이 반복됨
3. 20:20 두 번째 링크 타임아웃 뒤 복구
4. 10-17~19 파드 재배치와 10-19 메모리 사용률 정점

정리하면 재시작 수치가 높은 건 프로그램 결함 때문이 아니라 **네트워크 단절의 2차 효과**였다. 재시작 원인을 볼 때는 [crictl](https://kubernetes.io/docs/tasks/debug/debug-cluster/crictl/) 의 attempt 숫자만 보지 말고 kubelet 로그의 날짜 분포를 함께 봐야 한다는 걸 다시 확인했다.

## 다음에 할 것

- 무선 링크는 이 노드의 단일 장애점이다. 유선 연결을 검토한다.
- 디스크 일별 기록을 남겨 다음 달에는 증감을 숫자로 비교한다.
- sysstat 보존 기간을 7일에서 늘려 월간 비교가 가능하게 한다.

## References

- sysstat (sar) 프로젝트: <https://sysstat.github.io/>
- earlyoom 공식 저장소: <https://github.com/rfjakob/earlyoom>
- Kubernetes, Node-pressure Eviction: <https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/>
- Kubernetes, Debugging Kubernetes nodes with crictl: <https://kubernetes.io/docs/tasks/debug/debug-cluster/crictl/>
- Advanced Bash-Scripting Guide, Exit Codes With Special Meanings: <https://tldp.org/LDP/abs/html/exitcodes.html>
- systemd, journalctl(1): <https://www.freedesktop.org/software/systemd/man/latest/journalctl.html>
