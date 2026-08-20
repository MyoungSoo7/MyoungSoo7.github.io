---
layout: post
title: "println 으로 HTML 을 찍던 시절과 가상 DOM — JSP 와 React 는 각각 무엇을 지웠나"
date: 2026-08-20 21:44:15 +0900
categories: [engineering, frontend]
tags: [jsp, react, servlet, cgi, ajax, jquery, virtual-dom, declarative, history]
---

JSP 와 React 를 "낡은 것과 새것"으로 놓으면 아무것도 안 보입니다. 둘은 **서로 다른 시대의 서로 다른 통증**에 대한 답이고, 공교롭게도 같은 방식으로 답했습니다 — **사람이 쓰던 절차를 지우고, 결과만 쓰게 했다.**

이 글은 두 번의 전환을 순서대로 봅니다. 서블릿에서 JSP 로 갈 때 무엇이 지워졌는지, 그리고 jQuery 시대에서 React 로 갈 때 무엇이 지워졌는지. 전/후 비교는 6절에 한 표로 모았습니다.

---

## 1. JSP 이전 — HTML 을 자바 코드로 '출력'하던 시대

### 1-1. CGI — 요청 하나에 프로세스 하나

웹에서 동적 페이지를 만드는 최초의 표준적 방법은 CGI 였습니다. NCSA 가 **1993년** 명세를 썼고, 정식 표준화는 한참 뒤인 **2004년 10월 RFC 3875** 로 이뤄집니다.[^cgi]

CGI 의 문제는 성능이었고, 원인은 구조에 있었습니다.

> For each incoming HTTP request, a Web server creates a new CGI process for handling it and destroys the CGI process after the HTTP request has been handled. Creating and destroying a process can consume more CPU time and memory resources than the actual work of generating the output of the process.[^cgi]

**요청을 처리하는 일보다 프로세스를 만들고 없애는 일이 더 비쌌습니다.** 트래픽이 늘면 이 비용이 그대로 곱해집니다.

### 1-2. 서블릿 — 프로세스를 스레드로 바꿨다

자바 진영의 답이 서블릿이었습니다. 위키백과는 이 전환을 한 문장으로 정리합니다.

> replaces the overhead of creating and destroying processes with the much lower overhead of creating and destroying threads.[^cgi]

**프로세스 생성 비용을 스레드 생성 비용으로 바꿨습니다.** 이건 진짜 해결이었고, 지금까지 유효합니다.

그런데 서블릿은 성능만 고쳤을 뿐 **화면을 만드는 방식은 안 고쳤습니다.** 서블릿에서 HTML 을 만들려면 이렇게 씁니다.

```java
out.println("<html>");
out.println("<body>");
out.println("<h1>" + user.getName() + " 님 환영합니다</h1>");
out.println("<table>");
for (Order o : orders) {
    out.println("<tr><td>" + o.getId() + "</td><td>" + o.getAmount() + "</td></tr>");
}
out.println("</table>");
out.println("</body></html>");
```

### 1-3. 공통의 통증

이 코드가 만드는 통증은 성능이 아니라 **사람 쪽**에 있습니다.

| 통증 | 실제로 무엇이었나 |
| --- | --- |
| **디자이너가 못 건드림** | 화면 문구 하나 고치려면 자바 파일을 열고, 컴파일하고, 재배포해야 함 |
| **HTML 이 문자열** | 태그 오타를 컴파일러가 못 잡음. 따옴표 이스케이프 지옥 |
| **구조가 안 보임** | `println` 사이에 흩어진 태그로는 문서 구조를 눈으로 못 읽음 |
| **역할 분리 불가** | 화면 담당과 로직 담당이 같은 파일을 동시에 고침 |

## 2. JSP (1999) — 안팎을 뒤집었다

**1999년 Sun Microsystems** 가 JSP 를 내놓습니다.[^jsp] 한 일은 단순합니다 — **뒤집었습니다.**

- 이전: **자바 코드 안에 HTML 문자열**이 들어감
- 이후: **HTML 문서 안에 자바 코드 조각**이 들어감

