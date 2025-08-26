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
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your project portfolio
          </p>
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Form Sidebar */}
          <div className="lg:col-span-1">
            <ProjectForm onCreated={fetchProjects} />
          </div>

          {/* Table Main Content */}
          <div className="lg:col-span-2">
            <ProjectsTable
              projects={projects}
              onDelete={handleDelete}
              onEdit={fetchProjects}
            />
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-sm text-muted-foreground">
                  Loading projects...
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
