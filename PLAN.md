# Internet Speed Monitor — Implementation Plan

**Overall Progress:** `85%`

## TLDR
A set-it-and-forget-it macOS monitor that auto-runs an official Ookla speed test every 30 minutes against **Comcast's own NJ server**, logs each result (incl. failures) to a CSV, and generates an Xfinity-ready report quantifying how often your 1 Gbps plan underperforms. Goal: turn "my internet feels slow" into timestamped, ISP-can't-deny-it evidence.

## Critical Decisions
- **Tool: Ookla official `speedtest` CLI v1.2.0** — accurate, reports packet loss / jitter / latency-under-load, and gives a public shareable result URL per test.
- **Pinned to server 1767 (Comcast, Plainfield NJ)** — testing against Xfinity's *own* server removes the "it's the wider internet, not us" excuse.
- **Scheduler: macOS `launchd`** every 1800s, `RunAtLoad` on — native, survives reboot/login; runs only while Mac is awake (accepted).
- **Location: `~/internet-speed-monitor`** (NOT `~/Documents`) — Documents is macOS-privacy-protected and blocks background jobs from writing ("Operation not permitted"). This was found and fixed during setup.
- **Evidence strategy** — since a Mac (esp. over Wi-Fi) can't saturate a gig line, the report leans on metrics Xfinity *can't* blame on Wi-Fi: **failed tests/dropouts, packet loss, and latency-under-load (bufferbloat)**, alongside raw speeds.

## Tasks

- [x] 🟩 **Step 1: Install & verify the speed test tool**
  - [x] 🟩 Install Ookla `speedtest` CLI v1.2.0 via Homebrew (required trusting the tap)
  - [x] 🟩 Accept license/GDPR, confirm JSON output works
  - [x] 🟩 Pin to Comcast server 1767 (Plainfield, NJ)

- [x] 🟩 **Step 2: Build the logging script** (`run-speedtest.sh`)
  - [x] 🟩 One test in JSON mode → appends a row to `speedlog.csv`
  - [x] 🟩 Captures download/upload Mbps, idle ping, jitter, packet loss, loaded latency, interface, server, result URL
  - [x] 🟩 Logs FAILED rows on dropout (failures are evidence), keeps full JSON in `logs/raw.jsonl`
  - [x] 🟩 Verified: writes clean rows

- [x] 🟩 **Step 3: Schedule it every 30 minutes** (`launchd`)
  - [x] 🟩 `~/Library/LaunchAgents/com.kayu.speedmonitor.plist`, 1800s interval, RunAtLoad
  - [x] 🟩 Loaded and confirmed firing automatically (exit 0, writes rows unattended)
  - [x] 🟩 Survives reboot/login (LaunchAgent auto-loads)

- [x] 🟩 **Step 4: Build the Xfinity-ready report** (`report.py`)
  - [x] 🟩 Threshold set to 1000 Mbps plan
  - [x] 🟩 Summarizes avg/median/worst speeds, % below 90/50/25% of plan
  - [x] 🟩 Reliability section: dropouts, packet loss, bufferbloat
  - [x] 🟩 Worst-times-of-day breakdown by hour
  - [ ] 🟥 (Optional) speed-over-time chart — deferred unless you want a visual

- [ ] 🟥 **Step 5: Run the evidence campaign & hand off** *(your part — passive)*
  - [ ] 🟥 Let it collect for ~1–2 weeks (keep Mac awake; longer = stronger case)
  - [ ] 🟥 Run a few **wired-ethernet** tests to preempt the "it's your Wi-Fi" rebuttal
  - [ ] 🟥 Generate final report: `python3 ~/internet-speed-monitor/report.py --days 14`
  - [ ] 🟥 Share `speedlog.csv` + report with Xfinity
  - [ ] 🟥 Decide whether to keep running or unload the job once resolved

## How to use it
- **See the report anytime:** `python3 ~/internet-speed-monitor/report.py` (add `--days 14` to scope)
- **Run an extra test on demand:** `~/internet-speed-monitor/run-speedtest.sh`
- **Pause monitoring:** `launchctl bootout gui/$(id -u)/com.kayu.speedmonitor`
- **Resume:** `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kayu.speedmonitor.plist`
- **Raw data:** `~/internet-speed-monitor/speedlog.csv` (each row has a shareable speedtest.net link)
