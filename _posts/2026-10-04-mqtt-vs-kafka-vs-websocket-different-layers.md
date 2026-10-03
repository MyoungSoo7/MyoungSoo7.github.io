---
layout: post
title: "MQTT vs Kafka vs WebSocket — 셋은 왜 경쟁자가 아니라 서로 다른 층인가?"
date: 2026-10-04 00:14:14 +0900
categories: [Architecture, Messaging]
tags: [MQTT, Kafka, WebSocket, IoT, Event Streaming, Pub/Sub, Architecture]
---

"실시간 데이터를 주고받아야 하는데 MQTT, Kafka, WebSocket 중 뭘 써야 하나요?" 자주 나오는 질문이다. 그런데 이 질문에는 함정이 있다. **셋은 같은 문제를 푸는 경쟁 제품이 아니다.** 하나는 통로(transport), 하나는 메시징 프로토콜, 하나는 이벤트 저장소에 가깝다.

이 글은 세 기술을 표준·공식 문서가 스스로를 어떻게 정의하는지에서 출발해 비교하고, 홈랩 IoT 실험에서 MQTT 만 쓰고 Kafka 를 쓰지 않은 이유까지 정리한다.

| | WebSocket | MQTT | Kafka |
|---|---|---|---|
| 본질 | 브라우저와 서버 사이의 **양방향 통로** | 기기를 위한 **발행/구독 메시징 프로토콜** | **이벤트를 저장하는** 분산 스트리밍 플랫폼 |
| 정의한 곳 | IETF RFC 6455[^rfc6455] | OASIS 표준(3.1.1, 5.0)[^mqtt5] | Apache Kafka 프로젝트[^kafka] |
| 메시지 의미 | 없음 (프레임만 운반) | 토픽, QoS 0/1/2, retain, Last Will | 토픽·파티션, 오프셋 |
| 소비 후 데이터 | 남지 않음 | 남지 않음 (retain 은 토픽당 마지막 1건) | **남음** (보존 기간 동안) |
| 다시 읽기(replay) | 불가 | 불가 | 가능 |
| 주 클라이언트 | 웹 브라우저 | 센서·임베디드 기기·모바일 | 서버·마이크로서비스 |

## 1. WebSocket — 통로일 뿐, 메시징이 아니다

RFC 6455 는 WebSocket 을 이렇게 소개한다.[^rfc6455]

> *"The protocol consists of an opening handshake followed by basic message framing, layered over TCP. The goal of this technology is to provide a mechanism for browser-based applications that need two-way communication with servers that does not rely on opening multiple HTTP connections..."*

핵심어는 **브라우저**와 **양방향**이다. WebSocket 은 HTTP 로 시작해 TCP 위에 메시지 프레임을 얹은 통로를 연다. 그 안에 무엇을, 누구에게, 몇 번 보낼지는 정하지 않는다. 토픽도, 구독도, 재전송 보장도 없다. 그런 의미 체계는 그 위에 올라가는 프로토콜이나 애플리케이션이 만들어야 한다.

그래서 "WebSocket vs MQTT" 는 사실 층이 다른 비교다. 실제로 MQTT 5.0 표준에는 **MQTT 를 WebSocket 위로 실어 나르는 방법**이 별도 장(6장, *Using WebSocket as a network transport*)으로 들어 있다.[^mqtt5] 브라우저 대시보드가 MQTT 브로커에 직접 붙을 때 쓰는 방식이다.

## 2. MQTT — 작은 기기를 위한 발행/구독

MQTT 5.0 표준의 첫 문장은 이렇다.[^mqtt5]

> *"MQTT is a Client Server publish/subscribe messaging transport protocol. It is light weight, open, simple, and designed to be easy to implement. These characteristics make it ideal for use in many situations, including constrained environments such as for communication in Machine to Machine (M2M) and Internet of Things (IoT) contexts where a small code footprint is required and/or network bandwidth is at a premium."*

WebSocket 과 달리 MQTT 에는 **메시징의 의미**가 들어 있다.

- **토픽과 구독** — 발행자는 받는 쪽을 모르고, 브로커가 구독자에게 나눠 준다.
- **세 단계의 전달 보장(QoS)** — 표준은 QoS 0 을 이렇게 설명한다: *"'At most once', where messages are delivered according to the best efforts of the operating environment. Message loss can occur. This level could be used, for example, with ambient sensor data where it does not matter if an individual reading is lost as the next one will be published soon after."* QoS 1 은 최소 한 번, QoS 2 는 정확히 한 번이다.
- **retain** — 토픽의 마지막 메시지를 브로커가 들고 있다가 새 구독자에게 준다.
- **Last Will** — 기기가 비정상적으로 사라지면 브로커가 대신 "offline" 을 알린다. ([이전 글](/2026/10/04/mqtt-keep-alive-last-will-silent-device/)에서 실제 사례로 다뤘다.)

그리고 MQTT 가 **하지 않는 일**도 분명하다. 브로커는 메시지를 구독자에게 전달하는 중개자이지, **기록 보관소가 아니다.** 지난 1시간의 센서값을 다시 읽고 싶어도 MQTT 만으로는 할 수 없다. retain 은 토픽당 마지막 한 건뿐이다.

## 3. Kafka — 지워지지 않는 이벤트 로그

Kafka 공식 소개는 스스로를 "event streaming platform" 이라 부르며 세 가지 능력을 든다.[^kafka]

> *"To publish (write) and subscribe to (read) streams of events... To store streams of events durably and reliably for as long as you want. To process streams of events as they occur or retrospectively."*

