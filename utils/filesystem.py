"""Filesystem utilities for Windows-safe file operations."""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


# Windows reserved names and invalid characters
WINDOWS_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
}

WINDOWS_INVALID_CHARS = r'<>:"/\|?*'


def create_windows_safe_filename(title: str, video_id: str, max_length: int = 200) -> str:
    """
    Create a Windows-safe filename from title and video ID.
    
    Format: YYYY-MM-DD__slug__VIDEO_ID.md
    """
    # Create slug from title
    slug = title.lower()
    # Replace spaces and invalid chars with hyphens
    slug = re.sub(rf'[{re.escape(WINDOWS_INVALID_CHARS)}\s]+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate slug if too long (leave room for date, video_id, extension)
    date_prefix_len = 11  # "YYYY-MM-DD__"
    video_id_len = len(video_id) + 4  # "__VIDEO_ID.md"
    max_slug_len = max_length - date_prefix_len - video_id_len
    if len(slug) > max_slug_len:
        slug = slug[:max_slug_len].rstrip('-')
    
    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Construct filename
    filename = f"{today}__{slug}__{video_id}.md"
    
    # Final safety check: ensure no reserved names
    name_without_ext = filename.rsplit('.', 1)[0]
    if name_without_ext.upper() in WINDOWS_RESERVED_NAMES:
        filename = f"video__{slug}__{video_id}.md"
    
    return filename


def ensure_directory_exists(directory: Path) -> None:
    """Ensure directory exists, create if it doesn't."""
    directory.mkdir(parents=True, exist_ok=True)
