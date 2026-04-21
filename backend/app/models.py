"""
Zentro Leads — All database models (zl_* prefix)
Complete schema covering all 64 planned features.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, Enum, JSON, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════

class PlanTier(str, enum.Enum):
    FREE    = "free"
    STARTER = "starter"
    GROWTH  = "growth"
    PRO     = "pro"
    AGENCY  = "agency"


class LeadStatus(str, enum.Enum):
    NEW        = "new"
    CONTACTED  = "contacted"
    REPLIED    = "replied"
    MEETING    = "meeting"
    CLOSED     = "closed"
    LOST       = "lost"
    SUPPRESSED = "suppressed"


class LeadTier(str, enum.Enum):
    HOT       = "hot"        # score >= 85
    WARM      = "warm"       # score 60-84
    POTENTIAL = "potential"  # score 40-59
    COLD      = "cold"       # score < 40


class LeadSource(str, enum.Enum):
    GOOGLE_MAPS   = "google_maps"
    GOOGLE_SEARCH = "google_search"
    WEBSITE       = "website"
    LINKEDIN      = "linkedin"
    JOB_BOARD     = "job_board"
    GOVERNMENT    = "government"
    NEWS          = "news"
    LANDING_PAGE  = "landing_page"
    BROADCAST     = "broadcast"
    REFERRAL      = "referral"
    MANUAL        = "manual"
    INTERNAL_DB   = "internal_db"


class OutreachChannel(str, enum.Enum):
    EMAIL    = "email"
    WHATSAPP = "whatsapp"
    SMS      = "sms"
    LINKEDIN = "linkedin"


class OutreachStatus(str, enum.Enum):
    PENDING   = "pending"
    SENT      = "sent"
    DELIVERED = "delivered"
    OPENED    = "opened"
    REPLIED   = "replied"
    BOUNCED   = "bounced"
    FAILED    = "failed"


class CampaignType(str, enum.Enum):
    PROMOTION   = "promotion"
    FOLLOW_UP   = "follow_up"
    FESTIVE     = "festive"
    RE_ENGAGE   = "re_engage"
    REFERRAL    = "referral"
    EVENT       = "event"
    RENEWAL     = "renewal"


class ContentPlatform(str, enum.Enum):
    INSTAGRAM = "instagram"
    FACEBOOK  = "facebook"
    LINKEDIN  = "linkedin"
    WHATSAPP  = "whatsapp"
    YOUTUBE   = "youtube"
    TIKTOK    = "tiktok"


class ContentType(str, enum.Enum):
    POST        = "post"
    CAPTION     = "caption"
    REEL_SCRIPT = "reel_script"
    STORY       = "story"
    AD_COPY     = "ad_copy"
    BROADCAST   = "broadcast"


# ═══════════════════════════════════════════════════════════════
# zl_users
# ═══════════════════════════════════════════════════════════════

class ZLUser(Base):
    """Main user account for Zentro Leads."""
    __tablename__ = "zl_users"

    id             = Column(String, primary_key=True, default=gen_id)
    email          = Column(String, unique=True, nullable=False, index=True)
    hashed_password= Column(String, nullable=False)
    full_name      = Column(String, nullable=False)
    company_name   = Column(String)
    phone          = Column(String)
    avatar_url     = Column(String)

    # Plan & usage
    plan                   = Column(Enum(PlanTier), default=PlanTier.FREE, nullable=False)
    leads_used_this_month  = Column(Integer, default=0, nullable=False)
    leads_limit            = Column(Integer, default=25, nullable=False)

    # Stripe
    stripe_customer_id     = Column(String, unique=True)
    stripe_subscription_id = Column(String, unique=True)
    billing_status         = Column(String, default="inactive")

    # ZIMS Integration
    zims_linked    = Column(Boolean, default=False)
    zims_agency_id = Column(String)
    zims_api_key   = Column(String)

    # Settings
    digest_enabled      = Column(Boolean, default=True)
    sms_outreach_enabled= Column(Boolean, default=False)
    timezone            = Column(String, default="Asia/Kuala_Lumpur")

    # Status
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at  = Column(DateTime(timezone=True))

    # Relationships
    icps          = relationship("ZLICP",         back_populates="user", cascade="all, delete-orphan")
    leads         = relationship("ZLLead",         back_populates="user", cascade="all, delete-orphan")
    team_members  = relationship("ZLTeamMember",   back_populates="user", cascade="all, delete-orphan")
    exports       = relationship("ZLExport",        back_populates="user", cascade="all, delete-orphan")
    campaigns     = relationship("ZLCampaign",      back_populates="user", cascade="all, delete-orphan")
    landing_pages = relationship("ZLLandingPage",   back_populates="user", cascade="all, delete-orphan")
    content_items = relationship("ZLContentItem",   back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("ZLNotification",  back_populates="user", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════
# zl_team_members
# ═══════════════════════════════════════════════════════════════

class ZLTeamMember(Base):
    """Team members under a user account."""
    __tablename__ = "zl_team_members"

    id         = Column(String, primary_key=True, default=gen_id)
    user_id    = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    email      = Column(String, nullable=False)
    full_name  = Column(String, nullable=False)
    role       = Column(String, default="agent")  # admin / agent
    is_active  = Column(Boolean, default=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    joined_at  = Column(DateTime(timezone=True))

    user = relationship("ZLUser", back_populates="team_members")


# ═══════════════════════════════════════════════════════════════
# zl_icps
# ═══════════════════════════════════════════════════════════════

class ZLICP(Base):
    """Ideal Customer Profile — AI-generated from one sentence."""
    __tablename__ = "zl_icps"

    id          = Column(String, primary_key=True, default=gen_id)
    user_id     = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    name        = Column(String, nullable=False)
    description = Column(Text)  # original user input

    # AI-generated profile
    industries      = Column(JSON, default=list)
    job_titles      = Column(JSON, default=list)
    seniority_levels= Column(JSON, default=list)
    company_sizes   = Column(JSON, default=list)
    locations       = Column(JSON, default=list)
    keywords        = Column(JSON, default=list)
    intent_signals  = Column(JSON, default=list)
    search_queries  = Column(JSON, default=list)  # Generated by Claude

    # Performance tracking
    total_leads_generated = Column(Integer, default=0)
    total_converted       = Column(Integer, default=0)
    conversion_rate       = Column(Float, default=0.0)

    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user  = relationship("ZLUser",  back_populates="icps")
    leads = relationship("ZLLead",  back_populates="icp")

    __table_args__ = (
        Index("ix_zl_icps_user_active", "user_id", "is_active"),
    )


# ═══════════════════════════════════════════════════════════════
# zl_companies
# ═══════════════════════════════════════════════════════════════

class ZLCompany(Base):
    """Scraped company data — our own database."""
    __tablename__ = "zl_companies"

    id           = Column(String, primary_key=True, default=gen_id)
    name         = Column(String, nullable=False, index=True)
    domain       = Column(String, index=True)
    website      = Column(String)
    industry     = Column(String, index=True)
    sub_industry = Column(String)

    # Size & financials
    employee_count = Column(Integer)
    employee_range = Column(String)   # "10-50", "50-200"
    revenue        = Column(String)
    funding_stage  = Column(String)   # "seed", "series_a", etc.
    founded_year   = Column(Integer)

    # Location
    country   = Column(String, index=True)
    state     = Column(String)
    city      = Column(String, index=True)
    address   = Column(Text)
    latitude  = Column(Float)
    longitude = Column(Float)

    # Contact
    phone    = Column(String)
    whatsapp = Column(String)
    email    = Column(String)

    # Social
    linkedin_url  = Column(String)
    facebook_url  = Column(String)
    instagram_url = Column(String)

    # Tech & signals
    tech_stack        = Column(JSON, default=list)
    is_hiring         = Column(Boolean, default=False)
    job_posting_count = Column(Integer, default=0)
    last_funded_at    = Column(DateTime(timezone=True))
    in_the_news       = Column(Boolean, default=False)
    news_summary      = Column(Text)

    # Google Maps meta
    google_maps_id = Column(String, unique=True)
    google_rating  = Column(Float)
    google_reviews = Column(Integer)

    # Data quality
    data_source      = Column(Enum(LeadSource))
    last_verified_at = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    people = relationship("ZLPerson", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_zl_companies_industry_city",    "industry", "city"),
        Index("ix_zl_companies_country_industry", "country",  "industry"),
    )


# ═══════════════════════════════════════════════════════════════
# zl_people
# ═══════════════════════════════════════════════════════════════

class ZLPerson(Base):
    """Decision makers scraped from websites + LinkedIn."""
    __tablename__ = "zl_people"

    id           = Column(String, primary_key=True, default=gen_id)
    company_id   = Column(String, ForeignKey("zl_companies.id"), index=True)
    full_name    = Column(String, nullable=False, index=True)
    first_name   = Column(String)
    last_name    = Column(String)
    job_title    = Column(String, index=True)
    seniority    = Column(String)    # "c-level", "director", "manager", "individual"
    department   = Column(String)

    # Contact
    email            = Column(String, index=True)
    email_verified   = Column(Boolean, default=False)
    email_confidence = Column(Float, default=0.0)
    email_source     = Column(String)  # "smtp", "pattern", "website"
    phone            = Column(String)
    whatsapp         = Column(String)

    # LinkedIn
    linkedin_url      = Column(String)
    linkedin_id       = Column(String)
    linkedin_activity = Column(Text)
    recent_posts      = Column(JSON, default=list)

    # Job change detection
    job_changed_at    = Column(DateTime(timezone=True))
    previous_title    = Column(String)
    previous_company  = Column(String)

    # Data quality
    data_source      = Column(Enum(LeadSource))
    last_verified_at = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("ZLCompany", back_populates="people")
    leads   = relationship("ZLLead",   back_populates="person")


# ═══════════════════════════════════════════════════════════════
# zl_leads
# ═══════════════════════════════════════════════════════════════

class ZLLead(Base):
    """A lead generated for a specific user from their ICP."""
    __tablename__ = "zl_leads"

    id          = Column(String, primary_key=True, default=gen_id)
    user_id     = Column(String, ForeignKey("zl_users.id"),    nullable=False, index=True)
    icp_id      = Column(String, ForeignKey("zl_icps.id"),     index=True)
    person_id   = Column(String, ForeignKey("zl_people.id"),   index=True)
    company_id  = Column(String, ForeignKey("zl_companies.id"),index=True)
    assigned_to = Column(String, ForeignKey("zl_team_members.id"))

    # Score (100-point system)
    lead_score      = Column(Integer, default=0, index=True)
    lead_tier       = Column(Enum(LeadTier), default=LeadTier.COLD, index=True)
    score_breakdown = Column(JSON, default=dict)
    # e.g. {"company_size": 30, "role": 25, "industry": 20, "signals": 15, "email": 10}

    # Intent signals detected
    intent_signals  = Column(JSON, default=list)
    # e.g. ["hiring", "funded", "expanding", "job_change", "in_the_news"]

    # Status pipeline
    status         = Column(Enum(LeadStatus), default=LeadStatus.NEW, index=True)
    source         = Column(Enum(LeadSource))

    # AI-generated outreach
    ai_whatsapp_msg  = Column(Text)
    ai_email_subject = Column(String)
    ai_email_body    = Column(Text)
    ai_linkedin_note = Column(Text)
    ai_sms_message   = Column(Text)

    # Outreach tracking
    outreach_sent    = Column(Boolean, default=False)
    last_outreach_at = Column(DateTime(timezone=True))
    outreach_channel = Column(Enum(OutreachChannel))
    linkedin_status  = Column(String)

    # Behavioral signals (tracking pixel + UTM)
    email_opened    = Column(Boolean, default=False)
    email_opened_at = Column(DateTime(timezone=True))
    link_clicked    = Column(Boolean, default=False)
    link_clicked_at = Column(DateTime(timezone=True))
    page_visited    = Column(Boolean, default=False)
    page_visited_at = Column(DateTime(timezone=True))

    # CRM fields
    notes          = Column(Text)
    follow_up_date = Column(DateTime(timezone=True))

    # ZIMS sync
    zims_lead_id   = Column(String)
    zims_pushed_at = Column(DateTime(timezone=True))

    # Data freshness
    last_verified_at = Column(DateTime(timezone=True))
    is_stale         = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user    = relationship("ZLUser",       back_populates="leads")
    icp     = relationship("ZLICP",        back_populates="leads")
    person  = relationship("ZLPerson",     back_populates="leads")
    company = relationship("ZLCompany")
    history = relationship("ZLLeadHistory",back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_zl_leads_user_tier",   "user_id", "lead_tier"),
        Index("ix_zl_leads_user_status", "user_id", "status"),
        Index("ix_zl_leads_user_score",  "user_id", "lead_score"),
    )


# ═══════════════════════════════════════════════════════════════
# zl_lead_history
# ═══════════════════════════════════════════════════════════════

class ZLLeadHistory(Base):
    """Full activity timeline per lead."""
    __tablename__ = "zl_lead_history"

    id         = Column(String, primary_key=True, default=gen_id)
    lead_id    = Column(String, ForeignKey("zl_leads.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    # "status_change", "note_added", "outreach_sent", "email_opened",
    # "link_clicked", "score_updated", "zims_pushed", "assigned"
    old_value  = Column(String)
    new_value  = Column(String)
    note       = Column(Text)
    created_by = Column(String)  # user_id or "system"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("ZLLead", back_populates="history")


# ═══════════════════════════════════════════════════════════════
# zl_suppression_list
# ═══════════════════════════════════════════════════════════════

class ZLSuppressionList(Base):
    """Emails/domains to never show as leads."""
    __tablename__ = "zl_suppression_list"

    id          = Column(String, primary_key=True, default=gen_id)
    user_id     = Column(String, ForeignKey("zl_users.id"), index=True)
    # user_id=NULL means global suppression
    value       = Column(String, nullable=False, index=True)
    # Can be email or domain
    value_type  = Column(String, default="email")  # "email" or "domain"
    reason      = Column(String)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_zl_suppression_user_value", "user_id", "value"),
    )


# ═══════════════════════════════════════════════════════════════
# zl_scoring_feedback
# ═══════════════════════════════════════════════════════════════

class ZLScoringFeedback(Base):
    """Self-learning: records what actually converted for score re-weighting."""
    __tablename__ = "zl_scoring_feedback"

    id                  = Column(String, primary_key=True, default=gen_id)
    user_id             = Column(String, ForeignKey("zl_users.id"), index=True)
    lead_id             = Column(String, ForeignKey("zl_leads.id"), index=True)
    original_score      = Column(Integer)
    original_breakdown  = Column(JSON)
    converted           = Column(Boolean, default=False)
    conversion_value    = Column(Float)
    feedback_signal     = Column(String)
    # "closed_in_zims", "manually_marked", "replied_to_outreach"
    recorded_at         = Column(DateTime(timezone=True), server_default=func.now())


# ═══════════════════════════════════════════════════════════════
# zl_exports
# ═══════════════════════════════════════════════════════════════

class ZLExport(Base):
    """Track all lead exports per user."""
    __tablename__ = "zl_exports"

    id           = Column(String, primary_key=True, default=gen_id)
    user_id      = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    export_type  = Column(String, nullable=False)
    # "csv", "google_sheets", "webhook", "zims"
    lead_count   = Column(Integer, default=0)
    file_url     = Column(String)
    sheets_url   = Column(String)
    filters_used = Column(JSON)
    status       = Column(String, default="pending")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("ZLUser", back_populates="exports")


# ═══════════════════════════════════════════════════════════════
# zl_campaigns (WhatsApp broadcasts)
# ═══════════════════════════════════════════════════════════════

class ZLCampaign(Base):
    """WhatsApp broadcast campaigns."""
    __tablename__ = "zl_campaigns"

    id             = Column(String, primary_key=True, default=gen_id)
    user_id        = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    name           = Column(String, nullable=False)
    campaign_type  = Column(Enum(CampaignType))
    message        = Column(Text, nullable=False)
    channel        = Column(Enum(OutreachChannel), default=OutreachChannel.WHATSAPP)

    # Scheduling
    status         = Column(String, default="draft")
    # "draft", "scheduled", "sending", "sent", "failed"
    scheduled_at   = Column(DateTime(timezone=True))
    sent_at        = Column(DateTime(timezone=True))

    # Stats
    total_contacts = Column(Integer, default=0)
    sent_count     = Column(Integer, default=0)
    delivered_count= Column(Integer, default=0)
    replied_count  = Column(Integer, default=0)
    failed_count   = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user      = relationship("ZLUser",            back_populates="campaigns")
    contacts  = relationship("ZLCampaignContact", back_populates="campaign", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════
# zl_campaign_contacts
# ═══════════════════════════════════════════════════════════════

class ZLCampaignContact(Base):
    """Individual contacts within a broadcast campaign."""
    __tablename__ = "zl_campaign_contacts"

    id          = Column(String, primary_key=True, default=gen_id)
    campaign_id = Column(String, ForeignKey("zl_campaigns.id"), nullable=False, index=True)
    name        = Column(String)
    phone       = Column(String)
    email       = Column(String)
    status      = Column(Enum(OutreachStatus), default=OutreachStatus.PENDING)
    sent_at     = Column(DateTime(timezone=True))
    replied_at  = Column(DateTime(timezone=True))
    reply_text  = Column(Text)
    became_lead = Column(Boolean, default=False)
    lead_id     = Column(String, ForeignKey("zl_leads.id"))

    campaign = relationship("ZLCampaign", back_populates="contacts")


# ═══════════════════════════════════════════════════════════════
# zl_landing_pages
# ═══════════════════════════════════════════════════════════════

class ZLLandingPage(Base):
    """Public lead capture pages at page.zentro-leads.io/slug"""
    __tablename__ = "zl_landing_pages"

    id           = Column(String, primary_key=True, default=gen_id)
    user_id      = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    slug         = Column(String, unique=True, nullable=False, index=True)
    template     = Column(String, default="minimal")
    # "minimal", "bold", "trust"

    # Page content
    headline     = Column(String)
    subheadline  = Column(String)
    services     = Column(JSON, default=list)
    whatsapp_num = Column(String)
    photo_url    = Column(String)
    brand_color  = Column(String, default="#3B6FFF")

    # Stats
    views          = Column(Integer, default=0)
    leads_captured = Column(Integer, default=0)

    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("ZLUser", back_populates="landing_pages")


# ═══════════════════════════════════════════════════════════════
# zl_content_items
# ═══════════════════════════════════════════════════════════════

class ZLContentItem(Base):
    """AI-generated content pieces saved per user."""
    __tablename__ = "zl_content_items"

    id           = Column(String, primary_key=True, default=gen_id)
    user_id      = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    platform     = Column(Enum(ContentPlatform))
    content_type = Column(Enum(ContentType))
    content      = Column(Text, nullable=False)
    hashtags     = Column(JSON, default=list)
    icp_id       = Column(String, ForeignKey("zl_icps.id"))

    # Performance (if posted)
    posted_at    = Column(DateTime(timezone=True))
    views        = Column(Integer, default=0)
    clicks       = Column(Integer, default=0)
    leads_from   = Column(Integer, default=0)

    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("ZLUser", back_populates="content_items")


# ═══════════════════════════════════════════════════════════════
# zl_notifications
# ═══════════════════════════════════════════════════════════════

class ZLNotification(Base):
    """In-app notifications for users."""
    __tablename__ = "zl_notifications"

    id         = Column(String, primary_key=True, default=gen_id)
    user_id    = Column(String, ForeignKey("zl_users.id"), nullable=False, index=True)
    type       = Column(String, nullable=False)
    # "hot_lead_found", "lead_replied", "page_visited",
    # "broadcast_done", "plan_limit_warning", "zims_synced"
    title      = Column(String, nullable=False)
    body       = Column(Text)
    link       = Column(String)
    is_read    = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("ZLUser", back_populates="notifications")

    __table_args__ = (
        Index("ix_zl_notifications_user_unread", "user_id", "is_read"),
    )
