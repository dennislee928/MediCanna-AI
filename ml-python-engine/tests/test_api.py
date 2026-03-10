import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy.sparse import csr_matrix

os.environ["ML_FAIL_FAST"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main as ml_main  # noqa: E402  pylint: disable=wrong-import-position


class DummyTfidf:
    def transform(self, _texts):
        return csr_matrix([[1.0, 0.0]])


class DummyTypeEncoder:
    def transform(self, _value):
        return csr_matrix([[1.0]])


class DummyKMeans:
    def predict(self, _value):
        return [0]


@pytest.fixture(autouse=True)
def seed_model_state():
    ml_main.MODELS = {
        "kmeans": DummyKMeans(),
        "tfidf": DummyTfidf(),
        "type_encoder": DummyTypeEncoder(),
    }
    ml_main.CLUSTERED_DF = pd.DataFrame(
        [
            {
                "Name": "Alpha",
                "Type": "Hybrid",
                "Rating": 4.8,
                "Effects": "Relaxed, Happy",
                "Flavor": "Sweet",
                "cluster": 0,
            },
            {
                "Name": "Beta",
                "Type": "Sativa",
                "Rating": 4.5,
                "Effects": "Energetic, Focused",
                "Flavor": "Citrus",
                "cluster": 0,
            },
            {
                "Name": "Gamma",
                "Type": "Indica",
                "Rating": 4.2,
                "Effects": "Sleepy, Relaxed",
                "Flavor": "Earthy",
                "cluster": 0,
            },
        ]
    )
    ml_main.READY = True
    ml_main.STARTUP_ERROR = None
    yield
    ml_main.READY = True


def test_blank_symptoms_returns_validation_error():
    client = TestClient(ml_main.app)
    res = client.post(
        "/api/predict",
        headers={"x-request-id": "test-blank"},
        json={"symptoms": " ", "avoid_effects": []},
    )
    assert res.status_code == 400
    payload = res.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["request_id"] == "test-blank"


def test_prediction_returns_meta_and_top3():
    client = TestClient(ml_main.app)
    res = client.post(
        "/api/predict",
        headers={"x-request-id": "req-ml-1"},
        json={"symptoms": "pain relief", "avoid_effects": []},
    )
    assert res.status_code == 200
    payload = res.json()
    assert len(payload["recommendations"]) == 3
    assert payload["meta"]["request_id"] == "req-ml-1"
    assert payload["meta"]["model_version"] == ml_main.MODEL_VERSION
    assert isinstance(payload["meta"]["warnings"], list)


def test_avoid_effects_filtering_removes_matching_effects():
    client = TestClient(ml_main.app)
    res = client.post(
        "/api/predict",
        json={"symptoms": "pain relief", "avoid_effects": ["sleepy"]},
    )
    assert res.status_code == 200
    names = [item["name"] for item in res.json()["recommendations"]]
    assert "Gamma" not in names


def test_filter_to_zero_applies_fallback_with_warning():
    ml_main.CLUSTERED_DF = pd.DataFrame(
        [
            {
                "Name": "OnlyOne",
                "Type": "Hybrid",
                "Rating": 4.9,
                "Effects": "Relaxed",
                "Flavor": "Pine",
                "cluster": 0,
            }
        ]
    )
    client = TestClient(ml_main.app)
    res = client.post(
        "/api/predict",
        json={"symptoms": "pain relief", "avoid_effects": ["relaxed"]},
    )
    assert res.status_code == 200
    payload = res.json()
    assert len(payload["recommendations"]) == 1
    assert "avoid_effects_filtered_all_candidates_fallback_applied" in payload["meta"]["warnings"]


def test_contract_error_shape():
    client = TestClient(ml_main.app)
    res = client.post("/api/predict", json={"avoid_effects": []})
    assert res.status_code == 400
    payload = res.json()
    assert set(payload.keys()) == {"error"}
    assert {"code", "message", "request_id"} <= set(payload["error"].keys())
