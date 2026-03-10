use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SymptomRequest {
    pub symptoms: String,
    #[serde(default)]
    pub avoid_effects: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrainItem {
    pub name: String,
    #[serde(rename = "type")]
    pub r#type: String,
    pub rating: f64,
    pub effects: String,
    pub flavor: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ResponseMeta {
    pub request_id: String,
    pub model_version: String,
    #[serde(default)]
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RecommendationResponse {
    #[serde(default)]
    pub recommendations: Vec<StrainItem>,
    #[serde(default)]
    pub meta: ResponseMeta,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiError {
    pub code: String,
    pub message: String,
    pub request_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorEnvelope {
    pub error: ApiError,
}

#[derive(Debug, Clone, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub ready: bool,
}
