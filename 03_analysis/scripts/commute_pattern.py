# -*- coding: utf-8 -*-
"""
시간대별 통근 패턴 (교통카드) — 판교/청라 구역 기준 유입(도착)·유출(출발) 24시간 통행량.
"왜 판교 성공/청라 실패"의 실측 증거: 판교=아침 유입(일자리 도시), 청라=아침 유출·저녁 유입(베드타운).
입력: smartcard_tripchains_seoul + 정류장 매핑 + 구역계
산출: 04_system/web/public/data/commute_hourly.json  {region:{in:[24], out:[24], in_total, out_total, peak_in_hour, peak_out_hour}}
기준: 2024-11-14.
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

con = duckdb.connect()
SUB = (DIR / "subway_station_mapping_20241114.parquet").as_posix()
BUS = (DIR / "bus_stop_mapping_20241114.parquet").as_posix()
TC = (DIR / "segment/smartcard_tripchains_seoul_20241114.parquet").as_posix()

sub = con.execute(f"SELECT CAST(station_id AS VARCHAR) sid, stop_lat lat, stop_lon lon FROM read_parquet('{SUB}')").fetchdf()
bus = con.execute(f"SELECT CAST(stop_id AS VARCHAR) sid, lat, lon FROM read_parquet('{BUS}') WHERE lon>124 AND lat>32").fetchdf()
allm = pd.concat([sub, bus], ignore_index=True)
allm_g = gpd.GeoDataFrame(allm, geometry=[Point(x, y) for x, y in zip(allm.lon, allm.lat)], crs="EPSG:4326")

res = {}
for region in ["pangyo", "cheongna"]:
    poly = gpd.read_file(PROC / f"district_{region}.geojson").to_crs("EPSG:4326").geometry.iloc[0]
    zone = set(allm_g[allm_g.within(poly)]["sid"])
    con.register("zone", pd.DataFrame({"sid": list(zone)}))
    din = con.execute(f"SELECT hour, count(*) n FROM read_parquet('{TC}') WHERE CAST(last_alighting_station AS VARCHAR) IN (SELECT sid FROM zone) GROUP BY hour ORDER BY hour").fetchdf()
    dout = con.execute(f"SELECT hour, count(*) n FROM read_parquet('{TC}') WHERE CAST(first_boarding_station AS VARCHAR) IN (SELECT sid FROM zone) GROUP BY hour ORDER BY hour").fetchdf()
    in24, out24 = [0] * 24, [0] * 24
    for r in din.itertuples(index=False):
        if 0 <= int(r.hour) < 24:
            in24[int(r.hour)] = int(r.n)
    for r in dout.itertuples(index=False):
        if 0 <= int(r.hour) < 24:
            out24[int(r.hour)] = int(r.n)
    res[region] = {
        "in": in24, "out": out24,
        "in_total": sum(in24), "out_total": sum(out24),
        "peak_in_hour": int(max(range(24), key=lambda h: in24[h])),
        "peak_out_hour": int(max(range(24), key=lambda h: out24[h])),
    }
    print(f"{region}: 유입 {sum(in24):,}(피크 {res[region]['peak_in_hour']}시) / 유출 {sum(out24):,}(피크 {res[region]['peak_out_hour']}시)")

(SYS / "commute_hourly.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
print("[저장] commute_hourly.json")
