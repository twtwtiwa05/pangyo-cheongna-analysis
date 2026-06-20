"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import RegionMap, { type MapMode, type IsoBand } from "@/components/RegionMap";

export default function Home() {
  const [mode, setMode] = useState<MapMode>("main_use");
  const [isoBand, setIsoBand] = useState<IsoBand>("off");
  return (
    <main className="flex bg-slate-900 text-slate-100" style={{ height: "100vh", width: "100vw" }}>
      <Sidebar mode={mode} onModeChange={setMode} isoBand={isoBand} onIsoBandChange={setIsoBand} />
      <div className="flex-1 grid grid-cols-2" style={{ gap: "2px", background: "#334155" }}>
        <RegionMap region="pangyo" mode={mode} isoBand={isoBand} />
        <RegionMap region="cheongna" mode={mode} isoBand={isoBand} />
      </div>
    </main>
  );
}
