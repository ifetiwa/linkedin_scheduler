#!/usr/bin/env python3
"""
Generate LinkedIn share-card PNGs from a slug + headline + accent color.

Output size: 1200×630 (LinkedIn link-preview standard).
Run: python generate_post_images.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

W, H = 1200, 630

# (slug, title, accent_color, badge_label)
POSTS = [
    ("post13_cicd_pipeline",   "Building a CI/CD pipeline\nthat saves 4 hours/week",          "#2563EB", "DEVOPS"),
    ("post14_microservices",   "Microservices vs Monolith:\nwhen I pick each",                "#0EA5E9", "ARCHITECTURE"),
    ("post15_react_bundle",    "How I cut React bundle\nsize by 62%",                         "#10B981", "PERFORMANCE"),
    ("post16_hiring_seniors",  "5 questions before hiring\na senior developer",               "#F59E0B", "LEADERSHIP"),
    ("post17_multi_tenant",    "Building multi-tenant SaaS:\nthe 3 hardest decisions",        "#7C3AED", "SAAS"),
    ("post18_owasp",           "The OWASP Top 10\nevery full-stack dev should know",          "#EF4444", "SECURITY"),
    ("post19_integration_first","Why I write integration\ntests before unit tests",           "#EC4899", "TESTING"),
    ("post20_db_indexing",     "Database indexing:\na practical guide for app devs",          "#14B8A6", "BACKEND"),
    ("post21_graphql_vs_rest", "GraphQL vs REST in 2026:\na pragmatic take",                  "#6366F1", "API"),
    ("post22_standup",         "A standup that doesn't\nwaste 30 minutes",                    "#F97316", "LEADERSHIP"),
    ("post23_web_vitals",      "Web Vitals: the only 3\nmetrics I optimize for",              "#06B6D4", "PERFORMANCE"),
    ("post24_typescript",      "TypeScript: 3 patterns\nI now use every day",                 "#3178C6", "TYPESCRIPT"),
    ("post25_code_reviews",    "Code reviews that\ndon't hurt",                                "#A855F7", "LEADERSHIP"),
]

# ─── Font loading (graceful fallback) ─────────────────────────────────────────

def _font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def darker(rgb, factor=0.55):
    return tuple(max(0, int(c * factor)) for c in rgb)


def make_card(slug, title, accent, badge_label):
    accent_rgb = hex_to_rgb(accent)
    bg_top = darker(accent_rgb, 0.18)       # near-black with accent tint
    bg_bot = (15, 23, 42)                    # slate-900

    img = Image.new("RGB", (W, H), bg_top)
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(H):
        t = y / H
        r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Accent bar (left side)
    draw.rectangle([(0, 0), (16, H)], fill=accent_rgb)

    # Decorative dot pattern (top-right)
    for row in range(6):
        for col in range(8):
            cx = W - 80 - col * 24
            cy = 80 + row * 24
            opacity = max(40, 200 - (row + col) * 15)
            draw.ellipse([(cx - 2, cy - 2), (cx + 2, cy + 2)],
                         fill=(*accent_rgb, opacity) if False else accent_rgb)

    # Badge label (top)
    badge_font = _font(22, bold=True)
    badge_x, badge_y = 80, 80
    bbox = draw.textbbox((badge_x, badge_y), badge_label, font=badge_font)
    pad_x, pad_y = 18, 10
    draw.rounded_rectangle(
        [(bbox[0] - pad_x, bbox[1] - pad_y), (bbox[2] + pad_x, bbox[3] + pad_y)],
        radius=8, fill=accent_rgb,
    )
    draw.text((badge_x, badge_y), badge_label, font=badge_font, fill="white")

    # Title (main)
    title_font = _font(64, bold=True)
    lines = title.split("\n")
    line_height = 80
    total_h = line_height * len(lines)
    start_y = (H - total_h) // 2 + 30
    for i, line in enumerate(lines):
        draw.text((80, start_y + i * line_height), line, font=title_font, fill="white")

    # Author footer
    author_font = _font(22)
    handle_font = _font(20)
    draw.text((80, H - 90), "Tiwa Elegbeleye", font=author_font, fill="white")
    draw.text((80, H - 60), "Senior Full Stack Developer · Cybersecurity Engineer",
              font=handle_font, fill=(180, 200, 220))

    # Accent corner mark (bottom-right)
    draw.rectangle([(W - 60, H - 60), (W - 30, H - 30)], fill=accent_rgb)
    draw.rectangle([(W - 30, H - 60), (W - 10, H - 30)], fill=darker(accent_rgb, 0.7))

    out = IMAGES_DIR / f"{slug}.png"
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    for slug, title, accent, badge in POSTS:
        path = make_card(slug, title, accent, badge)
        print(f"  [ok] {path.name}")
    print(f"\nGenerated {len(POSTS)} images in {IMAGES_DIR}")
