"use client";

import { useEffect, useState } from "react";
import type { MapMode, IsoBand } from "./RegionMap";
import { REGIONS } from "@/lib/categories";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

type Pair = { pangyo: number; cheongna: number };
type ReachBand = { reach_population: number; reach_workers: number; reach_firms: number };
interface Metrics {
  headline: Record<string, Pair>;
  reach: { pangyo: Record<string, ReachBand>; cheongna: Record<string, ReachBand> };
}

const COMPARE: { key: string; label: string; unit: string; fmt?: (n: number) => string }[] = [
  { key: "직주비_종사자대인구", label: "직주비 (종사자/인구)", unit: "" },
  { key: "30분도달종사자", label: "30분 도달 종사자", unit: "명", fmt: (n) => n.toLocaleString() },
  { key: "업무시설_연면적%", label: "업무시설 비율", unit: "%" },
  { key: "평균용적률_%", label: "평균 용적률", unit: "%" },
  { key: "종사자밀도_㎢", label: "종사자밀도", unit: "/㎢", fmt: (n) => n.toLocaleString() },
  { key: "도로망밀도_km당㎢", label: "도로망 밀도", unit: "km/㎢" },
];

export default function Sidebar({
  mode, onModeChange, isoBand, onIsoBandChange,
}: {
  mode: MapMode;
  onModeChange: (m: MapMode) => void;
  isoBand: IsoBand;
  onIsoBandChange: (b: IsoBand) => void;
}) {
  const [m, setM] = useState<Metrics | null>(null);
  useEffect(() => {
    fetch(`${BASE_PATH}/data/metrics.json`).then((r) => r.json()).then(setM).catch(() => {});
  }, []);

  const band = isoBand === "off" ? null : `${isoBand}min`;
  const reachP = band && m ? m.reach.pangyo[band] : null;
  const reachC = band && m ? m.reach.cheongna[band] : null;

  return (
    <aside className="w-[340px] flex-shrink-0 h-full overflow-y-auto bg-slate-950 border-r border-slate-800">
      <header className="px-5 pt-5 pb-4 border-b border-slate-800">
        <div className="text-[10px] font-semibold tracking-wider uppercase text-sky-400">업무지구 비교분석</div>
        <h1 className="text-[17px] font-bold mt-1 leading-tight">판교 vs 청라</h1>
        <p className="text-[11px] text-slate-500 mt-1">데이터로 진단하는 업무지구의 성공과 실패</p>
        <div className="flex gap-2 mt-3 text-[10px]">
          <span className="px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-300 border border-sky-500/30">판교 · 성공</span>
          <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30">청라 · 저조</span>
        </div>
      </header>

      {/* 모드 토글 */}
      <section className="px-5 py-4 border-b border-slate-800">
        <SectionTitle>지도 표시 모드</SectionTitle>
        <div className="grid grid-cols-2 gap-1.5">
          <Btn active={mode === "main_use"} onClick={() => onModeChange("main_use")}>건물 주용도</Btn>
          <Btn active={mode === "zoning"} onClick={() => onModeChange("zoning")}>용도지역</Btn>
          <Btn active={mode === "population"} onClick={() => onModeChange("population")}>집계구 인구</Btn>
          <Btn active={mode === "worker"} onClick={() => onModeChange("worker")}>집계구 종사자</Btn>
        </div>
      </section>

      {/* 등시간권 */}
      <section className="px-5 py-4 border-b border-slate-800">
        <SectionTitle>핵심역 등시간권 (지하철)</SectionTitle>
        <div className="grid grid-cols-3 gap-1.5">
          <Btn active={isoBand === "off"} onClick={() => onIsoBandChange("off")}>끔</Btn>
          <Btn active={isoBand === "30"} onClick={() => onIsoBandChange("30")}>30분</Btn>
          <Btn active={isoBand === "60"} onClick={() => onIsoBandChange("60")}>60분</Btn>
        </div>
        {band && reachP && reachC && (
          <div className="mt-3 grid grid-cols-2 gap-2 text-center">
            <ReachCard color="sky" title="판교" pop={reachP.reach_population} wrk={reachP.reach_workers} />
            <ReachCard color="amber" title="청라" pop={reachC.reach_population} wrk={reachC.reach_workers} />
          </div>
        )}
        <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">
          {band ? `${isoBand}분 내 도달가능 인구·종사자(노동시장 규모). 행정동 면적안분.` : "30/60분 선택 시 도달 인구·종사자 표시"}
        </p>
      </section>

      {/* 비교 통계 */}
      <section className="px-5 py-4 border-b border-slate-800">
        <SectionTitle>핵심 지표 비교</SectionTitle>
        <div className="space-y-3 mt-1">
          {m && COMPARE.map((c) => {
            const v = m.headline[c.key];
            if (!v) return null;
            return <CompareBar key={c.key} label={c.label} unit={c.unit} p={v.pangyo} c={v.cheongna} fmt={c.fmt} />;
          })}
          {!m && <div className="text-[11px] text-slate-500">통계 로드 중...</div>}
        </div>
      </section>

      <footer className="px-5 py-4 text-[10px] text-slate-600 leading-relaxed">
        필지 클릭 시 상세(용적률·연면적). 데이터: SGIS·VWorld·건축HUB·OSM·지하철망 · 베이스맵 © V-World/OSM
      </footer>
    </aside>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-[10px] font-semibold text-slate-500 tracking-wider uppercase mb-2">{children}</div>;
}

function Btn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={`text-[12px] py-1.5 rounded-md font-medium transition-colors ${active ? "bg-sky-500 text-white shadow-sm shadow-sky-500/30" : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800"}`}>
      {children}
    </button>
  );
}

function ReachCard({ color, title, pop, wrk }: { color: "sky" | "amber"; title: string; pop: number; wrk: number }) {
  const c = color === "sky" ? "text-sky-300" : "text-amber-300";
  return (
    <div className="bg-slate-900/60 rounded-md px-2 py-2 border border-slate-800">
      <div className={`text-[11px] font-semibold ${c}`}>{title}</div>
      <div className="text-[10px] text-slate-500 mt-1">종사자</div>
      <div className="text-[13px] font-bold tabular-nums">{wrk.toLocaleString()}</div>
      <div className="text-[10px] text-slate-500 mt-0.5">인구 {pop.toLocaleString()}</div>
    </div>
  );
}

function CompareBar({ label, unit, p, c, fmt }: { label: string; unit: string; p: number; c: number; fmt?: (n: number) => string }) {
  const max = Math.max(p, c) || 1;
  const f = (n: number) => (fmt ? fmt(n) : n.toLocaleString(undefined, { maximumFractionDigits: 2 }));
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-600">{unit}</span>
      </div>
      <div className="space-y-1">
        <BarRow color="bg-sky-500" label="판교" value={p} width={(p / max) * 100} text={f(p)} />
        <BarRow color="bg-amber-500" label="청라" value={c} width={(c / max) * 100} text={f(c)} />
      </div>
    </div>
  );
}

function BarRow({ color, label, width, text }: { color: string; label: string; value: number; width: number; text: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-slate-500 w-6 flex-shrink-0">{label}</span>
      <div className="flex-1 h-3.5 bg-slate-900 rounded-sm overflow-hidden">
        <div className={`h-full ${color} rounded-sm`} style={{ width: `${Math.max(width, 1.5)}%` }} />
      </div>
      <span className="text-[10px] text-slate-300 tabular-nums w-16 text-right flex-shrink-0">{text}</span>
    </div>
  );
}
