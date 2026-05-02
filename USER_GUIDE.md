# LeadRadar — Complete User Guide for Insurance Agents

> **Who this is for:** You run an insurance agency selling general insurance, motor insurance, commercial vehicle coverage, workers compensation, fire insurance, and other business policies. You want a steady flow of qualified leads without cold calling random numbers.

---

## Table of Contents

1. [First-Time Setup (5 minutes)](#step-1-first-time-setup)
2. [Build Your Ideal Customer Profile (ICP)](#step-2-build-your-ideal-customer-profile-icp)
3. [Generate Your First Batch of Leads](#step-3-generate-your-first-batch-of-leads)
4. [Understanding Lead Scores & Tiers](#step-4-understanding-lead-scores--tiers)
5. [The Kanban Pipeline — Working Leads](#step-5-the-kanban-pipeline--working-leads)
6. [AI Outreach — WhatsApp & Email](#step-6-ai-outreach--whatsapp--email)
7. [Live Signal Feed — Automatic Detection](#step-7-live-signal-feed--automatic-detection)
8. [Daily Digest — Your Morning Briefing](#step-8-daily-digest--your-morning-briefing)
9. [Best Practices for Insurance Agents](#step-9-best-practices-for-insurance-agents)

---

## Step 1: First-Time Setup

### 1.1 Register & Login

1. Open `https://app.leadradar.io/login`
2. Click **Register** and fill in:
   - Full Name
   - Email
   - Password
   - Company Name (your insurance agency name)
   - Phone (with country code, e.g. `+60123456789`)
3. Click **Create Account**
4. You'll land on the **Dashboard**

### 1.2 Dashboard Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Good morning, Moses!                🟢 All systems op      │
├─────────────────────────────────────────────────────────────┤
│  Total Leads   Hot Leads   Contacted   Conversion Rate      │
│     27           25           3            11%              │
├─────────────────────────────────────────────────────────────┤
│  [Build ICP]  [View Pipeline]                               │
├─────────────────────────────────────────────────────────────┤
│  Pipeline by Stage                    │  Lead Quota         │
│  ████████ New (35%)                   │  27 of 100 used     │
│  ██████ Contacted (25%)               │  ████████░░ 27%     │
│  ████ Replied (20%)                   │  73 remaining       │
│  ██ Meeting (12%)                     │                     │
│  █ Closed (8%)                        │  Live Signal Feed   │
│                                       │  🔥 Tender: ABC...  │
│                                       │  📋 Hiring: XYZ...  │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 2: Build Your Ideal Customer Profile (ICP)

This is the **most important step**. LeadRadar uses your ICP to find the RIGHT companies.

### 2.1 Go to ICP Builder

1. Click **"Build ICP"** on the dashboard
2. Or navigate to `/dashboard/icp`

### 2.2 Describe Your Target in One Sentence

Type a plain English sentence. The AI will translate it into search queries.

**Example for General Insurance (Motor/Fleet):**
> *"Logistics and transport companies in Kuala Lumpur and Selangor with 10-100 employees that own lorries and delivery vans"*

**Example for Construction Insurance:**
> *"Construction contractors and developers in Penang and Johor with site supervisors and heavy equipment"*

**Example for Complete Business Package:**
> *"Manufacturing and warehouse companies in Malaysia with 20-200 workers that need fire insurance and workers compensation"*

### 2.3 Review the AI-Generated Profile

LeadRadar will generate:

| Field | Example Value |
|-------|---------------|
| **Industries** | Logistics, Transport, Freight |
| **Job Titles** | Director, Operations Manager, Fleet Manager |
| **Company Sizes** | 10-50, 50-200 employees |
| **Locations** | Kuala Lumpur, Selangor, Petaling Jaya |
| **Keywords** | fleet, lorry, cargo, commercial vehicle |
| **Search Queries** | "logistics company Kuala Lumpur", "transport company Selangor" |

**Tip:** If the generated profile looks wrong, edit it or write a more specific sentence.

### 2.4 Save the ICP

Click **"Save ICP"**. You can create multiple ICPs:
- ICP #1: Motor/Fleet Insurance
- ICP #2: Construction/Workmanship Insurance
- ICP #3: Complete Business Package

---

## Step 3: Generate Your First Batch of Leads

### 3.1 Start Generation

1. Go to `/dashboard/leads`
2. Click the **"Generate Leads"** button
3. Select your ICP from the dropdown
4. Click **"Start Generation"**

### 3.2 What Happens Behind the Scenes

```
You click "Generate" → 202 Accepted (90 seconds)

LeadRadar does:
  1. Scrapes Google Maps for companies matching your ICP
  2. Visits each company website
  3. Extracts decision maker names & titles
  4. Verifies emails (pattern matching + SMTP check)
  5. Scores each lead 0-100 points
  6. Saves HOT (≥85) and WARM (60-84) leads to your pipeline
  7. Generates AI outreach messages for each lead
```

### 3.3 Watch Them Appear

Leads appear progressively in the **Kanban board** (not all at once). You'll see:
- Company name
- Industry & size
- Decision maker name & title
- Phone number
- Email (with confidence score)
- Lead score & tier
- ICP match %
- **AI-generated WhatsApp message** (click to copy)

---

## Step 4: Understanding Lead Scores & Tiers

Each lead gets a **score out of 100** and a **tier**.

### 4.1 Score Breakdown

| Component | Max Points | What It Means |
|-----------|-----------|---------------|
| **Company Size** | 30 | Matches your ICP size range |
| **Role Fit** | 25 | Decision maker title matches (Director, Manager) |
| **Industry** | 20 | Company is in your target industry |
| **Signals** | 15 | Hiring, funded, in the news, tender win |
| **Email Quality** | 10 | Verified email = higher score |
| **ICP Match Bonus** | +25 | AI validation score ≥90 |
| **Email Pattern Bonus** | +10 | High-confidence pattern email |

### 4.2 Tiers

| Tier | Score | Color | Action |
|------|-------|-------|--------|
| **HOT** 🔥 | 85-100 | Red | Contact TODAY — highest probability |
| **WARM** | 60-84 | Orange | Contact this week — good fit |
| **POTENTIAL** | 40-59 | Yellow | Nurture — follow up later |
| **COLD** | 0-39 | Gray | Low priority |

### 4.3 Example: Why a Lead Scores 100

```
Company: Angkut Logistics Services
Score: 100/100 (HOT)

Breakdown:
  Company Size:    30/30  → "50-200" matches ICP "50-500"
  Role Fit:        25/25  → Director title
  Industry:        10/20  → Logistics (partial match)
  Email:           10/10  → director@angkutlogistics.com (pattern)
  ICP Bonus:      +25     → AI match score 95%
  Email Bonus:    +10     → Confidence 0.85
  ─────────────────────────────
  TOTAL:          100/100
```

---

## Step 5: The Kanban Pipeline — Working Leads

### 5.1 Pipeline Stages

```
┌─────────┐   ┌───────────┐   ┌────────┐   ┌─────────┐   ┌────────┐   ┌──────┐
│   NEW   │ → │ CONTACTED │ → │ REPLIED│ → │ MEETING │ → │ CLOSED │ → │ WON  │
│  (blue) │   │  (amber)  │   │(yellow)│   │(purple) │   │(green) │   │      │
└─────────┘   └───────────┘   └────────┘   └─────────┘   └────────┘   └──────┘
```

### 5.2 Drag & Drop

- Click and drag a lead card from **New** → **Contacted** when you reach out
- Drag to **Replied** when they respond
- Drag to **Meeting** when you book an appointment
- Drag to **Closed** when the deal is done (won or lost)

### 5.3 Lead Card Details

Each card shows:
- **Company name** (e.g., "Fast Cargo Logistics")
- **Industry · Size** (e.g., "Logistics · 50-200")
- **Contact:** Name & phone
- **Email:** Address + confidence bar
- **ICP Match:** Percentage badge
- **Signals:** Hiring, Tender Win, New Registration, etc.
- **Action buttons:** WhatsApp 📱 | Email ✉️ | View 👁️

---

## Step 6: AI Outreach — WhatsApp & Email

### 6.1 AI-Generated Messages

For every HOT/WARM lead, LeadRadar generates:

**WhatsApp Message Example:**
> *Hi Jason, I help logistics companies like Fast Cargo protect their fleet with comprehensive motor insurance. Quick question — when was the last time you reviewed your commercial vehicle coverage?*

**Email Subject Example:**
> *Quick question about Fast Cargo's fleet insurance*

**Email Body Example:**
> *Hi Jason,*
> *
> I noticed Fast Cargo Logistics has been expanding — congratulations on the growth.*
> *
> I'm Moses from [Your Agency]. We specialize in commercial motor insurance for logistics fleets in KL. Most companies I speak with are either underinsured on their lorries or paying 20-30% more than they should.*
> *
> Would you be open to a 10-minute call this week to review your current coverage?*
> *
> Best,*
> *Moses*

### 6.2 How to Send

1. Click the **WhatsApp** button on a lead card
2. This:
   - Logs the outreach in LeadRadar
   - Opens `wa.me/[phone]` in a new tab
   - Pastes the AI message (copy it from the lead drawer)
3. Click the **Email** button to open your mail client

### 6.3 Pro Tips for Insurance Agents

| Situation | Recommended Opening |
|-----------|-------------------|
| Logistics / Fleet | *"When did you last review your lorry insurance coverage?"* |
| Construction | *"Are your subcontractors covered under your current contractor's policy?"* |
| New Company (SSM) | *"Congrats on the new registration — most new businesses miss these 3 insurance requirements..."* |
| Tender Win | *"I saw you won the MRT contract — have you arranged performance bonds and contractor's all-risk insurance yet?"* |
| Hiring Drivers | *"Hiring new lorry drivers? You'll need to update your fleet insurance and employer liability coverage."* |

---

## Step 7: Live Signal Feed — Automatic Detection

This widget on your dashboard shows leads that were **automatically detected** by our monitors — no work required from you.

### 7.1 Types of Signals

| Icon | Source | What It Means | Insurance Need |
|------|--------|---------------|----------------|
| 🔥 **Tender** | Business News | Company won a construction/logistics contract | Performance bond, Contractor's all-risk |
| 📋 **Hiring** | Job Boards | Company hiring drivers, supervisors, safety officers | Fleet, Workmanship, Liability |
| 🆕 **New** | SSM Registry | Newly registered Sdn Bhd | Complete business package |
| ⏰ **Renewal** | Anniversary | Lead is 11 months old | Policy renewal, competitive quote |

### 7.2 How It Works

```
Every 6 hours:
  Tender Monitor scans Malaysian news
  → "ABC Construction wins highway contract"
  → LeadRadar finds ABC Construction in your database
  → Upgrades to HOT + adds "tender_win" signal
  → Appears in your Live Signal Feed

Every 6 hours:
  Job Board Monitor scans Indeed
  → "XYZ Logistics hiring 5 lorry drivers"
  → Finds XYZ Logistics
  → Boosts score +15, adds "hiring_drivers" signal
  → Recommends: "Fleet/Commercial Vehicle Insurance"

Every day at 6 AM:
  SSM Monitor finds new companies
  → Creates WARM lead with score 70
  → Notes: "New company — needs all insurance from scratch"

Every day at 7 AM:
  Renewal Monitor flags old leads
  → Adds "renewal_due" signal
  → Boosts score +15
  → Perfect time for a competitive quote call
```

### 7.3 Click to View Lead

Each signal has a **"View Lead"** link. Click it to open the lead in the pipeline.

---

## Step 8: Daily Digest — Your Morning Briefing

Every morning at **7:30 AM**, you receive:

### WhatsApp Message
```
Good morning Moses! 🌅

📊 LeadRadar Daily Digest
─────────────────────────

🔥 New HOT leads: 3
⚡ Upgraded to HOT: 2
⏰ Renewals due: 1

🎯 Contact today:
1. Fast Cargo Logistics
   📱 +60 13-276 7884
   💡 Hiring lorry drivers — fleet insurance expansion needed

2. Mega Builders Sdn Bhd
   📱 +60 3-2284 6588
   💡 Won highway contract — performance bond needed

3. Angkut Logistics
   📱 +60 10-238 7108
   💡 High-scoring lead

🔗 app.leadradar.io/dashboard
Good luck today! 💪
```

### Email (Same Content + HTML Formatting)

Arrives with subject: **🔥 Your LeadRadar Daily: 3 HOT leads today**

---

## Step 9: Best Practices for Insurance Agents

### 9.1 Weekly Routine

| Day | Action |
|-----|--------|
| **Monday** | Check Daily Digest. Contact top 3 HOT leads. |
| **Tuesday** | Review Live Signal Feed for new tender wins. |
| **Wednesday** | Follow up on leads you contacted last week. |
| **Thursday** | Generate a new ICP batch (different industry). |
| **Friday** | Update pipeline stages. Mark closed deals as WON/LOST. |

### 9.2 ICP Strategy — Rotate Monthly

| Month | ICP Focus | Why |
|-------|-----------|-----|
| Month 1 | Logistics & Transport | Fleet/motor insurance |
| Month 2 | Construction & Developers | Workmanship, liability, bonds |
| Month 3 | Manufacturing & Warehouses | Fire, workers comp, cargo |
| Month 4 | New Sdn Bhd companies | Complete business package |

### 9.3 Follow-Up Cadence

| Day | Action |
|-----|--------|
| Day 0 | WhatsApp with AI-generated message |
| Day 2 | If no reply, send email |
| Day 5 | Call the phone number |
| Day 7 | Final WhatsApp: *"Just following up — happy to answer any questions"* |
| Day 14 | Mark as LOST or move to long-term nurture |

### 9.4 What to Say on the Phone

**For Logistics (Motor/Fleet):**
> *"Hi, I'm Moses from [Agency]. I work with a lot of logistics companies in KL to make sure their lorries are properly covered. Most fleets I see are either underinsured or overpaying. Would you be open to a quick 10-minute review of your current policy?"*

**For Construction (Tender Win):**
> *"Hi, congratulations on winning the highway contract. I'm an insurance specialist — have you arranged your contractor's all-risk and performance bond yet? These are usually required before work starts, and I can get you a quote today."*

**For New Companies:**
> *"Hi, I see your company just registered. Most new business owners don't realize they need these 3 policies from day one: fire insurance, employer liability, and public liability. Can I send you a quick package quote?"*

### 9.5 Export & Share

You can export your leads as CSV:
1. Go to `/dashboard/leads`
2. Click **"Export CSV"**
3. Download `leads-2026-05-02.csv`
4. Open in Excel or share with your team

---

## Quick Reference

| URL | What It Does |
|-----|-------------|
| `app.leadradar.io/login` | Login / Register |
| `app.leadradar.io/dashboard` | Main dashboard with stats & signals |
| `app.leadradar.io/dashboard/icp` | Build your ICP |
| `app.leadradar.io/dashboard/leads` | Kanban pipeline |
| `app.leadradar.io/dashboard/settings` | Update profile & plan |

| Button | Action |
|--------|--------|
| **Build ICP** | Create target customer profile |
| **Generate Leads** | Start AI lead generation |
| **Export CSV** | Download leads spreadsheet |
| **WhatsApp** | Open wa.me with lead's phone |
| **Email** | Open mailto with lead's email |

---

## Need Help?

- **Email:** moses@zentrointelligence.com
- **WhatsApp:** Click any lead's WhatsApp button to test the flow
- **API Status:** `api.leadradar.io/health`
- **Jobs Status:** `api.leadradar.io/api/v1/jobs/status`

---

*Happy selling! 🔥*
