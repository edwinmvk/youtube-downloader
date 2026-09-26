# Media Downloader Backend

Flask backend for the `youtube-downloader` project.

The backend runs at:

```text
http://localhost:5000
```

The frontend normally runs at:

```text
http://localhost:3000
```

## What the backend does

- Downloads YouTube/media URLs as MP3
- Downloads video as MP4
- Supports `highest`, `medium`, and `lowest` MP4 resolution presets
- Falls back to an available resolution when the requested tier is not available
- Provides asynchronous jobs with progress tracking
- Supports cancellation of active downloads
- Converts uploaded local videos to MP3
- Uses FFmpeg for merging and audio extraction
- Uses temporary job directories and cleans them up
- Returns the actual media filename through HTTP download headers

## Prerequisites

### Required software

1. **Python 3.11 or newer**
2. **FFmpeg + ffprobe**
3. **Deno 2.3 or newer**
4. Windows PATH configured for `ffmpeg`, `ffprobe`, and `deno`

Current yt-dlp documentation says the PyPI installation should use the `default` dependency group so `yt-dlp-ejs` is installed, and a supported JavaScript runtime is required for full YouTube support. Deno is the recommended runtime.

Official guide: https://github.com/yt-dlp/yt-dlp/wiki/EJS

### Verify prerequisites on Windows

```cmd
python --version
ffmpeg -version
ffprobe -version
deno --version
where ffmpeg
where ffprobe
where deno
```

## Create the Python virtual environment

From the backend folder:

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\backend
python -m venv venv
```

Activate it in CMD:

```cmd
venv\Scripts\activate
```

PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Git Bash:

```bash
source venv/Scripts/activate
```

## Install dependencies

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` uses:

```text
Flask
flask-cors
yt-dlp[default]
python-dotenv
```

The `yt-dlp[default]` dependency group includes `yt-dlp-ejs` for the PyPI installation path.

## Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Recommended local configuration:

```env
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
```

### Variable descriptions

| Variable | Purpose | Example |
|---|---|---|
| `FRONTEND_URL` | Allowed CORS origin | `http://localhost:3000` |
| `MAX_FILE_SIZE_MB` | Maximum uploaded local-video size | `500` |
| `MAX_CONCURRENT_DOWNLOADS` | Number of background download workers | `2` |
| `DOWNLOAD_JOB_TTL_SECONDS` | In-memory job expiry window | `1800` |

## Start the backend

From:

```text
C:\Users\edwin\Downloads\youtube-downloader\backend
```

with the virtual environment activated:

```cmd
python app.py
```

Expected:

```text
 * Running on http://127.0.0.1:5000
```

## Health check

```cmd
curl.exe http://localhost:5000/api/health
```

Expected:

```json
{
  "status": "ok"
}
```

## API endpoints

### 1. Health

```http
GET /api/health
```

### 2. Synchronous URL download

Backward-compatible endpoint:

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

### 3. Start an asynchronous download

```http
POST /api/download/start
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
  "resolution": "medium"
}
```

Response:

```json
{
  "job_id": "abc123",
  "status": "queued",
  "progress_url": "/api/download/progress/abc123",
  "cancel_url": "/api/download/cancel/abc123",
  "file_url": "/api/download/file/abc123"
}
```

### 4. Progress

```http
GET /api/download/progress/{job_id}
```

Possible statuses:

```text
queued
downloading
processing
completed
cancelled
failed
```

The response includes fields such as:

```json
{
  "job_id": "abc123",
  "status": "downloading",
  "progress": 42.5,
  "phase": "downloading",
  "format": "mp4",
  "requested_resolution": "medium",
  "effective_resolution": 480,
  "selection_note": "720p is not available; using the closest available resolution: 480p.",
  "title": "Example title",
  "filename": null,
  "downloaded_bytes": 12345678,
  "total_bytes": 29000000,
  "speed_bytes_per_second": 950000,
  "eta_seconds": 18,
  "error": null,
  "cancel_requested": false
}
```

