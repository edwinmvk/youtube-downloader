'use client'

import { ChangeEvent, DragEvent, useRef, useState } from 'react'
import { ArrowLeft, CheckCircle2, FileAudio, FileVideo, Loader2, Music2, UploadCloud, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { convertVideosToMp3 } from '@/lib/api'
import { downloadResponse, formatFileSize } from '@/lib/download'
import { ACCEPTED_EXTENSIONS, MAX_FILE_SIZE, validateVideoFile } from '@/lib/validation'

const MAX_FILES = 10

export default function VideoToMp3Page() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [completed, setCompleted] = useState(false)

  function addFiles(candidates: File[]) {
    if (!candidates.length || loading) return
    setError('')
    const remaining = MAX_FILES - files.length
    if (candidates.length > remaining) {
      setError(`You can select a maximum of ${MAX_FILES} videos.`)
      return
    }
    const validation = candidates.map((file) => validateVideoFile(file)).find(Boolean)
    if (validation) {
      setError(validation)
      return
    }
    setFiles((current) => [...current, ...candidates])
    setCompleted(false)
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    addFiles(Array.from(event.dataTransfer.files))
  }

  function removeFile(index: number) {
    if (loading) return
    setFiles((current) => current.filter((_, fileIndex) => fileIndex !== index))
    setError('')
    setCompleted(false)
  }

  async function convert() {
    if (!files.length || loading) return
    setLoading(true)
    setError('')
    try {
      const response = await convertVideosToMp3(files)
      await downloadResponse(response, files.length === 1 ? `${files[0].name.replace(/\.[^.]+$/, '')}.mp3` : 'converted_audio.zip')
      setCompleted(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Conversion failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function newSet() {
    setFiles([])
    setError('')
    setCompleted(false)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.12),transparent_34rem),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.1),transparent_32rem)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
        <Button variant="ghost" render={<a href="/" />}><ArrowLeft /> Back</Button>
        <div className="flex items-center gap-2 text-sm font-semibold"><Music2 className="size-4 text-primary" /> Convert Video to MP3</div>
        <div className="w-16" />
      </header>

      <div className="mx-auto max-w-4xl px-5 pb-16 pt-8 sm:px-8 sm:pt-14">
        <div className="mx-auto max-w-2xl text-center">
          <div className="eyebrow"><FileAudio /> Local video conversion</div>
          <h1 className="mt-5 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">Convert your videos to MP3.</h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-muted-foreground">Select up to 10 local video files. They are sent to the conversion backend, converted with FFmpeg, and returned as MP3 files.</p>
        </div>

        <section className="surface-card mt-10 p-6 sm:p-8">
          <div
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
            onClick={() => !loading && inputRef.current?.click()}
            onKeyDown={(event) => { if (!loading && (event.key === 'Enter' || event.key === ' ')) inputRef.current?.click() }}
            role="button"
            tabIndex={loading ? -1 : 0}
            className={`dropzone min-h-64 ${loading ? 'cursor-not-allowed opacity-70' : ''}`}
          >
            <input ref={inputRef} type="file" multiple className="sr-only" accept={ACCEPTED_EXTENSIONS.map((item) => `.${item}`).join(',')} onChange={(event: ChangeEvent<HTMLInputElement>) => { addFiles(Array.from(event.target.files ?? [])); event.target.value = '' }} />
            <UploadCloud className="mb-3 text-primary" />
            <p className="text-lg font-semibold">Drop your videos here</p>
            <p className="my-2 text-sm text-muted-foreground">or <span className="font-medium text-primary">choose files</span></p>
            <p className="text-xs text-muted-foreground">MP4, MOV, MKV, AVI, WEBM · Maximum {MAX_FILES} files · Up to {MAX_FILE_SIZE / 1024 / 1024} MB each</p>
          </div>

          {error && <p role="alert" className="mt-5 text-sm text-destructive">{error}</p>}

          {files.length > 0 && (
            <div className="mt-6 space-y-3" aria-live="polite">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold">Selected videos ({files.length} / {MAX_FILES})</p>
                <Button variant="ghost" size="sm" onClick={newSet} disabled={loading}>Clear all</Button>
              </div>
              {files.map((file, index) => (
                <div key={`${file.name}-${file.lastModified}-${index}`} className="flex items-center gap-3 rounded-xl border border-border bg-muted/40 p-3">
                  <div className="rounded-lg bg-background p-2"><FileVideo className="size-5 text-primary" /></div>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium" title={file.name}>{file.name}</p><p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p></div>
                  <button type="button" aria-label={`Remove ${file.name}`} onClick={() => removeFile(index)} className="icon-button" disabled={loading}><X /></button>
                </div>
              ))}
            </div>
          )}

          {files.length > 0 && (
            <Button className="mt-6 h-12 w-full text-sm font-semibold" size="lg" disabled={loading} onClick={convert}>
              {loading ? <><Loader2 className="animate-spin" /> Converting {files.length} video{files.length === 1 ? '' : 's'}...</> : <><FileAudio /> Convert to MP3</>}
            </Button>
          )}

          {completed && (
            <div className="mt-5 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm">
              <div className="flex items-start gap-3"><CheckCircle2 className="mt-0.5 size-5 shrink-0 text-emerald-600" /><div><p className="font-semibold">Conversion complete</p><p className="mt-1 text-muted-foreground">Your MP3 download has started. You can continue with the same files or start a new set.</p></div></div>
              <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end"><Button variant="outline" onClick={() => setCompleted(false)}>Continue editing</Button><Button onClick={newSet}>New set</Button></div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
