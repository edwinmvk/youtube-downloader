# Media Downloader Backend

Flask backend for the `youtube-downloader` project.

Repository structure:

```text
youtube-downloader/
├── backend/
└── frontend/
```

The backend is responsible for media extraction/download, FFmpeg processing, asynchronous download jobs, cancellation, resolution selection, and local video-to-MP3 conversion.

## Features

- Download a URL as MP3.
- Download a URL as MP4.
- MP4 resolution presets: `highest`, `medium`, `lowest`.
- Automatic resolution fallback when the requested tier is unavailable.
- Asynchronous download jobs with progress tracking.
- Download cancellation.
- Local video upload -> MP3 conversion.
- FFmpeg audio extraction and video/audio merging.
- Temporary job directories with cleanup.
- YouTube titles used for output filenames.
- Safe filename sanitization.
- JSON errors instead of HTML stack traces.
- CORS configured for the Next.js frontend.
- yt-dlp EJS support using Deno.
- PO Token support through `bgutil-ytdlp-pot-provider`.
- Same PO Token architecture can run locally and in Docker/production.

## Local Prerequisites

Install the following before starting the backend.

### 1. Python

Python 3.11+ is required.

Check:

```cmd
python --version
```

### 2. FFmpeg and ffprobe

FFmpeg is required for MP3 extraction and MP4 merging.

Check:

```cmd
ffmpeg -version
ffprobe -version
```

Both commands must work from the terminal.

### 3. Deno

Deno is used by yt-dlp for JavaScript challenge solving.

Check:

```cmd
deno --version
```

### 4. Docker Desktop

Docker is not required for the basic non-Docker local development flow, but it is required for the recommended PO Token provider setup and for the later Docker deployment architecture.

Check:

```cmd
docker --version
docker compose version
```

## Python Virtual Environment

Open CMD in the backend folder:

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\backend
```

Create the environment:

```cmd
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

You should see `(venv)` in the terminal prompt.

## Install Python Dependencies

Upgrade pip:

```cmd
python -m pip install --upgrade pip
```

Install the backend dependencies:

```cmd
python -m pip install -r requirements.txt
```

Expected key packages:

```text
Flask
flask-cors
yt-dlp[default]
python-dotenv
bgutil-ytdlp-pot-provider
```

`yt-dlp[default]` installs the EJS support package used by modern YouTube extraction. `bgutil-ytdlp-pot-provider` provides the yt-dlp plugin that communicates with the PO Token HTTP service.

## Environment Configuration

Create `.env` from `.env.example`.

For local development, use:

```env
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_JOB_TTL_SECONDS=1800
POT_PROVIDER_URL=http://127.0.0.1:4416
```

### Environment variables

| Variable | Description | Local example |
|---|---|---|
| `FRONTEND_URL` | Allowed frontend CORS origin | `http://localhost:3000` |
| `MAX_FILE_SIZE_MB` | Maximum local upload size | `500` |
| `MAX_CONCURRENT_DOWNLOADS` | Maximum simultaneous URL download jobs | `2` |
| `DOWNLOAD_JOB_TTL_SECONDS` | In-memory job expiry period | `1800` |
| `POT_PROVIDER_URL` | URL of the bgutil PO Token HTTP server | `http://127.0.0.1:4416` |

Do not commit `.env` to Git.

## PO Token Provider

Modern YouTube extraction can require Proof-of-Origin (PO) tokens. This project uses `bgutil-ytdlp-pot-provider` and its HTTP server instead of manually copying tokens or browser cookies into the application.

The local architecture is:

```text
Flask / yt-dlp
      |
      | HTTP :4416
      v
bgutil PO Token Provider
      |
      v
   YouTube
```

### Start the local provider

Start Docker Desktop first, then run:

```cmd
docker run --name bgutil-provider -d --init ^
  -p 127.0.0.1:4416:4416 ^
  brainicism/bgutil-ytdlp-pot-provider:2.0.0
```

Verify the container:

```cmd
docker ps
```

Inspect logs if needed:

```cmd
docker logs bgutil-provider
```

The provider should be reachable at:

```text
http://127.0.0.1:4416
```

### Verify that yt-dlp sees the PO Token plugin

From the activated virtual environment:

