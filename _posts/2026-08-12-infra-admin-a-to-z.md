---
layout: post
title: "인프라 관리자가 알아야 할 A to Z — 6노드 클러스터가 나를 가르친 방식"
date: 2026-08-12 02:20:00 +0900
categories: [infrastructure, operations]
tags: [kubernetes, k3s, etcd, networking, ufw, vxlan, quorum, cloudflared, sre]
---

이 글에는 "인프라 관리 10가지 팁" 같은 목록이 없다. 대신 **내가 운영하는 6노드 K3s 클러스터에서 실제로 터진 장애**만 재료로 쓴다. 항목마다 증상 → 오진 → 실측 → 원인 → 1차 문서 근거 순으로 간다.

이렇게 쓰는 이유가 있다. 인프라 지식은 문서를 읽어서 얻는 게 아니라, **틀린 곳을 짚어보고 아닌 걸 확인하면서** 얻어진다. 아래 사례들의 공통점은 전부 내가 처음에 엉뚱한 데를 팠다는 것이다.

측정 시점은 2026년 8월 12일이고, 클러스터 현황은 이렇다.

```
NAME      STATUS  ROLES                 AGE    VERSION       INTERNAL-IP       OS
david     Ready   <none>                79d    v1.35.4+k3s1  192.168.219.113   Ubuntu 26.04 LTS
ilwon     Ready   control-plane,etcd    94d    v1.35.4+k3s1  192.168.219.110   Ubuntu 26.04 LTS
isagal    Ready   <none>                65d    v1.35.4+k3s1  192.168.219.105   Ubuntu 26.04 LTS
lemuel    Ready   control-plane,etcd   113d    v1.35.4+k3s1  192.168.219.101   Ubuntu 24.04.4 LTS
louise    Ready   <none>                93d    v1.35.4+k3s1  192.168.219.111   Ubuntu 24.04.4 LTS
solomon   Ready   control-plane,etcd    93d    v1.35.4+k3s1  192.168.219.108   Ubuntu 26.04 LTS
```

네임스페이스 56개, etcd voter 3개(ilwon·lemuel·solomon). 사설 대역이라 그대로 적는다.

---

## A. 물리 계층을 먼저 의심하라

**증상.** 특정 노드에 뜬 파드만 DB 커넥션 풀이 말랐다. HikariCP가 커넥션을 못 얻고 타임아웃을 뱉는데, 같은 이미지·같은 설정으로 다른 노드에 뜬 파드는 멀쩡했다.

**내 오진.** 당연히 애플리케이션을 봤다. 풀 사이즈, 커넥션 누수, 트랜잭션 경계, DB 쪽 `max_connections`. 전부 정상이었다. 그다음엔 DB 서버를 의심했다. 그것도 아니었다.

**실측이 끝냈다.** 노드 간 왕복 지연을 재보니 문제 노드만 **43.5ms**였다. 나머지는 **0.23ms**. 같은 랜선, 같은 스위치인데 190배 차이가 났다.

원인은 이거였다 — **그 노드에 IP가 두 인터페이스에 겹쳐 있었다.** 유선 랜과 USB WiFi 동글이 같은 주소를 물고 있어서, 인바운드 트래픽이 2.4GHz 무선으로 흐르고 있었다. 동글을 내리자 곧바로 0.23ms가 됐다.

**왜 커넥션 풀이 말랐나.** 풀에서 커넥션 하나를 빌리고 쓰고 반납하는 데 걸리는 시간을 $t$, 왕복 지연을 $d$라 하면, 커넥션 하나가 초당 처리할 수 있는 요청 수는 대략

$$r = \frac{1}{t_{\text{query}} + 2d}$$

$d$가 $0.23\text{ms} \to 43.5\text{ms}$로 커지면 $2d$만 87ms가 붙는다. 쿼리 자체가 5ms짜리였다면 처리량이 **약 17배** 떨어진다. 풀 크기는 그대로인데 반납이 늦어지니, 대기열이 쌓이다가 타임아웃이 난다. **애플리케이션 코드에는 아무 잘못이 없었다.**

