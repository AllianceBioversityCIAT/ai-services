// Simple in-memory rate limiter for login attempts
const attempts = new Map<string, { count: number; resetTime: number }>()

export function checkRateLimit(ip: string): boolean {
  const now = Date.now()
  const key = `login:${ip}`
  const current = attempts.get(key)

  // Reset if time window has passed
  if (current && now > current.resetTime) {
    attempts.delete(key)
  }

  const record = attempts.get(key) || { count: 0, resetTime: now + 5 * 60 * 1000 } // 5 minutes

  if (record.count >= 5) {
    return false // Rate limited
  }

  record.count++
  attempts.set(key, record)
  return true
}
