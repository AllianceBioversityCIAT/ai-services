import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { listProjects } from "../../lib/database/projects";
import { listProjectIdsForUserAccess } from "@/lib/database/prompts";
import ProjectsPageClient from "./projects-page-client";

export default async function ProjectsPage() {
  const user = await getSession();
  if (!user) {
    redirect("/login");
    return null;
  }

  const projects = await listProjects();
  const isAdmin = user.role === "admin";
  const editableProjectIds = isAdmin
    ? projects.map((p: any) => p.id || p.PK?.split("#")[1])
    : await listProjectIdsForUserAccess(user.email);

  return (
    <ProjectsPageClient
      initialProjects={projects}
      isAdmin={isAdmin}
      editableProjectIds={editableProjectIds}
    />
  );
}
