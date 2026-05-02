"use client";

import { useEffect, useRef } from "react";

interface Neutron {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
  glow: number;
}

interface Layer {
  neutrons: Neutron[];
  count: number;
  speedMult: number;
  radiusMin: number;
  radiusMax: number;
  opacityMin: number;
  opacityMax: number;
  glowChance: number;
  color: string; // rgb string
  connectDist: number;
  parallaxFactor: number;
}

function createLayer(
  count: number,
  speedMult: number,
  radiusMin: number,
  radiusMax: number,
  opacityMin: number,
  opacityMax: number,
  glowChance: number,
  color: string,
  connectDist: number,
  parallaxFactor: number,
  w: number,
  h: number
): Layer {
  const neutrons: Neutron[] = [];
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = (Math.random() * 0.15 + 0.05) * speedMult;
    neutrons.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      radius: Math.random() * (radiusMax - radiusMin) + radiusMin,
      opacity: Math.random() * (opacityMax - opacityMin) + opacityMin,
      glow: Math.random() < glowChance ? Math.random() * 0.4 + 0.2 : 0,
    });
  }
  return {
    neutrons,
    count,
    speedMult,
    radiusMin,
    radiusMax,
    opacityMin,
    opacityMax,
    glowChance,
    color,
    connectDist,
    parallaxFactor,
  };
}

export function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let layers: Layer[] = [];
    const c = canvas;
    const g = ctx;
    let mouseX = 0;
    let mouseY = 0;
    let targetMouseX = 0;
    let targetMouseY = 0;

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      c.width = window.innerWidth * dpr;
      c.height = window.innerHeight * dpr;
      g.scale(dpr, dpr);
      c.style.width = `${window.innerWidth}px`;
      c.style.height = `${window.innerHeight}px`;
    }

    function createLayers() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const area = w * h;
      const baseCount = Math.min(80, Math.floor(area / 18000));

      const isDark = document.documentElement.classList.contains("dark");

      // Layer 1 — far background: large, slow, dim, warm orange
      layers = [
        createLayer(
          Math.floor(baseCount * 0.4),
          0.4,
          1.5,
          3.5,
          0.08,
          0.2,
          0.1,
          isDark ? "200, 120, 60" : "249, 140, 40",
          140,
          0.03,
          w,
          h
        ),
        // Layer 2 — mid: medium, medium speed, amber
        createLayer(
          Math.floor(baseCount * 0.7),
          0.7,
          1.0,
          2.2,
          0.12,
          0.35,
          0.25,
          isDark ? "230, 170, 50" : "251, 170, 30",
          100,
          0.06,
          w,
          h
        ),
        // Layer 3 — near foreground: small, fast, bright with glow
        createLayer(
          Math.floor(baseCount * 0.5),
          1.1,
          0.6,
          1.5,
          0.2,
          0.6,
          0.5,
          isDark ? "255, 200, 80" : "255, 190, 50",
          80,
          0.1,
          w,
          h
        ),
      ];
    }

    function drawNeutron(n: Neutron, color: string, isDark: boolean) {
      // Glow effect for bright neutrons
      if (n.glow > 0) {
        const glowRadius = n.radius * (4 + n.glow * 6);
        const grad = g.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowRadius);
        grad.addColorStop(0, `rgba(${color}, ${n.opacity * n.glow * 1.5})`);
        grad.addColorStop(0.3, `rgba(${color}, ${n.opacity * n.glow * 0.5})`);
        grad.addColorStop(1, `rgba(${color}, 0)`);
        g.fillStyle = grad;
        g.beginPath();
        g.arc(n.x, n.y, glowRadius, 0, Math.PI * 2);
        g.fill();
      }

      // Core
      g.beginPath();
      g.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      g.fillStyle = `rgba(${color}, ${n.opacity})`;
      g.fill();

      // Bright center for larger neutrons
      if (n.radius > 1.2) {
        g.beginPath();
        g.arc(n.x, n.y, n.radius * 0.4, 0, Math.PI * 2);
        g.fillStyle = `rgba(${isDark ? "255, 230, 180" : "255, 240, 220"}, ${n.opacity * 0.8})`;
        g.fill();
      }
    }

    function draw() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const isDark = document.documentElement.classList.contains("dark");

      // Smooth mouse follow
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      g.clearRect(0, 0, w, h);

      layers.forEach((layer) => {
        const parallaxX = mouseX * layer.parallaxFactor;
        const parallaxY = mouseY * layer.parallaxFactor;

        // Update positions
        layer.neutrons.forEach((n) => {
          n.x += n.vx;
          n.y += n.vy;

          // Wrap with parallax offset
          const wrapW = w + Math.abs(parallaxX) * 4;
          const wrapH = h + Math.abs(parallaxY) * 4;
          if (n.x < -parallaxX * 2) n.x += wrapW;
          if (n.x > w + parallaxX * 2) n.x -= wrapW;
          if (n.y < -parallaxY * 2) n.y += wrapH;
          if (n.y > h + parallaxY * 2) n.y -= wrapH;
        });

        // Draw connecting lines within layer
        for (let i = 0; i < layer.neutrons.length; i++) {
          for (let j = i + 1; j < layer.neutrons.length; j++) {
            const a = layer.neutrons[i];
            const b = layer.neutrons[j];
            const dx = a.x - b.x;
            const dy = a.y - b.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < layer.connectDist) {
              const strength = (1 - dist / layer.connectDist) * Math.min(a.opacity, b.opacity);
              g.beginPath();
              g.moveTo(a.x, a.y);
              g.lineTo(b.x, b.y);
              g.strokeStyle = `rgba(${layer.color}, ${strength * 0.15})`;
              g.lineWidth = 0.5;
              g.stroke();
            }
          }
        }

        // Draw neutrons with parallax offset
        g.save();
        g.translate(parallaxX, parallaxY);
        layer.neutrons.forEach((n) => {
          drawNeutron(n, layer.color, isDark);
        });
        g.restore();
      });

      animId = requestAnimationFrame(draw);
    }

    function handleMouseMove(e: MouseEvent) {
      targetMouseX = (e.clientX - window.innerWidth / 2) * -1;
      targetMouseY = (e.clientY - window.innerHeight / 2) * -1;
    }

    resize();
    createLayers();
    draw();

    const handleResize = () => {
      resize();
      createLayers();
    };
    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0, opacity: 0.85 }}
    />
  );
}
