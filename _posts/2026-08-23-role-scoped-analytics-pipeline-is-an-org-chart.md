---
layout: post
title: "역할로 자른 파이프라인 — 이 그림은 아키텍처가 아니라 조직도다"
date: 2026-08-23 22:06:09 +0900
categories: [Data, Architecture]
tags: [data-engineering, data-mesh, nifi, trino, medallion, lineage, data-contract]
---

이런 다이어그램을 받았다.

![역할별 스윔레인으로 그린 분석 파이프라인 — 데이터 엔지니어/데이터 사이언티스트/분석가 3개 레인 × Ingest·Store·Transform·Analyze·Publish 5단계](/assets/images/role-scoped-analytics-pipeline.jpg)

가로축은 단계(Ingest → Store → Transform → Analyze → Publish), 세로축은 역할(데이터 엔지니어 / 데이터 사이언티스트 / 분석가)이다. 카드마다 좌우에 칩이 달려 있고 범례가 그 문법을 알려준다 — **왼쪽 칩이 입력, 오른쪽 칩이 출력**, `LG`=스트림, `DB`=데이터셋, `TB`=테이블, `FL`=대시보드. 화살표도 세 종류로 나뉜다: 회색은 일반 핸드오프, 주황은 초점 핸드오프(RAW TABLE), 남색은 발행 산출물.

도식으로서는 잘 만들었다. 그런데 이 그림이 실제로 무엇을 주장하고 있는지 보면, 데이터 플랫폼 문헌이 **실패 모드로 이름 붙여 놓은 분해축**과 정확히 일치한다.

## 그림이 잘한 것: 핸드오프가 보인다

먼저 공정하게. 이 다이어그램의 진짜 정보량은 박스가 아니라 **박스 사이**에 있다.

- `Capture Events`(스트림 입력 → 데이터셋 출력)에서 `Land Records`(데이터셋 → 데이터셋)로 넘어가는 지점
- `Land Records`에서 주황 화살표로 튀어나오는 **RAW TABLE** — 여기가 엔지니어 레인에서 사이언티스트 레인으로 넘어가는 유일한 경계다
- `Curate Metrics`(테이블 → 테이블)에서 남색으로 분석가 레인으로 내려가는 지점

즉 이 그림은 3개의 조직 경계와 그 위를 지나가는 3개의 자료형 변환을 명시한다. 대부분의 파이프라인 그림이 "Kafka → S3 → Spark → Tableau" 같은 **제품 이름의 나열**로 끝나는 걸 생각하면, 입력/출력 타입을 칩으로 못 박은 건 계약(contract)에 한 발 다가간 것이다.

문제는 축이다.

## 이 분해축에는 이미 이름이 있다

