"use client";

import * as React from "react";
import Image from "next/image";
import { cn } from "@/lib/cn";

interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  name?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeClasses = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-11 w-11 text-base",
  xl: "h-14 w-14 text-lg",
};

function getInitials(name: string = ""): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function stringToColor(str: string): string {
  const colors = [
    "#F97316", "#EA580C", "#FB923C", "#FBBF24",
    "#F59E0B", "#D97706", "#EF4444", "#DC2626",
    "#22C55E", "#16A34A", "#78716C", "#57534E",
  ];
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, src, name = "", size = "md", ...props }, ref) => {
    const initials = getInitials(name);
    const bgColor = stringToColor(name || "U");

    return (
      <div
        ref={ref}
        className={cn(
          "relative inline-flex items-center justify-center rounded-full overflow-hidden flex-shrink-0",
          sizeClasses[size],
          className
        )}
        style={!src ? { backgroundColor: bgColor } : undefined}
        {...props}
      >
        {src ? (
          <Image
            src={src}
            alt={name || "User"}
            fill
            unoptimized
            className="object-cover"
            sizes="56px"
          />
        ) : (
          <span className="font-semibold text-white">{initials}</span>
        )}
      </div>
    );
  }
);
Avatar.displayName = "Avatar";

export { Avatar, getInitials };
