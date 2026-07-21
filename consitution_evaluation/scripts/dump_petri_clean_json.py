"""
dump_petri_clean_json.py

Reads petri's raw transcript JSON files (written by petri's save_transcripts
cleanup hook) and produces one clean, organized JSON file per transcript:

{
  "transcript_id": "...",
  "auditor_model": "...",
  "target_model": "...",
  "created_at": "...",
  "seed_instruction": "...",
  "turns": [
    {
      "turn_index": 1,
      "auditor_generation_turn": 1,
      "action": "send_message",
      "auditor_prompt": "...",
      "prefill": null,
      "target_response": "..."
    },
    {
      "turn_index": 2,
      "auditor_generation_turn": 2,
      "action": "rollback",
      "rolled_back_to_index": 0
    },
    ...
  ],
  "judge": {
    "summary": "...",
    "justification": "...",
    "scores": {"...": 1},
    "score_descriptions": {"...": "..."}
  }
}

"turn_index" counts every individual action (each send_message or rollback).
"auditor_generation_turn" counts each time the auditor MODEL was called to
generate a decision (i.e. each iteration of petri's max_turns loop) -- a
single generation turn can bundle multiple actions together (e.g. a rollback
+ a new send_message in the same turn), so several turn_index entries can
share the same auditor_generation_turn number. This is why you can see more
turn_index entries than the max_turns value you passed to the eval.

This reconstructs the FULL sequence of auditor attempts (including ones that
were later rolled back/retried), not just the final surviving conversation
state -- unlike the "target_messages" field, which only has the final path.

Usage:
    python dump_petri_clean_json.py outputs -o clean_transcripts
    python dump_petri_clean_json.py outputs/some_transcript.json -o clean_transcripts --name sd_001_transcript
"""

import argparse
import json
import sys
from pathlib import Path


def _content_to_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(block["text"])
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


def extract_turns(events: list) -> list:
    """
    Walk the decision_event stream in order and reconstruct every
    auditor-prompt -> target-response pair, plus rollback markers.

    Each decision_event with source == "Auditor" represents ONE call to the
    auditor model (i.e. one iteration of petri's max_turns loop). That single
    call can include multiple tool calls (e.g. rollback_conversation AND
    send_message together), which we split into separate turn_index entries
    while tagging them all with the same auditor_generation_turn number.
    """
    turns = []
    turn_index = 0
    auditor_generation_turn = 0

    decision_events = [e for e in events if e.get("type") == "decision_event"]

    i = 0
    while i < len(decision_events):
        event = decision_events[i]
        content = event.get("content")

        # content can be a string (e.g. the very first seed instruction event)
        # or a dict (an actual model decision with role/tool_calls/etc.)
        if isinstance(content, dict):
            source = (content.get("metadata") or {}).get("source")
            role = content.get("role")
            tool_calls = content.get("tool_calls") or []

            if source == "Auditor" and role == "assistant":
                auditor_generation_turn += 1

                # Look for a send_message tool call -> this is a real prompt to the target
                send_msg_call = next((tc for tc in tool_calls if tc.get("function") == "send_message"), None)
                rollback_call = next((tc for tc in tool_calls if tc.get("function") == "rollback_conversation"), None)

                if rollback_call:
                    turn_index += 1
                    turns.append({
                        "turn_index": turn_index,
                        "auditor_generation_turn": auditor_generation_turn,
                        "action": "rollback",
                        "rolled_back_to_index": (rollback_call.get("arguments") or {}).get("index"),
                    })

                if send_msg_call:
                    args = send_msg_call.get("arguments") or {}
                    prompt_text = args.get("message", "")
                    prefill_text = args.get("prefill")

                    # The target's reply is the NEXT decision_event whose source is "Target"
                    target_reply = None
                    j = i + 1
                    while j < len(decision_events):
                        next_content = decision_events[j].get("content")
                        if isinstance(next_content, dict):
                            next_source = (next_content.get("metadata") or {}).get("source")
                            if next_source == "Target":
                                target_reply = _content_to_text(next_content.get("content"))
                                break
                            if next_source == "Auditor":
                                # another auditor turn started before a target reply showed up
                                break
                        j += 1

                    turn_index += 1
                    turns.append({
                        "turn_index": turn_index,
                        "auditor_generation_turn": auditor_generation_turn,
                        "action": "send_message",
                        "auditor_prompt": prompt_text,
                        "prefill": prefill_text,
                        "target_response": target_reply,
                    })

            elif source == "Target" and role == "assistant":
                # Already consumed as part of the preceding send_message turn (if any).
                # If it wasn't consumed (e.g. no matching auditor turn found), record it standalone.
                already_captured = any(
                    t.get("action") == "send_message" and t.get("target_response") == _content_to_text(content.get("content"))
                    for t in turns
                )
                if not already_captured:
                    turn_index += 1
                    turns.append({
                        "turn_index": turn_index,
                        "auditor_generation_turn": auditor_generation_turn,
                        "action": "target_response_only",
                        "target_response": _content_to_text(content.get("content")),
                    })

        i += 1

    return turns


def clean_transcript(json_path: Path) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    judge_output = metadata.get("judge_output", {})
    events = data.get("events", [])

    turns = extract_turns(events)

    cleaned = {
        "transcript_id": metadata.get("transcript_id", json_path.stem),
        "auditor_model": metadata.get("auditor_model"),
        "target_model": metadata.get("target_model"),
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "seed_instruction": metadata.get("seed_instruction"),
        "turns": turns,
        "judge": {
            "summary": judge_output.get("summary"),
            "justification": judge_output.get("justification"),
            "scores": judge_output.get("scores", {}),
            "score_descriptions": judge_output.get("score_descriptions", {}),
        },
    }
    return cleaned


def main():
    parser = argparse.ArgumentParser(description="Extract clean, organized JSON from raw petri transcript files.")
    parser.add_argument("path", help="Path to a transcript .json file, or a directory containing them")
    parser.add_argument("-o", "--output", default="clean_transcripts", help="Output folder (default: clean_transcripts)")
    parser.add_argument(
        "--name",
        default=None,
        help="Custom output filename (without .json), only used when processing a single input file. "
             "E.g. --name sd_001_transcript writes clean_transcripts/sd_001_transcript.json",
    )
    args = parser.parse_args()

    input_path = Path(args.path)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_dir():
        json_files = sorted(input_path.glob("*.json"))
        if not json_files:
            print(f"No .json files found in {input_path}")
            sys.exit(1)
        if args.name and len(json_files) > 1:
            print("Note: --name is ignored when a directory contains multiple files; "
                  "each output uses its transcript_id instead.")
    elif input_path.is_file():
        json_files = [input_path]
    else:
        print(f"Path not found: {input_path}")
        sys.exit(1)

    for f in json_files:
        try:
            cleaned = clean_transcript(f)

            if args.name and len(json_files) == 1:
                safe_id = args.name
            else:
                safe_id = str(cleaned["transcript_id"]).replace("/", "_").replace("\\", "_")

            out_file = out_dir / f"{safe_id}.json"
            out_file.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Wrote {out_file}")
        except Exception as e:
            print(f"Skipped {f} due to error: {e}")

    print(f"\nDone. Clean transcripts written under: {out_dir.resolve()}")


if __name__ == "__main__":
    main()