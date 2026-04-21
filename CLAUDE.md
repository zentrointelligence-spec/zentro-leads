# ZENTRO LEADS — PROJECT MEMORY

## Current Status
- Phase 1: Scaffold in progress
- Repo: https://github.com/zentrointelligence-spec/zentro-leads
- Local path: ~/zentro-leads

## What's Built So Far
- [ ] docker-compose.yml ← in progress
- [ ] backend/requirements.txt
- [ ] backend/app/config.py
- [ ] backend/app/database.py
- [ ] backend/app/models.py
- [ ] backend/app/main.py
- [ ] Auth system
- [ ] Alembic setup
- [ ] Frontend scaffold

## Key Decisions Made
1. No Apollo/Hunter — build own scraping engine
2. Separate repo from ZIMS
3. Azure deployment (not Vercel)
4. n8n for pipeline orchestration
5. proxy.ts not middleware.ts
6. All tables prefixed zl_
7. SMTP email verification (not Hunter)
8. Google Maps API for local business data
9. Hot leads ≥85 auto-push to ZIMS
10. shadcn/ui with render={} never asChild

## Companion Product
ZIMS repo: https://github.com/zentrointelligence-spec/zims
ZIMS API runs on port 8000
Zentro Leads API runs on port 8001

## Database
Name: zentro_leads
User: zl_user
Pass: zl_pass
Port: 5433 (local Docker)
All tables: zl_* prefix

## Redis
Port: 6380 (local Docker)
Password: zl_redis_pass
All keys: zl:* prefix

## Pricing Tiers
Free:    25 leads/mo   $0
Starter: 750 leads/mo  $19/mo
Growth:  3000 leads/mo $49/mo
Pro:     10000 leads/mo $99/mo
Agency:  Unlimited      $199/mo

## Target Market
Primary: Insurance agents + SMEs in SEA + Middle East
Secondary: Any small business globally
NOT targeting: US enterprise sales teams (Apollo's market)

## Competitive Edge
1. Local market data (SEA/ME) Apollo doesn't have
2. One sentence ICP setup
3. Native ZIMS integration
4. WhatsApp as primary outreach channel
5. All-in-one (find + attract + capture + convert)
6. Own database — no API dependency
