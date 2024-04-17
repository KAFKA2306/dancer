# アバターダンス動画自動生成システム

## 概要
このプロジェクトは、MMDやUnityを使用してアバターのダンス動画を自動生成し、YouTubeに定期的に投稿するシステムを開発することを目的としています。システムは、アバター、モーション、音楽、背景のパラメータをsemi autoで選択し、それらを組み合わせて高品質な動画を生成します。生成された動画は、YouTube APIを使用して自動的にアップロードされ、1日1本の投稿ペースを維持します。

## 主要機能
1. **動画生成**: MMDやUnityを使用して、選択されたパラメータを組み合わせてアバターのダンス動画を自動生成します。動画の解像度、フレームレート、エンコード設定は最適化されます。

2. **パラメータ選択**: アバター、モーション、音楽、背景のパラメータを semi auto で選択します。選択プロセスには、ランダム選択、ルールベース選択、機械学習を用いた選択など、複数のアルゴリズムが使用されます。

3. **YouTube投稿**: 生成された動画は、YouTube APIを使用して自動的にアップロードされます。動画のタイトル、説明、タグなどのメタデータは自動生成されます。投稿スケジュールはデータベースで管理され、1日1本の投稿ペースが維持されます。

4. **エラーハンドリングとモニタリング**: システムは、詳細なログ記録とチャットツールを使用したアラート通知機能を備えています。障害発生時には自動リトライと代替処理の仕組みが動作します。

5. **セキュリティとプライバシー**: APIキーや認証情報は安全に管理され、適切なアクセス制御が実施されます。ユーザーデータと生成された動画の機密性と完全性が確保されます。

## システムアーキテクチャ
- プログラミング言語: Python
- 開発環境: VSCode
- データ管理: SQLiteデータベース、ファイルシステム
- クラウドインフラ: AWS、GCP
- 動画生成: MMD (MikuMikuDance)、Unity

## セットアップ
1. リポジトリをクローンします。
2. 必要な依存関係をインストールします。
   - Python 3.x
   - pymeshio
   - PyYAML
   - google-api-python-client
   - google-auth-oauthlib
   - google-auth-httplib2
   - apscheduler
   - slack-sdk
3. MMDとUnityの環境を設定します。
   - MMDのインストールとパスの設定
   - Unityのインストールとプロジェクトの設定
4. Google Cloud ConsoleでYouTube APIの認証情報を取得します。
5. Slack APIの認証情報を取得します。
6. 設定ファイル (`config.yaml`) を編集し、必要な情報を記入します。
   - YouTube APIの認証情報
   - Slack APIの認証情報
   - データベースのパス
   - ログファイルのパス
   - MMDとUnityのパス

## 使用方法
1. パラメータ選択の設定を `parameters.yaml` ファイルで行います。
2. 動画生成の設定を `config.yaml` ファイルで行います。
3. 投稿スケジュールを `config.yaml` ファイルで設定します。
4. メインスクリプト (`main.py`) を実行します。

```bash
python main.py
```

## ディレクトリ構造
```
├── main.py
├── parameter_selection.py
├── video_generation.py
├── youtube_upload.py
├── database.py
├── error_handling.py
├── config.yaml
├── parameters.yaml
├── credentials.json
├── requirements.txt
└── README.md
```
