// MediCanna AI - Rust API Gateway，Port 8080，CORS 允許 localhost:4200
use axum::{
    routing::post,
    Router,
};
use tower_http::cors::{Any, CorsLayer};
use std::net::SocketAddr;

mod handlers;
mod models;
mod services;

use handlers::{get_recommendation_handler, AppState};

#[tokio::main]
async fn main() {
    let client = services::create_ml_client();
    let state = AppState {
        http_client: client,
    };

    let cors = CorsLayer::new()
        .allow_origin("http://localhost:4200".parse::<axum::http::HeaderValue>().unwrap())
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/api/v1/recommend", post(get_recommendation_handler))
        .layer(cors)
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("MediCanna Gateway 監聽 http://{}", addr);
    axum::serve(
        tokio::net::TcpListener::bind(addr).await.expect("bind 8080"),
        app,
    )
    .await
    .expect("serve");
}
