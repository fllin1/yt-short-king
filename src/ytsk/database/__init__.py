"""
Persistence module for ShortVideo entities.

- Generic CRUD: database_crud (StorageStrategy, SQLiteStrategy, FileStrategy, StorageFactory)
- Shorts-specific: database_shorts (ShortVideo, ShortVideoRepository)
"""

from ytsk.database.database_crud import (
    FileStrategy,
    SQLiteStrategy,
    StorageFactory,
    StorageStrategy,
)
from ytsk.database.database_shorts import ShortVideo, ShortVideoRepository

__all__ = [
    "FileStrategy",
    "ShortVideo",
    "ShortVideoRepository",
    "ShortVideoStorage",
    "SQLiteStrategy",
    "StorageFactory",
    "StorageStrategy",
]
