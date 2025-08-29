# 簡易ダンス動画パイプライン

このプロジェクトはサンプルのアバターとモーションを用いて生成された結果のみを記録します。

## 実行手順

```bash
pip install -r requirements.txt
python asset_fetcher.py
python main.py
```

## 実行結果

### asset_fetcher.py

```
Downloaded assets:
  avatars: ['assets/CesiumMan.gltf']
  motions: ['assets/AnimatedCube.gltf']
  music: ['assets/silence.mp3']
  backgrounds: ['assets/background.jpg']
```

### main.py

```
Video processed: 133d01068e5e4e4d940c3e4c8b345a4a
```

生成された動画ファイル `output/320b390283c5418796b288ed84783c29.mp4` の内容:

```
Generated video
avatar=assets/CesiumMan.gltf
motion=assets/AnimatedCube.gltf
music=assets/silence.mp3
background=assets/background.jpg
```

データベース `videos.db` のレコード:

```
1|133d01068e5e4e4d940c3e4c8b345a4a|assets/CesiumMan.gltf|assets/AnimatedCube.gltf|assets/silence.mp3|assets/background.jpg
```

## テスト

```bash
pytest
```

```
2 passed in 1.07s
```
