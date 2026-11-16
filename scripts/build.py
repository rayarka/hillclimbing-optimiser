"""Assemble the single-file page.

usage: python3 scripts/build.py [--audio path/to/clip.mp3] [--out index.html]

Reads data/fabdem.* (made by scripts/prep.py), src/template.html and src/scenarios.json.
Without --audio the page has no built-in chase clip (people can still load their own).
"""
import argparse, base64, gzip, json, mimetypes, os

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--audio", help="optional audio clip to embed for Benny Hill mode")
ap.add_argument("--out", default=os.path.join(root, "index.html"))
a = ap.parse_args()

def b64gz(path):
    return base64.b64encode(gzip.compress(open(path, "rb").read(), 9)).decode()

d = os.path.join(root, "data", "fabdem")
terrain = {"meta": json.load(open(d + ".meta.json")),
           "dem": b64gz(d + ".dem.u16"), "peaks": b64gz(d + ".peaks.u16")}
audio = "null"
if a.audio:
    mime = mimetypes.guess_type(a.audio)[0] or "audio/mpeg"
    audio = json.dumps({"name": os.path.basename(a.audio), "mime": mime,
                        "b64": base64.b64encode(open(a.audio, "rb").read()).decode()}, separators=(",", ":"))
html = open(os.path.join(root, "src", "template.html")).read()
html = (html.replace("__AUDIO__", audio)
            .replace("__TERRAIN__", json.dumps(terrain, separators=(",", ":")))
            .replace("__SCENARIOS__", open(os.path.join(root, "src", "scenarios.json")).read()))
open(a.out, "w").write(html)
print(a.out, round(len(html) / 1e6, 2), "MB")
