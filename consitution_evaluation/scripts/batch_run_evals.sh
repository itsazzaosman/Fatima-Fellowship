#!/usr/bin/env bash
# batch_run_evals.sh
#
# Runs petri/audit for every sd_XXX_seed.json / sd_XXX_rubric.json pair
# found in seeds/ and rubrics/, saving each run's transcript to its own
# isolated folder (outputs/sd_XXX/) so results don't collide, then
# immediately cleaning each transcript into clean_transcripts/sd_XXX_transcript.json.
#
# Run this from the project root (consitution_evaluation/), with your
# virtualenv already activated.
#
# Usage:
#   bash scripts/batch_run_evals.sh
#
# Adjust START / END / models / max turns below as needed.

set -e

AUDITOR_MODEL="openrouter/anthropic/claude-sonnet-4.5"
TARGET_MODEL="openrouter/anthropic/claude-sonnet-4.5"
JUDGE_MODEL="openrouter/openai/gpt-4o"
MAX_TURNS=5

START=1
END=19

for i in $(seq $START $END); do
  EVAL_ID="sd_$(printf '%03d' $i)"
  SEED_FILE="seeds/${EVAL_ID}_seed.json"
  RUBRIC_FILE="rubrics/${EVAL_ID}_rubric.json"
  OUT_DIR="outputs/${EVAL_ID}"

  if [[ ! -f "$SEED_FILE" ]]; then
    echo "Skipping $EVAL_ID: missing $SEED_FILE"
    continue
  fi
  if [[ ! -f "$RUBRIC_FILE" ]]; then
    echo "Skipping $EVAL_ID: missing $RUBRIC_FILE"
    continue
  fi

  echo ""
  echo "================================================================"
  echo "  Running $EVAL_ID"
  echo "================================================================"

  inspect eval petri/audit \
    --model-role auditor="$AUDITOR_MODEL" \
    --model-role target="$TARGET_MODEL" \
    --model-role judge="$JUDGE_MODEL" \
    -T seed_instructions="$SEED_FILE" \
    -T custom_rubric="$RUBRIC_FILE" \
    -T max_turns=$MAX_TURNS \
    -T transcript_save_dir="$OUT_DIR"

  echo "  Cleaning transcript for $EVAL_ID ..."
  python scripts/dump_petri_clean_json.py "$OUT_DIR" -o clean_transcripts --name "${EVAL_ID}_transcript"
done

echo ""
echo "All done. Clean transcripts are in clean_transcripts/"