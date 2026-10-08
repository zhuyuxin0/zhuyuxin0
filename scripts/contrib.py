"""Draw the last year's contribution calendar as an isometric city, light and dark.

    python scripts/contrib.py                 # read github.com/users/zhuyuxin0/contributions
    python scripts/contrib.py --html FILE     # or a saved copy of that page

It reads the public calendar, so it shows what any visitor already sees: daily levels,
never repository names. Exits 1 without writing if the page does not parse.
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = "zhuyuxin0"
TABLE = json.loads((ROOT / "scripts" / "glyphs.json").read_text(encoding="utf-8"))

W, H = 880, 330
WEEK, DAY = (12.6, 2.6), (-9.5, 8.5)  # screen vectors along a week and along a day
HEIGHTS = (1.5, 13, 28, 46, 68)
INSET = 0.82
RAMP = {
    "light": ("#e6e0d4", "#e3c2b6", "#cf897b", "#ae463c", "#8b1a1a"),
    "dark": ("#262119", "#4c2824", "#7d3832", "#ae473f", "#d85b53"),
}


def fetch() -> str:
    req = urllib.request.Request(
        f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "contrib.py"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def parse(page: str) -> tuple[list[tuple[date, int]], str]:
    cells = []
    for tag in re.findall(r"<td\b[^>]*>", page):
        when = re.search(r'data-date="(\d{4}-\d\d-\d\d)"', tag)
        level = re.search(r'data-level="([0-4])"', tag)
        if when and level:
            cells.append((date.fromisoformat(when.group(1)), int(level.group(1))))
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    total = re.search(r"([\d,]+) contributions? in the last year", text)
    if len(cells) < 300 or not total:
        sys.exit(f"calendar did not parse: {len(cells)} cells, total {'found' if total else 'missing'}")
    return sorted(cells), total.group(1)


def shade(hex_colour: str, k: float) -> str:
    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c * k):02x}" for c in (r, g, b))


def label(text: str, size: float, x: float, y: float) -> str:
    k, out = size / 1000, []
    for ch in text:
        g = TABLE["glyphs"][ch]
        if g["d"]:
            out.append(f'<path transform="translate({x:.1f} {y:.1f}) scale({k})" d="{g["d"]}"/>')
        x += g["advance"] * k
    return "".join(out)


def draw(cells: list[tuple[date, int]], total: str, theme: str) -> str:
    t, ramp = TABLE["themes"][theme], RAMP[theme]
    start = cells[0][0]
    first_sunday = start.toordinal() - (start.isoweekday() % 7)
    grid = [((d.toordinal() - first_sunday) // 7, d.isoweekday() % 7, lv) for d, lv in cells]
    ox, oy = 141, 86
    rows = []
    # Far to near: screen depth grows down the page, more steeply along a day.
    for i, j, lv in sorted(grid, key=lambda c: (c[0] * WEEK[1] + c[1] * DAY[1], c[0])):
        x, y = ox + i * WEEK[0] + j * DAY[0], oy + i * WEEK[1] + j * DAY[1]
        h, top = HEIGHTS[lv], ramp[lv]
        g = (1 - INSET) / 2  # a gap around each day, so the grid reads as towers
        p = [
            (x + (WEEK[0] * a + DAY[0] * b), y + (WEEK[1] * a + DAY[1] * b))
            for a, b in ((g, g), (1 - g, g), (1 - g, 1 - g), (g, 1 - g))
        ]
        up = [(a, b - h) for a, b in p]
        faces = (
            (top, up),
            (shade(top, 0.86), [up[1], up[2], p[2], p[1]]),
            (shade(top, 0.72), [up[3], up[2], p[2], p[3]]),
        )
        polys = "".join(
            f'<path fill="{c}" d="M{"L".join(f"{a:.1f} {b:.1f}" for a, b in pts)}Z"/>' for c, pts in faces
        )
        rows.append(f'<g class="b d{i + j}">{polys}</g>')
    delays = "".join(f".d{n} {{ animation-delay: {0.2 + n * 0.022:.3f}s; }}" for n in range(60))
    style = (
        "<style>.b { transform-box: fill-box; transform-origin: 50% 100%;"
        " animation: grow .9s cubic-bezier(.2,.8,.2,1) both; }"
        " @keyframes grow { from { transform: scaleY(.03); } } "
        + delays
        + " @media (prefers-reduced-motion: reduce) { * { animation: none !important; } }</style>"
    )
    caption = label(f"{total} contributions in the last year", 11, 28, H - 24)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img"><title>{total} contributions in the last year, drawn as one bar per day</title>'
        f'{style}<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}" '
        f'stroke="{t["line"]}"/>{"".join(rows)}<g fill="{t["faint"]}">{caption}</g></svg>\n'
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path)
    args = ap.parse_args()
    page = args.html.read_text(encoding="utf-8") if args.html else fetch()
    cells, total = parse(page)
    for theme in ("light", "dark"):
        (ROOT / "assets" / f"contrib-{theme}.svg").write_text(draw(cells, total, theme), encoding="utf-8")
    print(f"{len(cells)} days, {total} contributions")


if __name__ == "__main__":
    main()
