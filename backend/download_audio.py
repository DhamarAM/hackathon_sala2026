"""
download_audio.py — Download individual WAV files from Cloudflare R2 on demand.

Called by the frontend dev server when a WAV file is requested but not found locally.
Downloads to the external data directory (outside the repo).

Usage:
    python download_audio.py <filename>
    python download_audio.py 190806_3905.wav

Environment variables (or hardcoded defaults for hackathon):
    R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
    AUDIO_DIR — local directory for WAV files (default: ../../data/audio relative to repo)
"""

import os
import sys
from pathlib import Path

import boto3

# === R2 credentials (hackathon defaults) ===
R2_ENDPOINT = os.environ.get(
    "R2_ENDPOINT",
    "https://6200702e94592ad231a53daba00f8a5d.r2.cloudflarestorage.com",
)
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "93bb95ebfe47d5ef93c45efe3c108ca8")
R2_SECRET_ACCESS_KEY = os.environ.get(
    "R2_SECRET_ACCESS_KEY",
    "cee49fead9c1a8ac2741a4c2703c908efc5d965100a2d8d20c233fce05547a55",
)
R2_BUCKET = os.environ.get("R2_BUCKET", "sala-2026-hackathon-data")

# R2 key prefix for Pilot WAV files
R2_PREFIX = "marine-acoustic/Music_Soundtrap_Pilot/"

# === Local paths ===
REPO_ROOT = Path(__file__).resolve().parent.parent  # hackathon_sala2026/
SALA_ROOT = REPO_ROOT.parent.parent  # SALA/ (two levels above repo: GitHub/hackathon_sala2026)
AUDIO_DIR = Path(os.environ.get(
    "AUDIO_DIR",
    str(SALA_ROOT / "data" / "audio"),  # SALA/data/audio/
))


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def download_file(filename):
    """Download a single WAV file from R2 to the local audio directory."""
    local_path = AUDIO_DIR / filename

    if local_path.exists():
        print(f"ALREADY_EXISTS:{local_path}")
        return str(local_path)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    r2_key = R2_PREFIX + filename
    print(f"DOWNLOADING:{r2_key}", flush=True)

    s3 = get_s3_client()
    tmp_path = local_path.with_suffix(".wav.tmp")

    try:
        s3.download_file(R2_BUCKET, r2_key, str(tmp_path))
        tmp_path.rename(local_path)
        print(f"DONE:{local_path}")
        return str(local_path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        print(f"ERROR:{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_audio.py <filename.wav>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    if not filename.endswith(".wav"):
        filename += ".wav"

    download_file(filename)
