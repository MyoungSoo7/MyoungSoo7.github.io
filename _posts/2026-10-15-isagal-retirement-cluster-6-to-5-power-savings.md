---
layout: post
title: "랙 서버 한 대를 퇴역시켰다 — isagal 을 뺀 K3s 6→5노드 이전기와 아낀 전기요금 계산"
date: 2026-10-15 20:56:34 +0900
categories: [kubernetes, homelab]
tags: [k3s, kubernetes, homelab, persistent-volume, local-path, self-hosted-runner, power, ipmi, idrac, electricity]
---

> 홈랩 K3s 클러스터에서 **전기를 제일 많이 먹던 노드**를 뺐다. Dell PowerEdge R730xd, 이름은 isagal 이다.
> 이 글에는 세 가지를 적는다. 왜 하필 그 노드였는지, 무엇을 어디로 옮겼는지(로컬 볼륨 이전 방법 포함), 그리고 전기요금이 얼마나 줄었는지 한전 요금표로 계산한 결과다.
> 수치는 전부 2026-10-15 에 이 클러스터에서 직접 잰 값이다. 전기요금은 **추정**이고 실측 고지서가 아니다. 한계는 마지막 절에 따로 모았다.

## 1. Before — 코어는 제일 많은데 쓸모는 애매했던 노드

퇴역 전 클러스터는 6대였다. 역할은 아래와 같다.

| 노드 | 기종 | 코어·RAM | 역할 | 네트워크 |
| --- | --- | --- | --- | --- |
| lemuel | 노트북 | 4코어 · 31GB | control-plane + etcd | 유선 1Gb/s |
| ilwon | 데스크톱 | 12코어 · 31GB | control-plane + etcd | 유선 1Gb/s |
| david | 데스크톱 | 6코어 · 15GB | etcd + 워커 | 유선 1Gb/s |
| louise | 노트북 | 8코어 · 15.5GB | 워커 | Wi-Fi |
| solomon | Mac mini (2011) | 4코어 · 15GB | 워커 | Wi-Fi |
| **isagal** | **Dell R730xd (2U 랙 서버)** | **40 vCPU (E5-2630 v4 ×2) · 15GB** | **워커 전용** | **유선 100Mb/s** |

isagal 의 상태는 이랬다.

- **코어는 압도적으로 많았다.** 반면 메모리는 15GB 로 다른 노드와 같았다. 쿠버네티스에서 파드 배치를 막는 건 대개 메모리 요청량이라서, 40코어 대부분이 놀았다. 실제로 퇴역 직전 CPU 사용률은 거의 0% 였다.
- **링크가 100Mb/s 로 협상돼 있었고 재전송률이 약 7% 였다.** 노드 간 복사가 1MB/s 안팎으로 나왔다. 그런데도 파드는 159개로 제일 많이 올라가 있었다.
- **디스크는 3.6TB 회전식 HDD** 였다. 로컬 볼륨을 쓰는 상태 저장 서비스 몇 개(사진 서버, 비밀번호 관리자, 메모, n8n 등)가 여기 묶여 있었다.
- **control-plane 도 etcd 도 아니었다.** etcd voter 는 lemuel·ilwon·david 셋이다. 그래서 isagal 이 빠져도 정족수에는 영향이 없다. 이게 결정적이었다. 다섯 대 중 아무거나 빼는 게 아니라, **빼도 클러스터의 뇌가 안 다치는 노드**를 고른 것이다.
- 그리고 **전기를 제일 많이 먹었다.** 이건 3절에서 따로 계산한다.

## 2. 무엇을 어디로 — 이전 순서

[쿠버네티스 공식 문서의 안전한 노드 드레인 절차](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)대로 순서를 잡았다. 큰 흐름은 cordon → 상태 있는 워크로드부터 옮기기 → drain → 노드 삭제 → 전원 차단이다.

### 2.1 워크로드 이전처

