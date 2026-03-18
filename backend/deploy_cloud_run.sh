#!/bin/bash

# Configuration
SERVICE_NAME="resumeapply-backend"
REGION="us-central1"
# Get Project ID, Bucket, and Key Path from .env
PROJECT_ID=$(grep PROJECT_ID .env | cut -d '=' -f2)
GCS_BUCKET=$(grep GCS_BUCKET .env | cut -d '=' -f2)
KEY_FILE=$(grep GOOGLE_APPLICATION_CREDENTIALS .env | cut -d '=' -f2)

echo "🚀 Using currently logged-in 'gcloud' account for deployment..."
CURRENT_ACCOUNT=$(gcloud config get-value account)
echo "👤 Active Account: $CURRENT_ACCOUNT"
gcloud config set project $PROJECT_ID

echo "🚀 Deploying $SERVICE_NAME to Google Cloud Run in project $PROJECT_ID..."

# 1. Enable necessary services
echo "✅ Enabling Cloud Run and Cloud Build APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project $PROJECT_ID --quiet

# 2. Build and Deploy
# Note: --source . automatically builds using Buildpacks or Dockerfile
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID" \
  --set-env-vars "GCS_BUCKET=$GCS_BUCKET" \
  --memory 1Gi \
  --timeout 300 \
  --quiet

echo "🎉 Deployment complete! Your backend URL will be shown above."
