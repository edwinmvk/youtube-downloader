# Media Downloader Frontend

Next.js frontend for the `youtube-downloader` project.

The frontend runs locally at:

```text
http://localhost:3000
```

It communicates with the Flask backend at:

```text
http://localhost:5000
```

## Features

- URL input for media downloads
- MP3 / MP4 selection
- MP4 resolution selection: Highest / Medium / Lowest
- Resolution fallback messages from the backend
- Asynchronous download progress
- Download speed and ETA display
- Cancel Download action
- Automatic download after completion
- Preservation of the actual backend filename
- Existing local-video → MP3 upload flow
- Existing Next.js architecture and design system should be preserved

## Prerequisites

### Required software

- Node.js **20.9+** for current Next.js 16 projects
- npm, pnpm, yarn, or bun matching the project's lockfile
- A running Flask backend at `http://localhost:5000`
- A modern browser such as Chrome, Edge, Firefox, or Safari

Official Next.js system requirements: https://nextjs.org/docs/app/getting-started/installation

If the existing frontend project is pinned to an older Next.js version, follow the Node.js requirement from that project's `package.json`/lockfile instead of changing versions just for this README.

## Install dependencies

From the frontend folder:

### npm

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\frontend
npm install
```

### pnpm

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\frontend
pnpm install
```

### yarn

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\frontend
yarn install
```

### bun

```cmd
cd C:\Users\edwin\Downloads\youtube-downloader\frontend
bun install
```

Use only one package manager for the project.

## Configure the backend URL

Create/update the frontend environment file according to the existing project convention. A typical local setting is:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Do not hardcode `http://localhost:5000` in multiple React components.

## Start the frontend

With the backend already running:

```cmd
npm run dev
```

Open:

```text
http://localhost:3000
```

For pnpm/yarn/bun, run the equivalent `dev` script:

```cmd
pnpm dev
yarn dev
bun dev
```

## Frontend ↔ backend flow

For URL downloads, use the asynchronous backend API:

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
Display progress, speed, ETA, and phase
      ↓
Optional POST /api/download/cancel/{job_id}
      ↓
completed
      ↓
GET /api/download/file/{job_id}
      ↓
Browser saves file using server filename
```

### Progress states

Map backend statuses to the UI:

```text
queued      → Queued
downloading → Downloading
processing  → Processing
completed   → Completed
cancelled   → Cancelled
failed      → Failed
```

### Polling

Poll approximately every 500–1000 ms while the job is active.

Stop polling immediately when the job reaches:

```text
completed
cancelled
failed
```

Clear timers on component unmount and when a new job replaces an old job.

## Resolution selector

Only show the resolution selector for MP4.

User-facing values:

```text
Highest
Medium
Lowest
```

Backend values:

```text
Highest → highest
Medium  → medium
Lowest  → lowest
```

Do not expose raw yt-dlp format IDs.

The backend returns:

```json
{
  "requested_resolution": "medium",
  "effective_resolution": 480,
  "selection_note": "720p is not available; using the closest available resolution: 480p."
}
```

Show a non-blocking fallback message when `selection_note` is present.

## Cancel Download

The active download UI should provide a clear **Cancel Download** button.

When clicked:

1. Disable duplicate clicks.
2. Call `POST /api/download/cancel/{job_id}`.
3. Change the button state to `Cancelling...`.
4. Continue polling.
5. When the backend reports `cancelled`, stop polling.
6. Do not show a generic error for a user-initiated cancellation.
7. Re-enable the controls so another download can start.

## Filename preservation

This is important because downloading the completed Blob without using the response filename can produce a browser filename such as `download`.

When calling:

```http
GET /api/download/file/{job_id}
```

retrieve the filename from the response headers, preferably `Content-Disposition` and, when needed, the exposed `X-Download-Filename` header.

Example approach:

```ts
const response = await fetch(fileUrl);
const blob = await response.blob();

const headerName = response.headers.get("X-Download-Filename");
// Otherwise parse Content-Disposition.

const a = document.createElement("a");
a.href = URL.createObjectURL(blob);
a.download = headerName ?? "media-download";
a.click();
URL.revokeObjectURL(a.href);
```

The actual frontend should use its existing API/download abstraction if one already exists rather than duplicating this logic across components.

## Preserve existing architecture

This frontend was intended to be an incremental modification of the existing v0.dev-generated application.

Do not:

- rebuild the app from scratch
- replace the routing structure unnecessarily
- introduce a second global state system without a real need
- duplicate the API base URL
- remove the existing local conversion flow
- break responsive behavior
- replace the established visual design just to add the new functionality

Prefer extending an existing hook/service/download component.

## Accessibility

The progress bar should use appropriate semantics such as:

```text
role="progressbar"
aria-valuemin="0"
aria-valuemax="100"
aria-valuenow="..."
```

The Cancel button must have a clear accessible name, and status changes should be perceivable by screen readers where practical.

## Development checks

Before considering a frontend change complete:

1. Start the backend.
2. Start the frontend.
3. Test MP3 URL download.
4. Test MP4 Highest.
5. Test MP4 Medium.
6. Test MP4 Lowest.
7. Test a source where the requested resolution is not available.
8. Confirm progress does not run backwards.
9. Cancel during active downloading.
10. Confirm completed file keeps the real media title instead of the generic name `download`.
11. Test local video → MP3 upload.

## Troubleshooting

### Frontend cannot connect to Flask

Verify:

```text
http://localhost:5000/api/health
```

Then check the frontend environment variable:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### CORS error

Verify the backend has:

```env
FRONTEND_URL=http://localhost:3000
```

Restart Flask after changing `.env`.

### Browser downloads a file named `download`

Check that the frontend reads `Content-Disposition` or `X-Download-Filename` from the completed-file response and assigns the actual name to the download anchor.

### Progress keeps polling after the download finishes

Make sure the polling timer is cleared for all terminal states:

```text
completed
cancelled
failed
```

Also clear it during React component cleanup.

## Production note

`npm run dev` is for local development. For a production deployment use the frontend project's configured production build and start scripts.

Typical Next.js commands are:

```cmd
npm run build
npm run start
```

For current Next.js documentation, see: https://nextjs.org/docs/app/getting-started/installation
