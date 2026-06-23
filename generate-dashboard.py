#!/usr/bin/env python3
"""
generate-dashboard.py — turn speedlog.csv into a self-contained, offline,
auto-refreshing dashboard.html. No external dependencies, no internet needed
to render (charts are inline SVG). Regenerated after every speed test.

Plan under test: Verizon Fios 300/300 (300 Mbps symmetric).
"""
import csv, statistics
from datetime import datetime, timedelta
from collections import defaultdict

PLAN = 300
DIR = "/Users/kayu/internet-speed-monitor"
CSV_PATH = f"{DIR}/speedlog.csv"
OUT = f"{DIR}/dashboard.html"

# ---------- load ----------
rows = []
try:
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))
except FileNotFoundError:
    rows = []

def ptime(r):
    try: return datetime.strptime(r["timestamp_local"][:19], "%Y-%m-%d %H:%M:%S")
    except Exception: return None

def fnum(r, k):
    try: return float(r[k])
    except Exception: return None

rows = [r for r in rows if ptime(r)]
rows.sort(key=ptime)
ok = [r for r in rows if r.get("status") == "OK"]
failed = [r for r in rows if r.get("status") == "FAILED"]

dls = [fnum(r, "download_mbps") for r in ok if fnum(r, "download_mbps") is not None]
uls = [fnum(r, "upload_mbps") for r in ok if fnum(r, "upload_mbps") is not None]
loaded = [fnum(r, "download_latency_loaded_ms") for r in ok]
idle = [fnum(r, "idle_ping_ms") for r in ok]

def pct(n, d): return (100.0 * n / d) if d else 0.0
def color_for(ratio):  # ratio = value/plan, higher is better
    if ratio >= 0.9: return "#16a34a"
    if ratio >= 0.5: return "#d97706"
    return "#dc2626"

t90 = 0.9 * PLAN
avg_dl = statistics.mean(dls) if dls else 0
worst_dl = min(dls) if dls else 0
latest_dl = dls[-1] if dls else 0
avg_ul = statistics.mean(uls) if uls else 0
latest_ul = uls[-1] if uls else 0
below90 = sum(1 for x in dls if x < t90)
worst_loaded = max(loaded) if loaded else 0
avg_loaded = statistics.mean(loaded) if loaded else 0
avg_idle = statistics.mean(idle) if idle else 0

# ---------- SVG helpers ----------
def esc(s): return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def line_chart(series, ymax, height=300, refs=None, ylabel=""):
    """series: list of (label,color,[values]); refs: list of (yval,label,color)."""
    W, H = 1000, height
    pl, pr, pt, pb = 56, 20, 24, 40
    iw, ih = W - pl - pr, H - pt - pb
    n = max((len(v) for _, _, v in series), default=0)
    def X(i): return pl + (iw * (i / (n - 1)) if n > 1 else iw / 2)
    def Y(v): return pt + ih * (1 - (v / ymax if ymax else 0))
    svg = [f'<svg viewBox="0 0 {W} {H}" class="chart" preserveAspectRatio="none">']
    # gridlines + y labels
    for g in range(5):
        yv = ymax * g / 4
        y = Y(yv)
        svg.append(f'<line x1="{pl}" y1="{y:.0f}" x2="{W-pr}" y2="{y:.0f}" stroke="#eef0f3"/>')
        svg.append(f'<text x="{pl-8}" y="{y+4:.0f}" text-anchor="end" class="ax">{yv:.0f}</text>')
    # reference lines
    for yv, lbl, c in (refs or []):
        if yv <= ymax:
            y = Y(yv)
            svg.append(f'<line x1="{pl}" y1="{y:.0f}" x2="{W-pr}" y2="{y:.0f}" stroke="{c}" stroke-dasharray="6 5" stroke-width="1.5"/>')
            svg.append(f'<text x="{W-pr}" y="{y-6:.0f}" text-anchor="end" class="ref" fill="{c}">{lbl}</text>')
    # series
    for label, c, vals in series:
        if not vals: continue
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        # area fill for the first/primary series
        if label == series[0][0]:
            area = f"M {X(0):.1f},{Y(0):.1f} L " + " L ".join(f"{X(i):.1f},{Y(v):.1f}" for i,v in enumerate(vals)) + f" L {X(len(vals)-1):.1f},{Y(0):.1f} Z"
            svg.append(f'<path d="{area}" fill="{c}" fill-opacity="0.08"/>')
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2.5" stroke-linejoin="round"/>')
        for i, v in enumerate(vals):
            svg.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="2.6" fill="{c}"><title>{esc(v)}</title></circle>')
    svg.append('</svg>')
    return "".join(svg)

