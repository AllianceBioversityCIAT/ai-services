import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";
import {
  getPromptVersions,
  getPromptStats,
  getPromptAccessForUser,
  listPromptAccessUsers,
} from "@/lib/database/prompts";
import PromptsEditor from "@/components/prompts-editor";
import PromptAccessManager from "@/components/prompt-access-manager";

export default async function ProjectPromptsPage({
  params,
}: {
  params: { id: string };
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  const projectId = params.id;
  // Access guard for non-admin users
  if (session.role !== "admin") {
    const access = await getPromptAccessForUser(projectId, session.email);
    if (!access) redirect("/prompts");
  }

  const [versions, stats, access] = await Promise.all([
    getPromptVersions(projectId),
    getPromptStats(projectId),
    session.role !== "admin"
      ? getPromptAccessForUser(projectId, session.email)
      : Promise.resolve({ role: "editor" as const }),
  ]);

  const accessList = session.role === "admin" ? await listPromptAccessUsers(projectId) : [];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">Prompts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage prompt versions for this project
          </p>
        </div>

        <PromptsEditor
          projectId={projectId}
          initialVersions={versions}
          initialStats={stats}
          isAdmin={session.role === "admin"}
          canEdit={session.role === "admin" || access?.role === "editor"}
        />

        {session.role === "admin" && (
          <div className="mt-8">
            {/* Admin-only access manager */}
            <PromptAccessManager
              projectId={projectId}
              initial={accessList as any}
            />
          </div>
        )}
      </div>
    </div>
  );
}