Zhamak Dehghani가 2019년에 쓴 [How to Move Beyond a Monolithic Data Lake to a Distributed Data Mesh](https://martinfowler.com/articles/data-monolith-to-mesh.html)는 전통적 데이터 플랫폼의 실패 모드를 셋으로 정리한다. 그중 두 번째와 세 번째가 이 그림에 그대로 있다.

**두 번째 — Coupled pipeline decomposition.** 아키텍트는 플랫폼을 "수집·정제·집계·서빙" 같은 **기계적 기능 단계**로 쪼갠다. 이 글의 표현을 그대로 옮기면:

> Though this model provides some level of scale, by assigning teams to different stages of the pipeline, it has an inherent limitation that slows the delivery of features. It has high coupling between the stages of the pipeline to deliver an independent feature or value. **It's decomposed orthogonally to the axis of change.**

변화의 축과 분해의 축이 직교한다 — 이 한 문장이 핵심이다. Dehghani가 든 예시는 음악 스트리밍 서비스에서 '팟캐스트 재생률' 지표 하나를 추가하는 경우다. 새 수집 서비스, 새 정제, 새 집계가 **전부** 필요하고, 그 결과 세 팀의 구현과 릴리스를 동기화해야 한다. 파이프라인 단계가 독립 배포 단위처럼 보이지만 실제로 함께 바뀌어야 하는 최소 단위는 파이프라인 전체다.

받은 그림에 대입하면 이렇다. `상품별 전환율`이라는 지표를 새로 만들고 싶다면 — `Capture Events`에 이벤트를 추가하고, `Land Records`의 스키마를 늘리고, `Clean & Model`에서 신뢰 테이블을 다시 만들고, `Curate Metrics`에 정의를 넣고, `Publish Dashboard`에 타일을 붙여야 한다. 레인이 셋이므로 **세 사람의 일정이 맞아야 지표 하나가 나온다.**

거칠게 모형화하면, $k$개 레인에 걸쳐 있는 변경 하나가 만드는 조율 쌍(coordination pair)의 수는

$$
\binom{k}{2} = \frac{k(k-1)}{2}
$$

이다. $k=3$이면 3쌍. 숫자 자체는 그냥 조합 계산이고 실측이 아니지만, 방향은 분명하다 — **레인을 늘려 전문화할수록 지표 하나의 리드타임은 선형이 아니라 그보다 빠르게 는다.**

**세 번째 — Siloed and hyper-specialized ownership.** 같은 글은 이렇게 쓴다: 데이터 플랫폼 엔지니어들은 조직적으로도 분리돼 있고, 도메인 지식이 아니라 **빅데이터 도구 숙련도**를 기준으로 한 팀에 묶인다. 그들은 "meaningful, truthful and correct data를 제공할 유인이 없는 팀"으로부터 데이터를 받아, "데이터가 어디에 쓰이는지 이해하지 못한 채" 다양한 소비자에게 공급해야 한다.

받은 그림의 세로축 이름이 정확히 그 기준이다. `DATA ENGINEER` / `DATA SCIENTIST` / `ANALYTICS ANALYST`. 도메인이 아니라 **직무**다.

## 도구를 보면 경계가 더 선명해진다

그림에 적힌 도구 이름들을 공식 문서 기준으로 확인해 보면, 레인 경계가 조직 문제만이 아니라 **관측 가능성의 단절**이기도 하다는 게 드러난다.

**NiFi의 계보는 NiFi 안에서 끝난다.** Apache NiFi는 FlowFile 단위로 provenance 이벤트를 기록하고, 이를 Provenance Repository에 인덱싱해 검색·재생(replay)까지 지원한다. [공식 Overview 문서](https://nifi.apache.org/docs/nifi-docs/html/overview.html)는 이렇게 설명한다:

> NiFi automatically records, indexes, and makes available provenance data as objects flow through the system even across fan-in, fan-out, transformations, and more.

[In Depth 문서](https://nifi.apache.org/docs/nifi-docs/html/nifi-in-depth.html)는 이 저장소를 "Data Lineage (also known as the Chain of Custody)"를 제공하는 것으로 규정한다. 강력하다. 단, 그 lineage는 **FlowFile이 NiFi를 떠나는 SEND 이벤트에서 끝난다.** 그림에서 `Land Records`가 오브젝트 스토리지에 파일을 떨구는 순간, 그 파일이 어느 raw 테이블의 어느 파티션이 되고 어느 지표에 반영됐는지는 NiFi의 Provenance Repository가 알지 못한다. 주황색 RAW TABLE 화살표는 그림에서는 선 하나지만, **계보상으로는 절단면**이다.

**Trino는 저장소가 아니다.** [Trino 공식 문서의 Use cases 페이지](https://trino.io/docs/current/overview/use-cases.html)는 첫 절을 "What Trino is not"으로 시작한다:

> Trino is not a general-purpose relational database. It is not a replacement for databases like MySQL, PostgreSQL or Oracle. Trino was not designed to handle Online Transaction Processing (OLTP).

그리고 Trino는 OLAP — 대량 데이터 분석·집계·리포트를 위한 분산 쿼리 엔진으로 설계됐다고 못 박는다. 그림이 STORE(오브젝트 스토리지)와 TRANSFORM(Trino)을 다른 칸으로 분리한 건 이 점에서 **정확하다.** 저장 계층과 쿼리 계층이 분리돼 있다는 사실 자체는 잘 표현됐다.

**레이어↔사용자 대응은 벤더 문서에도 있다. 다만 1:1이 아니다.** Databricks의 [medallion lakehouse architecture 문서](https://docs.databricks.com/aws/en/lakehouse/medallion)는 Bronze(raw) / Silver(validated) / Gold(enriched) 각 레이어의 "intended user"를 표로 명시한다. 그런데 그 표를 실제로 보면 겹친다 — Bronze는 데이터 엔지니어뿐 아니라 **compliance·audit 팀**도 사용자로 잡고, Silver는 엔지니어·분석가·데이터 사이언티스트가 **모두** 쓰는 층으로 잡혀 있다. 게다가 같은 문서는 이렇게 덧붙인다:

> Following the medallion architecture is a recommended best practice but not a requirement.

즉 벤더 1차 문서조차 레이어와 역할을 깔끔한 3×3 격자로 나누지 않는다. 받은 그림은 실제보다 경계를 **더 단정하게** 그렸다.

## 그러면 어떻게 고칠까

세 가지 선택지가 있고, 셋 다 조건부다.

**1) 레인을 도메인으로 바꾼다.** Dehghani의 처방은 축을 90도 돌리는 것이다 — 레인을 `주문` / `결제` / `상품`으로 두고, 각 레인 안에 수집→정제→발행을 통째로 넣는다. 그러면 '상품별 전환율'은 한 레인 안에서 끝난다. 대신 각 도메인 팀이 자기 데이터를 **제품처럼** 소유해야 한다 — 발견 가능하고, 주소를 갖고, 신뢰할 수 있고, 스키마를 자기 기술하는 형태로.

**2) 역할 레인을 유지하되 화살표를 계약으로 승격시킨다.** 조직이 작아서 도메인 팀을 세울 인원이 없다면 역할 분리가 현실적인 답일 수 있다. 그때 해야 할 일은 **주황·남색 화살표에 스키마·SLA·소유자·호환성 정책을 붙이는 것**이다. 그림에 이미 칩(`DB`→`TB`)으로 자료형이 적혀 있으니 반쯤 와 있다. 남은 건 타입이 아니라 계약이다 — 이 테이블은 언제까지 신선한가, 컬럼을 지울 때 누구에게 알리는가, 깨졌을 때 누가 당직인가.

**3) 접합부에 식별자를 심는다.** 레인마다 계보를 남기는 도구가 다르므로(NiFi provenance / 쿼리 엔진 로그 / BI 도구 메타데이터) 자동 연결은 공짜로 오지 않는다. 최소한 이벤트 ID나 배치 ID를 raw 테이블 컬럼으로 끌고 들어가서, 대시보드 숫자에서 원본 FlowFile까지 **손으로라도 되짚을 수 있게** 해 둬야 한다.

## 한계 명시

- **데이터 메시는 논쟁적이다.** 위 인용은 원저자의 1차 글이지만, 이 접근이 역할 분리형 조직보다 낫다는 **중립 제3자의 정량 비교 연구는 내가 확인한 범위에 없다.** 조직 규모가 작으면 도메인 팀 구성 자체가 오버헤드이고, 그 경우 이 그림 같은 역할 분해가 오히려 합리적이다.
- **medallion은 벤더 권고다.** Databricks 문서의 내용은 자사 제품 맥락의 베스트 프랙티스이며, 문서 스스로 요구사항이 아니라고 밝힌다.
- **조합 계산은 모형일 뿐이다.** 위 $\binom{k}{2}$ 는 조율 비용의 방향을 보이려는 단순 모형이지 측정값이 아니다.

## 남는 한 문장

Melvin Conway가 1968년에 관찰한 바대로, 시스템 구조는 그것을 만든 조직의 소통 구조를 닮는다. 이 다이어그램의 값어치는 파이프라인을 설명하는 데 있지 않다. **누가 누구에게 무엇을 넘기는지**를 자백하는 데 있다. 그림이 예쁘게 나왔다면, 그건 조직이 그만큼 깔끔하게 분업돼 있다는 뜻이고 — 동시에 변화 하나가 그 분업선을 전부 가로질러야 한다는 뜻이기도 하다.

---

## References

- Zhamak Dehghani, [How to Move Beyond a Monolithic Data Lake to a Distributed Data Mesh](https://martinfowler.com/articles/data-monolith-to-mesh.html), martinfowler.com, 2019 — "coupled pipeline decomposition", "siloed and hyper-specialized ownership" 실패 모드 및 "decomposed orthogonally to the axis of change" 인용 출처.
- Apache NiFi Team, [Apache NiFi Overview](https://nifi.apache.org/docs/nifi-docs/html/overview.html) — 자동 provenance 기록·인덱싱.
- Apache NiFi Team, [Apache NiFi In Depth](https://nifi.apache.org/docs/nifi-docs/html/nifi-in-depth.html) — Provenance Repository 및 Data Lineage(Chain of Custody) 정의.
- Trino Documentation, [Use cases](https://trino.io/docs/current/overview/use-cases.html) — "What Trino is not" / OLAP 지향 분산 쿼리 엔진.
- Databricks Documentation, [What is the medallion lakehouse architecture?](https://docs.databricks.com/aws/en/lakehouse/medallion) — Bronze/Silver/Gold 레이어별 intended user 표, "recommended best practice but not a requirement".
- Melvin E. Conway, [How Do Committees Invent?](https://www.melconway.com/Home/Committees_Paper.html), *Datamation*, April 1968 — 시스템 구조와 조직 소통 구조의 대응(Conway의 법칙) 원 논문.
