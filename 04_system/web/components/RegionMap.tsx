"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap, MapMouseEvent, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { colorExpression, REGIONS, type RegionKey } from "@/lib/categories";

export type MapMode = "main_use" | "zoning" | "population" | "worker" | "flow";
export type IsoBand = "off" | "30" | "60";

const VWORLD_KEY = process.env.NEXT_PUBLIC_VWORLD_API_KEY;
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

// 구역 행정동(집계구 adm_cd 앞 8자리) — 집계구를 구역 범위로 한정(필지/용도지역과 영역 일치)
const DONG8_OF: Record<RegionKey, string[]> = {
  pangyo: ["31023740"],
  cheongna: ["23080740", "23080780", "23080790"],
};

type ParcelProps = {
  pnu: string;
  jibun: string | null;
  zoning: string | null;
  main_use: string | null;
  total_floor_area: number | null;
  lot_area: number | null;
  n_buildings: number | null;
  mean_use_apr_year: number | null;
};

type BBox = [number, number, number, number];

function bboxOf(geojson: { features: { geometry: { coordinates: unknown } }[] }): BBox {
  let minx = 180, miny = 90, maxx = -180, maxy = -90;
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === "number") {
      const x = c[0] as number, y = c[1] as number;
      if (x < minx) minx = x;
      if (y < miny) miny = y;
      if (x > maxx) maxx = x;
      if (y > maxy) maxy = y;
    } else if (Array.isArray(c)) {
      c.forEach(walk);
    }
  };
  geojson.features.forEach((f) => walk(f.geometry.coordinates));
  return [minx, miny, maxx, maxy];
}

