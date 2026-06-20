# -*- coding: utf-8 -*-
"""
판교·청라 핵심역 지하철 등시간권 — 1차 도달성 산출 (STEP 5 선행)

입력(읽기전용): {FE}/subway_network/network/{nodes,links}.tsv  (제공 데이터)
기준일  T = 2026-06-20  → active 노드/링크만 사용(미래 GTX-B/C·신안산선 등 제외; 미지정 시 도달성 과대)
출발점  판교 = 신분당선 id 824 + 경강선 id 26 (환승역 다중노드 → elementwise min)
        청라 = 청라국제도시(공항철도) id 313
시간    링크 timeFT/timeTF (초). 환승 대기시간은 transfer 링크에 이미 선반영(line_waits).

산출:
  02_data/processed/isochrone_nodes_pangyo.geojson     도달역 점 + reach_min (≤60분)
  02_data/processed/isochrone_nodes_cheongna.geojson
  03_analysis/transport/access_curve.csv               1~90분 누적 도달역 수(판교/청라)
  03_analysis/transport/isochrone_summary.json         30/60분 도달역수 + 주요역 소요시간

범위·단위(보고서 §5-A): 시간범위=네트워크 2026-06-20 운영본 / 공간범위=수도권 지하철망 /
  공간단위=역(노드) / 시간단위=분(누적접근성곡선).
한계: 본 단계는 '역 기준' 도달성. '도달 인구·종사자'는 SGIS 집계구 결합(STEP 3 수집 후) 추가.
      보행망 미포함 → 역→필지 도보접근은 STEP 5 본작업에서 보행버퍼로 보정.
재현성: 결정론적(난수 없음). 입력경로·기준일 위 헤더에 고정.
"""
import json
import csv
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
NET = FE / "subway_network" / "network"
PROJ = FE / "pangyo-cheongna-analysis"
OUT_GEO = PROJ / "02_data" / "processed"
OUT_ANA = PROJ / "03_analysis" / "transport"
OUT_GEO.mkdir(parents=True, exist_ok=True)
OUT_ANA.mkdir(parents=True, exist_ok=True)

T = "2026-06-20"
SOURCES = {"pangyo": [824, 26], "cheongna": [313]}

# ---- load (제공 tsv, 읽기전용) ----
nodes = pd.read_csv(NET / "nodes.tsv", sep="\t",
                    dtype={"begin": str, "effective_begin": str})
links = pd.read_csv(NET / "links.tsv", sep="\t", dtype={"begin": str})
assert (nodes["id"].to_numpy() == np.arange(len(nodes))).all(), "id가 행 index와 불일치"

# ---- 기준일 active 필터 ----
eb = nodes["effective_begin"].fillna("").astype(str)
node_eff = eb.where(eb.str.len() > 0, nodes["begin"])
active = set(nodes.loc[node_eff <= T, "id"].tolist())
L = links[(links["begin"] <= T)
          & links["fromNode"].isin(active)
          & links["toNode"].isin(active)]

# ---- 양방향 directed CSR (timeFT/timeTF를 두 행으로 펼침) ----
V = len(nodes)
u, v = L["fromNode"].to_numpy(), L["toNode"].to_numpy()
src = np.concatenate([u, v])
dst = np.concatenate([v, u])
cost = np.concatenate([L["timeFT"].to_numpy(), L["timeTF"].to_numpy()]).astype(np.float64)
A = csr_matrix((cost, (src, dst)), shape=(V, V))


def reach_seconds(ids):
    sol = dijkstra(A, indices=ids)
    if sol.ndim > 1:
        sol = sol.min(axis=0)
    return sol  # 초, 미도달은 inf


