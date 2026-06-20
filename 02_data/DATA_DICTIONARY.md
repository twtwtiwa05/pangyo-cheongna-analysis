# 데이터 사전 (DATA_DICTIONARY) — 판교·청라 업무지구 비교분석

> 작성: `data-cartographer` 종합 책임자 · 일자 2026-06-20 · STEP 1 (데이터 완전파악 게이트) 산출물
> 근거: 8갈래 정찰(C1~C6 + 검증 V-A, V-B)의 실측 결과(duckdb/pyogrio/pyarrow/unzip 쿼리)를 통합·중복제거.
> 원칙: **확인된 사실과 추정을 구분**한다. 모든 수치에 근거(쿼리·표본)를 명시한다. 원본 무수정·통째로드 금지(§4-D 도그마) 준수 하에 정찰했다.
> 기준 경로(`$FE`) = `C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam`

---

## 0. 한눈 요약 — 데이터셋별 한 줄(정체·규모·기준시점)

| # | 데이터셋 | 정체 | 규모(실측) | 기준시점 | 판정 |
|---|---|---|---|---|---|
| C1-1 | `subway_network/network/nodes.tsv` | 지하철 역 노드(등시간권 핵심) | 915행 × 10컬럼 | 시계열(begin/effective_begin) | **READY** |
| C1-2 | `subway_network/network/links.tsv` | 역간/환승 링크(통과시간 초) | 1192행 × 11컬럼 | 시계열 | **READY** |
| C1-3 | `subway_network/line_waits.parquet` | 노선별 환승 대기(초) | 42행 × 2컬럼 | — | **READY** |
| C2 | `통신사 데이터.zip` (P1_MOBILE) | 휴대폰 링크단위 경로통행(가점) | 194.2GB 압축 / 28 parquet | **2025-02-10~16(1주)** | **CONDITIONAL** |
| C3 | `integrated_network_202603_ver1.gpkg` | 통합 교통망(통신사 공간배치) | nodes 1,568,910 / links 680,913 | **2026-03** 버전 | **READY** |
| C4-1 | `smartcard_legs_seoul_*.parquet` | 교통카드 레그 단위 | 18,715,237행 | **2024-11-14(1일)** | **READY(+C5)** |
| C4-2 | `smartcard_tripchains_seoul_*.parquet` | 교통카드 OD 통행사슬 | 14,441,668행 | 2024-11-14 | **READY(+C5)** |
| C4-3 | `smartcard_tripchains_corrected_*.parquet` | RAPTOR 환승보정판 | 8,834,802행 | 2024-11-14 | READY(보조·부가가치 제한) |
| C4-4 | `trip_blocks_20241114.parquet` | 수단블록 분해(별도 trip_id) | 10,695,519행 | 2024-11-14 | **CONDITIONAL(카드체계 미연결)** |
| C4-5 | `subway_chained_nodes.parquet` | 지하철 노드사슬 | 2,802,202행 | 2024-11-14 | **CONDITIONAL(카드체계 미연결)** |
| C5-1 | `gtfs/stops.txt` | 전국 GTFS 정류장 좌표 | 212,105행 | GTFS 2025-01 생성 | READY |
| C5-2 | `bus_stop_mapping_20241114.parquet` | 버스 정류장ID→좌표 | 114,558행 | 2024-11-14 | **READY** |
| C5-3 | `subway_station_mapping_20241114.parquet` | 지하철 역ID→좌표 | 846행 | 2024-11-14 | **READY** |
| C5-4 | `gtfs/stop_times.txt` | GTFS 시간표(대용량) | 1.73GB | GTFS 2025-01 | READY(술어푸시다운 필수) |
| C6-A | 지정데이터 4종(SGIS·VWorld·건축HUB·OSM) | 판교/청라 **미수집** | 송파 산출물로 스키마 확정 | API 수집 필요 | **CONDITIONAL/BLOCKED** |
| C6-B | 교통카드 코드북 `CD/*.dat` + xlsx | 코드값 라벨링 사전 | 5종 .dat 전수 + TCN 144필드 | 2025-08 정의서 | **READY** |

> **핵심 한 줄 결론:** 등시간권(C1)·교통카드(C4+C5)·통신사 공간배치(C3)는 **모두 분석 가능(BLOCKED 아님)**. 통신사 본데이터(C2)는 **194GB 처리·전수 매칭률 미측정**으로 조건부. 지정데이터(C6-A)는 **API 미수집** 상태(스키마는 송파로 확정). **두 검증(V-A, V-B) 모두 PASS.**

---

## 1. C1 — 제공 지하철 네트워크 그래프 (등시간권 핵심)

> **판정: READY (BLOCKED 아님).** 데이터 자체로 등시간권 산출 즉시 가능. 핵심역 id 4개 전부 일치, dijkstra 레시피 실측 작동, 시계열 필터 작동(2026-06-20 검증). 단 '도달 인구·종사자' 최종 수치는 SGIS 집계구(C6-A) 면적안분 결합 필요.

### 1-1. `subway_network/network/nodes.tsv` (역 노드)

- **경로/형식/규모:** TSV(tab 구분, UTF-8, 헤더 1행) · **915행 × 10컬럼** · 120KB, 비압축. (동일 내용 `nodes.parquet` 병존 — tsv는 geometry WKT 문자열, parquet은 Point 객체)
- **기준시점:** export 2026-05-05. `begin` 운영시작일 분포 **1974-08-15 ~ 2032-12-31**(미래 개통 노선 포함). `effective_begin` 비어있지 않은 노드 10개(2021-12-18 ~ 2050-12-30).
- **공간범위:** 수도권 전역. WGS84 bbox lng 126.4237~127.7238, lat 36.7697~38.1016 (인천~경기동부~서울). 청라·판교·강남 모두 포함.
- **CRS:** EPSG:5179(Korea 2000 Unified, meter; `x_5179`/`y_5179`/`geometry_wkt`) + EPSG:4326(WGS84; `lng`/`lat`) **동시 제공**.
- **공간단위:** 점(Point) = 역. **환승역은 노선 수만큼 노드 중복**(판교 = 신분당 824 + 경강 26, 2노드).

| 컬럼 | 타입 | 단위 | 코드값/범위 | 비고 |
|---|---|---|---|---|
| `id` | int64 | — | 0..914 (연속·유일) | links가 참조. **행 index와 동일** → dijkstra indices 직접 사용 가능 |
| `linenm` | str | — | 노선명(신분당선·공항철도·경강선…) | 환승노드 식별에 statnm+linenm 페어 필요 |
| `statnm` | str | — | 역명 | 동명이역 주의 |
| `x_5179`,`y_5179` | float64 | meter | 904767~1019684 / 1863644~2011359 | EPSG:5179 |
| `lng`,`lat` | float64 | degree | 위 bbox | WGS84 |
| `begin` | str | — | `YYYY-MM-DD` | 운영/개통 시작일. **문자열 lexicographic 비교 OK** |
| `effective_begin` | str | — | `YYYY-MM-DD` 또는 `''`(905건 빈값) | 빈값이면 begin과 동일 |
| `geometry_wkt` | str(WKT) | — | `POINT (x y)` (5179) | null 0건 |

### 1-2. `subway_network/network/links.tsv` (링크/엣지)

- **규모:** TSV · **1192행 × 11컬럼** · 424KB. `begin` 1974-08-15 ~ 2032-12-31. 단위 = 라인(LineString, 5179).

