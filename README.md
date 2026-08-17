# SiroinoSotai_PC ダンス動画生成

[![Test real Siroino dance](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml/badge.svg)](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml)

このリポジトリは `KAFKA2306/image2outfit` の実アバター `SiroinoSotai_PC.fbx` に、公開済みの BVH モーションを適用し、Blender で H.264 MP4 を生成します。

procedural dance、stub、fallback、疑似成功、代替出力は持ちません。FBX取得、BVH取得、import、bone mapping、skinned mesh検証、Blender render、FFmpeg変換、ffprobe検証のどれかが失敗した場合は処理も失敗します。

## ダンスモーション

`motions.json` が利用可能なモーションの正本です。現在は **102件**の BVH を保持しています。

選定条件は次の通りです。

- CMU index の説明に `dance` / `dancing` を含む動作。ただし静止ポーズ `49_15` は除外
- Subject #93 `Charleston Dance` の実ダンス区間 `93_03`〜`93_08`
- Subject #94 `indian dance` の `94_01`〜`94_16`

モーション本体をこのリポジトリへ複製せず、`una-dinosauria/cmu-mocap` の commit `09a07f54f3bbb58797325f009282d0b2048a2871` に固定した raw URL から取得します。moving branch は使いません。

利用条件の正本は CMU と BVH 変換者の公開文書です。CMU は研究利用と商用製品への組込みを認めていますが、データ自体を変換後も含めて直接再販売することは禁止しています。Bruce Hahne の BVH 変換は追加制限を課していません。

BVH 変換版は各ファイルの第1 frame に T-pose を追加し、MotionBuilder 向けの joint 名へ変換し、frame time を 120 fps 相当に修正しています。`dancer` はこの第1 frame を基準姿勢として、source/target bone の局所 rest axis 差を補正して相対回転を `SiroinoSotai_PC` へ適用します。

一覧確認:

```bash
python main.py --list-motions
```

## 正本アバター

入力は moving branch ではなく、次の `image2outfit` commitへ固定しています。

- repository: `KAFKA2306/image2outfit`
- commit: `e6c3f707932fe3cdbddf07e77fa26279a0ff0252`
- path: `Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx`
- Git blob SHA: `13cc948a3db323ddce81e2b95e0b9ddc0b9480e2`
- size: `3,862,972 bytes`

実行時はこの immutable commit から FBX を取得し、既知の size と一致しない入力を拒否します。

必須 Armature bone は次の12本です。

`Hips`, `Chest`, `Neck`, `Head`, `UpperArm_L`, `UpperArm_R`, `LowerArm_L`, `LowerArm_R`, `UpperLeg_L`, `UpperLeg_R`, `LowerLeg_L`, `LowerLeg_R`

さらに、これらの bone を持つ Armature へ実際に接続された `ARMATURE` modifier 付き mesh が存在しなければ render しません。

## 実行

Python 3.11 と `ffmpeg` / `ffprobe` が必要です。Python 側は Blender Foundation の `bpy==4.5.12` を使用します。

```bash
python -m pip install -r requirements.txt
python main.py \
  --motion-id 93_03 \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512
```

`--motion-id` を省略した場合は `93_03` を使います。指定された id が `motions.json` に存在しなければ失敗します。

成功時は `output/dance.mp4` を生成し、ffprobe で確認した codec、解像度、duration、SHA-256 に加えて、実際に使った `motion_id` と固定 source URL を JSON で標準出力します。

## 自動対応する範囲

`motions.json` の BVH はすべて同じ adapter を通ります。motion ごとの専用コードは追加しません。

1. catalog から motion id を解決
2. commit 固定 URL から BVH を取得
3. `HIERARCHY` header と timing metadata を検証
4. Blender へ BVH Armature を import
5. CMU MotionBuilder joint 名を Siroino bone へ対応付け
6. source/target の局所 rest axis 差を補正
7. BVH の相対回転を Siroino Armature へ適用
8. 実 frame を render
9. H.264 へ変換し ffprobe と frame hash で検証

未対応形式を別形式として成功扱いする fallback はありません。

## 検証

CI 自身が正本 FBX と公開 BVH `93_03` を取得して短い動画を render し、次を確認します。

- catalog が102件で重複せず、全 URL が固定 commit を参照する
- 正本 FBX の size が一致する
- 必須 Siroino bone をすべて持つ Armature が1つ存在する
- その Armature に接続された skinned mesh が存在する
- BVH に必要な source bone が存在する
- Blender 4.5.12 で実 frame を render できる
- H.264 MP4 を ffprobe で読める
- FFmpeg `framemd5` で複数の異なる frame hash が存在する
- 出力 metadata に `motion_id` と固定 source URL が残る

最後の条件群により、Siroino の静止画を動画コンテナへ入れただけ、または出典不明の motion を使っただけでは合格しません。

## 一次資料

- CMU Graphics Lab Motion Capture Database: https://mocap.cs.cmu.edu/
- Bruce Hahne BVH conversion README / usage rights: https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/the-motionbuilder-friendly-bvh-conversion-release-of-cmus-motion-capture-database/readme-file-for-the-bvh-conversion-release
- 固定 BVH mirror commit: https://github.com/una-dinosauria/cmu-mocap/tree/09a07f54f3bbb58797325f009282d0b2048a2871
- 固定 motion index: https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/09a07f54f3bbb58797325f009282d0b2048a2871/cmu-mocap-index-text.txt
- Blender 4.5 Import/Export add-ons: https://docs.blender.org/manual/en/4.5/addons/import_export/index.html
- SiroinoSotai_PC FBX: https://github.com/KAFKA2306/image2outfit/blob/e6c3f707932fe3cdbddf07e77fa26279a0ff0252/Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx
- Blender Python module: https://pypi.org/project/bpy/4.5.12/
- FFmpeg / ffprobe: https://ffmpeg.org/
