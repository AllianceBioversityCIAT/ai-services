"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  LogOut,
  User,
  Shield,
  Boxes,
  FolderGit2,
  Stars,
  Users,
} from "lucide-react";
import type { JWTPayload } from "@/lib/auth";

interface DashboardContentProps {
  user: JWTPayload;
}

export function DashboardContent({ user }: DashboardContentProps) {
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const handleLogout = async () => {
    setIsLoggingOut(true);

    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
      });

      if (response.ok) {
        router.replace("/login");
      } else {
        console.error("Logout failed");
        setIsLoggingOut(false);
      }
    } catch (error) {
      console.error("Logout error:", error);
      setIsLoggingOut(false);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/dashboard/stats");
        const data = await res.json();
        if (res.ok) setStats(data);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Welcome Card */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <User className="h-5 w-5 text-primary" />
                Welcome Back
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-lg text-foreground">
                    Welcome, <span className="font-semibold">{user.email}</span>
                    .
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-muted-foreground">Your role is</span>
                    <Badge
                      variant={user.role === "admin" ? "default" : "secondary"}
                      className="capitalize"
                    >
                      {user.role}
                    </Badge>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Email:</span>
                      <p className="font-medium">{user.email}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Role:</span>
                      <p className="font-medium capitalize">{user.role}</p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted-foreground">
                      Projects
                    </div>
                    <div className="text-2xl font-semibold text-foreground">
                      {loading ? "…" : stats?.projects?.total ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Active {loading ? "…" : stats?.projects?.active ?? 0} •
                      Inactive {loading ? "…" : stats?.projects?.inactive ?? 0}
                    </div>
                  </div>
                  <FolderGit2 className="h-6 w-6 text-primary" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted-foreground">Prompts</div>
                    <div className="text-2xl font-semibold text-foreground">
                      {loading ? "…" : stats?.prompts?.total ?? 0}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Stable {loading ? "…" : stats?.prompts?.stable ?? 0} •
                      Unstable {loading ? "…" : stats?.prompts?.unstable ?? 0}
                    </div>
                  </div>
                  <Stars className="h-6 w-6 text-primary" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted-foreground">
                      Products
                    </div>
                    <div className="text-2xl font-semibold text-foreground">
                      {loading ? "…" : stats?.products?.total ?? 0}
                    </div>
                  </div>
                  <Boxes className="h-6 w-6 text-primary" />
                </div>
              </CardContent>
            </Card>

            {user.role === "admin" && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs text-muted-foreground">Users</div>
                      <div className="text-2xl font-semibold text-foreground">
                        {loading ? "…" : stats?.users?.total ?? 0}
                      </div>
                    </div>
                    <Users className="h-6 w-6 text-primary" />
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Recent Prompts */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Recent Prompts</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading…</div>
              ) : stats?.recentPrompts?.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="text-left py-2 px-3 font-medium">
                          Project
                        </th>
                        <th className="text-left py-2 px-3 font-medium">
                          Version
                        </th>
                        <th className="text-left py-2 px-3 font-medium">
                          Stable
                        </th>
                        <th className="text-left py-2 px-3 font-medium">By</th>
                        <th className="text-left py-2 px-3 font-medium">
                          Created
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recentPrompts.map((r: any) => (
                        <tr
                          key={`${r.project_id}-${r.version}`}
                          className="border-b border-border"
                        >
                          <td className="py-2 px-3 text-foreground">
                            {r.project_name || r.project_id}
                          </td>
                          <td className="py-2 px-3 text-foreground">
                            {r.version}
                          </td>
                          <td className="py-2 px-3 text-foreground">
                            {r.is_stable ? "Yes" : "No"}
                          </td>
                          <td className="py-2 px-3 text-muted-foreground">
                            {r.created_by}
                          </td>
                          <td className="py-2 px-3 text-muted-foreground">
                            {new Date(r.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  No recent prompts
                </div>
              )}
            </CardContent>
          </Card>

          {/* Admin Features */}
          {user.role === "admin" && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-primary" />
                  Admin Features
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  You have administrator privileges. Additional admin features
                  can be added here.
                </p>
                <Button
                  variant="outline"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="mt-2 inline-flex items-center gap-2"
                >
                  <LogOut className="h-4 w-4" />
                  {isLoggingOut ? "Logging out…" : "Log out"}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
