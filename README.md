## Podman CI/CD Deployment Agent Overview

This repository contains a containerized Python application (Flask) using MySQL and FAISS, plus a Podman Compose setup and a CI workflow.

### Project Structure

```
app/
data/mysql/
.github/workflows/
Dockerfile
podman-compose.yml
requirements.txt
```

### Quickstart (Development)

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start services:
   - With Podman Compose: `podman compose -f podman-compose.yml up --build`
3. App will be available at `http://localhost:5000`.

Endpoints:
- `GET /health` – health check
- `GET /db-ping` – simple MySQL connectivity test
- `POST /faiss/search` – basic FAISS vector search demo

### Notes / Best Practices

- Dev: Mount the `app/` directory for live code reload without rebuilding the image.
- Prod: Build the image from Git and deploy a versioned container.
- Windows/Podman Desktop: Ensure volume access permissions are granted for `data/mysql/`.

### CI/CD

GitHub Actions builds (and optionally pushes) the image on push. Configure registry secrets if you want to push images (see `.github/workflows/ci.yml`).


