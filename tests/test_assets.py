import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import asset_fetcher


def test_download_assets_without_network(tmp_path, monkeypatch):
    def fake_urlretrieve(url, path):
        pathlib.Path(path).write_bytes(f"fixture:{url}".encode("utf-8"))
        return str(path), None

    monkeypatch.setattr(asset_fetcher.urllib.request, "urlretrieve", fake_urlretrieve)

    assets = asset_fetcher.download_assets(dest_dir=tmp_path, parameter_file=None)
    assert set(assets) == {"avatars", "motions", "music", "backgrounds"}
    for paths in assets.values():
        for path in paths:
            assert pathlib.Path(path).is_file()
