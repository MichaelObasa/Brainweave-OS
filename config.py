"""Configuration for Brainweave-OS."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Knowledge vault directories
# Staging: local, fast, reliable (NOT synced)
KNOWLEDGE_VAULT_STAGING_DIR = Path(
    os.getenv("KNOWLEDGE_VAULT_STAGING_DIR", "knowledge_vault_staging")
)

# Final vault: Google Drive synced folder (may have sync delays/locks)
KNOWLEDGE_VAULT_DIR = Path(
    os.getenv("KNOWLEDGE_VAULT_DIR", "knowledge_vault")
)
