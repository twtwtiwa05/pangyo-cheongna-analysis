// 주용도 · 용도지역 카테고리별 컬러 팔레트 + 지역(판교/청라) 설정.
// 직관성 우선 (주거=따뜻, 상업=강조, 녹지=초록, 공업=회색 등).

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
  숙박시설: "#f59e0b",
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
  accent: string;   // 지역 강조색
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
