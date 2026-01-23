from fastapi import FastAPI, HTTPException
from youtube_transcript_api import YouTubeTranscriptApi
import asyncio

app = FastAPI(title="Brainweave Ingestion Engine")

def get_video_id(url: str):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        return url.split("be/")[1]
    return url

@app.get("/")
def home():
    return {"system": "Brainweave OS", "status": "Online", "mode": "Ingestion Ready"}

@app.get("/ingest-youtube")
async def ingest_youtube(url: str):
    try:
        video_id = get_video_id(url)
        
        # Corrected call: YouTubeTranscriptApi.get_transcript(video_id)
        loop = asyncio.get_event_loop()
        transcript_list = await loop.run_in_executor(
            None, 
            lambda: YouTubeTranscriptApi.get_transcript(video_id)
        )
        
        full_text = " ".join([t['text'] for t in transcript_list])
        
        return {
            "video_id": video_id,
            "transcript_length": len(full_text),
            "preview": full_text[:500] + "..."
        }
    except Exception as e:
        return {"error": str(e), "tip": "Make sure the video has captions enabled!"}