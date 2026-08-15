# あめ × じゃない方 シーシャオフ会 v6.5

## 今回の変更

Resendの認証済みドメイン `mail.shishaoffkai.com` を使い、
決済完了後に **申込フォームへ入力された参加者本人のメールアドレス**
へ自動メールを送信します。

送信元のデフォルト:

`オフ会受付 <info@mail.shishaoffkai.com>`

## 決済後の流れ

1. Stripe Checkoutで3,500円決済
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
4. Stripe Sandboxで3,500円テスト決済
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


## v6.5 変更点

- 参加費を 4,000円 → 3,500円 に変更
- 支払い方法から PayPay を削除
- 支払い方法は「クレジットカード」「銀行振込」の2種類
- Stripeのクレジットカード決済額も3,500円へ変更
- 決済完了画面・自動メール内の金額も3,500円へ変更

銀行振込は振込先口座情報が未設定のため、現時点では選択UIのみです。
次の版で振込先案内・振込申請・管理側の入金確認を追加できます。


## v6.5 銀行振込対応

銀行振込を選択した場合:

1. Supabaseを `payment_method = bank`
2. `payment_status = bank_transfer_pending`
3. 振込先画面を表示
4. 申込者本人へ振込先案内メールを自動送信
5. 入金確認後は運営側で `paid` に変更

振込先:
- 三菱UFJ銀行
- 浦和支店
- 普通
- 0347624
- トクノウマキ
- 3,500円

### 先にSupabaseで実行

`supabase_v6_5_migration.sql`

### 次の実装候補

管理画面から銀行振込の入金確認ボタンを押すと、
`bank_transfer_pending → paid` に変更し、
参加者へ「入金確認完了メール」を自動送信する機能。
