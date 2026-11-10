---
layout: post
title: "WebSocket·Spring Boot·STOMP — 채팅 구조로 보는 STOMP의 사용사례"
date: 2026-11-10 23:57:55 +0900
categories: [backend, spring]
tags: [websocket, stomp, spring-boot, chat, rabbitmq, spring-security, messaging]
---

WebSocket을 붙이면 곧바로 이런 질문들이 따라옵니다. "이 메시지는 어느 방 거지?", "누가 이 방을 구독하고 있지?", "서버가 두 대가 되면?", "인증은 어디서 하지?" **STOMP는 이 질문들에 미리 정해진 답을 주는 하위 프로토콜**입니다. 이 글은 개념을 순서대로 짚고, 채팅 서비스를 만든다고 가정해 STOMP의 각 기능이 어디에 쓰이는지 살펴봅니다.

모든 설명은 [Spring Framework 레퍼런스](https://docs.spring.io/spring-framework/reference/web/websocket.html), [STOMP 1.2 명세](https://stomp.github.io/stomp-specification-1.2.html), [RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455) 같은 1차 문서를 근거로 합니다. 이 글에는 성능 측정이 없습니다.

## 1. 층부터 정리 — WebSocket은 파이프, STOMP는 그 위의 약속

| 층 | 무엇을 정하나 | 무엇을 정하지 *않나* |
|---|---|---|
| **WebSocket** ([RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)) | HTTP Upgrade로 연 **양방향 연결**과 메시지 프레이밍 | 메시지의 의미, 수신자, 라우팅 |
| **STOMP** ([1.2 명세](https://stomp.github.io/stomp-specification-1.2.html)) | `CONNECT`·`SUBSCRIBE`·`SEND`·`MESSAGE` 등 **명령 + 헤더 + 본문** 프레임, `destination` 헤더 | destination 문자열의 의미(서버가 정함), 전달 보장 수준 |
| **Spring** (`spring-messaging`, `spring-websocket`) | destination 접두사로 컨트롤러와 브로커에 라우팅, 사용자별 큐, 보안 | — |

RFC 6455는 WebSocket 위에서 쓸 응용 프로토콜을 `Sec-WebSocket-Protocol` 헤더(하위 프로토콜)로 협상하도록 열어 둡니다. 하지만 *무엇을* 얹을지는 정하지 않습니다. 그래서 날것의 WebSocket만 쓰면 메시지 형식, "어느 방" 라우팅, 구독 관리를 **매번 직접 발명**해야 합니다.

STOMP 프레임은 HTTP를 본떴습니다([Spring 문서](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/overview.html)).

```
SEND
destination:/app/chat.room.42
content-type:application/json

{"text":"안녕하세요"}^@
```

STOMP 명세는 destination을 **"불투명한 문자열"** 로 둡니다. 다만 관례상 `/topic/..` 은 1:N 발행·구독을, `/queue/..` 는 1:1을 뜻합니다. 서버는 클라이언트가 구독하지 않은 곳으로 메시지를 보낼 수 없습니다. 서버가 보내는 `MESSAGE` 프레임의 `subscription` 헤더는 클라이언트 `SUBSCRIBE` 의 `id` 와 일치해야 합니다.

Spring 문서가 꼽는 STOMP의 이점은 다섯 가지입니다([Benefits](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/benefits.html)).

1. 메시지 프로토콜과 형식을 새로 만들 필요가 없습니다.
2. Spring의 Java 클라이언트를 비롯해 STOMP 클라이언트가 이미 있습니다.
3. (선택) RabbitMQ·ActiveMQ 같은 외부 브로커에 구독과 브로드캐스트를 맡길 수 있습니다.
4. 연결당 `WebSocketHandler` 하나 대신 **destination 별로 `@Controller` 에 나눠 라우팅**합니다.
5. destination과 메시지 타입 기준으로 Spring Security를 걸 수 있습니다.

## 2. Spring 안에서 메시지가 흐르는 길

`@EnableWebSocketMessageBroker` 를 켜면 채널 세 개가 생깁니다([Flow of Messages](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/message-flow.html)).

| 채널 | 방향 | 채팅에서의 의미 |
|---|---|---|
| `clientInboundChannel` | 클라이언트 → 서버 | 사용자가 보낸 메시지, 구독 요청 |
| `brokerChannel` | 서버 코드 → 브로커 | 컨트롤러·서비스가 방에 뿌리는 메시지 |
| `clientOutboundChannel` | 브로커 → 클라이언트 | 구독자에게 실제로 쓰는 메시지 |

라우팅은 **destination 접두사**로 갈립니다. `/app/**` 은 `@MessageMapping` 컨트롤러로 가고, `/topic/**` 과 `/queue/**` 는 브로커로 바로 갑니다. 같은 컨트롤러가 HTTP 요청(`@PostMapping`)을 받아 브로커로 메시지를 보낼 수도 있습니다.

Spring Boot에서는 `spring-boot-starter-websocket` 하나로 시작합니다.

```java
@Configuration
@EnableWebSocketMessageBroker
public class ChatStompConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws-chat")
                .setAllowedOriginPatterns("https://chat.example.com");
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.setApplicationDestinationPrefixes("/app");   // → @MessageMapping
        registry.enableSimpleBroker("/topic", "/queue");      // → 인메모리 브로커
        registry.setUserDestinationPrefix("/user");           // → 사용자별 큐 (기본값)
    }
}
```

## 3. 채팅 구조에 STOMP 개념을 대응시키기

| 채팅 기능 | STOMP / Spring 개념 | destination 예 |
|---|---|---|
| 방에 메시지 보내기 | `SEND` → `@MessageMapping` | `/app/chat.room.{roomId}` |
| 방 메시지 받기 | `SUBSCRIBE` → `/topic` (1:N) | `/topic/chat.room.{roomId}` |
| 귓속말·알림·읽음 표시 | **user destination** | `/user/queue/notifications` |
| 내 요청의 에러만 받기 | `@SendToUser(broadcast = false)` | `/user/queue/errors` |
| 입장·퇴장, 접속 상태 | `SessionConnectedEvent` / `SessionDisconnectEvent` | — |
| 방 단위 권한 | `SUBSCRIBE` 를 가로채는 `ChannelInterceptor` | — |
| 서버 여러 대 | **broker relay** (외부 STOMP 브로커) | — |

### 3-1. 방 메시지 — 저장하고 나서 뿌린다

```java
@Controller
@RequiredArgsConstructor
public class ChatController {

    private final ChatMessageService messages;   // DB 저장
    private final SimpMessagingTemplate broker;

    @MessageMapping("/chat.room.{roomId}")
    public void send(@DestinationVariable long roomId,
                     ChatSendRequest req, Principal principal) {
        ChatMessage saved = messages.save(roomId, principal.getName(), req.text());
        broker.convertAndSend("/topic/chat.room." + roomId, ChatMessageDto.from(saved));
    }
}
```

STOMP 브로커는 **메시지 저장소가 아닙니다.** simple broker는 메모리에 구독만 들고 있습니다. 그래서 연결이 끊긴 사이에 지나간 메시지는 그 클라이언트에게 다시 오지 않습니다. 채팅 기록은 DB에 먼저 저장하고, 재접속한 클라이언트는 **HTTP로 "마지막으로 받은 id 이후"를 조회**해 빈틈을 메우는 구조가 일반적입니다. 이 빈틈 조회가 앞 글의 [No-Offset 페이징](/2026/11/10/querydsl-use-cases-performance/)이 쓰이는 자리입니다.

### 3-2. 사용자에게만 — user destination

클라이언트는 모두 같은 이름 `/user/queue/notifications` 를 구독합니다. Spring의 `UserDestinationMessageHandler` 는 이를 **세션마다 고유한 destination**(예: `/queue/notifications-user123`)으로 바꿔 충돌을 막습니다. 서버 쪽에서는 사용자 이름만 알면 됩니다([User Destinations](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/user-destination.html)).

```java
broker.convertAndSendToUser(targetUsername, "/queue/notifications", notice);
```

한 사용자가 여러 탭으로 접속했다면 기본적으로 **모든 세션**에 갑니다. 보낸 세션에만 응답하려면 `@SendToUser(destinations = "/queue/errors", broadcast = false)` 를 씁니다.

### 3-3. 입장·퇴장과 접속 상태 — 이벤트는 두 번 올 수 있다

Spring은 `SessionConnectEvent`, `SessionConnectedEvent`, `SessionSubscribeEvent`, `SessionUnsubscribeEvent`, `SessionDisconnectEvent` 를 발행합니다([Events](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/application-context-events.html)). 함정은 문서에 그대로 적혀 있습니다. **`SessionDisconnectEvent` 는 한 세션에 두 번 이상 올 수 있으니 처리 로직은 멱등이어야 합니다.** "퇴장 메시지" 를 이벤트마다 그대로 뿌리면 같은 퇴장이 두 번 찍힙니다. 접속자 수를 `-1` 하는 카운터라면 음수가 됩니다.

## 4. 인증과 권한 — 핸드셰이크냐, CONNECT 프레임이냐

**쿠키 세션이면** 이미 끝난 셈입니다. Spring Security 문서에 따르면 WebSocket은 연결을 연 HTTP 요청의 인증 정보를 그대로 씁니다([WebSocket Security](https://docs.spring.io/spring-security/reference/servlet/integrations/websocket.html)).

**토큰(JWT)이면** 핸드셰이크에서 처리하기 어렵습니다. Spring 문서가 짚는 이유는 다음과 같습니다([Token Authentication](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/authentication-token-based.html)).

- RFC 6455는 핸드셰이크 인증 방식을 정하지 않습니다.
- 브라우저 WebSocket API는 **커스텀 헤더를 붙일 수 없습니다.**
- 쿼리 파라미터로 토큰을 넘기면 **URL째로 서버 로그에 남을** 위험이 있습니다.

권장 방식은 **STOMP `CONNECT` 프레임 헤더에 토큰을 싣고, `ChannelInterceptor` 에서 검증해 `accessor.setUser(...)`** 하는 것입니다. 한 번 설정한 사용자는 같은 세션의 이후 메시지에 자동으로 붙습니다.

```java
@Configuration
@Order(Ordered.HIGHEST_PRECEDENCE + 99)   // Spring Security 인터셉터보다 앞에
@RequiredArgsConstructor
public class StompAuthConfig implements WebSocketMessageBrokerConfigurer {

    private final JwtVerifier jwt;
    private final RoomMembership membership;

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(new ChannelInterceptor() {
            @Override
            public Message<?> preSend(Message<?> message, MessageChannel channel) {
                StompHeaderAccessor acc =
                        MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
                if (StompCommand.CONNECT.equals(acc.getCommand())) {
                    acc.setUser(jwt.verify(acc.getFirstNativeHeader("Authorization")));
                }
                if (StompCommand.SUBSCRIBE.equals(acc.getCommand())) {
                    membership.assertCanSubscribe(acc.getUser(), acc.getDestination());
                }
                return message;
            }
        });
    }
}
```

`@Order(Ordered.HIGHEST_PRECEDENCE + 99)` 는 Spring 문서가 직접 권하는 값입니다. 인증 인터셉터가 Spring Security의 메시지 인가보다 **먼저** 돌아야 하기 때문입니다.

**방 단위 권한은 직접 짜야 합니다.** Spring Security의 `@EnableWebSocketSecurity` 는 `simpDestMatchers("/app/**").hasRole("USER")` 처럼 **destination 패턴과 역할**로 인가합니다. 하지만 "이 사용자가 42번 방의 멤버인가"는 DB를 봐야 알 수 있습니다. 이 확인이 빠지면, 로그인한 아무나 `/topic/chat.room.42` 를 구독해서 **남의 방 대화를 엿들을 수 있습니다.** 위 코드의 `SUBSCRIBE` 분기가 그 구멍을 막는 자리입니다.

`@EnableWebSocketSecurity` 는 기본으로 **CONNECT 메시지에 CSRF 토큰을 요구**합니다. 토큰 기반 SPA에서 연결이 이유 없이 거절된다면 먼저 여기를 의심해 보세요.

## 5. 서버가 두 대가 되면 — simple broker의 한계와 broker relay

simple broker는 **인스턴스 메모리 안에** 구독을 들고 있습니다. 서버 A에 붙은 사용자와 서버 B에 붙은 사용자가 같은 방에 있으면, A에서 뿌린 메시지가 B의 사용자에게 가지 않습니다. Spring 문서도 simple broker는 ack·receipt 같은 STOMP 명령 일부를 지원하지 않고 **클러스터링에 적합하지 않다**고 적습니다([External Broker](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/handle-broker-relay.html)).

해법은 **broker relay**입니다. Spring은 구독 관리와 브로드캐스트를 외부 STOMP 브로커에 넘기고, 양방향으로 메시지를 중계만 합니다.

```java
registry.enableStompBrokerRelay("/topic", "/queue")
        .setRelayHost("rabbitmq").setRelayPort(61613)
        .setClientLogin("chat").setClientPasscode("...")
        .setSystemLogin("chat").setSystemPasscode("...");
registry.setApplicationDestinationPrefixes("/app");
registry.setPathMatcher(new AntPathMatcher("."));   // chat.room.42 처럼 점 구분
```

- RabbitMQ는 코어 배포판에 들어 있는 플러그인 `rabbitmq_stomp` 로 STOMP 1.0~1.2를 지원합니다. 기본 포트는 61613입니다([RabbitMQ STOMP Plugin](https://www.rabbitmq.com/docs/stomp)). TCP 연결 관리에는 `reactor-netty` 의존성이 필요합니다.
- destination을 `.` 으로 구분하는 것은 RabbitMQ의 토픽 라우팅 키 관례와 맞추기 위함입니다([Dots as Separators](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/destination-separator.html)).
- 다른 인스턴스에 붙은 사용자에게 보내는 user destination 메시지는 `userDestinationBroadcast` 를 설정해야 다른 서버가 받아서 처리할 기회를 얻습니다.

**relay가 공짜는 아닙니다.** Spring 문서에 따르면 relay는 서버 코드용 "시스템" TCP 연결 하나와 별개로, **WebSocket 클라이언트 하나마다 브로커로 가는 TCP 연결을 따로 엽니다**([Connecting to a Broker](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/handle-broker-relay-configure.html)). 동시 접속 1만 명이면 브로커 쪽 연결도 1만 개입니다. RabbitMQ 4.4부터는 `stomp.max_connections` 로 노드당 STOMP 연결 수를 제한할 수 있습니다. 용량 계획을 세울 때 이 숫자를 같이 봐야 합니다.

**브로커가 재시작되면** relay의 시스템 연결은 5초마다 재연결을 시도합니다. 하지만 **클라이언트 연결은 자동으로 복구되지 않습니다.** 하트비트를 켜 두면 클라이언트는 대개 10초 안에 이상을 알아채지만, 재연결 로직은 클라이언트가 직접 구현해야 합니다([Events](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/application-context-events.html)). 서버 쪽은 `BrokerAvailabilityEvent` 를 받아 브로커가 내려간 동안 전송을 멈추고, `MessageDeliveryException` 에 대비해야 합니다.

## 6. 운영에서 밟는 것들

**순서.** `clientOutboundChannel` 은 스레드 풀 위에서 돕니다. 그래서 **같은 세션에 보낸 메시지가 순서가 뒤바뀌어 도착할 수 있습니다.** 채팅에서 순서가 중요하다면 `registry.setPreservePublishOrder(true)` 를 켭니다(수신 쪽은 `setPreserveReceiveOrder`). 약간의 성능 비용이 있어서 기본값은 꺼져 있습니다([Order of Messages](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/ordered-messages.html)).

**느린 클라이언트.** 한 클라이언트에 동시에 쓸 수 있는 스레드는 하나뿐이고, 나머지 메시지는 버퍼에 쌓입니다. `sendTimeLimit` 와 `sendBufferSizeLimit` 로 "얼마나 기다리고 얼마나 쌓을지"를 정합니다. 문서 예시는 15초와 512KB입니다([Performance](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/configuration-performance.html)).

**스레드 풀.** inbound와 outbound 채널은 기본적으로 **가용 프로세서 수의 두 배** 스레드를 씁니다. 컨트롤러에서 DB 저장처럼 블로킹 작업을 한다면 inbound 풀을 키워야 합니다. 이때 함정이 있습니다. `ThreadPoolExecutor` 의 큐 용량이 기본값 `Integer.MAX_VALUE` 이면, max를 20으로 줘도 **core 크기 이상으로 절대 늘지 않습니다.** 모든 추가 작업이 큐로 가기 때문입니다. Spring 문서가 짚는 흔한 오해입니다.

**메시지 크기.** WebSocket 서버마다 메시지 크기 제한이 있습니다(문서 기준 Tomcat 8K, Jetty 64K). stomp.js 같은 클라이언트는 큰 STOMP 메시지를 16K 단위로 쪼개 보내고, Spring이 다시 조립합니다. 상한은 `setMessageSizeLimit` 로 정합니다. 이미지 같은 큰 첨부는 STOMP로 보내지 말고, HTTP로 업로드한 뒤 URL만 메시지에 담는 편이 낫습니다.

**SockJS.** 사내 프록시처럼 `Upgrade` 헤더를 통과시키지 않거나 유휴 연결을 끊는 환경을 위한 폴백입니다. WebSocket을 먼저 시도하고, 안 되면 HTTP 스트리밍이나 롱 폴링으로 내려갑니다([SockJS Fallback](https://docs.spring.io/spring-framework/reference/web/websocket/fallback.html)). 엔드포인트에 `.withSockJS()` 를 붙이면 됩니다. 다만 SockJS 브라우저 클라이언트는 **HTTP 헤더를 보낼 수 없어서** 4장의 CONNECT 헤더 방식과 짝을 이룹니다. 대상 환경에 그런 프록시가 없다면 굳이 켤 이유가 적습니다.

## 7. 언제 STOMP가 *안* 맞나

- **서버 → 클라이언트 단방향 알림뿐이라면** Server-Sent Events(SSE)로 충분합니다. 일반 HTTP라 인프라 부담이 적습니다.
- **초저지연 게임처럼 메시지 형식을 바이트 단위로 통제해야 한다면** 날것의 WebSocket(`WebSocketHandler`)에 직접 만든 바이너리 프로토콜이 낫습니다. STOMP의 텍스트 헤더는 그만큼 오버헤드입니다.
- **전달 보장(ack, 재전송)이 핵심이라면** simple broker로는 안 됩니다. 외부 브로커의 ack를 쓰거나, 3-1처럼 DB와 "마지막 id 이후" 조회로 보장을 직접 만들어야 합니다.

## 8. 정리 — 채팅 서비스용 체크리스트

1. `/app` → 컨트롤러, `/topic` → 방, `/user/queue` → 개인. 접두사부터 정합니다.
2. 메시지는 **DB 저장 → 브로드캐스트** 순서로 처리하고, 재접속 시 HTTP로 빈틈을 조회합니다.
3. JWT는 **CONNECT 헤더 + `ChannelInterceptor`**, 순서는 `HIGHEST_PRECEDENCE + 99`.
4. **SUBSCRIBE 시 방 멤버십을 검사합니다.** 역할 기반 matcher만으로는 남의 방 구독을 못 막습니다.
5. disconnect 처리는 **멱등**으로.
6. 서버가 2대 이상이면 **broker relay**를 쓰고, 클라이언트 수만큼 브로커 연결이 생긴다는 점을 용량 계획에 넣습니다.
7. 순서가 중요하면 `setPreservePublishOrder(true)`.
8. inbound 스레드 풀을 키울 때는 **큐 용량도 같이** 정합니다.

## 근거의 한계

- 이 글은 **1차 문서(Spring Framework·Spring Security 레퍼런스, STOMP 1.2 명세, RFC 6455, RabbitMQ 문서)를 정리한 개념 글**입니다. 직접 부하 시험을 하지 않았으므로 처리량이나 지연 수치는 일부러 넣지 않았습니다. simple broker와 relay 중 어느 쪽이 몇 명까지 버티는지에 대한 중립 제3자 벤치마크도 찾지 못했습니다.
- 3·4장의 채팅 구조(DB 저장 후 브로드캐스트, SUBSCRIBE 시 멤버십 검사)는 문서가 제시한 기능을 조합한 **글쓴이의 설계 제안**입니다. 문서가 그대로 권하는 패턴은 아닙니다. 코드의 `JwtVerifier`, `RoomMembership`, `ChatMessageService` 는 설명용 가상 컴포넌트입니다.
- Spring 문서의 설정 예시(15초, 512KB 등)는 **예시값**이지 권장값이 아닙니다. 실제 값은 클라이언트 네트워크 상황을 보고 정해야 합니다.
- 버전에 따라 세부 동작이 다를 수 있습니다. 이 글은 2026년 11월 현재 공개된 Spring Framework의 `current` 레퍼런스를 기준으로 합니다.

## References

1. Spring Framework Reference — [WebSockets](https://docs.spring.io/spring-framework/reference/web/websocket.html) / [STOMP Overview](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/overview.html) / [Benefits](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/benefits.html) / [Flow of Messages](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/message-flow.html)
2. Spring Framework Reference — [Simple Broker](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/handle-simple-broker.html) / [External Broker](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/handle-broker-relay.html) / [Connecting to a Broker](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/handle-broker-relay-configure.html) / [Dots as Separators](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/destination-separator.html)
3. Spring Framework Reference — [User Destinations](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/user-destination.html) / [Events](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/application-context-events.html) / [Interception](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/interceptors.html)
4. Spring Framework Reference — [Token Authentication](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/authentication-token-based.html)
5. Spring Framework Reference — [Performance](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/configuration-performance.html) / [Order of Messages](https://docs.spring.io/spring-framework/reference/web/websocket/stomp/ordered-messages.html) / [SockJS Fallback](https://docs.spring.io/spring-framework/reference/web/websocket/fallback.html)
6. Spring Security Reference — [WebSocket Security](https://docs.spring.io/spring-security/reference/servlet/integrations/websocket.html)
7. [STOMP Protocol Specification, Version 1.2](https://stomp.github.io/stomp-specification-1.2.html)
8. I. Fette, A. Melnikov, [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455), IETF, 2011.
9. RabbitMQ Documentation — [STOMP Plugin](https://www.rabbitmq.com/docs/stomp)