| 컬럼 | 타입 | 단위 | 코드값/범위 | 비고 |
|---|---|---|---|---|
| `id` | int64 | — | 0..1191 | |
| `fromNode`,`toNode` | int64 | — | 0..914 (nodes.id FK, 무결성 확인) | |
| `timeFT` | float64 | **초(sec)** | min 61, median 156, max 1295 | from→to. transfer는 도착노선 대기 포함 |
| `timeTF` | float64 | **초(sec)** | min 61, median 156, max 1295 | to→from. **비대칭**(transfer만 다름) |
| `kind` | str | — | **`subway` 875 / `transfer` 317** | |
| `begin` | str | — | `YYYY-MM-DD` | |
| `linenm_from`,`linenm_to` | str | — | 노선명 | transfer는 다를 수 있음 |
| `length_m` | float64 | meter | min 2.7, median 1024, max 12761 | **참고용 거리(시간 아님)** |
| `geometry_wkt` | str(WKT) | — | `LINESTRING (...)` (5179) | null 0건 |

### 1-3. `subway_network/line_waits.parquet` (노선별 배차)

- **규모:** 42행 × 2컬럼(`linenm`, `waittm`). waittm = **초 단위** 환승 추가 대기(보수적 가정값). 예: 신분당선 240, 공항철도 300, 경강선 600, GTX_A/B/C 300.
- **이미 반영됨:** transfer 링크의 timeFT/timeTF에 `line_waits[도착노선]`이 **선반영** → **그래프 자작·대기 재계산 불필요.**

### 조인키 & 의존성
- `links.fromNode`/`toNode` → `nodes.id` (FK, 무결성 검증 완료).
- `nodes.id` == 행 index(0..914 연속) → **id를 dijkstra `indices`로 직접 사용**(재매핑 불필요).
- **도달인구·종사자 산출 = C6-A(SGIS 집계구) 면적안분 결합 의존.**
- **보행망 미포함**(README 명시): 역→필지 도보 접근은 별도 보정(역세권 500m/1km 버퍼).

### 품질노트
- 무결성 OK: id 0..914 연속·유일, 링크 노드참조 전부 범위 내, geometry_wkt null 0.
- 연결성: 대형 성분 1개(910노드) + **고립 5노드(인천공항자기부상철도 id 243~247)**. 판교/청라/강남 모두 대형 성분 → 분석 무영향. 통계 집계 시 `np.isfinite` 마스킹.
- 시계열 가능: 2026-06-20 기준 active 817 / future 98(신안산선·동북선·GTX_B/C·위례선 등 미개통). **등시간권 산출 시 분석 기준일 명시 필수**(미지정 시 미래노선이 도달성 과대).

### 안전쿼리 레시피 (README 검증 + 실측 확인)
```python
import pandas as pd, numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

base = "subway_network/network"
nodes = pd.read_csv(f"{base}/nodes.tsv", sep="\t", dtype={"begin":str,"effective_begin":str})
links = pd.read_csv(f"{base}/links.tsv", sep="\t", dtype={"begin":str})

# 등시간권은 반드시 기준일 고정
T = "2026-06-20"
eb = nodes["effective_begin"].fillna("")
node_eff = eb.where(eb != "", nodes["begin"])
active_ids = set(nodes.loc[node_eff <= T, "id"])
L = links[(links["begin"] <= T)
          & links["fromNode"].isin(active_ids) & links["toNode"].isin(active_ids)]

# 양방향 directed CSR (timeFT/timeTF를 두 행으로 펼침)
V = len(nodes)                       # id == 행 index (연속)
u, v = L["fromNode"].to_numpy(), L["toNode"].to_numpy()
src = np.concatenate([u, v]); dst = np.concatenate([v, u])
cost = np.concatenate([L["timeFT"].to_numpy(), L["timeTF"].to_numpy()]).astype(np.float64)
A = csr_matrix((cost, (src, dst)), shape=(V, V))

# 판교 = 824(신분당)+26(경강) 두 출발점 elementwise min, 청라=313, 강남=820
sol = dijkstra(A, indices=[824, 26]).min(axis=0)
n30 = int(((sol > 0) & (sol <= 1800)).sum())   # 30분=1800s
n60 = int(((sol > 0) & (sol <= 3600)).sum())   # 60분=3600s
```

### 알려진 함정
1. **환승역 = 다중 노드.** 판교 824+26 → "판교역 등시간권"은 두 출발점 dijkstra의 **elementwise min**으로 합쳐야 환승 경유 최단을 정확히 잡음(824 단독은 경강선 직결 놓침).
2. **링크가 directed 아님** — 한 행에 양방향 cost 둘 다. 반드시 timeFT/timeTF를 두 행으로 펼침(안 펼치면 도달성 왜곡).
3. **미래 노선 노출** — 기준일 미지정 시 GTX/신안산선(2027~2032)이 그래프에 포함 → 등시간권 과대. **분석·시스템 모두 기준일 명시 의무.**
4. **고립 5노드(자기부상철도 243~247)** — 무한대 거리, `np.isfinite` 마스킹.
5. **보행망 없음** — 역→필지 도보 보정 별도(역점 버퍼/도보속도 가정 명시).
6. `length_m`는 참고용 거리, **시간은 timeFT/timeTF(초)만 사용.**

---

## 2. C2 — 통신사 경로통행 데이터 (P1, 가점 이동데이터)

> **판정: CONDITIONAL (가점 보강용).** 스키마·시점 확정. 공간배치는 C3 LINK_ID 매칭으로 가능(V-A PASS). 단 **194GB 처리·전수 매칭률·정확 행수·link_id=0 미매칭율 미측정** → 본처리 첫 단계에서 측정 필요. **기준월 2025-02 표기 의무.**

### 경로 / 형식 / 규모 / 압축
- **경로:** `$FE/DATA(통신사,교통카드)/통신사 데이터.zip`
- **형식:** 단일 ZIP(ZIP64) 아카이브. 내부 = 일자별 폴더 × 4분할 parquet.
- **압축 크기(실측):** **194,216,167,671 bytes (≈180.9 GiB / 194.2 GB)**. 압축해제 총량 **198,589,478,737 bytes (≈185.0 GiB)** (`unzip -l` 푸터, 37 entries).
- **내부 구성(실측):** 일자별 폴더 7개 `P1_MOBILE_2025021{0..6}_parquet_parts/`, 각 `..._part_01~04.parquet`(4분할) = **28 parquet** + sample.csv(27,790B) + codebook.xlsx(10,826B, 파일명 mojibake) + dir 7. part당 ≈6.5~7.7GB, 일자별 ≈26~31GB.

### 기준시점 / 공간범위 / CRS / 공간단위
- **기준시점:** **2025-02-10 ~ 2025-02-16 (정확히 7일, 월~일)** — 폴더명·trip_date 확정. ⚠️ **교통카드(2024-11) / 지정데이터와 기준월 불일치 → 보고서 출처·기준월 표기 의무.**
- **공간범위:** 전국(sample에 경기·경남·서울·인천). **판교·청라 모두 데이터 내 존재 확인**(인천 종료 trip TRAV_TIME 39분·12,693m).
- **CRS:** P1 자체는 좌표 없음(노드/링크 ID만) → 좌표는 **C3 gpkg(EPSG:5179)** 조인으로 획득.
- **공간단위:** 통합 네트워크 **링크(leg) 단위.** 1통행(trip_no) = N개 링크 행(seq 1..N). 시간단위 = 초(IN/OUT_TIME, **추정값**).

