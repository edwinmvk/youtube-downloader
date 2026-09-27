# YouTube Downloader Backend

## Docker architecture

The Flask backend runs in its own Docker container. It is not directly exposed to the Windows host. Nginx is the public entry point.

```text
                         Browser
                            │
                            │ /api/*
                            ▼
                    ┌────────────────┐
                    │ Nginx :80      │
                    │ proxy_net      │
                    └───────┬────────┘
                            │
                            ▼
                 ┌─────────────────────────┐
                 │ BACKEND CONTAINER       │
                 │                         │
                 │ Gunicorn                │
                 │     ↓                   │
                 │ Flask :5000             │
                 │                         │
                 │ ├─ Request validation   │
                 │ ├─ Async jobs           │
                 │ ├─ Progress tracking    │
                 │ ├─ Cancellation         │
                 │ ├─ Filename handling    │
                 │ ├─ Temporary cleanup    │
                 │ ├─ yt-dlp               │
                 │ ├─ EJS / Deno           │
                 │ └─ FFmpeg               │
                 └──────────┬──────────────┘
                            │
                            │ Docker HTTP
                            │
                            ▼
                 ┌─────────────────────────┐
                 │ BGUTIL-PROVIDER         │
                 │ CONTAINER :4416         │
                 └──────────┬──────────────┘
                            │
                            ▼
                         YouTube
```

### Docker networks

```text
proxy_net
├── nginx
├── frontend
└── backend

backend_net
├── backend
└── bgutil-provider
```

The backend is attached to both networks.

```text
nginx              → backend:5000
backend            → bgutil-provider:4416
```

Port `5000` is internal to Docker and is not published to the Windows host.

Port `4416` is internal to Docker and is not published publicly.

## Features

- YouTube URL downloads as MP3 or MP4.
- MP4 quality selection: Highest, Medium, Lowest.
- Automatic fallback when a requested resolution tier is unavailable.
- Asynchronous download jobs with progress, speed, bytes, and ETA.
- Download cancellation.
- Local video-to-MP3 conversion.
- Batch conversion of up to 10 local videos.
- Direct MP3 response for one conversion and ZIP output for multiple conversions.
- Unicode-preserving filename sanitization.
- FFmpeg audio extraction and media merging.
- Temporary-file and job cleanup.
- yt-dlp EJS/Deno support.
- PO Token retrieval through the internal bgutil provider.

## Error handling

The backend returns structured JSON errors for expected failures instead of exposing Python stack traces or HTML error pages.

Handled failures include:

- Invalid or incomplete API requests.
- Unsupported media formats or resolutions.
- Invalid or unsupported URLs.
- Upload-size and file-validation failures.
- yt-dlp extraction/download failures.
- FFmpeg processing failures.
- Missing runtime dependencies inside the container.
- Cancellation of active asynchronous jobs.
- Expired or unavailable asynchronous jobs.

Detailed technical errors are logged server-side. Client responses contain safe, user-facing error messages.

Temporary files are removed after successful processing, cancellation, or failure.

## Port visibility

```text
Windows host
└── :80 → Nginx container :80

Docker internal only
├── Frontend :3000
├── Backend  :5000
└── bgutil-provider :4416
```
