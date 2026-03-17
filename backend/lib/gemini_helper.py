import google.generativeai as genai

def get_gemini_model():
    """Returns the first available Gemini model without quota issues."""
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    for model_name in models_to_try:
        try:
            return genai.GenerativeModel(model_name)
        except Exception:
            pass
    return genai.GenerativeModel("gemini-1.5-flash")
