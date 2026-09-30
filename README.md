# YouTube Downloader

A full-stack media downloading and conversion application built with a **Next.js frontend** and a **Python FastAPI backend**.

The project combines URL-based media downloads, local video conversion, batch processing, progress tracking, cancellation, quality selection, Unicode-safe filenames, and modern YouTube extraction into a single application.

## Features

- Download media from YouTube URLs as **MP3**.
- Download media from YouTube URLs as **MP4**.
- Select MP4 quality using **Highest**, **Medium**, or **Lowest**.
- Automatically choose a suitable available resolution when the requested quality tier is unavailable.
- Process URL downloads through asynchronous background jobs.
- Display live download progress, including percentage, transferred data, speed, and ETA.
- Cancel an active URL download.
- Convert local video files to MP3.
- Submit up to **10 local videos in one conversion request**.
- Package multiple converted MP3 files into a ZIP archive.
- Preserve media and uploaded filenames whenever possible.
- Keep **Malayalam, Hindi, English, and mixed-language filenames** intact without transliterating Unicode scripts.
- Sanitize filenames for filesystem safety while retaining their original language and readable text.
- Use FFmpeg for MP3 extraction and MP4 audio/video merging.
- Use modern yt-dlp YouTube extraction with **EJS/Deno** and the **bgutil PO Token provider**.
- Store generated media temporarily and remove it after processing.
- Run without a database, authentication, user accounts, ORM, or persistent media records.

## Whole-project architecture

```text
                                    Internet / Browser
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │    Next.js Frontend     │
                              │                         │
                              │ • URL download UI      │
                              │ • MP3 / MP4 selection  │
                              │ • Quality selection    │
                              │ • Progress + ETA       │
                              │ • Cancel download      │
                              │ • Multi-file upload    │
                              │ • Filename handling    │
                              └────────────┬────────────┘
                                           │
                              REST / JSON / multipart
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │     FastAPI Backend       │
                              │                         │
                              │ • Request validation    │
                              │ • Async job management  │
                              │ • Progress callbacks    │
                              │ • Download cancellation │
                              │ • Media conversion      │
                              │ • Filename sanitization │
                              │ • Temporary cleanup     │
                              └───────┬─────────┬───────┘
                                      │         │
                       URL downloads  │         │  local conversion
                                      │         │
                                      ▼         ▼
                               ┌──────────┐  ┌──────────┐
                               │  yt-dlp  │  │  FFmpeg  │
                               └────┬─────┘  └──────────┘
                                    │
                      YouTube       │
                      extraction    │
                                    ▼
                         ┌─────────────────────┐
                         │ EJS / Deno          │
                         │ bgutil PO Token     │
                         │ Provider            │
                         └──────────┬──────────┘
                                    │
                                    ▼
                                  YouTube
```

## URL download flow

```text
User enters a media URL
        ↓
Choose MP3 or MP4
        ↓
For MP4: choose Highest / Medium / Lowest
        ↓
POST /api/download/start
        ↓
FastAPI creates an in-memory download job
        ↓
yt-dlp + mweb + PO Token provider
        ↓
YouTube media retrieval
        ↓
FFmpeg extraction / merging
        ↓
Frontend polls /api/download/progress/{job_id}
        ↓
User may cancel through /api/download/cancel/{job_id}
        ↓
Job completes
        ↓
GET /api/download/file/{job_id}
        ↓
Browser saves the file using its original media title
```

## Local-video conversion flow

```text
User selects 1–10 local video files
        ↓
POST /api/convert (multipart/form-data)
        ↓
FastAPI validates the complete upload
        ↓
Files are written to temporary storage
        ↓
FFmpeg extracts audio to MP3
        ↓
1 file  → direct MP3 response
2–10 files → ZIP containing MP3 files
        ↓
Temporary inputs and outputs are cleaned up
```

## Project structure

```text
youtube-downloader/
├── README.md
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   ├── routes/
│   ├── services/
│   └── utils/
│
└── frontend/
    ├── package.json
    ├── README.md
    └── ...
```
