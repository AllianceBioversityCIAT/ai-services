"use client";
import { useEffect, useState } from "react";
import ProjectsTable from "@/components/projects-table";
import ProjectForm from "@/components/project-form";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/projects/list")
      .then(res => res.json())
      .then(data => {
        setProjects(data.projects || []);
        setLoading(false);
      });
  }, []);

  return (
    <div className="max-w-5xl mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">Gestión de Proyectos</h2>
      <ProjectForm onCreated={() => window.location.reload()} />
      <div className="mt-8">
        {loading ? (
          <div className="text-muted-foreground">Cargando proyectos...</div>
        ) : (
          <ProjectsTable projects={projects} />
        )}
      </div>
    </div>
  );
}
