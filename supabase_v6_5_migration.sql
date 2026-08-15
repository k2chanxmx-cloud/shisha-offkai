-- v6.5 銀行振込対応
-- Supabase > SQL Editor で1回実行してください。

alter table public.event_applications
  add column if not exists bank_transfer_requested_at timestamptz;

alter table public.event_applications
  add column if not exists bank_instruction_sent_at timestamptz;

alter table public.event_applications
  add column if not exists bank_instruction_email_id text;

-- payment_status に bank_transfer_pending を追加
alter table public.event_applications
  drop constraint if exists event_applications_payment_status_check;

alter table public.event_applications
  add constraint event_applications_payment_status_check
  check (
    payment_status in (
      'unpaid',
      'pending',
      'bank_transfer_pending',
      'paid',
      'failed',
      'refunded'
    )
  );
