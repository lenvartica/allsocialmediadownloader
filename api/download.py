import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.extractor import DownloaderError, extract, safe_filename, validate  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def _error(self, code, msg):
        body = msg.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        url = (q.get("url") or [""])[0]
        platform = (q.get("platform") or [""])[0]
        quality = (q.get("quality") or ["normal"])[0]
        if quality not in ("normal", "hd"):
            quality = "normal"
        try:
            url = validate(url, platform)
            info = extract(url, quality)
            if "entries" in info and info["entries"]:
                info = info["entries"][0]
            media_url = info.get("url")
            protocol = info.get("protocol", "")
            if not media_url or not protocol.startswith("http"):
                raise DownloaderError(
                    "This video uses a streaming format that can't be downloaded in the free version."
                )
            ext = info.get("ext") or "mp4"
            headers = dict(info.get("http_headers") or {})
            req = urllib.request.Request(media_url, headers=headers)
            upstream = urllib.request.urlopen(req, timeout=20)

            self.send_response(200)
            self.send_header("Content-Type", upstream.headers.get("Content-Type", "video/mp4"))
            length = upstream.headers.get("Content-Length")
            if length:
                self.send_header("Content-Length", length)
            filename = safe_filename(info.get("title"), ext)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while True:
                chunk = upstream.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except DownloaderError as e:
            self._error(400, str(e))
        except Exception:
            self._error(500, "Download failed. The source may have blocked the request.")
