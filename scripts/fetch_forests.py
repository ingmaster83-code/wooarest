#!/usr/bin/env python3
"""
fetch_forests.py - 전국휴양림표준데이터에서 전체 자연휴양림 데이터 수집

사용법:
  python scripts/fetch_forests.py
"""
import sys, json, time, os, re
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding='utf-8')

API_KEY  = os.environ.get("FOREST_API_KEY", "")
BASE_URL = "https://api.data.go.kr/openapi/tn_pubr_public_rcrfrst_api"
OUT_FILE = Path(__file__).parent.parent / "_rawdata" / "forests.json"
DELAY    = 0.2

# 시도명 정규화 (표준명 → 짧은 이름 폴더/파일에 쓸 키)
DO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주",
}


def fetch_page(page: int, rows: int = 100) -> dict:
    params = {
        "serviceKey": API_KEY,
        "pageNo": page,
        "numOfRows": rows,
        "type": "json",
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def make_slug(name: str, inst_code: str) -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", name).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return f"{slug}-{inst_code}"


def extract_sigungu(rdnmadr: str, do_name: str) -> str:
    """도로명주소에서 시/군/구 추출"""
    if not rdnmadr:
        return ""
    parts = rdnmadr.split()
    if len(parts) < 2:
        return ""
    # 첫 토큰은 보통 시/도 전체명, 두번째가 시/군/구
    candidate = parts[1] if parts[0] not in (do_name,) or len(parts) > 1 else parts[0]
    for p in parts[1:3]:
        if p.endswith(("시", "군", "구")):
            return p
    return parts[1] if len(parts) > 1 else ""


def main():
    if not API_KEY:
        print("오류: FOREST_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    print("=== 전국휴양림표준데이터 수집 시작 ===")
    first = fetch_page(1, 1)
    total = int(first["response"]["body"]["totalCount"])
    rows_per_page = 100
    total_pages = (total + rows_per_page - 1) // rows_per_page
    print(f"총 휴양림 수: {total}개 / {total_pages}페이지")

    all_items = []
    for page in range(1, total_pages + 1):
        try:
            data = fetch_page(page, rows_per_page)
            items = data["response"]["body"]["items"]
            if isinstance(items, dict):
                items = [items]
            all_items.extend(items)
            print(f"  페이지 {page}/{total_pages}: {len(items)}개 (누적 {len(all_items)})")
            time.sleep(DELAY)
        except Exception as e:
            print(f"  [오류] 페이지 {page}: {e}")
            time.sleep(1)

    # 후처리: 시도 정규화, 시군구 추출, 슬러그 생성
    for item in all_items:
        do_raw = item.get("ctprvnNm", "")
        item["doShort"] = DO_MAP.get(do_raw, do_raw)
        item["sigungu"] = extract_sigungu(item.get("rdnmadr", ""), do_raw)
        item["slug"] = make_slug(item.get("rcrfrstNm", "휴양림"), item.get("insttCode", str(len(all_items))))

    if OUT_FILE.exists():
        existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        if len(all_items) < len(existing) * 0.5:
            raise SystemExit(
                f"수집 건수({len(all_items)}건)가 기존 데이터({len(existing)}건)의 절반 미만입니다. "
                "API 오류로 판단하여 저장을 중단합니다."
            )

    OUT_FILE.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n완료: {OUT_FILE}")
    print(f"  총 {len(all_items)}개 휴양림 저장")

    from collections import Counter
    do_counts = Counter(i["doShort"] for i in all_items)
    print("\n지역별 수:")
    for do, cnt in sorted(do_counts.items(), key=lambda x: -x[1]):
        print(f"  {do}: {cnt}개")


if __name__ == "__main__":
    main()
