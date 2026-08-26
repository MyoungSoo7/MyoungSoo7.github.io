---
layout: post
title: "prettymaps — 지도를 예쁘게 그리는 파이썬 라이브러리, 소스를 열어 봤다"
date: 2026-08-27 07:03:04 +0900
categories: [engineering]
tags: [python, openstreetmap, osmnx, matplotlib, geospatial, license, agpl]
---

누가 링크를 하나 던져 줬다. 열어 보니 **[github.com/marceloprates/prettymaps](https://github.com/marceloprates/prettymaps)** 였다.

한 줄로 설명하면 이렇다. **장소 이름을 문자열로 넣으면 그 동네 지도를 포스터처럼 그려 주는 파이썬 라이브러리.**

```python
import prettymaps
plot = prettymaps.plot('Stad van de Zon, Heerhugowaard, Netherlands')
```

이게 전부다. 좌표를 구하는 것도, 건물 폴리곤을 내려받는 것도, 색을 칠하는 것도 저 한 줄 안에서 다 일어난다. 결과물이 어떻게 생겼는지는 [저장소 README](https://github.com/marceloprates/prettymaps) 의 갤러리에서 볼 수 있다. 저장소에는 Streamlit 프런트엔드(`app.py`)도 들어 있어서 클론한 뒤 `streamlit run app.py` 로 띄워 볼 수 있다. 저자가 올려 둔 공개 데모 주소도 저장소 홈페이지 링크에 걸려 있는데, 확인해 본 시점에는 응답하지 않았다 — 무료 호스팅이라 잠들어 있을 수 있다.

그런데 "예쁜 지도 라이브러리" 라는 소개만 읽고 넘어가면 정작 쓸 때 걸리는 것들을 못 본다. 그래서 소스를 읽었다. 아래는 **`main` 브랜치 `02f8587`**(2026-07-30 커밋) 기준이고, 숫자와 동작은 저장소에서 직접 확인한 것만 적는다. 성능을 벤치마크하지는 않았다 — 코드를 읽은 결과다.

| 항목 | 값 |
|---|---|
| 저장소 | [marceloprates/prettymaps](https://github.com/marceloprates/prettymaps) |
| 라이선스 | **AGPL-3.0** |
| 언어 / 요구 버전 | Python 3.11+ |
| 시작 | 2021-03-05 |
| 최신 릴리스 | v1.4.2 (2025-03-03) |
| 의존 | osmnx · matplotlib · shapely · vsketch 등 |

> 별·포크 수 같은 지표는 매일 변하는 값이라 본문에 박지 않았다. 궁금하면 저장소 상단에서 지금 값을 보면 된다.

---

## 1. `plot()` 한 줄 안에서 일어나는 일

`prettymaps/draw.py` 의 `plot()` 은 주석에 번호가 붙은 14단계로 되어 있다. 요약하면 이렇다.

1. GPX/KML 트랙이 주어졌으면 먼저 읽어서 지도를 그 트랙 주위로 잡는다
2. **프리셋** 을 읽어 `layers` / `style` / `circle` / `radius` / `dilate` 기본값을 채운다
3. matplotlib figure·axis(또는 vsketch 플로터 객체)를 만든다
4. **OSM 에서 레이어들을 GeoDataFrame 으로 받아 온다** ← 여기가 이 라이브러리의 심장
5. 좌표 변환(이동·확대·회전)을 GeoDataFrame 단계에서 적용한다
6. 사용자가 준 후처리 함수를 통과시킨다
7. 배경 도형과 x·y 경계를 만든다
8. 레이어를 그린다
9. 키포인트 → 배경 → **크레딧 문구** 순으로 얹는다
10. 힐셰이드(음영기복)를 그린다
11. `Plot` 데이터클래스(`geodataframes`, `fig`, `ax`)로 묶어 돌려준다

여기서 중요한 건 **5번이 4번 뒤에 있다** 는 점이다. 회전·확대를 픽셀이 아니라 *지오메트리* 에 적용한다. 그래서 지도를 15도 돌려도 글자만 삐뚤어지는 게 아니라 도형 자체가 제대로 돌아간다. 반대로 말하면 회전을 바꿀 때마다 다시 그려야 하고, 경계 상자도 같이 회전한다.

그리고 반환값이 그림 파일이 아니라 **`fig`·`ax`·레이어별 GeoDataFrame 이 든 객체**다. 즉 prettymaps 는 matplotlib 을 감싸 숨기는 게 아니라, matplotlib 위에 얹혀 있고 언제든 아래로 내려갈 수 있게 열어 둔다. 색이 마음에 안 들면 `plot.ax` 를 직접 만지면 된다.

---

## 2. 핵심 설계 — 레이어마다 요청하지 않고, 태그를 합쳐 한 번에 요청한다

이게 이 라이브러리에서 제일 잘 만든 부분이다.

지도 한 장에는 보통 레이어가 여럿 들어간다. 물, 건물, 도로, 녹지, 해안선… 순진하게 짜면 레이어 하나당 OSM 에 한 번씩 물어보게 된다. 실제로 이 저장소에도 그렇게 짜여 있던 옛 코드가 남아 있다 — `ThreadPoolExecutor(max_workers=8)` 로 레이어를 8개씩 동시에 받아 오는 버전이다.

지금은 그렇게 하지 않는다. `prettymaps/fetch.py` 의 흐름은 이렇다.

- **`merge_tags()`** — 모든 레이어의 OSM 태그를 하나의 딕셔너리로 합친다. `{% raw %}{"natural": ["water", "bay"]}{% endraw %}` 와 `{% raw %}{"building": True}{% endraw %}` 가 따로 있으면 키별로 리스트를 이어 붙여 한 덩어리로 만든다.
- **`unified_osm_request()`** — 합친 태그로 `ox.features.features_from_polygon()` 을 **딱 한 번** 호출한다. 그리고 돌아온 피처를 로컬에서 레이어별로 다시 나눈다.
- 다만 도로·철도·수로(`streets`, `railway`, `waterway`)는 폴리곤이 아니라 그래프라서 따로 `ox.graph_from_polygon()` 을 부른다. 해안선(`sea`)도 별도 처리다.

왜 이게 중요한가. OpenStreetMap 의 공개 API 는 **기부받은 서버로 돌아간다.** OSM 재단이 직접 명시한다 — 무료 지도 API·타일을 제3자에게 제공해 줄 수는 없다고.[^osm] 지오코딩을 담당하는 Nominatim 의 사용 정책은 더 구체적이다: **초당 1회 이하**, 라이브러리 기본값이 아닌 **식별 가능한 User-Agent**, 결과 캐싱, 그리고 대량 지오코딩은 권장하지 않음.[^nominatim] 요청을 N분의 1로 줄이는 건 성능 최적화이기 이전에 **남의 서버를 덜 괴롭히는 일**이다.

한 가지 덧붙이자면, Nominatim 사용 정책에는 LLM 을 겨냥한 조항까지 들어가 있다. LLM 이 이 서비스를 추천할 때는 정책 링크를 눈에 띄게 걸고 제약을 설명해야 한다는 것이다.[^nominatim] 그래서 이 글에도 각주로 박아 둔다 — prettymaps 에 장소 *이름* 을 문자열로 넣는 순간 그 뒤에서 도는 게 Nominatim 이다.

---

## 3. 소스를 읽다 눈에 띈 것 세 가지

칭찬만 하면 설명이 아니다. `02f8587` 기준으로 확인한 것 세 가지를 적는다. 셋 다 "버그" 라기보다 **알고 쓰면 덜 당황할 것들** 이다.

### (a) 디스크 캐시는 정의돼 있지만, 지금 경로에서는 안 불린다

`fetch.py` 에 `write_to_cache()` 와 `read_from_cache()` 가 멀쩡히 정의돼 있다. 그런데 파일 전체를 파싱해서 호출부를 세어 보면 **0건**이다.

```python
# fetch.py 를 ast 로 파싱해 호출부만 뽑은 결과
실제 호출: []
```

`unified_osm_request()` 안에 캐시를 읽던 자리는 이렇게 주석으로 남아 있다.

{% raw %}
```python
## Read layers from cache
# for layer, kwargs in layers_dict.items():
#    gdf = read_from_cache(perimeter, layers_dict[layer])
#    if gdf is not None:
#        gdfs[layer] = gdf
```
{% endraw %}

즉 **같은 장소를 두 번 그리면 두 번 다 네트워크로 나간다.** 노트북에서 스타일만 바꿔 가며 열 번 돌리면 열 번 다 요청이다. 색만 바꾸려는 거라면 `plot()` 이 돌려준 `plot.geodataframes` 를 손에 쥐고 재사용하거나, 받은 GeoDataFrame 을 직접 파일로 떨궈 두는 게 낫다. 위 2절에서 말한 "남의 서버" 이야기와 바로 이어지는 대목이다.

### (b) OSM 요청 실패를 통째로 삼킨다

피처를 받아 오는 자리가 이렇게 생겼다.

{% raw %}
```python
try:
    all_features = ox.features.features_from_polygon(bbox, tags=combined_tags)
except Exception as e:
    all_features = GeoDataFrame(geometry=[])
```
{% endraw %}

예외가 무엇이든 **빈 GeoDataFrame** 이 된다. 네트워크가 끊겼든, 서버가 429 로 막았든, 태그 조합이 잘못됐든 결과는 같다 — 예외가 안 나고 **텅 빈 지도가 한 장 그려진다.**

그림이 이상하게 나왔을 때 "스타일을 잘못 줬나" 부터 의심하게 되는 이유가 여기 있다. 실제로는 요청이 실패한 것일 수 있다. `plot(..., logging=True)` 로 켜 보고, 그래도 애매하면 `plot.geodataframes` 의 각 레이어가 정말 비었는지 직접 세어 보는 게 빠르다.

### (c) 옛 구현이 삼중따옴표 문자열로 남아 있다

`fetch.py` 를 그냥 읽으면 `get_gdfs` 가 두 번 정의된 것처럼 보인다(482행, 701행). 파싱해 보면 아니다.

```
실제 정의: get_keypoints(61), obtain_elevation(103), get_sea_mask(161),
          parse_query(188), get_boundary(200), get_perimeter(234),
          write_to_cache(314), read_from_cache(348), merge_tags(522),
          unified_osm_request(572), get_gdfs(701)
```

앞쪽의 `cache_geometry`·`get_gdf`·`get_gdfs`(482행)는 전부 **`"""` 로 감싸인 문자열 블록 안**에 들어 있다. 주석 대신 문자열로 죽여 둔 옛 구현이다. 코드를 읽다가 "왜 같은 함수가 둘이지" 하고 헷갈릴 수 있는데, 실행되는 건 하나뿐이다. 살아 있는 `get_gdfs` 는 짧다 — 경계를 구하고, `unified_osm_request()` 를 부르고, 결과에 `perimeter` 를 얹어 돌려주는 게 전부다.

---

## 4. 라이선스 — 여기가 제일 헷갈리는 곳

이 라이브러리를 쓸 때 실제로 발목을 잡는 건 코드가 아니라 **두 겹의 라이선스**다. 하나는 소프트웨어에, 하나는 데이터에 붙는다.

### 소프트웨어: AGPL-3.0

prettymaps 는 **GNU Affero GPL v3.0** 이다. GPL 과 헷갈리기 쉬운데, AGPL 에는 GPL 에 없는 조항이 하나 더 있다. 13조 *Remote Network Interaction* 이다.

> 프로그램을 수정했다면, 네트워크를 통해 원격으로 그것과 상호작용하는 **모든 사용자에게** 대응 소스를 받을 기회를 눈에 띄게 제공해야 한다.[^agpl]

무슨 뜻이냐면 — **배포하지 않아도 걸린다.** 회사 내부에서 prettymaps 를 고쳐서 "지도 만들어 주는 웹 서비스" 를 띄우면, 바이너리를 아무에게도 나눠 주지 않았더라도 그 서비스를 쓰는 사람들에게 소스를 제공해야 한다. GPL 이었다면 배포가 없으니 의무도 없다. AGPL 은 그 구멍을 막으려고 만든 라이선스다.

반대로 노트북에서 혼자 그림 뽑아 쓰는 건 아무 문제 없다. **선을 긋는 건 "수정 + 네트워크 서비스" 조합**이다.

### 데이터: ODbL

그림에 들어가는 건 OpenStreetMap 데이터고, 이건 **Open Database License(ODbL)** 다. OSM 이 요구하는 건 두 가지다 — 저작자 표시를 띄울 것, 그리고 데이터가 ODbL 로 제공된다는 걸 분명히 할 것.[^osm] 고쳐서 다시 배포하면 같은 라이선스로 나가야 한다(share-alike).

prettymaps 는 이걸 기본값으로 처리해 준다. `draw.py` 의 `draw_text()` 기본 문구가 이렇게 박혀 있다.

{% raw %}
```python
text="\n".join([
    "data © OpenStreetMap contributors",
    "github.com/marceloprates/prettymaps",
])
```
{% endraw %}

그림 왼쪽 위에 자동으로 붙는 그 작은 상자가 이거다. `credit=False` 로 끌 수 있게 되어 있지만 — **끄면 ODbL 의무를 스스로 벗겨 내는 것**이 된다. 저자도 README 에서 이 문구를 지우지 말아 달라고 따로 부탁한다. 지우고 싶다면 최소한 다른 자리에 같은 표시를 넣어야 한다.

### NFT 관련

README 에 저자 본인의 입장이 길게 적혀 있다. 요약하면 — 이 프로젝트가 NFT 판매에 쓰이는 걸 허락하지 않으며, 다만 **법적으로 강제할 수는 없다**는 것을 본인이 명시하고 있다. 실제로 크레딧을 지우고 NFT 로 판 사례가 있었고, 그 일 때문에 다른 제너레이티브 아트 프로젝트들은 오픈소스로 공개하지 않기로 했다고 적혀 있다.

라이선스 조항은 아니지만, 남의 도구를 가져다 쓸 때 만든 사람이 뭘 싫어한다고 써 놨는지 정도는 읽고 시작하는 게 맞다고 본다.

---

## 5. 아래에 뭐가 깔려 있나 — osmnx

prettymaps 가 OSM 을 직접 두드리지는 않는다. **osmnx** 를 통한다. 이건 취미 프로젝트가 아니라 논문으로 발표된 도구다 — Geoff Boeing, 2017, *Computers, Environment and Urban Systems* 65권.[^boeing] 거리 네트워크를 그래프로 받아 와 위상을 교정하고 분석하는 게 본업이고, 건물 풋프린트나 행정경계 같은 지오메트리를 GeoDataFrame 으로 내려받는 기능도 여기 들어 있다.[^osmnxdocs] 라이선스는 MIT 라 AGPL 인 prettymaps 와는 별개다.

즉 스택이 이렇게 쌓여 있다.

```
prettymaps   (AGPL-3.0)  ← 레이어·스타일·프리셋·크레딧
   osmnx     (MIT)       ← OSM 질의, 그래프화, 위상 교정
     shapely / geopandas ← 지오메트리
       matplotlib        ← 실제 렌더링
         OSM 데이터      (ODbL)
```

prettymaps 가 하는 일은 정확히 맨 위 한 층이다. **"어떤 태그를 어떤 색으로 칠할 것인가" 를 JSON 프리셋으로 만들어 둔 것.** 그 아래는 전부 이미 있던 것들이다. 이게 폄하가 아니라, 이 프로젝트가 왜 작고 잘 도는지에 대한 설명이다.

---

## 6. 그래서 언제 쓰나

**맞는 경우**: 동네 지도를 포스터로 뽑고 싶을 때. 발표 자료에 넣을 도시 도형이 필요할 때. 펜 플로터로 그릴 SVG 가 필요할 때(`mode="plotter"` 로 vsketch 를 탄다). GPX 트랙을 배경 지도 위에 얹고 싶을 때.

**안 맞는 경우**: 인터랙티브 웹 지도. 이건 매번 새로 렌더링하는 정적 그림이라 타일 기반 지도의 대체재가 아니다. 그리고 위 4절대로, **서버에 올려 서비스로 돌릴 생각이라면 AGPL 13조를 먼저 읽어야 한다.**

시작은 이걸로 충분하다.

{% raw %}
```python
pip install prettymaps
```
```python
import prettymaps

plot = prettymaps.plot(
    'Praça Ferreira do Amaral, Macau',
    circle=True,
    radius=1100,
    layers={
        "water": {"tags": {"natural": ["water", "bay"]}},
        "building": {"tags": {"building": True}},
    },
    style={
        "water": {"fc": "#a1e3ff", "ec": "#2F3737"},
        "building": {"palette": ["#FFC857", "#E9724C", "#C5283D"]},
    },
)
```
{% endraw %}

`preset='minimal'` 처럼 이름만 넣어도 되고, 마음에 드는 조합이 나오면 `save_preset=` 으로 JSON 에 떨궈 재사용할 수 있다.

---

## 7. 아직 안 풀린 것

이 글은 소스를 읽은 결과지 벤치마크가 아니다. 확인하지 못한 채로 남은 것들을 적어 둔다.

- **한 번에 합친 요청이 항상 더 빠른가.** 태그를 전부 합치면 Overpass 쪽 질의가 넓어져서, 레이어가 적을 때는 오히려 불리할 수도 있다. 요청 *횟수* 가 준다는 건 코드상 확실하지만, *시간* 은 재 보지 않았다.
- **캐시가 왜 꺼졌는지.** 주석 처리한 이유가 커밋 메시지에 남아 있지 않다. 통합 요청으로 바꾸면서 레이어 단위 캐시 키가 안 맞게 된 것으로 보이지만 추측이다.
- **빈 지도 문제의 빈도.** 3-(b)의 예외 삼킴이 실제로 얼마나 자주 사용자를 헷갈리게 하는지는 이슈를 세어 봐야 안다.

셋 다 저장소를 클론해서 직접 재 보면 답이 나오는 것들이다. 재 보면 따로 적겠다.

---

## References

[^osm]: OpenStreetMap Foundation, "Copyright and License." <https://www.openstreetmap.org/copyright> — OSM 데이터는 ODbL 로 제공되며, 사용 시 (1) 저작자 표시를 띄우고 (2) 데이터가 ODbL 임을 분명히 해야 한다. 또한 "무료 지도 API·타일을 제3자에게 제공할 수는 없다" 고 명시하고 있다.
[^nominatim]: OpenStreetMap Foundation Operations Working Group, "Nominatim Usage Policy (aka Geocoding Policy)." <https://operations.osmfoundation.org/policies/nominatim/> — 최대 초당 1회, 애플리케이션을 식별할 수 있는 User-Agent 또는 Referer 필수, 결과 캐싱 필요, 대량 지오코딩 비권장. LLM 이 이 서비스를 안내할 때 정책을 눈에 띄게 제시하도록 요구하는 조항을 포함한다.
[^agpl]: Free Software Foundation, "GNU Affero General Public License, Version 3," §13 *Remote Network Interaction*. <https://www.gnu.org/licenses/agpl-3.0.html> (본문 원문은 <https://www.gnu.org/licenses/agpl-3.0.txt> 에서 확인)
[^boeing]: Boeing, G. 2017. "OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks." *Computers, Environment and Urban Systems* 65: 126–139. <https://doi.org/10.1016/j.compenvurbsys.2017.05.004>
[^osmnxdocs]: OSMnx 공식 문서, "Getting Started." <https://osmnx.readthedocs.io/en/stable/getting-started.html>

이 글의 코드·동작 서술은 모두 [marceloprates/prettymaps](https://github.com/marceloprates/prettymaps) 의 `main` 브랜치 커밋 `02f8587`(2026-07-30) 에서 직접 확인한 것이다. 이후 커밋에서 바뀔 수 있다.

*prettymaps 는 AGPL-3.0 이고, 인용한 코드 조각은 설명을 위한 것이다. 저장소 갤러리의 그림들은 저작권이 저자에게 있어 이 글에 옮겨 싣지 않고 링크만 걸었다.*