| 워크로드 | 옮긴 곳 | 방식 |
| --- | --- | --- |
| 메모·비밀번호 관리자·네트워크 에이전트·n8n | david | 데이터 복사 + 정적 PV |
| 사진 서버(Immich) 전체, 이미지 빌더(buildkitd) | solomon | 데이터 복사 / ML 캐시는 새 디스크 |
| 로컬 LLM(llama.cpp)·LLM 게이트웨이 | ilwon | 모델 캐시는 새로 받음 |
| 실험용 앱 1개 | louise | nodeSelector 변경 |
| **CI 자체 호스팅 러너 3개** | **louise** | 러너 재등록 + 라벨 변경 |

어디로 보낼지는 노드별 **메모리 요청량**으로 정했다. 그런데 control-plane 이자 etcd 인 ilwon 에는 무거운 걸 다 몰지 않았다. 로컬 LLM 은 원래 isagal 에서 20스레드로 돌았다. ilwon 에서는 12코어 중 **8스레드만 주고 CPU limit 도 8** 로 묶었다. etcd 가 CPU 기아에 빠지면 리더 선출이 흔들리기 때문이다. 소켓도 하나뿐이라 `--numa distribute` 는 뺐다. 이렇게 하면 토큰 속도는 isagal 때보다 떨어질 수 있다. 재측정은 아직 하지 않았다.

### 2.2 로컬 볼륨은 "옮기는" 기능이 없다

