"""Crop a 1-degree DEM tile to Singapore, mask Johor/water, smooth, export a heightmap + local maxima.

usage: python3 prep.py <tile.tif> <out_prefix>
Outputs: <out_prefix>.dem.u16 (little-endian uint16, height*20 metres, row-major)
         <out_prefix>.peaks.u16 (records of x,y,q,prom_cm as uint16)
         <out_prefix>.meta.json
"""
import sys, json, numpy as np, rasterio
from scipy import ndimage as ndi

tif, out = sys.argv[1], sys.argv[2]
import os
SIGMA = float(os.environ.get("SIGMA", "2.0"))  # cells (~31 m) of gaussian smoothing
SCALE = 100          # stored units per metre (0.01 m)
LON_W, LON_E, LAT_S, LAT_N = 103.60, 104.0, 1.15, 1.475

r = rasterio.open(tif)
a = r.read(1).astype(np.float64)
T0_LON, T0_LAT = r.bounds.left, r.bounds.top
col = lambda lon: int(round((lon - T0_LON) * 3600))
row = lambda lat: int(round((T0_LAT - lat) * 3600))
r0, r1, c0, c1 = row(LAT_N), row(LAT_S), col(LON_W), min(col(LON_E), a.shape[1])
sub = a[r0:r1, c0:c1].copy()
H, W = sub.shape
sub[sub < 0] = 0
land = sub > 0.5

# keep the main island + small Singapore islands; drop Johor (large components / far north-west)
lab, n = ndi.label(land, structure=np.ones((3, 3)))
ids = np.arange(1, n + 1)
sz = ndi.sum(land, lab, ids)
cm = ndi.center_of_mass(land, lab, ids)
main = lab[int(round((LAT_N - 1.354) * 3600)), int(round((103.776 - LON_W) * 3600))]
keep = np.zeros(n + 1, bool)
for i, s, (cy, cx) in zip(ids, sz, cm):
    lat = LAT_N - cy / 3600
    lon = LON_W + cx / 3600
    if i == main or (s < 40000 and lat < 1.44 and lon > 103.62):
        keep[i] = True
land = keep[lab]
sub[~land] = 0
sm = ndi.gaussian_filter(sub, SIGMA, mode="nearest")
sm[~land] = 0
q = np.round(sm * SCALE).astype(np.int64)
q[land] = np.maximum(q[land], 1)          # land is always >= 1 unit so it can be told from sea
q[~land] = 0
assert q.max() < 65535

# local maxima + prominence by descending flood, total order = (q, flat index)
flat = q.ravel()
land_idx = np.flatnonzero(land.ravel())
order = land_idx[np.lexsort((land_idx, flat[land_idx]))][::-1]   # highest key first
parent = {}
peak_of = {}
prom = {}
seen = np.zeros(H * W, bool)
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
off = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
for idx in order.tolist():
    y, x = divmod(idx, W)
    roots = set()
    for dy, dx in off:
        yy, xx = y + dy, x + dx
        if 0 <= yy < H and 0 <= xx < W:
            j = yy * W + xx
            if seen[j]:
                roots.add(find(j))
    seen[idx] = True
    if not roots:
        parent[idx] = idx
        peak_of[idx] = idx
        continue
    roots = sorted(roots, key=lambda rt: (flat[peak_of[rt]], peak_of[rt]), reverse=True)
    top = roots[0]
    parent[idx] = top
    for rt in roots[1:]:
        pk = peak_of[rt]
        prom[pk] = (flat[pk] - flat[idx]) / SCALE
        parent[rt] = top
for rt in {find(i) for i in parent}:
    pk = peak_of[rt]
    prom[pk] = flat[pk] / SCALE         # separate island: prominence above sea level

peaks = sorted(prom.keys(), key=lambda p: -flat[p])
rec = np.zeros((len(peaks), 4), np.uint16)
for k, p in enumerate(peaks):
    y, x = divmod(p, W)
    rec[k] = (x, y, flat[p], min(65535, int(round(prom[p] * 100))))

# hand-placed names (approximate coordinates; matched to the tallest real local peak nearby)
NAMES = [
    ("Bukit Timah Hill", 1.3541, 103.7767), ("Bukit Batok Hill", 1.3480, 103.7640),
    ("Bukit Gombak", 1.3600, 103.7515), ("Bukit Panjang Hill", 1.3800, 103.7640),
    ("Bukit Mandai", 1.4065, 103.7870), ("Mount Faber", 1.2724, 103.8196),
    ("Telok Blangah Hill", 1.2755, 103.8100), ("Fort Canning Hill", 1.2943, 103.8446),
    ("Mount Emily", 1.3016, 103.8480), ("Bukit Brown", 1.3385, 103.8365),
    ("Kent Ridge", 1.2905, 103.7855), ("Bukit Puaka (Ubin)", 1.4125, 103.9585),
    ("Mount Serapong (Sentosa)", 1.2500, 103.8290), ("Mount Imbiah (Sentosa)", 1.2530, 103.8200),
]
named = []
for nm, la, lo in NAMES:
    cx = (lo - LON_W) * 3600 - 0.5
    cy = (LAT_N - la) * 3600 - 0.5
    best = None
    for k in range(len(peaks)):
        x, y, qq, pc = rec[k]
        if (x - cx) ** 2 + (y - cy) ** 2 <= 23 ** 2 and pc >= 800:
            if best is None or qq > rec[best][2]:
                best = k
    if best is not None:
        named.append({"name": nm, "peak": int(best)})
        print("named", nm, "->", rec[best][:3] / [1, 1, SCALE], rec[best][3] / 100)
    else:
        print("no peak for", nm)

open(out + ".dem.u16", "wb").write(q.astype("<u2").tobytes())
open(out + ".peaks.u16", "wb").write(rec.astype("<u2").tobytes())
json.dump({"W": W, "H": H, "lon_w": T0_LON + c0 / 3600, "lat_n": T0_LAT - r0 / 3600,
           "scale": SCALE, "npeaks": len(peaks), "named": named,
           "max_m": float(q.max() / SCALE), "land_cells": int(land.sum())},
          open(out + ".meta.json", "w"))
print("W,H", W, H, "land", int(land.sum()), "peaks", len(peaks), "max", q.max() / SCALE)
print("peaks with prom>=0.3m:", int((rec[:, 3] >= 30).sum()), ">=10m:", int((rec[:, 3] >= 1000).sum()))
