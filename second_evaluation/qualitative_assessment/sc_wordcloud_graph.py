import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os

def generate_word_cloud(excel_file, text_column, width=1200, height=800, output_folder="output_wordcloud"):
    """
    Generates a word cloud from an Excel file and saves it as an image.

    :param excel_file: Path to the Excel file
    :param text_column: Name of the column from which the text will be extracted
    :param width: Width of the generated image
    :param height: Height of the generated image
    :param output_folder: Folder where the generated image will be saved
    """

    # Read Excel file
    df = pd.read_excel(excel_file)

    if text_column not in df.columns:
        raise ValueError(f"The column '{text_column}' does not exist in the file.")

    # Merge all text in the selected column
    text = " ".join(df[text_column].astype(str))

    # Create word cloud
    cloud = WordCloud(
        width=width,
        height=height,
        background_color="white",
        collocations=False
    ).generate(text)

    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Image path
    output_path = os.path.join(output_folder, "wordcloud.png")

    # Save the image
    cloud.to_file(output_path)

    # Display it
    plt.figure(figsize=(12, 8))
    plt.imshow(cloud, interpolation='bilinear')
    plt.axis('off')
    plt.show()

    print(f"✔ Word cloud generated and saved as: {output_path}")


# ------------------------------
# MAIN ENTRY POINT
# ------------------------------
if __name__ == "__main__":
    excel_file = "raw_data_questionnaires.xlsx"
    text_column = "Current country:"

    generate_word_cloud(excel_file, text_column)
