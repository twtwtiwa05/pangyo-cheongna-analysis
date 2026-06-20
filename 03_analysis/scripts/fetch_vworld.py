# -*- coding: utf-8 -*-
"""
VWorld — 판교(삼평동)·청라(청라1~3동) 구역계 내 필지 + 용도지역 수집.
songpa fetch_vworld_songpa 포팅 + 2지역 동시 + 10km² grid 분할 호출.

데이터셋: 필지 LP_PA_CBND_BUBUN(연속지적도 부번), 용도지역 LT_C_UQ111.
조인: 필지 centroid(EPSG:5179) → 용도지역 폴리곤 PIP(within) 1:1 (1:N이면 첫 매치).
범위·단위: 공간범위=판교 삼평동(2.84㎢)·청라1~3동(20.53㎢) 구역계 / 공간단위=필지(연속지적) /
           시간=VWorld 최신 고시(필지 jiga gosi_year·용도지역 dyear, 단년).
※ 코드체계: VWorld는 행안부 코드(판교 41135·청라 28260). SGIS 통계청코드(31023/23080) 아님.
VWorld 제약: geomFilter BBOX ≤ 10km² → 구역 envelope를 ~6km²(여유) grid 셀로 분할 순회.
             페이지당 1000건, 빈 페이지/1000 미만이면 종료. pnu(필지)·geometry hash(용도지역) dedup.

산출(저장·교환 EPSG:4326):
  02_data/processed/parcels_landuse_{pangyo,cheongna}.geojson  속성: pnu, jibun, zoning, zoning_year
  02_data/raw/vworld/{parcels,zoning}_raw_{pangyo,cheongna}.geojson  원본 필지·용도지역
재현성: 결정론적(난수 없음). 입력=VWorld Data API(songpa/.env VWORLD_API_KEY 재사용),
        grid 분할 파라미터·구역계 geojson 고정. "한 번 실행하면 같은 결과".
"""
import sys
import json
import time
import hashlib
import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, box
from shapely.ops import unary_union

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
SONGPA_FETCH = FE / "songpa-landuse-analysis" / "python" / "fetch"
sys.path.insert(0, str(SONGPA_FETCH))
import vworld_client  # songpa/.env 자동 로드(VWORLD_API_KEY 재사용)

PROJ = FE / "pangyo-cheongna-analysis"
PROC = PROJ / "02_data" / "processed"
RAW = PROJ / "02_data" / "raw" / "vworld"
PROC.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

CRS_UTMK, CRS_WGS84 = "EPSG:5179", "EPSG:4326"

# VWorld geomFilter BBOX는 10km² 이내. 안전 여유로 한 셀 변(m)을 2400m(=5.76km²)로 분할.
CELL_M = 2400
DATASET_PARCEL = "LP_PA_CBND_BUBUN"
DATASET_ZONING = "LT_C_UQ111"

REGIONS = ["pangyo", "cheongna"]


def fetch_in_bbox(dataset: str, bbox: str, *, max_pages: int = 50) -> list[dict]:
    """BBOX 내 1000건씩 페이지네이션. total 미상 → 빈 페이지/1000 미만에서 종료."""
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        r = vworld_client.get_feature(dataset, bbox, size=1000, page=page)
        feats = r.get("featureCollection", {}).get("features", [])
        if not feats:
            break
        out.extend(feats)
        if len(feats) < 1000:
            break
        time.sleep(0.1)
    return out


