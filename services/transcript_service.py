from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from models.schemas import TranscriptStats

class TranscriptService:
    def __init__(self):
        self.formatter = TextFormatter()
        # NEW: Initialize the API client (Required in v1.2.0+)
        self.yt_api = YouTubeTranscriptApi()

    async def get_transcript(self, video_id: str, language: str = "en") -> tuple[str, TranscriptStats]:
        """
        Fetches transcript from YouTube using the new instance-based .fetch() method.
        """
        print(f"📺 Fetching transcript for {video_id}...")
        
        try:
            # NEW METHOD: .fetch() instead of .get_transcript()
            transcript_list = self.yt_api.fetch(
                video_id, 
                languages=[language, 'en', 'en-US']
            )
            
            # Format it
            formatted_text = self.formatter.format_transcript(transcript_list)
            
            # Stats
            stats = TranscriptStats(
                character_count=len(formatted_text),
                word_count=len(formatted_text.split()),
                language=language
            )
            
            return formatted_text, stats
            
        except Exception as e:
            print(f"❌ Transcript Error: {e}")
            raise e