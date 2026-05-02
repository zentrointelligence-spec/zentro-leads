# LeadRadar Production Deployment Guide

## Overview

Deploy LeadRadar in production using **Railway** (backend + database) and **Vercel** (frontend).

---

## Prerequisites

- [Railway](https://railway.app) account
- [Vercel](https://vercel.com) account
- GitHub repository with your LeadRadar code
- All API keys ready (see checklist below)

---

## Step 1 — Deploy Backend on Railway

1. Go to [railway.app](https://railway.app) and log in.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Select your `zentro-leads` repository.
4. In project settings, set **Root Directory** to `/backend`.
5. Railway will detect `Dockerfile.production` automatically (via `railway.toml`).
6. Add a **PostgreSQL** database from Railway's plugin marketplace.
7. Add a **Redis** instance from Railway's plugin marketplace.
8. Go to **Variables** → **New Variable** and add all variables from `.env.production.example`.
   - Use Railway's auto-generated `DATABASE_URL` and `REDIS_URL` from the plugins.
9. Click **Deploy**.

### Run Database Migration

After first deploy, open a Railway shell for the backend service:

```bash
alembic upgrade head
```

Or run via Railway dashboard → Backend Service → **Deploy** → **Run Command**.

---

## Step 2 — Deploy Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) and log in.
2. Click **Add New Project** → Import your GitHub repository.
3. Set **Root Directory** to `/frontend`.
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app`
5. Click **Deploy**.

---

## Step 3 — Configure Custom Domains

| Service | Domain | Target |
|---------|--------|--------|
| Backend API | `api.leadradar.io` | Railway service |
| Frontend App | `app.leadradar.io` | Vercel project |

In Railway: **Settings** → **Domains** → add custom domain.
In Vercel: **Project Settings** → **Domains** → add custom domain.

Update `NEXT_PUBLIC_API_URL` in Vercel to your custom domain.

---

## Step 4 — Verify Deployment

### Health Check

```bash
curl https://api.leadradar.io/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "LeadRadar",
  "version": "2.0.0",
  "environment": "production",
  "jobs": 6,
  "timestamp": "2026-05-02T12:00:00+00:00"
}
```

### Job Status

```bash
curl https://api.leadradar.io/api/v1/jobs/status
```

### Login & Test

1. Visit `https://app.leadradar.io/login`
2. Log in with your account
3. Generate leads via ICP
4. Check the **Live Signal Feed** widget on the dashboard

---

## Environment Variables Checklist

| Variable | Source | Required |
|----------|--------|----------|
| `POSTGRES_URL` / `POSTGRES_URL_ASYNC` | Railway PostgreSQL plugin | ✅ |
| `REDIS_URL` | Railway Redis plugin | ✅ |
| `JWT_SECRET_KEY` | Generate with `openssl rand -hex 32` | ✅ |
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com) | ✅ |
| `GOOGLE_MAPS_API_KEY` | [Google Cloud](https://console.cloud.google.com) | ✅ |
| `GOOGLE_SEARCH_API_KEY` | Google Cloud | ✅ |
| `GOOGLE_SEARCH_CX` | Google Programmable Search Engine | ✅ |
| `STRIPE_SECRET_KEY` | [Stripe Dashboard](https://dashboard.stripe.com) | ✅ |
| `STRIPE_WEBHOOK_SECRET` | Stripe CLI or Dashboard | ✅ |
| `TWILIO_ACCOUNT_SID` | [Twilio Console](https://console.twilio.com) | ⚠️ (for WhatsApp alerts) |
| `TWILIO_AUTH_TOKEN` | Twilio Console | ⚠️ |
| `SENDGRID_API_KEY` | [SendGrid](https://app.sendgrid.com) | ⚠️ (for email digest) |
| `ADMIN_PHONE` | Your WhatsApp number | ⚠️ |
| `ADMIN_EMAIL` | Your email | ⚠️ |

---

## Step 5 — Post-Deploy Monitoring

### Check Job Logs

In Railway dashboard → Backend service → **Logs**:

```
APScheduler started with 6 jobs: monthly_reset, tender_monitor, ...
Tender Monitor: scan complete. matches=2, upgraded=1, created=1
Daily Digest: complete. users=5, whatsapp=3, email=5
```

### Database Quick Checks

```sql
-- Count signals
SELECT COUNT(*) FROM zl_auto_signals;

-- Count leads by tier
SELECT lead_tier, COUNT(*) FROM zl_leads GROUP BY lead_tier;

-- Recent signals
SELECT company_name, signal_source, detected_at
FROM zl_auto_signals
ORDER BY detected_at DESC
LIMIT 10;
```

### Common Issues

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` on deploy | Rebuild Docker image: `railway up` |
| Database connection timeout | Check `POSTGRES_URL_ASYNC` uses `asyncpg` |
| WhatsApp alerts not sending | Verify `TWILIO_WHATSAPP_NUMBER` has `whatsapp:` prefix in code |
| Scheduler not starting | Check logs for APScheduler startup message |
| Frontend API 404 | Verify `NEXT_PUBLIC_API_URL` has no trailing slash |

---

## Rollback

Railway keeps previous deploys. To rollback:
1. Railway Dashboard → Backend Service → **Deployments**
2. Click the previous working deployment → **Redeploy**

Vercel also keeps previous deploys. Go to **Deployments** → click **...** → **Redeploy**.
