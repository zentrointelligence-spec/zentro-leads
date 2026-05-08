import { redirect } from "next/navigation";
import { authApi } from "@/lib/api";
import { AdminSidebar } from "@/components/admin/admin-sidebar";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await authApi.me().catch(() => null);

  if (!user || user.role !== "admin") {
    redirect("/dashboard");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto bg-gray-950 p-6">
        {children}
      </main>
    </div>
  );
}
