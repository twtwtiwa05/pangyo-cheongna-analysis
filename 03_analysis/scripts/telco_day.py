# -*- coding: utf-8 -*-
"""
STEP 7-B 통신사 P1 경로통행 — 판교·청라 하루(2025-02-11 화) 수단분담·시간대·기종점.

★수정(2026-06-20): 기존 leg(링크) 단위 집계는 도로 링크 수가 압도적으로 많아 분담을 왜곡했음
  (도로 98% = '도로 링크 비율'일 뿐, 실제 수단분담 아님). → 통행(trip) 단위 + 거리(length) 가중으로 재산출.
  transfer_type: 1 도로(승용차·버스·택시 등 도로통행) / 2 지하철 / 3 철도 / 4 공항 / 5 환승 / 6 기타.

방법(§4-D 도그마): part 1개씩 임시추출 → 관련 trip(구역 노드 31023/23080 경유) → trip별 수단 포함·수단별 거리 집계
  → part 간 trip 병합(걸친 통행 합산) → 즉시 삭제.
지표: 통행수 / 지하철·철도 이용 통행% / 거리 분담% / 주수단(최장거리) 통행% / 첨두(통행 출발시각).
한계: P1은 휴대폰 통행의 통합망 맵매칭 — 지하철 구간이 도로로 맵매칭될 수 있어 철도 분담이 과소될 가능성(보조지표).
"""
import subprocess
import json
import re
import time
from pathlib import Path

import duckdb

FE = Path(".")
ZIP = FE / "DATA(통신사,교통카드)/통신사 데이터.zip"
SCRATCH = FE / "pangyo-cheongna-analysis/_scratch"
ANA = FE / "pangyo-cheongna-analysis/03_analysis/mobility"
ANA.mkdir(parents=True, exist_ok=True)
DAY = "20250211"

nd = json.load(open(SCRATCH / "telco_region_nodes.json", encoding="utf-8"))
import pandas as pd
pn_df = pd.DataFrame({"node": [str(x) for x in nd["pangyo"]]})
cn_df = pd.DataFrame({"node": [str(x) for x in nd["cheongna"]]})

lst = subprocess.run(["unzip", "-l", str(ZIP)], capture_output=True).stdout.decode("utf-8", errors="ignore")
members = sorted(set(re.findall(rf"(P1_MOBILE_{DAY}_parquet_parts/P1_MOBILE_{DAY}_part_\d+\.parquet)", lst)))
print(f"{DAY} part {len(members)}개", flush=True)

# trip_no -> {sub,rail,rd,sd,rrd,sh}  (part 간 병합)
db = {"pangyo": {}, "cheongna": {}}
for m in members:
    out = SCRATCH / "telco_day_part.parquet"
    t = time.time()
    with open(out, "wb") as f:
        subprocess.run(["unzip", "-p", str(ZIP), m], stdout=f, check=True)
    print(f"  {m.split('/')[-1]} 추출 {time.time()-t:.0f}s", flush=True)
    con = duckdb.connect()
    con.register("pn", pn_df)
    con.register("cn", cn_df)
    P = out.as_posix()
    for region, tbl in [("pangyo", "pn"), ("cheongna", "cn")]:
        df = con.execute(f"""
            WITH rel AS (
                SELECT DISTINCT trip_no FROM read_parquet('{P}')
                WHERE CAST(f_node_id AS VARCHAR) IN (SELECT node FROM {tbl})
                   OR CAST(t_node_id AS VARCHAR) IN (SELECT node FROM {tbl}))
            SELECT trip_no,
                bool_or(transfer_type = 2) has_sub,
                bool_or(transfer_type = 3) has_rail,
                sum(CASE WHEN transfer_type = 1 THEN length ELSE 0 END) rd,
                sum(CASE WHEN transfer_type = 2 THEN length ELSE 0 END) sd,
                sum(CASE WHEN transfer_type = 3 THEN length ELSE 0 END) rrd,
                hour(min(in_time)) sh
            FROM read_parquet('{P}') WHERE trip_no IN (SELECT trip_no FROM rel)
            GROUP BY trip_no
        """).fetchdf()
        d = db[region]
        for r in df.itertuples(index=False):
            t0 = d.setdefault(r.trip_no, {"sub": False, "rail": False, "rd": 0.0, "sd": 0.0, "rrd": 0.0, "sh": None})
            t0["sub"] |= bool(r.has_sub)
            t0["rail"] |= bool(r.has_rail)
            t0["rd"] += float(r.rd or 0)
            t0["sd"] += float(r.sd or 0)
            t0["rrd"] += float(r.rrd or 0)
            if r.sh is not None and not pd.isna(r.sh):
                t0["sh"] = int(r.sh) if t0["sh"] is None else min(t0["sh"], int(r.sh))
    con.close()
    out.unlink()

res = {}
for region in ["pangyo", "cheongna"]:
    d = db[region]
    n = len(d) or 1
    sub = sum(1 for t in d.values() if t["sub"])
    rail = sum(1 for t in d.values() if t["rail"])
    RD = sum(t["rd"] for t in d.values())
    SD = sum(t["sd"] for t in d.values())
    RRD = sum(t["rrd"] for t in d.values())
    totd = (RD + SD + RRD) or 1
    main = {"도로": 0, "지하철": 0, "철도": 0}
    hours = {}
    for t in d.values():
        cand = [("도로", t["rd"]), ("지하철", t["sd"]), ("철도", t["rrd"])]
        main[max(cand, key=lambda x: x[1])[0]] += 1
        if t["sh"] is not None:
            hours[t["sh"]] = hours.get(t["sh"], 0) + 1
    res[region] = {
        "trips": len(d),
        "subway_use_pct": round(sub / n * 100, 1),
        "rail_use_pct": round(rail / n * 100, 1),
        "dist_share_pct": {"도로": round(RD / totd * 100, 1), "지하철": round(SD / totd * 100, 1), "철도": round(RRD / totd * 100, 1)},
        "main_mode_trip_pct": {k: round(v / n * 100, 1) for k, v in main.items()},
        "peak_hour": dict(sorted(hours.items())),
    }
    r = res[region]
    print(f"\n{region}: 통행 {r['trips']:,}")
    print(f"  지하철이용 통행 {r['subway_use_pct']}% / 철도이용 {r['rail_use_pct']}%")
    print(f"  거리분담: {r['dist_share_pct']}")
    print(f"  주수단(최장거리) 통행: {r['main_mode_trip_pct']}")
    ph = sorted(r["peak_hour"].items(), key=lambda x: -x[1])[:3]
    print(f"  첨두 시간: {ph}")

res["_meta"] = {"base_date": "2025-02-11(화)", "method": "통행(trip) 단위 + 거리(length) 가중 — leg 단위 아님",
                "transfer_type": "1 도로(승용차·버스·택시) / 2 지하철 / 3 철도",
                "caveat": "P1 맵매칭 특성상 지하철 구간이 도로로 잡힐 수 있어 철도 분담 과소 가능 — 보조지표"}
(ANA / "telco_od.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n[저장] telco_od.json (통행·거리 기준 재산출)")
