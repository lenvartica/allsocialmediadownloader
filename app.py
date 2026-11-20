"""All Social Media Downloader — Free Version v1.0.0

Single Flask app so Vercel's Python runtime finds its entrypoint (app.py).
Static files in /public are served by Vercel's CDN; only /api/* hits this app.
"""
import os
import sys
import urllib.request

from flask import Flask, Response, jsonify, request, stream_with_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.extractor import DownloaderError, extract, safe_filename, validate  # noqa: E402

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
        qualities, meta = {}, None
        for quality in ("normal", "hd"):
            data = extract(url, quality)
            if data.get("entries"):
                data = data["entries"][0]
            meta = meta or data
            qualities[quality] = {
                "height": data.get("height"),
                "ext": data.get("ext"),
                "size": human_size(data.get("filesize") or data.get("filesize_approx")),
            }
        return jsonify(
            ok=True,
            title=meta.get("title"),
            thumbnail=meta.get("thumbnail"),
            uploader=meta.get("uploader"),
            duration=meta.get("duration"),
            qualities=qualities,
        )
    except DownloaderError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception:
        return jsonify(ok=False, error="Something went wrong fetching that video."), 500


@app.get("/api/download")
def download():
    url = request.args.get("url", "")
    platform = request.args.get("platform", "")
    quality = request.args.get("quality", "normal")
    if quality not in ("normal", "hd"):
        quality = "normal"
    try:
        url = validate(url, platform)
        data = extract(url, quality)
        if data.get("entries"):
            data = data["entries"][0]
        media_url = data.get("url")
        if not media_url or not str(data.get("protocol", "")).startswith("http"):
            raise DownloaderError(
                "This video uses a streaming format that can't be downloaded in the free version."
            )
        req = urllib.request.Request(media_url, headers=dict(data.get("http_headers") or {}))
        upstream = urllib.request.urlopen(req, timeout=20)
    except DownloaderError as e:
        return Response(str(e), status=400, mimetype="text/plain")
    except Exception:
        return Response("Download failed. The source may have blocked the request.",
                        status=500, mimetype="text/plain")

    def generate():
        try:
            while True:
                chunk = upstream.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()

    filename = safe_filename(data.get("title"), data.get("ext") or "mp4")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    length = upstream.headers.get("Content-Length")
    if length:
        headers["Content-Length"] = length
    return Response(
        stream_with_context(generate()),
        mimetype=upstream.headers.get("Content-Type", "video/mp4"),
        headers=headers,
    )


@app.errorhandler(404)
def not_found(_e):
    return jsonify(ok=False, error="Not found"), 404


if __name__ == "__main__":
    app.run(debug=True, port=3000)
