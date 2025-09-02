import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";
import { DashboardContent } from "@/components/dashboard-content";

export default async function DashboardPage() {
  const session = await getSession();

  if (!session) {
    redirect("/login");
  }

  return <DashboardContent user={session} />;
}
