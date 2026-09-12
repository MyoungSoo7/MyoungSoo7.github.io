---
layout: post
title: "Strimzi CRD 가 뭔가 — 쿠버네티스에 Kafka 라는 명사를 추가하는 일"
date: 2026-09-13 02:43:33 +0900
categories: [kubernetes, kafka]
tags: [strimzi, crd, custom-resource, operator, kafka, gitops]
---

집 K3s 클러스터의 `kafka` 네임스페이스를 GitOps 로 옮기다가, 옮길 수 **없는** 것 11개를
만났다. Strimzi 가 설치해 둔 CRD 들이다. "CRD 가 정확히 뭐길래 네임스페이스 앱에 못 담기나"
를 정리한다. 숫자는 전부 내 클러스터에서 실측한 값이고, 재현 명령을 같이 적는다.

## 1. CRD 는 API 서버에 엔드포인트를 하나 늘리는 것

쿠버네티스 공식 문서의 정의는 건조하다.

> A custom resource is an extension of the Kubernetes API that is not necessarily available
> in a default Kubernetes installation.
> — [Custom Resources, kubernetes.io](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)

CRD(`CustomResourceDefinition`)를 만들면 API 서버가 그 종류(kind)에 대한 **REST 경로를 새로
연다.**

> When you create a new CustomResourceDefinition (CRD), the Kubernetes API Server creates a
> new RESTful resource path for each version you specify.
> — [Extend the Kubernetes API with CustomResourceDefinitions, kubernetes.io](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)

여기서 중요한 건 **CRD 는 저장소일 뿐이라는 것**이다. 같은 문서가 못을 박는다.

> On their own, custom resources let you store and retrieve structured data. When you combine
> a custom resource with a custom controller, custom resources provide a true declarative API.

즉 CRD 는 `kind: Kafka` 라는 **명사**를 등록할 뿐이고, 그 명사를 읽고 실제로 브로커를 띄우는
**동사**는 별개의 컨트롤러(오퍼레이터)가 한다. 이 둘을 하나로 착각하면 뒤의 함정에 전부 걸린다.

## 2. Strimzi 가 등록하는 명사는 11개다

```bash
kubectl get crd -o json | jq -r '.items[]
  | select(.spec.group | endswith("strimzi.io"))
  | [.spec.names.kind, .spec.names.plural, .spec.scope,
     ([.spec.versions[].name] | join(","))] | @tsv'
```

내 클러스터(오퍼레이터 이미지 `quay.io/strimzi/operator:0.51.0`) 실측 결과:

| kind | plural | scope | 제공 버전 |
| --- | --- | --- | --- |
| `Kafka` | kafkas | Namespaced | v1, v1beta2 |
| `KafkaNodePool` | kafkanodepools | Namespaced | v1, v1beta2 |
| `KafkaTopic` | kafkatopics | Namespaced | v1, v1beta2, v1beta1, v1alpha1 |
| `KafkaUser` | kafkausers | Namespaced | v1, v1beta2, v1beta1, v1alpha1 |
| `KafkaConnect` | kafkaconnects | Namespaced | v1, v1beta2 |
| `KafkaConnector` | kafkaconnectors | Namespaced | v1, v1beta2 |
| `KafkaMirrorMaker2` | kafkamirrormaker2s | Namespaced | v1, v1beta2 |
| `KafkaMirrorMaker` | kafkamirrormakers | Namespaced | v1beta2 |
| `KafkaBridge` | kafkabridges | Namespaced | v1, v1beta2 |
| `KafkaRebalance` | kafkarebalances | Namespaced | v1, v1beta2 |
| `StrimziPodSet` | strimzipodsets | Namespaced | v1, v1beta2 |

이 11개 객체를 JSON 으로 직렬화해 크기를 재면 합계 **약 1.7MB** 다(위 명령을 `jq -c '.items[]
| select(...)' | wc -c` 로 바꾸면 같은 값이 나온다). 대부분이 `Kafka`(453KB)와
`KafkaMirrorMaker2`(345KB)의 **OpenAPI v3 스키마**다. `apiextensions.k8s.io/v1` 에서는
구조적 스키마(structural schema)가 **필수**라서, Kafka 의 온갖 설정 항목이 전부 스키마로
박혀 있다. 그래서 `kubectl apply` 시점에 오타가 API 서버에서 막힌다 — 브로커가 뜨고 나서
죽는 게 아니라.