```cmd
python -m yt_dlp -v "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

The debug output should contain something similar to:

```text
[debug] [youtube] [pot] PO Token Providers: bgutil:http-2.0.0 (external), ...
```

### Verify actual PO Token generation

The recommended test is:

```cmd
python -m yt_dlp -v ^
  --extractor-args "youtube:player_client=mweb;youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416" ^
  -f "bestaudio/best" ^
  --extract-audio ^
  --audio-format mp3 ^
  --audio-quality 192K ^
  --no-playlist ^
  "https://youtu.be/msjA3KVNH7g?si=hesR6sxIkuK_Asr3"
```

A successful run should contain lines similar to:

```text
[youtube] [pot:bgutil:http] Generating a gvs PO Token for mweb client via bgutil HTTP server
[youtube] [pot:bgutil:http] Retrieved a gvs PO Token for mweb client
```

and should continue to a successful media download and FFmpeg conversion.

### Why `POT_PROVIDER_URL` exists

The provider URL must not be hardcoded to `127.0.0.1` because that is only correct when Flask and the provider are both accessed from the local machine.

Local development:

```env
POT_PROVIDER_URL=http://127.0.0.1:4416
```

Docker Compose / production:

```env
POT_PROVIDER_URL=http://bgutil-provider:4416
```

Inside Docker, `bgutil-provider` is the Compose service name. `127.0.0.1` inside the backend container would point back to the backend container itself.

## Start the Flask Backend

With the virtual environment activated and `.env` configured:

```cmd
python app.py
```

Expected:

```text
 * Running on http://127.0.0.1:5000
```

The backend listens on all interfaces when running in a container so that Nginx/Docker can reach it.

## Health Check

```cmd
curl.exe http://localhost:5000/api/health
```

Expected:

```json
{
  "status": "ok"
}
```

## API Overview

### Health

```http
GET /api/health
```

### Existing synchronous URL download

This endpoint remains available for backward compatibility:

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

Successful requests return the generated binary file directly.

### Start asynchronous download

The frontend should use the asynchronous workflow for progress and cancellation:

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

Typical response:

```json
{
  "job_id": "abc123",
  "status": "queued",
  "progress_url": "/api/download/progress/abc123",
  "cancel_url": "/api/download/cancel/abc123",
  "file_url": "/api/download/file/abc123"
}
```

### Progress

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

Progress responses can contain:

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

### Cancel

```http
POST /api/download/cancel/{job_id}
```

The frontend should keep polling until the job reports `cancelled`.

### Retrieve completed file

```http
GET /api/download/file/{job_id}
```

Call this only after the progress endpoint reports `completed`.

The response is the generated MP3 or MP4 file. The backend supplies a `Content-Disposition` filename based on the media title.

### Local video -> MP3

```http
POST /api/convert
Content-Type: multipart/form-data
```

Field name:

```text
file
```

Supported video extensions include:

```text
.mp4
.mov
.mkv
.avi
.webm
```

The upload is stored temporarily, processed with FFmpeg, returned as MP3, and cleaned up.

## MP4 Resolution Selection

User-facing values:

```text
highest
medium
lowest
```

Behavior:

- `highest` selects the best available video/audio combination.
- `medium` targets a middle/high-quality tier (currently up to 720p) and falls back to the closest available resolution.
- `lowest` selects the lowest available video resolution.

When the requested tier is unavailable, the backend should return the actual height in `effective_resolution` and a human-readable `selection_note`.

Example:

```text
Requested: medium
Target: 720p
Available: 480p
Result: 480p
Note: 720p is not available; using the closest available resolution: 480p.
```

The fallback is not treated as an error.

## MP3 Download Implementation

The backend uses yt-dlp's FFmpeg audio postprocessor rather than treating `merge_output_format=mp3` as the MP3 conversion mechanism.

The effective yt-dlp behavior is equivalent to:

```python
ydl_opts = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ],
}
```

For the current YouTube setup, the extractor also uses the `mweb` client with the bgutil HTTP PO Token provider.

## Filename Handling

The backend uses the media title supplied by yt-dlp when possible.

The filename is sanitized to:

- remove invalid filesystem characters;
- prevent path traversal;
- avoid excessive filename length;
- preserve a readable title.

The backend also sends the filename through `Content-Disposition` and exposes filename-related response headers to the frontend when required for browser downloads.

The frontend must preserve that filename when downloading a Blob. Do not hardcode a browser filename such as `download`.

## Error Handling

The backend converts expected errors into JSON responses and does not expose Python stack traces.

Typical errors include:

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

If YouTube temporarily rejects extraction, the technical yt-dlp error is logged server-side and the API should return a safe, user-facing message instead of a traceback.

## YouTube Troubleshooting

### `Sign in to confirm you're not a bot`

