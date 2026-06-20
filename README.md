# 판교·청라 업무지구 비교분석 시스템

> 스마트시티 이론과 실제 기말과제(가천대) — **데이터로 진단하는 업무지구의 성공과 실패**.
> 판교테크노밸리(성공) vs 인천 청라국제업무지구(저조)를 공공데이터로 **동일 기준** 비교하여 업무지구 성공요인을 도출한다.

## 한 줄 결론
판교(삼평동, 직주비 **4.14**)는 신분당선으로 강남 노동시장에 **30분 직결**(도달 종사자 **106만**)되어 업무지구로 성공했고, 청라(청라1~3동, 직주비 **0.28**)는 핵심역 접근성 열위(강남 **65분**·도달 종사자 **7.6만**)로 업무기능이 미실현되어 주거 위주 베드타운화했다.

## 핵심 비교 (세 영역 모두 일관)
| 지표 | 판교 | 청라 | 격차 |
|---|---|---|---|
| 30분 도달 종사자(노동시장) | 1,059,434 | 76,486 | **13.9배** |
| 직주비(종사자/상주인구) | 4.14 | 0.28 | 약 15배 |
| 업무시설 연면적 비율 | 45.1% | 16.0% | — |
| 평균 용적률 | 156.7% | 52.4% | 3배 |
| 종사자밀도(명/㎢) | 34,319 | 1,517 | 22.6배 |
| 도로망 밀도(km/㎢) | 24.95 | 14.10 | — |
| 핵심역→강남 | 13.9분 | 65.3분 | 4.7배 |

## 구역 정의 (§2)
- **판교**: 경기 성남시 분당구 **삼평동** (행정동), 2.84㎢, 핵심역 **판교역**(신분당선). 제2판교(수정구)는 제외, 종사자 보조 인용.
- **청라**: 인천 서구 **청라1·2·3동** (행정동), 20.53㎢, 핵심역 **청라국제도시역**(공항철도).
- 비교 원칙: 면적 비대칭(7.2배)은 구성비·밀도·직주비로 정규화.

## 데이터 출처·기준월 (동일기준 비교 — §5-B)
| 데이터 | 출처 | 기준시점 | 코드체계 |
|---|---|---|---|
| 집계구 인구·가구·종사자·사업체 | 통계청 SGIS OpenAPI | 2023 | 통계청(분당 31023·서구 23080) |
| 용도지역·필지 | VWorld Data API (LP_PA_CBND_BUBUN·LT_C_UQ111) | 2025 고시 | 행안부(41135·28260) |
| 건축물대장(표제부) | 건축HUB getBrTitleInfo | 현행(2026-06 수집) | 행안부 |
| 도로망 | OpenStreetMap (osmnx) | 2026-06-20 수집 | 좌표(WGS84) |
| 수도권 지하철 그래프 | 제공(LMS) | 2026-06-20 운영본 | 노드 id |
| (가점) 통신사 경로통행 P1 | 제공 | **2025-02-11** | 통합망 노드 |
| (가점) 교통카드 OD | 제공(전처리) | **2024-11-14** | 정류장 id |

> ⚠️ 이동데이터(가점)는 기준월이 달라 **출처·기준월 명기 후 보조지표로만** 사용. 필수지표는 동일 기준연도.

## 재현 절차
```bash
# 1) 환경 (Python 3.12)
pip install -r requirements.txt
# 2) API 키: songpa-landuse-analysis/.env 재사용 (SGIS/VWORLD/BUILDING_HUB)
# 3) 분석 파이프라인 (03_analysis/scripts/)
python 03_analysis/scripts/fetch_sgis.py        # SGIS 집계구 인구·종사자
python 03_analysis/scripts/make_districts.py    # 구역계·면적
python 03_analysis/scripts/fetch_vworld.py      # VWorld 필지·용도지역
python 03_analysis/scripts/fetch_buildinghub.py # 건축물대장
python 03_analysis/scripts/fetch_osm.py         # OSM 도로망
python 03_analysis/scripts/step4_landuse.py     # 토지이용 지표
python 03_analysis/transport/isochrone.py       # 등시간권(dijkstra+폴리곤)
python 03_analysis/scripts/step5_reach.py       # 도달 인구·종사자(면적안분)
python 03_analysis/scripts/step6_socio.py       # 인구사회·직주비
python 03_analysis/scripts/step7_smartcard.py   # (가점) 교통카드 OD
python 03_analysis/scripts/telco_day.py         # (가점) 통신사 P1 하루
python 03_analysis/scripts/step8_validate.py    # 통계검증(KS·Cliff's δ)
python 03_analysis/scripts/make_manifest.py     # 시스템 데이터 통합
# 4) 시스템 빌드·로컬
cd 04_system/web && npm install && npm run dev   # http://localhost:3000
```

## 폴더 구조
```
pangyo-cheongna-analysis/
├── 00_과제/ 01_구역선정/        # 구역계 정의·리서치 근거
├── 02_data/                    # DATA_DICTIONARY.md + raw(로컬) + processed(GeoJSON/JSON)
├── 03_analysis/                # landuse·transport·socio·mobility·validation + scripts
├── 04_system/web/              # Next.js 16 + MapLibre (GitHub Pages 배포 루트)
└── 05_report/                  # 근거맵 (보고서 인계)
```
※ raw 대용량 데이터(통신사 194GB 등)는 저장소 커밋 제외(.gitignore). 배포엔 전처리 소형 GeoJSON/JSON만.

## 시스템 (배포)
- GitHub Pages: _(배포 후 URL 기재)_
- 필수기능: ①두 지역 비교지도(필지 주용도·용도지역) ②등시간권 30/60분 + 도달 인구·종사자 ③비교 통계패널·차트 ④필지 클릭 속성

## AI 활용 내역
데이터 파악·수집·분석·시각화 전 과정에 Claude Code(Anthropic) 활용. 모든 수치는 원데이터(SGIS/VWorld/건축HUB API·제공 데이터)로 직접 산출했으며, 청라 '저조' 근거·판교 통계는 1차 출처(IFEZ·경기도 실태조사 등)로 교차검증했다.
