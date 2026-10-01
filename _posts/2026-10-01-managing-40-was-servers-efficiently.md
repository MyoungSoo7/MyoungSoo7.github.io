---
layout: post
title: "서버 40대의 WAS 를 효율적으로 관리하는 법 — 손으로 40번 하던 일을 한 번으로"
date: 2026-10-01 20:56:58 +0900
categories: [devops, infra]
tags: [was, tomcat, spring-boot, ansible, prometheus, sre, rolling-update]
---

WAS 가 4대일 때는 SSH 창 네 개 띄워 놓고 손으로 해도 된다. **40대가 되면 그 방식이 깨진다.** 배포 한 번이 40번의 반복이 되고, 40대 중 한 대만 설정이 다르면 그게 다음 장애가 된다. 이 글은 "WAS 40대"라는 규모에서 무엇을 바꿔야 하는지를 공식 문서 기준으로 정리한다.

결론부터: **① 서버를 목록으로 다루고 ② 설정을 코드로 고정하고 ③ 배포를 배치 단위로 굴리고 ④ 지표를 한 곳에 모은다.** 하나하나는 새롭지 않다. 40대에서 중요한 건 *네 개를 같이* 하는 것이다.

## 0. 문제 정의 — 40대에서 생기는 건 "반복"과 "어긋남"

