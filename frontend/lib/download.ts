export function parseContentDispositionFilename(value: string | null) {
  if (!value) return null
  const encoded = value.match(/filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i)?.[1]?.trim()
  if (encoded) { try { return decodeURIComponent(encoded.replace(/^['"]|['"]$/g, '')) } catch {} }
  const quoted = value.match(/filename\s*=\s*"([^"]+)"/i)?.[1]
  if (quoted) return quoted
  return value.match(/filename\s*=\s*([^;]+)/i)?.[1]?.trim().replace(/^['"]|['"]$/g, '') ?? null
}

export async function downloadResponse(response: Response, fallbackName: string) {
  const filename = response.headers.get('x-download-filename') ?? parseContentDispositionFilename(response.headers.get('content-disposition')) ?? fallbackName
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(objectUrl)
}

export function formatFileSize(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 Bytes'
  const units = ['Bytes', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`
}

export function formatSpeed(bytesPerSecond: number) { return `${formatFileSize(bytesPerSecond)}/s` }
export function formatEta(seconds: number) {
  if (seconds < 60) return `ETA ${Math.round(seconds)}s`
  return `ETA ${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}
