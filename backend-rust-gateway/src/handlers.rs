// 處理前端請求：驗證、呼叫 ML 服務、錯誤處理
use axum::{extract::State, http::StatusCode, Json};
use reqwest::Client;

use crate::models::{RecommendationResponse, SymptomRequest};
use crate::services::fetch_recommendations_from_ml;

#[derive(Clone)]
pub struct AppState {
    pub http_client: Client,
}

/// 接收 JSON：symptoms 不可為空；呼叫 ML 取得推薦並回傳。
pub async fn get_recommendation_handler(
    State(state): State<AppState>,
    Json(payload): Json<SymptomRequest>,
) -> Result<Json<RecommendationResponse>, (StatusCode, String)> {
    let symptoms = payload.symptoms.trim();
    if symptoms.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            "symptoms 不可為空".to_string(),
        ));
    }

    let body = SymptomRequest {
        symptoms: symptoms.to_string(),
        avoid_effects: payload.avoid_effects.clone(),
    };

    match fetch_recommendations_from_ml(&state.http_client, &body).await {
        Ok(res) => Ok(Json(res)),
        Err(e) => Err((
            StatusCode::BAD_GATEWAY,
            format!("無法取得推薦: {}", e),
        )),
    }
}
