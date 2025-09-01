"use client";
import React, { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Plus, Save, Star } from "lucide-react";

type VersionItem = {
  PK: string;
  SK: string; // VERSION#<created_at>
  project_id: string;
  version: string;
  prompt_text: string;
  is_stable: boolean;
  created_at: string;
  created_by?: string;
  description?: string;
  parameters?: Record<string, any>;
};

type PromptsEditorProps = {
  projectId: string;
  initialVersions: VersionItem[];
  initialStats: any;
  user: { email: string; role: string };
};

export default function PromptsEditor(props: PromptsEditorProps) {
  const { projectId, initialVersions, initialStats, user } = props;
  const [versions, setVersions] = useState<VersionItem[]>(initialVersions);
  const [stats, setStats] = useState<any>(initialStats);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const latest = versions[0];

  const canEdit = useMemo(() => {
    if (user.role === "admin") return true;
    if (!latest) return true; // allow first creation
    return latest?.created_by === user.email;
  }, [latest, user]);

  const [editor, setEditor] = useState({
    prompt_text: latest?.prompt_text || "",
    version: "",
    description: latest?.description || "",
    parameters: JSON.stringify(latest?.parameters || {}, null, 2),
  });

  useEffect(() => {
    // Reset when versions change (e.g., after save)
    const l = versions[0];
    if (l) {
      setEditor((e) => ({
        ...e,
        prompt_text: l.prompt_text,
        description: l.description || "",
        parameters: JSON.stringify(l.parameters || {}, null, 2),
      }));
    }
  }, [versions]);

  async function refresh() {
    setLoading(true);
    const res = await fetch(`/api/prompts/list?projectId=${encodeURIComponent(projectId)}`);
    const data = await res.json();
    setVersions(data.versions || []);
    setStats(data.stats || {});
    setLoading(false);
  }

  async function handleSaveNew() {
    setSaving(true);
    let parsedParams: Record<string, any> = {};
    try {
      parsedParams = editor.parameters ? JSON.parse(editor.parameters) : {};
    } catch {
      alert("Parameters must be valid JSON");
      setSaving(false);
      return;
    }

    const res = await fetch("/api/prompts/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        projectId,
        prompt_text: editor.prompt_text,
        version: editor.version || undefined,
        description: editor.description,
        parameters: parsedParams,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || "Error creating version");
    } else {
      await refresh();
      setEditor((e) => ({ ...e, version: "" }));
    }
    setSaving(false);
  }

  async function handleMarkStable(created_at: string) {
    const res = await fetch("/api/prompts/mark-stable", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ projectId, createdAt: created_at }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || "Error marking stable");
      return;
    }
    refresh();
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Total versions</div>
          <div className="text-2xl font-semibold text-foreground">{stats.total ?? 0}</div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Stable</div>
          <div className="text-2xl font-semibold text-foreground">{stats.stable ?? 0}</div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="text-xs text-muted-foreground">Latest version</div>
          <div className="text-2xl font-semibold text-foreground">{stats.latest_version ?? "-"}</div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-foreground">Editor</h3>
            {!canEdit && (
              <span className="text-xs text-muted-foreground">Read-only (not owner)</span>
            )}
          </div>

          <label className="text-sm font-medium text-foreground">Prompt</label>
          <textarea
            rows={12}
            value={editor.prompt_text}
            onChange={(e) => setEditor((v) => ({ ...v, prompt_text: e.target.value }))}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="Write your prompt..."
            disabled={!canEdit}
          />

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium text-foreground">Version</label>
              <input
                type="text"
                value={editor.version}
                onChange={(e) => setEditor((v) => ({ ...v, version: e.target.value }))}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder={new Date().toISOString()}
                disabled={!canEdit}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">Description</label>
              <input
                type="text"
                value={editor.description}
                onChange={(e) => setEditor((v) => ({ ...v, description: e.target.value }))}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Short description"
                disabled={!canEdit}
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-foreground">Parameters (JSON)</label>
            <textarea
              rows={6}
              value={editor.parameters}
              onChange={(e) => setEditor((v) => ({ ...v, parameters: e.target.value }))}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder={`{\n  "temperature": 0.3\n}`}
              disabled={!canEdit}
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSaveNew}
              disabled={!canEdit || saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
              title="Save as new version"
            >
              <Save className="h-4 w-4" />
              {saving ? "Saving..." : "Save new version"}
            </button>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-medium text-foreground">Versions</h3>
            <button
              onClick={refresh}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-border text-sm text-foreground hover:bg-muted"
              title="Refresh"
            >
              <Plus className="h-4 w-4" />
              Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="text-left py-2 px-3 font-medium">Version</th>
                  <th className="text-left py-2 px-3 font-medium">Created</th>
                  <th className="text-left py-2 px-3 font-medium">By</th>
                  <th className="text-left py-2 px-3 font-medium">Stable</th>
                  <th className="text-right py-2 px-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">Loading...</td>
                  </tr>
                ) : versions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">No versions yet</td>
                  </tr>
                ) : (
                  versions.map((v) => (
                    <tr key={v.SK} className="border-b border-border">
                      <td className="py-2 px-3 text-foreground">{v.version}</td>
                      <td className="py-2 px-3 text-muted-foreground">
                        {new Date(v.created_at).toLocaleString()}
                      </td>
                      <td className="py-2 px-3 text-muted-foreground">{v.created_by || "-"}</td>
                      <td className="py-2 px-3">
                        {v.is_stable ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 text-xs">
                            <CheckCircle2 className="h-4 w-4" /> Stable
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">No</span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() =>
                              setEditor({
                                prompt_text: v.prompt_text,
                                version: "",
                                description: v.description || "",
                                parameters: JSON.stringify(v.parameters || {}, null, 2),
                              })
                            }
                            className="px-3 py-1.5 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10"
                            title="Load into editor"
                          >
                            Load
                          </button>
                          {user.role === "admin" && !v.is_stable && (
                            <button
                              onClick={() => handleMarkStable(v.created_at)}
                              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-amber-700 hover:bg-amber-50"
                              title="Mark as stable"
                            >
                              <Star className="h-4 w-4" /> Stable
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
