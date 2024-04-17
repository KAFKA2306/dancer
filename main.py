# main.py
from parameter_selection import select_parameters
from video_generation import generate_video
from youtube_upload import upload_video
from database import Database
from error_handling import log_error, send_alert
from apscheduler.schedulers.background import BackgroundScheduler

def main():
    # データベースの初期化
    db = Database('database.db')

    # スケジューラの設定
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_video, 'cron', hour=0)  # 毎日0時に実行
    scheduler.start()

def process_video():
    try:
        # パラメータの選択
        avatar, motion, music, background = select_parameters()

        # 動画の生成
        video_path = generate_video(avatar, motion, music, background)

        # YouTubeへのアップロード
        video_id = upload_video(video_path)

        # データベースへの保存
        db.save_video(video_id, avatar, motion, music, background)

    except Exception as e:
        # エラーハンドリング
        log_error(str(e))
        send_alert(str(e))

if __name__ == '__main__':
    main()
