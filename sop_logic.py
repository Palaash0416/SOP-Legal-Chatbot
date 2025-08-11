# sop_logic.py

import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")
client = OpenAI(api_key=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)

# In-memory session store
sessions = {}

# Your legal documents library
LEGAL_DOCS = {
    "sale agreement": "https://drive.google.com/file/d/SALE_DOC_ID/view?usp=sharing",
    "rent agreement": "https://drive.google.com/file/d/RENT_DOC_ID/view?usp=sharing",
    "gift deed": "https://drive.google.com/file/d/GIFT_DOC_ID/view?usp=sharing",
    "nda": "https://drive.google.com/file/d/NDA_DOC_ID/view?usp=sharing",
    "will": "https://drive.google.com/file/d/WILL_DOC_ID/view?usp=sharing",
    "affidavit": "https://drive.google.com/file/d/AFFIDAVIT_DOC_ID/view?usp=sharing",
    "power of attorney": "https://drive.google.com/file/d/POA_DOC_ID/view?usp=sharing",
    "adoption deed": "https://drive.google.com/file/d/ADOPTION_DOC_ID/view?usp=sharing",
    "divorce petition": "https://drive.google.com/file/d/DIVORCE_DOC_ID/view?usp=sharing",
    "consumer complaint": "https://drive.google.com/file/d/CONSUMER_DOC_ID/view?usp=sharing",
    "rti application": "https://drive.google.com/file/d/RTI_DOC_ID/view?usp=sharing"
}

# Email for human handoff
HUMAN_EMAIL = "palaashjain@sopinternationalllc.co.in"

def send_handoff_email(user_id, query):
    """Send email to notify human professional"""
    try:
        msg = MIMEText(f"User ID: {user_id}\n\nQuery: {query}\n\nPlease take over this conversation.")
        msg["Subject"] = "SOP Legal AI Assistant - Human Handoff Required"
        msg["From"] = "noreply@sopinternationalllc.co.in"
        msg["To"] = HUMAN_EMAIL

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
            server.send_message(msg)
    except Exception as e:
        print(f"[Email Error] {e}")

def sop_chatbot(user_id, user_input, session_state):
    """Main SOP Legal AI Assistant chatbot logic"""
    if user_id not in sessions:
        sessions[user_id] = {"state": "start", "history": []}

    session = sessions[user_id]
    user_input = user_input.strip()

    # Initial greeting
    if session["state"] == "start" or not user_input:
        session["state"] = "chatting"
        return "Hey, I’m SOP, your personal AI legal assistant. How may I help you today?"

    # Save history for persistence
    session["history"].append({"role": "user", "content": user_input})

    # Check if user asked for a legal document
    for doc_name, doc_link in LEGAL_DOCS.items():
        if doc_name in user_input.lower():
            return f"Here’s the {doc_name.title()} template you requested:\n{doc_link}"

    # Handle unavailable document request
    if "agreement" in user_input.lower() or "deed" in user_input.lower():
        send_handoff_email(user_id, user_input)
        return "I don’t have that exact document in my library. I’ve alerted a legal professional who will assist you shortly."

    # GPT-powered legal Q&A
    try:
        messages = [{"role": "system", "content": "You are SOP, a polite and professional Indian legal AI assistant. Provide accurate legal help under Indian law. Keep it simple and user-friendly."}]
        messages.extend(session["history"])

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2
        )

        bot_reply = response.choices[0].message.content
        session["history"].append({"role": "assistant", "content": bot_reply})
        return bot_reply

    except Exception as e:
        print(f"[GPT Error] {e}")
        return "I’m having trouble accessing my legal database right now. Please try again in a moment."
