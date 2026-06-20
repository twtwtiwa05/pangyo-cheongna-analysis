# -*- coding: utf-8 -*-
"""
교통카드 OD 흐름 시각화 데이터 — 판교/청라 '도착(유입)' 통행의 출발지 → 핵심역 arc.
입력: segment/smartcard_tripchains_seoul + subway/bus 정류장 매핑
산출: 04_system/web/public/data/flow_{region}.geojson (LineString 출발그리드→핵심역; weight=통행량, mode=수단)
방법: 도착역(구역 내) 통행의 first_boarding 좌표 → 0.03° 그리드 집계 → 상위 35 → 핵심역으로 베지어 arc.
기준: 2024-11-14. 보조 시각화(가점 이동데이터).
"""
import json
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

FE = Path(".")
DIR = FE / "DATA(통신사,교통카드)/교통카드 링크 노드"
PROC = FE / "pangyo-cheongna-analysis/02_data/processed"
SYS = FE / "pangyo-cheongna-analysis/04_system/web/public/data"
HUB = {"pangyo": (127.1112, 37.3956), "cheongna": (126.638, 37.535)}

con = duckdb.connect()
SUB = (DIR / "subway_station_mapping_20241114.parquet").as_posix()
BUS = (DIR / "bus_stop_mapping_20241114.parquet").as_posix()
TC = (DIR / "segment/smartcard_tripchains_seoul_20241114.parquet").as_posix()

sub = con.execute(f"SELECT CAST(station_id AS VARCHAR) sid, stop_lat lat, stop_lon lon FROM read_parquet('{SUB}')").fetchdf()
bus = con.execute(f"SELECT CAST(stop_id AS VARCHAR) sid, lat, lon FROM read_parquet('{BUS}') WHERE lon>124 AND lat>32").fetchdf()
allm = pd.concat([sub, bus], ignore_index=True)
allm_g = gpd.GeoDataFrame(allm, geometry=[Point(x, y) for x, y in zip(allm.lon, allm.lat)], crs="EPSG:4326")
coord = {r.sid: (r.lon, r.lat) for r in allm.itertuples()}


def arc(a, b, n=22, h=0.16):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    cx, cy = mx - dy * h, my + dx * h
    return [[(1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t * t * b[1]] for t in [i / n for i in range(n + 1)]]


for region in ["pangyo", "cheongna"]:
    poly = gpd.read_file(PROC / f"district_{region}.geojson").to_crs("EPSG:4326").geometry.iloc[0]
    arrive = set(allm_g[allm_g.within(poly)]["sid"])
    con.register("arr", pd.DataFrame({"sid": list(arrive)}))
    df = con.execute(f"""
        SELECT CAST(first_boarding_station AS VARCHAR) fb,
               sum(CASE WHEN is_subway_only THEN 1 ELSE 0 END) sub_n,
               sum(CASE WHEN is_bus_only THEN 1 ELSE 0 END) bus_n,
               count(*) n
        FROM read_parquet('{TC}')
        WHERE CAST(last_alighting_station AS VARCHAR) IN (SELECT sid FROM arr)
          AND first_boarding_station IS NOT NULL
        GROUP BY fb
    """).fetchdf()
    df["lon"] = df.fb.map(lambda s: coord.get(s, (None, None))[0])
    df["lat"] = df.fb.map(lambda s: coord.get(s, (None, None))[1])
    df = df.dropna(subset=["lon", "lat"])
    df["gx"] = (df.lon / 0.03).round() * 0.03
    df["gy"] = (df.lat / 0.03).round() * 0.03
    g = df.groupby(["gx", "gy"]).agg(n=("n", "sum"), sub_n=("sub_n", "sum"), bus_n=("bus_n", "sum")).reset_index()
    g = g.sort_values("n", ascending=False).head(35)
    hub = HUB[region]
    feats = []
    for r in g.itertuples():
        mode = "subway" if r.sub_n > r.bus_n else "bus"
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": arc((r.gx, r.gy), hub)},
                      "properties": {"weight": int(r.n), "mode": mode, "sub_n": int(r.sub_n), "bus_n": int(r.bus_n)}})
    fc = {"type": "FeatureCollection", "name": f"flow_{region}", "features": feats}
    (SYS / f"flow_{region}.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"{region}: OD 출발지 {len(g)}개 arc, 총 도착통행 {int(g.n.sum()):,} (지하철주 {int((g.sub_n>g.bus_n).sum())}/버스주 {int((g.bus_n>=g.sub_n).sum())})")
