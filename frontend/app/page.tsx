'use client'

import { ChangeEvent, DragEvent, FormEvent, useEffect, useRef, useState } from 'react'
import { CheckCircle2, Download, FileAudio, FileVideo, FolderOpen, Link2, Loader2, Music2, ShieldCheck, UploadCloud, X, Zap } from 'lucide-react'
import { checkBackendHealth, convertVideoToMp3, downloadFromUrl, type MediaFormat } from '@/lib/api'
import { downloadResponse, formatFileSize } from '@/lib/download'
import { ACCEPTED_EXTENSIONS, MAX_FILE_SIZE, validateMediaUrl, validateVideoFile } from '@/lib/validation'

function BackendStatus() {
  const [connected, setConnected] = useState<boolean | null>(null)
  useEffect(() => { checkBackendHealth().then(setConnected).catch(() => setConnected(false)) }, [])
  return <div className="flex items-center gap-2 rounded-full border border-border bg-card/70 px-3 py-1.5 text-xs text-muted-foreground"><span className={`size-2 rounded-full ${connected ? 'bg-emerald-500' : connected === false ? 'bg-rose-500' : 'bg-amber-400'}`} />{connected ? 'Backend connected' : connected === false ? 'Backend unavailable' : 'Checking backend'}</div>
}

function UrlDownloader({ notify }: { notify: (message: string, error?: boolean) => void }) {
  const [url, setUrl] = useState('')
  const [format, setFormat] = useState<MediaFormat>('mp3')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    const validation = validateMediaUrl(url)
    setError(validation)
    if (validation) return
    setLoading(true)
    try { const response = await downloadFromUrl(url.trim(), format); await downloadResponse(response, `download.${format}`); notify('Download completed successfully.') } catch (caught) { notify(caught instanceof Error ? caught.message : 'Download failed. Please try again.', true) } finally { setLoading(false) }
  }
  return <section className="surface-card flex flex-col gap-6 p-6 sm:p-8"><div className="flex items-start gap-4"><div className="icon-tile"><Link2 /></div><div><h2 className="text-xl font-semibold tracking-tight">Download from URL</h2><p className="mt-1 text-sm text-muted-foreground">Grab audio or video from a supported link.</p></div></div><form onSubmit={submit} className="flex flex-col gap-5"><div className="flex flex-col gap-2"><label htmlFor="video-url" className="text-sm font-medium">Video URL</label><input id="video-url" value={url} onChange={(event) => { setUrl(event.target.value); if (error) setError('') }} placeholder="Paste a YouTube or supported video URL" aria-invalid={Boolean(error)} aria-describedby={error ? 'url-error' : undefined} className="control" />{error && <p id="url-error" className="text-sm text-destructive">{error}</p>}</div><div className="flex flex-col gap-2"><label htmlFor="format" className="text-sm font-medium">Format</label><select id="format" value={format} onChange={(event) => setFormat(event.target.value as MediaFormat)} className="control"><option value="mp3">MP3 Audio</option><option value="mp4">MP4 Video</option></select></div><button className="primary-button" disabled={loading}>{loading ? <><Loader2 className="animate-spin" /> Downloading...</> : <><Download /> Download</>}</button></form></section>
}

function VideoConverter({ notify }: { notify: (message: string, error?: boolean) => void }) {
  const inputRef = useRef<HTMLInputElement>(null); const [file, setFile] = useState<File | null>(null); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  function choose(candidate?: File) { if (!candidate) return; const validation = validateVideoFile(candidate); setError(validation); if (!validation) setFile(candidate) }
  function onDrop(event: DragEvent<HTMLDivElement>) { event.preventDefault(); choose(event.dataTransfer.files[0]) }
  async function convert() { if (!file) return; setLoading(true); try { const response = await convertVideoToMp3(file); await downloadResponse(response, `${file.name.replace(/\.[^.]+$/, '')}.mp3`); notify('Video converted to MP3 successfully.'); setFile(null) } catch (caught) { notify(caught instanceof Error ? caught.message : 'Conversion failed. Please try again.', true) } finally { setLoading(false) } }
  return <section className="surface-card flex flex-col gap-6 p-6 sm:p-8"><div className="flex items-start gap-4"><div className="icon-tile"><Music2 /></div><div><h2 className="text-xl font-semibold tracking-tight">Convert Video to MP3</h2><p className="mt-1 text-sm text-muted-foreground">Turn a local video into an audio file.</p></div></div><div onDragOver={(event) => event.preventDefault()} onDrop={onDrop} onClick={() => inputRef.current?.click()} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click() }} role="button" tabIndex={0} className="dropzone"><input ref={inputRef} type="file" className="sr-only" accept={ACCEPTED_EXTENSIONS.map((item) => `.${item}`).join(',')} onChange={(event: ChangeEvent<HTMLInputElement>) => choose(event.target.files?.[0])} /><UploadCloud className="mb-3 text-primary" /><p className="font-medium">Drag & drop your video here</p><p className="my-2 text-sm text-muted-foreground">or <span className="font-medium text-primary">Choose File</span></p><p className="text-xs text-muted-foreground">MP4, MOV, MKV, AVI, WEBM · Up to {MAX_FILE_SIZE / 1024 / 1024} MB</p></div>{error && <p className="text-sm text-destructive">{error}</p>}{file && <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/40 p-3"><div className="rounded-lg bg-background p-2"><FileVideo className="text-primary" /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{file.name}</p><p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p></div><button type="button" aria-label="Remove selected file" onClick={() => setFile(null)} className="icon-button"><X /></button></div>}{file && <button className="primary-button" disabled={loading} onClick={convert}>{loading ? <><Loader2 className="animate-spin" /> Converting...</> : <><FileAudio /> Convert to MP3</>}</button>}</section>
}

export default function Page() {
  const [notice, setNotice] = useState<{ message: string; error?: boolean } | null>(null)
  function notify(message: string, error = false) { setNotice({ message, error }); window.setTimeout(() => setNotice(null), 5000) }
  return <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.12),transparent_34rem),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.1),transparent_32rem)]"><header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6 sm:px-8"><div className="flex items-center gap-3"><div className="brand-mark"><Zap /></div><span className="font-semibold tracking-tight">Media Downloader</span></div><BackendStatus /></header><div className="mx-auto max-w-6xl px-5 pb-12 pt-10 sm:px-8 sm:pt-16"><div className="mx-auto max-w-2xl text-center"><div className="eyebrow"><ShieldCheck /> Simple, fast, and private</div><h1 className="mt-5 text-4xl font-semibold tracking-[-0.04em] sm:text-6xl">Media, in the format you need.</h1><p className="mx-auto mt-5 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">Download audio, download video, or convert your local videos to MP3.</p></div><div className="mx-auto mt-12 grid max-w-5xl gap-5 lg:grid-cols-2"><UrlDownloader notify={notify} /><VideoConverter notify={notify} /></div><p className="mx-auto mt-8 flex max-w-xl items-center justify-center gap-2 text-center text-xs text-muted-foreground"><ShieldCheck /> Only download or convert media you have permission to use.</p></div>{notice && <div role="status" className={`toast ${notice.error ? 'toast-error' : ''}`}><CheckCircle2 />{notice.message}</div>}</main>
}
