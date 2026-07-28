#!/usr/bin/env python3
"""치유의숲 shapefile(EPSG:5179) -> WGS84 lat/lng 변환 + JSON 저장"""
import json
import re
from pathlib import Path
import shapefile
from pyproj import Transformer

ROOT = Path(__file__).parent.parent
SHP_DIR = ROOT / "_rawdata" / "healing_shp"
OUT_FILE = ROOT / "_rawdata" / "healing.json"

# EPSG:5179 (GRS80 UTM-K, Korea 2000) -> EPSG:4326 (WGS84)
transformer = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

FIELD_ORDER = ["seq", "region", "healingNm", "address", "phone", "homepage", "method", "manageType"]

DO_MAP = {
    "서울특별시": "서울", "서울": "서울",
    "부산광역시": "부산", "부산": "부산",
    "대구광역시": "대구", "대구": "대구",
    "인천광역시": "인천", "인천": "인천",
    "광주광역시": "광주", "광주": "광주",
    "대전광역시": "대전", "대전": "대전",
    "울산광역시": "울산", "울산": "울산",
    "세종특별자치시": "세종", "세종": "세종",
    "경기도": "경기", "경기": "경기",
    "강원특별자치도": "강원", "강원도": "강원", "강원": "강원",
    "충청북도": "충북", "충북": "충북",
    "충청남도": "충남", "충남": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전북": "전북",
    "전라남도": "전남", "전남": "전남",
    "경상북도": "경북", "경북": "경북",
    "경상남도": "경남", "경남": "경남",
    "제주특별자치도": "제주", "제주도": "제주", "제주": "제주",
}


def make_slug(name: str, seq) -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", name).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return f"{slug}-h{int(seq)}"


def extract_region_sigungu(address: str):
    parts = address.split()
    if len(parts) < 2:
        return "", ""
    sigungu = ""
    for p in parts[1:3]:
        if p.endswith(("시", "군", "구")):
            sigungu = p
            break
    return sigungu


def main():
    all_items = []
    shp_files = sorted(SHP_DIR.glob("*/*.shp"))
    for shp_path in shp_files:
        sf = shapefile.Reader(str(shp_path), encoding="cp949")
        for shaperec in sf.iterShapeRecords():
            values = list(shaperec.record)
            # values[0] is DeletionFlag-adjacent; pyshp record excludes DeletionFlag by default
            rec = dict(zip(FIELD_ORDER, values))
            x, y = shaperec.shape.points[0]
            lng, lat = transformer.transform(x, y)
            rec["latitude"] = round(lat, 6)
            rec["longitude"] = round(lng, 6)

            address = (rec.get("address") or "").strip()
            addr_do = address.split()[0] if address else ""
            rec["doShort"] = DO_MAP.get(addr_do, addr_do)
            rec["sigungu"] = extract_region_sigungu(address)
            rec["slug"] = make_slug(rec.get("healingNm") or "치유의숲", rec.get("seq") or len(all_items))

            all_items.append(rec)

    OUT_FILE.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"완료: {len(all_items)}개 치유의숲 -> {OUT_FILE}")

    from collections import Counter
    counts = Counter(i["doShort"] for i in all_items)
    for do, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {do}: {cnt}개")


if __name__ == "__main__":
    main()
