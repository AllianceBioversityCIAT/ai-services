import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { listProducts } from "@/lib/database/products";
import { getProject, getProjectStats, listProjects } from "@/lib/database/projects";
import {
  getPromptStats,
  getPromptVersions,
  listProjectIdsForUserAccess,
} from "@/lib/database/prompts";
import { listUsers } from "@/lib/database/users";

export async function GET() {
  try {
    const session = await getSession();
    if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

    const isAdmin = session.role === "admin";

    if (isAdmin) {
      const [products, projectStats, users, projects] = await Promise.all([
        listProducts(),
        getProjectStats(),
        listUsers(),
        listProjects(),
      ]);

      // Aggregate prompt stats across all projects
      const projectIds = projects.map((p: any) => p.id || p.PK?.split("#")[1]).filter(Boolean);
      const promptStatsList = await Promise.all(
        projectIds.map((id: string) => getPromptStats(id))
      );

      const promptsAgg = promptStatsList.reduce(
        (acc, s) => {
          acc.total += s.total || 0;
          acc.stable += s.stable || 0;
          acc.unstable += s.unstable || 0;
          return acc;
        },
        { total: 0, stable: 0, unstable: 0 }
      );

      // Recent prompts: pick latest version from each project and sort by created_at
      const recentCandidates = await Promise.all(
        projectIds.map(async (id) => {
          const versions = await getPromptVersions(id);
          const latest = versions?.[0];
          return latest
            ? {
                project_id: id,
                project_name: (projects.find((p: any) => (p.id || p.PK?.split("#")[1]) === id)?.name) || id,
                version: latest.version,
                created_at: latest.created_at,
                created_by: latest.created_by || "-",
                is_stable: latest.is_stable,
              }
            : null;
        })
      );

      const recentPrompts = recentCandidates
        .filter(Boolean)
        .sort((a: any, b: any) => (a!.created_at > b!.created_at ? -1 : 1))
        .slice(0, 8);

      return NextResponse.json({
        role: session.role,
        products: { total: products.length },
        projects: projectStats,
        prompts: promptsAgg,
        users: { total: users.length },
        recentPrompts,
      });
    }

    // Non-admin: restrict to accessible projects
    const accessibleIds = await listProjectIdsForUserAccess(session.email);
    const uniqueIds = Array.from(new Set(accessibleIds));
    const projects = await Promise.all(uniqueIds.map((id) => getProject(id)));
    const validProjects = projects.filter(Boolean) as any[];

    const promptStatsList = await Promise.all(uniqueIds.map((id) => getPromptStats(id)));
    const promptsAgg = promptStatsList.reduce(
      (acc, s) => {
        acc.total += s.total || 0;
        acc.stable += s.stable || 0;
        acc.unstable += s.unstable || 0;
        return acc;
      },
      { total: 0, stable: 0, unstable: 0 }
    );

    const recentCandidates = await Promise.all(
      uniqueIds.map(async (id) => {
        const versions = await getPromptVersions(id);
        const latest = versions?.[0];
        return latest
          ? {
              project_id: id,
              project_name: (validProjects.find((p: any) => (p.id || p.PK?.split("#")[1]) === id)?.name) || id,
              version: latest.version,
              created_at: latest.created_at,
              created_by: latest.created_by || "-",
              is_stable: latest.is_stable,
            }
          : null;
      })
    );

    const recentPrompts = recentCandidates
      .filter(Boolean)
      .sort((a: any, b: any) => (a!.created_at > b!.created_at ? -1 : 1))
      .slice(0, 8);

    // Derive project status counts from accessible projects
    const projectsStats = {
      total: validProjects.length,
      active: validProjects.filter((p) => p.status === "active").length,
      inactive: validProjects.filter((p) => p.status === "inactive").length,
    };

    return NextResponse.json({
      role: session.role,
      products: { total: 0 }, // hidden for users; could compute linked products if needed
      projects: projectsStats,
      prompts: promptsAgg,
      recentPrompts,
    });
  } catch (error) {
    return NextResponse.json({ error: "Error building dashboard stats" }, { status: 500 });
  }
}

