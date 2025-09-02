import { type NextRequest, NextResponse } from "next/server"
import { getSessionFromRequest } from "@/lib/auth"

// Define protected routes
const protectedRoutes = ["/dashboard"]

// Define public routes that should redirect to dashboard if authenticated
const publicRoutes = ["/login"]

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const session = await getSessionFromRequest(request)

  // Check if the current path is a protected route
  const isProtectedRoute = protectedRoutes.some((route) => pathname.startsWith(route))

  // Check if the current path is a public route
  const isPublicRoute = publicRoutes.some((route) => pathname.startsWith(route))

  // Handle protected routes
  if (isProtectedRoute) {
    if (!session) {
      // No valid session, redirect to login
      const loginUrl = new URL("/login", request.url)
      return NextResponse.redirect(loginUrl)
    }
    // Valid session, allow access
    return NextResponse.next()
  }

  // Handle public routes (like login page)
  if (isPublicRoute && session) {
    // User is already authenticated, redirect to dashboard
    const dashboardUrl = new URL("/dashboard", request.url)
    return NextResponse.redirect(dashboardUrl)
  }

  // For all other routes, allow access
  return NextResponse.next()
}

// Configure which paths the middleware should run on
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
}
