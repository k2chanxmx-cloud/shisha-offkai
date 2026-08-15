# あめ × じゃない方 シーシャオフ会 v6.3

## 今回の変更

Resendの認証済みドメイン `mail.shishaoffkai.com` を使い、
決済完了後に **申込フォームへ入力された参加者本人のメールアドレス**
へ自動メールを送信します。

送信元のデフォルト:

`オフ会受付 <info@mail.shishaoffkai.com>`

## 決済後の流れ

1. Stripe Checkoutで4,000円決済
2. Stripe Webhook `/webhook`
3. Supabaseを `payment_status = paid` に更新
4. 申込者のメールアドレスをSupabaseから取得
5. Resendで参加者本人へ確認メール送信
6. Supabaseへ `email_sent_at` / `resend_email_id` を保存

## Render Environment Variables

必要:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `RESEND_API_KEY`

任意:

- `RESEND_FROM`
  - 未設定時: `オフ会受付 <info@mail.shishaoffkai.com>`

### 不要になった環境変数

`RESEND_TEST_EMAIL_TO`

v6.3では使用しません。Renderから削除して構いません。

## テスト方法

1. v6.3をGitHubへ上書き
2. Render再デプロイ
3. 申込フォームには自分で受信できるメールアドレスを入力
4. Stripe Sandboxで4,000円テスト決済
5. Render Logsで
   - `POST /webhook ... 200`
   - `Payment confirmation email sent`
   を確認
6. フォームに入力したメールアドレスへメールが届くことを確認
7. Supabaseで
   - `payment_status = paid`
   - `email_sent_at` に日時
   - `resend_email_id` に値
   を確認

## 注意

現在Stripeはまだサンドボックスキー `sk_test_...` を使っているため、
決済自体はテストです。
本番公開前にStripe本番キー・本番Webhookへ切り替えてください。
