"""
YouTube Shorts–specialized persistence layer.

ShortVideo entity and ShortVideoRepository that wraps the generic CRUD layer.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ytsk.database import StorageFactory, StorageStrategy


# -----------------------------------------------------------------------------
# Schema
# -----------------------------------------------------------------------------

SHORTS_SCHEMA: dict[str, Any] = {
    "table": "short_videos",
    "id_column": "id",
    "columns": ["id", "url", "title", "channel", "scraped_at"],
}


# -----------------------------------------------------------------------------
# Entity
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ShortVideo:
    """Domain entity representing a scraped YouTube Short."""

    id: str
    url: str
    title: str
    channel: str
    scraped_at: datetime

    def to_row(self) -> dict[str, Any]:
        """Convert to a dict suitable for storage (row format)."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "channel": self.channel,
            "scraped_at": self.scraped_at.isoformat(),
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> ShortVideo:
        """Create a ShortVideo from a storage row."""
        scraped_at = row["scraped_at"]
        if isinstance(scraped_at, str):
            scraped_at = datetime.fromisoformat(scraped_at)
        return cls(
            id=str(row["id"]),
            url=str(row["url"]),
            title=str(row["title"]),
            channel=str(row["channel"]),
            scraped_at=scraped_at,
        )


# -----------------------------------------------------------------------------
# Repository
# -----------------------------------------------------------------------------


class ShortVideoRepository:
    """YouTube Shorts–specialized repository wrapping a generic StorageStrategy."""

    def __init__(self, strategy: StorageStrategy) -> None:
        self._strategy = strategy
        self._strategy.initialize()

    def get_all_videos(self) -> list[ShortVideo]:
        """Retrieve all ShortVideos from storage."""
        rows = self._strategy.get_all()
        return [ShortVideo.from_row(row) for row in rows]

    def save_video(self, video: ShortVideo) -> None:
        """Persist a single ShortVideo."""
        self.save_batch([video])

    def save_batch(self, videos: list[ShortVideo]) -> None:
        """Persist multiple ShortVideos in an optimized way."""
        self._strategy.save_batch([v.to_row() for v in videos])

    @classmethod
    def from_path(cls, path: str | Path) -> ShortVideoRepository:
        """
        Create a ShortVideoRepository from a storage path.

        Storage type is inferred from path suffix:
        .db/.sqlite -> SQLite; .csv -> CSV; .xlsx -> Excel.
        """
        strategy = StorageFactory.create(path, SHORTS_SCHEMA)
        return cls(strategy)

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ShortVideoRepository:
        """Create a ShortVideoRepository from a config dict with 'path' key."""
        return cls.from_path(config["path"])
