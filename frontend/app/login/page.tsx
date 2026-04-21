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
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(schema) });

  async function onSubmit(data: LoginForm) {
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Login failed");
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Login failed");
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
          <p className="text-slate-400 text-sm">AI-powered lead generation</p>
        </div>

        {/* Card */}
        <div className="bg-[#1a2840] rounded-2xl border border-white/10 p-8">
          <h1 className="text-white text-2xl font-semibold mb-1">Sign in</h1>
          <p className="text-slate-400 text-sm mb-6">Enter your credentials to continue</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
                placeholder="••••••••"
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
              {isSubmitting ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="text-slate-400 text-sm text-center mt-6">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-[#3B6FFF] hover:underline font-medium">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
