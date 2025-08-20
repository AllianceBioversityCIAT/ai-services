import { type NextRequest, NextResponse } from "next/server"
import { getUserByEmail } from "@/lib/dynamo"
import { verifyPassword, createToken, setSessionCookie } from "@/lib/auth"
import { loginSchema } from "@/lib/validation"
import { checkRateLimit } from "@/lib/rate-limit"

export async function POST(request: NextRequest) {
  try {
    // Get client IP for rate limiting
    const ip = request.ip || request.headers.get("x-forwarded-for") || "unknown"

    // Check rate limit
    if (!checkRateLimit(ip)) {
      return NextResponse.json({ error: "Too many login attempts. Please try again in 5 minutes." }, { status: 429 })
    }

    // Parse and validate request body
    const body = await request.json()
    const validationResult = loginSchema.safeParse(body)

    if (!validationResult.success) {
      return NextResponse.json({ error: "Invalid input data" }, { status: 400 })
    }

    const { email, password } = validationResult.data

    // Get user from database
    const user = await getUserByEmail(email.toLowerCase())
    if (!user) {
      return NextResponse.json({ error: "Invalid email or password" }, { status: 401 })
    }

    // Verify password
    const isValidPassword = await verifyPassword(password, user.passwordHash)
    if (!isValidPassword) {
      return NextResponse.json({ error: "Invalid email or password" }, { status: 401 })
    }

    // Create JWT token
    const token = await createToken(user.email, user.role)

    // Set session cookie
    setSessionCookie(token)

    return NextResponse.json(
      {
        message: "Login successful",
        user: {
          email: user.email,
          role: user.role,
        },
      },
      { status: 200 },
    )
  } catch (error) {
    console.error("Login error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
