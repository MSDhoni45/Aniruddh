"""YouTube Shorts through the official Data API v3 resumable upload. Not exercised against the live API yet:
no OAuth token is configured in this environment."""
from __future__ import annotations

import json
from pathlib import Path

from .. import config
from .base import credentials, request


def publish(video: Path, title: str, description: str, tags: list[str], date: str) -> dict:
    tok = credentials("youtube")["YT_ACCESS_TOKEN"]
    meta = {"snippet": {"title": title[:100], "description": description, "tags": tags, "categoryId": config.platforms()["youtube"]["category_id"]},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    size = video.stat().st_size
    start = request("POST", "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                             "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}, data=json.dumps(meta))
    if start.status_code != 200 or "Location" not in start.headers:
        raise RuntimeError(f"youtube upload start failed: HTTP {start.status_code} {start.text[:300]}")
    with open(video, "rb") as fh:
        up = request("PUT", start.headers["Location"], headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"},
                     data=fh, timeout=600, attempts=1)
    if up.status_code not in (200, 201) or "id" not in up.json():
        raise RuntimeError(f"youtube upload failed: HTTP {up.status_code} {up.text[:300]}")
    return {"platform_id": up.json()["id"]}
