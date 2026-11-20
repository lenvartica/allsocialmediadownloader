# All Social Media Downloader — Free Version v1.0.0

Tabbed web app (YouTube, Facebook, TikTok, Instagram, Twitter/X, Reddit, Vimeo, Pinterest).
Paste a link → fetch → download in Normal or HD quality.

- **Frontend:** `public/index.html` (plain HTML/CSS/JS, animated orbs)
- **Backend:** Python serverless functions on Vercel (`api/info.py`, `api/download.py`) using `yt-dlp`

## Structure
```
api/info.py        # returns title, thumbnail, available qualities
api/download.py    # streams the file to the browser as an attachment
lib/extractor.py   # yt-dlp wrapper + per-platform domain allowlist
public/index.html  # UI
requirements.txt
vercel.json
```

## Run locally
```
pip install yt-dlp
npm i -g vercel
vercel dev
```

## Deploy
```
vercel --prod
```
or push to GitHub and import the repo in Vercel.

## Known limits (important)
1. **Datacenter IP blocking.** YouTube, Instagram and Facebook often block Vercel's IPs
   ("Sign in to confirm you're not a bot"). Fixes: route yt-dlp through a residential proxy
   (`"proxy"` option in `lib/extractor.py`) or host the backend on a VPS (Render/Railway/Fly)
   and point the frontend `fetch` calls at it.
2. **No ffmpeg on Vercel.** Only single-file formats (video+audio together) are used, so HD
   tops out where the platform offers a combined file (YouTube combined streams are usually 360p/720p).
3. **Timeouts / size.** Downloads are proxied through a function (60s max, set in `vercel.json`;
   longer needs a paid plan). Big files may be cut off. For large videos, use a VPS backend.
4. **yt-dlp goes stale.** Platforms change often; redeploy regularly to pick up the newest yt-dlp.
5. Respect copyright and each platform's terms. Download only content you own or have permission to save.
