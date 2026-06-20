# -*- coding: utf-8 -*-
"""
SGIS 집계구 인구·가구·종사자·사업체 수집 — 판교(분당구 31023)·청라(서구 23080).
songpa fetch_sgis 포팅 + company.json(종사자·사업체) 추가 + 2지역 동시.

※ 코드체계: SGIS adm_cd = 통계청코드(분당구 31023·서구 23080). 행안부(41135/28260) 아님.
   (VWorld·건축HUB는 행안부 코드 사용 — 경로별 분리 관리)
기준연도 YEAR = 2023 (두 지역 동일 — §5-B 동일기준).
범위·단위: 공간범위=분당구·서구 행정구역 / 공간단위=집계구(약 500명 폴리곤) / 시간=2023 단년.

산출(저장 EPSG:4326):
  02_data/processed/census_tracts_{pangyo,cheongna}.geojson  집계구 + population·household_cnt·corp_cnt·tot_worker
  02_data/processed/emdong_{pangyo,cheongna}.geojson         행정동 경계(구역계 정의용: 삼평동 / 청라1~3동)
  02_data/raw/sgis/*.csv, *.json                              원본 통계·경계
재현성: 결정론적(난수 없음). 입력=SGIS API(songpa/.env 키), 기준연도 2023 고정.
"""
import sys
import json
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
SONGPA_FETCH = FE / "songpa-landuse-analysis" / "python" / "fetch"
sys.path.insert(0, str(SONGPA_FETCH))
import sgis_client  # songpa/.env 자동 로드(키 재사용)

PROJ = FE / "pangyo-cheongna-analysis"
PROC = PROJ / "02_data" / "processed"
RAW = PROJ / "02_data" / "raw" / "sgis"
PROC.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

CRS_UTMK, CRS_WGS84 = "EPSG:5179", "EPSG:4326"
YEAR = "2023"
REGIONS = {
    "pangyo":   {"sigungu": "31023", "name": "성남시 분당구", "focus": "삼평동(31023740)"},
    "cheongna": {"sigungu": "23080", "name": "인천 서구", "focus": "청라1~3동(23080740/780/790)"},
}


def gj_to_gdf(gj: dict, crs: str = CRS_UTMK) -> gpd.GeoDataFrame:
    feats = gj.get("features", [])
    if not feats:
        return gpd.GeoDataFrame(geometry=[], crs=crs)
    rows = [{**f["properties"], "geometry": shape(f["geometry"])} for f in feats]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)


def stats_df(payload: dict) -> pd.DataFrame:
    r = payload.get("result", [])
    if isinstance(r, dict):
        r = [r]
    return pd.DataFrame(r)


for key, reg in REGIONS.items():
    sig = reg["sigungu"]
    print(f"\n===== {key} ({reg['name']} {sig}) — focus {reg['focus']} =====")

    # 1) 행정동 경계 (구역계 정의용)
    gj_em = sgis_client.get("boundary/hadmarea.geojson", year=YEAR, adm_cd=sig, low_search=1)
    (RAW / f"{key}_emdong_boundary.json").write_text(json.dumps(gj_em, ensure_ascii=False))
    em = gj_to_gdf(gj_em).to_crs(CRS_WGS84)
    em.to_file(PROC / f"emdong_{key}.geojson", driver="GeoJSON")
    print(f"  행정동 {len(em)}개 → emdong_{key}.geojson")

    # 2) 집계구 통계 (low_search=2): 인구 / 가구 / 사업체·종사자
    pop = stats_df(sgis_client.get("stats/searchpopulation.json", year=YEAR, adm_cd=sig, low_search=2))
    hh = stats_df(sgis_client.get("stats/household.json", year=YEAR, adm_cd=sig, low_search=2))
    comp = stats_df(sgis_client.get("stats/company.json", year=YEAR, adm_cd=sig, low_search=2))
    print(f"  집계구 통계행: 인구 {len(pop)}, 가구 {len(hh)}, 사업체 {len(comp)}")
    pop.to_csv(RAW / f"{key}_pop.csv", index=False)
    hh.to_csv(RAW / f"{key}_hh.csv", index=False)
    comp.to_csv(RAW / f"{key}_comp.csv", index=False)

    # 3) 집계구 경계 — 행정동별 statsarea 순회
    feats: list[dict] = []
    for emcd in sorted(em["adm_cd"].tolist()):
        gj = sgis_client.get("boundary/statsarea.geojson", adm_cd=emcd)
        feats.extend(gj.get("features", []))
        time.sleep(0.12)
    (RAW / f"{key}_tracts_boundary.json").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    tr = gj_to_gdf({"type": "FeatureCollection", "features": feats}).to_crs(CRS_WGS84)
    print(f"  집계구 경계 {len(tr)}피처")

    # 4) 통계 join (adm_cd 14자리)
    merges = [
        (pop, ["adm_cd", "population"]),
        (hh, ["adm_cd", "household_cnt", "family_member_cnt", "avg_family_member_cnt"]),
        (comp, ["adm_cd", "corp_cnt", "tot_worker"]),
    ]
    for df, cols in merges:
        keep = [c for c in cols if c in df.columns]
        if "adm_cd" in keep and len(keep) > 1:
            tr = tr.merge(df[keep], on="adm_cd", how="left")
    for c in ["population", "household_cnt", "family_member_cnt", "corp_cnt", "tot_worker"]:
        if c in tr.columns:
            tr[c] = pd.to_numeric(tr[c], errors="coerce")

    out = PROC / f"census_tracts_{key}.geojson"
    tr.to_file(out, driver="GeoJSON")

    def _sum(col):
        return int(tr[col].sum(skipna=True)) if col in tr.columns else -1

    print(f"  → census_tracts_{key}.geojson: {len(tr)} 집계구")
    print(f"     인구합 {_sum('population'):,} / 종사자합 {_sum('tot_worker'):,} / 사업체합 {_sum('corp_cnt'):,} / 가구합 {_sum('household_cnt'):,}")
    if "population" in tr.columns:
        print(f"     결측: 인구 {int(tr['population'].isna().sum())}, 종사자 {int(tr['tot_worker'].isna().sum()) if 'tot_worker' in tr.columns else 'NA'}")

print("\n[완료] SGIS 집계구 수집 — 판교/청라. 다음: 직주비(tot_worker/population) 산출은 STEP 4·6.")
