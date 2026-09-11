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


def eun_neun(word: str) -> str:
    """받침 유무에 따라 은/는 선택."""
    if not word:
        return "는"
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return "는"
    jong = (ord(last) - ord("가")) % 28
    return "는" if jong == 0 else "은"


def ro_euro(word: str) -> str:
    """받침 유무(+ㄹ받침)에 따라 로/으로 선택."""
    if not word:
        return "으로"
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return "으로"
    jong = (ord(last) - ord("가")) % 28
    return "로" if jong in (0, 8) else "으로"  # 0=받침없음, 8=ㄹ받침


def period_sentence(period: str) -> str:
    period = (period or "").strip()
    if not period:
        return ""
    if "미운영" in period:
        return "올해는 운영하지 않는 것으로 확인됩니다. 재개 여부는 아래 연락처로 문의하세요."
    if period == "연중":
        return "연중 운영합니다."
    m = re.match(r"\d{4}-(\d{2})~\d{4}-(\d{2})", period)
    if m:
        m1, m2 = int(m.group(1)), int(m.group(2))
        if m1 == 1 and m2 == 12:
            return "연중 운영합니다."
        return f"{m1}월부터 {m2}월까지 운영합니다."
    return f"운영기간은 {period}입니다."


def particip_sentence(participway: str) -> str:
    p = (participway or "").strip()
    if not p or "미운영" in p:
        return ""
    parts = [x.strip() for x in re.split(r"[/,]", p) if x.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return f"참여 신청은 {parts[0]}{ro_euro(parts[0])} 할 수 있습니다."
    joined = ", ".join(parts)
    return f"참여 신청은 {joined} 등으로 할 수 있습니다."


def build_intro(k: dict, sido_count: int, sigungu_count: int, siblings: dict) -> str:
    name = k["kfName"]
    sido, sigungu = k["doShort"], k["sigungu"]
    loc = f"{sido} {sigungu}" if sigungu else sido
    sentences = [f"{name}{eun_neun(name)} {loc}에 있는 유아숲체험원입니다."]

    ps = period_sentence(k["operPeriod"])
    if ps:
        sentences.append(ps)

    ps2 = particip_sentence(k["participWay"])
    if ps2:
        sentences.append(ps2)

    if sigungu_count == 1:
        sentences.append(f"{sigungu}에는 유아숲체험원이 이곳 하나뿐입니다.")
    elif sigungu_count > 1:
        sentences.append(f"{sido}에는 유아숲체험원이 총 {sido_count}곳 있으며, {sigungu}에는 이곳을 포함해 {sigungu_count}곳이 있습니다.")
    else:
        sentences.append(f"{sido}에는 유아숲체험원이 총 {sido_count}곳 있습니다.")

    sib_parts = []
    for label, cnt in siblings.items():
        if cnt > 0:
            sib_parts.append(f"{label} {cnt}곳")
    if sib_parts:
        sentences.append(f"{sido} 지역에는 " + ", ".join(sib_parts) + "도 있어 함께 둘러볼 수 있습니다.")

    return " ".join(sentences)


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

    # --- introText 생성: 지역 집계 + 형제 카테고리(자연휴양림/치유의숲/수목원) 개수 ---
    sido_count = Counter(o["doShort"] for o in out)
    sigungu_count = Counter((o["doShort"], o["sigungu"]) for o in out)

    def load_sibling(fname):
        p = ROOT / "_rawdata" / fname
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    forests = load_sibling("forests.json")
    healings = load_sibling("healing.json")
    arboretums = load_sibling("arboretum.json")
    forest_by_sido = Counter(f.get("doShort") for f in forests)
    healing_by_sido = Counter(h.get("doShort") for h in healings)
    arb_by_sido = Counter(a.get("doShort") for a in arboretums)

    for o in out:
        siblings = {
            "자연휴양림": forest_by_sido.get(o["doShort"], 0),
            "치유의숲": healing_by_sido.get(o["doShort"], 0),
            "수목원": arb_by_sido.get(o["doShort"], 0),
        }
        o["introText"] = build_intro(
            o, sido_count[o["doShort"]], sigungu_count[(o["doShort"], o["sigungu"])], siblings
        )

    GEO_CACHE.write_text(json.dumps(geo_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    geo_ok = sum(1 for o in out if o["latitude"])
    print(f"총 {len(data_rows)}건 중 {len(out)}개 저장, {skipped}개 스킵 -> {OUT}")
    print(f"좌표 확보: {geo_ok}/{len(out)} ({geo_ok*100//max(len(out),1)}%)")
    region_count = Counter(o["doShort"] for o in out)
    print("지역별:", dict(region_count))


if __name__ == "__main__":
    main()