### 스키마표 (14컬럼, 소문자 — sample.csv 헤더·codebook 합치)
| # | 컬럼 | 타입 | 단위 | 코드값/포맷 | 비고 |
|---|---|---|---|---|---|
| 1 | `trip_no` | int64 | — | `YYYYMMDD`+10자리 (19자리) | **통행ID.** int64 경계내. **부동소수 변환 금지**(정밀손실) |
| 2 | `transfer_type` | int64 | — | **1도로 2지하철 3철도 4공항 5환승 6기타** | codebook 확정. 멀티모달 수단분담 핵심 |
| 3 | `seq` | int64 | — | 1..N | 통행 내 링크 순번 |
| 4 | `link_id` | int64 | — | **0=매칭정보없음(센티넬)** | **C3 `links.LINK_ID` 조인키.** 0은 공간배치 불가 |
| 5 | `f_node_id` | int64 | — | — | **C3 `nodes.NODE_ID_RAW` 조인**(NODE_UID 아님) |
| 6 | `t_node_id` | int64 | — | — | 동상 |
| 7 | `in_time` | timestamp[s] | — | datetime | 진입시각, **추정값** |
| 8 | `out_time` | timestamp[s] | — | datetime | 진출시각, **추정값** |
| 9 | `speed` | double | **km/h** | — | 링크 통과속도, **추정값** |
| 10 | `length` | double | **m** | — | **링크 개별 길이**(누적 아님) |
| 11 | `sido_name` | string | — | 시도명 한글 | sample: 경기·경남·서울·인천 |
| 12 | `trav_time` | int64 | **분** | — | **누적** 통행시간 |
| 13 | `trav_dist` | int64 | **m** | — | **누적** 통행거리 |
| 14 | `trip_date` | date32 | — | `YYYY-MM-DD` | **codebook 미문서화**(13필드만 기재). 폴더 일자와 일치 |

### 조인키 & 의존성
- **`link_id` → C3 `links.LINK_ID`** (공간배치 본선). `f_node_id`/`t_node_id` → C3 `nodes.NODE_ID_RAW`.
- **시군구 필터:** C3 `links.*_NODE_SIGUNGU`(KTDB 코드)로 판교 31023 / 청라 23080 직접 공간필터 → 전국 raw 미적재.
- **버전 정합:** 데이터 2025-02 vs 네트워크 gpkg 2026-03(13개월 차). **V-A에서 sample 165 link_id·164 node 100% 매칭** → 동일 ID 체계 판단. 전수 매칭률은 본처리 시 재확인.

### 품질노트 / 미측정 잔여
- sample.csv = 2통행(99+111링크) = 210행, transfer_type sample은 1(도로)만 등장(2~6 미관측, 코드 존재는 codebook 보증).
- **미측정(본처리 첫 단계 필수):** ① 정확 행수(part 1개 메타데이터, **수십억 행 추정**) ② `link_id=0` 미매칭율 ③ transfer_type 2~6 실분포 ④ LINK_ID↔C3 전수 매칭률.
- IN/OUT_TIME·SPEED는 codebook이 **추정값**으로 명시 → "맵매칭 추정"임을 보고서에 명기.

### 안전쿼리 레시피
```bash
# zip 목록만(수십초). 절대 전체해제 금지
unzip -l "$FE/DATA(통신사,교통카드)/통신사 데이터.zip" | head
unzip -p "$ZIP" "P1_MOBILE_20250210_sample.csv" > _scratch/telecom_sample.csv
unzip -p "$ZIP" "*.xlsx" > _scratch/telecom_codebook.xlsx   # 파일명 mojibake → 와일드카드
```
```python
# 본처리: 1개 part만 임시추출 → DuckDB 컬럼투영+술어푸시다운 → 즉시 삭제
import duckdb, pyarrow.parquet as pq
print(pq.ParquetFile('_scratch/tmp_part01.parquet').metadata.num_rows)  # 정확 행수
duckdb.sql("""
  SELECT transfer_type, count(*) n, sum(trav_dist) tot
  FROM read_parquet('_scratch/tmp_part01.parquet')
  WHERE sido_name IN ('경기도','인천광역시')
  GROUP BY 1 ORDER BY 2 DESC""").show()
# 정밀 두 지역 필터는 link_id JOIN C3.links(*_NODE_SIGUNGU) 후
```

### 알려진 함정
1. **기준월 2025-02** — 필수지표 동일기준 비교 직접 투입 금지, 보강용.
2. **194GB 도그마** — 통째 로드·전체 해제 절대 금지. part 1개도 7GB. 단일 part 임시추출→DuckDB→삭제, 공간(시군구)·시간 사전필터 우선.
3. **link_id=0(미매칭)** — 집계 전 비율 측정·처리방침 명시.
4. **노드 조인은 NODE_ID_RAW** (NODE_UID는 0% 매칭).
5. **trip_no 부동소수 변환 금지** — int64/string 유지.

---

## 3. C3 — 통신사 통합 교통망 gpkg (LINK_ID 공간배치)

> **판정: READY.** 통신사 공간배치 본선. 추가 마스터 불필요(좌표·시군구·노드 모두 내장). **두 지역 직접 공간필터 가능(판교 3,831 / 청라 5,051 링크).** ★SIGUNGU_CD 코드체계 교정 필수.

### 데이터셋 개요
- **경로:** `$FE/DATA(통신사,교통카드)/통신사 데이터 네트워크/integrated_network_202603_ver1.gpkg`
- **형식/규모:** GeoPackage(SQLite, v1.4.0), **540,618,752 B (≈515 MB)**, 비압축. 코드북 `integrated_network_data_dictionary.xlsx`(13,091 B). `~$…xlsx`(165 B)는 Excel 잠금파일 — 무시.
- **레이어 2종:** `nodes`(Point, **1,568,910**) · `links`(Line, **680,913**).
- **기준시점:** 네트워크 버전 `202603`(2026-03). ★통신사 데이터(2025-02)와 **약 13개월 시차** → 한계 명시 대상.
- **공간범위:** 전국(SIDO 17개 전부). **CRS: EPSG:5179** 확인. 5179→4326 sanity 통과.
- **공간단위:** 교통망 그래프(노드=교차/역점, 링크=구간).

### nodes 스키마표 (fid, geom + 12 속성)
| 컬럼 | 타입 | 단위 | 코드값/예시 | 비고 |
|---|---|---|---|---|
| NODE_UID | VARCHAR | — | `R_100185`/`T_11201`/`A_*` | 수단 prefix付 전역 고유 ID |
| MODE | VARCHAR | — | road/rail/air | road 1,563,891·rail 4,974·air 45 |
| NODE_ID_RAW | VARCHAR | — | `100185`,`11201` | ★**통신사 f/t_node_id 조인키**(prefix 제거) |
| NAME | VARCHAR | — | `청라국제도시`,`판교역(신분당)` | (코드북 NO.5 NODE_TYPE 자리 — 함정) |
| X, Y | float64 | m(5179) | — | geom과 동일계 |
| SIDO_CD/SIDO_NM | VARCHAR | — | `31`/경기, `23`/인천 | ★KTDB 커스텀 코드(표준 11/28 아님) |
| SIGUNGU_CD/SIGUNGU_NM | VARCHAR(5) | — | `31023`/성남분당, `23080`/서구 | ★**KTDB 커스텀 시군구코드** |
| ADM_CD/ADM_NM | VARCHAR | — | `31023750`/판교동, `23080740/780/790`/청라1·2·3동 | 읍면동 |

