# YouTube Downloader Backend

Flask backend for the `youtube-downloader` project.

## Backend responsibilities

The backend handles:

- URL validation and media download requests.
- Asynchronous URL download jobs.
- Download progress, speed, ETA, and cancellation.
- MP3 extraction and MP4 merging through FFmpeg.
- MP4 resolution selection and fallback.
- Local video-to-MP3 conversion.
- Batch conversion of up to 10 local videos per request.
- Unicode-preserving filename handling.
- Temporary-file/job cleanup.
- JSON error responses.
- CORS for the Next.js application.
- Modern YouTube extraction using yt-dlp, EJS/Deno, and bgutil PO Token support.

## Backend architecture

```text
                         Flask Application
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
        routes/download.py                    routes/convert.py
              │                                   │
              ▼                                   ▼
        services/job_service.py            Temporary request workspace
              │                                   │
              ▼                                   ▼
        services/yt_dlp_service.py         services/ffmpeg_service.py
              │                                   │
      ┌───────┴────────┐                          ▼
      ▼                ▼                       FFmpeg
   yt-dlp          PO Token HTTP
                     Provider
      │                │
      └───────┬────────┘
              ▼
           YouTube
```

### Main modules

| Module | Responsibility |
|---|---|
| `app.py` | Flask application creation, configuration, CORS, error handlers, startup checks |
| `routes/health.py` | Health-check endpoint |
| `routes/download.py` | Synchronous and asynchronous URL-download APIs |
| `routes/convert.py` | Single- and multi-file local-video conversion API |
| `services/yt_dlp_service.py` | yt-dlp configuration, resolution selection, progress hooks, PO Token configuration, output discovery |
| `services/ffmpeg_service.py` | FFmpeg/ffprobe validation and local video-to-MP3 conversion |
| `services/job_service.py` | In-memory job registry, thread pool, cancellation events, TTL cleanup |
| `services/file_service.py` | Allowed extensions, Unicode-safe filename sanitization, collision handling |

## URL download architecture

The progress-enabled frontend uses the asynchronous API:

```text
POST /api/download/start
        │
        ▼
DownloadJobManager
        │
        ▼
ThreadPoolExecutor worker
        │
        ▼
yt-dlp service
        │
        ├── mweb player client
        └── bgutil HTTP PO Token provider
                    │
                    ▼
                  YouTube
        │
        ▼
FFmpeg post-processing / MP4 merge
        │
        ▼
Temporary output file
        │
        ▼
GET /api/download/file/{job_id}
```

The job state is held in memory. There is no database.

## Local video conversion architecture

```text
POST /api/convert
Content-Type: multipart/form-data
        │
        ▼
Validate 1–10 files
        │
        ▼
Temporary directory
        │
        ├── input_1.mp4 → FFmpeg → Title 1.mp3
        ├── input_2.mkv → FFmpeg → Title 2.mp3
        └── ... up to 10 files
        │
        ├── one output  → audio/mpeg
        └── multiple    → application/zip
        │
        ▼
Response closes
        │
        ▼
Temporary directory removed
```

### Multi-file conversion contract

The conversion endpoint keeps the existing single-file field for compatibility:

```text
file
```

The new batch flow uses repeated multipart fields named:

```text
files
```

Example request:

```text
files=file1.mp4
files=file2.mkv
files=file3.webm
```

Rules:

- Maximum: **10 files per request**.
- Supported extensions: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`.
- If one file is submitted, the response is the MP3 directly.
- If 2–10 files are submitted, the response is a ZIP containing all MP3 files.
- If any uploaded file is unsupported, the request is rejected with a JSON error.
- The existing aggregate Flask upload-size limit still applies.

## Unicode filename handling

The backend deliberately does not use Werkzeug's ASCII-oriented `secure_filename()` for generated MP3 names.

Filenames preserve Unicode scripts when possible, including:

```text
Malayalam
Hindi
English
Mixed Malayalam + English
Mixed Hindi + English
```

For example:

```text
സ്വർഗീയ സിംഹാസനത്തിൽ വാഴും ｜ SWARGEEYA SIMHASANATTHIL VAZHUM.mp3
```

Invalid filesystem characters such as `<>:"/\\|?*` and control characters are replaced, path traversal is prevented, and excessive length is limited without transliterating the remaining Unicode text.

When duplicate output names occur during a multi-file conversion, the backend adds a suffix such as:

```text
song.mp3
song (2).mp3
```

The ZIP preserves these Unicode filenames as UTF-8 entries.

## Prerequisites

