# -*- coding: utf-8 -*-
"""수도권 시군구 경계 → public/data/sgg_boundary.geojson (이동 흐름 모드 범위 표시용)."""
import sys
import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape

FE = Path(".")
sys.path.insert(0, str(FE / "songpa-landuse-analysis/python/fetch"))
import sgis_client

SYS = FE / "pangyo-cheongna-analysis/04_system/web/public/data"

rows = []
for sido in ["11", "31", "23"]:
    d = sgis_client.get("boundary/hadmarea.geojson", year="2023", adm_cd=sido, low_search=1)
    for f in d["features"]:
        rows.append({"name": f["properties"]["adm_nm"].split()[-1], "geometry": shape(f["geometry"])})
g = gpd.GeoDataFrame(rows, crs="EPSG:5179")
g["geometry"] = g.geometry.simplify(80)  # 80m 단순화(시각용 — 파일 경량화)
g = g.to_crs("EPSG:4326")
g.to_file(SYS / "sgg_boundary.geojson", driver="GeoJSON")
print(f"수도권 시군구 {len(g)} → sgg_boundary.geojson")
