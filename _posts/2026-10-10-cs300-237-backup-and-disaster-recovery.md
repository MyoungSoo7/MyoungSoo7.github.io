---
layout: post
title: "[CS300 #237] 백업과 재해 복구 — RPO·RTO 로 설계하고 복원으로 증명한다"
date: 2026-10-10 21:57:00 +0900
categories: [cs]
tags: [cs300, devops, backup, disaster-recovery, rpo-rto]
---

컴퓨터공학 300 주제 시리즈의 237번째 글이다. 전체 지도는 [여기]({% post_url 2026-10-11-cs300-computer-science-300-topics-map %}).

## 한 줄 요약

백업 설계는 "얼마만큼의 데이터를 잃어도 되는가(RPO)"와 "얼마 안에 다시 서야 하는가(RTO)" 두 숫자에서 출발하고, 복원 테스트를 통과하기 전까지 백업은 백업이 아니다.

## 왜 필요한가

데이터를 잃는 방법은 생각보다 많다. 디스크 고장, 실수로 친 `DROP TABLE`, 잘못된 마이그레이션, 랜섬웨어, 클라우드 계정 탈취, 데이터센터 화재. 복제(replication)는 이 중 일부만 막는다. 실수로 지운 행은 복제본에서도 즉시 지워지고, 랜섬웨어가 암호화한 파일은 동기화 폴더에 그대로 동기화된다.

그래서 백업은 "과거 시점의 독립된 사본"이어야 한다. 그리고 재해 복구(DR)는 그 사본으로 서비스를 정해진 시간 안에 다시 세우는 계획이다.

## 핵심 개념

### RPO 와 RTO

```
         마지막 백업          장애 발생                  서비스 복구
 ────────────|───────────────────X──────────────────────────|────────>
             |<------ RPO ------>|<---------- RTO --------->|
              잃어버리는 데이터      서비스가 멈춘 시간
```

- **RPO (Recovery Point Objective)**: 허용 가능한 최대 데이터 손실 구간. 백업 주기가 24시간이면 최악의 경우 하루치를 잃는다.
- **RTO (Recovery Time Objective)**: 장애부터 서비스 복구까지 허용 가능한 최대 시간.

두 값을 줄일수록 비용이 늘어난다. 모든 시스템에 RPO 0, RTO 0 을 요구할 필요는 없다. 결제 원장과 사내 위키는 다른 등급이다. NIST SP 800-34 같은 비상 계획 지침도 업무 영향 분석(BIA)으로 시스템별 복구 우선순위와 목표를 먼저 정하라고 권한다.

### 백업의 종류

| 종류 | 내용 | 복원 |
|---|---|---|
| 전체(full) | 모든 데이터 | 하나만 있으면 된다. 크고 느리다 |
| 증분(incremental) | 직전 백업(종류 무관) 이후 변경분 | 전체 + 모든 증분을 순서대로 |
| 차등(differential) | 마지막 전체 이후 변경분 | 전체 + 마지막 차등 하나 |

### 논리 백업 vs 물리 백업 (DB 예)

PostgreSQL 문서는 백업 방법을 세 가지로 나눈다.

- **SQL 덤프**(`pg_dump`): 데이터를 SQL·아카이브 형식으로 뽑는다. 버전·아키텍처 간 이식성이 좋고 테이블 단위 복원이 쉽다. 큰 DB 에서는 느리다.
- **파일 시스템 수준 백업**: 데이터 디렉터리를 통째로 복사. DB 를 멈추거나 일관된 스냅샷이 필요하다.
- **연속 아카이빙 + PITR**: 베이스 백업(`pg_basebackup`)에 WAL(선행 기록 로그) 파일을 계속 보관한다. 베이스 백업을 복원하고 WAL 을 원하는 시각까지 재생하면 **특정 시점 복구(PITR)** 가 된다. "어제 14:03 의 `DROP TABLE` 직전"으로 돌아갈 수 있다.

DB 파일을 실행 중에 단순 복사하면 일관성이 깨진 사본이 나올 수 있다. 각 DB 가 제공하는 백업 방법을 쓴다.

### 3-2-1 원칙

널리 쓰이는 경험칙이다.

