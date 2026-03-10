"""MediCanna ML inference API with production-oriented validation and observability."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from scipy.sparse import hstack

logger = logging.getLogger("medicanna_ml")
logging.basicConfig(level=logging.INFO, format="%(message)s")

TOP_K = int(os.getenv("TOP_K_RECOMMENDATIONS", "3"))
MIN_SYMPTOMS_LEN = int(os.getenv("MIN_SYMPTOMS_LEN", "3"))
MAX_SYMPTOMS_LEN = int(os.getenv("MAX_SYMPTOMS_LEN", "300"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "kmeans-v1")
FAIL_FAST = os.getenv("ML_FAIL_FAST", "true").lower() == "true"


class SymptomRequest(BaseModel):
    symptoms: str
    avoid_effects: list[str] = Field(default_factory=list)


class StrainItem(BaseModel):
    name: str
    type: str
    rating: float
    effects: str
    flavor: str


class ResponseMeta(BaseModel):
    request_id: str
    model_version: str
    warnings: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    recommendations: list[StrainItem]
    meta: ResponseMeta


class ApiError(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ApiError


MODELS: dict = {}
CLUSTERED_DF: pd.DataFrame | None = None
READY = False
STARTUP_ERROR: str | None = None


def _request_id_from_request(request: Request) -> str:
    request_id = request.headers.get("x-request-id", "").strip()
    return request_id or str(uuid.uuid4())


def _log_event(event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, ensure_ascii=True, default=str))


def _artifact_paths() -> dict[str, Path]:
    base_dir = Path(__file__).resolve().parent
    models_dir = Path(os.getenv("MODELS_DIR", str(base_dir / "models")))
    data_dir = Path(os.getenv("DATA_DIR", str(base_dir / "data")))
    return {
        "kmeans": models_dir / "kmeans_model.pkl",
        "tfidf": models_dir / "tfidf_vectorizer.pkl",
        "type_encoder": models_dir / "type_encoder.pkl",
        "clustered_strains": data_dir / "clustered_strains.csv",
    }


def _validate_artifacts(paths: dict[str, Path]) -> None:
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise RuntimeError(
            "Missing ML artifacts: "
            + ", ".join(missing)
            + ". Run `python bootstrap_models.py` to generate required files."
        )

    empty = [name for name, path in paths.items() if path.stat().st_size == 0]
    if empty:
        raise RuntimeError("ML artifacts exist but are empty: " + ", ".join(empty))


def _load_models_and_data(paths: dict[str, Path]) -> tuple[dict, pd.DataFrame]:
    kmeans = joblib.load(paths["kmeans"])
    tfidf = joblib.load(paths["tfidf"])
    type_encoder = joblib.load(paths["type_encoder"])
    df = pd.read_csv(paths["clustered_strains"])
    return {"kmeans": kmeans, "tfidf": tfidf, "type_encoder": type_encoder}, df


def _normalize_avoid_effects(raw_effects: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw_effects:
        trimmed = item.strip()
        if not trimmed:
            continue
        key = trimmed.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(key)
    return normalized


def _validate_symptoms(symptoms: str, request_id: str) -> str:
    value = (symptoms or "").strip().lower()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "symptoms is required",
                "request_id": request_id,
            },
        )
    if len(value) < MIN_SYMPTOMS_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"symptoms must be at least {MIN_SYMPTOMS_LEN} characters",
                "request_id": request_id,
            },
        )
    if len(value) > MAX_SYMPTOMS_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"symptoms must be at most {MAX_SYMPTOMS_LEN} characters",
                "request_id": request_id,
            },
        )
    return value


@asynccontextmanager
async def lifespan(_: FastAPI):
    global MODELS, CLUSTERED_DF, READY, STARTUP_ERROR
    try:
        paths = _artifact_paths()
        _validate_artifacts(paths)
        MODELS, CLUSTERED_DF = _load_models_and_data(paths)
        READY = True
        STARTUP_ERROR = None
        _log_event("ml_startup_ready", model_version=MODEL_VERSION)
    except Exception as exc:  # pylint: disable=broad-except
        READY = False
        STARTUP_ERROR = str(exc)
        _log_event("ml_startup_failed", error=str(exc))
        if FAIL_FAST:
            raise
    yield
    MODELS.clear()
    CLUSTERED_DF = None
    READY = False
    STARTUP_ERROR = "shutdown"


app = FastAPI(title="MediCanna AI ML API", lifespan=lifespan)


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(
            error=ApiError(code=code, message=message, request_id=request_id)
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = _request_id_from_request(request)
    _log_event(
        "ml_request_validation_failed",
        request_id=request_id,
        errors=exc.errors(),
    )
    return _error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="VALIDATION_ERROR",
        message="invalid request payload",
        request_id=request_id,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = _request_id_from_request(request)
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    code = str(detail.get("code", "HTTP_ERROR"))
    message = str(detail.get("message", exc.detail))
    request_id = str(detail.get("request_id", request_id))
    _log_event(
        "ml_http_exception",
        request_id=request_id,
        status=exc.status_code,
        code=code,
        message=message,
    )
    return _error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        request_id=request_id,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _request_id_from_request(request)
    _log_event(
        "ml_unhandled_exception",
        request_id=request_id,
        message=str(exc),
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="internal server error",
        request_id=request_id,
    )


@app.post("/api/predict", response_model=RecommendationResponse)
def predict(payload: SymptomRequest, request: Request):
    started_at = time.perf_counter()
    request_id = _request_id_from_request(request)
    _log_event("ml_request_started", request_id=request_id, route="/api/predict")

    if not READY or CLUSTERED_DF is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "MODEL_NOT_READY",
                "message": STARTUP_ERROR or "model not ready",
                "request_id": request_id,
            },
        )

    symptoms = _validate_symptoms(payload.symptoms, request_id)
    avoid_effects = _normalize_avoid_effects(payload.avoid_effects)
    warnings: list[str] = []

    kmeans = MODELS["kmeans"]
    tfidf = MODELS["tfidf"]
    type_encoder = MODELS["type_encoder"]
    df = CLUSTERED_DF.copy()

    x_tfidf = tfidf.transform([symptoms])
    x_type = type_encoder.transform([["Hybrid"]])
    x = hstack([x_tfidf, x_type]).toarray()
    cluster = int(kmeans.predict(x)[0])

    cluster_rows = df[df["cluster"] == cluster].copy()
    cluster_rows["Rating"] = pd.to_numeric(cluster_rows["Rating"], errors="coerce").fillna(0)
    ranked_rows = cluster_rows.sort_values("Rating", ascending=False)

    filtered_rows = ranked_rows
    if avoid_effects:
        def has_avoid(effects: object) -> bool:
            if pd.isna(effects):
                return False
            effect_text = str(effects).lower()
            return any(avoid in effect_text for avoid in avoid_effects)

        filtered_rows = ranked_rows[~ranked_rows["Effects"].apply(has_avoid)]

    if avoid_effects and filtered_rows.empty and not ranked_rows.empty:
        warnings.append("avoid_effects_filtered_all_candidates_fallback_applied")
        final_rows = ranked_rows.head(TOP_K)
    else:
        final_rows = filtered_rows.head(TOP_K)

    recommendations = [
        StrainItem(
            name=str(row.get("Name", "")),
            type=str(row.get("Type", "")),
            rating=float(row.get("Rating", 0)),
            effects=str(row.get("Effects", "")),
            flavor=str(row.get("Flavor", "")),
        )
        for _, row in final_rows.iterrows()
    ]

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    _log_event(
        "ml_request_completed",
        request_id=request_id,
        route="/api/predict",
        status=200,
        latency_ms=latency_ms,
        result_count=len(recommendations),
        warnings=warnings,
    )

    return RecommendationResponse(
        recommendations=recommendations,
        meta=ResponseMeta(
            request_id=request_id,
            model_version=MODEL_VERSION,
            warnings=warnings,
        ),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.get("/readyz")
def readyz():
    if READY:
        return {"status": "ready", "ready": True, "model_version": MODEL_VERSION}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "not_ready",
            "ready": False,
            "reason": STARTUP_ERROR or "unknown",
            "model_version": MODEL_VERSION,
        },
    )
