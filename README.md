# あめ × じゃない方 シーシャオフ会 v6

今回の追加:
- 申込フォーム情報をSupabaseへ保存
- Supabaseの申込IDをStripe Checkoutの `client_reference_id` / metadata に設定
- Stripe Checkout Session IDを申込レコードへ保存
- Stripe成功画面でStripe APIを再確認し、テスト上は `paid` に更新
- 成功画面から内部用Session ID表示を削除

## 先にSupabaseでやること

1. Supabaseでプロジェクトを作成
2. SQL Editorで `supabase_schema.sql` を実行
3. Render Environment Variables に以下を追加

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

`SUPABASE_SECRET_KEY` は `sb_secret_...` を使用してください。
秘密鍵はGitHubへアップロードしないでください。

既存:
- `STRIPE_SECRET_KEY=sk_test_...`

## Render

Build Command:
`pip install -r requirements.txt`

Start Command:
`gunicorn app:app`

## 次の段階

Stripe Webhookを追加して、決済後に成功ページへ戻らなかった場合でも
必ず入金状態を `paid` に反映できるようにします。
その後、申込完了メールを自動送信します。
