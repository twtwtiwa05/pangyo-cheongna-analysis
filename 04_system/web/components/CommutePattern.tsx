"use client";

// 통근 패턴 모달 — 교통카드 실측 24시간 유입·유출 거울상 차트 (라이브러리 없이 SVG).
// "이동 흐름(지도 OD)" 대체: 시간 구조로 "판교=일자리 도시 / 청라=베드타운"을 보인다.
// 지도 영역을 꽉 채우는 대형 모달(좌측 사이드바와는 겹치지 않음). 데이터: commute_hourly.json.

import { useEffect, useState } from "react";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";
const PANGYO = "#38bdf8"; // sky-400
const CHEONGNA = "#f59e0b"; // amber-500

interface RegionFlow {
  in: number[];
  out: number[];
  in_total: number;
  out_total: number;
  peak_in_hour: number;
  peak_out_hour: number;
}
interface CommuteData {
  pangyo: RegionFlow;
  cheongna: RegionFlow;
}

const sumH = (arr: number[], hs: number[]): number => hs.reduce((s, h) => s + arr[h], 0);
const ratioAM = (d: RegionFlow): number => {
  const o = sumH(d.out, [7, 8, 9]);
  return o ? sumH(d.in, [7, 8, 9]) / o : 0;
};
const concAM = (d: RegionFlow): number => (d.in_total ? (sumH(d.in, [7, 8, 9]) / d.in_total) * 100 : 0);

