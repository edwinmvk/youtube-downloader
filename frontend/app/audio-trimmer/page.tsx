'use client'

import { ChangeEvent, KeyboardEvent, PointerEvent, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, CheckCircle2, Clock3, Download, FileAudio, Loader2, Music2, UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { trimAudio } from '@/lib/api'
import { downloadResponse, formatFileSize } from '@/lib/download'
import { ACCEPTED_AUDIO_EXTENSIONS, MAX_FILE_SIZE, validateAudioFile } from '@/lib/validation'

const MIN_SELECTION_SECONDS = 0.1

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00.0'
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  return `${minutes}:${remainder.toFixed(1).padStart(4, '0')}`
}

function getStep(duration: number) {
  return duration > 0 && duration < 0.1 ? 0.001 : duration < 1 ? 0.01 : 0.1
}

function DualRange({
  duration,
  start,
  end,
  onStartChange,
  onEndChange,
}: {
  duration: number
  start: number
  end: number
  onStartChange: (value: number) => void
  onEndChange: (value: number) => void
}) {
  const trackRef = useRef<HTMLDivElement>(null)
  const [activeThumb, setActiveThumb] = useState<'start' | 'end' | null>(null)
  const step = getStep(duration)
  const gap = Math.min(MIN_SELECTION_SECONDS, duration / 2)
  const safeStart = clamp(start, 0, Math.max(0, duration - gap))
  const safeEnd = clamp(end, Math.min(duration, gap), duration)
  const startPercent = duration > 0 ? (safeStart / duration) * 100 : 0
  const endPercent = duration > 0 ? (safeEnd / duration) * 100 : 100

  const valueFromPointer = (clientX: number) => {
    const track = trackRef.current
    if (!track || duration <= 0) return null
    const rect = track.getBoundingClientRect()
    if (rect.width <= 0) return null
    const ratio = clamp((clientX - rect.left) / rect.width, 0, 1)
    const raw = ratio * duration
    const stepped = Math.round(raw / step) * step
    return clamp(Number(stepped.toFixed(4)), 0, duration)
  }

  const updateFromPointer = (clientX: number, thumb: 'start' | 'end') => {
    const value = valueFromPointer(clientX)
    if (value === null) return
    if (thumb === 'start') {
      onStartChange(clamp(value, 0, Math.max(0, safeEnd - gap)))
    } else {
      onEndChange(clamp(value, Math.min(duration, safeStart + gap), duration))
    }
  }

  const beginPointerDrag = (event: PointerEvent<HTMLButtonElement>, thumb: 'start' | 'end') => {
    if (!duration) return
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    setActiveThumb(thumb)
    updateFromPointer(event.clientX, thumb)
  }

  const continuePointerDrag = (event: PointerEvent<HTMLButtonElement>, thumb: 'start' | 'end') => {
    if (activeThumb !== thumb || !event.currentTarget.hasPointerCapture(event.pointerId)) return
    event.preventDefault()
    updateFromPointer(event.clientX, thumb)
  }

  const finishPointerDrag = (event: PointerEvent<HTMLButtonElement>, thumb: 'start' | 'end') => {
    if (activeThumb !== thumb) return
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
    setActiveThumb(null)
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, thumb: 'start' | 'end') => {
    if (!duration) return
    const current = thumb === 'start' ? safeStart : safeEnd
    const minimum = thumb === 'start' ? 0 : Math.min(duration, safeStart + gap)
    const maximum = thumb === 'start' ? Math.max(0, safeEnd - gap) : duration
    const largeStep = Math.max(step, duration / 10)
    let next = current

    switch (event.key) {
      case 'ArrowLeft':
      case 'ArrowDown':
        next = current - step
        break
      case 'ArrowRight':
      case 'ArrowUp':
        next = current + step
        break
      case 'PageDown':
        next = current - largeStep
        break
      case 'PageUp':
        next = current + largeStep
        break
      case 'Home':
        next = minimum
        break
      case 'End':
        next = maximum
        break
      default:
        return
    }

    event.preventDefault()
    const bounded = clamp(next, minimum, maximum)
    if (thumb === 'start') onStartChange(bounded)
    else onEndChange(bounded)
  }

  return (
    <div className="dual-range" aria-label="Audio trim range">
      <div ref={trackRef} className="dual-range-track" aria-hidden="true" />
      <div
        className="dual-range-selection"
        aria-hidden="true"
        style={{ left: `${startPercent}%`, width: `${Math.max(0, endPercent - startPercent)}%` }}
      />
      <button
        type="button"
        className={`dual-range-thumb ${activeThumb === 'start' ? 'dual-range-thumb-active' : ''}`}
        style={{ left: `${startPercent}%`, zIndex: activeThumb === 'start' ? 10 : 4 }}
        onPointerDown={(event) => beginPointerDrag(event, 'start')}
        onPointerMove={(event) => continuePointerDrag(event, 'start')}
        onPointerUp={(event) => finishPointerDrag(event, 'start')}
        onPointerCancel={(event) => finishPointerDrag(event, 'start')}
        onKeyDown={(event) => handleKeyDown(event, 'start')}
        disabled={!duration}
        role="slider"
        aria-label={`Trim start, ${formatTime(safeStart)}`}
        aria-valuemin={0}
        aria-valuemax={Math.max(0, safeEnd - gap)}
        aria-valuenow={safeStart}
        aria-valuetext={formatTime(safeStart)}
      />
      <button
        type="button"
        className={`dual-range-thumb ${activeThumb === 'end' ? 'dual-range-thumb-active' : ''}`}
        style={{ left: `${endPercent}%`, zIndex: activeThumb === 'end' ? 10 : 5 }}
        onPointerDown={(event) => beginPointerDrag(event, 'end')}
        onPointerMove={(event) => continuePointerDrag(event, 'end')}
        onPointerUp={(event) => finishPointerDrag(event, 'end')}
        onPointerCancel={(event) => finishPointerDrag(event, 'end')}
        onKeyDown={(event) => handleKeyDown(event, 'end')}
        disabled={!duration}
        role="slider"
        aria-label={`Trim end, ${formatTime(safeEnd)}`}
        aria-valuemin={Math.min(duration, safeStart + gap)}
        aria-valuemax={duration}
        aria-valuenow={safeEnd}
        aria-valuetext={formatTime(safeEnd)}
      />
      <div className="dual-range-labels" aria-hidden="true">
        <span>0:00</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  )
}

