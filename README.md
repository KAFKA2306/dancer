# dancer

[![Test real Siroino dance](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml/badge.svg)](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml)
[![Render catalog motion](https://github.com/KAFKA2306/dancer/actions/workflows/render-catalog-motion.yml/badge.svg)](https://github.com/KAFKA2306/dancer/actions/workflows/render-catalog-motion.yml)

公開済みの実ダンスモーションを [`SiroinoSotai_PC`](https://github.com/KAFKA2306/image2outfit/blob/e6c3f707932fe3cdbddf07e77fa26279a0ff0252/Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx) へ retarget し、Blender で H.264 MP4 を生成します。

**手書きダンス、procedural pose、疑似モーション、fallback は使いません。** 動作源は [`src/dancer/motions.json`](https://github.com/KAFKA2306/dancer/blob/main/src/dancer/motions.json) が指す公開 BVH だけです。

依存管理と実行には [uv](https://docs.astral.sh/uv/) を使います。`bpy==4.5.12` は [PyPI の配布物](https://pypi.org/project/bpy/4.5.12/)が CPython 3.11 向けなので、このプロジェクトも Python 3.11 に固定しています。

## 実行

```bash
uv sync --locked
uv run --frozen dancer --list-motions
```

日付から自動選択して render:

```bash
uv run --frozen dancer \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512
```

特定 motion を指定:

```bash
uv run --frozen dancer \
  --motion-id 93_03 \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512
```

`--motion-id auto` は UTC 日付から1件を決定的に選び、102日で全カタログを一巡します。失敗した motion を別 motion に置き換えません。

## モーション

現在のカタログは **102件**です。元データと利用条件は以下を正本にしています。

- [CMU Graphics Lab Motion Capture Database](https://mocap.cs.cmu.edu/)
- [Bruce Hahne の MotionBuilder-friendly BVH conversion README](https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/the-motionbuilder-friendly-bvh-conversion-release-of-cmus-motion-capture-database/readme-file-for-the-bvh-conversion-release)
- [固定 BVH mirror commit `09a07f54...`](https://github.com/una-dinosauria/cmu-mocap/tree/09a07f54f3bbb58797325f009282d0b2048a2871)
- [固定 motion index](https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/09a07f54f3bbb58797325f009282d0b2048a2871/cmu-mocap-index-text.txt)

CMU は研究利用と商用製品への組込みを認めていますが、データ自体の直接再販売は変換後を含めて禁止しています。BVH 変換者は追加制限を課していません。利用前に上記一次資料を確認してください。

## 自動検証

[Test real Siroino dance](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml) は実 Siroino FBX と公開 BVH を取得し、Blender render、H.264、ffprobe、複数 frame hash を検証します。

[Render catalog motion](https://github.com/KAFKA2306/dancer/actions/workflows/render-catalog-motion.yml) は毎日 07:17 `Asia/Tokyo` に1件を render し、MP4 と metadata を Actions artifact として30日保持します。
