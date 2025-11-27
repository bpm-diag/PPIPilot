import os
import math
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

data_file = "questionnaire_answers.xlsx"  # File path
output_folder = "output_boxplots"
os.makedirs(output_folder, exist_ok=True)

YAxisName = "Role"

df_dict = pd.read_excel(data_file, sheet_name=None)
print("Sheets available::", list(df_dict.keys()))
df = list(df_dict.values())[0]

print(f"Data loaded. Rows: {len(df)}, Columns: {len(df.columns)}")

# Normalizing texts
df = df.apply(lambda col: col.astype(str).str.strip().str.capitalize())

scale = {
    "Muy bajo": 1,
    "Bajo": 2,
    "Moderado": 3,
    "Alto": 4,
    "Muy alto": 5,
    "Very low": 1,
    "Low": 2,
    "Moderate": 3,
    "High": 4,
    "Very high": 5
}

columns_to_analyze = df.columns[15:26]
df_cod = df.copy()

for col in columns_to_analyze:
    df_cod[col] = df_cod[col].map(scale).astype(float)

orden_type = ["Industry", "Academic", "Student"]

# --- Saving each individual boxplot ---
for col in columns_to_analyze:
    fig_col, ax_col = plt.subplots(figsize=(7, 5))
    data_plot = df_cod[[YAxisName, col]].dropna(subset=[col, YAxisName]).copy()
    data_plot[col] = pd.to_numeric(data_plot[col], errors='coerce')

    groups_included = data_plot[YAxisName].unique()
    adjusted_order = [g for g in orden_type if g in groups_included]

    sns.boxplot(
        y=YAxisName, x=col,
        data=data_plot,
        ax=ax_col,
        order=adjusted_order,
        orient='h'
    )
    ax_col.set_xlabel("")
    ax_col.set_ylabel(YAxisName)
    ax_col.set_xlim(0.5, 5.5)
    ax_col.set_xticks([1, 2, 3, 4, 5])
    ax_col.set_title(f"{col}")

    ruta = os.path.join(output_folder, f"boxplot_{(col[:40]).replace(' ', '_')}.png")
    fig_col.savefig(ruta, bbox_inches="tight")
    plt.close(fig_col)

# --- Complete figure with all boxplots together ---
n = len(columns_to_analyze)
cols_grid = 4
rows_grid = math.ceil(n / cols_grid)
figsize = (cols_grid * 5, rows_grid * 4)

fig, axes = plt.subplots(rows_grid, cols_grid, figsize=figsize, constrained_layout=True)
axes = axes.flatten()

for i, col in enumerate(columns_to_analyze):
    ax = axes[i]
    data_plot = df_cod[[YAxisName, col]].dropna(subset=[col, YAxisName]).copy()
    data_plot[col] = pd.to_numeric(data_plot[col], errors='coerce')

    groups_included = data_plot[YAxisName].unique()
    adjusted_order = [g for g in orden_type if g in groups_included]

    sns.boxplot(
        y=YAxisName, x=col,
        data=data_plot,
        ax=ax,
        order=adjusted_order,
        orient='h'
    )
    ax.set_xlabel("")
    ax.set_ylabel(YAxisName)
    ax.set_xlim(0.5, 5.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_title(f"{col}")

# Remove excess axes
for j in range(i + 1, len(axes)):
    fig.delaxes(axes[j])

ruta_completa = os.path.join(output_folder, "all_boxplots.png")
fig.savefig(ruta_completa, dpi=300, bbox_inches="tight")
plt.show()
