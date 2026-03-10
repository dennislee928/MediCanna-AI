use axum::{
    extract::State,
    http::{HeaderMap, StatusCode},
    response::{IntoResponse, Response},
    Json,
};
use reqwest::Client;
use std::collections::HashSet;
use std::time::Instant;
use tracing::{error, info};
use uuid::Uuid;

use crate::models::{ApiError, ErrorEnvelope, HealthResponse, SymptomRequest};
use crate::services::{check_ml_readiness, fetch_recommendations_from_ml, MlServiceError};

const MIN_SYMPTOMS_LEN: usize = 3;
const MAX_SYMPTOMS_LEN: usize = 300;

#[derive(Clone)]
pub struct AppState {
    pub http_client: Client,
    pub ml_predict_url: String,
    pub ml_health_url: String,
}

fn request_id_from_headers(headers: &HeaderMap) -> String {
    headers
        .get("x-request-id")
        .and_then(|v| v.to_str().ok())
        .filter(|v| !v.trim().is_empty())
        .map(|v| v.to_string())
        .unwrap_or_else(|| Uuid::new_v4().to_string())
}

fn json_error(status: StatusCode, code: &str, message: String, request_id: String) -> Response {
    (
        status,
        Json(ErrorEnvelope {
            error: ApiError {
                code: code.to_string(),
                message,
                request_id,
            },
        }),
    )
        .into_response()
}

fn normalize_avoid_effects(raw: &[String]) -> Vec<String> {
    let mut dedupe = HashSet::<String>::new();
    let mut normalized = Vec::<String>::new();

    for effect in raw {
        let trimmed = effect.trim();
        if trimmed.is_empty() {
            continue;
        }
        let key = trimmed.to_lowercase();
        if dedupe.insert(key) {
            normalized.push(trimmed.to_string());
        }
    }
    normalized
}

pub async fn get_recommendation_handler(
    State(state): State<AppState>,
    headers: HeaderMap,
    Json(payload): Json<SymptomRequest>,
) -> Response {
    let started_at = Instant::now();
    let request_id = request_id_from_headers(&headers);
    info!(target = "gateway.request", request_id = %request_id, route = "/api/v1/recommend", event = "request_started");

    let symptoms = payload.symptoms.trim();
    if symptoms.is_empty() {
        return json_error(
            StatusCode::BAD_REQUEST,
            "VALIDATION_ERROR",
            "symptoms is required".to_string(),
            request_id,
        );
    }
    if symptoms.len() < MIN_SYMPTOMS_LEN {
        return json_error(
            StatusCode::BAD_REQUEST,
            "VALIDATION_ERROR",
            format!("symptoms must be at least {MIN_SYMPTOMS_LEN} characters"),
            request_id,
        );
    }
    if symptoms.len() > MAX_SYMPTOMS_LEN {
        return json_error(
            StatusCode::BAD_REQUEST,
            "VALIDATION_ERROR",
            format!("symptoms must be at most {MAX_SYMPTOMS_LEN} characters"),
            request_id,
        );
    }

    let body = SymptomRequest {
        symptoms: symptoms.to_string(),
        avoid_effects: normalize_avoid_effects(&payload.avoid_effects),
    };

    let response = match fetch_recommendations_from_ml(
        &state.http_client,
        &state.ml_predict_url,
        &body,
        &request_id,
    )
    .await
    {
        Ok(mut res) => {
            if res.meta.request_id.trim().is_empty() {
                res.meta.request_id = request_id.clone();
            }
            info!(
                target = "gateway.request",
                request_id = %request_id,
                route = "/api/v1/recommend",
                status = 200,
                latency_ms = started_at.elapsed().as_millis() as u64,
                event = "request_completed"
            );
            (StatusCode::OK, Json(res)).into_response()
        }
        Err(err) => {
            let (status, code, message) = match err {
                MlServiceError::Timeout(msg) => (StatusCode::BAD_GATEWAY, "UPSTREAM_TIMEOUT", msg),
                MlServiceError::Connection(msg) => {
                    (StatusCode::BAD_GATEWAY, "UPSTREAM_UNAVAILABLE", msg)
                }
                MlServiceError::UpstreamStatus(upstream, msg) => (
                    StatusCode::BAD_GATEWAY,
                    "UPSTREAM_ERROR",
                    format!("ML upstream returned {upstream}: {msg}"),
                ),
                MlServiceError::Parse(msg) => {
                    (StatusCode::BAD_GATEWAY, "UPSTREAM_INVALID_RESPONSE", msg)
                }
            };

            error!(
                target = "gateway.request",
                request_id = %request_id,
                route = "/api/v1/recommend",
                status = status.as_u16(),
                latency_ms = started_at.elapsed().as_millis() as u64,
                error_code = code,
                error_message = %message,
                event = "request_failed"
            );
            json_error(status, code, message, request_id)
        }
    };

    response
}

pub async fn healthz_handler() -> impl IntoResponse {
    Json(HealthResponse {
        status: "ok".to_string(),
        ready: true,
    })
}

