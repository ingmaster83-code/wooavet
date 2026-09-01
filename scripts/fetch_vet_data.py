"""
wooavet 동물병원 데이터 수집 스크립트
행정안전부_동물_동물병원 데이터(전국 지자체 인허가 정보 취합)를
localdata.go.kr에서 CSV로 내려받아 data/vet_stores.json으로 정규화한다.

원본 데이터 특징 (hosppass 안전상비의약품과 동일 패턴):
- 인허가 이력 데이터라 폐업/취소/휴업 건도 섞여 있음 → 영업상태명 "영업/정상"만 필터링
- 좌표계가 WGS84가 아니라 Bessel 중부원점 TM(EPSG:5174) → pyproj로 위경도 변환 필요
- CP949(EUC-KR) 인코딩, Content-Type 헤더는 UTF-8이라고 잘못 표기됨(무시할 것)

실행: python scripts/fetch_vet_data.py
"""
import csv
import io
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import requests
from pyproj import Transformer

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
RAW_PATH = DATA_DIR / "animal_hospitals_raw.csv"
OUT_PATH = DATA_DIR / "vet_stores.json"

DOWNLOAD_URL = "https://file.localdata.go.kr/file/download/animal_hospitals/info"
DETAIL_URL = "https://file.localdata.go.kr/file/animal_hospitals/info"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": DETAIL_URL,
}

OPEN_STATUS = "영업/정상"

SIDO_PREFIXES = [
    ("서울특별시", "서울"), ("부산광역시", "부산"), ("인천광역시", "인천"),
    ("대구광역시", "대구"), ("광주광역시", "광주"), ("대전광역시", "대전"),
    ("울산광역시", "울산"), ("세종특별자치시", "세종"),
    ("경기도", "경기"),
    ("강원특별자치도", "강원"), ("강원도", "강원"),
    ("충청북도", "충북"), ("충청남도", "충남"),
    ("전북특별자치도", "전북"), ("전라북도", "전북"), ("전라남도", "전남"),
    ("경상북도", "경북"), ("경상남도", "경남"),
    ("제주특별자치도", "제주"), ("제주도", "제주"),
]


def guess_sido_sggu(addr: str):
    text = addr or ""
    # "전남광주통합특별시" — 광주+전남 통합 행정구역명. 시군구명이 "구"로 끝나면
    # (광주 자치구: 동/서/남/북/광산구) 광주, 그 외(전남 시/군)는 전남으로 재분류.
    UNIFIED_PREFIX = "전남광주통합특별시"
    if text.startswith(UNIFIED_PREFIX):
        rest = text[len(UNIFIED_PREFIX):].strip()
        sggu = rest.split()[0] if rest else ""
        short = "광주" if sggu.endswith("구") else "전남"
        return short, sggu
    for prefix, short in SIDO_PREFIXES:
        if text.startswith(prefix):
            rest = text[len(prefix):].strip()
            sggu = rest.split()[0] if rest else ""
            return short, sggu
    return "", ""


def download():
    resp = requests.get(DOWNLOAD_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    if len(resp.content) < 100_000:
        raise SystemExit(
            f"다운로드 실패로 추정 — 응답 크기가 너무 작음 ({len(resp.content)} bytes). "
            f"localdata.go.kr 다운로드 URL이 바뀌었을 수 있음 — 브라우저로 "
            f"{DETAIL_URL} 방문 후 다운로드 버튼의 실제 요청을 다시 확인할 것."
        )
    DATA_DIR.mkdir(exist_ok=True)
    RAW_PATH.write_bytes(resp.content)
    print(f"다운로드 완료: {RAW_PATH} ({len(resp.content):,} bytes)")


def parse():
    with open(RAW_PATH, encoding="cp949", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def main():
    if not RAW_PATH.exists():
        print("원본 CSV 없음 — 다운로드 시도")
        download()

    rows = parse()
    print(f"총 {len(rows):,}건 파싱 완료 (폐업·취소·휴업 포함)")
    print(f"컬럼: {list(rows[0].keys()) if rows else '(없음)'}")

    open_rows = [r for r in rows if r.get("영업상태명", "").strip() == OPEN_STATUS]
    print(f"영업중({OPEN_STATUS}) {len(open_rows):,}건")

    transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

    records = []
    skipped_coord = 0
    skipped_region = 0
    for r in open_rows:
        name = (r.get("사업장명") or "").strip()
        addr = (r.get("도로명주소") or r.get("지번주소") or "").strip()
        if not name or not addr:
            continue

        sido, sggu = guess_sido_sggu(addr)
        if not sido or not sggu:
            skipped_region += 1
            continue

        x_raw = (r.get("좌표정보(X)") or "").strip()
        y_raw = (r.get("좌표정보(Y)") or "").strip()
        lat = lng = ""
        if x_raw and y_raw:
            try:
                lng_v, lat_v = transformer.transform(float(x_raw), float(y_raw))
                lat, lng = str(lat_v), str(lng_v)
            except (ValueError, TypeError):
                skipped_coord += 1
        else:
            skipped_coord += 1

        records.append({
            "name": name,
            "addr": addr,
            "tel": (r.get("전화번호") or "").strip(),
            "x": lng,
            "y": lat,
            "sido_nm": sido,
            "sggu_nm": sggu,
            "permit_date": (r.get("인허가일자") or "").strip(),
        })

    print(f"좌표 없음/변환 실패 {skipped_coord:,}건 / 지역 매칭 실패 {skipped_region:,}건")
    print(f"최종 저장 {len(records):,}건")

    if OUT_PATH.exists():
        existing = json.loads(OUT_PATH.read_text(encoding="utf-8")).get("items", [])
        if existing and len(records) < len(existing) * 0.5:
            raise SystemExit(
                f"수집 건수({len(records)}건)가 기존 데이터({len(existing)}건)의 절반 미만입니다. "
                "다운로드 오류로 판단하여 저장을 중단합니다."
            )

    DATA_DIR.mkdir(exist_ok=True)
    OUT_PATH.write_text(
        json.dumps({"items": records}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
