import os
import time
from datetime import datetime, timezone, timedelta
import feedparser
import requests
from google import genai

# Grab protected keys from GitHub Secret Vault
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Explicitly load the client with your key so it never hangs
ai_client = genai.Client(api_key=GEMINI_KEY)

FEEDS = {
    "COD Blog": "https://rssproxy.migor.org/get?url=https://www.callofduty.com/blog",
    "COD YouTube": "https://www.youtube.com/feeds/videos.xml?channel_id=UC9YydG57epLqxA9cTzZXSeQ"
}

# File tracker to remember what has already been posted so it never repeats
TRACKER_FILE = "sent_links.txt"

def load_sent_links():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_link(link):
    with open(TRACKER_FILE, "a") as f:
        f.write(link + "\n")

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
    You are an AI assistant monitoring official Call of Duty updates, trailers, and media for a specialized DMZ extraction mode and MW4 community.
    Analyze the following content.
    
    TITLE: {title}
    CONTENT/DESCRIPTION: {description}
    
    Instructions:
    1. Determine if this content relates to Call of Duty: Modern Warfare / MW4 updates, extraction gameplay, or DMZ mode. 
    2. If it is completely unrelated (e.g., mobile games, unrelated studio titles, non-COD content), reply exactly with the word: IGNORE
    3. If it IS relevant, write a concise summary focusing on the key details or DMZ elements. Use short bullet points. Keep it under 4 sentences. Do not use conversational filler.
    4. CRITICAL DUPLICATE CHECK: If the text discusses general updates or patches that have already been well-established, filter out the fluff and summarize *only* what is unique. If it's completely repetitive information with nothing new, reply exactly with: IGNORE
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
    print("Checking feeds with enhanced YouTube description parsing...")
    sent_links = load_sent_links()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    
    # 14-day lookback window for catch-up
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    
    for source_name, feed_url in FEEDS.items():
        print(f"Connecting to {source_name}...")
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"Failed to connect to {source_name}. Error: {e}")
            continue
        
        if not feed.entries:
            print(f"No articles found for {source_name}.")
            continue

        for entry in feed.entries[:5]:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                entry_date = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)
                if entry_date < two_weeks_ago:
                    continue

            link = getattr(entry, 'link', feed_url)
            
            if link in sent_links:
                continue

            title = getattr(entry, 'title', 'Untitled')
            
            # Robust description extractor for YouTube Atom feeds & blogs
            description = getattr(entry, 'summary', '')
            if not description and hasattr(entry, 'content'):
                description = entry.content[0].get('value', '')
            if not description:
                description = title

            print(f"Analyzing: {title}")
            summary = analyze_and_summarize(title, description)
            
            if summary and "IGNORE" not in summary.upper():
                print(f"Found match: sending '{title}' to Discord!")
                send_to_discord(title, summary, link, source_name)
                save_sent_link(link)
                sent_links.add(link)
            else:
                print("Skipped: Not relevant.")

if __name__ == "__main__":
    check_for_updates()
    print("Scan complete.")
