"""Entry point for the simplified dance video pipeline."""
import logging
import yaml

from parameter_selection import select_parameters
from video_generation import generate_video
from youtube_upload import upload_video
from database import Database
from error_handling import log_error, send_alert


def process_video(db: Database, config: dict) -> str:
    """Run the full pipeline once and store the result.

    Returns the video id reported by :func:`youtube_upload.upload_video`.
    """
    avatar, motion, music, background = select_parameters()
    video_path = generate_video(avatar, motion, music, background, config["output_dir"])
    video_id = upload_video(video_path)
    db.save_video(video_id, avatar, motion, music, background)
    return video_id


def main() -> None:
    with open("config.yaml", "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    logging.basicConfig(filename=config["log_file"], level=logging.INFO)
    db = Database(config["database"])

    try:
        video_id = process_video(db, config)
        print(f"Video processed: {video_id}")
    except Exception as exc:  # pragma: no cover - defensive programming
        log_error(str(exc))
        send_alert(str(exc))


if __name__ == "__main__":
    main()
