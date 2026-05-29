#!/bin/bash
# run.sh — Process all CCTV clips and emit events.

set -e

CLIPS_DIR="${1:-./data/clips}"
LAYOUT="${2:-./data/store_layout.json}"
OUTPUT="${3:-./data/events.jsonl}"

echo "========================================"
echo " Store Intelligence — Detection Pipeline"
echo "========================================"
echo "Clips  : $CLIPS_DIR"
echo "Layout : $LAYOUT"
echo "Output : $OUTPUT"
echo ""

python pipeline/detect.py \
    --clips-dir "$CLIPS_DIR" \
    --layout    "$LAYOUT" \
    --output    "$OUTPUT" \
    --model     yolov8s.pt

echo ""
echo "Pipeline complete. Events: $OUTPUT"
