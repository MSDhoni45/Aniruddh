"""Publish orchestration: gate, duplicate check, platform call, ledger. Reports success only on platform confirmation."""
from __future__ import annotations

from pathlib import Path

from .. import config
from ..util import logger, read_json
from . import base, instagram, youtube

log = logger("publish")


def package(date: str) -> dict:
    """Post text per platform, taken from the day's brief data."""
    p = config.path("daily", date, "brief.json")
    if not p.exists():
        raise base.Blocked(f"no brief data for {date}")
    b = read_json(p)
    tags = " ".join(b["hashtags"])
    return {
        "instagram": {"file": f"final/{date}_instagram.mp4", "caption": f"{b['instagram_caption']}\n\n{tags}"},
        "linkedin": {"file": f"final/{date}_linkedin.mp4", "caption": b["linkedin_caption"]},
        "x": {"file": f"final/{date}_x.mp4", "caption": b["x_caption"]},
        "youtube": {"file": f"final/{date}_youtube.mp4", "title": b.get("youtube_title", b["selected_story"])[:100],
                    "description": f"{b['linkedin_caption']}\n\n#Shorts {tags}", "tags": [h.lstrip('#') for h in b["hashtags"]]},
    }


def publish(date: str, platform: str, reviewed: bool = False, dry_run: bool = False, ledger_path: Path | None = None) -> dict:
    result = {"date": date, "platform": platform}
    try:
        if not config.platforms().get(platform, {}).get("enabled"):
            raise base.Blocked(f"{platform}: no API adapter; post manually using the prepared package")
        base.gate(date, reviewed)
        pkg = package(date)[platform]
        video = config.path(pkg["file"])
        if not video.exists():
            raise base.Blocked(f"final video missing: {pkg['file']}")
        digest = base.sha256(video)
        prior = base.already_published(platform, digest, date, ledger_path)
        if prior:
            return {**result, "status": "skipped_duplicate", "platform_id": prior.get("platform_id")}
        base.credentials(platform)
        if dry_run:
            return {**result, "status": "dry_run_ok", "sha256": digest}
        if platform == "instagram":
            out = instagram.publish(video, pkg["caption"], date)
        else:
            out = youtube.publish(video, pkg["title"], pkg["description"], pkg["tags"], date)
        result.update(status="published", sha256=digest, **out)
    except base.Blocked as exc:
        result.update(status="blocked", reason=str(exc))
    except Exception as exc:  # platform or network failure: recorded, never reported as success
        result.update(status="failed", reason=str(exc)[:500])
    base.record(result, ledger_path)
    log.info("publish %s %s -> %s", date, platform, result["status"])
    return result
