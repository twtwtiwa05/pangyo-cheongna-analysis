# -*- coding: utf-8 -*-
"""
통신사 P1 OD 흐름 v2 — 시군구 단위, 유입(in)/유출(out), 도로/지하철(거리기준), 정규화 두께.
노드에 SIGUNGU_CD/SIGUNGU_NM 내장 → PIP 불필요. hour는 in_time 추정값이라 제외(전체만; 방향만).
산출: 04_system/web/public/data/flow_telco_{region}.geojson  {dir, sgg, mode, weight, w, hour:-1}
방법: trip 종점=구역노드면 시점노드(유입), 시점=구역노드면 종점노드(유출) → 노드 SIGUNGU_CD 집계 → arc(시군구centroid↔핵심역).
  수단=trip 거리(length) 최대 transfer_type(1 도로/2 지하철). 두께=통행량/지역최대. 기준 2025-02-11.
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
node_sets = {r: pd.DataFrame({"node": [str(x) for x in nd[r]]}) for r in ["pangyo", "cheongna"]}

nodes = pyogrio.read_dataframe(GPKG, layer="nodes", columns=["NODE_ID_RAW", "SIGUNGU_CD", "SIGUNGU_NM", "X", "Y"], read_geometry=False)
trf = Transformer.from_crs(5179, 4326, always_xy=True)
lonv, latv = trf.transform(nodes.X.values, nodes.Y.values)
nodes["lon"], nodes["lat"] = lonv, latv
node_sgg = dict(zip(nodes.NODE_ID_RAW.astype(str), nodes.SIGUNGU_CD.astype(str)))
sgg_name = dict(zip(nodes.SIGUNGU_CD.astype(str), nodes.SIGUNGU_NM))
cent = nodes.groupby(nodes.SIGUNGU_CD.astype(str))[["lon", "lat"]].mean()
sgg_cent = {k: (row.lon, row.lat) for k, row in cent.iterrows()}
print(f"노드 {len(nodes):,}, 시군구 {len(sgg_cent)}", flush=True)

lst = subprocess.run(["unzip", "-l", str(ZIP)], capture_output=True).stdout.decode("utf-8", errors="ignore")
members = sorted(set(re.findall(rf"(P1_MOBILE_{DAY}_parquet_parts/P1_MOBILE_{DAY}_part_\d+\.parquet)", lst)))

agg = {"pangyo": {}, "cheongna": {}}  # (dir, sgg, mode) -> n
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
                SELECT trip_no, arg_min(f_node_id, seq) orig, arg_max(t_node_id, seq) dest,
                       sum(CASE WHEN transfer_type=1 THEN length ELSE 0 END) rd,
                       sum(CASE WHEN transfer_type=2 THEN length ELSE 0 END) sd
                FROM read_parquet('{P}') GROUP BY trip_no)
            SELECT 'in' dir, CAST(orig AS VARCHAR) nd, rd, sd FROM t WHERE CAST(dest AS VARCHAR) IN (SELECT node FROM rg)
            UNION ALL
            SELECT 'out' dir, CAST(dest AS VARCHAR) nd, rd, sd FROM t WHERE CAST(orig AS VARCHAR) IN (SELECT node FROM rg)
        """).fetchdf()
        a = agg[region]
        for r in df.itertuples(index=False):
            sgg = node_sgg.get(str(r.nd))
            if not sgg:
                continue
            mode = "subway" if (r.sd or 0) > (r.rd or 0) else "road"
            k = (r.dir, sgg, mode)
            a[k] = a.get(k, 0) + 1
    con.close()
    out.unlink()


def arc(a, b, n=20, h=0.15):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    cx, cy = mx - dy * h, my + dx * h
    return [[(1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t * t * b[1]] for t in [i / n for i in range(n + 1)]]


for region in ["pangyo", "cheongna"]:
    a = agg[region]
    hub = HUB[region]
    feats = []
    for direction in ["in", "out"]:
        items = [(k, v) for k, v in a.items() if k[0] == direction]
        sgg_tot = {}
        for (d, sgg, mode), v in items:
            sgg_tot[sgg] = sgg_tot.get(sgg, 0) + v
        top = set(sorted(sgg_tot, key=lambda s: -sgg_tot[s])[:30])
        mx = max(sgg_tot.values(), default=1)
        for (d, sgg, mode), v in items:
            if sgg not in top:
                continue
            c = sgg_cent.get(sgg)
            if not c:
                continue
            aa, bb = (c, hub) if d == "in" else (hub, c)
            feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": arc(aa, bb)},
                          "properties": {"dir": d, "sgg": sgg_name.get(sgg, sgg), "mode": mode,
                                         "weight": int(v), "w": round(min(v / mx, 1), 3), "hour": -1}})
    fc = {"type": "FeatureCollection", "name": f"flow_telco_{region}", "features": feats}
    (SYS / f"flow_telco_{region}.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"{region}: {len(feats)} features (시군구 in/out × 도로/지하철)")
