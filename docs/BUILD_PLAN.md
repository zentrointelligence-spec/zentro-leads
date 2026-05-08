# Build Plan

_Source: `Downloads/Zentro_Leads_Master_Knowledge_Base.docx`._

Phased implementation plan and MVP timeline for Zentro Leads.

## Section 5 — Complete Phased Build Plan

This is the master build plan that combines: fixing the current codebase, completing missing features, building the knowledge base-driven AI layer, and expanding to B2C. Total estimated time: 16 focused development days to MVP, then ongoing feature expansion.

### Phase 1 — Critical Bug Fixes (Days 1–2)

Nothing else matters until these crashes are fixed. Do these first, in this order.

| Task | Estimated Time |
| --- | --- |
| Fix LeadStatus enum — add VIEWED/WON to DB migration | 1 hour |
| Fix ZLCompany missing columns — migration for twitter_url/tiktok_url | 30 min |
| Fix 20260502zims duplicate column — add IF NOT EXISTS guard | 30 min |
| Fix jobs auth bug — add Cookie param to _get_admin_user | 1 hour |
| Fix lib/api.ts contract mismatches (ICP list, delete 204, CSV stream) | 2 hours |
| Run full migration on clean DB and verify no errors | 1 hour |
| Manual smoke test — register, ICP build, generate leads, export CSV | 2 hours |

### Phase 2 — Core Missing Features (Days 3–8)

These are the features that complete the basic MVP — the things a paying agency needs to do their job.

| Task | Estimated Time |
| --- | --- |
| Build ICP Builder frontend page — connect to POST /icp/build | 1 day |
| Build Stripe checkout flow — POST /billing/checkout + plan select UI | 2 days |
| Build Stripe webhook handlers — subscription created/updated/cancelled | 0.5 day |
| Build pipeline server persistence — zl_pipeline_stages table + API | 1.5 days |
| Replace pipeline Zustand mock with real server state | 0.5 day |
| Build customers backend — derive from closed pipeline stages | 1 day |
| Fix CSV export frontend — stream download handler | 2 hours |
| Build lead scoring breakdown page — show score components | 1 day |

### Phase 3 — Search & RAG Layer (Days 9–12)

This phase builds the intelligent retrieval system that makes Zentro Leads feel like magic to users.

| Task | Estimated Time |
| --- | --- |
| Set up Elasticsearch — Docker service + mapping for leads index | 0.5 day |
| Build Elasticsearch indexing — index every lead on create/update | 0.5 day |
| Build Elasticsearch search endpoint — fast filtered lead queries | 0.5 day |
| Set up Pinecone — account, index, dimension config (1536 for text-embedding-3-small) | 0.5 day |
| Build embedding generation — embed each lead description on persist | 0.5 day |
| Build Pinecone upsert pipeline — store embeddings with metadata filters | 0.5 day |
| Build hybrid search merger — combine PostgreSQL + ES + Pinecone results | 1 day |
| Build re-ranker — apply final score formula, deduplicate, sort | 0.5 day |
| Update NL search endpoint — route through hybrid merger | 0.5 day |
| Test semantic search — 'give me motor insurance leads in KL aged 25-40' | 0.5 day |

### Phase 4 — AI Model Optimization (Days 11–13)

Replace Claude-for-everything with the right model for each task, reducing cost and increasing speed.

| Task | Estimated Time |
| --- | --- |
| Add OPENAI_API_KEY to config + environment | 30 min |
| Move outreach draft generation from Claude to GPT-4o Mini | 2 hours |
| Move lead scoring explanation from Claude to GPT-4o Mini | 2 hours |
| Add GOOGLE_GEMINI_API_KEY to config | 30 min |
| Build Gemini Flash-Lite bulk industry normalization pipeline | 1 day |
| Add XGBoost model training pipeline — train on scoring feedback data | 1 day |
| Replace deterministic rule engine with XGBoost inference | 0.5 day |
| Build MLflow experiment tracking — log model versions and performance | 0.5 day |

### Phase 5 — B2C Pipeline (Days 13–15)

This phase adds the individual insurance lead capability — the biggest competitive differentiator.

| Task | Estimated Time |
| --- | --- |
| Design B2C person schema — add life_event, age, income_bracket, vehicle fields | 0.5 day |
| Build B2C ICP template — individual insurance mode in ICP Builder | 0.5 day |
| Build JPJ vehicle signal scraper (Malaysia) — new car registrations | 1 day |
| Build NAPIC property signal scraper (Malaysia) — property transactions | 1 day |
| Build Vaahan vehicle signal scraper (India) — new vehicle registrations | 1 day |
| Build social signal detector — Facebook/Instagram life event keyword scan | 1 day |
| Build B2C scoring model — separate XGBoost model for individual leads | 0.5 day |
| Build B2C lead card UI — different display format from B2B cards | 0.5 day |
| Test full B2C pipeline — signal → enrich → score → display | 0.5 day |

### Phase 6 — Outreach & Nurturing (Days 15–16)

