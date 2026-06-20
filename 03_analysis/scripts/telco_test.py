# -*- coding: utf-8 -*-
"""
통신사 P1 실현가능성 테스트 — part 1개(7GB) 추출 → DuckDB 두 지역 노드 필터 → 삭제.
§4-D 도그마: zip 전체 해제 금지. part 1개만 임시추출 → DuckDB 컬럼투영+노드 사전필터 → 즉시 삭제.
입력: 통신사 데이터.zip, _scratch/telco_region_nodes.json(판교 31023·청라 23080 NODE_ID_RAW)
대표일: 2025-02-11(화). 작동 확인되면 하루 4 part 풀처리(telco_day.py)로 확장.
"""
import subprocess
import json
import time
from pathlib import Path

import duckdb
import pandas as pd

FE = Path(".")
ZIP = FE / "DATA(통신사,교통카드)/통신사 데이터.zip"
SCRATCH = FE / "pangyo-cheongna-analysis/_scratch"
DAY = "20250211"
member = f"P1_MOBILE_{DAY}_parquet_parts/P1_MOBILE_{DAY}_part_01.parquet"
out = SCRATCH / "telco_test_part.parquet"

nd = json.load(open(SCRATCH / "telco_region_nodes.json", encoding="utf-8"))
pn_df = pd.DataFrame({"node": [str(x) for x in nd["pangyo"]]})
cn_df = pd.DataFrame({"node": [str(x) for x in nd["cheongna"]]})

t = time.time()
with open(out, "wb") as f:
    subprocess.run(["unzip", "-p", str(ZIP), member], stdout=f, check=True)
print(f"추출 {time.time()-t:.0f}s, {out.stat().st_size/1e9:.1f}GB", flush=True)

con = duckdb.connect()
con.register("pn", pn_df)
con.register("cn", cn_df)
P = out.as_posix()
n = con.execute(f"SELECT count(*) FROM read_parquet('{P}')").fetchone()[0]
cols = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{P}') LIMIT 0").fetchdf()
print(f"part_01 행수 {n:,}")
print(f"컬럼: {list(cols['column_name'])}")

for label, tbl in [("판교", "pn"), ("청라", "cn")]:
    r = con.execute(f"""
        SELECT count(*) legs, count(distinct trip_no) trips
        FROM read_parquet('{P}')
        WHERE CAST(f_node_id AS VARCHAR) IN (SELECT node FROM {tbl})
           OR CAST(t_node_id AS VARCHAR) IN (SELECT node FROM {tbl})
    """).fetchone()
    print(f"  {label} part_01: leg {r[0]:,}, 통행(trip) {r[1]:,}")

out.unlink()
print("삭제 완료. 실현가능 → 하루 4 part 풀처리로 확장.")