- 사본 **3**개(원본 포함)
- 서로 다른 매체 **2**종
- 그중 **1**개는 오프사이트(다른 장소)

랜섬웨어 시대에는 여기에 **변경 불가(immutable)** 또는 **오프라인** 사본 하나를 더하는 것이 일반적이다. 운영 계정의 자격증명으로 지울 수 있는 백업은 공격자도 지울 수 있다. 객체 저장소의 객체 잠금(WORM) 기능이나 별도 계정의 백업 저장소를 쓴다.

### 보존 정책

모든 백업을 영원히 둘 수는 없다. 흔한 방식은 GFS(Grandfather-Father-Son) 다. 일 단위 7개, 주 단위 4개, 월 단위 12개처럼 오래될수록 성기게 남긴다. 법적 보존 의무가 있는 데이터는 그 기간을 따른다.

### 재해 복구 전략

AWS 의 DR 백서는 비용과 RTO/RPO 의 트레이드오프에 따라 네 가지 전략을 제시한다.

| 전략 | 평소 상태 | RTO/RPO | 비용 |
|---|---|---|---|
| Backup & Restore | 백업만 다른 리전에 | 시간 단위 | 낮음 |
| Pilot Light | 핵심 데이터 복제, 컴퓨팅은 꺼 둠 | 수십 분 | 중간 |
| Warm Standby | 축소된 규모로 상시 가동 | 분 단위 | 높음 |
| Multi-site active/active | 여러 곳에서 동시에 서비스 | 거의 0 | 가장 높음 |

### 쿠버네티스의 백업 대상

- **etcd**: 클러스터의 모든 객체가 있다. 정기 스냅샷을 다른 장소에 보관한다. 경량 배포판(k3s 등)도 내장 etcd 스냅샷 기능과 복원 절차를 제공한다.
- **매니페스트**: GitOps 를 쓰면 Git 이 곧 백업이다. 그렇지 않으면 Velero 같은 도구로 리소스를 내보낸다.
- **영속 볼륨 데이터**: etcd 스냅샷에는 PV 의 **내용**이 들어 있지 않다. 볼륨 스냅샷이나 애플리케이션 수준 백업(DB 덤프, WAL 아카이빙)이 따로 필요하다.

### 복원 테스트

백업 작업이 "성공"으로 끝났다는 것과 복원이 된다는 것은 다른 말이다. 암호화 키를 잃었거나, 백업 대상 경로가 바뀌어 빈 디렉터리를 백업하고 있었거나, 복원 절차를 아는 사람이 퇴사했을 수 있다. 정기적으로 실제 복원을 해 보고, 걸린 시간을 RTO 와 비교한다.

## 직접 해 보기

백업 방식과 주기에 따른 최악의 RPO 를 계산하고, 증분 백업에서 특정 시점을 복원하는 데 필요한 파일 목록을 구해 보자.

```python
def worst_rpo(full_every_h=None, incr_every_h=None, wal_ship_every_min=None):
    candidates = [x * 60 for x in (full_every_h, incr_every_h) if x]
    if wal_ship_every_min:
        candidates.append(wal_ship_every_min)
    return min(candidates)  # 가장 촘촘한 복구 지점 간격(분)

plans = {
    "daily full only":            dict(full_every_h=24),
    "weekly full + hourly incr":  dict(full_every_h=168, incr_every_h=1),
    "daily base + WAL every 1m":  dict(full_every_h=24, wal_ship_every_min=1),
}
for name, p in plans.items():
    print(f"{name:28} worst-case RPO = {worst_rpo(**p):6.0f} min")

# 증분 체인: (시각h, 종류)
chain = [(0, "full"), (1, "incr"), (2, "incr"), (3, "incr"),
         (24, "full"), (25, "incr"), (26, "incr")]

def restore_set(target_h, chain):
    usable = [b for b in chain if b[0] <= target_h]
    last_full = max(i for i, b in enumerate(usable) if b[1] == "full")
    return usable[last_full:]

for t in (2.5, 26.2):
    files = restore_set(t, chain)
    print(f"restore to t={t}h -> {files} (lost {t - files[-1][0]:.1f}h)")

# 증분 하나가 깨지면?
broken = {(25, "incr")}
files = restore_set(26.2, chain)
ok = []
for f in files:
    if f in broken:
        break
    ok.append(f)
print("with corrupted (25,'incr'):", ok, f"(lost {26.2 - ok[-1][0]:.1f}h)")
```

