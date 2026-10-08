"""Draw the profile's images, with every word outlined so it renders the same everywhere.

    python scripts/build.py --fonts DIR --icons DIR [--stack colour|ink]

--fonts holds the OFL fonts from github.com/google/fonts: InstrumentSerif-Italic.ttf,
InterTight[wght].ttf and JetBrainsMono[wght].ttf. --icons is the icons/ folder of the
simple-icons npm package (CC0), with data/simple-icons.json beside it. Neither is
committed; only the drawings are. Also writes scripts/glyphs.json, which contrib.py uses
to label the calendar without fonts.
"""

import argparse
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

THEMES = {
    "light": dict(
        bg="#f4f1ea",
        deep="#ebe6dc",
        line="#e2dccf",
        ink="#1a1814",
        dim="#6b6457",
        faint="#8f8676",
        accent="#8b1a1a",
    ),
    "dark": dict(
        bg="#15120e",
        deep="#201c16",
        line="#2c2720",
        ink="#efe9de",
        dim="#b5ac9c",
        faint="#8f8676",
        accent="#c4524d",
    ),
}

REDUCED = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"

# The tools the public and private repositories use, read from their languages and
# dependency files on 8 Oct 2026. Simple Icons slug, then the name shown.
STACK = [
    (
        "Languages",
        [
            ("python", "Python"),
            ("typescript", "TypeScript"),
            ("javascript", "JavaScript"),
            ("rust", "Rust"),
            ("solidity", "Solidity"),
            ("gnubash", "Bash"),
            ("latex", "LaTeX"),
            ("html5", "HTML"),
            ("css", "CSS"),
        ],
    ),
    (
        "Interfaces",
        [
            ("react", "React"),
            ("nextdotjs", "Next.js"),
            ("vite", "Vite"),
            ("tailwindcss", "Tailwind"),
            ("threedotjs", "Three.js"),
            ("d3", "D3"),
        ],
    ),
    (
        "Data and ML",
        [
            ("numpy", "NumPy"),
            ("pandas", "pandas"),
            ("pytorch", "PyTorch"),
            ("scikitlearn", "scikit-learn"),
            ("scipy", "SciPy"),
            ("jupyter", "Jupyter"),
            ("plotly", "Plotly"),
            ("huggingface", "Hugging Face"),
        ],
    ),
    (
        "Systems",
        [
            ("fastapi", "FastAPI"),
            ("nodedotjs", "Node.js"),
            ("docker", "Docker"),
            ("linux", "Linux"),
            ("githubactions", "Actions"),
            ("googlecloud", "Google Cloud"),
            ("git", "Git"),
        ],
    ),
    (
        "Chains, tests",
        [
            ("solana", "Solana"),
            ("ethereum", "Ethereum"),
            ("pytest", "pytest"),
            ("vitest", "Vitest"),
            ("ruff", "Ruff"),
        ],
    ),
]

# A rotary harmonograph: two damped pendulums at nearly 1:2 while the paper turns slowly.
PENDULA = ((1.0, math.pi / 2, 0.004), (2.003, 0.0, 0.004))
ROTATION = 0.002


def num(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


class Face:
    def __init__(self, path: Path, wght: float | None = None):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet(location={"wght": wght} if wght else None)
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
        if wght:
            self.hb.set_variations({"wght": wght})

    def run(self, text: str, size: float, tracking: float = 0.0):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        k = size / self.upem
        out, x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
            out.append((self.order[info.codepoint], x + pos.x_offset * k, pos.y_offset * k))
            x += pos.x_advance * k + tracking
        return out, x - tracking, k

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        return self.run(text, size, tracking)[1]

    def path(self, text: str, size: float, x: float, y: float, anchor="start", tracking: float = 0.0) -> str:
        glyphs, w, k = self.run(text, size, tracking)
        x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
        pen = SVGPathPen(self.glyphs, ntos=num)
        for name, gx, gy in glyphs:
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x0 + gx, y - gy)))
        return pen.getCommands()


def svg(w: float, h: float, label: str, body: str, style: str = "") -> str:
    css = f"<style>{style} {REDUCED}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" '
        f'viewBox="0 0 {num(w)} {num(h)}" role="img"><title>{escape(label)}</title>{css}{body}</svg>\n'
    )


def card(w: float, h: float, t: dict) -> str:
    return (
        f'<rect x="0.5" y="0.5" width="{num(w - 1)}" height="{num(h - 1)}" rx="14" '
        f'fill="{t["bg"]}" stroke="{t["line"]}"/>'
    )


