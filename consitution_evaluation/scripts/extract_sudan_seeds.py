import os
import re
import json

def parse_markdown_to_json(md_filepath, json_filepath, jsonl_filepath):
    if not os.path.exists(md_filepath):
        print(f"❌ Error: File not found at '{md_filepath}'")
        return

    scenarios = []
    current_category = "General"
    eval_counter = 1

    # Regex patterns
    category_pattern = re.compile(r"^##\s+(?:[IVX]+\.\s*)?(.*)")
    tenet_id_pattern = re.compile(r"T\d+\.\d+[a-z]?")

    with open(md_filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line_str = line.strip()

        # Check for category section headers (e.g., "## I. War, Conflict...")
        cat_match = category_pattern.match(line_str)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        # Check if the line is part of a table (contains a pipe) and is not a separator (---)
        if "|" in line_str and "---" not in line_str:
            # Split the line by pipes
            columns = [col.strip() for col in line_str.split("|")]
            
            # Clean up empty strings caused by leading or trailing outer pipes
            if columns and columns[0] == "":
                columns = columns[1:]
            if columns and columns[-1] == "":
                columns = columns[:-1]

            # If we successfully parsed 4 or more columns
            if len(columns) >= 4:
                trap_type = columns[0]
                
                # Skip the header row
                if trap_type.lower() == "taxonomy aspect":
                    continue

                raw_prompt = columns[1]
                
                # Remove surrounding quotes from the prompt if present
                if raw_prompt.startswith('"') and raw_prompt.endswith('"'):
                    raw_prompt = raw_prompt[1:-1].strip()

                target_tenets_raw = columns[2]
                failure_condition = columns[3]

                # Extract tenet IDs like ["T10.6a", "T11.4a"]
                target_tenets = tenet_id_pattern.findall(target_tenets_raw)

                eval_id = f"SD_{eval_counter:03d}"
                eval_counter += 1

                scenario = {
                    "eval_id": eval_id,
                    "category": current_category,
                    "trap_type": trap_type,
                    "prompt": raw_prompt,
                    "target_tenets": target_tenets,
                    "grading_rubric": failure_condition
                }

                scenarios.append(scenario)

    # Programmatically generate destination folders if they do not exist
    os.makedirs(os.path.dirname(json_filepath), exist_ok=True)
    os.makedirs(os.path.dirname(jsonl_filepath), exist_ok=True)

    # Save as formatted JSON array
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, indent=4, ensure_ascii=False)

    # Save as JSONL (one JSON object per line)
    with open(jsonl_filepath, "w", encoding="utf-8") as f:
        for scenario in scenarios:
            f.write(json.dumps(scenario, ensure_ascii=False) + "\n")

    print(f"🎉 Successfully parsed {len(scenarios)} scenarios!")
    print(f"📁 JSON output saved to: {json_filepath}")
    print(f"📁 JSONL output saved to: {jsonl_filepath}")

if __name__ == "__main__":
    # Ensure adversarial_taxonomy_sudan.md is in your root consitution_evaluation folder
    md_file = "adversarial_taxonomy_sudan.md"
    json_output = "seeds/sudan_evals.json"
    jsonl_output = "seeds/sudan_evals.jsonl"

    parse_markdown_to_json(md_file, json_output, jsonl_output)