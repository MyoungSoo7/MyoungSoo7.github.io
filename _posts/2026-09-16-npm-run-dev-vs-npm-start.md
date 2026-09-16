---
layout: post
title: "npm run dev 와 npm start 는 뭐가 다른가 — 예약어와 관례의 두 층위"
date: 2026-09-16 20:49:00 +0900
categories: [frontend, tooling]
tags: [npm, Node.js, Next.js, Vite, 빌드, 배포, package.json]
---

`npm run dev` 로 띄우던 앱을 서버에선 `npm start` 로 띄우라고 한다. 같은 앱인데 왜 명령이 둘인가, 아무거나 쓰면 안 되는가 — 답은 한 문장으로 줄일 수 있다. **start 는 npm 의 예약어고, dev 는 팀의 관례일 뿐이다.** 다만 그 관례 위에 프레임워크들이 "개발 모드 vs 프로덕션 모드" 라는 실질적 차이를 얹어 놨기 때문에, 아무거나 쓰면 정말로 안 된다. 층위를 나눠서 보자.

## 1층 — npm 이 아는 것: start 는 예약어, dev 는 그냥 이름

npm 자체의 규칙은 의외로 단순하다.

**`npm start` 는 라이프사이클 명령이다.** `package.json` 의 `scripts.start` 를 실행하며, `test`·`stop`·`restart` 와 함께 `run` 없이 바로 부를 수 있는 소수의 예약 명령에 속한다[^npm-scripts]. 두 가지 특수 동작이 따라온다:

- **기본값이 있다.** `start` 스크립트를 정의하지 않아도 `npm start` 는 실패하지 않고 `node server.js` 를 실행하려 든다[^npm-start]. 루트에 `server.js` 가 없으면 그제서야 에러다 — "스크립트가 없다" 가 아니라 "server.js 를 못 찾는다" 는 엉뚱한 메시지로.
- **훅이 걸린다.** `prestart`/`poststart` 를 정의해 두면 앞뒤로 자동 실행된다[^npm-scripts].

**`npm run dev` 는 임의 스크립트 실행이다.** `npm run` 은 `npm run-script` 의 별칭으로, `scripts` 객체에 적힌 아무 명령이나 이름으로 실행해 주는 범용 러너다[^npm-run]. `dev` 라는 이름에 npm 이 부여한 의미는 **없다.** `npm run banana` 와 지위가 같다. 우리가 `dev` 를 특별하게 느끼는 건 순전히 생태계의 관례 때문이다.

즉 1층에서의 차이는 "예약어 + 기본값 + 훅" vs "그냥 이름" 이 전부다. 진짜 차이는 그 이름 아래에 뭘 적어 두느냐에서 나온다.

## 2층 — 프레임워크가 얹은 것: 개발 서버 vs 프로덕션 서빙

메이저 프레임워크들은 이 두 이름에 일관된 관례를 실어 놨다.

**Next.js 가 가장 전형적이다.** 생성되는 `scripts` 는 `dev: next dev` / `build: next build` / `start: next start` 다. 공식 CLI 문서 기준 `next dev` 는 **개발 모드** — HMR(핫 리로드)·상세 에러 리포팅이 켜진 개발 서버를 띄우고, `next start` 는 **프로덕션 모드** — `next build` 로 컴파일된 결과물을 서빙한다[^next-cli]. 빌드 없이 `next start` 를 치면 빌드부터 하라고 거절당한다. 같은 코드라도 두 모드는 컴파일 최적화·캐싱 동작이 다르다.

**Vite 는 이름으로 오해를 차단한 쪽이다.** `vite`(dev 서버)·`vite build`·그리고 start 대신 **`vite preview`** 를 둔다. preview 는 빌드 산출물을 로컬에서 확인하는 용도이고, 공식 문서가 명시적으로 경고한다 — *"Do not use this as a production server as it's not designed for it"*[^vite-cli]. Vite 세계에서 프로덕션 서빙은 빌드된 정적 파일을 nginx 같은 별도 서버에 올리는 일이지, npm 스크립트의 일이 아니라는 설계다.

**Express 는 반대편 극단이다.** 클라이언트 빌드라는 개념이 없으니 generator 가 만들어 주는 스크립트는 `start` 하나뿐이다[^express-gen]. dev 용 자동 재시작(nodemon 류)을 원하면 그때 `dev` 스크립트를 손으로 추가하는 게 관례다.

