#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE="$ROOT_DIR/fankha-full.txt"

echo "Building combined corpus file: $OUTPUT_FILE ..."
> "$OUTPUT_FILE"

for vol in $(seq -w 1 34); do
    VOL_FILE="$ROOT_DIR/text/fahares_vol_${vol}.txt"
    if [ -f "$VOL_FILE" ]; then
        echo "Appending volume $vol ..."
        cat "$VOL_FILE" >> "$OUTPUT_FILE"
        printf "\n\n" >> "$OUTPUT_FILE"
    else
        echo "Warning: $VOL_FILE not found!" >&2
    fi
done

echo "Done! Generated $OUTPUT_FILE ($(du -h "$OUTPUT_FILE" | cut -f1))"
