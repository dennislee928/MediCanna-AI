"""
MediCanna AI - FastAPI 推論服務
啟動時載入 KMeans、TfidfVectorizer、type_encoder 與 clustered_strains；
POST /api/predict 依症狀推薦 Top 3 品種。
"""
import os
from contextlib import asynccontextmanager
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from scipy.sparse import hstack


# --- Pydantic 模型 ---
class SymptomRequest(BaseModel):
    symptoms: str
    avoid_effects: list[str] = []


class StrainItem(BaseModel):
    name: str
    type: str
    rating: float
    effects: str
    flavor: str


class RecommendationResponse(BaseModel):
    recommendations: list[StrainItem]


# 全域載入的模型與資料（在 lifespan 中填入）
MODELS = {}
CLUSTERED_DF: pd.DataFrame = None


def _load_models_and_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, "models")
    data_path = os.path.join(base_dir, "data", "clustered_strains.csv")
    kmeans = joblib.load(os.path.join(models_dir, "kmeans_model.pkl"))
    tfidf = joblib.load(os.path.join(models_dir, "tfidf_vectorizer.pkl"))
    type_encoder = joblib.load(os.path.join(models_dir, "type_encoder.pkl"))
    df = pd.read_csv(data_path)
    return {"kmeans": kmeans, "tfidf": tfidf, "type_encoder": type_encoder}, df


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODELS, CLUSTERED_DF
    MODELS, CLUSTERED_DF = _load_models_and_data()
    yield
    MODELS.clear()
    CLUSTERED_DF = None


app = FastAPI(title="MediCanna AI ML API", lifespan=lifespan)


@app.post("/api/predict", response_model=RecommendationResponse)
def predict(request: SymptomRequest):
    """依症狀與避免副作用，推薦 Top 3 品種。"""
    kmeans = MODELS["kmeans"]
    tfidf = MODELS["tfidf"]
    type_encoder = MODELS["type_encoder"]
    df = CLUSTERED_DF

    symptoms = (request.symptoms or "").strip().lower()
    if not symptoms:
        return RecommendationResponse(recommendations=[])

    # 症狀轉 TF-IDF 向量，Type 預設 Hybrid，合併後與訓練時維度一致
    X_tfidf = tfidf.transform([symptoms])
    X_type = type_encoder.transform([["Hybrid"]])
    X = hstack([X_tfidf, X_type]).toarray()
    cluster = int(kmeans.predict(X)[0])

    # 該群集內篩選：排除 avoid_effects，依 Rating 排序取 Top 3
    sub = df[df["cluster"] == cluster].copy()
    sub["Rating"] = pd.to_numeric(sub["Rating"], errors="coerce").fillna(0)

    avoid = set(e.strip().lower() for e in (request.avoid_effects or []) if e)
    if avoid:
        def has_avoid(effects):
            if pd.isna(effects):
                return False
            return any(a in str(effects).lower() for a in avoid)
        sub = sub[~sub["Effects"].apply(has_avoid)]

    sub = sub.sort_values("Rating", ascending=False).head(3)
    recommendations = [
        StrainItem(
            name=row.get("Name", ""),
            type=str(row.get("Type", "")),
            rating=float(row.get("Rating", 0)),
            effects=str(row.get("Effects", "")),
            flavor=str(row.get("Flavor", "")),
        )
        for _, row in sub.iterrows()
    ]
    return RecommendationResponse(recommendations=recommendations)


@app.get("/health")
def health():
    return {"status": "ok"}