def harmonograph(cx: float, cy: float, r: float) -> str:
    (fx, px, dx), (fy, py, dy) = PENDULA
    pts = []
    for n in range(0, 7500):
        t = n * 0.04
        x, y = math.sin(fx * t + px) * math.exp(-dx * t), math.sin(fy * t + py) * math.exp(-dy * t)
        a = ROTATION * t
        pts.append(
            f"{cx + r * (x * math.cos(a) - y * math.sin(a)):.1f} "
            f"{cy + r * (x * math.sin(a) + y * math.cos(a)):.1f}"
        )
    return "M" + "L".join(pts)


def hero(f: dict, t: dict) -> str:
    w, h = 880, 300
    cx, cy, r = 708, 144, 100
    lines = ("Building systems", "that prove things.")
    tag = "".join(f["serif"].path(line, 48, 52, 112 + i * 54) for i, line in enumerate(lines))
    fields = "energy markets · formal verification · physics-informed ML · interfaces"
    ticks = "".join(
        f'<path d="M{num(cx + dx)} {num(cy + r + 14)}v4M{num(cx - r - 18)} {num(cy + dx)}h4"/>'
        for dx in range(-112, 113, 28)
    )
    note = f["mono"].path("x, y = sin(f·t + φ) · e^(−λ·t), turning", 9.5, cx, 286, "middle")
    axes = f"M{cx - r - 6} {cy}H{cx + r + 6}M{cx} {cy - r - 6}V{cy + r + 6}"
    body = (
        card(w, h, t) + f'<path class="tag" pathLength="1" fill="{t["ink"]}" stroke="{t["ink"]}" '
        f'stroke-width="0.8" d="{tag}"/>'
        + f'<path class="fields" fill="{t["dim"]}" d="{f["mono"].path(fields, 11, 54, 222)}"/>'
        + f'<g class="axes" stroke="{t["line"]}" stroke-width="1"><path d="{axes}"/>{ticks}</g>'
        + f'<path class="curve" pathLength="1" fill="none" stroke="{t["accent"]}" stroke-width="0.6" '
        f'stroke-opacity="0.85" d="{harmonograph(cx, cy, r)}"/>'
        + f'<path class="note" fill="{t["faint"]}" d="{note}"/>'
    )
    style = (
        ".tag { stroke-dasharray: 1 1; stroke-opacity: 0;"
        " animation: draw 2s ease-in-out .2s both, ink .8s ease 1.7s both; }"
        "@keyframes draw { 0% { stroke-dashoffset: 1; stroke-opacity: 1; }"
        " 85% { stroke-dashoffset: 0; stroke-opacity: 1; } 100% { stroke-opacity: 0; } }"
        "@keyframes ink { from { fill-opacity: 0; } to { fill-opacity: 1; } }"
        ".curve { stroke-dasharray: 1 1; animation: trace 5.5s cubic-bezier(.3,.1,.3,1) .4s both; }"
        "@keyframes trace { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }"
        ".fields, .axes, .note { animation: fade 1s ease 1.9s both; }"
        "@keyframes fade { from { opacity: 0; } }"
    )
    return svg(
        w,
        h,
        "Building systems that prove things: energy markets, formal verification, "
        "physics-informed ML, interfaces",
        body,
        style,
    )


def luminance(hex_colour: str) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def stack(f: dict, t: dict, icons: dict, variant: str) -> str:
    w, pitch, row_h, x0, top = 880, 72, 94, 196, 34
    h = top + len(STACK) * row_h + 10
    parts, k = [card(w, h, t)], 0
    for r, (label, tools) in enumerate(STACK):
        y = top + r * row_h
        heading = f["label"].path(label.upper(), 9.5, 48, y + 29, tracking=1.4)
        parts.append(f'<path fill="{t["faint"]}" d="{heading}"/>')
        for i, (slug, name) in enumerate(tools):
            x = x0 + i * pitch
            d, brand = icons[slug]
            if variant == "colour":
                glyph = brand if contrast(brand, t["deep"]) >= 2.2 else t["ink"]
                mark = ""
            else:
                glyph = t["ink"]
                mark = f'<rect x="{x + 15}" y="{y + 52}" width="18" height="2" rx="1" fill="{brand}"/>'
            parts.append(
                f'<g class="tile" style="animation-delay:{0.15 + k * 0.035:.3f}s">'
                f'<rect x="{x}" y="{y}" width="48" height="48" rx="11" fill="{t["deep"]}"/>'
                f'<path transform="translate({x + 12} {y + 12})" fill="{glyph}" d="{d}"/>{mark}'
                f'<path fill="{t["dim"]}" d="{f["sans"].path(name, 10, x + 24, y + 70, "middle")}"/></g>'
            )
            k += 1
    style = (
        ".tile { animation: rise .6s cubic-bezier(.2,.8,.2,1) both; }"
        "@keyframes rise { from { opacity: 0; transform: translateY(6px); } }"
    )
    names = ", ".join(name for _, tools in STACK for _, name in tools)
    return svg(w, h, f"Tools: {names}", "".join(parts), style)


