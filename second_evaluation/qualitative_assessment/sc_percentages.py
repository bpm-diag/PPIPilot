import pandas as pd

# === 1. Load Excel file ===
file = "questionnaire_answers.xlsx"
df = pd.read_excel(file)

# === 2. Select Likert columns (from E to Z) ===
likert_columns = df.columns[4:26]

# === 3. Standardize responses into categories ===
def unify_likert(value):
    v = str(value).strip().lower()
    if v in ["very high", "muy alto"]:
        return "Very High"
    elif v in ["high", "alto"]:
        return "High"
    elif v in ["moderate", "moderado"]:
        return "Moderate"
    elif v in ["low", "bajo"]:
        return "Low"
    elif v in ["very low", "muy bajo"]:
        return "Very Low"
    else:
        return "Other"

for col in likert_columns:
    df[col] = df[col].apply(unify_likert)

categories = ["Very High", "High", "Moderate", "Low", "Very Low"]

# === 4. Total percentage per question ===
total_percentage_per_question = {}
for col in likert_columns:
    counts = df[col].value_counts(normalize=True) * 100
    total_percentage_per_question[col] = counts.reindex(categories, fill_value=0)
df_total_percentage_per_question = pd.DataFrame(total_percentage_per_question).T

# === 5. Percentage per question and Role ===
rows = []
for role, group in df.groupby("Role"):
    for col in likert_columns:
        counts = group[col].value_counts(normalize=True) * 100
        row = counts.reindex(categories, fill_value=0)
        row["Role"] = role
        row["Question"] = col
        rows.append(row)
df_percentage_by_role_question = pd.DataFrame(rows)
df_percentage_by_role_question = df_percentage_by_role_question.set_index(["Role", "Question"])

# === 6. Internal distribution percentage by Role for each question and Likert value ===
# For each question and category, calculate what % belongs to each Role

# Prepare list to store results
rows_internal = []

for col in likert_columns:
    for cat in categories:
        # Filter rows where response is category 'cat' in question 'col'
        df_cat = df[df[col] == cat]

        # Count how many are in each Role
        counts_role = df_cat["Role"].value_counts(normalize=True) * 100

        # Fill missing Roles with 0
        counts_role = counts_role.reindex(["Academic", "Industry", "Student"], fill_value=0)

        # Add info to list
        row = counts_role.to_dict()
        row["Question"] = col
        row["Likert"] = cat
        rows_internal.append(row)

df_internal_distribution = pd.DataFrame(rows_internal)
df_internal_distribution = df_internal_distribution.set_index(["Question", "Likert"])

# === 7. Save results to Excel ===
output_file = "output_percentages.xlsx"
with pd.ExcelWriter(output_file) as writer:
    df_total_percentage_per_question.to_excel(writer, sheet_name="Total per Question")
    df_percentage_by_role_question.to_excel(writer, sheet_name="By Question and Role")
    df_internal_distribution.to_excel(writer, sheet_name="Internal Role Distribution")

print(f"\nFile generated: {output_file}")
