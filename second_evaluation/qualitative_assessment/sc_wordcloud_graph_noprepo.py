import pandas as pd
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import os

def generate_word_cloud(excel_file, text_column, width=1200, height=800, output_folder="output_wordcloud"):
    """
    Generates a word cloud from an Excel file, removing English and Spanish stopwords, 
    and saves it as an image.
    """

    # Read Excel file
    df = pd.read_excel(excel_file)

    if text_column not in df.columns:
        raise ValueError(f"The column '{text_column}' does not exist in the file.")

    # Merge all text in the selected column
    text = " ".join(df[text_column].astype(str))

    # Built-in English stopwords
    stopwords = set(STOPWORDS)

    # Custom English stopwords
    extra_english = {
        "the", "and", "to", "of", "in", "on", "at", "is", "it", "for", "with", "as", 
        "this", "that", "these", "those", "from", "by", "be", "an", "a"
    }

    # Custom Spanish stopwords
    extra_spanish = {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "de", "del", "al", "en", "y", "o", "que", "por", "para", 
        "es", "eso", "esa", "este", "esta", "ese", "a", "con", "sin"
    }

    # Combine all stopwords
    stopwords.update(extra_english)
    stopwords.update(extra_spanish)

    # Create word cloud
    cloud = WordCloud(
        width=width,
        height=height,
        background_color="white",
        collocations=False,
        stopwords=stopwords
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
    text_column = "Main areas of expertise:"

    generate_word_cloud(excel_file, text_column)