### links 스키마표 (fid, geom + 23 속성)
| 컬럼 | 타입 | 단위 | 코드값 | 비고 |
|---|---|---|---|---|
| MODE | VARCHAR | — | road/rail/air/transfer | road 671,707·transfer 7,460·rail 1,727·air 19 |
| LINK_ID | VARCHAR | — | `338700014` | ★**통신사 link_id 조인키**. 680,913=distinct(전역 고유) |
| UP/DW_F/T_NODE | VARCHAR | — | NODE_ID_RAW 참조 | 양방향 dijkstra 펼치기용 |
| ONEWAY | VARCHAR | — | 0 양방향/1 일방 | 철도/항공/환승=0 |
| LEN_M | float64 | m | — | null 0건 |
| MAXSPEED | float64 | km/h | — | 도로만 |
| LINK_NAME | VARCHAR | — | `경강선(성남~여주)`,`공항철도(고속)` | |
| ROAD_RANK | int32 | — | 101 고속도로…108 연결램프 | 도로만 |
| ROAD_LINK_TYPE | int32 | — | 1 본선…8 연결로(IC) | 도로만. IC거리 보조지표 활용 가능 |
| RAIL_TYPE | int32 | — | 1 고속·2 일반·**3 지하철**·4 경전철·5~8 복합 | 철도만 |
| TRANSFER_LINK_TYPE | int32 | — | 1 철도↔철도…4 철도↔공항 | 환승만 |
| T_TIME_MIN | float64 | 분 | — | **항공 링크만**(일반 통행시간 아님 — 함정) |
| UP/DW_F/T_NODE_SIGUNGU | VARCHAR(5) | — | `31023`,`23080` | ★**지역필터 4컬럼**. null 0건 |
| UP/DW_F/T_NODE_MODE | VARCHAR | — | road/rail/air | 환승링크 해석용 |

### 조인키 & 의존성 (★실데이터 검증 완료 — V-A)
- 통신사 `link_id` → links.`LINK_ID`: sample distinct 165개 **100% 매칭**(전부 road).
- 통신사 `f/t_node_id` → nodes.`NODE_ID_RAW`: distinct 164개 **100% 매칭**.
- 지역필터: `where="UP_F_NODE_SIGUNGU IN ('31023','23080')"` → 판교 3,831 / 청라 5,051 링크. **추가 마스터 불필요.**
- 핵심역 NODE_ID_RAW: **청라국제도시 11201** / 판교(신분당) 10787·(경강) 10788·(고속) 11609.

### 안전쿼리 레시피
```python
import pyogrio
g = pyogrio.read_dataframe(GPKG, layer='links',
    columns=['MODE','LINK_ID','LINK_NAME','RAIL_TYPE','LEN_M','UP_F_NODE_SIGUNGU'],
    where="UP_F_NODE_SIGUNGU IN ('31023','23080') OR UP_T_NODE_SIGUNGU IN ('31023','23080')")
# 노드는 NODE_ID_RAW 중복(~3x) → dedup 후 통신사 조인(아니면 row 폭발)
nodes = pyogrio.read_dataframe(GPKG, layer='nodes',
    columns=['NODE_ID_RAW','SIGUNGU_CD','X','Y'], read_geometry=False)
```

### 품질노트 / 알려진 함정
- links 핵심컬럼(LINK_ID, *_NODE_SIGUNGU, LEN_M) **null 0건**.
1. **★SIGUNGU_CD 코드체계 불일치(최중요):** CLAUDE.md 가정값 `41135`(판교)·`28260`(청라)는 **표준 행안부 코드 → 이 네트워크에서 0건 매칭(footgun).** 이 gpkg는 **KTDB 커스텀 코드** = 판교/분당구 **`31023`**(SIDO `31`), 청라/인천서구 **`23080`**(SIDO `23`). **모든 통신사 공간필터 코드 교정 필수.**
2. **NODE_TYPE 미존재:** 코드북 NO.5는 실 gpkg에 컬럼 없음(`NAME`이 대체). 문서용으로만 취급.
3. **NODE_ID_RAW 다중행:** 1,568,910행 vs distinct(NODE_ID_RAW,MODE)=522,970 → 평균 ~3행 중복. **조인 전 dedup 필수.**
4. **NAME 동음이의:** `청라`→청라언덕역(대구3), `판교`→판교(서천군) → SIGUNGU_NM/SIDO_NM 병행 필터.
5. **T_TIME_MIN은 항공 전용** — 일반 통행시간 아님.
6. gpkg v1.4.0 → pyogrio "partially supported" 경고 출력하나 읽기 정상.

---

## 4. C4 — 교통카드 전처리물 segment (OD 통행사슬)

> **판정: legs/tripchains/corrected = READY(+C5 매핑).** raw `.dat` 직접 파싱 불필요(이미 OD 통행사슬로 전처리). **V-B PASS**(판교·청라 포함량 충분). trip_blocks/subway_chained = **CONDITIONAL**(smartcard 카드체계와 조인키 부재).
> 위치: `$FE/DATA(통신사,교통카드)/교통카드 링크 노드/`. 기준일 **2024-11-14(목) 단일 운영일**(04:00~익일 03:59). 'seoul' 파일명이나 실제 **수도권 전역(SIDO 11/41/28)**.

### 4-1. `segment/smartcard_legs_seoul_20241114.parquet` (레그 단위)
- **규모:** 668MB, **18,715,237행**, 15컬럼, 18 row-group. 1통행 = 1~5레그.
- **시점:** boarding_time `2024-11-14 04:00` ~ `2024-11-15 03:59`(정상). ⚠️ **alighting_time max `2024-11-23 14:25` → 이상치 존재(품질주의).**

| 컬럼 | 타입 | 단위/의미 | 관측치 | 비고 |
|---|---|---|---|---|
| card_id | string | 카드ID(익명) | | 통행주체 |
| transaction_id | string | 통행번호 | 3자리 zero-pad | **(card_id+transaction_id)=통행키** |
| num_transfers | string | 환승수 | 0~4 | 문자열 저장(캐스팅) |
| leg_num | int64 | 레그순번 | 1~5 | |
| region_code | string | **승차역 법정동코드(10자리)** | SIDO2+SIGUNGU3+… | **공간 1차필터**(판교 41135 / 청라 28260·28245) |
| transport_mode_code | string | 세부수단코드(3자리) | 201/202/115… | 코드북(CD) 미검증(추정) |
| transport_type | string | 수단대분류 | **B=버스 992만 / T=지하철 879만** | is_bus/is_subway와 1:1 |
| route_id | string | 노선ID | 버스 8자리·지하철 노선번호 | |
| distance_m | int64 | 레그거리 m | min -11485(이상치) | 음수 필터 |
| boarding_station_id | string | 승차역/정류장ID | **버스 7자리 / 지하철 4자리** | 결측 0건 |
| alighting_station_id | string | 하차역/정류장ID | 동일포맷 | **결측 204,331건(1.1%)** |
| boarding_time/alighting_time | timestamp[ns] | 승/하차 시각 | | alighting 이상치 |
| is_bus/is_subway | bool | 수단 플래그 | True 992만/879만 | 분기 기준 |

- **함정:** region_code는 **승차역 기준**(출발지만 포착). 도착지 분석은 alighting_station_id→매핑. 'seoul' 파일명에 속지 말 것.

