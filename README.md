# Media Downloader

A full-stack media downloader application with a **Next.js frontend** and **Python Flask backend**.

The application can download media from supported URLs using **yt-dlp**, convert/merge media with **FFmpeg**, convert uploaded videos to MP3, show download progress, cancel active downloads, and let users choose between **Highest**, **Medium**, and **Lowest** video quality.

> Use this application only for media you are authorized to download or convert.

---

## Architecture

```text
┌───────────────────────────────┐
│       Next.js Frontend        │
│       http://localhost:3000   │
│                               │
│  • URL input                  │
│  • MP3 / MP4 selection        │
│  • Resolution selection       │
│  • Progress bar               │
│  • Cancel download            │
│  • File download              │
└───────────────┬───────────────┘
                │ REST / JSON / multipart
                ▼
┌───────────────────────────────┐
│        Flask Backend          │
│       http://localhost:5000   │
│                               │
│  • API validation             │
│  • Async download jobs        │
│  • Progress tracking          │
│  • Cancellation               │
│  • Filename handling          │
│  • Temporary file cleanup     │
└───────────────┬───────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
   ┌─────────┐       ┌──────────┐
   │ yt-dlp  │       │  FFmpeg  │
   └─────────┘       └──────────┘
```

## Main features

### URL downloads

- Download audio as MP3.
- Download video as MP4.
- Download MP4 as:
  - Highest
  - Medium
  - Lowest
- Automatic resolution fallback when an exact target is unavailable.
- Progress percentage, bytes, speed, and ETA.
- Download cancellation.
- Original media title used for the downloaded filename.

### Local video conversion

Upload a local video and convert its audio to MP3.

Supported source extensions:

```text
.mp4
.mov
.mkv
.avi
.webm
```

### Backend characteristics

- Python 3.11+
- Flask
- flask-cors
- yt-dlp
- FFmpeg
- No database
- No authentication
- No user accounts
- No ORM
- Temporary files only
- In-memory download job state

---

# Project structure

A recommended repository layout is:

```text
media-downloader/
│
├── frontend/                      # Existing Next.js / v0.dev application
│   └── ...
│
├── backend/                       # Flask application
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   ├── FRONTEND_V0_INTEGRATION_PROMPT.md
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── download.py
│   │   └── convert.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── yt_dlp_service.py
│   │   ├── ffmpeg_service.py
│   │   ├── file_service.py
│   │   └── job_service.py
│   │
│   └── utils/
│       └── __init__.py
│
└── README.md
```

---

# Prerequisites

Install the following before running the project:

### Required

- Python 3.11 or newer
- Node.js suitable for the existing Next.js frontend
- npm, pnpm, or the package manager already used by the frontend
- FFmpeg
- FFprobe
- Internet access for URL-based downloads

Verify FFmpeg:

```bash
ffmpeg -version
ffprobe -version
```

Both commands must work from the terminal.

---

# Backend setup

## 1. Open the backend directory

```bash
cd backend
```

## 2. Create a Python virtual environment

Using a virtual environment is recommended so this project's Python packages do not conflict with other projects.

### Windows

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Create `.env` from `.env.example`.

Example:

```env
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
```

### Environment variables

| Variable | Purpose | Example |
|---|---|---|
| `FRONTEND_URL` | Allowed frontend CORS origin | `http://localhost:3000` |
| `MAX_FILE_SIZE_MB` | Maximum upload size for local video conversion | `500` |
| `MAX_CONCURRENT_DOWNLOADS` | Maximum concurrent async URL downloads in one Flask process | `2` |
| `DOWNLOAD_JOB_TTL_SECONDS` | How long completed jobs remain available | `1800` |

## 5. Start Flask

```bash
python app.py
```

The backend will be available at:

```text
http://localhost:5000
```

Health check:

```bash
curl http://localhost:5000/api/health
```

Expected response:

```json
{
  "status": "ok"
}
```

---

# Frontend setup

The frontend is a separate Next.js application.

From the frontend directory:

```bash
npm install
```

Then start the development server using the package manager and scripts already present in the frontend project, for example:

```bash
npm run dev
```

The frontend normally runs at:

```text
http://localhost:3000
```

The frontend should use the Flask backend as its API base URL.

Recommended environment variable:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Use the frontend project's existing environment-variable convention if it already has one.

For the v0.dev integration, use `FRONTEND_V0_INTEGRATION_PROMPT.md` from the backend package as the implementation guide. It is designed to extend the existing frontend architecture instead of rebuilding it.

---

# API overview

## Health

