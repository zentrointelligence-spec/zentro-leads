# Architecture

_Source: `Downloads/Zentro_Leads_Master_Knowledge_Base.docx`._

Technical architecture notes for the Zentro Leads platform.

## Section 3 — Full Technical Architecture

### 3.1 System Overview

Zentro Leads uses a five-layer architecture. Each layer has a specific job and communicates with the layers above and below it through well-defined interfaces.

| Architecture Layers<br>Layer 1 — Data Ingestion: Scrape and collect raw lead data from multiple sources<br>Layer 2 — Storage: PostgreSQL (truth), Elasticsearch (search), Pinecone (vectors), Redis (cache)<br>Layer 3 — RAG Intelligence: Intent parsing → hybrid search → re-ranking → lead cards<br>Layer 4 — Presentation: Lead cards, ICP builder UI, pipeline, analytics dashboard<br>Layer 5 — Action: Push to ZIMS, CSV export, Google Sheets, outreach sequence trigger |
| --- |

### 3.2 Data Ingestion Pipeline

The pipeline runs when an insurance agency clicks 'Generate Leads'. It executes these steps in order:

- Google Maps Places API — discovers businesses matching the ICP location + industry
- Playwright web scraper — visits each company website, extracts contact details
- Claude LLM enrichment — infers industry, revenue range, hiring status from website content
- Email pattern generation — creates likely email formats from name + domain
- SMTP email verification — MX lookup + RCPT TO probe to confirm deliverability
- ICP validation — scores how well each lead matches the agency's ICP
- XGBoost scoring — assigns 0–100 lead score using trained ML model
- Deduplication — removes leads already in the agency's database
- PostgreSQL persistence — stores all enriched lead data
- Pinecone embedding — stores vector embedding for semantic search
- Elasticsearch indexing — indexes lead for fast filtered search
### 3.3 Hybrid RAG Architecture

When an agency asks for leads — either through the UI or through natural language search — the system runs a three-path retrieval process and merges the results.

| Search Path | What It Does |
| --- | --- |
| PostgreSQL structured query | Exact filters: industry=manufacturing, size=10-50, location=KL |
| Elasticsearch full-text | Fast keyword search: 'Halal food company HR manager' |
| Pinecone vector search | Semantic similarity: finds leads similar to the agency's best existing clients |

The three result sets are merged, deduplicated, and re-ranked using a final scoring formula:

| Re-Ranking Formula<br>Final Score = (Base XGBoost Score × 0.40)<br>+ (ICP Similarity Match × 0.35)<br>+ (Intent Signal Recency × 0.25)<br>Leads are sorted by Final Score descending and returned as Lead Cards |
| --- |

### 3.4 AI Model Assignment

We use a multi-model approach, assigning each task to the most cost-effective model that can do it well.

| Task | Model | Reason |
| --- | --- | --- |
| ICP Builder | Claude Sonnet | Complex reasoning, structured output |
| Lead scoring explanation | GPT-4o Mini | Simple text, cost-efficient |
| Outreach draft generation | GPT-4o Mini | Template variation, high volume |
| Natural language lead search | Claude Haiku | Fast, cheap intent parsing |
| Bulk industry normalization | Gemini Flash-Lite | Highest volume, lowest cost |
| ICP validation | Claude Sonnet | Nuanced matching logic |
| Lead score model | XGBoost | No API cost, fast inference |
| Embedding generation | text-embedding-3-small | OpenAI, low cost per token |

### 3.5 Database Schema

#### Core Tables

| Table | Purpose |
| --- | --- |
| zl_users | Agency accounts, plan, subscription status |
| zl_companies | Enriched company profiles (B2B leads) |
| zl_people | Individual contacts — B2B decision makers + B2C individuals |
| zl_leads | Lead records linking person + company + score + status |
| zl_icps | Saved ICP profiles per agency user |
| zl_lead_history | Status change audit trail |
| zl_scoring_feedback | Agency feedback on lead quality (ML training data) |
| zl_suppression_list | Do-not-contact records |
| zl_exports | Export history and download links |
| zl_campaigns | Outreach campaign records |
| zl_auto_signals | Intent signal detection results |
| zl_pipeline_stages | Kanban pipeline stages (MISSING — needs to be built) |
| zl_subscriptions | Subscription + plan tracking (MISSING — needs to be built) |
