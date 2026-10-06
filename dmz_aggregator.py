import os
import feedparser
import requests
from google import genai

# Grab protected keys from GitHub Secret Vault
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Explicitly load the client with your key so it never hangs
ai_client = genai.Client(api_key=GEMINI_KEY)

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
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code != 204:
            print(f"Failed to post to Discord: {response.text}")
    except Exception as e:
        print(f"Discord Webhook Error: {e}")

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
    # Add a browser disguise so websites don't block the GitHub bot
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    for source_name, feed_url in FEEDS.items():
        print(f"Connecting to {source_name}...")
        try:
            # Force a 15-second timeout so it never freezes forever
            response = requests.get(feed_url, headers=headers, timeout=15)
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"Failed to connect to {source_name}. Error: {e}")
            continue
        
        if not feed.entries:
            print(f"No articles found for {source_name}. (Note: Make sure the URL is an RSS feed, not just a normal website link!)")
            continue

        # In GitHub Actions, we pull the singular top update from each cycle
        for entry in feed.entries[:2]:
            title = entry.title
            description = getattr(entry, 'summary', title)
            link = getattr(entry, 'link', feed_url)
            
            print(f"Analyzing: {title}")
            summary = analyze_and_summarize(title, description)
            
            if summary and "IGNORE" not in summary.upper():
                print(f"Found match: sending '{title}' to Discord!")
                send_to_discord(title, summary, link, source_name)
            else:
                print("Skipped: Not relevant to DMZ/MW4.")

if __name__ == "__main__":
    check_for_updates()
    print("Scan complete.")
