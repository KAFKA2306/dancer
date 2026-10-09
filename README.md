# dancer

[![Test real Siroino dance](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml/badge.svg)](https://github.com/KAFKA2306/dancer/actions/workflows/test.yml)
[![Autonomous production smoke](https://github.com/KAFKA2306/dancer/actions/workflows/production.yml/badge.svg)](https://github.com/KAFKA2306/dancer/actions/workflows/production.yml)

公開BVHを `SiroinoSotai_PC` へretargetし、Blender/FFmpegで実3Dダンス動画を生成します。手書きダンス、procedural pose、疑似motion、fallback motionは使いません。

## Render

```bash
uv sync --locked
uv run --frozen dancer \
  --motion-id auto \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512
```

`--motion-id auto` はUTC日付から1件を決定的に選び、102件を循環します。

カタログ内の102件をまとめて作成する場合は、各動画を
`output/motions/<motion-id>/dance.mp4` に分けて保存します。

```bash
uv run --frozen dancer \
  --all \
  --output-dir output \
  --duration-seconds 2 \
  --fps 24 \
  --size 512 \
  --samples 8
```

## Autonomous production

```bash
uv run --frozen dancer production \
  --output-dir output \
  --duration-seconds 8 \
  --fps 24 \
  --width 1080 \
  --height 1920 \
  --candidates 3
```

1回のproduction runは次を行います。

```text
pinned BVH + pinned Siroino FBX
  -> multiple Blender camera candidates
  -> rights-verified music + beat-aligned duration
  -> FFmpeg mux / loudness normalization
  -> ffprobe + black-frame + audio + framing audit
  -> deterministic winner selection
  -> thumbnail from the selected real frame
  -> provenance-derived YouTube metadata
  -> rights/policy gate
  -> manifest.json
```

同じinputでは同じrun IDを使い、hashが一致する完了artifactを再利用します。全candidateがauditに失敗した場合はpublish artifactを作りません。

## YT3 handoff / YouTube

YT3を隣接cloneして一度OAuthを済ませた環境では、同じproduction commandからYT3へ渡せます。

```bash
uv run --frozen dancer production \
  --output-dir output \
  --yt3-root ../yt3 \
  --publish-profile byosan
```

`--publish-profile` は `byosan | yawa | humanity` の明示指定が必須です。dancer自身はYouTube tokenやchannel routingを持たず、YT3のprofile/channel identity check、private staging、thumbnail、publish receipt、visibility verificationを使います。公開予約は `--publish-at 2026-08-21T12:00:00+09:00` のように指定できます。

GitHub Actions の production workflow は YT3 を mutable `main` から実行せず、workflow に記録した full commit SHA だけを fetch/checkout します。生成される dancer manifest の `publication` と `publication-state.json` には dancer revision と YT3 revision の両方を保存し、公開結果から実行コードを追跡できます。Pull Request では YT3 checkout と外部公開を実行しません。

YouTube OAuth client、refresh token、API project auditなど外部側の条件が成立しない場合、publishは成功扱いにしません。

## Source rights

- Motion: [CMU Motion Capture Database](https://mocap.cs.cmu.edu/) / [Bruce Hahne BVH conversion terms](https://sites.google.com/a/cgspeed.com/cgspeed/motion-capture/the-motionbuilder-friendly-bvh-conversion-release-of-cmus-motion-capture-database/readme-file-for-the-bvh-conversion-release)
- Avatar: [SiroinoSotai](https://booth.pm/ja/items/8268676), CC0 1.0; PC FBX is explicitly listed in the CC0-covered files.
- Default music: [Scott Joplin - Maple Leaf Rag.ogg](https://commons.wikimedia.org/wiki/File:Scott_Joplin_-_Maple_Leaf_Rag.ogg), recording released to the public domain by its copyright holder; catalog entry pins the source SHA-1 and 120 BPM metadata.

Every production manifest records these source URLs and hashes. Unknown-rights assets are blocked before YT3 handoff.