`KafkaTopic` 과 `KafkaUser` 만 `v1alpha1` 까지 네 버전을 물고 있는 게 눈에 띈다. 가장 오래
전에 생긴 명사라서 하위 호환을 길게 끌고 가는 것이다.

## 3. CR 하나가 자식 23개를 낳는다

정의만으로는 감이 안 온다. 내 `kafka` 네임스페이스에는 사람이 쓴 CR 이 딱 셋이다 —
`Kafka/lemuel`, `KafkaNodePool/dual-role`, `KafkaTopic/notification-topic`. 오퍼레이터가
이걸 보고 만들어 낸 것들은 `ownerReferences` 로 구분된다.

```bash
kubectl -n kafka get deploy,svc,cm,secret,sa,role,rolebinding,strimzipodset -o json \
  | jq -r '.items[] | select(.metadata.ownerReferences)
    | "\(.kind)/\(.metadata.name)  <- \(.metadata.ownerReferences[0].kind)/\(.metadata.ownerReferences[0].name)"'
```

세어 보면 **23개**다. `Kafka/lemuel` 직계 21개(Service 2, Secret 9, ConfigMap 2,
ServiceAccount 2, Role 2, RoleBinding 3, Deployment 1) + `KafkaNodePool/dual-role` 직계
2개(`StrimziPodSet/lemuel-dual-role`, ConfigMap 1). 브로커 Pod 는 다시 그 StrimziPodSet 의
자식이다.

Secret 9개 중 `lemuel-cluster-ca` / `lemuel-clients-ca` 계열이 **CA 와 인증서**다. Kafka 를
직접 StatefulSet 으로 짰다면 mTLS 용 CA 를 만들고 돌리고 갱신하는 걸 전부 손으로 해야 한다.
CRD + 오퍼레이터가 가져가는 건 결국 **이 도메인 지식**이다. 공식 문서 표현대로
"encode domain knowledge for specific applications into an extension of the Kubernetes API".

여기서 처음 사람을 놀라게 하는 지점: **`kubectl get all` 에 브로커가 안 보인다.** 정확히는
Pod 로는 보이는데 그걸 낳은 컨트롤러가 안 보인다. Strimzi 는 StatefulSet 을 쓰지 않고
자기 CRD 인 `StrimziPodSet` 으로 브로커 Pod 를 관리하기 때문이다. `kubectl get all` 은
빌트인 kind 만 나열하므로, CRD 로 늘린 명사는 이름을 알고 물어봐야 나온다.

```bash
kubectl -n kafka get strimzipodset
```

## 4. 그래서 GitOps 로 못 옮겼다

문제의 발단은 이것이었다. `kafka` 네임스페이스를 ArgoCD Application 으로 채택하면서
"이 앱만으로 빈 클러스터에 Kafka 를 재구축할 수 있는가"를 물었더니, 답은 **아니오** 였다.
CRD 가 빠져 있기 때문이다. 그리고 CRD 는 원리적으로 그 앱에 담을 수 없다.

> CustomResourceDefinitions themselves are non-namespaced and are available to all namespaces.
> — kubernetes.io

CRD 는 **클러스터 스코프**다. 네임스페이스 하나에 스코프된 앱의 소유물이 될 수 없다.
Strimzi 문서도 같은 경고를 한다 — 네임스페이스를 나눠도 "certain resources managed by the
Strimzi operator, such as Custom Resource Definitions (CRDs) and roles, have a cluster-wide
scope" 라서 오퍼레이터를 여러 개 깔면 충돌한다고.

그럼 CRD 는 누가 소유하나. **오퍼레이터 설치 번들**이다. Strimzi 배포 문서는
`install/cluster-operator` 한 디렉터리를 `kubectl apply` 하면 CRD · RBAC · Deployment ·
ServiceAccount 가 한꺼번에 깔린다고 적는다. CRD 는 그 번들의 일부이지, Kafka 클러스터의
일부가 아니다.

내 클러스터의 CRD 가 실제로 번들로 깔렸다는 것도 확인된다.