Check the following in order:

```cmd
python -m pip install -U "yt-dlp[default]"
deno --version
```

Then verify that the PO Token provider is running:

```cmd
docker ps
docker logs bgutil-provider
```

And test using the `mweb` client plus bgutil:

```cmd
python -m yt_dlp -v ^
  --extractor-args "youtube:player_client=mweb;youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416" ^
  -f "bestaudio/best" ^
  --extract-audio ^
  --audio-format mp3 ^
  --audio-quality 192K ^
  --no-playlist ^
  "YOUR_YOUTUBE_URL"
```

You should see:

```text
Generating a gvs PO Token for mweb client via bgutil HTTP server
Retrieved a gvs PO Token for mweb client
```

### HTTP 403 while downloading media

A 403 can occur when the requested client/format does not have the required YouTube token context. Verify that `mweb` and the PO Token provider are being used.

### HTTP 429 / bot challenge

Do not implement aggressive retry loops for an already-blocked request. Stop the job, return a clean retry-later message, and log the underlying yt-dlp error server-side.

## Docker / Production Notes

The intended production topology is:

```text
Internet
   |
   v
Nginx :80/:443
   |
   +--> frontend :3000
   |
   +--> backend :5000
              |
              +--> bgutil-provider :4416
                            |
                            v
                         YouTube
```

Only Nginx should be publicly exposed in production.

For Docker Compose, the backend should use:

```env
POT_PROVIDER_URL=http://bgutil-provider:4416
```

Do not expose the PO Token provider publicly. It is an internal service used by the backend.

## Useful Checks

Run these from the activated backend environment:

```cmd
python --version
python -m pip show yt-dlp
python -m pip show yt-dlp-ejs
python -m pip show bgutil-ytdlp-pot-provider
deno --version
ffmpeg -version
ffprobe -version
docker --version
docker compose version
```

Check the provider:

```cmd
docker ps
docker logs bgutil-provider
```

## Security and Usage

- Validate all incoming URLs and request bodies.
- Validate uploaded file extensions and upload size.
- Sanitize filenames.
- Prevent path traversal.
- Do not build shell commands by concatenating user input.
- Use subprocess argument arrays when invoking FFmpeg.
- Delete temporary media after job completion/cancellation/failure.
- Keep the PO Token provider internal; do not expose port `4416` publicly.
- Do not expose Python stack traces to clients.
- Do not implement DRM bypass or authentication bypass mechanisms.
- Use the application only for media you have permission to download or convert.

## Git Ignore

Do not commit:

```text
venv/
.env
__pycache__/
*.pyc
```

Temporary downloaded media and job files should also not be committed.

## Local Startup Checklist

From `youtube-downloader/backend`:

```cmd
venv\Scripts\activate
python -m pip install -r requirements.txt
```

Make sure the PO Token provider is running:

```cmd
docker ps
```

Verify `.env` contains:

```env
POT_PROVIDER_URL=http://127.0.0.1:4416
```

Start Flask:

```cmd
python app.py
```

Then verify:

```cmd
curl.exe http://localhost:5000/api/health
```

Start the Next.js frontend from `youtube-downloader/frontend` and open:

```text
http://localhost:3000
```

## Important

The current local PO Token setup has been validated with the following successful yt-dlp flow:

```text
yt-dlp
  -> mweb client
  -> bgutil HTTP PO Token provider
  -> GVS PO Token retrieved
  -> YouTube media request
  -> media downloaded
  -> FFmpeg conversion
```

For deployment, keep the same architecture and change only the provider URL from the local address to the Docker service name:

```text
Local:   http://127.0.0.1:4416
Docker:  http://bgutil-provider:4416
```
