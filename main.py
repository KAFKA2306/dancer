import os
import sys
import logging
from parameter_selection import select_parameters
from video_generation import generate_video
from youtube_upload import upload_video
from database import Database
from error_handling import log_error, send_alert
from apscheduler.schedulers.background import BackgroundScheduler
import yaml

def main():
    # 設定ファイルの読み込み
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    # ログの設定
    logging.basicConfig(filename=config['log_file'], level=logging.ERROR)

    # データベースの初期化
    db = Database(config['database'])

    # スケジューラの設定
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_video, 'cron', hour=config['schedule']['hour'], minute=config['schedule']['minute'])
    scheduler.start()

    print("動画生成システムが開始されました。")

def process_video():
    try:
        # パラメータの選択
        avatar, motion, music, background = select_parameters()

        # 動画の生成
        video_data = generate_video(avatar, motion, music, background)

        # YouTubeへのアップロード
        video_id = upload_video(video_data, config['youtube'])

        # データベースへの保存
        db.save_video(video_id, avatar, motion, music, background)

        print("動画が正常に生成・アップロードされました。")

    except Exception as e:
        # エラーハンドリング
        log_error(str(e))
        send_alert(str(e), config['slack'])

if __name__ == '__main__':
    main()
