import os
import smtplib
from email.mime.text import MIMEText
from typing import Dict

# Simulated session memory (for demo — replace with DB for production)
user_sessions: Dict[str, Dict] = {}

# List of available legal documents (must match actual file names in /static/)
available_documents = {
    "rent agreement", "sale agreement", "gift deed", "will",
    "affidavit", "power of attorney", "divorce petition",
    "lease deed", "consumer complaint", "non-disclosure agreement",
    "adoption agreement", "name change affidavit", "memorandum of understanding",
    "indemnity bond", "employment agreement", "freelance contract",
    "domestic violence petition", "general affidavit", "rti application"
}

# Email configuration for handoff
EMAIL_USER = "sop.bot.help@gmail.com"
EMAIL_PASS = "mmqs jjuv uhwm gmvy"
HUMAN_NOTIFY_EMAIL = "palaashjain@sopinternationalllc.co.in"

def send_email_notification(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = HUMAN_NOTIFY_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def sop_chatbot(user_id: str, user_input: str, session_state: str) -> str:
    user_input = user_input.lower().strip()
    session = user_sessions.setdefault(user_id, {"state": "start", "history": []})
    session["history"].append(user_input)

    # Handle resumption of human chat
    if session["state"] == "human_waiting":
        if "yes" in user_input:
            send_email_notification("Returning user needs human help", f"User {user_id} wants to resume the chat.\nPrevious conversation:\n" + "\n".join(session["history"]))
            return "Welcome back. We've notified a legal professional to resume your conversation shortly."
        else:
            session["state"] = "start"
            return "Alright. Let us know whenever you need help."

    # Start greeting
    if session["state"] == "start":
        session["state"] = "chatting"
        return "Hey, I’m SOP. How may I help you today?"

    # RTI-specific logic
    if "rti" in user_input and "application" in user_input:
        return "Here is a sample RTI Application you can use:\nhttps://www.soplegalaiassistant.co.in/static/Sample%20RTI%20Application.pdf"
    if "rti" in user_input:
        return "Yes, I can assist with RTI-related queries under Indian law. Please share your question."

    # Document access
    if any(word in user_input for word in ["document", "agreement", "form", "affidavit", "petition", "deed"]):
        for doc in available_documents:
            if doc in user_input:
                # Convert doc name to file-safe format
                filename = "Sample " + doc.title().replace("Non-Disclosure", "Non-Disclosure Agreement").replace(" ", "%20") + ".pdf"
                link = f"https://www.soplegalaiassistant.co.in/static/{filename}"
                return f"Here is your requested document:\n{link}"
        session["state"] = "confirm_handoff"
        return "Sorry, I can’t help you with that document but I surely can connect you with a professional. Would you like that?"

    # Professional help escalation
    if session["state"] == "confirm_handoff":
        if any(x in user_input for x in ["yes", "ok", "sure", "please", "yep"]):
            send_email_notification("New Human Handoff Request", f"User {user_id} has requested human help.\nConversation so far:\n" + "\n".join(session["history"]))
            session["state"] = "human_waiting"
            return "Let’s help you find the suitable professional for your problem. A team member will reach out shortly."
        else:
            session["state"] = "chatting"
            return "Alright. Let me know if you need help with anything else."

    # Legal inquiry fallback
    if any(word in user_input for word in ["ipc", "section", "act", "law", "legal", "court", "bail", "contract", "property", "penal"]):
        session["state"] = "confirm_handoff"
        return "Would you like help from a legal professional regarding this?"

    # Exit / End chat
    if any(x in user_input for x in ["bye", "thank you", "exit", "no thanks", "that's all"]):
        session["state"] = "start"
        return "It was nice talking to you. We hope to see you again soon."

    # Default fallback
    return "Please let me know if you need a legal document, legal help, or RTI assistance."
