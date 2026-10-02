const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export type MediaFormat = 'mp3' | 'mp4'
export type Resolution = 'highest' | 'medium' | 'lowest'
export type DownloadStatus = 'queued' | 'downloading' | 'processing' | 'completed' | 'cancelled' | 'failed'

export interface DownloadStartRequest { url: string; format: MediaFormat; resolution?: Resolution }
export interface DownloadStartResponse { job_id: string; status: 'queued'; progress_url: string; cancel_url: string; file_url: string }
export interface DownloadProgressResponse {
  job_id: string; status: DownloadStatus; progress?: number; phase?: string; format?: MediaFormat
  requested_resolution?: Resolution; effective_resolution?: number | null; selection_note?: string | null
  title?: string | null; filename?: string | null; downloaded_bytes?: number | null; total_bytes?: number | null
  speed_bytes_per_second?: number | null; eta_seconds?: number | null; error?: string | null; cancel_requested?: boolean
}
export interface DownloadCancelResponse { job_id: string; status: 'cancelling' | 'cancelled'; message?: string }

async function parseError(response: Response) {
  try { const body = await response.json(); if (typeof body?.error === 'string') return body.error } catch {}
  return `Request failed with status ${response.status}.`
}

async function request(url: string, init?: RequestInit) {
  // NEXT_PUBLIC_API_URL is commonly set to /api when Nginx owns the public /api prefix.
  // Keep endpoint definitions as /api/... so they also work when the base URL is empty or absolute.
  const normalizedPath = API_BASE_URL.replace(/\/$/, '') === '/api' && url.startsWith('/api/') ? url.slice(4) : url
  const target = `${API_BASE_URL.replace(/\/$/, '')}${normalizedPath}` || normalizedPath
  try { return await fetch(target, init) } catch { throw new Error('Backend unavailable. Please make sure the backend service is running.') }
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await request(url, init)
  if (!response.ok) throw new Error(await parseError(response))
  return response.json() as Promise<T>
}

export function startDownload(payload: DownloadStartRequest, signal?: AbortSignal) {
  return jsonRequest<DownloadStartResponse>('/api/download/start', { method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
}

export function getDownloadProgress(jobId: string, signal?: AbortSignal) {
  return jsonRequest<DownloadProgressResponse>(`/api/download/progress/${encodeURIComponent(jobId)}`, { signal })
}

export function cancelDownload(jobId: string, signal?: AbortSignal) {
  return jsonRequest<DownloadCancelResponse>(`/api/download/cancel/${encodeURIComponent(jobId)}`, { method: 'POST', signal })
}

export function getDownloadFile(jobId: string, signal?: AbortSignal) {
  return request(`/api/download/file/${encodeURIComponent(jobId)}`, { signal }).then(async (response) => { if (!response.ok) throw new Error(await parseError(response)); return response })
}

export async function downloadFromUrl(url: string, format: MediaFormat) {
  const response = await request('/api/download', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url, format }) })
  if (!response.ok) throw new Error(await parseError(response)); return response
}

export async function convertVideosToMp3(files: File[]) {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)
  const response = await request('/api/convert', { method: 'POST', body: formData })
  if (!response.ok) throw new Error(await parseError(response))
  return response
}


export async function trimAudio(file: File, startSeconds: number, endSeconds: number) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('start_seconds', String(startSeconds))
  formData.append('end_seconds', String(endSeconds))
  const response = await request('/api/audio/trim', { method: 'POST', body: formData })
  if (!response.ok) throw new Error(await parseError(response))
  return response
}

export async function mergeAudioFiles(files: File[]) {
  const formData = new FormData()
  for (const file of files) formData.append('files', file)
  const response = await request('/api/audio/merge', { method: 'POST', body: formData })
  if (!response.ok) throw new Error(await parseError(response))
  return response
}

export async function checkBackendHealth() {
  const response = await request('/api/health'); if (!response.ok) throw new Error(await parseError(response))
  const body = await response.json(); return body.status === 'ok'
}

export const backendBaseUrl = API_BASE_URL
export function buildDownloadUrl(path: string) { return `${backendBaseUrl}${path}` }

export function formatBackendError(error: unknown) { return error instanceof Error ? error.message : 'Download failed. Please try again.' }
