# -*- coding: utf-8 -*-
"""
시스템 통계패널용 통합 metrics manifest 생성.
모든 분석 산출 json + 핵심 비교표(headline) → 04_system/web/public/data/metrics.json
"""
import json
from pathlib import Path

FE = Path(".")
ANA = FE / "pangyo-cheongna-analysis/03_analysis"
OUT = FE / "pangyo-cheongna-analysis/04_system/web/public/data"
OUT.mkdir(parents=True, exist_ok=True)


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


m = {
    "landuse": load(ANA / "landuse/landuse_metrics.json"),
    "socio": load(ANA / "socio/socio_metrics.json"),
    "reach": load(ANA / "transport/reach_metrics.json"),
    "isochrone": load(ANA / "transport/isochrone_summary.json"),
    "road": load(ANA / "transport/road_metrics.json"),
    "smartcard": load(ANA / "mobility/smartcard_od.json"),
    "telco": load(ANA / "mobility/telco_od.json"),
    "stat_tests": load(ANA / "validation/stat_tests.json"),
}

# 핵심 비교표 (통계패널 직결) — 분석 산출 수치
m["headline"] = {
    "구역면적_㎢": {"pangyo": 2.84, "cheongna": 20.53},
    "직주비_종사자대인구": {"pangyo": 4.14, "cheongna": 0.28},
    "종사자수": {"pangyo": 95905, "cheongna": 31201},
    "종사자밀도_㎢": {"pangyo": 34319, "cheongna": 1517},
    "업무시설_연면적%": {"pangyo": 45.06, "cheongna": 16.03},
    "공동주택_연면적%": {"pangyo": 26.49, "cheongna": 54.74},
    "평균용적률_%": {"pangyo": 156.66, "cheongna": 52.42},
    "도로망밀도_km당㎢": {"pangyo": 24.95, "cheongna": 14.10},
    "30분도달종사자": {"pangyo": 1059434, "cheongna": 76486},
    "60분도달종사자": {"pangyo": 5550694, "cheongna": 2554873},
    "핵심역_강남_분": {"pangyo": 13.9, "cheongna": 65.3},
}
m["_regions"] = {
    "pangyo": {"name": "판교테크노밸리(삼평동)", "station": "판교역(신분당선)", "center": [127.1112, 37.3956]},
    "cheongna": {"name": "청라국제도시(청라1~3동)", "station": "청라국제도시역(공항철도)", "center": [126.638, 37.535]},
}

(OUT / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
present = [k for k, v in m.items() if v is not None and not k.startswith("_")]
print(f"[저장] metrics.json — 포함: {present}")
print(f"telco: {'OK' if m['telco'] else '미완(통신사 대기)'}")
