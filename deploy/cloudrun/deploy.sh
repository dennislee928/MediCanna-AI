#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?PROJECT_ID is required}"
REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-medicanna}"
TAG="${TAG:-$(git rev-parse --short HEAD)}"

FRONTEND_SERVICE="${FRONTEND_SERVICE:-medicanna-frontend}"
GATEWAY_SERVICE="${GATEWAY_SERVICE:-medicanna-gateway}"
ML_SERVICE="${ML_SERVICE:-medicanna-ml}"

AR_HOST="${REGION}-docker.pkg.dev"
IMAGE_PREFIX="${AR_HOST}/${PROJECT_ID}/${REPOSITORY}"

FRONTEND_IMAGE="${IMAGE_PREFIX}/frontend:${TAG}"
GATEWAY_IMAGE="${IMAGE_PREFIX}/gateway:${TAG}"
ML_IMAGE="${IMAGE_PREFIX}/ml:${TAG}"

echo "[deploy] project=${PROJECT_ID} region=${REGION} tag=${TAG}"

gcloud auth configure-docker "${AR_HOST}" --quiet

gcloud builds submit --project "${PROJECT_ID}" --tag "${ML_IMAGE}" ./ml-python-engine
gcloud run deploy "${ML_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${ML_IMAGE}" \
  --platform managed \
  --allow-unauthenticated \
  --ingress internal \
  --set-env-vars "MODEL_VERSION=${TAG},ML_FAIL_FAST=true"

ML_URL="$(gcloud run services describe "${ML_SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"

gcloud builds submit --project "${PROJECT_ID}" --tag "${GATEWAY_IMAGE}" ./backend-rust-gateway
gcloud run deploy "${GATEWAY_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${GATEWAY_IMAGE}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ML_PREDICT_URL=${ML_URL}/api/predict,ML_HEALTH_URL=${ML_URL}/readyz,ALLOWED_ORIGINS=*"

GATEWAY_URL="$(gcloud run services describe "${GATEWAY_SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"

gcloud builds submit --project "${PROJECT_ID}" --tag "${FRONTEND_IMAGE}" ./frontend-angular
gcloud run deploy "${FRONTEND_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${FRONTEND_IMAGE}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GATEWAY_URL=${GATEWAY_URL}/api/v1/recommend"

echo "[deploy] complete"
echo "  frontend: $(gcloud run services describe "${FRONTEND_SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
echo "  gateway : ${GATEWAY_URL}"
echo "  ml      : ${ML_URL}"
