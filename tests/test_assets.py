import os
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from asset_fetcher import download_assets


def test_download_assets(tmp_path):
    assets = download_assets(dest_dir=tmp_path, parameter_file=None)
    for paths in assets.values():
        for p in paths:
            assert os.path.exists(p)
