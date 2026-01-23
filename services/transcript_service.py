"""YouTube transcript extraction service."""

import asyncio
import logging
from typing import Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests,
    YouTubeRequestFailed,
)

from models.schemas import TranscriptStats

logger = logging.getLogger(__name__)


class TranscriptService:
    """Service for extracting YouTube transcripts with robust error handling."""
    
    @staticmethod
    async def get_transcript(
        video_id: str,
        language: str = "en",
        preferred_languages: Optional[list] = None
    ) -> Tuple[str, TranscriptStats]:
        """
        Extract transcript from YouTube video.
        
        Returns:
            Tuple of (transcript_text, TranscriptStats)
        
        Raises:
            ValueError: If video ID is invalid
            TranscriptsDisabled: If captions are disabled
            NoTranscriptFound: If no transcript available
            VideoUnavailable: If video doesn't exist or is private
            TooManyRequests: If rate limited
            YouTubeRequestFailed: If YouTube API fails
        """
        if preferred_languages is None:
            preferred_languages = [language, "en"]
        
        def _fetch_transcript():
            """Synchronous transcript fetching wrapped for async execution."""
            try:
                # Try to get transcript in preferred languages
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=preferred_languages
                )
                
                # Determine source type
                source = "unknown"
                detected_language = language
                
                # Try to get transcript info to determine if it's auto-generated
                try:
                    transcript_data = YouTubeTranscriptApi.list_transcripts(video_id)
                    for transcript in transcript_data:
                        if transcript.language_code == transcript_list[0].get('language', language):
                            if transcript.is_generated:
                                source = "auto"
                            else:
                                source = "manual"
                            detected_language = transcript.language_code
                            break
                except Exception:
                    # If we can't determine, default to "unknown"
                    pass
                
                # Combine transcript segments
                full_text = " ".join([item['text'] for item in transcript_list])
                
                # Add newlines between segments for readability
                # (transcript API returns segments that may be missing punctuation)
                cleaned_text = full_text.replace("  ", " ").strip()
                
                stats = TranscriptStats(
                    character_count=len(cleaned_text),
                    language=detected_language,
                    source=source,
                    segment_count=len(transcript_list)
                )
                
                return cleaned_text, stats
                
            except TranscriptsDisabled:
                logger.error(f"Transcripts disabled for video {video_id}")
                raise
            except NoTranscriptFound:
                logger.error(f"No transcript found for video {video_id} in languages {preferred_languages}")
                raise
            except VideoUnavailable as e:
                logger.error(f"Video unavailable: {video_id} - {e}")
                raise
            except TooManyRequests as e:
                logger.warning(f"Rate limited for video {video_id}: {e}")
                raise
            except YouTubeRequestFailed as e:
                logger.error(f"YouTube API request failed for {video_id}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching transcript for {video_id}: {e}")
                raise
        
        # Run in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        try:
            transcript_text, stats = await loop.run_in_executor(None, _fetch_transcript)
            return transcript_text, stats
        except Exception as e:
            # Re-raise with context
            raise
