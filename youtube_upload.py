"""Simplified YouTube upload stub.

The original project was intended to upload to YouTube via the official API.
For the purposes of this kata we replace that behaviour with a stub that
simply returns a unique identifier based on :mod:`uuid`.
"""
import uuid
from typing import Optional


def upload_video(video_path: str) -> Optional[str]:
    """Pretend to upload ``video_path`` and return a fake video id."""
    # In a real implementation we would use the Google API client here.
    # Returning a uuid keeps the interface stable for downstream consumers.
    return uuid.uuid4().hex
