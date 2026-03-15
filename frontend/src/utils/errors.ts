export function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const response = (err as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (Array.isArray(detail)) {
      return detail.map((e: { msg?: string }) => e.msg || '').filter(Boolean).join('; ')
    }
    if (typeof detail === 'string') {
      return detail
    }
  }
  if (err instanceof Error) {
    return err.message
  }
  return 'An error occurred'
}
