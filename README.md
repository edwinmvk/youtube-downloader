# YouTube Downloader

A full-stack media downloader built with a Next.js frontend and a Python Flask backend.

## Features

- YouTube URL to MP3.
- YouTube URL to MP4.
- MP4 quality selection: **Highest**, **Medium**, and **Lowest**.
- Automatic resolution fallback when the requested quality tier is unavailable.
- Asynchronous URL download jobs.
- Live download progress with percentage, transferred bytes, speed, and ETA.
- Cancel/abort for active URL downloads.
- Local video to MP3 conversion.
- Batch local video conversion: up to **10 videos per request**.
- Batch conversion returns a ZIP containing the generated MP3 files.
- Original media/file titles are preserved in output filenames when possible, including Malayalam, Hindi, English, and mixed-language names.
- Filename sanitization that removes filesystem-invalid characters without transliterating Unicode scripts.
- FFmpeg-based MP3 extraction and MP4 stream merging.
- Modern YouTube extraction support through yt-dlp, EJS/Deno, and a bgutil PO Token provider.
- Temporary media storage with cleanup.
- No database, authentication, user accounts, ORM, or persistent media records.

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
                              │ • Resolution selector  │
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
                              │     Flask Backend       │
                              │                         │
                              │ • API validation       │
                              │ • Async job manager     │
                              │ • Progress callbacks    │
                              │ • Cancellation          │
                              │ • File conversion       │
                              │ • Filename sanitizing   │
                              │ • Temporary cleanup     │
                              └───────┬─────────┬───────┘
                                      │         │
                         URL downloads │         │ local conversion
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

## URL-download flow

```text
User selects MP3 or MP4
        ↓
For MP4: select Highest / Medium / Lowest
        ↓
POST /api/download/start
        ↓
Flask creates an in-memory job
        ↓
yt-dlp + mweb + PO Token provider
        ↓
YouTube media download
        ↓
FFmpeg post-processing / merging
        ↓
Frontend polls /api/download/progress/{job_id}
        ↓
User may cancel with /api/download/cancel/{job_id}
        ↓
Completed
        ↓
GET /api/download/file/{job_id}
        ↓
Browser saves the original media title
```

## Local-video conversion flow

```text
User selects 1–10 local videos
        ↓
POST /api/convert (multipart/form-data)
        ↓
Flask validates all files
        ↓
Temporary input files
        ↓
FFmpeg extracts first audio stream to MP3
        ↓
1 file → direct MP3 response
2–10 files → ZIP response
        ↓
Temporary files are cleaned up
```

## Project structure

```text
youtube-downloader/
├── README.md
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── README.md
│   ├── FRONTEND_V0_BATCH_CONVERT_CONTINUATION_PROMPT.md
│   ├── routes/
│   ├── services/
│   └── utils/
└── frontend/
    ├── package.json
    ├── README.md
    └── ...
```
