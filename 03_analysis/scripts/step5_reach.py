# -*- coding: utf-8 -*-
"""
STEP 5 등시간권 도달 인구·종사자 (행정동 면적안분).

방법: 핵심역 등시간권 폴리곤(30/60분, isochrone.py 산출) × 수도권 행정동(인구·종사자)을
  면적안분(행정동∩등시간권 면적 / 행정동 면적 × 인구·종사자)으로 합산.
입력: 02_data/processed/isochrone_{region}_{30,60}min.geojson + SGIS(행정동 경계·인구·종사자)
산출: 03_analysis/transport/reach_metrics.json
범위·단위: 공간범위=수도권 등시간권 도달역 / 공간단위=행정동(면적안분) / 시간=2023 / 등시간권 기준일 2026-06-20.
한계: 행정동 내 인구·종사자 균등분포 가정(집계구보다 거침). 경계 행정동만 안분, 완전포함 행정동은 정확.
재현성: 결정론적. YEAR=2023 고정.
"""
import sys
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
sys.path.insert(0, str(FE / "songpa-landuse-analysis" / "python" / "fetch"))
import sgis_client

PROC = FE / "pangyo-cheongna-analysis" / "02_data" / "processed"
ANA = FE / "pangyo-cheongna-analysis" / "03_analysis" / "transport"
YEAR = "2023"
BANDS = [30, 60]

# 등시간권 폴리곤 로드 (EPSG:5179)
isos = {}
for region in ["pangyo", "cheongna"]:
    isos[region] = {b: gpd.read_file(PROC / f"isochrone_{region}_{b}min.geojson").to_crs("EPSG:5179").geometry.iloc[0]
                    for b in BANDS}

# 수도권 시군구 경계 → 두 지역 60분 폴리곤에 닿는 시군구 union
sgg = []
for sido in ["11", "31", "23"]:
    d = sgis_client.get("boundary/hadmarea.geojson", year=YEAR, adm_cd=sido, low_search=1)
    for f in d["features"]:
        sgg.append({"adm_cd": f["properties"]["adm_cd"], "geometry": shape(f["geometry"])})
sgg = gpd.GeoDataFrame(sgg, crs="EPSG:5179")
union60 = isos["pangyo"][60].union(isos["cheongna"][60])
hit = sgg[sgg.intersects(union60)]
print(f"닿는 시군구 {len(hit)}개 — 행정동 경계·인구·종사자 수집...")

# 닿는 시군구의 행정동 경계 + 인구(searchpopulation) + 종사자(company) — low_search=1
emd_rows = []
for i, cd in enumerate(hit["adm_cd"]):
    gj = sgis_client.get("boundary/hadmarea.geojson", year=YEAR, adm_cd=cd, low_search=1)
    popm, wrkm, crpm = {}, {}, {}
    try:
        pr = sgis_client.get("stats/searchpopulation.json", year=YEAR, adm_cd=cd, low_search=1)["result"]
        pr = pr if isinstance(pr, list) else [pr]
        popm = {r["adm_cd"]: r.get("population") for r in pr}
    except Exception as e:
        print(f"  [skip pop {cd}] {str(e)[:45]}")
    try:
        cr = sgis_client.get("stats/company.json", year=YEAR, adm_cd=cd, low_search=1)["result"]
        cr = cr if isinstance(cr, list) else [cr]
        wrkm = {r["adm_cd"]: r.get("tot_worker") for r in cr}
        crpm = {r["adm_cd"]: r.get("corp_cnt") for r in cr}
    except Exception as e:
        print(f"  [skip comp {cd}] {str(e)[:45]}")
    for f in gj["features"]:
        a = f["properties"]["adm_cd"]
        emd_rows.append({"adm_cd": a, "population": popm.get(a), "tot_worker": wrkm.get(a),
                         "corp_cnt": crpm.get(a), "geometry": shape(f["geometry"])})
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(hit)} 시군구")

emd = gpd.GeoDataFrame(emd_rows, crs="EPSG:5179").drop_duplicates(subset="adm_cd")
for c in ["population", "tot_worker", "corp_cnt"]:
    emd[c] = pd.to_numeric(emd[c], errors="coerce").fillna(0.0)
emd["emd_area"] = emd.geometry.area
print(f"행정동 {len(emd)}개 (인구합 {emd['population'].sum():,.0f}, 종사자합 {emd['tot_worker'].sum():,.0f})")

# 면적안분
results = {}
for region in ["pangyo", "cheongna"]:
    out = {}
    for b in BANDS:
        iso = isos[region][b]
        inter_area = emd.geometry.intersection(iso).area
        frac = (inter_area / emd["emd_area"]).clip(0, 1)
        out[f"{b}min"] = {
            "reach_population": int((emd["population"] * frac).sum()),
            "reach_workers": int((emd["tot_worker"] * frac).sum()),
            "reach_firms": int((emd["corp_cnt"] * frac).sum()),
            "n_emd_touched": int((frac > 0).sum()),
        }
    results[region] = out
    print(f"\n{region}:")
    for b in BANDS:
        o = out[f"{b}min"]
        print(f"  {b}분: 도달인구 {o['reach_population']:,} / 도달종사자 {o['reach_workers']:,} / 사업체 {o['reach_firms']:,} (행정동 {o['n_emd_touched']})")

results["_meta"] = {"method": "행정동 면적안분", "year": YEAR, "base_date": "2026-06-20",
                    "n_sigungu": int(len(hit)), "n_emd": int(len(emd)),
                    "limitation": "행정동 내 균등분포 가정"}
ANA.mkdir(parents=True, exist_ok=True)
(ANA / "reach_metrics.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[저장] reach_metrics.json")
