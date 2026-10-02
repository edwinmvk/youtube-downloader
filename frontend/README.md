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
- Dedicated Audio Trimmer page with playback and range preview.
- Dedicated Audio Merger page with arrow-button ordering and smooth rearrangement animation.

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


## Audio editing pages

The frontend exposes three dedicated media-tool routes:

```text
/video-to-mp3
/audio-trimmer
/audio-merger
```

The pages use the project's existing shadcn-style `Button` component and the existing Tailwind/shadcn theme rather than introducing a separate component library.

### Video to MP3

The converter lets the user:

1. Select or drop up to 10 local video files.
2. Review and remove files before conversion.
3. Convert the selected videos to MP3 through the backend FFmpeg service.
4. Download one MP3 for a single input or a ZIP containing all converted files.
5. Continue editing the same set or start a new set after completion.

### Audio Trimmer

The trimmer lets the user:

1. Select one audio file.
2. Set the start and end of the section to keep with a single dual-handle range slider.
3. Use keyboard-accessible slider handles or numeric time inputs for precise adjustments.
4. Preview exactly that range in the browser.
5. Export and download the trimmed MP3.
6. Choose between continuing with the same song or starting with a new song after the download.

### Audio Merger

The merger lets the user:

1. Select multiple audio files, up to 10.
2. Drag files into the desired order.
3. Move files up/down or remove them.
4. Merge the ordered list into one MP3.
5. Choose between continuing with the current set or starting with a new set after download.

Supported audio extensions are:

```text
MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, WEBM
```

The existing `MAX_FILE_SIZE` limit applies to each uploaded file, while the backend request-size middleware continues to protect the overall request body.
