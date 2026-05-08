"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, EyeOff, Brain, Zap, MessageCircle } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ParticleField } from "@/components/ui/particle-field";
import { readAuthFetchResult } from "@/lib/parse-json-client";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof schema>;

function ZentroMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-600 via-amber-500 to-emerald-500 shadow-[0_0_24px_rgba(234,88,12,0.4)]">
        <svg viewBox="0 0 44 44" className="h-6 w-6" aria-hidden="true">
          <path d="M12 13.5h17.6L14.4 30.5H32" fill="none" stroke="#0B1120" strokeWidth="4.8" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M28 11c5.1 2.1 8 6 8 11s-2.9 8.9-8 11" fill="none" stroke="#fff7ed" strokeWidth="2" strokeLinecap="round" opacity=".95" />
        </svg>
      </div>
      <div className="leading-none">
        <div className="text-lg font-black tracking-tight text-white">Zentro Intelligence</div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
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
      const result = await readAuthFetchResult(res);
      if (!result.success) {
        toast.error(result.message);
        return;
      }
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="relative flex min-h-screen overflow-hidden">
      <ParticleField />

      {/* Left panel */}
      <div className="hidden lg:flex lg:w-[42%] relative flex-col justify-between bg-gradient-to-br from-[#0B1120] via-[#0f1a2e] to-[#1a0e08] p-12 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(234,88,12,0.22)_0%,transparent_60%)]" />
        <div className="relative z-10">
          <ZentroMark />
        </div>

        <div className="relative z-10 space-y-8">
          <h2 className="text-4xl font-black leading-tight tracking-tight">
            From Lead to Policy —{" "}
            <span className="bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">
              Fully Automated
            </span>
          </h2>
          <div className="space-y-5">
            {[
              { icon: Brain, title: "AI lead scoring", desc: "Every lead scored 0–100 with transparent reasoning" },
              { icon: Zap, title: "Real-time intent signals", desc: "Know which companies are ready to buy right now" },
              { icon: MessageCircle, title: "One-click outreach", desc: "WhatsApp and email drafts generated automatically" },
            ].map((item) => (
              <div key={item.title} className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-500/10 text-orange-300">
                  <item.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-black text-white">{item.title}</p>
                  <p className="mt-0.5 text-xs text-slate-400">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-xs text-slate-600">
          &copy; 2026 Zentro Intelligence Sdn Bhd
        </p>
      </div>

      {/* Right panel — form */}
      <div className="relative z-10 flex flex-1 items-center justify-center bg-background-primary p-4">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <ZentroMark />
          </div>

          <div className="mb-8">
            <h1 className="text-3xl font-black tracking-tight text-foreground-primary">
              Welcome back
            </h1>
            <p className="mt-1.5 text-sm text-foreground-secondary">
              Sign in to your Zentro Intelligence account
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@company.com"
              error={errors.email?.message}
              {...register("email")}
            />

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-foreground-primary">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  className={cn(
                    "flex w-full rounded-xl border border-border bg-background-elevated px-4 py-3 pr-11 text-sm text-foreground-primary shadow-sm placeholder:text-foreground-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 transition-all",
                    errors.password && "border-hot"
                  )}
                  {...register("password")}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-hot">{errors.password.message}</p>
              )}
            </div>

            <div className="flex items-center justify-between">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground-secondary">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                />
                Remember me
              </label>
              <Link href="#" className="text-sm font-medium text-primary transition-colors hover:text-primary-dark">
                Forgot password?
              </Link>
            </div>

            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Sign in
            </Button>
          </form>

          <div className="mt-8">
            <Separator className="my-5" />
            <p className="text-center text-sm text-foreground-secondary">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="font-semibold text-primary transition-colors hover:text-primary-dark">
                Create one free
              </Link>
            </p>
          </div>

          <div className="mt-6 text-center">
            <Link href="/" className="text-xs text-slate-600 transition hover:text-slate-400">
              ← Back to zentro.io
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
