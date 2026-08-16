# SiroinoSotai_PC ダンス動画生成

このリポジトリは `KAFKA2306/image2outfit` の実アバター `SiroinoSotai_PC.fbx` を Blender へ読み込み、実Armatureを時間ごとに変形して H.264 MP4 を生成します。

procedural character、stub、fallback、疑似成功、代替出力は持ちません。FBX取得、FBX import、必須bone検証、skinned mesh検証、Blender render、FFmpeg変換、ffprobe検証のどれかが失敗した場合は処理も失敗します。

## 正本アバター

入力は moving branch ではなく、次の `image2outfit` commitへ固定しています。

- repository: `KAFKA2306/image2outfit`
- commit: `e6c3f707932fe3cdbddf07e77fa26279a0ff0252`
- path: `Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx`
- Git blob SHA: `13cc948a3db323ddce81e2b95e0b9ddc0b9480e2`
- size: `3,862,972 bytes`

実行時はこのimmutable commitからFBXを取得し、既知のsizeと一致しない入力を拒否します。

必須Armature boneは `image2outfit` に保存されているUnity ModelImporter humanoid mappingと同じです。

`Hips`, `Chest`, `Neck`, `Head`, `UpperArm_L`, `UpperArm_R`, `LowerArm_L`, `LowerArm_R`, `UpperLeg_L`, `UpperLeg_R`, `LowerLeg_L`, `LowerLeg_R`

さらに、これらのboneを持つArmatureへ実際に接続された `ARMATURE` modifier付きmeshが存在しなければrenderしません。

## 実行

Python 3.11 と `ffmpeg` / `ffprobe` が必要です。Python側は Blender Foundation の `bpy==4.5.12` を使用します。

```bash
python -m pip install -r requirements.txt
python main.py \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512
```

成功時は `output/dance.mp4` を生成し、ffprobeで確認したcodec、解像度、duration、SHA-256をJSONで標準出力します。

## 検証

CI自身が正本FBXを取得して短い動画をrenderし、次を確認します。

- 正本FBXのsizeが一致する
- 必須Siroino boneをすべて持つArmatureが1つ存在する
- そのArmatureに接続されたskinned meshが存在する
- Blender 4.5.12で実frameをrenderできる
- H.264 MP4をffprobeで読める
- FFmpeg `framemd5` で複数の異なるframe hashが存在する

最後の条件により、Siroinoの静止画を動画コンテナへ入れただけでは合格しません。

## 一次資料

- SiroinoSotai_PC FBX: https://github.com/KAFKA2306/image2outfit/blob/e6c3f707932fe3cdbddf07e77fa26279a0ff0252/Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx
- Blender 4.5 FBX: https://docs.blender.org/manual/en/4.5/files/import_export/fbx.html
- Blender Python module: https://pypi.org/project/bpy/4.5.12/
- FFmpeg / ffprobe: https://ffmpeg.org/
