import json
from abc import ABC, abstractmethod
from pathlib import Path

import yt_dlp

from ytsk.config import EXTERNAL_DIR
from ytsk.utils import sanitize_title


class Downloader(ABC):
    @abstractmethod
    def download(self, url: str, verbose: bool = False) -> Path:
        pass


class YTDownloaderImpl(Downloader):
    """Downloader for YouTube videos."""

    def __init__(self):
        self.ydl_opts = {
            "format": "bestvideo+bestaudio/best",  # Get best video and audio
        }

    def download(self, url: str, verbose: bool = False) -> Path:
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            safe_title = sanitize_title(info["title"])
            outtmpl = (EXTERNAL_DIR / f"{safe_title}.%(ext)s").as_posix()
            opts = {**self.ydl_opts, "outtmpl": outtmpl}
            with yt_dlp.YoutubeDL(opts) as ydl2:
                ydl2.download([url])
                info_file = ydl2.extract_info(url)

        safe_title = sanitize_title(info_file["title"])
        output_path = EXTERNAL_DIR / f"{safe_title}.{info_file['ext']}"

        if verbose:
            info_file_path = f"{safe_title}.json"
            with open(EXTERNAL_DIR / info_file_path, "w") as f:
                json.dump(info_file, f, indent=4)
            print(f"Saved info file to {info_file_path}")

        return output_path


class DownloaderFactory:
    @staticmethod
    def create(source: str) -> Downloader:
        if source == "youtube":
            return YTDownloaderImpl()
        else:
            raise ValueError(f"Invalid source: {source}")
