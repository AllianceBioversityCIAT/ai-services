import Link from "next/link";
import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";
import { getProject, listProjects } from "@/lib/database/projects";
import { listProjectIdsForUserAccess } from "@/lib/database/prompts";

export default async function PromptsIndexPage() {
  const session = await getSession();
  if (!session) redirect("/login");

  let projects: any[] = [];
  if (session.role === "admin") {
    projects = await listProjects();
  } else {
    const ids = await listProjectIdsForUserAccess(session.email);
    const uniqueIds = Array.from(new Set(ids));
    const results = await Promise.all(uniqueIds.map((id) => getProject(id)));
    projects = results.filter(Boolean) as any[];
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-foreground">Prompts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Select a project to manage its prompts
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p: any) => {
            const id = p.id || p.PK?.split("#")[1];
            return (
              <Link
                href={`/projects/${id}/prompts`}
                key={p.PK || id}
                className="rounded-lg border border-border bg-card p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="text-sm text-muted-foreground">Project</div>
                <div className="text-base font-medium text-foreground">{p.name}</div>
                <div className="text-base font-medium text-foreground">{p.description}</div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
