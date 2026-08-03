#!/usr/bin/env python3
"""region/{시도}/index.html 프론트매터 페이지 생성"""
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent.parent
DATA = json.loads((ROOT / "_rawdata" / "forests.json").read_text(encoding="utf-8"))
HEALING = json.loads((ROOT / "_rawdata" / "healing.json").read_text(encoding="utf-8"))
ARBORETUM = json.loads((ROOT / "_rawdata" / "arboretum.json").read_text(encoding="utf-8"))

ICONS = {
    "서울": "🏙️", "경기": "🌾", "인천": "⚓", "강원": "🏔️", "충북": "🌲",
    "충남": "🌊", "대전": "🏛️", "세종": "🌿", "전북": "🌾", "전남": "🐚",
    "광주": "🎨", "경북": "🍎", "경남": "🎋", "부산": "🌅", "대구": "🍑",
    "울산": "🏭", "제주": "🌺",
}

FULLNAME = {
    "서울": "서울특별시", "경기": "경기도", "인천": "인천광역시", "강원": "강원특별자치도",
    "충북": "충청북도", "충남": "충청남도", "대전": "대전광역시", "세종": "세종특별자치시",
    "전북": "전북특별자치도", "전남": "전라남도", "광주": "광주광역시", "경북": "경상북도",
    "경남": "경상남도", "부산": "부산광역시", "대구": "대구광역시", "울산": "울산광역시",
    "제주": "제주특별자치도",
}

forest_counts = Counter(f["doShort"] for f in DATA)
healing_counts = Counter(h["doShort"] for h in HEALING)
arboretum_counts = Counter(a["doShort"] for a in ARBORETUM)
all_regions = set(forest_counts) | set(healing_counts) | set(arboretum_counts)

for region in sorted(all_regions):
    full = FULLNAME.get(region, region)
    icon = ICONS.get(region, "🌲")
    f_cnt = forest_counts.get(region, 0)
    h_cnt = healing_counts.get(region, 0)
    a_cnt = arboretum_counts.get(region, 0)
    d = ROOT / "region" / region
    d.mkdir(parents=True, exist_ok=True)

    if f_cnt > 0:
        page_title = f"{full} 자연휴양림"
        title_h1 = f"{full} 자연휴양림 {f_cnt}개"
        subtitle = f"{full} 지역 자연휴양림을 유형별, 숙박가능여부별로 검색하세요."
    elif a_cnt > 0:
        page_title = f"{full} 수목원·식물원"
        title_h1 = f"{full} 수목원·식물원 {a_cnt}개"
        subtitle = f"{full} 지역 수목원·식물원·치유의숲 정보를 확인하세요."
    else:
        page_title = f"{full} 치유의숲"
        title_h1 = f"{full} 치유의숲 {h_cnt}개"
        subtitle = f"{full} 지역 치유의숲 정보를 확인하세요."

    content = f"""---
layout: region
title: {page_title}
description: {full} 자연휴양림·수목원·치유의숲 정보. 위치, 이용요금, 시설, 숙박 가능 여부를 확인하세요.
do_name: {region}
title_h1: {title_h1}
subtitle: {subtitle}
---
"""
    (d / "index.html").write_text(content, encoding="utf-8")
    print(f"  {region} ({full}): 휴양림 {f_cnt} / 치유의숲 {h_cnt} / 수목원 {a_cnt}")

print(f"\n완료: {len(all_regions)}개 지역 페이지 생성")