```bash
kubectl get crd kafkas.kafka.strimzi.io -o json | jq '.metadata.labels, (.metadata.annotations | keys)'
```

라벨은 `app: strimzi`, `strimzi.io/crd-install: "true"` 이고, 어노테이션에는
`kubectl.kubernetes.io/last-applied-configuration` **하나뿐**이다. Helm 이 설치했다면
`meta.helm.sh/release-name` 이 붙어 있어야 하는데 없다. 즉 helm release 가 아니라
YAML 번들을 직접 apply 한 것이고, 되돌리려면 **helm 이 아니라 0.51.0 번들을 다시 적용해야
한다.** 이게 내가 남긴 "아직 안 메운 구멍" 의 정확한 형태다.

여기서 흔한 오답이 있다. CRD YAML 을 `kubectl get crd -o yaml` 로 떠서 git 에 넣으면 되지
않나? 된다. 그리고 **썩는다.** 그 스냅샷은 0.51.0 시점의 스키마고, 오퍼레이터를 0.52 로
올리는 순간 git 의 CRD 가 오퍼레이터보다 낡아진다. CRD 는 오퍼레이터의 **버전과 한 몸**이라,
버전이 붙은 설치 번들을 참조로 기록하는 게 맞지 손으로 뜬 스냅샷을 두는 게 아니다.

## 5. 가장 비싼 함정 — CRD 를 지우면 CR 이 같이 죽는다

공식 문서가 한 문장으로 경고한다.

> When you delete a CustomResourceDefinition, the server will uninstall the RESTful API
> endpoint and **delete all custom objects stored in it.**

`kubectl delete crd kafkas.kafka.strimzi.io` 는 "정의를 지운다" 가 아니라 **"이 클러스터의
모든 Kafka 클러스터를 지운다"** 이다. 확인 프롬프트도 없고, `Kafka` CR 이 사라지면 그 자식
23개가 ownerReference 따라 연쇄로 GC 된다. CA Secret 까지 포함해서.

그래서 CRD 를 GitOps 에 넣을 때 `prune` 을 켜는 건 위험하다. 내가 채택한 앱들을
`prune: false` 로 둔 이유가 이것이다 — 파일 하나를 잘못 옮기면 삭제가 **실물에 전파**된다.
자동 정리는 실수를 자동으로 증폭한다.

## 정리

- CRD 는 API 서버에 **명사를 하나 등록하는 것**이다. 동사는 오퍼레이터가 한다.
- Strimzi 는 명사를 11개 등록한다. 부피의 대부분은 apply 시점 검증을 해 주는 OpenAPI 스키마다.
- `Kafka` CR 하나가 `ownerReferences` 로 연결된 자식 23개를 만든다. 그중 9개가 인증서다 —
  이 도메인 지식의 이전이 CRD 를 쓰는 실질적 이유다.
- CRD 는 클러스터 스코프라 네임스페이스 GitOps 앱의 소유물이 될 수 없다. 오퍼레이터
  설치 번들이 소유자다.
- CRD 삭제 = 그 kind 의 모든 객체 삭제. 이 한 줄이 `prune: false` 의 근거다.

## References

- Kubernetes, *Custom Resources* — <https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/>
- Kubernetes, *Extend the Kubernetes API with CustomResourceDefinitions* — <https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/>
- Kubernetes API Reference, *CustomResourceDefinition v1* — <https://kubernetes.io/docs/reference/kubernetes-api/apiextensions/custom-resource-definition-v1/>
- Strimzi, *Deploying and Managing Strimzi* (§1.1 Strimzi custom resources, §1.2 Strimzi operators, §6.2 operator deployment best practices, §7.1 Deploying the Cluster Operator) — <https://strimzi.io/docs/operators/latest/full/deploying.html>
- Strimzi, *Custom Resource API Reference* — <https://strimzi.io/docs/operators/latest/full/configuring.html>
- strimzi/strimzi-kafka-operator (GitHub) — <https://github.com/strimzi/strimzi-kafka-operator>

*본문의 수치(CRD 11개, 직렬화 합계 약 1.7MB, 자식 리소스 23개, 오퍼레이터 0.51.0)는 필자의
K3s 클러스터에서 위에 적은 명령으로 직접 측정한 값이다. 다른 Strimzi 버전·구성에서는 달라진다.*
