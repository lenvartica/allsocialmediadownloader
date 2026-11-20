# All Social Media Downloader — Free Version v1.0.0

Tabbed web app (YouTube, Facebook, TikTok, Instagram, Twitter/X, Reddit, Vimeo, Pinterest).
Paste a link → fetch → download in Normal or HD quality.

- **Frontend:** `public/index.html` (plain HTML/CSS/JS, animated orbs)
- **Backend:** Flask (`app.py`) on Vercel's Python runtime using `yt-dlp`

## Structure
```
app.py             # Flask app: /api/info, /api/download, /api/health (Vercel entrypoint)
lib/extractor.py   # yt-dlp wrapper + per-platform domain allowlist
public/index.html  # UI
requirements.txt
vercel.json
```

## Run locally
```
pip install -r requirements.txt
python app.py        # API on http://localhost:3000
# or: npm i -g vercel && vercel dev
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

## SEO / meta / tracking
- `public/index.html` head: charset, viewport, description, robots, canonical, Open Graph (Facebook/Instagram/WhatsApp),
  Twitter/X card, Apple/Android/Windows meta, favicons, manifest, JSON-LD.
- `public/sitemap.xml`, `robots.txt`, `site.webmanifest`, `browserconfig.xml`, `humans.txt`, `.well-known/security.txt`.
- **Replace** `https://allsocialmediadownloader.vercel.app` everywhere with your real domain (search & replace).
- Pixels: put your IDs in `public/config.js` (Meta Pixel, GA4, TikTok, Clarity). Empty = off.