**교훈.** 애플리케이션 증상이 노드별로 갈리면, 코드를 더 파지 말고 **그 노드의 물리 경로를 재라.** `ping` 한 번이 코드 리뷰 3시간보다 낫다.

---

## B. 재부팅은 당신의 설정을 되돌린다

**증상.** 노드를 재부팅했더니 파드 간 통신이 죽었다. 노드는 `Ready`인데 파드끼리 서로 못 봤다.

**원인.** Ubuntu에서 재부팅하면 `ufw`가 다시 활성화되면서 **VXLAN 트래픽을 막는다.** `sudo ufw disable` 한 줄로 끝났다.

K3s 공식 요구사항 문서는 필요한 포트를 이렇게 명시한다.[^1]

> "The K3s server needs port 6443 to be accessible by all nodes. The nodes need to be able to reach other nodes over **UDP port 8472** when using the Flannel VXLAN backend... If you plan on achieving high availability with embedded etcd, server nodes must be accessible to each other on **ports 2379 and 2380**... If you wish to utilize the metrics server, all nodes must be accessible to each other on **port 10250**."

정리하면 이렇다.

| 포트      | 프로토콜 | 방향              | 용도                   |
| --------- | -------- | ----------------- | ---------------------- |
| 6443      | TCP      | Agent → Server    | apiserver / supervisor |
| 8472      | UDP      | 전 노드 ↔ 전 노드 | **Flannel VXLAN**      |
| 2379–2380 | TCP      | Server ↔ Server   | embedded etcd          |
| 10250     | TCP      | 전 노드 ↔ 전 노드 | Kubelet (metrics)      |

**여기서 정직하게 밝힐 게 있다.** K3s 공식 문서는 `firewalld`와 `iptables`는 이름을 대고 다루지만 **`ufw`는 한 번도 언급하지 않는다.** 내가 확인한 범위(요구사항 페이지, Known Issues 페이지)에서 ufw 관련 공식 지침은 없다. ufw 이야기는 k3s GitHub 이슈 스레드에만 있고 그건 문서가 아니다. 그러니 위 표는 공식이지만, "ufw가 범인"은 **내 클러스터에서의 관측**이라고 읽어야 한다.

한편 공식 문서는 8472를 무작정 열지 말라고도 경고한다.[^1]

> "The VXLAN port on nodes should not be exposed to the world as it opens up your cluster network to be accessed by anyone. Run your nodes behind a firewall/security group that disables access to port 8472."

**교훈.** "고쳤다"와 "고친 상태가 재부팅을 견딘다"는 다른 명제다. 손으로 끈 것은 반드시 다시 켜진다. 방화벽·커널 파라미터·라우팅처럼 부팅 시 초기화되는 것은 **부팅 후 상태를 한 번 더 확인**해야 끝난 것이다.

---

## C. 이중화처럼 보이는 것이 이중화가 아니다

한 노드는 내장 무선 카드가 WPA3를 지원하지 않아 USB 동글로 5GHz에 붙어 있다. 그리고 이 노드의 `--node-ip`가 **그 동글 인터페이스에만** 묶여 있었다.

K3s 문서상 `--node-ip`는 "IPv4/IPv6 addresses to advertise for node"다.[^2] 즉 노드가 자기 주소로 광고하는 값이다. 이 값이 무선 인터페이스를 가리키면, **동글이 죽는 순간 노드 자체가 클러스터에서 이탈한다.**

여기서 흔한 착각이 생긴다. "유선도 있고 무선도 있으니 이중화 아닌가?" 아니다. 링크가 둘이어도 **광고되는 주소가 하나**면 가용 경로는 하나다. 무선은 유선의 폴백이 아니라, 그냥 **유일한 경로**였다.

문제는 이 노드가 etcd voter라는 것이다. **가장 불안정한 링크 위에 합의(consensus) 참여자를 올려둔 셈**이다. etcd 공식 튜닝 문서는 이렇게 말한다.[^3]

