"use client";
import { useEffect, useState } from "react";
import ProjectsTable from "@/components/projects-table";
import ProjectForm from "@/components/project-form";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchProjects() {
    setLoading(true);
    const res = await fetch("/api/projects/list");
    const data = await res.json();
    setProjects(data.projects || []);
    setLoading(false);
  }

  async function handleDelete(id: string) {
    await fetch("/api/projects/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    fetchProjects();
  }

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <div className="container mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">Projects Management</h2>
      <div className="max-w-xl mx-auto">
        <div className="mb-8">
          <ProjectForm onCreated={fetchProjects} />
        </div>
        <ProjectsTable projects={projects} onDelete={handleDelete} />
      </div>
      {loading && (
        <div className="text-center py-8 text-muted-foreground">
          Loading projects...
        </div>
      )}
    </div>
  );
}