export default function RegionMap({
  region,
  mode,
  isoBand,
}: {
  region: RegionKey;
  mode: MapMode;
  isoBand: IsoBand;
}) {
  const cfg = REGIONS[region];
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const isoBbox = useRef<Record<string, BBox>>({});
  const [loaded, setLoaded] = useState(false);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container: containerRef.current,
        center: cfg.center,
        zoom: cfg.zoom,
        minZoom: 9,
        maxZoom: 18,
        style: {
          version: 8,
          sources: {
            vworld: VWORLD_KEY
              ? { type: "raster", tiles: [`https://api.vworld.kr/req/wmts/1.0.0/${VWORLD_KEY}/Base/{z}/{y}/{x}.png`], tileSize: 256, attribution: "© V-World" }
              : { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap" },
            osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap" },
          },
          layers: [
            { id: "osm-base", type: "raster", source: "osm", layout: { visibility: VWORLD_KEY ? "none" : "visible" } },
            { id: "vworld-base", type: "raster", source: "vworld" },
          ],
        },
      });
    } catch (e) {
      setErrMsg(`지도 초기화 실패: ${e instanceof Error ? e.message : String(e)}`);
      return;
    }

    let vErr = 0;
    map.on("error", (e) => {
      const url = (e as { error?: { url?: string } }).error?.url || "";
      if (url.includes("vworld.kr")) {
        vErr++;
        if (vErr >= 3) {
          map.setLayoutProperty("vworld-base", "visibility", "none");
          map.setLayoutProperty("osm-base", "visibility", "visible");
        }
      }
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

    // 핵심역 마커
    new maplibregl.Marker({ color: cfg.accent })
      .setLngLat(cfg.center)
      .setPopup(new maplibregl.Popup({ offset: 24 }).setHTML(`<b>${cfg.station}</b>`))
      .addTo(map);

    map.on("load", () => {
      const D = `${BASE_PATH}/data`;

      // 등시간권 폴리곤 (60 → 30 순으로 아래에)
      for (const b of ["60", "30"] as const) {
        const url = `${D}/isochrone_${region}_${b}min.geojson`;
        map.addSource(`iso${b}`, { type: "geojson", data: url });
        map.addLayer({ id: `iso${b}_fill`, type: "fill", source: `iso${b}`, paint: { "fill-color": cfg.accent, "fill-opacity": b === "30" ? 0.45 : 0.28 }, layout: { visibility: "none" } });
        map.addLayer({ id: `iso${b}_line`, type: "line", source: `iso${b}`, paint: { "line-color": cfg.accent, "line-width": 1.4 }, layout: { visibility: "none" } });
        fetch(url).then((r) => r.json()).then((g) => { isoBbox.current[b] = bboxOf(g); }).catch(() => {});
      }

      // 집계구 (인구/종사자 choropleth) — 구역 행정동만 표시(필지/용도지역과 영역 일치)
      const censusFilter = ["match", ["slice", ["to-string", ["get", "adm_cd"]], 0, 8], DONG8_OF[region], true, false] as maplibregl.FilterSpecification;
      map.addSource("census", { type: "geojson", data: `${D}/census_tracts_${region}.geojson` });
      map.addLayer({
        id: "census_fill", type: "fill", source: "census", filter: censusFilter,
        paint: { "fill-color": ["interpolate", ["linear"], ["coalesce", ["get", "population"], 0], 0, "#f1f5f9", 300, "#bae6fd", 700, "#38bdf8", 1500, "#0284c7", 3000, "#0c4a6e"], "fill-opacity": 0.78 },
        layout: { visibility: "none" },
      });
      map.addLayer({ id: "census_line", type: "line", source: "census", filter: censusFilter, paint: { "line-color": "#64748b", "line-width": 0.3 }, layout: { visibility: "none" } });

      // 필지 (주용도/용도지역)
      map.addSource("parcels", { type: "geojson", data: `${D}/parcels_joined_${region}.geojson` });
      map.addLayer({ id: "parcels_fill", type: "fill", source: "parcels", paint: { "fill-color": colorExpression("main_use") as maplibregl.DataDrivenPropertyValueSpecification<string>, "fill-opacity": 0.72 } });
      map.addLayer({ id: "parcels_line", type: "line", source: "parcels", paint: { "line-color": "#1e293b", "line-width": 0.12 } });
      map.addLayer({ id: "parcels_hover", type: "line", source: "parcels", paint: { "line-color": cfg.accent, "line-width": 2 }, filter: ["==", ["get", "pnu"], ""] });

      // 도달역 점
      map.addSource("isonodes", { type: "geojson", data: `${D}/isochrone_nodes_${region}.geojson` });
      map.addLayer({
        id: "isonodes_circle", type: "circle", source: "isonodes",
        paint: { "circle-radius": 3.2, "circle-color": ["match", ["get", "band"], "30min", "#22d3ee", "#c4b5fd"], "circle-stroke-color": "#0f172a", "circle-stroke-width": 0.5 },
        layout: { visibility: "none" },
      });

      // 이동 흐름 (교통카드 OD arc) — 출발지 → 핵심역, 수단별 색·통행량 두께
      map.addSource("flow", { type: "geojson", data: `${D}/flow_${region}.geojson` });
      map.addLayer({
        id: "flow_line", type: "line", source: "flow",
        paint: {
          "line-color": ["match", ["get", "mode"], "subway", "#38bdf8", "bus", "#22c55e", "#94a3b8"],
          "line-width": ["interpolate", ["linear"], ["get", "weight"], 10, 0.6, 300, 3, 1500, 7],
          "line-opacity": 0.6,
        },
        layout: { visibility: "none", "line-cap": "round" },
      });

      // 구역 경계 (최상단)
      map.addSource("district", { type: "geojson", data: `${D}/district_${region}.geojson` });
      map.addLayer({ id: "district_line", type: "line", source: "district", paint: { "line-color": "#0f172a", "line-width": 2.5, "line-dasharray": [2, 1] } });

      const showPopup = (e: MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as unknown as ParcelProps;
        map.setFilter("parcels_hover", ["==", ["get", "pnu"], p.pnu]);
        popupRef.current?.remove();
        popupRef.current = new maplibregl.Popup({ closeButton: true, maxWidth: "300px" }).setLngLat(e.lngLat).setHTML(parcelPopupHTML(p)).addTo(map);
      };
      map.on("click", "parcels_fill", showPopup);
      map.getCanvas().style.cursor = "default";
      map.on("mouseenter", "parcels_fill", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "parcels_fill", () => (map.getCanvas().style.cursor = "default"));

      setLoaded(true);
    });

    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [region]);

  // 모드 전환
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    const parcelMode = mode === "main_use" || mode === "zoning";
    const censusMode = mode === "population" || mode === "worker";
    const flowMode = mode === "flow";
    for (const l of ["parcels_fill", "parcels_line", "parcels_hover"]) map.setLayoutProperty(l, "visibility", parcelMode ? "visible" : "none");
    for (const l of ["census_fill", "census_line"]) map.setLayoutProperty(l, "visibility", censusMode ? "visible" : "none");
    map.setLayoutProperty("flow_line", "visibility", flowMode ? "visible" : "none");
    if (flowMode) {
      map.flyTo({ center: cfg.center, zoom: 9.3, duration: 700 });
    }
    if (parcelMode) {
      map.setPaintProperty("parcels_fill", "fill-color", colorExpression(mode) as maplibregl.DataDrivenPropertyValueSpecification<string>);
    } else {
      const field = mode === "worker" ? "tot_worker" : "population";
      const ramp = mode === "worker"
        ? ["interpolate", ["linear"], ["coalesce", ["get", field], 0], 0, "#f5f3ff", 100, "#ddd6fe", 500, "#a78bfa", 2000, "#7c3aed", 6000, "#4c1d95"]
        : ["interpolate", ["linear"], ["coalesce", ["get", field], 0], 0, "#f1f5f9", 300, "#bae6fd", 700, "#38bdf8", 1500, "#0284c7", 3000, "#0c4a6e"];
      map.setPaintProperty("census_fill", "fill-color", ramp as maplibregl.DataDrivenPropertyValueSpecification<string>);
    }
  }, [mode, loaded]);

  // 등시간권 전환 + 화면 맞춤
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    for (const b of ["30", "60"] as const) {
      const v = isoBand === b ? "visible" : "none";
      map.setLayoutProperty(`iso${b}_fill`, "visibility", v);
      map.setLayoutProperty(`iso${b}_line`, "visibility", v);
    }
    map.setLayoutProperty("isonodes_circle", "visibility", isoBand === "off" ? "none" : "visible");
    if (isoBand === "off") {
      map.flyTo({ center: cfg.center, zoom: cfg.zoom, duration: 700 });
    } else {
      const bb = isoBbox.current[isoBand];
      if (bb) map.fitBounds(bb, { padding: 24, duration: 800 });
    }
  }, [isoBand, loaded, cfg.center, cfg.zoom]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="bg-slate-800" style={{ position: "absolute", inset: 0 }} />
      <div className="absolute top-3 left-3 z-10 px-3 py-1.5 rounded-md bg-slate-900/85 border border-slate-700 backdrop-blur">
        <div className="text-[13px] font-semibold text-slate-100">{cfg.name}</div>
        <div className="text-[10px] text-slate-400">{cfg.sub} · {cfg.station}</div>
      </div>
      {errMsg && (
        <div className="absolute top-3 right-3 z-10 max-w-xs px-3 py-2 rounded-md bg-amber-500/10 border border-amber-500/40 text-amber-100 text-[11px]">{errMsg}</div>
      )}
      {!loaded && !errMsg && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-sm pointer-events-none">지도 로드 중...</div>
      )}
    </div>
  );
}

