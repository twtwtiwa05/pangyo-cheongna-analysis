# -*- coding: utf-8 -*-
"""
OSM 도로망 수집 + 도로망 밀도 지표 산출 — 판교(삼평동)·청라(청라1~3동).

입력:
  02_data/processed/district_{pangyo,cheongna}.geojson  (구역계 폴리곤, EPSG:4326)
산출:
  02_data/raw/osm/osm_graph_{pangyo,cheongna}.graphml    (원본 OSM 그래프, 재현용)
  02_data/processed/roads_{pangyo,cheongna}.geojson      (도로 LineString + highway 속성, EPSG:4326)
  03_analysis/transport/road_metrics.json                (지역별 총연장·밀도·교차점·면적)

기준:
  - 공간범위: 판교/청라 구역계 폴리곤 내부(전국 금지). 구역 경계로 클립(truncate_by_edge=True).
  - 네트워크: network_type='drive' (자동차 통행 도로). OSM은 시점 데이터 없음 → 수집시점(스냅샷) 명시.
  - 출처: OpenStreetMap contributors, ODbL. osmnx 2.0.2 Overpass API.
CRS:
  - osmnx 반환·저장·교환: EPSG:4326
  - 거리(총연장)·면적·교차점밀도 계산: EPSG:5179(UTM-K, m)로 재투영
도로율(도로면적/구역면적):
  - OSM에 도로 폭(lanes/width) 정보가 불완전 → 면적 기반 도로율은 산출 불가.
    본 지표는 '도로망 밀도(km/㎢)'로 대체함을 road_metrics.json 및 보고서에 명시.
재현성: random 미사용. 동일 입력·동일 OSM 스냅샷에서 동일 결과(수집일자 기록).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import osmnx as ox

FE = Path(r"C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
PROJ = FE / "pangyo-cheongna-analysis"
PROC = PROJ / "02_data" / "processed"
RAW = PROJ / "02_data" / "raw" / "osm"
TRANSPORT = PROJ / "03_analysis" / "transport"

CRS_STORE = "EPSG:4326"  # 저장·교환
CRS_METRIC = "EPSG:5179"  # 거리·면적 계산 (UTM-K)
NETWORK_TYPE = "drive"

REGIONS = {
    "pangyo": "district_pangyo.geojson",
    "cheongna": "district_cheongna.geojson",
}

# 재현성: 캐시 on, Overpass 안정 설정
ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.cache_folder = str(RAW / "_osmnx_cache")


def fetch_region(key: str, district_fn: str) -> dict:
    """단일 구역의 OSM 도로망 수집 + 지표 산출. dict 메트릭 반환."""
    gdf = gpd.read_file(PROC / district_fn).to_crs(CRS_STORE)
    polygon = gdf.geometry.union_all()  # 단일 폴리곤(여러 행이면 결합)
    area_km2 = float(gpd.GeoSeries([polygon], crs=CRS_STORE).to_crs(CRS_METRIC).area.iloc[0] / 1e6)

    # 구역 폴리곤 내부 도로망만 (경계 걸친 엣지는 truncate_by_edge로 보존)
    graph = ox.graph_from_polygon(
        polygon, network_type=NETWORK_TYPE, simplify=True, truncate_by_edge=True
    )

    # 원본 그래프 저장(재현용)
    RAW.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, RAW / f"osm_graph_{key}.graphml")

    nodes, edges = ox.graph_to_gdfs(graph, nodes=True, edges=True)

    # 거리·교차점밀도는 EPSG:5179에서
    edges_m = edges.to_crs(CRS_METRIC)
    total_len_km = float(edges_m.geometry.length.sum() / 1000.0)

    # 교차점(노드) 수: 실제 교차로 ≈ 진입차수(street_count) >= 3 인 노드
    if "street_count" in nodes.columns:
        n_intersections = int((nodes["street_count"] >= 3).sum())
    else:
        n_intersections = int(len(nodes))
    n_nodes_all = int(len(nodes))
    n_edges = int(len(edges))

    road_density = total_len_km / area_km2 if area_km2 else 0.0  # km/㎢
    intersection_density = n_intersections / area_km2 if area_km2 else 0.0  # 개/㎢

    # highway 타입 분포(리스트 값은 첫 요소로 정규화)
    def norm_hw(v: object) -> str:
        if isinstance(v, list):
            return str(v[0]) if v else "unknown"
        return str(v) if v is not None else "unknown"

    edges_out = edges.reset_index()[["highway", "name", "length", "geometry"]].copy()
    edges_out["highway"] = edges_out["highway"].apply(norm_hw)
    edges_out["name"] = edges_out["name"].apply(
        lambda v: ", ".join(map(str, v)) if isinstance(v, list) else (str(v) if v is not None else "")
    )
    hw_counts = edges_out["highway"].value_counts().to_dict()

    # 도로 LineString 저장 (EPSG:4326)
    edges_out = edges_out.set_geometry("geometry").set_crs(CRS_STORE)
    edges_out.to_file(PROC / f"roads_{key}.geojson", driver="GeoJSON")

    bounds = [round(float(b), 6) for b in edges.total_bounds]  # minx,miny,maxx,maxy

    metric = {
        "region": key,
        "area_km2": round(area_km2, 4),
        "road_total_length_km": round(total_len_km, 3),
        "road_density_km_per_km2": round(road_density, 3),
        "n_road_links": n_edges,
        "n_nodes_all": n_nodes_all,
        "n_intersections_streetcount_ge3": n_intersections,
        "intersection_density_per_km2": round(intersection_density, 3),
        "highway_type_counts": {k: int(v) for k, v in hw_counts.items()},
        "bbox_4326_minx_miny_maxx_maxy": bounds,
        "road_ratio_note": "도로폭 정보 불완전 → 면적기반 도로율 미산출, 도로망 밀도(km/㎢)로 대체",
    }
    print(
        f"[{key}] area={area_km2:.3f}㎢ len={total_len_km:.2f}km "
        f"density={road_density:.2f}km/㎢ links={n_edges} "
        f"intersections={n_intersections} ({intersection_density:.1f}/㎢)"
    )
    return metric


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    TRANSPORT.mkdir(parents=True, exist_ok=True)

    metrics = {
        "source": "OpenStreetMap contributors (ODbL)",
        "collected_via": f"osmnx {ox.__version__} graph_from_polygon",
        "collected_date": date.today().isoformat(),
        "network_type": NETWORK_TYPE,
        "crs_store": CRS_STORE,
        "crs_metric": CRS_METRIC,
        "spatial_scope": "판교 삼평동 구역계 + 청라1~3동 구역계 (구역 내부만)",
        "regions": {},
    }
    for key, fn in REGIONS.items():
        metrics["regions"][key] = fetch_region(key, fn)

    out = TRANSPORT / "road_metrics.json"
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
