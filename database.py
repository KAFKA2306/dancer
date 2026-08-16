"""SQLite persistence for completed pipeline runs."""

import sqlite3


class Database:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                mode TEXT NOT NULL,
                avatar TEXT NOT NULL,
                motion TEXT NOT NULL,
                music TEXT NOT NULL,
                background TEXT NOT NULL,
                artifact_path TEXT NOT NULL,
                artifact_sha256 TEXT NOT NULL,
                upload_status TEXT NOT NULL,
                youtube_video_id TEXT
            )
            """
        )
        self.conn.commit()

    def get_pipeline_run(self, idempotency_key: str):
        return self.conn.execute(
            "SELECT * FROM pipeline_runs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()

    def save_pipeline_run(
        self,
        *,
        idempotency_key: str,
        mode: str,
        avatar: str,
        motion: str,
        music: str,
        background: str,
        artifact_path: str,
        artifact_sha256: str,
        upload_status: str,
        youtube_video_id: str | None,
    ):
        self.conn.execute(
            """
            INSERT INTO pipeline_runs (
                idempotency_key, mode, avatar, motion, music, background,
                artifact_path, artifact_sha256, upload_status, youtube_video_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                mode,
                avatar,
                motion,
                music,
                background,
                artifact_path,
                artifact_sha256,
                upload_status,
                youtube_video_id,
            ),
        )
        self.conn.commit()
        return self.get_pipeline_run(idempotency_key)