> "An etcd cluster is very sensitive to disk latencies. Since etcd must persist proposals to its log, disk activity from other processes may cause long `fsync` latencies. The upshot is etcd may miss heartbeats, causing request timeouts and temporary leader loss."

디스크 이야기지만 원리는 같다 — **하트비트를 놓치면 리더를 잃는다.** 지연이 디스크에서 오든 무선 링크에서 오든 결과는 같다.

**교훈.** 이중화를 셀 때는 물리 링크 수가 아니라 **실제로 광고되는 경로 수**를 세라. 그리고 합의에 참여하는 노드는 인프라에서 가장 안정적인 링크 위에 올려라.

---

## D. etcd는 디스크에 목숨을 건다

etcd 공식 하드웨어 문서는 드물게도 **구체적인 숫자**를 준다.[^4]

> "etcd is very sensitive to disk write latency. Typically **50 sequential IOPS** (e.g., a 7200 RPM disk) is required. For heavily loaded clusters, **500 sequential IOPS** (e.g., a typical local SSD or a high performance virtualized block device) is recommended."

네트워크에 대해서도 마찬가지다.[^4]

> "Low latency ensures etcd members can communicate fast. High bandwidth can reduce the time to recover a failed etcd member. **1GbE is sufficient for common etcd deployments.** For large etcd clusters, a 10GbE network will reduce mean time to recovery."

내 클러스터에서도 이게 그대로 나왔다. etcd 노드 하나의 데이터 디렉터리를 SSD로 옮긴 뒤 체감이 달라졌다.

**그런데 여기서 반직관적인 사례가 하나 있었다.** 어떤 노드는 클러스터에서 **디스크가 가장 빠른데도** `kubectl apply`가 다른 노드보다 훨씬 느렸다. 디스크를 의심하고 잰 게 틀렸던 것이고, 실제 병목은 **CPU**였다. 그 노드에서만 컨트롤러들이 리더 선출을 놓치며 죽었다.

리더 선출 기본값을 보면 왜 CPU가 치명적인지 보인다. 쿠버네티스 공식 플래그 레퍼런스 기준이다.[^5]

| 플래그                          | 기본값  |
| ------------------------------- | ------- |
| `--leader-elect-lease-duration` | **15s** |
| `--leader-elect-renew-deadline` | **10s** |
| `--leader-elect-retry-period`   | **2s**  |

리더는 **10초 안에** 리스를 갱신해야 하고, 못 하면 15초 뒤 리더 자리를 잃는다. CPU가 포화되어 goroutine 스케줄링이 밀리면 이 10초를 놓치기 딱 좋다. 그래서 "리더 선출 실패로 죽는 오퍼레이터 여러 개"는 각각의 버그가 아니라 **노드 하나의 CPU 문제**가 만든 공통 증상이었다.

**교훈.** 여러 컴포넌트가 동시에 이상하면 컴포넌트를 하나씩 보지 말고 **공통 분모(노드·디스크·CPU·시계)**를 찾아라. 그리고 느리다고 무조건 디스크를 탓하지 마라 — 재고 나서 말해야 한다.

---

## E. 쿼럼은 '살아있는' 멤버가 아니라 '등록된' 멤버로 센다

이게 내가 가장 비싸게 배운 것이다.

etcd 클러스터를 리셋한 뒤 노드를 다시 넣었는데 계속 실패했다. 원인은 **옛 멤버가 등록부에 남아 있었던 것**이다. 죽은 멤버인데도 쿼럼 계산에는 들어간다.

멤버 수 $n$일 때 쿼럼은

$$q = \left\lfloor \frac{n}{2} \right\rfloor + 1$$

정상적으로 3개면 $q = 2$라 하나가 죽어도 버틴다. 그런데 **유령 멤버 하나가 등록부에 남으면 $n = 4$가 되어 $q = 3$**이 된다. 살아있는 건 여전히 2개뿐이니 **쿼럼을 잃는다.** 멤버를 "추가"했을 뿐인데 가용성이 떨어지는 것이다.

etcd 공식 문서가 정확히 이 함정을 경고한다.[^6]

