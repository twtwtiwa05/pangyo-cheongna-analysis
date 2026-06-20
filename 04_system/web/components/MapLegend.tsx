"use client";

// 지도 위 색의 의미를 알려주는 범례. 모드/등시간권 상태에 따라 전환된다.
// categories.ts의 팔레트·스케일을 그대로 공유하므로 지도 채색과 항상 일치한다.

import {
  MAIN_USE_LEGEND,
  ZONING_LEGEND,
  POP_RAMP,
  WORKER_RAMP,
  type LegendItem,
  type RampStop,
} from "@/lib/categories";
import type { MapMode, IsoBand } from "./RegionMap";

export default function MapLegend({
  mode,
  isoBand,
  accent,
}: {
  mode: MapMode;
  isoBand: IsoBand;
  accent: string;
}) {
  // 등시간권이 켜져 있으면 등시간권 범례를 우선 표시
  if (isoBand !== "off") return <IsoLegend isoBand={isoBand} accent={accent} />;
  if (mode === "main_use") return <ChipLegend title="건물 주용도" items={MAIN_USE_LEGEND} />;
  if (mode === "zoning") return <ChipLegend title="용도지역(대분류)" items={ZONING_LEGEND} />;
  if (mode === "population") return <RampLegend title="집계구 인구 (명)" ramp={POP_RAMP} />;
  if (mode === "worker") return <RampLegend title="집계구 종사자 (명)" ramp={WORKER_RAMP} />;
  // flow 모드 범례는 사이드바에 상세히 존재하므로 지도에서는 생략
  return null;
}

function Box({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute top-[58px] left-3 z-[5] rounded-lg bg-slate-900/90 border border-slate-700 backdrop-blur px-2.5 py-2 shadow-lg pointer-events-none max-w-[220px]">
      {children}
    </div>
  );
}

function Title({ children }: { children: React.ReactNode }) {
  return <div className="text-[10px] font-semibold text-slate-300 mb-1.5">{children}</div>;
}

function ChipLegend({ title, items }: { title: string; items: LegendItem[] }) {
  return (
    <Box>
      <Title>{title}</Title>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-sm flex-shrink-0 border border-black/20"
              style={{ background: it.color }}
            />
            <span className="text-[10px] text-slate-300 whitespace-nowrap">{it.label}</span>
          </div>
        ))}
      </div>
    </Box>
  );
}

function RampLegend({ title, ramp }: { title: string; ramp: RampStop[] }) {
  const gradient = `linear-gradient(to right, ${ramp.map((r) => r.color).join(", ")})`;
  const min = ramp[0].stop;
  const mid = ramp[Math.floor(ramp.length / 2)].stop;
  const max = ramp[ramp.length - 1].stop;
  return (
    <Box>
      <Title>{title}</Title>
      <div className="h-2.5 w-40 rounded-sm border border-black/20" style={{ background: gradient }} />
      <div className="flex justify-between text-[9px] text-slate-400 mt-1 w-40 tabular-nums">
        <span>{min.toLocaleString()}</span>
        <span>{mid.toLocaleString()}</span>
        <span>{`${max.toLocaleString()}+`}</span>
      </div>
    </Box>
  );
}

function IsoLegend({ isoBand, accent }: { isoBand: IsoBand; accent: string }) {
  return (
    <Box>
      <Title>{`핵심역 ${isoBand}분 등시간권`}</Title>
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <span
            className="w-3 h-2.5 rounded-sm flex-shrink-0 border"
            style={{ background: accent, opacity: isoBand === "30" ? 0.55 : 0.38, borderColor: accent }}
          />
          <span className="text-[10px] text-slate-300">{isoBand}분 내 도달권</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: "#22d3ee" }} />
          <span className="text-[10px] text-slate-300">도달 지하철역</span>
        </div>
      </div>
    </Box>
  );
}
