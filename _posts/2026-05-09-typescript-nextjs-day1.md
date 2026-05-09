---
layout: post
title: "TypeScript + Next.js 15 풀스택 1일차 — App Router 첫 페이지"
date: 2026-05-09 15:30:00 +0900
categories: [frontend, nextjs]
tags: [typescript, nextjs, react, app-router, server-components]
---

> 이 시리즈는 르무엘이 jen.lemuel.co.kr (커머스) + academy.lemuel.co.kr (영상 강의) 를 만들면서 정리한 7일 노트입니다.

오늘은 셋업 + App Router 첫 페이지 + Server Component 와 Client Component 차이까지.

> 이 글에서 다루는 것
> - 왜 Next.js 15 + React 19
> - 5분 부트스트랩
> - App Router 디렉토리 구조
> - Server Component 가 default 인 의미
> - "use client" 를 언제 써야 하나

---

## 1. 왜 Next.js 15

| 기능 | Next.js 15 + React 19 |
|---|---|
| 라우팅 | App Router (file-based) |
| 데이터 fetching | Server Component 직접 fetch |
| SEO | 자동 SSR / SSG / ISR 선택 |
| 이미지 최적화 | `<Image>` 자동 webp/avif |
| 폼 처리 | Server Action — 백엔드 없이 form |
| 캐싱 | 자동 + per-fetch 제어 |
| 빌드 | Turbopack (Webpack 보다 ~10배) |

장점은 **풀스택을 한 프레임워크로** — API Route + DB 호출 + UI 까지.

---

## 2. 5분 부트스트랩

```bash
npx create-next-app@latest lemuel-frontend
# ✔ Would you like to use TypeScript? Yes
# ✔ Would you like to use ESLint? Yes
# ✔ Would you like to use Tailwind CSS? Yes
# ✔ Would you like your code inside a `src/` directory? Yes
# ✔ Would you like to use App Router? Yes
# ✔ Would you like to use Turbopack for `next dev`? Yes
# ✔ Would you like to customize the import alias? No

cd lemuel-frontend
npm run dev
# http://localhost:3000
```

---

## 3. App Router 디렉토리

```
src/app/
├── layout.tsx           ← 모든 페이지의 공통 wrapper (HTML <html>)
├── page.tsx             ← / (홈)
├── about/
│   └── page.tsx         ← /about
├── courses/
│   ├── page.tsx         ← /courses
│   └── [id]/
│       └── page.tsx     ← /courses/123
├── api/
│   └── healthz/
│       └── route.ts     ← API Route (GET /api/healthz)
└── globals.css
```

핵심 규칙:

- `page.tsx` 가 있으면 그 폴더가 라우트
- `[id]` 같은 대괄호는 동적 파라미터
- `route.ts` 는 API endpoint
- `layout.tsx` 는 자식 페이지 감싸는 컴포넌트

---

## 4. Server Component 가 default

Next.js 15 의 모든 컴포넌트는 **기본적으로 Server Component** 입니다. 즉:

- 서버에서만 렌더 → HTML 만 클라이언트로 전송
- DB / 비밀 키 / Node API 직접 접근 가능
- React state / `useEffect` / 브라우저 API 사용 X

```tsx
// src/app/courses/page.tsx (Server Component)
import { db } from "@/lib/db";

export default async function CoursesPage() {
  const courses = await db.course.findMany();  // ← DB 직접 호출
  return (
    <main className="p-8">
      <h1 className="text-2xl font-bold">강의 목록</h1>
      <ul>
        {courses.map((c) => <li key={c.id}>{c.title}</li>)}
      </ul>
    </main>
  );
}
```

이게 가능한 이유: 이 컴포넌트는 **브라우저로 안 갑니다.** HTML 만 갑니다. DB 비밀번호 노출 없음.

---

## 5. "use client" — 언제 쓰나

브라우저 인터랙션이 필요할 때.

```tsx
// src/components/SearchBox.tsx
"use client";  // ← 첫 줄

import { useState } from "react";

export function SearchBox() {
  const [q, setQ] = useState("");
  return (
    <input
      value={q}
      onChange={(e) => setQ(e.target.value)}
      placeholder="검색"
    />
  );
}
```

Server Component 안에 Client Component 를 자식으로 넣을 수 있습니다 (반대는 X — Server 가 Client 안에 못 들어감).

```tsx
// page.tsx (Server)
import { SearchBox } from "@/components/SearchBox";   // Client OK

export default async function Page() {
  const data = await fetchOnServer();
  return (
    <div>
      <h1>{data.title}</h1>
      <SearchBox />   {/* ← 인터랙티브 부분만 Client */}
    </div>
  );
}
```

### 황금률

> "기본은 Server. `useState`, `useEffect`, `onClick` 이 필요할 때만 Client."

---

## 6. 첫 API Route

```typescript
// src/app/api/healthz/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    ok: true,
    time: new Date().toISOString(),
  });
}
```

```bash
curl http://localhost:3000/api/healthz
# {"ok":true,"time":"2026-05-09T..."}
```

---

## 7. 함정 모음

1. **Server → Client props** — Server 에서 Client 로 함수/Date 객체 직접 전달 X (직렬화 안 됨)
2. **`use client` 가 page 자체** — page 가 Client 면 metadata / generateMetadata 못 씀 → 보통 page 는 Server, 인터랙티브 부분만 Client 컴포넌트로
3. **fetch 캐시 default** — `fetch()` 가 자동으로 캐시. 동적 데이터는 `{ cache: "no-store" }` 또는 `next: { revalidate: 60 }`
4. **환경변수** — 클라이언트로 보내려면 `NEXT_PUBLIC_` 접두사. 그 외는 서버만 보임
5. **`<Image>` width/height 필수** — CLS 방지

---

## 다음 학습 (7일 코스)

| Day | 주제 |
|---|---|
| 1 | App Router + Server/Client Component (오늘) |
| 2 | 데이터 fetching + 캐싱 + revalidate |
| 3 | Server Action + Form 처리 |
| 4 | 인증 (NextAuth.js v5 또는 Clerk) |
| 5 | Tailwind + shadcn/ui 디자인 시스템 |
| 6 | API 통합 (axios / SWR / Tanstack Query) |
| 7 | 배포 (Vercel / 자체 호스팅 + Docker) |

---

> 코드 표본: jen.lemuel.co.kr 의 백오피스 / academy.lemuel.co.kr 의 learner / studio / admin.
