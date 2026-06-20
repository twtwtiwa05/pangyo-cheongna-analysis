"use client";

// metrics.json의 미활용 데이터를 시각화하는 경량 차트 모음 (라이브러리 없이 SVG/CSS).
// 정적 데이터 + 단순 형태이므로 의존성 0으로 배포 안정성·번들 크기를 지킨다.

const PANGYO = "#38bdf8"; // sky-400
const CHEONGNA = "#f59e0b"; // amber-500

// ── 핵심 도심까지 소요시간 (분, 지하철) — 접근성 격차의 핵심 근거 ──
export interface DestMinute {
  pangyo: number | null;
  cheongna: number | null;
}

export function AccessChart({ dest }: { dest: Record<string, DestMinute> }) {
  // 도심 목적지만 선별 (자기 지역·공항·null 제외)
  const order = ["강남", "삼성", "여의도", "광화문", "시청"];
  const rows = order
    .map((k) => ({ name: k, ...dest[k] }))
    .filter((r) => typeof r.pangyo === "number" && typeof r.cheongna === "number") as {
    name: string;
    pangyo: number;
    cheongna: number;
  }[];
  if (rows.length === 0) return null;
  const max = Math.max(...rows.flatMap((r) => [r.pangyo, r.cheongna])) * 1.05;
  return (
    <div className="space-y-3">
      {rows.map((r) => (
        <div key={r.name}>
          <div className="flex justify-between text-[12.5px] mb-1.5">
            <span className="text-slate-200 font-medium">{r.name}</span>
            <span className="text-[11.5px] tabular-nums">
              <span style={{ color: PANGYO }}>{r.pangyo.toFixed(0)}분</span>
              <span className="text-slate-500"> vs </span>
              <span style={{ color: CHEONGNA }}>{r.cheongna.toFixed(0)}분</span>
            </span>
          </div>
          <MiniBar color={PANGYO} width={(r.pangyo / max) * 100} />
          <div className="h-1" />
          <MiniBar color={CHEONGNA} width={(r.cheongna / max) * 100} />
        </div>
      ))}
      <p className="text-[11px] text-slate-400 leading-relaxed pt-0.5">
        막대가 짧을수록 접근성 우위. 판교는 신분당선으로 강남 직결(13.9분), 청라는 4.7배(65.3분).
      </p>
    </div>
  );
}

function MiniBar({ color, width }: { color: string; width: number }) {
  return (
    <div className="h-3 bg-slate-800 rounded-sm overflow-hidden">
      <div className="h-full rounded-sm" style={{ width: `${Math.max(width, 1.5)}%`, background: color }} />
    </div>
  );
}

// ── 시간대별 대중교통 통행 (24h 곡선) — 출근형 vs 퇴근형 ──────
export function PeakHourChart({
  pangyo,
  cheongna,
}: {
  pangyo: Record<string, number>;
  cheongna: Record<string, number>;
}) {
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const pArr = hours.map((h) => pangyo[String(h)] ?? 0);
  const cArr = hours.map((h) => cheongna[String(h)] ?? 0);
  const pSum = pArr.reduce((a, b) => a + b, 0) || 1;
  const cSum = cArr.reduce((a, b) => a + b, 0) || 1;
  const pPct = pArr.map((v) => v / pSum); // 지역 내 비율로 정규화 → 패턴(모양) 비교
  const cPct = cArr.map((v) => v / cSum);
  const maxPct = Math.max(...pPct, ...cPct) || 1;

  const W = 320, H = 112, padL = 6, padR = 6, padT = 8, padB = 18;
  const iw = W - padL - padR, ih = H - padT - padB;
  const x = (i: number) => padL + (i / 23) * iw;
  const y = (v: number) => padT + ih - (v / maxPct) * ih;
  const line = (arr: number[]) =>
    arr.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = (arr: number[]) =>
    `${line(arr)} L${x(23).toFixed(1)},${(padT + ih).toFixed(1)} L${x(0).toFixed(1)},${(padT + ih).toFixed(1)} Z`;

  return (
    <div>
      {/* 범례 */}
      <div className="flex gap-3 text-[11px] mb-1.5">
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-[3px] rounded" style={{ background: PANGYO }} /><span className="text-slate-300">판교</span></span>
        <span className="flex items-center gap-1"><span className="inline-block w-3 h-[3px] rounded" style={{ background: CHEONGNA }} /><span className="text-slate-300">청라</span></span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: "auto" }} role="img" aria-label="시간대별 통행 곡선">
        {/* 출근(7-9시)·퇴근(17-19시) 가이드 밴드 */}
        <rect x={x(7)} y={padT} width={x(9) - x(7)} height={ih} fill="#ffffff" opacity={0.05} />
        <rect x={x(17)} y={padT} width={x(19) - x(17)} height={ih} fill="#ffffff" opacity={0.05} />
        <path d={area(pPct)} fill={PANGYO} fillOpacity={0.14} />
        <path d={area(cPct)} fill={CHEONGNA} fillOpacity={0.14} />
        <path d={line(pPct)} fill="none" stroke={PANGYO} strokeWidth={1.9} strokeLinejoin="round" />
        <path d={line(cPct)} fill="none" stroke={CHEONGNA} strokeWidth={1.9} strokeLinejoin="round" />
        {[0, 6, 12, 18, 23].map((h) => (
          <text key={h} x={x(h)} y={H - 5} fontSize={9.5} fill="#94a3b8" textAnchor={h === 0 ? "start" : h === 23 ? "end" : "middle"}>
            {h}시
          </text>
        ))}
      </svg>
      <p className="text-[11px] text-slate-400 leading-relaxed mt-0.5">
        지역 내 통행 비율(패턴). 판교는 <span style={{ color: PANGYO }}>아침 출근</span> 첨두(업무 유입), 청라는{" "}
        <span style={{ color: CHEONGNA }}>저녁 퇴근</span> 첨두(베드타운 귀가).
      </p>
    </div>
  );
}

