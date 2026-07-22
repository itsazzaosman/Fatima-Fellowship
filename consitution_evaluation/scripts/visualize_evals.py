import os
import json
import glob
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Update this to the folder where your 19 JSON files are saved
LOGS_DIRECTORY = "clean_transcripts" 

def load_and_process_directory(directory_path):
    records = []
    
    # Create a search pattern to find all matching JSON files
    search_pattern = os.path.join(directory_path, "sd_*_transcript.json")
    file_list = glob.glob(search_pattern)
    
    print(f"Found {len(file_list)} transcript files to process.")
    
    for filepath in file_list:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Use json.load() because these are standard JSON files, not JSONL
                data = json.load(f)
                
                # Navigate to the judge scores
                transcript_id = data.get("transcript_id", os.path.basename(filepath))
                judge_data = data.get("judge", {})
                scores = judge_data.get("scores", {})
                
                # Flatten the dictionary so each tenet gets its own row
                for tenet, score in scores.items():
                    records.append({
                        "Transcript_ID": transcript_id,
                        "Tenet": tenet,
                        "Score": score
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    return pd.DataFrame(records)

def plot_stacked_bar(df):
    if df.empty:
        print("No data found. Please check your LOGS_DIRECTORY path.")
        return

    # Categorize the numeric scores based on your rubric definitions
    score_mapping = {
        1: "1 - Pass",
        2: "2 - Borderline Pass",
        3: "3 - Borderline Fail",
        4: "4 - Fail/Unsafe"
    }
    df['Score_Category'] = df['Score'].map(score_mapping)

    # Calculate the percentage of each score category per tenet
    crosstab = pd.crosstab(df['Tenet'], df['Score_Category'], normalize='index') * 100

    # Reorder columns for logical progression (Pass -> Fail)
    available_cols = [score_mapping[i] for i in range(1, 5) if score_mapping[i] in crosstab.columns]
    crosstab = crosstab[available_cols]

    # Set up a cleaner plot style
    sns.set_theme(style="white")
    
    # Modern, softer color palette
    color_dict = {
        "1 - Pass": '#4CAF50',             # Soft Green
        "2 - Borderline Pass": '#FFC107',  # Amber/Yellow
        "3 - Borderline Fail": '#FF9800',  # Orange
        "4 - Fail/Unsafe": '#F44336'       # Soft Red
    }
    colors = [color_dict[col] for col in available_cols]
    
    # Make the figure taller so the bars aren't squished
    fig, ax = plt.subplots(figsize=(12, 8))
    crosstab.plot(kind='barh', stacked=True, color=colors, width=0.75, ax=ax)

    # Clean formatting
    plt.title('Model Safety Performance by Tenet', fontsize=16, pad=20, fontweight='bold', color='#333333')
    plt.xlabel('Percentage of Scenarios (%)', fontsize=12, color='#555555', labelpad=10)
    plt.ylabel('Anthropic Tenet', fontsize=12, color='#555555', labelpad=10)
    
    # Format the legend cleanly outside the plot
    plt.legend(title="Evaluation Score", bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False)
    plt.xlim(0, 100)
    
    # Remove top, right, and left borders (spines) for a modern look
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#DDDDDD')
    
    # Add vertical gridlines to make percentages easy to read
    ax.xaxis.grid(True, linestyle='--', alpha=0.6, color='#EEEEEE')
    ax.set_axisbelow(True) # Put gridlines behind the bars

    plt.tight_layout()
    
    # Save the cleaned-up image
    os.makedirs('visuals', exist_ok=True)
    plt.savefig('visuals/tenet_performance_distribution_clean.png', dpi=300, bbox_inches='tight')
    print("Clean visualization saved to 'visuals/tenet_performance_distribution_clean.png'")
    plt.show()

if __name__ == "__main__":
    # Ensure LOGS_DIRECTORY matches where your JSON files are stored
    df = load_and_process_directory(LOGS_DIRECTORY)
    plot_stacked_bar(df)