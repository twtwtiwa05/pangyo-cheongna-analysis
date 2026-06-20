# -*- coding: utf-8 -*-
"""
STEP 6 인구사회 지표 — 판교(삼평동)·청라(청라1~3동) 구역계 집계구 클립.

입력: 02_data/processed/census_tracts_{region}.geojson (SGIS 집계구 + 인구·가구·종사자·사업체, 2023)
산출: 03_analysis/socio/socio_metrics.json
지표(과제 §3-3): 인구·가구 / 종사자·사업체 / 직주비(종사자/상주인구) / 인구·종사자 밀도.
구역 한정: 집계구 adm_cd 앞8자리(행정동) = 삼평동 31023740 / 청라1·2·3동 23080740·23080780·23080790.
범위·단위: 공간범위=구역계 행정동 / 공간단위=집계구 / 시간=2023 단년.
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
PROC = FE / "pangyo-cheongna-analysis" / "02_data" / "processed"
ANA = FE / "pangyo-cheongna-analysis" / "03_analysis" / "socio"
ANA.mkdir(parents=True, exist_ok=True)

DONG = {"pangyo": ["31023740"], "cheongna": ["23080740", "23080780", "23080790"]}

metrics = {}
for region in ["pangyo", "cheongna"]:
    tr = gpd.read_file(PROC / f"census_tracts_{region}.geojson")
    tr["dong8"] = tr["adm_cd"].astype(str).str[:8]
    for c in ["population", "household_cnt", "tot_worker", "corp_cnt"]:
        if c in tr.columns:
            tr[c] = pd.to_numeric(tr[c], errors="coerce")
    dist = tr[tr["dong8"].isin(DONG[region])].copy()
    area = float(dist.to_crs("EPSG:5179").geometry.area.sum() / 1e6)
    pop = float(dist["population"].sum(skipna=True))
    hh = float(dist["household_cnt"].sum(skipna=True))
    wrk = float(dist["tot_worker"].sum(skipna=True))
    crp = float(dist["corp_cnt"].sum(skipna=True))

    metrics[region] = {
        "n_tracts": int(len(dist)),
        "area_km2": round(area, 3),
        "population": int(pop),
        "households": int(hh),
        "workers": int(wrk),
        "firms": int(crp),
        "jobs_housing_ratio": round(wrk / pop, 3) if pop else None,   # 직주비 = 종사자/상주인구
        "pop_density_per_km2": round(pop / area, 0) if area else None,
        "worker_density_per_km2": round(wrk / area, 0) if area else None,
        "workers_per_firm": round(wrk / crp, 2) if crp else None,
        "avg_household_size": round(pop / hh, 2) if hh else None,
    }
    m = metrics[region]
    print(f"\n===== {region} (집계구 {m['n_tracts']}, {m['area_km2']}㎢) =====")
    print(f"  인구 {m['population']:,} / 가구 {m['households']:,} / 종사자 {m['workers']:,} / 사업체 {m['firms']:,}")
    print(f"  ★직주비(종사자/인구) {m['jobs_housing_ratio']}")
    print(f"  인구밀도 {m['pop_density_per_km2']:,.0f}/㎢ / 종사자밀도 {m['worker_density_per_km2']:,.0f}/㎢")
    print(f"  업체당 종사자 {m['workers_per_firm']} / 평균가구원 {m['avg_household_size']}")

(ANA / "socio_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[저장] 03_analysis/socio/socio_metrics.json")
print("주: 업종(산업분류) 구성은 SGIS 사업체통계 업종 엔드포인트로 STEP 6-2 보강 예정.")
