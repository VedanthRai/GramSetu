#!/usr/bin/env bash
# ONE command to rebuild every demo video after editing demo_assets/sentences.json:
#   bash scripts/build_video.sh            (or: make video)
# 1. re-auditions the Timbre voices and checks each utterance with live Prisma (only if sentences.json changed)
# 2. records a fresh LIVE take of all scenes (real Prisma, Timbre, Playwright, persisted demo records)
# 3. re-edits and re-exports every output into demo-output/final/ from demo-output/edit/edl.json
# 4. runs the QC suite (ffprobe, loudness, frames, sync, integrity, secret scan of outputs)
# Needs: the server running (scripts/dev.sh or uvicorn) with GNANI_API_KEY in .env, ffmpeg, Playwright Chromium.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"
if [ -x "$HOME/.venvs/gramsetu/Scripts/python" ]; then PY="$HOME/.venvs/gramsetu/Scripts/python"; fi
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi
BASE="${BASE:-http://127.0.0.1:8000}"
curl -sf "$BASE/api/health" >/dev/null || { echo "Start the server first (scripts/dev.sh)"; exit 1; }
# Stop before any phase if free disk drops below 2 GB (a take needs ~0.5 GB, rendering ~0.2 GB).
check_disk() {
  FREE_MB=$("$PY" -c "import shutil; print(shutil.disk_usage('.').free // 2**20)")
  echo "[disk] $1: ${FREE_MB} MB free"
  if [ "$FREE_MB" -lt 2048 ]; then echo "Stopping: less than 2 GB free before '$1'."; exit 2; fi
}

N=$(ls -d demo-output/takes/take* 2>/dev/null | sed 's/.*take//' | grep -E '^[0-9]+$' | sort -n | tail -1 || true)
TAKE=$(( ${N:-0} + 1 ))
check_disk "record take $TAKE"
"$PY" scripts/record_demo.py --live --take "$TAKE"
"$PY" - "$TAKE" <<'EOF'
import json, sys, pathlib
p = pathlib.Path("demo-output/edit/edl.json"); edl = json.loads(p.read_text(encoding="utf-8"))
edl["take"] = f"takes/take{sys.argv[1]}"; p.write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
EOF
check_disk "edit"
"$PY" scripts/edit_demo.py
check_disk "QC"
"$PY" scripts/qc_video.py
"$PY" scripts/demo/build_replay.py
# raw frames of the PREVIOUS takes are no longer needed once the new outputs passed QC (logs are kept)
if grep -q "QC issues: none" <("$PY" -c "import json;r=json.load(open('demo-output/qc/qc_report.json',encoding='utf-8'));print('QC issues: none' if not any(v['issues'] for v in r['videos']) and not r['secret_scan']['hits'] else 'QC issues')"); then
  for d in demo-output/takes/take*/; do
    [ "$d" = "demo-output/takes/take$TAKE/" ] || rm -rf "$d"frames_* "$d"agent_shots_* "$d"tts
  done
  rm -rf demo-output/edit/cache demo-output/edit/work
fi
check_disk "done"
echo "Done: demo-output/final/ (see demo-output/qc/qc_report.md)"
