"""
MediCanna AI - 數據預處理、特徵工程與 K-Means 分群
Phase 2: 讀取 CSV、缺失值填補、文本合併、SpaCy NLP 清洗
Phase 3: TF-IDF、One-Hot Type、KMeans 訓練、模型儲存、clustered_strains 匯出
"""
import os
import sys
import subprocess
import pandas as pd
import numpy as np
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.cluster import KMeans
from scipy.sparse import hstack


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

    # --- Phase 3: TF-IDF、One-Hot、KMeans ---
    print("TF-IDF 轉換...")
    tfidf = TfidfVectorizer(max_features=500, min_df=1, stop_words="english")
    X_tfidf = tfidf.fit_transform(df["combined_text_cleaned"].fillna(""))

    print("Type 欄位 One-Hot Encoding...")
    type_encoder = OneHotEncoder(sparse_output=True, handle_unknown="ignore")
    type_col = df["Type"].fillna("Hybrid").values.reshape(-1, 1)
    X_type = type_encoder.fit_transform(type_col)

    print("合併特徵矩陣...")
    X = hstack([X_tfidf, X_type]).toarray()

    print("KMeans 分群 (n_clusters=5)...")
    n_clusters = 5
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(X)

    # 評估：各群集最常出現的關鍵字
    feature_names = list(tfidf.get_feature_names_out())
    print("\n各群集代表性關鍵字 (療效/風味):")
    for c in range(n_clusters):
        center = kmeans.cluster_centers_[c][: len(feature_names)]
        top_idx = np.argsort(center)[-5:][::-1]
        keywords = [feature_names[i] for i in top_idx if i < len(feature_names)]
        print(f"  Cluster {c}: {keywords}")

    # 儲存模型與向量器
    models_dir = os.path.join(base_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    joblib.dump(kmeans, os.path.join(models_dir, "kmeans_model.pkl"))
    joblib.dump(tfidf, os.path.join(models_dir, "tfidf_vectorizer.pkl"))
    print(f"\n已儲存: {models_dir}/kmeans_model.pkl, tfidf_vectorizer.pkl")

    # 匯出帶 cluster 的資料集
    out_path = os.path.join(base_dir, "data", "clustered_strains.csv")
    df.to_csv(out_path, index=False)
    print(f"已匯出: {out_path}")

    return df


if __name__ == "__main__":
    main()
