import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { listProjects } from "../../lib/config";
import ProjectsPageClient from "./projects-page-client";

export default async function ProjectsPage() {
  const user = await getSession();
  if (!user) {
    redirect("/login");
    return null;
  }

  const projects = await listProjects();

  return <ProjectsPageClient initialProjects={projects} />;
}
