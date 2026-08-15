# あめ × じゃない方 シーシャオフ会 v6.1

今回の追加:
- Stripe Webhook `/webhook`
- `Stripe-Signature` の署名検証
- `checkout.session.completed` を受信
- `client_reference_id` / metadata の申込IDでSupabaseレコードを特定
- `payment_status == paid` のときだけ `paid` / `paid_at` を更新
- WebhookのDB更新失敗時は500を返し、Stripeの再送対象にする

## Render Environment Variables

以下4つを登録します。

- `STRIPE_SECRET_KEY=sk_test_...`
- `STRIPE_WEBHOOK_SECRET=whsec_...`
- `SUPABASE_URL=https://....supabase.co`
- `SUPABASE_SECRET_KEY=sb_secret_...`

秘密情報はGitHubへアップロードしないでください。

## Stripe Sandbox Webhook

Endpoint:
`https://shisha-offkai.onrender.com/webhook`

Listen event:
`checkout.session.completed`

## テスト方法

1. v6.1 をGitHubへアップロードしRenderを再デプロイ
2. Stripe SandboxのWebhook画面で「テストイベントを送信する」
3. Renderログで `POST /webhook ... 200` を確認
4. 実際のテスト申込 → 4,000円Sandbox決済
5. Supabaseで `payment_status = paid` を確認

Webhookを使うため、決済後にユーザーがsuccess画面へ戻らなくても
Stripeから通知を受信できればpaidに更新されます。
