#!/usr/bin/env python3
"""
YouTube Transcript Extractor

This script accepts a YouTube video URL (or share link) and downloads its transcript (subtitles) into a text file stored
in the `transcripts/` directory. Filenames are based on the video title (sanitized) or video ID as fallback.

Prerequisites:
    pip install youtube-transcript-api pytube requests

Usage:
    python youtube_transcript_extractor.py <video_url> [-l LANG1 LANG2 ...] [-o OUTPUT_FILE]

Example:
    python youtube_transcript_extractor.py https://youtu.be/dQw4w9WgXcQ -l en es
"""
import argparse
import os
import re
import sys
from urllib.error import HTTPError
import requests
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from pytube import YouTube


def extract_video_id(url: str) -> str:
    """
    Extracts the 11-character YouTube video ID from a URL or share link.
    Raises ValueError if no valid ID is found.
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|#|$)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid YouTube URL or missing video ID: {url}")


def fetch_video_title(url: str) -> str:
    """
    Tries to fetch YouTube video title via pytube, falls back to scraping page HTML.
    """
    # Primary method: pytube
    try:
        yt = YouTube(url)
        return yt.title
    except Exception:
        pass
    # Fallback: HTTP GET + regex on meta tags or title tag
    response = requests.get(url)
    response.raise_for_status()
    html = response.text
    # Try Open Graph title
    og = re.search(r'<meta property="og:title" content="(.*?)"', html)
    if og:
        return og.group(1)
    # Try <title> tag
    title_tag = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if title_tag:
        title_raw = title_tag.group(1)
        return title_raw.replace(' - YouTube', '').strip()
    raise Exception("Could not retrieve video title from HTML")


def fetch_transcript(video_id: str, languages: list = None) -> list:
    """
    Fetches transcript segments for a given video ID (prefers manual, then auto-generated).
    If `languages` provided, tries transcripts in that order.
    Returns a list of dicts with 'text', 'start', 'duration'.
    Raises NoTranscriptFound, TranscriptsDisabled
    """
    try:
        # direct fetch (auto or manual)
        return YouTubeTranscriptApi.get_transcript(video_id)
    except HTTPError:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        if languages:
            transcripts = transcripts.find_transcript(languages)
        else:
            try:
                transcripts = transcripts.find_manually_created_transcript(
                    [t.lang_code for t in transcripts.manually_created_transcripts]
                )
            except Exception:
                transcripts = transcripts.find_generated_transcript(
                    [t.lang_code for t in transcripts.generated_transcripts]
                )
        return transcripts.fetch()


def save_transcript(transcript: list, output_path: str, url: str, title: str) -> None:
    """
    Saves the transcript to a text file with timestamps,
    including video title and URL at the top.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Video Title: {title}\n")
        f.write(f"Video URL: {url}\n\n")
        for entry in transcript:
            start = entry.get("start", 0.0)
            text = entry.get("text", "")
            f.write(f"[{start:0.2f}] {text}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube transcript into 'transcripts/' folder"
    )
    parser.add_argument("url", help="YouTube video URL or share link")
    parser.add_argument(
        "-l", "--languages", nargs='+',
        help="Preferred languages (ISO codes) in order. E.g., en es fr",
        default=None
    )
    parser.add_argument(
        "-o", "--output",
        help="Custom output filename (default: <sanitized_title>_<video_id>_transcript.txt)",
        default=None
    )
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url.strip())
    except ValueError as ve:
        print(f"❌ URL Error: {ve}")
        sys.exit(1)

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        title = fetch_video_title(canonical_url)
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch title ({e}). Using video ID as title.")
        title = video_id
        safe_title = video_id

    output_dir = "transcripts"
    os.makedirs(output_dir, exist_ok=True)
    default_name = f"{safe_title}_{video_id}_transcript.txt"
    output_filename = args.output or default_name
    output_path = os.path.join(output_dir, output_filename)

    try:
        transcript = fetch_transcript(video_id, args.languages)
        save_transcript(transcript, output_path, canonical_url, title)
        print(f"✅ Transcript saved: '{output_path}'")
    except (NoTranscriptFound, TranscriptsDisabled):
        print("❌ No transcript available for this video.")
        sys.exit(1)
    except HTTPError as he:
        print(f"❌ HTTP Error during transcript fetch: {he}. ``Transcript may not exist or access is restricted.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
