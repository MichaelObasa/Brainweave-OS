import youtube_transcript_api
from youtube_transcript_api.formatters import TextFormatter
from models.schemas import TranscriptStats

class TranscriptService:
    def __init__(self):
        self.formatter = TextFormatter()

    async def get_transcript(self, video_id: str, language: str = "en") -> tuple[str, TranscriptStats]:
        """
        Fetches transcript from YouTube using explicit module referencing.
        """
        print(f"📺 Fetching transcript for {video_id}...")
        
        # EXPLICIT CALL: module.Class.method
        # This prevents the "AttributeError" confusion
        transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(
            video_id, 
            languages=[language, 'en', 'en-US']
        )
        
        # Format the text
        formatted_text = self.formatter.format_transcript(transcript_list)
        
        # Generate stats
        stats = TranscriptStats(
            character_count=len(formatted_text),
            word_count=len(formatted_text.split()),
            language=language
        )
        
        return formatted_text, stats