# Singapore Hill Climbers

Four optimizers (SGD, Momentum, AdamW, Muon) climb Singapore's terrain. Loss is negative elevation, so hilltops are local minima and Bukit Timah Hill is the global one.
The finished page is one self-contained file: **`index.html`** (about 2 MB, no server, no external requests).

## Publish it

Any static host works. You only need to upload `index.html`.

**GitHub Pages**
1. Create a repository and add this folder's contents.
2. Settings > Pages > Deploy from a branch > `main` / root.
3. Your page appears at `https://<you>.github.io/<repo>/`.

**Netlify / Cloudflare Pages / Vercel**
Drag the folder (or just `index.html`, plus `assets/` if you added a clip) into the dashboard. No build step is needed.

## Rebuild from source

Requires Python 3.9+ with `numpy`, `scipy`, `rasterio`.

```bash
# 1. (optional) regenerate the heightmap from the FABDEM tile N01E103
python3 scripts/prep.py N01E103_FABDEM_V1-2.tif data/fabdem

# 2. assemble the page
python3 scripts/build.py                       # no chase clip
python3 scripts/build.py --audio my-clip.mp3   # with a built-in clip for Benny Hill mode
```

`data/` already holds the prepared heightmap, so step 1 is only needed if you want to change the smoothing (`SIGMA=2.0 python3 scripts/prep.py ...`) or the area.

## Layout

- `src/template.html` the whole app (HTML, CSS, JS). `__TERRAIN__`, `__SCENARIOS__`, `__AUDIO__` are filled in by `build.py`.
- `src/scenarios.json` the guided scenarios (start cell, settings, captions).
- `scripts/prep.py` crops the tile, masks Johor and sea, smooths, and finds local maxima and their prominence.
- `scripts/build.py` packs the data (gzip + base64) into the page.
- `assets/` optional chase clip (`chase.mp3`).
- `data/fabdem.*` prepared heightmap (uint16, 0.01 m units), peaks and metadata.

## Chase audio (Benny Hill mode)

Two ways to ship a clip, both optional:

1. **As an asset (simplest):** save it as `assets/chase.mp3` next to `index.html` and upload both. The page loads it automatically; if the file is missing, the page still works.
2. **Embedded:** `python3 scripts/build.py --audio my-clip.mp3` bakes it into `index.html` (one file, about 2x bigger).

Visitors can also swap in their own clip with "Replace audio...". Only ship a clip you have the right to distribute: anyone who opens the page can download it, whichever way you ship it.

## Known limits

- FABDEM is not survey data. Bukit Timah Hill reads 162 m (surveyed 163.6 m) and Bukit Gombak reads about 55 m (surveyed 133 m).
- The tile ends at 104 E, so Pulau Tekong and far-east Changi are missing.
- Hilltop names are approximate.
