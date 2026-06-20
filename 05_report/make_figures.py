# -*- coding: utf-8 -*-
"""보고서용 시각화 생성 — 판교(파랑) vs 청라(주황) 일관 팔레트.
설계 원칙(논문급 정교화):
 - 모든 그림 가로세로 동일(FIGSIZE), 제목 크기 동일(TS).
 - 라벨/주석이 데이터(곡선·막대·면적)와 겹치지 않도록 여백 배치.
 - 배수는 학술 표기 '배'(곱셈기호 × 미사용). 단위·축라벨·표본수(n) 명시.
 - 수치는 03_analysis/*.json 산출물에서 직접 로드(재현성). 출처·기준월은 캡션(docx)에 기재.
"""
import json, csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# --- 한글 폰트 ---
fm.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf")
fm.fontManager.addfont(r"C:\Windows\Fonts\malgunbd.ttf")
plt.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "figure.dpi": 200, "savefig.dpi": 200,
    "axes.grid": True, "grid.alpha": 0.22, "grid.linewidth": 0.5,
    "axes.edgecolor": "#475569", "axes.linewidth": 0.8,
    "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
})

# --- 공통 규격(전 그림 통일) ---
FIGSIZE = (7.2, 4.3)   # 모든 그림 동일 가로세로
TS = 12                # 제목 크기 동일
AX = 10.2              # 축라벨 크기
P, C = "#1d4ed8", "#ea580c"           # 판교 / 청라
PL, CL = "#bfdbfe", "#fed7aa"          # 연한 톤(음영)
GREEN, GREY, LGREY = "#0f9d58", "#64748b", "#cbd5e1"

ROOT = Path(__file__).resolve().parents[1]
ANA, OUT = ROOT/"03_analysis", ROOT/"05_report"/"figures"
OUT.mkdir(parents=True, exist_ok=True)
def J(p): return json.load(open(p, encoding="utf-8"))
land=J(ANA/"landuse"/"landuse_metrics.json"); reach=J(ANA/"transport"/"reach_metrics.json")
iso=J(ANA/"transport"/"isochrone_summary.json"); road=J(ANA/"transport"/"road_metrics.json")
socio=J(ANA/"socio"/"socio_metrics.json"); sc=J(ANA/"mobility"/"smartcard_od.json")
tel=J(ANA/"mobility"/"telco_od.json"); stat=J(ANA/"validation"/"stat_tests.json")
aux=J(ANA/"transport"/"aux_transport.json")
commute=J(ROOT/"04_system"/"web"/"public"/"data"/"commute_hourly.json")

def newfig():
    fig, ax = plt.subplots(figsize=FIGSIZE)
    return fig, ax
def title(ax, t): ax.set_title(t, fontsize=TS, fontweight="bold", pad=10)
def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT/name, bbox_inches="tight", facecolor="white", pad_inches=0.12)
    plt.close(fig); print("saved", name)

# ========== FIG 0 — 핵심 구조 지표 격차(청라=1.0 기준) ==========
ratios = sorted([
    ("종사자 밀도 (명/㎢)", 34319/1517),
    ("직주비 (종사자/상주인구)", 4.144/0.282),
    ("30분 도달 종사자 수", 1059434/76486),
    ("평균 용적률", 156.66/52.42),
    ("업무시설 연면적 비율", 45.06/16.03),
    ("도로망 밀도 (km/㎢)", 24.947/14.102),
    ("지하철 이용 통행 비율", 27.6/16.0),
], key=lambda x: x[1])
fig, ax = newfig()
ys=np.arange(len(ratios)); vals=[r[1] for r in ratios]
ax.barh(ys, vals, color=P, height=0.60, zorder=3)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in ratios])
ax.axvline(1, color=GREY, lw=1.0, ls="--", zorder=2)
ax.text(1, len(ratios)-0.35, "청라=1.0", color=GREY, fontsize=8.5, ha="center", va="bottom")
for y,v in zip(ys,vals):
    ax.text(v+max(vals)*0.012, y, f"{v:.1f}배", va="center", ha="left",
            fontsize=10, fontweight="bold", color=P)
