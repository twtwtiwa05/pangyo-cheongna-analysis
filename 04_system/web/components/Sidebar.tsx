"use client";

import { useEffect, useState } from "react";
import type { MapMode, IsoBand } from "./RegionMap";
import { AccessChart, PeakHourChart, ModeShareChart, type DestMinute } from "./Charts";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

type Pair = { pangyo: number; cheongna: number };
type ReachBand = { reach_population: number; reach_workers: number; reach_firms: number };
export type SelMetric = { label: string; unit: string; p: number; c: number; fmt?: (n: number) => string };

interface Metrics {
  headline: Record<string, Pair>;
  reach: { pangyo: Record<string, ReachBand>; cheongna: Record<string, ReachBand> };
  landuse: {
    pangyo: { mainuse_pct: Record<string, number> };
    cheongna: { mainuse_pct: Record<string, number> };
  };
  isochrone?: { key_dest_minutes: Record<string, DestMinute> };
  smartcard?: {
    pangyo: { peak_hour: Record<string, number> };
    cheongna: { peak_hour: Record<string, number> };
  };
  telco?: {
    pangyo: { main_mode_trip_pct: Record<string, number> };
    cheongna: { main_mode_trip_pct: Record<string, number> };
  };
}

const USES = ["업무시설", "공동주택", "교육연구시설", "단독주택", "공장"];

const COMPARE: { key: string; label: string; unit: string; fmt?: (n: number) => string }[] = [
  { key: "직주비_종사자대인구", label: "직주비 (종사자/인구)", unit: "" },
  { key: "30분도달종사자", label: "30분 도달 종사자", unit: "명", fmt: (n) => n.toLocaleString() },
  { key: "업무시설_연면적%", label: "업무시설 비율", unit: "%" },
  { key: "평균용적률_%", label: "평균 용적률", unit: "%" },
  { key: "종사자밀도_㎢", label: "종사자밀도", unit: "/㎢", fmt: (n) => n.toLocaleString() },
  { key: "도로망밀도_km당㎢", label: "도로망 밀도", unit: "km/㎢" },
];

