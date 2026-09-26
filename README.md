# YouTube Downloader

A full-stack media downloader with a **Next.js frontend** and a **Python Flask backend**.

The project is organized as:

```text
youtube-downloader/
├── README.md
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   ├── routes/
│   ├── services/
│   └── utils/
└── frontend/
    ├── package.json
    ├── README.md
    └── ...
```

## Features

- YouTube URL → MP3
- YouTube URL → MP4
- MP4 resolution presets: **Highest**, **Medium**, **Lowest**
- Resolution fallback when an exact target is unavailable
- Download progress with percentage, speed, ETA, and processing state
- Cancel/abort an active download
- Browser download using the actual media title as the filename
- Local video upload → MP3 conversion
- REST API between Next.js and Flask
- No database, authentication, or user accounts
- Temporary server-side media storage with cleanup

## Architecture

```text
Browser
  │
  │ http://localhost:3000
  ▼
Next.js Frontend
  │
  │ REST API / CORS
  ▼
Flask Backend
  │
  ├── yt-dlp
  │     └── Deno + yt-dlp-ejs for modern YouTube extraction
  │
  └── FFmpeg / ffprobe
```

For URL downloads that need progress/cancellation, the frontend uses the asynchronous job API:

```text
POST /api/download/start
        ↓
GET  /api/download/progress/{job_id}
        ↓
POST /api/download/cancel/{job_id}   (optional)
        ↓
GET  /api/download/file/{job_id}     (after completion)
```

The original synchronous endpoint remains available for backward compatibility:

```text
POST /api/download
```

## Prerequisites

### Backend

Install these before starting Flask:

- Python 3.11+
- FFmpeg
- ffprobe (normally included with FFmpeg builds)
- Deno 2.3+
- Git (optional)

For YouTube extraction with a PyPI installation of yt-dlp, the current yt-dlp documentation recommends the `default` dependency group, which includes `yt-dlp-ejs`. A supported external JavaScript runtime is also required for full YouTube support; Deno is the recommended runtime. See the official yt-dlp EJS guide: https://github.com/yt-dlp/yt-dlp/wiki/EJS

### Frontend

For a current Next.js 16 project, Node.js **20.9+** is required. Use the package manager already selected by the frontend project (`npm`, `pnpm`, `yarn`, or `bun`) and follow the project's lockfile. Official Next.js installation guidance: https://nextjs.org/docs/app/getting-started/installation

## Recommended local startup order

Open two terminals.

### Terminal 1 — backend

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\backend
venv\Scripts\activate
python app.py
```

Backend:

```text
http://localhost:5000
```

### Terminal 2 — frontend

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

If the frontend project uses `pnpm-lock.yaml`, `yarn.lock`, or `bun.lockb`/`bun.lock`, use the corresponding package manager instead of npm.

## Quick health check

```cmd
curl.exe http://localhost:5000/api/health
```

Expected:

```json
{
  "status": "ok"
}
```

## Environment configuration

### Backend

Copy:

```text
backend/.env.example
```

to:

```text
backend/.env
```

Typical values:

```env
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
```

### Frontend

Set the backend base URL using the environment variable already used by the existing frontend architecture. The intended local value is:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Do not hardcode the backend URL throughout React components.

## Main APIs

### Health

```http
GET /api/health
```

### Synchronous download — backward compatible

```http
POST /api/download
Content-Type: application/json
```

MP3:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp3"
}
```

MP4:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp4",
  "resolution": "highest"
}
```

Valid resolutions:

```text
highest
medium
lowest
```

### Asynchronous download

Start:

```http
POST /api/download/start
```

Progress:

```http
GET /api/download/progress/{job_id}
```

Cancel:

```http
POST /api/download/cancel/{job_id}
```

Completed file:

```http
GET /api/download/file/{job_id}
```

### Local video → MP3

```http
POST /api/convert
Content-Type: multipart/form-data
```

Upload field:

```text
file
```

## Resolution behavior

The frontend exposes only:

- Highest
- Medium
- Lowest

The backend chooses an appropriate available stream rather than requiring an exact format ID.

The current backend targets **720p** for Medium when possible and falls back when the requested tier is unavailable. The actual selected resolution is returned through `effective_resolution`, and `selection_note` explains a fallback when appropriate.

## Filename behavior

The backend generates filenames from the media title and returns them through `Content-Disposition`.

The frontend must preserve that filename when it fetches the completed file as a Blob. In particular, do not hardcode:

```ts
anchor.download = "download";
```

Instead, read the filename from the response headers and use that value for the browser download.

## Troubleshooting

### `ffmpeg: command not found`

FFmpeg is not installed or its `bin` directory is not in PATH.

Verify:

```cmd
ffmpeg -version
ffprobe -version
```

### `No supported JavaScript runtime could be found`

Verify Deno:

```cmd
deno --version
where deno
```

Deno should be available in PATH.

### `yt-dlp-ejs` is missing

Verify:

```cmd
python -m pip show yt-dlp-ejs
```

The backend requirements use:

```text
yt-dlp[default]
```

which is the recommended PyPI installation path for the EJS package.

### YouTube returns `HTTP 429` or `Sign in to confirm you're not a bot`

This is a YouTube/yt-dlp extraction issue rather than a Flask routing issue. First upgrade yt-dlp and confirm Deno/EJS are installed:

```cmd
python -m pip install -U "yt-dlp[default]"
deno --version
python -m pip show yt-dlp-ejs
```

A browser cookie/session may be required in some environments. Consult the yt-dlp documentation before adding cookie handling to the backend.

### Frontend downloads a file named `download`

Check that the frontend reads `Content-Disposition` (and/or the backend's exposed `X-Download-Filename` header) and assigns the resolved name to the temporary download anchor.

## Development notes

- Backend jobs are stored in memory only.
- There is no database.
- Temporary media is deleted after completion, cancellation, failure, or delivery/expiry according to the backend job lifecycle.
- Do not expose raw Python tracebacks to the browser.
- Only use the application with media you have permission to download or convert.

## Project-specific documentation

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
