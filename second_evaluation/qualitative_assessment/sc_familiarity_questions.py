import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import pi

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------

ORDINAL_MAP = {
    "Very high": 5,
    "Muy alto": 5,
    "High": 4,
    "Alto": 4,
    "Moderate": 3,
    "Moderado": 3,
    "Low": 2,
    "Bajo": 2,
    "Very low": 1,
    "Muy bajo": 1
}

LIKERT_COLUMNS = []

OUTPUT_FOLDER = "output_familiarity_questions"

# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------

def wrap_labels(labels, width=30):
    """Split long labels into multiple lines for better visualisation."""
    import textwrap
    return ['\n'.join(textwrap.wrap(label, width=width)) for label in labels]


def excel_col_to_index(col_letter):
    """Convert Excel column letter (A, B, ..., AA, AB, ...) to 0-based index"""
    col_letter = col_letter.upper()
    exp = 0
    col_index = 0
    for char in reversed(col_letter):
        col_index += (ord(char) - ord('A') + 1) * (26 ** exp)
        exp += 1
    return col_index - 1  # zero based

def get_likert_columns_by_letters(df, start_col_letter, end_col_letter):
    cols = df.columns.tolist()
    start_idx = excel_col_to_index(start_col_letter)
    end_idx = excel_col_to_index(end_col_letter)
    return cols[start_idx:end_idx + 1]

# ----------------------------------------------------------------------
# LOAD AND CLEAN DATA
# ----------------------------------------------------------------------

def load_and_prepare_data(excel_file, start_col_letter, end_col_letter):
    df = pd.read_excel(excel_file)
    
    global LIKERT_COLUMNS
    LIKERT_COLUMNS = get_likert_columns_by_letters(df, start_col_letter, end_col_letter)

    for col in LIKERT_COLUMNS:
        df[col] = df[col].map(ORDINAL_MAP)

    return df

# ----------------------------------------------------------------------
# RADAR CHART FUNCTION
# ----------------------------------------------------------------------

def radar_chart(data, group_name, title, output_name):
    labels = data.columns.tolist()
    num_vars = len(labels)
    
    angles = [n / float(num_vars) * 2 * pi for n in range(num_vars)]
    angles += angles[:1]
    
    plt.figure(figsize=(10, 8))
    ax = plt.subplot(111, polar=True)

    for group, values in data.iterrows():
        vals = values.tolist()
        vals += vals[:1]
        ax.plot(angles, vals, linewidth=2, label=str(group))
        ax.fill(angles, vals, alpha=0.2)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(wrap_labels(labels, width=25), fontsize=10)
    ax.tick_params(axis='x', pad=30)
    ax.set_title(title, size=14, weight="bold")
    ax.set_rlabel_position(0)
    plt.legend(
        title=group_name, 
        loc="upper right", 
        bbox_to_anchor=(1.4, 1.1)
    )

    plt.tight_layout()
    
    full_path = os.path.join(OUTPUT_FOLDER, output_name)
    plt.savefig(full_path, dpi=300)
    plt.show()
    plt.close()

# ----------------------------------------------------------------------
# DIVERGING LIKERT CHART
# ----------------------------------------------------------------------

def diverging_likert(df, output_name):
    dist = df[LIKERT_COLUMNS].apply(lambda col: col.value_counts(normalize=True)).fillna(0)
    dist = dist.sort_index()

    negative = dist.loc[[1, 2]].sum()
    neutral = dist.loc[[3]].sum()
    positive = dist.loc[[4, 5]].sum()

    x = np.arange(len(LIKERT_COLUMNS))

    plt.figure(figsize=(12, 8))
    plt.barh(x, negative, color="red", label="Low/Very Low")
    plt.barh(x, neutral, left=negative, color="gray", label="Moderate")
    plt.barh(x, positive, left=negative + neutral, color="green", label="High/Very High")

    plt.yticks(x, wrap_labels(LIKERT_COLUMNS, width=40), fontsize=10)
    plt.xlabel("Percentage")
    plt.title("Distribution of Familiarity with Process Domains and PPIs", fontsize=14, weight="bold")
    plt.legend()
    plt.tight_layout()
    
    full_path = os.path.join(OUTPUT_FOLDER, output_name)
    plt.savefig(full_path, dpi=300)
    plt.show()
    plt.close()

# ----------------------------------------------------------------------
# MAIN EXECUTION
# ----------------------------------------------------------------------

def generate_charts(excel_file, start_column_letter, end_column_letter):
    # Create output folder if not exists
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Folder '{OUTPUT_FOLDER}' created at: {os.path.abspath(OUTPUT_FOLDER)}")
    else:
        print(f"Folder '{OUTPUT_FOLDER}' already exists at: {os.path.abspath(OUTPUT_FOLDER)}")

    df = load_and_prepare_data(excel_file, start_column_letter, end_column_letter)

    grouped_B = df.groupby(df.columns[1])[LIKERT_COLUMNS].mean()
    radar_chart(grouped_B, group_name=df.columns[1],
                title="Familiarity with Process Domains and PPIs, Grouped by Role\n",
                output_name="radar_group_by_role.png")

    grouped_D = df.groupby(df.columns[3])[LIKERT_COLUMNS].mean()
    radar_chart(grouped_D, group_name=df.columns[3],
                title="Familiarity with Process Domains and PPIs, Grouped by Country\n",
                output_name="radar_group_by_country.png")

    diverging_likert(df, "diverging_likert.png")

    print("Charts generated successfully!")

# ----------------------------------------------------------------------
# RUN (example)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    generate_charts("questionnaire_answers.xlsx", start_column_letter="E", end_column_letter="M")
