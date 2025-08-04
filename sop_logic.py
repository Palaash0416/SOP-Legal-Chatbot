def sop_chatbot(user_id, user_input, session_state):
    if "help" in user_input.lower():
        return "Would you like help from a professional? Yes or No"
    elif user_input.lower() in ["yes", "y", "sure"]:
        return "Thank you. A professional will reach out to you shortly."
    elif user_input.lower() in ["no", "n"]:
        return "Alright. Let us know if you need anything else."
    return "Hi, I’m SOP. How may I help you today?"
