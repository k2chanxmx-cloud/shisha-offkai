
import os
import json
from datetime import date, datetime
from flask import Flask, render_template, request, jsonify
from supabase import create_client, Client
from openai import OpenAI

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

MEAL_ORDER = {"朝食": 1, "昼食": 2, "夕飯": 3, "夜食": 4, "間食": 5}
EXERCISES = ["腹筋", "腹斜筋", "スクワット", "ジム", "パーソナル"]


def ensure_db():
    if not supabase:
        raise RuntimeError("Supabaseの環境変数が設定されていません。")


def safe_rows(resp):
    return getattr(resp, "data", None) or []


@app.route("/")
def index():
    selected_date = request.args.get("date") or date.today().isoformat()
    return render_template(
        "index.html",
        selected_date=selected_date,
        meal_types=list(MEAL_ORDER.keys()),
        exercises=EXERCISES,
    )


@app.get("/api/day/<selected_date>")
def get_day(selected_date):
    ensure_db()

    daily = safe_rows(
        supabase.table("daily_logs").select("*").eq("log_date", selected_date).limit(1).execute()
    )
    meals = safe_rows(
        supabase.table("meal_logs").select("*").eq("log_date", selected_date).execute()
    )
    exercises = safe_rows(
        supabase.table("exercise_logs").select("*").eq("log_date", selected_date).execute()
    )
    soreness = safe_rows(
        supabase.table("muscle_soreness_logs").select("*").eq("log_date", selected_date).execute()
    )

    meals.sort(key=lambda r: (MEAL_ORDER.get(r.get("meal_type", ""), 99), r.get("id", 0)))
    return jsonify({
        "daily": daily[0] if daily else None,
        "meals": meals,
        "exercises": exercises,
        "soreness": soreness
    })


@app.post("/api/day")
def save_day():
    ensure_db()
    payload = request.get_json(force=True)
    selected_date = payload["date"]
    weight = payload.get("weight")
    meals = payload.get("meals", [])
    exercises = payload.get("exercises", [])
    soreness = payload.get("soreness", [])

    # Upsert daily log
    daily_payload = {
        "log_date": selected_date,
        "weight": float(weight) if weight not in (None, "") else None,
        "updated_at": datetime.utcnow().isoformat()
    }
    existing = safe_rows(
        supabase.table("daily_logs").select("id").eq("log_date", selected_date).limit(1).execute()
    )
    if existing:
        supabase.table("daily_logs").update(daily_payload).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("daily_logs").insert(daily_payload).execute()

    # Replace child rows for this date
    supabase.table("meal_logs").delete().eq("log_date", selected_date).execute()
    supabase.table("exercise_logs").delete().eq("log_date", selected_date).execute()
    supabase.table("muscle_soreness_logs").delete().eq("log_date", selected_date).execute()

    meal_rows = []
    for m in meals:
        text = (m.get("meal_text") or "").strip()
        meal_type = m.get("meal_type") or "朝食"
        vomited = bool(m.get("vomited"))
        if text or vomited:
            meal_rows.append({
                "log_date": selected_date,
                "meal_type": meal_type,
                "meal_text": text,
                "vomited": vomited
            })
    if meal_rows:
        supabase.table("meal_logs").insert(meal_rows).execute()

    exercise_rows = []
    for e in exercises:
        etype = e.get("exercise_type")
        if etype in EXERCISES and e.get("done"):
            exercise_rows.append({
                "log_date": selected_date,
                "exercise_type": etype,
                "memo": (e.get("memo") or "").strip()
            })
    if exercise_rows:
        supabase.table("exercise_logs").insert(exercise_rows).execute()

    soreness_rows = [
        {"log_date": selected_date, "muscle_name": str(x).strip()}
        for x in soreness if str(x).strip()
    ]
    if soreness_rows:
        supabase.table("muscle_soreness_logs").insert(soreness_rows).execute()

    return jsonify({"ok": True})


@app.post("/api/ai-comment")
def ai_comment():
    ensure_db()
    if not client:
        return jsonify({"error": "OPENAI_API_KEY が設定されていません。"}), 400

    payload = request.get_json(force=True)
    selected_date = payload["date"]

    daily = safe_rows(
        supabase.table("daily_logs").select("*").eq("log_date", selected_date).limit(1).execute()
    )
    meals = safe_rows(
        supabase.table("meal_logs").select("*").eq("log_date", selected_date).execute()
    )
    exercises = safe_rows(
        supabase.table("exercise_logs").select("*").eq("log_date", selected_date).execute()
    )
    soreness = safe_rows(
        supabase.table("muscle_soreness_logs").select("*").eq("log_date", selected_date).execute()
    )

    previous_weight = None
    prev = safe_rows(
        supabase.table("daily_logs")
        .select("weight,log_date")
        .lt("log_date", selected_date)
        .not_.is_("weight", "null")
        .order("log_date", desc=True)
        .limit(1)
        .execute()
    )
    if prev:
        previous_weight = prev[0].get("weight")

    summary = {
        "date": selected_date,
        "weight": daily[0].get("weight") if daily else None,
        "previous_weight": previous_weight,
        "meals": [
            {
                "type": m.get("meal_type"),
                "food": m.get("meal_text"),
                "vomited": bool(m.get("vomited")),
            }
            for m in meals
        ],
        "exercises": [e.get("exercise_type") for e in exercises],
        "exercise_memos": [e.get("memo") for e in exercises if e.get("memo")],
        "muscle_soreness": [s.get("muscle_name") for s in soreness],
    }

    system = """
あなたは日々の体重・食事・運動・筋肉痛を見守る、クールで少しぶっきらぼうだが優しいキャラクターです。
日本語で80〜160文字程度、1〜3文でコメントしてください。
褒めすぎず、説教臭くせず、その日の記録に具体的に触れてください。
嘔吐の記録がある場合、摂取カロリーが減った・帳消しになった等の表現は絶対にしないでください。
嘔吐がある日は、体調への配慮、水分補給、続く場合は医療機関への相談を穏やかに促してください。
体重の数値だけで価値判断をしないでください。
運動と筋肉痛が同じ部位に関係しそうな場合は、休養や無理をしないことを勧めてください。
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system,
        input=json.dumps(summary, ensure_ascii=False)
    )
    comment = (response.output_text or "").strip()

    existing = safe_rows(
        supabase.table("daily_logs").select("id").eq("log_date", selected_date).limit(1).execute()
    )
    if existing:
        supabase.table("daily_logs").update({"ai_comment": comment}).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("daily_logs").insert({
            "log_date": selected_date,
            "ai_comment": comment,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()

    return jsonify({"comment": comment})


@app.get("/api/history")
def history():
    ensure_db()
    rows = safe_rows(
        supabase.table("daily_logs")
        .select("log_date,weight,ai_comment")
        .order("log_date", desc=True)
        .limit(60)
        .execute()
    )
    return jsonify(rows)


@app.get("/api/weights")
def weights():
    ensure_db()
    rows = safe_rows(
        supabase.table("daily_logs")
        .select("log_date,weight")
        .not_.is_("weight", "null")
        .order("log_date")
        .limit(365)
        .execute()
    )
    return jsonify(rows)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    app.run(debug=True)
