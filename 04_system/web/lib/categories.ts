// 주용도 · 용도지역 카테고리별 컬러 팔레트 + 지역(판교/청라) 설정 + 범례·스케일 데이터.
// 직관성 우선 (주거=따뜻, 상업=강조, 녹지=초록, 공업=회색 등).
// 지도 채색과 범례가 동일 색을 공유하도록 이 파일을 단일 소스로 둔다.

export const MAIN_USE_COLORS: Record<string, string> = {
  공동주택: "#ef4444",
  단독주택: "#f97316",
  제1종근린생활시설: "#eab308",
  제2종근린생활시설: "#facc15",
  업무시설: "#8b5cf6",
  판매시설: "#ec4899",
  교육연구시설: "#06b6d4",
  의료시설: "#0ea5e9",
  종교시설: "#a78bfa",
  운동시설: "#22c55e",
  문화및집회시설: "#d946ef",
  숙박시설: "#fbbf24",
  자동차관련시설: "#64748b",
  창고시설: "#78716c",
  공장: "#475569",
  발전시설: "#0891b2",
  "분뇨.쓰레기처리시설": "#57534e",
  분뇨쓰레기처리시설: "#57534e",
  노유자시설: "#14b8a6",
  위락시설: "#db2777",
  교정및군사시설: "#1f2937",
};

export const ZONING_COLORS: Record<string, string> = {
  제1종전용주거지역: "#fef08a",
  제2종전용주거지역: "#fde68a",
  제1종일반주거지역: "#fcd34d",
  제2종일반주거지역: "#fbbf24",
  제3종일반주거지역: "#f59e0b",
  준주거지역: "#fb923c",
  근린상업지역: "#fb7185",
  일반상업지역: "#ef4444",
  중심상업지역: "#b91c1c",
  유통상업지역: "#dc2626",
  일반공업지역: "#6b7280",
  준공업지역: "#9ca3af",
  자연녹지지역: "#22c55e",
  생산녹지지역: "#16a34a",
  보전녹지지역: "#15803d",
  도시지역기타: "#94a3b8",
};

export const DEFAULT_COLOR = "#cbd5e1"; // slate-300

export function colorExpression(field: "main_use" | "zoning"): unknown[] {
  const palette = field === "main_use" ? MAIN_USE_COLORS : ZONING_COLORS;
  const expr: unknown[] = ["match", ["get", field]];
  for (const [k, v] of Object.entries(palette)) {
    expr.push(k, v);
  }
  expr.push(DEFAULT_COLOR);
  return expr;
}

// ── 범례 구성 (지도 위 색의 의미) ────────────────────────────
export interface LegendItem {
  label: string;
  color: string;
}

// 주용도: 두 지역에서 비중이 큰 주요 카테고리만 노출 (20종 전체는 과부하)
export const MAIN_USE_LEGEND: LegendItem[] = [
  { label: "업무시설", color: MAIN_USE_COLORS["업무시설"] },
  { label: "공동주택", color: MAIN_USE_COLORS["공동주택"] },
  { label: "단독주택", color: MAIN_USE_COLORS["단독주택"] },
  { label: "교육연구시설", color: MAIN_USE_COLORS["교육연구시설"] },
  { label: "판매시설", color: MAIN_USE_COLORS["판매시설"] },
  { label: "근린생활시설", color: MAIN_USE_COLORS["제1종근린생활시설"] },
  { label: "공장", color: MAIN_USE_COLORS["공장"] },
  { label: "기타", color: DEFAULT_COLOR },
];

// 용도지역: 세분(16종) 대신 대분류 그룹으로 요약 (직관성)
export const ZONING_LEGEND: LegendItem[] = [
  { label: "주거지역", color: "#fbbf24" },
  { label: "상업지역", color: "#ef4444" },
  { label: "공업지역", color: "#6b7280" },
  { label: "녹지지역", color: "#22c55e" },
];

// ── 집계구 choropleth 스케일 (인구·종사자) ───────────────────
export interface RampStop {
  stop: number;
  color: string;
}

export const POP_RAMP: RampStop[] = [
  { stop: 0, color: "#f1f5f9" },
  { stop: 300, color: "#bae6fd" },
  { stop: 700, color: "#38bdf8" },
  { stop: 1500, color: "#0284c7" },
  { stop: 3000, color: "#0c4a6e" },
];

// 종사자: 인구(파랑)와 구분되는 보라 계열
export const WORKER_RAMP: RampStop[] = [
  { stop: 0, color: "#f5f3ff" },
  { stop: 100, color: "#ddd6fe" },
  { stop: 500, color: "#a78bfa" },
  { stop: 2000, color: "#7c3aed" },
  { stop: 6000, color: "#4c1d95" },
];

// MapLibre interpolate 표현식 생성 (지도 채색 — 범례와 동일 ramp 공유)
export function rampExpression(field: string, ramp: RampStop[]): unknown[] {
  const expr: unknown[] = ["interpolate", ["linear"], ["coalesce", ["get", field], 0]];
  for (const r of ramp) expr.push(r.stop, r.color);
  return expr;
}

// ── 이동 흐름 방향별 색 (유입/유출 — 지역 정체색 amber와 충돌 회피) ──
export const FLOW_COLORS = {
  in: "#3b82f6", // 유입 (→ 구역) blue
  out: "#fb7185", // 유출 (구역 →) rose — 청라 amber(#f59e0b)와 구분
  default: "#94a3b8",
};

// ── 지역(구역) 설정 ──────────────────────────────────────────
export type RegionKey = "pangyo" | "cheongna";

export interface RegionConfig {
  key: RegionKey;
  name: string;     // 표시명
  sub: string;      // 행정구역
  station: string;  // 핵심역
  outcome: "success" | "low";
  center: [number, number];
  zoom: number;
  accent: string;   // 지역 강조색 (지역 구분 전용)
}

export const REGIONS: Record<RegionKey, RegionConfig> = {
  pangyo: {
    key: "pangyo",
    name: "판교테크노밸리",
    sub: "성남 분당구 삼평동",
    station: "판교역 (신분당선)",
    outcome: "success",
    center: [127.1112, 37.3956],
    zoom: 14,
    accent: "#38bdf8", // sky
  },
  cheongna: {
    key: "cheongna",
    name: "청라국제도시",
    sub: "인천 서구 청라1~3동",
    station: "청라국제도시역 (공항철도)",
    outcome: "low",
    center: [126.638, 37.535],
    zoom: 12.5,
    accent: "#f59e0b", // amber
  },
};
