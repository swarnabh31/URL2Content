"""
YouTubeTranscriptExtractor - Extract transcripts from YouTube videos.
Uses youtube-transcript-api and yt-dlp with multiple fallback strategies.
"""

import os
import re
import tempfile
import logging
from error_handler import AppError

logger = logging.getLogger(__name__)


def extract_transcript(youtube_url: str) -> str:
    """
    Extract the transcript (captions/subtitles) from a YouTube video.
    Falls back through multiple strategies in order of preference.
    Returns the full transcript as plain text.
    """
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        raise AppError("Invalid YouTube URL", f"Could not extract video ID from {youtube_url}")

    errors = []

    # Strategy 1: youtube-transcript-api with list() + fetch()
    try:
        logger.info(f"Attempting Strategy 1 (transcript_api) for video {video_id}")
        return _extract_via_transcript_api(video_id)
    except Exception as e:
        logger.warning(f"Strategy 1 failed: {e}")
        errors.append(f"transcript_api: {e}")

    # Strategy 2: youtube-transcript-api direct api.fetch()
    try:
        logger.info(f"Attempting Strategy 2 (transcript_api_direct) for video {video_id}")
        return _extract_via_transcript_api_direct(video_id)
    except Exception as e:
        logger.warning(f"Strategy 2 failed: {e}")
        errors.append(f"transcript_api_direct: {e}")

    # Strategy 3: yt-dlp subtitles
    try:
        logger.info(f"Attempting Strategy 3 (yt-dlp) for video {video_id}")
        return _extract_via_yt_dlp(youtube_url, video_id)
    except Exception as e:
        logger.warning(f"Strategy 3 failed: {e}")
        errors.append(f"yt-dlp: {e}")

    err_msg = (
        f"Could not extract transcript. The video may not have captions/subtitles available. "
        f"Errors: {'; '.join(errors)}"
    )
    logger.error(err_msg)
    raise AppError("Transcript not available", err_msg)


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/|youtube\.com\/live\/)([a-zA-Z0-9_-]{11})",
        r"[a-zA-Z0-9_-]{11}",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


# ── Strategy 1: youtube-transcript-api with list() ──────────

def _extract_via_transcript_api(video_id: str) -> str:
    """Use YouTubeTranscriptApi.list() to find transcripts, then fetch."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    # Collect candidates: prefer manual, then generated
    candidates = []
    for t in transcript_list:
        if t.is_generated:
            candidates.append(("generated", t))
        else:
            candidates.append(("manual", t))

    if not candidates:
        raise RuntimeError("No transcripts found")

    # Pick best candidate
    transcript_obj = candidates[0][1]

    # Try English directly
    transcript_data = None
    for t in transcript_list:
        if t.language_code.lower().startswith("en"):
            transcript_data = t.fetch()
            break

    # Try translation to English
    if transcript_data is None:
        try:
            translated = transcript_obj.translate("en")
            transcript_data = translated.fetch()
        except Exception:
            pass

    # Final fallback
    if transcript_data is None:
        transcript_data = transcript_obj.fetch()

    text = " ".join([item.text for item in transcript_data])

    if not text.strip():
        raise RuntimeError("Transcript fetched but returned empty text")

    return _clean_transcript_text(text)


# ── Strategy 2: youtube-transcript-api direct fetch ─────────

def _extract_via_transcript_api_direct(video_id: str) -> str:
    """Direct api.fetch() bypassing list_transcripts entirely."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()

    # Try English first
    for lang_list in [["en", "en-US"], ["en-US", "en-GB"], ["en-GB", "en"], ["any"]]:
        try:
            transcript = api.fetch(video_id, languages=lang_list)
            text = " ".join([item.text for item in transcript])
            if text.strip():
                return _clean_transcript_text(text)
        except Exception:
            continue

    raise RuntimeError("Direct fetch failed for all language options")


# ── Strategy 3: yt-dlp subtitles ───────────────────────────

def _extract_via_yt_dlp(youtube_url: str, video_id: str) -> str:
    """Extract subtitles via yt-dlp info dump + direct URL fetch."""
    import yt_dlp

    ydl_opts = {
        "skip_download": True,
        "dump_single_json": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        if info is None:
            raise RuntimeError("Could not extract video info")

    # Get subtitle URLs
    subtitles = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    # Build ordered language list
    lang_priority = ["en", "en-US", "en-GB", "es", "fr", "de", "ja", "ko", "pt", "hi"]

    target_url = None

    for lang in lang_priority:
        if lang in subtitles:
            target_url = subtitles[lang][0]["url"]
            break

    if target_url is None:
        for lang in lang_priority:
            if lang in auto_subs and auto_subs[lang]:
                target_url = auto_subs[lang][0]["url"]
                break

    if target_url is None:
        raise RuntimeError("No subtitles found in yt-dlp info")

    # Download subtitle content directly via urllib
    import urllib.request
    with urllib.request.urlopen(target_url, timeout=15) as resp:
        content = resp.read().decode("utf-8")

    text = _parse_subtitle_content(content)
    cleaned = _clean_transcript_text(text)

    if not cleaned.strip():
        raise RuntimeError("Subtitle file parsed but produced empty text")

    return cleaned


# ── Helpers ──────────────────────────────────────────────────

def _parse_subtitle_content(content: str) -> str:
    """Parse VTT or SRT subtitle content into plain text lines."""
    lines = content.strip().split("\n")
    texts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+$", line):
            continue
        if re.match(r"^0?\d?:\d{2}:\d{2}", line):
            continue
        if line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        texts.append(line)

    return "\n".join(texts)


def _clean_transcript_text(text: str) -> str:
    """Clean and normalize transcript text."""
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove HTML entities
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&apos;", "'").replace("&#39;", "'")
    text = text.replace("&#x27;", "'")
    return text