### 4-2. `segment/smartcard_tripchains_seoul_20241114.parquet` (OD 단위 — **분석 핵심**)
- **규모:** 841MB, **14,441,668행**, 21컬럼 = legs의 distinct (card_id,transaction_id)와 정확히 일치(**통행당 1행**).
- **핵심 컬럼:** `first_boarding_station`/`last_alighting_station`(OD 양끝, **last 결측 17.8만=1.2%**), `boarding_stations`/`alighting_stations`/`route_ids`/`transport_types`(레그배열, `|` 구분), `mode_chain`(`T` 623만·`B` 454만·`B-B`·`B-T`…), `duration_sec`(**min -65 이상치, median 1674, max 773498**), `hour`(0~23, 피크 08시·18시), `is_bus_only`/`is_subway_only`/`is_mixed`, `total_distance_m`.
- **함정:** **tripchains 자체엔 법정동코드 없음** → 공간필터는 station_id→C5 매핑 경유(또는 legs.region_code 1차필터 후 통행키 역조인).

### 4-3. `segment/smartcard_tripchains_corrected_20241114.parquet` (RAPTOR 환승보정)
- **규모:** 511MB, **8,834,802행**(tripchains의 61% 부분집합), 26컬럼(+`transfer_corrected`·`corrected_num_transfers`·`corrected_legs_json`·`raptor_duration_sec`·`correction_error`).
- **부가가치 제한:** 환승보정 실발생 **820건**(0.009%), num_transfers 변경 501건뿐. raptor_duration 대부분 NULL → **보조용.**

### 4-4. `trip_blocks_20241114.parquet` (수단블록 — **별도 trip_id 체계**)
- **규모:** 2.2GB, **10,695,519행**, 20컬럼, 3,304,756 distinct trip_id.
- **컬럼:** trip_id(int64, 1~3.3M), block_idx, block_type/block_type_name(**1 도로 410만·2 지하철 280만·3 철도 10.4만·4 항공 34·5 환승 369만**), entry_node/exit_node(KTDB 통합노드ID), link_ids_json, assigned_mode(XFER/SUB/RAIL/AIR, 도로 NULL), mode_confidence, evidence_type.
- **⚠ 함정(중대):** **trip_id(int 1~3.3M)는 smartcard (card_id,transaction_id) 문자열키와 매핑정보 없음.** 규모도 상이(3.3M vs 14.4M) → **두 데이터 직접 조인 불가.** entry/exit_node→C3 통합망 노드좌표 경유로만 공간필터 가능(추정).

### 4-5. `subway_chained_nodes.parquet` (지하철 노드사슬)
- **규모:** 49MB, **2,802,202행**(=trip_blocks 지하철블록 280만과 일치), 5컬럼(trip_id, block_idx, chained_nodes(`[11326,…]` JSON), n_original_links, n_chained_nodes).
- **조인:** `(trip_id, block_idx)` → trip_blocks(block_type=2)와 1:1. **smartcard 카드체계와 분리**(보조).

### 핵심 의존성
- **C5 매핑(필수):** `subway_station_mapping`(846)·`bus_stop_mapping`(114,558) — station_id→좌표·구역계 PIP.
- **구역계 정의(STEP 2):** region_code 5자리는 시군구 단위(분당구/서구 전체)로 거칠다 → 업무지구 정밀경계는 station_id 좌표 PIP 필요.
- **C3 통합망 nodes:** trip_blocks/subway_chained의 entry/exit_node 좌표화(추정, 검증과제).

---

## 5. C5 — GTFS + 정류장 좌표 매핑 (station_id→좌표)

> **판정: READY (BLOCKED 아님).** segment station_id가 매핑으로 97.9%/99.7% 좌표화, 판교/청라 핵심역 좌표 확인. **C4 OD 공간배치의 필수 자산.**
> 베이스: `$FE/DATA(통신사,교통카드)/교통카드 링크 노드/` (이하 `<C5>`)

### 5-1. `gtfs/stops.txt` — 전국 정류장 좌표 마스터
- CSV(UTF-8 BOM), 13.5MB, **212,105행**. CRS WGS84(EPSG:4326, `stop_lat`/`stop_lon`). 전국(lat 33.12~38.54, lon 124.62~131.87).
- **함정:** stop_id가 **GTFS 내부 ID**(`RS_ACC1_S-2-0095`)로 segment의 4/7자리 `station_id`와 **직접 일치 안 함** → segment→좌표는 반드시 §5-2/5-3 매핑 사용. stops.txt는 시간표/보조좌표용.

### 5-2. `bus_stop_mapping_20241114.parquet` — 버스 정류장ID→좌표 (★C4 조인 핵심)
- 4.5MB, **114,558행**. WGS84+UTMK(5179) 병기.
| 컬럼 | 의미 | 비고 |
|---|---|---|
| stop_id | **7자리 zero-pad** | segment 버스레그 직접 조인 |
| lat/lon | WGS84 | **4,243행 0,0 garbage → lon>124 필터 필수** |
| utmk_x/utmk_y | EPSG:5179 | |
| type_code/region_code | 추정(코드북 미확인) | region_code SIDO 2자리(41경기·11서울·28인천) |
- **조인 검증(실측):** 버스레그 LEFT JOIN → **9,891,001/9,920,269 = 99.7% 매칭.**

### 5-3. `subway_station_mapping_20241114.parquet` — 지하철 역ID→좌표 (★C4 조인 핵심)
- 77KB, **846행**. WGS84+UTMK+rnode.
| 컬럼 | 의미 | 비고 |
|---|---|---|
| station_id | **4자리 zero-pad** | segment 지하철레그 직접 조인 |
| stop_id | GTFS 연결 ID | |
| stop_name | 역명 | |
| line_code | 노선코드(추정) | |
| stop_lat/stop_lon | WGS84 | |
| utmk_x/utmk_y | EPSG:5179 | |
| rnode_id/rnode_name/snap_distance_m | 도로/철도망 노드 | trip_blocks 연결·품질지표 |
- **핵심역 확인(실측):** **판교 station_id=`1501`**(37.39491,127.11135) 및 `4311`(중복) · **청라국제도시 `4210`**(37.55588,126.62533) · 강남 `0222`/`4307` · 정자 `1857`/`4312`.
- **조인 검증(실측):** 지하철레그 → **8,613,711/8,794,968 = 97.9% 매칭.**
- **함정:** 동일역 복수 station_id(판교 1501·4311) → 역 단위 집계 시 stop_name/좌표 그룹핑.

### 5-4. 기타 GTFS / crossref
- `routes.txt`(27,138), `trips.txt`(349,580), `stop_times.txt`(**1.73GB — 통째 로드 금지, 술어푸시다운**), `calendar.txt`(service B1, 2017~2030 매일).
- `station_crossref.csv`(110행): gtfs_id↔card_id 부분집합(부산권 추정) → 전수매핑 아님, 정합 검증 보조용.

### ★조인 체인 (C4↔C5↔공간)
```
segment.boarding/alighting_station_id (4자리=지하철, 7자리=버스)
  ├─ is_subway → subway_station_mapping.station_id → stop_lat/lon (WGS84)
  └─ is_bus    → bus_stop_mapping.stop_id        → lat/lon (WGS84)
       → 판교/청라 bbox 또는 구역계 PIP 필터
tripchains.first_boarding_station / last_alighting_station → 동일 매핑 → OD 분석
trip_blocks.entry/exit_node, subway_chained.chained_nodes → C3 통합망 nodes 의존(별도)
```

