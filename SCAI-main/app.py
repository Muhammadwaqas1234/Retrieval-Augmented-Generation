import base64
import os
import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from gtts import gTTS

import database as db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "local-dev-secret-change-in-production")

# Local SQLite persistence (replaces AWS DynamoDB)
db.init_db()

# Stripe is optional for local runs — billing routes degrade gracefully
# when no key is configured.
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
if STRIPE_API_KEY:
    import stripe

    stripe.api_key = STRIPE_API_KEY

messages = []


def appendMessage(role, message, type="message"):
    messages.append({"role": role, "content": message, "type": type})


# ---------------------------------------------------------------------------
# RAG engine (LlamaIndex + OpenAI) — the vector index is built once and
# cached for the lifetime of the process instead of being rebuilt per query.
# ---------------------------------------------------------------------------

pdf_dir = "./data"
_index = None
_chat_engine = None
_question_engine = None

SYSTEM_PROMPT = (
    "Use the books in the data folder as the source for the answer. Generate a "
    "valid and relevant answer to a query related to construction problems. "
    "Ensure the answer is based strictly on the content of the book and not "
    "influenced by other sources. Do not hallucinate. The answer should be "
    "informative and fact-based."
)


def get_index():
    global _index
    if _index is None:
        from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
        from llama_index.llms.openai import OpenAI

        Settings.llm = OpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            system_prompt=SYSTEM_PROMPT,
        )
        docs = SimpleDirectoryReader(pdf_dir, recursive=True).load_data()
        _index = VectorStoreIndex.from_documents(docs)
    return _index


def get_chat_engine():
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = get_index().as_chat_engine(chat_mode="condense_question", verbose=True)
    return _chat_engine


def get_question_engine():
    """Query engine used to generate follow-up questions."""
    global _question_engine
    if _question_engine is None:
        from llama_index.core.prompts.base import ChatPromptTemplate

        additional_questions_prompt_str = (
            "Given the context below, generate only one additional question different "
            "from previous additional questions related to the user's query:\n"
            "Context:\n"
            "User Query: {query_str}\n"
            "Chatbot Response: \n"
        )
        new_context_prompt_str = (
            "We have the opportunity to generate only one additional question different "
            "from previous additional questions based on new context.\n"
            "New Context:\n"
            "User Query: {query_str}\n"
            "Chatbot Response: \n"
            "Given the new context, generate only one additional question different from "
            "previous additional questions related to the user's query. If the context "
            "isn't useful, generate only one additional question based on the original context.\n"
        )
        text_qa_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Generate only one additional question that facilitates deeper "
                    "exploration of the main topic discussed in the user's query and the "
                    "chatbot's response. The question should be relevant and insightful, "
                    "encouraging further discussion. Keep the question concise and focused.",
                ),
                ("user", additional_questions_prompt_str),
            ]
        )
        refine_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Based on the user's question and the chatbot's response, generate "
                    "only one additional question related to the main topic. The question "
                    "should be insightful and encourage further exploration.",
                ),
                ("user", new_context_prompt_str),
            ]
        )
        _question_engine = get_index().as_query_engine(
            text_qa_template=text_qa_template,
            refine_template=refine_template,
        )
    return _question_engine


def generate_additional_questions(response_text):
    additional_questions = []
    engine = get_question_engine()
    for _ in range(3):
        result = engine.query(response_text)
        additional_questions.append(result.response if result else None)
    return additional_questions


def synthesize_speech(text):
    """Text-to-speech via gTTS; returns base64 audio or None when offline."""
    try:
        tts = gTTS(text=text, lang="en")
        tts.save("output.wav")
        with open("output.wav", "rb") as audio_file:
            return base64.b64encode(audio_file.read()).decode("utf-8")
    except Exception:
        return None


def generate_response(user_question):
    response = get_chat_engine().chat(user_question)
    if response:
        response_text = response.response
        audio_data = synthesize_speech(response_text)
        additional_questions = generate_additional_questions(response_text)
        return response_text, additional_questions, audio_data, response_text
    return None, None, None, None


# ---------------------------------------------------------------------------
# Local demo mode — set DEMO_MODE=1 to auto-login a demo account so the app
# can be explored without registering. Never enable in production.
# ---------------------------------------------------------------------------

