import { redirect } from "next/navigation"
import { getSession } from "@/lib/auth"
import { DashboardContent } from "@/components/dashboard-content"

export default async function DashboardPage() {
  // Get session data
  const session = await getSession()

  // Redirect to login if no session (backup protection)
  if (!session) {
    redirect("/login")
  }

  return <DashboardContent user={session} />
}
