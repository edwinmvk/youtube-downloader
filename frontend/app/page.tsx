'use client'

import { FormEvent, useEffect, useRef, useState } from 'react'
import { CheckCircle2, Download, FileAudio, Link2, Loader2, Music2, ShieldCheck, Zap } from 'lucide-react'
import { cancelDownload, checkBackendHealth, getDownloadFile, getDownloadProgress, startDownload, type DownloadProgressResponse, type MediaFormat, type Resolution } from '@/lib/api'
import { downloadResponse, formatEta, formatFileSize, formatSpeed } from '@/lib/download'
import { validateMediaUrl } from '@/lib/validation'
import { Button } from '@/components/ui/button'

function BackendStatus() {
  const [connected, setConnected] = useState<boolean | null>(null)
  useEffect(() => { checkBackendHealth().then(setConnected).catch(() => setConnected(false)) }, [])
  return <div className="flex items-center gap-2 rounded-full border border-border bg-card/70 px-3 py-1.5 text-xs text-muted-foreground"><span className={`size-2 rounded-full ${connected ? 'bg-emerald-500' : connected === false ? 'bg-rose-500' : 'bg-amber-400'}`} />{connected ? 'Backend connected' : connected === false ? 'Backend unavailable' : 'Checking backend'}</div>
}