def grid_cells_5179(geom_5179, cell_m: int = CELL_M) -> list[tuple[float, float, float, float]]:
    """구역 폴리곤(EPSG:5179) envelope를 cell_m 변의 그리드 셀로 분할.
    구역과 교차하는 셀만 반환(빈 BBOX 호출 최소화)."""
    minx, miny, maxx, maxy = geom_5179.bounds
    nx = max(1, math.ceil((maxx - minx) / cell_m))
    ny = max(1, math.ceil((maxy - miny) / cell_m))
    cells: list[tuple[float, float, float, float]] = []
    for i in range(nx):
        for j in range(ny):
            x0 = minx + i * cell_m
            y0 = miny + j * cell_m
            x1 = min(x0 + cell_m, maxx)
            y1 = min(y0 + cell_m, maxy)
            if geom_5179.intersects(box(x0, y0, x1, y1)):
                cells.append((x0, y0, x1, y1))
    return cells


def bbox_5179_to_wgs84(cell, gdf_one_5179) -> str:
    """EPSG:5179 셀 사각형 → EPSG:4326 BBOX 문자열(VWorld geomFilter, crs EPSG:4326)."""
    x0, y0, x1, y1 = cell
    rect = gpd.GeoSeries([box(x0, y0, x1, y1)], crs=CRS_UTMK).to_crs(CRS_WGS84)
    minx, miny, maxx, maxy = rect.total_bounds
    return f"BOX({minx},{miny},{maxx},{maxy})"


def feats_to_gdf(feats: list[dict]) -> gpd.GeoDataFrame:
    rows = [{**f["properties"], "geometry": shape(f["geometry"])} for f in feats]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS_WGS84)


