"""건축HUB 건축물대장 표제부(getBrTitleInfo) — 판교·청라 수집.

입력(코드 추출): CD/CD_AREA.dat (행안부 법정동코드, 파이프구분·헤더없음·UTF-8)
  - 판교 구역계=삼평동 → sigunguCd=41135(분당구), bjdongCd=10900(삼평동)
  - 청라 구역계=청라1~3동 → 단일 법정동 청라동 → sigunguCd=28260(서구), bjdongCd=12200(청라동)
기준: 건축HUB 표제부 현행(수집일 2026-06-20). 좌표 없음(PNU 기반).
공간단위: 건축물(점, PNU 19자리). 클립: 법정동 단위 전체 수집(정밀 구역클립은 STEP4 PNU↔필지 조인).
CRS: 해당 없음(좌표 미포함). PNU = sigunguCd(5)+bjdongCd(5)+platGbCd(1)+bun(4 zfill)+ji(4 zfill).

산출:
  02_data/raw/buildinghub/buildings_raw_{pangyo,cheongna}.json   원본 item 배열
  02_data/processed/buildings_pangyo.json, buildings_cheongna.json  정제 + PNU

재현: python fetch_buildinghub.py
"""

import json
import sys
import time
from collections import Counter
from pathlib import Path

# songpa fetch 클라이언트 재사용 (songpa/.env 자동 로드 → BUILDING_HUB_API_KEY)
FE = Path("C:/Users/USER/OneDrive/Desktop/시험준비/스마트시티입문/final_exam")
sys.path.insert(0, str(FE / "songpa-landuse-analysis" / "python" / "fetch"))
import buildinghub_client  # noqa: E402

PROJ = FE / "pangyo-cheongna-analysis"
RAW = PROJ / "02_data" / "raw" / "buildinghub"
PROC = PROJ / "02_data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 100  # 건축HUB 표제부 실질 한도 100건/페이지

# (지역명, sigunguCd, [(bjdongCd, 법정동명)])
REGIONS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("pangyo", "41135", [("10900", "삼평동")]),
    ("cheongna", "28260", [("12200", "청라동")]),
]


def build_pnu(row: dict) -> str | None:
    """건축HUB row → 19자리 PNU 조립."""
    try:
        plat_gb = row.get("platGbCd", "0") or "0"
        bun = (row.get("bun") or "0").zfill(4)
        ji = (row.get("ji") or "0").zfill(4)
        return f"{row['sigunguCd']}{row['bjdongCd']}{plat_gb}{bun}{ji}"
    except Exception:
        return None


def fetch_bjdong(sigungu: str, bjdong: str) -> list[dict]:
    """법정동 1개 전체 페이지네이션 수집 (totalCount까지)."""
    out: list[dict] = []
    page = 1
    total = None
    while True:
        body = buildinghub_client.title_info(sigungu, bjdong, page=page, rows=PAGE_SIZE)
        items = body["_items"]
        total = int(body.get("totalCount") or 0)
        out.extend(items)
        if not items or len(out) >= total or len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(0.15)  # API 예의
    return out


def clean_row(it: dict) -> dict | None:
    pnu = build_pnu(it)
    if pnu is None:
        return None
    return {
        "pnu": pnu,
        "bldNm": it.get("bldNm"),
        "platPlc": it.get("platPlc"),
        "mainPurpsCd": it.get("mainPurpsCd"),
        "mainPurpsCdNm": it.get("mainPurpsCdNm"),
        "totArea": it.get("totArea"),
        "archArea": it.get("archArea"),
        "grndFlrCnt": it.get("grndFlrCnt"),
        "ugrndFlrCnt": it.get("ugrndFlrCnt"),
        "useAprDay": it.get("useAprDay"),
        "sigunguCd": it.get("sigunguCd"),
        "bjdongCd": it.get("bjdongCd"),
        "platGbCd": it.get("platGbCd"),
        "bun": it.get("bun"),
        "ji": it.get("ji"),
    }


def to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def report(name: str, clean: list[dict]) -> None:
    n = len(clean)
    purps = Counter(c.get("mainPurpsCdNm") or "(미상)" for c in clean)
    tot_missing = sum(1 for c in clean if c.get("totArea") in (None, "", "0"))
    tot_sum = sum(to_float(c.get("totArea")) for c in clean)
    print(f"\n[{name}] 건수={n:,}")
    print(f"  totArea 합계={tot_sum:,.0f} m²  결측/0={tot_missing} ({tot_missing/n*100 if n else 0:.1f}%)")
    print("  주용도(mainPurpsCdNm) top10:")
    for nm, c in purps.most_common(10):
        print(f"    {c:>5,}  {nm}")


def main() -> None:
    for name, sigungu, bjdongs in REGIONS:
        raw_items: list[dict] = []
        for bjcd, bjnm in bjdongs:
            print(f"수집 {name} {sigungu}-{bjcd}({bjnm}) ...")
            items = fetch_bjdong(sigungu, bjcd)
            print(f"  → {len(items):,}건")
            raw_items.extend(items)

        clean = [c for c in (clean_row(it) for it in raw_items) if c is not None]

        (RAW / f"buildings_raw_{name}.json").write_text(
            json.dumps(raw_items, ensure_ascii=False), encoding="utf-8"
        )
        (PROC / f"buildings_{name}.json").write_text(
            json.dumps(clean, ensure_ascii=False), encoding="utf-8"
        )
        report(name, clean)

    print("\n완료. processed/buildings_pangyo.json, buildings_cheongna.json")


if __name__ == "__main__":
    main()
