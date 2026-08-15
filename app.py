import os
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, render_template, request
import stripe
from supabase import create_client

app = Flask(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

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
            except Exception:
                app.logger.exception("Webhook Supabase update failed")
                # Stripeに再送してもらうため5xxを返す
                return "Database update failed", 500

    # 未処理イベントも正常受信として200を返す
    return jsonify(received=True), 200


@app.get("/cancel")
def cancel():
    return render_template("cancel.html")


if __name__ == "__main__":
    app.run(debug=True)
