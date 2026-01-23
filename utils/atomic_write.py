"""Atomic file operations with Windows/Google Drive sync lock handling."""

import os
import time
import uuid
import shutil
from pathlib import Path
from typing import Optional

# Windows error codes for file locks
LOCK_ERRNOS = {32, 5}  # WinError 32 (in use), 5 (access denied)


def _is_windows_lock_error(e: Exception) -> bool:
    """Check if exception is a Windows file lock error."""
    winerror = getattr(e, "winerror", None)
    return winerror in LOCK_ERRNOS


def atomic_write_text(path: Path, content: str) -> Path:
    """
    Atomically write text content to a file.
    
    Writes to a temp file, fsyncs, then atomically replaces the target.
    This ensures the file is either fully written or not present (no partial files).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{uuid.uuid4().hex}")
    
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        # Atomic replace on same filesystem
        os.replace(tmp, path)
        return path
    except Exception:
        # Clean up temp file on error
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass
        raise


def copy_with_retries(
    src: Path,
    dst: Path,
    attempts: int = 8,
    base_delay: float = 0.15
) -> None:
    """
    Copy file with retries for Windows/Google Drive sync locks.
    
    Uses exponential backoff with jitter to handle transient lock errors.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    last_err = None
    for i in range(attempts):
        try:
            # Copy to temp in destination dir, then replace (reduces partial files)
            tmp_dst = dst.with_suffix(dst.suffix + f".copytmp.{uuid.uuid4().hex}")
            shutil.copyfile(src, tmp_dst)
            os.replace(tmp_dst, dst)
            return
        except PermissionError as e:
            last_err = e
            if _is_windows_lock_error(e):
                # Backoff with a bit of jitter
                time.sleep(base_delay * (2 ** i) + (0.02 * i))
                continue
            raise
        except OSError as e:
            last_err = e
            if _is_windows_lock_error(e):
                time.sleep(base_delay * (2 ** i) + (0.02 * i))
                continue
            raise
        finally:
            # Clean up temp file if it exists
            if 'tmp_dst' in locals() and tmp_dst.exists():
                try:
                    tmp_dst.unlink()
                except Exception:
                    pass
    
    raise PermissionError(
        f"Destination file stayed locked after {attempts} attempts: {dst}"
    ) from last_err
