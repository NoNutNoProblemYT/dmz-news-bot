import os
import time
from datetime import datetime, timezone, timedelta
import feedparser
import requests
from google import genai

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_KEY)

FEEDS = {
    "CharlieINTEL (Official Blog Mirror)": "https://charlieintel.com/feed",
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
        print(f"Discord Response Status: {response.status_code}")
    except Exception as e:
        print(f"Discord Webhook Error: {e}")

def analyze_and_summarize(title, description):
    prompt = f"""
    You are an AI assistant monitoring Call of Duty updates for a specialized DMZ extraction mode and MW4 community.
    Analyze the following content.
    
    TITLE: {title}
    CONTENT/DESCRIPTION: {description}
    
    Instructions:
    1. Determine if this content relates to Call of Duty: Modern Warfare / MW4 updates, extraction gameplay, or DMZ mode. 
    2. If it is completely unrelated, reply exactly with the word: IGNORE
    3. If it IS relevant, write a concise summary focusing on the key details or DMZ elements. Use short bullet points. Keep it under 4 sentences. Do not use conversational filler.
    4. CRITICAL DUPLICATE CHECK: If the text discusses general updates or patches that have already been well-established, filter out the fluff and summarize *only* what is unique. If it's completely repetitive information with nothing new, reply exactly with: IGNORE
    """
    try:
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',  # Updated to the correct active model name
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "IGNORE"

def check_for_updates():
    print("=== STARTING AGGREGATOR RUN ===")
    sent_links = load_sent_links()
    print(f"Loaded {len(sent_links)} previously sent links from memory.")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    
    for source_name, feed_url in FEEDS.items():
        print(f"\nConnecting to {source_name}...")
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            print(f"HTTP Status: {response.status_code}")
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"Failed to connect: {e}")
            continue
        
        if not feed.entries:
            print(f"WARNING: Zero entries found for {source_name}!")
            continue

        print(f"Successfully retrieved {len(feed.entries)} items from {source_name}.")

        for entry in feed.entries[:10]: # Checking top 10 items to catch recent news
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                entry_date = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)
                if entry_date < two_weeks_ago:
                    continue

            link = getattr(entry, 'link', feed_url)
            
            if link in sent_links:
                print(f"   [SKIPPED] Already in sent_links.txt memory: {link}")
                continue

            title = getattr(entry, 'title', 'Untitled')
            description = getattr(entry, 'summary', '')
            if not description and hasattr(entry, 'content'):
                description = entry.content[0].get('value', '')
            if not description:
                description = title

            print(f"\n-> Checking Item: '{title}'")
            summary = analyze_and_summarize(title, description)
            print(f"   Gemini Raw Output: {summary}")
            
            if summary and "IGNORE" not in summary.upper():
                print("   >>> MATCH FOUND! Pushing to Discord...")
                send_to_discord(title, summary, link, source_name)
                save_sent_link(link)
                sent_links.add(link)
            else:
                print("   [SKIPPED] Gemini returned IGNORE.")

    print("\n=== AGGREGATOR RUN COMPLETE ===")

if __name__ == "__main__":
    check_for_updates()
