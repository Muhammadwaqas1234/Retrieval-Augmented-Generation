import os
import uuid
from datetime import datetime
import openai
import boto3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from gtts import gTTS
from boto3.dynamodb.conditions import Key, Attr
from llama_index.core import VectorStoreIndex, ServiceContext
from llama_index.core.prompts.base import ChatPromptTemplate
from llama_index.llms.openai import OpenAI
from llama_index.core import SimpleDirectoryReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz
import base64
import stripe
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
dynamodb_client = boto3.client('dynamodb', region_name='ap-southeast-2')

# Create tables if they don't exist
def create_dynamodb_table(table_name, key_schema, attribute_definitions, provisioned_throughput, global_secondary_indexes=None):
    try:
        table_params = {
            'TableName': table_name,
            'KeySchema': key_schema,
            'AttributeDefinitions': attribute_definitions,
            'ProvisionedThroughput': provisioned_throughput
        }
        if global_secondary_indexes:
            table_params['GlobalSecondaryIndexes'] = global_secondary_indexes

        table = dynamodb.create_table(**table_params)
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"Table {table_name} created successfully.")
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists.")

create_dynamodb_table(
    'Users',
    key_schema=[
        {'AttributeName': 'id', 'KeyType': 'HASH'}
    ],
    attribute_definitions=[
        {'AttributeName': 'id', 'AttributeType': 'S'},
        {'AttributeName': 'email', 'AttributeType': 'S'}
    ],
    provisioned_throughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    },
    global_secondary_indexes=[
        {
            'IndexName': 'email-index',
            'KeySchema': [
                {'AttributeName': 'email', 'KeyType': 'HASH'}
            ],
            'Projection': {
                'ProjectionType': 'ALL'
            },
            'ProvisionedThroughput': {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        }
    ]
)

create_dynamodb_table(
    'ChatHistory',
    key_schema=[
        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
    ],
    attribute_definitions=[
        {'AttributeName': 'user_id', 'AttributeType': 'S'},
        {'AttributeName': 'timestamp', 'AttributeType': 'S'}
    ],
    provisioned_throughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)

create_dynamodb_table(
    'Feedback',
    key_schema=[
        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
    ],
    attribute_definitions=[
        {'AttributeName': 'user_id', 'AttributeType': 'S'},
        {'AttributeName': 'timestamp', 'AttributeType': 'S'}
    ],
    provisioned_throughput={
        'ReadCapacityUnits': 10,
        'WriteCapacityUnits': 10
    }
)

users_table = dynamodb.Table('Users')
chat_history_table = dynamodb.Table('ChatHistory')
feedback_table = dynamodb.Table('Feedback')

openai.api_key = os.getenv("OPENAI_API_KEY")
messages = []

def appendMessage(role, message, type='message'):
    messages.append({"role": role, "content": message, "type": type})


pdf_dir="./data"

def load_data():
    reader = SimpleDirectoryReader(pdf_dir, recursive=True)
    docs = reader.load_data()
    
    llm = OpenAI(model="gpt-3.5-turbo", temperature="0.1", systemprompt="""Use the books in data file as source for the answer. Generate a valid 
                 and relevant answer to a query related to 
                 construction problems, ensure the answer is based strictly on the content of 
                 the book and not influenced by other sources. Do not hallucinate. The answer should 
                 be informative and fact-based. """)
    service_content = ServiceContext.from_defaults(llm=llm)
    index = VectorStoreIndex.from_documents(docs, service_context=service_content)
    return index

def query_chatbot(query_engine, user_question):
    response = query_engine.query(user_question)
    return response.response if response else None