결과는 다음과 같다.

```
daily full only              worst-case RPO =   1440 min
weekly full + hourly incr    worst-case RPO =     60 min
daily base + WAL every 1m    worst-case RPO =      1 min
restore to t=2.5h -> [(0, 'full'), (1, 'incr'), (2, 'incr')] (lost 0.5h)
restore to t=26.2h -> [(24, 'full'), (25, 'incr'), (26, 'incr')] (lost 0.2h)
with corrupted (25,'incr'): [(24, 'full')] (lost 2.2h)
```

증분 체인은 사슬이다. 중간 고리 하나가 깨지면 그 뒤의 모든 증분이 쓸모없어진다. 복원 테스트가 필요한 이유이고, 전체 백업을 주기적으로 다시 받는 이유다.

## 현업에서는

- **복제는 백업이 아니다.** 실시간 복제본, RAID, 동기화 폴더는 장비 고장을 막지만 논리적 실수(삭제, 잘못된 업데이트)는 그대로 복제한다.
- **백업 성공 알림만 믿지 않는다.** 백업 크기가 갑자기 0 에 가까워지거나 급증하면 경보를 건다. 마지막 성공 시각이 기준보다 오래되면 경보를 건다. 백업도 232번에서 본 모니터링 대상이다.
- **복원 리허설.** 분기마다 별도 환경에 실제로 복원하고, 걸린 시간과 막힌 지점을 기록한다. 이 기록이 곧 DR 런북이 된다.
- **클러스터 재구축 시나리오.** 노드 여러 대짜리 클러스터라면 "컨트롤 플레인 노드 전부를 잃었다"를 가정해 etcd 스냅샷으로 복원하는 절차를 미리 적어 둔다. 스냅샷이 같은 노드 디스크에만 있다면 노드와 함께 사라진다. 다른 장소로 복사한다.
- **암호화 키 보관.** 백업을 암호화했다면 키는 백업과 다른 곳에, 그러나 재해 상황에서도 꺼낼 수 있는 곳에 둔다. 키를 잃은 암호화 백업은 없는 것과 같다.

## 확인 문제

1. RPO 와 RTO 를 정의하고, 각각을 줄이는 기술을 하나씩 들라.
2. 증분 백업과 차등 백업의 복원 시 필요한 파일 차이는?
3. 실시간 복제본이 있는데도 별도 백업이 필요한 이유는?
4. etcd 스냅샷만으로 쿠버네티스 클러스터의 모든 것을 복원할 수 있는가?
5. 백업 작업이 매일 "성공"으로 끝나는데도 복원이 실패할 수 있는 이유 두 가지는?

### 풀이

1. RPO 는 허용 데이터 손실 구간, RTO 는 허용 복구 시간. RPO 는 WAL 아카이빙·잦은 백업·복제로, RTO 는 대기 시스템(warm standby)·자동화된 복원으로 줄인다.
2. 증분은 전체 + 이후 모든 증분, 차등은 전체 + 마지막 차등 하나.
3. 삭제·잘못된 갱신·랜섬웨어 암호화 같은 논리적 손상도 즉시 복제되기 때문이다.
4. 아니다. 객체 정의는 복원되지만 영속 볼륨의 데이터는 들어 있지 않다.
5. 잘못된 경로(빈 디렉터리)를 백업, 증분 체인 손상, 암호화 키 분실, 일관성 없는 DB 파일 복사, 복원 절차 미검증 등.

## 더 읽을거리 (References)

- NIST, [SP 800-34 Rev. 1: Contingency Planning Guide for Federal Information Systems](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final)
- PostgreSQL Docs, [Backup and Restore](https://www.postgresql.org/docs/current/backup.html)
- AWS, [Disaster Recovery of Workloads on AWS — Disaster recovery options in the cloud](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-options-in-the-cloud.html)
- Kubernetes Docs, [Operating etcd clusters for Kubernetes](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)
