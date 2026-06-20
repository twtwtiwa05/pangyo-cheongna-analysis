# -*- coding: utf-8 -*-
"""
교통카드 OD 흐름 v2 — 시군구 단위 / 유입(in)·유출(out) / 시간대(hour) / 지하철·버스(has_subway) / 정규화 두께.
입력: segment/smartcard_tripchains_seoul + 정류장 매핑 + SGIS 수도권 시군구 경계
산출: 04_system/web/public/data/flow_{region}.geojson
  feature.properties: dir(in/out), sgg(시군구명), hour(-1=전체|0~23), mode(subway/bus), weight, w(0~1 정규화)
방법: 도착(또는 출발)역이 구역 내인 통행의 상대 station → 시군구 PIP → (시군구,hour,mode) 통행량 집계 → arc(시군구centroid↔핵심역).
  수단=has_subway(지하철 이용 여부, 환승통행 포함). 두께 w=통행량/지역최대(전체기준). 기준 2024-11-14.
"""
import sys
import json
from pathlib import Path

import duckdb
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, shape

FE = Path(".")
sys.path.insert(0, str(FE / "songpa-landuse-analysis/python/fetch"))
import sgis_client

DIR = FE / "DATA(통신사,교통카드)/교통카드 링크 노드"
PROC = FE / "pangyo-cheongna-analysis/02_data/processed"
SYS = FE / "pangyo-cheongna-analysis/04_system/web/public/data"
HUB = {"pangyo": (127.1112, 37.3956), "cheongna": (126.638, 37.535)}

con = duckdb.connect()
SUB = (DIR / "subway_station_mapping_20241114.parquet").as_posix()
BUS = (DIR / "bus_stop_mapping_20241114.parquet").as_posix()
TC = (DIR / "segment/smartcard_tripchains_seoul_20241114.parquet").as_posix()

# 1) 수도권 시군구 경계 + 4326 centroid
rows = []
for sido in ["11", "31", "23"]:
    d = sgis_client.get("boundary/hadmarea.geojson", year="2023", adm_cd=sido, low_search=1)
    for f in d["features"]:
        rows.append({"sgg": f["properties"]["adm_cd"], "name": f["properties"]["adm_nm"].split()[-1], "geometry": shape(f["geometry"])})
sgg = gpd.GeoDataFrame(rows, crs="EPSG:5179")
sgg4 = sgg.to_crs("EPSG:4326")
cent = gpd.GeoSeries(sgg.geometry.centroid, crs="EPSG:5179").to_crs("EPSG:4326")
sgg["clon"], sgg["clat"] = cent.x.values, cent.y.values
sgg_name = dict(zip(sgg["sgg"], sgg["name"]))
sgg_cent = dict(zip(sgg["sgg"], zip(sgg["clon"], sgg["clat"])))

# 2) station 좌표 → 시군구 PIP
sub = con.execute(f"SELECT CAST(station_id AS VARCHAR) sid, stop_lat lat, stop_lon lon FROM read_parquet('{SUB}')").fetchdf()
bus = con.execute(f"SELECT CAST(stop_id AS VARCHAR) sid, lat, lon FROM read_parquet('{BUS}') WHERE lon>124 AND lat>32").fetchdf()
allm = pd.concat([sub, bus], ignore_index=True)
allm_g = gpd.GeoDataFrame(allm, geometry=[Point(x, y) for x, y in zip(allm.lon, allm.lat)], crs="EPSG:4326")
sj = gpd.sjoin(allm_g, sgg4[["sgg", "geometry"]], how="left", predicate="within").drop_duplicates("sid")
station_sgg = dict(zip(sj.sid.astype(str), sj.sgg))


def arc(a, b, n=20, h=0.15):
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    cx, cy = mx - dy * h, my + dx * h
    return [[(1 - t) ** 2 * a[0] + 2 * (1 - t) * t * cx + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * cy + t * t * b[1]] for t in [i / n for i in range(n + 1)]]


for region in ["pangyo", "cheongna"]:
    poly = gpd.read_file(PROC / f"district_{region}.geojson").to_crs("EPSG:4326").geometry.iloc[0]
    zone = set(allm_g[allm_g.within(poly)]["sid"])
    con.register("zone", pd.DataFrame({"sid": list(zone)}))
    hub = HUB[region]
    feats = []
    for direction, anchor, other in [("in", "last_alighting_station", "first_boarding_station"),
                                      ("out", "first_boarding_station", "last_alighting_station")]:
        df = con.execute(f"""
            SELECT CAST({other} AS VARCHAR) st, hour, has_subway, count(*) n
            FROM read_parquet('{TC}')
            WHERE CAST({anchor} AS VARCHAR) IN (SELECT sid FROM zone) AND {other} IS NOT NULL
            GROUP BY st, hour, has_subway
        """).fetchdf()
        df["sgg"] = df.st.map(station_sgg)
        df = df.dropna(subset=["sgg"])
        df["mode"] = df.has_subway.map(lambda b: "subway" if b else "bus")
        g = df.groupby(["sgg", "hour", "mode"], as_index=False).n.sum()
        gall = df.groupby(["sgg", "mode"], as_index=False).n.sum()
        gall["hour"] = -1
        allrows = pd.concat([g, gall], ignore_index=True)
        top = df.groupby("sgg").n.sum().sort_values(ascending=False).head(30).index
        allrows = allrows[allrows.sgg.isin(top)]
        mx = allrows[allrows.hour == -1].n.max() or 1
        for r in allrows.itertuples(index=False):
            c = sgg_cent.get(r.sgg)
            if not c:
                continue
            a, b = (c, hub) if direction == "in" else (hub, c)
            feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": arc(a, b)},
                          "properties": {"dir": direction, "sgg": sgg_name.get(r.sgg, r.sgg), "hour": int(r.hour),
                                         "mode": r.mode, "weight": int(r.n), "w": round(min(r.n / mx, 1), 3)}})
    fc = {"type": "FeatureCollection", "name": f"flow_{region}", "features": feats}
    (SYS / f"flow_{region}.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    nin = sum(1 for f in feats if f["properties"]["dir"] == "in" and f["properties"]["hour"] == -1)
    print(f"{region}: {len(feats)} features | 전체 유입 시군구 {nin} | 지하철feat {sum(1 for f in feats if f['properties']['mode']=='subway' and f['properties']['hour']==-1)}")
