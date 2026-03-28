#!/bin/bash

# Usage:
# ./benchmark.sh "uv run receiver.py" duckdb

set -e

CMD="$1"
NAME="$2"

if [ -z "$CMD" ] || [ -z "$NAME" ]; then
  echo "Usage: $0 \"<receiver_command>\" <name>"
  exit 1
fi

# ---------------------------
# Create output directory
# ---------------------------
TS=$(date +%Y%m%d_%H%M%S)
OUTDIR="bench_${NAME}_${TS}"
mkdir -p "$OUTDIR"

PIDSTAT_CSV="${OUTDIR}/ps.csv"
APP_LOG="${OUTDIR}/app.log"
APP_CSV="${OUTDIR}/app.csv"

echo "Running benchmark: $NAME"
echo "Output directory: $OUTDIR"

# ---------------------------
# Start sender
# ---------------------------
uv run sender.py --mps 1000 > /dev/null 2>&1 &
SENDER_PID=$!
echo "Sender PID: $SENDER_PID"

sleep 2  # stabilize sender

# ---------------------------
# Start receiver
# ---------------------------
bash -c "$CMD" > "$APP_LOG" 2>&1 &
PID=$!

echo "Receiver root PID: $PID"

# ---------------------------
# Start ps sampling (0.1s)
# ---------------------------
echo "timestamp,pid,cpu_percent,rss_kb,vsz_kb,command" > "$PIDSTAT_CSV"

(
while kill -0 $PID 2>/dev/null; do
    ts=$(date +%H:%M:%S.%3N)

    ps -eo pid,ppid,%cpu,rss,vsz,comm | awk -v root=$PID -v ts="$ts" '
    {
        if ($1 == root || $2 == root) {
            print ts","$1","$3","$4","$5","$6
        }
    }'

    sleep 0.1
done
) >> "$PIDSTAT_CSV" &

PS_PID=$!

echo "Collecting metrics..."

# ---------------------------
# Wait for receiver
# ---------------------------
wait $PID

# stop sampler + sender
kill $PS_PID 2>/dev/null || true
kill $SENDER_PID 2>/dev/null || true

echo "Processing app output..."

# ---------------------------
# Convert JSON logs → CSV
# ---------------------------
echo "time_s,total_count" > "$APP_CSV"

grep -E '^\{' "$APP_LOG" | while read -r line; do
    time_s=$(echo "$line" | jq -r '.time_s')
    total_count=$(echo "$line" | jq -r '.total_count')
    echo "$time_s,$total_count" >> "$APP_CSV"
done

echo "Done!"
echo "Files in: $OUTDIR"
echo "  ps.csv       → system metrics"
echo "  app.csv      → app metrics"
echo "  app.log      → raw logs"