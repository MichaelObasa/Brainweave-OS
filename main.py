"""Brainweave-OS Ingestion API - FastAPI application."""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    TooManyRequests,
    YouTubeRequestFailed,
)

# Load environment variables from .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional

from models.schemas import IngestRequest, IngestResponse, ErrorResponse
from services.transcript_service import TranscriptService
from services.llm_service import LLMService
from services.markdown_service import MarkdownService
from utils.youtube import extract_video_id

# Request ID context variable
request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)

# Custom formatter to include request ID
class RequestIDFormatter(logging.Formatter):
    """Log formatter that includes request ID."""
    
    def format(self, record):
        record.request_id = request_id_var.get()
        return super().format(record)

# Update handler formatter
for handler in logging.root.handlers:
    handler.setFormatter(RequestIDFormatter("%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Ensure directories exist
    from config import KNOWLEDGE_VAULT_STAGING_DIR, KNOWLEDGE_VAULT_DIR
    KNOWLEDGE_VAULT_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_VAULT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Brainweave-OS Ingestion API starting up")
    logger.info(f"Staging directory: {KNOWLEDGE_VAULT_STAGING_DIR}")
    logger.info(f"Vault directory: {KNOWLEDGE_VAULT_DIR}")
    yield
    logger.info("Brainweave-OS Ingestion API shutting down")


app = FastAPI(
    title="Brainweave-OS Ingestion API",
    description="YouTube ingestion pipeline with structured metadata extraction",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Middleware to add request ID to requests."""
    request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def home():
    """Root endpoint."""
    return {
        "system": "Brainweave OS",
        "status": "Online",
        "mode": "Ingestion Ready",
        "version": "1.0.0"
    }


@app.post("/ingest/youtube", response_model=IngestResponse)
async def ingest_youtube(request: IngestRequest):
    """
    Ingest YouTube video: extract transcript, generate metadata, save markdown.
    
    Returns structured JSON with transcript stats, metadata, and file save info.
    """
    logger.info(f"Processing ingestion request for URL: {request.url}")
    
    try:
        # Extract video ID
        try:
            video_id = extract_video_id(request.url)
            logger.info(f"Extracted video ID: {video_id}")
        except ValueError as e:
            logger.error(f"Invalid YouTube URL: {request.url} - {e}")
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_URL",
                    message=f"Could not extract video ID from URL: {request.url}",
                    details={"url": request.url, "error": str(e)}
                ).model_dump()
            )
        
        # Extract transcript
        try:
            transcript_service = TranscriptService()
            transcript_text, transcript_stats = await transcript_service.get_transcript(
                video_id=video_id,
                language=request.language
            )
            logger.info(f"Extracted transcript: {transcript_stats.character_count} characters")
        except TranscriptsDisabled:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="TRANSCRIPTS_DISABLED",
                    message="This video has captions disabled. Cannot extract transcript.",
                    details={"video_id": video_id}
                ).model_dump()
            )
        except NoTranscriptFound:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="NO_TRANSCRIPT_FOUND",
                    message=f"No transcript found for this video in language '{request.language}'",
                    details={"video_id": video_id, "language": request.language}
                ).model_dump()
            )
        except VideoUnavailable as e:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="VIDEO_UNAVAILABLE",
                    message="Video is unavailable (may be private, deleted, or region-restricted)",
                    details={"video_id": video_id, "error": str(e)}
                ).model_dump()
            )
        except TooManyRequests:
            raise HTTPException(
                status_code=429,
                detail=ErrorResponse(
                    error_code="RATE_LIMITED",
                    message="YouTube API rate limit exceeded. Please try again later.",
                    details={"video_id": video_id}
                ).model_dump()
            )
        except YouTubeRequestFailed as e:
            raise HTTPException(
                status_code=502,
                detail=ErrorResponse(
                    error_code="YOUTUBE_API_ERROR",
                    message="YouTube API request failed",
                    details={"video_id": video_id, "error": str(e)}
                ).model_dump()
            )
        except Exception as e:
            logger.error(f"Unexpected error extracting transcript: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error_code="TRANSCRIPT_EXTRACTION_ERROR",
                    message="Failed to extract transcript",
                    details={"video_id": video_id, "error": str(e)}
                ).model_dump()
            )
        
        # Extract metadata using LLM
        try:
            llm_service = LLMService(provider=request.provider)
            metadata = await asyncio.to_thread(
                llm_service.extract_metadata,
                transcript_text,
                request.url
            )
            logger.info(f"Extracted metadata: title='{metadata.title}'")
        except ValueError as e:
            # LLM validation error
            logger.error(f"LLM validation error: {e}")
            raise HTTPException(
                status_code=502,
                detail=ErrorResponse(
                    error_code="LLM_VALIDATION_ERROR",
                    message="LLM returned invalid or malformed output",
                    details={"error": str(e)}
                ).model_dump()
            )
        except Exception as e:
            logger.error(f"LLM extraction error: {e}", exc_info=True)
            raise HTTPException(
                status_code=502,
                detail=ErrorResponse(
                    error_code="LLM_EXTRACTION_ERROR",
                    message="Failed to extract metadata from transcript",
                    details={"error": str(e), "provider": request.provider}
                ).model_dump()
            )
        
        # Save markdown file if requested
        # This is best-effort: staging always succeeds, vault copy may fail
        file_save_info = None
        if request.save_markdown:
            try:
                markdown_service = MarkdownService()
                file_save_info = markdown_service.save_metadata(
                    metadata,
                    overwrite=request.overwrite
                )
                if file_save_info.saved:
                    logger.info(f"Markdown file saved to vault: {file_save_info.filename}")
                else:
                    logger.warning(
                        f"Markdown file saved to staging only (vault copy failed): "
                        f"{file_save_info.filename} - {file_save_info.error_code}"
                    )
            except Exception as e:
                logger.error(f"Failed to save markdown file even to staging: {e}", exc_info=True)
                # This is a real failure - staging should always work
                # But we still return success with metadata, just no file_save_info
                file_save_info = None
        
        # Return response
        return IngestResponse(
            success=True,
            transcript_stats=transcript_stats,
            metadata=metadata,
            file_save_info=file_save_info
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ingestion endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"error": str(e)}
            ).model_dump()
        )
