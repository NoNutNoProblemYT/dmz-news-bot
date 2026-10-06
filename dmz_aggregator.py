import os
import requests
from google import genai

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

print(f"DEBUG: DISCORD_WEBHOOK_URL is present? {bool(DISCORD_WEBHOOK_URL)}")
print(f"DEBUG: GEMINI_KEY is present? {bool(GEMINI_KEY)}")

# Force an immediate test message to Discord
if DISCORD_WEBHOOK_URL:
    payload = {
        "embeds": [{
            "title": "🚨 Bot Diagnostics Test",
            "description": "If you see this message, your GitHub Secret and Discord Webhook are 100% working!",
            "color": 3066993
        }]
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    print(f"Discord Test Response Code: {response.status_code}")
    print(f"Discord Test Response Text: {response.text}")
else:
    print("ERROR: DISCORD_WEBHOOK_URL environment variable is missing or empty!")

if GEMINI_KEY:
    ai_client = genai.Client(api_key=GEMINI_KEY)
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents='Say hello in 3 words.'
    )
    print(f"Gemini Test Response: {response.text.strip()}")
else:
    print("ERROR: GEMINI_API_KEY environment variable is missing or empty!")
