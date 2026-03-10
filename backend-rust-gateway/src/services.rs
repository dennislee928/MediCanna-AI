// 呼叫 Python ML 服務 /api/predict
use crate::models::{RecommendationResponse, SymptomRequest};
use reqwest::Client;
use std::time::Duration;

fn ml_predict_url() -> String {
    std::env::var("ML_PREDICT_URL").unwrap_or_else(|_| "http://localhost:8000/api/predict".into())
}
const TIMEOUT_SECS: u64 = 10;

/// 向 Python FastAPI 請求推薦結果；逾時或服務離線時回傳錯誤。
pub async fn fetch_recommendations_from_ml(
    client: &Client,
    body: &SymptomRequest,
) -> Result<RecommendationResponse, String> {
    let url = ml_predict_url();
    let res = client
        .post(&url)
        .json(body)
        .send()
        .await
        .map_err(|e| format!("ML 服務連線失敗: {}", e))?;

    if !res.status().is_success() {
        let status = res.status();
        let text = res.text().await.unwrap_or_default();
        return Err(format!("ML 服務錯誤 {}: {}", status, text));
    }

    let recommendations: RecommendationResponse = res
        .json()
        .await
        .map_err(|e| format!("ML 回傳解析失敗: {}", e))?;

    Ok(recommendations)
}

/// 建立帶逾時的 reqwest Client（供 main 注入 handler）
pub fn create_ml_client() -> Client {
    Client::builder()
        .timeout(Duration::from_secs(TIMEOUT_SECS))
        .build()
        .expect("reqwest Client 建立失敗")
}
