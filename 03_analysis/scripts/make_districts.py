# -*- coding: utf-8 -*-
"""
구역계 정의·면적 산출 — 판교(삼평동)·청라(청라1~3동).

입력: 02_data/processed/emdong_{pangyo,cheongna}.geojson (SGIS 행정동 경계, EPSG:4326)
산출: 02_data/processed/district_{pangyo,cheongna}.geojson (구역계 폴리곤 + area_km2 + 포함 행정동)
면적: EPSG:5179(UTM-K, m)에서 계산 → ㎢. 과제 §2 '구역계 직접 정의·출처·면적 명시' 충족.
구역계 정의: 행정동 경계 기준(SGIS). 한계 — 삼평동은 판교테크노밸리 + 인근 주거 일부 포함(STEP 4에서 용도지역으로 업무지구 정밀 클립 가능).
"""
import geopandas as gpd
from pathlib import Path

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
PROC = FE / "pangyo-cheongna-analysis" / "02_data" / "processed"

SEL = {
    "pangyo":   ("emdong_pangyo.geojson",   ["삼평동"]),
    "cheongna": ("emdong_cheongna.geojson", ["청라1동", "청라2동", "청라3동"]),
}

for key, (fn, dongs) in SEL.items():
    em = gpd.read_file(PROC / fn)
    nmcol = "adm_nm" if "adm_nm" in em.columns else em.columns[0]
    sel = em[em[nmcol].apply(lambda s: any(str(s).endswith(d) or d in str(s) for d in dongs))]
    print(f"{key}: 후보 행정동 {list(em[nmcol])[:3]}... → 선택 {list(sel[nmcol])} ({len(sel)}개)")
    if len(sel) == 0:
        print(f"  !! {key} 행정동 매칭 실패 — adm_nm 값 확인 필요")
        continue
    area_km2 = float(sel.to_crs("EPSG:5179").geometry.area.sum() / 1e6)
    diss = sel.dissolve().to_crs("EPSG:4326")
    diss["district"] = key
    diss["area_km2"] = round(area_km2, 4)
    diss["dongs"] = ", ".join(str(x) for x in sel[nmcol])
    diss = diss[["district", "area_km2", "dongs", "geometry"]]
    diss.to_file(PROC / f"district_{key}.geojson", driver="GeoJSON")
    print(f"  → district_{key}.geojson  면적 {area_km2:.4f} ㎢")
