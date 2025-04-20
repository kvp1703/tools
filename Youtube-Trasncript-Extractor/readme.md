# YouTube Transcript Extractor

This script downloads a YouTube video’s transcript and saves it as a text file in the `transcripts/` directory.
Filenames are derived from the video title (sanitized) and video ID, and each transcript file includes the video URL.

## Features

- Automatically creates a `transcripts/` folder
- Names files using the video title and ID
- Inserts “Video Title” and “Video URL” at the top of each transcript
- Supports language preferences (e.g. `-l en es`)
- Allows custom output filenames

## Prerequisites

- Python 3.1 or higher
- `youtube-transcript-api`
- `pytube`

Install dependencies:
```bash
pip install youtube-transcript-api pytube pytube
