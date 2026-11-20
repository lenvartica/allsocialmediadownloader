"""Shared helpers: platform validation + yt-dlp extraction."""
import re
from urllib.parse import urlparse

import yt_dlp

# Tab name -> allowed hostnames (suffix match). Server-side allowlist so the
# API cannot be used as a generic proxy for arbitrary sites.
PLATFORMS = {
    "youtube": ["youtube.com", "youtu.be"],
    "facebook": ["facebook.com", "fb.watch", "fb.com"],
    "tiktok": ["tiktok.com"],
    "instagram": ["instagram.com"],
    "twitter": ["twitter.com", "x.com"],
    "reddit": ["reddit.com", "redd.it"],
    "vimeo": ["vimeo.com"],
    "pinterest": ["pinterest.com", "pin.it"],
}

# No ffmpeg on Vercel, so only pick single-file (audio+video) formats.
QUALITY = {
    "normal": "best[height<=480]/worst",
    "hd": "best[height<=1080]/best",
}


class DownloaderError(Exception):
    pass


def validate(url: str, platform: str) -> str:
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise DownloaderError("Please paste a full link starting with https://")
    host = (urlparse(url).hostname or "").lower()
    allowed = PLATFORMS.get(platform)
    if not allowed:
        raise DownloaderError("Unknown platform tab.")
    if not any(host == d or host.endswith("." + d) for d in allowed):
        raise DownloaderError(f"That link doesn't look like a {platform.title()} link.")
    return url


def extract(url: str, quality: str = "normal") -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "format": QUALITY.get(quality, QUALITY["normal"]),
        "socket_timeout": 15,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = re.sub(r"\x1b\[[0-9;]*m", "", str(e))
        raise DownloaderError(msg.replace("ERROR: ", "")[:300])


def safe_filename(title: str, ext: str) -> str:
    title = re.sub(r"[^\w\- ]+", "", title or "video").strip()[:80] or "video"
    return f"{title}.{ext}"