```jsp
<html>
<body>
  <h1>${user.name} 님 환영합니다</h1>
  <table>
    <c:forEach var="o" items="${orders}">
      <tr><td>${o.id}</td><td>${o.amount}</td></tr>
    </c:forEach>
  </table>
</body>
</html>
```

같은 화면인데 이제 **HTML 로 보입니다.** 디자이너가 열 수 있고, 에디터가 태그를 검사하고, 구조가 눈에 들어옵니다.

여기서 중요한 사실 하나. **JSP 는 서블릿을 대체하지 않았습니다.**

> JSPs are translated into servlets at runtime ... A JavaServer Pages compiler is a program that parses JSPs and transforms them into executable Java Servlets.[^jsp]

JSP 는 서블릿의 **고수준 추상**이고, 실행 시점에 서블릿으로 번역됩니다. 즉 1-2 절의 그 `println` 코드는 사라진 게 아니라 **기계가 대신 쓰게 된 것**입니다. 지워진 건 기술이 아니라 **사람의 작업**입니다.

## 3. JSP 가 남긴 것 — 스크립틀릿, 그리고 되돌아온 뒤집기

JSP 는 새 통증도 만들었습니다. **스크립틀릿**입니다.

> a fragment of Java code that runs when the user requests the page[^jsp]

`<% ... %>` 안에는 자바를 뭐든 쓸 수 있었습니다. DB 접속도, 트랜잭션도, 비즈니스 로직도. 그래서 현장의 JSP 는 금세 **HTML 과 자바가 다시 뒤엉킨 파일**이 됐습니다. 1-3 절에서 지웠던 통증이 방향만 바꿔 돌아온 겁니다.

해법은 두 갈래로 왔습니다.

1. **JSTL 과 EL** — 반복문·조건문 같은 흔한 작업을 태그로 대체하고, 값 참조를 `${...}` 로 통일했습니다. EL 은 JSP 2.0 에 도입돼 2.1 에서 Unified EL 로 통합됩니다.[^jsp] 스크립틀릿을 **문법적으로 안 써도 되게** 만든 조치입니다.
2. **Model 2 (MVC)** — JSP 에서 로직을 걷어내 서블릿/컨트롤러로 옮기고, JSP 는 **출력만** 하게 역할을 좁혔습니다.

정리하면 JSP 의 최종 형태는 "만능 페이지"가 아니라 **책임이 좁혀진 템플릿**입니다. 참고로 이 기술은 현재 Eclipse Foundation 의 Jakarta EE 아래에서 **Jakarta Server Pages** 라는 이름으로 이어지고 있습니다.[^jsp]

## 4. React 이전 — 서버 렌더링이 만든 새 통증

JSP 가 자리를 잡은 뒤에도 웹에는 큰 제약이 하나 남아 있었습니다.

> Each user action required a complete new page to be loaded from the server.[^ajax]

**클릭 한 번에 화면 전체가 다시 그려졌습니다.** 목록에서 체크박스 하나를 켜도 페이지가 깜빡이고, 스크롤 위치가 날아갔습니다.

이 제약을 푼 게 XMLHttpRequest 입니다. Microsoft 의 Outlook Web Access 팀이 1998년에 만들었고, **1999년 3월 Internet Explorer 5.0** 과 함께 MSXML 라이브러리 2판에 실려 나왔습니다.[^ajax] 그리고 **2005년 2월 18일**, Jesse James Garrett 이 「Ajax: A New Approach to Web Applications」에서 이 방식에 이름을 붙입니다.[^ajax]

Ajax 는 진짜 해결이었지만, **상태를 두 군데로 쪼갰습니다.**

서버는 여전히 데이터의 정본을 갖고 있는데, 화면의 현재 모습은 이제 브라우저 안에서 계속 바뀝니다. 그래서 개발자는 jQuery 같은 도구로 **DOM 을 손으로 고치는 절차**를 직접 써야 했습니다.

```javascript
// 주문이 하나 추가됐을 때, 개발자가 직접 써야 하는 "절차"
$('#order-table').append('<tr>...</tr>');
$('#order-count').text(count + 1);
$('#empty-message').hide();
if (count + 1 > 10) { $('#pagination').show(); }
```

