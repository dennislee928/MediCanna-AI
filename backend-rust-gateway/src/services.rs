use crate::models::{ErrorEnvelope, RecommendationResponse, SymptomRequest};
use reqwest::Client;
use std::time::Duration;

pub const DEFAULT_ML_PREDICT_URL: &str = "http://localhost:8000/api/predict";
pub const DEFAULT_TIMEOUT_SECS: u64 = 10;

#[derive(Debug)]
pub enum MlServiceError {
    Timeout(String),
    Connection(String),
    UpstreamStatus(u16, String),
    Parse(String),
}

pub fn ml_predict_url_from_env() -> String {
    std::env::var("ML_PREDICT_URL").unwrap_or_else(|_| DEFAULT_ML_PREDICT_URL.to_string())
}

pub fn ml_health_url_from_predict_url(predict_url: &str) -> String {
    predict_url
        .replace("/api/predict", "/readyz")
        .replace("//readyz", "/readyz")
}

pub async fn fetch_recommendations_from_ml(
    client: &Client,
    ml_predict_url: &str,
    body: &SymptomRequest,
    request_id: &str,
) -> Result<RecommendationResponse, MlServiceError> {
    let res = client
        .post(ml_predict_url)
        .header("x-request-id", request_id)
        .json(body)
        .send()
        .await
        .map_err(|e| {
            if e.is_timeout() {
                MlServiceError::Timeout(format!("ML request timeout: {e}"))
            } else {
                MlServiceError::Connection(format!("ML connection failure: {e}"))
            }
        })?;

    if !res.status().is_success() {
        let status = res.status().as_u16();
        let text = res.text().await.unwrap_or_default();
        let message = serde_json::from_str::<ErrorEnvelope>(&text)
            .map(|e| e.error.message)
            .unwrap_or(text);
        return Err(MlServiceError::UpstreamStatus(status, message));
    }

    res.json()
        .await
        .map_err(|e| MlServiceError::Parse(format!("ML response parse failure: {e}")))
}

pub async fn check_ml_readiness(
    client: &Client,
    ml_health_url: &str,
    request_id: &str,
) -> Result<(), MlServiceError> {
    let res = client
        .get(ml_health_url)
        .header("x-request-id", request_id)
        .send()
        .await
        .map_err(|e| {
            if e.is_timeout() {
                MlServiceError::Timeout(format!("ML readiness timeout: {e}"))
            } else {
                MlServiceError::Connection(format!("ML readiness connection failure: {e}"))
            }
        })?;

    if res.status().is_success() {
        return Ok(());
    }

    let status = res.status().as_u16();
    let text = res.text().await.unwrap_or_default();
    Err(MlServiceError::UpstreamStatus(status, text))
}

pub fn create_ml_client() -> Client {
    let timeout_secs = std::env::var("ML_TIMEOUT_SECS")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(DEFAULT_TIMEOUT_SECS);
    Client::builder()
        .timeout(Duration::from_secs(timeout_secs))
        .build()
        .expect("failed to build reqwest client")
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{extract::Json, http::StatusCode, routing::get, routing::post, Router};
    use serde_json::json;
    use std::net::SocketAddr;
    use tokio::time::{sleep, Duration};

    async fn spawn_test_server(app: Router) -> SocketAddr {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind listener");
        let addr = listener.local_addr().expect("local addr");
        tokio::spawn(async move {
            axum::serve(listener, app).await.expect("serve app");
        });
        addr
    }

    #[tokio::test]
    async fn parse_failure_is_mapped() {
        let app = Router::new().route("/api/predict", post(|| async { "not-json" }));
        let addr = spawn_test_server(app).await;
        let url = format!("http://{addr}/api/predict");

        let client = Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .expect("client");

        let req = SymptomRequest {
            symptoms: "pain".to_string(),
            avoid_effects: vec![],
        };
        let res = fetch_recommendations_from_ml(&client, &url, &req, "req-1").await;
        assert!(matches!(res, Err(MlServiceError::Parse(_))));
    }

    #[tokio::test]
    async fn timeout_is_mapped() {
        async fn delayed() -> Json<serde_json::Value> {
            sleep(Duration::from_millis(200)).await;
            Json(
                json!({"recommendations":[],"meta":{"request_id":"x","model_version":"v","warnings":[]}}),
            )
        }

        let app = Router::new().route("/api/predict", post(delayed));
        let addr = spawn_test_server(app).await;
        let url = format!("http://{addr}/api/predict");

        let client = Client::builder()
            .timeout(Duration::from_millis(50))
            .build()
            .expect("client");

        let req = SymptomRequest {
            symptoms: "pain".to_string(),
            avoid_effects: vec![],
        };
        let res = fetch_recommendations_from_ml(&client, &url, &req, "req-2").await;
        assert!(matches!(res, Err(MlServiceError::Timeout(_))));
    }

    #[tokio::test]
    async fn upstream_status_is_mapped() {
        async fn upstream_error() -> (StatusCode, Json<serde_json::Value>) {
            (
                StatusCode::BAD_REQUEST,
                Json(
                    json!({"error":{"code":"VALIDATION_ERROR","message":"bad input","request_id":"upstream"}}),
                ),
            )
        }

        let app = Router::new().route("/api/predict", post(upstream_error));
        let addr = spawn_test_server(app).await;
        let url = format!("http://{addr}/api/predict");

        let client = Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .expect("client");
        let req = SymptomRequest {
            symptoms: "pain".to_string(),
            avoid_effects: vec![],
        };

        let res = fetch_recommendations_from_ml(&client, &url, &req, "req-3").await;
        match res {
            Err(MlServiceError::UpstreamStatus(status, message)) => {
                assert_eq!(status, 400);
                assert_eq!(message, "bad input");
            }
            _ => panic!("expected upstream status error"),
        }
    }

    #[tokio::test]
    async fn readiness_check_success() {
        async fn ready() -> &'static str {
            "ok"
        }
        let app = Router::new().route("/readyz", get(ready));
        let addr = spawn_test_server(app).await;
        let url = format!("http://{addr}/readyz");

        let client = Client::builder()
            .timeout(Duration::from_secs(1))
            .build()
            .expect("client");

        check_ml_readiness(&client, &url, "req-4")
            .await
            .expect("should be ready");
    }
}
