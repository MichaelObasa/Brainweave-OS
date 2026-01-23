# Brainweave-OS Ingestion API

A robust YouTube ingestion pipeline that extracts transcripts, generates structured metadata using LLMs, and saves markdown files for your knowledge vault.

## Features

- **YouTube Transcript Extraction**: Handles various URL formats, auto/manual captions, multiple languages
- **Structured Metadata Extraction**: Uses OpenAI or Gemini to extract host, guests, topics, tags, summary, and key points
- **Markdown Storage**: Saves structured markdown files with YAML frontmatter to `knowledge_vault/`
- **Idempotent**: Won't re-process videos unless `overwrite=true`
- **Robust Error Handling**: Clear error codes and messages for common failure modes
- **Windows-Safe**: Handles Windows filename restrictions and Google Drive sync

## Requirements

- Python 3.12+
- Windows 11 (or compatible OS)
- OpenAI API key OR Gemini API key

## Setup

1. **Clone and navigate to the repository:**
   ```bash
   cd brainweave-os
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   
   Create a `.env` file in the project root (or set system environment variables):
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   # OR
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Optional: Custom vault directories (defaults shown)
   KNOWLEDGE_VAULT_STAGING_DIR=knowledge_vault_staging
   KNOWLEDGE_VAULT_DIR=knowledge_vault
   ```
   
   The API will default to OpenAI if both are set.
   
   **Vault Configuration:**
   - `KNOWLEDGE_VAULT_STAGING_DIR`: Local staging directory (fast, reliable, NOT synced)
   - `KNOWLEDGE_VAULT_DIR`: Final vault directory (typically Google Drive synced folder)

5. **Start the server:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```bash
GET /health
```

Returns: `{"status": "ok"}`

### Ingest YouTube Video
```bash
POST /ingest/youtube
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "provider": "openai",           # optional: "openai" | "gemini", default: "openai"
  "language": "en",                # optional: preferred transcript language, default: "en"
  "save_markdown": true,           # optional: save markdown file, default: true
  "overwrite": false               # optional: overwrite existing files, default: false
}
```

**Response:**
```json
{
  "success": true,
  "transcript_stats": {
    "character_count": 12345,
    "language": "en",
    "source": "manual",
    "segment_count": 150
  },
  "metadata": {
    "title": "Video Title",
    "source_url": "https://www.youtube.com/watch?v=...",
    "source_type": "youtube",
    "date_published": "2024-01-15T10:30:00Z",
    "host": "John Doe",
    "guests": ["Jane Smith"],
    "topics": ["Artificial Intelligence", "Venture Capital"],
    "tags": ["#AI", "#VC"],
    "summary": "3-5 paragraph executive summary...",
    "key_points": ["Point 1", "Point 2", ...],
    "transcript": "Full transcript text...",
    "chapters": [...]
  },
  "file_save_info": {
    "path": "knowledge_vault/2026-01-23__video-title__VIDEO_ID.md",
    "filename": "2026-01-23__video-title__VIDEO_ID.md",
    "skipped": false
  }
}
```

## Example Usage

### Using curl:
```bash
curl -X POST "http://localhost:8000/ingest/youtube" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "provider": "openai",
    "save_markdown": true
  }'
```

### Using Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/ingest/youtube",
    json={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "provider": "openai",
        "save_markdown": True
    }
)

print(response.json())
```

## Error Handling

The API returns structured error responses:

```json
{
  "error_code": "TRANSCRIPTS_DISABLED",
  "message": "This video has captions disabled. Cannot extract transcript.",
  "details": {
    "video_id": "dQw4w9WgXcQ"
  }
}
```

**Common Error Codes:**
- `INVALID_URL`: Could not extract video ID from URL
- `TRANSCRIPTS_DISABLED`: Video has captions disabled
- `NO_TRANSCRIPT_FOUND`: No transcript available in requested language
- `VIDEO_UNAVAILABLE`: Video is private, deleted, or region-restricted
- `RATE_LIMITED`: YouTube API rate limit exceeded
- `LLM_VALIDATION_ERROR`: LLM returned invalid JSON
- `LLM_EXTRACTION_ERROR`: LLM API call failed

## Project Structure

```
brainweave-os/
├── main.py                 # FastAPI application
├── models/                 # Pydantic models
│   ├── __init__.py
│   └── schemas.py
├── services/               # Business logic
│   ├── __init__.py
│   ├── transcript_service.py
│   ├── llm_service.py
│   └── markdown_service.py
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── youtube.py
│   └── filesystem.py
├── knowledge_vault/         # Output directory (created automatically)
├── requirements.txt
├── .gitignore
└── README.md
```

## Markdown File Format

Saved markdown files include:

1. **YAML Frontmatter**: Title, URL, date, host, guests, topics, tags
2. **Summary**: 3-5 paragraph executive summary
3. **Key Points**: Bulleted list of main takeaways
4. **Chapters**: Optional chapter breakdown with timestamps
5. **Transcript**: Full transcript text

Files are saved with Windows-safe filenames: `YYYY-MM-DD__slug__VIDEO_ID.md`

**Staging + Vault Architecture:**
- Files are **always** written to staging first (`knowledge_vault_staging/`) - this is fast and reliable
- Then copied to the final vault (`knowledge_vault/`) - may fail due to Google Drive sync locks
- If vault copy fails, the file remains in staging and the API still returns success with metadata
- This ensures ingestion never fails due to sync issues - you always get your data

**Response includes:**
- `staged_path`: Always present if file was saved (staging location)
- `path`: Final vault path (may be null if copy failed)
- `saved`: Boolean indicating if copy to vault succeeded
- `error_code`: Error code if vault copy failed (e.g., "FILE_LOCKED")

## Testing

Run the smoke test script:
```bash
python smoke_test.py
```

Or test manually:
```bash
# Health check
curl http://localhost:8000/health

# Ingest a video
curl -X POST http://localhost:8000/ingest/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## Notes

- Long transcripts are automatically chunked for LLM processing
- The API is idempotent: ingesting the same video twice won't duplicate work unless `overwrite=true`
- Markdown files are saved with LF line endings for consistency
- Google Drive Desktop sync is supported (handles file locks gracefully)
- Windows filename restrictions are automatically handled

## License

See LICENSE file.
