# YouTube Downloader

> **Running locally without Docker:** switch to the `runtime-native-without-docker` branch.
>
> This branch uses the Docker-based architecture described below.

## Description

YouTube Downloader is a full-stack media downloading and conversion application built with a **Next.js frontend**, **Python Flask backend**, **yt-dlp**, **FFmpeg**, **Deno**, **bgutil PO Token provider**, and **Nginx**.

The application supports YouTube URL downloads as MP3 or MP4, MP4 quality selection, asynchronous download progress, download cancellation, local video-to-MP3 conversion, batch conversion of up to 10 local videos, ZIP output for multi-file conversion, Unicode-safe filenames, and temporary-file cleanup. The application does not use a database, authentication, user accounts, or persistent media records.

## Whole-project architecture

```text
                                      Browser
                                         │
                                         │ http://localhost
                                         ▼
                              Windows host port :80
                                         │
                                         │ 80:80
                                         ▼
                          ┌─────────────────────────┐
                          │     NGINX CONTAINER     │
                          │          :80            │
                          │                         │
                          │  Reverse proxy / entry  │
                          │        point            │
                          └────────────┬────────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         │                           │
                         ▼                           ▼
                ┌─────────────────┐       ┌─────────────────────────────┐
                │ FRONTEND        │       │ BACKEND                     │
                │ CONTAINER       │       │ CONTAINER                   │
                │                 │       │                             │
                │ Next.js :3000   │       │ Gunicorn :5000              │
                │                 │       │                             │
                │                 │       │ yt-dlp + EJS/Deno + FFmpeg  │
                └─────────────────┘       └────────┬────────────────────┘
                                                    │
                                                    │ Docker HTTP
                                                    ▼
                                          ┌────────────────────┐
                                          │ BGUTIL-PROVIDER    │
                                          │ CONTAINER          │
                                          │       :4416        │
                                          └─────────┬──────────┘
                                                    │
                                                    ▼
                                                 YouTube
```

Inside the Docker frontend container, Next.js runs as a production app (`NODE_ENV=production` in Docker Compose). The Docker setup does not start the application with `npm run dev`.

Inside the Docker backend container, the Flask application is served by Gunicorn on port 5000. The Docker setup does not start the application with `python app.py` or Flask's development server.

The backend container also contains:

```text
yt-dlp
FFmpeg
Deno / EJS support
Python application dependencies
```

### Request routing

```text
Browser
  │
  ├── GET / --------------------------> Nginx ----> Frontend :3000
  │
  └── /api/* -------------------------> Nginx ----> Backend :5000
                                                    │
                                                    ├── yt-dlp
                                                    ├── Deno / EJS
                                                    ├── FFmpeg
                                                    └── bgutil-provider :4416
```

### Docker networking

```text
proxy_net
├── nginx
├── frontend
└── backend

backend_net
├── backend
└── bgutil-provider
```

Only Nginx publishes a host port:

```text
Windows host :80  →  nginx container :80
```

The following ports remain internal to Docker:

```text
frontend :3000
backend  :5000
bgutil   :4416
```

## Prerequisites

Install the following on the host machine:

- **Docker Desktop** with Docker Compose support
- **Git**
- A modern web browser
- Internet access for URL-based media downloads

The application runtime dependencies such as Python, Flask, FFmpeg, Deno, yt-dlp, Node.js, Next.js, Nginx, and the PO Token provider run inside their respective Docker images/containers.

Verify Docker:

```cmd
docker --version
docker compose version
```

## Run locally with Docker

Run all commands from the repository root.

The project uses a single root environment file named `.env.docker`. Since the file is intentionally named `.env.docker` instead of `.env`, pass it explicitly to Docker Compose using `--env-file .env.docker`.

### 1. Validate the Compose configuration

```cmd
docker compose --env-file .env.docker config
```

### 2. Build the application images

```cmd
docker compose --env-file .env.docker build
```

### 3. Start the complete application

```cmd
docker compose --env-file .env.docker up
```

For detached/background mode:

```cmd
docker compose --env-file .env.docker up -d
```

### 4. Verify the containers

```cmd
docker compose --env-file .env.docker ps
```

Expected services:

```text
backend
bgutil-provider
frontend
nginx
```

### 5. Verify the backend through Nginx

```cmd
curl.exe http://localhost/api/health
```

Expected response:

```json
{"status":"ok"}
```

### 6. Open the application

```text
http://localhost
```

### 7. Stop the application

```cmd
docker compose --env-file .env.docker down -v
```

## Environment variables

The Docker setup uses a single environment file in the root `.env.docker`.

### Root `.env.docker`

The root `.env.docker` supplies the Docker Compose configuration used by the application:

```env
FRONTEND_URL=http://localhost
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
POT_PROVIDER_URL=http://bgutil-provider:4416
NEXT_PUBLIC_API_URL=/api
```

| Variable | Purpose | Value |
|---|---|---|
| `FRONTEND_URL` | Browser-facing origin served by Nginx and used by backend CORS | `http://localhost` |
| `MAX_FILE_SIZE_MB` | Total request body/upload limit for Flask conversion | `500` |
| `MAX_CONCURRENT_DOWNLOADS` | In-memory async download worker count | `2` |
| `DOWNLOAD_JOB_TTL_SECONDS` | How long completed async jobs remain available in memory | `1800` |
| `POT_PROVIDER_URL` | Docker Compose service address of the PO Token provider | `http://bgutil-provider:4416` |
| `NEXT_PUBLIC_API_URL` | Browser-facing API base path routed by Nginx to Flask | `/api` |

There are no required `.env` files in the root, `frontend`, or `backend` directories for this Docker setup.

## Project structure

```text
youtube-downloader/
│
├── README.md
├── docker-compose.yml
├── .env.docker
│
├── nginx/
│   └── default.conf
│
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── app.py
│   ├── README.md
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── download.py
│   │   └── convert.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── yt_dlp_service.py
│   │   ├── ffmpeg_service.py
│   │   ├── file_service.py
│   │   └── job_service.py
│   └── utils/
│       └── __init__.py
│
└── frontend/
    ├── Dockerfile
    ├── .dockerignore
    ├── package.json
    ├── README.md
    ├── next.config.mjs
    └── ...
```
