"""Pydantic schemas for request/response models."""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Chapter(BaseModel):
    """Chapter/timestamp segment in video."""
    title: str
    timestamp: Optional[str] = None  # e.g., "00:15:30" or null
    summary: str


class MetadataSchema(BaseModel):
    """Strict metadata schema that LLM must output."""
    title: str
    source_url: str
    source_type: Literal["youtube"] = "youtube"
    date_published: Optional[str] = None  # ISO8601 date string or null
    host: Optional[str] = None
    guests: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)  # Plain English topics
    tags: List[str] = Field(default_factory=list)  # Hashtags like "#AI"
    summary: str  # 3-5 paragraphs
    key_points: List[str] = Field(default_factory=list)  # 5-12 bullets
    transcript: str  # Full transcript
    chapters: List[Chapter] = Field(default_factory=list)

    @field_validator("date_published")
    @classmethod
    def validate_date(cls, v):
        """Validate ISO8601 date format if provided."""
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            return None  # Return null if invalid


class IngestRequest(BaseModel):
    """Request model for YouTube ingestion endpoint."""
    url: str = Field(..., description="YouTube URL to ingest")
    provider: Literal["openai", "gemini"] = Field(
        default="openai", description="LLM provider to use"
    )
    language: str = Field(default="en", description="Preferred transcript language")
    save_markdown: bool = Field(default=True, description="Save markdown file")
    overwrite: bool = Field(default=False, description="Overwrite existing files")


class TranscriptStats(BaseModel):
    """Statistics about extracted transcript."""
    character_count: int
    language: str
    source: Literal["manual", "auto", "translated", "unknown"] = "unknown"
    segment_count: int = 0


class FileSaveInfo(BaseModel):
    """Information about saved markdown file."""
    path: Optional[str] = None  # Final vault path (may be None if copy failed)
    filename: str
    skipped: bool = False  # True if file existed and overwrite=False
    staged_path: Optional[str] = None  # Staging directory path (always present if saved)
    saved: bool = True  # False if final vault copy failed
    error_code: Optional[str] = None  # Error code if save failed (e.g., "FILE_LOCKED")


class IngestResponse(BaseModel):
    """Response model for YouTube ingestion endpoint."""
    success: bool = True
    transcript_stats: TranscriptStats
    metadata: MetadataSchema
    file_save_info: Optional[FileSaveInfo] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str
    message: str
    details: Optional[dict] = None
