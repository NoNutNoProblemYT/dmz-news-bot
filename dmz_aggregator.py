import os
import feedparser
import requests
from google import genai

# Grab protected keys from GitHub Secret Vault
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
ai_client = genai.Client()

FEEDS = {
    "COD Blog": "https://callofduty.com",
    "COD YouTube": "https://youtube.com"
}

def send_to_discord(title, summary, link, source_name):
    payload = {
        "embeds": [{
            "title": f"📢 {source_name}: {title}",
            "description": summary,
            "url": link,
            "color": 3066993, 
            "footer": {"text": "🧠 Powered by Gemini AI Intelligence Engine"}
        }]
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"Failed to post to Discord: {response.text}")

def analyze_and_summarize(title, description):
    prompt = f"""
    You are an AI assistant monitoring Call of Duty updates for a specialized DMZ extraction mode community.
    Analyze the following content.
    
    TITLE: {title}
    CONTENT: {description}
    
    Instructions:
    1. Determine if this content contains information relevant to 'DMZ mode', extraction gameplay, or MW4 updates.
    2. If it is NOT relevant to DMZ or general MW4 updates, reply exactly with the word: IGNORE
    3. If it IS relevant, write a concise summary focusing purely on DMZ elements. Use short bullet points. Keep it under 4 sentences. Do not use conversational filler.
    4. CRITICAL DUPLICATE CHECK: If the text discusses general updates or patches that have already been well-established or repeated across normal news streams, filter out the redundant fluff and summarize *only* what is unique. If it's completely repetitive information with nothing new, reply exactly with: IGNORE
    """
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "IGNORE"

def check_for_updates():
    print("Checking official feeds...")
    for source_name, feed_url in FEEDS.items():
        feed = feedparser.parse(feed_url)
        
        # In GitHub Actions, we pull the singular top update from each cycle
        for entry in feed.entries[:2]:
            title = entry.title
            description = entry.summary if hasattr(entry, 'summary') else title
            link = entry.link
            
            summary = analyze_and_summarize(title, description)
            
            if summary and "IGNORE" not in summary.upper():
                print(f"Found match: sending '{title}' to Discord!")
                send_to_discord(title, summary, link, source_name)

if __name__ == "__main__":
    check_for_updates()
    print("Scan complete.")
