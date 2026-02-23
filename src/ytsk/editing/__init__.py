"""Editing module for audio and video processing.

- audio_speech_to_text: Whisper large-v3-turbo transcriber
- video_cuts_detect: scenedetect scene detection
- video_get_audio: extract audio from downloaded videos
- video_download: download videos from YouTube
"""

from ytsk.editing.audio_speech_to_text import TranscriberFactory
from ytsk.editing.video_cuts_detect import CutsDetectorFactory
from ytsk.editing.video_get_audio import extract_audio
from ytsk.editing.video_download import DownloaderFactory

__all__ = [
    "TranscriberFactory",
    "CutsDetectorFactory",
    "extract_audio",
    "DownloaderFactory",
]