ax.set_xlim(0, max(vals)*1.16); ax.set_xlabel("청라 대비 판교 배율 (배)", fontsize=AX)
ax.margins(y=0.05)
title(ax, "핵심 구조 지표의 판교·청라 격차")
save(fig, "fig0_gap_overview.png")

# ========== FIG 1 — 누적 철도 접근성 곡선 ==========
mins=[]; pg=[]; ch=[]
for row in csv.DictReader(open(ANA/"transport"/"access_curve.csv", encoding="utf-8")):
    mins.append(int(row["minute"])); pg.append(int(row["pangyo_reachable_stations"])); ch.append(int(row["cheongna_reachable_stations"]))
mins,pg,ch = map(np.array,(mins,pg,ch))
fig, ax = newfig()
ax.fill_between(mins, ch, pg, where=(pg>=ch), color=PL, alpha=0.55, zorder=1, label="접근성 격차")
ax.plot(mins, pg, color=P, lw=2.6, zorder=3, label="판교역 (신분당·경강선)")
ax.plot(mins, ch, color=C, lw=2.6, zorder=3, label="청라국제도시역 (공항철도)")
for t in (30,60): ax.axvline(t, color=GREY, lw=0.8, ls=":", zorder=2)
ax.scatter([30,30,60,60],[100,49,456,303], s=26, zorder=5, color=[P,C,P,C], edgecolor="white", linewidth=0.8)
# 값은 좌상단 정보박스로 분리(곡선·면적과 비겹침)
info=("도달 가능 역 수 (개)\n"
      "  30분    판교 100  ·  청라 49\n"
      "  60분    판교 456  ·  청라 303")
ax.text(2.2, 472, info, va="top", ha="left", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=LGREY, lw=0.8, alpha=0.95))
ax.set_xlabel("핵심역 출발 철도 소요시간 (분)", fontsize=AX)
ax.set_ylabel("누적 도달 역 수 (개)", fontsize=AX)
ax.set_xlim(1,70); ax.set_ylim(0,490)
ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
title(ax, "핵심역 누적 철도 접근성 곡선")
save(fig, "fig1_access_curve.png")

# ========== FIG 2 — 30분 등시간권 도달 노동시장 ==========
cats=["도달 종사자","도달 인구","도달 사업체"]
pv=[reach["pangyo"]["30min"][k]/1e4 for k in ("reach_workers","reach_population","reach_firms")]
cv=[reach["cheongna"]["30min"][k]/1e4 for k in ("reach_workers","reach_population","reach_firms")]
mult=[pv[i]/cv[i] for i in range(3)]
x=np.arange(3); w=0.36
fig, ax = newfig()
ax.bar(x-w/2, pv, w, color=P, label="판교", zorder=3)
ax.bar(x+w/2, cv, w, color=C, label="청라", zorder=3)
for i in range(3):
    ax.text(x[i]-w/2, pv[i]+1.6, f"{pv[i]:,.1f}만", ha="center", fontsize=8.8, color=P, fontweight="bold")
    ax.text(x[i]+w/2, cv[i]+1.6, f"{cv[i]:,.1f}만", ha="center", fontsize=8.8, color=C, fontweight="bold")
    ax.text(x[i], max(pv[i],cv[i])+11, f"{mult[i]:.1f}배", ha="center", fontsize=10, fontweight="bold", color="#334155")
ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=10.5)
ax.set_ylabel("30분 등시간권 내 도달 규모 (만 명·만 개소)", fontsize=AX)
ax.set_ylim(0, max(pv)*1.24); ax.legend(fontsize=9.5, loc="upper right")
title(ax, "핵심역 30분 등시간권 내 도달 노동시장")
save(fig, "fig2_reach_market.png")

