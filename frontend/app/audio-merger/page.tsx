'use client'

import { ChangeEvent, DragEvent, useLayoutEffect, useRef, useState } from 'react'
import { ArrowLeft, CheckCircle2, Download, FileAudio, Loader2, Music2, RotateCcw, Trash2, UploadCloud } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { mergeAudioFiles } from '@/lib/api'
import { downloadResponse, formatFileSize } from '@/lib/download'
import { ACCEPTED_AUDIO_EXTENSIONS, MAX_FILE_SIZE, validateAudioFile } from '@/lib/validation'

const fileIds = new WeakMap<File, string>()
let nextFileId = 0

function getFileId(file: File) {
  const existing = fileIds.get(file)
  if (existing) return existing
  const id = `audio-${++nextFileId}`
  fileIds.set(file, id)
  return id
}

export default function AudioMergerPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const dialogRef = useRef<HTMLDialogElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const itemRefs = useRef(new Map<string, HTMLDivElement>())
  const pendingReorderRects = useRef<Map<string, DOMRect> | null>(null)

  useLayoutEffect(() => {
    const firstRects = pendingReorderRects.current
    if (!firstRects) return
    pendingReorderRects.current = null

    requestAnimationFrame(() => {
      for (const [id, firstRect] of firstRects) {
        const element = itemRefs.current.get(id)
        if (!element) continue
        const lastRect = element.getBoundingClientRect()
        const deltaX = firstRect.left - lastRect.left
        const deltaY = firstRect.top - lastRect.top
        if (Math.abs(deltaX) < 0.5 && Math.abs(deltaY) < 0.5) continue

        element.animate(
          [
            { transform: `translate(${deltaX}px, ${deltaY}px)` },
            { transform: 'translate(0, 0)' },
          ],
          { duration: 240, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' },
        )
      }
    })
  }, [files])

  function addFiles(candidates: File[]) {
    setError('')
    if (files.length + candidates.length > 10) {
      setError('You can merge a maximum of 10 audio files at once.')
      return
    }
    for (const file of candidates) {
      const validation = validateAudioFile(file)
      if (validation) { setError(validation); return }
    }
    setFiles((current) => [...current, ...candidates])
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    addFiles(Array.from(event.dataTransfer.files))
  }

  function captureReorderRects() {
    const firstRects = new Map<string, DOMRect>()
    for (const file of files) {
      const id = getFileId(file)
      const element = itemRefs.current.get(id)
      if (element) firstRects.set(id, element.getBoundingClientRect())
    }
    pendingReorderRects.current = firstRects
  }

  function moveFileByOffset(fileId: string, offset: -1 | 1) {
    const from = files.findIndex((file) => getFileId(file) === fileId)
    const to = from + offset
    if (from < 0 || to < 0 || to >= files.length) return

    captureReorderRects()
    setFiles((current) => {
      const actualFrom = current.findIndex((file) => getFileId(file) === fileId)
      const actualTo = actualFrom + offset
      if (actualFrom < 0 || actualTo < 0 || actualTo >= current.length) return current
      const next = [...current]
      const [item] = next.splice(actualFrom, 1)
      next.splice(actualTo, 0, item)
      return next
    })
  }

  function removeFile(index: number) {
    setFiles((current) => current.filter((_, currentIndex) => currentIndex !== index))
    setError('')
  }

  async function merge() {
    if (files.length < 2 || loading) return
    setLoading(true)
    setError('')
    try {
      const response = await mergeAudioFiles(files)
      await downloadResponse(response, `${files[0].name.replace(/\.[^.]+$/, '')} - merged.mp3`)
      dialogRef.current?.showModal()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to merge the audio files.')
    } finally {
      setLoading(false)
    }
  }

  function restart() {
    setFiles([])
    setError('')
    dialogRef.current?.close()
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(99,102,241,0.12),transparent_34rem),radial-gradient(circle_at_bottom_right,rgba(20,184,166,0.1),transparent_32rem)]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-6 sm:px-8">
        <Button variant="ghost" render={<a href="/" />}><ArrowLeft /> Back</Button>
        <div className="flex items-center gap-2 text-sm font-semibold"><Music2 className="size-4 text-primary" /> Audio Merger</div>
        <div className="w-16" />
      </header>

      <div className="mx-auto max-w-4xl px-5 pb-16 pt-8 sm:px-8 sm:pt-14">
        <div className="mx-auto max-w-2xl text-center">
          <div className="eyebrow"><Music2 /> Build one track from many</div>
          <h1 className="mt-5 text-4xl font-semibold tracking-[-0.04em] sm:text-5xl">Put your audio files in the perfect order.</h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-muted-foreground">Select multiple files, rearrange them with the arrow controls, and download one merged MP3 when the sequence is ready.</p>
        </div>

        <section className="surface-card mt-10 p-6 sm:p-8">
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click() }}
            className="dropzone min-h-56"
          >
            <input ref={inputRef} type="file" multiple className="sr-only" accept={ACCEPTED_AUDIO_EXTENSIONS.map((item) => `.${item}`).join(',')} onChange={(event: ChangeEvent<HTMLInputElement>) => { addFiles(Array.from(event.target.files ?? [])); event.target.value = '' }} />
            <UploadCloud className="mb-4 text-primary" />
            <p className="text-lg font-semibold">Add your audio files</p>
            <p className="mt-2 text-sm text-muted-foreground">Drag and drop or choose up to 10 files.</p>
            <p className="mt-4 text-xs text-muted-foreground">MP3, WAV, M4A, AAC, FLAC, OGG, OPUS or WEBM · Up to {MAX_FILE_SIZE / 1024 / 1024} MB each</p>
          </div>

          {error && <p role="alert" className="mt-4 text-sm text-destructive">{error}</p>}

          {files.length > 0 && (
            <div className="mt-7 space-y-3">
              <div className="flex items-center justify-between">
                <div><p className="font-semibold">Merge order</p><p className="text-sm text-muted-foreground">Use the arrow buttons to set the merge order.</p></div>
                <span className="rounded-full border border-border bg-muted px-3 py-1 text-xs font-medium">{files.length} / 10</span>
              </div>

              <div className="audio-merge-list space-y-2" aria-live="polite">
                {files.map((file, index) => (
                  <div
                    key={getFileId(file)}
                    ref={(element) => {
                      const id = getFileId(file)
                      if (element) itemRefs.current.set(id, element)
                      else itemRefs.current.delete(id)
                    }}
                    data-merge-file-id={getFileId(file)}
                    className="audio-merge-item flex items-center gap-3 rounded-xl border border-border bg-background p-3"
                  >
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"><FileAudio className="size-4" /></div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium" title={file.name}>{file.name}</p>
                      <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                    </div>
                    <span className="hidden rounded-md bg-muted px-2 py-1 text-xs font-medium sm:inline">{index + 1}</span>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon-sm" disabled={loading || index === 0} aria-label={`Move ${file.name} up`} onClick={() => moveFileByOffset(getFileId(file), -1)}>↑</Button>
                      <Button variant="ghost" size="icon-sm" disabled={loading || index === files.length - 1} aria-label={`Move ${file.name} down`} onClick={() => moveFileByOffset(getFileId(file), 1)}>↓</Button>
                      <Button variant="ghost" size="icon-sm" disabled={loading} aria-label={`Remove ${file.name}`} onClick={() => removeFile(index)}><Trash2 /></Button>
                    </div>
                  </div>
                ))}
              </div>

              <Button className="mt-4 h-12 w-full text-sm font-semibold" size="lg" disabled={files.length < 2 || loading} onClick={merge}>
                {loading ? <><Loader2 className="animate-spin" /> Merging {files.length} files...</> : <><Download /> Merge & download MP3</>}
              </Button>
            </div>
          )}
        </section>
      </div>

      <dialog ref={dialogRef} className="w-[calc(100%-2rem)] max-w-md rounded-2xl border border-border bg-background p-0 text-foreground shadow-2xl backdrop:bg-black/50">
        <div className="p-6 sm:p-7">
          <div className="flex size-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600"><CheckCircle2 /></div>
          <h2 className="mt-5 text-xl font-semibold">Merge complete</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">Your merged MP3 has been downloaded. Keep the current files if you want to make another arrangement, or start with a new set.</p>
          <div className="mt-6 grid gap-2 sm:grid-cols-2">
            <Button variant="outline" onClick={() => dialogRef.current?.close()}>Continue editing</Button>
            <Button onClick={restart}><RotateCcw /> New set</Button>
          </div>
        </div>
      </dialog>
    </main>
  )
}
