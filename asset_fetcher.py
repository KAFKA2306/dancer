"""Download free sample assets for the demo pipeline.

The function :func:`download_assets` fetches a small avatar, animation,
background image and silent audio clip from public domain sources.  The files
are written into the ``assets`` directory (which is ignored by git) and the
resulting parameter lists are returned so they can populate ``parameters.yaml``.
"""
from __future__ import annotations

from pathlib import Path
import urllib.request
import yaml

ASSET_URLS = {
    "avatars": {
        "CesiumMan.gltf": "https://github.com/KhronosGroup/glTF-Sample-Models/raw/main/2.0/CesiumMan/glTF/CesiumMan.gltf",
    },
    "motions": {
        "AnimatedCube.gltf": "https://github.com/KhronosGroup/glTF-Sample-Models/raw/main/2.0/AnimatedCube/glTF/AnimatedCube.gltf",
    },
    "music": {
        "silence.mp3": "https://github.com/anars/blank-audio/blob/master/1-second-of-silence.mp3?raw=1",
    },
    "backgrounds": {
        "background.jpg": "https://www.w3.org/People/mimasa/test/imgformat/img/w3c_home.jpg",
    },
}


def download_assets(dest_dir: str = "assets", parameter_file: str | None = "parameters.yaml") -> dict:
    """Download demo assets and optionally update ``parameters.yaml``.

    Parameters
    ----------
    dest_dir:
        Directory where assets will be stored.
    parameter_file:
        If provided, write the downloaded paths into this YAML file so that
        :func:`parameter_selection.select_parameters` will pick them up.
    Returns
    -------
    dict
        Dictionary mapping parameter categories to lists of downloaded file
        paths.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    downloaded: dict[str, list[str]] = {}
    for category, files in ASSET_URLS.items():
        paths = []
        for filename, url in files.items():
            path = dest / filename
            if not path.exists():
                urllib.request.urlretrieve(url, path)
            paths.append(str(path))
        downloaded[category] = paths

    if parameter_file:
        with open(parameter_file, "w", encoding="utf-8") as fh:
            yaml.safe_dump(downloaded, fh)
    return downloaded


if __name__ == "__main__":  # pragma: no cover - manual utility
    assets = download_assets()
    print("Downloaded assets:")
    for category, files in assets.items():
        print(f"  {category}: {files}")