Google SRE 책은 이런 일을 **toil(토일)** 이라 부른다. 운영에 묶여 있고, 수작업이고, 반복적이고, 자동화 가능하고, 오래 남는 가치가 없고, **서비스가 커질수록 선형으로 늘어나는 일**이다 ([Google SRE Book, Ch.5 Eliminating Toil](https://sre.google/sre-book/eliminating-toil/)). WAS 40대의 수동 배포·수동 재시작·수동 로그 확인이 정확히 여기에 해당한다. 서버가 80대가 되면 일도 두 배가 된다.

Google 은 SRE 한 사람의 운영 업무를 **50% 이하로 묶는다**는 목표를 공개하고 있다 ([같은 장](https://sre.google/sre-book/eliminating-toil/); [Introduction](https://sre.google/sre-book/introduction/)). 이 숫자를 그대로 가져올 필요는 없지만, 요점은 "운영 시간을 측정하고 상한을 두라"는 것이다. 40대 관리의 첫 단계는 도구가 아니라 **지금 배포·재시작·장애 대응에 몇 시간을 쓰는지 재는 것**이다.

또 하나. 같은 책 서론은 **장애의 대략 70%가 운영 중인 시스템을 바꾸는 순간에 생긴다**고 적는다 ([Introduction](https://sre.google/sre-book/introduction/)). 그래서 대책도 세 가지다. 점진적으로 내보내고, 문제를 빨리 감지하고, 문제가 생기면 안전하게 되돌린다. 아래 3장의 배치 배포가 이 세 가지를 그대로 구현한다.

## 1. 서버를 "목록"으로 다룬다 — 인벤토리와 그룹

40대를 한 대씩 기억하지 않는다. **역할별 그룹**으로 묶는다. Ansible 인벤토리가 가장 흔한 형태다.

```ini
# inventory/prod.ini
[was_order]
was-order-[01:10].prod.internal

[was_settle]
was-settle-[01:15].prod.internal

[was_batch]
was-batch-[01:15].prod.internal

[was:children]
was_order
was_settle
was_batch

[lb]
lb-01.prod.internal
lb-02.prod.internal
```

`[01:10]` 같은 범위 표기로 10대를 한 줄에 쓴다. 이제 "주문 WAS 전체", "WAS 전부" 같은 단위로 명령할 수 있다.

```bash
# 40대 전부에서 WAS 프로세스 상태 확인 — 한 줄
ansible was -i inventory/prod.ini -m shell -a "systemctl is-active tomcat" -f 20
```

주의: Ansible 은 기본적으로 **동시에 5대(forks=5)** 에만 붙는다 ([Ansible: Controlling playbook execution](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html)). 40대에 기본값을 쓰면 조회 한 번도 8번에 나눠서 돈다. 읽기 작업은 `-f 20` 처럼 올리고, 쓰기 작업은 아래 `serial` 로 따로 제어한다. **forks 는 속도, serial 은 안전**이다. 둘을 헷갈리면 안 된다.

Ansible·Terraform·Helm 의 역할 구분은 [Terraform·Ansible·Helm 은 언제 무엇을 쓰나]({% post_url 2026-09-12-terraform-ansible-helm-use-cases %}) 에 따로 정리했다.

## 2. 설정을 코드로 고정한다 — "한 대만 다른" 서버를 없앤다

40대에서 가장 비싼 장애는 대개 **설정 드리프트**다. 누군가 급하게 한 대에서만 `-Xmx` 를 올렸거나, 커넥션 풀 크기를 바꿨거나, 인증서를 갱신했다. 39대는 정상이고 1대만 이상하면 로드밸런서 뒤에서 **간헐 장애**로 보이고, 원인을 찾는 데 오래 걸린다.

원칙은 단순하다. **서버에서 손으로 고치지 않는다. 템플릿을 고치고 다시 뿌린다.**

```yaml
# roles/tomcat/templates/setenv.sh.j2
export JAVA_OPTS="-Xms{{ heap_size }} -Xmx{{ heap_size }} \
  -XX:+UseG1GC -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/var/log/tomcat/heapdump"
```

```yaml
# group_vars/was_batch.yml — 배치용만 힙을 크게
heap_size: 8g
# group_vars/was.yml — 나머지 기본값
heap_size: 4g
```

차이가 필요하면 **그룹 변수로 드러낸다.** 개별 서버에 숨겨 두지 않는다. 그리고 주기적으로 `--check --diff` (드라이런)를 돌려 "코드와 실제가 다른 서버"를 찾는다. 드리프트를 *막는* 것보다 *보이게* 하는 게 먼저다.

같은 이유로 **WAS 종류와 버전도 통일**하는 게 좋다. 40대 중 Tomcat 9·10·JBoss 가 섞여 있으면 플레이북도 세 벌이 된다. 섞어 운영할 때 생기는 함정은 [JBoss 와 Tomcat 을 나란히 운영할 때의 함정]({% post_url 2026-09-15-jboss-tomcat-side-by-side-pitfalls %}) 과 [JBoss·WildFly·Tomcat 3자 비교]({% post_url 2026-09-15-jboss-wildfly-tomcat-three-way %}) 를 참고.

## 3. 배포는 배치로 굴린다 — serial, max_fail_percentage, LB 드레인

40대를 한 번에 재시작하면 서비스가 멈춘다. 한 대씩 하면 너무 느리다. 답은 **배치 롤링**이다.

```yaml
# rolling_deploy.yml
- hosts: was_order
  serial: [1, "25%", "50%"]     # 1대 → 25% → 나머지 절반씩
  max_fail_percentage: 0        # 한 대라도 실패하면 중단
  pre_tasks:
    - name: LB 에서 빼기
      shell: echo "disable server was_pool/{{ inventory_hostname }}" | socat stdio /var/run/haproxy.sock
      delegate_to: "{{ item }}"
      loop: "{{ groups.lb }}"
  roles:
    - deploy_war
  post_tasks:
    - name: 헬스체크 통과까지 대기
      uri:
        url: "http://{{ inventory_hostname }}:8080/actuator/health/readiness"
        status_code: 200
      register: r
      until: r.status == 200
      retries: 30
      delay: 5
    - name: LB 에 다시 넣기
      shell: echo "enable server was_pool/{{ inventory_hostname }}" | socat stdio /var/run/haproxy.sock
      delegate_to: "{{ item }}"
      loop: "{{ groups.lb }}"
```

각 키워드가 하는 일은 Ansible 공식 문서에 정의돼 있다.

- **`serial`** — 지정한 수(또는 비율)만큼 *플레이 전체를 끝낸 뒤* 다음 묶음으로 넘어간다. 리스트로 주면 `[1, 5, 10]` 처럼 첫 배치를 작게 시작할 수 있다 ([Ansible: strategies](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html)). **첫 배치 1대 = 사실상 카나리**다.
- **`max_fail_percentage`** — `serial` 과 함께 쓰면 **배치마다** 적용되고, 지정 비율을 *초과*해야 중단된다. 예컨대 4대 배치에서 2대 실패 시 멈추려면 50 이 아니라 49 를 써야 한다 ([Ansible: Error handling](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_error_handling.html)). 이 "초과" 규칙을 모르면 의도보다 하나 더 깨진다.
- **`delegate_to`** — 작업을 WAS 가 아니라 **LB 서버에서 대신 실행**한다. 공식 롤링 업그레이드 예제가 정확히 이 패턴(HAProxy 에서 빼기 → 업그레이드 → 다시 넣기)을 쓴다 ([Ansible: Rolling Upgrades](https://docs.ansible.com/projects/ansible/latest/playbook_guide/guide_rolling_upgrade.html)).

`serial` 을 쓰면 **실패 범위가 배치 단위로 바뀐다**는 점도 기억해 둔다. 한 배치가 전부 실패하면 그 시점에 전체 실행이 실패한다 ([같은 문서](https://docs.ansible.com/projects/ansible/latest/playbook_guide/guide_rolling_upgrade.html)). 첫 배치를 작게 잡는 이유가 이것이다. 잘못된 WAR 가 1대만 망가뜨리고 멈춘다.

### WAS 쪽도 "깨끗하게 내려가야" 한다

LB 에서 뺐는데 처리 중이던 요청이 끊기면 롤링도 무중단이 아니다. Spring Boot 는 **내장 Tomcat·Jetty·Reactor Netty 모두에서 graceful shutdown 이 기본으로 켜져 있다.** 종료가 시작되면 새 요청은 받지 않고 진행 중인 요청은 유예 시간 안에 끝낸다. 유예 시간은 `spring.lifecycle.timeout-per-shutdown-phase` 로 정한다 ([Spring Boot: Graceful Shutdown](https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html)).

```properties
spring.lifecycle.timeout-per-shutdown-phase=20s
```

위 플레이북의 `/actuator/health/readiness` 도 Spring Boot 가 제공하는 것이다. 기동 중에는 `REFUSING_TRAFFIC`, 준비가 끝나면 `ACCEPTING_TRAFFIC` 이 된다 ([Spring Boot: Actuator Endpoints](https://docs.spring.io/spring-boot/4.0/reference/actuator/endpoints.html)). "프로세스가 떴다"가 아니라 **"트래픽을 받을 준비가 됐다"** 를 확인하고 LB 에 넣는 게 핵심이다.

문서가 짚는 함정 하나. **readiness 에 외부 DB 를 함부로 넣지 마라.** 40대가 같은 DB 를 보는데 DB 가 잠깐 흔들리면 40대가 동시에 "준비 안 됨"이 되고, LB 뒤에 남는 서버가 없다. 공유 외부 시스템을 readiness 에 넣을지는 판단의 문제라고 문서도 명시한다 ([같은 문서](https://docs.spring.io/spring-boot/4.0/reference/actuator/endpoints.html)).

### 외장 Tomcat 이라면 — 병렬 배포

Spring Boot 내장이 아니라 외장 Tomcat 에 WAR 를 올린다면, Tomcat 의 **병렬 배포(parallel deployment)** 도 선택지다. `app##002.war` 처럼 버전을 붙여 올리면 같은 경로에 두 버전이 공존한다. 세션이 없는 새 요청은 최신 버전으로 가고, 기존 세션은 그 세션이 있는 옛 버전에 남는다. `undeployOldVersions` 를 켜면 안 쓰이는 옛 버전은 자동으로 내려간다 ([Tomcat 10.1: The Context Container](https://tomcat.apache.org/tomcat-10.1-doc/config/context)). 세션 기반 레거시 앱에서 재시작 없이 교체할 때 유용하다. 다만 메모리를 두 벌 쓰니 힙 여유를 먼저 확인한다.

## 4. 지표를 한 곳에 모은다 — 40개 대시보드가 아니라 1개

40대를 하나씩 들여다보는 순간 다시 toil 이다. **모든 WAS 가 같은 형식으로 지표를 내보내고, 한 곳이 긁어 간다.**

- Spring Boot 라면 Actuator + Micrometer 의 `/actuator/prometheus`.
- 외장 Tomcat·레거시 WAS 라면 Prometheus 공식 [JMX Exporter](https://github.com/prometheus/jmx_exporter) 를 Java agent 로 붙여 JMX MBean(스레드 풀, 힙, GC)을 내보낸다.
- 서버 자체(CPU·디스크·메모리)는 node_exporter.

Prometheus 의 수집 대상 목록은 **파일 기반 서비스 디스커버리(`file_sd_configs`)** 로 관리할 수 있다 ([Prometheus: Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config)). 1장의 Ansible 인벤토리에서 이 파일을 생성하면 **서버 목록이 한 곳에서만 관리된다.** 서버를 추가했는데 모니터링에서 빠지는 일이 구조적으로 사라진다.

무엇을 볼지는 SRE 책의 **네 가지 황금 신호**가 기준이다: **지연(latency), 트래픽(traffic), 에러(errors), 포화(saturation).** 넷만 잴 수 있다면 이 넷을 재라고 한다 ([Google SRE Book, Ch.6 Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)). WAS 에 대입하면:

| 신호 | WAS 에서 보는 것 |
| --- | --- |
| 지연 | 요청 응답시간 p99 (성공·실패를 *분리*해서) |
| 트래픽 | 초당 요청 수 |
| 에러 | 5xx 비율 + "200 인데 내용이 틀린" 응답 |
| 포화 | 스레드 풀 사용률, 힙, DB 커넥션 풀 대기 |

같은 장의 조언 두 가지가 40대 운영에 특히 맞는다. **실패 요청의 지연을 섞지 말 것** — DB 가 끊겨서 빨리 떨어지는 500 이 평균 지연을 좋게 보이게 만든다. 그리고 **p99 지연 상승은 포화의 선행 신호**다 ([같은 장](https://sre.google/sre-book/monitoring-distributed-systems/)).

그리고 대시보드의 기본 단위는 **"서버별"이 아니라 "그룹별"** 로 둔다. 40개 선을 겹쳐 그리면 아무것도 안 보인다. 그룹 평균과 함께 "그룹 안에서 가장 나쁜 1대"를 같이 띄우면, 2장에서 말한 "한 대만 다른 서버"가 바로 튀어나온다.

로그도 같은 원리다. 40대에 SSH 해서 `tail -f` 하지 않는다. 수집기(Fluent Bit 등)로 한 곳에 모으고, **로그 줄마다 호스트명과 배포 버전을 붙인다.** "배포 직후 이 버전에서만 에러"를 찾는 게 40대 운영에서 가장 자주 하는 질문이기 때문이다.

## 5. 프로세스 관리는 OS 에 맡긴다 — systemd

WAS 를 `nohup ./startup.sh &` 로 띄우면 죽어도 아무도 모르고, 재부팅하면 안 뜬다. 40대면 매주 한두 대는 이렇게 조용히 빠져 있다. systemd 유닛으로 등록해 **자동 재시작·부팅 시 기동·로그 수집**을 OS 에 맡긴다.

```ini
# /etc/systemd/system/tomcat.service (요지)
[Service]
User=tomcat
ExecStart=/opt/tomcat/bin/catalina.sh run
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
```

`TimeoutStopSec` 는 3장의 graceful shutdown 유예(20s)보다 **길게** 잡는다. 짧으면 OS 가 정리 중인 프로세스를 강제로 죽인다. 이 파일도 당연히 2장의 템플릿으로 뿌린다.

## 6. 그다음 단계 — 컨테이너·오케스트레이터는 언제

여기까지 하면 40대는 충분히 관리된다. 그다음 선택지가 컨테이너 이미지 + Kubernetes 같은 오케스트레이터다. 2장의 "설정 고정"이 **불변 이미지**로, 3장의 롤링이 **Deployment 의 롤링 업데이트**로, 3장의 readiness 대기가 **readinessProbe** 로, 5장의 systemd 재시작이 **kubelet 재시작**으로 바뀐다. 개념이 그대로 옮겨 간다. Spring Boot 문서가 liveness·readiness 를 Kubernetes 프로브와 바로 연결해 설명하는 것도 그래서다 ([Spring Boot: Actuator Endpoints](https://docs.spring.io/spring-boot/4.0/reference/actuator/endpoints.html)).

다만 오케스트레이터는 그 자체가 운영 대상이다. 컨트롤 플레인, 네트워크 플러그인, 스토리지가 새로 생긴다. **1~5장을 못 하는 팀이 Kubernetes 로 가면 같은 문제를 더 복잡한 층에서 다시 만난다.** 순서는 이 글의 순서가 맞다고 본다. 이건 필자의 판단이고, "몇 대부터 Kubernetes 가 이득"이라는 중립적 기준선은 공식 문서·논문에서 찾지 못했다.

## 정리 — 40대에서 바뀌는 것

| 4대일 때 | 40대일 때 |
| --- | --- |
| 서버 이름을 외운다 | 인벤토리 그룹으로 다룬다 |
| 서버에서 직접 고친다 | 템플릿을 고치고 다시 뿌린다 (드라이런으로 드리프트 탐지) |
| 하나씩 재시작한다 | `serial` 배치 + 첫 배치 1대 + 실패 시 중단 |
| 프로세스가 뜨면 끝 | readiness 200 확인 후 LB 투입, graceful shutdown |
| 서버마다 들어가 본다 | 황금 신호 4개를 그룹 단위로 한 화면에 |
| `nohup` | systemd |

한 문장으로 줄이면, **40대를 40번 다루지 말고 1개의 시스템으로 다뤄라.** 그리고 그 전에 지금 운영에 몇 시간을 쓰는지부터 재라.

### 이 글의 한계

- Ansible·Spring Boot·Tomcat·Prometheus 동작은 각 공식 문서 기준이다. 버전에 따라 기본값이 다를 수 있으니(예: Spring Boot 구버전은 graceful shutdown 이 기본 꺼짐) 쓰는 버전의 문서를 확인할 것.
- "SRE 운영 업무 50% 상한", "장애 약 70% 가 변경에서" 는 Google 이 자사 경험으로 밝힌 수치다. 다른 조직에 그대로 적용된다는 독립 검증은 아니다.
- JEUS·WebLogic 같은 상용 WAS 는 자체 클러스터 관리 도구가 있어 이 글의 Ansible 중심 접근과 겹치거나 충돌할 수 있다. 이 글에선 다루지 않았다.

## References

1. Beyer, B. et al. (eds.), *Site Reliability Engineering*, Google/O'Reilly, 2016. — [Introduction](https://sre.google/sre-book/introduction/) · [Ch.5 Eliminating Toil (Vivek Rau)](https://sre.google/sre-book/eliminating-toil/) · [Ch.6 Monitoring Distributed Systems (Rob Ewaschuk)](https://sre.google/sre-book/monitoring-distributed-systems/)
2. Google, *The Site Reliability Workbook* — [Eliminating Toil](https://sre.google/workbook/eliminating-toil/)
3. Ansible Documentation — [Controlling playbook execution: strategies and more](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html)
4. Ansible Documentation — [Error handling in playbooks](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_error_handling.html)
5. Ansible Documentation — [Playbook Example: Continuous Delivery and Rolling Upgrades](https://docs.ansible.com/projects/ansible/latest/playbook_guide/guide_rolling_upgrade.html)
6. Spring Boot Reference — [Graceful Shutdown](https://docs.spring.io/spring-boot/reference/web/graceful-shutdown.html)
7. Spring Boot Reference — [Actuator Endpoints (Kubernetes Probes, Application Lifecycle)](https://docs.spring.io/spring-boot/4.0/reference/actuator/endpoints.html)
8. Apache Tomcat 10.1 — [The Context Container (Parallel deployment)](https://tomcat.apache.org/tomcat-10.1-doc/config/context)
9. Prometheus — [JMX Exporter (GitHub)](https://github.com/prometheus/jmx_exporter)
10. Prometheus — [Configuration: file_sd_config](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#file_sd_config)

---

*이 글은 Anthropic 의 Claude(Opus 5.5)가 공식 문서를 조사해 초안을 쓰고 사람이 검토하는 방식으로 작성했습니다.*