function UrlDownloader({ notify }: { notify: (message: string, error?: boolean) => void }) {
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState<MediaFormat>('mp3')
  const [resolution, setResolution] = useState<Resolution>('highest')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState<DownloadProgressResponse | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const timerRef = useRef<number | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const activeJobRef = useRef<string | null>(null)

  function clearPolling() { if (timerRef.current !== null) { window.clearTimeout(timerRef.current); timerRef.current = null } controllerRef.current?.abort(); controllerRef.current = null }
  useEffect(() => () => clearPolling(), [])
  function phaseLabel(phase?: string, status?: string) { const value = phase || status || 'queued'; return value.charAt(0).toUpperCase() + value.slice(1) }
  async function poll(id: string) {
    if (activeJobRef.current !== id) return
    try {
      const next = await getDownloadProgress(id)
      if (activeJobRef.current !== id) return
      setProgress(next)
      if (next.status === 'completed') {
        clearPolling(); const response = await getDownloadFile(id); await downloadResponse(response, `media.${format}`); setJobId(null); setCancelling(false); notify('Download completed successfully.'); return
      }
      if (next.status === 'failed') { clearPolling(); setJobId(null); setCancelling(false); notify(next.error || 'Download failed. Please try again.', true); return }
      if (next.status === 'cancelled') { clearPolling(); setJobId(null); setCancelling(false); return }
      timerRef.current = window.setTimeout(() => poll(id), 700)
    } catch (caught) { if (activeJobRef.current === id) { clearPolling(); setJobId(null); setCancelling(false); notify(caught instanceof Error ? caught.message : 'Unable to check download progress.', true) } }
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); const validation = validateMediaUrl(url); setError(validation); if (validation || jobId) return
    clearPolling(); setProgress(null); setCancelling(false); const controller = new AbortController(); controllerRef.current = controller
    try { const started = await startDownload({ url: url.trim(), format, ...(format === 'mp4' ? { resolution } : {}) }, controller.signal); activeJobRef.current = started.job_id; setJobId(started.job_id); await poll(started.job_id) } catch (caught) { if (!controller.signal.aborted) notify(caught instanceof Error ? caught.message : 'Download failed. Please try again.', true) }
  }
  async function handleCancel() { if (!jobId || cancelling) return; setCancelling(true); try { await cancelDownload(jobId); } catch (caught) { setCancelling(false); notify(caught instanceof Error ? caught.message : 'Unable to cancel download.', true) } }
  const active = Boolean(jobId)
  const percent = Math.max(0, Math.min(100, progress?.progress ?? 0))
  return <section className="surface-card flex flex-col gap-6 p-6 sm:p-8"><div className="flex items-start gap-4"><div className="icon-tile"><Link2 /></div><div><h2 className="text-xl font-semibold tracking-tight">Download from URL</h2><p className="mt-1 text-sm text-muted-foreground">Grab audio or video from a supported link.</p></div></div><form onSubmit={submit} className="flex flex-col gap-5"><div className="flex flex-col gap-2"><label htmlFor="video-url" className="text-sm font-medium">Video URL</label><input id="video-url" value={url} disabled={active} onChange={(event) => { setUrl(event.target.value); if (error) setError('') }} placeholder="Paste a YouTube or supported video URL" aria-invalid={Boolean(error)} aria-describedby={error ? 'url-error' : undefined} className="control" />{error && <p id="url-error" className="text-sm text-destructive">{error}</p>}</div><div className="flex flex-col gap-2"><label htmlFor="format" className="text-sm font-medium">Format</label><select id="format" value={format} disabled={active} onChange={(event) => setFormat(event.target.value as MediaFormat)} className="control"><option value="mp3">MP3 Audio</option><option value="mp4">MP4 Video</option></select></div>{format === 'mp4' && <div className="flex flex-col gap-2"><label htmlFor="resolution" className="text-sm font-medium">Video quality</label><select id="resolution" value={resolution} disabled={active} onChange={(event) => setResolution(event.target.value as Resolution)} className="control"><option value="highest">Highest</option><option value="medium">Medium</option><option value="lowest">Lowest</option></select></div>}<button className="primary-button" disabled={active}>{active ? <><Loader2 className="animate-spin" /> Downloading...</> : <><Download /> Download</>}</button></form>{progress && active && <div className="flex flex-col gap-3" aria-live="polite"><div className="flex items-center justify-between text-sm font-medium"><span>{phaseLabel(progress.phase, progress.status)}</span><span>{progress.status === 'processing' ? 'Finalizing file' : `${percent.toFixed(1)}%`}</span></div><div role="progressbar" aria-label="Download progress" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent}%` }} /></div>{progress.status === 'processing' && <p className="text-xs text-muted-foreground">Processing media...</p>}{progress.selection_note && progress.effective_resolution && <p className="text-xs text-muted-foreground">Using {progress.effective_resolution}p because the requested quality was not available.</p>}<div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">{progress.downloaded_bytes && progress.total_bytes ? <span>{formatFileSize(progress.downloaded_bytes)} / {formatFileSize(progress.total_bytes)}</span> : null}{progress.speed_bytes_per_second ? <span>{formatSpeed(progress.speed_bytes_per_second)}</span> : null}{progress.eta_seconds ? <span>{formatEta(progress.eta_seconds)}</span> : null}</div><button type="button" className="secondary-button" disabled={cancelling} onClick={handleCancel}>{cancelling ? 'Cancelling...' : 'Cancel Download'}</button></div>}</section>
}

export default function Page() {
  const [notice, setNotice] = useState<{ message: string; error?: boolean } | null>(null)
  function notify(message: string, error = false) {
    setNotice({ message, error })
    window.setTimeout(() => setNotice(null), 5000)
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.14),transparent_34rem),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.12),transparent_32rem)]">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <a href="/" className="flex items-center gap-3">
            <div className="brand-mark"><Zap /></div>
            <div>
              <p className="font-semibold tracking-tight">Media Downloader</p>
              <p className="hidden text-[11px] text-muted-foreground sm:block">Download · Convert · Edit</p>
            </div>
          </a>
          <div className="flex items-center gap-2">
            <nav className="hidden items-center gap-1 md:flex">
              <Button variant="ghost" size="sm" render={<a href="/audio-trimmer" />}>Audio Trimmer</Button>
              <Button variant="ghost" size="sm" render={<a href="/audio-merger" />}>Audio Merger</Button>
              <Button variant="ghost" size="sm" render={<a href="/video-to-mp3" />}>Video to MP3</Button>
            </nav>
            <BackendStatus />
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 pb-16 pt-10 sm:px-8 sm:pt-16">
        <div className="mx-auto max-w-3xl text-center">
          <div className="eyebrow"><ShieldCheck /> Fast, focused media tools</div>
          <h1 className="mt-5 text-4xl font-semibold tracking-[-0.045em] sm:text-6xl">One place for your everyday media tasks.</h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">Download media, convert local videos to MP3, trim audio precisely, or merge multiple tracks into one.</p>
        </div>

        <div className="mx-auto mt-10 grid max-w-5xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <a href="#download" className="rounded-2xl border border-border/70 bg-card/70 p-4 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg">
            <Link2 className="size-5 text-primary" />
            <p className="mt-3 font-semibold">Download media</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">YouTube URL to MP3 or MP4 with quality controls.</p>
          </a>
          <a href="/video-to-mp3" className="rounded-2xl border border-border/70 bg-card/70 p-4 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg">
            <Music2 className="size-5 text-primary" />
            <p className="mt-3 font-semibold">Video to MP3</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">Convert up to 10 local videos to MP3.</p>
          </a>
          <a href="/audio-trimmer" className="rounded-2xl border border-border/70 bg-card/70 p-4 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg">
            <Music2 className="size-5 text-primary" />
            <p className="mt-3 font-semibold">Trim audio</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">Preview a range and export the exact section you need.</p>
          </a>
          <a href="/audio-merger" className="rounded-2xl border border-border/70 bg-card/70 p-4 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg">
            <FileAudio className="size-5 text-primary" />
            <p className="mt-3 font-semibold">Merge audio</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">Arrange up to 10 tracks and combine them into one MP3.</p>
          </a>
        </div>

        <div id="download" className="mx-auto mt-8 max-w-5xl">
          <UrlDownloader notify={notify} />
        </div>

        <div className="mx-auto mt-10 flex max-w-3xl flex-wrap items-center justify-center gap-2 text-center text-xs text-muted-foreground">
          <span className="rounded-full border border-border bg-background/70 px-3 py-1.5">Unicode-safe filenames</span>
          <span className="rounded-full border border-border bg-background/70 px-3 py-1.5">Up to 10-file batch conversion</span>
          <span className="rounded-full border border-border bg-background/70 px-3 py-1.5">FFmpeg powered</span>
        </div>

        <p className="mx-auto mt-6 flex max-w-xl items-center justify-center gap-2 text-center text-xs text-muted-foreground"><ShieldCheck /> Only download or convert media you have permission to use.</p>
      </div>

      {notice && <div role="status" className={`toast ${notice.error ? 'toast-error' : ''}`}><CheckCircle2 />{notice.message}</div>}
    </main>
  )
}