function parcelPopupHTML(p: ParcelProps): string {
  const far = p.total_floor_area && p.lot_area ? `${((p.total_floor_area / p.lot_area) * 100).toFixed(0)}%` : "-";
  const rows: [string, string][] = [
    ["지번", p.jibun || "-"],
    ["용도지역", p.zoning || "-"],
    ["대표 주용도", p.main_use || "(건물 없음)"],
    ["연면적", p.total_floor_area ? `${Math.round(p.total_floor_area).toLocaleString()} ㎡` : "-"],
    ["용적률", far],
    ["건물 수", p.n_buildings != null ? String(p.n_buildings) : "-"],
    ["평균 사용승인년", p.mean_use_apr_year ? String(p.mean_use_apr_year) : "-"],
  ];
  return `<div style="font:12px/1.5 system-ui,sans-serif;color:#0f172a;">
    <div style="font-weight:700;font-size:13px;margin-bottom:6px;">${p.jibun || p.pnu}</div>
    <table style="border-collapse:collapse;width:100%;">
      ${rows.map(([k, v]) => `<tr><td style="color:#64748b;padding:2px 8px 2px 0;white-space:nowrap;vertical-align:top;">${k}</td><td style="padding:2px 0;">${v}</td></tr>`).join("")}
    </table></div>`;
}