### 5. Cancel a download

```http
POST /api/download/cancel/{job_id}
```

Response while cancellation is being processed:

```json
{
  "job_id": "abc123",
  "status": "cancelling",
  "message": "Download cancellation requested."
}
```

Continue polling until the job becomes `cancelled`.

### 6. Retrieve the completed file

```http
GET /api/download/file/{job_id}
```

This endpoint should be called only after the progress API reports `completed`.

The backend returns the MP3/MP4 binary with `Content-Disposition` and exposes filename-related headers through CORS.

### 7. Local video → MP3

```http
POST /api/convert
Content-Type: multipart/form-data
```

Field:

```text
file
```

Supported upload types include `.mp4`, `.mov`, `.mkv`, `.avi`, and `.webm`.

## Resolution presets

The user-facing presets are:

```text
highest
medium
lowest
```

The current implementation uses:

- `highest` → best available video/audio combination
- `medium` → attempts to use up to 720p and falls back when unavailable
- `lowest` → lowest available video/audio combination

The API reports the actual selected height through `effective_resolution`.

## cURL examples

### Start MP3 job

```cmd
curl.exe -X POST "http://localhost:5000/api/download/start" -H "Content-Type: application/json" -d "{\"url\":\"https://youtu.be/nH_k4_e-0yU?si=nR_lU2-B2N_9U8GK\",\"format\":\"mp3\"}"
```

### Start MP4 job at medium resolution

```cmd
curl.exe -X POST "http://localhost:5000/api/download/start" -H "Content-Type: application/json" -d "{\"url\":\"https://youtu.be/nH_k4_e-0yU?si=nR_lU2-B2N_9U8GK\",\"format\":\"mp4\",\"resolution\":\"medium\"}"
```

### Poll progress

```cmd
curl.exe "http://localhost:5000/api/download/progress/YOUR_JOB_ID"
```

### Cancel

```cmd
curl.exe -X POST "http://localhost:5000/api/download/cancel/YOUR_JOB_ID"
```

### Download completed file

```cmd
curl.exe -OJ "http://localhost:5000/api/download/file/YOUR_JOB_ID"
```

`-OJ` lets cURL use the server-supplied attachment filename.

### Convert a local video

```cmd
curl.exe -X POST "http://localhost:5000/api/convert" -F "file=@video.mp4" --output converted.mp3
```

## Filename handling

The backend uses the media title for output filenames and sanitizes filesystem-sensitive characters.

The download response includes `Content-Disposition` and, when applicable, `X-Download-Filename`.

The frontend must preserve this filename when it performs a Blob download. Do not hardcode `download` as the browser filename.

## YouTube extraction notes

The backend relies on yt-dlp. Modern YouTube extraction may require:

- an up-to-date yt-dlp
- `yt-dlp-ejs`
- a supported JavaScript runtime such as Deno

If YouTube returns a bot or login challenge such as `HTTP 429` or `Sign in to confirm you're not a bot`, verify Deno/EJS first and consult yt-dlp's official documentation for the applicable browser-session/cookie workflow.

## Error handling

The backend returns JSON errors instead of HTML stack traces. Typical responses include:

```json
{
  "error": "Invalid request. URL and format are required."
}
```

```json
{
  "error": "Unsupported resolution. Use highest, medium or lowest."
}
```

```json
{
  "error": "FFmpeg is not installed or is not available in PATH."
}
```

```json
{
  "error": "Unable to download the requested media."
}
```

## Development

Do not commit:

```text
venv/
.env
__pycache__/
*.pyc
```

The backend uses in-memory jobs and temporary directories; there is no database or persistent download history.

## Useful checks

```cmd
python --version
python -m pip show yt-dlp
after=python -m pip show yt-dlp-ejs
deno --version
ffmpeg -version
ffprobe -version
```

Only run media downloads for content you have permission to download or convert.
