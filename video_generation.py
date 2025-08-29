"""Utility for generating placeholder videos.

The real project would use MMD or Unity, but for testing purposes we
simply create a small text file with an ``.mp4`` extension that records the
chosen parameters.  The function returns the path to the created file.
"""
import os
import uuid


def generate_video(avatar: str, motion: str, music: str, background: str, output_dir: str) -> str:
    """Create a dummy video file and return its path.

    Parameters
    ----------
    avatar, motion, music, background:
        Selected parameter values. They are written into the file for
        traceability.
    output_dir:
        Directory where the generated file will be placed. It is created if
        it does not already exist.
    """
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, f"{uuid.uuid4().hex}.mp4")
    with open(video_path, "w", encoding="utf-8") as fh:
        fh.write(
            "Generated video\n"
            f"avatar={avatar}\n"
            f"motion={motion}\n"
            f"music={music}\n"
            f"background={background}\n"
        )
    return video_path
