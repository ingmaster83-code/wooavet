#!/usr/bin/env python3
"""
process_data.py - data/vet_stores.json을 Jekyll 페이지 생성용 JSON으로 가공

입력: data/vet_stores.json ({"items":[{name,addr,tel,x,y,sido_nm,sggu_nm,permit_date}]})
출력: _rawdata/vet.json (병원 목록), search_index.json (검색용, 루트)

사용법:
  python scripts/process_data.py
"""
import json, re, hashlib, sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "vet_stores.json"
OUT = ROOT / "_rawdata" / "vet.json"
SEARCH_INDEX_OUT = ROOT / "search_index.json"


def make_slug(name: str, addr: str) -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", name).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    h = hashlib.md5(f"{name}|{addr}".encode("utf-8")).hexdigest()[:6]
    return f"{slug}-{h}" if slug else h


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8")).get("items", [])
    items = []
    seen_slugs = Counter()
    for d in raw:
        # 필드명 주의: Jekyll 내장 Page.name과 충돌하므로 "storeName" 사용
        store_name = (d.get("name") or "").strip()
        addr = (d.get("addr") or "").strip()
        do_short = (d.get("sido_nm") or "").strip()
        sigungu = (d.get("sggu_nm") or "").strip()
        if not store_name or not addr or not do_short:
            continue

        slug = make_slug(store_name, addr)
        seen_slugs[slug] += 1
        if seen_slugs[slug] > 1:
            slug = f"{slug}-{seen_slugs[slug]}"

        items.append({
            "storeName": store_name,
            "doShort": do_short,
            "sigungu": sigungu,
            "addr": addr,
            "tel": (d.get("tel") or "").strip(),
            "lat": (d.get("y") or "").strip(),
            "lng": (d.get("x") or "").strip(),
            "permitDate": (d.get("permit_date") or "").strip(),
            "slug": slug,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"동물병원 {len(items)}개 저장 → {OUT}")

    do_counts = Counter(i["doShort"] for i in items)
    print("\n지역별 수:")
    for do, cnt in sorted(do_counts.items(), key=lambda x: -x[1]):
        print(f"  {do}: {cnt}개")

    coord_count = sum(1 for i in items if i["lat"] and i["lng"])
    print(f"\n좌표 보유: {coord_count}개 / 주소만: {len(items)-coord_count}개")

    index = [
        {"n": i["storeName"], "slug": i["slug"], "doShort": i["doShort"], "sigungu": i["sigungu"]}
        for i in items
    ]
    SEARCH_INDEX_OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = SEARCH_INDEX_OUT.stat().st_size / 1024 / 1024
    print(f"\n검색 인덱스 {len(index)}건 저장 → {SEARCH_INDEX_OUT} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
