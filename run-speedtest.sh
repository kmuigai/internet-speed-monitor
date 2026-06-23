#!/bin/bash
#
# run-speedtest.sh — runs one Ookla speed test against Verizon's own NY server
# and appends a single row to speedlog.csv. Failures are logged too (as dropouts),
# because a failed test is itself evidence of bad service.
#
# Configured for Kayu's Verizon Fios 300/300 plan.

set -uo pipefail

# --- Config ---------------------------------------------------------------
DIR="$HOME/internet-speed-monitor"
CSV="$DIR/speedlog.csv"
RAWLOG="$DIR/logs/raw.jsonl"        # full JSON of every run, for deep dives
SERVER_ID=30411                      # Verizon — New York, NY (your own ISP)
SPEEDTEST="/opt/homebrew/bin/speedtest"

# --- CSV header (created once) -------------------------------------------
if [ ! -f "$CSV" ]; then
  echo "timestamp_local,timestamp_utc,status,download_mbps,upload_mbps,idle_ping_ms,jitter_ms,packet_loss_pct,download_latency_loaded_ms,upload_latency_loaded_ms,interface,server,result_url" > "$CSV"
fi

LOCAL_TS=$(date '+%Y-%m-%d %H:%M:%S %Z')

# --- Run the test --------------------------------------------------------
JSON=$("$SPEEDTEST" --server-id="$SERVER_ID" --accept-license --accept-gdpr --format=json 2>>"$DIR/logs/errors.log")
EXIT=$?

if [ $EXIT -ne 0 ] || [ -z "$JSON" ]; then
  # Test failed to complete = a dropout. This is valuable evidence, log it.
  echo "$LOCAL_TS,,FAILED,,,,,,,,,$SERVER_ID," >> "$CSV"
  echo "{\"local\":\"$LOCAL_TS\",\"status\":\"FAILED\",\"exit\":$EXIT}" >> "$RAWLOG"
  exit 0
fi

echo "$JSON" >> "$RAWLOG"

# --- Parse JSON -> CSV row (python3 for safety) --------------------------
echo "$JSON" | python3 -c '
import json, sys
d = json.load(sys.stdin)
def mbps(b): return round(b * 8 / 1_000_000, 1)
row = [
    """'"$LOCAL_TS"'""",
    d.get("timestamp",""),
    "OK",
    str(mbps(d["download"]["bandwidth"])),
    str(mbps(d["upload"]["bandwidth"])),
    str(round(d["ping"]["latency"],1)),
    str(round(d["ping"]["jitter"],1)),
    str(d.get("packetLoss",0)),
    str(round(d["download"].get("latency",{}).get("high",0),1)),
    str(round(d["upload"].get("latency",{}).get("high",0),1)),
    d.get("interface",{}).get("name",""),
    str(d.get("server",{}).get("id","")),
    d.get("result",{}).get("url",""),
]
print(",".join(row))
' >> "$CSV"

# Refresh the visual dashboard after each test
python3 "$DIR/generate-dashboard.py" >/dev/null 2>&1

# Publish updated dashboard to GitHub Pages (non-fatal if offline)
cd "$DIR" && git add -A >/dev/null 2>&1 && \
  git commit -q -m "data $(date '+%Y-%m-%d %H:%M')" >/dev/null 2>&1 && \
  git push -q origin main >/dev/null 2>&1
true