여기서 진짜 문제는 코드 길이가 아닙니다. **화면의 최종 모습이 코드 어디에도 안 적혀 있다는 것**입니다. 적혀 있는 건 "이럴 땐 이걸 바꿔라"는 변경 절차의 목록뿐이고, 실제 화면은 그 절차들이 **순서대로 다 성공했을 때만** 맞습니다. 하나를 빠뜨리면 데이터와 화면이 어긋나고, 그 버그는 재현이 어렵습니다.

## 5. React (2013) — 절차 대신 결과를 쓰게 했다

React 는 Facebook 의 **Jordan Walke** 가 만들었습니다. **2011년 뉴스피드**에 처음 투입됐고, **2012년 인스타그램**으로 확대된 뒤, **2013년 5월 JSConf US** 에서 오픈소스로 공개됩니다.[^react]

React 가 바꾼 것은 한 문장입니다.

> Developers design views for each state of an application, and React updates and renders components when data changes.[^react]

**상태마다 화면이 어때야 하는지를 쓰고, 바꾸는 일은 React 가 합니다.** 4절의 그 jQuery 코드가 통째로 사라지고, 대신 이걸 씁니다.

```jsx
function OrderTable({ orders }) {
  if (orders.length === 0) return <EmptyMessage />;
  return (
    <>
      <table>{orders.map(o => <Row key={o.id} order={o} />)}</table>
      <span>{orders.length}건</span>
      {orders.length > 10 && <Pagination />}
    </>
  );
}
```

"주문이 추가되면 무엇을 하라"가 없습니다. **"주문이 이럴 때 화면은 이렇다"** 만 있습니다.

이게 성능상 가능한 이유가 **가상 DOM** 입니다. 위키백과의 설명은 이렇습니다 — 가상 DOM 은 "an in-memory data-structure, similar to the browser DOM" 이고, 컴포넌트가 렌더링되면 그 결과를 이전 가상 DOM 과 비교해 **브라우저의 실제 DOM 을 효율적으로 갱신**합니다.[^react]

즉 **"전부 다시 그린다"고 쓰되, 실제로는 달라진 부분만 고칩니다.** 3절에서 JSP 가 그랬듯이, 여기서도 사라진 건 기술이 아니라 **사람이 쓰던 절차**입니다. 이제 그 diff 를 기계가 계산합니다.

이후 React 는 **2019년 2월 16일 16.8 버전에서 Hooks** 를 도입하며 상태 로직 자체도 컴포넌트 밖으로 꺼내 재사용할 수 있게 만듭니다.[^react]

## 6. 두 번의 전환을 나란히 놓기

| 축 | 서블릿 시대 (JSP 이전) | JSP 이후 | jQuery 시대 (React 이전) | React 이후 |
| --- | --- | --- | --- | --- |
| **화면을 어디에 쓰나** | 자바 코드 안 문자열 | HTML 템플릿 파일 | HTML + 흩어진 조작 코드 | 컴포넌트 함수 |
| **무엇을 쓰나** | 출력 절차 (`println`) | 문서 구조 | 변경 절차 (`append`/`hide`) | 상태별 결과 |
| **diff 를 누가 계산하나** | — (전체 출력) | — (전체 출력) | **사람** | **가상 DOM** |
| **디자이너 접근** | 불가 | 가능 | 부분적 | 컴포넌트 단위 |
| **틀렸을 때 증상** | 컴파일 에러 / 태그 깨짐 | 태그 깨짐 | **데이터와 화면 불일치** | 렌더 결과가 틀림 (추적 쉬움) |
| **갱신 단위** | 페이지 전체 | 페이지 전체 | DOM 노드 하나하나 | 컴포넌트 |
| **남긴 새 통증** | — | 스크립틀릿 지옥 | 상태 이중화 | 번들 크기·하이드레이션 |

두 전환은 서로 30년 가까이 떨어져 있고 기술 스택도 완전히 다른데, **같은 모양**입니다.

> 사람이 쓰던 **절차**를 지우고, **결과**를 선언하게 한다. 그 사이의 차이를 메우는 일은 기계가 반복한다.

