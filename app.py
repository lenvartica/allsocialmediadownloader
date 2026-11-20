"""All Social Media Downloader — Free Version v1.0.0

Single Flask app so Vercel's Python runtime finds its entrypoint (app.py).
Static files in /public are served by Vercel's CDN; only /api/* hits this app.

/api/download supports HEAD and Range requests, so download managers
(IDM, Free Download Manager, JDownloader, ADM...) can use it with resume
and multi-connection downloads.
"""
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from urllib.parse import quote

from flask import Flask, Response, jsonify, redirect, request, stream_with_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.extractor import (  # noqa: E402
    DownloaderError, extract, extract_formats, pick_formats, safe_filename, validate,
)

app = Flask(__name__)
VERSION = "1.0.0"


def human_size(n):
    if not n:
        return None
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def content_disposition(filename: str) -> str:
    """Header values must be latin-1; send an ASCII fallback plus RFC 5987 UTF-8 name."""
    base, ext = os.path.splitext(filename)
    ascii_base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    ascii_base = re.sub(r'[^\w\- ]+', "", ascii_base).strip() or "video"
    return f'attachment; filename="{ascii_base}{ext}"; filename*=UTF-8\'\'{quote(filename)}'


def fail(code: int, msg: str):
    """Browsers (Accept: text/html) get sent back to the page with the error shown;
    download managers and scripts get a plain-text error."""
    if request.method == "GET" and "text/html" in request.headers.get("Accept", ""):
        return redirect("/?error=" + quote(msg[:300]), code=303)
    return Response(msg, status=code, mimetype="text/plain")


@app.after_request
def no_store(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/api/health")
def health():
    return jsonify(ok=True, version=VERSION)


@app.get("/api/info")
def info():
    url = request.args.get("url", "")
    platform = request.args.get("platform", "")
    try:
        url = validate(url, platform)
        data = extract_formats(url)
        picks = pick_formats(data)
        if not picks["normal"] and not picks["hd"]:
            raise DownloaderError(
                "No direct download is available for this video (it only offers a streaming format)."
            )
        for q in picks.values():
            if q:
                q["size"] = human_size(q["size"])
        thumb = data.get("thumbnail")
        if not thumb and data.get("thumbnails"):
            thumb = data["thumbnails"][-1].get("url")
        return jsonify(
            ok=True,
            title=data.get("title"),
            thumbnail=thumb,
            uploader=data.get("uploader") or data.get("channel"),
            duration=data.get("duration"),
            qualities=picks,
        )
    except DownloaderError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception:
        return jsonify(ok=False, error="Something went wrong fetching that video."), 500


@app.route("/api/download", methods=["GET", "HEAD"])
def download():
    url = request.args.get("url", "")
    platform = request.args.get("platform", "")
    quality = request.args.get("quality", "normal")
    if quality not in ("normal", "hd"):
        quality = "normal"
    try:
        url = validate(url, platform)
        data = extract(url, quality)
        media_url = data.get("url")
        if not media_url or not str(data.get("protocol", "")).startswith("http"):
            raise DownloaderError(
                "This video uses a streaming format that can't be downloaded in the free version."
            )
        up_headers = dict(data.get("http_headers") or {})
        if request.headers.get("Range"):
            up_headers["Range"] = request.headers["Range"]
        upstream = urllib.request.urlopen(
            urllib.request.Request(media_url, headers=up_headers), timeout=20
        )
    except DownloaderError as e:
        return fail(400, str(e))
    except urllib.error.HTTPError as e:
        if e.code == 416:
            return Response(status=416)
        return fail(502, "The source refused the download request.")
    except Exception:
        return fail(500, "Download failed. The source may have blocked the request.")

    status = getattr(upstream, "status", 200) or 200
    headers = {"Content-Disposition": content_disposition(safe_filename(data.get("title"), data.get("ext") or "mp4"))}
    if upstream.headers.get("Content-Length"):
        headers["Content-Length"] = upstream.headers["Content-Length"]
    if upstream.headers.get("Content-Range"):
        headers["Content-Range"] = upstream.headers["Content-Range"]
    if status == 206 or "bytes" in (upstream.headers.get("Accept-Ranges") or ""):
        headers["Accept-Ranges"] = "bytes"
    mimetype = upstream.headers.get("Content-Type", "video/mp4")

    if request.method == "HEAD":
        upstream.close()
        return Response(status=status, mimetype=mimetype, headers=headers)

    def generate():
        try:
            while True:
                chunk = upstream.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()

    return Response(stream_with_context(generate()), status=status, mimetype=mimetype, headers=headers)


@app.errorhandler(404)
def not_found(_e):
    return jsonify(ok=False, error="Not found"), 404


if __name__ == "__main__":
    app.run(debug=True, port=3000)
