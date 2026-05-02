"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, EyeOff, Radar, Brain, Zap, MessageCircle } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ParticleField } from "@/components/ui/particle-field";

const schema = z.object({
  full_name: z.string().min(2, "Full name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirm_password: z.string().min(1, "Confirm your password"),
  company_name: z.string().optional(),
  agree_terms: z.boolean().refine((v) => v === true, {
    message: "You must agree to the Terms of Service",
  }),
}).refine((data) => data.password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});

type RegisterForm = z.infer<typeof schema>;

type Strength = { label: string; color: string; width: string };

function getPasswordStrength(password: string): Strength {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const levels: Strength[] = [
    { label: "Weak", color: "bg-hot", width: "25%" },
    { label: "Fair", color: "bg-warm", width: "50%" },
    { label: "Strong", color: "bg-potential", width: "75%" },
    { label: "Very Strong", color: "bg-success", width: "100%" },
  ];
  return levels[Math.min(score, 3)];
}

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ resolver: zodResolver(schema) });

  const password = watch("password", "");
  const strength = getPasswordStrength(password);

  async function onSubmit(data: RegisterForm) {
    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          full_name: data.full_name,
          company_name: data.company_name,
        }),
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
        <div className="w-full max-w-sm py-8">
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
              Create your account
            </h1>
            <p className="text-sm text-foreground-secondary mt-1.5">
              Free plan — no credit card required
            </p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Full Name"
              placeholder="Ahmad Faiz"
              error={errors.full_name?.message}
              {...register("full_name")}
            />

            <Input
              label="Company Name"
              placeholder="Acme Sdn Bhd (optional)"
              {...register("company_name")}
            />

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
                  placeholder="Min 8 characters"
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

              {password.length > 0 && (
                <div className="mt-2.5">
                  <div className="h-1.5 w-full rounded-full bg-background-secondary overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all duration-300", strength.color)}
                      style={{ width: strength.width }}
                    />
                  </div>
                  <p className="mt-1.5 text-xs text-foreground-muted">
                    Strength:{" "}
                    <span className={cn("font-semibold", strength.color.replace("bg-", "text-"))}>
                      {strength.label}
                    </span>
                  </p>
                </div>
              )}
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-foreground-primary">
                Confirm Password
              </label>
              <div className="relative">
                <input
                  type={showConfirm ? "text" : "password"}
                  placeholder="Confirm your password"
                  className={cn(
                    "flex w-full rounded-xl border border-border bg-background-elevated px-4 py-3 pr-11 text-sm text-foreground-primary shadow-sm placeholder:text-foreground-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 transition-all",
                    errors.confirm_password && "border-hot"
                  )}
                  {...register("confirm_password")}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground-primary transition-colors"
                >
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="mt-1.5 text-xs text-hot">{errors.confirm_password.message}</p>
              )}
            </div>

            <label className="flex items-start gap-2.5 text-sm text-foreground-secondary cursor-pointer">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 rounded-lg border-border text-primary focus:ring-primary"
                {...register("agree_terms")}
              />
              <span>
                I agree to the{" "}
                <Link href="#" className="font-semibold text-primary hover:text-primary-dark">
                  Terms of Service
                </Link>{" "}
                and{" "}
                <Link href="#" className="font-semibold text-primary hover:text-primary-dark">
                  Privacy Policy
                </Link>
              </span>
            </label>
            {errors.agree_terms && (
              <p className="text-xs text-hot">{errors.agree_terms.message}</p>
            )}

            <Button type="submit" className="w-full" isLoading={isSubmitting}>
              Create account
            </Button>
          </form>

          <div className="mt-8">
            <Separator className="my-5" />
            <p className="text-center text-sm text-foreground-secondary">
              Already have an account?{" "}
              <Link href="/login" className="font-semibold text-primary hover:text-primary-dark transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