def initialize_chatbot(pdf_dir = "./data", model="gpt-3.5-turbo", temperature=0.4):
    documents = SimpleDirectoryReader(pdf_dir).load_data()
    llm = OpenAI(model=model, temperature=temperature)

    additional_questions_prompt_str = (
        "Given the context below, generate only one additional question different from previous additional questions related to the user's query:\n"
        "Context:\n"
        "User Query: {query_str}\n"
        "Chatbot Response: \n"
    )

    new_context_prompt_str = (
        "We have the opportunity to only one generate additional question different from previous additional questions based on new context.\n"
        "New Context:\n"
        "User Query: {query_str}\n"
        "Chatbot Response: \n"
        "Given the new context, generate only one additional questions different at each time from previous additional questions related to the user's query."
        "If the context isn't useful, generate only one additional questions different at each from previous time from previous additional questions based on the original context.\n"
    )

    chat_text_qa_msgs = [
        (
            "system",
            """Generate only one additional question that facilitates deeper exploration of the main topic 
            discussed in the user's query and the chatbot's response. The question should be relevant and
              insightful, encouraging further discussion and exploration of the topic. Keep the question concise 
              and focused on different aspects of the main topic to provide a comprehensive understanding.""",
        ),
        ("user", additional_questions_prompt_str),
    ]
    text_qa_template = ChatPromptTemplate.from_messages(chat_text_qa_msgs)

    chat_refine_msgs = [
        (
            "system",
            """Based on the user's question '{prompt}' and the chatbot's response '{response}', please 
            generate only one additional question related to the main topic. The question should be 
            insightful and encourage further exploration of the main topic, providing a more comprehensive 
            understanding of the subject matter.""",
        ),
        ("user", new_context_prompt_str),
    ]
    refine_template = ChatPromptTemplate.from_messages(chat_refine_msgs)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine(
        text_qa_template=text_qa_template,
        refine_template=refine_template,
        llm=llm,
    )

    return query_engine

def generate_response(user_question):
    index = load_data()
    chat_engine = index.as_chat_engine(chat_mode="condense_question", verbose=True)

    response = chat_engine.chat(user_question)
    if response:
        response_text = response.response

        tts = gTTS(text=response_text, lang='en')
        tts.save('output.wav')

        with open('output.wav', 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')

        additional_questions = generate_additional_questions(response_text)
        document_session = response_text

        return response_text, additional_questions, audio_data, document_session

    return None, None, None, None

def generate_additional_questions(user_question):
    additional_questions = []
    words = ["1", "2", "3"]
    for word in words:
        question = query_chatbot(initialize_chatbot(), user_question)
        additional_questions.append(question if question else None)

    return additional_questions



@app.route("/")
def home():
    if 'username' in session:
        return render_template("index.html" , messages=messages)
    return render_template("home.html")

@app.route("/index")
def index():
    if 'username' in session:
        return render_template("index.html", messages=messages)
    return redirect(url_for("login"))



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first"]
        last_name = request.form["last"]
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        user_type = "basic"

        # Check if email is already registered
        response = users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )
        if response['Items']:
            return render_template("register.html", error="Email already registered.")

        user_id = str(uuid.uuid4())
        registration_date = datetime.utcnow().isoformat()

        users_table.put_item(
            Item={
                "id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "password": password,
                "email": email,
                "registration_date": registration_date,
                "user_type": user_type,  # Default user type
                "question_count": 0,
                "last_question_date": registration_date
            }
        )
        
        session["username"] = username
        session["user_id"] = user_id  # Set the user_id in the session

        return redirect(url_for("index"))
    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        response = users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )

        if response['Items']:
            session["username"] = response['Items'][0]['username']
            session["user_id"] = response['Items'][0]['id']  # Set the user_id in the session
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")


@app.route("/chat", methods=["POST"])
def chat():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"})

    user_question = request.json["user_question"]
    user_id = session['user_id']

    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')
    if user:
        last_question_date = datetime.fromisoformat(user.get('last_question_date', '1970-01-01')).date()
        current_date = datetime.utcnow().date()

        if last_question_date < current_date:
            user['question_count'] = 0

        question_limit = 10 if user.get('user_type') == 'pro' else 5

        if user['question_count'] >= question_limit:
            return jsonify({"error": f"{user['user_type'].capitalize()} user has reached maximum question limit"})

        user['question_count'] += 1
        user['last_question_date'] = current_date.isoformat()
        users_table.put_item(Item=user)

        response_text, additional_questions, audio_data, document_session = generate_response(user_question)
        appendMessage('user', user_question)
        appendMessage('assistant', response_text, type='response')

        if additional_questions:
            for question in additional_questions:
                appendMessage("user", question)
                appendMessage('assistant', question, type='additional_question')

        # Save the complete chat session
        session_id = str(uuid.uuid4())
        session_name = ' '.join(user_question.split()[:4])  # First 3 words of the first message
        timestamp = datetime.utcnow().isoformat()  
        chat_history_table.put_item(
            Item={
                "session_id": session_id,
                "user_id": user_id,
                "session_name": session_name,
                "start_time": timestamp,
                "chat_history": messages,
                "timestamp": timestamp  
            }
        )

        return jsonify({"response_text": response_text, "additional_questions": additional_questions, "audio_data": audio_data, "document_session": document_session})

    return jsonify({"error": "User not found"})





