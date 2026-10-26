"""Build web/src/lib/ap-map.ts (simplified SVG district outlines) from a district GeoJSON.

Input : andhra-pradesh.geojson from https://github.com/udit-001/india-maps-data
        (geojson/states/andhra-pradesh.geojson; community-curated from public sources, 26 districts).
Output: web/src/lib/ap-map.ts  (viewBox, one SVG path + label point per district)

Run:    python -I web/tools/build-ap-map.py path/to/andhra-pradesh.geojson
Borders are heavily simplified for a schematic web map; they are indicative, not survey-accurate.
"""
import json
import math
import sys
from pathlib import Path

SCALE = 80.0          # SVG units per degree of latitude
TOLERANCE = 0.45      # simplification tolerance in SVG units (~0.5 px)
MIN_RING_AREA = 5.0   # drop specks smaller than this (SVG units squared)
PAD = 6

# dataset name -> name used on the site
RENAME = {"YSR": "YSR Kadapa", "Anantapuramu": "Anantapur", "Sri Potti Sriramulu Nellore": "Nellore"}


def rdp(pts, eps):
    """Ramer-Douglas-Peucker on an open polyline (iterative)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy) or 1e-12
        best, idx = 0.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * (px - ax) - dx * (py - ay)) / norm
            if d > best:
                best, idx = d, i
        if best > eps:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def simplify_ring(ring, eps):
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    # split the closed ring at its two farthest-apart anchor points so RDP has stable ends
    i0 = 0
    i1 = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    a = rdp(pts[i0:i1 + 1], eps)
    b = rdp(pts[i1:] + [pts[0]], eps)
    return a[:-1] + b[:-1]


def area(r):
    return 0.5 * sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))


def inside(x, y, r):
    c = False
    j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i]
        xj, yj = r[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def label_point(r):
    """Approximate pole of inaccessibility: the interior grid point farthest from the border."""
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    best = (0.0, sum(xs) / len(xs), sum(ys) / len(ys))
    step = 2.5
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            if inside(x, y, r):
                d = min(seg_dist(x, y, *r[i], *r[(i + 1) % len(r)]) for i in range(len(r)))
                if d > best[0]:
                    best = (d, x, y)
            x += step
        y += step
    return best


def main(src: str) -> None:
    gj = json.loads(Path(src).read_text(encoding="utf-8"))
    lons = [c[0] for f in gj["features"] for poly in ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon" else f["geometry"]["coordinates"]) for ring in poly for c in ring]
    lats = [c[1] for f in gj["features"] for poly in ([f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon" else f["geometry"]["coordinates"]) for ring in poly for c in ring]
    lon0, lat_max = min(lons), max(lats)
    kx = math.cos(math.radians((min(lats) + lat_max) / 2))

    def proj(c):
        return ((c[0] - lon0) * kx * SCALE + PAD, (lat_max - c[1]) * SCALE + PAD)

    out, total = {}, 0
    for f in gj["features"]:
        name = RENAME.get(f["properties"]["district"], f["properties"]["district"])
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        rings = []
        for poly in polys:
            for ring in poly:  # outer ring first, holes after (drawn with evenodd)
                pts = simplify_ring([proj(c) for c in ring], TOLERANCE)
                if len(pts) >= 3 and abs(area(pts)) >= MIN_RING_AREA:
                    rings.append(pts)
        total += sum(len(r) for r in rings)
        d = "".join("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in r) + "Z" for r in rings)
        biggest = max(rings, key=lambda r: abs(area(r)))
        r_in, cx, cy = label_point(biggest)
        out[name] = {"d": d, "x": round(cx, 1), "y": round(cy, 1), "r": round(r_in, 1)}

    width = max(p[0] for f in out.values() for p in [(0, 0)]) if False else None
    all_pts = [tuple(map(float, pt.split())) for v in out.values() for pt in v["d"].replace("M", "L").replace("Z", "").split("L") if pt.strip()]
    w = math.ceil(max(p[0] for p in all_pts) + PAD)
    h = math.ceil(max(p[1] for p in all_pts) + PAD)

    ts = [
        "// GENERATED by web/tools/build-ap-map.py: simplified Andhra Pradesh district outlines.",
        "// Boundaries: udit-001/india-maps-data (community-curated from public sources), heavily simplified.",
        "// Indicative only; not an official or survey-accurate map.",
        f"export const AP_MAP_SIZE = {{ w: {w}, h: {h} }};",
        "export const AP_DISTRICTS: Record<string, { d: string; x: number; y: number; r: number }> = "
        + json.dumps(out, ensure_ascii=False, indent=1) + ";",
        "",
    ]
    dest = Path(__file__).resolve().parents[1] / "src" / "lib" / "ap-map.ts"
    dest.write_text("\n".join(ts), encoding="utf-8")
    print(f"{len(out)} districts, {total} points, viewBox {w}x{h}, {dest.stat().st_size / 1024:.1f} KB -> {dest}")


if __name__ == "__main__":
    main(sys.argv[1])
