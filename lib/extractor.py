"""Shared helpers: platform validation + yt-dlp extraction.

Optional environment variables (set in Vercel > Settings > Environment Variables):
  YTDLP_PROXY    e.g. http://user:pass@host:port   (residential proxy avoids datacenter blocks)
  YTDLP_COOKIES  contents of a Netscape-format cookies.txt (lets yt-dlp see login-gated videos)
"""
import os
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

# No ffmpeg on Vercel, so only pick single-file (audio+video) HTTP formats.
# "<=?" also accepts formats whose height is unknown; [protocol^=http] skips HLS/DASH.
QUALITY = {
    "normal": "best[height<=?480][protocol^=http]/worst[protocol^=http]",
    "hd": "best[height<=?1080][protocol^=http]/best[protocol^=http]",
}
LIST_FORMAT = "best/bestvideo*/worst"

COOKIE_PATH = "/tmp/yt_cookies.txt"


class DownloaderError(Exception):
    pass


def validate(url: str, platform: str) -> str:
    url = (url or "").strip()
    if len(url) > 2000:
        raise DownloaderError("That link is too long.")
    if not re.match(r"^https?://", url, re.I):
        raise DownloaderError("Please paste a full link starting with https://")
    host = (urlparse(url).hostname or "").lower()
    allowed = PLATFORMS.get(platform)
    if not allowed:
        raise DownloaderError("Unknown platform tab.")
    if not any(host == d or host.endswith("." + d) for d in allowed):
        raise DownloaderError(f"That link doesn't look like a {platform.title()} link.")
    return url


def _options(fmt: str) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "format": fmt,
        "ignore_no_formats_error": True,
        "socket_timeout": 15,
        "retries": 2,
        "geo_bypass": True,
    }
    proxy = os.environ.get("YTDLP_PROXY")
    if proxy:
        opts["proxy"] = proxy
    cookies = os.environ.get("YTDLP_COOKIES")
    if cookies:
        try:
            with open(COOKIE_PATH, "w") as f:
                f.write(cookies)
            opts["cookiefile"] = COOKIE_PATH
        except OSError:
            pass
    return opts


def _is_facebook(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in PLATFORMS["facebook"])


def _facebook_candidates(url: str) -> list:
    """Same video, different URL shapes. yt-dlp's parser works on some and not others."""
    out = [url]
    m = re.search(r"(?:/videos/(?:[^/?#]+/)?|[?&]v=|/reel/)(\d{6,})", url)
    if m:
        vid = m.group(1)
        out += [
            f"https://www.facebook.com/watch/?v={vid}",
            f"https://www.facebook.com/reel/{vid}",
            f"https://www.facebook.com/video.php?v={vid}",
            f"https://m.facebook.com/watch/?v={vid}",
        ]
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def _friendly(msg: str, facebook: bool) -> str:
    low = msg.lower()
    if facebook and any(k in low for k in ("cannot parse data", "login", "log in", "private", "unavailable", "unsupported url")):
        return ("Couldn't read this Facebook video. It may be private, friends-only or restricted, "
                "or Facebook is blocking this server. Try a public video link "
                "(facebook.com/watch/?v=… or a public reel).")
    if any(k in low for k in ("sign in to confirm", "not a bot", "confirm you")):
        return "The platform is blocking this server right now. Please try again later."
    if "private" in low or "login required" in low or "requires authentication" in low:
        return "This video is private or needs a login, so it can't be downloaded."
    if "unsupported url" in low:
        return "That link isn't a direct video link. Open the video itself and copy its link."
    if "429" in low or "too many requests" in low:
        return "Too many requests. Please wait a minute and try again."
    return (msg or "Could not fetch that video.")[:300]


def _run(url: str, fmt: str) -> dict:
    facebook = _is_facebook(url)
    candidates = _facebook_candidates(url) if facebook else [url]
    last_err = ""
    for candidate in candidates:
        try:
            with yt_dlp.YoutubeDL(_options(fmt)) as ydl:
                info = ydl.extract_info(candidate, download=False)
            if info:
                if info.get("entries"):
                    entries = list(info["entries"])
                    info = entries[0] if entries else None
                if info:
                    return info
            last_err = "No video found at that link."
        except yt_dlp.utils.DownloadError as e:
            last_err = re.sub(r"\x1b\[[0-9;]*m", "", str(e)).replace("ERROR: ", "")
        except Exception as e:  # parser crashes etc.
            last_err = str(e)
    raise DownloaderError(_friendly(last_err, facebook))


def extract(url: str, quality: str = "normal") -> dict:
    """Resolve one downloadable single-file format for the chosen quality."""
    return _run(url, QUALITY.get(quality, QUALITY["normal"]))


def extract_formats(url: str) -> dict:
    """One extraction that returns every format, so /api/info needs only one network round trip."""
    return _run(url, LIST_FORMAT)


def _size(f):
    return f.get("filesize") or f.get("filesize_approx")


def pick_formats(info: dict) -> dict:
    """Choose the normal/HD single-file HTTP formats from an extraction result."""
    fmts = [
        f for f in (info.get("formats") or [])
        if f.get("vcodec") != "none" and f.get("acodec") != "none"
        and str(f.get("protocol", "")).startswith("http") and f.get("url")
    ]
    if not fmts and info.get("url") and str(info.get("protocol", "")).startswith("http"):
        fmts = [info]  # extractors that return a single format (TikTok, Twitter, ...)

    def h(f):
        return f.get("height") or 0

    out = {"normal": None, "hd": None}
    if fmts:
        small = [f for f in fmts if h(f) <= 480]
        out["normal"] = max(small, key=h) if small else min(fmts, key=h)
        hd = [f for f in fmts if h(f) <= 1080]
        out["hd"] = max(hd, key=h) if hd else min(fmts, key=h)
    return {
        k: ({"height": v.get("height"), "ext": v.get("ext"), "size": _size(v)} if v else None)
        for k, v in out.items()
    }


def safe_filename(title: str, ext: str) -> str:
    title = re.sub(r"[^\w\- ]+", "", title or "video").strip()[:80] or "video"
    return f"{title}.{ext}"