export default function Sidebar({
  mode, onModeChange, isoBand, onIsoBandChange, onSelectMetric,
}: {
  mode: MapMode;
  onModeChange: (m: MapMode) => void;
  isoBand: IsoBand;
  onIsoBandChange: (b: IsoBand) => void;
  onSelectMetric: (s: SelMetric) => void;
}) {
  const [m, setM] = useState<Metrics | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    fetch(`${BASE_PATH}/data/metrics.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setM)
      .catch(() => setErr(true));
  }, []);

  const band = isoBand === "off" ? null : `${isoBand}min`;
  const reachP = band && m ? m.reach.pangyo[band] : null;
  const reachC = band && m ? m.reach.cheongna[band] : null;
  const reachRatio =
    m && m.headline["30분도달종사자"].cheongna > 0
      ? m.headline["30분도달종사자"].pangyo / m.headline["30분도달종사자"].cheongna
      : null;

  return (
    <aside className="w-[380px] flex-shrink-0 h-full overflow-y-auto bg-slate-950 border-r border-slate-800">
      <header className="px-5 pt-5 pb-4 border-b border-slate-800">
        <div className="text-[11px] font-bold tracking-wider uppercase text-sky-400">업무지구 비교분석</div>
        <h1 className="text-[22px] font-bold mt-1 leading-tight text-white">판교 vs 청라</h1>
        <p className="text-[12.5px] text-slate-300 mt-1">데이터로 진단하는 업무지구의 성공과 실패</p>
        <div className="flex gap-2 mt-3 text-[11px] font-medium">
          <span className="px-2.5 py-0.5 rounded-full bg-sky-500/20 text-sky-200 border border-sky-500/40">판교 · 성공</span>
          <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/40">청라 · 저조</span>
        </div>

        {/* KPI 히어로 — 핵심 격차를 첫 화면에 노출 */}
        {m && (
          <div className="grid grid-cols-2 gap-2 mt-3.5">
            <div className="rounded-lg bg-gradient-to-br from-sky-500/15 to-transparent border border-sky-500/25 px-3 py-2.5">
              <div className="text-[11px] text-slate-300 font-medium">직주비 (종사자/인구)</div>
              <div className="text-[20px] font-bold tabular-nums mt-1 leading-none">
                <span className="text-sky-300">{m.headline["직주비_종사자대인구"].pangyo.toFixed(2)}</span>
                <span className="text-slate-400 text-[13px] mx-1">vs</span>
                <span className="text-amber-300">{m.headline["직주비_종사자대인구"].cheongna.toFixed(2)}</span>
              </div>
            </div>
            <div className="rounded-lg bg-gradient-to-br from-sky-500/15 to-transparent border border-sky-500/25 px-3 py-2.5">
              <div className="text-[11px] text-slate-300 font-medium">30분 노동시장 격차</div>
              <div className="text-[20px] font-bold tabular-nums text-sky-300 mt-1 leading-none">
                {reachRatio ? `${reachRatio.toFixed(1)}배` : "-"}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">판교 도달 종사자 우위</div>
            </div>
          </div>
        )}
        {err && (
          <div className="mt-3 px-3 py-2 rounded-md bg-amber-500/10 border border-amber-500/40 text-amber-100 text-[12px]">
            통계 데이터를 불러오지 못했습니다. dev 서버·데이터 경로를 확인하세요.
          </div>
        )}
      </header>

      {/* 모드 토글 */}
      <section className="px-5 py-4 border-b border-slate-800">
        <SectionTitle>지도 표시 모드</SectionTitle>
        <div className="grid grid-cols-2 gap-2">
          <Btn active={mode === "main_use"} onClick={() => onModeChange("main_use")}>건물 주용도</Btn>
          <Btn active={mode === "zoning"} onClick={() => onModeChange("zoning")}>용도지역</Btn>
          <Btn active={mode === "population"} onClick={() => onModeChange("population")}>집계구 인구</Btn>
          <Btn active={mode === "worker"} onClick={() => onModeChange("worker")}>집계구 종사자</Btn>
        </div>
      </section>

      {/* 등시간권 */}
      <section className="px-5 py-4 border-b border-slate-800">
        <SectionTitle>핵심역 등시간권 (지하철)</SectionTitle>
        <div className="grid grid-cols-3 gap-2">
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
        <p className="text-[12px] text-slate-400 mt-2.5 leading-relaxed">
          {band ? `${isoBand}분 내 도달가능 인구·종사자(노동시장 규모). 행정동 면적안분.` : "30/60분 선택 시 도달 인구·종사자 표시"}
        </p>
      </section>

      {/* 비교 통계 */}
      <section className="px-5 py-4 border-b border-slate-800">
        <SectionTitle>핵심 지표 비교</SectionTitle>
        <div className="space-y-3.5 mt-1">
          {m && COMPARE.map((c) => {
            const v = m.headline[c.key];
            if (!v) return null;
            return <CompareBar key={c.key} label={c.label} unit={c.unit} p={v.pangyo} c={v.cheongna} fmt={c.fmt}
              onClick={() => onSelectMetric({ label: c.label, unit: c.unit, p: v.pangyo, c: v.cheongna, fmt: c.fmt })} />;
          })}
          {!m && !err && <div className="text-[12px] text-slate-400">통계 로드 중...</div>}
        </div>
      </section>

      {/* 핵심 도심 접근성 (등시간권 보조 — 강력한 격차 근거) */}
      {m?.isochrone && (
        <section className="px-5 py-4 border-b border-slate-800">
          <SectionTitle>핵심 도심까지 소요시간 (분)</SectionTitle>
          <AccessChart dest={m.isochrone.key_dest_minutes} />
        </section>
      )}

      {/* 주용도 구성 비교 (연면적%) */}
      {m && (
        <section className="px-5 py-4 border-b border-slate-800">
          <SectionTitle>주용도 구성 (연면적%)</SectionTitle>
          <div className="space-y-3.5 mt-1">
            {USES.map((u) => {
              const p = m.landuse.pangyo.mainuse_pct[u] || 0;
              const c = m.landuse.cheongna.mainuse_pct[u] || 0;
              if (p < 1 && c < 1) return null;
              return <CompareBar key={u} label={u} unit="%" p={p} c={c} />;
            })}
          </div>
        </section>
      )}

      {/* 수단분담 (통신사 통행 기준) */}
      {m?.telco && (
        <section className="px-5 py-4 border-b border-slate-800">
          <SectionTitle>수단분담 (통행 기준)</SectionTitle>
          <ModeShareChart pangyo={m.telco.pangyo.main_mode_trip_pct} cheongna={m.telco.cheongna.main_mode_trip_pct} />
        </section>
      )}

      {/* 시간대별 통행 패턴 (교통카드) */}
      {m?.smartcard && (
        <section className="px-5 py-4 border-b border-slate-800">
          <SectionTitle>시간대별 대중교통 통행</SectionTitle>
          <PeakHourChart pangyo={m.smartcard.pangyo.peak_hour} cheongna={m.smartcard.cheongna.peak_hour} />
        </section>
      )}

      <footer className="px-5 py-4 text-[11px] text-slate-500 leading-relaxed">
        필지 클릭 시 상세(용적률·연면적). 데이터: SGIS·VWorld·건축HUB·OSM·지하철망 · 베이스맵 © V-World/OSM
      </footer>
    </aside>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div className="text-[12.5px] font-bold text-slate-200 tracking-wide uppercase mb-2.5">{children}</div>;
}

function Btn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={`text-[13px] py-2 rounded-md font-semibold transition-colors ${active ? "bg-sky-500 text-white shadow-sm shadow-sky-500/30" : "bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white border border-slate-700"}`}>
      {children}
    </button>
  );
}

function ReachCard({ color, title, pop, wrk }: { color: "sky" | "amber"; title: string; pop: number; wrk: number }) {
  const c = color === "sky" ? "text-sky-300" : "text-amber-300";
  return (
    <div className="bg-slate-900/60 rounded-md px-2.5 py-2 border border-slate-700">
      <div className={`text-[12.5px] font-bold ${c}`}>{title}</div>
      <div className="text-[11px] text-slate-400 mt-1">종사자</div>
      <div className="text-[15px] font-bold tabular-nums text-slate-100">{wrk.toLocaleString()}</div>
      <div className="text-[11px] text-slate-400 mt-0.5">인구 {pop.toLocaleString()}</div>
    </div>
  );
}

function CompareBar({ label, unit, p, c, fmt, onClick }: { label: string; unit: string; p: number; c: number; fmt?: (n: number) => string; onClick?: () => void }) {
  const max = Math.max(p, c) || 1;
  const f = (n: number) => (fmt ? fmt(n) : n.toLocaleString(undefined, { maximumFractionDigits: 2 }));
  return (
    <div onClick={onClick} className={onClick ? "cursor-pointer hover:bg-slate-800/50 -mx-2 px-2 py-1 rounded-md transition-colors" : ""}>
      <div className="flex justify-between text-[12.5px] mb-1.5">
        <span className="text-slate-200 font-medium">{label}{onClick ? " ⤢" : ""}</span>
        <span className="text-slate-400">{unit}</span>
      </div>
      <div className="space-y-1.5">
        <BarRow color="bg-sky-500" label="판교" width={(p / max) * 100} text={f(p)} />
        <BarRow color="bg-amber-500" label="청라" width={(c / max) * 100} text={f(c)} />
      </div>
    </div>
  );
}

function BarRow({ color, label, width, text }: { color: string; label: string; width: number; text: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-slate-400 w-7 flex-shrink-0">{label}</span>
      <div className="flex-1 h-4 bg-slate-900 rounded-sm overflow-hidden">
        <div className={`h-full ${color} rounded-sm`} style={{ width: `${Math.max(width, 1.5)}%` }} />
      </div>
      <span className="text-[12px] text-slate-100 font-medium tabular-nums w-16 text-right flex-shrink-0">{text}</span>
    </div>
  );
}