isagal 의 볼륨은 k3s 기본 [local-path-provisioner](https://github.com/rancher/local-path-provisioner) 로 만든 것이었다. 이 PV 는 노드 디스크의 디렉터리이고 `nodeAffinity` 로 그 노드에 못박혀 있다. 그래서 노드를 바꾸는 API 가 없다. 그래서 아래 순서를 스크립트로 만들어 PVC 마다 돌렸다.

1. **옛 PV 를 `Retain` 으로 바꾼다.** PVC 를 지우는 순간 provisioner 가 데이터 디렉터리까지 지우는 걸 막는다. [PV 회수 정책](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming)상 `Delete` 가 기본이라 이 단계를 빼면 데이터가 사라진다.
2. 원본 노드에서 `tar --numeric-owner -cp` 로 묶어 대상 노드에 푼다. 소유 UID 를 숫자로 보존해야 `fsGroup` 이 걸린 컨테이너가 권한 오류 없이 뜬다.
3. **파일 수를 대조한다.** 다르면 중단한다.
4. 대상 노드를 가리키는 **정적 PV** 를 만든다. 이때 `claimRef` 로 미리 특정 PVC 에 예약해 둔다. [PV 예약(claimRef)](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reserving-a-persistentvolume)은 다른 PVC 가 먼저 이 PV 를 가로채는 걸 막는다.
5. 옛 PVC 를 지우고 **같은 이름**의 PVC 를 `volumeName` 을 고정해 다시 만든다. 워크로드 매니페스트는 PVC 이름만 보므로 고칠 게 없다.
6. `Bound` 를 확인한 뒤 파드를 다시 띄운다.

옛 PV 와 원본 디렉터리는 **지우지 않았다.** 지금도 꺼진 isagal 디스크에 남아 있다. 전원만 다시 넣으면 회수할 수 있다는 게 이 이전의 롤백 계획이다.

### 2.3 100Mb/s 링크가 정한 것

복사 속도가 1MB/s 안팎이라 수 GB 짜리 캐시는 복사할 엄두가 안 났다. 그래서 **다시 받을 수 있는 데이터는 복사하지 않았다.** LLM 모델 파일(GGUF)과 사진 서버의 ML 모델 캐시가 여기 해당한다. 대상 노드에 빈 디스크로 새로 띄우고 각자 인터넷에서 다시 받게 했다. 모델 파일은 init 컨테이너가 sha256 을 검증하고 나서야 쓰도록 돼 있었다. 그래서 새로 받아도 같은 바이트라는 게 보장된다.

여기서 얻은 교훈은 데이터를 두 부류로 나눠야 한다는 것이다. **"원본이 여기밖에 없는 데이터"** 는 무조건 옮긴다. **"다른 데서 다시 만들 수 있는 데이터"** 는 버린다. 링크가 느릴수록 이 구분이 이전 시간을 정한다.

### 2.4 노드 밖에 흩어진 "isagal" 문자열

파드를 다 빼도 노드 이름은 클러스터 **바깥**에 남아 있었다. 실제로 손본 곳은 이렇다.

- **API 서버 접속 터널의 경유 호스트**: 맥에서 k3s API 로 가는 SSH 터널이 isagal 을 거치고 있었다. 이걸 ilwon 으로 바꿨다. 이걸 놓치면 노드를 끄는 순간 `kubectl` 이 전부 죽는다. 순서상 **가장 먼저** 바꿔야 했다.
- **CI 러너**: GitHub [self-hosted runner](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners) 3개를 louise 로 재등록했다. 워크플로의 `runs-on` 라벨도 `louise` 로 바꿨다. 러너끼리 한 번에 하나만 돌게 하는 전역 락 훅도 같이 옮겼다. 원래 경로에 호스트 이름이 박혀 있었는데, 이번에 호스트와 무관하게 바꿨다.
- **모니터링**: 정적 스크레이프 대상, 백업(velero) 노드별 튜닝, 노드 자가치유 프로파일, Wi-Fi 측정 대상 목록에서 뺐다.
- **서버 감시 봇**: 설정을 시작할 때만 읽는 구조였다. 그래서 설정을 고쳐도 계속 "isagal 다운" 을 울렸고, 프로세스를 재시작해서야 멈췄다.

마지막으로 노드를 drain 하고 삭제했다. k3s-agent 서비스를 disable 한 뒤 전원을 내렸다. 서비스를 disable 해 두었기 때문에 누가 전원을 다시 넣어도 **자동으로 재가입하지 않는다.** k3s 를 [언인스톨](https://docs.k3s.io/installation/uninstall)하지는 않았다. agent 언인스톨 스크립트는 로컬 볼륨 데이터 디렉터리까지 지운다. 그러면 위에서 말한 롤백 계획이 사라진다.

## 3. After — 5노드 클러스터

| 노드 | 역할 | 메모리 요청 | 메모리 실사용 |
| --- | --- | --- | --- |
| lemuel | control-plane + etcd | 16% | 37% |
| ilwon | control-plane + etcd | 79% | 66% |
| david | etcd + 워커 | 72% | 46% |
| louise | 워커 + CI 러너 | 77% | 41% |
| solomon | 워커 | 54% | 28% |

- **노드 5/5 Ready, 파드 174/174 Running** 이다.
- **etcd 정족수(3 voter)는 그대로다.** 한 대가 더 죽어도 2/3 로 버틴다.
- **눈여겨볼 곳은 요청량과 실사용의 차이다.** ilwon 79%·louise 77% 는 "요청" 기준이고 실사용은 66%·41% 다. 스케줄러는 요청량만 본다. 그래서 다음에 뭔가 더 올리면 메모리가 남아 있는데도 `Pending` 이 먼저 뜬다. 노드를 하나 더 빼기 전에 요청량부터 실사용에 맞추는 게 순서다.
- lemuel 이 16% 로 비어 보인다. 하지만 이건 의도된 상태다. control-plane 노드라 일부러 비워 둔 것이다.

## 4. 아낀 전기요금 계산

### 4.1 소비전력 실측

isagal 은 Dell 의 원격관리 컨트롤러(iDRAC)가 있어서 전원 측 소비전력을 직접 읽을 수 있었다. [ipmitool](https://github.com/ipmitool/ipmitool) 의 `dcmi power reading` 결과는 이랬다.

- **순간값 114W.** 퇴역 직전이라 CPU 는 거의 0% 였다.
- iDRAC 이 보고한 통계 구간의 **최솟값은 82W, 최댓값은 214W** 였다.

그래서 아래 계산은 **114W 를 상시 평균으로 가정**한다. 범위는 82~214W 로 같이 적는다.

$$
114\,\text{W} \times 24\,\text{h} \times 365 = 998{,}640\,\text{Wh} \approx 998.6\,\text{kWh/년}
$$

$$
\frac{998.6\,\text{kWh}}{12} \approx 83.2\,\text{kWh/월}
\qquad (\text{범위: } 82\,\text{W} \to 59.9,\ \ 214\,\text{W} \to 156.2\,\text{kWh/월})
$$

### 4.2 단가 — 한전 주택용(저압) 요금

집에 있는 서버라서 [한전 전기공급약관 별표1 월간 전기요금표](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/D/C/CYDCHP00401.jsp)의 **주택용전력(저압)** 을 적용했다. 기타계절(1~6월, 9~12월) 기준 값은 다음과 같다.

| 구간 | 기본요금(원/호) | 전력량요금(원/kWh) |
| --- | --- | --- |
| 200kWh 이하 | 910 | 120.0 |
| 201~400kWh | 1,600 | 214.6 |
| 400kWh 초과 | 7,300 | 307.3 |

전력량요금 말고도 kWh 마다 두 가지가 더 붙는다.

- **연료비조정단가 +5.0원/kWh.** 한전이 2026년 4분기(10~12월)에도 유지한다고 [공지](https://www.kepco.co.kr/home/media/newsroom/notice/boardView.do?boardMngNo=14&boardNo=2759)했다. 산정 결과는 +7.3원이었지만 상한 ±5원에 걸려 +5원이 됐다([연합뉴스](https://www.yna.co.kr/view/AKR20260921019151003)).
- **기후환경요금 9.0원/kWh.** 2021년 5.3원에서 9.0원으로 올랐다는 2025년 국정감사 지적이 [보도](https://www.newspim.com/news/view/20251029001176)됐다. 4분기에는 기후환경요금도 별도로 인상되지 않았다([투데이에너지](https://www.todayenergy.kr/news/articleView.html?idxno=303750)). ⚠️ 이 9.0원은 한전 1차 페이지의 텍스트로는 확인하지 못했다. 그래서 보도 기준값이라고 밝혀 둔다.

### 4.3 핵심 — 아낀 돈은 "가장 비싼 kWh" 로 계산된다

주택용 요금은 [누진제](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/H/C/CYHCHP00206.jsp)다. 그래서 83kWh 를 덜 쓰면 **사용량의 맨 위층**, 곧 가장 비싼 구간부터 빠진다. 아낀 돈은 평균 단가가 아니라 **한계 단가**로 계산해야 한다.

kWh 당 한계 단가는 다음과 같다(부가세 전).

$$
p_{\text{한계}} = \text{전력량요금}_{\text{구간}} + 9.0 + 5.0
\;\Rightarrow\;
\begin{cases}
134.0\ \text{원/kWh} & (\text{1구간})\\
228.6\ \text{원/kWh} & (\text{2구간})\\
321.3\ \text{원/kWh} & (\text{3구간})
\end{cases}
$$

월 83.2kWh, 연 998.6kWh 에 곱하면 아래 표가 된다.

| 집 전체 월 사용량이 머무는 구간 | 월 절감(부가세 전) | 연 절감(부가세 전) | 연 절감(부가세 10% 포함) |
| --- | --- | --- | --- |
| 1구간 (200kWh 이하) | 약 11,200원 | 약 133,800원 | 약 147,200원 |
| 2구간 (201~400kWh) | 약 19,000원 | 약 228,300원 | 약 251,100원 |
| **3구간 (400kWh 초과)** | **약 26,700원** | **약 320,900원** | **약 352,900원** |

그리고 하나가 더 있다. 83kWh 를 빼서 월 사용량이 400kWh **아래로 내려가면** 기본요금 자체도 7,300원에서 1,600원으로 떨어진다. 월 5,700원이 더 빠지는 셈이다. 계단 경계를 넘을 때만 생기는 보너스라 위 표에는 넣지 않았다.

**우리 집은 어느 구간인가?** 나머지 노드 다섯 대와 맥, 그리고 생활 전기가 다 같은 계량기에 물려 있다. 그래서 3구간일 가능성이 높다고 본다. 다만 고지서로 확인한 게 아니라서 표의 세 줄을 모두 남겨 둔다. 3구간이라면 **한 해에 약 32만~35만 원**이다. 범위로 보면 최솟값 82W 로는 연 약 23만 원(부가세 전), 최댓값 214W 로는 약 60만 원 꼴이다. 둘 다 3구간 기준이다.

## 5. 이 계산이 틀릴 수 있는 지점

- **순수 절감은 114W 보다 작다.** isagal 이 하던 일이 다른 노드로 옮겨갔다. 받은 쪽(david·solomon·ilwon·louise)의 소비전력도 조금 늘었을 것이다. 그런데 그 노드들엔 전력계가 없어서 **증가분은 재지 못했다.**
- **꺼진 서버도 대기전력을 먹는다.** 전원 코드가 꽂혀 있으면 iDRAC 같은 관리 컨트롤러가 대기 상태로 살아 있다. 퇴역 후 대기전력은 **측정하지 않았다.**
- **iDRAC 값은 PSU 쪽 계측이다.** 벽 콘센트 전력계로 교차 검증하지 않았다.
- **단가가 바뀐다.** 연료비조정단가는 분기마다 다시 정해진다. 7~8월 하계에는 누진 구간이 300/450kWh 로 넓어진다([약관 별표1](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/D/C/CYDCHP00401.jsp)). 연간 수치는 기타계절 단가를 12개월에 그대로 적용한 근사다. 전력산업기반기금도 계산에서 뺐다.
- **"40코어를 버렸다"** 는 손실도 있다. 다만 메모리 15GB 와 100Mb/s 링크에 묶여 그 코어를 쓸 수 있는 워크로드가 사실상 로컬 LLM 하나뿐이었다. 그게 이번 결정의 전제였다.

## 6. 정리

- **노드 6 → 5, 파드 174개 전부 Running, etcd 정족수 그대로.**
- 로컬 볼륨은 **Retain → tar 복사 → claimRef 정적 PV → 같은 이름 PVC** 순서로 옮겼다. 원본은 꺼진 디스크에 롤백용으로 남겨 뒀다.
- 느린 링크 위에서는 **다시 받을 수 있는 데이터는 옮기지 않는다.**
- 노드를 빼기 전에 노드 **바깥**(API 터널, CI 러너, 모니터링, 감시 봇)에 박힌 이름부터 찾는다.
- 전기요금은 실측 114W 기준으로 **연 약 1,000kWh** 를 덜 쓴다. 누진 3구간이라면 **연 약 32만 원(부가세 포함 약 35만 원)** 이다. 다만 옮겨간 부하와 대기전력은 재지 못해서 이 값은 상한 쪽 추정이다.

## References

1. 한국전력공사, [전기공급약관 별표1 — 월간 전기요금표](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/D/C/CYDCHP00401.jsp) (주택용 저압 기본요금·전력량요금·하계 구간, 2023-11-09 시행)
2. 한국전력공사, [주요 전기요금제도 — 주택용전력 요금 누진제](https://cyber.kepco.co.kr/ckepco/front/jsp/CY/H/C/CYHCHP00206.jsp)
3. 한국전력공사, [2026년 4분기 연료비조정단가 산정내역 (공지)](https://www.kepco.co.kr/home/media/newsroom/notice/boardView.do?boardMngNo=14&boardNo=2759)
4. 연합뉴스, [4분기 전기요금 동결…연료비조정단가 '+5원' 유지](https://www.yna.co.kr/view/AKR20260921019151003) (2026-09-21)
5. 투데이에너지, [한전, 4분기 전기요금 동결](https://www.todayenergy.kr/news/articleView.html?idxno=303750) (2026-10-01)
6. 뉴스핌, [전기요금에 포함된 기후환경요금 4년새 70% 인상](https://www.newspim.com/news/view/20251029001176) (2025-10-29, 기후환경요금 9.0원/kWh 출처 — 보도 기준)
7. Kubernetes, [Safely Drain a Node](https://kubernetes.io/docs/tasks/administer-cluster/safely-drain-node/)
8. Kubernetes, [Persistent Volumes — Reclaiming / Reserving a PersistentVolume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
9. Kubernetes, [Volumes — local](https://kubernetes.io/docs/concepts/storage/volumes/#local)
10. Rancher, [local-path-provisioner](https://github.com/rancher/local-path-provisioner)
11. K3s, [Uninstalling K3s](https://docs.k3s.io/installation/uninstall)
12. GitHub Docs, [About self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)
13. ipmitool, [ipmitool (DCMI power reading)](https://github.com/ipmitool/ipmitool)
