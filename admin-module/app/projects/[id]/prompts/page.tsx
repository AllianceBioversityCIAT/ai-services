import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";
import { getPromptVersions, getPromptStats } from "@/lib/database/prompts";
import PromptsEditor from "@/components/prompts-editor";

export default async function ProjectPromptsPage({
  params,
}: {
  params: { id: string };
}) {
  const session = await getSession();
  if (!session) redirect("/login");

  const projectId = params.id;
  const [versions, stats] = await Promise.all([
    getPromptVersions(projectId),
    getPromptStats(projectId),
  ]);

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
          user={session}
        />
      </div>
    </div>
  );
}

