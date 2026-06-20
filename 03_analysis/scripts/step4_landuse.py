# -*- coding: utf-8 -*-
"""
STEP 4 토지이용 지표 — 판교(삼평동)·청라(청라1~3동).
songpa join_pipeline 계승: 건물→필지 18자리 PNU 조인(platGb 무시) + 연면적 가중 최빈 대표주용도.

입력: 02_data/processed/parcels_landuse_{region}.geojson, buildings_{region}.json
산출:
  02_data/processed/parcels_joined_{region}.geojson  (필지+대표주용도+용적률용 대지면적)
  03_analysis/landuse/landuse_metrics.json           (두 지역 비교지표)
지표(과제 §3-1): ①용도지역 구성비(필지 대지면적%) ②주용도 구성비(연면적%) ③토지이용 혼합도(LUM 섀넌 엔트로피)
  ④개발실현도(평균 용적률=연면적/대지면적, 공지율=무건축 필지 비율)
범위·단위: 공간범위=구역계 / 공간단위=필지·건축물 / 시간=VWorld 고시·건축물대장 현행(최신) / 단년.
CRS: 면적은 EPSG:5179 계산. 한계: 용도지역 구성비는 필지 대지면적 기준(도로·공원 등 무필지 구역 제외).
"""
import json
import math
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pandas as pd

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
PROC = FE / "pangyo-cheongna-analysis" / "02_data" / "processed"
ANA = FE / "pangyo-cheongna-analysis" / "03_analysis" / "landuse"
ANA.mkdir(parents=True, exist_ok=True)


def pnu18(s: str) -> str:
    s = str(s)
    return s[:10] + s[11:]


def entropy(weights: dict) -> float:
    tot = sum(weights.values())
    if tot <= 0:
        return 0.0
    h = 0.0
    for w in weights.values():
        if w > 0:
            p = w / tot
            h -= p * math.log(p, 2)
    return h


metrics = {}
for region in ["pangyo", "cheongna"]:
    parcels = gpd.read_file(PROC / f"parcels_landuse_{region}.geojson")
    buildings = pd.DataFrame(json.loads((PROC / f"buildings_{region}.json").read_text(encoding="utf-8")))

    parcels["lot_area"] = parcels.to_crs("EPSG:5179").geometry.area
    parcels["pnu18"] = parcels["pnu"].astype(str).map(pnu18)
    buildings["pnu18"] = buildings["pnu"].astype(str).map(pnu18)
    buildings["totArea"] = pd.to_numeric(buildings["totArea"], errors="coerce").fillna(0.0)
    buildings["useAprDay"] = pd.to_numeric(buildings["useAprDay"], errors="coerce")

    # A) 건물 → 필지(18자리): 대표주용도(연면적 가중 최빈)·다양성·연면적
    rows = []
    for k, grp in buildings.groupby("pnu18"):
        w = {}
        for pu, ar in zip(grp["mainPurpsCdNm"], grp["totArea"]):
            if pu and not pd.isna(pu):
                w[pu] = w.get(pu, 0.0) + float(ar or 0)
        main = max(w, key=w.get) if w else None
        tw = sum(w.values())
        rows.append({
            "pnu18": k, "main_use": main,
            "use_breakdown": json.dumps({kk: round(vv / tw, 4) for kk, vv in w.items()}, ensure_ascii=False) if tw > 0 else "{}",
            "use_diversity": round(entropy(w), 4),
            "n_buildings": len(grp),
            "total_floor_area": round(float(grp["totArea"].sum()), 2),
            "mean_use_apr_year": int(grp["useAprDay"].dropna().mean() // 10000) if grp["useAprDay"].notna().any() else None,
        })
    pa = parcels.merge(pd.DataFrame(rows), on="pnu18", how="left")

    keep = [c for c in ["pnu", "jibun", "zoning", "zoning_year", "lot_area", "main_use",
                        "use_breakdown", "use_diversity", "n_buildings", "total_floor_area",
                        "mean_use_apr_year", "geometry"] if c in pa.columns]
    gpd.GeoDataFrame(pa[keep], geometry="geometry", crs="EPSG:4326").to_file(
        PROC / f"parcels_joined_{region}.geojson", driver="GeoJSON")

    # 지표
    zarea = pa.groupby("zoning")["lot_area"].sum()
    zoning_pct = (zarea / zarea.sum() * 100).round(2).sort_values(ascending=False)
    bu = pa.dropna(subset=["main_use"]).groupby("main_use")["total_floor_area"].sum()
    mainuse_pct = (bu / bu.sum() * 100).round(2).sort_values(ascending=False)
    lum = round(entropy(bu.to_dict()), 4)
    lum_norm = round(lum / math.log(len(bu), 2), 4) if len(bu) > 1 else 0.0

    n_parcel = len(pa)
    n_bld = int(pa["main_use"].notna().sum())
    far = round(pa["total_floor_area"].sum(skipna=True) / pa["lot_area"].sum() * 100, 2)
    vacant_cnt_pct = round((1 - n_bld / n_parcel) * 100, 2)
    vacant_area_pct = round(pa.loc[pa["main_use"].isna(), "lot_area"].sum() / pa["lot_area"].sum() * 100, 2)
    bjd = Counter(s[:10] for s in pa["pnu"].astype(str))

    metrics[region] = {
        "n_parcels": n_parcel, "n_built_parcels": n_bld,
        "lot_area_km2": round(pa["lot_area"].sum() / 1e6, 4),
        "total_floor_area_m2": round(float(pa["total_floor_area"].sum(skipna=True)), 0),
        "avg_FAR_pct": far, "vacant_parcel_pct": vacant_cnt_pct, "vacant_area_pct": vacant_area_pct,
        "LUM_entropy": lum, "LUM_normalized": lum_norm,
        "zoning_pct": zoning_pct.to_dict(),
        "mainuse_pct": mainuse_pct.head(12).to_dict(),
        "bjdong_dist": dict(bjd.most_common()),
    }
    print(f"\n===== {region} =====")
    print(f" 필지 {n_parcel} (건물있음 {n_bld}, {n_bld/n_parcel*100:.0f}%) | 대지 {pa['lot_area'].sum()/1e6:.3f}㎢ | 연면적 {pa['total_floor_area'].sum(skipna=True):,.0f}㎡")
    print(f" 평균용적률 {far}% | 공지율(필지수) {vacant_cnt_pct}% | 공지율(면적) {vacant_area_pct}%")
    print(f" LUM 엔트로피 {lum} (정규화 {lum_norm})")
    print(f" 용도지역 top5(%): {dict(list(zoning_pct.items())[:5])}")
    print(f" 주용도 top5(연면적%): {dict(list(mainuse_pct.items())[:5])}")
    print(f" 법정동 분포: {dict(bjd.most_common())}")

(ANA / "landuse_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[저장] 03_analysis/landuse/landuse_metrics.json")