def bar_chart(pairs, ymax, height=260):
    """pairs: list of (label, value, color)."""
    W, H = 1000, height
    pl, pr, pt, pb = 56, 20, 20, 44
    iw, ih = W - pl - pr, H - pt - pb
    n = len(pairs)
    bw = iw / n * 0.62 if n else 0
    gap = iw / n if n else 0
    svg = [f'<svg viewBox="0 0 {W} {H}" class="chart" preserveAspectRatio="none">']
    for g in range(5):
        yv = ymax * g / 4
        y = pt + ih * (1 - g/4)
        svg.append(f'<line x1="{pl}" y1="{y:.0f}" x2="{W-pr}" y2="{y:.0f}" stroke="#eef0f3"/>')
        svg.append(f'<text x="{pl-8}" y="{y+4:.0f}" text-anchor="end" class="ax">{yv:.0f}</text>')
    for i, (lbl, v, c) in enumerate(pairs):
        x = pl + gap*i + (gap-bw)/2
        bh = ih * (v/ymax if ymax else 0)
        y = pt + ih - bh
        svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{c}"><title>{esc(lbl)}: {esc(round(v))} Mbps</title></rect>')
        svg.append(f'<text x="{x+bw/2:.1f}" y="{pt+ih+18:.0f}" text-anchor="middle" class="ax">{esc(lbl)}</text>')
    svg.append('</svg>')
    return "".join(svg)

# ---------- build charts ----------
if dls:
    dl_chart = line_chart(
        [("Download", "#2563eb", dls), ("Upload", "#0d9488", uls)],
        ymax=PLAN,
        refs=[(PLAN, f"{PLAN:.0f} — your paid speed", "#94a3b8"), (t90, f"{t90:.0f} (90%)", "#cbd5e1")],
    )
else:
    dl_chart = '<div class="empty">No completed tests yet.</div>'

if loaded and idle:
    lat_max = max(max(loaded), max(idle)) * 1.15 or 100
    lat_chart = line_chart(
        [("Lag under load", "#dc2626", loaded), ("Idle ping", "#16a34a", idle)],
        ymax=lat_max,
        refs=[(100, "100ms — noticeable lag", "#cbd5e1")],
    )
else:
    lat_chart = '<div class="empty">No latency data yet.</div>'

by_hour = defaultdict(list)
for r in ok:
    t, d = ptime(r), fnum(r, "download_mbps")
    if t and d is not None: by_hour[t.hour].append(d)
if by_hour:
    hours = sorted(by_hour.keys())
    pairs = [(f"{h:02d}h", statistics.mean(by_hour[h]), color_for(statistics.mean(by_hour[h])/PLAN)) for h in hours]
    hour_chart = bar_chart(pairs, ymax=PLAN)
else:
    hour_chart = '<div class="empty">Not enough data yet — fills in across the day.</div>'

# ---------- verdict ----------
ratio = avg_dl / PLAN if PLAN else 0
verdict_color = color_for(ratio)
verdict = f"Delivering {avg_dl/PLAN*100:.0f}% of your paid speed on average" if dls else "Waiting for first results…"

span = ""
if rows:
    span = f"{ptime(rows[0]):%b %d, %H:%M} → {ptime(rows[-1]):%b %d, %H:%M}"
now = ok[-1] if ok else None
gen_time = ptime(rows[-1]).strftime("%b %d, %Y at %H:%M") if rows else ""

def card(value, label, color="#0f172a", sub=""):
    return f'<div class="card"><div class="cv" style="color:{color}">{value}</div><div class="cl">{label}</div>{f"<div class=cs>{sub}</div>" if sub else ""}</div>'

cards = "".join([
    card(f"{avg_dl:.0f}", "Avg download (Mbps)", verdict_color, f"of {PLAN:.0f} paid"),
    card(f"{avg_ul:.0f}", "Avg upload (Mbps)", color_for(avg_ul/PLAN) if uls else "#0f172a", f"of {PLAN:.0f} paid"),
    card(f"{pct(below90, len(dls)):.0f}%", f"Tests below {t90:.0f} Mbps", color_for(1-pct(below90,len(dls))/100) if dls else "#0f172a", f"{below90} of {len(dls)}"),
    card(f"{len(failed)}", "Dropouts (failed tests)", "#dc2626" if failed else "#16a34a"),
    card(f"{worst_loaded:.0f}", "Worst lag under load (ms)", color_for(1 - min(worst_loaded,500)/500) if loaded else "#0f172a", f"idle ~{avg_idle:.0f}ms"),
])

html = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Internet Health — Verizon Fios 300</title>
<style>
  :root {{ font-family: -apple-system, "SF Pro Text", Segoe UI, Roboto, sans-serif; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#f6f7f9; color:#0f172a; padding:28px 22px 60px; }}
  .wrap {{ max-width:1040px; margin:0 auto; }}
  h1 {{ font-size:22px; margin:0 0 2px; letter-spacing:-.3px; }}
  .sub {{ color:#64748b; font-size:13px; margin-bottom:18px; }}
  .verdict {{ display:flex; align-items:center; gap:12px; background:#fff; border:1px solid #e7e9ee; border-left:6px solid {verdict_color};
             border-radius:12px; padding:16px 18px; margin-bottom:18px; }}
  .verdict b {{ font-size:18px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; background:{verdict_color}; box-shadow:0 0 0 4px {verdict_color}22; }}
  .cards {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:22px; }}
  .card {{ background:#fff; border:1px solid #e7e9ee; border-radius:12px; padding:14px 16px; }}
  .cv {{ font-size:26px; font-weight:700; letter-spacing:-.5px; }}
  .cl {{ font-size:12px; color:#64748b; margin-top:3px; }}
  .cs {{ font-size:11px; color:#94a3b8; margin-top:2px; }}
  .panel {{ background:#fff; border:1px solid #e7e9ee; border-radius:14px; padding:18px 18px 8px; margin-bottom:18px; }}
  .panel h2 {{ font-size:15px; margin:0 0 2px; }}
  .panel p {{ font-size:12.5px; color:#64748b; margin:0 0 10px; }}
  .chart {{ width:100%; height:auto; display:block; }}
  .ax {{ font-size:11px; fill:#94a3b8; }}
  .ref {{ font-size:11px; font-weight:600; }}
  .legend {{ display:flex; gap:18px; font-size:12px; color:#475569; margin:2px 0 6px 56px; }}
  .legend span::before {{ content:""; display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:middle; }}
  .lg-load::before {{ background:#dc2626; }} .lg-idle::before {{ background:#16a34a; }}
  .lg-dl::before {{ background:#2563eb; }} .lg-ul::before {{ background:#0d9488; }}
  .empty {{ color:#94a3b8; font-size:13px; padding:30px 0; text-align:center; }}
  footer {{ color:#94a3b8; font-size:11.5px; line-height:1.6; margin-top:8px; }}
  @media (max-width:760px) {{ .cards {{ grid-template-columns:repeat(2,1fr); }} }}
</style></head>
<body><div class="wrap">
  <h1>Internet Health — Verizon Fios 300/300 plan</h1>
  <div class="sub">Tested every 30&nbsp;min against Verizon's own server (New York, NY) · {span} · {len(rows)} tests · updated {gen_time}</div>

  <div class="verdict"><span class="dot"></span><div><b>{verdict}</b><br>
    <span style="font-size:13px;color:#64748b">Latest test: {latest_dl:.0f}&nbsp;↓ / {latest_ul:.0f}&nbsp;↑ Mbps · worst lag under load: {worst_loaded:.0f}&nbsp;ms (idle ~{avg_idle:.0f}&nbsp;ms)</span></div></div>

  <div class="cards">{cards}</div>

  <div class="panel">
    <h2>Download &amp; upload over time</h2>
    <p>Each dot is a test. Fios is symmetric, so you pay for {PLAN:.0f}&nbsp;Mbps both ways (dashed line) — the gap is what you're not getting.</p>
    <div class="legend"><span class="lg-dl">Download</span><span class="lg-ul">Upload</span></div>
    {dl_chart}
  </div>

  <div class="panel">
    <h2>Lag under load — the evidence your ISP can't blame on your Wi-Fi</h2>
    <p>How much your connection lags <i>while in use</i> (red) vs. when idle (green). Big red spikes = stutter on calls, video, gaming.</p>
    <div class="legend"><span class="lg-load">Lag under load</span><span class="lg-idle">Idle ping</span></div>
    {lat_chart}
  </div>

  <div class="panel">
    <h2>Worst times of day</h2>
    <p>Average download by hour. Red bars = when your service is worst.</p>
    {hour_chart}
  </div>

  <footer>
    Auto-refreshes every 60&nbsp;seconds · Renders offline (no internet needed) · Data: ~/internet-speed-monitor/speedlog.csv<br>
    Note: tested over Wi-Fi — for the strongest case on raw speed, run a few tests plugged into Ethernet. Latency, packet loss & dropouts above are <i>not</i> Wi-Fi-dependent.
  </footer>
</div></body></html>"""

with open(OUT, "w") as f:
    f.write(html)
# index.html = what GitHub Pages serves (identical content)
with open(f"{DIR}/index.html", "w") as f:
    f.write(html)
print(f"Wrote {OUT} + index.html ({len(rows)} tests)")