정리하면 관례의 실체는 이렇다: **`dev` = 소스를 직접 물고 도는 개발 서버 (빠른 피드백이 목적, 서빙 성능은 목적 아님)** / **`start` = 빌드 산출물을 서빙하는 프로덕션 실행 (빌드가 선행 조건)**.

## 사고가 나는 네 지점

1. **운영 서버에서 `npm run dev`.** 가장 흔하고 가장 나쁘다. dev 서버는 파일 감시·변환을 상시 수행하며 프로덕션 최적화(압축·캐싱)가 꺼져 있고, 애초에 다중 사용자 서빙용으로 설계되지 않았다 — Vite 는 preview 조차 프로덕션 서버로 쓰지 말라고 못 박는다[^vite-cli]. Dockerfile·systemd 유닛의 실행 명령은 `build` 후 `start` 가 기본이다.
2. **`start` 없이 `npm start`.** 위에서 본 대로 `node server.js` 폴백이 발동해, 스크립트 누락이 "server.js 없음" 이라는 오해하기 좋은 에러로 둔갑한다[^npm-start].
3. **인자 전달.** `npm start 3000` 처럼 붙인 인자는 스크립트에 안 간다 — `npm start -- --port 3000` 처럼 `--` 뒤에 붙여야 스크립트로 전달된다[^npm-run].
4. **`dev` 가 늘 dev 인 건 아니다.** 관례일 뿐이라 리포마다 `serve`·`watch`·`start:dev`(NestJS 계열) 등으로 흩어져 있다. 남의 리포에선 이름을 믿지 말고 `package.json` 의 `scripts` 를 열어 실제 명령을 읽는 게 정답이다.

## 정리

| | `npm run dev` | `npm start` |
| --- | --- | --- |
| npm 에서의 지위 | 임의 스크립트 (`run-script`) | 예약 라이프사이클 명령 |
| 스크립트 없을 때 | 에러 | `node server.js` 폴백 |
| pre/post 훅 | `predev`/`postdev` 가능 | `prestart`/`poststart` |
| 관례상 역할 | 개발 서버 (HMR, 소스 직결) | 프로덕션 빌드 서빙 |
| 선행 조건 | 없음 | 대개 `npm run build` |
| 쓰는 곳 | 로컬 개발 | 배포 환경 (Docker/CI) |

한 줄 요약 — **npm 은 start 만 알고 dev 는 모른다. 하지만 프레임워크 관례가 dev=개발 서버, start=프로덕션 서빙으로 굳혀 놨으니, 로컬에선 dev 를, 배포 명령엔 build + start 를, 남의 리포에선 이름 대신 scripts 본문을 믿어라.**

---

## 근거의 한계

- 프레임워크 관례는 Next.js·Vite·Express 세 곳의 공식 문서로만 실측했다. 다른 프레임워크(SvelteKit, Nuxt 등)도 대체로 같은 관례를 따르지만 이 글에서 검증하지는 않았다.
- "dev 서버가 프로덕션 대비 얼마나 느린가" 류의 정량 비교는 중립 출처를 확인하지 못해 싣지 않았다 — 이 글의 근거는 성능 수치가 아니라 각 도구의 공식 설계 서술이다.

## References

[^npm-start]: npm 공식 문서 — [npm-start](https://docs.npmjs.com/cli/v11/commands/npm-start) (`start` 미정의 시 `node server.js` 실행)
[^npm-run]: npm 공식 문서 — [npm-run](https://docs.npmjs.com/cli/v11/commands/npm-run) (`run-script` 별칭, 임의 명령 실행, `--` 인자 전달)
[^npm-scripts]: npm 공식 문서 — [scripts](https://docs.npmjs.com/cli/v11/using-npm/scripts) (라이프사이클 스크립트, `prestart`/`poststart`)
[^next-cli]: Next.js 공식 문서 — [next CLI](https://nextjs.org/docs/app/api-reference/cli/next) (`next dev` 개발 모드 / `next start` 프로덕션 모드, 빌드 선행)
[^vite-cli]: Vite 공식 문서 — [Command Line Interface](https://vite.dev/guide/cli) (`vite preview` — "Do not use this as a production server as it's not designed for it")
[^express-gen]: Express 공식 문서 — [Express application generator](https://expressjs.com/en/starter/generator.html) (`npm start` 로 실행하는 기본 구조)
