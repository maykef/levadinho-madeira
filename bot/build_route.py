"""Build a guide route: GPX track + stop list → route.json + one MP3 per stop and language.

  bot/.tts/bin/python bot/build_route.py bot/routes_private/ely-test

The folder holds route.gpx and source.json:
  {"id": "ely-test", "title": {"en": "…", "pt": "…"}, "langs": ["en", "pt"], "loop": true,
   "stops": [{"id": "s1", "at_m": 0, "name": {"en": "…"}, "line": {"en": "…"}, "radius": 35}, …]}
A stop is placed on the track at `at_m` metres from the start ("end" = the last point).
Each clip says: stop n of N, the name, the stop's line, then the next stop and its distance.
Audio needs Piper (bot/.tts venv, voices in bot/.tts/voices); --no-audio skips it.
"""
import io
import json
import os
import re
import sys
import wave

from geo import distance_m

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES = {"en": "en_GB-alba-medium", "pt": "pt_PT-tugão-medium"}
TEMPLATE = {
    "en": {"stop": "Stop {n} of {N}: {name}.", "next": "Next stop: {name}, in about {dist}."},
    "pt": {"stop": "Paragem {n} de {N}: {name}.", "next": "Próxima paragem: {name}, daqui a cerca de {dist}."},
}


def spoken_distance(m, lang):
    if m < 950:
        m = max(50, round(m / 50) * 50)
        return f"{m} metres" if lang == "en" else f"{m} metros"
    km = f"{m / 1000:.1f}".removesuffix(".0")
    if lang == "en":
        return f"{km} kilometre" + ("" if km == "1" else "s")
    return f"{km.replace('.', ',')} quilómetro" + ("" if km == "1" else "s")


def read_gpx(path):
    s = open(path, encoding="utf-8").read()
    pts = [(float(a), float(b)) for a, b in re.findall(r'<trkpt lat="([-\d.]+)" lon="([-\d.]+)"', s)]
    cum = [0.0]
    for (a, b), (c, d) in zip(pts, pts[1:]):
        cum.append(cum[-1] + distance_m(a, b, c, d))
    return pts, cum


def point_at(pts, cum, at):
    """Interpolated track point `at` metres from the start."""
    at = min(max(at, 0), cum[-1])
    for i in range(1, len(pts)):
        if cum[i] >= at:
            f = (at - cum[i - 1]) / ((cum[i] - cum[i - 1]) or 1)
            return (pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f,
                    pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f)
    return pts[-1]


def synth(voice, text):
    import lameenc
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        voice.synthesize_wav(text, w)
    buf.seek(0)
    w = wave.open(buf)
    enc = lameenc.Encoder()
    enc.set_bit_rate(48)
    enc.set_in_sample_rate(w.getframerate())
    enc.set_channels(1)
    enc.set_quality(2)
    return enc.encode(w.readframes(w.getnframes())) + enc.flush()


def build(folder, audio=True):
    src = json.load(open(os.path.join(folder, "source.json"), encoding="utf-8"))
    pts, cum = read_gpx(os.path.join(folder, "route.gpx"))
    stops = src["stops"]
    for s in stops:
        s["at_m"] = round(cum[-1]) if s["at_m"] == "end" else s["at_m"]
        s["lat"], s["lon"] = (round(x, 6) for x in point_at(pts, cum, s["at_m"]))
        s.setdefault("radius", 35)
    stops.sort(key=lambda s: s["at_m"])
    N = len(stops)
    for n, s in enumerate(stops, 1):
        s["n"] = n
        s["text"] = {}
        for lang in src["langs"]:
            t = TEMPLATE[lang]
            parts = [t["stop"].format(n=n, N=N, name=s["name"][lang]), s.get("line", {}).get(lang, "")]
            if n < N:
                nxt = stops[n]
                parts.append(t["next"].format(name=nxt["name"][lang],
                                              dist=spoken_distance(nxt["at_m"] - s["at_m"], lang)))
            s["text"][lang] = " ".join(p for p in parts if p)

    if audio:
        from piper import PiperVoice
        for lang in src["langs"]:
            voice = PiperVoice.load(os.path.join(HERE, ".tts", "voices", VOICES[lang] + ".onnx"))
            os.makedirs(os.path.join(folder, "audio", lang), exist_ok=True)
            for s in stops:
                rel = f"audio/{lang}/{s['id']}.mp3"
                open(os.path.join(folder, rel), "wb").write(synth(voice, s["text"][lang]))
                s.setdefault("audio", {})[lang] = rel

    route = {"id": src["id"], "title": src["title"], "langs": src["langs"], "loop": src.get("loop", False),
             "length_m": round(cum[-1]),
             "line": [[round(a, 6), round(b, 6)] for a, b in pts],
             "stops": [{k: s[k] for k in ("id", "n", "name", "lat", "lon", "at_m", "radius", "text", "audio") if k in s}
                       for s in stops]}
    json.dump(route, open(os.path.join(folder, "route.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{src['id']}: {route['length_m']} m, {N} stops, audio={'yes' if audio else 'no'}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for folder in args:
        build(folder, audio="--no-audio" not in sys.argv)
