export const MAX_FILE_SIZE = 500 * 1024 * 1024
export const ACCEPTED_EXTENSIONS = ['mp4', 'mov', 'mkv', 'avi', 'webm'] as const

export function validateMediaUrl(value: string) {
  if (!value.trim()) return 'Enter a video URL to continue.'
  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol)) return 'Use a valid HTTP or HTTPS URL.'
  } catch {
    return 'Enter a valid URL, including https://.'
  }
  return ''
}

export function validateVideoFile(file: File) {
  if (file.size > MAX_FILE_SIZE) return 'That file is larger than the 500 MB limit.'
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension || !ACCEPTED_EXTENSIONS.includes(extension as (typeof ACCEPTED_EXTENSIONS)[number])) {
    return 'Choose an MP4, MOV, MKV, AVI, or WEBM video.'
  }
  return ''
}
