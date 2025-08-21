import UserRegisterForm from "@/components/user-register-form";
import UsersTable from "@/components/users-table";
import { getSession } from "@/lib/auth";
import { redirect } from "next/navigation";
import { listUsers } from "../../lib/dynamo";

export default async function UsersPage() {
  const user = await getSession();
  if (!user || user.role !== "admin") {
    redirect("/dashboard");
    return null;
  }

  const users = await listUsers();

  return (
    <div className="container mx-auto py-8">
      <h2 className="text-2xl font-bold mb-6">User Management</h2>
      <div className="max-w-xl mx-auto">
        {/* Formulario en Card */}
        <div className="mb-8">
          <div className="shadow-lg rounded-lg bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Register New User</h3>
            <UserRegisterForm isAdmin={true} />
          </div>
        </div>
        {/* Tabla de usuarios en Card */}
        <div className="shadow-lg rounded-lg bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Registered Users</h3>
          <div className="overflow-x-auto">
            <UsersTable users={users} currentUserEmail={user.email} />
          </div>
        </div>
      </div>
    </div>
  );
}
