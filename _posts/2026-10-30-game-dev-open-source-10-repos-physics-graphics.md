---
layout: post
title: "게임 그래픽·물리 오픈소스 10선, README 로 다시 읽기 — Jolt 부터 FastNoise2 까지"
date: 2026-10-30 12:41:50 +0900
categories: [gamedev, opensource]
tags: [jolt-physics, godot, terrain3d, material-maker, effekseer, godot-voxel, recast-navigation, ozz-animation, the-forge, meshoptimizer, fastnoise2]
---

텔레그램 채널 [AI Innovation Studio](https://t.me/aiinnovationstudio) 에 「AI 에이전트로 상용 게임 수준의 그래픽과 물리 효과 구현하기: 유용한 오픈소스 저장소 10선」이라는 목록이 올라왔다. 이 글은 그 목록에 나온 저장소 10개를 **각 저장소의 README 와 GitHub API 응답만 근거로** 다시 정리한 것이다.

기준과 범위는 이렇다.

- 별 수·라이선스·최근 push·최신 릴리스는 2026-10-30 12:40 KST 에 GitHub REST API(`/repos/{owner}/{repo}`, `/releases/latest`)로 직접 조회했다. 별 수는 계속 변하므로 이 시각의 스냅샷이다.
- "어느 게임에 쓰였다", "어느 엔진에 들어갔다"는 내용은 **저장소가 README 에서 스스로 밝힌 주장**이다. 이 글에서 따로 검증하지 않았다.
- 원 게시물의 제목에 있는 "AI 에이전트로 상용 게임 수준"이라는 표현을 뒷받침하는 중립적인 비교·벤치마크는 찾지 못했다. 그래서 이 글은 그 주장을 평가하지 않는다. 대신 각 라이브러리가 **무슨 문제를 푸는지**, 그리고 **어떤 단서가 붙어 있는지**를 적었다.

## 한눈에

| # | 저장소 | 역할 | 언어 | 라이선스 | ★ (10/30) | 최신 릴리스 |
|---|---|---|---|---|---|---|
| 1 | [jrouwe/JoltPhysics](https://github.com/jrouwe/JoltPhysics) | 강체 물리·충돌 | C++ | MIT | 11,917 | v5.6.0 (2026-07-11) |
| 2 | [TokisanGames/Terrain3D](https://github.com/TokisanGames/Terrain3D) | Godot 지형 | C++ | MIT | 4,531 | v1.0.2-stable (2026-05-19) |
| 3 | [RodZill4/material-maker](https://github.com/RodZill4/material-maker) | 절차적 텍스처 | GDScript | MIT | 6,115 | 1.8 (2026-10-25) |
| 4 | [effekseer/Effekseer](https://github.com/effekseer/Effekseer) | 파티클 이펙트 | C | MIT | 1,899 | 1807 (2026-08-07) |
| 5 | [Zylann/godot_voxel](https://github.com/Zylann/godot_voxel) | Godot 복셀 지형 | C++ | MIT | 4,024 | v1.7 (2026-08-20) |
| 6 | [recastnavigation/recastnavigation](https://github.com/recastnavigation/recastnavigation) | 내비메시·길찾기 | C++ | Zlib | 8,053 | v1.6.0 (2023-05-21) |
| 7 | [guillaumeblanc/ozz-animation](https://github.com/guillaumeblanc/ozz-animation) | 스켈레탈 애니메이션 | C++ | MIT (README 기준) | 3,038 | 0.17.0 (2026-08-01) |
| 8 | [ConfettiFX/The-Forge](https://github.com/ConfettiFX/The-Forge) | 크로스플랫폼 렌더링 프레임워크 | C++ | Apache-2.0 (+콘솔 상용) | 5,745 | v1.63 (2025-03-21) |
| 9 | [zeux/meshoptimizer](https://github.com/zeux/meshoptimizer) | 메시 최적화·압축 | C++ | MIT | 8,701 | v1.3 (2026-09-25) |
| 10 | [Auburn/FastNoise2](https://github.com/Auburn/FastNoise2) | SIMD 노이즈 생성 | C++ | MIT | 1,506 | v1.1.1 (2026-02-24) |

10개 중 3개(Terrain3D·Material Maker·godot_voxel)는 Godot 생태계에 묶여 있다. 나머지 7개는 엔진에 매이지 않는 라이브러리다. 이 차이가 실제로 고를 때 가장 먼저 걸리는 기준이다.

## 1. 물리 — Jolt Physics

README 의 첫 문장은 "멀티코어 친화적인 강체 물리·충돌 감지 라이브러리"이다. 게임과 VR 용도라고 밝히고, Horizon Forbidden West 와 Death Stranding 2 에 쓰였다고 적는다 ([README](https://github.com/jrouwe/JoltPhysics#readme)).

README 의 "Design considerations" 를 보면 왜 굳이 새 물리 엔진을 만들었는지가 나온다. 게임은 물리만 돌리는 게 아니라는 것이다.

- **시뮬레이션 밖에서의 동시 접근을 우선한다.** 백그라운드 스레드에서 바디 묶음을 만들어 놓았다가, 시뮬레이션을 잠그지 않고 한 번에 넣는다. 충돌 쿼리는 바디 추가·삭제나 시뮬레이션 스텝과 병렬로 돌릴 수 있다.
- **바디가 저절로 깨어나지 않는다.** 바디를 만들어도 자동으로 깨우지 않고, 바디를 지워도 이웃 바디를 깨우지 않는다. 콘텐츠를 스트리밍할 때 생기는 성능 문제를 막기 위한 선택이다.
- **결정론적이다.** 입력만 복제하면 원격 클라이언트에서 같은 시뮬레이션을 재현할 수 있다. 다만 README 는 [Deterministic Simulation](https://jrouwe.github.io/JoltPhysics/#deterministic-simulation) 절에 그 한계를 따로 적어 두었다.

기능 목록에는 다음이 들어 있다.

- 연속 충돌 감지를 쓰는 11가지 형상: 구·박스·캡슐·볼록 껍질·메시·높이맵 지형 등
- 힌지·슬라이더·6DOF·스윙-트위스트 같은 구속 조건
- 캐릭터(강체형·가상형)
- 바퀴형·궤도형 차량
- 소프트 바디(천·말랑한 공)

엔진 통합 목록에는 Godot, Source Engine(커뮤니티 VPhysics-Jolt), Unreal 플러그인 두 개가 있다. 바인딩은 JavaScript(WASM)·Rust·Python·Zig 등으로 나와 있다.

## 2. 지형 — Terrain3D (Godot)

Godot 용 고성능 편집형 지형 시스템이다. C++ GDExtension 으로 만들어서 **공식 Godot 빌드에서 그대로** 돌아가고, GDScript·C# 에서 접근할 수 있다 ([README](https://github.com/TokisanGames/Terrain3D#readme)).

README 에 적힌 범위는 이렇다.

- 지형 크기는 64×64m 부터 65.5×65.5km(4,295km²)까지이고, 영역이 이어져 있지 않아도 된다.
- 텍스처는 최대 32장, LOD 는 최대 10단계까지 쓸 수 있다.
- 풀·바위 같은 폴리지 인스턴싱도 10단계 LOD 와 그림자 임포스터를 지원한다.
- 조각(sculpting), 구멍 뚫기, 텍스처 페인팅, 반복 무늬 깨기(detiling), 색·젖음 표현을 지원한다.
- HTerrain·Gaea·World Creator·World Machine·Unity·Unreal 의 높이맵을 가져올 수 있다.

## 3. 텍스처 — Material Maker

Godot 엔진 위에서 만든 **절차적 텍스처 저작 도구**다. 노드를 이어 붙여 머티리얼을 만들고, 3D 모델에 직접 칠할 수도 있다. UI 는 Godot 의 GraphEdit 노드를 쓴다 ([README](https://github.com/RodZill4/material-maker#readme)). 언어가 GDScript 로 표시되는 것도 이 때문이다.

목록의 다른 항목은 대부분 게임에 넣는 **런타임 라이브러리**다. Material Maker 는 다르다. 결과물(텍스처)을 뽑아내는 **독립 실행형 앱**이다. 배포는 itch.io·Steam·Scoop·Chocolatey·Homebrew 로 한다. 10/25 에 1.8 이 나왔다.

## 4. 이펙트 — Effekseer

파티클 이펙트를 **편집하는 툴**과, 그 이펙트를 앱 안에서 **재생하는 런타임·플러그인**으로 이뤄져 있다. README 는 프로그래머가 아니라 디자이너가 이펙트를 만들게 하는 것이 목표라고 밝힌다 ([README](https://github.com/effekseer/Effekseer#readme)).

런타임이 지원하는 대상은 다음과 같다.

- 그래픽 API: DirectX 9/11/12, Metal, Vulkan, OpenGL, WebGL
- 엔진: Unity, Godot, Unreal, DX Library, Cocos2d-x
- 콘솔: 메일로 문의

단서가 하나 있다. README 는 **"master 브랜치는 개발 브랜치이니 프로덕션에 쓰지 말라"** 고 적어 두었다. 릴리스 태그를 받아 써야 한다.

원 게시물의 요약에는 2D 애니메이션 내보내기 기능도 언급돼 있다. 그런데 README 본문에서는 그 기능을 확인하지 못해서 이 글에서는 뺐다.

## 5. 복셀 — Voxel Tools for Godot (godot_voxel)

README 의 자기소개는 "Godot Engine 4 에서 볼륨 지형을 만드는 C++ 모듈/확장"이다 ([README](https://github.com/Zylann/godot_voxel#readme)). 높이맵 지형으로는 못 만드는 것들을 위한 도구다.

- 동굴·오버행·터널
- 게임 안에서 파고 쌓기

README 가 밝힌 기능은 다음과 같다.

- 무한 페이징 청크
- 마인크래프트식 블록 복셀
- Transvoxel 알고리즘으로 LOD 를 거는 매끈한 지형
- 인스턴싱

단서는 배포 형태다. README 로드맵에 아직 **"Make GDExtension work"** 가 남아 있다. 지금 가장 확실한 경로는 엔진 모듈 쪽이고, 그러려면 **Godot 를 직접 빌드**해야 할 수 있다. 같은 Godot 지형 도구여도 Terrain3D(공식 빌드에서 바로 동작)와 도입 비용이 다르다. 또 README 는 이 프로젝트를 비영리·자원봉사로 개발한다고 밝힌다.

## 6. 길찾기 — Recast Navigation

게임 AI 내비게이션의 사실상 표준 라이브러리다. README 는 이 라이브러리가 Unity·Unreal·Godot·O3DE 의 AI 내비게이션 기능을 떠받친다고 적는다 ([README](https://github.com/recastnavigation/recastnavigation#readme)). 모듈은 이렇게 나뉜다.

| 모듈 | 하는 일 |
|---|---|
| Recast | 레벨 지오메트리 → 내비메시 생성 (복셀로 래스터화 → 필터링 → 영역 분할 → 폴리곤화) |
| Detour | 내비메시 위 길찾기·공간 쿼리 |
| DetourTileCache | 타일 단위 스트리밍·동적 장애물 |
| DetourCrowd | 다수 에이전트의 이동·충돌 회피·군중 시뮬레이션 |
| DebugUtils / RecastDemo | 시각화·데모 |

요구 사항은 C++98 컴파일러뿐이고, 라이선스는 Zlib 이다.

유의할 점도 있다. **마지막 정식 릴리스가 v1.6.0(2023-05-21)** 이다. 저장소에는 2026-02 까지 push 가 있었지만, 그 뒤로 태그는 나오지 않았다. 최신 수정이 필요하면 특정 커밋에 고정해서 쓰는 수밖에 없다. 공식 문서는 [recastnav.com](https://recastnav.com) 에 있다.

## 7. 애니메이션 — ozz-animation

스켈레탈 애니메이션 **런타임** 라이브러리다. 로딩·샘플링·블렌딩을 맡고, 특정 렌더러나 엔진에 매이지 않는다. README 는 데이터 지향 설계를 강조한다 ([README](https://github.com/guillaumeblanc/ozz-animation#readme)).

- **오프라인 툴체인**이 glTF·FBX·Collada·OBJ·3DS·DXF 를 ozz 형식으로 변환한다.
- **런타임**은 C++17 과 표준 라이브러리에만 의존한다.
- WebAssembly·Linux·macOS·Windows 에서 테스트한다고 밝힌다.

라이선스 표기에 사소한 불일치가 있다. README 는 MIT 라고 적지만, GitHub API 의 license 필드는 `NOASSERTION` 을 돌려줬다. GitHub 가 라이선스 파일을 자동으로 판별하지 못했다는 뜻이다. 상용 프로젝트에 넣을 생각이라면 저장소의 라이선스 파일 원문을 직접 확인하는 편이 안전하다.

참고로 아래 8번 The Forge 의 애니메이션 시스템이 ozz 를 기반으로 한다 (The Forge README).

## 8. 렌더링 프레임워크 — The Forge

ConfettiFX 의 크로스플랫폼 렌더링 프레임워크다 ([README](https://github.com/ConfettiFX/The-Forge#readme)). README 의 지원 플랫폼 목록은 이렇다.

- Windows 10/11 (DirectX 12 + DXR 레이트레이싱)
- Steam Deck (Vulkan 1.1 + ray query)
- Android (Vulkan 1.1)
- iOS·iPadOS·macOS (Intel·Apple silicon)
- Quest 2
- Xbox·PS4·PS5·Switch

라이선스는 플랫폼에 따라 갈린다. PC·Apple·Android·Steam Deck·Quest 는 **Apache-2.0** 으로 GitHub 에 공개돼 있다. 반면 **콘솔(PlayStation·Xbox·Switch)은 인증된 개발자에게 요청 시에만 제공되는 상용 라이선스**다.

README 는 무엇이 들어 있고 무엇이 빠졌는지도 직접 밝힌다.

- 들어 있는 것: 비동기 리소스 로더, Lua 스크립팅, ozz 기반 애니메이션, NEON 을 쓰는 수학 라이브러리, GPU·CPU 메모리 관리, 터치 제스처 입력
- 빠진 것: 씬 그래프·리소스 스트리밍은 제공하지 않는다. **물리·네트워킹·사운드도 없다.**

그러니까 "엔진"이 아니라 엔진을 만들거나 기존 엔진을 다른 플랫폼으로 옮기기 위한 부품 세트다. README 는 Starfield 의 플랫폼 확장, Supergiant 의 Hades 를 사례로 든다(ConfettiFX 의 자체 주장).

GitHub 의 마지막 릴리스는 v1.63(2025-03-21)이다. push 는 2026-08 까지 있었다.

## 9. 메시 최적화 — meshoptimizer

README 는 목적을 이렇게 설명한다. GPU 가 삼각형 메시를 그릴 때 여러 단계가 정점·인덱스 데이터를 처리하는데, 그 데이터를 각 단계에 맞게 재배열하고, 메시 복잡도와 저장 용량을 줄이는 알고리즘을 제공한다 ([README](https://github.com/zeux/meshoptimizer#readme)). README 가 권하는 기본 파이프라인 순서는 이렇다.

1. 인덱싱
2. 정점 캐시 최적화
3. (선택) 오버드로 최적화
4. 정점 페치 최적화

그 위에 다음 기능들이 더 있다.

- **단순화(LOD 생성)**
- **메시 셰이더용 클러스터(meshlet) 생성**
- **정점·인덱스·meshlet 압축**: 이 압축 방식은 glTF 확장 `EXT_meshopt_compression`·`KHR_meshopt_compression` 으로 표준화돼 있다.

README 가 밝힌 수치는 다음과 같다. 모두 저자 측 수치이고 데이터에 따라 달라진다고 단서를 단다.

- 정점 디코더는 최신 데스크톱 CPU 에서 3–6 GB/s
- 정점 데이터 압축률은 보통 2–4배

인터페이스는 C/C++ 이고, Rust crate 와 JS 패키지도 있다. 함께 배포되는 명령줄 도구 `gltfpack` 은 glTF 파일을 자동으로 최적화한다. 데비안·우분투·vcpkg·Conan 패키지로도 받을 수 있다.

## 10. 노이즈 — FastNoise2

SIMD 를 쓰는 **노드 그래프 기반** 노이즈 생성 라이브러리다(C++17). 노드 그래프 구조를 택한 이유를 README 가 직접 설명한다 ([README](https://github.com/Auburn/FastNoise2#readme)). 노이즈 종류별로 배열을 따로 만들어 나중에 스칼라 연산으로 합치는 기존 방식에서는 SIMD 의 이점이 사라진다. 노드 그래프로 묶으면 다음이 가능하다.

- 덧셈·곱셈·블렌드 같은 연산 전체를 하나로 융합할 수 있다.
- 중간값이 메모리에 쓰이지 않고 **SIMD 레지스터 안에** 머문다.

README 의 기능 목록은 다음과 같다.

- 노이즈: Perlin·Simplex·SuperSimplex(OpenSimplex2S)·Value·Cellular
- 프랙탈: FBm·Ridged
- 도메인 워핑
- 2D/3D/4D 생성
- 같은 노드 트리를 여러 스레드에서 쓸 수 있는 스레드 안전성

실무에서 쓸모 있는 부분은 **시각적 Node Editor** 다. 2D 높이맵과 3D 메시로 결과를 미리 보면서 노드를 짜고, 그 트리를 **짧은 문자열로 직렬화**해 런타임에 그대로 불러온다. 웹(WASM) 버전도 있다.

## 고를 때 걸리는 것들

1. **엔진 종속성.** Terrain3D·godot_voxel 은 Godot 전용이다. Material Maker 는 Godot 로 만든 독립 앱이라 출력물(텍스처)은 어느 엔진에서나 쓸 수 있다. 나머지 7개는 C/C++ 라이브러리라서 자체 엔진이나 다른 엔진에 붙일 수 있다.
2. **"최신 릴리스"의 날짜.** Recast(2023-05)와 The Forge(2025-03)는 저장소 활동에 비해 릴리스 태그가 오래됐다. 태그를 쓸지 커밋에 고정할지 먼저 정해야 한다.
3. **README 가 직접 단 경고.** Effekseer master 는 프로덕션 비권장이다. godot_voxel 은 GDExtension 이 미완이다. The Forge 의 콘솔 지원은 상용 라이선스다.
4. **"상용 게임 수준"이라는 말.** 실제 상용 타이틀에 쓰였다는 근거는 Jolt(Horizon Forbidden West, Death Stranding 2)와 The Forge(Hades 등)의 README 자기 서술뿐이다. 10개를 같은 조건에서 비교한 중립적인 제3자 벤치마크는 찾지 못했다.

AI 코딩 에이전트와 함께 쓴다는 관점에서 하나만 덧붙인다. 위 라이브러리들은 대부분 README·공식 문서·샘플이 충실하다. 그래서 에이전트에게 "이 README 의 기본 파이프라인대로 붙여라"라고 범위를 좁혀 시키기 좋은 재료다. 다만 그렇게 했을 때 결과물이 상용 수준이 되는지는 별개의 문제다. 이 글에서는 그 부분을 다룰 근거를 갖고 있지 않다.

## References

**원 게시물**
- AI Innovation Studio (Telegram) — <https://t.me/aiinnovationstudio>

**저장소 (README 가 1차 출처)**
- Jolt Physics — <https://github.com/jrouwe/JoltPhysics> · 문서 <https://jrouwe.github.io/JoltPhysics/>
- Terrain3D — <https://github.com/TokisanGames/Terrain3D>
- Material Maker — <https://github.com/RodZill4/material-maker>
- Effekseer — <https://github.com/effekseer/Effekseer>
- Voxel Tools for Godot — <https://github.com/Zylann/godot_voxel>
- Recast & Detour — <https://github.com/recastnavigation/recastnavigation> · 문서 <https://recastnav.com>
- ozz-animation — <https://github.com/guillaumeblanc/ozz-animation>
- The Forge — <https://github.com/ConfettiFX/The-Forge>
- meshoptimizer — <https://github.com/zeux/meshoptimizer> · gltfpack <https://github.com/zeux/meshoptimizer/tree/master/gltf>
- FastNoise2 — <https://github.com/Auburn/FastNoise2> · Web Node Editor <https://auburn.github.io/FastNoise2/>

**표준·데이터**
- Khronos glTF — [KHR_meshopt_compression](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_meshopt_compression/README.md)
- GitHub REST API — [Repositories](https://docs.github.com/en/rest/repos/repos) · [Releases](https://docs.github.com/en/rest/releases/releases) (별 수·라이선스·릴리스 조회, 2026-10-30 12:40 KST)