Install these before starting the backend:

### Python

Python **3.11 or newer**.

```cmd
python --version
```

### FFmpeg and ffprobe

Both are required for MP3 extraction and MP4 merging.

```cmd
ffmpeg -version
ffprobe -version
```

### Deno

Deno is used by yt-dlp's JavaScript challenge solver.

```cmd
deno --version
```

### Docker Desktop

Docker is used for the local bgutil PO Token HTTP provider and will also be used by the later deployment architecture.

```cmd
docker --version
docker compose version
```

## Python environment

From the repository root:

```cmd
cd backend
python -m venv venv
```

Activate in Command Prompt:

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

The current requirements include:

```text
Flask
flask-cors
yt-dlp[default]
python-dotenv
bgutil-ytdlp-pot-provider==2.0.0
```

## Environment configuration

Create `.env` from `.env.example`.

Local configuration:

```env
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
POT_PROVIDER_URL=http://127.0.0.1:4416
```

### Environment variables

| Variable | Purpose | Local value |
|---|---|---|
| `FRONTEND_URL` | Allowed Next.js origin for CORS | `http://localhost:3000` |
| `MAX_FILE_SIZE_MB` | Maximum request/upload size | `500` |
| `MAX_CONCURRENT_DOWNLOADS` | Maximum URL-download workers | `2` |
| `DOWNLOAD_JOB_TTL_SECONDS` | In-memory job retention after completion | `1800` |
| `POT_PROVIDER_URL` | bgutil PO Token HTTP service | `http://127.0.0.1:4416` |

Do not commit `.env`.

## Start the local PO Token provider

The backend expects the bgutil HTTP service to be available on port `4416`.

```cmd
docker run --name bgutil-provider -d --init ^
  -p 127.0.0.1:4416:4416 ^
  brainicism/bgutil-ytdlp-pot-provider:2.0.0
```

Verify:

```cmd
docker ps
docker logs bgutil-provider
```

The local provider URL is:

```text
http://127.0.0.1:4416
```

The backend explicitly passes `POT_PROVIDER_URL` to yt-dlp's `youtubepot-bgutilhttp` extractor configuration and uses the `mweb` client.

A verbose yt-dlp check should contain lines similar to:

```text
Generating a gvs PO Token for mweb client via bgutil HTTP server
Retrieved a gvs PO Token for mweb client
```

## Start the backend

From the `backend` directory with the virtual environment activated:

```cmd
python app.py
```

The API is available at:

```text
http://localhost:5000
```

Health check:

```cmd
curl.exe http://localhost:5000/api/health
```

Expected:

```json
{
  "status": "ok"
}
```

## API overview

### Health

```http
GET /api/health
```

### Synchronous URL download

Backward-compatible endpoint:

```http
POST /api/download
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

### Asynchronous URL download

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

### Local video conversion

```http
POST /api/convert
Content-Type: multipart/form-data
```

Single file compatibility:

```text
file=@video.mp4
```

Batch:

```text
files=@video1.mp4
files=@video2.mkv
files=@video3.webm
```

## cURL examples

### Single conversion

```cmd
curl.exe -X POST "http://localhost:5000/api/convert" -F "file=@video.mp4" --output converted.mp3
```

### Batch conversion

```cmd
curl.exe -X POST "http://localhost:5000/api/convert" ^
  -F "files=@video1.mp4" ^
  -F "files=@video2.mkv" ^
  -F "files=@video3.webm" ^
  --output converted_audio.zip
```

## Error handling

The backend returns JSON for API failures and does not expose Python tracebacks to clients.

Examples:

```json
{
  "error": "You can convert a maximum of 10 files at once."
}
```

```json
{
  "error": "Unsupported video format: example.txt"
}
```

```json
{
  "error": "FFmpeg is not installed or is not available in PATH."
}
```

URL-download errors are logged server-side and returned as clean job/API errors.

## Temporary storage and cleanup

- URL-download jobs use temporary directories.
- Local conversion uses a temporary request directory.
- Completed, failed, cancelled, and delivered jobs are cleaned up.
- No generated media is intentionally stored permanently.

## Security

- Validate URL and request input on the server.
- Restrict uploaded video extensions.
- Enforce the request-size limit.
- Limit local conversion to 10 files per request.
- Preserve Unicode filenames without allowing path traversal.
- Invoke FFmpeg with argument arrays, not shell command strings.
- Keep the PO Token provider private; do not expose port `4416` to untrusted clients.
- Do not expose stack traces.
- Use the application only for content you have permission to download or convert.
