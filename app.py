import os
from flask import Flask, render_template, redirect, request
import stripe

app = Flask(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

EVENT_NAME = "あめ × じゃない方 シーシャオフ会"
EVENT_PRICE = 4000


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


@app.get("/create-checkout-session")
def create_checkout_session():
    if not stripe.api_key:
        return (
            "STRIPE_SECRET_KEY が設定されていません。"
            "Render の Environment Variables に sk_test_... を登録してください。",
            500,
        )

    base_url = request.url_root.rstrip("/")

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
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
        success_url=base_url
        + "/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=base_url + "/cancel",
    )

    return redirect(checkout_session.url, code=303)


@app.get("/success")
def success():
    session_id = request.args.get("session_id", "")
    return render_template("success.html", session_id=session_id)


@app.get("/cancel")
def cancel():
    return render_template("cancel.html")


if __name__ == "__main__":
    app.run(debug=True)