@app.before_request
def demo_auto_login():
    if os.getenv("DEMO_MODE") == "1" and "username" not in session:
        demo = db.get_user_by_email("demo@scai.local")
        if not demo:
            now = datetime.utcnow().isoformat()
            demo = {
                "id": str(uuid.uuid4()),
                "first_name": "Demo",
                "last_name": "User",
                "username": "demo",
                "password": "demo",
                "email": "demo@scai.local",
                "registration_date": now,
                "user_type": "pro",
                "question_count": 0,
                "last_question_date": now,
            }
            db.upsert_user(demo)
        session["username"] = demo["username"]
        session["user_id"] = demo["id"]


# ---------------------------------------------------------------------------
# Routes — unchanged UI and behavior, now backed by SQLite
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    if "username" in session:
        user = db.get_user(session["user_id"]) or {}
        return render_template("index.html", messages=messages, user=user)
    return render_template("home.html")


@app.route("/index")
def index():
    if "username" in session:
        user = db.get_user(session["user_id"]) or {}
        return render_template("index.html", messages=messages, user=user)
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]

        if db.get_user_by_email(email):
            return render_template("register.html", error="Email already registered.")

        user_id = str(uuid.uuid4())
        registration_date = datetime.utcnow().isoformat()

        db.upsert_user(
            {
                "id": user_id,
                "first_name": request.form["first"],
                "last_name": request.form["last"],
                "username": request.form["username"],
                "password": request.form["password"],
                "email": email,
                "registration_date": registration_date,
                "user_type": "basic",
                "question_count": 0,
                "last_question_date": registration_date,
            }
        )

        session["username"] = request.form["username"]
        session["user_id"] = user_id
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = db.get_user_by_email(email)
        if user and user["password"] == password:
            session["username"] = user["username"]
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")


@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return jsonify({"error": "User not logged in"})

    user_question = request.json["user_question"]
    user_id = session["user_id"]

    user = db.get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"})

    last_question_date = datetime.fromisoformat(
        user.get("last_question_date") or "1970-01-01"
    ).date()
    current_date = datetime.utcnow().date()

    if last_question_date < current_date:
        user["question_count"] = 0

    question_limit = 10 if user.get("user_type") == "pro" else 5
    if user["question_count"] >= question_limit:
        return jsonify(
            {"error": f"{user['user_type'].capitalize()} user has reached maximum question limit"}
        )

    user["question_count"] += 1
    user["last_question_date"] = current_date.isoformat()
    db.upsert_user(user)

    response_text, additional_questions, audio_data, document_session = generate_response(
        user_question
    )
    appendMessage("user", user_question)
    appendMessage("assistant", response_text, type="response")

    if additional_questions:
        for question in additional_questions:
            appendMessage("user", question)
            appendMessage("assistant", question, type="additional_question")

    session_id = str(uuid.uuid4())
    session_name = " ".join(user_question.split()[:4])
    timestamp = datetime.utcnow().isoformat()
    db.save_chat_session(session_id, user_id, session_name, timestamp, messages, timestamp)

    return jsonify(
        {
            "response_text": response_text,
            "additional_questions": additional_questions,
            "audio_data": audio_data,
            "document_session": document_session,
        }
    )


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    """Add documents to the local corpus and rebuild the vector index."""
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        global _index, _chat_engine, _question_engine
        os.makedirs(pdf_dir, exist_ok=True)
        saved = 0
        for file in request.files.getlist("file"):
            if file and file.filename:
                safe_name = os.path.basename(file.filename)
                file.save(os.path.join(pdf_dir, safe_name))
                saved += 1
        if saved:
            _index = None
            _chat_engine = None
            _question_engine = None
        return redirect(url_for("index"))

    return render_template("upload.html")


@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "username" not in session:
        return redirect(url_for("login"))

    user = db.get_user(session["user_id"])
    if user:
        if request.method == "POST":
            current_password = request.form["current_password"]
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if user["password"] != current_password:
                return render_template("change_password.html", error="Current password is incorrect")
            if new_password != confirm_password:
                return render_template("change_password.html", error="Passwords do not match")

            user["password"] = new_password
            db.upsert_user(user)
            return redirect(url_for("account"))

        return render_template("change_password.html")
    return redirect(url_for("index"))