MQTT 와 가장 크게 다른 건 두 번째 줄, **저장**이다. 같은 문서는 이렇게 강조한다.

> *"Events in a topic can be read as often as needed—unlike traditional messaging systems, events are not deleted after consumption. Instead, you define for how long Kafka should retain your events through a per-topic configuration setting, after which old events will be discarded."*

이 성질 덕분에 Kafka 에서는 **새 소비자가 과거부터 다시 읽을 수 있고**, 여러 시스템이 같은 이벤트를 각자의 속도로 읽는다. 순서 보장도 파티션 단위로 명시돼 있다: *"Kafka guarantees that any consumer of a given topic-partition will always read that partition's events in exactly the same order as they were written."*[^kafka]

대신 Kafka 클라이언트는 서버 간 통신을 전제로 한다. 공식 문서는 Kafka 를 *"a distributed system consisting of servers and clients that communicate via a high-performance TCP network protocol"* 이라고 설명한다.[^kafka] 서버 간 통신을 전제로 한 설계이니, 메모리와 대역폭이 빠듯한 작은 기기 앞에는 MQTT 같은 게이트웨이를 두는 편이 자연스럽다.

## 4. 그래서 실제로는 겹쳐 쓴다

세 기술이 층이 다르다는 걸 받아들이면, 흔한 IoT 구조가 자연스럽게 나온다.

```
[센서·기기] ──MQTT──▶ [MQTT 브로커] ──브리지──▶ [Kafka] ──▶ 저장·분석·알림 서비스들
                                │
                                └──MQTT over WebSocket──▶ [브라우저 대시보드]
```

- 기기 쪽은 **MQTT**: 가볍고, Last Will 로 생사를 알고, QoS 로 전달 수준을 고른다.
- 서버 쪽은 **Kafka**: 이벤트를 쌓아 두고, 여러 소비자가 다시 읽는다.
- 화면 쪽은 **WebSocket**: 브라우저가 실시간 값을 받는 통로. 그 위에 MQTT 를 얹거나 자체 메시지를 정의한다.

## 5. 우리 홈랩은 왜 MQTT 만 쓰나

홈랩 IoT 보안 실험은 지금 **MQTT 하나**로 돈다. 센서가 달린 노트북 한 대가 10초마다 가속도 값을, 60초마다 전원 상태를 보내고, 브로커 옆의 탐지기가 이를 실시간으로 보고 이상하면 텔레그램으로 알린다.

Kafka 를 넣지 않은 이유는 단순하다. 지금 요구사항에 **저장과 다시 읽기가 없기** 때문이다. 탐지기는 들어오는 값을 바로 판정하고, 지난 데이터를 되돌려 볼 일이 없다. 이 상태에서 Kafka 를 넣으면 운영할 클러스터가 하나 늘 뿐, 얻는 게 없다.

반대로 이런 요구가 생기면 Kafka 를 고려할 때다.

1. "어젯밤 연결이 끊기기 직전 10분의 가속도 값을 보고 싶다" — **재생(replay)** 이 필요하다.
2. 탐지기 말고도 대시보드, 장기 저장, 학습용 데이터 수집처럼 **소비자가 여럿**이 되고, 각자 다른 속도로 읽어야 한다.
3. 소비자가 잠시 죽어도 그동안의 이벤트를 **잃으면 안 된다.**

1번만 필요하다면 MQTT 수집기가 시계열 DB 에 쓰는 것으로도 충분할 수 있다. Kafka 는 2·3번이 같이 올 때 제값을 한다.

## 6. 고르는 질문 네 가지

| 질문 | 예 → | 아니오 → |
|---|---|---|
| 상대가 웹 브라우저인가? | WebSocket (필요하면 그 위에 MQTT) | 다음 질문 |
| 상대가 작고 많은 기기이고, 생사·전달 보장이 중요한가? | MQTT | 다음 질문 |
| 지나간 이벤트를 다시 읽거나, 여러 소비자가 각자 읽어야 하나? | Kafka | 단순 요청/응답이면 HTTP 로도 충분 |
| 둘 이상에 해당하나? | 층을 나눠 **같이** 쓴다 | — |

## 맺으며 — 비교의 단위를 맞추자

"MQTT vs Kafka vs WebSocket" 이라는 질문이 헷갈리는 이유는, 셋이 모두 "실시간" 이라는 단어로 묶이기 때문이다. 하지만 표준 문서를 펼쳐 보면 각자 자기 일을 분명히 말한다. WebSocket 은 **브라우저의 양방향 통로**, MQTT 는 **작은 기기의 발행/구독**, Kafka 는 **지워지지 않는 이벤트 로그**다.

기술 선택에서 비싼 실수는 대개 **층을 잘못 고르는 것**에서 나온다. 브라우저 통로에 메시지 보장을 기대하거나, 센서 수천 개를 Kafka 에 직접 붙이거나, 다시 읽어야 할 데이터를 MQTT 에만 흘려보내는 식이다. 질문을 "어느 게 더 좋은가" 에서 **"어느 층에 무엇이 필요한가"** 로 바꾸면, 대부분의 경우 답은 하나가 아니라 조합이다.

---

## References

[^rfc6455]: I. Fette, A. Melnikov, *RFC 6455: The WebSocket Protocol*, IETF, December 2011. <https://www.rfc-editor.org/rfc/rfc6455>
[^mqtt5]: OASIS, *MQTT Version 5.0* (OASIS Standard, 2019) — Abstract/Introduction, 4.3 Quality of Service, 6 Using WebSocket as a network transport. <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>
[^kafka]: Apache Kafka, *Introduction*. <https://kafka.apache.org/intro>