> "The quorum loss happens since the **newly added member are counted in the quorum even if that member is not reachable** from other existing members."

> "Reconfiguration requests can only be processed when a majority of cluster members are functioning. It is highly recommended to always have a cluster size greater than two in production. **It is unsafe to remove a member from a two member cluster.**"

그래서 복구는 DB 파일을 지우는 것만으로 끝나지 않고, **등록부에서 옛 멤버를 강제로 제거**해야 했다.

`--cluster-reset` 자체의 정의도 알아둘 만하다. K3s 문서는 이렇게 적는다.[^7]

> "`--cluster-reset` ... **Forget all peers and become sole member of a new cluster**"

그리고 안전장치가 있다.[^8]

> "As a safety mechanism, when K3s resets the cluster, it creates an empty file at `/var/lib/rancher/k3s/server/db/reset-flag` that prevents users from accidentally running multiple cluster resets in succession."

**한 가지 정직하게 적어둔다.** K3s 공식 문서에는 "cluster-reset 후 고아 etcd 멤버를 제거하라"는 **절차가 없다.** 그건 etcd 일반 운영 절차(`etcdctl member remove`)지 k3s가 문서화한 단계가 아니다. 내가 겪은 복구 순서는 공식 절차가 아니라 두 문서를 합쳐 만든 것이다.

**교훈.** 분산 합의에서 "죽은 노드"와 "등록 해제된 노드"는 완전히 다르다. 노드를 뺐으면 **등록부에서도 뺐는지** 확인하라.

---

## F. 노드는 균질하지 않다 — 그리고 그건 설계 제약이다

위 노드 목록을 다시 보자. 같은 클러스터인데 **Ubuntu 24.04와 26.04가 섞여 있다.** 커널도 6.8 계열과 7.0 계열이 공존한다.

측정한 CPU 사용률도 균질하지 않다.

| 노드    | CPU     | 메모리  |
| ------- | ------- | ------- |
| lemuel  | **51%** | 35%     |
| solomon | 11%     | 28%     |
| ilwon   | 8%      | **71%** |
| louise  | 3%      | 53%     |
| david   | 2%      | 55%     |
| isagal  | 0%      | 59%     |

한 노드가 51%를 쓰는 동안 다른 노드는 0~3%다. 그리고 이 불균형은 스케줄러 탓이 아니라 **역할 배치의 결과**다(컨트롤 플레인 + 특정 워크로드 집중).

여기에 더해 내 클러스터에는 **물리적으로 증설이 불가능한 노드**들이 있다. 노트북 두 대와 오래된 미니 PC는 메모리를 더 꽂을 수 없다. 이건 운영 이슈가 아니라 **설계 상수**다. "메모리 늘리면 되지"가 선택지가 아닌 노드가 있으면, 그 노드에는 처음부터 메모리를 적게 쓰는 워크로드만 올려야 한다.

참고로 위 수치는 `kubectl top` 값인데, 이건 정밀 계측용이 아니다. metrics-server 공식 문서가 못을 박는다.[^9]

> "Metrics Server is **not meant for non-autoscaling purposes**. For example, don't use it to forward metrics to monitoring solutions, or as a source of monitoring solution metrics. In such cases please collect metrics from Kubelet `/metrics/resource` endpoint directly."

> "Don't use Metrics Server when you need: ... **An accurate source of resource usage metrics**"

그래서 위 표는 "대략의 편중"을 보여줄 뿐, 용량 계획의 근거로 쓰면 안 된다. 나도 그렇게 쓰지 않았다.

**교훈.** 홈랩이든 프로덕션이든 노드는 균질하지 않다. **하드웨어 제약을 스케줄링 정책으로 표현**해두지 않으면(taint·label·affinity), 언젠가 스케줄러가 그 제약을 모르고 최악의 배치를 한다.

---

## G. 엣지는 클러스터 밖에 있다 — 그리고 그게 제일 위험하다

이번 조사에서 제일 놀란 건 이거다.

내 클러스터에는 **인그레스 컨트롤러가 하나도 없다.** 확인한 것:

