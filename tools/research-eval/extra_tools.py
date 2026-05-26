"""Extra tools beyond the base set in review_tools.py.

  web_search             — Tavily search → ranked results as markdown
  web_fetch              — fetch URL → main content as clean markdown
  render_html_screenshot — Playwright headless render of HTML/URL → PNG
  vision_inspect         — Gemini vision via OpenRouter (OpenAI-compatible)
  video_understand       — ffmpeg + Gemini vision (video frames → text)
  large_doc_reader       — chunked + keyword-search reader for big PDF/HTML/text

These are essential for research review:
  - large_doc_reader  → read the paper PDF
  - web_search        → verify a citation actually exists
  - web_fetch         → pull a cited paper's abstract / authors / venue
  - vision_inspect    → cross-check figures in the PDF against numbers in tables

Configuration (env vars)
────────────────────────
  TAVILY_API_KEY                Tavily key for web_search
  OPENROUTER_API_KEY            OpenRouter key — required for vision/video tools
                                (GEMINI_API_KEY also accepted as fallback)
  GEMINI_BASE_URL               OpenAI-compatible base URL
                                (default: https://openrouter.ai/api/v1)
  GEMINI_MODEL                  model slug used for vision/video calls
                                (default: google/gemini-3-pro-preview)
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


_TOOL_NAMES: set[str] = {
    "web_search",
    "web_fetch",
    "render_html_screenshot",
    "vision_inspect",
    "video_understand",
    "large_doc_reader",
}

_DEFAULT_GEMINI_MODEL = "google/gemini-3-pro-preview"
_DEFAULT_BASE_URL     = "https://openrouter.ai/api/v1"

# No hardcoded credentials — web_search requires TAVILY_API_KEY in the env
# (configurable as a secret after hiring; see manifest.json / api-key.example.md).
_BUILTIN_TAVILY_KEY = ""


def _gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", _DEFAULT_GEMINI_MODEL)


def _gemini_base_url() -> str:
    return os.environ.get("GEMINI_BASE_URL", _DEFAULT_BASE_URL)


def _gemini_api_key() -> str | None:
    return (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )


def _make_openai_client():
    api_key = _gemini_api_key()
    if not api_key:
        return None, "OPENROUTER_API_KEY (or GEMINI_API_KEY) not set in env."
    try:
        from openai import OpenAI
    except ImportError:
        return None, "missing dependency 'openai'. pip install 'openai>=1.30.0'"
    try:
        client = OpenAI(api_key=api_key, base_url=_gemini_base_url())
    except Exception as e:
        return None, f"failed to construct OpenAI client: {e}"
    return client, None


EXTRA_TOOL_SPECS: list[dict] = [
    {
        "name": "web_search",
        "description": (
            "Search the web via Tavily and return ranked results as markdown "
            "(title, URL, snippet). Use to verify a cited paper actually exists, "
            "look up the canonical title/authors/venue of a reference, or check the "
            "factual basis of a claim. Requires TAVILY_API_KEY in env (or built-in fallback)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":        {"type": "string",  "description": "Search query (≤400 chars)."},
                "max_results":  {"type": "integer", "description": "Max results 1–20 (default 5)."},
                "search_depth": {"type": "string",  "enum": ["basic", "advanced"], "description": "Search depth (default 'basic')."},
                "include_raw":  {"type": "boolean", "description": "Include raw page content (default false)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch a URL and return its main content as clean markdown "
            "(strips nav/script/style; truncates at max_chars). "
            "Use to read an arXiv/OpenReview/ACL Anthology page, a project README, or any cited online resource."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url":       {"type": "string",  "description": "Full http/https URL."},
                "max_chars": {"type": "integer", "description": "Max output chars (default 15000)."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "render_html_screenshot",
        "description": (
            "Render a local HTML file (or http(s) URL) to a PNG screenshot using "
            "Playwright headless Chromium. Pair with vision_inspect for HTML/notebook results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source":          {"type": "string"},
                "output_path":     {"type": "string"},
                "full_page":       {"type": "boolean"},
                "viewport_width":  {"type": "integer"},
                "viewport_height": {"type": "integer"},
                "wait_ms":         {"type": "integer"},
            },
            "required": ["source"],
        },
    },
    {
        "name": "vision_inspect",
        "description": (
            "Run Gemini vision on an image with a question — read figures, charts, tables "
            "from a paper PDF (after rendering a page to PNG) or visualize a result file. "
            "Requires OPENROUTER_API_KEY in env."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string"},
                "prompt":     {"type": "string"},
                "model":      {"type": "string"},
            },
            "required": ["image_path", "prompt"],
        },
    },
    {
        "name": "video_understand",
        "description": (
            "Analyse a video by extracting evenly-spaced frames with ffmpeg and "
            "sending them to Gemini vision. Requires ffmpeg+ffprobe on PATH and "
            "OPENROUTER_API_KEY in env."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "prompt":     {"type": "string"},
                "num_frames": {"type": "integer"},
                "model":      {"type": "string"},
            },
            "required": ["video_path", "prompt"],
        },
    },
    {
        "name": "large_doc_reader",
        "description": (
            "Chunked reader for big files (>256KB) — PDF, HTML, plain text/markdown. "
            "Use this to READ THE PAPER (.pdf). Three modes:\n"
            "  overview            — total size, chunk count, headings/TOC, first chunk preview\n"
            "  search (+ query)    — top matching chunks for a keyword/regex\n"
            "  page   (+ chunk_index) — full content of one chunk plus optional N neighbors\n"
            "Each chunk is ~4000 chars by default, paragraph-aligned. PDFs use pypdf."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":        {"type": "string"},
                "mode":        {"type": "string",  "enum": ["overview", "search", "page"]},
                "query":       {"type": "string"},
                "chunk_index": {"type": "integer"},
                "chunk_size":  {"type": "integer"},
                "max_hits":    {"type": "integer"},
                "context":     {"type": "integer"},
            },
            "required": ["path"],
        },
    },
]


class ExtraTools:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._doc_cache: dict[str, tuple[list[str], list[str]]] = {}

    @staticmethod
    def supports(name: str) -> bool:
        return name in _TOOL_NAMES

    def dispatch(self, name: str, args: dict) -> str:
        try:
            if name == "web_search":
                return self._web_search(
                    args["query"],
                    max_results=int(args.get("max_results", 5)),
                    search_depth=args.get("search_depth", "basic"),
                    include_raw=bool(args.get("include_raw", False)),
                )
            if name == "web_fetch":
                return self._web_fetch(
                    args["url"],
                    max_chars=int(args.get("max_chars", 15000)),
                )
            if name == "render_html_screenshot":
                return self._render_html_screenshot(
                    args["source"],
                    output_path=args.get("output_path"),
                    full_page=bool(args.get("full_page", True)),
                    viewport_width=int(args.get("viewport_width", 1280)),
                    viewport_height=int(args.get("viewport_height", 800)),
                    wait_ms=int(args.get("wait_ms", 1500)),
                )
            if name == "vision_inspect":
                return self._vision_inspect(
                    args["image_path"], args["prompt"], model=args.get("model"),
                )
            if name == "video_understand":
                return self._video_understand(
                    args["video_path"], args["prompt"],
                    num_frames=int(args.get("num_frames", 8)),
                    model=args.get("model"),
                )
            if name == "large_doc_reader":
                return self._large_doc_reader(
                    args["path"],
                    mode=args.get("mode", "overview"),
                    query=args.get("query"),
                    chunk_index=args.get("chunk_index"),
                    chunk_size=int(args.get("chunk_size", 4000)),
                    max_hits=int(args.get("max_hits", 5)),
                    context=int(args.get("context", 0)),
                )
        except KeyError as e:
            return f"ERROR: missing required argument: {e}"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
        return f"ERROR: extra tool '{name}' not implemented"

    def _safe_path(self, rel: str) -> Path | None:
        target = (self._root / rel).resolve()
        try:
            target.relative_to(self._root)
        except ValueError:
            return None
        return target

    def _web_search(
        self,
        query: str,
        max_results: int,
        search_depth: str,
        include_raw: bool,
    ) -> str:
        api_key = os.environ.get("TAVILY_API_KEY") or _BUILTIN_TAVILY_KEY
        if not api_key:
            return "ERROR: TAVILY_API_KEY not set in env (and no built-in fallback)."
        try:
            import httpx
        except ImportError:
            return "ERROR: missing dependency 'httpx'. pip install httpx"

        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "search_depth": search_depth,
                    "max_results": max(1, min(20, max_results)),
                    "include_raw_content": include_raw,
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return f"ERROR: Tavily request failed: {e}"

        out = [f"### Search Results for: {query}", ""]
        for i, r in enumerate(data.get("results", []), 1):
            title = r.get("title") or "(no title)"
            url = r.get("url", "")
            content = r.get("raw_content") if include_raw else r.get("content")
            snippet = (content or "").strip()
            if len(snippet) > 3000:
                snippet = snippet[:3000] + "..."
            out.append(f"**[{i}] {title}**")
            if url:
                out.append(f"URL: {url}")
            if snippet:
                out.append("Content:" if include_raw else "Snippet:")
                out.append(snippet)
            out.append("")
        if len(out) == 2:
            out.append("(no results)")
        return "\n".join(out).strip()

    def _web_fetch(self, url: str, max_chars: int) -> str:
        try:
            import httpx
            from bs4 import BeautifulSoup
            import markdownify
        except ImportError as e:
            return (
                f"ERROR: missing dependency: {e}. "
                f"pip install httpx beautifulsoup4 markdownify"
            )

        try:
            resp = httpx.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=15.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception as e:
            return f"ERROR: fetch failed: {e}"

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find("body") or soup
        md = markdownify.markdownify(str(main), heading_style="ATX")
        md = re.sub(r"\n\s*\n", "\n\n", md).strip()
        if len(md) > max_chars:
            md = md[:max_chars] + f"\n\n... (truncated at {max_chars} chars)"
        return f"--- Source: {url} ---\n{md}"

    def _render_html_screenshot(
        self,
        source: str,
        output_path: str | None,
        full_page: bool,
        viewport_width: int,
        viewport_height: int,
        wait_ms: int,
    ) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return (
                "ERROR: missing dependency 'playwright'. "
                "pip install playwright && playwright install chromium"
            )

        if source.startswith(("http://", "https://", "file://")):
            target_url = source
        else:
            local_in = self._safe_path(source)
            if local_in is None or not local_in.exists():
                return f"ERROR: source not found or escapes workspace: {source}"
            target_url = local_in.as_uri()

        if not output_path:
            stem = Path(source).stem or "screenshot"
            output_path = f"__screenshots__/{stem}.png"
        out = self._safe_path(output_path)
        if out is None:
            return f"ERROR: output_path escapes workspace: {output_path}"
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(
                    viewport={"width": viewport_width, "height": viewport_height}
                )
                page = ctx.new_page()
                page.goto(target_url, wait_until="networkidle", timeout=30_000)
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(out), full_page=full_page)
                browser.close()
        except Exception as e:
            return f"ERROR: render failed: {e}"

        size = out.stat().st_size
        return (
            f"OK: rendered {target_url}\n"
            f"  → {out.relative_to(self._root)} ({size:,} B)\n"
            f"Pass this PNG to vision_inspect for content analysis."
        )

    def _vision_inspect(self, image_path: str, prompt: str, model: str | None) -> str:
        local = self._safe_path(image_path)
        if local is None or not local.exists():
            return f"ERROR: image not found or escapes workspace: {image_path}"

        mime = _mime_for(local.suffix.lower(), kind="image")
        if mime is None:
            return (
                f"ERROR: unsupported image extension '{local.suffix}'. "
                f"Use PNG/JPG/WEBP/GIF."
            )

        client, err = _make_openai_client()
        if err is not None:
            return f"ERROR: {err}"

        data_url = _encode_data_url(local.read_bytes(), mime)
        try:
            resp = client.chat.completions.create(
                model=model or _gemini_model(),
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text",      "text": prompt},
                    ],
                }],
            )
        except Exception as e:
            return f"ERROR: vision call failed: {e}"

        text = _extract_openai_text(resp)
        return text or "(empty response)"

    def _video_understand(
        self,
        video_path: str,
        prompt: str,
        num_frames: int,
        model: str | None,
    ) -> str:
        local = self._safe_path(video_path)
        if local is None or not local.exists():
            return f"ERROR: video not found or escapes workspace: {video_path}"

        mime = _mime_for(local.suffix.lower(), kind="video")
        if mime is None:
            return (
                f"ERROR: unsupported video extension '{local.suffix}'. "
                f"Use MP4/MOV/WEBM/MKV/AVI."
            )

        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            return "ERROR: ffmpeg/ffprobe not on PATH. Install with: brew install ffmpeg"

        n = max(1, min(32, num_frames))

        client, err = _make_openai_client()
        if err is not None:
            return f"ERROR: {err}"

        with tempfile.TemporaryDirectory(prefix="researcheval_frames_") as td:
            try:
                frames = _extract_video_frames(local, n=n, out_dir=Path(td))
            except Exception as e:
                return f"ERROR: frame extraction failed: {e}"
            if not frames:
                return "ERROR: ffmpeg produced 0 frames (corrupt or zero-duration video?)"

            content: list[dict] = []
            for fp in frames:
                data_url = _encode_data_url(fp.read_bytes(), "image/jpeg")
                content.append({"type": "image_url", "image_url": {"url": data_url}})
            content.append({
                "type": "text",
                "text": (
                    f"You are looking at {len(frames)} frames sampled evenly from a video "
                    f"({video_path}), in chronological order.\n\nUser question:\n{prompt}"
                ),
            })

            try:
                resp = client.chat.completions.create(
                    model=model or _gemini_model(),
                    messages=[{"role": "user", "content": content}],
                )
            except Exception as e:
                return f"ERROR: video vision call failed: {e}"

        text = _extract_openai_text(resp)
        return text or "(empty response)"

    def _large_doc_reader(
        self,
        path: str,
        mode: str,
        query: str | None,
        chunk_index: int | None,
        chunk_size: int,
        max_hits: int,
        context: int,
    ) -> str:
        local = self._safe_path(path)
        if local is None or not local.exists():
            return f"ERROR: file not found or escapes workspace: {path}"
        if chunk_size <= 0:
            chunk_size = 4000

        cache_key = f"{local}:{chunk_size}"
        cached = self._doc_cache.get(cache_key)
        if cached is not None:
            chunks, headings = cached
        else:
            try:
                text, headings = _extract_text(local)
            except Exception as e:
                return f"ERROR: extraction failed: {e}"
            chunks = _chunkify(text, chunk_size)
            self._doc_cache[cache_key] = (chunks, headings)

        total_chars = sum(len(c) for c in chunks)

        if mode == "overview":
            preview = chunks[0] if chunks else ""
            if len(preview) > 1500:
                preview = preview[:1500] + "..."
            head_block = (
                "\n".join(f"  - {h}" for h in headings[:50]) or "  (no headings detected)"
            )
            return (
                f"DOC OVERVIEW: {local.relative_to(self._root)}\n"
                f"  total_chars: {total_chars:,}\n"
                f"  chunk_size:  {chunk_size}\n"
                f"  num_chunks:  {len(chunks)}\n"
                f"\nTOP HEADINGS (first 50):\n{head_block}\n"
                f"\nCHUNK 0 PREVIEW:\n{preview}"
            )

        if mode == "search":
            if not query:
                return "ERROR: mode='search' requires a 'query' argument."
            try:
                rx = re.compile(query, re.IGNORECASE)
            except re.error as e:
                return f"ERROR: invalid regex: {e}"
            hits: list[tuple[int, int, str]] = []
            for i, c in enumerate(chunks):
                m = rx.search(c)
                if m:
                    snippet = c[max(0, m.start() - 100): m.end() + 200]
                    hits.append((i, m.start(), snippet))
                    if len(hits) >= max_hits:
                        break
            if not hits:
                return f"(no matches for /{query}/ in {len(chunks)} chunks)"
            out = [f"SEARCH '{query}' — {len(hits)} hit(s) (cap {max_hits}):", ""]
            for i, pos, snip in hits:
                out.append(f"--- chunk {i} (offset {pos}) ---")
                out.append(snip.strip())
                out.append("")
            out.append("Use mode='page' with chunk_index=N for the full chunk.")
            return "\n".join(out)

        if mode == "page":
            if chunk_index is None:
                return "ERROR: mode='page' requires 'chunk_index'."
            if not (0 <= chunk_index < len(chunks)):
                return f"ERROR: chunk_index out of range [0, {len(chunks) - 1}]"
            lo = max(0, chunk_index - context)
            hi = min(len(chunks) - 1, chunk_index + context)
            parts = []
            for i in range(lo, hi + 1):
                parts.append(f"--- chunk {i} of {len(chunks)} ---")
                parts.append(chunks[i])
            return "\n".join(parts)

        return f"ERROR: unknown mode '{mode}'. Use overview/search/page."


def _encode_data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _extract_openai_text(resp) -> str:
    try:
        choice = resp.choices[0]
        msg = choice.message
        content = msg.content
    except Exception:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("text")
                if t:
                    parts.append(t)
            else:
                t = getattr(item, "text", None)
                if t:
                    parts.append(t)
        return "\n".join(parts).strip()
    return ""


def _extract_video_frames(video: Path, n: int, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        capture_output=True, text=True, timeout=30,
    )
    try:
        duration = float(probe.stdout.strip())
    except ValueError:
        duration = 0.0

    pattern = str(out_dir / "frame_%03d.jpg")
    if duration > 0:
        fps_expr = f"{n}/{duration}"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video),
            "-vf", f"fps={fps_expr}",
            "-frames:v", str(n),
            "-q:v", "3",
            pattern,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video),
            "-frames:v", str(n),
            "-q:v", "3",
            pattern,
        ]

    subprocess.run(cmd, capture_output=True, timeout=180, check=True)
    return sorted(out_dir.glob("frame_*.jpg"))


def _mime_for(ext: str, kind: str) -> str | None:
    if kind == "image":
        return {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif":  "image/gif",
        }.get(ext)
    if kind == "video":
        return {
            ".mp4":  "video/mp4",
            ".mov":  "video/quicktime",
            ".webm": "video/webm",
            ".mkv":  "video/x-matroska",
            ".avi":  "video/x-msvideo",
        }.get(ext)
    return None


def _extract_text(path: Path) -> tuple[str, list[str]]:
    ext = path.suffix.lower()

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise RuntimeError(
                f"missing dependency 'pypdf' for PDF reading: pip install pypdf ({e})"
            )
        reader = PdfReader(str(path))
        pages: list[str] = []
        for i, page in enumerate(reader.pages):
            try:
                pages.append(f"\n[Page {i + 1}]\n" + (page.extract_text() or ""))
            except Exception:
                pages.append(f"\n[Page {i + 1}]\n(extraction error)")
        text = "\n".join(pages)
        headings = [
            ln.strip() for ln in text.splitlines()
            if 4 <= len(ln.strip()) <= 100
            and ln.strip()[:1].isalpha()
            and ln.strip() == ln.strip().title()
        ][:200]
        return text, headings

    if ext in (".html", ".htm"):
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            raise RuntimeError(
                f"missing dependency 'beautifulsoup4': pip install beautifulsoup4 ({e})"
            )
        raw = path.read_bytes().decode("utf-8", errors="replace")
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside", "header"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        headings = [
            h.get_text(" ", strip=True)
            for h in soup.find_all(["h1", "h2", "h3", "h4"])
        ][:200]
        return text, headings

    text = path.read_bytes().decode("utf-8", errors="replace")
    headings = [
        ln.strip() for ln in text.splitlines()
        if ln.strip().startswith("#")
    ][:200]
    return text, headings


def _chunkify(text: str, chunk_size: int) -> list[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for p in paragraphs:
        plen = len(p) + 2
        if cur_len + plen > chunk_size and cur:
            chunks.append("\n\n".join(cur))
            cur = [p]
            cur_len = plen
        else:
            cur.append(p)
            cur_len += plen
    if cur:
        chunks.append("\n\n".join(cur))

    out: list[str] = []
    for c in chunks:
        if len(c) <= int(chunk_size * 1.5):
            out.append(c)
        else:
            for i in range(0, len(c), chunk_size):
                out.append(c[i: i + chunk_size])
    return out
