"""Instagram Reels through the official Graph API (content publishing). Not exercised against the live API yet:
this environment has no credentials and cannot reach graph.facebook.com."""
from __future__ import annotations

import os
import time
from pathlib import Path

from .. import config
from .base import Blocked, credentials, request


def publish(video: Path, caption: str, date: str) -> dict:
    cfg = config.platforms()["instagram"]
    cred = credentials("instagram")
    base_url = os.environ.get(cfg["public_base_url_env"])
    if not base_url:
        raise Blocked(f"instagram: the Graph API fetches the video from a public URL; set {cfg['public_base_url_env']} "
                      "to where final/ files are hosted")
    api, uid, tok = cfg["api_base"], cred["IG_USER_ID"], cred["IG_ACCESS_TOKEN"]
    r = request("POST", f"{api}/{uid}/media", data={"media_type": "REELS", "video_url": f"{base_url.rstrip('/')}/{video.name}",
                                                    "caption": caption, "share_to_feed": "true", "access_token": tok})
    if r.status_code != 200:
        raise RuntimeError(f"instagram container creation failed: HTTP {r.status_code} {r.text[:300]}")
    container = r.json()["id"]
    for _ in range(60):
        s = request("GET", f"{api}/{container}", params={"fields": "status_code,status", "access_token": tok}).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"instagram processing failed: {s.get('status')}")
        time.sleep(5)
    else:
        raise RuntimeError("instagram processing did not finish within 5 minutes")
    p = request("POST", f"{api}/{uid}/media_publish", data={"creation_id": container, "access_token": tok})
    if p.status_code != 200 or "id" not in p.json():
        raise RuntimeError(f"instagram publish failed: HTTP {p.status_code} {p.text[:300]}")
    return {"platform_id": p.json()["id"]}


def insights(media_id: str) -> dict:
    cfg = config.platforms()["instagram"]
    cred = credentials("instagram")
    metrics = "views,reach,saved,shares,comments,likes,total_interactions,ig_reels_avg_watch_time,ig_reels_video_view_total_time"
    r = request("GET", f"{cfg['api_base']}/{media_id}/insights", params={"metric": metrics, "access_token": cred["IG_ACCESS_TOKEN"]})
    if r.status_code != 200:
        raise RuntimeError(f"instagram insights failed: HTTP {r.status_code} {r.text[:300]}")
    return {m["name"]: m["values"][0]["value"] for m in r.json().get("data", [])}