def icon_svgs(t: dict) -> dict[str, str]:
    c = t["ink"]

    def icon(title: str, paint: str, body: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" {paint} '
            f'role="img"><title>{title}</title>{body}</svg>\n'
        )

    line = f'fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round"'
    return {
        "website": icon(
            "Website",
            line,
            '<circle cx="12" cy="12" r="9.2"/><path d="M2.8 12h18.4M12 2.8c2.6 2.6 3.9 5.6 3.9 9.2'
            's-1.3 6.6-3.9 9.2M12 2.8C9.4 5.4 8.1 8.4 8.1 12s1.3 6.6 3.9 9.2"/>',
        ),
        "x": icon(
            "X",
            f'fill="{c}"',
            '<path d="M18.9 2.2h3.4l-7.4 8.5 8.7 11.5h-6.8l-5.3-7-6.1 7H1.9l7.9-9.1'
            'L1.5 2.2h7l4.8 6.4ZM17.7 20.1h1.9L7.4 4.2H5.4Z"/>',
        ),
        "linkedin": icon(
            "LinkedIn",
            line,
            '<rect x="2.6" y="2.6" width="18.8" height="18.8" rx="4"/><path stroke-width="1.9" '
            'd="M8 11v6M12.2 17v-6M12.2 13.6c0-1.7 1.2-2.7 2.6-2.7s2.4 1 2.4 2.7V17"/>'
            f'<circle cx="8" cy="7.9" r="1.15" fill="{c}" stroke="none"/>',
        ),
    }


def glyph_table(mono: Face) -> dict:
    """Outlines at 1,000 units for the characters contrib.py writes."""
    table = {}
    for ch in sorted(set("0123456789, contributionsheaylrpvt")):
        glyphs, w, _ = mono.run(ch, 1000)
        pen = SVGPathPen(mono.glyphs, ntos=num)
        for name, gx, gy in glyphs:
            mono.glyphs[name].draw(TransformPen(pen, (1, 0, 0, -1, gx, -gy)))
        table[ch] = {"d": pen.getCommands(), "advance": round(w, 1)}
    return table


def load_icons(folder: Path) -> dict[str, tuple[str, str]]:
    data = json.loads((folder.parent / "data" / "simple-icons.json").read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data["icons"]
    hexes = {}
    for row in rows:
        slug = row.get("slug") or re.sub(r"[^a-z0-9]", "", row["title"].lower().replace(".", "dot"))
        hexes[slug] = "#" + row["hex"]
    out = {}
    for _, tools in STACK:
        for slug, _ in tools:
            d = re.search(r' d="([^"]+)"', (folder / f"{slug}.svg").read_text(encoding="utf-8")).group(1)
            out[slug] = (d, hexes[slug])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, type=Path)
    ap.add_argument("--icons", required=True, type=Path)
    ap.add_argument("--stack", choices=("colour", "ink"), default="colour")
    args = ap.parse_args()
    d = args.fonts
    f = {
        "serif": Face(d / "InstrumentSerif-Italic.ttf"),
        "sans": Face(d / "InterTight[wght].ttf", 400),
        "label": Face(d / "InterTight[wght].ttf", 560),
        "mono": Face(d / "JetBrainsMono[wght].ttf", 400),
    }
    icons = load_icons(args.icons)
    ASSETS.mkdir(exist_ok=True)
    for theme, t in THEMES.items():
        (ASSETS / f"hero-{theme}.svg").write_text(hero(f, t), encoding="utf-8")
        (ASSETS / f"stack-{theme}.svg").write_text(stack(f, t, icons, args.stack), encoding="utf-8")
        for name, body in icon_svgs(t).items():
            (ASSETS / f"icon-{name}-{theme}.svg").write_text(body, encoding="utf-8")
    table = {"themes": THEMES, "glyphs": glyph_table(f["mono"])}
    (ROOT / "scripts" / "glyphs.json").write_text(
        json.dumps(table, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print("\n".join(sorted(p.name for p in ASSETS.glob("*.svg"))))


if __name__ == "__main__":
    main()
