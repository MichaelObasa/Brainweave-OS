"""Brainweave-OS Ingestion API - FastAPI application."""

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
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
from services.vision_service import VisionService
from services.router import route_file
import shutil
import os

# --- CONFIGURATION ---
# YOUR GOOGLE DRIVE PATH (The "Vault")
# We use a raw string (r"...") to handle the backslashes and emojis correctly
VAULT_PATH = r"G:\My Drive\Brainweave OS ⚔️"

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
    # Ensure local staging exists
    os.makedirs("staging", exist_ok=True)
    
    logger.info("Brainweave-OS Ingestion API starting up")
    logger.info(f"Vault Path Configured: {VAULT_PATH}")
    
    # Verify we can see the Google Drive
    if os.path.exists(VAULT_PATH):
        logger.info("✅ Connection to Google Drive confirmed.")
    else:
        logger.warning(f"⚠️ WARNING: Could not find Google Drive at {VAULT_PATH}. Check your path!")
        
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


@app.get("/")
async def home():
    """Root endpoint."""
    return {
        "system": "Brainweave OS",
        "status": "Online",
        "vault_connection": "Active" if os.path.exists(VAULT_PATH) else "Disconnected",
        "vault_path": VAULT_PATH
    }


@app.post("/ingest/youtube", response_model=IngestResponse)
async def ingest_youtube(request: IngestRequest):
    """
    Ingest YouTube video: extract transcript, generate metadata, save markdown to Google Drive.
    """
    logger.info(f"Processing ingestion request for URL: {request.url}")
    
    try:
        # Extract video ID
        try:
            video_id = extract_video_id(request.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Extract transcript
        transcript_service = TranscriptService()
        transcript_text, transcript_stats = await transcript_service.get_transcript(
            video_id=video_id,
            language=request.language
        )
        
        # Extract metadata using LLM
        llm_service = LLMService(provider=request.provider)
        metadata = await asyncio.to_thread(
            llm_service.extract_metadata,
            transcript_text,
            request.url
        )
        
        # Save markdown file
        file_save_info = None
        if request.save_markdown:
            # We override the default markdown service to use our Router logic
            # so it goes to the correct "04 Library" folder in Google Drive
            try:
                # Create a temporary file first
                safe_title = "".join([c for c in metadata.title if c.isalnum() or c in " -_"]).strip()
                temp_filename = f"temp_{safe_title}.md"
                temp_path = os.path.join("staging", temp_filename)
                
                # Write content to temp file
                from services.markdown_service import MarkdownService
                md_service = MarkdownService()
                content = md_service._generate_markdown_content(metadata)
                
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # ROUTE IT to Google Drive
                final_path = route_file(temp_path, metadata, VAULT_PATH)
                
                # Create the response object manually since we bypassed the service's save method
                from models.schemas import FileSaveInfo
                file_save_info = FileSaveInfo(
                    filename=os.path.basename(final_path),
                    saved=True,
                    path=final_path
                )
                logger.info(f"✅ Saved to Google Drive: {final_path}")
                
            except Exception as e:
                error_msg = f"Failed to save to Drive: {str(e)}"
                logger.error(error_msg)
                
                # IMPORTANT: Return the error details so Streamlit can see them
                from models.schemas import FileSaveInfo
                file_save_info = FileSaveInfo(
                    filename="ERROR_DURING_SAVE",
                    saved=False,
                    # We hijack the 'path' field to send the error message back to UI
                    path=error_msg
                )
        
        return IngestResponse(
            success=True,
            transcript_stats=transcript_stats,
            metadata=metadata,
            file_save_info=file_save_info
        )
    
    except Exception as e:
        logger.error(f"Error in YouTube ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Magic Upload Endpoint.
    1. Saves upload to temp staging.
    2. Runs Vision Analysis.
    3. Auto-routes to Google Drive.
    """
    # 1. Save to temp staging
    os.makedirs("staging", exist_ok=True)
    temp_path = f"staging/{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Analyze & Route
    try:
        vision = VisionService()
        metadata = vision.analyze_image(temp_path)
        
        # 3. Route to Google Drive
        final_path = route_file(temp_path, metadata, VAULT_PATH)
        
        return {
            "status": "success", 
            "file": final_path, 
            "meta": metadata
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"error": str(e)}