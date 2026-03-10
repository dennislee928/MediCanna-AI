// 與 Python FastAPI /api/predict 對接的 Request/Response 結構
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct SymptomRequest {
    pub symptoms: String,
    #[serde(default)]
    pub avoid_effects: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct StrainItem {
    pub name: String,
    #[serde(rename = "type")]
    pub r#type: String,
    pub rating: f64,
    pub effects: String,
    pub flavor: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RecommendationResponse {
    pub recommendations: Vec<StrainItem>,
}
