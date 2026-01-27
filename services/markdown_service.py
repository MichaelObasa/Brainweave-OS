"""Markdown file writing service with staging and atomic writes."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from models.schemas import MetadataSchema, FileSaveInfo
from utils.filesystem import create_windows_safe_filename, ensure_directory_exists
from utils.youtube import extract_video_id
from utils.atomic_write import atomic_write_text, copy_with_retries
from config import KNOWLEDGE_VAULT_STAGING_DIR, KNOWLEDGE_VAULT_DIR

logger = logging.getLogger(__name__)


class MarkdownService:
    """Service for writing structured markdown files with staging support."""
    
    def __init__(
        self,
        staging_directory: Optional[Path] = None,
        vault_directory: Optional[Path] = None
    ):
        self.staging_directory = staging_directory or KNOWLEDGE_VAULT_STAGING_DIR
        self.vault_directory = vault_directory or KNOWLEDGE_VAULT_DIR
        ensure_directory_exists(self.staging_directory)
        ensure_directory_exists(self.vault_directory)
    
    def _build_markdown_content(self, metadata: MetadataSchema) -> str:
        """Build markdown content from metadata."""
        formatted_date = self._format_date(metadata.date_published)
        source_value = "A16z"
        speakers = [speaker for speaker in [metadata.host] if speaker]
        if metadata.guests:
            speakers.extend(metadata.guests)
        speakers_value = ", ".join(speakers) if speakers else "Unknown"
        topics_value = ", ".join(metadata.topics) if metadata.topics else "None"
        type_value = metadata.source_type.title() if metadata.source_type else "Unknown"

        lines = [
            f"Title: {metadata.title}",
            f"Date: {formatted_date}",
            f"Source: {source_value}",
            f"Speaker(s): {speakers_value}",
            f"Type: {type_value}",
            f"Topics: {topics_value}",
            "",
            "# Summary",
            "",
            metadata.summary,
            "",
            "—----------------------",
            "",
            "## Transcript",
            "",
            metadata.transcript,
            "",
        ]

        return "\n".join(lines)

    @staticmethod
    def _format_date(date_value: Optional[str]) -> str:
        """Format ISO8601 date string into DD-MM-YYYY."""
        if not date_value:
            return "Unknown"
        try:
            parsed_date = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            return "Unknown"
        return parsed_date.strftime("%d-%m-%Y")
    
    def save_metadata(
        self,
        metadata: MetadataSchema,
        overwrite: bool = False
    ) -> FileSaveInfo:
        """
        Save metadata to markdown file with staging support.
        
        Always writes to staging first (reliable), then attempts to copy to final vault.
        If final vault copy fails due to locks, returns success with staged_path set.
        
        Returns FileSaveInfo with staging and final vault info.
        """
        # Extract video ID from URL
        try:
            video_id = extract_video_id(metadata.source_url)
        except ValueError:
            # Fallback: use hash or timestamp
            video_id = metadata.source_url.split("/")[-1][:11]
        
        # Create filename
        filename = create_windows_safe_filename(metadata.title, video_id)
        staging_path = self.staging_directory / filename
        vault_path = self.vault_directory / filename
        
        # Check if file exists in final vault
        if vault_path.exists() and not overwrite:
            logger.info(f"File already exists in vault, skipping: {vault_path}")
            return FileSaveInfo(
                path=str(vault_path),
                filename=filename,
                skipped=True,
                staged_path=str(staging_path) if staging_path.exists() else None,
                saved=True
            )
        
        # Build markdown content
        content = self._build_markdown_content(metadata)
        
        # Always write to staging first (this should never fail)
        try:
            atomic_write_text(staging_path, content)
            logger.info(f"Saved to staging: {staging_path}")
        except Exception as e:
            logger.error(f"Failed to write to staging {staging_path}: {e}")
            raise IOError(f"Could not write to staging directory: {e}")
        
        # Attempt to copy to final vault (best-effort, may fail due to locks)
        saved_to_vault = False
        error_code = None
        
        try:
            # Check if file exists in vault and we're not overwriting
            if vault_path.exists() and not overwrite:
                logger.info(f"File exists in vault, skipping copy: {vault_path}")
                saved_to_vault = True
            else:
                # Copy with retries
                copy_with_retries(staging_path, vault_path)
                logger.info(f"Successfully copied to vault: {vault_path}")
                saved_to_vault = True
        except PermissionError as e:
            error_code = "FILE_LOCKED"
            logger.warning(
                f"Failed to copy to vault due to lock (staged at {staging_path}): {e}"
            )
        except Exception as e:
            error_code = "COPY_ERROR"
            logger.warning(
                f"Failed to copy to vault (staged at {staging_path}): {e}"
            )
        
        return FileSaveInfo(
            path=str(vault_path) if saved_to_vault else None,
            filename=filename,
            skipped=False,
            staged_path=str(staging_path),
            saved=saved_to_vault,
            error_code=error_code
        )
