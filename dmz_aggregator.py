import os
from datetime import datetime, timezone
import feedparser
import requests
from google import genai

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

FEEDS = {
    "CharlieINTEL": "https://charlieintel.com/feed",
    "MP1st COD Feed": "https://mp1st.com/feed"
}

TRACKER_FILE = "sent_links.txt"

def load_sent_links():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_link(link):
    with open(TRACKER_FILE, "a") as f:
        f.write(link + "\n")

def send_to_discord(title, summary, link, source_name, is_status_update=False):
    if is_status_update:
        payload = {
            "embeds": [{
                "title": "🔍 Scheduled Check Status",
                "description": summary,
                "color": 8421504, # Gray color for status updates
                "footer": {"text": f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Status Check"}
            }]
        }
    else:
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
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Discord Webhook Error: {e}")

def analyze_and_summarize(title, description):
    prompt = f"""
    You are an AI assistant monitoring Call of Duty updates for a specialized DMZ extraction mode and Modern Warfare 4 community.
    Analyze the following content.
    
    TITLE: {title}
    CONTENT/DESCRIPTION: {description}
    
    Instructions:
    1. Write a concise summary focusing on key details, map features, or DMZ elements. Use short bullet points. Keep it under 4 sentences. Do not use conversational filler.
    """
    try:
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def check_for_updates():
    print("=== STARTING RUN WITH STATUS LOGGING ===")
    sent_links = load_sent_links()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    target_keywords = ["dmz", "hajin", "exclusion zone", "mw4", "modern warfare 4"]
    matches_found = 0

    for source_name, feed_url in FEEDS.items():
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"Failed to connect to {source_name}: {e}")
            continue
        
        if not feed.entries:
            continue

        for entry in feed.entries:
            link = getattr(entry, 'link', feed_url)
            if link in sent_links:
                continue

            title = getattr(entry, 'title', 'Untitled')
            description = getattr(entry, 'summary', '')
            if not description and hasattr(entry, 'content'):
                description = entry.content[0].get('value', '')
            if not description:
                description = title

            lower_text = (title + " " + description).lower()
            if not any(kw in lower_text for kw in target_keywords):
                continue

            print(f"[TARGET FOUND]: {title}")
            summary = analyze_and_summarize(title, description)
            
            if summary:
                send_to_discord(title, summary, link, source_name, is_status_update=False)
                save_sent_link(link)
                sent_links.add(link)
                matches_found += 1

    # If no new relevant items were found during this run, post a confirmation status log
    if matches_found == 0:
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        status_msg = f"✅ Routine check completed successfully.\n• **Status:** No new MW4 / DMZ matches found.\n• **Time:** {current_time}"
        send_to_discord(None, status_msg, None, None, is_status_update=True)
        print("No new matches found. Status update posted to Discord.")

    print("=== RUN COMPLETE ===")

if __name__ == "__main__":
    check_for_updates()
