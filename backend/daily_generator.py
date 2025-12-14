import os
import asyncio
import requests
import json
from datetime import datetime
from groq import Groq
import edge_tts
from supabase import create_client

# CONFIGURATION (Loaded from GitHub Secrets)
NEWS_API_KEY = os.getenv("NEWSDATA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def main():
    print("🚀 NewsKernal Engine Starting...")

    # 1. FETCH NEWS (Global Tech & Science)
    print("📰 Fetching World News...")
    # Fetching 'Technology' and 'Science' to keep it smart
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&category=technology,science&language=en"
    
    try:
        response = requests.get(url)
        data = response.json()
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
        # Voice: 'en-US-BrianNeural' -> A very calm, deep, trusted voice
        communicate = edge_tts.Communicate(script_text, "en-US-BrianNeural") 
        await communicate.save(output_file)

        # 4. UPLOAD TO SUPABASE
        print("☁️ Uploading to NewsKernal Cloud...")
        
        # Upload MP3
        with open(output_file, 'rb') as f:
            supabase.storage.from_("briefs").upload(
                path="public/latest_brief.mp3",
                file=f,
                file_options={"content-type": "audio/mpeg", "upsert": "true"}
            )

        # Upload JSON Metadata (for the website to read)
        metadata = {
            "date": datetime.now().strftime("%B %d, %Y"),
            "summary": script_text
        }
        supabase.storage.from_("briefs").upload(
            path="public/latest_data.json",
            file=json.dumps(metadata).encode('utf-8'),
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        print("✅ NewsKernal Broadcast is LIVE.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        # Optional: Add code here to send you an email if it fails

if __name__ == "__main__":
    asyncio.run(main())