```http
GET /api/health
```

Response:

```json
{
  "status": "ok"
}
```

---

# Synchronous URL download API

The original synchronous endpoint remains available for backward compatibility.

```http
POST /api/download
```

Request:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp3"
}
```

or:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp4",
  "resolution": "medium"
}
```

Valid formats:

```text
mp3
mp4
```

Valid MP4 resolutions:

```text
highest
medium
lowest
```

Successful requests return the binary media file directly.

---

# Asynchronous download API

The progress-enabled frontend should use the asynchronous API.

## 1. Start a download

```http
POST /api/download/start
Content-Type: application/json
```

### MP3

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp3"
}
```

### MP4

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp4",
  "resolution": "highest"
}
```

Successful response:

```json
{
  "job_id": "abc123",
  "status": "queued",
  "progress_url": "/api/download/progress/abc123",
  "cancel_url": "/api/download/cancel/abc123",
  "file_url": "/api/download/file/abc123"
}
```

## 2. Poll progress

```http
GET /api/download/progress/{job_id}
```

Poll approximately every **500–1000 ms** while the job is active.

Example:

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

Possible statuses:

```text
queued
downloading
processing
completed
cancelled
failed
```

## 3. Cancel a download

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

Continue polling until the job reaches:

```text
cancelled
```

## 4. Retrieve the completed file

```http
GET /api/download/file/{job_id}
```

Call this only after the progress endpoint reports:

```text
status: completed
```

The response is the actual MP3/MP4 binary file.

---

# Resolution behavior

The user can choose:

```text
Highest
Medium
Lowest
```

The frontend sends:

```text
Highest -> highest
Medium  -> medium
Lowest  -> lowest
```

## Highest

Selects the best available video/audio combination.

## Medium

Targets 720p and falls back when 720p is unavailable.

Examples:

```text
Available: 1080p, 720p, 480p
Medium -> 720p
```

```text
Available: 1080p, 480p
Medium -> 480p
```

```text
Available: 1080p only
Medium -> 1080p
```

```text
Available: 360p only
Medium -> 360p
```

The backend reports the actual selected resolution through:

```text
effective_resolution
```

and explains fallback through:

```text
selection_note
```

An unavailable target resolution is therefore not automatically treated as an error.

## Lowest

Selects the lowest available video/audio combination.

---

# Download progress

The asynchronous job system reports:

- Progress percentage
- Downloaded bytes
- Total bytes when available
- Download speed
- ETA
- Current phase
- Actual selected resolution
- Requested resolution
- Job status

Typical frontend flow:

```text
User enters URL
      ↓
Select MP3 / MP4
      ↓
For MP4 → select resolution
      ↓
POST /api/download/start
      ↓
Receive job_id
      ↓
Poll /api/download/progress/{job_id}
      ↓
Show progress bar + speed + ETA
      ↓
User may cancel
      ↓
Completed
      ↓
GET /api/download/file/{job_id}
```

The backend keeps progress monotonic so the frontend progress bar does not unexpectedly move backwards.

For MP3, the job enters `processing` while FFmpeg extracts the MP3 after the download phase.

For MP4, the job enters `processing` while FFmpeg merges the downloaded streams.

---

# Cancellation behavior

Cancellation is cooperative.

When the frontend requests cancellation:

```http
POST /api/download/cancel/{job_id}
```

the backend marks cancellation as requested and the yt-dlp worker stops when it observes the cancellation event.

If FFmpeg processing has already started, cancellation may complete after that process returns. Partial and temporary files are then cleaned up.

The frontend should continue polling until the final state is:

```text
cancelled
```

---

# Filename handling

The backend uses the media title as the filename whenever possible.

The yt-dlp output is based on:

```text
%(title)s.%(ext)s
```

The backend also sanitizes filenames for Windows/Linux/macOS compatibility and prevents path traversal.

Responses include filename information through `Content-Disposition` and, when applicable:

```http
X-Download-Filename: ...
```

### Important frontend note

When the frontend uses:

```text
fetch() → blob() → temporary <a> → click()
```

the browser will not automatically preserve the server's attachment filename.

The frontend must read `Content-Disposition` (or `X-Download-Filename`) and set:

```ts
anchor.download = filename;
```

Otherwise the browser may save the file with a generic name such as:

```text
 download
```

---

# Local video → MP3

Endpoint:

```http
POST /api/convert
```

Content type:

```text
multipart/form-data
```

Form field:

```text
file
```

Example:

```bash
curl -X POST http://localhost:5000/api/convert \
  -F "file=@video.mp4" \
  --output converted.mp3
```

