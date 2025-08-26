import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { listUsers } from "../../lib/dynamo";
import UsersPageClient from "./user-page-client";

export default async function UsersPage() {
  const user = await getSession();
  if (!user || user.role !== "admin") {
    redirect("/dashboard");
    return null;
  }

  const users = await listUsers();

  return <UsersPageClient initialUsers={users} currentUserEmail={user.email} />;
}
