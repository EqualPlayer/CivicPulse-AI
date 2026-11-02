
BEGIN;

-- =====================================================
-- 1. CITIZEN AND STAFF PROFILES
-- =====================================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- 2. PROTECTED USER ROLES
-- =====================================================

CREATE TABLE IF NOT EXISTS public.user_roles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'citizen'
        CHECK (role IN ('citizen', 'worker', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================
-- 3. EXTEND EXISTING COMPLAINTS TABLE
-- =====================================================

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS user_id UUID
REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS assigned_to UUID
REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS evidence_path TEXT;

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS current_remark TEXT;

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ;

ALTER TABLE public.civic_reports
ADD COLUMN IF NOT EXISTS legacy_unassigned BOOLEAN NOT NULL DEFAULT FALSE;

-- Normalize existing statuses without deleting reports.

UPDATE public.civic_reports
SET status = CASE LOWER(TRIM(status))
    WHEN 'pending' THEN 'pending'
    WHEN 'under review' THEN 'under_review'
    WHEN 'under_review' THEN 'under_review'
    WHEN 'in progress' THEN 'in_progress'
    WHEN 'in_progress' THEN 'in_progress'
    WHEN 'resolved' THEN 'resolved'
    WHEN 'rejected' THEN 'rejected'
    ELSE 'pending'
END
WHERE status NOT IN (
    'pending', 'under_review', 'in_progress', 'resolved', 'rejected'
);

UPDATE public.civic_reports
SET legacy_unassigned = TRUE
WHERE user_id IS NULL;

ALTER TABLE public.civic_reports
ALTER COLUMN status SET DEFAULT 'pending';

ALTER TABLE public.civic_reports
DROP CONSTRAINT IF EXISTS civic_reports_status_check;

ALTER TABLE public.civic_reports
ADD CONSTRAINT civic_reports_status_check
CHECK (
    status IN (
        'pending',
        'under_review',
        'in_progress',
        'resolved',
        'rejected'
    )
);

-- =====================================================
-- 4. COMPLAINT STATUS HISTORY
-- =====================================================

CREATE TABLE IF NOT EXISTS public.report_status_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    report_id TEXT NOT NULL
        REFERENCES public.civic_reports(id) ON DELETE CASCADE,

    changed_by UUID
        REFERENCES auth.users(id) ON DELETE SET NULL,

    old_status TEXT,

    new_status TEXT NOT NULL
        CHECK (
            new_status IN (
                'pending',
                'under_review',
                'in_progress',
                'resolved',
                'rejected'
            )
        ),

    remark TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Preserve a starting history entry for existing reports.

INSERT INTO public.report_status_history
    (report_id, changed_by, old_status, new_status, remark)

SELECT
    r.id,
    NULL,
    NULL,
    r.status,
    'Legacy report migrated into the CivicPulse status tracking system. Original submitter is not associated with an authenticated account.'

FROM public.civic_reports r

WHERE NOT EXISTS (
    SELECT 1
    FROM public.report_status_history h
    WHERE h.report_id = r.id
);

-- =====================================================
-- 5. AUTOMATIC CITIZEN ROLE ON REGISTRATION
-- =====================================================

CREATE OR REPLACE FUNCTION public.handle_new_civicpulse_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''

AS $$
BEGIN

    INSERT INTO public.profiles (id, display_name)

    VALUES (
        NEW.id,
        COALESCE(
            NULLIF(NEW.raw_user_meta_data ->> 'full_name', ''),
            NULLIF(NEW.raw_user_meta_data ->> 'name', ''),
            NULLIF(SPLIT_PART(COALESCE(NEW.email, ''), '@', 1), ''),
            'CivicPulse citizen'
        )
    )

    ON CONFLICT (id) DO NOTHING;


    INSERT INTO public.user_roles (user_id, role)

    VALUES (NEW.id, 'citizen')

    ON CONFLICT (user_id) DO NOTHING;

    RETURN NEW;

END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created_civicpulse
ON auth.users;

CREATE TRIGGER on_auth_user_created_civicpulse

AFTER INSERT ON auth.users

FOR EACH ROW

EXECUTE FUNCTION public.handle_new_civicpulse_user();

-- Backfill accounts that already existed before this migration.

INSERT INTO public.profiles (id, display_name)

SELECT
    id,
    COALESCE(
        NULLIF(raw_user_meta_data ->> 'full_name', ''),
        NULLIF(raw_user_meta_data ->> 'name', ''),
        NULLIF(SPLIT_PART(COALESCE(email, ''), '@', 1), ''),
        'CivicPulse citizen'
    )

FROM auth.users

ON CONFLICT (id) DO NOTHING;


INSERT INTO public.user_roles (user_id, role)

SELECT id, 'citizen'

FROM auth.users

ON CONFLICT (user_id) DO NOTHING;

-- =====================================================
-- 6. DATABASE INDEXES
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_civic_reports_user_created
ON public.civic_reports(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_civic_reports_assigned
ON public.civic_reports(assigned_to);

CREATE INDEX IF NOT EXISTS idx_civic_reports_status
ON public.civic_reports(status);

CREATE INDEX IF NOT EXISTS idx_report_history_report_created
ON public.report_status_history(report_id, created_at DESC);

-- =====================================================
-- 7. PRIVATE PHOTOGRAPHIC EVIDENCE STORAGE
-- =====================================================

INSERT INTO storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)

VALUES (
    'civic-evidence',
    'civic-evidence',
    FALSE,
    8388608,
    ARRAY['image/jpeg', 'image/png', 'image/webp']
)

ON CONFLICT (id)

DO UPDATE SET
    public = FALSE,
    file_size_limit = 8388608,
    allowed_mime_types = ARRAY[
        'image/jpeg',
        'image/png',
        'image/webp'
    ];

-- =====================================================
-- 8. SECURITY: ENABLE ROW LEVEL SECURITY
-- =====================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.civic_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_status_history ENABLE ROW LEVEL SECURITY;

-- Deny direct browser access to protected records.
-- The Python backend uses its server-side secret key.

REVOKE ALL ON TABLE public.profiles FROM anon, authenticated;
REVOKE ALL ON TABLE public.user_roles FROM anon, authenticated;
REVOKE ALL ON TABLE public.civic_reports FROM anon, authenticated;
REVOKE ALL ON TABLE public.report_status_history FROM anon, authenticated;

GRANT ALL ON TABLE public.profiles TO service_role;
GRANT ALL ON TABLE public.user_roles TO service_role;
GRANT ALL ON TABLE public.civic_reports TO service_role;
GRANT ALL ON TABLE public.report_status_history TO service_role;

COMMIT;
