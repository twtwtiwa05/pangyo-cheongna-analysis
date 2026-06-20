# -*- coding: utf-8 -*-
"""
STEP 8 통계검증 — 두 지역 분포 차이의 통계적 유의성 (분석깊이 보강).
검정: 집계구 직주비 분포 / 필지 용적률 분포 — KS·Mann-Whitney U·Cliff's delta(효과크기).
입력: census_tracts_{region}.geojson, parcels_joined_{region}.geojson
산출: 03_analysis/validation/stat_tests.json
원칙(research-data-analysis): 통계 주장엔 검정법·표본수·p값·효과크기 명시.
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

FE = Path(".")
PROC = FE / "pangyo-cheongna-analysis/02_data/processed"
ANA = FE / "pangyo-cheongna-analysis/03_analysis/validation"
ANA.mkdir(parents=True, exist_ok=True)
DONG = {"pangyo": ["31023740"], "cheongna": ["23080740", "23080780", "23080790"]}


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    gt = (a[:, None] > b[None, :]).sum()
    lt = (a[:, None] < b[None, :]).sum()
    return (gt - lt) / (len(a) * len(b))


out = {}

# 1) 집계구 직주비 분포 (판교 > 청라 검정)
jhr = {}
for region in ["pangyo", "cheongna"]:
    tr = gpd.read_file(PROC / f"census_tracts_{region}.geojson")
    tr["dong8"] = tr["adm_cd"].astype(str).str[:8]
    d = tr[tr["dong8"].isin(DONG[region])].copy()
    for c in ["population", "tot_worker"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[d["population"].fillna(0) > 0]
    jhr[region] = (d["tot_worker"].fillna(0) / d["population"]).replace([np.inf, -np.inf], np.nan).dropna()

ks = stats.ks_2samp(jhr["pangyo"], jhr["cheongna"])
mw = stats.mannwhitneyu(jhr["pangyo"], jhr["cheongna"], alternative="greater")
out["jobs_housing_ratio"] = {
    "test": "집계구 직주비(종사자/상주인구) 분포 — 판교 vs 청라",
    "n_pangyo": int(len(jhr["pangyo"])), "n_cheongna": int(len(jhr["cheongna"])),
    "median_pangyo": round(float(jhr["pangyo"].median()), 3),
    "median_cheongna": round(float(jhr["cheongna"].median()), 3),
    "KS_stat": round(float(ks.statistic), 3), "KS_p": float(ks.pvalue),
    "MannWhitney_U_p(판교>청라)": float(mw.pvalue),
    "cliffs_delta": round(float(cliffs_delta(jhr["pangyo"], jhr["cheongna"])), 3),
}

# 2) 필지 용적률 분포
far = {}
for region in ["pangyo", "cheongna"]:
    pa = gpd.read_file(PROC / f"parcels_joined_{region}.geojson")
    pa = pa[pa["total_floor_area"].notna() & (pd.to_numeric(pa["lot_area"], errors="coerce") > 0)]
    far[region] = (pd.to_numeric(pa["total_floor_area"], errors="coerce") / pa["lot_area"] * 100).replace([np.inf], np.nan).dropna()
ks2 = stats.ks_2samp(far["pangyo"], far["cheongna"])
mw2 = stats.mannwhitneyu(far["pangyo"], far["cheongna"], alternative="greater")
out["FAR"] = {
    "test": "건축 필지 용적률(연면적/대지면적%) 분포 — 판교 vs 청라",
    "n_pangyo": int(len(far["pangyo"])), "n_cheongna": int(len(far["cheongna"])),
    "median_pangyo": round(float(far["pangyo"].median()), 1),
    "median_cheongna": round(float(far["cheongna"].median()), 1),
    "KS_stat": round(float(ks2.statistic), 3), "KS_p": float(ks2.pvalue),
    "MannWhitney_U_p(판교>청라)": float(mw2.pvalue),
    "cliffs_delta": round(float(cliffs_delta(far["pangyo"], far["cheongna"])), 3),
}

(ANA / "stat_tests.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
for k, v in out.items():
    print(f"\n[{k}] {v['test']}")
    print(f"  중앙값 판교 {v['median_pangyo']} vs 청라 {v['median_cheongna']} (n={v['n_pangyo']}/{v['n_cheongna']})")
    print(f"  KS={v['KS_stat']} p={v['KS_p']:.2e} | Cliff's δ={v['cliffs_delta']}")
print("\n[저장] stat_tests.json")
