# YouTube Downloader

> **Running locally without Docker:** switch to the `runtime-native-without-docker` branch.
>
> This branch uses the Docker-based architecture described below.

## Description

YouTube Downloader is a full-stack media downloading and conversion application built with a **Next.js frontend**, **Python FastAPI backend**, **yt-dlp**, **FFmpeg**, **Deno**, **bgutil PO Token provider**, and **Nginx**.

The application supports YouTube URL downloads as MP3 or MP4, MP4 quality selection, asynchronous download progress, download cancellation, local video-to-MP3 conversion, batch conversion of up to 10 local videos, ZIP output for multi-file conversion, Unicode-safe filenames, temporary-file cleanup, interactive audio trimming, multi-track audio merging, and a dedicated local video-to-MP3 page. The application does not use a database, authentication, user accounts, or persistent media records.

## Media editing features

### Video to MP3

The dedicated `/video-to-mp3` page accepts up to 10 local video files and converts them to MP3 with FFmpeg. A single video downloads as an MP3; multiple videos are returned as a ZIP archive.


### Audio trimmer

The audio trimmer accepts one audio file and provides:

- A single dual-handle trim slider for start and end points, plus numeric time inputs.
- Native browser playback for the original audio.
- Preview of only the selected trim range.
- FFmpeg-based MP3 export at 192 kbps.
- Unicode-preserving output names.
- Completion dialog with options to continue editing or start with a new song.

### Audio merger

The audio merger accepts up to 10 audio files and provides:

- Drag-and-drop reordering.
- Accessible move-up and move-down controls.
- File removal before processing.
- FFmpeg normalization and ordered concatenation.
- A single MP3 download after merging.
- Completion dialog with options to continue editing or start with a new set.

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
                │ Next.js :3000   │       │ Gunicorn + Uvicorn :5000    │
                │                 │       │                             │
                │                 │       │ FastAPI                     │
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

Inside the Docker backend container, the FastAPI application is served by Gunicorn with a Uvicorn worker on port 5000. The Docker setup does not start the application with the FastAPI development server in production.

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
                                                    ├── FastAPI
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

The application runtime dependencies such as Python, FastAPI, FFmpeg, Deno, yt-dlp, Node.js, Next.js, Nginx, and the PO Token provider run inside their respective Docker images/containers.

Verify Docker:

```cmd
docker --version
docker compose version
```

## Run locally with Docker

Run all commands from the repository root.

The project uses a single root environment file named `.env`. Docker Compose automatically reads `.env` from the project root, so no `--env-file` option is required.

### 1. Validate the Compose configuration

```cmd
docker compose config
```

### 2. Build the application images

```cmd
docker compose build
```

### 3. Start the complete application

```cmd
docker compose up
```

For detached/background mode:

```cmd
docker compose up -d
```

### 4. Verify the containers

```cmd
docker compose ps
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
docker compose down -v
```

## Environment variables

The Docker setup uses two root environment files:

```text
.env
.env.example
```

`.env` contains the values used by your local Docker Compose environment and should not be committed to Git.

`.env.example` is the safe template for other developers. It should be committed to Git and should not contain secrets.

### Root `.env`

The local `.env` should contain:

```env
FRONTEND_URL=http://localhost
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
POT_PROVIDER_URL=http://bgutil-provider:4416
NEXT_PUBLIC_API_URL=/api
```

### Root `.env.example`

Keep the same variable names and safe example values:

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
| `FRONTEND_URL` | Browser-facing origin served by Nginx and used by the backend for CORS | `http://localhost` |
| `MAX_FILE_SIZE_MB` | Total request body/upload limit for FastAPI conversion | `500` |
| `MAX_CONCURRENT_DOWNLOADS` | In-memory async download concurrency limit | `2` |
| `DOWNLOAD_JOB_TTL_SECONDS` | How long completed async jobs remain available in memory | `1800` |
| `POT_PROVIDER_URL` | Docker Compose service address of the PO Token provider | `http://bgutil-provider:4416` |
| `NEXT_PUBLIC_API_URL` | Browser-facing API base path routed by Nginx to FastAPI | `/api` |

There are no required `.env` files inside the `frontend` or `backend` directories for this Docker setup.

## Project structure

```text
youtube-downloader/
│
├── README.md
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
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
