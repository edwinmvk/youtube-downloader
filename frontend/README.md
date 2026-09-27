# YouTube Downloader Frontend

## Docker architecture

The Next.js frontend runs as a separate Docker container. Its port is internal to Docker and is not published to the Windows host.

```text
                                Browser
                                   │
                                   │ http://localhost
                                   ▼
                         Windows host port :80
                                   │
                                   ▼
                          ┌─────────────────┐
                          │ Nginx container │
                          │      :80        │
                          └────────┬────────┘
                                   │
                         ┌─────────┴─────────┐
                         │                   │
                         │ /                 │ /api/*
                         ▼                   ▼
                 ┌────────────────┐  ┌────────────────┐
                 │ FRONTEND       │  │ BACKEND       │
                 │ CONTAINER      │  │ CONTAINER     │
                 │                │  │               │
                 │ Next.js :3000  │  │ Gunicorn :5000│
                 └────────────────┘  └───────┬───────┘
                                             │
                                             ▼
                                      bgutil-provider
                                           :4416
```

### Browser communication

The browser uses one public origin:

```text
http://localhost
```

The frontend sends API requests to:

```text
/api/*
```

Nginx routes those requests to the backend container.

The browser does not communicate directly with:

```text
backend:5000
bgutil-provider:4416
```

### Docker network

```text
proxy_net
├── nginx
├── frontend
└── backend
```

The frontend listens on:

```text
3000
```

but port `3000` is internal to Docker.

Nginx reaches the frontend using the Docker service name:

```text
frontend:3000
```

## Features

- YouTube URL input.
- MP3 / MP4 selection.
- MP4 quality selection: Highest, Medium, Lowest.
- Resolution fallback messages.
- Asynchronous download progress.
- Download speed and ETA display.
- Download cancellation.
- Automatic file retrieval after completion.
- Preservation of the backend-provided filename.
- Local video upload and MP3 conversion.
- Multi-file upload for up to 10 videos.
- ZIP download handling for multi-file conversion.
- Unicode filename preservation.

## Error handling

The frontend handles API, download, conversion, and network failures as user-facing states rather than treating every response as a successful file.

Handled UI cases include:

- Invalid requests or URLs.
- Unsupported resolution.
- Download failure.
- Cancelled downloads.
- Conversion failure.
- Upload validation failure.
- Expired or unavailable jobs.
- Network or server errors.

For active URL downloads, polling stops when the job reaches:

```text
completed
cancelled
failed
```

Completed file downloads use the filename supplied by the backend instead of a generic browser filename.

## Port visibility

```text
Windows host
└── :80 → Nginx

Docker internal
└── Frontend :3000
```

The frontend is not directly published on `localhost:3000` in the Docker-based setup.
