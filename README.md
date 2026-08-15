# あめ × じゃない方 シーシャオフ会 v6.2

## 今回の追加

Stripe Webhookで決済成功後、

1. Supabaseを `paid` に更新
2. 申込情報を取得
3. Resendで決済完了メールを送信
4. `email_sent_at` / `resend_email_id` をSupabaseへ保存

まで自動処理します。

現在は独自ドメインがないため、Resendのテスト送信です。
`onboarding@resend.dev` から、Resendアカウントに登録した
自分のメールアドレスだけへ送信します。

## 先にSupabaseで実行

`supabase_v6_2_migration.sql` をSQL Editorで実行してください。

追加される列:

- `email_sent_at`
- `resend_email_id`

## Render Environment Variables

既存:
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `RESEND_API_KEY`

今回追加:
- `RESEND_TEST_EMAIL_TO`
  - Resendアカウントに登録した自分のメールアドレス

任意:
- `RESEND_FROM`
  - 未設定なら `オフ会受付 <onboarding@resend.dev>`

## テスト

1. v6.2をGitHubへ上書き
2. Render再デプロイ
3. 新しく参加申込
4. Stripe Sandboxで4,000円決済
5. Render Logsで以下を確認
   - `POST /webhook ... 200`
   - `Payment confirmation email sent`
6. 自分のメール受信箱を確認
7. Supabaseで
   - `payment_status = paid`
   - `email_sent_at` に日時
   - `resend_email_id` にID
   を確認

ResendのIdempotency-Keyも付けているので、
Webhook再送による重複メールを抑止します。
