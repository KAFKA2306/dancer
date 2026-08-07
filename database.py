"""SQLite persistence for legacy videos and audited pipeline runs."""

import sqlite3


class Database:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY,
                video_id TEXT,
                avatar TEXT,
                motion TEXT,
                music TEXT,
                background TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                mode TEXT NOT NULL,
                avatar TEXT NOT NULL,
                motion TEXT NOT NULL,
                music TEXT NOT NULL,
                background TEXT NOT NULL,
                artifact_path TEXT,
                artifact_sha256 TEXT,
                generation_status TEXT NOT NULL,
                validation_status TEXT NOT NULL,
                upload_status TEXT NOT NULL,
                youtube_video_id TEXT,
                error TEXT
            )
            """
        )
        self.conn.commit()

    def save_video(self, video_id, avatar, motion, music, background):
        """Legacy compatibility method; new pipeline code uses pipeline_runs."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO videos (video_id, avatar, motion, music, background)
            VALUES (?, ?, ?, ?, ?)
            """,
            (video_id, avatar, motion, music, background),
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
        artifact_path: str | None,
        artifact_sha256: str | None,
        generation_status: str,
        validation_status: str,
        upload_status: str,
        youtube_video_id: str | None,
        error: str | None,
    ):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO pipeline_runs (
                idempotency_key, mode, avatar, motion, music, background,
                artifact_path, artifact_sha256, generation_status,
                validation_status, upload_status, youtube_video_id, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                generation_status,
                validation_status,
                upload_status,
                youtube_video_id,
                error,
            ),
        )
        self.conn.commit()
        return self.get_pipeline_run(idempotency_key)
