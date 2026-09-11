# -*- coding: utf-8 -*-
"""forest.html/healing.html/arboretum.html의 카드 렌더 함수(itemCard/recentCard/forestCard)에
'kidforest' kind 분기를 추가 — 안 하면 같은 지역/최근 본 목록에 유아숲체험원이 섞여 나올 때
엉뚱한 필드(rcrfrstNm 등 undefined)로 렌더링됨."""
from pathlib import Path

ROOT = Path(r"C:\개인\wooahouse\wooarest\_layouts")

KIDFOREST_BRANCH = """    if (f.kind === 'kidforest') {
      return `<a class="camp-card" href="/kidforest/${f.slug}/">
        <div class="camp-card-img-placeholder" style="background:linear-gradient(135deg,#fef3c7,#fde68a);">🧒</div>
        <div class="camp-card-body">
          <div class="camp-card-name">${f.kfName}</div>
          <div class="camp-card-loc">📍 ${f.sigungu || f.doShort || ''}</div>
          <div class="camp-card-tags"><span class="tag tag-env">🧒 유아숲체험원</span></div>
        </div>
      </a>`;
    }
"""

TARGETS = {
    "forest.html": ["recentCard"],
    "healing.html": ["itemCard", "recentCard"],
    "arboretum.html": ["itemCard", "recentCard"],
}


def patch_function(text, fn_name):
    anchor = f"function {fn_name}(f) {{\n"
    idx = text.find(anchor)
    if idx == -1:
        raise RuntimeError(f"anchor not found for {fn_name}")
    insert_at = idx + len(anchor)
    if "kind === 'kidforest'" in text[insert_at:insert_at + 400]:
        return text, "skip(already)"
    return text[:insert_at] + KIDFOREST_BRANCH + text[insert_at:], "ok"


def main():
    for fname, fns in TARGETS.items():
        p = ROOT / fname
        t = p.read_text(encoding="utf-8")
        results = []
        for fn in fns:
            t, r = patch_function(t, fn)
            results.append(f"{fn}:{r}")
        p.write_text(t, encoding="utf-8")
        print(f"{fname}: {', '.join(results)}")


if __name__ == "__main__":
    main()
