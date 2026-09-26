const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export type MediaFormat = 'mp3' | 'mp4'

async function parseError(response: Response) {
  try {
    const body = await response.json()
    if (typeof body?.error === 'string') return body.error
  } catch {
    // The backend may return an empty or non-JSON error response.
  }
  return `Request failed with status ${response.status}.`
}

async function request(url: string, init: RequestInit) {
  try {
    return await fetch(`${API_BASE_URL}${url}`, init)
  } catch {
    throw new Error('Backend unavailable. Please make sure the Flask server is running.')
  }
}

export async function downloadFromUrl(url: string, format: MediaFormat) {
  const response = await request('/api/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, format }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response
}

export async function convertVideoToMp3(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await request('/api/convert', { method: 'POST', body: formData })
  if (!response.ok) throw new Error(await parseError(response))
  return response
}

export async function checkBackendHealth() {
  const response = await request('/api/health')
  if (!response.ok) throw new Error(await parseError(response))
  const body = await response.json()
  return body.status === 'ok'
}
