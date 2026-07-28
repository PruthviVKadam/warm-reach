PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    domain TEXT,
    careers_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resume_versions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    file_path TEXT,
    checksum TEXT,
    active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    company TEXT NOT NULL,
    job_title TEXT,
    job_id TEXT,
    location TEXT,
    careers_url TEXT,
    application_date TEXT,
    status TEXT NOT NULL DEFAULT 'submitted',
    resume_version_id TEXT REFERENCES resume_versions(id),
    source_email_id TEXT,
    application_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recruiters (
    id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES companies(id),
    name TEXT NOT NULL,
    role TEXT,
    location TEXT,
    public_email TEXT,
    linkedin_url TEXT,
    team TEXT,
    experience TEXT,
    hiring_area TEXT,
    source_url TEXT,
    score INTEGER,
    score_explanation TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, name, role, linkedin_url)
);

CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    application_id TEXT REFERENCES applications(id),
    recruiter_id TEXT REFERENCES recruiters(id),
    gmail_message_id TEXT UNIQUE,
    direction TEXT NOT NULL,
    email_type TEXT NOT NULL,
    subject TEXT,
    body_preview TEXT,
    draft_body TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    resume_version_id TEXT REFERENCES resume_versions(id),
    sent_at TEXT,
    received_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS replies (
    id TEXT PRIMARY KEY,
    email_id TEXT REFERENCES emails(id),
    recruiter_id TEXT REFERENCES recruiters(id),
    application_id TEXT REFERENCES applications(id),
    gmail_message_id TEXT UNIQUE,
    subject TEXT,
    body_preview TEXT,
    received_at TEXT,
    sentiment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS followups (
    id TEXT PRIMARY KEY,
    application_id TEXT REFERENCES applications(id),
    recruiter_id TEXT REFERENCES recruiters(id),
    email_id TEXT REFERENCES emails(id),
    followup_type TEXT NOT NULL,
    due_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'suggested',
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(application_id, recruiter_id, followup_type)
);

CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    application_id TEXT REFERENCES applications(id),
    recruiter_id TEXT REFERENCES recruiters(id),
    note TEXT NOT NULL,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    recruiter_id TEXT REFERENCES recruiters(id),
    company_id TEXT REFERENCES companies(id),
    application_id TEXT REFERENCES applications(id),
    relationship_type TEXT NOT NULL,
    strength INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timeline (
    id TEXT PRIMARY KEY,
    application_id TEXT REFERENCES applications(id),
    event_key TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    event_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS embeddings_queue (
    id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,
    source_id TEXT NOT NULL,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_table, source_id)
);

CREATE TABLE IF NOT EXISTS referral_contacts (
    id TEXT PRIMARY KEY,
    contact_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT,
    organization TEXT,
    relationship_context TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referral_asks (
    id TEXT PRIMARY KEY,
    referral_key TEXT NOT NULL UNIQUE,
    contact_id TEXT NOT NULL REFERENCES referral_contacts(id),
    company TEXT,
    opportunity TEXT,
    ask_context TEXT,
    status TEXT NOT NULL DEFAULT 'planned',
    draft_subject TEXT,
    draft_body TEXT,
    sent_at TEXT,
    replied_at TEXT,
    next_followup_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referral_activity (
    id TEXT PRIMARY KEY,
    referral_ask_id TEXT NOT NULL REFERENCES referral_asks(id),
    activity_key TEXT NOT NULL UNIQUE,
    activity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    details_json TEXT,
    event_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS referral_reply_candidates (
    id TEXT PRIMARY KEY,
    candidate_key TEXT NOT NULL UNIQUE,
    referral_ask_id TEXT NOT NULL REFERENCES referral_asks(id),
    gmail_message_id TEXT,
    from_email TEXT NOT NULL,
    subject TEXT,
    body_preview TEXT,
    received_at TEXT,
    match_score INTEGER NOT NULL,
    match_confidence TEXT NOT NULL,
    match_reasons_json TEXT NOT NULL DEFAULT '[]',
    review_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_applications_company ON applications(company);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_recruiters_company ON recruiters(company_id);
CREATE INDEX IF NOT EXISTS idx_emails_application ON emails(application_id);
CREATE INDEX IF NOT EXISTS idx_followups_due ON followups(due_at, status);
CREATE INDEX IF NOT EXISTS idx_timeline_application ON timeline(application_id, event_time);
CREATE INDEX IF NOT EXISTS idx_referral_asks_status ON referral_asks(status, next_followup_at);
CREATE INDEX IF NOT EXISTS idx_referral_asks_contact ON referral_asks(contact_id);
CREATE INDEX IF NOT EXISTS idx_referral_activity_ask ON referral_activity(referral_ask_id, event_time);
CREATE INDEX IF NOT EXISTS idx_referral_reply_candidates_ask ON referral_reply_candidates(referral_ask_id);
CREATE INDEX IF NOT EXISTS idx_referral_reply_candidates_review ON referral_reply_candidates(review_status, match_score);
