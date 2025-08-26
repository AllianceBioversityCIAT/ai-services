"use client";
import { useState } from "react";
import UserRegisterForm from "@/components/user-register-form";
import UsersTable from "@/components/users-table";

export default function UsersPageClient({
  initialUsers,
  currentUserEmail,
}: {
  initialUsers: any[];
  currentUserEmail: string;
}) {
  const [users, setUsers] = useState(initialUsers);
  const [loading, setLoading] = useState(false);

  async function fetchUsers() {
    setLoading(true);
    const res = await fetch("/api/users/list");
    const data = await res.json();
    setUsers(data.users || []);
    setLoading(false);
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-foreground">
            User Management
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage system users and permissions
          </p>
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Form Sidebar */}
          <div className="lg:col-span-1">
            <UserRegisterForm isAdmin={true} onUserCreated={fetchUsers} />
          </div>

          {/* Table Main Content */}
          <div className="lg:col-span-2">
            <UsersTable
              users={users}
              currentUserEmail={currentUserEmail}
              onUserDeleted={fetchUsers}
            />
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="text-sm text-muted-foreground">
                  Loading users...
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
