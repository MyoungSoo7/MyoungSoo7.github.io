---
layout: post
title: "OnPrem 모델 서빙 플랫폼 보안 정리 — vLLM·Ray Serve·Triton·BentoML·KServe·OpenLLM"
date: 2026-10-26 03:18:49 +0900
categories: [AI, MLOps, Kubernetes, Security]
tags: [OnPrem, Model Serving, vLLM, Ray Serve, Triton, BentoML, KServe, OpenLLM]
---

> 이 글은 [라빔님의 네이버 글](https://m.blog.naver.com/PostView.naver?blogId=pty115&logNo=224453501478)을 읽고, 핵심 논점을 독립적으로 재구성한 기술 정리다. 원문을 복제하지 않고, 공식 플랫폼 문서와 대조해 사실·해석·미확인 범위를 구분한다.

## 결론

OnPrem 모델 서빙의 장점은 **추론 데이터와 모델을 조직 내부에서 통제하기 쉬운 것**이지, 배포 직후 자동으로 보안이 완성된다는 뜻은 아니다. 실제 보안 수준은 **인증·TLS·네트워크 격리·감사 로그·PII 처리·모델 공급망·모델 저장소 권한**을 운영자가 직접 설계했는지에 달려 있다.[1][2][3][4][6]

가장 현실적인 원칙은 다음과 같다.

```text
외부 모델 다운로드
→ 내부 검증·레지스트리 저장
→ private model repository
→ 인증된 gateway
→ mTLS·RBAC·NetworkPolicy
→ 구조화 감사 로그·PII 통제
→ 출력·비용·지연·모델 버전 관측
```

## 1. 왜 OnPrem인가

Cloud LLM은 리전, 네트워크 경로, 계약, 로그 보존, API 설정으로 데이터 주권을 통제해야 한다. OnPrem은 추론 요청을 내부 GPU 서버나 Kubernetes·베어메탈 클러스터에서 처리하는 구조를 기본으로 삼을 수 있어 데이터가 조직 경계를 넘어가는 경로를 줄인다.[1]

그러나 “외부 전송이 기본적으로 없다”와 “아무 데이터도 외부로 나가지 않는다”는 다르다.

- 모델 최초 다운로드
- 컨테이너 이미지 pull
- 패키지 설치
- 외부 telemetry
- 외부 object storage
- 관리자·운영자의 로그 반출

에어갭을 요구한다면 위 경로를 모두 확인하고, 모델·이미지·패키지를 내부 Nexus·Harbor·S3 호환 저장소 등으로 반입한 뒤 외부 egress를 차단해야 한다. 원문도 Hugging Face·NGC 등에서 모델을 가져오는 초기 공급망을 별도 검토해야 한다고 지적한다.[1]

## 2. 플랫폼별 역할과 보안 관점

| 플랫폼 | 기본 역할 | 유리한 환경 | 핵심 보안 확인점 |
| --- | --- | --- | --- |
| vLLM | OpenAI 호환 LLM 추론 서버 | 단일·고성능 LLM API | API key, TLS/gateway, 모델 revision, remote code, 로그·rate limit |
| Ray Serve | Python 기반 분산 서빙·오케스트레이션 | 여러 모델·분산 애플리케이션 | Dashboard·Jobs·Client 접근제어, token auth, 네트워크 격리 |
| NVIDIA Triton | 다중 모델·GPU 추론 서버 | LLM·임베딩·비전 혼합 워크로드 | model repository 권한, model load API, HTTP/gRPC/TLS, metrics·trace 노출 |
| BentoML | 모델 패키징·배포 프레임워크 | Python MLOps·Bento 단위 배포 | 서비스 인증, 이미지·아티팩트 서명, secret·env, 배포 플랫폼 권한 |
| KServe | Kubernetes 네이티브 모델 서빙 추상화 | 기존 K8s·Istio·멀티테넌시 | K8s RBAC, NetworkPolicy, Istio mTLS·AuthorizationPolicy, storage secret |
| OpenLLM | LLM을 API 서비스로 패키징 | 간단한 LLM 배포·실험 | 기본 인증, 이미지·모델 출처, ingress·TLS, 로그·리소스 제한 |

이 표는 제품의 절대적인 우열이 아니라, 각 구성요소가 보안 책임을 어디에 남기는지에 대한 설계 관점이다. KServe는 Istio와 연동해 mTLS·트래픽 관리·authorization policy·observability를 구성할 수 있다.[3] Triton은 HTTP/REST·gRPC·모델 저장소를 제공하지만, 공식 보안 문서는 신뢰되지 않은 네트워크에 Triton을 직접 노출하지 말고 gateway·proxy에서 인증·인가·암호화·자원관리를 처리하라고 권고한다.[4]

## 3. 인증과 네트워크 노출

### vLLM

vLLM은 OpenAI 호환 HTTP API를 제공하고 `--api-key`로 요청 헤더 인증을 요구할 수 있다.[2] 그러나 API key 하나가 곧 사용자별 RBAC·감사 체계가 되는 것은 아니다.

```bash
vllm serve <approved-model> \
  --host 127.0.0.1 \
  --port 8000 \
  --api-key <secret>
```

운영 환경에서는 비밀값을 명령행에 직접 남기지 말고 Secret·vault·gateway를 사용한다. 외부 사용자 인증, 사용자별 quota, tenant 분리, TLS 종료, audit correlation ID는 앞단 gateway 또는 service mesh에서 별도로 설계한다.

### Ray Serve

Ray Dashboard·Jobs·Client 같은 관리 표면은 단순 모니터링 UI가 아니라 클러스터와 실행 자원에 접근할 수 있는 민감한 경로다. Ray 공식 보안 문서는 이 표면이 임의 코드 실행으로 이어질 수 있으므로 신뢰된 사용자만 접근하도록 통제해야 한다고 경고한다.[6]

따라서 Dashboard를 `0.0.0.0`으로 열고 인증 없이 인터넷이나 사내 전체망에 노출하는 방식은 피해야 한다. 방화벽·NetworkPolicy·인증 proxy·token authentication을 함께 적용하고, 사용하지 않는 관리 포트는 닫는다.

### Triton

Triton은 모델 repository와 model control API가 특히 중요하다. 공식 문서는 동적 모델 repository 업데이트나 model load/unload API가 잘못 노출되면 임의 코드 실행 위험이 생길 수 있으므로, 저장소와 제어 API 접근을 신뢰된 운영자에게만 제한하라고 설명한다.[4]

```text
Client
  ↓ TLS·인증·인가
Gateway / Ingress
  ↓ private network
Triton
  ↓ read-only 또는 제한된 접근
Model Repository
```

Triton 공식 문서는 필요하지 않은 HTTP·gRPC·metrics·trace·logging API를 노출하지 말고, TLS·mTLS와 restricted API를 사용하라고 안내한다.[4]

## 4. 개인정보와 감사 로그

추론 요청이 외부로 나가지 않아도 내부 로그에 개인정보가 남을 수 있다. 프롬프트·응답·사용자 ID·IP·문서 내용·검색 결과가 모두 감사 대상이 될 수 있다.

### 최소 감사 이벤트

```json
{
  "request_id": "redacted",
  "principal": "redacted",
  "model_id": "approved-model@digest",
  "model_revision": "immutable-revision",
  "timestamp": "2026-10-26T03:18:49+09:00",
  "input_policy": "pii-redaction-v1",
  "status": "success",
  "latency_ms": 0,
  "tokens": "policy-dependent"
}
```

운영 로그에 프롬프트·응답 전문을 무조건 저장하는 것은 감사성보다 개인정보 위험을 키울 수 있다. 기본값은 다음처럼 분리하는 편이 안전하다.

- 일반 운영: 메타데이터·해시·token 수·지연·상태코드
- 보안 조사: 승인된 시간창·승인된 요청만 제한적 원문 보존
- 개인정보: 수집 최소화·마스킹·보존기간·접근권한 명시
- 디버깅: 샘플링과 별도 보호 저장소 사용

PII 탐지·마스킹은 서빙 엔진의 기본 기능이라고 가정하지 말고 gateway 전처리·정책 엔진·DLP 파이프라인으로 검증해야 한다.[1]

## 5. 모델 공급망 보안

OnPrem의 가장 큰 오해는 GPU 서버 안에 모델 파일이 있으면 안전하다는 생각이다. 위험은 모델을 받는 순간부터 시작된다.

### 공급망 통제 흐름

1. 허용 모델·제공자·라이선스 목록 작성
2. 외부 모델을 격리된 수집 환경에서 다운로드
3. 파일 hash·서명·revision·출처 기록
4. 악성 파일·압축 폭탄·원격 코드·license 검사
5. 내부 Harbor·Nexus·MinIO·NFS에 승인 아티팩트 저장
6. 배포 파이프라인은 내부 아티팩트만 읽도록 제한
7. runtime에 immutable digest와 모델 버전 기록
8. 모델 교체 시 재검토·승인·rollback 준비

vLLM의 공식 문서에는 Hugging Face 모델 revision 지정과 remote code 관련 설정이 제공되며, 신뢰되지 않은 remote code를 무심코 활성화하지 않는 것이 중요하다.[2] Triton도 실행 가능한 model/backend code와 model repository 접근을 신뢰된 출처·운영자에 한정하라고 명시한다.[4]

## 6. Kubernetes에 배치할 때의 기준

KServe는 Kubernetes·Istio와 결합해 모델 배포·트래픽·보안정책을 인프라 계층에서 다룰 수 있는 선택지다.[3] 하지만 Kubernetes 위에 올렸다는 사실만으로 안전해지지 않는다.

```text
Namespace 분리
  + ServiceAccount 최소권한
  + RBAC
  + NetworkPolicy
  + Istio STRICT mTLS
  + AuthorizationPolicy
  + private model storage
  + resource limit/quotas
  + audit·metrics·trace 보호
```

특히 모델 서빙은 GPU·메모리·파일 시스템·네트워크를 많이 사용하므로 다음을 함께 검증해야 한다.

- 모델 Pod가 접근 가능한 Secret·PVC 범위
- Ingress와 내부 Service의 노출 범위
- GPU 노드에 대한 workload 격리
- 모델 저장소 credential의 만료·rotation
- Prompt/response 로그의 namespace·tenant 분리
- NetworkPolicy가 model storage·gateway·observability만 허용하는지
- scale-out 시 새 replica가 동일한 정책을 받는지

## 7. 플랫폼 선택의 현실적인 조합

### 단일 모델·빠른 시작

```text
vLLM
 + private network
 + 인증 gateway
 + 내부 model registry
 + 구조화 로그
```

vLLM은 OpenAI 호환 API가 필요하고 단일 또는 소수의 LLM을 빠르게 서빙할 때 출발점으로 적합하다. 단, API key만 추가하고 운영 보안이 끝났다고 판단하면 안 된다.[2]

### Kubernetes 표준화

```text
KServe
  + vLLM 또는 Triton backend
  + Istio mTLS
  + K8s RBAC/NetworkPolicy
  + 내부 object storage
```

기존 K8s·Istio·관측 체계가 있다면 KServe를 표준 진입점으로 두고 실제 추론 엔진은 vLLM·Triton 중 workload에 맞게 선택할 수 있다.[3]

### 혼합 GPU 워크로드

```text
Triton
 + 제한된 model repository
 + inference-only public surface
 + gateway-mediated model control
 + metrics/trace 최소 노출
```

LLM뿐 아니라 임베딩·비전·분류 모델을 같은 GPU 풀에서 운영한다면 Triton의 모델 저장소·프로토콜·health·metrics 구성을 검토할 수 있다. 단, model repository와 동적 load API는 가장 강하게 보호해야 한다.[4]

### Ray 기반 분산 Python 서비스

Ray Serve는 Python 애플리케이션과 분산 서빙을 결합할 때 유용할 수 있지만, Dashboard·Jobs·Client 표면의 권한을 먼저 설계해야 한다. Ray 공식 문서가 강조하듯 이 표면은 임의 코드 실행 위험을 가지므로 네트워크 격리와 인증은 선택사항이 아니다.[6]

### BentoML·Yatai

BentoML·Yatai는 모델과 서빙 코드를 패키징하고 Kubernetes에 배포·운영하는 흐름을 제공한다.[5] 이 조합을 선택할 경우 Bento 이미지·모델 아티팩트의 provenance, registry 접근권한, 배포 API·secret·서비스 인증을 검증해야 한다.

## 8. 보안 검증 체크리스트

### 배포 전

- [ ] 모델 출처·license·revision·hash 확인
- [ ] 내부 registry에 승인 아티팩트 저장
- [ ] 외부 egress·모델 다운로드 경로 차단 또는 승인
- [ ] 인증·TLS·mTLS 설계
- [ ] model control API의 관리자 전용화
- [ ] PII 로깅·마스킹·보존정책 결정
- [ ] NetworkPolicy·RBAC·ServiceAccount 작성

### 운영 중

- [ ] 모델 ID·digest·revision read-back
- [ ] request ID·principal·status·latency·token 메트릭
- [ ] 401/403/429/5xx와 timeout 분리
- [ ] 모델 저장소 변경 이벤트 감사
- [ ] prompt·response 원문 노출 여부 점검
- [ ] GPU·메모리·queue·batch·tail latency 관측
- [ ] 모델 rollback과 credential rotation 테스트

### 사고 대응

- [ ] 의심 모델 endpoint 격리
- [ ] model repository write·load API 차단
- [ ] gateway·K8s·Triton·Ray·Ingress 로그 시간 정렬
- [ ] 영향받은 모델 digest와 replica 식별
- [ ] secret·token rotation
- [ ] 외부 반출·PII 노출 여부 확인
- [ ] clean artifact로 재배포 후 read-back

## 최종 판단

원문이 제시한 핵심 대비는 유효하다. Cloud는 보안 인프라를 서비스로 활용하고, 로컬 런타임은 최소한의 개발 편의성에서 시작하며, OnPrem 서빙은 데이터 통제권과 함께 보안 운영 책임을 조직이 가져온다.[1]

다만 플랫폼을 선택하는 것만으로 보안 수준이 결정되지는 않는다. **“KServe라서 안전하다”, “vLLM은 내부망이라 안전하다”, “Triton은 NVIDIA라 안전하다” 같은 문장은 근거가 부족하다.** 실제 판정은 인증·경로·저장소·로그·모델 digest·정책·read-back Trace로 내려야 한다.

## 확인된 사실과 미확인 범위

- **원문 확인:** OnPrem 모델 서빙을 vLLM·Ray Serve·NVIDIA Triton·BentoML·KServe·OpenLLM 관점에서 데이터 주권·개인정보·접근·감사·모델 공급망으로 비교한다.[1]
- **공식 문서 대조:** vLLM API key, KServe Istio 통합, Triton model repository 보안, Yatai 배포, Ray 보안 경고를 공식 문서로 교차 확인했다.[2][3][4][5][6]
- **해석:** 플랫폼별 최적 조합과 체크리스트는 문서 사실을 운영 설계로 재구성한 것이다.
- **미확인:** 원문에 언급된 실제 프로덕션 채택 비중, 특정 기업의 내부 구성, 모델별 성능·비용·보안 수준은 이 글에서 독립 검증하지 않았다.

## 참고 자료

[1] [네이버 블로그 — OnPrem 모델 서빙 플랫폼, '보안적으로 안전하게' 쓸 수 있을까](https://m.blog.naver.com/PostView.naver?blogId=pty115&logNo=224453501478&proxyReferer=&noTrackingCode=true)

[2] [vLLM — OpenAI-Compatible Server](https://docs.vllm.ai/en/v0.22.0/serving/online_serving/openai_compatible_server/)

[3] [KServe — Integrations](https://kserve.github.io/website/docs/reference/integrations)

[4] [NVIDIA Triton — Secure Deployment Considerations](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/customization_guide/deploy.html)

[5] [Yatai — Model Deployment at Scale on Kubernetes](https://docs.yatai.io/en/latest/)

[6] [Ray — Security](https://docs.ray.io/en/master/ray-security/index.html)

> ※ 원문에 포함된 사설 네트워크·개인 식별자·비밀값은 재게시하지 않았다.

## Sources

[1] https://m.blog.naver.com/PostView.naver?blogId=pty115&logNo=224453501478&proxyReferer=&noTrackingCode=true
[2] https://docs.vllm.ai/en/v0.22.0/serving/online_serving/openai_compatible_server
[3] https://kserve.github.io/website/docs/reference/integrations
[4] https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/customization_guide/deploy.html
[5] https://docs.yatai.io/en/latest
[6] https://docs.ray.io/en/master/ray-security/index.html
