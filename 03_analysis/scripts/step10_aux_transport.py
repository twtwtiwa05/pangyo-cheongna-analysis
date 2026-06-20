# -*- coding: utf-8 -*-
"""
교통망 보조지표 — 역세권 면적비(500m/1km) + 버스 정류장 밀도(개/㎢). (도로망 밀도는 road_metrics.json 별도)
입력(읽기전용):
  subway_network/network/nodes.tsv                                   지하철 역 좌표(기준일 active 필터)
  DATA(통신사,교통카드)/교통카드 링크 노드/bus_stop_mapping_20241114.parquet  버스 정류장 좌표
  02_data/processed/district_{region}.geojson                        구역계
산출: 03_analysis/transport/aux_transport.json
정의:
  역세권 면적비 = (구역 ∩ {임의 지하철역 r m 버퍼 union}) 면적 / 구역 면적.  r=500, 1000.
  버스 밀도     = 구역계 내 버스정류장 수 / 구역 면적(㎢).
범위·단위(§5-A): 공간범위=판교 삼평동·청라1~3동 구역계 / 공간단위=구역 / CRS 계산 EPSG:5179.
기준: 지하철망 2026-06-20 운영본 active / 버스정류장 2024-11-14. 재현성: 결정론적(난수 없음).
"""
import json
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
NET = FE / "subway_network" / "network"
PROJ = FE / "pangyo-cheongna-analysis"
PROC = PROJ / "02_data" / "processed"
OUT = PROJ / "03_analysis" / "transport"
BUS = (FE / "DATA(통신사,교통카드)/교통카드 링크 노드/bus_stop_mapping_20241114.parquet").as_posix()
T = "2026-06-20"

# ---- 지하철 역 (기준일 active) — 노선별 플랫폼 노드 포함, 버퍼 union으로 중복 흡수 ----
nodes = pd.read_csv(NET / "nodes.tsv", sep="\t", dtype={"begin": str, "effective_begin": str})
eb = nodes["effective_begin"].fillna("").astype(str)
node_eff = eb.where(eb.str.len() > 0, nodes["begin"])
sta = nodes[node_eff <= T].copy()
sta_g = gpd.GeoDataFrame(sta, geometry=[Point(x, y) for x, y in zip(sta.x_5179, sta.y_5179)], crs="EPSG:5179")

# ---- 버스 정류장 (좌표 유효치만) ----
con = duckdb.connect()
bus = con.execute(f"SELECT lat, lon FROM read_parquet('{BUS}') WHERE lon>124 AND lat>32").fetchdf()
bus_g = gpd.GeoDataFrame(bus, geometry=[Point(x, y) for x, y in zip(bus.lon, bus.lat)], crs="EPSG:4326").to_crs("EPSG:5179")

res = {}
for region in ["pangyo", "cheongna"]:
    dist = gpd.read_file(PROC / f"district_{region}.geojson").to_crs("EPSG:5179")
    poly = unary_union(dist.geometry.values)
    area_km2 = poly.area / 1e6

    # 역세권 면적비: 구역 인근(1.2km 이내) 역만 버퍼 → union → 구역 교차
    near = sta_g[sta_g.distance(poly) <= 1200]
    catch = {}
    for r in (500, 1000):
        if len(near):
            buf = unary_union([g.buffer(r) for g in near.geometry])
            inter = poly.intersection(buf)
            catch[f"{r}m"] = {"area_km2": round(inter.area / 1e6, 4), "ratio_pct": round(inter.area / poly.area * 100, 2)}
        else:
            catch[f"{r}m"] = {"area_km2": 0.0, "ratio_pct": 0.0}

    # 버스 밀도: 구역계 내 정류장 수 ÷ 면적
    nbus = int(bus_g.within(poly).sum())
    res[region] = {
        "area_km2": round(area_km2, 4),
        "subway_catchment": catch,
        "n_subway_stations_near": int(len(near)),
        "bus_stops_in_zone": nbus,
        "bus_density_per_km2": round(nbus / area_km2, 2),
    }
    print(f"{region}: 역세권 500m {catch['500m']['ratio_pct']}% / 1km {catch['1000m']['ratio_pct']}% "
          f"· 버스 {nbus}개 {res[region]['bus_density_per_km2']}/㎢ · 인근역 {len(near)} (면적 {area_km2:.2f}㎢)")

out = {
    "source": {"subway": "제공 subway_network nodes (active 2026-06-20)",
               "bus": "교통카드 bus_stop_mapping 2024-11-14",
               "district": "행정동 구역계 EPSG:5179"},
    "definitions": {
        "subway_catchment_ratio": "구역 ∩ (임의 지하철역 r m 버퍼 union) 면적 / 구역 면적",
        "bus_density": "구역 내 버스정류장 수 / 구역 면적(㎢)"},
    "crs_metric": "EPSG:5179", "base": {"subway": T, "bus": "2024-11-14"},
    "regions": res,
}
(OUT / "aux_transport.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("[저장] aux_transport.json")
