"""Additive schema for the career workspace and background delivery worker."""
from sqlalchemy import text

def configure_features(engine):
    statements = [
        """CREATE TABLE IF NOT EXISTS public.application_answer_memory (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            question_key TEXT NOT NULL, question TEXT NOT NULL, answer TEXT NOT NULL,
            source TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id,question_key))""",
        "ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE public.auth_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        "ALTER TABLE public.auth_sessions ADD COLUMN IF NOT EXISTS auth_method TEXT NOT NULL DEFAULT 'password'",
        "ALTER TABLE public.career_job_tracker ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE public.career_job_tracker ADD COLUMN IF NOT EXISTS salary TEXT NOT NULL DEFAULT ''",
        """CREATE TABLE IF NOT EXISTS public.resume_versions (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            name TEXT NOT NULL, filename TEXT NOT NULL, content BYTEA NOT NULL, extracted_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS public.mock_interviews (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            role TEXT NOT NULL, resume_id BIGINT REFERENCES public.resume_versions(id) ON DELETE SET NULL,
            resume_name TEXT NOT NULL, questions JSONB NOT NULL, answers JSONB NOT NULL DEFAULT '{}',
            report JSONB, status TEXT NOT NULL DEFAULT 'In progress',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        "ALTER TABLE public.career_job_tracker ADD COLUMN IF NOT EXISTS resume_id BIGINT REFERENCES public.resume_versions(id) ON DELETE SET NULL",
        """CREATE TABLE IF NOT EXISTS public.career_reminders (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            tracker_id BIGINT REFERENCES public.career_job_tracker(id) ON DELETE CASCADE,
            title TEXT NOT NULL, kind TEXT NOT NULL, due_at TIMESTAMPTZ NOT NULL,
            completed BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS public.interview_practice (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            job_title TEXT NOT NULL, questions JSONB NOT NULL, answers JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS public.job_reports (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL,
            job_id TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL, reason TEXT NOT NULL,
            details TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Open', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS public.employer_reviews (
            domain TEXT PRIMARY KEY, company TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Unverified',
            evidence TEXT NOT NULL DEFAULT '', updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS public.notification_preferences (
            user_id BIGINT PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
            email_digest BOOLEAN NOT NULL DEFAULT FALSE)""",
        """CREATE TABLE IF NOT EXISTS public.email_verifications (
            token_hash TEXT PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS public.mail_outbox (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            subject TEXT NOT NULL, body TEXT NOT NULL, dedupe_key TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending', attempts INT NOT NULL DEFAULT 0,
            next_attempt TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            sent_at TIMESTAMPTZ, last_error TEXT)""",
        """CREATE TABLE IF NOT EXISTS public.worker_runs (
            id BIGSERIAL PRIMARY KEY, started_at TIMESTAMPTZ DEFAULT NOW(), finished_at TIMESTAMPTZ,
            status TEXT NOT NULL DEFAULT 'Running', detail TEXT NOT NULL DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS public.oauth_flows (
            state_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, verifier TEXT NOT NULL,
            link_user_id BIGINT REFERENCES public.users(id) ON DELETE CASCADE,
            expires_at TIMESTAMPTZ NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS public.oauth_identities (
            provider TEXT NOT NULL, subject TEXT NOT NULL, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            PRIMARY KEY(provider, subject), UNIQUE(provider, user_id))""",
        "ALTER TABLE public.worker_runs ADD COLUMN IF NOT EXISTS sources JSONB NOT NULL DEFAULT '{}'",
        """CREATE TABLE IF NOT EXISTS public.saved_searches (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            name TEXT NOT NULL, filters JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
        """CREATE TABLE IF NOT EXISTS public.application_events (
            id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            tracker_id BIGINT NOT NULL REFERENCES public.career_job_tracker(id) ON DELETE CASCADE,
            kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_key TEXT, UNIQUE(tracker_id,event_key))""",
        "CREATE INDEX IF NOT EXISTS application_events_owner_time ON public.application_events(user_id,occurred_at DESC,id DESC)",
        """INSERT INTO public.application_events(user_id,tracker_id,kind,title,body,occurred_at,event_key)
            SELECT u.id,t.id,'baseline','Opportunity saved',
                'Tracking began here. Earlier activity was not recorded.',t.saved_at,'baseline'
            FROM public.career_job_tracker t JOIN public.users u ON t.user_id=u.id::text
            ON CONFLICT(tracker_id,event_key) DO NOTHING""",
        "CREATE INDEX IF NOT EXISTS career_reminders_due ON public.career_reminders(user_id, due_at)",
        "CREATE INDEX IF NOT EXISTS auth_sessions_user ON public.auth_sessions(user_id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
