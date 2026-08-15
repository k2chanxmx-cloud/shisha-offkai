-- v6.2 メール送信管理カラム追加
-- Supabase > SQL Editor で1回だけ実行してください。

alter table public.event_applications
  add column if not exists email_sent_at timestamptz;

alter table public.event_applications
  add column if not exists resend_email_id text;
