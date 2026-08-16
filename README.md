# 3Dダンス動画生成

このリポジトリは、3D形状で構成した関節キャラクターの姿勢を時間ごとに更新し、実際に動くフレーム列を描画して H.264 MP4 を生成します。

未実装の動画生成、疑似成功、YouTube公開状態、代替出力は持ちません。レンダリング、FFmpeg変換、ffprobe検証のいずれかが失敗した場合は処理も失敗します。

## 実行

必要な外部コマンドは `ffmpeg` と `ffprobe` です。Python側の3D描画には VTK 9.6.2 を使用します。

```bash
python -m pip install -r requirements.txt
python main.py \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512
```

成功時は `output/dance.mp4` を生成し、ffprobeで確認したcodec、解像度、duration、SHA-256をJSONで標準出力します。

## 何を検証しているか

CIは短い3Dダンス動画を実際に生成し、次を確認します。

- H.264 MP4 が生成される
- 指定した解像度とdurationをffprobeで取得できる
- FFmpeg `framemd5` で複数の異なるframe hashが存在する

最後の条件により、静止画を動画コンテナへ入れただけの出力は合格しません。

## 実装

- `dance_renderer.py`: VTKで3Dキャラクターを組み立て、関節位置を時間更新してPNG frameを描画する
- `video_generation.py`: FFmpegで生成したMP4をffprobeで検証し、SHA-256とmedia metadataを返す
- `main.py`: 明示されたduration、fps、size、output directoryで1本の動画を生成する

## 外部仕様

- VTK: https://vtk.org/
- VTK 9.6.2: https://vtk.org/download/
- FFmpeg / ffprobe: https://ffmpeg.org/
