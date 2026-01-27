"""Batch runner for processing queued YouTube URLs."""

import sys
import time
import subprocess
from pathlib import Path

import requests

QUEUE_FILE = Path(__file__).with_name("queue.txt")
ENDPOINT = "http://localhost:8000/ingest/youtube"
SLEEP_SECONDS = 15


def load_queue() -> list[str]:
    if not QUEUE_FILE.exists():
        return []
    lines = [line.strip() for line in QUEUE_FILE.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line]


def ingest_url(url: str) -> str:
    response = requests.post(ENDPOINT, json={"url": url}, timeout=600)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", True):
        raise RuntimeError(f"Ingest failed for {url}: {payload}")
    title = payload.get("metadata", {}).get("title")
    if not title:
        title = "Untitled Video"
    return " ".join(title.split())


def run_git_commands(title: str) -> None:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Added notes for {title}"], check=True)
    subprocess.run(["git", "push"], check=True)


def main() -> int:
    urls = load_queue()
    if not urls:
        print("No URLs found in queue.txt")
        return 0

    total = len(urls)
    for index, url in enumerate(urls, start=1):
        try:
            title = ingest_url(url)
            run_git_commands(title)
        except requests.RequestException as exc:
            print(f"Failed to ingest {url}: {exc}", file=sys.stderr)
            continue
        except subprocess.CalledProcessError as exc:
            print(f"Git command failed for {url}: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            continue

        print(f"✅ {title} Done")

        if index < total:
            time.sleep(SLEEP_SECONDS)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
