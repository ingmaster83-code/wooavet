"""
create_og_image.py — OG 이미지 생성 (1200x630)
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets"

BG        = (239, 246, 255)   # #EFF6FF  blue-50
ACCENT    = (37,  99,  235)   # #2563EB  primary
ACCENT2   = (59,  130, 246)   # #3B82F6  accent
DARK      = (17,  24,  39)
GRAY      = (107, 114, 128)
WHITE     = (255, 255, 255)

W, H = 1200, 630


def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothicBold.ttf",
        "C:/Windows/Fonts/NanumGothic.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + radius * 2, y0 + radius * 2], fill=fill)
    draw.ellipse([x1 - radius * 2, y0, x1, y0 + radius * 2], fill=fill)
    draw.ellipse([x0, y1 - radius * 2, x0 + radius * 2, y1], fill=fill)
    draw.ellipse([x1 - radius * 2, y1 - radius * 2, x1, y1], fill=fill)


def create_og_image():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.ellipse([820, -120, 1380, 440], fill=(191, 219, 254))
    draw.ellipse([900, 340, 1300, 740], fill=(147, 197, 253))

    draw_rounded_rect(draw, (60, 60, 72, 570), 6, ACCENT)

    badge_font = load_font(22, bold=True)
    badge_text = "지자체 인허가 공공데이터"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0] + 32
    bh = bbox[3] - bbox[1] + 14
    draw_rounded_rect(draw, (100, 110, 100 + bw, 110 + bh), 8, ACCENT)
    draw.text((116, 117), badge_text, fill=WHITE, font=badge_font)

    title_font = load_font(72, bold=True)
    title1 = "우리 동네"
    title2 = "동물병원 찾기"
    draw.text((100, 178), title1, fill=DARK, font=title_font)
    draw.text((100, 268), title2, fill=ACCENT2, font=title_font)

    sub_font = load_font(32)
    draw.text((100, 390), "위치·전화번호 바로 확인하는 전국 동물병원", fill=GRAY, font=sub_font)

    icon_font = load_font(26, bold=True)
    boxes = [
        ("전국 5,468곳", ACCENT2),
        ("영업중만 표시", (21, 128, 61)),
        ("지도 바로보기", (180, 83, 9)),
    ]
    cx, y = 100, 456
    for label, color in boxes:
        lbbox = draw.textbbox((0, 0), label, font=icon_font)
        lw = lbbox[2] - lbbox[0]
        bw = lw + 36
        draw_rounded_rect(draw, (cx, y, cx + bw, y + 50), 10, color)
        draw.text((cx + 18, y + 11), label, fill=WHITE, font=icon_font)
        cx += bw + 14

    domain_font = load_font(30, bold=True)
    draw.text((100, 550), "wooavet.wooahouse.com", fill=ACCENT, font=domain_font)

    ASSETS_DIR.mkdir(exist_ok=True)
    out = ASSETS_DIR / "og-image.png"
    img.save(str(out), "PNG", optimize=True)
    print(f"OG image created: {out} ({W}x{H})")


if __name__ == "__main__":
    create_og_image()
