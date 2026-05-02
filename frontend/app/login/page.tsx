"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, EyeOff, Radar, Brain, Zap, MessageCircle, ArrowRight } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ParticleField } from "@/components/ui/particle-field";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof schema>;

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
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail ?? "Login failed");
      toast.success("Welcome back!");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Login failed");
    }
  }

  return (
    <div className="relative flex min-h-screen overflow-hidden">
      <ParticleField />

      {/* Left side — dark gradient with branding */}
      <div className="hidden lg:flex lg:w-[42%] relative flex-col justify-between bg-gradient-to-br from-stone-900 via-stone-800 to-orange-950 p-12 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(249,115,22,0.25)_0%,_transparent_60%)]" />
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-glow">
              <Radar className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">LeadRadar</span>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          <h2 className="text-4xl font-extrabold leading-tight tracking-tight">
            Find buyers before{" "}
            <span className="text-gradient">your competitors do</span>
          </h2>
          <div className="space-y-5">
            {[
              { icon: Brain, title: "AI-powered lead scoring", desc: "Every lead scored 0-100 with explanation" },
              { icon: Zap, title: "Real-time intent signals", desc: "Know who's ready to buy RIGHT NOW" },
              { icon: MessageCircle, title: "One-click outreach", desc: "WhatsApp, Email & LinkedIn in one click" },
            ].map((item) => (
              <div key={item.title} className="flex items-start gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 backdrop-blur-sm flex-shrink-0">
                  <item.icon className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <p className="font-semibold text-sm">{item.title}</p>
                  <p className="text-xs text-white/50 mt-0.5">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative z-10 text-xs text-white/30">
          &copy; 2025 LeadRadar. All rights reserved.
        </p>
      </div>

      {/* Right side — form */}
      <div className="relative z-10 flex flex-1 items-center justify-center bg-background-primary p-4">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex items-center gap-3 mb-10 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-glow">
              <Radar className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold text-foreground-primary tracking-tight">
              LeadRadar
            </span>
          </div>

          <div className="mb-8">
            <h1 className="text-3xl font-extrabold text-foreground-primary tracking-tight">
              Welcome back
            </h1>
            <p className="text-sm text-foreground-secondary mt-1.5">
              Sign in to your account to continue
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
              <label className="flex items-center gap-2 text-sm text-foreground-secondary cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded-lg border-border text-primary focus:ring-primary"
                />
                Remember me
              </label>
              <Link href="#" className="text-sm font-medium text-primary hover:text-primary-dark transition-colors">
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
              <Link href="/register" className="font-semibold text-primary hover:text-primary-dark transition-colors">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