```
$ kubectl get ingressclass
No resources found

$ kubectl get svc -A --field-selector spec.type=LoadBalancer
No resources found

$ kubectl get pods -A | grep -Ei 'traefik|ingress-nginx|contour'
(빈 출력)
```

그런데 `Ingress` 오브젝트는 **6개가 멀쩡히 존재하고, ADDRESS 칸에 노드 IP 5개가 찍혀 있다.**

```
$ kubectl get ingress -A
NS                  NAME                       CLASS     ADDRESS
agent-system        litellm-ingress            traefik   192.168.219.101,...,192.168.219.113
lemuel-xr-prod      lemuel-xr-ingress          traefik   192.168.219.101,...
n8n                 n8n-ingress                traefik   192.168.219.101,...
order-oms-prod      order-oms-prod-ingress     traefik   192.168.219.101,...
settlement-prod     payment-webhook            traefik   192.168.219.101,...
warehouse-wms-prod  warehouse-wms-prod-ingress traefik   192.168.219.101,...
```

**주소가 찍혀 있으니 정상으로 보인다. 전부 거짓이다.** 저 `status`는 Traefik이 살아 있던 시절 컨트롤러가 써넣은 값이고, 컨트롤러가 사라져도 **status는 지워지지 않는다.** 아무도 갱신하지 않으니 마지막 값에서 그대로 굳는다.

그럼 서비스는 죽었나? 아니다. 외부에서 재보면 멀쩡하다.

```
$ curl -sI https://<n8n 호스트>/
HTTP/2 200
```

**실제 트래픽은 `cloudflared`가 나른다.** Cloudflare Tunnel 파드 3개가 떠 있고, 이들이 Service로 직접 넣는다. Ingress 오브젝트는 경로에 아예 없다.

여기서 진짜 위험은 따로 있다. cloudflared는 `tunnel run`으로 뜨는데, 이 모드에서 **라우팅 규칙은 Cloudflare 대시보드(원격)에 있다.** 즉 우리 서비스의 실제 라우팅 설정은

- 클러스터 안에 없고,
- git 저장소에도 없고,
- `kubectl`로 볼 수도 없다.

**당신이 볼 수 있는 설정이 실제로 도는 설정이 아니다.** 저 Ingress 6개를 지금 고쳐도 아무 일도 일어나지 않는다. 반대로 대시보드에서 누군가 한 줄 바꾸면 git에는 흔적 없이 프로덕션 라우팅이 바뀐다.

**교훈.** 트래픽 경로는 오브젝트가 아니라 **실제 요청**으로 검증하라. 그리고 "설정이 어디 사는지" 목록을 만들어라 — git 밖에 사는 설정이 하나라도 있으면, 그건 장애 시 아무도 못 찾는 곳이다.

---

## H. 인프라 관리자 체크리스트

위 사례들에서 뽑은 것만 적는다.

1. **노드별로 증상이 갈리면 물리 경로부터 재라.** 노드 간 RTT는 30초면 잰다.
2. **한 노드에 IP가 두 인터페이스에 걸쳐 있지 않은지** 확인하라. 인바운드는 당신이 원하는 길로 오지 않는다.
3. **재부팅 후 상태를 다시 확인하라.** 방화벽은 되살아난다.
4. **광고되는 경로 수를 세라.** 링크가 둘이어도 `--node-ip`가 하나면 경로는 하나다.
5. **합의 참여 노드(etcd)는 가장 안정적인 링크·가장 빠른 디스크 위에 둬라.** 공식 권고는 최소 50 IOPS, 부하 시 500 IOPS.
6. **노드를 뺐으면 등록부에서도 뺐는지 확인하라.** 유령 멤버는 쿼럼을 갉아먹는다.
7. **여러 컴포넌트가 동시에 아프면 공통 분모를 찾아라.** 리더 선출은 10초 안에 갱신 못 하면 끊긴다.
8. **하드웨어 제약을 스케줄링 정책으로 표현하라.** 증설 불가 노드는 문서가 아니라 taint로 말해야 한다.
9. **트래픽은 오브젝트가 아니라 요청으로 검증하라.** `ADDRESS`가 찍혀 있어도 아무도 안 듣고 있을 수 있다.
10. **git 밖에 사는 설정을 목록화하라.**

