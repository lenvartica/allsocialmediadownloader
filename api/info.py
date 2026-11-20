import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.extractor import DownloaderError, extract, validate  # noqa: E402


def human_size(n):
    if not n:
        return None
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        url = (q.get("url") or [""])[0]
        platform = (q.get("platform") or [""])[0]
        try:
            url = validate(url, platform)
            result = {}
            meta = None
            for quality in ("normal", "hd"):
                info = extract(url, quality)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
                meta = meta or info
                result[quality] = {
                    "height": info.get("height"),
                    "ext": info.get("ext"),
                    "size": human_size(info.get("filesize") or info.get("filesize_approx")),
                }
            self._send(200, {
                "ok": True,
                "title": meta.get("title"),
                "thumbnail": meta.get("thumbnail"),
                "uploader": meta.get("uploader"),
                "duration": meta.get("duration"),
                "qualities": result,
            })
        except DownloaderError as e:
            self._send(400, {"ok": False, "error": str(e)})
        except Exception:
            self._send(500, {"ok": False, "error": "Something went wrong fetching that video."})
