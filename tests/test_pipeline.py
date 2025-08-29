import os
import sys
import pathlib

# Ensure project root is on the import path
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from parameter_selection import select_parameters
from video_generation import generate_video
from database import Database


def test_full_pipeline(tmp_path):
    avatar, motion, music, background = select_parameters()
    video_path = generate_video(avatar, motion, music, background, tmp_path)
    assert os.path.exists(video_path)

    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.save_video("vid123", avatar, motion, music, background)

    cursor = db.conn.cursor()
    cursor.execute("SELECT video_id, avatar FROM videos")
    row = cursor.fetchone()
    assert row == ("vid123", avatar)
