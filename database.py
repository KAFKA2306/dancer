# database.py
import sqlite3

class Database:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY,
                video_id TEXT,
                avatar TEXT,
                motion TEXT,
                music TEXT,
                background TEXT
            )
        ''')
        self.conn.commit()

    def save_video(self, video_id, avatar, motion, music, background):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO videos (video_id, avatar, motion, music, background)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, avatar, motion, music, background))
        self.conn.commit()
