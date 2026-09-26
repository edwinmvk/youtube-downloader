# Media Downloader — Flask Backend

A small Flask backend for the **Media Downloader** web application. The frontend is a separate Next.js application and communicates with this server through three REST endpoints.

## Features

- Download URL media as MP3 using yt-dlp + FFmpeg.
- Download URL media as MP4 using yt-dlp + FFmpeg.
- Convert an uploaded local video to MP3 using FFmpeg.
- Temporary storage only; no database or persistent download records.
- CORS configured for the Next.js frontend.
- Server-side validation and clean JSON error responses.
- No authentication or user accounts.

## Requirements

- Python 3.11+
- FFmpeg with both `ffmpeg` and `ffprobe` available on PATH
- Internet access for URL downloads

## Project structure

```text
backend/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── routes/
│   ├── __init__.py
│   ├── health.py
│   ├── download.py
│   └── convert.py
├── services/
│   ├── __init__.py
│   ├── yt_dlp_service.py
│   ├── ffmpeg_service.py
│   └── file_service.py
└── utils/
    └── __init__.py
```

## Windows setup

### 1. Create and activate a virtual environment

From the backend directory:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Install FFmpeg

Install a Windows FFmpeg build, then make sure the directory containing `ffmpeg.exe` and `ffprobe.exe` is on your system `PATH`.

A common manual approach is:

1. Download a Windows FFmpeg build from a reputable FFmpeg Windows build provider.
2. Extract it somewhere such as `C:\ffmpeg`.
3. Locate the `bin` directory containing `ffmpeg.exe` and `ffprobe.exe`, for example `C:\ffmpeg\bin`.
4. Open **Start → Edit the system environment variables → Environment Variables**.
5. Under **System variables**, edit `Path` and add the FFmpeg `bin` directory.
6. Close and reopen PowerShell/Command Prompt.
7. Verify both commands:

```powershell
ffmpeg -version
ffprobe -version
```

The backend checks both binaries before media conversion.

### 4. Configure environment variables

Copy `.env.example` to `.env` and adjust values when needed:

```env
FRONTEND_URL=http://localhost:3000
MAX_FILE_SIZE_MB=500
```

`FRONTEND_URL` controls the allowed CORS origin. `MAX_FILE_SIZE_MB` controls the maximum uploaded file size for `/api/convert`.

### 5. Run the backend

```powershell
python app.py
```

The server listens on:

```text
http://localhost:5000
```

## API

### GET `/api/health`

Successful response:

```json
{
  "status": "ok"
}
```

HTTP status: `200`.

### POST `/api/download`

Request header:

```http
Content-Type: application/json
```

MP3 request:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp3"
}
```

MP4 request:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "mp4"
}
```

Supported formats are exactly `mp3` and `mp4`.

Successful MP3 responses are returned as `audio/mpeg` with an attachment filename ending in `.mp3`. Successful MP4 responses are returned as `video/mp4` with an attachment filename ending in `.mp4`.

### POST `/api/convert`

Request header:

```http
Content-Type: multipart/form-data
```

The upload field name is exactly:

```text
file
```

Supported source extensions:

```text
.mp4
.mov
.mkv
.avi
.webm
```

The successful response is a binary MP3 file with `Content-Type: audio/mpeg`.

## Validation and errors

Invalid `/api/download` input returns:

```json
{
  "error": "Invalid request. URL and format are required."
}
```

Unsupported download format returns:

```json
{
  "error": "Unsupported format. Use mp3 or mp4."
}
```

Invalid or unsupported URLs return a clean JSON error instead of an HTML traceback.

An FFmpeg installation problem returns:

```json
{
  "error": "FFmpeg is not installed or is not available in PATH."
}
```

An oversized upload returns HTTP `413`:

```json
{
  "error": "File is too large."
}
```

Unsupported uploaded video extensions return HTTP `400`:

```json
{
  "error": "Unsupported video format."
}
```

Unexpected server-side details are logged on the server and are not exposed as Python stack traces to the frontend.

## curl examples

### Health

```bash
curl http://localhost:5000/api/health
```

### URL → MP3

```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.youtube.com/watch?v=example\",\"format\":\"mp3\"}" \
  --output output.mp3
```

### URL → MP4

```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.youtube.com/watch?v=example\",\"format\":\"mp4\"}" \
  --output output.mp4
```

### Local video → MP3

```bash
curl -X POST http://localhost:5000/api/convert \
  -F "file=@video.mp4" \
  --output converted.mp3
```

## Media processing behavior

### URL → MP3

The backend configures yt-dlp with `bestaudio/best`, disables playlists, and uses the `FFmpegExtractAudio` postprocessor with MP3 at 192 kbps. `merge_output_format=mp3` is intentionally not used as the only MP3 conversion mechanism.

### URL → MP4

The backend uses `bestvideo+bestaudio/best`, disables playlists, and requests MP4 output. When yt-dlp selects separate video and audio streams, FFmpeg performs the merge.

### Local video → MP3

The backend calls FFmpeg with an argument array equivalent to:

```text
ffmpeg -i input.mp4 -vn -map 0:a:0 -codec:a libmp3lame -b:a 192k output.mp3
```

The video stream is not re-encoded because only audio is needed.

## Temporary files and cleanup

Each URL download or local conversion gets its own temporary directory under the operating system's temporary location. Generated files are sent directly as binary Flask responses and the temporary directory is removed when the response closes. Error paths also delete the temporary directory.

No database, persistent download records, or permanent media storage are used.

## Security notes

- URL input is restricted to HTTP/HTTPS URLs.
- Playlists are disabled.
- Upload extensions are validated server-side.
- Flask's `MAX_CONTENT_LENGTH` enforces the configured upload size limit.
- User-controlled names are sanitized before use as filenames.
- FFmpeg is invoked with a subprocess argument array rather than shell string concatenation.
- Temporary files are deleted after requests.
- Python tracebacks are not returned to clients.
- This application does not implement DRM bypass, authentication bypass, or other access-control circumvention. Use it only with media you have permission to download or convert.
