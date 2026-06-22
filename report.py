#!/usr/bin/env python3
"""
report.py — summarize speedlog.csv into an Xfinity-ready report.

Usage:
    python3 report.py            # full history
    python3 report.py --days 14  # last 14 days only

Plan under test: Xfinity 1 Gbps (1000 Mbps advertised download).
"""
import csv, sys, statistics
from datetime import datetime, timedelta
from collections import defaultdict

PLAN_MBPS = 1000
DIR = "/Users/kayu/internet-speed-monitor"
CSV_PATH = f"{DIR}/speedlog.csv"

# --- args ---
days = None
if "--days" in sys.argv:
    days = int(sys.argv[sys.argv.index("--days") + 1])

rows = []
with open(CSV_PATH) as f:
    for r in csv.DictReader(f):
        rows.append(r)

# Filter by date window if requested
def parse_local(r):
    try:
        return datetime.strptime(r["timestamp_local"][:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

if days is not None:
    cutoff = datetime.now() - timedelta(days=days)
    rows = [r for r in rows if (parse_local(r) or datetime.min) >= cutoff]

total = len(rows)
ok = [r for r in rows if r["status"] == "OK"]
failed = [r for r in rows if r["status"] == "FAILED"]

if total == 0:
    print("No data yet. Let the monitor run for a while, then re-run this report.")
    sys.exit(0)

def fnum(r, k):
    try: return float(r[k])
    except Exception: return None

dls = [fnum(r, "download_mbps") for r in ok if fnum(r, "download_mbps") is not None]
uls = [fnum(r, "upload_mbps") for r in ok if fnum(r, "upload_mbps") is not None]
losses = [fnum(r, "packet_loss_pct") for r in ok if fnum(r, "packet_loss_pct") is not None]
dl_load = [fnum(r, "download_latency_loaded_ms") for r in ok if fnum(r, "download_latency_loaded_ms")]
idle_ping = [fnum(r, "idle_ping_ms") for r in ok if fnum(r, "idle_ping_ms") is not None]

span_start = min((parse_local(r) for r in rows if parse_local(r)), default=None)
span_end = max((parse_local(r) for r in rows if parse_local(r)), default=None)

def pct(n, d): return (100.0 * n / d) if d else 0.0

print("=" * 64)
print("  XFINITY 1 Gbps PLAN — INTERNET PERFORMANCE REPORT")
print("=" * 64)
if span_start and span_end:
    print(f"  Period: {span_start:%Y-%m-%d %H:%M} -> {span_end:%Y-%m-%d %H:%M}")
print(f"  Tests run: {total}   (completed: {len(ok)}, FAILED/dropouts: {len(failed)})")
print(f"  Tested against Comcast's own server (Plainfield, NJ, ID 1767)")
print()

print("-- DOWNLOAD (advertised: 1000 Mbps) " + "-" * 28)
if dls:
    print(f"  Average:   {statistics.mean(dls):7.1f} Mbps   ({pct(statistics.mean(dls), PLAN_MBPS):.0f}% of plan)")
    print(f"  Median:    {statistics.median(dls):7.1f} Mbps")
    print(f"  Worst:     {min(dls):7.1f} Mbps")
    print(f"  Best:      {max(dls):7.1f} Mbps")
    print(f"  Tests below 900 Mbps (90% of plan): {sum(1 for x in dls if x<900):3d} of {len(dls)}  ({pct(sum(1 for x in dls if x<900),len(dls)):.0f}%)")
    print(f"  Tests below 500 Mbps (50% of plan): {sum(1 for x in dls if x<500):3d} of {len(dls)}  ({pct(sum(1 for x in dls if x<500),len(dls)):.0f}%)")
    print(f"  Tests below 250 Mbps (25% of plan): {sum(1 for x in dls if x<250):3d} of {len(dls)}  ({pct(sum(1 for x in dls if x<250),len(dls)):.0f}%)")
print()

print("-- UPLOAD " + "-" * 53)
if uls:
    print(f"  Average:   {statistics.mean(uls):7.1f} Mbps")
    print(f"  Worst:     {min(uls):7.1f} Mbps")
print()

print("-- RELIABILITY (Xfinity can't blame these on Wi-Fi) " + "-" * 12)
print(f"  Failed tests / dropouts:  {len(failed)} of {total}  ({pct(len(failed),total):.0f}%)")
if losses:
    bad_loss = [x for x in losses if x > 0]
    print(f"  Tests with packet loss:   {len(bad_loss)} of {len(losses)}  ({pct(len(bad_loss),len(losses)):.0f}%)")
    print(f"  Worst packet loss:        {max(losses):.1f}%")
if dl_load and idle_ping:
    avg_idle = statistics.mean(idle_ping)
    bad_buffer = [x for x in dl_load if x > 100]
    print(f"  Avg idle ping:            {avg_idle:.0f} ms")
    print(f"  Avg latency UNDER LOAD:   {statistics.mean(dl_load):.0f} ms   (bufferbloat: lag while in use)")
    print(f"  Worst latency under load: {max(dl_load):.0f} ms")
    print(f"  Tests with bad lag-under-load (>100ms): {len(bad_buffer)} of {len(dl_load)}  ({pct(len(bad_buffer),len(dl_load)):.0f}%)")
print()

# --- Worst times of day ---
by_hour = defaultdict(list)
for r in ok:
    t = parse_local(r)
    d = fnum(r, "download_mbps")
    if t and d is not None:
        by_hour[t.hour].append(d)
if by_hour:
    print("-- WORST TIMES OF DAY (avg download by hour) " + "-" * 19)
    worst = sorted(((statistics.mean(v), h, len(v)) for h, v in by_hour.items()))[:5]
    for avg, h, n in worst:
        bar = "#" * int(avg / 20)
        print(f"  {h:02d}:00  {avg:7.1f} Mbps  {bar}  (n={n})")
print()
print("=" * 64)
print("  Raw data: speedlog.csv  |  Each row has a shareable speedtest.net link")
print("=" * 64)
