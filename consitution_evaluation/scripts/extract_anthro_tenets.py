import re
import json
import os

def clean_citations(text):
    """
    Removes inline citation links like:
    ([constitutions/anthropic_soul_doc.md:159-167](../constitutions/anthropic_soul_doc.md#L159-L167))
    ([constitutions/anthropic_soul_doc.md:1157](../constitutions/anthropic_soul_doc.md#L1157))
    ([constitutions/anthropic_soul_doc.md:253-270](../constitutions/anthropic_soul_doc.md#L253-L270), 302-306)
    """
    pattern = re.compile(
        r"\(\[constitutions/anthropic_soul_doc\.md:\d+(?:-\d+)?\]"   # [constitutions/...md:159-167]
        r"\(\.\./constitutions/anthropic_soul_doc\.md#L\d+(?:-L\d+)?\)"  # (../...md#L159-L167)
        r"(?:,\s*\d+(?:-\d+)?)*\)"                                    # optional trailing ", 302-306)"
    )
    cleaned = pattern.sub("", text)
    # Collapse leftover double spaces and fix spacing before punctuation
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)
    return cleaned.strip()


def clean_existing_json(json_filepath):
    if not os.path.exists(json_filepath):
        print(f"❌ ERROR: Cannot find the JSON file at:\n{json_filepath}")
        return

    with open(json_filepath, "r", encoding="utf-8") as f:
        tenets = json.load(f)

    cleaned_tenets = {k: clean_citations(v) for k, v in tenets.items()}

    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(cleaned_tenets, f, indent=4)

    print(f"🎉 Cleaned {len(cleaned_tenets)} tenets in '{json_filepath}'")


if __name__ == "__main__":
    # Use a path relative to this script's location so it works regardless of
    # the Windows username or which directory you run it from
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    json_file = os.path.join(project_root, "anthropic_tenets", "tenets.json")

    clean_existing_json(json_file)