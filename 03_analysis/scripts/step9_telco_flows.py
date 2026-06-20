# -*- coding: utf-8 -*-
"""
통신사 P1 OD 흐름 시각화 데이터 — 판교/청라 '도착(종점)' 통행의 시점 → 핵심역 arc.
입력: 통신사 데이터.zip(하루 4 part) + 통합망 gpkg(노드 좌표) + _scratch/telco_region_nodes.json
산출: 04_system/web/public/data/flow_telco_{region}.geojson (LineString 시점격자→핵심역; weight, mode=도로/지하철)
방법: trip 종점(arg_max t_node by seq)이 구역노드면, 시점(arg_min f_node by seq) 노드 좌표 → 0.04° 격자 집계 → 상위 35 arc.
  수단은 trip의 거리(length) 최대 transfer_type(1 도로/2 지하철). 전체 통행(승용차 포함)이라 도로 우세.
기준: 2025-02-11. 보조 시각화. part 1개씩 추출→집계→삭제(§4-D).
"""
import subprocess
import json
import re
import time
from pathlib import Path

import duckdb
import pyogrio
import pandas as pd
from pyproj import Transformer

FE = Path(".")
ZIP = FE / "DATA(통신사,교통카드)/통신사 데이터.zip"
GPKG = (FE / "DATA(통신사,교통카드)/통신사 데이터 네트워크/integrated_network_202603_ver1.gpkg").as_posix()
SCRATCH = FE / "pangyo-cheongna-analysis/_scratch"
SYS = FE / "pangyo-cheongna-analysis/04_system/web/public/data"
DAY = "20250211"
HUB = {"pangyo": (127.1112, 37.3956), "cheongna": (126.638, 37.535)}

nd = json.load(open(SCRATCH / "telco_region_nodes.json", encoding="utf-8"))
node_sets = {"pangyo": pd.DataFrame({"node": [str(x) for x in nd["pangyo"]]}),
             "cheongna": pd.DataFrame({"node": [str(x) for x in nd["cheongna"]]})}

# 노드 좌표 (NODE_ID_RAW → lon/lat, 5179→4326)
nodes = pyogrio.read_dataframe(GPKG, layer="nodes", columns=["NODE_ID_RAW", "X", "Y"], read_geometry=False)
trf = Transformer.from_crs(5179, 4326, always_xy=True)
lon, lat = trf.transform(nodes.X.values, nodes.Y.values)
ncoord = dict(zip(nodes.NODE_ID_RAW.astype(str), zip(lon, lat)))
print(f"노드좌표 {len(ncoord):,}", flush=True)

lst = subprocess.run(["unzip", "-l", str(ZIP)], capture_output=True).stdout.decode("utf-8", errors="ignore")
members = sorted(set(re.findall(rf"(P1_MOBILE_{DAY}_parquet_parts/P1_MOBILE_{DAY}_part_\d+\.parquet)", lst)))

agg = {"pangyo": {}, "cheongna": {}}  # (gx,gy) -> [n, road_d, sub_d]
for m in members:
    out = SCRATCH / "telco_flow_part.parquet"
    t = time.time()
    with open(out, "wb") as f:
        subprocess.run(["unzip", "-p", str(ZIP), m], stdout=f, check=True)
    print(f"  {m.split('/')[-1]} 추출 {time.time()-t:.0f}s", flush=True)
    con = duckdb.connect()
    P = out.as_posix()
    for region in ["pangyo", "cheongna"]:
        con.register("rg", node_sets[region])
        df = con.execute(f"""
            WITH t AS (
                SELECT trip_no,
                       arg_min(f_node_id, seq) orig,
                       arg_max(t_node_id, seq) dest,
                       sum(CASE WHEN transfer_type=1 THEN length ELSE 0 END) road_d,
                       sum(CASE WHEN transfer_type=2 THEN length ELSE 0 END) sub_d
                FROM read_parquet('{P}') GROUP BY trip_no)
            SELECT orig, road_d, sub_d FROM t
            WHERE CAST(dest AS VARCHAR) IN (SELECT node FROM rg)
        """).fetchdf()
        a = agg[region]
        for r in df.itertuples(index=False):
            xy = ncoord.get(str(r.orig))
            if not xy:
                continue
            gx, gy = round(xy[0] / 0.04) * 0.04, round(xy[1] / 0.04) * 0.04
            cell = a.setdefault((gx, gy), [0, 0.0, 0.0])
            cell[0] += 1
            cell[1] += float(r.road_d or 0)
            cell[2] += float(r.sub_d or 0)
    con.close()
    out.unlink()


def arc(a, b, n=22, h=0.16):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    cx, cy = mx - dy * h, my + dx * h
    return [[(1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t * t * b[1]] for t in [i / n for i in range(n + 1)]]


for region in ["pangyo", "cheongna"]:
    cells = sorted(agg[region].items(), key=lambda kv: -kv[1][0])[:35]
    hub = HUB[region]
    feats = []
    for (gx, gy), (n, road, sub) in cells:
        if (gx, gy) == hub:
            continue
        mode = "subway" if sub > road else "road"
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": arc((gx, gy), hub)},
                      "properties": {"weight": int(n), "mode": mode}})
    fc = {"type": "FeatureCollection", "name": f"flow_telco_{region}", "features": feats}
    (SYS / f"flow_telco_{region}.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    tot = sum(v[0] for v in agg[region].values())
    print(f"{region}: 시점격자 {len(cells)}개 arc, 총 도착통행 {tot:,}")
