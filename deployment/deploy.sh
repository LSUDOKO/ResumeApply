#!/bin/bash
# ResumeApply — Manual GCP deployment script
# Usage: ./deployment/deploy.sh
# Requires: gcloud CLI authenticated, docker, PROJECT_ID set

set -e

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION="us-central1"
SERVICE_NAME="resumeapply-backend"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "==> Project: $PROJECT_ID"
echo "==> Region:  $REGION"
echo ""

# 1. Build backend image
echo "[1/4] Building backend Docker image..."
docker build -t "$IMAGE:latest" ./backend
echo "      Done."

# 2. Push to GCR
echo "[2/4] Pushing image to Google Container Registry..."
docker push "$IMAGE:latest"
echo "      Done."

# 3. Deploy to Cloud Run
echo "[3/4] Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE:latest" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY},GCS_BUCKET=${GCS_BUCKET:-resumeapply-resumes},PROJECT_ID=${PROJECT_ID}"

BACKEND_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" \
  --format 'value(status.url)')

echo "      Backend live at: $BACKEND_URL"

# 4. Build & deploy frontend
echo "[4/4] Building and deploying frontend..."
cd frontend
NEXT_PUBLIC_API_URL="$BACKEND_URL" \
NEXT_PUBLIC_WS_URL="${BACKEND_URL/https/wss}" \
npm run build

if command -v firebase &> /dev/null; then
  firebase deploy --only hosting
  echo "      Frontend deployed to Firebase Hosting."
else
  echo "      firebase-tools not found. Run: npm install -g firebase-tools && firebase deploy --only hosting"
fi

echo ""
echo "==> Deployment complete."
echo "    Backend:  $BACKEND_URL"
echo "    API Docs: $BACKEND_URL/docs"