# ========== FIG 3 — 핵심역 → 주요 거점 철도 소요시간 ==========
dests=["강남","삼성","여의도","시청","광화문","인천공항"]; km=iso["key_dest_minutes"]
keys=["강남","삼성","여의도","시청","광화문","인천공항1터미널"]
pmin=[km[k]["pangyo"] for k in keys]; cmin=[km[k]["cheongna"] for k in keys]
y=np.arange(len(dests)); h=0.36
fig, ax = newfig()
ax.barh(y+h/2, pmin, h, color=P, label="판교", zorder=3)
ax.barh(y-h/2, cmin, h, color=C, label="청라", zorder=3)
for i in range(len(dests)):
    ax.text(pmin[i]+1.2, y[i]+h/2, f"{pmin[i]:.0f}", va="center", fontsize=8.6, color=P, fontweight="bold")
    ax.text(cmin[i]+1.2, y[i]-h/2, f"{cmin[i]:.0f}", va="center", fontsize=8.6, color=C, fontweight="bold")
ax.axvline(30, color=GREY, ls=":", lw=0.9, zorder=2)
ax.text(30, -0.95, "30분", fontsize=8.4, color=GREY, ha="center")
ax.set_yticks(y); ax.set_yticklabels(dests, fontsize=10.5); ax.invert_yaxis()
ax.set_xlim(0,112); ax.set_xlabel("핵심역 출발 철도 소요시간 (분, 환승대기 포함)", fontsize=AX)
ax.legend(fontsize=9.5, loc="upper right", framealpha=0.95)
title(ax, "핵심역→주요 고용·도심 거점 철도 소요시간")
save(fig, "fig3_rail_time.png")

# ========== FIG 4 — 건물 주용도 연면적 구성비(세로 100% 누적) ==========
def mainuse_group(d):
    m=d["mainuse_pct"]
    office=m.get("업무시설",0); resi=m.get("공동주택",0)+m.get("단독주택",0)
    edu=m.get("교육연구시설",0); fac=m.get("공장",0)
    return [office, resi, edu, fac, max(0,100-(office+resi+edu+fac))]
