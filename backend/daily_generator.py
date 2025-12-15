import os
import asyncio
import requests
import json
from datetime import datetime
from groq import Groq
import edge_tts
from supabase import create_client

# --- CONFIGURATION ---
# The exact name of your bucket from the screenshot (Case Sensitive!)
BUCKET_NAME = "NewsKernal" 

# Load Secrets
NEWS_API_KEY = os.getenv("NEWSDATA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verify Secrets exist before starting
if not all([NEWS_API_KEY, GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    print("❌ ERROR: One or more API Keys are missing from GitHub Secrets.")
    exit(1)

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def main():
    print(f"🚀 NewsKernal Engine Starting... Target Bucket: '{BUCKET_NAME}'")

    # 1. FETCH NEWS
    print("📰 Fetching World News...")
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&category=technology,science&language=en"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('status') == 'error':
            print(f"❌ NewsAPI Error: {data.get('results', 'Unknown error')}")
            return

        articles = []
        # Grab top 5 stories
        for item in data.get('results', [])[:5]:
            desc = item.get('description') or item.get('title')
            articles.append(f"Headline: {item['title']}\nSummary: {desc}")
            
        if not articles:
            print("❌ No news found. Aborting.")
            return

        print(f"✅ Found {len(articles)} stories.")

        # 2. SUMMARIZE (Groq / Llama 3)
        print("🧠 NewsKernal AI is writing the script...")
        system_prompt = (
            "You are the voice of NewsKernal, a futuristic tech news station. "
            "Summarize these 5 stories into a tightly packed 120-second briefing. "
            "Style: Professional, fast-paced, insightful. "
            "Start with: 'This is NewsKernal. Here is your daily download.' "
            "End with: 'System update complete. This was NewsKernal.'"
            "Do not use emojis or markdown formatting."
        )
        
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n\n".join(articles)}
            ],
            model="llama3-8b-8192"
        )
        script_text = completion.choices[0].message.content

        # 3. GENERATE AUDIO (Edge-TTS)
        print("🎙️ Synthesizing Voice...")
        output_file = "brief_today.mp3"
        # Voice: 'en-US-BrianNeural'
        communicate = edge_tts.Communicate(script_text, "en-US-BrianNeural") 
        await communicate.save(output_file)

        # 4. UPLOAD TO SUPABASE (Using BUCKET_NAME variable)
        print(f"☁️ Uploading MP3 to {BUCKET_NAME}...")
        
        with open(output_file, 'rb') as f:
            supabase.storage.from_(BUCKET_NAME).upload(
                path="public/latest_brief.mp3",
                file=f,
                file_options={"content-type": "audio/mpeg", "upsert": "true"}
            )

        print(f"☁️ Uploading Metadata to {BUCKET_NAME}...")
        metadata = {
            "date": datetime.now().strftime("%B %d, %Y"),
            "summary": script_text
        }
        
        supabase.storage.from_(BUCKET_NAME).upload(
            path="public/latest_data.json",
            file=json.dumps(metadata).encode('utf-8'),
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        print("✅ NewsKernal Broadcast is LIVE.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        exit(1) # Force GitHub Action to fail so you see the Red X

if __name__ == "__main__":
    asyncio.run(main())