| Task | Estimated Time |
| --- | --- |
| Build WhatsApp template generator — Malaysia (BM + EN) and India (EN + Hindi) | 0.5 day |
| Build email sequence generator — 5-touch outreach sequence per lead type | 0.5 day |
| Build SendGrid email integration — send outreach emails from platform | 0.5 day |
| Build Twilio WhatsApp integration — send WhatsApp from platform | 0.5 day |
| Build re-scoring cron job — re-score leads monthly, alert on score increase | 0.5 day |
| Build Google Sheets export — connect to Sheets API, create export function | 1 day |

### Phase 7 — DevOps & Quality (Days 16+)

| Task | Estimated Time |
| --- | --- |
| Add proxy.ts auth guard — replace server-layout-only auth | 0.5 day |
| Set up GitHub Actions CI/CD — build + lint + test + deploy pipeline | 0.5 day |
| Set up staging environment — separate .env.staging, Railway staging service | 0.5 day |
| Configure Cloudflare DNS for zentrointelligence.com | 0.5 day |
| Write pytest unit tests for critical backend paths | 1.5 days |
| Write Playwright smoke tests — register → ICP → generate → export flow | 1 day |
| Set up error monitoring — Sentry integration (backend + frontend) | 0.5 day |
| Set up uptime monitoring — basic health check alerts | 0.5 day |
| Performance test — simulate 50 concurrent lead generation requests | 0.5 day |

### Phase 8 — Knowledge Base AI Layer (Ongoing)

This phase builds the AI layer that uses the Zentro Leads knowledge base to power smarter features — not by storing books, but by encoding our own distilled frameworks into the system.

| Task | Description |
| --- | --- |
| ICP Knowledge Vectors | Embed all B2B and B2C ICP frameworks into Pinecone as context for ICP Builder |
| Signal Library | Build a structured library of 50+ insurance intent signals with weights |
| Outreach Template Bank | Build 30+ outreach templates across languages, channels, and insurance types |
| Scoring Feedback Loop | Use agency conversion data to continuously retrain XGBoost model |
| Market Context Embeddings | Embed Malaysia and India market knowledge for better lead enrichment |
| ICP Similarity Engine | Find leads similar to an agency's existing best clients using vector similarity |
| Objection Handler | AI module that suggests responses to common insurance objection patterns |
| Lead Decay Model | Model that predicts how fast a lead's intent expires by signal type |

## Section 6 — Implementation Timeline

### 16-Day MVP Sprint

| Days | Phase | Deliverable |
| --- | --- | --- |
| Days 1–2 | Phase 1: Bug Fixes | All 7 critical blockers resolved, clean DB migration |
| Days 3–5 | Phase 2a: ICP + Billing | ICP Builder page live, Stripe checkout working |
| Days 5–8 | Phase 2b: Pipeline + Customers | Pipeline server-synced, customers from real DB |
| Days 9–10 | Phase 3a: Elasticsearch | Fast lead filtering working via ES |
| Days 10–12 | Phase 3b: Pinecone + RAG | Semantic search working, hybrid merger live |
| Days 11–13 | Phase 4: AI Models | GPT-4o Mini + Gemini + XGBoost all wired |
| Days 13–15 | Phase 5: B2C Pipeline | JPJ + NAPIC + Vaahan scrapers + B2C lead cards |
| Days 15–16 | Phase 6: Outreach | WhatsApp + email templates + Sheets export |
| Day 16+ | Phase 7: DevOps | CI/CD, staging, tests, monitoring |

### Post-MVP Roadmap

| Timeline | Milestone |
| --- | --- |
| Month 1 | 10 paying insurance agencies onboarded (ZIMS base) |
| Month 2 | 1,000 leads generated, first conversion data for ML training |
| Month 3 | XGBoost model retrained on real conversion feedback |
| Month 4 | B2C pipeline fully live with JPJ + NAPIC signals |
| Month 5 | India market launch — IndiaMART + Vaahan + JustDial |
| Month 6 | 50 paying agencies, RM 15,000+ MRR |
| Month 7 | Finance & loan vertical — Phase 2 expansion begins |
| Month 12 | Southeast Asia expansion — Singapore, Indonesia |

### Missing API Keys — Priority Order

Add these keys in this order, testing after each one:

| Priority | Key & What It Unlocks |
| --- | --- |
| #1 — Add Now | GOOGLE_SEARCH_CX — Complete Google Custom Search for web lead discovery |
| #2 — Add Now | OPENAI_API_KEY — GPT-4o Mini outreach drafts + text-embedding-3-small for Pinecone |
| #3 — Week 2 | PINECONE_API_KEY — Vector similarity search (after embedding code is written) |
| #4 — Week 2 | ELASTICSEARCH_URL — Full-text search (after ES Docker service added) |
| #5 — Week 3 | GOOGLE_GEMINI_API_KEY — Bulk normalization (after Gemini code is written) |
| #6 — Week 3 | XGBOOST_MODEL_PATH — ML scoring (after training pipeline is built) |
| #7 — Week 4 | STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET — Billing checkout |
| #8 — Week 4 | SENDGRID_API_KEY — Email outreach from platform |
| #9 — Week 5 | TWILIO_* — WhatsApp outreach from platform |
