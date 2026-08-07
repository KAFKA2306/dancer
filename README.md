# 簡易ダンス動画パイプライン

このリポジトリは、動画生成と外部公開を同じ「成功」として扱わないため、生成・媒体検証・公開状態を分離して記録します。

## 実行モード

`config.yaml` の `mode` で実行境界を明示します。既定値は安全な `STUB` です。

| mode | 保証範囲 | YouTube公開 |
| --- | --- | --- |
| `STUB` | 選択パラメータを `.stub.json` に記録するだけ。動画は生成しない | 行わない |
| `LOCAL_RENDER` | 明示的に注入したrendererの出力を `ffprobe` で検証する | 行わない |
| `YOUTUBE_PUBLISH` | 検証済み動画だけを明示的なYouTube uploaderへ渡す | uploaderの成功responseに非空の `id` がある場合だけ `UPLOADED` |

`STUB` は `.mp4` を生成せず、YouTube動画IDも生成しません。サンプル実行を実動画生成済み・YouTube公開済みの証拠として扱わないでください。

## 状態モデル

新規実行は `pipeline_runs` に保存され、少なくとも次を独立して確認できます。

- `generation_status`
- `validation_status`
- `upload_status`
- `youtube_video_id`
- `error`
- artifact path / SHA-256
- `idempotency_key`

公開状態は `NOT_ATTEMPTED | STUBBED | UPLOADED | FAILED` です。無効なmediaは `YOUTUBE_PUBLISH` でもuploadへ進まず、`UPLOADED` にはなりません。同一入力はidempotency keyで重複実行を識別します。

## 実行手順

```bash
python -m pip install -r requirements.txt
python asset_fetcher.py
python main.py
```

既定の `STUB` 実行例では、出力は次のように公開未実施を明示します。

```text
Pipeline result: mode=STUB validation=NOT_APPLICABLE upload=STUBBED youtube_video_id=NONE
```

`LOCAL_RENDER` / `YOUTUBE_PUBLISH` では、実際のrendererを実装側から明示的に注入する必要があります。動画検証には `ffprobe` を使用します。`YOUTUBE_PUBLISH` はさらに公式APIを呼ぶuploaderの実装とcredential管理が必要であり、このリポジトリはcredentialや疑似YouTube IDを自動生成しません。

## テスト

テストは外部YouTube APIや実credentialを使用しません。

```bash
python -m py_compile video_generation.py youtube_upload.py database.py main.py
python -m pytest -q
```

固定fixtureで次を検証します。

- stubで `.mp4` とYouTube IDが生成されない
- 無効mediaが公開成功へ進まない
- uploader例外を `FAILED` として記録する
- 成功responseの `id` だけをYouTube IDとして保存する
- DBで生成・検証・公開状態を分離する
- 同一idempotency keyの二重登録を拒否する

GitHub Actionsでも同じofflineテストを実行します。

## 外部仕様

- ffprobe documentation: https://ffmpeg.org/ffprobe.html
- YouTube Data API `videos.insert`: https://developers.google.com/youtube/v3/docs/videos/insert
