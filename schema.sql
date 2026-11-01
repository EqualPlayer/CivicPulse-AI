-- Run this in Supabase SQL Editor if you want the hosted PostgreSQL database.
-- Keep SUPABASE_SERVICE_ROLE_KEY on the Python server only; never expose it in browser code.
create table if not exists public.civic_reports (
  id text primary key,
  category text not null,
  severity text not null,
  confidence double precision not null,
  image_observation text not null,
  location text not null,
  user_description text,
  recommended_department text not null,
  complaint_title text not null,
  complaint_body text not null,
  language text not null,
  status text not null,
  created_at timestamptz not null,
  provider text not null
);