export default function AudioTrimmerPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [objectUrl, setObjectUrl] = useState('')
  const [duration, setDuration] = useState(0)
  const [start, setStart] = useState(0)
  const [end, setEnd] = useState(0)
  const [previewing, setPreviewing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [downloaded, setDownloaded] = useState(false)

  const step = useMemo(() => getStep(duration), [duration])
  const minGap = Math.min(MIN_SELECTION_SECONDS, duration / 2)

  useEffect(() => {
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [objectUrl])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    const onTimeUpdate = () => {
      if (previewing && audio.currentTime >= end) {
        audio.pause()
        audio.currentTime = start
        setPreviewing(false)
      }
    }
    audio.addEventListener('timeupdate', onTimeUpdate)
    return () => audio.removeEventListener('timeupdate', onTimeUpdate)
  }, [previewing, start, end])

  function selectFile(selected: File | undefined) {
    if (!selected) return
    const validation = validateAudioFile(selected)
    if (validation) {
      setError(validation)
      return
    }
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    const url = URL.createObjectURL(selected)
    setFile(selected)
    setObjectUrl(url)
    setDuration(0)
    setStart(0)
    setEnd(0)
    setPreviewing(false)
    setDownloaded(false)
    setError('')
  }

  function onLoadedMetadata(event: ChangeEvent<HTMLAudioElement>) {
    const nextDuration = event.currentTarget.duration
    if (!Number.isFinite(nextDuration) || nextDuration <= 0) {
      setError('Unable to read the duration of this audio file.')
      return
    }
    setDuration(nextDuration)
    setStart(0)
    setEnd(nextDuration)
  }

  function updateStart(value: number) {
    if (!Number.isFinite(value) || duration <= 0) return
    const maxStart = Math.max(0, end - minGap)
    setStart(clamp(value, 0, maxStart))
  }

  function updateEnd(value: number) {
    if (!Number.isFinite(value) || duration <= 0) return
    const minEnd = Math.min(duration, start + minGap)
    setEnd(clamp(value, minEnd, duration))
  }

  async function previewSelection() {
    const audio = audioRef.current
    if (!audio || !file || duration <= 0 || end <= start) return
    if (previewing) {
      audio.pause()
      audio.currentTime = start
      setPreviewing(false)
      return
    }
    audio.currentTime = start
    try {
      await audio.play()
      setPreviewing(true)
    } catch {
      setError('The browser could not start audio playback.')
    }
  }

  async function trim() {
    if (!file || loading || duration <= 0 || end <= start || end - start < minGap) return
    setLoading(true)
    setError('')
    try {
      const response = await trimAudio(file, start, end)
      await downloadResponse(response, `${file.name.replace(/\.[^.]+$/, '')} - trimmed.mp3`)
      setDownloaded(true)
      dialogRef.current?.showModal()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to trim the audio.')
    } finally {
      setLoading(false)
    }
  }

  function restart() {
    audioRef.current?.pause()
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    setFile(null)
    setObjectUrl('')
    setDuration(0)
    setStart(0)
    setEnd(0)
    setPreviewing(false)
    setDownloaded(false)
    setError('')
    dialogRef.current?.close()
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.12),transparent_34rem),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.1),transparent_32rem)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
        <Button variant="ghost" render={<a href="/" />}><ArrowLeft /> Back</Button>
        <div className="flex items-center gap-2 text-sm font-semibold"><Music2 className="size-4 text-primary" /> Audio Trimmer</div>
        <div className="w-16" />
      </header>

      <div className="mx-auto max-w-4xl px-5 pb-16 pt-8 sm:px-8 sm:pt-14">
        <div className="mx-auto max-w-2xl text-center">
          <div className="eyebrow"><Clock3 /> Precise audio editing</div>
          <h1 className="mt-5 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">Trim your audio exactly where you want it.</h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-muted-foreground">Choose one audio file, set the start and end points on one range slider, preview the selected section, and download the trimmed MP3.</p>
        </div>

        <section className="surface-card mt-10 p-6 sm:p-8">
          {!file ? (
            <div
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]) }}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click() }}
              className="dropzone min-h-72"
            >
              <input ref={inputRef} type="file" className="sr-only" accept={ACCEPTED_AUDIO_EXTENSIONS.map((item) => `.${item}`).join(',')} onChange={(event) => { selectFile(event.target.files?.[0]); event.target.value = '' }} />
              <UploadCloud className="mb-4 text-primary" />
              <p className="text-lg font-semibold">Drop an audio file here</p>
              <p className="mt-2 text-sm text-muted-foreground">or <span className="font-medium text-primary">choose a file</span></p>
              <p className="mt-4 text-xs text-muted-foreground">MP3, WAV, M4A, AAC, FLAC, OGG, OPUS or WEBM · Up to {MAX_FILE_SIZE / 1024 / 1024} MB</p>
            </div>
          ) : (
            <div className="space-y-7">
              <div className="flex flex-col gap-4 rounded-2xl border border-border bg-muted/30 p-4 sm:flex-row sm:items-center">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary"><FileAudio /></div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold" title={file.name}>{file.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{formatFileSize(file.size)} · {duration ? `${duration.toFixed(1)} seconds` : 'Reading duration...'}</p>
                </div>
                <Button variant="outline" onClick={() => { restart(); window.setTimeout(() => inputRef.current?.click(), 0) }}>Choose another</Button>
              </div>

              <audio ref={audioRef} src={objectUrl} controls className="w-full" onLoadedMetadata={onLoadedMetadata} onPlay={() => setPreviewing(true)} onPause={() => setPreviewing(false)} />

              <div className="rounded-2xl border border-border bg-background p-5 sm:p-6">
                <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-semibold">Trim range</p>
                    <p className="text-sm text-muted-foreground">Drag either handle. The highlighted section will be kept.</p>
                  </div>
                  <Button variant="outline" onClick={previewSelection} disabled={!duration}>{previewing ? 'Stop preview' : 'Preview selection'}</Button>
                </div>

                <DualRange duration={duration} start={start} end={end} onStartChange={updateStart} onEndChange={updateEnd} />

                <div className="mt-7 grid grid-cols-2 gap-3">
                  <label className="text-sm">
                    <span className="mb-2 block text-muted-foreground">Start time</span>
                    <input className="control w-full" type="number" min="0" max={Math.max(0, end - minGap)} step={step} value={start.toFixed(duration < 0.1 ? 3 : duration < 1 ? 2 : 1)} onChange={(event) => updateStart(Number(event.target.value))} disabled={!duration} />
                  </label>
                  <label className="text-sm">
                    <span className="mb-2 block text-muted-foreground">End time</span>
                    <input className="control w-full" type="number" min={Math.min(duration, start + minGap)} max={duration} step={step} value={end.toFixed(duration < 0.1 ? 3 : duration < 1 ? 2 : 1)} onChange={(event) => updateEnd(Number(event.target.value))} disabled={!duration} />
                  </label>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                  <span>Selected: <strong className="font-mono text-foreground">{formatTime(Math.max(0, end - start))}</strong></span>
                  <span>From <strong className="font-mono text-foreground">{formatTime(start)}</strong> to <strong className="font-mono text-foreground">{formatTime(end)}</strong></span>
                </div>
              </div>

              {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

              <Button className="h-12 w-full text-sm font-semibold" size="lg" disabled={loading || !duration || end <= start || end - start < minGap} onClick={trim}>
                {loading ? <><Loader2 className="animate-spin" /> Processing audio...</> : <><Download /> Download trimmed MP3</>}
              </Button>

              {downloaded && <p className="flex items-center justify-center gap-2 text-xs text-muted-foreground"><CheckCircle2 className="size-4 text-emerald-500" /> Your trimmed MP3 has been downloaded.</p>}
            </div>
          )}
        </section>
      </div>

      <dialog ref={dialogRef} className="m-auto w-[min(92vw,30rem)] rounded-2xl border border-border bg-background p-0 text-foreground shadow-2xl backdrop:bg-black/50">
        <div className="p-6">
          <div className="flex size-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600"><CheckCircle2 /></div>
          <h2 className="mt-4 text-xl font-semibold">Trim downloaded</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">Your trimmed MP3 is ready. Continue with this audio or start with a new song.</p>
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => dialogRef.current?.close()}>Continue editing</Button>
            <Button onClick={restart}>New song</Button>
          </div>
        </div>
      </dialog>
    </main>
  )
}