results = {}
for name, ids in SOURCES.items():
    sol = reach_seconds(ids)
    results[name] = sol
    feats = []
    for i in range(V):
        s = sol[i]
        if (i not in active) or (not np.isfinite(s)) or s > 3600:
            continue
        r = nodes.iloc[i]
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r.lng), float(r.lat)]},
            "properties": {
                "node_id": int(r.id), "statnm": r.statnm, "linenm": r.linenm,
                "reach_sec": round(float(s), 1), "reach_min": round(float(s) / 60, 1),
                "band": "30min" if s <= 1800 else "60min",
            },
        })
    fc = {
        "type": "FeatureCollection", "name": f"isochrone_nodes_{name}",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {"origin_node_ids": ids, "base_date": T,
                     "unit": "subway travel minutes (walk excluded)"},
        "features": feats,
    }
    (OUT_GEO / f"isochrone_nodes_{name}.geojson").write_text(
        json.dumps(fc, ensure_ascii=False), encoding="utf-8")

# ---- 누적 접근성 곡선 (1~90분, 역 기준) ----
with open(OUT_ANA / "access_curve.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["minute", "pangyo_reachable_stations", "cheongna_reachable_stations"])
    for t in range(1, 91):
        sec = t * 60
        pg = int(((results["pangyo"] > 0) & (results["pangyo"] <= sec)).sum())
        cn = int(((results["cheongna"] > 0) & (results["cheongna"] <= sec)).sum())
        w.writerow([t, pg, cn])


def t_to(name, statnm):
    """name 출발 → statnm(임의 노선) 최단 도달분."""
    sol = results[name]
    ids = nodes.loc[nodes["statnm"] == statnm, "id"].tolist()
    vals = [sol[i] for i in ids if np.isfinite(sol[i])]
    return round(min(vals) / 60, 1) if vals else None


def band_counts(name):
    sol = results[name]
    return {"n30": int(((sol > 0) & (sol <= 1800)).sum()),
            "n60": int(((sol > 0) & (sol <= 3600)).sum())}


dest = ["강남", "서울", "여의도", "삼성", "광화문", "시청", "판교", "청라국제도시", "인천공항1터미널"]
summary = {
    "base_date": T, "sources": SOURCES,
    "active_nodes": len(active), "total_nodes": V, "links_used": int(len(L)),
    "pangyo": band_counts("pangyo"), "cheongna": band_counts("cheongna"),
    "key_dest_minutes": {
        d: {"pangyo": t_to("pangyo", d), "cheongna": t_to("cheongna", d)} for d in dest
    },
}
(OUT_ANA / "isochrone_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(summary, ensure_ascii=False, indent=2))

# ---- 등시간권 폴리곤 (도달역 보행버퍼 union) ----
# 근사: 각 도달역에서 잔여시간(threshold-도착초)만큼 직선 도보(4km/h=1.11m/s) 반경 버퍼 → union.
# 한계: 보행망 미반영 직선근사. EPSG:5179(m)에서 버퍼·union 후 4326 저장.
WALK_MS = 1.11
xs = nodes["x_5179"].to_numpy()
ys = nodes["y_5179"].to_numpy()
for name, ids in SOURCES.items():
    sol = results[name]
    for thr_min in (30, 60):
        thr = thr_min * 60
        buffs = []
        for i in range(V):
            s = sol[i]
            if (i not in active) or (not np.isfinite(s)) or s > thr:
                continue
            r = WALK_MS * (thr - s)
            if r > 0:
                buffs.append(Point(xs[i], ys[i]).buffer(r))
        if not buffs:
            continue
        poly = unary_union(buffs)
        gdf = gpd.GeoDataFrame(
            {"region": [name], "band_min": [thr_min], "area_km2": [round(poly.area / 1e6, 3)],
             "n_stations": [len(buffs)], "base_date": [T], "note": ["walk 4km/h buffer, walk-network excluded"]},
            geometry=[poly], crs="EPSG:5179").to_crs("EPSG:4326")
        gdf.to_file(OUT_GEO / f"isochrone_{name}_{thr_min}min.geojson", driver="GeoJSON")
        print(f"  폴리곤 {name} {thr_min}min: 면적 {poly.area / 1e6:.1f} ㎢, 도달역 {len(buffs)}")
