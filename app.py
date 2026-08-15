import os
import json
from datetime import datetime, timezone
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from flask import Flask, jsonify, redirect, render_template, request
import stripe
from supabase import create_client

app = Flask(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM = os.environ.get("RESEND_FROM", "オフ会受付 <info@mail.shishaoffkai.com>")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_SECRET_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

EVENT_NAME = "あめ × じゃない方 シーシャオフ会"
EVENT_PRICE = 4000


def require_supabase():
    if supabase is None:
        raise RuntimeError(
            "Supabase未設定です。RenderのEnvironment Variablesに "
            "SUPABASE_URL と SUPABASE_SECRET_KEY を登録してください。"
        )


def mark_application_paid(application_id, checkout_session):
    """Stripe決済成功をSupabaseへ反映。複数回呼ばれても同じ内容を更新する。"""
    if not application_id:
        return

    payment_intent_id = getattr(checkout_session, "payment_intent", None)

    update_data = {
        "payment_status": "paid",
        "stripe_checkout_session_id": checkout_session.id,
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }

    if payment_intent_id:
        update_data["stripe_payment_intent_id"] = payment_intent_id

    (
        supabase.table("event_applications")
        .update(update_data)
        .eq("id", application_id)
        .execute()
    )


def send_payment_confirmation_email(application_id):
    """
    決済完了後、申込フォームに入力されたメールアドレスへ
    Resendから自動で確認メールを送信する。
    """
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY が設定されていません。")

    response = (
        supabase.table("event_applications")
        .select(
            "id,name,handle,email,phone,x_account,payment_status,"
            "email_sent_at,resend_email_id"
        )
        .eq("id", application_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        raise RuntimeError("メール送信用の申込情報が見つかりません。")

    application = rows[0]

    # Webhook再送などで既に送信済みなら重複送信しない
    if application.get("email_sent_at"):
        return application.get("resend_email_id")

    applicant_name = application.get("name") or application.get("handle") or "参加者"
    applicant_email = (application.get("email") or "").strip()

    if not applicant_email or "@" not in applicant_email:
        raise RuntimeError("申込者のメールアドレスが不正です。")

    subject = "【あめ × じゃない方 シーシャオフ会】お申し込み・お支払い完了のお知らせ"

    html = f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Yu Gothic',sans-serif;
                color:#4a2f3d;line-height:1.8;max-width:620px;margin:auto;">
      <div style="background:#fff2f8;border:1px solid #efb8d1;border-radius:22px;padding:28px;">
        <div style="text-align:center;font-size:28px;font-weight:700;margin-bottom:8px;">
          お申し込みありがとうございます♡
        </div>
        <div style="text-align:center;color:#d96b9c;font-weight:700;margin-bottom:24px;">
          あめ × じゃない方 シーシャオフ会
        </div>

        <p>{applicant_name} 様</p>

        <p>
          シーシャオフ会へのお申し込みありがとうございます。<br>
          参加費 4,000円のお支払いを確認しました。
        </p>

        <div style="background:#ffffff;border:1px dashed #efb8d1;border-radius:16px;
                    padding:18px;margin:22px 0;">
          <strong>開催日</strong><br>
          2026年10月18日<br><br>

          <strong>会場</strong><br>
          亀戸シーシャ Eighty -80-<br><br>

          <strong>参加費</strong><br>
          4,000円（お支払い済み）
        </div>

        <p>
          当日は喫煙目的店への入店となるため、
          <strong>身分証明書を必ずお持ちください。</strong><br>
          身分証をご提示いただけない場合はご参加いただけません。
        </p>

        <p>
          当日はシーシャ8台をご用意しています。<br>
          ツーショット写メも撮影できます♡
        </p>

        <p style="text-align:center;margin-top:28px;color:#d96b9c;font-weight:700;">
          まったりシーシャしよ？♡
        </p>

        <hr style="border:0;border-top:1px solid #f2c9db;margin:28px 0 18px;">

        <p style="font-size:12px;color:#8f6d7e;margin:0;">
          このメールは「あめ × じゃない方 シーシャオフ会」の
          お申し込み・決済完了後に自動送信されています。
        </p>
      </div>
    </div>
    """

    payload = {
        "from": RESEND_FROM,
        "to": [applicant_email],
        "subject": subject,
        "html": html,
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        "https://api.resend.com/emails",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "shisha-offkai/1.0",
            "Idempotency-Key": f"shisha-paid-{application_id}",
        },
    )

    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API error {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Resend connection error: {exc}") from exc

    resend_email_id = result.get("id")

    (
        supabase.table("event_applications")
        .update(
            {
                "email_sent_at": datetime.now(timezone.utc).isoformat(),
                "resend_email_id": resend_email_id,
            }
        )
        .eq("id", application_id)
        .execute()
    )

    return resend_email_id


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/apply")
def apply():
    return render_template("apply.html")


@app.get("/confirm")
def confirm():
    return render_template("confirm.html")


@app.get("/payment")
def payment():
    return render_template("payment.html")


@app.post("/api/applications")
def api_create_application():
    try:
        require_supabase()
        data = request.get_json(silent=True) or {}

        required_text = ["name", "handle", "email", "phone"]
        for field in required_text:
            if not str(data.get(field, "")).strip():
                return jsonify(error=f"{field} が未入力です。"), 400

        required_consents = [
            "age_confirmed",
            "id_required_confirmed",
            "cancellation_confirmed",
            "privacy_confirmed",
        ]
        if not all(data.get(k) is True for k in required_consents):
            return jsonify(error="注意事項への同意を確認できません。"), 400

        payload = {
            "name": str(data["name"]).strip()[:100],
            "handle": str(data["handle"]).strip()[:100],
            "email": str(data["email"]).strip()[:254],
            "phone": str(data["phone"]).strip()[:30],
            "x_account": str(data.get("xid", "")).strip()[:100] or None,
            "age_confirmed": True,
            "id_required_confirmed": True,
            "cancellation_confirmed": True,
            "privacy_confirmed": True,
            "payment_status": "unpaid",
        }

        response = supabase.table("event_applications").insert(payload).execute()
        rows = response.data or []
        if not rows:
            return jsonify(error="申込情報を保存できませんでした。"), 500

        return jsonify(application_id=rows[0]["id"])

    except Exception as exc:
        app.logger.exception("application insert failed")
        return jsonify(error=f"申込情報の保存に失敗しました: {exc}"), 500


@app.get("/create-checkout-session")
def create_checkout_session():
    if not stripe.api_key:
        return (
            "STRIPE_SECRET_KEY が設定されていません。"
            "Render の Environment Variables に sk_test_... を登録してください。",
            500,
        )

    try:
        require_supabase()

        application_id = (request.args.get("application_id") or "").strip()
        if not application_id:
            return "application_id がありません。参加申し込みからやり直してください。", 400

        response = (
            supabase.table("event_applications")
            .select("id,email,payment_status")
            .eq("id", application_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return "申込情報が見つかりません。", 404

        application = rows[0]
        base_url = request.url_root.rstrip("/")

        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=application_id,
            customer_email=application["email"],
            metadata={
                "application_id": application_id,
                "event": "ame_janaihou_shisha_2026_10_18",
            },
            line_items=[
                {
                    "price_data": {
                        "currency": "jpy",
                        "product_data": {
                            "name": EVENT_NAME,
                            "description": "2026年10月18日 / 亀戸シーシャ Eighty -80-",
                        },
                        "unit_amount": EVENT_PRICE,
                    },
                    "quantity": 1,
                }
            ],
            success_url=base_url + "/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=base_url + "/cancel",
        )

        (
            supabase.table("event_applications")
            .update(
                {
                    "payment_method": "card",
                    "payment_status": "pending",
                    "stripe_checkout_session_id": checkout_session.id,
                }
            )
            .eq("id", application_id)
            .execute()
        )

        return redirect(checkout_session.url, code=303)

    except Exception as exc:
        app.logger.exception("checkout create failed")
        return f"決済画面の作成に失敗しました: {exc}", 500


@app.get("/success")
def success():
    session_id = (request.args.get("session_id") or "").strip()

    if session_id and stripe.api_key and supabase is not None:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            application_id = checkout_session.client_reference_id

            # Stripe APIから支払い済みを確認できたときだけDBをpaidにする。
            # 次の段階でWebhookも追加し、購入者がこの画面へ戻らなくても
            # 入金状態を反映できるようにする。
            if application_id and checkout_session.payment_status == "paid":
                mark_application_paid(application_id, checkout_session)
        except Exception:
            app.logger.exception("success verification failed")

    return render_template("success.html")


@app.post("/webhook")
def stripe_webhook():
    """
    StripeからのWebhookを署名検証して受信。
    checkout.session.completed のうち payment_status == paid の場合のみ
    申込レコードを paid に更新する。
    """
    if not STRIPE_WEBHOOK_SECRET:
        app.logger.error("STRIPE_WEBHOOK_SECRET is not configured")
        return "Webhook secret is not configured", 500

    try:
        require_supabase()
    except Exception:
        app.logger.exception("Supabase is not configured")
        return "Supabase is not configured", 500

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        app.logger.warning("Invalid webhook payload")
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        app.logger.warning("Invalid Stripe webhook signature")
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]

        application_id = (
            checkout_session.get("client_reference_id")
            or (checkout_session.get("metadata") or {}).get("application_id")
        )

        # カード決済ではcompleted時点でpaidになる。
        # 支払状態を再確認し、未払いならDBをpaidにしない。
        if application_id and checkout_session.get("payment_status") == "paid":
            try:
                mark_application_paid(application_id, checkout_session)
                app.logger.info(
                    "Webhook paid application updated: %s / session: %s",
                    application_id,
                    checkout_session.get("id"),
                )

                resend_email_id = send_payment_confirmation_email(application_id)
                app.logger.info(
                    "Payment confirmation email sent: application=%s / resend=%s",
                    application_id,
                    resend_email_id,
                )
            except Exception:
                app.logger.exception("Webhook Supabase update failed")
                # DB更新またはメール送信に失敗した場合はStripeに再送してもらうため5xx
                return "Post-payment processing failed", 500

    # 未処理イベントも正常受信として200を返す
    return jsonify(received=True), 200


@app.get("/cancel")
def cancel():
    return render_template("cancel.html")


if __name__ == "__main__":
    app.run(debug=True)
