# あめ × じゃない方 シーシャオフ会

Flask + Stripe Checkout のテスト版です。

## Render

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Environment Variable:
  - `STRIPE_SECRET_KEY=sk_test_...`

Stripeの秘密鍵はGitHubへアップロードしないでください。

## 現在の実装

- TOP
- 参加申込フォーム
- 入力確認
- 支払い方法選択
- クレジットカード → Stripe Checkout Sandbox
- 決済成功 / キャンセルページ

PayPay・銀行振込・申込保存・自動メールは未接続です。
