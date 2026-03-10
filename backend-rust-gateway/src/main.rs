use axum::{
    http::{HeaderValue, Method},
    routing::{get, post},
    Router,
};
use std::net::SocketAddr;
use tower_http::cors::{Any, CorsLayer};
use tracing::info;
use tracing_subscriber::EnvFilter;

mod handlers;
mod models;
mod services;

use handlers::{get_recommendation_handler, healthz_handler, readyz_handler, AppState};
use services::{ml_health_url_from_predict_url, ml_predict_url_from_env};

fn build_cors_layer() -> CorsLayer {
    let allow_origins = std::env::var("ALLOWED_ORIGINS").unwrap_or_else(|_| "*".to_string());
    let cors = CorsLayer::new()
        .allow_methods([Method::GET, Method::POST, Method::OPTIONS])
        .allow_headers(Any);

    if allow_origins.trim() == "*" {
        return cors.allow_origin(Any);
    }

    let origins: Vec<HeaderValue> = allow_origins
        .split(',')
        .filter_map(|origin| origin.trim().parse::<HeaderValue>().ok())
        .collect();
    if origins.is_empty() {
        cors.allow_origin(Any)
    } else {
        cors.allow_origin(origins)
    }
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .json()
        .init();

    let client = services::create_ml_client();
    let ml_predict_url = ml_predict_url_from_env();
    let ml_health_url = std::env::var("ML_HEALTH_URL")
        .unwrap_or_else(|_| ml_health_url_from_predict_url(&ml_predict_url));
    let state = AppState {
        http_client: client,
        ml_predict_url,
        ml_health_url,
    };

    let app = Router::new()
        .route("/api/v1/recommend", post(get_recommendation_handler))
        .route("/healthz", get(healthz_handler))
        .route("/readyz", get(readyz_handler))
        .layer(build_cors_layer())
        .with_state(state);

    let port = std::env::var("PORT")
        .ok()
        .or_else(|| std::env::var("GATEWAY_PORT").ok())
        .and_then(|v| v.parse::<u16>().ok())
        .unwrap_or(8080);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    info!(address = %addr, event = "gateway_startup");
    axum::serve(
        tokio::net::TcpListener::bind(addr)
            .await
            .expect("failed to bind listener"),
        app,
    )
    .await
    .expect("gateway server failed");
}