이 구조는 웹만의 것이 아닙니다. 오늘 쓴 [쿠버네티스 글](/2026/08/20/what-problem-did-kubernetes-come-to-solve/)에서도 정확히 같은 전환이 나옵니다 — 명령형에서 선언형으로, 그리고 그 차이를 메우는 제어 루프. 인프라와 UI 가 각자 도달한 답이 같습니다.

## 7. 그럼 React 는 완전한 해결인가

아닙니다. 그리고 이 대목이 재미있습니다.

React 가 화면을 브라우저로 가져오자 **서버 렌더링이 주던 것들**이 사라졌습니다. 첫 화면이 늦게 뜨고(빈 HTML 을 받은 뒤 JS 를 내려받아 실행해야 하므로), 검색 엔진과 링크 미리보기가 내용을 못 읽고, 번들이 커집니다.

그래서 업계는 서버 렌더링으로 **되돌아갑니다.** SSR, 그리고 서버에서 만든 HTML 에 이벤트를 다시 붙이는 하이드레이션, 나아가 React Server Components 까지 — 방향만 보면 **1절의 서버 렌더링으로 회귀**입니다.

다만 같은 자리로 돌아온 건 아닙니다.

| | JSP 의 서버 렌더링 | 오늘의 서버 렌더링 |
| --- | --- | --- |
| 작성 단위 | 페이지 | 컴포넌트 |
| 상호작용 | 매번 서버 왕복 | 클라이언트에서 처리 |
| 서버/클라이언트 경계 | 고정 (전부 서버) | **개발자가 컴포넌트마다 고름** |

**경계가 고정에서 선택으로 바뀐 것** — 이게 30년간 실제로 늘어난 자유이고, 동시에 오늘 프론트엔드가 어려운 이유이기도 합니다. 고를 게 없으면 틀릴 일도 없으니까요.

## 8. 정리

- **CGI** 는 요청마다 프로세스를 띄웠고, **서블릿**이 그걸 스레드로 바꿔 성능을 고쳤습니다. 하지만 HTML 은 여전히 `println` 이었습니다.
- **JSP(1999)** 는 안팎을 뒤집어 **HTML 안에 코드**를 넣었습니다. 실행 시점에 서블릿으로 번역되므로, 지워진 건 기술이 아니라 사람의 작업입니다.
- JSP 는 **스크립틀릿**이라는 새 통증을 만들었고, **JSTL/EL 과 Model 2** 로 역할을 다시 좁혀 수습했습니다.
- **Ajax(2005 명명)** 는 전체 새로고침을 지웠지만 **상태를 서버와 브라우저로 쪼갰고**, 그 사이를 사람이 DOM 조작 절차로 메워야 했습니다.
- **React(2013 공개)** 는 그 절차를 지웠습니다. 상태별 결과만 쓰고, diff 는 **가상 DOM** 이 계산합니다.
- 두 전환의 공통 문법은 하나입니다 — **절차를 지우고 결과를 선언하게 한다.**
- 그리고 React 이후 업계는 서버 렌더링으로 되돌아갔습니다. 다만 **경계가 고정이 아니라 선택**이라는 점이 다릅니다.

기술 선택을 할 때 "JSP 는 낡았고 React 는 최신"이라는 축은 별로 쓸모가 없습니다. 더 나은 질문은 이쪽입니다 — **우리 화면에서 사람이 아직도 절차를 손으로 쓰고 있는 곳이 어디인가.** 거기가 다음에 지워질 자리입니다.

---

[^cgi]: Wikipedia, "Common Gateway Interface" — <https://en.wikipedia.org/wiki/Common_Gateway_Interface>
[^jsp]: Wikipedia, "Jakarta Server Pages" — <https://en.wikipedia.org/wiki/Jakarta_Server_Pages>
[^ajax]: Wikipedia, "Ajax (programming)" — <https://en.wikipedia.org/wiki/Ajax_(programming)>
[^react]: Wikipedia, "React (software)" — <https://en.wikipedia.org/wiki/React_(software)>