Maximum upload size is controlled through:

```env
MAX_FILE_SIZE_MB=500
```

Temporary files are removed after conversion.

---

# cURL examples

## Health

```bash
curl http://localhost:5000/api/health
```

## Synchronous MP3

```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=example","format":"mp3"}' \
  --output output.mp3
```

## Start asynchronous MP3

```bash
curl -X POST http://localhost:5000/api/download/start \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=example","format":"mp3"}'
```

## Start asynchronous MP4 at medium quality

```bash
curl -X POST http://localhost:5000/api/download/start \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=example","format":"mp4","resolution":"medium"}'
```

## Poll progress

```bash
curl http://localhost:5000/api/download/progress/JOB_ID
```

## Cancel

```bash
curl -X POST http://localhost:5000/api/download/cancel/JOB_ID
```

## Retrieve completed file

```bash
curl http://localhost:5000/api/download/file/JOB_ID --output output.mp4
```

---

# Error handling

The API returns JSON errors instead of HTML stack traces.

Example:

```json
{
  "error": "Invalid request. URL and format are required."
}
```

Other common errors include:

```json
{
  "error": "Unsupported format. Use mp3 or mp4."
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

Detailed server-side errors should be logged by Flask while clean messages are returned to the frontend.

---

# Temporary storage and jobs

The backend intentionally does not use a database.

Download jobs are stored in memory for the lifetime of the Flask process.

Temporary media files are stored in temporary directories and are deleted when no longer needed.

Completed jobs remain temporarily available so the frontend can retrieve the binary file. They are eventually removed according to:

```env
DOWNLOAD_JOB_TTL_SECONDS=1800
```

Because job state is in memory, the async architecture should be run as a **single Flask process** for local development and this project architecture.

If the project is later deployed with multiple WSGI worker processes or multiple server instances, shared job state/cancellation storage would be required.

---

# Security considerations

The backend implements reasonable application-level protections:

- Validates request bodies.
- Restricts URL schemes to HTTP/HTTPS.
- Disables playlists.
- Validates uploaded video extensions.
- Enforces upload size limits.
- Sanitizes filenames.
- Prevents path traversal.
- Uses subprocess argument arrays instead of shell command concatenation.
- Deletes temporary files.
- Does not expose Python tracebacks to clients.
- Does not implement DRM bypass or access-control circumvention.

---

# Troubleshooting

## `ffmpeg: command not found`

Install FFmpeg and add the directory containing `ffmpeg.exe` and `ffprobe.exe` to the Windows `PATH`.

Then open a new terminal and verify:

```bash
ffmpeg -version
ffprobe -version
```

## Flask starts but `/api/download` returns 400

First test yt-dlp directly:

```bash
python -m yt_dlp -f "bestaudio/best" --extract-audio --audio-format mp3 --audio-quality 192K --no-playlist "YOUR_URL"
```

If direct yt-dlp works but the API fails, check the Flask terminal logs for the server-side error.

## Browser downloads a file named `download`

The frontend is probably creating a Blob download without applying the filename from the HTTP response headers.

Read `Content-Disposition` or `X-Download-Filename` and set the anchor's `download` attribute explicitly.

## Progress remains at `processing`

This means the media has been downloaded and FFmpeg is finalizing the MP3 or MP4. Check that both `ffmpeg` and `ffprobe` are installed and accessible through `PATH`.

## Download cancellation does not stop instantly

Cancellation is cooperative. A running yt-dlp operation or an FFmpeg processing step may need to return before the worker can fully clean up the job.

---

# Development checklist

Before using the frontend integration, verify:

```text
[ ] Python 3.11+ installed
[ ] Virtual environment created and activated
[ ] pip dependencies installed
[ ] ffmpeg -version works
[ ] ffprobe -version works
[ ] Backend starts on port 5000
[ ] /api/health returns {"status":"ok"}
[ ] Direct yt-dlp MP3 test works
[ ] /api/download/start returns a job_id
[ ] /api/download/progress/{job_id} reports progress
[ ] /api/download/cancel/{job_id} cancels a job
[ ] /api/download/file/{job_id} returns the completed file
[ ] Frontend is running on port 3000
[ ] NEXT_PUBLIC_API_URL points to http://localhost:5000
[ ] Frontend preserves the downloaded filename
```

---

# License and usage

Add the project's chosen license here before public distribution.

The application is intended for personal or otherwise authorized media downloads/conversions. Respect the terms of service, copyright, and access permissions applicable to the media and platform being used.