// ── 수단분담 (통행 기준 %) — 지하철 분담률 격차 ──────────────
export function ModeShareChart({
  pangyo,
  cheongna,
}: {
  pangyo: Record<string, number>;
  cheongna: Record<string, number>;
}) {
  const modes: { key: string; color: string }[] = [
    { key: "도로", color: "#64748b" },
    { key: "지하철", color: "#38bdf8" },
    { key: "철도", color: "#a78bfa" },
  ];
  const Row = ({ title, data }: { title: string; data: Record<string, number> }) => (
    <div className="mb-2.5">
      <div className="text-[12px] text-slate-300 font-medium mb-1">{title}</div>
      <div className="flex h-6 rounded-sm overflow-hidden bg-slate-800">
        {modes.map((mm) => {
          const v = data[mm.key] ?? 0;
          if (v < 0.5) return null;
          return (
            <div
              key={mm.key}
              className="h-full flex items-center justify-center"
              style={{ width: `${v}%`, background: mm.color }}
              title={`${mm.key} ${v}%`}
            >
              {v >= 8 && <span className="text-[10px] text-white font-semibold">{v.toFixed(0)}%</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
  return (
    <div>
      <Row title="판교" data={pangyo} />
      <Row title="청라" data={cheongna} />
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-300 mt-1.5">
        {modes.map((mm) => (
          <span key={mm.key} className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: mm.color }} />
            {mm.key}
          </span>
        ))}
        <span className="text-slate-400 w-full">지하철 분담 판교 9.7% vs 청라 4.1% (통신사 2025-02, 통행 기준)</span>
      </div>
    </div>
  );
}

// ── 통계 검증 배지 (현재 미사용 — 필요 시 재사용) ─────────────
export function StatBadges({
  workerConcP,
  workerConcC,
  farDelta,
  farP,
}: {
  workerConcP: number;
  workerConcC: number;
  farDelta: number;
  farP: number;
}) {
  return (
    <div className="grid grid-cols-1 gap-2">
      <div className="rounded-md bg-slate-900/60 border border-slate-800 px-3 py-2">
        <div className="text-[11px] text-slate-400">종사자 공간집중도 (상위 10% 집계구 점유율)</div>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-[16px] font-bold tabular-nums" style={{ color: PANGYO }}>
            {workerConcP.toFixed(1)}%
          </span>
          <span className="text-slate-500 text-[12px]">vs</span>
          <span className="text-[16px] font-bold tabular-nums" style={{ color: CHEONGNA }}>
            {workerConcC.toFixed(1)}%
          </span>
        </div>
        <div className="text-[10px] text-slate-500 mt-0.5">높을수록 업무 집적 — 판교가 소수 집계구에 종사자 집중</div>
      </div>
      <div className="rounded-md bg-slate-900/60 border border-slate-800 px-3 py-2">
        <div className="text-[11px] text-slate-400">용적률 분포 차이 (필지 단위)</div>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-[16px] font-bold text-slate-100 tabular-nums">Cliff&apos;s δ = {farDelta.toFixed(2)}</span>
          <span className="text-[10px] text-emerald-400 px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
            큰 효과
          </span>
        </div>
        <div className="text-[10px] text-slate-500 mt-0.5">
          KS 검정 p {farP < 0.001 ? "< 0.001" : `= ${farP.toFixed(3)}`} — 판교 필지가 통계적으로 고밀
        </div>
      </div>
    </div>
  );
}
