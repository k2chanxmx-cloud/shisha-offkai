-- Supabase SQL Editor で実行してください。
-- 2026/10/18 シーシャオフ会 申込管理テーブル

create extension if not exists pgcrypto;

create table if not exists public.event_applications (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),

  name text not null,
  handle text not null,
  email text not null,
  phone text not null,
  x_account text,

  age_confirmed boolean not null default false,
  id_required_confirmed boolean not null default false,
  cancellation_confirmed boolean not null default false,
  privacy_confirmed boolean not null default false,

  payment_method text,
  payment_status text not null default 'unpaid'
    check (payment_status in ('unpaid', 'pending', 'paid', 'failed', 'refunded')),

  stripe_checkout_session_id text unique,
  stripe_payment_intent_id text,
  paid_at timestamptz
);

create index if not exists event_applications_created_at_idx
  on public.event_applications (created_at desc);

create index if not exists event_applications_payment_status_idx
  on public.event_applications (payment_status);

-- 個人情報を含むため、ブラウザから直接テーブルを読ませません。
alter table public.event_applications enable row level security;

-- anon / authenticated 向けのRLSポリシーは作成しません。
-- Flask(Render)側だけが SUPABASE_SECRET_KEY を使って操作します。
