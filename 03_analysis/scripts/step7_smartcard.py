# -*- coding: utf-8 -*-
"""
STEP 7-A 교통카드 OD 분석 (가점) — 판교·청라 유입·유출 통행·첨두·수단.
입력: 교통카드 링크 노드/segment/smartcard_tripchains_seoul_20241114.parquet (OD 통행사슬)
      + subway_station_mapping / bus_stop_mapping (정류장 좌표)
방법: 정류장을 구역계 polygon(district_{region}) PIP로 정밀 필터 → first/last_station ∈ 구역 통행 집계.
기준: 2024-11-14(1일). ★보조지표(기준월 통신사·지정데이터와 상이 — 보고서 출처·기준월 명기).
산출: 03_analysis/mobility/smartcard_od.json
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
ANA = FE / "pangyo-cheongna-analysis/03_analysis/mobility"
ANA.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
SUB = f"{(DIR / 'subway_station_mapping_20241114.parquet').as_posix()}"
BUS = f"{(DIR / 'bus_stop_mapping_20241114.parquet').as_posix()}"
TC = f"{(DIR / 'segment/smartcard_tripchains_seoul_20241114.parquet').as_posix()}"

print("tripchains 컬럼:", con.execute(f"DESCRIBE SELECT * FROM read_parquet('{TC}') LIMIT 0").fetchdf()["column_name"].tolist())

# 정류장 좌표 (지하철 4자리 + 버스 7자리)
sub = con.execute(f"SELECT CAST(station_id AS VARCHAR) sid, stop_lat lat, stop_lon lon FROM read_parquet('{SUB}')").fetchdf()
bus = con.execute(f"SELECT CAST(stop_id AS VARCHAR) sid, lat, lon FROM read_parquet('{BUS}') WHERE lon > 124 AND lat > 32").fetchdf()
allm = pd.concat([sub, bus], ignore_index=True)
allm_g = gpd.GeoDataFrame(allm, geometry=[Point(x, y) for x, y in zip(allm.lon, allm.lat)], crs="EPSG:4326")

res = {}
for region in ["pangyo", "cheongna"]:
    poly = gpd.read_file(PROC / f"district_{region}.geojson").to_crs("EPSG:4326").geometry.iloc[0]
    ids = set(allm_g[allm_g.within(poly)]["sid"])
    con.register(f"st_{region}", pd.DataFrame({"sid": list(ids)}))
    print(f"{region} 구역내 정류장 {len(ids)}")

for region in ["pangyo", "cheongna"]:
    inflow = con.execute(f"SELECT count(*) FROM read_parquet('{TC}') WHERE CAST(last_alighting_station AS VARCHAR) IN (SELECT sid FROM st_{region})").fetchone()[0]
    outflow = con.execute(f"SELECT count(*) FROM read_parquet('{TC}') WHERE CAST(first_boarding_station AS VARCHAR) IN (SELECT sid FROM st_{region})").fetchone()[0]
    peak = con.execute(f"SELECT hour, count(*) n FROM read_parquet('{TC}') WHERE CAST(last_alighting_station AS VARCHAR) IN (SELECT sid FROM st_{region}) GROUP BY hour ORDER BY hour").fetchdf()
    mode = con.execute(f"SELECT mode_chain, count(*) n FROM read_parquet('{TC}') WHERE CAST(last_alighting_station AS VARCHAR) IN (SELECT sid FROM st_{region}) GROUP BY mode_chain ORDER BY n DESC LIMIT 8").fetchdf()
    res[region] = {
        "inflow_trips": int(inflow), "outflow_trips": int(outflow),
        "inflow_outflow_ratio": round(inflow / outflow, 3) if outflow else None,
        "peak_hour": {int(h): int(n) for h, n in zip(peak.hour, peak.n)},
        "mode_chain_top": {str(m): int(n) for m, n in zip(mode.mode_chain, mode.n)},
    }
    print(f"\n{region}: 유입(도착) {inflow:,} / 유출(출발) {outflow:,} (유입/유출 {res[region]['inflow_outflow_ratio']})")
    ph = res[region]["peak_hour"]
    top_h = sorted(ph.items(), key=lambda x: -x[1])[:3]
    print(f"  첨두 hour top3: {top_h}")
    print(f"  수단(mode_chain): {res[region]['mode_chain_top']}")

res["_meta"] = {"base_date": "2024-11-14", "source": "교통카드 OD 통행사슬(전처리물)", "filter": "구역계 polygon PIP"}
(ANA / "smartcard_od.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[저장] smartcard_od.json")