def collect_region(region: str) -> dict:
    """한 지역 필지·용도지역 수집 → 구역계 클립 → PIP 조인 → 저장. 검증 metrics 반환."""
    dist = gpd.read_file(PROC / f"district_{region}.geojson").to_crs(CRS_WGS84)
    dist_geom_wgs = unary_union(dist.geometry)
    dist_5179 = dist.to_crs(CRS_UTMK)
    dist_geom_5179 = unary_union(dist_5179.geometry)
    cells = grid_cells_5179(dist_geom_5179)
    print(f"\n[{region}] 구역 {dist['area_km2'].sum():.2f}㎢ → grid {len(cells)}셀(셀변 {CELL_M}m)")

    # ── 1) 필지 수집(pnu dedup) ──
    parcel_feats: list[dict] = []
    seen_pnu: set[str] = set()
    for n, cell in enumerate(cells, 1):
        bbox = bbox_5179_to_wgs84(cell, dist_5179)
        feats = fetch_in_bbox(DATASET_PARCEL, bbox)
        for f in feats:
            pnu = f.get("properties", {}).get("pnu")
            if pnu and pnu not in seen_pnu:
                seen_pnu.add(pnu)
                parcel_feats.append(f)
        print(f"  필지 셀 {n}/{len(cells)}: +{len(feats)} (누적 유니크 {len(parcel_feats)})")
        time.sleep(0.15)
    (RAW / f"parcels_raw_{region}.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": parcel_feats}, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── 2) 용도지역 수집(geometry hash dedup) ──
    zoning_feats: list[dict] = []
    seen_geo: set[str] = set()
    for n, cell in enumerate(cells, 1):
        bbox = bbox_5179_to_wgs84(cell, dist_5179)
        feats = fetch_in_bbox(DATASET_ZONING, bbox)
        for f in feats:
            gh = hashlib.md5(
                json.dumps(f.get("geometry", {}), sort_keys=True).encode()
            ).hexdigest()
            if gh not in seen_geo:
                seen_geo.add(gh)
                zoning_feats.append(f)
        print(f"  용도 셀 {n}/{len(cells)}: +{len(feats)} (누적 유니크 {len(zoning_feats)})")
        time.sleep(0.15)
    (RAW / f"zoning_raw_{region}.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zoning_feats}, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── 3) 필지 GDF → centroid(5179) 구역계 within 클립 ──
    parcels = feats_to_gdf(parcel_feats)
    n_raw = len(parcels)
    parcels_5179 = parcels.to_crs(CRS_UTMK)
    cent_5179 = parcels_5179.geometry.centroid
    in_dist = cent_5179.within(dist_geom_5179)
    parcels = parcels[in_dist.values].reset_index(drop=True)
    parcels_5179 = parcels_5179[in_dist.values].reset_index(drop=True)
    n_clip = len(parcels)
    print(f"  → 수집 필지 {n_raw} → 구역계 within 클립 {n_clip}")

    # ── 4) 용도지역 GDF(빈 uname 제외) ──
    zoning = feats_to_gdf(zoning_feats)
    if "uname" not in zoning.columns:
        zoning["uname"] = ""
    if "dyear" not in zoning.columns:
        zoning["dyear"] = None
    zoning["uname"] = zoning["uname"].fillna("").astype(str).str.strip()
    n_blank = int((zoning["uname"] == "").sum())
    zoning = zoning[zoning["uname"] != ""].reset_index(drop=True)
    zoning_5179 = zoning.to_crs(CRS_UTMK)

    # ── 5) 필지 centroid → 용도지역 PIP(within) 1:1 (1:N이면 첫 매치) ──
    cent = gpd.GeoDataFrame(
        {"pnu": parcels_5179["pnu"].values},
        geometry=parcels_5179.geometry.centroid,
        crs=CRS_UTMK,
    )
    sj = gpd.sjoin(
        cent, zoning_5179[["uname", "dyear", "geometry"]], how="left", predicate="within"
    )
    sj = sj.drop_duplicates(subset="pnu", keep="first")[["pnu", "uname", "dyear"]]
    sj = sj.rename(columns={"uname": "zoning", "dyear": "zoning_year"})

    # ── 6) 출력 속성만 추려 1:1 병합 → 저장(EPSG:4326) ──
    keep = parcels[["pnu", "jibun", "geometry"]].copy()
    joined = keep.merge(sj, on="pnu", how="left")
    joined = gpd.GeoDataFrame(joined, geometry="geometry", crs=CRS_WGS84)
    out_path = PROC / f"parcels_landuse_{region}.geojson"
    joined.to_file(out_path, driver="GeoJSON")

    # ── 검증 metrics ──
    n_missing = int(joined["zoning"].isna().sum())
    pct_missing = round(100 * n_missing / max(1, len(joined)), 2)
    top = joined["zoning"].value_counts().head(8)
    bounds = [round(b, 5) for b in joined.to_crs(CRS_WGS84).total_bounds]
    dbounds = [round(b, 5) for b in dist.total_bounds]
    print(f"  → 저장 {out_path.name}: {len(joined)}필지, zoning 결측 {n_missing}({pct_missing}%)")
    return {
        "region": region,
        "cells": len(cells),
        "parcels_collected": n_raw,
        "parcels_in_district": n_clip,
        "zoning_polys": len(zoning),
        "zoning_blank_dropped": n_blank,
        "zoning_missing": n_missing,
        "zoning_missing_pct": pct_missing,
        "top_zoning": {str(k): int(v) for k, v in top.items()},
        "parcel_bounds_wgs84": bounds,
        "district_bounds_wgs84": dbounds,
    }


def main() -> None:
    results = []
    for region in REGIONS:
        results.append(collect_region(region))
    print("\n" + "=" * 64)
    print("VWorld 필지+용도지역 수집 완료")
    for r in results:
        print(f"\n[{r['region']}] grid {r['cells']}셀")
        print(f"  필지: 수집 {r['parcels_collected']} → 구역내 {r['parcels_in_district']}")
        print(f"  용도지역 폴리곤 {r['zoning_polys']} (빈uname 제외 {r['zoning_blank_dropped']})")
        print(f"  zoning 결측 {r['zoning_missing']} ({r['zoning_missing_pct']}%)")
        print(f"  top zoning: {r['top_zoning']}")
        print(f"  필지 bounds {r['parcel_bounds_wgs84']}")
        print(f"  구역 bounds {r['district_bounds_wgs84']}")
    print("=" * 64)
    (RAW / "_fetch_metrics.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
