
# AquaDiet v1

水色UIの、体重・食事・運動・筋肉痛・AIコメントをまとめるPWAです。

## 1. Supabase
SupabaseのSQL Editorで `schema.sql` を実行してください。

## 2. 環境変数
Renderに以下を設定します。

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-5-mini`

## 3. Render
Build Command:
`pip install -r requirements.txt`

Start Command:
`gunicorn app:app --timeout 120`

## 主な機能
- 日別の体重記録
- 前回測定比
- 食事行の追加・削除
- 朝食 / 昼食 / 夕飯 / 夜食 / 間食プルダウン
- 食事ごとの「嘔吐した」チェック
- 腹筋 / 腹斜筋 / スクワット / ジム / パーソナル
- 運動メモ
- 筋肉痛の筋肉名タグ
- AIコメント
- キャラクター画像をCSSでシルエット表示
- 履歴
- 体重グラフ
- PWA

## 補足
v1は1ユーザー用のシンプル構成です。
公開URLを他人に知られる可能性がある場合は、次版でログイン/PINを追加してください。


## v1.1変更
- UIをグリーン系に変更
- キャラクターを最新WEBP画像へ差し替え
- キャラクターをカラー表示
- AIコメントのjson importエラーを修正

## v1.2変更
- キャラクター表示を大きく調整
- AIコメント吹き出しを拡大
- AIコメントを180〜320文字程度に拡張
- 「記録を保存」で保存後にAIコメントを自動生成
- 「AIコメントをもらう」単独ボタンを削除