pub async fn readyz_handler(State(state): State<AppState>, headers: HeaderMap) -> Response {
    let request_id = request_id_from_headers(&headers);
    match check_ml_readiness(&state.http_client, &state.ml_health_url, &request_id).await {
        Ok(()) => (
            StatusCode::OK,
            Json(HealthResponse {
                status: "ready".to_string(),
                ready: true,
            }),
        )
            .into_response(),
        Err(err) => {
            let message = format!("gateway dependency not ready: {err:?}");
            error!(
                target = "gateway.readiness",
                request_id = %request_id,
                status = 503,
                error_message = %message,
                event = "readiness_failed"
            );
            (
                StatusCode::SERVICE_UNAVAILABLE,
                Json(HealthResponse {
                    status: "not_ready".to_string(),
                    ready: false,
                }),
            )
                .into_response()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::ErrorEnvelope;
    use axum::{body, routing::post, Router};
    use serde_json::json;
    use tower::ServiceExt;

    fn state_for_tests(url: &str) -> AppState {
        AppState {
            http_client: Client::builder()
                .timeout(std::time::Duration::from_secs(2))
                .build()
                .expect("client"),
            ml_predict_url: url.to_string(),
            ml_health_url: url.replace("/api/predict", "/readyz"),
        }
    }

    async fn spawn_predict_server(status: StatusCode, body: serde_json::Value) -> String {
        async fn predict_ok() -> Json<serde_json::Value> {
            Json(json!({
                "recommendations":[
                    {"name":"A","type":"Hybrid","rating":4.2,"effects":"Relaxed","flavor":"Sweet"}
                ],
                "meta":{"request_id":"ml-1","model_version":"kmeans-v1","warnings":[]}
            }))
        }
        async fn predict_bad() -> (StatusCode, Json<serde_json::Value>) {
            (
                StatusCode::BAD_REQUEST,
                Json(
                    json!({"error":{"code":"VALIDATION_ERROR","message":"bad input","request_id":"ml-2"}}),
                ),
            )
        }

        let app = if status == StatusCode::OK {
            Router::new().route("/api/predict", post(predict_ok))
        } else {
            let _ = body;
            Router::new().route("/api/predict", post(predict_bad))
        };
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind listener");
        let addr = listener.local_addr().expect("local addr");
        tokio::spawn(async move {
            axum::serve(listener, app).await.expect("serve");
        });
        format!("http://{addr}/api/predict")
    }

    #[tokio::test]
    async fn validation_blank_symptoms_returns_error_envelope() {
        let url = spawn_predict_server(StatusCode::OK, json!({})).await;
        let state = state_for_tests(&url);
        let app = Router::new()
            .route("/api/v1/recommend", post(get_recommendation_handler))
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::post("/api/v1/recommend")
                    .header("content-type", "application/json")
                    .body(body::Body::from(r#"{"symptoms":"  ","avoid_effects":[]}"#))
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
        let bytes = body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read body");
        let envelope: ErrorEnvelope = serde_json::from_slice(&bytes).expect("parse error");
        assert_eq!(envelope.error.code, "VALIDATION_ERROR");
    }

    #[tokio::test]
    async fn upstream_failure_maps_to_bad_gateway() {
        let url = spawn_predict_server(StatusCode::BAD_REQUEST, json!({})).await;
        let state = state_for_tests(&url);
        let app = Router::new()
            .route("/api/v1/recommend", post(get_recommendation_handler))
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::post("/api/v1/recommend")
                    .header("content-type", "application/json")
                    .body(body::Body::from(
                        r#"{"symptoms":"pain relief","avoid_effects":[]}"#,
                    ))
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
        let bytes = body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read body");
        let envelope: ErrorEnvelope = serde_json::from_slice(&bytes).expect("parse error");
        assert_eq!(envelope.error.code, "UPSTREAM_ERROR");
    }

    #[tokio::test]
    async fn success_response_contains_meta() {
        let url = spawn_predict_server(StatusCode::OK, json!({})).await;
        let state = state_for_tests(&url);
        let app = Router::new()
            .route("/api/v1/recommend", post(get_recommendation_handler))
            .with_state(state);

        let response = app
            .oneshot(
                axum::http::Request::post("/api/v1/recommend")
                    .header("content-type", "application/json")
                    .header("x-request-id", "req-gw-1")
                    .body(body::Body::from(
                        r#"{"symptoms":"pain relief","avoid_effects":[]}"#,
                    ))
                    .expect("request"),
            )
            .await
            .expect("response");

        assert_eq!(response.status(), StatusCode::OK);
        let bytes = body::to_bytes(response.into_body(), usize::MAX)
            .await
            .expect("read body");
        let data: serde_json::Value = serde_json::from_slice(&bytes).expect("parse response");
        assert_eq!(data["meta"]["request_id"], "ml-1");
        assert_eq!(data["meta"]["model_version"], "kmeans-v1");
    }
}