### 안전쿼리 레시피
```python
import duckdb
DIR = "$FE/DATA(통신사,교통카드)/교통카드 링크 노드"
con = duckdb.connect()
seg = f"{DIR}/segment/smartcard_legs_seoul_20241114.parquet"
sub = f"{DIR}/subway_station_mapping_20241114.parquet"
df = con.execute(f"""
  SELECT s.card_id, s.boarding_time, m.stop_name, m.stop_lat, m.stop_lon
  FROM read_parquet('{seg}') s
  JOIN read_parquet('{sub}') m ON s.boarding_station_id = m.station_id
  WHERE s.is_subway
    AND m.stop_lon BETWEEN 127.09 AND 127.13 AND m.stop_lat BETWEEN 37.38 AND 37.42
""").fetchdf()
# tripchains OD: WHERE first_boarding_station IN ('1501','4311')  -- 판교역
```

### 알려진 함정 (종합)
1. **stops.txt ID ≠ segment station_id** → 반드시 bus/subway 매핑 경유.
2. **동일역 복수 station_id**(판교 1501·4311) → 좌표/역명 그룹핑.
3. **bbox 면적 비대칭** — 1차 bbox 카운트(판교 296 vs 청라 477)는 bbox 크기 차이 → 구역계 클립 후 동일 면적 정규화.
4. **distance_m 음수**(legs 최소 -11485) → 거리 집계 시 필터.
5. **기준월 불일치**(카드 2024-11 / 통신사 2025-02 / 네트워크 2026-03) → 보고서 표기 의무.
6. **line/type/region_code 코드값 의미 미확정**(코드북 미동봉) → '추정'.

---

## 6. C6 — 지정데이터 수집 readiness + 교통카드 코드북(CD)

### 6-A. 지정데이터 4종 (판교/청라 **미수집** — 송파 산출물로 스키마 확정)

> **판정: CONDITIONAL/BLOCKED.** SGIS·VWorld·건축HUB·OSM 4종은 판교/청라용 **아직 미수집**(API 호출 필요=의존성 미충족). 단 송파 산출물로 **수집 후 산출 스키마 100% 확정**. OSM만 송파에도 산출물 없어 readiness 낮음.

#### A-1. SGIS 집계구 인구·가구 → `census_tracts.geojson`
- 송파 샘플: 3.8MB, **1,278 집계구**. GeoJSON, **저장 EPSG:4326**(원천 SGIS 5179 → `.to_crs(4326)`). 공간단위 = 집계구(~500명 폴리곤).
- 주요 컬럼: `adm_cd`(14자리 SGIS ID), `population`, `household_cnt`, `family_member_cnt`, `avg_family_member_cnt`, `x`/`y`(UTM-K 대표점).
- API: BASE `https://sgisapi.mods.go.kr/OpenAPI3`. ① 인증 `/auth/authentication.json` ② 경계 `/boundary/hadmarea.geojson` ③ 집계구 `/boundary/statsarea.geojson` ④ 통계 `/stats/searchpopulation.json`·`/stats/household.json`.
- **★핵심 함정 — SGIS adm_cd ≠ 행안부 코드:** SGIS 자체 5자리(송파 SGIS=11240, 행안부=11710). 판교/청라도 행안부코드 직접 입력 불가 → `find_songpa_code.py` 패턴(hadmarea를 adm_nm으로 매칭)으로 **SGIS 코드 런타임 역산** 필요.
- **★종사자/사업체 통계 부재:** 송파 샘플엔 인구·가구만 → 필수지표 '도달 종사자' 산출용 **SGIS 사업체통계 별도 엔드포인트 확인 필요.**

#### A-2. VWorld 용도지역·필지 → `parcels_landuse.geojson`
- 송파 샘플: 24.8MB, **31,117 필지**. GeoJSON MultiPolygon, EPSG:4326. `gosi_year=2025`.
- 주요 컬럼: `pnu`(**PNU 19자리** 조인키), `jibun`, `jiga`(공시지가), `zoning`(용도지역명, 예 제2종일반주거지역), `zoning_year`.
- API: `GET https://api.vworld.kr/req/data` dataset **필지=`LP_PA_CBND_BUBUN`**, **용도지역=`LT_C_UQ111`**. **BBOX 10km² 이내 제약** → 행정동 envelope 분할 + dedup. 필지↔용도지역은 centroid PIP sjoin.
- **수집 시:** 데이터셋명 전국공통(변경 불필요), BBOX(동 envelope)만 판교/청라로 교체.

#### A-3. 건축HUB 건축물대장(표제부) → `buildings.json`
- 송파 샘플: 10.3MB, JSON 배열 **24,211 동**(GeoJSON 아님, 좌표 없음, PNU 기반).
- 주요 컬럼: `pnu`(19자리 조립), `mainPurpsCdNm`(주용도명), `totArea`(**연면적 ㎡**, 연면적가중 최빈 기준), `grndFlrCnt`/`ugrndFlrCnt`, `useAprDay`.
- API: `getBrTitleInfo?serviceKey&sigunguCd&bjdongCd&...`. **100건/page 한도.**
- **★바꿀 상수:** `SIGUNGU` 11710→**판교 41135 / 청라 28260**(VWorld·건축HUB는 행안부 코드 사용), `BJDONG_CODES`(법정동) 전체교체. **법정동코드는 CD_AREA.dat에서 도출 가능**(판교 41135 산하 19행 / 청라 28260 산하 23행).

#### A-4. OSM 도로망 → (송파 산출물 **없음**)
- **현황:** 송파 processed/에 도로망 산출물 부재, data-sources.md에도 절차 미기재. **스키마 미확정** → 수집수단(osmnx/Overpass)·스키마 신규 설계 필요. **이 항목만 readiness 낮음(BLOCKED).**

#### A-5. 3단계 공간조인 요약 (`join-strategy.md` + `parcels_joined.geojson` 실측)
- A 건축물→필지: PNU(19) 조인, 대표주용도 = **연면적(totArea) 가중 최빈**.
- B 필지→집계구: centroid **PIP(within) sjoin**, 경계걸침 면적최대 귀속.
- PNU 구조(19): 시군구(5)+법정동(5)+산여부(1)+본번(4)+부번(4).
- CRS 정책: 저장/교환 EPSG:4326, 거리·면적·centroid 계산 EPSG:5179.
- 최종 `parcels_joined.geojson`(31,117 필지) 컬럼: pnu, zoning, **main_use**, use_breakdown(dict), use_diversity(섀넌 엔트로피), n_buildings, total_floor_area, jiga, **census_adm_cd**.

### 6-B. 교통카드 코드북 (`CD/`) — 전수 해석 완료

> **판정: READY.** 5종 .dat 전수 해석 + TCN 144필드 정의서 확보. raw `.dat`(`DATA_20241114.zip`) 삭제됨 → **코드북은 C4 segment 전처리물의 코드값 라벨링 사전**으로 활용.

