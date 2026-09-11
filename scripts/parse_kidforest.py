# -*- coding: utf-8 -*-
"""
_rawdata/kidforest_raw.csv (산림청_유아숲체험원 현황, CP949 CSV, 컬럼: 시설명/주소/운영기간/전화번호/참여방법)
-> 카카오 지오코딩 -> _rawdata/kidforest.json (wooarest 기존 forest.json 계열과 동일 스키마 스타일)

원본: https://www.data.go.kr/data/15081674/fileData.do (산림청, 499개소, 2026-09-03 수정)
다운로드: https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=FILE_000000003211347&fileDetailSn=1&insertDataPrcus=N

재실행 시 이미 지오코딩된 주소는 캐시(_rawdata/kidforest_geo_cache.json)로 건너뜀.
사용법: python scripts/parse_kidforest.py
"""
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "_rawdata" / "kidforest_raw.csv"
GEO_CACHE = ROOT / "_rawdata" / "kidforest_geo_cache.json"
OUT = ROOT / "_rawdata" / "kidforest.json"

KAKAO_REST_KEY = "02a25c9d9c8a834c12938e84a5235f6d"
KAKAO_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_HEADERS = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

REGION_ALIAS = {
    "경기도": "경기", "경기": "경기",
    "인천광역시": "인천", "인천": "인천",
    "강원특별자치도": "강원", "강원도": "강원", "강원": "강원",
    "충청북도": "충북", "충북": "충북",
    "충청남도": "충남", "충남": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전북": "전북",
    "전라남도": "전남", "전남": "전남",
    "경상북도": "경북", "경북": "경북",
    "경상남도": "경남", "경남": "경남",
    "대구광역시": "대구", "대구": "대구",
    "울산광역시": "울산", "울산": "울산",
    "부산광역시": "부산", "부산": "부산",
    "광주광역시": "광주", "광주": "광주",
    "세종특별자치시": "세종", "세종시": "세종", "세종": "세종",
    "대전광역시": "대전", "대전": "대전",
    "제주특별자치도": "제주", "제주도": "제주", "제주": "제주",
    "서울특별시": "서울", "서울": "서울",
}
GWANGJU_CITY_HINTS = ("동구", "서구", "남구", "북구", "광산구")


def normalize_region(addr):
    if not addr:
        return None
    first = addr.split()[0]
    if first == "전남광주통합특별시":
        tokens = addr.split()
        city_token = tokens[1] if len(tokens) > 1 else ""
        return "광주" if any(h in city_token for h in GWANGJU_CITY_HINTS) else "전남"
    return REGION_ALIAS.get(first)


def extract_city(addr):
    tokens = addr.split()
    return tokens[1] if len(tokens) >= 2 else ""


def search_kakao(query: str, attempt: int = 1) -> dict:
    try:
        resp = requests.get(KAKAO_SEARCH_URL, params={"query": query, "size": 1},
                             headers=KAKAO_HEADERS, timeout=15)
        if resp.status_code == 429:
            if attempt >= 5:
                return {}
            time.sleep(2 * attempt)
            return search_kakao(query, attempt + 1)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        return docs[0] if docs else {}
    except requests.exceptions.RequestException:
        if attempt >= 3:
            return {}
        time.sleep(1.5 * attempt)
        return search_kakao(query, attempt + 1)


def main():
    rows = list(csv.reader(RAW_CSV.read_text(encoding="cp949", errors="replace").splitlines()))
    header, data_rows = rows[0], rows[1:]
    print("header:", header)

    geo_cache = json.loads(GEO_CACHE.read_text(encoding="utf-8")) if GEO_CACHE.exists() else {}

    out = []
    region_seq = Counter()
    skipped = 0
    geocoded_now = 0

    for r in data_rows:
        if len(r) < 5:
            skipped += 1
            continue
        name, addr, period, phone, particip = (c.strip() for c in r[:5])
        if not name or not addr:
            skipped += 1
            continue

        region = normalize_region(addr)
        if not region:
            skipped += 1
            continue
        city = extract_city(addr)

        geo_query = re.sub(r"\s*\([^)]*\)\s*$", "", addr).strip() or addr
        if addr in geo_cache and geo_cache[addr].get("lat"):
            lat, lng = geo_cache[addr]["lat"], geo_cache[addr]["lng"]
        else:
            doc = search_kakao(geo_query)
            lat, lng = doc.get("y", ""), doc.get("x", "")
            if lat:
                geo_cache[addr] = {"lat": lat, "lng": lng}
                geocoded_now += 1
                if geocoded_now % 50 == 0:
                    print(f"  geocoded {geocoded_now}...")

        region_seq[region] += 1
        h = hashlib.md5(f"{name}|{addr}".encode("utf-8")).hexdigest()[:6]
        slug_base = re.sub(r"[^\w가-힣\s-]", "", name).strip()
        slug_base = re.sub(r"\s+", "-", slug_base) or "kf"
        slug = f"{slug_base}-{h}"

        out.append({
            "kfName": name,
            "doShort": region,
            "sigungu": city,
            "address": addr,
            "phone": phone,
            "operPeriod": period,
            "participWay": particip,
            "latitude": lat,
            "longitude": lng,
            "slug": slug,
        })

    GEO_CACHE.write_text(json.dumps(geo_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    geo_ok = sum(1 for o in out if o["latitude"])
    print(f"총 {len(data_rows)}건 중 {len(out)}개 저장, {skipped}개 스킵 -> {OUT}")
    print(f"좌표 확보: {geo_ok}/{len(out)} ({geo_ok*100//max(len(out),1)}%)")
    region_count = Counter(o["doShort"] for o in out)
    print("지역별:", dict(region_count))


if __name__ == "__main__":
    main()