export default function CommutePattern({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<CommuteData | null>(null);
  useEffect(() => {
    fetch(`${BASE_PATH}/data/commute_hourly.json`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});
  }, []);

  // 두 지역 공통 y축 — 통행량 '크기'까지 정직하게 비교 (판교가 더 큼)
  const rawMax = data
    ? Math.max(...data.pangyo.in, ...data.pangyo.out, ...data.cheongna.in, ...data.cheongna.out)
    : 0;
  const ymax = data ? Math.ceil(rawMax / 2000) * 2000 : 8000;

  return (
    <div
      className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full h-full max-w-none flex flex-col p-7 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 헤더 */}
        <div className="flex justify-between items-start shrink-0">
          <div>
            <div className="text-[13px] text-sky-400 uppercase tracking-wider font-semibold">이동성 · 교통카드 실측 (가점)</div>
            <h2 className="text-3xl font-bold mt-1">통근 패턴 — 시간대별 유입·유출</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-4xl leading-none -mt-1">
            ×
          </button>
        </div>
        <p className="text-[16px] text-slate-200 mt-3 leading-relaxed shrink-0">
          판교는 <b style={{ color: PANGYO }}>아침에 채워지고</b>(유입 피크 07시) 저녁에 비워지는 <b>일자리 도시</b>,
          청라는 <b style={{ color: CHEONGNA }}>아침에 비워지고</b>(유출 피크 07시) 저녁에 채워지는{" "}
          <b>베드타운</b> — 두 지역의 유입·유출 피크가 정확히 뒤바뀐 <b>거울상</b>.
        </p>

        {!data ? (
          <div className="flex-1 flex items-center justify-center text-slate-500 text-base">데이터 로드 중...</div>
        ) : (
          <>
            {/* 차트 2패널 — 남는 높이를 모두 사용 */}
            <div className="flex gap-5 flex-1 min-h-0 mt-4">
              <Panel title="판교테크노밸리" accent={PANGYO} d={data.pangyo} ymax={ymax} />
              <Panel title="청라국제도시" accent={CHEONGNA} d={data.cheongna} ymax={ymax} />
            </div>
            {/* 통계 카드 */}
            <div className="grid grid-cols-3 gap-4 mt-5 shrink-0">
              <StatCard
                label="오전(7–9시) 유입/유출 비"
                p={ratioAM(data.pangyo)}
                c={ratioAM(data.cheongna)}
                fmt={(n) => `${n.toFixed(2)}배`}
                hint="판교 들어옴 · 청라 나감 (약 13배 차)"
              />
              <StatCard
                label="유입 피크 시각"
                p={data.pangyo.peak_in_hour}
                c={data.cheongna.peak_in_hour}
                fmt={(n) => `${n}시`}
                hint="판교 출근 도착 · 청라 저녁 귀가"
              />
              <StatCard
                label="오전유입 집중도"
                p={concAM(data.pangyo)}
                c={concAM(data.cheongna)}
                fmt={(n) => `${n.toFixed(1)}%`}
                hint="하루 유입 중 7–9시 비중"
              />
            </div>
            <p className="text-[12.5px] text-slate-400 leading-relaxed mt-4 pt-3 border-t border-slate-800 shrink-0">
              유입=마지막 하차역이 구역 내(도착) · 유출=첫 승차역이 구역 내(출발). 단위 통행 수(건),{" "}
              <b>대중교통 한정</b>(승용차 제외) · 공간단위 구역 내 정류장 승하차 · 2024-11-14(목) 1일 · 출처 교통카드
              통행사슬. 두 패널 동일 y축(통행량 크기 비교). 음영=출근(7–9시)·퇴근(17–19시) 첨두대.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function Panel({ title, accent, d, ymax }: { title: string; accent: string; d: RegionFlow; ymax: number }) {
  const W = 480;
  const H = 320;
  const padL = 44;
  const padR = 18;
  const padT = 40;
  const padB = 36;
  const iw = W - padL - padR;
  const ih = H - padT - padB;
  const x = (h: number): number => padL + (h / 23) * iw;
  const y = (v: number): number => padT + ih - (v / ymax) * ih;
  const line = (arr: number[]): string =>
    arr.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = (arr: number[]): string =>
    `${line(arr)} L${x(23).toFixed(1)},${(padT + ih).toFixed(1)} L${x(0).toFixed(1)},${(padT + ih).toFixed(1)} Z`;
  const gridFracs = [0, 0.25, 0.5, 0.75, 1];
  const labelTicks = [0, ymax / 2, ymax];
  const pin = d.in[d.peak_in_hour];
  const pout = d.out[d.peak_out_hour];

  return (
    <div className="flex-1 bg-slate-950/40 rounded-xl border border-slate-800 p-3.5 flex flex-col min-h-0">
      <div className="flex items-center justify-between mb-1.5 px-1 shrink-0">
        <span className="text-[18px] font-bold" style={{ color: accent }}>
          {title}
        </span>
        <span className="text-[13.5px] text-slate-400">
          유입 <b style={{ color: accent }}>실선</b> · 유출 <b className="text-slate-200">점선</b>
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label={`${title} 시간대별 유입·유출`}
        >
          {/* y 그리드 */}
          {gridFracs.map((f) => (
            <line key={f} x1={padL} y1={y(f * ymax)} x2={W - padR} y2={y(f * ymax)} stroke="#1e293b" strokeWidth={1} />
          ))}
          {labelTicks.map((t) => (
            <text key={t} x={padL - 7} y={y(t) + 4} fontSize={13} fill="#94a3b8" textAnchor="end">
              {t === 0 ? "0" : `${t / 1000}천`}
            </text>
          ))}
          {/* 출근(7–9)·퇴근(17–19) 첨두 음영 */}
          <rect x={x(7)} y={padT} width={x(9) - x(7)} height={ih} fill="#ffffff" opacity={0.05} />
          <rect x={x(17)} y={padT} width={x(19) - x(17)} height={ih} fill="#ffffff" opacity={0.05} />
          {/* 유입 area + line */}
          <path d={area(d.in)} fill={accent} fillOpacity={0.14} />
          <path d={line(d.in)} fill="none" stroke={accent} strokeWidth={2.8} strokeLinejoin="round" />
          {/* 유출 dashed */}
          <path d={line(d.out)} fill="none" stroke="#94a3b8" strokeWidth={2.4} strokeDasharray="5 4" strokeLinejoin="round" />
          {/* 유입 피크 (라벨 위) */}
          <circle cx={x(d.peak_in_hour)} cy={y(pin)} r={4.5} fill={accent} stroke="#0f172a" strokeWidth={1.4} />
          <text x={x(d.peak_in_hour)} y={y(pin) - 12} fontSize={16} fill={accent} textAnchor="middle" fontWeight="bold">
            유입 {d.peak_in_hour}시 {pin.toLocaleString()}
          </text>
          {/* 유출 피크 (라벨 위 — 점선 위로 띄움) */}
          <circle cx={x(d.peak_out_hour)} cy={y(pout)} r={4.5} fill="none" stroke="#cbd5e1" strokeWidth={2.2} />
          <text x={x(d.peak_out_hour)} y={y(pout) - 12} fontSize={15} fill="#cbd5e1" textAnchor="middle" fontWeight="bold">
            유출 {d.peak_out_hour}시 {pout.toLocaleString()}
          </text>
          {/* x 라벨 */}
          {[0, 6, 9, 12, 18, 23].map((h) => (
            <text key={h} x={x(h)} y={H - 8} fontSize={13} fill="#94a3b8" textAnchor={h === 0 ? "start" : h === 23 ? "end" : "middle"}>
              {h}시
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}

function StatCard({
  label,
  p,
  c,
  fmt,
  hint,
}: {
  label: string;
  p: number;
  c: number;
  fmt: (n: number) => string;
  hint: string;
}) {
  return (
    <div className="rounded-lg bg-slate-900/60 border border-slate-800 px-5 py-4">
      <div className="text-[14px] text-slate-300 leading-tight font-medium">{label}</div>
      <div className="flex items-baseline gap-2.5 mt-2.5">
        <span className="text-[30px] font-bold tabular-nums" style={{ color: PANGYO }}>
          {fmt(p)}
        </span>
        <span className="text-slate-500 text-[15px]">vs</span>
        <span className="text-[30px] font-bold tabular-nums" style={{ color: CHEONGNA }}>
          {fmt(c)}
        </span>
      </div>
      <div className="text-[12.5px] text-slate-500 mt-1.5">{hint}</div>
    </div>
  );
}
