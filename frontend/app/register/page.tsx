"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { cn } from "@/lib/cn";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().min(2, "Full name is required"),
  company_name: z.string().optional(),
});

type RegisterForm = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(schema) });

  async function onSubmit(data: RegisterForm) {
    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Registration failed");
      toast.success("Account created! Let's build your ICP.");
      router.push("/dashboard/icp");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="min-h-screen bg-[#0F1B2D] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <div className="w-9 h-9 rounded-lg bg-[#3B6FFF] flex items-center justify-center">
              <span className="text-white font-bold text-lg">Z</span>
            </div>
            <span className="text-white font-bold text-xl">Zentro Leads</span>
          </div>
          <p className="text-slate-400 text-sm">Start generating leads with AI</p>
        </div>

        {/* Card */}
        <div className="bg-[#1a2840] rounded-2xl border border-white/10 p-8">
          <h1 className="text-white text-2xl font-semibold mb-1">Create account</h1>
          <p className="text-slate-400 text-sm mb-6">Free plan — no credit card required</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">
                Full Name
              </label>
              <input
                {...register("full_name")}
                type="text"
                placeholder="Ahmad Faiz"
                className={cn(
                  "w-full px-3.5 py-2.5 rounded-lg bg-[#0F1B2D] border text-white placeholder-slate-500",
                  "focus:outline-none focus:ring-2 focus:ring-[#3B6FFF] focus:border-transparent",
                  errors.full_name ? "border-red-500" : "border-white/10"
                )}
              />
              {errors.full_name && (
                <p className="text-red-400 text-xs mt-1">{errors.full_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">
                Company Name <span className="text-slate-500">(optional)</span>
              </label>
              <input
                {...register("company_name")}
                type="text"
                placeholder="Acme Sdn Bhd"
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#0F1B2D] border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#3B6FFF] focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">
                Email
              </label>
              <input
                {...register("email")}
                type="email"
                placeholder="you@company.com"
                className={cn(
                  "w-full px-3.5 py-2.5 rounded-lg bg-[#0F1B2D] border text-white placeholder-slate-500",
                  "focus:outline-none focus:ring-2 focus:ring-[#3B6FFF] focus:border-transparent",
                  errors.email ? "border-red-500" : "border-white/10"
                )}
              />
              {errors.email && (
                <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">
                Password
              </label>
              <input
                {...register("password")}
                type="password"
                placeholder="Min 8 characters"
                className={cn(
                  "w-full px-3.5 py-2.5 rounded-lg bg-[#0F1B2D] border text-white placeholder-slate-500",
                  "focus:outline-none focus:ring-2 focus:ring-[#3B6FFF] focus:border-transparent",
                  errors.password ? "border-red-500" : "border-white/10"
                )}
              />
              {errors.password && (
                <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                "w-full py-2.5 rounded-lg bg-[#3B6FFF] text-white font-semibold",
                "hover:bg-[#2855D8] transition-colors",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {isSubmitting ? "Creating account…" : "Create account"}
            </button>
          </form>

          <p className="text-slate-400 text-sm text-center mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-[#3B6FFF] hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
