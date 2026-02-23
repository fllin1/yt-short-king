"""
Generic CRUD operations and storage strategies.

Schema-agnostic: works with row dicts. No domain entity knowledge.
Uses pandas for CSV and XLSX.
"""

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd


# -----------------------------------------------------------------------------
# Contract (ABC)
# -----------------------------------------------------------------------------


class StorageStrategy(ABC):
    """Abstract contract for generic row-based persistence."""

    @abstractmethod
    def initialize(self) -> None:
        """Create or ensure the storage backend is ready."""
        ...

    @abstractmethod
    def get_all(self) -> list[dict[str, Any]]:
        """Retrieve all rows as list of dicts."""
        ...

    @abstractmethod
    def save_batch(self, rows: list[dict[str, Any]]) -> None:
        """Persist multiple rows in an optimized way (upsert by id)."""
        ...


# -----------------------------------------------------------------------------
# Strategy: SQLite
# -----------------------------------------------------------------------------


class SQLiteStrategy(StorageStrategy):
    """SQLite-backed storage for generic row dicts."""

    def __init__(self, path: str | Path, schema: dict[str, Any]) -> None:
        self._path = Path(path)
        self._schema = schema
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def _table(self) -> str:
        return str(self._schema.get("table", "rows"))

    def _id_column(self) -> str:
        return str(self._schema.get("id_column", "id"))

    def _columns(self) -> list[str]:
        return list(self._schema.get("columns", []))

    def _build_create_table(self) -> str:
        cols = self._columns()
        if not cols:
            raise ValueError("Schema must include 'columns'")
        id_col = self._id_column()
        parts = []
        for c in cols:
            if c == id_col:
                parts.append(f"{c} TEXT PRIMARY KEY")
            else:
                parts.append(f"{c} TEXT")
        return f"CREATE TABLE IF NOT EXISTS {self._table()} ({', '.join(parts)})"

    def initialize(self) -> None:
        try:
            with self._connect() as conn:
                conn.execute(self._build_create_table())
                conn.commit()
        except sqlite3.Error as e:
            raise RuntimeError(
                f"Failed to initialize SQLite storage at {self._path}: {e}"
            ) from e

    def get_all(self) -> list[dict[str, Any]]:
        cols = self._columns()
        col_list = ", ".join(cols)
        try:
            with self._connect() as conn:
                cur = conn.execute(f"SELECT {col_list} FROM {self._table()}")
                return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to read from SQLite: {e}") from e

    def save_batch(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        cols = self._columns()
        placeholders = ", ".join("?" * len(cols))
        col_list = ", ".join(cols)
        data = [tuple(r.get(c) for c in cols) for r in rows]
        try:
            with self._connect() as conn:
                conn.execute("BEGIN TRANSACTION")
                try:
                    conn.executemany(
                        f"""
                        INSERT OR REPLACE INTO {self._table()} ({col_list})
                        VALUES ({placeholders})
                        """,
                        data,
                    )
                    conn.commit()
                except sqlite3.Error:
                    conn.rollback()
                    raise
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to save batch of {len(rows)} rows: {e}") from e


# -----------------------------------------------------------------------------
# Strategy: File (CSV / XLSX)
# -----------------------------------------------------------------------------


class FileStrategy(StorageStrategy):
    """File-backed storage for generic row dicts (CSV and XLSX via Pandas)."""

    def __init__(
        self,
        path: str | Path,
        schema: dict[str, Any],
        format: str = "csv",
    ) -> None:
        self._path = Path(path)
        self._schema = schema
        fmt = format.lower()
        if fmt not in ("csv", "xlsx"):
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'xlsx'.")
        self._format = fmt
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _id_column(self) -> str:
        return str(self._schema.get("id_column", "id"))

    def _columns(self) -> list[str]:
        return list(self._schema.get("columns", []))

    def _write_df(self, df: pd.DataFrame) -> None:
        cols = self._columns()
        df = df.reindex(columns=cols, fill_value="")
        if self._format == "csv":
            df.to_csv(self._path, index=False)
        else:
            df.to_excel(self._path, index=False, engine="openpyxl")

    def _read_df(self) -> pd.DataFrame:
        try:
            if self._format == "csv":
                return pd.read_csv(self._path)
            return pd.read_excel(self._path, engine="openpyxl")
        except Exception as e:
            raise RuntimeError(f"Failed to read from {self._path}: {e}") from e

    def initialize(self) -> None:
        if not self._path.exists():
            try:
                df = pd.DataFrame(columns=self._columns())
                self._write_df(df)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize file storage at {self._path}: {e}"
                ) from e

    def get_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        cols = self._columns()
        try:
            df = self._read_df()
            if df.empty:
                return []
            df = df.reindex(columns=cols, fill_value="")
            return [
                {c: str(row[c]) if pd.notna(row[c]) else "" for c in cols}
                for _, row in df.iterrows()
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to read from {self._path}: {e}") from e

    def save_batch(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        cols = self._columns()
        id_col = self._id_column()
        try:
            new_df = pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows])
            if self._path.exists():
                existing = self._read_df()
                if id_col in existing.columns and len(existing) > 0:
                    new_ids = set(str(r.get(id_col, "")) for r in rows)
                    existing = existing[~existing[id_col].astype(str).isin(new_ids)]
                    combined = pd.concat([existing, new_df], ignore_index=True)
                else:
                    combined = new_df
            else:
                combined = new_df
            self._write_df(combined)
        except Exception as e:
            raise RuntimeError(
                f"Failed to save batch of {len(rows)} rows to {self._path}: {e}"
            ) from e


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------


class StorageFactory:
    """
    Factory to instantiate the appropriate StorageStrategy from path and schema.
    """

    @staticmethod
    def create(path: str | Path, schema: dict[str, Any]) -> StorageStrategy:
        """
        Create a StorageStrategy from a path and table schema.

        Storage type is inferred from the path suffix:
        .db/.sqlite/.sqlite3 -> SQLite; .csv -> CSV; .xlsx -> Excel

        Schema keys:
        - table: str — table or file base name
        - id_column: str — primary key column name
        - columns: list[str] — ordered column names
        """
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in (".db", ".sqlite", ".sqlite3"):
            return SQLiteStrategy(path, schema=schema)
        if suffix == ".csv":
            return FileStrategy(path, schema=schema, format="csv")
        if suffix == ".xlsx":
            return FileStrategy(path, schema=schema, format="xlsx")
        raise ValueError(
            f"Unknown path suffix '{suffix}'. "
            "Use .db/.sqlite for SQLite, .csv for CSV, .xlsx for Excel."
        )