@app.route("/change_email", methods=["POST"])
def change_email():
    if "username" not in session:
        return redirect(url_for("login"))

    user = db.get_user(session["user_id"])
    new_email = request.form.get("new_email", "").strip()
    if user and new_email:
        if db.get_user_by_email(new_email):
            return redirect(url_for("account"))
        user["email"] = new_email
        db.upsert_user(user)
    return redirect(url_for("account"))


@app.route("/condition")
def condition():
    return render_template("condition.html")


@app.route("/account")
def account():
    if "username" not in session:
        return redirect(url_for("login"))

    user = db.get_user(session["user_id"])
    if user:
        user_data = {
            "username": user["username"],
            "email": user["email"],
            "password": user["password"],
        }
        return render_template("account.html", user=user_data)
    return redirect(url_for("index"))


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


def time_since(timestamp):
    now = datetime.utcnow()
    time_diff = now - timestamp

    if time_diff < timedelta(minutes=1):
        return "just now"
    elif time_diff < timedelta(hours=1):
        return f"{int(time_diff.total_seconds() // 60)} minutes ago"
    elif time_diff < timedelta(days=1):
        return f"{int(time_diff.total_seconds() // 3600)} hours ago"
    elif time_diff < timedelta(weeks=1):
        return f"{int(time_diff.total_seconds() // 86400)} days ago"
    else:
        return f"{int(time_diff.total_seconds() // 604800)} weeks ago"


@app.route("/history")
def history():
    if "username" not in session:
        return redirect(url_for("login"))

    items = db.get_chat_history(session["user_id"])
    chat_history = []
    for item in items:
        timestamp = datetime.fromisoformat(item["start_time"])
        chat_history.append(
            {
                "session_name": item["session_name"],
                "time_since": time_since(timestamp),
                "chat_history": item["chat_history"],
            }
        )

    return render_template("history.html", chat_history=chat_history)


@app.route("/support", methods=["GET", "POST"])
def support():
    if request.method == "POST":
        if "username" not in session:
            return jsonify({"error": "User not logged in"})

        db.save_feedback(session["user_id"], str(datetime.utcnow()), request.form["message"])
        return render_template("feedback_submitted.html")

    return render_template("support.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("user_id", None)
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Billing (optional) — active only when STRIPE_API_KEY is configured
# ---------------------------------------------------------------------------

def handle_checkout_session(checkout_session):
    customer_email = checkout_session["customer_details"]["email"]
    user = db.get_user_by_email(customer_email)
    if user:
        user["user_type"] = "pro"
        db.upsert_user(user)


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    if not STRIPE_API_KEY:
        return jsonify(success=False, error="Billing is not configured"), 501

    import stripe

    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return jsonify(success=False), 400

    if event["type"] == "checkout.session.completed":
        handle_checkout_session(event["data"]["object"])

    return jsonify(success=True)


@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if not STRIPE_API_KEY:
            return jsonify({"error": "Billing is not configured on this deployment"}), 501

        import stripe

        user = db.get_user(session["user_id"])
        if not user:
            return jsonify({"error": "User not found"})

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer_email=user["email"],
                line_items=[{"price": STRIPE_PRICE_ID}],
                mode="subscription",
                success_url=url_for("subscription_success", _external=True),
                cancel_url=url_for("subscription_cancel", _external=True),
            )
            return jsonify({"checkout_session_id": checkout_session["id"]})
        except Exception as e:
            return jsonify(error=str(e)), 403

    return render_template("subscribe.html")


@app.route("/subscription_success")
def subscription_success():
    if "username" not in session:
        return redirect(url_for("login"))

    user = db.get_user(session["user_id"])
    if user:
        user["user_type"] = "pro"
        db.upsert_user(user)

    return render_template("subscription_success.html")


@app.route("/subscription_cancel")
def subscription_cancel():
    return render_template("subscription_cancel.html")


@app.route("/feedback", methods=["POST"])
def feedback():
    if "username" not in session:
        return jsonify({"error": "User not logged in"})

    db.save_feedback(session["user_id"], str(datetime.utcnow()), request.json["feedback"])
    return jsonify({"message": "Thank you for your feedback!"})


if __name__ == "__main__":
    app.run(debug=True)
