# YouTube Downloader Frontend

Next.js frontend for the `youtube-downloader` project.

## Frontend responsibilities

The frontend provides the user interface for:

- URL entry and media-format selection.
- MP3 and MP4 download selection.
- Highest / Medium / Lowest MP4 quality selection.
- Resolution fallback messages.
- Download progress, speed, ETA, and processing state.
- Download cancellation.
- Automatic binary-file download after a completed async job.
- Preservation of the backend-provided media filename, including Unicode names.
- Single local-video upload to MP3.
- Batch local-video selection of up to 10 files.
- Batch conversion download of the generated ZIP.

## Frontend architecture

```text
                         Next.js Application
                                  │
                  ┌───────────────┴────────────────┐
                  │                                │
                  ▼                                ▼
          URL Download UI                  Local Conversion UI
                  │                                │
        ┌─────────┼─────────┐            ┌─────────┴─────────┐
        │         │         │            │                   │
        ▼         ▼         ▼            ▼                   ▼
      MP3       MP4     Resolution    1 file            2–10 files
                │        selector        │                   │
                ▼                       ▼                   ▼
          Async job API            /api/convert        /api/convert
                │                                           │
                ▼                                           ▼
        Progress polling                              ZIP response
                │
                ▼
        Cancel / complete
                │
                ▼
       Completed file fetch
```

## URL download flow

```text
User enters URL
      ↓
Select MP3 / MP4
      ↓
If MP4 → Highest / Medium / Lowest
      ↓
POST /api/download/start
      ↓
Receive job_id
      ↓
Poll /api/download/progress/{job_id}
      ↓
Show progress + speed + ETA + phase
      ↓
Optional cancel
      ↓
completed
      ↓
GET /api/download/file/{job_id}
      ↓
Read Content-Disposition / X-Download-Filename
      ↓
Browser saves the real media title
```

## Local conversion flow

```text
Select up to 10 video files
      ↓
Display selected-file list
      ↓
POST /api/convert using repeated `files` fields
      ↓
1 selected file → MP3 response
2–10 selected files → ZIP response
      ↓
Preserve each original filename as the MP3 name
      ↓
Browser downloads the result
```

## Prerequisites

Install the following before running the frontend:

- Node.js supported by the existing Next.js project. For a current Next.js 16 project, Node.js 20.9+ is required.
- A package manager matching the repository lockfile: npm, pnpm, yarn, or bun.
- A modern browser.
- A running FastAPI backend at `http://localhost:5000` for local development.

## Install dependencies

From the repository root:

```cmd
cd frontend
```

Then use the package manager already selected by the project.

### npm

```cmd
npm install
```

## Environment configuration

Create `.env` from `.env.example`.

Typical local value:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Start the frontend

Start the backend first, then from the `frontend` directory run:

```cmd
npm run dev
```

The frontend normally runs at:

```text
http://localhost:3000
```

## Multiple-file conversion UI

The local conversion UI should allow the user to select up to **10** supported video files at once.

Supported extensions:

```text
.mp4
.mov
.mkv
.avi
.webm
```

Recommended UI behavior:

- Use a single `multiple` file input or the existing drag-and-drop component.
- Show every selected file in the existing conversion card/list.
- Display filename and useful metadata such as size.
- Allow removing an individual file before conversion.
- Reject or disable selection when more than 10 files would be submitted.
- Do not silently discard the 11th file.
- Preserve Unicode filenames in the UI.

Send the request as `multipart/form-data` using repeated `files` fields:

```ts
const formData = new FormData();
for (const file of selectedFiles) {
  formData.append("files", file);
}
```

Do not manually set the `Content-Type` header for `FormData`; let the browser set the multipart boundary.

### Response handling

For one selected file:

```text
Content-Type: audio/mpeg
```

Download the returned Blob using its server-provided filename.

For two to ten selected files:

```text
Content-Type: application/zip
```

Download the ZIP. The ZIP contains one MP3 per source video.

Use the response filename when available rather than hardcoding `download`.

## Unicode filename handling

The backend intentionally preserves Unicode output names. The frontend must not transliterate, ASCII-normalize, or replace Malayalam/Hindi characters.

Examples of valid output names include:

```text
സ്വർഗീയ സിംഹാസനത്തിൽ വാഴും.mp3
भक्ति गीत.mp3
Malayalam English Mixed Title.mp3
हिंदी English Mixed Title.mp3
```

When downloading a Blob response, prefer this filename resolution order:

1. `X-Download-Filename`, when present.
2. RFC 5987/6266 `filename*` from `Content-Disposition`.
3. Quoted/plain `filename` from `Content-Disposition`.
4. A sensible final fallback such as `converted.mp3` or `converted_audio.zip`.

Do not use `download` as the default filename.

## Existing URL-download UI

For URL downloads, use the backend async API rather than the old synchronous API for the progress-enabled experience:

```text
POST /api/download/start
GET  /api/download/progress/{job_id}
POST /api/download/cancel/{job_id}
GET  /api/download/file/{job_id}
```

Poll about every 500–1000 ms while active and stop polling on `completed`, `cancelled`, or `failed`.

Keep the current architecture, components, service layer, design system, and routing. New functionality should be implemented as an extension of the existing frontend rather than a replacement.

## Error handling

Show backend-provided human-readable error messages in the existing error state or toast.

Handle at least:

- More than 10 selected files.
- Unsupported video format.
- Empty file.
- File too large.
- Conversion failure.
- Backend unavailable.
- URL download failure.
- Cancelled download.

Do not expose Python tracebacks or raw internal server errors in the UI.
