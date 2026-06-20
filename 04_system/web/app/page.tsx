"use client";

import { useState } from "react";
import Sidebar, { type SelMetric } from "@/components/Sidebar";
import RegionMap, { type MapMode, type IsoBand } from "@/components/RegionMap";

export default function Home() {
  const [mode, setMode] = useState<MapMode>("main_use");
  const [isoBand, setIsoBand] = useState<IsoBand>("off");
  const [sel, setSel] = useState<SelMetric | null>(null);
  // 지도 표시모드 클릭 시 등시간권을 끄고 구역으로 줌 복귀
  const handleMode = (m: MapMode) => {
    setMode(m);
    setIsoBand("off");
  };
  return (
    <main className="flex bg-slate-900 text-slate-100" style={{ height: "100vh", width: "100vw" }}>
      <Sidebar mode={mode} onModeChange={handleMode} isoBand={isoBand} onIsoBandChange={setIsoBand} onSelectMetric={setSel} />
      <div className="flex-1 grid grid-cols-2 relative" style={{ gap: "2px", background: "#334155" }}>
        <RegionMap region="pangyo" mode={mode} isoBand={isoBand} />
        <RegionMap region="cheongna" mode={mode} isoBand={isoBand} />
        {sel && <MetricOverlay sel={sel} onClose={() => setSel(null)} />}
      </div>
    </main>
  );
}

function MetricOverlay({ sel, onClose }: { sel: SelMetric; onClose: () => void }) {
  const max = Math.max(sel.p, sel.c) || 1;
  const f = (n: number) => (sel.fmt ? sel.fmt(n) : n.toLocaleString(undefined, { maximumFractionDigits: 2 }));
  const ratio = sel.c > 0 ? sel.p / sel.c : null;
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-7 w-[460px] max-w-[90%]" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-5">
          <div>
            <div className="text-[11px] text-sky-400 uppercase tracking-wider">핵심 지표 비교</div>
            <h2 className="text-lg font-bold mt-0.5">{sel.label}{sel.unit ? ` (${sel.unit})` : ""}</h2>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200 text-2xl leading-none">×</button>
        </div>
        <div className="space-y-4">
          <BigBar color="bg-sky-500" label="판교테크노밸리" width={(sel.p / max) * 100} text={f(sel.p)} />
          <BigBar color="bg-amber-500" label="청라국제도시" width={(sel.c / max) * 100} text={f(sel.c)} />
        </div>
        {ratio && (
          <div className="mt-5 pt-4 border-t border-slate-800 text-center">
            <span className="text-[12px] text-slate-400">판교 / 청라 = </span>
            <span className="text-xl font-bold text-sky-300 tabular-nums">
              {ratio >= 1 ? `${ratio.toFixed(1)}배` : `${(1 / ratio).toFixed(1)}배 (청라 우위)`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function BigBar({ color, label, width, text }: { color: string; label: string; width: number; text: string }) {
  return (
    <div>
      <div className="flex justify-between text-[13px] mb-1.5">
        <span className="text-slate-300 font-medium">{label}</span>
        <span className="text-slate-100 font-bold tabular-nums">{text}</span>
      </div>
      <div className="h-7 bg-slate-800 rounded-md overflow-hidden">
        <div className={`h-full ${color} rounded-md`} style={{ width: `${Math.max(width, 2)}%` }} />
      </div>
    </div>
  );
}
