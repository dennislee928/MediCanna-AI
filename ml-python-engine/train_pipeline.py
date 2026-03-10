"""
MediCanna AI - 數據預處理與特徵工程
Phase 2: 讀取 CSV、缺失值填補、文本合併、SpaCy NLP 清洗
"""
import os
import pandas as pd


def load_dataset(data_path: str) -> pd.DataFrame:
    """讀取 Kaggle 大麻品種 CSV 資料集。"""
    return pd.read_csv(data_path)


def fill_missing_numeric(df: pd.DataFrame, column: str = "Rating") -> pd.DataFrame:
    """針對數值欄位（如 Rating）以中位數填補缺失值。"""
    df = df.copy()
    if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
        df[column] = df[column].fillna(df[column].median())
    return df


def build_combined_text(df: pd.DataFrame, effects_col: str = "Effects", flavor_col: str = "Flavor") -> pd.DataFrame:
    """將療效 (Effects) 與風味 (Flavor) 字串合併為 combined_text。"""
    df = df.copy()
    effects = df[effects_col].fillna("").astype(str)
    flavor = df[flavor_col].fillna("").astype(str)
    df["combined_text"] = (effects + " " + flavor).str.strip()
    return df


def clean_text_with_spacy(text: str, nlp) -> str:
    """
    使用 SpaCy 進行 NLP 清洗：轉小寫、去除標點與停用詞。
    nlp 應為已載入的 en_core_web_sm 模型。
    """
    if not text or not isinstance(text, str):
        return ""
    text = text.lower().strip()
    doc = nlp(text)
    tokens = [
        token.text
        for token in doc
        if not token.is_punct and not token.is_space and not token.is_stop
    ]
    return " ".join(tokens)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "data", "strains_dataset.csv")

    print("載入資料集...")
    df = load_dataset(data_path)

    print("填補數值缺失值 (Rating)...")
    df = fill_missing_numeric(df, "Rating")

    print("建立 combined_text (Effects + Flavor)...")
    df = build_combined_text(df, "Effects", "Flavor")

    print("下載/載入 SpaCy 英文模型 (en_core_web_sm)...")
    import sys
    import subprocess
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm")

    print("NLP 清洗 combined_text...")
    df["combined_text_cleaned"] = df["combined_text"].apply(lambda x: clean_text_with_spacy(x, nlp))

    print("預處理完成，前 3 筆 combined_text_cleaned:")
    print(df[["Name", "Type", "Rating", "combined_text_cleaned"]].head(3).to_string())
    return df


if __name__ == "__main__":
    main()