- **공통 .dat 포맷:** 파이프(`|`) 구분, 헤더 없음, UTF-8(콘솔 cp949 mojibake → Python utf-8 정상). 정의서 `CD/ColumnDefinition_20250804.xlsx`(11 시트).
- **`CD_AREA.dat`** (49,838행, 8열): 시도/시군구/읍면동(10자리)/명칭/생성·말소일자. ★**판교 41135=19행, 청라 28260=23행, 송파 11710=15행 실측 확인.** 법정동코드 추출원.
- **`CD_CARDGB.dat`** (104행): `(정산사ID, 카드구분코드)` **복합키** → 명칭. 단일코드 해석 금지.
- **`CD_USERTYPE.dat`** (8행, 전수): 01 일반 / 02 어린이 / 03 청소년 / 04 경로 / 05 장애인 / 06 국가유공자 / 07 외국인 / 08 기타.
- **`CD_TCBO.dat`** (5행, 전수): 03 마이비 / 08 티머니 / 11 이동의즐거움 / 14 iM유페이먼트 / 15 한페이시스.
- **`CD_TFCMN.dat`** (1,955행): `(정산사ID, 수단코드)` 복합키. **공항철도(206)·신분당선(208) 식별 가능**(청라·판교 서사 직결).
- **★TCN 144필드 — CLAUDE.md 가설 정정:** '10칸 반복'은 부정확. 실제 = **속성블록별 10슬롯 병렬배열**(1~6 기본, 지역 7~16, 승차역 97~106, 하차역 117~126, 시작/종료 요약 127~139, 총계 140~144). raw 삭제됨 → segment parquet 라벨링용. 부속 마스터 STTN(정류장 X/Y좌표+시군구), ROUTESTTN(경유정류장 좌표) 존재.

### 안전쿼리 레시피
```python
def load_cd(path):
    with open(path, encoding="utf-8") as f:
        return [l.rstrip("\n").split("|") for l in f]
cardgb = {(r[0], r[1]): r[2] for r in load_cd("CD/CD_CARDGB.dat")}   # 복합키
tfcmn  = {(r[0], r[1]): r[2] for r in load_cd("CD/CD_TFCMN.dat")}
area = load_cd("CD/CD_AREA.dat")
pangyo_emd  = [r for r in area if r[1]=="41135" and r[5].strip()]   # 법정동 추출
cheongna_emd= [r for r in area if r[1]=="28260" and r[5].strip()]
```

---

## 기준시점 정합표 (§5-B 동일기준 비교 원칙)

| 데이터 영역 | 데이터셋 | 기준시점 | 처리방침 |
|---|---|---|---|
| **지정(필수)** | SGIS 집계구 | base_year 2025 / YEAR 2023(코드) | **두 지역 동일 기준연도로 고정**(수집 시 YEAR 통일) |
| **지정(필수)** | VWorld 용도지역·필지 | gosi 2025-01 | 동일 기준 |
| **지정(필수)** | 건축HUB 건축물대장 | 표제부 최신 | 동일 기준 |
| **지정(필수)** | OSM 도로망 | 수집 시점 | 동일 일자 수집 |
| 제공 | 지하철 그래프 | 시계열(begin), 분석 기준일 명시 | **등시간권 기준일 고정 명시 의무** |
| 가점(보강) | **통신사 P1** | **2025-02-10~16(1주)** | **출처·기준월 표기 후 보강.** 필수지표 직접 투입 금지 |
| 가점(보강) | **교통카드 segment** | **2024-11-14(1일)** | **출처·기준월 표기 후 보강** |
| 룩업 | 통신사 통합망 gpkg | 2026-03 | 공간배치용(시점성 없음) |
| 룩업 | GTFS·정류장 매핑 | 2024-11~2025-01 | 좌표 룩업용 |

> **처리 원칙:** **핵심 필수지표(토지이용·등시간권·인구사회)는 동일 기준연도로 비교**한다. **이동데이터(통신사 2025-02 / 교통카드 2024-11)는 출처·기준월을 명기한 뒤 보조지표로만** 사용한다(§5-B 동일기준 위반·감점 방지).

---

## Readiness 게이트 표

| 데이터셋 | 스키마확정 | 시점확정 | 공간매핑 | 의존성충족 | 분석가능 |
|---|:---:|:---:|:---:|:---:|:---:|
| C1 nodes.tsv (915) | ✅ | ✅ | ✅(5179+4326) | △ 도달인구는 SGIS 의존 | ✅ |
| C1 links.tsv (1192) | ✅ | ✅ | ✅ | ✅(line_waits 선반영) | ✅ |
| C1 line_waits (42) | ✅ | ✅ | n/a | ✅ | ✅ |
| C2 통신사 P1 (28 parquet) | ✅ | ✅ | △ C3 조인 필요 | △ 전수매칭률 미측정 | **조건부**(보강용) |
| C3 gpkg nodes (1.57M) | ✅ | ✅ | ✅ | ✅ | ✅ |
| C3 gpkg links (681K) | ✅ | ✅ | ✅(SIGUNGU 31023/23080) | ✅ | ✅ |
| C4 legs (18.7M) | ✅ | ✅ | ✅(region+station) | △ C5 매핑 필요 | ✅ |
| C4 tripchains (14.4M) | ✅ | ✅ | ✅(station→C5) | △ C5 매핑 필요 | ✅(OD/첨두 즉시) |
| C4 corrected (8.8M) | ✅ | ✅ | ✅ | △ | ✅(부가가치 제한) |
| C4 trip_blocks (10.7M) | ✅ | ✅ | △ KTDB노드 경유 | ❌ 카드체계 조인키 부재 | **조건부** |
| C4 subway_chained (2.8M) | ✅ | ✅ | △ KTDB노드 경유 | ❌ 카드체계 조인키 부재 | **조건부** |
| C5 stops.txt (212K) | ✅ | ✅ | ✅(WGS84) | 자립 | ✅ |
| C5 bus_mapping (114K) | ✅ | ✅ | ✅(99.7% 매칭) | 자립 | ✅ |
| C5 subway_mapping (846) | ✅ | ✅ | ✅(97.9% 매칭) | 자립 | ✅ |
| C6-A SGIS (미수집) | ✅(스키마) | ❌ | ✅ | ❌ API 수집+코드역산 | 수집 후 |
| C6-A VWorld (미수집) | ✅(스키마) | ❌ | ✅ | ❌ API 수집 | 수집 후 |
| C6-A 건축HUB (미수집) | ✅(스키마) | ❌ | ✅ | ❌ API 수집 | 수집 후 |
| C6-A OSM (미수집) | ❌ | ❌ | ✅ | ❌ 수단·스키마 미설계 | **BLOCKED** |
| C6-B CD 코드북 5종 | ✅ | ✅ | n/a | ✅ | ✅ |

범례: ✅ 충족 · △ 부분/의존 · ❌ 미충족

---

## 핵심 검증 결과 (V-A, V-B)

### V-A — 통신사 P1 LINK_ID/NODE_ID ↔ 통합네트워크 gpkg 매칭 + 버전·공간 정합 → **PASS**
- **표본:** `P1_MOBILE_20250210_sample.csv`(210 leg, 165 distinct LINK_ID, 164 distinct node; 경기·경남·서울·인천, transfer_type 전부=1 도로).
- **결과:** ① **LINK_ID 165/165 = 100.0%** 매칭(links 680,913행). ② **F/T_NODE_ID ↔ nodes.NODE_ID_RAW 164/164 = 100.0%**(NODE_UID 대비 0% → 반드시 NODE_ID_RAW). ③ (f,t)노드쌍 ↔ UP/DW 노드쌍 **210/210 = 100.0%**. ④ 공간정합 완벽(경남→김해, 서울→강서, 경기→부천오정, 인천→계양, 좌표 5179 정합).
- **버전:** 네트워크 202603 vs 통신사 2025-02(13개월 명목 시차). ID·공간 100% 정합 → 실질 영향 없음. 단 **본데이터 전수 매칭률 + link_id=0 비율은 본처리(STEP 7)에서 재확인 권장**(표본은 도로 전용 → rail/transfer 링크 별도 확인).