---

## 이 글의 한계

- **모든 사례는 단일 클러스터(6노드 K3s v1.35.4, 홈랩 규모)의 관측이다.** 일반화하지 않았고, 재현 환경이 다르면 결과도 다르다.
- **ufw ↔ VXLAN 인과는 내 관측이지 공식 문서의 서술이 아니다.** K3s 공식 문서는 ufw를 언급하지 않는다(firewalld·iptables만 다룬다). 위에 그대로 밝혔다.
- **43.5ms → 0.23ms는 이전 측정 기록이고, 이 글을 쓰며 재측정한 값이 아니다.** 이번에 재측정한 것은 노드 목록·CPU/메모리·Ingress/컨트롤러 존재 여부·외부 응답 코드다.
- **커넥션 풀 처리량 수식은 단순화 모델이다.** 실제 HikariCP 동작(대기 큐, 타임아웃, 검증 쿼리)을 반영하지 않았고, 17배는 그 모델 위에서 나온 계산이지 측정값이 아니다.
- **`kubectl top` 수치는 metrics-server 공식 문서가 정밀 계측용이 아니라고 명시한 값이다.** 편중을 보이는 용도로만 썼다.
- **다중 인터페이스에서 k3s가 어느 IP를 고르는지에 대한 설명은 docs.k3s.io 본문에 없다.** 메인테이너의 GitHub Discussion 답변이 가장 명확한 출처인데, 이건 공식 문서 사이트가 아니므로 본문 논지의 근거로 쓰지 않았다.

---

## 마무리

인프라 관리에서 제일 자주 틀리는 순간은 **"여기가 문제일 리 없다"고 건너뛸 때**다. 위 사례에서 나는 코드를 봤어야 할 때 네트워크를 보지 않았고, 디스크를 의심할 때 CPU를 재지 않았고, 오브젝트가 있으니 컨트롤러도 있으려니 했다.

그래서 A to Z 중 A는 이것 하나로 충분하다. **재고 나서 말하라.** 나머지는 그 습관에서 파생된다.

다음 글에서는 같은 클러스터를 **쿠버네티스 안쪽 시선**으로 본다 — 컨트롤러, 리컨실 루프, 셀렉터, 자원 한계처럼 `kubectl`로 보이는 층의 A to Z다.

---

## References

[^1]: K3s 공식 문서, "Requirements — Networking / Inbound Rules" (1차·공식). <https://docs.k3s.io/installation/requirements>

[^2]: K3s 공식 문서, "k3s agent — CLI flags" (1차·공식). <https://docs.k3s.io/cli/agent> · 네트워크 옵션 <https://docs.k3s.io/networking/basic-network-options>

[^3]: etcd 공식 문서, "Tuning" (1차·공식). <https://etcd.io/docs/v3.7/tuning/>

[^4]: etcd 공식 문서, "Hardware recommendations" (1차·공식). <https://etcd.io/docs/v3.3/op-guide/hardware/>

[^5]: Kubernetes 공식 문서, kube-controller-manager / kube-scheduler 플래그 레퍼런스 (1차·공식). <https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/> · <https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler/>

[^6]: etcd 공식 문서, "Runtime reconfiguration" (1차·공식). <https://etcd.io/docs/v3.8/op-guide/runtime-configuration/>

[^7]: K3s 공식 문서, "k3s server — CLI flags" (1차·공식). <https://docs.k3s.io/cli/server>

[^8]: K3s 공식 문서, "etcd snapshot & restore" (1차·공식). <https://docs.k3s.io/cli/etcd-snapshot>

[^9]: kubernetes-sigs/metrics-server 공식 문서 (1차·공식). <https://kubernetes-sigs.github.io/metrics-server/> · FAQ <https://github.com/kubernetes-sigs/metrics-server/blob/master/FAQ.md>