@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        if request.method == "POST":
            current_password = request.form["current_password"]
            new_password = request.form["new_password"]
            confirm_password = request.form["confirm_password"]

            if user['password'] != current_password:
                return render_template("change_password.html", error="Current password is incorrect")

            if new_password != confirm_password:
                return render_template("change_password.html", error="Passwords do not match")

            user['password'] = new_password
            users_table.put_item(Item=user)

            return redirect(url_for('account'))

        return render_template("change_password.html")

    return redirect(url_for('index'))

@app.route("/account")
def account():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        user_data = {
            "username": user['username'],
            "email": user['email'],
            "password": user['password']
        }
        return render_template("account.html", user=user_data)
    return redirect(url_for('index'))

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

from datetime import datetime, timedelta

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
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = chat_history_table.query(
        KeyConditionExpression=Key('user_id').eq(user_id),
        ScanIndexForward=False  # Descending order
    )
    items = response['Items']
    chat_history = []
    for item in items:
        timestamp = datetime.fromisoformat(item['start_time'])
        chat_history.append({
            "session_name": item['session_name'],
            "time_since": time_since(timestamp),
            "chat_history": item['chat_history']
        })

    return render_template("history.html", chat_history=chat_history)


@app.route("/support", methods=["GET", "POST"])
def support():
    if request.method == "POST":
        if 'username' not in session:
            return jsonify({"error": "User not logged in"})

        user_id = session['user_id']
        message = request.form["message"]

        feedback_table.put_item(Item={
            'user_id': user_id,
            'timestamp': str(datetime.utcnow()),
            'feedback': message
        })

        return render_template("feedback_submitted.html")

    return render_template("support.html")

@app.route("/logout")
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

def handle_checkout_session(session):
    print("Handling checkout session...")
    customer_email = session['customer_details']['email']
    print(f"Customer email: {customer_email}")

    response = users_table.scan(FilterExpression=Attr('email').eq(customer_email))
    users = response['Items']

    if users:
        user = users[0]
        print(f"Found user: {user}")

        user['user_type'] = 'pro'
        users_table.put_item(Item=user)
        print(f"Updated user: {user}")
    else:
        print("User not found")

    print("Checkout session handling complete.")


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    print("Webhook received")
    payload = request.get_data(as_text=True)
    print("Payload:", payload)
    
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        print("Event:", event)
    except ValueError as e:
        print("ValueError:", e)
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        print("SignatureVerificationError:", e)
        return jsonify(success=False), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)

    return jsonify(success=True)

@app.route('/subscribe', methods=['GET', 'POST'])
def subscribe():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        print(f"User ID from session: {user_id}")

        response = users_table.get_item(Key={'id': user_id})
        user = response.get('Item')
        if not user:
            return jsonify({"error": "User not found"})

        print(f"User found: {user}")

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                customer_email=user['email'],
                line_items=[{
                    'price': 'price_1PQOO3Gthr7AaSvU3fHuPOGN',
                }],
                mode='subscription',
                success_url=url_for('subscription_success', _external=True),
                cancel_url=url_for('subscription_cancel', _external=True),
            )

            print(f"Checkout session created: {checkout_session}")

            return jsonify({'checkout_session_id': checkout_session['id']})
        except Exception as e:
            print(f"Error creating checkout session: {str(e)}")
            return jsonify(error=str(e)), 403

    else:
        return render_template('subscribe.html')


@app.route('/subscription_success')
def subscription_success():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    response = users_table.get_item(Key={'id': user_id})
    user = response.get('Item')

    if user:
        user['user_type'] = 'pro'
        users_table.put_item(Item=user)

    return render_template('subscription_success.html')

@app.route('/subscription_cancel')
def subscription_cancel():
    return render_template('subscription_cancel.html')



@app.route("/feedback", methods=["POST"])
def feedback():
    if 'username' not in session:
        return jsonify({"error": "User not logged in"})

    feedback_text = request.json["feedback"]
    user_id = session['user_id']

    feedback_table.put_item(Item={
        'user_id': user_id,
        'timestamp': str(datetime.utcnow()),
        'feedback': feedback_text
    })

    return jsonify({"message": "Thank you for your feedback!"})


if __name__ == "__main__":
    app.run(debug=True)