### V-B — 교통카드 segment 판교·청라 포함량 정류장 기준 카운트 → **PASS**
- `'seoul' 전처리물에 경기/인천 누락` 위험 **기각.** segment는 수도권 전역(SIDO 11/41/28).
- **판교**(bbox 127.09~127.13/37.38~37.42): 정류장 302(지하철 6+버스 296), 레그 437,981(버스 227,356+지하철 210,625), OD 326,001, 판교역(1501/4311) 지하철 승/하차 45,829/46,131.
- **청라**(bbox 126.61~126.68/37.51~37.57): 정류장 499(8+491), 레그 182,900(지하철 99,622+버스 83,278), OD 146,482, 청라국제도시역(4210) 승/하차 8,319/8,030.
- **두 지역 모두 수만~수십만 건으로 임계(수천+) 압도 → PASS.** 지역 교차검증(region_code 판교 41135xxxxx·청라 28260xxxxx) 확인. 조인 매칭률 지하철 97.9%·버스 99.7%.
- **주의:** bbox는 사각형이라 인접역(서현·야탑 등) 혼입 가능 → 현 수치는 **포함량 충분성 판정용 하한**. STEP 2 구역계 폴리곤 PIP로 재집계 권장. (판교>청라 약 2배 통행 → 서사가설과 정합, 단 면적 정규화 후 재집계.)

### 핵심역 id 확정 (C1 그래프 / C3 통합망 / C5 매핑 3계통 일치 확인)
| 역 | C1 지하철그래프 id | C3 통합망 NODE_ID_RAW | C5 교통카드 station_id |
|---|---|---|---|
| **청라국제도시**(공항철도) | **313** | 11201 | 4210 |
| **판교**(신분당선) | **824** | 10787 | 1501(+4311 중복) |
| **판교**(경강선) | **26** | 10788 | (지하철 4311) |
| **강남**(신분당선) | **820** | — | 0222/4307 |

- C1 dijkstra 실측: 판교(824) 30분 90노드·60분 592 / 청라(313) 30분 50·60분 317 → **판교 30분권 1.8배·60분권 1.87배 더 많은 노드 도달.** 역간 통행시간: 판교→강남 832초(13.9분), 청라→강남 3916초(65.3분, **약 4.7배**). 서사가설을 네트워크 차원에서 1차 지지(단 노드수≠인구·종사자, SGIS 결합 필요).

---

## BLOCKED / CONDITIONAL 항목과 해결방안 (우선순위)

| 우선 | 항목 | 상태 | 해결방안 |
|---|---|---|---|
| 1 | **C6-A 지정데이터 4종 미수집** | CONDITIONAL | STEP 3에서 송파 `python/fetch/*` 포팅. API 키(SGIS/VWORLD/BUILDING_HUB) 확보 + 상수 교체(아래) |
| 2 | **SGIS adm_cd 역산** | CONDITIONAL | 수집 시 `find_songpa_code` 패턴으로 판교/청라 SGIS 5자리 코드 런타임 해결(행안부 41135/28260 직접 입력 불가) |
| 3 | **SGIS 종사자/사업체 통계 엔드포인트** | CONDITIONAL | 송파 샘플 인구·가구만 → '도달 종사자' 지표용 SGIS 사업체통계 별도 엔드포인트 확인(필수지표) |
| 4 | **C6-A OSM 도로망** | BLOCKED | 송파 산출물·문서 모두 부재 → osmnx/Overpass 수집수단·스키마 신규 설계 |
| 5 | **C2 통신사 본데이터 측정** | CONDITIONAL | 본처리 첫 단계: 단일 part 임시추출→정확 행수·link_id=0율·transfer_type 2~6 분포·LINK_ID 전수 매칭률 측정→삭제 |
| 6 | **C4 trip_blocks/subway_chained 카드체계 미연결** | CONDITIONAL | smartcard 직접 조인 불가 → entry/exit_node→C3 통합망 노드좌표 경유. 보조지표로만 활용 |
| 7 | **SIGUNGU_CD 코드체계 교정** | 조치 필요 | 통신사 공간필터는 KTDB 코드(판교 31023/청라 23080), 지정데이터는 행안부(41135/28260) — **하네스 문서·코드의 41135/28260을 통신사 경로에 쓰면 0건(footgun)** |

> **순수 BLOCKED는 OSM 도로망 1건뿐.** 나머지는 모두 CONDITIONAL(수집·측정으로 해소). 등시간권·교통카드·통신사 공간배치는 즉시 분석 가능.

---

## 분석 착수 권고 — 다음 STEP 우선순위 + 리스크 Top 3

### 다음 STEP 우선순위
1. **STEP 2 (구역선정·근거):** 판교/청라 구역계(지구단위계획 경계) 직접 정의 + 면적 + 출처. region_code/bbox를 정밀 폴리곤으로 교체(V-B 하한치를 구역계 PIP로 확정). 청라 '저조' 근거 리서치. **기준월 확정표 고정.**
2. **STEP 5 (등시간권 — 즉시 착수 가능):** C1 그래프로 dijkstra 30/60분(판교 824+26 elementwise min, 청라 313, 기준일 2026-06-20 명시). C6-A SGIS 집계구 면적안분 결합 → 도달 인구·종사자 + 누적접근성곡선. **C1은 READY이므로 SGIS 수집과 병렬 진행.**
3. **STEP 3 (지정데이터 수집):** SGIS(코드 역산+사업체통계)·VWorld·건축HUB 수집(상수 교체). OSM 수단·스키마 설계. STEP 4 토지이용 지표로 연결.
4. **STEP 7 (가점 이동데이터):** 교통카드(C4+C5)는 OD·첨두 즉시 가능. 통신사(C2)는 본데이터 측정 후 두 지역 시군구 필터 추출.

### 리스크 Top 3
1. **기준시점 불일치(감점 1순위 위험):** 통신사 2025-02 / 교통카드 2024-11 / 지정데이터 별도. **완화:** 필수지표는 동일 기준연도, 이동데이터는 출처·기준월 명기 후 보조지표로만(기준월 정합표 고정·모든 표/그림에 §5-A 4종 범위·단위 명시).
2. **통신사 194GB 처리:** 통째 로드 1회 = 분석 마비. **완화:** §4-D 도그마 엄수(단일 part 임시추출→DuckDB 컬럼투영+시군구/시간 술어푸시다운→즉시 삭제). 정확 행수·미매칭율 사전 측정.
3. **OneDrive 동기화 / 대용량 + 코드체계 footgun:** (a) `$FE`가 OneDrive 경로 → 대용량 parquet 동기화 충돌·잠금 위험(작업 중 동기화 일시중지 권장, raw·_scratch 커밋 금지). (b) **SIGUNGU_CD 이원화**(통신사 KTDB 31023/23080 vs 지정데이터 행안부 41135/28260) — 경로별 코드 혼용 시 0건 매칭. 코드 상수를 데이터 출처별로 분리 관리.

---

## 부속 — 정찰 산출물(로컬 `_scratch/`, 커밋 금지)
`telecom_sample.csv`(27KB)·`telecom_codebook.xlsx`(10KB)·`zip_list_full.txt`·`c4_*.py`·`cd_decoded.txt`·`coldef_decoded.txt`·`songpa_schema.txt`. 원본 통신사 zip(194,216,167,671 bytes) 무수정 확인.
