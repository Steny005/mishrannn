# GCP Deployment Guide for Mishran Server

This guide provides the commands to deploy the Mishran Server to Google Cloud Platform using Google Cloud Shell and Compute Engine.

## 1. Initial Setup
Enable required APIs and create an Artifact Registry repository.

```bash
# Set your Project ID variable
PROJECT_ID=$(gcloud config get-value project)

# Enable Artifact Registry and Compute Engine APIs
gcloud services enable artifactregistry.googleapis.com compute.googleapis.com

# Create a Docker repository
gcloud artifacts repositories create mishran-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Mishran Server Repository"
```

## 2. Build and Push Container Image
Authenticate Docker and push your local image to GCP.

```bash
# Configure Docker to authenticate with GCP Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build the image (Run this from inside the mishran-server directory)
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/mishran-repo/mishran-server:v1 .

# Push the image to GCP
docker push us-central1-docker.pkg.dev/$PROJECT_ID/mishran-repo/mishran-server:v1
```

## 3. Deploy to Compute Engine
Create a Virtual Machine instance that automatically runs the container.

```bash
gcloud compute instances create-with-container mishran-server-instance \
    --container-image=us-central1-docker.pkg.dev/$PROJECT_ID/mishran-repo/mishran-server:v1 \
    --container-mount-host-path=host-path=/var/lib/mishran/recordings,mount-path=/app/recordings \
    --container-env=AI_DIRECTOR_URL=https://hari-n8n.laddu.cc/webhook/ai-director-input \
    --tags=mishran-server \
    --machine-type=e2-standard-2 \
    --zone=us-central1-a
```

## 4. Network Configuration
Open port 8080 to allow WebSocket and HTTP traffic.

```bash
gcloud compute firewall-rules create allow-mishran-ws \
    --allow tcp:8080 \
    --target-tags=mishran-server \
    --description="Allow Mishran WebSocket traffic"
```

## 5. Verify Deployment
Retrieve the public IP address of your new server.

```bash
gcloud compute instances list --filter="name=mishran-server-instance" --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
```

## 6. Troubleshooting & Cleanup
If you previously ran `docker-compose` or `gcloud create-with-container` and are facing port conflicts or connection issues, follow these steps in Cloud Shell:

### Stop and Remove Existing VM
```bash
gcloud compute instances delete mishran-server-instance --zone=us-central1-a --quiet
```

### Reset Firewall (if needed)
```bash
gcloud compute firewall-rules delete allow-mishran-ws --quiet
gcloud compute firewall-rules create allow-mishran-ws --allow tcp:8080 --target-tags=mishran-server
```

### Important Note on HTTPS
If your host/camera app is running on an **HTTPS** URL (like Vercel, Netlify, or SvelteKit default preview), browsers will **BLOCK** connections to a non-secure `ws://` server.
- **Solution:** Either run your host app via `http://localhost` for testing, or set up an SSL certificate/Reverse Proxy (like Nginx) on your VM to use `wss://`.