data=np.array([mainuse_group(land["pangyo"]), mainuse_group(land["cheongna"])])
seg=["업무시설","주거(공동·단독)","교육·연구","공장","기타"]; cols=[P,C,GREEN,GREY,LGREY]
fig, ax = newfig()
xx=np.arange(2); bottom=np.zeros(2)
for j in range(len(seg)):
    ax.bar(xx, data[:,j], bottom=bottom, width=0.46, color=cols[j], label=seg[j], edgecolor="white", linewidth=1.2, zorder=3)
    for i in range(2):
        if data[i,j]>=4.5:
            ax.text(i, bottom[i]+data[i,j]/2, f"{data[i,j]:.0f}%", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    bottom+=data[:,j]
ax.set_xticks(xx); ax.set_xticklabels(["판교","청라"], fontsize=11)
ax.set_xlim(-0.65,1.55); ax.set_ylim(0,100); ax.set_ylabel("건물 연면적 구성비 (%)", fontsize=AX)
ax.grid(axis="x", visible=False)
ax.legend(loc="center left", bbox_to_anchor=(1.02,0.5), fontsize=9.3, frameon=False, title="주용도")
title(ax, "건물 주용도 연면적 구성비")
save(fig, "fig4_mainuse.png")

# ========== FIG 5 — 필지 용적률 분포(boxplot, 중앙값 라벨 박스 밖) ==========
def far_values(reg):
    gj=J(ROOT/"02_data"/"processed"/f"parcels_joined_{reg}.geojson"); v=[]
    for f in gj["features"]:
        p=f["properties"]; la,fa=p.get("lot_area"),p.get("total_floor_area")
        if la and fa and la>0 and fa>0: v.append(fa/la*100)
    return np.array(v)
pfar,cfar=far_values("pangyo"),far_values("cheongna")
fig, ax = newfig()
bp=ax.boxplot([pfar,cfar], vert=True, positions=[1,2], widths=0.5, patch_artist=True,
              showfliers=False, medianprops=dict(color="black", lw=1.8),
              whiskerprops=dict(color="#334155"), capprops=dict(color="#334155"))
for patch,col in zip(bp["boxes"],[P,C]): patch.set_facecolor(col); patch.set_alpha(0.55); patch.set_edgecolor(col)
mp,mc=np.median(pfar),np.median(cfar)
ax.annotate(f"중앙값 {mp:.0f}%", xy=(1.255,mp), xytext=(1.40,mp), fontsize=9.3, color=P, fontweight="bold",
            va="center", ha="left", arrowprops=dict(arrowstyle="-", color=P, lw=0.8))
ax.annotate(f"중앙값 {mc:.0f}%", xy=(2.255,mc), xytext=(2.40,mc), fontsize=9.3, color=C, fontweight="bold",
            va="center", ha="left", arrowprops=dict(arrowstyle="-", color=C, lw=0.8))
ax.set_xticks([1,2]); ax.set_xticklabels([f"판교\n(n={len(pfar)})", f"청라\n(n={len(cfar)})"], fontsize=10.5)
ax.set_xlim(0.4,2.95); ax.set_ylim(0, np.percentile(np.concatenate([pfar,cfar]),97))
ax.set_ylabel("필지 용적률 = 연면적 / 대지면적 (%)", fontsize=AX)
ax.grid(axis="x", visible=False)
title(ax, "건축 필지 용적률 분포")
save(fig, "fig5_far_box.png")

# ========== FIG 6 — 인구·사회 핵심 지표(1x3) ==========
fig, axs = plt.subplots(1, 3, figsize=FIGSIZE)
metrics=[("직주비\n(종사자/상주인구)", [socio["pangyo"]["jobs_housing_ratio"],socio["cheongna"]["jobs_housing_ratio"]], "{:.2f}"),
         ("종사자 밀도\n(명/㎢)", [socio["pangyo"]["worker_density_per_km2"],socio["cheongna"]["worker_density_per_km2"]], "{:,.0f}"),
         ("업체당 종사자\n(명/사업체)", [socio["pangyo"]["workers_per_firm"],socio["cheongna"]["workers_per_firm"]], "{:.1f}")]
for ax,(t,vals,fmt) in zip(axs,metrics):
    ax.bar(["판교","청라"], vals, color=[P,C], width=0.62, zorder=3)
    for i,v in enumerate(vals):
        ax.text(i, v*1.02, fmt.format(v), ha="center", va="bottom", fontsize=9.6, fontweight="bold", color=[P,C][i])
    ax.set_title(t, fontsize=10); ax.set_ylim(0, max(vals)*1.22); ax.tick_params(labelsize=10)
    ax.grid(axis="x", visible=False)
fig.suptitle("인구·사회 핵심 지표 (SGIS 집계구, 구역 합산)", fontsize=TS, fontweight="bold", y=1.02)
save(fig, "fig6_socio.png")

# ========== FIG 7 — 통근 거울상(유입 vs 유출) ==========
hrs = np.arange(24)
fig, axs = plt.subplots(1, 2, figsize=FIGSIZE)
for ax, (reg, col, name) in zip(axs, [("pangyo", P, "판교"), ("cheongna", C, "청라")]):
    d = commute[reg]; inn = np.array(d["in"], float); out = np.array(d["out"], float)
    ax.fill_between(hrs, inn, color=col, alpha=0.28, zorder=1)
    ax.plot(hrs, inn, color=col, lw=2.3, zorder=3, label="유입(도착)")
    ax.plot(hrs, out, color="#475569", lw=1.7, ls="--", zorder=3, label="유출(출발)")
    am = inn[7:10].sum() / out[7:10].sum()
    ax.axvspan(6.5, 8.5, color="#94a3b8", alpha=0.14, zorder=0)
    ax.set_title(f"({'a' if reg=='pangyo' else 'b'}) {name} · 오전 유입/유출 {am:.1f}배", fontsize=10)
    ax.set_xlabel("시각 (시)", fontsize=9.6); ax.set_xticks(range(0, 24, 4))
    ax.set_ylim(0, max(inn.max(), out.max()) * 1.18)
    ax.legend(fontsize=8.6, loc="upper left", framealpha=0.92)
    ax.grid(axis="x", visible=False)
axs[0].set_ylabel("대중교통 통행량 (건/시)", fontsize=9.6)
fig.suptitle("통근 거울상 — 판교(일자리)·청라(베드타운)", fontsize=TS, fontweight="bold", y=1.02)
save(fig, "fig7_commute_mirror.png")

# ========== FIG 8 — 실측 이동·집적 보조 지표(1x2) ==========
fig, axs = plt.subplots(1, 2, figsize=FIGSIZE)
a=axs[0]; sv=[tel["pangyo"]["subway_use_pct"],tel["cheongna"]["subway_use_pct"]]
a.bar(["판교","청라"], sv, color=[P,C], width=0.6, zorder=3)
for i,v in enumerate(sv): a.text(i, v+0.5, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold", color=[P,C][i])
a.set_ylim(0, max(sv)*1.28); a.set_ylabel("지하철 이용 통행 비율 (%)", fontsize=9.8)
a.set_title("(a) 통신사 경로통행 중 지하철 이용", fontsize=10); a.tick_params(labelsize=10); a.grid(axis="x", visible=False)
b=axs[1]; wc=[stat["worker_concentration"]["top10pct_share_pangyo"],stat["worker_concentration"]["top10pct_share_cheongna"]]
b.bar(["판교","청라"], wc, color=[P,C], width=0.6, zorder=3)
for i,v in enumerate(wc): b.text(i, v+1.5, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold", color=[P,C][i])
b.set_ylim(0,112); b.set_ylabel("상위 10% 집계구 종사자 점유율 (%)", fontsize=9.8)
b.set_title("(b) 종사자 공간집중도", fontsize=10); b.tick_params(labelsize=10); b.grid(axis="x", visible=False)
fig.suptitle("실측 이동·집적 보조 지표", fontsize=TS, fontweight="bold", y=1.02)
save(fig, "fig8_mobility.png")

# ========== FIG A1 (부록) — 용도지역 면적 구성비(세로 100% 누적) ==========
def zoning_group(d):
    z=d["zoning_pct"]
    comm=sum(v for k,v in z.items() if "상업" in k); junju=z.get("준주거지역",0)
    resi=sum(v for k,v in z.items() if ("주거" in k and "준주거" not in k))
    green=sum(v for k,v in z.items() if "녹지" in k); ind=sum(v for k,v in z.items() if "공업" in k)
    return [comm,junju,resi,green,ind, max(0,100-(comm+junju+resi+green+ind))]
zdata=np.array([zoning_group(land["pangyo"]), zoning_group(land["cheongna"])])
seg2=["상업지역","준주거지역","주거지역","녹지지역","공업지역","기타"]
cols2=[C,"#f59e0b",P,GREEN,GREY,LGREY]
fig, ax = newfig()
xx=np.arange(2); bottom=np.zeros(2)
for j in range(len(seg2)):
    ax.bar(xx, zdata[:,j], bottom=bottom, width=0.46, color=cols2[j], label=seg2[j], edgecolor="white", linewidth=1.2, zorder=3)
    for i in range(2):
        if zdata[i,j]>=5: ax.text(i, bottom[i]+zdata[i,j]/2, f"{zdata[i,j]:.0f}%", ha="center", va="center", color="white", fontsize=8.8, fontweight="bold")
    bottom+=zdata[:,j]
ax.set_xticks(xx); ax.set_xticklabels(["판교","청라"], fontsize=11); ax.set_xlim(-0.65,1.55); ax.set_ylim(0,100)
ax.set_ylabel("용도지역 면적 구성비 (%)", fontsize=AX); ax.grid(axis="x", visible=False)
ax.legend(loc="center left", bbox_to_anchor=(1.02,0.5), fontsize=9.3, frameon=False, title="용도지역")
title(ax, "용도지역 면적 구성비")
save(fig, "figA1_zoning.png")

# ---- 파생 수치(본문 검증용) ----
print("\n=== 파생 수치 ===")
print("FAR median P/C:", round(np.median(pfar),1), round(np.median(cfar),1), "n:", len(pfar), len(cfar))
print("상업 P/C:", round(zdata[0,0],1), round(zdata[1,0],1), "| 준주거 P/C:", round(zdata[0,1],1), round(zdata[1,1],1))
print("주거 P/C:", round(zdata[0,2],1), round(zdata[1,2],1))
print("DONE")
